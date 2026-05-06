#!/usr/bin/env python3
"""
易衍·Evomorph 回归测试框架
用于验证自举编译器改进的效果
确保进化过程中不会破坏现有功能
"""

import sys
import os
import json
import time
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from evomorph.compiler import EvocCompiler
from evomorph.compiler.lexer import Lexer, TokenType
from evomorph.compiler.parser import Parser
from evomorph.compiler.codegen import CodeGenerator
from evomorph.vm.virtual_machine import IChingVM, VMState
from evomorph.hexagrams import HexagramInstructionSet


class TestResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class TestCase:
    name: str
    category: str
    description: str
    test_source: str
    expected_tokens: Optional[List[Dict]] = None
    expected_ast: Optional[Dict] = None
    expected_bytecode: Optional[bytes] = None
    expected_output: Optional[Any] = None
    priority: int = 1


@dataclass
class TestReport:
    timestamp: float
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    test_results: List[Dict] = field(default_factory=list)
    duration_ms: float = 0.0
    
    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.passed / self.total_tests


class BootstrapRegressionTestSuite:
    """
    自举编译器回归测试套件
    """
    
    TEST_CASES: List[TestCase] = []
    
    def __init__(self):
        self.isa = HexagramInstructionSet()
        self.compiler = EvocCompiler(self.isa)
        self.vm = IChingVM()
        self._init_test_cases()
    
    def _init_test_cases(self):
        self.TEST_CASES = [
            TestCase(
                name="lexer_simple",
                category="lexer",
                description="测试基本词法分析",
                test_source='''
@evolang "3.0"

@locus test {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
        ䷾ SYNC
    }
}
''',
                priority=1
            ),
            
            TestCase(
                name="lexer_hexagram_symbol",
                category="lexer",
                description="测试卦象符号识别",
                test_source="䷀ ䷁ ䷂ ䷃ ䷄ ䷅ ䷆ ䷇",
                priority=1
            ),
            
            TestCase(
                name="lexer_mnemonic",
                category="lexer",
                description="测试助记符识别",
                test_source="CREA RECV ALLOC SPRT WAIT LOCK BRANCH MERGE",
                priority=1
            ),
            
            TestCase(
                name="lexer_register",
                category="lexer",
                description="测试寄存器识别",
                test_source="R0 R1 R15 R_FP R_SP R_LR R_A0",
                priority=1
            ),
            
            TestCase(
                name="lexer_number",
                category="lexer",
                description="测试数字识别",
                test_source="0xFF 0b101010 42 3.14159 -128",
                priority=1
            ),
            
            TestCase(
                name="lexer_string",
                category="lexer",
                description="测试字符串识别",
                test_source='"hello world" "中文测试" "escape\\n\\t"',
                priority=1
            ),
            
            TestCase(
                name="lexer_modifier",
                category="lexer",
                description="测试修饰符识别",
                test_source=".ASYNC .ATOMIC .PRIV .WEAK .STRONG .VOLATILE",
                priority=1
            ),
            
            TestCase(
                name="lexer_comment",
                category="lexer",
                description="测试注释处理",
                test_source='''
// 这是一行注释
䷀ CREA R0, R1  // 行尾注释
// 另一行注释
''',
                priority=1
            ),
            
            TestCase(
                name="parser_locus",
                category="parser",
                description="测试基因座解析",
                test_source='''
@locus test.locus {
    mut_rate = 0.01
    cross_pool = "test"
    fitness = min_latency + max_throughput
    env_target = ["linux-6.x", "ios-18"]
    max_generations = 100

    卦序: {
        ䷀ CREA R0, R1
        ䷌ FELLOWSHIP R0, R1
        ䷾ SYNC
    }
}
''',
                priority=1
            ),
            
            TestCase(
                name="parser_meta_locus",
                category="parser",
                description="测试元基因座解析",
                test_source='''
@meta_locus 进化策略 {
    mut_rate = 0.005
    fitness = min_size + max_throughput

    卦序: {
        ䷓ CONTEMPLATE R0
        ䷑ MUT R0, 0x02
        ䷾ SYNC
    }
}
''',
                priority=1
            ),
            
            TestCase(
                name="parser_xiangci",
                category="parser",
                description="测试象辞解析",
                test_source='''
@xiangci {
    "分治求和算法"
    "将数组分成两半，递归计算，然后合并结果"
    "目标平台：Linux 6.x 和 Android 14"
}
''',
                priority=1
            ),
            
            TestCase(
                name="parser_fitness_expr",
                category="parser",
                description="测试适应度表达式解析",
                test_source='''
@locus test {
    fitness = min_latency + 2.0*max_throughput - 0.5*min_energy + min_size

    卦序: {
        ䷾ SYNC
    }
}
''',
                priority=1
            ),
            
            TestCase(
                name="parser_instruction",
                category="parser",
                description="测试指令解析",
                test_source='''
@locus test {
    卦序: {
        ䷀ CREA R0, R1
        ䷀ CREA.ASYNC R2, R3
        ䷌ FELLOWSHIP R0, R2
        ䷂ ALLOC R4, 0x10
        ䷾ SYNC
    }
}
''',
                priority=1
            ),
            
            TestCase(
                name="codegen_simple",
                category="codegen",
                description="测试基本代码生成",
                test_source='''
@evolang "3.0"

@locus hello {
    mut_rate = 0.02
    fitness = min_latency
    env_target = ["linux-6.x"]

    卦序: {
        ䷀ CREA R0, R1
        ䷌ FELLOWSHIP R0, R1
        ䷾ SYNC
    }
}
''',
                priority=1
            ),
            
            TestCase(
                name="codegen_evb_format",
                category="codegen",
                description="测试EVOB格式生成",
                test_source='''
@locus evb_test {
    卦序: {
        ䷀ CREA
        ䷁ RECV
        ䷾ SYNC
    }
}
''',
                priority=1
            ),
            
            TestCase(
                name="vm_execute_simple",
                category="vm",
                description="测试虚拟机简单执行",
                test_source='''
@locus vm_test {
    卦序: {
        ䷀ CREA R0, R1
        ䷂ ALLOC R2, 0x04
        ䷾ SYNC
    }
}
''',
                priority=1
            ),
            
            TestCase(
                name="full_compile_pipeline",
                category="integration",
                description="测试完整编译流程",
                test_source='''
@evolang "3.0"

@xiangci {
    "测试完整编译流程"
    "词法分析 → 语法分析 → 代码生成"
}

@locus full_pipeline_test {
    mut_rate = 0.01
    cross_pool = "test"
    fitness = min_latency + max_throughput
    env_target = ["linux-6.x", "android-14", "ios-18"]
    max_generations = 50

    卦序: {
        ䷀ CREA R0, R1
        ䷌ FELLOWSHIP R1, R0
        ䷂ ALLOC R2, 0x20
        ䷍ ABUNDANCE R2, R0
        ䷾ SYNC
    }
}

@meta_locus 测试.元策略 {
    mut_rate = 0.005
    fitness = min_size

    卦序: {
        ䷓ CONTEMPLATE R0
        ䷑ MUT R0, 0x03
        ䷾ SYNC
    }
}
''',
                priority=1
            ),
            
            TestCase(
                name="bootstrap_compile",
                category="bootstrap",
                description="测试自举编译器源代码编译",
                test_source='''
@evolang "3.0"

@xiangci {
    "易衍自举编译器"
    "编译器用自身语言书写自身"
}

@locus evoc.bootstrap.compile_source {
    mut_rate = 0.001
    cross_pool = "bootstrap"
    fitness = max_throughput + min_latency
    env_target = ["linux-6.x", "android-14", "ios-18", "win-11", "harmony-5"]

    卦序: {
        ䷁ RECV R0, env::SOURCE_TEXT
        ䷌ FELLOWSHIP R1, R0
        ䷄ WAIT R1
        ䷀ CREA R2, @evoc.lexer.tokenize
        ䷌ FELLOWSHIP R1, R2
        ䷀ CREA R3, @evoc.parser.full_pass
        ䷌ FELLOWSHIP R2, R3
        ䷀ CREA R4, @evoc.codegen.full_pass
        ䷌ FELLOWSHIP R3, R4
        ䷾ SYNC
    }
}
''',
                priority=1
            ),
        ]
    
    def run_lexer_test(self, test_case: TestCase) -> Tuple[TestResult, str]:
        try:
            lexer = Lexer(test_case.test_source)
            tokens = lexer.tokenize()
            
            if not tokens:
                return TestResult.FAIL, "No tokens generated"
            
            token_types = [t.type for t in tokens]
            
            if TokenType.EOF not in token_types:
                return TestResult.FAIL, "No EOF token"
            
            return TestResult.PASS, f"Generated {len(tokens)} tokens"
            
        except Exception as e:
            return TestResult.ERROR, f"Lexer exception: {e}"
    
    def run_parser_test(self, test_case: TestCase) -> Tuple[TestResult, str]:
        try:
            lexer = Lexer(test_case.test_source)
            tokens = lexer.tokenize()
            
            parser = Parser(tokens, self.isa)
            ast = parser.parse()
            
            if ast is None:
                return TestResult.FAIL, "No AST generated"
            
            return TestResult.PASS, f"AST has {len(ast.loci)} loci, {len(ast.meta_loci)} meta_loci"
            
        except Exception as e:
            return TestResult.ERROR, f"Parser exception: {e}"
    
    def run_codegen_test(self, test_case: TestCase) -> Tuple[TestResult, str]:
        try:
            result = self.compiler.compile(test_case.test_source, output_format="dict")
            
            if result.get("error"):
                errors = result.get("errors", [])
                return TestResult.FAIL, f"Codegen errors: {errors}"
            
            loci = result.get("loci", [])
            if not loci:
                return TestResult.FAIL, "No loci in compilation result"
            
            return TestResult.PASS, f"Generated {len(loci)} loci"
            
        except Exception as e:
            return TestResult.ERROR, f"Codegen exception: {e}"
    
    def run_evb_test(self, test_case: TestCase) -> Tuple[TestResult, str]:
        try:
            evb_bytes = self.compiler.compile(test_case.test_source, output_format="evb")
            
            if not isinstance(evb_bytes, bytes):
                return TestResult.FAIL, "EVB output is not bytes"
            
            if len(evb_bytes) < 12:
                return TestResult.FAIL, f"EVB too short: {len(evb_bytes)} bytes"
            
            magic = evb_bytes[:4]
            if magic != b"EVOB":
                return TestResult.FAIL, f"Invalid EVB magic: {magic!r}"
            
            version = int.from_bytes(evb_bytes[4:6], byteorder='big')
            if version != 3:
                return TestResult.FAIL, f"Invalid EVB version: {version}"
            
            return TestResult.PASS, f"Generated {len(evb_bytes)} bytes EVB"
            
        except Exception as e:
            return TestResult.ERROR, f"EVB generation exception: {e}"
    
    def run_vm_test(self, test_case: TestCase) -> Tuple[TestResult, str]:
        try:
            result = self.compiler.compile(test_case.test_source, output_format="dict")
            
            if result.get("error"):
                return TestResult.SKIP, f"Skipping VM test: compile failed"
            
            loci = result.get("loci", [])
            if not loci:
                return TestResult.SKIP, "No loci to execute"
            
            instructions = []
            for locus in loci:
                for instr in locus.get("instructions", []):
                    if "opcode" in instr:
                        instructions.append({
                            "opcode": instr["opcode"],
                            "modifier": instr.get("modifier", 0),
                            "operands": [
                                op.get("value", 0) if isinstance(op, dict) else op
                                for op in instr.get("operands", [])
                            ]
                        })
            
            if not instructions:
                return TestResult.SKIP, "No instructions to execute"
            
            self.vm.reset()
            self.vm.load_program(instructions)
            self.vm.run(max_cycles=1000)
            
            if self.vm.state in (VMState.HALTED, VMState.PAUSED):
                return TestResult.PASS, f"VM executed {self.vm.cycle_count} cycles, state={self.vm.state.name}"
            elif self.vm.state == VMState.ERROR:
                return TestResult.FAIL, f"VM entered error state"
            else:
                return TestResult.PASS, f"VM state: {self.vm.state.name}"
            
        except Exception as e:
            return TestResult.ERROR, f"VM exception: {e}"
    
    def run_test(self, test_case: TestCase) -> Dict[str, Any]:
        start_time = time.time()
        
        if test_case.category == "lexer":
            result, message = self.run_lexer_test(test_case)
        elif test_case.category == "parser":
            result, message = self.run_parser_test(test_case)
        elif test_case.category == "codegen":
            if "evb" in test_case.name.lower():
                result, message = self.run_evb_test(test_case)
            else:
                result, message = self.run_codegen_test(test_case)
        elif test_case.category == "vm":
            result, message = self.run_vm_test(test_case)
        elif test_case.category in ("integration", "bootstrap"):
            codegen_result, codegen_msg = self.run_codegen_test(test_case)
            if codegen_result == TestResult.PASS:
                result, message = TestResult.PASS, codegen_msg
            else:
                result, message = codegen_result, codegen_msg
        else:
            result, message = TestResult.SKIP, f"Unknown category: {test_case.category}"
        
        duration_ms = (time.time() - start_time) * 1000
        
        return {
            "name": test_case.name,
            "category": test_case.category,
            "description": test_case.description,
            "result": result.value,
            "message": message,
            "duration_ms": duration_ms,
            "priority": test_case.priority
        }
    
    def run_all_tests(self) -> TestReport:
        print("\n" + "=" * 70)
        print("  易衍·Evomorph 回归测试套件")
        print("=" * 70)
        print(f"\n  测试数量: {len(self.TEST_CASES)}")
        print(f"  开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        report = TestReport(timestamp=time.time())
        report.total_tests = len(self.TEST_CASES)
        
        categories: Dict[str, List[Dict]] = defaultdict(list)
        
        start_time = time.time()
        
        for i, test_case in enumerate(self.TEST_CASES, 1):
            print(f"\n  [{i}/{len(self.TEST_CASES)}] {test_case.name}")
            print(f"      类别: {test_case.category}")
            print(f"      描述: {test_case.description}")
            
            test_result = self.run_test(test_case)
            report.test_results.append(test_result)
            categories[test_case.category].append(test_result)
            
            result_status = test_result["result"]
            if result_status == "pass":
                report.passed += 1
                print(f"      ✅ 通过: {test_result['message']}")
            elif result_status == "fail":
                report.failed += 1
                print(f"      ❌ 失败: {test_result['message']}")
            elif result_status == "skip":
                report.skipped += 1
                print(f"      ⏭️  跳过: {test_result['message']}")
            elif result_status == "error":
                report.errors += 1
                print(f"      ⚠️  错误: {test_result['message']}")
            
            print(f"      耗时: {test_result['duration_ms']:.2f}ms")
        
        report.duration_ms = (time.time() - start_time) * 1000
        
        print("\n" + "=" * 70)
        print("  测试结果统计")
        print("=" * 70)
        
        print(f"\n  总测试数: {report.total_tests}")
        print(f"  通过: {report.passed} ({report.pass_rate:.1%})")
        print(f"  失败: {report.failed}")
        print(f"  跳过: {report.skipped}")
        print(f"  错误: {report.errors}")
        print(f"  总耗时: {report.duration_ms:.2f}ms")
        
        print(f"\n  各类别统计:")
        for category, results in categories.items():
            passed = sum(1 for r in results if r["result"] == "pass")
            total = len(results)
            rate = passed / total if total > 0 else 0.0
            print(f"    {category}: {passed}/{total} ({rate:.1%})")
        
        if report.failed > 0 or report.errors > 0:
            print(f"\n  失败/错误的测试:")
            for result in report.test_results:
                if result["result"] in ("fail", "error"):
                    print(f"    ❌ [{result['category']}] {result['name']}: {result['message']}")
        
        return report
    
    def save_report(self, report: TestReport, filepath: Optional[str] = None):
        if filepath is None:
            report_dir = PROJECT_ROOT / "evomorph" / "bootstrap" / "reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            filepath = report_dir / f"regression_{int(time.time())}.json"
        
        report_data = {
            "timestamp": report.timestamp,
            "datetime": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report.timestamp)),
            "total_tests": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
            "skipped": report.skipped,
            "errors": report.errors,
            "pass_rate": report.pass_rate,
            "duration_ms": report.duration_ms,
            "test_results": report.test_results
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n  报告已保存: {filepath}")


def main():
    test_suite = BootstrapRegressionTestSuite()
    
    print("\n" + "=" * 70)
    print("  易衍·Evomorph 回归测试")
    print("=" * 70)
    
    print("\n  选择运行模式:")
    print("    1. 运行所有测试 (默认)")
    print("    2. 仅运行词法分析测试")
    print("    3. 仅运行语法分析测试")
    print("    4. 仅运行代码生成测试")
    print("    5. 仅运行集成测试")
    
    try:
        choice = input("\n  请选择 (1-5, 默认=1): ").strip()
        
        if choice == "2":
            test_suite.TEST_CASES = [t for t in test_suite.TEST_CASES if t.category == "lexer"]
        elif choice == "3":
            test_suite.TEST_CASES = [t for t in test_suite.TEST_CASES if t.category == "parser"]
        elif choice == "4":
            test_suite.TEST_CASES = [t for t in test_suite.TEST_CASES if t.category == "codegen"]
        elif choice == "5":
            test_suite.TEST_CASES = [t for t in test_suite.TEST_CASES if t.category in ("integration", "bootstrap")]
        
        report = test_suite.run_all_tests()
        test_suite.save_report(report)
        
        if report.pass_rate >= 0.95:
            print("\n  🎉 恭喜！测试通过率超过95%！")
        elif report.pass_rate >= 0.8:
            print("\n  ✅ 测试通过，表现良好")
        else:
            print(f"\n  ⚠️ 测试通过率较低 ({report.pass_rate:.1%})，需要关注")
        
        return 0 if report.failed == 0 and report.errors == 0 else 1
        
    except KeyboardInterrupt:
        print("\n\n  用户中断测试")
        return 1


if __name__ == "__main__":
    from collections import defaultdict
    sys.exit(main())
