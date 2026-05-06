#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LOOKUP_ASM, NATIVE_TABLE, NATIVE_STRINGS
)
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

vm = ExtendedIChingVM2()
c = BootstrapCompiler()
c.vm = vm
c._load_mnemonic_table()
c._load_native_table()

# Test strcmp with different strings
vm.load_string(0x9000, "MOVI")
vm.load_string(0x9010, "NOP")

test_asm = """
JMP test_start

""" + STDLIB_ASM + """

test_start:
    ; Test 1: strcmp("MOVI", "NOP") should NOT be 0
    MOVI R0, #0x9000
    MOVI R1, #0x9010
    CALL strcmp
    ; R0 should be non-zero
    MOVI R5, #0xFF00
    STRB R5, R0
    
    ; Test 2: strcmp("MOVI", "MOVI") should be 0
    MOVI R0, #0x9000
    MOVI R1, #0x9000
    CALL strcmp
    MOVI R5, #0xFF01
    STRB R5, R0
    
    HLT
"""
vm.load_assembled(test_asm)
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=10000)

print(f"strcmp('MOVI', 'NOP'): {vm.heap[0xFF00]} (should be non-zero)")
print(f"strcmp('MOVI', 'MOVI'): {vm.heap[0xFF01]} (should be 0)")

# Also test lookup_native
vm2 = ExtendedIChingVM2()
c2 = BootstrapCompiler()
c2.vm = vm2
c2._load_mnemonic_table()
c2._load_native_table()

vm2.load_string(0x9000, "MOVI")
test_asm2 = """
JMP test_start2

""" + STDLIB_ASM + LOOKUP_ASM + """

test_start2:
    MOVI R0, #0x9000
    CALL lookup_native
    HLT
"""
vm2.load_assembled(test_asm2)
vm2.registers[29] = vm2.STACK_SIZE
vm2.run(max_cycles=100000)
print(f"lookup_native('MOVI'): {vm2.registers[0]:#x} (should be 0x33)")

# Check the native table first entry
entry0_str_addr = vm2._load_word_heap(NATIVE_TABLE)
entry0_opcode = vm2._load_word_heap(NATIVE_TABLE + 4)
name0 = vm2.read_string(entry0_str_addr)
print(f"Native table[0]: name='{name0}' opcode={entry0_opcode:#x}")
