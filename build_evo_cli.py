#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, '/Users/zhouxiaoming/Downloads/evomorph')

from evomorph.compiler import EvocCompiler

evo_file = '/Users/zhouxiaoming/Downloads/evomorph/evomorph/bootstrap/evoc/evo_cli.evo'
asm_file = '/Users/zhouxiaoming/Downloads/evomorph/evomorph/bootstrap/evoc/evo_cli.asm'

print(f'编译: {evo_file}')

compiler = EvocCompiler()
result = compiler.compile_file(evo_file, output_format='dict')

if result.get('errors'):
    print('编译错误:')
    for err in result['errors']:
        print(f'  {err}')
    sys.exit(1)

loci = result.get('loci', [])
print(f'基因座数量: {len(loci)}')

asm_lines = [
    '; 易衍·Evomorph 编译输出',
    f'; 源文件: {evo_file}',
    f'; 基因座数量: {len(loci)}',
    '',
    'ABOUND R0, 0',
    'ABOUND R1, 0',
    'ABOUND R2, 0',
    'ABOUND R3, 0',
    'ABOUND R4, 0',
    'ABOUND R5, 0',
    'ABOUND R6, 0',
    'ABOUND R7, 0',
    'ABOUND R8, 0',
    'ABOUND R9, 0',
    'ABOUND R10, 0',
    'ABOUND R11, 0',
    'ABOUND R12, 0',
    'ABOUND R13, 65536',
    'ABOUND R14, 0',
    'ABOUND R15, 0',
    '',
]

def parse_register(value):
    if isinstance(value, str):
        if value.startswith('R') or value.startswith('r'):
            try:
                return int(value[1:])
            except ValueError:
                return 0
    elif isinstance(value, int):
        return value
    return 0

for locus in loci:
    locus_name = locus.get('name', 'unknown')
    instructions = locus.get('instructions', [])
    
    asm_lines.append(f'; --- {locus_name} ---')
    
    for instr in instructions:
        if 'error' in instr:
            asm_lines.append(f'; 错误: {instr["error"]}')
            continue
        
        mnemonic = instr.get('mnemonic', 'NOP')
        operands = instr.get('operands', [])
        
        op_strs = []
        for op in operands:
            if isinstance(op, dict):
                kind = op.get('kind', '')
                value = op.get('value', 0)
                
                if kind == 'register':
                    if isinstance(value, str) and (value.startswith('R') or value.startswith('r')):
                        op_strs.append(value.upper())
                    else:
                        op_strs.append(f'R{value}')
                elif kind == 'immediate':
                    op_strs.append(str(value))
                elif kind == 'env_ref':
                    env_val = hash(str(value)) & 0xFF
                    op_strs.append(str(env_val))
                elif kind == 'label':
                    op_strs.append(str(value))
                else:
                    op_strs.append(str(value))
            elif isinstance(op, int):
                if op <= 15:
                    op_strs.append(f'R{op}')
                else:
                    op_strs.append(str(op))
            else:
                op_strs.append(str(op))
        
        if op_strs:
            asm_line = f'{mnemonic} {", ".join(op_strs)}'
        else:
            asm_line = mnemonic
        
        asm_lines.append(asm_line)
    
    asm_lines.append('')

asm_lines.append('HALT')

with open(asm_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(asm_lines))

print(f'汇编文件已生成: {asm_file}')
print(f'总行数: {len(asm_lines)}')

print('\n=== 预览 ===')
for i, line in enumerate(asm_lines[:60]):
    print(f'{i+1:3}: {line}')
if len(asm_lines) > 60:
    print(f'... 还有 {len(asm_lines) - 60} 行')
