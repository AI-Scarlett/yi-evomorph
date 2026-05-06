# 易衍 · Evomorph

**六十四卦指令集 · 进化编程 · AI 驱动**

易衍（Evomorph）是一种基于《易经》六十四卦的进化编程语言。每条指令的操作码等于其对应卦象的六爻二进制值，代码通过遗传算法自动进化优化，适应不同目标平台。

**当前版本**: v0.0.6

## 特性

- **六十四卦指令集** — 操作码 = 爻位二进制，元亨利贞四大类 64 条指令
- **基因座（Locus）** — 代码基本单元，包含指令序列和进化元数据
- **象辞（Xiangci）** — 自然语言描述程序意图，AI 翻译为卦象指令
- **进化编译** — 遗传算法自动优化代码，适应目标平台
- **IChingVM** — 卦象虚拟机，执行 EVB 字节码
- **AI 驱动** — 内置 11 家大模型厂商支持，自然语言直接生成 .evo 代码
- **交互式 CLI** — 下拉菜单命令选择，上下键导航，回车确认
- **✅ IChing EVB 自举编译器** — 编译器核心完全用 IChing 汇编(.evoasm)实现，运行于 ExtendedIChingVM2
- **🧬 MCP Server（双版本）** — 提供Python版和Evomorph版MCP Server，支持编译、象辞翻译、进化编译、运行、查询卦象、列出平台

## 自举状态

### 🎉 IChing EVB 自举编译器已实现！

v0.0.6 实现了用 IChing 汇编直接编写的自举编译器，消除了对 Python 编译器类的依赖。

**编译链路**: `compiler.evoasm` (36KB 汇编) → VM 汇编器 → `compiler.evob` (7.9KB 字节码) → 加载到 VM → 编译 .evo 源码

### 编译器架构

```
compiler.evoasm  (36KB IChing 汇编)
  ├── 词法分析器  — tokenize .evo 源码
  ├── 语法分析器  — 递归下降解析
  └── 代码生成器  — 直接生成 EVB 字节码
       │
       ▼ Python 汇编器 (唯一不可替代的 Python 依赖)
  compiler.evob  (7.9KB 编译产物)
       │
       ▼ 加载到 ExtendedIChingVM2
  IChingEvocCompiler  — 主编译路径
```

### 最小可信计算基（TCB）

| 组件 | 实现 | 说明 |
|------|------|------|
| ExtendedIChingVM2 | Python | 32寄存器 VM，执行 EVB 字节码 |
| Assembler | Python | 将 .evoasm 汇编为 EVB 字节码 |
| compiler.evoasm | IChing 汇编 | 编译器核心（lexer/parser/codegen） |
| compiler.evob | EVB 字节码 | 编译器可执行体 |

### 编译路径

| 输出格式 | 编译路径 |
|----------|----------|
| `evb` | IChing EVB 编译器（纯自举路径，失败即报错） |
| `dict/json` | 文本元数据提取 + IChing 字节码注入 |

### 已消除的 Python 依赖

- ❌ `lexer.py` → 标记 legacy，保留供 bootstrap 脚本使用
- ❌ `parser.py` → 标记 legacy
- ❌ `codegen.py` → 标记 legacy
- ❌ `ir.py` → 已删除（546行死代码）
- ❌ `PythonEvocCompiler` → 已移除（~376行）
- ❌ `ASTToIRConverter` → 已移除
- ❌ `bootstrap_compiler.py` → 已删除（~1250行，被 compiler.evoasm 完全替代）
- ❌ `native_lib.py` → 已删除（~320行，仅服务于已删除的 bootstrap_compiler）
- ❌ `compile_evo_for_vm.py` → 已删除（~120行，被直接 compiler.evoasm 编译替代）

### 新增 .evo 替代文件

- `evomorph/native/bytecode_utils.evo` — 字节码编解码（IChing 汇编 132 行）
- `evomorph/sdk/xiangci_data.evo` — 象辞模板数据（69 行）
- `evomorph/hexagrams/hexagram_table.evo` — 64卦指令集自省表（273行）
- `evomorph/hexagrams/categories.evo` — 卦象四类分组（170行）
- `evomorph/hexagrams/modifiers.evo` — 修饰符标志定义（130行）
- `evomorph/sdk/xiangci_templates.evo` — 24个象辞编程模板（200+行）
- `evomorph/simulator/niche_data.evo` — 5个平台性能数据（100+行）
- `evomorph/simulator/opcode_cost.evo` — 操作码成本映射（60+行）
- `evomorph/monitor/evomon.evo` — 性能监控基因座（90+行）

### 📦 小模型友好

易衍·Evomorph 专为小模型（3B/4B 参数、4K-8K 上下文）AI 驱动编程优化：

- **9 个自省 .evo 文件** — AI 模型无需阅读 Python 源码，通过 `.evo` 文件即可理解完整的指令集、修饰符、象辞模板、平台数据和监控逻辑
- **指令集自述（自省）** — `hexagram_table.evo` 包含完整的 64 卦指令表，支持运行时查询操作码、助记符和指令编码
- **象辞模板库** — 24 个预定义编程模式模板，小模型通过模板匹配即可生成正确代码
- **平台数据自省** — `niche_data.evo` 和 `opcode_cost.evo` 替代 Python 配置，模型可直接读取平台性能参数

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
│   ├── __init__.py              # 版本定义 (v0.0.6)
│   ├── cli/evo_ai.py             # AI 编程 CLI（交互式 Shell）
│   ├── prompts/system_prompt.md  # LLM 系统提示词
│   ├── lsp/language_server.py    # LSP 语言服务器
│   ├── compiler/                 # EvocCompiler 编译器
│   │   ├── __init__.py           # IChingEvocCompiler 主编译路径
│   │   ├── codegen.py            # 代码生成器 (legacy)
│   │   ├── lexer.py              # 词法分析器 (legacy)
│   │   └── parser.py             # 语法分析器 (legacy)
│   ├── vm/
│   │   ├── extended_vm2.py       # ExtendedIChingVM2 (32寄存器)
│   │   └── virtual_machine.py    # IChingVM 基础虚拟机
│   ├── evolution/                # 进化引擎
│   │   ├── engine.py             # Python版进化引擎
│   │   ├── evolution_core.evo    # Evomorph版进化引擎核心
│   │   └── evolution_meta.evo    # Evomorph版元基因座
│   ├── hexagrams/
│   │   ├── instruction_set.py      # 六十四卦指令集
│   │   ├── hexagram_table.evo      # 指令集自省表 (273行)
│   │   ├── categories.evo          # 卦象四类分组 (170行)
│   │   └── modifiers.evo           # 修饰符标志定义 (130行)
│   ├── simulator/
│   │   ├── niche.py                # 平台模拟生态位
│   │   ├── niche_data.evo          # 平台性能数据 (100+行)
│   │   └── opcode_cost.evo         # 操作码成本映射 (60+行)
│   ├── sdk/
│   │   ├── xiangci.py              # 象辞翻译 SDK
│   │   ├── xiangci_data.evo        # 象辞模板数据 (69行)
│   │   └── xiangci_templates.evo   # 24个象辞编程模板 (200+行)
│   ├── stdlib/                   # 标准库（.evo 格式）
│   ├── debugger/                 # 爻镜调试器
│   ├── monitor/
│   │   └── evomon.evo            # 性能监控基因座 (90+行)
│   ├── native/                   # 原生模块
│   │   ├── bytecode_utils.py     # 字节码工具 (桥接层)
│   │   └── bytecode_utils.evo    # 字节码工具 (.evo)
│   └── bootstrap/                # 自举编译器
│       ├── compiler.evoasm       # IChing 汇编编译器 (36KB)
│       ├── compiler.evob         # 编译器可执行体 (7.9KB)
│       ├── assembler.evoasm      # 汇编器源码
│       ├── self_compile.py       # 自举过程实现 (legacy)
│       ├── enhanced_bootstrap.py # 增强自举接口 (legacy)
│       ├── true_self_hosting.py  # 真正自举实现 (legacy)
│       └── iching/               # IChing 编译器桥接
│           └── iching_compiler.py # 主编译器桥接 (已清理传统编译路径)
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

### v0.0.6 (2026-05-06)

#### 🔥 重大变更：IChing EVB 自举编译器成为唯一编译路径

- **移除 PythonEvocCompiler** — Python 编译器类已完全移除，不再作为回退路径
- **删除 ir.py** (546行) — 中间表示层，仅被已废弃的 Python 编译器引用
- **标记 legacy** — lexer.py / parser.py / codegen.py 保留供 bootstrap 脚本使用
- **新增 .evo 替代** — bytecode_utils.evo (132行) / xiangci_data.evo (69行)

#### 🐛 VM Bug 修复 (ExtendedIChingVM2)
- PC 推进: ext_mode=2 缺少立即数时正确报错 (不再静默继续)
- 寄存器掩码: ext_mode=0 支持全部 32 个寄存器 R0-R31 (之前只有 R0-R15)
- 编码注释修正与实际派发逻辑一致

#### 🧬 指令集自省（Phase 1）
- **hexagram_table.evo** (273行) — 完整64卦指令表，支持运行时自省查询（lookup_by_opcode / lookup_by_mnemonic / encode_instruction / decode_instruction）
- **categories.evo** (170行) — 四类卦象分组（元/亨/利/贞），每类16个操作码
- **modifiers.evo** (130行) — 6种修饰符标志定义（ASYNC/ATOMIC/PRIV/WEAK/STRONG/VOLATILE）
- **export_evo_heap_data()** — 导出二进制指令表（3202字节）供 VM 堆加载

#### 📚 象辞模板库扩展（Phase 2）
- **xiangci_templates.evo** — 24个预定义编程模板（原仅3个 parallel/IO/compute）
- 覆盖：并发原语(5)、数据处理(5)、IO操作(4)、容错恢复(3)、安全(3)、内存管理(2)、生命周期(2)
- 每个模板包含 template_instructions 和 fitness_hint

#### 🧹 Bootstrap 清理（Phase 3）
- **删除 bootstrap_compiler.py** (~1250行) — 传统CPU汇编编译器，被 compiler.evoasm 完全替代
- **删除 native_lib.py** (~320行) — 原生标准库，仅服务于已删除的编译器
- **删除 compile_evo_for_vm.py** (~120行) — .evo→C VM 格式编译包装器
- **标记 legacy** — enhanced_bootstrap.py / complete_bootstrap_runtime.py / self_compile.py / true_self_hosting.py / iching_compiler.py

#### 📊 数据模块 .evo 化（Phase 4）
- **niche_data.evo** (100+行) — 5个平台性能数据（Linux/Android/iOS/Windows/Harmony）
- **opcode_cost.evo** (60+行) — 操作码成本分类映射（thread_create/io/memory/sync/lock/branch/compute）
- **evomon.evo** (90+行) — 性能监控基因座（采样/热点路径/进化建议/报告生成）

#### 🧹 清理
- 删除根目录 92 个临时 test/debug 脚本
- README 和文档更新至 v0.0.6

### v0.0.5
- IChing EVB 编译器集成
- ExtendedIChingVM2 (32寄存器, 双指令集)
- self_compile.py 自举引导
- continuous_bootstrap.py 持续自举循环
- 元数据提取 (_extract_evo_metadata)

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
