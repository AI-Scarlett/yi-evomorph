#!/usr/bin/env python3
"""
P3 EVB VM 自举 — vm_core.evob 运行验证
"""

import sys
import os
import struct

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState

# Guest 内存布局 (与 vm_core.evoasm 一致)
G_PROGRAM_BASE = 0x30000
G_REGS_BASE    = 0x40000
G_STACK_BASE   = 0x40400
G_FLAGS_BASE   = 0x44400


def assemble(source: str) -> bytes:
    """用 Python assembler 汇编 guest 程序"""
    vm = ExtendedIChingVM2()
    return bytes(vm.assemble(source))


def run_vm(vm_bytecode: bytes, guest_program: bytes, verbose: bool = True) -> dict:
    """在 vm_core.evob 中运行 guest program

    Returns:
        dict with 'regs', 'flags', 'cycles', 'state'
    """
    vm = ExtendedIChingVM2()

    # 加载 vm_core.evob 到 program
    vm.program = bytearray(vm_bytecode)

    # 加载 guest program 到 heap
    for i, b in enumerate(guest_program):
        vm.heap[G_PROGRAM_BASE + i] = b

    # 设置 R0 = 0 (guest program 在 g_program_base + 0)
    vm.registers[0] = 0
    vm.registers[29] = vm.STACK_SIZE

    vm.run(max_cycles=500000)

    if verbose:
        print(f"  VM state: {vm.state.name}, cycle_count: {vm.cycle_count}")

    # 读取 guest registers
    guest_regs = {}
    if vm.state == VMState.HALTED:
        for i in range(16):
            addr = G_REGS_BASE + i * 4
            if addr + 3 < len(vm.heap):
                val = struct.unpack('<I', bytes(vm.heap[addr:addr+4]))[0]
                if val != 0:
                    guest_regs[i] = val

        # 读取 guest flags
        guest_flags = {}
        for i in range(4):
            guest_flags[i] = vm.heap[G_FLAGS_BASE + i]

    return {
        'regs': guest_regs,
        'flags': guest_flags if vm.state == VMState.HALTED else {},
        'cycles': vm.cycle_count,
        'state': vm.state.name,
        'result': vm.registers[0]  # host R0 = return value
    }


def test_1_simple_arithmetic():
    """测试 1: 简单算术
    CREA.1 R0, R0, #5     ; R0 = 5
    CREA.1 R1, R1, #3     ; R1 = 3
    INCREASE.0 R0, R1      ; R0 = R0 + R1 (= 8)
    HALT
    验证: guest R0 = 8, result = 8
    """
    print("\n=== Test 1: Simple Arithmetic ===")

    guest_src = """
CREA.1 R0, R0, #5
CREA.1 R1, R1, #3
INCREASE.0 R0, R1
HALT
"""
    guest_bytes = assemble(guest_src)
    print(f"  Guest program: {len(guest_bytes)} bytes")

    vm_path = "/tmp/vm_core.evob"
    if not os.path.exists(vm_path):
        vm_path = os.path.join(PROJECT_ROOT, "evomorph", "bootstrap", "vm_core.evob")
    vm_bytes = open(vm_path, "rb").read()

    result = run_vm(vm_bytes, guest_bytes)
    print(f"  Host R0 (return): {result['result']}")
    print(f"  Guest regs: {result['regs']}")
    print(f"  Guest flags: {result['flags']}")

    # guest R0 should be 8
    guest_r0 = result['regs'].get(0)
    if guest_r0 == 8:
        print("  ✓ PASS: guest R0 = 8")
        return True
    else:
        print(f"  ✗ FAIL: guest R0 = {guest_r0}, expected 8")
        return False


def test_2_conditional_branch():
    """测试 2: 条件分支
    CREA.1 R0, R0, #5
    CREA.1 R1, R1, #5
    REDUCE.0 R0, R1        ; R0 = 0, zero_flag = 1
    BRANCH.2 @label        ; JE → 跳转到 label
    CREA.1 R2, R2, #99     ; 不应执行
    label:
    HALT
    验证: guest R2 未设置 (= 0)
    """
    print("\n=== Test 2: Conditional Branch (JE) ===")

    guest_src = """
CREA.1 R0, R0, #5
CREA.1 R1, R1, #5
REDUCE.0 R0, R1
BRANCH.2 skip_99
CREA.1 R2, R2, #99
skip_99:
HALT
"""
    guest_bytes = assemble(guest_src)

    vm_path = "/tmp/vm_core.evob"
    if not os.path.exists(vm_path):
        vm_path = os.path.join(PROJECT_ROOT, "evomorph", "bootstrap", "vm_core.evob")
    vm_bytes = open(vm_path, "rb").read()

    result = run_vm(vm_bytes, guest_bytes)
    print(f"  Guest regs: {result['regs']}")
    print(f"  Guest flags: {result['flags']}")

    # guest R2 should NOT be 99
    guest_r2 = result['regs'].get(2)
    if guest_r2 is None or guest_r2 == 0:
        print("  ✓ PASS: guest R2 not set to 99 (branch taken)")
        return True
    else:
        print(f"  ✗ FAIL: guest R2 = {guest_r2}, expected not set")
        return False


def test_3_function_call():
    """测试 3: 函数调用
    CREA.1 R0, R0, #10
    ABUNDANCE.1 R0, R0, func  ; call func
    HALT
    func:
      INCREASE.0 R0, R0      ; R0 += R0 (= 20)
      RETURN.0 R0, R0
    验证: guest R0 = 20
    """
    print("\n=== Test 3: Function Call ===")

    guest_src = """
CREA.1 R0, R0, #10
ABUNDANCE.1 R0, R0, func
HALT
func:
INCREASE.0 R0, R0
RETURN.0 R0, R0
"""
    guest_bytes = assemble(guest_src)

    vm_path = "/tmp/vm_core.evob"
    if not os.path.exists(vm_path):
        vm_path = os.path.join(PROJECT_ROOT, "evomorph", "bootstrap", "vm_core.evob")
    vm_bytes = open(vm_path, "rb").read()

    result = run_vm(vm_bytes, guest_bytes)
    print(f"  Guest regs: {result['regs']}")

    guest_r0 = result['regs'].get(0)
    if guest_r0 == 20:
        print("  ✓ PASS: guest R0 = 20")
        return True
    else:
        print(f"  ✗ FAIL: guest R0 = {guest_r0}, expected 20")
        return False


def test_4_carry_flag():
    """测试 4: 借位标志 (carry/below)
    REDUCE: 3 - 5 = -2 (unsigned borrow)
    CARRY 应为 1, JL 应跳转
    CREA.1 R0, R0, #3
    CREA.1 R1, R1, #5
    REDUCE.0 R0, R1        ; R0 = 3-5 = 0xFFFFFFFE, carry=1
    BRANCH.4 skip_99       ; JL → if carry==1 → jump
    CREA.1 R2, R2, #99     ; 不应执行
    skip_99:
    HALT
    验证: guest R2 未设置, flags = {0: 0, 1: 1} (carry=1)
    """
    print("\n=== Test 4: Carry Flag (JL) ===")

    guest_src = """
CREA.1 R0, R0, #3
CREA.1 R1, R1, #5
REDUCE.0 R0, R1
BRANCH.4 skip_99
CREA.1 R2, R2, #99
skip_99:
HALT
"""
    guest_bytes = assemble(guest_src)

    vm_path = "/tmp/vm_core.evob"
    if not os.path.exists(vm_path):
        vm_path = os.path.join(PROJECT_ROOT, "evomorph", "bootstrap", "vm_core.evob")
    vm_bytes = open(vm_path, "rb").read()

    result = run_vm(vm_bytes, guest_bytes)
    print(f"  Guest regs: {result['regs']}")
    print(f"  Guest flags: {result['flags']}")

    guest_r2 = result['regs'].get(2)
    guest_carry = result['flags'].get(1)

    ok = True
    if guest_r2 is not None and guest_r2 != 0:
        print(f"  ✗ FAIL: guest R2 = {guest_r2}, expected not set")
        ok = False
    if guest_carry != 1:
        print(f"  ✗ FAIL: guest carry flag = {guest_carry}, expected 1")
        ok = False
    if ok:
        print("  ✓ PASS: JL took branch (carry=1)")
    return ok


if __name__ == "__main__":
    print("P3 EVB VM 核心解释器 — 测试套件")
    print("=" * 50)

    # 先编译 vm_core.evoasm
    vm_evob_path = "/tmp/vm_core.evob"
    if not os.path.exists(vm_evob_path):
        print("请先运行: python3 evomorph/tools/evo_assemble.py evomorph/bootstrap/vm_core.evoasm -o /tmp/vm_core.evob")
        sys.exit(1)

    results = []
    results.append(("Test 1: Arithmetic", test_1_simple_arithmetic()))
    results.append(("Test 2: Branch (JE)", test_2_conditional_branch()))
    results.append(("Test 3: Function Call", test_3_function_call()))
    results.append(("Test 4: Carry Flag (JL)", test_4_carry_flag()))

    print("\n" + "=" * 50)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    for name, r in results:
        print(f"  {'✓' if r else '✗'} {name}")
    print(f"\n  {passed}/{total} tests passed")
