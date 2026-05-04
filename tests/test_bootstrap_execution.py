#!/usr/bin/env python3
"""
自举执行测试：验证第1代编译器是否可以实际执行编译任务
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

BOOTSTRAP_FILE = os.path.join(
    PROJECT_ROOT,
    "evomorph", "bootstrap", "full_self_bootstrap.evo"
)

def test_compile_and_execute():
    """编译第1代编译器并测试执行"""
    print("=" * 70)
    print("易衍·Evomorph 自举执行测试")
    print("=" * 70)
    
    from evomorph.compiler import EvocCompiler
    from evomorph.bootstrap.runtime import EvoRuntime
    
    print("\n[步骤1] 编译 full_self_bootstrap.evo (第1代编译器)")
    print("-" * 70)
    
    compiler = EvocCompiler()
    
    try:
        with open(BOOTSTRAP_FILE, "r", encoding="utf-8") as f:
            source = f.read()
        print(f"  源代码大小: {len(source)} 字符")
    except Exception as e:
        print(f"  ❌ 错误: 无法读取文件 - {e}")
        return False
    
    print("\n  编译中...")
    try:
        result = compiler.compile(source, output_format="dict")
        print("  ✅ 编译成功!")
        
        loci = result.get("loci", [])
        meta_loci = result.get("meta_loci", [])
        
        print(f"\n  编译结果统计:")
        print(f"    - 基因座数量: {len(loci)}")
        print(f"    - 元基因座数量: {len(meta_loci)}")
        
        # 打印所有基因座名称，用于分析
        print(f"\n  基因座列表:")
        for i, locus in enumerate(loci):
            instr_count = len(locus.get("instructions", []))
            print(f"    {i+1:3}. {locus.get('name', '?'):40} ({instr_count:3} 条指令)")
        
    except Exception as e:
        print(f"  ❌ 错误: 编译失败 - {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n[步骤2] 加载编译结果到运行时")
    print("-" * 70)
    
    runtime = EvoRuntime()
    
    for locus in loci:
        runtime.loaded_loci[locus["name"]] = locus
    
    print(f"  ✅ 已加载 {len(runtime.loaded_loci)} 个基因座")
    
    print("\n[步骤3] 执行关键基因座，测试功能")
    print("-" * 70)
    
    # 测试的关键基因座
    test_loci = [
        # 基础初始化
        "evoc.bootstrap.init",
        "evoc.core.memory_copy",
        "evoc.core.memory_compare",
        "evoc.core.string_length",
        
        # 词法分析
        "evoc.lexer.init",
        "evoc.lexer.advance",
        "evoc.lexer.peek",
        "evoc.lexer.tokenize",
        "evoc.lexer.full_pass",
        
        # 语法分析
        "evoc.parser.init",
        "evoc.parser.current_token",
        "evoc.parser.advance",
        "evoc.parser.parse_evolang",
        "evoc.parser.parse_locus",
        "evoc.parser.full_pass",
        
        # 代码生成
        "evoc.codegen.init",
        "evoc.codegen.emit_header",
        "evoc.codegen.encode_opcode",
        "evoc.codegen.encode_operand",
        "evoc.codegen.emit_instruction",
        "evoc.codegen.full_pass",
        
        # 虚拟机
        "evoc.vm.init",
        "evoc.vm.load_program",
        "evoc.vm.decode_instruction",
        "evoc.vm.step",
        "evoc.vm.run",
        
        # 标准库
        "evoc.stdlib.string.length",
        "evoc.stdlib.string.compare",
        "evoc.stdlib.string.concat",
        "evoc.stdlib.math.add",
        "evoc.stdlib.math.sub",
        "evoc.stdlib.math.mul",
        "evoc.stdlib.math.div",
    ]
    
    success_count = 0
    fail_count = 0
    results = []
    
    for locus_name in test_loci:
        if locus_name in runtime.loaded_loci:
            print(f"\n  执行: {locus_name}")
            try:
                result = runtime.execute_locus(locus_name, max_cycles=1000)
                state = result.get('state')
                cycles = result.get('cycle_count')
                
                if state == 'HALTED':
                    print(f"    ✅ 状态: {state}, 周期数: {cycles}")
                    success_count += 1
                    results.append((locus_name, True, cycles))
                else:
                    print(f"    ⚠️  状态: {state}, 周期数: {cycles}")
                    # 非HALTED状态也记录，但不算失败
                    results.append((locus_name, False, cycles))
                    
            except Exception as e:
                print(f"    ❌ 错误: {e}")
                fail_count += 1
                results.append((locus_name, False, 0))
        else:
            print(f"\n  ⚠️  基因座未找到: {locus_name}")
            results.append((locus_name, False, -1))
    
    print("\n" + "=" * 70)
    print("执行结果总结")
    print("=" * 70)
    print(f"\n  成功执行: {success_count} 个")
    print(f"  失败/未找到: {fail_count} 个")
    print(f"  总计测试: {len(test_loci)} 个")
    
    # 详细结果
    print(f"\n  详细执行结果:")
    for name, success, cycles in results:
        status = "✅" if success else ("❌" if cycles == 0 else "⚠️")
        cycle_str = f"({cycles} 周期)" if cycles >= 0 else "(未找到)"
        print(f"    {status} {name:40} {cycle_str}")
    
    print("\n[步骤4] 尝试编译一个简单的测试程序")
    print("-" * 70)
    
    # 简单的测试程序
    test_program = '''@evolang "3.0"

@locus test.simple {
    mut_rate   = 0.01
    fitness    = min_latency
    env_target = ["linux-6.x"]

    卦序: {
        ䷂ ALLOC R0, 0x10
        ䷍ ABUNDANCE R0, 0x05
        ䷝ ILLUMINATE R0
        ䷾ SYNC
    }
}
'''
    
    print(f"\n  测试程序:")
    for line in test_program.strip().split('\n'):
        print(f"    {line}")
    
    print(f"\n  使用Python编译器编译测试程序...")
    try:
        test_result = compiler.compile(test_program, output_format="dict")
        test_loci = test_result.get("loci", [])
        print(f"  ✅ Python编译器: 成功编译 {len(test_loci)} 个基因座")
        
        for locus in test_loci:
            print(f"    - {locus.get('name')}: {len(locus.get('instructions', []))} 条指令")
            
    except Exception as e:
        print(f"  ❌ Python编译器错误: {e}")
    
    print(f"\n  尝试使用EvomorphBackend编译测试程序...")
    try:
        from evomorph.bootstrap import EvomorphBackend
        backend = EvomorphBackend()
        
        print(f"\n  后端状态:")
        status = backend.get_status()
        print(f"    - 使用Evomorph: {status.get('use_evomorph')}")
        print(f"    - 可用模块: {status.get('available_modules', [])}")
        
        if status.get('use_evomorph') and status.get('available_modules'):
            print(f"\n  使用Evomorph后端编译...")
            result = backend.compile_source(test_program, output_format="dict")
            if "error" in result:
                print(f"    ❌ 错误: {result['error']}")
            else:
                loci = result.get("loci", [])
                print(f"    ✅ 成功编译 {len(loci)} 个基因座")
        else:
            print(f"\n  ⚠️  Evomorph后端模块未完全加载，使用Python实现")
            
    except Exception as e:
        print(f"  ❌ 后端错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("自举测试总结")
    print("=" * 70)
    
    print(f"""
当前状态:
1. ✅ Python编译器（第0代）: 完全可用，可以编译.evo文件
2. ⚠️  易衍语言编译器框架（第1代）: 已定义，但实现需要验证
3. ❓ 完全自举: 需要第1代编译器能够实际执行编译任务

关键发现:
- full_self_bootstrap.evo 定义了 {len(loci)} 个基因座
- 这些基因座涵盖了编译器的所有组件（词法、语法、代码生成、虚拟机等）
- 但这些实现目前是"骨架"形式，需要验证是否完整可执行

下一步建议:
1. 分析每个关键基因座的指令序列完整性
2. 补充或完善不完整的实现
3. 确保第1代编译器可以实际执行编译任务
4. 然后才能实现完全自举
""")
    
    return True


def analyze_locus_implementation():
    """分析基因座实现的完整性"""
    print("\n" + "=" * 70)
    print("分析基因座实现完整性")
    print("=" * 70)
    
    from evomorph.compiler import EvocCompiler
    
    compiler = EvocCompiler()
    
    with open(BOOTSTRAP_FILE, "r", encoding="utf-8") as f:
        source = f.read()
    
    result = compiler.compile(source, output_format="dict")
    loci = result.get("loci", [])
    
    print(f"\n  分析 {len(loci)} 个基因座...")
    
    # 按类别分组
    categories = {
        "bootstrap": [],
        "core": [],
        "lexer": [],
        "parser": [],
        "codegen": [],
        "vm": [],
        "stdlib": [],
        "evolution": [],
        "cli": [],
        "other": []
    }
    
    for locus in loci:
        name = locus.get("name", "")
        instr_count = len(locus.get("instructions", []))
        
        # 分类
        if "bootstrap" in name:
            categories["bootstrap"].append((name, instr_count))
        elif "core" in name:
            categories["core"].append((name, instr_count))
        elif "lexer" in name:
            categories["lexer"].append((name, instr_count))
        elif "parser" in name:
            categories["parser"].append((name, instr_count))
        elif "codegen" in name:
            categories["codegen"].append((name, instr_count))
        elif "vm" in name:
            categories["vm"].append((name, instr_count))
        elif "stdlib" in name:
            categories["stdlib"].append((name, instr_count))
        elif "evolution" in name:
            categories["evolution"].append((name, instr_count))
        elif "cli" in name:
            categories["cli"].append((name, instr_count))
        else:
            categories["other"].append((name, instr_count))
    
    # 打印分类结果
    for cat_name, items in categories.items():
        if items:
            total_instr = sum(count for _, count in items)
            print(f"\n  [{cat_name.upper()}] ({len(items)} 个基因座, {total_instr} 条指令)")
            
            # 按指令数量排序
            items_sorted = sorted(items, key=lambda x: x[1], reverse=True)
            
            for name, count in items_sorted[:10]:  # 只显示前10个
                status = "✅" if count > 5 else "⚠️" if count > 0 else "❌"
                print(f"    {status} {name:40} ({count:3} 条指令)")
            
            if len(items_sorted) > 10:
                print(f"    ... 还有 {len(items_sorted) - 10} 个")
    
    # 找出指令数量为0或很少的基因座
    print(f"\n  [警告] 指令数量较少的基因座 (< 3条指令):")
    warning_count = 0
    for locus in loci:
        name = locus.get("name", "")
        instr_count = len(locus.get("instructions", []))
        if instr_count < 3:
            warning_count += 1
            print(f"    ❌ {name:40} ({instr_count} 条指令)")
    
    if warning_count == 0:
        print(f"    ✅ 所有基因座都有合理数量的指令")
    
    print(f"\n  完整性分析总结:")
    print(f"    - 总基因座数: {len(loci)}")
    print(f"    - 需要注意的基因座: {warning_count}")
    
    return loci


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("易衍·Evomorph 完全自举分析")
    print("道枢自举：编译器用自身之语言书写自身")
    print("=" * 70)
    
    # 分析实现完整性
    loci = analyze_locus_implementation()
    
    # 执行测试
    test_compile_and_execute()
    
    print("\n" + "=" * 70)
    print("分析完成")
    print("=" * 70)
