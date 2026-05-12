"""Evomorph VM 包 — 支持 Python VM 和 C 原生 VM 双后端

通过环境变量 EVOMORPH_VM_BACKEND 选择:
  EVOMORPH_VM_BACKEND=c   → 使用 C 原生 VM (libichingvm2.dylib)
  EVOMORPH_VM_BACKEND=py  → 使用 Python VM (默认)
"""

from .virtual_machine import IChingVM, VMState

# 可选: C 原生 VM 桥接 (~10x 加速, 消除 ~2600 行 Python VM 代码)
try:
    from .cbridge import CBridgeVM, c_vm_available, create_c_vm
    _C_VM_AVAILABLE = c_vm_available()
except Exception:
    _C_VM_AVAILABLE = False
    CBridgeVM = None
    create_c_vm = None

__all__ = ["IChingVM", "VMState", "CBridgeVM", "create_c_vm", "c_vm_available"]
