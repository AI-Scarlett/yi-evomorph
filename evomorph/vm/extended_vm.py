#!/usr/bin/env python3
"""
扩展的易衍虚拟机 - 支持双指令集
- 六十四卦指令（操作码0-63）- 保持兼容
- 传统CPU指令（操作码64-255）- 新增，用于实现编译器
"""

import sys
import os
import struct
from enum import IntEnum
from typing import Dict, List, Any, Optional, Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from evomorph.vm.virtual_machine import IChingVM, VMState


class Opcodes:
    NOP = 64
    HLT = 65
    
    ADD = 70
    SUB = 71
    MUL = 72
    DIV = 73
    MOD = 74
    INC = 75
    DEC = 76
    NEG = 77
    ABS = 78
    
    AND = 80
    OR = 81
    XOR = 82
    NOT = 83
    SHL = 84
    SHR = 85
    SAR = 86
    ROL = 87
    ROR = 88
    
    CMP = 90
    TEST = 91
    
    JMP = 100
    JE = 101
    JNE = 102
    JZ = 103
    JNZ = 104
    JL = 105
    JLE = 106
    JG = 107
    JGE = 108
    JC = 109
    JNC = 110
    JO = 111
    JNO = 112
    JS = 113
    JNS = 114
    
    MOV = 120
    LEA = 121
    XCHG = 122
    
    PUSH = 130
    POP = 131
    PUSHA = 132
    POPA = 133
    
    CALL = 140
    RET = 141
    INT = 142
    IRET = 143
    
    LOAD = 150
    STORE = 151
    LODSB = 152
    STOSB = 153
    MOVSB = 154
    
    IN = 160
    OUT = 161
    
    STI = 170
    CLI = 171
    
    CLC = 180
    STC = 181
    CMC = 182
    CLD = 183
    STD = 184


class OperandType(IntEnum):
    REG = 0
    IMM = 1
    MEM = 2
    REG_INDIRECT = 3
    REG_OFFSET = 4


class ExtendedIChingVM(IChingVM):
    NUM_REGISTERS = 32
    
    SPECIAL_REGS = {
        "R_FP": 28,
        "R_SP": 29,
        "R_LR": 30,
        "R_A0": 31,
        "R_A1": 0,
        "R_A2": 1,
        "R_A3": 2,
        "R_T0": 3,
        "R_T1": 4,
        "R_T2": 5,
        "R_T3": 6,
        "R_S0": 7,
        "R_S1": 8,
        "R_IP": 15,
    }
    
    def __init__(self):
        super().__init__()
        self.registers = [0] * self.NUM_REGISTERS
        self.flag_direction = False
        self.flag_interrupt = True
        self.interrupt_table = {}
        self.syscall_table = {}
        self._init_special_regs()
        self._setup_default_interrupts()
    
    def _init_special_regs(self):
        self.registers[self.SPECIAL_REGS["R_SP"]] = self.STACK_SIZE
        self.registers[self.SPECIAL_REGS["R_FP"]] = self.STACK_SIZE
    
    def _setup_default_interrupts(self):
        self.interrupt_table[0x00] = self._int_divide_by_zero
        self.interrupt_table[0x01] = self._int_single_step
        self.interrupt_table[0x03] = self._int_breakpoint
        self.interrupt_table[0x0E] = self._int_page_fault
        self.interrupt_table[0x20] = self._int_timer
        self.interrupt_table[0x80] = self._int_syscall
    
    def _int_divide_by_zero(self):
        self.state = VMState.ERROR
        print("[VM Error] Division by zero")
    
    def _int_single_step(self):
        self.state = VMState.PAUSED
    
    def _int_breakpoint(self):
        self.state = VMState.PAUSED
    
    def _int_page_fault(self):
        self.state = VMState.ERROR
        print("[VM Error] Page fault")
    
    def _int_timer(self):
        pass
    
    def _int_syscall(self):
        syscall_num = self.registers[self.SPECIAL_REGS["R_A0"]]
        handler = self.syscall_table.get(syscall_num)
        if handler:
            handler(self)
    
    def register_syscall(self, num: int, handler: Callable):
        self.syscall_table[num] = handler
    
    def _step(self):
        if self.pc + 1 >= len(self.program):
            self.state = VMState.HALTED
            return
        
        byte1 = self.program[self.pc]
        byte2 = self.program[self.pc + 1] if self.pc + 1 < len(self.program) else 0
        
        opcode = (byte1 >> 2) & 0x3F
        modifier = ((byte1 & 0x03) << 4) | (byte2 & 0x0F)
        
        if opcode < 64:
            self.pc += 2
            operands = self._read_operands(opcode)
            self._execute_iching(opcode, modifier, operands)
        else:
            self._execute_extended(byte1, byte2)
    
    def _execute_iching(self, opcode, modifier, operands):
        handler = self._OPCODE_HANDLERS.get(opcode)
        if handler:
            handler(self, modifier, operands)
            self.energy_cost += self._instruction_energy(opcode)
            self.trace_log.append({
                "pc": self.pc - 2,
                "opcode": opcode,
                "modifier": modifier,
                "operands": operands,
                "cycle": self.cycle_count,
                "instruction_set": "iching",
            })
        else:
            self.state = VMState.ERROR
    
    def _execute_extended(self, byte1, byte2):
        opcode = byte1
        sub_opcode = byte2
        
        if opcode == Opcodes.NOP:
            self.pc += 1
        elif opcode == Opcodes.HLT:
            self.pc += 1
            self.state = VMState.HALTED
        elif opcode == Opcodes.ADD:
            self._op_add(sub_opcode)
        elif opcode == Opcodes.SUB:
            self._op_sub(sub_opcode)
        elif opcode == Opcodes.MUL:
            self._op_mul(sub_opcode)
        elif opcode == Opcodes.DIV:
            self._op_div(sub_opcode)
        elif opcode == Opcodes.MOD:
            self._op_mod(sub_opcode)
        elif opcode == Opcodes.INC:
            self._op_inc(sub_opcode)
        elif opcode == Opcodes.DEC:
            self._op_dec(sub_opcode)
        elif opcode == Opcodes.NEG:
            self._op_neg(sub_opcode)
        elif opcode == Opcodes.ABS:
            self._op_abs(sub_opcode)
        elif opcode == Opcodes.AND:
            self._op_and(sub_opcode)
        elif opcode == Opcodes.OR:
            self._op_or(sub_opcode)
        elif opcode == Opcodes.XOR:
            self._op_xor(sub_opcode)
        elif opcode == Opcodes.NOT:
            self._op_not(sub_opcode)
        elif opcode == Opcodes.SHL:
            self._op_shl(sub_opcode)
        elif opcode == Opcodes.SHR:
            self._op_shr(sub_opcode)
        elif opcode == Opcodes.SAR:
            self._op_sar(sub_opcode)
        elif opcode == Opcodes.CMP:
            self._op_cmp(sub_opcode)
        elif opcode == Opcodes.TEST:
            self._op_test(sub_opcode)
        elif opcode == Opcodes.JMP:
            self._op_jmp(sub_opcode)
        elif opcode == Opcodes.JE:
            self._op_je(sub_opcode)
        elif opcode == Opcodes.JNE:
            self._op_jne(sub_opcode)
        elif opcode == Opcodes.JL:
            self._op_jl(sub_opcode)
        elif opcode == Opcodes.JLE:
            self._op_jle(sub_opcode)
        elif opcode == Opcodes.JG:
            self._op_jg(sub_opcode)
        elif opcode == Opcodes.JGE:
            self._op_jge(sub_opcode)
        elif opcode == Opcodes.MOV:
            self._op_mov(sub_opcode)
        elif opcode == Opcodes.LEA:
            self._op_lea(sub_opcode)
        elif opcode == Opcodes.XCHG:
            self._op_xchg(sub_opcode)
        elif opcode == Opcodes.PUSH:
            self._op_push(sub_opcode)
        elif opcode == Opcodes.POP:
            self._op_pop(sub_opcode)
        elif opcode == Opcodes.PUSHA:
            self._op_pusha(sub_opcode)
        elif opcode == Opcodes.POPA:
            self._op_popa(sub_opcode)
        elif opcode == Opcodes.CALL:
            self._op_call(sub_opcode)
        elif opcode == Opcodes.RET:
            self._op_ret(sub_opcode)
        elif opcode == Opcodes.INT:
            self._op_int(sub_opcode)
        elif opcode == Opcodes.LOAD:
            self._op_load(sub_opcode)
        elif opcode == Opcodes.STORE:
            self._op_store(sub_opcode)
        elif opcode == Opcodes.IN:
            self._op_in(sub_opcode)
        elif opcode == Opcodes.OUT:
            self._op_out(sub_opcode)
        elif opcode == Opcodes.STI:
            self._op_sti(sub_opcode)
        elif opcode == Opcodes.CLI:
            self._op_cli(sub_opcode)
        elif opcode == Opcodes.CLC:
            self._op_clc(sub_opcode)
        elif opcode == Opcodes.STC:
            self._op_stc(sub_opcode)
        elif opcode == Opcodes.CMC:
            self._op_cmc(sub_opcode)
        elif opcode == Opcodes.CLD:
            self._op_cld(sub_opcode)
        elif opcode == Opcodes.STD:
            self._op_std(sub_opcode)
        else:
            self.state = VMState.ERROR
            print(f"[VM Error] Unknown extended opcode: {opcode}")
        
        self.cycle_count += 1
    
    def _get_imm32(self, offset=2):
        if self.pc + offset + 3 >= len(self.program):
            return 0
        val = struct.unpack('<I', bytes(self.program[self.pc+offset:self.pc+offset+4]))[0]
        return val
    
    def _set_flags_arithmetic(self, result: int, carry: bool = False, overflow: bool = False):
        self.flag_zero = (result == 0)
        self.flag_negative = (result & 0x80000000) != 0
        self.flag_carry = carry
        self.flag_overflow = overflow
    
    def _op_add(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        a = self.registers[dst]
        b = self.registers[src]
        result = a + b
        
        carry = (result > 0xFFFFFFFF)
        overflow = ((a & 0x80000000) == (b & 0x80000000)) and \
                   ((result & 0x80000000) != (a & 0x80000000))
        
        self.registers[dst] = result & 0xFFFFFFFF
        self._set_flags_arithmetic(result, carry, overflow)
    
    def _op_sub(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        a = self.registers[dst]
        b = self.registers[src]
        result = a - b
        
        carry = (a < b)
        overflow = ((a & 0x80000000) != (b & 0x80000000)) and \
                   ((result & 0x80000000) != (a & 0x80000000))
        
        self.registers[dst] = result & 0xFFFFFFFF
        self._set_flags_arithmetic(result, carry, overflow)
    
    def _op_mul(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        a = self.registers[dst]
        b = self.registers[src]
        result = a * b
        
        self.registers[dst] = result & 0xFFFFFFFF
        self._set_flags_arithmetic(result)
    
    def _op_div(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        divisor = self.registers[src]
        if divisor == 0:
            self._int_divide_by_zero()
            return
        
        dividend = self.registers[dst]
        result = dividend // divisor
        
        self.registers[dst] = result & 0xFFFFFFFF
        self._set_flags_arithmetic(result)
    
    def _op_mod(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        divisor = self.registers[src]
        if divisor == 0:
            self._int_divide_by_zero()
            return
        
        dividend = self.registers[dst]
        result = dividend % divisor
        
        self.registers[dst] = result & 0xFFFFFFFF
        self._set_flags_arithmetic(result)
    
    def _op_inc(self, sub_opcode):
        reg = sub_opcode & 0x1F
        self.pc += 2
        
        self.registers[reg] = (self.registers[reg] + 1) & 0xFFFFFFFF
        self._set_flags_arithmetic(self.registers[reg])
    
    def _op_dec(self, sub_opcode):
        reg = sub_opcode & 0x1F
        self.pc += 2
        
        self.registers[reg] = (self.registers[reg] - 1) & 0xFFFFFFFF
        self._set_flags_arithmetic(self.registers[reg])
    
    def _op_neg(self, sub_opcode):
        reg = sub_opcode & 0x1F
        self.pc += 2
        
        self.registers[reg] = (-self.registers[reg]) & 0xFFFFFFFF
        self._set_flags_arithmetic(self.registers[reg])
    
    def _op_abs(self, sub_opcode):
        reg = sub_opcode & 0x1F
        self.pc += 2
        
        val = self.registers[reg]
        if val & 0x80000000:
            self.registers[reg] = (-val) & 0xFFFFFFFF
        
        self._set_flags_arithmetic(self.registers[reg])
    
    def _op_and(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        result = self.registers[dst] & self.registers[src]
        self.registers[dst] = result
        self._set_flags_arithmetic(result)
    
    def _op_or(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        result = self.registers[dst] | self.registers[src]
        self.registers[dst] = result
        self._set_flags_arithmetic(result)
    
    def _op_xor(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        result = self.registers[dst] ^ self.registers[src]
        self.registers[dst] = result
        self._set_flags_arithmetic(result)
    
    def _op_not(self, sub_opcode):
        reg = sub_opcode & 0x1F
        self.pc += 2
        
        result = ~self.registers[reg] & 0xFFFFFFFF
        self.registers[reg] = result
        self._set_flags_arithmetic(result)
    
    def _op_shl(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        shift = self.registers[src] & 0x1F
        result = (self.registers[dst] << shift) & 0xFFFFFFFF
        self.registers[dst] = result
        self._set_flags_arithmetic(result)
    
    def _op_shr(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        shift = self.registers[src] & 0x1F
        result = (self.registers[dst] >> shift) & 0xFFFFFFFF
        self.registers[dst] = result
        self._set_flags_arithmetic(result)
    
    def _op_sar(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        shift = self.registers[src] & 0x1F
        val = self.registers[dst]
        
        if val & 0x80000000:
            mask = (0xFFFFFFFF << (32 - shift)) & 0xFFFFFFFF
            result = (val >> shift) | mask
        else:
            result = val >> shift
        
        self.registers[dst] = result & 0xFFFFFFFF
        self._set_flags_arithmetic(result)
    
    def _op_cmp(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        a = self.registers[dst]
        b = self.registers[src]
        result = a - b
        
        self.flag_zero = (a == b)
        self.flag_negative = (result & 0x80000000) != 0
        self.flag_carry = (a < b)
        
        signed_a = a if a < 0x80000000 else a - 0x100000000
        signed_b = b if b < 0x80000000 else b - 0x100000000
        self.flag_overflow = ((signed_a > 0 and signed_b < 0 and signed_a - signed_b < 0) or
                              (signed_a < 0 and signed_b > 0 and signed_a - signed_b > 0))
    
    def _op_test(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        result = self.registers[dst] & self.registers[src]
        self.flag_zero = (result == 0)
        self.flag_negative = (result & 0x80000000) != 0
        self.flag_carry = False
        self.flag_overflow = False
    
    def _op_jmp(self, sub_opcode):
        mode = sub_opcode & 0x03
        
        if mode == 0:
            target = self._get_imm32(offset=2)
            self.pc = target
        elif mode == 1:
            reg = (sub_opcode >> 2) & 0x1F
            self.pc = self.registers[reg]
        elif mode == 2:
            rel = self._get_imm32(offset=2)
            self.pc = self.pc + 6 + rel
    
    def _op_je(self, sub_opcode):
        self.pc += 2
        if self.flag_zero:
            rel = self._get_imm32(offset=0)
            self.pc = self.pc + 4 + rel
    
    def _op_jne(self, sub_opcode):
        self.pc += 2
        if not self.flag_zero:
            rel = self._get_imm32(offset=0)
            self.pc = self.pc + 4 + rel
    
    def _op_jl(self, sub_opcode):
        self.pc += 2
        if self.flag_negative != self.flag_overflow:
            rel = self._get_imm32(offset=0)
            self.pc = self.pc + 4 + rel
    
    def _op_jle(self, sub_opcode):
        self.pc += 2
        if self.flag_zero or (self.flag_negative != self.flag_overflow):
            rel = self._get_imm32(offset=0)
            self.pc = self.pc + 4 + rel
    
    def _op_jg(self, sub_opcode):
        self.pc += 2
        if not self.flag_zero and (self.flag_negative == self.flag_overflow):
            rel = self._get_imm32(offset=0)
            self.pc = self.pc + 4 + rel
    
    def _op_jge(self, sub_opcode):
        self.pc += 2
        if self.flag_negative == self.flag_overflow:
            rel = self._get_imm32(offset=0)
            self.pc = self.pc + 4 + rel
    
    def _op_mov(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        self.registers[dst] = self.registers[src]
    
    def _op_lea(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        addr = self.registers[src]
        self.registers[dst] = addr
    
    def _op_xchg(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        temp = self.registers[dst]
        self.registers[dst] = self.registers[src]
        self.registers[src] = temp
    
    def _op_push(self, sub_opcode):
        reg = sub_opcode & 0x1F
        self.pc += 2
        
        sp = self.registers[self.SPECIAL_REGS["R_SP"]]
        if sp >= 4:
            sp -= 4
            val = self.registers[reg]
            self.stack[sp] = val & 0xFF
            self.stack[sp+1] = (val >> 8) & 0xFF
            self.stack[sp+2] = (val >> 16) & 0xFF
            self.stack[sp+3] = (val >> 24) & 0xFF
            self.registers[self.SPECIAL_REGS["R_SP"]] = sp
    
    def _op_pop(self, sub_opcode):
        reg = sub_opcode & 0x1F
        self.pc += 2
        
        sp = self.registers[self.SPECIAL_REGS["R_SP"]]
        if sp + 4 <= self.STACK_SIZE:
            val = (self.stack[sp] |
                   (self.stack[sp+1] << 8) |
                   (self.stack[sp+2] << 16) |
                   (self.stack[sp+3] << 24))
            self.registers[reg] = val
            self.registers[self.SPECIAL_REGS["R_SP"]] = sp + 4
    
    def _op_pusha(self, sub_opcode):
        self.pc += 2
        
        for reg in range(16):
            sp = self.registers[self.SPECIAL_REGS["R_SP"]]
            if sp >= 4:
                sp -= 4
                val = self.registers[reg]
                self.stack[sp] = val & 0xFF
                self.stack[sp+1] = (val >> 8) & 0xFF
                self.stack[sp+2] = (val >> 16) & 0xFF
                self.stack[sp+3] = (val >> 24) & 0xFF
                self.registers[self.SPECIAL_REGS["R_SP"]] = sp
    
    def _op_popa(self, sub_opcode):
        self.pc += 2
        
        for reg in reversed(range(16)):
            sp = self.registers[self.SPECIAL_REGS["R_SP"]]
            if sp + 4 <= self.STACK_SIZE:
                val = (self.stack[sp] |
                       (self.stack[sp+1] << 8) |
                       (self.stack[sp+2] << 16) |
                       (self.stack[sp+3] << 24))
                self.registers[reg] = val
                self.registers[self.SPECIAL_REGS["R_SP"]] = sp + 4
    
    def _op_call(self, sub_opcode):
        mode = sub_opcode & 0x03
        self.pc += 2
        
        sp = self.registers[self.SPECIAL_REGS["R_SP"]]
        if sp >= 4:
            sp -= 4
            return_addr = self.pc + 4
            self.stack[sp] = return_addr & 0xFF
            self.stack[sp+1] = (return_addr >> 8) & 0xFF
            self.stack[sp+2] = (return_addr >> 16) & 0xFF
            self.stack[sp+3] = (return_addr >> 24) & 0xFF
            self.registers[self.SPECIAL_REGS["R_SP"]] = sp
        
        if mode == 0:
            target = self._get_imm32(offset=0)
            self.pc = target
        elif mode == 1:
            reg = (sub_opcode >> 2) & 0x1F
            self.pc = self.registers[reg]
    
    def _op_ret(self, sub_opcode):
        self.pc += 2
        
        sp = self.registers[self.SPECIAL_REGS["R_SP"]]
        if sp + 4 <= self.STACK_SIZE:
            return_addr = (self.stack[sp] |
                          (self.stack[sp+1] << 8) |
                          (self.stack[sp+2] << 16) |
                          (self.stack[sp+3] << 24))
            self.registers[self.SPECIAL_REGS["R_SP"]] = sp + 4
            self.pc = return_addr
    
    def _op_int(self, sub_opcode):
        int_num = sub_opcode
        self.pc += 2
        
        handler = self.interrupt_table.get(int_num)
        if handler:
            handler()
    
    def _op_load(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        addr = self.registers[src]
        if 0 <= addr < self.HEAP_SIZE - 3:
            val = (self.heap[addr] |
                   (self.heap[addr+1] << 8) |
                   (self.heap[addr+2] << 16) |
                   (self.heap[addr+3] << 24))
            self.registers[dst] = val
    
    def _op_store(self, sub_opcode):
        dst = sub_opcode & 0x1F
        src = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        addr = self.registers[dst]
        val = self.registers[src]
        if 0 <= addr < self.HEAP_SIZE - 3:
            self.heap[addr] = val & 0xFF
            self.heap[addr+1] = (val >> 8) & 0xFF
            self.heap[addr+2] = (val >> 16) & 0xFF
            self.heap[addr+3] = (val >> 24) & 0xFF
    
    def _op_in(self, sub_opcode):
        dst = sub_opcode & 0x1F
        port = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        if port in self.io_handlers:
            val = self.io_handlers[port]()
            self.registers[dst] = val
    
    def _op_out(self, sub_opcode):
        src = sub_opcode & 0x1F
        port = (sub_opcode >> 5) & 0x1F
        self.pc += 2
        
        if port in self.io_handlers:
            self.io_handlers[port](self.registers[src])
    
    def _op_sti(self, sub_opcode):
        self.pc += 1
        self.flag_interrupt = True
    
    def _op_cli(self, sub_opcode):
        self.pc += 1
        self.flag_interrupt = False
    
    def _op_clc(self, sub_opcode):
        self.pc += 1
        self.flag_carry = False
    
    def _op_stc(self, sub_opcode):
        self.pc += 1
        self.flag_carry = True
    
    def _op_cmc(self, sub_opcode):
        self.pc += 1
        self.flag_carry = not self.flag_carry
    
    def _op_cld(self, sub_opcode):
        self.pc += 1
        self.flag_direction = False
    
    def _op_std(self, sub_opcode):
        self.pc += 1
        self.flag_direction = True
    
    def load_extended_program(self, instructions: List[Dict]):
        """加载传统CPU指令程序"""
        self.program = bytearray()
        
        for instr in instructions:
            opcode = instr.get("opcode", 0)
            operands = instr.get("operands", [])
            
            if opcode < 64:
                modifier = instr.get("modifier", 0)
                byte1 = ((opcode & 0x3F) << 2) | ((modifier >> 4) & 0x03)
                byte2 = modifier & 0x0F
                self.program.extend([byte1, byte2])
                for op in operands[:2]:
                    if isinstance(op, int):
                        self.program.append(op & 0xFF)
                    else:
                        self.program.append(0)
            else:
                sub_opcode = instr.get("sub_opcode", 0)
                self.program.append(opcode)
                self.program.append(sub_opcode)
                
                if "imm" in instr:
                    imm = instr["imm"]
                    self.program.extend([
                        imm & 0xFF,
                        (imm >> 8) & 0xFF,
                        (imm >> 16) & 0xFF,
                        (imm >> 24) & 0xFF,
                    ])
        
        self.pc = 0
        self.state = VMState.INIT
    
    def assemble_extended(self, asm_source: str):
        """汇编传统CPU指令"""
        instructions = []
        
        lines = asm_source.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('#'):
                continue
            
            parts = line.split()
            if not parts:
                continue
            
            mnemonic = parts[0].upper()
            operands_str = ' '.join(parts[1:]) if len(parts) > 1 else ''
            
            opcode_map = {
                'NOP': Opcodes.NOP,
                'HLT': Opcodes.HLT,
                'ADD': Opcodes.ADD,
                'SUB': Opcodes.SUB,
                'MUL': Opcodes.MUL,
                'DIV': Opcodes.DIV,
                'MOD': Opcodes.MOD,
                'INC': Opcodes.INC,
                'DEC': Opcodes.DEC,
                'NEG': Opcodes.NEG,
                'ABS': Opcodes.ABS,
                'AND': Opcodes.AND,
                'OR': Opcodes.OR,
                'XOR': Opcodes.XOR,
                'NOT': Opcodes.NOT,
                'SHL': Opcodes.SHL,
                'SHR': Opcodes.SHR,
                'SAR': Opcodes.SAR,
                'CMP': Opcodes.CMP,
                'TEST': Opcodes.TEST,
                'JMP': Opcodes.JMP,
                'JE': Opcodes.JE,
                'JNE': Opcodes.JNE,
                'JZ': Opcodes.JE,
                'JNZ': Opcodes.JNE,
                'JL': Opcodes.JL,
                'JLE': Opcodes.JLE,
                'JG': Opcodes.JG,
                'JGE': Opcodes.JGE,
                'MOV': Opcodes.MOV,
                'LEA': Opcodes.LEA,
                'XCHG': Opcodes.XCHG,
                'PUSH': Opcodes.PUSH,
                'POP': Opcodes.POP,
                'PUSHA': Opcodes.PUSHA,
                'POPA': Opcodes.POPA,
                'CALL': Opcodes.CALL,
                'RET': Opcodes.RET,
                'INT': Opcodes.INT,
                'LOAD': Opcodes.LOAD,
                'STORE': Opcodes.STORE,
                'IN': Opcodes.IN,
                'OUT': Opcodes.OUT,
                'STI': Opcodes.STI,
                'CLI': Opcodes.CLI,
                'CLC': Opcodes.CLC,
                'STC': Opcodes.STC,
                'CMC': Opcodes.CMC,
                'CLD': Opcodes.CLD,
                'STD': Opcodes.STD,
            }
            
            if mnemonic not in opcode_map:
                continue
            
            opcode = opcode_map[mnemonic]
            sub_opcode = 0
            imm_value = None
            
            operands = []
            if operands_str:
                operand_parts = [p.strip() for p in operands_str.split(',')]
                
                for i, op in enumerate(operand_parts[:2]):
                    op = op.strip()
                    if op.startswith('R') or op.startswith('r'):
                        try:
                            reg_idx = int(op[1:])
                            operands.append(('reg', reg_idx))
                        except ValueError:
                            continue
                    elif op.startswith('#'):
                        try:
                            val = int(op[1:], 0)
                            operands.append(('imm', val))
                            imm_value = val
                        except ValueError:
                            continue
                    elif op.startswith('[') and op.endswith(']'):
                        reg_part = op[1:-1].strip()
                        if reg_part.startswith('R') or reg_part.startswith('r'):
                            try:
                                reg_idx = int(reg_part[1:])
                                operands.append(('mem', reg_idx))
                            except ValueError:
                                continue
                    else:
                        try:
                            val = int(op, 0)
                            operands.append(('imm', val))
                            imm_value = val
                        except ValueError:
                            continue
            
            if len(operands) >= 2:
                if operands[0][0] == 'reg' and operands[1][0] == 'reg':
                    sub_opcode = (operands[1][1] << 5) | operands[0][1]
                elif operands[0][0] == 'reg' and operands[1][0] == 'imm':
                    sub_opcode = (0 << 5) | operands[0][1]
            elif len(operands) == 1:
                if operands[0][0] == 'reg':
                    sub_opcode = operands[0][1]
                elif operands[0][0] == 'imm':
                    sub_opcode = 0
                    imm_value = operands[0][1]
            
            instr = {"opcode": opcode, "sub_opcode": sub_opcode}
            if imm_value is not None:
                instr["imm"] = imm_value
            
            instructions.append(instr)
        
        self.load_extended_program(instructions)
        return instructions
