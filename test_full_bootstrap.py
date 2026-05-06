#!/usr/bin/env python3
"""
易衍·Evomorph 完全自举验证
Phase 1: 编译器A(Python+ASM) 编译编译器自身的 .evo 源码 → EVOB
Phase 2: 编译器B(EVOB在VM上运行) 编译简单程序 → EVOB
Phase 3: 简单程序的EVOB在VM上执行 → 验证结果正确
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM,
    INPUT_BUF, TOKEN_BUF, OUTPUT_BUF, HEADER_RESERVE
)
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

def build_compiler_evo_source():
    asm_code = "JMP main\n" + STDLIB_ASM + LEXER_ASM + LOOKUP_ASM + CODEGEN_ASM + PARSER_ASM + MAIN_ASM
    guaxu_lines = []
    for line in asm_code.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith(';'):
            continue
        guaxu_lines.append('        ' + line)
    evo_source = '@evolang "3.0"\n\n@locus bootstrap_compiler {\n    GUAXU: {\n'
    evo_source += '\n'.join(guaxu_lines) + '\n    }\n}\n'
    return evo_source

print("=" * 60)
print("易衍·Evomorph 完全自举验证")
print("=" * 60)

# Phase 1: 编译器A 编译编译器自身
print("\n[Phase 1] 编译器A 编译编译器自身的 .evo 源码")
compiler_a = BootstrapCompiler()
compiler_evo = build_compiler_evo_source()
result_a = compiler_a.compile_source(compiler_evo)

print(f"  编译成功: {result_a['success']}")
print(f"  EVOB有效: {result_a.get('evob_valid', False)}")
print(f"  字节码大小: {result_a['output_size'] - 14} 字节")
print(f"  基因座数: {result_a.get('locus_count', 'N/A')}")
print(f"  执行周期: {result_a['cycles']}")

if not result_a.get('evob_valid'):
    print("  ✗ 编译器EVOB无效")
    sys.exit(1)

evob_compiler = result_a['output_bytes']
print(f"  ✓ 编译器EVOB: {len(evob_compiler)} 字节")

# Phase 2: 编译器B(EVOB在VM上运行) 编译简单程序
print("\n[Phase 2] 编译器B(EVOB在VM上运行) 编译简单程序")

test_program = '@evolang "3.0"\n\n@locus hello {\n    GUAXU: {\n        MOVI R0, #42\n        HLT\n    }\n}\n'

vm_b = ExtendedIChingVM2()
ok = vm_b.load_evob(evob_compiler)
print(f"  编译器EVOB加载: {ok}")

if not ok:
    print("  ✗ 编译器EVOB加载失败")
    sys.exit(1)

# 设置编译器运行环境
compiler_helper = BootstrapCompiler()
compiler_helper.vm = vm_b
compiler_helper._load_mnemonic_table()
compiler_helper._load_native_table()

# 加载输入源码
processed = compiler_helper._preprocess_source(test_program)
vm_b.load_string(INPUT_BUF, processed)

# 设置栈指针和入口参数
vm_b.registers[29] = vm_b.STACK_SIZE
vm_b.registers[0] = INPUT_BUF

# 运行编译器B
vm_b.run(max_cycles=10000000)

print(f"  VM状态: {vm_b.state}")
print(f"  执行周期: {vm_b.cycle_count}")

if vm_b.state.value != 3:  # HALTED
    print(f"  ✗ 编译器B未正常结束")
    sys.exit(1)

# 读取输出
output_size = vm_b.registers[0]
print(f"  输出大小: {output_size}")

if output_size <= 0:
    print("  ✗ 编译器B无输出")
    sys.exit(1)

raw_output = bytes(vm_b.heap[OUTPUT_BUF:OUTPUT_BUF + min(output_size, 24576)])
print(f"  输出前4字节: {raw_output[:4]}")

if raw_output[:4] != b'EVOB':
    print("  ✗ 编译器B输出不是EVOB格式")
    # Show first 20 bytes for debugging
    print(f"  前20字节: {raw_output[:20].hex()}")
    sys.exit(1)

print("  ✓ 编译器B成功编译了简单程序!")

# Phase 3: 验证编译器B的输出可执行
print("\n[Phase 3] 验证编译器B的输出可执行")

# 构造完整的EVOB
header_size = struct.unpack(">H", raw_output[6:8])[0]
if header_size < 10 or header_size > output_size:
    print(f"  ✗ 无效header_size: {header_size}")
    sys.exit(1)

bytecode_data = raw_output[HEADER_RESERVE:]
evob_test = raw_output[:header_size] + bytecode_data

vm_c = ExtendedIChingVM2()
ok = vm_c.load_evob(evob_test)
print(f"  EVOB加载: {ok}")

if ok:
    vm_c.run(max_cycles=1000)
    print(f"  VM状态: {vm_c.state}")
    print(f"  R0 = {vm_c.registers[0]} (期望 42)")
    if vm_c.registers[0] == 42:
        print("  ✓✓✓ 自举验证成功! 编译器B的输出正确执行!")
    else:
        print("  ✗ 执行结果不正确")
else:
    print("  ✗ EVOB加载失败")

# Phase 4: 确定性验证
print("\n[Phase 4] 确定性验证")
result_a2 = compiler_a.compile_source(compiler_evo)
if result_a.get('output_bytes') and result_a2.get('output_bytes'):
    match = result_a['output_bytes'] == result_a2['output_bytes']
    print(f"  两次编译输出一致: {match}")
    if match:
        print("  ✓ 编译确定性验证通过!")

print("\n" + "=" * 60)
print("自举验证完成")
print("=" * 60)
