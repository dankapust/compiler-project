import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))

from parser.ast import (
    ProgramNode, FunctionDecl, Param, BlockStmt, CallExpr,
    LiteralExpr, ReturnStmt, ExprStmt
)
from semantic.symbol_table import SymbolTable
from semantic.analyzer import DecoratedAST
from ir.ir_instructions import IROpcode
from ir.ir_generator import IRGenerator


def _make_decorated_ast():
    return DecoratedAST(program=None, expr_types={}, folded_constants={}, symbol_refs={}, call_refs={})


class TestFunctionTranslation(unittest.TestCase):
    def _gen(self, program):
        st = SymbolTable()
        dec = _make_decorated_ast()
        gen = IRGenerator(st, dec)
        return gen.generate(program)

    def test_function_with_params(self):
        prog = ProgramNode(1, 1, declarations=(
            FunctionDecl(1, 1, name="add", return_type="int",
                params=(Param(1, 9, param_type="int", name="a"), Param(1, 16, param_type="int", name="b")),
                body=BlockStmt(1, 25, statements=(
                    ReturnStmt(2, 5, value=LiteralExpr(2, 12, value=0, type_tag="int")),
                )),
            ),
        ))
        ir = self._gen(prog)
        func = ir.functions[0]
        self.assertEqual(func.name, "add")
        self.assertEqual(func.return_type, "int")
        self.assertEqual(len(func.params), 2)

        entry = func.entry_block
        store_instrs = [i for i in entry.instructions if i.opcode == IROpcode.STORE]
        self.assertTrue(len(store_instrs) >= 2)

    def test_function_call(self):
        prog = ProgramNode(1, 1, declarations=(
            FunctionDecl(1, 1, name="main", return_type="void", body=BlockStmt(1, 1, statements=(
                ExprStmt(2, 5, expression=CallExpr(2, 5, callee="foo", arguments=(
                    LiteralExpr(2, 9, value=1, type_tag="int"),
                    LiteralExpr(2, 12, value=2, type_tag="int"),
                ))),
            ))),
        ))
        ir = self._gen(prog)
        entry = ir.functions[0].basic_blocks[0]

        param_instrs = [i for i in entry.instructions if i.opcode == IROpcode.PARAM]
        self.assertEqual(len(param_instrs), 2)

        call_instrs = [i for i in entry.instructions if i.opcode == IROpcode.CALL]
        self.assertEqual(len(call_instrs), 1)

    def test_multiple_functions(self):
        prog = ProgramNode(1, 1, declarations=(
            FunctionDecl(1, 1, name="foo", return_type="void", body=BlockStmt(1, 1, statements=())),
            FunctionDecl(5, 1, name="bar", return_type="int", body=BlockStmt(5, 1, statements=(
                ReturnStmt(6, 5, value=LiteralExpr(6, 12, value=0, type_tag="int")),
            ))),
        ))
        ir = self._gen(prog)
        self.assertEqual(len(ir.functions), 2)
        self.assertEqual(ir.functions[0].name, "foo")
        self.assertEqual(ir.functions[1].name, "bar")

    def test_get_function_ir(self):
        prog = ProgramNode(1, 1, declarations=(
            FunctionDecl(1, 1, name="main", return_type="void", body=BlockStmt(1, 1, statements=())),
        ))
        st = SymbolTable()
        dec = _make_decorated_ast()
        gen = IRGenerator(st, dec)
        gen.generate(prog)
        self.assertIsNotNone(gen.get_function_ir("main"))
        self.assertIsNone(gen.get_function_ir("nonexistent"))

    def test_return_void(self):
        prog = ProgramNode(1, 1, declarations=(
            FunctionDecl(1, 1, name="main", return_type="void", body=BlockStmt(1, 1, statements=(
                ReturnStmt(2, 5, value=None),
            ))),
        ))
        ir = self._gen(prog)
        entry = ir.functions[0].basic_blocks[0]
        ret_instrs = [i for i in entry.instructions if i.opcode == IROpcode.RETURN]
        self.assertEqual(len(ret_instrs), 1)
        self.assertEqual(len(ret_instrs[0].args), 0)


if __name__ == "__main__":
    unittest.main()
