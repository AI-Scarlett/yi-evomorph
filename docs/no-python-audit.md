# Evomorph 依赖审计报告 (No-Python Audit)

> P0 阶段交付物 — 建立可量化的去依赖基线  
> 审计日期: 2026-05-07 | 分支: dev

---

## 1. 审计范围

本次审计覆盖 Evomorph 项目中所有非 Evomorph 语言的运行时/构建/测试依赖：

| 语言 | 涵盖内容 |
|------|----------|
| Python (`.py`) | VM、编译器桥接、CLI、LSP、MCP、测试、构建脚本 |
| JavaScript (`.js`) | IDE 扩展 |
| TOML/JSON (配置) | 包管理、entry_points、项目元数据 |

---

## 2. 总体统计

| 指标 | 数值 |
|------|------|
| 项目总 `.py` 文件数 | **112** |
| 项目根目录 `.py` 文件 | **39** (含调试脚本) |
| `evomorph/` 包内 `.py` 文件 | **73** |
| Python 运行时依赖 (pip) | **2** (prompt_toolkit, rich) |
| Python 标准库依赖 | os, sys, json, re, struct, hashlib, pathlib, subprocess |
| JavaScript 文件 | **1** (`tools/yistudio/extension.js`) |
| 构建系统依赖 | setuptools >= 61.0 |

---

## 3. Python 依赖详细分析

### 3.1 核心 TCB (Trusted Computing Base)

以下 Python 组件是 Evomorph 运行时的核心 TCB，必须在 VM 自举后才能替换：

| 文件 | 用途 | 行数 | 计划阶段 |
|------|------|------|----------|
| `evomorph/vm/extended_vm2.py` | 扩展 IChing VM (主运行时) | ~600 | P3: VM 自举 |
| `evomorph/vm/extended_vm.py` | 基础 IChing VM | ~400 | P3: VM 自举 |
| `evomorph/vm/virtual_machine.py` | VM 基类/VMState | ~300 | P3: VM 自举 |
| `evomorph/bootstrap/iching/iching_compiler.py` | IChing 编译器桥接 | ~1900 | P1/P2 |
| `evomorph/bootstrap/runtime/enhanced_runtime.py` | 增强运行时 (primitive 编译链) | ~800 | P1 |
| `evomorph/bootstrap/complete_bootstrap_runtime.py` | 完整自举运行时 | ~1300 | P1 |

### 3.2 编译器遗留 (Legacy)

保留用于测试/灾难恢复，不参与核心编译路径：

| 文件 | 用途 | 行数 |
|------|------|------|
| `evomorph/compiler/lexer.py` | 词法分析 | ~300 |
| `evomorph/compiler/parser.py` | 语法分析 | ~400 |
| `evomorph/compiler/codegen.py` | 代码生成 | ~400 |
| `evomorph/compiler/__init__.py` | EvocCompiler 类 | ~300 |

**主编译路径已不导入上述文件** (已验证: `evomorph/` 包内除 `tests/` 和 `evo_doctor.py` 外零直接导入)。

### 3.3 工具链/CLI/MCP (Python 实现)

| 文件 | 用途 | 计划阶段 |
|------|------|----------|
| `evomorph/cli/evo_ai.py` | AI CLI 入口 | P5: CLI 替换 |
| `evomorph/lsp/language_server.py` | LSP 服务端 | P7: MCP/LSP 隔离 |
| `evomorph/debug/dap_adapter.py` | DAP 调试适配器 | P7: 延后处理 |
| `evomorph/debugger/` | 调试器组件 | P7: 延后处理 |
| `ai/mcp/evomorph_mcp_server.py` | MCP 服务端 | P7: MCP 隔离 |

### 3.4 Native 工具链 (可被 Evomorph 替换)

| 文件 | 用途 | 计划阶段 |
|------|------|----------|
| `evomorph/native/loader/evb_loader.py` | EVB 文件加载器 | P4: runtime/stdlib |
| `evomorph/native/linker/linker.py` | EVB 链接器 | P4 |
| `evomorph/native/image/evo_image.py` | runtime image 打包 | P4 |
| `evomorph/native/bytecode_utils.py` | 字节码工具 | P4 |
| `evomorph/native/shell/evoshell.py` | 交互式 shell | P5 |
| `evomorph/native/repl/repl.py` | REPL | P5 |

### 3.5 构建脚本 (用于 stage0 构建)

| 文件 | 用途 | 保留策略 |
|------|------|----------|
| `build_assembler.py` | 汇编器构建入口 | 移入 legacy/stage0 |
| `build_evo_cli.py` | CLI 构建 | 移入 legacy/stage0 |
| `complete_bootstrap_runner.py` | 完整自举运行器 | 归档 |
| `continuous_bootstrap.py` | 持续自举验证 | 归档 |
| `auto_bootstrap_runner.py` | 自动自举运行器 | 归档 |
| `regression_test_suite.py` | 回归测试 | 移至 tests/ 或归档 |

### 3.6 调试/追踪脚本 (不进核心发布物)

根目录 39 个 `.py` 中有约 20 个调试/追踪脚本 (`debug_*.py`, `trace*.py`, `test_*.py`)，不进核心发布物。

---

## 4. Python 标准库依赖统计

在 `evomorph/` 包内的使用频率：

| 模块 | 使用文件数 | 是否可通过 syscall 替代 |
|------|------------|------------------------|
| `os` | 26 | 是 — io.evo + syscall |
| `json` | 18 | 是 — json.evo |
| `sys` | 17 | 是 — 进程参数 syscall |
| `re` | 8 | 是 — 已在编译器内部实现 |
| `struct` | 6 | 是 — EVB 原生支持 |
| `hashlib` | 3 | 是 — crypto.evo |
| `pathlib` | 2 | 是 — fs.evo |
| `subprocess` | 2 | 是 — syscall |

---

## 5. pip 运行时依赖

从 `pyproject.toml`:

| 包名 | 版本 | 用途 | 是否可替换 |
|------|------|------|-----------|
| `prompt_toolkit` | >=3.0 | 交互式 REPL 输入 | 是 — Evomorph TUI (远期) |
| `rich` | >=13.0 | 终端格式化输出 | 是 — 基本输出可替代 |
| `setuptools` | >=61.0 | 构建系统 | 是 — Makefile/纯 EVB 分发包 |

**Python 版本要求**: >= 3.9

---

## 6. JavaScript 依赖

| 文件 | 用途 | 策略 |
|------|------|------|
| `tools/yistudio/extension.js` | IDE 扩展 (YiStudio 适配) | 从核心仓库剥离为 optional adapter |

---

## 7. 关键依赖分类

### 核心必需 (TCB)

```
evomorph/vm/*.py              ← 运行 EVB 的宿主 VM (P3 前必须保留)
evomorph/bootstrap/runtime/   ← 自举运行时 (P2 后部分可移除)
evomorph/bootstrap/iching/    ← IChing 编译器桥接 (P3 后完全移除)
```

### 构建必需 (Stage-0)

```
build_assembler.py            ← 首次生成 assembler.evob
compiler.evoasm               ← EVB 快照不存在时的源输入
FULL_COMPILER_ASM (内联)      ← 最终的 Python 汇编回退
```

### 测试必需

```
tests/*.py                    ← Python pytest 测试套件
regression_test_suite.py
continuous_bootstrap.py
```

### IDE 可选

```
tools/yistudio/extension.js
evomorph/lsp/language_server.py
evomorph/debug/dap_adapter.py
```

---

## 8. 依赖缩减路线图

| 阶段 | 当前 Python TCB | 目标 Python TCB | 缩减量 |
|------|----------------|----------------|--------|
| **基线 (当前)** | 112 .py 文件 | — | — |
| **P1 完成** | ~100 .py (编译器路径已去 Python) | — | ~12 已移除 import |
| **P2 完成** | ~95 .py (汇编器自举) | — | ~5 |
| **P3 完成** | ~85 .py (VM 自举) | — | ~10 (Python VM 可移除) |
| **P4 完成** | ~70 .py (runtime/stdlib) | — | ~15 |
| **P5 完成** | ~50 .py (CLI/Tools) | — | ~20 |
| **P6 完成** | ~20 .py (native backend) | — | ~30 |
| **P7 完成** | ~10 .py (MCP/LSP/IDE) | 0 核心必需 | 隔离为 optional |
| **最终** | — | 0 (核心发布不含 .py) | — |

---

## 9. 结论

Evomorph 当前仍依赖 Python 作为运行时宿主，但核心编译路径已完全脱离 Python 编译器组件 (lexer/parser/codegen)。接下来的关键里程碑是:

1. **立即**: 移除 `load_assembled` 默认回退路径
2. **近期**: 实现 `assembler.evob` 自举 (P2)
3. **中期**: 实现 VM 自举 (P3)，将 Python 从运行时 TCB 中移除
4. **远期**: 实现 native 后端 (P6)，彻底消除解释器依赖
