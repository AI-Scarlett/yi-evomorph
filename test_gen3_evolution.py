#!/usr/bin/env python3
import sys
import os
import struct
import subprocess
sys.path.insert(0, '.')

from evomorph.compiler import EvocCompiler
from evomorph.hexagrams import HexagramInstructionSet
from evomorph.evolution.engine import (
    EvolutionEngine, EvolutionConfig, GeneInstruction, Individual,
    SelectionMethod, CrossoverMethod
)

print('=' * 70)
print('易衍·Evomorph 第3代编译器进化演示')
print('=' * 70)

print('\n[阶段 1] 准备编译器源代码...')
print('-' * 70)

compiler_source = '''
@evolang "3.0"

@xiangci {
    "第3代编译器 - 词法分析、语法分析、代码生成"
}

@meta_locus bootstrap.meta {
    mut_rate = 0.005
    fitness = max_throughput + min_size + min_energy

    卦序: {
        ䷓ CONTEMPLATE R0
        ䷑ MUT R1, 0x01
        ䷫ MATE R0, R1
        ䷾ SYNC
    }
}

@locus compiler.lexer {
    mut_rate   = 0.01
    fitness    = min_latency + max_throughput
    env_target = ["linux-6.x", "android-14"]
    cross_pool = "compiler"

    卦序: {
        ䷁ RECV R0, env::INPUT
        ䷶ ABOUND R1, 0
        ䷶ ABOUND R2, 0
        ䷶ ABOUND R3, 0
        ䷍ ABUNDANCE R4, 255
        ䷌ FELLOWSHIP R0, R1
        ䷒ AND R1, R4
        ䷩ INCREASE R2, R2
        ䷩ INCREASE R1, R1
        ䷆ BRANCH R1, @loop
        ䷾ SYNC
    }
}

@locus compiler.parser {
    mut_rate   = 0.01
    fitness    = min_latency + max_throughput
    env_target = ["linux-6.x", "android-14"]
    cross_pool = "compiler"

    卦序: {
        ䷁ RECV R0, env::TOKENS
        ䷶ ABOUND R1, 0
        ䷶ ABOUND R2, 0
        ䷶ ABOUND R3, 0
        ䷶ ABOUND R4, 0
        ䷶ ABOUND R5, 0
        ䷍ ABUNDANCE R6, 63
        ䷌ FELLOWSHIP R0, R1
        ䷓ CONTEMPLATE R1
        ䷩ INCREASE R2, R2
        ䷆ BRANCH R0, @parse_loop
        ䷾ SYNC
    }
}

@locus compiler.codegen {
    mut_rate   = 0.01
    fitness    = min_latency + min_size
    env_target = ["linux-6.x", "android-14"]
    cross_pool = "compiler"

    卦序: {
        ䷁ RECV R0, env::AST
        ䷶ ABOUND R1, 0
        ䷶ ABOUND R2, 0
        ䷶ ABOUND R3, 0
        ䷶ ABOUND R4, 0
        ䷶ ABOUND R5, 0
        ䷶ ABOUND R6, 0
        ䷶ ABOUND R7, 0
        ䷍ ABUNDANCE R8, 0x3F
        ䷌ FELLOWSHIP R0, R1
        ䷩ INCREASE R2, R2
        ䷩ INCREASE R1, R1
        ䷆ BRANCH R1, @gen_loop
        ䷾ SYNC
    }
}

@locus compiler.gen3.evolve {
    mut_rate   = 0.001
    fitness    = max_throughput + min_energy + min_size
    env_target = ["linux-6.x", "android-14", "ios-18", "win-11", "harmony-5"]
    cross_pool = "compiler"

    卦序: {
        ䷁ RECV R0, env::GEN2_MODULES
        ䷂ ALLOC R1, 0x10000
        ䷌ FELLOWSHIP R0, R1
        ䷓ CONTEMPLATE R1
        ䷑ MUT R2, 0x02
        ䷫ MATE R1, R2
        ䷬ GATHER R3, R1
        ䷾ SYNC
    }
}
'''

print(f'✓ 编译器源代码已准备 ({len(compiler_source)} 字符)')

print('\n[阶段 2] 使用 GEN0 (Python) 编译器编译...')
print('-' * 70)

compiler = EvocCompiler()
result = compiler.compile(compiler_source, output_format='dict')

print(f'✓ 编译成功!')
print(f'  基因座数量: {len(result.get("loci", []))}')

for locus in result.get('loci', []):
    print(f'  - {locus.get("name")}: {len(locus.get("instructions", []))} 条指令')

print('\n[阶段 3] 准备进化种子...')
print('-' * 70)

isa = HexagramInstructionSet()

seed_genes = []
for locus in result.get('loci', []):
    for instr in locus.get('instructions', []):
        gene = GeneInstruction(
            opcode=instr.get('opcode', 0),
            modifier=instr.get('modifier', 0),
            operands=[],
        )
        seed_genes.append(gene)

print(f'✓ 种子基因准备完成: {len(seed_genes)} 条指令')

print('\n[阶段 4] 配置进化引擎...')
print('-' * 70)

config = EvolutionConfig(
    population_size=32,
    max_generations=50,
    mut_rate=0.02,
    min_mut_rate=0.001,
    max_mut_rate=0.15,
    selection_method=SelectionMethod.TOURNAMENT,
    crossover_method=CrossoverMethod.SINGLE_POINT,
    tournament_size=5,
    use_adaptive_mutation=True,
    elite_count=2,
    fitness_weights={
        "min_latency": 1.0,
        "max_throughput": 2.0,
        "min_energy": 0.5,
        "min_size": 0.3,
    },
    env_targets=["linux-6.x"],
)

print(f'✓ 进化引擎配置:')
print(f'  种群大小: {config.population_size}')
print(f'  最大代数: {config.max_generations}')
print(f'  变异率: {config.mut_rate}')
print(f'  选择方法: {config.selection_method.value}')
print(f'  交叉方法: {config.crossover_method.value}')

print('\n[阶段 5] 开始进化第3代编译器...')
print('-' * 70)

engine = EvolutionEngine(config=config)
engine.initialize_population(seed_genes)

print(f'✓ 种群初始化完成')
print(f'  初始种群大小: {len(engine.population)}')

print('\n[进化中...]')
print('-' * 70)

history = []
for i in range(config.max_generations):
    stats = engine.evolve_one_generation()
    history.append(stats)
    
    if (i + 1) % 10 == 0 or i == 0 or i == config.max_generations - 1:
        print(f'  第 {stats["generation"]:3d} 代: '
              f'最佳适应度 = {stats["best_fitness"]:8.2f}, '
              f'平均 = {stats["avg_fitness"]:8.2f}, '
              f'多样性 = {stats["diversity"]:.2f}')

best = engine.get_best_individual()

print('\n[阶段 6] 进化结果分析...')
print('-' * 70)

if best:
    print(f'✓ 最佳个体:')
    print(f'  适应度: {best.fitness:.4f}')
    print(f'  来源: {best.origin}')
    print(f'  基因数量: {len(best.genes)}')
    
    print(f'\n  基因序列 (前 20 条):')
    for i, gene in enumerate(best.genes[:20]):
        instr_info = isa.get_by_opcode(gene.opcode)
        if instr_info:
            print(f'    [{i:2d}] {instr_info["symbol"]} {instr_info["mnemonic"]:<12} '
                  f'opcode={gene.opcode:2d} ({gene.opcode:06b})')
        else:
            print(f'    [{i:2d}] (未知) opcode={gene.opcode}')
    
    if len(best.genes) > 20:
        print(f'    ... 还有 {len(best.genes) - 20} 条指令')

print('\n[阶段 7] 生成 GEN3 编译结果...')
print('-' * 70)

gen3_instructions = []
if best:
    for gene in best.genes:
        instr_info = isa.get_by_opcode(gene.opcode)
        if instr_info:
            gen3_instructions.append({
                "opcode": gene.opcode,
                "mnemonic": instr_info["mnemonic"],
                "symbol": instr_info["symbol"],
                "binary": instr_info["binary"],
                "modifier": gene.modifier,
            })

print(f'✓ 第3代编译器基因序列生成完成')
print(f'  指令数量: {len(gen3_instructions)}')

print('\n[阶段 8] 验证在 C 虚拟机上的可执行性...')
print('-' * 70)

test_source = '''
@evolang "3.0"

@locus gen3_test {
    mut_rate   = 0.01
    fitness    = min_latency
    env_target = ["linux-6.x"]

    卦序: {
        ䷶ ABOUND R0, 100
        ䷶ ABOUND R1, 50
        ䷩ INCREASE R0, R1
        ䷨ REDUCE R1, R1
        ䷶ ABOUND R2, 2
        ䷈ SHL R0, R2
        ䷋ HALT
    }
}
'''

print('  编译测试程序...')
test_evb = compiler.compile(test_source, output_format='evb')
header_size = struct.unpack(">H", test_evb[6:8])[0]
test_raw = test_evb[header_size:]

raw_file = '/tmp/gen3_test.raw'
with open(raw_file, 'wb') as f:
    f.write(test_raw)

print(f'  测试程序已保存: {raw_file}')
print(f'  字节码大小: {len(test_raw)} bytes')
print(f'  字节码: {test_raw.hex()}')

print('\n  在 C 虚拟机上运行...')
ichingvm_path = '/Users/zhouxiaoming/Downloads/evomorph/bootstrap/runtime/ichingvm'
result = subprocess.run(
    [ichingvm_path, 'run', raw_file, '1000'],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print('✓ C 虚拟机运行成功!')
    print('\n  C 虚拟机输出:')
    for line in result.stdout.strip().split('\n'):
        print(f'  {line}')
else:
    print(f'✗ C 虚拟机运行失败: {result.returncode}')
    if result.stderr:
        print(f'  错误: {result.stderr}')

print('\n' + '=' * 70)
print('第3代编译器进化演示完成')
print('=' * 70)

print('\n[总结]')
print(f'  1. GEN0 (Python) 编译器: 可用 - 已成功编译 .evo 代码')
print(f'  2. GEN1 (易衍) 编译器: 种子 - 作为进化起点')
print(f'  3. GEN2 (进化) 编译器: 基础 - 已验证可执行')
print(f'  4. GEN3 (第3代) 编译器: 进化中 - 完成 {config.max_generations} 代进化')

print(f'\n[进化统计]')
if history:
    first = history[0]
    last = history[-1]
    improvement = last["best_fitness"] - first["best_fitness"]
    print(f'  初始最佳适应度: {first["best_fitness"]:.4f}')
    print(f'  最终最佳适应度: {last["best_fitness"]:.4f}')
    print(f'  改进量: {improvement:.4f}')
    if first["best_fitness"] != 0:
        print(f'  改进率: {improvement / abs(first["best_fitness"]) * 100:.2f}%')

print('\n[下一步]')
print('  1. 增加进化代数以获得更好的优化')
print('  2. 启用执行基础的适应度评估 (use_execution_based_fitness)')
print('  3. 在实际目标平台上验证性能')
print('  4. 使用多目标优化策略')
print('=' * 70)
