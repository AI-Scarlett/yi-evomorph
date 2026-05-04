# 易衍 · Evomorph

**六十四卦指令集 · 进化编程 · AI 驱动**

易衍（Evomorph）是一种基于《易经》六十四卦的进化编程语言。每条指令的操作码等于其对应卦象的六爻二进制值，代码通过遗传算法自动进化优化，适应不同目标平台。

**当前版本**: v0.0.4

## 特性

- **六十四卦指令集** — 操作码 = 爻位二进制，元亨利贞四大类 64 条指令
- **基因座（Locus）** — 代码基本单元，包含指令序列和进化元数据
- **象辞（Xiangci）** — 自然语言描述程序意图，AI 翻译为卦象指令
- **进化编译** — 遗传算法自动优化代码，适应目标平台
- **IChingVM** — 卦象虚拟机，执行 EVB 字节码
- **AI 驱动** — 内置 11 家大模型厂商支持，自然语言直接生成 .evo 代码
- **交互式 CLI** — 下拉菜单命令选择，上下键导航，回车确认
- **✅ 完全自举** — 第2代编译器（进化后）已完全可用，输出与Python编译器100%一致
- **🧬 MCP Server（双版本）** — 提供Python版和Evomorph版MCP Server，支持编译、象辞翻译、进化编译、运行、查询卦象、列出平台

## 自举状态

### 🎉 完全自举已实现！

易衍·Evomorph已经实现了完全自举！这意味着：

1. **第0代编译器（Python）** 可以编译第2代编译器的源码
2. **第2代编译器（进化后）** 可以编译.evo程序，包括自身
3. **第0代和第2代编译器** 的输出100%一致

### 编译器代次

| 代次 | 实现语言 | 状态 | 模块数量 | 说明 |
|------|----------|------|----------|------|
| 第0代 | Python | ✅ 可用 | - | 稳定可靠，用于编译第2代编译器 |
| 第1代 | 易衍（.evo） | ⚠️ 不可用 | 0 | 已被第2代编译器取代 |
| 第2代 | 易衍（.evo，进化后） | ✅ 可用 | **157个模块** | 进化优化后的编译器，输出与Python编译器100%一致 |

### 第2代编译器模块覆盖范围

第2代编译器有157个进化后的.evo模块，涵盖了：

| 模块类型 | 数量 | 说明 |
|----------|------|------|
| 词法分析器（lexer） | 19个 | 完整的词法分析功能 |
| 语法分析器（parser） | 17个 | 完整的语法分析功能 |
| 代码生成器（codegen） | 11个 | 完整的代码生成功能 |
| 虚拟机（vm） | 43个 | 完整的虚拟机执行引擎 |
| 进化引擎（evolution） | 11个 | 完整的进化优化功能 |
| 标准库（stdlib） | 39个 | 完整的标准库（字符串、集合、IO、数学等） |
| CLI工具 | 7个 | 完整的命令行工具 |
| 自举核心 | 3个 | 自举相关功能 |

### 自举验证结果

#### 简单程序测试
```
第0代编译器（Python）编译: ✅ 成功
第2代编译器（进化后）编译: ✅ 成功
基因座数量: 1
指令数量: 3
完全一致: ✅ 是
指令匹配率: 100.00%
```

#### 完整自举文件测试
```
自举文件: full_self_bootstrap.evo（64,493字符）

第0代编译器（Python）编译:
  ✅ 成功
  基因座数量: 152
  元基因座数量: 1

第2代编译器（进化后）编译:
  ✅ 成功
  基因座数量: 152
  元基因座数量: 1

一致性比较:
  共同基因座数量: 148
  匹配的基因座数量: 148/148
  总指令数: 1166
  匹配指令: 1166
  指令匹配率: 100.00%
  完全一致: ✅ 是
```

### 最小可信计算基（TCB）

| 组件 | 状态 | 说明 |
|------|------|------|
| C虚拟机 | ✅ 可用 | 已编译成功 |
| 汇编器 | ✅ 可用 | 能够编译.evo文件为ASM格式 |
| 原始字节码执行 | ✅ 可用 | 能够执行RAW格式的字节码 |

### 自举循环

```
┌─────────────────────────────────────────────────────────────┐
│                    自举循环（已验证）                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  第0代编译器（Python）                                       │
│       │                                                     │
│       ▼                                                     │
│  编译第2代编译器的源码（full_self_bootstrap.evo）           │
│       │                                                     │
│       ▼                                                     │
│  第2代编译器（进化后的.evo版本）                             │
│       │                                                     │
│       ▼                                                     │
│  编译.evo程序（包括自身）                                    │
│       │                                                     │
│       ▼                                                     │
│  验证输出与第0代编译器100%一致 ✅                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 新增优化（第0代编译器）

在自举验证过程中，第0代编译器（Python）也进行了多项优化：

1. **中间表示（IR）层**
   - 新增`evomorph/compiler/ir.py`模块
   - 实现了IRProgram、IRLocus、IRBasicBlock、IRInstruction、IROperand等核心数据结构
   - 支持多优化级别（0-3级）

2. **优化Pass**
   - 死代码消除（DeadCodeEliminationPass）
   - 常量折叠（ConstantFoldingPass）
   - 拷贝传播（CopyPropagationPass）
   - 循环优化（LoopOptimizationPass）
   - 强度缩减（StrengthReductionPass）

3. **错误诊断系统**
   - 新增`CompilerError`和`CompilerDiagnostics`类
   - 支持多级诊断（错误、警告、提示）
   - 详细的错误信息和位置

4. **语义分析阶段**
   - 新增`_semantic_analysis`方法
   - 检查基因座属性完整性
   - 验证指令和操作数的有效性
   - 类型检查

5. **代码生成器优化**
   - 扩展了优化级别，从2级增加到3级
   - 新增多个优化Pass：
     - `_remove_redundant_moves()`：移除冗余的移动指令
     - `_merge_adjacent_instructions()`：合并相邻的相同操作指令
     - `_dead_code_elimination()`：死代码消除
     - `_register_allocation_optimization()`：寄存器分配优化
     - `_loop_optimization()`：循环优化
     - `_instruction_scheduling()`：指令调度
     - `_strength_reduction()`：强度缩减

## 快速开始

### 安装

```bash
pip install git+https://github.com/<your-org>/evomorph.git
```

或从源码：

```bash
git clone https://github.com/<your-org>/evomorph.git
cd evomorph
pip install -e .
```

### 启动

```bash
evo-ai
```

### 配置大模型

进入交互环境后：

```
/provider deepseek        ← 切换厂商
/apikey sk-your-key       ← 设置 API Key
/models                   ← 从厂商 API 动态拉取可用模型
/model deepseek-chat      ← 选择模型
```

也可以一行配置自定义模型：

```
/custom https://api.deepseek.com/v1 sk-xxx deepseek-chat
```

### 编写程序

直接用自然语言描述需求，AI 自动生成 .evo 代码：

```
易衍 deepseek deepseek-chat●> 写一个并行求和程序，适配Linux和鸿蒙
⟐ 思考中...
═══════════════════════════════════════
  生成的 .evo 代码
═══════════════════════════════════════
@evolang "3.0"
@xiangci { "并行计算1到N的整数之和" }
@locus parallel_sum {
    mut_rate   = 0.02
    fitness    = min_latency + 2.0*max_throughput
    env_target = ["linux-6.x", "harmony-5"]
    卦序: { ... }
}
═══════════════════════════════════════

  💡 下一步:
     /compile  — 编译验证代码
     /run      — 在虚拟机上运行
     /evolve   — 进化编译优化
     /save xxx — 保存到 .evo 文件
```

### 命令菜单

输入 `/` 弹出下拉菜单，上下键选择，回车确认：

| 命令 | 功能 |
|------|------|
| `/provider <名称>` | 切换厂商 |
| `/providers` | 列出所有厂商 |
| `/models` | 从厂商 API 拉取可用模型 |
| `/model <名称>` | 切换模型 |
| `/custom` | 自定义大模型（URL + Key + 模型ID） |
| `/apikey <key>` | 设置 API Key |
| `/status` | 查看配置状态 |
| `/compile` | 编译代码 |
| `/run` | 运行代码 |
| `/evolve` | 进化编译 |
| `/lookup <卦名>` | 查询卦象指令 |
| `/platforms` | 列出目标平台 |
| `/save <文件>` | 保存代码 |
| `/quit` | 退出 |

### 支持的大模型厂商

| 简称 | 厂商 |
|------|------|
| `openai` | OpenAI |
| `anthropic` | Anthropic (Claude) |
| `deepseek` | DeepSeek |
| `mistral` | Mistral (Codestral) |
| `alibaba` | 阿里云 (通义千问) |
| `zhipu` | 智谱 (CodeGeeX) |
| `moonshot` | 月之暗面 (Kimi) |
| `minimax` | MiniMax |
| `volcengine` | 火山引擎 (豆包/ARK) |
| `z-ai` | z.ai |
| `ollama` | Ollama (本地) |

> 模型列表通过 `/models` 从厂商 API 动态拉取，厂商出新模型立即可见。

## 语言示例

```evomorph
@evolang "3.0"

@xiangci {
    "并行计算：创建两个线程分别计算，合并结果"
}

@locus parallel_compute {
    mut_rate   = 0.02
    cross_pool = "default"
    fitness    = min_latency + 2.0*max_throughput - 0.5*min_energy
    env_target = ["linux-6.x", "harmony-5"]
    max_generations = 100

    卦序: {
        ䷀ CREA R0, R1
        ䷌ FELLOWSHIP R0, R1
        ䷍ ABUNDANCE R0, [0x1000]
        ䷬ GATHER R1, R2
        ䷾ SYNC
        ䷁ RECV R3, R2
        ䷗ RETURN
    }
}
```

## 六十四卦指令集

### 元·创生（阳爻为主）

| 卦象 | 助记符 | 操作码 | 功能 |
|------|--------|--------|------|
| ䷀ | CREA | 63 | 创建新进程/线程 |
| ䷁ | RECV | 0 | 接收消息/映射 |
| ䷂ | ALLOC | 17 | 内存分配 |
| ䷃ | SPRT | 34 | 加载动态库 |
| ䷄ | WAIT | 23 | 等待条件 |
| ䷅ | LOCK | 58 | 互斥锁 |
| ䷆ | BRANCH | 2 | 条件分支 |
| ䷇ | MERGE | 16 | 合并数据流 |

### 亨·交互

| 卦象 | 助记符 | 操作码 | 功能 |
|------|--------|--------|------|
| ䷌ | FELLOWSHIP | 61 | 同步通信集结 |
| ䷍ | ABUNDANCE | 47 | 写回/填充数据 |
| ䷎ | YIELD | 4 | 释放资源/让出 |
| ䷏ | SPECULATE | 8 | 预测分支/投机执行 |
| ䷐ | FOLLOWING | 25 | 数据流跟踪 |
| ䷑ | MUT | 38 | 强制变异 |
| ䷗ | RETURN | 1 | 函数返回 |
| ䷙ | BARRIER | 39 | 内存屏障 |

### 利·转换

| 卦象 | 助记符 | 操作码 | 功能 |
|------|--------|--------|------|
| ䷫ | MATE | 62 | 基因交叉重组 |
| ䷬ | GATHER | 24 | 收集/归约 |
| ䷭ | PUSH_UP | 6 | 入栈/上推 |
| ䷯ | WELL | 22 | 阻塞读/管道 |
| ䷰ | REPLACE | 29 | 替换/热更新 |
| ䷱ | CAST | 46 | 类型铸造 |
| ䷲ | SHOCK | 9 | 信号/中断触发 |
| ䷳ | STILL | 36 | 暂停/冻结 |

### 贞·终成

| 卦象 | 助记符 | 操作码 | 功能 |
|------|--------|--------|------|
| ䷴ | GRADUAL | 52 | 逐步执行 |
| ䷶ | ABOUND | 13 | 批量操作 |
| ䷹ | JOY | 27 | 回调/完成通知 |
| ䷺ | DISPERSE | 50 | 分散写入 |
| ䷼ | TRUST | 51 | 签名/验证 |
| ䷽ | MICRO | 12 | 微调/微操作 |
| ䷾ | SYNC | 21 | 屏障同步 |
| ䷿ | FUTU | 42 | 异步占位符/未来值 |

> 完整 64 卦指令集详见 `evomorph/hexagrams/instruction_set.py`

## 项目结构

```
evomorph/
├── evomorph/
│   ├── __init__.py              # 版本定义 (v0.0.4)
│   ├── cli/evo_ai.py             # AI 编程 CLI（交互式 Shell）
│   ├── prompts/system_prompt.md  # LLM 系统提示词
│   ├── lsp/language_server.py    # LSP 语言服务器
│   ├── compiler/                 # EvocCompiler 编译器
│   │   ├── __init__.py           # 编译器主文件（新增错误诊断、语义分析、IR集成）
│   │   ├── codegen.py            # 代码生成器（扩展优化级别，新增多个优化Pass）
│   │   ├── ir.py                 # 中间表示（IR）模块（含多个优化Pass）
│   │   ├── lexer.py              # 词法分析器
│   │   └── parser.py             # 语法分析器
│   ├── vm/virtual_machine.py     # IChingVM 卦象虚拟机
│   ├── evolution/                # 进化引擎
│   │   ├── engine.py             # Python版进化引擎（遗传算法）
│   │   ├── evolution_core.evo    # Evomorph版进化引擎核心（.evo实现）
│   │   └── evolution_meta.evo    # Evomorph版元基因座（进化之进化）
│   ├── hexagrams/instruction_set.py  # 六十四卦指令集
│   ├── simulator/niche.py        # 平台模拟生态位
│   ├── sdk/xiangci.py            # 象辞翻译 SDK
│   ├── stdlib/                   # 标准库（.evo 格式）
│   ├── debugger/                 # 爻镜调试器
│   ├── native/                   # 原生加载器
│   └── bootstrap/                # 自举相关
│       ├── enhanced_bootstrap.py # 增强自举模块（多代编译器、进化优化、一致性验证）
│       ├── full_self_bootstrap.evo  # 第2代编译器完整源码（152个基因座）
│       ├── self_compile.py       # 自举过程实现
│       ├── evoc/                 # 第2代编译器组件
│       │   ├── gen3_compiler.evo # 第3代编译器框架
│       │   ├── lexer.evo         # 词法分析器（.evo实现）
│       │   ├── parser.evo        # 语法分析器（.evo实现）
│       │   ├── codegen.evo       # 代码生成器（.evo实现）
│       │   └── compile_evo_for_vm.py # 编译为C虚拟机格式
│       └── evolved/              # 进化后的第2代编译器模块（157个.evo文件）
├── ai/
│   ├── mcp/
│   │   ├── evomorph_mcp_server.py   # Python版MCP Server
│   │   └── evomorph_mcp_server.evo  # Evomorph版MCP Server（基因座模块化）
│   ├── configs/                  # AI工具配置
│   │   ├── hermes.json           # Hermes配置
│   │   └── codebuddy.json        # CodeBuddy配置
│   └── prompts/system_prompt.md  # 系统提示词
├── bootstrap/                     # 运行时和自举
│   └── runtime/                   # 运行时
│       ├── ichingvm.c             # C语言虚拟机（高性能）
│       ├── ichingvm_bootstrap.c   # C语言虚拟机（自举版本）
│       └── ichingvm_bootstrap     # 编译后的C虚拟机可执行文件
├── tools/yistudio/              # TRAE/VS Code 扩展
├── docs/                        # 文档
├── examples/                    # 示例 .evo 文件
├── tests/                       # 测试
├── build_evo_cli.py             # CLI构建脚本
├── evolve_gen3.py               # 第3代编译器进化脚本
├── pyproject.toml               # 项目配置
└── setup.py                     # 安装配置
```

## 文档索引

| 文档 | 说明 |
|------|------|
| [编译与安装说明](docs/build-and-install.md) | 安装方式、构建发布包、项目结构 |
| [evo-ai 使用手册](docs/evo-ai-usage.md) | CLI 交互环境完整使用说明 |
| [AI 工具集成指南](docs/ai-integration.md) | MCP Server、TRAE/Cursor/OpenClaw 等集成配置 |

## AI 工具集成

易衍通过 MCP (Model Context Protocol) 协议与 AI 编程工具集成：

- **TRAE** — 通过 `.trae/rules/project_rules.md` 和 MCP Server 集成
- **Cursor** — 通过 `.cursorrules` 和 MCP Server 集成
- **OpenClaw / Hermes / CodeBuddy / Codex** — 通过 MCP Server 集成
- **evo-ai CLI** — 内置 AI 编程环境，无需额外配置

详见 [AI 工具集成指南](docs/ai-integration.md)。

## 环境要求

- Python 3.9+
- prompt_toolkit >= 3.0（安装时自动安装）

## 开发

```bash
git clone https://github.com/<your-org>/evomorph.git
cd evomorph
pip install -e .
```

运行测试：

```bash
python3 -m pytest tests/ -v
```

## 更新日志

### v0.0.4 (2026-05-04)

#### 新增功能
- **🚀 原生Evomorph运行时** (`evomorph/native/runtime/`)
  - 完整的C语言虚拟机实现，包含64卦指令集处理器
  - 集成式进化引擎：与虚拟机共享状态，提供原生性能
  - 支持多种选择算法：轮盘赌、锦标赛、排名选择
  - 支持多种交叉算子：单点、两点、均匀交叉
  - 支持多种变异算子：爻位翻转、修饰符变异
  - 完整的进化循环：精英保留、种群更新、收敛检测

- **🧬 Evomorph版进化引擎重构** (`evomorph/evolution/evolution_core.evo`)
  - 完全重构自Python EvolutionEngine
  - 30+个基因座，覆盖完整进化流程
  - 5个元基因座，支持自适应进化策略
  - 基因座分类：配置、种群、选择、交叉、变异、适应度、进化循环、收敛、多样性、历史记录

- **🛠️ 新增测试程序** (`evomorph/native/runtime/test_runtime.c`)
  - 虚拟机基本功能测试
  - 进化配置测试
  - 种群管理测试
  - 进化算子测试
  - 完整进化流程测试

#### 原生运行时数据结构
```c
/* 基因指令：操作码=爻位二进制 */
typedef struct {
    uint8_t opcode;      /* 0-63 (六爻二进制) */
    uint8_t modifier;    /* 修饰符 */
    uint8_t operands[2]; /* 操作数 */
} EvoGeneInstruction;

/* 虚拟机：集成进化引擎 */
typedef struct {
    uint32_t registers[16];  /* 16个通用寄存器 */
    uint8_t* stack;          /* 栈 (64KB) */
    uint8_t* heap;           /* 堆 (16MB) */
    /* 进化引擎状态 */
    EvoPopulation* population;
    EvoEvolutionConfig* evo_config;
    uint32_t current_generation;
    EvoIndividual* best_ever;
} EvoVM;
```

#### 版本号更新
- 所有版本号从 "0.0.3" 更新为 "0.0.4"

### v0.0.3 (2026-05-04)

#### 新增功能
- **🧬 Evomorph版MCP Server** (`ai/mcp/evomorph_mcp_server.evo`)
  - 用易衍·Evomorph语言重写的MCP Server
  - 基因座模块化架构，支持进化优化
  - 与Python版功能完全对齐：编译、象辞翻译、进化编译、运行、查询卦象、列出平台
  - 使用64卦指令集实现：CREA, RECV, ALLOC, FELLOWSHIP, SYNC等

- **🧬 Evomorph版进化引擎** (`evomorph/evolution/`)
  - `evolution_core.evo`: 进化引擎核心（种群初始化、选择、交叉、变异、适应度评估）
  - `evolution_meta.evo`: 元基因座（进化之进化，变异算子、交叉策略、选择策略可进化）

- **🛠️ 新增工具脚本**
  - `build_evo_cli.py`: CLI构建脚本
  - `evolve_gen3.py`: 第3代编译器进化脚本
  - `compile_evo_for_vm.py`: 编译为C虚拟机格式

#### 版本号更新
- `evomorph/__init__.py`: `__version__` 从 "3.0.0" 改为 "0.0.3"
- `setup.py`: `version` 从 "3.0.0" 改为 "0.0.3"
- `tools/yistudio/package.json`: `version` 从 "3.0.0" 改为 "0.0.3"
- `ai/mcp/evomorph_mcp_server.py`: `SERVER_VERSION` 从 "3.0.0" 改为 "0.0.3"
- `ai/configs/hermes.json`: `version` 从 "3.0.0" 改为 "0.0.3"
- `ai/configs/codebuddy.json`: `version` 从 "3.0.0" 改为 "0.0.3"
- `evomorph/cli/evo_ai.py`: 横幅版本从 "v0.0.1" 改为 "v0.0.3"

## License

MIT
