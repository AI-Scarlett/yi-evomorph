# EVB v3 文件格式规范

**版本**: 3  
**状态**: 冻结 (Frozen)  
**日期**: 2026-05-07

> 本规范冻结 EVB v3 格式。任何新格式必须使用新版本号 (v4+)。
> 自举闭环依赖此格式的稳定性。

---

## 1. 概述

EVB (Evomorph Binary) 是 Evomorph 项目的编译输出格式和自举资产格式。
一个 `.evob` 文件由 **EVB Header** + **Locus Segments** 组成。

## 2. 文件结构

```text
┌─────────────────────────┐
│  Magic: "EVOB" (4 bytes)│
│  Version: uint16_be      │
│  HeaderSize: uint16_be   │
│  LocusCount: uint16_be   │
│  LocusOffsets[]: uint32_be│
│  [Metadata: optional]    │
├─────────────────────────┤
│  Locus Bytecode          │
│  ...                     │
└─────────────────────────┘
```

## 3. Header 格式

| 偏移 | 大小 | 字段 | 说明 |
|---:|---:|---|---|
| 0 | 4 | Magic | 固定 `EVOB` (0x45564F42) |
| 4 | 2 | Version | uint16_be, 当前 = 3 |
| 6 | 2 | HeaderSize | uint16_be, header 总字节数 (含 magic) |
| 8 | 2 | LocusCount | uint16_be, locus 数量 |
| 10 | 4×N | LocusOffsets | 每个 locus 在文件中的字节偏移, uint32_be |

HeaderSize 之后可能有可选的 metadata 段。

## 4. Locus Segment 格式 (Native Loader)

当使用 `evb_loader.py` 加载时，每个 Locus Segment 格式为：

| 偏移 | 大小 | 字段 | 说明 |
|---:|---:|---|---|
| 0 | 2 | NameLen | uint16_be, 名称 UTF-8 字节长度 |
| 2 | NameLen | Name | UTF-8 编码的 locus 名称 |
| 2+NL | 4 | MutRate | float32_be |
| 6+NL | 2 | PoolLen | uint16_be |
| 8+NL | PoolLen | CrossPool | UTF-8 编码 |
| 8+NL+PL | 4 | EntryPoint | uint32_be |
| 12+NL+PL | 4 | BytecodeLen | uint32_be |
| 16+NL+PL | BytecodeLen | Bytecode | 原始字节码 |

## 5. IChing 指令编码 (4 字节)

每条 IChing 指令占 4 字节：

```text
Byte 0: [opcode[5:0]][modifier_high[1:0]]
Byte 1: [modifier_low[3:0]][reserved]
Byte 2: operand_0
Byte 3: operand_1
```

- opcode: 6 位 (0-63)
- modifier: 6 位 (高 2 位在 byte0, 低 4 位在 byte1)
- operand: 8 位无符号

## 6. Native 指令编码

Native 指令有两种格式：

- **3 字节**: `[opcode][mod_rm][disp8]`
- **7 字节**: `[opcode][mod_rm][imm32]` (4 字节立即数, little-endian)

## 7. 验证

任何 `.evob` 文件必须满足：

1. 前 4 字节 = `EVOB`
2. Version = 3
3. HeaderSize >= 10
4. HeaderSize <= 文件大小
5. LocusCount * 4 + 10 <= HeaderSize
6. 所有 LocusOffset < 文件大小

## 8. Hash 约定

自举验证使用 SHA-256 对整个 `.evob` 文件计算 hash。
黄金样例 hash 存储在 `tests/evo/golden/*.sha256`。

## 9. 兼容性

- EVB v3 阅读器必须能忽略不认识的 header 扩展字段
- EVB v3 阅读器遇到 version > 3 的文件应拒绝加载
