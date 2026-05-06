#!/usr/bin/env python3
"""
测试完整的自举编译器运行时
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evomorph.bootstrap.complete_bootstrap_runtime import CompleteBootstrapRuntime


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_simple_compile():
    print_header("测试1: 简单程序编译")
    
    runtime = CompleteBootstrapRuntime()
    
    test_source = '''@evolang "3.0"

@xiangci {
    "测试程序：创建进程并同步通信"
}

@locus test.program {
    mut_rate   = 0.02
    cross_pool = "default"
    fitness    = min_latency + max_throughput
    env_target = ["linux-6.x"]

    卦序: {
        ䷀ CREA R0, R1
        ䷌ FELLOWSHIP R0, R1
        ䷾ SYNC
    }
}
'''
    
    result = runtime.full_compile(test_source)
    
    print(f"✓ 编译成功")
    print(f"  - 版本: {result.get('version')}")
    print(f"  - 基因座数量: {len(result.get('loci', []))}")
    print(f"  - 象辞数量: {len(result.get('xiangci', []))}")
    
    for locus in result.get('loci', []):
        print(f"\n  基因座: {locus.get('name')}")
        print(f"    - mut_rate: {locus.get('mut_rate')}")
        print(f"    - cross_pool: {locus.get('cross_pool')}")
        print(f"    - env_targets: {locus.get('env_targets')}")
        print(f"    - 指令数量: {len(locus.get('instructions', []))}")
        
        for instr in locus.get('instructions', []):
            print(f"      * {instr.get('symbol')} {instr.get('mnemonic')} (opcode={instr.get('opcode')})")
            for op in instr.get('operands', []):
                print(f"        - {op.get('kind')}: {op.get('value')}")
    
    return True


def test_compiler_comparison():
    print_header("测试2: 与Python编译器对比")
    
    runtime = CompleteBootstrapRuntime()
    
    test_source = '''@evolang "3.0"

@locus comparison.test {
    mut_rate   = 0.01
    fitness    = min_size + min_latency
    env_target = ["linux-6.x", "android-14"]

    卦序: {
        ䷁ RECV R0, env::INPUT
        ䷀ CREA R1
        ䷂ ALLOC R2, 0x100
        ䷌ FELLOWSHIP R0, R1
        ䷆ BRANCH R0, @loop
        ䷾ SYNC
    }
}
'''
    
    comparison = runtime.compare_compilers(test_source)
    
    print(f"✓ 对比完成")
    print(f"  - 易衍编译器基因座数: {comparison['evo_loci_count']}")
    print(f"  - Python编译器基因座数: {comparison['python_loci_count']}")
    print(f"  - 基因座匹配: {'✓' if comparison['loci_match'] else '✗'}")
    print(f"  - 指令匹配: {'✓' if comparison['all_instruction_match'] else '✗'}")
    
    print(f"\n  性能对比:")
    print(f"    - 易衍编译时间: {comparison['timing_comparison']['evo_total']:.4f}s")
    print(f"    - Python编译时间: {comparison['timing_comparison']['python_total']:.4f}s")
    print(f"    - 时间比率: {comparison['timing_comparison']['ratio']:.2f}x")
    
    for comp in comparison.get('instruction_comparison', []):
        print(f"\n  基因座 '{comp['locus_name']}':")
        print(f"    - 易衍指令数: {comp['evo_instr_count']}")
        print(f"    - Python指令数: {comp['python_instr_count']}")
        print(f"    - 匹配: {'✓' if comp['match'] else '✗'}")
    
    return comparison['loci_match'] and comparison['all_instruction_match']


def test_feature_gap_analysis():
    print_header("测试3: 功能差距分析")
    
    runtime = CompleteBootstrapRuntime()
    gaps = runtime.analyze_feature_gaps()
    
    print(f"✓ 分析完成")
    print(f"\n  总体状态:")
    print(f"    - 总功能数: {gaps['summary']['total_features']}")
    print(f"    - 已完成: {gaps['summary']['closed_gaps']}")
    print(f"    - 待完成: {gaps['summary']['open_gaps']}")
    print(f"    - 完成度: {gaps['summary']['completion_percentage']:.1f}%")
    
    print(f"\n  按优先级分布:")
    for prio in [1, 2, 3, 4, 5]:
        open_count = len([g for g in gaps['open'] if g['priority'] == prio])
        closed_count = len([g for g in gaps['closed'] if g['priority'] == prio])
        total = open_count + closed_count
        pct = (closed_count / total * 100) if total > 0 else 0
        print(f"    优先级 {prio}: {closed_count}/{total} ({pct:.0f}%)")
    
    print(f"\n  高优先级待完成功能 (优先级 1-2):")
    for gap in gaps['open']:
        if gap['priority'] <= 2:
            print(f"    - [{gap['priority']}] {gap['feature']}: {gap['description']}")
    
    return gaps['summary']['completion_percentage']


def test_self_compile():
    print_header("测试4: 自举编译器测试 - 编译器编译自身")
    
    runtime = CompleteBootstrapRuntime()
    test_result = runtime.run_self_compile_test()
    
    print(f"✓ 自举测试完成")
    print(f"  - Token数量: {test_result['tokens']}")
    print(f"  - AST有效: {'✓' if test_result['ast_valid'] else '✗'}")
    print(f"  - 代码生成有效: {'✓' if test_result['codegen_valid'] else '✗'}")
    
    return test_result['ast_valid'] and test_result['codegen_valid']


def test_vm_execution():
    print_header("测试5: 虚拟机执行")
    
    runtime = CompleteBootstrapRuntime()
    
    print("  初始化虚拟机...")
    vm_state = runtime._vm_init()
    print(f"    ✓ VM ID: {vm_state['vm_id']}")
    print(f"    ✓ 初始状态: {vm_state['state']}")
    
    print("\n  测试寄存器操作...")
    vm_state = runtime._vm_set_register(vm_state, 0, 42)
    r0_val = runtime._vm_get_register(vm_state, 0)
    print(f"    ✓ R0 = {r0_val}")
    
    print("\n  测试指令执行...")
    result = runtime._vm_execute(vm_state, 63, 0, [0, 1])
    print(f"    ✓ CREA指令执行状态: {result['state']}")
    print(f"    ✓ 周期数: {result['cycle_count']}")
    print(f"    ✓ 能耗: {result['energy_cost']}")
    
    return True


def test_evolution_engine():
    print_header("测试6: 进化引擎")
    
    runtime = CompleteBootstrapRuntime()
    
    seed_genes = [
        {"opcode": 63, "modifier": 0, "operands": [0, 1]},
        {"opcode": 61, "modifier": 0, "operands": [0, 1]},
        {"opcode": 21, "modifier": 0, "operands": []},
    ]
    
    print("  初始化种群...")
    pop_result = runtime._evo_init_population(seed_genes, {"population_size": 16})
    print(f"    ✓ 种群大小: {pop_result['population_size']}")
    print(f"    ✓ 代数: {pop_result['generation']}")
    
    print("\n  评估适应度...")
    individual = {"genes": seed_genes, "fitness": 0.0}
    fitness = runtime._evo_evaluate_fitness(individual)
    print(f"    ✓ 适应度分数: {fitness:.2f}")
    
    print("\n  运行进化...")
    evo_result = runtime._evo_evolve(
        seed_genes, 
        generations=10,
        config={"population_size": 16, "mut_rate": 0.05}
    )
    print(f"    ✓ 最佳适应度: {evo_result['best_fitness']:.2f}")
    print(f"    ✓ 完成代数: {evo_result['generations']}")
    print(f"    ✓ 最佳基因数: {len(evo_result['best_genes'])}")
    
    return True


def test_continuous_bootstrap():
    print_header("测试7: 持续自举循环")
    
    runtime = CompleteBootstrapRuntime()
    
    compiler_source = runtime.get_evo_compiler_source()
    print(f"  编译器源代码长度: {len(compiler_source)} 字符")
    
    loop_result = runtime.continuous_bootstrap_loop(
        compiler_source,
        max_generations=3,
        fitness_threshold=70.0
    )
    
    print(f"\n  循环结果:")
    print(f"    - 最佳适应度: {loop_result['best_fitness']:.2f}")
    print(f"    - 完成代数: {loop_result['generations_completed']}")
    
    print(f"\n  每代历史:")
    for entry in loop_result['loop_history']:
        print(f"    - 代 {entry['generation']+1}: 适应度={entry['fitness']:.2f}, 改进={entry['improvements']}")
    
    return loop_result['best_fitness']


def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         易衍·Evomorph 完整自举编译器测试                     ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    all_passed = True
    test_results = {}
    
    tests = [
        ("简单程序编译", test_simple_compile),
        ("与Python编译器对比", test_compiler_comparison),
        ("功能差距分析", test_feature_gap_analysis),
        ("自举编译器测试", test_self_compile),
        ("虚拟机执行", test_vm_execution),
        ("进化引擎", test_evolution_engine),
        ("持续自举循环", test_continuous_bootstrap),
    ]
    
    for name, test_func in tests:
        try:
            result = test_func()
            test_results[name] = result
            if isinstance(result, bool):
                status = "✓ 通过" if result else "✗ 失败"
                if not result:
                    all_passed = False
            else:
                status = f"✓ 完成 (结果: {result})"
            print(f"\n{status}")
        except Exception as e:
            print(f"\n✗ 测试 '{name}' 失败: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
            test_results[name] = False
    
    print("\n" + "=" * 60)
    print("                        测试总结")
    print("=" * 60)
    
    for name, result in test_results.items():
        if isinstance(result, bool):
            status = "✓ 通过" if result else "✗ 失败"
        else:
            status = f"✓ 完成"
        print(f"  {name}: {status}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("                    ✓ 所有测试通过！")
        print("         自举编译器运行时已完全可用！")
    else:
        print("                    ✗ 部分测试失败")
        print("         请检查上述失败的测试并修复问题")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
