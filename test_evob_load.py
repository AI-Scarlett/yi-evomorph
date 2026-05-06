#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

compiler = BootstrapCompiler()

source = '@evolang "3.0"\n\n@locus compute {\n    GUAXU: {\n        MOVI R0, #10\n        MOVI R1, #20\n        ADD R0, R1\n        HLT\n    }\n}\n'

result = compiler.compile_source(source)
print(f'Compile success: {result["success"]}')
print(f'EVOB valid: {result.get("evob_valid", False)}')
print(f'Output size: {result.get("output_size", 0)}')

if result.get('output_bytes'):
    evob = result['output_bytes']
    print(f'EVOB hex: {evob.hex()}')
    vm = ExtendedIChingVM2()
    ok = vm.load_evob(evob)
    print(f'EVOB load: {ok}')
    if ok:
        vm.run(max_cycles=1000)
        print(f'VM state: {vm.state}')
        print(f'R0 = {vm.registers[0]} (expected 30)')
        print(f'R1 = {vm.registers[1]} (expected 20)')
        print(f'Cycles: {vm.cycle_count}')
