#!/usr/bin/env python3
"""追踪 EVB 汇编器的函数调用过程"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from build_assembler import (
    build_opcode_table, load_assembler_source,
    INPUT_BUF, OUTPUT_BUF, LABEL_TABLE, OPCODE_TABLE
)

vm = ExtendedIChingVM2()
vm.verbose = False

# Load assembler
opcode_table = build_opcode_table()
for i, b in enumerate(opcode_table):
    vm.heap[OPCODE_TABLE + i] = b

asm_source = load_assembler_source()
evob = vm.assemble(asm_source)

vm.program = bytearray(evob)
vm.pc = 0

# Simple test: one instruction
test = 'CREA.1 R0, R0, #42\n'
src = test.encode('ascii') + b'\x00'
for i, b in enumerate(src):
    vm.heap[INPUT_BUF + i] = b
for i in range(LABEL_TABLE, LABEL_TABLE + 0x4000):
    vm.heap[i] = 0

vm.registers[0] = INPUT_BUF
vm.registers[29] = vm.STACK_SIZE

# Instrument to track function calls
call_log = []
orig_step = vm._step

def instrumented_step():
    pc = vm.pc
    if pc < len(vm.program):
        b1 = vm.program[pc]
        if (b1 >> 6) == 2 and pc + 7 < len(vm.program):
            op = b1 & 0x3F
            mod = vm.program[pc + 1]
            sub = mod & 0x3F
            em = (mod >> 6) & 3
            if op == 47 and sub == 1 and em == 2:  # CALL
                addr = struct.unpack('<I', bytes(vm.program[pc+4:pc+8]))[0]
                call_log.append(('CALL', pc, addr, vm.registers[0]))
            elif op == 1 and sub == 0:  # RET
                call_log.append(('RET', pc, vm.registers[0], vm.registers[10]))
    orig_step()

vm._step = instrumented_step

try:
    vm.run(max_cycles=50000)
    print(f'State: {vm.state}, Cycles: {vm.cycle_count}')
    print(f'R0: {vm.registers[0]}, R10: {vm.registers[10]}')
    print(f'R8: {vm.registers[8]}, SP(R29): {vm.registers[29]}')

    print(f'\nCall trace ({len(call_log)} entries):')
    for i, entry in enumerate(call_log):
        if entry[0] == 'CALL':
            print(f'  [{i:4d}] -> PC={entry[1]:5d} target={entry[2]:5d} R0={entry[3]}')
        else:
            print(f'  [{i:4d}] <- PC={entry[1]:5d} R0={entry[2]} R10={entry[3]}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
