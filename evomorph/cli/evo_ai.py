import json
import os
import sys
import re
import threading
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
    "max_tokens": 16384,
    "temperature": 0.7,
    "default_platforms": ["linux-6.x"],
    "default_mut_rate": 0.02,
    "default_generations": 50,
    "default_population": 32,
}

PROVIDERS = {
    "openai": {"name": "OpenAI", "base_url": "https://api.openai.com/v1"},
    "anthropic": {"name": "Anthropic (Claude)", "base_url": "https://api.anthropic.com/v1"},
    "deepseek": {"name": "DeepSeek", "base_url": "https://api.deepseek.com/v1"},
    "mistral": {"name": "Mistral (Codestral)", "base_url": "https://codestral.mistral.ai/v1"},
    "alibaba": {"name": "阿里云 (通义千问)", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    "alibaba-token": {"name": "阿里云 (通义千问 Token Plan)", "base_url": "https://token-plan.cn-beijing.maas.aliyuncs.com/v1"},
    "zhipu": {"name": "智谱 AI (GLM-4/CodeGeeX)", "base_url": "https://open.bigmodel.cn/api/paas/v4"},
    "zhipu-coding": {"name": "智谱 AI (GLM Coding Plan)", "base_url": "https://open.bigmodel.cn/api/coding/paas/v4"},
    "moonshot": {"name": "月之暗面 (Kimi)", "base_url": "https://api.moonshot.cn/v1"},
    "minimax-global": {"name": "MiniMax 国际站", "base_url": "https://api.minimax.io/v1"},
    "minimax-cn": {"name": "MiniMax 中国站", "base_url": "https://api.minimaxi.com/v1"},
    "volcengine": {"name": "火山引擎 (豆包/ARK)", "base_url": "https://ark.cn-beijing.volces.com/api/v3"},
    "z-ai": {"name": "z.ai", "base_url": "https://api.z.ai/api/paas/v4"},
    "z-ai-coding": {"name": "z.ai (GLM Coding Plan)", "base_url": "https://api.z.ai/api/coding/paas/v4"},
    "ollama": {"name": "Ollama (本地)", "base_url": "http://localhost:11434/v1"},
    "lmstudio": {"name": "LM Studio (本地)", "base_url": "http://localhost:1234/v1"},
    "xiaomi": {"name": "小米 (MiMo Token Plan)", "base_url": "https://token-plan-cn.xiaominimo.com/v1"},
}

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.spinner import Spinner
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.formatted_text import FormattedText
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.shortcuts import radiolist_dialog
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False


def _print(text="", style=None, **kwargs):
    if HAS_RICH:
        console.print(text, style=style, **kwargs)
    else:
        print(text)


def _print_markdown(text):
    if HAS_RICH:
        console.print(Markdown(text))
    else:
        print(text)


def _print_code(code, language="evomorph"):
    if HAS_RICH:
        try:
            syntax = Syntax(code, "python", theme="monokai", line_numbers=True, word_wrap=True)
            console.print(syntax)
        except Exception:
            console.print(Panel(code, title=".evo 代码", border_style="green"))
    else:
        print(code)


def _print_panel(content, title=None, style="green"):
    if HAS_RICH:
        console.print(Panel(content, title=title, border_style=style))
    else:
        if title:
            print(f"=== {title} ===")
        print(content)


def _spinner_start(message="思考中"):
    if HAS_RICH:
        spinner = Spinner("dots", text=f"  {message}...", style="cyan")
        live = Live(spinner, console=console, transient=True)
        live.start()
        return live
    return None


def _spinner_stop(live):
    if live:
        live.stop()


def fetch_models(api_url, api_key):
    if not api_key:
        return None
    try:
        import urllib.request
        base = api_url.rstrip("/")
        if base.endswith("/chat/completions"):
            base = base[: -len("/chat/completions")]
        models_url = f"{base}/models"
        headers = {"Authorization": f"Bearer {api_key}"}
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
    max_tokens = config.get("max_tokens", 16384)
    temperature = config.get("temperature", 0.7)

    if not api_key:
        return _local_fallback(messages[-1]["content"], config)

    result_holder = {"content": "", "error": None, "done": False}

    def _stream():
        try:
            import http.client
            from urllib.parse import urlparse

            parsed = urlparse(api_url)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            path = parsed.path or "/v1/chat/completions"

            payload = json.dumps({
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
            }).encode("utf-8")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "Accept": "text/event-stream",
            }

            if parsed.scheme == "https":
                conn = http.client.HTTPSConnection(host, port, timeout=120)
            else:
                conn = http.client.HTTPConnection(host, port, timeout=120)

            conn.request("POST", path, body=payload, headers=headers)
            resp = conn.getresponse()

            if resp.status != 200:
                body = resp.read().decode("utf-8", errors="replace")
                result_holder["error"] = f"API 错误 {resp.status}: {body[:200]}"
                conn.close()
                return

            full_content = []
            buffer = b""
            while not result_holder.get("cancelled"):
                chunk = resp.read(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line_bytes, buffer = buffer.split(b"\n", 1)
                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_content.append(content)
                                print(content, end="", flush=True)
                        except (json.JSONDecodeError, IndexError, KeyError):
                            pass
            conn.close()
            result_holder["content"] = "".join(full_content)
        except Exception as e:
            result_holder["error"] = str(e)
        finally:
            result_holder["done"] = True

    t = threading.Thread(target=_stream, daemon=True)
    t.start()

    print()
    _print("  按 Ctrl+C 可随时打断", style="dim")
    print()

    try:
        while t.is_alive():
            t.join(timeout=0.1)
    except KeyboardInterrupt:
        result_holder["cancelled"] = True
        _print("\n⏹ 已打断生成", style="yellow")
        t.join(timeout=2)

    print()

    if result_holder.get("error"):
        _print(f"[LLM 调用失败] {result_holder['error']}", style="bold red")
        return _local_fallback(messages[-1]["content"], config)

    if result_holder["content"]:
        return result_holder["content"]

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


def _read_local_context(user_text):
    paths = re.findall(r'(/[\w./\-\u4e00-\u9fff]+\w|\~/[\w./\-\u4e00-\u9fff]+\w|[A-Za-z]:[/\\][\w./\-\u4e00-\u9fff]+\w)', user_text)
    context_parts = []
    _SKIP_DIRS = {".git", "node_modules", "dist", "__pycache__", ".next", ".nuxt", "build", ".cache", "venv", ".venv"}
    _SOURCE_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".evo", ".md", ".txt", ".yaml", ".yml", ".toml", ".cfg", ".html", ".css", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".mjs", ".cjs", ".vue", ".svelte"}
    for p in paths:
        expanded = Path(os.path.expanduser(p))
        if not expanded.exists():
            continue
        if expanded.is_file():
            try:
                content = expanded.read_text(encoding="utf-8", errors="replace")
                if len(content) > 8000:
                    content = content[:8000] + "\n... (文件过长，已截断)"
                context_parts.append(f"=== 文件: {p} ===\n{content}")
            except Exception:
                pass
        elif expanded.is_dir():
            try:
                all_files = []
                for f in expanded.rglob("*"):
                    if any(skip in f.parts for skip in _SKIP_DIRS):
                        continue
                    if f.is_file() and f.suffix in _SOURCE_EXTS:
                        all_files.append(f)
                all_files.sort(key=lambda f: (0 if f.suffix in (".ts", ".tsx", ".js", ".jsx", ".py", ".evo") else 1, str(f)))
                file_list = []
                total_chars = 0
                max_chars = 50000
                for f in all_files[:60]:
                    try:
                        content = f.read_text(encoding="utf-8", errors="replace")
                        if len(content) > 4000:
                            content = content[:4000] + "\n... (已截断)"
                        if total_chars + len(content) > max_chars:
                            break
                        rel = f.relative_to(expanded)
                        file_list.append(f"--- {rel} ---\n{content}")
                        total_chars += len(content)
                    except Exception:
                        pass
                if file_list:
                    context_parts.append(f"=== 目录: {p} (共 {len(file_list)} 个源码文件) ===\n" + "\n".join(file_list))
                else:
                    dir_listing = "\n".join(str(f.relative_to(expanded)) for f in all_files[:50])
                    context_parts.append(f"=== 目录结构: {p} ===\n{dir_listing}")
            except Exception:
                pass
    return "\n\n".join(context_parts) if context_parts else ""


def _get_provider_short(config):
    cur_url = config.get("api_url", "")
    for k, v in PROVIDERS.items():
        if v["base_url"] in cur_url:
            return k
    return ""


def _build_prompt_str(config, current_file=None):
    model_short = config.get("model", "?")
    if len(model_short) > 16:
        model_short = model_short[:13] + "..."
    provider_short = _get_provider_short(config)
    key_mark = "●" if config.get("api_key") else "○"
    prompt = "易衍"
    if current_file:
        prompt += f" [{current_file}]"
    if provider_short:
        prompt += f" {provider_short}"
    prompt += f" {model_short}{key_mark}> "
    return prompt


def print_banner():
    if HAS_RICH:
        banner = Text()
        banner.append("  易衍 · Evomorph ", style="bold cyan")
        banner.append("v0.0.1", style="dim")
        banner.append("\n  六十四卦指令集 · 进化编程 · AI 驱动", style="dim")
        console.print()
        console.print(Panel(banner, border_style="cyan", padding=(1, 2)))
        console.print()
        console.print("  直接输入自然语言 → AI 生成 .evo 代码", style="green")
        console.print("  输入 / → 弹出命令菜单，上下键选择", style="green")
        console.print("  按 Ctrl+C → 随时打断 AI 生成", style="green")
        console.print()
    else:
        print()
        print("\033[36m  ╔═══════════════════════════════════════════════════════╗")
        print("  ║   易衍 · Evomorph  v0.0.1                            ║")
        print("  ║   六十四卦指令集 · 进化编程 · AI 驱动                  ║")
        print("  ╚═══════════════════════════════════════════════════════╝\033[0m")
        print()
        print("\033[32m  直接输入自然语言 → AI 生成 .evo 代码\033[0m")
        print("\033[32m  输入 / → 弹出命令菜单，上下键选择\033[0m")
        print()


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
    model_short = config.get("model", "?")
    if len(model_short) > 16:
        model_short = model_short[:13] + "..."
    provider_short = _get_provider_short(config)
    key_style = "#00ff00 bold" if config.get("api_key") else "#ff0000 bold"
    key_mark = "●" if config.get("api_key") else "○"

    prompt_formatted = FormattedText([
        ("bold cyan", "易衍"),
    ])
    if current_file:
        prompt_formatted.append(("dim", f" [{current_file}]"))
    if provider_short:
        prompt_formatted.append(("", f" {provider_short}"))
    prompt_formatted.append(("", f" {model_short}"))
    prompt_formatted.append((key_style, key_mark))
    prompt_formatted.append(("bold", " ❯ "))

    try:
        user_input = session.prompt(prompt_formatted).strip()
    except KeyboardInterrupt:
        return None
    except EOFError:
        return "/quit"
    return user_input


def _get_input_basic(config, current_file):
    prompt_str = _build_prompt_str(config, current_file)
    colored = f"\033[36m{prompt_str}\033[0m"
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
    for i, (key, prov) in enumerate(PROVIDERS.items()):
        marker = " ← 当前" if prov["base_url"] in cur_url else ""
        items.append(f"{key:18s} {prov['name']}{marker}")
    idx = _select_from_list("选择厂商 (上下键选择，回车确认)", items)
    if idx is None:
        return None
    key = list(PROVIDERS.keys())[idx]
    return key


def _select_model(models, current_model=""):
    if not models:
        return None
    items = []
    for i, m in enumerate(models):
        marker = " ← 当前" if m == current_model else ""
        items.append(f"{m}{marker}")
    idx = _select_from_list("选择模型 (上下键选择，回车确认)", items)
    if idx is None:
        return None
    return models[idx]


def _handle_provider_switch(config, prov_key):
    if prov_key not in PROVIDERS:
        _print(f"未知厂商: {prov_key}", style="bold red")
        _print("输入 /providers 查看所有厂商")
        close = [k for k in PROVIDERS if prov_key in k]
        if close:
            _print(f"你是否想用: {', '.join(close)}", style="yellow")
        return
    prov = PROVIDERS[prov_key]
    config["api_url"] = f"{prov['base_url']}/chat/completions"
    config["model"] = ""
    save_config(config)
    _print(f"✓ 已切换到 {prov['name']}", style="bold green")
    _print(f"  API 地址: {prov['base_url']}", style="dim")
    if not config.get("api_key"):
        _print("  ⚠ 需要设置 API Key，输入 /apikey <your-key>", style="yellow")
    else:
        _print("  ⟐ 自动拉取模型列表...", style="cyan")
        models = fetch_models(config["api_url"], config.get("api_key", ""))
        if models:
            if HAS_PROMPT_TOOLKIT:
                model_sel = _select_model(models)
                if model_sel:
                    config["model"] = model_sel
                    save_config(config)
                    _print(f"✓ 模型已切换到 {model_sel}", style="bold green")
                else:
                    _print("  模型未选择，输入 /models 选择模型", style="yellow")
            else:
                _print(f"可用模型 ({len(models)} 个):", style="green")
                for m in models:
                    _print(f"  {m}")
                _print("  使用 /model <模型名> 切换", style="yellow")
        else:
            _print("  拉取失败，输入 /model <名称> 手动设置", style="yellow")


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
        _print("  ⚠ 未配置 API Key，使用本地模板模式", style="yellow")
        _print("  输入 /apikey <your-key> 配置，或 /models 查看可用模型", style="dim")
        _print()

    while True:
        user_input = get_input()
        if user_input is None:
            continue
        if user_input == "/quit":
            _print("再见！", style="bold cyan")
            break

        if not user_input:
            continue

        is_path_input = False
        if user_input.startswith("/"):
            rest = user_input[1:]
            if re.match(r'[A-Za-z]', rest) and ("/" in user_input[1:] or Path(user_input).exists()):
                is_path_input = True

        if is_path_input:
            local_ctx = _read_local_context(user_input)
            if local_ctx:
                enriched = f"请阅读以下路径的文件内容：{user_input}\n\n以下是本地文件内容供参考:\n{local_ctx}"
                conversation.append({"role": "user", "content": enriched})
            else:
                conversation.append({"role": "user", "content": user_input})

            spinner = _spinner_start("⟐ 思考中")
            if local_ctx:
                _print("  已读取本地文件加入上下文", style="dim")
            llm_output = call_llm(config, conversation)
            _spinner_stop(spinner)

            evo_code = extract_evo_code(llm_output)
            if evo_code.startswith("@evolang"):
                last_evo_code = evo_code
                _print()
                _print_code(evo_code)
                _print()
                _print("  💡 /compile 编译  /run 运行  /evolve 进化  /save xxx 保存", style="dim")
            else:
                if evo_code and not evo_code.startswith("@evolang"):
                    last_evo_code = evo_code

            conversation.append({"role": "assistant", "content": llm_output})
            if len(conversation) > 30:
                conversation = [conversation[0]] + conversation[-20:]
            continue

        if not user_input.startswith("/"):
            local_ctx = _read_local_context(user_input)
            if local_ctx:
                enriched = f"{user_input}\n\n以下是本地文件内容供参考:\n{local_ctx}"
                conversation.append({"role": "user", "content": enriched})
            else:
                conversation.append({"role": "user", "content": user_input})

            spinner = _spinner_start("⟐ 思考中")
            if local_ctx:
                _print("  已读取本地文件加入上下文", style="dim")
            llm_output = call_llm(config, conversation)
            _spinner_stop(spinner)

            evo_code = extract_evo_code(llm_output)
            if evo_code.startswith("@evolang"):
                last_evo_code = evo_code
                _print()
                _print_code(evo_code)
                _print()
                _print("  💡 /compile 编译  /run 运行  /evolve 进化  /save xxx 保存", style="dim")
            else:
                if evo_code and not evo_code.startswith("@evolang"):
                    last_evo_code = evo_code

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
            _print(f"未知命令: {cmd}", style="bold red")
            if close:
                _print(f"  你是否想输入: {', '.join(close)}", style="yellow")
            else:
                _print("  输入 /help 查看所有命令，或直接输入自然语言让 AI 生成代码", style="dim")
            continue

        elif cmd == "/help":
            _print_markdown("""
## 易衍·Evomorph 命令

**不带 / 的文字** → 直接发给 AI，生成 .evo 代码
**输入 /** → 弹出命令菜单，上下键选择

### 厂商与模型
- `/provider <名称>` — 切换厂商（如 /provider deepseek）
- `/providers` — 列出所有厂商
- `/models` — 从厂商 API 拉取可用模型
- `/model <名称>` — 切换模型
- `/custom` — 自定义大模型（URL + Key + 模型ID）
- `/apikey <key>` — 设置 API Key
- `/status` — 查看配置状态

### 编译运行
- `/compile [文件]` — 编译代码
- `/run [文件]` — 运行代码
- `/evolve [文件]` — 进化编译优化

### 查询
- `/lookup <卦名>` — 查询卦象指令
- `/platforms` — 列出可用目标平台

### 文件
- `/new [名称]` — 新建 .evo 文件
- `/open <文件>` — 打开 .evo 文件
- `/save [文件]` — 保存代码到文件

### 其他
- `/history` — 查看对话历史
- `/clear` — 清空对话历史
- `/config` — 查看完整配置
- `/quit` — 退出
""")

        elif cmd == "/quit":
            _print("再见！", style="bold cyan")
            break

        elif cmd == "/clear":
            conversation = [{"role": "system", "content": system_prompt}]
            last_evo_code = None
            _print("✓ 对话已清空", style="green")

        elif cmd == "/models":
            api_key = config.get("api_key", "")
            api_url = config.get("api_url", "")
            if not api_key:
                _print("请先设置 API Key: /apikey <your-key>", style="bold red")
                continue
            _print("⟐ 从厂商 API 拉取模型列表...", style="cyan")
            models = fetch_models(api_url, api_key)
            if models:
                cur = config.get("model", "")
                if HAS_PROMPT_TOOLKIT:
                    selected = _select_model(models, cur)
                    if selected:
                        config["model"] = selected
                        save_config(config)
                        _print(f"✓ 模型已切换到 {selected}", style="bold green")
                    else:
                        _print("已取消", style="yellow")
                else:
                    _print(f"可用模型 ({len(models)} 个):", style="green")
                    for m in models:
                        marker = " ← 当前" if m == cur else ""
                        _print(f"  {m}{marker}")
                    _print("  使用 /model <模型名> 切换", style="yellow")
            else:
                _print("拉取失败，请检查 API Key 和网络连接", style="bold red")
                _print("  也可以手动设置: /model <模型名>", style="yellow")

        elif cmd == "/model":
            if not arg:
                cur = config.get("model", "未设置")
                _print(f"当前模型: {cur}", style="green")
                _print("使用 /model <模型名> 切换，或 /models 拉取可用模型", style="dim")
                continue
            config["model"] = arg
            save_config(config)
            _print(f"✓ 模型已切换到 {arg}", style="bold green")

        elif cmd == "/providers":
            if HAS_PROMPT_TOOLKIT:
                selected = _select_provider(config)
                if selected:
                    _handle_provider_switch(config, selected)
                else:
                    _print("已取消", style="yellow")
            else:
                _print("可用厂商:", style="green")
                cur_url = config.get("api_url", "")
                for key, prov in PROVIDERS.items():
                    marker = " ← 当前" if prov["base_url"] in cur_url else ""
                    _print(f"  {key:18s} {prov['name']}{marker}")
                _print("  使用 /provider <名称> 切换厂商", style="yellow")

        elif cmd == "/provider":
            if not arg:
                cur_prov = _get_provider_short(config) or "自定义"
                _print(f"当前厂商: {cur_prov}", style="green")
                _print("使用 /provider <名称> 切换，或 /providers 查看所有厂商", style="dim")
                continue
            _handle_provider_switch(config, arg)

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
                    _print("✓ 自定义模型已配置", style="bold green")
                    _print(f"  API URL: {url}", style="dim")
                    _print(f"  API Key: {key_masked}", style="dim")
                    _print(f"  模型 ID: {model_id}", style="dim")
                else:
                    _print("用法: /custom <API_URL> <API_KEY> <模型ID>", style="bold red")
                    _print("  /custom https://api.deepseek.com/v1 sk-xxx deepseek-chat", style="dim")
                continue

            _print_panel("自定义大模型配置\n\n请依次输入 API URL、API Key、模型 ID", title="自定义大模型", style="cyan")
            try:
                url = input("  API URL (如 https://api.deepseek.com/v1): ").strip()
                key = input("  API Key (如 sk-xxx): ").strip()
                model_id = input("  模型 ID (如 deepseek-chat): ").strip()
            except (EOFError, KeyboardInterrupt):
                _print("\n已取消", style="yellow")
                continue

            if not url or not model_id:
                _print("URL 和模型 ID 不能为空", style="bold red")
                continue

            if not url.endswith("/chat/completions"):
                url = url.rstrip("/") + "/chat/completions"

            config["api_url"] = url
            config["api_key"] = key
            config["model"] = model_id
            save_config(config)
            key_masked = key[:4] + "..." + key[-4:] if len(key) > 8 else "***"
            _print("✓ 自定义模型已配置", style="bold green")
            _print(f"  API URL: {url}", style="dim")
            _print(f"  API Key: {key_masked}", style="dim")
            _print(f"  模型 ID: {model_id}", style="dim")

        elif cmd == "/apikey":
            if not arg:
                cur = config.get("api_key", "")
                if cur:
                    _print(f"当前 API Key: {cur[:8]}...{cur[-4:]}", style="green")
                else:
                    _print("未设置 API Key", style="yellow")
                _print("使用 /apikey <your-key> 设置", style="dim")
                continue
            config["api_key"] = arg
            save_config(config)
            masked = arg[:4] + "..." + arg[-4:] if len(arg) > 8 else "***"
            _print(f"✓ API Key 已设置 ({masked})", style="bold green")
            _print(f"  当前模型: {config.get('model', '未设置')}", style="dim")

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

            status_lines = []
            status_lines.append(f"厂商:     {provider_name or '自定义'}")
            status_lines.append(f"模型:     {model_name}")
            if api_key:
                status_lines.append(f"API Key:  已配置 ({api_key[:4]}...{api_key[-4:]})")
            else:
                status_lines.append("API Key:  未配置")
            status_lines.append(f"API 地址: {api_url}")
            status_lines.append(f"目标平台: {', '.join(config.get('default_platforms', ['linux-6.x']))}")

            _print_panel("\n".join(status_lines), title="易衍·Evomorph 配置状态", style="cyan" if api_key else "yellow")

        elif cmd == "/history":
            for i, msg in enumerate(conversation[1:], 1):
                role = msg["role"]
                content = msg["content"][:80].replace("\n", " ")
                _print(f"  [{i}] {role}: {content}...", style="dim")

        elif cmd == "/platforms":
            _print(do_list_platforms())

        elif cmd == "/lookup":
            if not arg:
                _print("用法: /lookup <助记符/拼音/符号>", style="yellow")
                continue
            _print(do_lookup(arg))

        elif cmd == "/config":
            if not arg:
                safe = {k: (v[:8] + "..." if k == "api_key" and v else v) for k, v in config.items()}
                _print(json.dumps(safe, ensure_ascii=False, indent=2))
            elif arg.startswith("set "):
                set_parts = arg[4:].split(None, 1)
                if len(set_parts) < 2:
                    _print("用法: /config set <key> <value>", style="yellow")
                    continue
                key, value = set_parts
                if key in config:
                    config[key] = value
                    save_config(config)
                    _print(f"✓ {key} 已更新", style="green")
                else:
                    _print(f"未知配置项: {key}", style="bold red")
            else:
                _print("用法: /config 或 /config set <key> <value>", style="yellow")

        elif cmd == "/new":
            filename = arg or "untitled.evo"
            if not filename.endswith(".evo"):
                filename += ".evo"
            template = '@evolang "3.0"\n\n@xiangci {\n\t""\n}\n\n@locus main {\n\tmut_rate   = 0.02\n\tcross_pool = "default"\n\tfitness    = min_latency + 2.0*max_throughput\n\tenv_target = ["linux-6.x"]\n\tmax_generations = 100\n\n\t卦序: {\n\t\t\n\t}\n}\n'
            Path(filename).write_text(template, encoding="utf-8")
            current_file = filename
            last_evo_code = template
            _print(f"✓ 已创建 {filename}", style="bold green")

        elif cmd == "/open":
            if not arg:
                _print("用法: /open <文件路径>", style="yellow")
                continue
            filepath = Path(arg)
            if not filepath.exists():
                _print(f"文件不存在: {arg}", style="bold red")
                continue
            source = filepath.read_text(encoding="utf-8")
            current_file = arg
            last_evo_code = source
            _print(f"✓ 已打开 {arg}", style="bold green")
            _print_code(source)

        elif cmd == "/save":
            if not last_evo_code:
                _print("没有可保存的代码", style="bold red")
                continue
            filepath = arg or current_file or "output.evo"
            if not filepath.endswith(".evo"):
                filepath += ".evo"
            Path(filepath).write_text(last_evo_code, encoding="utf-8")
            current_file = filepath
            _print(f"✓ 已保存到 {filepath}", style="bold green")

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
                _print("没有可编译的代码，请先生成或打开文件", style="bold red")
                continue
            try:
                result = do_compile(source, "json")
                _print(result[:600], style="dim")
                if len(result) > 600:
                    _print("...", style="dim")
                _print("✓ 编译通过", style="bold green")
            except Exception as e:
                _print(f"✗ 编译失败: {e}", style="bold red")

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
                _print("没有可运行的代码，请先生成或打开文件", style="bold red")
                continue
            try:
                result = do_run(source)
                _print(result)
                _print("✓ 运行完成", style="bold green")
            except Exception as e:
                _print(f"✗ 运行失败: {e}", style="bold red")

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
                _print("没有可进化的代码，请先生成或打开文件", style="bold red")
                continue
            try:
                platforms = config.get("default_platforms", ["linux-6.x"])
                result = do_evolve(source,
                                   generations=config.get("default_generations", 50),
                                   population=config.get("default_population", 32),
                                   platforms=platforms)
                _print(result)
                _print("✓ 进化完成", style="bold green")
            except Exception as ex:
                _print(f"✗ 进化失败: {ex}", style="bold red")


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
