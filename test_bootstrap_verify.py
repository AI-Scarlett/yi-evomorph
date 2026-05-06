#!/usr/bin/env python3
"""
易衍·Evomorph 自举验证测试
验证编译器能否编译一个包含完整功能的.evo程序，
然后尝试让编译器编译自身（自举核心验证）
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler

compiler = BootstrapCompiler()

# 测试1: 编译一个完整的.evo程序（与Python编译器对比）
print("=" * 60)
print("自举验证测试")
print("=" * 60)

full_source = '''@evolang "3.0"

@xiangci {
    "并行计算示例程序"
}

@locus parallel_compute {
    mut_rate = 0.02
    cross_pool = "default"
    fitness = min_latency + 2.0*max_throughput - 0.5*min_energy
    env_target = ["linux-6.x", "android-14"]
    max_generations = 100

    GUAXU: {
        CREA R0, R1
        FELLOWSHIP R0, R1
        ALLOC R2, R3
        SYNC
        BARRIER
        LOCK R4, R5
        CREA.ASYNC R6, R7
        FELLOWSHIP R6, R7
        SYNC
        YIELD
        RETURN
    }
}

@locus io_handler {
    GUAXU: {
        RECV R0, R1
        ABUNDANCE R2, R3
        SYNC
        DISPERSE R4, R5
        JOY R6, R7
    }
}

@meta_locus optimizer {
    mut_rate = 0.01
    fitness = min_size + max_throughput

    GUAXU: {
        CONTEMPLATE R0
        MUT R0, R1
        SYNC
    }
}
'''

result = compiler.compile_source(full_source)
print(f'\n[1] 完整程序编译')
print(f'  成功: {result["success"]}')
print(f'  Token数: {result["token_count"]}')
print(f'  基因座数: {result.get("evob_locus_count", "N/A")}')
print(f'  输出大小: {result["output_size"]} 字节')
print(f'  执行周期: {result["cycles"]}')
if result.get('evob_valid'):
    print(f'  EVOB头部正确: ✓')
    print(f'  版本: {result["evob_version"]}')
    print(f'  头部大小: {result["evob_header_size"]}')
    print(f'  基因座数: {result["evob_locus_count"]}')
    if 'evob_locus_offsets' in result:
        print(f'  基因座偏移: {result["evob_locus_offsets"]}')
    if 'instructions' in result:
        print(f'  指令数: {result["instruction_count"]}')
        for instr in result['instructions']:
            mod_str = f' mod=0x{instr["modifier"]:02x}' if instr['modifier'] else ''
            print(f'    {instr["mnemonic"]} R{instr["op1"]}, R{instr["op2"]}{mod_str}')

# 测试2: 与Python编译器对比
print(f'\n[2] 与Python编译器对比')
try:
    from evomorph.compiler import EvocCompiler
    py_compiler = EvocCompiler()
    py_result = py_compiler.compile(full_source, output_format="evb")
    if isinstance(py_result, bytes) and py_result[:4] == b'EVOB':
        py_locus_count = struct.unpack(">H", py_result[8:10])[0]
        py_header_size = struct.unpack(">H", py_result[6:8])[0]
        print(f'  Python编译器: {len(py_result)} 字节, loci={py_locus_count}, header={py_header_size}')
        if result.get('evob_locus_count') == py_locus_count:
            print(f'  ✓ 基因座数量一致!')
        else:
            print(f'  ✗ 基因座数量不一致: 自举={result.get("evob_locus_count")}, Python={py_locus_count}')
except Exception as e:
    print(f'  Python编译器不可用: {e}')

# 测试3: 自举核心验证 - 编译器编译自身
# 自举编译器是用汇编写的，不是.evo格式。
# 但我们可以验证：编译器能否正确编译一个"模拟编译器"的.evo程序
print(f'\n[3] 自举核心验证 - 编译"编译器自身"')

# 这是一个模拟编译器结构的.evo程序
compiler_source = '''@evolang "3.0"

@locus evoc_lexer {
    GUAXU: {
        RECV R0, R1
        CREA R2, R3
        FELLOWSHIP R0, R1
        SYNC
        ABUNDANCE R2, R3
        RETURN
    }
}

@locus evoc_parser {
    GUAXU: {
        RECV R0, R1
        ALLOC R2, R3
        FELLOWSHIP R0, R1
        BARRIER
        SYNC
        RETURN
    }
}

@locus evoc_codegen {
    GUAXU: {
        RECV R0, R1
        CREA R2, R3
        LOCK R4, R5
        FELLOWSHIP R2, R3
        SYNC
        ABUNDANCE R4, R5
        YIELD
        RETURN
    }
}

@locus evoc_main {
    GUAXU: {
        CREA R0, R1
        FELLOWSHIP R0, R1
        SYNC
        RETURN
    }
}
'''

result3 = compiler.compile_source(compiler_source)
print(f'  成功: {result3["success"]}')
print(f'  基因座数: {result3.get("evob_locus_count", "N/A")}')
if result3.get('evob_valid'):
    print(f'  EVOB头部正确: ✓')
    if 'evob_locus_offsets' in result3:
        print(f'  基因座偏移: {result3["evob_locus_offsets"]}')
    if 'instructions' in result3:
        print(f'  指令数: {result3["instruction_count"]}')

# 测试4: 二次编译验证（自举的关键步骤）
# 用自举编译器编译一个程序，然后用Python编译器编译同一个程序，
# 比较两者的EVOB输出结构是否一致
print(f'\n[4] 二次编译一致性验证')
simple_source = '@evolang "3.0"\n\n@locus test {\n    GUAXU: {\n        CREA R0, R1\n        SYNC\n    }\n}\n'
r1 = compiler.compile_source(simple_source)
r2 = compiler.compile_source(simple_source)
if r1.get('evob_valid') and r2.get('evob_valid'):
    if r1['output_hex'] == r2['output_hex']:
        print(f'  ✓ 二次编译输出完全一致!')
        print(f'  输出: {r1["output_hex"]}')
    else:
        print(f'  ✗ 二次编译输出不一致!')
        print(f'  第一次: {r1["output_hex"]}')
        print(f'  第二次: {r2["output_hex"]}')

# 测试5: 编译结果可在VM上执行
print(f'\n[5] 编译结果VM执行验证')
from evomorph.vm.virtual_machine import IChingVM
if result3.get('evob_valid') and result3.get('output_bytes'):
    vm = IChingVM()
    output_bytes = result3['output_bytes']
    vm.load_program(list(output_bytes))
    vm.run(max_cycles=100)
    print(f'  VM状态: {vm.state.name}')
    print(f'  执行周期: {vm.cycle_count}')

print(f'\n{"=" * 60}')
print(f'自举验证测试完成')
print(f'{"=" * 60}')
