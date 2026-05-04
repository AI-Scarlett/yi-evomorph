from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Union
from abc import ABC, abstractmethod


class IRNodeType(Enum):
    PROGRAM = auto()
    LOCUS = auto()
    META_LOCUS = auto()
    BASIC_BLOCK = auto()
    INSTRUCTION = auto()
    OPERAND = auto()
    PHI = auto()
    CONSTANT = auto()
    LABEL = auto()


class OperandType(Enum):
    REGISTER = auto()
    IMMEDIATE = auto()
    LABEL = auto()
    MEMORY = auto()
    PHI = auto()


@dataclass
class IROperand:
    type: OperandType
    value: Any
    name: Optional[str] = None
    
    def __repr__(self):
        if self.type == OperandType.REGISTER:
            return f"%{self.name or self.value}"
        elif self.type == OperandType.IMMEDIATE:
            return f"#{self.value}"
        elif self.type == OperandType.LABEL:
            return f"@{self.name or self.value}"
        elif self.type == OperandType.MEMORY:
            return f"mem[{self.value}]"
        elif self.type == OperandType.PHI:
            return f"phi({self.value})"
        return str(self.value)


@dataclass
class IRInstruction:
    opcode: int
    mnemonic: str
    symbol: str
    operands: List[IROperand] = field(default_factory=list)
    modifier: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self):
        op_str = ", ".join(str(op) for op in self.operands)
        return f"{self.symbol} {self.mnemonic} {op_str}"
    
    def clone(self) -> 'IRInstruction':
        return IRInstruction(
            opcode=self.opcode,
            mnemonic=self.mnemonic,
            symbol=self.symbol,
            operands=[IROperand(op.type, op.value, op.name) for op in self.operands],
            modifier=self.modifier,
            metadata=dict(self.metadata)
        )


@dataclass
class IRPhiNode:
    dest: IROperand
    sources: Dict[str, IROperand] = field(default_factory=dict)
    
    def __repr__(self):
        sources_str = ", ".join(f"{label}: {val}" for label, val in self.sources.items())
        return f"{self.dest} = phi({sources_str})"


@dataclass
class IRBasicBlock:
    label: str
    instructions: List[Union[IRInstruction, IRPhiNode]] = field(default_factory=list)
    predecessors: List[str] = field(default_factory=list)
    successors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self):
        return f"BB.{self.label}: {len(self.instructions)} instrs"
    
    def add_instruction(self, instr: Union[IRInstruction, IRPhiNode]):
        self.instructions.append(instr)
    
    def get_last_instruction(self) -> Optional[Union[IRInstruction, IRPhiNode]]:
        if self.instructions:
            return self.instructions[-1]
        return None
    
    def is_terminated(self) -> bool:
        last = self.get_last_instruction()
        if last is None:
            return False
        if isinstance(last, IRPhiNode):
            return False
        branch_ops = {2, 1, 56, 31, 60}
        return last.opcode in branch_ops


@dataclass
class IRLocus:
    name: str
    basic_blocks: Dict[str, IRBasicBlock] = field(default_factory=dict)
    entry_block: Optional[str] = None
    mut_rate: float = 0.02
    cross_pool: str = "default"
    fitness_terms: List[Dict[str, Any]] = field(default_factory=list)
    env_targets: List[str] = field(default_factory=list)
    max_generations: int = 100
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self):
        return f"Locus {self.name}: {len(self.basic_blocks)} blocks"
    
    def add_basic_block(self, label: str) -> IRBasicBlock:
        if label in self.basic_blocks:
            return self.basic_blocks[label]
        block = IRBasicBlock(label=label)
        self.basic_blocks[label] = block
        if self.entry_block is None:
            self.entry_block = label
        return block
    
    def get_block_order(self) -> List[str]:
        if self.entry_block is None:
            return []
        
        visited = set()
        order = []
        stack = [self.entry_block]
        
        while stack:
            label = stack.pop()
            if label in visited:
                continue
            visited.add(label)
            order.append(label)
            
            if label in self.basic_blocks:
                block = self.basic_blocks[label]
                for succ in reversed(block.successors):
                    if succ not in visited:
                        stack.append(succ)
        
        return order


@dataclass
class IRProgram:
    version: str = "3.0"
    loci: Dict[str, IRLocus] = field(default_factory=dict)
    meta_loci: Dict[str, IRLocus] = field(default_factory=dict)
    xiangci: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self):
        return f"IR Program v{self.version}: {len(self.loci)} loci, {len(self.meta_loci)} meta loci"
    
    def add_locus(self, locus: IRLocus):
        self.loci[locus.name] = locus
    
    def add_meta_locus(self, locus: IRLocus):
        self.meta_loci[locus.name] = locus


class IROptimizationPass(ABC):
    @abstractmethod
    def run(self, program: IRProgram) -> int:
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        pass


class DeadCodeEliminationPass(IROptimizationPass):
    def get_name(self) -> str:
        return "Dead Code Elimination"
    
    def run(self, program: IRProgram) -> int:
        total_removed = 0
        
        for locus in list(program.loci.values()) + list(program.meta_loci.values()):
            for block in locus.basic_blocks.values():
                used_values = self._find_used_values(block)
                removed = self._remove_unused_instructions(block, used_values)
                total_removed += removed
        
        return total_removed
    
    def _find_used_values(self, block: IRBasicBlock) -> Set[str]:
        used = set()
        
        for instr in reversed(block.instructions):
            if isinstance(instr, IRPhiNode):
                for val in instr.sources.values():
                    if val.type == OperandType.REGISTER:
                        used.add(str(val))
            elif isinstance(instr, IRInstruction):
                for op in instr.operands:
                    if op.type == OperandType.REGISTER:
                        used.add(str(op))
        
        return used
    
    def _remove_unused_instructions(self, block: IRBasicBlock, used: Set[str]) -> int:
        removed = 0
        new_instrs = []
        
        for instr in block.instructions:
            if isinstance(instr, IRPhiNode):
                if str(instr.dest) in used:
                    new_instrs.append(instr)
                else:
                    removed += 1
            elif isinstance(instr, IRInstruction):
                if instr.opcode in {2, 1, 56, 31, 60, 17, 47, 50, 54, 45}:
                    new_instrs.append(instr)
                elif len(instr.operands) > 0 and str(instr.operands[0]) in used:
                    new_instrs.append(instr)
                else:
                    removed += 1
        
        block.instructions = new_instrs
        return removed


class ConstantFoldingPass(IROptimizationPass):
    def get_name(self) -> str:
        return "Constant Folding"
    
    def run(self, program: IRProgram) -> int:
        total_folded = 0
        
        for locus in list(program.loci.values()) + list(program.meta_loci.values()):
            for block in locus.basic_blocks.values():
                folded = self._fold_constants_in_block(block)
                total_folded += folded
        
        return total_folded
    
    def _fold_constants_in_block(self, block: IRBasicBlock) -> int:
        folded = 0
        new_instrs = []
        
        for instr in block.instructions:
            if isinstance(instr, IRInstruction):
                if self._can_fold(instr):
                    new_instr = self._fold_instruction(instr)
                    if new_instr != instr:
                        new_instrs.append(new_instr)
                        folded += 1
                        continue
            new_instrs.append(instr)
        
        block.instructions = new_instrs
        return folded
    
    def _can_fold(self, instr: IRInstruction) -> bool:
        arithmetic_ops = {24, 49, 35, 3, 16, 37, 55, 7}
        if instr.opcode not in arithmetic_ops:
            return False
        
        for op in instr.operands:
            if op.type != OperandType.IMMEDIATE and op.type != OperandType.REGISTER:
                return False
        
        return True
    
    def _fold_instruction(self, instr: IRInstruction) -> IRInstruction:
        if len(instr.operands) < 2:
            return instr
        
        op1 = instr.operands[0]
        op2 = instr.operands[1]
        
        if op1.type != OperandType.IMMEDIATE or op2.type != OperandType.IMMEDIATE:
            return instr
        
        val1 = int(op1.value)
        val2 = int(op2.value)
        result = 0
        
        if instr.opcode == 24:
            result = val1 + val2
        elif instr.opcode == 49:
            result = val1 + val2
        elif instr.opcode == 35:
            result = val1 - val2
        elif instr.opcode == 3:
            result = val1 & val2
        elif instr.opcode == 16:
            result = val1 | val2
        elif instr.opcode == 37:
            result = val1 ^ val2
        elif instr.opcode == 55:
            result = val1 << val2
        elif instr.opcode == 7:
            result = val1 >> val2
        
        new_instr = instr.clone()
        new_instr.operands = [
            IROperand(OperandType.REGISTER, 0, "R0"),
            IROperand(OperandType.IMMEDIATE, result)
        ]
        return new_instr


class CopyPropagationPass(IROptimizationPass):
    def get_name(self) -> str:
        return "Copy Propagation"
    
    def run(self, program: IRProgram) -> int:
        total_propagated = 0
        
        for locus in list(program.loci.values()) + list(program.meta_loci.values()):
            for block in locus.basic_blocks.values():
                propagated = self._propagate_copies(block)
                total_propagated += propagated
        
        return total_propagated
    
    def _propagate_copies(self, block: IRBasicBlock) -> int:
        propagated = 0
        copies: Dict[str, IROperand] = {}
        
        for i, instr in enumerate(block.instructions):
            if isinstance(instr, IRInstruction):
                copy_ops = {25, 61, 15, 53, 43, 29, 46}
                if instr.opcode in copy_ops and len(instr.operands) >= 2:
                    dst = instr.operands[0]
                    src = instr.operands[1]
                    if dst.type == OperandType.REGISTER and src.type in (OperandType.REGISTER, OperandType.IMMEDIATE):
                        copies[str(dst)] = src
                        propagated += 1
                
                for j, op in enumerate(instr.operands):
                    if op.type == OperandType.REGISTER:
                        op_str = str(op)
                        if op_str in copies:
                            instr.operands[j] = copies[op_str].clone()
        
        return propagated


class LoopOptimizationPass(IROptimizationPass):
    def get_name(self) -> str:
        return "Loop Optimization"
    
    def run(self, program: IRProgram) -> int:
        total_optimized = 0
        
        for locus in list(program.loci.values()) + list(program.meta_loci.values()):
            loops = self._find_loops(locus)
            for loop in loops:
                optimized = self._optimize_loop(locus, loop)
                total_optimized += optimized
        
        return total_optimized
    
    def _find_loops(self, locus: IRLocus) -> List[List[str]]:
        loops = []
        visited = set()
        stack = []
        
        def dfs(label: str):
            if label in visited:
                if label in stack:
                    idx = stack.index(label)
                    loop = stack[idx:]
                    loops.append(loop)
                return
            
            visited.add(label)
            stack.append(label)
            
            if label in locus.basic_blocks:
                for succ in locus.basic_blocks[label].successors:
                    dfs(succ)
            
            stack.pop()
        
        if locus.entry_block:
            dfs(locus.entry_block)
        
        return loops
    
    def _optimize_loop(self, locus: IRLocus, loop: List[str]) -> int:
        optimized = 0
        
        if len(loop) <= 2:
            for label in loop:
                if label in locus.basic_blocks:
                    block = locus.basic_blocks[label]
                    for instr in block.instructions:
                        if isinstance(instr, IRInstruction):
                            if instr.opcode == 24 and len(instr.operands) >= 2:
                                src = instr.operands[1]
                                if src.type == OperandType.IMMEDIATE and src.value == 1:
                                    instr.opcode = 40
                                    instr.mnemonic = "ADVANCE"
                                    instr.symbol = "䷢"
                                    optimized += 1
        
        return optimized


class StrengthReductionPass(IROptimizationPass):
    def get_name(self) -> str:
        return "Strength Reduction"
    
    def run(self, program: IRProgram) -> int:
        total_reduced = 0
        
        for locus in list(program.loci.values()) + list(program.meta_loci.values()):
            for block in locus.basic_blocks.values():
                reduced = self._reduce_strength(block)
                total_reduced += reduced
        
        return total_reduced
    
    def _reduce_strength(self, block: IRBasicBlock) -> int:
        reduced = 0
        new_instrs = []
        
        for instr in block.instructions:
            if isinstance(instr, IRInstruction):
                if instr.opcode == 55 and len(instr.operands) >= 2:
                    src = instr.operands[1]
                    if src.type == OperandType.IMMEDIATE:
                        if src.value == 1:
                            new_instr = instr.clone()
                            new_instr.opcode = 24
                            new_instr.mnemonic = "GATHER"
                            new_instr.symbol = "䷬"
                            if len(new_instr.operands) >= 2:
                                new_instr.operands[1] = IROperand(OperandType.REGISTER, 
                                    int(new_instr.operands[0].value) if new_instr.operands[0].type == OperandType.REGISTER else 0,
                                    new_instr.operands[0].name)
                            new_instrs.append(new_instr)
                            reduced += 1
                            continue
                
                if instr.opcode == 7 and len(instr.operands) >= 2:
                    src = instr.operands[1]
                    if src.type == OperandType.IMMEDIATE:
                        if src.value == 1:
                            new_instr = instr.clone()
                            new_instr.opcode = 35
                            new_instr.mnemonic = "REDUCE"
                            new_instr.symbol = "䷨"
                            if len(new_instr.operands) >= 2:
                                new_instr.operands[1] = IROperand(OperandType.IMMEDIATE, 1)
                            new_instrs.append(new_instr)
                            reduced += 1
                            continue
            
            new_instrs.append(instr)
        
        block.instructions = new_instrs
        return reduced


class IROptimizer:
    def __init__(self, level: int = 1):
        self.level = level
        self.passes: List[IROptimizationPass] = []
        self._setup_passes()
    
    def _setup_passes(self):
        if self.level >= 1:
            self.passes.append(CopyPropagationPass())
            self.passes.append(DeadCodeEliminationPass())
        
        if self.level >= 2:
            self.passes.append(ConstantFoldingPass())
            self.passes.append(StrengthReductionPass())
        
        if self.level >= 3:
            self.passes.append(LoopOptimizationPass())
    
    def optimize(self, program: IRProgram) -> Dict[str, int]:
        results = {}
        
        for pass_ in self.passes:
            count = pass_.run(program)
            results[pass_.get_name()] = count
        
        return results
    
    def add_pass(self, pass_: IROptimizationPass):
        self.passes.append(pass_)


class IRBuilder:
    def __init__(self, isa=None):
        self.isa = isa
        self._register_counter = 0
    
    def create_operand(self, kind: str, value: Any, name: Optional[str] = None) -> IROperand:
        type_map = {
            "register": OperandType.REGISTER,
            "immediate": OperandType.IMMEDIATE,
            "label": OperandType.LABEL,
            "memory": OperandType.MEMORY,
            "phi": OperandType.PHI,
        }
        return IROperand(type_map.get(kind, OperandType.IMMEDIATE), value, name)
    
    def create_instruction(self, opcode: int, mnemonic: str, symbol: str,
                           operands: List[IROperand] = None,
                           modifier: int = 0) -> IRInstruction:
        return IRInstruction(
            opcode=opcode,
            mnemonic=mnemonic,
            symbol=symbol,
            operands=operands or [],
            modifier=modifier
        )
    
    def create_phi(self, dest: IROperand, sources: Dict[str, IROperand] = None) -> IRPhiNode:
        return IRPhiNode(dest=dest, sources=sources or {})
    
    def create_basic_block(self, label: str) -> IRBasicBlock:
        return IRBasicBlock(label=label)
    
    def create_locus(self, name: str) -> IRLocus:
        return IRLocus(name=name)
    
    def create_program(self, version: str = "3.0") -> IRProgram:
        return IRProgram(version=version)
    
    def new_register(self, prefix: str = "t") -> IROperand:
        self._register_counter += 1
        return IROperand(OperandType.REGISTER, self._register_counter, f"{prefix}{self._register_counter}")
