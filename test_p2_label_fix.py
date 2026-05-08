#!/usr/bin/env python3
"""Diagnostic: Test p2_check_at label fix with simple programs"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from build_assembler import (
    build_opcode_table, OPCODE_TABLE, INPUT_BUF, OUTPUT_BUF, LABEL_TABLE
)

def run_evob_assembler(asm_source, max_cycles=500000):
    """Run EVB assembler on source, return output bytes"""
    vm = ExtendedIChingVM2()
    
    # Pre-fill opcode table
    opcode_table = build_opcode_table()
    for i, byte_val in enumerate(opcode_table):
        vm.heap[OPCODE_TABLE + i] = byte_val
    
    # Load source to heap
    source_bytes = asm_source.encode('ascii', errors='replace') + b'\x00'
    for i, byte_val in enumerate(source_bytes):
        vm.heap[INPUT_BUF + i] = byte_val
    
    # Clear label table
    for i in range(LABEL_TABLE, LABEL_TABLE + 0x4000):
        vm.heap[i] = 0
    
    # Load assembler evob
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assembler_path = os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob')
    with open(assembler_path, 'rb') as f:
        assembler_evob = f.read()
    
    vm.program = bytearray(assembler_evob)
    vm.pc = 0
    vm.registers[0] = INPUT_BUF
    vm.registers[29] = vm.STACK_SIZE
    vm.run(max_cycles=max_cycles)
    
    output_size = vm.registers[0]
    if output_size <= 0 or output_size > 100000:
        return None, f"Invalid output size: {output_size}, state={vm.state}, cycles={vm.cycle_count}"
    
    output = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF + output_size])
    return output, f"size={output_size} cycles={vm.cycle_count} state={vm.state}"

def run_python_assembler(asm_source):
    """Run Python assembler for reference"""
    vm = ExtendedIChingVM2()
    return bytes(vm.assemble(asm_source))

# Test cases
test_cases = {
    "simple_no_label": """
HALT.0
""",
    "simple_branch": """
    CREA.1 R0, R0, #1
    BRANCH.1 @skip
    CREA.1 R1, R1, #99
skip:
    HALT.0
""",
    "call_label": """
    ABUNDANCE.1 R0, R0, @my_func
    HALT.0
my_func:
    CREA.1 R0, R0, #42
    RETURN.0 R0, R0
""",
    "label_ref_only": """
    BRANCH.1 @target
    HALT.0
target:
    CREA.1 R0, R0, #1
    HALT.0
""",
}

print("=" * 60)
print("P2 Label Fix Diagnostic")
print("=" * 60)

all_pass = True
for name, source in test_cases.items():
    source = source.strip()
    print(f"\n--- Test: {name} ---")
    print(f"Source:\n{source}")
    
    py_output = run_python_assembler(source)
    print(f"Python: {len(py_output)} bytes")
    
    evb_output, evb_info = run_evob_assembler(source)
    if evb_output is None:
        print(f"EVB: FAIL - {evb_info}")
        all_pass = False
    else:
        print(f"EVB: {evb_info}")
        print(f"EVB output: {evb_output.hex()}")
        print(f"Python output: {py_output.hex()}")
        
        if evb_output == py_output:
            print("PASS: Byte-level match!")
        else:
            print(f"FAIL: {sum(1 for i in range(min(len(evb_output), len(py_output))) if evb_output[i] != py_output[i])} byte mismatches")
            all_pass = False

print("\n" + "=" * 60)
if all_pass:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
print("=" * 60)
