from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional


class TokenType(Enum):
    END_OF_FILE = auto()
    ERROR = auto()

    IDENTIFIER = auto()
    INT_LITERAL = auto()
    FLOAT_LITERAL = auto()
    STRING_LITERAL = auto()
    BOOL_LITERAL = auto()
    NULL_LITERAL = auto()

    KW_IF = auto()
    KW_ELSE = auto()
    KW_WHILE = auto()
    KW_FOR = auto()
    KW_INT = auto()
    KW_FLOAT = auto()
    KW_BOOL = auto()
    KW_RETURN = auto()
    KW_VOID = auto()
    KW_STRUCT = auto()
    KW_FN = auto()

    PLUS = auto()
    MINUS = auto()
    PLUS_PLUS = auto()
    MINUS_MINUS = auto()
    BANG = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    ARROW = auto()

    ASSIGN = auto()
    PLUS_ASSIGN = auto()
    MINUS_ASSIGN = auto()
    STAR_ASSIGN = auto()
    SLASH_ASSIGN = auto()
    PERCENT_ASSIGN = auto()

    EQUAL_EQUAL = auto()
    BANG_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    AND_AND = auto()
    OR_OR = auto()

    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    DOT = auto()
    COMMA = auto()
    SEMICOLON = auto()


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    line: int
    column: int
    literal: Optional[Any] = None

    def format(self) -> str:
        base = f'{self.line}:{self.column} {self.type.name} "{self.lexeme}"'
        if self.literal is None:
            return base
        return f"{base} {self.literal}"
