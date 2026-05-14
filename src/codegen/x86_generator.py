import struct
from typing import Dict, List, Optional
from ir.ir_instructions import IRInstruction, IROpcode, IRTemp, IRLiteral, IRVar, IRLabel, IRMemory, IROperand
from ir.basic_block import IRProgram, IRFunction, BasicBlock
from .abi import INTEGER_PARAM_REGISTERS
from .stack_frame import StackFrame
from .register_allocator import RegisterAllocator
from .control_flow_generator import ControlFlowGenerator
from .expression_generator import ExpressionGenerator
from .label_manager import LabelManager


class X86Generator:
    def __init__(self, program: IRProgram):
        self.program = program
        self.output: List[str] = []
        self.current_frame: Optional[StackFrame] = None
        self.string_literals: Dict[str, str] = {}
        self.string_count = 0
        self.is_leaf = False

        self._pending_stack_arg_bytes = 0
        self._temp_to_reg: Dict[int, str] = {}
        self._spilled_temps: set[int] = set()
        self._last_cmp_temp_id: int | None = None
        self._last_cmp_opcode: IROpcode | None = None
        self._last_cmp_unsigned: bool = False
        self.label_manager = LabelManager()
        self.control_flow = ControlFlowGenerator(self.output)
        self.expr_gen = ExpressionGenerator(self.output)

    def generate(self) -> str:
        self.output.append("bits 64")
        self.output.append("")


        self._collect_data()


        self.output.append("section .text")


        self.output.append("extern print_int")
        self.output.append("extern print_string")
        self.output.append("extern read_int")
        self.output.append("extern exit")
        self.output.append("")

        for func in self.program.functions:
            self._generate_function(func)


        self._generate_data_sections()

        return "\n".join(self.output)

    def _collect_data(self):

        for func in self.program.functions:
            for block in func.basic_blocks:
                for instr in block.instructions:
                    for arg in instr.args:
                        if isinstance(arg, IRLiteral) and isinstance(arg.value, str):
                            if arg.value not in self.string_literals:
                                label = f".L.str{self.string_count}"
                                self.string_literals[arg.value] = label
                                self.string_count += 1

    def _generate_function(self, func: IRFunction):
        self.output.append(f"global {func.name}")
        self.output.append(f"{func.name}:")


        self.current_frame = StackFrame(func.name)
        alloc = RegisterAllocator().allocate_function(func)
        self._temp_to_reg = {tid: reg.value for tid, reg in alloc.temp_to_reg.items()}
        self._spilled_temps = set(alloc.spilled_temps)
        for i in range(len(func.params)):
            self._temp_to_reg.pop(i, None)
            self._spilled_temps.add(i)



        for i, (p_type, p_name) in enumerate(func.params):
            offset = self.current_frame.allocate_param(i)

            self.current_frame.local_offsets[p_name] = offset

            self.current_frame.temp_offsets[i] = offset


        gsyms = self.program.global_symbol_names()

        def collect_vars(op):
            if isinstance(op, IRVar):
                if op.name in gsyms:
                    return
                sz = self.program.slot_sizes.get(op.name, 8)
                self.current_frame.allocate_local(op.name, sz)
            elif isinstance(op, IRTemp):
                self.current_frame.allocate_temp(op.id)
            elif isinstance(op, IRMemory):
                collect_vars(op.base)

        for block in func.basic_blocks:
            for instr in block.instructions:
                if instr.dest:
                    collect_vars(instr.dest)
                for arg in instr.args:
                    collect_vars(arg)


        self.is_leaf = True
        for block in func.basic_blocks:
            for instr in block.instructions:
                if instr.opcode == IROpcode.CALL:
                    self.is_leaf = False
                    break
            if not self.is_leaf:
                break

        stack_size = self.current_frame.finalize()
        self._pending_stack_arg_bytes = 0


        self.output.append("    push rbp")
        self.output.append("    mov rbp, rsp")




        use_red_zone = self.is_leaf and stack_size <= 128
        if stack_size > 0 and not use_red_zone:
            self.output.append(f"    sub rsp, {stack_size}")


        for i, (p_type, p_name) in enumerate(func.params):
            if p_type == "float":
                if i < 8:
                    reg = f"xmm{i}"
                    offset = self.current_frame.param_offsets[i]
                    self.output.append(f"    movss [rbp{offset:+d}], {reg}")
            else:
                if i < len(INTEGER_PARAM_REGISTERS):
                    reg = INTEGER_PARAM_REGISTERS[i].value
                    offset = self.current_frame.param_offsets[i]
                    self.output.append(f"    mov [rbp{offset:+d}], {reg}")
                else:

                    continue


        referenced_labels = set()
        for block in func.basic_blocks:
            for instr in block.instructions:
                if instr.opcode in (IROpcode.JUMP, IROpcode.JUMP_IF, IROpcode.JUMP_IF_NOT) and len(instr.args) >= 1:
                    for arg in instr.args:
                        if isinstance(arg, IRLabel):
                            referenced_labels.add(arg.name)
                if instr.opcode in (IROpcode.RETURN, IROpcode.JUMP):
                    # Ignore unreachable IR that may appear after a terminator.
                    break

        for i, block in enumerate(func.basic_blocks):
            if not block.instructions and i != 0 and block.label not in referenced_labels:
                continue

            self.output.append(f"{block.label}:")
            for idx, instr in enumerate(block.instructions):
                next_instr = block.instructions[idx + 1] if idx + 1 < len(block.instructions) else None
                self._generate_instruction(instr, next_instr=next_instr)
                if instr.opcode in (IROpcode.RETURN, IROpcode.JUMP):
                    # Control flow terminators end the block; remaining IR is unreachable.
                    break

        self.output.append("")

    def _generate_instruction(self, instr: IRInstruction, next_instr: IRInstruction | None = None):
        opcode = instr.opcode
        dest = instr.dest
        args = instr.args

        if opcode not in (IROpcode.JUMP_IF, IROpcode.JUMP_IF_NOT):
            self._last_cmp_temp_id = None
            self._last_cmp_opcode = None
            self._last_cmp_unsigned = False

        if opcode == IROpcode.STORE:

            src_val = self._resolve_operand(args[0], "rax")

            if isinstance(dest, IRVar):
                offset = self.current_frame.get_offset(dest.name)
                self.output.append(f"    mov [rbp{offset:+d}], {src_val}")
            elif isinstance(dest, IRMemory):
                if isinstance(dest.base, IRTemp):
                    addr_reg = self._resolve_operand(dest.base, "r10", force_reg=True)
                    self._store_scalar_at_addr_register(addr_reg, args[0])
                    return

                if isinstance(dest.base, IRVar):

                    offset = self.current_frame.get_offset(dest.base.name)
                    if offset is not None:
                        if isinstance(args[0], IRTemp) and args[0].type == "int":
                            self._resolve_operand(args[0], "rax", force_reg=True)
                            self.output.append(f"    mov dword [rbp{offset:+d}], eax")
                            return
                        if isinstance(args[0], IRTemp) and args[0].type == "float":
                            self._resolve_operand(args[0], "xmm0", force_reg=True)
                            self.output.append(f"    movss dword [rbp{offset:+d}], xmm0")
                            return
                        if isinstance(args[0], IRTemp) and args[0].type == "bool":
                            self._resolve_operand(args[0], "rax", force_reg=True)
                            self.output.append(f"    mov byte [rbp{offset:+d}], al")
                            return

                        if src_val.startswith("[") or src_val.isdigit():
                            self.output.append(f"    mov rax, {src_val}")
                            src_val = "rax"
                        self.output.append(f"    mov [rbp{offset:+d}], {src_val}")
                    else:

                        gname = dest.base.name
                        if isinstance(args[0], IRTemp) and args[0].type == "int":
                            self._resolve_operand(args[0], "rax", force_reg=True)
                            self.output.append(f"    mov dword [{gname}], eax")
                            return
                        if isinstance(args[0], IRTemp) and args[0].type == "float":
                            self._resolve_operand(args[0], "xmm0", force_reg=True)
                            self.output.append(f"    movss dword [{gname}], xmm0")
                            return
                        if isinstance(args[0], IRTemp) and args[0].type == "bool":
                            self._resolve_operand(args[0], "rax", force_reg=True)
                            self.output.append(f"    mov byte [{gname}], al")
                            return
                        if src_val.startswith("[") or src_val.isdigit():
                            self.output.append(f"    mov rax, {src_val}")
                            src_val = "rax"
                        self.output.append(f"    mov [{gname}], {src_val}")
                else:

                    addr_reg = self._resolve_operand(dest.base, "r10", force_reg=True)
                    if isinstance(args[0], IRTemp) and args[0].type == "float":
                        self._resolve_operand(args[0], "xmm0", force_reg=True)
                        self.output.append(f"    movss dword [{addr_reg}], xmm0")
                    elif isinstance(args[0], IRTemp) and args[0].type == "int":
                        self._resolve_operand(args[0], "rax", force_reg=True)
                        self.output.append(f"    mov dword [{addr_reg}], eax")
                    elif isinstance(args[0], IRTemp) and args[0].type == "bool":
                        self._resolve_operand(args[0], "rax", force_reg=True)
                        self.output.append(f"    mov byte [{addr_reg}], al")
                    else:
                        if src_val.startswith("[") or src_val.isdigit():
                            self.output.append(f"    mov rax, {src_val}")
                            src_val = "rax"
                        self.output.append(f"    mov qword [{addr_reg}], {src_val}")
            elif isinstance(dest, IRTemp):
                self._store_temp_from_value(dest, src_val)

        elif opcode == IROpcode.LOAD:

            src_arg = args[0]
            if isinstance(dest, IRTemp):
                offset = self.current_frame.get_temp_offset(dest.id)
                if isinstance(src_arg, IRMemory):
                    if isinstance(src_arg.base, IRTemp):
                        addr_reg = self._resolve_operand(src_arg.base, "r10", force_reg=True)
                        self._load_scalar_from_address(addr_reg, dest, offset)
                        return
                    if isinstance(src_arg.base, IRVar):
                        loff = self.current_frame.get_offset(src_arg.base.name)
                        if loff is not None:
                            self._load_scalar_from_rbp_offset(loff, dest, offset)
                            return
                        self._load_scalar_from_global_symbol(src_arg.base.name, dest, offset)
                        return
                src_val = self._resolve_operand(src_arg, "rax")
                if src_val.startswith("["):
                    self.output.append(f"    mov rax, {src_val}")
                    src_val = "rax"
                self.output.append(f"    mov [rbp{offset:+d}], {src_val}")

        elif opcode == IROpcode.GEP:
            off_raw = args[1]
            if isinstance(off_raw, IRLiteral) and isinstance(off_raw.value, int):
                extra = off_raw.value
            else:
                extra = 0
            base_arg = args[0]
            if isinstance(base_arg, IRMemory) and isinstance(base_arg.base, IRVar):
                base_off = self.current_frame.get_offset(base_arg.base.name)
                if base_off is not None:
                    self.output.append(f"    lea rax, [rbp{base_off:+d}]")
                else:
                    gnm = base_arg.base.name
                    self.output.append(f"    lea rax, [{gnm}]")
            elif isinstance(base_arg, IRTemp):
                self._resolve_operand(base_arg, "rax", force_reg=True)
            else:
                self.output.append("    xor eax, eax")
            if extra != 0:
                self.output.append(f"    add rax, {extra}")
            if isinstance(dest, IRTemp):
                self._store_temp_from_gpr(dest, "rax")

        elif opcode == IROpcode.MOD:
            self._resolve_operand(args[0], "rax", force_reg=True)
            divr = self._resolve_operand(args[1], "rcx", force_reg=True)
            self.output.append("    cqo")
            self.output.append(f"    idiv {divr}")
            if isinstance(dest, IRTemp):
                self._store_temp_from_gpr(dest, "rdx")

        elif opcode in (IROpcode.ADD, IROpcode.SUB, IROpcode.MUL, IROpcode.DIV, IROpcode.AND, IROpcode.OR, IROpcode.XOR):
            is_float = self._is_float(dest) or self._is_float(args[0])

            if is_float:
                lhs = self._resolve_operand(args[0], "xmm0", force_reg=True)
                rhs = self._resolve_operand(args[1], "xmm1", force_reg=True)
                if opcode == IROpcode.ADD: self.output.append("    addss xmm0, xmm1")
                elif opcode == IROpcode.SUB: self.output.append("    subss xmm0, xmm1")
                elif opcode == IROpcode.MUL: self.output.append("    mulss xmm0, xmm1")
                elif opcode == IROpcode.DIV: self.output.append("    divss xmm0, xmm1")

                if isinstance(dest, IRTemp):
                    offset = self.current_frame.get_temp_offset(dest.id)
                    self.output.append(f"    movss [rbp{offset:+d}], xmm0")
            else:
                lhs = self._resolve_operand(args[0], "rax", force_reg=True)
                rhs = self._resolve_operand(args[1], "rcx")

                if opcode == IROpcode.DIV:

                    if not rhs.startswith("r") and not rhs.startswith("e"):
                        self.output.append(f"    mov rcx, {rhs}")
                        rhs = "rcx"
                    self.output.append("    cqo")
                    self.output.append(f"    idiv {rhs}")
                else:
                    if opcode == IROpcode.ADD: self.output.append(f"    add rax, {rhs}")
                    elif opcode == IROpcode.SUB: self.output.append(f"    sub rax, {rhs}")
                    elif opcode == IROpcode.MUL: self.output.append(f"    imul rax, {rhs}")
                    elif opcode in (IROpcode.AND, IROpcode.OR, IROpcode.XOR):
                        self.expr_gen.emit_int_binop(opcode, "rax", rhs)

                if isinstance(dest, IRTemp):
                    self._store_temp_from_gpr(dest, "rax")

        elif opcode == IROpcode.NOT:
            is_float = self._is_float(args[0])
            if is_float:


                pass
            else:
                val = self._resolve_operand(args[0], "rax", force_reg=True)
                self.expr_gen.emit_not("rax")
                if isinstance(dest, IRTemp):
                    self._store_temp_from_gpr(dest, "rax")

        elif opcode == IROpcode.NEG:
            is_float = self._is_float(args[0])
            if is_float:

                pass
            else:
                val = self._resolve_operand(args[0], "rax", force_reg=True)
                self.expr_gen.emit_neg("rax")
                if isinstance(dest, IRTemp):
                    self._store_temp_from_gpr(dest, "rax")

        elif opcode in (IROpcode.CMP_EQ, IROpcode.CMP_NE, IROpcode.CMP_LT, IROpcode.CMP_LE, IROpcode.CMP_GT, IROpcode.CMP_GE):
            lhs = self._resolve_operand(args[0], "rax", force_reg=True)
            rhs = self._resolve_operand(args[1], "rcx")
            self.output.append(f"    cmp {lhs}, {rhs}")

            if isinstance(dest, IRTemp) and self._cmp_result_is_consumed_by_jump(dest, next_instr):
                self._last_cmp_temp_id = dest.id
                self._last_cmp_opcode = opcode
                self._last_cmp_unsigned = self._should_use_unsigned_cmp(args[0], args[1])
                return

            set_map = {
                IROpcode.CMP_EQ: "sete",
                IROpcode.CMP_NE: "setne",
                IROpcode.CMP_LT: "setl",
                IROpcode.CMP_LE: "setle",
                IROpcode.CMP_GT: "setg",
                IROpcode.CMP_GE: "setge",
            }
            self.output.append(f"    {set_map[opcode]} al")
            self.output.append("    movzx rax, al")

            if isinstance(dest, IRTemp):
                self._store_temp_from_gpr(dest, "rax")

        elif opcode == IROpcode.JUMP:
            target = args[0].name if isinstance(args[0], IRLabel) else args[0]
            self.control_flow.emit_jump(target)

        elif opcode == IROpcode.JUMP_IF:
            if self._emit_direct_cmp_jump(args[0], args[1], invert=False):
                return
            cond = self._resolve_operand(args[0], "rax", force_reg=True)
            target = args[1].name if isinstance(args[1], IRLabel) else args[1]
            self.control_flow.emit_jump_if_nonzero(cond, target)

        elif opcode == IROpcode.JUMP_IF_NOT:
            if self._emit_direct_cmp_jump(args[0], args[1], invert=True):
                return
            cond = self._resolve_operand(args[0], "rax", force_reg=True)
            target = args[1].name if isinstance(args[1], IRLabel) else args[1]
            self.control_flow.emit_jump_if_zero(cond, target)

        elif opcode == IROpcode.RETURN:
            if args:
                is_float = self._is_float(args[0])
                if is_float:
                    val = self._resolve_operand(args[0], "xmm0", force_reg=True)
                else:
                    val = self._resolve_operand(args[0], "rax", force_reg=True)


            stack_size = self.current_frame.stack_size
            use_red_zone = self.is_leaf and stack_size <= 128

            if stack_size > 0 and not use_red_zone:
                self.output.append("    mov rsp, rbp")
            self.output.append("    pop rbp")
            self.output.append("    ret")

        elif opcode == IROpcode.CALL:
            func_name = args[0].name if hasattr(args[0], 'name') else str(args[0])

            stack_bytes = self._pending_stack_arg_bytes
            self._pending_stack_arg_bytes = 0

            pad = (16 - (stack_bytes % 16)) % 16
            if pad:
                self.output.append(f"    sub rsp, {pad}")
            self.output.append(f"    call {func_name}")
            cleanup = stack_bytes + pad
            if cleanup:
                self.output.append(f"    add rsp, {cleanup}")

            if dest and isinstance(dest, IRTemp):
                self._store_temp_from_gpr(dest, "rax")

        elif opcode == IROpcode.PARAM:
            idx = args[0].value
            if not isinstance(idx, int):
                idx = int(idx)
            is_float = self._is_float(args[1])

            if is_float:
                if idx < 8:
                    reg = f"xmm{idx}"
                    self._resolve_operand(args[1], reg, force_reg=True)
                else:
                    self._resolve_operand(args[1], "xmm0", force_reg=True)
                    self.output.append("    sub rsp, 8")
                    self.output.append("    movss [rsp], xmm0")
                    self._pending_stack_arg_bytes += 8
            else:
                val = self._resolve_operand(args[1], "rax", force_reg=True)
                if idx < len(INTEGER_PARAM_REGISTERS):
                    reg = INTEGER_PARAM_REGISTERS[idx].value
                    self.output.append(f"    mov {reg}, {val}")
                else:
                    self.output.append("    sub rsp, 8")
                    self.output.append(f"    mov qword [rsp], {val}")
                    self._pending_stack_arg_bytes += 8

    def _store_scalar_at_addr_register(self, addr_reg: str, src_op: IROperand) -> None:
        if isinstance(src_op, IRLiteral):
            if isinstance(src_op.value, int):
                self.output.append(f"    mov dword [{addr_reg}], {int(src_op.value)}")
                return
            if isinstance(src_op.value, bool):
                v = "1" if src_op.value else "0"
                self.output.append(f"    mov dword [{addr_reg}], {v}")
                return
            if isinstance(src_op.value, float):
                bits = struct.unpack("I", struct.pack("f", float(src_op.value)))[0]
                self.output.append(f"    mov dword [{addr_reg}], {bits}")
                return
        if isinstance(src_op, IRTemp) and src_op.type == "float":
            self._resolve_operand(src_op, "xmm0", force_reg=True)
            self.output.append(f"    movss dword [{addr_reg}], xmm0")
            return
        if isinstance(src_op, IRTemp) and src_op.type == "int":
            self._resolve_operand(src_op, "rax", force_reg=True)
            self.output.append(f"    mov dword [{addr_reg}], eax")
            return
        if isinstance(src_op, IRTemp) and src_op.type == "bool":
            self._resolve_operand(src_op, "rax", force_reg=True)
            self.output.append(f"    mov byte [{addr_reg}], al")
            return
        val = self._resolve_operand(src_op, "rax", force_reg=True)
        self.output.append(f"    mov qword [{addr_reg}], {val}")

    def _load_scalar_from_address(self, addr_reg: str, dest: IRTemp, dest_slot_off: int) -> None:
        typ = dest.type or ""
        if typ == "int":
            self.output.append(f"    movsx rax, dword [{addr_reg}]")
            self._store_temp_from_gpr(dest, "rax")
            return
        elif typ == "float":
            self.output.append(f"    movss xmm0, dword [{addr_reg}]")
            self.output.append(f"    movss [rbp{dest_slot_off:+d}], xmm0")
            return
        elif typ == "bool":
            self.output.append(f"    movzx rax, byte [{addr_reg}]")
            self._store_temp_from_gpr(dest, "rax")
            return
        else:
            self.output.append(f"    mov rax, qword [{addr_reg}]")
            self._store_temp_from_gpr(dest, "rax")
            return
        self.output.append(f"    mov [rbp{dest_slot_off:+d}], rax")

    def _load_scalar_from_rbp_offset(self, rbp_off: int, dest: IRTemp, dest_slot_off: int) -> None:
        typ = dest.type or ""
        if typ == "int":
            self.output.append(f"    movsx rax, dword [rbp{rbp_off:+d}]")
            self._store_temp_from_gpr(dest, "rax")
            return
        elif typ == "float":
            self.output.append(f"    movss xmm0, dword [rbp{rbp_off:+d}]")
            self.output.append(f"    movss [rbp{dest_slot_off:+d}], xmm0")
            return
        elif typ == "bool":
            self.output.append(f"    movzx rax, byte [rbp{rbp_off:+d}]")
            self._store_temp_from_gpr(dest, "rax")
            return
        else:
            self.output.append(f"    mov rax, [rbp{rbp_off:+d}]")
            self._store_temp_from_gpr(dest, "rax")
            return
        self.output.append(f"    mov [rbp{dest_slot_off:+d}], rax")

    def _load_scalar_from_global_symbol(self, gname: str, dest: IRTemp, dest_slot_off: int) -> None:
        typ = dest.type or ""
        if typ == "int":
            self.output.append(f"    movsx rax, dword [{gname}]")
            self._store_temp_from_gpr(dest, "rax")
            return
        elif typ == "float":
            self.output.append(f"    movss xmm0, dword [{gname}]")
            self.output.append(f"    movss [rbp{dest_slot_off:+d}], xmm0")
            return
        elif typ == "bool":
            self.output.append(f"    movzx rax, byte [{gname}]")
            self._store_temp_from_gpr(dest, "rax")
            return
        else:
            self.output.append(f"    mov rax, qword [{gname}]")
            self._store_temp_from_gpr(dest, "rax")
            return
        self.output.append(f"    mov [rbp{dest_slot_off:+d}], rax")

    def _resolve_operand(self, op: IROperand, scratch_reg: str, force_reg: bool = False) -> str:
        if isinstance(op, IRLiteral):
            if isinstance(op.value, int):
                if force_reg:
                    self.output.append(f"    mov {scratch_reg}, {op.value}")
                    return scratch_reg
                return str(op.value)
            if isinstance(op.value, bool):
                val = "1" if op.value else "0"
                if force_reg:
                    self.output.append(f"    mov {scratch_reg}, {val}")
                    return scratch_reg
                return val
            if isinstance(op.value, str):
                label = self.string_literals[op.value]
                self.output.append(f"    lea {scratch_reg}, [{label}]")
                return scratch_reg
        elif isinstance(op, IRTemp):
            mapped = self._temp_to_reg.get(op.id)
            if mapped and op.id not in self._spilled_temps and op.type != "float":
                if force_reg and scratch_reg != mapped:
                    self.output.append(f"    mov {scratch_reg}, {mapped}")
                    return scratch_reg
                return mapped
            offset = self.current_frame.get_temp_offset(op.id)
            if force_reg:
                if scratch_reg.startswith("xmm"):
                    self.output.append(f"    movss {scratch_reg}, [rbp{offset:+d}]")
                else:
                    self.output.append(f"    mov {scratch_reg}, [rbp{offset:+d}]")
                return scratch_reg
            return f"[rbp{offset:+d}]"
        elif isinstance(op, IRVar):
            offset = self.current_frame.get_offset(op.name)
            if offset is not None:
                if force_reg:
                    if scratch_reg.startswith("xmm"):
                        self.output.append(f"    movss {scratch_reg}, [rbp{offset:+d}]")
                    else:
                        self.output.append(f"    mov {scratch_reg}, [rbp{offset:+d}]")
                    return scratch_reg
                return f"[rbp{offset:+d}]"
            else:

                if force_reg:
                    if scratch_reg.startswith("xmm"):
                        self.output.append(f"    movss {scratch_reg}, [{op.name}]")
                    else:
                        self.output.append(f"    mov {scratch_reg}, [{op.name}]")
                    return scratch_reg
                return f"[{op.name}]"
        elif isinstance(op, IRMemory):
            if isinstance(op.base, IRVar):
                return self._resolve_operand(op.base, scratch_reg, force_reg)

            base = self._resolve_operand(op.base, "r11", force_reg=True)
            if force_reg:
                if scratch_reg.startswith("xmm"):
                    self.output.append(f"    movss {scratch_reg}, [{base}]")
                else:
                    self.output.append(f"    mov {scratch_reg}, [{base}]")
                return scratch_reg
            return f"[{base}]"

        return "0"

    def _store_temp_from_gpr(self, temp: IRTemp, src_reg: str) -> None:
        mapped = self._temp_to_reg.get(temp.id)
        if mapped and temp.id not in self._spilled_temps and temp.type != "float":
            if mapped != src_reg:
                self.output.append(f"    mov {mapped}, {src_reg}")
            return
        offset = self.current_frame.get_temp_offset(temp.id)
        self.output.append(f"    mov [rbp{offset:+d}], {src_reg}")

    def _store_temp_from_value(self, temp: IRTemp, value: str) -> None:
        mapped = self._temp_to_reg.get(temp.id)
        if mapped and temp.id not in self._spilled_temps and temp.type != "float":
            if value != mapped:
                self.output.append(f"    mov {mapped}, {value}")
            return
        offset = self.current_frame.get_temp_offset(temp.id)
        self.output.append(f"    mov [rbp{offset:+d}], {value}")

    def _is_float(self, op: IROperand) -> bool:
        if isinstance(op, IRTemp):
            return op.type == "float"
        if isinstance(op, IRLiteral):
            return isinstance(op.value, float)


        return False

    def _cmp_result_is_consumed_by_jump(self, cmp_dest: IRTemp, next_instr: IRInstruction | None) -> bool:
        if next_instr is None:
            return False
        if next_instr.opcode not in (IROpcode.JUMP_IF, IROpcode.JUMP_IF_NOT):
            return False
        if not next_instr.args:
            return False
        cond = next_instr.args[0]
        return isinstance(cond, IRTemp) and cond.id == cmp_dest.id

    def _should_use_unsigned_cmp(self, lhs: IROperand, rhs: IROperand) -> bool:
        return self._is_pointer_like(lhs) or self._is_pointer_like(rhs)

    def _is_pointer_like(self, op: IROperand) -> bool:
        if isinstance(op, IRTemp):
            return op.type == "*"
        return False

    def _emit_direct_cmp_jump(self, cond_op: IROperand, target_op: IROperand, invert: bool) -> bool:
        if not isinstance(cond_op, IRTemp):
            return False
        if self._last_cmp_temp_id != cond_op.id or self._last_cmp_opcode is None:
            return False
        target = target_op.name if isinstance(target_op, IRLabel) else str(target_op)
        jcc = self._jump_for_cmp(self._last_cmp_opcode, invert=invert, unsigned=self._last_cmp_unsigned)
        self.output.append(f"    {jcc} {target}")
        self._last_cmp_temp_id = None
        self._last_cmp_opcode = None
        self._last_cmp_unsigned = False
        return True

    def _jump_for_cmp(self, opcode: IROpcode, invert: bool, unsigned: bool) -> str:
        if unsigned:
            direct = {
                IROpcode.CMP_EQ: "je",
                IROpcode.CMP_NE: "jne",
                IROpcode.CMP_LT: "jb",
                IROpcode.CMP_LE: "jbe",
                IROpcode.CMP_GT: "ja",
                IROpcode.CMP_GE: "jae",
            }
            inverse = {
                IROpcode.CMP_EQ: "jne",
                IROpcode.CMP_NE: "je",
                IROpcode.CMP_LT: "jae",
                IROpcode.CMP_LE: "ja",
                IROpcode.CMP_GT: "jbe",
                IROpcode.CMP_GE: "jb",
            }
        else:
            direct = {
                IROpcode.CMP_EQ: "je",
                IROpcode.CMP_NE: "jne",
                IROpcode.CMP_LT: "jl",
                IROpcode.CMP_LE: "jle",
                IROpcode.CMP_GT: "jg",
                IROpcode.CMP_GE: "jge",
            }
            inverse = {
                IROpcode.CMP_EQ: "jne",
                IROpcode.CMP_NE: "je",
                IROpcode.CMP_LT: "jge",
                IROpcode.CMP_LE: "jg",
                IROpcode.CMP_GT: "jle",
                IROpcode.CMP_GE: "jl",
            }
        return (inverse if invert else direct)[opcode]

    def _generate_data_sections(self):
        if self.string_literals:
            self.output.append("")
            self.output.append("section .rodata")
            for content, label in self.string_literals.items():

                escaped = content.replace("'", "''")
                self.output.append(f"{label} db '{escaped}', 0")

        gl = self.program.globals
        if not gl:
            return
        data_g = [x for x in gl if x.init_int is not None or x.init_float_bits is not None]
        bss_g = [x for x in gl if x.init_int is None and x.init_float_bits is None]
        if data_g:
            self.output.append("")
            self.output.append("section .data")
            for g in data_g:
                self.output.append(f"global {g.asm_name}")
                if g.init_int is not None:
                    self.output.append(f"{g.asm_name} dd {g.init_int}")
                else:
                    self.output.append(f"{g.asm_name} dd {g.init_float_bits}")
        if bss_g:
            self.output.append("")
            self.output.append("section .bss")
            for g in bss_g:
                self.output.append(f"global {g.asm_name}")
                self.output.append(f"{g.asm_name} resb {g.size_bytes}")
