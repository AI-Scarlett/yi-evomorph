#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, INPUT_BUF, TOKEN_BUF, STRPOOL_BUF
)
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

vm = ExtendedIChingVM2()
c = BootstrapCompiler()
c.vm = vm
c._load_mnemonic_table()
c._load_native_table()

def build_compiler_evo_source():
    from evomorph.bootstrap.native.bootstrap_compiler import LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM
    asm_code = "JMP main\n" + STDLIB_ASM + LEXER_ASM + LOOKUP_ASM + CODEGEN_ASM + PARSER_ASM + MAIN_ASM
    guaxu_lines = []
    for line in asm_code.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith(';'):
            continue
        guaxu_lines.append('        ' + line)
    
    evo_source = '@evolang "3.0"\n\n'
    evo_source += '@locus bootstrap_compiler {\n'
    evo_source += '    GUAXU: {\n'
    evo_source += '\n'.join(guaxu_lines) + '\n'
    evo_source += '    }\n'
    evo_source += '}\n'
    return evo_source

evo_source = build_compiler_evo_source()
processed = c._preprocess_source(evo_source)

vm.load_string(INPUT_BUF, processed)
lexer_asm = "JMP test_main\n" + STDLIB_ASM + LEXER_ASM + """
test_main:
    CALL lexer_tokenize
    HLT
"""
vm.load_assembled(lexer_asm)
vm.registers[0] = INPUT_BUF
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=500000)

# Check string pool usage
r11_final = vm.registers[11]
strpool_start = STRPOOL_BUF
strpool_used = r11_final - strpool_start
strpool_size = 0x2C000 - STRPOOL_BUF  # Until MNEMONIC_TABLE

print(f"String pool start: {strpool_start:#x}")
print(f"String pool end (R11): {r11_final:#x}")
print(f"String pool used: {strpool_used} bytes")
print(f"String pool size: {strpool_size} bytes")
print(f"String pool overflow: {strpool_used > strpool_size}")

# Check if string pool wrote into MNEMONIC_TABLE area
mnemonic_first = vm._load_word_heap(0x2C000)
print(f"\nMNEMONIC_TABLE[0] string addr: {mnemonic_first:#x}")
# If this is corrupted, the lookup tables are broken
