#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM,
    INPUT_BUF, TOKEN_BUF
)
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

vm = ExtendedIChingVM2()
c = BootstrapCompiler()
c.vm = vm
c._load_mnemonic_table()
c._load_native_table()

def build_compiler_evo_source():
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

# Run just the lexer
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

token_count = vm.registers[10]
print(f"Token count: {token_count}")
print(f"Token buffer end: {TOKEN_BUF + token_count * 8:#x}")
print(f"Token buffer limit: 0x10FFF")

# Show first 10 and last 10 tokens
type_names = {1:"KEYWORD", 2:"IDENT", 3:"NUMBER", 4:"STRING", 5:"SYMBOL", 6:"MODIFIER"}
for i in list(range(min(10, token_count))) + list(range(max(0, token_count-10), token_count)):
    addr = TOKEN_BUF + i * 8
    ttype = vm._load_word_heap(addr)
    tval = vm._load_word_heap(addr + 4)
    tname = type_names.get(ttype, f"?{ttype}")
    if ttype == 2:
        s = vm.read_string(tval) if tval > 0 else ""
        print(f"  [{i:4d}] {tname:8s} '{s}'")
    elif ttype == 5:
        c_val = chr(tval) if 32 <= tval < 127 else str(tval)
        print(f"  [{i:4d}] {tname:8s} '{c_val}'")
    elif ttype == 3:
        print(f"  [{i:4d}] {tname:8s} {tval}")
    elif ttype == 4:
        s = vm.read_string(tval) if tval > 0 else ""
        print(f"  [{i:4d}] {tname:8s} \"{s}\"")
    else:
        print(f"  [{i:4d}] {tname:8s} {tval}")
