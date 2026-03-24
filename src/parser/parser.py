from __future__ import annotations

from lexer.token import Token, TokenType
from parser.ast import (
    ASTNode, ProgramNode,
    LiteralExpr, IdentifierExpr, BinaryExpr, UnaryExpr, CallExpr, AssignmentExpr, IncDecExpr,
    BlockStmt, ExprStmt, IfStmt, WhileStmt, ForStmt, ReturnStmt, VarDeclStmt, EmptyStmt,
    FunctionDecl, StructDecl, Param,
)
from parser.errors import ParseError, ErrorMetrics


_TYPE_KEYWORDS = frozenset({
    TokenType.KW_INT, TokenType.KW_FLOAT, TokenType.KW_BOOL, TokenType.KW_VOID,
})

_ASSIGN_OPS = frozenset({
    TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN,
    TokenType.STAR_ASSIGN, TokenType.SLASH_ASSIGN, TokenType.PERCENT_ASSIGN,
})

_SYNC_TOKENS = frozenset({
    TokenType.SEMICOLON, TokenType.RBRACE,
    TokenType.KW_FN, TokenType.KW_STRUCT, TokenType.KW_IF, TokenType.KW_WHILE,
    TokenType.KW_FOR, TokenType.KW_RETURN, TokenType.KW_INT, TokenType.KW_FLOAT,
    TokenType.KW_BOOL, TokenType.KW_VOID,
})


class Parser:
    def __init__(self, tokens: list[Token], max_errors: int | None = None):
        self._tokens = tokens
        self._pos = 0
        self._max_errors = max_errors
        self.errors: list[ParseError] = []
        self.metrics = ErrorMetrics()
        self._just_synced = False
        self._known_types: set[str] = {"int", "float", "bool", "void"}

    def parse(self) -> ProgramNode:
        decls: list[ASTNode] = []
        while not self._is_at_end():
            d = self._declaration()
            if d is not None:
                decls.append(d)
        tok = self._tokens[0] if self._tokens else None
        line = tok.line if tok else 1
        col = tok.column if tok else 1
        return ProgramNode(line, col, tuple(decls))

    def _declaration(self) -> ASTNode | None:
        try:
            if self._check(TokenType.KW_FN):
                return self._function_decl()
            if self._check(TokenType.KW_STRUCT):
                return self._struct_decl()
            if self._is_type_start():
                return self._var_decl()
            return self._statement()
        except _ParseAbort:
            self._synchronize()
            return None

    def _function_decl(self) -> FunctionDecl:
        fn_tok = self._consume(TokenType.KW_FN, "ожидалось ключевое слово 'fn'")
        name_tok = self._consume(TokenType.IDENTIFIER, "ожидалось имя функции")
        self._consume(TokenType.LPAREN, "ожидалось '(' после имени функции")
        params = self._parameters()
        self._consume(TokenType.RPAREN, "ожидалось ')' после списка параметров")
        ret_type = "void"
        if self._match(TokenType.ARROW):
            ret_type = self._type_name()
        body = self._block()
        return FunctionDecl(fn_tok.line, fn_tok.column, name_tok.lexeme, tuple(params), ret_type, body)

    def _struct_decl(self) -> StructDecl:
        st_tok = self._consume(TokenType.KW_STRUCT, "ожидалось ключевое слово 'struct'")
        name_tok = self._consume(TokenType.IDENTIFIER, "ожидалось имя структуры")
        self._known_types.add(name_tok.lexeme)
        self._consume(TokenType.LBRACE, "ожидалось '{' после имени структуры")
        fields: list[VarDeclStmt] = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            fields.append(self._var_decl())
        self._consume(TokenType.RBRACE, "ожидалось '}' после тела структуры")
        return StructDecl(st_tok.line, st_tok.column, name_tok.lexeme, tuple(fields))

    def _var_decl(self) -> VarDeclStmt:
        type_tok = self._peek()
        vtype = self._type_name()
        name_tok = self._consume(TokenType.IDENTIFIER, "ожидалось имя переменной")
        init: ASTNode | None = None
        if self._match(TokenType.ASSIGN):
            init = self._expression()
        self._consume(TokenType.SEMICOLON, "ожидалось ';' после объявления переменной",
                      suggestion="Не забыли ли точку с запятой?")
        return VarDeclStmt(type_tok.line, type_tok.column, vtype, name_tok.lexeme, init)

    def _var_decl_no_semi(self) -> VarDeclStmt:
        type_tok = self._peek()
        vtype = self._type_name()
        name_tok = self._consume(TokenType.IDENTIFIER, "ожидалось имя переменной")
        init: ASTNode | None = None
        if self._match(TokenType.ASSIGN):
            init = self._expression()
        return VarDeclStmt(type_tok.line, type_tok.column, vtype, name_tok.lexeme, init)

    def _parameters(self) -> list[Param]:
        params: list[Param] = []
        if self._check(TokenType.RPAREN):
            return params
        params.append(self._parameter())
        while self._match(TokenType.COMMA):
            params.append(self._parameter())
        return params

    def _parameter(self) -> Param:
        type_tok = self._peek()
        ptype = self._type_name()
        name_tok = self._consume(TokenType.IDENTIFIER, "ожидалось имя параметра")
        return Param(type_tok.line, type_tok.column, ptype, name_tok.lexeme)

    def _type_name(self) -> str:
        for kw in _TYPE_KEYWORDS:
            if self._match(kw):
                return self._previous().lexeme
        if self._check(TokenType.IDENTIFIER):
            return self._advance().lexeme
        self._error("ожидалось имя типа")
        return "<error>"

    def _is_type_start(self) -> bool:
        if self._peek().type in _TYPE_KEYWORDS:
            return True
        if self._peek().type == TokenType.IDENTIFIER and self._peek().lexeme in self._known_types:
            return True
        return False

    def _statement(self) -> ASTNode:
        if self._check(TokenType.LBRACE):
            return self._block()
        if self._check(TokenType.KW_IF):
            return self._if_stmt()
        if self._check(TokenType.KW_WHILE):
            return self._while_stmt()
        if self._check(TokenType.KW_FOR):
            return self._for_stmt()
        if self._check(TokenType.KW_RETURN):
            return self._return_stmt()
        if self._match(TokenType.SEMICOLON):
            prev = self._previous()
            return EmptyStmt(prev.line, prev.column)
        if self._is_type_start():
            return self._var_decl()
        return self._expr_stmt()

    def _block(self) -> BlockStmt:
        tok = self._consume(TokenType.LBRACE, "ожидалось '{'")
        stmts: list[ASTNode] = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            d = self._declaration()
            if d is not None:
                stmts.append(d)
        self._consume(TokenType.RBRACE, "ожидалось '}'")
        return BlockStmt(tok.line, tok.column, tuple(stmts))

    def _if_stmt(self) -> IfStmt:
        tok = self._consume(TokenType.KW_IF, "ожидалось ключевое слово 'if'")
        self._consume(TokenType.LPAREN, "ожидалось '(' после 'if'")
        cond = self._expression()
        self._consume(TokenType.RPAREN, "ожидалось ')' после условия if")
        then_br = self._statement()
        else_br: ASTNode | None = None
        if self._match(TokenType.KW_ELSE):
            else_br = self._statement()
        return IfStmt(tok.line, tok.column, cond, then_br, else_br)

    def _while_stmt(self) -> WhileStmt:
        tok = self._consume(TokenType.KW_WHILE, "ожидалось ключевое слово 'while'")
        self._consume(TokenType.LPAREN, "ожидалось '(' после 'while'")
        cond = self._expression()
        self._consume(TokenType.RPAREN, "ожидалось ')' после условия while")
        body = self._statement()
        return WhileStmt(tok.line, tok.column, cond, body)

    def _for_stmt(self) -> ForStmt:
        tok = self._consume(TokenType.KW_FOR, "ожидалось ключевое слово 'for'")
        self._consume(TokenType.LPAREN, "ожидалось '(' после 'for'")

        init: ASTNode | None = None
        if self._match(TokenType.SEMICOLON):
            pass
        elif self._is_type_start():
            init = self._var_decl_no_semi()
            self._consume(TokenType.SEMICOLON, "ожидалось ';' после инициализации for")
        else:
            init = self._expression()
            self._consume(TokenType.SEMICOLON, "ожидалось ';' после инициализации for")

        cond: ASTNode | None = None
        if not self._check(TokenType.SEMICOLON):
            cond = self._expression()
        self._consume(TokenType.SEMICOLON, "ожидалось ';' после условия for")

        update: ASTNode | None = None
        if not self._check(TokenType.RPAREN):
            update = self._expression()
        self._consume(TokenType.RPAREN, "ожидалось ')' после заголовка for")

        body = self._statement()
        return ForStmt(tok.line, tok.column, init, cond, update, body)

    def _return_stmt(self) -> ReturnStmt:
        tok = self._consume(TokenType.KW_RETURN, "ожидалось ключевое слово 'return'")
        value: ASTNode | None = None
        if not self._check(TokenType.SEMICOLON):
            value = self._expression()
        self._consume(TokenType.SEMICOLON, "ожидалось ';' после return",
                      suggestion="Не забыли ли точку с запятой?")
        return ReturnStmt(tok.line, tok.column, value)

    def _expr_stmt(self) -> ExprStmt:
        expr = self._expression()
        self._consume(TokenType.SEMICOLON, "ожидалось ';' после выражения",
                      suggestion="Не забыли ли точку с запятой?")
        return ExprStmt(expr.line, expr.column, expr)

    def _expression(self) -> ASTNode:
        return self._assignment()

    def _assignment(self) -> ASTNode:
        expr = self._logical_or()
        if self._peek().type in _ASSIGN_OPS:
            op_tok = self._advance()
            if not isinstance(expr, IdentifierExpr):
                self._error_at(expr.line, expr.column, "недопустимая цель присваивания")
            value = self._assignment()
            target = expr.name if isinstance(expr, IdentifierExpr) else "<error>"
            return AssignmentExpr(expr.line, expr.column, target, op_tok.lexeme, value)
        return expr

    def _logical_or(self) -> ASTNode:
        left = self._logical_and()
        while self._match(TokenType.OR_OR):
            op = self._previous().lexeme
            right = self._logical_and()
            left = BinaryExpr(left.line, left.column, left, op, right)
        return left

    def _logical_and(self) -> ASTNode:
        left = self._equality()
        while self._match(TokenType.AND_AND):
            op = self._previous().lexeme
            right = self._equality()
            left = BinaryExpr(left.line, left.column, left, op, right)
        return left

    def _equality(self) -> ASTNode:
        left = self._relational()
        if self._peek().type in (TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
            op_tok = self._advance()
            right = self._relational()
            left = BinaryExpr(left.line, left.column, left, op_tok.lexeme, right)
            if self._peek().type in (TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
                self._error("цепочка операций сравнения на равенство недопустима (неассоциативно)")
        return left

    def _relational(self) -> ASTNode:
        left = self._additive()
        if self._peek().type in (TokenType.LESS, TokenType.LESS_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL):
            op_tok = self._advance()
            right = self._additive()
            left = BinaryExpr(left.line, left.column, left, op_tok.lexeme, right)
            if self._peek().type in (TokenType.LESS, TokenType.LESS_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL):
                self._error("цепочка отношений (<, >, …) недопустима (неассоциативно)")
        return left

    def _additive(self) -> ASTNode:
        left = self._multiplicative()
        while self._peek().type in (TokenType.PLUS, TokenType.MINUS):
            op_tok = self._advance()
            right = self._multiplicative()
            left = BinaryExpr(left.line, left.column, left, op_tok.lexeme, right)
        return left

    def _multiplicative(self) -> ASTNode:
        left = self._unary()
        while self._peek().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_tok = self._advance()
            right = self._unary()
            left = BinaryExpr(left.line, left.column, left, op_tok.lexeme, right)
        return left

    def _unary(self) -> ASTNode:
        if self._peek().type in (TokenType.PLUS_PLUS, TokenType.MINUS_MINUS):
            op_tok = self._advance()
            operand = self._unary()
            if isinstance(operand, IdentifierExpr):
                return IncDecExpr(op_tok.line, op_tok.column, operand.name, op_tok.lexeme, True)
            self._error_at(op_tok.line, op_tok.column, "недопустимая цель для ++/--")
            return operand
        if self._peek().type in (TokenType.MINUS, TokenType.BANG):
            op_tok = self._advance()
            operand = self._unary()
            return UnaryExpr(op_tok.line, op_tok.column, op_tok.lexeme, operand)
        return self._postfix()

    def _postfix(self) -> ASTNode:
        expr = self._primary()
        if self._peek().type in (TokenType.PLUS_PLUS, TokenType.MINUS_MINUS):
            op_tok = self._advance()
            if isinstance(expr, IdentifierExpr):
                return IncDecExpr(expr.line, expr.column, expr.name, op_tok.lexeme, False)
            self._error_at(op_tok.line, op_tok.column, "недопустимая цель для ++/--")
        return expr

    def _primary(self) -> ASTNode:
        tok = self._peek()

        match tok.type:
            case TokenType.INT_LITERAL:
                self._advance()
                return LiteralExpr(tok.line, tok.column, tok.literal, "int")
            case TokenType.FLOAT_LITERAL:
                self._advance()
                return LiteralExpr(tok.line, tok.column, tok.literal, "float")
            case TokenType.STRING_LITERAL:
                self._advance()
                return LiteralExpr(tok.line, tok.column, tok.literal, "string")
            case TokenType.BOOL_LITERAL:
                self._advance()
                return LiteralExpr(tok.line, tok.column, tok.literal, "bool")
            case TokenType.NULL_LITERAL:
                self._advance()
                return LiteralExpr(tok.line, tok.column, None, "null")
            case TokenType.IDENTIFIER:
                self._advance()
                if self._match(TokenType.LPAREN):
                    args = self._arguments()
                    self._consume(TokenType.RPAREN, "ожидалось ')' после аргументов")
                    return CallExpr(tok.line, tok.column, tok.lexeme, tuple(args))
                return IdentifierExpr(tok.line, tok.column, tok.lexeme)
            case TokenType.LPAREN:
                self._advance()
                expr = self._expression()
                self._consume(TokenType.RPAREN, "ожидалось ')' после выражения")
                return expr

        self._error(f"ожидалось выражение, получен токен {tok.type.name}")
        return LiteralExpr(tok.line, tok.column, None, "null")

    def _arguments(self) -> list[ASTNode]:
        if self._check(TokenType.RPAREN):
            return []
        args = [self._expression()]
        while self._match(TokenType.COMMA):
            args.append(self._expression())
        return args

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _previous(self) -> Token:
        return self._tokens[self._pos - 1]

    def _is_at_end(self) -> bool:
        return self._tokens[self._pos].type == TokenType.END_OF_FILE

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        if not self._is_at_end():
            self._pos += 1
        self._just_synced = False
        return tok

    def _check(self, tt: TokenType) -> bool:
        return self._peek().type == tt

    def _match(self, *types: TokenType) -> bool:
        for tt in types:
            if self._check(tt):
                self._advance()
                return True
        return False

    def _consume(self, tt: TokenType, message: str, suggestion: str | None = None) -> Token:
        if self._check(tt):
            return self._advance()
        self._error(f"{message} (ожидалось: {tt.name})", suggestion=suggestion)
        return self._peek()

    def _error(self, message: str, suggestion: str | None = None) -> None:
        tok = self._peek()
        self._error_at(tok.line, tok.column, message, suggestion)

    def _error_at(self, line: int, col: int, message: str, suggestion: str | None = None) -> None:
        if self._just_synced:
            self.metrics.cascade_prevented_count += 1
            return

        if self._max_errors is not None and self.metrics.reported_count >= self._max_errors:
            raise _ParseAbort()

        self.errors.append(ParseError(message, line, col, suggestion))
        self.metrics.reported_count += 1
        raise _ParseAbort()

    def _synchronize(self) -> None:
        self.metrics.recovered_count += 1
        self._just_synced = True
        while not self._is_at_end():
            if self._previous().type == TokenType.SEMICOLON:
                return
            if self._peek().type in _SYNC_TOKENS:
                return
            self._advance()


class _ParseAbort(Exception):
    pass
