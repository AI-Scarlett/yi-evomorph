# P3: EVB VM 自举规格

**日期**: 2026-05-09
**状态**: 开发中 — Phase 1 核心指令解释器

---

## 架构概述

目标是创建一个**元循环解释器**（meta-circular interpreter）：用 EVB 汇编编写一个 VM，该 VM 在宿主 Python VM 中运行，能够解释执行任意 EVB 程序。

```
[宿主 Python VM] → 运行 [EVB VM (vm_core.evob)] → 解释 [guest program]
  registers[32]       guest 状态存在 heap 中        被解释的 EVB 程序
  heap[16MB]          解释循环占用 host regs
```

---

## Guest 内存布局

| 区域 | 偏移 | 大小 | 说明 |
|------|------|------|------|
| g_program | 0x30000 | 64KB | guest 程序字节码 |
| g_regs | 0x40000 | 128B | guest 寄存器文件 (32 × 4B) |
| g_stack | 0x40400 | 16KB | guest 调用栈 |
| g_flags | 0x44400 | 4B | guest 标志位 (zero, carry) |
| g_heap | 0x50000 | 512KB | guest 堆内存 |
| g_pc | 0x40080 | 4B | guest PC (存于 regs 区后) |

---

## 指令格式 (IChing)

```
byte1: 0x80 | (opcode & 0x3F)    ; bit7=1 表示 IChing 指令
byte2: (mode << 6) | sub_op      ; mode=1(无立即数), mode=2(有立即数)
byte3: dst_reg                    ; 目标寄存器号 (0-31)
byte4: src_reg                    ; 源寄存器号 (0-31)
如果 mode=2: imm[4 bytes LE]   ; 立即数
```

---

## Phase 1 实现指令集 (14 条核心指令)

| # | 操作码 | 助记符 | 语义 |
|---|--------|--------|------|
| 63 | CREA | 设置寄存器=立即数 | g_regs[dst] = imm |
| 61 | FELLOWSHIP | 寄存器复制 | g_regs[dst] = g_regs[src] |
| 49 | INCREASE | 加法 | g_regs[dst] += g_regs[src] |
| 35 | REDUCE | 减法 | g_regs[dst] -= g_regs[src]; 设 flags |
| 24 | GATHER | 加法(立即数) | g_regs[dst] += imm |
| 12 | MICRO | 自增 | g_regs[dst] += 1 |
| 2  | BRANCH.2 | 相等跳转 (JE) | if zero: g_pc = imm |
| 2  | BRANCH.3 | 不等跳转 (JNE) | if !zero: g_pc = imm |
| 2  | BRANCH.4 | 小于跳转 (JL) | if carry: g_pc = imm |
| 2  | BRANCH.7 | 大于等于跳转 (JGE) | if !carry: g_pc = imm |
| 56 | HALT | 停机 | 退出解释循环 |
| 47 | ABUNDANCE | 调用 (call) | push g_pc; g_pc = imm |
| 1  | RETURN | 返回 (ret) | pop g_pc |
| 17 | ALLOC | 内存写入 | g_heap[g_regs[dst]] = byte_val |

---

## 执行循环 (伪代码)

```
g_pc = 0
while True:
    byte1 = g_program[g_pc]
    opcode = byte1 & 0x3F
    
    byte2 = g_program[g_pc+1]
    mode = (byte2 >> 6) & 0x03
    sub_op = byte2 & 0x3F
    
    byte3 = g_program[g_pc+2]    ; dst_reg
    byte4 = g_program[g_pc+3]    ; src_reg
    
    instr_size = 4
    if mode == 2:
        imm = g_program[g_pc+4..g_pc+8]  ; 4 bytes LE
        instr_size = 8
    
    dispatch(opcode, sub_op, dst, src, imm, mode)
    g_pc += instr_size
```

---

## 测试计划

### 测试 1: 简单算术
```
CREA.1 R0, R0, #5       ; R0 = 5
CREA.1 R1, R1, #3       ; R1 = 3
INCREASE.0 R0, R1        ; R0 = R0 + R1 (= 8)
HALT
```
验证: R0 = 8

### 测试 2: 条件分支
```
CREA.1 R0, R0, #5
CREA.1 R1, R1, #5
REDUCE.0 R0, R1          ; R0 = 0, zero_flag = 1
BRANCH.2 @label          ; JE → 跳转到 label
CREA.1 R2, R2, #99       ; 不应执行
label:
HALT
```
验证: R2 未被设为 99

### 测试 3: 函数调用
```
CREA.1 R0, R0, #10
ABUNDANCE.1 R0, R0, @func  ; call func
HALT
func:
  INCREASE.0 R0, R0      ; R0 += R0 (= 20)
  RETURN.0 R0, R0
```
验证: R0 = 20
