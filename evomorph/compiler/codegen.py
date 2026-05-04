import struct
import json
from typing import Dict, List, Optional, Any, Tuple
from .parser import Parser, ProgramNode, LocusNode, MetaLocusNode, InstructionNode, FitnessExpr, FitnessTerm, OperandNode
from evomorph.hexagrams import HexagramInstructionSet


class CodeGeneratorError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0):
        self.message = message
        self.line = line
        self.col = col
        super().__init__(f"CodeGen error at L{line}:{col}: {message}")


class CodeGenerator:
    EVOB_MAGIC = b"EVOB"
    EVOB_VERSION = 3
    HEADER_SIZE_MIN = 12

    SPECIAL_REGISTERS = {
        "R_FP": 12,
        "R_SP": 13,
        "R_LR": 14,
        "R_A0": 15,
    }

    def __init__(self, instruction_set: Optional[HexagramInstructionSet] = None):
        self.isa: HexagramInstructionSet = instruction_set or HexagramInstructionSet()
        self.bytecode: bytearray = bytearray()
        self.symbol_table: Dict[str, int] = {}
        self.relocation_table: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self._errors: List[CodeGeneratorError] = []

    def reset(self):
        self.bytecode = bytearray()
        self.symbol_table = {}
        self.relocation_table = []
        self.metadata = {}
        self._errors = []

    def generate(self, ast: Any) -> Any:
        if isinstance(ast, ProgramNode):
            return self._generate_program(ast)
        elif isinstance(ast, LocusNode):
            return self._generate_locus(ast)
        return {}

    def _generate_program(self, program: ProgramNode) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        if program.version:
            result["version"] = program.version

        result["loci"] = []
        for locus in program.loci:
            try:
                locus_data = self._generate_locus(locus)
                result["loci"].append(locus_data)
            except CodeGeneratorError as e:
                self._errors.append(e)
                result["loci"].append({"name": locus.name, "error": e.message})

        result["meta_loci"] = []
        for meta in program.meta_loci:
            try:
                meta_data = self._generate_meta_locus(meta)
                result["meta_loci"].append(meta_data)
            except CodeGeneratorError as e:
                self._errors.append(e)
                result["meta_loci"].append({"name": meta.name, "error": e.message})

        result["xiangci"] = []
        for xiangci in program.xiangci_blocks:
            result["xiangci"].append({"text": xiangci.text})

        if self._errors:
            result["errors"] = [
                {"message": e.message, "line": e.line, "col": e.col}
                for e in self._errors
            ]

        return result

    def _generate_locus(self, locus: LocusNode) -> Dict[str, Any]:
        self.reset()
        instructions_data: List[Dict[str, Any]] = []

        for instr in locus.instructions:
            try:
                encoded = self._encode_instruction(instr)
                instructions_data.append(encoded)
            except CodeGeneratorError as e:
                self._errors.append(e)
                instructions_data.append({
                    "error": e.message,
                    "line": instr.line,
                    "col": instr.col,
                })

        return {
            "name": locus.name,
            "mut_rate": locus.mut_rate,
            "cross_pool": locus.cross_pool,
            "fitness": self._serialize_fitness(locus.fitness_expr),
            "env_targets": locus.env_targets,
            "max_generations": locus.max_generations,
            "instructions": instructions_data,
            "bytecode": list(self.bytecode),
            "symbol_table": dict(self.symbol_table),
            "relocation_table": list(self.relocation_table),
        }

    def _generate_meta_locus(self, meta: MetaLocusNode) -> Dict[str, Any]:
        self.reset()
        instructions_data: List[Dict[str, Any]] = []

        for instr in meta.instructions:
            try:
                encoded = self._encode_instruction(instr)
                instructions_data.append(encoded)
            except CodeGeneratorError as e:
                self._errors.append(e)
                instructions_data.append({
                    "error": e.message,
                    "line": instr.line,
                    "col": instr.col,
                })

        return {
            "name": meta.name,
            "mut_rate": meta.mut_rate,
            "fitness": self._serialize_fitness(meta.fitness_expr),
            "instructions": instructions_data,
            "bytecode": list(self.bytecode),
        }

    def _encode_instruction(self, instr: InstructionNode) -> Dict[str, Any]:
        opcode: int = instr.opcode if instr.opcode is not None else 0
        modifier: int = instr.modifier if hasattr(instr, "modifier") else 0

        operands_encoded: List[bytes] = []
        for op in instr.operands:
            try:
                encoded = self._encode_operand(op)
                operands_encoded.append(encoded)
            except CodeGeneratorError as e:
                self._errors.append(e)
                operands_encoded.append(b"\x00")

        while len(operands_encoded) < 2:
            operands_encoded.append(b"\x00")

        byte1 = ((opcode & 0x3F) << 2) | ((modifier >> 4) & 0x03)
        byte2 = modifier & 0x0F

        offset = len(self.bytecode)
        self.bytecode.extend([byte1, byte2])

        for op_bytes in operands_encoded[:2]:
            self.bytecode.extend(op_bytes)

        return {
            "opcode": opcode,
            "symbol": instr.symbol,
            "mnemonic": instr.mnemonic,
            "modifier": modifier,
            "operands": [self._operand_to_dict(op) for op in instr.operands],
            "offset": offset,
            "line": getattr(instr, "line", 0),
            "col": getattr(instr, "col", 0),
        }

    def _encode_operand(self, operand: OperandNode) -> bytes:
        kind = operand.kind
        value = operand.value

        if kind == "register":
            reg_idx = self._register_index(str(value))
            return bytes([reg_idx & 0x0F])

        elif kind == "immediate":
            try:
                val = int(value)
                return bytes([val & 0xFF])
            except (ValueError, TypeError):
                if isinstance(value, float):
                    ival = int(value)
                    return bytes([ival & 0xFF])
                return bytes([0])

        elif kind == "label":
            label_str = str(value)
            self.relocation_table.append({
                "label": label_str,
                "offset": len(self.bytecode),
            })
            if label_str in self.symbol_table:
                return bytes([self.symbol_table[label_str] & 0xFF])
            return bytes([0])

        elif kind == "env_ref":
            env_str = str(value)
            hash_val = hash(env_str) & 0xFF
            return bytes([hash_val])

        elif kind == "string":
            str_val = str(value)
            hash_val = hash(str_val) & 0xFF
            return bytes([hash_val])

        elif kind == "identifier":
            ident_str = str(value)
            if ident_str.startswith("R") and len(ident_str) > 1:
                if ident_str[1:].isdigit():
                    reg_idx = int(ident_str[1:])
                    return bytes([reg_idx & 0x0F])
            hash_val = hash(ident_str) & 0xFF
            return bytes([hash_val])

        else:
            return bytes([0])

    def _register_index(self, name: str) -> int:
        if name in self.SPECIAL_REGISTERS:
            return self.SPECIAL_REGISTERS[name]

        if name.startswith("R") and name[1:].isdigit():
            idx = int(name[1:])
            return idx & 0x0F

        return 0

    def _operand_to_dict(self, operand: OperandNode) -> Dict[str, Any]:
        return {
            "kind": operand.kind,
            "value": operand.value,
        }

    def _serialize_fitness(self, fitness_expr: Optional[FitnessExpr]) -> Optional[Dict[str, Any]]:
        if fitness_expr is None:
            return None

        return {
            "terms": [
                {"keyword": t.keyword, "weight": t.weight}
                for t in fitness_expr.terms
            ]
        }

    def generate_evb(self, program_ast: ProgramNode) -> bytes:
        self.reset()
        header = bytearray()

        header.extend(self.EVOB_MAGIC)
        header.extend(struct.pack(">H", self.EVOB_VERSION))

        header_size_offset = len(header)
        header.extend(struct.pack(">H", 0))

        loci_offsets: List[int] = []

        for locus in program_ast.loci:
            offset = len(self.bytecode)
            loci_offsets.append(offset)

            for instr in locus.instructions:
                opcode = instr.opcode if instr.opcode is not None else 0
                modifier = instr.modifier if hasattr(instr, "modifier") else 0

                byte1 = ((opcode & 0x3F) << 2) | ((modifier >> 4) & 0x03)
                byte2 = modifier & 0x0F
                self.bytecode.extend([byte1, byte2])

                operands_count = 0
                for op in instr.operands:
                    try:
                        encoded = self._encode_operand(op)
                        self.bytecode.extend(encoded)
                        operands_count += 1
                    except CodeGeneratorError:
                        self.bytecode.extend(b"\x00")
                        operands_count += 1
                
                while operands_count < 2:
                    self.bytecode.extend(b"\x00")
                    operands_count += 1

        header.extend(struct.pack(">H", len(loci_offsets)))
        for offset in loci_offsets:
            header.extend(struct.pack(">I", offset))

        actual_header_size = len(header)
        header[header_size_offset:header_size_offset + 2] = struct.pack(">H", actual_header_size)

        return bytes(header + self.bytecode)

    def parse_evb(self, evb_data: bytes) -> Dict[str, Any]:
        if len(evb_data) < self.HEADER_SIZE_MIN:
            raise CodeGeneratorError(f"EVB data too short: expected at least {self.HEADER_SIZE_MIN} bytes")

        offset = 0

        magic = evb_data[offset:offset + 4]
        offset += 4

        if magic != self.EVOB_MAGIC:
            raise CodeGeneratorError(f"Invalid EVOB magic: expected {self.EVOB_MAGIC!r}, got {magic!r}")

        version = struct.unpack(">H", evb_data[offset:offset + 2])[0]
        offset += 2

        header_size = struct.unpack(">H", evb_data[offset:offset + 2])[0]
        offset += 2

        if header_size < self.HEADER_SIZE_MIN or header_size > len(evb_data):
            raise CodeGeneratorError(f"Invalid header size: {header_size}")

        num_loci = struct.unpack(">H", evb_data[offset:offset + 2])[0]
        offset += 2

        loci_offsets: List[int] = []
        for _ in range(num_loci):
            if offset + 4 > len(evb_data):
                raise CodeGeneratorError("Truncated loci offsets")
            loci_offset = struct.unpack(">I", evb_data[offset:offset + 4])[0]
            loci_offsets.append(loci_offset)
            offset += 4

        return {
            "magic": magic,
            "version": version,
            "header_size": header_size,
            "num_loci": num_loci,
            "loci_offsets": loci_offsets,
            "code_offset": header_size,
            "code_size": len(evb_data) - header_size,
        }

    def generate_json(self, program_ast: ProgramNode) -> str:
        result = self._generate_program(program_ast)
        return json.dumps(result, ensure_ascii=False, indent=2)

    def generate_from_tokens(self, tokens: List[Any]) -> Dict[str, Any]:
        parser = Parser(tokens, self.isa)
        ast = parser.parse()
        return self._generate_program(ast)

    def validate_instruction(self, opcode: int, operands: List[Any]) -> Tuple[bool, str]:
        if opcode < 0 or opcode > 63:
            return False, f"Invalid opcode: {opcode} (must be 0-63)"

        entry = self.isa.get_by_opcode(opcode)
        if not entry:
            return False, f"Unknown opcode: {opcode}"

        return True, "Valid"

    def get_errors(self) -> List[CodeGeneratorError]:
        return self._errors.copy()

    def link_labels(self, label_offsets: Dict[str, int]):
        for reloc in self.relocation_table:
            label = reloc["label"]
            offset = reloc["offset"]

            if label in label_offsets:
                target_offset = label_offsets[label]
                if offset + 4 <= len(self.bytecode):
                    packed = struct.pack(">i", target_offset)
                    self.bytecode[offset:offset + 4] = packed

    def optimize_bytecode(self, level: int = 1) -> int:
        if level < 1:
            return 0

        optimizations = 0

        if level >= 1:
            optimizations += self._remove_redundant_nops()
            optimizations += self._remove_redundant_moves()
            optimizations += self._merge_adjacent_instructions()

        if level >= 2:
            optimizations += self._fold_constants()
            optimizations += self._dead_code_elimination()
            optimizations += self._register_allocation_optimization()

        if level >= 3:
            optimizations += self._loop_optimization()
            optimizations += self._instruction_scheduling()
            optimizations += self._strength_reduction()

        return optimizations

    def _remove_redundant_nops(self) -> int:
        if len(self.bytecode) < 4:
            return 0

        optimized = 0
        new_bytecode = bytearray()
        i = 0

        while i < len(self.bytecode):
            if i + 3 < len(self.bytecode):
                byte1 = self.bytecode[i]
                byte2 = self.bytecode[i + 1]
                opcode = (byte1 >> 2) & 0x3F

                if opcode == 56:
                    optimized += 1
                    i += 4
                    continue

            if i < len(self.bytecode):
                new_bytecode.append(self.bytecode[i])
                i += 1

        if optimized > 0:
            self.bytecode = new_bytecode

        return optimized

    def _remove_redundant_moves(self) -> int:
        if len(self.bytecode) < 8:
            return 0

        optimized = 0
        new_bytecode = bytearray()
        i = 0

        while i < len(self.bytecode) - 3:
            if i + 7 < len(self.bytecode):
                byte1_1 = self.bytecode[i]
                byte2_1 = self.bytecode[i + 1]
                op1 = (byte1_1 >> 2) & 0x3F
                op1_dst = self.bytecode[i + 2]
                op1_src = self.bytecode[i + 3]

                byte1_2 = self.bytecode[i + 4]
                byte2_2 = self.bytecode[i + 5]
                op2 = (byte1_2 >> 2) & 0x3F
                op2_dst = self.bytecode[i + 6]
                op2_src = self.bytecode[i + 7]

                move_ops = {25, 61, 15, 53, 43, 29, 46}
                if op1 in move_ops and op2 in move_ops:
                    if op1_src == op2_dst and op1_dst == op2_src:
                        optimized += 1
                        i += 8
                        continue

            if i < len(self.bytecode):
                new_bytecode.append(self.bytecode[i])
                i += 1

        if optimized > 0:
            self.bytecode = new_bytecode

        return optimized

    def _merge_adjacent_instructions(self) -> int:
        if len(self.bytecode) < 8:
            return 0

        optimized = 0
        new_bytecode = bytearray()
        i = 0

        while i < len(self.bytecode) - 3:
            if i + 7 < len(self.bytecode):
                byte1_1 = self.bytecode[i]
                byte2_1 = self.bytecode[i + 1]
                op1 = (byte1_1 >> 2) & 0x3F
                op1_dst = self.bytecode[i + 2]
                op1_src = self.bytecode[i + 3]

                byte1_2 = self.bytecode[i + 4]
                byte2_2 = self.bytecode[i + 5]
                op2 = (byte1_2 >> 2) & 0x3F
                op2_dst = self.bytecode[i + 6]
                op2_src = self.bytecode[i + 7]

                if op1 == 24 and op2 == 24 and op1_dst == op2_dst:
                    new_bytecode.extend([byte1_1, byte2_1, op1_dst, op1_src + op2_src])
                    optimized += 1
                    i += 8
                    continue

                if op1 == 49 and op2 == 49 and op1_dst == op2_dst:
                    new_bytecode.extend([byte1_1, byte2_1, op1_dst, op1_src + op2_src])
                    optimized += 1
                    i += 8
                    continue

            if i < len(self.bytecode):
                new_bytecode.append(self.bytecode[i])
                i += 1

        if optimized > 0:
            self.bytecode = new_bytecode

        return optimized

    def _fold_constants(self) -> int:
        if len(self.bytecode) < 4:
            return 0

        optimized = 0
        new_bytecode = bytearray()
        i = 0

        while i < len(self.bytecode):
            if i + 3 < len(self.bytecode):
                byte1 = self.bytecode[i]
                byte2 = self.bytecode[i + 1]
                opcode = (byte1 >> 2) & 0x3F
                dst = self.bytecode[i + 2]
                src = self.bytecode[i + 3]

                arithmetic_ops = {24, 49, 35, 3, 16, 37, 55, 7}
                if opcode in arithmetic_ops:
                    if src < 16 and dst < 16:
                        pass
                    else:
                        if opcode == 24 and src == 0:
                            optimized += 1
                            i += 4
                            continue
                        if opcode == 49 and src == 0:
                            optimized += 1
                            i += 4
                            continue
                        if opcode == 35 and src == 0:
                            optimized += 1
                            i += 4
                            continue

            if i < len(self.bytecode):
                new_bytecode.append(self.bytecode[i])
                i += 1

        if optimized > 0:
            self.bytecode = new_bytecode

        return optimized

    def _dead_code_elimination(self) -> int:
        if len(self.bytecode) < 8:
            return 0

        optimized = 0
        new_bytecode = bytearray()
        i = 0
        used_registers = set()

        while i < len(self.bytecode):
            if i + 3 < len(self.bytecode):
                byte1 = self.bytecode[i]
                byte2 = self.bytecode[i + 1]
                opcode = (byte1 >> 2) & 0x3F
                dst = self.bytecode[i + 2]
                src = self.bytecode[i + 3]

                if opcode in {2, 56, 31, 60}:
                    pass
                elif dst not in used_registers and opcode not in {61, 25, 15, 53, 43, 29, 46}:
                    used_registers.add(src)
                    optimized += 1
                    i += 4
                    continue

                used_registers.add(dst)
                used_registers.add(src)

            if i < len(self.bytecode):
                new_bytecode.append(self.bytecode[i])
                i += 1

        if optimized > 0:
            self.bytecode = new_bytecode

        return optimized

    def _register_allocation_optimization(self) -> int:
        if len(self.bytecode) < 4:
            return 0

        optimized = 0
        register_usage = [0] * 16
        i = 0

        while i < len(self.bytecode) - 3:
            byte1 = self.bytecode[i]
            byte2 = self.bytecode[i + 1]
            opcode = (byte1 >> 2) & 0x3F
            dst = self.bytecode[i + 2]
            src = self.bytecode[i + 3]

            if dst < 16:
                register_usage[dst] += 1
            if src < 16:
                register_usage[src] += 1

            i += 4

        frequently_used = [i for i, count in enumerate(register_usage) if count > 5]
        rarely_used = [i for i, count in enumerate(register_usage) if count <= 1]

        if len(frequently_used) > 0 and len(rarely_used) > 0:
            optimized = 1

        return optimized

    def _loop_optimization(self) -> int:
        if len(self.bytecode) < 16:
            return 0

        optimized = 0
        i = 0

        while i < len(self.bytecode) - 3:
            if i + 15 < len(self.bytecode):
                byte1 = self.bytecode[i]
                byte2 = self.bytecode[i + 1]
                opcode = (byte1 >> 2) & 0x3F

                if opcode == 2:
                    loop_body_start = i + 4
                    branch_target = self.bytecode[i + 3]

                    if branch_target < i:
                        loop_size = i - branch_target
                        if loop_size <= 16 and loop_size > 0:
                            optimized += 1

            i += 4

        return optimized

    def _instruction_scheduling(self) -> int:
        if len(self.bytecode) < 8:
            return 0

        optimized = 0
        i = 0

        while i < len(self.bytecode) - 7:
            byte1_1 = self.bytecode[i]
            byte2_1 = self.bytecode[i + 1]
            op1 = (byte1_1 >> 2) & 0x3F
            op1_dst = self.bytecode[i + 2]
            op1_src = self.bytecode[i + 3]

            byte1_2 = self.bytecode[i + 4]
            byte2_2 = self.bytecode[i + 5]
            op2 = (byte1_2 >> 2) & 0x3F
            op2_dst = self.bytecode[i + 6]
            op2_src = self.bytecode[i + 7]

            memory_ops = {17, 47, 50, 54}
            arithmetic_ops = {24, 49, 35, 3, 16, 37, 55, 7}

            if op1 in memory_ops and op2 in arithmetic_ops:
                if op1_dst != op2_dst and op1_dst != op2_src and op1_src != op2_dst:
                    temp = bytearray()
                    temp.extend(self.bytecode[i + 4:i + 8])
                    temp.extend(self.bytecode[i:i + 4])

                    self.bytecode[i:i + 8] = temp
                    optimized += 1

            i += 4

        return optimized

    def _strength_reduction(self) -> int:
        if len(self.bytecode) < 4:
            return 0

        optimized = 0
        new_bytecode = bytearray()
        i = 0

        while i < len(self.bytecode):
            if i + 3 < len(self.bytecode):
                byte1 = self.bytecode[i]
                byte2 = self.bytecode[i + 1]
                opcode = (byte1 >> 2) & 0x3F
                dst = self.bytecode[i + 2]
                src = self.bytecode[i + 3]

                if opcode == 55 and src == 1:
                    new_bytecode.extend([
                        ((24 << 2) | ((0 >> 4) & 0x03)),
                        0 & 0x0F,
                        dst,
                        dst
                    ])
                    optimized += 1
                    i += 4
                    continue

                if opcode == 7 and src == 1:
                    new_bytecode.extend([
                        ((35 << 2) | ((0 >> 4) & 0x03)),
                        0 & 0x0F,
                        dst,
                        1
                    ])
                    optimized += 1
                    i += 4
                    continue

            if i < len(self.bytecode):
                new_bytecode.append(self.bytecode[i])
                i += 1

        if optimized > 0:
            self.bytecode = new_bytecode

        return optimized

    def dump_bytecode(self) -> str:
        lines = []
        lines.append(f"Bytecode size: {len(self.bytecode)} bytes")
        lines.append("-" * 40)

        for i in range(0, len(self.bytecode), 16):
            chunk = self.bytecode[i:i + 16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"{i:08X}: {hex_part:<48} {ascii_part}")

        return "\n".join(lines)

    def disassemble(self, bytecode: bytes) -> List[Dict[str, Any]]:
        instructions: List[Dict[str, Any]] = []
        offset = 0

        while offset < len(bytecode):
            if offset + 1 >= len(bytecode):
                break

            byte1 = bytecode[offset]
            byte2 = bytecode[offset + 1]
            offset += 2

            opcode = (byte1 >> 2) & 0x3F
            modifier = ((byte1 & 0x03) << 4) | (byte2 & 0x0F)

            entry = self.isa.get_by_opcode(opcode)
            mnemonic = entry["mnemonic"] if entry else f"UNKNOWN_{opcode:02X}"
            symbol = entry["symbol"] if entry else "???"

            operands: List[Dict[str, Any]] = []
            for _ in range(2):
                if offset < len(bytecode):
                    op_val = bytecode[offset]
                    offset += 1
                    operands.append({"kind": "byte", "value": op_val})
                else:
                    operands.append({"kind": "byte", "value": 0})

            instructions.append({
                "offset": offset - 2 - len(operands),
                "opcode": opcode,
                "modifier": modifier,
                "mnemonic": mnemonic,
                "symbol": symbol,
                "operands": operands,
            })

        return instructions

    def generate_header(self) -> Dict[str, Any]:
        return {
            "magic": self.EVOB_MAGIC,
            "version": self.EVOB_VERSION,
            "generator": "Evomorph CodeGenerator",
            "timestamp": None,
        }
