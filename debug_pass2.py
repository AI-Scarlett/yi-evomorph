#!/usr/bin/env python3
"""Deep debug: trace pass2 of assemble() for @asm_main resolution"""

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

# Manually trace the assemble() logic
vm = ExtendedIChingVM2()

# Parse
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

# Pass1
labels = {}
label_refs = []
pc = 0
for item in parsed_lines:
    if item[0] == 'LABEL':
        labels[item[1]] = pc
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

print(f"Pass1: asm_main = {labels.get('asm_main', 'NOT FOUND')}")

# Pass2
program = bytearray()
pc = 0
for item in parsed_lines:
    if item[0] == 'LABEL':
        labels[item[1]] = pc
        continue
    
    mnemonic = item[1]
    operands_str = item[2]
    
    iching_ext = None
    if '.' in mnemonic:
        parts = mnemonic.split('.', 1)
        if parts[0] in vm.ICHING_OPCODE_REVERSE and parts[1].isdigit():
            iching_ext = int(parts[1])
            mnemonic = parts[0]
    
    if mnemonic in vm.ICHING_OPCODE_REVERSE:
        old_opcode = vm.ICHING_OPCODE_REVERSE[mnemonic]
        byte1 = 0x80 | (old_opcode & 0x3F)
        
        if iching_ext is not None:
            sub_op = iching_ext & 0x3F
            has_imm_operand = False
            if operands_str:
                ops = [p.strip() for p in operands_str.split(',')]
                for op in ops:
                    if op.startswith('#') or op.startswith('@'):
                        has_imm_operand = True
                        break
                for op in ops:
                    if op and not op.startswith('R') and not op.startswith('#') and not op.startswith('@'):
                        if not op.isdigit() and not op.startswith('0x') and not op.startswith('0X'):
                            if op in labels:
                                has_imm_operand = True
                                break
            
            ext_mode = 2 if has_imm_operand else 1
            byte2 = (ext_mode << 6) | sub_op
            
            regs = [p.strip() for p in operands_str.split(',')] if operands_str else []
            dst_reg = 0
            src_reg = 0
            imm_val = 0
            
            is_branch = (old_opcode == 2)
            
            if len(regs) >= 1:
                r = regs[0].strip()
                if r.upper().startswith('R'):
                    try:
                        dst_reg = int(r[1:])
                    except ValueError:
                        dst_reg = 0
                elif r.startswith('@'):
                    label_name = r[1:]
                    print(f"DEBUG @ check: r='{r}', label_name='{label_name}', in labels: {label_name in labels}, value: {labels.get(label_name, 'N/A')}")
                    if label_name in labels:
                        imm_val = labels[label_name]
                        has_imm_operand = True
                elif is_branch:
                    try:
                        imm_val = int(r, 0)
                        has_imm_operand = True
                    except ValueError:
                        if r in labels:
                            imm_val = labels[r]
                            has_imm_operand = True
            
            # ... more operand handling
            
            byte3 = dst_reg & 0x1F
            byte4 = src_reg & 0x1F
            
            if has_imm_operand:
                ext_mode = 2
                byte2 = (ext_mode << 6) | sub_op
                program.extend([byte1, byte2, byte3, byte4])
                program.extend(struct.pack('<I', imm_val & 0xFFFFFFFF))
                pc += 8
                if pc <= 8:
                    print(f"  first instr: {byte1:02x} {byte2:02x} {byte3:02x} {byte4:02x} imm=0x{imm_val:08x}")
            else:
                ext_mode = 1
                byte2 = (ext_mode << 6) | sub_op
                program.extend([byte1, byte2, byte3, byte4])
                pc += 4
                if pc <= 4:
                    print(f"  first instr: {byte1:02x} {byte2:02x} {byte3:02x} {byte4:02x}")
        else:
            byte2 = 0
            program.extend([byte1, byte2, 0, 0])
            pc += 4
        continue
    
    # Native instructions
    continue

print(f"\nFinal program: {len(program)} bytes")
print(f"First 8 bytes: {bytes(program[:8]).hex()}")
