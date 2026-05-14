"""
Golden tests for IR generation (TEST-3).

Compares actual IR output against .expected reference files.
Also checks structural properties (block count, instruction count).

To generate/update .expected files:
    set UPDATE_GOLDEN=1
    python -m pytest tests/ir/test_golden.py -v -s
"""

import sys
import os
import unittest

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)
sys.path.insert(0, os.path.join(_dir, "..", "..", "src"))

from golden_runner import run_golden_test, run_golden_structural_test


def _golden_path(*parts):
    return os.path.join(_dir, "generation", *parts)


# ──────────────────────────────────────────────
# Golden: Expression Translation
# ──────────────────────────────────────────────

class TestGoldenExpressions(unittest.TestCase):
    """Golden tests: expression → IR (TEST-3)."""

    def test_golden_literal_return(self):
        run_golden_test(
            self,
            _golden_path("expressions", "golden", "literal_return.src"),
            _golden_path("expressions", "golden", "literal_return.expected"),
        )

    def test_golden_binary_add(self):
        run_golden_test(
            self,
            _golden_path("expressions", "golden", "binary_add.src"),
            _golden_path("expressions", "golden", "binary_add.expected"),
        )

    def test_golden_nested_expr(self):
        run_golden_test(
            self,
            _golden_path("expressions", "golden", "nested_expr.src"),
            _golden_path("expressions", "golden", "nested_expr.expected"),
        )

    def test_golden_comparison(self):
        run_golden_test(
            self,
            _golden_path("expressions", "golden", "comparison.src"),
            _golden_path("expressions", "golden", "comparison.expected"),
        )


# ──────────────────────────────────────────────
# Golden: Control Flow Translation
# ──────────────────────────────────────────────

class TestGoldenControlFlow(unittest.TestCase):
    """Golden tests: control flow → IR (TEST-3)."""

    def test_golden_if_simple(self):
        run_golden_test(
            self,
            _golden_path("control_flow", "golden", "if_simple.src"),
            _golden_path("control_flow", "golden", "if_simple.expected"),
        )

    def test_golden_if_else(self):
        run_golden_test(
            self,
            _golden_path("control_flow", "golden", "if_else.src"),
            _golden_path("control_flow", "golden", "if_else.expected"),
        )

    def test_golden_while_loop(self):
        run_golden_test(
            self,
            _golden_path("control_flow", "golden", "while_loop.src"),
            _golden_path("control_flow", "golden", "while_loop.expected"),
        )


# ──────────────────────────────────────────────
# Golden: Function Translation
# ──────────────────────────────────────────────

class TestGoldenFunctions(unittest.TestCase):
    """Golden tests: functions → IR (TEST-3)."""

    def test_golden_function_params(self):
        run_golden_test(
            self,
            _golden_path("functions", "golden", "function_params.src"),
            _golden_path("functions", "golden", "function_params.expected"),
        )

    def test_golden_function_call(self):
        run_golden_test(
            self,
            _golden_path("functions", "golden", "function_call.src"),
            _golden_path("functions", "golden", "function_call.expected"),
        )


# ──────────────────────────────────────────────
# Golden: Integration (full pipeline src → IR)
# ──────────────────────────────────────────────

class TestGoldenIntegration(unittest.TestCase):
    """Golden tests: full pipeline (TEST-3, TEST-5)."""

    def test_golden_var_assign(self):
        run_golden_test(
            self,
            _golden_path("integration", "golden", "var_assign.src"),
            _golden_path("integration", "golden", "var_assign.expected"),
        )

    def test_golden_full_program(self):
        run_golden_test(
            self,
            _golden_path("integration", "golden", "full_program.src"),
            _golden_path("integration", "golden", "full_program.expected"),
        )

    def test_golden_optimized(self):
        run_golden_test(
            self,
            _golden_path("integration", "golden", "constant_fold.src"),
            _golden_path("integration", "golden", "constant_fold.expected"),
            optimize=True,
        )


# ──────────────────────────────────────────────
# Structural Property Checks (TEST-3)
# ──────────────────────────────────────────────

class TestGoldenStructural(unittest.TestCase):
    """Golden tests: structural properties — block count, instruction count (TEST-3)."""

    def test_structural_literal_return(self):
        run_golden_structural_test(
            self,
            _golden_path("expressions", "golden", "literal_return.src"),
            {"functions": 1, "basic_blocks": (">=", 2)},
        )

    def test_structural_if_else(self):
        run_golden_structural_test(
            self,
            _golden_path("control_flow", "golden", "if_else.src"),
            {"functions": 1, "basic_blocks": (">=", 4)},
        )

    def test_structural_while_loop(self):
        run_golden_structural_test(
            self,
            _golden_path("control_flow", "golden", "while_loop.src"),
            {"functions": 1, "basic_blocks": (">=", 4)},
        )

    def test_structural_function_call(self):
        run_golden_structural_test(
            self,
            _golden_path("functions", "golden", "function_call.src"),
            {"functions": 2},
        )

    def test_structural_full_program(self):
        run_golden_structural_test(
            self,
            _golden_path("integration", "golden", "full_program.src"),
            {"functions": 2, "basic_blocks": (">=", 6)},
        )


if __name__ == "__main__":
    unittest.main()
