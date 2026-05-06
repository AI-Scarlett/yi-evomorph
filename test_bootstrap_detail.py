#!/usr/bin/env python3
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM,
    INPUT_BUF, TOKEN_BUF, OUTPUT_BUF, HEADER_RESERVE
)
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

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

# Run the compiler and check intermediate state
result = compiler.compile_source(evo_source)

print(f"Compile success: {result['success']}")
print(f"Token count: {result['token_count']}")
print(f"Locus count: {result.get('locus_count', 'N/A')}")
print(f"Output size: {result['output_size']}")
print(f"Cycles: {result['cycles']}")

# Check the tokens - how many are IDENT type?
vm = compiler.vm
token_count = vm.registers[10]
ident_count = 0
number_count = 0
symbol_count = 0
other_count = 0
unknown_idents = set()

for i in range(min(token_count, 2000)):
    addr = TOKEN_BUF + i * 8
    ttype = vm._load_word_heap(addr)
    tval = vm._load_word_heap(addr + 4)
    if ttype == 2:  # IDENT
        ident_count += 1
        s = vm.read_string(tval) if tval > 0 else ""
        # Check if it's a known mnemonic
        from evomorph.bootstrap.native.bootstrap_compiler import MNEMONICS, NATIVE_MNEMONICS
        known = {m for m, _ in MNEMONICS} | {m for m, _ in NATIVE_MNEMONICS}
        if s not in known and not s.startswith('R'):
            unknown_idents.add(s)
    elif ttype == 3:
        number_count += 1
    elif ttype == 5:
        symbol_count += 1
    else:
        other_count += 1

print(f"\nToken breakdown:")
print(f"  IDENT: {ident_count}")
print(f"  NUMBER: {number_count}")
print(f"  SYMBOL: {symbol_count}")
print(f"  Other: {other_count}")
print(f"\nUnknown identifiers (first 20): {list(unknown_idents)[:20]}")

# Check the EVOB output
if result.get('output_bytes'):
    evob = result['output_bytes']
    if evob[:4] == b'EVOB':
        header_size = struct.unpack(">H", evob[6:8])[0]
        bytecode = evob[header_size:]
        print(f"\nBytecode size: {len(bytecode)} (expected ~6735)")
        
        # Count instructions in bytecode
        pos = 0
        iching_count = 0
        native_count = 0
        while pos < len(bytecode):
            b1 = bytecode[pos]
            itype = (b1 >> 6) & 3
            if itype == 1:  # Native
                b2 = bytecode[pos+1]
                has_imm = bool(b2 & 0x20)
                pos += 3
                if has_imm:
                    pos += 4
                native_count += 1
            elif itype == 2:  # IChing
                pos += 4
                iching_count += 1
            else:
                break
        print(f"  IChing instructions: {iching_count}")
        print(f"  Native instructions: {native_count}")
        print(f"  Total: {iching_count + native_count} (expected ~1257)")
