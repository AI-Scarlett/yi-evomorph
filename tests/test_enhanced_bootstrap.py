#!/usr/bin/env python3
"""
综合测试脚本 - 验证增强自举模块的所有功能

测试内容:
1. 第2代编译器接口测试
2. 进化优化功能测试
3. 一致性验证测试
4. 最小可信计算基测试
"""

import sys
import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from evomorph.bootstrap.enhanced_bootstrap import (
    EnhancedBootstrap,
    CompilerGeneration,
    CompilationResult,
    ConsistencyReport,
    EvolutionReport,
    TCBReport,
)
from evomorph.bootstrap.enhanced_bootstrap import main as eb_main


class TestCompilerGenerations(unittest.TestCase):
    """测试各代编译器接口"""
    
    def setUp(self):
        self.eb = EnhancedBootstrap()
        
        self.test_program = '''@evolang "3.0"

@xiangci {
    "测试程序"
}

@locus test.simple {
    mut_rate   = 0.01
    cross_pool = "test"
    fitness    = min_latency
    env_target = ["linux-6.x"]

    卦序: {
        ䷂ ALLOC R0, 0x10
        ䷍ ABUNDANCE R0, 0x05
        ䷾ SYNC
    }
}
'''

    def test_gen0_compiler_available(self):
        """测试第0代编译器（Python）可用"""
        result = self.eb.compile_with_gen0(self.test_program)
        
        self.assertTrue(result.success)
        self.assertEqual(result.generation, "gen0")
        self.assertGreater(len(result.loci), 0)
    
    def test_compile_with_auto_generation(self):
        """测试自动选择编译器代次"""
        result = self.eb.compile(self.test_program, generation="auto")
        
        self.assertTrue(result.success)
        self.assertIn(result.generation, ["gen0", "gen1", "gen2"])
    
    def test_compile_batch(self):
        """测试批量编译"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.evo', delete=False) as f:
            f.write(self.test_program)
            temp_path1 = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.evo', delete=False) as f:
            f.write(self.test_program)
            temp_path2 = f.name
        
        try:
            results = self.eb.compile_batch([temp_path1, temp_path2], generation="gen0")
            
            self.assertEqual(len(results), 2)
            for path, result in results.items():
                self.assertTrue(result.success)
        finally:
            os.unlink(temp_path1)
            os.unlink(temp_path2)
    
    def test_compile_file_path(self):
        """测试编译文件路径"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.evo', delete=False) as f:
            f.write(self.test_program)
            temp_path = f.name
        
        try:
            result = self.eb.compile(temp_path, generation="gen0")
            self.assertTrue(result.success)
            self.assertGreater(len(result.loci), 0)
        finally:
            os.unlink(temp_path)
    
    def test_compilation_result_structure(self):
        """测试编译结果结构"""
        result = self.eb.compile_with_gen0(self.test_program)
        
        self.assertIsInstance(result.success, bool)
        self.assertIsInstance(result.generation, str)
        self.assertIsInstance(result.loci, list)
        self.assertIsInstance(result.meta_loci, list)
        self.assertIsInstance(result.metrics, dict)
        
        if result.success:
            self.assertIn("loci_count", result.metrics)


class TestEvolutionOptimization(unittest.TestCase):
    """测试进化优化功能"""
    
    def setUp(self):
        self.eb = EnhancedBootstrap()
        
        test_locus = {
            "name": "test.evolution",
            "mut_rate": 0.02,
            "env_targets": ["linux-6.x"],
            "instructions": [
                {"opcode": 17, "modifier": 0, "mnemonic": "ALLOC", "operands": [0, 16]},
                {"opcode": 47, "modifier": 0, "mnemonic": "ABUNDANCE", "operands": [0, 5]},
                {"opcode": 21, "modifier": 0, "mnemonic": "SYNC", "operands": []},
            ]
        }
        self.eb.runtime.loaded_loci["test.evolution"] = test_locus
    
    def test_evolution_configs_exist(self):
        """测试进化配置存在"""
        self.assertIn("quick", self.eb.evolution_configs)
        self.assertIn("standard", self.eb.evolution_configs)
        self.assertIn("deep", self.eb.evolution_configs)
        self.assertIn("extreme", self.eb.evolution_configs)
    
    def test_evolve_locus_quick_mode(self):
        """测试快速进化模式"""
        report = self.eb.evolve_locus_enhanced("test.evolution", mode="quick")
        
        self.assertIsInstance(report, EvolutionReport)
        self.assertGreater(report.generations, 0)
        self.assertIsInstance(report.initial_fitness, float)
        self.assertIsInstance(report.final_fitness, float)
        self.assertIsInstance(report.improvement_rate, float)
        self.assertIsInstance(report.history, list)
    
    def test_custom_evolution_config(self):
        """测试自定义进化配置"""
        custom_config = {
            "population_size": 8,
            "max_generations": 5,
            "mut_rate": 0.05,
        }
        
        report = self.eb.evolve_locus_enhanced(
            "test.evolution",
            mode="custom",
            custom_config=custom_config
        )
        
        self.assertIsInstance(report, EvolutionReport)
        self.assertGreater(report.generations, 0)
    
    def test_evolve_nonexistent_locus(self):
        """测试进化不存在的基因座"""
        report = self.eb.evolve_locus_enhanced("nonexistent.locus", mode="quick")
        
        self.assertEqual(report.generations, 0)
        self.assertEqual(report.initial_fitness, 0.0)
        self.assertEqual(report.final_fitness, 0.0)
    
    def test_evolution_report_structure(self):
        """测试进化报告结构"""
        report = self.eb.evolve_locus_enhanced("test.evolution", mode="quick")
        
        self.assertIsInstance(report.generations, int)
        self.assertIsInstance(report.initial_fitness, float)
        self.assertIsInstance(report.final_fitness, float)
        self.assertIsInstance(report.improvement_rate, float)
        self.assertIsInstance(report.history, list)


class TestConsistencyVerification(unittest.TestCase):
    """测试一致性验证功能"""
    
    def setUp(self):
        self.eb = EnhancedBootstrap()
        
        self.test_program = '''@evolang "3.0"

@locus test.consistency {
    mut_rate   = 0.01
    fitness    = min_latency
    env_target = ["linux-6.x"]

    卦序: {
        ䷂ ALLOC R0, 0x10
        ䷾ SYNC
    }
}
'''
    
    def test_verify_consistency_returns_report(self):
        """测试一致性验证返回报告"""
        report = self.eb.verify_consistency(self.test_program, verbose=False)
        
        self.assertIsInstance(report, ConsistencyReport)
        self.assertIsInstance(report.gen1_result, CompilationResult)
        self.assertIsInstance(report.gen2_result, CompilationResult)
        self.assertIsInstance(report.match_percentage, float)
        self.assertIsInstance(report.differences, list)
        self.assertIsInstance(report.is_consistent, bool)
    
    def test_verify_batch_consistency(self):
        """测试批量一致性验证"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.evo', delete=False) as f:
            f.write(self.test_program)
            temp_path = f.name
        
        try:
            reports = self.eb.verify_batch_consistency([temp_path], verbose=False)
            
            self.assertEqual(len(reports), 1)
            for path, report in reports.items():
                self.assertIsInstance(report, ConsistencyReport)
        finally:
            os.unlink(temp_path)
    
    def test_consistency_report_structure(self):
        """测试一致性报告结构"""
        report = self.eb.verify_consistency(self.test_program, verbose=False)
        
        self.assertIsInstance(report.gen1_result, CompilationResult)
        self.assertIsInstance(report.gen2_result, CompilationResult)
        self.assertGreaterEqual(report.match_percentage, 0.0)
        self.assertLessEqual(report.match_percentage, 100.0)
        self.assertIsInstance(report.differences, list)
        self.assertIsInstance(report.is_consistent, bool)


class TestTrustedComputingBase(unittest.TestCase):
    """测试最小可信计算基功能"""
    
    def setUp(self):
        self.eb = EnhancedBootstrap()
    
    def test_check_tcb_status(self):
        """测试检查TCB状态"""
        status = self.eb.check_tcb_status()
        
        self.assertIsInstance(status, TCBReport)
        self.assertIsInstance(status.c_vm_available, bool)
        self.assertIsInstance(status.assembler_available, bool)
        self.assertIsInstance(status.can_execute_raw, bool)
        self.assertIsInstance(status.bootstrap_test_result, dict)
        self.assertIsInstance(status.is_fully_independent, bool)
    
    def test_tcb_report_structure(self):
        """测试TCB报告结构"""
        status = self.eb.check_tcb_status()
        
        self.assertIsInstance(status.c_vm_available, bool)
        self.assertIsInstance(status.c_vm_path, str)
        self.assertIsInstance(status.assembler_available, bool)
        self.assertIsInstance(status.can_execute_raw, bool)
        self.assertIsInstance(status.bootstrap_test_result, dict)
        self.assertIsInstance(status.is_fully_independent, bool)
    
    def test_compile_for_tcb_generates_asm(self):
        """测试为TCB编译生成汇编文件"""
        test_program = '''@evolang "3.0"

@locus test.tcb {
    mut_rate   = 0.01
    fitness    = min_latency
    env_target = ["linux-6.x"]

    卦序: {
        ䷶ ABOUND R0, 5
        ䷶ ABOUND R1, 10
        ䷩ INCREASE R0, R1
        ䷋ HALT
    }
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as f:
            temp_asm = f.name
        
        try:
            result = self.eb.compile_for_tcb(test_program, temp_asm, verbose=False)
            
            self.assertTrue(result["success"])
            self.assertIn("asm_file", result)
            self.assertTrue(os.path.exists(temp_asm))
            
            with open(temp_asm, 'r', encoding='utf-8') as f:
                asm_content = f.read()
            
            self.assertIn("ABOUND", asm_content)
            self.assertIn("INCREASE", asm_content)
            self.assertIn("HALT", asm_content)
        finally:
            if os.path.exists(temp_asm):
                os.unlink(temp_asm)


class TestSystemStatus(unittest.TestCase):
    """测试系统状态查询"""
    
    def setUp(self):
        self.eb = EnhancedBootstrap()
    
    def test_get_status_returns_dict(self):
        """测试获取状态返回字典"""
        status = self.eb.get_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn("generations", status)
        self.assertIn("tcb", status)
        self.assertIn("loaded_loci", status)
        self.assertIn("evolution_modes", status)
    
    def test_generations_status(self):
        """测试各代编译器状态"""
        status = self.eb.get_status()
        gens = status["generations"]
        
        self.assertIn("gen0", gens)
        self.assertIn("gen1", gens)
        self.assertIn("gen2", gens)
        
        self.assertTrue(gens["gen0"]["available"])
        self.assertIsInstance(gens["gen1"]["available"], bool)
        self.assertIsInstance(gens["gen2"]["available"], bool)


class TestCommandLineInterface(unittest.TestCase):
    """测试命令行接口"""
    
    def setUp(self):
        self.test_program = '''@evolang "3.0"

@locus test.cli {
    mut_rate   = 0.01
    fitness    = min_latency
    env_target = ["linux-6.x"]

    卦序: {
        ䷶ ABOUND R0, 42
        ䷋ HALT
    }
}
'''
    
    def test_cli_help(self):
        """测试CLI帮助"""
        with patch('sys.argv', ['enhanced_bootstrap', '--help']):
            with patch('sys.stdout.write'):
                try:
                    eb_main()
                except SystemExit as e:
                    self.assertEqual(e.code, 0)
    
    def test_cli_status_command(self):
        """测试CLI状态命令"""
        with patch('sys.argv', ['enhanced_bootstrap', 'status']):
            try:
                eb_main()
            except SystemExit as e:
                self.assertEqual(e.code, 0)
    
    def test_cli_compile_command(self):
        """测试CLI编译命令"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.evo', delete=False) as f:
            f.write(self.test_program)
            temp_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            with patch('sys.argv', [
                'enhanced_bootstrap', 'compile',
                temp_path,
                '-g', 'gen0',
                '-o', output_path,
                '-v'
            ]):
                try:
                    eb_main()
                except SystemExit as e:
                    self.assertEqual(e.code, 0)
            
            self.assertTrue(os.path.exists(output_path))
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_cli_tcb_status_command(self):
        """测试CLI TCB状态命令"""
        with patch('sys.argv', ['enhanced_bootstrap', 'tcb', 'status', '-v']):
            try:
                eb_main()
            except SystemExit as e:
                self.assertEqual(e.code, 0)


def run_tests():
    """运行所有测试"""
    print("=" * 70)
    print("易衍·Evomorph 增强自举模块测试")
    print("=" * 70)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestCompilerGenerations))
    suite.addTests(loader.loadTestsFromTestCase(TestEvolutionOptimization))
    suite.addTests(loader.loadTestsFromTestCase(TestConsistencyVerification))
    suite.addTests(loader.loadTestsFromTestCase(TestTrustedComputingBase))
    suite.addTests(loader.loadTestsFromTestCase(TestSystemStatus))
    suite.addTests(loader.loadTestsFromTestCase(TestCommandLineInterface))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    print(f"  运行测试: {result.testsRun}")
    print(f"  成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  失败: {len(result.failures)}")
    print(f"  错误: {len(result.errors)}")
    
    if result.failures:
        print("\n失败详情:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback[:100]}...")
    
    if result.errors:
        print("\n错误详情:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback[:100]}...")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
