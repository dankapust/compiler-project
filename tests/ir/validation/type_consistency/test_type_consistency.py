import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))

from ir.ir_instructions import IRInstruction, IROpcode, IRTemp
from ir.basic_block import IRProgram, BasicBlock, IRFunction

class TestTypeConsistency(unittest.TestCase):
    def test_temp_types(self):
        func = IRFunction("test_func", "int", [])
        block = BasicBlock("entry")
        func.add_block(block)
        
        t1 = IRTemp(1, type="int")
        t2 = IRTemp(2, type="int")
        instr = IRInstruction(IROpcode.ADD, IRTemp(3, type="int"), [t1, t2])
        block.add_instruction(instr)
        
        program = IRProgram()
        program.add_function(func)
        
        # Validates that temp variables have types and they match roughly in operations
        for f in program.functions:
            for b in f.basic_blocks:
                for i in b.instructions:
                    if hasattr(i.dest, "type") and i.dest.type is not None:
                        # Should have type consistency across some basic ops
                        for arg in i.args:
                            if hasattr(arg, "type") and arg.type is not None:
                                self.assertEqual(i.dest.type, arg.type)

if __name__ == "__main__":
    unittest.main()
