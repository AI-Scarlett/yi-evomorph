"""
可视化进化界面
- 实时进度条显示
- ASCII 图表
- 交互式代码编辑
- 调试可视化
"""

import math
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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

    from rich.console import Console, Group
    from rich.table import Table as RichTable
    from rich.text import Text
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.panel import Panel
    from rich.progress import (
        Progress as RichProgress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TimeRemainingColumn,
        TimeElapsedColumn,
        TaskProgressColumn,
    )
    from rich.rule import Rule
    from rich.columns import Columns
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False


class ProgressBarStyle(Enum):
    SIMPLE = "simple"
    BLOCK = "block"
    DETAILED = "detailed"
    ANIMATED = "animated"


class ChartType(Enum):
    LINE = "line"
    BAR = "bar"
    HISTOGRAM = "histogram"
    SPARKLINE = "sparkline"


@dataclass
class ProgressMetrics:
    generation: int = 0
    total_generations: int = 100
    best_fitness: float = 0.0
    avg_fitness: float = 0.0
    population_size: int = 0
    mutations: int = 0
    crossovers: int = 0
    time_elapsed: float = 0.0
    improvements: int = 0
    diversities: List[float] = field(default_factory=list)


@dataclass
class CodeDiff:
    original: str
    modified: str
    hunks: List[Dict[str, Any]] = field(default_factory=list)


class BaseVisualizer(ABC):
    @abstractmethod
    def render(self) -> str:
        pass

    @abstractmethod
    def update(self, **kwargs) -> None:
        pass


class ASCIIProgressBar(BaseVisualizer):
    def __init__(
        self,
        width: int = 50,
        style: ProgressBarStyle = ProgressBarStyle.BLOCK,
        show_percent: bool = True,
        show_count: bool = False,
    ):
        self.width = width
        self.style = style
        self.show_percent = show_percent
        self.show_count = show_count
        self._current: float = 0.0
        self._total: float = 100.0
        self._animated_pos = 0

    def update(self, current: Optional[float] = None, total: Optional[float] = None, **kwargs):
        if current is not None:
            self._current = current
        if total is not None:
            self._total = total
        self._animated_pos = (self._animated_pos + 1) % self.width

    def render(self) -> str:
        if self._total <= 0:
            percent = 0.0
        else:
            percent = min(1.0, self._current / self._total)

        filled = int(percent * self.width)

        if self.style == ProgressBarStyle.SIMPLE:
            bar = "=" * filled + "-" * (self.width - filled)
        elif self.style == ProgressBarStyle.BLOCK:
            bar = "█" * filled + "░" * (self.width - filled)
        elif self.style == ProgressBarStyle.ANIMATED:
            if filled < self.width:
                bar = "█" * filled + "▌" + "░" * max(0, self.width - filled - 1)
            else:
                bar = "█" * self.width
        else:
            bar = "[" + "=" * filled + ">" + "-" * max(0, self.width - filled - 1) + "]"

        parts = [f"[{bar}]"]

        if self.show_percent:
            parts.append(f"{percent * 100:6.1f}%")

        if self.show_count:
            parts.append(f"({int(self._current)}/{int(self._total)})")

        return " ".join(parts)


class ASCIIChart(BaseVisualizer):
    def __init__(
        self,
        chart_type: ChartType = ChartType.LINE,
        width: int = 60,
        height: int = 15,
        title: str = "",
        x_label: str = "",
        y_label: str = "",
    ):
        self.chart_type = chart_type
        self.width = width
        self.height = height
        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self._data: List[float] = []
        self._max_value: float = 0.0
        self._min_value: float = 0.0

    def update(self, data: Optional[List[float]] = None, **kwargs):
        if data is not None:
            self._data = data
            if self._data:
                self._max_value = max(self._data)
                self._min_value = min(self._data)
            else:
                self._max_value = 0.0
                self._min_value = 0.0

    def render(self) -> str:
        if not self._data:
            return "(no data)"

        lines = []

        if self.title:
            lines.append(f"┌─ {self.title} {'─' * max(0, self.width - len(self.title) - 4)}┐")
        else:
            lines.append("┌" + "─" * self.width + "┐")

        if self.chart_type == ChartType.SPARKLINE:
            chart_line = self._render_sparkline()
            lines.append(f"│ {chart_line}{' ' * (self.width - len(chart_line) - 2)} │")
        elif self.chart_type == ChartType.BAR:
            bars = self._render_bars()
            for bar_line in bars:
                lines.append(f"│ {bar_line}{' ' * (self.width - len(bar_line) - 2)} │")
        else:
            plot_lines = self._render_line_plot()
            for plot_line in plot_lines:
                lines.append(f"│ {plot_line}{' ' * (self.width - len(plot_line) - 2)} │")

        lines.append("└" + "─" * self.width + "┘")

        if self.x_label or self.y_label:
            labels = []
            if self.y_label:
                labels.append(f"Y: {self.y_label}")
            if self.x_label:
                labels.append(f"X: {self.x_label}")
            lines.append("  " + " | ".join(labels))

        return "\n".join(lines)

    def _render_sparkline(self) -> str:
        if len(self._data) == 0:
            return ""

        bars = "▁▂▃▄▅▆▇█"
        data_min = self._min_value
        data_max = self._max_value

        if data_max == data_min:
            normalized = [4] * len(self._data)
        else:
            normalized = [
                int(7 * (val - data_min) / (data_max - data_min))
                for val in self._data
            ]

        return "".join(bars[n] for n in normalized[-self.width :])

    def _render_bars(self) -> List[str]:
        if not self._data:
            return [""]

        data_range = max(self._max_value - self._min_value, 0.001)
        max_bar_height = self.height - 2

        bars = []
        num_bars = min(len(self._data), self.width // 2)
        data_points = self._data[-num_bars:] if len(self._data) > num_bars else self._data

        for h in range(max_bar_height, 0, -1):
            line = ""
            for val in data_points:
                normalized = (val - self._min_value) / data_range
                bar_height = int(normalized * max_bar_height)
                if bar_height >= h:
                    line += "██"
                else:
                    line += "  "
            bars.append(line)

        return bars

    def _render_line_plot(self) -> List[str]:
        if not self._data:
            return [""]

        data_range = max(self._max_value - self._min_value, 0.001)
        plot_height = self.height - 2

        num_points = min(len(self._data), self.width - 4)
        data_points = self._data[-num_points:] if len(self._data) > num_points else self._data

        normalized = [
            int(plot_height * (val - self._min_value) / data_range)
            for val in data_points
        ]

        lines = []
        for y in range(plot_height, -1, -1):
            line = ""
            last_x = 0
            for x, ny in enumerate(normalized):
                if ny == y:
                    line += "●"
                elif x > 0 and abs(ny - normalized[x - 1]) > 1:
                    min_ny = min(ny, normalized[x - 1])
                    max_ny = max(ny, normalized[x - 1])
                    if min_ny < y < max_ny:
                        line += "│"
                    else:
                        line += " "
                else:
                    line += " "
            lines.append(line)

        return lines


class EvolutionVisualizer(BaseVisualizer):
    def __init__(
        self,
        width: int = 80,
        show_fitness: bool = True,
        show_diversity: bool = True,
        show_progress: bool = True,
    ):
        self.width = width
        self.show_fitness = show_fitness
        self.show_diversity = show_diversity
        self.show_progress = show_progress

        self._metrics = ProgressMetrics()
        self._fitness_history: List[float] = []
        self._diversity_history: List[float] = []
        self._generation_time: List[float] = []

        self._progress_bar = ASCIIProgressBar(
            width=width - 20,
            style=ProgressBarStyle.BLOCK,
            show_percent=True,
            show_count=True,
        )
        self._fitness_chart = ASCIIChart(
            chart_type=ChartType.SPARKLINE,
            width=width - 10,
            height=5,
            title="Fitness",
        )
        self._diversity_chart = ASCIIChart(
            chart_type=ChartType.SPARKLINE,
            width=width - 10,
            height=5,
            title="Diversity",
        )

    def update(
        self,
        metrics: Optional[ProgressMetrics] = None,
        generation: Optional[int] = None,
        total_generations: Optional[int] = None,
        best_fitness: Optional[float] = None,
        avg_fitness: Optional[float] = None,
        population_size: Optional[int] = None,
        mutations: Optional[int] = None,
        crossovers: Optional[int] = None,
        time_elapsed: Optional[float] = None,
        improvements: Optional[int] = None,
        **kwargs,
    ):
        if metrics:
            self._metrics = metrics

        if generation is not None:
            self._metrics.generation = generation
        if total_generations is not None:
            self._metrics.total_generations = total_generations
        if best_fitness is not None:
            self._metrics.best_fitness = best_fitness
            self._fitness_history.append(best_fitness)
        if avg_fitness is not None:
            self._metrics.avg_fitness = avg_fitness
        if population_size is not None:
            self._metrics.population_size = population_size
        if mutations is not None:
            self._metrics.mutations = mutations
        if crossovers is not None:
            self._metrics.crossovers = crossovers
        if time_elapsed is not None:
            self._metrics.time_elapsed = time_elapsed
        if improvements is not None:
            self._metrics.improvements = improvements

        self._progress_bar.update(
            current=self._metrics.generation,
            total=self._metrics.total_generations,
        )
        self._fitness_chart.update(data=self._fitness_history[-50:])
        self._diversity_chart.update(data=self._diversity_history[-50:])

    def update_diversity(self, diversity: float):
        self._metrics.diversities.append(diversity)
        self._diversity_history.append(diversity)

    def render(self) -> str:
        lines = []
        w = self.width

        lines.append("╔" + "═" * (w - 2) + "╗")
        lines.append(f"║ {self._render_header():{w-4}} ║")
        lines.append("╠" + "═" * (w - 2) + "╣")

        if self.show_progress:
            lines.append(f"║ 进化进度: {self._progress_bar.render():{w-18}} ║")
            lines.append("║" + " " * (w - 2) + "║")

        lines.append(f"║ {self._render_stats():{w-4}} ║")
        lines.append("║" + " " * (w - 2) + "║")

        if self.show_fitness and self._fitness_history:
            self._fitness_chart.title = "适应度趋势 (Sparkline)"
            fitness_lines = self._fitness_chart.render().split("\n")
            for fl in fitness_lines:
                padded = fl.ljust(w - 4)[: w - 4]
                lines.append(f"║ {padded} ║")
            lines.append("║" + " " * (w - 2) + "║")

        if self.show_diversity and self._diversity_history:
            self._diversity_chart.title = "多样性趋势 (Sparkline)"
            diversity_lines = self._diversity_chart.render().split("\n")
            for dl in diversity_lines:
                padded = dl.ljust(w - 4)[: w - 4]
                lines.append(f"║ {padded} ║")

        lines.append("╚" + "═" * (w - 2) + "╝")

        return "\n".join(lines)

    def _render_header(self) -> str:
        gen = self._metrics.generation
        total = self._metrics.total_generations
        return f"🧬 易衍进化引擎 | 第 {gen}/{total} 代"

    def _render_stats(self) -> str:
        m = self._metrics
        parts = [
            f"最佳={m.best_fitness:.4f}",
            f"平均={m.avg_fitness:.4f}",
            f"种群={m.population_size}",
            f"突变={m.mutations}",
            f"交叉={m.crossovers}",
            f"改进={m.improvements}",
        ]
        return " | ".join(parts)


class CodeDiffVisualizer:
    def __init__(self, context_lines: int = 3):
        self.context_lines = context_lines

    def compute_diff(self, original: str, modified: str) -> CodeDiff:
        orig_lines = original.split("\n")
        mod_lines = modified.split("\n")

        hunks = self._compute_hunks(orig_lines, mod_lines)

        return CodeDiff(
            original=original,
            modified=modified,
            hunks=hunks,
        )

    def _compute_hunks(
        self, orig_lines: List[str], mod_lines: List[str]
    ) -> List[Dict[str, Any]]:
        hunks = []

        lcs = self._longest_common_subsequence(orig_lines, mod_lines)

        i, j = 0, 0
        current_hunk: Optional[Dict[str, Any]] = None

        for match_i, match_j in lcs:
            while i < match_i or j < match_j:
                if i < match_i and j < match_j:
                    change_type = "modify"
                elif i < match_i:
                    change_type = "delete"
                else:
                    change_type = "insert"

                if current_hunk is None:
                    current_hunk = {
                        "orig_start": max(0, i - self.context_lines),
                        "mod_start": max(0, j - self.context_lines),
                        "orig_lines": [],
                        "mod_lines": [],
                        "changes": [],
                    }

                for c in range(max(0, i - self.context_lines), i):
                    if c < len(orig_lines):
                        current_hunk["orig_lines"].append(
                            {"type": "context", "line": orig_lines[c], "num": c + 1}
                        )

                while i < match_i:
                    current_hunk["changes"].append(
                        {"type": "delete", "line": orig_lines[i], "orig_num": i + 1}
                    )
                    current_hunk["orig_lines"].append(
                        {"type": "delete", "line": orig_lines[i], "num": i + 1}
                    )
                    i += 1

                while j < match_j:
                    current_hunk["changes"].append(
                        {"type": "insert", "line": mod_lines[j], "mod_num": j + 1}
                    )
                    current_hunk["mod_lines"].append(
                        {"type": "insert", "line": mod_lines[j], "num": j + 1}
                    )
                    j += 1

            if current_hunk is not None:
                for c in range(match_i, min(match_i + self.context_lines, len(orig_lines))):
                    if c < len(orig_lines):
                        current_hunk["orig_lines"].append(
                            {"type": "context", "line": orig_lines[c], "num": c + 1}
                        )

            i = match_i + 1
            j = match_j + 1

            if current_hunk is not None:
                hunks.append(current_hunk)
                current_hunk = None

        while i < len(orig_lines) or j < len(mod_lines):
            if current_hunk is None:
                current_hunk = {
                    "orig_start": max(0, i - self.context_lines),
                    "mod_start": max(0, j - self.context_lines),
                    "orig_lines": [],
                    "mod_lines": [],
                    "changes": [],
                }

            if i < len(orig_lines):
                current_hunk["changes"].append(
                    {"type": "delete", "line": orig_lines[i], "orig_num": i + 1}
                )
                current_hunk["orig_lines"].append(
                    {"type": "delete", "line": orig_lines[i], "num": i + 1}
                )
                i += 1

            if j < len(mod_lines):
                current_hunk["changes"].append(
                    {"type": "insert", "line": mod_lines[j], "mod_num": j + 1}
                )
                current_hunk["mod_lines"].append(
                    {"type": "insert", "line": mod_lines[j], "num": j + 1}
                )
                j += 1

        if current_hunk is not None:
            hunks.append(current_hunk)

        return hunks

    def _longest_common_subsequence(
        self, a: List[str], b: List[str]
    ) -> List[Tuple[int, int]]:
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i - 1] == b[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        result = []
        i, j = m, n
        while i > 0 and j > 0:
            if a[i - 1] == b[j - 1]:
                result.append((i - 1, j - 1))
                i -= 1
                j -= 1
            elif dp[i - 1][j] > dp[i][j - 1]:
                i -= 1
            else:
                j -= 1

        return list(reversed(result))

    def render_diff(self, diff: CodeDiff, use_colors: bool = True) -> str:
        lines = []

        for hunk in diff.hunks:
            lines.append(
                f"@@ -{hunk['orig_start'] + 1},{len(hunk['orig_lines'])} "
                f"+{hunk['mod_start'] + 1},{len(hunk['mod_lines'])} @@"
            )

            all_lines = sorted(
                [
                    (line["num"], "orig", line["type"], line["line"])
                    for line in hunk["orig_lines"]
                ]
                + [
                    (line["num"], "mod", line["type"], line["line"])
                    for line in hunk["mod_lines"]
                ],
                key=lambda x: x[0],
            )

            for num, source, line_type, content in all_lines:
                if use_colors:
                    if line_type == "delete":
                        lines.append(f"\033[31m- {content}\033[0m")
                    elif line_type == "insert":
                        lines.append(f"\033[32m+ {content}\033[0m")
                    else:
                        lines.append(f"  {content}")
                else:
                    if line_type == "delete":
                        lines.append(f"- {content}")
                    elif line_type == "insert":
                        lines.append(f"+ {content}")
                    else:
                        lines.append(f"  {content}")

            lines.append("")

        return "\n".join(lines)


class LiveEvolutionMonitor:
    def __init__(
        self,
        visualizer: Optional[EvolutionVisualizer] = None,
        update_interval: float = 0.5,
    ):
        self.visualizer = visualizer or EvolutionVisualizer()
        self.update_interval = update_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._metrics = ProgressMetrics()
        self._callbacks: List[Callable[[ProgressMetrics], None]] = []

    def add_callback(self, callback: Callable[[ProgressMetrics], None]):
        self._callbacks.append(callback)

    def update_metrics(self, **kwargs):
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._metrics, key):
                    setattr(self._metrics, key, value)
            self.visualizer.update(metrics=self._metrics)

    def start(self):
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _monitor_loop(self):
        last_gen = -1

        while self._running:
            with self._lock:
                current_gen = self._metrics.generation
                if current_gen != last_gen:
                    last_gen = current_gen
                    self._render()
                    for callback in self._callbacks:
                        callback(self._metrics)

            time.sleep(self.update_interval)

    def _render(self):
        if HAS_RICH:
            pass
        else:
            print("\033[H\033[J", end="")
            print(self.visualizer.render())


class DebugVisualizer:
    def __init__(self, width: int = 80):
        self.width = width
        self._breakpoints: Dict[int, bool] = {}
        self._watchpoints: Dict[str, Any] = {}
        self._call_stack: List[Dict[str, Any]] = []
        self._registers: Dict[int, int] = {i: 0 for i in range(20)}
        self._memory_view: Dict[int, int] = {}
        self._current_ip: int = 0

    def set_breakpoint(self, line: int):
        self._breakpoints[line] = True

    def remove_breakpoint(self, line: int):
        self._breakpoints.pop(line, None)

    def set_watchpoint(self, variable: str, value: Any = None):
        self._watchpoints[variable] = value

    def update_registers(self, registers: Dict[int, int]):
        self._registers.update(registers)

    def update_memory(self, address: int, value: int):
        self._memory_view[address] = value

    def update_call_stack(self, stack: List[Dict[str, Any]]):
        self._call_stack = stack

    def set_instruction_pointer(self, ip: int):
        self._current_ip = ip

    def render(self) -> str:
        lines = []
        w = self.width

        lines.append("┌" + "─" * (w - 2) + "┐")
        lines.append(f"│ {'🐛 易衍调试器':{w-4}} │")
        lines.append("├" + "─" * (w - 2) + "┤")

        lines.append(f"│ 指令指针: IP={self._current_ip:5d} {'':{w-25}} │")

        lines.append("├" + "─" * (w - 2) + "┤")
        lines.append(f"│ {'寄存器 (Registers)':{w-4}} │")

        reg_line = ""
        for i in range(20):
            val = self._registers.get(i, 0)
            reg_line += f"R{i:02d}={val:8x} "
            if (i + 1) % 5 == 0:
                lines.append(f"│ {reg_line.strip():{w-4}} │")
                reg_line = ""

        lines.append("├" + "─" * (w - 2) + "┤")
        lines.append(f"│ {'调用栈 (Call Stack)':{w-4}} │")

        if self._call_stack:
            for frame in reversed(self._call_stack):
                frame_str = f"{frame.get('name', 'unknown')} @ {frame.get('ip', 0)}"
                lines.append(f"│   {frame_str:{w-6}} │")
        else:
            lines.append(f"│   (空){'':{w-8}} │")

        if self._watchpoints:
            lines.append("├" + "─" * (w - 2) + "┤")
            lines.append(f"│ {'观察点 (Watchpoints)':{w-4}} │")
            for var, val in self._watchpoints.items():
                lines.append(f"│   {var} = {val}{'':{w-8-len(str(var))-len(str(val))}} │")

        if self._breakpoints:
            lines.append("├" + "─" * (w - 2) + "┤")
            lines.append(f"│ {'断点 (Breakpoints)':{w-4}} │")
            bp_str = ", ".join(str(bp) for bp in sorted(self._breakpoints.keys()))
            lines.append(f"│   {bp_str:{w-6}} │")

        lines.append("└" + "─" * (w - 2) + "┘")

        return "\n".join(lines)


class StatusBar:
    def __init__(self, width: int = 80):
        self.width = width
        self._segments: List[Tuple[str, str, str]] = []

    def add_segment(self, key: str, label: str, value: str):
        for i, (k, _, _) in enumerate(self._segments):
            if k == key:
                self._segments[i] = (key, label, value)
                return
        self._segments.append((key, label, value))

    def remove_segment(self, key: str):
        self._segments = [(k, l, v) for k, l, v in self._segments if k != key]

    def render(self) -> str:
        parts = []
        remaining = self.width

        for key, label, value in self._segments:
            part = f"[{label}: {value}]"
            if len(parts) == 0:
                parts.append(part)
                remaining -= len(part)
            else:
                parts.append(part)
                remaining -= len(part) + 1

        if remaining > 0:
            parts.append(" " * remaining)

        return "".join(parts)


class InteractiveCodeEditor:
    def __init__(self):
        self._lines: List[str] = [""]
        self._cursor_line: int = 0
        self._cursor_col: int = 0
        self._modified: bool = False
        self._undo_stack: List[List[str]] = []
        self._redo_stack: List[List[str]] = []

    def load_content(self, content: str):
        self._save_state()
        self._lines = content.split("\n")
        if not self._lines:
            self._lines = [""]
        self._cursor_line = 0
        self._cursor_col = 0
        self._modified = False

    def get_content(self) -> str:
        return "\n".join(self._lines)

    def insert_char(self, char: str):
        if char == "\n":
            self._newline()
        elif char == "\t":
            self._tab()
        elif char == "\x7f":
            self._backspace()
        elif char == "\x08":
            self._backspace()
        else:
            self._save_state()
            line = self._lines[self._cursor_line]
            self._lines[self._cursor_line] = (
                line[: self._cursor_col] + char + line[self._cursor_col :]
            )
            self._cursor_col += 1
            self._modified = True

    def _newline(self):
        self._save_state()
        line = self._lines[self._cursor_line]
        before = line[: self._cursor_col]
        after = line[self._cursor_col :]

        self._lines[self._cursor_line] = before
        self._lines.insert(self._cursor_line + 1, after)
        self._cursor_line += 1
        self._cursor_col = 0
        self._modified = True

    def _tab(self):
        self._save_state()
        line = self._lines[self._cursor_line]
        self._lines[self._cursor_line] = (
            line[: self._cursor_col] + "    " + line[self._cursor_col :]
        )
        self._cursor_col += 4
        self._modified = True

    def _backspace(self):
        if self._cursor_col > 0:
            self._save_state()
            line = self._lines[self._cursor_line]
            self._lines[self._cursor_line] = (
                line[: self._cursor_col - 1] + line[self._cursor_col :]
            )
            self._cursor_col -= 1
            self._modified = True
        elif self._cursor_line > 0:
            self._save_state()
            prev_line = self._lines[self._cursor_line - 1]
            current_line = self._lines[self._cursor_line]
            self._lines[self._cursor_line - 1] = prev_line + current_line
            self._cursor_col = len(prev_line)
            self._lines.pop(self._cursor_line)
            self._cursor_line -= 1
            self._modified = True

    def move_cursor(self, dx: int = 0, dy: int = 0):
        new_line = max(0, min(self._cursor_line + dy, len(self._lines) - 1))
        max_col = len(self._lines[new_line])

        if dy != 0:
            self._cursor_col = min(self._cursor_col, max_col)
        else:
            self._cursor_col = max(0, min(self._cursor_col + dx, max_col))

        self._cursor_line = new_line

    def undo(self):
        if self._undo_stack:
            self._redo_stack.append(self._lines.copy())
            self._lines = self._undo_stack.pop()
            self._cursor_line = min(self._cursor_line, len(self._lines) - 1)
            self._cursor_col = min(self._cursor_col, len(self._lines[self._cursor_line]))

    def redo(self):
        if self._redo_stack:
            self._undo_stack.append(self._lines.copy())
            self._lines = self._redo_stack.pop()
            self._cursor_line = min(self._cursor_line, len(self._lines) - 1)
            self._cursor_col = min(self._cursor_col, len(self._lines[self._cursor_line]))

    def _save_state(self):
        self._undo_stack.append(self._lines.copy())
        if len(self._undo_stack) > 100:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def render(self, height: int = 20, width: int = 80) -> str:
        lines = []

        start_line = max(0, self._cursor_line - height // 2)
        end_line = min(start_line + height, len(self._lines))

        for i in range(start_line, end_line):
            line_num = i + 1
            line_content = self._lines[i]

            if i == self._cursor_line:
                cursor_indicator = "▶"
                col = self._cursor_col
                display_line = (
                    line_content[:col]
                    + "\033[7m"
                    + (line_content[col] if col < len(line_content) else " ")
                    + "\033[0m"
                    + line_content[col + 1 :]
                )
            else:
                cursor_indicator = " "
                display_line = line_content

            display_line = display_line.ljust(width - 6)[: width - 6]
            lines.append(f"{cursor_indicator} {line_num:3d} | {display_line}")

        if start_line > 0:
            lines.insert(0, f"  ... | {'(above)':{width-10}}")
        if end_line < len(self._lines):
            lines.append(f"  ... | {'(below)':{width-10}}")

        return "\n".join(lines)


def create_sparkline(data: List[float], width: int = 40) -> str:
    if not data:
        return ""

    bars = "▁▂▃▄▅▆▇█"
    data_min = min(data)
    data_max = max(data)

    if data_max == data_min:
        return bars[4] * min(len(data), width)

    normalized = [
        int(7 * (val - data_min) / (data_max - data_min)) for val in data[-width:]
    ]

    return "".join(bars[n] for n in normalized)


def render_memory_dump(
    memory: Dict[int, int],
    start: int = 0,
    count: int = 128,
    bytes_per_row: int = 16,
) -> str:
    lines = []

    for addr in range(start, start + count, bytes_per_row):
        hex_part = ""
        ascii_part = ""

        for offset in range(bytes_per_row):
            byte_val = memory.get(addr + offset, 0)
            hex_part += f"{byte_val:02x} "

            if 32 <= byte_val < 127:
                ascii_part += chr(byte_val)
            else:
                ascii_part += "."

        lines.append(f"{addr:08x}: {hex_part} {ascii_part}")

    return "\n".join(lines)
