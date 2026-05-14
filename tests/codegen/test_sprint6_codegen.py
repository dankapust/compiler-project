from tests.codegen.test_x86_generation import compile_to_asm
from ir.basic_block import BasicBlock, IRFunction, IRProgram
from ir.ir_instructions import IRInstruction, IROpcode, IRLabel, IRTemp
from codegen.x86_generator import X86Generator


def test_short_circuit_generates_conditional_jumps():
    source = """
    fn rhs() -> bool { return true; }
    fn main() -> int {
        bool a = false;
        if (a && rhs()) { return 1; }
        return 0;
    }
    """
    asm = compile_to_asm(source)
    assert "jne" in asm or "je" in asm
    assert "call rhs" in asm
    assert "setg" not in asm
    assert "setl" not in asm


def test_switch_codegen_has_case_labels_and_jumps():
    source = """
    fn main() -> int {
        int x = 2;
        switch (x) {
            case 1:
                return 11;
            case 2:
                return 22;
            default:
                return 0;
        }
    }
    """
    asm = compile_to_asm(source)
    assert "cmp" in asm
    assert "jne" in asm or "je" in asm
    assert "ret" in asm


def test_unsigned_pointer_compare_uses_jb():
    entry = BasicBlock("entry_main_1")
    exit_block = BasicBlock("exit_main_2")
    t1 = IRTemp(1, type="*")
    t2 = IRTemp(2, type="*")
    t3 = IRTemp(3, type="bool")
    entry.instructions = [
        IRInstruction(IROpcode.CMP_LT, t3, [t1, t2]),
        IRInstruction(IROpcode.JUMP_IF, None, [t3, IRLabel("L_then_3")]),
        IRInstruction(IROpcode.JUMP, None, [IRLabel("exit_main_2")]),
    ]
    fn = IRFunction("main", "int", [], [entry, exit_block], entry, exit_block)
    prog = IRProgram(functions=[fn])
    asm = X86Generator(prog).generate()
    assert " jb " in f" {asm} "
