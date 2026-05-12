"""
IChingVM2 C Bridge — 通过 ctypes 调用 C 共享库实现
替代 Python VM，消除 ~2600 行核心 VM 代码

C 运行时: evomorph/native/runtime/libichingvm2.dylib
头文件:   evomorph/native/runtime/ichingvm2.h
"""

import ctypes
import os
from ctypes import (
    c_uint8, c_uint32, c_uint64, c_int, c_double, c_char, c_void_p,
    POINTER, Structure, byref, cast, sizeof
)

_LIB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "evomorph", "native", "runtime", "libichingvm2.dylib"
)

# 回退路径: 构建产物可能在当前包目录下
if not os.path.exists(_LIB_PATH):
    _LIB_PATH = os.path.join(os.path.dirname(__file__), "..", "native", "runtime", "libichingvm2.dylib")
_lib = ctypes.CDLL(_LIB_PATH)

# === C 结构体定义 ===

NUM_REGS = 32
STACK_SIZE = 65536
HEAP_SIZE = 1048576
MAX_PROGRAM = 2097152
MAX_LABELS = 4096
MAX_CALLS = 4096
SP_REG = 29
FP_REG = 28
LR_REG = 30


class IChingVM2_C(Structure):
    """映射 ichingvm2.h 中的 IChingVM2 结构体"""
    _fields_ = [
        ("regs", c_uint32 * 32),
        ("heap", c_void_p),
        ("stack", c_void_p),
        ("program", c_void_p),
        ("program_size", c_uint32),
        ("pc", c_uint32),
        ("heap_ptr", c_uint32),
        ("state", c_int),
        ("cycle_count", c_uint64),
        ("energy_cost", c_double),
        ("flag_zero", c_int),
        ("flag_carry", c_int),
        ("flag_negative", c_int),
        ("flag_overflow", c_int),
        ("flag_direction", c_int),
        ("flag_interrupt", c_int),
        ("call_stack", c_uint32 * MAX_CALLS),
        ("call_stack_top", c_int),
        ("output_buffer", c_char * 65536),
        ("output_len", c_uint32),
    ]


# === C API 函数签名 ===

_lib.ichingvm2_create.restype = POINTER(IChingVM2_C)
_lib.ichingvm2_create.argtypes = []

_lib.ichingvm2_destroy.restype = None
_lib.ichingvm2_destroy.argtypes = [POINTER(IChingVM2_C)]

_lib.ichingvm2_reset.restype = None
_lib.ichingvm2_reset.argtypes = [POINTER(IChingVM2_C)]

_lib.ichingvm2_step.restype = c_int
_lib.ichingvm2_step.argtypes = [POINTER(IChingVM2_C)]

_lib.ichingvm2_run.restype = c_int
_lib.ichingvm2_run.argtypes = [POINTER(IChingVM2_C), c_uint64]

_lib.ichingvm2_load_program.restype = c_int
_lib.ichingvm2_load_program.argtypes = [
    POINTER(IChingVM2_C), POINTER(c_uint8), c_uint32
]

_lib.ichingvm2_load_evob.restype = c_int
_lib.ichingvm2_load_evob.argtypes = [
    POINTER(IChingVM2_C), POINTER(c_uint8), c_uint32
]

_lib.ichingvm2_load_string.restype = c_int
_lib.ichingvm2_load_string.argtypes = [
    POINTER(IChingVM2_C), c_uint32, ctypes.c_char_p
]

_lib.ichingvm2_read_string.restype = None
_lib.ichingvm2_read_string.argtypes = [
    POINTER(IChingVM2_C), c_uint32, ctypes.c_char_p, c_uint32
]

_lib.ichingvm2_assemble.restype = c_uint32
_lib.ichingvm2_assemble.argtypes = [
    POINTER(IChingVM2_C), ctypes.c_char_p
]

_lib.ichingvm2_load_assembled.restype = c_int
_lib.ichingvm2_load_assembled.argtypes = [
    POINTER(IChingVM2_C), ctypes.c_char_p
]

_lib.ichingvm2_register_syscall.restype = None
_lib.ichingvm2_register_syscall.argtypes = [
    POINTER(IChingVM2_C), c_int, c_void_p
]

_lib.ichingvm2_get_output.restype = ctypes.c_char_p
_lib.ichingvm2_get_output.argtypes = [POINTER(IChingVM2_C)]

_lib.ichingvm2_clear_output.restype = None
_lib.ichingvm2_clear_output.argtypes = [POINTER(IChingVM2_C)]

_lib.ichingvm2_load_word.restype = c_uint32
_lib.ichingvm2_load_word.argtypes = [POINTER(IChingVM2_C), c_uint32]

_lib.ichingvm2_store_word.restype = None
_lib.ichingvm2_store_word.argtypes = [POINTER(IChingVM2_C), c_uint32, c_uint32]


# === VM 状态常量 ===

VM_INIT = 0
VM_RUNNING = 1
VM_PAUSED = 2
VM_HALTED = 3
VM_ERROR = 4

STATE_NAMES = {
    VM_INIT: "INIT",
    VM_RUNNING: "RUNNING",
    VM_PAUSED: "PAUSED",
    VM_HALTED: "HALTED",
    VM_ERROR: "ERROR",
}


class CBridgeVM:
    """Pythonic 封装, 兼容 ExtendedIChingVM2 API"""

    def __init__(self):
        self._vm = _lib.ichingvm2_create()
        if not self._vm:
            raise RuntimeError("Failed to create IChingVM2 instance via C bridge")
        self.program = bytearray()
        self.state = VM_INIT
        self._callbacks = {}

    def __del__(self):
        if hasattr(self, "_vm") and self._vm:
            _lib.ichingvm2_destroy(self._vm)
            self._vm = None

    def reset(self):
        _lib.ichingvm2_reset(self._vm)
        self.program = bytearray()
        self.state = VM_INIT

    @property
    def registers(self):
        """返回 32 个寄存器的 list (兼容 Python VM .registers)"""
        return list(self._vm.contents.regs)

    @property
    def pc(self):
        return self._vm.contents.pc

    @pc.setter
    def pc(self, val):
        self._vm.contents.pc = val

    @property
    def cycle_count(self):
        return self._vm.contents.cycle_count

    @property
    def energy_cost(self):
        return self._vm.contents.energy_cost

    @property
    def flag_zero(self):
        return bool(self._vm.contents.flag_zero)

    @property
    def flag_carry(self):
        return bool(self._vm.contents.flag_carry)

    @property
    def flag_negative(self):
        return bool(self._vm.contents.flag_negative)

    @property
    def flag_overflow(self):
        return bool(self._vm.contents.flag_overflow)

    def load_program(self, data: bytes):
        """加载裸字节码"""
        buf = (c_uint8 * len(data))(*data)
        ret = _lib.ichingvm2_load_program(self._vm, buf, len(data))
        if ret != 0:
            raise RuntimeError(f"Failed to load program (code {ret})")
        self.program = bytearray(data)

    def load_evob(self, data: bytes):
        """加载 EVB v3 格式字节码 (带 header 自动剥离)"""
        buf = (c_uint8 * len(data))(*data)
        ret = _lib.ichingvm2_load_evob(self._vm, buf, len(data))
        if ret != 0:
            raise RuntimeError(f"Failed to load EVOB (code {ret})")
        sz = self._vm.contents.program_size
        self.program = bytearray(sz)

    def assemble(self, asm_source: str) -> bytes:
        """汇编 .evoasm 源码, 返回机器码"""
        src = asm_source.encode("utf-8") if isinstance(asm_source, str) else asm_source
        size = _lib.ichingvm2_assemble(self._vm, src)
        if size == 0:
            raise RuntimeError("Assembly failed")
        sz = self._vm.contents.program_size
        self.program = bytearray(sz)
        if self._vm.contents.program:
            buf = (c_uint8 * sz)()
            ctypes.memmove(buf, self._vm.contents.program, sz)
            return bytes(buf)
        return bytes(self.program)

    def load_assembled(self, asm_source: str) -> bytes:
        """汇编并加载到 VM"""
        src = asm_source.encode("utf-8") if isinstance(asm_source, str) else asm_source
        ret = _lib.ichingvm2_load_assembled(self._vm, src)
        if ret != 0:
            raise RuntimeError(f"Assembly failed (code {ret})")
        sz = self._vm.contents.program_size
        self.program = bytearray(sz)
        return bytes(self.program)

    def step(self) -> int:
        """单步执行, 返回 exit code"""
        return _lib.ichingvm2_step(self._vm)

    def run(self, max_cycles: int = 10000000) -> int:
        """运行直到 HALT/ERROR 或达到 max_cycles"""
        ret = _lib.ichingvm2_run(self._vm, max_cycles)
        self.state = self._vm.contents.state
        return ret

    def load_string(self, addr: int, s: str):
        """在 VM heap 的 addr 处写入字符串"""
        _lib.ichingvm2_load_string(self._vm, addr, s.encode("utf-8"))

    def read_string(self, addr: int, max_len: int = 4096) -> str:
        """从 VM heap 的 addr 处读取字符串"""
        buf = ctypes.create_string_buffer(max_len)
        _lib.ichingvm2_read_string(self._vm, addr, buf, max_len)
        return buf.value.decode("utf-8", errors="replace") if buf.value else ""

    def load_word(self, addr: int) -> int:
        return _lib.ichingvm2_load_word(self._vm, addr)

    def store_word(self, addr: int, val: int):
        _lib.ichingvm2_store_word(self._vm, addr, val)

    def get_output(self) -> str:
        out = _lib.ichingvm2_get_output(self._vm)
        return out.decode("utf-8", errors="replace") if out else ""

    def clear_output(self):
        _lib.ichingvm2_clear_output(self._vm)

    @property
    def state_name(self) -> str:
        return STATE_NAMES.get(self._vm.contents.state, "UNKNOWN")

    def is_halted(self) -> bool:
        return self._vm.contents.state == VM_HALTED

    def is_error(self) -> bool:
        return self._vm.contents.state == VM_ERROR

    # === 内存访问 (heap/stack 读写) ===

    def _heap_ptr(self):
        """获取 heap 的原始指针地址"""
        hp = self._vm.contents.heap
        if not hp:
            return 0
        # c_void_p 的 value 是整数地址
        if isinstance(hp, int):
            return hp
        return hp.value if hasattr(hp, 'value') else int(hp)

    def heap_read(self, addr: int, size: int) -> bytes:
        heap_addr = self._heap_ptr()
        if heap_addr == 0:
            return b""
        buf = (c_uint8 * size)()
        ctypes.memmove(buf, heap_addr + addr, size)
        return bytes(buf)

    def heap_write(self, addr: int, data: bytes):
        heap_addr = self._heap_ptr()
        if heap_addr == 0:
            return
        ctypes.memmove(heap_addr + addr, data, len(data))

    # === Syscall 扩展 ===

    def register_syscall(self, num: int, handler):
        """注册 Python 回调为 syscall handler
        注: C 侧使用函数指针, Python 回调需要 wrapper
        当前版本仅支持已内置的 syscall (0-9)
        """
        self._callbacks[num] = handler
        # TODO: 通过 ctypes CFUNCTYPE 桥接 Python 回调到 C

    # === 便捷方法 (兼容 Python VM) ===

    def load_and_run_evob(self, evob_data: bytes, max_cycles: int = 10000000):
        """一步加载并运行 EVOB"""
        self.reset()
        self.load_evob(evob_data)
        return self.run(max_cycles)

    def assemble_and_run(self, asm_source: str, max_cycles: int = 10000000):
        """一步汇编并运行"""
        self.reset()
        self.load_assembled(asm_source)
        return self.run(max_cycles)


# === 全局工厂 ===

def create_c_vm() -> CBridgeVM:
    return CBridgeVM()


def c_vm_available() -> bool:
    """检查 C VM 共享库是否可用"""
    return os.path.exists(_LIB_PATH)
