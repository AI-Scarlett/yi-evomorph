#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, NATIVE_TABLE, NATIVE_STRINGS, NATIVE_MNEMONICS
)
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

vm = ExtendedIChingVM2()
c = BootstrapCompiler()
c.vm = vm
c._load_mnemonic_table()
c._load_native_table()

# Check native table entries
print("=== Native table entries ===")
for i in range(5):
    entry_addr = NATIVE_TABLE + i * 8
    str_addr = vm._load_word_heap(entry_addr)
    opcode = vm._load_word_heap(entry_addr + 4)
    name = vm.read_string(str_addr) if str_addr > 0 else "?"
    print(f"  [{i}] at {entry_addr:#x}: str_addr={str_addr:#x} opcode={opcode:#x} name='{name}'")

# Now check what LDR would read
# LDR R5, R4 where R4 = NATIVE_TABLE
# LDR loads a 32-bit word from heap[R4]
val_at_table = vm._load_word_heap(NATIVE_TABLE)
print(f"\nValue at NATIVE_TABLE ({NATIVE_TABLE:#x}): {val_at_table:#x}")
print(f"Expected (NOP string addr): {vm._load_word_heap(NATIVE_TABLE):#x}")

# Check if the string at that address is correct
nop_str_addr = vm._load_word_heap(NATIVE_TABLE)
nop_name = vm.read_string(nop_str_addr)
print(f"String at {nop_str_addr:#x}: '{nop_name}'")

# The problem might be that LDR in the VM uses a different byte order
# Let's check the raw bytes at NATIVE_TABLE
raw_bytes = bytes(vm.heap[NATIVE_TABLE:NATIVE_TABLE+8])
print(f"\nRaw bytes at NATIVE_TABLE: {raw_bytes.hex()}")
print(f"Expected NOP string addr: {NATIVE_STRINGS:#x} = {NATIVE_STRINGS.to_bytes(4, 'little').hex()}")
