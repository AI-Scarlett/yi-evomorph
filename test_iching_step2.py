#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState

vm = ExtendedIChingVM2()
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

for i in range(20):
    if vm.state != VMState.RUNNING:
        break
    old_pc = vm.pc
    vm.step()
    print(f"Step {i}: PC={old_pc}->{vm.pc} R0={vm.registers[0]} R1={vm.registers[1]} zero={vm.flag_zero} neg={vm.flag_negative} state={vm.state}")
