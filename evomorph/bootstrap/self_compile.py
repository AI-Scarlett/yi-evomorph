import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from evomorph.bootstrap.runtime import EvoRuntime
from evomorph.compiler import EvocCompiler
from evomorph.evolution.engine import EvolutionEngine, EvolutionConfig, GeneInstruction, Individual
from evomorph.simulator.niche import PlatformSimNiche
from evomorph.hexagrams import HexagramInstructionSet


class SelfCompiler:
    def __init__(self):
        self.runtime = EvoRuntime()
        self.isa = HexagramInstructionSet()
        self.sim = PlatformSimNiche()
        self.generation = 0
        self.compile_history = []

    def bootstrap(self, evo_compiler_path: str) -> dict:
        print("=" * 60)
        print("易衍·Evomorph 道枢自举")
        print("=" * 60)

        print("\n[第一步] 加载自编译器 .evo 源码")
        result = self.runtime.load_evo_file(evo_compiler_path)
        loci_names = [l["name"] for l in result.get("loci", [])]
        meta_names = [m["name"] for m in result.get("meta_loci", [])]
        print(f"  加载基因座: {len(loci_names)}")
        for name in loci_names:
            print(f"    - {name}")
        print(f"  加载元基因座: {len(meta_names)}")
        for name in meta_names:
            print(f"    - meta:{name}")

        print("\n[第二步] 执行编译器各基因座")
        for name in loci_names:
            exec_result = self.runtime.execute_locus(name, max_cycles=100)
            print(f"  {name}: 状态={exec_result['state']}, 周期={exec_result['cycle_count']}, 能耗={exec_result['energy_cost']:.2f}")

        print("\n[第三步] 进化编译器各基因座")
        evolution_results = {}
        for name in loci_names:
            evo_result = self.runtime.evolve_locus(name, generations=10, population_size=16)
            if evo_result:
                evolution_results[name] = evo_result
                print(f"  {name}: 最佳适应度={evo_result['best_fitness']:.4f}, 基因数={evo_result['best_genes_count']}")

        print("\n[第四步] 用进化后的编译器编译自身")
        with open(evo_compiler_path, "r", encoding="utf-8") as f:
            original_source = f.read()
        self_compilation = self.runtime.self_compile(original_source)
        self_loci = [l["name"] for l in self_compilation.get("loci", [])]
        print(f"  自编译成功: {len(self_loci)} 个基因座")
        for name in self_loci:
            locus = self.runtime.get_locus(name)
            instr_count = len(locus.get("instructions", [])) if locus else 0
            print(f"    - {name}: {instr_count} 条指令")

        print("\n[第五步] 交叉验证——自编译结果与原始编译结果对比")
        compiler = EvocCompiler()
        original_result = compiler.compile(original_source, output_format="dict")
        original_loci = {l["name"]: l for l in original_result.get("loci", [])}
        evolved_loci = {l["name"]: l for l in self_compilation.get("loci", [])}
        match_count = 0
        for name in evolved_loci:
            if name in original_loci:
                evo_instrs = evolved_loci[name].get("instructions", [])
                orig_instrs = original_loci[name].get("instructions", [])
                if len(evo_instrs) == len(orig_instrs):
                    match = all(
                        e.get("opcode") == o.get("opcode")
                        for e, o in zip(evo_instrs, orig_instrs)
                    )
                    if match:
                        match_count += 1
        total = len(evolved_loci)
        print(f"  完全匹配: {match_count}/{total}")

        print("\n[第六步] 导出进化后的编译器")
        for name in loci_names:
            evolved_source = self.runtime.export_evolved_locus(name)
            if evolved_source:
                output_dir = os.path.join(os.path.dirname(evo_compiler_path), "evolved")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{name.replace('.', '_')}.evo")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(evolved_source)
                print(f"  导出: {output_path}")

        self.generation += 1
        summary = {
            "generation": self.generation,
            "loci_count": len(loci_names),
            "meta_loci_count": len(meta_names),
            "evolution_results": {
                k: {"best_fitness": v["best_fitness"], "genes_count": v["best_genes_count"]}
                for k, v in evolution_results.items()
            },
            "self_compilation_match": f"{match_count}/{total}",
            "timestamp": time.time(),
        }
        self.compile_history.append(summary)

        print("\n" + "=" * 60)
        print("道枢自举完成！")
        print("简易 · 变易 · 不易 · 进化 · 自举")
        print("=" * 60)

        return summary

    def iterative_evolution(self, evo_compiler_path: str, iterations: int = 5) -> list:
        print("=" * 60)
        print("易衍·Evomorph 迭代自进化")
        print("=" * 60)
        results = []
        for i in range(iterations):
            print(f"\n--- 迭代 {i + 1}/{iterations} ---")
            result = self.bootstrap(evo_compiler_path)
            results.append(result)
            if i < iterations - 1:
                evolved_dir = os.path.join(os.path.dirname(evo_compiler_path), "evolved")
                evolved_files = [f for f in os.listdir(evolved_dir) if f.endswith(".evo")] if os.path.exists(evolved_dir) else []
                if evolved_files:
                    print(f"  使用进化后的编译器继续迭代...")
        return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="易衍·Evomorph 道枢自举")
    parser.add_argument("input", help="编译器 .evo 文件路径（如 evoc/lexer.evo）")
    parser.add_argument("-i", "--iterations", type=int, default=1, help="迭代次数")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    args = parser.parse_args()

    sc = SelfCompiler()
    if args.iterations > 1:
        results = sc.iterative_evolution(args.input, args.iterations)
        print(f"\n迭代进化完成: {len(results)} 轮")
        for r in results:
            print(f"  代{r['generation']}: 匹配={r['self_compilation_match']}")
    else:
        sc.bootstrap(args.input)


if __name__ == "__main__":
    main()
