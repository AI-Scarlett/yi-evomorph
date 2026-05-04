import os
from evomorph.bootstrap.runtime import EvoRuntime
from evomorph.compiler import EvocCompiler
from evomorph.evolution.engine import GeneInstruction, Individual, EvolutionConfig, EvolutionEngine
from evomorph.simulator.niche import PlatformSimNiche


_STDLIB_PATH = os.path.dirname(os.path.abspath(__file__))
_RUNTIME = EvoRuntime()


def _load_evo_stdlib(filename: str):
    filepath = os.path.join(_STDLIB_PATH, filename)
    if not os.path.exists(filepath):
        return {}
    return _RUNTIME.load_evo_file(filepath)


def load_io():
    return _load_evo_stdlib("io.evo")


def load_sync():
    return _load_evo_stdlib("sync.evo")


def load_math():
    return _load_evo_stdlib("math.evo")


def load_ai():
    return _load_evo_stdlib("ai.evo")


def load_all():
    return {
        "io": load_io(),
        "sync": load_sync(),
        "math": load_math(),
        "ai": load_ai(),
    }


def execute_locus(locus_name: str, max_cycles: int = 10000):
    return _RUNTIME.execute_locus(locus_name, max_cycles)


def evolve_locus(locus_name: str, generations: int = 20, population_size: int = 32):
    return _RUNTIME.evolve_locus(locus_name, generations, population_size)


def get_locus_gene_instructions(locus_data: dict) -> list:
    instructions = []
    for instr in locus_data.get("instructions", []):
        gene = GeneInstruction(
            opcode=instr.get("opcode", 0),
            modifier=instr.get("modifier", 0),
            operands=[op.get("value", 0) if isinstance(op, dict) else op
                      for op in instr.get("operands", [])],
        )
        instructions.append(gene)
    return instructions


def get_runtime():
    return _RUNTIME
