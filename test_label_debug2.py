#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, MNEMONICS, NATIVE_MNEMONICS
)

# Directly test _resolve_labels_in_block
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
    '    }',
]

compiler = BootstrapCompiler()

# Manually call the method
resolved = compiler._resolve_labels_in_block(
    guaxu_lines, iching_opcodes, native_opcodes, native_imm_always, native_no_operand
)

print("=== Resolved lines ===")
for i, line in enumerate(resolved):
    print(f'  {i:3d}: {line}')

# Check labels found
labels = {}
offset = 0
for line in guaxu_lines:
    stripped = line.strip()
    if not stripped or stripped.startswith('//'):
        continue
    parts = [p.strip().rstrip(',') for p in stripped.split(',')]
    if not parts or not parts[0]:
        continue
    raw_first = parts[0].strip()
    first = raw_first.rstrip(':')
    is_label = raw_first.endswith(':') or (stripped.rstrip().endswith(':')
                                            and first not in iching_opcodes
                                            and first not in native_opcodes)
    if is_label:
        labels[first] = offset
        print(f'  Found label: {first} at offset {offset}')
        continue
    if first in iching_opcodes:
        offset += 4
    elif first in native_opcodes:
        if first in native_no_operand:
            offset += 3
        elif first in native_imm_always:
            offset += 7
        else:
            has_imm = False
            for p in parts[1:]:
                p = p.strip()
                if p.startswith('#') or p.isdigit() or (p.startswith('0x') and len(p) > 2):
                    has_imm = True
                    break
            offset += 7 if has_imm else 3

print(f'\nLabels found: {labels}')
