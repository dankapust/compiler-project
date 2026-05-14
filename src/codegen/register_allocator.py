from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ir.basic_block import IRFunction
from ir.ir_instructions import IRInstruction, IRMemory, IROperand, IRTemp

from .abi import Register


@dataclass
class LiveInterval:
    temp_id: int
    start: int
    end: int
    crosses_call: bool = False


@dataclass
class AllocationResult:
    temp_to_reg: dict[int, Register]
    spilled_temps: set[int]
    intervals: dict[int, LiveInterval]


class RegisterAllocator:
    def __init__(self):
        self.available_regs = [
            Register.R10,
            Register.R11,
        ]

    def allocate_function(self, func: IRFunction) -> AllocationResult:
        intervals = self._build_live_intervals(func)
        ordered = sorted(intervals.values(), key=lambda x: (x.start, x.end))
        active: list[tuple[LiveInterval, Register]] = []
        temp_to_reg: dict[int, Register] = {}
        spilled_temps: set[int] = set()

        for interval in ordered:
            self._expire_old(interval.start, active)
            if interval.crosses_call:
                spilled_temps.add(interval.temp_id)
                continue

            used = {reg for _, reg in active}
            free = [reg for reg in self.available_regs if reg not in used]
            if free:
                reg = free[0]
                active.append((interval, reg))
                active.sort(key=lambda item: item[0].end)
                temp_to_reg[interval.temp_id] = reg
                continue

            spill_interval, spill_reg = active[-1]
            if spill_interval.end > interval.end:
                spilled_temps.add(spill_interval.temp_id)
                del temp_to_reg[spill_interval.temp_id]
                active[-1] = (interval, spill_reg)
                active.sort(key=lambda item: item[0].end)
                temp_to_reg[interval.temp_id] = spill_reg
            else:
                spilled_temps.add(interval.temp_id)

        return AllocationResult(
            temp_to_reg=temp_to_reg,
            spilled_temps=spilled_temps,
            intervals=intervals,
        )

    def _expire_old(self, current_start: int, active: list[tuple[LiveInterval, Register]]) -> None:
        kept: list[tuple[LiveInterval, Register]] = []
        for item in active:
            if item[0].end >= current_start:
                kept.append(item)
        active[:] = kept

    def _build_live_intervals(self, func: IRFunction) -> dict[int, LiveInterval]:
        intervals: dict[int, LiveInterval] = {}
        call_positions: list[int] = []
        pos = 0
        for block in func.basic_blocks:
            for instr in block.instructions:
                if instr.opcode.value == "CALL":
                    call_positions.append(pos)
                self._touch_instruction(intervals, instr, pos)
                pos += 2
        for itv in intervals.values():
            itv.crosses_call = any(itv.start < cp < itv.end for cp in call_positions)
        return intervals

    def _touch_instruction(self, intervals: dict[int, LiveInterval], instr: IRInstruction, pos: int) -> None:
        for arg in instr.args:
            self._touch_operand(intervals, arg, pos)
        if isinstance(instr.dest, IRTemp):
            self._touch_temp(intervals, instr.dest.id, pos + 1)

    def _touch_operand(self, intervals: dict[int, LiveInterval], op: IROperand, pos: int) -> None:
        if isinstance(op, IRTemp):
            self._touch_temp(intervals, op.id, pos)
        elif isinstance(op, IRMemory):
            self._touch_operand(intervals, op.base, pos)

    def _touch_temp(self, intervals: dict[int, LiveInterval], temp_id: int, pos: int) -> None:
        current = intervals.get(temp_id)
        if current is None:
            intervals[temp_id] = LiveInterval(temp_id=temp_id, start=pos, end=pos)
            return
        if pos < current.start:
            current.start = pos
        if pos > current.end:
            current.end = pos
