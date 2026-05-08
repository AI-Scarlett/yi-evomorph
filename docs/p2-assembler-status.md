# P2 汇编器自举 — 诊断结果

**日期**: 2026-05-07  
**状态**: 暂停 — 核心 bug 已定位，待修复

## 已发现的问题

1. **add_label 函数对齐 bug (已修复)**
   - `al_pad_lp` 中 BRANCH.5 (JLE) 在 R7 < 12 时错误退出对齐循环
   - 修复: 改为 BRANCH.4 (JL) 继续填充直到 R7 >= 12

2. **lookup_opcode 步长不匹配**
   - 查找循环用 12 字节步长，但 opcode 表是 14 字节/条目
   - 导致后续条目读取偏移错误

3. **pass2 strcmp 终止符问题**
   - 原 strcmp 只支持 `\0` 作终止符
   - pass2 中 label 引用 `@target` 后跟 `\n`，查找失败
   - 需要 strcmp 兼容 `\n` 作为终止符

## 下一步

需要重新设计/重写 assembler.evob，这属于深层重构，不适合在当前会话中完成。
当前: 继续使用 Python assembler 作为 Stage-0 构建工具。
