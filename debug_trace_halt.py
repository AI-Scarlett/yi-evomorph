#!/usr/bin/env python3
"""Trace EVB assembler execution to find why VM doesn't HALT"""
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

source = "  CREA.1 R0, R0, #42\n"
sb = source.encode('ascii')+b'\x00'
for i,b in enumerate(sb): vm.heap[INPUT_BUF+i]=b
for i in range(LABEL_TABLE, LABEL_TABLE+0x4000): vm.heap[i]=0
for i in range(OUTPUT_BUF, OUTPUT_BUF+0x1000): vm.heap[i]=0

vm.program = evob
vm.pc = 0xc34  # asm_main entry
vm.registers[0] = INPUT_BUF
vm.registers[29] = vm.STACK_SIZE
vm.state = VMState.RUNNING

# Track call_stack changes
prev_call_stack = []
prev_r30 = 0
r10_changes = []
halt_check_addr = 0xc5c  # RETURN.1 HLT

asmmain_call_depth = 0  # track calls to pass1/pass2 from asm_main
pass2_entry_count = 0

for step in range(5000):
    pc = vm.pc
    call_stack = list(vm.call_stack) if hasattr(vm, 'call_stack') else []
    r30 = vm.registers[30]
    r10 = vm.registers[10]
    r8 = vm.registers[8]
    r9 = vm.registers[9]
    
    # Detect call_stack changes
    if len(call_stack) != len(prev_call_stack):
        if len(call_stack) > len(prev_call_stack):
            print(f"[{step}] CALL: pc={pc:#x} → push {call_stack[-1]:#x}, stack_depth={len(call_stack)}")
        else:
            print(f"[{step}] RET: pc={pc:#x}, popped, stack_depth={len(call_stack)}")
    
    if r30 != prev_r30:
        if r30 >= 0xc00:
            print(f"[{step}] R30(LR) changed: {prev_r30:#x} → {r30:#x}, pc={pc:#x}")
    
    # Track R10 changes
    if step > 0 and r10 != vm.registers[10]:
        r10_changes.append((step, pc, vm.registers[10], vm.registers[8], vm.registers[9]))
    
    vm.step()
    prev_call_stack = call_stack
    prev_r30 = r30
    
    # Check if we hit asm_main RETURN.1
    if vm.pc == halt_check_addr:
        print(f"[{step}] → PC=0xc5c (RETURN.1 HLT)")
    
    if vm.state != VMState.RUNNING:
        print(f"[{step}] VM {vm.state}, pc={vm.pc:#x}")
        break

print(f"\n=== After {step+1} steps ===")
print(f"VM state: {vm.state}, PC: {vm.pc:#x}")
print(f"R0={vm.registers[0]}, R8={vm.registers[8]:#x}, R9={vm.registers[9]:#x}, R10={vm.registers[10]}")
print(f"R30={vm.registers[30]:#x}")
print(f"call_stack: {list(vm.call_stack) if hasattr(vm, 'call_stack') else 'N/A'}")
print(f"Last 10 R10 changes: {r10_changes[-10:]}")

# Check output
if vm.registers[10] > 0:
    out = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF+vm.registers[10]])
    print(f"Output: {out.hex()}")
