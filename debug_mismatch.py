#!/usr/bin/env python3
"""Debug byte-level mismatches"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

base_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    assembler_evob = f.read()

from build_assembler import build_opcode_table, OPCODE_TABLE, INPUT_BUF, OUTPUT_BUF, LABEL_TABLE

def run_evb(source, max_cycles=100000):
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
    output_size = vm.registers[0]
    if output_size <= 0:
        return None
    return bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF + output_size])

def run_py(source):
    vm = ExtendedIChingVM2()
    return bytes(vm.assemble(source))

# Test 1: Simple CREA
source = "  CREA.1 R0, R0, #42\n  HALT.0\n"
evb = run_evb(source)
py_out = run_py(source)
print("=== Simple CREA ===")
print(f"Source: {source.strip()}")
print(f"EVB ({len(evb)} bytes): {evb.hex()}")
print(f"Python ({len(py_out)} bytes): {py_out.hex()}")
if evb != py_out:
    min_len = min(len(evb), len(py_out))
    for i in range(min_len):
        if evb[i] != py_out[i]:
            print(f"  Mismatch at byte {i}: EVB=0x{evb[i]:02x} vs Python=0x{py_out[i]:02x}")
    if len(evb) != len(py_out):
        print(f"  Extra EVB bytes: {evb[min_len:].hex()}")
        print(f"  Extra Python bytes: {py_out[min_len:].hex()}")

# Test 2: Label def only
source2 = "skip:\n  CREA.1 R0, R0, #1\n  HALT.0\n"
evb2 = run_evb(source2)
py_out2 = run_py(source2)
print("\n=== Label def only ===")
print(f"Source: {source2.strip()}")
print(f"EVB ({len(evb2)} bytes): {evb2.hex()}")
print(f"Python ({len(py_out2)} bytes): {py_out2.hex()}")
if evb2 != py_out2:
    for i in range(min(len(evb2), len(py_out2))):
        if evb2[i] != py_out2[i]:
            print(f"  Mismatch at byte {i}: EVB=0x{evb2[i]:02x} vs Python=0x{py_out2[i]:02x}")

# Test 3: Label ref
source3 = "  BRANCH.1 @target\n  CREA.1 R1, R1, #99\ntarget:\n  HALT.0\n"
evb3 = run_evb(source3)
py_out3 = run_py(source3)
print("\n=== Label ref (branch) ===")
print(f"Source: {source3.strip()}")
print(f"EVB ({len(evb3)} bytes): {evb3.hex()}")
print(f"Python ({len(py_out3)} bytes): {py_out3.hex()}")
if evb3 != py_out3:
    for i in range(min(len(evb3), len(py_out3))):
        if evb3[i] != py_out3[i]:
            print(f"  Mismatch at byte {i}: EVB=0x{evb3[i]:02x} vs Python=0x{py_out3[i]:02x}")
