import random
import copy
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set, Callable, Any
from evomorph.hexagrams import HexagramInstructionSet
from evomorph.hexagrams.instruction_set import (
    HEXAGRAM_TABLE, HEXAGRAM_CATEGORIES, MODIFIERS,
    CATEGORY_YUAN, CATEGORY_HENG, CATEGORY_LI, CATEGORY_ZHEN
)
from evomorph.evolution.engine import GeneInstruction


class InstructionRole(Enum):
    CONTROL_FLOW = "control_flow"
    MEMORY = "memory"
    COMPUTATION = "computation"
    SYNCHRONIZATION = "synchronization"
    IO = "io"
    THREAD = "thread"
    EVOLUTION = "evolution"
    METADATA = "metadata"


class InstructionSemantics:
    def __init__(self):
        self.isa = HexagramInstructionSet()
        self._build_semantic_maps()
    
    def _build_semantic_maps(self):
        self.category_to_opcodes: Dict[str, List[int]] = copy.deepcopy(HEXAGRAM_CATEGORIES)
        
        self.opcode_to_category: Dict[int, str] = {}
        for cat, opcodes in HEXAGRAM_CATEGORIES.items():
            for opcode in opcodes:
                self.opcode_to_category[opcode] = cat
        
        self.role_to_opcodes: Dict[InstructionRole, Set[int]] = {
            InstructionRole.CONTROL_FLOW: {2, 1, 56, 31, 36},
            InstructionRole.MEMORY: {17, 34, 47, 6, 22, 54, 50},
            InstructionRole.COMPUTATION: {59, 38, 48, 41, 37, 32, 57, 35, 49, 62, 24, 52, 13, 12},
            InstructionRole.SYNCHRONIZATION: {58, 61, 21, 39, 4, 10, 20, 36},
            InstructionRole.IO: {0, 45, 14, 28},
            InstructionRole.THREAD: {63},
            InstructionRole.EVOLUTION: {38, 62, 9},
            InstructionRole.METADATA: {48, 35},
        }
        
        self.opcode_to_role: Dict[int, Set[InstructionRole]] = {}
        for role, opcodes in self.role_to_opcodes.items():
            for opcode in opcodes:
                if opcode not in self.opcode_to_role:
                    self.opcode_to_role[opcode] = set()
                self.opcode_to_role[opcode].add(role)
        
        self.equivalent_groups: List[Set[int]] = [
            {58, 10, 39},
            {61, 21},
            {6, 22, 54},
            {63, 34},
            {47, 50},
        ]
        
        self.opcode_to_equivalents: Dict[int, Set[int]] = {}
        for group in self.equivalent_groups:
            for opcode in group:
                self.opcode_to_equivalents[opcode] = group - {opcode}
        
        self.context_transitions: Dict[int, List[int]] = {
            63: [61, 21, 0],
            0: [17, 47],
            17: [47, 59],
            61: [21, 47],
            21: [1, 56],
            47: [21, 1],
        }
    
    def get_category(self, opcode: int) -> Optional[str]:
        return self.opcode_to_category.get(opcode)
    
    def get_roles(self, opcode: int) -> Set[InstructionRole]:
        return self.opcode_to_role.get(opcode, set())
    
    def get_same_category_opcodes(self, opcode: int) -> List[int]:
        cat = self.get_category(opcode)
        if cat:
            opcodes = self.category_to_opcodes.get(cat, [])
            return [o for o in opcodes if o != opcode]
        return []
    
    def get_same_role_opcodes(self, opcode: int) -> List[int]:
        roles = self.get_roles(opcode)
        same_role = set()
        for role in roles:
            same_role.update(self.role_to_opcodes.get(role, set()))
        same_role.discard(opcode)
        return list(same_role)
    
    def get_equivalent_opcodes(self, opcode: int) -> List[int]:
        return list(self.opcode_to_equivalents.get(opcode, set()))
    
    def get_contextually_valid_followers(self, opcode: int) -> List[int]:
        return self.context_transitions.get(opcode, self.get_all_opcodes())
    
    def get_all_opcodes(self) -> List[int]:
        return [row[0] for row in HEXAGRAM_TABLE]
    
    def is_semantically_valid_mutation(self, from_opcode: int, to_opcode: int) -> bool:
        if from_opcode == to_opcode:
            return True
        
        from_cat = self.get_category(from_opcode)
        to_cat = self.get_category(to_opcode)
        
        if from_cat == to_cat:
            return True
        
        from_roles = self.get_roles(from_opcode)
        to_roles = self.get_roles(to_opcode)
        
        if from_roles & to_roles:
            return True
        
        equivalents = self.get_equivalent_opcodes(from_opcode)
        if to_opcode in equivalents:
            return True
        
        return False
    
    def get_possible_mutations(self, opcode: int, 
                                 same_category_weight: float = 0.5,
                                 same_role_weight: float = 0.3,
                                 equivalent_weight: float = 0.15,
                                 any_weight: float = 0.05) -> List[Tuple[int, float]]:
        mutations = []
        
        same_category = self.get_same_category_opcodes(opcode)
        for o in same_category:
            mutations.append((o, same_category_weight))
        
        same_role = self.get_same_role_opcodes(opcode)
        for o in same_role:
            if o not in [m[0] for m in mutations]:
                mutations.append((o, same_role_weight))
        
        equivalents = self.get_equivalent_opcodes(opcode)
        for o in equivalents:
            if o not in [m[0] for m in mutations]:
                mutations.append((o, equivalent_weight))
        
        all_opcodes = self.get_all_opcodes()
        existing = {m[0] for m in mutations}
        existing.add(opcode)
        for o in all_opcodes:
            if o not in existing:
                mutations.append((o, any_weight))
        
        return mutations
    
    def select_semantic_mutation(self, opcode: int, rng: random.Random) -> int:
        mutations = self.get_possible_mutations(opcode)
        if not mutations:
            return opcode
        
        total_weight = sum(m[1] for m in mutations)
        r = rng.random() * total_weight
        cumulative = 0.0
        for target_opcode, weight in mutations:
            cumulative += weight
            if r <= cumulative:
                return target_opcode
        
        return mutations[-1][0]


@dataclass
class SemanticMutationConfig:
    use_semantic_mutation: bool = True
    same_category_prob: float = 0.6
    same_role_prob: float = 0.25
    equivalent_prob: float = 0.1
    random_prob: float = 0.05
    
    preserve_control_flow: bool = True
    preserve_memory_access: bool = False
    context_aware: bool = True
    
    modifier_semantic_match: bool = True


class SemanticMutationEngine:
    def __init__(self, config: Optional[SemanticMutationConfig] = None):
        self.config = config or SemanticMutationConfig()
        self.semantics = InstructionSemantics()
        self._rng = random.Random()
    
    def set_seed(self, seed: int):
        self._rng.seed(seed)
    
    def mutate_gene(self, gene: GeneInstruction, 
                     position: int = 0,
                     context: Optional[Dict[str, Any]] = None) -> GeneInstruction:
        if not self.config.use_semantic_mutation:
            return self._random_mutation(gene)
        
        mutated = gene.clone()
        
        if self._rng.random() < 0.7:
            mutated = self._semantic_opcode_mutation(mutated, position, context)
        
        if self._rng.random() < 0.3:
            mutated = self._semantic_modifier_mutation(mutated)
        
        if self._rng.random() < 0.2:
            mutated = self._semantic_operand_mutation(mutated)
        
        return mutated
    
    def _semantic_opcode_mutation(self, gene: GeneInstruction,
                                    position: int,
                                    context: Optional[Dict[str, Any]]) -> GeneInstruction:
        original_opcode = gene.opcode
        
        if self.config.preserve_control_flow:
            roles = self.semantics.get_roles(original_opcode)
            if InstructionRole.CONTROL_FLOW in roles:
                if self._rng.random() < 0.8:
                    same_role = self.semantics.get_same_role_opcodes(original_opcode)
                    if same_role:
                        target_opcode = self._rng.choice(same_role)
                        gene.opcode = target_opcode
                        return gene
        
        if self.config.context_aware and context:
            valid_followers = self._get_context_valid_mutations(original_opcode, position, context)
            if valid_followers:
                target_opcode = self._rng.choice(valid_followers)
                gene.opcode = target_opcode
                return gene
        
        r = self._rng.random()
        if r < self.config.same_category_prob:
            same_category = self.semantics.get_same_category_opcodes(original_opcode)
            if same_category:
                target_opcode = self._rng.choice(same_category)
                gene.opcode = target_opcode
        elif r < self.config.same_category_prob + self.config.same_role_prob:
            same_role = self.semantics.get_same_role_opcodes(original_opcode)
            if same_role:
                target_opcode = self._rng.choice(same_role)
                gene.opcode = target_opcode
        elif r < self.config.same_category_prob + self.config.same_role_prob + self.config.equivalent_prob:
            equivalents = self.semantics.get_equivalent_opcodes(original_opcode)
            if equivalents:
                target_opcode = self._rng.choice(equivalents)
                gene.opcode = target_opcode
        else:
            all_opcodes = self.semantics.get_all_opcodes()
            target_opcode = self._rng.choice(all_opcodes)
            gene.opcode = target_opcode
        
        return gene
    
    def _get_context_valid_mutations(self, opcode: int, position: int,
                                       context: Dict[str, Any]) -> List[int]:
        instructions = context.get('instructions', [])
        if not instructions:
            return []
        
        valid_mutations = []
        
        if position > 0:
            prev_opcode = instructions[position - 1].opcode if position - 1 < len(instructions) else None
            if prev_opcode is not None:
                followers = self.semantics.get_contextually_valid_followers(prev_opcode)
                valid_mutations.extend(followers)
        
        if position < len(instructions) - 1:
            next_opcode = instructions[position + 1].opcode if position + 1 < len(instructions) else None
            if next_opcode is not None:
                for o in self.semantics.get_all_opcodes():
                    followers = self.semantics.get_contextually_valid_followers(o)
                    if next_opcode in followers:
                        valid_mutations.append(o)
        
        if valid_mutations:
            return list(set(valid_mutations))
        return []
    
    def _semantic_modifier_mutation(self, gene: GeneInstruction) -> GeneInstruction:
        if self.config.modifier_semantic_match:
            roles = self.semantics.get_roles(gene.opcode)
            
            relevant_modifiers = []
            if InstructionRole.SYNCHRONIZATION in roles:
                relevant_modifiers.extend([
                    (".ATOMIC", 0b010000),
                    (".VOLATILE", 0b000001),
                ])
            if InstructionRole.MEMORY in roles:
                relevant_modifiers.extend([
                    (".VOLATILE", 0b000001),
                    (".STRONG", 0b000010),
                    (".WEAK", 0b000100),
                ])
            if InstructionRole.THREAD in roles:
                relevant_modifiers.append((".ASYNC", 0b100000))
            
            if relevant_modifiers and self._rng.random() < 0.7:
                modifier_name, modifier_val = self._rng.choice(relevant_modifiers)
                gene.modifier = modifier_val
                return gene
        
        if gene.operands:
            bit = self._rng.randint(0, 5)
            gene.modifier ^= (1 << bit)
        
        return gene
    
    def _semantic_operand_mutation(self, gene: GeneInstruction) -> GeneInstruction:
        if not gene.operands:
            return gene
        
        roles = self.semantics.get_roles(gene.opcode)
        
        if InstructionRole.CONTROL_FLOW in roles:
            if len(gene.operands) >= 2:
                offset = self._rng.choice([-2, -1, 1, 2])
                idx = 1 if len(gene.operands) > 1 else 0
                if idx < len(gene.operands):
                    old_val = gene.operands[idx]
                    if isinstance(old_val, int):
                        gene.operands[idx] = max(0, old_val + offset)
        
        elif InstructionRole.MEMORY in roles:
            if len(gene.operands) >= 2:
                size_variations = [0.5, 0.75, 1.25, 1.5, 2.0]
                idx = 1
                if idx < len(gene.operands):
                    old_val = gene.operands[idx]
                    if isinstance(old_val, int) and old_val > 0:
                        factor = self._rng.choice(size_variations)
                        gene.operands[idx] = max(1, int(old_val * factor))
        
        else:
            idx = self._rng.randint(0, len(gene.operands) - 1)
            if isinstance(gene.operands[idx], int):
                gene.operands[idx] = self._rng.randint(0, 15)
        
        return gene
    
    def _random_mutation(self, gene: GeneInstruction) -> GeneInstruction:
        mutated = gene.clone()
        
        if self._rng.random() < 0.7:
            bit = self._rng.randint(0, 5)
            mutated.opcode ^= (1 << bit)
        
        if self._rng.random() < 0.3:
            bit = self._rng.randint(0, 5)
            mutated.modifier ^= (1 << bit)
        
        if self._rng.random() < 0.2 and mutated.operands:
            idx = self._rng.randint(0, len(mutated.operands) - 1)
            if isinstance(mutated.operands[idx], int):
                mutated.operands[idx] = self._rng.randint(0, 15)
        
        return mutated
    
    def evaluate_mutation_semantics(self, original: GeneInstruction,
                                      mutated: GeneInstruction) -> Dict[str, Any]:
        original_opcode = original.opcode
        mutated_opcode = mutated.opcode
        
        original_cat = self.semantics.get_category(original_opcode)
        mutated_cat = self.semantics.get_category(mutated_opcode)
        
        original_roles = self.semantics.get_roles(original_opcode)
        mutated_roles = self.semantics.get_roles(mutated_opcode)
        
        equivalents = self.semantics.get_equivalent_opcodes(original_opcode)
        
        return {
            "original_opcode": original_opcode,
            "mutated_opcode": mutated_opcode,
            "same_category": original_cat == mutated_cat,
            "original_category": original_cat,
            "mutated_category": mutated_cat,
            "role_overlap": list(original_roles & mutated_roles),
            "original_roles": [r.value for r in original_roles],
            "mutated_roles": [r.value for r in mutated_roles],
            "is_equivalent": mutated_opcode in equivalents,
            "semantically_valid": self.semantics.is_semantically_valid_mutation(
                original_opcode, mutated_opcode
            ),
        }


class InsertDeleteMutation:
    def __init__(self, semantics: InstructionSemantics):
        self.semantics = semantics
        self._rng = random.Random()
    
    def insert_instruction(self, genes: List[GeneInstruction], 
                            position: int) -> List[GeneInstruction]:
        if position < 0 or position > len(genes):
            position = len(genes)
        
        context_opcodes = []
        if position > 0:
            context_opcodes.append(genes[position - 1].opcode)
        if position < len(genes):
            context_opcodes.append(genes[position].opcode)
        
        candidates = []
        for opcode in context_opcodes:
            candidates.extend(self.semantics.get_same_category_opcodes(opcode))
            candidates.extend(self.semantics.get_same_role_opcodes(opcode))
        
        if not candidates:
            candidates = self.semantics.get_all_opcodes()
        
        new_opcode = self._rng.choice(candidates)
        new_gene = GeneInstruction(opcode=new_opcode)
        
        new_genes = list(genes)
        new_genes.insert(position, new_gene)
        return new_genes
    
    def delete_instruction(self, genes: List[GeneInstruction],
                            position: int) -> List[GeneInstruction]:
        if len(genes) <= 1:
            return genes
        
        if position < 0 or position >= len(genes):
            position = len(genes) - 1
        
        opcode = genes[position].opcode
        roles = self.semantics.get_roles(opcode)
        
        if InstructionRole.CONTROL_FLOW in roles:
            if self._rng.random() < 0.8:
                return genes
        
        if InstructionRole.SYNCHRONIZATION in roles:
            if self._rng.random() < 0.6:
                return genes
        
        new_genes = list(genes)
        new_genes.pop(position)
        return new_genes
    
    def reorder_instructions(self, genes: List[GeneInstruction],
                              from_pos: int, to_pos: int) -> List[GeneInstruction]:
        if len(genes) <= 1:
            return genes
        
        if from_pos < 0 or from_pos >= len(genes):
            return genes
        if to_pos < 0 or to_pos >= len(genes):
            return genes
        if from_pos == to_pos:
            return genes
        
        from_opcode = genes[from_pos].opcode
        from_roles = self.semantics.get_roles(from_opcode)
        
        if InstructionRole.CONTROL_FLOW in from_roles:
            return genes
        
        new_genes = list(genes)
        gene = new_genes.pop(from_pos)
        new_genes.insert(to_pos, gene)
        return new_genes
