#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

vm = ExtendedIChingVM2()

# Test codegen_emit_native directly
test_asm = """
JMP test_start

emit_native:
    PUSH R5
    PUSH R6
    ; R0=opcode, R1=dst, R2=src, R3=imm, R4=has_imm
    MOV R5, R0
    AND R5, #63
    MOVI R6, #64
    OR R5, R6
    STRB R12, R5
    INC R12
    MOV R5, R1
    AND R5, #31
    CMPI R4, #0
    JE byte2
    MOVI R6, #32
    OR R5, R6
byte2:
    STRB R12, R5
    INC R12
    MOV R5, R2
    AND R5, #31
    STRB R12, R5
    INC R12
    CMPI R4, #0
    JE done
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
done:
    POP R6
    POP R5
    RET

test_start:
    MOVI R12, #0xB040
    ; Emit MOVI R0, #42: opcode=0x33, dst=0, src=0, imm=42, has_imm=1
    MOVI R0, #0x33
    MOVI R1, #0
    MOVI R2, #0
    MOVI R3, #42
    MOVI R4, #1
    CALL emit_native
    ; Check R12
    MOV R0, R12
    HLT
"""

vm.load_assembled(test_asm)
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=1000)

print(f"VM state: {vm.state}")
print(f"R0 (final R12): {vm.registers[0]:#x}")
print(f"R12: {vm.registers[12]:#x}")

# Read output at 0xB040
for i in range(10):
    print(f"  heap[0x{0xB040+i:x}] = {vm.heap[0xB040+i]:#04x}")

# Expected: 73 20 00 2a 00 00 00
print(f"\nExpected: 73 20 00 2a 00 00 00")
