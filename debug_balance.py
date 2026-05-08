#!/usr/bin/env python3
"""Check call_stack push/pop balance - find where imbalance occurs"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState

# Patch the ABUNDANCE CALL and RETURN handlers to log AND count
_orig_iching = ExtendedIChingVM2._iching_extended
call_log = []
ret_log = []
    
def traced_iching(self, opcode, sub_op, ext_mode, dst, src, imm):
    if opcode == 47 and sub_op == 1:  # CALL
        call_log.append((len(call_log)+len(ret_log), list(self.call_stack), self.pc))
    elif opcode == 1 and sub_op == 0:  # RET
        ret_log.append((len(call_log)+len(ret_log), list(self.call_stack), self.pc))
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
        print(f"[{step}] HALTED")
        break

print(f"\nTotal CALLs: {len(call_log)}, RETs: {len(ret_log)}")
print(f"Final call_stack depth: {len(vm.call_stack)}")
print(f"Expected depth: {len(call_log) - len(ret_log)}")

# Show last few CALLs and RETs
print(f"\nLast 5 CALLs:")
for i, cs, pc in call_log[-5:]:
    print(f"  seq={i}, CS={[f'{x:#x}' for x in cs]}, pc_before={pc:#x}")
print(f"\nLast 5 RETs:")
for i, cs, pc in ret_log[-5:]:
    print(f"  seq={i}, CS={[f'{x:#x}' for x in cs]}, pc_before={pc:#x}")

# Show all non-strcmp CALLs and RETs
print(f"\n--- All non-strcmp events ---")
last_event_seq = 0
for i, cs, pc in call_log:
    if len(calls := len(call_log)): pass
    # We need the pushed value which is PC+8
    # For CALL at pc, pushed = pc + 8 (since ABUNDANCE.1 with ext=2 is 8 bytes)
    # Actually, let me just check the call_stack after each CALL
    label = f"CALL from {pc:#x}"
    print(f"  [{i}] {label}, CS_depth={len(cs)+1}")
for i, cs, pc in ret_log:
    label = f"RET from {pc:#x}"
    print(f"  [{i}] {label}, CS_depth={len(cs)}")

# Check if any CALL didn't have a matching RET by analyzing the sequence
full_events = []
for i, cs, pc in call_log:
    full_events.append(('CALL', i, pc, len(cs)))
for i, cs, pc in ret_log:
    full_events.append(('RET', i, pc, len(cs)))
full_events.sort(key=lambda x: x[1])

stack_sim = []
for evt_type, seq, pc, cs_len in full_events:
    if evt_type == 'CALL':
        stack_sim.append(pc + 8)  # return addr
    else:
        if stack_sim:
            stack_sim.pop()
    if evt_type == 'CALL':
        print(f"  seq={seq}: CALL pc={pc:#x} → push {pc+8:#x}, depth={len(stack_sim)}")
    else:
        print(f"  seq={seq}: RET pc={pc:#x}, depth={len(stack_sim)}")
