#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler
from evomorph.vm.extended_vm2 import ExtendedIChingVM2, NativeOpcodes

compiler = BootstrapCompiler()

# Minimal test: single MOVI instruction
source = '@evolang "3.0"\n\n@locus test {\n    GUAXU: {\n        MOVI R0, #42\n    }\n}\n'
result = compiler.compile_source(source)
print(f'Compile success: {result["success"]}')
print(f'Token count: {result["token_count"]}')

# Check tokens
lexer_result = compiler.test_lexer('MOVI R0, #42')
print(f'\nLexer tokens for "MOVI R0, #42":')
for t in lexer_result['tokens']:
    print(f'  type={t["type"]} value={t["value"]}')

# Check bytecode
if result.get('output_bytes'):
    evob = result['output_bytes']
    header_size = result.get('evob_header_size', 14)
    bytecode = evob[header_size:]
    print(f'\nBytecode ({len(bytecode)} bytes): {bytecode.hex()}')
    print(f'Expected for MOVI R0, #42: 7 bytes')
    print(f'  byte1=0x73 (0x40|0x33), byte2=0x20 (R0|has_imm), byte3=0x00, imm=0x2A000000 (LE)')
    expected = bytes([0x73, 0x20, 0x00, 42, 0, 0, 0])
    print(f'Expected: {expected.hex()}')
    print(f'Match: {bytecode == expected}')

# Now let's trace the VM execution step by step
print('\n--- VM step-by-step trace ---')
vm = ExtendedIChingVM2()
compiler2 = BootstrapCompiler()
compiler2.vm = vm
compiler2._load_mnemonic_table()
compiler2._load_native_table()

processed = compiler2._preprocess_source(source)
vm.load_string(0x1000, processed)
vm.load_assembled(compiler2.FULL_COMPILER_ASM if hasattr(compiler2, 'FULL_COMPILER_ASM') else '')
vm.registers[0] = 0x1000
vm.registers[29] = vm.STACK_SIZE

# Run just a few steps and check
for i in range(200):
    if vm.state.value != 1:  # not RUNNING
        break
    vm.step()
    
print(f'VM state after 200 steps: {vm.state}')
print(f'R10 (token count): {vm.registers[10]}')
print(f'R12 (output pos): {vm.registers[12]:#x}')
print(f'R13 (token index): {vm.registers[13]}')
print(f'R15 (locus count): {vm.registers[15]}')
print(f'R17 (current opcode): {vm.registers[17]:#x}')
print(f'R22 (has_imm): {vm.registers[22]}')

# Check what's in the output buffer
output_start = 0x4000 + 64
for i in range(20):
    b = vm.heap[output_start + i]
    print(f'  output[{i}] = {b:#04x}')
