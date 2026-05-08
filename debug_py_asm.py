#!/usr/bin/env python3
"""Debug: Check Python assembler output for modified source"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

# Load modified sources
base_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'asm_core.evoasm'), 'r') as f:
    core = f.read()

with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'asm_main.evoasm'), 'r') as f:
    main = f.read()

# Combine exactly as build_assembler.py does
lines = main.split('\n')
entry_line = ''
main_body_lines = []
found_entry = False
for line in lines:
    s = line.strip()
    if not found_entry and s.startswith('BRANCH') and '@asm_main' in s:
        entry_line = line
        found_entry = True
        continue
    if found_entry:
        main_body_lines.append(line)

main_body = '\n'.join(main_body_lines)
combined = entry_line + '\n' + core + '\n' + main_body

# Count lines and check for asm_main label
combined_lines = combined.split('\n')
for i, line in enumerate(combined_lines):
    if 'asm_main' in line and line.strip().endswith(':'):
        print(f"Found 'asm_main:' at line {i}: '{line}'")

print(f"Total lines: {len(combined_lines)}")
print(f"First 5 lines:")
for line in combined_lines[:5]:
    print(f"  '{line}'")

# Run Python assembler
vm = ExtendedIChingVM2()
result = vm.assemble(combined)
print(f"\nPython assembler output: {len(result)} bytes")
print(f"First 32 bytes: {result[:32].hex()}")

# Also check: assemble the ORIGINAL source (before modifications)
# Let me check if git can show the original
print("\n--- Checking if original asm_main would work ---")
print("(This test only validates the Python assembler, not EVB)")
