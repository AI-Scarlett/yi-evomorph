#!/usr/bin/env python3
"""Disassemble assembler.evob around key areas"""
import struct

base_dir = '/Users/zhouxiaoming/Downloads/evomorph'
with open(f'{base_dir}/evomorph/bootstrap/assembler.evob', 'rb') as f:
    evob = f.read()

ICHING_NAMES = {
    0: "RECV", 1: "RETURN", 2: "BRANCH", 6: "PUSH_UP", 9: "SHOCK",
    12: "MICRO", 13: "ABOUND", 17: "ALLOC", 22: "WELL", 24: "GATHER",
    38: "MUT", 46: "CAST", 47: "ABUNDANCE", 48: "CONTEMPLATE",
    56: "HALT", 61: "FELLOWSHIP", 62: "MATE", 63: "CREA",
}

def disasm_range(prog, start, end, show_labels=True):
    pc = start
    while pc < end and pc + 3 < len(prog):
        byte1 = prog[pc]
        opcode = byte1 & 0x3F
        modifier = prog[pc + 1]
        op1 = prog[pc + 2]
        op2 = prog[pc + 3]
        ext_mode = (modifier >> 6) & 0x03
        sub_op = modifier & 0x3F
        
        name = ICHING_NAMES.get(opcode, f"OP{opcode}")
        
        if ext_mode == 2 and pc + 7 < len(prog):
            imm = struct.unpack('<I', bytes(prog[pc+4:pc+8]))[0]
            instr = f"@{pc:04x}: {name}.{sub_op} R{op1},R{op2},#{imm}(0x{imm:x})"
            pc += 8
        else:
            instr = f"@{pc:04x}: {name}.{sub_op} R{op1},R{op2}"
            pc += 4
        
        # Check if this is a branch target
        target_marker = ""
        if opcode in (1, 2) and ext_mode == 2 and sub_op in (1, 2) and pc > 8:
            pass  # ignore for brevity
            
        print(f"  {instr}")
    return pc

print("=== assembler.evob disassembly ===")
print(f"Total size: {len(evob)} bytes")
print()

# Disassemble strcmp (should be around address 0xe8 based on CALL #232 target)
print("--- strcmp (CALL target is #232 = 0xe8) ---")
disasm_range(evob, 0xe8, 0xe8 + 0x70)
print()

# Disassemble lookup_opcode (around 0x180 based on trace: PC=0x1a0 CALL, PC=0x1c0 GATHER)
print("--- lookup_opcode ---")
disasm_range(evob, 0x150, 0x220)
print()

# Disassemble p2_emit (find it by looking for MATE.3 with #128 and ABUNDANCE to emit_byte)
print("--- pass2 p2_emit near end ---")
# p2_emit starts somewhere after pass2 code. Let's find it.
# p2_emit has FELLOWSHIP.0 R0,R11 → FELLOWSHIP.0 R0,R6 → MATE.3 R0,R0,#128
# Search for this pattern
print("Searching for p2_emit signature...")
# The pattern: parse_reg is the important function being called
# Let's also disassemble the main lookup area more carefully
