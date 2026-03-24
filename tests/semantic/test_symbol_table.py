"""Unit tests: symbol table and scope nesting (Sprint 3)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))

from semantic.symbol_table import SymbolInfo, SymbolKind, SymbolTable  # noqa: E402
from semantic.type_system import INT, assignment_compatible, binary_arithmetic_result  # noqa: E402
from semantic.analyzer import SemanticAnalyzer  # noqa: E402
from preprocessor.preprocessor import Preprocessor  # noqa: E402
from lexer.scanner import Scanner  # noqa: E402
from lexer.token import TokenType  # noqa: E402
from parser.parser import Parser  # noqa: E402


class TestSymbolTable(unittest.TestCase):
    def test_enter_exit_scope(self) -> None:
        t = SymbolTable()
        self.assertEqual(t.scope_depth(), 1)
        t.enter_scope("block")
        self.assertEqual(t.scope_depth(), 2)
        t.exit_scope()
        self.assertEqual(t.scope_depth(), 1)

    def test_insert_lookup_local(self) -> None:
        t = SymbolTable()
        a = SymbolInfo("a", INT, SymbolKind.VARIABLE, 1, 1, initialized=True)
        self.assertTrue(t.insert("a", a))
        self.assertFalse(t.insert("a", a))
        self.assertIsNotNone(t.lookup_local("a"))
        self.assertIsNone(t.lookup_local("b"))

    def test_lookup_nested(self) -> None:
        t = SymbolTable()
        g = SymbolInfo("x", INT, SymbolKind.VARIABLE, 1, 1, initialized=True)
        t.insert("x", g)
        t.enter_scope("block")
        inner = SymbolInfo("y", INT, SymbolKind.VARIABLE, 2, 1, initialized=True)
        t.insert("y", inner)
        self.assertEqual(t.lookup("x").name, "x")
        self.assertEqual(t.lookup("y").name, "y")
        t.exit_scope()
        self.assertIsNotNone(t.lookup("x"))
        self.assertIsNone(t.lookup("y"))


class TestTypeSystem(unittest.TestCase):
    def test_assignment_int_to_float(self) -> None:
        from semantic.type_system import FLOAT

        self.assertTrue(assignment_compatible(FLOAT, INT))
        self.assertFalse(assignment_compatible(INT, FLOAT))

    def test_arithmetic(self) -> None:
        from semantic.type_system import FLOAT as F

        self.assertEqual(binary_arithmetic_result(INT, INT), INT)
        self.assertEqual(binary_arithmetic_result(INT, F), F)


def _analyze_src(src: str) -> SemanticAnalyzer:
    pp = Preprocessor(src)
    processed = pp.process()
    sc = Scanner(processed)
    toks: list = []
    while True:
        t = sc.next_token()
        toks.append(t)
        if t.type == TokenType.END_OF_FILE:
            break

    p = Parser(tokens=toks)
    program = p.parse()

    sem = SemanticAnalyzer(file_name="test.src", source_text=processed)
    sem.analyze(program)
    return sem


class TestSemanticAnalyzer(unittest.TestCase):
    def test_function_call_wrong_arg_count(self) -> None:
        sem = _analyze_src(
            "fn add(int a, int b) -> int { return a + b; }\n"
            "fn main() { add(1); }\n"
        )
        cats = [e.category for e in sem.get_errors()]
        self.assertIn("argument_count_mismatch", cats)

    def test_use_before_init_in_initializer(self) -> None:
        sem = _analyze_src(
            "fn main() -> int {\n"
            "  int x;\n"
            "  int y = x + 1;\n"
            "  return y;\n"
            "}\n"
        )
        cats = [e.category for e in sem.get_errors()]
        self.assertIn("use_before_declaration", cats)

    def test_error_format_contains_caret_pointer(self) -> None:
        sem = _analyze_src("fn main() { x = 1; }\n")
        errs = sem.get_errors()
        self.assertTrue(errs)
        formatted = errs[0].format()
        self.assertIn("^", formatted)


if __name__ == "__main__":
    unittest.main()
