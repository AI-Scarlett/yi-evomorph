#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM,
    INPUT_BUF, TOKEN_BUF, OUTPUT_BUF
)

c = BootstrapCompiler()
vm = c.vm
c._load_mnemonic_table()
c._load_native_table()

source = '@evolang "3.0"\n\n@locus test {\n    GUAXU: {\n        MOVI R0, #42\n        HLT\n    }\n}\n'
processed = c._preprocess_source(source)

# Load and run the full compiler
vm.load_string(INPUT_BUF, processed)
vm.load_assembled("JMP main\n" + STDLIB_ASM + LEXER_ASM + LOOKUP_ASM + CODEGEN_ASM + PARSER_ASM + MAIN_ASM)
vm.registers[0] = INPUT_BUF
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=500000)

print(f"VM state: {vm.state}")
print(f"R0 (output size): {vm.registers[0]}")
print(f"R10 (token count): {vm.registers[10]}")
print(f"R12 (output pos): {vm.registers[12]:#x}")
print(f"R13 (token index): {vm.registers[13]}")
print(f"R15 (locus count): {vm.registers[15]}")
print(f"Cycles: {vm.cycle_count}")

# Check tokens
token_count = vm.registers[10]
type_names = {1:"KEYWORD", 2:"IDENT", 3:"NUMBER", 4:"STRING", 5:"SYMBOL", 6:"MODIFIER"}
for i in range(min(token_count, 20)):
    addr = TOKEN_BUF + i * 8
    ttype = vm._load_word_heap(addr)
    tval = vm._load_word_heap(addr + 4)
    tname = type_names.get(ttype, f"?{ttype}")
    if ttype == 2:
        s = vm.read_string(tval) if tval > 0 else ""
        print(f"  Token[{i}]: {tname} '{s}' (addr={tval:#x})")
    elif ttype == 3:
        print(f"  Token[{i}]: {tname} {tval}")
    elif ttype == 5:
        c_val = chr(tval) if 32 <= tval < 127 else str(tval)
        print(f"  Token[{i}]: {tname} '{c_val}'")
    else:
        print(f"  Token[{i}]: {tname} {tval}")

# Check output buffer
output_start = OUTPUT_BUF + 64
for i in range(20):
    b = vm.heap[output_start + i]
    if b != 0:
        print(f"  output[{i}] = {b:#04x}")
