import copy
import json
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set, Any, Callable, Union
from collections import defaultdict, deque


class EvolutionTrigger(Enum):
    MANUAL = "manual"
    HOT_PATH_DETECTED = "hot_path_detected"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    SCHEDULED = "scheduled"
    USER_REQUEST = "user_request"


class OptimizationLevel(Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class HotPathInfo:
    path_id: str
    instruction_indices: List[int]
    execution_count: int = 0
    total_cycles: float = 0.0
    avg_cycles_per_execution: float = 0.0
    estimated_improvement_potential: float = 0.0
    is_critical: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "instruction_count": len(self.instruction_indices),
            "execution_count": self.execution_count,
            "total_cycles": self.total_cycles,
            "avg_cycles": self.avg_cycles_per_execution,
            "improvement_potential": self.estimated_improvement_potential,
            "is_critical": self.is_critical,
        }


@dataclass
class OptimizationCandidate:
    candidate_id: str
    original_instructions: List[Dict]
    hot_path_info: Optional[HotPathInfo] = None
    trigger: EvolutionTrigger = EvolutionTrigger.MANUAL
    optimization_level: OptimizationLevel = OptimizationLevel.MODERATE
    
    objectives: List[str] = field(default_factory=lambda: ["min_latency", "min_energy"])
    max_generations: int = 100
    population_size: int = 32
    
    created_at: float = field(default_factory=time.time)
    status: str = "pending"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "trigger": self.trigger.value,
            "optimization_level": self.optimization_level.value,
            "objectives": list(self.objectives),
            "max_generations": self.max_generations,
            "population_size": self.population_size,
            "created_at": self.created_at,
            "status": self.status,
            "hot_path": self.hot_path_info.to_dict() if self.hot_path_info else None,
        }


@dataclass
class OptimizationResult:
    candidate_id: str
    success: bool
    original_instructions: List[Dict]
    optimized_instructions: Optional[List[Dict]] = None
    
    original_fitness: float = 0.0
    optimized_fitness: float = 0.0
    fitness_improvement: float = 0.0
    
    generations_run: int = 0
    pareto_front_size: int = 0
    
    behavior_check_passed: bool = True
    regression_test_passed: bool = True
    
    metrics: Dict[str, float] = field(default_factory=dict)
    
    started_at: float = 0.0
    completed_at: float = 0.0
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "success": self.success,
            "original_fitness": self.original_fitness,
            "optimized_fitness": self.optimized_fitness,
            "fitness_improvement_ratio": (
                self.optimized_fitness / self.original_fitness 
                if self.original_fitness > 0 else 0
            ),
            "generations_run": self.generations_run,
            "pareto_front_size": self.pareto_front_size,
            "behavior_check_passed": self.behavior_check_passed,
            "regression_test_passed": self.regression_test_passed,
            "metrics": copy.deepcopy(self.metrics),
            "duration_seconds": self.duration_seconds,
        }


class ExecutionProfiler:
    def __init__(self, 
                 hot_path_threshold: int = 100,
                 cycle_threshold: float = 1000.0,
                 max_history_size: int = 10000):
        
        self.hot_path_threshold = hot_path_threshold
        self.cycle_threshold = cycle_threshold
        self.max_history_size = max_history_size
        
        self.execution_history: deque = deque(maxlen=max_history_size)
        self.path_counts: Dict[tuple, int] = defaultdict(int)
        self.path_cycles: Dict[tuple, float] = defaultdict(float)
        self.instruction_counts: Dict[int, int] = defaultdict(int)
        self.instruction_cycles: Dict[int, float] = defaultdict(float)
        
        self.baseline_performance: Optional[Dict[str, float]] = None
        self.current_performance: Dict[str, float] = defaultdict(float)
        
        self.window_size = 100
        self.recent_executions: deque = deque(maxlen=self.window_size)
    
    def record_execution(self, 
                          instruction_sequence: List[int],
                          cycles: float,
                          timestamp: Optional[float] = None):
        ts = timestamp or time.time()
        path_key = tuple(instruction_sequence)
        
        self.execution_history.append({
            "path": instruction_sequence,
            "cycles": cycles,
            "timestamp": ts,
        })
        
        self.path_counts[path_key] += 1
        self.path_cycles[path_key] += cycles
        
        for idx in instruction_sequence:
            self.instruction_counts[idx] += 1
            self.instruction_cycles[idx] += cycles
        
        self.recent_executions.append({
            "cycles": cycles,
            "timestamp": ts,
        })
        
        self._update_current_performance(cycles)
    
    def _update_current_performance(self, cycles: float):
        if not self.recent_executions:
            return
        
        recent_cycles = [e["cycles"] for e in self.recent_executions]
        self.current_performance["avg_cycles"] = sum(recent_cycles) / len(recent_cycles)
        self.current_performance["max_cycles"] = max(recent_cycles)
        self.current_performance["min_cycles"] = min(recent_cycles)
        
        if self.baseline_performance:
            baseline_avg = self.baseline_performance.get("avg_cycles", 0)
            if baseline_avg > 0:
                self.current_performance["degradation_ratio"] = (
                    self.current_performance["avg_cycles"] / baseline_avg
                )
    
    def set_baseline(self, performance: Dict[str, float]):
        self.baseline_performance = copy.deepcopy(performance)
    
    def detect_hot_paths(self, 
                          count_threshold: Optional[int] = None,
                          cycle_threshold: Optional[float] = None) -> List[HotPathInfo]:
        hot_paths = []
        
        actual_count_threshold = count_threshold or self.hot_path_threshold
        actual_cycle_threshold = cycle_threshold or self.cycle_threshold
        
        for path_key, count in self.path_counts.items():
            total_cycles = self.path_cycles[path_key]
            avg_cycles = total_cycles / count if count > 0 else 0
            
            if count >= actual_count_threshold or total_cycles >= actual_cycle_threshold:
                path_info = HotPathInfo(
                    path_id=f"path_{len(hot_paths)}",
                    instruction_indices=list(path_key),
                    execution_count=count,
                    total_cycles=total_cycles,
                    avg_cycles_per_execution=avg_cycles,
                    estimated_improvement_potential=total_cycles * 0.3,
                    is_critical=total_cycles >= actual_cycle_threshold * 2,
                )
                hot_paths.append(path_info)
        
        hot_paths.sort(key=lambda p: p.total_cycles, reverse=True)
        
        return hot_paths
    
    def detect_performance_degradation(self, 
                                         threshold_ratio: float = 1.2) -> bool:
        if not self.baseline_performance or not self.current_performance:
            return False
        
        baseline_avg = self.baseline_performance.get("avg_cycles", 0)
        current_avg = self.current_performance.get("avg_cycles", 0)
        
        if baseline_avg > 0 and current_avg > baseline_avg * threshold_ratio:
            return True
        
        return False
    
    def get_hot_instructions(self, top_n: int = 10) -> List[Tuple[int, int, float]]:
        hot = [
            (idx, self.instruction_counts[idx], self.instruction_cycles[idx])
            for idx in self.instruction_counts
        ]
        hot.sort(key=lambda x: x[1], reverse=True)
        return hot[:top_n]
    
    def reset(self):
        self.execution_history.clear()
        self.path_counts.clear()
        self.path_cycles.clear()
        self.instruction_counts.clear()
        self.instruction_cycles.clear()
        self.recent_executions.clear()
        self.current_performance.clear()


class EvolutionOrchestrator:
    def __init__(self,
                 evolution_engine: Optional[Any] = None,
                 vm_evaluator: Optional[Callable] = None,
                 behavior_checker: Optional[Any] = None,
                 test_runner: Optional[Any] = None):
        
        self.evolution_engine = evolution_engine
        self.vm_evaluator = vm_evaluator
        self.behavior_checker = behavior_checker
        self.test_runner = test_runner
        
        self.pending_candidates: deque = deque()
        self.active_optimization: Optional[OptimizationCandidate] = None
        self.completed_results: List[OptimizationResult] = []
        
        self.max_concurrent_optimizations = 1
        self.optimization_history: List[Dict] = []
        
        self._lock = threading.Lock()
    
    def submit_candidate(self, candidate: OptimizationCandidate) -> str:
        with self._lock:
            self.pending_candidates.append(candidate)
            return candidate.candidate_id
    
    def get_next_candidate(self) -> Optional[OptimizationCandidate]:
        with self._lock:
            if self.pending_candidates:
                self.active_optimization = self.pending_candidates.popleft()
                self.active_optimization.status = "running"
                return self.active_optimization
            return None
    
    def run_optimization(self, candidate: OptimizationCandidate) -> OptimizationResult:
        result = OptimizationResult(
            candidate_id=candidate.candidate_id,
            success=False,
            original_instructions=copy.deepcopy(candidate.original_instructions),
            started_at=time.time(),
        )
        
        try:
            if self.vm_evaluator:
                original_metrics = self.vm_evaluator(candidate.original_instructions)
                result.original_fitness = self._calculate_fitness_from_metrics(
                    original_metrics, candidate.objectives
                )
                result.metrics["original"] = original_metrics
            
            if self.evolution_engine:
                from evomorph.evolution.engine import GeneInstruction
                
                genes = self._instructions_to_genes(candidate.original_instructions)
                
                self.evolution_engine.initialize_population(
                    genes, 
                    size=candidate.population_size
                )
                
                if hasattr(self.evolution_engine, 'pareto_front'):
                    self.evolution_engine.evolve(
                        max_generations=candidate.max_generations
                    )
                    best_individual = self.evolution_engine.select_by_preference(
                        {obj: 1.0 for obj in candidate.objectives}
                    )
                    result.pareto_front_size = len(self.evolution_engine.pareto_front.individuals)
                else:
                    best_individual = self.evolution_engine.evolve(
                        max_generations=candidate.max_generations
                    )
                
                result.generations_run = self.evolution_engine.generation
                
                if best_individual:
                    result.optimized_instructions = self._genes_to_instructions(best_individual.genes)
                    
                    if self.vm_evaluator and result.optimized_instructions:
                        optimized_metrics = self.vm_evaluator(result.optimized_instructions)
                        result.optimized_fitness = self._calculate_fitness_from_metrics(
                            optimized_metrics, candidate.objectives
                        )
                        result.metrics["optimized"] = optimized_metrics
                        
                        result.fitness_improvement = (
                            result.optimized_fitness - result.original_fitness
                        )
            
            if result.optimized_instructions and self.behavior_checker:
                consistent, check_result = self.behavior_checker.compare_behavior(
                    candidate.original_instructions,
                    result.optimized_instructions
                )
                result.behavior_check_passed = consistent
                result.metrics["behavior_check"] = check_result
            
            if result.optimized_instructions and self.test_runner:
                from evomorph.analysis.test_framework import TestSuiteGenerator
                generator = TestSuiteGenerator()
                suite = generator.generate_from_instructions(
                    candidate.original_instructions,
                    name_prefix="evolution_test"
                )
                
                test_results = self.test_runner.run_suite(suite)
                summary = self.test_runner.get_summary()
                result.regression_test_passed = summary.get("all_passed", False)
                result.metrics["test_summary"] = summary
            
            result.success = (
                result.optimized_instructions is not None and
                result.behavior_check_passed and
                result.fitness_improvement > 0
            )
        
        except Exception as e:
            result.metrics["error"] = str(e)
        
        result.completed_at = time.time()
        result.duration_seconds = result.completed_at - result.started_at
        
        with self._lock:
            self.completed_results.append(result)
            self.active_optimization = None
            self.optimization_history.append(result.to_dict())
        
        return result
    
    def _instructions_to_genes(self, instructions: List[Dict]) -> List:
        from evomorph.evolution.engine import GeneInstruction
        
        genes = []
        for instr in instructions:
            gene = GeneInstruction(
                opcode=instr.get("opcode", 0),
                modifier=instr.get("modifier", 0),
                operands=list(instr.get("operands", [])),
            )
            genes.append(gene)
        
        return genes
    
    def _genes_to_instructions(self, genes: List) -> List[Dict]:
        instructions = []
        for gene in genes:
            instr = {
                "opcode": gene.opcode,
                "modifier": gene.modifier,
                "operands": list(gene.operands),
            }
            instructions.append(instr)
        
        return instructions
    
    def _calculate_fitness_from_metrics(self, 
                                          metrics: Dict,
                                          objectives: List[str]) -> float:
        fitness = 0.0
        
        for obj in objectives:
            if obj == "min_latency":
                cycles = metrics.get("total_cycles", 1.0)
                fitness += 1.0 / max(cycles, 0.1)
            elif obj == "min_energy":
                energy = metrics.get("total_energy", 1.0)
                fitness += 1.0 / max(energy, 0.1)
            elif obj == "min_size":
                cycles = metrics.get("instruction_count", 1.0)
                fitness += 1.0 / max(cycles, 0.1)
            elif obj == "max_throughput":
                ipc = metrics.get("ipc", 0.1)
                fitness += ipc
        
        return fitness
    
    def get_pending_count(self) -> int:
        with self._lock:
            return len(self.pending_candidates)
    
    def get_completed_results(self) -> List[OptimizationResult]:
        with self._lock:
            return list(self.completed_results)
    
    def get_best_result(self) -> Optional[OptimizationResult]:
        with self._lock:
            if not self.completed_results:
                return None
            
            successful = [r for r in self.completed_results if r.success]
            if not successful:
                return None
            
            successful.sort(key=lambda r: r.fitness_improvement, reverse=True)
            return successful[0]


class ContinuousEvolutionSystem:
    def __init__(self,
                 evolution_engine: Optional[Any] = None,
                 vm_evaluator: Optional[Callable] = None,
                 behavior_checker: Optional[Any] = None,
                 test_runner: Optional[Any] = None):
        
        self.profiler = ExecutionProfiler()
        self.orchestrator = EvolutionOrchestrator(
            evolution_engine=evolution_engine,
            vm_evaluator=vm_evaluator,
            behavior_checker=behavior_checker,
            test_runner=test_runner,
        )
        
        self.main_instructions: List[Dict] = []
        self.optimized_versions: Dict[str, List[Dict]] = {}
        
        self.hot_path_monitor_interval: float = 5.0
        self.auto_evolution_enabled: bool = True
        self.min_improvement_threshold: float = 0.05
        
        self._running: bool = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        self.callbacks: Dict[str, List[Callable]] = defaultdict(list)
    
    def set_instructions(self, instructions: List[Dict]):
        self.main_instructions = copy.deepcopy(instructions)
        
        if self.vm_evaluator:
            baseline = self.vm_evaluator(instructions)
            self.profiler.set_baseline({
                "avg_cycles": baseline.get("total_cycles", 0.0),
            })
    
    def register_callback(self, event: str, callback: Callable):
        self.callbacks[event].append(callback)
    
    def _trigger_callbacks(self, event: str, *args, **kwargs):
        for callback in self.callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception:
                pass
    
    def record_execution(self, 
                          instruction_indices: List[int],
                          cycles: float):
        self.profiler.record_execution(instruction_indices, cycles)
    
    def start_monitoring(self):
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
            self._monitor_thread = None
    
    def _monitor_loop(self):
        while self._running:
            try:
                hot_paths = self.profiler.detect_hot_paths()
                
                if hot_paths and self.auto_evolution_enabled:
                    for path in hot_paths[:3]:
                        if path.is_critical or path.execution_count > self.profiler.hot_path_threshold:
                            self._submit_optimization_for_path(path)
                
                if self.profiler.detect_performance_degradation():
                    self._trigger_callbacks(
                        "performance_degradation",
                        current_performance=dict(self.profiler.current_performance),
                        baseline=dict(self.profiler.baseline_performance) 
                        if self.profiler.baseline_performance else None,
                    )
                
                self._check_and_apply_optimizations()
                
                time.sleep(self.hot_path_monitor_interval)
            
            except Exception:
                time.sleep(self.hot_path_monitor_interval)
    
    def _submit_optimization_for_path(self, hot_path: HotPathInfo):
        if not self.main_instructions:
            return
        
        path_instructions = []
        for idx in hot_path.instruction_indices:
            if 0 <= idx < len(self.main_instructions):
                path_instructions.append(self.main_instructions[idx])
        
        if not path_instructions:
            return
        
        import uuid
        candidate = OptimizationCandidate(
            candidate_id=str(uuid.uuid4())[:8],
            original_instructions=path_instructions,
            hot_path_info=hot_path,
            trigger=EvolutionTrigger.HOT_PATH_DETECTED,
            optimization_level=OptimizationLevel.MODERATE,
            objectives=["min_latency", "min_energy"],
            max_generations=50,
            population_size=32,
        )
        
        self.orchestrator.submit_candidate(candidate)
        
        self._trigger_callbacks(
            "optimization_submitted",
            candidate=candidate.to_dict(),
            hot_path=hot_path.to_dict(),
        )
    
    def _check_and_apply_optimizations(self):
        results = self.orchestrator.get_completed_results()
        
        for result in results[-5:]:
            if result.success and result.candidate_id not in self.optimized_versions:
                if result.fitness_improvement >= self.min_improvement_threshold:
                    if result.optimized_instructions:
                        self.optimized_versions[result.candidate_id] = copy.deepcopy(
                            result.optimized_instructions
                        )
                        
                        self._trigger_callbacks(
                            "optimization_applied",
                            result=result.to_dict(),
                        )
    
    def request_optimization(self,
                              instructions: List[Dict],
                              trigger: EvolutionTrigger = EvolutionTrigger.USER_REQUEST,
                              optimization_level: OptimizationLevel = OptimizationLevel.MODERATE,
                              objectives: List[str] = None) -> str:
        import uuid
        candidate = OptimizationCandidate(
            candidate_id=str(uuid.uuid4())[:8],
            original_instructions=copy.deepcopy(instructions),
            trigger=trigger,
            optimization_level=optimization_level,
            objectives=objectives or ["min_latency", "min_energy"],
        )
        
        return self.orchestrator.submit_candidate(candidate)
    
    def get_status(self) -> Dict[str, Any]:
        hot_paths = self.profiler.detect_hot_paths()
        hot_instructions = self.profiler.get_hot_instructions()
        
        return {
            "monitoring": self._running,
            "auto_evolution_enabled": self.auto_evolution_enabled,
            "main_instructions_count": len(self.main_instructions),
            "optimized_versions_count": len(self.optimized_versions),
            "pending_optimizations": self.orchestrator.get_pending_count(),
            "has_active_optimization": self.orchestrator.active_optimization is not None,
            "completed_optimizations": len(self.orchestrator.completed_results),
            "hot_paths": [p.to_dict() for p in hot_paths[:5]],
            "hot_instructions": [
                {"index": i, "count": c, "cycles": cy}
                for i, c, cy in hot_instructions
            ],
            "baseline_performance": dict(self.profiler.baseline_performance)
            if self.profiler.baseline_performance else None,
            "current_performance": dict(self.profiler.current_performance),
        }
    
    def get_optimization_history(self) -> List[Dict]:
        return list(self.orchestrator.optimization_history)
    
    def run_immediate_optimization(self,
                                     instructions: List[Dict],
                                     max_generations: int = 100) -> Optional[OptimizationResult]:
        import uuid
        candidate = OptimizationCandidate(
            candidate_id=str(uuid.uuid4())[:8],
            original_instructions=copy.deepcopy(instructions),
            trigger=EvolutionTrigger.MANUAL,
            optimization_level=OptimizationLevel.AGGRESSIVE,
            max_generations=max_generations,
        )
        
        result = self.orchestrator.run_optimization(candidate)
        
        self._trigger_callbacks(
            "optimization_completed",
            result=result.to_dict(),
        )
        
        return result
