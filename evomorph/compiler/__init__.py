from .lexer import Lexer
from .parser import Parser
from .codegen import CodeGenerator
from evomorph.hexagrams import HexagramInstructionSet


class EvocCompiler:
    def __init__(self, instruction_set=None):
        self.isa = instruction_set or HexagramInstructionSet()
        self.codegen = CodeGenerator(self.isa)

    def compile(self, source, output_format="json"):
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens, self.isa)
        ast = parser.parse()
        if output_format == "json":
            return self.codegen.generate_json(ast)
        elif output_format == "evb":
            return self.codegen.generate_evb(ast)
        elif output_format == "dict":
            return self.codegen.generate(ast)
        else:
            return self.codegen.generate(ast)

    def compile_file(self, filepath, output_format="json"):
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        return self.compile(source, output_format)
