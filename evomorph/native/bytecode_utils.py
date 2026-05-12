"""
字节码工具 — Python 桥接层
==============================
状态: P4 — EVB-native 核心函数已完成 (bytecode_utils.evo)
      operand_to_byte, encode_instruction, locus_to_bytecode 已 EVB-ify
      source_to_segments 仍需 Python 编译器接口

EVB-native 实现: bytecode_utils.evo (operand_to_byte, encode_instruction, locus_to_bytecode)
Python 桥接原因: source_to_segments 需要 EnhancedEvoRuntime 编译器接口
计划移除: P3 VM 自举后，source_to_segments 可在 EVB-native 编译器中实现
"""

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
    # 支持 EnhancedEvoRuntime (full_compile) 和 EvocCompiler (compile) 两种接口
    if hasattr(compiler, 'full_compile'):
        ast = compiler.full_compile(source)
    else:
        ast = compiler.compile(source, output_format="dict")
    segments = []
    for locus_data in ast.get("loci", []):
        cross_pool = locus_data.get("cross_pool", "default")
        if not isinstance(cross_pool, str):
            cross_pool = "default"
        seg = LocusSegment(
            name=locus_data["name"],
            mut_rate=locus_data.get("mut_rate", 0.02),
            cross_pool=cross_pool,
            bytecode=locus_to_bytecode(locus_data),
        )
        segments.append(seg)
    return segments
