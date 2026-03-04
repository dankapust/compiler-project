from __future__ import annotations

from parser.ast import (
    ASTVisitor, ASTNode, ProgramNode,
    LiteralExpr, IdentifierExpr, BinaryExpr, UnaryExpr, CallExpr, AssignmentExpr,
    BlockStmt, ExprStmt, IfStmt, WhileStmt, ForStmt, ReturnStmt, VarDeclStmt, EmptyStmt,
    Param, FunctionDecl, StructDecl,
)


def pretty_print(node: ASTNode) -> str:
    printer = _PrettyPrinter()
    node.accept(printer)
    return "\n".join(printer.lines) + "\n"


class _PrettyPrinter(ASTVisitor):
    def __init__(self) -> None:
        self.lines: list[str] = []
        self._indent = 0

    def _emit(self, text: str) -> None:
        self.lines.append("  " * self._indent + text)

    def _loc(self, node: ASTNode) -> str:
        return f"[{node.line}:{node.column}]"

    def visit_program(self, node: ProgramNode) -> None:
        self._emit(f"Program {self._loc(node)}:")
        self._indent += 1
        for d in node.declarations:
            d.accept(self)
        self._indent -= 1

    def visit_function_decl(self, node: FunctionDecl) -> None:
        self._emit(f"FunctionDecl: {node.name} -> {node.return_type} {self._loc(node)}")
        self._indent += 1
        params_str = ", ".join(f"{p.param_type} {p.name}" for p in node.params)
        self._emit(f"Parameters: [{params_str}]")
        if node.body is not None:
            self._emit("Body:")
            self._indent += 1
            node.body.accept(self)
            self._indent -= 1
        self._indent -= 1

    def visit_struct_decl(self, node: StructDecl) -> None:
        self._emit(f"StructDecl: {node.name} {self._loc(node)}")
        self._indent += 1
        for f in node.fields:
            f.accept(self)
        self._indent -= 1

    def visit_var_decl(self, node: VarDeclStmt) -> None:
        init_str = ""
        if node.initializer is not None:
            init_str = f" = {_expr_str(node.initializer)}"
        self._emit(f"VarDeclStmt: {node.var_type} {node.name}{init_str} {self._loc(node)}")

    def visit_block(self, node: BlockStmt) -> None:
        self._emit(f"Block {self._loc(node)}:")
        self._indent += 1
        for s in node.statements:
            s.accept(self)
        self._indent -= 1

    def visit_expr_stmt(self, node: ExprStmt) -> None:
        self._emit(f"ExprStmt: {_expr_str(node.expression)} {self._loc(node)}")

    def visit_if(self, node: IfStmt) -> None:
        self._emit(f"IfStmt {self._loc(node)}:")
        self._indent += 1
        self._emit(f"Condition: {_expr_str(node.condition)}")
        self._emit("Then:")
        self._indent += 1
        node.then_branch.accept(self)
        self._indent -= 1
        if node.else_branch is not None:
            self._emit("Else:")
            self._indent += 1
            node.else_branch.accept(self)
            self._indent -= 1
        self._indent -= 1

    def visit_while(self, node: WhileStmt) -> None:
        self._emit(f"WhileStmt {self._loc(node)}:")
        self._indent += 1
        self._emit(f"Condition: {_expr_str(node.condition)}")
        self._emit("Body:")
        self._indent += 1
        node.body.accept(self)
        self._indent -= 1
        self._indent -= 1

    def visit_for(self, node: ForStmt) -> None:
        self._emit(f"ForStmt {self._loc(node)}:")
        self._indent += 1
        if node.init is not None:
            if isinstance(node.init, VarDeclStmt):
                init_str = f"{node.init.var_type} {node.init.name}"
                if node.init.initializer:
                    init_str += f" = {_expr_str(node.init.initializer)}"
                self._emit(f"Init: {init_str}")
            else:
                self._emit(f"Init: {_expr_str(node.init)}")
        else:
            self._emit("Init: <none>")
        self._emit(f"Condition: {_expr_str(node.condition) if node.condition else '<none>'}")
        self._emit(f"Update: {_expr_str(node.update) if node.update else '<none>'}")
        self._emit("Body:")
        self._indent += 1
        node.body.accept(self)
        self._indent -= 1
        self._indent -= 1

    def visit_return(self, node: ReturnStmt) -> None:
        val = _expr_str(node.value) if node.value else "<none>"
        self._emit(f"ReturnStmt {self._loc(node)}: {val}")

    def visit_empty_stmt(self, node: EmptyStmt) -> None:
        self._emit(f"EmptyStmt {self._loc(node)}")

    def visit_param(self, node: Param) -> None:
        self._emit(f"Param: {node.param_type} {node.name} {self._loc(node)}")

    def visit_literal(self, node: LiteralExpr) -> None:
        self._emit(f"Literal: {_literal_repr(node)}")

    def visit_identifier(self, node: IdentifierExpr) -> None:
        self._emit(f"Identifier: {node.name}")

    def visit_binary(self, node: BinaryExpr) -> None:
        self._emit(f"Binary: {_expr_str(node)}")

    def visit_unary(self, node: UnaryExpr) -> None:
        self._emit(f"Unary: {_expr_str(node)}")

    def visit_call(self, node: CallExpr) -> None:
        args = ", ".join(_expr_str(a) for a in node.arguments)
        self._emit(f"Call: {node.callee}({args})")

    def visit_assignment(self, node: AssignmentExpr) -> None:
        self._emit(f"Assignment: {node.target} {node.operator} {_expr_str(node.value)}")


def _literal_repr(node: LiteralExpr) -> str:
    match node.type_tag:
        case "int":
            return str(node.value)
        case "float":
            return str(node.value)
        case "string":
            return f'"{node.value}"'
        case "bool":
            return "true" if node.value else "false"
        case "null":
            return "null"
    return repr(node.value)


def _expr_str(node: ASTNode) -> str:
    match node:
        case LiteralExpr():
            return _literal_repr(node)
        case IdentifierExpr():
            return node.name
        case BinaryExpr():
            return f"({_expr_str(node.left)} {node.operator} {_expr_str(node.right)})"
        case UnaryExpr():
            return f"({node.operator}{_expr_str(node.operand)})"
        case CallExpr():
            args = ", ".join(_expr_str(a) for a in node.arguments)
            return f"{node.callee}({args})"
        case AssignmentExpr():
            return f"({node.target} {node.operator} {_expr_str(node.value)})"
    return repr(node)
