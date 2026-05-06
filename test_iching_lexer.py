#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState

vm = ExtendedIChingVM2()

# Just test the lexer part
test_asm = """
    BRANCH.1 @test_main

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
    BRANCH.6 @is_digit_yes
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
    BRANCH.6 @is_alpha_yes
is_alpha_no:
    CREA.1 R0, R0, #0
    RETURN.0 R0, R0
is_alpha_yes:
    CREA.1 R0, R0, #1
    RETURN.0 R0, R0

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

lexer_emit_token:
    PUSH_UP.1 R4, R4
    ALLOC.1 R9, R0
    CREA.1 R4, R4, #4
    GATHER.0 R9, R4
    ALLOC.1 R9, R1
    GATHER.0 R9, R4
    MICRO.1 R10, R10
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
    ABUNDANCE.1 R0, R0, @is_alpha
    FELLOWSHIP.2 R0, R0, #1
    BRANCH.2 @scan_id_cont
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @is_digit
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
    BRANCH.3 @tokenize_check_alpha
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @lexer_scan_identifier
    BRANCH.1 @tokenize_loop
tokenize_check_alpha:
    RECV.2 R5, R8
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @is_alpha
    FELLOWSHIP.2 R0, R0, #1
    BRANCH.3 @tokenize_check_symbol
    FELLOWSHIP.0 R0, R5
    ABUNDANCE.1 R0, R0, @lexer_scan_identifier
    BRANCH.1 @tokenize_loop
tokenize_check_symbol:
    RECV.2 R0, R8
    MICRO.1 R8, R8
    CREA.1 R0, R0, #5
    CREA.1 R1, R1, #0
    ABUNDANCE.1 R0, R0, @lexer_emit_token
    BRANCH.1 @tokenize_loop
tokenize_done:
    RETURN.0 R0, R0

test_main:
    CREA.1 R0, R0, #0x1000
    ABUNDANCE.1 R0, R0, @lexer_tokenize
    RETURN.1 R0, R0
"""

vm.load_assembled(test_asm)
vm.load_string(0x1000, '@evolang "3.0"')
vm.registers[29] = vm.STACK_SIZE

print(f"Program: {len(vm.program)} bytes")
print(f"State before: {vm.state}, PC={vm.pc}")

vm.run(max_cycles=5000)
print(f"State after: {vm.state}, PC={vm.pc}, cycles={vm.cycle_count}")
print(f"R0={vm.registers[0]}, R8=0x{vm.registers[8]:X}, R10={vm.registers[10]} (token count)")

# Check tokens
print("\nTokens:")
for i in range(min(vm.registers[10], 20)):
    token_addr = 0x9000 + i * 8
    token_val = vm._load_word_heap(token_addr)
    token_type = vm._load_word_heap(token_addr + 4)
    type_names = {1: "KEYWORD", 2: "IDENT", 3: "NUMBER", 4: "STRING", 5: "SYMBOL", 6: "MODIFIER", 9: "NEWLINE"}
    type_name = type_names.get(token_type, f"?{token_type}")
    print(f"  Token {i}: type={type_name}({token_type}) val=0x{token_val:X}")
