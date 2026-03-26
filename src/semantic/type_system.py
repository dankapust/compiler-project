from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TypeKind(Enum):
    VOID = auto()
    INT = auto()
    FLOAT = auto()
    BOOL = auto()
    STRING = auto()
    NULL = auto()
    STRUCT = auto()
    FUNCTION = auto()
    ERROR = auto()


@dataclass(frozen=True, eq=True)
class Type:
    kind: TypeKind
    name: str | None = None
    fields: dict[str, Type] | None = None
    param_types: tuple[Type, ...] | None = None
    return_type: Type | None = None

    def __str__(self) -> str:
        match self.kind:
            case TypeKind.VOID:
                return "void"
            case TypeKind.INT:
                return "int"
            case TypeKind.FLOAT:
                return "float"
            case TypeKind.BOOL:
                return "bool"
            case TypeKind.STRING:
                return "string"
            case TypeKind.NULL:
                return "null"
            case TypeKind.STRUCT:
                return self.name or "<struct>"
            case TypeKind.FUNCTION:
                ps = ", ".join(str(p) for p in (self.param_types or ()))
                rt = str(self.return_type) if self.return_type else "void"
                return f"fn({ps}) -> {rt}"
            case TypeKind.ERROR:
                return "<error>"


VOID = Type(TypeKind.VOID, "void")
INT = Type(TypeKind.INT, "int")
FLOAT = Type(TypeKind.FLOAT, "float")
BOOL = Type(TypeKind.BOOL, "bool")
STRING = Type(TypeKind.STRING, "string")
NULL_T = Type(TypeKind.NULL, "null")
ERROR_T = Type(TypeKind.ERROR, "<error>")


def struct_type(name: str, fields: dict[str, Type]) -> Type:
    return Type(TypeKind.STRUCT, name, fields)


def function_type(params: tuple[Type, ...], ret: Type) -> Type:
    return Type(TypeKind.FUNCTION, None, None, params, ret)


def type_size_bytes(t: Type) -> int:
    match t.kind:
        case TypeKind.INT:
            return 4
        case TypeKind.FLOAT:
            return 4
        case TypeKind.BOOL:
            return 1
        case TypeKind.STRING:
            return 8
        case TypeKind.VOID:
            return 0
        case TypeKind.STRUCT:
            total = 0
            for ft in (t.fields or {}).values():
                sz = type_size_bytes(ft)
                align = type_alignment(ft)
                pad = (align - (total % align)) % align
                total += pad + sz
            return total
        case _:
            return 4


def type_alignment(t: Type) -> int:
    if t.kind == TypeKind.STRUCT:
        return 4
    if t.kind in (TypeKind.INT, TypeKind.FLOAT):
        return 4
    if t.kind == TypeKind.BOOL:
        return 1
    return 4


def types_equal(a: Type, b: Type) -> bool:
    if a.kind != b.kind:
        return False
    if a.kind == TypeKind.STRUCT:
        return a.name == b.name
    if a.kind == TypeKind.FUNCTION:
        return (
            a.param_types == b.param_types
            and a.return_type == b.return_type
        )
    return True


def is_numeric(t: Type) -> bool:
    return t.kind in (TypeKind.INT, TypeKind.FLOAT)


def assignment_compatible(target: Type, value: Type) -> bool:
    if target.kind == TypeKind.ERROR or value.kind == TypeKind.ERROR:
        return True
    if types_equal(target, value):
        return True
    if target.kind == TypeKind.FLOAT and value.kind == TypeKind.INT:
        return True
    if target.kind == TypeKind.STRUCT and value.kind == TypeKind.STRUCT:
        return target.name == value.name
    return False


def binary_arithmetic_result(left: Type, right: Type) -> Type | None:
    if not is_numeric(left) or not is_numeric(right):
        return None
    if left.kind == TypeKind.FLOAT or right.kind == TypeKind.FLOAT:
        return FLOAT
    return INT


def binary_compare_result(left: Type, right: Type) -> Type | None:
    if is_numeric(left) and is_numeric(right):
        return BOOL
    if left.kind == TypeKind.BOOL and right.kind == TypeKind.BOOL:
        return BOOL
    if left.kind == TypeKind.STRING and right.kind == TypeKind.STRING:
        return BOOL
    if left.kind == TypeKind.NULL and right.kind == TypeKind.NULL:
        return BOOL
    return None


def unary_minus_type(operand: Type) -> Type | None:
    if operand.kind == TypeKind.INT:
        return INT
    if operand.kind == TypeKind.FLOAT:
        return FLOAT
    return None


def unary_bang_type(operand: Type) -> Type | None:
    if operand.kind == TypeKind.BOOL:
        return BOOL
    return None
