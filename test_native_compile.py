#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler
from evomorph.vm.extended_vm2 import ExtendedIChingVM2, NativeOpcodes

compiler = BootstrapCompiler()

# 测试1: 混合IChing和Native指令
source1 = '''@evolang "3.0"

@locus mixed_test {
    GUAXU: {
        CREA R0, R1
        MOV R2, R0
        ADD R3, #4
        SYNC
        PUSH R4
        CALL 100
        POP R4
        RET
    }
}
'''
result = compiler.compile_source(source1)
print('=== Test 1: Mixed IChing + Native instructions ===')
print(f'Success: {result["success"]}')
print(f'Locus count: {result.get("evob_locus_count", "N/A")}')
print(f'Output size: {result["output_size"]} bytes')
if result.get('evob_valid'):
    print(f'EVOB valid: True')
    output_hex = result.get('output_hex', '')
    print(f'Output hex: {output_hex}')

# 验证输出可以在ExtendedIChingVM2上运行
if result.get('output_bytes'):
    vm = ExtendedIChingVM2()
    output = result['output_bytes']
    # 跳过EVOB头部，加载字节码
    header_size = result.get('evob_header_size', 14)
    bytecode = output[header_size:]
    vm.load_program(list(bytecode))
    vm.registers[29] = vm.STACK_SIZE
    vm.run(max_cycles=1000)
    print(f'VM execution: state={vm.state.name}, cycles={vm.cycle_count}')

# 测试2: 纯Native指令程序
source2 = '''@evolang "3.0"

@locus native_compute {
    GUAXU: {
        MOVI R0, #10
        MOVI R1, #20
        ADD R2, R0
        SUB R3, R1
        MUL R4, R0
        CMP R0, R1
        JE 100
        INC R0
        DEC R1
        RET
    }
}
'''
result2 = compiler.compile_source(source2)
print('\n=== Test 2: Pure Native instructions ===')
print(f'Success: {result2["success"]}')
print(f'Output size: {result2["output_size"]} bytes')
if result2.get('output_bytes'):
    output_hex = result2.get('output_hex', '')
    print(f'Output hex: {output_hex}')

# 测试3: 自举关键测试 - 编译一个简单的"编译器"程序
# 这个程序用Native指令实现了基本的字符串操作
source3 = '''@evolang "3.0"

@locus mini_compiler {
    GUAXU: {
        MOVI R8, #4096
        MOVI R9, #8192
        MOVI R10, #0
        MOVI R11, #24576
        LDRB R0, R8
        CMPI R0, #0
        JE 100
        INC R8
        JMP 20
        MOVI R0, #0
        STRB R9, R0
        RET
    }
}
'''
result3 = compiler.compile_source(source3)
print('\n=== Test 3: Mini-compiler program ===')
print(f'Success: {result3["success"]}')
print(f'Output size: {result3["output_size"]} bytes')
if result3.get('output_bytes'):
    vm2 = ExtendedIChingVM2()
    output3 = result3['output_bytes']
    header_size3 = result3.get('evob_header_size', 14)
    bytecode3 = output3[header_size3:]
    vm2.load_program(list(bytecode3))
    vm2.registers[29] = vm2.STACK_SIZE
    vm2.load_string(4096, "hello")
    vm2.run(max_cycles=5000)
    print(f'VM execution: state={vm2.state.name}, cycles={vm2.cycle_count}')
    print(f'R8={vm2.registers[8]}, R10={vm2.registers[10]}')

print('\n=== All native instruction tests completed ===')
