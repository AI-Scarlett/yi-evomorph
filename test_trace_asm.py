#!/usr/bin/env python3
"""Deep diagnostic: Trace EVB assembler execution for HALT.0"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

# Load assembler
base_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    assembler_evob = f.read()

# Simple source
source = "HALT.0\n"
source_bytes = source.encode('ascii') + b'\x00'

# Setup
from build_assembler import build_opcode_table, OPCODE_TABLE, INPUT_BUF, OUTPUT_BUF, LABEL_TABLE

vm = ExtendedIChingVM2()

# Pre-fill opcode table
opcode_table = build_opcode_table()
for i, byte_val in enumerate(opcode_table):
    vm.heap[OPCODE_TABLE + i] = byte_val

for i, byte_val in enumerate(source_bytes):
    vm.heap[INPUT_BUF + i] = byte_val

for i in range(LABEL_TABLE, LABEL_TABLE + 0x4000):
    vm.heap[i] = 0

vm.program = bytearray(assembler_evob)
vm.pc = 0
vm.registers[0] = INPUT_BUF
vm.registers[29] = vm.STACK_SIZE

# Trace execution: print brief state every few cycles
step = 0
while vm.state.value == 0 and step < 200:  # RUNNING
    old_pc = vm.pc
    
    # Decode current instruction
    if vm.pc < len(vm.program):
        b0, b1, b2, b3 = vm.program[vm.pc], vm.program[vm.pc+1], vm.program[vm.pc+2], vm.program[vm.pc+3]
        opcode = b0 & 0x3F
        instr_type = (b0 >> 6) & 0x03
        
        # Decode based on type
        if instr_type == 2:  # IChing extended
            sub_op = b1 & 0x3F
            ext_mode = (b1 >> 6) & 0x3
            if ext_mode == 2:
                imm = (b2) | (b3 << 8) | (vm.program[vm.pc+4] << 16) | (vm.program[vm.pc+5] << 24) if vm.pc + 5 < len(vm.program) else 0
                inst_size = 8
            else:
                dst = b2 & 0x1F
                src = b3 & 0x1F
                imm = None
                inst_size = 4
        elif instr_type == 0:  # IChing base
            sub_op = b1 & 0x3F
            dst = b2 & 0x1F
            src = b3 & 0x1F
            imm = None
            inst_size = 4
        else:
            inst_size = 4
        
        op_name = ExtendedIChingVM2.ICHING_OPCODE_MAP.get(opcode, f"OP_{opcode}")
        
        if step < 80:
            print(f"  step={step} pc=0x{old_pc:04x} [{op_name}.{sub_op}] R0=0x{vm.registers[0]:08x} R10=0x{vm.registers[10]:08x} R8=0x{vm.registers[8]:08x} R9=0x{vm.registers[9]:08x}")
    else:
        print(f"  step={step} pc=0x{old_pc:04x} OUT OF RANGE")
        break
    
    vm.step()
    step += 1

print(f"\nAfter {step} steps:")
print(f"  state={vm.state}, pc=0x{vm.pc:04x}")
print(f"  R0=0x{vm.registers[0]:08x}")
print(f"  R8=0x{vm.registers[8]:08x}")
print(f"  R9=0x{vm.registers[9]:08x}")
print(f"  R10=0x{vm.registers[10]:08x}")
print(f"  Output buffer first 32 bytes: {bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF+32]).hex()}")
