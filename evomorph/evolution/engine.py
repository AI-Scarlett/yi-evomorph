import random
import copy
import math
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any


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

    def clone(self):
        return Individual(
            genes=[g.clone() for g in self.genes],
            fitness=self.fitness,
            age=self.age,
            origin=self.origin,
            platform_scores=dict(self.platform_scores),
        )


@dataclass
class EvolutionConfig:
    population_size: int = 64
    max_generations: int = 100
    mut_rate: float = 0.02
    crossover_rate: float = 0.7
    elite_count: int = 2
    selection_method: SelectionMethod = SelectionMethod.TOURNAMENT
    crossover_method: CrossoverMethod = CrossoverMethod.SINGLE_POINT
    tournament_size: int = 5
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
                 platform_simulator: Optional[Any] = None):
        self.config = config or EvolutionConfig()
        self.fitness_evaluator = fitness_evaluator
        self.platform_simulator = platform_simulator
        self.population: List[Individual] = []
        self.generation = 0
        self.history: List[Dict] = []
        self.best_ever: Optional[Individual] = None
        self.cross_pool: Dict[str, List[Individual]] = {}
        self._rng = random.Random()

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

    def _default_fitness(self, individual: Individual, platform: Optional[str] = None) -> float:
        score = 0.0
        weights = self.config.fitness_weights
        n_genes = len(individual.genes)
        if n_genes == 0:
            return -1000.0
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
        stats = {
            "generation": self.generation,
            "best_fitness": self.population[0].fitness if self.population else 0,
            "avg_fitness": sum(ind.fitness for ind in self.population) / max(len(self.population), 1),
            "worst_fitness": self.population[-1].fitness if self.population else 0,
            "diversity": self._calculate_diversity(),
            "population_size": len(self.population),
        }
        self.history.append(stats)
        return stats

    def evolve(self, max_generations: Optional[int] = None, callback: Optional[Callable] = None) -> Individual:
        gens = max_generations or self.config.max_generations
        for _ in range(gens):
            stats = self.evolve_one_generation()
            if callback:
                callback(stats)
            if self._converged():
                break
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
        opcodes = [tuple(g.opcode for g in ind.genes) for ind in self.population]
        unique = len(set(opcodes))
        return unique / len(self.population)

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
