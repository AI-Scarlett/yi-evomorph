#!/usr/bin/env python3
import sys, os

filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                         'evomorph', 'bootstrap', 'native', 'bootstrap_compiler.py')

with open(filepath, 'r') as f:
    content = f.read()

# Replace all old addresses with new ones (v4 layout)
replacements = [
    # STRPOOL (R11 init) - was 0x2B000, now stays 0x2B000 (same)
    # MNEMONIC_TABLE - was 0x2C000, now 0x33000
    ('#0x2C000', '#0x33000'),
    # MNEMONIC_STRINGS - was 0x2C200, now 0x33200
    ('#0x2C200', '#0x33200'),
    # LOCUS_OFFSET_TABLE - was 0x2C400, now 0x33400
    ('#0x2C400', '#0x33400'),
    # MODIFIER_STRINGS - was 0x2C500, now 0x33500
    ('#0x2C500', '#0x33500'),
    # Individual modifier addresses
    ('#0x2C507', '#0x33507'),
    ('#0x2C514', '#0x33514'),
    ('#0x2C519', '#0x33519'),
    ('#0x2C524', '#0x33524'),
    ('#0x2C531', '#0x33531'),
    # KEYWORD_STRINGS - was 0x2C600, now 0x33600
    ('#0x2C600', '#0x33600'),
    ('#0x2C608', '#0x33608'),
    ('#0x2C60E', '#0x3360E'),
    ('#0x2C616', '#0x33616'),
    ('#0x2C621', '#0x33621'),
    # NATIVE_TABLE - was 0x2C700, now 0x33700
    ('#0x2C700', '#0x33700'),
    # NATIVE_STRINGS - was 0x2C900, now 0x33900
    ('#0x2C900', '#0x33900'),
    # Python dict addresses
    ('0x2C500: "ASYNC"', '0x33500: "ASYNC"'),
    ('0x2C507: "ATOMIC"', '0x33507: "ATOMIC"'),
    ('0x2C514: "PRIV"', '0x33514: "PRIV"'),
    ('0x2C519: "WEAK"', '0x33519: "WEAK"'),
    ('0x2C524: "STRONG"', '0x33524: "STRONG"'),
    ('0x2C531: "VOLATILE"', '0x33531: "VOLATILE"'),
    ('0x2C600: "evolang"', '0x33600: "evolang"'),
    ('0x2C608: "locus"', '0x33608: "locus"'),
    ('0x2C60E: "xiangci"', '0x3360E: "xiangci"'),
    ('0x2C616: "meta_locus"', '0x33616: "meta_locus"'),
    ('0x2C621: "GUAXU"', '0x33621: "GUAXU"'),
]

for old, new in replacements:
    content = content.replace(old, new)

# Also update the Python constants
content = content.replace('MNEMONIC_TABLE = 0x2C000', 'MNEMONIC_TABLE = 0x33000')
content = content.replace('MNEMONIC_STRINGS = 0x2C200', 'MNEMONIC_STRINGS = 0x33200')
content = content.replace('LOCUS_OFFSET_TABLE = 0x2C400', 'LOCUS_OFFSET_TABLE = 0x33400')
content = content.replace('MODIFIER_STRINGS = 0x2C500', 'MODIFIER_STRINGS = 0x33500')
content = content.replace('KEYWORD_STRINGS = 0x2C600', 'KEYWORD_STRINGS = 0x33600')
content = content.replace('NATIVE_TABLE = 0x2C700', 'NATIVE_TABLE = 0x33700')
content = content.replace('NATIVE_STRINGS = 0x2C900', 'NATIVE_STRINGS = 0x33900')

with open(filepath, 'w') as f:
    f.write(content)

print("v4 address replacements done!")
