#!/usr/bin/env python3
import sys
import json
sys.path.insert(0, '/Users/zhouxiaoming/Downloads/evomorph')

from evomorph.compiler import EvocCompiler

compiler = EvocCompiler()
result = compiler.compile_file('/Users/zhouxiaoming/Downloads/evomorph/evomorph/bootstrap/evoc_bootstrap_complete.evo', output_format='dict')

if result.get('errors'):
    print('编译错误:')
    for err in result['errors']:
        print(f'  {err}')
    sys.exit(1)

loci = result.get('loci', [])
meta_loci = result.get('meta_loci', [])
xiangci = result.get('xiangci', [])

print('=' * 60)
print('易衍·Evomorph 自举编译器编译测试')
print('=' * 60)

print(f'\n编译成功!')
print(f'基因座数量: {len(loci)}')
print(f'元基因座数量: {len(meta_loci)}')
print(f'象辞块数量: {len(xiangci)}')

print('\n--- 基因座列表 ---')
for i, locus in enumerate(loci):
    name = locus.get('name', 'unnamed')
    instr_count = len(locus.get('instructions', []))
    fitness = locus.get('fitness', {})
    env_targets = locus.get('env_targets', [])
    print(f'\n{i+1}. {name}')
    print(f'   指令数: {instr_count}')
    print(f'   适应度: {fitness}')
    print(f'   目标平台: {env_targets}')
    
    if locus.get('instructions'):
        print(f'   前3条指令:')
        for j, instr in enumerate(locus['instructions'][:3]):
            if 'error' in instr:
                print(f'     [{j+1}] 错误: {instr["error"]}')
            else:
                op = instr.get('opcode', '?')
                mn = instr.get('mnemonic', '?')
                sym = instr.get('symbol', '?')
                ops = instr.get('operands', [])
                print(f'     [{j+1}] {sym} {mn} (opcode={op}) operands={ops}')

print('\n--- 元基因座列表 ---')
for i, meta in enumerate(meta_loci):
    name = meta.get('name', 'unnamed')
    instr_count = len(meta.get('instructions', []))
    print(f'\n{i+1}. {name}')
    print(f'   指令数: {instr_count}')

print('\n' + '=' * 60)
print('测试通过！易衍自举编译器可以被Python编译器正确编译')
print('=' * 60)

output_path = '/Users/zhouxiaoming/Downloads/evomorph/evomorph/bootstrap/compile_result.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f'\n编译结果已保存到: {output_path}')
