#!/usr/bin/env python3
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM
)
from evomorph.vm.extended_vm2 import ExtendedIChingVM2, NativeOpcodes

NATIVE_NAMES = {v: k for k, v in [
    ('NOP', NativeOpcodes.NOP), ('HLT', NativeOpcodes.HLT),
    ('ADD', NativeOpcodes.ADD), ('SUB', NativeOpcodes.SUB),
    ('MUL', NativeOpcodes.MUL), ('DIV', NativeOpcodes.DIV),
    ('MOD', NativeOpcodes.MOD), ('INC', NativeOpcodes.INC),
    ('DEC', NativeOpcodes.DEC), ('NEG', NativeOpcodes.NEG),
    ('AND', NativeOpcodes.AND), ('OR', NativeOpcodes.OR),
    ('XOR', NativeOpcodes.XOR), ('NOT', NativeOpcodes.NOT),
    ('SHL', NativeOpcodes.SHL), ('SHR', NativeOpcodes.SHR),
    ('SAR', NativeOpcodes.SAR),
    ('CMP', NativeOpcodes.CMP), ('CMPI', NativeOpcodes.CMPI),
    ('TEST', NativeOpcodes.TEST),
    ('JMP', NativeOpcodes.JMP), ('JE', NativeOpcodes.JE),
    ('JNE', NativeOpcodes.JNE), ('JL', NativeOpcodes.JL),
    ('JLE', NativeOpcodes.JLE), ('JG', NativeOpcodes.JG),
    ('JGE', NativeOpcodes.JGE), ('JC', NativeOpcodes.JC),
    ('JNC', NativeOpcodes.JNC),
    ('MOV', NativeOpcodes.MOV), ('LEA', NativeOpcodes.LEA),
    ('XCHG', NativeOpcodes.XCHG), ('MOVI', NativeOpcodes.MOVI),
    ('LDR', NativeOpcodes.LDR), ('STR', NativeOpcodes.STR),
    ('LDRB', NativeOpcodes.LDRB), ('STRB', NativeOpcodes.STRB),
    ('PUSH', NativeOpcodes.PUSH), ('POP', NativeOpcodes.POP),
    ('PUSHA', NativeOpcodes.PUSHA), ('POPA', NativeOpcodes.POPA),
    ('CALL', NativeOpcodes.CALL), ('RET', NativeOpcodes.RET),
    ('INT', NativeOpcodes.INT), ('IRET', NativeOpcodes.IRET),
]}

def build_compiler_evo_source():
    asm_code = "JMP main\n" + STDLIB_ASM + LEXER_ASM + LOOKUP_ASM + CODEGEN_ASM + PARSER_ASM + MAIN_ASM
    guaxu_lines = []
    for line in asm_code.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith(';'):
            continue
        guaxu_lines.append('        ' + line)
    evo_source = '@evolang "3.0"\n\n@locus bootstrap_compiler {\n    GUAXU: {\n'
    evo_source += '\n'.join(guaxu_lines) + '\n    }\n}\n'
    return evo_source

compiler = BootstrapCompiler()
evo_source = build_compiler_evo_source()
result = compiler.compile_source(evo_source)

print(f"Compile success: {result['success']}")
print(f"EVOB valid: {result.get('evob_valid', False)}")
print(f"Bytecode: {result['output_size'] - 14} bytes")

if result.get('output_bytes'):
    evob = result['output_bytes']
    header_size = struct.unpack(">H", evob[6:8])[0]
    bytecode = evob[header_size:]
    
    # Decode first 20 instructions
    pos = 0
    count = 0
    while pos < len(bytecode) and count < 20:
        b1 = bytecode[pos]
        itype = (b1 >> 6) & 3
        if itype == 1:
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
            reg_dst = f'R{dst}' if dst < 29 else ['FP','SP','LR','R30'][dst-28]
            reg_src = f'R{src}' if src < 29 else ['FP','SP','LR','R30'][src-28]
            print(f'  {count:3d}: {mnem:6s} {reg_dst}, {reg_src}{imm_str}')
            count += 1
        elif itype == 2:
            opc = b1 & 0x3F
            mod = bytecode[pos+1]
            op1 = bytecode[pos+2]
            op2 = bytecode[pos+3]
            pos += 4
            ICHING = {0:'RECV',1:'RETURN',2:'BRANCH',17:'ALLOC',21:'SYNC',
                     23:'WAIT',34:'SPRT',36:'STILL',38:'MUT',39:'BARRIER',
                     46:'CAST',47:'ABUNDANCE',58:'LOCK',61:'FELLOWSHIP',62:'MATE',63:'CREA'}
            mnem = ICHING.get(opc, f'IChing_{opc}')
            print(f'  {count:3d}: {mnem:6s} mod={mod} R{op1}, R{op2}')
            count += 1
        else:
            print(f'  {count:3d}: UNKNOWN type={itype} byte={b1:#04x}')
            break

    # Try loading and running
    vm = ExtendedIChingVM2()
    ok = vm.load_evob(evob)
    print(f"\nEVOB load: {ok}")
    if ok:
        vm.run(max_cycles=100)
        print(f"VM state after 100 cycles: {vm.state}")
        print(f"PC: {vm.pc}")
