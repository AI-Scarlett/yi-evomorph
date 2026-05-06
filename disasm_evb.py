#!/usr/bin/env python3
"""反汇编 assembler.evob，查看关键函数位置和调用关系"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from build_assembler import (
    build_opcode_table, load_assembler_source,
    INPUT_BUF, OUTPUT_BUF, LABEL_TABLE, OPCODE_TABLE
)

# IChing opcode names
OPCODE_NAMES = [
    "RECV", "RETURN", "BRANCH", "APPROACH", "YIELD", "OBSCURE", "PUSH_UP",
    "FLUSH", "SPECULATE", "SHOCK", "UNLOCK", "MISMATCH", "MICRO", "ABOUND",
    "PERSIST", "THRUST", "MERGE", "ALLOC", "TRAP", "THROTTLE", "LAME",
    "SYNC", "WELL", "WAIT", "GATHER", "FOLLOWING", "TRAPPED", "JOY",
    "SENSE", "REPLACE", "OVERLOAD", "BREAK", "STRIP", "NOURISH", "SPRT",
    "REDUCE", "STILL", "ADORN", "MUT", "BARRIER", "ADVANCE", "BITE",
    "FUTU", "CONVERT", "TRAVEL", "ILLUMINATE", "CAST", "ABUNDANCE",
    "CONTEMPLATE", "INCREASE", "DISPERSE", "TRUST", "GRADUAL", "BIND",
    "PENETRATE", "PREFETCH", "HALT", "INTRINSIC", "LOCK", "STEP",
    "RETREAT", "FELLOWSHIP", "MATE", "CREA"
]

vm = ExtendedIChingVM2()
HEAP_SIZE = len(vm.heap)
print(f'VM heap size: {HEAP_SIZE}')

opcode_table = build_opcode_table()
for i, b in enumerate(opcode_table):
    vm.heap[OPCODE_TABLE + i] = b
evob = vm.assemble(load_assembler_source())
print(f'Assembler EVB: {len(evob)} bytes')

# Collect labels from assembly
labels = {}
source = load_assembler_source()
for line in source.split('\n'):
    line = line.strip()
    if ':' in line:
        # Check if it's a label definition (not instruction with ':' in operand)
        parts = line.split(':')
        potential_label = parts[0].strip()
        if potential_label and not any(c in potential_label for c in ' .@#'):
            # Check if it's a function name or branch target
            if len(potential_label) > 0:
                pass  # We'll find the address

# Now look for label definitions in pass1 of the assembled bytecode
# Actually, let's just find the CALL targets and try to identify functions

print(f'\n=== Bytecode at key positions ===')

# Disassemble function entry points
# Functions in order: skip_spaces, skip_line, parse_reg, strcmp, 
# lookup_opcode, lookup_label, add_label, emit_byte, emit_word

def disasm_at(evob, pc):
    """Disassemble one instruction"""
    if pc + 3 >= len(evob):
        return None, 0, ""
    b1 = evob[pc]
    t = (b1 >> 6) & 3
    if t != 2:
        return None, 0, f"type={t}"
    
    op = b1 & 0x3F
    b2 = evob[pc+1]
    mode = (b2 >> 6) & 3
    sub = b2 & 0x3F
    dst = evob[pc+2]
    src = evob[pc+3]
    
    opname = OPCODE_NAMES[op] if op < len(OPCODE_NAMES) else f"OP{op}"
    
    size = 4
    imm_str = ""
    if mode == 2 and pc + 8 <= len(evob):
        imm = struct.unpack('<I', bytes(evob[pc+4:pc+8]))[0]
        size = 8
        imm_str = f" #0x{imm:x}"
    
    return op, size, f"{opname}.{sub} R{dst}, R{src}{imm_str}"

# Find functions by scanning for RETURN.0 patterns
print("\n=== Scanning for function entry/exit points ===")
func_starts = {}
pc = 0
while pc < len(evob) - 3:
    b1 = evob[pc]
    t = (b1 >> 6) & 3
    if t == 2:
        op = b1 & 0x3F
        sub = evob[pc+1] & 0x3F
        mode = (evob[pc+1] >> 6) & 3
        
        # RETURN.0 → function end
        if op == 1 and sub == 0:
            func_starts[pc] = "← RETURN (func end)"
        
        # CALL (ABUNDANCE.1 with imm)
        if op == 47 and sub == 1 and mode == 2 and pc + 8 <= len(evob):
            imm = struct.unpack('<I', bytes(evob[pc+4:pc+8]))[0]
            # Check if this calls a known function
            if imm == 0:
                func_starts[imm] = f"← entry point (@0)"
        
        size = 4 if mode < 2 else 8
    else:
        size = 4
    pc += max(size, 4)

# Print first few instructions at PC=0 (entry point)
print(f"\n=== Entry point (PC=0) ===")
pc = 0
for _ in range(5):
    if pc + 3 >= len(evob):
        break
    _, size, dis = disasm_at(evob, pc)
    print(f"  {pc:5d}: {dis}")
    pc += size

# Now trace through the assembled bytecode to find all CALL targets
print(f"\n=== All CALL targets in assembled bytecode ===")
call_targets = {}
pc = 0
while pc < len(evob) - 3:
    b1 = evob[pc]
    t = (b1 >> 6) & 3
    if t == 2:
        op = b1 & 0x3F
        mode = (evob[pc+1] >> 6) & 3
        sub = evob[pc+1] & 0x3F
        
        if op == 47 and sub == 1 and mode == 2 and pc + 8 <= len(evob):
            imm = struct.unpack('<I', bytes(evob[pc+4:pc+8]))[0]
            if imm not in call_targets:
                call_targets[imm] = []
            call_targets[imm].append(pc)
        
        size = 4 if mode < 2 else 8
    else:
        size = 4
    pc += max(size, 4)

# Identify functions by their first instruction
print(f"  {len(call_targets)} unique call targets:")
for target in sorted(call_targets.keys()):
    callers = call_targets[target]
    if target + 3 < len(evob):
        _, _, first_instr = disasm_at(evob, target)
        # Try to identify function by scanning context
        # Look at nearby instructions for PUSH_UP pattern
        context = []
        for i in range(max(0, target-8), min(target+20, len(evob))):
            if i + 3 < len(evob):
                _, _, d = disasm_at(evob, i)
                if d:
                    context.append(f"  {i}: {d}")
        context_str = ""
        if context:
            context_str = f" | ctx: {context[0]}" if context else ""
        print(f"  0x{target:04x} ({target:5d}): {first_instr}  ← called from {len(callers)} places: {callers[:3]}{'...' if len(callers)>3 else ''}{context_str}")

# Specifically look for CREA.1 R0,R0,#0x1000 pattern (pass1/pass2 entry)
print(f"\n=== Searching for CREA.1 R0,R0,#0x1000 ===")
pc = 0
while pc < len(evob) - 7:
    if pc + 7 < len(evob):
        b1 = evob[pc]
        t = (b1 >> 6) & 3
        if t == 2:
            op = b1 & 0x3F
            sub = evob[pc+1] & 0x3F
            mode = (evob[pc+1] >> 6) & 3
            if op == 63 and sub == 1 and mode == 2:  # CREA.1 with imm
                imm = struct.unpack('<I', bytes(evob[pc+4:pc+8]))[0]
                if imm == 0x1000:
                    print(f"  PC={pc}: CREA.1 R0,R0,#0x1000")
                    # Show surrounding instructions
                    for offset in range(-16, 24, 4):
                        check_pc = pc + offset
                        if 0 <= check_pc < len(evob):
                            _, sz, d = disasm_at(evob, check_pc)
                            if d:
                                marker = " ←" if offset == 0 else ""
                                print(f"    {check_pc:5d}: {d}{marker}")
                    print()
        size = 4 if (b1 & 0x40 and evob[pc+1] & 0x80) else 4
    else:
        size = 4
    pc += max(size, 4)
