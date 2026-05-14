from __future__ import annotations

from ir.ir_instructions import IROpcode


class ExpressionGenerator:
    """Helper for small expression instruction templates."""

    def __init__(self, output: list[str]) -> None:
        self.output = output

    def emit_int_binop(self, opcode: IROpcode, lhs: str, rhs: str) -> None:
        if opcode == IROpcode.ADD:
            self.output.append(f"    add {lhs}, {rhs}")
        elif opcode == IROpcode.SUB:
            self.output.append(f"    sub {lhs}, {rhs}")
        elif opcode == IROpcode.MUL:
            self.output.append(f"    imul {lhs}, {rhs}")
        elif opcode == IROpcode.AND:
            self.output.append(f"    and {lhs}, {rhs}")
        elif opcode == IROpcode.OR:
            self.output.append(f"    or {lhs}, {rhs}")
        elif opcode == IROpcode.XOR:
            self.output.append(f"    xor {lhs}, {rhs}")

    def emit_not(self, reg: str) -> None:
        self.output.append(f"    not {reg}")

    def emit_neg(self, reg: str) -> None:
        self.output.append(f"    neg {reg}")
