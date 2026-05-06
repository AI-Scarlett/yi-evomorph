#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler, OUTPUT_BUF
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

compiler = BootstrapCompiler()
vm = compiler.vm

# Test just the EVOB header writing part
test_asm = """
JMP test_start

codegen_write_byte_at:
    PUSH R4
    MOVI R4, #0x4000
    ADD R4, R0
    STRB R4, R1
    POP R4
    RET

codegen_write_half_at:
    PUSH R4
    PUSH R5
    MOVI R4, #0x4000
    ADD R4, R0
    MOV R5, R1
    SHR R5, #8
    AND R5, #255
    STRB R4, R5
    INC R4
    MOV R5, R1
    AND R5, #255
    STRB R4, R5
    POP R5
    POP R4
    RET

test_start:
    ; Write "EVOB" at offset 0
    MOVI R0, #0
    MOVI R1, #69
    CALL codegen_write_byte_at
    MOVI R0, #1
    MOVI R1, #86
    CALL codegen_write_byte_at
    MOVI R0, #2
    MOVI R1, #79
    CALL codegen_write_byte_at
    MOVI R0, #3
    MOVI R1, #66
    CALL codegen_write_byte_at
    ; version = 3 at offset 4
    MOVI R0, #4
    MOVI R1, #3
    CALL codegen_write_half_at
    ; header_size at offset 6
    MOVI R0, #6
    MOVI R1, #14
    CALL codegen_write_half_at
    ; locus_count at offset 8
    MOVI R0, #8
    MOVI R1, #1
    CALL codegen_write_half_at
    HLT
"""

vm.load_assembled(test_asm)
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=1000)

print(f"VM state: {vm.state}")
# Read output buffer
output = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF+20])
print(f"Output hex: {output.hex()}")
print(f"Magic: {output[:4]}")
if output[:4] == b'EVOB':
    print("EVOB header written correctly!")
else:
    print("EVOB header NOT written correctly!")
    # Check individual bytes
    for i in range(10):
        print(f"  heap[{OUTPUT_BUF+i}] = {vm.heap[OUTPUT_BUF+i]} ({chr(vm.heap[OUTPUT_BUF+i]) if 32 <= vm.heap[OUTPUT_BUF+i] < 127 else '?'})")
