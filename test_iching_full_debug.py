#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.iching.iching_compiler import IChingBootstrapCompiler, FULL_COMPILER_ASM, INPUT_BUF
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState

compiler = IChingBootstrapCompiler()
vm = compiler.vm
vm.__init__()

compiler._load_mnemonic_table()
compiler._load_native_table()

source = '@evolang "3.0"\n\n@locus test {\n    mut_rate = 0.01\n    fitness = min_latency\n    env_target = ["linux-6.x"]\n    max_generations = 50\n\n    GUAXU: {\n        CREA R0, R1\n        FELLOWSHIP R0, R1\n        SYNC\n    }\n}\n'
processed = compiler._preprocess_source(source)
vm.load_string(INPUT_BUF, processed)

try:
    vm.load_assembled(FULL_COMPILER_ASM)
    print(f"Assembled OK: {len(vm.program)} bytes")
except Exception as e:
    print(f"Assembly error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

vm.registers[0] = INPUT_BUF
vm.registers[29] = vm.STACK_SIZE

# Run for a limited number of cycles and check state
vm.state = VMState.RUNNING
for i in range(200):
    if vm.state != VMState.RUNNING:
        print(f"Cycle {i}: VM stopped, state={vm.state}")
        break
    old_pc = vm.pc
    vm._step()
    vm.cycle_count += 1
    if i < 20 or i % 50 == 0:
        print(f"Cycle {i}: PC={old_pc}->{vm.pc} R0={vm.registers[0]} R8=0x{vm.registers[8]:X} R10={vm.registers[10]} R13={vm.registers[13]}")

print(f"\nFinal: state={vm.state}, PC={vm.pc}, R10={vm.registers[10]} (tokens), R15={vm.registers[15]} (loci)")
print(f"R8=0x{vm.registers[8]:X} (input ptr), R9=0x{vm.registers[9]:X} (token buf), R12=0x{vm.registers[12]:X} (output)")
