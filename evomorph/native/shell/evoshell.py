import sys
import os
import argparse
import json
import time
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from evomorph.native.loader.evb_loader import NativeLoader
from evomorph.native.linker.linker import EvoLinker
from evomorph.native.image.evo_image import EvoImage
from evomorph.bootstrap.runtime.enhanced_runtime import EnhancedEvoRuntime
from evomorph.vm.virtual_machine import IChingVM, VMState
from evomorph.hexagrams import HexagramInstructionSet
from evomorph.evolution.engine import EvolutionEngine, EvolutionConfig, GeneInstruction
from evomorph.simulator.niche import PlatformSimNiche
from evomorph.sdk.xiangci import XiangciSDK
from evomorph.debugger.yaojing import YaoJingDebugger


class EvoShell:
    def __init__(self):
        self.compiler = EnhancedEvoRuntime()
        self.loader = NativeLoader()
        self.linker = EvoLinker()
        self.image_builder = EvoImage()
        self.isa = HexagramInstructionSet()
        self.sdk = XiangciSDK()
        self.vm = IChingVM()
        self.dbg = YaoJingDebugger(self.vm)
        self.sim = PlatformSimNiche()
        self.verbose = False

    def cmd_compile(self, input_path: str, output_path: Optional[str] = None,
                    fmt: str = "json") -> int:
        try:
            if fmt == "evb":
                from evomorph.native.bytecode_utils import source_to_segments
                with open(input_path, "r", encoding="utf-8") as f:
                    source = f.read()
                segments = source_to_segments(self.compiler, source)
                out = output_path or input_path.replace(".evo", ".evb")
                self.loader.save_evb(out, segments)
                print(f"✓ 编译完成: {out} ({len(segments)} 个基因座)")
            else:
                result = self.compiler.full_compile(source)
                out = output_path or input_path.replace(".evo", f".{fmt}")
                with open(out, "w", encoding="utf-8") as f:
                    if isinstance(result, str):
                        f.write(result)
                    else:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"✓ 编译完成: {out}")
            return 0
        except Exception as e:
            print(f"✗ 编译错误: {e}", file=sys.stderr)
            return 1

    def cmd_run(self, input_path: str, max_cycles: int = 100000,
                entry_locus: Optional[str] = None) -> int:
        try:
            if input_path.endswith(".evb"):
                self.loader.load_evb(input_path)
                if entry_locus:
                    name = entry_locus
                else:
                    names = list(self.loader.loaded_segments.keys())
                    name = names[0] if names else None
                if not name:
                    print("✗ 未找到基因座", file=sys.stderr)
                    return 1
                result = self.loader.execute_segment(name, max_cycles=max_cycles)
            elif input_path.endswith(".evoi"):
                result = EvoImage.load_and_run(input_path, max_cycles=max_cycles)
            else:
                with open(input_path, "r", encoding="utf-8") as f:
                    source = f.read()
                ast = self.compiler.full_compile(source)
                loci = ast.get("loci", [])
                if not loci:
                    print("✗ 未找到基因座", file=sys.stderr)
                    return 1
                locus = loci[0]
                if entry_locus:
                    for l in loci:
                        if l["name"] == entry_locus:
                            locus = l
                            break
                program = []
                for instr in locus.get("instructions", []):
                    program.append({
                        "opcode": instr.get("opcode", 0),
                        "modifier": instr.get("modifier", 0),
                        "operands": [op.get("value", 0) if isinstance(op, dict) else op
                                     for op in instr.get("operands", [])],
                    })
                self.vm.reset()
                self.vm.register_io_handler(0xFF00, lambda val: print(f"[输出] {val}"))
                self.vm.load_program(program)
                state = self.vm.run(max_cycles=max_cycles)
                result = {
                    "state": state.name,
                    "cycles": self.vm.cycle_count,
                    "energy": self.vm.energy_cost,
                }
            print(f"状态: {result.get('state', '???')}")
            print(f"周期: {result.get('cycles', 0)}")
            print(f"能耗: {result.get('energy', 0):.2f}")
            return 0
        except Exception as e:
            print(f"✗ 运行错误: {e}", file=sys.stderr)
            return 1

    def cmd_evolve(self, input_path: str, generations: int = 20,
                   population: int = 32, target: Optional[str] = None,
                   output_path: Optional[str] = None) -> int:
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                source = f.read()
            ast = self.compiler.full_compile(source)
            loci = ast.get("loci", [])
            if not loci:
                print("✗ 未找到基因座", file=sys.stderr)
                return 1
            locus = loci[0]
            seed_genes = []
            for instr in locus.get("instructions", []):
                gene = GeneInstruction(
                    opcode=instr.get("opcode", 0),
                    modifier=instr.get("modifier", 0),
                )
                seed_genes.append(gene)
            targets = target.split(",") if target else locus.get("env_targets", ["linux-6.x"])
            config = EvolutionConfig(
                population_size=population,
                max_generations=generations,
                mut_rate=locus.get("mut_rate", 0.02),
                env_targets=targets,
            )
            engine = EvolutionEngine(config=config, platform_simulator=self.sim)
            engine.initialize_population(seed_genes)
            print(f"⟳ 进化: {locus['name']} ({generations}代, {population}个体)")
            best = engine.evolve(callback=lambda s: None)
            if best:
                print(f"✓ 最佳适应度: {best.fitness:.4f}")
                print(f"  基因数: {len(best.genes)}")
                for p, s in best.platform_scores.items():
                    print(f"  {p}: {s:.4f}")
                if output_path:
                    result = {
                        "locus": locus["name"],
                        "best_fitness": best.fitness,
                        "genes": [{"opcode": g.opcode, "modifier": g.modifier} for g in best.genes],
                        "history": engine.get_evolution_history(),
                    }
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
            return 0
        except Exception as e:
            print(f"✗ 进化错误: {e}", file=sys.stderr)
            return 1

    def cmd_xiangci(self, text: str, target: Optional[str] = None,
                    evo_source: bool = False) -> int:
        targets = target.split(",") if target else ["linux-6.x"]
        translation = self.sdk.translate(text, env_targets=targets)
        print(f"象辞: {translation.original_text}")
        print(f"基因座: {translation.locus_name}")
        print(f"置信度: {translation.confidence:.2f}")
        if evo_source:
            source = self.sdk.export_to_evo_source(translation)
            print(f"\n{source}")
        else:
            for gene in translation.generated_genes:
                entry = self.isa.get_by_opcode(gene.get("opcode", 0))
                sym = entry["symbol"] if entry else "???"
                mn = gene.get("mnemonic", "???")
                print(f"  {sym} {mn}")
        return 0

    def cmd_image(self, input_path: str, entry_locus: str,
                  output_path: Optional[str] = None) -> int:
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                source = f.read()
            image_data = self.image_builder.build_from_source(source, entry_locus)
            out = output_path or input_path.replace(".evo", ".evoi")
            self.image_builder.save_image(out, image_data)
            print(f"✓ 映像构建完成: {out} ({len(image_data)} 字节)")
            return 0
        except Exception as e:
            print(f"✗ 映像构建错误: {e}", file=sys.stderr)
            return 1

    def cmd_link(self, input_files: list, output_path: str,
                 entry_locus: Optional[str] = None) -> int:
        try:
            for f in input_files:
                if f.endswith(".evb"):
                    self.linker.add_evb(f)
                else:
                    with open(f, "r", encoding="utf-8") as fh:
                        source = fh.read()
                    self.linker.add_evo_source(source)
            result = self.linker.link(output_path, entry_locus)
            print(f"✓ 链接完成: {output_path}")
            print(f"  基因座: {result['segment_count']}")
            for name in result["segments"]:
                print(f"    - {name}")
            return 0
        except Exception as e:
            print(f"✗ 链接错误: {e}", file=sys.stderr)
            return 1


def main():
    parser = argparse.ArgumentParser(
        prog="evoshell",
        description="易衍·Evomorph 原生运行时外壳 v3.0",
    )
    subparsers = parser.add_subparsers(dest="command")

    compile_p = subparsers.add_parser("compile", help="编译 .evo → .evb/.json")
    compile_p.add_argument("input")
    compile_p.add_argument("-o", "--output")
    compile_p.add_argument("-f", "--format", default="evb", choices=["json", "evb"])

    run_p = subparsers.add_parser("run", help="执行 .evo/.evb/.evoi")
    run_p.add_argument("input")
    run_p.add_argument("-c", "--max-cycles", type=int, default=100000)
    run_p.add_argument("-e", "--entry-locus")

    evolve_p = subparsers.add_parser("evolve", help="进化编译")
    evolve_p.add_argument("input")
    evolve_p.add_argument("-g", "--generations", type=int, default=20)
    evolve_p.add_argument("-p", "--population", type=int, default=32)
    evolve_p.add_argument("-t", "--target")
    evolve_p.add_argument("-o", "--output")

    xiangci_p = subparsers.add_parser("xiangci", help="象辞翻译")
    xiangci_p.add_argument("text")
    xiangci_p.add_argument("-t", "--target")
    xiangci_p.add_argument("--evo-source", action="store_true")

    image_p = subparsers.add_parser("image", help="构建可执行映像")
    image_p.add_argument("input")
    image_p.add_argument("-e", "--entry-locus", required=True)
    image_p.add_argument("-o", "--output")

    link_p = subparsers.add_parser("link", help="链接多个文件")
    link_p.add_argument("inputs", nargs="+")
    link_p.add_argument("-o", "--output", required=True)
    link_p.add_argument("-e", "--entry-locus")

    args = parser.parse_args()
    shell = EvoShell()

    if args.command == "compile":
        sys.exit(shell.cmd_compile(args.input, args.output, args.format))
    elif args.command == "run":
        sys.exit(shell.cmd_run(args.input, args.max_cycles, args.entry_locus))
    elif args.command == "evolve":
        sys.exit(shell.cmd_evolve(args.input, args.generations, args.population, args.target, args.output))
    elif args.command == "xiangci":
        sys.exit(shell.cmd_xiangci(args.text, args.target, args.evo_source))
    elif args.command == "image":
        sys.exit(shell.cmd_image(args.input, args.entry_locus, args.output))
    elif args.command == "link":
        sys.exit(shell.cmd_link(args.inputs, args.output, args.entry_locus))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
