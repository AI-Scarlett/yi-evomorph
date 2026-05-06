#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler

compiler = BootstrapCompiler()

# Test lexer for MOVI instruction
source = 'MOVI R0, #10\nMOVI R1, #20\nADD R0, R1\nHLT'
result = compiler.test_lexer(source)
print(f'Lexer success: {result["success"]}')
print(f'Token count: {result["token_count"]}')
for t in result['tokens']:
    print(f'  {t["type"]} {t["value"]}')

# Test full compile
source2 = '@evolang "3.0"\n\n@locus compute {\n    GUAXU: {\n        MOVI R0, #10\n        MOVI R1, #20\n        ADD R0, R1\n        HLT\n    }\n}\n'
result2 = compiler.compile_source(source2)
print(f'\nCompile success: {result2["success"]}')
print(f'EVOB valid: {result2.get("evob_valid", False)}')
if result2.get('output_bytes'):
    evob = result2['output_bytes']
    header_size = result2.get('evob_header_size', 14)
    bytecode = evob[header_size:]
    print(f'Bytecode ({len(bytecode)} bytes): {bytecode.hex()}')
    # Decode
    pos = 0
    while pos < len(bytecode):
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
            if has_imm or opc in {0x19, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x33, 0x3C}:
                if pos + 3 < len(bytecode):
                    import struct
                    imm = struct.unpack('<I', bytecode[pos:pos+4])[0]
                    pos += 4
            mnem = {0x33:'MOVI',0x08:'ADD',0x01:'HLT'}.get(opc, f'?{opc:#x}')
            imm_str = f', #{imm}' if imm is not None else ''
            print(f'  {mnem} R{dst}, R{src}{imm_str} (has_imm={has_imm})')
        elif itype == 2:  # IChing
            opc = b1 & 0x3F
            mod = bytecode[pos+1]
            op1 = bytecode[pos+2]
            op2 = bytecode[pos+3]
            pos += 4
            print(f'  IChing opcode={opc} mod={mod} op1={op1} op2={op2}')
        else:
            print(f'  Unknown type={itype} byte={b1:#x}')
            break
