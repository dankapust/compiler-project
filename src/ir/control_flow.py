from __future__ import annotations
from .ir_instructions import IROpcode, IRInstruction, IRLiteral, IRTemp
from .basic_block import IRProgram, IRFunction, BasicBlock


class PeepholeOptimizer:
    def __init__(self, program: IRProgram):
        self.program = program
        self._changes: list[str] = []

    def optimize(self) -> IRProgram:
        for func in self.program.functions:
            for block in func.basic_blocks:
                changed = True
                while changed:
                    changed = False
                    changed |= self._algebraic_simplify(block)
                    changed |= self._constant_fold(block)
                    changed |= self._strength_reduce(block)
                    changed |= self._dead_code_eliminate(block, func)
                self._jump_chain(func)
        return self.program

    def get_optimization_report(self) -> list[str]:
        return list(self._changes)

    def _is_literal(self, op, value) -> bool:
        return isinstance(op, IRLiteral) and op.value == value

    def _algebraic_simplify(self, block: BasicBlock) -> bool:
        changed = False
        new_instrs = []
        for instr in block.instructions:
            if instr.opcode == IROpcode.ADD and len(instr.args) == 2:
                if self._is_literal(instr.args[1], 0):
                    new_instrs.append(IRInstruction(IROpcode.ADD, instr.dest, [instr.args[0], IRLiteral(0)]))
                    new_instrs[-1] = IRInstruction(IROpcode.LOAD, instr.dest, [instr.args[0]])
                    self._changes.append(f"x + 0 -> x at {instr.dest}")
                    changed = True
                    continue
                if self._is_literal(instr.args[0], 0):
                    new_instrs.append(IRInstruction(IROpcode.LOAD, instr.dest, [instr.args[1]]))
                    self._changes.append(f"0 + x -> x at {instr.dest}")
                    changed = True
                    continue
            if instr.opcode == IROpcode.MUL and len(instr.args) == 2:
                if self._is_literal(instr.args[1], 1):
                    new_instrs.append(IRInstruction(IROpcode.LOAD, instr.dest, [instr.args[0]]))
                    self._changes.append(f"x * 1 -> x at {instr.dest}")
                    changed = True
                    continue
                if self._is_literal(instr.args[0], 1):
                    new_instrs.append(IRInstruction(IROpcode.LOAD, instr.dest, [instr.args[1]]))
                    self._changes.append(f"1 * x -> x at {instr.dest}")
                    changed = True
                    continue
                if self._is_literal(instr.args[1], 0) or self._is_literal(instr.args[0], 0):
                    new_instrs.append(IRInstruction(IROpcode.LOAD, instr.dest, [IRLiteral(0)]))
                    self._changes.append(f"x * 0 -> 0 at {instr.dest}")
                    changed = True
                    continue
            if instr.opcode == IROpcode.SUB and len(instr.args) == 2:
                if self._is_literal(instr.args[1], 0):
                    new_instrs.append(IRInstruction(IROpcode.LOAD, instr.dest, [instr.args[0]]))
                    self._changes.append(f"x - 0 -> x at {instr.dest}")
                    changed = True
                    continue
            new_instrs.append(instr)
        block.instructions = new_instrs
        return changed

    def _constant_fold(self, block: BasicBlock) -> bool:
        changed = False
        new_instrs = []
        for instr in block.instructions:
            if instr.dest and len(instr.args) == 2:
                a, b = instr.args
                if isinstance(a, IRLiteral) and isinstance(b, IRLiteral):
                    result = self._eval_op(instr.opcode, a.value, b.value)
                    if result is not None:
                        new_instrs.append(IRInstruction(IROpcode.LOAD, instr.dest, [IRLiteral(result)]))
                        self._changes.append(f"constant fold {a.value} {instr.opcode.value} {b.value} -> {result}")
                        changed = True
                        continue
            new_instrs.append(instr)
        block.instructions = new_instrs
        return changed

    def _eval_op(self, opcode: IROpcode, a, b):
        try:
            if opcode == IROpcode.ADD:
                return a + b
            if opcode == IROpcode.SUB:
                return a - b
            if opcode == IROpcode.MUL:
                return a * b
            if opcode == IROpcode.DIV and b != 0:
                return a // b if isinstance(a, int) and isinstance(b, int) else a / b
            if opcode == IROpcode.MOD and b != 0:
                return a % b
            if opcode == IROpcode.CMP_EQ:
                return int(a == b)
            if opcode == IROpcode.CMP_NE:
                return int(a != b)
            if opcode == IROpcode.CMP_LT:
                return int(a < b)
            if opcode == IROpcode.CMP_LE:
                return int(a <= b)
            if opcode == IROpcode.CMP_GT:
                return int(a > b)
            if opcode == IROpcode.CMP_GE:
                return int(a >= b)
        except (TypeError, ZeroDivisionError):
            pass
        return None

    def _strength_reduce(self, block: BasicBlock) -> bool:
        changed = False
        new_instrs = []
        for instr in block.instructions:
            if instr.opcode == IROpcode.MUL and len(instr.args) == 2:
                if self._is_literal(instr.args[1], 2):
                    new_instrs.append(IRInstruction(IROpcode.ADD, instr.dest, [instr.args[0], instr.args[0]]))
                    self._changes.append(f"x * 2 -> x + x at {instr.dest}")
                    changed = True
                    continue
                if self._is_literal(instr.args[0], 2):
                    new_instrs.append(IRInstruction(IROpcode.ADD, instr.dest, [instr.args[1], instr.args[1]]))
                    self._changes.append(f"2 * x -> x + x at {instr.dest}")
                    changed = True
                    continue
            new_instrs.append(instr)
        block.instructions = new_instrs
        return changed

    def _dead_code_eliminate(self, block: BasicBlock, func: IRFunction) -> bool:
        used_temps: set[int] = set()
        for b in func.basic_blocks:
            for instr in b.instructions:
                for arg in instr.args:
                    if isinstance(arg, IRTemp):
                        used_temps.add(arg.id)

        changed = False
        new_instrs = []
        for instr in block.instructions:
            if (instr.dest and isinstance(instr.dest, IRTemp)
                    and instr.dest.id not in used_temps
                    and instr.opcode not in (
                        IROpcode.CALL, IROpcode.STORE, IROpcode.RETURN,
                        IROpcode.JUMP, IROpcode.JUMP_IF, IROpcode.JUMP_IF_NOT)):
                self._changes.append(f"dead code: removed {instr.format()}")
                changed = True
                continue
            new_instrs.append(instr)
        block.instructions = new_instrs
        return changed

    def _jump_chain(self, func: IRFunction) -> None:
        label_map: dict[str, str] = {}
        for block in func.basic_blocks:
            if (len(block.instructions) == 1
                    and block.instructions[0].opcode == IROpcode.JUMP
                    and block.instructions[0].args):
                from .ir_instructions import IRLabel as _IRLabel
                target = block.instructions[0].args[0]
                if isinstance(target, _IRLabel):
                    label_map[block.label] = target.name

        if not label_map:
            return

        def resolve(label: str) -> str:
            visited = set()
            while label in label_map and label not in visited:
                visited.add(label)
                label = label_map[label]
            return label

        for block in func.basic_blocks:
            for instr in block.instructions:
                if instr.opcode in (IROpcode.JUMP, IROpcode.JUMP_IF, IROpcode.JUMP_IF_NOT):
                    for i, arg in enumerate(instr.args):
                        from .ir_instructions import IRLabel as _IRLabel
                        if isinstance(arg, _IRLabel) and arg.name in label_map:
                            old = arg.name
                            new = resolve(arg.name)
                            instr.args[i] = _IRLabel(new)
                            self._changes.append(f"jump chain: {old} -> {new}")
