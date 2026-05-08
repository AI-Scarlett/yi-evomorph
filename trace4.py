#!/usr/bin/env python3
"""Full trace of all steps for EVB assembler with CREA.1 R0, R0, #42"""
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
        return f"@{pc:04x}: {name}.{sub_op} R{op1},R{op2},#{imm}(#{imm:#x})"
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

# Trace 250 steps, showing ALL
for i in range(250):
    pc_before = vm.pc
    instr = disasm_one(assembler_evob, pc_before)
    vm.step()
    
    if vm.state != VMState.RUNNING:
        print(f"[{i:3d}] {instr:52s} | state={vm.state}")
        break
    
    r8 = vm.registers[8]
    r10 = vm.registers[10]
    r30 = vm.registers[30]
    
    # Print all steps
    opcode = assembler_evob[pc_before] & 0x3F
    name = ICHING_NAMES.get(opcode, "?")
    if name in ("ABUNDANCE", "RETURN", "CREA", "BRANCH"):
        print(f"[{i:3d}] {instr:52s} | R8={r8:#06x} R10={r10:5d} R30={r30:#06x} ***")
    else:
        print(f"[{i:3d}] {instr:52s} | R8={r8:#06x} R10={r10:5d}")

print(f"\n=== Final state ===")
print(f"R0={vm.registers[0]}, R4={vm.registers[4]}, R5={vm.registers[5]}")
print(f"R8={vm.registers[8]:#x}, R9={vm.registers[9]:#x}, R10={vm.registers[10]}")
print(f"PC={vm.pc}, R30(LR)={vm.registers[30]}")

# Check output buffer
if vm.registers[10] > 0:
    out_bytes = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF+min(vm.registers[10], 32)])
    print(f"Output: {out_bytes.hex()}")
