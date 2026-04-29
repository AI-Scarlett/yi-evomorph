import json
import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from evomorph.compiler import EvocCompiler
from evomorph.hexagrams import HexagramInstructionSet

HEXAGRAM_DATA = [
    (63, "䷀", "QIAN", "CREA", "创生", "乾元创生，创建新进程/线程"),
    (0, "䷁", "KUN", "RECV", "承纳", "坤厚载物，接收消息/映射"),
    (17, "䷂", "ZHUN", "ALLOC", "初生", "初生之难，在堆/栈开辟内存"),
    (34, "䷃", "MENG", "SPRT", "苗蒙", "蒙以养正，加载动态库"),
    (23, "䷄", "XU", "WAIT", "需待", "需，须也，等待条件满足"),
    (58, "䷅", "SONG", "LOCK", "争讼", "讼，争也，争抢互斥锁"),
    (2, "䷆", "SHI", "BRANCH", "师众", "师，众也，条件分支跳转"),
    (16, "䷇", "BI", "MERGE", "比辅", "比，辅也，合并数据流"),
    (55, "䷈", "XIAOXU", "PREFETCH", "小畜", "小畜，寡也，预取缓存行"),
    (59, "䷉", "LV", "STEP", "履礼", "履，礼也，单步执行/迭代"),
    (7, "䷊", "TAI", "FLUSH", "泰通", "泰，通也，刷新写缓冲"),
    (56, "䷋", "PI", "HALT", "否闭", "否，闭也，暂停/阻塞"),
    (61, "䷌", "TONGREN", "FELLOWSHIP", "同人", "与人同者物必归，同步通信集结"),
    (47, "䷍", "DAYOU", "ABUNDANCE", "大有", "大有，众也，写回/填充数据"),
    (4, "䷎", "QIANX", "YIELD", "谦退", "谦，退也，释放资源/让出"),
    (8, "䷏", "YU", "SPECULATE", "豫乐", "豫，乐也，预测分支/投机执行"),
    (25, "䷐", "SUI", "FOLLOWING", "随从", "随，从也，数据流跟踪/复制"),
    (38, "䷑", "GU", "MUT", "蛊坏", "蛊，败坏而后新生，强制变异"),
    (3, "䷒", "LIN", "APPROACH", "临近", "临，大也，接近临界区"),
    (48, "䷓", "GUAN", "CONTEMPLATE", "观瞻", "观，瞻也，观测/性能监视"),
    (41, "䷔", "SHIHE", "BITE", "噬嗑", "噬嗑，食也，断言/校验"),
    (37, "䷕", "BIX", "ADORN", "贲饰", "贲，饰也，格式化/编码转换"),
    (32, "䷖", "BO", "STRIP", "剥落", "剥，落也，剥离/解构数据"),
    (1, "䷗", "FU", "RETURN", "复归", "复，归也，函数返回/循环回跳"),
    (57, "䷘", "WUWANG", "INTRINSIC", "无妄", "无妄，天命也，内建原子操作"),
    (39, "䷙", "DAXU", "BARRIER", "大畜", "大畜，厚积也，内存屏障"),
    (33, "䷚", "YI", "NOURISH", "颐养", "颐，养也，垃圾回收/内存养护"),
    (30, "䷛", "DAGUO", "OVERLOAD", "大过", "大过，颠也，异常/溢出处理"),
    (18, "䷜", "KAN", "TRAP", "坎险", "坎，陷也，异常捕获/陷阱"),
    (45, "䷝", "LI", "ILLUMINATE", "离明", "离，丽也，日志/调试输出"),
    (28, "䷞", "XIAN", "SENSE", "咸感", "咸，感也，事件监听/感应"),
    (14, "䷟", "HENG", "PERSIST", "恒久", "恒，久也，持久化存储"),
    (60, "䷠", "DUN", "RETREAT", "遁退", "遁，退也，安全退出/回滚"),
    (15, "䷡", "DAZHUANG", "THRUST", "大壮", "大壮，壮也，强制执行/突破"),
    (40, "䷢", "JIN", "ADVANCE", "晋进", "晋，进也，队列推进/流水线"),
    (5, "䷣", "MINGYI", "OBSCURE", "明夷", "明夷，诛也，加密/混淆"),
    (53, "䷤", "JIAREN", "BIND", "家人", "家人，内也，绑定/闭包"),
    (43, "䷥", "KUI", "CONVERT", "睽乖", "睽，乖也，类型转换"),
    (20, "䷦", "JIANX", "LAME", "蹇难", "蹇，难也，重试/降级"),
    (10, "䷧", "JIE", "UNLOCK", "解缓", "解，缓也，解锁/释放"),
    (35, "䷨", "SUN", "REDUCE", "损减", "损，减也，缩减/压缩"),
    (49, "䷩", "YIX", "INCREASE", "益增", "益，增也，扩展/增强"),
    (31, "䷪", "GUAI", "BREAK", "夬决", "夬，决也，中断/断开"),
    (62, "䷫", "GOU", "MATE", "姤遇", "姤，遇也，基因交叉重组"),
    (24, "䷬", "CUI", "GATHER", "萃聚", "萃，聚也，收集/归约"),
    (6, "䷭", "SHENG", "PUSH_UP", "升推", "升，推也，入栈/上推"),
    (26, "䷮", "KUNX", "TRAPPED", "困穷", "困，穷也，死锁检测"),
    (22, "䷯", "JING", "WELL", "井泉", "井，通也，阻塞读/管道"),
    (29, "䷰", "GE", "REPLACE", "革变", "革，变也，替换/热更新"),
    (46, "䷱", "DING", "CAST", "鼎定", "鼎，定也，类型铸造/固化"),
    (9, "䷲", "ZHEN", "SHOCK", "震动", "震，动也，信号/中断触发"),
    (36, "䷳", "GEN", "STILL", "艮止", "艮，止也，暂停/冻结"),
    (52, "䷴", "JIANJ", "GRADUAL", "渐进", "渐，进也，逐步执行"),
    (11, "䷵", "GUIMEI", "MISMATCH", "归妹", "归妹，未当也，类型不匹配"),
    (13, "䷶", "FENG", "ABOUND", "丰盛", "丰，大也，批量操作"),
    (44, "䷷", "LVX", "TRAVEL", "旅寄", "旅，寄也，上下文切换"),
    (54, "䷸", "XUN", "PENETRATE", "巽入", "巽，入也，渗透/穿透访问"),
    (27, "䷹", "DUI", "JOY", "兑悦", "兑，悦也，回调/完成通知"),
    (50, "䷺", "HUAN", "DISPERSE", "涣散", "涣，散也，分散写入"),
    (19, "䷻", "JIEX", "THROTTLE", "节度", "节，度也，节流/流控"),
    (51, "䷼", "ZHONGFU", "TRUST", "中孚", "中孚，信也，签名/验证"),
    (12, "䷽", "XIAOGUO", "MICRO", "小过", "小过，过也，微调/微操作"),
    (21, "䷾", "JIJI", "SYNC", "既济", "既济，事已成而防其乱，屏障同步"),
    (42, "䷿", "WEIJI", "FUTU", "未济", "物不可穷，事未成，异步占位符"),
]

MNEMONIC_MAP = {row[3]: row for row in HEXAGRAM_DATA}
SYMBOL_MAP = {row[1]: row for row in HEXAGRAM_DATA}
PINYIN_MAP = {row[2]: row for row in HEXAGRAM_DATA}

MODIFIERS = {
    ".ASYNC": ("异步执行", 0b100000),
    ".ATOMIC": ("原子操作", 0b010000),
    ".PRIV": ("私有访问", 0b001000),
    ".WEAK": ("弱引用", 0b000100),
    ".STRONG": ("强引用", 0b000010),
    ".VOLATILE": ("易失性", 0b000001),
}

FITNESS_KW = {
    "min_latency": "最小延迟",
    "max_throughput": "最大吞吐量",
    "min_energy": "最小能耗",
    "min_size": "最小代码体积",
}

PLATFORMS = ["linux-6.x", "android-14", "ios-18", "win-11", "harmony-5"]

compiler = EvocCompiler()
isa = HexagramInstructionSet()


def _make_completion(label, kind, detail, documentation, insert_text=None):
    return {
        "label": label,
        "kind": kind,
        "detail": detail,
        "documentation": documentation,
        "insertText": insert_text or label,
    }


def get_completions(uri, line, character, source_lines):
    completions = []
    current_line = source_lines[line] if line < len(source_lines) else ""
    prefix = current_line[:character]

    in_guaxu = False
    in_locus_header = False
    brace_depth = 0
    guaxu_found = False

    for i, src_line in enumerate(source_lines):
        if i >= line:
            break
        if "卦序" in src_line:
            guaxu_found = True
        if "{" in src_line:
            brace_depth += src_line.count("{")
        if "}" in src_line:
            brace_depth -= src_line.count("}")

    if guaxu_found and brace_depth > 0:
        in_guaxu = True
    elif brace_depth > 0 and not guaxu_found:
        in_locus_header = True

    if in_guaxu:
        for row in HEXAGRAM_DATA:
            opcode, symbol, pinyin, mnemonic, cn_name, desc = row
            completions.append(_make_completion(
                label=f"{symbol} {mnemonic}",
                kind=3,
                detail=f"{symbol} {mnemonic} (0x{opcode:02X})",
                documentation=f"**{cn_name}** — {desc}\n\n操作码: {opcode} ({format(opcode, '06b')})\n拼音: {pinyin}",
                insert_text=mnemonic,
            ))

        for mod, (desc, val) in MODIFIERS.items():
            completions.append(_make_completion(
                label=mod,
                kind=14,
                detail=desc,
                documentation=f"修饰符 {mod}: {desc} (0b{val:06b})",
            ))

        for i in range(16):
            completions.append(_make_completion(
                label=f"R{i}",
                kind=6,
                detail=f"通用寄存器 R{i}",
                documentation=f"通用寄存器 R{i}",
            ))
        for name, idx in [("R_FP", 12), ("R_SP", 13), ("R_LR", 14), ("R_A0", 15)]:
            completions.append(_make_completion(
                label=name,
                kind=6,
                detail=f"特殊寄存器 {name} (索引 {idx})",
                documentation=f"特殊寄存器 {name}",
            ))

    elif in_locus_header:
        for prop, snippet in [
            ("mut_rate", "mut_rate = ${1:0.02}"),
            ("cross_pool", 'cross_pool = "${1:default}"'),
            ("fitness", "fitness = ${1:min_latency} + ${2:2.0}*${3:max_throughput}"),
            ("env_target", 'env_target = [${1:"linux-6.x"}]'),
            ("max_generations", "max_generations = ${1:100}"),
        ]:
            completions.append(_make_completion(
                label=prop.split("=")[0].strip(),
                kind=10,
                detail=f"基因座属性: {prop}",
                documentation=f"设置 {prop}",
                insert_text=snippet,
            ))

        for kw, desc in FITNESS_KW.items():
            completions.append(_make_completion(
                label=kw,
                kind=14,
                detail=desc,
                documentation=f"适应度关键词: {kw} — {desc}",
            ))

        completions.append(_make_completion(
            label="卦序:",
            kind=15,
            detail="卦序块 — 定义指令序列",
            documentation="卦序块：在此花括号内编写卦象指令序列",
            insert_text="卦序: {\n\t$0\n}",
        ))

    else:
        for kw, snippet in [
            ("@evolang", '@evolang "${1:3.0}"'),
            ("@xiangci", '@xiangci {\n\t"${1:描述程序意图}"\n}'),
            ("@locus", '@locus ${1:name} {\n\tmut_rate   = ${2:0.02}\n\tcross_pool = "${3:default}"\n\tfitness    = ${4:min_latency + 2.0*max_throughput}\n\tenv_target = [${5:"linux-6.x"}]\n\tmax_generations = ${6:100}\n\n\t卦序: {\n\t\t$0\n\t}\n}'),
            ("@meta_locus", '@meta_locus ${1:name} {\n\tmut_rate = ${2:0.01}\n\tfitness  = ${3:min_size + max_throughput}\n\n\t卦序: {\n\t\t$0\n\t}\n}'),
        ]:
            completions.append(_make_completion(
                label=kw,
                kind=14,
                detail=f"易衍关键字: {kw}",
                documentation=f"插入 {kw} 块",
                insert_text=snippet,
            ))

        for platform in PLATFORMS:
            completions.append(_make_completion(
                label=platform,
                kind=19,
                detail=f"目标平台: {platform}",
                documentation=f"目标平台标识: {platform}",
            ))

    return completions


def get_diagnostics(uri, source):
    diagnostics = []
    try:
        result = compiler.compile(source, output_format="dict")
        loci = result.get("loci", [])
        for locus in loci:
            name = locus.get("name", "")
            if not locus.get("env_targets"):
                diagnostics.append({
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}},
                    "severity": 2,
                    "message": f"基因座 '{name}' 缺少 env_target 目标平台",
                    "source": "evomorph",
                })
            if not locus.get("fitness") or not locus.get("fitness", {}).get("terms"):
                diagnostics.append({
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}},
                    "severity": 2,
                    "message": f"基因座 '{name}' 缺少 fitness 适应度表达式",
                    "source": "evomorph",
                })
            for instr in locus.get("instructions", []):
                if instr.get("opcode") is None:
                    diagnostics.append({
                        "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}},
                        "severity": 1,
                        "message": f"无法识别的指令: {instr.get('mnemonic', '?')}",
                        "source": "evomorph",
                    })
    except SyntaxError as e:
        diagnostics.append({
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}},
            "severity": 1,
            "message": f"语法错误: {str(e)}",
            "source": "evomorph",
        })
    except Exception as e:
        diagnostics.append({
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}},
            "severity": 1,
            "message": f"编译错误: {str(e)}",
            "source": "evomorph",
        })
    return diagnostics


def get_hover(uri, line, character, source_lines):
    if line >= len(source_lines):
        return None
    source_line = source_lines[line]
    word = _extract_word(source_line, character)
    if not word:
        return None

    if word in MNEMONIC_MAP:
        row = MNEMONIC_MAP[word]
        opcode, symbol, pinyin, mnemonic, cn_name, desc = row
        return {
            "contents": {
                "kind": "markdown",
                "value": (
                    f"**{symbol} {mnemonic}** — {cn_name}\n\n"
                    f"{desc}\n\n"
                    f"| 属性 | 值 |\n|------|----|\n"
                    f"| 操作码 | {opcode} |\n"
                    f"| 二进制 | {format(opcode, '06b')} |\n"
                    f"| 拼音 | {pinyin} |\n"
                    f"| 修饰符 | .ASYNC .ATOMIC .PRIV .WEAK .STRONG .VOLATILE |"
                ),
            }
        }

    if word in SYMBOL_MAP:
        row = SYMBOL_MAP[word]
        opcode, symbol, pinyin, mnemonic, cn_name, desc = row
        return {
            "contents": {
                "kind": "markdown",
                "value": f"**{symbol} {mnemonic}** — {cn_name}\n\n{desc}\n\n操作码: {opcode} ({format(opcode, '06b')})",
            }
        }

    if word in PINYIN_MAP:
        row = PINYIN_MAP[word]
        opcode, symbol, pinyin, mnemonic, cn_name, desc = row
        return {
            "contents": {
                "kind": "markdown",
                "value": f"**{symbol} {mnemonic}** — {cn_name}\n\n{desc}\n\n操作码: {opcode} ({format(opcode, '06b')})",
            }
        }

    if word in MODIFIERS:
        desc, val = MODIFIERS[word]
        return {
            "contents": {
                "kind": "markdown",
                "value": f"**{word}** — {desc}\n\n修饰符位: 0b{val:06b}",
            }
        }

    if word in FITNESS_KW:
        return {
            "contents": {
                "kind": "markdown",
                "value": f"**{word}** — {FITNESS_KW[word]}\n\n用于 fitness 适应度表达式",
            }
        }

    if word.startswith("R") and (word[1:].isdigit() or word in ("R_FP", "R_SP", "R_LR", "R_A0")):
        special = {"R_FP": "帧指针 (索引12)", "R_SP": "栈指针 (索引13)", "R_LR": "链接寄存器 (索引14)", "R_A0": "累加器 (索引15)"}
        if word in special:
            return {"contents": {"kind": "markdown", "value": f"**{word}** — {special[word]}"}}
        idx = int(word[1:])
        return {"contents": {"kind": "markdown", "value": f"**{word}** — 通用寄存器 (索引{idx})"}}

    if word in ("mut_rate", "cross_pool", "fitness", "env_target", "max_generations"):
        descs = {
            "mut_rate": "变异率 (0.0~1.0)，控制进化编译中的爻位翻转概率",
            "cross_pool": "交叉池名称，同池基因座可进行基因交叉",
            "fitness": "适应度表达式，定义进化优化的目标函数",
            "env_target": "目标平台列表，代码将针对这些平台优化",
            "max_generations": "最大进化代数",
        }
        return {"contents": {"kind": "markdown", "value": f"**{word}** — {descs.get(word, '')}"}}

    return None


def get_signature_help(uri, line, character, source_lines):
    if line >= len(source_lines):
        return None
    source_line = source_lines[line]
    prefix = source_line[:character]

    match = re.search(r'(\w+)\s*', prefix[::-1])
    if not match:
        return None
    mnemonic = match.group(1)[::-1]

    if mnemonic not in MNEMONIC_MAP:
        return None

    row = MNEMONIC_MAP[mnemonic]
    opcode, symbol, pinyin, mnem, cn_name, desc = row

    operand_docs = {
        "CREA": "CREA R_dest, R_param — 创建新进程/线程",
        "RECV": "RECV R_dest, source — 接收消息/数据",
        "ALLOC": "ALLOC R_dest, size — 分配内存",
        "FELLOWSHIP": "FELLOWSHIP R_group, R_member — 同步通信集结",
        "ABUNDANCE": "ABUNDANCE R_dest, R_source — 写回/填充数据",
        "SYNC": "SYNC — 屏障同步（无操作数）",
        "FUTU": "FUTU R_dest — 创建异步占位符/未来值",
        "MUT": "MUT R_target, mask — 强制变异指定爻位",
        "MATE": "MATE R_parent1, R_parent2 — 基因交叉重组",
        "GATHER": "GATHER R_dest, R_source — 收集/归约",
        "PUSH_UP": "PUSH_UP R_value — 入栈/上推",
        "WELL": "WELL R_dest — 阻塞读/管道取值",
        "RETURN": "RETURN R_value — 函数返回",
        "HALT": "HALT — 暂停/阻塞（无操作数）",
        "ILLUMINATE": "ILLUMINATE R_value — 日志/调试输出",
        "LOCK": "LOCK R_mutex — 获取互斥锁",
        "BRANCH": "BRANCH R_cond, @label — 条件分支跳转",
        "WAIT": "WAIT R_cond — 等待条件满足",
    }

    sig = operand_docs.get(mnemonic, f"{mnemonic} [operands...] — {desc}")

    return {
        "signatures": [{
            "label": sig,
            "documentation": f"{symbol} {cn_name} — {desc}",
            "parameters": [],
        }],
        "activeSignature": 0,
        "activeParameter": 0,
    }


def get_definition(uri, line, character, source_lines):
    if line >= len(source_lines):
        return None
    source_line = source_lines[line]
    word = _extract_word(source_line, character)

    if word and word.startswith("@"):
        label_name = word[1:]
        for i, src_line in enumerate(source_lines):
            if label_name in src_line and ("@locus" in src_line or "@meta_locus" in src_line or "@xiangci" in src_line):
                return {
                    "uri": uri,
                    "range": {"start": {"line": i, "character": 0}, "end": {"line": i, "character": len(src_line)}},
                }
    return None


def get_document_symbols(source_lines):
    symbols = []
    for i, line in enumerate(source_lines):
        stripped = line.strip()
        if stripped.startswith("@locus "):
            name = stripped.replace("@locus", "").strip().rstrip("{").strip()
            symbols.append({
                "name": name,
                "kind": 12,
                "range": {"start": {"line": i, "character": 0}, "end": {"line": i, "character": len(line)}},
                "selectionRange": {"start": {"line": i, "character": 0}, "end": {"line": i, "character": len(line)}},
                "children": [],
            })
        elif stripped.startswith("@meta_locus "):
            name = stripped.replace("@meta_locus", "").strip().rstrip("{").strip()
            symbols.append({
                "name": f"[meta] {name}",
                "kind": 12,
                "range": {"start": {"line": i, "character": 0}, "end": {"line": i, "character": len(line)}},
                "selectionRange": {"start": {"line": i, "character": 0}, "end": {"line": i, "character": len(line)}},
                "children": [],
            })
        elif stripped.startswith("@xiangci"):
            symbols.append({
                "name": "象辞",
                "kind": 8,
                "range": {"start": {"line": i, "character": 0}, "end": {"line": i, "character": len(line)}},
                "selectionRange": {"start": {"line": i, "character": 0}, "end": {"line": i, "character": len(line)}},
                "children": [],
            })
    return symbols


def _extract_word(line, character):
    if character > len(line):
        character = len(line)
    start = character
    while start > 0 and (line[start - 1].isalnum() or line[start - 1] in ('_', '.', '@', '䷀', '䷁', '䷂', '䷃', '䷄', '䷅', '䷆', '䷇', '䷈', '䷉', '䷊', '䷋', '䷌', '䷍', '䷎', '䷏', '䷐', '䷑', '䷒', '䷓', '䷔', '䷕', '䷖', '䷗', '䷘', '䷙', '䷚', '䷛', '䷜', '䷝', '䷞', '䷟', '䷠', '䷡', '䷢', '䷣', '䷤', '䷥', '䷦', '䷧', '䷨', '䷩', '䷪', '䷫', '䷬', '䷭', '䷮', '䷯', '䷰', '䷱', '䷲', '䷳', '䷴', '䷵', '䷶', '䷷', '䷸', '䷹', '䷺', '䷻', '䷼', '䷽', '䷾', '䷿')):
        start -= 1
    end = character
    while end < len(line) and (line[end].isalnum() or line[end] in ('_', '.', '@')):
        end += 1
    word = line[start:end]
    if word.startswith('.') and word in MODIFIERS:
        return word
    if word.startswith('.'):
        word = word.lstrip('.')
    return word if word else None


def handle_request(request):
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        result = {
            "capabilities": {
                "completionProvider": {"triggerCharacters": [".", " ", "\t", "@", "䷀"]},
                "hoverProvider": True,
                "signatureHelpProvider": {"triggerCharacters": [" ", ","]},
                "definitionProvider": True,
                "documentSymbolProvider": True,
                "textDocumentSync": {"change": 1, "openClose": True},
                "publishDiagnostics": True,
            }
        }
    elif method == "textDocument/completion":
        uri = params.get("textDocument", {}).get("uri", "")
        pos = params.get("position", {})
        line = pos.get("line", 0)
        character = pos.get("character", 0)
        source = _get_source(uri)
        if source:
            source_lines = source.split("\n")
            items = get_completions(uri, line, character, source_lines)
            result = {"isIncomplete": False, "items": items}
        else:
            result = {"isIncomplete": False, "items": []}
    elif method == "textDocument/hover":
        uri = params.get("textDocument", {}).get("uri", "")
        pos = params.get("position", {})
        line = pos.get("line", 0)
        character = pos.get("character", 0)
        source = _get_source(uri)
        if source:
            source_lines = source.split("\n")
            result = get_hover(uri, line, character, source_lines)
        else:
            result = None
    elif method == "textDocument/signatureHelp":
        uri = params.get("textDocument", {}).get("uri", "")
        pos = params.get("position", {})
        line = pos.get("line", 0)
        character = pos.get("character", 0)
        source = _get_source(uri)
        if source:
            source_lines = source.split("\n")
            result = get_signature_help(uri, line, character, source_lines)
        else:
            result = None
    elif method == "textDocument/definition":
        uri = params.get("textDocument", {}).get("uri", "")
        pos = params.get("position", {})
        line = pos.get("line", 0)
        character = pos.get("character", 0)
        source = _get_source(uri)
        if source:
            source_lines = source.split("\n")
            result = get_definition(uri, line, character, source_lines)
        else:
            result = None
    elif method == "textDocument/documentSymbol":
        uri = params.get("textDocument", {}).get("uri", "")
        source = _get_source(uri)
        if source:
            source_lines = source.split("\n")
            result = get_document_symbols(source_lines)
        else:
            result = []
    elif method == "textDocument/didOpen":
        uri = params.get("textDocument", {}).get("uri", "")
        source = params.get("textDocument", {}).get("text", "")
        _store_source(uri, source)
        result = None
        diagnostics = get_diagnostics(uri, source)
        if diagnostics and req_id is not None:
            return {"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics", "params": {"uri": uri, "diagnostics": diagnostics}}
        return None
    elif method == "textDocument/didChange":
        uri = params.get("textDocument", {}).get("uri", "")
        changes = params.get("contentChanges", [])
        if changes:
            source = changes[0].get("text", "")
            _store_source(uri, source)
            diagnostics = get_diagnostics(uri, source)
            if diagnostics:
                return {"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics", "params": {"uri": uri, "diagnostics": diagnostics}}
        return None
    elif method == "initialized":
        return None
    else:
        result = None

    if req_id is not None and result is not None:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    return None


_source_cache: Dict[str, str] = {}


def _get_source(uri):
    if uri in _source_cache:
        return _source_cache[uri]
    path = uri.replace("file://", "")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def _store_source(uri, source):
    _source_cache[uri] = source


def main():
    import asyncio

    async def run():
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        transport, _ = await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            line = await reader.readline()
            if not line:
                break
            header = line.decode("utf-8").strip()
            content_length = 0
            if header.startswith("Content-Length:"):
                content_length = int(header.split(":")[1].strip())
                await reader.readline()

            if content_length > 0:
                body = await reader.read(content_length)
                try:
                    request = json.loads(body.decode("utf-8"))
                    response = handle_request(request)
                    if response:
                        resp_str = json.dumps(response)
                        sys.stdout.write(f"Content-Length: {len(resp_str.encode('utf-8'))}\r\n\r\n{resp_str}")
                        sys.stdout.flush()
                except Exception as e:
                    error = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
                    err_str = json.dumps(error)
                    sys.stdout.write(f"Content-Length: {len(err_str.encode('utf-8'))}\r\n\r\n{err_str}")
                    sys.stdout.flush()

    asyncio.run(run())


if __name__ == "__main__":
    main()
