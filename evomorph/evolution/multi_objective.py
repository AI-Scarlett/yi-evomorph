import random
import copy
import math
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set, Callable, Any
from evomorph.evolution.engine import GeneInstruction, Individual, EvolutionConfig


class ObjectiveType(Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


@dataclass
class Objective:
    name: str
    objective_type: ObjectiveType
    weight: float = 1.0
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    
    def normalize(self, value: float) -> float:
        if self.lower_bound is not None and self.upper_bound is not None:
            if self.upper_bound == self.lower_bound:
                return 0.0
            return (value - self.lower_bound) / (self.upper_bound - self.lower_bound)
        return value
    
    def compare(self, a: float, b: float) -> int:
        if self.objective_type == ObjectiveType.MINIMIZE:
            if a < b:
                return -1
            elif a > b:
                return 1
            return 0
        else:
            if a > b:
                return -1
            elif a < b:
                return 1
            return 0


@dataclass
class ParetoFront:
    individuals: List[Individual] = field(default_factory=list)
    objectives: List[Objective] = field(default_factory=list)
    
    def dominates(self, a: Individual, b: Individual) -> bool:
        a_dominated = False
        b_dominated = False
        
        for obj in self.objectives:
            a_val = self._get_objective_value(a, obj.name)
            b_val = self._get_objective_value(b, obj.name)
            
            cmp = obj.compare(a_val, b_val)
            if cmp < 0:
                a_dominated = True
            elif cmp > 0:
                b_dominated = True
        
        return a_dominated and not b_dominated
    
    def _get_objective_value(self, individual: Individual, obj_name: str) -> float:
        if individual.execution_metrics:
            if obj_name in individual.execution_metrics:
                return individual.execution_metrics[obj_name]
        
        if hasattr(individual, 'multi_objective_values'):
            vals = getattr(individual, 'multi_objective_values', {})
            if obj_name in vals:
                return vals[obj_name]
        
        return self._estimate_objective(individual, obj_name)
    
    def _estimate_objective(self, individual: Individual, obj_name: str) -> float:
        if obj_name == "min_latency":
            return len(individual.genes) * 10.0
        elif obj_name == "max_throughput":
            return 1.0 / (len(individual.genes) * 0.1)
        elif obj_name == "min_energy":
            return len(individual.genes) * 5.0
        elif obj_name == "min_size":
            return len(individual.genes) * 8.0
        
        return individual.fitness
    
    def compute_non_dominated_sort(self, population: List[Individual]) -> List[List[Individual]]:
        fronts: List[List[Individual]] = []
        domination_count: Dict[int, int] = {}
        dominated_set: Dict[int, Set[int]] = {}
        
        for i, ind in enumerate(population):
            domination_count[i] = 0
            dominated_set[i] = set()
        
        for i, a in enumerate(population):
            for j, b in enumerate(population):
                if i == j:
                    continue
                
                if self.dominates(a, b):
                    dominated_set[i].add(j)
                elif self.dominates(b, a):
                    domination_count[i] += 1
        
        front_0 = [i for i, count in domination_count.items() if count == 0]
        fronts.append([population[i] for i in front_0])
        
        current_front = front_0
        while current_front:
            next_front: List[int] = []
            
            for i in current_front:
                for j in dominated_set[i]:
                    domination_count[j] -= 1
                    if domination_count[j] == 0:
                        next_front.append(j)
            
            if next_front:
                fronts.append([population[i] for i in next_front])
            current_front = next_front
        
        return fronts
    
    def compute_crowding_distance(self, front: List[Individual]) -> Dict[int, float]:
        distances: Dict[int, float] = {i: 0.0 for i in range(len(front))}
        n = len(front)
        
        if n == 0:
            return distances
        if n == 1:
            return {0: float('inf')}
        
        for obj in self.objectives:
            values = [self._get_objective_value(ind, obj.name) for ind in front]
            sorted_indices = sorted(range(n), key=lambda i: values[i])
            
            distances[sorted_indices[0]] = float('inf')
            distances[sorted_indices[-1]] = float('inf')
            
            min_val = values[sorted_indices[0]]
            max_val = values[sorted_indices[-1]]
            
            if max_val == min_val:
                continue
            
            for i in range(1, n - 1):
                prev_val = values[sorted_indices[i - 1]]
                next_val = values[sorted_indices[i + 1]]
                distances[sorted_indices[i]] += (next_val - prev_val) / (max_val - min_val)
        
        return distances


@dataclass
class MultiObjectiveConfig(EvolutionConfig):
    objectives: List[Objective] = field(default_factory=lambda: [
        Objective("min_latency", ObjectiveType.MINIMIZE, 1.0),
        Objective("max_throughput", ObjectiveType.MAXIMIZE, 2.0),
        Objective("min_energy", ObjectiveType.MINIMIZE, 0.5),
        Objective("min_size", ObjectiveType.MINIMIZE, 0.3),
    ])
    use_nsga2: bool = True
    crowding_distance_weight: float = 1.0


class NSGAIIEngine:
    def __init__(self, config: Optional[MultiObjectiveConfig] = None):
        self.config = config or MultiObjectiveConfig()
        self.pareto_front = ParetoFront(objectives=self.config.objectives)
        self._rng = random.Random()
        self.generation = 0
        self.population: List[Individual] = []
        self.history: List[Dict] = []
    
    def set_seed(self, seed: int):
        self._rng.seed(seed)
    
    def initialize_population(self, genes: List[GeneInstruction], size: Optional[int] = None):
        pop_size = size or self.config.population_size
        self.population = []
        
        for _ in range(pop_size):
            individual = Individual(
                genes=[g.clone() for g in genes],
                origin="initial"
            )
            self._randomize_individual(individual)
            self.population.append(individual)
        
        self.generation = 0
    
    def _randomize_individual(self, individual: Individual):
        for gene in individual.genes:
            if self._rng.random() < 0.3:
                bit = self._rng.randint(0, 5)
                gene.flip_yao(bit)
    
    def evaluate_population(self, vm_evaluator: Optional[Callable] = None):
        for ind in self.population:
            if vm_evaluator:
                metrics = vm_evaluator(ind)
                if metrics:
                    ind.execution_metrics = metrics
            
            self._compute_multi_objective_values(ind)
    
    def _compute_multi_objective_values(self, individual: Individual):
        values = {}
        
        for obj in self.config.objectives:
            if individual.execution_metrics:
                if obj.name in individual.execution_metrics:
                    values[obj.name] = individual.execution_metrics[obj.name]
                else:
                    values[obj.name] = self.pareto_front._estimate_objective(individual, obj.name)
            else:
                values[obj.name] = self.pareto_front._estimate_objective(individual, obj.name)
        
        individual.multi_objective_values = values
        
        weighted_sum = 0.0
        for obj in self.config.objectives:
            val = values.get(obj.name, 0.0)
            normalized = obj.normalize(val)
            if obj.objective_type == ObjectiveType.MINIMIZE:
                normalized = 1.0 - normalized
            weighted_sum += normalized * obj.weight
        
        individual.fitness = weighted_sum
    
    def select(self, population: List[Individual]) -> Individual:
        if self.config.use_nsga2:
            return self._nsga2_selection(population)
        else:
            return self._tournament_selection(population)
    
    def _nsga2_selection(self, population: List[Individual]) -> Individual:
        fronts = self.pareto_front.compute_non_dominated_sort(population)
        
        if not fronts:
            return self._tournament_selection(population)
        
        front_idx = 0
        while front_idx < len(fronts) - 1 and len(fronts[front_idx]) < self.config.tournament_size:
            front_idx += 1
        
        selection_pool = fronts[front_idx]
        
        if len(selection_pool) == 1:
            return selection_pool[0].clone()
        
        crowding = self.pareto_front.compute_crowding_distance(selection_pool)
        
        candidates = self._rng.sample(list(range(len(selection_pool))), 
                                        min(self.config.tournament_size, len(selection_pool)))
        
        best = max(candidates, key=lambda i: crowding.get(i, 0.0))
        
        return selection_pool[best].clone()
    
    def _tournament_selection(self, population: List[Individual]) -> Individual:
        if len(population) < self.config.tournament_size:
            return population[0].clone()
        
        candidates = self._rng.sample(population, self.config.tournament_size)
        
        best = max(candidates, key=lambda ind: ind.fitness)
        
        return best.clone()
    
    def crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        min_len = min(len(parent1.genes), len(parent2.genes))
        
        if min_len < 2:
            return parent1.clone(), parent2.clone()
        
        point1 = self._rng.randint(0, min_len - 1)
        point2 = self._rng.randint(point1 + 1, min_len)
        
        child1_genes = []
        child2_genes = []
        
        for i in range(min(len(parent1.genes), len(parent2.genes))):
            if point1 <= i < point2:
                g1 = parent2.genes[i].clone()
                g2 = parent1.genes[i].clone()
            else:
                g1 = parent1.genes[i].clone()
                g2 = parent2.genes[i].clone()
            
            child1_genes.append(g1)
            child2_genes.append(g2)
        
        return (
            Individual(genes=child1_genes, origin="crossover"),
            Individual(genes=child2_genes, origin="crossover")
        )
    
    def mutate(self, individual: Individual) -> Individual:
        from evomorph.evolution.semantic_mutation import (
            SemanticMutationEngine, SemanticMutationConfig, InsertDeleteMutation, InstructionSemantics
        )
        
        semantic_config = SemanticMutationConfig()
        mutation_engine = SemanticMutationEngine(semantic_config)
        mutation_engine.set_seed(self._rng.randint(0, 1000000))
        
        mutated = individual.clone()
        mutated.origin = "mutated"
        
        for i, gene in enumerate(mutated.genes):
            if self._rng.random() < self.config.mut_rate:
                context = {'instructions': mutated.genes}
                mutated_gene = mutation_engine.mutate_gene(gene, position=i, context=context)
                mutated.genes[i] = mutated_gene
        
        if self._rng.random() < 0.1 and len(mutated.genes) > 1:
            semantics = InstructionSemantics()
            indel = InsertDeleteMutation(semantics)
            
            if self._rng.random() < 0.5:
                pos = self._rng.randint(0, len(mutated.genes))
                new_genes = indel.insert_instruction(mutated.genes, pos)
                mutated.genes = new_genes
            else:
                pos = self._rng.randint(0, len(mutated.genes) - 1)
                new_genes = indel.delete_instruction(mutated.genes, pos)
                if new_genes:
                    mutated.genes = new_genes
        
        return mutated
    
    def evolve_one_generation(self, vm_evaluator: Optional[Callable] = None) -> Dict:
        self.evaluate_population(vm_evaluator)
        
        fronts = self.pareto_front.compute_non_dominated_sort(self.population)
        
        if fronts:
            self.pareto_front.individuals = fronts[0]
        
        current_diversity = self._calculate_diversity()
        old_mut_rate = self.config.mut_rate
        new_mut_rate = self._update_mutation_rate()
        
        elites = []
        if fronts:
            elites = [ind.clone() for ind in fronts[0][:self.config.elite_count]]
        
        new_population = list(elites)
        
        while len(new_population) < self.config.population_size:
            parent1 = self.select(self.population)
            parent2 = self.select(self.population)
            
            if self._rng.random() < self.config.crossover_rate:
                child1, child2 = self.crossover(parent1, parent2)
            else:
                child1, child2 = parent1.clone(), parent2.clone()
            
            child1 = self.mutate(child1)
            child2 = self.mutate(child2)
            
            new_population.append(child1)
            if len(new_population) < self.config.population_size:
                new_population.append(child2)
        
        self.population = new_population[:self.config.population_size]
        self.generation += 1
        
        for ind in self.population:
            ind.age += 1
        
        new_diversity = self._calculate_diversity()
        
        stats = {
            "generation": self.generation,
            "pareto_front_size": len(self.pareto_front.individuals),
            "fronts_count": len(fronts) if fronts else 0,
            "avg_fitness": sum(ind.fitness for ind in self.population) / max(len(self.population), 1),
            "diversity": new_diversity,
            "diversity_before_selection": current_diversity,
            "population_size": len(self.population),
            "mutation_rate": new_mut_rate,
            "mutation_rate_change": new_mut_rate - old_mut_rate,
        }
        
        self.history.append(stats)
        return stats
    
    def evolve(self, max_generations: Optional[int] = None, 
               vm_evaluator: Optional[Callable] = None,
               callback: Optional[Callable] = None) -> ParetoFront:
        gens = max_generations or self.config.max_generations
        
        for _ in range(gens):
            stats = self.evolve_one_generation(vm_evaluator)
            
            if callback:
                callback(stats)
            
            if self._converged():
                break
        
        return self.pareto_front
    
    def _calculate_diversity(self) -> float:
        if len(self.population) < 2:
            return 0.0
        
        opcode_sequences = []
        for ind in self.population:
            seq = tuple(g.opcode for g in ind.genes)
            opcode_sequences.append(seq)
        
        unique_sequences = set(opcode_sequences)
        return len(unique_sequences) / len(self.population)
    
    def _update_mutation_rate(self) -> float:
        if not self.config.use_adaptive_mutation:
            return self.config.mut_rate
        
        diversity = self._calculate_diversity()
        
        if diversity < self.config.diversity_threshold_low:
            self.config.mut_rate = min(
                self.config.mut_rate * 1.2,
                self.config.max_mut_rate
            )
        elif diversity > self.config.diversity_threshold_high:
            self.config.mut_rate = max(
                self.config.mut_rate * 0.8,
                self.config.min_mut_rate
            )
        
        return self.config.mut_rate
    
    def _converged(self, threshold=0.001, window=10) -> bool:
        if len(self.history) < window:
            return False
        
        recent = self.history[-window:]
        fitnesses = [h["avg_fitness"] for h in recent]
        variance = sum((f - sum(fitnesses) / len(fitnesses)) ** 2 for f in fitnesses) / len(fitnesses)
        
        return variance < threshold
    
    def get_representative_solutions(self, count: int = 5) -> List[Individual]:
        if not self.pareto_front.individuals:
            return []
        
        if len(self.pareto_front.individuals) <= count:
            return [ind.clone() for ind in self.pareto_front.individuals]
        
        crowding = self.pareto_front.compute_crowding_distance(self.pareto_front.individuals)
        
        sorted_indices = sorted(
            range(len(self.pareto_front.individuals)),
            key=lambda i: crowding.get(i, 0.0),
            reverse=True
        )
        
        return [self.pareto_front.individuals[i].clone() for i in sorted_indices[:count]]
    
    def select_by_preference(self, preferences: Dict[str, float]) -> Optional[Individual]:
        if not self.pareto_front.individuals:
            return None
        
        best_score = -float('inf')
        best_ind = None
        
        for ind in self.pareto_front.individuals:
            score = 0.0
            for obj_name, weight in preferences.items():
                val = self.pareto_front._get_objective_value(ind, obj_name)
                
                for obj in self.config.objectives:
                    if obj.name == obj_name:
                        normalized = obj.normalize(val)
                        if obj.objective_type == ObjectiveType.MINIMIZE:
                            normalized = 1.0 - normalized
                        score += normalized * weight
                        break
            
            if score > best_score:
                best_score = score
                best_ind = ind
        
        return best_ind.clone() if best_ind else None
