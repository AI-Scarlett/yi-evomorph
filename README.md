# 易衍 · Evomorph

**六十四卦指令集 · 进化编程 · AI 驱动**

易衍（Evomorph）是一种基于《易经》六十四卦的进化编程语言。每条指令的操作码等于其对应卦象的六爻二进制值，代码通过遗传算法自动进化优化，适应不同目标平台。

## 特性

- **六十四卦指令集** — 操作码 = 爻位二进制，元亨利贞四大类 64 条指令
- **基因座（Locus）** — 代码基本单元，包含指令序列和进化元数据
- **象辞（Xiangci）** — 自然语言描述程序意图，AI 翻译为卦象指令
- **进化编译** — 遗传算法自动优化代码，适应目标平台
- **IChingVM** — 卦象虚拟机，执行 EVB 字节码
- **AI 驱动** — 内置 11 家大模型厂商支持，自然语言直接生成 .evo 代码
- **交互式 CLI** — 下拉菜单命令选择，上下键导航，回车确认

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
│   ├── cli/evo_ai.py             # AI 编程 CLI（交互式 Shell）
│   ├── prompts/system_prompt.md  # LLM 系统提示词
│   ├── lsp/language_server.py    # LSP 语言服务器
│   ├── compiler/                 # EvocCompiler 编译器
│   ├── vm/virtual_machine.py     # IChingVM 卦象虚拟机
│   ├── evolution/engine.py       # 进化引擎（遗传算法）
│   ├── hexagrams/instruction_set.py  # 六十四卦指令集
│   ├── simulator/niche.py        # 平台模拟生态位
│   ├── sdk/xiangci.py            # 象辞翻译 SDK
│   ├── stdlib/                   # 标准库（.evo 格式）
│   └── debugger/                 # 爻镜调试器
├── ai/
│   ├── mcp/evomorph_mcp_server.py  # MCP Server
│   └── prompts/system_prompt.md    # 系统提示词
├── tools/yistudio/              # TRAE/VS Code 扩展
├── docs/                        # 文档
├── examples/                    # 示例 .evo 文件
├── tests/                       # 测试
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

## License

MIT
