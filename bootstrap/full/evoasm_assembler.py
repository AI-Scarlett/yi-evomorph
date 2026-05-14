#!/usr/bin/env python3
"""
易衍·Evomorph EvoASM 汇编器 (Bootstrap Tool)
将 .evoasm 源码汇编为 .raw 字节码，供 IChingVM 执行。

支持特性:
- %macro / %endmacro 宏定义和展开
- EQU 常量定义
- 标签 (label:) 和标签引用
- 所有 64 条六十四卦指令
- 寄存器 R0-R15
- 十进制、十六进制(0x)、二进制(0b)立即数
- 注释 (;)

指令编码格式 (4 字节/指令):
    byte1: ((opcode & 0x3F) << 2) | ((modifier >> 4) & 0x03)
    byte2: modifier & 0x0F
    byte3: operand1 (寄存器号或立即数低8位)
    byte4: operand2 (寄存器号或立即数低8位)
"""

import sys
import os
import re
import struct
from typing import Dict, List, Tuple, Optional

# ============================================================
# 64 卦指令集 - 助记符到操作码映射
# ============================================================
MNEMONIC_TO_OPCODE: Dict[str, int] = {
    # 核心指令
    "ABOUND": 13,     # 加载立即数
    "FELLOWSHIP": 61, # 寄存器复制
    "INCREASE": 49,   # 加法
    "REDUCE": 35,     # 减法
    "DISPERSE": 50,   # 内存存储
    "PENETRATE": 54,  # 内存加载
    "ALLOC": 17,      # 内存分配
    "HALT": 56,       # 停止
    "RECV": 0,        # 系统调用
    "BRANCH": 2,      # 条件跳转
    "CREA": 63,       # 创建进程/线程
    "RETURN": 1,      # 返回

    # 位运算
    "AND": 3, "APPROACH": 3,
    "OR": 16, "MERGE": 16,
    "XOR": 37, "ADORN": 37,
    "SHL": 55, "PREFETCH": 55,
    "SHR": 7, "FLUSH": 7,
    "OBSCURE": 5,

    # 其他指令
    "SPRT": 34, "WAIT": 23, "LOCK": 58,
    "ABUNDANCE": 47, "YIELD": 4, "SPECULATE": 8,
    "FOLLOWING": 25, "MUT": 38, "CONTEMPLATE": 48,
    "BITE": 41, "STRIP": 32, "INTRINSIC": 57,
    "BARRIER": 39, "NOURISH": 33, "OVERLOAD": 30,
    "TRAP": 18, "ILLUMINATE": 45, "SENSE": 28,
    "PERSIST": 14, "RETREAT": 60, "THRUST": 15,
    "ADVANCE": 40, "BIND": 53, "CONVERT": 43,
    "LAME": 20, "UNLOCK": 10, "BREAK": 31,
    "MATE": 62, "GATHER": 24, "PUSH_UP": 6,
    "TRAPPED": 26, "WELL": 22, "REPLACE": 29,
    "CAST": 46, "SHOCK": 9, "STILL": 36,
    "GRADUAL": 52, "MISMATCH": 11, "TRAVEL": 44,
    "JOY": 27, "THROTTLE": 19, "TRUST": 51,
    "MICRO": 12, "SYNC": 21, "FUTU": 42,
    "STEP": 59,
}

# 大写化的别名
for name, op in list(MNEMONIC_TO_OPCODE.items()):
    MNEMONIC_TO_OPCODE[name.lower()] = op


class EvoASMAssembler:
    """EvoASM 汇编器 - 支持宏、常量、标签"""

    def __init__(self):
        self.macros: Dict[str, Tuple[int, List[str]]] = {}  # name -> (argc, body_lines)
        self.constants: Dict[str, int] = {}  # name -> value
        self.labels: Dict[str, int] = {}  # name -> address (in bytes)

    def parse_number(self, token: str) -> int:
        """解析数字 token"""
        token = token.strip()
        if token.startswith('0x') or token.startswith('0X'):
            return int(token, 16)
        elif token.startswith('0b') or token.startswith('0B'):
            return int(token, 2)
        elif token.startswith('0') and len(token) > 1 and token[1].isdigit():
            return int(token, 8)
        else:
            try:
                return int(token)
            except ValueError:
                return 0

    def is_register(self, token: str) -> bool:
        """检查是否为寄存器"""
        token = token.strip().upper()
        if token.startswith('R'):
            try:
                r = int(token[1:])
                return 0 <= r <= 15
            except ValueError:
                pass
        return False

    def parse_register(self, token: str) -> int:
        """解析寄存器号"""
        return int(token.strip().upper()[1:])

    def resolve_operand(self, token: str) -> int:
        """解析操作数: 寄存器、立即数、常量、标签"""
        token = token.strip()
        if not token:
            return 0
        if self.is_register(token):
            return self.parse_register(token)
        if token.upper() in self.constants:
            return self.constants[token.upper()]
        if token in self.labels:
            return self.labels[token]
        return self.parse_number(token) & 0xFF

    def tokenize_line(self, line: str) -> List[str]:
        """将一行拆分为 token 列表"""
        tokens = []
        current = ""
        in_string = False
        string_char = None
        i = 0

        while i < len(line):
            c = line[i]

            # 注释
            if c == ';' and not in_string:
                break

            # 字符串处理
            if in_string:
                if c == string_char:
                    current += c
                    tokens.append(current)
                    current = ""
                    in_string = False
                else:
                    current += c
                i += 1
                continue

            if c in '"\'':
                if current:
                    tokens.append(current)
                    current = ""
                in_string = True
                string_char = c
                current += c
                i += 1
                continue

            # 分隔符
            if c.isspace():
                if current:
                    tokens.append(current)
                    current = ""
            elif c in ',:':
                if current:
                    tokens.append(current)
                    current = ""
                tokens.append(c)
            else:
                current += c
            i += 1

        if current:
            tokens.append(current)

        return tokens

    def preprocess(self, source: str) -> List[str]:
        """预处理: 展开宏、解析 EQU"""
        lines = source.split('\n')
        result_lines = []

        # 第一遍: 收集宏定义和常量
        i = 0
        clean_lines = []  # 去掉宏定义和 EQU 后的行
        while i < len(lines):
            line = lines[i].rstrip()

            # 跳过空行和纯注释行
            stripped = line.strip()
            if not stripped or stripped.startswith(';'):
                clean_lines.append(line)
                i += 1
                continue

            # EQU 常量定义
            tokens = self.tokenize_line(line)
            if len(tokens) >= 3 and tokens[1].upper() == 'EQU':
                name = tokens[0].upper()
                value = self.resolve_operand(tokens[2])
                self.constants[name] = value
                i += 1
                continue

            # %macro 定义
            if tokens and tokens[0].upper() == '%MACRO':
                if len(tokens) >= 3:
                    macro_name = tokens[1].upper()
                    try:
                        argc = int(tokens[2])
                    except ValueError:
                        argc = 0
                    body = []
                    i += 1
                    while i < len(lines):
                        body_line = lines[i].rstrip()
                        if body_line.strip().upper().startswith('%ENDMACRO'):
                            break
                        body.append(body_line)
                        i += 1
                    self.macros[macro_name] = (argc, body)
                i += 1
                continue

            clean_lines.append(line)
            i += 1

        # 第二遍: 展开宏调用
        for line in clean_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(';'):
                result_lines.append(line)
                continue

            # 检查是否为宏调用
            tokens = self.tokenize_line(line)
            if tokens and tokens[0].upper() in self.macros:
                macro_name = tokens[0].upper()
                argc, body = self.macros[macro_name]
                args = [t for t in tokens[1:] if t != ','] if len(tokens) > 1 else []

                # 展开宏体
                for body_line in body:
                    expanded = body_line
                    for ai, arg in enumerate(args):
                        # 替换 %1, %2, ... 为实际参数
                        expanded = expanded.replace(f'%{ai + 1}', arg)
                    # 处理嵌套宏调用，按换行符拆分为多行
                    expanded = self._expand_inline(expanded)
                    for sub_line in expanded.split('\n'):
                        result_lines.append(sub_line)
                continue

            result_lines.append(line)

        return result_lines

    def _expand_inline(self, line: str) -> str:
        """递归展开行内的宏调用"""
        tokens = self.tokenize_line(line)
        if tokens and tokens[0].upper() in self.macros:
            macro_name = tokens[0].upper()
            argc, body = self.macros[macro_name]
            args = [t for t in tokens[1:] if t != ','] if len(tokens) > 1 else []
            # Expand the macro body, a single-line macro
            expanded = []
            for body_line in body:
                bl = body_line
                for ai, arg in enumerate(args):
                    bl = bl.replace(f'%{ai + 1}', arg)
                # Recursively expand nested macros in this line
                bl = self._expand_inline(bl)
                expanded.append(bl)
            # For inline use, return concatenated body (join with newlines if multi-line)
            result = '\n'.join(expanded)
            return result
        return line

    def assemble_line(self, line: str, current_address: int,
                      pass2: bool = True) -> Optional[bytes]:
        """汇编单行，返回 4 字节编码或 None"""
        tokens = self.tokenize_line(line)
        if not tokens:
            return None

        # 跳过注释行
        if tokens[0].startswith(';'):
            return None

        first_token = tokens[0]

        # 标签定义: 'LABEL:' 或 'LABEL :' 两种格式
        # tokenizer 把 ':' 作为分隔符，所以 'LABEL:' -> ['LABEL', ':']
        is_label = False
        label_name = None
        instr_start = 1  # start index of instruction tokens

        if first_token.endswith(':'):
            # Format: LABEL:
            label_name = first_token[:-1].upper()
            is_label = True
            if len(tokens) > 1:
                instr_start = 1
        elif len(tokens) >= 2 and tokens[1] == ':':
            # Format: LABEL :
            label_name = first_token.upper()
            is_label = True
            instr_start = 2

        if is_label and label_name:
            self.labels[label_name] = current_address
            # 检查冒号后是否有指令
            if len(tokens) > instr_start:
                remaining = ' '.join(tokens[instr_start:])
                return self.assemble_line(remaining, current_address, pass2)
            return None

        # 检查是否为指令
        mnemonic = first_token.upper()
        if mnemonic not in MNEMONIC_TO_OPCODE:
            return None

        opcode = MNEMONIC_TO_OPCODE[mnemonic]

        # 收集操作数
        operands = []
        for tok in tokens[1:]:
            if tok == ',':
                continue
            operands.append(tok)

        # 解析操作数
        op1 = 0
        op2 = 0
        modifier = 0
        is_long_jump = False
        long_jump_addr = 0

        # BRANCH 远跳转检测 (16 位地址编码)
        if mnemonic == 'BRANCH' and pass2 and len(operands) >= 2:
            target_token = operands[1]
            resolved = self.resolve_operand(target_token)
            if resolved > 255:
                is_long_jump = True
                long_jump_addr = resolved
                op1 = 1  # cond_reg placeholder (会被下面覆盖)
            else:
                op2 = resolved

        if not is_long_jump:
            if operands:
                op1 = self.resolve_operand(operands[0])
            if len(operands) >= 2:
                op2 = self.resolve_operand(operands[1])

        # 编码
        if is_long_jump:
            # 长跳转编码: byte1[0]=1, byte2=addr_hi, byte3=cond_reg, byte4=addr_lo
            op1 = self.resolve_operand(operands[0])  # cond_reg
            byte1 = ((opcode & 0x3F) << 2) | 0x01
            byte2 = (long_jump_addr >> 8) & 0xFF
            byte3 = op1 & 0xFF
            byte4 = long_jump_addr & 0xFF
        else:
            byte1 = ((opcode & 0x3F) << 2) | ((modifier >> 4) & 0x03)
            byte2 = modifier & 0x0F
            byte3 = op1 & 0xFF
            byte4 = op2 & 0xFF

        return bytes([byte1, byte2, byte3, byte4])

    def assemble(self, source: str, debug: bool = False) -> bytes:
        """两遍扫描汇编"""
        # 重置状态
        self.macros.clear()
        self.constants.clear()
        self.labels.clear()

        # 预处理
        lines = self.preprocess(source)

        if debug:
            print(f"[DEBUG] Preprocessed {len(lines)} lines")
            for i, line in enumerate(lines[:10]):
                print(f"  {i}: {line}")
            if len(lines) > 10:
                print(f"  ... ({len(lines) - 10} more lines)")
            print(f"[DEBUG] Constants: {self.constants}")
            print(f"[DEBUG] Macros: {list(self.macros.keys())}")

        # 第一遍: 收集标签地址
        address = 0
        valid_lines = []  # (line_index, line_text, address)
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(';'):
                # 保留注释和空行以保持行号对应
                valid_lines.append((line, address))
                continue

            tokens = self.tokenize_line(line)
            if not tokens:
                valid_lines.append((line, address))
                continue

            # 检查标签: 'LABEL:' 或 'LABEL :'
            first_token = tokens[0]
            is_label = False
            label_name = None
            instr_start = 1

            if first_token.endswith(':'):
                label_name = first_token[:-1].upper()
                is_label = True
                instr_start = 1
            elif len(tokens) >= 2 and tokens[1] == ':':
                label_name = first_token.upper()
                is_label = True
                instr_start = 2

            if is_label and label_name:
                self.labels[label_name] = address
                if debug:
                    print(f"[PASS1] Label '{label_name}' at address {address} (0x{address:04X})")
                # 检查标签后是否有指令
                remaining = ' '.join(tokens[instr_start:]).strip()
                if remaining:
                    valid_lines.append((remaining, address))
                    # 计算剩余部分是否为有效指令
                    rem_tokens = self.tokenize_line(remaining)
                    if rem_tokens and rem_tokens[0].upper() in MNEMONIC_TO_OPCODE:
                        address += 4
                continue

            # 检查是否为指令
            if first_token.upper() in MNEMONIC_TO_OPCODE:
                valid_lines.append((line, address))
                address += 4
            else:
                # 非指令行（可能是数据或其他）
                valid_lines.append((line, address))

        if debug:
            print(f"[PASS1] Total code size: {address} bytes ({address // 4} instructions)")
            print(f"[PASS1] Labels: {self.labels}")

        # 第二遍: 生成代码
        output = bytearray()
        for line, expected_addr in valid_lines:
            result = self.assemble_line(line, expected_addr, pass2=True)
            if result is not None:
                output.extend(result)
                if debug and len(output) < 200:
                    print(f"[PASS2] {expected_addr:4d}: {line[:50]:50s} -> "
                          f"{result[0]:02X} {result[1]:02X} {result[2]:02X} {result[3]:02X}")

        if debug:
            print(f"[PASS2] Output size: {len(output)} bytes ({len(output) // 4} instructions)")

        return bytes(output)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='易衍·Evomorph EvoASM 汇编器 - 将 .evoasm 源码汇编为 .raw 字节码'
    )
    parser.add_argument('input', help='输入 .evoasm 文件')
    parser.add_argument('-o', '--output', help='输出 .raw 文件 (默认: 输入文件名.raw)')
    parser.add_argument('-d', '--debug', action='store_true', help='调试模式')
    parser.add_argument('--hexdump', action='store_true', help='输出十六进制 dump')

    args = parser.parse_args()

    # 读取源文件
    with open(args.input, 'r', encoding='utf-8') as f:
        source = f.read()

    # 汇编
    assembler = EvoASMAssembler()
    bytecode = assembler.assemble(source, debug=args.debug)

    # 确定输出文件名
    output_file = args.output
    if not output_file:
        base = os.path.splitext(args.input)[0]
        output_file = base + '.raw'

    # 写入输出
    with open(output_file, 'wb') as f:
        f.write(bytecode)

    print(f"✓ 汇编完成: {args.input} -> {output_file}")
    print(f"  代码大小: {len(bytecode)} bytes ({len(bytecode) // 4} instructions)")
    print(f"  标签数: {len(assembler.labels)}")
    print(f"  常量数: {len(assembler.constants)}")

    if args.hexdump:
        print("\n十六进制 dump:")
        for i in range(0, len(bytecode), 16):
            hex_str = ' '.join(f'{b:02X}' for b in bytecode[i:i+16])
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in bytecode[i:i+16])
            print(f"  {i:06X}: {hex_str:<48s} |{ascii_str}|")

    return 0


if __name__ == '__main__':
    sys.exit(main())
