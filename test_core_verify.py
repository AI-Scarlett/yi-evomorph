#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '.')

from evomorph.compiler import EvocCompiler
from evomorph.hexagrams import HexagramInstructionSet
import struct

print('=' * 60)
print('易衍·Evomorph 核心功能验证')
print('=' * 60)

print('\n[1] 验证指令集...')
isa = HexagramInstructionSet()

key_mnemonics = ['CREA', 'RECV', 'ABOUND', 'INCREASE', 'REDUCE', 'HALT']
for mnemonic in key_mnemonics:
    entry = isa.get_by_mnemonic(mnemonic)
    if entry:
        print(f'  {entry["symbol"]} {mnemonic:<12} opcode={entry["opcode"]:2} - {entry["binary"]}')
    else:
        print(f'  ✗ {mnemonic} 未找到')

print('\n[2] 验证编译器...')
test_source = '''
@evolang "3.0"

@locus simple_test {
    mut_rate = 0.01
    env_target = ["linux-6.x"]

    卦序: {
        ䷶ ABOUND R0, 5
        ䷶ ABOUND R1, 10
        ䷩ INCREASE R0, R1
        ䷋ HALT
    }
}
'''

compiler = EvocCompiler()
result = compiler.compile(test_source, output_format='dict')
print(f'  ✓ 编译成功')
print(f'  基因座数量: {len(result.get("loci", []))}')

locus_instr_count = 0
for locus in result.get('loci', []):
    print(f'\n  基因座: {locus.get("name")}')
    instrs = locus.get('instructions', [])
    locus_instr_count = len(instrs)
    for i, instr in enumerate(instrs):
        print(f'    [{i}] {instr.get("symbol")} {instr.get("mnemonic"):<12} '
              f'opcode={instr.get("opcode"):2} operands={instr.get("operands")}')

print('\n[3] 验证字节码编码...')
evb_data = compiler.compile(test_source, output_format='evb')
header_size = struct.unpack(">H", evb_data[6:8])[0]
raw_code = evb_data[header_size:]

print(f'  EVB 大小: {len(evb_data)} bytes')
print(f'  原始字节码: {len(raw_code)} bytes')
print(f'  十六进制: {raw_code.hex()}')

print('\n[4] 验证指令格式 (每条 4 字节)...')
expected_bytes = locus_instr_count * 4
print(f'  预期字节数: {expected_bytes}')
print(f'  实际字节数: {len(raw_code)}')
print(f'  匹配: {len(raw_code) == expected_bytes}')

print('\n[5] 逐指令解码验证...')
for i in range(0, len(raw_code), 4):
    if i + 4 <= len(raw_code):
        b1, b2, b3, b4 = raw_code[i:i+4]
        opcode = (b1 >> 2) & 0x3F
        modifier = ((b1 & 0x03) << 4) | b2
        
        entry = isa.get_by_opcode(opcode)
        if entry:
            symbol = entry['symbol']
            mnemonic = entry['mnemonic']
        else:
            symbol = '?'
            mnemonic = 'UNKNOWN'
        
        print(f'  [{i:2d}] {b1:02X} {b2:02X} {b3:02X} {b4:02X} -> '
              f'{symbol} {mnemonic:<12} '
              f'opcode={opcode:2}, op1={b3}, op2={b4}')

print('\n[6] 预期结果验证...')
expected = [
    ('ABOUND', 13, 0, 5,   'R0 = 5'),
    ('ABOUND', 13, 1, 10,  'R1 = 10'),
    ('INCREASE', 49, 0, 1, 'R0 = R0 + R1 = 15'),
    ('HALT', 56, 0, 0,     '停止'),
]

all_match = True
for i, (exp_mnemonic, exp_opcode, exp_op1, exp_op2, exp_desc) in enumerate(expected):
    if i * 4 + 4 <= len(raw_code):
        b1, b2, b3, b4 = raw_code[i*4:i*4+4]
        opcode = (b1 >> 2) & 0x3F
        
        match = (opcode == exp_opcode) and (b3 == exp_op1) and (b4 == exp_op2)
        status = '✓' if match else '✗'
        if not match:
            all_match = False
        
        entry = isa.get_by_opcode(opcode)
        actual_mnemonic = entry['mnemonic'] if entry else 'UNKNOWN'
        
        print(f'  {status} 指令 {i}: 预期 {exp_mnemonic}({exp_opcode}) op1={exp_op1}, op2={exp_op2}')
        print(f'         实际 {actual_mnemonic}({opcode}) op1={b3}, op2={b4}')

print('\n' + '=' * 60)
if all_match:
    print('✓ 所有验证通过!')
else:
    print('✗ 部分验证失败')
print('=' * 60)
