from __future__ import annotations

import re
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

_RE_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]*|_[A-Za-z0-9_]*")
_RE_NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+(?:\.[0-9.]*)?)?")
_RE_WHITESPACE = re.compile(r"[ \t]+")

_UNESCAPE: dict[str, str] = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
_ESCAPE_CHARS = frozenset(_UNESCAPE)
_NEWLINES = frozenset("\n\r")
_INT32_MIN = -(2**31)
_INT32_MAX = 2**31 - 1


@dataclass
class _Cursor:
    i: int = 0
    line: int = 1
    col: int = 1


class Scanner:
    """
    Lexer: produces tokens with (line, column) positions (1-indexed),
    skips whitespace and comments, emits ERROR for recoverable lexical errors.
    """

    def __init__(self, source: str):
        self._src = source
        self._cur = _Cursor()
        self._peeked: Token | None = None
        self._pending_error: Token | None = None
        self.errors: list[ScanError] = []

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

        self._mark_start()
        c = self._src[self._cur.i]

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
        m = _RE_WORD.match(self._src, self._cur.i)
        assert m is not None
        lex = m.group()
        self._advance_by(len(lex))
        if lex[0] == "_":
            return self._err(lex, "identifier cannot start with underscore")
        if len(lex) > 255:
            return self._err(lex, "identifier exceeds maximum length (255)")
        if lex in _BOOL_LITERALS:
            return self._tok(TokenType.BOOL_LITERAL, lex, _BOOL_LITERALS[lex])
        if lex == _NULL_LITERAL:
            return self._tok(TokenType.NULL_LITERAL, lex, None)
        return self._tok(_KEYWORDS.get(lex, TokenType.IDENTIFIER), lex, None)

    def _scan_number(self) -> Token:
        m = _RE_NUMBER.match(self._src, self._cur.i)
        assert m is not None
        lex = m.group()
        self._advance_by(len(lex))
        dot_count = lex.count(".")
        if dot_count == 0:
            return self._make_int(lex)
        if dot_count == 1:
            return self._make_float(lex)
        return self._err(lex, "malformed number literal")

    def _make_int(self, lex: str) -> Token:
        try:
            val = int(lex)
        except ValueError:
            return self._err(lex, "malformed integer literal")
        if val < _INT32_MIN or val > _INT32_MAX:
            return self._err(lex, "integer literal out of 32-bit range")
        return self._tok(TokenType.INT_LITERAL, lex, val)

    def _make_float(self, lex: str) -> Token:
        try:
            return self._tok(TokenType.FLOAT_LITERAL, lex, float(lex))
        except ValueError:
            return self._err(lex, "malformed float literal")

    def _scan_string(self) -> Token:
        parts: list[str] = []
        while True:
            if self.is_at_end():
                return self._err(self._lex(), "unterminated string literal")
            p = self._src[self._cur.i]
            if p == '"':
                self._advance()
                return self._tok(TokenType.STRING_LITERAL, self._lex(), "".join(parts))
            if p in _NEWLINES:
                return self._err(self._lex(), "unterminated string literal")
            if p == "\\":
                parts.append(self._scan_escape())
                continue
            parts.append(p)
            self._advance()

    def _scan_escape(self) -> str:
        self._advance()
        if self.is_at_end():
            return ""
        esc = self._src[self._cur.i]
        if esc in _ESCAPE_CHARS:
            self._advance()
            return _UNESCAPE[esc]
        self._add_error(self._cur.line, self._cur.col, f"unknown escape sequence \\{esc}")
        self._advance()
        return esc

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
        while not self.is_at_end():
            c = self._src[self._cur.i]
            if c == " " or c == "\t":
                m = _RE_WHITESPACE.match(self._src, self._cur.i)
                if m:
                    self._advance_by(m.end() - m.start())
                else:
                    self._advance()
            elif c in _NEWLINES:
                self._advance_newline()
            elif c == "/" and self._cur.i + 1 < len(self._src):
                nc = self._src[self._cur.i + 1]
                if nc == "/":
                    self._skip_line_comment()
                elif nc == "*":
                    self._skip_block_comment()
                else:
                    return
            else:
                return

    def _skip_line_comment(self) -> None:
        self._advance()
        self._advance()
        while not self.is_at_end() and self._src[self._cur.i] not in _NEWLINES:
            self._advance()

    def _skip_block_comment(self) -> None:
        start_line = self._cur.line
        start_col = self._cur.col
        self._advance()
        self._advance()
        depth = 1
        while depth > 0:
            if self.is_at_end():
                self._add_error(start_line, start_col, "unterminated block comment")
                self._pending_error = Token(
                    TokenType.ERROR, "/*", start_line, start_col, "unterminated block comment",
                )
                return
            ch = self._advance()
            if ch in _NEWLINES:
                self._rewind_one_for_newline(ch)
                self._advance_newline()
            elif ch == "/" and not self.is_at_end() and self._src[self._cur.i] == "*":
                self._advance()
                depth += 1
            elif ch == "*" and not self.is_at_end() and self._src[self._cur.i] == "/":
                self._advance()
                depth -= 1

    def _mark_start(self) -> None:
        self._start_i = self._cur.i
        self._start_line = self._cur.line
        self._start_col = self._cur.col
        start_i = self._cur.i
        start_line = self._cur.line
        start_col = self._cur.col

        c = self._advance()

        match c:
            case "_":
                self._consume_alnum_or_underscore()
                lex = self._src[start_i : self._cur.i]
                return self._error_token(start_line, start_col, lex, "identifier cannot start with underscore")
            case c if _is_alpha(c):
                self._consume_alnum_or_underscore()
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
                if lex == _NULL_LITERAL:
                    return Token(TokenType.NULL_LITERAL, lex, start_line, start_col, None)
                kw = _KEYWORDS.get(lex)
                if kw is not None:
                    return Token(kw, lex, start_line, start_col, None)
                return Token(TokenType.IDENTIFIER, lex, start_line, start_col, None)
            case c if c.isdigit():
                self._consume_digits()

                if self._peek_char() == "." and self._peek_next_char().isdigit():
                    self._advance()
                    self._consume_digits()

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

                lex = self._src[start_i : self._cur.i]
                try:
                    val = int(lex)
                except ValueError:
                    return self._error_token(start_line, start_col, lex, "malformed integer literal")
                return Token(TokenType.INT_LITERAL, lex, start_line, start_col, val)
            case '"':
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
                        self._advance()
                        esc = self._peek_char()
                        if esc in ['\\', '"', "n", "t", "r"]:
                            self._advance()
                            s.append(_unescape(esc))
                        else:
                            err_line = self._cur.line
                            err_col = self._cur.col
                            self._advance()
                            self._add_error(err_line, err_col, f"unknown escape sequence \\{esc}")
                            s.append(esc)
                        continue
                    s.append(self._advance())
            case "&":
                if self._match("&"):
                    return Token(TokenType.AND_AND, "&&", start_line, start_col, None)
                return self._error_token(start_line, start_col, "&", "unexpected character '&' (did you mean '&&'?)")
            case "=":
                if self._match("="):
                    return Token(TokenType.EQUAL_EQUAL, "==", start_line, start_col, None)
                return Token(TokenType.ASSIGN, "=", start_line, start_col, None)
            case "!":
                if self._match("="):
                    return Token(TokenType.BANG_EQUAL, "!=", start_line, start_col, None)
                return Token(TokenType.BANG, "!", start_line, start_col, None)
            case "<":
                if self._match("="):
                    return Token(TokenType.LESS_EQUAL, "<=", start_line, start_col, None)
                return Token(TokenType.LESS, "<", start_line, start_col, None)
            case ">":
                if self._match("="):
                    return Token(TokenType.GREATER_EQUAL, ">=", start_line, start_col, None)
                return Token(TokenType.GREATER, ">", start_line, start_col, None)
            case "+":
                if self._match("="):
                    return Token(TokenType.PLUS_ASSIGN, "+=", start_line, start_col, None)
                return Token(TokenType.PLUS, "+", start_line, start_col, None)
            case "-":
                if self._match("="):
                    return Token(TokenType.MINUS_ASSIGN, "-=", start_line, start_col, None)
                if self._match(">"):
                    return Token(TokenType.ARROW, "->", start_line, start_col, None)
                return Token(TokenType.MINUS, "-", start_line, start_col, None)
            case "|":
                if self._match("|"):
                    return Token(TokenType.OR_OR, "||", start_line, start_col, None)
                return self._error_token(start_line, start_col, "|", "unexpected character '|' (did you mean '||'?)")
            case "*":
                if self._match("="):
                    return Token(TokenType.STAR_ASSIGN, "*=", start_line, start_col, None)
                return Token(TokenType.STAR, "*", start_line, start_col, None)
            case "/":
                if self._match("="):
                    return Token(TokenType.SLASH_ASSIGN, "/=", start_line, start_col, None)
                return Token(TokenType.SLASH, "/", start_line, start_col, None)
            case "%":
                if self._match("="):
                    return Token(TokenType.PERCENT_ASSIGN, "%=", start_line, start_col, None)
                return Token(TokenType.PERCENT, "%", start_line, start_col, None)
            case _:
                t = _single_char_token(c)
                if t is not None:
                    return Token(t, c, start_line, start_col, None)
                return self._error_token(start_line, start_col, c, f"invalid character: {repr(c)}")

    def _skip_whitespace_and_comments(self) -> None:
        while True:
            if self.is_at_end():
                return
            c = self._peek_char()
            match c:
                case " " | "\t":
                    self._advance()
                case "\n" | "\r":
                    self._advance_newline()
                case "/":
                    if self._peek_next_char() == "/":
                        self._advance()
                        self._advance()
                        while not self.is_at_end() and self._peek_char() not in "\n\r":
                            self._advance()
                    elif self._peek_next_char() == "*":
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
                    else:
                        return
                case _:
                    return

    def _consume_alnum_or_underscore(self) -> None:
        src = self._src
        n = len(src)
        i = self._cur.i
        while i < n:
            p = src[i]
            if ("a" <= p <= "z") or ("A" <= p <= "Z") or ("0" <= p <= "9") or p == "_":
                i += 1
            else:
                break
        diff = i - self._cur.i
        self._cur.i = i
        self._cur.col += diff

    def _consume_digits(self) -> None:
        src = self._src
        n = len(src)
        i = self._cur.i
        while i < n and src[i].isdigit():
            i += 1
        diff = i - self._cur.i
        self._cur.i = i
        self._cur.col += diff

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

    def _advance_by(self, n: int) -> None:
        self._cur.i += n
        self._cur.col += n

    def _match(self, expected: str) -> bool:
        if self.is_at_end() or self._src[self._cur.i] != expected:
            return False
        self._cur.i += 1
        self._cur.col += 1
        return True

    def _advance_newline(self) -> None:
        c = self._src[self._cur.i] if not self.is_at_end() else ""
        if c == "\r":
            self._cur.i += 1
            if not self.is_at_end() and self._src[self._cur.i] == "\n":
                self._cur.i += 1
        elif c == "\n":
            self._cur.i += 1
        else:
            return
        self._cur.line += 1
        self._cur.col = 1

    def _rewind_one_for_newline(self, ch: str) -> None:
        self._cur.i -= 1
        self._cur.col -= 1

    def _add_error(self, line: int, col: int, message: str) -> None:
        self.errors.append(ScanError(message=message, line=line, column=col))


    def _error_token(self, line: int, col: int, lexeme: str, message: str) -> Token:
        self._add_error(line, col, message)
        return Token(TokenType.ERROR, lexeme, line, col, message)


def _is_alpha(c: str) -> bool:
    return ("a" <= c <= "z") or ("A" <= c <= "Z")


def _is_alnum_or_underscore(c: str) -> bool:
    return _is_alpha(c) or c.isdigit() or c == "_"


_SINGLE_CHAR_TOKENS = {
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    ",": TokenType.COMMA,
    ";": TokenType.SEMICOLON,
}

def _single_char_token(c: str) -> TokenType | None:
    return _SINGLE_CHAR_TOKENS.get(c)


_UNESCAPE_MAP = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}

def _unescape(esc: str) -> str:
    return _UNESCAPE_MAP.get(esc, esc)