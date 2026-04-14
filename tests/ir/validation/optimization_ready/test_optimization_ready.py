import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))

from ir.control_flow import PeepholeOptimizer
from ir.basic_block import IRProgram

class TestOptimizationReady(unittest.TestCase):
    def test_optimizer_init(self):
        program = IRProgram()
        opt = PeepholeOptimizer(program)
        
        # Check optimization level interfaces
        optimized_program = opt.optimize()
        report = opt.get_optimization_report()
        
        self.assertIsInstance(optimized_program, IRProgram)
        self.assertIsInstance(report, list)

if __name__ == "__main__":
    unittest.main()
