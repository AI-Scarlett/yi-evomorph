#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    MNEMONICS, NATIVE_MNEMONICS, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM
)

iching_opcodes = {m for m, _ in MNEMONICS}
native_opcodes = {m for m, _ in NATIVE_MNEMONICS}
native_imm_always = {"CMPI", "JMP", "JE", "JNE", "JL", "JLE", "JG", "JGE",
                     "JC", "JNC", "MOVI", "CALL"}
native_no_operand = {"NOP", "HLT", "RET", "PUSHA", "POPA"}

asm_code = "JMP main\n" + STDLIB_ASM + LEXER_ASM + LOOKUP_ASM + CODEGEN_ASM + PARSER_ASM + MAIN_ASM

offset = 0
instr_count = 0
label_count = 0
skip_count = 0

for line in asm_code.strip().split('\n'):
    stripped = line.strip()
    if not stripped or stripped.startswith(';') or stripped.startswith('//'):
        continue
    
    words = stripped.split()
    if not words:
        continue
    
    raw_first = words[0]
    first = raw_first.rstrip(':')
    is_label = raw_first.endswith(':') or (stripped.rstrip().endswith(':')
                                            and first not in iching_opcodes
                                            and first not in native_opcodes)
    if is_label:
        label_count += 1
        continue
    
    if first in iching_opcodes:
        offset += 4
        instr_count += 1
    elif first in native_opcodes:
        if first in native_no_operand:
            size = 3
        elif first in native_imm_always:
            size = 7
        else:
            has_imm = False
            for w in words[1:]:
                w = w.rstrip(',').lstrip(',')
                if w.startswith('#') or w.isdigit() or (w.startswith('0x') and len(w) > 2):
                    has_imm = True
                    break
            size = 7 if has_imm else 3
        offset += size
        instr_count += 1
    else:
        skip_count += 1
        if skip_count <= 10:
            print(f"  SKIPPED: '{first}' (full: '{stripped[:60]}')")

print(f"\nTotal bytecode size: {offset}")
print(f"Instructions: {instr_count}")
print(f"Labels: {label_count}")
print(f"Skipped lines: {skip_count}")
