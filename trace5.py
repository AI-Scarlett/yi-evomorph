#!/usr/bin/env python3
"""Extended trace - show when R10 changes and when WELL/POP instructions execute"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState
from build_assembler import build_opcode_table, OPCODE_TABLE, INPUT_BUF, OUTPUT_BUF, LABEL_TABLE
import struct

base_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    assembler_evob = f.read()

ICHING_NAMES = {
    0: "RECV", 1: "RETURN", 2: "BRANCH", 6: "PUSH_UP", 9: "SHOCK",
    12: "MICRO", 13: "ABOUND", 17: "ALLOC", 22: "WELL", 24: "GATHER",
    38: "MUT", 46: "CAST", 47: "ABUNDANCE", 48: "CONTEMPLATE",
    56: "HALT", 61: "FELLOWSHIP", 62: "MATE", 63: "CREA",
}

def disasm_one(prog, pc):
    if pc + 3 >= len(prog):
        return f"@{pc:04x}: ???"
    byte1 = prog[pc]
    opcode = byte1 & 0x3F
    modifier = prog[pc + 1]
    op1 = prog[pc + 2]
    op2 = prog[pc + 3]
    ext_mode = (modifier >> 6) & 0x03
    sub_op = modifier & 0x3F
    name = ICHING_NAMES.get(opcode, f"OP{opcode}")
    if ext_mode == 2 and pc + 7 < len(prog):
        imm = struct.unpack('<I', bytes(prog[pc+4:pc+8]))[0]
        return f"@{pc:04x}: {name}.{sub_op} R{op1},R{op2},#{imm}"
    else:
        return f"@{pc:04x}: {name}.{sub_op} R{op1},R{op2}"

source = "  CREA.1 R0, R0, #42\n"
source_bytes = source.encode('ascii') + b'\x00'

vm = ExtendedIChingVM2()
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
vm.state = VMState.RUNNING

last_r10 = 0
last_r8 = 0

for i in range(500):
    pc_before = vm.pc
    instr = disasm_one(assembler_evob, pc_before)
    
    opcode = assembler_evob[pc_before] & 0x3F
    modifier = assembler_evob[pc_before + 1]
    sub_op = modifier & 0x3F
    
    # Read current R4 value for diagnostics  
    r4_before = vm.registers[4]
    r5_before = vm.registers[5]
    
    vm.step()
    
    if vm.state != VMState.RUNNING:
        print(f"[{i:4d}] {instr:55s} | state={vm.state} *** STOPPED ***")
        break
    
    r8 = vm.registers[8]
    r10 = vm.registers[10]
    r4 = vm.registers[4]
    r5 = vm.registers[5]
    
    # Track key changes
    changes = []
    if r10 != last_r10:
        changes.append(f"R10: {last_r10}->{r10}")
    if r8 != last_r8:
        changes.append(f"R8: {last_r8:#x}->{r8:#x}")
    
    # Only print when something interesting happens
    name = ICHING_NAMES.get(opcode, "?")
    marker = ""
    if changes:
        marker = f" <<< {' '.join(changes)}"
    
    # Print instructions at key addresses and state changes
    important_addrs = {0x534, 0x584, 0x588, 0x58c, 0x590, 0x594, 0x598, 
                       0x5a0, 0x5c0, 0x5d0, 0x5f0, 0x5f4, 0x5fc, 0x600}
    
    if pc_before in important_addrs or changes or name in ("GATHER", "ABUNDANCE", "RETURN", "CREA", "ABUNDANCE", "WELL"):
        print(f"[{i:4d}] {instr:55s} | R4={r4:#06x} R5={r5:#06x} R8={r8:#06x} R10={r10:5d}{marker}")
    
    last_r10 = r10
    last_r8 = r8

print(f"\n=== Final state at step {i} ===")
print(f"R0={vm.registers[0]}, R4={vm.registers[4]:#x}, R5={vm.registers[5]:#x}")
print(f"R8={vm.registers[8]:#x}, R9={vm.registers[9]:#x}, R10={vm.registers[10]}")
print(f"PC={vm.pc}, R30(LR)={vm.registers[30]}")
print(f"State={vm.state}")

# Dump source buffer to see what's at specific positions
p = 0x1000
while p < 0x1030:
    c = vm.heap[p]
    print(f"  [{p:#06x}] = {c:3d} ({chr(c) if 32 <= c < 127 else '.'})")
    p += 1
