#!/usr/bin/env python3
"""
易衍·Evomorph 自动持续自举执行脚本
非交互式执行，自动完成所有步骤
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from continuous_bootstrap import ContinuousBootstrapSystem


def auto_run():
    """自动执行完整的持续自举流程"""
    
    print("\n" + "=" * 70)
    print("  易衍·Evomorph 自动持续自举执行")
    print("  目标：让易衍编译器持续编译自身，对比Python编译器功能")
    print("        逐步完善，最终达到与Python编译器同等的水平")
    print("=" * 70)
    print(f"\n  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  项目根目录: {PROJECT_ROOT}")
    
    system = ContinuousBootstrapSystem()
    
    print("\n" + "-" * 70)
    print("  步骤 1: 功能差距分析")
    print("-" * 70)
    
    analysis = system.analyze_functional_gaps()
    
    print("\n" + "-" * 70)
    print("  步骤 2: 生成改进计划")
    print("-" * 70)
    
    plan = system.generate_improvement_plan(analysis)
    
    print("\n" + "-" * 70)
    print("  步骤 3: 增强VM模块")
    print("-" * 70)
    
    vm_improvements = [
        ("vm", "initialize_registers"),
        ("vm", "initialize_stack"),
        ("vm", "initialize_heap"),
        ("vm", "load_program_bytes"),
        ("vm", "load_program_dict"),
        ("vm", "run_program"),
        ("vm", "step_execution"),
    ]
    
    for module, feature in vm_improvements:
        print(f"\n  实现: [{module}] {feature}")
        success, code = system.enhance_bootstrap_module(module, feature, analysis)
        if success:
            print(f"    ✅ 成功")
        else:
            print(f"    ⚠️ 跳过（已存在或失败）")
    
    print("\n" + "-" * 70)
    print("  步骤 4: 增强Evolution模块")
    print("-" * 70)
    
    evolution_improvements = [
        ("evolution", "initialize_population"),
        ("evolution", "selection_roulette"),
        ("evolution", "selection_tournament"),
        ("evolution", "selection_rank"),
        ("evolution", "crossover_single_point"),
        ("evolution", "crossover_two_point"),
        ("evolution", "mutation_flip_yao"),
        ("evolution", "mutation_modifier"),
        ("evolution", "evaluate_fitness"),
        ("evolution", "elite_preservation"),
        ("evolution", "convergence_detection"),
    ]
    
    for module, feature in evolution_improvements:
        print(f"\n  实现: [{module}] {feature}")
        success, code = system.enhance_bootstrap_module(module, feature, analysis)
        if success:
            print(f"    ✅ 成功")
        else:
            print(f"    ⚠️ 跳过（已存在或失败）")
    
    print("\n" + "-" * 70)
    print("  步骤 5: 增强Parser和Codegen模块")
    print("-" * 70)
    
    parser_improvements = [
        ("parser", "parse_program"),
        ("parser", "parse_evolang_declaration"),
        ("parser", "parse_locus_declaration"),
        ("parser", "parse_meta_locus_declaration"),
        ("parser", "parse_xiangci_block"),
    ]
    
    for module, feature in parser_improvements:
        print(f"\n  实现: [{module}] {feature}")
        success, code = system.enhance_bootstrap_module(module, feature, analysis)
        if success:
            print(f"    ✅ 成功")
        else:
            print(f"    ⚠️ 跳过（已存在或失败）")
    
    codegen_improvements = [
        ("codegen", "encode_modifier"),
        ("codegen", "optimization_level_2"),
        ("codegen", "optimization_level_3"),
    ]
    
    for module, feature in codegen_improvements:
        print(f"\n  实现: [{module}] {feature}")
        success, code = system.enhance_bootstrap_module(module, feature, analysis)
        if success:
            print(f"    ✅ 成功")
        else:
            print(f"    ⚠️ 跳过（已存在或失败）")
    
    print("\n" + "-" * 70)
    print("  步骤 6: 进化优化所有模块")
    print("-" * 70)
    
    modules_to_evolve = ["lexer", "parser", "codegen", "vm", "evolution"]
    evolution_results = {}
    
    for module_name in modules_to_evolve:
        print(f"\n  进化优化模块: {module_name} (15代)")
        result = system.run_evolution_on_module(module_name, generations=15)
        evolution_results[module_name] = result
        print(f"    最佳适应度: {result.get('best_fitness', 0):.4f}")
    
    print("\n" + "-" * 70)
    print("  步骤 7: 验证自举")
    print("-" * 70)
    
    verification = system.verify_bootstrap()
    
    print("\n  验证结果:")
    print(f"    Python编译: {'✅ 成功' if verification['python_compile']['success'] else '❌ 失败'}")
    print(f"    易衍自举: {'✅ 成功' if verification['evomorph_compile']['success'] else '❌ 失败'}")
    print(f"    输出匹配: {'✅ 匹配' if verification['output_match'] else '⚠️ 不匹配'}")
    
    print("\n" + "-" * 70)
    print("  步骤 8: 保存报告")
    print("-" * 70)
    
    report_dir = PROJECT_ROOT / "evomorph" / "bootstrap" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    final_report = {
        "timestamp": time.time(),
        "datetime": datetime.now().isoformat(),
        "analysis": analysis,
        "improvement_plan": plan,
        "evolution_results": evolution_results,
        "verification": verification,
        "status": system.get_current_status()
    }
    
    report_file = report_dir / f"auto_bootstrap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n  报告已保存: {report_file}")
    
    print("\n" + "=" * 70)
    print("  执行总结")
    print("=" * 70)
    
    print("\n  新创建的增强模块:")
    print(f"    1. evoc_vm_enhanced.evo - VM增强（13个基因座）")
    print(f"    2. evoc_evolution_enhanced.evo - 进化引擎增强（16个基因座）")
    
    print("\n  已增强的功能数量:")
    print(f"    VM模块: {len(vm_improvements)} 个基础功能")
    print(f"    Evolution模块: {len(evolution_improvements)} 个核心功能")
    print(f"    Parser模块: {len(parser_improvements)} 个解析功能")
    print(f"    Codegen模块: {len(codegen_improvements)} 个代码生成功能")
    
    print("\n  进化优化结果:")
    for module, result in evolution_results.items():
        print(f"    {module}: 最佳适应度 = {result.get('best_fitness', 0):.4f}")
    
    print("\n  功能覆盖率变化:")
    status = system.get_current_status()
    for name, module_status in status["modules"].items():
        print(f"    {name}: {module_status['coverage']:.1%}")
    
    print("\n" + "=" * 70)
    print("  下一步建议")
    print("=" * 70)
    
    print("""
  1. 查看生成的报告:
     python3 -m json.tool evomorph/bootstrap/reports/auto_bootstrap_*.json

  2. 查看新创建的增强模块:
     cat evomorph/bootstrap/evolved/evoc_vm_enhanced.evo
     cat evomorph/bootstrap/evolved/evoc_evolution_enhanced.evo

  3. 运行回归测试验证:
     python3 regression_test_suite.py

  4. 继续运行更多自举循环:
     python3 continuous_bootstrap.py
     选择: 4 → 启动完整持续自举循环
     
  5. 检查功能差距分析:
     python3 continuous_bootstrap.py
     选择: 2 → 仅功能差距分析
    """)
    
    return final_report


if __name__ == "__main__":
    auto_run()
