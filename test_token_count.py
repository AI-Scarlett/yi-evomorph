#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM
)

asm_code = "JMP main\n" + STDLIB_ASM + LEXER_ASM + LOOKUP_ASM + CODEGEN_ASM + PARSER_ASM + MAIN_ASM

# Count approximate tokens
lines = asm_code.strip().split('\n')
total_tokens = 0
for line in lines:
    stripped = line.strip()
    if not stripped or stripped.startswith(';') or stripped.startswith('//'):
        continue
    # Each word, symbol, number is a token
    # Count @ as token, { } : , # as tokens
    import re
    tokens = re.findall(r'@|[a-zA-Z_]\w*|\d+|0x[0-9a-fA-F]+|"[^"]*"|[{}:,#.()]', stripped)
    total_tokens += len(tokens)

print(f"Source lines: {len(lines)}")
print(f"Approximate tokens: {total_tokens}")

# Also count with the .evo wrapper
evo_wrapper_tokens = 10  # @evolang "3.0" @locus bootstrap_compiler { GUAXU : { } }
print(f"Total with wrapper: {total_tokens + evo_wrapper_tokens}")
