import random
import copy
import math
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any

try:
    from ..vm.virtual_machine import IChingVM, VMState
    HAS_VM = True
except ImportError:
    HAS_VM = False


class SelectionMethod(Enum):
    ROULETTE = "roulette"
    TOURNAMENT = "tournament"
    RANK = "rank"


class CrossoverMethod(Enum):
    SINGLE_POINT = "single_point"
    TWO_POINT = "two_point"
    UNIFORM = "uniform"


@dataclass
class GeneInstruction:
    opcode: int
    modifier: int = 0
    operands: List[int] = field(default_factory=list)

    def to_binary(self):
        bits = format(self.opcode, "06b")
        return bits

    def flip_yao(self, position):
        if 0 <= position <= 5:
            self.opcode ^= (1 << position)

    def mutate_modifier(self):
        bit = random.randint(0, 5)
        self.modifier ^= (1 << bit)

    def clone(self):
        return GeneInstruction(
            opcode=self.opcode,
            modifier=self.modifier,
            operands=list(self.operands),
        )


@dataclass
class Individual:
    genes: List[GeneInstruction] = field(default_factory=list)
    fitness: float = 0.0
    age: int = 0
    origin: str = "initial"
    platform_scores: Dict[str, float] = field(default_factory=dict)
    execution_metrics: Dict[str, float] = field(default_factory=dict)
    compiled_instructions: List = field(default_factory=list)

    def clone(self):
        return Individual(
            genes=[g.clone() for g in self.genes],
            fitness=self.fitness,
            age=self.age,
            origin=self.origin,
            platform_scores=dict(self.platform_scores),
            execution_metrics=dict(self.execution_metrics) if self.execution_metrics else {},
            compiled_instructions=list(self.compiled_instructions) if self.compiled_instructions else [],
        )


@dataclass
class EvolutionConfig:
    population_size: int = 64
    max_generations: int = 100
    mut_rate: float = 0.02
    min_mut_rate: float = 0.001
    max_mut_rate: float = 0.15
    crossover_rate: float = 0.7
    elite_count: int = 2
    selection_method: SelectionMethod = SelectionMethod.TOURNAMENT
    crossover_method: CrossoverMethod = CrossoverMethod.SINGLE_POINT
    tournament_size: int = 5
    use_adaptive_mutation: bool = True
    diversity_threshold_high: float = 0.7
    diversity_threshold_low: float = 0.3
    use_execution_based_fitness: bool = False
    fitness_weights: Dict[str, float] = field(default_factory=lambda: {
        "min_latency": 1.0,
        "max_throughput": 2.0,
        "min_energy": 0.5,
        "min_size": 0.3,
    })
    env_targets: List[str] = field(default_factory=list)
    cross_pool: str = "default"
    hard_constraints: List[Callable] = field(default_factory=list)


class EvolutionEngine:
    def __init__(self, config: Optional[EvolutionConfig] = None,
                 fitness_evaluator: Optional[Callable] = None,
                 platform_simulator: Optional[Any] = None,
                 use_evomorph: bool = False):
        self.config = config or EvolutionConfig()
        self.fitness_evaluator = fitness_evaluator
        self.platform_simulator = platform_simulator
        self.population: List[Individual] = []
        self.generation = 0
        self.history: List[Dict] = []
        self.best_ever: Optional[Individual] = None
        self.cross_pool: Dict[str, List[Individual]] = {}
        self._rng = random.Random()
        
        self._use_evomorph = use_evomorph
        self._backend = None
        
        if use_evomorph:
            try:
                from evomorph.bootstrap import EvomorphBackend
                self._backend = EvomorphBackend()
            except ImportError:
                self._use_evomorph = False

    def set_mode(self, use_evomorph: bool):
        """设置使用 Evomorph 实现还是 Python 实现"""
        self._use_evomorph = use_evomorph
        if use_evomorph and self._backend is None:
            try:
                from evomorph.bootstrap import EvomorphBackend
                self._backend = EvomorphBackend()
            except ImportError:
                self._use_evomorph = False

    def initialize_population(self, seed_genes: List[GeneInstruction]) -> List[Individual]:
        self.population = []
        seed = Individual(genes=[g.clone() for g in seed_genes], origin="seed")
        self.population.append(seed)
        for i in range(self.config.population_size - 1):
            variant = self._create_variant(seed_genes, self.config.mut_rate * 5)
            variant.origin = f"init_variant_{i}"
            self.population.append(variant)
        self.generation = 0
        self.history = []
        return self.population

    def _create_variant(self, base_genes: List[GeneInstruction], mut_rate: float) -> Individual:
        genes = []
        for g in base_genes:
            new_g = g.clone()
            if self._rng.random() < mut_rate:
                bit = self._rng.randint(0, 5)
                new_g.flip_yao(bit)
            if self._rng.random() < mut_rate * 0.5:
                new_g.mutate_modifier()
            if self._rng.random() < mut_rate * 0.3:
                if new_g.operands:
                    idx = self._rng.randint(0, len(new_g.operands) - 1)
                    new_g.operands[idx] = self._rng.randint(0, 15)
            genes.append(new_g)
        return Individual(genes=genes, origin="variant")

    def evaluate_fitness(self, individual: Individual, platform: Optional[str] = None) -> float:
        if self.fitness_evaluator:
            score = self.fitness_evaluator(individual, platform)
            individual.fitness = score
            if platform:
                individual.platform_scores[platform] = score
            return score
        score = self._default_fitness(individual, platform)
        individual.fitness = score
        if platform:
            individual.platform_scores[platform] = score
        return score

    def _evaluate_on_vm(self, individual: Individual) -> Dict[str, float]:
        if not HAS_VM or not individual.compiled_instructions:
            return {}
        
        try:
            vm = IChingVM()
            
            for i, instr in enumerate(individual.compiled_instructions[:256]):
                if isinstance(instr, dict):
                    opcode = instr.get("opcode", 0)
                    operands = instr.get("operands", [])
                    vm.memory[vm.registers.get("PC", 0) + i] = opcode
                elif isinstance(instr, tuple):
                    opcode = instr[0]
                    vm.memory[vm.registers.get("PC", 0) + i] = opcode
                elif isinstance(instr, int):
                    vm.memory[vm.registers.get("PC", 0) + i] = instr
            
            max_cycles = 1000
            cycles = 0
            while cycles < max_cycles and vm.state == VMState.RUNNING:
                try:
                    vm.step()
                    cycles += 1
                except Exception:
                    break
            
            metrics = {
                "executed_cycles": float(cycles),
                "instructions_executed": float(vm.registers.get("PC", 0)),
                "halted": 1.0 if vm.state == VMState.HALTED else 0.0,
                "error": 1.0 if vm.state == VMState.ERROR else 0.0,
            }
            
            if hasattr(vm, 'energy_used'):
                metrics["energy_used"] = float(vm.energy_used)
            else:
                metrics["energy_used"] = cycles * 0.1
            
            if hasattr(vm, 'memory_usage'):
                metrics["memory_usage"] = float(vm.memory_usage)
            else:
                metrics["memory_usage"] = float(len([x for x in vm.memory if x != 0]))
            
            return metrics
            
        except Exception:
            return {"error": 1.0}
    
    def _default_fitness(self, individual: Individual, platform: Optional[str] = None) -> float:
        score = 0.0
        weights = self.config.fitness_weights
        n_genes = len(individual.genes)
        if n_genes == 0:
            return -1000.0
        
        use_execution_based = self.config.use_execution_based_fitness if hasattr(self.config, 'use_execution_based_fitness') else False
        
        if use_execution_based and HAS_VM:
            metrics = self._evaluate_on_vm(individual)
            
            if metrics.get("error", 0.0) > 0.5:
                return -2000.0
            
            latency_score = -metrics.get("executed_cycles", n_genes * 2.0) * 1.0
            throughput_score = max(0, 100.0 - metrics.get("executed_cycles", n_genes * 2.0) * 0.5)
            energy_score = -metrics.get("energy_used", n_genes * 0.1) * 0.5
            size_score = -n_genes * 0.1
            halt_bonus = 100.0 if metrics.get("halted", 0.0) > 0.5 else -50.0
            
            score = (weights.get("min_latency", 1.0) * latency_score +
                     weights.get("max_throughput", 2.0) * throughput_score +
                     weights.get("min_energy", 0.5) * energy_score +
                     weights.get("min_size", 0.3) * size_score +
                     halt_bonus)
            
            individual.execution_metrics = metrics
            
        else:
            latency_score = -n_genes * 1.0
            throughput_score = max(0, 10.0 - n_genes * 0.5)
            energy_score = -sum(g.opcode for g in individual.genes) * 0.01
            size_score = -n_genes * 0.1
            score = (weights.get("min_latency", 1.0) * latency_score +
                     weights.get("max_throughput", 2.0) * throughput_score +
                     weights.get("min_energy", 0.5) * energy_score +
                     weights.get("min_size", 0.3) * size_score)
        
        if platform and self.platform_simulator:
            platform_bonus = self.platform_simulator.evaluate(individual, platform)
            score += platform_bonus
        
        return score

    def select(self, population: List[Individual]) -> Individual:
        if self.config.selection_method == SelectionMethod.ROULETTE:
            return self._roulette_select(population)
        elif self.config.selection_method == SelectionMethod.TOURNAMENT:
            return self._tournament_select(population)
        elif self.config.selection_method == SelectionMethod.RANK:
            return self._rank_select(population)
        return self._tournament_select(population)

    def _roulette_select(self, population: List[Individual]) -> Individual:
        total = sum(max(ind.fitness, 0.001) for ind in population)
        if total == 0:
            return self._rng.choice(population)
        r = self._rng.random() * total
        cumulative = 0.0
        for ind in population:
            cumulative += max(ind.fitness, 0.001)
            if cumulative >= r:
                return ind
        return population[-1]

    def _tournament_select(self, population: List[Individual]) -> Individual:
        contestants = self._rng.sample(population, min(self.config.tournament_size, len(population)))
        return max(contestants, key=lambda x: x.fitness)

    def _rank_select(self, population: List[Individual]) -> Individual:
        sorted_pop = sorted(population, key=lambda x: x.fitness, reverse=True)
        ranks = list(range(len(sorted_pop), 0, -1))
        total_rank = sum(ranks)
        r = self._rng.random() * total_rank
        cumulative = 0
        for i, rank in enumerate(ranks):
            cumulative += rank
            if cumulative >= r:
                return sorted_pop[i]
        return sorted_pop[0]

    def crossover(self, parent1: Individual, parent2: Individual) -> tuple:
        if self._rng.random() > self.config.crossover_rate:
            return parent1.clone(), parent2.clone()
        if self.config.crossover_method == CrossoverMethod.SINGLE_POINT:
            return self._single_point_crossover(parent1, parent2)
        elif self.config.crossover_method == CrossoverMethod.TWO_POINT:
            return self._two_point_crossover(parent1, parent2)
        elif self.config.crossover_method == CrossoverMethod.UNIFORM:
            return self._uniform_crossover(parent1, parent2)
        return self._single_point_crossover(parent1, parent2)

    def _single_point_crossover(self, p1: Individual, p2: Individual) -> tuple:
        len1, len2 = len(p1.genes), len(p2.genes)
        min_len = min(len1, len2)
        if min_len <= 1:
            return p1.clone(), p2.clone()
        point = self._rng.randint(1, min_len - 1)
        child1_genes = [g.clone() for g in p1.genes[:point]] + [g.clone() for g in p2.genes[point:]]
        child2_genes = [g.clone() for g in p2.genes[:point]] + [g.clone() for g in p1.genes[point:]]
        c1 = Individual(genes=child1_genes, origin="crossover")
        c2 = Individual(genes=child2_genes, origin="crossover")
        return c1, c2

    def _two_point_crossover(self, p1: Individual, p2: Individual) -> tuple:
        min_len = min(len(p1.genes), len(p2.genes))
        if min_len <= 2:
            return self._single_point_crossover(p1, p2)
        pts = sorted(self._rng.sample(range(1, min_len), 2))
        child1_genes = ([g.clone() for g in p1.genes[:pts[0]]] +
                        [g.clone() for g in p2.genes[pts[0]:pts[1]]] +
                        [g.clone() for g in p1.genes[pts[1]:]])
        child2_genes = ([g.clone() for g in p2.genes[:pts[0]]] +
                        [g.clone() for g in p1.genes[pts[0]:pts[1]]] +
                        [g.clone() for g in p2.genes[pts[1]:]])
        return Individual(genes=child1_genes, origin="crossover"), Individual(genes=child2_genes, origin="crossover")

    def _uniform_crossover(self, p1: Individual, p2: Individual) -> tuple:
        max_len = max(len(p1.genes), len(p2.genes))
        child1_genes = []
        child2_genes = []
        for i in range(max_len):
            g1 = p1.genes[i].clone() if i < len(p1.genes) else p2.genes[i].clone()
            g2 = p2.genes[i].clone() if i < len(p2.genes) else p1.genes[i].clone()
            if self._rng.random() < 0.5:
                child1_genes.append(g1)
                child2_genes.append(g2)
            else:
                child1_genes.append(g2)
                child2_genes.append(g1)
        return Individual(genes=child1_genes, origin="crossover"), Individual(genes=child2_genes, origin="crossover")

    def mutate(self, individual: Individual) -> Individual:
        mutated = individual.clone()
        mutated.origin = "mutated"
        for gene in mutated.genes:
            if self._rng.random() < self.config.mut_rate:
                bit = self._rng.randint(0, 5)
                gene.flip_yao(bit)
            if self._rng.random() < self.config.mut_rate * 0.5:
                gene.mutate_modifier()
            if self._rng.random() < self.config.mut_rate * 0.3:
                if gene.operands:
                    idx = self._rng.randint(0, len(gene.operands) - 1)
                    gene.operands[idx] = self._rng.randint(0, 15)
        return mutated

    def evolve_one_generation(self) -> Dict:
        for ind in self.population:
            for platform in self.config.env_targets:
                self.evaluate_fitness(ind, platform)
            if not self.config.env_targets:
                self.evaluate_fitness(ind)
        self.population.sort(key=lambda x: x.fitness, reverse=True)
        if self.best_ever is None or self.population[0].fitness > self.best_ever.fitness:
            self.best_ever = self.population[0].clone()
        
        current_diversity = self._calculate_diversity()
        old_mut_rate = self.config.mut_rate
        new_mut_rate = self._update_mutation_rate()
        
        elites = [ind.clone() for ind in self.population[:self.config.elite_count]]
        new_population = list(elites)
        while len(new_population) < self.config.population_size:
            parent1 = self.select(self.population)
            parent2 = self.select(self.population)
            child1, child2 = self.crossover(parent1, parent2)
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
            "best_fitness": self.population[0].fitness if self.population else 0,
            "avg_fitness": sum(ind.fitness for ind in self.population) / max(len(self.population), 1),
            "worst_fitness": self.population[-1].fitness if self.population else 0,
            "diversity": new_diversity,
            "diversity_before_selection": current_diversity,
            "population_size": len(self.population),
            "mutation_rate": new_mut_rate,
            "mutation_rate_change": new_mut_rate - old_mut_rate,
        }
        
        best_individual = self.population[0] if self.population else None
        if best_individual and best_individual.execution_metrics:
            stats["best_execution_metrics"] = dict(best_individual.execution_metrics)
        
        self.history.append(stats)
        return stats

    def evolve(self, max_generations: Optional[int] = None, callback: Optional[Callable] = None) -> Individual:
        if self._use_evomorph and self._backend and self._backend.is_evomorph_available("evolution"):
            return self._evolve_using_evomorph(max_generations, callback)
        
        gens = max_generations or self.config.max_generations
        for _ in range(gens):
            stats = self.evolve_one_generation()
            if callback:
                callback(stats)
            if self._converged():
                break
        return self.best_ever if self.best_ever else (self.population[0] if self.population else None)
    
    def _evolve_using_evomorph(self, max_generations: Optional[int], callback: Optional[Callable]) -> Individual:
        """使用 Evomorph 实现进行进化"""
        seed_genes_list = [
            {"opcode": g.opcode, "modifier": g.modifier, "operands": list(g.operands)}
            for g in self.population[0].genes
        ] if self.population else []
        
        config = {
            "population_size": self.config.population_size,
            "max_generations": max_generations or self.config.max_generations,
            "mut_rate": self.config.mut_rate,
            "env_targets": list(self.config.env_targets),
        }
        
        result = self._backend.evolve_population(seed_genes_list, config)
        
        if "error" in result:
            return self.best_ever if self.best_ever else (self.population[0] if self.population else None)
        
        if "best_genes" in result:
            best_genes = [
                GeneInstruction(
                    opcode=g.get("opcode", 0),
                    modifier=g.get("modifier", 0),
                    operands=[],
                )
                for g in result["best_genes"]
            ]
            best_individual = Individual(
                genes=best_genes,
                fitness=result.get("best_fitness", 0.0),
                origin="evomorph_evolved",
            )
            
            if self.best_ever is None or best_individual.fitness > self.best_ever.fitness:
                self.best_ever = best_individual
            
            return best_individual
        
        return self.best_ever if self.best_ever else (self.population[0] if self.population else None)

    def _converged(self, threshold=0.001, window=10) -> bool:
        if len(self.history) < window:
            return False
        recent = self.history[-window:]
        fitnesses = [h["best_fitness"] for h in recent]
        variance = sum((f - sum(fitnesses) / len(fitnesses)) ** 2 for f in fitnesses) / len(fitnesses)
        return variance < threshold

    def _calculate_diversity(self) -> float:
        if len(self.population) < 2:
            return 0.0
        
        opcode_sequences = []
        for ind in self.population:
            seq = tuple(g.opcode for g in ind.genes)
            opcode_sequences.append(seq)
        
        unique_sequences = len(set(opcode_sequences))
        sequence_diversity = unique_sequences / len(self.population)
        
        opcode_counts = {}
        total_opcodes = 0
        for ind in self.population:
            for g in ind.genes:
                opcode_counts[g.opcode] = opcode_counts.get(g.opcode, 0) + 1
                total_opcodes += 1
        
        if total_opcodes > 0:
            unique_opcodes = len(opcode_counts)
            opcode_diversity = unique_opcodes / 64.0
        else:
            opcode_diversity = 0.0
        
        fitness_values = [ind.fitness for ind in self.population]
        if len(fitness_values) > 1:
            avg_fitness = sum(fitness_values) / len(fitness_values)
            variance = sum((f - avg_fitness) ** 2 for f in fitness_values) / len(fitness_values)
            fitness_range = max(fitness_values) - min(fitness_values)
            if fitness_range > 0:
                fitness_diversity = min(1.0, variance / (fitness_range * fitness_range / 4 + 0.001))
            else:
                fitness_diversity = 0.0
        else:
            fitness_diversity = 0.0
        
        combined_diversity = (
            0.4 * sequence_diversity + 
            0.3 * opcode_diversity + 
            0.3 * fitness_diversity
        )
        
        return combined_diversity
    
    def _update_mutation_rate(self) -> float:
        if not self.config.use_adaptive_mutation:
            return self.config.mut_rate
        
        diversity = self._calculate_diversity()
        
        current_rate = self.config.mut_rate
        min_rate = self.config.min_mut_rate
        max_rate = self.config.max_mut_rate
        
        low_threshold = self.config.diversity_threshold_low
        high_threshold = self.config.diversity_threshold_high
        
        if diversity < low_threshold:
            factor = 1.0 + (low_threshold - diversity) * 2.0
            new_rate = min(max_rate, current_rate * factor)
        elif diversity > high_threshold:
            factor = 0.5 + (diversity - high_threshold)
            new_rate = max(min_rate, current_rate * factor)
        else:
            target_rate = (min_rate + max_rate) / 2
            new_rate = current_rate + (target_rate - current_rate) * 0.1
        
        new_rate = max(min_rate, min(max_rate, new_rate))
        
        if abs(new_rate - current_rate) > 0.0001:
            self.config.mut_rate = new_rate
        
        return new_rate

    def register_cross_pool(self, name: str, individuals: List[Individual]):
        self.cross_pool[name] = individuals

    def cross_pool_crossover(self, pool_name: str, individual: Individual) -> Individual:
        if pool_name not in self.cross_pool or not self.cross_pool[pool_name]:
            return individual
        pool_member = self._rng.choice(self.cross_pool[pool_name])
        child, _ = self.crossover(individual, pool_member)
        return child

    def get_evolution_history(self) -> List[Dict]:
        return list(self.history)

    def get_best_individual(self) -> Optional[Individual]:
        return self.best_ever

    def get_population_stats(self) -> Dict:
        if not self.population:
            return {}
        fitnesses = [ind.fitness for ind in self.population]
        return {
            "generation": self.generation,
            "population_size": len(self.population),
            "best_fitness": max(fitnesses),
            "avg_fitness": sum(fitnesses) / len(fitnesses),
            "worst_fitness": min(fitnesses),
            "fitness_std": (sum((f - sum(fitnesses) / len(fitnesses)) ** 2 for f in fitnesses) / len(fitnesses)) ** 0.5,
            "best_ever_fitness": self.best_ever.fitness if self.best_ever else None,
        }

    def export_population(self) -> List[Dict]:
        result = []
        for ind in self.population:
            result.append({
                "fitness": ind.fitness,
                "age": ind.age,
                "origin": ind.origin,
                "platform_scores": dict(ind.platform_scores),
                "genes": [
                    {
                        "opcode": g.opcode,
                        "binary": format(g.opcode, "06b"),
                        "modifier": g.modifier,
                        "operands": list(g.operands),
                    }
                    for g in ind.genes
                ],
            })
        return result

    def get_backend_status(self):
        """获取后端状态"""
        if self._backend:
            return {
                "use_evomorph": self._use_evomorph,
                "backend_available": self._backend.is_evomorph_available("evolution"),
                "backend_status": self._backend.get_status(),
            }
        return {
            "use_evomorph": self._use_evomorph,
            "backend_available": False,
            "message": "使用 Python 实现",
        }
