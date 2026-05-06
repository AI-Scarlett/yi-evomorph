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

# Check preprocessing
preprocessed = compiler._preprocess_source(evo_source)
print(f"Original lines: {len(evo_source.splitlines())}")
print(f"Preprocessed lines: {len(preprocessed.splitlines())}")

# Show first 30 lines of preprocessed source
print("\n=== First 30 lines of preprocessed source ===")
for i, line in enumerate(preprocessed.splitlines()[:30]):
    print(f'  {i:3d}: {line}')

# Check lexer
lexer_result = compiler.test_lexer(preprocessed)
print(f"\nLexer: success={lexer_result['success']}, tokens={lexer_result['token_count']}")
for t in lexer_result['tokens'][:20]:
    print(f"  {t['type']} {t['value']}")

# Check for GUAXU token
guaxu_tokens = [t for t in lexer_result['tokens'] if t['value'] == 'GUAXU']
print(f"\nGUAXU tokens: {len(guaxu_tokens)}")

# Check for locus token
locus_tokens = [t for t in lexer_result['tokens'] if t['value'] == 'locus']
print(f"locus tokens: {len(locus_tokens)}")

# Try compile
result = compiler.compile_source(evo_source)
print(f"\nCompile: success={result['success']}, locus_count={result.get('locus_count')}, output_size={result['output_size']}")
