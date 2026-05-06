#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM,
    INPUT_BUF, TOKEN_BUF, OUTPUT_BUF, MNEMONIC_TABLE, MNEMONIC_STRINGS,
    NATIVE_TABLE, NATIVE_STRINGS
)
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

vm = ExtendedIChingVM2()
c = BootstrapCompiler()
c.vm = vm
c._load_mnemonic_table()
c._load_native_table()

source = '@evolang "3.0"\n\n@locus test {\n    GUAXU: {\n        MOVI R0, #42\n        HLT\n    }\n}\n'
processed = c._preprocess_source(source)
vm.load_string(INPUT_BUF, processed)

# Modify parser to write debug info to 0xFF00
# When lookup_native succeeds, write opcode to 0xFF00
# When codegen_emit_native is called, write to 0xFF04
debug_parser = PARSER_ASM.replace(
    '; 找到原生指令，R0=native_opcode\n    MOV R17, R0',
    '; 找到原生指令，R0=native_opcode\n    MOV R17, R0\n    MOVI R5, #0xFF00\n    STRB R5, R0'
)

full_asm = "JMP main\n" + STDLIB_ASM + LEXER_ASM + LOOKUP_ASM + CODEGEN_ASM + debug_parser + MAIN_ASM
program = vm.assemble(full_asm)
vm.program = program
vm.pc = 0
vm.state = 1
vm.registers[0] = INPUT_BUF
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=500000)

print(f"VM state: {vm.state}")
print(f"R0: {vm.registers[0]}")
print(f"R10: {vm.registers[10]}")
print(f"R12: {vm.registers[12]:#x}")
print(f"R15: {vm.registers[15]}")
print(f"Debug at 0xFF00: {vm.heap[0xFF00]:#x}")
print(f"Debug at 0xFF01: {vm.heap[0xFF01]:#x}")
print(f"Debug at 0xFF02: {vm.heap[0xFF02]:#x}")

# Check if parse_guaxu_block was even reached
# Let's check the token index progression
print(f"R13 (token index): {vm.registers[13]}")
