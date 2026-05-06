# 易衍·Evomorph — 编译与安装说明

## 环境要求

- Python 3.9+
- 无额外第三方依赖（核心功能使用标准库）

---

## 安装方式

### 方式一：从 Git 仓库安装（推荐）

在任意机器上，无需预先下载源码：

```bash
pip install git+https://github.com/<your-org>/evomorph.git
```

安装完成后，`evo-ai` 命令即可直接使用：

```bash
evo-ai
```

### 方式二：从源码安装

```bash
git clone https://github.com/<your-org>/evomorph.git
cd evomorph
pip install .
```

### 方式三：从 wheel 文件安装

先在开发机构建 wheel：

```bash
cd evomorph
pip install build
python3 -m build
```

构建产物在 `dist/` 目录下：
- `evomorph-0.0.6-py3-none-any.whl` — wheel 包（跨平台）
- `evomorph-0.0.6.tar.gz` — 源码包

将 `.whl` 文件拷贝到目标机器后安装：

```bash
pip install evomorph-0.0.6-py3-none-any.whl
```

### 方式四：开发模式安装

适合开发者，修改源码后无需重新安装：

```bash
cd evomorph
pip install -e .
```

### 方式五：无需安装，直接运行

适合有源码但不希望安装到系统的情况：

```bash
cd evomorph
python3 evomorph/cli/evo_ai.py
```

---

## 验证安装

```bash
evo-ai help
evo-ai platforms
evo-ai lookup CREA
```

如果以上命令正常输出，说明安装成功。

---

## 快速开始

### 1. 启动 AI 编程环境

```bash
evo-ai
```

进入后配置大模型即可使用：

```
/provider deepseek        ← 切换厂商
/apikey sk-your-key       ← 设置 API Key
/models                   ← 拉取可用模型
/model deepseek-chat      ← 选模型
```

### 2. 提示符说明

```
易衍 deepseek deepseek-chat●>
     ↑厂商      ↑模型        ↑●=Key已配置 ○=未配置
```

---

## 构建发布包

### 构建 wheel 和源码包

```bash
pip install build
python3 -m build
```

### 发布到 PyPI（可选）

```bash
pip install twine
twine upload dist/*
```

发布后，任何人都可以通过以下命令安装：

```bash
pip install evomorph
```

---

## 项目结构

```
evomorph/
├── evo-ai                        # 快捷启动脚本
├── evomorph/
│   ├── cli/
│   │   └── evo_ai.py             # AI 编程 CLI（交互式 Shell）
│   ├── prompts/
│   │   └── system_prompt.md      # LLM 系统提示词（打包内嵌）
│   ├── lsp/
│   │   └── language_server.py    # LSP 语言服务器
│   ├── compiler/
│   │   ├── __init__.py           # IChingEvocCompiler 主编译路径
│   │   ├── lexer.py              # 词法分析器 (legacy)
│   │   ├── parser.py             # 语法分析器 (legacy)
│   │   └── codegen.py            # 代码生成器 (legacy)
│   ├── vm/
│   │   └── virtual_machine.py    # IChingVM 卦象虚拟机
│   ├── evolution/
│   │   └── engine.py             # 进化引擎（遗传算法）
│   ├── hexagrams/
│   │   ├── __init__.py             # 指令集模块入口，export_evo_heap_data()
│   │   ├── instruction_set.py      # 六十四卦指令集
│   │   ├── hexagram_table.evo      # 64卦指令集自省表 (273行)
│   │   ├── categories.evo          # 卦象四类分组 (170行)
│   │   └── modifiers.evo           # 修饰符标志定义 (130行)
│   ├── simulator/
│   │   ├── niche.py                # 平台模拟生态位
│   │   ├── niche_data.evo          # 5个平台性能数据 (100+行)
│   │   └── opcode_cost.evo         # 操作码成本映射 (60+行)
│   ├── sdk/
│   │   ├── xiangci.py            # 象辞翻译 SDK
│   │   ├── xiangci_data.evo      # 象辞模板数据 (69行)
│   │   └── xiangci_templates.evo # 24个象辞编程模板 (200+行)
│   ├── bootstrap/                # 自举编译器（.evo 格式）
│   ├── native/                   # 原生模块（链接器/加载器/Shell/REPL）
│   ├── stdlib/                   # 标准库（.evo 格式）
│   ├── debugger/                 # 爻镜调试器
│   ├── monitor/
│   │   └── evomon.evo            # 性能监控基因座 (90+行)
│   └── hub/                      # 基因座仓库
├── ai/
│   ├── mcp/
│   │   ├── evomorph_mcp_server.py # MCP Server
│   │   └── mcp_config.json       # MCP 配置
│   ├── prompts/
│   │   └── system_prompt.md      # LLM 系统提示词（开发用）
│   └── configs/                  # AI 工具配置（Hermes/CodeBuddy/Codex）
├── examples/                     # 示例 .evo 文件
├── tests/                        # 测试
├── tools/
│   ├── evoc                      # evoc 编译器脚本
│   └── yistudio/                 # TRAE/VS Code 扩展（易衍工作室）
├── docs/                         # 文档
├── .trae/rules/project_rules.md  # TRAE 项目规则
├── .cursorrules                  # Cursor 规则
├── pyproject.toml                # 项目配置
├── setup.py                      # 安装配置
└── MANIFEST.in                   # 打包清单
```

---

## CLI 命令

### 交互模式（默认）

输入 `evo-ai` 进入交互式 Shell：

- 不带 `/` 的文字 → 发给 AI 生成代码
- `/` 开头 → 执行命令
- `/` 后按 Tab → 自动补全

常用命令：

```
/provider deepseek    切换厂商
/models               拉取可用模型
/model xxx            切换模型
/custom               自定义大模型
/apikey sk-xxx        设置 API Key
/status               查看配置
/compile              编译
/run                  运行
/evolve               进化编译
/save xxx.evo         保存
/quit                 退出
```

### 单次命令模式

```bash
evo-ai compile xxx.evo
evo-ai run xxx.evo
evo-ai evolve xxx.evo
evo-ai lookup CREA
evo-ai platforms
evo-ai config
```

---

## 配置 AI 编程

### 方式一：预设厂商

```
/provider deepseek
/apikey sk-your-key
/models
/model deepseek-chat
```

### 方式二：一行自定义

```
/custom https://api.deepseek.com/v1 sk-xxx deepseek-chat
```

### 方式三：交互式自定义

```
/custom
```

### 支持的厂商

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

> 模型列表通过 `/models` 从厂商 API 动态拉取，不硬编码。

### 配置文件位置

`~/.evomorph/config.json`

---

## 运行测试

```bash
python3 -m pytest tests/ -v
```

---

## 故障排除

### 安装后 evo-ai 命令找不到

- 确认 Python 的 Scripts 目录在 PATH 中
- 尝试 `python3 -m evomorph.cli.evo_ai` 直接运行
- 或使用 `python3 -c "from evomorph.cli.evo_ai import main; main()"`

### 编译失败

- 检查 `.evo` 文件是否以 `@evolang "3.0"` 开头
- 检查卦序中的指令格式是否正确
- 在交互模式中用 `/compile` 查看详细错误

### LLM 调用失败

- 用 `/status` 检查配置是否正确
- 检查 API Key 是否有效
- 未配置 API Key 时自动使用本地模板模式

### VM 运行异常

- 查看非零寄存器值判断执行状态
- 使用爻镜调试器（`evomorph.debugger.yaojing`）进行调试
