#!/usr/bin/env python3
"""
EVB 汇编器驱动 — 使用 assembler.evob 在 VM 中汇编 .evoasm 文件

P2 阶段关键工具:
- 优先使用 assembler.evob (EVB 自举汇编器)
- 当 EVB 汇编器失败或输出不匹配时, 回退到 Python assembler (Stage-0)
- 记录回退原因, 便于追踪 P2 进度

用法:
  python3 evomorph/tools/evo_assemble.py compiler.evoasm -o compiler.evob
  python3 evomorph/tools/evo_assemble.py --verify compiler.evoasm
  python3 evomorph/tools/evo_assemble.py --no-fallback compiler.evoasm  # 禁止回退
"""

import sys
import os
import struct
import hashlib

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState

# 内存布局 (与 build_assembler.py / asm_core.evoasm 一致)
INPUT_BUF   = 0x1000
OUTPUT_BUF  = 0x20000
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


def _python_assemble(source: str) -> bytes:
    """使用 Python assembler 汇编 (Stage-0 回退)"""
    vm_ref = ExtendedIChingVM2()
    return bytes(vm_ref.assemble(source))


def assemble_with_evob(evoasm_path: str, assembler_evob_path: str = None,
                       use_python_fallback: bool = True,
                       verbose: bool = False) -> tuple:
    """使用 assembler.evob 在 VM 中汇编 .evoasm 文件

    Returns:
        (output_bytes, method_used, fallback_reason)
        method_used: "evob" 或 "python"
        fallback_reason: 回退原因 (仅当 method_used="python" 时)
    """
    if assembler_evob_path is None:
        assembler_evob_path = os.path.join(PROJECT_ROOT, "evomorph", "bootstrap", "assembler.evob")

    if not os.path.exists(assembler_evob_path):
        if not use_python_fallback:
            raise FileNotFoundError(f"assembler.evob not found: {assembler_evob_path}")
        source = open(evoasm_path, 'r', encoding='utf-8', errors='replace').read()
        return _python_assemble(source), "python", "assembler.evob not found"

    if not os.path.exists(evoasm_path):
        raise FileNotFoundError(f"Source not found: {evoasm_path}")

    with open(evoasm_path, 'r', encoding='utf-8', errors='replace') as f:
        source = f.read()

    with open(assembler_evob_path, 'rb') as f:
        assembler_bytecode = f.read()

    # 尝试使用 EVB 汇编器
    try:
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

        # 检查 VM 是否正常终止
        if vm.state != VMState.HALTED:
            if not use_python_fallback:
                raise RuntimeError(f"EVB assembler did not halt: state={vm.state}")
            if verbose:
                print(f"  [fallback] EVB assembler did not halt (state={vm.state}), using Python")
            return _python_assemble(source), "python", f"VM state={vm.state}"

        if output_size <= 0 or output_size > 100000:
            if not use_python_fallback:
                raise RuntimeError(f"EVB assembler invalid output: size={output_size}")
            if verbose:
                print(f"  [fallback] EVB assembler invalid output size={output_size}, using Python")
            return _python_assemble(source), "python", f"invalid output size={output_size}"

        output = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF + output_size])

        # 验证输出: 与 Python assembler 对比
        ref_output = _python_assemble(source)
        if output != ref_output:
            if not use_python_fallback:
                # 不回退时, 返回 EVB 输出但标记不匹配
                return output, "evob", f"output mismatch (evb={len(output)}B, py={len(ref_output)}B)"
            if verbose:
                evb_hash = hashlib.sha256(output).hexdigest()[:16]
                py_hash = hashlib.sha256(ref_output).hexdigest()[:16]
                print(f"  [fallback] EVB output mismatch (evb={len(output)}B/{evb_hash}, py={len(ref_output)}B/{py_hash}), using Python")
            return ref_output, "python", f"output mismatch (evb={len(output)}B, py={len(ref_output)}B)"

        # EVB 汇编器成功, 输出与 Python 一致
        if verbose:
            print(f"  [ok] EVB assembler output matches Python ({len(output)} bytes)")
        return output, "evob", None

    except Exception as e:
        if not use_python_fallback:
            raise
        if verbose:
            print(f"  [fallback] EVB assembler exception: {e}, using Python")
        return _python_assemble(source), "python", str(e)


def verify_against_python(evoasm_path: str, evb_output: bytes) -> bool:
    """与 Python assembler 输出对比验证"""
    ref_output = _python_assemble(open(evoasm_path, 'r', encoding='utf-8', errors='replace').read())

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
    parser.add_argument("--no-fallback", action="store_true", help="禁止回退到 Python assembler")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    args = parser.parse_args()

    print(f"EVB Assembler Driver")
    print(f"  Input: {args.input}")

    try:
        evb_output, method, fallback_reason = assemble_with_evob(
            args.input, args.assembler,
            use_python_fallback=not args.no_fallback,
            verbose=args.verbose,
        )
        print(f"  Output: {len(evb_output)} bytes (method={method})")
        if fallback_reason:
            print(f"  Fallback reason: {fallback_reason}")
    except Exception as e:
        print(f"  ERROR: {e}")
        return 1

    if args.verify and method == "evob":
        if not verify_against_python(args.input, evb_output):
            return 1

    if args.output:
        with open(args.output, 'wb') as f:
            f.write(evb_output)
        print(f"  Saved: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
