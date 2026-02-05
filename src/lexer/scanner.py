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


@dataclass
class _Cursor:
    i: int = 0
    line: int = 1
    col: int = 1


class Scanner:
    """
    Sprint 1 scanner:
    - Produces tokens with (line, column) positions (1-indexed).
    - Skips whitespace and comments.
    - Emits TokenType.ERROR for recoverable lexical errors and continues scanning.
    """

    def __init__(self, source: str):
        self._src = source
        self._cur = _Cursor()
        self._peeked: Token | None = None
        self._pending_error: Token | None = None
        self.errors: list[ScanError] = []

    # --- Public API (LEX-2) ---

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

    # --- Core scanning ---

    def _scan_token(self) -> Token:
        if self._pending_error is not None:
            t = self._pending_error
            self._pending_error = None
            return t

        self._skip_whitespace_and_comments()

        if self.is_at_end():
            return Token(TokenType.END_OF_FILE, "", self._cur.line, self._cur.col, None)

        start_i = self._cur.i
        start_line = self._cur.line
        start_col = self._cur.col

        c = self._advance()

        # Identifier-like that starts with underscore is invalid by spec (Sprint 1 LANG-3).
        # Consume the whole run to avoid cascaded errors like: '_' ERROR then 'x' IDENTIFIER.
        if c == "_":
            while _is_alnum_or_underscore(self._peek_char()):
                self._advance()
            lex = self._src[start_i : self._cur.i]
            return self._error_token(start_line, start_col, lex, "identifier cannot start with underscore")

        # Identifiers / keywords / bool
        if _is_alpha(c):
            while _is_alnum_or_underscore(self._peek_char()):
                self._advance()
            lex = self._src[start_i : self._cur.i]
            if len(lex) > 255:
                return self._error_token(
                    start_line,
                    start_col,
                    lex,
                    "identifier exceeds maximum length (255)",
                )
            if lex in _BOOL_LITERALS:
                return Token(TokenType.BOOL_LITERAL, lex, start_line, start_col, _BOOL_LITERALS[lex])
            kw = _KEYWORDS.get(lex)
            if kw is not None:
                return Token(kw, lex, start_line, start_col, None)
            return Token(TokenType.IDENTIFIER, lex, start_line, start_col, None)

        # Numbers
        if c.isdigit():
            while self._peek_char().isdigit():
                self._advance()

            # Float?
            if self._peek_char() == "." and self._peek_next_char().isdigit():
                self._advance()  # '.'
                while self._peek_char().isdigit():
                    self._advance()

                # Malformed number: second '.' followed by digit
                if self._peek_char() == "." and self._peek_next_char().isdigit():
                    self._advance()
                    while True:
                        p = self._peek_char()
                        if p.isdigit() or p == ".":
                            self._advance()
                        else:
                            break
                    lex = self._src[start_i : self._cur.i]
                    return self._error_token(start_line, start_col, lex, "malformed number literal")

                lex = self._src[start_i : self._cur.i]
                try:
                    val = float(lex)
                except ValueError:
                    return self._error_token(start_line, start_col, lex, "malformed float literal")
                return Token(TokenType.FLOAT_LITERAL, lex, start_line, start_col, val)

            # Integer
            lex = self._src[start_i : self._cur.i]
            try:
                val = int(lex)
            except ValueError:
                return self._error_token(start_line, start_col, lex, "malformed integer literal")
            if val < -(2**31) or val > (2**31 - 1):
                return self._error_token(start_line, start_col, lex, "integer literal out of 32-bit range")
            return Token(TokenType.INT_LITERAL, lex, start_line, start_col, val)

        # String
        if c == '"':
            s = []
            while True:
                if self.is_at_end():
                    lex = self._src[start_i : self._cur.i]
                    return self._error_token(start_line, start_col, lex, "unterminated string literal")
                p = self._peek_char()
                if p == '"':
                    self._advance()
                    lex = self._src[start_i : self._cur.i]
                    return Token(TokenType.STRING_LITERAL, lex, start_line, start_col, "".join(s))
                if p == "\n" or p == "\r":
                    lex = self._src[start_i : self._cur.i]
                    return self._error_token(start_line, start_col, lex, "unterminated string literal")
                if p == "\\":
                    self._advance()  # '\'
                    esc = self._peek_char()
                    if esc in ['\\', '"', "n", "t", "r"]:
                        self._advance()
                        s.append(_unescape(esc))
                    else:
                        # Unknown escape: keep raw char (Sprint 1 permissive) but record error.
                        err_line = self._cur.line
                        err_col = self._cur.col
                        self._advance()
                        self._add_error(err_line, err_col, f"unknown escape sequence \\{esc}")
                        s.append(esc)
                    continue
                s.append(self._advance())

        # Operators & delimiters (maximal munch: try multi-char before single-char)
        if c == "&":
            if self._match("&"):
                return Token(TokenType.AND_AND, "&&", start_line, start_col, None)
            return self._error_token(start_line, start_col, "&", "unexpected character '&' (did you mean '&&'?)")

        if c == "=":
            if self._match("="):
                return Token(TokenType.EQUAL_EQUAL, "==", start_line, start_col, None)
            return Token(TokenType.ASSIGN, "=", start_line, start_col, None)

        if c == "!":
            if self._match("="):
                return Token(TokenType.BANG_EQUAL, "!=", start_line, start_col, None)
            return self._error_token(start_line, start_col, "!", "invalid character: '!'")

        if c == "<":
            if self._match("="):
                return Token(TokenType.LESS_EQUAL, "<=", start_line, start_col, None)
            return Token(TokenType.LESS, "<", start_line, start_col, None)

        if c == ">":
            if self._match("="):
                return Token(TokenType.GREATER_EQUAL, ">=", start_line, start_col, None)
            return Token(TokenType.GREATER, ">", start_line, start_col, None)

        if c == "+":
            if self._match("="):
                return Token(TokenType.PLUS_ASSIGN, "+=", start_line, start_col, None)
            return Token(TokenType.PLUS, "+", start_line, start_col, None)

        if c == "-":
            if self._match("="):
                return Token(TokenType.MINUS_ASSIGN, "-=", start_line, start_col, None)
            return Token(TokenType.MINUS, "-", start_line, start_col, None)

        if c == "*":
            if self._match("="):
                return Token(TokenType.STAR_ASSIGN, "*=", start_line, start_col, None)
            return Token(TokenType.STAR, "*", start_line, start_col, None)

        if c == "/":
            if self._match("="):
                return Token(TokenType.SLASH_ASSIGN, "/=", start_line, start_col, None)
            return Token(TokenType.SLASH, "/", start_line, start_col, None)

        if c == "%":
            if self._match("="):
                return Token(TokenType.PERCENT_ASSIGN, "%=", start_line, start_col, None)
            return Token(TokenType.PERCENT, "%", start_line, start_col, None)

        # Delimiters
        t = _single_char_token(c)
        if t is not None:
            return Token(t, c, start_line, start_col, None)

        # Invalid character
        return self._error_token(start_line, start_col, c, f"invalid character: {repr(c)}")

    def _skip_whitespace_and_comments(self) -> None:
        while True:
            if self.is_at_end():
                return
            c = self._peek_char()

            # Whitespace (incl. CRLF)
            if c == " " or c == "\t":
                self._advance()
                continue
            if c == "\n":
                self._advance_newline()
                continue
            if c == "\r":
                self._advance_newline()
                continue

            # Comments
            if c == "/" and self._peek_next_char() == "/":
                self._advance()  # '/'
                self._advance()  # '/'
                while not self.is_at_end() and self._peek_char() not in ("\n", "\r"):
                    self._advance()
                continue

            if c == "/" and self._peek_next_char() == "*":
                start_line = self._cur.line
                start_col = self._cur.col
                self._advance()  # '/'
                self._advance()  # '*'
                depth = 1
                while depth > 0:
                    if self.is_at_end():
                        self._add_error(start_line, start_col, "unterminated block comment")
                        # Emit one ERROR token, then END_OF_FILE (recovery).
                        self._pending_error = Token(
                            TokenType.ERROR,
                            "/*",
                            start_line,
                            start_col,
                            "unterminated block comment",
                        )
                        return
                    ch = self._advance()
                    if ch == "\n" or ch == "\r":
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

    # --- Low-level helpers ---

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
        # Supports '\n' and '\r\n' and bare '\r'
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
        # We already advanced 1 char, but if it's newline marker, we want to handle it
        # via _advance_newline() to apply CRLF logic and line/col reset.
        self._cur.i -= 1
        self._cur.col -= 1
        assert self._src[self._cur.i] == ch

    def _add_error(self, line: int, col: int, message: str) -> None:
        self.errors.append(ScanError(message=message, line=line, column=col))

    def _error_token(self, line: int, col: int, lexeme: str, message: str) -> Token:
        self._add_error(line, col, message)
        return Token(TokenType.ERROR, lexeme, line, col, message)


def _is_alpha(c: str) -> bool:
    return ("a" <= c <= "z") or ("A" <= c <= "Z")


def _is_alnum_or_underscore(c: str) -> bool:
    return _is_alpha(c) or c.isdigit() or c == "_"


def _single_char_token(c: str) -> TokenType | None:
    return {
        "(": TokenType.LPAREN,
        ")": TokenType.RPAREN,
        "{": TokenType.LBRACE,
        "}": TokenType.RBRACE,
        "[": TokenType.LBRACKET,
        "]": TokenType.RBRACKET,
        ",": TokenType.COMMA,
        ";": TokenType.SEMICOLON,
    }.get(c)


def _unescape(esc: str) -> str:
    return {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}.get(esc, esc)


