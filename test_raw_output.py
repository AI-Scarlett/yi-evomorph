#!/usr/bin/env python3
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler, OUTPUT_BUF, HEADER_RESERVE

c = BootstrapCompiler()
r = c.compile_source('@evolang "3.0"\n\n@locus test {\n    GUAXU: {\n        MOVI R0, #42\n        HLT\n    }\n}\n')

vm = c.vm
output_size = vm.registers[0]
print(f"output_size (R0): {output_size}")
print(f"OUTPUT_BUF: {OUTPUT_BUF:#x}")

# Read raw output from VM heap
raw = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF + 100])
print(f"Raw first 80 bytes: {raw[:80].hex()}")

# Check EVOB header
if raw[:4] == b'EVOB':
    header_size = struct.unpack(">H", raw[6:8])[0]
    locus_count = struct.unpack(">H", raw[8:10])[0]
    print(f"EVOB header_size: {header_size}")
    print(f"EVOB locus_count: {locus_count}")
    
    # Show where bytecode starts
    print(f"HEADER_RESERVE: {HEADER_RESERVE}")
    print(f"Bytecode at offset {HEADER_RESERVE}: {raw[HEADER_RESERVE:HEADER_RESERVE+20].hex()}")
    
    # The compacted output
    bytecode_data = raw[HEADER_RESERVE:]
    compacted = raw[:header_size] + bytecode_data
    print(f"Compacted: {compacted.hex()}")
    print(f"Compacted size: {len(compacted)}")
