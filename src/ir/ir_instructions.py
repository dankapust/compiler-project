from dataclasses import dataclass
from enum import Enum
from typing import Any


class IROpcode(Enum):
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    MOD = "MOD"
    NEG = "NEG"

    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    XOR = "XOR"

    CMP_EQ = "CMP_EQ"
    CMP_NE = "CMP_NE"
    CMP_LT = "CMP_LT"
    CMP_LE = "CMP_LE"
    CMP_GT = "CMP_GT"
    CMP_GE = "CMP_GE"

    LOAD = "LOAD"
    STORE = "STORE"
    ALLOCA = "ALLOCA"
    GEP = "GEP"

    JUMP = "JUMP"
    JUMP_IF = "JUMP_IF"
    JUMP_IF_NOT = "JUMP_IF_NOT"
    LABEL = "LABEL"
    PHI = "PHI"

    CALL = "CALL"
    RETURN = "RETURN"
    PARAM = "PARAM"


@dataclass
class IROperand:
    def format(self) -> str:
        raise NotImplementedError


@dataclass
class IRTemp(IROperand):
    id: int
    type: str | None = None

    def format(self) -> str:
        t_info = f":{self.type}" if self.type else ""
        return f"t{self.id}{t_info}"


@dataclass
class IRLiteral(IROperand):
    value: Any

    def format(self) -> str:
        if isinstance(self.value, bool):
            return "true" if self.value else "false"
        return str(self.value)


@dataclass
class IRVar(IROperand):
    name: str

    def format(self) -> str:
        return self.name


@dataclass
class IRLabel(IROperand):
    name: str

    def format(self) -> str:
        return self.name


@dataclass
class IRMemory(IROperand):
    base: IROperand

    def format(self) -> str:
        return f"[{self.base.format()}]"


@dataclass
class IRPhiParam:
    value: IROperand
    block_label: IRLabel

    def format(self) -> str:
        return f"({self.value.format()}, {self.block_label.format()})"


@dataclass
class IRInstruction:
    opcode: IROpcode
    dest: IROperand | None = None
    args: list[IROperand | IRPhiParam] = None

    def __post_init__(self):
        if self.args is None:
            self.args = []

    def format(self) -> str:
        parts = []
        if self.dest:
            parts.append(f"{self.dest.format()} =")

        parts.append(self.opcode.value)
        args_str = ", ".join(arg.format() for arg in self.args)
        if args_str:
            parts.append(args_str)

        return " ".join(parts)
