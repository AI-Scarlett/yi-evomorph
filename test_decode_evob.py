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
print(f"EVOB valid: {result.get('evob_valid', False)}")
print(f"Output size: {result['output_size']}")
print(f"Cycles: {result['cycles']}")

if result.get('output_bytes'):
    evob = result['output_bytes']
    if evob[:4] == b'EVOB':
        header_size = struct.unpack(">H", evob[6:8])[0]
        locus_count = struct.unpack(">H", evob[8:10])[0]
        bytecode = evob[header_size:]
        print(f"Header size: {header_size}, Locus count: {locus_count}")
        print(f"Bytecode: {len(bytecode)} bytes")
        
        # Decode first 20 instructions
        pos = 0
        count = 0
        while pos < len(bytecode) and count < 20:
            b1 = bytecode[pos]
            itype = (b1 >> 6) & 3
            if itype == 1:  # Native
                opc = b1 & 0x3F
                b2 = bytecode[pos+1] if pos+1 < len(bytecode) else 0
                b3 = bytecode[pos+2] if pos+2 < len(bytecode) else 0
                dst = b2 & 0x1F
                has_imm = bool(b2 & 0x20)
                src = b3 & 0x1F
                pos += 3
                imm = None
                if has_imm or opc in {0x19, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x33, 0x3C}:
                    if pos + 3 < len(bytecode):
                        imm = struct.unpack('<I', bytecode[pos:pos+4])[0]
                        pos += 4
                NATIVE_NAMES = {
                    0x01:'HLT', 0x02:'NOP', 0x03:'ADD', 0x04:'SUB', 0x05:'MUL', 0x06:'DIV',
                    0x07:'MOD', 0x08:'AND', 0x09:'OR', 0x0A:'XOR', 0x0B:'NOT', 0x0C:'SHL',
                    0x0D:'SHR', 0x0E:'SAR', 0x0F:'CMP', 0x10:'CMPI', 0x11:'TEST',
                    0x12:'JMP', 0x13:'JE', 0x14:'JNE', 0x15:'JL', 0x16:'JLE',
                    0x17:'JG', 0x18:'JGE', 0x19:'JC', 0x1A:'JNC',
                    0x1B:'MOV', 0x1C:'MOVI', 0x1D:'LEA', 0x1E:'XCHG',
                    0x1F:'LDR', 0x20:'STR', 0x21:'LDRB', 0x22:'STRB',
                    0x23:'PUSH', 0x24:'POP', 0x25:'PUSHA', 0x26:'POPA',
                    0x27:'CALL', 0x28:'RET', 0x29:'INT', 0x2A:'IRET',
                    0x2B:'INC', 0x2C:'DEC',
                }
                mnem = NATIVE_NAMES.get(opc, f'?{opc:#x}')
                imm_str = f', #{imm}' if imm is not None else ''
                print(f'  {pos:4d}: {mnem} R{dst}, R{src}{imm_str}')
                count += 1
            elif itype == 2:  # IChing
                opc = b1 & 0x3F
                mod = bytecode[pos+1] if pos+1 < len(bytecode) else 0
                op1 = bytecode[pos+2] if pos+2 < len(bytecode) else 0
                op2 = bytecode[pos+3] if pos+3 < len(bytecode) else 0
                pos += 4
                ICHING_NAMES = {
                    0:'RECV', 1:'RETURN', 2:'BRANCH', 17:'ALLOC', 21:'SYNC',
                    23:'WAIT', 34:'SPRT', 36:'STILL', 38:'MUT', 39:'BARRIER',
                    46:'CAST', 47:'ABUNDANCE', 58:'LOCK', 61:'FELLOWSHIP', 62:'MATE', 63:'CREA'
                }
                mnem = ICHING_NAMES.get(opc, f'IChing_{opc}')
                print(f'  {pos:4d}: {mnem} mod={mod} R{op1}, R{op2}')
                count += 1
            else:
                print(f'  {pos:4d}: UNKNOWN byte={b1:#04x} type={itype}')
                break
