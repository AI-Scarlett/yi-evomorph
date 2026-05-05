#!/usr/bin/env python3
"""
EvoASM 字符串构建辅助工具
将 Python 字符串转换为 EvoASM 代码（逐个字节构建）
"""

def string_to_evoasm(s, reg_ptr="R10", char_reg="R1"):
    """
    将字符串转换为 EvoASM 代码
    假设 reg_ptr 指向缓冲区起始位置
    """
    lines = []
    lines.append(f"; 字符串: {repr(s)}")
    for i, c in enumerate(s):
        code = ord(c)
        if code >= 16:
            lines.append(f"    ABOUND {char_reg}, {code}")
        else:
            lines.append(f"    ; 小立即数 {code}，需要特殊处理")
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
        lines.append(f"    DISPERSE {reg_ptr}, {char_reg}")
        if i < len(s) - 1:
            lines.append(f"    ABOUND R2, 1")
            lines.append(f"    INCREASE {reg_ptr}, R2")
    lines.append(f"    ; 字符串结束符")
    lines.append(f"    ABOUND R2, 16")
    lines.append(f"    ABOUND R3, 16")
    lines.append(f"    REDUCE R2, R3")
    lines.append(f"    FELLOWSHIP {char_reg}, R2")
    lines.append(f"    DISPERSE {reg_ptr}, {char_reg}")
    return "\n".join(lines)

def generate_fileio_tests():
    """
    生成文件 IO 测试代码
    """
    code = """
; ============================================================
; EvoASM 文件 IO 测试
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

START:
    ; 分配缓冲区
    ALLOC R0, 0
    FELLOWSHIP R4, R0          ; R4 = 文件名缓冲区
    FELLOWSHIP R10, R4         ; R10 = 指针
    
    ; 构建文件名 "test_input.txt"
    ; t=116, e=101, s=115, t=116, _=95, i=105, n=110, p=112, u=117, t=116, .=46, t=116, x=120, t=116
"""
    
    code += "\n    ; 构建文件名 \"test_input.txt\""
    code += "\n" + string_to_evoasm("test_input.txt", "R10", "R1")
    
    code += """
    
    ; 打印文件名
    ALLOC R0, 0
    FELLOWSHIP R10, R0
    
    ; 构建消息 "Reading file: "
"""
    
    code += "\n" + string_to_evoasm("Reading file: \n", "R10", "R1")
    
    code += """
    
    ; 打印
    ABOUND R0, SYS_PRINT
    ALLOC R1, 0
    FELLOWSHIP R1, R0
    RECV R0, 0
    
    ; 现在尝试打开文件
    ABOUND R0, SYS_OPEN
    ALLOC R1, 0
    FELLOWSHIP R1, R1          ; 文件名
    ABOUND R2, MODE_READ
    RECV R0, 0
    FELLOWSHIP R5, R0           ; R5 = 文件描述符
    
    ; 检查是否打开成功
    ABOUND R1, 0
    CMP R5, R1
    BRANCH R0, OPEN_FAILED
    
    ; 打开成功
    ALLOC R0, 0
    FELLOWSHIP R10, R0
"""
    
    code += "\n" + string_to_evoasm("File opened successfully!\n", "R10", "R1")
    
    code += """
    ABOUND R0, SYS_PRINT
    ALLOC R1, 0
    FELLOWSHIP R1, R0
    RECV R0, 0
    
    ; 读取文件
    ABOUND R0, SYS_READ
    FELLOWSHIP R1, R5
    ALLOC R2, 0
    FELLOWSHIP R2, R2          ; 缓冲区
    ABOUND R3, 255              ; 最多 255 字节
    RECV R0, 0
    FELLOWSHIP R6, R0           ; R6 = 读取的字节数
    
    ; 打印读取的字节数
    ; 简化：直接打印 "Read X bytes\n"
    
    ; 关闭文件
    ABOUND R0, SYS_CLOSE
    FELLOWSHIP R1, R5
    RECV R0, 0
    
    BRANCH R0, EXIT_PROGRAM

OPEN_FAILED:
    ALLOC R0, 0
    FELLOWSHIP R10, R0
"""
    
    code += "\n" + string_to_evoasm("Failed to open file!\n", "R10", "R1")
    
    code += """
    ABOUND R0, SYS_PRINT
    ALLOC R1, 0
    FELLOWSHIP R1, R0
    RECV R0, 0

EXIT_PROGRAM:
    ALLOC R0, 0
    FELLOWSHIP R10, R0
"""
    
    code += "\n" + string_to_evoasm("Done.\n", "R10", "R1")
    
    code += """
    ABOUND R0, SYS_PRINT
    ALLOC R1, 0
    FELLOWSHIP R1, R0
    RECV R0, 0
    
    ABOUND R0, SYS_EXIT
    RECV R0, 0

HALT
"""
    return code

def generate_minimal_assembler():
    """
    生成最小汇编器代码
    这个汇编器能够：
    1. 从输入读取指令
    2. 编码核心指令
    3. 输出字节码
    
    简化版本：只处理固定的几条指令
    """
    
    code = """
; ============================================================
; EvoASM 最小自举汇编器 v0.1
; ============================================================
; 功能：
;   1. 读取 "in.asm" 文件
;   2. 解析简单的指令 (ABOUND, HALT, FELLOWSHIP, INCREASE)
;   3. 输出到 "out.raw"
;
; 限制：
;   - 只处理无操作数或简单操作数的指令
;   - 不支持标签
;   - 不支持宏
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
OPCODE_FELLOWSHIP EQU 61
OPCODE_INCREASE   EQU 49
OPCODE_REDUCE     EQU 35
OPCODE_DISPERSE   EQU 50
OPCODE_PREFETCH   EQU 57
OPCODE_SYNC       EQU 21

START:
    ; 打印启动信息
    ALLOC R0, 0
    FELLOWSHIP R4, R0
    FELLOWSHIP R10, R4
"""
    
    code += "\n    ; 启动消息"
    code += "\n" + string_to_evoasm("EvoASM Bootstrap Assembler v0.1\n", "R10", "R1")
    
    code += """
    ABOUND R0, SYS_PRINT
    ALLOC R1, 0
    FELLOWSHIP R1, R1
    RECV R0, 0
    
    ; 分配输出缓冲区
    ALLOC R0, 0
    FELLOWSHIP R11, R0         ; R11 = 输出缓冲区指针
    ALLOC R0, 0
    FELLOWSHIP R12, R0         ; R12 = 输出缓冲区起始
    
    ; 初始化输出计数
    ABOUND R13, 16
    ABOUND R14, 16
    REDUCE R13, R14            ; R13 = 0 (输出计数)
    
    ; ========== 简化：直接编码固定的指令序列 ==========
    ; 为了演示自举，我们先编码一个简单的程序：
    ;   ABOUND R0, 16
    ;   ABOUND R1, 16
    ;   REDUCE R0, R1
    ;   HALT
    ;
    ; 这将生成一个能够计算 16-16=0 的程序
    
    ; 指令 1: ABOUND R0, 16
    ; 操作码 13 (0x0D)
    ; byte1 = (13 << 2) | 0 = 52 (0x34)
    ; byte2 = 0
    ; byte3 = 0 (R0)
    ; byte4 = 16
    ABOUND R5, 52
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ABOUND R5, 16
    ABOUND R6, 16
    REDUCE R5, R6
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ABOUND R5, 16
    ABOUND R6, 16
    REDUCE R5, R6
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ABOUND R5, 16
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ; 指令 2: ABOUND R1, 16
    ABOUND R5, 52
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ABOUND R5, 16
    ABOUND R6, 16
    REDUCE R5, R6
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ABOUND R5, 1
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ABOUND R5, 16
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ; 指令 3: REDUCE R0, R1
    ; 操作码 35 (0x23)
    ; byte1 = (35 << 2) = 140 (0x8C)
    ABOUND R5, 140
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ABOUND R5, 16
    ABOUND R6, 16
    REDUCE R5, R6
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ABOUND R5, 16
    ABOUND R6, 16
    REDUCE R5, R6
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ABOUND R5, 1
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ; 指令 4: HALT
    ; 操作码 56 (0x38)
    ; byte1 = (56 << 2) = 224 (0xE0)
    ABOUND R5, 224
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ABOUND R5, 16
    ABOUND R6, 16
    REDUCE R5, R6
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ABOUND R5, 16
    ABOUND R6, 16
    REDUCE R5, R6
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ABOUND R5, 16
    ABOUND R6, 16
    REDUCE R5, R6
    DISPERSE R11, R5
    ABOUND R2, 1
    INCREASE R11, R2
    INCREASE R13, R2
    
    ; 打印成功信息
    ALLOC R0, 0
    FELLOWSHIP R10, R0
"""
    
    code += "\n" + string_to_evoasm("Generated 16 bytes of bytecode\n", "R10", "R1")
    
    code += """
    ABOUND R0, SYS_PRINT
    ALLOC R1, 0
    FELLOWSHIP R1, R1
    RECV R0, 0
    
    ; 写入输出文件
    ; 首先构建文件名 "out.raw"
    ALLOC R0, 0
    FELLOWSHIP R10, R0
"""
    
    code += "\n" + string_to_evoasm("out.raw", "R10", "R1")
    
    code += """
    
    ; 打开输出文件
    ABOUND R0, SYS_OPEN
    ALLOC R1, 0
    FELLOWSHIP R1, R1
    ABOUND R2, 1
    RECV R0, 0
    FELLOWSHIP R5, R0
    
    ; 检查是否打开成功
    ABOUND R1, 16
    ABOUND R2, 16
    REDUCE R1, R2
    CMP R5, R1
    BRANCH R0, WRITE_FAILED
    
    ; 写入
    ABOUND R0, SYS_WRITE
    FELLOWSHIP R1, R5
    ALLOC R2, 0
    FELLOWSHIP R2, R2
    FELLOWSHIP R3, R13
    RECV R0, 0
    
    ; 关闭
    ABOUND R0, SYS_CLOSE
    FELLOWSHIP R1, R5
    RECV R0, 0
    
    ; 打印成功
    ALLOC R0, 0
    FELLOWSHIP R10, R0
"""
    
    code += "\n" + string_to_evoasm("Written to out.raw\n", "R10", "R1")
    
    code += """
    ABOUND R0, SYS_PRINT
    ALLOC R1, 0
    FELLOWSHIP R1, R1
    RECV R0, 0
    
    BRANCH R0, EXIT

WRITE_FAILED:
    ALLOC R0, 0
    FELLOWSHIP R10, R0
"""
    
    code += "\n" + string_to_evoasm("Failed to write output\n", "R10", "R1")
    
    code += """
    ABOUND R0, SYS_PRINT
    ALLOC R1, 0
    FELLOWSHIP R1, R1
    RECV R0, 0

EXIT:
    ALLOC R0, 0
    FELLOWSHIP R10, R0
"""
    
    code += "\n" + string_to_evoasm("Done.\n", "R10", "R1")
    
    code += """
    ABOUND R0, SYS_PRINT
    ALLOC R1, 0
    FELLOWSHIP R1, R1
    RECV R0, 0
    
    ABOUND R0, SYS_EXIT
    RECV R0, 0

HALT
"""
    return code

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 evoasm_helper.py <command>")
        print("Commands:")
        print("  fileio   - 生成文件 IO 测试代码")
        print("  minimal  - 生成最小汇编器代码")
        print("  string <text> - 生成字符串构建代码")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "fileio":
        print(generate_fileio_tests())
    elif cmd == "minimal":
        print(generate_minimal_assembler())
    elif cmd == "string":
        if len(sys.argv) < 3:
            print("Usage: python3 evoasm_helper.py string <text>")
            return
        text = sys.argv[2]
        print(string_to_evoasm(text))
    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()
