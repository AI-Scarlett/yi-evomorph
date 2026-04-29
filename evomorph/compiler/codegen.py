import struct
import json
from .parser import Parser, ProgramNode, LocusNode, MetaLocusNode, InstructionNode
from evomorph.hexagrams import HexagramInstructionSet


class CodeGenerator:
    def __init__(self, instruction_set=None):
        self.isa = instruction_set or HexagramInstructionSet()
        self.bytecode = bytearray()
        self.symbol_table = {}
        self.relocation_table = []
        self.metadata = {}

    def generate(self, ast):
        if isinstance(ast, ProgramNode):
            return self._generate_program(ast)
        elif isinstance(ast, LocusNode):
            return self._generate_locus(ast)
        return bytearray()

    def _generate_program(self, program):
        result = {}
        if program.version:
            result["version"] = program.version
        result["loci"] = []
        for locus in program.loci:
            locus_data = self._generate_locus(locus)
            result["loci"].append(locus_data)
        result["meta_loci"] = []
        for meta in program.meta_loci:
            meta_data = self._generate_meta_locus(meta)
            result["meta_loci"].append(meta_data)
        result["xiangci"] = []
        for xiangci in program.xiangci_blocks:
            result["xiangci"].append({"text": xiangci.text})
        return result

    def _generate_locus(self, locus):
        self.bytecode = bytearray()
        self.symbol_table = {}
        self.relocation_table = []
        instructions_data = []
        for instr in locus.instructions:
            encoded = self._encode_instruction(instr)
            instructions_data.append(encoded)
        return {
            "name": locus.name,
            "mut_rate": locus.mut_rate,
            "cross_pool": locus.cross_pool,
            "fitness": self._serialize_fitness(locus.fitness_expr),
            "env_targets": locus.env_targets,
            "max_generations": locus.max_generations,
            "instructions": instructions_data,
            "bytecode": list(self.bytecode),
        }

    def _generate_meta_locus(self, meta):
        self.bytecode = bytearray()
        instructions_data = []
        for instr in meta.instructions:
            encoded = self._encode_instruction(instr)
            instructions_data.append(encoded)
        return {
            "name": meta.name,
            "mut_rate": meta.mut_rate,
            "fitness": self._serialize_fitness(meta.fitness_expr),
            "instructions": instructions_data,
            "bytecode": list(self.bytecode),
        }

    def _encode_instruction(self, instr):
        opcode = instr.opcode if instr.opcode is not None else 0
        modifier = instr.modifier if hasattr(instr, "modifier") else 0
        operands = []
        for op in instr.operands:
            operands.append(self._encode_operand(op))
        byte1 = ((opcode & 0x3F) << 2) | ((modifier >> 4) & 0x03)
        byte2 = modifier & 0x0F
        self.bytecode.extend([byte1, byte2])
        for op_bytes in operands:
            self.bytecode.extend(op_bytes)
        return {
            "opcode": opcode,
            "symbol": instr.symbol,
            "mnemonic": instr.mnemonic,
            "modifier": modifier,
            "operands": [self._operand_to_dict(op) for op in instr.operands],
            "offset": len(self.bytecode) - 2,
        }

    def _encode_operand(self, operand):
        if operand.kind == "register":
            reg_idx = self._register_index(operand.value)
            return bytes([reg_idx & 0xFF])
        elif operand.kind == "immediate":
            val = int(operand.value)
            return struct.pack(">i", val)
        elif operand.kind == "label":
            self.relocation_table.append({
                "label": operand.value,
                "offset": len(self.bytecode),
            })
            return struct.pack(">i", 0)
        elif operand.kind == "env_ref":
            return struct.pack(">i", hash(operand.value) & 0x7FFFFFFF)
        else:
            return struct.pack(">i", 0)

    def _register_index(self, name):
        special = {
            "R_FP": 12, "R_SP": 13, "R_LR": 14, "R_A0": 15,
        }
        if name in special:
            return special[name]
        if name.startswith("R") and name[1:].isdigit():
            return int(name[1:])
        return 0

    def _operand_to_dict(self, operand):
        return {"kind": operand.kind, "value": operand.value}

    def _serialize_fitness(self, fitness_expr):
        if fitness_expr is None:
            return None
        return {
            "terms": [
                {"keyword": t.keyword, "weight": t.weight}
                for t in fitness_expr.terms
            ]
        }

    def generate_evb(self, program_ast):
        self.bytecode = bytearray()
        header = bytearray()
        header.extend(b"EVOB")
        header.extend(struct.pack(">H", 3))
        header.extend(struct.pack(">H", 0))
        loci_offsets = []
        for locus in program_ast.loci:
            offset = len(self.bytecode)
            loci_offsets.append(offset)
            for instr in locus.instructions:
                opcode = instr.opcode if instr.opcode is not None else 0
                modifier = instr.modifier if hasattr(instr, "modifier") else 0
                byte1 = ((opcode & 0x3F) << 2) | ((modifier >> 4) & 0x03)
                byte2 = modifier & 0x0F
                self.bytecode.extend([byte1, byte2])
                for op in instr.operands:
                    self.bytecode.extend(self._encode_operand(op))
        header.extend(struct.pack(">H", len(loci_offsets)))
        for offset in loci_offsets:
            header.extend(struct.pack(">I", offset))
        header[6:8] = struct.pack(">H", len(header))
        return bytes(header + self.bytecode)

    def generate_json(self, program_ast):
        result = self._generate_program(program_ast)
        return json.dumps(result, ensure_ascii=False, indent=2)
