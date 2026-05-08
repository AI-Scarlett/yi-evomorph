#!/usr/bin/env python3
"""Trace pass2 execution for CREA.1"""
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
    12: "MICRO", 17: "ALLOC", 22: "WELL", 24: "GATHER",
    38: "MUT", 46: "CAST", 47: "ABUNDANCE", 56: "HALT",
    61: "FELLOWSHIP", 62: "MATE", 63: "CREA",
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

in_pass2 = False
last_r10 = 0
last_r8 = 0

for i in range(2000):
    pc_before = vm.pc
    instr = disasm_one(assembler_evob, pc_before)
    opcode = assembler_evob[pc_before] & 0x3F
    
    # Check if we're entering pass2
    if opcode == 47 and not in_pass2:  # ABUNDANCE
        # Check if this CALL targets pass2
        ext_mode = (assembler_evob[pc_before + 1] >> 6) & 0x03
        if ext_mode == 2:
            imm = struct.unpack('<I', bytes(assembler_evob[pc_before+4:pc_before+8]))[0]
            # pass2 starts around 0x600+, so imm > 0x600 likely targets pass2
            if imm > 0x600:
                in_pass2 = True
                print(f"\n=== Entering pass2 at step {i} (CALL to {imm:#x}) ===\n")
    
    r8_before = vm.registers[8]
    r10_before = vm.registers[10]
    
    vm.step()
    
    if vm.state != VMState.RUNNING:
        print(f"[{i:4d}] {instr:55s} | state={vm.state}")
        break
    
    r8 = vm.registers[8]
    r10 = vm.registers[10]
    r9 = vm.registers[9]
    r30 = vm.registers[30]
    
    changes = []
    if r10 != last_r10:
        changes.append(f"R10:{last_r10}->{r10}")
    if r8 != last_r8:
        changes.append(f"R8:{last_r8:#x}->{r8:#x}")
    
    if in_pass2 or changes:
        marker = f"  {' <<< '+', '.join(changes) if changes else ''}"
        name = ICHING_NAMES.get(opcode, "?")
        if name in ("ALLOC", "ABUNDANCE", "RETURN", "GATHER") or changes:
            print(f"[{i:4d}] {instr:55s} | R9={r9:#06x} R10={r10:5d}{marker}")
    
    last_r10 = r10
    last_r8 = r8
    
    if in_pass2 and r10 > 0 and changes:
        # Check output buffer
        out = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF+r10])
        print(f"       Output so far: {out.hex()}")

print(f"\n=== Final ===")
print(f"R0={vm.registers[0]}, R6={vm.registers[6]}, R7={vm.registers[7]}")
print(f"R8={vm.registers[8]:#x}, R9={vm.registers[9]:#x}, R10={vm.registers[10]}")
print(f"R11={vm.registers[11]}, R12={vm.registers[12]}, R13={vm.registers[13]}")
print(f"State={vm.state}, PC={vm.pc}")
if vm.registers[10] > 0:
    out = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF+min(vm.registers[10], 32)])
    print(f"Output: {out.hex()}")
