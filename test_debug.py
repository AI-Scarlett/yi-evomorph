#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler

compiler = BootstrapCompiler()

source2 = '@evolang "3.0"\n\n@locus first {\n    GUAXU: {\n        CREA R0, R1\n    }\n}\n\n@locus second {\n    GUAXU: {\n        SYNC\n        FELLOWSHIP R2, R3\n    }\n}\n'

# First test the lexer
lexer_result = compiler.test_lexer(source2)
print('=== Lexer output ===')
print(f'Token count: {lexer_result["token_count"]}')
for i, t in enumerate(lexer_result['tokens']):
    print(f'  [{i:3d}] {t["type"]:10s} {t["value"]}')

# Then test full compilation
result = compiler.compile_source(source2)
print(f'\n=== Compilation result ===')
print(f'Success: {result["success"]}')
print(f'Locus count: {result.get("evob_locus_count", "N/A")}')
print(f'Token count: {result["token_count"]}')
if 'evob_locus_offsets' in result:
    print(f'Offsets: {result["evob_locus_offsets"]}')
if 'instructions' in result:
    print(f'Instructions:')
    for instr in result['instructions']:
        mod_str = f' mod=0x{instr["modifier"]:02x}' if instr['modifier'] else ''
        print(f'  {instr["mnemonic"]} R{instr["op1"]}, R{instr["op2"]}{mod_str}')

# Check keyword strings in memory
vm = compiler.vm
print(f'\n=== Keyword strings in memory ===')
for addr, name in [(0x7700, "evolang"), (0x7708, "locus"), (0x770E, "xiangci"), (0x7716, "meta_locus"), (0x7720, "GUAXU")]:
    s = vm.read_string(addr)
    print(f'  0x{addr:04X}: "{s}" (expected: "{name}")')
