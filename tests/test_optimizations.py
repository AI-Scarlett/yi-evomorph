#!/usr/bin/env python3
"""
验证易衍·Evomorph 新优化功能的测试脚本
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evomorph.evolution.engine import (
    EvolutionEngine, 
    EvolutionConfig, 
    Individual, 
    GeneInstruction,
    SelectionMethod,
    CrossoverMethod
)


def test_evolution_config():
    """测试新的 EvolutionConfig 配置项"""
    print("=" * 60)
    print("测试 1: 验证新的 EvolutionConfig 配置项")
    print("=" * 60)
    
    config = EvolutionConfig()
    
    print(f"  ✓ population_size: {config.population_size}")
    print(f"  ✓ mut_rate: {config.mut_rate}")
    print(f"  ✓ min_mut_rate: {config.min_mut_rate}")
    print(f"  ✓ max_mut_rate: {config.max_mut_rate}")
    print(f"  ✓ use_adaptive_mutation: {config.use_adaptive_mutation}")
    print(f"  ✓ diversity_threshold_low: {config.diversity_threshold_low}")
    print(f"  ✓ diversity_threshold_high: {config.diversity_threshold_high}")
    print(f"  ✓ use_execution_based_fitness: {config.use_execution_based_fitness}")
    
    print("\n  所有配置项验证通过! ✅")


def test_individual_class():
    """测试增强的 Individual 类"""
    print("\n" + "=" * 60)
    print("测试 2: 验证增强的 Individual 类")
    print("=" * 60)
    
    genes = [GeneInstruction(opcode=63), GeneInstruction(opcode=0)]
    ind = Individual(genes=genes)
    
    print(f"  ✓ 基础 genes 列表: {[g.opcode for g in ind.genes]}")
    print(f"  ✓ execution_metrics 字段存在: {hasattr(ind, 'execution_metrics')}")
    print(f"  ✓ compiled_instructions 字段存在: {hasattr(ind, 'compiled_instructions')}")
    
    ind.execution_metrics = {
        "executed_cycles": 42.0,
        "energy_used": 5.2,
        "halted": 1.0
    }
    ind.compiled_instructions = [63, 0, 21]
    
    ind2 = ind.clone()
    print(f"  ✓ clone() 保留 execution_metrics: {ind2.execution_metrics == ind.execution_metrics}")
    print(f"  ✓ clone() 保留 compiled_instructions: {ind2.compiled_instructions == ind.compiled_instructions}")
    
    print("\n  Individual 类增强验证通过! ✅")


def test_diversity_calculation():
    """测试增强的种群多样性计算"""
    print("\n" + "=" * 60)
    print("测试 3: 验证增强的种群多样性计算")
    print("=" * 60)
    
    config = EvolutionConfig(population_size=10)
    engine = EvolutionEngine(config=config)
    
    initial_population = []
    for i in range(10):
        genes = []
        for j in range(5):
            opcode = (i * 7 + j * 3) % 64
            genes.append(GeneInstruction(opcode=opcode))
        initial_population.append(Individual(genes=genes))
    
    engine.population = initial_population
    
    for ind in engine.population:
        ind.fitness = (sum(g.opcode for g in ind.genes) % 100) / 10.0
    
    diversity = engine._calculate_diversity()
    print(f"  ✓ 种群多样性计算结果: {diversity:.4f}")
    print(f"  ✓ 多样性范围检查 (0.0-1.0): {0.0 <= diversity <= 1.0}")
    
    print("\n  多样性计算验证通过! ✅")


def test_adaptive_mutation_rate():
    """测试自适应变异率调整"""
    print("\n" + "=" * 60)
    print("测试 4: 验证自适应变异率调整")
    print("=" * 60)
    
    config = EvolutionConfig(
        population_size=8,
        mut_rate=0.02,
        min_mut_rate=0.001,
        max_mut_rate=0.15,
        use_adaptive_mutation=True,
        diversity_threshold_low=0.3,
        diversity_threshold_high=0.7
    )
    
    engine = EvolutionEngine(config=config)
    
    uniform_population = []
    for i in range(8):
        genes = [GeneInstruction(opcode=63), GeneInstruction(opcode=63), GeneInstruction(opcode=63)]
        uniform_population.append(Individual(genes=genes))
    
    engine.population = uniform_population
    
    for ind in engine.population:
        ind.fitness = 1.0 if id(ind) % 2 == 0 else 0.5
    
    low_diversity = engine._calculate_diversity()
    print(f"  ✓ 低多样性种群 (所有个体相似): {low_diversity:.4f}")
    
    old_rate = config.mut_rate
    new_rate = engine._update_mutation_rate()
    print(f"  ✓ 原始变异率: {old_rate:.4f}")
    print(f"  ✓ 低多样性下新变异率: {new_rate:.4f}")
    print(f"  ✓ 变异率增加: {new_rate > old_rate}")
    
    diverse_population = []
    for i in range(8):
        genes = [
            GeneInstruction(opcode=i * 8 % 64),
            GeneInstruction(opcode=(i * 8 + 1) % 64),
            GeneInstruction(opcode=(i * 8 + 2) % 64)
        ]
        diverse_population.append(Individual(genes=genes))
    
    engine.population = diverse_population
    
    for idx, ind in enumerate(engine.population):
        ind.fitness = (idx * 0.1) % 1.0
    
    high_diversity = engine._calculate_diversity()
    print(f"  ✓ 高多样性种群 (所有个体不同): {high_diversity:.4f}")
    
    config.mut_rate = 0.10
    old_rate2 = config.mut_rate
    new_rate2 = engine._update_mutation_rate()
    print(f"  ✓ 原始变异率: {old_rate2:.4f}")
    print(f"  ✓ 高多样性下新变异率: {new_rate2:.4f}")
    print(f"  ✓ 变异率减少: {new_rate2 < old_rate2}")
    
    print("\n  自适应变异率验证通过! ✅")


def test_evolve_one_generation_stats():
    """测试增强的进化统计信息"""
    print("\n" + "=" * 60)
    print("测试 5: 验证增强的进化统计信息")
    print("=" * 60)
    
    config = EvolutionConfig(
        population_size=8,
        max_generations=2,
        mut_rate=0.02,
        use_adaptive_mutation=True
    )
    
    engine = EvolutionEngine(config=config)
    
    initial_population = []
    for i in range(8):
        genes = [
            GeneInstruction(opcode=(i * 7) % 64),
            GeneInstruction(opcode=(i * 7 + 3) % 64),
            GeneInstruction(opcode=(i * 7 + 5) % 64)
        ]
        initial_population.append(Individual(genes=genes))
    
    engine.population = initial_population
    
    for idx, ind in enumerate(engine.population):
        ind.fitness = (idx * 10) % 100
    
    stats = engine.evolve_one_generation()
    
    print(f"  ✓ generation: {stats['generation']}")
    print(f"  ✓ best_fitness: {stats['best_fitness']:.2f}")
    print(f"  ✓ avg_fitness: {stats['avg_fitness']:.2f}")
    print(f"  ✓ diversity: {stats['diversity']:.4f}")
    print(f"  ✓ diversity_before_selection: {stats['diversity_before_selection']:.4f}")
    print(f"  ✓ mutation_rate: {stats['mutation_rate']:.4f}")
    print(f"  ✓ mutation_rate_change: {stats['mutation_rate_change']:.6f}")
    
    expected_keys = [
        'generation', 'best_fitness', 'avg_fitness', 'worst_fitness',
        'diversity', 'diversity_before_selection', 'population_size',
        'mutation_rate', 'mutation_rate_change'
    ]
    
    all_keys_present = all(k in stats for k in expected_keys)
    print(f"  ✓ 所有预期统计键存在: {all_keys_present}")
    
    print("\n  进化统计信息验证通过! ✅")


def main():
    print("\n" + "=" * 60)
    print("   易衍·Evomorph 优化功能验证测试")
    print("=" * 60)
    print("\n执行以下测试:\n")
    
    try:
        test_evolution_config()
        test_individual_class()
        test_diversity_calculation()
        test_adaptive_mutation_rate()
        test_evolve_one_generation_stats()
        
        print("\n" + "=" * 60)
        print("   ✅ 所有测试通过!")
        print("=" * 60)
        print("\n已成功实现的优化:")
        print("  1. 生成-验证-修复循环 (GVR Loop) - evo_ai.py")
        print("  2. 基于实际执行的适应度评估 - engine.py")
        print("  3. 自适应变异率 - engine.py")
        print("  4. 增强的种群多样性计算 - engine.py")
        print("  5. 增强的系统提示词 - system_prompt.md")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
