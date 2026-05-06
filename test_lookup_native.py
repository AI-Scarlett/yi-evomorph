#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM,
    INPUT_BUF, TOKEN_BUF, OUTPUT_BUF, MNEMONIC_STRINGS, MNEMONIC_TABLE,
    NATIVE_TABLE, NATIVE_STRINGS, HEADER_RESERVE
)
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

compiler = BootstrapCompiler()
vm = compiler.vm

# Load tables
compiler._load_mnemonic_table()
compiler._load_native_table()

# Check if "JMP" is in the native table
# NATIVE_STRINGS = 0x7A00
# Let's read the first few entries
print("=== Native mnemonic table ===")
for i in range(5):
    entry_addr = NATIVE_TABLE + i * 8
    str_addr = vm._load_word_heap(entry_addr)
    opcode = vm._load_word_heap(entry_addr + 4)
    name = vm.read_string(str_addr) if str_addr > 0 else "?"
    print(f"  Entry[{i}]: str_addr={str_addr:#x}, opcode={opcode:#x}, name='{name}'")

# Check if "JMP" string exists in the heap
print("\n=== Searching for 'JMP' in heap ===")
for offset in range(NATIVE_STRINGS, NATIVE_STRINGS + 500):
    s = vm.read_string(offset)
    if s == "JMP":
        print(f"  Found 'JMP' at {offset:#x}")
        break
    if len(s) > 0 and offset == NATIVE_STRINGS:
        print(f"  First string at {offset:#x}: '{s}'")

# Now test the lookup_native function directly
test_asm = """
JMP test_start

""" + STDLIB_ASM + LOOKUP_ASM + """

test_start:
    ; Load address of "JMP" string
    MOVI R0, #0x7A00
    ; Look up in native table
    CALL lookup_native
    ; R0 should be the opcode for JMP
    HLT
"""
vm.load_assembled(test_asm)
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=10000)

print(f"\n=== lookup_native test ===")
print(f"VM state: {vm.state}")
print(f"R0 (result): {vm.registers[0]} (expected: 0x12 = 18 for JMP)")

# Also test with "MOVI"
vm2 = ExtendedIChingVM2()
compiler2 = BootstrapCompiler()
compiler2.vm = vm2
compiler2._load_mnemonic_table()
compiler2._load_native_table()

# Find MOVI string address
movi_addr = None
for offset in range(NATIVE_STRINGS, NATIVE_STRINGS + 500):
    s = vm2.read_string(offset)
    if s == "MOVI":
        movi_addr = offset
        print(f"Found 'MOVI' at {offset:#x}")
        break
    if s and offset == NATIVE_STRINGS:
        print(f"First string at {offset:#x}: '{s}'")

if movi_addr:
    test_asm2 = """
JMP test_start2

""" + STDLIB_ASM + LOOKUP_ASM + f"""

test_start2:
    MOVI R0, #{movi_addr}
    CALL lookup_native
    HLT
"""
    vm2.load_assembled(test_asm2)
    vm2.registers[29] = vm2.STACK_SIZE
    vm2.run(max_cycles=10000)
    print(f"lookup_native('MOVI'): R0={vm2.registers[0]:#x} (expected: 0x1C = 28)")
