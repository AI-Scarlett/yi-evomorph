# Evomorph 自举基线文档 (Bootstrap Baseline)

> P0 阶段交付物 — 固化当前可运行自举链路  
> 基线冻结日期: 2026-05-07 | EVB v3 格式

---

## 1. 基线概览

Evomorph 自举的核心理念是：编译器/汇编器/VM 最终全部用 Evomorph 语言自身实现，形成一个无外部语言依赖的独立生态。

当前基线状态：**编译器核心部分自举**（编译器逻辑以 EVB 字节码形式存在，由 Python VM 执行）。

---

## 2. 当前自举链路

### 2.1 编译器自举链路 (主路径)

```
.evo 源码
  ↓
EnhancedEvoRuntime.full_compile()
  ├── _prim_lexer_tokenize()    (Python runtime 调用 compiler.evob)
  ├── _prim_parser_parse_program()
  └── _prim_codegen_generate_evb()
  ↓
.evob 字节码
  ↓
ExtendedIChingVM2 (Python VM)
  ↓
执行输出
```

### 2.2 IChing 编译器路径 (iching_compiler.py)

```
.evo 源码
  ↓
IChingEvocCompiler.compile_source()
  ↓
ExtendedIChingVM2 + compiler.evob (优先)
  ↓
.evob 字节码
```

### 2.3 编译器快照生成链路 (Stage-0)

```
compiler.evoasm (汇编源码)
  ↓
Python assembler (build_assembler.py)  ← 仅 stage0
  ↓
compiler.evob (EVB 快照)
  ↓
ExtendedIChingVM2.run()
  ↓
编译输入 .evo
```

### 2.4 汇编器快照生成链路

```
asm_core.evoasm + asm_main.evoasm
  ↓
Python assembler (build_assembler.py)
  ↓
assembler.evob
```

---

## 3. 自举资产清单

| 文件 | 类型 | 路径 | SHA-256 |
|------|------|------|---------|
| `compiler.evob` | EVB 快照 | `evomorph/bootstrap/` | `e9cfa57a...` |
| `assembler.evob` | EVB 快照 | `evomorph/bootstrap/` | `0f03182a...` |
| `compiler.evoasm` | 汇编源码 | `evomorph/bootstrap/` | — |
| `asm_core.evoasm` | 汇编器核心 | `evomorph/bootstrap/` | — |
| `asm_main.evoasm` | 汇编器主逻辑 | `evomorph/bootstrap/` | — |
| `evoc/*.evo` | 编译器组件 | `evomorph/bootstrap/evoc/` | — |

---

## 4. 黄金测试样例

所有样例位于 `tests/evo/golden/`：

| 样例 | 源文件 | 预期 SHA-256 | 状态 |
|------|--------|-------------|------|
| Hello World | `hello.evo` | `hello.sha256` | ✅ |
| 数组求和 | `sum_all.evo` | `sum_all.sha256` | ✅ |
| 条件分支 | `branch.evo` | `branch.sha256` | ✅ |
| 函数调用 | `call_ret.evo` | `call_ret.sha256` | ✅ |
| 多 Locus | `multi_locus.evo` | `multi_locus.sha256` | ✅ |

### 黄金样例验证流程

```
python3 -m evomorph.tools.evo_doctor
```

检查项：
1. compiler.evob 存在且 hash 匹配
2. assembler.evob 存在且 hash 匹配
3. 主编译路径未误触 Python assembler
4. 5 个黄金样例编译通过
5. Python TCB 依赖数统计

---

## 5. EVB v3 文件格式 (已冻结)

详见 `docs/bootstrap-spec.md`，关键要素：

| 字段 | 偏移 | 大小 | 说明 |
|------|------|------|------|
| Magic | 0 | 4B | `EVOB` (0x45564F42) |
| Version | 4 | 2B | uint16_be, 当前=3 |
| Locus Count | 6 | 2B | uint16_be |
| Reserved | 8 | 4B | 保留，填充 0 |

### IChing 指令编码 (4 字节)

```
[opcode:6bit][sub_op:2bit][ext_mode:8bit][dst:4bit][src:4bit][imm:8bit]
```

### Native 指令编码 (3/7 字节)

```
[0x00][opcode:8bit][operand]        (3 字节)
[opcode:8bit][reg:4+4bit][imm:32bit] (7 字节)
```

---

## 6. 差异验证方法

### 6.1 EVB 字节级对比

```bash
python3 -c "
from evomorph.bootstrap.runtime.enhanced_runtime import EnhancedEvoRuntime
import hashlib
rt = EnhancedEvoRuntime()
source = open('examples/hello.evo').read()
result = rt.full_compile(source)
# compare with golden
"
```

### 6.2 编译器 hash 可复现性

```bash
# 用 compiler.evob 编译自身
python3 continuous_bootstrap.py --verify-hash
```

---

## 7. 自举阶段路线图

```text
当前基线 (2026-05-07)
  │
  ├── P0: 依赖审计 + 黄金样例 ✅ 完成
  ├── P1: 主编译链 EVB 化    ✅ 基本完成
  ├── P2: 汇编器自举         🔲 待完成
  ├── P3: VM 自举            🔲 待开始
  ├── P4: Runtime/Stdlib     🔲 待开始
  ├── P5: CLI 替换           🔲 待开始
  ├── P6: Native 后端        🔲 待开始
  └── P7: MCP/LSP 隔离       🔲 待开始
```

### 目标闭环

```
目标闭环一 (无 Python assembler):
  assembler.evob → compiler.evoasm → compiler.evob

目标闭环二 (无 Python VM):
  vm.evob → assembler.evob → compiler.evoasm → compiler.evob → compile vm.evo → new vm.evob

目标闭环三 (零宿主):
  evo native executable → compile/assemble/run/test → rebuild evo
```

---

## 8. 关键常量

```python
# 从 iching_compiler.py
INPUT_BUF       = 0x1000      # 输入缓冲区
TOKEN_BUF       = 0x9000      # Token 缓冲区
OUTPUT_BUF      = 0x11000     # 输出缓冲区
STRPOOL_BUF     = 0x2B000     # 字符串池
MNEMONIC_TABLE  = 0x33000     # 助记符表
NATIVE_TABLE    = 0x33700     # Native 指令表
HEADER_RESERVE  = 64          # EVB 头部保留
```

---

## 9. 运行命令速查

```bash
# 环境诊断
python3 -m evomorph.tools.evo_doctor

# 运行黄金测试
python3 tests/run_golden_tests.py

# 编译器自编译验证
python3 continuous_bootstrap.py

# 汇编器构建 (stage0)
python3 build_assembler.py

# 运行自举验证
python3 complete_bootstrap_runner.py
```
