#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler

compiler = BootstrapCompiler()

source1 = '@evolang "3.0"\n\n@locus test {\n    GUAXU: {\n        SYNC\n        CREA R0, R1\n        BARRIER\n        FELLOWSHIP R0, R1\n        SYNC .ASYNC\n    }\n}\n'
result = compiler.compile_source(source1)
print('=== Test 1: No-operand instructions ===')
print(f'Success: {result["success"]}')
print(f'Locus count: {result.get("evob_locus_count", "N/A")}')
if 'instructions' in result:
    print(f'Instruction count: {result["instruction_count"]}')
    for instr in result['instructions']:
        mod_str = f' mod=0x{instr["modifier"]:02x}' if instr['modifier'] else ''
        print(f'  {instr["mnemonic"]} R{instr["op1"]}, R{instr["op2"]}{mod_str}')

source2 = '@evolang "3.0"\n\n@locus first {\n    GUAXU: {\n        CREA R0, R1\n    }\n}\n\n@locus second {\n    GUAXU: {\n        SYNC\n        FELLOWSHIP R2, R3\n    }\n}\n'
result2 = compiler.compile_source(source2)
print('\n=== Test 2: Multiple loci ===')
print(f'Success: {result2["success"]}')
print(f'Locus count: {result2.get("evob_locus_count", "N/A")}')
if 'evob_locus_offsets' in result2:
    print(f'Offsets: {result2["evob_locus_offsets"]}')

source3 = '@evolang "3.0"\n\n@locus mod_test {\n    GUAXU: {\n        CREA.ASYNC R0, R1\n        LOCK.ATOMIC R2, R3\n        SYNC\n    }\n}\n'
result3 = compiler.compile_source(source3)
print('\n=== Test 3: Modifiers ===')
print(f'Success: {result3["success"]}')
if 'instructions' in result3:
    for instr in result3['instructions']:
        mod_str = f' mod=0x{instr["modifier"]:02x}' if instr['modifier'] else ''
        print(f'  {instr["mnemonic"]} R{instr["op1"]}, R{instr["op2"]}{mod_str}')

source4 = '@evolang "3.0"\n\n@xiangci {\n    "test program"\n}\n\n@locus main {\n    GUAXU: {\n        CREA R0, R1\n        SYNC\n    }\n}\n'
result4 = compiler.compile_source(source4)
print('\n=== Test 4: With xiangci ===')
print(f'Success: {result4["success"]}')
print(f'Locus count: {result4.get("evob_locus_count", "N/A")}')

source5 = '@evolang "3.0"\n\n@locus full_test {\n    mut_rate = 0.02\n    fitness = min_latency\n    env_target = ["linux-6.x"]\n    GUAXU: {\n        CREA R0, R1\n        ALLOC R2, R3\n        SYNC\n        FELLOWSHIP R0, R1\n        BARRIER\n        LOCK R4, R5\n        YIELD\n        RETURN\n    }\n}\n'
result5 = compiler.compile_source(source5)
print('\n=== Test 5: Full program with metadata ===')
print(f'Success: {result5["success"]}')
print(f'Locus count: {result5.get("evob_locus_count", "N/A")}')
if 'instructions' in result5:
    print(f'Instruction count: {result5["instruction_count"]}')
    for instr in result5['instructions']:
        mod_str = f' mod=0x{instr["modifier"]:02x}' if instr['modifier'] else ''
        print(f'  {instr["mnemonic"]} R{instr["op1"]}, R{instr["op2"]}{mod_str}')

print('\n=== All tests completed ===')
