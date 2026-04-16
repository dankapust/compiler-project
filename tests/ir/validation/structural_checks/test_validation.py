import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

from ir.ir_instructions import IROpcode, IRLabel
from ir.ir_generator import IRGenerator
from semantic.analyzer import SemanticAnalyzer
from parser.parser import Parser
from lexer.scanner import Scanner
from lexer.token import TokenType

def _compile_to_ir(source: str):
    scanner = Scanner(source)
    tokens = []
    while True:
        t = scanner.next_token()
        tokens.append(t)
        if t.type == TokenType.END_OF_FILE:
            break
    parser = Parser(tokens=tokens)
    program = parser.parse()
    sem = SemanticAnalyzer(file_name="<test>")
    sem.analyze(program)
    gen = IRGenerator(sem.get_symbol_table(), sem.get_decorated_ast())
    return gen.generate(program)

class TestIRValidation(unittest.TestCase):
    def test_basic_block_termination(self):
        source = "fn main() -> int { if (1) { return 1; } return 0; }"
        ir = _compile_to_ir(source)
        for func in ir.functions:
            for block in func.basic_blocks:
                if block == func.exit_block: continue
                self.assertTrue(len(block.instructions) > 0, f"Block {block.label} is empty")
                last = block.instructions[-1]
                is_terminator = last.opcode in (
                    IROpcode.JUMP, IROpcode.JUMP_IF, IROpcode.JUMP_IF_NOT, IROpcode.RETURN
                )
                self.assertTrue(is_terminator, f"Block {block.label} does not end with a terminator")

    def test_label_validity(self):
        source = "fn main() -> int { while(1) { if(1) break; } return 0; }"
        # Note: break might not be supported yet, using simple while
        source = "fn main() -> int { while(1) { if(1) { return 1; } } return 0; }"
        ir = _compile_to_ir(source)
        for func in ir.functions:
            all_labels = {b.label for b in func.basic_blocks}
            for block in func.basic_blocks:
                for instr in block.instructions:
                    for arg in instr.args:
                        if isinstance(arg, IRLabel):
                            self.assertIn(arg.name, all_labels, f"Undefined label {arg.name} in block {block.label}")

if __name__ == "__main__":
    unittest.main()
