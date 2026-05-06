#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import MNEMONICS, NATIVE_MNEMONICS

iching_opcodes = {m for m, _ in MNEMONICS}
native_opcodes = {m for m, _ in NATIVE_MNEMONICS}
native_imm_always = {"CMPI", "JMP", "JE", "JNE", "JL", "JLE", "JG", "JGE",
                     "JC", "JNC", "MOVI", "CALL"}
native_no_operand = {"NOP", "HLT", "RET", "PUSHA", "POPA"}

guaxu_lines = [
    '        JMP main',
    '        strlen:',
    '        PUSH R4',
    '        MOVI R5, #0',
    '        strlen_loop:',
    '        LDRB R0, R4',
    '        CMPI R0, #0',
    '        JE strlen_done',
    '        INC R4',
    '        INC R5',
    '        JMP strlen_loop',
    '        strlen_done:',
    '        MOV R0, R5',
    '        POP R4',
    '        RET',
    '        main:',
    '        MOVI R0, #42',
    '        HLT',
]

offset = 0
for line in guaxu_lines:
    stripped = line.strip()
    words = stripped.split()
    if not words:
        continue
    raw_first = words[0]
    first = raw_first.rstrip(':')
    is_label = raw_first.endswith(':') or (stripped.rstrip().endswith(':')
                                            and first not in iching_opcodes
                                            and first not in native_opcodes)
    if is_label:
        print(f'  LABEL: {first} at offset {offset}')
        continue
    if first in iching_opcodes:
        size = 4
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
    else:
        print(f'  UNKNOWN: {first} (not in iching or native opcodes)')
        continue
    print(f'  INSTR: {first} size={size} offset={offset} -> {offset+size}')
    offset += size

print(f'\nTotal bytecode size: {offset}')
