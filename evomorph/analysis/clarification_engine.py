"""
多轮澄清机制模块
- 模糊需求识别
- 澄清问题生成
- 多轮对话管理
- 澄清后信息整合
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
    Callable,
    Union,
)

try:
    import sys
    from pathlib import Path
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))

    from evomorph.analysis.requirement_analyzer import (
        RequirementAnalysis,
        Ambiguity,
        AmbiguityLevel,
        RequirementAnalyzer,
        PerformanceGoal,
        ComputingPattern,
        PlatformDetector,
    )

    HAS_REQUIREMENT_ANALYZER = True
except ImportError:
    HAS_REQUIREMENT_ANALYZER = False
    RequirementAnalysis = None
    Ambiguity = None
    AmbiguityLevel = None
    RequirementAnalyzer = None
    PerformanceGoal = None
    ComputingPattern = None
    PlatformDetector = None


class ClarificationType(Enum):
    PERFORMANCE_GOAL = "performance_goal"
    COMPUTING_PATTERN = "computing_pattern"
    TARGET_PLATFORM = "target_platform"
    VAGUE_ADJECTIVE = "vague_adjective"
    VAGUE_QUANTITY = "vague_quantity"
    INCOMPLETE_LIST = "incomplete_list"
    ALTERNATIVE_CHOICE = "alternative_choice"
    CONDITIONAL_CONTEXT = "conditional_context"
    TECHNICAL_DETAIL = "technical_detail"
    BUSINESS_CONTEXT = "business_context"


class ClarificationState(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ClarificationQuestion:
    id: str = ""
    question_text: str = ""
    question_type: ClarificationType = ClarificationType.VAGUE_ADJECTIVE
    ambiguity_level: AmbiguityLevel = AmbiguityLevel.MEDIUM
    options: List[str] = field(default_factory=list)
    default_option_index: int = 0
    is_required: bool = False
    context: str = ""
    related_ambiguity: Optional[Ambiguity] = None
    answer: Optional[str] = None
    answer_confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question_text": self.question_text,
            "question_type": self.question_type.value,
            "ambiguity_level": self.ambiguity_level.value if self.ambiguity_level else None,
            "options": self.options,
            "default_option_index": self.default_option_index,
            "is_required": self.is_required,
            "context": self.context,
            "answer": self.answer,
            "answer_confidence": self.answer_confidence,
        }


@dataclass
class ClarificationSession:
    id: str = ""
    original_requirement: str = ""
    state: ClarificationState = ClarificationState.NOT_STARTED
    questions: List[ClarificationQuestion] = field(default_factory=list)
    current_question_index: int = -1
    answers: Dict[str, str] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    analysis: Optional[RequirementAnalysis] = None
    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "original_requirement": self.original_requirement,
            "state": self.state.value,
            "questions": [q.to_dict() for q in self.questions],
            "current_question_index": self.current_question_index,
            "answers": self.answers,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class QuestionGenerator:
    def __init__(self):
        self._question_templates: Dict[ClarificationType, List[Dict[str, Any]]] = {
            ClarificationType.PERFORMANCE_GOAL: [
                {
                    "template": "您对这个程序的性能有什么具体要求？",
                    "options": [
                        "最小化延迟（快速响应）",
                        "最大化吞吐量（处理更多请求）",
                        "最小化能耗（省电）",
                        "最小化代码体积",
                        "平衡各项指标",
                    ],
                },
                {
                    "template": "这个程序的延迟目标是多少？",
                    "options": [
                        "100毫秒以内",
                        "1秒以内",
                        "5秒以内",
                        "没有严格要求",
                    ],
                },
            ],
            ClarificationType.COMPUTING_PATTERN: [
                {
                    "template": "这个程序的计算模式是什么？",
                    "options": [
                        "并行计算（同时处理多个任务）",
                        "流水线处理（分阶段处理）",
                        "流式处理（连续数据）",
                        "批量处理（一次性处理）",
                        "事件驱动（响应式）",
                        "顺序执行",
                    ],
                },
            ],
            ClarificationType.TARGET_PLATFORM: [
                {
                    "template": "这个程序需要在哪些平台上运行？",
                    "options": [
                        "Linux 服务器",
                        "Android 移动设备",
                        "iOS 设备",
                        "Windows 桌面",
                        "鸿蒙系统",
                        "嵌入式设备",
                        "浏览器（WebAssembly）",
                    ],
                },
            ],
            ClarificationType.VAGUE_ADJECTIVE: [
                {
                    "template": "您说的「{term}」具体指什么？",
                    "options": [
                        "性能优先",
                        "代码简洁",
                        "易于维护",
                        "资源占用少",
                    ],
                },
            ],
            ClarificationType.VAGUE_QUANTITY: [
                {
                    "template": "您说的「{term}」具体数量是多少？",
                    "options": [
                        "几个（2-5个）",
                        "十几个（10-20个）",
                        "几十个（50个以内）",
                        "几百个",
                        "需要确认具体数值",
                    ],
                },
            ],
            ClarificationType.INCOMPLETE_LIST: [
                {
                    "template": "除了已经提到的，还有其他需要包含的项吗？",
                    "options": [
                        "没有其他项了",
                        "还有一些，稍后补充",
                        "请帮我分析可能遗漏的项",
                    ],
                },
            ],
            ClarificationType.ALTERNATIVE_CHOICE: [
                {
                    "template": "在这些选项中，您希望选择哪一个？",
                    "options": [
                        "第一个选项",
                        "第二个选项",
                        "请帮我推荐最合适的",
                        "需要更多信息才能决定",
                    ],
                },
            ],
            ClarificationType.CONDITIONAL_CONTEXT: [
                {
                    "template": "在什么条件下会触发这个逻辑？",
                    "options": [
                        "每次执行都需要",
                        "只有在特定条件下",
                        "根据配置决定",
                        "需要进一步分析",
                    ],
                },
            ],
            ClarificationType.TECHNICAL_DETAIL: [
                {
                    "template": "关于这个技术细节，您有什么偏好？",
                    "options": [
                        "使用现有的标准方案",
                        "追求极致性能",
                        "保持代码简洁",
                        "让我自己决定",
                    ],
                },
            ],
            ClarificationType.BUSINESS_CONTEXT: [
                {
                    "template": "这个功能的业务背景是什么？",
                    "options": [
                        "核心业务功能",
                        "辅助工具",
                        "性能优化",
                        "不需要特别考虑业务背景",
                    ],
                },
            ],
        }

        self._term_mappings: Dict[str, str] = {
            "快": "快速",
            "快速": "快速",
            "高效": "高效",
            "好": "好",
            "好的": "好",
            "合适": "合适",
            "适当": "适当",
            "合理": "合理",
            "足够": "足够",
            "一些": "一些",
            "几个": "几个",
            "许多": "许多",
            "大量": "大量",
            "部分": "部分",
            "一定": "一定",
            "适当的": "适当的",
            "fast": "快速",
            "quick": "快速",
            "efficient": "高效",
            "good": "好",
            "better": "更好",
            "nice": "好",
            "some": "一些",
            "many": "许多",
            "several": "几个",
            "appropriate": "适当",
            "suitable": "合适",
            "reasonable": "合理",
            "enough": "足够",
        }

    def generate(
        self,
        ambiguity_type: ClarificationType,
        context: str = "",
        term: str = "",
    ) -> ClarificationQuestion:
        templates = self._question_templates.get(ambiguity_type, [])
        if not templates:
            templates = self._question_templates[ClarificationType.VAGUE_ADJECTIVE]

        template_info = templates[0]

        question_text = template_info["template"]
        if "{term}" in question_text:
            normalized_term = self._term_mappings.get(term.lower(), term)
            question_text = question_text.replace("{term}", normalized_term)

        return ClarificationQuestion(
            id=f"q_{int(datetime.now().timestamp() * 1000)}_{id(self)}",
            question_text=question_text,
            question_type=ambiguity_type,
            options=template_info.get("options", []),
            default_option_index=0,
            is_required=True,
            context=context,
        )

    def generate_from_ambiguity(self, ambiguity: Ambiguity) -> ClarificationQuestion:
        type_mapping = {
            "vague_adjective": ClarificationType.VAGUE_ADJECTIVE,
            "vague_quantity": ClarificationType.VAGUE_QUANTITY,
            "uncertainty": ClarificationType.VAGUE_ADJECTIVE,
            "incomplete_list": ClarificationType.INCOMPLETE_LIST,
            "alternative": ClarificationType.ALTERNATIVE_CHOICE,
            "conditional": ClarificationType.CONDITIONAL_CONTEXT,
        }

        ambiguity_type = type_mapping.get(
            ambiguity.category,
            ClarificationType.VAGUE_ADJECTIVE,
        )

        question = self.generate(
            ambiguity_type,
            context=ambiguity.context,
            term=ambiguity.text,
        )
        question.ambiguity_level = ambiguity.level
        question.related_ambiguity = ambiguity

        return question

    def generate_performance_question(self) -> ClarificationQuestion:
        return self.generate(ClarificationType.PERFORMANCE_GOAL)

    def generate_platform_question(self) -> ClarificationQuestion:
        return self.generate(ClarificationType.TARGET_PLATFORM)

    def generate_pattern_question(self) -> ClarificationQuestion:
        return self.generate(ClarificationType.COMPUTING_PATTERN)


class ClarificationManager:
    def __init__(self):
        self._question_generator = QuestionGenerator()
        self._active_sessions: Dict[str, ClarificationSession] = {}
        self._requirement_analyzer: Optional[RequirementAnalyzer] = None
        self._platform_detector = PlatformDetector() if PlatformDetector else None

        if HAS_REQUIREMENT_ANALYZER and RequirementAnalyzer:
            self._requirement_analyzer = RequirementAnalyzer()

    def create_session(
        self,
        requirement_text: str,
        auto_analyze: bool = True,
    ) -> ClarificationSession:
        session = ClarificationSession(
            id=f"session_{int(datetime.now().timestamp() * 1000)}",
            original_requirement=requirement_text,
            state=ClarificationState.NOT_STARTED,
        )

        if auto_analyze and self._requirement_analyzer:
            analysis = self._requirement_analyzer.analyze(requirement_text)
            session.analysis = analysis
            self._populate_questions_from_analysis(session, analysis)

        self._active_sessions[session.id] = session
        return session

    def _populate_questions_from_analysis(
        self,
        session: ClarificationSession,
        analysis: RequirementAnalysis,
    ) -> None:
        questions: List[ClarificationQuestion] = []

        for amb in analysis.ambiguities:
            level_priority = {
                AmbiguityLevel.CRITICAL: 100,
                AmbiguityLevel.HIGH: 80,
                AmbiguityLevel.MEDIUM: 50,
                AmbiguityLevel.LOW: 20,
                AmbiguityLevel.NONE: 0,
            }

            priority = level_priority.get(amb.level, 0)
            if priority >= 20:
                question = self._question_generator.generate_from_ambiguity(amb)
                question.metadata["priority"] = priority
                questions.append(question)

        if not analysis.performance_goals:
            perf_question = self._question_generator.generate_performance_question()
            perf_question.metadata["priority"] = 60
            perf_question.is_required = False
            questions.append(perf_question)

        if len(analysis.target_platforms) == 1 and analysis.target_platforms[0] == "linux-6.x":
            default_platform = self._platform_detector.get_default_platform() if self._platform_detector else "linux-6.x"
            if analysis.target_platforms[0] == default_platform:
                platform_question = self._question_generator.generate_platform_question()
                platform_question.metadata["priority"] = 40
                platform_question.is_required = False
                questions.append(platform_question)

        if not analysis.computing_patterns:
            pattern_question = self._question_generator.generate_pattern_question()
            pattern_question.metadata["priority"] = 30
            pattern_question.is_required = False
            questions.append(pattern_question)

        questions.sort(key=lambda q: q.metadata.get("priority", 0), reverse=True)

        session.questions = questions

    def start_session(self, session: ClarificationSession) -> Optional[ClarificationQuestion]:
        session.state = ClarificationState.IN_PROGRESS
        session.started_at = datetime.now()
        session.current_question_index = 0

        session.history.append(
            {
                "action": "start",
                "timestamp": datetime.now().isoformat(),
                "question_count": len(session.questions),
            }
        )

        return self.get_current_question(session)

    def get_current_question(self, session: ClarificationSession) -> Optional[ClarificationQuestion]:
        if 0 <= session.current_question_index < len(session.questions):
            session.state = ClarificationState.WAITING_USER
            return session.questions[session.current_question_index]
        return None

    def answer_question(
        self,
        session: ClarificationSession,
        answer: str,
        confidence: float = 1.0,
    ) -> Optional[ClarificationQuestion]:
        current = self.get_current_question(session)
        if current:
            current.answer = answer
            current.answer_confidence = confidence
            session.answers[current.id] = answer

            session.history.append(
                {
                    "action": "answer",
                    "question_id": current.id,
                    "answer": answer,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        session.current_question_index += 1

        next_question = self.get_current_question(session)

        if next_question is None:
            session.state = ClarificationState.COMPLETED
            session.completed_at = datetime.now()

            session.history.append(
                {
                    "action": "complete",
                    "timestamp": datetime.now().isoformat(),
                    "total_answered": len(session.answers),
                }
            )

        return next_question

    def skip_question(self, session: ClarificationSession) -> Optional[ClarificationQuestion]:
        current = self.get_current_question(session)
        if current and not current.is_required:
            current.answer = "(跳过)"
            current.answer_confidence = 0.0
            return self.answer_question(session, "(跳过)", 0.0)
        return self.answer_question(session, "", 0.0)

    def has_required_remaining(self, session: ClarificationSession) -> bool:
        for i in range(session.current_question_index, len(session.questions)):
            q = session.questions[i]
            if q.is_required and q.answer is None:
                return True
        return False

    def get_session_status(self, session: ClarificationSession) -> Dict[str, Any]:
        total = len(session.questions)
        answered = len(session.answers)
        required_remaining = sum(
            1 for q in session.questions
            if q.is_required and q.answer is None
        )

        return {
            "session_id": session.id,
            "state": session.state.value,
            "total_questions": total,
            "answered": answered,
            "required_remaining": required_remaining,
            "progress": answered / max(1, total),
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "current_index": session.current_question_index,
        }

    def get_progress_summary(self, session: ClarificationSession) -> str:
        status = self.get_session_status(session)
        total = status["total_questions"]
        answered = status["answered"]
        remaining = total - answered

        progress_pct = int(status["progress"] * 100)
        progress_bar = "█" * (progress_pct // 10) + "░" * (10 - progress_pct // 10)

        lines = []
        lines.append("澄清进度:")
        lines.append(f"  [{progress_bar}] {progress_pct}%")
        lines.append(f"  已回答: {answered}/{total}")
        if remaining > 0:
            lines.append(f"  剩余: {remaining} 个问题")
        if status["required_remaining"] > 0:
            lines.append(f"  必答: {status['required_remaining']} 个")

        return "\n".join(lines)

    def consolidate_answers(self, session: ClarificationSession) -> Dict[str, Any]:
        result = {
            "original_requirement": session.original_requirement,
            "answers": {},
            "clarified_goals": [],
            "clarified_platforms": [],
            "clarified_patterns": [],
            "resolved_ambiguities": [],
        }

        for q in session.questions:
            if q.answer and q.answer != "(跳过)":
                result["answers"][q.id] = {
                    "question": q.question_text,
                    "answer": q.answer,
                    "confidence": q.answer_confidence,
                    "type": q.question_type.value,
                }

                if q.question_type == ClarificationType.PERFORMANCE_GOAL:
                    goal_mapping = {
                        "最小化延迟": "min_latency",
                        "快速响应": "min_latency",
                        "最大化吞吐量": "max_throughput",
                        "处理更多请求": "max_throughput",
                        "最小化能耗": "min_energy",
                        "省电": "min_energy",
                        "最小化代码体积": "min_size",
                        "平衡各项指标": "min_latency + max_throughput",
                    }
                    for key, value in goal_mapping.items():
                        if key in q.answer:
                            if " + " in value:
                                result["clarified_goals"].extend(value.split(" + "))
                            else:
                                result["clarified_goals"].append(value)
                            break

                elif q.question_type == ClarificationType.TARGET_PLATFORM:
                    platform_mapping = {
                        "Linux": "linux-6.x",
                        "linux": "linux-6.x",
                        "Android": "android-14",
                        "android": "android-14",
                        "iOS": "ios-18",
                        "ios": "ios-18",
                        "Windows": "win-11",
                        "windows": "win-11",
                        "鸿蒙": "harmony-5",
                        "HarmonyOS": "harmony-5",
                        "嵌入式": "embedded",
                        "浏览器": "wasm-wasi",
                        "WebAssembly": "wasm-wasi",
                    }
                    for key, value in platform_mapping.items():
                        if key in q.answer:
                            result["clarified_platforms"].append(value)
                            break

                elif q.question_type == ClarificationType.COMPUTING_PATTERN:
                    pattern_mapping = {
                        "并行": "parallel",
                        "同时": "parallel",
                        "流水线": "pipeline",
                        "分阶段": "pipeline",
                        "流式": "streaming",
                        "连续": "streaming",
                        "批量": "batch",
                        "一次性": "batch",
                        "事件驱动": "event_driven",
                        "响应式": "event_driven",
                        "顺序": "sequential",
                    }
                    for key, value in pattern_mapping.items():
                        if key in q.answer:
                            result["clarified_patterns"].append(value)
                            break

                if q.related_ambiguity:
                    result["resolved_ambiguities"].append(
                        {
                            "original_term": q.related_ambiguity.text,
                            "clarified_as": q.answer,
                            "category": q.related_ambiguity.category,
                        }
                    )

        result["clarified_goals"] = list(dict.fromkeys(result["clarified_goals"]))
        result["clarified_platforms"] = list(dict.fromkeys(result["clarified_platforms"]))
        result["clarified_patterns"] = list(dict.fromkeys(result["clarified_patterns"]))

        return result

    def generate_clarified_requirement(
        self,
        session: ClarificationSession,
    ) -> str:
        consolidated = self.consolidate_answers(session)
        parts = [session.original_requirement]

        if consolidated["clarified_goals"]:
            goals_str = "、".join(consolidated["clarified_goals"])
            parts.append(f"\n\n[澄清后的性能目标: {goals_str}]")

        if consolidated["clarified_platforms"]:
            platforms_str = "、".join(consolidated["clarified_platforms"])
            parts.append(f"[目标平台: {platforms_str}]")

        if consolidated["clarified_patterns"]:
            patterns_str = "、".join(consolidated["clarified_patterns"])
            parts.append(f"[计算模式: {patterns_str}]")

        if consolidated["resolved_ambiguities"]:
            parts.append("\n\n[已澄清的模糊点]:")
            for amb in consolidated["resolved_ambiguities"]:
                parts.append(f"  - 「{amb['original_term']}」已澄清为: {amb['clarified_as']}")

        return "".join(parts)

    def cancel_session(self, session: ClarificationSession) -> None:
        session.state = ClarificationState.CANCELLED
        session.history.append(
            {
                "action": "cancel",
                "timestamp": datetime.now().isoformat(),
            }
        )
        if session.id in self._active_sessions:
            del self._active_sessions[session.id]

    def get_session(self, session_id: str) -> Optional[ClarificationSession]:
        return self._active_sessions.get(session_id)

    def list_active_sessions(self) -> List[str]:
        return list(self._active_sessions.keys())


class InteractiveClarificationFlow:
    def __init__(self):
        self._manager = ClarificationManager()
        self._current_session: Optional[ClarificationSession] = None

    def start(self, requirement: str) -> str:
        self._current_session = self._manager.create_session(requirement)

        if not self._current_session.questions:
            return "✅ 需求清晰，无需额外澄清。"

        status = self._manager.get_session_status(self._current_session)
        total = status["total_questions"]

        response = f"📋 检测到 {total} 个需要澄清的问题。\n"
        response += f"开始澄清流程...\n\n"

        first_question = self._manager.start_session(self._current_session)
        if first_question:
            response += self._format_question(first_question)

        return response

    def _format_question(self, question: ClarificationQuestion) -> str:
        lines = []
        lines.append("=" * 60)

        if question.is_required:
            lines.append(f"❓ 问题 [{question.question_type.value}] (必答):")
        else:
            lines.append(f"❓ 问题 [{question.question_type.value}] (可选):")

        lines.append("")
        lines.append(f"   {question.question_text}")
        lines.append("")

        if question.options:
            lines.append("   可选答案:")
            for i, option in enumerate(question.options, 1):
                if i - 1 == question.default_option_index:
                    lines.append(f"   [{i}] {option} (默认)")
                else:
                    lines.append(f"   [{i}] {option}")

            lines.append("")
            lines.append("   请输入选项序号或直接输入答案。")
            if not question.is_required:
                lines.append("   输入 'skip' 跳过此问题。")

        lines.append("=" * 60)

        return "\n".join(lines)

    def process_answer(self, answer: str) -> str:
        if not self._current_session:
            return "⚠️ 当前没有活跃的澄清会话。"

        answer = answer.strip()

        if answer.lower() in ["skip", "跳过"]:
            next_question = self._manager.skip_question(self._current_session)
        else:
            next_question = self._manager.answer_question(self._current_session, answer)

        status = self._manager.get_session_status(self._current_session)

        response = ""
        response += f"\n{self._manager.get_progress_summary(self._current_session)}\n"

        if next_question:
            response += "\n" + self._format_question(next_question)
        else:
            response += "\n" + "=" * 60
            response += "\n✅ 澄清流程完成！"
            response += "\n" + "=" * 60

            consolidated = self._manager.consolidate_answers(self._current_session)
            response += f"\n\n📊 澄清结果摘要:"
            response += f"\n   原始需求: {self._current_session.original_requirement[:50]}..."

            if consolidated["clarified_goals"]:
                response += f"\n   性能目标: {', '.join(consolidated['clarified_goals'])}"

            if consolidated["clarified_platforms"]:
                response += f"\n   目标平台: {', '.join(consolidated['clarified_platforms'])}"

            if consolidated["clarified_patterns"]:
                response += f"\n   计算模式: {', '.join(consolidated['clarified_patterns'])}"

            response += "\n\n" + self._manager.generate_clarified_requirement(self._current_session)

        return response

    def get_current_session(self) -> Optional[ClarificationSession]:
        return self._current_session

    def is_complete(self) -> bool:
        if not self._current_session:
            return True
        return self._current_session.state == ClarificationState.COMPLETED

    def get_status(self) -> Dict[str, Any]:
        if not self._current_session:
            return {"state": "no_session"}
        return self._manager.get_session_status(self._current_session)
