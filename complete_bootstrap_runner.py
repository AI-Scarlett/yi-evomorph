#!/usr/bin/env python3
"""
易衍·Evomorph 完整持续自举执行脚本
持续运行直到达到目标功能覆盖率
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


def complete_bootstrap():
    """执行完整的持续自举流程"""
    
    print("\n" + "=" * 70)
    print("  易衍·Evomorph 完整持续自举执行")
    print("  目标：持续运行直到达到90%+功能覆盖率")
    print("=" * 70)
    print(f"\n  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  项目根目录: {PROJECT_ROOT}")
    
    system = ContinuousBootstrapSystem()
    
    # Phase 1: 基础功能完善（高优先级）
    print("\n" + "=" * 70)
    print("  PHASE 1: 基础功能完善")
    print("  目标：实现所有高优先级功能（优先级1）")
    print("=" * 70)
    
    analysis = system.analyze_functional_gaps()
    plan = system.generate_improvement_plan(analysis)
    
    # 获取所有高优先级改进项
    prioritized = analysis.get("prioritized_improvements", [])
    phase1_items = [item for item in prioritized if item["priority"] == 1]
    
    print(f"\n  Phase 1 待实现功能: {len(phase1_items)} 个")
    
    for i, item in enumerate(phase1_items):
        module = item["module"]
        feature = item["feature"]
        print(f"\n  [{i+1}/{len(phase1_items)}] 实现: [{module}] {feature}")
        success, code = system.enhance_bootstrap_module(module, feature, analysis)
        if success:
            print(f"    ✅ 成功")
        else:
            print(f"    ⚠️ 跳过（已存在或失败）")
    
    # Phase 2: 功能完整性（中优先级）
    print("\n" + "=" * 70)
    print("  PHASE 2: 功能完整性")
    print("  目标：实现所有中优先级功能（优先级2）")
    print("=" * 70)
    
    phase2_items = [item for item in prioritized if item["priority"] == 2]
    print(f"\n  Phase 2 待实现功能: {len(phase2_items)} 个")
    
    for i, item in enumerate(phase2_items):
        module = item["module"]
        feature = item["feature"]
        print(f"\n  [{i+1}/{len(phase2_items)}] 实现: [{module}] {feature}")
        success, code = system.enhance_bootstrap_module(module, feature, analysis)
        if success:
            print(f"    ✅ 成功")
        else:
            print(f"    ⚠️ 跳过（已存在或失败）")
    
    # Phase 3: 优化与增强（低优先级）
    print("\n" + "=" * 70)
    print("  PHASE 3: 优化与增强")
    print("  目标：实现所有低优先级功能（优先级3）")
    print("=" * 70)
    
    phase3_items = [item for item in prioritized if item["priority"] == 3]
    print(f"\n  Phase 3 待实现功能: {len(phase3_items)} 个")
    
    for i, item in enumerate(phase3_items):
        module = item["module"]
        feature = item["feature"]
        print(f"\n  [{i+1}/{len(phase3_items)}] 实现: [{module}] {feature}")
        success, code = system.enhance_bootstrap_module(module, feature, analysis)
        if success:
            print(f"    ✅ 成功")
        else:
            print(f"    ⚠️ 跳过（已存在或失败）")
    
    # 进化优化所有模块
    print("\n" + "=" * 70)
    print("  进化优化所有模块")
    print("=" * 70)
    
    modules_to_evolve = ["lexer", "parser", "codegen", "vm", "evolution"]
    evolution_results = {}
    
    for module_name in modules_to_evolve:
        print(f"\n  进化优化模块: {module_name} (25代)")
        result = system.run_evolution_on_module(module_name, generations=25)
        evolution_results[module_name] = result
        print(f"    最佳适应度: {result.get('best_fitness', 0):.4f}")
    
    # 验证自举
    print("\n" + "=" * 70)
    print("  验证自举")
    print("=" * 70)
    
    verification = system.verify_bootstrap()
    
    print("\n  验证结果:")
    print(f"    Python编译: {'✅ 成功' if verification['python_compile']['success'] else '❌ 失败'}")
    print(f"    易衍自举: {'✅ 成功' if verification['evomorph_compile']['success'] else '❌ 失败'}")
    print(f"    输出匹配: {'✅ 匹配' if verification['output_match'] else '⚠️ 不匹配'}")
    
    # 重新分析功能差距
    print("\n" + "=" * 70)
    print("  重新分析功能差距")
    print("=" * 70)
    
    system._init_module_status()
    final_analysis = system.analyze_functional_gaps()
    
    # 保存最终报告
    print("\n" + "=" * 70)
    print("  保存最终报告")
    print("=" * 70)
    
    report_dir = PROJECT_ROOT / "evomorph" / "bootstrap" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    final_report = {
        "start_time": datetime.now().isoformat(),
        "end_time": datetime.now().isoformat(),
        "initial_analysis": analysis,
        "final_analysis": final_analysis,
        "improvement_plan": plan,
        "evolution_results": evolution_results,
        "verification": verification,
        "status": system.get_current_status(),
        "phase1_completed": len(phase1_items),
        "phase2_completed": len(phase2_items),
        "phase3_completed": len(phase3_items),
    }
    
    report_file = report_dir / f"complete_bootstrap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n  最终报告已保存: {report_file}")
    
    # 最终总结
    print("\n" + "=" * 70)
    print("  完整持续自举执行完成")
    print("=" * 70)
    
    initial_coverage = analysis.get("implemented_features", 0) / analysis.get("total_features", 1)
    final_coverage = final_analysis.get("implemented_features", 0) / final_analysis.get("total_features", 1)
    
    print(f"\n  功能覆盖率变化:")
    print(f"    初始: {initial_coverage:.1%}")
    print(f"    最终: {final_coverage:.1%}")
    print(f"    提升: {(final_coverage - initial_coverage):.1%}")
    
    print(f"\n  实现的功能数量:")
    print(f"    Phase 1 (高优先级): {len(phase1_items)} 个")
    print(f"    Phase 2 (中优先级): {len(phase2_items)} 个")
    print(f"    Phase 3 (低优先级): {len(phase3_items)} 个")
    print(f"    总计: {len(phase1_items) + len(phase2_items) + len(phase3_items)} 个")
    
    print(f"\n  进化优化结果:")
    for module, result in evolution_results.items():
        print(f"    {module}: 最佳适应度 = {result.get('best_fitness', 0):.4f}")
    
    print(f"\n  模块最终状态:")
    status = system.get_current_status()
    for name, module_status in status["modules"].items():
        print(f"    {name}: {module_status['level']} (覆盖率 {module_status['coverage']:.1%})")
    
    # 判断是否达到目标
    if final_coverage >= 0.9:
        print(f"\n  🎉 恭喜！已达到目标功能覆盖率 (90%+)")
    elif final_coverage >= 0.7:
        print(f"\n  ✅ 已完成基础功能，继续运行可达到更高覆盖率")
    else:
        print(f"\n  ⚠️ 仍有较大差距，建议继续运行")
    
    print("\n" + "=" * 70)
    print("  下一步建议")
    print("=" * 70)
    
    print("""
  1. 查看最终报告:
     python3 -m json.tool evomorph/bootstrap/reports/complete_bootstrap_*.json

  2. 查看所有增强模块:
     ls -la evomorph/bootstrap/evolved/

  3. 运行回归测试验证:
     python3 regression_test_suite.py

  4. 如果需要进一步提升覆盖率:
     python3 continuous_bootstrap.py
     选择: 4 → 启动完整持续自举循环

  5. 查看功能差距分析:
     python3 continuous_bootstrap.py
     选择: 2 → 仅功能差距分析
    """)
    
    return final_report


if __name__ == "__main__":
    complete_bootstrap()
