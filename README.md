# 易衍 · Evomorph

**六十四卦指令集 · 进化编程 · AI 驱动**

易衍（Evomorph）是一种基于《易经》六十四卦的进化编程语言。每条指令的操作码等于其对应卦象的六爻二进制值，代码通过遗传算法自动进化优化，适应不同目标平台。

**当前版本**: v0.1.0

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

### 🎉 全面 .evo 化完成！v0.1.0

v0.1.0 标志着易衍·Evomorph 全面进入自举时代：编译器核心、VM 运行时、进化引擎、MCP Server、象辞 SDK、模拟器、监控器 — **所有核心模块均已完成 .evo 格式实现**。Python 模块仅保留桥接层和 CLI 入口，约 5000+ 行 Python 已被 .evo 替代。VM 执行路径默认走 C 原生 VM（libichingvm2.dylib），异常时自动回退 Python VM。

**编译链路**: `compiler.evoasm` (36KB 汇编) → VM 汇编器 → `compiler.evob` (7.9KB 字节码) → 加载到 VM → 编译 .evo 源码

### 核心模块 .evo 化一览

| 模块 | .evo 文件 | 行数 | 说明 |
|------|-----------|------|------|
| 编译器 | `compiler.evoasm` + `compiler.evob` | 36KB/7.9KB | 词法/语法/代码生成全链路 |
| 进化引擎 | `evolution_core.evo` + `evolution_meta.evo` | 500+ | 遗传算法完整实现 |
| MCP Server | `evomorph_mcp_server.evo` | 17 基因座 | 双版本之一 |
| 象辞 SDK | `xiangci_data.evo` + `xiangci_templates.evo` | 270+ | 24 个编程模板 |
| 指令集自省 | `hexagram_table.evo` + `categories.evo` + `modifiers.evo` | 573 | 64 卦完整自省 |
| 模拟器 | `niche_data.evo` + `opcode_cost.evo` | 160+ | 5 平台性能数据 |
| 监控 | `evomon.evo` | 90+ | 性能监控基因座 |
| 字节码工具 | `bytecode_utils.evo` | 132 | 编解码 |

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
| ExtendedIChingVM2 | Python + C VM | 32寄存器 VM，执行默认走 C 原生 VM |
| CBridgeVM | Python ctypes | C 原生 VM 桥接（310行替代 2600行） |
| Assembler | Python | 将 .evoasm 汇编为 EVB 字节码 |
| compiler.evoasm | IChing 汇编 | 编译器核心（lexer/parser/codegen） |
| compiler.evob | EVB 字节码 | 编译器可执行体 |
| libichingvm2.dylib | C | 原生 VM 共享库（38KB, 10/10测试通过） |

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
pip install git+https://github.com/AI-Scarlett/yi-evomorph.git
```

或从源码：

```bash
git clone https://github.com/AI-Scarlett/yi-evomorph.git
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

> 完整 64 卦指令集详见 `evomorph/hexagrams/hexagram_table.evo`（自省格式）

## 项目结构

```
evomorph/
├── evomorph/                      # 核心库（.evo/.evob 格式）
│   ├── bootstrap/                 # 自举编译器
│   │   ├── compiler.evoasm        # IChing 汇编编译器 (36KB)
│   │   ├── compiler.evob          # 编译器可执行体 (7.9KB)
│   │   ├── assembler.evoasm       # 汇编器源码
│   │   ├── preprocess.py          # 预处理桥接层
│   │   └── iching/evoc_compiler.py # 编译器桥接
│   ├── native/                    # C 原生 VM
│   │   ├── runtime/
│   │   │   ├── ichingvm.c         # C语言虚拟机
│   │   │   ├── ichingvm_bootstrap.c
│   │   │   └── libichingvm2.dylib # 编译后的共享库
│   │   ├── runtime.py             # C VM 桥接 (CBridgeVM)
│   │   ├── bytecode_utils.evo     # 字节码编解码 (132行)
│   │   └── bytecode_utils.evob
│   ├── vm/
│   │   ├── vm_runtime.evo         # IChingVM 运行时
│   │   └── vm_runtime.evob
│   ├── evolution/                 # 进化引擎
│   │   ├── evolution_core.evo     # 进化引擎核心 (500+行)
│   │   └── evolution_meta.evo     # 元基因座
│   ├── hexagrams/                 # 指令集自省
│   │   ├── hexagram_table.evo     # 64卦指令表 (273行)
│   │   ├── categories.evo         # 卦象四类分组 (170行)
│   │   └── modifiers.evo          # 修饰符标志 (130行)
│   ├── simulator/                 # 平台模拟
│   │   ├── niche_data.evo         # 5平台性能数据 (100+行)
│   │   └── opcode_cost.evo        # 操作码成本映射 (60+行)
│   ├── sdk/                       # 象辞 SDK
│   │   ├── xiangci_data.evo       # 象辞模板数据 (69行)
│   │   └── xiangci_templates.evo  # 24个编程模板 (200+行)
│   ├── monitor/
│   │   └── evomon.evo             # 性能监控基因座 (90+行)
│   ├── hub/
│   │   ├── repository.evo         # 基因座仓库
│   │   └── repository.evob
│   └── stdlib/                    # 标准库 (.evo)
├── ai/                            # AI 工具集成
│   ├── mcp/
│   │   ├── evomorph_mcp_server.py # Python版MCP Server
│   │   ├── evomorph_mcp_server.evo # Evomorph版MCP Server (17基因座)
│   │   ├── evomorph_mcp_server.evob
│   │   └── mcp_config.json        # MCP 配置
│   ├── configs/                   # AI工具配置
│   │   ├── codebuddy.json
│   │   ├── codex.json
│   │   └── hermes.json
│   └── prompts/
│       └── system_prompt.md       # AI 系统提示词
├── cli/                           # CLI 工具 (.evo 格式)
│   ├── evo_ai.evo
│   └── evo_ai.evob
├── tools/                         # 开发和构建工具
│   ├── evoc                       # evomorph CLI 工具 (Python)
│   ├── yaojing/                   # 爻镜调试器 (.evo)
│   ├── yistudio/                  # VS Code 扩展
│   └── lsp/                       # LSP 语言服务器 (.evo)
├── bootstrap/                     # C 原生运行时
├── docs/                          # 文档 (10篇)
├── examples/                      # 示例 .evo 文件
├── tests/                         # 测试 (.evo/.sha256)
├── meta/                          # 项目元数据
├── pyproject.toml                 # Python 项目配置
└── README.md
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
git clone https://github.com/AI-Scarlett/yi-evomorph.git
cd evomorph
pip install -e .
```

运行测试：

```bash
python3 -m pytest tests/ -v
```

## 更新日志

### v0.1.0 (2026-05-13)

#### 🎉 全面 .evo 化完成

- **所有核心模块完成 .evo 格式实现**：编译器、进化引擎、MCP Server、象辞 SDK、指令集自省、模拟器、监控器全部 .evo 化
- **累计消除约 5000+ 行 Python**：lexer.py / parser.py / codegen.py / ir.py / bootstrap_compiler.py / native_lib.py 等全部删除或标记 legacy
- **VM 执行默认走 C 原生 VM**（libichingvm2.dylib），异常时自动回退 Python VM
- **编译器全链路自举**：compiler.evoasm → compiler.evob → 加载到 VM → 编译 .evo 源码
- **进化引擎完全 .evo 化**：evolution_core.evo + evolution_meta.evo，30+ 基因座覆盖完整进化流程
- **MCP Server 双版本**：Python 稳定版 + Evomorph 基因座模块化版（17 基因座）
- **9 个自省 .evo 文件**：AI 模型无需阅读 Python 源码即可理解完整指令集
- **文档全面更新**：版本号统一至 v0.1.0，GitHub 地址更新至 AI-Scarlett/yi-evomorph

### v0.0.7 (2026-05-07)
- C 原生 VM 桥接（CBridgeVM），消除 ~900 行 Python `_step()`
- libichingvm2.dylib 原生 VM 共享库（10/10 测试通过）
- compiler.evoasm 编译器核心完全用 IChing 汇编实现
- 删除 ir.py、PythonEvocCompiler、ASTToIRConverter 等

### v0.0.6 (2026-05-06)
- IChing EVB 自举编译器成为唯一编译路径
- 指令集自省（hexagram_table / categories / modifiers .evo）
- 象辞模板库扩展至 24 个编程模板
- 数据模块 .evo 化（niche_data / opcode_cost / evomon）

### v0.0.3 ~ v0.0.5 (2026-05-04)
- Evomorph 版 MCP Server、进化引擎、原生 C VM 运行时
- ExtendedIChingVM2 (32 寄存器, 双指令集)
- 自举编译器引导（self_compile / continuous_bootstrap）

## License

MIT
