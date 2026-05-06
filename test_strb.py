#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

vm = ExtendedIChingVM2()

# Simple test: MOVI R5, #0x33 then STRB R12, R5
test_asm = """
MOVI R5, #0x33
MOVI R12, #0xB040
STRB R12, R5
HLT
"""
vm.load_assembled(test_asm)
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=100)

print(f"R5 = {vm.registers[5]:#x}")
print(f"R12 = {vm.registers[12]:#x}")
print(f"heap[0xB040] = {vm.heap[0xB040]:#x}")
print(f"Expected: 0x33")
