from .lexer import Lexer
from .parser import Parser
from .codegen import CodeGenerator
from .ir import IRProgram, IRLocus, IRBasicBlock, IRInstruction, IROperand, IRBuilder, IROptimizer, OperandType
from evomorph.hexagrams import HexagramInstructionSet
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum, auto


class ErrorSeverity(Enum):
    ERROR = auto()
    WARNING = auto()
    NOTE = auto()


class ErrorType(Enum):
    SYNTAX_ERROR = auto()
    SEMANTIC_ERROR = auto()
    TYPE_ERROR = auto()
    UNDEFINED_SYMBOL = auto()
    REDEFINED_SYMBOL = auto()
    INVALID_OPERAND = auto()
    INVALID_OPCODE = auto()
    MISSING_ATTRIBUTE = auto()
    INVALID_FITNESS = auto()
    INVALID_ENV_TARGET = auto()


@dataclass
class CompilerError:
    type: ErrorType
    message: str
    line: int = 0
    col: int = 0
    severity: ErrorSeverity = ErrorSeverity.ERROR
    context: str = ""
    suggestion: Optional[str] = None

    def __str__(self):
        return f"{self.severity.name} L{self.line}:{self.col}: {self.message}"


class CompilerDiagnostics:
    def __init__(self):
        self.errors: List[CompilerError] = []
        self.warnings: List[CompilerError] = []
        self.notes: List[CompilerError] = []

    def add_error(self, error: CompilerError):
        if error.severity == ErrorSeverity.ERROR:
            self.errors.append(error)
        elif error.severity == ErrorSeverity.WARNING:
            self.warnings.append(error)
        else:
            self.notes.append(error)

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def get_all(self) -> List[CompilerError]:
        return self.errors + self.warnings + self.notes

    def count(self) -> Dict[str, int]:
        return {
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "notes": len(self.notes)
        }


class ASTToIRConverter:
    def __init__(self, isa=None):
        self.isa = isa or HexagramInstructionSet()
        self.builder = IRBuilder(self.isa)
        self._block_counter = 0

    def convert(self, ast) -> IRProgram:
        program = self.builder.create_program(ast.version if hasattr(ast, 'version') else "3.0")

        if hasattr(ast, 'xiangci_blocks'):
            for xiangci in ast.xiangci_blocks:
                if hasattr(xiangci, 'text'):
                    program.xiangci.append(xiangci.text)

        if hasattr(ast, 'loci'):
            for locus_ast in ast.loci:
                locus = self._convert_locus(locus_ast)
                program.add_locus(locus)

        if hasattr(ast, 'meta_loci'):
            for meta_ast in ast.meta_loci:
                locus = self._convert_locus(meta_ast, is_meta=True)
                program.add_meta_locus(locus)

        return program

    def _convert_locus(self, locus_ast, is_meta: bool = False) -> IRLocus:
        locus = self.builder.create_locus(locus_ast.name if hasattr(locus_ast, 'name') else "unnamed")

        if hasattr(locus_ast, 'mut_rate'):
            locus.mut_rate = locus_ast.mut_rate
        if hasattr(locus_ast, 'cross_pool'):
            locus.cross_pool = locus_ast.cross_pool
        if hasattr(locus_ast, 'env_targets'):
            locus.env_targets = list(locus_ast.env_targets)
        if hasattr(locus_ast, 'max_generations'):
            locus.max_generations = locus_ast.max_generations

        if hasattr(locus_ast, 'fitness_expr') and locus_ast.fitness_expr:
            if hasattr(locus_ast.fitness_expr, 'terms'):
                for term in locus_ast.fitness_expr.terms:
                    locus.fitness_terms.append({
                        "keyword": term.keyword if hasattr(term, 'keyword') else "",
                        "weight": term.weight if hasattr(term, 'weight') else 1.0
                    })

        if hasattr(locus_ast, 'instructions') and locus_ast.instructions:
            entry_block = self._new_block_label()
            block = locus.add_basic_block(entry_block)

            for instr_ast in locus_ast.instructions:
                instr = self._convert_instruction(instr_ast)
                if instr:
                    block.add_instruction(instr)

        return locus

    def _convert_instruction(self, instr_ast) -> Optional[IRInstruction]:
        if not hasattr(instr_ast, 'opcode') or instr_ast.opcode is None:
            return None

        operands = []
        if hasattr(instr_ast, 'operands'):
            for op_ast in instr_ast.operands:
                operand = self._convert_operand(op_ast)
                if operand:
                    operands.append(operand)

        return self.builder.create_instruction(
            opcode=instr_ast.opcode,
            mnemonic=instr_ast.mnemonic if hasattr(instr_ast, 'mnemonic') else "",
            symbol=instr_ast.symbol if hasattr(instr_ast, 'symbol') else "???",
            operands=operands,
            modifier=instr_ast.modifier if hasattr(instr_ast, 'modifier') else 0
        )

    def _convert_operand(self, op_ast) -> Optional[IROperand]:
        if not hasattr(op_ast, 'kind'):
            return None

        kind = op_ast.kind
        value = op_ast.value if hasattr(op_ast, 'value') else None

        if kind == "register":
            name = str(value) if value else ""
            reg_num = 0
            if name.startswith("R") and len(name) > 1:
                try:
                    reg_num = int(name[1:])
                except ValueError:
                    pass
            return self.builder.create_operand("register", reg_num, name)
        elif kind == "immediate":
            return self.builder.create_operand("immediate", value)
        elif kind == "label":
            return self.builder.create_operand("label", value)
        elif kind == "env_ref":
            return self.builder.create_operand("immediate", hash(str(value)) & 0xFF)
        else:
            return self.builder.create_operand("immediate", 0)

    def _new_block_label(self) -> str:
        self._block_counter += 1
        return f"bb_{self._block_counter}"


class EvocCompiler:
    def __init__(self, instruction_set=None):
        self.isa = instruction_set or HexagramInstructionSet()
        self.codegen = CodeGenerator(self.isa)
        self.diagnostics = CompilerDiagnostics()
        self.converter = ASTToIRConverter(self.isa)
        self.optimization_level = 1

    def set_optimization_level(self, level: int):
        self.optimization_level = max(0, min(3, level))

    def compile(self, source, output_format="json"):
        self.diagnostics = CompilerDiagnostics()

        try:
            lexer = Lexer(source)
            tokens = lexer.tokenize()
        except Exception as e:
            self.diagnostics.add_error(CompilerError(
                type=ErrorType.SYNTAX_ERROR,
                message=f"Lexical error: {str(e)}",
                severity=ErrorSeverity.ERROR
            ))
            return self._generate_error_output()

        try:
            parser = Parser(tokens, self.isa)
            ast = parser.parse()
        except SyntaxError as e:
            line = 0
            col = 0
            if hasattr(e, 'lineno'):
                line = e.lineno
            if hasattr(e, 'offset'):
                col = e.offset
            self.diagnostics.add_error(CompilerError(
                type=ErrorType.SYNTAX_ERROR,
                message=str(e.msg) if hasattr(e, 'msg') else str(e),
                line=line,
                col=col,
                severity=ErrorSeverity.ERROR
            ))
            return self._generate_error_output()
        except Exception as e:
            self.diagnostics.add_error(CompilerError(
                type=ErrorType.SYNTAX_ERROR,
                message=f"Parse error: {str(e)}",
                severity=ErrorSeverity.ERROR
            ))
            return self._generate_error_output()

        self._semantic_analysis(ast)

        if self.diagnostics.has_errors():
            return self._generate_error_output()

        try:
            ir_program = self.converter.convert(ast)
        except Exception as e:
            self.diagnostics.add_error(CompilerError(
                type=ErrorType.SEMANTIC_ERROR,
                message=f"IR conversion error: {str(e)}",
                severity=ErrorSeverity.ERROR
            ))
            return self._generate_error_output()

        if self.optimization_level > 0:
            try:
                optimizer = IROptimizer(self.optimization_level)
                opt_results = optimizer.optimize(ir_program)
            except Exception as e:
                self.diagnostics.add_error(CompilerError(
                    type=ErrorType.SEMANTIC_ERROR,
                    message=f"Optimization error: {str(e)}",
                    severity=ErrorSeverity.WARNING
                ))

        try:
            if output_format == "json":
                result = self.codegen.generate_json(ast)
            elif output_format == "evb":
                result = self.codegen.generate_evb(ast)
            elif output_format == "dict":
                result = self.codegen.generate(ast)
            else:
                result = self.codegen.generate(ast)

            if self.optimization_level > 0:
                if hasattr(self.codegen, 'optimize_bytecode'):
                    opt_count = self.codegen.optimize_bytecode(self.optimization_level)

            if self.diagnostics.warnings or self.diagnostics.notes:
                if isinstance(result, dict):
                    result["warnings"] = [
                        {"message": w.message, "line": w.line, "col": w.col}
                        for w in self.diagnostics.warnings
                    ]
                    result["notes"] = [
                        {"message": n.message, "line": n.line, "col": n.col}
                        for n in self.diagnostics.notes
                    ]

            return result
        except Exception as e:
            self.diagnostics.add_error(CompilerError(
                type=ErrorType.SEMANTIC_ERROR,
                message=f"Code generation error: {str(e)}",
                severity=ErrorSeverity.ERROR
            ))
            return self._generate_error_output()

    def compile_file(self, filepath, output_format="json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            return self.compile(source, output_format)
        except FileNotFoundError:
            self.diagnostics.add_error(CompilerError(
                type=ErrorType.SEMANTIC_ERROR,
                message=f"File not found: {filepath}",
                severity=ErrorSeverity.ERROR
            ))
            return self._generate_error_output()
        except Exception as e:
            self.diagnostics.add_error(CompilerError(
                type=ErrorType.SEMANTIC_ERROR,
                message=f"Error reading file: {str(e)}",
                severity=ErrorSeverity.ERROR
            ))
            return self._generate_error_output()

    def _semantic_analysis(self, ast):
        if hasattr(ast, 'loci'):
            for locus in ast.loci:
                self._check_locus(locus)

        if hasattr(ast, 'meta_loci'):
            for meta in ast.meta_loci:
                self._check_locus(meta, is_meta=True)

    def _check_locus(self, locus, is_meta: bool = False):
        name = locus.name if hasattr(locus, 'name') else "unnamed"

        if not is_meta:
            if not hasattr(locus, 'mut_rate') or locus.mut_rate is None:
                self.diagnostics.add_error(CompilerError(
                    type=ErrorType.MISSING_ATTRIBUTE,
                    message=f"Locus '{name}' is missing 'mut_rate' attribute",
                    line=locus.line if hasattr(locus, 'line') else 0,
                    severity=ErrorSeverity.WARNING,
                    suggestion="Add 'mut_rate = 0.02' to locus definition"
                ))

            if not hasattr(locus, 'fitness_expr') or locus.fitness_expr is None:
                self.diagnostics.add_error(CompilerError(
                    type=ErrorType.MISSING_ATTRIBUTE,
                    message=f"Locus '{name}' is missing 'fitness' attribute",
                    line=locus.line if hasattr(locus, 'line') else 0,
                    severity=ErrorSeverity.WARNING,
                    suggestion="Add 'fitness = min_latency + max_throughput' to locus definition"
                ))

            if not hasattr(locus, 'env_targets') or not locus.env_targets:
                self.diagnostics.add_error(CompilerError(
                    type=ErrorType.MISSING_ATTRIBUTE,
                    message=f"Locus '{name}' is missing 'env_target' attribute",
                    line=locus.line if hasattr(locus, 'line') else 0,
                    severity=ErrorSeverity.WARNING,
                    suggestion="Add 'env_target = [\"linux-6.x\"]' to locus definition"
                ))

        if hasattr(locus, 'instructions'):
            for instr in locus.instructions:
                self._check_instruction(instr, name)

    def _check_instruction(self, instr, locus_name: str):
        if not hasattr(instr, 'opcode') or instr.opcode is None:
            self.diagnostics.add_error(CompilerError(
                type=ErrorType.INVALID_OPCODE,
                message=f"Invalid instruction in locus '{locus_name}'",
                line=instr.line if hasattr(instr, 'line') else 0,
                col=instr.col if hasattr(instr, 'col') else 0,
                severity=ErrorSeverity.ERROR
            ))
            return

        if hasattr(instr, 'operands'):
            for op in instr.operands:
                self._check_operand(op, locus_name)

    def _check_operand(self, operand, locus_name: str):
        if not hasattr(operand, 'kind'):
            return

        if operand.kind == "register":
            value = str(operand.value) if hasattr(operand, 'value') else ""
            if value.startswith("R"):
                try:
                    reg_num = int(value[1:])
                    if reg_num < 0 or reg_num > 15:
                        self.diagnostics.add_error(CompilerError(
                            type=ErrorType.INVALID_OPERAND,
                            message=f"Invalid register number {reg_num} in locus '{locus_name}'",
                            line=operand.line if hasattr(operand, 'line') else 0,
                            severity=ErrorSeverity.ERROR,
                            suggestion="Register numbers must be between 0 and 15"
                        ))
                except ValueError:
                    pass

        elif operand.kind == "immediate":
            value = operand.value if hasattr(operand, 'value') else 0
            if isinstance(value, int):
                if value < 0 or value > 255:
                    self.diagnostics.add_error(CompilerError(
                        type=ErrorType.INVALID_OPERAND,
                        message=f"Immediate value {value} out of range (0-255) in locus '{locus_name}'",
                        line=operand.line if hasattr(operand, 'line') else 0,
                        severity=ErrorSeverity.WARNING,
                        suggestion="Immediate values should be between 0 and 255"
                    ))

    def _generate_error_output(self) -> Dict[str, Any]:
        return {
            "error": True,
            "errors": [
                {
                    "type": e.type.name,
                    "message": e.message,
                    "line": e.line,
                    "col": e.col,
                    "severity": e.severity.name,
                    "suggestion": e.suggestion
                }
                for e in self.diagnostics.errors
            ],
            "warnings": [
                {
                    "message": w.message,
                    "line": w.line,
                    "col": w.col,
                    "suggestion": w.suggestion
                }
                for w in self.diagnostics.warnings
            ],
            "count": self.diagnostics.count()
        }
