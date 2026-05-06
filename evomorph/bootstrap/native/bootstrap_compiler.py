#!/usr/bin/env python3
"""
易衍·Evomorph 完全自举编译器 v2
用传统CPU汇编指令实现，在扩展虚拟机v2上运行

完全自举 = 虚拟机(Python/C) + 编译器全部逻辑(传统CPU汇编)

内存布局 (v4 - 大字符串池支持自举):
- 0x001000-0x008FFF: 输入缓冲区（源代码，32KB）
- 0x009000-0x010FFF: Token缓冲区 (每个Token 8字节，最多4096个，32KB)
- 0x011000-0x02AFFF: 输出缓冲区（EVOB字节码，96KB）
- 0x02B000-0x032FFF: 字符串常量池（32KB，支持大程序）
- 0x033000-0x0331FF: 助记符查找表 (64项 × 8字节)
- 0x033200-0x0333FF: 助记符字符串区 (512字节)
- 0x033400-0x0334FF: 基因座偏移表
- 0x033500-0x0335FF: 修饰符字符串区
- 0x033600-0x0336FF: 关键字字符串区
- 0x033700-0x0338FF: 原生指令查找表 (44项 × 8字节)
- 0x033900-0x033BFF: 原生指令字符串区 (768字节)
- 0x040000-0x0FFFFF: 栈和工作区

Token类型:
- 1=KEYWORD, 2=IDENT, 3=NUMBER, 4=STRING, 5=SYMBOL, 6=MODIFIER, 9=NEWLINE

EVOB格式 (大端序):
- Header: "EVOB"(4) + version(2 BE) + header_size(2 BE) + locus_count(2 BE) + offsets(4 BE × N)
"""

import sys
import os
import re
import struct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

INPUT_BUF = 0x1000
TOKEN_BUF = 0x9000
OUTPUT_BUF = 0x11000
STRPOOL_BUF = 0x2B000
MNEMONIC_TABLE = 0x33000
MNEMONIC_STRINGS = 0x33200
LOCUS_OFFSET_TABLE = 0x33400
MODIFIER_STRINGS = 0x33500
KEYWORD_STRINGS = 0x33600
NATIVE_TABLE = 0x33700
NATIVE_STRINGS = 0x33900
HEADER_RESERVE = 64

MNEMONICS = [
    ("RECV", 0), ("RETURN", 1), ("BRANCH", 2), ("APPROACH", 3),
    ("YIELD", 4), ("OBSCURE", 5), ("PUSH_UP", 6), ("FLUSH", 7),
    ("SPECULATE", 8), ("SHOCK", 9), ("UNLOCK", 10), ("MISMATCH", 11),
    ("MICRO", 12), ("ABOUND", 13), ("PERSIST", 14), ("THRUST", 15),
    ("MERGE", 16), ("ALLOC", 17), ("TRAP", 18), ("THROTTLE", 19),
    ("LAME", 20), ("SYNC", 21), ("WELL", 22), ("WAIT", 23),
    ("GATHER", 24), ("FOLLOWING", 25), ("TRAPPED", 26), ("JOY", 27),
    ("SENSE", 28), ("REPLACE", 29), ("OVERLOAD", 30), ("BREAK", 31),
    ("STRIP", 32), ("NOURISH", 33), ("SPRT", 34), ("REDUCE", 35),
    ("STILL", 36), ("ADORN", 37), ("MUT", 38), ("BARRIER", 39),
    ("ADVANCE", 40), ("BITE", 41), ("FUTU", 42), ("CONVERT", 43),
    ("TRAVEL", 44), ("ILLUMINATE", 45), ("CAST", 46), ("ABUNDANCE", 47),
    ("CONTEMPLATE", 48), ("INCREASE", 49), ("DISPERSE", 50), ("TRUST", 51),
    ("GRADUAL", 52), ("BIND", 53), ("PENETRATE", 54), ("PREFETCH", 55),
    ("HALT", 56), ("INTRINSIC", 57), ("LOCK", 58), ("STEP", 59),
    ("RETREAT", 60), ("FELLOWSHIP", 61), ("MATE", 62), ("CREA", 63),
]

MODIFIER_MAP = {
    ".ASYNC": 0x20, ".ATOMIC": 0x10, ".PRIV": 0x08,
    ".WEAK": 0x04, ".STRONG": 0x02, ".VOLATILE": 0x01,
}

NATIVE_MNEMONICS = [
    ("NOP", 0x00), ("HLT", 0x01),
    ("ADD", 0x08), ("SUB", 0x09), ("MUL", 0x0A), ("DIV", 0x0B), ("MOD", 0x0C),
    ("INC", 0x0D), ("DEC", 0x0E), ("NEG", 0x0F),
    ("AND", 0x10), ("OR", 0x11), ("XOR", 0x12), ("NOT", 0x13),
    ("SHL", 0x14), ("SHR", 0x15), ("SAR", 0x16),
    ("CMP", 0x18), ("CMPI", 0x19), ("TEST", 0x1A),
    ("JMP", 0x20), ("JE", 0x21), ("JNE", 0x22),
    ("JL", 0x23), ("JLE", 0x24), ("JG", 0x25), ("JGE", 0x26),
    ("JC", 0x27), ("JNC", 0x28),
    ("MOV", 0x30), ("LEA", 0x31), ("XCHG", 0x32), ("MOVI", 0x33),
    ("LDR", 0x34), ("STR", 0x35), ("LDRB", 0x36), ("STRB", 0x37),
    ("PUSH", 0x38), ("POP", 0x39), ("PUSHA", 0x3A), ("POPA", 0x3B),
    ("CALL", 0x3C), ("RET", 0x3D), ("INT", 0x3E), ("IRET", 0x3F),
]

NATIVE_NO_OPERAND = {0x00, 0x01, 0x3D, 0x3A, 0x3B}
NATIVE_ONE_REG = {0x0D, 0x0E, 0x0F, 0x13, 0x38, 0x39, 0x3E}
NATIVE_IMM_ALWAYS = {0x19, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x33, 0x3C}
NATIVE_TWO_REG_IMM_COMPAT = {0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x10, 0x11, 0x12, 0x14, 0x15, 0x16, 0x18, 0x1A}

STDLIB_ASM = """
; ========================================
; 标准库
; 寄存器约定: R0-R3=参数/返回值, R4-R7=临时
; ========================================

strlen:
    PUSH R4
    PUSH R5
    MOV R4, R0
    MOVI R5, #0
strlen_loop:
    LDRB R0, R4
    CMPI R0, #0
    JE strlen_done
    INC R4
    INC R5
    JMP strlen_loop
strlen_done:
    MOV R0, R5
    POP R5
    POP R4
    RET

strcmp:
    PUSH R4
    PUSH R5
strcmp_loop:
    LDRB R4, R0
    LDRB R5, R1
    CMP R4, R5
    JNE strcmp_diff
    CMPI R4, #0
    JE strcmp_equal
    INC R0
    INC R1
    JMP strcmp_loop
strcmp_diff:
    JL strcmp_less
    MOVI R0, #1
    JMP strcmp_ret
strcmp_less:
    MOVI R0, #-1
    JMP strcmp_ret
strcmp_equal:
    MOVI R0, #0
strcmp_ret:
    POP R5
    POP R4
    RET

is_whitespace:
    CMPI R0, #32
    JE is_ws_yes
    CMPI R0, #9
    JE is_ws_yes
    CMPI R0, #10
    JE is_ws_yes
    CMPI R0, #13
    JE is_ws_yes
    MOVI R0, #0
    RET
is_ws_yes:
    MOVI R0, #1
    RET

is_digit:
    CMPI R0, #48
    JL is_digit_no
    CMPI R0, #57
    JG is_digit_no
    MOVI R0, #1
    RET
is_digit_no:
    MOVI R0, #0
    RET

is_alpha:
    CMPI R0, #65
    JL is_alpha_lower
    CMPI R0, #90
    JG is_alpha_lower
    MOVI R0, #1
    RET
is_alpha_lower:
    CMPI R0, #97
    JL is_alpha_no
    CMPI R0, #122
    JG is_alpha_no
    MOVI R0, #1
    RET
is_alpha_no:
    MOVI R0, #0
    RET

is_alnum:
    PUSH R4
    MOV R4, R0
    CALL is_digit
    CMPI R0, #1
    JE is_alnum_yes
    MOV R0, R4
    CALL is_alpha
    CMPI R0, #1
    JE is_alnum_yes
    MOVI R0, #0
    POP R4
    RET
is_alnum_yes:
    MOVI R0, #1
    POP R4
    RET

is_underscore:
    CMPI R0, #95
    JNE is_under_no
    MOVI R0, #1
    RET
is_under_no:
    MOVI R0, #0
    RET

hex_char_to_val:
    CMPI R0, #48
    JL hex_invalid
    CMPI R0, #57
    JG hex_check_upper
    SUB R0, #48
    RET
hex_check_upper:
    CMPI R0, #65
    JL hex_check_lower
    CMPI R0, #70
    JG hex_check_lower
    SUB R0, #55
    RET
hex_check_lower:
    CMPI R0, #97
    JL hex_invalid
    CMPI R0, #102
    JG hex_invalid
    SUB R0, #87
    RET
hex_invalid:
    MOVI R0, #-1
    RET

; 解析寄存器名 "R0"-"R31" → 数字
; 输入: R0 = 字符串地址
; 输出: R0 = 寄存器号(0-31), 或 -1
parse_register_name:
    PUSH R4
    PUSH R5
    PUSH R6
    MOV R4, R0
    LDRB R5, R4
    CMPI R5, #82
    JNE parse_reg_fail
    INC R4
    LDRB R5, R4
    MOV R0, R5
    CALL is_digit
    CMPI R0, #0
    JE parse_reg_fail
    MOVI R6, #0
parse_reg_loop:
    LDRB R5, R4
    CMPI R5, #0
    JE parse_reg_done
    MOV R0, R5
    CALL is_digit
    CMPI R0, #0
    JE parse_reg_done
    MOVI R0, #10
    MUL R6, R0
    SUB R5, #48
    ADD R6, R5
    INC R4
    JMP parse_reg_loop
parse_reg_done:
    CMP R6, #31
    JG parse_reg_fail
    MOV R0, R6
    POP R6
    POP R5
    POP R4
    RET
parse_reg_fail:
    MOVI R0, #-1
    POP R6
    POP R5
    POP R4
    RET
"""

LEXER_ASM = """
; ========================================
; 词法分析器
; R8=源代码位置, R9=Token写入位置, R10=Token计数, R11=字符串池位置
; ========================================

lexer_init:
    MOV R8, R0
    MOVI R9, #0x9000
    MOVI R10, #0
    MOVI R11, #0x2B000
    RET

lexer_skip_whitespace:
    LDRB R0, R8
    CMPI R0, #0
    JE skip_ws_done
    CALL is_whitespace
    CMPI R0, #1
    JNE skip_ws_done
    INC R8
    JMP lexer_skip_whitespace
skip_ws_done:
    RET

lexer_skip_comment:
    INC R8
    INC R8
skip_comment_loop:
    LDRB R0, R8
    CMPI R0, #0
    JE skip_comment_done
    CMPI R0, #10
    JE skip_comment_done
    INC R8
    JMP skip_comment_loop
skip_comment_done:
    RET

; 跳过多字节UTF-8字符 (非ASCII)
lexer_skip_utf8:
    LDRB R0, R8
    CMPI R0, #0
    JE skip_utf8_done
    CMPI R0, #128
    JL skip_utf8_done
    CMPI R0, #192
    JGE skip_utf8_2
    INC R8
    JMP lexer_skip_utf8
skip_utf8_2:
    CMPI R0, #224
    JGE skip_utf8_3
    INC R8
    INC R8
    JMP lexer_skip_utf8
skip_utf8_3:
    CMPI R0, #240
    JGE skip_utf8_4
    INC R8
    INC R8
    INC R8
    JMP lexer_skip_utf8
skip_utf8_4:
    INC R8
    INC R8
    INC R8
    INC R8
    JMP lexer_skip_utf8
skip_utf8_done:
    RET

lexer_emit_token:
    PUSH R4
    STR R9, R0
    MOVI R4, #4
    ADD R9, R4
    STR R9, R1
    ADD R9, R4
    INC R10
    POP R4
    RET

lexer_scan_number:
    PUSH R4
    PUSH R5
    PUSH R6
    MOVI R1, #0
    MOV R5, R0
    MOVI R6, #0
scan_num_loop:
    MOV R0, R5
    CALL is_digit
    CMPI R0, #0
    JE scan_num_check_hex
    MOVI R4, #10
    MUL R1, R4
    SUB R5, #48
    ADD R1, R5
    INC R8
    LDRB R5, R8
    CMPI R5, #0
    JE scan_num_emit
    JMP scan_num_loop
scan_num_check_hex:
    CMPI R5, #120
    JE scan_num_hex
    CMPI R5, #88
    JE scan_num_hex
    JMP scan_num_emit
scan_num_hex:
    INC R8
    MOVI R1, #0
scan_hex_loop:
    LDRB R0, R8
    CMPI R0, #0
    JE scan_num_emit
    CALL hex_char_to_val
    CMPI R0, #-1
    JE scan_num_emit
    MOVI R4, #16
    MUL R1, R4
    ADD R1, R0
    INC R8
    JMP scan_hex_loop
scan_num_emit:
    MOVI R0, #3
    CALL lexer_emit_token
    POP R6
    POP R5
    POP R4
    RET

lexer_scan_identifier:
    PUSH R4
    PUSH R5
    MOV R4, R11
    ; R0 already contains the first character
scan_id_loop:
    STRB R11, R0
    INC R11
    INC R8
    LDRB R5, R8
    MOV R0, R5
    CALL is_alnum
    CMPI R0, #1
    JE scan_id_cont
    MOV R0, R5
    CALL is_underscore
    CMPI R0, #1
    JE scan_id_cont
    JMP scan_id_done
scan_id_cont:
    MOV R0, R5
    JMP scan_id_loop
scan_id_done:
    MOVI R0, #0
    STRB R11, R0
    INC R11
    MOV R1, R4
    MOVI R0, #2
    CALL lexer_emit_token
    POP R5
    POP R4
    RET

lexer_scan_modifier:
    PUSH R4
    PUSH R5
    MOV R4, R11
    MOVI R0, #46
    STRB R11, R0
    INC R11
    INC R8
scan_mod_loop:
    LDRB R5, R8
    MOV R0, R5
    CALL is_alpha
    CMPI R0, #1
    JNE scan_mod_done
    STRB R11, R5
    INC R11
    INC R8
    JMP scan_mod_loop
scan_mod_done:
    MOVI R0, #0
    STRB R11, R0
    INC R11
    MOV R1, R4
    MOVI R0, #6
    CALL lexer_emit_token
    POP R5
    POP R4
    RET

lexer_scan_string:
    INC R8
    PUSH R4
    MOV R4, R11
scan_str_loop:
    LDRB R0, R8
    CMPI R0, #0
    JE scan_str_done
    CMPI R0, #34
    JE scan_str_end
    CMPI R0, #92
    JE scan_str_escape
    STRB R11, R0
    INC R11
    INC R8
    JMP scan_str_loop
scan_str_escape:
    INC R8
    LDRB R0, R8
    CMPI R0, #110
    JNE scan_str_esc_t
    MOVI R0, #10
    JMP scan_str_esc_store
scan_str_esc_t:
    CMPI R0, #116
    JNE scan_str_esc_default
    MOVI R0, #9
    JMP scan_str_esc_store
scan_str_esc_default:
    JMP scan_str_esc_store
scan_str_esc_store:
    STRB R11, R0
    INC R11
    INC R8
    JMP scan_str_loop
scan_str_end:
    INC R8
scan_str_done:
    MOVI R0, #0
    STRB R11, R0
    INC R11
    MOV R1, R4
    MOVI R0, #4
    CALL lexer_emit_token
    POP R4
    RET

lexer_tokenize:
    CALL lexer_init
tokenize_loop:
    CALL lexer_skip_whitespace
    LDRB R0, R8
    CMPI R0, #0
    JE tokenize_done
    CMPI R0, #128
    JGE tokenize_skip_utf8
    CMPI R0, #47
    JNE tokenize_check_at
    PUSH R4
    PUSH R5
    LDRB R4, R8
    MOVI R5, #1
    ADD R5, R8
    LDRB R5, R5
    CMPI R5, #47
    POP R5
    POP R4
    JNE tokenize_check_at
    CALL lexer_skip_comment
    JMP tokenize_loop
tokenize_skip_utf8:
    CALL lexer_skip_utf8
    JMP tokenize_loop
tokenize_check_at:
    CMPI R0, #64
    JNE tokenize_check_quote
    MOVI R0, #5
    MOVI R1, #64
    CALL lexer_emit_token
    INC R8
    JMP tokenize_loop
tokenize_check_quote:
    CMPI R0, #34
    JNE tokenize_check_digit
    CALL lexer_scan_string
    JMP tokenize_loop
tokenize_check_digit:
    LDRB R5, R8
    MOV R0, R5
    CALL is_digit
    CMPI R0, #1
    JNE tokenize_check_dot
    MOV R0, R5
    CALL lexer_scan_number
    JMP tokenize_loop
tokenize_check_dot:
    CMPI R5, #46
    JNE tokenize_check_alpha
    CALL lexer_scan_modifier
    JMP tokenize_loop
tokenize_check_alpha:
    LDRB R5, R8
    MOV R0, R5
    CALL is_alpha
    CMPI R0, #1
    JNE tokenize_check_underscore
    MOV R0, R5
    CALL lexer_scan_identifier
    JMP tokenize_loop
tokenize_check_underscore:
    CMPI R5, #95
    JNE tokenize_check_symbol
    MOV R0, R5
    CALL lexer_scan_identifier
    JMP tokenize_loop
tokenize_check_symbol:
    LDRB R0, R8
    CMPI R0, #123
    JNE tok_sym_rbrace
    MOVI R0, #5
    MOVI R1, #123
    CALL lexer_emit_token
    INC R8
    JMP tokenize_loop
tok_sym_rbrace:
    CMPI R0, #125
    JNE tok_sym_lparen
    MOVI R0, #5
    MOVI R1, #125
    CALL lexer_emit_token
    INC R8
    JMP tokenize_loop
tok_sym_lparen:
    CMPI R0, #40
    JNE tok_sym_rparen
    MOVI R0, #5
    MOVI R1, #40
    CALL lexer_emit_token
    INC R8
    JMP tokenize_loop
tok_sym_rparen:
    CMPI R0, #41
    JNE tok_sym_lbracket
    MOVI R0, #5
    MOVI R1, #41
    CALL lexer_emit_token
    INC R8
    JMP tokenize_loop
tok_sym_lbracket:
    CMPI R0, #91
    JNE tok_sym_rbracket
    MOVI R0, #5
    MOVI R1, #91
    CALL lexer_emit_token
    INC R8
    JMP tokenize_loop
tok_sym_rbracket:
    CMPI R0, #93
    JNE tok_sym_comma
    MOVI R0, #5
    MOVI R1, #93
    CALL lexer_emit_token
    INC R8
    JMP tokenize_loop
tok_sym_comma:
    CMPI R0, #44
    JNE tok_sym_colon
    MOVI R0, #5
    MOVI R1, #44
    CALL lexer_emit_token
    INC R8
    JMP tokenize_loop
tok_sym_colon:
    CMPI R0, #58
    JNE tok_sym_eq
    MOVI R0, #5
    MOVI R1, #58
    CALL lexer_emit_token
    INC R8
    JMP tokenize_loop
tok_sym_eq:
    CMPI R0, #61
    JNE tok_sym_newline
    MOVI R0, #5
    MOVI R1, #61
    CALL lexer_emit_token
    INC R8
    JMP tokenize_loop
tok_sym_newline:
    CMPI R0, #10
    JNE tok_sym_semicolon
    MOVI R0, #9
    MOVI R1, #10
    CALL lexer_emit_token
    INC R8
    JMP tokenize_loop
tok_sym_semicolon:
    CMPI R0, #59
    JNE tok_sym_skip
    INC R8
    JMP tokenize_loop
tok_sym_skip:
    INC R8
    JMP tokenize_loop
tokenize_done:
    RET
"""

LOOKUP_ASM = """
; ========================================
; 助记符查找
; 表格地址: 0x7000, 每项8字节: ptr(4) + opcode(4)
; 共64项
; ========================================

lookup_mnemonic:
    PUSH R4
    PUSH R5
    PUSH R6
    PUSH R7
    MOV R7, R0
    MOVI R4, #0x33000
    MOVI R6, #64
lookup_loop:
    CMPI R6, #0
    JE lookup_not_found
    LDR R5, R4
    MOV R0, R7
    MOV R1, R5
    CALL strcmp
    CMPI R0, #0
    JE lookup_found
    ADD R4, #8
    DEC R6
    JMP lookup_loop
lookup_found:
    MOVI R5, #4
    ADD R4, R5
    LDR R0, R4
    POP R7
    POP R6
    POP R5
    POP R4
    RET
lookup_not_found:
    MOVI R0, #-1
    POP R7
    POP R6
    POP R5
    POP R4
    RET

; 查找修饰符
; 输入: R0 = 修饰符字符串地址 (如 ".ASYNC")
; 输出: R0 = 修饰符值, 或 0
lookup_modifier:
    PUSH R4
    PUSH R5
    LDRB R4, R0
    CMPI R4, #46
    JNE lookup_mod_zero
    MOVI R5, #1
    ADD R5, R0
    ; 比较每个修饰符
    ; .ASYNC = 0x20
    PUSH R0
    PUSH R1
    MOVI R0, #0x33500
    MOV R1, R5
    CALL strcmp
    CMPI R0, #0
    POP R1
    POP R0
    JNE lookup_mod_atomic
    MOVI R0, #32
    POP R5
    POP R4
    RET
lookup_mod_atomic:
    ; .ATOMIC = 0x10
    PUSH R0
    PUSH R1
    MOVI R0, #0x33507
    MOV R1, R5
    CALL strcmp
    CMPI R0, #0
    POP R1
    POP R0
    JNE lookup_mod_priv
    MOVI R0, #16
    POP R5
    POP R4
    RET
lookup_mod_priv:
    ; .PRIV = 0x08
    PUSH R0
    PUSH R1
    MOVI R0, #0x33514
    MOV R1, R5
    CALL strcmp
    CMPI R0, #0
    POP R1
    POP R0
    JNE lookup_mod_weak
    MOVI R0, #8
    POP R5
    POP R4
    RET
lookup_mod_weak:
    ; .WEAK = 0x04
    PUSH R0
    PUSH R1
    MOVI R0, #0x33519
    MOV R1, R5
    CALL strcmp
    CMPI R0, #0
    POP R1
    POP R0
    JNE lookup_mod_strong
    MOVI R0, #4
    POP R5
    POP R4
    RET
lookup_mod_strong:
    ; .STRONG = 0x02
    PUSH R0
    PUSH R1
    MOVI R0, #0x33524
    MOV R1, R5
    CALL strcmp
    CMPI R0, #0
    POP R1
    POP R0
    JNE lookup_mod_volatile
    MOVI R0, #2
    POP R5
    POP R4
    RET
lookup_mod_volatile:
    ; .VOLATILE = 0x01
    PUSH R0
    PUSH R1
    MOVI R0, #0x33531
    MOV R1, R5
    CALL strcmp
    CMPI R0, #0
    POP R1
    POP R0
    JNE lookup_mod_zero
    MOVI R0, #1
    POP R5
    POP R4
    RET
lookup_mod_zero:
    MOVI R0, #0
    POP R5
    POP R4
    RET

; ========================================
; 原生指令查找
; 表格地址: 0x7800, 每项8字节: ptr(4) + opcode(4)
; ========================================

lookup_native:
    PUSH R4
    PUSH R5
    PUSH R6
    PUSH R7
    MOV R7, R0
    MOVI R4, #0x33700
    MOVI R6, #44
lookup_native_loop:
    CMPI R6, #0
    JE lookup_native_not_found
    LDR R5, R4
    MOV R0, R7
    MOV R1, R5
    CALL strcmp
    CMPI R0, #0
    JE lookup_native_found
    ADD R4, #8
    DEC R6
    JMP lookup_native_loop
lookup_native_found:
    MOVI R5, #4
    ADD R4, R5
    LDR R0, R4
    POP R7
    POP R6
    POP R5
    POP R4
    RET
lookup_native_not_found:
    MOVI R0, #-1
    POP R7
    POP R6
    POP R5
    POP R4
    RET
"""

CODEGEN_ASM = """
; ========================================
; 代码生成器
; R12=输出位置, R13=当前Token索引, R14=Token总数
; R15=基因座计数, R16=当前基因座字节码起始偏移
; ========================================

codegen_init:
    MOVI R12, #0x11000
    ADD R12, #64
    MOVI R13, #0
    MOV R14, R10
    MOVI R15, #0
    RET

codegen_emit_byte:
    STRB R12, R0
    INC R12
    RET

; 大端序输出32位字
codegen_emit_word_be:
    PUSH R4
    MOV R4, R0
    SHR R4, #24
    AND R4, #255
    STRB R12, R4
    INC R12
    MOV R4, R0
    SHR R4, #16
    AND R4, #255
    STRB R12, R4
    INC R12
    MOV R4, R0
    SHR R4, #8
    AND R4, #255
    STRB R12, R4
    INC R12
    MOV R4, R0
    AND R4, #255
    STRB R12, R4
    INC R12
    POP R4
    RET

; 大端序输出16位字
codegen_emit_half_be:
    PUSH R4
    MOV R4, R0
    SHR R4, #8
    AND R4, #255
    STRB R12, R4
    INC R12
    MOV R4, R0
    AND R4, #255
    STRB R12, R4
    INC R12
    POP R4
    RET

; 读取当前Token (不修改R13)
; 输出: R0=type, R1=value
codegen_read_token:
    PUSH R4
    PUSH R5
    MOV R4, R13
    MOVI R5, #8
    MUL R4, R5
    MOVI R5, #0x9000
    ADD R5, R4
    LDR R0, R5
    ADD R5, #4
    LDR R1, R5
    POP R5
    POP R4
    RET

codegen_next_token:
    INC R13
    RET

codegen_has_tokens:
    CMP R13, R14
    JL has_tokens_yes
    MOVI R0, #0
    RET
has_tokens_yes:
    MOVI R0, #1
    RET

; 输出一条六十四卦指令 (4字节)
; 编码: [0x80|opcode, modifier, op1, op2]
; R0=opcode, R1=modifier, R2=op1, R3=op2
codegen_emit_iching:
    PUSH R4
    ; byte1 = 0x80 | (opcode & 0x3F)
    MOV R4, R0
    AND R4, #63
    MOVI R0, #128
    OR R4, R0
    STRB R12, R4
    INC R12
    ; byte2 = modifier
    STRB R12, R1
    INC R12
    ; byte3 = op1
    STRB R12, R2
    INC R12
    ; byte4 = op2
    STRB R12, R3
    INC R12
    POP R4
    RET

; 输出一条原生CPU指令 (3字节头 + 可选4字节立即数)
; R0=opcode, R1=dst_reg, R2=src_reg, R3=imm_value, R4=has_imm(1/0)
codegen_emit_native:
    PUSH R5
    PUSH R6
    ; byte1 = 0x40 | (opcode & 0x3F)
    MOV R5, R0
    AND R5, #63
    MOVI R6, #64
    OR R5, R6
    STRB R12, R5
    INC R12
    ; byte2 = dst_reg & 0x1F | (has_imm ? 0x20 : 0) for TWO_REG_IMM ops
    MOV R5, R1
    AND R5, #31
    CMPI R4, #0
    JE codegen_native_byte2
    MOVI R6, #32
    OR R5, R6
codegen_native_byte2:
    STRB R12, R5
    INC R12
    ; byte3 = src_reg & 0x1F
    MOV R5, R2
    AND R5, #31
    STRB R12, R5
    INC R12
    ; optional 4-byte immediate (little-endian)
    CMPI R4, #0
    JE codegen_native_done
    MOV R5, R3
    AND R5, #255
    STRB R12, R5
    INC R12
    MOV R5, R3
    SHR R5, #8
    AND R5, #255
    STRB R12, R5
    INC R12
    MOV R5, R3
    SHR R5, #16
    AND R5, #255
    STRB R12, R5
    INC R12
    MOV R5, R3
    SHR R5, #24
    AND R5, #255
    STRB R12, R5
    INC R12
codegen_native_done:
    POP R6
    POP R5
    RET

; 在输出缓冲区指定位置写回数据
; R0=偏移(从0x4000起), R1=值(字节)
codegen_write_byte_at:
    PUSH R4
    MOVI R4, #0x11000
    ADD R4, R0
    STRB R4, R1
    POP R4
    RET

; 在输出缓冲区指定位置写回16位大端序
; R0=偏移(从0x4000起), R1=值
codegen_write_half_at:
    PUSH R4
    PUSH R5
    MOVI R4, #0x11000
    ADD R4, R0
    MOV R5, R1
    SHR R5, #8
    AND R5, #255
    STRB R4, R5
    INC R4
    MOV R5, R1
    AND R5, #255
    STRB R4, R5
    POP R5
    POP R4
    RET

; 在输出缓冲区指定位置写回32位大端序
; R0=偏移(从0x4000起), R1=值
codegen_write_word_at:
    PUSH R4
    PUSH R5
    MOVI R4, #0x11000
    ADD R4, R0
    MOV R5, R1
    SHR R5, #24
    AND R5, #255
    STRB R4, R5
    INC R4
    MOV R5, R1
    SHR R5, #16
    AND R5, #255
    STRB R4, R5
    INC R4
    MOV R5, R1
    SHR R5, #8
    AND R5, #255
    STRB R4, R5
    INC R4
    MOV R5, R1
    AND R5, #255
    STRB R4, R5
    POP R5
    POP R4
    RET
"""

PARSER_ASM = """
; ========================================
; 语法分析器 + 代码生成
; 递归下降解析器，单遍编译
; R17=当前指令修饰符, R18-R23=临时, R24-R27=保存
; ========================================

; 判断当前Token是否为指定类型和值
; 输入: R0=期望type, R1=期望value
; 输出: R0=1匹配, 0不匹配
parser_match:
    PUSH R2
    PUSH R3
    PUSH R4
    PUSH R5
    MOV R4, R0
    MOV R5, R1
    CALL codegen_read_token
    CMP R4, R0
    JNE parser_match_no
    CMP R5, R1
    JNE parser_match_no
    MOVI R0, #1
    POP R5
    POP R4
    POP R3
    POP R2
    RET
parser_match_no:
    MOVI R0, #0
    POP R5
    POP R4
    POP R3
    POP R2
    RET

; 解析并编译整个程序
parse_program:
    ; 先写入EVOB头部占位
    ; "EVOB" at offset 0
    MOVI R0, #0
    MOVI R1, #69
    CALL codegen_write_byte_at
    MOVI R0, #1
    MOVI R1, #86
    CALL codegen_write_byte_at
    MOVI R0, #2
    MOVI R1, #79
    CALL codegen_write_byte_at
    MOVI R0, #3
    MOVI R1, #66
    CALL codegen_write_byte_at
    ; version = 3 at offset 4 (uint16 BE)
    MOVI R0, #4
    MOVI R1, #3
    CALL codegen_write_half_at
    ; header_size placeholder at offset 6
    MOVI R0, #6
    MOVI R1, #0
    CALL codegen_write_half_at
    ; locus_count placeholder at offset 8
    MOVI R0, #8
    MOVI R1, #0
    CALL codegen_write_half_at

parse_loop:
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_done
    CALL codegen_read_token
    ; R0=type, R1=value
    CMPI R0, #5
    JNE parse_skip_token
    CMPI R1, #64
    JNE parse_check_brace
    CALL parse_at_keyword
    JMP parse_loop
parse_check_brace:
    CMPI R1, #123
    JNE parse_skip_token
    CALL parse_skip_block
    JMP parse_loop
parse_skip_token:
    CALL codegen_next_token
    JMP parse_loop
parse_done:
    ; 回填头部
    ; locus_count at offset 8
    MOVI R0, #8
    MOV R1, R15
    CALL codegen_write_half_at
    ; header_size at offset 6
    ; header = 10 + locus_count * 4
    MOVI R18, #10
    MOVI R19, #4
    MUL R19, R15
    ADD R18, R19
    PUSH R15
    MOVI R0, #6
    MOV R1, R18
    CALL codegen_write_half_at
    ; 写入基因座偏移表 (在头部末尾)
    ; 偏移表起始 = 10
    MOVI R18, #10
    MOVI R19, #0
write_offsets_loop:
    CMP R19, R15
    JGE write_offsets_done
    ; 读取偏移值
    MOVI R20, #0x33400
    MOVI R21, #4
    MUL R19, R21
    ADD R20, R19
    LDR R21, R20
    ; 写入偏移 (加上头部大小)
    ; 实际偏移 = header_size + 基因座内偏移
    ; 但我们的R12已经是从0x4000+64开始的
    ; 基因座偏移是相对于字节码起始的
    MOV R0, R18
    MOV R1, R21
    CALL codegen_write_word_at
    ADD R18, #4
    INC R19
    JMP write_offsets_loop
write_offsets_done:
    POP R15
    RET

; 解析@关键字
parse_at_keyword:
    CALL codegen_next_token
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_at_done
    CALL codegen_read_token
    CMPI R0, #2
    JNE parse_at_done
    ; R1 = 标识符字符串地址
    ; 比较 "evolang"
    PUSH R1
    MOVI R0, #0x33600
    MOV R1, R1
    CALL strcmp
    CMPI R0, #0
    POP R1
    JNE parse_at_check_locus
    CALL parse_evolang
    JMP parse_at_done
parse_at_check_locus:
    PUSH R1
    MOVI R0, #0x33608
    CALL strcmp
    CMPI R0, #0
    POP R1
    JNE parse_at_check_xiangci
    CALL parse_locus
    JMP parse_at_done
parse_at_check_xiangci:
    PUSH R1
    MOVI R0, #0x3360E
    CALL strcmp
    CMPI R0, #0
    POP R1
    JNE parse_at_check_meta
    CALL parse_skip_rest
    JMP parse_at_done
parse_at_check_meta:
    PUSH R1
    MOVI R0, #0x33616
    CALL strcmp
    CMPI R0, #0
    POP R1
    JNE parse_at_done
    CALL parse_locus
    JMP parse_at_done
parse_at_done:
    RET

; 解析 @evolang "version"
parse_evolang:
    CALL codegen_next_token
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_evolang_done
    CALL codegen_read_token
    CMPI R0, #4
    JNE parse_evolang_done
    CALL codegen_next_token
parse_evolang_done:
    RET

; 解析 @locus name { ... }
parse_locus:
    CALL codegen_next_token
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_locus_done
    CALL codegen_read_token
    CMPI R0, #2
    JNE parse_locus_done
    ; 跳过基因座名称
    CALL codegen_next_token
    ; 记录基因座偏移
    ; 当前输出位置 - 0x4000 - 64 = 字节码偏移
    MOV R16, R12
    SUB R16, #0x11000
    SUB R16, #64
    ; 存入偏移表
    MOVI R20, #0x33400
    MOVI R21, #4
    MUL R21, R15
    ADD R20, R21
    STR R20, R16
    INC R15
    ; 期待 { ... }
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_locus_done
    CALL codegen_read_token
    CMPI R0, #5
    JNE parse_locus_done
    CMPI R1, #123
    JNE parse_locus_done
    CALL codegen_next_token
    ; 解析基因座体
    CALL parse_locus_body
parse_locus_done:
    RET

; 解析基因座体 { ... }
parse_locus_body:
parse_locus_loop:
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_locus_body_done
    CALL codegen_read_token
    ; 检查 }
    CMPI R0, #5
    JNE parse_locus_check_ident
    CMPI R1, #125
    JE parse_locus_body_end
    JMP parse_locus_skip
parse_locus_check_ident:
    CMPI R0, #2
    JNE parse_locus_check_modifier
    ; 检查是否为 GUAXU (卦序)
    PUSH R1
    MOVI R0, #0x33621
    MOV R1, R1
    CALL strcmp
    CMPI R0, #0
    POP R1
    JNE parse_locus_skip_ident
    ; 找到 GUAXU，解析指令块
    CALL codegen_next_token
    ; 跳过冒号
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_locus_body_done
    CALL codegen_read_token
    CMPI R0, #5
    JNE parse_guaxu_block
    CMPI R1, #58
    JNE parse_guaxu_block
    CALL codegen_next_token
    ; 期待 {
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_locus_body_done
    CALL codegen_read_token
    CMPI R0, #5
    JNE parse_locus_body_done
    CMPI R1, #123
    JNE parse_locus_body_done
    CALL codegen_next_token
    ; 解析指令
    CALL parse_guaxu_block
    JMP parse_locus_loop
parse_locus_check_modifier:
    CMPI R0, #6
    JNE parse_locus_skip
    CALL codegen_next_token
    JMP parse_locus_loop
parse_locus_skip_ident:
    CALL codegen_next_token
    JMP parse_locus_loop
parse_locus_skip:
    CALL codegen_next_token
    JMP parse_locus_loop
parse_locus_body_end:
    CALL codegen_next_token
parse_locus_body_done:
    RET

; 解析卦序指令块 { ... }
parse_guaxu_block:
parse_guaxu_loop:
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_guaxu_done
    CALL codegen_read_token
    ; 检查 }
    CMPI R0, #5
    JNE parse_guaxu_check_ident
    CMPI R1, #125
    JE parse_guaxu_end
    JMP parse_guaxu_skip
parse_guaxu_check_ident:
    CMPI R0, #2
    JNE parse_guaxu_check_modifier
    ; 尝试查找六十四卦助记符
    PUSH R1
    MOV R0, R1
    CALL lookup_mnemonic
    CMPI R0, #-1
    POP R1
    JNE parse_guaxu_found_iching
    ; 尝试查找原生CPU指令助记符
    PUSH R1
    MOV R0, R1
    CALL lookup_native
    CMPI R0, #-1
    POP R1
    JE parse_guaxu_skip_ident
    ; 找到原生指令，R0=native_opcode
    MOV R17, R0
    CALL codegen_next_token
    ; 解析原生指令操作数
    JMP parse_native_ops
parse_guaxu_found_iching:
    ; 找到六十四卦助记符，R0=opcode
    MOV R17, R0
    CALL codegen_next_token
    ; 检查修饰符
    MOVI R18, #0
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_guaxu_emit
    CALL codegen_read_token
    CMPI R0, #6
    JNE parse_guaxu_parse_ops
    ; 是修饰符
    PUSH R1
    MOV R0, R1
    CALL lookup_modifier
    MOV R18, R0
    POP R1
    CALL codegen_next_token
parse_guaxu_parse_ops:
    ; 解析操作数
    MOVI R19, #0
    MOVI R20, #0
    ; 第一个操作数
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_guaxu_emit
    CALL codegen_read_token
    ; 检查是否为寄存器
    CMPI R0, #2
    JNE parse_guaxu_check_num1
    PUSH R1
    MOV R0, R1
    CALL parse_register_name
    CMPI R0, #-1
    POP R1
    JE parse_guaxu_emit_no_consume
    MOV R19, R0
    CALL codegen_next_token
    ; 检查逗号
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_guaxu_emit
    CALL codegen_read_token
    CMPI R0, #5
    JNE parse_guaxu_emit_no_consume
    CMPI R1, #44
    JNE parse_guaxu_emit_no_consume
    CALL codegen_next_token
    ; 第二个操作数
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_guaxu_emit
    CALL codegen_read_token
    CMPI R0, #2
    JNE parse_guaxu_check_num2
    PUSH R1
    MOV R0, R1
    CALL parse_register_name
    CMPI R0, #-1
    POP R1
    JE parse_guaxu_emit_no_consume
    MOV R20, R0
    CALL codegen_next_token
    JMP parse_guaxu_emit
parse_guaxu_check_num1:
    CMPI R0, #3
    JNE parse_guaxu_emit_no_consume
    MOV R19, R1
    CALL codegen_next_token
    ; 检查逗号
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_guaxu_emit
    CALL codegen_read_token
    CMPI R0, #5
    JNE parse_guaxu_emit_no_consume
    CMPI R1, #44
    JNE parse_guaxu_emit_no_consume
    CALL codegen_next_token
    ; 第二个操作数
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_guaxu_emit
    CALL codegen_read_token
parse_guaxu_check_num2:
    CMPI R0, #3
    JNE parse_guaxu_emit_no_consume
    MOV R20, R1
    CALL codegen_next_token
parse_guaxu_emit:
    ; 发射指令: opcode=R17, modifier=R18, op1=R19, op2=R20
    MOV R0, R17
    MOV R1, R18
    MOV R2, R19
    MOV R3, R20
    CALL codegen_emit_iching
    JMP parse_guaxu_loop
parse_guaxu_emit_no_consume:
    ; 当前token不是操作数，直接发射（无操作数/单操作数指令）
    MOV R0, R17
    MOV R1, R18
    MOV R2, R19
    MOV R3, R20
    CALL codegen_emit_iching
    JMP parse_guaxu_loop

; ========================================
; 解析原生CPU指令操作数并发射
; R17=native_opcode
; ========================================
parse_native_ops:
    ; R19=dst_reg, R20=src_reg, R21=imm_value, R22=has_imm
    MOVI R19, #0
    MOVI R20, #0
    MOVI R21, #0
    MOVI R22, #0
    ; 检查是否为无操作数指令 (NOP, HLT, RET, PUSHA, POPA)
    ; opcode in {0x00, 0x01, 0x3D, 0x3A, 0x3B}
    CMPI R17, #0
    JE parse_native_emit
    CMPI R17, #1
    JE parse_native_emit
    CMPI R17, #61
    JE parse_native_emit
    CMPI R17, #58
    JE parse_native_emit
    CMPI R17, #59
    JE parse_native_emit
    ; 第一个操作数（目标寄存器）
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_native_emit
    CALL codegen_read_token
    ; 检查是否为寄存器
    CMPI R0, #2
    JNE parse_native_check_imm1
    PUSH R1
    MOV R0, R1
    CALL parse_register_name
    CMPI R0, #-1
    POP R1
    JE parse_native_emit_no_consume
    MOV R19, R0
    CALL codegen_next_token
    JMP parse_native_check_comma
parse_native_check_imm1:
    ; 检查是否为立即数 (#value)
    CMPI R0, #3
    JNE parse_native_emit_no_consume
    MOV R21, R1
    MOVI R22, #1
    CALL codegen_next_token
    JMP parse_native_emit
parse_native_check_comma:
    ; 检查逗号
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_native_emit
    CALL codegen_read_token
    CMPI R0, #5
    JNE parse_native_emit_no_consume
    CMPI R1, #44
    JNE parse_native_emit_no_consume
    CALL codegen_next_token
    ; 第二个操作数（源寄存器或立即数）
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_native_emit
    CALL codegen_read_token
    CMPI R0, #2
    JNE parse_native_check_imm2
    ; 源寄存器
    PUSH R1
    MOV R0, R1
    CALL parse_register_name
    CMPI R0, #-1
    POP R1
    JE parse_native_emit_no_consume
    MOV R20, R0
    CALL codegen_next_token
    JMP parse_native_emit
parse_native_check_imm2:
    ; 立即数
    CMPI R0, #3
    JNE parse_native_emit_no_consume
    MOV R21, R1
    MOVI R22, #1
    CALL codegen_next_token
parse_native_emit:
    ; 发射原生指令
    MOV R0, R17
    MOV R1, R19
    MOV R2, R20
    MOV R3, R21
    MOV R4, R22
    CALL codegen_emit_native
    JMP parse_guaxu_loop
parse_native_emit_no_consume:
    ; 当前token不是操作数，直接发射
    MOV R0, R17
    MOV R1, R19
    MOV R2, R20
    MOV R3, R21
    MOV R4, R22
    CALL codegen_emit_native
    JMP parse_guaxu_loop
parse_guaxu_check_modifier:
    CMPI R0, #6
    JNE parse_guaxu_skip
    CALL codegen_next_token
    JMP parse_guaxu_loop
parse_guaxu_skip_ident:
    CALL codegen_next_token
    JMP parse_guaxu_loop
parse_guaxu_skip:
    CALL codegen_next_token
    JMP parse_guaxu_loop
parse_guaxu_end:
    CALL codegen_next_token
parse_guaxu_done:
    RET

; 跳过花括号块
parse_skip_block:
    CALL codegen_next_token
    MOVI R18, #1
parse_skip_loop:
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_skip_done
    CALL codegen_read_token
    CMPI R0, #5
    JNE parse_skip_next
    CMPI R1, #123
    JNE parse_skip_check_close
    INC R18
    JMP parse_skip_next
parse_skip_check_close:
    CMPI R1, #125
    JNE parse_skip_next
    DEC R18
    CMPI R18, #0
    JE parse_skip_close
    JMP parse_skip_next
parse_skip_next:
    CALL codegen_next_token
    JMP parse_skip_loop
parse_skip_close:
    CALL codegen_next_token
parse_skip_done:
    RET

; 跳过@关键字后的内容直到下一个@
parse_skip_rest:
    CALL codegen_next_token
parse_skip_rest_loop:
    CALL codegen_has_tokens
    CMPI R0, #0
    JE parse_skip_rest_done
    CALL codegen_read_token
    CMPI R0, #5
    JNE parse_skip_rest_next
    CMPI R1, #64
    JE parse_skip_rest_done
parse_skip_rest_next:
    CALL codegen_next_token
    JMP parse_skip_rest_loop
parse_skip_rest_done:
    RET
"""

MAIN_ASM = """
main:
    CALL lexer_tokenize
    CALL codegen_init
    CALL parse_program
    MOV R0, R12
    SUB R0, #0x11000
    HLT
"""

FULL_COMPILER_ASM = "JMP main\n" + STDLIB_ASM + LEXER_ASM + LOOKUP_ASM + CODEGEN_ASM + PARSER_ASM + MAIN_ASM


class BootstrapCompiler:
    def __init__(self):
        self.vm = ExtendedIChingVM2()
        self._mnemonic_table_loaded = False

    def _preprocess_source(self, source: str) -> str:
        result = source
        result = re.sub(r'[\u4DC0-\u4DFF]', '', result)
        result = result.replace('\u5366\u5E8F', 'GUAXU')
        result = result.replace('\u201C', '"')
        result = result.replace('\u201D', '"')
        result = result.replace('\uFF08', '(')
        result = result.replace('\uFF09', ')')
        result = self._resolve_guaxu_labels(result)
        return result

    def _resolve_guaxu_labels(self, source: str) -> str:
        iching_opcodes = {m for m, _ in MNEMONICS}
        native_opcodes = {m for m, _ in NATIVE_MNEMONICS}
        native_imm_always = {"CMPI", "JMP", "JE", "JNE", "JL", "JLE", "JG", "JGE",
                             "JC", "JNC", "MOVI", "CALL"}
        native_no_operand = {"NOP", "HLT", "RET", "PUSHA", "POPA"}

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
                resolved = self._resolve_labels_in_block(guaxu_lines, iching_opcodes,
                                                          native_opcodes, native_imm_always,
                                                          native_no_operand)
                result_lines.extend(resolved)
                in_guaxu = False
                guaxu_lines = []

        if in_guaxu and guaxu_lines:
            resolved = self._resolve_labels_in_block(guaxu_lines, iching_opcodes,
                                                      native_opcodes, native_imm_always,
                                                      native_no_operand)
            result_lines.extend(resolved)

        return '\n'.join(result_lines)

    def _resolve_labels_in_block(self, lines, iching_opcodes, native_opcodes,
                                  native_imm_always, native_no_operand):
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
            is_label = raw_first.endswith(':') or (stripped.rstrip().endswith(':')
                                                    and first not in iching_opcodes
                                                    and first not in native_opcodes)
            if is_label:
                labels[first] = offset
                instructions.append((offset, line, None))
                continue

            if first in iching_opcodes:
                size = 4
                instructions.append((offset, line, first))
                offset += size
            elif first in native_opcodes:
                if first in native_no_operand:
                    size = 3
                elif first in native_imm_always:
                    size = 7
                else:
                    has_imm = False
                    for w in words[1:]:
                        w = w.rstrip(',').lstrip(',')
                        if w.startswith('#') or w.isdigit() or (w.startswith('0x') and len(w) > 2):
                            has_imm = True
                            break
                    size = 7 if has_imm else 3
                instructions.append((offset, line, first))
                offset += size
            else:
                instructions.append((offset, line, None))

        result = []
        for off, line, mnemonic in instructions:
            if mnemonic is None:
                result.append(line)
                continue

            stripped = line.strip()

            if any(lbl in stripped for lbl in labels):
                import re as _re
                resolved = _re.sub(
                    r'(?<![a-zA-Z_#])(' + '|'.join(_re.escape(k) for k in labels) + r')(?![a-zA-Z_0-9])',
                    lambda m: '#' + str(labels[m.group(1)]),
                    stripped
                )
                result.append('    ' + resolved)
            else:
                result.append(line)

        return result

    def _load_mnemonic_table(self):
        vm = self.vm
        str_offset = 0
        for i, (mnemonic, opcode) in enumerate(MNEMONICS):
            str_addr = MNEMONIC_STRINGS + str_offset
            vm.load_string(str_addr, mnemonic)
            entry_addr = MNEMONIC_TABLE + i * 8
            vm._store_word_heap(entry_addr, str_addr)
            vm._store_word_heap(entry_addr + 4, opcode)
            str_offset += len(mnemonic) + 1

        mod_strings = {
            0x33500: "ASYNC", 0x33507: "ATOMIC", 0x33514: "PRIV",
            0x33519: "WEAK", 0x33524: "STRONG", 0x33531: "VOLATILE",
        }
        for addr, s in mod_strings.items():
            vm.load_string(addr, s)

        kw_strings = {
            0x33600: "evolang", 0x33608: "locus", 0x3360E: "xiangci",
            0x33616: "meta_locus", 0x33621: "GUAXU",
        }
        for addr, s in kw_strings.items():
            vm.load_string(addr, s)

        self._mnemonic_table_loaded = True

    def _load_native_table(self):
        vm = self.vm
        str_offset = 0
        for i, (mnemonic, opcode) in enumerate(NATIVE_MNEMONICS):
            str_addr = NATIVE_STRINGS + str_offset
            vm.load_string(str_addr, mnemonic)
            entry_addr = NATIVE_TABLE + i * 8
            vm._store_word_heap(entry_addr, str_addr)
            vm._store_word_heap(entry_addr + 4, opcode)
            str_offset += len(mnemonic) + 1

    def _ensure_table_loaded(self):
        if not self._mnemonic_table_loaded:
            self._load_mnemonic_table()
            self._load_native_table()

    def compile_source(self, source: str) -> dict:
        vm = self.vm
        vm.__init__()

        self._load_mnemonic_table()
        self._load_native_table()

        processed = self._preprocess_source(source)
        vm.load_string(INPUT_BUF, processed)
        vm.load_assembled(FULL_COMPILER_ASM)

        vm.registers[0] = INPUT_BUF
        vm.registers[29] = vm.STACK_SIZE
        vm.run(max_cycles=5000000)

        output_size = vm.registers[0]
        result = {
            "success": vm.state == 3,
            "token_count": vm.registers[10],
            "locus_count": vm.registers[15],
            "output_size": output_size,
            "cycles": vm.cycle_count,
        }
        if output_size > 0:
            raw = bytes(vm.heap[OUTPUT_BUF:OUTPUT_BUF + min(output_size, 24576)])
            if raw[:4] == b'EVOB':
                header_size = struct.unpack(">H", raw[6:8])[0]
                bytecode_offset = HEADER_RESERVE
                bytecode_data = raw[bytecode_offset:]
                compacted = raw[:header_size] + bytecode_data
                result["output_bytes"] = compacted
                result["output_hex"] = compacted.hex()
                result["evob_valid"] = True
                version = struct.unpack(">H", raw[4:6])[0]
                locus_count = struct.unpack(">H", raw[8:10])[0]
                result["evob_version"] = version
                result["evob_header_size"] = header_size
                result["evob_locus_count"] = locus_count
                result["output_size"] = len(compacted)
                if header_size >= 10 and locus_count > 0:
                    offsets = []
                    for i in range(min(locus_count, 16)):
                        off = struct.unpack(">I", raw[10 + i * 4:14 + i * 4])[0]
                        offsets.append(off)
                    result["evob_locus_offsets"] = offsets
                    bytecode = bytecode_data
                    result["bytecode_size"] = len(bytecode)
                    opcode_to_mnem = {}
                    for mname, opc in MNEMONICS:
                        opcode_to_mnem[opc] = mname
                    native_opc_to_mnem = {}
                    for mname, opc in NATIVE_MNEMONICS:
                        native_opc_to_mnem[opc] = mname
                    instructions = []
                    pos = 0
                    while pos < len(bytecode) and len(instructions) < 64:
                        b1 = bytecode[pos]
                        itype = (b1 >> 6) & 0x03
                        if itype == 0x02:
                            if pos + 3 >= len(bytecode):
                                break
                            opcode = b1 & 0x3F
                            modifier = bytecode[pos + 1]
                            op1 = bytecode[pos + 2]
                            op2 = bytecode[pos + 3]
                            mnem = opcode_to_mnem.get(opcode, f"?{opcode}")
                            instructions.append({
                                "type": "iching", "opcode": opcode,
                                "mnemonic": mnem, "modifier": modifier,
                                "op1": op1, "op2": op2
                            })
                            pos += 4
                        elif itype == 0x01:
                            if pos + 2 >= len(bytecode):
                                break
                            native_opc = b1 & 0x3F
                            dst = bytecode[pos + 1] & 0x1F
                            src = bytecode[pos + 2] & 0x1F
                            has_imm = bool(bytecode[pos + 1] & 0x20)
                            mnem = native_opc_to_mnem.get(native_opc, f"N?{native_opc}")
                            instr = {
                                "type": "native", "opcode": native_opc,
                                "mnemonic": mnem, "modifier": 0,
                                "op1": dst, "op2": src
                            }
                            pos += 3
                            if has_imm or native_opc in NATIVE_IMM_ALWAYS:
                                if pos + 3 < len(bytecode):
                                    imm = struct.unpack('<I', bytecode[pos:pos+4])[0]
                                    instr["imm"] = imm
                                    pos += 4
                            instructions.append(instr)
                        else:
                            break
                    result["instruction_count"] = len(instructions)
                    result["instructions"] = instructions
            else:
                result["output_bytes"] = raw
                result["output_hex"] = raw.hex()
                result["evob_valid"] = False
        return result

    def test_lexer(self, source: str) -> dict:
        vm = self.vm
        vm.__init__()
        self._load_mnemonic_table()
        self._load_native_table()

        processed = self._preprocess_source(source)
        vm.load_string(INPUT_BUF, processed)
        lexer_asm = "JMP test_main\n" + STDLIB_ASM + LEXER_ASM + """
test_main:
    CALL lexer_tokenize
    HLT
"""
        vm.load_assembled(lexer_asm)
        vm.registers[0] = INPUT_BUF
        vm.registers[29] = vm.STACK_SIZE
        vm.run(max_cycles=100000)

        token_count = vm.registers[10]
        tokens = []
        type_names = {
            1: "KEYWORD", 2: "IDENT", 3: "NUMBER", 4: "STRING",
            5: "SYMBOL", 6: "MODIFIER", 9: "NEWLINE"
        }
        for i in range(min(token_count, 100)):
            tok_addr = TOKEN_BUF + i * 8
            tok_type = vm._load_word_heap(tok_addr)
            tok_val = vm._load_word_heap(tok_addr + 4)
            type_name = type_names.get(tok_type, f"?({tok_type})")
            if tok_type == 3:
                val_str = str(tok_val)
            elif tok_type == 5:
                val_str = chr(tok_val) if 32 <= tok_val < 127 else str(tok_val)
            elif tok_type in (2, 4, 6):
                val_str = vm.read_string(tok_val) if tok_val > 0 else ""
            else:
                val_str = str(tok_val)
            tokens.append({"type": type_name, "value": val_str})

        return {"success": vm.state == 3, "token_count": token_count, "tokens": tokens, "cycles": vm.cycle_count}


def test_all():
    print("=" * 60)
    print("易衍·Evomorph 完全自举编译器 v2 测试")
    print("=" * 60)

    compiler = BootstrapCompiler()

    print("\n[1] 词法分析器测试")
    test_cases = [
        ('@evolang "3.0"', ["SYMBOL @", "IDENT evolang", "STRING 3.0"]),
        ("CREA R0, R1", ["IDENT CREA", "IDENT R0", "SYMBOL ,", "IDENT R1"]),
        ("42", ["NUMBER 42"]),
        ("0xFF", ["NUMBER 255"]),
        ('@locus test { }', ["SYMBOL @", "IDENT locus", "IDENT test", "SYMBOL {", "SYMBOL }"]),
        ("SYNC .ASYNC", ["IDENT SYNC", "MODIFIER .ASYNC"]),
    ]
    for source, expected in test_cases:
        result = compiler.test_lexer(source)
        actual = [f"{t['type']} {t['value']}" for t in result['tokens']]
        ok = actual == expected
        status = "✓" if ok else "✗"
        print(f"  {status} '{source}' → {actual}")
        if not ok:
            print(f"    期望: {expected}")

    print("\n[2] 完整编译测试")
    test_source = '@evolang "3.0"\n\n@locus test {\n    mut_rate = 0.01\n    fitness = min_latency\n    env_target = ["linux-6.x"]\n    max_generations = 50\n\n    GUAXU: {\n        CREA R0, R1\n        FELLOWSHIP R0, R1\n        SYNC\n    }\n}\n'
    result = compiler.compile_source(test_source)
    print(f"  编译成功: {result['success']}")
    print(f"  Token数量: {result['token_count']}")
    print(f"  基因座数量: {result.get('locus_count', 'N/A')}")
    print(f"  输出大小: {result['output_size']} 字节")
    print(f"  执行周期: {result['cycles']}")
    if result.get('evob_valid'):
        print(f"  ✓ EVOB头部正确!")
        print(f"  版本: {result.get('evob_version')}")
        print(f"  头部大小: {result.get('evob_header_size')}")
        print(f"  基因座数: {result.get('evob_locus_count')}")
        if 'instructions' in result:
            print(f"  指令数: {result.get('instruction_count')}")
            for instr in result['instructions']:
                mod_str = f" mod={instr['modifier']}" if instr['modifier'] else ""
                print(f"    {instr['mnemonic']} R{instr['op1']}, R{instr['op2']}{mod_str}")
    elif result['output_size'] > 0:
        print(f"  ✗ EVOB头部错误: {result['output_bytes'][:4]}")

    print("\n[3] 与Python编译器对比测试")
    try:
        from evomorph.compiler import EvocCompiler
        py_compiler = EvocCompiler()
        py_result = py_compiler.compile(test_source, output_format="evb")
        if isinstance(py_result, bytes):
            print(f"  Python编译器输出: {len(py_result)} 字节")
            if py_result[:4] == b'EVOB':
                py_version = struct.unpack(">H", py_result[4:6])[0]
                py_header_size = struct.unpack(">H", py_result[6:8])[0]
                py_locus_count = struct.unpack(">H", py_result[8:10])[0]
                print(f"  Python: version={py_version}, header={py_header_size}, loci={py_locus_count}")
                if result.get('evob_valid') and result.get('evob_locus_count') == py_locus_count:
                    print(f"  ✓ 基因座数量一致!")
                else:
                    print(f"  ✗ 基因座数量不一致: 自举={result.get('evob_locus_count')}, Python={py_locus_count}")
        else:
            print(f"  Python编译器返回: {type(py_result)}")
    except Exception as e:
        print(f"  Python编译器不可用: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_all()
