#!/usr/bin/env python3
"""
增强自举模块演示脚本

演示以下功能:
1. 第2代编译器接口
2. 进化优化功能
3. 一致性验证
4. 最小可信计算基
"""

import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from evomorph.bootstrap.enhanced_bootstrap import EnhancedBootstrap


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_compiler_generations():
    """演示各代编译器接口"""
    print_header("1. 第2代编译器接口演示")
    
    eb = EnhancedBootstrap()
    
    test_program = '''@evolang "3.0"

@xiangci {
    "演示程序：计算5+10=15"
}

@locus demo.addition {
    mut_rate   = 0.01
    cross_pool = "demo"
    fitness    = min_latency + min_size
    env_target = ["linux-6.x"]

    卦序: {
        ䷶ ABOUND R0, 5
        ䷶ ABOUND R1, 10
        ䷩ INCREASE R0, R1
        ䷋ HALT
    }
}
'''
    
    print("\n[1.1] 使用第0代编译器（Python实现）编译:")
    result_gen0 = eb.compile_with_gen0(test_program)
    print(f"    成功: {'是' if result_gen0.success else '否'}")
    print(f"    代次: {result_gen0.generation}")
    print(f"    基因座数量: {len(result_gen0.loci)}")
    if result_gen0.loci:
        for locus in result_gen0.loci:
            print(f"      - {locus['name']}: {len(locus.get('instructions', []))} 条指令")
    
    print("\n[1.2] 自动选择编译器代次编译:")
    result_auto = eb.compile(test_program, generation="auto")
    print(f"    成功: {'是' if result_auto.success else '否'}")
    print(f"    实际使用代次: {result_auto.generation}")
    
    print("\n[1.3] 批量编译示例:")
    print("    (可使用 compile_batch() 方法批量编译多个 .evo 文件)")
    
    return eb


def demo_evolution_optimization(eb):
    """演示进化优化功能"""
    print_header("2. 进化优化功能演示")
    
    print("\n[2.1] 可用的进化模式:")
    for mode, config in eb.evolution_configs.items():
        print(f"    - {mode}:")
        print(f"        种群大小: {config.population_size}")
        print(f"        最大代数: {config.max_generations}")
        print(f"        变异率: {config.mut_rate}")
        print(f"        选择方法: {config.selection_method.value}")
    
    test_locus = {
        "name": "demo.evolve_test",
        "mut_rate": 0.02,
        "env_targets": ["linux-6.x"],
        "instructions": [
            {"opcode": 13, "modifier": 0, "mnemonic": "ABOUND", "operands": [0, 5]},
            {"opcode": 13, "modifier": 0, "mnemonic": "ABOUND", "operands": [1, 10]},
            {"opcode": 49, "modifier": 0, "mnemonic": "INCREASE", "operands": [0, 1]},
            {"opcode": 56, "modifier": 0, "mnemonic": "HALT", "operands": []},
        ]
    }
    eb.runtime.loaded_loci["demo.evolve_test"] = test_locus
    
    print("\n[2.2] 快速进化模式演示 (10代):")
    report = eb.evolve_locus_enhanced("demo.evolve_test", mode="quick")
    print(f"    进化代数: {report.generations}")
    print(f"    初始适应度: {report.initial_fitness:.4f}")
    print(f"    最终适应度: {report.final_fitness:.4f}")
    print(f"    改进率: {report.improvement_rate:.2f}%")
    
    print("\n[2.3] 自定义进化配置示例:")
    print("    可使用 custom 模式，指定:")
    print("    - population_size: 种群大小")
    print("    - max_generations: 最大进化代数")
    print("    - mut_rate: 变异率")
    print("    - selection_method: 选择方法 (roulette/tournament/rank)")
    print("    - crossover_method: 交叉方法 (single_point/two_point/uniform)")
    print("    - use_adaptive_mutation: 是否使用自适应变异")
    
    return eb


def demo_consistency_verification(eb):
    """演示一致性验证功能"""
    print_header("3. 一致性验证演示")
    
    test_program = '''@evolang "3.0"

@locus verify.test {
    mut_rate   = 0.01
    fitness    = min_latency
    env_target = ["linux-6.x"]

    卦序: {
        ䷂ ALLOC R0, 0x20
        ䷍ ABUNDANCE R0, 0x42
        ䷾ SYNC
    }
}
'''
    
    print("\n[3.1] 验证第1代与第2代编译器输出一致性:")
    report = eb.verify_consistency(test_program, verbose=True)
    
    print(f"\n[3.2] 一致性验证结果:")
    print(f"    第1代编译成功: {'是' if report.gen1_result.success else '否'}")
    print(f"    第2代编译成功: {'是' if report.gen2_result.success else '否'}")
    print(f"    匹配率: {report.match_percentage:.1f}%")
    print(f"    完全一致: {'是' if report.is_consistent else '否'}")
    
    if report.differences:
        print(f"\n[3.3] 发现的差异 ({len(report.differences)} 个):")
        for diff in report.differences[:5]:
            print(f"    - {diff}")
        if len(report.differences) > 5:
            print(f"    ... 还有 {len(report.differences) - 5} 个差异")
    
    return eb


def demo_trusted_computing_base(eb):
    """演示最小可信计算基功能"""
    print_header("4. 最小可信计算基（TCB）演示")
    
    print("\n[4.1] TCB 状态检查:")
    status = eb.check_tcb_status()
    print(f"    C 虚拟机可用: {'是' if status.c_vm_available else '否'}")
    print(f"    C 虚拟机路径: {status.c_vm_path}")
    print(f"    汇编器可用: {'是' if status.assembler_available else '否'}")
    print(f"    可执行原始字节码: {'是' if status.can_execute_raw else '否'}")
    print(f"    完全独立运行: {'是' if status.is_fully_independent else '否'}")
    
    if status.bootstrap_test_result:
        print(f"\n[4.2] 自举测试结果:")
        print(f"    测试成功: {'是' if status.bootstrap_test_result.get('success') else '否'}")
        if status.bootstrap_test_result.get('output'):
            print(f"    测试输出: {status.bootstrap_test_result['output'][:100]}")
    
    print("\n[4.3] 编译 .evo 代码为 C 虚拟机可执行格式:")
    test_program = '''@evolang "3.0"

@locus tcb.demo {
    mut_rate   = 0.01
    fitness    = min_latency
    env_target = ["linux-6.x"]

    卦序: {
        ䷶ ABOUND R0, 1
        ䷶ ABOUND R1, 2
        ䷩ INCREASE R0, R1
        ䷶ ABOUND R2, 3
        ䷩ INCREASE R0, R2
        ䷋ HALT
    }
}
'''
    
    temp_asm = os.path.join(PROJECT_ROOT, "tests", "temp_tcb_demo.asm")
    
    result = eb.compile_for_tcb(test_program, temp_asm, verbose=False)
    
    if result["success"]:
        print(f"    编译成功!")
        print(f"    汇编文件: {result['asm_file']}")
        print(f"    使用代次: {result['generation']}")
        
        if os.path.exists(temp_asm):
            with open(temp_asm, 'r', encoding='utf-8') as f:
                asm_content = f.read()
            print(f"\n[4.4] 生成的汇编代码片段:")
            for line in asm_content.strip().split('\n')[:15]:
                print(f"    {line}")
            if len(asm_content.split('\n')) > 15:
                print(f"    ...")
            
            os.unlink(temp_asm)
            print(f"\n    临时文件已清理")
    else:
        print(f"    编译失败: {result.get('error', '未知错误')}")
    
    print("\n[4.5] 构建 TCB (编译 C 虚拟机):")
    print("    使用 build_tcb() 方法可以重新编译 C 虚拟机")
    print("    命令行: python -m evomorph.bootstrap.enhanced_bootstrap tcb build")
    
    return eb


def demo_system_status(eb):
    """演示系统状态查询"""
    print_header("5. 系统状态查询")
    
    status = eb.get_status()
    
    print("\n[5.1] 编译器代次状态:")
    for gen, info in status["generations"].items():
        print(f"    {gen}:")
        print(f"        可用: {'是' if info['available'] else '否'}")
        print(f"        描述: {info['description']}")
        if info.get("modules"):
            print(f"        模块数量: {len(info['modules'])}")
    
    print(f"\n[5.2] 已加载的基因座: {len(status['loaded_loci'])} 个")
    if status['loaded_loci']:
        for locus in status['loaded_loci'][:10]:
            print(f"    - {locus}")
        if len(status['loaded_loci']) > 10:
            print(f"    ... 还有 {len(status['loaded_loci']) - 10} 个")
    
    print(f"\n[5.3] 可用进化模式: {status['evolution_modes']}")
    
    return eb


def demo_command_line_usage():
    """演示命令行使用方法"""
    print_header("6. 命令行使用方法")
    
    print("""
增强自举模块提供了完整的命令行接口:

  查看帮助:
    python -m evomorph.bootstrap.enhanced_bootstrap --help

  编译代码:
    python -m evomorph.bootstrap.enhanced_bootstrap compile source.evo
    python -m evomorph.bootstrap.enhanced_bootstrap compile source.evo -g gen2 -o output.json -v

  进化优化:
    python -m evomorph.bootstrap.enhanced_bootstrap evolve locus.name
    python -m evomorph.bootstrap.enhanced_bootstrap evolve locus.name -m deep -g 100 -p 64

  一致性验证:
    python -m evomorph.bootstrap.enhanced_bootstrap verify file1.evo file2.evo -v

  最小可信计算基操作:
    python -m evomorph.bootstrap.enhanced_bootstrap tcb status -v
    python -m evomorph.bootstrap.enhanced_bootstrap tcb build -v
    python -m evomorph.bootstrap.enhanced_bootstrap tcb compile source.evo -o output.asm

  查看系统状态:
    python -m evomorph.bootstrap.enhanced_bootstrap status
""")


def main():
    """主演示函数"""
    print("\n" + "#" * 70)
    print("#  易衍·Evomorph 增强自举模块演示")
    print("#  =====================================")
    print("#")
    print("#  功能概述:")
    print("#    1. 第2代编译器接口 - 使用进化后的编译器编译更多 .evo 代码")
    print("#    2. 进化优化 - 支持调整参数、增加进化代数")
    print("#    3. 一致性验证 - 验证第2代与第1代输出是否一致")
    print("#    4. 最小可信计算基 - 结合 C 虚拟机实现独立自举")
    print("#" * 70)
    
    eb = demo_compiler_generations()
    eb = demo_evolution_optimization(eb)
    eb = demo_consistency_verification(eb)
    eb = demo_trusted_computing_base(eb)
    eb = demo_system_status(eb)
    demo_command_line_usage()
    
    print("\n" + "=" * 70)
    print("演示完成!")
    print("=" * 70)
    print("""
下一步操作建议:
  1. 使用第2代编译器编译更多 .evo 代码:
     eb.compile("your_code.evo", generation="gen2")

  2. 深度进化优化:
     eb.evolve_locus_enhanced("locus.name", mode="deep")
     或自定义配置:
     eb.evolve_locus_enhanced("locus.name", mode="custom", 
         custom_config={"max_generations": 200, "population_size": 64})

  3. 验证编译器一致性:
     eb.verify_consistency("test_file.evo", verbose=True)

  4. 使用最小可信计算基:
     eb.build_tcb(verbose=True)  # 编译 C 虚拟机
     eb.compile_for_tcb("source.evo", "output.asm", "output.raw")
""")


if __name__ == "__main__":
    main()
