#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/zhouxiaoming/Downloads/evomorph')

from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler

bc = BootstrapCompiler()

print('=== 词法分析器测试 ===')
result = bc.test_lexer('@evolang "3.0"')
print(f'结果: {result}')

print('\n=== 完整编译测试 ===')
source = '@evolang "3.0"\n\n@locus test {\n    mut_rate = 0.02\n    fitness = min_latency\n    env_target = ["linux-6.x"]\n    max_generations = 50\n\n    卦序: {\n        ䷀ CREA R0, R1\n        ䷾ SYNC\n    }\n}\n'
result = bc.compile_source(source)
print(f'成功: {result["success"]}')
print(f'Token数: {result.get("token_count", "N/A")}')
print(f'输出大小: {result.get("output_size", "N/A")}')
print(f'执行周期: {result.get("cycles", "N/A")}')
if 'output_hex' in result:
    print(f'输出字节(前64): {result["output_hex"][:64]}')
    if result['output_bytes'][:4] == b'EVOB':
        print('✓ EVOB头部正确')
    else:
        print(f'✗ EVOB头部错误: {result["output_bytes"][:4]}')

print('\n=== 自举测试: 编译器编译自身 ===')
try:
    with open('/Users/zhouxiaoming/Downloads/evomorph/evomorph/bootstrap/native/bootstrap_compiler.py', 'r') as f:
        compiler_source = f.read()
    result2 = bc.compile_source(compiler_source)
    print(f'成功: {result2["success"]}')
    print(f'Token数: {result2.get("token_count", "N/A")}')
    print(f'输出大小: {result2.get("output_size", "N/A")}')
    print(f'执行周期: {result2.get("cycles", "N/A")}')
except Exception as e:
    print(f'错误: {e}')

print('\n=== 自举测试: 编译.evo源码 ===')
try:
    evo_source = '@evolang "3.0"\n\n@locus hello {\n    mut_rate = 0.01\n    fitness = min_latency\n    env_target = ["linux-6.x"]\n    max_generations = 100\n\n    卦序: {\n        ䷀ CREA R0, R1\n        ䷌ FELLOWSHIP R0, R1\n        ䷾ SYNC\n    }\n}\n'
    result3 = bc.compile_source(evo_source)
    print(f'成功: {result3["success"]}')
    print(f'Token数: {result3.get("token_count", "N/A")}')
    print(f'输出大小: {result3.get("output_size", "N/A")}')
    print(f'执行周期: {result3.get("cycles", "N/A")}')
    if 'output_bytes' in result3 and result3['output_bytes'][:4] == b'EVOB':
        print('✓ EVOB头部正确')
except Exception as e:
    print(f'错误: {e}')
