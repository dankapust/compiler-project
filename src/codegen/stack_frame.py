from typing import Dict, Optional
from .abi import Register, INTEGER_PARAM_REGISTERS


class StackFrame:
    def __init__(self, func_name: str):
        self.func_name = func_name
        self.local_offsets: Dict[str, int] = {}
        self.temp_offsets: Dict[int, int] = {}
        self.param_offsets: Dict[int, int] = {}
        self.next_offset = 0
        self.stack_size = 0

    def allocate_local(self, name: str, size: int = 8) -> int:
        if name not in self.local_offsets:
            self.next_offset -= size
            self.local_offsets[name] = self.next_offset
        return self.local_offsets[name]

    def allocate_temp(self, temp_id: int, size: int = 8) -> int:
        if temp_id not in self.temp_offsets:
            self.next_offset -= size
            self.temp_offsets[temp_id] = self.next_offset
        return self.temp_offsets[temp_id]

    def allocate_param(self, index: int, size: int = 8) -> int:

        if index < 6:

            if index not in self.param_offsets:
                self.next_offset -= size
                self.param_offsets[index] = self.next_offset
            return self.param_offsets[index]
        else:

            offset = 16 + (index - 6) * 8
            self.param_offsets[index] = offset
            return offset

    def finalize(self) -> int:







        self.stack_size = (-self.next_offset + 15) // 16 * 16
        return self.stack_size

    def get_offset(self, operand_name: str) -> Optional[int]:
        return self.local_offsets.get(operand_name)

    def get_temp_offset(self, temp_id: int) -> Optional[int]:
        return self.temp_offsets.get(temp_id)
