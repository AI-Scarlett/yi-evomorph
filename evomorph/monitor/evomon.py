import time
import json
import os
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class MonitorState(Enum):
    IDLE = "idle"
    COLLECTING = "collecting"
    EVOLVING = "evolving"
    REPORTING = "reporting"


@dataclass
class PerformanceSample:
    timestamp: float
    function_name: str
    latency_ms: float
    energy_mj: float = 0.0
    memory_bytes: int = 0
    cpu_cycles: int = 0
    platform: str = "unknown"
    metadata: Dict = field(default_factory=dict)


@dataclass
class HotPath:
    function_name: str
    call_count: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    total_energy_mj: float = 0.0
    is_hot: bool = False


class EvoMon:
    def __init__(self, config_path: Optional[str] = None):
        self.state = MonitorState.IDLE
        self.samples: List[PerformanceSample] = []
        self.hot_paths: Dict[str, HotPath] = {}
        self.evolution_suggestions: List[Dict] = []
        self.collection_interval: float = 1.0
        self.hot_threshold: float = 100.0
        self.max_samples: int = 100000
        self.report_callback: Optional[Callable] = None
        self.evolution_trigger: Optional[Callable] = None
        self._config_path = config_path
        self._start_time = time.time()
        if config_path:
            self._load_config(config_path)

    def _load_config(self, path: str):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            self.collection_interval = config.get("collection_interval", 1.0)
            self.hot_threshold = config.get("hot_threshold", 100.0)
            self.max_samples = config.get("max_samples", 100000)

    def record_sample(self, sample: PerformanceSample):
        self.samples.append(sample)
        if len(self.samples) > self.max_samples:
            self.samples = self.samples[-self.max_samples:]
        self._update_hot_path(sample)

    def _update_hot_path(self, sample: PerformanceSample):
        if sample.function_name not in self.hot_paths:
            self.hot_paths[sample.function_name] = HotPath(
                function_name=sample.function_name
            )
        hp = self.hot_paths[sample.function_name]
        hp.call_count += 1
        hp.total_latency_ms += sample.latency_ms
        hp.avg_latency_ms = hp.total_latency_ms / hp.call_count
        hp.max_latency_ms = max(hp.max_latency_ms, sample.latency_ms)
        hp.total_energy_mj += sample.energy_mj
        hp.is_hot = hp.avg_latency_ms > self.hot_threshold or hp.call_count > 1000

    def get_hot_paths(self) -> List[HotPath]:
        return sorted(
            [hp for hp in self.hot_paths.values() if hp.is_hot],
            key=lambda x: x.total_latency_ms,
            reverse=True,
        )

    def suggest_evolution(self) -> List[Dict]:
        suggestions = []
        for hp in self.get_hot_paths():
            suggestion = {
                "locus_name": hp.function_name,
                "reason": "high_latency" if hp.avg_latency_ms > self.hot_threshold else "high_frequency",
                "current_avg_latency_ms": hp.avg_latency_ms,
                "call_count": hp.call_count,
                "total_energy_mj": hp.total_energy_mj,
                "suggested_fitness": "min_latency + min_energy",
                "priority": "high" if hp.avg_latency_ms > self.hot_threshold * 2 else "medium",
            }
            suggestions.append(suggestion)
        self.evolution_suggestions = suggestions
        return suggestions

    def should_trigger_evolution(self) -> bool:
        hot = self.get_hot_paths()
        if not hot:
            return False
        critical = [hp for hp in hot if hp.avg_latency_ms > self.hot_threshold * 3]
        return len(critical) > 0

    def trigger_background_evolution(self, engine, locus_name: str):
        if self.evolution_trigger:
            self.evolution_trigger(engine, locus_name)
        self.state = MonitorState.EVOLVING

    def generate_report(self) -> Dict:
        uptime = time.time() - self._start_time
        total_calls = sum(hp.call_count for hp in self.hot_paths.values())
        total_latency = sum(hp.total_latency_ms for hp in self.hot_paths.values())
        total_energy = sum(hp.total_energy_mj for hp in self.hot_paths.values())
        return {
            "uptime_seconds": uptime,
            "total_samples": len(self.samples),
            "total_calls": total_calls,
            "total_latency_ms": total_latency,
            "total_energy_mj": total_energy,
            "hot_paths_count": len(self.get_hot_paths()),
            "hot_paths": [
                {
                    "name": hp.function_name,
                    "calls": hp.call_count,
                    "avg_latency_ms": hp.avg_latency_ms,
                    "total_energy_mj": hp.total_energy_mj,
                }
                for hp in self.get_hot_paths()[:20]
            ],
            "evolution_suggestions": self.evolution_suggestions[:10],
            "state": self.state.value,
        }

    def export_metrics(self, filepath: str):
        report = self.generate_report()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    def reset(self):
        self.samples = []
        self.hot_paths = {}
        self.evolution_suggestions = []
        self._start_time = time.time()
        self.state = MonitorState.IDLE
