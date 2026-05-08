import sys
import os
import json
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from evomorph.bootstrap.runtime.enhanced_runtime import EnhancedEvoRuntime
from evomorph.vm.virtual_machine import IChingVM, VMState
from evomorph.evolution.engine import EvolutionEngine, EvolutionConfig, GeneInstruction
from evomorph.simulator.niche import PlatformSimNiche
from evomorph.sdk.xiangci import XiangciSDK
from evomorph.hexagrams import HexagramInstructionSet
from evomorph.native.bytecode_utils import source_to_segments
from evomorph.native.loader.evb_loader import NativeLoader


MCP_VERSION = "2024-11-05"
SERVER_NAME = "evomorph-mcp"
SERVER_VERSION = "0.0.6"

isa = HexagramInstructionSet()
compiler = EnhancedEvoRuntime()
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
                "description": "使用 IChing EVB 自举编译器编译易衍 .evo 源代码。编译路径完全走 IChing 六十四卦指令集 (VM 中执行) 生成 EVB 字节码，不依赖 Python 编译器。输入 .evo 源码，输出编译结果。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "易衍 .evo 源代码",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "dict", "evb"],
                            "description": "输出格式: json/dict(含元数据+字节码), evb(纯 EVB 字节码)",
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
            {
                "name": "evomorph_version",
                "description": "获取易衍·Evomorph版本信息。",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "evomorph_full_instruction_set",
                "description": "获取完整的六十四卦指令集信息。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["all", "元", "亨", "利", "贞"],
                            "description": "指令集分类，默认 all",
                        },
                    },
                },
            },
            {
                "name": "evomorph_native_runtime_info",
                "description": "获取原生C语言运行时信息。",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "evomorph_evolution_analyze",
                "description": "分析进化引擎状态和参数。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "可选的 .evo 源代码，用于分析基因座",
                        },
                    },
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
        elif tool_name == "evomorph_version":
            return _tool_version(arguments)
        elif tool_name == "evomorph_full_instruction_set":
            return _tool_full_instruction_set(arguments)
        elif tool_name == "evomorph_native_runtime_info":
            return _tool_native_runtime_info(arguments)
        elif tool_name == "evomorph_evolution_analyze":
            return _tool_evolution_analyze(arguments)
        else:
            return {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}], "isError": True}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}], "isError": True}


def _tool_compile(args):
    source = args.get("source", "")
    fmt = args.get("format", "json")
    result = compiler.full_compile(source)
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
    ast = compiler.full_compile(source)
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
    ast = compiler.full_compile(source)
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


def _tool_version(args):
    from evomorph import __version__, __lang__
    output = f"""易衍·Evomorph 版本信息:
- 版本号: v{__version__}
- 语言名称: {__lang__}
- MCP Server版本: {SERVER_VERSION}
- 六十四卦指令集: 64条指令
- 支持平台: {len(sim.list_platforms())}个

新增功能 (v0.0.4):
- 原生C语言运行时 (evomorph/native/runtime/)
- Evomorph语言重构进化引擎核心
- 30+个基因座，5个元基因座
- 完整的选择/交叉/变异算子"""
    return {"content": [{"type": "text", "text": output}]}


def _tool_full_instruction_set(args):
    category = args.get("category", "all")
    
    categories = {
        "元": "元·创生",
        "亨": "亨·交互",
        "利": "利·转换",
        "贞": "贞·终成"
    }
    
    category_full_names = {
        "元·创生": "元·创生（阳爻为主）",
        "亨·交互": "亨·交互",
        "利·转换": "利·转换",
        "贞·终成": "贞·终成"
    }
    
    lines = ["六十四卦指令集:"]
    
    if category == "all":
        for cat, desc in categories.items():
            lines.append(f"\n【{category_full_names.get(desc, desc)}】")
            instructions = isa.instructions_by_category(desc)
            for entry in instructions:
                lines.append(f"  {entry['symbol']} {entry['mnemonic']:12} - 操作码:{entry['opcode']:2d} {entry['binary']} | {entry['cn_name']}")
    else:
        cat_name = categories.get(category)
        if cat_name:
            lines.append(f"\n【{category_full_names.get(cat_name, cat_name)}】")
            instructions = isa.instructions_by_category(cat_name)
            for entry in instructions:
                lines.append(f"  {entry['symbol']} {entry['mnemonic']:12} - 操作码:{entry['opcode']:2d} {entry['binary']} | {entry['cn_name']}")
    
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


def _tool_native_runtime_info(args):
    import os
    native_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                              "evomorph", "native", "runtime")
    
    header_file = os.path.join(native_dir, "evomorph_runtime.h")
    source_file = os.path.join(native_dir, "evomorph_runtime.c")
    test_file = os.path.join(native_dir, "test_runtime.c")
    
    header_exists = os.path.exists(header_file)
    source_exists = os.path.exists(source_file)
    test_exists = os.path.exists(test_file)
    
    output = f"""原生Evomorph运行时信息:

位置: {native_dir}

文件状态:
- evomorph_runtime.h: {'✅ 存在' if header_exists else '❌ 不存在'}
- evomorph_runtime.c: {'✅ 存在' if source_exists else '❌ 不存在'}
- test_runtime.c: {'✅ 存在' if test_exists else '❌ 不存在'}

主要特性:
1. 完整的64卦指令集处理器
   - 操作码 = 爻位二进制 (0-63)
   - 每条指令 = 4字节
   - 16个通用寄存器

2. 集成式进化引擎
   - 与虚拟机共享状态
   - 原生性能执行

3. 选择算法
   - 轮盘赌选择 (Roulette)
   - 锦标赛选择 (Tournament)
   - 排名选择 (Rank)

4. 交叉算子
   - 单点交叉 (Single-point)
   - 两点交叉 (Two-point)
   - 均匀交叉 (Uniform)

5. 变异算子
   - 爻位翻转 (Flip yao)
   - 修饰符变异 (Modifier)

6. 主进化循环
   - 精英保留
   - 种群更新
   - 收敛检测

数据结构:
- EvoVM: 虚拟机状态
- EvoGeneInstruction: 基因指令 (4字节)
- EvoIndividual: 个体
- EvoPopulation: 种群
- EvoEvolutionConfig: 进化配置

编译测试:
gcc -o test_runtime test_runtime.c evomorph_runtime.c -Wall -Wextra"""
    
    return {"content": [{"type": "text", "text": output}]}


def _tool_evolution_analyze(args):
    source = args.get("source", "")
    
    lines = ["进化引擎分析:"]
    lines.append("\n【默认参数】")
    lines.append(f"- 默认种群大小: 32")
    lines.append(f"- 默认进化代数: 20")
    lines.append(f"- 默认变异率: 0.02")
    lines.append(f"- 默认目标平台: linux-6.x")
    
    lines.append("\n【选择算法】")
    lines.append("- 轮盘赌选择 (Roulette) - 基于适应度比例")
    lines.append("- 锦标赛选择 (Tournament) - 基于局部竞争")
    lines.append("- 排名选择 (Rank) - 基于排名线性")
    
    lines.append("\n【交叉算子】")
    lines.append("- 单点交叉 - 随机一个交叉点")
    lines.append("- 两点交叉 - 随机两个交叉点")
    lines.append("- 均匀交叉 - 每一位独立选择")
    
    lines.append("\n【变异算子】")
    lines.append("- 爻位翻转 - 翻转操作码的某一位")
    lines.append("- 修饰符变异 - 修改修饰符字段")
    
    lines.append("\n【适应度关键词】")
    lines.append("- min_latency - 最小延迟")
    lines.append("- max_throughput - 最大吞吐量")
    lines.append("- min_energy - 最小能耗")
    lines.append("- min_size - 最小代码体积")
    
    if source:
        lines.append("\n【基因座分析】")
        try:
            ast = compiler.full_compile(source)
            loci = ast.get("loci", [])
            meta_loci = ast.get("meta_loci", [])
            
            lines.append(f"- 基因座数量: {len(loci)}")
            lines.append(f"- 元基因座数量: {len(meta_loci)}")
            
            for i, locus in enumerate(loci):
                lines.append(f"\n  基因座[{i}]: {locus.get('name', 'unknown')}")
                lines.append(f"    - 变异率: {locus.get('mut_rate', 0.02)}")
                lines.append(f"    - 适应度: {locus.get('fitness', 'N/A')}")
                lines.append(f"    - 目标平台: {locus.get('env_target', ['N/A'])}")
                lines.append(f"    - 指令数量: {len(locus.get('instructions', []))}")
        except Exception as e:
            lines.append(f"  分析失败: {str(e)}")
    
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
