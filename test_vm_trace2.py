#!/usr/bin/env python3
"""Re-test: load assembler.evob and run HALT.0 with better diagnostics"""

import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

base_dir = os.path.dirname(os.path.abspath(__file__))

# Load assembler
with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    assembler_evob = f.read()

print(f"Assembler size: {len(assembler_evob)} bytes")
print(f"First 16 bytes: {assembler_evob[:16].hex()}")

# Verify first instruction decodes correctly
b0, b1, b2, b3 = assembler_evob[0:4]
instr_type = (b0 >> 6) & 0x03
opcode = b0 & 0x3F
sub_op = b1 & 0x3F
ext_mode = (b1 >> 6) & 0x03
if ext_mode == 2:
    imm = struct.unpack('<I', bytes(assembler_evob[4:8]))[0]
    print(f"First instruction: type={instr_type} opcode={opcode} sub_op={sub_op} ext_mode={ext_mode} imm={imm} (0x{imm:08x})")

# Setup VM for HALT.0 test
from build_assembler import build_opcode_table, OPCODE_TABLE, INPUT_BUF, OUTPUT_BUF, LABEL_TABLE

source = "HALT.0\n"
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

# Run for 50 steps with full state trace
print("\nTracing VM execution:")
for i in range(50):
    if vm.state.value != 0:
        print(f"  VM state changed: {vm.state}")
        break
    
    pc = vm.pc
    if pc >= len(vm.program):
        print(f"  PC out of range: {pc} >= {len(vm.program)}")
        break
    
    op_name = ExtendedIChingVM2.ICHING_OPCODE_MAP.get(assembler_evob[pc] & 0x3F, "???")
    sub = assembler_evob[pc+1] & 0x3F if pc+1 < len(assembler_evob) else 0
    print(f"  step={i:3d} pc=0x{pc:04x} [{op_name}.{sub}] R0=0x{vm.registers[0]:08x} R10={vm.registers[10]} R8=0x{vm.registers[8]:08x}")
    
    vm.step()

print(f"\nAfter {vm.cycle_count} cycles:")
print(f"  state={vm.state}, pc=0x{vm.pc:04x}")
print(f"  R0=0x{vm.registers[0]:08x} (output size)")
print(f"  Output buffer first 32 bytes: {bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF+32]).hex()}")
