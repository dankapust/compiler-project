from __future__ import annotations

import re

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

_OPERATOR_TABLE = {
    "&": ([("&", TokenType.AND_AND)], None, "unexpected character '&' (did you mean '&&'?)"),
    "|": ([("|", TokenType.OR_OR)], None, "unexpected character '|' (did you mean '||'?)"),
    "=": ([("=", TokenType.EQUAL_EQUAL)], TokenType.ASSIGN, None),
    "!": ([("=", TokenType.BANG_EQUAL)], TokenType.BANG, None),
    "<": ([("=", TokenType.LESS_EQUAL)], TokenType.LESS, None),
    ">": ([("=", TokenType.GREATER_EQUAL)], TokenType.GREATER, None),
    "+": ([("+", TokenType.PLUS_PLUS), ("=", TokenType.PLUS_ASSIGN)], TokenType.PLUS, None),
    "-": ([("-", TokenType.MINUS_MINUS), ("=", TokenType.MINUS_ASSIGN), (">", TokenType.ARROW)], TokenType.MINUS, None),
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

_RE_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]*|_[A-Za-z0-9_]*")
_RE_NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+(?:\.[0-9.]*)?)?")
_RE_WHITESPACE = re.compile(r"[ \t]+")
_RE_STR_CHUNK = re.compile(r'[^"\\\n\r]+')

_UNESCAPE: dict[str, str] = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
_NEWLINES = frozenset("\n\r")
_INT32_MIN = -(2**31)
_INT32_MAX = 2**31 - 1


class Scanner:
    def __init__(self, source: str):
        self._src = source
        self._n = len(source)
        self._i = 0
        self._line = 1
        self._col = 1
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
        return self._i >= self._n

    def get_line(self) -> int:
        return self._line

    def get_column(self) -> int:
        return self._col

    def _scan_token(self) -> Token:
        if self._pending_error is not None:
            t = self._pending_error
            self._pending_error = None
            return t

        self._skip_whitespace_and_comments()

        if self._i >= self._n:
            return Token(TokenType.END_OF_FILE, "", self._line, self._col, None)

        self._mark_start()
        c = self._src[self._i]

        if c == "_" or ("a" <= c <= "z") or ("A" <= c <= "Z"):
            return self._scan_word()
        if "0" <= c <= "9":
            return self._scan_number()
        if c == '"':
            self._advance()
            return self._scan_string()
        self._advance()
        return self._scan_operator(c)

    def _scan_word(self) -> Token:
        m = _RE_WORD.match(self._src, self._i)
        assert m is not None
        lex = m.group()
        self._advance_by(len(lex))
        if lex[0] == "_":
            return self._err(lex, "identifier cannot start with underscore")
        if len(lex) > 255:
            return self._err(lex, "identifier exceeds maximum length (255)")
        if lex in _BOOL_LITERALS:
            return self._tok(TokenType.BOOL_LITERAL, lex, _BOOL_LITERALS[lex])
        if lex == "null":
            return self._tok(TokenType.NULL_LITERAL, lex, None)
        return self._tok(_KEYWORDS.get(lex, TokenType.IDENTIFIER), lex, None)

    def _scan_number(self) -> Token:
        m = _RE_NUMBER.match(self._src, self._i)
        assert m is not None
        lex = m.group()
        self._advance_by(len(lex))
        dots = lex.count(".")
        if dots == 0:
            try:
                val = int(lex)
            except ValueError:
                return self._err(lex, "malformed integer literal")
            if not _INT32_MIN <= val <= _INT32_MAX:
                return self._err(lex, "integer literal out of 32-bit range")
            return self._tok(TokenType.INT_LITERAL, lex, val)
        if dots == 1:
            try:
                return self._tok(TokenType.FLOAT_LITERAL, lex, float(lex))
            except ValueError:
                return self._err(lex, "malformed float literal")
        return self._err(lex, "malformed number literal")

    def _scan_string(self) -> Token:
        parts: list[str] = []
        while True:
            m = _RE_STR_CHUNK.match(self._src, self._i)
            if m:
                parts.append(m.group())
                self._advance_by(len(m.group()))
            if self._i >= self._n:
                return self._err(self._lex(), "unterminated string literal")
            p = self._src[self._i]
            if p == '"':
                self._advance()
                return self._tok(TokenType.STRING_LITERAL, self._lex(), "".join(parts))
            if p in _NEWLINES:
                return self._err(self._lex(), "unterminated string literal")
            if p == "\\":
                self._advance()
                if self._i >= self._n:
                    continue
                esc = self._src[self._i]
                if esc in _UNESCAPE:
                    self._advance()
                    parts.append(_UNESCAPE[esc])
                else:
                    self._add_error(self._line, self._col, f"unknown escape sequence \\{esc}")
                    self._advance()
                    parts.append(esc)

    def _scan_operator(self, c: str) -> Token:
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
        src, n = self._src, self._n
        while self._i < n:
            c = src[self._i]
            if c == " " or c == "\t":
                m = _RE_WHITESPACE.match(src, self._i)
                self._advance_by(m.end() - m.start())
            elif c in _NEWLINES:
                self._advance_newline()
            elif c == "/" and self._i + 1 < n:
                nc = src[self._i + 1]
                if nc == "/":
                    self._skip_line_comment()
                elif nc == "*":
                    self._skip_block_comment()
                else:
                    return
            else:
                return

    def _skip_line_comment(self) -> None:
        self._advance_by(2)
        src, n = self._src, self._n
        i = self._i
        while i < n and src[i] not in _NEWLINES:
            i += 1
        self._advance_by(i - self._i)

    def _skip_block_comment(self) -> None:
        sl, sc = self._line, self._col
        self._advance_by(2)
        src, n = self._src, self._n
        depth = 1
        while depth > 0:
            if self._i >= n:
                self._add_error(sl, sc, "unterminated block comment")
                self._pending_error = Token(
                    TokenType.ERROR, "/*", sl, sc, "unterminated block comment",
                )
                return
            ch = src[self._i]
            if ch in _NEWLINES:
                self._advance_newline()
            elif ch == "/" and self._i + 1 < n and src[self._i + 1] == "*":
                self._advance_by(2)
                depth += 1
            elif ch == "*" and self._i + 1 < n and src[self._i + 1] == "/":
                self._advance_by(2)
                depth -= 1
            else:
                self._advance()

    def _mark_start(self) -> None:
        self._start_i = self._i
        self._start_line = self._line
        self._start_col = self._col

    def _advance(self) -> str:
        ch = self._src[self._i]
        self._i += 1
        self._col += 1
        return ch

    def _advance_by(self, n: int) -> None:
        self._i += n
        self._col += n

    def _match(self, expected: str) -> bool:
        if self._i >= self._n or self._src[self._i] != expected:
            return False
        self._i += 1
        self._col += 1
        return True

    def _advance_newline(self) -> None:
        if self._i >= self._n:
            return
        c = self._src[self._i]
        if c == "\r":
            self._i += 1
            if self._i < self._n and self._src[self._i] == "\n":
                self._i += 1
        elif c == "\n":
            self._i += 1
        else:
            return
        self._line += 1
        self._col = 1

    def _lex(self) -> str:
        return self._src[self._start_i : self._i]

    def _tok(self, typ: TokenType, lexeme: str, literal: object = None) -> Token:
        return Token(typ, lexeme, self._start_line, self._start_col, literal)

    def _err(self, lexeme: str, message: str) -> Token:
        self._add_error(self._start_line, self._start_col, message)
        return Token(TokenType.ERROR, lexeme, self._start_line, self._start_col, message)

    def _add_error(self, line: int, col: int, message: str) -> None:
        self.errors.append(ScanError(message=message, line=line, column=col))
