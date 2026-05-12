import sys
import os
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evomorph.hexagrams import HexagramInstructionSet
from evomorph.hexagrams import HEXAGRAM_TABLE, HEXAGRAM_CATEGORIES, MODIFIERS
from evomorph.compiler import EvocCompiler
from evomorph.vm.virtual_machine import IChingVM, VMState
from evomorph.evolution.engine import (
    EvolutionEngine, EvolutionConfig, GeneInstruction, Individual,
    SelectionMethod, CrossoverMethod,
)
from evomorph.simulator.niche import PlatformSimNiche, PLATFORM_PROFILES
from tools.yaojing.yaojing import YaoJingDebugger
from evomorph.monitor.evomon import EvoMon, PerformanceSample
from evomorph.hub.repository import EvoHub, LocusPackage
from evomorph.sdk.xiangci import XiangciSDK


class TestHexagramInstructionSet(unittest.TestCase):
    def setUp(self):
        self.isa = HexagramInstructionSet()

    def test_total_instructions(self):
        self.assertEqual(len(HEXAGRAM_TABLE), 64)

    def test_lookup_by_symbol(self):
        qian = self.isa.get_by_symbol("䷀")
        self.assertIsNotNone(qian)
        self.assertEqual(qian["mnemonic"], "CREA")

    def test_lookup_by_mnemonic(self):
        recv = self.isa.get_by_mnemonic("RECV")
        self.assertIsNotNone(recv)
        self.assertEqual(recv["opcode"], 0)

    def test_lookup_by_opcode(self):
        alloc = self.isa.get_by_opcode(17)
        self.assertIsNotNone(alloc)
        self.assertEqual(alloc["mnemonic"], "ALLOC")

    def test_generic_lookup(self):
        self.assertIsNotNone(self.isa.lookup("䷀"))
        self.assertIsNotNone(self.isa.lookup("CREA"))
        self.assertIsNotNone(self.isa.lookup(0x00))

    def test_mutate_opcode(self):
        original = 0b111111
        mutated = self.isa.mutate_opcode(original, 0)
        self.assertEqual(mutated, 0b111110)

    def test_crossover_opcodes(self):
        p1 = 0b111100
        p2 = 0b001111
        c1, c2 = self.isa.crossover_opcodes(p1, p2, 3)
        self.assertEqual(c1, 0b111111)
        self.assertEqual(c2, 0b001100)

    def test_neighbors(self):
        neighbors = self.isa.neighbors(0b000000)
        self.assertEqual(len(neighbors), 6)

    def test_encode_decode(self):
        encoded = self.isa.encode_instruction(0x2B, 0x20)
        decoded = self.isa.decode_instruction(encoded)
        self.assertEqual(decoded[0], 0x2B)
        self.assertEqual(decoded[1], 0x20)

    def test_categories(self):
        for cat_name, opcodes in HEXAGRAM_CATEGORIES.items():
            self.assertEqual(len(opcodes), 16)


# TestLexer 和 TestParser 已移除 — 对应的 lexer.py/parser.py/codegen.py 已在 P1 阶段删除
# 编译路径已 100% 使用 compiler.evob


class TestCompiler(unittest.TestCase):
    def test_compile_simple(self):
        source = '''@evolang "3.0"

@locus hello {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
        ䷾ SYNC
    }
}'''
        compiler = EvocCompiler()
        result = compiler.compile(source, output_format="dict")
        self.assertIn("loci", result)
        self.assertEqual(len(result["loci"]), 1)
        self.assertEqual(result["loci"][0]["name"], "hello")

    def test_compile_evb(self):
        source = '''@locus test {
    卦序: {
        ䷀ CREA
        ䷁ RECV
    }
}'''
        compiler = EvocCompiler()
        evb = compiler.compile(source, output_format="evb")
        self.assertIsInstance(evb, bytes)
        self.assertTrue(evb.startswith(b"EVOB"))


class TestIChingVM(unittest.TestCase):
    def test_vm_init(self):
        vm = IChingVM()
        self.assertEqual(vm.state, VMState.INIT)
        self.assertEqual(vm.pc, 0)

    def test_vm_load_and_run(self):
        vm = IChingVM()
        program = [
            {"opcode": 63, "modifier": 0, "operands": [0, 1]},
            {"opcode": 56, "modifier": 0, "operands": []},
        ]
        vm.load_program(program)
        vm.run(max_cycles=100)
        self.assertEqual(vm.state, VMState.HALTED)

    def test_vm_alloc(self):
        vm = IChingVM()
        program = [
            {"opcode": 17, "modifier": 0, "operands": [0, 4]},
            {"opcode": 56, "modifier": 0, "operands": []},
        ]
        vm.load_program(program)
        vm.run(max_cycles=100)
        self.assertGreater(vm.registers[0], 0)

    def test_vm_dump(self):
        vm = IChingVM()
        dump = vm.dump_state()
        self.assertIn("pc", dump)
        self.assertIn("registers", dump)
        self.assertIn("state", dump)


class TestEvolutionEngine(unittest.TestCase):
    def test_initialize_population(self):
        config = EvolutionConfig(population_size=32, max_generations=10)
        engine = EvolutionEngine(config=config)
        seed = [GeneInstruction(opcode=63), GeneInstruction(opcode=0)]
        pop = engine.initialize_population(seed)
        self.assertEqual(len(pop), 32)

    def test_evolve(self):
        config = EvolutionConfig(
            population_size=16,
            max_generations=5,
            mut_rate=0.05,
        )
        engine = EvolutionEngine(config=config)
        seed = [GeneInstruction(opcode=63), GeneInstruction(opcode=21)]
        engine.initialize_population(seed)
        best = engine.evolve()
        self.assertIsNotNone(best)
        self.assertGreater(len(engine.history), 0)

    def test_mutation(self):
        gene = GeneInstruction(opcode=0b111111)
        ind = Individual(genes=[gene])
        config = EvolutionConfig(mut_rate=1.0)
        engine = EvolutionEngine(config=config)
        mutated = engine.mutate(ind)
        self.assertIsInstance(mutated, Individual)

    def test_crossover(self):
        p1 = Individual(genes=[GeneInstruction(opcode=63), GeneInstruction(opcode=0)])
        p2 = Individual(genes=[GeneInstruction(opcode=21), GeneInstruction(opcode=42)])
        config = EvolutionConfig(crossover_rate=1.0)
        engine = EvolutionEngine(config=config)
        c1, c2 = engine.crossover(p1, p2)
        self.assertIsInstance(c1, Individual)
        self.assertIsInstance(c2, Individual)


class TestPlatformSimNiche(unittest.TestCase):
    def setUp(self):
        self.sim = PlatformSimNiche()

    def test_list_platforms(self):
        platforms = self.sim.list_platforms()
        self.assertGreater(len(platforms), 0)
        self.assertIn("linux-6.x", platforms)

    def test_evaluate(self):
        ind = Individual(genes=[
            GeneInstruction(opcode=63),
            GeneInstruction(opcode=0),
        ])
        score = self.sim.evaluate(ind, "linux-6.x")
        self.assertIsInstance(score, float)

    def test_evaluate_all(self):
        ind = Individual(genes=[GeneInstruction(opcode=63)])
        results = self.sim.evaluate_all_platforms(ind)
        self.assertGreater(len(results), 0)

    def test_simulate_execution(self):
        ind = Individual(genes=[
            GeneInstruction(opcode=63),
            GeneInstruction(opcode=0),
            GeneInstruction(opcode=21),
        ])
        result = self.sim.simulate_execution(ind, "ios-18", input_size=100)
        self.assertIn("total_cycles", result)
        self.assertIn("estimated_latency_ms", result)


class TestYaoJingDebugger(unittest.TestCase):
    def test_add_breakpoint(self):
        dbg = YaoJingDebugger()
        bp_id = dbg.add_address_breakpoint(10)
        self.assertEqual(bp_id, 0)

    def test_step(self):
        vm = IChingVM()
        program = [{"opcode": 56, "modifier": 0, "operands": []}]
        vm.load_program(program)
        dbg = YaoJingDebugger(vm)
        dbg.step_instruction()
        self.assertGreater(dbg.step_count, 0)

    def test_explain_instruction(self):
        vm = IChingVM()
        program = [{"opcode": 63, "modifier": 0, "operands": [0, 1]}]
        vm.load_program(program)
        dbg = YaoJingDebugger(vm)
        explanation = dbg.explain_instruction()
        self.assertIn("CREA", explanation)

    def test_natural_language_query(self):
        dbg = YaoJingDebugger(IChingVM())
        response = dbg.query_natural_language("功耗如何？")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)


class TestEvoMon(unittest.TestCase):
    def test_record_sample(self):
        mon = EvoMon()
        sample = PerformanceSample(
            timestamp=0, function_name="test", latency_ms=50.0
        )
        mon.record_sample(sample)
        self.assertEqual(len(mon.samples), 1)

    def test_hot_path_detection(self):
        mon = EvoMon()
        for i in range(100):
            mon.record_sample(PerformanceSample(
                timestamp=i, function_name="hot_func", latency_ms=200.0
            ))
        hot = mon.get_hot_paths()
        self.assertGreater(len(hot), 0)

    def test_evolution_suggestion(self):
        mon = EvoMon()
        for i in range(50):
            mon.record_sample(PerformanceSample(
                timestamp=i, function_name="slow_func", latency_ms=500.0
            ))
        suggestions = mon.suggest_evolution()
        self.assertGreater(len(suggestions), 0)

    def test_report(self):
        mon = EvoMon()
        report = mon.generate_report()
        self.assertIn("uptime_seconds", report)
        self.assertIn("total_samples", report)


class TestEvoHub(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmpdir = tempfile.mkdtemp()
        self.hub = EvoHub(repo_path=self.tmpdir)

    def test_publish_and_pull(self):
        pkg = LocusPackage(name="test_pkg", version="1.0.0",
                           genes_data=[{"opcode": 63}])
        self.hub.publish(pkg)
        pulled = self.hub.pull("test_pkg")
        self.assertIsNotNone(pulled)
        self.assertEqual(pulled.name, "test_pkg")

    def test_search(self):
        pkg = LocusPackage(name="my_parallel_lib", version="1.0.0")
        self.hub.publish(pkg)
        results = self.hub.search("parallel")
        self.assertGreater(len(results), 0)

    def test_fitness_upload(self):
        self.hub.upload_fitness_data("test_pkg", "linux-6.x", 85.5)
        history = self.hub.get_fitness_history("test_pkg")
        self.assertEqual(len(history), 1)


class TestXiangciSDK(unittest.TestCase):
    def test_translate(self):
        sdk = XiangciSDK()
        result = sdk.translate("并行求和，适安卓与视窗")
        self.assertIsNotNone(result)
        self.assertGreater(len(result.generated_genes), 0)
        self.assertGreater(result.confidence, 0)

    def test_export_evo_source(self):
        sdk = XiangciSDK()
        result = sdk.translate("创建一个进程")
        source = sdk.export_to_evo_source(result)
        self.assertIn("@locus", source)
        self.assertIn("卦序", source)

    def test_prompt_generation(self):
        sdk = XiangciSDK()
        prompt = sdk.get_prompt_for_llm("分治求和")
        self.assertIn("象辞编译器", prompt)
        self.assertIn("分治求和", prompt)

    def test_stats(self):
        sdk = XiangciSDK()
        sdk.translate("测试1")
        sdk.translate("测试2")
        stats = sdk.get_translation_stats()
        self.assertEqual(stats["total_translations"], 2)


class TestEndToEnd(unittest.TestCase):
    def test_full_pipeline(self):
        source = '''@evolang "3.0"

@locus e2e_test {
    mut_rate = 0.05
    cross_pool = "test"
    fitness = min_latency + max_throughput
    env_target = ["linux-6.x", "ios-18"]
    max_generations = 10

    卦序: {
        ䷀ CREA R0, R1
        ䷌ FELLOWSHIP R0, R1
        ䷾ SYNC
        ䷁ RECV R2, R0
    }
}'''
        compiler = EvocCompiler()
        result = compiler.compile(source, output_format="dict")
        self.assertIn("loci", result)
        locus = result["loci"][0]
        self.assertEqual(locus["name"], "e2e_test")

        seed_genes = []
        for instr in locus.get("instructions", []):
            gene = GeneInstruction(
                opcode=instr.get("opcode", 0),
                modifier=instr.get("modifier", 0),
            )
            seed_genes.append(gene)

        sim = PlatformSimNiche()
        config = EvolutionConfig(
            population_size=16,
            max_generations=5,
            mut_rate=0.05,
            env_targets=["linux-6.x", "ios-18"],
        )
        engine = EvolutionEngine(config=config, platform_simulator=sim)
        engine.initialize_population(seed_genes)
        best = engine.evolve()
        self.assertIsNotNone(best)
        self.assertGreater(len(engine.history), 0)

        vm = IChingVM()
        vm.load_program([{"opcode": g.opcode, "modifier": g.modifier,
                          "operands": list(g.operands)} for g in best.genes])
        vm.run(max_cycles=1000)
        self.assertIn(vm.state, [VMState.HALTED, VMState.PAUSED, VMState.RUNNING])

        dbg = YaoJingDebugger(vm)
        explanation = dbg.explain_instruction()
        self.assertIsInstance(explanation, str)


if __name__ == "__main__":
    unittest.main()
