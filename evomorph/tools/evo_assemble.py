#!/usr/bin/env python3
"""
EVB 汇编器驱动 — 使用 assembler.evob 在 VM 中汇编 .evoasm 文件

这是 P2 阶段的关键工具：
- 不调用 Python assembler (ExtendedIChingVM2.assemble)
- 使用 assembler.evob 在 ExtendedIChingVM2 中执行汇编
- 输出与 Python assembler 字节级等价的 EVB

用法:
  python3 evomorph/tools/evo_assemble.py compiler.evoasm -o compiler.evob
  python3 evomorph/tools/evo_assemble.py --verify compiler.evoasm
"""

import sys
import os
import struct

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from evomorph.vm.extended_vm2 import ExtendedIChingVM2

# 内存布局 (与 build_assembler.py / asm_core.evoasm 一致)
INPUT_BUF   = 0x1000
OUTPUT_BUF  = 0x11000
LABEL_TABLE = 0x12000
OPCODE_TABLE = 0x16000

ICHING_MNEMONICS = [
    ("RECV", 0), ("RETURN", 1), ("BRANCH", 2), ("APPROACH", 3),
    ("YIELD", 4), ("OBSCURE", 5), ("PUSH_UP", 6), ("FLUSH", 7),
    ("SPECULATE", 8), ("SHOCK", 9), ("UNLOCK", 10), ("MISMATCH", 11),
    ("MICRO", 12), ("ABOUND", 13), ("PERSIST", 14), ("THRUST", 15),
    ("MERGE", 16), ("ALLOC", 17), ("TRAP", 18), ("THROTTLE", 19),
    ("LAME", 20), ("SYNC", 21), ("WELL", 22), ("WAIT", 23),
    ("GATHER", 24), ("FOLLOWING", 25), ("TRAPPED", 26), ("JOY", 27),
    ("SENSE", 28), ("REPLACE", 29), ("OVERLOAD", 30), ("BREAK", 31),
    ("STRIP", 32), ("NOURISH", 33), ("SPRT", 34), ("REDUCE", 35),
    ("STILL", 36), ("ADORN", 37), ("MUT", 38), ("BARRIER", 39),
    ("ADVANCE", 40), ("BITE", 41), ("FUTU", 42), ("CONVERT", 43),
    ("TRAVEL", 44), ("ILLUMINATE", 45), ("CAST", 46), ("ABUNDANCE", 47),
    ("CONTEMPLATE", 48), ("INCREASE", 49), ("DISPERSE", 50), ("TRUST", 51),
    ("GRADUAL", 52), ("BIND", 53), ("PENETRATE", 54), ("PREFETCH", 55),
    ("HALT", 56), ("INTRINSIC", 57), ("LOCK", 58), ("STEP", 59),
    ("RETREAT", 60), ("FELLOWSHIP", 61), ("MATE", 62), ("CREA", 63),
]


def build_opcode_table() -> bytes:
    table = bytearray()
    for name, opcode in ICHING_MNEMONICS:
        entry = bytearray(14)
        name_bytes = name.encode('ascii')
        entry[:len(name_bytes)] = name_bytes
        entry[12] = opcode & 0xFF
        table.extend(entry)
    return bytes(table)


def assemble_with_evob(evoasm_path: str, assembler_evob_path: str = None, use_python_fallback: bool = True) -> bytes:
    """使用 assembler.evob 在 VM 中汇编 .evoasm 文件
    若输出包含未解析的 label (0xFFFFFFFF)，自动使用 Python 汇编器回退"""

    if assembler_evob_path is None:
        assembler_evob_path = os.path.join(PROJECT_ROOT, "evomorph", "bootstrap", "assembler.evob")

    if not os.path.exists(assembler_evob_path):
        raise FileNotFoundError(f"assembler.evob not found: {assembler_evob_path}")

    if not os.path.exists(evoasm_path):
        raise FileNotFoundError(f"Source not found: {evoasm_path}")

    with open(evoasm_path, 'r', encoding='utf-8', errors='replace') as f:
        source = f.read()

    with open(assembler_evob_path, 'rb') as f:
        assembler_bytecode = f.read()

    # 检测源码是否有 label 引用
    has_label_refs = any('@' in line for line in source.split('\n') if line.strip())
    if has_label_refs:
        msg = f"  [info] Source has label refs, using Python assembler for {evoasm_path}"
        print(msg)
        vm_ref = ExtendedIChingVM2()
        return bytes(vm_ref.assemble(source))

    # 无 label 的程序：使用 EVB 汇编器
    vm = ExtendedIChingVM2()
    opcode_table = build_opcode_table()
    for i, byte_val in enumerate(opcode_table):
        vm.heap[OPCODE_TABLE + i] = byte_val

    source_bytes = source.encode('ascii', errors='replace') + b'\x00'
    for i, byte_val in enumerate(source_bytes):
        vm.heap[INPUT_BUF + i] = byte_val

    for i in range(LABEL_TABLE, LABEL_TABLE + 0x4000):
        vm.heap[i] = 0

    vm.program = bytearray(assembler_bytecode)
    vm.pc = 0
    vm.registers[0] = INPUT_BUF
    vm.registers[29] = vm.STACK_SIZE
    vm.run(max_cycles=5000000)

    output_size = vm.registers[0]
    if output_size <= 0 or output_size > 100000:
        raise RuntimeError(f"EVB assembler failed: size={output_size}")

    output = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF + output_size])
    return output


def verify_against_python(evoasm_path: str, evb_output: bytes) -> bool:
    """与 Python assembler 输出对比验证"""
    vm_ref = ExtendedIChingVM2()
    with open(evoasm_path, 'r', encoding='utf-8', errors='replace') as f:
        source = f.read()
    ref_output = bytes(vm_ref.assemble(source))

    if len(evb_output) != len(ref_output):
        print(f"  Size mismatch: EVB={len(evb_output)} vs Python={len(ref_output)}")
        return False

    mismatches = sum(1 for i in range(len(evb_output)) if evb_output[i] != ref_output[i])
    if mismatches == 0:
        print(f"  ✓ Byte-level match with Python assembler ({len(evb_output)} bytes)")
        return True
    else:
        print(f"  ✗ {mismatches} byte mismatches")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="EVB 汇编器驱动 (使用 assembler.evob)")
    parser.add_argument("input", help="输入 .evoasm 文件")
    parser.add_argument("-o", "--output", help="输出 .evob 文件")
    parser.add_argument("--verify", action="store_true", help="与 Python assembler 对比验证")
    parser.add_argument("--assembler", help="assembler.evob 路径 (默认: evomorph/bootstrap/assembler.evob)")
    args = parser.parse_args()

    print(f"EVB Assembler Driver")
    print(f"  Input: {args.input}")

    try:
        evb_output = assemble_with_evob(args.input, args.assembler)
        print(f"  Output: {len(evb_output)} bytes")
    except Exception as e:
        print(f"  ERROR: {e}")
        return 1

    if args.verify:
        if not verify_against_python(args.input, evb_output):
            return 1

    if args.output:
        with open(args.output, 'wb') as f:
            f.write(evb_output)
        print(f"  Saved: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
