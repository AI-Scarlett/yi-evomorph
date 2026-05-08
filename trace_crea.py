#!/usr/bin/env python3
"""Trace EVB assembler execution for Simple CREA to find the bug"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from build_assembler import build_opcode_table, OPCODE_TABLE, INPUT_BUF, OUTPUT_BUF, LABEL_TABLE

base_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    assembler_evob = f.read()

source = "  CREA.1 R0, R0, #42\n  HALT.0\n"
source_bytes = source.encode('ascii') + b'\x00'

vm = ExtendedIChingVM2()
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

# Run for up to 5000 cycles and check state
vm.run(max_cycles=5000)

print(f"R0 (output_size): {vm.registers[0]}")
print(f"R8 (input cursor): {vm.registers[8]}")
print(f"R9 (output cursor - base): {vm.registers[9]}")
print(f"R10 (byte count): {vm.registers[10]}")
print(f"PC: {vm.pc}")
print(f"Cycles: {vm.cycle_count}")
print(f"State: {vm.state}")

# Check output buffer
output_size = vm.registers[10]  # R10 is the output byte count
if output_size > 0 and output_size < 200:
    out_bytes = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF + min(output_size, 64)])
    print(f"Output ({output_size} bytes): {out_bytes.hex()}")

# Check input buffer state
input_data = bytes(vm.heap[INPUT_BUF:INPUT_BUF + 60])
print(f"Input BUF: {input_data!r}")

# Check what's around R8 (input cursor)
r8_pos = vm.registers[8] - INPUT_BUF
print(f"R8 at offset {r8_pos} in input (char: {chr(vm.heap[vm.registers[8]]) if 0 < vm.heap[vm.registers[8]] < 128 else '?':>6})")
print(f"Chars around R8: {bytes(vm.heap[vm.registers[8]:vm.registers[8]+20])!r}")

# Show output buffer area
if output_size < 200 and output_size > 0:
    print(f"\nOutput buffer hex:")
    for i in range(0, output_size, 8):
        chunk = bytes(vm.heap[OUTPUT_BUF+i:OUTPUT_BUF+i+8])
        print(f"  +{i:4d}: {chunk.hex()}")
elif output_size > 200:
    print(f"\nOutput too large ({output_size}), showing first 64 bytes:")
    print(bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF+64]).hex())
else:
    print(f"\nOutput size is 0 or negative")
