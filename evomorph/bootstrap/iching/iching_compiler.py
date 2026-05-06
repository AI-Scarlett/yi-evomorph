#!/usr/bin/env python3
"""
易衍·Evomorph 纯IChing指令自举编译器 v3
用六十四卦扩展指令实现，在扩展虚拟机v2上运行

完全自举 = 虚拟机(Python/C) + 编译器全部逻辑(六十四卦扩展指令)

这是真正的Evomorph实现 - 编译器本身用易衍语言编写

指令映射:
  MOVI Rd, #imm     → CREA.1 Rd, Rd, #imm
  MOV Rd, Rs        → FELLOWSHIP.0 Rd, Rs
  ADD Rd, Rs/#imm   → GATHER.0 Rd, Rs/#imm
  SUB Rd, Rs/#imm   → GATHER.1 Rd, Rs/#imm
  MUL Rd, Rs/#imm   → GATHER.2 Rd, Rs/#imm
  AND Rd, Rs/#imm   → MATE.1 Rd, Rs/#imm
  OR  Rd, Rs/#imm   → MATE.3 Rd, Rs/#imm
  XOR Rd, Rs/#imm   → MATE.2 Rd, Rs/#imm
  SHL Rd, Rs/#imm   → MUT.1 Rd, Rs/#imm
  SHR Rd, Rs/#imm   → MUT.2 Rd, Rs/#imm
  CMP Rd, Rs/#imm   → FELLOWSHIP.1 Rd, Rs/#imm
  CMPI Rd, #imm     → FELLOWSHIP.2 Rd, Rd, #imm
  JMP label         → BRANCH.1 @label
  JE label          → BRANCH.2 @label
  JNE label         → BRANCH.3 @label
  JL label          → BRANCH.4 @label
  JLE label         → BRANCH.5 @label
  JG label          → BRANCH.6 @label
  JGE label         → BRANCH.7 @label
  LDR Rd, [Rs]      → RECV.1 Rd, Rs
  LDRB Rd, [Rs]     → RECV.2 Rd, Rs
  STR [Rd], Rs      → ALLOC.1 Rd, Rs
  STRB [Rd], Rs     → ALLOC.2 Rd, Rs
  PUSH Rd           → PUSH_UP.1 Rd, Rd
  POP Rd            → WELL.1 Rd, Rd
  CALL label        → ABUNDANCE.1 R0, R0, @label
  RET               → RETURN.0 R0, R0
  HLT               → RETURN.1 R0, R0
  INC Rd            → MICRO.1 Rd, Rd
  DEC Rd            → GRADUAL.1 Rd, Rd
  NOT Rd            → CAST.1 Rd, Rd
  NEG Rd            → CAST.2 Rd, Rd
  TEST Rd, Rs/#imm  → JOY.1 Rd, Rs/#imm
"""

import sys
import os
import re
import struct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
strlen:
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
    FELLOWSHIP.0 R4, R0
    CREA.1 R5, R5, #0
strlen_loop:
    RECV.2 R0, R4
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @strlen_done
    MICRO.1 R4, R4
    MICRO.1 R5, R5
    BRANCH.1 @strlen_loop
strlen_done:
    FELLOWSHIP.0 R0, R5
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0

strcmp:
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
strcmp_loop:
    RECV.2 R4, R0
    RECV.2 R5, R1
    FELLOWSHIP.1 R4, R5
    BRANCH.3 @strcmp_diff
    FELLOWSHIP.2 R4, R4, #0
    BRANCH.2 @strcmp_equal
    MICRO.1 R0, R0
    MICRO.1 R1, R1
    BRANCH.1 @strcmp_loop
strcmp_diff:
    BRANCH.4 @strcmp_less
    CREA.1 R0, R0, #1
    BRANCH.1 @strcmp_ret
strcmp_less:
    CREA.1 R0, R0, #4294967295
    BRANCH.1 @strcmp_ret
strcmp_equal:
    CREA.1 R0, R0, #0
strcmp_ret:
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0

is_whitespace:
    FELLOWSHIP.2 R0, R0, #32
    BRANCH.2 @is_ws_yes
    FELLOWSHIP.2 R0, R0, #9
    BRANCH.2 @is_ws_yes
    FELLOWSHIP.2 R0, R0, #10
    BRANCH.2 @is_ws_yes
    FELLOWSHIP.2 R0, R0, #13
    BRANCH.2 @is_ws_yes
    CREA.1 R0, R0, #0
    RETURN.0 R0, R0
is_ws_yes:
    CREA.1 R0, R0, #1
    RETURN.0 R0, R0

is_digit:
    FELLOWSHIP.2 R0, R0, #48
    BRANCH.4 @is_digit_no
    FELLOWSHIP.2 R0, R0, #57
    BRANCH.5 @is_digit_yes
is_digit_no:
    CREA.1 R0, R0, #0
    RETURN.0 R0, R0
is_digit_yes:
    CREA.1 R0, R0, #1
    RETURN.0 R0, R0

is_alpha:
    FELLOWSHIP.2 R0, R0, #65
    BRANCH.4 @is_alpha_lower
    FELLOWSHIP.2 R0, R0, #90
    BRANCH.5 @is_alpha_yes
is_alpha_lower:
    FELLOWSHIP.2 R0, R0, #97
    BRANCH.4 @is_alpha_no
    FELLOWSHIP.2 R0, R0, #122
    BRANCH.5 @is_alpha_yes
is_alpha_no:
    CREA.1 R0, R0, #0
    RETURN.0 R0, R0
is_alpha_yes:
    CREA.1 R0, R0, #1
    RETURN.0 R0, R0

is_alnum:
    PUSH_UP.1 R4, R4
    FELLOWSHIP.0 R4, R0
    ABUNDANCE.1 R0, R0, @is_digit
    FELLOWSHIP.2 R0, R0, #1
    BRANCH.2 @is_alnum_yes
    FELLOWSHIP.0 R0, R4
    ABUNDANCE.1 R0, R0, @is_alpha
    FELLOWSHIP.2 R0, R0, #1
    BRANCH.2 @is_alnum_yes
    CREA.1 R0, R0, #0
    WELL.1 R4, R4
    RETURN.0 R0, R0
is_alnum_yes:
    CREA.1 R0, R0, #1
    WELL.1 R4, R4
    RETURN.0 R0, R0

is_underscore:
    FELLOWSHIP.2 R0, R0, #95
    BRANCH.3 @is_under_no
    CREA.1 R0, R0, #1
    RETURN.0 R0, R0
is_under_no:
    CREA.1 R0, R0, #0
    RETURN.0 R0, R0

hex_char_to_val:
    FELLOWSHIP.2 R0, R0, #48
    BRANCH.4 @hex_invalid
    FELLOWSHIP.2 R0, R0, #57
    BRANCH.5 @hex_digit
    BRANCH.1 @hex_check_upper
hex_digit:
    GATHER.1 R0, R0, #48
    RETURN.0 R0, R0
hex_check_upper:
    FELLOWSHIP.2 R0, R0, #65
    BRANCH.4 @hex_check_lower
    FELLOWSHIP.2 R0, R0, #70
    BRANCH.5 @hex_upper
    BRANCH.1 @hex_check_lower
hex_upper:
    GATHER.1 R0, R0, #55
    RETURN.0 R0, R0
hex_check_lower:
    FELLOWSHIP.2 R0, R0, #97
    BRANCH.4 @hex_invalid
    FELLOWSHIP.2 R0, R0, #102
    BRANCH.5 @hex_lower
    BRANCH.1 @hex_invalid
hex_lower:
    GATHER.1 R0, R0, #87
    RETURN.0 R0, R0
hex_invalid:
    CREA.1 R0, R0, #4294967295
    RETURN.0 R0, R0

parse_register_name:
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
    PUSH_UP.1 R6, R6
    FELLOWSHIP.0 R4, R0
    RECV.2 R5, R4
    FELLOWSHIP.2 R5, R5, #82
    BRANCH.3 @parse_reg_fail
    MICRO.1 R4, R4
    RECV.2 R5, R4
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @is_digit
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_reg_fail
    CREA.1 R6, R6, #0
parse_reg_loop:
    RECV.2 R5, R4
    FELLOWSHIP.2 R5, R5, #0
    BRANCH.2 @parse_reg_done
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @is_digit
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_reg_done
    CREA.1 R0, R0, #10
    GATHER.2 R6, R0
    GATHER.1 R5, R5, #48
    GATHER.0 R6, R5
    MICRO.1 R4, R4
    BRANCH.1 @parse_reg_loop
parse_reg_done:
    FELLOWSHIP.1 R6, R6, #31
    BRANCH.6 @parse_reg_fail
    FELLOWSHIP.0 R0, R6
    WELL.1 R6, R6
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0
parse_reg_fail:
    CREA.1 R0, R0, #4294967295
    WELL.1 R6, R6
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0
"""

LEXER_ASM = """
lexer_init:
    FELLOWSHIP.0 R8, R0
    CREA.1 R9, R9, #0x9000
    CREA.1 R10, R10, #0
    CREA.1 R11, R11, #0x2B000
    RETURN.0 R0, R0

lexer_skip_whitespace:
    RECV.2 R0, R8
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @skip_ws_done
    ABUNDANCE.1 R0, R0, @is_whitespace
    FELLOWSHIP.2 R0, R0, #1
    BRANCH.3 @skip_ws_done
    MICRO.1 R8, R8
    BRANCH.1 @lexer_skip_whitespace
skip_ws_done:
    RETURN.0 R0, R0

lexer_skip_comment:
    MICRO.1 R8, R8
    MICRO.1 R8, R8
skip_comment_loop:
    RECV.2 R0, R8
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @skip_comment_done
    FELLOWSHIP.2 R0, R0, #10
    BRANCH.2 @skip_comment_done
    MICRO.1 R8, R8
    BRANCH.1 @skip_comment_loop
skip_comment_done:
    RETURN.0 R0, R0

lexer_skip_utf8:
    RECV.2 R0, R8
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @skip_utf8_done
    FELLOWSHIP.2 R0, R0, #128
    BRANCH.4 @skip_utf8_done
    FELLOWSHIP.2 R0, R0, #192
    BRANCH.7 @skip_utf8_2
    MICRO.1 R8, R8
    BRANCH.1 @lexer_skip_utf8
skip_utf8_2:
    FELLOWSHIP.2 R0, R0, #224
    BRANCH.7 @skip_utf8_3
    MICRO.1 R8, R8
    MICRO.1 R8, R8
    BRANCH.1 @lexer_skip_utf8
skip_utf8_3:
    FELLOWSHIP.2 R0, R0, #240
    BRANCH.7 @skip_utf8_4
    MICRO.1 R8, R8
    MICRO.1 R8, R8
    MICRO.1 R8, R8
    BRANCH.1 @lexer_skip_utf8
skip_utf8_4:
    MICRO.1 R8, R8
    MICRO.1 R8, R8
    MICRO.1 R8, R8
    MICRO.1 R8, R8
    BRANCH.1 @lexer_skip_utf8
skip_utf8_done:
    RETURN.0 R0, R0

lexer_emit_token:
    PUSH_UP.1 R4, R4
    ALLOC.1 R9, R1
    CREA.1 R4, R4, #4
    GATHER.0 R9, R4
    ALLOC.1 R9, R0
    GATHER.0 R9, R4
    MICRO.1 R10, R10
    WELL.1 R4, R4
    RETURN.0 R0, R0

lexer_scan_number:
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
    PUSH_UP.1 R6, R6
    CREA.1 R1, R1, #0
    FELLOWSHIP.0 R5, R0
    CREA.1 R6, R6, #0
scan_num_loop:
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @is_digit
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @scan_num_check_hex
    CREA.1 R4, R4, #10
    GATHER.2 R1, R4
    GATHER.1 R5, R5, #48
    GATHER.0 R1, R5
    MICRO.1 R8, R8
    RECV.2 R5, R8
    FELLOWSHIP.2 R5, R5, #0
    BRANCH.2 @scan_num_emit
    BRANCH.1 @scan_num_loop
scan_num_check_hex:
    FELLOWSHIP.2 R5, R5, #120
    BRANCH.2 @scan_num_hex
    FELLOWSHIP.2 R5, R5, #88
    BRANCH.2 @scan_num_hex
    BRANCH.1 @scan_num_emit
scan_num_hex:
    MICRO.1 R8, R8
    CREA.1 R1, R1, #0
scan_hex_loop:
    RECV.2 R0, R8
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @scan_num_emit
    ABUNDANCE.1 R0, R0, @hex_char_to_val
    FELLOWSHIP.2 R0, R0, #4294967295
    BRANCH.2 @scan_num_emit
    CREA.1 R4, R4, #16
    GATHER.2 R1, R4
    GATHER.0 R1, R0
    MICRO.1 R8, R8
    BRANCH.1 @scan_hex_loop
scan_num_emit:
    CREA.1 R0, R0, #3
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    WELL.1 R6, R6
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0

lexer_scan_identifier:
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
    FELLOWSHIP.0 R4, R11
scan_id_loop:
    ALLOC.2 R11, R0
    MICRO.1 R11, R11
    MICRO.1 R8, R8
    RECV.2 R5, R8
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @is_alnum
    FELLOWSHIP.2 R0, R0, #1
    BRANCH.2 @scan_id_cont
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @is_underscore
    FELLOWSHIP.2 R0, R0, #1
    BRANCH.2 @scan_id_cont
    BRANCH.1 @scan_id_done
scan_id_cont:
    FELLOWSHIP.0 R0, R5
    BRANCH.1 @scan_id_loop
scan_id_done:
    CREA.1 R0, R0, #0
    ALLOC.2 R11, R0
    MICRO.1 R11, R11
    FELLOWSHIP.0 R1, R4
    CREA.1 R0, R0, #2
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0

lexer_scan_modifier:
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
    FELLOWSHIP.0 R4, R11
    CREA.1 R0, R0, #46
    ALLOC.2 R11, R0
    MICRO.1 R11, R11
    MICRO.1 R8, R8
scan_mod_loop:
    RECV.2 R5, R8
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @is_alpha
    FELLOWSHIP.2 R0, R0, #1
    BRANCH.3 @scan_mod_done
    ALLOC.2 R11, R5
    MICRO.1 R11, R11
    MICRO.1 R8, R8
    BRANCH.1 @scan_mod_loop
scan_mod_done:
    CREA.1 R0, R0, #0
    ALLOC.2 R11, R0
    MICRO.1 R11, R11
    FELLOWSHIP.0 R1, R4
    CREA.1 R0, R0, #6
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0

lexer_scan_string:
    MICRO.1 R8, R8
    PUSH_UP.1 R4, R4
    FELLOWSHIP.0 R4, R11
scan_str_loop:
    RECV.2 R0, R8
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @scan_str_done
    FELLOWSHIP.2 R0, R0, #34
    BRANCH.2 @scan_str_end
    FELLOWSHIP.2 R0, R0, #92
    BRANCH.2 @scan_str_escape
    ALLOC.2 R11, R0
    MICRO.1 R11, R11
    MICRO.1 R8, R8
    BRANCH.1 @scan_str_loop
scan_str_escape:
    MICRO.1 R8, R8
    RECV.2 R0, R8
    FELLOWSHIP.2 R0, R0, #110
    BRANCH.3 @scan_str_esc_t
    CREA.1 R0, R0, #10
    BRANCH.1 @scan_str_esc_store
scan_str_esc_t:
    FELLOWSHIP.2 R0, R0, #116
    BRANCH.3 @scan_str_esc_default
    CREA.1 R0, R0, #9
    BRANCH.1 @scan_str_esc_store
scan_str_esc_default:
    BRANCH.1 @scan_str_esc_store
scan_str_esc_store:
    ALLOC.2 R11, R0
    MICRO.1 R11, R11
    MICRO.1 R8, R8
    BRANCH.1 @scan_str_loop
scan_str_end:
    MICRO.1 R8, R8
scan_str_done:
    CREA.1 R0, R0, #0
    ALLOC.2 R11, R0
    MICRO.1 R11, R11
    FELLOWSHIP.0 R1, R4
    CREA.1 R0, R0, #4
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    WELL.1 R4, R4
    RETURN.0 R0, R0

lexer_tokenize:
    ABUNDANCE.1 R0, R0, @lexer_init
tokenize_loop:
    ABUNDANCE.1 R0, R0, @lexer_skip_whitespace
    RECV.2 R0, R8
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @tokenize_done
    FELLOWSHIP.2 R0, R0, #128
    BRANCH.7 @tokenize_skip_utf8
    FELLOWSHIP.2 R0, R0, #47
    BRANCH.3 @tokenize_check_at
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
    RECV.2 R4, R8
    CREA.1 R5, R5, #1
    GATHER.0 R5, R8
    RECV.2 R5, R5
    FELLOWSHIP.2 R5, R5, #47
    WELL.1 R5, R5
    WELL.1 R4, R4
    BRANCH.3 @tokenize_check_at
    ABUNDANCE.1 R0, R0, @lexer_skip_comment
    BRANCH.1 @tokenize_loop
tokenize_skip_utf8:
    ABUNDANCE.1 R0, R0, @lexer_skip_utf8
    BRANCH.1 @tokenize_loop
tokenize_check_at:
    FELLOWSHIP.2 R0, R0, #64
    BRANCH.3 @tokenize_check_quote
    CREA.1 R0, R0, #5
    CREA.1 R1, R1, #64
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    MICRO.1 R8, R8
    BRANCH.1 @tokenize_loop
tokenize_check_quote:
    FELLOWSHIP.2 R0, R0, #34
    BRANCH.3 @tokenize_check_digit
    ABUNDANCE.1 R0, R0, @lexer_scan_string
    BRANCH.1 @tokenize_loop
tokenize_check_digit:
    RECV.2 R5, R8
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @is_digit
    FELLOWSHIP.2 R0, R0, #1
    BRANCH.3 @tokenize_check_dot
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @lexer_scan_number
    BRANCH.1 @tokenize_loop
tokenize_check_dot:
    FELLOWSHIP.2 R5, R5, #46
    BRANCH.3 @tokenize_check_alpha
    ABUNDANCE.1 R0, R0, @lexer_scan_modifier
    BRANCH.1 @tokenize_loop
tokenize_check_alpha:
    RECV.2 R5, R8
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @is_alpha
    FELLOWSHIP.2 R0, R0, #1
    BRANCH.3 @tokenize_check_underscore
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @lexer_scan_identifier
    BRANCH.1 @tokenize_loop
tokenize_check_underscore:
    FELLOWSHIP.2 R5, R5, #95
    BRANCH.3 @tokenize_check_symbol
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @lexer_scan_identifier
    BRANCH.1 @tokenize_loop
tokenize_check_symbol:
    RECV.2 R0, R8
    FELLOWSHIP.2 R0, R0, #123
    BRANCH.3 @tok_sym_rbrace
    CREA.1 R0, R0, #5
    CREA.1 R1, R1, #123
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    MICRO.1 R8, R8
    BRANCH.1 @tokenize_loop
tok_sym_rbrace:
    FELLOWSHIP.2 R0, R0, #125
    BRANCH.3 @tok_sym_lparen
    CREA.1 R0, R0, #5
    CREA.1 R1, R1, #125
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    MICRO.1 R8, R8
    BRANCH.1 @tokenize_loop
tok_sym_lparen:
    FELLOWSHIP.2 R0, R0, #40
    BRANCH.3 @tok_sym_rparen
    CREA.1 R0, R0, #5
    CREA.1 R1, R1, #40
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    MICRO.1 R8, R8
    BRANCH.1 @tokenize_loop
tok_sym_rparen:
    FELLOWSHIP.2 R0, R0, #41
    BRANCH.3 @tok_sym_lbracket
    CREA.1 R0, R0, #5
    CREA.1 R1, R1, #41
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    MICRO.1 R8, R8
    BRANCH.1 @tokenize_loop
tok_sym_lbracket:
    FELLOWSHIP.2 R0, R0, #91
    BRANCH.3 @tok_sym_rbracket
    CREA.1 R0, R0, #5
    CREA.1 R1, R1, #91
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    MICRO.1 R8, R8
    BRANCH.1 @tokenize_loop
tok_sym_rbracket:
    FELLOWSHIP.2 R0, R0, #93
    BRANCH.3 @tok_sym_comma
    CREA.1 R0, R0, #5
    CREA.1 R1, R1, #93
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    MICRO.1 R8, R8
    BRANCH.1 @tokenize_loop
tok_sym_comma:
    FELLOWSHIP.2 R0, R0, #44
    BRANCH.3 @tok_sym_colon
    CREA.1 R0, R0, #5
    CREA.1 R1, R1, #44
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    MICRO.1 R8, R8
    BRANCH.1 @tokenize_loop
tok_sym_colon:
    FELLOWSHIP.2 R0, R0, #58
    BRANCH.3 @tok_sym_eq
    CREA.1 R0, R0, #5
    CREA.1 R1, R1, #58
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    MICRO.1 R8, R8
    BRANCH.1 @tokenize_loop
tok_sym_eq:
    FELLOWSHIP.2 R0, R0, #61
    BRANCH.3 @tok_sym_newline
    CREA.1 R0, R0, #5
    CREA.1 R1, R1, #61
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    MICRO.1 R8, R8
    BRANCH.1 @tokenize_loop
tok_sym_newline:
    FELLOWSHIP.2 R0, R0, #10
    BRANCH.3 @tok_sym_semicolon
    CREA.1 R0, R0, #9
    CREA.1 R1, R1, #10
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    MICRO.1 R8, R8
    BRANCH.1 @tokenize_loop
tok_sym_semicolon:
    FELLOWSHIP.2 R0, R0, #59
    BRANCH.3 @tok_sym_skip
    MICRO.1 R8, R8
    BRANCH.1 @tokenize_loop
tok_sym_skip:
    MICRO.1 R8, R8
    BRANCH.1 @tokenize_loop
tokenize_done:
    RETURN.0 R0, R0
"""

LOOKUP_ASM = """
lookup_mnemonic:
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
    PUSH_UP.1 R6, R6
    PUSH_UP.1 R7, R7
    FELLOWSHIP.0 R7, R0
    CREA.1 R4, R4, #0x33000
    CREA.1 R6, R6, #64
lookup_loop:
    FELLOWSHIP.2 R6, R6, #0
    BRANCH.2 @lookup_not_found
    RECV.1 R5, R4
    FELLOWSHIP.0 R0, R7
    FELLOWSHIP.0 R1, R5
    ABUNDANCE.1 R0, R0, @strcmp
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @lookup_found
    CREA.1 R5, R5, #8
    GATHER.0 R4, R5
    GRADUAL.1 R6, R6
    BRANCH.1 @lookup_loop
lookup_found:
    CREA.1 R5, R5, #4
    GATHER.0 R4, R5
    RECV.1 R0, R4
    WELL.1 R7, R7
    WELL.1 R6, R6
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0
lookup_not_found:
    CREA.1 R0, R0, #4294967295
    WELL.1 R7, R7
    WELL.1 R6, R6
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0

lookup_modifier:
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
    RECV.2 R4, R0
    FELLOWSHIP.2 R4, R4, #46
    BRANCH.3 @lookup_mod_zero
    CREA.1 R5, R5, #1
    GATHER.0 R5, R0
    PUSH_UP.1 R0, R0
    PUSH_UP.1 R1, R1
    CREA.1 R0, R0, #0x33500
    FELLOWSHIP.0 R1, R5
    ABUNDANCE.1 R0, R0, @strcmp
    FELLOWSHIP.2 R0, R0, #0
    WELL.1 R1, R1
    WELL.1 R0, R0
    BRANCH.3 @lookup_mod_atomic
    CREA.1 R0, R0, #32
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0
lookup_mod_atomic:
    PUSH_UP.1 R0, R0
    PUSH_UP.1 R1, R1
    CREA.1 R0, R0, #0x33507
    FELLOWSHIP.0 R1, R5
    ABUNDANCE.1 R0, R0, @strcmp
    FELLOWSHIP.2 R0, R0, #0
    WELL.1 R1, R1
    WELL.1 R0, R0
    BRANCH.3 @lookup_mod_priv
    CREA.1 R0, R0, #16
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0
lookup_mod_priv:
    PUSH_UP.1 R0, R0
    PUSH_UP.1 R1, R1
    CREA.1 R0, R0, #0x33514
    FELLOWSHIP.0 R1, R5
    ABUNDANCE.1 R0, R0, @strcmp
    FELLOWSHIP.2 R0, R0, #0
    WELL.1 R1, R1
    WELL.1 R0, R0
    BRANCH.3 @lookup_mod_weak
    CREA.1 R0, R0, #8
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0
lookup_mod_weak:
    PUSH_UP.1 R0, R0
    PUSH_UP.1 R1, R1
    CREA.1 R0, R0, #0x33519
    FELLOWSHIP.0 R1, R5
    ABUNDANCE.1 R0, R0, @strcmp
    FELLOWSHIP.2 R0, R0, #0
    WELL.1 R1, R1
    WELL.1 R0, R0
    BRANCH.3 @lookup_mod_strong
    CREA.1 R0, R0, #4
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0
lookup_mod_strong:
    PUSH_UP.1 R0, R0
    PUSH_UP.1 R1, R1
    CREA.1 R0, R0, #0x33524
    FELLOWSHIP.0 R1, R5
    ABUNDANCE.1 R0, R0, @strcmp
    FELLOWSHIP.2 R0, R0, #0
    WELL.1 R1, R1
    WELL.1 R0, R0
    BRANCH.3 @lookup_mod_volatile
    CREA.1 R0, R0, #2
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0
lookup_mod_volatile:
    PUSH_UP.1 R0, R0
    PUSH_UP.1 R1, R1
    CREA.1 R0, R0, #0x33531
    FELLOWSHIP.0 R1, R5
    ABUNDANCE.1 R0, R0, @strcmp
    FELLOWSHIP.2 R0, R0, #0
    WELL.1 R1, R1
    WELL.1 R0, R0
    BRANCH.3 @lookup_mod_zero
    CREA.1 R0, R0, #1
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0
lookup_mod_zero:
    CREA.1 R0, R0, #0
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0

lookup_native:
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
    PUSH_UP.1 R6, R6
    PUSH_UP.1 R7, R7
    FELLOWSHIP.0 R7, R0
    CREA.1 R4, R4, #0x33700
    CREA.1 R6, R6, #44
lookup_native_loop:
    FELLOWSHIP.2 R6, R6, #0
    BRANCH.2 @lookup_native_not_found
    RECV.1 R5, R4
    FELLOWSHIP.0 R0, R7
    FELLOWSHIP.0 R1, R5
    ABUNDANCE.1 R0, R0, @strcmp
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @lookup_native_found
    CREA.1 R5, R5, #8
    GATHER.0 R4, R5
    GRADUAL.1 R6, R6
    BRANCH.1 @lookup_native_loop
lookup_native_found:
    CREA.1 R5, R5, #4
    GATHER.0 R4, R5
    RECV.1 R0, R4
    WELL.1 R7, R7
    WELL.1 R6, R6
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0
lookup_native_not_found:
    CREA.1 R0, R0, #4294967295
    WELL.1 R7, R7
    WELL.1 R6, R6
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0
"""

CODEGEN_ASM = """
codegen_init:
    CREA.1 R12, R12, #0x11000
    CREA.1 R4, R4, #64
    GATHER.0 R12, R4
    CREA.1 R13, R13, #0
    FELLOWSHIP.0 R14, R10
    CREA.1 R15, R15, #0
    RETURN.0 R0, R0

codegen_emit_byte:
    ALLOC.2 R12, R0
    MICRO.1 R12, R12
    RETURN.0 R0, R0

codegen_emit_word_be:
    PUSH_UP.1 R4, R4
    FELLOWSHIP.0 R4, R0
    MUT.2 R4, R4, #24
    MATE.1 R4, R4, #255
    ALLOC.2 R12, R4
    MICRO.1 R12, R12
    FELLOWSHIP.0 R4, R0
    MUT.2 R4, R4, #16
    MATE.1 R4, R4, #255
    ALLOC.2 R12, R4
    MICRO.1 R12, R12
    FELLOWSHIP.0 R4, R0
    MUT.2 R4, R4, #8
    MATE.1 R4, R4, #255
    ALLOC.2 R12, R4
    MICRO.1 R12, R12
    FELLOWSHIP.0 R4, R0
    MATE.1 R4, R4, #255
    ALLOC.2 R12, R4
    MICRO.1 R12, R12
    WELL.1 R4, R4
    RETURN.0 R0, R0

codegen_emit_half_be:
    PUSH_UP.1 R4, R4
    FELLOWSHIP.0 R4, R0
    MUT.2 R4, R4, #8
    MATE.1 R4, R4, #255
    ALLOC.2 R12, R4
    MICRO.1 R12, R12
    FELLOWSHIP.0 R4, R0
    MATE.1 R4, R4, #255
    ALLOC.2 R12, R4
    MICRO.1 R12, R12
    WELL.1 R4, R4
    RETURN.0 R0, R0

codegen_read_token:
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
    FELLOWSHIP.0 R4, R13
    CREA.1 R5, R5, #8
    GATHER.2 R4, R5
    CREA.1 R5, R5, #0x9000
    GATHER.0 R5, R4
    RECV.1 R1, R5
    CREA.1 R4, R4, #4
    GATHER.0 R5, R4
    RECV.1 R0, R5
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0

codegen_next_token:
    MICRO.1 R13, R13
    RETURN.0 R0, R0

codegen_has_tokens:
    FELLOWSHIP.1 R13, R14
    BRANCH.4 @has_tokens_yes
    CREA.1 R0, R0, #0
    RETURN.0 R0, R0
has_tokens_yes:
    CREA.1 R0, R0, #1
    RETURN.0 R0, R0

codegen_emit_iching:
    PUSH_UP.1 R4, R4
    FELLOWSHIP.0 R4, R0
    MATE.1 R4, R4, #63
    CREA.1 R0, R0, #128
    MATE.3 R4, R0
    ALLOC.2 R12, R4
    MICRO.1 R12, R12
    ALLOC.2 R12, R1
    MICRO.1 R12, R12
    ALLOC.2 R12, R2
    MICRO.1 R12, R12
    ALLOC.2 R12, R3
    MICRO.1 R12, R12
    WELL.1 R4, R4
    RETURN.0 R0, R0

codegen_emit_native:
    PUSH_UP.1 R5, R5
    PUSH_UP.1 R6, R6
    FELLOWSHIP.0 R5, R0
    MATE.1 R5, R5, #63
    CREA.1 R6, R6, #64
    MATE.3 R5, R6
    ALLOC.2 R12, R5
    MICRO.1 R12, R12
    FELLOWSHIP.0 R5, R1
    MATE.1 R5, R5, #31
    FELLOWSHIP.2 R4, R4, #0
    BRANCH.2 @codegen_native_byte2
    CREA.1 R6, R6, #32
    MATE.3 R5, R6
codegen_native_byte2:
    ALLOC.2 R12, R5
    MICRO.1 R12, R12
    FELLOWSHIP.0 R5, R2
    MATE.1 R5, R5, #31
    ALLOC.2 R12, R5
    MICRO.1 R12, R12
    FELLOWSHIP.2 R4, R4, #0
    BRANCH.2 @codegen_native_done
    FELLOWSHIP.0 R5, R3
    MATE.1 R5, R5, #255
    ALLOC.2 R12, R5
    MICRO.1 R12, R12
    FELLOWSHIP.0 R5, R3
    MUT.2 R5, R5, #8
    MATE.1 R5, R5, #255
    ALLOC.2 R12, R5
    MICRO.1 R12, R12
    FELLOWSHIP.0 R5, R3
    MUT.2 R5, R5, #16
    MATE.1 R5, R5, #255
    ALLOC.2 R12, R5
    MICRO.1 R12, R12
    FELLOWSHIP.0 R5, R3
    MUT.2 R5, R5, #24
    MATE.1 R5, R5, #255
    ALLOC.2 R12, R5
    MICRO.1 R12, R12
codegen_native_done:
    WELL.1 R6, R6
    WELL.1 R5, R5
    RETURN.0 R0, R0

codegen_write_byte_at:
    PUSH_UP.1 R4, R4
    CREA.1 R4, R4, #0x11000
    GATHER.0 R4, R0
    ALLOC.2 R4, R1
    WELL.1 R4, R4
    RETURN.0 R0, R0

codegen_write_half_at:
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
    CREA.1 R4, R4, #0x11000
    GATHER.0 R4, R0
    FELLOWSHIP.0 R5, R1
    MUT.2 R5, R5, #8
    MATE.1 R5, R5, #255
    ALLOC.2 R4, R5
    MICRO.1 R4, R4
    FELLOWSHIP.0 R5, R1
    MATE.1 R5, R5, #255
    ALLOC.2 R4, R5
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0

codegen_write_word_at:
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
    CREA.1 R4, R4, #0x11000
    GATHER.0 R4, R0
    FELLOWSHIP.0 R5, R1
    MUT.2 R5, R5, #24
    MATE.1 R5, R5, #255
    ALLOC.2 R4, R5
    MICRO.1 R4, R4
    FELLOWSHIP.0 R5, R1
    MUT.2 R5, R5, #16
    MATE.1 R5, R5, #255
    ALLOC.2 R4, R5
    MICRO.1 R4, R4
    FELLOWSHIP.0 R5, R1
    MUT.2 R5, R5, #8
    MATE.1 R5, R5, #255
    ALLOC.2 R4, R5
    MICRO.1 R4, R4
    FELLOWSHIP.0 R5, R1
    MATE.1 R5, R5, #255
    ALLOC.2 R4, R5
    WELL.1 R5, R5
    WELL.1 R4, R4
    RETURN.0 R0, R0
"""

PARSER_ASM = """
parser_match:
    PUSH_UP.1 R2, R2
    PUSH_UP.1 R3, R3
    PUSH_UP.1 R4, R4
    PUSH_UP.1 R5, R5
    FELLOWSHIP.0 R4, R0
    FELLOWSHIP.0 R5, R1
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.1 R4, R0
    BRANCH.3 @parser_match_no
    FELLOWSHIP.1 R5, R1
    BRANCH.3 @parser_match_no
    CREA.1 R0, R0, #1
    WELL.1 R5, R5
    WELL.1 R4, R4
    WELL.1 R3, R3
    WELL.1 R2, R2
    RETURN.0 R0, R0
parser_match_no:
    CREA.1 R0, R0, #0
    WELL.1 R5, R5
    WELL.1 R4, R4
    WELL.1 R3, R3
    WELL.1 R2, R2
    RETURN.0 R0, R0

parse_program:
    CREA.1 R0, R0, #0
    CREA.1 R1, R1, #69
    ABUNDANCE.1 R0, R0, @codegen_write_byte_at
    CREA.1 R0, R0, #1
    CREA.1 R1, R1, #86
    ABUNDANCE.1 R0, R0, @codegen_write_byte_at
    CREA.1 R0, R0, #2
    CREA.1 R1, R1, #79
    ABUNDANCE.1 R0, R0, @codegen_write_byte_at
    CREA.1 R0, R0, #3
    CREA.1 R1, R1, #66
    ABUNDANCE.1 R0, R0, @codegen_write_byte_at
    CREA.1 R0, R0, #4
    CREA.1 R1, R1, #3
    ABUNDANCE.1 R0, R0, @codegen_write_half_at
    CREA.1 R0, R0, #6
    CREA.1 R1, R1, #0
    ABUNDANCE.1 R0, R0, @codegen_write_half_at
    CREA.1 R0, R0, #8
    CREA.1 R1, R1, #0
    ABUNDANCE.1 R0, R0, @codegen_write_half_at

parse_loop:
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_done
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #5
    BRANCH.3 @parse_skip_token
    FELLOWSHIP.2 R1, R1, #64
    BRANCH.3 @parse_check_brace
    ABUNDANCE.1 R0, R0, @parse_at_keyword
    BRANCH.1 @parse_loop
parse_check_brace:
    FELLOWSHIP.2 R1, R1, #123
    BRANCH.3 @parse_skip_token
    ABUNDANCE.1 R0, R0, @parse_skip_block
    BRANCH.1 @parse_loop
parse_skip_token:
    ABUNDANCE.1 R0, R0, @codegen_next_token
    BRANCH.1 @parse_loop
parse_done:
    CREA.1 R0, R0, #8
    FELLOWSHIP.0 R1, R15
    ABUNDANCE.1 R0, R0, @codegen_write_half_at
    CREA.1 R18, R18, #10
    CREA.1 R19, R19, #4
    GATHER.2 R19, R15
    GATHER.0 R18, R19
    PUSH_UP.1 R15, R15
    CREA.1 R0, R0, #6
    FELLOWSHIP.0 R1, R18
    ABUNDANCE.1 R0, R0, @codegen_write_half_at
    CREA.1 R18, R18, #10
    CREA.1 R19, R19, #0
write_offsets_loop:
    FELLOWSHIP.1 R19, R15
    BRANCH.5 @write_offsets_done
    CREA.1 R20, R20, #0x33400
    CREA.1 R21, R21, #4
    GATHER.2 R19, R21
    GATHER.0 R20, R19
    RECV.1 R21, R20
    FELLOWSHIP.0 R0, R18
    FELLOWSHIP.0 R1, R21
    ABUNDANCE.1 R0, R0, @codegen_write_word_at
    CREA.1 R18, R18, #4
    MICRO.1 R19, R19
    BRANCH.1 @write_offsets_loop
write_offsets_done:
    WELL.1 R15, R15
    RETURN.0 R0, R0

parse_at_keyword:
    ABUNDANCE.1 R0, R0, @codegen_next_token
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_at_done
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #2
    BRANCH.3 @parse_at_done
    PUSH_UP.1 R1, R1
    CREA.1 R0, R0, #0x33600
    FELLOWSHIP.0 R1, R1
    ABUNDANCE.1 R0, R0, @strcmp
    FELLOWSHIP.2 R0, R0, #0
    WELL.1 R1, R1
    BRANCH.3 @parse_at_check_locus
    ABUNDANCE.1 R0, R0, @parse_evolang
    BRANCH.1 @parse_at_done
parse_at_check_locus:
    PUSH_UP.1 R1, R1
    CREA.1 R0, R0, #0x33608
    ABUNDANCE.1 R0, R0, @strcmp
    FELLOWSHIP.2 R0, R0, #0
    WELL.1 R1, R1
    BRANCH.3 @parse_at_check_xiangci
    ABUNDANCE.1 R0, R0, @parse_locus
    BRANCH.1 @parse_at_done
parse_at_check_xiangci:
    PUSH_UP.1 R1, R1
    CREA.1 R0, R0, #0x3360E
    ABUNDANCE.1 R0, R0, @strcmp
    FELLOWSHIP.2 R0, R0, #0
    WELL.1 R1, R1
    BRANCH.3 @parse_at_check_meta
    ABUNDANCE.1 R0, R0, @parse_skip_rest
    BRANCH.1 @parse_at_done
parse_at_check_meta:
    PUSH_UP.1 R1, R1
    CREA.1 R0, R0, #0x33616
    ABUNDANCE.1 R0, R0, @strcmp
    FELLOWSHIP.2 R0, R0, #0
    WELL.1 R1, R1
    BRANCH.3 @parse_at_done
    ABUNDANCE.1 R0, R0, @parse_locus
    BRANCH.1 @parse_at_done
parse_at_done:
    RETURN.0 R0, R0

parse_evolang:
    ABUNDANCE.1 R0, R0, @codegen_next_token
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_evolang_done
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #4
    BRANCH.3 @parse_evolang_done
    ABUNDANCE.1 R0, R0, @codegen_next_token
parse_evolang_done:
    RETURN.0 R0, R0

parse_locus:
    ABUNDANCE.1 R0, R0, @codegen_next_token
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_locus_done
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #2
    BRANCH.3 @parse_locus_done
    ABUNDANCE.1 R0, R0, @codegen_next_token
    FELLOWSHIP.0 R16, R12
    GATHER.1 R16, R16, #0x11000
    GATHER.1 R16, R16, #64
    CREA.1 R20, R20, #0x33400
    CREA.1 R21, R21, #4
    GATHER.2 R21, R15
    GATHER.0 R20, R21
    ALLOC.1 R20, R16
    MICRO.1 R15, R15
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_locus_done
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #5
    BRANCH.3 @parse_locus_done
    FELLOWSHIP.2 R1, R1, #123
    BRANCH.3 @parse_locus_done
    ABUNDANCE.1 R0, R0, @codegen_next_token
    ABUNDANCE.1 R0, R0, @parse_locus_body
parse_locus_done:
    RETURN.0 R0, R0

parse_locus_body:
parse_locus_loop:
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_locus_body_done
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #5
    BRANCH.3 @parse_locus_check_ident
    FELLOWSHIP.2 R1, R1, #125
    BRANCH.2 @parse_locus_body_end
    BRANCH.1 @parse_locus_skip
parse_locus_check_ident:
    FELLOWSHIP.2 R0, R0, #2
    BRANCH.3 @parse_locus_check_modifier
    PUSH_UP.1 R1, R1
    CREA.1 R0, R0, #0x33621
    FELLOWSHIP.0 R1, R1
    ABUNDANCE.1 R0, R0, @strcmp
    FELLOWSHIP.2 R0, R0, #0
    WELL.1 R1, R1
    BRANCH.3 @parse_locus_skip_ident
    ABUNDANCE.1 R0, R0, @codegen_next_token
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_locus_body_done
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #5
    BRANCH.3 @parse_guaxu_block
    FELLOWSHIP.2 R1, R1, #58
    BRANCH.3 @parse_guaxu_block
    ABUNDANCE.1 R0, R0, @codegen_next_token
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_locus_body_done
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #5
    BRANCH.3 @parse_locus_body_done
    FELLOWSHIP.2 R1, R1, #123
    BRANCH.3 @parse_locus_body_done
    ABUNDANCE.1 R0, R0, @codegen_next_token
    ABUNDANCE.1 R0, R0, @parse_guaxu_block
    BRANCH.1 @parse_locus_loop
parse_locus_check_modifier:
    FELLOWSHIP.2 R0, R0, #6
    BRANCH.3 @parse_locus_skip
    ABUNDANCE.1 R0, R0, @codegen_next_token
    BRANCH.1 @parse_locus_loop
parse_locus_skip_ident:
    ABUNDANCE.1 R0, R0, @codegen_next_token
    BRANCH.1 @parse_locus_loop
parse_locus_skip:
    ABUNDANCE.1 R0, R0, @codegen_next_token
    BRANCH.1 @parse_locus_loop
parse_locus_body_end:
    ABUNDANCE.1 R0, R0, @codegen_next_token
parse_locus_body_done:
    RETURN.0 R0, R0

parse_guaxu_block:
parse_guaxu_loop:
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_guaxu_done
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #5
    BRANCH.3 @parse_guaxu_check_ident
    FELLOWSHIP.2 R1, R1, #125
    BRANCH.2 @parse_guaxu_end
    BRANCH.1 @parse_guaxu_skip
parse_guaxu_check_ident:
    FELLOWSHIP.2 R0, R0, #2
    BRANCH.3 @parse_guaxu_check_modifier
    PUSH_UP.1 R1, R1
    FELLOWSHIP.0 R0, R1
    ABUNDANCE.1 R0, R0, @lookup_mnemonic
    FELLOWSHIP.2 R0, R0, #4294967295
    BRANCH.3 @parse_guaxu_found_iching
    PUSH_UP.1 R1, R1
    FELLOWSHIP.0 R0, R1
    ABUNDANCE.1 R0, R0, @lookup_native
    FELLOWSHIP.2 R0, R0, #4294967295
    BRANCH.2 @parse_guaxu_skip_ident
    FELLOWSHIP.0 R17, R0
    ABUNDANCE.1 R0, R0, @codegen_next_token
    BRANCH.1 @parse_native_ops
parse_guaxu_found_iching:
    FELLOWSHIP.0 R17, R0
    ABUNDANCE.1 R0, R0, @codegen_next_token
    CREA.1 R18, R18, #0
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_guaxu_emit
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #6
    BRANCH.3 @parse_guaxu_parse_ops
    PUSH_UP.1 R1, R1
    FELLOWSHIP.0 R0, R1
    ABUNDANCE.1 R0, R0, @lookup_modifier
    FELLOWSHIP.0 R18, R0
    WELL.1 R1, R1
    ABUNDANCE.1 R0, R0, @codegen_next_token
parse_guaxu_parse_ops:
    CREA.1 R19, R19, #0
    CREA.1 R20, R20, #0
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_guaxu_emit
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #2
    BRANCH.3 @parse_guaxu_check_num1
    PUSH_UP.1 R1, R1
    FELLOWSHIP.0 R0, R1
    ABUNDANCE.1 R0, R0, @parse_register_name
    FELLOWSHIP.2 R0, R0, #4294967295
    WELL.1 R1, R1
    BRANCH.2 @parse_guaxu_emit_no_consume
    FELLOWSHIP.0 R19, R0
    ABUNDANCE.1 R0, R0, @codegen_next_token
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_guaxu_emit
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #5
    BRANCH.3 @parse_guaxu_emit_no_consume
    FELLOWSHIP.2 R1, R1, #44
    BRANCH.3 @parse_guaxu_emit_no_consume
    ABUNDANCE.1 R0, R0, @codegen_next_token
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_guaxu_emit
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #2
    BRANCH.3 @parse_guaxu_check_num2
    PUSH_UP.1 R1, R1
    FELLOWSHIP.0 R0, R1
    ABUNDANCE.1 R0, R0, @parse_register_name
    FELLOWSHIP.2 R0, R0, #4294967295
    WELL.1 R1, R1
    BRANCH.2 @parse_guaxu_emit_no_consume
    FELLOWSHIP.0 R20, R0
    ABUNDANCE.1 R0, R0, @codegen_next_token
    BRANCH.1 @parse_guaxu_emit
parse_guaxu_check_num1:
    FELLOWSHIP.2 R0, R0, #3
    BRANCH.3 @parse_guaxu_emit_no_consume
    FELLOWSHIP.0 R19, R1
    ABUNDANCE.1 R0, R0, @codegen_next_token
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_guaxu_emit
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #5
    BRANCH.3 @parse_guaxu_emit_no_consume
    FELLOWSHIP.2 R1, R1, #44
    BRANCH.3 @parse_guaxu_emit_no_consume
    ABUNDANCE.1 R0, R0, @codegen_next_token
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_guaxu_emit
    ABUNDANCE.1 R0, R0, @codegen_read_token
parse_guaxu_check_num2:
    FELLOWSHIP.2 R0, R0, #3
    BRANCH.3 @parse_guaxu_emit_no_consume
    FELLOWSHIP.0 R20, R1
    ABUNDANCE.1 R0, R0, @codegen_next_token
parse_guaxu_emit:
    FELLOWSHIP.0 R0, R17
    FELLOWSHIP.0 R1, R18
    FELLOWSHIP.0 R2, R19
    FELLOWSHIP.0 R3, R20
    ABUNDANCE.1 R0, R0, @codegen_emit_iching
    BRANCH.1 @parse_guaxu_loop
parse_guaxu_emit_no_consume:
    FELLOWSHIP.0 R0, R17
    FELLOWSHIP.0 R1, R18
    FELLOWSHIP.0 R2, R19
    FELLOWSHIP.0 R3, R20
    ABUNDANCE.1 R0, R0, @codegen_emit_iching
    BRANCH.1 @parse_guaxu_loop

parse_native_ops:
    CREA.1 R19, R19, #0
    CREA.1 R20, R20, #0
    CREA.1 R21, R21, #0
    CREA.1 R22, R22, #0
    FELLOWSHIP.2 R17, R17, #0
    BRANCH.2 @parse_native_emit
    FELLOWSHIP.2 R17, R17, #1
    BRANCH.2 @parse_native_emit
    FELLOWSHIP.2 R17, R17, #61
    BRANCH.2 @parse_native_emit
    FELLOWSHIP.2 R17, R17, #58
    BRANCH.2 @parse_native_emit
    FELLOWSHIP.2 R17, R17, #59
    BRANCH.2 @parse_native_emit
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_native_emit
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #2
    BRANCH.3 @parse_native_check_imm1
    PUSH_UP.1 R1, R1
    FELLOWSHIP.0 R0, R1
    ABUNDANCE.1 R0, R0, @parse_register_name
    FELLOWSHIP.2 R0, R0, #4294967295
    WELL.1 R1, R1
    BRANCH.2 @parse_native_emit_no_consume
    FELLOWSHIP.0 R19, R0
    ABUNDANCE.1 R0, R0, @codegen_next_token
    BRANCH.1 @parse_native_check_comma
parse_native_check_imm1:
    FELLOWSHIP.2 R0, R0, #3
    BRANCH.3 @parse_native_emit_no_consume
    FELLOWSHIP.0 R21, R1
    CREA.1 R22, R22, #1
    ABUNDANCE.1 R0, R0, @codegen_next_token
    BRANCH.1 @parse_native_emit
parse_native_check_comma:
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_native_emit
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #5
    BRANCH.3 @parse_native_emit_no_consume
    FELLOWSHIP.2 R1, R1, #44
    BRANCH.3 @parse_native_emit_no_consume
    ABUNDANCE.1 R0, R0, @codegen_next_token
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_native_emit
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #2
    BRANCH.3 @parse_native_check_imm2
    PUSH_UP.1 R1, R1
    FELLOWSHIP.0 R0, R1
    ABUNDANCE.1 R0, R0, @parse_register_name
    FELLOWSHIP.2 R0, R0, #4294967295
    WELL.1 R1, R1
    BRANCH.2 @parse_native_emit_no_consume
    FELLOWSHIP.0 R20, R0
    ABUNDANCE.1 R0, R0, @codegen_next_token
    BRANCH.1 @parse_native_emit
parse_native_check_imm2:
    FELLOWSHIP.2 R0, R0, #3
    BRANCH.3 @parse_native_emit_no_consume
    FELLOWSHIP.0 R21, R1
    CREA.1 R22, R22, #1
    ABUNDANCE.1 R0, R0, @codegen_next_token
parse_native_emit:
    FELLOWSHIP.0 R0, R17
    FELLOWSHIP.0 R1, R19
    FELLOWSHIP.0 R2, R20
    FELLOWSHIP.0 R3, R21
    FELLOWSHIP.0 R4, R22
    ABUNDANCE.1 R0, R0, @codegen_emit_native
    BRANCH.1 @parse_guaxu_loop
parse_native_emit_no_consume:
    FELLOWSHIP.0 R0, R17
    FELLOWSHIP.0 R1, R19
    FELLOWSHIP.0 R2, R20
    FELLOWSHIP.0 R3, R21
    FELLOWSHIP.0 R4, R22
    ABUNDANCE.1 R0, R0, @codegen_emit_native
    BRANCH.1 @parse_guaxu_loop
parse_guaxu_check_modifier:
    FELLOWSHIP.2 R0, R0, #6
    BRANCH.3 @parse_guaxu_skip
    ABUNDANCE.1 R0, R0, @codegen_next_token
    BRANCH.1 @parse_guaxu_loop
parse_guaxu_skip_ident:
    ABUNDANCE.1 R0, R0, @codegen_next_token
    BRANCH.1 @parse_guaxu_loop
parse_guaxu_skip:
    ABUNDANCE.1 R0, R0, @codegen_next_token
    BRANCH.1 @parse_guaxu_loop
parse_guaxu_end:
    ABUNDANCE.1 R0, R0, @codegen_next_token
parse_guaxu_done:
    RETURN.0 R0, R0

parse_skip_block:
    ABUNDANCE.1 R0, R0, @codegen_next_token
    CREA.1 R18, R18, #1
parse_skip_loop:
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_skip_done
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #5
    BRANCH.3 @parse_skip_next
    FELLOWSHIP.2 R1, R1, #123
    BRANCH.3 @parse_skip_check_close
    MICRO.1 R18, R18
    BRANCH.1 @parse_skip_next
parse_skip_check_close:
    FELLOWSHIP.2 R1, R1, #125
    BRANCH.3 @parse_skip_next
    GRADUAL.1 R18, R18
    FELLOWSHIP.2 R18, R18, #0
    BRANCH.2 @parse_skip_close
    BRANCH.1 @parse_skip_next
parse_skip_next:
    ABUNDANCE.1 R0, R0, @codegen_next_token
    BRANCH.1 @parse_skip_loop
parse_skip_close:
    ABUNDANCE.1 R0, R0, @codegen_next_token
parse_skip_done:
    RETURN.0 R0, R0

parse_skip_rest:
    ABUNDANCE.1 R0, R0, @codegen_next_token
parse_skip_rest_loop:
    ABUNDANCE.1 R0, R0, @codegen_has_tokens
    FELLOWSHIP.2 R0, R0, #0
    BRANCH.2 @parse_skip_rest_done
    ABUNDANCE.1 R0, R0, @codegen_read_token
    FELLOWSHIP.2 R0, R0, #5
    BRANCH.3 @parse_skip_rest_next
    FELLOWSHIP.2 R1, R1, #64
    BRANCH.2 @parse_skip_rest_done
parse_skip_rest_next:
    ABUNDANCE.1 R0, R0, @codegen_next_token
    BRANCH.1 @parse_skip_rest_loop
parse_skip_rest_done:
    RETURN.0 R0, R0
"""

MAIN_ASM = """
main:
    ABUNDANCE.1 R0, R0, @lexer_tokenize
    ABUNDANCE.1 R0, R0, @codegen_init
    ABUNDANCE.1 R0, R0, @parse_program
    FELLOWSHIP.0 R0, R12
    GATHER.1 R0, R0, #0x11000
    RETURN.1 R0, R0
"""

FULL_COMPILER_ASM = "BRANCH.1 @main\n" + STDLIB_ASM + LEXER_ASM + LOOKUP_ASM + CODEGEN_ASM + PARSER_ASM + MAIN_ASM


class IChingBootstrapCompiler:
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

    def _resolve_guaxu_labels(self, source: str):
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
        vm.run(max_cycles=10000000)

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


def test_all():
    print("=" * 60)
    print("易衍·Evomorph 纯IChing指令自举编译器 v3 测试")
    print("=" * 60)

    compiler = IChingBootstrapCompiler()

    print("\n[1] 完整编译测试")
    test_source = '@evolang "3.0"\n\n@locus test {\n    mut_rate = 0.01\n    fitness = min_latency\n    env_target = ["linux-6.x"]\n    max_generations = 50\n\n    GUAXU: {\n        CREA R0, R1\n        FELLOWSHIP R0, R1\n        SYNC\n    }\n}\n'
    result = compiler.compile_source(test_source)
    print(f"  编译成功: {result['success']}")
    print(f"  Token数量: {result['token_count']}")
    print(f"  基因座数量: {result.get('locus_count', 'N/A')}")
    print(f"  输出大小: {result['output_size']} 字节")
    print(f"  执行周期: {result['cycles']}")
    if result.get('evob_valid'):
        print(f"  EVOB头部正确!")
        print(f"  版本: {result.get('evob_version')}")
        print(f"  头部大小: {result.get('evob_header_size')}")
        print(f"  基因座数: {result.get('evob_locus_count')}")
        if 'instructions' in result:
            print(f"  指令数: {result.get('instruction_count')}")
            for instr in result['instructions']:
                mod_str = f" mod={instr['modifier']}" if instr['modifier'] else ""
                print(f"    {instr['mnemonic']} R{instr['op1']}, R{instr['op2']}{mod_str}")
    elif result['output_size'] > 0:
        print(f"  EVOB头部错误: {result['output_bytes'][:4]}")

    print("\n[2] 与传统CPU汇编编译器对比测试")
    try:
        from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler
        old_compiler = BootstrapCompiler()
        old_result = old_compiler.compile_source(test_source)
        print(f"  传统汇编编译器: success={old_result['success']}, tokens={old_result['token_count']}, loci={old_result.get('locus_count', 'N/A')}")
        print(f"  IChing编译器: success={result['success']}, tokens={result['token_count']}, loci={result.get('locus_count', 'N/A')}")
        if result.get('evob_valid') and old_result.get('evob_valid'):
            if result.get('evob_locus_count') == old_result.get('evob_locus_count'):
                print(f"  基因座数量一致!")
            else:
                print(f"  基因座数量不一致: IChing={result.get('evob_locus_count')}, 传统={old_result.get('evob_locus_count')}")
    except Exception as e:
        print(f"  传统编译器不可用: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_all()
