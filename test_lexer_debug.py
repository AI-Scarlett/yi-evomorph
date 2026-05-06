#!/usr/bin/env python3
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler, NATIVE_MNEMONICS

compiler = BootstrapCompiler()

# 简化版词法分析器 - 只扫描标识符
simple_lexer = '''@evolang "3.0"

@locus simple {
    GUAXU: {
        MOVI R8, #4096
        MOVI R9, #0
        LDRB R0, R8
        CMPI R0, #0
        JE 100
        INC R9
        INC R8
        JMP 20
        MOV R0, R9
        RET
    }
}
'''

result = compiler.compile_source(simple_lexer)
print(f'Success: {result["success"]}')
print(f'Output size: {result["output_size"]}')
print(f'Output hex: {result.get("output_hex", "N/A")}')

if result.get('output_bytes'):
    evob = result['output_bytes']
    header_size = result.get('evob_header_size', 14)
    bytecode = evob[header_size:]
    print(f'\nBytecode ({len(bytecode)} bytes):')
    print(f'  Hex: {bytecode.hex()}')
    
    # 手动解码
    native_opc_map = {}
    for mname, opc in NATIVE_MNEMONICS:
        native_opc_map[opc] = mname
    
    pos = 0
    while pos < len(bytecode):
        b1 = bytecode[pos]
        itype = (b1 >> 6) & 0x03
        if itype == 0x02:  # IChing
            if pos + 3 < len(bytecode):
                opcode = b1 & 0x3F
                mod = bytecode[pos+1]
                op1 = bytecode[pos+2]
                op2 = bytecode[pos+3]
                print(f'  [{pos:3d}] IChing: opcode={opcode} mod={mod} op1=R{op1} op2=R{op2}')
                pos += 4
            else:
                print(f'  [{pos:3d}] Incomplete IChing')
                break
        elif itype == 0x01:  # Native
            if pos + 2 < len(bytecode):
                native_opc = b1 & 0x3F
                byte2 = bytecode[pos+1]
                byte3 = bytecode[pos+2]
                dst = byte2 & 0x1F
                has_imm = bool(byte2 & 0x20)
                src = byte3 & 0x1F
                mnem = native_opc_map.get(native_opc, f"N?{native_opc}")
                imm_str = ""
                pos += 3
                # Check if instruction needs immediate
                needs_imm = has_imm or native_opc in {0x19, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x33, 0x3C}
                if needs_imm and pos + 3 < len(bytecode):
                    imm = struct.unpack('<I', bytecode[pos:pos+4])[0]
                    imm_str = f" imm={imm} (0x{imm:x})"
                    pos += 4
                print(f'  [{pos-3-len(imm_str)//2:3d}] Native: {mnem} R{dst}, R{src}{imm_str}')
            else:
                print(f'  [{pos:3d}] Incomplete Native')
                break
        else:
            print(f'  [{pos:3d}] Unknown type {itype}: 0x{b1:02x}')
            break

# 测试词法分析器
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
vm = ExtendedIChingVM2()
vm.load_program(list(bytecode))
vm.registers[29] = vm.STACK_SIZE
vm.load_string(0x1000, "ABC")
print(f'\nVM execution:')
vm.run(max_cycles=1000)
print(f'  State: {vm.state.name}')
print(f'  Cycles: {vm.cycle_count}')
print(f'  R0={vm.registers[0]} R8={vm.registers[8]} R9={vm.registers[9]}')
