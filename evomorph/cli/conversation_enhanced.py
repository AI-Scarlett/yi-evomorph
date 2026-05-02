"""
AI 对话增强模块
- 上下文感知对话
- 代码 diff 显示
- 多轮需求澄清
- 对话历史管理
"""

import re
import time
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
    from evomorph.cli.visualization import CodeDiffVisualizer, CodeDiff

    HAS_VISUALIZATION = True
except ImportError:
    HAS_VISUALIZATION = False
    CodeDiffVisualizer = None
    CodeDiff = None


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MessageType(Enum):
    TEXT = "text"
    CODE = "code"
    DIFF = "diff"
    QUESTION = "question"
    CONFIRMATION = "confirmation"
    ERROR = "error"
    WARNING = "warning"
    SUCCESS = "success"


class ContextType(Enum):
    CODE_CONTEXT = "code_context"
    CONVERSATION_HISTORY = "conversation_history"
    DOCUMENTATION = "documentation"
    ERROR_CONTEXT = "error_context"
    PLATFORM_CONTEXT = "platform_context"


@dataclass
class ConversationMessage:
    role: MessageRole
    content: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"msg_{int(time.time() * 1e6)}_{id(self)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class CodeContext:
    file_path: str = ""
    content: str = ""
    line_numbers: Tuple[int, int] = (1, 1)
    language: str = "evomorph"
    relevance_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_numbers": list(self.line_numbers),
            "language": self.language,
            "relevance_score": self.relevance_score,
        }


@dataclass
class ClarificationQuestion:
    id: str = ""
    question: str = ""
    options: List[str] = field(default_factory=list)
    answer_type: str = "single_choice"
    is_required: bool = False
    context: str = ""
    answer: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            self.id = f"q_{int(time.time() * 1e6)}"


class ContextWindowManager:
    def __init__(self, max_tokens: int = 128000, max_messages: int = 50):
        self.max_tokens = max_tokens
        self.max_messages = max_messages
        self._messages: List[ConversationMessage] = []
        self._contexts: Dict[str, CodeContext] = {}

    def add_message(self, message: ConversationMessage) -> None:
        self._messages.append(message)
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages :]

    def add_context(self, key: str, context: CodeContext) -> None:
        self._contexts[key] = context

    def remove_context(self, key: str) -> None:
        self._contexts.pop(key, None)

    def get_recent_messages(self, count: int = 10) -> List[ConversationMessage]:
        return self._messages[-count:]

    def get_context_summary(self) -> str:
        if not self._contexts:
            return ""

        parts = ["[当前上下文]"]
        for key, ctx in self._contexts.items():
            if ctx.file_path:
                parts.append(f"文件: {ctx.file_path} (行 {ctx.line_numbers[0]}-{ctx.line_numbers[1]})")
            if ctx.content:
                preview = ctx.content[:500]
                if len(ctx.content) > 500:
                    preview += "..."
                parts.append(f"内容预览:\n{preview}")

        return "\n".join(parts)

    def build_prompt_context(self, include_recent: int = 5) -> List[Dict[str, str]]:
        result = []

        for msg in self._messages[-include_recent:]:
            result.append(
                {"role": msg.role.value, "content": msg.content}
            )

        return result

    def clear(self) -> None:
        self._messages.clear()
        self._contexts.clear()


class ConversationHistory:
    def __init__(self, max_items: int = 100):
        self.max_items = max_items
        self._messages: List[ConversationMessage] = []
        self._sessions: List[Dict[str, Any]] = []
        self._current_session_id: str = ""

    def start_session(self, session_id: Optional[str] = None) -> str:
        if session_id is None:
            session_id = f"session_{int(time.time())}"

        self._current_session_id = session_id
        self._sessions.append(
            {
                "id": session_id,
                "start_time": datetime.now(),
                "message_count": 0,
            }
        )
        return session_id

    def add_message(self, message: ConversationMessage) -> None:
        self._messages.append(message)

        for session in reversed(self._sessions):
            if session["id"] == self._current_session_id:
                session["message_count"] += 1
                break

        if len(self._messages) > self.max_items:
            self._messages = self._messages[-self.max_items:]

    def get_messages(
        self,
        since: Optional[datetime] = None,
        role: Optional[MessageRole] = None,
        session_id: Optional[str] = None,
    ) -> List[ConversationMessage]:
        result = self._messages

        if since:
            result = [m for m in result if m.timestamp >= since]

        if role:
            result = [m for m in result if m.role == role]

        return result

    def search(self, keyword: str) -> List[ConversationMessage]:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        return [m for m in self._messages if pattern.search(m.content)]

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_messages": len(self._messages),
            "total_sessions": len(self._sessions),
            "current_session": self._current_session_id,
            "messages_by_role": {
                "user": len([m for m in self._messages if m.role == MessageRole.USER]),
                "assistant": len([m for m in self._messages if m.role == MessageRole.ASSISTANT]),
                "system": len([m for m in self._messages if m.role == MessageRole.SYSTEM]),
            },
        }

    def export(self) -> List[Dict[str, Any]]:
        return [msg.to_dict() for msg in self._messages]


class CodeDiffPresenter:
    def __init__(self):
        self._visualizer = CodeDiffVisualizer() if HAS_VISUALIZATION and CodeDiffVisualizer else None
        self._change_stats: Dict[str, int] = {}

    def compute_diff(
        self, original: str, modified: str, context_lines: int = 3
    ) -> Dict[str, Any]:
        if self._visualizer:
            self._visualizer.context_lines = context_lines
            diff = self._visualizer.compute_diff(original, modified)

            additions = 0
            deletions = 0
            for hunk in diff.hunks:
                for change in hunk.get("changes", []):
                    if change.get("type") == "insert":
                        additions += 1
                    elif change.get("type") == "delete":
                        deletions += 1

            self._change_stats = {
                "additions": additions,
                "deletions": deletions,
                "hunks": len(diff.hunks),
            }

            return {
                "diff_obj": diff,
                "original": original,
                "modified": modified,
                "stats": self._change_stats,
            }
        else:
            return self._simple_diff(original, modified)

    def _simple_diff(self, original: str, modified: str) -> Dict[str, Any]:
        orig_lines = original.split("\n")
        mod_lines = modified.split("\n")

        min_len = min(len(orig_lines), len(mod_lines))
        changes = []

        for i in range(min_len):
            if orig_lines[i] != mod_lines[i]:
                changes.append(
                    {
                        "line": i + 1,
                        "original": orig_lines[i],
                        "modified": mod_lines[i],
                    }
                )

        if len(orig_lines) > min_len:
            for i in range(min_len, len(orig_lines)):
                changes.append(
                    {
                        "line": i + 1,
                        "original": orig_lines[i],
                        "modified": None,
                        "type": "delete",
                    }
                )

        if len(mod_lines) > min_len:
            for i in range(min_len, len(mod_lines)):
                changes.append(
                    {
                        "line": i + 1,
                        "original": None,
                        "modified": mod_lines[i],
                        "type": "insert",
                    }
                )

        self._change_stats = {
            "additions": len([c for c in changes if c.get("type") == "insert"]),
            "deletions": len([c for c in changes if c.get("type") == "delete"]),
            "changes": len([c for c in changes if "type" not in c]),
        }

        return {
            "changes": changes,
            "original": original,
            "modified": modified,
            "stats": self._change_stats,
        }

    def format_diff(
        self,
        diff_data: Dict[str, Any],
        use_colors: bool = True,
        compact: bool = False,
    ) -> str:
        if "diff_obj" in diff_data and self._visualizer:
            return self._visualizer.render_diff(diff_data["diff_obj"], use_colors=use_colors)

        changes = diff_data.get("changes", [])
        if not changes:
            return "(无变更)"

        lines = []
        stats = diff_data.get("stats", {})

        lines.append("=" * 60)
        lines.append(
            f"变更摘要: +{stats.get('additions', 0)} -{stats.get('deletions', 0)}"
        )
        lines.append("=" * 60)

        for change in changes:
            line_num = change.get("line", 0)
            original = change.get("original")
            modified = change.get("modified")
            change_type = change.get("type", "modify")

            if change_type == "insert":
                if use_colors:
                    lines.append(f"\033[32m+{line_num:4d} | {modified}\033[0m")
                else:
                    lines.append(f"+{line_num:4d} | {modified}")
            elif change_type == "delete":
                if use_colors:
                    lines.append(f"\033[31m-{line_num:4d} | {original}\033[0m")
                else:
                    lines.append(f"-{line_num:4d} | {original}")
            else:
                if use_colors:
                    lines.append(f"\033[31m-{line_num:4d} | {original}\033[0m")
                    lines.append(f"\033[32m+{line_num:4d} | {modified}\033[0m")
                else:
                    lines.append(f"-{line_num:4d} | {original}")
                    lines.append(f"+{line_num:4d} | {modified}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def generate_summary(self, diff_data: Dict[str, Any]) -> str:
        stats = diff_data.get("stats", {})
        additions = stats.get("additions", 0)
        deletions = stats.get("deletions", 0)
        hunks = stats.get("hunks", 0)

        parts = []

        if additions == 0 and deletions == 0:
            return "代码未变更"

        if additions > 0:
            parts.append(f"新增 {additions} 行")
        if deletions > 0:
            parts.append(f"删除 {deletions} 行")

        if hunks > 0:
            parts.append(f"共 {hunks} 个变更区块")

        return " | ".join(parts)


class ContextAwareResponder:
    def __init__(self):
        self._context_window = ContextWindowManager()
        self._history = ConversationHistory()
        self._code_extractor = CodeExtractor()

    def add_user_message(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            role=MessageRole.USER,
            content=content,
            metadata=metadata or {},
        )
        self._history.add_message(msg)
        self._context_window.add_message(msg)
        return msg

    def add_assistant_message(
        self,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            role=MessageRole.ASSISTANT,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
        )
        self._history.add_message(msg)
        self._context_window.add_message(msg)
        return msg

    def add_code_context(
        self,
        content: str,
        file_path: str = "",
        language: str = "evomorph",
    ) -> None:
        context = CodeContext(
            content=content,
            file_path=file_path,
            language=language,
            relevance_score=1.0,
        )
        self._context_window.add_context(file_path or "current_code", context)

    def extract_code_from_message(self, message: ConversationMessage) -> List[Dict[str, str]]:
        return self._code_extractor.extract_code_blocks(message.content)

    def get_conversation_context(self) -> str:
        recent = self._context_window.get_recent_messages(3)
        parts = []

        for msg in recent:
            role_label = "用户" if msg.role == MessageRole.USER else "助手"
            content_preview = msg.content[:200]
            if len(msg.content) > 200:
                content_preview += "..."
            parts.append(f"[{role_label}]: {content_preview}")

        code_context = self._context_window.get_context_summary()
        if code_context:
            parts.append(code_context)

        return "\n".join(parts)

    def build_system_prompt(
        self,
        base_prompt: str,
        include_code_context: bool = True,
        include_conversation: bool = True,
    ) -> str:
        parts = [base_prompt]

        if include_conversation:
            conv_ctx = self.get_conversation_context()
            if conv_ctx:
                parts.append("\n\n[对话上下文]\n" + conv_ctx)

        return "\n".join(parts)

    def get_history_summary(self) -> Dict[str, Any]:
        return self._history.get_summary()

    def clear_context(self) -> None:
        self._context_window.clear()


class CodeExtractor:
    def __init__(self):
        self._patterns = {
            "fenced": re.compile(
                r"```(?:(\w+))?\s*\n(.*?)```",
                re.DOTALL,
            ),
            "inline_fenced": re.compile(r"`([^`]+)`"),
            "evo_keywords": [
                "@evolang",
                "@locus",
                "@meta_locus",
                "@xiangci",
                "mut_rate",
                "fitness",
                "env_target",
                "卦序",
            ],
            "hexagram_chars": set("䷀䷁䷂䷃䷄䷅䷆䷇䷈䷉䷊䷋䷌䷍䷎䷏䷐䷑䷒䷓䷔䷕䷖䷗䷘䷙䷚䷛䷜䷝䷞䷟䷠䷡䷢䷣䷤䷥䷦䷧䷨䷩䷪䷫䷬䷭䷮䷯䷰䷱䷲䷳䷴䷵䷶䷷䷸䷹䷺䷻䷼䷽䷾䷿"),
        }

    def extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        results = []

        fenced_matches = self._patterns["fenced"].findall(text)
        for match in fenced_matches:
            language = match[0] if match[0] else ""
            code = match[1].strip()
            if self._is_likely_evo_code(code, language):
                results.append(
                    {
                        "code": code,
                        "language": language or "evomorph",
                        "type": "fenced",
                    }
                )

        if not results:
            if self._contains_evo_patterns(text):
                results.append(
                    {
                        "code": text.strip(),
                        "language": "evomorph",
                        "type": "inline",
                    }
                )

        return results

    def _is_likely_evo_code(self, code: str, language: str) -> bool:
        if language in ["evomorph", "evo"]:
            return True

        if self._contains_evo_patterns(code):
            return True

        return False

    def _contains_evo_patterns(self, text: str) -> bool:
        for keyword in self._patterns["evo_keywords"]:
            if keyword in text:
                return True

        for char in text:
            if char in self._patterns["hexagram_chars"]:
                return True

        return False

    def extract_filename(self, text: str) -> Optional[str]:
        patterns = [
            r"文件[：:]\s*([^\s，。；,\n]+\.(?:evo|evb|evoi))",
            r"保存到\s*([^\s，。；,\n]+\.(?:evo|evb|evoi))",
            r"([^\s，。；,\n]+\.evo)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None


class ResponseFormatter:
    def __init__(self):
        self._diff_presenter = CodeDiffPresenter()

    def format_code_block(
        self,
        code: str,
        language: str = "evomorph",
        line_numbers: bool = True,
        title: Optional[str] = None,
    ) -> str:
        lines = code.split("\n")

        result_parts = []

        if title:
            result_parts.append(f"┌─ {title} {'─' * max(0, 60 - len(title) - 4)}┐")
        else:
            result_parts.append("┌" + "─" * 60 + "┐")

        max_line_num = len(lines)
        line_num_width = len(str(max_line_num))

        for i, line in enumerate(lines):
            if line_numbers:
                line_num = str(i + 1).rjust(line_num_width)
                result_parts.append(f"│ {line_num} │ {line}")
            else:
                result_parts.append(f"│ {line}")

        result_parts.append("└" + "─" * 60 + "┘")

        return "\n".join(result_parts)

    def format_error(
        self,
        message: str,
        error_type: str = "错误",
        details: Optional[str] = None,
    ) -> str:
        lines = []
        lines.append("╔" + "═" * 60 + "╗")
        lines.append(f"║ ❌ {error_type}: {message[:50]:<50} ║")

        if details:
            detail_lines = details.split("\n")
            for dl in detail_lines:
                lines.append(f"║    {dl[:56]:<56} ║")

        lines.append("╚" + "═" * 60 + "╝")
        return "\n".join(lines)

    def format_warning(
        self,
        message: str,
        details: Optional[str] = None,
    ) -> str:
        lines = []
        lines.append("╓" + "─" * 60 + "╖")
        lines.append(f"║ ⚠️  警告: {message[:51]:<51} ║")

        if details:
            detail_lines = details.split("\n")
            for dl in detail_lines:
                lines.append(f"║    {dl[:56]:<56} ║")

        lines.append("╙" + "─" * 60 + "╜")
        return "\n".join(lines)

    def format_success(
        self,
        message: str,
        details: Optional[str] = None,
    ) -> str:
        lines = []
        lines.append("┏" + "━" * 60 + "┓")
        lines.append(f"┃ ✅ 成功: {message[:51]:<51} ┃")

        if details:
            detail_lines = details.split("\n")
            for dl in detail_lines:
                lines.append(f"┃    {dl[:56]:<56} ┃")

        lines.append("┗" + "━" * 60 + "┛")
        return "\n".join(lines)

    def format_info(
        self,
        message: str,
        details: Optional[str] = None,
    ) -> str:
        lines = []
        lines.append("─── " + message + " " + "─" * max(0, 55 - len(message)))

        if details:
            detail_lines = details.split("\n")
            for dl in detail_lines:
                lines.append(f"    {dl}")

        return "\n".join(lines)

    def format_question(
        self,
        question: str,
        options: Optional[List[str]] = None,
        default_index: int = 0,
    ) -> str:
        lines = []
        lines.append("? " + question)

        if options:
            for i, option in enumerate(options):
                marker = " [*]" if i == default_index else " [ ]"
                lines.append(f"  {i + 1}. {option}{marker}")

        return "\n".join(lines)

    def format_table(
        self,
        headers: List[str],
        rows: List[List[Any]],
        title: Optional[str] = None,
    ) -> str:
        if not headers:
            return ""

        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))

        lines = []

        if title:
            total_width = sum(col_widths) + 3 * len(headers) + 1
            lines.append("┌" + "─" * (total_width - 2) + "┐")
            lines.append(f"│ {title:<{total_width - 4}} │")
            lines.append("├" + "─" * (total_width - 2) + "┤")

        header_line = "│"
        for i, header in enumerate(headers):
            header_line += f" {header:<{col_widths[i]}} │"
        lines.append(header_line)

        sep_line = "├"
        for w in col_widths:
            sep_line += "─" * (w + 2) + "┼"
        sep_line = sep_line[:-1] + "┤"
        lines.append(sep_line)

        for row in rows:
            row_line = "│"
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    row_line += f" {str(cell):<{col_widths[i]}} │"
            lines.append(row_line)

        end_line = "└"
        for w in col_widths:
            end_line += "─" * (w + 2) + "┴"
        end_line = end_line[:-1] + "┘"
        lines.append(end_line)

        return "\n".join(lines)

    def format_diff(
        self,
        original: str,
        modified: str,
        use_colors: bool = True,
        compact: bool = False,
    ) -> str:
        diff_data = self._diff_presenter.compute_diff(original, modified)
        return self._diff_presenter.format_diff(diff_data, use_colors=use_colors, compact=compact)

    def format_diff_summary(
        self,
        original: str,
        modified: str,
    ) -> str:
        diff_data = self._diff_presenter.compute_diff(original, modified)
        return self._diff_presenter.generate_summary(diff_data)


class DialogManager:
    def __init__(self):
        self._questions: List[ClarificationQuestion] = []
        self._current_question_index: int = -1
        self._answers: Dict[str, str] = {}
        self._on_complete: Optional[Callable[[Dict[str, str]], None]] = None

    def add_question(self, question: ClarificationQuestion) -> None:
        self._questions.append(question)

    def add_questions(self, questions: List[ClarificationQuestion]) -> None:
        self._questions.extend(questions)

    def start(self, on_complete: Optional[Callable[[Dict[str, str]], None]] = None) -> Optional[ClarificationQuestion]:
        self._on_complete = on_complete
        self._current_question_index = 0
        return self.get_current_question()

    def get_current_question(self) -> Optional[ClarificationQuestion]:
        if 0 <= self._current_question_index < len(self._questions):
            return self._questions[self._current_question_index]
        return None

    def answer_question(self, answer: str) -> Optional[ClarificationQuestion]:
        current = self.get_current_question()
        if current:
            current.answer = answer
            self._answers[current.id] = answer

        self._current_question_index += 1

        next_question = self.get_current_question()
        if next_question is None and self._on_complete:
            self._on_complete(self._answers)

        return next_question

    def skip_question(self) -> Optional[ClarificationQuestion]:
        return self.answer_question("")

    def get_all_answers(self) -> Dict[str, str]:
        return self._answers.copy()

    def get_unanswered_required(self) -> List[ClarificationQuestion]:
        return [
            q for q in self._questions
            if q.is_required and q.answer is None
        ]

    def is_complete(self) -> bool:
        return self._current_question_index >= len(self._questions)

    def has_required_remaining(self) -> bool:
        return len(self.get_unanswered_required()) > 0

    def reset(self) -> None:
        self._questions.clear()
        self._current_question_index = -1
        self._answers.clear()
        self._on_complete = None


def format_duration(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        return f"{seconds / 3600:.1f}h"


def format_file_size(bytes_: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_ < 1024:
            return f"{bytes_:.1f}{unit}"
        bytes_ /= 1024
    return f"{bytes_:.1f}TB"
