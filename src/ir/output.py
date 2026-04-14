import json
from .ir_instructions import IRInstruction
from .basic_block import IRProgram, IRFunction, BasicBlock


def format_ir_text(program: IRProgram) -> str:
    lines = []

    for f in program.functions:
        lines.append(f"function {f.name}: {f.return_type} ({', '.join(f'{t} {n}' for t, n in f.params)})")
        for block in f.basic_blocks:
            lines.append(f"  {block.label}:")
            for instr in block.instructions:
                lines.append(f"    {instr.format()}")
            lines.append("")

    return "\n".join(lines)


def format_ir_dot(program: IRProgram) -> str:
    lines = ["digraph CFG {"]
    lines.append("  node [shape=record, fontname=\"Courier\"];")

    for f in program.functions:
        for block in f.basic_blocks:
            instrs_str = "\\l".join(
                instr.format().replace("\"", "\\\"").replace("<", "\\<").replace(">", "\\>")
                for instr in block.instructions
            )
            if instrs_str:
                instrs_str += "\\l"
            node_label = f"{{ {block.label} | {instrs_str} }}"
            lines.append(f"  \"{block.label}\" [label=\"{node_label}\"];")

            for succ in block.successors:
                lines.append(f"  \"{block.label}\" -> \"{succ.label}\";")

    lines.append("}")
    return "\n".join(lines)


def format_ir_json(program: IRProgram) -> str:
    data = {
        "functions": []
    }

    for f in program.functions:
        func_data = {
            "name": f.name,
            "return_type": f.return_type,
            "params": [{"type": t, "name": n} for t, n in f.params],
            "basic_blocks": []
        }
        for block in f.basic_blocks:
            block_data = {
                "label": block.label,
                "instructions": [instr.format() for instr in block.instructions]
            }
            func_data["basic_blocks"].append(block_data)
        data["functions"].append(func_data)

    return json.dumps(data, indent=2, ensure_ascii=False)


def format_ir_stats(program: IRProgram) -> str:
    total_instructions = 0
    total_blocks = 0
    total_temps = 0
    opcode_counts: dict[str, int] = {}

    for f in program.functions:
        total_blocks += len(f.basic_blocks)
        for block in f.basic_blocks:
            for instr in block.instructions:
                total_instructions += 1
                op = instr.opcode.value
                opcode_counts[op] = opcode_counts.get(op, 0) + 1
                if instr.dest and hasattr(instr.dest, "id"):
                    total_temps = max(total_temps, instr.dest.id)

    lines = [
        "=== IR Statistics ===",
        f"Functions:    {len(program.functions)}",
        f"Basic blocks: {total_blocks}",
        f"Instructions: {total_instructions}",
        f"Temporaries:  {total_temps}",
        "",
        "Instructions by type:",
    ]
    for op_name, count in sorted(opcode_counts.items()):
        lines.append(f"  {op_name:15s} {count}")

    return "\n".join(lines)
