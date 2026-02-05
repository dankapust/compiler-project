from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional


class TokenType(Enum):
    # Special
    END_OF_FILE = auto()
    ERROR = auto()

    # Identifiers / literals
    IDENTIFIER = auto()
    INT_LITERAL = auto()
    FLOAT_LITERAL = auto()
    STRING_LITERAL = auto()
    BOOL_LITERAL = auto()

    # Keywords
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

    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()

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

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    SEMICOLON = auto()


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    line: int  # 1-indexed
    column: int  # 1-indexed
    literal: Optional[Any] = None

    def format(self) -> str:
        # Required format:
        # LINE:COLUMN TOKEN_TYPE "LEXEME" [LITERAL_VALUE]
        base = f'{self.line}:{self.column} {self.type.name} "{self.lexeme}"'
        if self.literal is None:
            return base
        if isinstance(self.literal, str):
            return f"{base} {self.literal}"
        return f"{base} {self.literal}"


