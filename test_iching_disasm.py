#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.iching.iching_compiler import IChingBootstrapCompiler, FULL_COMPILER_ASM, INPUT_BUF
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
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

# Disassemble around the tokenize_check_at area (PC 2100-2250)
print("Disassembly around tokenize_check_at (PC 2100-2250):")
pos = 2100
while pos < 2250 and pos < len(vm.program):
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
