import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

from parser.ast import (
    ProgramNode, FunctionDecl, Param, BlockStmt, VarDeclStmt,
    LiteralExpr, IdentifierExpr, BinaryExpr, ReturnStmt, ExprStmt
)
from semantic.symbol_table import SymbolTable
from semantic.analyzer import DecoratedAST
from ir.ir_instructions import IROpcode
from ir.ir_generator import IRGenerator


def _make_decorated_ast():
    return DecoratedAST(expr_types={}, symbol_refs={}, call_refs={})


class TestExpressionTranslation(unittest.TestCase):
    def _gen(self, program):
        st = SymbolTable()
        dec = _make_decorated_ast()
        gen = IRGenerator(st, dec)
        return gen.generate(program)

    def test_literal(self):
        prog = ProgramNode(1, 1, declarations=(
            FunctionDecl(1, 1, name="main", return_type="void", body=BlockStmt(1, 1, statements=(
                ReturnStmt(2, 5, value=LiteralExpr(2, 12, value=42, type_tag="int")),
            ))),
        ))
        ir = self._gen(prog)
        self.assertEqual(len(ir.functions), 1)
        entry = ir.functions[0].basic_blocks[0]
        ret_instr = [i for i in entry.instructions if i.opcode == IROpcode.RETURN]
        self.assertTrue(len(ret_instr) >= 1)

    def test_binary_add(self):
        prog = ProgramNode(1, 1, declarations=(
            FunctionDecl(1, 1, name="main", return_type="int", body=BlockStmt(1, 1, statements=(
                ReturnStmt(2, 5, value=BinaryExpr(
                    2, 12,
                    left=LiteralExpr(2, 12, value=3, type_tag="int"),
                    operator="+",
                    right=LiteralExpr(2, 16, value=4, type_tag="int"),
                )),
            ))),
        ))
        ir = self._gen(prog)
        entry = ir.functions[0].basic_blocks[0]
        add_instrs = [i for i in entry.instructions if i.opcode == IROpcode.ADD]
        self.assertEqual(len(add_instrs), 1)

    def test_binary_mul(self):
        prog = ProgramNode(1, 1, declarations=(
            FunctionDecl(1, 1, name="main", return_type="int", body=BlockStmt(1, 1, statements=(
                ReturnStmt(2, 5, value=BinaryExpr(
                    2, 12,
                    left=LiteralExpr(2, 12, value=2, type_tag="int"),
                    operator="*",
                    right=LiteralExpr(2, 16, value=5, type_tag="int"),
                )),
            ))),
        ))
        ir = self._gen(prog)
        entry = ir.functions[0].basic_blocks[0]
        mul_instrs = [i for i in entry.instructions if i.opcode == IROpcode.MUL]
        self.assertEqual(len(mul_instrs), 1)

    def test_nested_expression(self):
        prog = ProgramNode(1, 1, declarations=(
            FunctionDecl(1, 1, name="main", return_type="int", body=BlockStmt(1, 1, statements=(
                ReturnStmt(2, 5, value=BinaryExpr(
                    2, 12,
                    left=BinaryExpr(
                        2, 12,
                        left=LiteralExpr(2, 12, value=2, type_tag="int"),
                        operator="*",
                        right=LiteralExpr(2, 16, value=3, type_tag="int"),
                    ),
                    operator="+",
                    right=LiteralExpr(2, 20, value=4, type_tag="int"),
                )),
            ))),
        ))
        ir = self._gen(prog)
        entry = ir.functions[0].basic_blocks[0]
        mul_instrs = [i for i in entry.instructions if i.opcode == IROpcode.MUL]
        add_instrs = [i for i in entry.instructions if i.opcode == IROpcode.ADD]
        self.assertEqual(len(mul_instrs), 1)
        self.assertEqual(len(add_instrs), 1)

    def test_comparison(self):
        prog = ProgramNode(1, 1, declarations=(
            FunctionDecl(1, 1, name="main", return_type="int", body=BlockStmt(1, 1, statements=(
                ReturnStmt(2, 5, value=BinaryExpr(
                    2, 12,
                    left=LiteralExpr(2, 12, value=1, type_tag="int"),
                    operator="==",
                    right=LiteralExpr(2, 17, value=2, type_tag="int"),
                )),
            ))),
        ))
        ir = self._gen(prog)
        entry = ir.functions[0].basic_blocks[0]
        cmp_instrs = [i for i in entry.instructions if i.opcode == IROpcode.CMP_EQ]
        self.assertEqual(len(cmp_instrs), 1)


if __name__ == "__main__":
    unittest.main()
