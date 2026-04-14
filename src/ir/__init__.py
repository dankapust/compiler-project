from .ir_instructions import IRInstruction, IROpcode, IRTemp, IRLiteral, IRVar, IRLabel, IRMemory, IRPhiParam
from .basic_block import BasicBlock, IRFunction, IRProgram
from .ir_generator import IRGenerator
from .output import format_ir_text, format_ir_dot, format_ir_json, format_ir_stats
from .control_flow import PeepholeOptimizer

__all__ = [
    "IRInstruction", "IROpcode", "IRTemp", "IRLiteral", "IRVar", "IRLabel", "IRMemory", "IRPhiParam",
    "BasicBlock", "IRFunction", "IRProgram", "IRGenerator",
    "format_ir_text", "format_ir_dot", "format_ir_json", "format_ir_stats",
    "PeepholeOptimizer",
]
