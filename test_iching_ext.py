#!/usr/bin/env python3
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

vm = ExtendedIChingVM2()

# Test IChing extended instructions
# CREA.1 = MOVI, RECV.2 = LDRB, ALLOC.2 = STRB
# FELLOWSHIP.1 = CMP, BRANCH.2 = JE, BRANCH.3 = JNE
# ABUNDANCE.1 = CALL, RETURN.0 = RET, RETURN.1 = HLT
# GATHER.0 = ADD, GATHER.1 = SUB, PUSH_UP.1 = PUSH, WELL.1 = POP
# GRADUAL.0 = INC, MATE.1 = AND

test_asm = """
JMP test_start

strlen:
    PUSH_UP.1 R4
    CREA.1 R5, R0, #0
strlen_loop:
    RECV.2 R0, R4
    FELLOWSHIP.1 R0, R0, #0
    BRANCH.2 strlen_done
    GRADUAL.0 R4
    GRADUAL.0 R5
    BRANCH.1 strlen_loop
strlen_done:
    FELLOWSHIP.0 R0, R5
    WELL.1 R4
    RETURN.0 R0, R0

test_start:
    CREA.1 R8, R0, #0x1000
    MOVI R0, #72
    ALLOC.2 R8, R0
    GRADUAL.0 R8
    MOVI R0, #101
    ALLOC.2 R8, R0
    GRADUAL.0 R8
    MOVI R0, #0
    ALLOC.2 R8, R0
    CREA.1 R8, R0, #0x1000
    ABUNDANCE.1 strlen
    RETURN.1 R0, R0
"""

vm.load_assembled(test_asm)
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=10000)

print(f"VM state: {vm.state}")
print(f"R0 (strlen result): {vm.registers[0]} (expected 2)")
print(f"Cycles: {vm.cycle_count}")

# Test 2: MOVI + ADD + CMP + JE
vm2 = ExtendedIChingVM2()
test2_asm = """
    CREA.1 R0, R0, #10
    CREA.1 R1, R1, #20
    GATHER.0 R0, R1
    FELLOWSHIP.1 R0, R0, #30
    BRANCH.2 correct
    CREA.1 R0, R0, #0
    RETURN.1 R0, R0
correct:
    CREA.1 R0, R0, #42
    RETURN.1 R0, R0
"""
vm2.load_assembled(test2_asm)
vm2.registers[29] = vm2.STACK_SIZE
vm2.run(max_cycles=1000)

print(f"\nTest 2: R0 = {vm2.registers[0]} (expected 42)")

# Test 3: Loop with IChing instructions
vm3 = ExtendedIChingVM2()
test3_asm = """
    CREA.1 R0, R0, #0
    CREA.1 R1, R1, #10
loop:
    FELLOWSHIP.1 R0, R1
    BRANCH.3 done
    GRADUAL.0 R0
    BRANCH.1 loop
done:
    RETURN.1 R0, R0
"""
vm3.load_assembled(test3_asm)
vm3.registers[29] = vm3.STACK_SIZE
vm3.run(max_cycles=1000)

print(f"Test 3: R0 = {vm3.registers[0]} (expected 10)")
