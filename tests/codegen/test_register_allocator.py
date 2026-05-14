from codegen.register_allocator import RegisterAllocator
from ir.basic_block import BasicBlock, IRFunction
from ir.ir_instructions import IRInstruction, IROpcode, IRLiteral, IRTemp


def _build_func(instructions):
    block = BasicBlock("entry")
    for instr in instructions:
        block.add_instruction(instr)
    func = IRFunction(name="f", return_type="int", params=[])
    func.add_block(block)
    return func


def test_lsra_allocates_short_intervals():
    t1 = IRTemp(1, "int")
    t2 = IRTemp(2, "int")
    t3 = IRTemp(3, "int")
    func = _build_func(
        [
            IRInstruction(IROpcode.LOAD, t1, [IRLiteral(1)]),
            IRInstruction(IROpcode.LOAD, t2, [IRLiteral(2)]),
            IRInstruction(IROpcode.ADD, t3, [t1, t2]),
            IRInstruction(IROpcode.RETURN, None, [t3]),
        ]
    )
    ra = RegisterAllocator()
    result = ra.allocate_function(func)
    assert len(result.temp_to_reg) >= 2
    assert not result.spilled_temps


def test_lsra_spills_when_pressure_exceeds_registers():
    t1 = IRTemp(1, "int")
    t2 = IRTemp(2, "int")
    t3 = IRTemp(3, "int")
    t4 = IRTemp(4, "int")
    func = _build_func(
        [
            IRInstruction(IROpcode.LOAD, t1, [IRLiteral(1)]),
            IRInstruction(IROpcode.LOAD, t2, [IRLiteral(2)]),
            IRInstruction(IROpcode.LOAD, t3, [IRLiteral(3)]),
            IRInstruction(IROpcode.ADD, t4, [t1, t2]),
            IRInstruction(IROpcode.ADD, t4, [t4, t3]),
            IRInstruction(IROpcode.RETURN, None, [t4]),
        ]
    )
    ra = RegisterAllocator()
    result = ra.allocate_function(func)
    assert result.spilled_temps
    assert len(set(result.temp_to_reg.values())) <= 2


def test_lsra_marks_values_live_across_call_as_spilled():
    t1 = IRTemp(1, "int")
    t2 = IRTemp(2, "int")
    t3 = IRTemp(3, "int")
    func = _build_func(
        [
            IRInstruction(IROpcode.LOAD, t1, [IRLiteral(10)]),
            IRInstruction(IROpcode.CALL, t2, []),
            IRInstruction(IROpcode.ADD, t3, [t1, IRLiteral(1)]),
            IRInstruction(IROpcode.RETURN, None, [t3]),
        ]
    )
    ra = RegisterAllocator()
    result = ra.allocate_function(func)
    assert 1 in result.spilled_temps
    assert result.intervals[1].crosses_call
