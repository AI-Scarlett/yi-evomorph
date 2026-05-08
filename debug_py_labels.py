#!/usr/bin/env python3
"""Debug: Instrument Python assembler to trace label resolution"""

import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evomorph.vm.extended_vm2 import ExtendedIChingVM2

base_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'asm_core.evoasm'), 'r') as f:
    core = f.read()

with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'asm_main.evoasm'), 'r') as f:
    main = f.read()

# Combine
lines = main.split('\n')
entry_line = ''
main_body_lines = []
found_entry = False
for line in lines:
    s = line.strip()
    if not found_entry and s.startswith('BRANCH') and '@asm_main' in s:
        entry_line = line
        found_entry = True
        continue
    if found_entry:
        main_body_lines.append(line)

main_body = '\n'.join(main_body_lines)
combined = entry_line + '\n' + core + '\n' + main_body

# Parse lines
lines = combined.strip().split('\n')
parsed_lines = []
for line in lines:
    line = line.strip()
    if not line or line.startswith(';') or line.startswith('#'):
        continue
    if line.endswith(':'):
        label = line[:-1].strip()
        parsed_lines.append(('LABEL', label))
        continue
    parts = line.split(None, 1)
    mnemonic = parts[0].upper()
    operands_str = parts[1].strip() if len(parts) > 1 else ''
    parsed_lines.append(('INSTR', mnemonic, operands_str))

# Count labels
label_positions = []
pc = 0
vm = ExtendedIChingVM2()

# Skip first pass, just track positions in pass1 style
MNEMONIC_MAP = {}  # Not used for IChing instructions
IMM_OPCODES = set()
NO_OPERAND_OPS = set()
ONE_REG_OPS = set()
TWO_REG_OPS = set()
TWO_REG_IMM_COMPAT = set()

for item in parsed_lines:
    if item[0] == 'LABEL':
        label_positions.append((item[1], pc))
        continue
    mnemonic = item[1]
    if mnemonic in vm.ICHING_OPCODE_REVERSE:
        pc += 4
        continue
    if '.' in mnemonic:
        parts = mnemonic.split('.', 1)
        if parts[0] in vm.ICHING_OPCODE_REVERSE and parts[1].isdigit():
            operands_str = item[2] if len(item) > 2 else ''
            has_imm = False
            if operands_str:
                for op in operands_str.split(','):
                    op = op.strip()
                    if op.startswith('#') or op.startswith('0x') or op.startswith('0X'):
                        has_imm = True
                        break
                    if not op.upper().startswith('R') and op not in vm.ICHING_OPCODE_REVERSE:
                        try:
                            int(op, 0)
                            has_imm = True
                            break
                        except ValueError:
                            has_imm = True
                            break
            pc += 8 if has_imm else 4
            continue
    # Skip native instructions
    continue

# Show label positions
print(f"Total parsed: {len(parsed_lines)} lines, {len(label_positions)} labels")
print(f"Final pc after all IChing instructions: {pc}")
print(f"\nLast 10 labels:")
for name, pos in label_positions[-10:]:
    print(f"  {name}: {pos} (0x{pos:04x})")

print(f"\n'asm_main' label search:")
for name, pos in label_positions:
    if name == 'asm_main':
        print(f"  asm_main: {pos} (0x{pos:04x})")

# Now do a full assembly and check
result = vm.assemble(combined)
print(f"\nFull assemble: {len(result)} bytes")
print(f"First 8 bytes: {result[:8].hex()}")
