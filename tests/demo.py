import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evomorph.compiler import EvocCompiler
from evomorph.evolution.engine import EvolutionEngine, EvolutionConfig, GeneInstruction
from evomorph.simulator.niche import PlatformSimNiche
from evomorph.sdk.xiangci import XiangciSDK
from tools.yaojing.yaojing import YaoJingDebugger
from evomorph.vm.virtual_machine import IChingVM

print("=" * 60)
print("易衍·Evomorph 完整工作流演示")
print("=" * 60)

print("\n[一] 编译 sum_all.evo")
compiler = EvocCompiler()
with open("examples/sum_all.evo", "r") as f:
    source = f.read()
result = compiler.compile(source, output_format="dict")
print(f"  基因座数量: {len(result.get('loci', []))}")
for locus in result.get("loci", []):
    print(f"  基因座: {locus['name']}")
    print(f"  变异率: {locus['mut_rate']}")
    print(f"  目标平台: {locus['env_targets']}")
    print(f"  指令数: {len(locus['instructions'])}")

print("\n[二] 进化编译")
locus = result["loci"][0]
seed_genes = []
for instr in locus.get("instructions", []):
    gene = GeneInstruction(opcode=instr.get("opcode", 0), modifier=instr.get("modifier", 0))
    seed_genes.append(gene)

sim = PlatformSimNiche()
config = EvolutionConfig(
    population_size=32, max_generations=20, mut_rate=0.03,
    env_targets=["android-14", "win-11"],
)
engine = EvolutionEngine(config=config, platform_simulator=sim)
engine.initialize_population(seed_genes)

def progress(stats):
    if stats["generation"] % 5 == 0:
        print(f"  代 {stats['generation']:3d} | 最佳: {stats['best_fitness']:8.2f} | 多样性: {stats['diversity']:.3f}")

best = engine.evolve(callback=progress)
print(f"  最终最佳适应度: {best.fitness:.4f}")
print(f"  最佳个体基因数: {len(best.genes)}")
for platform, score in best.platform_scores.items():
    print(f"    {platform}: {score:.4f}")

print("\n[三] 象辞翻译")
sdk = XiangciSDK()
translation = sdk.translate("并行求和，适安卓与鸿蒙", env_targets=["android-14", "harmony-5"])
print(f"  象辞: {translation.original_text}")
print(f"  生成基因座: {translation.locus_name}")
print(f"  置信度: {translation.confidence:.2f}")
print(f"  指令数: {len(translation.generated_genes)}")
for gene in translation.generated_genes:
    print(f"    {gene.get('mnemonic', '???')} (opcode={gene.get('opcode', 0):#04x})")

print("\n[四] IChingVM 运行")
vm = IChingVM()
program = [{"opcode": g.opcode, "modifier": g.modifier, "operands": list(g.operands)} for g in best.genes]
vm.load_program(program)
vm.run(max_cycles=100)
print(f"  VM 状态: {vm.state.name}")
print(f"  运行周期: {vm.cycle_count}")
print(f"  累计能耗: {vm.energy_cost:.2f}")

print("\n[五] 爻镜调试")
dbg = YaoJingDebugger(IChingVM())
program2 = [
    {"opcode": 63, "modifier": 0, "operands": [0, 1]},
    {"opcode": 61, "modifier": 0, "operands": [0, 1]},
    {"opcode": 21, "modifier": 0, "operands": [0]},
    {"opcode": 0, "modifier": 0, "operands": [2, 0]},
    {"opcode": 56, "modifier": 0, "operands": [0, 0]},
]
dbg.vm.load_program(program2)
dbg.step_instruction()
print(f"  指令解释: {dbg.explain_instruction()}")
print(f"  爻位视图:")
print(dbg.get_yao_visualization())
print(f"  自然语言查询: {dbg.query_natural_language('当前状态如何？')}")

print("\n" + "=" * 60)
print("易衍·Evomorph 演示完成！")
print("简易 · 变易 · 不易 · 进化")
print("=" * 60)
