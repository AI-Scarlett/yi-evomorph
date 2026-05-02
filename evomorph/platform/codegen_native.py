import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set, Any, Callable, Union
from collections import defaultdict


class RegisterType(Enum):
    GENERAL = "general"
    FLOATING = "floating"
    VECTOR = "vector"
    SPECIAL = "special"


@dataclass
class MachineRegister:
    name: str
    index: int
    reg_type: RegisterType
    is_caller_saved: bool = True
    is_reserved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "index": self.index,
            "type": self.reg_type.value,
            "is_caller_saved": self.is_caller_saved,
            "is_reserved": self.is_reserved,
        }


@dataclass
class VirtualRegister:
    vreg_id: int
    reg_type: RegisterType = RegisterType.GENERAL
    assigned_mreg: Optional[MachineRegister] = None
    spill_slot: Optional[int] = None
    live_range: Tuple[int, int] = (0, 0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "vreg_id": self.vreg_id,
            "type": self.reg_type.value,
            "assigned_mreg": self.assigned_mreg.to_dict() if self.assigned_mreg else None,
            "spill_slot": self.spill_slot,
            "live_range": self.live_range,
        }


@dataclass
class MachineInstruction:
    opcode: str
    operands: List[Any] = field(default_factory=list)
    comment: str = ""
    size_bytes: int = 0
    latency_cycles: float = 0.0
    is_branch: bool = False
    is_call: bool = False
    is_return: bool = False
    may_access_memory: bool = False
    is_pseudo: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opcode": self.opcode,
            "operands": [str(o) for o in self.operands],
            "comment": self.comment,
            "size_bytes": self.size_bytes,
            "is_branch": self.is_branch,
            "is_call": self.is_call,
            "is_return": self.is_return,
        }


@dataclass
class BasicBlock:
    label: str
    instructions: List[MachineInstruction] = field(default_factory=list)
    predecessors: List[str] = field(default_factory=list)
    successors: List[str] = field(default_factory=list)
    is_entry: bool = False
    is_exit: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "instructions_count": len(self.instructions),
            "predecessors": list(self.predecessors),
            "successors": list(self.successors),
        }


@dataclass
class ControlFlowGraph:
    blocks: Dict[str, BasicBlock] = field(default_factory=dict)
    entry_block: Optional[str] = None
    exit_blocks: List[str] = field(default_factory=list)
    
    def add_block(self, block: BasicBlock):
        self.blocks[block.label] = block
        if block.is_entry:
            self.entry_block = block.label
        if block.is_exit:
            self.exit_blocks.append(block.label)
    
    def get_block(self, label: str) -> Optional[BasicBlock]:
        return self.blocks.get(label)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "blocks_count": len(self.blocks),
            "entry_block": self.entry_block,
            "exit_blocks": list(self.exit_blocks),
            "blocks": {k: v.to_dict() for k, v in self.blocks.items()},
        }


class RegisterAllocator:
    def __init__(self, machine_registers: List[MachineRegister]):
        self.machine_registers = machine_registers
        self.available_general = [r for r in machine_registers 
                                    if r.reg_type == RegisterType.GENERAL and not r.is_reserved]
        self.available_float = [r for r in machine_registers 
                                  if r.reg_type == RegisterType.FLOATING and not r.is_reserved]
        self.virtual_registers: Dict[int, VirtualRegister] = {}
        self.next_vreg_id = 0
        self.spill_counter = 0
    
    def alloc_virtual(self, reg_type: RegisterType = RegisterType.GENERAL) -> VirtualRegister:
        vreg = VirtualRegister(
            vreg_id=self.next_vreg_id,
            reg_type=reg_type,
        )
        self.virtual_registers[self.next_vreg_id] = vreg
        self.next_vreg_id += 1
        return vreg
    
    def alloc_spill_slot(self, size: int = 8) -> int:
        slot = self.spill_counter * size
        self.spill_counter += 1
        return slot
    
    def linear_scan_allocate(self, 
                               virtual_registers: List[VirtualRegister],
                               instructions: List[MachineInstruction]) -> Dict[int, MachineRegister]:
        sorted_regs = sorted(virtual_registers, key=lambda r: r.live_range[0])
        
        active: List[VirtualRegister] = []
        allocation: Dict[int, MachineRegister] = {}
        
        available = list(self.available_general)
        
        for vreg in sorted_regs:
            active = [r for r in active if r.live_range[1] > vreg.live_range[0]]
            
            if len(active) >= len(available):
                to_spill = max(active, key=lambda r: r.live_range[1])
                active.remove(to_spill)
                
                if to_spill.assigned_mreg:
                    available.append(to_spill.assigned_mreg)
                
                to_spill.spill_slot = self.alloc_spill_slot()
                
                to_spill.assigned_mreg = None
            
            if available:
                mreg = available.pop(0)
                vreg.assigned_mreg = mreg
                allocation[vreg.vreg_id] = mreg
                active.append(vreg)
        
        return allocation
    
    def build_interference_graph(self, 
                                   virtual_registers: List[VirtualRegister],
                                   instructions: List[MachineInstruction]) -> Dict[int, Set[int]]:
        interference: Dict[int, Set[int]] = defaultdict(set)
        
        for i, r1 in enumerate(virtual_registers):
            for j, r2 in enumerate(virtual_registers):
                if i >= j:
                    continue
                
                if self._ranges_overlap(r1.live_range, r2.live_range):
                    interference[r1.vreg_id].add(r2.vreg_id)
                    interference[r2.vreg_id].add(r1.vreg_id)
        
        return interference
    
    def _ranges_overlap(self, r1: Tuple[int, int], r2: Tuple[int, int]) -> bool:
        return not (r1[1] <= r2[0] or r2[1] <= r1[0])


class InstructionSelector:
    def __init__(self, target_arch: str):
        self.target_arch = target_arch
        self.opcode_map: Dict[int, str] = {}
        self._init_opcode_map()
    
    def _init_opcode_map(self):
        if self.target_arch == "x86_64":
            self.opcode_map = {
                63: "call",
                0: "mov",
                59: "mov",
                17: "malloc",
                2: "jmp",
                1: "ret",
                58: "lock",
                61: "pause",
                21: "mfence",
                62: "syscall",
            }
        elif self.target_arch == "arm64":
            self.opcode_map = {
                63: "bl",
                0: "ldr",
                59: "mov",
                17: "bl malloc",
                2: "b",
                1: "ret",
                58: "dmb",
                61: "wfe",
                21: "dsb",
                62: "svc",
            }
    
    def select(self, evo_opcode: int, operands: List[Any]) -> List[MachineInstruction]:
        instructions = []
        
        if evo_opcode in self.opcode_map:
            machine_op = self.opcode_map[evo_opcode]
            
            if evo_opcode == 63:
                instructions.append(MachineInstruction(
                    opcode=machine_op,
                    operands=operands,
                    is_call=True,
                ))
            elif evo_opcode == 1:
                instructions.append(MachineInstruction(
                    opcode=machine_op,
                    operands=[],
                    is_return=True,
                ))
            elif evo_opcode == 2:
                instructions.append(MachineInstruction(
                    opcode=machine_op,
                    operands=operands,
                    is_branch=True,
                ))
            else:
                instructions.append(MachineInstruction(
                    opcode=machine_op,
                    operands=operands,
                    may_access_memory=evo_opcode in (0, 47, 17),
                ))
        
        return instructions


class CodeEmitter:
    def __init__(self, target_arch: str):
        self.target_arch = target_arch
        self.output: List[str] = []
        self.labels: Dict[str, int] = {}
        self.label_counter = 0
    
    def emit_instruction(self, instr: MachineInstruction):
        parts = [f"  {instr.opcode}"]
        
        if instr.operands:
            operand_strs = []
            for op in instr.operands:
                if isinstance(op, MachineRegister):
                    operand_strs.append(op.name)
                elif isinstance(op, VirtualRegister) and op.assigned_mreg:
                    operand_strs.append(op.assigned_mreg.name)
                else:
                    operand_strs.append(str(op))
            parts.append(", ".join(operand_strs))
        
        line = " ".join(parts)
        
        if instr.comment:
            line = f"{line:40}  ; {instr.comment}"
        
        self.output.append(line)
    
    def emit_label(self, label: str):
        self.labels[label] = len(self.output)
        self.output.append(f"{label}:")
    
    def emit_pseudo_op(self, name: str, value: Any):
        if isinstance(value, str):
            self.output.append(f'  {name} "{value}"')
        else:
            self.output.append(f"  {name} {value}")
    
    def emit_section(self, section_name: str):
        self.output.append(f"  .section {section_name}")
    
    def emit_global(self, symbol_name: str):
        self.output.append(f"  .global {symbol_name}")
    
    def emit_align(self, alignment: int):
        self.output.append(f"  .align {alignment}")
    
    def get_assembly(self) -> str:
        return "\n".join(self.output)
    
    def clear(self):
        self.output.clear()
        self.labels.clear()


class MachineCodeGenerator:
    def __init__(self, target_arch: str, platform_profile: Optional[Dict] = None):
        self.target_arch = target_arch
        self.platform_profile = platform_profile or {}
        
        self.machine_registers = self._init_registers()
        self.register_allocator = RegisterAllocator(self.machine_registers)
        self.instruction_selector = InstructionSelector(target_arch)
        self.code_emitter = CodeEmitter(target_arch)
        
        self.cfg: Optional[ControlFlowGraph] = None
        self.liveness_analysis: Dict[int, Tuple[int, int]] = {}
    
    def _init_registers(self) -> List[MachineRegister]:
        if self.target_arch == "x86_64":
            return [
                MachineRegister("rax", 0, RegisterType.GENERAL, is_caller_saved=True),
                MachineRegister("rcx", 1, RegisterType.GENERAL, is_caller_saved=True),
                MachineRegister("rdx", 2, RegisterType.GENERAL, is_caller_saved=True),
                MachineRegister("rsi", 3, RegisterType.GENERAL, is_caller_saved=True),
                MachineRegister("rdi", 4, RegisterType.GENERAL, is_caller_saved=True),
                MachineRegister("r8", 5, RegisterType.GENERAL, is_caller_saved=True),
                MachineRegister("r9", 6, RegisterType.GENERAL, is_caller_saved=True),
                MachineRegister("r10", 7, RegisterType.GENERAL, is_caller_saved=True),
                MachineRegister("r11", 8, RegisterType.GENERAL, is_caller_saved=True),
                MachineRegister("rbx", 9, RegisterType.GENERAL, is_caller_saved=False),
                MachineRegister("rbp", 10, RegisterType.GENERAL, is_caller_saved=False, is_reserved=True),
                MachineRegister("r12", 11, RegisterType.GENERAL, is_caller_saved=False),
                MachineRegister("r13", 12, RegisterType.GENERAL, is_caller_saved=False),
                MachineRegister("r14", 13, RegisterType.GENERAL, is_caller_saved=False),
                MachineRegister("r15", 14, RegisterType.GENERAL, is_caller_saved=False),
                MachineRegister("rsp", 15, RegisterType.GENERAL, is_reserved=True),
                MachineRegister("xmm0", 0, RegisterType.FLOATING, is_caller_saved=True),
                MachineRegister("xmm1", 1, RegisterType.FLOATING, is_caller_saved=True),
                MachineRegister("xmm2", 2, RegisterType.FLOATING, is_caller_saved=True),
                MachineRegister("xmm3", 3, RegisterType.FLOATING, is_caller_saved=True),
            ]
        elif self.target_arch == "arm64":
            general_regs = []
            for i in range(31):
                is_caller = i < 19
                is_reserved = i in (29, 30)
                general_regs.append(MachineRegister(
                    f"x{i}", i, RegisterType.GENERAL,
                    is_caller_saved=is_caller,
                    is_reserved=is_reserved
                ))
            
            float_regs = []
            for i in range(32):
                float_regs.append(MachineRegister(
                    f"q{i}", i, RegisterType.VECTOR,
                    is_caller_saved=i < 16
                ))
            
            return general_regs + float_regs
        
        return []
    
    def generate_from_instructions(self, 
                                     evo_instructions: List[Dict],
                                     function_name: str = "evomorph_func") -> str:
        self.code_emitter.clear()
        
        if self.target_arch == "x86_64":
            self.code_emitter.emit_section(".text")
            self.code_emitter.emit_global(function_name)
            self.code_emitter.emit_align(16)
            self.code_emitter.emit_label(function_name)
            
            self.code_emitter.emit_instruction(MachineInstruction(
                opcode="push",
                operands=["rbp"],
                comment="保存帧指针"
            ))
            self.code_emitter.emit_instruction(MachineInstruction(
                opcode="mov",
                operands=["rbp", "rsp"],
                comment="设置新帧指针"
            ))
        
        elif self.target_arch == "arm64":
            self.code_emitter.emit_section(".text")
            self.code_emitter.emit_global(function_name)
            self.code_emitter.emit_align(4)
            self.code_emitter.emit_label(function_name)
            
            self.code_emitter.emit_instruction(MachineInstruction(
                opcode="stp",
                operands=["x29", "x30", "[sp, #-16]!"],
                comment="保存帧指针和链接寄存器"
            ))
            self.code_emitter.emit_instruction(MachineInstruction(
                opcode="mov",
                operands=["x29", "sp"],
                comment="设置帧指针"
            ))
        
        for evo_instr in evo_instructions:
            opcode = evo_instr.get("opcode", 0)
            operands = evo_instr.get("operands", [])
            comment = evo_instr.get("comment", "")
            
            machine_instrs = self.instruction_selector.select(opcode, operands)
            
            for instr in machine_instrs:
                if comment:
                    instr.comment = f"{comment} (䷗{opcode:02X})"
                else:
                    instr.comment = f"䷗{opcode:02X}"
                self.code_emitter.emit_instruction(instr)
        
        if self.target_arch == "x86_64":
            self.code_emitter.emit_instruction(MachineInstruction(
                opcode="xor",
                operands=["rax", "rax"],
                comment="返回0"
            ))
            self.code_emitter.emit_instruction(MachineInstruction(
                opcode="pop",
                operands=["rbp"],
                comment="恢复帧指针"
            ))
            self.code_emitter.emit_instruction(MachineInstruction(
                opcode="ret",
                operands=[],
                is_return=True
            ))
        
        elif self.target_arch == "arm64":
            self.code_emitter.emit_instruction(MachineInstruction(
                opcode="mov",
                operands=["x0", "#0"],
                comment="返回0"
            ))
            self.code_emitter.emit_instruction(MachineInstruction(
                opcode="ldp",
                operands=["x29", "x30", "[sp], #16"],
                comment="恢复帧指针和链接寄存器"
            ))
            self.code_emitter.emit_instruction(MachineInstruction(
                opcode="ret",
                operands=[],
                is_return=True
            ))
        
        return self.code_emitter.get_assembly()
    
    def generate_object_file(self, 
                               assembly_code: str,
                               output_path: str,
                               optimize: bool = False) -> bool:
        import subprocess
        import os
        
        asm_path = f"{output_path}.s"
        
        with open(asm_path, 'w') as f:
            f.write(assembly_code)
        
        try:
            if self.target_arch == "x86_64":
                cmd = ["gcc", "-c", "-o", output_path, asm_path]
                if optimize:
                    cmd.insert(1, "-O2")
                result = subprocess.run(cmd, capture_output=True, text=True)
            elif self.target_arch == "arm64":
                cmd = ["clang", "-c", "-target", "arm64-apple-darwin", "-o", output_path, asm_path]
                if optimize:
                    cmd.insert(1, "-O2")
                result = subprocess.run(cmd, capture_output=True, text=True)
            else:
                return False
            
            return result.returncode == 0
        except Exception:
            return False
        finally:
            if os.path.exists(asm_path):
                os.remove(asm_path)


class JITCompiler:
    def __init__(self, target_arch: str):
        self.target_arch = target_arch
        self.code_generator = MachineCodeGenerator(target_arch)
        self.compiled_functions: Dict[str, Any] = {}
    
    def compile_function(self, 
                          evo_instructions: List[Dict],
                          function_name: str) -> Optional[Callable]:
        try:
            import ctypes
            import tempfile
            import os
            
            assembly = self.code_generator.generate_from_instructions(
                evo_instructions, function_name
            )
            
            with tempfile.NamedTemporaryFile(suffix='.s', mode='w', delete=False) as f:
                f.write(assembly)
                asm_path = f.name
            
            obj_path = asm_path + '.o'
            so_path = asm_path + '.so'
            
            import subprocess
            
            if self.target_arch == "x86_64":
                subprocess.run(["gcc", "-shared", "-fPIC", "-o", so_path, asm_path], 
                              capture_output=True)
            elif self.target_arch == "arm64":
                subprocess.run(["clang", "-shared", "-fPIC", "-o", so_path, asm_path],
                              capture_output=True)
            
            if os.path.exists(so_path):
                lib = ctypes.CDLL(so_path)
                func = getattr(lib, function_name)
                self.compiled_functions[function_name] = {
                    "library": lib,
                    "function": func,
                    "so_path": so_path,
                }
                
                os.unlink(asm_path)
                os.unlink(obj_path)
                
                return func
            
            return None
            
        except Exception:
            return None
    
    def get_function(self, name: str) -> Optional[Callable]:
        if name in self.compiled_functions:
            return self.compiled_functions[name]["function"]
        return None
    
    def cleanup(self):
        for name, info in self.compiled_functions.items():
            try:
                import os
                if "so_path" in info and os.path.exists(info["so_path"]):
                    os.unlink(info["so_path"])
            except Exception:
                pass
        self.compiled_functions.clear()
