#!/usr/bin/env python3
"""Verify opcode table and lookup_opcode behavior"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState
from build_assembler import build_opcode_table, OPCODE_TABLE, INPUT_BUF, LABEL_TABLE
import struct

base_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    assembler_evob = f.read()

# Build and dump opcode table
vm = ExtendedIChingVM2()
opcode_table = build_opcode_table()
for i, byte_val in enumerate(opcode_table):
    vm.heap[OPCODE_TABLE + i] = byte_val

print(f"Opcode table size: {len(opcode_table)} bytes ({len(opcode_table)//14} entries)")
print(f"First few bytes at 0x16000: {bytes(vm.heap[OPCODE_TABLE:OPCODE_TABLE+20]).hex()}")
print()

# Show each entry
for idx in range(64):
    addr = OPCODE_TABLE + idx * 14
    name_bytes = bytes(vm.heap[addr:addr+12])
    opcode = vm.heap[addr+12]
    name = name_bytes.rstrip(b'\x00').decode('ascii', errors='replace')
    print(f"  Entry {idx:2d} @ {addr:#x}: name='{name}' opcode={opcode}")

# Also verify what's at 0x18100 after parsing "CREA"
print("\n=== Simulate parsing ===")
source = "  CREA.1 R0, R0, #42\n"
source_bytes = source.encode('ascii') + b'\x00'
for i, byte_val in enumerate(source_bytes):
    vm.heap[INPUT_BUF + i] = byte_val

# Look at input buffer
print(f"Input buffer at 0x1000: {bytes(vm.heap[INPUT_BUF:INPUT_BUF+len(source_bytes)]).hex()}")
print(f"Input buffer as str: {bytes(vm.heap[INPUT_BUF:INPUT_BUF+len(source_bytes)]).decode('ascii', errors='replace')!r}")

# Let's check what the mnemonic copy loop would produce
# p2_parse_mnem copies from R4 (line start) to LINE_BUF until space/tab/./\0/\n
LINE_BUF = 0x18100
r4 = INPUT_BUF + 2  # after "  " → points to 'C'
r1 = LINE_BUF
print(f"\nCopying from {r4:#x}:")
while True:
    c = vm.heap[r4]
    if c in (0, 10, 32, 9, 46):  # \0, \n, space, tab, '.'
        break
    vm.heap[r1] = c
    print(f"  [{r4:#x}] '{chr(c)}' → [{r1:#x}]")
    r4 += 1
    r1 += 1
vm.heap[r1] = 0  # null-terminate
r1 += 1
print(f"  null-terminate at [{r1-1:#x}]")

mnemonic = bytes(vm.heap[LINE_BUF:r1]).rstrip(b'\x00').decode('ascii')
print(f"\nCopied mnemonic: '{mnemonic}' at 0x18100")
print(f"Hex: {bytes(vm.heap[LINE_BUF:LINE_BUF+10]).hex()}")

# Now look up the opcode manually
print("\n=== Manual lookup ===")
mnem_ptr = LINE_BUF
for idx in range(64):
    entry_addr = OPCODE_TABLE + idx * 14
    # Check if entry is empty (first byte 0)
    first_byte = vm.heap[entry_addr]
    if first_byte == 0:
        print(f"  Entry {idx}: empty (first_byte=0) → NOT FOUND")
        break
    
    # Compare mnemonic with table entry
    match = True
    for j in range(12):
        mc = vm.heap[mnem_ptr + j]
        ec = vm.heap[entry_addr + j]
        if mc == 0 and ec == 0:
            break  # both null-terminated
        if mc != ec:
            match = False
            break
    
    if match:
        opcode = vm.heap[entry_addr + 12]
        print(f"  Entry {idx}: MATCH! opcode={opcode}")
        break
else:
    print("  NOT FOUND in table")
