#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

vm = ExtendedIChingVM2()

test_asm = """
    BRANCH.1 @main
strlen:
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
    FELLOWSHIP.0 R4, R0
    CREA.1 R5, R5, #0
strlen_loop:
    RECV.2 R0, R4
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @strlen_done
    MICRO.1 R4, R4
    MICRO.1 R5, R5
    BRANCH.1 @strlen_loop
strlen_done:
    FELLOWSHIP.0 R0, R5
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0
main:
    CREA.1 R0, R0, #0x1000
    ABUNDANCE.1 R0, R0, @strlen
    RETURN.1 R0, R0
"""

prog = vm.assemble(test_asm)
print(f"Assembled: {len(prog)} bytes")
print(f"Hex: {prog.hex()}")

vm.program = prog
vm.pc = 0
vm.state = 0  # INIT
vm.load_string(0x1000, "hello")
vm.registers[29] = vm.STACK_SIZE

print(f"Before run: state={vm.state}, pc={vm.pc}, cycle_count={vm.cycle_count}")
print(f"Program length: {len(vm.program)}")

# Manual stepping
from evomorph.vm.virtual_machine import VMState
vm.state = VMState.RUNNING
for i in range(50):
    if vm.state != VMState.RUNNING:
        print(f"Step {i}: state changed to {vm.state}")
        break
    old_pc = vm.pc
    vm._step()
    vm.cycle_count += 1
    print(f"Step {i}: PC={old_pc}->{vm.pc} R0={vm.registers[0]} state={vm.state}")

print(f"\nFinal: R0={vm.registers[0]} (expected 5)")
