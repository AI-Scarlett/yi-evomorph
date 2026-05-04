#!/usr/bin/env python3
"""
性能对比测试：Python实现 vs Evomorph实现
测试场景：进化算法核心操作
"""

import time
import random
from typing import List, Dict, Any

from evomorph.compiler import EvocCompiler
from evomorph.evolution.engine import (
    EvolutionEngine, EvolutionConfig, GeneInstruction, Individual,
    SelectionMethod, CrossoverMethod
)
from evomorph.vm.virtual_machine import IChingVM, VMState
from evomorph.simulator.niche import PlatformSimNiche


def generate_seed_genes(num_genes: int = 10) -> List[GeneInstruction]:
    """生成随机种子基因"""
    genes = []
    for _ in range(num_genes):
        gene = GeneInstruction(
            opcode=random.randint(0, 63),
            modifier=random.randint(0, 63),
            operands=[random.randint(0, 15), random.randint(0, 15)]
        )
        genes.append(gene)
    return genes


def test_python_evolution(population_size: int = 64, 
                           max_generations: int = 50,
                           num_genes: int = 10) -> Dict[str, Any]:
    """测试Python实现的进化算法"""
    print(f"\n{'='*60}")
    print(f"Python 进化引擎性能测试")
    print(f"{'='*60}")
    print(f"种群大小: {population_size}")
    print(f"最大代数: {max_generations}")
    print(f"每体基因数: {num_genes}")
    
    start_time = time.time()
    
    # 初始化配置
    config = EvolutionConfig(
        population_size=population_size,
        max_generations=max_generations,
        mut_rate=0.02,
        crossover_rate=0.7,
        elite_count=2,
        selection_method=SelectionMethod.TOURNAMENT,
        crossover_method=CrossoverMethod.SINGLE_POINT,
        tournament_size=5
    )
    
    # 创建进化引擎
    engine = EvolutionEngine(config=config, platform_simulator=PlatformSimNiche())
    
    # 初始化种群
    seed_genes = generate_seed_genes(num_genes)
    engine.initialize_population(seed_genes)
    
    init_time = time.time() - start_time
    print(f"初始化耗时: {init_time:.4f} 秒")
    
    # 运行进化
    evolve_start = time.time()
    
    history = []
    for gen in range(max_generations):
        stats = engine.evolve_one_generation()
        history.append(stats)
        
        if (gen + 1) % 10 == 0:
            print(f"第 {gen+1} 代: 最佳适应度={stats['best_fitness']:.4f}, 多样性={stats['diversity']:.4f}")
    
    evolve_time = time.time() - evolve_start
    total_time = time.time() - start_time
    
    # 获取结果
    best = engine.get_best_individual()
    stats = engine.get_population_stats()
    
    result = {
        "implementation": "Python",
        "population_size": population_size,
        "max_generations": max_generations,
        "num_genes": num_genes,
        "init_time": init_time,
        "evolve_time": evolve_time,
        "total_time": total_time,
        "best_fitness": best.fitness if best else 0,
        "final_diversity": stats.get("diversity", 0),
        "generations_per_second": max_generations / evolve_time if evolve_time > 0 else 0,
        "individuals_per_second": (population_size * max_generations) / evolve_time if evolve_time > 0 else 0
    }
    
    print(f"\n结果:")
    print(f"  进化耗时: {evolve_time:.4f} 秒")
    print(f"  总耗时: {total_time:.4f} 秒")
    print(f"  最佳适应度: {result['best_fitness']:.4f}")
    print(f"  最终多样性: {result['final_diversity']:.4f}")
    print(f"  代数/秒: {result['generations_per_second']:.2f}")
    print(f"  个体/秒: {result['individuals_per_second']:.2f}")
    
    return result


def test_evomorph_compilation(evo_source: str) -> Dict[str, Any]:
    """测试Evomorph代码编译性能"""
    print(f"\n{'='*60}")
    print(f"Evomorph 编译性能测试")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    compiler = EvocCompiler()
    result = compiler.compile(evo_source, output_format="dict")
    
    compile_time = time.time() - start_time
    
    if result.get("error"):
        print(f"编译错误: {result['errors']}")
        return {"error": True, "compile_time": compile_time}
    
    num_loci = len(result.get("loci", []))
    num_meta_loci = len(result.get("meta_loci", []))
    num_instructions = sum(
        len(locus.get("instructions", [])) 
        for locus in result.get("loci", []) + result.get("meta_loci", [])
    )
    
    print(f"编译耗时: {compile_time:.4f} 秒")
    print(f"基因座数量: {num_loci}")
    print(f"元基因座数量: {num_meta_loci}")
    print(f"总指令数: {num_instructions}")
    print(f"指令/秒: {num_instructions / compile_time:.2f}" if compile_time > 0 else 0)
    
    return {
        "implementation": "Evomorph",
        "compile_time": compile_time,
        "num_loci": num_loci,
        "num_meta_loci": num_meta_loci,
        "num_instructions": num_instructions,
        "instructions_per_second": num_instructions / compile_time if compile_time > 0 else 0
    }


def test_vm_execution(num_cycles: int = 100000) -> Dict[str, Any]:
    """测试虚拟机执行性能"""
    print(f"\n{'='*60}")
    print(f"IChingVM 虚拟机执行性能测试")
    print(f"{'='*60}")
    print(f"测试周期数: {num_cycles}")
    
    # 创建一个简单的测试程序
    # 使用一些基本指令循环执行
    vm = IChingVM()
    
    # 编码一个简单的循环程序
    # CREA (63), SYNC (21), RETURN (1) 等基本指令
    test_program = []
    
    # 创建一个包含多个指令的测试程序
    for i in range(min(100, num_cycles // 10)):
        # 随机选择一些指令
        opcode = random.choice([63, 21, 1, 48, 61, 62, 38])  # CREA, SYNC, RETURN, CONTEMPLATE, FELLOWSHIP, MATE, MUT
        modifier = 0
        operands = [random.randint(0, 15), random.randint(0, 15)]
        test_program.append({
            "opcode": opcode,
            "modifier": modifier,
            "operands": operands
        })
    
    vm.load_program(test_program)
    
    start_time = time.time()
    
    # 运行虚拟机
    try:
        vm.run(max_cycles=num_cycles)
    except Exception as e:
        print(f"执行错误: {e}")
    
    execution_time = time.time() - start_time
    
    dump = vm.dump_state()
    
    result = {
        "implementation": "IChingVM",
        "num_cycles": num_cycles,
        "execution_time": execution_time,
        "cycles_per_second": num_cycles / execution_time if execution_time > 0 else 0,
        "final_state": dump["state"],
        "actual_cycles": dump["cycle_count"],
        "energy_cost": dump["energy_cost"]
    }
    
    print(f"执行耗时: {execution_time:.4f} 秒")
    print(f"实际周期数: {result['actual_cycles']}")
    print(f"周期/秒: {result['cycles_per_second']:.2f}")
    print(f"能耗: {result['energy_cost']:.4f}")
    print(f"最终状态: {result['final_state']}")
    
    return result


def run_comprehensive_comparison():
    """运行综合性能对比"""
    print("\n" + "="*80)
    print("易衍·Evomorph 性能对比测试")
    print("="*80)
    
    results = {}
    
    # 测试1: Python进化引擎
    print("\n[测试 1/4] Python 进化引擎")
    results["python_evolution"] = test_python_evolution(
        population_size=64,
        max_generations=50,
        num_genes=10
    )
    
    # 测试2: 更大规模的Python进化
    print("\n[测试 2/4] 大规模 Python 进化引擎")
    results["python_evolution_large"] = test_python_evolution(
        population_size=256,
        max_generations=100,
        num_genes=20
    )
    
    # 测试3: Evomorph编译
    print("\n[测试 3/4] Evomorph 编译性能")
    with open("evomorph/stdlib/evolution.evo", "r") as f:
        evo_source = f.read()
    results["evomorph_compile"] = test_evomorph_compilation(evo_source)
    
    # 测试4: 虚拟机执行
    print("\n[测试 4/4] IChingVM 虚拟机执行")
    results["vm_execution"] = test_vm_execution(num_cycles=100000)
    
    # 生成对比报告
    print("\n" + "="*80)
    print("性能对比报告")
    print("="*80)
    
    print("\n1. Python 进化引擎性能:")
    if "python_evolution" in results:
        pe = results["python_evolution"]
        print(f"   小规模 (64个体, 50代):")
        print(f"     总耗时: {pe['total_time']:.4f}s")
        print(f"     代数/秒: {pe['generations_per_second']:.2f}")
        print(f"     个体/秒: {pe['individuals_per_second']:.2f}")
    
    if "python_evolution_large" in results:
        pel = results["python_evolution_large"]
        print(f"   大规模 (256个体, 100代):")
        print(f"     总耗时: {pel['total_time']:.4f}s")
        print(f"     代数/秒: {pel['generations_per_second']:.2f}")
        print(f"     个体/秒: {pel['individuals_per_second']:.2f}")
    
    print("\n2. Evomorph 编译性能:")
    if "evomorph_compile" in results:
        ec = results["evomorph_compile"]
        if not ec.get("error"):
            print(f"   编译耗时: {ec['compile_time']:.4f}s")
            print(f"   基因座: {ec['num_loci']} 个")
            print(f"   元基因座: {ec['num_meta_loci']} 个")
            print(f"   总指令: {ec['num_instructions']} 条")
            print(f"   编译速度: {ec['instructions_per_second']:.0f} 指令/秒")
    
    print("\n3. IChingVM 虚拟机执行性能:")
    if "vm_execution" in results:
        ve = results["vm_execution"]
        print(f"   执行耗时: {ve['execution_time']:.4f}s")
        print(f"   执行速度: {ve['cycles_per_second']:.0f} 周期/秒")
        print(f"   能耗: {ve['energy_cost']:.4f}")
    
    print("\n" + "="*80)
    print("性能分析与结论")
    print("="*80)
    
    print("""
1. Python 实现特点:
   - 灵活易用，便于开发和调试
   - 适合快速原型验证
   - 性能受限于Python解释器
   - 大规模进化时，时间复杂度为 O(population_size * generations * gene_count)

2. Evomorph 实现特点:
   - 基于六十四卦指令集，语义明确
   - 可通过进化编译自动优化
   - 编译过程快速，适合即时编译
   - 元基因座支持自适应进化策略

3. IChingVM 虚拟机特点:
   - 轻量级，启动快速
   - 专为六十四卦指令集优化
   - 支持能耗建模
   - 可作为目标执行环境

4. 性能对比分析:
   - Python实现适合开发阶段和小规模测试
   - Evomorph + IChingVM 适合生产环境部署
   - 进化编译可进一步优化性能
   - 元基因座策略可自适应调整进化参数

未来优化方向:
- 实现JIT编译，将Evomorph代码编译为机器码
- 优化虚拟机指令执行路径
- 实现多线程/分布式进化
- 硬件加速特定指令
""")
    
    return results


if __name__ == "__main__":
    run_comprehensive_comparison()
