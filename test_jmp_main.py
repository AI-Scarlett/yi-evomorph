#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM
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

compiler = BootstrapCompiler()
evo_source = build_compiler_evo_source()

# Check preprocessed source - specifically the JMP main line
preprocessed = compiler._preprocess_source(evo_source)

# Find JMP lines
for i, line in enumerate(preprocessed.splitlines()):
    if 'JMP' in line and 'main' in line.lower():
        print(f"Line {i}: {line}")
    if 'JMP #' in line:
        print(f"Line {i} (resolved): {line}")

# Show first 5 and last 5 lines of GUAXU block
in_guaxu = False
guaxu_start = 0
for i, line in enumerate(preprocessed.splitlines()):
    if 'GUAXU' in line:
        in_guaxu = True
        guaxu_start = i
    if in_guaxu and '}' == line.strip() and i > guaxu_start + 2:
        print(f"\nGUAXU block: lines {guaxu_start} to {i}")
        # Show first 10 lines
        lines = preprocessed.splitlines()
        for j in range(guaxu_start, min(guaxu_start + 10, i + 1)):
            print(f"  {j}: {lines[j]}")
        # Show last 10 lines
        for j in range(max(guaxu_start, i - 10), i + 1):
            print(f"  {j}: {lines[j]}")
        break
