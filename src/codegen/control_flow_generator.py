from __future__ import annotations

from ir.ir_instructions import IRLabel


class ControlFlowGenerator:
    """Small helper for branch/jump emission."""

    def __init__(self, output: list[str]) -> None:
        self.output = output

    def emit_jump(self, target: IRLabel | str) -> None:
        name = target.name if isinstance(target, IRLabel) else str(target)
        self.output.append(f"    jmp {name}")

    def emit_jump_if_nonzero(self, cond_reg: str, target: IRLabel | str) -> None:
        name = target.name if isinstance(target, IRLabel) else str(target)
        self.output.append(f"    cmp {cond_reg}, 0")
        self.output.append(f"    jne {name}")

    def emit_jump_if_zero(self, cond_reg: str, target: IRLabel | str) -> None:
        name = target.name if isinstance(target, IRLabel) else str(target)
        self.output.append(f"    cmp {cond_reg}, 0")
        self.output.append(f"    je {name}")
