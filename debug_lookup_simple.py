#!/usr/bin/env python3
"""Test lookup_opcode by setting PC directly, with proper call_stack pre-population."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState
from build_assembler import build_opcode_table, OPCODE_TABLE

base_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    evob = bytearray(f.read())

# Find lookup_opcode
lookup_addr = None
for i in range(0, len(evob)-20, 4):
    if evob[i]==0x86 and (evob[i+1]&0x3F)==1 and evob[i+4]==0x86 and (evob[i+5]&0x3F)==1:
        if (evob[i+8]&0x3F)==61 and (evob[i+10]&0x1F)==4 and (evob[i+11]&0x1F)==0:
            if (evob[i+12]&0x3F)==63 and (evob[i+14]&0x1F)==5 and ((evob[i+13]>>6)&3)==2:
                if struct.unpack('<I',bytes(evob[i+16:i+20]))[0]==0x16000:
                    lookup_addr = i; break
print(f"lookup_opcode at {lookup_addr:#x}")

# Build opcode table
vm = ExtendedIChingVM2()
ot = build_opcode_table()
for i, b in enumerate(ot): vm.heap[OPCODE_TABLE+i] = b

LINE_BUF = 0x18100
for i, c in enumerate(b"CREA"): vm.heap[LINE_BUF+i] = c
vm.heap[LINE_BUF+4] = 0

vm.program = evob
vm.registers[0] = LINE_BUF
vm.registers[29] = vm.STACK_SIZE

# Pre-populate call_stack with a fake return address that will make the VM halt.
# The fake return address points to a safe location after the evob.
# When lookup_opcode returns, it will pop this address and try to execute there.
# Since it's past the end, the VM will error/halt.
# Actually, RETURN.0 checks call_stack first, then R30.
# If call_stack is empty, it uses R30. If R30 <= 0, it HALT.
# So we can just ensure R30 is 0 after lookup_opcode returns.

# Actually, the simplest approach: just run for a limited number of steps
# and check if R0 becomes 63.
vm.pc = lookup_addr
vm.state = VMState.RUNNING

print(f"\n=== Running lookup_opcode for ~2000 steps ===")
print(f"Entry 63 (CREA) at {OPCODE_TABLE + 63*14:#x}")
print(f"LINE_BUF: {bytes(vm.heap[LINE_BUF:LINE_BUF+6])}")

# Run with step counting
found = False
for step in range(2500):
    pc = vm.pc
    op = evob[pc] & 0x3F
    
    vm.step()
    
    # Check if we returned (call_stack went from 1→0) outside lookup_opcode
    # Actually, we started with call_stack empty. When strcmp is called, cs goes 0→1.
    # When strcmp returns, cs goes 1→0.
    # When lookup_opcode returns, cs goes from 1→0 (strcmp's push) 
    # ... that's wrong. lookup_opcode's final RETURN pops the FIRST entry that was there from a real caller.
    # Since we have no real caller, the final RETURN uses R30.
    
    # Let's just check if R0 becomes 63 at any point
    if vm.registers[0] == 63 and not found:
        found = True
        print(f"\n*** Step {step}: R0=63 (FOUND CREA!) ***")
    
    if vm.state != VMState.RUNNING:
        break

print(f"\nFinal state: R0={vm.registers[0]}, R5={vm.registers[5]:#x}, state={vm.state}")
print(f"Was CREA found: {found}")
