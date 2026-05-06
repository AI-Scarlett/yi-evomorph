#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM,
    INPUT_BUF, TOKEN_BUF, OUTPUT_BUF, HEADER_RESERVE
)
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

compiler = BootstrapCompiler()
vm = compiler.vm
compiler._load_mnemonic_table()
compiler._load_native_table()

# Test with a simple program that has native instructions
source = '@evolang "3.0"\n\n@locus test {\n    GUAXU: {\n        MOVI R0, #42\n        HLT\n    }\n}\n'
processed = compiler._preprocess_source(source)

# Load and run just the lexer
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
print(f"Token count: {token_count}")

# Dump tokens
type_names = {1:"KEYWORD", 2:"IDENT", 3:"NUMBER", 4:"STRING", 5:"SYMBOL", 6:"MODIFIER", 9:"NEWLINE"}
for i in range(min(token_count, 20)):
    addr = TOKEN_BUF + i * 8
    ttype = vm._load_word_heap(addr)
    tval = vm._load_word_heap(addr + 4)
    tname = type_names.get(ttype, f"?{ttype}")
    if ttype == 2:  # IDENT
        # Read string from the address
        s = vm.read_string(tval) if tval > 0 else ""
        print(f"  Token[{i}]: {tname} addr={tval:#x} str='{s}'")
    elif ttype == 3:  # NUMBER
        print(f"  Token[{i}]: {tname} value={tval}")
    elif ttype == 5:  # SYMBOL
        c = chr(tval) if 32 <= tval < 127 else str(tval)
        print(f"  Token[{i}]: {tname} '{c}'")
    else:
        print(f"  Token[{i}]: {tname} value={tval}")

# Now test lookup_native with the MOVI token's string address
# Find the MOVI token
for i in range(token_count):
    addr = TOKEN_BUF + i * 8
    ttype = vm._load_word_heap(addr)
    tval = vm._load_word_heap(addr + 4)
    if ttype == 2:
        s = vm.read_string(tval) if tval > 0 else ""
        if s == "MOVI":
            movi_addr = tval
            print(f"\nFound MOVI token at index {i}, string addr={movi_addr:#x}")
            
            # Test lookup_native with this address
            vm2 = ExtendedIChingVM2()
            compiler2 = BootstrapCompiler()
            compiler2.vm = vm2
            compiler2._load_mnemonic_table()
            compiler2._load_native_table()
            
            test_asm = """
JMP test_lookup

""" + STDLIB_ASM + LOOKUP_ASM + f"""

test_lookup:
    MOVI R0, #{movi_addr}
    CALL lookup_native
    HLT
"""
            vm2.load_assembled(test_asm)
            vm2.registers[29] = vm2.STACK_SIZE
            vm2.run(max_cycles=10000)
            print(f"lookup_native(lexer_MOVI): R0={vm2.registers[0]:#x} (expected 0x33)")
            break
