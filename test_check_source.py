#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.bootstrap.iching.iching_compiler import FULL_COMPILER_ASM

# Search for tokenize_check_at in the source
lines = FULL_COMPILER_ASM.split('\n')
for i, line in enumerate(lines):
    if 'tokenize_check_at' in line or 'tokenize_check_quote' in line:
        start = max(0, i-1)
        end = min(len(lines), i+8)
        for j in range(start, end):
            marker = ">>>" if j == i else "   "
            print(f"{marker} {j:4d}: {lines[j]}")
        print()
