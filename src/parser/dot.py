from __future__ import annotations

from parser.ast import (
    ASTVisitor, ASTNode, ProgramNode,

    LiteralExpr, IdentifierExpr, BinaryExpr, UnaryExpr, CallExpr, AssignmentExpr, IncDecExpr,
    LiteralExpr, IdentifierExpr, BinaryExpr, UnaryExpr, CallExpr, AssignmentExpr,
    BlockStmt, ExprStmt, IfStmt, WhileStmt, ForStmt, ReturnStmt, VarDeclStmt, EmptyStmt,
    Param, FunctionDecl, StructDecl,
)


def to_dot(node: ASTNode) -> str:
    gen = _DotGenerator()
    node.accept(gen)
    lines = ["digraph AST {", '  node [shape=box, fontname="monospace"];']
    lines.extend(f"  {line}" for line in gen.nodes)
    lines.extend(f"  {line}" for line in gen.edges)
    lines.append("}")
    return "\n".join(lines) + "\n"


_DECL_COLOR = "#ADD8E6"
_STMT_COLOR = "#FFFFCC"
_EXPR_COLOR = "#90EE90"
_OTHER_COLOR = "#D3D3D3"


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class _DotGenerator(ASTVisitor):
    def __init__(self) -> None:
        self.nodes: list[str] = []
        self.edges: list[str] = []
        self._counter = 0

    def _new_id(self) -> str:
        self._counter += 1
        return f"n{self._counter}"

    def _add_node(self, nid: str, label: str, color: str) -> None:
        self.nodes.append(f'{nid} [label="{_esc(label)}", style=filled, fillcolor="{color}"];')

    def _add_edge(self, parent: str, child: str, label: str = "") -> None:
        if label:
            self.edges.append(f'{parent} -> {child} [label="{_esc(label)}"];')
        else:
            self.edges.append(f"{parent} -> {child};")

    def visit_program(self, node: ProgramNode) -> str:
        nid = self._new_id()
        self._add_node(nid, "Program", _OTHER_COLOR)
        for d in node.declarations:
            cid = d.accept(self)
            self._add_edge(nid, cid)
        return nid

    def visit_function_decl(self, node: FunctionDecl) -> str:
        nid = self._new_id()
        self._add_node(nid, f"FunctionDecl\\n{node.name} -> {node.return_type}", _DECL_COLOR)
        if node.params:
            pid = self._new_id()
            params_str = ", ".join(f"{p.param_type} {p.name}" for p in node.params)
            self._add_node(pid, f"Params: [{params_str}]", _DECL_COLOR)
            self._add_edge(nid, pid, "params")
        if node.body:
            bid = node.body.accept(self)
            self._add_edge(nid, bid, "body")
        return nid

    def visit_struct_decl(self, node: StructDecl) -> str:
        nid = self._new_id()
        self._add_node(nid, f"StructDecl\\n{node.name}", _DECL_COLOR)
        for f in node.fields:
            fid = f.accept(self)
            self._add_edge(nid, fid)
        return nid

    def visit_var_decl(self, node: VarDeclStmt) -> str:
        nid = self._new_id()
        self._add_node(nid, f"VarDecl\\n{node.var_type} {node.name}", _STMT_COLOR)
        if node.initializer:
            iid = node.initializer.accept(self)
            self._add_edge(nid, iid, "init")
        return nid

    def visit_block(self, node: BlockStmt) -> str:
        nid = self._new_id()
        self._add_node(nid, "Block", _STMT_COLOR)
        for s in node.statements:
            sid = s.accept(self)
            self._add_edge(nid, sid)
        return nid

    def visit_expr_stmt(self, node: ExprStmt) -> str:
        nid = self._new_id()
        self._add_node(nid, "ExprStmt", _STMT_COLOR)
        eid = node.expression.accept(self)
        self._add_edge(nid, eid)
        return nid

    def visit_if(self, node: IfStmt) -> str:
        nid = self._new_id()
        self._add_node(nid, "IfStmt", _STMT_COLOR)
        cid = node.condition.accept(self)
        self._add_edge(nid, cid, "cond")
        tid = node.then_branch.accept(self)
        self._add_edge(nid, tid, "then")
        if node.else_branch:
            eid = node.else_branch.accept(self)
            self._add_edge(nid, eid, "else")
        return nid

    def visit_while(self, node: WhileStmt) -> str:
        nid = self._new_id()
        self._add_node(nid, "WhileStmt", _STMT_COLOR)
        cid = node.condition.accept(self)
        self._add_edge(nid, cid, "cond")
        bid = node.body.accept(self)
        self._add_edge(nid, bid, "body")
        return nid

    def visit_for(self, node: ForStmt) -> str:
        nid = self._new_id()
        self._add_node(nid, "ForStmt", _STMT_COLOR)
        if node.init:
            iid = node.init.accept(self)
            self._add_edge(nid, iid, "init")
        if node.condition:
            cid = node.condition.accept(self)
            self._add_edge(nid, cid, "cond")
        if node.update:
            uid = node.update.accept(self)
            self._add_edge(nid, uid, "update")
        bid = node.body.accept(self)
        self._add_edge(nid, bid, "body")
        return nid

    def visit_return(self, node: ReturnStmt) -> str:
        nid = self._new_id()
        self._add_node(nid, "ReturnStmt", _STMT_COLOR)
        if node.value:
            vid = node.value.accept(self)
            self._add_edge(nid, vid)
        return nid

    def visit_empty_stmt(self, node: EmptyStmt) -> str:
        nid = self._new_id()
        self._add_node(nid, "EmptyStmt", _STMT_COLOR)
        return nid

    def visit_param(self, node: Param) -> str:
        nid = self._new_id()
        self._add_node(nid, f"Param\\n{node.param_type} {node.name}", _DECL_COLOR)
        return nid

    def visit_literal(self, node: LiteralExpr) -> str:
        nid = self._new_id()
        match node.type_tag:
            case "string":
                label = f'Literal\\n"{node.value}"'
            case "bool":
                label = f"Literal\\n{'true' if node.value else 'false'}"
            case "null":
                label = "Literal\\nnull"
            case _:
                label = f"Literal\\n{node.value}"
        self._add_node(nid, label, _EXPR_COLOR)
        return nid

    def visit_identifier(self, node: IdentifierExpr) -> str:
        nid = self._new_id()
        self._add_node(nid, f"Identifier\\n{node.name}", _EXPR_COLOR)
        return nid

    def visit_binary(self, node: BinaryExpr) -> str:
        nid = self._new_id()
        self._add_node(nid, f"Binary\\n{node.operator}", _EXPR_COLOR)
        lid = node.left.accept(self)
        self._add_edge(nid, lid, "left")
        rid = node.right.accept(self)
        self._add_edge(nid, rid, "right")
        return nid

    def visit_unary(self, node: UnaryExpr) -> str:
        nid = self._new_id()
        self._add_node(nid, f"Unary\\n{node.operator}", _EXPR_COLOR)
        oid = node.operand.accept(self)
        self._add_edge(nid, oid)
        return nid

    def visit_call(self, node: CallExpr) -> str:
        nid = self._new_id()
        self._add_node(nid, f"Call\\n{node.callee}", _EXPR_COLOR)
        for a in node.arguments:
            aid = a.accept(self)
            self._add_edge(nid, aid)
        return nid

    def visit_assignment(self, node: AssignmentExpr) -> str:
        nid = self._new_id()
        self._add_node(nid, f"Assignment\\n{node.target} {node.operator}", _EXPR_COLOR)
        vid = node.value.accept(self)
        self._add_edge(nid, vid)
        return nid


    def visit_incdec(self, node: IncDecExpr) -> str:
        nid = self._new_id()
        form = f"{node.operator}{node.target}" if node.prefix else f"{node.target}{node.operator}"
        self._add_node(nid, f"IncDec\\n{form}", _EXPR_COLOR)
        return nid
