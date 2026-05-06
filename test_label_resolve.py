#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.native.bootstrap_compiler import BootstrapCompiler

compiler = BootstrapCompiler()

# Simple test of label resolution
test_source = '''@evolang "3.0"

@locus test {
    GUAXU: {
        JMP main
        strlen:
        PUSH R4
        MOVI R5, #0
        strlen_loop:
        LDRB R0, R4
        CMPI R0, #0
        JE strlen_done
        INC R4
        INC R5
        JMP strlen_loop
        strlen_done:
        MOV R0, R5
        POP R4
        RET
        main:
        MOVI R0, #42
        HLT
    }
}
'''

# Test preprocessing step by step
import re
result = test_source
result = re.sub(r'[\u4DC0-\u4DFF]', '', result)
result = result.replace('\u5366\u5E8F', 'GUAXU')

# Now test _resolve_guaxu_labels directly
resolved = compiler._resolve_guaxu_labels(result)

print("=== After label resolution ===")
for i, line in enumerate(resolved.splitlines()):
    print(f'  {i:3d}: {line}')

# Check if labels were resolved
if 'JMP #' in resolved:
    print("\n✓ Labels were resolved!")
else:
    print("\n✗ Labels were NOT resolved!")

# Also check the full preprocess
full_preprocessed = compiler._preprocess_source(test_source)
print("\n=== Full preprocess ===")
for i, line in enumerate(full_preprocessed.splitlines()[:30]):
    print(f'  {i:3d}: {line}')
