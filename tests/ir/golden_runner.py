"""
Golden test infrastructure for IR generation (TEST-3).

Workflow:
  1. First run — generate .expected files:
       set UPDATE_GOLDEN=1
       python -m pytest tests/ir/test_golden.py -v -s

  2. Normal run — compare actual vs. expected:
       python -m pytest tests/ir/test_golden.py -v

  3. After IR changes — update expected files:
       set UPDATE_GOLDEN=1
       python -m pytest tests/ir/test_golden.py -v -s
"""

import os
import sys
import difflib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from lexer.scanner import Scanner
from lexer.token import TokenType
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer
from ir.ir_generator import IRGenerator
from ir.output import format_ir_text, format_ir_stats
from ir.control_flow import PeepholeOptimizer


def compile_to_ir_text(source: str, optimize: bool = False) -> str:
    """Full pipeline: source -> tokens -> AST -> semantic -> IR -> text."""
    scanner = Scanner(source)
    tokens = []
    while True:
        t = scanner.next_token()
        tokens.append(t)
        if t.type == TokenType.END_OF_FILE:
            break

    parser = Parser(tokens=tokens)
    program = parser.parse()

    sem = SemanticAnalyzer(file_name="<golden>")
    sem.analyze(program)

    gen = IRGenerator(
        sem.get_symbol_table(),
        sem.get_decorated_ast(),
        sem.get_registered_struct_types(),
    )
    ir_prog = gen.generate(program)

    if optimize:
        opt = PeepholeOptimizer(ir_prog)
        ir_prog = opt.optimize()

    return format_ir_text(ir_prog)


def compile_to_ir_stats(source: str) -> dict:
    """Full pipeline: source -> IR -> structural properties (block count, instruction count)."""
    scanner = Scanner(source)
    tokens = []
    while True:
        t = scanner.next_token()
        tokens.append(t)
        if t.type == TokenType.END_OF_FILE:
            break

    parser = Parser(tokens=tokens)
    program = parser.parse()

    sem = SemanticAnalyzer(file_name="<golden>")
    sem.analyze(program)

    gen = IRGenerator(
        sem.get_symbol_table(),
        sem.get_decorated_ast(),
        sem.get_registered_struct_types(),
    )
    ir_prog = gen.generate(program)

    total_blocks = 0
    total_instructions = 0
    total_temps = 0
    for func in ir_prog.functions:
        total_blocks += len(func.basic_blocks)
        for block in func.basic_blocks:
            for instr in block.instructions:
                total_instructions += 1
                if instr.dest and hasattr(instr.dest, "id"):
                    total_temps = max(total_temps, instr.dest.id)

    return {
        "functions": len(ir_prog.functions),
        "basic_blocks": total_blocks,
        "instructions": total_instructions,
        "temporaries": total_temps,
    }


def run_golden_test(test_case, src_path: str, expected_path: str, optimize: bool = False):
    """
    Run a golden test: compile .src, compare IR text with .expected file.

    If UPDATE_GOLDEN=1 env var is set or .expected file doesn't exist,
    the actual IR output will be saved as the new expected file.
    """
    if not os.path.exists(src_path):
        test_case.fail(f"Source file not found: {src_path}")

    with open(src_path, "r", encoding="utf-8") as f:
        source = f.read()

    actual = compile_to_ir_text(source, optimize=optimize)

    update = os.environ.get("UPDATE_GOLDEN", "").strip() == "1"

    if update:
        os.makedirs(os.path.dirname(expected_path), exist_ok=True)
        with open(expected_path, "w", encoding="utf-8") as f:
            f.write(actual)
        print(f"  [golden] Updated: {os.path.basename(expected_path)}")
        return

    if not os.path.exists(expected_path):
        test_case.fail(
            f"Expected file not found: {expected_path}\n"
            f"Create it manually or run with UPDATE_GOLDEN=1 to generate."
        )

    with open(expected_path, "r", encoding="utf-8") as f:
        expected = f.read()

    if actual != expected:
        diff_lines = list(difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile="expected",
            tofile="actual",
        ))
        diff_text = "".join(diff_lines)
        test_case.fail(
            f"\nGolden test mismatch for {os.path.basename(src_path)}:\n"
            f"{diff_text}\n\n"
            f"To update expected files:\n"
            f"  set UPDATE_GOLDEN=1\n"
            f"  python -m pytest tests/ir/test_golden.py -v -s"
        )


def run_golden_structural_test(test_case, src_path: str, expected_props: dict):
    """
    Golden test for structural properties (TEST-3):
    block count, instruction count, function count, temporaries.
    """
    if not os.path.exists(src_path):
        test_case.fail(f"Source file not found: {src_path}")

    with open(src_path, "r", encoding="utf-8") as f:
        source = f.read()

    actual_props = compile_to_ir_stats(source)

    for key, expected_val in expected_props.items():
        actual_val = actual_props.get(key)
        if isinstance(expected_val, tuple):
            op, val = expected_val
            if op == ">=":
                test_case.assertGreaterEqual(
                    actual_val, val,
                    f"Structural check failed: {key} = {actual_val}, expected >= {val}"
                )
        else:
            test_case.assertEqual(
                actual_val, expected_val,
                f"Structural check failed: {key} = {actual_val}, expected {expected_val}"
            )
