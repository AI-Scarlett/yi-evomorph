#!/usr/bin/env python3
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.virtual_machine import VMState
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

vm = ExtendedIChingVM2()

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
vm.program = program
vm.pc = 0
vm.state = 1  # RUNNING
vm.registers[29] = vm.STACK_SIZE

# Step through
for i in range(20):
    if vm.state != VMState.RUNNING:
        break
    old_pc = vm.pc
    vm.step()
    print(f"Step {i}: PC={old_pc}->{vm.pc} R0={vm.registers[0]} zero={vm.flag_zero} neg={vm.flag_negative} state={vm.state}")

print(f"\nFinal: R0={vm.registers[0]} (expected 42)")
