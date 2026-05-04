#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from evomorph.compiler import EvocCompiler

source = '''
@evolang "3.0"

@locus test {
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

print('=== 测试完整编译 ===')
compiler = EvocCompiler()
result = compiler.compile(source, output_format='dict')

print(f'基因座数量: {len(result.get("loci", []))}')
for locus in result.get('loci', []):
    print(f'\n基因座: {locus.get("name")}')
    print(f'指令数量: {len(locus.get("instructions", []))}')
    for i, instr in enumerate(locus.get('instructions', [])):
        print(f'  [{i}] {instr.get("symbol")} {instr.get("mnemonic")} opcode={instr.get("opcode")}')
        print(f'      操作数: {instr.get("operands")}')
        print(f'      字节码偏移: {instr.get("offset")}')

print('\n=== 测试 EVB 格式 ===')
evb_data = compiler.compile(source, output_format='evb')
print(f'EVB 大小: {len(evb_data)} bytes')
print(f'十六进制: {evb_data.hex()}')

import struct
from evomorph.compiler.codegen import CodeGenerator
codegen = CodeGenerator()

# 解析 EVB 头部
magic = evb_data[0:4]
version = struct.unpack(">H", evb_data[4:6])[0]
header_size = struct.unpack(">H", evb_data[6:8])[0]
num_loci = struct.unpack(">H", evb_data[8:10])[0]

print(f'\nEVB Header:')
print(f'  magic: {magic}')
print(f'  version: {version}')
print(f'  header_size: {header_size}')
print(f'  num_loci: {num_loci}')

raw_code = evb_data[header_size:]
print(f'\n原始字节码大小: {len(raw_code)} bytes')
print(f'原始字节码十六进制: {raw_code.hex()}')

instructions = codegen.disassemble(raw_code)
print('\n=== 反汇编 ===')
for instr in instructions:
    print(f'{instr["offset"]:08X}: {instr["mnemonic"]:<12} opcode={instr["opcode"]:2} operands={instr["operands"]}')

print('\n=== 预期结果 ===')
print('ABOUND R0, 5  -> 0x34 0x00 0x00 0x05')
print('ABOUND R1, 10 -> 0x34 0x00 0x01 0x0A')
print('INCREASE R0, R1 -> 操作码 49 (0x31)')
