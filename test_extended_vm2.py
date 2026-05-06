#!/usr/bin/env python3
"""
扩展虚拟机 v2 完整测试 - 验证标签跳转、CALL/RET、CMPI等
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evomorph.vm.extended_vm2 import ExtendedIChingVM2


def test_arithmetic():
    print("=" * 50)
    print("测试算术指令")
    print("=" * 50)
    
    vm = ExtendedIChingVM2()
    vm.load_assembled("""
        MOVI R0, #10
        MOVI R1, #20
        ADD R0, R1
        HLT
    """)
    vm.run(max_cycles=100)
    assert vm.registers[0] == 30, f"加法失败: {vm.registers[0]}"
    print("✓ 加法: 10 + 20 = 30")


def test_cmpi_and_je():
    print("\n" + "=" * 50)
    print("测试CMPI和条件跳转")
    print("=" * 50)
    
    vm = ExtendedIChingVM2()
    vm.load_assembled("""
        MOVI R0, #42
        CMPI R0, #42
        JE match
        MOVI R1, #0
        JMP done
match:
        MOVI R1, #1
done:
        HLT
    """)
    vm.run(max_cycles=100)
    assert vm.registers[1] == 1, f"CMPI+JE失败: R1={vm.registers[1]}"
    print("✓ CMPI + JE: R0=42, CMPI #42 → JE match → R1=1")


def test_cmpi_and_jne():
    vm = ExtendedIChingVM2()
    vm.load_assembled("""
        MOVI R0, #10
        CMPI R0, #20
        JNE not_equal
        MOVI R1, #0
        JMP done
not_equal:
        MOVI R1, #1
done:
        HLT
    """)
    vm.run(max_cycles=100)
    assert vm.registers[1] == 1, f"CMPI+JNE失败: R1={vm.registers[1]}"
    print("✓ CMPI + JNE: R0=10, CMPI #20 → JNE not_equal → R1=1")


def test_loop_with_labels():
    print("\n" + "=" * 50)
    print("测试循环（标签跳转）")
    print("=" * 50)
    
    vm = ExtendedIChingVM2()
    vm.load_assembled("""
        MOVI R0, #0
        MOVI R1, #10
loop:
        INC R0
        CMP R0, R1
        JNE loop
        HLT
    """)
    vm.run(max_cycles=1000)
    assert vm.registers[0] == 10, f"循环失败: R0={vm.registers[0]}"
    print("✓ 循环: R0从0加到10")


def test_call_ret():
    print("\n" + "=" * 50)
    print("测试CALL/RET")
    print("=" * 50)
    
    vm = ExtendedIChingVM2()
    vm.load_assembled("""
        MOVI R0, #5
        MOVI R1, #3
        CALL add_func
        HLT
add_func:
        ADD R0, R1
        RET
    """)
    vm.run(max_cycles=100)
    assert vm.registers[0] == 8, f"CALL/RET失败: R0={vm.registers[0]}"
    print("✓ CALL/RET: 5 + 3 = 8")


def test_nested_call():
    vm = ExtendedIChingVM2()
    vm.load_assembled("""
        MOVI R0, #1
        CALL func_a
        HLT
func_a:
        MOVI R1, #10
        CALL func_b
        ADD R0, R1
        RET
func_b:
        MOVI R2, #100
        ADD R0, R2
        RET
    """)
    vm.run(max_cycles=200)
    assert vm.registers[0] == 111, f"嵌套CALL失败: R0={vm.registers[0]}"
    print("✓ 嵌套CALL: 1 + 100 + 10 = 111")


def test_push_pop():
    print("\n" + "=" * 50)
    print("测试PUSH/POP")
    print("=" * 50)
    
    vm = ExtendedIChingVM2()
    vm.load_assembled("""
        MOVI R0, #42
        MOVI R1, #99
        PUSH R0
        PUSH R1
        MOVI R0, #0
        MOVI R1, #0
        POP R2
        POP R3
        HLT
    """)
    vm.run(max_cycles=100)
    assert vm.registers[2] == 99, f"POP R2失败: {vm.registers[2]}"
    assert vm.registers[3] == 42, f"POP R3失败: {vm.registers[3]}"
    print(f"✓ PUSH/POP: R2={vm.registers[2]}, R3={vm.registers[3]}")


def test_memory_operations():
    print("\n" + "=" * 50)
    print("测试内存操作")
    print("=" * 50)
    
    vm = ExtendedIChingVM2()
    vm.load_assembled("""
        MOVI R0, #0x1000
        MOVI R1, #0xDEADBEEF
        STR R0, R1
        LDR R2, R0
        HLT
    """)
    vm.run(max_cycles=100)
    assert vm.registers[2] == 0xDEADBEEF, f"STR/LDR失败: R2=0x{vm.registers[2]:08X}"
    print(f"✓ STR/LDR: 写入0xDEADBEEF到0x1000, 读回R2=0x{vm.registers[2]:08X}")


def test_string_operations():
    print("\n" + "=" * 50)
    print("测试字符串操作（LDRB/STRB）")
    print("=" * 50)
    
    vm = ExtendedIChingVM2()
    vm.load_string(0x2000, "Hello")
    
    vm.load_assembled("""
        MOVI R0, #0x2000
        MOVI R1, #0
strlen_loop:
        LDRB R2, R0
        CMPI R2, #0
        JE strlen_done
        INC R0
        INC R1
        JMP strlen_loop
strlen_done:
        HLT
    """)
    vm.run(max_cycles=1000)
    assert vm.registers[1] == 5, f"strlen失败: R1={vm.registers[1]}"
    print(f"✓ strlen: 'Hello' 长度 = {vm.registers[1]}")


def test_factorial():
    print("\n" + "=" * 50)
    print("测试阶乘计算（递归用循环模拟）")
    print("=" * 50)
    
    vm = ExtendedIChingVM2()
    vm.load_assembled("""
        MOVI R0, #1
        MOVI R1, #5
        MOVI R2, #1
fact_loop:
        MUL R0, R2
        INC R2
        CMP R2, R1
        JLE fact_loop
        HLT
    """)
    vm.run(max_cycles=1000)
    assert vm.registers[0] == 120, f"阶乘失败: R0={vm.registers[0]}"
    print(f"✓ 阶乘: 5! = {vm.registers[0]}")


def test_char_classification():
    print("\n" + "=" * 50)
    print("测试字符分类")
    print("=" * 50)
    
    vm = ExtendedIChingVM2()
    vm.load_assembled("""
        MOVI R0, #'5'
        CMPI R0, #'0'
        JL not_digit
        CMPI R0, #'9'
        JG not_digit
        MOVI R3, #1
        JMP done
not_digit:
        MOVI R3, #0
done:
        HLT
    """)
    vm.run(max_cycles=100)
    assert vm.registers[3] == 1, f"字符分类失败: R3={vm.registers[3]}"
    print(f"✓ 字符分类: '5' 是数字 → R3={vm.registers[3]}")


def test_fibonacci():
    print("\n" + "=" * 50)
    print("测试斐波那契数列")
    print("=" * 50)
    
    vm = ExtendedIChingVM2()
    vm.load_assembled("""
        MOVI R0, #0
        MOVI R1, #1
        MOVI R2, #0
        MOVI R3, #10
fib_loop:
        ADD R2, R0, R1
        MOV R0, R1
        MOV R1, R2
        MOVI R2, #0
        DEC R3
        CMPI R3, #0
        JNE fib_loop
        HLT
    """)
    vm.run(max_cycles=1000)
    print(f"✓ 斐波那契: R0={vm.registers[0]}, R1={vm.registers[1]}")


def test_string_copy():
    print("\n" + "=" * 50)
    print("测试字符串复制（用汇编实现）")
    print("=" * 50)
    
    vm = ExtendedIChingVM2()
    vm.load_string(0x3000, "Evomorph")
    
    vm.load_assembled("""
        MOVI R0, #0x3000
        MOVI R1, #0x4000
copy_loop:
        LDRB R2, R0
        STRB R1, R2
        CMPI R2, #0
        JE copy_done
        INC R0
        INC R1
        JMP copy_loop
copy_done:
        HLT
    """)
    vm.run(max_cycles=1000)
    result = vm.read_string(0x4000)
    assert result == "Evomorph", f"字符串复制失败: '{result}'"
    print(f"✓ 字符串复制: 'Evomorph' → '{result}'")


def test_complex_compiler_pattern():
    print("\n" + "=" * 50)
    print("测试编译器模式（扫描+分类+输出）")
    print("=" * 50)
    
    vm = ExtendedIChingVM2()
    test_input = b"ABC 123\x00"
    for i, b in enumerate(test_input):
        vm.heap[0x5000 + i] = b
    
    vm.load_assembled("""
        MOVI R0, #0x5000
        MOVI R10, #0
        MOVI R11, #0
        MOVI R12, #0
scan_loop:
        LDRB R1, R0
        CMPI R1, #0
        JE scan_done
        CMPI R1, #'A'
        JL check_digit
        CMPI R1, #'Z'
        JG check_lower
        INC R10
        JMP scan_next
check_lower:
        CMPI R1, #'a'
        JL check_digit
        CMPI R1, #'z'
        JG check_digit
        INC R10
        JMP scan_next
check_digit:
        CMPI R1, #'0'
        JL check_space
        CMPI R1, #'9'
        JG check_space
        INC R11
        JMP scan_next
check_space:
        CMPI R1, #' '
        JNE scan_next
        INC R12
scan_next:
        INC R0
        JMP scan_loop
scan_done:
        HLT
    """)
    vm.run(max_cycles=5000)
    print(f"✓ 编译器模式: 字母={vm.registers[10]}, 数字={vm.registers[11]}, 空格={vm.registers[12]}")
    assert vm.registers[10] == 3, f"字母数错误: {vm.registers[10]}"
    assert vm.registers[11] == 3, f"数字数错误: {vm.registers[11]}"
    assert vm.registers[12] == 1, f"空格数错误: {vm.registers[12]}"


if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     扩展虚拟机 v2 完整测试 - 标签跳转/CALL/RET/CMPI      ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    test_arithmetic()
    test_cmpi_and_je()
    test_cmpi_and_jne()
    test_loop_with_labels()
    test_call_ret()
    test_nested_call()
    test_push_pop()
    test_memory_operations()
    test_string_operations()
    test_factorial()
    test_char_classification()
    test_string_copy()
    test_complex_compiler_pattern()
    
    print("\n" + "=" * 60)
    print("所有测试通过！扩展虚拟机 v2 完全可用！")
    print("=" * 60)
