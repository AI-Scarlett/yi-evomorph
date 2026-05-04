#!/usr/bin/env python3
import sys
import os
import subprocess
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
print('易衍·Evomorph 编译器测试')
print('=' * 60)

print('\n[1/4] 编译 .evo 源码...')
compiler = EvocCompiler()
evb_data = compiler.compile(source, output_format='evb')
print(f'    EVB 大小: {len(evb_data)} bytes')

print('\n[2/4] 解析 EVB 头部...')
magic = evb_data[0:4]
version = struct.unpack(">H", evb_data[4:6])[0]
header_size = struct.unpack(">H", evb_data[6:8])[0]
num_loci = struct.unpack(">H", evb_data[8:10])[0]

print(f'    Magic: {magic}')
print(f'    Version: {version}')
print(f'    Header size: {header_size}')
print(f'    Num loci: {num_loci}')

raw_code = evb_data[header_size:]
print(f'\n[3/4] 提取原始字节码...')
print(f'    大小: {len(raw_code)} bytes')
print(f'    十六进制: {raw_code.hex()}')

raw_file = '/tmp/test_math.raw'
with open(raw_file, 'wb') as f:
    f.write(raw_code)
print(f'    已保存到: {raw_file}')

print('\n[4/4] 在 C 虚拟机上运行...')

asm_content = '''
ABOUND R0, 5
ABOUND R1, 10
INCREASE R0, R1
ABOUND R1, 20
ABOUND R2, 5
REDUCE R1, R2
ABOUND R2, 1
ABOUND R3, 3
SHL R2, R3
ABOUND R3, 16
ABOUND R4, 2
SHR R3, R4
ABOUND R4, 255
ABOUND R5, 15
AND R4, R5
ABOUND R5, 240
ABOUND R6, 15
OR R5, R6
ABOUND R6, 255
ABOUND R7, 15
XOR R6, R7
HALT
'''

asm_file = '/tmp/test_math.asm'
with open(asm_file, 'w') as f:
    f.write(asm_content)

print(f'    汇编文件: {asm_file}')

print('\n--- 使用 C 汇编器编译 ---')
result = subprocess.run(
    ['ichingvm', 'asm', asm_file, '/tmp/test_math.evb'],
    capture_output=True,
    text=True
)
print(f'输出: {result.stdout}')
if result.stderr:
    print(f'错误: {result.stderr}')

print('\n--- 在 C 虚拟机上运行 ---')
result = subprocess.run(
    ['ichingvm', 'run', '/tmp/test_math.evb'],
    capture_output=True,
    text=True
)
print(f'输出: {result.stdout}')
if result.stderr:
    print(f'错误: {result.stderr}')

print('\n' + '=' * 60)
print('测试完成')
print('=' * 60)
