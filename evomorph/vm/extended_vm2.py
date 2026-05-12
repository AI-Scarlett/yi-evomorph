#!/usr/bin/env python3
"""
扩展的易衍虚拟机 v2 - 重新设计指令编码
- 使用高2位作为指令类型标记
- 00xxxxxx: 扩展/预留 (当前触发ERROR)
- 01xxxxxx: 传统CPU指令 (Native)
- 10xxxxxx: 六十四卦指令 (IChing, opcode 0-63)
- 11xxxxxx: 长指令/多字节 (当前触发ERROR)

完全自举版本 - 支持标签、CALL/RET、完整条件跳转
"""

import sys
import os
import struct
from enum import IntEnum
from typing import Dict, List, Any, Optional, Callable, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from evomorph.vm.virtual_machine import IChingVM, VMState

# P9: C 原生 VM 桥接（可选，用于消除 Python 执行路径）
try:
    from .cbridge import CBridgeVM, VM_INIT, VM_RUNNING, VM_PAUSED, VM_HALTED, VM_ERROR
    _C_VM_AVAILABLE = True
except Exception:
    _C_VM_AVAILABLE = False
    CBridgeVM = None


class InstrType(IntEnum):
    ICHING = 0
    NATIVE = 1
    EXTENDED = 2
    LONG = 3


class NativeOpcodes:
    NOP = 0x00
    HLT = 0x01
    
    ADD = 0x08
    SUB = 0x09
    MUL = 0x0A
    DIV = 0x0B
    MOD = 0x0C
    INC = 0x0D
    DEC = 0x0E
    NEG = 0x0F
    
    AND = 0x10
    OR = 0x11
    XOR = 0x12
    NOT = 0x13
    SHL = 0x14
    SHR = 0x15
    SAR = 0x16
    
    CMP = 0x18
    CMPI = 0x19
    TEST = 0x1A
    
    JMP = 0x20
    JE = 0x21
    JNE = 0x22
    JL = 0x23
    JLE = 0x24
    JG = 0x25
    JGE = 0x26
    JC = 0x27
    JNC = 0x28
    
    MOV = 0x30
    LEA = 0x31
    XCHG = 0x32
    MOVI = 0x33
    
    LDR = 0x34
    STR = 0x35
    LDRB = 0x36
    STRB = 0x37
    
    PUSH = 0x38
    POP = 0x39
    PUSHA = 0x3A
    POPA = 0x3B
    
    CALL = 0x3C
    RET = 0x3D
    INT = 0x3E
    IRET = 0x3F


class ExtendedIChingVM2(IChingVM):
    NUM_REGISTERS = 32
    
    SP_REG = 29
    FP_REG = 28
    LR_REG = 30
    
    ICHING_OPCODE_MAP = {
        63: "CREA", 0: "RECV", 17: "ALLOC", 34: "SPRT",
        23: "WAIT", 58: "LOCK", 2: "BRANCH", 16: "MERGE",
        55: "PREFETCH", 59: "STEP", 7: "FLUSH", 56: "HALT",
        61: "FELLOWSHIP", 47: "ABUNDANCE", 4: "YIELD",
        8: "SPECULATE", 25: "FOLLOWING", 38: "MUT",
        3: "APPROACH", 48: "CONTEMPLATE", 41: "BITE",
        37: "ADORN", 32: "STRIP", 1: "RETURN",
        57: "INTRINSIC", 39: "BARRIER", 33: "NOURISH",
        30: "OVERLOAD", 18: "TRAP", 45: "ILLUMINATE",
        28: "SENSE", 14: "PERSIST", 60: "RETREAT",
        15: "THRUST", 40: "ADVANCE", 5: "OBSCURE",
        53: "BIND", 43: "CONVERT", 20: "LAME",
        10: "UNLOCK", 35: "REDUCE", 49: "INCREASE",
        31: "BREAK", 62: "MATE", 24: "GATHER",
        6: "PUSH_UP", 26: "TRAPPED", 22: "WELL",
        29: "REPLACE", 46: "CAST", 9: "SHOCK",
        36: "STILL", 52: "GRADUAL", 11: "MISMATCH",
        13: "ABOUND", 44: "TRAVEL", 54: "PENETRATE",
        27: "JOY", 50: "DISPERSE", 19: "THROTTLE",
        51: "TRUST", 12: "MICRO", 21: "SYNC", 42: "FUTU",
    }
    
    ICHING_OPCODE_REVERSE = {v: k for k, v in ICHING_OPCODE_MAP.items()}
    
    def __init__(self):
        super().__init__()
        self.registers = [0] * self.NUM_REGISTERS
        self.flag_direction = False
        self.flag_interrupt = True
        self.interrupt_table = {}
        self.syscall_table = {}
        self.output_buffer = []
        self._cvm = None  # P9: C VM bridge (lazy init)
        self._init_special_regs()
        self._setup_default_interrupts()
        self._setup_native_handlers()
    
    def reset(self):
        self.pc = 0
        self.state = VMState.INIT
        self.cycle_count = 0
        self.energy_cost = 0
        self.registers = [0] * self.NUM_REGISTERS
        self.flag_zero = False
        self.flag_carry = False
        self.flag_negative = False
        self.flag_overflow = False
        self.flag_direction = False
        self.flag_interrupt = True
        self.heap = bytearray(self.HEAP_SIZE)
        self.stack = bytearray(self.STACK_SIZE)
        self.program = bytearray()
        self.output_buffer = []
        self._init_special_regs()

    # === P9: C 原生 VM 桥接（消除 Python 执行路径） ===

    def _has_c_vm(self) -> bool:
        """C VM 共享库是否可用"""
        return _C_VM_AVAILABLE and CBridgeVM is not None

    def _ensure_cvm(self):
        """惰性初始化 C VM bridge"""
        if self._cvm is None and self._has_c_vm():
            self._cvm = CBridgeVM()

    def _sync_to_c(self):
        """将 Python VM 状态复制到 C VM"""
        if self._cvm is None:
            return
        c = self._cvm._vm.contents
        # 寄存器
        for i in range(self.NUM_REGISTERS):
            c.regs[i] = self.registers[i]
        # Heap
        if len(self.heap) > 0:
            self._cvm.heap_write(0, bytes(self.heap))
        # 程序
        if len(self.program) > 0:
            self._cvm.load_program(bytes(self.program))
        # PC & 状态
        c.pc = self.pc
        c.state = int(self.state)

    def _sync_from_c(self):
        """将 C VM 状态复制回 Python VM"""
        if self._cvm is None:
            return
        c = self._cvm._vm.contents
        # 寄存器
        self.registers = [c.regs[i] for i in range(self.NUM_REGISTERS)]
        # Heap（部分回读：C heap 只同步前面 HEAP_SIZE 字节）
        new_heap = self._cvm.heap_read(0, min(self.HEAP_SIZE, 1048576))
        if new_heap:
            self.heap[:len(new_heap)] = new_heap
        # PC & 状态
        self.pc = c.pc
        raw_state = c.state
        try:
            self.state = VMState(raw_state)
        except ValueError:
            self.state = VMState.ERROR
        # 标志位
        self.flag_zero = bool(c.flag_zero)
        self.flag_carry = bool(c.flag_carry)
        self.flag_negative = bool(c.flag_negative)
        self.flag_overflow = bool(c.flag_overflow)
        # 周期计数
        self.cycle_count = c.cycle_count
        # 输出缓冲
        c_out = self._cvm.get_output()
        if c_out:
            self.output_buffer.extend(list(c_out))

    def run(self, max_cycles=None):
        """P9: 通过 C 原生 VM 加速执行。失败时回退到 Python VM。"""
        if self._has_c_vm():
            try:
                self._ensure_cvm()
                self.state = VMState.RUNNING
                self._sync_to_c()
                max_c = max_cycles if max_cycles else 10000000
                self._cvm.run(max_c)
                self._sync_from_c()
                return self.state
            except Exception:
                pass  # 回退到 Python VM
        return super().run(max_cycles)

    def step(self):
        """P9: 单步执行（通过 C VM 桥接，支持逐步跟踪）"""
        if self._has_c_vm():
            try:
                self._ensure_cvm()
                if self.state not in (VMState.RUNNING, VMState.PAUSED):
                    self.state = VMState.RUNNING
                self._sync_to_c()
                self._cvm.step()
                self._sync_from_c()
                return
            except Exception:
                pass  # 回退到 Python VM
        return super().step()

    # === P9 END ===
    
    def _init_special_regs(self):
        self.registers[self.SP_REG] = self.STACK_SIZE
        self.registers[self.FP_REG] = self.STACK_SIZE
    
    def _setup_default_interrupts(self):
        self.interrupt_table[0x00] = self._int_divide_by_zero
        self.interrupt_table[0x01] = self._int_single_step
        self.interrupt_table[0x03] = self._int_breakpoint
        self.interrupt_table[0x0E] = self._int_page_fault
        self.interrupt_table[0x20] = self._int_timer
        self.interrupt_table[0x80] = self._int_syscall
        self._setup_default_syscalls()
    
    def _setup_default_syscalls(self):
        self.syscall_table[0] = self._sys_print_char
        self.syscall_table[1] = self._sys_print_string
        self.syscall_table[2] = self._sys_read_char
        self.syscall_table[3] = self._sys_open_file
        self.syscall_table[4] = self._sys_read_file
        self.syscall_table[5] = self._sys_write_file
        self.syscall_table[6] = self._sys_close_file
        self.syscall_table[7] = self._sys_exit
        self.syscall_table[8] = self._sys_get_time
        self.syscall_table[9] = self._sys_heap_alloc
    
    def _sys_print_char(self):
        ch = self.registers[1] & 0xFF
        self.output_buffer.append(chr(ch))
    
    def _sys_print_string(self):
        addr = self.registers[1]
        while 0 <= addr < self.HEAP_SIZE and self.heap[addr] != 0:
            self.output_buffer.append(chr(self.heap[addr]))
            addr += 1
    
    def _sys_read_char(self):
        self.registers[1] = 0
    
    def _sys_open_file(self):
        self.registers[1] = 0xFFFFFFFF
    
    def _sys_read_file(self):
        self.registers[1] = 0
    
    def _sys_write_file(self):
        self.registers[1] = 0
    
    def _sys_close_file(self):
        self.registers[1] = 0
    
    def _sys_exit(self):
        self.state = VMState.HALTED
    
    def _sys_get_time(self):
        import time
        self.registers[1] = int(time.time()) & 0xFFFFFFFF
    
    def _sys_heap_alloc(self):
        size = self.registers[1]
        if self.heap_ptr + size <= self.HEAP_SIZE:
            addr = self.heap_ptr
            self.heap_ptr += size
            self.registers[1] = addr
        else:
            self.registers[1] = 0
    
    def _int_divide_by_zero(self):
        self.state = VMState.ERROR
    
    def _int_single_step(self):
        self.state = VMState.PAUSED
    
    def _int_breakpoint(self):
        self.state = VMState.PAUSED
    
    def _int_page_fault(self):
        self.state = VMState.ERROR
    
    def _int_timer(self):
        pass
    
    def _int_syscall(self):
        syscall_num = self.registers[0]
        handler = self.syscall_table.get(syscall_num)
        if handler:
            handler(self)
    
    def register_syscall(self, num: int, handler: Callable):
        self.syscall_table[num] = handler
    
    def _setup_native_handlers(self):
        self.native_handlers = {
            NativeOpcodes.NOP: self._native_nop,
            NativeOpcodes.HLT: self._native_hlt,
            NativeOpcodes.ADD: self._native_add,
            NativeOpcodes.SUB: self._native_sub,
            NativeOpcodes.MUL: self._native_mul,
            NativeOpcodes.DIV: self._native_div,
            NativeOpcodes.MOD: self._native_mod,
            NativeOpcodes.INC: self._native_inc,
            NativeOpcodes.DEC: self._native_dec,
            NativeOpcodes.NEG: self._native_neg,
            NativeOpcodes.AND: self._native_and,
            NativeOpcodes.OR: self._native_or,
            NativeOpcodes.XOR: self._native_xor,
            NativeOpcodes.NOT: self._native_not,
            NativeOpcodes.SHL: self._native_shl,
            NativeOpcodes.SHR: self._native_shr,
            NativeOpcodes.SAR: self._native_sar,
            NativeOpcodes.CMP: self._native_cmp,
            NativeOpcodes.CMPI: self._native_cmpi,
            NativeOpcodes.TEST: self._native_test,
            NativeOpcodes.JMP: self._native_jmp,
            NativeOpcodes.JE: self._native_je,
            NativeOpcodes.JNE: self._native_jne,
            NativeOpcodes.JL: self._native_jl,
            NativeOpcodes.JLE: self._native_jle,
            NativeOpcodes.JG: self._native_jg,
            NativeOpcodes.JGE: self._native_jge,
            NativeOpcodes.JC: self._native_jc,
            NativeOpcodes.JNC: self._native_jnc,
            NativeOpcodes.MOV: self._native_mov,
            NativeOpcodes.MOVI: self._native_movi,
            NativeOpcodes.LEA: self._native_lea,
            NativeOpcodes.XCHG: self._native_xchg,
            NativeOpcodes.PUSH: self._native_push,
            NativeOpcodes.POP: self._native_pop,
            NativeOpcodes.PUSHA: self._native_pusha,
            NativeOpcodes.POPA: self._native_popa,
            NativeOpcodes.CALL: self._native_call,
            NativeOpcodes.RET: self._native_ret,
            NativeOpcodes.INT: self._native_int,
            NativeOpcodes.IRET: self._native_iret,
            NativeOpcodes.LDR: self._native_ldr,
            NativeOpcodes.STR: self._native_str,
            NativeOpcodes.LDRB: self._native_ldrb,
            NativeOpcodes.STRB: self._native_strb,
        }
    
    def _step(self):
        if self.pc >= len(self.program):
            self.state = VMState.HALTED
            return
        
        byte1 = self.program[self.pc]
        instr_type = (byte1 >> 6) & 0x03
        
        if instr_type == 0x02:
            self._step_iching(byte1)
        elif instr_type == 0x01:
            self._step_native(byte1)
        elif instr_type == 0x00:
            self.state = VMState.ERROR
        else:
            self._step_long(byte1)
    
    def _step_iching(self, byte1):
        if self.pc + 3 >= len(self.program):
            self.state = VMState.HALTED
            return
        
        opcode = byte1 & 0x3F
        modifier = self.program[self.pc + 1]
        op1 = self.program[self.pc + 2]
        op2 = self.program[self.pc + 3]
        
        self.pc += 4
        
        sub_op = modifier & 0x3F
        ext_mode = (modifier >> 6) & 0x03
        
        if ext_mode == 0:
            dst = op1 & 0x1F
            src = op2 & 0x1F
            imm = None
        elif ext_mode == 1:
            dst = op1 & 0x1F
            src = op2 & 0x1F
            imm = None
        elif ext_mode == 2:
            dst = op1 & 0x1F
            src = op2 & 0x1F
            if self.pc + 3 < len(self.program):
                imm = struct.unpack('<I', bytes(self.program[self.pc:self.pc+4]))[0]
                self.pc += 4
            else:
                self.state = VMState.ERROR
                return
        else:
            dst = op1 & 0x1F
            src = op2 & 0x1F
            imm = None
        
        if sub_op == 0 and ext_mode == 0:
            handler = self._OPCODE_HANDLERS.get(opcode)
            if handler:
                handler(self, modifier, [op1, op2])
                self.energy_cost += self._instruction_energy(opcode)
            else:
                self.state = VMState.ERROR
            return
        
        self._iching_extended(opcode, sub_op, ext_mode, dst, src, imm)
        self.energy_cost += self._instruction_energy(opcode)
    
    def _iching_extended(self, opcode, sub_op, ext_mode, dst, src, imm):
        if opcode == 63:  # CREA
            if sub_op == 1:  # MOVI
                self.registers[dst] = imm if imm is not None else 0
            elif sub_op == 2:  # NOP
                pass
            else:
                self._iching_crea_ext(sub_op, dst, src, imm)
        elif opcode == 0:  # RECV
            if sub_op == 1:  # LDR
                addr = self.registers[src]
                if 0 <= addr <= self.HEAP_SIZE - 4:
                    self.registers[dst] = self._load_word_heap(addr)
                else:
                    self.registers[dst] = 0
            elif sub_op == 2:  # LDRB
                addr = self.registers[src]
                if 0 <= addr < self.HEAP_SIZE:
                    self.registers[dst] = self.heap[addr]
                else:
                    self.registers[dst] = 0
            else:
                self._iching_recv_ext(sub_op, dst, src, imm)
        elif opcode == 61:  # FELLOWSHIP
            if sub_op == 1:  # CMP
                a = self.registers[dst]
                b = self.registers[src] if imm is None else imm
                result = a - b
                self.flag_zero = (a == b)
                self.flag_negative = (result & 0x80000000) != 0
                self.flag_carry = (a < b)
            elif sub_op == 2:  # CMPI
                a = self.registers[dst]
                b = imm if imm is not None else 0
                result = a - b
                self.flag_zero = (a == b)
                self.flag_negative = (result & 0x80000000) != 0
                self.flag_carry = (a < b)
            else:
                self.registers[dst] = self.registers[src]
        elif opcode == 17:  # ALLOC
            if sub_op == 1:  # STR
                addr = self.registers[dst]
                if 0 <= addr <= self.HEAP_SIZE - 4:
                    self._store_word_heap(addr, self.registers[src])
            elif sub_op == 2:  # STRB
                addr = self.registers[dst]
                if 0 <= addr < self.HEAP_SIZE:
                    self.heap[addr] = self.registers[src] & 0xFF
            else:
                if self.heap_ptr + (src if src > 0 else 256) <= self.HEAP_SIZE:
                    addr = self.heap_ptr + 1
                    self.heap_ptr += (src if src > 0 else 256)
                    self.registers[dst] = addr
                else:
                    self.registers[dst] = 0
        elif opcode == 2:  # BRANCH
            if sub_op == 1:  # JMP
                target = imm if imm is not None else self.registers[src]
                self.pc = target
            elif sub_op == 2:  # JE
                if self.flag_zero:
                    target = imm if imm is not None else self.registers[src]
                    self.pc = target
            elif sub_op == 3:  # JNE
                if not self.flag_zero:
                    target = imm if imm is not None else self.registers[src]
                    self.pc = target
            elif sub_op == 4:  # JL (unsigned: carry set)
                if self.flag_carry:
                    target = imm if imm is not None else self.registers[src]
                    self.pc = target
            elif sub_op == 5:  # JLE (unsigned: carry or zero)
                if self.flag_carry or self.flag_zero:
                    target = imm if imm is not None else self.registers[src]
                    self.pc = target
            elif sub_op == 6:  # JG (unsigned: !carry && !zero)
                if not self.flag_carry and not self.flag_zero:
                    target = imm if imm is not None else self.registers[src]
                    self.pc = target
            elif sub_op == 7:  # JGE (unsigned: !carry)
                if not self.flag_carry:
                    target = imm if imm is not None else self.registers[src]
                    self.pc = target
            else:
                if self.registers[dst] != 0:
                    self.pc = imm if imm is not None else self.registers[src]
        elif opcode == 47:  # ABUNDANCE
            if sub_op == 1:  # CALL
                self.call_stack.append(self.pc)
                self.registers[30] = self.pc  # LR
                target = imm if imm is not None else self.registers[src]
                self.pc = target
            else:
                addr = self.registers[dst]
                if 0 <= addr < self.HEAP_SIZE:
                    self.heap[addr] = self.registers[src] & 0xFF
        elif opcode == 1:  # RETURN
            if sub_op == 1:  # HLT
                self.state = VMState.HALTED
            else:
                if self.call_stack:
                    self.pc = self.call_stack.pop()
                elif self.registers[30] > 0:  # LR
                    self.pc = self.registers[30]
                else:
                    self.state = VMState.HALTED
        elif opcode == 62:  # MATE
            if sub_op == 1:  # AND
                a = self.registers[dst]
                b = self.registers[src] if imm is None else imm
                self.registers[dst] = (a & b) & 0xFFFFFFFF
            elif sub_op == 2:  # XOR
                a = self.registers[dst]
                b = self.registers[src] if imm is None else imm
                self.registers[dst] = (a ^ b) & 0xFFFFFFFF
            elif sub_op == 3:  # OR
                a = self.registers[dst]
                b = self.registers[src] if imm is None else imm
                self.registers[dst] = (a | b) & 0xFFFFFFFF
            else:
                a = self.registers[dst]
                b = self.registers[src]
                self.registers[dst] = ((a + b) // 2) & 0xFFFFFFFF
        elif opcode == 24:  # GATHER
            if sub_op == 1:  # SUB
                a = self.registers[dst]
                b = self.registers[src] if imm is None else imm
                result = a - b
                self.registers[dst] = result & 0xFFFFFFFF
                self._set_flags_arithmetic(result, a < b)
            elif sub_op == 2:  # MUL
                a = self.registers[dst]
                b = self.registers[src] if imm is None else imm
                result = a * b
                self.registers[dst] = result & 0xFFFFFFFF
            elif sub_op == 3:  # DIV
                divisor = self.registers[src] if imm is None else imm
                if divisor == 0:
                    self._int_divide_by_zero()
                    return
                result = self.registers[dst] // divisor
                self.registers[dst] = result & 0xFFFFFFFF
            elif sub_op == 4:  # MOD
                divisor = self.registers[src] if imm is None else imm
                if divisor == 0:
                    self._int_divide_by_zero()
                    return
                result = self.registers[dst] % divisor
                self.registers[dst] = result & 0xFFFFFFFF
            else:
                a = self.registers[dst]
                b = self.registers[src] if imm is None else imm
                result = a + b
                self.registers[dst] = result & 0xFFFFFFFF
                self._set_flags_arithmetic(result, result > 0xFFFFFFFF)
        elif opcode == 38:  # MUT
            if sub_op == 1:  # SHL
                a = self.registers[dst]
                b = self.registers[src] if imm is None else imm
                self.registers[dst] = (a << b) & 0xFFFFFFFF
            elif sub_op == 2:  # SHR
                a = self.registers[dst]
                b = self.registers[src] if imm is None else imm
                self.registers[dst] = (a >> b) & 0xFFFFFFFF
            elif sub_op == 3:  # SAR
                a = self.registers[dst]
                if a & 0x80000000:
                    a = a - 0x100000000
                b = self.registers[src] if imm is None else imm
                result = a >> b
                self.registers[dst] = result & 0xFFFFFFFF
            else:
                bit = self.registers[src] if imm is None else imm
                self.registers[dst] ^= (1 << bit)
                self.registers[dst] &= 0xFFFFFFFF
        elif opcode == 6:  # PUSH_UP
            if sub_op == 1:  # PUSH 32-bit
                self.registers[29] -= 4
                self._store_word_heap(self.registers[29], self.registers[dst])
            else:
                self.registers[29] -= 1
                if 0 <= self.registers[29] < self.HEAP_SIZE:
                    self.heap[self.registers[29]] = self.registers[dst] & 0xFF
        elif opcode == 22:  # WELL
            if sub_op == 1:  # POP 32-bit
                self.registers[dst] = self._load_word_heap(self.registers[29])
                self.registers[29] += 4
            else:
                if 0 <= self.registers[29] < self.HEAP_SIZE:
                    self.registers[dst] = self.heap[self.registers[29]]
                self.registers[29] += 1
        elif opcode == 48:  # CONTEMPLATE
            if sub_op == 1:  # LEA
                self.registers[dst] = imm if imm is not None else self.registers[src]
            else:
                self.registers[dst] = self.cycle_count
        elif opcode == 46:  # CAST
            if sub_op == 1:  # NOT
                self.registers[dst] = (~self.registers[dst]) & 0xFFFFFFFF
            elif sub_op == 2:  # NEG
                self.registers[dst] = (-self.registers[dst]) & 0xFFFFFFFF
            else:
                self.registers[dst] = self.registers[src]
        elif opcode == 9:  # SHOCK
            if sub_op == 1:  # INT
                int_num = imm if imm is not None else self.registers[src]
                if int_num in self.interrupt_table:
                    self.interrupt_table[int_num]()
            else:
                pass
        elif opcode == 21:  # SYNC
            if sub_op == 1:  # IRET
                if self.registers[29] + 8 <= self.HEAP_SIZE:
                    self.pc = self._load_word_heap(self.registers[29])
                    self.registers[29] += 4
                    flags = self._load_word_heap(self.registers[29])
                    self.registers[29] += 4
            else:
                pass
        elif opcode == 13:  # ABOUND
            if sub_op == 1:  # PUSHA
                for i in range(32):
                    self.registers[29] -= 4
                    self._store_word_heap(self.registers[29], self.registers[i])
            elif sub_op == 2:  # POPA
                for i in range(31, -1, -1):
                    self.registers[i] = self._load_word_heap(self.registers[29])
                    self.registers[29] += 4
            else:
                pass
        elif opcode == 27:  # JOY
            if sub_op == 1:  # TEST
                a = self.registers[dst]
                b = self.registers[src] if imm is None else imm
                result = a & b
                self._set_flags_arithmetic(result)
            else:
                pass
        elif opcode == 50:  # DISPERSE
            if sub_op == 1:  # XCHG
                tmp = self.registers[dst]
                self.registers[dst] = self.registers[src]
                self.registers[src] = tmp
            else:
                addr = self.registers[dst]
                if 0 <= addr < self.HEAP_SIZE:
                    self.heap[addr] = self.registers[src] & 0xFF
        elif opcode == 52:  # GRADUAL
            if sub_op == 1:  # DEC
                self.registers[dst] = (self.registers[dst] - 1) & 0xFFFFFFFF
            else:
                self.registers[dst] = (self.registers[dst] + 1) & 0xFFFFFFFF
        elif opcode == 12:  # MICRO
            if sub_op == 1:  # INC
                self.registers[dst] = (self.registers[dst] + 1) & 0xFFFFFFFF
            else:
                val = imm if imm is not None else 1
                self.registers[dst] = (self.registers[dst] + val) & 0xFFFFFFFF
        elif opcode == 32:  # STRIP
            if imm is not None:
                self.registers[dst] = self.registers[src] & imm
            else:
                self.registers[dst] = self.registers[src] & 0xFF
        elif opcode == 36:  # STILL
            self.state = VMState.PAUSED
        elif opcode == 56:  # HALT (RETREAT)
            self.state = VMState.HALTED
        else:
            handler = self._OPCODE_HANDLERS.get(opcode)
            if handler:
                handler(self, 0, [dst, src])
            else:
                pass
    
    def _iching_crea_ext(self, sub_op, dst, src, imm):
        pass
    
    def _iching_recv_ext(self, sub_op, dst, src, imm):
        if 0 <= src < self.NUM_REGISTERS:
            port = self.registers[src]
        else:
            port = 0
        if port in self.io_handlers:
            self.registers[dst] = self.io_handlers[port]()
        else:
            self.registers[dst] = 0

    def _step_native(self, byte1):
        native_opcode = byte1 & 0x3F
        
        if self.pc + 2 >= len(self.program):
            self.state = VMState.HALTED
            return
        
        byte2 = self.program[self.pc + 1]
        byte3 = self.program[self.pc + 2]
        
        dst = byte2 & 0x1F
        src = byte3 & 0x1F
        
        self.pc += 3
        
        imm = 0
        has_imm = False
        
        needs_imm = native_opcode in (
            NativeOpcodes.MOVI, NativeOpcodes.CMPI,
            NativeOpcodes.JMP, NativeOpcodes.CALL,
            NativeOpcodes.JE, NativeOpcodes.JNE,
            NativeOpcodes.JL, NativeOpcodes.JLE,
            NativeOpcodes.JG, NativeOpcodes.JGE,
            NativeOpcodes.JC, NativeOpcodes.JNC,
        )
        
        TWO_REG_IMM_OPS = {
            NativeOpcodes.ADD, NativeOpcodes.SUB,
            NativeOpcodes.MUL, NativeOpcodes.DIV, NativeOpcodes.MOD,
            NativeOpcodes.AND, NativeOpcodes.OR, NativeOpcodes.XOR,
            NativeOpcodes.SHL, NativeOpcodes.SHR, NativeOpcodes.SAR,
            NativeOpcodes.CMP, NativeOpcodes.TEST,
        }
        
        if needs_imm:
            if self.pc + 3 < len(self.program):
                imm = struct.unpack('<I', bytes(self.program[self.pc:self.pc+4]))[0]
                self.pc += 4
                has_imm = True
            else:
                self.state = VMState.ERROR
                return
        elif native_opcode in TWO_REG_IMM_OPS and (byte2 & 0x20):
            if self.pc + 3 < len(self.program):
                imm = struct.unpack('<I', bytes(self.program[self.pc:self.pc+4]))[0]
                self.pc += 4
                has_imm = True
            else:
                self.state = VMState.ERROR
                return
        
        handler = self.native_handlers.get(native_opcode)
        if handler:
            handler(dst, src, imm if has_imm else None)
        else:
            self.state = VMState.ERROR
    
    def _step_extended(self, byte1):
        self.state = VMState.ERROR
    
    def _step_long(self, byte1):
        self.state = VMState.ERROR
    
    def _set_flags_arithmetic(self, result: int, carry: bool = False, overflow: bool = False):
        self.flag_zero = (result & 0xFFFFFFFF) == 0
        self.flag_negative = (result & 0x80000000) != 0
        self.flag_carry = carry
        self.flag_overflow = overflow
    
    def _native_nop(self, dst, src, imm):
        pass
    
    def _native_hlt(self, dst, src, imm):
        self.state = VMState.HALTED
    
    def _native_add(self, dst, src, imm):
        a = self.registers[dst]
        b = self.registers[src] if imm is None else imm
        result = a + b
        carry = (result > 0xFFFFFFFF)
        self.registers[dst] = result & 0xFFFFFFFF
        self._set_flags_arithmetic(result, carry)
    
    def _native_sub(self, dst, src, imm):
        a = self.registers[dst]
        b = self.registers[src] if imm is None else imm
        result = a - b
        carry = (a < b)
        self.registers[dst] = result & 0xFFFFFFFF
        self._set_flags_arithmetic(result, carry)
    
    def _native_mul(self, dst, src, imm):
        a = self.registers[dst]
        b = self.registers[src] if imm is None else imm
        result = a * b
        self.registers[dst] = result & 0xFFFFFFFF
        self._set_flags_arithmetic(result)
    
    def _native_div(self, dst, src, imm):
        divisor = self.registers[src] if imm is None else imm
        if divisor == 0:
            self._int_divide_by_zero()
            return
        dividend = self.registers[dst]
        result = dividend // divisor
        self.registers[dst] = result & 0xFFFFFFFF
        self._set_flags_arithmetic(result)
    
    def _native_mod(self, dst, src, imm):
        divisor = self.registers[src] if imm is None else imm
        if divisor == 0:
            self._int_divide_by_zero()
            return
        dividend = self.registers[dst]
        result = dividend % divisor
        self.registers[dst] = result & 0xFFFFFFFF
        self._set_flags_arithmetic(result)
    
    def _native_inc(self, dst, src, imm):
        self.registers[dst] = (self.registers[dst] + 1) & 0xFFFFFFFF
        self._set_flags_arithmetic(self.registers[dst])
    
    def _native_dec(self, dst, src, imm):
        self.registers[dst] = (self.registers[dst] - 1) & 0xFFFFFFFF
        self._set_flags_arithmetic(self.registers[dst])
    
    def _native_neg(self, dst, src, imm):
        self.registers[dst] = (-self.registers[dst]) & 0xFFFFFFFF
        self._set_flags_arithmetic(self.registers[dst])
    
    def _native_and(self, dst, src, imm):
        result = self.registers[dst] & (self.registers[src] if imm is None else imm)
        self.registers[dst] = result
        self._set_flags_arithmetic(result)
    
    def _native_or(self, dst, src, imm):
        result = self.registers[dst] | (self.registers[src] if imm is None else imm)
        self.registers[dst] = result
        self._set_flags_arithmetic(result)
    
    def _native_xor(self, dst, src, imm):
        result = self.registers[dst] ^ (self.registers[src] if imm is None else imm)
        self.registers[dst] = result
        self._set_flags_arithmetic(result)
    
    def _native_not(self, dst, src, imm):
        result = ~self.registers[dst] & 0xFFFFFFFF
        self.registers[dst] = result
        self._set_flags_arithmetic(result)
    
    def _native_shl(self, dst, src, imm):
        shift = (self.registers[src] if imm is None else imm) & 0x1F
        result = (self.registers[dst] << shift) & 0xFFFFFFFF
        self.registers[dst] = result
        self._set_flags_arithmetic(result)
    
    def _native_shr(self, dst, src, imm):
        shift = (self.registers[src] if imm is None else imm) & 0x1F
        result = (self.registers[dst] >> shift) & 0xFFFFFFFF
        self.registers[dst] = result
        self._set_flags_arithmetic(result)
    
    def _native_sar(self, dst, src, imm):
        shift = (self.registers[src] if imm is None else imm) & 0x1F
        val = self.registers[dst]
        if val & 0x80000000:
            mask = (0xFFFFFFFF << (32 - shift)) & 0xFFFFFFFF
            result = (val >> shift) | mask
        else:
            result = val >> shift
        self.registers[dst] = result & 0xFFFFFFFF
        self._set_flags_arithmetic(result)
    
    def _native_cmp(self, dst, src, imm):
        a = self.registers[dst]
        b = self.registers[src] if imm is None else imm
        result = a - b
        self.flag_zero = (a == b)
        self.flag_negative = (result & 0x80000000) != 0
        self.flag_carry = (a < b)
        signed_a = a if a < 0x80000000 else a - 0x100000000
        signed_b = b if b < 0x80000000 else b - 0x100000000
        self.flag_overflow = ((signed_a > 0 and signed_b < 0 and signed_a - signed_b < 0) or
                              (signed_a < 0 and signed_b > 0 and signed_a - signed_b > 0))
    
    def _native_cmpi(self, dst, src, imm):
        if imm is None:
            return
        a = self.registers[dst]
        b = imm & 0xFFFFFFFF
        result = a - b
        self.flag_zero = (a == b)
        self.flag_negative = (result & 0x80000000) != 0
        self.flag_carry = (a < b)
    
    def _native_test(self, dst, src, imm):
        result = self.registers[dst] & (self.registers[src] if imm is None else imm)
        self.flag_zero = (result == 0)
        self.flag_negative = (result & 0x80000000) != 0
        self.flag_carry = False
        self.flag_overflow = False
    
    def _native_jmp(self, dst, src, imm):
        if imm is not None:
            self.pc = imm
    
    def _native_je(self, dst, src, imm):
        if self.flag_zero and imm is not None:
            self.pc = imm
    
    def _native_jne(self, dst, src, imm):
        if not self.flag_zero and imm is not None:
            self.pc = imm
    
    def _native_jl(self, dst, src, imm):
        if self.flag_carry and imm is not None:
            self.pc = imm
    
    def _native_jle(self, dst, src, imm):
        if (self.flag_zero or self.flag_carry) and imm is not None:
            self.pc = imm
    
    def _native_jg(self, dst, src, imm):
        if (not self.flag_zero and not self.flag_carry) and imm is not None:
            self.pc = imm
    
    def _native_jge(self, dst, src, imm):
        if not self.flag_carry and imm is not None:
            self.pc = imm
    
    def _native_jc(self, dst, src, imm):
        if self.flag_carry and imm is not None:
            self.pc = imm
    
    def _native_jnc(self, dst, src, imm):
        if not self.flag_carry and imm is not None:
            self.pc = imm
    
    def _native_mov(self, dst, src, imm):
        self.registers[dst] = self.registers[src]
    
    def _native_movi(self, dst, src, imm):
        if imm is not None:
            self.registers[dst] = imm & 0xFFFFFFFF
    
    def _native_lea(self, dst, src, imm):
        base = self.registers[src]
        offset = imm if imm is not None else 0
        self.registers[dst] = (base + offset) & 0xFFFFFFFF
    
    def _native_xchg(self, dst, src, imm):
        temp = self.registers[dst]
        self.registers[dst] = self.registers[src]
        self.registers[src] = temp
    
    def _native_push(self, dst, src, imm):
        sp = self.registers[self.SP_REG]
        if sp >= 4:
            sp -= 4
            val = self.registers[dst]
            self._store_word_stack(sp, val)
            self.registers[self.SP_REG] = sp
    
    def _native_pop(self, dst, src, imm):
        sp = self.registers[self.SP_REG]
        if sp + 4 <= self.STACK_SIZE:
            val = self._load_word_stack(sp)
            self.registers[dst] = val
            self.registers[self.SP_REG] = sp + 4
    
    def _native_pusha(self, dst, src, imm):
        for reg in range(self.NUM_REGISTERS):
            sp = self.registers[self.SP_REG]
            if sp >= 4:
                sp -= 4
                self._store_word_stack(sp, self.registers[reg])
                self.registers[self.SP_REG] = sp
    
    def _native_popa(self, dst, src, imm):
        for reg in reversed(range(self.NUM_REGISTERS)):
            sp = self.registers[self.SP_REG]
            if sp + 4 <= self.STACK_SIZE:
                self.registers[reg] = self._load_word_stack(sp)
                self.registers[self.SP_REG] = sp + 4
    
    def _native_call(self, dst, src, imm):
        sp = self.registers[self.SP_REG]
        if sp >= 4:
            sp -= 4
            self._store_word_stack(sp, self.pc)
            self.registers[self.SP_REG] = sp
        if imm is not None:
            self.pc = imm
    
    def _native_ret(self, dst, src, imm):
        sp = self.registers[self.SP_REG]
        if sp + 4 <= self.STACK_SIZE:
            return_addr = self._load_word_stack(sp)
            self.registers[self.SP_REG] = sp + 4
            self.pc = return_addr
    
    def _native_int(self, dst, src, imm):
        int_num = dst
        handler = self.interrupt_table.get(int_num)
        if handler:
            handler()
    
    def _native_iret(self, dst, src, imm):
        sp = self.registers[self.SP_REG]
        if sp + 4 <= self.STACK_SIZE:
            return_addr = self._load_word_stack(sp)
            self.registers[self.SP_REG] = sp + 4
            self.pc = return_addr
            self.flag_interrupt = True
    
    def _native_ldr(self, dst, src, imm):
        addr = self.registers[src]
        if 0 <= addr < self.HEAP_SIZE - 3:
            self.registers[dst] = self._load_word_heap(addr)
    
    def _native_str(self, dst, src, imm):
        addr = self.registers[dst]
        val = self.registers[src]
        if 0 <= addr < self.HEAP_SIZE - 3:
            self._store_word_heap(addr, val)
    
    def _native_ldrb(self, dst, src, imm):
        addr = self.registers[src]
        if 0 <= addr < self.HEAP_SIZE:
            self.registers[dst] = self.heap[addr]
    
    def _native_strb(self, dst, src, imm):
        addr = self.registers[dst]
        val = self.registers[src]
        if 0 <= addr < self.HEAP_SIZE:
            self.heap[addr] = val & 0xFF
    
    def _load_word_stack(self, addr):
        return (self.stack[addr] |
                (self.stack[addr+1] << 8) |
                (self.stack[addr+2] << 16) |
                (self.stack[addr+3] << 24))
    
    def _store_word_stack(self, addr, val):
        self.stack[addr] = val & 0xFF
        self.stack[addr+1] = (val >> 8) & 0xFF
        self.stack[addr+2] = (val >> 16) & 0xFF
        self.stack[addr+3] = (val >> 24) & 0xFF
    
    def _load_word_heap(self, addr):
        return (self.heap[addr] |
                (self.heap[addr+1] << 8) |
                (self.heap[addr+2] << 16) |
                (self.heap[addr+3] << 24))
    
    def _store_word_heap(self, addr, val):
        self.heap[addr] = val & 0xFF
        self.heap[addr+1] = (val >> 8) & 0xFF
        self.heap[addr+2] = (val >> 16) & 0xFF
        self.heap[addr+3] = (val >> 24) & 0xFF
    
    def load_string(self, addr: int, s: str):
        encoded = s.encode('utf-8')
        for i, b in enumerate(encoded):
            self.heap[addr + i] = b
        self.heap[addr + len(encoded)] = 0
        return len(encoded)
    
    def read_string(self, addr: int) -> str:
        result = bytearray()
        while addr < self.HEAP_SIZE and self.heap[addr] != 0:
            result.append(self.heap[addr])
            addr += 1
        return result.decode('utf-8', errors='replace')
    
    def assemble(self, asm_source: str) -> bytearray:
        program = bytearray()
        lines = asm_source.strip().split('\n')
        labels = {}
        label_refs = []
        
        MNEMONIC_MAP = {
            'NOP': NativeOpcodes.NOP, 'HLT': NativeOpcodes.HLT,
            'ADD': NativeOpcodes.ADD, 'SUB': NativeOpcodes.SUB,
            'MUL': NativeOpcodes.MUL, 'DIV': NativeOpcodes.DIV,
            'MOD': NativeOpcodes.MOD, 'INC': NativeOpcodes.INC,
            'DEC': NativeOpcodes.DEC, 'NEG': NativeOpcodes.NEG,
            'AND': NativeOpcodes.AND, 'OR': NativeOpcodes.OR,
            'XOR': NativeOpcodes.XOR, 'NOT': NativeOpcodes.NOT,
            'SHL': NativeOpcodes.SHL, 'SHR': NativeOpcodes.SHR,
            'SAR': NativeOpcodes.SAR,
            'CMP': NativeOpcodes.CMP, 'CMPI': NativeOpcodes.CMPI,
            'TEST': NativeOpcodes.TEST,
            'JMP': NativeOpcodes.JMP, 'JE': NativeOpcodes.JE,
            'JNE': NativeOpcodes.JNE, 'JL': NativeOpcodes.JL,
            'JLE': NativeOpcodes.JLE, 'JG': NativeOpcodes.JG,
            'JGE': NativeOpcodes.JGE, 'JC': NativeOpcodes.JC,
            'JNC': NativeOpcodes.JNC,
            'MOV': NativeOpcodes.MOV, 'MOVI': NativeOpcodes.MOVI,
            'LEA': NativeOpcodes.LEA, 'XCHG': NativeOpcodes.XCHG,
            'LDR': NativeOpcodes.LDR, 'STR': NativeOpcodes.STR,
            'LDRB': NativeOpcodes.LDRB, 'STRB': NativeOpcodes.STRB,
            'PUSH': NativeOpcodes.PUSH, 'POP': NativeOpcodes.POP,
            'PUSHA': NativeOpcodes.PUSHA, 'POPA': NativeOpcodes.POPA,
            'CALL': NativeOpcodes.CALL, 'RET': NativeOpcodes.RET,
            'INT': NativeOpcodes.INT,
        }
        
        IMM_OPCODES = {
            NativeOpcodes.MOVI, NativeOpcodes.CMPI,
            NativeOpcodes.JMP, NativeOpcodes.CALL,
            NativeOpcodes.JE, NativeOpcodes.JNE,
            NativeOpcodes.JL, NativeOpcodes.JLE,
            NativeOpcodes.JG, NativeOpcodes.JGE,
            NativeOpcodes.JC, NativeOpcodes.JNC,
        }
        
        NO_OPERAND_OPS = {
            NativeOpcodes.NOP, NativeOpcodes.HLT,
            NativeOpcodes.RET, NativeOpcodes.PUSHA, NativeOpcodes.POPA,
        }
        
        ONE_REG_OPS = {
            NativeOpcodes.INC, NativeOpcodes.DEC, NativeOpcodes.NEG,
            NativeOpcodes.NOT, NativeOpcodes.PUSH, NativeOpcodes.POP,
            NativeOpcodes.INT,
        }
        
        TWO_REG_OPS = {
            NativeOpcodes.ADD, NativeOpcodes.SUB,
            NativeOpcodes.MUL, NativeOpcodes.DIV, NativeOpcodes.MOD,
            NativeOpcodes.AND, NativeOpcodes.OR, NativeOpcodes.XOR,
            NativeOpcodes.SHL, NativeOpcodes.SHR, NativeOpcodes.SAR,
            NativeOpcodes.CMP, NativeOpcodes.TEST,
            NativeOpcodes.MOV, NativeOpcodes.LEA, NativeOpcodes.XCHG,
            NativeOpcodes.LDR, NativeOpcodes.STR,
            NativeOpcodes.LDRB, NativeOpcodes.STRB,
        }
        
        TWO_REG_IMM_COMPAT = {
            NativeOpcodes.ADD, NativeOpcodes.SUB,
            NativeOpcodes.MUL, NativeOpcodes.DIV, NativeOpcodes.MOD,
            NativeOpcodes.AND, NativeOpcodes.OR, NativeOpcodes.XOR,
            NativeOpcodes.SHL, NativeOpcodes.SHR, NativeOpcodes.SAR,
            NativeOpcodes.CMP, NativeOpcodes.TEST,
        }
        
        parsed_lines = []
        for line in lines:
            line = line.strip()
            # Strip inline comments (everything after ';')
            if ';' in line:
                line = line.split(';', 1)[0].strip()
            if not line or line.startswith('#'):
                continue
            if line.endswith(':'):
                label = line[:-1].strip()
                parsed_lines.append(('LABEL', label))
                continue
            parts = line.split(None, 1)
            mnemonic = parts[0].upper()
            operands_str = parts[1].strip() if len(parts) > 1 else ''
            parsed_lines.append(('INSTR', mnemonic, operands_str))
        
        # First pass: calculate label positions
        # All native instructions use 3-byte header (byte1+byte2+byte3)
        # IMM_OPCODES add 4 more bytes for immediate value
        # TWO_REG_OPS with immediate operand also add 4 bytes
        # IChing instructions use 4 bytes
        pc = 0
        for item in parsed_lines:
            if item[0] == 'LABEL':
                labels[item[1]] = pc
                continue
            mnemonic = item[1]
            if mnemonic in self.ICHING_OPCODE_REVERSE:
                pc += 4
                continue
            if '.' in mnemonic:
                parts = mnemonic.split('.', 1)
                if parts[0] in self.ICHING_OPCODE_REVERSE and parts[1].isdigit():
                    operands_str = item[2] if len(item) > 2 else ''
                    has_imm = False
                    if operands_str:
                        for op in operands_str.split(','):
                            op = op.strip()
                            if op.startswith('#') or op.startswith('0x') or op.startswith('0X'):
                                has_imm = True
                                break
                            if not op.upper().startswith('R') and op not in self.ICHING_OPCODE_REVERSE:
                                try:
                                    int(op, 0)
                                    has_imm = True
                                    break
                                except ValueError:
                                    has_imm = True
                                    break
                    pc += 8 if has_imm else 4
                    continue
            if mnemonic not in MNEMONIC_MAP:
                continue
            opcode = MNEMONIC_MAP[mnemonic]
            if opcode in IMM_OPCODES:
                pc += 7  # 3 header + 4 imm
            elif opcode in TWO_REG_IMM_COMPAT:
                operands_str = item[2] if len(item) > 2 else ''
                has_imm_operand = False
                if operands_str:
                    parts = [p.strip() for p in operands_str.split(',')]
                    if len(parts) >= 2:
                        src_str = parts[1].strip()
                        if src_str.startswith('#') or src_str.startswith('0x') or src_str.startswith('0X'):
                            has_imm_operand = True
                        else:
                            try:
                                int(src_str, 10)
                                has_imm_operand = True
                            except ValueError:
                                pass
                if has_imm_operand:
                    pc += 7  # 3 header + 4 imm
                else:
                    pc += 3  # 3 header
            else:
                pc += 3  # 3 header
        
        # Second pass: generate bytecode
        pc = 0
        for item in parsed_lines:
            if item[0] == 'LABEL':
                labels[item[1]] = pc
                continue
            
            mnemonic = item[1]
            operands_str = item[2]
            
            iching_ext = None
            if '.' in mnemonic:
                parts = mnemonic.split('.', 1)
                if parts[0] in self.ICHING_OPCODE_REVERSE and parts[1].isdigit():
                    iching_ext = int(parts[1])
                    mnemonic = parts[0]
            
            if mnemonic in self.ICHING_OPCODE_REVERSE:
                old_opcode = self.ICHING_OPCODE_REVERSE[mnemonic]
                byte1 = 0x80 | (old_opcode & 0x3F)
                
                if iching_ext is not None:
                    sub_op = iching_ext & 0x3F
                    has_imm_operand = False
                    if operands_str:
                        ops = [p.strip() for p in operands_str.split(',')]
                        for op in ops:
                            if op.startswith('#') or op.startswith('@'):
                                has_imm_operand = True
                                break
                        # Also check if any operand is just a label name (no prefix)
                        for op in ops:
                            if op and not op.startswith('R') and not op.startswith('#') and not op.startswith('@'):
                                if not op.isdigit() and not op.startswith('0x') and not op.startswith('0X'):
                                    if op in labels:
                                        has_imm_operand = True
                                        break
                    
                    ext_mode = 2 if has_imm_operand else 1
                    byte2 = (ext_mode << 6) | sub_op
                    
                    regs = [p.strip() for p in operands_str.split(',')] if operands_str else []
                    dst_reg = 0
                    src_reg = 0
                    imm_val = 0
                    
                    is_branch = (old_opcode == 2)  # BRANCH
                    
                    if len(regs) >= 1:
                        r = regs[0].strip()
                        if r.upper().startswith('R'):
                            try:
                                dst_reg = int(r[1:])
                            except ValueError:
                                dst_reg = 0
                        elif r.startswith('@'):
                            label_name = self._extract_label_name(r[1:])
                            if label_name in labels:
                                imm_val = labels[label_name]
                                has_imm_operand = True
                        elif is_branch:
                            try:
                                imm_val = int(r, 0)
                                has_imm_operand = True
                            except ValueError:
                                if r in labels:
                                    imm_val = labels[r]
                                    has_imm_operand = True
                    if len(regs) >= 2:
                        r = regs[1].strip()
                        if r.upper().startswith('R'):
                            try:
                                src_reg = int(r[1:])
                            except ValueError:
                                src_reg = 0
                        elif r.startswith('#'):
                            try:
                                imm_val = int(r[1:], 0)
                                has_imm_operand = True
                            except ValueError:
                                imm_val = 0
                        elif r.startswith('0x') or r.startswith('0X'):
                            try:
                                imm_val = int(r, 16)
                                has_imm_operand = True
                            except ValueError:
                                imm_val = 0
                        elif r.startswith('@'):
                            label_name = self._extract_label_name(r[1:])
                            if label_name in labels:
                                imm_val = labels[label_name]
                                has_imm_operand = True
                        else:
                            if r in labels:
                                imm_val = labels[r]
                                has_imm_operand = True
                    if len(regs) >= 3:
                        r = regs[2].strip()
                        if r.startswith('#'):
                            try:
                                imm_val = int(r[1:], 0)
                                has_imm_operand = True
                            except ValueError:
                                imm_val = 0
                        elif r.startswith('0x') or r.startswith('0X'):
                            try:
                                imm_val = int(r, 16)
                                has_imm_operand = True
                            except ValueError:
                                imm_val = 0
                        elif r.startswith('@'):
                            label_name = self._extract_label_name(r[1:])
                            if label_name in labels:
                                imm_val = labels[label_name]
                                has_imm_operand = True
                        else:
                            if r in labels:
                                imm_val = labels[r]
                                has_imm_operand = True
                            else:
                                try:
                                    imm_val = int(r, 0)
                                    has_imm_operand = True
                                except ValueError:
                                    pass
                    
                    byte3 = dst_reg & 0x1F
                    byte4 = src_reg & 0x1F
                    
                    if has_imm_operand:
                        ext_mode = 2
                        byte2 = (ext_mode << 6) | sub_op
                        program.extend([byte1, byte2, byte3, byte4])
                        program.extend(struct.pack('<I', imm_val & 0xFFFFFFFF))
                        pc += 8
                    else:
                        ext_mode = 1
                        byte2 = (ext_mode << 6) | sub_op
                        program.extend([byte1, byte2, byte3, byte4])
                        pc += 4
                else:
                    byte2 = 0
                    program.extend([byte1, byte2, 0, 0])
                    pc += 4
                continue
            
            if mnemonic not in MNEMONIC_MAP:
                continue
            
            opcode = MNEMONIC_MAP[mnemonic]
            byte1 = 0x40 | (opcode & 0x3F)
            byte2 = 0
            byte3 = 0
            
            has_imm = False
            imm_value = 0
            
            if operands_str:
                operand_parts = [p.strip() for p in operands_str.split(',')]
                
                if opcode in NO_OPERAND_OPS:
                    pass
                elif opcode in ONE_REG_OPS:
                    reg_idx = self._parse_register(operand_parts[0])
                    if reg_idx is not None:
                        byte2 = reg_idx & 0x1F
                elif opcode in TWO_REG_OPS:
                    if len(operand_parts) >= 2:
                        dst_idx = self._parse_register(operand_parts[0])
                        src_str = operand_parts[1].strip()
                        src_idx = self._parse_register(src_str)
                        if dst_idx is not None:
                            byte2 = dst_idx & 0x1F
                        if src_idx is not None:
                            byte3 = src_idx & 0x1F
                        elif opcode in TWO_REG_IMM_COMPAT:
                            imm_val = self._parse_imm_or_label(src_str, labels)
                            if imm_val is not None:
                                byte2 = (dst_idx & 0x1F) | 0x20
                                byte3 = 0
                                has_imm = True
                                imm_value = imm_val
                    elif len(operand_parts) == 1:
                        dst_idx = self._parse_register(operand_parts[0])
                        if dst_idx is not None:
                            byte2 = dst_idx & 0x1F
                elif opcode in IMM_OPCODES:
                    if len(operand_parts) >= 2:
                        dst_idx = self._parse_register(operand_parts[0])
                        if dst_idx is not None:
                            byte2 = dst_idx & 0x1F
                        imm_val = self._parse_imm_or_label(operand_parts[1].strip(), labels)
                        if imm_val is not None:
                            has_imm = True
                            imm_value = imm_val
                        else:
                            label_name = operand_parts[1].strip().lstrip('@')
                            label_refs.append((pc + 3, label_name))
                            has_imm = True
                            imm_value = 0
                    elif len(operand_parts) == 1:
                        target = operand_parts[0].strip()
                        imm_val = self._parse_imm_or_label(target, labels)
                        if imm_val is not None:
                            has_imm = True
                            imm_value = imm_val
                        else:
                            label_name = target.lstrip('@')
                            label_refs.append((pc + 3, label_name))
                            has_imm = True
                            imm_value = 0
            
            program.append(byte1)
            program.append(byte2)
            program.append(byte3)
            pc += 3
            
            if has_imm and (opcode in IMM_OPCODES or opcode in TWO_REG_IMM_COMPAT):
                program.extend([
                    imm_value & 0xFF,
                    (imm_value >> 8) & 0xFF,
                    (imm_value >> 16) & 0xFF,
                    (imm_value >> 24) & 0xFF,
                ])
                pc += 4
        
        for ref_pc, label in label_refs:
            if label in labels:
                target_pc = labels[label]
                pos = ref_pc
                program[pos] = target_pc & 0xFF
                program[pos+1] = (target_pc >> 8) & 0xFF
                program[pos+2] = (target_pc >> 16) & 0xFF
                program[pos+3] = (target_pc >> 24) & 0xFF
        
        return program
    
    def _parse_register(self, s: str) -> Optional[int]:
        s = s.strip().upper()
        if s.startswith('R'):
            try:
                return int(s[1:])
            except ValueError:
                return None
        if s == 'SP':
            return self.SP_REG
        if s == 'FP':
            return self.FP_REG
        if s == 'LR':
            return self.LR_REG
        return None
    
    def _extract_label_name(self, s: str) -> str:
        """从 @label 之后的字符串中提取纯净的标签名，跳过尾随空格和注释"""
        # Truncate at first whitespace or semicolon (comment start)
        end = len(s)
        for i, ch in enumerate(s):
            if ch in (' ', '\t', ';', '\n', '\r', ','):
                end = i
                break
        return s[:end].strip()
    
    def _parse_imm_or_label(self, s: str, labels: Dict[str, int]) -> Optional[int]:
        s = s.strip()
        if s.startswith('#'):
            inner = s[1:]
            if inner.startswith("'") and inner.endswith("'") and len(inner) == 3:
                return ord(inner[1])
            try:
                return int(inner, 0)
            except ValueError:
                return None
        if s.startswith("'") and s.endswith("'") and len(s) == 3:
            return ord(s[1])
        if s.startswith('0x') or s.startswith('0X'):
            try:
                return int(s, 16)
            except ValueError:
                return None
        try:
            return int(s, 10)
        except ValueError:
            pass
        label = self._extract_label_name(s.lstrip('@'))
        if label in labels:
            return labels[label]
        return None
    
    def load_assembled(self, asm_source: str):
        program = self.assemble(asm_source)
        self.program = program
        self.pc = 0
        self.state = VMState.INIT
    
    def load_evob(self, evob_data: bytes):
        if isinstance(evob_data, bytearray):
            evob_data = bytes(evob_data)
        if len(evob_data) < 10:
            return False
        if evob_data[:4] != b'EVOB':
            return False
        header_size = struct.unpack(">H", evob_data[6:8])[0]
        if header_size < 10 or header_size > len(evob_data):
            return False
        bytecode = evob_data[header_size:]
        self.program = bytearray(bytecode)
        self.pc = 0
        self.state = VMState.INIT
        return True
