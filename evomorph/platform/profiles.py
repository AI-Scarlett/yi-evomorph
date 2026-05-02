import copy
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set, Any, Callable
from collections import defaultdict


class ArchitectureType(Enum):
    X86_64 = "x86_64"
    ARM64 = "arm64"
    RISC_V = "riscv64"
    WASM = "wasm"
    EVM = "evm"


class PlatformOS(Enum):
    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "macos"
    ANDROID = "android"
    IOS = "ios"
    HARMONY = "harmonyos"
    WASI = "wasi"


class CPUFeature(Enum):
    SSE = "sse"
    SSE2 = "sse2"
    SSE3 = "sse3"
    SSSE3 = "ssse3"
    SSE41 = "sse4.1"
    SSE42 = "sse4.2"
    AVX = "avx"
    AVX2 = "avx2"
    AVX512 = "avx512"
    NEON = "neon"
    SVE = "sve"
    BMI = "bmi"
    BMI2 = "bmi2"
    LZCNT = "lzcnt"
    POPCNT = "popcnt"
    AES = "aes"
    SHA = "sha"


@dataclass
class CacheLevel:
    size: int = 32768
    line_size: int = 64
    associativity: int = 8
    hit_latency_cycles: float = 4.0
    miss_penalty_cycles: float = 12.0
    is_shared: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "size_bytes": self.size,
            "size_kb": self.size // 1024,
            "size_mb": self.size // (1024 * 1024),
            "line_size": self.line_size,
            "associativity": self.associativity,
            "hit_latency": self.hit_latency_cycles,
            "miss_penalty": self.miss_penalty_cycles,
            "is_shared": self.is_shared,
        }


@dataclass
class MemoryController:
    bandwidth_bytes_per_cycle: float = 64.0
    latency_cycles: float = 200.0
    channels: int = 1
    ranks_per_channel: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bandwidth_bpc": self.bandwidth_bytes_per_cycle,
            "bandwidth_gbps_3ghz": self.bandwidth_bytes_per_cycle * 3e9 / 1e9,
            "latency_cycles": self.latency_cycles,
            "channels": self.channels,
            "ranks_per_channel": self.ranks_per_channel,
        }


@dataclass
class CPUCoreProfile:
    frequency_ghz: float = 3.0
    pipeline_depth: int = 14
    superscalar_width: int = 4
    issue_width: int = 4
    retire_width: int = 4
    out_of_order: bool = True
    reorder_buffer_size: int = 128
    reservation_stations: int = 32
    load_store_queue_size: int = 32
    
    branch_predictor_size: int = 1024
    btb_entries: int = 512
    ras_entries: int = 16
    mispredict_penalty: int = 14
    
    simd_width: int = 128
    num_fp_units: int = 2
    num_int_units: int = 4
    num_load_units: int = 2
    num_store_units: int = 1
    
    features: Set[CPUFeature] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "frequency_ghz": self.frequency_ghz,
            "pipeline_depth": self.pipeline_depth,
            "superscalar_width": self.superscalar_width,
            "issue_width": self.issue_width,
            "retire_width": self.retire_width,
            "out_of_order": self.out_of_order,
            "reorder_buffer_size": self.reorder_buffer_size,
            "features": [f.value for f in self.features],
        }


@dataclass
class OSProfile:
    os_type: PlatformOS
    version: str = ""
    
    syscall_latency_median_cycles: float = 1000.0
    syscall_latency_p99_cycles: float = 5000.0
    
    scheduler_quantum_ms: float = 1.0
    context_switch_cycles: float = 2000.0
    
    page_size: int = 4096
    huge_page_sizes: List[int] = field(default_factory=list)
    
    tlb_entries: int = 256
    tlb_miss_latency_cycles: float = 200.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "os": self.os_type.value,
            "version": self.version,
            "syscall_latency_median": self.syscall_latency_median_cycles,
            "context_switch_cycles": self.context_switch_cycles,
            "page_size": self.page_size,
        }


@dataclass
class PowerModel:
    idle_power_w: float = 5.0
    active_power_per_core_w: float = 10.0
    memory_power_per_gb_w: float = 0.5
    
    dynamic_power_factor: float = 1.0
    leakage_power_factor: float = 0.3
    
    instruction_power: Dict[str, float] = field(default_factory=lambda: {
        "arithmetic": 0.1,
        "memory": 0.5,
        "branch": 0.2,
        "simd": 0.3,
        "system": 2.0,
    })
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "idle_power_w": self.idle_power_w,
            "active_power_per_core_w": self.active_power_per_core_w,
            "instruction_power": copy.deepcopy(self.instruction_power),
        }


@dataclass
class DetailedPlatformProfile:
    name: str
    architecture: ArchitectureType
    os: OSProfile
    
    cores: int = 4
    threads_per_core: int = 2
    
    cpu_profile: CPUCoreProfile = field(default_factory=CPUCoreProfile)
    
    cache_hierarchy: List[CacheLevel] = field(default_factory=list)
    memory_controller: MemoryController = field(default_factory=MemoryController)
    
    power_model: PowerModel = field(default_factory=PowerModel)
    
    instruction_latencies: Dict[int, float] = field(default_factory=dict)
    instruction_throughputs: Dict[int, float] = field(default_factory=dict)
    
    max_inline_depth: int = 3
    prefer_vectorization: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "architecture": self.architecture.value,
            "os": self.os.to_dict(),
            "cores": self.cores,
            "threads_per_core": self.threads_per_core,
            "cpu_profile": self.cpu_profile.to_dict(),
            "cache_hierarchy": [c.to_dict() for c in self.cache_hierarchy],
            "memory_controller": self.memory_controller.to_dict(),
            "power_model": self.power_model.to_dict(),
        }


class PlatformProfileRegistry:
    _profiles: Dict[str, DetailedPlatformProfile] = {}
    
    @classmethod
    def register(cls, profile: DetailedPlatformProfile):
        cls._profiles[profile.name] = profile
    
    @classmethod
    def get(cls, name: str) -> Optional[DetailedPlatformProfile]:
        return cls._profiles.get(name)
    
    @classmethod
    def list_all(cls) -> List[str]:
        return list(cls._profiles.keys())
    
    @classmethod
    def match_by_target(cls, env_target: str) -> Optional[DetailedPlatformProfile]:
        parts = env_target.lower().split("-")
        
        candidates = []
        for name, profile in cls._profiles.items():
            match_score = 0
            
            if profile.architecture.value in env_target:
                match_score += 10
            if profile.os.os_type.value in env_target:
                match_score += 10
            
            for part in parts:
                if part in name.lower():
                    match_score += 1
            
            if match_score > 0:
                candidates.append((-match_score, profile))
        
        if candidates:
            candidates.sort()
            return candidates[0][1]
        
        return None


def _create_x86_64_linux_profile() -> DetailedPlatformProfile:
    profile = DetailedPlatformProfile(
        name="linux-x86_64-generic",
        architecture=ArchitectureType.X86_64,
        os=OSProfile(
            os_type=PlatformOS.LINUX,
            syscall_latency_median_cycles=800.0,
            syscall_latency_p99_cycles=3000.0,
            context_switch_cycles=1500.0,
            page_size=4096,
            huge_page_sizes=[2097152, 1073741824],
            tlb_entries=1024,
        ),
        cores=8,
        threads_per_core=2,
        cpu_profile=CPUCoreProfile(
            frequency_ghz=3.5,
            pipeline_depth=14,
            superscalar_width=4,
            issue_width=4,
            retire_width=4,
            out_of_order=True,
            reorder_buffer_size=224,
            reservation_stations=97,
            load_store_queue_size=72,
            branch_predictor_size=4096,
            btb_entries=4096,
            ras_entries=16,
            mispredict_penalty=16,
            simd_width=256,
            num_fp_units=4,
            num_int_units=4,
            num_load_units=3,
            num_store_units=2,
            features={
                CPUFeature.SSE, CPUFeature.SSE2, CPUFeature.SSE3, CPUFeature.SSSE3,
                CPUFeature.SSE41, CPUFeature.SSE42, CPUFeature.AVX, CPUFeature.AVX2,
                CPUFeature.BMI, CPUFeature.BMI2, CPUFeature.LZCNT, CPUFeature.POPCNT,
                CPUFeature.AES,
            },
        ),
        cache_hierarchy=[
            CacheLevel(
                size=32 * 1024,
                line_size=64,
                associativity=8,
                hit_latency_cycles=4,
                miss_penalty_cycles=12,
                is_shared=False,
            ),
            CacheLevel(
                size=256 * 1024,
                line_size=64,
                associativity=8,
                hit_latency_cycles=12,
                miss_penalty_cycles=36,
                is_shared=False,
            ),
            CacheLevel(
                size=8 * 1024 * 1024,
                line_size=64,
                associativity=16,
                hit_latency_cycles=36,
                miss_penalty_cycles=200,
                is_shared=True,
            ),
        ],
        memory_controller=MemoryController(
            bandwidth_bytes_per_cycle=64.0,
            latency_cycles=200.0,
            channels=2,
            ranks_per_channel=2,
        ),
        power_model=PowerModel(
            idle_power_w=10.0,
            active_power_per_core_w=15.0,
            memory_power_per_gb_w=0.3,
        ),
    )
    
    return profile


def _create_arm64_android_profile() -> DetailedPlatformProfile:
    profile = DetailedPlatformProfile(
        name="android-arm64-generic",
        architecture=ArchitectureType.ARM64,
        os=OSProfile(
            os_type=PlatformOS.ANDROID,
            version="14",
            syscall_latency_median_cycles=1200.0,
            syscall_latency_p99_cycles=8000.0,
            context_switch_cycles=2000.0,
            page_size=4096,
            tlb_entries=512,
        ),
        cores=8,
        threads_per_core=1,
        cpu_profile=CPUCoreProfile(
            frequency_ghz=2.8,
            pipeline_depth=12,
            superscalar_width=3,
            issue_width=3,
            retire_width=3,
            out_of_order=True,
            reorder_buffer_size=128,
            branch_predictor_size=2048,
            mispredict_penalty=12,
            simd_width=128,
            features={CPUFeature.NEON},
        ),
        cache_hierarchy=[
            CacheLevel(
                size=64 * 1024,
                line_size=64,
                associativity=4,
                hit_latency_cycles=3,
                miss_penalty_cycles=10,
            ),
            CacheLevel(
                size=512 * 1024,
                line_size=64,
                associativity=8,
                hit_latency_cycles=10,
                miss_penalty_cycles=28,
            ),
            CacheLevel(
                size=4 * 1024 * 1024,
                line_size=64,
                associativity=16,
                hit_latency_cycles=28,
                miss_penalty_cycles=180,
                is_shared=True,
            ),
        ],
        memory_controller=MemoryController(
            bandwidth_bytes_per_cycle=32.0,
            latency_cycles=180.0,
        ),
        power_model=PowerModel(
            idle_power_w=2.0,
            active_power_per_core_w=4.0,
        ),
    )
    return profile


def _create_ios_arm64_profile() -> DetailedPlatformProfile:
    profile = DetailedPlatformProfile(
        name="ios-arm64-generic",
        architecture=ArchitectureType.ARM64,
        os=OSProfile(
            os_type=PlatformOS.IOS,
            version="18",
            syscall_latency_median_cycles=900.0,
            syscall_latency_p99_cycles=4000.0,
            context_switch_cycles=1200.0,
        ),
        cores=6,
        cpu_profile=CPUCoreProfile(
            frequency_ghz=3.2,
            pipeline_depth=14,
            superscalar_width=4,
            mispredict_penalty=14,
            features={CPUFeature.NEON},
        ),
        cache_hierarchy=[
            CacheLevel(size=192 * 1024, line_size=128, associativity=6, hit_latency_cycles=3),
            CacheLevel(size=8 * 1024 * 1024, line_size=128, associativity=16, hit_latency_cycles=20),
        ],
        power_model=PowerModel(
            idle_power_w=1.5,
            active_power_per_core_w=3.5,
        ),
    )
    return profile


def _create_wasm_profile() -> DetailedPlatformProfile:
    profile = DetailedPlatformProfile(
        name="wasm-wasi-generic",
        architecture=ArchitectureType.WASM,
        os=OSProfile(
            os_type=PlatformOS.WASI,
            syscall_latency_median_cycles=5000.0,
            context_switch_cycles=5000.0,
        ),
        cores=1,
        threads_per_core=1,
        cpu_profile=CPUCoreProfile(
            frequency_ghz=1.0,
            pipeline_depth=1,
            superscalar_width=1,
            out_of_order=False,
            simd_width=128,
            features=set(),
        ),
        cache_hierarchy=[
            CacheLevel(size=0, line_size=64, associativity=1, hit_latency_cycles=0, miss_penalty_cycles=0),
        ],
        memory_controller=MemoryController(
            bandwidth_bytes_per_cycle=8.0,
            latency_cycles=100.0,
        ),
        power_model=PowerModel(
            idle_power_w=0.0,
            active_power_per_core_w=0.0,
        ),
    )
    return profile


PlatformProfileRegistry.register(_create_x86_64_linux_profile())
PlatformProfileRegistry.register(_create_arm64_android_profile())
PlatformProfileRegistry.register(_create_ios_arm64_profile())
PlatformProfileRegistry.register(_create_wasm_profile())


class PlatformPerformanceEstimator:
    def __init__(self, profile: DetailedPlatformProfile):
        self.profile = profile
        self._instruction_cycles: Dict[int, float] = {}
        self._init_latencies()
    
    def _init_latencies(self):
        base_latencies = {
            "arithmetic": 1.0,
            "memory_load": 4.0,
            "memory_store": 1.0,
            "branch": 1.0,
            "branch_taken": 2.0,
            "system": 100.0,
            "simd": 2.0,
            "synchronization": 5.0,
        }
        
        if self.profile.instruction_latencies:
            self._instruction_cycles.update(self.profile.instruction_latencies)
    
    def estimate_instruction_latency(self, 
                                       opcode: int,
                                       operands: List[Any],
                                       context: Optional[Dict[str, Any]] = None) -> float:
        from evomorph.hexagrams.instruction_set import HEXAGRAM_CATEGORIES
        
        category = None
        for cat_name, opcodes in HEXAGRAM_CATEGORIES.items():
            if opcode in opcodes:
                category = cat_name
                break
        
        if category == "元":
            return self.profile.cpu_profile.pipeline_depth * 0.5
        
        elif category == "亨":
            return 2.0
        
        elif category == "利":
            return 1.0
        
        elif category == "贞":
            return 3.0
        
        return 1.0
    
    def estimate_memory_access_latency(self, 
                                         address: int,
                                         is_write: bool = False,
                                         size_bytes: int = 8) -> float:
        cycles = 0.0
        current_penalty = 0.0
        
        for cache_level in self.profile.cache_hierarchy:
            line_address = address // cache_level.line_size
            
            cycles += cache_level.hit_latency_cycles
            
            if self._simulate_cache_hit(cache_level, line_address):
                return cycles
            
            current_penalty = cache_level.miss_penalty_cycles
        
        cycles += self.profile.memory_controller.latency_cycles
        
        return cycles
    
    def _simulate_cache_hit(self, cache: CacheLevel, line_addr: int) -> bool:
        import random
        hit_probability = 0.95 if cache.size >= 1024 * 1024 else 0.9
        return random.random() < hit_probability
    
    def estimate_branch_misprediction_penalty(self) -> float:
        return self.profile.cpu_profile.mispredict_penalty
    
    def estimate_throughput(self, 
                              instruction_sequence: List[Dict],
                              window_size: int = 100) -> Dict[str, float]:
        if not instruction_sequence:
            return {"ipc": 0.0, "total_cycles": 0.0}
        
        total_cycles = 0.0
        total_instructions = len(instruction_sequence)
        
        issue_width = self.profile.cpu_profile.issue_width
        cycles_needed = (total_instructions + issue_width - 1) // issue_width
        
        memory_bound_factor = 1.0
        for instr in instruction_sequence:
            opcode = instr.get("opcode", 0)
            if self._is_memory_instruction(opcode):
                memory_bound_factor = max(memory_bound_factor, 1.5)
        
        total_cycles = cycles_needed * memory_bound_factor
        
        return {
            "ipc": total_instructions / max(total_cycles, 1),
            "total_cycles": total_cycles,
            "issue_width": issue_width,
        }
    
    def _is_memory_instruction(self, opcode: int) -> bool:
        memory_opcodes = {17, 34, 47, 6, 22, 54, 50}
        return opcode in memory_opcodes
    
    def estimate_energy(self,
                         instruction_count: int,
                         memory_accesses: int,
                         branches: int,
                         cycles: float) -> Dict[str, float]:
        power = self.profile.power_model
        
        instruction_energy = instruction_count * power.instruction_power.get("arithmetic", 0.1)
        memory_energy = memory_accesses * power.instruction_power.get("memory", 0.5)
        branch_energy = branches * power.instruction_power.get("branch", 0.2)
        
        active_energy = (cycles / (self.profile.cpu_profile.frequency_ghz * 1e9)) * power.active_power_per_core_w
        
        total_energy = instruction_energy + memory_energy + branch_energy + active_energy
        
        return {
            "instruction_energy_nj": instruction_energy,
            "memory_energy_nj": memory_energy,
            "branch_energy_nj": branch_energy,
            "active_energy_nj": active_energy,
            "total_energy_nj": total_energy,
        }


class DynamicProfileCollector:
    def __init__(self):
        self.instruction_counts: Dict[int, int] = defaultdict(int)
        self.register_usage: Dict[int, int] = defaultdict(int)
        self.memory_accesses: Dict[int, int] = defaultdict(int)
        self.branch_outcomes: List[Tuple[int, bool]] = []
        self.hot_paths: List[List[int]] = []
        self.total_cycles: float = 0.0
        self.total_instructions: int = 0
    
    def record_instruction(self, opcode: int, pc: int):
        self.instruction_counts[opcode] += 1
        self.total_instructions += 1
    
    def record_memory_access(self, address: int, is_write: bool, size: int):
        self.memory_accesses[address] += 1
    
    def record_branch(self, pc: int, taken: bool):
        self.branch_outcomes.append((pc, taken))
    
    def record_register_use(self, reg: int):
        self.register_usage[reg] += 1
    
    def get_hot_instructions(self, top_n: int = 10) -> List[Tuple[int, int]]:
        sorted_instr = sorted(self.instruction_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_instr[:top_n]
    
    def get_branch_accuracy(self) -> float:
        if not self.branch_outcomes:
            return 1.0
        
        taken_count = sum(1 for _, taken in self.branch_outcomes if taken)
        not_taken_count = len(self.branch_outcomes) - taken_count
        
        majority = max(taken_count, not_taken_count)
        return majority / len(self.branch_outcomes)
    
    def merge(self, other: 'DynamicProfileCollector'):
        for opcode, count in other.instruction_counts.items():
            self.instruction_counts[opcode] += count
        for reg, count in other.register_usage.items():
            self.register_usage[reg] += count
        for addr, count in other.memory_accesses.items():
            self.memory_accesses[addr] += count
        self.branch_outcomes.extend(other.branch_outcomes)
        self.total_cycles += other.total_cycles
        self.total_instructions += other.total_instructions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_instructions": self.total_instructions,
            "total_cycles": self.total_cycles,
            "hot_instructions": self.get_hot_instructions(),
            "branch_accuracy": self.get_branch_accuracy(),
            "unique_memory_addresses": len(self.memory_accesses),
        }
