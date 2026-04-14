import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from parser.ast import (
    ProgramNode, FunctionDecl, BlockStmt, IfStmt, WhileStmt,
    BinaryExpr, LiteralExpr, IdentifierExpr, ReturnStmt,
    VarDeclStmt, ExprStmt, AssignmentExpr
)
from semantic.symbol_table import SymbolTable
from semantic.analyzer import DecoratedAST
from ir.ir_instructions import IROpcode
from ir.ir_generator import IRGenerator


def _make_decorated_ast():
    return DecoratedAST(expr_types={}, symbol_refs={}, call_refs={})


class TestControlFlowTranslation(unittest.TestCase):
    def _gen(self, program):
        st = SymbolTable()
        dec = _make_decorated_ast()
        gen = IRGenerator(st, dec)
        return gen.generate(program)

    def test_if_then(self):
        prog = ProgramNode(1, 1, declarations=(
            FunctionDecl(1, 1, name="main", return_type="void", body=BlockStmt(1, 1, statements=(
                IfStmt(2, 5,
                    condition=LiteralExpr(2, 9, value=1, type_tag="int"),
                    then_branch=BlockStmt(2, 12, statements=(
                        ReturnStmt(3, 9, value=LiteralExpr(3, 16, value=1, type_tag="int")),
                    )),
                ),
            ))),
        ))
        ir = self._gen(prog)
        func = ir.functions[0]
        self.assertTrue(len(func.basic_blocks) >= 3)
        entry = func.basic_blocks[0]
        jump_if_instrs = [i for i in entry.instructions if i.opcode == IROpcode.JUMP_IF]
        self.assertTrue(len(jump_if_instrs) >= 1)

    def test_if_then_else(self):
        prog = ProgramNode(1, 1, declarations=(
            FunctionDecl(1, 1, name="main", return_type="void", body=BlockStmt(1, 1, statements=(
                IfStmt(2, 5,
                    condition=LiteralExpr(2, 9, value=1, type_tag="int"),
                    then_branch=BlockStmt(2, 12, statements=(
                        ReturnStmt(3, 9, value=LiteralExpr(3, 16, value=1, type_tag="int")),
                    )),
                    else_branch=BlockStmt(4, 12, statements=(
                        ReturnStmt(5, 9, value=LiteralExpr(5, 16, value=2, type_tag="int")),
                    )),
                ),
            ))),
        ))
        ir = self._gen(prog)
        func = ir.functions[0]
        self.assertTrue(len(func.basic_blocks) >= 4)

    def test_while_loop(self):
        prog = ProgramNode(1, 1, declarations=(
            FunctionDecl(1, 1, name="main", return_type="void", body=BlockStmt(1, 1, statements=(
                WhileStmt(2, 5,
                    condition=LiteralExpr(2, 12, value=1, type_tag="int"),
                    body=BlockStmt(2, 15, statements=()),
                ),
            ))),
        ))
        ir = self._gen(prog)
        func = ir.functions[0]
        self.assertTrue(len(func.basic_blocks) >= 4)

        all_instrs = []
        for block in func.basic_blocks:
            all_instrs.extend(block.instructions)
        jump_instrs = [i for i in all_instrs if i.opcode in (IROpcode.JUMP, IROpcode.JUMP_IF)]
        self.assertTrue(len(jump_instrs) >= 3)

    def test_basic_block_successors(self):
        prog = ProgramNode(1, 1, declarations=(
            FunctionDecl(1, 1, name="main", return_type="void", body=BlockStmt(1, 1, statements=(
                IfStmt(2, 5,
                    condition=LiteralExpr(2, 9, value=1, type_tag="int"),
                    then_branch=BlockStmt(2, 12, statements=()),
                ),
            ))),
        ))
        ir = self._gen(prog)
        func = ir.functions[0]
        entry = func.entry_block
        self.assertTrue(len(entry.successors) >= 1)


if __name__ == "__main__":
    unittest.main()
