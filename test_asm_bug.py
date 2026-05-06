#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
import struct

vm = ExtendedIChingVM2()

# Test assembling just the tokenize_check_at section
test_asm = """
    BRANCH.1 @start
tokenize_check_at:
    FELLOWSHIP.2 R0, R0, #64
    BRANCH.3 @tokenize_check_quote
    CREA.1 R0, R0, #5
    CREA.1 R1, R1, #64
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    MICRO.1 R8, R8
    BRANCH.1 @start
tokenize_check_quote:
    FELLOWSHIP.2 R0, R0, #34
    BRANCH.3 @done
    RETURN.0 R0, R0
lexer_emit_token:
    PUSH_UP.1 R4, R4
    ALLOC.1 R9, R1
    CREA.1 R4, R4, #4
    GATHER.0 R9, R4
    ALLOC.1 R9, R0
    GATHER.0 R9, R4
    MICRO.1 R10, R10
    WELL.1 R4, R4
    RETURN.0 R0, R0
start:
    RETURN.1 R0, R0
done:
    RETURN.1 R0, R0
"""

prog = vm.assemble(test_asm)
print(f"Assembled: {len(prog)} bytes")

# Find the FELLOWSHIP.2 instruction
for i in range(0, len(prog) - 7, 1):
    b = prog[i]
    if b == 0xBD:  # FELLOWSHIP (0x80 | 61)
        modifier = prog[i+1]
        sub_op = modifier & 0x3F
        ext_mode = (modifier >> 6) & 0x03
        if sub_op == 2 and ext_mode == 2:
            imm = struct.unpack('<I', bytes(prog[i+4:i+8]))[0]
            print(f"  Found FELLOWSHIP.2 at PC={i}: imm={imm}")

# Also test with the FULL_COMPILER_ASM
from evomorph.bootstrap.iching.iching_compiler import FULL_COMPILER_ASM
vm2 = ExtendedIChingVM2()
prog2 = vm2.assemble(FULL_COMPILER_ASM)
print(f"\nFull compiler: {len(prog2)} bytes")

# Find all FELLOWSHIP.2 instructions with imm=128
for i in range(0, len(prog2) - 7, 1):
    b = prog2[i]
    if b == 0xBD:  # FELLOWSHIP
        modifier = prog2[i+1]
        sub_op = modifier & 0x3F
        ext_mode = (modifier >> 6) & 0x03
        if sub_op == 2 and ext_mode == 2:
            imm = struct.unpack('<I', bytes(prog2[i+4:i+8]))[0]
            if imm == 128:
                print(f"  Found FELLOWSHIP.2 with imm=128 at PC={i}")

# Find all BRANCH.5 instructions
for i in range(0, len(prog2) - 7, 1):
    b = prog2[i]
    if b == 0x82:  # BRANCH
        modifier = prog2[i+1]
        sub_op = modifier & 0x3F
        ext_mode = (modifier >> 6) & 0x03
        if sub_op == 5 and ext_mode == 2:
            imm = struct.unpack('<I', bytes(prog2[i+4:i+8]))[0]
            print(f"  Found BRANCH.5 at PC={i}: imm={imm}")
