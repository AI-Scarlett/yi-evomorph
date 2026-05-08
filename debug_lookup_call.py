#!/usr/bin/env python3
"""Test: CALL lookup_opcode('CREA') via ABUNDANCE.1, trace strcmp only near entry 63"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState
from build_assembler import build_opcode_table, OPCODE_TABLE

base_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    evob = bytearray(f.read())

def disasm_one(prog, pc):
    if pc + 3 >= len(prog): return f"@{pc:04x}: ???"
    b0,b1,o1,o2 = prog[pc:pc+4]
    op, sub = b0&0x3F, b1&0x3F
    ext = (b1>>6)&3
    name = {0:"RECV",1:"RETURN",2:"BRANCH",6:"PUSH_UP",12:"MICRO",17:"ALLOC",22:"WELL",
            24:"GATHER",47:"ABUNDANCE",61:"FELLOWSHIP",62:"MATE",63:"CREA"}.get(op,f"OP{op}")
    dst, src = o1&0x1F, o2&0x1F
    if ext==2 and pc+7<len(prog):
        imm = struct.unpack('<I', bytes(prog[pc+4:pc+8]))[0]
        return f"@{pc:04x}: {name}.{sub} R{dst},R{src},#{imm}"
    return f"@{pc:04x}: {name}.{sub} R{dst},R{src}"

# Build opcode table
vm = ExtendedIChingVM2()
ot = build_opcode_table()
for i, b in enumerate(ot): vm.heap[OPCODE_TABLE+i] = b

# Put "CREA\0" at LINE_BUF
LINE_BUF, ENTRY_63 = 0x18100, OPCODE_TABLE + 63*14
for i, c in enumerate(b"CREA"): vm.heap[LINE_BUF+i] = c
vm.heap[LINE_BUF+4] = 0

# Find lookup_opcode (signature: PUSH_UP.1 R4,R4; PUSH_UP.1 R5,R5; FELLOWSHIP.0 R4,R0; CREA.1 R5,R5,#0x16000)
lookup_addr = None
for i in range(0, len(evob)-20, 4):
    if evob[i]==0x86 and (evob[i+1]&0x3F)==1 and evob[i+4]==0x86 and (evob[i+5]&0x3F)==1:
        if (evob[i+8]&0x3F)==61 and (evob[i+10]&0x1F)==4 and (evob[i+11]&0x1F)==0:
            if (evob[i+12]&0x3F)==63 and (evob[i+14]&0x1F)==5 and ((evob[i+13]>>6)&3)==2:
                if struct.unpack('<I',bytes(evob[i+16:i+20]))[0]==0x16000:
                    lookup_addr = i; break
if not lookup_addr: print("NOT FOUND!"); sys.exit(1)
print(f"lookup_opcode at {lookup_addr:#x}")

# Test program: CALL lookup_opcode; HLT
t = bytearray()
t.append(0x80|47); t.append(0x80|1); t.append(0); t.append(0)  # ABUNDANCE.1 R0,R0,#...
t.extend(struct.pack('<I', lookup_addr))                         # imm = lookup_addr
t.append(0x80|1); t.append(0x40|1); t.append(0); t.append(0)   # RETURN.1 (HLT)

vm2 = ExtendedIChingVM2()
for i, b in enumerate(ot): vm2.heap[OPCODE_TABLE+i] = b
for i, c in enumerate(b"CREA"): vm2.heap[LINE_BUF+i] = c
vm2.heap[LINE_BUF+4] = 0
vm2.program = t; vm2.pc = 0
vm2.registers[0] = LINE_BUF; vm2.registers[29] = vm2.STACK_SIZE
vm2.state = VMState.RUNNING

print(f"\n=== Calling lookup_opcode('CREA') ===")
print(f"Opcode table entries 62-64:")
for idx in range(62, 65):
    a = OPCODE_TABLE+idx*14
    nb = bytes(vm2.heap[a:a+12]).rstrip(b'\x00').decode('ascii',errors='replace')
    print(f"  [{idx}] @{a:#x}: '{nb}' first_byte={vm2.heap[a]} opcode={vm2.heap[a+12]}")

near_63 = False
for step in range(5000):
    pc = vm2.pc
    byte0, byte1 = evob[pc], evob[pc+1]
    op, sub = byte0&0x3F, byte1&0x3F
    ext = (byte1>>6)&3
    r0, r5 = vm2.registers[0], vm2.registers[5]
    
    # Detect when we're at entry 63
    if not near_63 and op==47 and sub==1 and r5==ENTRY_63:
        near_63 = True
        print(f"\n[{step}] >>> CALL strcmp for entry 63 (CREA)! R0={r0:#x} R5={r5:#x} R1={vm2.registers[1]} {disasm_one(evob,pc)}")
    
    if near_63 or (op==1 and sub!=1) or (op==47 and sub==1):
        inst = disasm_one(evob, pc)
        r0_af, r5_af = vm2.registers[0], vm2.registers[5]
        r4, r1_ = vm2.registers[4], vm2.registers[1]
        cs = len(vm2.call_stack)
        
        vm2.step()
        
        # Show important register changes
        changes = []
        if r0_af!=vm2.registers[0]: changes.append(f"R0:{r0_af:#x}→{vm2.registers[0]:#x}")
        if r4!=vm2.registers[4]: changes.append(f"R4:{r4:#x}→{vm2.registers[4]:#x}")
        if r5_af!=vm2.registers[5]: changes.append(f"R5:{r5_af:#x}→{vm2.registers[5]:#x}")
        m = " " + ",".join(changes) if changes else ""
        print(f"[{step:4d}] {inst:55s} | R0={vm2.registers[0]:#x} R5={vm2.registers[5]:#x} CS={cs} FZ={vm2.flag_zero}{m}")
        
        if op==1 and sub!=1:  # RETURN.0
            if cs==1:  # returning from strcmp
                if near_63:
                    print(f"       <<< strcmp returned R0={vm2.registers[0]}")
                near_63 = False
            elif cs==0:  # returning from lookup_opcode
                print(f"\n=== lookup_opcode returned R0={vm2.registers[0]}")
                if vm2.registers[0]==63:
                    print("SUCCESS! Found CREA opcode=63!")
                else:
                    print(f"FAILED: expected 63, got {vm2.registers[0]}")
                break
    else:
        vm2.step()
    
    if vm2.state != VMState.RUNNING:
        print(f"VM state: {vm2.state}")
        break
