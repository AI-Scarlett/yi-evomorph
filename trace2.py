#!/usr/bin/env python3
"""Trace EVB assembler comparing HALT-only vs CREA+HALT to find divergence"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from build_assembler import build_opcode_table, OPCODE_TABLE, INPUT_BUF, OUTPUT_BUF, LABEL_TABLE

base_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    assembler_evob = f.read()

def run_asm(source, max_cycles=50000):
    vm = ExtendedIChingVM2()
    opcode_table = build_opcode_table()
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
    vm.run(max_cycles=max_cycles)
    return vm

# Test 1: HALT only
print("=== Test 1: HALT.0 only ===")
vm1 = run_asm("  HALT.0\n")
print(f"R10 (bytecount): {vm1.registers[10]}, cycles: {vm1.cycle_count}")
if vm1.registers[10] > 0:
    out = bytes(vm1.heap[OUTPUT_BUF:OUTPUT_BUF+vm1.registers[10]])
    print(f"Output ({len(out)} bytes): {out.hex()}")
else:
    print("No output")

# Test 2: CREA.1 R0, R0, #42 only
print("\n=== Test 2: CREA.1 R0, R0, #42 only ===")
vm2 = run_asm("  CREA.1 R0, R0, #42\n", max_cycles=50000)
print(f"R10 (bytecount): {vm2.registers[10]}, cycles: {vm2.cycle_count}, PC: {vm2.pc}")
print(f"R0: {vm2.registers[0]}, R6: {vm2.registers[6]}, R9: {vm2.registers[9]:#x}")
if vm2.registers[10] > 0:
    out = bytes(vm2.heap[OUTPUT_BUF:OUTPUT_BUF+min(vm2.registers[10], 32)])
    print(f"Output: {out.hex()}")
else:
    print("No output")

# Test 3: CREA+HALT with more cycle limit
print("\n=== Test 3: CREA + HALT ===")
vm3 = run_asm("  CREA.1 R0, R0, #42\n  HALT.0\n", max_cycles=10000)
print(f"R10: {vm3.registers[10]}, cycles: {vm3.cycle_count}, PC: {vm3.pc}, state: {vm3.state}")
print(f"R8 (cursor): {vm3.registers[8]:#x}")
print(f"R9 (out ptr): {vm3.registers[9]:#x}")

# Check if it halted or hit max
if vm3.state.value == 1:  # HALTED
    print("VM halted normally")
    if vm3.registers[10] > 0:
        out = bytes(vm3.heap[OUTPUT_BUF:OUTPUT_BUF+min(vm3.registers[10], 32)])
        print(f"Output: {out.hex()}")
elif vm3.state.value == 2:  # RUNNING
    print(f"VM still running after {vm3.cycle_count} cycles (stuck in loop)")
