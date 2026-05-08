#!/usr/bin/env python3
"""
Focused diagnostic: trace lookup_opcode execution on "CREA" mnemonic.
Tests whether the isolated lookup_opcode function works correctly.
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState
from build_assembler import build_opcode_table, OPCODE_TABLE, INPUT_BUF, OUTPUT_BUF, LABEL_TABLE

base_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    assembler_evob = bytearray(f.read())

ICHING_NAMES = {
    0: "RECV", 1: "RETURN", 2: "BRANCH", 6: "PUSH_UP", 9: "SHOCK",
    12: "MICRO", 17: "ALLOC", 22: "WELL", 24: "GATHER",
    38: "MUT", 46: "CAST", 47: "ABUNDANCE", 56: "HALT",
    61: "FELLOWSHIP", 62: "MATE", 63: "CREA",
}

def disasm_one(prog, pc):
    if pc + 3 >= len(prog):
        return f"@{pc:04x}: ??? (len={len(prog)})"
    byte0 = prog[pc]
    byte1 = prog[pc + 1]
    opcode = byte0 & 0x3F
    modifier = byte1
    op1 = prog[pc + 2]
    op2 = prog[pc + 3]
    ext_mode = (modifier >> 6) & 0x03
    sub_op = modifier & 0x3F
    name = ICHING_NAMES.get(opcode, f"OP{opcode}")
    dst = op1 & 0x1F
    src = op2 & 0x1F
    if ext_mode == 2 and pc + 7 < len(prog):
        imm = struct.unpack('<I', bytes(prog[pc+4:pc+8]))[0]
        return f"@{pc:04x}: {name}.{sub_op} R{dst},R{src},#{imm}"
    else:
        return f"@{pc:04x}: {name}.{sub_op} R{dst},R{src}"

# Build opcode table
vm = ExtendedIChingVM2()
opcode_table = build_opcode_table()
for i, byte_val in enumerate(opcode_table):
    vm.heap[OPCODE_TABLE + i] = byte_val

# Set up "CREA" at LINE_BUF (0x18100)
LINE_BUF = 0x18100
mnemonic = "CREA"
for i, c in enumerate(mnemonic.encode('ascii')):
    vm.heap[LINE_BUF + i] = c
vm.heap[LINE_BUF + len(mnemonic)] = 0  # null-terminate

# Verify opcode table entries
print("=== Opcode Table Verification ===")
for idx in range(3):  # first 3
    addr = OPCODE_TABLE + idx * 14
    name_bytes = bytes(vm.heap[addr:addr+12])
    name = name_bytes.rstrip(b'\x00').decode('ascii', errors='replace')
    opc = vm.heap[addr+12]
    print(f"  [{idx}] @{addr:#x}: '{name}' op={opc}  hex: {name_bytes.hex()}")
print(f"  ...")
# Check entry 63 (CREA)
addr63 = OPCODE_TABLE + 63 * 14
name_bytes = bytes(vm.heap[addr63:addr63+12])
name = name_bytes.rstrip(b'\x00').decode('ascii', errors='replace')
opc = vm.heap[addr63+12]
print(f"  [63] @{addr63:#x}: '{name}' op={opc}  hex: {name_bytes.hex()}")
# Check entry 64 (should be 0)
addr64 = OPCODE_TABLE + 64 * 14
first_byte = vm.heap[addr64]
print(f"  [64] @{addr64:#x}: first_byte={first_byte} (should be 0 for terminator)")
print()

# Print LINE_BUF content
print(f"LINE_BUF (0x18100): {bytes(vm.heap[LINE_BUF:LINE_BUF+10]).hex()}")
print(f"  as str: {bytes(vm.heap[LINE_BUF:LINE_BUF+10]).decode('ascii', errors='replace')!r}")
print()

# Find lookup_opcode entry point in assembled EVB
# lookup_opcode source starts at asm_core.evoasm line 89
# In the EVB, it's after strcmp. Let me search for the pattern:
# PUSH_UP.1 R4,R4; PUSH_UP.1 R5,R5; FELLOWSHIP.0 R4,R0; CREA.1 R5,R5,#0x16000
# Byte0: 0x86, Byte1: 0x41, Byte2: 0x04|4, Byte3: 0x04|4
# Then: 0x86, 0x41, ...
# Then: 0xBF, 0x40 or 0x00 (FELLOWSHIP.0 R4,R0 = MOV R4,R0, ext_mode=0, sub_op=0)
# Then: 0xBF, 0xC1 or 0x81 (CREA.1 R5,R5 = MOVI, ext_mode=2 for imm #0x16000)

# Search for lookup_opcode entry
lookup_addr = None
for i in range(0, len(assembler_evob) - 8, 4):
    byte0 = assembler_evob[i]
    byte1 = assembler_evob[i + 1]
    # PUSH_UP.1 R4,R4: opcode=6, sub_op=1, dst=4, src=4
    # byte0 = 0x80|6 = 0x86, byte1 = ext_mode<<6 | 1
    # For PUSH_UP.1 without imm, ext_mode=0 → byte1 = 0x01
    if byte0 == 0x86 and (byte1 & 0x3F) == 1:
        next_byte0 = assembler_evob[i + 4]
        next_byte1 = assembler_evob[i + 5]
        # Next should also be PUSH_UP.1: byte0=0x86
        if next_byte0 == 0x86 and (next_byte1 & 0x3F) == 1:
            # Two PUSH_UP.1 in a row
            third_byte0 = assembler_evob[i + 8]
            third_byte1 = assembler_evob[i + 9]
            third_op1 = assembler_evob[i + 10]
            third_op2 = assembler_evob[i + 11]
            # FELLOWSHIP.0 R4,R0: opcode=61 (0x3D), sub_op=0
            # byte0 = 0x80|61 = 0xBD (ext_mode in byte0, but VM ignores top bits)
            # Actually: byte0 = 0x80 | 61 = 0xBD? No, 0x80|61 = 0x80|0x3D = 0xBD ✓
            # Wait, PUSH_UP has opcode=6, byte0 = 0x80|6 = 0x86
            # But in EVB encoding, p2_emit uses 0x80|opcode. So all instructions have byte0=0x80|opcode
            # Actually no. Let me re-check the encoding.
            # p2_emit: FELLOWSHIP.0 R0, R6 → R0=R6 then MATE.3 R0,R0,#128 → R0|=0x80
            # So byte0 = 0x80 | opcode
            # Then byte1: for something with sub_op=0 and ext_mode=1 (no imm): 
            #   FELLOWSHIP.0 R0, R7 → R0=R7 then MATE.3 R0,R0,#64 → R0|=0x40
            #   So byte1 = 0x40 | 0 = 0x40
            dst = third_op1 & 0x1F
            src = third_op2 & 0x1F
            third_opcode = third_byte0 & 0x3F
            if third_opcode == 61 and dst == 4 and src == 0:
                # This is FELLOWSHIP.0 R4,R0!
                # Now check 4th instruction: CREA.1 R5,R5,#0x16000
                fourth_byte0 = assembler_evob[i + 12]
                fourth_byte1 = assembler_evob[i + 13]
                fourth_op1 = assembler_evob[i + 14]
                fourth_op2 = assembler_evob[i + 15]
                fourth_opcode = fourth_byte0 & 0x3F
                fourth_dst = fourth_op1 & 0x1F
                fourth_src = fourth_op2 & 0x1F
                fourth_ext = (fourth_byte1 >> 6) & 0x03
                fourth_sub = fourth_byte1 & 0x3F
                if fourth_opcode == 63 and fourth_dst == 5 and fourth_ext == 2:
                    imm = struct.unpack('<I', bytes(assembler_evob[i+16:i+20]))[0]
                    if imm == 0x16000:
                        lookup_addr = i
                        print(f"Found lookup_opcode at bytecode address {lookup_addr:#x}")
                        break

if lookup_addr is None:
    # Fallback: try to find by looking at strcmp and what comes after
    print("Could not find lookup_opcode by signature. Searching manually...")
    # strcmp ends with: WELL.1 R5,R5; WELL.1 R4,R4; RETURN.0
    # After strcmp comes lookup_opcode
    strcmp_ret_addr = None
    for i in range(0, len(assembler_evob) - 4, 4):
        byte0 = assembler_evob[i]
        byte1 = assembler_evob[i + 1]
        # RETURN.0: opcode=1, sub_op=0 → byte0=0x81, byte1=0x40 (ext_mode=1, sub_op=0)
        if (byte0 & 0x3F) == 1 and (byte1 & 0x3F) == 0:
            # Check if previous were WELL instructions
            prev_op1 = assembler_evob[i - 4]
            prev_op2 = assembler_evob[i - 8]
            if (prev_op1 & 0x3F) == 22 and (prev_op2 & 0x3F) == 22:
                strcmp_ret_addr = i
                print(f"  strcmp RETURN.0 at {i:#x}")
                # Next instruction after RETURN.0 starts lookup_opcode
                lookup_addr = i + 4
                print(f"  lookup_opcode at {lookup_addr:#x}")
                break
    
if lookup_addr is None:
    # Last resort: disasm from 0xe8 (strcmp) and 0x170 (known lookup_opcode area)
    print("Disassembling strcmp area...")
    for pc in range(0xe8, 0x200, 4):
        print(f"  {disasm_one(assembler_evob, pc)}")
    sys.exit(1)

print(f"\n=== lookup_opcode at EVB offset {lookup_addr:#x} ===")
print("First 8 instructions:")
for i in range(8):
    pc = lookup_addr + i * 4
    if pc < len(assembler_evob):
        inst = disasm_one(assembler_evob, pc)
        ext = (assembler_evob[pc + 1] >> 6) & 0x03
        if ext == 2 and pc + 7 < len(assembler_evob):
            pc += 4
        print(f"  {inst}")

print(f"\n=== Direct call to lookup_opcode: R0->LINE_BUF ('CREA') ===")
print(f"Expected: should find opcode=63 for CREA\n")

# Set up VM to call lookup_opcode directly
vm2 = ExtendedIChingVM2()
for i, byte_val in enumerate(opcode_table):
    vm2.heap[OPCODE_TABLE + i] = byte_val
for i, c in enumerate(mnemonic.encode('ascii')):
    vm2.heap[LINE_BUF + i] = c
vm2.heap[LINE_BUF + len(mnemonic)] = 0

vm2.program = bytearray(assembler_evob)
vm2.pc = lookup_addr  # Start at lookup_opcode
vm2.registers[0] = LINE_BUF  # R0 = mnemonic pointer
vm2.registers[29] = vm2.STACK_SIZE  # SP
vm2.state = VMState.RUNNING

# Trace execution
call_depth = 0
step_count = 0
max_steps = 5000
visited_pcs = {}
found_opcode = None
hung = False
entry_63_addr = OPCODE_TABLE + 63 * 14  # 0x16372
saw_entry_63 = False

for step in range(max_steps):
    pc_before = vm2.pc
    if pc_before not in visited_pcs:
        visited_pcs[pc_before] = 0
    visited_pcs[pc_before] += 1
    
    if visited_pcs[pc_before] > 200:
        print(f"\n!!! INFINITE LOOP detected at {pc_before:#x} (visited {visited_pcs[pc_before]} times)")
        hung = True
        break
    
    byte0 = assembler_evob[pc_before]
    byte1 = assembler_evob[pc_before + 1]
    opcode = byte0 & 0x3F
    sub_op = byte1 & 0x3F
    ext_mode = (byte1 >> 6) & 0x03
    
    inst = disasm_one(assembler_evob, pc_before)
    
    # Track important registers
    r0_before = vm2.registers[0]
    r4_before = vm2.registers[4]
    r5_before = vm2.registers[5]
    r29_before = vm2.registers[29]
    r30_before = vm2.registers[30]
    cs_before = len(vm2.call_stack)
    fz_before = vm2.flag_zero
    
    vm2.step()
    
    r0 = vm2.registers[0]
    r4 = vm2.registers[4]
    r5 = vm2.registers[5]
    r29 = vm2.registers[29]
    r30 = vm2.registers[30]
    cs = len(vm2.call_stack)
    fz = vm2.flag_zero
    
    # Check if we just advanced past entry 63
    if r5 == entry_63_addr and not saw_entry_63:
        print(f"\n[{step:3d}] >>> R5 reached entry 63 (CREA) at {r5:#x} <<<")
        saw_entry_63 = True
    
    # Check if we returned from lookup_opcode
    if opcode == 1 and sub_op != 1:  # RETURN.0 (not HLT)
        if cs_before > 0:
            call_depth -= 1
            if call_depth < 0:
                # lookup_opcode returned!
                found_opcode = r0
                print(f"\n[{step:3d}] lookup_opcode RETURNED with R0={r0} (0x{r0:#x}) at step {step}")
                break
    
    # Check for CALL into strcmp
    is_call = (opcode == 47 and sub_op == 1)
    
    # Check if we're about to compare against entry 63
    if (opcode == 47 and sub_op == 1) or (saw_entry_63 and (opcode == 1 or opcode == 24)):
        # Print details when near entry 63
        changes = []
        if r0 != r0_before: changes.append(f"R0:0x{r0_before:x}→0x{r0:x}")
        if r4 != r4_before: changes.append(f"R4:0x{r4_before:x}→0x{r4:x}")
        if r5 != r5_before: changes.append(f"R5:0x{r5_before:x}→0x{r5:x}")
        if r29 != r29_before: changes.append(f"SP:0x{r29_before:x}→0x{r29:x}")
        if cs != cs_before: changes.append(f"CS:{cs_before}→{cs}")
        
        marker = "  " + ", ".join(changes) if changes else ""
        depth = "  " * call_depth
        print(f"[{step:4d}]{depth} {inst:55s} | R0=0x{r0:08x} R4=0x{r4:08x} R5=0x{r5:08x} SP=0x{r29:04x} CS={cs} FZ={fz}{marker}")
        
        if is_call:
            call_depth += 1
    elif is_call or (opcode == 1) or step % 200 == 0 or (r4 != r4_before or r5 != r5_before and opcode == 24):
        changes = []
        if r0 != r0_before: changes.append(f"R0:0x{r0_before:x}→0x{r0:x}")
        if r4 != r4_before: changes.append(f"R4:0x{r4_before:x}→0x{r4:x}")
        if r5 != r5_before and opcode not in (24,): changes.append(f"R5:0x{r5_before:x}→0x{r5:x}")
        if r29 != r29_before: changes.append(f"SP:0x{r29_before:x}→0x{r29:x}")
        if cs != cs_before: changes.append(f"CS:{cs_before}→{cs}")
        
        marker = "  " + ", ".join(changes) if changes else ""
        depth = "  " * call_depth
        print(f"[{step:4d}]{depth} {inst:55s} | R0=0x{r0:08x} R4=0x{r4:08x} R5=0x{r5:08x} SP=0x{r29:04x} CS={cs} FZ={fz}{marker}")
        
        if is_call:
            call_depth += 1
    
    step_count = step

if found_opcode is not None:
    print(f"\n=== SUCCESS: lookup_opcode returned R0={found_opcode} (opcode for CREA) ===")
    print(f"Expected: 63, Got: {found_opcode}")
elif not hung:
    print(f"\n=== lookup_opcode did not return within {max_steps} steps ===")
else:
    print(f"\n=== HUNG at step {step_count} ===")
    print(f"R0=0x{vm2.registers[0]:08x} R4=0x{vm2.registers[4]:08x} R5=0x{vm2.registers[5]:08x}")
    print(f"SP=0x{vm2.registers[29]:04x} CS size={len(vm2.call_stack)}")
    print(f"Last 10 call_stack entries: {vm2.call_stack[-10:]}")
