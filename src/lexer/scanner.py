from __future__ import annotations

from dataclasses import dataclass

from lexer.token import Token, TokenType
from utils.errors import ScanError


_KEYWORDS: dict[str, TokenType] = {
    "if": TokenType.KW_IF,
    "else": TokenType.KW_ELSE,
    "while": TokenType.KW_WHILE,
    "for": TokenType.KW_FOR,
    "int": TokenType.KW_INT,
    "float": TokenType.KW_FLOAT,
    "bool": TokenType.KW_BOOL,
    "return": TokenType.KW_RETURN,
    "void": TokenType.KW_VOID,
    "struct": TokenType.KW_STRUCT,
    "fn": TokenType.KW_FN,
}

_BOOL_LITERALS: dict[str, bool] = {"true": True, "false": False}
_NULL_LITERAL = "null"

_OpEntry = tuple[list[tuple[str, TokenType]], TokenType | None, str | None]

_OPERATOR_TABLE: dict[str, _OpEntry] = {
    "&": ([("&", TokenType.AND_AND)], None, "unexpected character '&' (did you mean '&&'?)"),
    "|": ([("|", TokenType.OR_OR)], None, "unexpected character '|' (did you mean '||'?)"),
    "=": ([("=", TokenType.EQUAL_EQUAL)], TokenType.ASSIGN, None),
    "!": ([("=", TokenType.BANG_EQUAL)], TokenType.BANG, None),
    "<": ([("=", TokenType.LESS_EQUAL)], TokenType.LESS, None),
    ">": ([("=", TokenType.GREATER_EQUAL)], TokenType.GREATER, None),
    "+": ([("=", TokenType.PLUS_ASSIGN)], TokenType.PLUS, None),
    "-": ([("=", TokenType.MINUS_ASSIGN), (">", TokenType.ARROW)], TokenType.MINUS, None),
    "*": ([("=", TokenType.STAR_ASSIGN)], TokenType.STAR, None),
    "/": ([("=", TokenType.SLASH_ASSIGN)], TokenType.SLASH, None),
    "%": ([("=", TokenType.PERCENT_ASSIGN)], TokenType.PERCENT, None),
    "(": ([], TokenType.LPAREN, None),
    ")": ([], TokenType.RPAREN, None),
    "{": ([], TokenType.LBRACE, None),
    "}": ([], TokenType.RBRACE, None),
    "[": ([], TokenType.LBRACKET, None),
    "]": ([], TokenType.RBRACKET, None),
    ",": ([], TokenType.COMMA, None),
    ";": ([], TokenType.SEMICOLON, None),
}

_WHITESPACE_SPACE_TAB = (" ", "\t")
_NEWLINE_CHARS = ("\n", "\r")
_ESCAPE_CHARS = frozenset("\\\"ntr")


@dataclass
class _Cursor:
    i: int = 0
    line: int = 1
    col: int = 1


class Scanner:
    def __init__(self, source: str):
        self._src = source
        self._cur = _Cursor()
        self._peeked: Token | None = None
        self._pending_error: Token | None = None
        self.errors: list[ScanError] = []
        self._start_i = 0
        self._start_line = 1
        self._start_col = 1

    def next_token(self) -> Token:
        if self._peeked is not None:
            t = self._peeked
            self._peeked = None
            return t
        return self._scan_token()

    def peek_token(self) -> Token:
        if self._peeked is None:
            self._peeked = self._scan_token()
        return self._peeked

    def is_at_end(self) -> bool:
        return self._cur.i >= len(self._src)

    def get_line(self) -> int:
        return self._cur.line

    def get_column(self) -> int:
        return self._cur.col

    def _scan_token(self) -> Token:
        if self._pending_error is not None:
            t = self._pending_error
            self._pending_error = None
            return t

        self._skip_whitespace_and_comments()

        if self.is_at_end():
            return Token(TokenType.END_OF_FILE, "", self._cur.line, self._cur.col, None)

        self._start_i = self._cur.i
        self._start_line = self._cur.line
        self._start_col = self._cur.col
        c = self._advance()

        if c == "_":
            while _is_alnum_or_underscore(self._peek_char()):
                self._advance()
            return self._err(self._lex(), "identifier cannot start with underscore")

        if _is_alpha(c):
            while _is_alnum_or_underscore(self._peek_char()):
                self._advance()
            lex = self._lex()
            if len(lex) > 255:
                return self._err(lex, "identifier exceeds maximum length (255)")
            if lex in _BOOL_LITERALS:
                return self._tok(TokenType.BOOL_LITERAL, lex, _BOOL_LITERALS[lex])
            if lex == _NULL_LITERAL:
                return self._tok(TokenType.NULL_LITERAL, lex, None)
            return self._tok(_KEYWORDS.get(lex, TokenType.IDENTIFIER), lex, None)

        if c.isdigit():
            while self._peek_char().isdigit():
                self._advance()
            if self._peek_char() == "." and self._peek_next_char().isdigit():
                self._advance()
                while self._peek_char().isdigit():
                    self._advance()
                if self._peek_char() == "." and self._peek_next_char().isdigit():
                    self._advance()
                    while self._peek_char().isdigit() or self._peek_char() == ".":
                        self._advance()
                    return self._err(self._lex(), "malformed number literal")
                lex = self._lex()
                try:
                    return self._tok(TokenType.FLOAT_LITERAL, lex, float(lex))
                except ValueError:
                    return self._err(lex, "malformed float literal")
            lex = self._lex()
            try:
                val = int(lex)
            except ValueError:
                return self._err(lex, "malformed integer literal")
            if val < -(2**31) or val > (2**31 - 1):
                return self._err(lex, "integer literal out of 32-bit range")
            return self._tok(TokenType.INT_LITERAL, lex, val)

        if c == '"':
            s = []
            while True:
                if self.is_at_end():
                    return self._err(self._lex(), "unterminated string literal")
                p = self._peek_char()
                if p == '"':
                    self._advance()
                    return self._tok(TokenType.STRING_LITERAL, self._lex(), "".join(s))
                if p in _NEWLINE_CHARS:
                    return self._err(self._lex(), "unterminated string literal")
                if p == "\\":
                    self._advance()
                    esc = self._peek_char()
                    if esc in _ESCAPE_CHARS:
                        self._advance()
                        s.append(_unescape(esc))
                    else:
                        self._add_error(self._cur.line, self._cur.col, f"unknown escape sequence \\{esc}")
                        self._advance()
                        s.append(esc)
                    continue
                s.append(self._advance())

        entry = _OPERATOR_TABLE.get(c)
        if entry is not None:
            two_char_list, single_tt, err_msg = entry
            for second, tok_type in two_char_list:
                if self._match(second):
                    return self._tok(tok_type, c + second, None)
            if single_tt is not None:
                return self._tok(single_tt, c, None)
            if err_msg is not None:
                return self._err(c, err_msg)

        return self._err(c, f"invalid character: {repr(c)}")

    def _skip_whitespace_and_comments(self) -> None:
        while True:
            if self.is_at_end():
                return
            c = self._peek_char()
            if c in _WHITESPACE_SPACE_TAB:
                self._advance()
                continue
            if c in _NEWLINE_CHARS:
                self._advance_newline()
                continue
            if c == "/" and self._peek_next_char() == "/":
                self._advance()
                self._advance()
                while not self.is_at_end() and self._peek_char() not in _NEWLINE_CHARS:
                    self._advance()
                continue

            if c == "/" and self._peek_next_char() == "*":
                start_line = self._cur.line
                start_col = self._cur.col
                self._advance()
                self._advance()
                depth = 1
                while depth > 0:
                    if self.is_at_end():
                        self._add_error(start_line, start_col, "unterminated block comment")
                        self._pending_error = Token(
                            TokenType.ERROR,
                            "/*",
                            start_line,
                            start_col,
                            "unterminated block comment",
                        )
                        return
                    ch = self._advance()
                    if ch in _NEWLINE_CHARS:
                        self._rewind_one_for_newline(ch)
                        self._advance_newline()
                        continue
                    if ch == "/" and self._peek_char() == "*":
                        self._advance()
                        depth += 1
                        continue
                    if ch == "*" and self._peek_char() == "/":
                        self._advance()
                        depth -= 1
                        continue
                continue

            return

    def _peek_char(self) -> str:
        if self.is_at_end():
            return "\0"
        return self._src[self._cur.i]

    def _peek_next_char(self) -> str:
        j = self._cur.i + 1
        if j >= len(self._src):
            return "\0"
        return self._src[j]

    def _advance(self) -> str:
        ch = self._src[self._cur.i]
        self._cur.i += 1
        self._cur.col += 1
        return ch

    def _match(self, expected: str) -> bool:
        if self.is_at_end():
            return False
        if self._src[self._cur.i] != expected:
            return False
        self._cur.i += 1
        self._cur.col += 1
        return True

    def _advance_newline(self) -> None:
        if self._peek_char() == "\r":
            self._advance()
            if self._peek_char() == "\n":
                self._advance()
        elif self._peek_char() == "\n":
            self._advance()
        else:
            return
        self._cur.line += 1
        self._cur.col = 1

    def _rewind_one_for_newline(self, ch: str) -> None:
        self._cur.i -= 1
        self._cur.col -= 1
        assert self._src[self._cur.i] == ch

    def _lex(self) -> str:
        return self._src[self._start_i : self._cur.i]

    def _tok(self, typ: TokenType, lexeme: str, literal: object = None) -> Token:
        return Token(typ, lexeme, self._start_line, self._start_col, literal)

    def _err(self, lexeme: str, message: str) -> Token:
        self._add_error(self._start_line, self._start_col, message)
        return Token(TokenType.ERROR, lexeme, self._start_line, self._start_col, message)

    def _add_error(self, line: int, col: int, message: str) -> None:
        self.errors.append(ScanError(message=message, line=line, column=col))

    def _error_token(self, line: int, col: int, lexeme: str, message: str) -> Token:
        self._add_error(line, col, message)
        return Token(TokenType.ERROR, lexeme, line, col, message)


def _is_alpha(c: str) -> bool:
    return ("a" <= c <= "z") or ("A" <= c <= "Z")


def _is_alnum_or_underscore(c: str) -> bool:
    return _is_alpha(c) or c.isdigit() or c == "_"


def _unescape(esc: str) -> str:
    return {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}.get(esc, esc)


