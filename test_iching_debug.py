#!/usr/bin/env python3
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

vm = ExtendedIChingVM2()

# Simple test: CREA.1 R0, #10 then FELLOWSHIP.1 R0, #10 then BRANCH.2 ok
test_asm = """
    CREA.1 R0, R0, #10
    FELLOWSHIP.1 R0, R0, #10
    BRANCH.2 ok
    CREA.1 R0, R0, #0
    RETURN.1 R0, R0
ok:
    CREA.1 R0, R0, #42
    RETURN.1 R0, R0
"""

program = vm.assemble(test_asm)
print(f"Program: {len(program)} bytes")
print(f"Hex: {program.hex()}")

# Decode
pos = 0
while pos < len(program):
    b1 = program[pos]
    itype = (b1 >> 6) & 3
    if itype == 2:  # IChing
        opc = b1 & 0x3F
        mod = program[pos+1]
        op1 = program[pos+2]
        op2 = program[pos+3]
        sub_op = mod & 0x3F
        ext_mode = (mod >> 6) & 3
        pos += 4
        imm = None
        if ext_mode == 2:
            imm = struct.unpack('<I', bytes(program[pos:pos+4]))[0]
            pos += 4
        ICHING_NAMES = {63:'CREA', 0:'RECV', 61:'FELLOWSHIP', 2:'BRANCH', 1:'RETURN'}
        name = ICHING_NAMES.get(opc, f'?{opc}')
        sub_names = {
            (63,1):'MOVI', (0,1):'LDR', (0,2):'LDRB',
            (61,1):'CMP', (61,2):'CMPI',
            (2,1):'JMP', (2,2):'JE', (2,3):'JNE',
            (1,1):'HLT',
        }
        sub_name = sub_names.get((opc, sub_op), name)
        imm_str = f', #{imm}' if imm is not None else ''
        print(f'  {sub_name} R{op1&0x1F}, R{op2&0x1F}{imm_str} (opc={opc} sub={sub_op} ext={ext_mode})')
    elif itype == 1:  # Native
        opc = b1 & 0x3F
        b2 = program[pos+1]
        b3 = program[pos+2]
        pos += 3
        has_imm = bool(b2 & 0x20)
        if has_imm and pos + 3 < len(program):
            imm = struct.unpack('<I', bytes(program[pos:pos+4]))[0]
            pos += 4
        else:
            imm = None
        NATIVE_NAMES = {0x01:'HLT',0x1C:'MOVI',0x20:'JMP'}
        name = NATIVE_NAMES.get(opc, f'?{opc:#x}')
        imm_str = f', #{imm}' if imm is not None else ''
        print(f'  {name} R{b2&0x1F}, R{b3&0x1F}{imm_str}')
    else:
        print(f'  ? byte={b1:#x}')
        break

# Run
vm.load_assembled(test_asm)
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=1000)
print(f"\nR0 = {vm.registers[0]} (expected 42)")
print(f"flag_zero = {vm.flag_zero}")
print(f"flag_negative = {vm.flag_negative}")
