#!/usr/bin/env python3
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler, INPUT_BUF, TOKEN_BUF, OUTPUT_BUF, HEADER_RESERVE, STDLIB_ASM, LEXER_ASM

compiler = BootstrapCompiler()
vm = compiler.vm

source = '@evolang "3.0"\n\n@locus test {\n    GUAXU: {\n        MOVI R0, #42\n    }\n}\n'
processed = compiler._preprocess_source(source)

# Load and run just the lexer
compiler._load_mnemonic_table()
compiler._load_native_table()
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

print(f'Lexer done. State={vm.state}, Tokens={vm.registers[10]}')
token_count = vm.registers[10]

# Dump token buffer
type_names = {1:"KEYWORD", 2:"IDENT", 3:"NUMBER", 4:"STRING", 5:"SYMBOL", 6:"MODIFIER", 9:"NEWLINE"}
for i in range(min(token_count, 30)):
    addr = TOKEN_BUF + i * 8
    ttype = vm._load_word_heap(addr)
    tval = vm._load_word_heap(addr + 4)
    tname = type_names.get(ttype, f"?{ttype}")
    if ttype == 3:
        val_str = str(tval)
    elif ttype == 5:
        val_str = chr(tval) if 32 <= tval < 127 else str(tval)
    elif ttype in (2, 4, 6):
        val_str = vm.read_string(tval) if tval > 0 else ""
    else:
        val_str = str(tval)
    print(f'  Token[{i}]: type={tname}({ttype}) value={val_str}({tval})')

# Now run the full compiler
compiler2 = BootstrapCompiler()
result = compiler2.compile_source(source)
print(f'\nFull compile: success={result["success"]}')
if result.get('output_bytes'):
    evob = result['output_bytes']
    hs = result.get('evob_header_size', 14)
    bc = evob[hs:]
    print(f'Bytecode ({len(bc)} bytes): {bc.hex()}')
    # Expected: 73 20 00 2a 00 00 00 (7 bytes for MOVI R0, #42)
    if len(bc) >= 3:
        b1, b2, b3 = bc[0], bc[1], bc[2]
        print(f'  byte1={b1:#04x} (type={(b1>>6)&3}, opc={b1&0x3f:#04x})')
        print(f'  byte2={b2:#04x} (dst={b2&0x1f}, has_imm={bool(b2&0x20)})')
        print(f'  byte3={b3:#04x} (src={b3&0x1f})')
