import json
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field


@dataclass
class XiangciTranslation:
    original_text: str
    locus_name: str
    generated_genes: List[Dict] = field(default_factory=list)
    fitness_expression: str = ""
    env_targets: List[str] = field(default_factory=list)
    confidence: float = 0.0
    model_used: str = "local"
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelCapability:
    model_name: str
    translation_quality: float = 0.5
    reasoning_depth: float = 0.5
    code_generation_score: float = 0.5
    context_window: int = 4096
    supported_languages: List[str] = field(default_factory=lambda: ["zh", "en"])


SYSTEM_PROMPT = """你是易衍·Evomorph 编程语言的象辞编译器。
你的任务是将用户的自然语言意图（象辞）翻译为易衍基因座（Locus）。

易衍语言核心概念：
1. 六十四卦指令集：每条指令对应一个卦象，用于原子操作
2. 基因座（Locus）：包含指令序列和进化元数据的代码单元
3. 象辞：自然语言描述的程序意图

常用指令映射：
- 创建/启动 → CREA (䷀) - 创建执行单元
- 接收/输入 → RECV (䷁) - 接收数据
- 分配内存 → ALLOC (䷂) - 内存分配
- 同步/通信 → FELLOWSHIP (䷌) - 进程间通信
- 写回数据 → ABUNDANCE (䷍) - 数据写回
- 屏障同步 → SYNC (䷾) - 同步屏障
- 异步占位 → FUTU (䷿) - 未来值
- 变异操作 → MUT (䷑) - 指令变异
- 交叉重组 → MATE (䷫) - 基因交叉
- 入栈操作 → PUSH_UP (䷭) - 栈操作
- 出栈操作 → WELL (䷯) - 取栈值
- 暂停/阻塞 → HALT (䷋) - 暂停
- 返回/跳转 → RETURN (䷗) - 返回

输出格式要求：
返回JSON格式，包含：
- locus_name: 基因座名称
- instructions: 指令列表，每条包含 opcode(数字), mnemonic, operands
- fitness_expr: 适应度表达式
- env_targets: 目标平台列表
"""


# =============================================================================
# 象辞模板库 — 24个预定义编程模式
# =============================================================================
# .evo 等价文件: xiangci_templates.evo (完整的 24 个模板基因座)
# AI 模型可阅读该 .evo 文件选择模板，本 Python dict 用于 SDK 的模板匹配引擎。
# =============================================================================
XIANCI_TEMPLATES = {
    # 并发原语
    "parallel": {
        "pattern": r"(并行|并发|分治|多线程|多核|parallel|concurrent)",
        "template_instructions": [
            {"opcode": 63, "mnemonic": "CREA"}, {"opcode": 61, "mnemonic": "FELLOWSHIP"},
            {"opcode": 21, "mnemonic": "SYNC"}, {"opcode": 0, "mnemonic": "RECV"},
        ],
        "fitness_hint": "min_latency + max_throughput",
    },
    "mutex_guard": {
        "pattern": r"(互斥|锁|临界区|guard|mutex|lock)",
        "template_instructions": [
            {"opcode": 58, "mnemonic": "LOCK"}, {"opcode": 17, "mnemonic": "ALLOC"},
            {"opcode": 10, "mnemonic": "UNLOCK"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "min_latency",
    },
    "atomic_op": {
        "pattern": r"(原子|atomic|不可中断|CAS|compare.and.swap)",
        "template_instructions": [
            {"opcode": 57, "mnemonic": "INTRINSIC"}, {"opcode": 58, "mnemonic": "LOCK"},
            {"opcode": 59, "mnemonic": "STEP"}, {"opcode": 10, "mnemonic": "UNLOCK"},
            {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "min_latency + correctness",
    },
    "barrier_sync": {
        "pattern": r"(屏障|同步点|barrier|rendezvous|集结)",
        "template_instructions": [
            {"opcode": 61, "mnemonic": "FELLOWSHIP"}, {"opcode": 21, "mnemonic": "SYNC"},
            {"opcode": 39, "mnemonic": "BARRIER"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "min_latency",
    },
    "fork_join": {
        "pattern": r"(fork|join|分叉|汇合|spawn|派生)",
        "template_instructions": [
            {"opcode": 63, "mnemonic": "CREA"}, {"opcode": 63, "mnemonic": "CREA"},
            {"opcode": 61, "mnemonic": "FELLOWSHIP"}, {"opcode": 24, "mnemonic": "GATHER"},
            {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "max_throughput + min_latency",
    },
    # 数据处理
    "map_reduce": {
        "pattern": r"(map|reduce|映射|归约|分布式|mapreduce)",
        "template_instructions": [
            {"opcode": 63, "mnemonic": "CREA"}, {"opcode": 24, "mnemonic": "GATHER"},
            {"opcode": 35, "mnemonic": "REDUCE"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "max_throughput + min_latency",
    },
    "pipeline": {
        "pattern": r"(流水线|管道|pipeline|链式|stage|阶段)",
        "template_instructions": [
            {"opcode": 0, "mnemonic": "RECV"}, {"opcode": 40, "mnemonic": "ADVANCE"},
            {"opcode": 47, "mnemonic": "ABUNDANCE"}, {"opcode": 59, "mnemonic": "STEP"},
            {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "max_throughput",
    },
    "batch_process": {
        "pattern": r"(批量|batch|chunk|块|批处理)",
        "template_instructions": [
            {"opcode": 13, "mnemonic": "ABOUND"}, {"opcode": 59, "mnemonic": "STEP"},
            {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "max_throughput + min_energy",
    },
    "data_transform": {
        "pattern": r"(转换|transform|格式化|编码|序列化|encode|decode)",
        "template_instructions": [
            {"opcode": 0, "mnemonic": "RECV"}, {"opcode": 37, "mnemonic": "ADORN"},
            {"opcode": 47, "mnemonic": "ABUNDANCE"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "min_latency",
    },
    "stream_filter": {
        "pattern": r"(流|stream|过滤|filter|筛选|条件)",
        "template_instructions": [
            {"opcode": 54, "mnemonic": "PENETRATE"}, {"opcode": 2, "mnemonic": "BRANCH"},
            {"opcode": 47, "mnemonic": "ABUNDANCE"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "max_throughput",
    },
    # IO操作
    "io_bound": {
        "pattern": r"(输入|输出|读写|IO|文件|网络)",
        "template_instructions": [
            {"opcode": 0, "mnemonic": "RECV"}, {"opcode": 17, "mnemonic": "ALLOC"},
            {"opcode": 47, "mnemonic": "ABUNDANCE"},
        ],
        "fitness_hint": "min_energy + min_latency",
    },
    "cache_access": {
        "pattern": r"(缓存|cache|预取|prefetch|热数据)",
        "template_instructions": [
            {"opcode": 55, "mnemonic": "PREFETCH"}, {"opcode": 3, "mnemonic": "APPROACH"},
            {"opcode": 47, "mnemonic": "ABUNDANCE"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "min_latency",
    },
    "log_writer": {
        "pattern": r"(日志|log|记录|追踪|trace|debug|调试)",
        "template_instructions": [
            {"opcode": 45, "mnemonic": "ILLUMINATE"}, {"opcode": 14, "mnemonic": "PERSIST"},
            {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "min_latency",
    },
    "disperse_write": {
        "pattern": r"(分散写|scatter|分布|disperse|多路)",
        "template_instructions": [
            {"opcode": 50, "mnemonic": "DISPERSE"}, {"opcode": 7, "mnemonic": "FLUSH"},
            {"opcode": 21, "mnemonic": "SYNC"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "max_throughput",
    },
    # 计算
    "compute": {
        "pattern": r"(计算|运算|处理|算法|数学|compute|math)",
        "template_instructions": [
            {"opcode": 63, "mnemonic": "CREA"}, {"opcode": 59, "mnemonic": "STEP"},
            {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "max_throughput",
    },
    # 容错恢复
    "retry_loop": {
        "pattern": r"(重试|retry|重来|重新|再次尝试)",
        "template_instructions": [
            {"opcode": 20, "mnemonic": "LAME"}, {"opcode": 2, "mnemonic": "BRANCH"},
            {"opcode": 59, "mnemonic": "STEP"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "min_latency",
    },
    "degrade_fallback": {
        "pattern": r"(降级|回退|fallback|degrade|备选|兜底)",
        "template_instructions": [
            {"opcode": 2, "mnemonic": "BRANCH"}, {"opcode": 2, "mnemonic": "BRANCH"},
            {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "correctness",
    },
    "trap_handler": {
        "pattern": r"(异常|错误|exception|error|trap|catch|捕获)",
        "template_instructions": [
            {"opcode": 18, "mnemonic": "TRAP"}, {"opcode": 45, "mnemonic": "ILLUMINATE"},
            {"opcode": 60, "mnemonic": "RETREAT"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "correctness + min_latency",
    },
    # 安全
    "crypto_ops": {
        "pattern": r"(加密|解密|密码|crypto|签名|哈希|hash|安全)",
        "template_instructions": [
            {"opcode": 5, "mnemonic": "OBSCURE"}, {"opcode": 53, "mnemonic": "BIND"},
            {"opcode": 51, "mnemonic": "TRUST"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "correctness",
    },
    "throttle_limit": {
        "pattern": r"(限流|节流|throttle|rate.limit|频率|qps)",
        "template_instructions": [
            {"opcode": 19, "mnemonic": "THROTTLE"}, {"opcode": 23, "mnemonic": "WAIT"},
            {"opcode": 59, "mnemonic": "STEP"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "correctness + min_latency",
    },
    "trust_verify": {
        "pattern": r"(验证|校验|verify|签名|认证|信任)",
        "template_instructions": [
            {"opcode": 51, "mnemonic": "TRUST"}, {"opcode": 41, "mnemonic": "BITE"},
            {"opcode": 2, "mnemonic": "BRANCH"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "correctness",
    },
    # 内存管理
    "mem_pool": {
        "pattern": r"(内存池|内存|pool|alloc|分配|管理|mem)",
        "template_instructions": [
            {"opcode": 17, "mnemonic": "ALLOC"}, {"opcode": 33, "mnemonic": "NOURISH"},
            {"opcode": 47, "mnemonic": "ABUNDANCE"}, {"opcode": 4, "mnemonic": "YIELD"},
            {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "min_latency + min_energy",
    },
    "context_switch": {
        "pattern": r"(上下文|切换|context|switch|调度|schedule)",
        "template_instructions": [
            {"opcode": 44, "mnemonic": "TRAVEL"}, {"opcode": 6, "mnemonic": "PUSH_UP"},
            {"opcode": 14, "mnemonic": "PERSIST"}, {"opcode": 4, "mnemonic": "YIELD"},
            {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "min_latency",
    },
    # 生命周期
    "event_loop": {
        "pattern": r"(事件循环|消息循环|event.loop|消息泵|主循环)",
        "template_instructions": [
            {"opcode": 28, "mnemonic": "SENSE"}, {"opcode": 0, "mnemonic": "RECV"},
            {"opcode": 2, "mnemonic": "BRANCH"}, {"opcode": 59, "mnemonic": "STEP"},
            {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "max_throughput",
    },
    "hot_reload": {
        "pattern": r"(热更新|热加载|hot.reload|热替换|在线更新)",
        "template_instructions": [
            {"opcode": 29, "mnemonic": "REPLACE"}, {"opcode": 46, "mnemonic": "CAST"},
            {"opcode": 15, "mnemonic": "THRUST"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "min_latency + correctness",
    },
    "signal_handler": {
        "pattern": r"(信号|中断|signal|interrupt|事件|event)",
        "template_instructions": [
            {"opcode": 28, "mnemonic": "SENSE"}, {"opcode": 9, "mnemonic": "SHOCK"},
            {"opcode": 2, "mnemonic": "BRANCH"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "min_latency",
    },
    "type_convert": {
        "pattern": r"(类型转换|cast|类型|转换|convert|coerce)",
        "template_instructions": [
            {"opcode": 43, "mnemonic": "CONVERT"}, {"opcode": 41, "mnemonic": "BITE"},
            {"opcode": 47, "mnemonic": "ABUNDANCE"}, {"opcode": 1, "mnemonic": "RETURN"},
        ],
        "fitness_hint": "correctness",
    },
}


class XiangciSDK:
    def __init__(self):
        self.translations_history: List[XiangciTranslation] = []
        self.model_capabilities: Dict[str, ModelCapability] = {}
        self.custom_handlers: Dict[str, Callable] = {}
        self.memory_bank: List[Dict] = []
        self._register_default_models()

    def _register_default_models(self):
        default_models = [
            ModelCapability("gpt-4", 0.95, 0.9, 0.9, 128000),
            ModelCapability("claude-3-opus", 0.93, 0.92, 0.88, 200000),
            ModelCapability("gemini-pro", 0.85, 0.8, 0.82, 32000),
            ModelCapability("local-evomorph", 0.7, 0.6, 0.65, 8000),
        ]
        for m in default_models:
            self.model_capabilities[m.model_name] = m

    def register_model(self, capability: ModelCapability):
        self.model_capabilities[capability.model_name] = capability

    def register_handler(self, pattern: str, handler: Callable):
        self.custom_handlers[pattern] = handler

    def translate(self, xiangci_text: str,
                  model_name: Optional[str] = None,
                  env_targets: Optional[List[str]] = None) -> XiangciTranslation:
        start_time = time.time()
        if not model_name:
            model_name = self._select_best_model()
        translation = XiangciTranslation(
            original_text=xiangci_text,
            locus_name=self._generate_locus_name(xiangci_text),
            env_targets=env_targets or ["linux-6.x"],
            model_used=model_name,
            timestamp=start_time,
        )
        matched_template = self._match_template(xiangci_text)
        if matched_template:
            template_data = XIANCI_TEMPLATES[matched_template]
            translation.generated_genes = list(template_data["template_instructions"])
            translation.fitness_expression = template_data["fitness_hint"]
            translation.confidence = 0.75
        elif any(pattern in xiangci_text.lower() for pattern in self.custom_handlers):
            for pattern, handler in self.custom_handlers.items():
                if pattern in xiangci_text.lower():
                    result = handler(xiangci_text)
                    if isinstance(result, dict):
                        translation.generated_genes = result.get("instructions", [])
                        translation.fitness_expression = result.get("fitness", "")
                        translation.confidence = result.get("confidence", 0.6)
                    break
        else:
            translation.generated_genes = self._default_translation(xiangci_text)
            translation.confidence = 0.5
        translation.metadata["processing_time"] = time.time() - start_time
        self.translations_history.append(translation)
        self.memory_bank.append({
            "text": xiangci_text,
            "locus": translation.locus_name,
            "genes_count": len(translation.generated_genes),
            "timestamp": start_time,
        })
        return translation

    def _select_best_model(self) -> str:
        best_model = "local-evomorph"
        best_quality = 0
        for name, cap in self.model_capabilities.items():
            quality = cap.translation_quality * 0.4 + cap.reasoning_depth * 0.3 + cap.code_generation_score * 0.3
            if quality > best_quality:
                best_quality = quality
                best_model = name
        return best_model

    def _generate_locus_name(self, text: str) -> str:
        import hashlib
        hash_val = hashlib.md5(text.encode()).hexdigest()[:6]
        return f"xiangci_{hash_val}"

    def _match_template(self, text: str) -> Optional[str]:
        import re
        for name, tmpl in XIANCI_TEMPLATES.items():
            if re.search(tmpl["pattern"], text, re.IGNORECASE):
                return name
        return None

    def _default_translation(self, text: str) -> List[Dict]:
        text_lower = text.lower()
        genes = []
        if any(kw in text_lower for kw in ("创建", "诞生", "生成", "create")):
            genes.append({"opcode": 63, "mnemonic": "CREA"})
        if any(kw in text_lower for kw in ("接收", "读取", "输入", "recv", "input")):
            genes.append({"opcode": 0, "mnemonic": "RECV"})
        if any(kw in text_lower for kw in ("分配", "内存", "alloc")):
            genes.append({"opcode": 17, "mnemonic": "ALLOC"})
        if any(kw in text_lower for kw in ("通信", "同步", "并行", "sync")):
            genes.append({"opcode": 61, "mnemonic": "FELLOWSHIP"})
        if any(kw in text_lower for kw in ("写入", "输出", "填充", "write")):
            genes.append({"opcode": 47, "mnemonic": "ABUNDANCE"})
        if any(kw in text_lower for kw in ("同步", "屏障", "等待", "barrier")):
            genes.append({"opcode": 21, "mnemonic": "SYNC"})
        if any(kw in text_lower for kw in ("异步", "未来", "future")):
            genes.append({"opcode": 42, "mnemonic": "FUTU"})
        if not genes:
            genes = [
                {"opcode": 0, "mnemonic": "RECV"},
                {"opcode": 59, "mnemonic": "STEP"},
                {"opcode": 1, "mnemonic": "RETURN"},
            ]
        return genes

    def get_prompt_for_llm(self, xiangci_text: str) -> str:
        return f"""{SYSTEM_PROMPT}

用户象辞：
「{xiangci_text}」

请将上述象辞翻译为易衍基因座。"""

    def get_memory_context(self, limit: int = 10) -> List[Dict]:
        return self.memory_bank[-limit:]

    def get_translation_stats(self) -> Dict:
        total = len(self.translations_history)
        avg_confidence = sum(t.confidence for t in self.translations_history) / max(total, 1)
        model_usage = {}
        for t in self.translations_history:
            model_usage[t.model_used] = model_usage.get(t.model_used, 0) + 1
        return {
            "total_translations": total,
            "avg_confidence": avg_confidence,
            "model_usage": model_usage,
            "memory_bank_size": len(self.memory_bank),
        }

    def export_to_evo_source(self, translation: XiangciTranslation) -> str:
        lines = ['@evolang "3.0"', ""]
        lines.append(f'@locus {translation.locus_name} {{')
        lines.append(f"    mut_rate   = 0.03")
        lines.append(f"    cross_pool = \"default\"")
        if translation.fitness_expression:
            lines.append(f"    fitness    = \"{translation.fitness_expression}\"")
        if translation.env_targets:
            targets_str = ", ".join(f'"{t}"' for t in translation.env_targets)
            lines.append(f"    env_target = [{targets_str}]")
        lines.append("")
        lines.append("    卦序: {")
        for gene in translation.generated_genes:
            mnemonic = gene.get("mnemonic", "HALT")
            lines.append(f"        {mnemonic}")
        lines.append("    }")
        lines.append("}")
        return "\n".join(lines)

    def update_model_capability(self, model_name: str, **kwargs):
        if model_name in self.model_capabilities:
            cap = self.model_capabilities[model_name]
            for key, value in kwargs.items():
                if hasattr(cap, key):
                    setattr(cap, key, value)
