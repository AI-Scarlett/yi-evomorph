# P2 汇编器自举 — 自举收敛 ✅

**日期**: 2026-05-09
**状态**: ✅ **完成** — assembler.evob 实现完全自举收敛

---

## 自举验证结果

```
v1 (Python-built): 3756 bytes
v2 (v1 self-assembled): 3756 bytes [MATCH] ✓
v3 (v2 self-assembled): 3756 bytes [MATCH] ✓
v4 (v3 self-assembled): 3756 bytes [MATCH] ✓

v1 == v2 → immediate convergence
v2 == v3 → CONVERGED
v3 == v4 → CONVERGED
```

---

## 已修复的所有 Bug

### 1. strcmp 缺少 `\n` 终止符 ✅
- **问题**: 原 strcmp 只支持 `\0` 作终止符
- **修复**: `sc_chk_term` 中增加对 R1 的 `\n` 终止符检查

### 2. lookup_opcode 步长不匹配 ✅
- **问题**: 查找循环用 12 字节步长，但 opcode 表是 14 字节/条目
- **修复**: 步长从 12 改为 14

### 3. lookup_label 步长不匹配 ✅
- **问题**: label 表步长不匹配（最终格式: 32 字节名称 + 4 字节地址 = 36 字节/条目）
- **修复**: 步长改为 36

### 4. add_label 填充和对齐 ✅
- **修复**: 改为 32 字节名称填充，写入 4 字节地址 (ALLOC.1)

### 5. add_label 终止符写入 ✅
- **修复**: `al_pd` 先将 R2 设为 0 再写入

### 6. 缩进注释行被误判为指令 ✅
- **问题**: `p1_loop` 只在行首检查 `;`，缩进的注释行首字符被当作指令编码
- **修复**: 在 `p1_label_scan`/`p2_scan` 中添加 `;` 检测和空白跳过逻辑 (`p1_skip_ws_chk`/`p2_skip_ws_chk`)

### 7. strcmp 缺少空格终止符 ✅ (关键修复)
- **问题**: 行中间的标签引用（如 `@pr_done      ; < '0'`）后跟空格，而标签表条目是 `\0` 终止。strcmp 只识别 `\0` 和 `\n` 终止符，导致比较 `pr_done ` vs `pr_done\0` 失败，11 个 BRANCH 目标变为 0xFFFFFFFF
- **修复**: `sc_lp` 中增加对空格 `#32` 的终止符检查

---

## 编译器验证

- compiler.evoasm: EVB 汇编器 vs Python 汇编器 → **逐字节匹配** (8012 bytes)

---

## 技术细节

### 标签表格式
- 条目大小: 36 字节 (32 名称 + 4 地址)
- 地址写入: ALLOC.1 (4 字节 LE word)
- 地址读取: RECV.1 (4 字节 LE word)

### strcmp 终止符
- `\0` (0x00) — 标准 C 字符串终止
- `\n` (0x0A) — 行尾标签引用
- ` ` (0x20) — 行中标签引用（后跟空格/注释）

### 当前大小
- assembler.evob: 3756 bytes
- compiler.evob: 8012 bytes
- 源码行数: 758 lines (asm_core.evoasm + asm_main.evoasm)
