#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

# Test 1: MOVI + ADD + CMP + JE (pure IChing)
vm = ExtendedIChingVM2()
test1 = """
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
vm.load_assembled(test1)
vm.registers[29] = vm.STACK_SIZE
vm.run(max_cycles=1000)
print(f"Test 1 (ADD+CMP+JE): R0={vm.registers[0]} (expected 42)")

# Test 2: Loop counting to 10
vm2 = ExtendedIChingVM2()
test2 = """
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
vm2.load_assembled(test2)
vm2.registers[29] = vm2.STACK_SIZE
vm2.run(max_cycles=1000)
print(f"Test 2 (Loop): R0={vm2.registers[0]} (expected 10)")

# Test 3: CALL/RET
vm3 = ExtendedIChingVM2()
test3 = """
    ABUNDANCE.1 add_numbers
    RETURN.1 R0, R0

add_numbers:
    PUSH_UP.1 R1
    CREA.1 R0, R0, #5
    CREA.1 R1, R1, #7
    GATHER.0 R0, R1
    WELL.1 R1
    RETURN.0 R0, R0
"""
vm3.load_assembled(test3)
vm3.registers[29] = vm3.STACK_SIZE
vm3.run(max_cycles=1000)
print(f"Test 3 (CALL/RET): R0={vm3.registers[0]} (expected 12)")

# Test 4: Memory read/write
vm4 = ExtendedIChingVM2()
test4 = """
    CREA.1 R8, R0, #0x1000
    CREA.1 R0, R0, #72
    ALLOC.2 R8, R0
    GRADUAL.0 R8
    CREA.1 R0, R0, #0
    ALLOC.2 R8, R0
    CREA.1 R8, R0, #0x1000
    RECV.2 R0, R8
    RETURN.1 R0, R0
"""
vm4.load_assembled(test4)
vm4.registers[29] = vm4.STACK_SIZE
vm4.run(max_cycles=1000)
print(f"Test 4 (LDRB/STRB): R0={vm4.registers[0]} (expected 72)")

# Test 5: AND/OR
vm5 = ExtendedIChingVM2()
test5 = """
    CREA.1 R0, R0, #0xFF
    CREA.1 R1, R1, #0x0F
    MATE.1 R0, R1
    RETURN.1 R0, R0
"""
vm5.load_assembled(test5)
vm5.registers[29] = vm5.STACK_SIZE
vm5.run(max_cycles=1000)
print(f"Test 5 (AND): R0={vm5.registers[0]} (expected 15)")

# Test 6: SUB
vm6 = ExtendedIChingVM2()
test6 = """
    CREA.1 R0, R0, #100
    CREA.1 R1, R1, #37
    GATHER.1 R0, R1
    RETURN.1 R0, R0
"""
vm6.load_assembled(test6)
vm6.registers[29] = vm6.STACK_SIZE
vm6.run(max_cycles=1000)
print(f"Test 6 (SUB): R0={vm6.registers[0]} (expected 63)")

# Test 7: SHL/SHR
vm7 = ExtendedIChingVM2()
test7 = """
    CREA.1 R0, R0, #1
    CREA.1 R1, R1, #8
    MUT.1 R0, R1
    RETURN.1 R0, R0
"""
vm7.load_assembled(test7)
vm7.registers[29] = vm7.STACK_SIZE
vm7.run(max_cycles=1000)
print(f"Test 7 (SHL): R0={vm7.registers[0]} (expected 256)")
