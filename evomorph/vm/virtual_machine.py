import struct
from enum import IntEnum


class VMState(IntEnum):
    INIT = 0
    RUNNING = 1
    PAUSED = 2
    HALTED = 3
    ERROR = 4
    TRAPPED = 5


class IChingVM:
    NUM_REGISTERS = 16
    STACK_SIZE = 65536
    HEAP_SIZE = 1048576
    MAX_FUTURES = 256

    SPECIAL_REGS = {
        "R_FP": 12,
        "R_SP": 13,
        "R_LR": 14,
        "R_A0": 15,
    }

    def __init__(self, use_evomorph: bool = False):
        self.registers = [0] * self.NUM_REGISTERS
        self.stack = bytearray(self.STACK_SIZE)
        self.heap = bytearray(self.HEAP_SIZE)
        self.heap_ptr = 0
        self.pc = 0
        self.state = VMState.INIT
        self.program = bytearray()
        self.flag_zero = False
        self.flag_carry = False
        self.flag_negative = False
        self.flag_overflow = False
        self.futures = {}
        self.future_id_counter = 0
        self.locks = {}
        self.barriers = {}
        self.event_listeners = {}
        self.labels = {}
        self.call_stack = []
        self.io_handlers = {}
        self.trace_log = []
        self.generation = 0
        self.cycle_count = 0
        self.energy_cost = 0.0
        
        self._use_evomorph = use_evomorph
        self._backend = None
        
        if use_evomorph:
            try:
                from evomorph.bootstrap import EvomorphBackend
                self._backend = EvomorphBackend()
            except ImportError:
                self._use_evomorph = False
        
        self._init_special_regs()

    def set_mode(self, use_evomorph: bool):
        """设置使用 Evomorph 实现还是 Python 实现"""
        self._use_evomorph = use_evomorph
        if use_evomorph and self._backend is None:
            try:
                from evomorph.bootstrap import EvomorphBackend
                self._backend = EvomorphBackend()
            except ImportError:
                self._use_evomorph = False

    def _init_special_regs(self):
        self.registers[self.SPECIAL_REGS["R_SP"]] = self.STACK_SIZE
        self.registers[self.SPECIAL_REGS["R_FP"]] = self.STACK_SIZE

    def load_program(self, bytecode):
        if isinstance(bytecode, (bytes, bytearray)):
            self.program = bytearray(bytecode)
        elif isinstance(bytecode, list):
            self.program = bytearray()
            for instr in bytecode:
                if isinstance(instr, dict):
                    self._encode_instruction_to_program(instr)
                elif isinstance(instr, int):
                    self.program.append(instr & 0xFF)
        self.pc = 0
        self.state = VMState.INIT

    def _encode_instruction_to_program(self, instr):
        opcode = instr.get("opcode", 0)
        modifier = instr.get("modifier", 0)
        operands = instr.get("operands", [])
        byte1 = ((opcode & 0x3F) << 2) | ((modifier >> 4) & 0x03)
        byte2 = modifier & 0x0F
        self.program.extend([byte1, byte2])
        num_operands = self._operand_count(opcode)
        for i in range(num_operands):
            if i < len(operands):
                op = operands[i]
                if isinstance(op, int):
                    self.program.append(op & 0xFF)
                elif isinstance(op, str) and op.startswith("R"):
                    try:
                        reg_idx = int(op[1:])
                        self.program.append(reg_idx & 0xFF)
                    except ValueError:
                        self.program.append(0)
                else:
                    self.program.append(0)
            else:
                self.program.append(0)

    @staticmethod
    def _operand_count(opcode):
        if opcode in (0x00, 0x0E, 0x1E, 0x33):
            return 2
        if opcode in (0x02, 0x04, 0x0B, 0x1A, 0x1B, 0x20, 0x27, 0x2E, 0x30, 0x3B):
            return 2
        return 2

    def register_io_handler(self, port, handler):
        self.io_handlers[port] = handler

    def run(self, max_cycles=None):
        if self._use_evomorph and self._backend and self._backend.is_evomorph_available("vm"):
            return self._run_using_evomorph(max_cycles)
        
        self.state = VMState.RUNNING
        while self.state == VMState.RUNNING:
            if max_cycles is not None and self.cycle_count >= max_cycles:
                self.state = VMState.PAUSED
                break
            if self.pc >= len(self.program):
                self.state = VMState.HALTED
                break
            self._step()
            self.cycle_count += 1
        return self.state
    
    def _run_using_evomorph(self, max_cycles=None):
        """使用 Evomorph 实现执行程序"""
        program_list = []
        for i in range(0, len(self.program), 2):
            if i + 1 < len(self.program):
                byte1 = self.program[i]
                byte2 = self.program[i + 1]
                opcode = (byte1 >> 2) & 0x3F
                modifier = ((byte1 & 0x03) << 4) | (byte2 & 0x0F)
                program_list.append({
                    "opcode": opcode,
                    "modifier": modifier,
                    "operands": [],
                })
        
        result = self._backend.execute_program(program_list, max_cycles or 10000)
        
        if "state" in result:
            state_map = {
                "INIT": VMState.INIT,
                "RUNNING": VMState.RUNNING,
                "PAUSED": VMState.PAUSED,
                "HALTED": VMState.HALTED,
                "ERROR": VMState.ERROR,
                "TRAPPED": VMState.TRAPPED,
            }
            self.state = state_map.get(result["state"], VMState.ERROR)
        
        if "cycle_count" in result:
            self.cycle_count = result["cycle_count"]
        
        if "energy_cost" in result:
            self.energy_cost = result["energy_cost"]
        
        if "registers" in result:
            for i in range(min(self.NUM_REGISTERS, 16)):
                reg_name = f"R{i}"
                if reg_name in result["registers"]:
                    self.registers[i] = result["registers"][reg_name]
        
        return self.state

    def step(self):
        if self.state not in (VMState.RUNNING, VMState.PAUSED):
            return
        self.state = VMState.RUNNING
        self._step()
        self.cycle_count += 1

    def _step(self):
        if self.pc + 1 >= len(self.program):
            self.state = VMState.HALTED
            return
        byte1 = self.program[self.pc]
        byte2 = self.program[self.pc + 1]
        opcode = (byte1 >> 2) & 0x3F
        modifier = ((byte1 & 0x03) << 4) | (byte2 & 0x0F)
        self.pc += 2
        operands = self._read_operands(opcode)
        self._execute(opcode, modifier, operands)

    def _read_operands(self, opcode):
        operands = []
        count = self._operand_count(opcode)
        for _ in range(count):
            if self.pc < len(self.program):
                operands.append(self.program[self.pc])
                self.pc += 1
            else:
                operands.append(0)
        return operands

    def _execute(self, opcode, modifier, operands):
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
                "generation": self.generation,
            })
        else:
            self.state = VMState.ERROR

    def _instruction_energy(self, opcode):
        base = 1.0
        if opcode in (63, 17):
            base = 5.0
        elif opcode in (61, 21):
            base = 3.0
        elif opcode in (18, 45):
            base = 2.0
        return base

    def _op_crea(self, modifier, operands):
        thread_id = len(self.call_stack) + 1
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            self.registers[dst] = thread_id
        self.energy_cost += 10.0

    def _op_recv(self, modifier, operands):
        if len(operands) >= 1:
            dst = operands[0] & 0x0F
            port = operands[1] if len(operands) >= 2 else 0
            if port in self.io_handlers:
                self.registers[dst] = self.io_handlers[port]()
            else:
                self.registers[dst] = 0

    def _op_alloc(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            size = operands[1] if operands[1] > 0 else 256
            if self.heap_ptr + size <= self.HEAP_SIZE:
                addr = self.heap_ptr + 1
                self.heap_ptr += size
                self.registers[dst] = addr
            else:
                self.registers[dst] = 0
                self.flag_overflow = True

    def _op_sprt(self, modifier, operands):
        if len(operands) >= 1:
            dst = operands[0] & 0x0F
            self.registers[dst] = 1

    def _op_wait(self, modifier, operands):
        if len(operands) >= 1:
            cond = operands[0] & 0x0F
            if self.registers[cond] == 0:
                self.pc -= 2

    def _op_lock(self, modifier, operands):
        if len(operands) >= 1:
            lock_id = operands[0]
            if lock_id in self.locks and self.locks[lock_id]:
                self.pc -= 2
            else:
                self.locks[lock_id] = True

    def _op_branch(self, modifier, operands):
        if len(operands) >= 1:
            cond = operands[0] & 0x0F
            if self.registers[cond] != 0:
                if len(operands) >= 2:
                    self.pc = operands[1]

    def _op_merge(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            self.registers[dst] = self.registers[dst] | self.registers[src]

    def _op_prefetch(self, modifier, operands):
        pass

    def _op_step(self, modifier, operands):
        if len(operands) >= 1:
            reg = operands[0] & 0x0F
            self.registers[reg] += 1

    def _op_flush(self, modifier, operands):
        pass

    def _op_halt(self, modifier, operands):
        self.state = VMState.HALTED

    def _op_fellowship(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            self.registers[dst] = self.registers[src]

    def _op_abundance(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            if isinstance(self.registers[src], int):
                addr = self.registers[dst]
                if 0 <= addr < self.HEAP_SIZE:
                    self.heap[addr] = self.registers[src] & 0xFF

    def _op_yield(self, modifier, operands):
        self.state = VMState.PAUSED

    def _op_speculate(self, modifier, operands):
        pass

    def _op_following(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            self.registers[dst] = self.registers[src]

    def _op_mut(self, modifier, operands):
        if len(operands) >= 1:
            target = operands[0] & 0x0F
            bit = operands[1] if len(operands) >= 2 else 0
            self.registers[target] ^= (1 << (bit & 0x1F))

    def _op_approach(self, modifier, operands):
        pass

    def _op_contemplate(self, modifier, operands):
        if len(operands) >= 1:
            reg = operands[0] & 0x0F
            self.registers[reg] = self.cycle_count

    def _op_bite(self, modifier, operands):
        if len(operands) >= 2:
            expected = operands[0]
            actual_reg = operands[1] & 0x0F
            if self.registers[actual_reg] != expected:
                self.state = VMState.TRAPPED

    def _op_adorn(self, modifier, operands):
        pass

    def _op_strip(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            self.registers[dst] = self.registers[src] & 0xFF

    def _op_return(self, modifier, operands):
        if self.call_stack:
            self.pc = self.call_stack.pop()
        else:
            self.state = VMState.HALTED

    def _op_intrinsic(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            self.registers[dst] = self.registers[src]

    def _op_barrier(self, modifier, operands):
        pass

    def _op_nourish(self, modifier, operands):
        self.heap_ptr = 0
        for i in range(self.HEAP_SIZE):
            self.heap[i] = 0

    def _op_overload(self, modifier, operands):
        self.state = VMState.ERROR

    def _op_trap(self, modifier, operands):
        self.state = VMState.TRAPPED

    def _op_illuminate(self, modifier, operands):
        if len(operands) >= 1:
            reg = operands[0] & 0x0F
            val = self.registers[reg]
            if 0xFF00 in self.io_handlers:
                self.io_handlers[0xFF00](val)

    def _op_sense(self, modifier, operands):
        if len(operands) >= 1:
            event_type = operands[0]
            if event_type in self.event_listeners:
                self.event_listeners[event_type]()

    def _op_persist(self, modifier, operands):
        pass

    def _op_retreat(self, modifier, operands):
        self.state = VMState.HALTED

    def _op_thrust(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            self.registers[dst] = self.registers[src]

    def _op_advance(self, modifier, operands):
        if len(operands) >= 1:
            reg = operands[0] & 0x0F
            self.registers[reg] += 1

    def _op_obscure(self, modifier, operands):
        pass

    def _op_bind(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            self.registers[dst] = self.registers[src]

    def _op_convert(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            self.registers[dst] = self.registers[src]

    def _op_lame(self, modifier, operands):
        pass

    def _op_unlock(self, modifier, operands):
        if len(operands) >= 1:
            lock_id = operands[0]
            self.locks[lock_id] = False

    def _op_reduce(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            self.registers[dst] -= self.registers[src]

    def _op_increase(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            self.registers[dst] += self.registers[src]

    def _op_break(self, modifier, operands):
        self.state = VMState.HALTED

    def _op_mate(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            self.registers[dst] = (self.registers[dst] + self.registers[src]) // 2

    def _op_gather(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            self.registers[dst] += self.registers[src]

    def _op_push_up(self, modifier, operands):
        if len(operands) >= 1:
            reg = operands[0] & 0x0F
            sp = self.registers[self.SPECIAL_REGS["R_SP"]]
            if sp > 0:
                sp -= 1
                self.stack[sp] = self.registers[reg] & 0xFF
                self.registers[self.SPECIAL_REGS["R_SP"]] = sp

    def _op_trapped(self, modifier, operands):
        self.state = VMState.ERROR

    def _op_well(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            sp = self.registers[self.SPECIAL_REGS["R_SP"]]
            if sp < self.STACK_SIZE:
                self.registers[dst] = self.stack[sp]
                self.registers[self.SPECIAL_REGS["R_SP"]] = sp + 1

    def _op_replace(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            self.registers[dst] = self.registers[src]

    def _op_cast(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            src = operands[1] & 0x0F
            self.registers[dst] = self.registers[src]

    def _op_shock(self, modifier, operands):
        if len(operands) >= 1:
            signal = operands[0]
            if signal in self.event_listeners:
                self.event_listeners[signal]()

    def _op_still(self, modifier, operands):
        self.state = VMState.PAUSED

    def _op_gradual(self, modifier, operands):
        if len(operands) >= 1:
            reg = operands[0] & 0x0F
            self.registers[reg] += 1

    def _op_mismatch(self, modifier, operands):
        self.state = VMState.ERROR

    def _op_abound(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            count = operands[1]
            self.registers[dst] = count

    def _op_travel(self, modifier, operands):
        pass

    def _op_penetrate(self, modifier, operands):
        if len(operands) >= 2:
            addr = self.registers[operands[0] & 0x0F]
            dst = operands[1] & 0x0F
            if 0 <= addr < self.HEAP_SIZE:
                self.registers[dst] = self.heap[addr]

    def _op_joy(self, modifier, operands):
        if len(operands) >= 1:
            callback_id = operands[0]
            if callback_id in self.event_listeners:
                self.event_listeners[callback_id]()

    def _op_disperse(self, modifier, operands):
        if len(operands) >= 2:
            addr = self.registers[operands[0] & 0x0F]
            val = self.registers[operands[1] & 0x0F]
            if 0 <= addr < self.HEAP_SIZE:
                self.heap[addr] = val & 0xFF

    def _op_throttle(self, modifier, operands):
        pass

    def _op_trust(self, modifier, operands):
        pass

    def _op_micro(self, modifier, operands):
        if len(operands) >= 2:
            dst = operands[0] & 0x0F
            val = operands[1]
            self.registers[dst] += val

    def _op_sync(self, modifier, operands):
        barrier_id = operands[0] if operands else 0
        if barrier_id not in self.barriers:
            self.barriers[barrier_id] = 0
        self.barriers[barrier_id] += 1

    def _op_futu(self, modifier, operands):
        fid = self.future_id_counter
        self.future_id_counter += 1
        self.futures[fid] = {"resolved": False, "value": 0}
        if len(operands) >= 1:
            dst = operands[0] & 0x0F
            self.registers[dst] = fid

    _OPCODE_HANDLERS = {
        63: _op_crea,
        0:  _op_recv,
        17: _op_alloc,
        34: _op_sprt,
        23: _op_wait,
        58: _op_lock,
        2:  _op_branch,
        16: _op_merge,
        55: _op_prefetch,
        59: _op_step,
        7:  _op_flush,
        56: _op_halt,
        61: _op_fellowship,
        47: _op_abundance,
        4:  _op_yield,
        8:  _op_speculate,
        25: _op_following,
        38: _op_mut,
        3:  _op_approach,
        48: _op_contemplate,
        41: _op_bite,
        37: _op_adorn,
        32: _op_strip,
        1:  _op_return,
        57: _op_intrinsic,
        39: _op_barrier,
        33: _op_nourish,
        30: _op_overload,
        18: _op_trap,
        45: _op_illuminate,
        28: _op_sense,
        14: _op_persist,
        60: _op_retreat,
        15: _op_thrust,
        40: _op_advance,
        5:  _op_obscure,
        53: _op_bind,
        43: _op_convert,
        20: _op_lame,
        10: _op_unlock,
        35: _op_reduce,
        49: _op_increase,
        31: _op_break,
        62: _op_mate,
        24: _op_gather,
        6:  _op_push_up,
        26: _op_trapped,
        22: _op_well,
        29: _op_replace,
        46: _op_cast,
        9:  _op_shock,
        36: _op_still,
        52: _op_gradual,
        11: _op_mismatch,
        13: _op_abound,
        44: _op_travel,
        54: _op_penetrate,
        27: _op_joy,
        50: _op_disperse,
        19: _op_throttle,
        51: _op_trust,
        12: _op_micro,
        21: _op_sync,
        42: _op_futu,
    }

    def get_register(self, idx):
        if 0 <= idx < self.NUM_REGISTERS:
            return self.registers[idx]
        return None

    def set_register(self, idx, value):
        if 0 <= idx < self.NUM_REGISTERS:
            self.registers[idx] = value & 0xFFFFFFFF

    def read_heap(self, addr, size=1):
        if 0 <= addr < self.HEAP_SIZE:
            return bytes(self.heap[addr:addr + size])
        return None

    def write_heap(self, addr, data):
        if 0 <= addr and addr + len(data) <= self.HEAP_SIZE:
            self.heap[addr:addr + len(data)] = data
            return True
        return False

    def reset(self):
        self.registers = [0] * self.NUM_REGISTERS
        self.heap_ptr = 0
        self.pc = 0
        self.state = VMState.INIT
        self.flag_zero = False
        self.flag_carry = False
        self.flag_negative = False
        self.flag_overflow = False
        self.futures = {}
        self.future_id_counter = 0
        self.locks = {}
        self.barriers = {}
        self.call_stack = []
        self.cycle_count = 0
        self.energy_cost = 0.0
        self.trace_log = []
        self._init_special_regs()

    def dump_state(self):
        return {
            "pc": self.pc,
            "state": self.state.name,
            "cycle_count": self.cycle_count,
            "energy_cost": self.energy_cost,
            "generation": self.generation,
            "registers": {
                f"R{i}": self.registers[i] for i in range(self.NUM_REGISTERS)
            },
            "heap_ptr": self.heap_ptr,
            "futures": dict(self.futures),
            "locks": dict(self.locks),
            "barriers": dict(self.barriers),
            "flags": {
                "zero": self.flag_zero,
                "carry": self.flag_carry,
                "negative": self.flag_negative,
                "overflow": self.flag_overflow,
            },
        }

    def export_bytecode(self):
        return bytes(self.program)

    def get_backend_status(self):
        """获取后端状态"""
        if self._backend:
            return {
                "use_evomorph": self._use_evomorph,
                "backend_available": self._backend.is_evomorph_available("vm"),
                "backend_status": self._backend.get_status(),
            }
        return {
            "use_evomorph": self._use_evomorph,
            "backend_available": False,
            "message": "使用 Python 实现",
        }
