#!/usr/bin/env python3
"""
EvoASM 自举汇编器生成器 v2.1
修复版：正确处理字符串缓冲区地址
"""

import sys

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
    "OR": 16, "XOR": 37, "NOT": 5, "CMP": 37
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

def string_to_evoasm(s, buf_reg="R4", ptr_reg="R10", char_reg="R1"):
    """
    将字符串转换为 EvoASM 代码
    buf_reg: 保存缓冲区起始地址的寄存器
    ptr_reg: 工作指针寄存器
    """
    lines = []
    lines.append(f"    ; 字符串: {repr(s)}")
    lines.append(f"    ; 分配缓冲区并保存地址到 {buf_reg}")
    lines.append(f"    ALLOC R0, 0")
    lines.append(f"    FELLOWSHIP {buf_reg}, R0      ; 保存缓冲区起始地址")
    lines.append(f"    FELLOWSHIP {ptr_reg}, R0      ; 工作指针")
    
    for i, c in enumerate(s):
        code = ord(c)
        if code >= 16:
            lines.append(f"    ABOUND {char_reg}, {code}")
        else:
            lines.append(f"    ; 小立即数 {code}")
            if code == 0:
                lines.append(f"    ABOUND R2, 16")
                lines.append(f"    ABOUND R3, 16")
                lines.append(f"    REDUCE R2, R3")
                lines.append(f"    FELLOWSHIP {char_reg}, R2")
            else:
                lines.append(f"    ABOUND R2, 16")
                lines.append(f"    ABOUND R3, {16 - code}")
                lines.append(f"    REDUCE R2, R3")
                lines.append(f"    FELLOWSHIP {char_reg}, R2")
        lines.append(f"    DISPERSE {ptr_reg}, {char_reg}")
        if i < len(s) - 1:
            lines.append(f"    ABOUND R2, 1")
            lines.append(f"    INCREASE {ptr_reg}, R2")
    
    lines.append(f"    ; 字符串结束符")
    lines.append(f"    ABOUND R2, 16")
    lines.append(f"    ABOUND R3, 16")
    lines.append(f"    REDUCE R2, R3")
    lines.append(f"    FELLOWSHIP {char_reg}, R2")
    lines.append(f"    DISPERSE {ptr_reg}, {char_reg}")
    return "\n".join(lines)

def print_with_reg(reg="R4"):
    """生成打印代码，使用指定寄存器中的地址"""
    lines = []
    lines.append(f"    ; 打印字符串（地址在 {reg}）")
    lines.append(f"    ABOUND R0, SYS_PRINT")
    lines.append(f"    FELLOWSHIP R1, {reg}      ; R1 = 字符串地址")
    lines.append(f"    RECV R0, 0")
    return "\n".join(lines)

def generate_minimal_assembler():
    """
    生成最小自举汇编器 - 修复版
    正确处理字符串缓冲区地址
    """
    
    code = """
; ============================================================
; EvoASM 最小自举汇编器 v0.2 - 修复版
; ============================================================
; 这是一个能够实际工作的 EvoASM 程序
; 功能：
;   1. 打印启动信息
;   2. 编码一个简单的程序（ABOUND + HALT）
;   3. 写入输出文件
; ============================================================

; 系统调用号
SYS_OPEN    EQU 0
SYS_READ    EQU 1
SYS_WRITE   EQU 2
SYS_CLOSE   EQU 3
SYS_MALLOC  EQU 10
SYS_PRINT   EQU 40
SYS_EXIT    EQU 255

; 文件模式
MODE_READ   EQU 0
MODE_WRITE  EQU 1

; 操作码
OPCODE_ABOUND    EQU 13
OPCODE_HALT      EQU 56

START:
    ; ========== 打印启动信息 ==========
"""
    
    code += "\n" + string_to_evoasm("EvoASM Bootstrap Assembler v0.2\n", "R4", "R10", "R1")
    code += "\n" + print_with_reg("R4")
    
    code += """
    
    ; ========== 分配输出缓冲区 ==========
    ALLOC R0, 0
    FELLOWSHIP R11, R0         ; R11 = 输出缓冲区指针
    ALLOC R0, 0
    FELLOWSHIP R12, R0         ; R12 = 输出缓冲区起始
    
    ; 初始化输出计数
    ABOUND R13, 16
    ABOUND R14, 16
    REDUCE R13, R14            ; R13 = 0 (输出字节计数)
    
    ; ========== 编码指令 1: ABOUND R0, 16 ==========
    ; 指令格式：4 字节
    ; byte1 = (opcode << 2) | modifier
    ; byte2 = 操作数扩展
    ; byte3 = dst 寄存器
    ; byte4 = src/立即数
    
    ; ABOUND 操作码 13 (0x0D)
    ; byte1 = (13 << 2) | 0 = 52 (0x34)
    ; byte2 = 0
    ; byte3 = 0 (R0)
    ; byte4 = 16
    
    ; byte1: 52
    ABOUND R5, 52
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ; byte2: 0
    ABOUND R5, 16
    ABOUND R6, 16
    REDUCE R5, R6
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ; byte3: 0 (R0)
    ABOUND R5, 16
    ABOUND R6, 16
    REDUCE R5, R6
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ; byte4: 16
    ABOUND R5, 16
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ; ========== 编码指令 2: HALT ==========
    ; HALT 操作码 56 (0x38)
    ; byte1 = (56 << 2) | 0 = 224 (0xE0)
    ; byte2 = 0
    ; byte3 = 0
    ; byte4 = 0
    
    ; byte1: 224
    ABOUND R5, 224
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ; byte2: 0
    ABOUND R5, 16
    ABOUND R6, 16
    REDUCE R5, R6
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ; byte3: 0
    ABOUND R5, 16
    ABOUND R6, 16
    REDUCE R5, R6
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ; byte4: 0
    ABOUND R5, 16
    ABOUND R6, 16
    REDUCE R5, R6
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ; ========== 打印生成信息 ==========
"""
    
    code += "\n" + string_to_evoasm("Generated 8 bytes of bytecode\n", "R4", "R10", "R1")
    code += "\n" + print_with_reg("R4")
    
    code += """
    
    ; ========== 构建输出文件名 ==========
"""
    
    code += "\n" + string_to_evoasm("output.raw", "R5", "R10", "R1")
    
    code += """
    
    ; ========== 打开输出文件 ==========
    ; R5 包含文件名地址
    ABOUND R0, SYS_OPEN
    FELLOWSHIP R1, R5          ; R1 = 文件名地址
    ABOUND R2, MODE_WRITE       ; R2 = 写模式
    RECV R0, 0
    FELLOWSHIP R6, R0           ; R6 = 文件描述符
    
    ; 检查是否打开成功 (fd != 0)
    ABOUND R1, 16
    ABOUND R2, 16
    REDUCE R1, R2               ; R1 = 0
    CMP R6, R1
    BRANCH R0, WRITE_FAILED     ; 如果 R6 == 0，跳转
    
    ; ========== 写入文件 ==========
"""
    
    code += "\n" + string_to_evoasm("Writing to output.raw...\n", "R4", "R10", "R1")
    code += "\n" + print_with_reg("R4")
    
    code += """
    
    ; 执行写入
    ; R6 = 文件描述符
    ; R12 = 输出缓冲区起始
    ; R13 = 字节计数
    ABOUND R0, SYS_WRITE
    FELLOWSHIP R1, R6           ; R1 = 文件描述符
    FELLOWSHIP R2, R12          ; R2 = 缓冲区地址
    FELLOWSHIP R3, R13          ; R3 = 字节计数
    RECV R0, 0
    FELLOWSHIP R7, R0           ; R7 = 实际写入的字节数
    
    ; 关闭文件
    ABOUND R0, SYS_CLOSE
    FELLOWSHIP R1, R6
    RECV R0, 0
    
    ; 打印成功信息
"""
    
    code += "\n" + string_to_evoasm("Success! Output written to output.raw\n", "R4", "R10", "R1")
    code += "\n" + print_with_reg("R4")
    
    code += """
    
    BRANCH R0, EXIT_PROGRAM

WRITE_FAILED:
    ; 打印错误信息
"""
    
    code += "\n" + string_to_evoasm("ERROR: Failed to open output file\n", "R4", "R10", "R1")
    code += "\n" + print_with_reg("R4")
    
    code += """

EXIT_PROGRAM:
    ; 打印完成信息
"""
    
    code += "\n" + string_to_evoasm("Done.\n", "R4", "R10", "R1")
    code += "\n" + print_with_reg("R4")
    
    code += """
    
    ; 退出
    ABOUND R0, SYS_EXIT
    RECV R0, 0

HALT
"""
    return code

def generate_simple_test():
    """
    生成一个简单的测试程序
    只打印 "Hello from EvoASM!"
    """
    
    code = """
; ============================================================
; EvoASM 简单测试程序
; ============================================================

SYS_PRINT   EQU 40
SYS_EXIT    EQU 255

START:
"""
    
    code += "\n" + string_to_evoasm("Hello from EvoASM!\n", "R4", "R10", "R1")
    code += "\n" + print_with_reg("R4")
    
    code += """
    
    ABOUND R0, SYS_EXIT
    RECV R0, 0

HALT
"""
    return code

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 evoasm_bootstrap_gen.py <command>")
        print("Commands:")
        print("  minimal  - 生成最小自举汇编器")
        print("  test     - 生成简单测试程序")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "minimal":
        print(generate_minimal_assembler())
    elif cmd == "test":
        print(generate_simple_test())
    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()
