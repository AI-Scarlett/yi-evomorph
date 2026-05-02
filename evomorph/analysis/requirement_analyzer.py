"""
需求深度分析模块
- 计算模式识别
- 功能需求提取
- 非功能需求识别
- 需求可追溯性
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Optional,
    List,
    Dict,
    Any,
    Tuple,
    Set,
    Union,
)


class RequirementType(Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAIN = "constrain"
    ASSUMPTION = "assumption"


class ComputingPattern(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    MAP_REDUCE = "map_reduce"
    STREAMING = "streaming"
    EVENT_DRIVEN = "event_driven"
    BATCH = "batch"
    REAL_TIME = "real_time"


class PerformanceGoal(Enum):
    MIN_LATENCY = "min_latency"
    MAX_THROUGHPUT = "max_throughput"
    MIN_ENERGY = "min_energy"
    MIN_SIZE = "min_size"
    HIGH_AVAILABILITY = "high_availability"
    SCALABILITY = "scalability"


class AmbiguityLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FunctionalRequirement:
    id: str = ""
    description: str = ""
    action: str = ""
    subject: str = ""
    object: str = ""
    conditions: List[str] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    confidence: float = 1.0
    source_text: str = ""
    extracted_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "action": self.action,
            "subject": self.subject,
            "object": self.object,
            "conditions": self.conditions,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "confidence": self.confidence,
        }


@dataclass
class NonFunctionalRequirement:
    id: str = ""
    description: str = ""
    category: str = ""
    target_value: Optional[float] = None
    unit: str = ""
    target_operation: str = "min"
    related_goals: List[PerformanceGoal] = field(default_factory=list)
    source_text: str = ""
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "category": self.category,
            "target_value": self.target_value,
            "unit": self.unit,
            "target_operation": self.target_operation,
            "related_goals": [g.value for g in self.related_goals],
            "confidence": self.confidence,
        }


@dataclass
class RequirementAnalysis:
    original_text: str = ""
    functional_requirements: List[FunctionalRequirement] = field(default_factory=list)
    non_functional_requirements: List[NonFunctionalRequirement] = field(default_factory=list)
    computing_patterns: List[ComputingPattern] = field(default_factory=list)
    target_platforms: List[str] = field(default_factory=list)
    performance_goals: List[PerformanceGoal] = field(default_factory=list)
    ambiguities: List["Ambiguity"] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_text": self.original_text,
            "functional_requirements": [r.to_dict() for r in self.functional_requirements],
            "non_functional_requirements": [r.to_dict() for r in self.non_functional_requirements],
            "computing_patterns": [p.value for p in self.computing_patterns],
            "target_platforms": self.target_platforms,
            "performance_goals": [g.value for g in self.performance_goals],
            "ambiguities": [a.to_dict() for a in self.ambiguities],
            "keywords": self.keywords,
            "entities": self.entities,
            "actions": self.actions,
        }


@dataclass
class Ambiguity:
    id: str = ""
    text: str = ""
    level: AmbiguityLevel = AmbiguityLevel.MEDIUM
    category: str = ""
    possible_interpretations: List[str] = field(default_factory=list)
    suggestion: str = ""
    context: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "level": self.level.value,
            "category": self.category,
            "possible_interpretations": self.possible_interpretations,
            "suggestion": self.suggestion,
        }


class KeywordExtractor:
    def __init__(self):
        self._domain_keywords: Dict[str, List[str]] = {
            "action": [
                "创建", "生成", "计算", "处理", "转换", "传输", "接收", "发送",
                "读取", "写入", "存储", "加载", "保存", "删除", "更新", "修改",
                "执行", "运行", "启动", "停止", "暂停", "继续", "等待", "同步",
                "并行", "并发", "串行", "批量", "实时", "异步", "同步",
                "create", "generate", "compute", "process", "transform", "transfer",
                "receive", "send", "read", "write", "store", "load", "save",
                "delete", "update", "modify", "execute", "run", "start", "stop",
                "pause", "continue", "wait", "sync", "parallel", "concurrent",
                "batch", "real-time", "async", "asynchronous", "synchronous",
            ],
            "entity": [
                "数据", "文件", "消息", "进程", "线程", "任务", "函数", "模块",
                "程序", "代码", "算法", "数据库", "网络", "协议", "接口",
                "data", "file", "message", "process", "thread", "task",
                "function", "module", "program", "code", "algorithm", "database",
                "network", "protocol", "interface", "API",
            ],
            "performance": [
                "速度", "快速", "高效", "延迟", "吞吐量", "性能", "优化",
                "内存", "空间", "能耗", "功耗", "大小", "体积",
                "speed", "fast", "efficient", "latency", "throughput",
                "performance", "optimize", "memory", "space", "energy",
                "power", "size", "small", "minimal", "maximum", "minimum",
            ],
            "platform": [
                "Linux", "Android", "iOS", "Windows", "HarmonyOS", "鸿蒙",
                "嵌入式", "嵌入式系统", "云", "云端", "服务器",
                "linux", "android", "ios", "windows", "embedded", "cloud",
                "server", "web", "mobile", "desktop",
            ],
            "pattern": [
                "并行", "并发", "流水线", "管道", "映射", "规约",
                "流处理", "事件驱动", "批量", "实时", "异步",
                "parallel", "concurrent", "pipeline", "map", "reduce",
                "streaming", "stream", "event-driven", "batch", "real-time",
                "asynchronous",
            ],
        }

        self._compiled_patterns: Dict[str, re.Pattern] = {}
        for category, keywords in self._domain_keywords.items():
            pattern = "|".join(re.escape(k) for k in keywords)
            self._compiled_patterns[category] = re.compile(pattern, re.IGNORECASE)

    def extract(self, text: str) -> Dict[str, List[str]]:
        results = {}

        for category, pattern in self._compiled_patterns.items():
            matches = pattern.findall(text)
            normalized = [self._normalize_keyword(m) for m in matches]
            results[category] = list(dict.fromkeys(normalized))

        all_keywords = []
        for keywords in results.values():
            all_keywords.extend(keywords)
        results["all"] = list(dict.fromkeys(all_keywords))

        return results

    def _normalize_keyword(self, keyword: str) -> str:
        mapping = {
            "创建": "create", "生成": "generate", "计算": "compute",
            "处理": "process", "转换": "transform", "传输": "transfer",
            "接收": "receive", "发送": "send", "读取": "read",
            "写入": "write", "存储": "store", "加载": "load",
            "保存": "save", "删除": "delete", "更新": "update",
            "修改": "modify", "执行": "execute", "运行": "run",
            "启动": "start", "停止": "stop", "暂停": "pause",
            "继续": "continue", "等待": "wait", "同步": "sync",
            "并行": "parallel", "并发": "concurrent", "串行": "sequential",
            "批量": "batch", "实时": "real-time", "异步": "asynchronous",
            "数据": "data", "文件": "file", "消息": "message",
            "进程": "process", "线程": "thread", "任务": "task",
            "函数": "function", "模块": "module", "程序": "program",
            "代码": "code", "算法": "algorithm", "数据库": "database",
            "网络": "network", "协议": "protocol", "接口": "interface",
            "速度": "speed", "快速": "fast", "高效": "efficient",
            "延迟": "latency", "吞吐量": "throughput", "性能": "performance",
            "优化": "optimize", "内存": "memory", "空间": "space",
            "能耗": "energy", "功耗": "power", "大小": "size",
            "嵌入式": "embedded", "嵌入式系统": "embedded",
            "云": "cloud", "云端": "cloud", "服务器": "server",
            "鸿蒙": "HarmonyOS", "流水线": "pipeline", "管道": "pipeline",
            "映射": "map", "规约": "reduce", "流处理": "streaming",
            "事件驱动": "event-driven",
        }
        return mapping.get(keyword.lower(), keyword.lower())


class ComputingPatternDetector:
    def __init__(self):
        self._pattern_indicators: Dict[ComputingPattern, Dict[str, Any]] = {
            ComputingPattern.PARALLEL: {
                "keywords": [
                    "并行", "同时", "多线程", "多进程", "多核", "分布式",
                    "parallel", "concurrent", "simultaneous", "multi-thread",
                    "multi-process", "multi-core", "distributed",
                ],
                "weight": 1.0,
            },
            ComputingPattern.PIPELINE: {
                "keywords": [
                    "流水线", "管道", "阶段", "分阶段", "依次处理",
                    "pipeline", "pipe", "stage", "phased",
                ],
                "weight": 0.9,
            },
            ComputingPattern.MAP_REDUCE: {
                "keywords": [
                    "映射", "规约", "MapReduce", "map", "reduce", "聚合",
                    "aggregate",
                ],
                "weight": 0.9,
            },
            ComputingPattern.STREAMING: {
                "keywords": [
                    "流处理", "流式", "数据流", "连续", "实时流",
                    "streaming", "stream", "dataflow", "continuous",
                ],
                "weight": 0.85,
            },
            ComputingPattern.EVENT_DRIVEN: {
                "keywords": [
                    "事件驱动", "事件", "回调", "触发器", "响应式",
                    "event-driven", "event", "callback", "trigger", "reactive",
                ],
                "weight": 0.85,
            },
            ComputingPattern.BATCH: {
                "keywords": [
                    "批量", "批处理", "批次", "批量处理",
                    "batch", "batched",
                ],
                "weight": 0.8,
            },
            ComputingPattern.REAL_TIME: {
                "keywords": [
                    "实时", "低延迟", "实时处理", "硬实时", "软实时",
                    "real-time", "realtime", "low latency",
                ],
                "weight": 0.9,
            },
            ComputingPattern.SEQUENTIAL: {
                "keywords": [
                    "串行", "顺序", "依次", "同步执行",
                    "sequential", "serial", "synchronous", "in order",
                ],
                "weight": 0.7,
            },
        }

    def detect(self, text: str) -> List[Tuple[ComputingPattern, float]]:
        scores: Dict[ComputingPattern, float] = {}

        for pattern, indicators in self._pattern_indicators.items():
            score = 0.0
            keywords = indicators["keywords"]
            weight = indicators["weight"]

            for keyword in keywords:
                if re.search(re.escape(keyword), text, re.IGNORECASE):
                    score += 1.0

            if score > 0:
                normalized_score = min(1.0, score / max(1, len(keywords) * 0.3))
                scores[pattern] = normalized_score * weight

        sorted_patterns = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return sorted_patterns

    def get_primary_pattern(self, text: str) -> Optional[ComputingPattern]:
        patterns = self.detect(text)
        if patterns and patterns[0][1] > 0.3:
            return patterns[0][0]
        return None


class PerformanceGoalExtractor:
    def __init__(self):
        self._goal_indicators: Dict[PerformanceGoal, Dict[str, Any]] = {
            PerformanceGoal.MIN_LATENCY: {
                "keywords": [
                    "延迟", "响应时间", "快", "快速", "实时", "低延迟",
                    "latency", "response time", "fast", "quick", "real-time",
                    "low latency", "speed",
                ],
                "fitness_key": "min_latency",
            },
            PerformanceGoal.MAX_THROUGHPUT: {
                "keywords": [
                    "吞吐量", "并发量", "高并发", "高效", "处理能力",
                    "throughput", "concurrency", "highly concurrent",
                    "processing power", "efficient", "performance",
                ],
                "fitness_key": "max_throughput",
            },
            PerformanceGoal.MIN_ENERGY: {
                "keywords": [
                    "能耗", "功耗", "节能", "低功耗", "电池", "省电",
                    "energy", "power", "low power", "save power",
                    "battery", "power-efficient",
                ],
                "fitness_key": "min_energy",
            },
            PerformanceGoal.MIN_SIZE: {
                "keywords": [
                    "大小", "体积", "代码大小", "内存占用", "紧凑", "精简",
                    "size", "code size", "memory footprint", "compact",
                    "small", "minimal", "lightweight",
                ],
                "fitness_key": "min_size",
            },
            PerformanceGoal.HIGH_AVAILABILITY: {
                "keywords": [
                    "可用性", "可靠", "容错", "高可用", "鲁棒",
                    "availability", "reliable", "fault-tolerant",
                    "high availability", "robust",
                ],
                "fitness_key": None,
            },
            PerformanceGoal.SCALABILITY: {
                "keywords": [
                    "可扩展", "伸缩", "横向扩展", "纵向扩展",
                    "scalable", "scalability", "scale-out", "scale-up",
                    "elastic",
                ],
                "fitness_key": None,
            },
        }

        self._value_patterns = [
            re.compile(r"(\d+(?:\.\d+)?)\s*(ms|毫秒|秒|s|minute|分钟|hour|小时)"),
            re.compile(r"(小于|小于等于|不超过|最多|小于\s*等于)\s*(\d+(?:\.\d+)?)\s*(ms|毫秒|秒|s|minute|分钟)"),
            re.compile(r"(大于|大于等于|至少|超过|多于)\s*(\d+(?:\.\d+)?)\s*(个|条|MB|KB|GB|次/秒|每秒)"),
        ]

    def extract(self, text: str) -> List[Tuple[PerformanceGoal, float, Dict[str, Any]]]:
        results = []

        for goal, indicators in self._goal_indicators.items():
            score = 0.0
            keywords = indicators["keywords"]

            for keyword in keywords:
                if re.search(re.escape(keyword), text, re.IGNORECASE):
                    score += 1.0

            if score > 0:
                normalized_score = min(1.0, score / max(1, len(keywords) * 0.3))

                metadata = {
                    "fitness_key": indicators["fitness_key"],
                    "matched_keywords": [
                        k for k in keywords
                        if re.search(re.escape(k), text, re.IGNORECASE)
                    ],
                }

                value_info = self._extract_value(text, goal)
                if value_info:
                    metadata["value_info"] = value_info

                results.append((goal, normalized_score, metadata))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def _extract_value(self, text: str, goal: PerformanceGoal) -> Optional[Dict[str, Any]]:
        for pattern in self._value_patterns:
            match = pattern.search(text)
            if match:
                groups = match.groups()
                if len(groups) >= 3:
                    try:
                        value = float(groups[-2])
                        unit = groups[-1]
                        relation = groups[0] if len(groups) > 2 else None
                        return {
                            "value": value,
                            "unit": unit,
                            "relation": relation,
                        }
                    except (ValueError, IndexError):
                        pass
        return None

    def build_fitness_expression(
        self,
        goals: List[Tuple[PerformanceGoal, float, Dict[str, Any]]],
        weights: Optional[Dict[PerformanceGoal, float]] = None,
    ) -> str:
        weights = weights or {}
        parts = []

        default_weights = {
            PerformanceGoal.MIN_LATENCY: 1.0,
            PerformanceGoal.MAX_THROUGHPUT: 2.0,
            PerformanceGoal.MIN_ENERGY: 0.5,
            PerformanceGoal.MIN_SIZE: 1.0,
        }

        for goal, score, metadata in goals:
            fitness_key = metadata.get("fitness_key")
            if fitness_key:
                weight = weights.get(goal, default_weights.get(goal, 1.0))

                if goal in [PerformanceGoal.MIN_LATENCY, PerformanceGoal.MIN_ENERGY, PerformanceGoal.MIN_SIZE]:
                    parts.append(f"{fitness_key}")
                else:
                    parts.append(f"{weight}*{fitness_key}")

        if parts:
            return " + ".join(parts)
        return "min_latency + max_throughput"


class PlatformDetector:
    def __init__(self):
        self._platform_aliases: Dict[str, List[str]] = {
            "linux-6.x": [
                "linux", "Linux", "Linux 6", "linux-6", "内核6", "kernel 6",
                "ubuntu", "Ubuntu", "debian", "Debian", "centos", "CentOS",
                "redhat", "RedHat", "fedora", "Fedora",
            ],
            "android-14": [
                "android", "Android", "安卓", "Android 14", "android-14",
                "Android 13", "android-13", "Android 15", "android-15",
            ],
            "ios-18": [
                "ios", "iOS", "IOS", "iPhone", "iPad", "苹果手机", "苹果平板",
                "iOS 17", "ios-17", "iOS 18", "ios-18", "iOS 19", "ios-19",
            ],
            "win-11": [
                "windows", "Windows", "视窗", "win", "Win",
                "Windows 10", "win-10", "Windows 11", "win-11",
                "Windows Server", "windows server",
            ],
            "harmony-5": [
                "harmony", "Harmony", "鸿蒙", "鸿蒙OS", "HarmonyOS",
                "OpenHarmony", "openharmony", "HarmonyOS 5", "harmony-5",
            ],
            "wasm-wasi": [
                "wasm", "WASM", "WebAssembly", "webassembly",
                "wasi", "WASI", "WebAssembly System Interface",
                "浏览器", "browser", "Browser", "web", "Web",
            ],
            "embedded": [
                "embedded", "Embedded", "嵌入式", "嵌入式系统",
                "MCU", "微控制器", "单片机", "Arduino", "arduino",
                "STM32", "stm32", "ESP32", "esp32", "RISC-V", "riscv",
                "ARM Cortex", "arm cortex", "裸机", "bare metal",
            ],
        }

        self._default_platform = "linux-6.x"

    def detect(self, text: str) -> List[Tuple[str, float]]:
        scores: Dict[str, float] = {}

        for platform, aliases in self._platform_aliases.items():
            score = 0.0

            for alias in aliases:
                matches = re.findall(re.escape(alias), text, re.IGNORECASE)
                score += len(matches) * (1.0 / len(aliases))

            if score > 0:
                scores[platform] = min(1.0, score)

        sorted_platforms = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return sorted_platforms

    def get_default_platform(self) -> str:
        return self._default_platform

    def is_embedded_platform(self, platform: str) -> bool:
        return platform in ["embedded"] or "embedded" in platform.lower()

    def is_mobile_platform(self, platform: str) -> bool:
        return any(p in platform for p in ["android", "ios", "harmony"])


class AmbiguityDetector:
    def __init__(self):
        self._ambiguity_patterns: List[Dict[str, Any]] = [
            {
                "pattern": r"(快|快速|高效|好|好的|合适|适当|合理|足够)",
                "category": "vague_adjective",
                "level": AmbiguityLevel.MEDIUM,
                "suggestion": "请明确具体的性能指标或数值要求",
            },
            {
                "pattern": r"(一些|几个|许多|大量|部分|一定|适当的)",
                "category": "vague_quantity",
                "level": AmbiguityLevel.HIGH,
                "suggestion": "请明确具体的数量或范围",
            },
            {
                "pattern": r"(可能|也许|大概|大约|差不多|左右)",
                "category": "uncertainty",
                "level": AmbiguityLevel.MEDIUM,
                "suggestion": "请确认具体的数值或条件",
            },
            {
                "pattern": r"(等等|等|之类|诸如此类)",
                "category": "incomplete_list",
                "level": AmbiguityLevel.HIGH,
                "suggestion": "请明确完整的列表或范围",
            },
            {
                "pattern": r"(或|或者|还是|和/或)",
                "category": "alternative",
                "level": AmbiguityLevel.MEDIUM,
                "suggestion": "请明确选择哪个选项",
            },
            {
                "pattern": r"(当|如果|一旦|假如|假设)",
                "category": "conditional",
                "level": AmbiguityLevel.LOW,
                "suggestion": "请明确条件触发的具体场景",
            },
        ]

        self._compiled_patterns = [
            {
                **p,
                "compiled": re.compile(p["pattern"], re.IGNORECASE),
            }
            for p in self._ambiguity_patterns
        ]

    def detect(self, text: str) -> List[Ambiguity]:
        ambiguities = []
        seen_matches: Set[Tuple[str, int]] = set()

        for i, pattern_info in enumerate(self._compiled_patterns):
            matches = pattern_info["compiled"].finditer(text)

            for match in matches:
                matched_text = match.group(0)
                start_pos = match.start()

                key = (matched_text, start_pos)
                if key in seen_matches:
                    continue
                seen_matches.add(key)

                context_start = max(0, start_pos - 20)
                context_end = min(len(text), match.end() + 20)
                context = text[context_start:context_end]

                ambiguities.append(
                    Ambiguity(
                        id=f"amb_{len(ambiguities):03d}",
                        text=matched_text,
                        level=pattern_info["level"],
                        category=pattern_info["category"],
                        suggestion=pattern_info["suggestion"],
                        context=context,
                    )
                )

        if ambiguities:
            ambiguities.sort(key=lambda a: self._level_priority(a.level), reverse=True)

        return ambiguities

    def _level_priority(self, level: AmbiguityLevel) -> int:
        priority = {
            AmbiguityLevel.CRITICAL: 5,
            AmbiguityLevel.HIGH: 4,
            AmbiguityLevel.MEDIUM: 3,
            AmbiguityLevel.LOW: 2,
            AmbiguityLevel.NONE: 1,
        }
        return priority.get(level, 0)

    def get_overall_ambiguity_level(self, ambiguities: List[Ambiguity]) -> AmbiguityLevel:
        if not ambiguities:
            return AmbiguityLevel.NONE

        max_level = AmbiguityLevel.NONE
        for amb in ambiguities:
            if self._level_priority(amb.level) > self._level_priority(max_level):
                max_level = amb.level

        return max_level


class RequirementAnalyzer:
    def __init__(self):
        self._keyword_extractor = KeywordExtractor()
        self._pattern_detector = ComputingPatternDetector()
        self._goal_extractor = PerformanceGoalExtractor()
        self._platform_detector = PlatformDetector()
        self._ambiguity_detector = AmbiguityDetector()
        self._counter = 0

    def analyze(self, text: str) -> RequirementAnalysis:
        self._counter += 1

        keywords = self._keyword_extractor.extract(text)

        patterns = self._pattern_detector.detect(text)
        detected_patterns = [p[0] for p in patterns if p[1] > 0.3]

        goals = self._goal_extractor.extract(text)
        performance_goals = [g[0] for g in goals]

        platforms = self._platform_detector.detect(text)
        target_platforms = [p[0] for p in platforms if p[1] > 0.3]
        if not target_platforms:
            target_platforms = [self._platform_detector.get_default_platform()]

        ambiguities = self._ambiguity_detector.detect(text)

        functional_reqs = self._extract_functional_requirements(text)
        non_functional_reqs = self._extract_non_functional_requirements(text, goals)

        entities = keywords.get("entity", [])
        actions = keywords.get("action", [])

        return RequirementAnalysis(
            original_text=text,
            functional_requirements=functional_reqs,
            non_functional_requirements=non_functional_reqs,
            computing_patterns=detected_patterns,
            target_platforms=target_platforms,
            performance_goals=performance_goals,
            ambiguities=ambiguities,
            keywords=keywords.get("all", []),
            entities=entities,
            actions=actions,
        )

    def _extract_functional_requirements(self, text: str) -> List[FunctionalRequirement]:
        requirements = []

        sentences = re.split(r'[。；！？.!?;]+', text)

        action_verbs = [
            "创建", "生成", "计算", "处理", "转换", "传输", "接收", "发送",
            "读取", "写入", "存储", "加载", "保存", "删除", "更新", "修改",
            "执行", "运行", "启动", "停止", "暂停", "继续", "等待", "同步",
            "实现", "开发", "编写", "设计",
            "create", "generate", "compute", "process", "transform",
            "transfer", "receive", "send", "read", "write", "store",
            "load", "save", "delete", "update", "modify", "execute",
            "run", "implement", "develop", "design",
        ]

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            for verb in action_verbs:
                if re.search(re.escape(verb), sentence, re.IGNORECASE):
                    req = FunctionalRequirement(
                        id=f"FR_{self._counter:04d}_{len(requirements):02d}",
                        description=sentence,
                        action=verb,
                        source_text=sentence,
                        confidence=0.7,
                    )

                    object_match = re.search(
                        rf"{re.escape(verb)}[\s，,]*([\u4e00-\u9fa5a-zA-Z0-9_]+)",
                        sentence,
                        re.IGNORECASE,
                    )
                    if object_match:
                        req.object = object_match.group(1)

                    conditions = re.findall(
                        r"(当|如果|一旦|在.*下|在.*时|当.*时)[，,]*([^。；！？]+)",
                        sentence,
                    )
                    if conditions:
                        req.conditions = ["".join(c) for c in conditions]

                    requirements.append(req)
                    break

        return requirements

    def _extract_non_functional_requirements(
        self,
        text: str,
        goals: List[Tuple[PerformanceGoal, float, Dict[str, Any]]],
    ) -> List[NonFunctionalRequirement]:
        requirements = []

        for goal, score, metadata in goals:
            if score < 0.3:
                continue

            value_info = metadata.get("value_info")

            category_map = {
                PerformanceGoal.MIN_LATENCY: "性能",
                PerformanceGoal.MAX_THROUGHPUT: "性能",
                PerformanceGoal.MIN_ENERGY: "能耗",
                PerformanceGoal.MIN_SIZE: "资源",
                PerformanceGoal.HIGH_AVAILABILITY: "可靠性",
                PerformanceGoal.SCALABILITY: "可扩展性",
            }

            req = NonFunctionalRequirement(
                id=f"NFR_{self._counter:04d}_{len(requirements):02d}",
                description=f"目标: {goal.value}",
                category=category_map.get(goal, "其他"),
                related_goals=[goal],
                source_text=text,
                confidence=score,
            )

            if value_info:
                req.target_value = value_info.get("value")
                req.unit = value_info.get("unit", "")
                req.target_operation = value_info.get("relation", "min")

            requirements.append(req)

        return requirements

    def generate_summary(self, analysis: RequirementAnalysis) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("📋 需求分析报告")
        lines.append("=" * 60)

        if analysis.functional_requirements:
            lines.append("\n【功能需求】")
            for i, req in enumerate(analysis.functional_requirements, 1):
                lines.append(f"  {i}. {req.description[:60]}...")
                if req.conditions:
                    lines.append(f"     条件: {', '.join(req.conditions)}")

        if analysis.non_functional_requirements:
            lines.append("\n【非功能需求】")
            for req in analysis.non_functional_requirements:
                value_str = ""
                if req.target_value:
                    value_str = f" (目标: {req.target_value} {req.unit})"
                lines.append(f"  - {req.category}: {req.description}{value_str}")

        if analysis.computing_patterns:
            lines.append("\n【计算模式】")
            for pattern in analysis.computing_patterns:
                lines.append(f"  - {pattern.value}")

        if analysis.target_platforms:
            lines.append("\n【目标平台】")
            for platform in analysis.target_platforms:
                lines.append(f"  - {platform}")

        if analysis.performance_goals:
            lines.append("\n【性能目标】")
            for goal in analysis.performance_goals:
                lines.append(f"  - {goal.value}")

        if analysis.ambiguities:
            lines.append("\n【⚠️ 模糊点检测】")
            for amb in analysis.ambiguities[:5]:
                lines.append(f"  [{amb.level.value.upper()}] {amb.text}: {amb.suggestion}")
            if len(analysis.ambiguities) > 5:
                lines.append(f"  ... 还有 {len(analysis.ambiguities) - 5} 个模糊点")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def build_evo_template(self, analysis: RequirementAnalysis) -> str:
        fitness_expr = self._goal_extractor.build_fitness_expression(
            [(g, 1.0, {}) for g in analysis.performance_goals]
            if analysis.performance_goals
            else [
                (PerformanceGoal.MIN_LATENCY, 1.0, {"fitness_key": "min_latency"}),
                (PerformanceGoal.MAX_THROUGHPUT, 1.0, {"fitness_key": "max_throughput"}),
            ]
        )

        platforms_str = ", ".join(f'"{p}"' for p in analysis.target_platforms)

        pattern_comment = ""
        if analysis.computing_patterns:
            pattern_names = [p.value for p in analysis.computing_patterns]
            pattern_comment = f"// 计算模式: {', '.join(pattern_names)}"

        xiangci_content = analysis.original_text.replace("\n", " ")
        if len(xiangci_content) > 200:
            xiangci_content = xiangci_content[:200] + "..."

        template = f'''@evolang "3.0"

@xiangci {{
    "{xiangci_content}"
}}

@locus main_locus {{
    mut_rate   = 0.02
    cross_pool = "default"
    fitness    = {fitness_expr}
    env_target = [{platforms_str}]
    max_generations = 50

    {pattern_comment}
    卦序: {{
        // TODO: 根据需求实现具体的卦象指令序列
        ䷀ CREA R0, R1
        ䷌ FELLOWSHIP R0, R1
        ䷾ SYNC
    }}
}}
'''
        return template
