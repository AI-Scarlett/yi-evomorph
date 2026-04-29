import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evomorph.bootstrap.runtime import EvoRuntime
from evomorph.bootstrap.self_compile import SelfCompiler
from evomorph.compiler import EvocCompiler
from evomorph.evolution.engine import GeneInstruction, Individual, EvolutionConfig, EvolutionEngine
from evomorph.simulator.niche import PlatformSimNiche
from evomorph.hexagrams import HexagramInstructionSet


BOOTSTRAP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "evomorph", "bootstrap"
)


class TestEvoRuntime(unittest.TestCase):
    def setUp(self):
        self.runtime = EvoRuntime()

    def test_load_evo_source(self):
        source = '''@evolang "3.0"

@locus test_runtime {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
        ䷾ SYNC
    }
}'''
        result = self.runtime.load_evo_source(source)
        self.assertIn("loci", result)
        self.assertEqual(len(result["loci"]), 1)
        self.assertEqual(result["loci"][0]["name"], "test_runtime")

    def test_execute_locus(self):
        source = '''@locus exec_test {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
        ䷋ HALT
    }
}'''
        self.runtime.load_evo_source(source)
        result = self.runtime.execute_locus("exec_test", max_cycles=100)
        self.assertEqual(result["locus"], "exec_test")
        self.assertEqual(result["state"], "HALTED")

    def test_evolve_locus(self):
        source = '''@locus evo_test {
    mut_rate = 0.05
    env_target = ["linux-6.x"]
    卦序: {
        ䷀ CREA R0, R1
        ䷌ FELLOWSHIP R0, R1
        ䷾ SYNC
    }
}'''
        self.runtime.load_evo_source(source)
        result = self.runtime.evolve_locus("evo_test", generations=5, population_size=16)
        self.assertIsNotNone(result)
        self.assertIn("best_fitness", result)
        self.assertIn("evolution_history", result)

    def test_bind_env(self):
        self.runtime.bind_env("TEST_INPUT", 42)
        self.assertIn("TEST_INPUT", self.runtime.env_bindings)

    def test_native_handlers(self):
        self.assertIn("print", self.runtime.native_handlers)
        self.assertIn("evolve_locus", self.runtime.native_handlers)
        self.assertIn("compile_source", self.runtime.native_handlers)

    def test_self_compile(self):
        source = '''@locus self_test {
    mut_rate = 0.02
    卦序: {
        ䷁ RECV R0, R1
        ䷾ SYNC
    }
}'''
        result = self.runtime.self_compile(source)
        self.assertIn("loci", result)
        self.assertIn("self_test", self.runtime.loaded_loci)

    def test_bootstrap_pipeline(self):
        source = '''@locus pipe_test {
    mut_rate = 0.05
    env_target = ["linux-6.x"]
    卦序: {
        ䷀ CREA R0, R1
        ䷾ SYNC
    }
}'''
        result = self.runtime.bootstrap_pipeline(source, generations=3)
        self.assertIn("compilation", result)
        self.assertIn("evolution", result)
        self.assertIn("execution", result)

    def test_export_evolved_locus(self):
        source = '''@locus export_test {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
    }
}'''
        self.runtime.load_evo_source(source)
        exported = self.runtime.export_evolved_locus("export_test")
        self.assertIsNotNone(exported)
        self.assertIn("@locus", exported)
        self.assertIn("卦序", exported)


class TestSelfCompiler(unittest.TestCase):
    def test_bootstrap_lexer(self):
        lexer_path = os.path.join(BOOTSTRAP_DIR, "evoc", "lexer.evo")
        if not os.path.exists(lexer_path):
            self.skipTest("lexer.evo not found")
        sc = SelfCompiler()
        result = sc.bootstrap(lexer_path)
        self.assertIn("generation", result)
        self.assertIn("loci_count", result)
        self.assertGreater(result["loci_count"], 0)

    def test_bootstrap_codegen(self):
        codegen_path = os.path.join(BOOTSTRAP_DIR, "evoc", "codegen.evo")
        if not os.path.exists(codegen_path):
            self.skipTest("codegen.evo not found")
        sc = SelfCompiler()
        result = sc.bootstrap(codegen_path)
        self.assertIn("generation", result)
        self.assertGreater(result["loci_count"], 0)


class TestMetaLocusEvolution(unittest.TestCase):
    def test_meta_locus_compilation(self):
        source = '''@meta_locus test_meta {
    mut_rate = 0.01
    fitness  = min_size + max_throughput

    卦序: {
        ䷓ CONTEMPLATE R0
        ䷑ MUT R0, 0x03
        ䷾ SYNC
    }
}'''
        runtime = EvoRuntime()
        result = runtime.load_evo_source(source)
        self.assertIn("meta_loci", result)
        self.assertEqual(len(result["meta_loci"]), 1)

    def test_meta_evolution_evo_file(self):
        evo_path = os.path.join(BOOTSTRAP_DIR, "meta", "evolution.evo")
        if not os.path.exists(evo_path):
            self.skipTest("evolution.evo not found")
        runtime = EvoRuntime()
        result = runtime.load_evo_file(evo_path)
        meta_names = [m["name"] for m in result.get("meta_loci", [])]
        self.assertGreater(len(meta_names), 0)
        self.assertIn("进化之进化.变异算子", meta_names)
        self.assertIn("进化之进化.交叉策略", meta_names)
        self.assertIn("进化之进化.选择策略", meta_names)


class TestBootstrapEndToEnd(unittest.TestCase):
    def test_full_bootstrap_pipeline(self):
        source = '''@evolang "3.0"

@xiangci {
    "自举端到端测试"
}

@locus bootstrap_e2e {
    mut_rate = 0.03
    cross_pool = "test"
    fitness = min_latency + max_throughput
    env_target = ["linux-6.x", "ios-18"]

    卦序: {
        ䷀ CREA R0, R1
        ䷌ FELLOWSHIP R0, R1
        ䷾ SYNC
        ䷁ RECV R2, R0
    }
}

@meta_locus 自举测试.元策略 {
    mut_rate = 0.01
    fitness  = max_throughput

    卦序: {
        ䷓ CONTEMPLATE R0
        ䷑ MUT R0, 0x03
        ䷾ SYNC
    }
}'''
        runtime = EvoRuntime()
        result = runtime.bootstrap_pipeline(source, generations=5)
        self.assertIn("compilation", result)
        self.assertIn("evolution", result)
        self.assertIn("execution", result)
        comp = result["compilation"]
        self.assertEqual(len(comp["loci"]), 1)
        self.assertEqual(len(comp["meta_loci"]), 1)
        evo = result["evolution"]
        self.assertIn("bootstrap_e2e", evo)
        self.assertIn("best_fitness", evo["bootstrap_e2e"])
        exec_result = result["execution"]
        self.assertIn("bootstrap_e2e", exec_result)
        self.assertEqual(exec_result["bootstrap_e2e"]["state"], "HALTED")

    def test_compiler_self_compilation(self):
        source = '''@locus self_comp {
    mut_rate = 0.02
    卦序: {
        ䷁ RECV R0, env::SOURCE
        ䷓ CONTEMPLATE R0
        ䷍ ABUNDANCE R1, R0
        ䷾ SYNC
    }
}'''
        runtime = EvoRuntime()
        step1 = runtime.self_compile(source)
        self.assertIn("self_comp", runtime.loaded_loci)
        step2 = runtime.self_compile(source)
        self.assertIn("self_comp", runtime.loaded_loci)
        locus1 = runtime.loaded_loci["self_comp"]
        self.assertIsNotNone(locus1)


class TestOpcodeYaoConsistency(unittest.TestCase):
    def test_all_opcodes_match_yao(self):
        isa = HexagramInstructionSet()
        for instr in isa.all_instructions():
            opcode = instr["opcode"]
            yao = instr["yao"]
            from_yao = 0
            for i, c in enumerate(yao):
                if c == "⚊":
                    from_yao |= (1 << (5 - i))
            self.assertEqual(opcode, from_yao,
                             f"Opcode {opcode} ({instr['mnemonic']}) doesn't match yao {yao} (expected {from_yao})")

    def test_qian_is_63(self):
        isa = HexagramInstructionSet()
        qian = isa.get_by_mnemonic("CREA")
        self.assertEqual(qian["opcode"], 63)
        self.assertEqual(qian["yao"], "⚊⚊⚊⚊⚊⚊")

    def test_kun_is_0(self):
        isa = HexagramInstructionSet()
        kun = isa.get_by_mnemonic("RECV")
        self.assertEqual(kun["opcode"], 0)
        self.assertEqual(kun["yao"], "⚋⚋⚋⚋⚋⚋")

    def test_jiji_is_21(self):
        isa = HexagramInstructionSet()
        jiji = isa.get_by_mnemonic("SYNC")
        self.assertEqual(jiji["opcode"], 21)

    def test_weiji_is_42(self):
        isa = HexagramInstructionSet()
        weiji = isa.get_by_mnemonic("FUTU")
        self.assertEqual(weiji["opcode"], 42)


if __name__ == "__main__":
    unittest.main()
