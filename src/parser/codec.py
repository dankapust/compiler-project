from __future__ import annotations

from typing import Any

from parser.ast import (
    ASTNode, ProgramNode,
    LiteralExpr, IdentifierExpr, BinaryExpr, UnaryExpr, CallExpr, AssignmentExpr,
    BlockStmt, ExprStmt, IfStmt, WhileStmt, ForStmt, ReturnStmt, VarDeclStmt, EmptyStmt,
    Param, FunctionDecl, StructDecl,
)


def node_to_jsonable(node: ASTNode) -> dict[str, Any]:
    match node:
        case ProgramNode():
            return {
                "node": "Program",
                "line": node.line, "column": node.column,
                "declarations": [node_to_jsonable(d) for d in node.declarations],
            }
        case FunctionDecl():
            return {
                "node": "FunctionDecl",
                "line": node.line, "column": node.column,
                "name": node.name,
                "params": [node_to_jsonable(p) for p in node.params],
                "return_type": node.return_type,
                "body": node_to_jsonable(node.body) if node.body else None,
            }
        case StructDecl():
            return {
                "node": "StructDecl",
                "line": node.line, "column": node.column,
                "name": node.name,
                "fields": [node_to_jsonable(f) for f in node.fields],
            }
        case Param():
            return {
                "node": "Param",
                "line": node.line, "column": node.column,
                "param_type": node.param_type,
                "name": node.name,
            }
        case VarDeclStmt():
            return {
                "node": "VarDeclStmt",
                "line": node.line, "column": node.column,
                "var_type": node.var_type,
                "name": node.name,
                "initializer": node_to_jsonable(node.initializer) if node.initializer else None,
            }
        case BlockStmt():
            return {
                "node": "BlockStmt",
                "line": node.line, "column": node.column,
                "statements": [node_to_jsonable(s) for s in node.statements],
            }
        case ExprStmt():
            return {
                "node": "ExprStmt",
                "line": node.line, "column": node.column,
                "expression": node_to_jsonable(node.expression),
            }
        case IfStmt():
            return {
                "node": "IfStmt",
                "line": node.line, "column": node.column,
                "condition": node_to_jsonable(node.condition),
                "then_branch": node_to_jsonable(node.then_branch),
                "else_branch": node_to_jsonable(node.else_branch) if node.else_branch else None,
            }
        case WhileStmt():
            return {
                "node": "WhileStmt",
                "line": node.line, "column": node.column,
                "condition": node_to_jsonable(node.condition),
                "body": node_to_jsonable(node.body),
            }
        case ForStmt():
            return {
                "node": "ForStmt",
                "line": node.line, "column": node.column,
                "init": node_to_jsonable(node.init) if node.init else None,
                "condition": node_to_jsonable(node.condition) if node.condition else None,
                "update": node_to_jsonable(node.update) if node.update else None,
                "body": node_to_jsonable(node.body),
            }
        case ReturnStmt():
            return {
                "node": "ReturnStmt",
                "line": node.line, "column": node.column,
                "value": node_to_jsonable(node.value) if node.value else None,
            }
        case EmptyStmt():
            return {
                "node": "EmptyStmt",
                "line": node.line, "column": node.column,
            }
        case LiteralExpr():
            return {
                "node": "LiteralExpr",
                "line": node.line, "column": node.column,
                "value": node.value,
                "type_tag": node.type_tag,
            }
        case IdentifierExpr():
            return {
                "node": "IdentifierExpr",
                "line": node.line, "column": node.column,
                "name": node.name,
            }
        case BinaryExpr():
            return {
                "node": "BinaryExpr",
                "line": node.line, "column": node.column,
                "operator": node.operator,
                "left": node_to_jsonable(node.left),
                "right": node_to_jsonable(node.right),
            }
        case UnaryExpr():
            return {
                "node": "UnaryExpr",
                "line": node.line, "column": node.column,
                "operator": node.operator,
                "operand": node_to_jsonable(node.operand),
            }
        case CallExpr():
            return {
                "node": "CallExpr",
                "line": node.line, "column": node.column,
                "callee": node.callee,
                "arguments": [node_to_jsonable(a) for a in node.arguments],
            }
        case AssignmentExpr():
            return {
                "node": "AssignmentExpr",
                "line": node.line, "column": node.column,
                "target": node.target,
                "operator": node.operator,
                "value": node_to_jsonable(node.value),
            }
    raise ValueError(f"unknown node type: {type(node).__name__}")


def from_jsonable(data: dict[str, Any]) -> ASTNode:
    line = data["line"]
    col = data["column"]
    match data["node"]:
        case "Program":
            return ProgramNode(line, col, tuple(from_jsonable(d) for d in data["declarations"]))
        case "FunctionDecl":
            body = from_jsonable(data["body"]) if data["body"] else None
            return FunctionDecl(
                line, col, data["name"],
                tuple(from_jsonable(p) for p in data["params"]),
                data["return_type"], body,
            )
        case "StructDecl":
            return StructDecl(line, col, data["name"], tuple(from_jsonable(f) for f in data["fields"]))
        case "Param":
            return Param(line, col, data["param_type"], data["name"])
        case "VarDeclStmt":
            init = from_jsonable(data["initializer"]) if data["initializer"] else None
            return VarDeclStmt(line, col, data["var_type"], data["name"], init)
        case "BlockStmt":
            return BlockStmt(line, col, tuple(from_jsonable(s) for s in data["statements"]))
        case "ExprStmt":
            return ExprStmt(line, col, from_jsonable(data["expression"]))
        case "IfStmt":
            else_br = from_jsonable(data["else_branch"]) if data["else_branch"] else None
            return IfStmt(line, col, from_jsonable(data["condition"]), from_jsonable(data["then_branch"]), else_br)
        case "WhileStmt":
            return WhileStmt(line, col, from_jsonable(data["condition"]), from_jsonable(data["body"]))
        case "ForStmt":
            init = from_jsonable(data["init"]) if data["init"] else None
            cond = from_jsonable(data["condition"]) if data["condition"] else None
            upd = from_jsonable(data["update"]) if data["update"] else None
            return ForStmt(line, col, init, cond, upd, from_jsonable(data["body"]))
        case "ReturnStmt":
            val = from_jsonable(data["value"]) if data["value"] else None
            return ReturnStmt(line, col, val)
        case "EmptyStmt":
            return EmptyStmt(line, col)
        case "LiteralExpr":
            return LiteralExpr(line, col, data["value"], data["type_tag"])
        case "IdentifierExpr":
            return IdentifierExpr(line, col, data["name"])
        case "BinaryExpr":
            return BinaryExpr(line, col, from_jsonable(data["left"]), data["operator"], from_jsonable(data["right"]))
        case "UnaryExpr":
            return UnaryExpr(line, col, data["operator"], from_jsonable(data["operand"]))
        case "CallExpr":
            return CallExpr(line, col, data["callee"], tuple(from_jsonable(a) for a in data["arguments"]))
        case "AssignmentExpr":
            return AssignmentExpr(line, col, data["target"], data["operator"], from_jsonable(data["value"]))
    raise ValueError(f"unknown node type: {data.get('node')}")
