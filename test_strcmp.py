#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, KEYWORD_STRINGS
)
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

vm = ExtendedIChingVM2()
c = BootstrapCompiler()
c.vm = vm
c._load_mnemonic_table()

# Load "GUAXU" at two different addresses
vm.load_string(0x11017, "GUAXU")  # lexer string pool address
# The keyword string is at 0x12621 (loaded by _load_mnemonic_table)
s1 = vm.read_string(0x11017)
s2 = vm.read_string(0x12621)
print(f"String at 0x11017: '{s1}'")
print(f"String at 0x12621: '{s2}'")

# Test strcmp
test_asm = """
JMP test_start

""" + STDLIB_ASM + """

test_start:
    MOVI R0, #0x11017
    MOVI R1, #0x12621
    CALL strcmp
    HLT
"""
vm.load_assembled(test_asm)
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=10000)

print(f"strcmp result: R0={vm.registers[0]} (0=match)")
