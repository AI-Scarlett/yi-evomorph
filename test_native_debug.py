#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler, NATIVE_MNEMONICS

compiler = BootstrapCompiler()

# 先初始化VM和加载表
compiler.vm.__init__()
compiler._load_mnemonic_table()
compiler._load_native_table()

vm = compiler.vm

# 检查原生指令表
print("=== Native instruction table ===")
for i, (mnemonic, opcode) in enumerate(NATIVE_MNEMONICS):
    entry_addr = 0x7800 + i * 8
    str_addr = vm._load_word_heap(entry_addr)
    stored_opcode = vm._load_word_heap(entry_addr + 4)
    stored_str = vm.read_string(str_addr)
    match = "✓" if stored_str == mnemonic and stored_opcode == opcode else "✗"
    if i < 10 or mnemonic in ("ADD", "MOV", "MOVI", "CALL", "RET"):
        print(f"  [{i:2d}] 0x{entry_addr:04X}: str@0x{str_addr:04X}=\"{stored_str}\" opcode=0x{stored_opcode:02X} expected=0x{opcode:02X} {match}")

# 测试词法分析器对 # 符号的处理
source = "ADD R3, #4\n"
lexer_result = compiler.test_lexer(source)
print("\n=== Lexer test: 'ADD R3, #4' ===")
for t in lexer_result['tokens']:
    print(f"  {t['type']:10s} {t['value']}")

# 测试完整编译
source2 = '@evolang "3.0"\n\n@locus test {\n    GUAXU: {\n        ADD R3, #4\n    }\n}\n'
result = compiler.compile_source(source2)
print(f"\n=== Compile test: ADD R3, #4 ===")
print(f"Success: {result['success']}")
if result.get('output_bytes'):
    output = result['output_bytes']
    header_size = result.get('evob_header_size', 14)
    bytecode = output[header_size:]
    print(f"Bytecode hex: {bytecode.hex()}")
    print(f"Bytecode bytes: {[hex(b) for b in bytecode]}")
