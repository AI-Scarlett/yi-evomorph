#!/usr/bin/env python3
"""Full pass2 trace for 'CREA.1 R0, R0, #42' — trace every step in p2_parse_mnem + lookup"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2
from evomorph.vm.virtual_machine import VMState
from build_assembler import build_opcode_table, OPCODE_TABLE, INPUT_BUF, OUTPUT_BUF, LABEL_TABLE

base_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base_dir, 'evomorph', 'bootstrap', 'assembler.evob'), 'rb') as f:
    evob = bytearray(f.read())

ICHING = {0:"RECV",1:"RETURN",2:"BRANCH",6:"PUSH_UP",9:"SHOCK",12:"MICRO",
          17:"ALLOC",22:"WELL",24:"GATHER",38:"MUT",46:"CAST",47:"ABUNDANCE",
          56:"HALT",61:"FELLOWSHIP",62:"MATE",63:"CREA"}

def dis(p,pk): 
    if pk+3>=len(p): return "???"
    b0,b1,o1,o2=p[pk:pk+4]; op,sub=b0&0x3F,b1&0x3F; ext=(b1>>6)&3
    n=ICHING.get(op,f"OP{op}"); d,s=o1&0x1F,o2&0x1F
    if ext==2 and pk+7<len(p): 
        i=struct.unpack('<I',bytes(p[pk+4:pk+8]))[0]; return f"@{pk:04x}: {n}.{sub} R{d},R{s},#{i}"
    return f"@{pk:04x}: {n}.{sub} R{d},R{s}"

# Build
vm = ExtendedIChingVM2()
ot = build_opcode_table()
for i,b in enumerate(ot): vm.heap[OPCODE_TABLE+i]=b

source = "  CREA.1 R0, R0, #42\n"
sb = source.encode('ascii')+b'\x00'
for i,b in enumerate(sb): vm.heap[INPUT_BUF+i]=b
for i in range(LABEL_TABLE, LABEL_TABLE+0x4000): vm.heap[i]=0

# Find pass2 entry
# pass2 starts with: PUSH_UP.1 R4,R4; PUSH_UP.1 R5,R5; PUSH_UP.1 R6,R6; PUSH_UP.1 R7,R7; PUSH_UP.1 R11,R11
# Then: CREA.1 R0,R0,#0x1000; FELLOWSHIP.0 R8,R0
pass2_addr = None
for i in range(0,len(evob)-24,4):
    if evob[i]==0x86 and evob[i+4]==0x86 and evob[i+8]==0x86 and evob[i+12]==0x86 and evob[i+16]==0x86:
        # Check for 5 consecutive PUSH_UP.1 with different registers
        regs = [evob[i+j*4+2]&0x1F for j in range(5)]
        if regs[0]==4 and regs[1]==5 and regs[2]==6 and regs[3]==7 and regs[4]==11:
            # Check next: CREA.1 R0,R0,#0x1000
            cr = i+20
            if (evob[cr]&0x3F)==63 and (evob[cr+1]&0x3F)==1:
                imm = struct.unpack('<I',bytes(evob[cr+4:cr+8]))[0]
                if imm==0x1000:
                    pass2_addr = i; break
if not pass2_addr:
    print("Could not find pass2!")
    sys.exit(1)
print(f"pass2 at {pass2_addr:#x}")

vm.program = evob
vm.registers[0] = INPUT_BUF
vm.registers[29] = vm.STACK_SIZE
vm.state = VMState.RUNNING

# Run pass1 first to set up labels (R10 accumulates instruction sizes)
# Then manually call pass2

# Actually, let's skip pass1 entirely for a single no-label instruction
# and directly call pass2. pass2 reads source from INPUT_BUF directly, 
# doesn't need labels for CREA.1 R0, R0, #42 (no @label)
# 
# But we need to call pass2 via asm_main's convention.
# Let's trace from asm_main entry.

# Find asm_main
asm_main_addr = None
for i in range(0,len(evob)-8,4):
    # asm_main: PUSH_UP.1 R4,R4 → that's common, let's look for the pattern after
    if evob[i]==0x86 and (evob[i+1]&0x3F)==1 and (evob[i+2]&0x1F)==4:
        # FELLOWSHIP.0 R4,R0 at i+4
        if (evob[i+4]&0x3F)==61 and (evob[i+5]&0x3F)==0 and (evob[i+6]&0x1F)==4 and (evob[i+7]&0x1F)==0:
            # ABUNDANCE.1 R0,R0,#pass1
            ab = i+8
            if (evob[ab]&0x3F)==47 and (evob[ab+1]&0x3F)==1:
                imm = struct.unpack('<I',bytes(evob[ab+4:ab+8]))[0]
                if imm==pass2_addr - 8 or abs(imm - 900) < 200:
                    # This might be asm_main, verify with more context
                    asm_main_addr = i; break

print(f"asm_main candidate at {asm_main_addr:#x}")

# Let's test directly: call pass2 and trace
vm2 = ExtendedIChingVM2()
for i,b in enumerate(ot): vm2.heap[OPCODE_TABLE+i]=b
for i,b in enumerate(sb): vm2.heap[INPUT_BUF+i]=b
for i in range(LABEL_TABLE, LABEL_TABLE+0x4000): vm2.heap[i]=0
# Clear output buffer
for i in range(OUTPUT_BUF, OUTPUT_BUF+0x1000): vm2.heap[i]=0
# Clear LINE_BUF
for i in range(0x18100, 0x18200): vm2.heap[i]=0

vm2.program = evob
vm2.registers[0] = INPUT_BUF+2  # Start at 'C' (after "  ")
vm2.registers[8] = INPUT_BUF     # R8 = source cursor
vm2.registers[9] = OUTPUT_BUF    # R9 = output cursor
vm2.registers[10] = 0            # R10 = byte count
vm2.registers[29] = vm2.STACK_SIZE
vm2.state = VMState.RUNNING

print(f"\n=== Tracing pass2 execution ===")
print(f"Source: {source!r}")
print(f"INPUT_BUF: {bytes(vm2.heap[INPUT_BUF:INPUT_BUF+30])}")
print(f"R8=INPUT_BUF={INPUT_BUF:#x}, R9=OUTPUT_BUF={OUTPUT_BUF:#x}, R10=0\n")

# Plant HALT at safe addr, pre-populate call_stack so we can detect returns
vm2.heap[0x1FFFC] = 0x81  # RETURN.1 at safe addr (will be executed? No, we just need it)

in_lookup = False
in_strcmp = False
step_limit = 5000
last_r5_lookup = 0

for step in range(step_limit):
    pc = vm2.pc
    b0, b1 = evob[pc], evob[pc+1]
    op, sub = b0&0x3F, b1&0x3F
    ext = (b1>>6)&3
    name = ICHING.get(op, "?")
    
    r0_b, r4_b, r5_b, r6_b, r8_b, r9_b, r10_b = [vm2.registers[i] for i in [0,4,5,6,8,9,10]]
    cs_b = len(vm2.call_stack)
    
    vm2.step()
    
    r0, r4, r5, r6, r8, r9, r10 = [vm2.registers[i] for i in [0,4,5,6,8,9,10]]
    cs = len(vm2.call_stack)
    
    # Detect entering lookup_opcode CALL
    if op==47 and sub==1:  # ABUNDANCE.1 (CALL)
        target = struct.unpack('<I',bytes(evob[pc+4:pc+8]))[0] if ext==2 else None
        if target and target >= 0x150 and target <= 0x200:  # lookup_opcode area
            in_lookup = True
            print(f"\n[{step}] --- ENTERING lookup_opcode (CALL to {target:#x}) ---")
            print(f"  R0={r0_b:#x} (mnemonic ptr), R4={r4_b:#x}, R6={r6_b:#x}")
            which_mnem = bytes(vm2.heap[r0_b:r0_b+6]).split(b'\x00')[0]
            print(f"  Looking up: '{which_mnem.decode()}'")

    # Show key instructions
    show = False
    if in_lookup:
        show = True
        if op==1 and sub!=1 and cs_b==1:  # RETURN from strcmp
            pass  # will show below
    elif cs_b==2:  # We're in pass2 and something called
        show = True

    if show and (op==47 or op==1 or name in ("FELLOWSHIP","CREA","BRANCH","GATHER","ALLOC","RECV","MICRO") or r10!=r10_b):
        inst = dis(evob,pc)
        ch = []
        if r0!=r0_b: ch.append(f"R0:{r0_b}→{r0}")
        if r4!=r4_b: ch.append(f"R4:{r4_b}→{r4}")
        if r5!=r5_b and r5_b!=0: ch.append(f"R5:{r5_b}→{r5}")
        if r6!=r6_b: ch.append(f"R6:{r6_b}→{r6}")
        if r8!=r8_b: ch.append(f"R8:{r8_b:#x}→{r8:#x}")
        if r9!=r9_b: ch.append(f"R9:{r9_b:#x}→{r9:#x}")
        if r10!=r10_b: ch.append(f"R10:{r10_b}→{r10}")
        m = " | " + " ".join(ch) if ch else ""
        print(f"[{step:4d}] {inst:55s}{m}")

    # Detect returning from lookup_opcode
    if op==1 and sub!=1 and cs_b==1 and in_lookup:
        print(f"\n[{step}] <<< RETURN from lookup_opcode: R0={r0_b} (opcode)")
        in_lookup = False
        if r0_b == 63:
            print("*** SUCCESS: lookup returned 63 (CREA) ***")
        else:
            print(f"*** FAIL: expected 63, got {r0_b} ***")

    if vm2.state != VMState.RUNNING:
        print(f"\nVM state: {vm2.state} at step {step}")
        break

print(f"\nFinal: R0={vm2.registers[0]}, R6={vm2.registers[6]}, R8={vm2.registers[8]:#x}, R9={vm2.registers[9]:#x}, R10={vm2.registers[10]}")
if vm2.registers[10]>0:
    print(f"Output: {bytes(vm2.heap[OUTPUT_BUF:OUTPUT_BUF+vm2.registers[10]]).hex()}")
