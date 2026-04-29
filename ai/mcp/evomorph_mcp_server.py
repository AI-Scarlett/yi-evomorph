import sys
import os
import json
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from evomorph.compiler import EvocCompiler
from evomorph.vm.virtual_machine import IChingVM, VMState
from evomorph.evolution.engine import EvolutionEngine, EvolutionConfig, GeneInstruction
from evomorph.simulator.niche import PlatformSimNiche
from evomorph.sdk.xiangci import XiangciSDK
from evomorph.hexagrams import HexagramInstructionSet
from evomorph.native.bytecode_utils import source_to_segments
from evomorph.native.loader.evb_loader import NativeLoader


MCP_VERSION = "2024-11-05"
SERVER_NAME = "evomorph-mcp"
SERVER_VERSION = "3.0.0"

isa = HexagramInstructionSet()
compiler = EvocCompiler()
sdk = XiangciSDK()
sim = PlatformSimNiche()
loader = NativeLoader()


def handle_initialize(params):
    return {
        "protocolVersion": MCP_VERSION,
        "capabilities": {
            "tools": {},
        },
        "serverInfo": {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
        },
    }


def handle_tools_list(params):
    return {
        "tools": [
            {
                "name": "evomorph_compile",
                "description": "编译易衍 .evo 源代码为字节码或 JSON。输入 .evo 源码，输出编译结果。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "易衍 .evo 源代码",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "dict"],
                            "description": "输出格式，默认 json",
                        },
                    },
                    "required": ["source"],
                },
            },
            {
                "name": "evomorph_xiangci",
                "description": "象辞翻译：将自然语言意图翻译为易衍卦象指令。输入中文或英文描述，输出 .evo 源码。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "自然语言描述（象辞），如'并行求和，适安卓与鸿蒙'",
                        },
                        "target_platforms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "目标平台列表，如 ['linux-6.x', 'android-14']",
                        },
                    },
                    "required": ["text"],
                },
            },
            {
                "name": "evomorph_evolve",
                "description": "进化编译：对 .evo 源码进行遗传算法优化。输入源码和进化参数，输出最优个体。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "易衍 .evo 源代码",
                        },
                        "generations": {
                            "type": "integer",
                            "description": "进化代数，默认 20",
                        },
                        "population_size": {
                            "type": "integer",
                            "description": "种群大小，默认 32",
                        },
                        "target_platforms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "目标平台列表",
                        },
                    },
                    "required": ["source"],
                },
            },
            {
                "name": "evomorph_run",
                "description": "在 IChingVM 卦象虚拟机上运行 .evo 程序。输入源码，输出执行结果。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "易衍 .evo 源代码",
                        },
                        "max_cycles": {
                            "type": "integer",
                            "description": "最大执行周期，默认 10000",
                        },
                    },
                    "required": ["source"],
                },
            },
            {
                "name": "evomorph_lookup_hexagram",
                "description": "查询六十四卦指令信息。输入卦象符号、助记符或拼音，返回指令详情。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "查询关键词：卦象符号(如䷀)、助记符(如CREA)、或拼音(如QIAN)",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "evomorph_list_platforms",
                "description": "列出所有可用的目标平台及其性能参数。",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ],
    }


def handle_tools_call(params):
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    try:
        if tool_name == "evomorph_compile":
            return _tool_compile(arguments)
        elif tool_name == "evomorph_xiangci":
            return _tool_xiangci(arguments)
        elif tool_name == "evomorph_evolve":
            return _tool_evolve(arguments)
        elif tool_name == "evomorph_run":
            return _tool_run(arguments)
        elif tool_name == "evomorph_lookup_hexagram":
            return _tool_lookup(arguments)
        elif tool_name == "evomorph_list_platforms":
            return _tool_list_platforms(arguments)
        else:
            return {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}], "isError": True}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}], "isError": True}


def _tool_compile(args):
    source = args.get("source", "")
    fmt = args.get("format", "json")
    result = compiler.compile(source, output_format=fmt)
    if isinstance(result, str):
        text = result
    else:
        text = json.dumps(result, ensure_ascii=False, indent=2)
    return {"content": [{"type": "text", "text": text}]}


def _tool_xiangci(args):
    text = args.get("text", "")
    platforms = args.get("target_platforms", ["linux-6.x"])
    translation = sdk.translate(text, env_targets=platforms)
    evo_source = sdk.export_to_evo_source(translation)
    output = f"""象辞翻译结果:
- 原文: {translation.original_text}
- 基因座: {translation.locus_name}
- 置信度: {translation.confidence:.2f}
- 使用模型: {translation.model_used}
- 指令数: {len(translation.generated_genes)}

生成的 .evo 源码:
```evomorph
{evo_source}
```"""
    return {"content": [{"type": "text", "text": output}]}


def _tool_evolve(args):
    source = args.get("source", "")
    generations = args.get("generations", 20)
    population = args.get("population_size", 32)
    platforms = args.get("target_platforms", ["linux-6.x"])
    ast = compiler.compile(source, output_format="dict")
    loci = ast.get("loci", [])
    if not loci:
        return {"content": [{"type": "text", "text": "未找到基因座"}], "isError": True}
    locus = loci[0]
    seed_genes = []
    for instr in locus.get("instructions", []):
        gene = GeneInstruction(opcode=instr.get("opcode", 0), modifier=instr.get("modifier", 0))
        seed_genes.append(gene)
    config = EvolutionConfig(
        population_size=population,
        max_generations=generations,
        mut_rate=locus.get("mut_rate", 0.02),
        env_targets=platforms,
    )
    engine = EvolutionEngine(config=config, platform_simulator=sim)
    engine.initialize_population(seed_genes)
    best = engine.evolve()
    if best:
        output = f"""进化编译完成:
- 基因座: {locus['name']}
- 最佳适应度: {best.fitness:.4f}
- 最佳个体基因数: {len(best.genes)}
- 起源: {best.origin}
- 平台评分: {json.dumps(best.platform_scores, ensure_ascii=False)}
- 进化历史: {len(engine.get_evolution_history())} 代"""
    else:
        output = "进化失败"
    return {"content": [{"type": "text", "text": output}]}


def _tool_run(args):
    source = args.get("source", "")
    max_cycles = args.get("max_cycles", 10000)
    ast = compiler.compile(source, output_format="dict")
    loci = ast.get("loci", [])
    if not loci:
        return {"content": [{"type": "text", "text": "未找到基因座"}], "isError": True}
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
    state = vm.run(max_cycles=max_cycles)
    dump = vm.dump_state()
    output = f"""IChingVM 执行结果:
- 状态: {dump['state']}
- 周期: {dump['cycle_count']}
- 能耗: {dump['energy_cost']:.2f}
- 非零寄存器: {json.dumps({k: v for k, v in dump['registers'].items() if v != 0}, ensure_ascii=False)}"""
    return {"content": [{"type": "text", "text": output}]}


def _tool_lookup(args):
    query = args.get("query", "")
    entry = isa.lookup(query)
    if entry:
        output = f"""卦象指令详情:
- 卦象: {entry['symbol']}
- 助记符: {entry['mnemonic']}
- 拼音: {entry['pinyin']}
- 操作码: {entry['opcode']} (十进制) = {entry['binary']} (二进制)
- 爻位: {entry['yao']}
- 中文名: {entry['cn_name']}
- 义理: {entry['description']}"""
    else:
        output = f"未找到匹配 '{query}' 的卦象指令"
    return {"content": [{"type": "text", "text": output}]}


def _tool_list_platforms(args):
    platforms = sim.list_platforms()
    lines = ["可用目标平台:"]
    for name in platforms:
        profile = sim.get_profile(name)
        if profile:
            lines.append(f"- {name}: {profile.platform_type.value} v{profile.version}, "
                         f"内存延迟={profile.memory_latency_ns}ns, "
                         f"线程创建={profile.thread_create_cost}, "
                         f"最大线程={profile.max_threads}")
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


async def handle_request(request):
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        result = handle_initialize(params)
    elif method == "tools/list":
        result = handle_tools_list(params)
    elif method == "tools/call":
        result = handle_tools_call(params)
    elif method == "notifications/initialized":
        return None
    else:
        result = {"error": f"Unknown method: {method}"}

    if req_id is not None:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    return None


async def main():
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    transport, _ = await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break
        line = line.decode("utf-8").strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = await handle_request(request)
            if response:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            pass
        except Exception as e:
            error_response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
