import struct
import os
import json
from typing import Dict, List, Optional, Any
from evomorph.vm.virtual_machine import IChingVM, VMState
from evomorph.hexagrams import HexagramInstructionSet
from evomorph.compiler import EvocCompiler
from evomorph.evolution.engine import (
    EvolutionEngine, EvolutionConfig, GeneInstruction, Individual,
)


class EvoRuntime:
    def __init__(self):
        self.vm = IChingVM()
        self.isa = HexagramInstructionSet()
        self.compiler = EvocCompiler()
        self.loaded_loci: Dict[str, dict] = {}
        self.linked_programs: Dict[str, bytearray] = {}
        self.env_bindings: Dict[str, Any] = {}
        self.native_handlers: Dict[str, callable] = {}
        self._setup_native_handlers()

    def _setup_native_handlers(self):
        self.native_handlers = {
            "print": lambda val: print(f"[evort] {val}"),
            "stdout": lambda val: print(val, end=""),
            "assert": self._native_assert,
            "evolve_locus": self._native_evolve_locus,
            "compile_source": self._native_compile_source,
            "load_evo": self._native_load_evo,
            "measure_fitness": self._native_measure_fitness,
            "mutate_gene": self._native_mutate_gene,
            "crossover_genes": self._native_crossover_genes,
        }

    def _native_assert(self, expected, actual):
        if expected != actual:
            raise RuntimeError(f"Assertion failed: expected {expected}, got {actual}")

    def _native_evolve_locus(self, locus_name, generations=10):
        if locus_name not in self.loaded_loci:
            return None
        locus_data = self.loaded_loci[locus_name]
        seed_genes = []
        for instr in locus_data.get("instructions", []):
            gene = GeneInstruction(
                opcode=instr.get("opcode", 0),
                modifier=instr.get("modifier", 0),
            )
            seed_genes.append(gene)
        config = EvolutionConfig(
            population_size=32,
            max_generations=generations,
            mut_rate=locus_data.get("mut_rate", 0.02),
            env_targets=locus_data.get("env_targets", ["linux-6.x"]),
        )
        engine = EvolutionEngine(config=config)
        engine.initialize_population(seed_genes)
        best = engine.evolve()
        if best:
            return {
                "fitness": best.fitness,
                "genes": [{"opcode": g.opcode, "modifier": g.modifier} for g in best.genes],
            }
        return None

    def _native_compile_source(self, source_text):
        try:
            result = self.compiler.compile(source_text, output_format="dict")
            return result
        except Exception as e:
            return {"error": str(e)}

    def _native_load_evo(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            result = self.compiler.compile(source, output_format="dict")
            for locus in result.get("loci", []):
                self.loaded_loci[locus["name"]] = locus
            return result
        except Exception as e:
            return {"error": str(e)}

    def _native_measure_fitness(self, individual_data, platform="linux-6.x"):
        from evomorph.simulator.niche import PlatformSimNiche
        sim = PlatformSimNiche()
        genes = []
        for g in individual_data.get("genes", []):
            genes.append(GeneInstruction(opcode=g.get("opcode", 0), modifier=g.get("modifier", 0)))
        ind = Individual(genes=genes)
        return sim.evaluate(ind, platform)

    def _native_mutate_gene(self, opcode, bit_position):
        return self.isa.mutate_opcode(opcode, bit_position)

    def _native_crossover_genes(self, opcode1, opcode2, point):
        c1, c2 = self.isa.crossover_opcodes(opcode1, opcode2, point)
        return c1, c2

    def bind_env(self, env_name: str, value):
        self.env_bindings[env_name] = value

    def bind_native(self, name: str, handler: callable):
        self.native_handlers[name] = handler

    def load_evo_file(self, filepath: str) -> dict:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        result = self.compiler.compile(source, output_format="dict")
        for locus in result.get("loci", []):
            self.loaded_loci[locus["name"]] = locus
        for meta in result.get("meta_loci", []):
            self.loaded_loci[f"meta:{meta['name']}"] = meta
        return result

    def load_evo_source(self, source: str) -> dict:
        result = self.compiler.compile(source, output_format="dict")
        for locus in result.get("loci", []):
            self.loaded_loci[locus["name"]] = locus
        for meta in result.get("meta_loci", []):
            self.loaded_loci[f"meta:{meta['name']}"] = meta
        return result

    def get_locus(self, name: str) -> Optional[dict]:
        return self.loaded_loci.get(name)

    def compile_locus_to_vm_program(self, locus_name: str) -> List[dict]:
        locus = self.loaded_loci.get(locus_name)
        if not locus:
            return []
        program = []
        for instr in locus.get("instructions", []):
            program.append({
                "opcode": instr.get("opcode", 0),
                "modifier": instr.get("modifier", 0),
                "operands": [op.get("value", 0) if isinstance(op, dict) else op
                             for op in instr.get("operands", [])],
            })
        return program

    def execute_locus(self, locus_name: str, max_cycles: int = 10000) -> dict:
        program = self.compile_locus_to_vm_program(locus_name)
        if not program:
            return {"error": f"Locus '{locus_name}' not found or empty"}
        self.vm.reset()
        self._bind_env_to_vm()
        self.vm.load_program(program)
        state = self.vm.run(max_cycles=max_cycles)
        return {
            "locus": locus_name,
            "state": state.name,
            "cycle_count": self.vm.cycle_count,
            "energy_cost": self.vm.energy_cost,
            "registers": {f"R{i}": self.vm.registers[i] for i in range(16)},
        }

    def _bind_env_to_vm(self):
        for env_name, value in self.env_bindings.items():
            port = hash(env_name) & 0xFFFF
            if callable(value):
                self.vm.register_io_handler(port, value)
            else:
                self.vm.register_io_handler(port, lambda v=value: v)

    def evolve_locus(self, locus_name: str, generations: int = 20,
                     population_size: int = 32) -> Optional[dict]:
        locus = self.loaded_loci.get(locus_name)
        if not locus:
            return None
        seed_genes = []
        for instr in locus.get("instructions", []):
            gene = GeneInstruction(
                opcode=instr.get("opcode", 0),
                modifier=instr.get("modifier", 0),
            )
            seed_genes.append(gene)
        config = EvolutionConfig(
            population_size=population_size,
            max_generations=generations,
            mut_rate=locus.get("mut_rate", 0.02),
            env_targets=locus.get("env_targets", ["linux-6.x"]),
        )
        engine = EvolutionEngine(config=config)
        engine.initialize_population(seed_genes)
        best = engine.evolve()
        if best:
            evolved_locus = dict(locus)
            evolved_locus["instructions"] = [
                {"opcode": g.opcode, "modifier": g.modifier, "operands": list(g.operands),
                 "mnemonic": self.isa.get_by_opcode(g.opcode)["mnemonic"] if self.isa.get_by_opcode(g.opcode) else "???",
                 "symbol": self.isa.get_by_opcode(g.opcode)["symbol"] if self.isa.get_by_opcode(g.opcode) else "???"}
                for g in best.genes
            ]
            evolved_locus["evolved_fitness"] = best.fitness
            evolved_locus["evolved_origin"] = best.origin
            evolved_locus["evolved_platform_scores"] = best.platform_scores
            self.loaded_loci[locus_name] = evolved_locus
            return {
                "locus_name": locus_name,
                "best_fitness": best.fitness,
                "best_genes_count": len(best.genes),
                "platform_scores": best.platform_scores,
                "evolution_history": [
                    {"generation": h["generation"], "best_fitness": h["best_fitness"]}
                    for h in engine.get_evolution_history()
                ],
            }
        return None

    def self_compile(self, source: str) -> dict:
        result = self.compiler.compile(source, output_format="dict")
        for locus in result.get("loci", []):
            self.loaded_loci[locus["name"]] = locus
        for meta in result.get("meta_loci", []):
            self.loaded_loci[f"meta:{meta['name']}"] = meta
        return result

    def bootstrap_pipeline(self, evo_source: str, generations: int = 20) -> dict:
        step1 = self.load_evo_source(evo_source)
        loci_names = [l["name"] for l in step1.get("loci", [])]
        meta_names = [f"meta:{m['name']}" for m in step1.get("meta_loci", [])]
        results = {
            "compilation": step1,
            "evolution": {},
            "execution": {},
        }
        for name in loci_names:
            evo_result = self.evolve_locus(name, generations=generations)
            if evo_result:
                results["evolution"][name] = evo_result
            exec_result = self.execute_locus(name, max_cycles=1000)
            results["execution"][name] = exec_result
        return results

    def export_evolved_locus(self, locus_name: str) -> Optional[str]:
        locus = self.loaded_loci.get(locus_name)
        if not locus:
            return None
        lines = ['@evolang "3.0"', ""]
        if "xiangci" in locus:
            lines.append(f'@xiangci {{')
            lines.append(f'    "{locus.get("xiangci", "")}"')
            lines.append(f'}}')
            lines.append("")
        lines.append(f"@locus {locus_name} {{")
        lines.append(f"    mut_rate   = {locus.get('mut_rate', 0.02)}")
        lines.append(f"    cross_pool = \"{locus.get('cross_pool', 'default')}\"")
        if locus.get("env_targets"):
            targets = ", ".join(f'"{t}"' for t in locus["env_targets"])
            lines.append(f"    env_target = [{targets}]")
        lines.append("")
        lines.append("    卦序: {")
        for instr in locus.get("instructions", []):
            symbol = instr.get("symbol", "")
            mnemonic = instr.get("mnemonic", "")
            line = f"        {symbol} {mnemonic}" if symbol else f"        {mnemonic}"
            lines.append(line)
        lines.append("    }")
        lines.append("}")
        return "\n".join(lines)
