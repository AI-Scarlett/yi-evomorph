#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState

vm = ExtendedIChingVM2()

# Monkey-patch _iching_extended to add debug output
orig_ext = vm._iching_extended
def debug_ext(self, opcode, sub_op, ext_mode, dst, src, imm):
    if opcode == 61:  # FELLOWSHIP
        a = self.registers[dst]
        b = self.registers[src] if imm is None else imm
        print(f"  CMP: R{dst}={a}, imm={imm}, b={b}, result={a-b}")
    orig_ext(opcode, sub_op, ext_mode, dst, src, imm)

import types
vm._iching_extended = types.MethodType(debug_ext, vm)

test1 = """
    CREA.1 R0, R0, #10
    CREA.1 R1, R1, #20
    GATHER.0 R0, R1
    FELLOWSHIP.1 R0, R0, #30
    BRANCH.2 correct
    CREA.1 R0, R0, #0
    RETURN.1 R0, R0
correct:
    CREA.1 R0, R0, #42
    RETURN.1 R0, R0
"""
program = vm.assemble(test1)
vm.program = program
vm.pc = 0
vm.state = VMState.RUNNING
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=1000)

print(f"\nR0={vm.registers[0]} (expected 42)")
