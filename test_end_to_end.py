#!/usr/bin/env python3
import sys
import os
import struct
import subprocess
sys.path.insert(0, '.')

from evomorph.compiler import EvocCompiler

print('=' * 70)
print('易衍·Evomorph 端到端测试')
print('=' * 70)

test_source = '''
@evolang "3.0"

@xiangci {
    "测试算术运算：加法、减法、位移、位运算"
}

@locus test_math {
    mut_rate   = 0.01
    fitness    = min_latency
    env_target = ["linux-6.x"]
    max_generations = 10

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

print('\n[步骤 1/5] 编译 .evo 源代码...')
print('-' * 70)

compiler = EvocCompiler()
evb_data = compiler.compile(test_source, output_format='evb')
print(f'✓ EVB 文件大小: {len(evb_data)} bytes')

print('\n[步骤 2/5] 解析 EVB 头部...')
print('-' * 70)

magic = evb_data[0:4]
version = struct.unpack(">H", evb_data[4:6])[0]
header_size = struct.unpack(">H", evb_data[6:8])[0]
num_loci = struct.unpack(">H", evb_data[8:10])[0]

print(f'  Magic:     {magic}')
print(f'  Version:   {version}')
print(f'  Header:    {header_size} bytes')
print(f'  Num loci:  {num_loci}')

print('\n[步骤 3/5] 提取原始字节码...')
print('-' * 70)

raw_code = evb_data[header_size:]
print(f'✓ 原始字节码大小: {len(raw_code)} bytes')
print(f'  十六进制: {raw_code.hex()}')

raw_file = '/tmp/evomorph_test.raw'
with open(raw_file, 'wb') as f:
    f.write(raw_code)
print(f'✓ 已保存到: {raw_file}')

print('\n[步骤 4/5] 验证字节码格式...')
print('-' * 70)

from evomorph.compiler.codegen import CodeGenerator
codegen = CodeGenerator()
instructions = codegen.disassemble(raw_code)

print(f'反汇编结果 ({len(instructions)} 条指令):')
for i, instr in enumerate(instructions):
    ops = [f"{op['value']}" for op in instr['operands']]
    print(f'  [{i:2d}] {instr["offset"]:08X}: {instr["mnemonic"]:<12} opcode={instr["opcode"]:2}  operands={", ".join(ops)}')

print('\n[步骤 5/5] 在 C 虚拟机上运行...')
print('-' * 70)

ichingvm_path = '/Users/zhouxiaoming/Downloads/evomorph/bootstrap/runtime/ichingvm'

result = subprocess.run(
    [ichingvm_path, 'run', raw_file, '1000'],
    capture_output=True,
    text=True
)

print(f'C 虚拟机输出:')
print(result.stdout)
if result.stderr:
    print(f'错误输出:')
    print(result.stderr)

if result.returncode == 0:
    print('✓ 测试通过!')
else:
    print(f'✗ 测试失败，返回码: {result.returncode}')

print('\n' + '=' * 70)
print('预期结果:')
print('  R0 = 15  (5 + 10)')
print('  R1 = 15  (20 - 5)')
print('  R2 = 8   (1 << 3)')
print('  R3 = 4   (16 >> 2)')
print('  R4 = 15  (255 & 15)')
print('  R5 = 255 (240 | 15)')
print('  R6 = 240 (255 ^ 15)')
print('=' * 70)
