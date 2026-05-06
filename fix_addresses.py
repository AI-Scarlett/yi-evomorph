#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                         'evomorph', 'bootstrap', 'native', 'bootstrap_compiler.py')

with open(filepath, 'r') as f:
    content = f.read()

# Replace all old addresses with new ones
# Order matters - replace most specific patterns first
replacements = [
    # STRPOOL (R11 init) - was 0x11000, now 0x2B000
    ('MOVI R11, #0x11000', 'MOVI R11, #0x2B000'),
    # OUTPUT_BUF - was 0xB000, now 0x11000
    ('#0xB000', '#0x11000'),
    # MNEMONIC_TABLE
    ('#0x12000', '#0x2C000'),
    # MNEMONIC_STRINGS
    ('#0x12200', '#0x2C200'),
    # LOCUS_OFFSET_TABLE
    ('#0x12400', '#0x2C400'),
    # MODIFIER_STRINGS
    ('#0x12500', '#0x2C500'),
    # Individual modifier addresses
    ('#0x7607', '#0x2C507'),
    ('#0x7614', '#0x2C514'),
    ('#0x7619', '#0x2C519'),
    ('#0x7624', '#0x2C524'),
    ('#0x7631', '#0x2C531'),
    # KEYWORD_STRINGS
    ('#0x12600', '#0x2C600'),
    ('#0x12608', '#0x2C608'),
    ('#0x1260E', '#0x2C60E'),
    ('#0x12616', '#0x2C616'),
    ('#0x12621', '#0x2C621'),
    # NATIVE_TABLE
    ('#0x12700', '#0x2C700'),
    # NATIVE_STRINGS
    ('#0x12900', '#0x2C900'),
    # Python dict addresses
    ('0x12500: "ASYNC"', '0x2C500: "ASYNC"'),
    ('0x12507: "ATOMIC"', '0x2C507: "ATOMIC"'),
    ('0x12514: "PRIV"', '0x2C514: "PRIV"'),
    ('0x12519: "WEAK"', '0x2C519: "WEAK"'),
    ('0x12524: "STRONG"', '0x2C524: "STRONG"'),
    ('0x12531: "VOLATILE"', '0x2C531: "VOLATILE"'),
    ('0x12600: "evolang"', '0x2C600: "evolang"'),
    ('0x12608: "locus"', '0x2C608: "locus"'),
    ('0x1260E: "xiangci"', '0x2C60E: "xiangci"'),
    ('0x12616: "meta_locus"', '0x2C616: "meta_locus"'),
    ('0x12621: "GUAXU"', '0x2C621: "GUAXU"'),
]

for old, new in replacements:
    content = content.replace(old, new)

with open(filepath, 'w') as f:
    f.write(content)

print("Address replacements done!")

# Verify
with open(filepath, 'r') as f:
    content = f.read()

# Check for any remaining old addresses
import re
old_addrs = re.findall(r'#0x[0-9A-Fa-f]{4,5}', content)
print(f"Remaining hex addresses in ASM: {old_addrs}")
