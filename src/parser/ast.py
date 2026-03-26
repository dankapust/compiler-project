from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ASTNode:
    line: int
    column: int

    def accept(self, visitor: ASTVisitor) -> Any:
        raise NotImplementedError


@dataclass(frozen=True)
class ProgramNode(ASTNode):
    declarations: tuple[ASTNode, ...] = ()

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_program(self)


@dataclass(frozen=True)
class LiteralExpr(ASTNode):
    value: Any
    type_tag: str

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_literal(self)


@dataclass(frozen=True)
class IdentifierExpr(ASTNode):
    name: str

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_identifier(self)


@dataclass(frozen=True)
class MemberAccessExpr(ASTNode):
    base: ASTNode
    member: str

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_member_access(self)


@dataclass(frozen=True)
class BinaryExpr(ASTNode):
    left: ASTNode
    operator: str
    right: ASTNode

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_binary(self)


@dataclass(frozen=True)
class UnaryExpr(ASTNode):
    operator: str
    operand: ASTNode

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_unary(self)


@dataclass(frozen=True)
class CallExpr(ASTNode):
    callee: str
    arguments: tuple[ASTNode, ...] = ()

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_call(self)


@dataclass(frozen=True)
class AssignmentExpr(ASTNode):
    target: ASTNode
    operator: str
    value: ASTNode

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_assignment(self)


@dataclass(frozen=True)
class IncDecExpr(ASTNode):
    target: ASTNode
    operator: str
    prefix: bool

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_incdec(self)


@dataclass(frozen=True)
class BlockStmt(ASTNode):
    statements: tuple[ASTNode, ...] = ()

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_block(self)


@dataclass(frozen=True)
class ExprStmt(ASTNode):
    expression: ASTNode

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_expr_stmt(self)


@dataclass(frozen=True)
class IfStmt(ASTNode):
    condition: ASTNode
    then_branch: ASTNode
    else_branch: ASTNode | None = None

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_if(self)


@dataclass(frozen=True)
class WhileStmt(ASTNode):
    condition: ASTNode
    body: ASTNode

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_while(self)


@dataclass(frozen=True)
class ForStmt(ASTNode):
    init: ASTNode | None
    condition: ASTNode | None
    update: ASTNode | None
    body: ASTNode

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_for(self)


@dataclass(frozen=True)
class ReturnStmt(ASTNode):
    value: ASTNode | None = None

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_return(self)


@dataclass(frozen=True)
class VarDeclStmt(ASTNode):
    var_type: str
    name: str
    initializer: ASTNode | None = None

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_var_decl(self)


@dataclass(frozen=True)
class EmptyStmt(ASTNode):
    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_empty_stmt(self)


@dataclass(frozen=True)
class Param(ASTNode):
    param_type: str
    name: str

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_param(self)


@dataclass(frozen=True)
class FunctionDecl(ASTNode):
    name: str
    params: tuple[Param, ...] = ()
    return_type: str = "void"
    body: BlockStmt | None = None

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_function_decl(self)


@dataclass(frozen=True)
class StructDecl(ASTNode):
    name: str
    fields: tuple[VarDeclStmt, ...] = ()

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_struct_decl(self)


class ASTVisitor:
    def visit_program(self, node: ProgramNode) -> Any: ...
    def visit_literal(self, node: LiteralExpr) -> Any: ...
    def visit_identifier(self, node: IdentifierExpr) -> Any: ...
    def visit_member_access(self, node: MemberAccessExpr) -> Any: ...
    def visit_binary(self, node: BinaryExpr) -> Any: ...
    def visit_unary(self, node: UnaryExpr) -> Any: ...
    def visit_call(self, node: CallExpr) -> Any: ...
    def visit_assignment(self, node: AssignmentExpr) -> Any: ...
    def visit_incdec(self, node: IncDecExpr) -> Any: ...
    def visit_block(self, node: BlockStmt) -> Any: ...
    def visit_expr_stmt(self, node: ExprStmt) -> Any: ...
    def visit_if(self, node: IfStmt) -> Any: ...
    def visit_while(self, node: WhileStmt) -> Any: ...
    def visit_for(self, node: ForStmt) -> Any: ...
    def visit_return(self, node: ReturnStmt) -> Any: ...
    def visit_var_decl(self, node: VarDeclStmt) -> Any: ...
    def visit_empty_stmt(self, node: EmptyStmt) -> Any: ...
    def visit_param(self, node: Param) -> Any: ...
    def visit_function_decl(self, node: FunctionDecl) -> Any: ...
    def visit_struct_decl(self, node: StructDecl) -> Any: ...
