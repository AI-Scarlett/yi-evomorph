#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler

compiler = BootstrapCompiler()

source = '''@evolang "3.0"

@locus test {
    GUAXU: {
        MOVI R8, #4096
        MOVI R9, #0
loop:
        LDRB R11, R8
        CMPI R11, #0
        JE done
        INC R9
        INC R8
        JMP loop
done:
        MOV R0, R9
        RET
    }
}
'''

# 测试预处理
preprocessed = compiler._preprocess_source(source)
print("=== Preprocessed source ===")
for i, line in enumerate(preprocessed.split('\n')):
    print(f'  {i:3d}: {line}')

# 测试编译
result = compiler.compile_source(source)
print(f'\n=== Compilation result ===')
print(f'Success: {result["success"]}')
print(f'Output hex: {result.get("output_hex", "N/A")}')

if result.get('output_bytes'):
    evob = result['output_bytes']
    header_size = result.get('evob_header_size', 14)
    bytecode = evob[header_size:]
    print(f'\nBytecode ({len(bytecode)} bytes):')
    print(f'  Hex: {bytecode.hex()}')
