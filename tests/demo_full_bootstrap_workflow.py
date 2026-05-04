#!/usr/bin/env python3
"""
完全自举工作流演示

展示完整的自举流程：
1. .evo 源代码
2. gen2 编译器编译 → .asm 汇编
3. C 虚拟机汇编器 → .raw 原始字节码
4. C 虚拟机直接运行（不依赖 Python）

这证明系统已经完全自举：
- 编译器核心（gen2）用易衍语言写的
- 执行层（C 虚拟机）完全独立于 Python
"""

import sys
import os
import subprocess
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from evomorph.bootstrap.enhanced_bootstrap import EnhancedBootstrap


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_full_bootstrap_workflow():
    """
    演示完整的自举工作流
    
    流程：
    .evo → gen2编译器 → .asm → C汇编器 → .raw → C虚拟机运行
    """
    
    print_header("完全自举工作流演示")
    
    eb = EnhancedBootstrap()
    
    demo_evo = os.path.join(PROJECT_ROOT, "tests", "full_bootstrap_demo.evo")
    
    if not os.path.exists(demo_evo):
        print(f"错误: 演示文件不存在: {demo_evo}")
        return False
    
    print("\n📄 第1步: 查看 .evo 源代码")
    print("-" * 70)
    with open(demo_evo, 'r', encoding='utf-8') as f:
        print(f.read())
    
    print_header("第2步: 用 gen2 编译器编译 .evo → .asm")
    print("-" * 70)
    
    temp_asm = os.path.join(PROJECT_ROOT, "tests", "temp_demo.asm")
    temp_raw = os.path.join(PROJECT_ROOT, "tests", "temp_demo.raw")
    
    print(f"\n编译: {demo_evo}")
    print(f"输出: {temp_asm}")
    
    result = eb.compile_for_tcb(
        demo_evo,
        temp_asm,
        temp_raw,
        verbose=True
    )
    
    if not result["success"]:
        print(f"编译失败: {result.get('error', '未知错误')}")
        return False
    
    print(f"\n✅ 编译成功!")
    print(f"   使用代次: {result['generation']}")
    print(f"   基因座数量: {result['loci_count']}")
    
    if os.path.exists(temp_asm):
        print(f"\n📄 生成的 .asm 文件内容:")
        print("-" * 70)
        with open(temp_asm, 'r', encoding='utf-8') as f:
            print(f.read())
    
    print_header("第3步: C 虚拟机汇编器 .asm → .raw")
    print("-" * 70)
    
    tcb_status = eb.check_tcb_status()
    vm_exec = tcb_status.c_vm_path
    
    if not tcb_status.assembler_available:
        print("⚠️  C 虚拟机汇编器不可用，跳过此步")
    else:
        if os.path.exists(temp_raw):
            print(f"\n✅ 原始字节码已生成: {temp_raw}")
            
            import struct
            with open(temp_raw, 'rb') as f:
                raw_bytes = f.read()
            
            print(f"\n📄 原始字节码 (十六进制):")
            print("-" * 70)
            for i in range(0, len(raw_bytes), 16):
                hex_line = ' '.join(f'{b:02X}' for b in raw_bytes[i:i+16])
                ascii_line = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw_bytes[i:i+16])
                print(f'{i:04X}: {hex_line:<48} {ascii_line}')
            
            print(f"\n📋 指令解码:")
            print("-" * 70)
            
            hex_instrs = {
                0: "RECV", 1: "RETURN", 2: "BRANCH", 4: "YIELD",
                6: "PUSH_UP", 8: "SPECULATE", 9: "SHOCK", 12: "MICRO",
                13: "ABOUND", 16: "MERGE", 17: "ALLOC", 21: "SYNC",
                22: "WELL", 24: "GATHER", 25: "FOLLOWING", 27: "JOY",
                29: "REPLACE", 34: "SPRT", 36: "STILL", 38: "MUT",
                39: "BARRIER", 42: "FUTU", 46: "CAST", 47: "ABUNDANCE",
                49: "INCREASE", 50: "DISPERSE", 51: "TRUST", 52: "GRADUAL",
                56: "HALT", 58: "LOCK", 61: "FELLOWSHIP", 62: "MATE", 63: "CREA",
            }
            
            for i in range(0, len(raw_bytes), 4):
                if i + 3 >= len(raw_bytes):
                    break
                byte1 = raw_bytes[i]
                byte2 = raw_bytes[i+1]
                op1 = raw_bytes[i+2]
                op2 = raw_bytes[i+3]
                
                opcode = (byte1 >> 2) & 0x3F
                modifier = ((byte1 & 0x03) << 4) | (byte2 & 0x0F)
                
                mnemonic = hex_instrs.get(opcode, f"UNKNOWN_{opcode}")
                
                if opcode in [0, 2, 21, 56]:
                    instr_str = mnemonic
                else:
                    instr_str = f"{mnemonic} R{op1}, {op2}"
                
                print(f"  {i//4:2d}: {byte1:02X} {byte2:02X} {op1:02X} {op2:02X}  →  {instr_str}")
    
    print_header("第4步: 用 C 虚拟机直接运行 .raw 字节码")
    print("-" * 70)
    
    if not tcb_status.can_execute_raw:
        print("⚠️  C 虚拟机不可执行原始字节码")
        return False
    
    if not os.path.exists(temp_raw):
        print(f"⚠️  原始字节码文件不存在: {temp_raw}")
        return False
    
    print(f"\n▶️  执行命令: {vm_exec} run {temp_raw}")
    print("-" * 70)
    
    try:
        result = subprocess.run(
            [vm_exec, "run", temp_raw, "1000000"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"\n📤 标准输出:")
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                print(f"  {line}")
        else:
            print("  (无输出)")
        
        if result.stderr:
            print(f"\n📥 标准错误:")
            for line in result.stderr.strip().split('\n'):
                print(f"  {line}")
        
        print(f"\n✅ 执行完成! 返回码: {result.returncode}")
        
    except subprocess.TimeoutExpired:
        print("❌ 执行超时")
    except Exception as e:
        print(f"❌ 执行错误: {e}")
    
    print_header("第5步: 运行现有的自举测试程序")
    print("-" * 70)
    
    test_asm = os.path.join(PROJECT_ROOT, "bootstrap", "runtime", "bootstrap_full_test.asm")
    test_raw = os.path.join(PROJECT_ROOT, "bootstrap", "runtime", "bootstrap_full_test.raw")
    
    if os.path.exists(test_asm):
        print(f"\n📄 现有测试程序: {test_asm}")
        print("-" * 70)
        with open(test_asm, 'r', encoding='utf-8') as f:
            print(f.read())
        
        print(f"\n▶️  汇编测试程序...")
        try:
            result = subprocess.run(
                [vm_exec, "asm", test_asm, test_raw],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and os.path.exists(test_raw):
                print(f"✅ 汇编成功")
                
                print(f"\n▶️  运行测试程序...")
                result = subprocess.run(
                    [vm_exec, "run", test_raw, "1000000"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                print(f"\n📤 输出:")
                if result.stdout:
                    for line in result.stdout.strip().split('\n'):
                        print(f"  {line}")
                
                print(f"\n✅ 测试程序执行完成! 返回码: {result.returncode}")
            else:
                print(f"❌ 汇编失败: {result.stderr}")
                
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    print_header("自举流程演示完成")
    print("-" * 70)
    
    print("""
📌 关键点总结:

1. ✅ 编译器核心已自举
   - gen1/gen2 编译器用易衍语言编写
   - 由易衍编译器编译，不再依赖 Python

2. ✅ 执行层完全独立
   - C 虚拟机 (ichingvm_bootstrap) 独立运行
   - 不依赖 Python 解释器

3. ⚠️ Python 只是"用户界面层"
   - 用于命令行解析、文件 IO
   - 作为"验证层"检查编译器输出
   - 可以完全用易衍重写（当 stdlib 完善后）

4. 🚀 完全独立的执行流程:
   .evo → gen2编译器 → .asm → C汇编器 → .raw → C虚拟机运行
                   ↑                    ↑
              易衍语言实现            完全独立于 Python
""")
    
    for f in [temp_asm, temp_raw]:
        if os.path.exists(f):
            try:
                os.unlink(f)
            except:
                pass
    
    return True


def demo_comparison():
    """
    演示两种运行方式的对比
    """
    
    print_header("两种运行方式对比")
    
    print("""
方式 A: Python 辅助方式 (当前用于开发/调试)
─────────────────────────────────────────────────────

用户输入
    ↓
Python 接口层 (enhanced_bootstrap.py)
    ├─ 解析命令行参数
    ├─ 读取文件
    ├─ 调用 gen1/gen2 编译器
    └─ 显示结果
    ↓
gen1/gen2 编译器 (易衍语言实现)
    ↓
Python 运行时解释器 或 C 虚拟机
    ↓
结果输出


方式 B: 完全自举方式 (生产/独立执行)
─────────────────────────────────────────────────────

用户输入
    ↓
易衍语言编写的命令行程序 (*.evo)
    ↓
gen2 编译器 (自举编译)
    ↓
.asm 汇编文件
    ↓
C 虚拟机汇编器
    ↓
.raw 原始字节码
    ↓
C 虚拟机 (ichingvm_bootstrap) 直接运行
    ↓
结果输出

⚠️ 注意: 方式 B 需要易衍语言有完善的 stdlib 支持
    (文件IO、命令行参数解析等)
""")


def main():
    """主函数"""
    
    print("\n" + "#" * 70)
    print("#  易衍·Evomorph 完全自举演示")
    print("#  =====================================")
    print("#")
    print("#  目标: 展示系统已完全自举")
    print("#        - 编译器核心用易衍语言编写")
    print("#        - C 虚拟机完全独立于 Python")
    print("#" * 70)
    
    demo_full_bootstrap_workflow()
    demo_comparison()
    
    print("\n" + "=" * 70)
    print("演示完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
