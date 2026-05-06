#!/usr/bin/env python3
"""详细追踪 pass1"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from build_assembler import (
    build_opcode_table, load_assembler_source,
    INPUT_BUF, OUTPUT_BUF, LABEL_TABLE, OPCODE_TABLE
)

vm = ExtendedIChingVM2()
opcode_table = build_opcode_table()
for i, b in enumerate(opcode_table):
    vm.heap[OPCODE_TABLE + i] = b

asm_source = load_assembler_source()
evob = vm.assemble(asm_source)

# Get the label addresses from Python assembler
label_map = vm.labels
print("Python assembler labels:", list(label_map.keys())[:10], "...")

# Simple test
test_source = '; comment\nCREA.1 R0, R0, #42\n'
src_bytes = test_source.encode('ascii') + b'\x00'
print(f"Test: {repr(test_source)}")

# Clean VM
vm2 = ExtendedIChingVM2()
for i, b in enumerate(opcode_table):
    vm2.heap[OPCODE_TABLE + i] = b
for i, b in enumerate(src_bytes):
    vm2.heap[INPUT_BUF + i] = b
for i in range(LABEL_TABLE, LABEL_TABLE + 0x4000):
    vm2.heap[i] = 0

vm2.program = bytearray(evob)
vm2.pc = 0
vm2.registers[0] = INPUT_BUF
vm2.registers[29] = vm2.STACK_SIZE

# Trace every step
steps = []
orig = vm2._step

def trace_step():
    pc = vm2.pc
    if pc < len(vm2.program):
        b1 = vm2.program[pc]
        t = (b1 >> 6) & 3
        if t == 2 and pc + 3 < len(vm2.program):
            op = b1 & 0x3F
            mod = vm2.program[pc + 1]
            sub = mod & 0x3F
            em = (mod >> 6) & 3
            d = vm2.program[pc + 2]
            s = vm2.program[pc + 3]
            imm = 0
            if em == 2 and pc + 7 < len(vm2.program):
                imm = struct.unpack('<I', bytes(vm2.program[pc+4:pc+8]))[0]
            
            # Label matching
            lbl = ''
            for name, addr in label_map.items():
                if pc == addr:
                    lbl = name
                    break
            
            r0 = vm2.registers[0]; r8 = vm2.registers[8]; r10 = vm2.registers[10]
            
            if op == 47 and sub == 1:  # CALL
                steps.append(f'PC={pc:5d} {lbl:20s} CALL → {imm} | R0={r0} R8={r8} R10={r10}')
            elif op == 1 and sub == 0:  # RET
                steps.append(f'PC={pc:5d} {lbl:20s} RET | R0={r0} R8={r8} R10={r10}')
            elif op == 2:  # BRANCH
                taken = False
                if sub == 1: taken = True
                elif sub == 2: taken = vm2.flag_zero
                elif sub == 3: taken = not vm2.flag_zero
                arrow = '→TAKEN' if taken else '→skip'
                steps.append(f'PC={pc:5d} {lbl:20s} BRANCH.{sub} {arrow} {imm} | R0={r0} R8={r8}')
            elif op == 0 and sub == 2:  # LDRB (RECV.2)
                addr = vm2.registers[d & 0x1F]
                val = vm2.heap[addr] if 0 <= addr < len(vm2.heap) else 0
                ch = chr(val) if 32 <= val < 127 else f'\\x{val:02x}'
                steps.append(f'PC={pc:5d} {lbl:20s} LDRB R{d&0x1f}=[{addr}]={val}(\'{ch}\') | R8={r8}')
    
    orig()

vm2._step = trace_step
vm2.run(max_cycles=500)

print(f'\nTrace ({len(steps)} steps):')
for s in steps:
    print(f'  {s}')
print(f'\nFinal: state={vm2.state} cycles={vm2.cycle_count} R0={vm2.registers[0]} R10={vm2.registers[10]}')
