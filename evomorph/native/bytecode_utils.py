# IChing EVB 等价实现: bytecode_utils.evo (operand_to_byte, encode_instruction, locus_to_bytecode)
# Python 版本保留为桥接层，供 native/linker/image 等基础设施使用

def operand_to_byte(val) -> int:
    if isinstance(val, int):
        return val & 0xFF
    if isinstance(val, str):
        if val.startswith("R"):
            try:
                return int(val[1:]) & 0xFF
            except ValueError:
                return 0
        try:
            return int(val) & 0xFF
        except ValueError:
            return 0
    if isinstance(val, dict):
        v = val.get("value", 0)
        return operand_to_byte(v)
    return 0


def locus_to_bytecode(locus_data: dict) -> bytes:
    bytecode = bytearray()
    for instr in locus_data.get("instructions", []):
        opcode = instr.get("opcode", 0)
        modifier = instr.get("modifier", 0)
        byte1 = ((opcode & 0x3F) << 2) | ((modifier >> 4) & 0x03)
        byte2 = modifier & 0x0F
        bytecode.extend([byte1, byte2])
        for op in instr.get("operands", []):
            bytecode.append(operand_to_byte(op))
    return bytes(bytecode)


def source_to_segments(compiler, source: str) -> list:
    from evomorph.native.loader.evb_loader import LocusSegment
    ast = compiler.compile(source, output_format="dict")
    segments = []
    for locus_data in ast.get("loci", []):
        seg = LocusSegment(
            name=locus_data["name"],
            mut_rate=locus_data.get("mut_rate", 0.02),
            cross_pool=locus_data.get("cross_pool", "default"),
            bytecode=locus_to_bytecode(locus_data),
        )
        segments.append(seg)
    return segments
