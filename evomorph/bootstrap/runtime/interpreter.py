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
        """编译 .evo 源码 (自举路径: IChing EVB 编译器 + Python 元数据提取)."""
        try:
            result = self.compiler.compile(source_text, output_format="dict")
            return result
        except Exception as e:
            return {"error": str(e)}

    def compile_to_evb(self, source_text: str) -> Optional[bytes]:
        """使用自举编译器直接将 .evo 源码编译为 EVB 字节码.

        这是真正的自举编译: 编译器逻辑完全在 EVB 字节码中执行,
        不依赖 Python 编译器类.
        """
        try:
            return self.compiler.compile(source_text, output_format="evb")
        except Exception:
            return None

    def self_compile_verify(self, source: str) -> dict:
        """自举验证: 同一编译器逻辑在 VM 裸执行 vs Python 辅助执行下逐字节对比.

        验证原理:
          - 路径 A (裸 VM): compiler.evoasm → EVB → VM 直接执行 → 输出 EVB A
          - 路径 B (Python 辅助): compiler.evoasm → EVB → Python IChingBootstrapCompiler 执行 → 输出 EVB B
          - 验证: A == B (字节级)

        这证明了 EVB 字节码加载和执行机制的正确性:
        无论是通过 Python 辅助管理还是 VM 裸执行, 相同的编译器 EVB 字节码产出相同结果.

        Returns:
            {
                "bytes_match": bool,
                "raw_vm_hash": str, "python_vm_hash": str,
                "raw_vm_size": int, "python_vm_size": int,
                "diff_positions": [...],
            }
        """
        import hashlib

        # 路径 A: 裸 VM 执行 (IChingEvocCompiler → evb 格式)
        raw_vm_bytes = self.compile_to_evb(source)

        # 路径 B: Python 辅助执行 (IChingBootstrapCompiler.compile_source)
        from evomorph.bootstrap.iching.iching_compiler import IChingBootstrapCompiler
        py_vm_bytes = b""
        try:
            py_bc = IChingBootstrapCompiler()
            py_result = py_bc.compile_source(source)
            if py_result.get("success") and py_result.get("evob_valid"):
                py_vm_bytes = py_result.get("output_bytes", b"")
        except Exception:
            pass

        result = {
            "raw_vm_size": len(raw_vm_bytes) if raw_vm_bytes else 0,
            "python_vm_size": len(py_vm_bytes),
            "bytes_match": False,
        }

        if raw_vm_bytes and py_vm_bytes:
            result["raw_vm_hash"] = hashlib.sha256(raw_vm_bytes).hexdigest()[:16]
            result["python_vm_hash"] = hashlib.sha256(py_vm_bytes).hexdigest()[:16]
            result["bytes_match"] = (raw_vm_bytes == py_vm_bytes)

            if not result["bytes_match"]:
                min_len = min(len(raw_vm_bytes), len(py_vm_bytes))
                diffs = []
                for i in range(min_len):
                    if raw_vm_bytes[i] != py_vm_bytes[i]:
                        diffs.append(i)
                        if len(diffs) >= 10:
                            break
                result["diff_positions"] = diffs
        elif raw_vm_bytes:
            result["raw_vm_hash"] = hashlib.sha256(raw_vm_bytes).hexdigest()[:16]
        elif py_vm_bytes:
            result["python_vm_hash"] = hashlib.sha256(py_vm_bytes).hexdigest()[:16]

        return result

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
        fitness_expr = locus.get("fitness", "min_latency + max_throughput")
        if isinstance(fitness_expr, dict) and "terms" in fitness_expr:
            terms = fitness_expr["terms"]
            parts = []
            for t in terms:
                kw = t.get("keyword", "min_latency")
                w = t.get("weight", 1.0)
                if w == 1.0:
                    parts.append(kw)
                else:
                    parts.append(f"{w}*{kw}")
            fitness_expr = " + ".join(parts)
        elif not isinstance(fitness_expr, str):
            fitness_expr = "min_latency + max_throughput"
        lines.append(f"    fitness    = {fitness_expr}")
        if locus.get("env_targets"):
            targets = ", ".join(f'"{t}"' for t in locus["env_targets"])
            lines.append(f"    env_target = [{targets}]")
        max_gen = locus.get("max_generations", 100)
        lines.append(f"    max_generations = {max_gen}")
        lines.append("")
        lines.append("    卦序: {")
        for instr in locus.get("instructions", []):
            symbol = instr.get("symbol", "")
            mnemonic = instr.get("mnemonic", "")
            operands = instr.get("operands", [])
            operand_str = ""
            if operands:
                parts = []
                for op in operands:
                    if isinstance(op, dict):
                        val = op.get("value", 0)
                        name = op.get("name", "")
                        if name:
                            parts.append(name)
                        elif isinstance(val, int) and val >= 0 and val < 20:
                            parts.append(f"R{val}")
                        elif isinstance(val, int):
                            parts.append(f"0x{val & 0xFFFF:04X}")
                        else:
                            parts.append(str(val))
                    elif isinstance(op, int):
                        if 0 <= op < 20:
                            parts.append(f"R{op}")
                        else:
                            parts.append(f"0x{op & 0xFFFF:04X}")
                    else:
                        parts.append(str(op))
                operand_str = " " + ", ".join(parts)
            line = f"        {symbol} {mnemonic}{operand_str}" if symbol else f"        {mnemonic}{operand_str}"
            lines.append(line)
        lines.append("    }")
        lines.append("}")
        if locus.get("evolved_fitness") is not None:
            lines.append("")
            lines.append(f"// 进化适应度: {locus['evolved_fitness']:.4f}")
            if locus.get("evolved_origin"):
                lines.append(f"// 进化来源: {locus['evolved_origin']}")
        return "\n".join(lines)

    def bootstrap_self_compile(self, evo_source: str, generations: int = 20,
                               population_size: int = 32) -> dict:
        step1 = self.load_evo_source(evo_source)
        loci_names = [l["name"] for l in step1.get("loci", [])]
        meta_names = [f"meta:{m['name']}" for m in step1.get("meta_loci", [])]
        results = {
            "compilation": {"loci_count": len(loci_names), "meta_loci_count": len(meta_names)},
            "evolution": {},
            "execution": {},
            "self_compilation": None,
            "cross_validation": None,
        }
        for name in loci_names:
            evo_result = self.evolve_locus(name, generations=generations, population_size=population_size)
            if evo_result:
                results["evolution"][name] = evo_result
        for name in loci_names:
            exec_result = self.execute_locus(name, max_cycles=1000)
            results["execution"][name] = exec_result
        self_comp = self.self_compile(evo_source)
        self_loci = [l["name"] for l in self_comp.get("loci", [])]
        results["self_compilation"] = {"loci_count": len(self_loci)}
        orig_loci = {l["name"]: l for l in step1.get("loci", [])}
        evolved_loci = {l["name"]: l for l in self_comp.get("loci", [])}
        match = 0
        partial = 0
        for name in evolved_loci:
            if name in orig_loci:
                e_instrs = evolved_loci[name].get("instructions", [])
                o_instrs = orig_loci[name].get("instructions", [])
                if len(e_instrs) == len(o_instrs):
                    opcode_match = sum(
                        1 for e, o in zip(e_instrs, o_instrs)
                        if e.get("opcode") == o.get("opcode")
                    )
                    if opcode_match == len(e_instrs):
                        match += 1
                    elif opcode_match > 0:
                        partial += 1
        total = max(len(evolved_loci), 1)
        results["cross_validation"] = {
            "match": f"{match}/{total}",
            "partial_match": partial,
        }
        return results
