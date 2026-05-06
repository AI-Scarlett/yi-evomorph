#!/usr/bin/env python3
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM
)

def build_compiler_evo_source():
    asm_code = "JMP main\n" + STDLIB_ASM + LEXER_ASM + LOOKUP_ASM + CODEGEN_ASM + PARSER_ASM + MAIN_ASM
    guaxu_lines = []
    for line in asm_code.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith(';'):
            continue
        guaxu_lines.append('        ' + line)
    
    evo_source = '@evolang "3.0"\n\n'
    evo_source += '@locus bootstrap_compiler {\n'
    evo_source += '    GUAXU: {\n'
    evo_source += '\n'.join(guaxu_lines) + '\n'
    evo_source += '    }\n'
    evo_source += '}\n'
    return evo_source

compiler = BootstrapCompiler()
evo_source = build_compiler_evo_source()

result = compiler.compile_source(evo_source)
evob = result.get('output_bytes', b'')
print(f"EVOB length: {len(evob)}")
print(f"First 20 bytes hex: {evob[:20].hex()}")
print(f"Magic: {evob[:4]}")

# Check if it starts with EVOB
if evob[:4] != b'EVOB':
    print("NOT EVOB! Checking raw output...")
    # The compile_source method might return different format
    # Check what's in the output
    print(f"Output hex: {evob.hex()[:200]}")
else:
    version = struct.unpack(">H", evob[4:6])[0]
    header_size = struct.unpack(">H", evob[6:8])[0]
    locus_count = struct.unpack(">H", evob[8:10])[0]
    print(f"Version: {version}")
    print(f"Header size: {header_size}")
    print(f"Locus count: {locus_count}")
    
    bytecode = evob[header_size:]
    print(f"Bytecode length: {len(bytecode)}")
    print(f"Bytecode first 40 bytes: {bytecode[:40].hex()}")
    
    # Try decoding
    pos = 0
    count = 0
    while pos < len(bytecode) and count < 15:
        b1 = bytecode[pos]
        itype = (b1 >> 6) & 3
        if itype == 1:  # Native
            opc = b1 & 0x3F
            b2 = bytecode[pos+1]
            b3 = bytecode[pos+2]
            dst = b2 & 0x1F
            has_imm = bool(b2 & 0x20)
            src = b3 & 0x1F
            pos += 3
            imm = None
            if has_imm:
                if pos + 3 < len(bytecode):
                    imm = struct.unpack('<I', bytecode[pos:pos+4])[0]
                    pos += 4
            NATIVE_NAMES = {0x01:'HLT',0x03:'ADD',0x04:'SUB',0x05:'MUL',0x06:'DIV',
                          0x07:'MOD',0x08:'AND',0x09:'OR',0x0A:'XOR',0x0B:'NOT',
                          0x0C:'SHL',0x0D:'SHR',0x0E:'SAR',0x0F:'CMP',0x10:'CMPI',
                          0x12:'JMP',0x13:'JE',0x14:'JNE',0x15:'JL',0x16:'JLE',
                          0x17:'JG',0x18:'JGE',0x1B:'MOV',0x1C:'MOVI',0x1D:'LEA',
                          0x1F:'LDR',0x20:'STR',0x21:'LDRB',0x22:'STRB',
                          0x23:'PUSH',0x24:'POP',0x25:'PUSHA',0x26:'POPA',
                          0x27:'CALL',0x28:'RET',0x2B:'INC',0x2C:'DEC'}
            mnem = NATIVE_NAMES.get(opc, f'?{opc:#x}')
            imm_str = f', #{imm}' if imm is not None else ''
            print(f'  {mnem} R{dst}, R{src}{imm_str} (has_imm={has_imm})')
            count += 1
        elif itype == 2:  # IChing
            opc = b1 & 0x3F
            pos += 4
            print(f'  IChing opcode={opc}')
            count += 1
        else:
            print(f'  UNKNOWN type={itype} byte={b1:#04x}')
            break
