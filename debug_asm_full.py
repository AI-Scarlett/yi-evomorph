#!/usr/bin/env python3
"""Run EVB assembler from asm_main with proper entry, trace pass2 key states"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState
from build_assembler import build_opcode_table, OPCODE_TABLE, INPUT_BUF, OUTPUT_BUF, LABEL_TABLE

base_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    evob = bytearray(f.read())

vm = ExtendedIChingVM2()
ot = build_opcode_table()
for i,b in enumerate(ot): vm.heap[OPCODE_TABLE+i]=b

# Test source: CREA.1 R0, R0, #42
source = "  CREA.1 R0, R0, #42\n"
sb = source.encode('ascii')+b'\x00'
for i,b in enumerate(sb): vm.heap[INPUT_BUF+i]=b
for i in range(LABEL_TABLE, LABEL_TABLE+0x4000): vm.heap[i]=0
for i in range(OUTPUT_BUF, OUTPUT_BUF+0x1000): vm.heap[i]=0
for i in range(0x18100, 0x18200): vm.heap[i]=0

# Find asm_main: PUSH_UP.1 R4; FELLOWSHIP.0 R4,R0; ABUNDANCE.1 #pass1; CREA.1 R0,R0,#0x1000; ABUNDANCE.1 #pass2
# Look for: PUSH_UP.1 R4,R4 (0x86, 0x41, 0x04, 0x04) then FELLOWSHIP.0 R4,R0 (0xBD, 0x40, 0x04, 0x00)
asm_main = None
for i in range(0xc00, len(evob)-4, 4):
    if evob[i]==0x86 and (evob[i+1]&0x3F)==1 and evob[i+4]==0xBD and (evob[i+5]&0x3F)==0 and (evob[i+6]&0x1F)==4:
        asm_main = i; break
print(f"asm_main at {asm_main:#x}")

vm.program = evob
vm.pc = asm_main
vm.registers[0] = INPUT_BUF
vm.registers[29] = vm.STACK_SIZE
vm.state = VMState.RUNNING

# Trace with key events
in_pass1 = True
in_pass2 = False
pass1_done_step = None
pass2_start_step = None
last_r10 = -1
emit_events = []  # (step, r9, byte)

for step in range(10000):
    pc = vm.pc
    op = evob[pc] & 0x3F
    sub = evob[pc+1] & 0x3F
    
    r10_b = vm.registers[10]
    r8_b = vm.registers[8]
    r9_b = vm.registers[9]
    r0_b = vm.registers[0]
    
    vm.step()
    
    # Detect pass1→pass2 transition
    if in_pass1 and vm.pc >= 0x604 and vm.pc <= 0x610:
        in_pass1 = False
        in_pass2 = True
        pass2_start_step = step
        print(f"\n[{step}] === PASS2 STARTED === R8={vm.registers[8]:#x} R9={vm.registers[9]:#x}")
    
    # Detect byte emission (ALLOC.2 to output area)
    if (evob[pc] & 0x3F) == 17 and (evob[pc+1] & 0x3F) == 2:  # ALLOC.2
        if 0x11000 <= vm.registers[9] <= 0x11800:
            byte_written = vm.registers[r0_b & 0x1F] & 0xFF
            emit_events.append((step, r9_b, byte_written))
    
    if vm.registers[10] != r10_b:
        if in_pass2:
            print(f"[{step}] R10: {r10_b} -> {vm.registers[10]} (emitted byte)")
    
    if vm.state != VMState.RUNNING:
        print(f"\n[{step}] VM HALTED/ERROR. State={vm.state}")
        break

print(f"\n=== Results ===")
print(f"R0={vm.registers[0]}, R10={vm.registers[10]}, R8={vm.registers[8]:#x}")
print(f"Cycles: {vm.cycle_count}")

if vm.registers[10] > 0:
    out = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF+vm.registers[10]])
    print(f"Output ({len(out)} bytes): {out.hex()}")
    expected = bytes([0xBF, 0x81, 0x00, 0x00, 0x2a, 0x00, 0x00, 0x00])
    print(f"Expected: {expected.hex()}")
    if out == expected: print("MATCH!")
    else: print("MISMATCH!")

if len(emit_events) > 0:
    print(f"\nEmit events: {emit_events[:10]}")
