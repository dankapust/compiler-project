import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))

from tests.ir.golden_runner import compile_to_ir_text


def test_short_circuit_and_uses_branches():
    source = """
    fn rhs() -> bool { return true; }
    fn main() -> int {
        bool a = false;
        if (a && rhs()) { return 1; }
        return 0;
    }
    """
    ir_text = compile_to_ir_text(source)
    assert "L_sc_rhs" in ir_text
    assert "JUMP_IF" in ir_text
    assert "CALL rhs" in ir_text


def test_short_circuit_or_uses_branches():
    source = """
    fn rhs() -> bool { return false; }
    fn main() -> int {
        bool a = true;
        if (a || rhs()) { return 1; }
        return 0;
    }
    """
    ir_text = compile_to_ir_text(source)
    assert "L_sc_short" in ir_text
    assert "JUMP_IF" in ir_text
    assert "CALL rhs" in ir_text


def test_break_continue_and_switch_emit_jumps():
    source = """
    fn main() -> int {
        int i = 0;
        while (i < 10) {
            i += 1;
            if (i == 2) { continue; }
            if (i == 5) { break; }
        }
        switch (i) {
            case 5:
                return 5;
            default:
                return 0;
        }
    }
    """
    ir_text = compile_to_ir_text(source)
    assert "L_while_cond" in ir_text
    assert "L_switch_case" in ir_text
    assert "L_switch_end" in ir_text
    assert "JUMP " in ir_text
