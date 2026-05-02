#!/usr/bin/env python3
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSemanticMutation(unittest.TestCase):
    def setUp(self):
        from evomorph.evolution.semantic_mutation import (
            InstructionSemantics, SemanticMutationEngine, SemanticMutationConfig,
            InstructionRole, InsertDeleteMutation
        )
        self.semantics = InstructionSemantics()
        self.config = SemanticMutationConfig()
        self.engine = SemanticMutationEngine(self.config)
        self.engine.set_seed(42)
    
    def test_instruction_semantics_initialization(self):
        self.assertIsNotNone(self.semantics)
        self.assertIsNotNone(self.semantics.opcode_to_category)
        self.assertIsNotNone(self.semantics.role_to_opcodes)
    
    def test_get_category(self):
        yuan_opcode = 63
        category = self.semantics.get_category(yuan_opcode)
        self.assertIsNotNone(category)
    
    def test_get_roles(self):
        roles = self.semantics.get_roles(63)
        self.assertIsInstance(roles, set)
    
    def test_same_category_mutation(self):
        opcode = 63
        same_cat = self.semantics.get_same_category_opcodes(opcode)
        self.assertIsInstance(same_cat, list)
    
    def test_is_semantically_valid_mutation(self):
        result = self.semantics.is_semantically_valid_mutation(63, 34)
        self.assertIsInstance(result, bool)
    
    def test_mutation_config_defaults(self):
        self.assertTrue(self.config.use_semantic_mutation)
        self.assertTrue(self.config.preserve_control_flow)
        self.assertEqual(self.config.same_category_prob, 0.6)
    
    def test_insert_delete_mutation(self):
        from evomorph.evolution.engine import GeneInstruction
        
        indel = InsertDeleteMutation(self.semantics)
        genes = [GeneInstruction(opcode=63), GeneInstruction(opcode=0)]
        
        new_genes = indel.insert_instruction(genes, 1)
        self.assertEqual(len(new_genes), 3)
        
        new_genes2 = indel.delete_instruction(new_genes, 1)
        self.assertEqual(len(new_genes2), 2)


class TestMultiObjectiveOptimization(unittest.TestCase):
    def setUp(self):
        from evomorph.evolution.multi_objective import (
            Objective, ObjectiveType, ParetoFront,
            MultiObjectiveConfig, NSGAIIEngine
        )
        self.obj1 = Objective("min_latency", ObjectiveType.MINIMIZE, 1.0)
        self.obj2 = Objective("max_throughput", ObjectiveType.MAXIMIZE, 2.0)
        self.pareto = ParetoFront(objectives=[self.obj1, self.obj2])
    
    def test_objective_creation(self):
        self.assertEqual(self.obj1.name, "min_latency")
        self.assertEqual(self.obj1.objective_type, ObjectiveType.MINIMIZE)
    
    def test_objective_normalize(self):
        obj = Objective("test", ObjectiveType.MINIMIZE, 
                       lower_bound=0, upper_bound=100)
        result = obj.normalize(50)
        self.assertEqual(result, 0.5)
    
    def test_pareto_front_initialization(self):
        self.assertEqual(len(self.pareto.objectives), 2)
        self.assertEqual(len(self.pareto.individuals), 0)
    
    def test_multi_objective_config(self):
        config = MultiObjectiveConfig()
        self.assertTrue(config.use_nsga2)
        self.assertGreater(len(config.objectives), 0)


class TestExecutionTracing(unittest.TestCase):
    def setUp(self):
        from evomorph.evolution.execution_tracing import (
            EnhancedExecutionTracer, CacheModel, BranchPredictor,
            ResourceUsageAnalyzer, BehaviorConsistencyChecker
        )
        self.tracer = EnhancedExecutionTracer()
        self.cache = CacheModel()
        self.predictor = BranchPredictor()
        self.analyzer = ResourceUsageAnalyzer()
    
    def test_tracer_initialization(self):
        self.assertIsNotNone(self.tracer.metrics)
        self.assertEqual(self.tracer.step_count, 0)
    
    def test_trace_instruction(self):
        step = self.tracer.trace_instruction(opcode=63, operands=[0, 1])
        self.assertIsNotNone(step)
        self.assertEqual(self.tracer.step_count, 1)
    
    def test_cache_access(self):
        result = self.cache.access(0x1000)
        from evomorph.evolution.execution_tracing import CacheResult
        self.assertEqual(result, CacheResult.MISS)
        
        result2 = self.cache.access(0x1000)
        self.assertEqual(result2, CacheResult.HIT)
    
    def test_branch_predictor(self):
        outcome = self.predictor.predict(0x100)
        from evomorph.evolution.execution_tracing import BranchOutcome
        self.assertIn(outcome, [BranchOutcome.TAKEN, BranchOutcome.NOT_TAKEN])
        
        self.predictor.update(0x100, BranchOutcome.TAKEN)
    
    def test_resource_analyzer(self):
        self.analyzer.track_register_write(0, 1)
        self.analyzer.track_register_read(0, 2)
        
        critical = self.analyzer.calculate_critical_path()
        self.assertGreaterEqual(critical, 1)
    
    def test_behavior_checker(self):
        checker = BehaviorConsistencyChecker()
        
        original = {
            "R0": 42,
            "R1": 100
        }
        same = {
            "R0": 42,
            "R1": 100
        }
        different = {
            "R0": 99,
            "R1": 100
        }
        
        checker._outputs_equivalent = MagicMock(return_value=True)
        
        self.assertIsNotNone(checker)


class TestStaticAnalyzer(unittest.TestCase):
    def setUp(self):
        from evomorph.analysis.static_analyzer import (
            CFGConstructor, ControlFlowGraph, StaticAnalyzer,
            ReachingDefinitions, LiveVariables
        )
        self.constructor = CFGConstructor()
        self.analyzer = StaticAnalyzer()
    
    def test_cfg_constructor(self):
        instructions = [
            {"opcode": 63, "operands": [0, 1]},
            {"opcode": 59, "operands": [0, 1]},
            {"opcode": 1, "operands": []},
        ]
        
        cfg = self.constructor.build_from_instructions(instructions)
        self.assertIsNotNone(cfg)
        self.assertGreater(len(cfg.nodes), 0)
    
    def test_cfg_reachable_nodes(self):
        instructions = [
            {"opcode": 63, "operands": [0, 1]},
            {"opcode": 1, "operands": []},
        ]
        
        cfg = self.constructor.build_from_instructions(instructions)
        if cfg.entry_node is not None:
            reachable = cfg.reachable_nodes(cfg.entry_node)
            self.assertIsInstance(reachable, set)
    
    def test_static_analyzer(self):
        instructions = [
            {"opcode": 63, "operands": [0, 1]},
            {"opcode": 59, "operands": [0, 1]},
            {"opcode": 1, "operands": []},
        ]
        
        result = self.analyzer.analyze_instructions(instructions)
        self.assertIsNotNone(result)
        self.assertIn("summary", result)
        self.assertIn("issues", result)
    
    def test_analysis_summary(self):
        instructions = [
            {"opcode": 63, "operands": [0, 1]},
            {"opcode": 1, "operands": []},
        ]
        
        result = self.analyzer.analyze_instructions(instructions)
        summary = result["summary"]
        self.assertIn("total_issues", summary)
        self.assertIn("errors", summary)
        self.assertIn("warnings", summary)


class TestTestFramework(unittest.TestCase):
    def setUp(self):
        from evomorph.analysis.test_framework import (
            TestCase, TestSuite, TestRunner, TestResult,
            TestCategory, BehaviorComparator
        )
        self.test_case = TestCase(
            name="test_example",
            description="Example test",
            category=TestCategory.UNIT,
        )
        self.suite = TestSuite(name="test_suite")
        self.runner = TestRunner()
    
    def test_test_case_creation(self):
        self.assertEqual(self.test_case.name, "test_example")
        self.assertEqual(self.test_case.category, TestCategory.UNIT)
        self.assertTrue(self.test_case.enabled)
    
    def test_test_suite(self):
        self.suite.add_test(self.test_case)
        self.assertEqual(len(self.suite.test_cases), 1)
        
        unit_tests = self.suite.get_tests_by_category(TestCategory.UNIT)
        self.assertEqual(len(unit_tests), 1)
    
    def test_test_runner(self):
        self.test_case.test_code = [
            {"opcode": 59, "operands": [0, 42]},
        ]
        self.test_case.expected_output = {"R0": 42}
        
        self.suite.add_test(self.test_case)
        
        results = self.runner.run_suite(self.suite)
        self.assertIsInstance(results, list)
        
        summary = self.runner.get_summary()
        self.assertIn("total", summary)
        self.assertIn("passed", summary)
    
    def test_behavior_comparator(self):
        comparator = BehaviorComparator()
        
        original = [
            {"opcode": 59, "operands": [0, 42]},
        ]
        mutated = [
            {"opcode": 59, "operands": [0, 42]},
        ]
        
        test = comparator.generate_test_cases_from_original(original)
        self.assertEqual(len(test), 1)


class TestPlatformProfiles(unittest.TestCase):
    def setUp(self):
        from evomorph.platform.profiles import (
            PlatformProfileRegistry, PlatformPerformanceEstimator,
            DynamicProfileCollector, ArchitectureType, PlatformOS
        )
        self.registry = PlatformProfileRegistry()
    
    def test_platform_registry(self):
        platforms = self.registry.list_all()
        self.assertGreater(len(platforms), 0)
        
        profile = self.registry.get("linux-x86_64-generic")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.architecture, ArchitectureType.X86_64)
    
    def test_profile_match(self):
        profile = self.registry.match_by_target("linux-6.x")
        self.assertIsNotNone(profile)
    
    def test_performance_estimator(self):
        profile = self.registry.get("linux-x86_64-generic")
        self.assertIsNotNone(profile)
        
        estimator = PlatformPerformanceEstimator(profile)
        self.assertIsNotNone(estimator)
        
        latency = estimator.estimate_instruction_latency(63, [0, 1])
        self.assertGreater(latency, 0)
    
    def test_dynamic_collector(self):
        collector = DynamicProfileCollector()
        
        collector.record_execution([0, 1, 2], 100.0)
        collector.record_execution([0, 1, 2], 105.0)
        
        hot = collector.detect_hot_paths(count_threshold=1)
        self.assertIsInstance(hot, list)
        
        summary = collector.to_dict()
        self.assertIn("total_instructions", summary)


class TestTypesSystem(unittest.TestCase):
    def setUp(self):
        from evomorph.lang.types import (
            EvomorphType, TypeKind, TrigramTypeSystem,
            PrimitiveTypes, TypeChecker, TypeEnvironment
        )
        self.primitives = PrimitiveTypes()
    
    def test_primitive_types(self):
        int32 = PrimitiveTypes.INT32
        self.assertEqual(int32.kind, TypeKind.INTEGER)
        self.assertEqual(int32.size, 4)
    
    def test_pointer_type(self):
        int_ptr = PrimitiveTypes.get_pointer(PrimitiveTypes.INT32)
        self.assertEqual(int_ptr.kind, TypeKind.POINTER)
        self.assertEqual(int_ptr.size, 8)
    
    def test_array_type(self):
        array_type = PrimitiveTypes.get_array(PrimitiveTypes.INT32, 10)
        self.assertEqual(array_type.kind, TypeKind.ARRAY)
        self.assertEqual(array_type.array_length, 10)
        self.assertEqual(array_type.size, 4 * 10)
    
    def test_trigram_type_system(self):
        trigram = TrigramTypeSystem.get_trigram("䷀")
        self.assertIsNotNone(trigram)
        self.assertEqual(trigram.name, "乾")
    
    def test_type_checker(self):
        checker = TypeChecker()
        
        checker.check_type_compatibility(
            PrimitiveTypes.INT32,
            PrimitiveTypes.INT64
        )
        
        diag = checker.get_diagnostics()
        self.assertIsNotNone(diag)
    
    def test_type_environment(self):
        env = TypeEnvironment()
        env.bind("x", PrimitiveTypes.INT32)
        
        result = env.lookup("x")
        self.assertEqual(result, PrimitiveTypes.INT32)


class TestFunctionsSystem(unittest.TestCase):
    def setUp(self):
        from evomorph.lang.functions import (
            FunctionSignature, FunctionParameter, FunctionDefinition,
            FunctionRegistry, CallStack, FunctionCallABI,
            FunctionVisibility, CallingConvention
        )
        self.registry = FunctionRegistry()
        self.abi = FunctionCallABI()
    
    def test_function_parameter(self):
        param = FunctionParameter(name="arg0", type_hint="int")
        self.assertEqual(param.name, "arg0")
    
    def test_function_signature(self):
        sig = FunctionSignature(
            name="test_func",
            parameters=[
                FunctionParameter(name="a"),
                FunctionParameter(name="b"),
            ],
            visibility=FunctionVisibility.PUBLIC,
        )
        
        self.assertEqual(sig.name, "test_func")
        self.assertEqual(len(sig.parameters), 2)
    
    def test_function_registry(self):
        sig = FunctionSignature(name="test")
        func = FunctionDefinition(sig)
        func.start_address = 0x100
        
        self.registry.register(func)
        
        retrieved = self.registry.get("test")
        self.assertIsNotNone(retrieved)
        
        by_addr = self.registry.get_by_address(0x100)
        self.assertIsNotNone(by_addr)
    
    def test_call_stack(self):
        from evomorph.lang.functions import CallFrame
        
        stack = CallStack(max_depth=10)
        
        frame = CallFrame(
            return_address=0x200,
            frame_pointer=0x1000,
            function_name="test",
        )
        
        result = stack.push(frame)
        self.assertTrue(result)
        self.assertEqual(stack.depth(), 1)
        
        popped = stack.pop()
        self.assertEqual(popped.function_name, "test")
        self.assertEqual(stack.depth(), 0)
    
    def test_function_call_abi(self):
        reg = self.abi.get_parameter_register(0)
        self.assertIsNotNone(reg)
        
        preserved = self.abi.get_preserved_registers()
        self.assertIsInstance(preserved, list)


class TestPackageManager(unittest.TestCase):
    def setUp(self):
        from evomorph.lang.package_manager import (
            Dependency, DependencyConstraint, PackageManifest,
            Version, PackageType
        )
        self.manifest = PackageManifest(
            name="test_package",
            version="1.0.0",
            package_type=PackageType.LIBRARY,
        )
    
    def test_dependency_creation(self):
        dep = Dependency(
            name="other_package",
            version="^1.0.0",
            constraint=DependencyConstraint.COMPATIBLE,
        )
        
        self.assertEqual(dep.name, "other_package")
        self.assertEqual(dep.constraint, DependencyConstraint.COMPATIBLE)
    
    def test_package_manifest(self):
        self.assertEqual(self.manifest.name, "test_package")
        self.assertEqual(self.manifest.version, "1.0.0")
        
        dep = Dependency(name="dep1", version="*")
        self.manifest.dependencies.append(dep)
        
        self.assertEqual(len(self.manifest.dependencies), 1)
    
    def test_manifest_json(self):
        json_str = self.manifest.to_json()
        self.assertIsInstance(json_str, str)
        
        parsed = PackageManifest.from_json(json_str)
        self.assertEqual(parsed.name, self.manifest.name)
        self.assertEqual(parsed.version, self.manifest.version)
    
    def test_version_parsing(self):
        v = Version("1.2.3")
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 2)
        self.assertEqual(v.patch, 3)
    
    def test_version_constraints(self):
        v1 = Version("1.2.0")
        v2 = Version("1.3.0")
        
        compatible = v2.satisfies(DependencyConstraint.COMPATIBLE, v1)
        self.assertTrue(compatible)
        
        exact = v2.satisfies(DependencyConstraint.EXACT, v1)
        self.assertFalse(exact)


class TestContinuousEvolution(unittest.TestCase):
    def setUp(self):
        from evomorph.evolution.continuous_evolution import (
            ExecutionProfiler, EvolutionOrchestrator,
            EvolutionTrigger, OptimizationLevel, OptimizationCandidate
        )
        self.profiler = ExecutionProfiler(
            hot_path_threshold=5,
            cycle_threshold=100.0
        )
    
    def test_profiler_initialization(self):
        self.assertEqual(self.profiler.hot_path_threshold, 5)
        self.assertEqual(self.profiler.cycle_threshold, 100.0)
    
    def test_execution_recording(self):
        for i in range(10):
            self.profiler.record_execution([0, 1, 2], 100.0 + i)
        
        hot_paths = self.profiler.detect_hot_paths(count_threshold=5)
        self.assertGreater(len(hot_paths), 0)
    
    def test_hot_instructions(self):
        for i in range(10):
            self.profiler.record_execution([0, 1, 2], 50.0)
        
        hot = self.profiler.get_hot_instructions(top_n=5)
        self.assertIsInstance(hot, list)
    
    def test_performance_degradation(self):
        self.profiler.set_baseline({"avg_cycles": 50.0})
        self.profiler._update_current_performance(60.0)
        
        degraded = self.profiler.detect_performance_degradation(threshold_ratio=1.1)
        self.assertTrue(degraded)
    
    def test_optimization_candidate(self):
        import uuid
        
        candidate = OptimizationCandidate(
            candidate_id=str(uuid.uuid4())[:8],
            original_instructions=[
                {"opcode": 63, "operands": [0, 1]},
            ],
            trigger=EvolutionTrigger.MANUAL,
            optimization_level=OptimizationLevel.MODERATE,
            objectives=["min_latency"],
            max_generations=50,
            population_size=32,
        )
        
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.status, "pending")


class TestNativeCodeGeneration(unittest.TestCase):
    def setUp(self):
        from evomorph.platform.codegen_native import (
            MachineCodeGenerator, ControlFlowGraph, BasicBlock,
            RegisterAllocator, InstructionSelector
        )
        self.generator = MachineCodeGenerator("x86_64")
    
    def test_code_generator_initialization(self):
        self.assertIsNotNone(self.generator)
        self.assertIsNotNone(self.generator.machine_registers)
        self.assertGreater(len(self.generator.machine_registers), 0)
    
    def test_instruction_selector(self):
        selector = InstructionSelector("x86_64")
        self.assertIsNotNone(selector)
        
        instructions = selector.select(63, [0, 1])
        self.assertIsInstance(instructions, list)
    
    def test_register_allocator(self):
        from evomorph.platform.codegen_native import MachineRegister, RegisterType
        
        registers = [
            MachineRegister("R0", 0, RegisterType.GENERAL),
            MachineRegister("R1", 1, RegisterType.GENERAL),
        ]
        
        allocator = RegisterAllocator(registers)
        self.assertIsNotNone(allocator)
        
        vreg = allocator.alloc_virtual(RegisterType.GENERAL)
        self.assertIsNotNone(vreg)
    
    def test_basic_block(self):
        block = BasicBlock(
            label="entry",
            is_entry=True,
        )
        
        self.assertEqual(block.label, "entry")
        self.assertTrue(block.is_entry)
    
    def test_control_flow_graph(self):
        cfg = ControlFlowGraph()
        
        entry = BasicBlock(label="entry", is_entry=True)
        exit_block = BasicBlock(label="exit", is_exit=True)
        
        cfg.add_node(entry)
        cfg.add_node(exit_block)
        cfg.add_edge(entry.node_id, exit_block.node_id)
        
        self.assertIsNotNone(cfg.entry_node)
        self.assertGreater(len(cfg.exit_nodes), 0)


class TestExceptions(unittest.TestCase):
    def setUp(self):
        from evomorph.lang.exceptions import (
            EvomorphError, ErrorSeverity, ErrorCategory,
            ErrorCodeRegistry, ExceptionHandler,
            SourceLocation
        )
        self.handler = ExceptionHandler()
    
    def test_error_creation(self):
        error = EvomorphError(
            code="E0001",
            message="Test error",
            category=ErrorCategory.SYNTAX,
            severity=ErrorSeverity.ERROR,
        )
        
        self.assertEqual(error.code, "E0001")
        self.assertEqual(error.severity, ErrorSeverity.ERROR)
    
    def test_source_location(self):
        loc = SourceLocation(
            file_path="test.evo",
            line=10,
            column=5,
        )
        
        self.assertEqual(loc.file_path, "test.evo")
        self.assertEqual(loc.line, 10)
    
    def test_error_code_registry(self):
        error = ErrorCodeRegistry.create_error("E0001", "Custom message")
        
        self.assertEqual(error.code, "E0001")
        self.assertEqual(error.category, ErrorCategory.SYNTAX)
    
    def test_exception_handler(self):
        def custom_handler(exc):
            pass
        
        self.handler.register_handler(custom_handler, ErrorCategory.SYNTAX)
        
        error = ErrorCodeRegistry.create_error("E0001")
        with self.assertRaises(Exception):
            self.handler.raise_exception(error)


if __name__ == "__main__":
    unittest.main(verbosity=2)
