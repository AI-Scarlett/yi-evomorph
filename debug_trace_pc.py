#!/usr/bin/env python3
"""Trace PC trajectory to find where pass2 accidentally calls pass1"""
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
vm.pc = 0xc34
vm.registers[0] = INPUT_BUF
vm.registers[29] = vm.STACK_SIZE
vm.state = VMState.RUNNING

# Start tracing from step 4580
start_step = 4580
last_pc = -1
last_r30 = -1
last_cs_len = -1

for step in range(4660):
    pc = vm.pc
    cs = list(vm.call_stack)
    r30 = vm.registers[30]
    r10 = vm.registers[10]
    
    # Log from step 4580 onwards with PC and instruction bytes
    if step >= start_step:
        b0 = evob[pc] if pc < len(evob) else 0
        b1 = evob[pc+1] if pc+1 < len(evob) else 0
        op = b0 & 0x3F
        sub = b1 & 0x3F
        ext = (b1 >> 6) & 3
        is_call = (op == 47 and sub == 1)
        is_ret = (op == 1 and sub == 0)
        is_jump = (op == 2)
        
        if is_call or is_ret or step == start_step or step == start_step + 1 or cs != prev_cs or r30 != prev_r30:
            cs_str = f"[{len(cs)}]{','.join(f'{x:#x}' for x in cs[-3:])}" if cs else "[0]"
            print(f"[{step}] PC={pc:#06x} | OP={op:02d}.{sub} ext={ext} | CS={cs_str} | R30={r30:#06x} | R10={r10}")
    
    prev_pc = pc
    prev_cs = cs
    prev_r30 = r30
    vm.step()
    
    if vm.state != VMState.RUNNING:
        print(f"[{step}] VM {vm.state}, pc={vm.pc:#06x}")
        break

print(f"\n=== After {step+1} steps ===")
print(f"VM state: {vm.state}, PC: {vm.pc:#06x}")
print(f"R0={vm.registers[0]}, R30={vm.registers[30]:#06x}")
print(f"call_stack: {list(vm.call_stack)}")
