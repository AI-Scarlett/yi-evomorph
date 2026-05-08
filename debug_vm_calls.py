#!/usr/bin/env python3
"""Instrument VM to trace ALL call_stack pushes/pops"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState

# Monkey-patch to trace call_stack
_orig_step = ExtendedIChingVM2.step
step_count = [0]
def traced_step(self):
    pc_before = self.pc
    cs_before = list(self.call_stack)
    r30_before = self.registers[30]
    _orig_step(self)
    cs_after = list(self.call_stack)
    step_count[0] += 1
    if len(cs_after) != len(cs_before):
        if len(cs_after) > len(cs_before):
            pushed = cs_after[-1]
            if pushed != 0x1a8:  # filter strcmp calls
                print(f"[{step_count[0]}] PUSH {pushed:#x} @ PC={pc_before:#x}, cs_depth {len(cs_before)}→{len(cs_after)}")
        else:
            popped = cs_before[-1]
            if popped != 0x1a8:
                print(f"[{step_count[0]}] POP {popped:#x} @ PC={pc_before:#x}, cs_depth {len(cs_before)}→{len(cs_after)}")
ExtendedIChingVM2.step = traced_step

# Also trace the CALL handler directly
_orig_iching = ExtendedIChingVM2._iching_extended
def traced_iching(self, opcode, sub_op, ext_mode, dst, src, imm):
    if opcode == 47 and sub_op == 1:  # ABUNDANCE.1 CALL
        cs_before = list(self.call_stack)
        _orig_iching(self, opcode, sub_op, ext_mode, dst, src, imm)
        print(f"  [CALL_TRACE] opcode=47 sub=1 pc={self.pc:#x} pushed={cs_before[-1] if cs_before else 'N/A' if not hasattr(self,'call_stack') else '?'}")
    else:
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
        print(f"\n[{step_count[0]}] VM {vm.state}, pc={vm.pc:#x}")
        break

print(f"\nFinal call_stack ({len(vm.call_stack)}): {[f'{x:#x}' for x in vm.call_stack]}")
print(f"R30={vm.registers[30]:#x}, R10={vm.registers[10]}")
print(f"PC={vm.pc:#x}")
