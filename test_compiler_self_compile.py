#!/usr/bin/env python3
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import (
    BootstrapCompiler, STDLIB_ASM, LEXER_ASM, LOOKUP_ASM, CODEGEN_ASM, PARSER_ASM, MAIN_ASM
)
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

def build_compiler_evo_source():
    asm_code = "JMP main\n" + STDLIB_ASM + LEXER_ASM + LOOKUP_ASM + CODEGEN_ASM + PARSER_ASM + MAIN_ASM
    guaxu_lines = []
    for line in asm_code.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith(';'):
            continue
        guaxu_lines.append('        ' + line)
    
    evo_source = '@evolang "3.0"\n\n'
    evo_source += '@locus bootstrap_compiler {\n'
    evo_source += '    GUAXU: {\n'
    evo_source += '\n'.join(guaxu_lines) + '\n'
    evo_source += '    }\n'
    evo_source += '}\n'
    return evo_source

compiler = BootstrapCompiler()
evo_source = build_compiler_evo_source()

result = compiler.compile_source(evo_source)
print(f"Compile: success={result['success']}")
print(f"Locus count: {result.get('locus_count', 'N/A')}")
print(f"Output size: {result['output_size']}")
print(f"EVOB valid: {result.get('evob_valid', False)}")
print(f"Token count: {result['token_count']}")
print(f"Cycles: {result['cycles']}")

if result.get('output_bytes'):
    evob = result['output_bytes']
    print(f"\nEVOB hex (first 100 bytes): {evob[:100].hex()}")
    print(f"EVOB total: {len(evob)} bytes")
    
    # Parse EVOB header
    if evob[:4] == b'EVOB':
        version = struct.unpack(">H", evob[4:6])[0]
        header_size = struct.unpack(">H", evob[6:8])[0]
        locus_count = struct.unpack(">H", evob[8:10])[0]
        print(f"\nEVOB Header:")
        print(f"  Magic: EVOB")
        print(f"  Version: {version}")
        print(f"  Header size: {header_size}")
        print(f"  Locus count: {locus_count}")
        
        # Parse locus offset table
        for i in range(locus_count):
            off = 10 + i * 4
            locus_offset = struct.unpack(">I", evob[off:off+4])[0]
            print(f"  Locus[{i}] offset: {locus_offset}")
        
        # Show first few bytes of bytecode
        bytecode = evob[header_size:]
        print(f"\nBytecode: {len(bytecode)} bytes")
        print(f"  First 40 bytes: {bytecode[:40].hex()}")
        
        # Try to load and verify
        vm = ExtendedIChingVM2()
        ok = vm.load_evob(evob)
        print(f"\nEVOB load into VM: {ok}")
        if ok:
            print(f"  Program size: {len(vm.program)} bytes")
            print(f"  PC: {vm.pc}")
            # Try running a few steps
            vm.run(max_cycles=100)
            print(f"  After 100 cycles: state={vm.state}")
