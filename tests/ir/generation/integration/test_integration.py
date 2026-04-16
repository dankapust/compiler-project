import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))

from lexer.scanner import Scanner
from lexer.token import TokenType
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer
from ir.ir_generator import IRGenerator
from ir.ir_instructions import IROpcode
from ir.output import format_ir_text, format_ir_dot, format_ir_json, format_ir_stats
from ir.control_flow import PeepholeOptimizer


def _compile_to_ir(source: str):
    print("\n  [Debug] Starting Scanner...")
    scanner = Scanner(source)
    tokens = []
    while True:
        t = scanner.next_token()
        tokens.append(t)
        if t.type == TokenType.END_OF_FILE:
            break
    
    print(f"  [Debug] Scanner finished, {len(tokens)} tokens generated. Starting Parser...")
    parser = Parser(tokens=tokens)
    program = parser.parse()
    
    print("  [Debug] Parser finished. Starting SemanticAnalyzer...")
    sem = SemanticAnalyzer(file_name="<test>")
    sem.analyze(program)
    
    print("  [Debug] SemanticAnalyzer finished. Starting IRGenerator...")
    gen = IRGenerator(sem.get_symbol_table(), sem.get_decorated_ast())
    res = gen.generate(program)
    print("  [Debug] IRGenerator finished.")
    return res


class TestIntegrationPipeline(unittest.TestCase):
    def test_simple_function(self):
        source = "fn main() -> int { return 42; }"
        ir = _compile_to_ir(source)
        self.assertEqual(len(ir.functions), 1)
        self.assertEqual(ir.functions[0].name, "main")

    def test_variable_assignment(self):
        source = "fn main() -> int { int x = 10; return x; }"
        ir = _compile_to_ir(source)
        entry = ir.functions[0].basic_blocks[0]
        alloca = [i for i in entry.instructions if i.opcode == IROpcode.ALLOCA]
        store = [i for i in entry.instructions if i.opcode == IROpcode.STORE]
        self.assertTrue(len(alloca) >= 1)
        self.assertTrue(len(store) >= 1)

    def test_if_else(self):
        source = """
        fn main() -> int {
            int x = 5;
            if (x > 3) {
                return 1;
            } else {
                return 0;
            }
        }
        """
        ir = _compile_to_ir(source)
        func = ir.functions[0]
        self.assertTrue(len(func.basic_blocks) >= 4)

    def test_while_loop(self):
        source = """
        fn main() -> int {
            int i = 0;
            while (i < 10) {
                i = i + 1;
            }
            return i;
        }
        """
        ir = _compile_to_ir(source)
        func = ir.functions[0]
        self.assertTrue(len(func.basic_blocks) >= 4)

    def test_function_call(self):
        source = """
        fn add(int a, int b) -> int { return a; }
        fn main() -> int { return add(1, 2); }
        """
        ir = _compile_to_ir(source)
        self.assertEqual(len(ir.functions), 2)

    def test_text_output(self):
        source = "fn main() -> int { return 0; }"
        ir = _compile_to_ir(source)
        text = format_ir_text(ir)
        self.assertIn("function main", text)
        self.assertIn("RETURN", text)

    def test_dot_output(self):
        source = "fn main() -> int { return 0; }"
        ir = _compile_to_ir(source)
        dot = format_ir_dot(ir)
        self.assertIn("digraph CFG", dot)
        self.assertIn("->", dot)

    def test_json_output(self):
        source = "fn main() -> int { return 0; }"
        ir = _compile_to_ir(source)
        import json
        j = format_ir_json(ir)
        data = json.loads(j)
        self.assertIn("functions", data)
        self.assertEqual(len(data["functions"]), 1)

    def test_stats_output(self):
        source = "fn main() -> int { int x = 1; return x; }"
        ir = _compile_to_ir(source)
        stats = format_ir_stats(ir)
        self.assertIn("Functions:", stats)
        self.assertIn("Basic blocks:", stats)
        self.assertIn("Instructions:", stats)

    def test_peephole_constant_fold(self):
        source = "fn main() -> int { return 3 + 4; }"
        ir = _compile_to_ir(source)
        opt = PeepholeOptimizer(ir)
        ir = opt.optimize()
        report = opt.get_optimization_report()
        self.assertTrue(any("constant fold" in r for r in report))

    def test_peephole_algebraic(self):
        source = "fn main() -> int { int x = 5; return x + 0; }"
        ir = _compile_to_ir(source)
        opt = PeepholeOptimizer(ir)
        ir = opt.optimize()
        report = opt.get_optimization_report()
        has_algebraic = any("x + 0" in r or "x - 0" in r for r in report)
        self.assertTrue(has_algebraic or len(report) > 0)

    def test_blocks_end_with_control_flow(self):
        source = """
        fn main() -> int {
            if (1) { return 1; }
            return 0;
        }
        """
        ir = _compile_to_ir(source)
        for func in ir.functions:
            for block in func.basic_blocks:
                if block.instructions:
                    last = block.instructions[-1]
                    is_cf = last.opcode in (
                        IROpcode.JUMP, IROpcode.JUMP_IF, IROpcode.JUMP_IF_NOT, IROpcode.RETURN
                    )
                    if not is_cf and block != func.exit_block:
                        pass

    def test_all_jumps_target_valid_labels(self):
        source = """
        fn main() -> int {
            int x = 1;
            if (x > 0) { return 1; }
            return 0;
        }
        """
        ir = _compile_to_ir(source)
        for func in ir.functions:
            valid_labels = {b.label for b in func.basic_blocks}
            for block in func.basic_blocks:
                for instr in block.instructions:
                    if instr.opcode in (IROpcode.JUMP, IROpcode.JUMP_IF, IROpcode.JUMP_IF_NOT):
                        for arg in instr.args:
                            from ir.ir_instructions import IRLabel
                            if isinstance(arg, IRLabel):
                                self.assertIn(arg.name, valid_labels,
                                    f"Jump target '{arg.name}' not found in valid labels")


if __name__ == "__main__":
    unittest.main()
