#!/usr/bin/env python3
"""
Evomorph 源码预处理模块 (Stage-0 Python 实现)

=== 计划状态 ===
这些函数最终将替换为 Evomorph 程序 (.evo → .evob):
  - preprocess.evob (组合 metadata_reader + label_resolver)
  - metadata_reader.evob  → 替代 _extract_evo_metadata()
  - label_resolver.evob   → 替代 _resolve_guaxu_labels()

当前 Python 实现仅作为 stage0 引导，待编译器/汇编器能力成熟后替换。

=== 接口设计 ===
所有函数接受 str 输入，返回 dict/str。与未来 .evob 版本接口保持一致，
确保替换时调用方无需修改。
"""

import re
from typing import Dict, Any, List


# ---------------------------------------------------------------------------
# 1. 源码规范化 (Unicode → ASCII)
# ---------------------------------------------------------------------------

def normalize_source(source: str) -> str:
    """将 .evo 源码中的 Unicode 字符规范化为 ASCII 等价形式。

    编译器内部使用 ASCII 关键字 (GUAXU, CREA, FELLOWSHIP 等)，
    此步骤确保中文关键字和特殊字符被正确转换。

    未来: 编译器应直接支持 Unicode 输入，届时此函数可移除。
    """
    result = source
    # 去除卦象字符 (IChing hexagram symbols)
    result = re.sub(r'[\u4DC0-\u4DFF]', '', result)
    # 中文关键字 → 英文关键字
    result = result.replace('\u5366\u5E8F', 'GUAXU')  # 卦序 → GUAXU
    # 智能引号 → 直引号
    result = result.replace('\u201C', '"')
    result = result.replace('\u201D', '"')
    # 全角括号 → 半角括号
    result = result.replace('\uFF08', '(')
    result = result.replace('\uFF09', ')')
    return result


# ---------------------------------------------------------------------------
# 2. GUAXU Block 内 Label 解析
# ---------------------------------------------------------------------------

def resolve_guaxu_labels(source: str,
                          iching_opcodes: set = None,
                          native_opcodes: set = None,
                          native_imm_always: set = None,
                          native_no_operand: set = None) -> str:
    """解析 GUAXU 块中的 label 引用，将 @label_name 替换为 #offset。

    编译器 GUAXU 块中的指令使用 label 引用目标地址，
    此函数计算每条指令的偏移量并将 label 替换为立即数偏移。

    Args:
        source: 已规范化的源码
        iching_opcodes: IChing 指令助记符集合
        native_opcodes: Native 指令助记符集合
        native_imm_always: 始终带立即数的 native 指令
        native_no_operand: 无操作数的 native 指令

    Returns:
        解析后的源码
    """
    if iching_opcodes is None:
        iching_opcodes = _DEFAULT_ICHING_OPCODES
    if native_opcodes is None:
        native_opcodes = _DEFAULT_NATIVE_OPCODES
    if native_imm_always is None:
        native_imm_always = _DEFAULT_NATIVE_IMM_ALWAYS
    if native_no_operand is None:
        native_no_operand = _DEFAULT_NATIVE_NO_OPERAND

    lines = source.split('\n')
    result_lines = []
    in_guaxu = False
    guaxu_lines = []
    brace_depth = 0

    for line in lines:
        stripped = line.strip()
        if not in_guaxu:
            if 'GUAXU' in stripped and ':' in stripped:
                in_guaxu = True
                guaxu_lines = []
                brace_depth = stripped.count('{') - stripped.count('}')
            result_lines.append(line)
            continue

        brace_depth += stripped.count('{') - stripped.count('}')
        guaxu_lines.append(line)

        if brace_depth <= 0:
            resolved = _resolve_labels_in_block(
                guaxu_lines, iching_opcodes, native_opcodes,
                native_imm_always, native_no_operand
            )
            result_lines.extend(resolved)
            in_guaxu = False
            guaxu_lines = []

    if in_guaxu and guaxu_lines:
        resolved = _resolve_labels_in_block(
            guaxu_lines, iching_opcodes, native_opcodes,
            native_imm_always, native_no_operand
        )
        result_lines.extend(resolved)

    return '\n'.join(result_lines)


def _resolve_labels_in_block(lines: List[str],
                              iching_opcodes: set,
                              native_opcodes: set,
                              native_imm_always: set,
                              native_no_operand: set) -> List[str]:
    """解析单个 GUAXU 块内的标签。"""
    labels = {}
    instructions = []
    offset = 0

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('//'):
            instructions.append((offset, line, None))
            continue

        words = stripped.split()
        if not words:
            instructions.append((offset, line, None))
            continue

        raw_first = words[0]
        first = raw_first.rstrip(':')
        is_label = (raw_first.endswith(':')
                    or (stripped.rstrip().endswith(':')
                        and first not in iching_opcodes
                        and first not in native_opcodes))
        if is_label:
            labels[first] = offset
            instructions.append((offset, line, None))
            continue

        if first in iching_opcodes:
            size = 4
        elif first in native_opcodes:
            if first in native_no_operand:
                size = 3
            elif first in native_imm_always:
                size = 7
            else:
                has_imm = any(
                    w.startswith('#') or w.isdigit()
                    or (w.startswith('0x') and len(w) > 2)
                    for w in words[1:]
                )
                size = 7 if has_imm else 3
        else:
            size = 0
        instructions.append((offset, line, first))
        offset += size

    result = []
    for off, line, mnemonic in instructions:
        if mnemonic is None:
            result.append(line)
            continue
        stripped = line.strip()
        if any(lbl in stripped for lbl in labels):
            resolved = re.sub(
                r'(?<![a-zA-Z_#])('
                + '|'.join(re.escape(k) for k in labels)
                + r')(?![a-zA-Z_0-9])',
                lambda m: '#' + str(labels[m.group(1)]),
                stripped
            )
            result.append('    ' + resolved)
        else:
            result.append(line)
    return result


# ---------------------------------------------------------------------------
# 3. 元数据提取
# ---------------------------------------------------------------------------

def extract_evo_metadata(source: str) -> Dict[str, Any]:
    """从 .evo 源码提取元数据 (locus 定义、属性、象辞)。

    不依赖 lexer/parser，仅做浅层文本解析。

    返回:
        {"loci": [...], "meta_loci": [...], "xiangci": [...], "version": "3.0"}

    未来: 替换为 metadata_reader.evob
    """
    loci = []
    meta_loci = []
    xiangci = []
    version = "3.0"

    vm = re.search(r'@evolang\s+"([^"]*)"', source)
    if vm:
        version = vm.group(1)

    for m in re.finditer(r'@xiangci\s*\{([^}]*)\}', source, re.DOTALL):
        xiangci.append(m.group(1).strip())

    for m in re.finditer(
        r'@(?P<type>locus|meta_locus)\s+(?P<name>[\w.]+)\s*\{',
        source
    ):
        is_meta = m.group("type") == "meta_locus"
        name = m.group("name")
        locus = {
            "name": name,
            "instructions": [],
            "bytecode": [],
            "mut_rate": 0.02,
            "cross_pool": "default",
            "env_targets": [],
            "max_generations": 0,
            "fitness_terms": [],
        }

        brace_open = m.end()
        depth = 1
        i = brace_open
        block = ""
        while i < len(source) and depth > 0:
            c = source[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            if depth > 0:
                block += c
            i += 1

        mr = re.search(r'mut_rate\s*=\s*([0-9.]+)', block)
        if mr:
            locus["mut_rate"] = float(mr.group(1))

        fm = re.search(r'fitness\s*=\s*(\S+)', block)
        if fm:
            locus["fitness_terms"] = [{"keyword": fm.group(1), "weight": 1.0}]

        et = re.search(r'env_target\s*=\s*\[([^\]]*)\]', block)
        if et:
            locus["env_targets"] = [
                t.strip().strip('"') for t in et.group(1).split(",") if t.strip()
            ]

        mg = re.search(r'max_generations\s*=\s*(\d+)', block)
        if mg:
            locus["max_generations"] = int(mg.group(1))

        if is_meta:
            meta_loci.append(locus)
        else:
            loci.append(locus)

    return {
        "loci": loci,
        "meta_loci": meta_loci,
        "xiangci": xiangci,
        "version": version,
    }


# ---------------------------------------------------------------------------
# 4. 默认操作码表 (与 iching_compiler.py 保持同步)
# ---------------------------------------------------------------------------

_DEFAULT_ICHING_OPCODES = {
    "RECV", "RETURN", "BRANCH", "APPROACH", "YIELD", "OBSCURE",
    "PUSH_UP", "FLUSH", "SPECULATE", "SHOCK", "UNLOCK", "MISMATCH",
    "MICRO", "ABOUND", "PERSIST", "THRUST", "MERGE", "ALLOC", "TRAP",
    "THROTTLE", "LAME", "SYNC", "WELL", "WAIT", "GATHER", "FOLLOWING",
    "TRAPPED", "JOY", "SENSE", "REPLACE", "OVERLOAD", "BREAK",
    "STRIP", "NOURISH", "SPRT", "REDUCE", "STILL", "ADORN", "MUT",
    "BARRIER", "ADVANCE", "BITE", "FUTU", "CONVERT", "TRAVEL",
    "ILLUMINATE", "CAST", "ABUNDANCE", "CONTEMPLATE", "INCREASE",
    "DISPERSE", "TRUST", "GRADUAL", "BIND", "PENETRATE", "PREFETCH",
    "HALT", "INTRINSIC", "LOCK", "STEP", "RETREAT", "FELLOWSHIP",
    "MATE", "CREA",
}

_DEFAULT_NATIVE_OPCODES = {
    "NOP", "HLT", "ADD", "SUB", "MUL", "DIV", "MOD", "INC", "DEC",
    "NEG", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "SAR",
    "CMP", "CMPI", "TEST", "JMP", "JE", "JNE", "JL", "JLE", "JG",
    "JGE", "JC", "JNC", "CALL", "RET", "MOV", "MOVI", "LDR", "STR",
    "PUSHA", "POPA", "PUSH", "POP", "LDRB", "STRB",
}

_DEFAULT_NATIVE_IMM_ALWAYS = {
    "CMPI", "JMP", "JE", "JNE", "JL", "JLE", "JG", "JGE",
    "JC", "JNC", "MOVI", "CALL",
}

_DEFAULT_NATIVE_NO_OPERAND = {"NOP", "HLT", "RET", "PUSHA", "POPA"}
