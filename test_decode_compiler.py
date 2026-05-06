#!/usr/bin/env python3
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM
)
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

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

evob = result['output_bytes']
header_size = struct.unpack(">H", evob[6:8])[0]
bytecode = evob[header_size:]

NATIVE_NAMES = {0x01:'HLT',0x02:'NOP',0x03:'ADD',0x04:'SUB',0x05:'MUL',0x06:'DIV',
              0x07:'MOD',0x08:'AND',0x09:'OR',0x0A:'XOR',0x0B:'NOT',
              0x0C:'SHL',0x0D:'SHR',0x0E:'SAR',0x0F:'CMP',0x10:'CMPI',
              0x12:'JMP',0x13:'JE',0x14:'JNE',0x15:'JL',0x16:'JLE',
              0x17:'JG',0x18:'JGE',0x1B:'MOV',0x1C:'MOVI',0x1D:'LEA',
              0x1F:'LDR',0x20:'STR',0x21:'LDRB',0x22:'STRB',
              0x23:'PUSH',0x24:'POP',0x25:'PUSHA',0x26:'POPA',
              0x27:'CALL',0x28:'RET',0x2B:'INC',0x2C:'DEC'}

# Decode first 30 instructions
pos = 0
count = 0
while pos < len(bytecode) and count < 30:
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
        mnem = NATIVE_NAMES.get(opc, f'?{opc:#x}')
        imm_str = f', #{imm}' if imm is not None else ''
        print(f'  {count:3d} @{pos-3 if imm is None else pos-7:4d}: {mnem} R{dst}, R{src}{imm_str}')
        count += 1
    elif itype == 2:  # IChing
        opc = b1 & 0x3F
        mod = bytecode[pos+1]
        op1 = bytecode[pos+2]
        op2 = bytecode[pos+3]
        pos += 4
        print(f'  {count:3d} @{pos-4:4d}: IChing_{opc} mod={mod} R{op1}, R{op2}')
        count += 1
    else:
        print(f'  {count:3d} @{pos:4d}: UNKNOWN type={itype} byte={b1:#04x}')
        break

# The first instruction should be JMP to main
# Let's check what the compiler actually generated
print(f"\nExpected first instruction: JMP main (MOVI R0, #0 + MOVI R1, #offset + ...)")
print(f"Actually got: bytecode[0:3] = {bytecode[0]:#04x} {bytecode[1]:#04x} {bytecode[2]:#04x}")
