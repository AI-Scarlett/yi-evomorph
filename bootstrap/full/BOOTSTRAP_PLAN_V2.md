# 易衍·Evomorph 完全自举计划

## 版本：2.0
## 日期：2026-05-04
## 状态：阶段 2 进行中

---

## 执行摘要

### 已完成 ✅

#### 阶段 0：整理和标准化当前状态

**Bug 修复：**
1. **虚拟机内存边界检查** - 程序加载地址从 `0x00110000` 改为 `0`
   - 原因：`BRANCH` 指令使用 8 位绝对地址，高地址无法正确跳转
   
2. **汇编器嵌套宏展开** - 添加 `expand_line_recursive` 方法支持递归展开
   - 之前：`PTR_INC` 只展开 `INCREASE`，不展开内部的 `LOAD_1`
   - 之后：完整递归展开所有嵌套宏

**创建的文件：**
- `std/instructions.evoasm` - 标准指令集定义
- `std/macros.evoasm` - 基础宏库（小立即数加载、指针操作等）
- `std/string.evoasm` - 字符串操作宏（STRLEN, STRCMP, STRCPY 等）
- `std/number.evoasm` - 数字操作宏
- `lib/test_lib.evoasm` - 完整测试程序

**验证通过的测试：**
- `test_ab.evoasm` - 输出 "AB" ✅
- `test_alloc_print.evoasm` - 输出 "ABC" ✅
- `test_lib.evoasm` - 输出 "Hello123\nHello123\nTests passed!\n" ✅

#### 阶段 1：基础组件 - 字符串和数字处理库

**利用虚拟机系统调用实现：**
- `SYS_STRLEN` (20) - 字符串长度
- `SYS_STRCMP` (21) - 字符串比较
- `SYS_STRCPY` (22) - 字符串复制
- `SYS_STRCAT` (23) - 字符串连接
- `SYS_MEMCPY` (12) - 内存复制
- `SYS_MEMSET` (13) - 内存填充
- `SYS_ISDIGIT` (30) - 是否数字
- `SYS_ISALPHA` (31) - 是否字母
- `SYS_ATOI` (36) - 字符串转整数
- `SYS_PRINT` (40) - 打印字符串

**创建的宏：**
- `STRLEN`, `STRCMP`, `STRCPY`, `STRCAT`
- `ISDIGIT`, `ISALPHA`, `ISALNUM`, `ISSPACE`
- `TOUPPER`, `TOLOWER`, `ATOI`
- `MEMCPY`, `MEMSET`, `MEMCMP`
- `PRINT`, `PRINTLN`, `EXIT`
- `MALLOC`, `ALLOC_256`

---

## 当前进度

### 阶段 2：词法分析器（Token 化）🔄 进行中

#### 目标
用 EvoASM 编写词法分析器，将源代码转换为 Token 流。

#### Python 参考实现（来自 `evoasm_assembler.py`）

```python
def tokenize(self, line: str) -> List[str]:
    tokens = []
    current = ""
    i = 0
    in_string = False
    string_char = None
    
    while i < len(line):
        c = line[i]
        
        if c == ';':
            if not in_string:
                break
        
        if in_string:
            if c == string_char:
                current += c
                tokens.append(current)
                current = ""
                in_string = False
            else:
                current += c
            i += 1
            continue
        
        if c in '"\'':
            if current:
                tokens.append(current)
                current = ""
            in_string = True
            string_char = c
            current += c
            i += 1
            continue
        
        if c.isspace():
            if current:
                tokens.append(current)
                current = ""
        elif c in ',:':
            if current:
                tokens.append(current)
                current = ""
            tokens.append(c)
        else:
            current += c
        i += 1
    
    if current:
        tokens.append(current)
    
    return tokens
```

#### Token 类型定义
```
TOKEN_EOF        = 0
TOKEN_MNEMONIC   = 1   ; CREA, RECV, ABOUND 等
TOKEN_REGISTER   = 2   ; R0-R15
TOKEN_NUMBER     = 3   ; 123, 0x1F, 0b1010
TOKEN_IDENTIFIER = 4   ; 标签名、宏名、常量名
TOKEN_COMMA      = 5   ; ,
TOKEN_COLON      = 6   ; :
TOKEN_MODIFIER   = 7   ; .ASYNC, .ATOMIC 等
TOKEN_EQU        = 8   ; EQU 关键字
TOKEN_MACRO      = 9   ; %macro, %endmacro
TOKEN_STRING     = 10  ; 字符串常量
```

#### 实现步骤（EvoASM）

##### 2.1 逐字符处理循环

**输入：** 字符串地址（每行源代码）
**输出：** Token 列表

```
; 伪代码
ptr = input_string
while *ptr != 0:
    c = *ptr
    
    if c == ';' and not in_string:
        break  ; 注释结束
    
    if in_string:
        if c == string_char:
            ; 字符串结束
            add_token(current_string)
            in_string = False
        else:
            append_to_current(c)
        ptr++
        continue
    
    if c == '"' or c == "'":
        ; 字符串开始
        if current_token:
            add_token(current_token)
        in_string = True
        string_char = c
        current_string = c
        ptr++
        continue
    
    if isspace(c):
        if current_token:
            add_token(current_token)
            current_token = ""
    elif c == ',' or c == ':':
        if current_token:
            add_token(current_token)
            current_token = ""
        add_token(c)
    else:
        append_to_current_token(c)
    
    ptr++

if current_token:
    add_token(current_token)
```

##### 2.2 字符分类函数（使用系统调用）

```
; 检查是否为空白字符
; 输入: R1 = 字符
; 输出: R0 = 1(是) 或 0(否)
isspace:
    ABOUND R0, SYS_ISSPACE
    RECV R0, 0
    RET

; 检查是否为数字字符
isdigit:
    ABOUND R0, SYS_ISDIGIT
    RECV R0, 0
    RET

; 检查是否为字母
isalpha:
    ABOUND R0, SYS_ISALPHA
    RECV R0, 0
    RET
```

##### 2.3 Token 存储结构

```
; 每个 Token 占用 8 字节
; +0: type (Token 类型)
; +4: value (数值或字符串指针)

TOKEN_TYPE_OFFSET   EQU 0
TOKEN_VALUE_OFFSET  EQU 4
TOKEN_SIZE          EQU 8

; Token 缓冲区
; 使用 ALLOC 分配，或者使用预定义的内存区域
```

---

## 阶段 3-6 计划（待实现）

### 阶段 3：指令编码器

将解析后的指令转换为 4 字节机器码。

**编码格式：**
```
byte1 = ((opcode & 0x3F) << 2) | ((modifier >> 4) & 0x03)
byte2 = modifier & 0x0F
byte3 = operand1 (寄存器或立即数)
byte4 = operand2 (寄存器或立即数)
```

**助记符表（64 条指令）：**
需要构建助记符字符串到操作码的映射。

### 阶段 4：完整汇编器（两遍扫描）

**第一遍：**
1. 逐行解析
2. 收集标签定义及其地址
3. 不生成代码，只计算指令地址

**第二遍：**
1. 逐行解析
2. 编码指令
3. 解析标签引用
4. 输出机器码

### 阶段 5：自举验证

1. 用 Python 汇编器编译 EvoASM 汇编器 → `assembler.raw`
2. 在虚拟机上运行 `assembler.raw`，让它编译自身源码 → `assembler_v2.raw`
3. 再运行 `assembler_v2.raw` 编译自身 → `assembler_v3.raw`
4. 比较 `assembler_v2.raw` 和 `assembler_v3.raw`，如果相同则自举成功

### 阶段 6：IDE 开发基础设施

- 输入/输出系统（键盘、鼠标、屏幕）
- 文件系统扩展
- 标准库扩展（数据结构、动态内存）
- GUI 组件（窗口、控件、事件处理）

---

## 技术限制和解决方案

### 限制 1：小立即数加载
**问题：** `ABOUND Rx, N` 只能直接加载 >= 16 的值

**解决方案：** 使用宏库
```
%macro LOAD_0 1
    ABOUND R1, 16
    ABOUND R2, 16
    REDUCE R1, R2
    FELLOWSHIP %1, R1
%endmacro
```

### 限制 2：8 位跳转限制
**问题：** `BRANCH` 目标地址只能是 0-255

**解决方案：**
1. 短程序可以正常工作
2. 长程序需要使用间接跳转或代码分段
3. 可以考虑修改虚拟机支持更大的跳转范围

### 限制 3：没有除法/乘法指令
**问题：** 无法直接进行乘除运算

**解决方案：**
1. 使用加减法循环模拟
2. 对于编译器，可以先在 Python 中实现，然后用 EvoASM 重写
3. 利用系统调用（如果需要可以添加）

---

## 文件结构

```
bootstrap/full/
├── std/                    # 标准宏库
│   ├── instructions.evoasm   # 指令集定义
│   ├── macros.evoasm         # 基础宏
│   ├── string.evoasm         # 字符串操作
│   └── number.evoasm         # 数字操作
├── lib/                    # 测试程序
│   ├── test_ab.evoasm         # "AB" 测试
│   ├── test_alloc_print.evoasm # "ABC" 测试
│   ├── test_lib.evoasm        # 完整库测试
│   └── test_simple_char.evoasm # 简单字符测试
├── evoasm_assembler.py     # Python 临时汇编器（阶段 2）
├── BOOTSTRAP_PLAN.md       # 本计划文档
└── bootstrap_v4.evoasm     # 原始验证程序
```

---

## 下一步行动

### 立即行动（本周）

1. **完成词法分析器**
   - 实现逐字符处理循环
   - 实现 Token 类型判断
   - 实现 Token 存储
   - 编写测试用例

2. **创建测试框架**
   - 断言宏（ASSERT_EQ, ASSERT_NE）
   - 测试报告生成

### 中期行动（2-4 周）

1. 实现指令编码器
2. 实现完整汇编器（两遍扫描）
3. 自举验证

### 长期行动（4-12 周）

1. IDE 开发基础设施
2. 更多标准库函数
3. 性能优化

---

## 关键成功指标

| 指标 | 目标 | 当前状态 |
|------|------|----------|
| 核心指令验证 | 100% | ✅ 完成 |
| 标准库宏 | 全部可用 | ✅ 完成 |
| 词法分析器 | Token 化 | 🔄 进行中 |
| 指令编码器 | 生成字节码 | ⏳ 待开始 |
| 自举验证 | 编译自身 | ⏳ 待开始 |

---

## 风险评估

### 高风险
1. **8 位跳转限制** - 可能需要修改虚拟机
2. **缺少乘除指令** - 编译器实现复杂
3. **调试困难** - 没有调试器

### 缓解措施
1. 先实现小型测试程序验证功能
2. 利用 Python 版本作为参考实现
3. 详细的日志和状态输出
