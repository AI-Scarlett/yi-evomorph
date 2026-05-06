#!/usr/bin/env python3
"""
测试扩展虚拟机 - 简化版
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evomorph.vm.virtual_machine import IChingVM, VMState


def test_basic_operations():
    print("=" * 50)
    print("测试基本运算（使用六十四卦指令）")
    print("=" * 50)
    
    vm = IChingVM()
    
    vm.load_program([
        {"opcode": 13, "modifier": 0, "operands": [0, 10]},
        {"opcode": 13, "modifier": 0, "operands": [1, 20]},
        {"opcode": 49, "modifier": 0, "operands": [0, 1]},
        {"opcode": 56, "modifier": 0, "operands": []},
    ])
    
    vm.run(max_cycles=100)
    
    print(f"R0 (10 + 20) = {vm.registers[0]}")
    assert vm.registers[0] == 30, f"加法测试失败: {vm.registers[0]}"
    print("✓ 基本加法测试通过")


def test_extended_arithmetic():
    print("\n" + "=" * 50)
    print("测试扩展算术指令")
    print("=" * 50)
    
    from evomorph.vm.extended_vm import ExtendedIChingVM, Opcodes
    
    vm = ExtendedIChingVM()
    
    vm.registers[0] = 10
    vm.registers[1] = 20
    
    vm.load_extended_program([
        {"opcode": Opcodes.ADD, "sub_opcode": (1 << 5) | 0},
        {"opcode": Opcodes.HLT, "sub_opcode": 0},
    ])
    
    vm.run(max_cycles=100)
    
    print(f"R0 (10 + 20) = {vm.registers[0]}")
    assert vm.registers[0] == 30, f"加法测试失败: {vm.registers[0]}"
    print("✓ 扩展加法测试通过")


def test_full_arithmetic():
    print("\n" + "=" * 50)
    print("测试完整算术运算")
    print("=" * 50)
    
    from evomorph.vm.extended_vm import ExtendedIChingVM, Opcodes
    
    vm = ExtendedIChingVM()
    
    vm.registers[0] = 100
    vm.registers[1] = 30
    
    vm.load_extended_program([
        {"opcode": Opcodes.SUB, "sub_opcode": (1 << 5) | 0},
        {"opcode": Opcodes.HLT, "sub_opcode": 0},
    ])
    
    vm.run(max_cycles=100)
    
    print(f"R0 (100 - 30) = {vm.registers[0]}")
    assert vm.registers[0] == 70, f"减法测试失败: {vm.registers[0]}"
    print("✓ 减法测试通过")
    
    vm2 = ExtendedIChingVM()
    vm2.registers[0] = 7
    vm2.registers[1] = 8
    
    vm2.load_extended_program([
        {"opcode": Opcodes.MUL, "sub_opcode": (1 << 5) | 0},
        {"opcode": Opcodes.HLT, "sub_opcode": 0},
    ])
    
    vm2.run(max_cycles=100)
    
    print(f"R0 (7 * 8) = {vm2.registers[0]}")
    assert vm2.registers[0] == 56, f"乘法测试失败: {vm2.registers[0]}"
    print("✓ 乘法测试通过")


def test_bitwise():
    print("\n" + "=" * 50)
    print("测试位运算")
    print("=" * 50)
    
    from evomorph.vm.extended_vm import ExtendedIChingVM, Opcodes
    
    vm = ExtendedIChingVM()
    vm.registers[0] = 0xFF00
    vm.registers[1] = 0x00FF
    
    vm.load_extended_program([
        {"opcode": Opcodes.AND, "sub_opcode": (1 << 5) | 0},
        {"opcode": Opcodes.HLT, "sub_opcode": 0},
    ])
    
    vm.run(max_cycles=100)
    
    print(f"R0 (0xFF00 & 0x00FF) = 0x{vm.registers[0]:08X}")
    assert vm.registers[0] == 0x0000, f"AND测试失败"
    print("✓ AND测试通过")
    
    vm2 = ExtendedIChingVM()
    vm2.registers[0] = 0xFF00
    vm2.registers[1] = 0x00FF
    
    vm2.load_extended_program([
        {"opcode": Opcodes.OR, "sub_opcode": (1 << 5) | 0},
        {"opcode": Opcodes.HLT, "sub_opcode": 0},
    ])
    
    vm2.run(max_cycles=100)
    
    print(f"R0 (0xFF00 | 0x00FF) = 0x{vm2.registers[0]:08X}")
    assert vm2.registers[0] == 0xFFFF, f"OR测试失败"
    print("✓ OR测试通过")


def test_comparison():
    print("\n" + "=" * 50)
    print("测试比较和标志位")
    print("=" * 50)
    
    from evomorph.vm.extended_vm import ExtendedIChingVM, Opcodes
    
    vm = ExtendedIChingVM()
    vm.registers[0] = 10
    vm.registers[1] = 10
    
    vm.load_extended_program([
        {"opcode": Opcodes.CMP, "sub_opcode": (1 << 5) | 0},
        {"opcode": Opcodes.HLT, "sub_opcode": 0},
    ])
    
    vm.run(max_cycles=100)
    
    print(f"零标志: {vm.flag_zero} (10 == 10, 预期 True)")
    assert vm.flag_zero == True, f"零标志测试失败"
    print("✓ 相等比较测试通过")
    
    vm2 = ExtendedIChingVM()
    vm2.registers[0] = 5
    vm2.registers[1] = 10
    
    vm2.load_extended_program([
        {"opcode": Opcodes.CMP, "sub_opcode": (1 << 5) | 0},
        {"opcode": Opcodes.HLT, "sub_opcode": 0},
    ])
    
    vm2.run(max_cycles=100)
    
    print(f"进位标志: {vm2.flag_carry} (5 < 10, 预期 True)")
    assert vm2.flag_carry == True, f"进位标志测试失败"
    print("✓ 小于比较测试通过")


def test_inc_dec():
    print("\n" + "=" * 50)
    print("测试INC/DEC指令")
    print("=" * 50)
    
    from evomorph.vm.extended_vm import ExtendedIChingVM, Opcodes
    
    vm = ExtendedIChingVM()
    vm.registers[0] = 41
    
    vm.load_extended_program([
        {"opcode": Opcodes.INC, "sub_opcode": 0},
        {"opcode": Opcodes.HLT, "sub_opcode": 0},
    ])
    
    vm.run(max_cycles=100)
    
    print(f"R0 (41 + 1) = {vm.registers[0]}")
    assert vm.registers[0] == 42, f"INC测试失败: {vm.registers[0]}"
    print("✓ INC测试通过")
    
    vm2 = ExtendedIChingVM()
    vm2.registers[0] = 100
    
    vm2.load_extended_program([
        {"opcode": Opcodes.DEC, "sub_opcode": 0},
        {"opcode": Opcodes.HLT, "sub_opcode": 0},
    ])
    
    vm2.run(max_cycles=100)
    
    print(f"R0 (100 - 1) = {vm2.registers[0]}")
    assert vm2.registers[0] == 99, f"DEC测试失败: {vm2.registers[0]}"
    print("✓ DEC测试通过")


def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║           扩展虚拟机测试 - 传统CPU指令集                      ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    try:
        test_basic_operations()
        test_extended_arithmetic()
        test_full_arithmetic()
        test_bitwise()
        test_comparison()
        test_inc_dec()
        
        print("\n" + "=" * 50)
        print("所有测试通过！扩展虚拟机工作正常！")
        print("=" * 50)
        return 0
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return 1
    except Exception as e:
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
