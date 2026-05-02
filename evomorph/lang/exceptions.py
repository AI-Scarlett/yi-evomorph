import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set, Any, Callable, TypeVar, Generic
from collections import defaultdict


T = TypeVar('T')


class ErrorSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


class ErrorCategory(Enum):
    SYNTAX = "syntax"
    TYPE = "type"
    SEMANTIC = "semantic"
    RUNTIME = "runtime"
    COMPILER = "compiler"
    LINKER = "linker"
    IO = "io"
    MEMORY = "memory"
    THREAD = "thread"
    EVOLUTION = "evolution"


@dataclass
class SourceLocation:
    file_path: str = ""
    line: int = 0
    column: int = 0
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }


@dataclass
class EvomorphError:
    code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    location: Optional[SourceLocation] = None
    cause: Optional['EvomorphError'] = None
    related_errors: List['EvomorphError'] = field(default_factory=list)
    suggested_fixes: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "code": self.code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "location": self.location.to_dict() if self.location else None,
            "suggested_fixes": list(self.suggested_fixes),
            "context": copy.deepcopy(self.context),
            "related_errors": [e.to_dict() for e in self.related_errors],
        }
        
        if self.cause:
            result["cause"] = self.cause.to_dict()
        
        return result
    
    def format(self, with_color: bool = True) -> str:
        lines = []
        
        if with_color:
            severity_colors = {
                ErrorSeverity.INFO: "\033[94m",
                ErrorSeverity.WARNING: "\033[93m",
                ErrorSeverity.ERROR: "\033[91m",
                ErrorSeverity.CRITICAL: "\033[95m",
                ErrorSeverity.FATAL: "\033[41m\033[97m",
            }
            reset = "\033[0m"
            color = severity_colors.get(self.severity, "")
        else:
            color = ""
            reset = ""
        
        lines.append(f"{color}{self.severity.value.upper()}{reset}: {self.code}")
        
        if self.location:
            lines.append(f"  在 {self.location.file_path}:{self.location.line}:{self.location.column}")
        
        lines.append(f"  {self.message}")
        
        if self.suggested_fixes:
            lines.append("  建议修复:")
            for fix in self.suggested_fixes:
                lines.append(f"    • {fix}")
        
        if self.cause:
            lines.append("  原因:")
            cause_lines = self.cause.format(with_color).split("\n")
            for line in cause_lines:
                lines.append(f"    {line}")
        
        return "\n".join(lines)


@dataclass
class ExceptionFrame:
    function_name: str = ""
    file_path: str = ""
    line: int = 0
    instruction_address: int = 0
    local_variables: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_name": self.function_name,
            "file_path": self.file_path,
            "line": self.line,
            "instruction_address": self.instruction_address,
            "local_variables": copy.deepcopy(self.local_variables),
        }


class EvomorphException(Exception):
    def __init__(self, 
                 error: EvomorphError,
                 stack_trace: Optional[List[ExceptionFrame]] = None):
        self.error = error
        self.stack_trace = stack_trace or []
        super().__init__(error.message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.error.to_dict(),
            "stack_trace": [f.to_dict() for f in self.stack_trace],
        }
    
    def format_stack_trace(self, with_color: bool = True) -> str:
        if not self.stack_trace:
            return "无堆栈追踪"
        
        lines = ["堆栈追踪:"]
        for i, frame in enumerate(reversed(self.stack_trace)):
            lines.append(f"  #{len(self.stack_trace) - 1 - i} {frame.function_name}")
            lines.append(f"     at {frame.file_path}:{frame.line}")
            lines.append(f"     指令地址: 0x{frame.instruction_address:X}")
        
        return "\n".join(lines)


class ErrorCodeRegistry:
    _codes: Dict[str, Tuple[ErrorCategory, ErrorSeverity, str]] = {}
    
    @classmethod
    def register(cls, code: str, category: ErrorCategory, severity: ErrorSeverity, 
                 default_message: str):
        cls._codes[code] = (category, severity, default_message)
    
    @classmethod
    def get(cls, code: str) -> Optional[Tuple[ErrorCategory, ErrorSeverity, str]]:
        return cls._codes.get(code)
    
    @classmethod
    def create_error(cls, code: str, 
                     message: Optional[str] = None,
                     location: Optional[SourceLocation] = None,
                     **kwargs) -> EvomorphError:
        info = cls.get(code)
        if info is None:
            return EvomorphError(
                code=code,
                message=message or f"未知错误代码: {code}",
                category=ErrorCategory.COMPILER,
                severity=ErrorSeverity.ERROR,
                location=location,
                **kwargs
            )
        
        category, severity, default_msg = info
        return EvomorphError(
            code=code,
            message=message or default_msg,
            category=category,
            severity=severity,
            location=location,
            **kwargs
        )


ErrorCodeRegistry.register(
    "E0001", ErrorCategory.SYNTAX, ErrorSeverity.ERROR,
    "语法错误"
)
ErrorCodeRegistry.register(
    "E0002", ErrorCategory.TYPE, ErrorSeverity.ERROR,
    "类型不匹配"
)
ErrorCodeRegistry.register(
    "E0003", ErrorCategory.SEMANTIC, ErrorSeverity.ERROR,
    "未定义的符号"
)
ErrorCodeRegistry.register(
    "E0004", ErrorCategory.RUNTIME, ErrorSeverity.ERROR,
    "除零错误"
)
ErrorCodeRegistry.register(
    "E0005", ErrorCategory.MEMORY, ErrorSeverity.CRITICAL,
    "内存越界访问"
)
ErrorCodeRegistry.register(
    "E0006", ErrorCategory.RUNTIME, ErrorSeverity.ERROR,
    "空指针引用"
)
ErrorCodeRegistry.register(
    "E0007", ErrorCategory.THREAD, ErrorSeverity.CRITICAL,
    "检测到死锁"
)
ErrorCodeRegistry.register(
    "E0008", ErrorCategory.IO, ErrorSeverity.ERROR,
    "IO操作失败"
)
ErrorCodeRegistry.register(
    "E0009", ErrorCategory.LINKER, ErrorSeverity.ERROR,
    "未解析的符号引用"
)
ErrorCodeRegistry.register(
    "E0010", ErrorCategory.COMPILER, ErrorSeverity.FATAL,
    "编译器内部错误"
)


ErrorCodeRegistry.register(
    "W0001", ErrorCategory.TYPE, ErrorSeverity.WARNING,
    "隐式类型转换可能导致精度损失"
)
ErrorCodeRegistry.register(
    "W0002", ErrorCategory.SEMANTIC, ErrorSeverity.WARNING,
    "未使用的变量"
)
ErrorCodeRegistry.register(
    "W0003", ErrorCategory.EVOLUTION, ErrorSeverity.WARNING,
    "变异可能导致程序语义改变"
)
ErrorCodeRegistry.register(
    "W0004", ErrorCategory.RUNTIME, ErrorSeverity.WARNING,
    "可能的空指针引用"
)


class ExceptionHandler:
    def __init__(self):
        self.exception_stack: List[EvomorphException] = []
        self.handlers: Dict[ErrorCategory, List[Callable]] = defaultdict(list)
        self.global_handlers: List[Callable] = []
    
    def register_handler(self, handler: Callable, 
                         category: Optional[ErrorCategory] = None):
        if category:
            self.handlers[category].append(handler)
        else:
            self.global_handlers.append(handler)
    
    def raise_exception(self, error: EvomorphError, 
                        stack_trace: Optional[List[ExceptionFrame]] = None):
        exception = EvomorphException(error, stack_trace)
        self.exception_stack.append(exception)
        self._dispatch(exception)
        raise exception
    
    def _dispatch(self, exception: EvomorphException):
        for handler in self.handlers[exception.error.category]:
            try:
                handler(exception)
            except Exception:
                pass
        
        for handler in self.global_handlers:
            try:
                handler(exception)
            except Exception:
                pass
    
    def get_last_exception(self) -> Optional[EvomorphException]:
        return self.exception_stack[-1] if self.exception_stack else None
    
    def clear(self):
        self.exception_stack.clear()


class TryCatchScope:
    def __init__(self, 
                 catch_types: Optional[List[ErrorCategory]] = None,
                 handler: Optional[Callable] = None):
        self.catch_types = catch_types or []
        self.handler = handler
        self.entered_pc: int = 0
        self.exited_pc: int = 0
    
    def should_catch(self, exception: EvomorphException) -> bool:
        if not self.catch_types:
            return True
        return exception.error.category in self.catch_types


class VMExceptionManager:
    def __init__(self):
        self.exception_handler = ExceptionHandler()
        self.try_catch_stack: List[TryCatchScope] = []
        self.pending_exception: Optional[EvomorphException] = None
    
    def enter_try(self, scope: TryCatchScope, pc: int):
        scope.entered_pc = pc
        self.try_catch_stack.append(scope)
    
    def exit_try(self, pc: int):
        if self.try_catch_stack:
            scope = self.try_catch_stack.pop()
            scope.exited_pc = pc
    
    def throw_exception(self, error_code: str, message: Optional[str] = None,
                        pc: int = 0) -> Optional[TryCatchScope]:
        error = ErrorCodeRegistry.create_error(error_code, message)
        
        stack_trace = [
            ExceptionFrame(
                function_name="<unknown>",
                instruction_address=pc,
                line=pc
            )
        ]
        
        exception = EvomorphException(error, stack_trace)
        self.pending_exception = exception
        
        for scope in reversed(self.try_catch_stack):
            if scope.should_catch(exception):
                return scope
        
        return None
    
    def has_pending_exception(self) -> bool:
        return self.pending_exception is not None
    
    def get_pending_exception(self) -> Optional[EvomorphException]:
        return self.pending_exception
    
    def clear_pending(self):
        self.pending_exception = None
    
    def catch_and_handle(self, scope: TryCatchScope) -> bool:
        if not self.pending_exception:
            return False
        
        if scope.handler:
            try:
                scope.handler(self.pending_exception)
                self.clear_pending()
                return True
            except Exception:
                pass
        
        return False


class Signal(Enum):
    SIGINT = "SIGINT"
    SIGTERM = "SIGTERM"
    SIGFPE = "SIGFPE"
    SIGSEGV = "SIGSEGV"
    SIGILL = "SIGILL"
    SIGBUS = "SIGBUS"
    SIGTRAP = "SIGTRAP"


class SignalHandler:
    def __init__(self):
        self.handlers: Dict[Signal, List[Callable]] = defaultdict(list)
        self.default_handlers: Dict[Signal, Callable] = {}
        self._setup_defaults()
    
    def _setup_defaults(self):
        self.default_handlers[Signal.SIGFPE] = self._handle_sigfpe
        self.default_handlers[Signal.SIGSEGV] = self._handle_sigsegv
        self.default_handlers[Signal.SIGILL] = self._handle_sigill
    
    def register_handler(self, signal: Signal, handler: Callable):
        self.handlers[signal].append(handler)
    
    def raise_signal(self, signal: Signal, 
                      context: Optional[Dict[str, Any]] = None):
        for handler in self.handlers[signal]:
            try:
                handler(signal, context or {})
            except Exception:
                pass
        
        if signal in self.default_handlers:
            try:
                self.default_handlers[signal](signal, context or {})
            except Exception:
                pass
    
    def _handle_sigfpe(self, signal: Signal, context: Dict[str, Any]):
        pc = context.get('pc', 0)
        raise EvomorphException(
            ErrorCodeRegistry.create_error("E0004", f"在地址 0x{pc:X} 发生浮点异常")
        )
    
    def _handle_sigsegv(self, signal: Signal, context: Dict[str, Any]):
        pc = context.get('pc', 0)
        addr = context.get('address', 0)
        raise EvomorphException(
            ErrorCodeRegistry.create_error(
                "E0005", 
                f"在地址 0x{pc:X} 访问非法内存地址 0x{addr:X}"
            )
        )
    
    def _handle_sigill(self, signal: Signal, context: Dict[str, Any]):
        pc = context.get('pc', 0)
        opcode = context.get('opcode', 0)
        raise EvomorphException(
            ErrorCodeRegistry.create_error(
                "E0001", 
                f"在地址 0x{pc:X} 发现非法指令 0x{opcode:02X}"
            )
        )
