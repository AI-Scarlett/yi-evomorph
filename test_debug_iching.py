#!/usr/bin/env python3
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evomorph.vm.extended_vm2 import ExtendedIChingVM2

vm = ExtendedIChingVM2()
test = """
    CREA.1 R0, R0, #10
    CREA.1 R1, R1, #20
    GATHER.0 R0, R1
    RETURN.1 R0, R0
"""
vm.load_assembled(test)
prog = vm.program
print(f"Program bytes ({len(prog)}): {prog.hex()}")

pos = 0
while pos < len(prog):
    b1 = prog[pos]
    itype = (b1 >> 6) & 0x03
    if itype == 0x02:
        opcode = b1 & 0x3F
        modifier = prog[pos+1]
        op1 = prog[pos+2]
        op2 = prog[pos+3]
        sub_op = modifier & 0x3F
        ext_mode = (modifier >> 6) & 0x03
        mnem = vm.ICHING_OPCODE_MAP.get(opcode, f"?{opcode}")
        extra = ""
        pos += 4
        if ext_mode == 2 and pos + 3 < len(prog):
            imm = struct.unpack('<I', bytes(prog[pos:pos+4]))[0]
            extra = f" imm={imm}"
            pos += 4
        print(f"  [{pos-8 if ext_mode==2 else pos-4:3d}] IChing: {mnem}.{sub_op} ext_mode={ext_mode} dst={op1&0x1F} src={op2&0x1F}{extra}")
    elif itype == 0x01:
        opcode = b1 & 0x3F
        b2 = prog[pos+1]
        b3 = prog[pos+2]
        dst = b2 & 0x1F
        src = b3 & 0x1F
        print(f"  [{pos:3d}] Native: opcode={opcode} dst=R{dst} src=R{src}")
        pos += 3
    else:
        print(f"  [{pos:3d}] Unknown: 0x{b1:02X}")
        pos += 1

vm.registers[29] = vm.STACK_SIZE
print(f"\nInitial: PC={vm.pc} state={vm.state} R0={vm.registers[0]} R1={vm.registers[1]}")

for step in range(20):
    if vm.state.value not in (0, 1):
        break
    old_pc = vm.pc
    old_r0 = vm.registers[0]
    old_r1 = vm.registers[1]
    vm._step()
    print(f"Step {step}: PC={old_pc}->{vm.pc} R0={old_r0}->{vm.registers[0]} R1={old_r1}->{vm.registers[1]} state={vm.state}")

print(f"\nFinal: R0={vm.registers[0]} (expected 30)")
