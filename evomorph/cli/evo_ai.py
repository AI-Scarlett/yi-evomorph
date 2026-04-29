import json
import os
import sys
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from evomorph.compiler import EvocCompiler
from evomorph.vm.virtual_machine import IChingVM, VMState
from evomorph.evolution.engine import EvolutionEngine, EvolutionConfig, GeneInstruction
from evomorph.simulator.niche import PlatformSimNiche
from evomorph.hexagrams import HexagramInstructionSet

_SYSTEM_PROMPT_CANDIDATES = [
    PROJECT_ROOT / "ai" / "prompts" / "system_prompt.md",
    Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.md",
]

SYSTEM_PROMPT_PATH = next((p for p in _SYSTEM_PROMPT_CANDIDATES if p.exists()), _SYSTEM_PROMPT_CANDIDATES[-1])
CONFIG_DIR = Path.home() / ".evomorph"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history"

DEFAULT_CONFIG = {
    "api_url": "https://api.openai.com/v1/chat/completions",
    "api_key": "",
    "model": "deepseek-chat",
    "max_tokens": 2048,
    "temperature": 0.7,
    "default_platforms": ["linux-6.x"],
    "default_mut_rate": 0.02,
    "default_generations": 50,
    "default_population": 32,
}

PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
    },
    "anthropic": {
        "name": "Anthropic (Claude)",
        "base_url": "https://api.anthropic.com/v1",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
    },
    "mistral": {
        "name": "Mistral (Codestral)",
        "base_url": "https://codestral.mistral.ai/v1",
    },
    "alibaba": {
        "name": "阿里云 (通义千问)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    "alibaba-token": {
        "name": "阿里云 (通义千问 Token Plan)",
        "base_url": "https://token-plan.cn-beijing.maas.aliyuncs.com/v1",
    },
    "zhipu": {
        "name": "智谱 AI (GLM-4/CodeGeeX)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
    },
    "zhipu-coding": {
        "name": "智谱 AI (GLM Coding Plan)",
        "base_url": "https://open.bigmodel.cn/api/coding/paas/v4",
    },
    "moonshot": {
        "name": "月之暗面 (Kimi)",
        "base_url": "https://api.moonshot.cn/v1",
    },
    "minimax-global": {
        "name": "MiniMax 国际站",
        "base_url": "https://api.minimax.io/v1",
    },
    "minimax-cn": {
        "name": "MiniMax 中国站",
        "base_url": "https://api.minimaxi.chat/v1",
    },
    "volcengine": {
        "name": "火山引擎 (豆包/ARK)",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    },
    "z-ai": {
        "name": "z.ai",
        "base_url": "https://api.z.ai/api/paas/v4",
    },
    "z-ai-coding": {
        "name": "z.ai (GLM Coding Plan)",
        "base_url": "https://api.z.ai/api/coding/paas/v4",
    },
    "ollama": {
        "name": "Ollama (本地)",
        "base_url": "http://localhost:11434/v1",
    },
    "lmstudio": {
        "name": "LM Studio (本地)",
        "base_url": "http://localhost:1234/v1",
    },
    "xiaomi": {
        "name": "小米 (MiMo Token Plan)",
        "base_url": "https://token-plan-cn.xiaominimo.com/v1",
    },
}


def fetch_models(api_url, api_key):
    if not api_key:
        return None
    try:
        import urllib.request
        base = api_url.rstrip("/")
        if base.endswith("/chat/completions"):
            base = base[: -len("/chat/completions")]
        models_url = f"{base}/models"
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        req = urllib.request.Request(models_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = data.get("data", [])
            return sorted([m.get("id", "") for m in models if m.get("id")])
    except Exception:
        return None


def load_config() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        return {**DEFAULT_CONFIG, **saved}
    return dict(DEFAULT_CONFIG)


def save_config(config: Dict[str, Any]):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_system_prompt() -> str:
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    return "你是易衍·Evomorph 编程语言专家。请根据用户需求生成 .evo 源代码。"


def call_llm(config: Dict[str, Any], messages: List[Dict[str, str]]) -> str:
    api_key = config.get("api_key", "")
    api_url = config.get("api_url", "https://api.openai.com/v1/chat/completions")
    model = config.get("model", "gpt-4o")
    max_tokens = config.get("max_tokens", 2048)
    temperature = config.get("temperature", 0.7)

    if not api_key:
        return _local_fallback(messages[-1]["content"], config)

    try:
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except ImportError:
        pass
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"\033[31m[LLM API 错误 {e.code}]\033[0m {body[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"\033[31m[LLM 调用失败]\033[0m {e}", file=sys.stderr)

    return _local_fallback(messages[-1]["content"], config)


def _local_fallback(user_text: str, config: Dict[str, Any]) -> str:
    from evomorph.sdk.xiangci import XiangciSDK
    sdk = XiangciSDK()
    platforms = config.get("default_platforms", ["linux-6.x"])
    translation = sdk.translate(user_text, env_targets=platforms)
    evo_source = sdk.export_to_evo_source(translation)
    return evo_source


def extract_evo_code(llm_output: str) -> str:
    fenced = re.findall(r"```(?:evomorph|evo)?\s*\n(.*?)```", llm_output, re.DOTALL)
    if fenced:
        return fenced[0].strip()
    if llm_output.strip().startswith("@evolang"):
        return llm_output.strip()
    lines = llm_output.strip().split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("@evolang"):
            start = i
            break
    if start is not None:
        return "\n".join(lines[start:]).strip()
    return llm_output.strip()


def do_compile(source: str, fmt: str = "json") -> str:
    compiler = EvocCompiler()
    result = compiler.compile(source, output_format=fmt)
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False, indent=2)


def do_run(source: str, max_cycles: int = 10000) -> str:
    compiler = EvocCompiler()
    ast = compiler.compile(source, output_format="dict")
    loci = ast.get("loci", [])
    if not loci:
        return "错误：未找到基因座"
    locus = loci[0]
    program = []
    for instr in locus.get("instructions", []):
        program.append({
            "opcode": instr.get("opcode", 0),
            "modifier": instr.get("modifier", 0),
            "operands": [op.get("value", 0) if isinstance(op, dict) else op
                         for op in instr.get("operands", [])],
        })
    vm = IChingVM()
    vm.load_program(program)
    vm.register_io_handler(0xFF00, lambda val: None)
    vm.run(max_cycles=max_cycles)
    dump = vm.dump_state()
    return (
        f"状态: {dump['state']}\n"
        f"周期: {dump['cycle_count']}\n"
        f"能耗: {dump['energy_cost']:.2f}\n"
        f"非零寄存器: {json.dumps({k: v for k, v in dump['registers'].items() if v != 0}, ensure_ascii=False)}"
    )


def do_evolve(source: str, generations: int = 50, population: int = 32,
              platforms: Optional[List[str]] = None) -> str:
    compiler = EvocCompiler()
    sim = PlatformSimNiche()
    ast = compiler.compile(source, output_format="dict")
    loci = ast.get("loci", [])
    if not loci:
        return "错误：未找到基因座"
    locus = loci[0]
    seed_genes = []
    for instr in locus.get("instructions", []):
        gene = GeneInstruction(opcode=instr.get("opcode", 0), modifier=instr.get("modifier", 0))
        seed_genes.append(gene)
    config = EvolutionConfig(
        population_size=population,
        max_generations=generations,
        mut_rate=locus.get("mut_rate", 0.02),
        env_targets=platforms or ["linux-6.x"],
    )
    engine = EvolutionEngine(config=config, platform_simulator=sim)
    engine.initialize_population(seed_genes)
    best = engine.evolve()
    if best:
        return (
            f"基因座: {locus['name']}\n"
            f"最佳适应度: {best.fitness:.4f}\n"
            f"最佳个体基因数: {len(best.genes)}\n"
            f"起源: {best.origin}\n"
            f"平台评分: {json.dumps(best.platform_scores, ensure_ascii=False)}"
        )
    return "进化失败"


def do_lookup(query: str) -> str:
    isa = HexagramInstructionSet()
    entry = isa.lookup(query)
    if entry:
        return (
            f"卦象: {entry['symbol']}\n"
            f"助记符: {entry['mnemonic']}\n"
            f"拼音: {entry['pinyin']}\n"
            f"操作码: {entry['opcode']} (十进制) = {entry['binary']} (二进制)\n"
            f"爻位: {entry['yao']}\n"
            f"中文名: {entry['cn_name']}\n"
            f"义理: {entry['description']}"
        )
    return f"未找到匹配 '{query}' 的卦象指令"


def do_list_platforms() -> str:
    sim = PlatformSimNiche()
    lines = []
    for name in sim.list_platforms():
        profile = sim.get_profile(name)
        if profile:
            lines.append(
                f"  {name}: {profile.platform_type.value} v{profile.version}, "
                f"内存延迟={profile.memory_latency_ns}ns, "
                f"线程创建={profile.thread_create_cost}, "
                f"最大线程={profile.max_threads}"
            )
    return "可用目标平台:\n" + "\n".join(lines)


SLASH_COMMANDS = {
    "/provider": "切换厂商",
    "/providers": "列出厂商",
    "/model": "切换模型",
    "/models": "列出可用模型",
    "/custom": "自定义大模型",
    "/apikey": "设置 API Key",
    "/status": "查看配置状态",
    "/compile": "编译代码",
    "/run": "运行代码",
    "/evolve": "进化编译",
    "/lookup": "查询卦象",
    "/platforms": "列出平台",
    "/new": "新建文件",
    "/open": "打开文件",
    "/save": "保存代码",
    "/history": "对话历史",
    "/clear": "清空对话",
    "/config": "查看配置",
    "/help": "显示帮助",
    "/quit": "退出",
}


def _fuzzy_match(typo, candidates, threshold=2):
    best = []
    for c in candidates:
        if len(c) < 2:
            continue
        if typo in c or c in typo:
            best.append(c)
            continue
        dist = _levenshtein(typo, c)
        if dist <= threshold:
            best.append(c)
    return best


def _levenshtein(s1, s2):
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def _build_prompt_str(config, current_file=None):
    model_short = config.get("model", "?")
    if len(model_short) > 20:
        model_short = model_short[:17] + "..."
    provider_short = ""
    cur_url = config.get("api_url", "")
    for k, v in PROVIDERS.items():
        if v["base_url"] in cur_url:
            provider_short = k
            break
    key_mark = "\u25cf" if config.get("api_key") else "\u25cb"
    prompt = "易衍"
    if current_file:
        prompt += f" [{current_file}]"
    if provider_short:
        prompt += f" {provider_short}"
    prompt += f" {model_short}{key_mark}> "
    return prompt


def print_banner():
    print()
    print("\033[36m  ╔═══════════════════════════════════════════════════════╗")
    print("  ║                                                       ║")
    print("  ║   易衍 · Evomorph  v3.0                               ║")
    print("  ║   六十四卦指令集 · 进化编程 · AI 驱动                  ║")
    print("  ║                                                       ║")
    print("  ╠═══════════════════════════════════════════════════════╣")
    print("  ║                                                       ║")
    print("  ║   直接输入自然语言 → AI 生成 .evo 代码               ║")
    print("  ║   输入 / → 弹出命令菜单，上下键选择，回车确认        ║")
    print("  ║                                                       ║")
    print("  ║   常用命令:                                           ║")
    print("  ║     /provider deepseek  切换厂商                      ║")
    print("  ║     /models             拉取可用模型                  ║")
    print("  ║     /model xxx          切换模型                      ║")
    print("  ║     /custom             自定义大模型                  ║")
    print("  ║     /apikey sk-xxx      设置 API Key                  ║")
    print("  ║     /compile            编译代码                      ║")
    print("  ║     /run                运行代码                      ║")
    print("  ║     /evolve             进化编译                      ║")
    print("  ║     /save xxx.evo       保存代码                      ║")
    print("  ║     /help               显示帮助                      ║")
    print("  ║     /quit               退出                          ║")
    print("  ║                                                       ║")
    print("  ╚═══════════════════════════════════════════════════════╝\033[0m")
    print()


try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.formatted_text import FormattedText
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.shortcuts import radiolist_dialog, button_dialog
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False


if HAS_PROMPT_TOOLKIT:
    class EvoCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            if not text.startswith("/"):
                return
            if " " in text:
                parts = text.split(None, 1)
                cmd = parts[0]
                partial = parts[1] if len(parts) > 1 else ""
                if cmd == "/provider":
                    for k, v in PROVIDERS.items():
                        if k.startswith(partial):
                            yield Completion(
                                f"/provider {k}",
                                start_position=-len(text),
                                display=f"/provider {k}",
                                display_meta=v["name"],
                            )
                return
            for cmd, desc in SLASH_COMMANDS.items():
                if cmd.startswith(text):
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display=cmd,
                        display_meta=desc,
                    )


def _get_input_ptk(session, config, current_file):
    prompt_str = _build_prompt_str(config, current_file)
    key_mark = "\033[32m●\033[0m" if config.get("api_key") else "\033[31m○\033[0m"
    model_short = config.get("model", "?")
    if len(model_short) > 20:
        model_short = model_short[:17] + "..."
    provider_short = ""
    cur_url = config.get("api_url", "")
    for k, v in PROVIDERS.items():
        if v["base_url"] in cur_url:
            provider_short = k
            break

    prompt_formatted = FormattedText([
        ("#00ff00 bold", "易衍"),
    ])
    if current_file:
        prompt_formatted.append(("", f" [{current_file}]"))
    if provider_short:
        prompt_formatted.append(("", f" {provider_short}"))
    prompt_formatted.append(("", f" {model_short}"))
    if config.get("api_key"):
        prompt_formatted.append(("#00ff00 bold", "●"))
    else:
        prompt_formatted.append(("#ff0000 bold", "○"))
    prompt_formatted.append(("", "> "))

    try:
        user_input = session.prompt(prompt_formatted).strip()
    except KeyboardInterrupt:
        return None
    except EOFError:
        return "/quit"
    return user_input


def _get_input_basic(config, current_file):
    prompt_str = _build_prompt_str(config, current_file)
    colored = f"\033[32m{prompt_str}\033[0m"
    try:
        user_input = input(colored).strip()
    except KeyboardInterrupt:
        print()
        return None
    except EOFError:
        return "/quit"
    return user_input


def _select_from_list(title, items, cancel_text="取消"):
    if not HAS_PROMPT_TOOLKIT:
        return None
    if not items:
        return None
    choices = [(str(i), label) for i, label in enumerate(items)]
    try:
        result = radiolist_dialog(
            title=title,
            values=choices,
            cancel_text=cancel_text,
        ).run()
    except (KeyboardInterrupt, EOFError):
        return None
    if result is None:
        return None
    return int(result)


def _select_provider(config):
    cur_url = config.get("api_url", "")
    items = []
    cur_idx = 0
    for i, (key, prov) in enumerate(PROVIDERS.items()):
        marker = " ← 当前" if prov["base_url"] in cur_url else ""
        items.append(f"{key:18s} {prov['name']}{marker}")
        if prov["base_url"] in cur_url:
            cur_idx = i
    idx = _select_from_list("选择厂商 (上下键选择，回车确认)", items)
    if idx is None:
        return None
    key = list(PROVIDERS.keys())[idx]
    return key


def _select_model(models, current_model=""):
    if not models:
        return None
    items = []
    cur_idx = 0
    for i, m in enumerate(models):
        marker = " ← 当前" if m == current_model else ""
        items.append(f"{m}{marker}")
        if m == current_model:
            cur_idx = i
    idx = _select_from_list("选择模型 (上下键选择，回车确认)", items)
    if idx is None:
        return None
    return models[idx]


def shell():
    config = load_config()
    system_prompt = load_system_prompt()
    conversation = [{"role": "system", "content": system_prompt}]
    last_evo_code = None
    current_file = None

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if HAS_PROMPT_TOOLKIT:
        history = FileHistory(str(CONFIG_DIR / "history"))
        session = PromptSession(
            completer=EvoCompleter(),
            history=history,
            complete_while_typing=True,
        )
        get_input = lambda: _get_input_ptk(session, config, current_file)
    else:
        get_input = lambda: _get_input_basic(config, current_file)

    print_banner()

    if not config.get("api_key"):
        print("\033[33m  ⚠ 未配置 API Key，使用本地模板模式")
        print("  输入 /apikey <your-key> 配置，或 /models 查看可用模型\033[0m")
        print()

    while True:
        user_input = get_input()
        if user_input is None:
            continue
        if user_input == "/quit":
            print("\033[36m再见！\033[0m")
            break

        if not user_input:
            continue

        if not user_input.startswith("/"):
            conversation.append({"role": "user", "content": user_input})
            print("\033[36m⟐ 思考中...\033[0m")
            llm_output = call_llm(config, conversation)
            evo_code = extract_evo_code(llm_output)
            if evo_code.startswith("@evolang"):
                last_evo_code = evo_code
                print()
                print("\033[32m═══════════════════════════════════════")
                print("  生成的 .evo 代码")
                print("═══════════════════════════════════════\033[0m")
                print(evo_code)
                print("\033[32m═══════════════════════════════════════\033[0m")
                print()
                print("\033[33m  💡 下一步:\033[0m")
                print("\033[33m     /compile  — 编译验证代码\033[0m")
                print("\033[33m     /run      — 在虚拟机上运行\033[0m")
                print("\033[33m     /evolve   — 进化编译优化\033[0m")
                print("\033[33m     /save xxx — 保存到 .evo 文件\033[0m")
                print("\033[33m     或继续用自然语言修改需求\033[0m")
            else:
                print(f"\n{llm_output}")
            conversation.append({"role": "assistant", "content": llm_output})
            if len(conversation) > 30:
                conversation = [conversation[0]] + conversation[-20:]
            continue

        cleaned = user_input
        if cleaned.startswith("/apikey<") and cleaned.endswith(">"):
            cleaned = "/apikey " + cleaned[8:-1]
        if cleaned.startswith("/apikey<") and ">" in cleaned:
            end = cleaned.index(">")
            cleaned = "/apikey " + cleaned[8:end]

        parts = cleaned.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd not in SLASH_COMMANDS:
            close = _fuzzy_match(cmd, SLASH_COMMANDS.keys())
            print(f"\033[31m未知命令: {cmd}\033[0m")
            if close:
                print(f"\033[33m  你是否想输入: {', '.join(close)}\033[0m")
            else:
                print("\033[33m  输入 /help 查看所有命令，或直接输入自然语言让 AI 生成代码\033[0m")
            continue

        elif cmd == "/help":
            cur_model = config.get("model", "未设置")
            cur_key = "已配置" if config.get("api_key") else "未配置"
            print(f"""
\033[36m易衍·Evomorph 命令:\033[0m

  \033[33m不带 / 的文字\033[0m    直接发给 AI，生成 .evo 代码
  \033[33m输入 /\033[0m           弹出命令菜单，上下键选择

  \033[36m── 厂商与模型 ───────────────────────────\033[0m
  \033[33m/provider <名称>\033[0m  切换厂商（如 /provider deepseek）
  \033[33m/providers\033[0m       列出所有厂商
  \033[33m/models\033[0m          从厂商 API 拉取可用模型
  \033[33m/model <名称>\033[0m    切换模型
  \033[33m/custom\033[0m          自定义大模型（手动填 URL + Key + 模型ID）
  \033[33m/apikey <key>\033[0m    设置 API Key
  \033[33m/status\033[0m          查看配置状态

  \033[36m── 编译运行 ─────────────────────────────\033[0m
  \033[33m/compile [文件]\033[0m   编译代码（无文件则编译上次生成的代码）
  \033[33m/run [文件]\033[0m       运行代码（无文件则运行上次生成的代码）
  \033[33m/evolve [文件]\033[0m    进化编译优化

  \033[36m── 查询 ─────────────────────────────────\033[0m
  \033[33m/lookup [卦名]\033[0m    查询卦象指令
  \033[33m/platforms\033[0m        列出可用目标平台

  \033[36m── 文件 ─────────────────────────────────\033[0m
  \033[33m/new [名称]\033[0m       新建 .evo 文件
  \033[33m/open [文件]\033[0m      打开 .evo 文件
  \033[33m/save [文件]\033[0m      保存代码到文件

  \033[36m── 其他 ─────────────────────────────────\033[0m
  \033[33m/history\033[0m          查看对话历史
  \033[33m/clear\033[0m            清空对话历史
  \033[33m/config\033[0m           查看完整配置
  \033[33m/quit\033[0m             退出

\033[36m当前状态:\033[0m  模型={cur_model}  API Key={cur_key}

\033[36m💡 输入 / 弹出命令菜单，上下键选择，回车确认\033[0m
""")

        elif cmd == "/quit":
            print("\033[36m再见！\033[0m")
            break

        elif cmd == "/clear":
            conversation = [{"role": "system", "content": system_prompt}]
            last_evo_code = None
            print("\033[36m✓ 对话已清空\033[0m")

        elif cmd == "/models":
            api_key = config.get("api_key", "")
            api_url = config.get("api_url", "")
            if not api_key:
                print("\033[31m请先设置 API Key: /apikey <your-key>\033[0m")
                continue
            print("\033[36m⟐ 从厂商 API 拉取模型列表...\033[0m")
            models = fetch_models(api_url, api_key)
            if models:
                cur = config.get("model", "")
                if HAS_PROMPT_TOOLKIT:
                    selected = _select_model(models, cur)
                    if selected:
                        config["model"] = selected
                        save_config(config)
                        print(f"\033[36m✓ 模型已切换到 {selected}\033[0m")
                        print()
                        print("\033[33m  💡 下一步: 直接用自然语言描述你想写的程序\033[0m")
                    else:
                        print("\033[33m已取消\033[0m")
                else:
                    print(f"\033[36m可用模型 ({len(models)} 个):\033[0m")
                    print()
                    for m in models:
                        marker = " \033[32m← 当前\033[0m" if m == cur else ""
                        print(f"  \033[33m{m}\033[0m{marker}")
                    print()
                    print(f"  使用 \033[33m/model <模型名>\033[0m 切换")
            else:
                print("\033[31m拉取失败，请检查 API Key 和网络连接\033[0m")
                print("  也可以手动设置: /model <模型名>")

        elif cmd == "/model":
            if not arg:
                cur = config.get("model", "未设置")
                print(f"当前模型: \033[33m{cur}\033[0m")
                print("使用 \033[33m/model <模型名>\033[0m 切换，或 \033[33m/models\033[0m 拉取可用模型")
                continue
            config["model"] = arg
            save_config(config)
            print(f"\033[36m✓ 模型已切换到 {arg}\033[0m")
            if not config.get("api_key"):
                print("\033[33m  ⚠ 需要设置 API Key，输入 /apikey <your-key>\033[0m")
            else:
                print()
                print("\033[33m  💡 下一步: 直接用自然语言描述你想写的程序\033[0m")

        elif cmd == "/providers":
            if HAS_PROMPT_TOOLKIT:
                selected = _select_provider(config)
                if selected:
                    prov = PROVIDERS[selected]
                    config["api_url"] = f"{prov['base_url']}/chat/completions"
                    config["model"] = ""
                    save_config(config)
                    print(f"\033[36m✓ 已切换到 {prov['name']}\033[0m")
                    print(f"  API 地址: {prov['base_url']}")
                    if not config.get("api_key"):
                        print("\033[33m  ⚠ 需要设置 API Key，输入 /apikey <your-key>\033[0m")
                    else:
                        print("\033[33m  ⟐ 自动拉取模型列表...\033[0m")
                        models = fetch_models(config["api_url"], config.get("api_key", ""))
                        if models:
                            model_sel = _select_model(models)
                            if model_sel:
                                config["model"] = model_sel
                                save_config(config)
                                print(f"\033[36m✓ 模型已切换到 {model_sel}\033[0m")
                                print()
                                print("\033[33m  💡 下一步: 直接用自然语言描述你想写的程序\033[0m")
                            else:
                                print("\033[33m  模型未选择，输入 /models 选择模型\033[0m")
                        else:
                            print("\033[33m  拉取失败，输入 /model <名称> 手动设置\033[0m")
                else:
                    print("\033[33m已取消\033[0m")
            else:
                print("\033[36m可用厂商:\033[0m")
                print()
                cur_url = config.get("api_url", "")
                for key, prov in PROVIDERS.items():
                    marker = " \033[32m← 当前\033[0m" if prov["base_url"] in cur_url else ""
                    print(f"  \033[33m{key:15s}\033[0m {prov['name']}{marker}")
                print()
                print("  使用 \033[33m/provider <名称>\033[0m 切换厂商")

        elif cmd == "/provider":
            if not arg:
                cur_url = config.get("api_url", "")
                cur_prov = ""
                for k, v in PROVIDERS.items():
                    if v["base_url"] in cur_url:
                        cur_prov = k
                        break
                print(f"当前厂商: \033[33m{cur_prov or '自定义'}\033[0m")
                print("使用 \033[33m/provider <名称>\033[0m 切换，或 \033[33m/providers\033[0m 查看所有厂商")
                continue
            if arg in PROVIDERS:
                prov = PROVIDERS[arg]
                config["api_url"] = f"{prov['base_url']}/chat/completions"
                config["model"] = ""
                save_config(config)
                print(f"\033[36m✓ 已切换到 {prov['name']}\033[0m")
                print(f"  API 地址: {prov['base_url']}")
                if not config.get("api_key"):
                    print("\033[33m  ⚠ 需要设置 API Key，输入 /apikey <your-key>\033[0m")
                else:
                    print("\033[33m  ⟐ 自动拉取模型列表...\033[0m")
                    models = fetch_models(config["api_url"], config.get("api_key", ""))
                    if models:
                        if HAS_PROMPT_TOOLKIT:
                            model_sel = _select_model(models)
                            if model_sel:
                                config["model"] = model_sel
                                save_config(config)
                                print(f"\033[36m✓ 模型已切换到 {model_sel}\033[0m")
                                print()
                                print("\033[33m  💡 下一步: 直接用自然语言描述你想写的程序\033[0m")
                            else:
                                print("\033[33m  模型未选择，输入 /models 选择模型\033[0m")
                        else:
                            print(f"\033[36m可用模型 ({len(models)} 个):\033[0m")
                            for m in models:
                                print(f"  \033[33m{m}\033[0m")
                            print(f"  使用 \033[33m/model <模型名>\033[0m 切换")
                    else:
                        print("\033[33m  拉取失败，输入 /model <名称> 手动设置\033[0m")
            else:
                print(f"\033[31m未知厂商: {arg}\033[0m")
                print("输入 \033[33m/providers\033[0m 查看所有厂商")
                close = [k for k in PROVIDERS if arg in k]
                if close:
                    print(f"你是否想用: {', '.join(close)}")

        elif cmd == "/custom":
            if arg:
                parts_c = arg.split()
                if len(parts_c) >= 3:
                    url, key, model_id = parts_c[0], parts_c[1], " ".join(parts_c[2:])
                    if not url.endswith("/chat/completions"):
                        url = url.rstrip("/") + "/chat/completions"
                    config["api_url"] = url
                    config["api_key"] = key
                    config["model"] = model_id
                    save_config(config)
                    key_masked = key[:4] + "..." + key[-4:] if len(key) > 8 else "***"
                    print(f"\033[36m✓ 自定义模型已配置\033[0m")
                    print(f"  API URL: {url}")
                    print(f"  API Key: {key_masked}")
                    print(f"  模型 ID: {model_id}")
                    print()
                    print("\033[33m  💡 下一步: 直接用自然语言描述你想写的程序\033[0m")
                else:
                    print("\033[31m用法: /custom <API_URL> <API_KEY> <模型ID>\033[0m")
                    print()
                    print("\033[33m示例:\033[0m")
                    print("  /custom https://api.deepseek.com/v1 sk-xxx deepseek-chat")
                    print("  /custom https://api.openai.com/v1 sk-xxx gpt-4o")
                    print("  /custom http://localhost:11434/v1 none qwen2.5-coder")
                    print()
                    print("\033[33m也可以分步设置:\033[0m")
                    print("  /provider deepseek    ← 选厂商")
                    print("  /apikey sk-xxx        ← 设 Key")
                    print("  /models               ← 拉取模型列表")
                    print("  /model deepseek-chat  ← 选模型")
                continue

            print("\033[36m═══════════════════════════════════════")
            print("  自定义大模型配置")
            print("═══════════════════════════════════════\033[0m")
            print()
            print("  请依次输入 API URL、API Key、模型 ID")
            print()

            try:
                url = input("  \033[33mAPI URL\033[0m (如 https://api.deepseek.com/v1): ").strip()
                key = input("  \033[33mAPI Key\033[0m (如 sk-xxx): ").strip()
                model_id = input("  \033[33m模型 ID\033[0m (如 deepseek-chat): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\033[31m已取消\033[0m")
                continue

            if not url or not model_id:
                print("\033[31mURL 和模型 ID 不能为空\033[0m")
                continue

            if not url.endswith("/chat/completions"):
                url = url.rstrip("/") + "/chat/completions"

            config["api_url"] = url
            config["api_key"] = key
            config["model"] = model_id
            save_config(config)

            key_masked = key[:4] + "..." + key[-4:] if len(key) > 8 else "***"
            print()
            print(f"\033[36m✓ 自定义模型已配置\033[0m")
            print(f"  API URL: {url}")
            print(f"  API Key: {key_masked}")
            print(f"  模型 ID: {model_id}")
            print()
            print("\033[33m  💡 下一步: 直接用自然语言描述你想写的程序\033[0m")

        elif cmd == "/apikey":
            if not arg:
                cur = config.get("api_key", "")
                if cur:
                    print(f"当前 API Key: \033[33m{cur[:8]}...{cur[-4:]}\033[0m")
                else:
                    print("\033[33m未设置 API Key\033[0m")
                print("使用 \033[33m/apikey <your-key>\033[0m 设置")
                continue
            config["api_key"] = arg
            save_config(config)
            masked = arg[:4] + "..." + arg[-4:] if len(arg) > 8 else "***"
            print(f"\033[36m✓ API Key 已设置 ({masked})\033[0m")
            print(f"  当前模型: {config.get('model', '未设置')}")
            print(f"  提示符: \033[32m●\033[0m = Key 已配置  \033[31m○\033[0m = Key 未配置")
            print()
            print("\033[33m  💡 下一步: 直接用自然语言描述你想写的程序\033[0m")

        elif cmd == "/status":
            model_name = config.get("model", "未设置")
            provider_name = ""
            cur_url = config.get("api_url", "")
            for k, v in PROVIDERS.items():
                if v["base_url"] in cur_url:
                    provider_name = v["name"]
                    break
            api_key = config.get("api_key", "")
            api_url = config.get("api_url", "未设置")
            print()
            print("\033[36m═══════════════════════════════════════")
            print("  易衍·Evomorph 当前配置状态")
            print("═══════════════════════════════════════\033[0m")
            print(f"  厂商:     \033[33m{provider_name or '自定义'}\033[0m")
            print(f"  模型:     \033[33m{model_name}\033[0m")
            if api_key:
                print(f"  API Key:  \033[32m已配置\033[0m ({api_key[:4]}...{api_key[-4:]})")
            else:
                print(f"  API Key:  \033[31m未配置\033[0m (输入 /apikey <key> 设置)")
            print(f"  API 地址: {api_url}")
            print(f"  目标平台: {', '.join(config.get('default_platforms', ['linux-6.x']))}")
            if api_key:
                print()
                print("  \033[32m✓ 配置完成\033[0m")
                print()
                print("\033[33m  💡 下一步: 直接用自然语言描述你想写的程序\033[0m")
            else:
                print()
                print("  \033[33m⚠ 未配置 API Key，将使用本地模板模式（功能有限）\033[0m")
                print()
                print("\033[33m  💡 下一步: 输入 /apikey <your-key> 设置 API Key\033[0m")
            print()

        elif cmd == "/history":
            for i, msg in enumerate(conversation[1:], 1):
                role = msg["role"]
                content = msg["content"][:80].replace("\n", " ")
                print(f"  \033[2m[{i}]\033[0m {role}: {content}...")

        elif cmd == "/platforms":
            print(do_list_platforms())

        elif cmd == "/lookup":
            if not arg:
                print("\033[31m用法: lookup <助记符/拼音/符号>\033[0m")
                continue
            print(do_lookup(arg))

        elif cmd == "/config":
            if not arg:
                safe = {k: (v[:8] + "..." if k == "api_key" and v else v) for k, v in config.items()}
                print(json.dumps(safe, ensure_ascii=False, indent=2))
            elif arg.startswith("set "):
                set_parts = arg[4:].split(None, 1)
                if len(set_parts) < 2:
                    print("\033[31m用法: config set <key> <value>\033[0m")
                    continue
                key, value = set_parts
                if key in config:
                    config[key] = value
                    save_config(config)
                    print(f"\033[36m✓ {key} 已更新\033[0m")
                else:
                    print(f"\033[31m未知配置项: {key}\033[0m")
                    print(f"可用项: {', '.join(DEFAULT_CONFIG.keys())}")
            elif arg == "init":
                save_config(config)
                print(f"\033[36m✓ 配置已初始化: {CONFIG_FILE}\033[0m")
            else:
                print("\033[31m用法: config / config set <key> <value>\033[0m")

        elif cmd == "/new":
            filename = arg or "untitled.evo"
            if not filename.endswith(".evo"):
                filename += ".evo"
            template = '@evolang "3.0"\n\n@xiangci {\n\t""\n}\n\n@locus main {\n\tmut_rate   = 0.02\n\tcross_pool = "default"\n\tfitness    = min_latency + 2.0*max_throughput\n\tenv_target = ["linux-6.x"]\n\tmax_generations = 100\n\n\t卦序: {\n\t\t\n\t}\n}\n'
            Path(filename).write_text(template, encoding="utf-8")
            current_file = filename
            last_evo_code = template
            print(f"\033[36m✓ 已创建 {filename}\033[0m")
            print()
            print("\033[33m  💡 下一步: 编辑卦序中的指令，然后 compile 编译\033[0m")

        elif cmd == "/open":
            if not arg:
                print("\033[31m用法: open <文件路径>\033[0m")
                continue
            filepath = Path(arg)
            if not filepath.exists():
                print(f"\033[31m文件不存在: {arg}\033[0m")
                continue
            source = filepath.read_text(encoding="utf-8")
            current_file = arg
            last_evo_code = source
            print(f"\033[36m✓ 已打开 {arg}\033[0m")
            print(source)
            print()
            print("\033[33m  💡 下一步: compile 编译 / run 运行 / evolve 进化\033[0m")

        elif cmd == "/save":
            if not last_evo_code:
                print("\033[31m没有可保存的代码\033[0m")
                continue
            filepath = arg or current_file or "output.evo"
            if not filepath.endswith(".evo"):
                filepath += ".evo"
            Path(filepath).write_text(last_evo_code, encoding="utf-8")
            current_file = filepath
            print(f"\033[36m✓ 已保存到 {filepath}\033[0m")
            print()
            print("\033[33m  💡 下一步: compile 编译 / run 运行 / evolve 进化优化\033[0m")

        elif cmd == "/compile":
            source = None
            if arg:
                filepath = Path(arg)
                if filepath.exists():
                    source = filepath.read_text(encoding="utf-8")
                    current_file = arg
                    last_evo_code = source
            if not source and last_evo_code:
                source = last_evo_code
            if not source:
                print("\033[31m没有可编译的代码，请先生成或打开文件\033[0m")
                continue
            try:
                result = do_compile(source, "json")
                print(result[:600])
                if len(result) > 600:
                    print("...")
                print("\033[33m✓ 编译通过\033[0m")
                print()
                print("\033[33m  💡 下一步: run 运行 / evolve 进化优化\033[0m")
            except Exception as e:
                print(f"\033[31m✗ 编译失败: {e}\033[0m")
                print()
                print("\033[33m  💡 修改代码后重新 compile，或用自然语言重新描述需求\033[0m")

        elif cmd == "/run":
            source = None
            if arg:
                filepath = Path(arg)
                if filepath.exists():
                    source = filepath.read_text(encoding="utf-8")
                    current_file = arg
                    last_evo_code = source
            if not source and last_evo_code:
                source = last_evo_code
            if not source:
                print("\033[31m没有可运行的代码，请先生成或打开文件\033[0m")
                continue
            try:
                result = do_run(source)
                print(result)
                print("\033[35m✓ 运行完成\033[0m")
                print()
                print("\033[33m  💡 下一步: evolve 进化优化 / save 保存代码\033[0m")
            except Exception as e:
                print(f"\033[31m✗ 运行失败: {e}\033[0m")
                print()
                print("\033[33m  💡 检查卦序指令是否正确，或用自然语言重新描述需求\033[0m")

        elif cmd == "/evolve":
            source = None
            if arg:
                filepath = Path(arg)
                if filepath.exists():
                    source = filepath.read_text(encoding="utf-8")
                    current_file = arg
                    last_evo_code = source
            if not source and last_evo_code:
                source = last_evo_code
            if not source:
                print("\033[31m没有可进化的代码，请先生成或打开文件\033[0m")
                continue
            try:
                platforms = config.get("default_platforms", ["linux-6.x"])
                result = do_evolve(source,
                                   generations=config.get("default_generations", 50),
                                   population=config.get("default_population", 32),
                                   platforms=platforms)
                print(result)
                print("\033[34m✓ 进化完成\033[0m")
                print()
                print("\033[33m  💡 下一步: save 保存代码 / run 运行进化后的代码\033[0m")
            except Exception as ex:
                print(f"\033[31m✗ 进化失败: {ex}\033[0m")
                print()
                print("\033[33m  💡 检查代码是否可编译，先 compile 再 evolve\033[0m")

        else:
            conversation.append({"role": "user", "content": user_input})

            print("\033[36m⟐ 思考中...\033[0m")
            llm_output = call_llm(config, conversation)
            evo_code = extract_evo_code(llm_output)

            if evo_code.startswith("@evolang"):
                last_evo_code = evo_code
                print()
                print("\033[32m═══════════════════════════════════════")
                print("  生成的 .evo 代码")
                print("═══════════════════════════════════════\033[0m")
                print(evo_code)
                print("\033[32m═══════════════════════════════════════\033[0m")
                print()
                print("\033[33m  💡 下一步:\033[0m")
                print("\033[33m     compile  — 编译验证代码\033[0m")
                print("\033[33m     run      — 在虚拟机上运行\033[0m")
                print("\033[33m     evolve   — 进化编译优化\033[0m")
                print("\033[33m     save xxx — 保存到 .evo 文件\033[0m")
                print("\033[33m     或继续用自然语言修改需求\033[0m")
            else:
                print(f"\n{llm_output}")

            conversation.append({"role": "assistant", "content": llm_output})

            if len(conversation) > 30:
                conversation = [conversation[0]] + conversation[-20:]


def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="evo-ai",
        description="易衍·Evomorph AI 编程环境",
    )
    parser.add_argument("command", nargs="?", help="单次命令（不进入交互模式）")
    parser.add_argument("args", nargs="*", help="命令参数")

    if len(sys.argv) > 1:
        args = parser.parse_args()
        cmd = args.command
        cmd_args = args.args

        if cmd == "compile" and cmd_args:
            source_path = Path(cmd_args[0])
            if source_path.exists():
                source = source_path.read_text(encoding="utf-8")
                try:
                    result = do_compile(source, "json")
                    print(result)
                except Exception as e:
                    print(f"编译失败: {e}", file=sys.stderr)
                    sys.exit(1)
        elif cmd == "run" and cmd_args:
            source_path = Path(cmd_args[0])
            if source_path.exists():
                source = source_path.read_text(encoding="utf-8")
                try:
                    print(do_run(source))
                except Exception as e:
                    print(f"运行失败: {e}", file=sys.stderr)
                    sys.exit(1)
        elif cmd == "evolve" and cmd_args:
            source_path = Path(cmd_args[0])
            if source_path.exists():
                source = source_path.read_text(encoding="utf-8")
                try:
                    print(do_evolve(source))
                except Exception as e:
                    print(f"进化失败: {e}", file=sys.stderr)
                    sys.exit(1)
        elif cmd == "lookup" and cmd_args:
            print(do_lookup(cmd_args[0]))
        elif cmd == "platforms":
            print(do_list_platforms())
        elif cmd == "config":
            config = load_config()
            if cmd_args and cmd_args[0] == "set" and len(cmd_args) >= 3:
                key, value = cmd_args[1], cmd_args[2]
                if key in config:
                    config[key] = value
                    save_config(config)
                    print(f"✓ {key} 已更新")
            else:
                safe = {k: (v[:8] + "..." if k == "api_key" and v else v) for k, v in config.items()}
                print(json.dumps(safe, ensure_ascii=False, indent=2))
        elif cmd == "help" or cmd == "--help" or cmd == "-h":
            parser.print_help()
            print()
            print("不带参数直接运行 evo-ai 进入交互式环境")
        else:
            print(f"未知命令: {cmd}")
            print("直接运行 evo-ai 进入交互式环境，或使用: compile/run/evolve/lookup/platforms/config")
            sys.exit(1)
    else:
        shell()


if __name__ == "__main__":
    main()
