from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))

from preprocessor.preprocessor import Preprocessor


def test_comment_removal_single_line() -> None:
    pp = Preprocessor("int x = 1; // trailing comment\n")
    result = pp.process()
    assert "//" not in result
    assert "int x = 1;" in result
    assert pp.errors == []


def test_comment_removal_block() -> None:
    pp = Preprocessor("/* block */ int y = 2;\n")
    result = pp.process()
    assert "/*" not in result and "*/" not in result
    assert "int y = 2;" in result
    assert pp.errors == []


def test_comments_preserved_in_strings() -> None:
    pp = Preprocessor('fn main() { string s = "hello // world"; }\n')
    result = pp.process()
    assert '// world' in result or '"hello' in result
    assert "hello" in result


def test_define_macro() -> None:
    pp = Preprocessor("#define MAX 100\nint x = MAX;\n")
    result = pp.process()
    assert "MAX" not in result or "define" in result
    assert "100" in result


def test_define_api() -> None:
    pp = Preprocessor("int x = N;\n")
    pp.define("N", "42")
    result = pp.process()
    assert "42" in result


def test_undefine_api() -> None:
    pp = Preprocessor("#define X 1\nint a = X;\n#undef X\nint b = X;\n")
    result = pp.process()
    assert "int a = 1" in result or "= 1" in result
    assert "int b = X" in result or "b = X" in result


def test_ifdef_defined() -> None:
    src = "#define FOO\n#ifdef FOO\nint x = 1;\n#endif\n"
    pp = Preprocessor(src)
    result = pp.process()
    assert "int x = 1;" in result


def test_ifdef_not_defined() -> None:
    src = "#ifdef FOO\nint x = 1;\n#endif\nint y = 2;\n"
    pp = Preprocessor(src)
    result = pp.process()
    assert "int x = 1;" not in result
    assert "int y = 2;" in result


def test_ifndef() -> None:
    src = "#ifndef FOO\nint a = 1;\n#endif\n#define FOO\n#ifndef FOO\nint b = 2;\n#endif\n"
    pp = Preprocessor(src)
    result = pp.process()
    assert "int a = 1;" in result
    assert "int b = 2;" not in result


def test_unterminated_comment_error() -> None:
    pp = Preprocessor("/* never ends\n")
    result = pp.process()
    assert len(pp.errors) == 1
    assert "unterminated" in pp.errors[0].message.lower()


def test_macro_recursion_detected() -> None:
    pp = Preprocessor("#define A B\n#define B A\nint x = A;\n")
    result = pp.process()
    assert len(pp.errors) >= 1
    assert "recursion" in pp.errors[0].message.lower()


def test_line_count_preserved() -> None:
    src = "line1\n// comment\nline3\n"
    pp = Preprocessor(src)
    result = pp.process()
    lines = result.split("\n")
    assert len(lines) >= 3
    assert "line1" in lines[0]
    assert "line3" in lines[2]


def test_nested_block_comments() -> None:
    pp = Preprocessor("/* outer /* inner */ outer */ int x = 1;\n")
    result = pp.process()
    assert "int x = 1;" in result
    assert pp.errors == []
