# 易衍·Evomorph 完全自举计划

## 版本：1.0
## 日期：2026-05-04

---

## 概述

本计划描述了如何将 Evomorph 编程语言实现为完全自举的系统。
最终目标：**Evomorph 可以编写任何程序并运行**。

---

## 阶段 0：整理和标准化当前状态 ✅ 进行中

### 目标
- 确定虚拟机实际支持的指令集
- 创建标准助记符表
- 验证所有基础指令

### 已完成
- [x] 分析虚拟机指令集 (64 条指令)
- [x] 创建标准助记符表 (`std/instructions.evoasm`)
- [x] 验证核心指令：
  - `ABOUND` - 立即数加载
  - `FELLOWSHIP` - 寄存器复制
  - `INCREASE` - 加法
  - `REDUCE` - 减法
  - `DISPERSE` - 内存存储
  - `PENETRATE` - 内存加载
  - `ALLOC` - 内存分配
  - `HALT` - 停止
  - `RECV` - 系统调用

### 位运算指令映射
| 常见名称 | 实际助记符 | 功能 | 状态 |
|---------|-----------|------|------|
| `AND` | `APPROACH` | 按位与 | ✅ 可用 |
| `OR` | `MERGE` | 按位或 | ✅ 可用 |
| `XOR` | `ADORN` | 按位异或 | ✅ 可用 |
| `SHL` | `PREFETCH` | 左移 | ✅ 可用 |
| `SHR` | `FLUSH` | 右移 | ✅ 可用 |
| `NOT` | `OBSCURE` | 按位取反 | ✅ 可用 |

### 比较操作
| 常见名称 | 实际实现方式 | 说明 |
|---------|-------------|------|
| `CMP Rx, Ry` | `REDUCE Rx, Ry` | 设置标志位 (zero, negative) |
| `JE` / `JZ` | `BRANCH R0, target` | R0=0 时跳转 |
| `JNE` / `JNZ` | `APPROACH Rx, Rx` + `BRANCH Rx, target` | Rx != 0 时跳转 |

### 注意事项
1. **立即数限制**：`ABOUND Rx, N` 中 N 必须 >= 16
   - 0-15 需要通过计算获得：`ABOUND R1, 16; ABOUND R2, 16-K; REDUCE R1, R2`
   
2. **没有 `CMP` 指令**：需要用 `REDUCE` 模拟
   - 注意：`REDUCE` 会修改目标寄存器

3. **跳转目标限制**：`BRANCH` 的目标地址是 8 位 (0-255)
   - 长跳转需要额外处理

---

## 阶段 1：基础组件 - 字符串和数字处理库

### 目标
创建用 EvoASM 编写的标准库函数，供汇编器使用。

### 任务清单

#### 1.1 字符串操作
- [ ] `strlen` - 计算字符串长度
- [ ] `strcmp` - 比较字符串
- [ ] `strcpy` - 复制字符串
- [ ] `strcat` - 连接字符串
- [ ] `strchr` - 查找字符
- [ ] `toupper` - 字符转大写
- [ ] `tolower` - 字符转小写
- [ ] `isspace` - 判断空白字符
- [ ] `isdigit` - 判断数字
- [ ] `isalpha` - 判断字母
- [ ] `isalnum` - 判断字母数字

#### 1.2 数字操作
- [ ] `atoi` - 字符串转整数
- [ ] `itoa` - 整数转字符串
- [ ] `hextoi` - 十六进制转整数
- [ ] `bintoi` - 二进制转整数

#### 1.3 内存操作
- [ ] `memcpy` - 内存复制
- [ ] `memset` - 内存填充
- [ ] `memcmp` - 内存比较

### 关键技术挑战

**挑战 1：小立即数加载**
```
; 加载 0 到 R1
ABOUND R1, 16
ABOUND R2, 16
REDUCE R1, R2    ; R1 = 0

; 加载 1 到 R1
ABOUND R1, 16
ABOUND R2, 15
REDUCE R1, R2    ; R1 = 1
```

**挑战 2：比较操作**
```
; 比较 Rx 和 Ry
; 注意：这会修改 Rx
FELLOWSHIP Rtmp, Rx   ; 保存 Rx
REDUCE Rx, Ry         ; Rx = Rx - Ry，设置标志位
FELLOWSHIP Rx, Rtmp   ; 恢复 Rx
```

**挑战 3：循环控制**
```
; while (*ptr != 0) { ptr++; }
loop_start:
    PENETRATE Rptr, Rtmp    ; Rtmp = *Rptr
    ABOUND R1, 16
    ABOUND R2, 16
    REDUCE R1, R2           ; R1 = 0
    FELLOWSHIP R0, Rtmp
    REDUCE R0, R1            ; R0 = Rtmp - 0
    BRANCH R0, loop_continue ; 如果 R0 != 0，继续
    
    ; R0 == 0，退出
    BRANCH R0, loop_done
    
loop_continue:
    ; ptr++
    ABOUND R1, 16
    ABOUND R2, 15
    REDUCE R1, R2           ; R1 = 1
    INCREASE Rptr, R1
    
    BRANCH R0, loop_start
    
loop_done:
```

---

## 阶段 2：词法分析器（Token 化）

### 目标
用 EvoASM 编写词法分析器，将源代码转换为 Token 流。

### 功能要求
1. 跳过空白字符（空格、制表符、换行）
2. 识别助记符（指令名）
3. 识别寄存器（R0-R15）
4. 识别数字（十进制、十六进制、二进制）
5. 识别标识符（标签、宏名、常量名）
6. 识别标点符号（逗号、冒号）
7. 处理注释（`;` 开头）

### Token 类型定义
```
TOKEN_EOF        = 0
TOKEN_MNEMONIC   = 1
TOKEN_REGISTER   = 2
TOKEN_NUMBER     = 3
TOKEN_IDENTIFIER = 4
TOKEN_LABEL      = 5
TOKEN_COMMA      = 6
TOKEN_COLON      = 7
TOKEN_COMMENT    = 8
TOKEN_ERROR      = 9
TOKEN_MODIFIER   = 10
TOKEN_EQU        = 11
TOKEN_MACRO      = 12
```

### 实现步骤

#### 2.1 字符分类函数
- [ ] 实现 `isspace` 检测
- [ ] 实现 `isdigit` 检测
- [ ] 实现 `isalpha` 检测
- [ ] 实现 `isalnum` 检测

#### 2.2 核心循环
```
while (not EOF):
    跳过空白
    读取下一个字符
    根据字符类型决定处理方式:
        ';' → 跳过注释
        ',' → 返回 TOKEN_COMMA
        ':' → 返回 TOKEN_COLON
        数字 → 解析数字
        字母 → 解析标识符/助记符/寄存器
        其他 → 错误
```

#### 2.3 标识符解析
1. 收集所有连续的字母数字下划线
2. 判断类型：
   - 以 `R` 开头且后续是数字 → 寄存器
   - 下一个字符是 `:` → 标签
   - 在助记符表中 → 助记符
   - 其他 → 标识符

---

## 阶段 3：指令编码器（生成字节码）

### 目标
将解析后的指令转换为 4 字节机器码。

### 指令编码格式
```
byte1 = ((opcode & 0x3F) << 2) | ((modifier >> 4) & 0x03)
byte2 = modifier & 0x0F
byte3 = operand1 (寄存器或立即数)
byte4 = operand2 (寄存器或立即数)
```

### 任务清单

#### 3.1 助记符表
- [ ] 构建 64 条指令的助记符到操作码映射
- [ ] 每条指令的操作数数量（0, 1, 2）

#### 3.2 操作数解析
- [ ] 寄存器解析：`R0-R15` → 0-15
- [ ] 十进制数字解析
- [ ] 十六进制数字解析（`0x` 前缀）
- [ ] 二进制数字解析（`0b` 前缀）
- [ ] 标签引用（待重定位）
- [ ] 常量引用

#### 3.3 编码函数
- [ ] `encode_instruction(mnemonic, op1, op2, modifier)` → 4 字节
- [ ] 处理修饰符（`.ASYNC`, `.ATOMIC`, 等）

---

## 阶段 4：完整汇编器（两遍扫描）

### 目标
实现完整的汇编器，支持：
- 第一遍：收集标签地址
- 第二遍：生成代码并解析标签引用

### 功能要求

#### 4.1 常量定义
```
NAME EQU value
```

#### 4.2 标签
```
label:         ; 标签定义
BRANCH R0, label  ; 标签引用
```

#### 4.3 宏（可选，先实现基础功能）
```
%macro name n
    ; 宏体
%endmacro
```

### 两遍扫描流程

#### 第一遍
1. 逐行解析
2. 收集标签定义及其地址
3. 不生成代码，只计算指令地址

#### 第二遍
1. 逐行解析
2. 编码指令
3. 解析标签引用（使用第一遍收集的标签地址）
4. 输出机器码

---

## 阶段 5：自举验证

### 目标
验证汇编器可以编译自身。

### 验证步骤

#### 5.1 准备工作
- [ ] 用 Python 汇编器 (`evoasm_assembler.py`) 编译 EvoASM 版本的汇编器
- [ ] 得到 `assembler.raw`

#### 5.2 第一轮编译
- [ ] 在虚拟机上运行 `assembler.raw`
- [ ] 让它编译自身的源代码 `assembler.evoasm`
- [ ] 得到 `assembler_v2.raw`

#### 5.3 第二轮编译
- [ ] 在虚拟机上运行 `assembler_v2.raw`
- [ ] 让它编译 `assembler.evoasm`
- [ ] 得到 `assembler_v3.raw`

#### 5.4 验证
- [ ] 比较 `assembler_v2.raw` 和 `assembler_v3.raw`
- [ ] 如果完全相同，自举成功！

---

## 阶段 6：IDE 开发基础设施

### 目标
为 IDE 开发准备必要的组件。

### 功能要求

#### 6.1 输入/输出系统
- [ ] 键盘输入
- [ ] 鼠标输入
- [ ] 屏幕输出
- [ ] 文本渲染

#### 6.2 文件系统
- [ ] 列出目录
- [ ] 创建/删除文件
- [ ] 重命名文件
- [ ] 文件属性

#### 6.3 标准库扩展
- [ ] 动态内存管理
- [ ] 数据结构（链表、哈希表、数组）
- [ ] 字符串缓冲
- [ ] 格式化输出

#### 6.4 GUI 组件
- [ ] 窗口系统
- [ ] 控件（按钮、文本框、列表）
- [ ] 事件处理
- [ ] 渲染引擎

---

## 里程碑

### 里程碑 1：基础验证（当前）
- 截止日期：1 周内
- 目标：所有核心指令验证通过

### 里程碑 2：标准库
- 截止日期：2 周内
- 目标：字符串/数字/内存库完成并测试

### 里程碑 3：词法分析器
- 截止日期：3 周内
- 目标：可以将源代码转换为 Token 流

### 里程碑 4：指令编码器
- 截止日期：4 周内
- 目标：可以编码简单指令

### 里程碑 5：完整汇编器
- 截止日期：6 周内
- 目标：支持标签、常量、两遍扫描

### 里程碑 6：自举成功
- 截止日期：8 周内
- 目标：汇编器可以编译自身

### 里程碑 7：IDE 基础
- 截止日期：12 周内
- 目标：具备基本的 I/O 和文件系统能力

---

## 技术栈

### 阶段 0-5
- **虚拟机**: `ichingvm_bootstrap.c` (1500 行 C)
- **临时汇编器**: `evoasm_assembler.py` (Python)
- **目标汇编器**: 用 EvoASM 编写

### 阶段 6+
- 需要扩展虚拟机以支持 I/O
- 需要开发 GUI 层

---

## 风险和挑战

### 高风险
1. **小立即数限制**: 0-15 需要计算，代码冗长
2. **8 位跳转限制**: `BRANCH` 只能跳转到 0-255
3. **调试困难**: 没有调试器，只能通过打印调试

### 中风险
1. **标签重定位**: 需要正确处理
2. **性能**: 解释执行可能较慢
3. **内存限制**: 堆只有 1MB 左右

### 缓解措施
1. 创建宏库来简化小立即数加载
2. 实现长跳转（间接跳转）
3. 创建详细的测试套件

---

## 测试策略

### 单元测试
- 每个标准库函数都有测试
- 每条指令都有验证测试

### 集成测试
- 词法分析器测试
- 指令编码器测试
- 完整汇编器测试

### 自举测试
- 见阶段 5

---

## 目录结构建议

```
bootstrap/full/
├── std/                    # 标准库
│   ├── instructions.evoasm   # 指令定义
│   ├── string.evoasm         # 字符串操作
│   ├── number.evoasm         # 数字操作
│   └── memory.evoasm         # 内存操作
├── lib/                    # 库函数 (EvoASM 实现)
│   ├── string.evoasm
│   ├── number.evoasm
│   └── memory.evoasm
├── tests/                  # 测试
│   ├── test_string.evoasm
│   ├── test_number.evoasm
│   └── test_lexer.evoasm
├── lexer.evoasm            # 词法分析器
├── codegen.evoasm          # 指令编码器
├── assembler.evoasm        # 完整汇编器
└── BOOTSTRAP_PLAN.md       # 本文件
```

---

## 下一步行动

1. **立即开始**：阶段 1 - 标准库开发
   - 先实现字符串长度计算
   - 然后是字符串比较
   - 逐个实现并测试

2. **创建测试框架**：简单的测试宏，通过/失败打印

3. **迭代开发**：实现一个函数，测试一个函数，提交

---

## 附录

### 附录 A：核心指令速查表

| 助记符 | 操作码 | 功能 | 示例 |
|--------|--------|------|------|
| ABOUND | 13 | 立即数加载 | `ABOUND R0, 16` → R0 = 16 |
| FELLOWSHIP | 61 | 寄存器复制 | `FELLOWSHIP R1, R0` → R1 = R0 |
| INCREASE | 49 | 加法 | `INCREASE R0, R1` → R0 += R1 |
| REDUCE | 35 | 减法 | `REDUCE R0, R1` → R0 -= R1 |
| DISPERSE | 50 | 内存存储 | `DISPERSE R0, R1` → *R0 = R1 |
| PENETRATE | 54 | 内存加载 | `PENETRATE R0, R1` → R1 = *R0 |
| ALLOC | 17 | 内存分配 | `ALLOC R0, 0` → R0 = 256 字节地址 |
| HALT | 56 | 停止 | `HALT` |
| RECV | 0 | 系统调用 | `RECV R0, 0` (R0=调用号) |
| APPROACH | 3 | 按位与 | `APPROACH R0, R1` → R0 = R0 & R1 |
| MERGE | 16 | 按位或 | `MERGE R0, R1` → R0 = R0 \| R1 |
| ADORN | 37 | 按位异或 | `ADORN R0, R1` → R0 = R0 ^ R1 |
| PREFETCH | 55 | 左移 | `PREFETCH R0, R1` → R0 <<= R1 |
| FLUSH | 7 | 右移 | `FLUSH R0, R1` → R0 >>= R1 |
| OBSCURE | 5 | 按位取反 | `OBSCURE R0, R1` → R0 = ~R1 |
| BRANCH | 2 | 条件跳转 | `BRANCH R0, 8` → 如果 R0!=0 跳转到 8 |

### 附录 B：小立即数加载宏

```
%macro LOAD_0 1
    ABOUND R1, 16
    ABOUND R2, 16
    REDUCE R1, R2
    FELLOWSHIP %1, R1
%endmacro

%macro LOAD_1 1
    ABOUND R1, 16
    ABOUND R2, 15
    REDUCE R1, R2
    FELLOWSHIP %1, R1
%endmacro

%macro LOAD_N 2
    ; 加载 0-15
    ABOUND R1, 16
    ABOUND R2, 16-%2
    REDUCE R1, R2
    FELLOWSHIP %1, R1
%endmacro
```

### 附录 C：系统调用速查表

| 调用号 | 名称 | 参数 | 说明 |
|--------|------|------|------|
| 0 | OPEN | R1=文件名, R2=模式 | 打开文件 |
| 1 | READ | R1=fd, R2=buf, R3=count | 读取文件 |
| 2 | WRITE | R1=fd, R2=buf, R3=count | 写入文件 |
| 3 | CLOSE | R1=fd | 关闭文件 |
| 10 | MALLOC | R1=size | 分配内存 |
| 12 | MEMCPY | R1=dst, R2=src, R3=len | 内存复制 |
| 13 | MEMSET | R1=dst, R2=val, R3=len | 内存填充 |
| 20 | STRLEN | R1=str | 字符串长度 |
| 21 | STRCMP | R1=s1, R2=s2 | 字符串比较 |
| 30 | ISDIGIT | R1=char | 是否数字 |
| 31 | ISALPHA | R1=char | 是否字母 |
| 33 | ISSPACE | R1=char | 是否空白 |
| 40 | PRINT | R1=str | 打印字符串 |
| 255 | EXIT | - | 退出 |

---

## 更新日志

### 2026-05-04
- 创建初始版本计划
- 分析虚拟机指令集
- 确定阶段划分
