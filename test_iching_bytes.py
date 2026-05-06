#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.iching.iching_compiler import IChingBootstrapCompiler, FULL_COMPILER_ASM, INPUT_BUF
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

# Print raw bytes at specific locations
for pc in [2132, 2140]:
    if pc + 7 < len(vm.program):
        b = vm.program[pc:pc+8]
        print(f"PC={pc}: {' '.join(f'0x{x:02X}' for x in b)}")
        opcode = b[0] & 0x3F
        modifier = b[1]
        sub_op = modifier & 0x3F
        ext_mode = (modifier >> 6) & 0x03
        op1 = b[2]
        op2 = b[3]
        if ext_mode == 2:
            imm = struct.unpack('<I', bytes(b[4:8]))[0]
            print(f"  opcode={opcode} sub_op={sub_op} ext_mode={ext_mode} op1={op1} op2={op2} imm={imm}")
        else:
            print(f"  opcode={opcode} sub_op={sub_op} ext_mode={ext_mode} op1={op1} op2={op2}")

# Also check what the assembler produces for a simple test
print("\nSimple assembly test:")
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
vm2 = ExtendedIChingVM2()
test = """
    FELLOWSHIP.2 R0, R0, #64
    BRANCH.3 @done
done:
    RETURN.1 R0, R0
"""
prog = vm2.assemble(test)
print(f"Bytes: {prog.hex()}")
for i in range(0, len(prog), 4):
    chunk = prog[i:i+4]
    print(f"  [{i:3d}] {' '.join(f'0x{x:02X}' for x in chunk)}")
