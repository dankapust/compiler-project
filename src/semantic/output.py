from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from parser.ast import (
    ASTNode,
    ProgramNode,
    LiteralExpr,
    IdentifierExpr,
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
)
from semantic.symbol_table import SymbolInfo, SymbolKind, SymbolTable
from semantic.type_system import Type


@dataclass
class DecoratedAST:
    program: ProgramNode
    expr_types: dict[int, str]
    folded_constants: dict[int, Any]
    symbol_refs: dict[int, SymbolInfo]
    call_refs: dict[int, SymbolInfo]


_KIND_RU = {
    "VARIABLE": "переменная",
    "FUNCTION": "функция",
    "PARAMETER": "параметр",
    "STRUCT": "структура",
}


def format_symbol_table_text(table: SymbolTable) -> str:
    lines: list[str] = ["Таблица символов (по областям видимости):"]
    for i, (kind, syms) in enumerate(table.dump_scopes()):
        lines.append(f"  [{i}] область={kind}")
        if not syms:
            lines.append("    (пусто)")
            continue
        for name, info in sorted(syms.items()):
            lines.append(_format_symbol_line(name, info))
    return "\n".join(lines) + "\n"


def _format_symbol_line(name: str, info: SymbolInfo) -> str:
    extra: list[str] = []
    if info.kind == SymbolKind.FUNCTION and info.param_types is not None:
        ps = ", ".join(str(p) for p in info.param_types)
        rt = str(info.return_type) if info.return_type else "void"
        extra.append(f"fn({ps}) -> {rt}")
    elif info.kind == SymbolKind.STRUCT and info.struct_fields:
        fs = ", ".join(f"{k}: {v}" for k, v in info.struct_fields.items())
        extra.append(f"struct {{ {fs} }}")
    else:
        extra.append(str(info.type))
    loc = f"стр. {info.line}"
    init = "инициализирована" if info.initialized else "не инициализирована"
    off = f" смещение={info.stack_offset}" if info.stack_offset is not None else ""
    sz = f" размер={info.size_bytes} б" if info.size_bytes is not None else ""
    kind_ru = _KIND_RU.get(info.kind.name, info.kind.name.lower())
    return f"    - {name}: {kind_ru} {' '.join(extra)} ({loc}, {init}{off}{sz})"


def format_symbol_table_json(table: SymbolTable) -> str:
    data: list[dict[str, Any]] = []
    for kind, syms in table.dump_scopes():
        scope_obj: dict[str, Any] = {"scope": kind, "symbols": {}}
        for n, info in syms.items():
            scope_obj["symbols"][n] = {
                "kind": info.kind.name,
                "type": str(info.type),
                "line": info.line,
                "column": info.column,
                "initialized": info.initialized,
                "stack_offset": info.stack_offset,
                "size_bytes": info.size_bytes,
            }
            if info.param_types is not None:
                scope_obj["symbols"][n]["param_types"] = [str(t) for t in info.param_types]
                scope_obj["symbols"][n]["return_type"] = str(info.return_type) if info.return_type else None
        data.append(scope_obj)
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def format_type_annotations(program: ProgramNode, expr_types: dict[int, str]) -> str:
    lines: list[str] = ["Аннотации типов (выражения):"]

    def walk_expr(n: ASTNode) -> None:
        tid = id(n)
        if tid in expr_types:
            label = _expr_label(n)
            lines.append(f"  {n.line}:{n.column}  {label}  [тип: {expr_types[tid]}]")
        match n:
            case LiteralExpr() | IdentifierExpr():
                pass
            case BinaryExpr(left=left, right=right):
                walk_expr(left)
                walk_expr(right)
            case UnaryExpr(operand=op):
                walk_expr(op)
            case CallExpr(arguments=args):
                for a in args:
                    walk_expr(a)
            case AssignmentExpr(value=v):
                walk_expr(v)
            case IncDecExpr():
                pass
            case _:
                pass

    def walk_stmt(s: ASTNode) -> None:
        match s:
            case VarDeclStmt(initializer=init):
                if init:
                    walk_expr(init)
            case ExprStmt(expression=e):
                walk_expr(e)
            case IfStmt(condition=c, then_branch=th, else_branch=el):
                walk_expr(c)
                walk_stmt(th)
                if el:
                    walk_stmt(el)
            case WhileStmt(condition=c, body=b):
                walk_expr(c)
                walk_stmt(b)
            case ForStmt(init=i, condition=cd, update=u, body=b):
                if i and not isinstance(i, VarDeclStmt):
                    walk_expr(i)
                elif isinstance(i, VarDeclStmt) and i.initializer:
                    walk_expr(i.initializer)
                if cd:
                    walk_expr(cd)
                if u:
                    walk_expr(u)
                walk_stmt(b)
            case ReturnStmt(value=v):
                if v:
                    walk_expr(v)
            case BlockStmt(statements=stmts):
                for x in stmts:
                    walk_stmt(x)
            case _:
                pass

    def walk_decl(d: ASTNode) -> None:
        match d:
            case FunctionDecl(body=b):
                if b:
                    walk_stmt(b)
            case StructDecl():
                pass
            case VarDeclStmt(initializer=init):
                if init:
                    walk_expr(init)
            case _:
                walk_stmt(d)

    for decl in program.declarations:
        walk_decl(decl)
    return "\n".join(lines) + "\n"


def _expr_label(n: ASTNode) -> str:
    match n:
        case IdentifierExpr(name=name):
            return f"идент {name}"
        case LiteralExpr():
            return "литерал"
        case BinaryExpr(operator=op):
            return f"бинарн. {op}"
        case UnaryExpr(operator=op):
            return f"унарн. {op}"
        case CallExpr(callee=c):
            return f"вызов {c}"
        case AssignmentExpr(target=t, operator=op):
            return f"присв. {t} {op}"
        case IncDecExpr(target=t, operator=op):
            return f"инкр. {op} {t}"
    return type(n).__name__


def format_validation_report(
    error_count: int,
    warning_count: int,
    table: SymbolTable,
    expr_types: dict[int, str],
) -> str:
    lines: list[str] = [
        "Отчёт семантической проверки",
        f"  ошибок: {error_count}",
        f"  предупреждений: {warning_count}",
        "",
        "Символы по областям:",
    ]
    for kind, syms in table.dump_scopes():
        lines.append(f"  область={kind}: {', '.join(sorted(syms.keys())) or '(нет)'}")
    lines.append("")
    lines.append(f"Всего аннотированных выражений: {len(expr_types)}")
    return "\n".join(lines) + "\n"


def format_decorated_ast_text(
    program: ProgramNode,
    expr_types: dict[int, str],
    symbol_refs: dict[int, SymbolInfo] | None = None,
    call_refs: dict[int, SymbolInfo] | None = None,
) -> str:
    lines: list[str] = [f"Программа [с типами] {program.line}:{program.column}:"]

    def _sym_desc(sym: SymbolInfo | None) -> str:
        if sym is None:
            return "?"
        if sym.kind == SymbolKind.FUNCTION and sym.param_types is not None and sym.return_type is not None:
            ps = ", ".join(str(t) for t in sym.param_types)
            return f"функция({ps}) -> {sym.return_type}"
        return sym.kind.name.lower()

    def fmt_expr(n: ASTNode, indent: int) -> None:
        pad = "  " * indent
        ts = expr_types.get(id(n), "?")
        match n:
            case LiteralExpr(value=v, type_tag=tag):
                lines.append(f"{pad}Литерал {v!r} ({tag}) [тип: {ts}]")
            case IdentifierExpr(name=name):
                sym = symbol_refs.get(id(n)) if symbol_refs is not None else None
                lines.append(
                    f"{pad}Идентификатор {name} [тип: {ts}, символ: {_sym_desc(sym)}]"
                )
            case BinaryExpr(left=l, operator=op, right=r):
                lines.append(f"{pad}Бинарное {op} [тип: {ts}]")
                fmt_expr(l, indent + 1)
                fmt_expr(r, indent + 1)
            case UnaryExpr(operator=op, operand=o):
                lines.append(f"{pad}Унарное {op} [тип: {ts}]")
                fmt_expr(o, indent + 1)
            case CallExpr(callee=c, arguments=args):
                sym = call_refs.get(id(n)) if call_refs is not None else None
                lines.append(f"{pad}Вызов {c} [тип: {ts}, resolved: {_sym_desc(sym)}]")
                for a in args:
                    fmt_expr(a, indent + 1)
            case AssignmentExpr(target=t, operator=op, value=v):
                sym = symbol_refs.get(id(n)) if symbol_refs is not None else None
                lines.append(f"{pad}Присваивание {t} {op} [тип: {ts}, символ: {_sym_desc(sym)}]")
                fmt_expr(v, indent + 1)
            case IncDecExpr(target=t, operator=op, prefix=pr):
                sym = symbol_refs.get(id(n)) if symbol_refs is not None else None
                lines.append(
                    f"{pad}Инкремент {op} {'преф' if pr else 'пост'} {t} [тип: {ts}, символ: {_sym_desc(sym)}]"
                )

    def fmt_stmt(s: ASTNode, indent: int) -> None:
        pad = "  " * indent
        match s:
            case VarDeclStmt(var_type=vt, name=nm, initializer=init):
                ini = f" = ..." if init else ""
                lines.append(f"{pad}Объявление {vt} {nm}{ini}")
                if init:
                    fmt_expr(init, indent + 1)
            case ExprStmt(expression=e):
                lines.append(f"{pad}Выражение-оператор")
                fmt_expr(e, indent + 1)
            case BlockStmt(statements=stmts):
                lines.append(f"{pad}Блок")
                for x in stmts:
                    fmt_stmt(x, indent + 1)
            case IfStmt(condition=c, then_branch=th, else_branch=el):
                lines.append(f"{pad}Условие if")
                fmt_expr(c, indent + 1)
                fmt_stmt(th, indent + 1)
                if el:
                    fmt_stmt(el, indent + 1)
            case WhileStmt(condition=c, body=b):
                lines.append(f"{pad}Цикл while")
                fmt_expr(c, indent + 1)
                fmt_stmt(b, indent + 1)
            case ForStmt(init=i, condition=cd, update=u, body=b):
                lines.append(f"{pad}Цикл for")
                if isinstance(i, VarDeclStmt):
                    fmt_stmt(i, indent + 1)
                elif i:
                    fmt_expr(i, indent + 1)
                if cd:
                    fmt_expr(cd, indent + 1)
                if u:
                    fmt_expr(u, indent + 1)
                fmt_stmt(b, indent + 1)
            case ReturnStmt(value=v):
                lines.append(f"{pad}Возврат")
                if v:
                    fmt_expr(v, indent + 1)
            case EmptyStmt():
                lines.append(f"{pad}Пустой оператор")
            case _:
                lines.append(f"{pad}{type(s).__name__}")

    def fmt_decl(d: ASTNode, indent: int) -> None:
        pad = "  " * indent
        match d:
            case StructDecl(name=nm, fields=fields):
                lines.append(f"{pad}Структура {nm}")
                for f in fields:
                    fmt_stmt(f, indent + 1)
            case FunctionDecl(name=nm, params=ps, return_type=rt, body=b):
                lines.append(f"{pad}Функция {nm} -> {rt}")
                for p in ps:
                    lines.append(f"{pad}  Параметр {p.param_type} {p.name}")
                if b:
                    fmt_stmt(b, indent + 1)
            case VarDeclStmt():
                fmt_stmt(d, indent)
            case _:
                fmt_stmt(d, indent)

    for decl in program.declarations:
        fmt_decl(decl, 1)
    return "\n".join(lines) + "\n"
