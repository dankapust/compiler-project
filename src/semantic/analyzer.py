from __future__ import annotations

from typing import Any

from parser.ast import (
    ASTNode,
    ProgramNode,
    LiteralExpr,
    IdentifierExpr,

    MemberAccessExpr,

    BinaryExpr,
    UnaryExpr,
    CallExpr,
    AssignmentExpr,
    IncDecExpr,
    BlockStmt,
    ExprStmt,
    IfStmt,
    WhileStmt,
    ForStmt,
    ReturnStmt,
    VarDeclStmt,
    EmptyStmt,
    FunctionDecl,
    StructDecl,
    Param,
)
from semantic.errors import SemanticError
from semantic.output import DecoratedAST
from semantic.symbol_table import SymbolInfo, SymbolKind, SymbolTable
from semantic import type_system as TS
from semantic.type_system import (
    Type,
    TypeKind,
    VOID,
    INT,
    FLOAT,
    BOOL,
    STRING,
    NULL_T,
    ERROR_T,
    struct_type,
    function_type,
    types_equal,
    is_numeric,
    assignment_compatible,
    binary_arithmetic_result,
    binary_compare_result,
    unary_minus_type,
    unary_bang_type,
    type_size_bytes,
    type_alignment,
)


class SemanticAnalyzer:
    def __init__(self, file_name: str = "", source_text: str | None = None) -> None:
        self.file_name = file_name
        self._source_lines: list[str] | None = source_text.splitlines() if source_text is not None else None
        self._table = SymbolTable()
        self._structs: dict[str, Type] = {}
        self._errors: list[SemanticError] = []
        self._program: ProgramNode | None = None
        self._expr_types: dict[int, Type] = {}
        self._folded: dict[int, Any] = {}
        self._symbol_refs: dict[int, SymbolInfo] = {}
        self._call_refs: dict[int, SymbolInfo] = {}
        self._current_return: Type = VOID
        self._current_fn: str = ""
        self._local_stack_next: int = 0


    def _snapshot_initialized(self) -> dict[int, tuple[SymbolInfo, bool]]:
        snap: dict[int, tuple[SymbolInfo, bool]] = {}
        for _, symbols in self._table.dump_scopes():
            for sym in symbols.values():
                snap[id(sym)] = (sym, sym.initialized)
        return snap

    def _restore_initialized(self, snap: dict[int, tuple[SymbolInfo, bool]]) -> None:
        for sym, init in snap.values():
            sym.initialized = init

    def _merge_initialized_after_if(
        self,
        before: dict[int, tuple[SymbolInfo, bool]],
        then_state: dict[int, tuple[SymbolInfo, bool]],
        else_state: dict[int, tuple[SymbolInfo, bool]],
    ) -> None:
        for sid, (sym, before_init) in before.items():
            then_init = then_state.get(sid, (sym, before_init))[1]
            else_init = else_state.get(sid, (sym, before_init))[1]
            sym.initialized = before_init or (then_init and else_init)


    def analyze(self, ast: ProgramNode) -> None:
        self._program = ast
        self._table.reset()
        self._structs.clear()
        self._errors.clear()
        self._expr_types.clear()
        self._folded.clear()
        self._symbol_refs.clear()
        self._call_refs.clear()

        decls = list(ast.declarations)
        for d in decls:
            if isinstance(d, StructDecl):
                self._register_struct(d)
        for d in decls:
            if isinstance(d, FunctionDecl):
                self._register_function_signature(d)
        for d in decls:
            if isinstance(d, VarDeclStmt):
                self._analyze_global_var(d)
        for d in decls:
            if isinstance(d, FunctionDecl):
                self._analyze_function_body(d)
            elif not isinstance(d, (StructDecl, VarDeclStmt)):
                self._analyze_statement(d)

    def get_errors(self) -> list[SemanticError]:
        return list(self._errors)

    def get_symbol_table(self) -> SymbolTable:
        return self._table

    def get_decorated_ast(self) -> DecoratedAST:
        assert self._program is not None
        et = {k: str(v) for k, v in self._expr_types.items()}
        return DecoratedAST(
            self._program,
            et,
            dict(self._folded),
            symbol_refs=dict(self._symbol_refs),
            call_refs=dict(self._call_refs),
        )

    def _err(
        self,
        category: str,
        message: str,
        line: int,
        col: int,
        *,
        context: str = "",
        expected: str | None = None,
        found: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        ctx = context or (f"в функции «{self._current_fn}»" if self._current_fn else "")
        src_line: str | None = None
        if self._source_lines is not None and 1 <= line <= len(self._source_lines):
            src_line = self._source_lines[line - 1]
        self._errors.append(
            SemanticError(
                category=category,
                message=message,
                line=line,
                column=col,
                file_name=self.file_name,
                context=ctx,
                expected=expected,
                found=found,
                suggestion=suggestion,
                source_line=src_line,
            )
        )

    def _resolve_named_type(self, name: str, line: int, col: int) -> Type:
        match name:
            case "void":
                return VOID
            case "int":
                return INT
            case "float":
                return FLOAT
            case "bool":
                return BOOL
            case "string":
                return STRING
        if name in self._structs:
            return self._structs[name]
        self._err("type_mismatch", f"неизвестный тип «{name}»", line, col)
        return ERROR_T

    def _register_struct(self, node: StructDecl) -> None:
        if self._table.lookup_local(node.name) is not None or node.name in self._structs:
            self._err(
                "duplicate_declaration",
                f"повторное объявление «{node.name}»",
                node.line,
                node.column,
                context="глобальная область видимости",
            )
            return
        fields: dict[str, Type] = {}
        seen: set[str] = set()
        for f in node.fields:
            if f.name in seen:
                self._err(
                    "duplicate_declaration",
                    f"повторное поле структуры «{f.name}»",
                    f.line,
                    f.column,
                    context=f"структура «{node.name}»",
                )
                continue
            seen.add(f.name)
            ft = self._resolve_named_type(f.var_type, f.line, f.column)
            if ft.kind == TypeKind.VOID:
                self._err(
                    "type_mismatch",
                    f"поле «{f.name}» не может иметь тип void",
                    f.line,
                    f.column,
                )
                ft = ERROR_T
            fields[f.name] = ft
        st = struct_type(node.name, fields)
        self._structs[node.name] = st
        info = SymbolInfo(
            name=node.name,
            type=st,
            kind=SymbolKind.STRUCT,
            line=node.line,
            column=node.column,
            struct_fields=dict(fields),
            initialized=True,
        )
        if not self._table.insert(node.name, info):
            self._err("duplicate_declaration", f"повторное объявление «{node.name}»", node.line, node.column)

    def _register_function_signature(self, node: FunctionDecl) -> None:
        if self._table.lookup_local(node.name) is not None:
            self._err(
                "duplicate_declaration",
                f"повторное объявление «{node.name}»",
                node.line,
                node.column,
            )
            return
        params: list[Type] = []
        pnames: list[str] = []
        for p in node.params:
            t = self._resolve_named_type(p.param_type, p.line, p.column)
            if t.kind == TypeKind.VOID:
                self._err("type_mismatch", "параметр не может иметь тип void", p.line, p.column)
                t = ERROR_T
            params.append(t)
            pnames.append(p.name)
        ret = self._resolve_named_type(node.return_type, node.line, node.column)
        ft = function_type(tuple(params), ret)
        info = SymbolInfo(
            name=node.name,
            type=ft,
            kind=SymbolKind.FUNCTION,
            line=node.line,
            column=node.column,
            return_type=ret,
            param_types=tuple(params),
            param_names=tuple(pnames),
            initialized=True,
        )
        if not self._table.insert(node.name, info):
            self._err("duplicate_declaration", f"повторное объявление «{node.name}»", node.line, node.column)

    def _analyze_global_var(self, node: VarDeclStmt) -> None:
        t = self._resolve_named_type(node.var_type, node.line, node.column)
        if t.kind == TypeKind.VOID:
            self._err("type_mismatch", "переменная не может иметь тип void", node.line, node.column)
            t = ERROR_T
        if self._table.lookup_local(node.name) is not None:
            self._err("duplicate_declaration", f"повторное объявление «{node.name}»", node.line, node.column)
            return
        info = SymbolInfo(
            name=node.name,
            type=t,
            kind=SymbolKind.VARIABLE,
            line=node.line,
            column=node.column,

            
            
            initialized=False,
            stack_offset=None,
        )
        self._table.insert(node.name, info)
        if node.initializer:
            vt = self._check_expr(node.initializer)
            if not assignment_compatible(t, vt):
                self._err(
                    "type_mismatch",
                    f"несовместимость типов при инициализации «{node.name}»",
                    node.line,
                    node.column,
                    expected=str(t),
                    found=str(vt),
                )
            sym = self._table.lookup(node.name)
            if sym:
                sym.initialized = True

    def _analyze_function_body(self, node: FunctionDecl) -> None:
        self._current_fn = node.name
        self._current_return = self._resolve_named_type(node.return_type, node.line, node.column)
        self._local_stack_next = 0
        if self._table.scope_depth() >= 64:
            self._err("scope_error", "превышена максимальная глубина вложенности областей видимости", node.line, node.column)
        self._table.enter_scope("function")
        fn_sym = self._table.lookup(node.name)
        if fn_sym is None or fn_sym.kind != SymbolKind.FUNCTION:
            self._table.exit_scope()
            self._current_fn = ""
            return
        for i, p in enumerate(node.params):
            t = self._resolve_named_type(p.param_type, p.line, p.column)
            if t.kind == TypeKind.VOID:
                t = ERROR_T
            off = self._local_stack_next
            sz = type_size_bytes(t)
            al = type_alignment(t)
            pad = (al - (off % al)) % al
            off += pad
            info = SymbolInfo(
                name=p.name,
                type=t,
                kind=SymbolKind.PARAMETER,
                line=p.line,
                column=p.column,
                initialized=True,
                stack_offset=off,
                size_bytes=sz,
                alignment=al,
            )
            self._local_stack_next = off + sz
            if not self._table.insert(p.name, info):
                self._err("duplicate_declaration", f"повторное имя параметра «{p.name}»", p.line, p.column)
        if node.body:
            self._analyze_statement(node.body)
        self._table.exit_scope()
        self._current_fn = ""

    def _analyze_statement(self, node: ASTNode) -> None:
        match node:
            case BlockStmt(statements=stmts):
                self._table.enter_scope("block")
                for s in stmts:
                    self._analyze_statement(s)
                self._table.exit_scope()
            case VarDeclStmt():
                self._analyze_var_decl(node)
            case ExprStmt(expression=e):
                self._check_expr(e)
            case IfStmt(condition=c, then_branch=th, else_branch=el):
                ct = self._check_expr(c)
                if ct.kind != TypeKind.BOOL and ct.kind != TypeKind.ERROR:
                    self._err(
                        "invalid_condition_type",
                        "условие if должно иметь тип bool",
                        c.line,
                        c.column,
                        expected="bool",
                        found=str(ct),
                    )
                before = self._snapshot_initialized()
                self._analyze_statement(th)
                then_state = self._snapshot_initialized()
                self._restore_initialized(before)
                if el:
                    self._analyze_statement(el)
                    else_state = self._snapshot_initialized()
                else:
                    else_state = before
                self._merge_initialized_after_if(before, then_state, else_state)

            case WhileStmt(condition=c, body=b):
                ct = self._check_expr(c)
                if ct.kind != TypeKind.BOOL and ct.kind != TypeKind.ERROR:
                    self._err(
                        "invalid_condition_type",
                        "условие while должно иметь тип bool",
                        c.line,
                        c.column,
                        expected="bool",
                        found=str(ct),
                    )

                before = self._snapshot_initialized()
                self._analyze_statement(b)
                
                self._restore_initialized(before)

            case ForStmt(init=init, condition=cond, update=upd, body=body):
                if self._table.scope_depth() >= 64:
                    self._err("scope_error", "превышена максимальная глубина вложенности областей видимости", node.line, node.column)
                self._table.enter_scope("loop")
                loop_var: str | None = init.name if isinstance(init, VarDeclStmt) else None
                if isinstance(init, VarDeclStmt):
                    self._analyze_var_decl(init)
                elif init:
                    self._check_expr(init)
                if cond:
                    ctt = self._check_expr(cond)
                    if ctt.kind != TypeKind.BOOL and ctt.kind != TypeKind.ERROR:
                        self._err(
                            "invalid_condition_type",
                            "условие for должно иметь тип bool",
                            cond.line,
                            cond.column,
                            expected="bool",
                            found=str(ctt),
                        )
                if upd:
                    self._check_expr(upd)
                    if loop_var is not None:
                        ok = (
                            isinstance(upd, AssignmentExpr)

                            and isinstance(upd.target, IdentifierExpr)
                            and upd.target.name == loop_var
                        ) or (
                            isinstance(upd, IncDecExpr)
                            and isinstance(upd.target, IdentifierExpr)
                            and upd.target.name == loop_var

                        )
                        if not ok:
                            self._err(
                                "invalid_assignment_target",
                                f"переменная цикла «{loop_var}» должна обновляться в for-обновлении (используйте присваивание или ++/--)",
                                upd.line,
                                upd.column,
                            )
                self._analyze_statement(body)
                self._table.exit_scope()
            case ReturnStmt(value=val):
                if self._current_return.kind == TypeKind.VOID:
                    if val is not None:
                        self._err(
                            "invalid_return_type",
                            "функция void не должна возвращать значение",
                            val.line,
                            val.column,
                        )
                else:
                    if val is None:
                        self._err(
                            "invalid_return_type",
                            f"функция должна возвращать значение типа {self._current_return}",
                            node.line,
                            node.column,
                            expected=str(self._current_return),
                            found="(нет значения)",
                        )
                    else:
                        vt = self._check_expr(val)
                        if not assignment_compatible(self._current_return, vt):
                            self._err(
                                "invalid_return_type",
                                "тип возвращаемого значения не совпадает с типом функции",
                                val.line,
                                val.column,
                                expected=str(self._current_return),
                                found=str(vt),
                            )
            case EmptyStmt():
                pass
            case _:
                pass

    def _analyze_var_decl(self, node: VarDeclStmt) -> None:
        t = self._resolve_named_type(node.var_type, node.line, node.column)
        if t.kind == TypeKind.VOID:
            self._err("type_mismatch", "переменная не может иметь тип void", node.line, node.column)
            t = ERROR_T
        if self._table.lookup_local(node.name) is not None:
            self._err("duplicate_declaration", f"повторное объявление «{node.name}»", node.line, node.column)
            return
        off = self._local_stack_next
        sz = type_size_bytes(t)
        al = type_alignment(t)
        pad = (al - (off % al)) % al
        off += pad
        info = SymbolInfo(
            name=node.name,
            type=t,
            kind=SymbolKind.VARIABLE,
            line=node.line,
            column=node.column,
            initialized=False,
            stack_offset=off,
            size_bytes=sz,
            alignment=al,
        )
        self._local_stack_next = off + sz
        self._table.insert(node.name, info)
        if node.initializer:
            vt = self._check_expr(node.initializer)
            if not assignment_compatible(t, vt):
                self._err(
                    "type_mismatch",
                    f"несовместимость типов при инициализации «{node.name}»",
                    node.line,
                    node.column,
                    expected=str(t),
                    found=str(vt),
                )
            sym = self._table.lookup_local(node.name)
            if sym:
                sym.initialized = True


    def _resolve_lvalue_target(self, target: ASTNode) -> tuple[Type, SymbolInfo | None]:
        match target:
            case IdentifierExpr(name=name):
                sym = self._table.lookup(name)
                if sym is None:
                    self._err(
                        "undeclared_identifier",
                        f"необъявленный идентификатор «{name}»",
                        target.line,
                        target.column,
                    )
                    return ERROR_T, None
                if sym.kind != SymbolKind.VARIABLE:
                    self._err(
                        "invalid_assignment_target",
                        f"нельзя присвоить значение «{name}»",
                        target.line,
                        target.column,
                    )
                    return ERROR_T, None
                self._symbol_refs[id(target)] = sym
                return sym.type, sym
            case MemberAccessExpr(base=base, member=member):
                bt = self._check_expr(base)
                if bt.kind == TypeKind.ERROR:
                    return ERROR_T, None
                if bt.kind != TypeKind.STRUCT:
                    self._err(
                        "type_mismatch",
                        "доступ к полю возможен только у структуры",
                        target.line,
                        target.column,
                        expected="struct",
                        found=str(bt),
                    )
                    return ERROR_T, None
                fields = bt.fields or {}
                if member not in fields:
                    self._err(
                        "undeclared_identifier",
                        f"поле «{member}» не найдено в структуре «{bt.name}»",
                        target.line,
                        target.column,
                    )
                    return ERROR_T, None
                
                if id(base) in self._symbol_refs:
                    self._symbol_refs[id(target)] = self._symbol_refs[id(base)]
                return fields[member], None
        self._err(
            "invalid_assignment_target",
            "недопустимая цель присваивания",
            target.line,
            target.column,
        )
        return ERROR_T, None

    def _check_expr(self, node: ASTNode) -> Type:
        tid = id(node)
        if tid in self._expr_types:
            return self._expr_types[tid]
        t = self._infer_expr(node)
        self._expr_types[tid] = t
        return t

    def _infer_expr(self, node: ASTNode) -> Type:
        match node:
            case LiteralExpr(value=v, type_tag=tag):
                self._folded[id(node)] = v
                match tag:
                    case "int":
                        return INT
                    case "float":
                        return FLOAT
                    case "bool":
                        return BOOL
                    case "string":
                        return STRING
                    case "null":
                        return NULL_T
                return ERROR_T
            case IdentifierExpr(name=name):
                sym = self._table.lookup(name)
                if sym is None:
                    self._err(
                        "undeclared_identifier",
                        f"необъявленный идентификатор «{name}»",
                        node.line,
                        node.column,
                    )
                    return ERROR_T
                self._symbol_refs[id(node)] = sym
                if sym.kind == SymbolKind.VARIABLE and not sym.initialized:
                    self._err(
                        "use_before_declaration",
                        f"переменная «{name}» использована до инициализации",
                        node.line,
                        node.column,
                        suggestion="сначала присвойте значение",
                    )
                if sym.kind == SymbolKind.FUNCTION:
                    self._err(
                        "type_mismatch",
                        f"«{name}» — функция; возможно, имелся в виду вызов?",
                        node.line,
                        node.column,
                    )
                    return ERROR_T
                return sym.type
            case MemberAccessExpr(base=base, member=member):
                bt = self._check_expr(base)
                if bt.kind == TypeKind.ERROR:
                    return ERROR_T
                if bt.kind != TypeKind.STRUCT:
                    self._err(
                        "type_mismatch",
                        "доступ к полю возможен только у структуры",
                        node.line,
                        node.column,
                        expected="struct",
                        found=str(bt),
                    )
                    return ERROR_T
                fields = bt.fields or {}
                if member not in fields:
                    self._err(
                        "undeclared_identifier",
                        f"поле «{member}» не найдено в структуре «{bt.name}»",
                        node.line,
                        node.column,
                    )
                    return ERROR_T
                if id(base) in self._symbol_refs:
                    self._symbol_refs[id(node)] = self._symbol_refs[id(base)]
                return fields[member]
            case UnaryExpr(operator=op, operand=child):
                ct = self._check_expr(child)
                if op == "-":
                    ut = unary_minus_type(ct)
                    if ut is None:
                        self._err(
                            "type_mismatch",
                            f"унарный '-' к операнду типа {ct}",
                            node.line,
                            node.column,
                            expected="int или float",
                            found=str(ct),
                        )
                        return ERROR_T
                    if id(child) in self._folded:
                        v = self._folded[id(child)]
                        try:
                            self._folded[id(node)] = -v
                        except Exception:
                            pass

                    return ut
                if op == "!":
                    ut = unary_bang_type(ct)
                    if ut is None:
                        self._err(
                            "type_mismatch",
                            f"унарный '!' к операнду типа {ct}",
                            node.line,
                            node.column,
                            expected="bool",
                            found=str(ct),
                        )
                        return ERROR_T

                    if id(child) in self._folded and ut.kind == TypeKind.BOOL:
                        v = self._folded[id(child)]
                        if isinstance(v, bool):
                            self._folded[id(node)] = (not v)


                    return ut
                return ERROR_T
            case BinaryExpr(left=left, operator=op, right=right):
                lt = self._check_expr(left)
                rt = self._check_expr(right)
                if op in ("&&", "||"):
                    if lt.kind != TypeKind.BOOL or rt.kind != TypeKind.BOOL:
                        self._err(
                            "type_mismatch",
                            f"оператор «{op}» требует операнды типа bool",
                            node.line,
                            node.column,
                            expected="bool, bool",
                            found=f"{lt}, {rt}",
                        )
                        return ERROR_T

                    if id(left) in self._folded and id(right) in self._folded:
                        lv = self._folded[id(left)]
                        rv = self._folded[id(right)]
                        if isinstance(lv, bool) and isinstance(rv, bool):
                            self._folded[id(node)] = (lv and rv) if op == "&&" else (lv or rv)

                    return BOOL
                if op in ("==", "!="):
                    if binary_compare_result(lt, rt) is None:
                        self._err(
                            "type_mismatch",
                            f"недопустимые операнды для «{op}»",
                            node.line,
                            node.column,
                            found=f"{lt}, {rt}",
                        )
                        return ERROR_T

                    if id(left) in self._folded and id(right) in self._folded:
                        lv = self._folded[id(left)]
                        rv = self._folded[id(right)]
                        try:
                            self._folded[id(node)] = (lv == rv) if op == "==" else (lv != rv)
                        except Exception:
                            pass
                    return BOOL
                if op in ("<", "<=", ">", ">="):
                    if not is_numeric(lt) or not is_numeric(rt):
                        self._err(
                            "type_mismatch",
                            f"оператор «{op}» требует числовые операнды",
                            node.line,
                            node.column,
                            found=f"{lt}, {rt}",
                        )
                        return ERROR_T

                    if id(left) in self._folded and id(right) in self._folded:
                        lv = self._folded[id(left)]
                        rv = self._folded[id(right)]
                        if isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
                            try:
                                if op == "<":
                                    self._folded[id(node)] = lv < rv
                                elif op == "<=":
                                    self._folded[id(node)] = lv <= rv
                                elif op == ">":
                                    self._folded[id(node)] = lv > rv
                                else:
                                    self._folded[id(node)] = lv >= rv
                            except Exception:
                                pass

                    return BOOL
                if op == "%":
                    if lt.kind != TypeKind.INT or rt.kind != TypeKind.INT:
                        self._err(
                            "type_mismatch",
                            "оператор «%» требует операнды типа int",
                            node.line,
                            node.column,
                            found=f"{lt}, {rt}",
                        )
                        return ERROR_T

                    if id(left) in self._folded and id(right) in self._folded:
                        lv = self._folded[id(left)]
                        rv = self._folded[id(right)]
                        if isinstance(lv, int) and isinstance(rv, int):
                            if rv != 0:
                                self._folded[id(node)] = lv % rv

                    return INT
                if op in ("+", "-", "*", "/"):
                    res = binary_arithmetic_result(lt, rt)
                    if res is None:
                        self._err(
                            "type_mismatch",
                            f"недопустимые операнды для «{op}»",
                            node.line,
                            node.column,
                            found=f"{lt}, {rt}",
                        )
                        return ERROR_T

                    if id(left) in self._folded and id(right) in self._folded:
                        lv = self._folded[id(left)]
                        rv = self._folded[id(right)]
                        if isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
                            try:
                                if op == "+":
                                    self._folded[id(node)] = lv + rv
                                elif op == "-":
                                    self._folded[id(node)] = lv - rv
                                elif op == "*":
                                    self._folded[id(node)] = lv * rv
                                elif op == "/":
                                    if rv == 0:
                                        raise ZeroDivisionError()
                                    if res.kind == TypeKind.INT:
                                        
                                        self._folded[id(node)] = int(lv / rv)
                                    else:
                                        self._folded[id(node)] = lv / rv
                            except Exception:
                                pass
                    return res
                return ERROR_T
            case CallExpr(callee=name, arguments=args):
                sym = self._table.lookup(name)
                if sym is None:
                    self._err(
                        "undeclared_identifier",
                        f"необъявленная функция «{name}»",
                        node.line,
                        node.column,
                    )
                    return ERROR_T
                self._call_refs[id(node)] = sym
                if sym.kind != SymbolKind.FUNCTION:
                    self._err(
                        "type_mismatch",
                        f"«{name}» не является функцией",
                        node.line,
                        node.column,
                    )
                    return ERROR_T
                assert sym.param_types is not None and sym.return_type is not None
                if len(args) != len(sym.param_types):
                    self._err(
                        "argument_count_mismatch",
                        f"вызов «{name}»: неверное число аргументов",
                        node.line,
                        node.column,
                        expected=f"{len(sym.param_types)} аргументов",
                        found=f"{len(args)} аргументов",
                        suggestion=f"сигнатура: {sym.type}",
                    )
                else:
                    for i, (arg, pt) in enumerate(zip(args, sym.param_types)):
                        at = self._check_expr(arg)
                        if not assignment_compatible(pt, at):
                            self._err(
                                "argument_type_mismatch",
                                f"аргумент {i + 1} вызова «{name}»: неверный тип",
                                arg.line,
                                arg.column,
                                expected=str(pt),
                                found=str(at),
                            )
                return sym.return_type
            case AssignmentExpr(target=target, operator=op, value=value):

                lt, sym = self._resolve_lvalue_target(target)
                vt = self._check_expr(value)
                if lt.kind == TypeKind.ERROR:
                    self._expr_types[id(node)] = ERROR_T
                    return ERROR_T
                if sym is not None:
                    self._symbol_refs[id(node)] = sym
                if op == "=":
                    if not assignment_compatible(lt, vt):
                        self._err(
                            "type_mismatch",
                            "несовместимость типов при присваивании",
                            node.line,
                            node.column,
                            expected=str(lt),
                            found=str(vt),
                        )
                else:
                    if not is_numeric(lt) or not is_numeric(vt):
                sym = self._table.lookup(target)
                if sym is None:
                    self._err(
                        "undeclared_identifier",
                        f"необъявленный идентификатор «{target}»",
                        node.line,
                        node.column,
                    )
                    vt = self._check_expr(value)
                    self._expr_types[id(node)] = vt
                    return vt
                if sym.kind != SymbolKind.VARIABLE:
                    self._err(
                        "invalid_assignment_target",
                        f"нельзя присвоить значение «{target}»",
                        node.line,
                        node.column,
                    )
                    vt = self._check_expr(value)
                    self._expr_types[id(node)] = ERROR_T
                    return ERROR_T
                self._symbol_refs[id(node)] = sym
                vt = self._check_expr(value)
                if op == "=":
                    if not assignment_compatible(sym.type, vt):
                        self._err(
                            "type_mismatch",
                            f"несовместимость типов при присваивании в «{target}»",
                            node.line,
                            node.column,
                            expected=str(sym.type),
                            found=str(vt),
                        )
                else:
                    if not is_numeric(sym.type) or not is_numeric(vt):

                        self._err(
                            "type_mismatch",
                            f"оператор «{op}» требует числовые типы",
                            node.line,
                            node.column,
                            expected="числовой тип",

                            found=f"{lt}, {vt}",
                        )
                    elif lt.kind == TypeKind.INT and vt.kind == TypeKind.FLOAT:

                        self._err(
                            "type_mismatch",
                            "нельзя присвоить float переменной int составным присваиванием (нет неявного сужения)",
                            node.line,
                            node.column,
                        )

                if sym is not None:
                    sym.initialized = True
                self._expr_types[id(node)] = lt
                return lt
            case IncDecExpr(target=target, operator=op):
                lt, sym = self._resolve_lvalue_target(target)
                if lt.kind == TypeKind.ERROR:
                    return ERROR_T
                if sym is not None:
                    self._symbol_refs[id(node)] = sym
                if not is_numeric(lt):

                    self._err(
                        "type_mismatch",
                        f"оператор «{op}» требует числовую переменную",
                        node.line,
                        node.column,

                        found=str(lt),
                    )
                    return ERROR_T
                if sym is not None:
                    sym.initialized = True
                self._expr_types[id(node)] = lt
                return lt

        return ERROR_T
