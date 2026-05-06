#!/usr/bin/env python3
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler, OUTPUT_BUF
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

compiler = BootstrapCompiler()
vm = compiler.vm

# Test codegen_init and a simple emit
test_asm = """
JMP test_start

codegen_init:
    MOVI R12, #0xB000
    ADD R12, #64
    MOVI R13, #0
    MOV R14, R10
    RET

codegen_emit_native:
    PUSH R5
    PUSH R6
    MOV R5, R0
    AND R5, #63
    MOVI R6, #64
    OR R5, R6
    STRB R12, R5
    INC R12
    MOV R5, R1
    AND R5, #31
    CMPI R4, #0
    JE codegen_native_byte2
    MOVI R6, #32
    OR R5, R6
codegen_native_byte2:
    STRB R12, R5
    INC R12
    MOV R5, R2
    AND R5, #31
    STRB R12, R5
    INC R12
    CMPI R4, #0
    JE codegen_native_done
    MOV R5, R3
    AND R5, #255
    STRB R12, R5
    INC R12
    MOV R5, R3
    SHR R5, #8
    AND R5, #255
    STRB R12, R5
    INC R12
    MOV R5, R3
    SHR R5, #16
    AND R5, #255
    STRB R12, R5
    INC R12
    MOV R5, R3
    SHR R5, #24
    AND R5, #255
    STRB R12, R5
    INC R12
codegen_native_done:
    POP R6
    POP R5
    RET

test_start:
    ; Set R10 (token count) to 0
    MOVI R10, #0
    CALL codegen_init
    ; Emit MOVI R0, #42
    MOVI R0, #0x33    ; MOVI opcode
    MOVI R1, #0       ; dst=R0
    MOVI R2, #0       ; src=R0
    MOVI R3, #42      ; imm=42
    MOVI R4, #1       ; has_imm=1
    CALL codegen_emit_native
    ; Emit HLT
    MOVI R0, #0x01    ; HLT opcode
    MOVI R1, #0       ; dst
    MOVI R2, #0       ; src
    MOVI R3, #0       ; imm
    MOVI R4, #0       ; has_imm=0
    CALL codegen_emit_native
    ; Check output
    MOV R0, R12
    SUB R0, #0xB000
    HLT
"""

vm.load_assembled(test_asm)
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=10000)

print(f"VM state: {vm.state}")
print(f"R0 (output size): {vm.registers[0]}")
print(f"R12 (output pos): {vm.registers[12]:#x}")

# Read output
output_start = OUTPUT_BUF + 64
for i in range(20):
    b = vm.heap[output_start + i]
    print(f"  output[{i}] = {b:#04x}")
