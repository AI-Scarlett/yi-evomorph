from .lexer import Lexer
from .parser import Parser
from .codegen import CodeGenerator
from evomorph.hexagrams import HexagramInstructionSet


class EvocCompiler:
    def __init__(self, instruction_set=None, use_evomorph: bool = False):
        self.isa = instruction_set or HexagramInstructionSet()
        self.codegen = CodeGenerator(self.isa)
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
        elif not use_evomorph:
            self._backend = None

    def compile(self, source, output_format="json"):
        if self._use_evomorph and self._backend and self._backend.is_evomorph_available("lexer"):
            return self._backend.compile_source(source, output_format)
        
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

    def get_backend_status(self):
        """获取后端状态"""
        if self._backend:
            return {
                "use_evomorph": self._use_evomorph,
                "backend_available": self._backend.is_evomorph_available("lexer"),
                "backend_status": self._backend.get_status(),
            }
        return {
            "use_evomorph": self._use_evomorph,
            "backend_available": False,
            "message": "使用 Python 实现",
        }
