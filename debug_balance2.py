#!/usr/bin/env python3
"""Find where call_stack becomes unbalanced"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState

call_log = []
ret_log = []
    
_orig_iching = ExtendedIChingVM2._iching_extended
def traced_iching(self, opcode, sub_op, ext_mode, dst, src, imm):
    global call_log, ret_log
    seq = len(call_log) + len(ret_log)
    if opcode == 47 and sub_op == 1:
        call_log.append((seq, list(self.call_stack), self.pc))
    elif opcode == 1 and sub_op == 0:
        ret_log.append((seq, list(self.call_stack), self.pc))
    _orig_iching(self, opcode, sub_op, ext_mode, dst, src, imm)    
ExtendedIChingVM2._iching_extended = traced_iching

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

for step in range(5000):
    vm.step()
    if vm.state != VMState.RUNNING:
        break

# Sort events by seq and simulate
full = []
for seq, cs, pc in call_log:
    full.append(('CALL', seq, pc, len(cs)))
for seq, cs, pc in ret_log:
    full.append(('RET', seq, pc, len(cs)))
full.sort(key=lambda x: x[1])

stack_sim = []  # simulate stack
for evt_type, seq, pc, cs_len in full:
    if evt_type == 'CALL':
        # pushed = pc (which is already past instruction+immediate)
        pushed = pc
        stack_sim.append(pushed)
        if pushed != 0x1a8:  # highlight non-strcmp calls
            print(f"  [{seq}] CALL pc={pc:#06x} → push {pushed:#06x}, depth={len(stack_sim)} ★")
    else:
        if stack_sim:
            popped = stack_sim.pop()
            if popped != 0x1a8:
                print(f"  [{seq}] RET pc={pc:#06x} ← pop {popped:#06x}, depth={len(stack_sim)} ★")

print(f"\nFinal simulated depth: {len(stack_sim)}")
print(f"Actual call_stack depth: {len(vm.call_stack)}")
print(f"Total CALLs: {len(call_log)}, RETs: {len(ret_log)}, diff: {len(call_log)-len(ret_log)}")
