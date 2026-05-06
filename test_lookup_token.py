#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM,
    INPUT_BUF, TOKEN_BUF, OUTPUT_BUF, NATIVE_TABLE, NATIVE_STRINGS
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

full_asm = "JMP main\n" + STDLIB_ASM + LEXER_ASM + LOOKUP_ASM + CODEGEN_ASM + PARSER_ASM + MAIN_ASM
program = vm.assemble(full_asm)
vm.program = program
vm.pc = 0
vm.state = 1
vm.registers[0] = INPUT_BUF
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=500000)

# Check Token[10] (MOVI) string
token_count = vm.registers[10]
for i in range(token_count):
    addr = TOKEN_BUF + i * 8
    ttype = vm._load_word_heap(addr)
    tval = vm._load_word_heap(addr + 4)
    if ttype == 2:  # IDENT
        s = vm.read_string(tval) if tval > 0 else ""
        if s in ("MOVI", "HLT", "GUAXU", "locus"):
            print(f"Token[{i}]: IDENT '{s}' addr={tval:#x}")
            # Test lookup_native with this address
            vm2 = ExtendedIChingVM2()
            c2 = BootstrapCompiler()
            c2.vm = vm2
            c2._load_mnemonic_table()
            c2._load_native_table()
            test_asm = "JMP t\n" + STDLIB_ASM + LOOKUP_ASM + f"\nt: MOVI R0, #{tval}\nCALL lookup_native\nHLT\n"
            vm2.load_assembled(test_asm)
            vm2.registers[29] = vm2.STACK_SIZE
            vm2.run(max_cycles=10000)
            print(f"  lookup_native result: {vm2.registers[0]:#x}")
