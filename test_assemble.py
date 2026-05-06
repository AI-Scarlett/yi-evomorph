#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM,
    INPUT_BUF
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

# Try assembling the full compiler
full_asm = "JMP main\n" + STDLIB_ASM + LEXER_ASM + LOOKUP_ASM + CODEGEN_ASM + PARSER_ASM + MAIN_ASM
try:
    program = vm.assemble(full_asm)
    print(f"Assembled OK: {len(program)} bytes")
    vm.program = program
    vm.pc = 0
    vm.state = 1  # RUNNING
    vm.registers[0] = INPUT_BUF
    vm.registers[29] = vm.STACK_SIZE
    vm.run(max_cycles=500000)
    print(f"VM state: {vm.state}")
    print(f"R0: {vm.registers[0]}")
    print(f"R10: {vm.registers[10]}")
    print(f"R12: {vm.registers[12]:#x}")
    print(f"R15: {vm.registers[15]}")
except Exception as e:
    print(f"Assembly error: {e}")
