from __future__ import annotations
from dataclasses import dataclass, field
from .ir_instructions import IRInstruction


@dataclass
class BasicBlock:
    label: str
    instructions: list[IRInstruction] = field(default_factory=list)
    predecessors: list[BasicBlock] = field(default_factory=list)
    successors: list[BasicBlock] = field(default_factory=list)

    def add_instruction(self, instruction: IRInstruction) -> None:
        self.instructions.append(instruction)

    def add_successor(self, block: BasicBlock) -> None:
        if block not in self.successors:
            self.successors.append(block)
        if self not in block.predecessors:
            block.predecessors.append(self)

    def __hash__(self):
        return hash(self.label)

    def __eq__(self, other):
        if not isinstance(other, BasicBlock):
            return NotImplemented
        return self.label == other.label


@dataclass
class IRFunction:
    name: str
    return_type: str
    params: list[tuple[str, str]]
    basic_blocks: list[BasicBlock] = field(default_factory=list)
    entry_block: BasicBlock | None = None
    exit_block: BasicBlock | None = None

    def add_block(self, block: BasicBlock) -> None:
        self.basic_blocks.append(block)


@dataclass
class IRProgram:
    functions: list[IRFunction] = field(default_factory=list)
    globals: list[str] = field(default_factory=list)

    def add_function(self, func: IRFunction) -> None:
        self.functions.append(func)
