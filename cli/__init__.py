# Evomorph CLI 工具集 (P5 分离, 不属于核心 TCB)
# 依赖于 evomorph 包, 但 evomorph 不依赖 cli/
from .evoshell import EvoShell
from .repl import EvoREPL

__all__ = ["EvoShell", "EvoREPL"]
