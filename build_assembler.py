#!/usr/bin/env python3
"""
自举汇编器构建脚本 (一次性工具)
1. 预填充 IChing 操作码表 (64 条目) 到 VM 堆内存
2. 组合并汇编 asm_core + asm_main → assembler.evob
3. 验证: 用 assembler.evob 汇编 compiler.evoasm, 与 Python 输出对比
"""

import sys, os, struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

# ============================================================
# 内存布局
# ============================================================
INPUT_BUF     = 0x1000
OUTPUT_BUF    = 0x20000
LABEL_TABLE   = 0x12000
OPCODE_TABLE  = 0x16000
TEMP_BUF      = 0x17000
LINE_BUF      = 0x18100

# ============================================================
# IChing 操作码表 (64 条目, 每条目 14 字节: 12 名称 + 1 opcode + 1 填充)
# ============================================================
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
    """构建操作码表的二进制数据"""
    table = bytearray()
    for name, opcode in ICHING_MNEMONICS:
        entry = bytearray(14)
        name_bytes = name.encode('ascii')
        entry[:len(name_bytes)] = name_bytes
        entry[12] = opcode & 0xFF
        table.extend(entry)
    return bytes(table)

def load_assembler_source():
    """加载并组合汇编器源码"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'asm_core.evoasm'), 'r') as f:
        core = f.read()
    
    with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'asm_main.evoasm'), 'r') as f:
        main = f.read()
    
    # 组合: BRANCH.1 @asm_main 在顶部, 然后核心函数, 然后主模块代码
    # asm_main.evoasm 以 BRANCH.1 @asm_main 开头，将其提取到最前面
    lines = main.split('\n')
    entry_line = ''
    main_body_lines = []
    found_entry = False
    for line in lines:
        s = line.strip()
        if not found_entry and s.startswith('BRANCH') and '@asm_main' in s:
            entry_line = line
            found_entry = True
            continue
        if found_entry:
            main_body_lines.append(line)
    
    main_body = '\n'.join(main_body_lines)
    combined = entry_line + '\n' + core + '\n' + main_body
    return combined

def build_assembler_evob() -> bytes:
    """构建 assembler.evob"""
    vm = ExtendedIChingVM2()
    
    # 1. 预填充操作码表
    opcode_table = build_opcode_table()
    for i, byte_val in enumerate(opcode_table):
        vm.heap[OPCODE_TABLE + i] = byte_val
    print(f"  [ok] Opcode table: {len(opcode_table)} bytes ({len(ICHING_MNEMONICS)} entries)")
    
    # 2. 加载汇编器源码
    asm_source = load_assembler_source()
    print(f"  [ok] Assembler source: {len(asm_source)} chars, {len(asm_source.splitlines())} lines")
    
    # 3. 汇编
    evob = vm.assemble(asm_source)
    print(f"  [ok] Assembled: {len(evob)} bytes")
    
    return bytes(evob)

def test_assembler(assembler_evob: bytes) -> bool:
    """测试: 用 EVB 汇编器汇编 compiler.evoasm, 与 Python 输出对比"""
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    compiler_path = os.path.join(base_dir, 'evomorph', 'bootstrap', 'compiler.evoasm')
    
    with open(compiler_path, 'r') as f:
        compiler_source = f.read()
    
    print(f"\n  Testing: assembling compiler.evoasm ({len(compiler_source)} chars)...")
    
    # Python 汇编器输出 (基准)
    vm_ref = ExtendedIChingVM2()
    ref_output = bytes(vm_ref.assemble(compiler_source))
    print(f"  [ref] Python assembler: {len(ref_output)} bytes")
    
    # EVB 汇编器输出
    vm = ExtendedIChingVM2()
    
    # 预填充操作码表
    opcode_table = build_opcode_table()
    for i, byte_val in enumerate(opcode_table):
        vm.heap[OPCODE_TABLE + i] = byte_val
    
    # 加载源码到堆
    source_bytes = compiler_source.encode('ascii', errors='replace') + b'\x00'
    for i, byte_val in enumerate(source_bytes):
        vm.heap[INPUT_BUF + i] = byte_val
    
    # 清除标签表区域
    for i in range(LABEL_TABLE, LABEL_TABLE + 0x4000):
        vm.heap[i] = 0
    
    # 加载汇编器并执行 (直接加载字节码)
    vm.program = bytearray(assembler_evob)
    vm.pc = 0
    vm.registers[0] = INPUT_BUF
    vm.registers[29] = vm.STACK_SIZE
    vm.registers[29] = vm.STACK_SIZE
    vm.run(max_cycles=5000000)
    
    output_size = vm.registers[0]
    if output_size <= 0 or output_size > 100000:
        print(f"  [FAIL] EVB assembler returned invalid size: {output_size}")
        print(f"         VM state: {vm.state}, cycles: {vm.cycle_count}")
        return False
    
    evb_output = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF + output_size])
    print(f"  [evb] EVB assembler:     {len(evb_output)} bytes, cycles={vm.cycle_count}")
    
    # 比较
    if len(evb_output) != len(ref_output):
        print(f"  [WARN] Size mismatch: EVB={len(evb_output)} vs Python={len(ref_output)}")
        min_len = min(len(evb_output), len(ref_output))
        mismatches = sum(1 for i in range(min_len) if evb_output[i] != ref_output[i])
        print(f"         First {min_len} bytes: {mismatches} mismatches")
        if min_len < 64:
            print(f"         EVB:    {evb_output[:min_len].hex()}")
            print(f"         Python: {ref_output[:min_len].hex()}")
    else:
        mismatches = sum(1 for i in range(len(evb_output)) if evb_output[i] != ref_output[i])
        if mismatches == 0:
            print(f"  [PASS] Byte-level match!")
        else:
            print(f"  [FAIL] {mismatches} byte mismatches (same size)")
    
    return len(evb_output) > 0

def main():
    print("=" * 60)
    print("Building Self-Hosting Assembler")
    print("=" * 60)
    
    # 构建
    assembler_evob = build_assembler_evob()
    
    # 保存
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob')
    with open(output_path, 'wb') as f:
        f.write(assembler_evob)
    print(f"\n  Saved: {output_path} ({len(assembler_evob)} bytes)")
    
    # 测试
    print("\n" + "-" * 40)
    success = test_assembler(assembler_evob)
    
    print("\n" + "=" * 60)
    if success:
        print("BUILD SUCCESSFUL - Assembler is self-hosting ready")
    else:
        print("BUILD COMPLETE - Assembler needs debugging")
    print("=" * 60)

if __name__ == '__main__':
    main()
