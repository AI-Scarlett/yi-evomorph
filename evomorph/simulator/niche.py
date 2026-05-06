# =============================================================================
# 平台模拟生态位
# =============================================================================
# IChing EVB 自举等价文件: niche_data.evo   (5平台性能配置)
#                        opcode_cost.evo  (64指令成本映射)
# AI模型可阅读上述 .evo 文件了解Evomorph在各平台的性能特征
# =============================================================================
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class PlatformType(Enum):
    LINUX = "linux"
    ANDROID = "android"
    IOS = "ios"
    WINDOWS = "windows"
    HARMONY = "harmony"


@dataclass
class PlatformProfile:
    name: str
    platform_type: PlatformType
    version: str
    syscall_cost: Dict[str, float] = field(default_factory=dict)
    memory_latency_ns: float = 100.0
    thread_create_cost: float = 50.0
    lock_cost: float = 10.0
    sync_cost: float = 20.0
    io_cost: float = 100.0
    energy_per_cycle: float = 1.0
    simd_available: bool = False
    max_threads: int = 8
    cache_line_size: int = 64
    page_size: int = 4096


PLATFORM_PROFILES = {
    "linux-6.x": PlatformProfile(
        name="linux-6.x", platform_type=PlatformType.LINUX, version="6.x",
        syscall_cost={"clone": 30.0, "mmap": 20.0, "futex": 5.0},
        memory_latency_ns=80.0, thread_create_cost=30.0,
        lock_cost=5.0, sync_cost=15.0, io_cost=80.0,
        energy_per_cycle=0.8, simd_available=True, max_threads=128,
    ),
    "android-14": PlatformProfile(
        name="android-14", platform_type=PlatformType.ANDROID, version="14",
        syscall_cost={"clone": 40.0, "mmap": 25.0, "futex": 8.0},
        memory_latency_ns=120.0, thread_create_cost=40.0,
        lock_cost=8.0, sync_cost=20.0, io_cost=120.0,
        energy_per_cycle=1.5, simd_available=True, max_threads=16,
    ),
    "ios-18": PlatformProfile(
        name="ios-18", platform_type=PlatformType.IOS, version="18",
        syscall_cost={"clone": 25.0, "mmap": 15.0, "futex": 3.0},
        memory_latency_ns=60.0, thread_create_cost=25.0,
        lock_cost=3.0, sync_cost=10.0, io_cost=60.0,
        energy_per_cycle=0.6, simd_available=True, max_threads=8,
    ),
    "win-11": PlatformProfile(
        name="win-11", platform_type=PlatformType.WINDOWS, version="11",
        syscall_cost={"clone": 35.0, "mmap": 22.0, "futex": 6.0},
        memory_latency_ns=90.0, thread_create_cost=35.0,
        lock_cost=6.0, sync_cost=18.0, io_cost=90.0,
        energy_per_cycle=1.0, simd_available=True, max_threads=64,
    ),
    "harmony-5": PlatformProfile(
        name="harmony-5", platform_type=PlatformType.HARMONY, version="5",
        syscall_cost={"clone": 35.0, "mmap": 20.0, "futex": 5.0},
        memory_latency_ns=100.0, thread_create_cost=35.0,
        lock_cost=7.0, sync_cost=16.0, io_cost=100.0,
        energy_per_cycle=1.2, simd_available=True, max_threads=32,
    ),
}

OPCODE_COST_MAP = {
    63: "thread_create",
    0:  "io",
    17: "memory",
    34: "memory",
    23: "sync",
    58: "lock",
    2:  "branch",
    16: "memory",
    55: "memory",
    59: "compute",
    7:  "memory",
    56: "sync",
    61: "sync",
    47: "memory",
    4:  "sync",
    8:  "compute",
    25: "memory",
    38: "compute",
    3:  "sync",
    48: "compute",
    41: "compute",
    37: "compute",
    32: "memory",
    1:  "branch",
    57: "compute",
    39: "sync",
    33: "memory",
    30: "sync",
    18: "sync",
    45: "io",
    28: "sync",
    14: "io",
    60: "sync",
    15: "compute",
    40: "compute",
    5:  "compute",
    53: "memory",
    43: "compute",
    20: "sync",
    10: "lock",
    35: "compute",
    49: "compute",
    31: "branch",
    62: "compute",
    24: "compute",
    6:  "memory",
    26: "sync",
    22: "memory",
    29: "memory",
    46: "compute",
    9:  "sync",
    36: "sync",
    52: "compute",
    11: "sync",
    13: "memory",
    44: "sync",
    54: "memory",
    27: "sync",
    50: "memory",
    19: "sync",
    51: "compute",
    12: "compute",
    21: "sync",
    42: "sync",
}

BASE_COSTS = {
    "thread_create": 50.0,
    "io": 100.0,
    "memory": 10.0,
    "sync": 20.0,
    "lock": 15.0,
    "branch": 5.0,
    "compute": 2.0,
}


class PlatformSimNiche:
    def __init__(self):
        self.profiles: Dict[str, PlatformProfile] = dict(PLATFORM_PROFILES)
        self.custom_profiles: Dict[str, PlatformProfile] = {}

    def register_profile(self, profile: PlatformProfile):
        self.custom_profiles[profile.name] = profile
        self.profiles[profile.name] = profile

    def get_profile(self, platform_name: str) -> Optional[PlatformProfile]:
        return self.profiles.get(platform_name)

    def list_platforms(self) -> List[str]:
        return list(self.profiles.keys())

    def evaluate(self, individual, platform_name: str) -> float:
        profile = self.profiles.get(platform_name)
        if not profile:
            return 0.0
        total_latency = 0.0
        total_energy = 0.0
        thread_count = 0
        for gene in individual.genes:
            cost_type = OPCODE_COST_MAP.get(gene.opcode, "compute")
            base = BASE_COSTS.get(cost_type, 2.0)
            if cost_type == "thread_create":
                latency = profile.thread_create_cost
                thread_count += 1
            elif cost_type == "io":
                latency = profile.io_cost
            elif cost_type == "memory":
                latency = profile.memory_latency_ns
            elif cost_type == "sync":
                latency = profile.sync_cost
            elif cost_type == "lock":
                latency = profile.lock_cost
            else:
                latency = base
            total_latency += latency
            total_energy += latency * profile.energy_per_cycle
        if thread_count > profile.max_threads:
            total_latency *= (1.0 + (thread_count - profile.max_threads) * 0.5)
        throughput = 1000.0 / max(total_latency, 1.0)
        energy_eff = 1000.0 / max(total_energy, 1.0)
        code_size = len(individual.genes) * 6
        score = (throughput * 2.0) - (total_latency * 0.01) - (total_energy * 0.1) - (code_size * 0.05)
        return score

    def evaluate_all_platforms(self, individual) -> Dict[str, float]:
        results = {}
        for name in self.profiles:
            results[name] = self.evaluate(individual, name)
        return results

    def simulate_execution(self, individual, platform_name: str, input_size: int = 1000) -> Dict:
        profile = self.profiles.get(platform_name)
        if not profile:
            return {"error": f"Unknown platform: {platform_name}"}
        total_cycles = 0
        total_energy = 0.0
        memory_accesses = 0
        io_operations = 0
        sync_operations = 0
        for gene in individual.genes:
            cost_type = OPCODE_COST_MAP.get(gene.opcode, "compute")
            base = BASE_COSTS.get(cost_type, 2.0)
            if cost_type == "memory":
                cycles = int(profile.memory_latency_ns / 10)
                memory_accesses += 1
            elif cost_type == "io":
                cycles = int(profile.io_cost / 10)
                io_operations += 1
            elif cost_type == "sync":
                cycles = int(profile.sync_cost / 10)
                sync_operations += 1
            elif cost_type == "lock":
                cycles = int(profile.lock_cost / 10)
                sync_operations += 1
            elif cost_type == "thread_create":
                cycles = int(profile.thread_create_cost / 10)
            else:
                cycles = max(1, int(base / 10))
            total_cycles += cycles * input_size
            total_energy += cycles * profile.energy_per_cycle * input_size
        return {
            "platform": platform_name,
            "total_cycles": total_cycles,
            "estimated_latency_ms": total_cycles * 0.001,
            "total_energy_mj": total_energy * 0.001,
            "memory_accesses": memory_accesses * input_size,
            "io_operations": io_operations * input_size,
            "sync_operations": sync_operations * input_size,
            "code_size_bytes": len(individual.genes) * 6,
        }
