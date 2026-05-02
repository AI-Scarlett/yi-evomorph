import copy
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set, Any, Callable
from collections import defaultdict
from enum import Enum


class BranchOutcome(Enum):
    TAKEN = "taken"
    NOT_TAKEN = "not_taken"
    UNKNOWN = "unknown"


class CacheResult(Enum):
    HIT = "hit"
    MISS = "miss"
    UNKNOWN = "unknown"


@dataclass
class ExecutionStep:
    step_number: int
    opcode: int
    register_state: Dict[int, int] = field(default_factory=dict)
    memory_access: Optional[Tuple[int, int, str]] = None
    branch_outcome: Optional[BranchOutcome] = None
    latency_cycles: float = 0.0
    energy_estimate: float = 0.0
    cache_result: CacheResult = CacheResult.UNKNOWN


@dataclass
class ExecutionMetrics:
    instruction_count: int = 0
    actual_instruction_count: int = 0
    
    branch_mispredictions: int = 0
    total_branches: int = 0
    branch_hit_rate: float = 1.0
    
    cache_misses: int = 0
    total_memory_accesses: int = 0
    cache_hit_rate: float = 1.0
    
    memory_bandwidth_used: float = 0.0
    io_operations: int = 0
    thread_synchronizations: int = 0
    
    total_cycles: float = 0.0
    total_energy: float = 0.0
    
    deadlock_risk: float = 0.0
    data_race_risk: float = 0.0
    
    critical_path_length: int = 0
    parallelism_potential: float = 0.0
    
    register_usage: Dict[int, int] = field(default_factory=dict)
    memory_usage: Dict[int, int] = field(default_factory=dict)
    
    hot_instructions: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    hot_registers: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    execution_history: List[ExecutionStep] = field(default_factory=list)


class CacheModel:
    def __init__(self, size: int = 32768, line_size: int = 64, assoc: int = 8):
        self.size = size
        self.line_size = line_size
        self.assoc = assoc
        self.num_sets = (size // line_size) // assoc
        self.cache_lines: Dict[int, Dict[int, int]] = defaultdict(dict)
        self.lru_counter: Dict[int, int] = defaultdict(int)
    
    def access(self, address: int) -> CacheResult:
        line_addr = address // self.line_size
        set_idx = line_addr % self.num_sets
        tag = line_addr // self.num_sets
        
        if tag in self.cache_lines[set_idx]:
            self.lru_counter[set_idx] += 1
            self.cache_lines[set_idx][tag] = self.lru_counter[set_idx]
            return CacheResult.HIT
        
        if len(self.cache_lines[set_idx]) >= self.assoc:
            lru_tag = min(
                self.cache_lines[set_idx].keys(),
                key=lambda t: self.cache_lines[set_idx][t]
            )
            del self.cache_lines[set_idx][lru_tag]
        
        self.lru_counter[set_idx] += 1
        self.cache_lines[set_idx][tag] = self.lru_counter[set_idx]
        return CacheResult.MISS


class BranchPredictor:
    def __init__(self, history_size: int = 128):
        self.history_size = history_size
        self.predictor: Dict[int, int] = defaultdict(lambda: 1)
        self.global_history: int = 0
        self.history_mask = (1 << history_size) - 1 if history_size > 0 else 0
    
    def predict(self, pc: int) -> BranchOutcome:
        index = (pc ^ self.global_history) & self.history_mask if self.history_size > 0 else pc
        
        if self.predictor[index] >= 2:
            return BranchOutcome.TAKEN
        else:
            return BranchOutcome.NOT_TAKEN
    
    def update(self, pc: int, actual: BranchOutcome):
        index = (pc ^ self.global_history) & self.history_mask if self.history_size > 0 else pc
        
        if actual == BranchOutcome.TAKEN:
            self.predictor[index] = min(3, self.predictor[index] + 1)
            self.global_history = ((self.global_history << 1) | 1) & self.history_mask
        else:
            self.predictor[index] = max(0, self.predictor[index] - 1)
            self.global_history = (self.global_history << 1) & self.history_mask


class ResourceUsageAnalyzer:
    def __init__(self):
        self.register_lifetime: Dict[int, Tuple[int, int]] = {}
        self.memory_lifetime: Dict[int, Tuple[int, int]] = {}
        self.dependencies: List[Tuple[int, int, str]] = []
    
    def track_register_write(self, reg: int, step: int):
        if reg in self.register_lifetime:
            start, _ = self.register_lifetime[reg]
            self.register_lifetime[reg] = (start, step)
        else:
            self.register_lifetime[reg] = (step, step)
    
    def track_register_read(self, reg: int, step: int):
        if reg in self.register_lifetime:
            start, end = self.register_lifetime[reg]
            self.register_lifetime[reg] = (start, max(end, step))
    
    def track_memory_write(self, addr: int, step: int):
        if addr in self.memory_lifetime:
            start, _ = self.memory_lifetime[addr]
            self.memory_lifetime[addr] = (start, step)
        else:
            self.memory_lifetime[addr] = (step, step)
    
    def track_memory_read(self, addr: int, step: int):
        if addr in self.memory_lifetime:
            start, end = self.memory_lifetime[addr]
            self.memory_lifetime[addr] = (start, max(end, step))
    
    def add_dependency(self, from_step: int, to_step: int, dep_type: str):
        self.dependencies.append((from_step, to_step, dep_type))
    
    def calculate_critical_path(self) -> int:
        if not self.dependencies:
            return 1
        
        max_step = max(max(d[0], d[1]) for d in self.dependencies)
        
        in_degree = defaultdict(int)
        adj = defaultdict(list)
        
        for from_step, to_step, _ in self.dependencies:
            adj[from_step].append(to_step)
            in_degree[to_step] += 1
        
        from collections import deque
        queue = deque()
        for step in range(1, max_step + 2):
            if in_degree[step] == 0:
                queue.append(step)
        
        distances = {step: 1 for step in range(1, max_step + 2)}
        
        while queue:
            current = queue.popleft()
            
            for neighbor in adj[current]:
                in_degree[neighbor] -= 1
                if distances[neighbor] < distances[current] + 1:
                    distances[neighbor] = distances[current] + 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return max(distances.values()) if distances else 1


class EnhancedExecutionTracer:
    def __init__(self, 
                 use_cache_model: bool = True,
                 use_branch_predictor: bool = True,
                 max_history_size: int = 1000):
        
        self.use_cache_model = use_cache_model
        self.use_branch_predictor = use_branch_predictor
        self.max_history_size = max_history_size
        
        self.cache = CacheModel() if use_cache_model else None
        self.branch_predictor = BranchPredictor() if use_branch_predictor else None
        self.resource_analyzer = ResourceUsageAnalyzer()
        
        self.metrics = ExecutionMetrics()
        self.step_count = 0
        
        self.register_state: Dict[int, int] = {}
        for i in range(16):
            self.register_state[i] = 0
    
    def reset(self):
        self.metrics = ExecutionMetrics()
        self.step_count = 0
        
        self.register_state = {i: 0 for i in range(16)}
        
        if self.cache:
            self.cache = CacheModel()
        if self.branch_predictor:
            self.branch_predictor = BranchPredictor()
        self.resource_analyzer = ResourceUsageAnalyzer()
    
    def trace_instruction(self, 
                           opcode: int, 
                           operands: List[int],
                           is_branch: bool = False,
                           is_memory: bool = False,
                           branch_taken: bool = False,
                           memory_address: Optional[int] = None,
                           memory_size: int = 0) -> ExecutionStep:
        
        self.step_count += 1
        self.metrics.instruction_count += 1
        
        step = ExecutionStep(
            step_number=self.step_count,
            opcode=opcode,
            register_state=copy.deepcopy(self.register_state)
        )
        
        latency = self._estimate_latency(opcode, operands)
        energy = self._estimate_energy(opcode, operands)
        
        step.latency_cycles = latency
        step.energy_estimate = energy
        
        self.metrics.total_cycles += latency
        self.metrics.total_energy += energy
        
        if is_memory and memory_address is not None:
            self.metrics.total_memory_accesses += 1
            self.metrics.memory_bandwidth_used += memory_size
            
            step.memory_access = (memory_address, memory_size, "read" if operands else "write")
            
            if self.cache:
                cache_result = self.cache.access(memory_address)
                step.cache_result = cache_result
                
                if cache_result == CacheResult.MISS:
                    self.metrics.cache_misses += 1
            
            if memory_size > 0:
                self.resource_analyzer.track_memory_read(memory_address, self.step_count)
                self.resource_analyzer.track_memory_write(memory_address, self.step_count)
        
        if is_branch:
            self.metrics.total_branches += 1
            
            actual_outcome = BranchOutcome.TAKEN if branch_taken else BranchOutcome.NOT_TAKEN
            step.branch_outcome = actual_outcome
            
            if self.branch_predictor:
                predicted = self.branch_predictor.predict(opcode)
                
                if predicted != actual_outcome:
                    self.metrics.branch_mispredictions += 1
                    self.metrics.total_cycles += 10
                
                self.branch_predictor.update(opcode, actual_outcome)
        
        if operands:
            for i, operand in enumerate(operands):
                if i == 0 and isinstance(operand, int):
                    self.resource_analyzer.track_register_write(operand, self.step_count)
                    self.metrics.hot_registers[operand] += 1
                elif isinstance(operand, int):
                    self.resource_analyzer.track_register_read(operand, self.step_count)
                    self.metrics.hot_registers[operand] += 1
        
        self.metrics.hot_instructions[opcode] += 1
        
        if len(self.metrics.execution_history) < self.max_history_size:
            self.metrics.execution_history.append(step)
        
        return step
    
    def _estimate_latency(self, opcode: int, operands: List[int]) -> float:
        from evomorph.hexagrams.instruction_set import HEXAGRAM_CATEGORIES
        
        if opcode in HEXAGRAM_CATEGORIES.get("元", []):
            return 2.0
        elif opcode in HEXAGRAM_CATEGORIES.get("亨", []):
            return 1.0
        elif opcode in HEXAGRAM_CATEGORIES.get("利", []):
            return 0.5
        elif opcode in HEXAGRAM_CATEGORIES.get("贞", []):
            return 3.0
        
        return 1.0
    
    def _estimate_energy(self, opcode: int, operands: List[int]) -> float:
        from evomorph.hexagrams.instruction_set import HEXAGRAM_CATEGORIES
        
        base_energy = 0.1
        
        if opcode in HEXAGRAM_CATEGORIES.get("元", []):
            multiplier = 3.0
        elif opcode in HEXAGRAM_CATEGORIES.get("亨", []):
            multiplier = 2.0
        elif opcode in HEXAGRAM_CATEGORIES.get("利", []):
            multiplier = 1.0
        elif opcode in HEXAGRAM_CATEGORIES.get("贞", []):
            multiplier = 4.0
        else:
            multiplier = 1.5
        
        operand_factor = 1.0 + len(operands) * 0.1
        
        return base_energy * multiplier * operand_factor
    
    def finalize_metrics(self):
        if self.metrics.total_memory_accesses > 0:
            self.metrics.cache_hit_rate = (
                1.0 - self.metrics.cache_misses / self.metrics.total_memory_accesses
            )
        
        if self.metrics.total_branches > 0:
            self.metrics.branch_hit_rate = (
                1.0 - self.metrics.branch_mispredictions / self.metrics.total_branches
            )
        
        self.metrics.critical_path_length = self.resource_analyzer.calculate_critical_path()
        
        if self.metrics.critical_path_length > 0:
            self.metrics.parallelism_potential = (
                self.metrics.instruction_count / self.metrics.critical_path_length
            )
        
        self._assess_risks()
        
        self.metrics.register_usage = dict(self.resource_analyzer.register_lifetime)
        self.metrics.memory_usage = dict(self.resource_analyzer.memory_lifetime)
    
    def _assess_risks(self):
        deadlock_risk = 0.0
        data_race_risk = 0.0
        
        from evomorph.hexagrams.instruction_set import HEXAGRAM_CATEGORIES
        
        yuan_ops = HEXAGRAM_CATEGORIES.get("元", [])
        heng_ops = HEXAGRAM_CATEGORIES.get("亨", [])
        
        lock_ops = {58, 10, 39}
        sync_ops = {21, 61}
        thread_ops = {63, 34}
        
        lock_count = sum(1 for op, count in self.metrics.hot_instructions.items() 
                         if op in lock_ops)
        sync_count = sum(1 for op, count in self.metrics.hot_instructions.items() 
                         if op in sync_ops)
        thread_count = sum(1 for op, count in self.metrics.hot_instructions.items() 
                          if op in thread_ops)
        
        if lock_count > 0 and thread_count > 1:
            deadlock_risk += 0.3
        
        if lock_count > 2:
            deadlock_risk += 0.2
        
        if sync_count > 0 and thread_count > 1:
            data_race_risk += 0.4
        
        for addr, (start, end) in self.resource_analyzer.memory_lifetime.items():
            if end - start > 5:
                data_race_risk += 0.05
        
        self.metrics.deadlock_risk = min(1.0, deadlock_risk)
        self.metrics.data_race_risk = min(1.0, data_race_risk)
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        return {
            "instruction_count": self.metrics.instruction_count,
            "branch_mispredictions": self.metrics.branch_mispredictions,
            "branch_hit_rate": self.metrics.branch_hit_rate,
            "cache_misses": self.metrics.cache_misses,
            "cache_hit_rate": self.metrics.cache_hit_rate,
            "memory_bandwidth_bytes": self.metrics.memory_bandwidth_used,
            "io_operations": self.metrics.io_operations,
            "thread_synchronizations": self.metrics.thread_synchronizations,
            "total_cycles": self.metrics.total_cycles,
            "total_energy_nj": self.metrics.total_energy,
            "deadlock_risk": self.metrics.deadlock_risk,
            "data_race_risk": self.metrics.data_race_risk,
            "critical_path_length": self.metrics.critical_path_length,
            "parallelism_potential": self.metrics.parallelism_potential,
        }
    
    def get_hotspots(self, top_n: int = 5) -> Dict[str, List[Tuple[Any, int]]]:
        hot_insts = sorted(
            self.metrics.hot_instructions.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        hot_regs = sorted(
            self.metrics.hot_registers.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        return {
            "hot_instructions": hot_insts,
            "hot_registers": hot_regs,
        }


class BehaviorConsistencyChecker:
    def __init__(self):
        self.test_cases: List[Dict] = []
    
    def add_test_case(self, inputs: Dict[str, int], expected_outputs: Dict[str, int]):
        self.test_cases.append({
            "inputs": inputs,
            "expected_outputs": expected_outputs
        })
    
    def check_consistency(self, 
                          original_execution: ExecutionMetrics,
                          mutated_execution: ExecutionMetrics,
                          tolerance: float = 0.1) -> Tuple[bool, Dict[str, Any]]:
        
        issues = []
        is_consistent = True
        
        if abs(original_execution.total_cycles - mutated_execution.total_cycles) > tolerance:
            issues.append({
                "type": "performance_regression",
                "metric": "cycles",
                "original": original_execution.total_cycles,
                "mutated": mutated_execution.total_cycles,
                "ratio": mutated_execution.total_cycles / max(1, original_execution.total_cycles)
            })
        
        if abs(original_execution.total_energy - mutated_execution.total_energy) > tolerance:
            issues.append({
                "type": "energy_regression",
                "metric": "energy",
                "original": original_execution.total_energy,
                "mutated": mutated_execution.total_energy,
            })
        
        if original_execution.deadlock_risk < 0.3 and mutated_execution.deadlock_risk >= 0.3:
            issues.append({
                "type": "deadlock_introduced",
                "original_risk": original_execution.deadlock_risk,
                "mutated_risk": mutated_execution.deadlock_risk,
            })
            is_consistent = False
        
        if original_execution.data_race_risk < 0.3 and mutated_execution.data_race_risk >= 0.3:
            issues.append({
                "type": "data_race_introduced",
                "original_risk": original_execution.data_race_risk,
                "mutated_risk": mutated_execution.data_race_risk,
            })
            is_consistent = False
        
        return is_consistent, {
            "consistent": is_consistent,
            "issues": issues,
            "original_metrics": {
                "cycles": original_execution.total_cycles,
                "energy": original_execution.total_energy,
                "deadlock_risk": original_execution.deadlock_risk,
                "data_race_risk": original_execution.data_race_risk,
            },
            "mutated_metrics": {
                "cycles": mutated_execution.total_cycles,
                "energy": mutated_execution.total_energy,
                "deadlock_risk": mutated_execution.deadlock_risk,
                "data_race_risk": mutated_execution.data_race_risk,
            }
        }
