#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

def test_iching_extended():
    # Test 1: MOVI + ADD + CMP + JE
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
    ok = vm.registers[0] == 42
    print(f"Test 1 (ADD+CMP+JE): R0={vm.registers[0]} (expected 42) - {'PASS' if ok else 'FAIL'}")

    # Test 2: CMPI + JL (unsigned less than)
    vm2 = ExtendedIChingVM2()
    test2 = """
    CREA.1 R0, R0, #5
    FELLOWSHIP.2 R0, R0, #10
    BRANCH.4 less_than
    CREA.1 R1, R1, #0
    RETURN.1 R1, R1
less_than:
    CREA.1 R1, R1, #1
    RETURN.1 R1, R1
"""
    vm2.load_assembled(test2)
    vm2.registers[29] = vm2.STACK_SIZE
    vm2.run(max_cycles=1000)
    ok = vm2.registers[1] == 1
    print(f"Test 2 (CMPI+JL): R1={vm2.registers[1]} (expected 1) - {'PASS' if ok else 'FAIL'}")

    # Test 3: CMPI + JG (unsigned greater than)
    vm3 = ExtendedIChingVM2()
    test3 = """
    CREA.1 R0, R0, #20
    FELLOWSHIP.2 R0, R0, #10
    BRANCH.6 greater_than
    CREA.1 R1, R1, #0
    RETURN.1 R1, R1
greater_than:
    CREA.1 R1, R1, #1
    RETURN.1 R1, R1
"""
    vm3.load_assembled(test3)
    vm3.registers[29] = vm3.STACK_SIZE
    vm3.run(max_cycles=1000)
    ok = vm3.registers[1] == 1
    print(f"Test 3 (CMPI+JG): R1={vm3.registers[1]} (expected 1) - {'PASS' if ok else 'FAIL'}")

    # Test 4: OR (MATE.3)
    vm4 = ExtendedIChingVM2()
    test4 = """
    CREA.1 R0, R0, #15
    CREA.1 R1, R1, #240
    MATE.3 R0, R1
    RETURN.1 R0, R0
"""
    vm4.load_assembled(test4)
    vm4.registers[29] = vm4.STACK_SIZE
    vm4.run(max_cycles=1000)
    ok = vm4.registers[0] == 255
    print(f"Test 4 (OR): R0={vm4.registers[0]} (expected 255) - {'PASS' if ok else 'FAIL'}")

    # Test 5: Loop with JGE (exit when R0 >= R1)
    vm5 = ExtendedIChingVM2()
    test5 = """
    CREA.1 R0, R0, #0
    CREA.1 R1, R1, #10
loop:
    FELLOWSHIP.1 R0, R1
    BRANCH.7 done
    MICRO.1 R0, R0
    BRANCH.1 loop
done:
    RETURN.1 R0, R0
"""
    vm5.load_assembled(test5)
    vm5.registers[29] = vm5.STACK_SIZE
    vm5.run(max_cycles=1000)
    ok = vm5.registers[0] == 10
    print(f"Test 5 (Loop+JGE): R0={vm5.registers[0]} (expected 10) - {'PASS' if ok else 'FAIL'}")

    # Test 6: CALL/RET with label
    vm6 = ExtendedIChingVM2()
    test6 = """
    BRANCH.1 start
double_it:
    GATHER.0 R0, R0
    RETURN.0 R0, R0
start:
    CREA.1 R0, R0, #21
    ABUNDANCE.1 R0, R0, @double_it
    RETURN.1 R0, R0
"""
    vm6.load_assembled(test6)
    vm6.registers[29] = vm6.STACK_SIZE
    vm6.run(max_cycles=1000)
    ok = vm6.registers[0] == 42
    print(f"Test 6 (CALL/RET): R0={vm6.registers[0]} (expected 42) - {'PASS' if ok else 'FAIL'}")

    # Test 7: Memory operations (STR/STRB/LDR/LDRB)
    vm7 = ExtendedIChingVM2()
    test7 = """
    CREA.1 R0, R0, #0x1000
    CREA.1 R1, R1, #0x41424344
    ALLOC.1 R0, R1
    RECV.1 R2, R0
    RETURN.1 R2, R2
"""
    vm7.load_assembled(test7)
    vm7.registers[29] = vm7.STACK_SIZE
    vm7.run(max_cycles=1000)
    ok = vm7.registers[2] == 0x41424344
    print(f"Test 7 (STR+LDR): R2=0x{vm7.registers[2]:08X} (expected 0x41424344) - {'PASS' if ok else 'FAIL'}")

    # Test 8: SUB + JNE
    vm8 = ExtendedIChingVM2()
    test8 = """
    CREA.1 R0, R0, #100
    CREA.1 R1, R1, #1
loop8:
    GATHER.1 R0, R1
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.3 loop8
    RETURN.1 R0, R0
"""
    vm8.load_assembled(test8)
    vm8.registers[29] = vm8.STACK_SIZE
    vm8.run(max_cycles=10000)
    ok = vm8.registers[0] == 0
    print(f"Test 8 (SUB+JNE loop): R0={vm8.registers[0]} (expected 0) - {'PASS' if ok else 'FAIL'}")

    # Test 9: PUSH/POP
    vm9 = ExtendedIChingVM2()
    test9 = """
    CREA.1 R0, R0, #12345
    PUSH_UP.1 R0, R0
    CREA.1 R0, R0, #0
    WELL.1 R0, R0
    RETURN.1 R0, R0
"""
    vm9.load_assembled(test9)
    vm9.registers[29] = vm9.STACK_SIZE
    vm9.run(max_cycles=1000)
    ok = vm9.registers[0] == 12345
    print(f"Test 9 (PUSH/POP): R0={vm9.registers[0]} (expected 12345) - {'PASS' if ok else 'FAIL'}")

    # Test 10: AND + SHR (bitwise operations)
    vm10 = ExtendedIChingVM2()
    test10 = """
    CREA.1 R0, R0, #0xFF00
    CREA.1 R1, R1, #8
    MUT.2 R0, R1
    RETURN.1 R0, R0
"""
    vm10.load_assembled(test10)
    vm10.registers[29] = vm10.STACK_SIZE
    vm10.run(max_cycles=1000)
    ok = vm10.registers[0] == 0xFF
    print(f"Test 10 (SHR): R0={vm10.registers[0]} (expected 255) - {'PASS' if ok else 'FAIL'}")

    print("\nAll IChing extended instruction tests completed!")

if __name__ == "__main__":
    test_iching_extended()
