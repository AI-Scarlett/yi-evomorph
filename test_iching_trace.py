#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.iching.iching_compiler import IChingBootstrapCompiler, FULL_COMPILER_ASM, INPUT_BUF
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState
import struct

compiler = IChingBootstrapCompiler()
vm = compiler.vm
vm.__init__()

compiler._load_mnemonic_table()
compiler._load_native_table()

source = '@evolang "3.0"\n'
processed = compiler._preprocess_source(source)
vm.load_string(INPUT_BUF, processed)
vm.load_assembled(FULL_COMPILER_ASM)

vm.registers[0] = INPUT_BUF
vm.registers[29] = vm.STACK_SIZE

# Disassemble around the is_whitespace area
print("Disassembly around is_whitespace (PC 192-272):")
pos = 192
while pos < 272 and pos < len(vm.program):
    b1 = vm.program[pos]
    itype = (b1 >> 6) & 0x03
    if itype == 0x02:
        opcode = b1 & 0x3F
        modifier = vm.program[pos+1]
        op1 = vm.program[pos+2]
        op2 = vm.program[pos+3]
        sub_op = modifier & 0x3F
        ext_mode = (modifier >> 6) & 0x03
        mnem = vm.ICHING_OPCODE_MAP.get(opcode, f"?{opcode}")
        extra = ""
        pos += 4
        if ext_mode == 2 and pos + 3 < len(vm.program):
            imm = struct.unpack('<I', bytes(vm.program[pos:pos+4]))[0]
            extra = f" imm={imm}"
            pos += 4
        print(f"  [{pos-8 if ext_mode==2 else pos-4:4d}] {mnem}.{sub_op} ext={ext_mode} op1={op1} op2={op2}{extra}")
    else:
        print(f"  [{pos:4d}] 0x{b1:02X}")
        pos += 1

# Now trace execution step by step
print("\nDetailed trace:")
vm.state = VMState.RUNNING
for i in range(100):
    if vm.state != VMState.RUNNING:
        print(f"Cycle {i}: VM stopped, state={vm.state}")
        break
    
    pc = vm.pc
    if pc >= len(vm.program):
        print(f"Cycle {i}: PC out of bounds")
        break
    
    b1 = vm.program[pc]
    itype = (b1 >> 6) & 0x03
    instr_desc = f"0x{b1:02X}"
    if itype == 0x02:
        opcode = b1 & 0x3F
        modifier = vm.program[pc+1] if pc+1 < len(vm.program) else 0
        sub_op = modifier & 0x3F
        mnem = vm.ICHING_OPCODE_MAP.get(opcode, f"?{opcode}")
        instr_desc = f"{mnem}.{sub_op}"
    
    old_pc = vm.pc
    old_r0 = vm.registers[0]
    vm._step()
    vm.cycle_count += 1
    
    r0_changed = " *" if vm.registers[0] != old_r0 else ""
    print(f"  C{i:3d}: PC={old_pc:4d}->{vm.pc:4d} R0={old_r0}->{vm.registers[0]}{r0_changed} [{instr_desc}] call_stack={len(vm.call_stack)}")
