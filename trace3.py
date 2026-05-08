#!/usr/bin/env python3
"""Step-by-step trace of EVB assembler with CREA.1 R0, R0, #42"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState
from build_assembler import build_opcode_table, OPCODE_TABLE, INPUT_BUF, OUTPUT_BUF, LABEL_TABLE
import struct

base_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    assembler_evob = f.read()

# Build a label table for the assembler.evob itself (for disassembly)
def find_labels(prog):
    labels = {}
    pc = 0
    while pc < len(prog) - 3:
        byte1 = prog[pc]
        opcode = byte1 & 0x3F
        modifier = prog[pc + 1]
        ext_mode = (modifier >> 6) & 0x03
        sub_op = modifier & 0x3F
        
        if opcode == 1 and sub_op == 1:  # HLT
            break
        if opcode == 2 and sub_op == 1:  # JMP
            if ext_mode == 2 and pc + 7 < len(prog):
                imm = struct.unpack('<I', bytes(prog[pc+4:pc+8]))[0]
                labels[imm] = f"L_{imm:x}"
        pc += 4 if ext_mode != 2 else 8
    return labels

# IChing opcode names
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
    instr = f"@{pc:04x}: {name}.{sub_op}"
    
    if ext_mode == 2 and pc + 7 < len(prog):
        imm = struct.unpack('<I', bytes(prog[pc+4:pc+8]))[0]
        instr += f" R{op1}, R{op2}, #{imm} (#{imm:#x})"
    else:
        instr += f" R{op1}, R{op2}"
    
    return instr

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

# Trace first 200 steps
trace_count = 0
while vm.state == VMState.RUNNING and trace_count < 300:
    pc_before = vm.pc
    instr = disasm_one(assembler_evob, pc_before)
    
    # Show relevant state
    r0 = vm.registers[0]
    r6 = vm.registers[6]
    r7 = vm.registers[7]
    r8 = vm.registers[8]
    r9 = vm.registers[9]
    r10 = vm.registers[10]
    r11 = vm.registers[11]
    r12 = vm.registers[12]
    r13 = vm.registers[13]
    r30 = vm.registers[30]
    
    vm.step()
    
    # Only print interesting instructions
    name = ICHING_NAMES.get(assembler_evob[pc_before] & 0x3F, "?")
    if name in ("ABUNDANCE", "RETURN", "CREA", "BRANCH", "FELLOWSHIP") or pc_before < 20 or r10 != 0:
        print(f"  [{trace_count:3d}] {instr:50s} | R0={r0:5d} R6={r6:3d} R7={r7:3d} R8={r8:#06x} R9={r9:#06x} R10={r10:5d} R11={r11:3d} R12={r12:3d} R13={r13:5d} R30={r30:5d}")
    
    trace_count += 1

print(f"\nTotal steps: {trace_count}, state: {vm.state}")
print(f"Final R10 (byte count): {vm.registers[10]}")
print(f"Final R8 (cursor): {vm.registers[8]}")
print(f"Final R9 (output ptr): {vm.registers[9]}")
