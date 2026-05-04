#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from evomorph.compiler import EvocCompiler
import struct

source = '''
@evolang "3.0"

@locus test_math {
    mut_rate = 0.01
    env_target = ["linux-6.x"]

    卦序: {
        ䷶ ABOUND R0, 5
        ䷶ ABOUND R1, 10
        ䷩ INCREASE R0, R1
        ䷶ ABOUND R1, 20
        ䷶ ABOUND R2, 5
        ䷨ REDUCE R1, R2
        ䷶ ABOUND R2, 1
        ䷶ ABOUND R3, 3
        ䷈ SHL R2, R3
        ䷶ ABOUND R3, 16
        ䷶ ABOUND R4, 2
        ䷊ SHR R3, R4
        ䷶ ABOUND R4, 255
        ䷶ ABOUND R5, 15
        ䷒ AND R4, R5
        ䷶ ABOUND R5, 240
        ䷶ ABOUND R6, 15
        ䷇ OR R5, R6
        ䷶ ABOUND R6, 255
        ䷶ ABOUND R7, 15
        ䷕ XOR R6, R7
        ䷋ HALT
    }
}
'''

print('=' * 60)
print('字节码编码验证')
print('=' * 60)

compiler = EvocCompiler()
evb_data = compiler.compile(source, output_format='evb')

header_size = struct.unpack(">H", evb_data[6:8])[0]
raw_code = evb_data[header_size:]

print(f'\n原始字节码 ({len(raw_code)} bytes):')
print(f'十六进制: {raw_code.hex()}')

print('\n--- 逐指令解码 ---')
from evomorph.compiler.codegen import CodeGenerator
codegen = CodeGenerator()
instructions = codegen.disassemble(raw_code)

print(f'\n反汇编结果 ({len(instructions)} 条指令):')
for i, instr in enumerate(instructions):
    print(f'  [{i:2d}] {instr["offset"]:08X}: {instr["mnemonic"]:<12} opcode={instr["opcode"]:2} operands={instr["operands"]}')

print('\n--- 预期的指令编码 ---')
print('''
指令格式: [byte1][byte2][byte3][byte4]
  byte1 = (opcode << 2) | ((modifier >> 4) & 0x03)
  byte2 = modifier & 0x0F
  byte3 = operand1 (寄存器索引 或 立即数低8位)
  byte4 = operand2 (寄存器索引 或 立即数低8位)

预期:
  ABOUND R0, 5    -> opcode=13, modifier=0, op1=0, op2=5
                  -> byte1=(13<<2)=52=0x34, byte2=0, byte3=0, byte4=5
                  -> 34 00 00 05
  ABOUND R1, 10   -> 34 00 01 0A
  INCREASE R0, R1 -> opcode=49, modifier=0, op1=0, op2=1
                  -> byte1=(49<<2)=196=0xC4, byte2=0, byte3=0, byte4=1
                  -> C4 00 00 01
  REDUCE R1, R2   -> opcode=50, byte1=(50<<2)=200=0xC8
                  -> C8 00 01 02
  SHL R2, R3      -> opcode=52, byte1=(52<<2)=208=0xD0
                  -> D0 00 02 03
  SHR R3, R4      -> opcode=53, byte1=(53<<2)=212=0xD4
                  -> D4 00 03 04
  AND R4, R5      -> opcode=54, byte1=(54<<2)=216=0xD8
                  -> D8 00 04 05
  OR R5, R6       -> opcode=55, byte1=(55<<2)=220=0xDC
                  -> DC 00 05 06
  XOR R6, R7      -> opcode=57, byte1=(57<<2)=228=0xE4
                  -> E4 00 06 07
  HALT            -> opcode=56, byte1=(56<<2)=224=0xE0
                  -> E0 00 00 00
''')

print('\n--- 实际字节码分解 ---')
for i in range(0, len(raw_code), 4):
    if i + 4 <= len(raw_code):
        instr_bytes = raw_code[i:i+4]
        byte1, byte2, byte3, byte4 = instr_bytes
        opcode = (byte1 >> 2) & 0x3F
        modifier = ((byte1 & 0x03) << 4) | byte2
        print(f'  [{i:3d}] {instr_bytes.hex()} -> opcode={opcode:2}, modifier={modifier}, op1={byte3}, op2={byte4}')

print('\n' + '=' * 60)
