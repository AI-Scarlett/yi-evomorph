import time
from typing import Dict, List, Optional, Any
from evomorph.vm.virtual_machine import IChingVM, VMState
from evomorph.hexagrams import HexagramInstructionSet


class Breakpoint:
    def __init__(self, bp_type: str, target: Any, condition: Optional[str] = None):
        self.bp_type = bp_type
        self.target = target
        self.condition = condition
        self.hit_count = 0
        self.enabled = True


class EvolutionSnapshot:
    def __init__(self, generation: int, individual_data: Dict, fitness: float):
        self.generation = generation
        self.individual_data = individual_data
        self.fitness = fitness
        self.timestamp = time.time()


class YaoJingDebugger:
    def __init__(self, vm: Optional[IChingVM] = None):
        self.vm = vm or IChingVM()
        self.isa = HexagramInstructionSet()
        self.breakpoints: List[Breakpoint] = []
        self.evolution_history: List[EvolutionSnapshot] = []
        self.watch_registers: List[int] = []
        self.watch_memory: List[tuple] = []
        self.step_count = 0
        self.paused = False
        self.reverse_stack: List[Dict] = []

    def attach(self, vm: IChingVM):
        self.vm = vm

    def add_breakpoint(self, bp_type: str, target: Any, condition: Optional[str] = None) -> int:
        bp = Breakpoint(bp_type, target, condition)
        self.breakpoints.append(bp)
        return len(self.breakpoints) - 1

    def remove_breakpoint(self, bp_id: int):
        if 0 <= bp_id < len(self.breakpoints):
            self.breakpoints[bp_id].enabled = False

    def add_address_breakpoint(self, address: int) -> int:
        return self.add_breakpoint("address", address)

    def add_generation_breakpoint(self, generation: int) -> int:
        return self.add_breakpoint("generation", generation)

    def add_opcode_breakpoint(self, opcode: int) -> int:
        return self.add_breakpoint("opcode", opcode)

    def add_fitness_breakpoint(self, threshold: float) -> int:
        return self.add_breakpoint("fitness_threshold", threshold)

    def step_instruction(self):
        if self.vm:
            state_before = self.vm.dump_state()
            self.reverse_stack.append(state_before)
            if len(self.reverse_stack) > 1000:
                self.reverse_stack.pop(0)
            self.vm.step()
            self.step_count += 1
            self._check_breakpoints()

    def step_generation(self, engine):
        if engine:
            stats = engine.evolve_one_generation()
            snapshot = EvolutionSnapshot(
                generation=stats["generation"],
                individual_data=engine.get_population_stats(),
                fitness=stats["best_fitness"],
            )
            self.evolution_history.append(snapshot)
            self._check_breakpoints()
            return stats
        return None

    def continue_execution(self, max_cycles: int = 10000):
        if not self.vm:
            return
        for _ in range(max_cycles):
            if self.paused:
                break
            self.step_instruction()
            if self.vm.state in (VMState.HALTED, VMState.ERROR, VMState.TRAPPED):
                break

    def reverse_step(self):
        if self.reverse_stack:
            state = self.reverse_stack.pop()
            self._restore_state(state)
            return True
        return False

    def _restore_state(self, state: Dict):
        if not self.vm:
            return
        self.vm.pc = state["pc"]
        for i, (name, val) in enumerate(state["registers"].items()):
            self.vm.registers[i] = val
        self.vm.cycle_count = state["cycle_count"]
        self.vm.energy_cost = state["energy_cost"]
        self.vm.generation = state["generation"]

    def _check_breakpoints(self):
        for bp in self.breakpoints:
            if not bp.enabled:
                continue
            if bp.bp_type == "address" and self.vm and self.vm.pc == bp.target:
                bp.hit_count += 1
                self.paused = True
                return
            elif bp.bp_type == "opcode" and self.vm:
                if self.vm.pc < len(self.vm.program):
                    byte1 = self.vm.program[self.vm.pc]
                    current_opcode = (byte1 >> 2) & 0x3F
                    if current_opcode == bp.target:
                        bp.hit_count += 1
                        self.paused = True
                        return
            elif bp.bp_type == "generation":
                if self.evolution_history and self.evolution_history[-1].generation >= bp.target:
                    bp.hit_count += 1
                    self.paused = True
                    return
            elif bp.bp_type == "fitness_threshold":
                if self.evolution_history and self.evolution_history[-1].fitness >= bp.target:
                    bp.hit_count += 1
                    self.paused = True
                    return

    def watch_register(self, reg_idx: int):
        if reg_idx not in self.watch_registers:
            self.watch_registers.append(reg_idx)

    def watch_memory(self, addr: int, size: int = 4):
        self.watch_memory.append((addr, size))

    def get_watched_values(self) -> Dict:
        result = {"registers": {}, "memory": {}}
        if self.vm:
            for reg_idx in self.watch_registers:
                result["registers"][f"R{reg_idx}"] = self.vm.get_register(reg_idx)
            for addr, size in self.watch_memory:
                data = self.vm.read_heap(addr, size)
                if data:
                    result["memory"][hex(addr)] = data.hex()
        return result

    def explain_instruction(self, pc: Optional[int] = None) -> str:
        if not self.vm:
            return "No VM attached"
        target_pc = pc if pc is not None else self.vm.pc
        if target_pc + 1 >= len(self.vm.program):
            return "PC out of bounds"
        byte1 = self.vm.program[target_pc]
        byte2 = self.vm.program[target_pc + 1]
        opcode = (byte1 >> 2) & 0x3F
        modifier = ((byte1 & 0x03) << 4) | (byte2 & 0x0F)
        entry = self.isa.get_by_opcode(opcode)
        if entry:
            yao = entry["yao"]
            return (f"PC={target_pc} | {entry['symbol']} {entry['mnemonic']} "
                    f"(爻:{yao}) | 卦名:{entry['cn_name']} | "
                    f"义理:{entry['description']} | 修饰:{modifier}")
        return f"PC={target_pc} | Unknown opcode: {opcode:#04x}"

    def query_natural_language(self, question: str) -> str:
        if not self.vm:
            return "无虚拟机附加"
        state = self.vm.dump_state()
        q_lower = question.lower()
        if any(kw in q_lower for kw in ("功耗", "energy", "电")):
            return (f"当前累计能耗: {state['energy_cost']:.2f} 单位。"
                    f"运行周期: {state['cycle_count']}。"
                    f"平均每周期能耗: {state['energy_cost']/max(state['cycle_count'],1):.4f}")
        elif any(kw in q_lower for kw in ("寄存器", "register", "r0", "r1")):
            regs = state["registers"]
            lines = [f"  {k} = {v}" for k, v in regs.items() if v != 0]
            return "非零寄存器:\n" + "\n".join(lines) if lines else "所有寄存器为零"
        elif any(kw in q_lower for kw in ("状态", "state", "运行")):
            return (f"虚拟机状态: {state['state']}\n"
                    f"PC: {state['pc']}\n"
                    f"周期: {state['cycle_count']}\n"
                    f"能耗: {state['energy_cost']:.2f}")
        elif any(kw in q_lower for kw in ("进化", "evolution", "适应度")):
            if self.evolution_history:
                latest = self.evolution_history[-1]
                return (f"最新代数: {latest.generation}\n"
                        f"最佳适应度: {latest.fitness:.4f}\n"
                        f"快照时间: {time.strftime('%H:%M:%S', time.localtime(latest.timestamp))}")
            return "暂无进化历史"
        else:
            return (f"当前状态: PC={state['pc']}, 周期={state['cycle_count']}, "
                    f"能耗={state['energy_cost']:.2f}, 状态={state['state']}")

    def get_yao_visualization(self, pc: Optional[int] = None) -> str:
        if not self.vm:
            return ""
        target_pc = pc if pc is not None else self.vm.pc
        if target_pc + 1 >= len(self.vm.program):
            return ""
        byte1 = self.vm.program[target_pc]
        opcode = (byte1 >> 2) & 0x3F
        entry = self.isa.get_by_opcode(opcode)
        if not entry:
            return ""
        bits = format(opcode, "06b")
        lines = []
        lines.append(f"  {entry['symbol']} {entry['mnemonic']}")
        for i, b in enumerate(bits):
            yao_char = "⚊ 阳爻" if b == "1" else "⚋ 阴爻"
            position_names = ["操作码·高位", "操作码·中位", "操作码·低位",
                              "源操作数·高", "源操作数·低", "目的/修饰"]
            lines.append(f"  第{6-i}爻: {yao_char}  ← {position_names[i]}")
        return "\n".join(lines)

    def get_evolution_trace(self, last_n: int = 10) -> List[Dict]:
        return [
            {
                "generation": s.generation,
                "fitness": s.fitness,
                "timestamp": s.timestamp,
                "data": s.individual_data,
            }
            for s in self.evolution_history[-last_n:]
        ]
