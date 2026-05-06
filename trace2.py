#!/usr/bin/env python3
"""简单追踪 - 看 EVB 汇编器对 compiler.evoasm 做了什么"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from build_assembler import (
    build_opcode_table, load_assembler_source,
    INPUT_BUF, OUTPUT_BUF, LABEL_TABLE, OPCODE_TABLE
)

# Load assembler
vm = ExtendedIChingVM2()
opcode_table = build_opcode_table()
for i, b in enumerate(opcode_table):
    vm.heap[OPCODE_TABLE + i] = b

asm_source = load_assembler_source()
evob = vm.assemble(asm_source)

# Ensure label addresses are preserved
label_addrs = dict(vm.labels)
print("Key function addresses:")
for name in ['asm_main', 'pass1', 'pass2', 'skip_line', 'lookup_opcode', 'lookup_label', 'add_label', 'emit_byte', 'p1_done']:
    if name in label_addrs:
        print(f"  {name}: {label_addrs[name]}")
print(f"  evob total: {len(evob)} bytes")

# Load test source
base_dir = os.path.dirname(os.path.abspath(__file__))
compiler_path = os.path.join(base_dir, 'evomorph', 'bootstrap', 'compiler.evoasm')
with open(compiler_path, 'r') as f:
    compiler_source = f.read()

vm2 = ExtendedIChingVM2()
for i, b in enumerate(opcode_table):
    vm2.heap[OPCODE_TABLE + i] = b

source_bytes = compiler_source.encode('ascii', errors='replace') + b'\x00'
for i, b in enumerate(source_bytes):
    vm2.heap[INPUT_BUF + i] = b
for i in range(LABEL_TABLE, LABEL_TABLE + 0x4000):
    vm2.heap[i] = 0

vm2.program = bytearray(evob)
vm2.pc = 0
vm2.registers[0] = INPUT_BUF
vm2.registers[29] = vm2.STACK_SIZE

# Track only CALLs and RETs
call_trace = []
orig_step = vm2._step

def track():
    pc = vm2.pc
    if pc < len(vm2.program):
        b1 = vm2.program[pc]
        if (b1 >> 6) == 2 and pc + 7 < len(vm2.program):
            op = b1 & 0x3F
            mod = vm2.program[pc + 1]
            sub = mod & 0x3F
            em = (mod >> 6) & 3
            if op == 47 and sub == 1 and em == 2:
                addr = struct.unpack('<I', bytes(vm2.program[pc+4:pc+8]))[0]
                # Find label name
                label = ''
                for n, a in label_addrs.items():
                    if a == addr:
                        label = n
                        break
                call_trace.append(f'CALL pc={pc:5d} → {addr:5d} ({label}) R0={vm2.registers[0]} R10={vm2.registers[10]} R8={vm2.registers[8]}')
            elif op == 1 and sub == 0:
                call_trace.append(f'RET  pc={pc:5d} R0={vm2.registers[0]} R10={vm2.registers[10]}')
    orig_step()

vm2._step = track

try:
    vm2.run(max_cycles=100000)
    print(f'\nState: {vm2.state}, Cycles: {vm2.cycle_count}')
    print(f'R0: {vm2.registers[0]}, R10: {vm2.registers[10]}')
    print(f'SP: {vm2.registers[29]}')
    
    print(f'\nCall trace:')
    for t in call_trace:
        print(f'  {t}')
    
    if vm2.registers[0] > 0 and vm2.registers[0] < 1000:
        ob = bytes(vm2.heap[OUTPUT_BUF:OUTPUT_BUF + vm2.registers[0]])
        print(f'\nOutput first {min(64, len(ob))} bytes: {ob[:64].hex()}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
