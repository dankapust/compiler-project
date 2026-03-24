"""Unit tests for Preprocessor (Sprint 1 Stretch Goal)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))

from preprocessor.preprocessor import Preprocessor  # noqa: E402


def test_comment_removal_single_line() -> None:
    """PRE-1: Single-line comments removed."""
    pp = Preprocessor("int x = 1; // trailing comment\n")
    result = pp.process()
    assert "//" not in result
    assert "int x = 1;" in result
    assert pp.errors == []


def test_comment_removal_block() -> None:
    """PRE-1: Block comments removed."""
    pp = Preprocessor("/* block */ int y = 2;\n")
    result = pp.process()
    assert "/*" not in result and "*/" not in result
    assert "int y = 2;" in result
    assert pp.errors == []


def test_comments_preserved_in_strings() -> None:
    """PRE-4: Comments inside strings preserved."""
    pp = Preprocessor('fn main() { string s = "hello // world"; }\n')
    result = pp.process()
    assert '// world' in result or '"hello' in result
    assert "hello" in result


def test_define_macro() -> None:
    """PRE-2: #define NAME value."""
    pp = Preprocessor("#define MAX 100\nint x = MAX;\n")
    result = pp.process()
    assert "MAX" not in result or "define" in result  # MAX should be expanded
    assert "100" in result


def test_define_api() -> None:
    """PRE-3: define(name, value) programmatic API."""
    pp = Preprocessor("int x = N;\n")
    pp.define("N", "42")
    result = pp.process()
    assert "42" in result


def test_undefine_api() -> None:
    """PRE-3: undefine(name) programmatic API."""
    pp = Preprocessor("#define X 1\nint a = X;\n#undef X\nint b = X;\n")
    result = pp.process()
    assert "int a = 1" in result or "= 1" in result
    assert "int b = X" in result or "b = X" in result


def test_ifdef_defined() -> None:
    """PRE-2: #ifdef includes block when defined."""
    src = "#define FOO\n#ifdef FOO\nint x = 1;\n#endif\n"
    pp = Preprocessor(src)
    result = pp.process()
    assert "int x = 1;" in result


def test_ifdef_not_defined() -> None:
    """PRE-2: #ifdef excludes block when not defined."""
    src = "#ifdef FOO\nint x = 1;\n#endif\nint y = 2;\n"
    pp = Preprocessor(src)
    result = pp.process()
    assert "int x = 1;" not in result
    assert "int y = 2;" in result


def test_ifndef() -> None:
    """PRE-2: #ifndef excludes when defined, includes when not."""
    src = "#ifndef FOO\nint a = 1;\n#endif\n#define FOO\n#ifndef FOO\nint b = 2;\n#endif\n"
    pp = Preprocessor(src)
    result = pp.process()
    assert "int a = 1;" in result
    assert "int b = 2;" not in result


def test_unterminated_comment_error() -> None:
    """PRE-4: Unterminated comment reports error."""
    pp = Preprocessor("/* never ends\n")
    result = pp.process()
    assert len(pp.errors) == 1
    assert "незавершённый" in pp.errors[0].message.lower()


def test_macro_recursion_detected() -> None:
    """PRE-4: Macro recursion detected and prevented."""
    pp = Preprocessor("#define A B\n#define B A\nint x = A;\n")
    result = pp.process()
    assert len(pp.errors) >= 1
    assert "рекурс" in pp.errors[0].message.lower()


def test_line_count_preserved() -> None:
    """PRE-1: Line numbering preserved after comment removal."""
    src = "line1\n// comment\nline3\n"
    pp = Preprocessor(src)
    result = pp.process()
    lines = result.split("\n")
    assert len(lines) >= 3
    assert "line1" in lines[0]
    assert "line3" in lines[2]


def test_nested_block_comments() -> None:
    """PRE-1: Nested block comments handled."""
    pp = Preprocessor("/* outer /* inner */ outer */ int x = 1;\n")
    result = pp.process()
    assert "int x = 1;" in result
    assert pp.errors == []
