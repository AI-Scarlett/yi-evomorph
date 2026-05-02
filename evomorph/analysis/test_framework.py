import copy
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set, Any, Callable, Union
from collections import defaultdict


class TestResult(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"


class TestCategory(Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    REGRESSION = "regression"
    PERFORMANCE = "performance"
    SECURITY = "security"
    EVOLUTION = "evolution"


@dataclass
class TestCase:
    name: str
    description: str = ""
    category: TestCategory = TestCategory.UNIT
    timeout_seconds: float = 5.0
    enabled: bool = True
    tags: Set[str] = field(default_factory=set)
    
    expected_output: Optional[Dict[str, Any]] = None
    input_values: Dict[str, Any] = field(default_factory=dict)
    setup_code: Optional[List[Dict]] = None
    test_code: Optional[List[Dict]] = None
    teardown_code: Optional[List[Dict]] = None
    
    assertions: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "timeout": self.timeout_seconds,
            "enabled": self.enabled,
            "tags": list(self.tags),
            "input_values": copy.deepcopy(self.input_values),
            "expected_output": copy.deepcopy(self.expected_output) if self.expected_output else None,
        }


@dataclass
class TestResultData:
    test_name: str
    result: TestResult
    duration_seconds: float = 0.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    actual_output: Optional[Dict[str, Any]] = None
    expected_output: Optional[Dict[str, Any]] = None
    exception: Optional[Exception] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "result": self.result.value,
            "duration_seconds": self.duration_seconds,
            "message": self.message,
            "details": copy.deepcopy(self.details),
            "actual_output": copy.deepcopy(self.actual_output) if self.actual_output else None,
            "expected_output": copy.deepcopy(self.expected_output) if self.expected_output else None,
            "has_exception": self.exception is not None,
        }


@dataclass
class TestSuite:
    name: str
    test_cases: List[TestCase] = field(default_factory=list)
    setup_hooks: List[Callable] = field(default_factory=list)
    teardown_hooks: List[Callable] = field(default_factory=list)
    
    def add_test(self, test: TestCase):
        self.test_cases.append(test)
    
    def get_tests_by_category(self, category: TestCategory) -> List[TestCase]:
        return [t for t in self.test_cases if t.category == category]
    
    def get_tests_by_tag(self, tag: str) -> List[TestCase]:
        return [t for t in self.test_cases if tag in t.tags]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "test_count": len(self.test_cases),
            "test_cases": [t.to_dict() for t in self.test_cases],
        }


class TestRunner:
    def __init__(self, vm_evaluator: Optional[Callable] = None):
        self.vm_evaluator = vm_evaluator
        self.results: List[TestResultData] = []
        self.before_each: List[Callable] = []
        self.after_each: List[Callable] = []
    
    def set_vm_evaluator(self, evaluator: Callable):
        self.vm_evaluator = evaluator
    
    def add_before_each(self, hook: Callable):
        self.before_each.append(hook)
    
    def add_after_each(self, hook: Callable):
        self.after_each.append(hook)
    
    def run_test(self, test_case: TestCase) -> TestResultData:
        start_time = time.time()
        result_data = TestResultData(
            test_name=test_case.name,
            result=TestResult.ERROR,
            expected_output=test_case.expected_output,
        )
        
        try:
            for hook in self.before_each:
                hook(test_case)
            
            if test_case.setup_code and self.vm_evaluator:
                setup_result = self.vm_evaluator(
                    test_case.setup_code,
                    test_case.input_values
                )
            
            actual_output = None
            if test_case.test_code:
                if self.vm_evaluator:
                    actual_output = self.vm_evaluator(
                        test_case.test_code,
                        test_case.input_values
                    )
                else:
                    actual_output = self._simulate_execution(
                        test_case.test_code,
                        test_case.input_values
                    )
            
            result_data.actual_output = actual_output
            
            passed, message = self._run_assertions(
                test_case, 
                actual_output
            )
            
            if passed:
                result_data.result = TestResult.PASSED
                result_data.message = message or "测试通过"
            else:
                result_data.result = TestResult.FAILED
                result_data.message = message or "断言失败"
            
            if test_case.teardown_code and self.vm_evaluator:
                self.vm_evaluator(test_case.teardown_code, {})
            
            for hook in self.after_each:
                hook(test_case, result_data)
        
        except TimeoutError as e:
            result_data.result = TestResult.TIMEOUT
            result_data.message = f"测试超时 ({test_case.timeout_seconds}秒)"
            result_data.exception = e
        
        except Exception as e:
            result_data.result = TestResult.ERROR
            result_data.message = str(e)
            result_data.exception = e
        
        result_data.duration_seconds = time.time() - start_time
        self.results.append(result_data)
        
        return result_data
    
    def _simulate_execution(self, code: List[Dict], inputs: Dict[str, Any]) -> Dict[str, Any]:
        registers = {f"R{i}": 0 for i in range(16)}
        registers.update(inputs)
        
        for instr in code:
            opcode = instr.get("opcode", 0)
            operands = instr.get("operands", [])
            
            if opcode == 59:
                if len(operands) >= 2:
                    dest = operands[0]
                    src = operands[1]
                    if isinstance(dest, int):
                        registers[f"R{dest}"] = src if isinstance(src, int) else registers.get(f"R{src}", 0)
            
            elif opcode == 0:
                if len(operands) >= 2:
                    dest = operands[0]
                    src = operands[1]
                    if isinstance(dest, int):
                        registers[f"R{dest}"] = src if isinstance(src, int) else registers.get(f"R{src}", 0)
        
        return registers
    
    def _run_assertions(self, test_case: TestCase, actual_output: Optional[Dict]) -> Tuple[bool, str]:
        if test_case.expected_output:
            if actual_output != test_case.expected_output:
                return False, f"期望输出 {test_case.expected_output}, 实际输出 {actual_output}"
        
        for assertion in test_case.assertions:
            passed, msg = self._evaluate_assertion(assertion, actual_output)
            if not passed:
                return False, msg
        
        return True, ""
    
    def _evaluate_assertion(self, assertion: Dict, actual_output: Optional[Dict]) -> Tuple[bool, str]:
        assert_type = assertion.get("type", "")
        
        if assert_type == "equals":
            actual = self._get_value(actual_output, assertion.get("path"))
            expected = assertion.get("expected")
            if actual != expected:
                return False, f"期望 {expected}, 实际 {actual}"
        
        elif assert_type == "not_equals":
            actual = self._get_value(actual_output, assertion.get("path"))
            expected = assertion.get("expected")
            if actual == expected:
                return False, f"期望不等于 {expected}, 实际 {actual}"
        
        elif assert_type == "greater_than":
            actual = self._get_value(actual_output, assertion.get("path"))
            threshold = assertion.get("threshold")
            if actual <= threshold:
                return False, f"期望 > {threshold}, 实际 {actual}"
        
        elif assert_type == "less_than":
            actual = self._get_value(actual_output, assertion.get("path"))
            threshold = assertion.get("threshold")
            if actual >= threshold:
                return False, f"期望 < {threshold}, 实际 {actual}"
        
        elif assert_type == "contains":
            actual = self._get_value(actual_output, assertion.get("path"))
            expected = assertion.get("expected")
            if expected not in actual:
                return False, f"{expected} 不在 {actual} 中"
        
        elif assert_type == "in_range":
            actual = self._get_value(actual_output, assertion.get("path"))
            min_val = assertion.get("min")
            max_val = assertion.get("max")
            if not (min_val <= actual <= max_val):
                return False, f"期望 [{min_val}, {max_val}], 实际 {actual}"
        
        return True, ""
    
    def _get_value(self, data: Optional[Dict], path: Optional[str]) -> Any:
        if not data or not path:
            return data
        
        parts = path.split(".")
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def run_suite(self, suite: TestSuite, 
                  tags: Optional[Set[str]] = None,
                  categories: Optional[Set[TestCategory]] = None) -> List[TestResultData]:
        self.results.clear()
        
        tests_to_run = suite.test_cases
        
        if tags:
            tests_to_run = [t for t in tests_to_run if t.tags & tags]
        
        if categories:
            tests_to_run = [t for t in tests_to_run if t.category in categories]
        
        for test in tests_to_run:
            if not test.enabled:
                continue
            self.run_test(test)
        
        return self.results
    
    def get_summary(self) -> Dict[str, Any]:
        if not self.results:
            return {"no_tests": True}
        
        passed = sum(1 for r in self.results if r.result == TestResult.PASSED)
        failed = sum(1 for r in self.results if r.result == TestResult.FAILED)
        skipped = sum(1 for r in self.results if r.result == TestResult.SKIPPED)
        errors = sum(1 for r in self.results if r.result == TestResult.ERROR)
        timeouts = sum(1 for r in self.results if r.result == TestResult.TIMEOUT)
        
        total_duration = sum(r.duration_seconds for r in self.results)
        avg_duration = total_duration / len(self.results) if self.results else 0
        
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
            "timeouts": timeouts,
            "pass_rate": passed / len(self.results) if self.results else 0,
            "total_duration_seconds": total_duration,
            "avg_duration_seconds": avg_duration,
            "all_passed": passed == len(self.results) and failed == 0 and errors == 0,
        }


class BehaviorComparator:
    def __init__(self, vm_evaluator: Optional[Callable] = None):
        self.vm_evaluator = vm_evaluator
        self.test_cases: List[TestCase] = []
    
    def add_test_case(self, test: TestCase):
        self.test_cases.append(test)
    
    def generate_test_cases_from_original(self, original_instructions: List[Dict]) -> List[TestCase]:
        tests = []
        
        test = TestCase(
            name="basic_behavior_test",
            description="基本行为测试 - 验证程序输出",
            category=TestCategory.REGRESSION,
            test_code=original_instructions,
        )
        
        if self.vm_evaluator:
            original_output = self.vm_evaluator(original_instructions, {})
            test.expected_output = original_output
        
        tests.append(test)
        self.test_cases.extend(tests)
        
        return tests
    
    def compare_behavior(self, 
                          original_code: List[Dict],
                          mutated_code: List[Dict],
                          inputs: Optional[List[Dict[str, Any]]] = None) -> Tuple[bool, Dict[str, Any]]:
        if inputs is None:
            inputs = [{}]
        
        all_passed = True
        results = []
        
        for input_set in inputs:
            original_output = self._execute_code(original_code, input_set)
            mutated_output = self._execute_code(mutated_code, input_set)
            
            passed = self._outputs_equivalent(original_output, mutated_output)
            
            if not passed:
                all_passed = False
            
            results.append({
                "input": input_set,
                "original_output": original_output,
                "mutated_output": mutated_output,
                "passed": passed,
            })
        
        return all_passed, {
            "all_passed": all_passed,
            "tests_run": len(results),
            "passed_count": sum(1 for r in results if r["passed"]),
            "results": results,
        }
    
    def _execute_code(self, code: List[Dict], inputs: Dict[str, Any]) -> Optional[Dict]:
        if self.vm_evaluator:
            try:
                return self.vm_evaluator(code, inputs)
            except Exception:
                return None
        return None
    
    def _outputs_equivalent(self, output1: Optional[Dict], output2: Optional[Dict]) -> bool:
        if output1 is None and output2 is None:
            return True
        
        if output1 is None or output2 is None:
            return False
        
        important_keys = {"R0", "R1", "R2", "R3", "R15"}
        
        for key in important_keys:
            val1 = output1.get(key)
            val2 = output2.get(key)
            if val1 != val2:
                return False
        
        return True
    
    def check_regression(self, 
                         original_fitness: float,
                         mutated_fitness: float,
                         tolerance: float = 0.05) -> bool:
        if mutated_fitness < original_fitness * (1 - tolerance):
            return True
        return False


class TestSuiteGenerator:
    def __init__(self):
        self.generated_count = 0
    
    def generate_from_instructions(self, 
                                    instructions: List[Dict],
                                    name_prefix: str = "auto_generated") -> TestSuite:
        suite = TestSuite(name=f"{name_prefix}_suite")
        
        suite.add_test(self._generate_smoke_test(instructions, name_prefix))
        
        suite.add_test(self._generate_edge_case_test(instructions, name_prefix))
        
        suite.add_test(self._generate_performance_test(instructions, name_prefix))
        
        self.generated_count += 1
        
        return suite
    
    def _generate_smoke_test(self, instructions: List[Dict], prefix: str) -> TestCase:
        return TestCase(
            name=f"{prefix}_smoke",
            description="冒烟测试 - 验证程序能够正常执行",
            category=TestCategory.UNIT,
            test_code=instructions,
            enabled=True,
            tags={"smoke", "basic"},
        )
    
    def _generate_edge_case_test(self, instructions: List[Dict], prefix: str) -> TestCase:
        return TestCase(
            name=f"{prefix}_edge_cases",
            description="边界情况测试",
            category=TestCategory.UNIT,
            test_code=instructions,
            input_values={"R0": 0, "R1": 0xFFFF},
            enabled=True,
            tags={"edge", "corner"},
        )
    
    def _generate_performance_test(self, instructions: List[Dict], prefix: str) -> TestCase:
        return TestCase(
            name=f"{prefix}_performance",
            description="性能基准测试",
            category=TestCategory.PERFORMANCE,
            test_code=instructions,
            timeout_seconds=30.0,
            enabled=True,
            tags={"performance", "benchmark"},
            assertions=[
                {
                    "type": "less_than",
                    "path": "_execution_time",
                    "threshold": 1.0,
                }
            ],
        )
    
    def generate_evolution_test(self, 
                                 original_instructions: List[Dict],
                                 fitness_threshold: float = 0.8) -> TestCase:
        return TestCase(
            name="evolution_regression",
            description="进化回归测试 - 验证变异不会破坏核心功能",
            category=TestCategory.EVOLUTION,
            test_code=original_instructions,
            enabled=True,
            tags={"evolution", "regression"},
        )
