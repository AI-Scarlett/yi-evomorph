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

vm.load_assembled(test_asm)
vm.load_string(0x1000, "hello")
vm.registers[29] = vm.STACK_SIZE

print(f"Before run: state={vm.state} ({type(vm.state)}), pc={vm.pc}, cycle_count={vm.cycle_count}")
print(f"Program length: {len(vm.program)}")

vm.run(max_cycles=1000)
print(f"After run: R0={vm.registers[0]} (expected 5), state={vm.state}, cycles={vm.cycle_count}")
