import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from evomorph.compiler import EvocCompiler
from evomorph.vm.virtual_machine import IChingVM, VMState
from evomorph.hexagrams import HexagramInstructionSet
from evomorph.evolution.engine import EvolutionEngine, EvolutionConfig, GeneInstruction
from evomorph.simulator.niche import PlatformSimNiche
from evomorph.sdk.xiangci import XiangciSDK
from evomorph.debugger.yaojing import YaoJingDebugger


class EvoREPL:
    def __init__(self):
        self.compiler = EvocCompiler()
        self.vm = IChingVM()
        self.isa = HexagramInstructionSet()
        self.sdk = XiangciSDK()
        self.dbg = YaoJingDebugger(self.vm)
        self.sim = PlatformSimNiche()
        self.running = True
        self.history = []
        self.session_loci = {}

    def banner(self):
        print()
        print("╔══════════════════════════════════════════════════╗")
        print("║  易衍·Evomorph 交互式卦象编程环境  v3.0         ║")
        print("║  简易 · 变易 · 不易 · 进化 · 自举              ║")
        print("╚══════════════════════════════════════════════════╝")
        print()
        print("命令:")
        print("  :help          显示帮助")
        print("  :xiangci <文>  象辞翻译")
        print("  :compile <码>  编译卦象指令")
        print("  :run           运行当前程序")
        print("  :step          单步执行")
        print("  :evolve <N>    进化N代")
        print("  :explain       解释当前指令")
        print("  :yao           显示爻位视图")
        print("  :query <问>    自然语言查询")
        print("  :state         显示VM状态")
        print("  :reset         重置VM")
        print("  :quit          退出")
        print()

    def run(self):
        self.banner()
        while self.running:
            try:
                line = input("易衍> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再见！简易·变易·不易·进化")
                break
            if not line:
                continue
            self.history.append(line)
            self._process(line)

    def _process(self, line: str):
        if line.startswith(":"):
            self._handle_command(line)
        else:
            self._handle_evo_input(line)

    def _handle_command(self, line: str):
        parts = line[1:].split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "help":
            self._cmd_help()
        elif cmd == "xiangci":
            self._cmd_xiangci(arg)
        elif cmd == "compile":
            self._cmd_compile(arg)
        elif cmd == "run":
            self._cmd_run()
        elif cmd == "step":
            self._cmd_step()
        elif cmd == "evolve":
            self._cmd_evolve(arg)
        elif cmd == "explain":
            self._cmd_explain()
        elif cmd == "yao":
            self._cmd_yao()
        elif cmd == "query":
            self._cmd_query(arg)
        elif cmd == "state":
            self._cmd_state()
        elif cmd == "reset":
            self._cmd_reset()
        elif cmd == "quit" or cmd == "exit":
            self.running = False
            print("再见！简易·变易·不易·进化")
        else:
            print(f"未知命令: :{cmd}")

    def _cmd_help(self):
        print("易衍·Evomorph REPL 命令列表:")
        print("  :xiangci <文>  - 将自然语言翻译为卦象指令")
        print("  :compile <码>  - 编译卦象指令行")
        print("  :run           - 运行当前程序")
        print("  :step          - 单步执行")
        print("  :evolve <N>    - 进化N代")
        print("  :explain       - 解释当前指令")
        print("  :yao           - 显示爻位视图")
        print("  :query <问>    - 自然语言查询VM状态")
        print("  :state         - 显示VM完整状态")
        print("  :reset         - 重置VM")
        print("  :quit          - 退出")
        print()
        print("直接输入卦象指令（如: ䷀ CREA R0, R1）也可执行")

    def _cmd_xiangci(self, text: str):
        if not text:
            print("用法: :xiangci <自然语言描述>")
            return
        translation = self.sdk.translate(text)
        print(f"象辞: {translation.original_text}")
        print(f"基因座: {translation.locus_name}")
        print(f"置信度: {translation.confidence:.2f}")
        print("指令:")
        for gene in translation.generated_genes:
            entry = self.isa.get_by_opcode(gene.get("opcode", 0))
            sym = entry["symbol"] if entry else "???"
            mn = gene.get("mnemonic", "???")
            print(f"  {sym} {mn}")
        source = self.sdk.export_to_evo_source(translation)
        print(f"\n.evo 源码:")
        for l in source.split("\n"):
            print(f"  {l}")

    def _cmd_compile(self, code: str):
        if not code:
            print("用法: :compile <卦象指令>")
            return
        try:
            source = f'@locus repl_session {{ mut_rate = 0.02; 卦序: {{ {code} }} }}'
            result = self.compiler.compile(source, output_format="dict")
            loci = result.get("loci", [])
            if loci:
                program = []
                for instr in loci[0].get("instructions", []):
                    program.append({
                        "opcode": instr.get("opcode", 0),
                        "modifier": instr.get("modifier", 0),
                        "operands": [op.get("value", 0) if isinstance(op, dict) else op
                                     for op in instr.get("operands", [])],
                    })
                self.vm.load_program(program)
                self.session_loci["repl"] = loci[0]
                print(f"✓ 编译成功: {len(program)} 条指令")
            else:
                print("✗ 编译结果为空")
        except Exception as e:
            print(f"✗ 编译错误: {e}")

    def _cmd_run(self):
        state = self.vm.run(max_cycles=100000)
        print(f"状态: {state.name}")
        print(f"周期: {self.vm.cycle_count}")
        print(f"能耗: {self.vm.energy_cost:.2f}")

    def _cmd_step(self):
        self.dbg.step_instruction()
        explanation = self.dbg.explain_instruction()
        print(explanation)

    def _cmd_evolve(self, arg: str):
        try:
            gens = int(arg) if arg else 10
        except ValueError:
            gens = 10
        if "repl" not in self.session_loci:
            print("✗ 无当前基因座，请先 :compile")
            return
        locus = self.session_loci["repl"]
        seed_genes = []
        for instr in locus.get("instructions", []):
            gene = GeneInstruction(opcode=instr.get("opcode", 0), modifier=instr.get("modifier", 0))
            seed_genes.append(gene)
        config = EvolutionConfig(population_size=16, max_generations=gens, mut_rate=0.03)
        engine = EvolutionEngine(config=config, platform_simulator=self.sim)
        engine.initialize_population(seed_genes)
        best = engine.evolve()
        if best:
            print(f"✓ 进化完成: 适应度={best.fitness:.4f}, 基因数={len(best.genes)}")

    def _cmd_explain(self):
        explanation = self.dbg.explain_instruction()
        print(explanation)

    def _cmd_yao(self):
        viz = self.dbg.get_yao_visualization()
        print(viz)

    def _cmd_query(self, question: str):
        if not question:
            question = "当前状态如何？"
        response = self.dbg.query_natural_language(question)
        print(response)

    def _cmd_state(self):
        state = self.vm.dump_state()
        print(f"PC: {state['pc']}")
        print(f"状态: {state['state']}")
        print(f"周期: {state['cycle_count']}")
        print(f"能耗: {state['energy_cost']:.2f}")
        print("寄存器:")
        for name, val in state["registers"].items():
            if val != 0:
                print(f"  {name} = {val}")

    def _cmd_reset(self):
        self.vm.reset()
        print("✓ VM 已重置")

    def _handle_evo_input(self, line: str):
        self._cmd_compile(line)


def main():
    repl = EvoREPL()
    repl.run()


if __name__ == "__main__":
    main()
