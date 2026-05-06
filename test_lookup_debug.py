#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LOOKUP_ASM,
    NATIVE_TABLE, NATIVE_STRINGS, NATIVE_MNEMONICS
)
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

compiler = BootstrapCompiler()
vm = compiler.vm
compiler._load_mnemonic_table()
compiler._load_native_table()

# Check the native table entries
print("=== Native table entries (first 10) ===")
for i in range(min(10, len(NATIVE_MNEMONICS))):
    entry_addr = NATIVE_TABLE + i * 8
    str_addr = vm._load_word_heap(entry_addr)
    opcode = vm._load_word_heap(entry_addr + 4)
    name = vm.read_string(str_addr) if str_addr > 0 else "?"
    print(f"  [{i}] str_addr={str_addr:#x} opcode={opcode:#x} name='{name}'")

# Find JMP entry
for i, (mnem, opc) in enumerate(NATIVE_MNEMONICS):
    if mnem == "JMP":
        entry_addr = NATIVE_TABLE + i * 8
        str_addr = vm._load_word_heap(entry_addr)
        stored_opc = vm._load_word_heap(entry_addr + 4)
        name = vm.read_string(str_addr)
        print(f"\nJMP entry: index={i}, str_addr={str_addr:#x}, stored_opcode={stored_opc:#x}, name='{name}'")
        
        # Now test strcmp with the JMP string
        # Load a test string at a known address
        test_addr = 0x9000
        vm.load_string(test_addr, "JMP")
        test_name = vm.read_string(test_addr)
        print(f"Test string at {test_addr:#x}: '{test_name}'")
        
        # Run strcmp in the VM
        test_asm = """
JMP test_start

""" + STDLIB_ASM + """

test_start:
    MOVI R0, #0x9000
    MOVI R1, #""" + hex(str_addr) + """
    CALL strcmp
    HLT
"""
        vm2 = ExtendedIChingVM2()
        compiler2 = BootstrapCompiler()
        compiler2.vm = vm2
        compiler2._load_mnemonic_table()
        compiler2._load_native_table()
        vm2.load_string(0x9000, "JMP")
        vm2.load_assembled(test_asm)
        vm2.registers[29] = vm2.STACK_SIZE
        vm2.run(max_cycles=10000)
        print(f"strcmp('JMP', table_JMP): R0={vm2.registers[0]} (0=match)")
        break

# Test lookup_native with a string loaded at a known address
print("\n=== lookup_native test with proper string ===")
vm3 = ExtendedIChingVM2()
compiler3 = BootstrapCompiler()
compiler3.vm = vm3
compiler3._load_mnemonic_table()
compiler3._load_native_table()

# Load "JMP" at 0x9000
vm3.load_string(0x9000, "JMP")

test_asm3 = """
JMP test_start3

""" + STDLIB_ASM + LOOKUP_ASM + """

test_start3:
    MOVI R0, #0x9000
    CALL lookup_native
    HLT
"""
vm3.load_assembled(test_asm3)
vm3.registers[29] = vm3.STACK_SIZE
vm3.run(max_cycles=100000)
print(f"lookup_native('JMP'): R0={vm3.registers[0]:#x} (expected 0x20)")

# Also test with "MOVI"
vm4 = ExtendedIChingVM2()
compiler4 = BootstrapCompiler()
compiler4.vm = vm4
compiler4._load_mnemonic_table()
compiler4._load_native_table()
vm4.load_string(0x9000, "MOVI")
test_asm4 = """
JMP test_start4

""" + STDLIB_ASM + LOOKUP_ASM + """

test_start4:
    MOVI R0, #0x9000
    CALL lookup_native
    HLT
"""
vm4.load_assembled(test_asm4)
vm4.registers[29] = vm4.STACK_SIZE
vm4.run(max_cycles=100000)
print(f"lookup_native('MOVI'): R0={vm4.registers[0]:#x} (expected 0x33)")
