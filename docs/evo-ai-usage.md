# 易衍·Evomorph — evo-ai CLI 使用手册

## 概述

`evo-ai` 是易衍·Evomorph 编程语言的 AI 编程命令行工具。进入后直接用自然语言描述需求，由大语言模型自动生成 `.evo` 源代码，并在终端中完成编译、运行和进化优化。

## 启动

```bash
evo-ai
```

> 首次使用需先 `source ~/.zshrc` 使别名生效。也可用 `python3 evomorph/cli/evo_ai.py` 启动。

## 核心交互规则

| 输入 | 行为 |
|------|------|
| 不带 `/` 的文字 | 发给 AI，生成 .evo 代码 |
| `/` 开头的命令 | 执行操作（编译/运行/配置等） |
| `/` 后按 Tab | 自动补全命令 |
| 命令拼错 | 自动建议正确命令 |

## 提示符说明

```
易衍 deepseek deepseek-chat●>
     ↑厂商      ↑模型        ↑●=Key已配置 ○=未配置
```

## 命令总览

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

---

## 1. 配置大模型

### 方式一：预设厂商（推荐）

```
/providers                ← 列出厂商
/provider deepseek        ← 切换厂商
/apikey sk-your-key       ← 设置 API Key
/models                   ← 从厂商 API 动态拉取可用模型
/model deepseek-chat      ← 选择模型
```

### 方式二：一行自定义

```
/custom <API_URL> <API_KEY> <模型ID>
```

示例：
```
/custom https://api.deepseek.com/v1 sk-xxx deepseek-chat
/custom https://api.openai.com/v1 sk-xxx gpt-4o
/custom http://localhost:11434/v1 none qwen2.5-coder
```

### 方式三：交互式自定义

```
/custom
```

然后逐步填写 API URL、API Key、模型 ID。

### 查看当前配置

```
/status
```

输出：
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

### 支持的厂商

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

---

## 2. 自然语言编程

直接输入自然语言，AI 生成 .evo 代码：

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
```

---

## 3. 编译 / 运行 / 进化

```
/compile              ← 编译上次生成的代码
/compile app.evo      ← 编译指定文件

/run                  ← 运行上次生成的代码
/run app.evo          ← 运行指定文件

/evolve               ← 进化编译上次生成的代码
/evolve app.evo       ← 进化编译指定文件
```

每个操作完成后都有下一步提示。

---

## 4. 查询与查看

```
/lookup CREA          ← 查询卦象指令
/lookup ䷀             ← 支持符号/助记符/拼音
/platforms            ← 列出可用目标平台
```

---

## 5. 文件操作

```
/new app              ← 新建 app.evo
/open app.evo         ← 打开文件
/save app.evo         ← 保存上次生成的代码
```

---

## 6. 单次命令模式（不进入交互）

```bash
evo-ai compile xxx.evo
evo-ai run xxx.evo
evo-ai evolve xxx.evo
evo-ai lookup CREA
evo-ai platforms
evo-ai config
```

---

## 7. 离线模式

未配置 API Key 时自动使用本地模板引擎（XiangciSDK），通过关键词匹配生成基础 .evo 代码。配置 API Key 后由大模型生成更精确的代码。

---

## 8. 配置文件

位置：`~/.evomorph/config.json`

| 键 | 说明 | 默认值 |
|----|------|--------|
| `api_url` | LLM API 地址 | DeepSeek |
| `api_key` | API 密钥 | 空 |
| `model` | 模型 ID | deepseek-chat |
| `max_tokens` | 最大生成 token | 2048 |
| `temperature` | 生成温度 | 0.7 |
| `default_platforms` | 默认目标平台 | ["linux-6.x"] |
| `default_generations` | 默认进化代数 | 50 |
| `default_population` | 默认种群大小 | 32 |
