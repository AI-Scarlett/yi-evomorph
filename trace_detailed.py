#!/usr/bin/env python3
"""详细追踪 EVB 汇编器 - 映射函数地址"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from build_assembler import (
    build_opcode_table, load_assembler_source,
    INPUT_BUF, OUTPUT_BUF, LABEL_TABLE, OPCODE_TABLE
)

# First, let's assemble and find function addresses
src = load_assembler_source()
vm = ExtendedIChingVM2()

# Build opcode table
opcode_table = build_opcode_table()
for i, b in enumerate(opcode_table):
    vm.heap[OPCODE_TABLE + i] = b

# Use Python assembler to get bytecode and label addresses
evob = vm.assemble(src)

# Print label addresses
print("Function addresses from Python assembler:")
for name, addr in sorted(vm.labels.items()):
    print(f"  {addr:5d}: {name}")

print(f"\nBytecode size: {len(evob)} bytes")
print("=" * 70)

# Now trace with these addresses
vm2 = ExtendedIChingVM2()
for i, b in enumerate(opcode_table):
    vm2.heap[OPCODE_TABLE + i] = b

vm2.program = bytearray(evob)
vm2.pc = 0

# Simple test
test = 'CREA.1 R0, R0, #42\n'
src_bytes = test.encode('ascii') + b'\x00'
for i, b in enumerate(src_bytes):
    vm2.heap[INPUT_BUF + i] = b
for i in range(LABEL_TABLE, LABEL_TABLE + 0x4000):
    vm2.heap[i] = 0

vm2.registers[0] = INPUT_BUF
vm2.registers[29] = vm2.STACK_SIZE

# Map function addresses for display
func_map = {addr: name for name, addr in vm.labels.items()}

# Detailed step trace
trace_steps = []
orig_step = vm2._step

MAX_TRACE = 200

def instrumented_step():
    pc = vm2.pc
    if pc < len(vm2.program) and len(trace_steps) < MAX_TRACE:
        b1 = vm2.program[pc]
        instr_type = (b1 >> 6) & 0x03
        if instr_type == 0x02 and pc + 3 < len(vm2.program):
            opcode = b1 & 0x3F
            mod = vm2.program[pc + 1]
            sub = mod & 0x3F
            em = (mod >> 6) & 3
            d_raw = vm2.program[pc + 2]
            s_raw = vm2.program[pc + 3]
            
            func_name = func_map.get(pc, '')
            if not func_name:
                for addr, name in sorted(func_map.items()):
                    if pc >= addr:
                        func_name = name
                    else:
                        break
            
            extra = ''
            if em >= 2 and pc + 7 < len(vm2.program):
                imm = struct.unpack('<I', bytes(vm2.program[pc+4:pc+8]))[0]
                if imm in func_map:
                    extra = f' @{func_map[imm]}'
                else:
                    extra = f' #{imm}'
            
            r0 = vm2.registers[0]
            r10 = vm2.registers[10]
            r8 = vm2.registers[8]
            sp = vm2.registers[29]
            
            is_call = (opcode == 47 and sub == 1)
            is_ret = (opcode == 1 and sub == 0)
            
            mark = 'CALL' if is_call else ('RET ' if is_ret else '    ')
            trace_steps.append(
                f'[{len(trace_steps):4d}] {mark} PC={pc:5d} {func_name:25s} '
                f'op={opcode:2d}.{sub} mode={em} dst={d_raw&0x1f:2d} src={s_raw&0x1f:2d}{extra} '
                f'| R0={r0} R10={r10} R8={r8} SP={sp}'
            )
    
    orig_step()

vm2._step = instrumented_step

try:
    vm2.run(max_cycles=100000)
    print(f'\nExecution trace:')
    for step in trace_steps:
        print(step)
    
    print(f'\n--- Final state ---')
    print(f'State: {vm2.state}, Cycles: {vm2.cycle_count}')
    print(f'R0: {vm2.registers[0]}, R10: {vm2.registers[10]}')
    
    if vm2.registers[0] > 0 and vm2.registers[0] < 1000:
        output = bytes(vm2.heap[OUTPUT_BUF:OUTPUT_BUF + vm2.registers[0]])
        print(f'Output ({len(output)} bytes): {output.hex()}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
