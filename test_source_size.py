#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM,
    INPUT_BUF
)

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
print(f"Source size: {len(evo_source)} chars")
print(f"INPUT_BUF: 0x{INPUT_BUF:x} = {INPUT_BUF}")
print(f"INPUT_BUF area: 0x1000-0x1FFF = 4096 bytes (4KB)")
print(f"Source exceeds INPUT_BUF: {len(evo_source) > 4096}")

# The source is too large for the 4KB input buffer!
# Need to increase INPUT_BUF or reduce source size
