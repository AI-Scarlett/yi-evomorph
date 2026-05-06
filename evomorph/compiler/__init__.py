from __future__ import annotations
from evomorph.hexagrams import HexagramInstructionSet
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum, auto

class ErrorSeverity(Enum):
    ERROR = auto()
    WARNING = auto()
    NOTE = auto()


class ErrorType(Enum):
    SYNTAX_ERROR = auto()
    SEMANTIC_ERROR = auto()
    TYPE_ERROR = auto()
    UNDEFINED_SYMBOL = auto()
    REDEFINED_SYMBOL = auto()
    INVALID_OPERAND = auto()
    INVALID_OPCODE = auto()
    MISSING_ATTRIBUTE = auto()
    INVALID_FITNESS = auto()
    INVALID_ENV_TARGET = auto()


@dataclass
class CompilerError:
    type: ErrorType
    message: str
    line: int = 0
    col: int = 0
    severity: ErrorSeverity = ErrorSeverity.ERROR
    context: str = ""
    suggestion: Optional[str] = None

    def __str__(self):
        return f"{self.severity.name} L{self.line}:{self.col}: {self.message}"


class CompilerDiagnostics:
    def __init__(self):
        self.errors: List[CompilerError] = []
        self.warnings: List[CompilerError] = []
        self.notes: List[CompilerError] = []

    def add_error(self, error: CompilerError):
        if error.severity == ErrorSeverity.ERROR:
            self.errors.append(error)
        elif error.severity == ErrorSeverity.WARNING:
            self.warnings.append(error)
        else:
            self.notes.append(error)

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def get_all(self) -> List[CompilerError]:
        return self.errors + self.warnings + self.notes

    def count(self) -> Dict[str, int]:
        return {
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "notes": len(self.notes)
        }



def _extract_evo_metadata(source: str) -> Dict[str, Any]:
    """从 .evo 源码中提取元数据 (不依赖 lexer/parser)。

    返回:
        {"loci": [...], "meta_loci": [...], "xiangci": [...], "version": "3.0"}
    每个 locus 包含 name 和基本属性，instructions 为空列表。
    """
    import re

    loci = []
    meta_loci = []
    xiangci = []
    version = "3.0"

    # 提取版本
    vm = re.search(r'@evolang\s+"([^"]*)"', source)
    if vm:
        version = vm.group(1)

    # 提取象辞块
    for m in re.finditer(r'@xiangci\s*\{([^}]*)\}', source, re.DOTALL):
        xiangci.append(m.group(1).strip())

    # 提取 gene locus 和 meta locus 块
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
            "cross_pool": 0,
            "env_targets": [],
            "max_generations": 0,
            "fitness_terms": [],
        }

        # 在 locus 块内提取属性
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

        # mut_rate
        mr = re.search(r'mut_rate\s*=\s*([0-9.]+)', block)
        if mr:
            locus["mut_rate"] = float(mr.group(1))

        # fitness
        fm = re.search(r'fitness\s*=\s*(\S+)', block)
        if fm:
            locus["fitness_terms"] = [{
                "keyword": fm.group(1),
                "weight": 1.0
            }]

        # env_target
        et = re.search(r'env_target\s*=\s*\[([^\]]*)\]', block)
        if et:
            locus["env_targets"] = [
                t.strip().strip('"') for t in et.group(1).split(",") if t.strip()
            ]

        # max_generations
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


class IChingEvocCompiler:
    """易衍自举编译器 — 完全走 IChing EVB 路径，不依赖 Python 编译器。

    编译链路:
      - evb 格式: IChing EVB 编译器 (VM 中执行) → 纯 EVB 字节码
      - dict/json 格式: 源码文本解析提取元数据 + IChing EVB 编译器注入字节码

    PythonEvocCompiler 不再作为回退路径。
    """

    def __init__(self, instruction_set=None):
        self.isa = instruction_set or HexagramInstructionSet()
        self.diagnostics = CompilerDiagnostics()
        self.optimization_level = 0
        self._iching_compiler = None

    def _get_iching_compiler(self):
        if self._iching_compiler is None:
            from evomorph.bootstrap.iching.iching_compiler import IChingBootstrapCompiler
            self._iching_compiler = IChingBootstrapCompiler()
        return self._iching_compiler

    def set_optimization_level(self, level: int):
        self.optimization_level = max(0, min(3, level))

    def compile(self, source, output_format="json"):
        """编译 .evo 源码。

        路径:
          - evb: IChing EVB 编译器 (真正自举路径) — 失败即报错，不降级
          - dict/json: 文本元数据提取 + IChing 字节码注入
        """
        self.diagnostics = CompilerDiagnostics()

        # Step 1: IChing EVB 编译器生成字节码
        iching_success = False
        evob_bytes = b""
        iching_result = {}
        iching_error = None
        try:
            bc = self._get_iching_compiler()
            iching_result = bc.compile_source(source)
            if iching_result.get("success") and iching_result.get("evob_valid"):
                iching_success = True
                evob_bytes = iching_result.get("output_bytes", b"")
            else:
                iching_error = iching_result.get("error", "IChing compilation failed")
        except Exception as e:
            iching_error = str(e)

        # evb 格式 — 纯 IChing 路径，失败即报错
        if output_format == "evb":
            if iching_success:
                return evob_bytes
            self.diagnostics.add_error(CompilerError(
                type=ErrorType.SEMANTIC_ERROR,
                message=f"IChing EVB compiler error: {iching_error}",
                severity=ErrorSeverity.ERROR
            ))
            return self._generate_error_output()

        # dict/json 格式: 文本元数据提取
        py_result = _extract_evo_metadata(source)

        # 注入 IChing 字节码
        if iching_success:
            self._inject_iching_bytecode(py_result, evob_bytes, iching_result, source)
        elif iching_error:
            self.diagnostics.add_error(CompilerError(
                type=ErrorType.SEMANTIC_ERROR,
                message=f"IChing bytecode generation failed: {iching_error}",
                severity=ErrorSeverity.WARNING
            ))

        if output_format == "json":
            import json
            return json.dumps(py_result, ensure_ascii=False, indent=2)
        return py_result

    def _inject_iching_bytecode(self, py_result: dict, evob_bytes: bytes,
                                 iching_result: dict, source: str) -> None:
        """将 IChing 编译器生成的字节码注入到 Python 解析的结构中.

        策略:
          1. 从源码中解析每个 locus 的 GUAXU 块, 统计指令数量
          2. 解码 IChing 字节码为指令列表
          3. 按 locus 指令数量分割字节码并注入
        """
        import struct as _struct

        # 从 IChing EVB 提取总字节码 (跳过 header)
        # compile_source 返回的 EVOB 已 compact，字节码直接跟在 header 后
        if evob_bytes[:4] == b'EVOB':
            hsize = _struct.unpack(">H", evob_bytes[6:8])[0]
            all_bc = evob_bytes[hsize:]
        else:
            all_bc = evob_bytes

        # 解码全部 IChing 字节码为指令列表 (含字节偏移和大小)
        all_instrs = self._decode_evob_bytecode_with_sizes(all_bc)

        # 从源码解析每个 locus 的指令数量
        locus_instr_counts = self._parse_locus_instruction_counts(source)
        py_loci = py_result.get("loci", [])

        instr_idx = 0
        for i, locus in enumerate(py_loci):
            n_instrs = locus_instr_counts[i] if i < len(locus_instr_counts) else 0
            if n_instrs == 0 or instr_idx >= len(all_instrs):
                continue

            # 从 IChing 字节码中取出对应数量的指令
            end_idx = min(instr_idx + n_instrs, len(all_instrs))
            locus_instrs = all_instrs[instr_idx:end_idx]
            if not locus_instrs:
                continue

            # 计算该 locus 的字节码范围并提取
            bc_start_pos = locus_instrs[0]["_byte_offset"]
            bc_end_pos = locus_instrs[-1]["_byte_offset"] + locus_instrs[-1]["_byte_size"]
            locus_bc = all_bc[bc_start_pos:bc_end_pos]

            # 更新 locus 数据
            locus["bytecode"] = list(locus_bc)
            locus["instructions"] = [
                {k: v for k, v in instr.items() if not k.startswith("_")}
                for instr in locus_instrs
            ]
            instr_idx = end_idx

    @staticmethod
    def _parse_locus_instruction_counts(source: str) -> list:
        """从 .evo 源码中解析每个 locus 的 GUAXU 块指令数量.

        返回每 locus 指令数的列表, 顺序与源码一致.
        """
        import re

        counts = []
        in_locus = False
        in_guaxu = False
        brace_depth = 0
        instr_count = 0

        for line in source.split('\n'):
            stripped = line.strip()

            if not in_locus:
                if stripped.startswith('@locus '):
                    in_locus = True
                    instr_count = 0
                    brace_depth = 0
                    # 处理当前行的括号计数 (不能 continue)
                    brace_depth += stripped.count('{') - stripped.count('}')
                else:
                    continue
            else:
                brace_depth += stripped.count('{') - stripped.count('}')

            if not in_guaxu:
                if 'GUAXU' in stripped and ':' in stripped:
                    in_guaxu = True
                if brace_depth <= 0:
                    # locus 结束 (无 GUAXU 块)
                    counts.append(0)
                    in_locus = False
                continue

            # 在 GUAXU 块内
            # 跳过空行、注释、标签行
            if not stripped or stripped.startswith('//') or stripped.startswith('#'):
                pass
            elif stripped.rstrip().endswith(':') and not any(
                    op in stripped for op in ['@', '=', '{', '}', '"']):
                pass  # 标签行
            elif '{' in stripped or '}' in stripped:
                pass  # 括号行
            else:
                # 这是一条指令
                instr_count += 1

            if brace_depth <= 0:
                # GUAXU 块和 locus 结束
                counts.append(instr_count)
                in_guaxu = False
                in_locus = False

        # 处理未闭合的 locus
        if in_locus and in_guaxu:
            counts.append(instr_count)

        return counts

    def _decode_evob_bytecode_with_sizes(self, bytecode: bytes) -> list:
        """将 EVB 字节码解码为指令列表, 含每条指令的字节偏移和大小."""
        from evomorph.bootstrap.iching.iching_compiler import MNEMONICS, NATIVE_MNEMONICS, NATIVE_IMM_ALWAYS

        opcode_to_mnem = {opc: mname for mname, opc in MNEMONICS}
        native_opc_to_mnem = {opc: mname for mname, opc in NATIVE_MNEMONICS}

        instructions = []
        pos = 0
        idx = 0

        while pos < len(bytecode) and len(instructions) < 1024:
            b1 = bytecode[pos]
            itype = (b1 >> 6) & 0x03
            byte_offset = pos

            if itype == 0x02:  # IChing 指令 (4 字节)
                if pos + 4 > len(bytecode):
                    break
                opcode = b1 & 0x3F
                modifier = bytecode[pos + 1]
                op1 = bytecode[pos + 2]
                op2 = bytecode[pos + 3]
                mnem = opcode_to_mnem.get(opcode, f"?{opcode}")
                pos += 4
                instructions.append({
                    "opcode": opcode, "symbol": "???",
                    "mnemonic": mnem, "modifier": modifier,
                    "operands": [
                        {"kind": "register", "value": f"R{op1}"},
                        {"kind": "register", "value": f"R{op2}"},
                    ],
                    "offset": idx, "line": 0, "col": 0,
                    "_byte_offset": byte_offset, "_byte_size": 4,
                })
            elif itype == 0x01:  # Native 指令
                if pos + 3 > len(bytecode):
                    break
                native_opc = b1 & 0x3F
                dst = bytecode[pos + 1] & 0x1F
                src = bytecode[pos + 2] & 0x1F
                has_imm = bool(bytecode[pos + 1] & 0x20)
                mnem = native_opc_to_mnem.get(native_opc, f"N?{native_opc}")
                instr = {
                    "opcode": native_opc, "symbol": "???",
                    "mnemonic": mnem, "modifier": 0,
                    "operands": [
                        {"kind": "register", "value": f"R{dst}"},
                        {"kind": "register", "value": f"R{src}"},
                    ],
                    "offset": idx, "line": 0, "col": 0,
                    "_byte_offset": byte_offset, "_byte_size": 3,
                }
                pos += 3
                import struct as _struct
                if has_imm or native_opc in NATIVE_IMM_ALWAYS:
                    if pos + 4 <= len(bytecode):
                        imm = _struct.unpack('<I', bytecode[pos:pos + 4])[0]
                        instr["operands"].append({"kind": "immediate", "value": imm})
                        instr["_byte_size"] += 4
                        pos += 4
                instructions.append(instr)
            else:
                break
            idx += 1

        return instructions

    def compile_file(self, filepath, output_format="json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            return self.compile(source, output_format)
        except FileNotFoundError:
            self.diagnostics.add_error(CompilerError(
                type=ErrorType.SEMANTIC_ERROR,
                message=f"File not found: {filepath}",
                severity=ErrorSeverity.ERROR
            ))
            return self._generate_error_output()
        except Exception as e:
            self.diagnostics.add_error(CompilerError(
                type=ErrorType.SEMANTIC_ERROR,
                message=f"Error reading file: {str(e)}",
                severity=ErrorSeverity.ERROR
            ))
            return self._generate_error_output()

    def _make_operands(self, instr):
        ops = []
        op1 = instr.get("op1", 0)
        op2 = instr.get("op2", 0)
        if op1 is not None:
            ops.append({"kind": "register", "value": f"R{op1}"})
        if op2 is not None:
            if instr.get("imm") is not None:
                ops.append({"kind": "immediate", "value": instr["imm"]})
            else:
                ops.append({"kind": "register", "value": f"R{op2}"})
        return ops

    def _generate_error_output(self) -> Dict[str, Any]:
        return {
            "error": True,
            "errors": [
                {
                    "type": e.type.name,
                    "message": e.message,
                    "line": e.line,
                    "col": e.col,
                    "severity": e.severity.name,
                    "suggestion": e.suggestion
                }
                for e in self.diagnostics.errors
            ],
            "warnings": [
                {
                    "message": w.message,
                    "line": w.line,
                    "col": w.col,
                    "suggestion": w.suggestion
                }
                for w in self.diagnostics.warnings
            ],
            "count": self.diagnostics.count()
        }


EvocCompiler = IChingEvocCompiler
