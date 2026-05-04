#!/usr/bin/env python3
"""
测试Evomorph进化引擎重构
验证创建的.evo文件是否可以正确编译
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evomorph.compiler import EvocCompiler
from evomorph.evolution.engine import (
    EvolutionEngine, EvolutionConfig, GeneInstruction, Individual,
)


def compile_evo_file(filepath):
    """编译.evo文件"""
    print(f"\n{'='*60}")
    print(f"编译文件: {filepath}")
    print('='*60)
    
    compiler = EvocCompiler()
    result = compiler.compile_file(filepath, output_format="dict")
    
    if result.get("error"):
        print(f"\n❌ 编译错误:")
        for err in result.get("errors", []):
            print(f"  - 行{err.get('line')}: {err.get('message')}")
            if err.get('suggestion'):
                print(f"    建议: {err.get('suggestion')}")
        return None
    
    print(f"\n✅ 编译成功!")
    
    if "loci" in result:
        print(f"\n📦 基因座数量: {len(result['loci'])}")
        for locus in result['loci']:
            print(f"\n  🔹 基因座: {locus.get('name', 'unnamed')}")
            print(f"     - 变异率: {locus.get('mut_rate', 'N/A')}")
            print(f"     - 交叉池: {locus.get('cross_pool', 'N/A')}")
            print(f"     - 目标平台: {locus.get('env_targets', [])}")
            print(f"     - 指令数量: {len(locus.get('instructions', []))}")
    
    if "meta_loci" in result:
        print(f"\n🔬 元基因座数量: {len(result['meta_loci'])}")
        for meta in result['meta_loci']:
            print(f"\n  🔸 元基因座: {meta.get('name', 'unnamed')}")
            print(f"     - 变异率: {meta.get('mut_rate', 'N/A')}")
            print(f"     - 指令数量: {len(meta.get('instructions', []))}")
    
    if "xiangci" in result:
        print(f"\n📝 象辞数量: {len(result['xiangci'])}")
    
    return result


def test_integration_with_evolution_engine(compiled_result):
    """测试与现有进化引擎的集成"""
    print(f"\n{'='*60}")
    print("测试与现有进化引擎的集成")
    print('='*60)
    
    if not compiled_result or "loci" not in compiled_result:
        print("❌ 没有可测试的基因座")
        return
    
    locus = compiled_result['loci'][0]
    print(f"\n使用基因座: {locus.get('name', 'unnamed')}")
    
    seed_genes = []
    for instr in locus.get("instructions", []):
        if "opcode" in instr:
            gene = GeneInstruction(
                opcode=instr["opcode"],
                modifier=instr.get("modifier", 0),
            )
            seed_genes.append(gene)
    
    if not seed_genes:
        print("⚠️  没有找到可执行的指令，使用默认测试基因")
        seed_genes = [
            GeneInstruction(opcode=63),
            GeneInstruction(opcode=21),
        ]
    
    print(f"\n种子基因数量: {len(seed_genes)}")
    for i, g in enumerate(seed_genes):
        print(f"  {i}: opcode={g.opcode} (0b{g.opcode:06b})")
    
    config = EvolutionConfig(
        population_size=16,
        max_generations=10,
        mut_rate=0.05,
    )
    
    engine = EvolutionEngine(config=config)
    engine.initialize_population(seed_genes)
    
    print(f"\n🚀 开始进化...")
    history = []
    
    def callback(stats):
        history.append(stats)
        print(f"  世代 {stats['generation']}: 最佳适应度={stats['best_fitness']:.2f}, 多样性={stats['diversity']:.2f}")
    
    best = engine.evolve(callback=callback)
    
    print(f"\n✅ 进化完成!")
    print(f"\n📊 进化统计:")
    print(f"  - 总世代数: {len(history)}")
    print(f"  - 最终最佳适应度: {best.fitness:.2f}")
    print(f"  - 最佳个体来源: {best.origin}")
    print(f"  - 种群多样性变化: {history[0]['diversity']:.2f} -> {history[-1]['diversity']:.2f}")
    
    print(f"\n🧬 最佳个体基因:")
    for i, g in enumerate(best.genes):
        print(f"  {i}: opcode={g.opcode} (0b{g.opcode:06b}), modifier={g.modifier}")
    
    return True


def main():
    """主测试函数"""
    print("="*60)
    print("易衍·Evomorph 进化引擎重构测试")
    print("="*60)
    
    evolution_core_path = os.path.join(
        os.path.dirname(__file__),
        "evomorph", "evolution", "evolution_core.evo"
    )
    
    evolution_meta_path = os.path.join(
        os.path.dirname(__file__),
        "evomorph", "evolution", "evolution_meta.evo"
    )
    
    result1 = compile_evo_file(evolution_core_path)
    result2 = compile_evo_file(evolution_meta_path)
    
    if result1:
        test_integration_with_evolution_engine(result1)
    
    print(f"\n{'='*60}")
    print("测试完成!")
    print('='*60)
    print(f"\n📁 创建的文件:")
    print(f"  - evomorph/evolution/evolution_core.evo")
    print(f"  - evomorph/evolution/evolution_meta.evo")
    print(f"\n这些文件包含:")
    print(f"  ✅ 核心进化算法基因座")
    print(f"     - 种群初始化")
    print(f"     - 选择算法（轮盘赌、锦标赛、排名）")
    print(f"     - 交叉算法（单点、两点、均匀）")
    print(f"     - 变异算法（爻位翻转、修饰符变异）")
    print(f"     - 适应度评估")
    print(f"     - 收敛检测")
    print(f"     - 进化控制")
    print(f"\n  ✅ 元基因座（自进化策略）")
    print(f"     - 变异算子进化")
    print(f"     - 交叉策略进化")
    print(f"     - 选择策略进化")
    print(f"     - 适应度评估进化")
    print(f"     - 种群管理进化")
    print(f"     - 收敛检测进化")
    print(f"     - 象辞翻译策略")
    print(f"     - 平台自适应")
    print(f"     - 优化策略")
    print(f"     - 元进化控制器")


if __name__ == "__main__":
    main()
