#!/usr/bin/env python3
"""
易衍·Evomorph 自举编译器
EvoASM 简化汇编器 - 增强版
支持：标签、跳转、宏、EQU 常量

语法：
  指令助记符 操作数1, 操作数2
  label:           ; 标签定义
  BRANCH R0, label ; 条件跳转
  %macro name n    ; 宏定义
  %endmacro        ; 宏结束
  NAME EQU value   ; 常量定义

这是实现完全自举的第一阶段编译器
"""

import sys
import os
from typing import Dict, List, Optional, Tuple

OPCODES = {
    "CREA": 63, "RECV": 0, "ALLOC": 17, "SPRT": 34,
    "WAIT": 23, "LOCK": 58, "BRANCH": 2, "MERGE": 16,
    "FELLOWSHIP": 61, "ABUNDANCE": 47, "YIELD": 4, "SPECULATE": 8,
    "FOLLOWING": 25, "MUT": 38, "RETURN": 1, "BARRIER": 39,
    "MATE": 62, "GATHER": 24, "PUSH_UP": 6, "WELL": 22,
    "REPLACE": 29, "CAST": 46, "SHOCK": 9, "STILL": 36,
    "GRADUAL": 52, "ABOUND": 13, "JOY": 27, "DISPERSE": 50,
    "TRUST": 51, "MICRO": 12, "SYNC": 21, "FUTU": 42,
    "HALT": 56, "INCREASE": 49, "REDUCE": 35, "SHL": 55,
    "STEP": 59, "PREFETCH": 57, "SHR": 7, "AND": 3,
    "APPROACH": 3, "OR": 16, "XOR": 37, "ADORN": 37,
    "NOT": 5, "OBSCURE": 5, "CMP": 37, "PENETRATE": 54
}

MODIFIERS = {
    ".ASYNC": 0x10, ".ATOMIC": 0x20, ".PRIV": 0x40,
    ".WEAK": 0x01, ".STRONG": 0x02, ".VOLATILE": 0x08
}

SYSCALLS = {
    "OPEN": 0, "READ": 1, "WRITE": 2, "CLOSE": 3,
    "MALLOC": 10, "FREE": 11, "MEMCPY": 12, "MEMSET": 13, "MEMCMP": 14,
    "STRLEN": 20, "STRCMP": 21, "STRCPY": 22, "STRCAT": 23, "STRCHR": 24,
    "ISDIGIT": 30, "ISALPHA": 31, "ISALNUM": 32, "ISSPACE": 33,
    "TOUPPER": 34, "TOLOWER": 35, "ATOI": 36,
    "PRINT": 40, "PRINTLN": 41, "SCAN": 42,
    "EXIT": 255
}


class Macro:
    """宏定义"""
    def __init__(self, name: str, param_count: int, body: List[str]):
        self.name = name.upper()
        self.param_count = param_count
        self.body = body


class Assembler:
    """增强版 EvoASM 汇编器"""
    
    def __init__(self):
        self.labels: Dict[str, int] = {}
        self.equis: Dict[str, int] = {}
        self.macros: Dict[str, Macro] = {}
        self.pending_labels: List[Tuple[int, int, str]] = []
        self.current_address = 0
        
    def tokenize(self, line: str) -> List[str]:
        """词法分析"""
        tokens = []
        current = ""
        i = 0
        in_string = False
        string_char = None
        
        while i < len(line):
            c = line[i]
            
            if c == ';':
                if not in_string:
                    break
            
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

    def parse_operand(self, token: str, allow_32bit: bool = False) -> Tuple[int, bool, bool, str, int]:
        """解析操作数
        返回: (值, 是否为寄存器, 是否为标签引用, 标签名, 完整值(用于32位))
        """
        token = token.upper()
        full_value = 0
        
        if token.startswith("R") and len(token) > 1:
            try:
                reg_num = int(token[1:])
                val = reg_num & 0x0F
                return (val, True, False, "", val)
            except ValueError:
                pass
        
        if token.startswith("0X"):
            try:
                full_value = int(token, 16)
                if allow_32bit:
                    return (full_value & 0xFF, False, False, "", full_value)
                else:
                    return (full_value & 0xFF, False, False, "", full_value)
            except ValueError:
                pass
        
        if token.startswith("0B"):
            try:
                full_value = int(token, 2)
                if allow_32bit:
                    return (full_value & 0xFF, False, False, "", full_value)
                else:
                    return (full_value & 0xFF, False, False, "", full_value)
            except ValueError:
                pass
        
        try:
            full_value = int(token)
            if allow_32bit:
                return (full_value & 0xFF, False, False, "", full_value)
            else:
                return (full_value & 0xFF, False, False, "", full_value)
        except ValueError:
            pass
        
        if token in SYSCALLS:
            full_value = SYSCALLS[token]
            return (full_value, False, False, "", full_value)
        
        if token in self.equis:
            full_value = self.equis[token]
            if allow_32bit:
                return (full_value & 0xFF, False, False, "", full_value)
            else:
                return (full_value & 0xFF, False, False, "", full_value)
        
        return (0, False, True, token, 0)

    def encode_instruction(self, mnemonic: str, operands: List[str], 
                           modifier: int = 0, line_num: int = 0) -> Optional[bytes]:
        """编码单条指令"""
        mnemonic = mnemonic.upper()
        
        if mnemonic not in OPCODES:
            print(f"Warning: Unknown mnemonic '{mnemonic}' at line {line_num}")
            return None
        
        opcode = OPCODES[mnemonic]
        
        while len(operands) < 2:
            operands.append("0")
        
        op1_val, op1_is_reg, op1_is_label, op1_label, op1_full = self.parse_operand(operands[0])
        op2_val, op2_is_reg, op2_is_label, op2_label, op2_full = self.parse_operand(operands[1])
        
        is_async_branch = (mnemonic == "BRANCH") and (modifier & 0x10)
        
        if op1_is_label and op1_label:
            if op1_label in self.labels:
                label_addr = self.labels[op1_label]
                op1_full = label_addr
                op1_val = label_addr & 0xFF
                if label_addr > 255:
                    if is_async_branch:
                        print(f"Info: Long jump to {op1_label} (0x{label_addr:04X}) using register indirect at line {line_num}")
                    else:
                        print(f"Warning: Label '{op1_label}' at address 0x{label_addr:04X} exceeds 8-bit limit (255) at line {line_num}")
                        print(f"         Use '.ASYNC BRANCH' with register indirect for long jumps")
            else:
                self.pending_labels.append((self.current_address, 2, op1_label, is_async_branch))
        
        if op2_is_label and op2_label:
            if op2_label in self.labels:
                label_addr = self.labels[op2_label]
                op2_full = label_addr
                if is_async_branch:
                    print(f"Error: .ASYNC BRANCH expects register for target, not label at line {line_num}")
                    print(f"       Use: ABOUND Rx, label_address  then  .ASYNC BRANCH cond, Rx")
                else:
                    op2_val = label_addr & 0xFF
                    if label_addr > 255:
                        print(f"Warning: Label '{op2_label}' at address 0x{label_addr:04X} exceeds 8-bit limit (255) at line {line_num}")
                        print(f"         Use '.ASYNC BRANCH' with register indirect for long jumps")
            else:
                self.pending_labels.append((self.current_address, 3, op2_label, is_async_branch))
        
        byte1 = ((opcode & 0x3F) << 2) | ((modifier >> 4) & 0x03)
        byte2 = modifier & 0x0F
        byte3 = op1_val
        byte4 = op2_val
        
        return bytes([byte1, byte2, byte3, byte4])

    def expand_macro(self, macro: Macro, args: List[str]) -> List[str]:
        """展开宏"""
        expanded = []
        for line in macro.body:
            result = line
            for i, arg in enumerate(args):
                result = result.replace(f"%{i+1}", arg)
            expanded.append(result)
        return expanded

    def expand_line_recursive(self, line: str, depth: int = 0) -> List[str]:
        """递归展开一行中的宏调用（支持嵌套宏）"""
        if depth > 10:
            return [line]
        
        tokens = self.tokenize(line)
        if tokens and tokens[0].upper() in self.macros:
            macro = self.macros[tokens[0].upper()]
            args = tokens[1:] if len(tokens) > 1 else []
            expanded_lines = self.expand_macro(macro, args)
            
            result = []
            for exp_line in expanded_lines:
                result.extend(self.expand_line_recursive(exp_line, depth + 1))
            return result
        else:
            return [line]
    
    def preprocess(self, lines: List[str]) -> List[str]:
        """预处理：处理宏定义和展开（支持嵌套宏）"""
        result = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith("%macro"):
                tokens = self.tokenize(line)
                if len(tokens) >= 3:
                    macro_name = tokens[1]
                    try:
                        param_count = int(tokens[2])
                    except ValueError:
                        param_count = 0
                    
                    macro_body = []
                    i += 1
                    while i < len(lines):
                        macro_line = lines[i].strip()
                        if macro_line.startswith("%endmacro"):
                            break
                        macro_body.append(macro_line)
                        i += 1
                    
                    self.macros[macro_name.upper()] = Macro(macro_name, param_count, macro_body)
                i += 1
                continue
            
            if line.startswith("EQU ") or " EQU " in line.upper():
                tokens = self.tokenize(line)
                if len(tokens) >= 3 and tokens[1].upper() == "EQU":
                    name = tokens[0].upper()
                    val = 0
                    val_token = tokens[2]
                    if val_token.startswith("0x") or val_token.startswith("0X"):
                        val = int(val_token, 16)
                    elif val_token.startswith("0b") or val_token.startswith("0B"):
                        val = int(val_token, 2)
                    else:
                        try:
                            val = int(val_token)
                        except ValueError:
                            if val_token.upper() in SYSCALLS:
                                val = SYSCALLS[val_token.upper()]
                    self.equis[name] = val
                i += 1
                continue
            
            expanded = self.expand_line_recursive(line)
            result.extend(expanded)
            
            i += 1
        
        return result

    def first_pass(self, lines: List[str]) -> List[Tuple[str, int, List[str]]]:
        """第一遍：收集标签，计算地址"""
        result = []
        self.current_address = 0
        self.labels = {}
        
        for line_num, line in enumerate(lines, 1):
            tokens = self.tokenize(line)
            
            if not tokens:
                continue
            
            if len(tokens) >= 2 and tokens[1] == ":":
                label_name = tokens[0].upper()
                self.labels[label_name] = self.current_address
                tokens = tokens[2:]
            
            if tokens and len(tokens) >= 1 and tokens[0].endswith(":"):
                label_name = tokens[0][:-1].upper()
                self.labels[label_name] = self.current_address
                tokens = tokens[1:]
            
            if tokens and (tokens[0].upper() in OPCODES or 
                          tokens[0].upper() in MODIFIERS):
                result.append((line, line_num, tokens))
                self.current_address += 4
        
        return result

    def second_pass(self, instructions: List[Tuple[str, int, List[str]]]) -> bytes:
        """第二遍：生成字节码，解析标签引用"""
        bytecode = bytearray()
        self.current_address = 0
        self.pending_labels = []
        
        for line, line_num, tokens in instructions:
            modifier = 0
            mnemonic_idx = 0
            
            if tokens and tokens[0].upper() in MODIFIERS:
                modifier = MODIFIERS[tokens[0].upper()]
                mnemonic_idx = 1
            
            if mnemonic_idx >= len(tokens):
                continue
            
            mnemonic = tokens[mnemonic_idx].upper()
            operands = []
            
            i = mnemonic_idx + 1
            while i < len(tokens):
                if tokens[i] != ',':
                    operands.append(tokens[i])
                i += 1
            
            encoded = self.encode_instruction(mnemonic, operands, modifier, line_num)
            if encoded:
                bytecode.extend(encoded)
                self.current_address += 4
        
        for pending in self.pending_labels:
            addr, byte_offset, label_name, is_async_branch = pending
            if label_name in self.labels:
                label_addr = self.labels[label_name]
                if addr + byte_offset < len(bytecode):
                    if is_async_branch:
                        print(f"Info: Long jump target '{label_name}' at 0x{label_addr:04X} (will use register indirect)")
                    else:
                        bytecode[addr + byte_offset] = label_addr & 0xFF
                        if label_addr > 255:
                            print(f"Warning: Label '{label_name}' at address 0x{label_addr:04X} exceeds 8-bit limit")
                            print(f"         Use '.ASYNC BRANCH' with register indirect for long jumps")
            else:
                print(f"Warning: Undefined label '{label_name}'")
        
        return bytes(bytecode)

    def assemble(self, source: str) -> bytes:
        """汇编源代码为原始字节码"""
        lines = source.split('\n')
        
        lines = self.preprocess(lines)
        
        instructions = self.first_pass(lines)
        
        bytecode = self.second_pass(instructions)
        
        return bytecode


def assemble_file(input_path: str, output_path: str = None) -> bytes:
    """汇编文件"""
    with open(input_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    assembler = Assembler()
    bytecode = assembler.assemble(source)
    
    if output_path is None:
        base = os.path.splitext(input_path)[0]
        output_path = base + ".raw"
    
    with open(output_path, 'wb') as f:
        f.write(bytecode)
    
    print(f"Assembled: {input_path} -> {output_path}")
    print(f"Generated: {len(bytecode)} bytes")
    print(f"Labels: {assembler.labels}")
    print(f"Constants: {assembler.equis}")
    print(f"Macros: {list(assembler.macros.keys())}")
    
    return bytecode


def disassemble(bytecode: bytes) -> List[Dict]:
    """反汇编字节码"""
    instructions = []
    offset = 0
    
    opcode_to_mnemonic = {v: k for k, v in OPCODES.items()}
    
    while offset < len(bytecode):
        if offset + 3 >= len(bytecode):
            break
        
        byte1 = bytecode[offset]
        byte2 = bytecode[offset + 1]
        operand1 = bytecode[offset + 2]
        operand2 = bytecode[offset + 3]
        
        opcode = (byte1 >> 2) & 0x3F
        modifier = ((byte1 & 0x03) << 4) | (byte2 & 0x0F)
        
        mnemonic = opcode_to_mnemonic.get(opcode, f"UNKNOWN_{opcode:02X}")
        
        instructions.append({
            "offset": offset,
            "opcode": opcode,
            "modifier": modifier,
            "mnemonic": mnemonic,
            "operand1": operand1,
            "operand2": operand2,
            "raw": [byte1, byte2, operand1, operand2]
        })
        
        offset += 4
    
    return instructions


def print_disassembly(instructions: List[Dict]):
    """打印反汇编结果"""
    print("\n" + "=" * 70)
    print("Disassembly")
    print("=" * 70)
    print(f"{'Offset':<8} {'Hex':<14} {'Mnemonic':<12} {'Operands'}")
    print("-" * 70)
    
    for instr in instructions:
        hex_str = " ".join(f"{b:02X}" for b in instr["raw"])
        op1 = f"R{instr['operand1']}" if instr['operand1'] < 16 else f"{instr['operand1']}"
        op2 = f"R{instr['operand2']}" if instr['operand2'] < 16 else f"{instr['operand2']}"
        print(f"{instr['offset']:08X} {hex_str:<14} {instr['mnemonic']:<12} {op1}, {op2}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="易衍·Evomorph EvoASM 汇编器 (增强版)")
    parser.add_argument("input", help="输入 .evoasm 文件")
    parser.add_argument("-o", "--output", help="输出 .raw 文件")
    parser.add_argument("-d", "--disassemble", action="store_true", help="反汇编输出")
    
    args = parser.parse_args()
    
    bytecode = assemble_file(args.input, args.output)
    
    if args.disassemble:
        instructions = disassemble(bytecode)
        print_disassembly(instructions)


if __name__ == "__main__":
    main()
