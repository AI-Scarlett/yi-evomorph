#!/usr/bin/env python3
"""
易衍·Evomorph 自举编译器
EvoASM 简化汇编器 - 增强版 v2.0
支持：标签、跳转、宏、EQU 常量、自动长跳转处理

新增功能：
- 自动检测长跳转（目标 > 255）
- 自动生成寄存器间接跳转代码
- 三扫描法：计算初始地址 -> 检测长跳转 -> 重新计算地址 -> 生成代码
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

LONG_JUMP_EXTRA_BYTES = 28


class Macro:
    def __init__(self, name: str, param_count: int, body: List[str]):
        self.name = name
        self.param_count = param_count
        self.body = body


class LongJumpInfo:
    def __init__(self, line_num: int, original_address: int, 
                 condition_reg: str, target_label: str):
        self.line_num = line_num
        self.original_address = original_address
        self.condition_reg = condition_reg
        self.target_label = target_label
        self.extra_bytes = 0


class Assembler:
    """增强版 EvoASM 汇编器 - 支持自动长跳转"""
    
    def __init__(self):
        self.labels: Dict[str, int] = {}
        self.adjusted_labels: Dict[str, int] = {}
        self.equis: Dict[str, int] = {}
        self.macros: Dict[str, Macro] = {}
        self.pending_labels: List[Tuple[int, int, str, bool]] = []
        self.current_address = 0
        self.long_jumps: List[LongJumpInfo] = []
        self.long_jump_map: Dict[int, LongJumpInfo] = {}
        self.temp_reg = "R5"
        self.shift_reg = "R6"
    
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
                return (full_value & 0xFF, False, False, "", full_value)
            except ValueError:
                pass
        
        if token.startswith("0B"):
            try:
                full_value = int(token, 2)
                return (full_value & 0xFF, False, False, "", full_value)
            except ValueError:
                pass
        
        try:
            full_value = int(token)
            return (full_value & 0xFF, False, False, "", full_value)
        except ValueError:
            pass
        
        if token in SYSCALLS:
            full_value = SYSCALLS[token]
            return (full_value, False, False, "", full_value)
        
        if token in self.equis:
            full_value = self.equis[token]
            return (full_value & 0xFF, False, False, "", full_value)
        
        return (0, False, True, token, 0)

    def encode_instruction_simple(self, mnemonic: str, operands: List[str], 
                                   modifier: int = 0, line_num: int = 0,
                                   use_adjusted_labels: bool = False) -> Optional[bytes]:
        """简单编码单条指令（不处理长跳转）"""
        mnemonic = mnemonic.upper()
        
        if mnemonic not in OPCODES:
            print(f"Warning: Unknown mnemonic '{mnemonic}' at line {line_num}")
            return None
        
        opcode = OPCODES[mnemonic]
        
        while len(operands) < 2:
            operands.append("0")
        
        op1_val, op1_is_reg, op1_is_label, op1_label, op1_full = self.parse_operand(operands[0])
        op2_val, op2_is_reg, op2_is_label, op2_label, op2_full = self.parse_operand(operands[1])
        
        labels_to_use = self.adjusted_labels if use_adjusted_labels else self.labels
        
        if op1_is_label and op1_label:
            if op1_label in labels_to_use:
                label_addr = labels_to_use[op1_label]
                op1_full = label_addr
                op1_val = label_addr & 0xFF
                if label_addr > 255:
                    print(f"Warning: Label '{op1_label}' at address 0x{label_addr:04X} exceeds 8-bit limit at line {line_num}")
            else:
                self.pending_labels.append((self.current_address, 2, op1_label, False))
        
        if op2_is_label and op2_label:
            if op2_label in labels_to_use:
                label_addr = labels_to_use[op2_label]
                op2_full = label_addr
                op2_val = label_addr & 0xFF
                if label_addr > 255:
                    print(f"Warning: Label '{op2_label}' at address 0x{label_addr:04X} exceeds 8-bit limit at line {line_num}")
            else:
                self.pending_labels.append((self.current_address, 3, op2_label, False))
        
        byte1 = ((opcode & 0x3F) << 2) | ((modifier >> 4) & 0x03)
        byte2 = modifier & 0x0F
        byte3 = op1_val
        byte4 = op2_val
        
        return bytes([byte1, byte2, byte3, byte4])

    def generate_long_jump_code(self, condition_reg: str, target_address: int, line_num: int) -> bytes:
        """生成长跳转代码序列
        
        正确的代码生成逻辑：
        - ABOUND: 直接设置寄存器值 (reg[dst] = val)
        - MICRO: 加法 (reg[dst] = reg[dst] + val)
        - SHL: 左移 (reg[dst] = reg[dst] << reg[src])
        
        注意：PREFETCH 助记符映射到操作码 57，在虚拟机中是寄存器复制（INTRINSIC）
              正确的左移助记符是 SHL（操作码 55）
        
        对于地址 0x032C (812):
            ABOUND R5, 3           ; R5 = 3 (byte2)
            ABOUND R6, 8            ; R6 = 8
            SHL R5, R6              ; R5 = 3 << 8 = 768
            MICRO R5, 44            ; R5 = 768 + 44 = 812
            .ASYNC BRANCH R1, R5
        """
        code = b""
        
        byte1 = (target_address >> 16) & 0xFF
        byte2 = (target_address >> 8) & 0xFF
        byte3 = target_address & 0xFF
        
        print(f"  Debug: target_address={target_address}, byte1={byte1}, byte2={byte2}, byte3={byte3}")
        
        if byte1 > 0:
            ins = self.encode_instruction_simple("ABOUND", [self.temp_reg, str(byte1)], line_num=line_num)
            if ins:
                code += ins
            
            ins = self.encode_instruction_simple("ABOUND", [self.shift_reg, "16"], line_num=line_num)
            if ins:
                code += ins
            ins = self.encode_instruction_simple("SHL", [self.temp_reg, self.shift_reg], line_num=line_num)
            if ins:
                code += ins
            
            if byte2 > 0:
                ins = self.encode_instruction_simple("ABOUND", [self.shift_reg, "8"], line_num=line_num)
                if ins:
                    code += ins
                ins = self.encode_instruction_simple("SHL", [self.temp_reg, self.shift_reg], line_num=line_num)
                if ins:
                    code += ins
                ins = self.encode_instruction_simple("MICRO", [self.temp_reg, str(byte2)], line_num=line_num)
                if ins:
                    code += ins
            
            if byte3 > 0:
                if byte2 == 0:
                    ins = self.encode_instruction_simple("ABOUND", [self.shift_reg, "8"], line_num=line_num)
                    if ins:
                        code += ins
                    ins = self.encode_instruction_simple("SHL", [self.temp_reg, self.shift_reg], line_num=line_num)
                    if ins:
                        code += ins
                ins = self.encode_instruction_simple("MICRO", [self.temp_reg, str(byte3)], line_num=line_num)
                if ins:
                    code += ins
        
        elif byte2 > 0:
            ins = self.encode_instruction_simple("ABOUND", [self.temp_reg, str(byte2)], line_num=line_num)
            if ins:
                code += ins
            
            ins = self.encode_instruction_simple("ABOUND", [self.shift_reg, "8"], line_num=line_num)
            if ins:
                code += ins
            ins = self.encode_instruction_simple("SHL", [self.temp_reg, self.shift_reg], line_num=line_num)
            if ins:
                code += ins
            
            if byte3 > 0:
                ins = self.encode_instruction_simple("MICRO", [self.temp_reg, str(byte3)], line_num=line_num)
                if ins:
                    code += ins
        
        else:
            ins = self.encode_instruction_simple("ABOUND", [self.temp_reg, str(byte3)], line_num=line_num)
            if ins:
                code += ins
        
        ins = self.encode_instruction_simple("BRANCH", [condition_reg, self.temp_reg], 
                                              modifier=MODIFIERS[".ASYNC"], line_num=line_num)
        if ins:
            code += ins
        
        print(f"  Debug: Generated {len(code)} bytes for long jump")
        return code

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
        """递归展开一行中的宏调用"""
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
        """预处理：处理宏定义和展开"""
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

    def first_pass_base(self, lines: List[str]) -> Tuple[List[Tuple[str, int, List[str]]], Dict[str, int]]:
        """第一遍基础扫描：收集标签，计算初始地址"""
        result = []
        self.current_address = 0
        labels = {}
        
        for line_num, line in enumerate(lines, 1):
            tokens = self.tokenize(line)
            
            if not tokens:
                continue
            
            if len(tokens) >= 2 and tokens[1] == ":":
                label_name = tokens[0].upper()
                labels[label_name] = self.current_address
                tokens = tokens[2:]
            
            if tokens and len(tokens) >= 1 and tokens[0].endswith(":"):
                label_name = tokens[0][:-1].upper()
                labels[label_name] = self.current_address
                tokens = tokens[1:]
            
            if tokens and (tokens[0].upper() in OPCODES or 
                          tokens[0].upper() in MODIFIERS):
                result.append((line, line_num, tokens))
                self.current_address += 4
        
        return result, labels

    def analyze_long_jumps(self, instructions: List[Tuple[str, int, List[str]]], labels: Dict[str, int]) -> List[LongJumpInfo]:
        """分析哪些BRANCH指令需要长跳转处理"""
        long_jumps = []
        
        for line, line_num, tokens in instructions:
            modifier = 0
            mnemonic_idx = 0
            
            if tokens and tokens[0].upper() in MODIFIERS:
                modifier = MODIFIERS[tokens[0].upper()]
                mnemonic_idx = 1
            
            if len(tokens) <= mnemonic_idx:
                continue
            
            mnemonic = tokens[mnemonic_idx].upper()
            
            if mnemonic != "BRANCH":
                continue
            
            is_async = (modifier & MODIFIERS[".ASYNC"]) != 0
            
            operands_start = mnemonic_idx + 1
            operands = []
            for t in tokens[operands_start:]:
                if t != ",":
                    operands.append(t)
            
            if len(operands) >= 2:
                cond_reg = operands[0]
                target = operands[1]
                
                _, _, is_label, label_name, _ = self.parse_operand(target)
                
                if is_label and label_name in labels:
                    target_addr = labels[label_name]
                    
                    if target_addr > 255 and not is_async:
                        lj = LongJumpInfo(line_num, labels.get("START", 0), cond_reg, label_name)
                        lj.extra_bytes = LONG_JUMP_EXTRA_BYTES
                        long_jumps.append(lj)
                        print(f"Info: Detected long jump at line {line_num} to {label_name} (0x{target_addr:04X})")
        
        return long_jumps

    def calculate_adjusted_addresses(self, lines: List[str], long_jumps: List[LongJumpInfo]) -> Dict[str, int]:
        """计算调整后的地址（考虑长跳转的额外字节）"""
        adjusted_labels = {}
        current_address = 0
        
        long_jump_set = {lj.line_num for lj in long_jumps}
        
        for line_num, line in enumerate(lines, 1):
            tokens = self.tokenize(line)
            
            if not tokens:
                continue
            
            if len(tokens) >= 2 and tokens[1] == ":":
                label_name = tokens[0].upper()
                adjusted_labels[label_name] = current_address
                tokens = tokens[2:]
            
            if tokens and len(tokens) >= 1 and tokens[0].endswith(":"):
                label_name = tokens[0][:-1].upper()
                adjusted_labels[label_name] = current_address
                tokens = tokens[1:]
            
            if tokens and (tokens[0].upper() in OPCODES or 
                          tokens[0].upper() in MODIFIERS):
                if line_num in long_jump_set:
                    current_address += LONG_JUMP_EXTRA_BYTES
                else:
                    current_address += 4
        
        return adjusted_labels

    def assemble(self, source: str) -> Tuple[bytes, Dict[str, int], Dict[str, int], Dict[str, Macro]]:
        """完整汇编过程"""
        lines = source.splitlines()
        
        print("Phase 1: Preprocessing...")
        preprocessed = self.preprocess(lines)
        
        print("Phase 2: First pass (base addresses)...")
        instructions, self.labels = self.first_pass_base(preprocessed)
        
        print("Phase 3: Analyzing long jumps...")
        self.long_jumps = self.analyze_long_jumps(instructions, self.labels)
        
        if self.long_jumps:
            print(f"Found {len(self.long_jumps)} long jumps, adjusting addresses...")
            
            max_iterations = 5
            for iteration in range(max_iterations):
                self.adjusted_labels = self.calculate_adjusted_addresses(preprocessed, self.long_jumps)
                
                new_long_jumps = self.analyze_long_jumps(instructions, self.adjusted_labels)
                
                old_set = {(lj.line_num, lj.target_label) for lj in self.long_jumps}
                new_set = {(lj.line_num, lj.target_label) for lj in new_long_jumps}
                
                if old_set == new_set:
                    print(f"Address calculation stabilized after {iteration + 1} iterations")
                    break
                
                self.long_jumps = new_long_jumps
            else:
                print("Warning: Address calculation did not stabilize, using last iteration")
        else:
            self.adjusted_labels = self.labels.copy()
        
        print("Phase 4: Generating bytecode...")
        bytecode = b""
        
        for line, line_num, tokens in instructions:
            modifier = 0
            mnemonic_idx = 0
            
            if tokens and tokens[0].upper() in MODIFIERS:
                modifier = MODIFIERS[tokens[0].upper()]
                mnemonic_idx = 1
            
            if len(tokens) <= mnemonic_idx:
                continue
            
            mnemonic = tokens[mnemonic_idx].upper()
            
            operands_start = mnemonic_idx + 1
            operands = []
            for t in tokens[operands_start:]:
                if t != ",":
                    operands.append(t)
            
            is_long_jump = False
            if mnemonic == "BRANCH" and len(operands) >= 2:
                target = operands[1]
                _, _, is_label, label_name, _ = self.parse_operand(target)
                
                if is_label and label_name in self.adjusted_labels:
                    target_addr = self.adjusted_labels[label_name]
                    if target_addr > 255 and (modifier & MODIFIERS[".ASYNC"]) == 0:
                        print(f"  Generating long jump code for line {line_num} to {label_name} (0x{target_addr:04X})")
                        
                        cond_reg = operands[0]
                        long_jump_code = self.generate_long_jump_code(cond_reg, target_addr, line_num)
                        bytecode += long_jump_code
                        is_long_jump = True
            
            if not is_long_jump:
                encoded = self.encode_instruction_simple(mnemonic, operands, modifier, line_num, use_adjusted_labels=True)
                if encoded:
                    bytecode += encoded
        
        print(f"Generated {len(bytecode)} bytes")
        print(f"Labels: {self.adjusted_labels}")
        print(f"Constants: {self.equis}")
        
        return bytecode, self.adjusted_labels, self.equis, self.macros


def main():
    if len(sys.argv) < 2:
        print("Usage: evoasm_assembler.py <input.evoasm> [-o output.raw]")
        print("       evoasm_assembler.py compile <input.evoasm> [output.raw]")
        sys.exit(1)
    
    input_file = None
    output_file = None
    
    if sys.argv[1] == "compile" and len(sys.argv) >= 3:
        input_file = sys.argv[2]
        if len(sys.argv) >= 4:
            output_file = sys.argv[3]
    else:
        input_file = sys.argv[1]
        if "-o" in sys.argv:
            idx = sys.argv.index("-o")
            if idx + 1 < len(sys.argv):
                output_file = sys.argv[idx + 1]
    
    if not output_file:
        base = os.path.splitext(input_file)[0]
        output_file = base + ".raw"
    
    with open(input_file, 'r') as f:
        source = f.read()
    
    assembler = Assembler()
    bytecode, labels, equis, macros = assembler.assemble(source)
    
    with open(output_file, 'wb') as f:
        f.write(bytecode)
    
    print(f"Assembled: {input_file} -> {output_file}")
    print(f"Generated: {len(bytecode)} bytes")


if __name__ == "__main__":
    main()
