#!/usr/bin/env python3
"""Test modified strcmp (supports \n terminator)"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

base_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    assembler_evob = f.read()

from build_assembler import build_opcode_table, OPCODE_TABLE, INPUT_BUF, OUTPUT_BUF, LABEL_TABLE

def run_test(name, source):
    vm = ExtendedIChingVM2()
    
    opcode_table = build_opcode_table()
    for i, byte_val in enumerate(opcode_table):
        vm.heap[OPCODE_TABLE + i] = byte_val
    
    source_bytes = source.encode('ascii') + b'\x00'
    for i, byte_val in enumerate(source_bytes):
        vm.heap[INPUT_BUF + i] = byte_val
    
    for i in range(LABEL_TABLE, LABEL_TABLE + 0x4000):
        vm.heap[i] = 0
    
    vm.program = bytearray(assembler_evob)
    vm.pc = 0
    vm.registers[0] = INPUT_BUF
    vm.registers[29] = vm.STACK_SIZE
    
    result = vm.run(max_cycles=200000)
    
    output_size = vm.registers[0]
    if output_size <= 0:
        return f"FAIL: size={output_size}, cycles={vm.cycle_count}, state={vm.state}"
    
    output = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF + output_size])
    
    # Python reference
    vm_py = ExtendedIChingVM2()
    py_output = bytes(vm_py.assemble(source))
    
    match = "PASS" if output == py_output else f"FAIL: {sum(1 for i in range(min(len(output), len(py_output))) if output[i] != py_output[i])} byte mismatches"
    return f"{match}, size={output_size} vs {len(py_output)}, cycles={vm.cycle_count}"

# Test cases
tests = {
    "HALT only": "HALT.0\n",
    "Simple CREA": "  CREA.1 R0, R0, #42\n  HALT.0\n",
    "Label def only": "skip:\n  CREA.1 R0, R0, #1\n  HALT.0\n",
    "Branch no label ref": "  CREA.1 R0, R0, #0\n  HALT.0\n",
    "Label ref (branch)": "  BRANCH.1 @target\n  CREA.1 R1, R1, #99\ntarget:\n  HALT.0\n",
    "Label ref (call)": "  ABUNDANCE.1 R0, R0, @my_func\n  HALT.0\nmy_func:\n  CREA.1 R0, R0, #42\n  RETURN.0 R0, R0\n",
    "Multiple labels": """  CREA.1 R0, R0, #1
  BRANCH.1 @skip
  CREA.1 R1, R1, #99
skip:
  CREA.1 R2, R2, #1
  BRANCH.1 @end
  CREA.1 R3, R3, #99
end:
  HALT.0
""",
}

print("=" * 60)
print("P2 strcmp fix test (strcmp now supports \\n terminator)")
print("=" * 60)

all_pass = True
for name, source in tests.items():
    result = run_test(name, source)
    status = "✅" if result.startswith("PASS") else "❌"
    print(f"  {status} {name}: {result}")
    if not result.startswith("PASS"):
        all_pass = False

print(f"\n{'ALL PASSED' if all_pass else 'SOME FAILED'}")
