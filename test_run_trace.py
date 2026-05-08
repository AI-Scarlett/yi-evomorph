#!/usr/bin/env python3
"""Correct test: use vm.run() with max_cycles for HALT.0"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

base_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    assembler_evob = f.read()

from build_assembler import build_opcode_table, OPCODE_TABLE, INPUT_BUF, OUTPUT_BUF, LABEL_TABLE

# Test 1: HALT.0
print("=== Test 1: HALT.0 ===")
source = "HALT.0\n"
source_bytes = source.encode('ascii') + b'\x00'

vm = ExtendedIChingVM2()
vm.state = vm.state.__class__.RUNNING  # Force RUNNING

opcode_table = build_opcode_table()
for i, byte_val in enumerate(opcode_table):
    vm.heap[OPCODE_TABLE + i] = byte_val

for i, byte_val in enumerate(source_bytes):
    vm.heap[INPUT_BUF + i] = byte_val

for i in range(LABEL_TABLE, LABEL_TABLE + 0x4000):
    vm.heap[i] = 0

vm.program = bytearray(assembler_evob)
vm.pc = 0
vm.registers[0] = INPUT_BUF
vm.registers[29] = vm.STACK_SIZE

# Use run with small cycle limit
result = vm.run(max_cycles=10000)
print(f"  cycles={vm.cycle_count} state={vm.state}")
print(f"  R0 (output size) = {vm.registers[0]}")
output_size = vm.registers[0]
if 0 < output_size < 200:
    print(f"  Output: {bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF+output_size]).hex()}")
else:
    print(f"  Output invalid or too large")

# Test 2: Simple branch
print("\n=== Test 2: Simple branch with label ===")
source = """  CREA.1 R0, R0, #1
skip:
  CREA.1 R1, R1, #2
"""

vm = ExtendedIChingVM2()
vm.state = vm.state.__class__.RUNNING

for i, byte_val in enumerate(opcode_table):
    vm.heap[OPCODE_TABLE + i] = byte_val

source_bytes = source.encode('ascii') + b'\x00'
for i, byte_val in enumerate(source_bytes):
    vm.heap[INPUT_BUF + i] = byte_val

for i in range(LABEL_TABLE, LABEL_TABLE + 0x4000):
    vm.heap[i] = 0

vm.program = bytearray(assembler_evob)
vm.pc = 0
vm.registers[0] = INPUT_BUF
vm.registers[29] = vm.STACK_SIZE

result = vm.run(max_cycles=10000)
print(f"  cycles={vm.cycle_count} state={vm.state}")
print(f"  R0 (output size) = {vm.registers[0]}")
output_size = vm.registers[0]
if 0 < output_size < 200:
    print(f"  Output: {bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF+output_size]).hex()}")
else:
    print(f"  Output invalid")

# Test 3: Python assembler reference
print("\n=== Test 3: Python reference ===")
from evomorph.vm.extended_vm2 import ExtendedIChingVM2 as VM2
vm_py = VM2()
for s in ["HALT.0\n", source]:
    py_out = vm_py.assemble(s)
    print(f"  Python ({s[:20].strip()}...): {len(py_out)} bytes = {py_out.hex()}")
