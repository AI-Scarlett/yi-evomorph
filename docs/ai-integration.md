# 易衍·Evomorph — AI 工具集成指南

## 概述

易衍·Evomorph 通过 MCP (Model Context Protocol) 协议与各类 AI 编程工具集成，实现自然语言驱动的易衍编程。所有 AI 工具共享同一个 MCP Server，提供编译、运行、进化、查询等标准工具接口。同时，evo-ai CLI 提供独立的交互式 AI 编程环境，内置 11 家大模型厂商支持，可动态拉取模型列表，也支持自定义大模型。

## 核心架构

```
┌─────────────────────────────────────────────┐
│              AI 编程工具                      │
│  (TRAE / Cursor / OpenClaw / Hermes /       │
│   CodeBuddy / Codex / evo-ai CLI)           │
└──────────────┬──────────────────────────────┘
               │ MCP 协议 / 系统提示词 / 项目规则
               ▼
┌─────────────────────────────────────────────┐
│         evomorph_mcp_server.py               │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐     │
│  │compile  │ │xiangci   │ │evolve    │     │
│  └─────────┘ └──────────┘ └──────────┘     │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐     │
│  │run      │ │lookup    │ │platforms │     │
│  └─────────┘ └──────────┘ └──────────┘     │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  EvocCompiler │ IChingVM │ EvolutionEngine  │
│  XiangciSDK   │ PlatformSimNiche            │
└─────────────────────────────────────────────┘
```

### 📦 小模型友好设计

易衍·Evomorph 专为小模型（3B/4B 参数、4K-8K 上下文）AI 驱动编程优化。AI 模型通过读取以下 9 个自省 `.evo` 文件即可理解完整的语言能力，无需阅读数万行 Python 源码：

| 文件 | 大小 | 用途 |
|------|------|------|
| `evomorph/hexagrams/hexagram_table.evo` | 273行 | 完整64卦指令表，支持运行时自省查询 |
| `evomorph/hexagrams/categories.evo` | 170行 | 四类卦象分组（元/亨/利/贞） |
| `evomorph/hexagrams/modifiers.evo` | 130行 | 6种修饰符标志定义 |
| `evomorph/sdk/xiangci_templates.evo` | 200+行 | 24个预定义编程模式模板 |
| `evomorph/sdk/xiangci_data.evo` | 69行 | 象辞模板数据 |
| `evomorph/native/bytecode_utils.evo` | 132行 | 字节码编解码 |
| `evomorph/simulator/niche_data.evo` | 100+行 | 5个平台性能数据 |
| `evomorph/simulator/opcode_cost.evo` | 60+行 | 操作码成本分类映射 |
| `evomorph/monitor/evomon.evo` | 90+行 | 性能监控基因座 |

> 这 9 个文件替代了约 1700 行已删除的 Python 编译器代码和大量 Python 配置逻辑，使小模型在有限上下文内即可完全理解 Evomorph。`EVO_INTROSPECTION_FILES` 常量在 `evomorph/__init__.py` 中定义。

---

## MCP Server

### 双版本实现

易衍·Evomorph 提供双版本 MCP Server，供不同场景使用：

#### 1. Python版（稳定推荐）

**位置**：`ai/mcp/evomorph_mcp_server.py`

**特点：
- 稳定可靠，经过充分测试
- 完整支持所有6个工具
- 适合生产环境使用

#### 2. Evomorph版（基因座模块化）

**位置**：`ai/mcp/evomorph_mcp_server.evo`

**特点**：
- 用易衍·Evomorph语言原生实现
- 基因座模块化架构，支持进化优化
- 包含17个基因座（3个元基因座 + 14个功能基因座）
- 展示六十四卦指令集的实际应用
- 适合学习和理解易衍语言

### 传输协议

Stdio（标准输入/输出），JSON-RPC 2.0

### 配置文件

`ai/mcp/mcp_config.json`

```json
{
    "mcpServers": {
        "evomorph": {
            "command": "python3",
            "args": ["/path/to/evomorph/ai/mcp/evomorph_mcp_server.py"],
            "transport": "stdio"
        }
    }
}
```

### Evomorph版MCP Server架构

```
@meta_locus
├── mcp.global_config          # 全局配置
├── mcp.evolution.strategy     # 进化策略
└── mcp.optimization.target    # 优化目标

@locus
├── mcp.io.read_line           # IO读取
├── mcp.io.write_line          # IO写入
├── mcp.request.parse          # 请求解析
├── mcp.request.route          # 请求路由
├── mcp.response.initialize    # 初始化响应
├── mcp.response.tools_list    # 工具列表响应
├── mcp.response.build         # 构建响应
├── mcp.response.build_error   # 构建错误响应
├── mcp.tool.compile           # 编译工具
├── mcp.tool.xiangci           # 象辞翻译工具
├── mcp.tool.evolve            # 进化编译工具
├── mcp.tool.run               # 运行工具
├── mcp.tool.lookup_hexagram   # 查询卦象工具
├── mcp.tool.list_platforms     # 列出平台工具
├── mcp.tools.call.dispatch    # 工具分发
└── mcp.main.loop            # 主循环
```

### 提供的工具

| 工具名 | 功能 | 输入参数 |
|--------|------|----------|
| `evomorph_compile` | 编译 .evo 源码 | `source` (必填), `format` (json/dict) |
| `evomorph_xiangci` | 象辞翻译：自然语言→卦象指令 | `text` (必填), `target_platforms` |
| `evomorph_evolve` | 进化编译 | `source` (必填), `generations`, `population_size`, `target_platforms` |
| `evomorph_run` | 在 IChingVM 上运行 | `source` (必填), `max_cycles` |
| `evomorph_lookup_hexagram` | 查询卦象指令 | `query` (必填) |
| `evomorph_list_platforms` | 列出可用平台 | (无) |

### 调用示例

```json
// 初始化
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}

// 列出工具
{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

// 编译
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "evomorph_compile", "arguments": {"source": "@evolang \"3.0\"\n@locus test { mut_rate = 0.02\nfitness = min_latency\nenv_target = [\"linux-6.x\"]\n卦序: { CREA R0, R1 SYNC } }", "format": "json"}}}

// 查询卦象
{"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "evomorph_lookup_hexagram", "arguments": {"query": "CREA"}}}
```

---

## 各 AI 工具配置

### 1. TRAE

**配置文件**：`.trae/rules/project_rules.md`

TRAE 自动读取项目规则文件，理解易衍语法和概念。

**配置步骤**：
1. 项目规则文件已存在于 `.trae/rules/project_rules.md`
2. 在 TRAE 设置中添加 MCP Server 配置，指向 `ai/mcp/mcp_config.json`
3. 直接在 TRAE 中用自然语言描述需求

**使用方式**：
```
你：帮我写一个并行求和程序，适配Linux和鸿蒙
TRAE：自动生成完整的 .evo 文件
```

### 2. Cursor

**配置文件**：`.cursorrules`

Cursor 自动读取 `.cursorrules` 文件。

**配置步骤**：
1. `.cursorrules` 已存在于项目根目录
2. 在 Cursor 设置中添加 MCP Server 配置
3. 直接编写 `.evo` 文件，AI 会根据规则辅助

### 3. OpenClaw

**配置步骤**：
1. 将 `ai/mcp/mcp_config.json` 的内容添加到 OpenClaw 的 MCP 服务器配置
2. 确保路径指向本地的 `evomorph_mcp_server.py`

**使用方式**：
通过 MCP 协议调用工具：
- `evomorph_xiangci(text="并行求和，适安卓与鸿蒙", target_platforms=["android-14", "harmony-5"])`
- `evomorph_compile(source="...")`
- `evomorph_run(source="...")`

### 4. Hermes

**配置文件**：`ai/configs/hermes.json`

**配置步骤**：
1. 在 Hermes 项目设置中导入 `hermes.json`
2. 将 `ai/prompts/system_prompt.md` 设为系统提示词来源
3. 配置 MCP Server 连接

**hermes.json 结构**：
```json
{
    "project": { "name": "易衍·Evomorph", "language": "evomorph", "version": "0.0.7" },
    "hermes": {
        "system_prompt_source": "ai/prompts/system_prompt.md",
        "rules_files": [".trae/rules/project_rules.md", ".cursorrules"],
        "mcp_integration": {
            "server_script": "ai/mcp/evomorph_mcp_server.py",
            "config": "ai/mcp/mcp_config.json"
        },
        "build_commands": {
            "compile": "python3 tools/evoc compile {input} -f evb -o {output}",
            "run": "python3 tools/evoc run {input}",
            "evolve": "python3 tools/evoc evolve {input} -g {generations} -v"
        }
    }
}
```

### 5. CodeBuddy

**配置文件**：`ai/configs/codebuddy.json`

**配置步骤**：
1. 将 `codebuddy.json` 内容添加到 CodeBuddy 的项目配置
2. 确保 MCP Server 路径正确

**codebuddy.json 结构**：
```json
{
    "context": {
        "language": "易衍·Evomorph",
        "version": "0.0.7",
        "file_extensions": [".evo"],
        "key_concepts": {
            "opcode_equals_yao_binary": "操作码等于卦象爻位二进制值",
            "locus": "基因座，代码基本单元",
            "xiangci": "象辞，自然语言意图描述",
            "evolutionary_compilation": "进化编译，遗传算法优化代码"
        }
    },
    "rules": [
        "每个 .evo 文件以 @evolang \"3.0\" 开头",
        "使用 @xiangci 块描述程序意图",
        "使用 @locus 定义基因座，必须包含 mut_rate/fitness/env_target"
    ],
    "commands": {
        "compile": "python3 tools/evoc compile input.evo -f evb",
        "run": "python3 tools/evoc run input.evo",
        "evolve": "python3 tools/evoc evolve input.evo -g 50 -v"
    },
    "mcp_server": {
        "enabled": true,
        "config_path": "ai/mcp/mcp_config.json"
    }
}
```

### 6. Codex (OpenAI)

**配置文件**：`ai/configs/codex.json`

**配置步骤**：
1. 在 Codex 的 model customizations 中导入 `codex.json`
2. 设置 `system_prompt_file` 指向 `ai/prompts/system_prompt.md`
3. 配置 MCP 端点

**codex.json 结构**：
```json
{
    "model_customizations": {
        "system_prompt_file": "ai/prompts/system_prompt.md",
        "supported_languages": ["evomorph"],
        "file_extensions": [".evo"],
        "evomorph": {
            "syntax": "卦象符号 + 助记符 + 操作数",
            "opcode_scheme": "yao_binary",
            "compilation": "evolutionary",
            "runtime": "IChingVM"
        }
    },
    "tools": [
        { "name": "evomorph_compile", "endpoint": "mcp://evomorph/evomorph_compile" },
        { "name": "evomorph_xiangci", "endpoint": "mcp://evomorph/evomorph_xiangci" },
        { "name": "evomorph_evolve", "endpoint": "mcp://evomorph/evomorph_evolve" },
        { "name": "evomorph_run", "endpoint": "mcp://evomorph/evomorph_run" },
        { "name": "evomorph_lookup_hexagram", "endpoint": "mcp://evomorph/evomorph_lookup_hexagram" }
    ],
    "mcp_config": {
        "servers": {
            "evomorph": {
                "command": "python3",
                "args": ["ai/mcp/evomorph_mcp_server.py"],
                "transport": "stdio"
            }
        }
    }
}
```

### 7. evo-ai CLI

**位置**：`evomorph/cli/evo_ai.py` 或通过 `evo-ai` 别名启动

evo-ai 是独立的交互式 AI 编程环境，内置 MCP Server 的所有功能，无需额外配置 MCP 协议。它直接调用大模型 API 生成 .evo 代码，并提供编译、运行、进化等操作。

#### 启动

```bash
evo-ai
```

> 首次使用需先 `source ~/.zshrc` 使别名生效。也可用 `python3 evomorph/cli/evo_ai.py` 启动。

#### 交互规则

| 输入 | 行为 |
|------|------|
| 不带 `/` 的文字 | 发给 AI，生成 .evo 代码 |
| `/` 开头的命令 | 执行操作（编译/运行/配置等） |
| `/` 后按 Tab | 自动补全命令 |
| 命令拼错 | 自动建议正确命令 |

#### 提示符说明

```
易衍 deepseek deepseek-chat●>
     ↑厂商      ↑模型        ↑●=Key已配置 ○=未配置
```

#### 配置大模型

**方式一：预设厂商（推荐）**

```
/providers                ← 列出所有厂商
/provider deepseek        ← 切换厂商
/apikey sk-your-key       ← 设置 API Key
/models                   ← 从厂商 API 动态拉取可用模型
/model deepseek-chat      ← 选择模型
```

**方式二：一行自定义**

```
/custom <API_URL> <API_KEY> <模型ID>
```

示例：
```
/custom https://api.deepseek.com/v1 sk-xxx deepseek-chat
/custom https://api.openai.com/v1 sk-xxx gpt-4o
/custom http://localhost:11434/v1 none qwen2.5-coder
```

**方式三：交互式自定义**

```
/custom
```

然后逐步填写 API URL、API Key、模型 ID。

#### 支持的厂商

| 简称 | 厂商 | API 地址 |
|------|------|----------|
| `openai` | OpenAI | api.openai.com/v1 |
| `anthropic` | Anthropic (Claude) | api.anthropic.com/v1 |
| `deepseek` | DeepSeek | api.deepseek.com/v1 |
| `mistral` | Mistral (Codestral) | codestral.mistral.ai/v1 |
| `alibaba` | 阿里云 (通义千问) | dashscope.aliyuncs.com |
| `zhipu` | 智谱 (CodeGeeX) | open.bigmodel.cn |
| `moonshot` | 月之暗面 (Kimi) | api.moonshot.cn/v1 |
| `minimax` | MiniMax | api.minimax.chat/v1 |
| `volcengine` | 火山引擎 (豆包/ARK) | ark.cn-beijing.volces.com |
| `z-ai` | z.ai | api.z.ai/v1 |
| `ollama` | Ollama (本地) | localhost:11434/v1 |

> 模型列表通过 `/models` 从厂商 API 动态拉取，不硬编码，厂商出新模型立即可见。

#### 查看配置状态

```
/status
```

输出示例：
```
═══════════════════════════════════════
  易衍·Evomorph 当前配置状态
═══════════════════════════════════════
  厂商:     DeepSeek
  模型:     deepseek-chat
  API Key:  已配置 (sk-x...xxxx)
  API 地址: https://api.deepseek.com/v1/chat/completions
  目标平台: linux-6.x

  ✓ 配置完成

  💡 下一步: 直接用自然语言描述你想写的程序
```

#### 常用命令

| 命令 | 功能 |
|------|------|
| `/provider <名称>` | 切换厂商 |
| `/providers` | 列出所有厂商 |
| `/models` | 从厂商 API 动态拉取可用模型 |
| `/model <名称>` | 切换模型 |
| `/custom` | 自定义大模型（手动填 URL + Key + 模型ID） |
| `/apikey <key>` | 设置 API Key |
| `/status` | 查看配置状态 |
| `/compile [文件]` | 编译代码 |
| `/run [文件]` | 运行代码 |
| `/evolve [文件]` | 进化编译 |
| `/lookup <卦名>` | 查询卦象指令 |
| `/platforms` | 列出可用平台 |
| `/new [名称]` | 新建 .evo 文件 |
| `/open <文件>` | 打开 .evo 文件 |
| `/save [文件]` | 保存代码 |
| `/history` | 查看对话历史 |
| `/clear` | 清空对话 |
| `/config` | 查看完整配置 |
| `/help` | 显示帮助 |
| `/quit` | 退出 |

#### 单次命令模式

不进入交互模式，直接执行单条命令：

```bash
evo-ai compile xxx.evo
evo-ai run xxx.evo
evo-ai evolve xxx.evo
evo-ai lookup CREA
evo-ai platforms
evo-ai config
```

#### 离线模式

未配置 API Key 时自动使用本地模板引擎（XiangciSDK），通过关键词匹配生成基础 .evo 代码。配置 API Key 后由大模型生成更精确的代码。

详细使用说明见 [evo-ai 使用手册](evo-ai-usage.md)。

---

## 系统提示词

**位置**：`ai/prompts/system_prompt.md`

系统提示词是所有 AI 工具理解易衍语言的核心。它包含：
- 语言核心概念（操作码=爻位二进制、基因座、象辞、进化编译）
- 常用指令速查表
- 输出格式要求（.evo 文件结构）
- 适应度表达式规则
- 平台选择指南

所有 AI 工具在生成易衍代码时，都应参考此提示词。

---

## AI 编程工作流

无论使用哪个 AI 工具，核心工作流相同：

```
自然语言需求 → 象辞翻译(@xiangci) → 卦象指令选择 → .evo代码生成 → 编译 → (可选)进化优化 → 运行
```

### 步骤详解

1. **描述意图**：用自然语言告诉 AI 你要做什么
2. **AI 生成 .evo 代码**：AI 自动撰写象辞、选择卦象指令、设定进化参数
3. **编译验证**：通过 MCP 调用 `evomorph_compile` 检查语法
4. **进化优化**（可选）：调用 `evomorph_evolve` 进行遗传算法优化
5. **运行测试**：调用 `evomorph_run` 在 IChingVM 上执行

### evo-ai CLI 工作流示例

```
易衍 deepseek deepseek-chat●> 写一个并行求和程序，适配Linux和鸿蒙
⟐ 思考中...
═══════════════════════════════════════
  生成的 .evo 代码
═══════════════════════════════════════
@evolang "3.0"
@xiangci { "并行计算1到N的整数之和" }
@locus parallel_sum { ... }
═══════════════════════════════════════

  💡 下一步:
     /compile  — 编译验证代码
     /run      — 在虚拟机上运行
     /evolve   — 进化编译优化
     /save xxx — 保存到 .evo 文件
     或继续用自然语言修改需求

易衍 deepseek deepseek-chat●> /compile
✓ 编译通过

易衍 deepseek deepseek-chat●> /run
✓ 运行完成

易衍 deepseek deepseek-chat●> /evolve
✓ 进化完成

易衍 deepseek deepseek-chat●> /save parallel_sum.evo
✓ 已保存到 parallel_sum.evo
```

---

## 文件索引

| 文件 | 用途 |
|------|------|
| `evomorph/cli/evo_ai.py` | evo-ai CLI 交互式 AI 编程环境 |
| `ai/mcp/evomorph_mcp_server.py` | Python版 MCP Server（稳定推荐） |
| `ai/mcp/evomorph_mcp_server.evo` | Evomorph版 MCP Server（基因座模块化） |
| `ai/mcp/mcp_config.json` | MCP 配置 |
| `ai/prompts/system_prompt.md` | LLM 系统提示词 |
| `ai/configs/hermes.json` | Hermes 配置 |
| `ai/configs/codebuddy.json` | CodeBuddy 配置 |
| `ai/configs/codex.json` | Codex 配置 |
| `evomorph/hexagrams/hexagram_table.evo` | 64卦指令集自省表 |
| `evomorph/hexagrams/categories.evo` | 四类卦象分组 |
| `evomorph/hexagrams/modifiers.evo` | 修饰符标志定义 |
| `evomorph/sdk/xiangci_templates.evo` | 24个象辞编程模板 |
| `evomorph/sdk/xiangci_data.evo` | 象辞模板数据 |
| `evomorph/simulator/niche_data.evo` | 平台性能数据 |
| `evomorph/simulator/opcode_cost.evo` | 操作码成本映射 |
| `evomorph/monitor/evomon.evo` | 性能监控基因座 |
| `evomorph/evolution/evolution_core.evo` | Evomorph版进化引擎核心 |
| `evomorph/evolution/evolution_meta.evo` | Evomorph版元基因座（进化之进化） |
| `evomorph/stdlib/evolution.evo` | 标准库进化模块 |
| `.trae/rules/project_rules.md` | TRAE 项目规则 |
| `.cursorrules` | Cursor 规则 |
| `docs/evo-ai-usage.md` | evo-ai CLI 使用手册 |
| `docs/build-and-install.md` | 编译与安装说明 |

## 版本信息

- 当前版本：**v0.0.7**
- 语言版本：**@evolang "3.0"**
- 发布日期：2026-05-06
