# 易衍·Evomorph 语言参考手册

## 1. 语言概述

易衍·Evomorph 是一种基于六十四卦指令集的进化编程语言。核心设计原则：

- **操作码 = 爻位二进制**：每条指令的操作码就是其对应卦象的六爻二进制值
- **基因座（Locus）**：代码的基本单元，包含指令序列和进化元数据
- **象辞（Xiangci）**：用自然语言描述程序意图，由 AI 翻译为卦象指令
- **进化编译**：代码通过遗传算法自动优化，适应目标平台

## 2. 文件格式

| 扩展名 | 格式 | 说明 |
|--------|------|------|
| `.evo` | 文本 | 易衍源代码文件 |
| `.evb` | 二进制 | EVB 字节码文件（EVOB 格式，魔数 `EVOB`） |
| `.evoi` | 二进制 | EVOI 可执行映像（含入口点、链接信息） |

## 3. 程序结构

每个 `.evo` 文件的基本结构：

```evomorph
@evolang "3.0"

@xiangci {
    "自然语言描述程序意图"
}

@locus 基因座名称 {
    mut_rate   = 0.02
    cross_pool = "default"
    fitness    = min_latency + 2.0*max_throughput - 0.5*min_energy
    env_target = ["linux-6.x", "android-14", "ios-18"]
    max_generations = 100

    卦序: {
        ䷀ CREA R0, R1
        ䷌ FELLOWSHIP R0, R1
        ䷾ SYNC
        ䷁ RECV R2, R0
    }
}
```

### 3.1 版本声明

```evomorph
@evolang "3.0"
```

每个 `.evo` 文件必须以此开头，声明语言版本。

### 3.2 象辞块 @xiangci

```evomorph
@xiangci {
    "用优雅的中文描述程序意图"
}
```

象辞是程序的自然语言描述，用于：
- 人类理解程序意图
- AI 模型翻译为卦象指令
- 文档与代码的对应

### 3.3 基因座 @locus

基因座是代码的核心单元，包含：

| 属性 | 类型 | 说明 | 必填 |
|------|------|------|------|
| `mut_rate` | float | 变异率（0.0~1.0） | 是 |
| `cross_pool` | string | 交叉池名称，同池基因座可交叉 | 否 |
| `fitness` | expression | 适应度表达式 | 是 |
| `env_target` | [string] | 目标平台列表 | 是 |
| `max_generations` | int | 最大进化代数 | 否 |

### 3.4 元基因座 @meta_locus

```evomorph
@meta_locus 编译器优化策略 {
    mut_rate = 0.01
    fitness  = min_size + max_throughput

    卦序: {
        ䷓ CONTEMPLATE R0
        ䷑ MUT R0, 0x03
        ䷾ SYNC
    }
}
```

元基因座定义编译器自身的进化策略，用于优化编译过程。

## 4. 卦序（指令序列）

卦序是基因座中的指令序列，以 `卦序:` 关键字开始，花括号内包含指令列表。

### 4.1 指令格式

```
卦象符号 助记符 [修饰符] [操作数1, 操作数2, ...]
```

示例：
```evomorph
䷀ CREA R0, R1
䷌ FELLOWSHIP.ASYNC R0, R1
䷾ SYNC
䷁ RECV R2, 0x0100
```

也可省略卦象符号，仅使用助记符：
```evomorph
CREA R0, R1
FELLOWSHIP R0, R1
SYNC
```

或使用拼音：
```evomorph
QIAN R0, R1
TONGREN R0, R1
```

### 4.2 操作数类型

| 类型 | 格式 | 示例 |
|------|------|------|
| 寄存器 | `R0`~`R15` | `R0`, `R1`, `R_FP`, `R_SP` |
| 立即数 | 十进制/十六进制/二进制 | `42`, `0xFF00`, `0b101010` |
| 标签 | `@label` | `@loop_start` |
| 环境引用 | `env.xxx` | `env.platform` |

### 4.3 特殊寄存器

| 寄存器 | 索引 | 用途 |
|--------|------|------|
| `R_FP` | 12 | 帧指针 |
| `R_SP` | 13 | 栈指针 |
| `R_LR` | 14 | 链接寄存器（返回地址） |
| `R_A0` | 15 | 累加器/参数寄存器 |

## 5. 六十四卦指令集

### 5.1 操作码编码规则

操作码 = 卦象六爻的二进制值。阳爻（⚊）= 1，阴爻（⚋）= 0，从下到上为 bit0 到 bit5。

示例：
- ䷀ 乾 = ⚊⚊⚊⚊⚊⚊ = 111111₂ = 63
- ䷁ 坤 = ⚋⚋⚋⚋⚋⚋ = 000000₂ = 0
- ䷾ 既济 = ⚊⚋⚊⚋⚊⚋ = 010101₂ = 21

### 5.2 元·创生（阳爻为主）

| 卦象 | 助记符 | 操作码 | 二进制 | 功能 |
|------|--------|--------|--------|------|
| ䷀ | CREA | 63 | 111111 | 创建新进程/线程 |
| ䷁ | RECV | 0 | 000000 | 接收消息/映射 |
| ䷂ | ALLOC | 17 | 010001 | 内存分配 |
| ䷃ | SPRT | 34 | 100010 | 加载动态库 |
| ䷄ | WAIT | 23 | 010111 | 等待条件 |
| ䷅ | LOCK | 58 | 111010 | 互斥锁 |
| ䷆ | BRANCH | 2 | 000010 | 条件分支 |
| ䷇ | MERGE | 16 | 010000 | 合并数据流 |
| ䷈ | PREFETCH | 55 | 110111 | 预取缓存行 |
| ䷉ | STEP | 59 | 111011 | 单步执行/迭代 |
| ䷊ | FLUSH | 7 | 000111 | 刷新写缓冲 |
| ䷋ | HALT | 56 | 111000 | 暂停/阻塞 |
| ䷌ | FELLOWSHIP | 61 | 111101 | 同步通信集结 |
| ䷍ | ABUNDANCE | 47 | 101111 | 写回/填充数据 |
| ䷎ | YIELD | 4 | 000100 | 释放资源/让出 |
| ䷏ | SPECULATE | 8 | 001000 | 预测分支/投机执行 |

### 5.3 亨·交互

| 卦象 | 助记符 | 操作码 | 功能 |
|------|--------|--------|------|
| ䷐ | FOLLOWING | 25 | 数据流跟踪/复制 |
| ䷑ | MUT | 38 | 强制变异 |
| ䷒ | APPROACH | 3 | 接近临界区 |
| ䷓ | CONTEMPLATE | 48 | 观测/性能监视 |
| ䷔ | BITE | 41 | 断言/校验 |
| ䷕ | ADORN | 37 | 格式化/编码转换 |
| ䷖ | STRIP | 32 | 剥离/解构数据 |
| ䷗ | RETURN | 1 | 函数返回/循环回跳 |
| ䷘ | INTRINSIC | 57 | 内建原子操作 |
| ䷙ | BARRIER | 39 | 内存屏障 |
| ䷚ | NOURISH | 33 | 垃圾回收/内存养护 |
| ䷛ | OVERLOAD | 30 | 异常/溢出处理 |
| ䷜ | TRAP | 18 | 异常捕获/陷阱 |
| ䷝ | ILLUMINATE | 45 | 日志/调试输出 |
| ䷞ | SENSE | 28 | 事件监听/感应 |
| ䷟ | PERSIST | 14 | 持久化存储 |

### 5.4 利·转换

| 卦象 | 助记符 | 操作码 | 功能 |
|------|--------|--------|------|
| ䷠ | RETREAT | 60 | 安全退出/回滚 |
| ䷡ | THRUST | 15 | 强制执行/突破 |
| ䷢ | ADVANCE | 40 | 队列推进/流水线 |
| ䷣ | OBSCURE | 5 | 加密/混淆 |
| ䷤ | BIND | 53 | 绑定/闭包 |
| ䷥ | CONVERT | 43 | 类型转换 |
| ䷦ | LAME | 20 | 重试/降级 |
| ䷧ | UNLOCK | 10 | 解锁/释放 |
| ䷨ | REDUCE | 35 | 缩减/压缩 |
| ䷩ | INCREASE | 49 | 扩展/增强 |
| ䷪ | BREAK | 31 | 中断/断开 |
| ䷫ | MATE | 62 | 基因交叉重组 |
| ䷬ | GATHER | 24 | 收集/归约 |
| ䷭ | PUSH_UP | 6 | 入栈/上推 |
| ䷮ | TRAPPED | 26 | 死锁检测 |
| ䷯ | WELL | 22 | 阻塞读/管道 |

### 5.5 贞·终成

| 卦象 | 助记符 | 操作码 | 功能 |
|------|--------|--------|------|
| ䷰ | REPLACE | 29 | 替换/热更新 |
| ䷱ | CAST | 46 | 类型铸造/固化 |
| ䷲ | SHOCK | 9 | 信号/中断触发 |
| ䷳ | STILL | 36 | 暂停/冻结 |
| ䷴ | GRADUAL | 52 | 逐步执行 |
| ䷵ | MISMATCH | 11 | 类型不匹配 |
| ䷶ | ABOUND | 13 | 批量操作 |
| ䷷ | TRAVEL | 44 | 上下文切换 |
| ䷸ | PENETRATE | 54 | 渗透/穿透访问 |
| ䷹ | JOY | 27 | 回调/完成通知 |
| ䷺ | DISPERSE | 50 | 分散写入 |
| ䷻ | THROTTLE | 19 | 节流/流控 |
| ䷼ | TRUST | 51 | 签名/验证 |
| ䷽ | MICRO | 12 | 微调/微操作 |
| ䷾ | SYNC | 21 | 屏障同步 |
| ䷿ | FUTU | 42 | 异步占位符/未来值 |

## 6. 修饰符

修饰符附加在助记符后，用点号分隔：

```evomorph
䷀ CREA.ASYNC R0, R1
䷅ LOCK.ATOMIC R0
䷁ RECV.PRIV R0, 0x100
```

| 修饰符 | 二进制 | 功能 |
|--------|--------|------|
| `.ASYNC` | 100000 | 异步执行 |
| `.ATOMIC` | 010000 | 原子操作 |
| `.PRIV` | 001000 | 私有访问 |
| `.WEAK` | 000100 | 弱引用 |
| `.STRONG` | 000010 | 强引用 |
| `.VOLATILE` | 000001 | 易失性 |

修饰符存储在指令的 modifier 字段中，与操作码一同编码为字节码。

## 7. 适应度表达式

适应度表达式定义进化编译的优化目标，由关键词和权重组成：

```evomorph
fitness = min_latency + 2.0*max_throughput - 0.5*min_energy
```

### 7.1 适应度关键词

| 关键词 | 含义 | 优化方向 |
|--------|------|----------|
| `min_latency` | 最小延迟 | 延迟越低越好 |
| `max_throughput` | 最大吞吐量 | 吞吐量越高越好 |
| `min_energy` | 最小能耗 | 能耗越低越好 |
| `min_size` | 最小代码体积 | 代码越短越好 |

### 7.2 场景推荐

| 场景 | 推荐表达式 |
|------|-----------|
| 并行程序 | `min_latency + 2.0*max_throughput - 0.5*min_energy` |
| IO 密集 | `min_latency + min_energy` |
| 计算密集 | `max_throughput + min_latency` |
| AI 应用 | `max_throughput + min_size` |
| 嵌入式/IoT | `min_energy + min_size + 0.5*min_latency` |

## 8. 目标平台

| 平台标识 | 说明 | 内存延迟 | 最大线程 |
|----------|------|----------|----------|
| `linux-6.x` | Linux 6.x | 80ns | 128 |
| `android-14` | Android 14 | 120ns | 16 |
| `ios-18` | iOS 18 | 60ns | 8 |
| `win-11` | Windows 11 | 90ns | 64 |
| `harmony-5` | HarmonyOS 5 | 100ns | 32 |

## 9. 注释

单行注释以 `//` 开头：

```evomorph
@evolang "3.0"

// 这是一个并行求和程序
@locus parallel_sum {
    // 接收输入
    mut_rate = 0.02
    ...
}
```

## 10. 完整示例

### 10.1 并行求和

```evomorph
@evolang "3.0"

@xiangci {
    "并行计算1到N的整数之和，适配Linux与鸿蒙平台"
}

@locus parallel_sum {
    mut_rate   = 0.02
    cross_pool = "compute"
    fitness    = min_latency + 2.0*max_throughput - 0.5*min_energy
    env_target = ["linux-6.x", "harmony-5"]
    max_generations = 100

    卦序: {
        ䷁ RECV R0, 0x0100
        ䷂ ALLOC R1, R0
        ䷀ CREA R2, R3
        ䷌ FELLOWSHIP R2, R3
        ䷬ GATHER R4, R2
        ䷍ ABUNDANCE R5, R4
        ䷝ ILLUMINATE R5
        ䷾ SYNC
        ䷗ RETURN R5
    }
}
```

### 10.2 AI 推理服务

```evomorph
@evolang "3.0"

@xiangci {
    "AI推理服务：接收输入数据，执行模型推理，返回结果，适配服务器与移动端"
}

@locus ai_inference {
    mut_rate   = 0.01
    cross_pool = "ai"
    fitness    = max_throughput + min_size
    env_target = ["linux-6.x", "android-14", "ios-18"]
    max_generations = 200

    卦序: {
        ䷁ RECV R0, 0x0200
        ䷂ ALLOC R1, R0
        ䷃ SPRT R2, 0x01
        ䷀ CREA R3, R4
        ䷌ FELLOWSHIP R3, R4
        ䷏ SPECULATE R5, R0
        ䷐ FOLLOWING R6, R5
        ䷱ CAST R7, R6
        ䷍ ABUNDANCE R8, R7
        ䷝ ILLUMINATE R8
        ䷾ SYNC
        ䷗ RETURN R8
    }
}

@meta_locus ai_inference_optimizer {
    mut_rate = 0.005
    fitness  = min_size + max_throughput

    卦序: {
        ䷓ CONTEMPLATE R0
        ䷑ MUT R0, 0x03
        ䷫ MATE R0, R1
        ䷾ SYNC
    }
}
```

### 10.3 IoT 传感器采集

```evomorph
@evolang "3.0"

@xiangci {
    "物联网传感器数据采集与边缘计算，低功耗优先，适配鸿蒙与安卓"
}

@locus iot_sensor {
    mut_rate   = 0.03
    cross_pool = "iot"
    fitness    = min_energy + min_size + 0.5*min_latency
    env_target = ["harmony-5", "android-14"]
    max_generations = 150

    卦序: {
        ䷁ RECV R0, 0x0300
        ䷂ ALLOC R1, 0x40
        ䷐ FOLLOWING R2, R0
        ䷬ GATHER R3, R2
        ䷽ MICRO R4, R3
        ䷍ ABUNDANCE R5, R4
        ䷹ JOY R6, R5
        ䷝ ILLUMINATE R6
        ䷎ YIELD
        ䷾ SYNC
        ䷗ RETURN R6
    }
}
```
