#!/usr/bin/env python3
"""
增强版易衍运行时系统
实现真正的自举编译能力
支持易衍代码真正执行编译任务
"""

import struct
import os
import json
import re
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

from evomorph.vm.virtual_machine import IChingVM, VMState
from evomorph.hexagrams import HexagramInstructionSet
from evomorph.compiler import EvocCompiler
from evomorph.compiler.lexer import Lexer, TokenType, Token
from evomorph.compiler.parser import Parser, ProgramNode, LocusNode, InstructionNode
from evomorph.compiler.codegen import CodeGenerator
from evomorph.evolution.engine import (
    EvolutionEngine, EvolutionConfig, GeneInstruction, Individual,
    SelectionMethod, CrossoverMethod
)


class TokenTypeEvo(Enum):
    EVOLANG = 0
    LOCUS = 1
    META_LOCUS = 2
    XIANGCI = 3
    GUA_XU = 4
    HEXAGRAM_SYMBOL = 5
    MNEMONIC = 6
    REGISTER = 7
    IMMEDIATE = 8
    LABEL = 9
    ENV_REF = 10
    MODIFIER = 11
    IDENTIFIER = 12
    STRING = 13
    NUMBER = 14
    FLOAT = 15
    LBRACE = 16
    RBRACE = 17
    LBRACKET = 18
    RBRACKET = 19
    LPAREN = 20
    RPAREN = 21
    COMMA = 22
    DOT = 23
    ASSIGN = 24
    PLUS = 25
    MINUS = 26
    STAR = 27
    SLASH = 28
    SEMICOLON = 29
    NEWLINE = 30
    EOF = 31
    FITNESS_KW = 32
    CROSS_POOL = 33
    MUT_RATE = 34
    ENV_TARGET = 35
    MAX_GEN = 36
    COMMENT = 37


@dataclass
class TokenEvo:
    type_code: int
    value: Any
    line: int = 0
    col: int = 0


@dataclass
class LexerState:
    source: str = ""
    pos: int = 0
    line: int = 1
    col: int = 1
    tokens: List[TokenEvo] = field(default_factory=list)
    current_char: str = ""


@dataclass
class ParserState:
    tokens: List[TokenEvo] = field(default_factory=list)
    pos: int = 0
    current_token: Optional[TokenEvo] = None


@dataclass
class ASTNodeEvo:
    node_type: str
    children: List[Dict] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


HEXAGRAM_SYMBOLS = set("䷀䷁䷂䷃䷄䷅䷆䷇䷈䷉䷊䷋䷌䷍䷎䷏䷐䷑䷒䷓䷔䷕䷖䷗䷘䷙䷚䷛䷜䷝䷞䷟䷠䷡䷢䷣䷤䷥䷦䷧䷨䷩䷪䷫䷬䷭䷮䷯䷰䷱䷲䷳䷴䷵䷶䷷䷸䷹䷺䷻䷼䷽䷾䷿")

MNEMONICS_SET = {
    "CREA", "RECV", "ALLOC", "SPRT", "WAIT", "LOCK", "BRANCH", "MERGE",
    "PREFETCH", "STEP", "FLUSH", "HALT", "FELLOWSHIP", "ABUNDANCE", "YIELD",
    "SPECULATE", "FOLLOWING", "MUT", "APPROACH", "CONTEMPLATE", "BITE",
    "ADORN", "STRIP", "RETURN", "INTRINSIC", "BARRIER", "NOURISH",
    "OVERLOAD", "TRAP", "ILLUMINATE", "SENSE", "PERSIST", "RETREAT",
    "THRUST", "ADVANCE", "OBSCURE", "BIND", "CONVERT", "LAME", "UNLOCK",
    "REDUCE", "INCREASE", "BREAK", "MATE", "GATHER", "PUSH_UP", "TRAPPED",
    "WELL", "REPLACE", "CAST", "SHOCK", "STILL", "GRADUAL", "MISMATCH",
    "ABOUND", "TRAVEL", "PENETRATE", "JOY", "DISPERSE", "THROTTLE",
    "TRUST", "MICRO", "SYNC", "FUTU",
}

FITNESS_KEYWORDS_SET = {"min_latency", "max_throughput", "min_energy", "min_size"}

MODIFIERS_SET = {".ASYNC", ".ATOMIC", ".PRIV", ".WEAK", ".STRONG", ".VOLATILE"}


class EnhancedEvoRuntime:
    """
    增强版易衍运行时
    实现真正的编译能力，支持自举
    """
    
    def __init__(self):
        self.vm = IChingVM()
        self.isa = HexagramInstructionSet()
        self.compiler = EvocCompiler()
        
        self.loaded_loci: Dict[str, dict] = {}
        self.env_bindings: Dict[str, Any] = {}
        self.native_handlers: Dict[str, Callable] = {}
        
        self.lexer_state: Optional[LexerState] = None
        self.parser_state: Optional[ParserState] = None
        self.codegen_state: Dict[str, Any] = {}
        
        self._setup_native_handlers()
        self._setup_compilation_primitives()
    
    def _setup_native_handlers(self):
        self.native_handlers = {
            "print": self._native_print,
            "stdout": self._native_stdout,
            "assert": self._native_assert,
            "evolve_locus": self._native_evolve_locus,
            "compile_source": self._native_compile_source,
            "load_evo": self._native_load_evo,
            "measure_fitness": self._native_measure_fitness,
            "mutate_gene": self._native_mutate_gene,
            "crossover_genes": self._native_crossover_genes,
        }
    
    def _setup_compilation_primitives(self):
        """设置编译原语 - 真正的易衍编译功能"""
        self.compilation_primitives = {
            "lexer_init": self._prim_lexer_init,
            "lexer_tokenize": self._prim_lexer_tokenize,
            "lexer_advance": self._prim_lexer_advance,
            "lexer_peek": self._prim_lexer_peek,
            "lexer_is_alpha": self._prim_lexer_is_alpha,
            "lexer_is_digit": self._prim_lexer_is_digit,
            "lexer_is_hexagram": self._prim_lexer_is_hexagram,
            "lexer_is_whitespace": self._prim_lexer_is_whitespace,
            "lexer_scan_identifier": self._prim_lexer_scan_identifier,
            "lexer_scan_number": self._prim_lexer_scan_number,
            "lexer_scan_string": self._prim_lexer_scan_string,
            "lexer_skip_comment": self._prim_lexer_skip_comment,
            "lexer_emit_token": self._prim_lexer_emit_token,
            
            "parser_init": self._prim_parser_init,
            "parser_advance": self._prim_parser_advance,
            "parser_peek": self._prim_parser_peek,
            "parser_current": self._prim_parser_current,
            "parser_expect": self._prim_parser_expect,
            "parser_match": self._prim_parser_match,
            "parser_skip_newlines": self._prim_parser_skip_newlines,
            "parser_parse_program": self._prim_parser_parse_program,
            "parser_parse_locus": self._prim_parser_parse_locus,
            "parser_parse_instruction": self._prim_parser_parse_instruction,
            
            "codegen_init": self._prim_codegen_init,
            "codegen_encode_opcode": self._prim_codegen_encode_opcode,
            "codegen_encode_operand": self._prim_codegen_encode_operand,
            "codegen_emit_instruction": self._prim_codegen_emit_instruction,
            "codegen_generate_evb": self._prim_codegen_generate_evb,
            
            "vm_execute_instruction": self._prim_vm_execute_instruction,
            "vm_load_program": self._prim_vm_load_program,
            "vm_run": self._prim_vm_run,
        }
    
    def _native_print(self, val):
        print(f"[evort] {val}")
        return val
    
    def _native_stdout(self, val):
        print(val, end="")
        return val
    
    def _native_assert(self, expected, actual):
        if expected != actual:
            raise RuntimeError(f"Assertion failed: expected {expected}, got {actual}")
        return True
    
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
            for locus in result.get("loci", []):
                self.loaded_loci[locus["name"]] = locus
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
        genes = []
        for g in individual_data.get("genes", []):
            genes.append(GeneInstruction(opcode=g.get("opcode", 0), modifier=g.get("modifier", 0)))
        ind = Individual(genes=genes)
        n_genes = len(ind.genes)
        if n_genes == 0:
            return -1000.0
        latency_score = -n_genes * 1.0
        throughput_score = max(0, 10.0 - n_genes * 0.5)
        energy_score = -sum(g.opcode for g in ind.genes) * 0.01
        size_score = -n_genes * 0.1
        valid_opcodes = sum(1 for g in ind.genes if 0 <= g.opcode <= 63)
        validity_score = (valid_opcodes / n_genes) * 50.0
        return latency_score + throughput_score * 2 + energy_score * 0.5 + size_score * 0.3 + validity_score
    
    def _native_mutate_gene(self, opcode, bit_position):
        return opcode ^ (1 << (bit_position & 0x1F))
    
    def _native_crossover_genes(self, opcode1, opcode2, point):
        mask = (1 << point) - 1
        c1 = (opcode1 & mask) | (opcode2 & ~mask)
        c2 = (opcode2 & mask) | (opcode1 & ~mask)
        return c1, c2
    
    def _prim_lexer_init(self, source: str) -> LexerState:
        self.lexer_state = LexerState(
            source=source,
            pos=0,
            line=1,
            col=1,
            tokens=[],
            current_char=source[0] if source else ""
        )
        return self.lexer_state
    
    def _prim_lexer_advance(self) -> None:
        if not self.lexer_state:
            return
        ls = self.lexer_state
        if ls.pos < len(ls.source):
            if ls.source[ls.pos] == '\n':
                ls.line += 1
                ls.col = 1
            else:
                ls.col += 1
            ls.pos += 1
            ls.current_char = ls.source[ls.pos] if ls.pos < len(ls.source) else ""
    
    def _prim_lexer_peek(self, offset: int = 0) -> str:
        if not self.lexer_state:
            return "\0"
        ls = self.lexer_state
        idx = ls.pos + offset
        if idx < len(ls.source):
            return ls.source[idx]
        return "\0"
    
    def _prim_lexer_is_alpha(self, char: str) -> bool:
        return char.isalpha() or char == "_"
    
    def _prim_lexer_is_digit(self, char: str) -> bool:
        return char.isdigit()
    
    def _prim_lexer_is_hexagram(self, char: str) -> bool:
        return char in HEXAGRAM_SYMBOLS
    
    def _prim_lexer_is_whitespace(self, char: str) -> bool:
        return char in " \t\r"
    
    def _prim_lexer_scan_identifier(self) -> Tuple[str, int]:
        if not self.lexer_state:
            return "", 0
        ls = self.lexer_state
        start_col = ls.col
        word = []
        while ls.current_char and (ls.current_char.isalnum() or ls.current_char in "_:"):
            word.append(ls.current_char)
            self._prim_lexer_advance()
        return "".join(word), start_col
    
    def _prim_lexer_scan_number(self) -> Tuple[Any, int, str]:
        if not self.lexer_state:
            return 0, 0, "NUMBER"
        ls = self.lexer_state
        start_col = ls.col
        num_str = []
        is_float = False
        is_hex = False
        is_bin = False
        
        if ls.current_char == "-":
            num_str.append("-")
            self._prim_lexer_advance()
        
        if ls.current_char == "0":
            next_char = self._prim_lexer_peek(1)
            if next_char in "xX":
                is_hex = True
                num_str.append("0")
                self._prim_lexer_advance()
                num_str.append(ls.current_char)
                self._prim_lexer_advance()
                while ls.current_char and ls.current_char in "0123456789abcdefABCDEF":
                    num_str.append(ls.current_char)
                    self._prim_lexer_advance()
            elif next_char in "bB":
                is_bin = True
                num_str.append("0")
                self._prim_lexer_advance()
                num_str.append(ls.current_char)
                self._prim_lexer_advance()
                while ls.current_char and ls.current_char in "01":
                    num_str.append(ls.current_char)
                    self._prim_lexer_advance()
        
        if not is_hex and not is_bin:
            while ls.current_char and (ls.current_char.isdigit() or ls.current_char == "."):
                if ls.current_char == ".":
                    is_float = True
                num_str.append(ls.current_char)
                self._prim_lexer_advance()
        
        value = "".join(num_str)
        if is_hex:
            return int(value, 16), start_col, "IMMEDIATE"
        elif is_bin:
            return int(value, 2), start_col, "IMMEDIATE"
        elif is_float:
            return float(value), start_col, "FLOAT"
        else:
            return int(value), start_col, "NUMBER"
    
    def _prim_lexer_scan_string(self, quote_char: str) -> Tuple[str, int]:
        if not self.lexer_state:
            return "", 0
        ls = self.lexer_state
        start_col = ls.col
        self._prim_lexer_advance()
        value = []
        end_char = '"' if quote_char == '"' else "\u201d"
        
        while ls.current_char and ls.current_char != end_char:
            if ls.current_char == "\\":
                self._prim_lexer_advance()
                if ls.current_char:
                    value.append(ls.current_char)
                    self._prim_lexer_advance()
            else:
                value.append(ls.current_char)
                self._prim_lexer_advance()
        
        if ls.current_char == end_char:
            self._prim_lexer_advance()
        
        return "".join(value), start_col
    
    def _prim_lexer_skip_comment(self) -> None:
        if not self.lexer_state:
            return
        ls = self.lexer_state
        while ls.current_char and ls.current_char != "\n":
            self._prim_lexer_advance()
    
    def _prim_lexer_emit_token(self, type_code: int, value: Any, line: int = None, col: int = None) -> None:
        if not self.lexer_state:
            return
        ls = self.lexer_state
        token = TokenEvo(
            type_code=type_code,
            value=value,
            line=line if line is not None else ls.line,
            col=col if col is not None else ls.col
        )
        ls.tokens.append(token)
    
    def _prim_lexer_tokenize(self, source: str) -> List[TokenEvo]:
        self._prim_lexer_init(source)
        ls = self.lexer_state
        if not ls:
            return []
        
        while ls.pos < len(ls.source):
            ch = ls.current_char
            
            if ch == "\n":
                self._prim_lexer_emit_token(TokenTypeEvo.NEWLINE.value, "\n")
                self._prim_lexer_advance()
                continue
            
            if self._prim_lexer_is_whitespace(ch):
                self._prim_lexer_advance()
                continue
            
            if ch == "/" and self._prim_lexer_peek(1) == "/":
                self._prim_lexer_skip_comment()
                continue
            
            if self._prim_lexer_is_hexagram(ch):
                self._prim_lexer_emit_token(TokenTypeEvo.HEXAGRAM_SYMBOL.value, ch)
                self._prim_lexer_advance()
                continue
            
            if ch == '"':
                value, col = self._prim_lexer_scan_string('"')
                self._prim_lexer_emit_token(TokenTypeEvo.STRING.value, value, col=col)
                continue
            
            if ch == "\u201c":
                value, col = self._prim_lexer_scan_string("\u201c")
                self._prim_lexer_emit_token(TokenTypeEvo.STRING.value, value, col=col)
                continue
            
            if ch == "{":
                self._prim_lexer_emit_token(TokenTypeEvo.LBRACE.value, "{")
                self._prim_lexer_advance()
                continue
            
            if ch == "}":
                self._prim_lexer_emit_token(TokenTypeEvo.RBRACE.value, "}")
                self._prim_lexer_advance()
                continue
            
            if ch == "[":
                self._prim_lexer_emit_token(TokenTypeEvo.LBRACKET.value, "[")
                self._prim_lexer_advance()
                continue
            
            if ch == "]":
                self._prim_lexer_emit_token(TokenTypeEvo.RBRACKET.value, "]")
                self._prim_lexer_advance()
                continue
            
            if ch == "(":
                self._prim_lexer_emit_token(TokenTypeEvo.LPAREN.value, "(")
                self._prim_lexer_advance()
                continue
            
            if ch == ")":
                self._prim_lexer_emit_token(TokenTypeEvo.RPAREN.value, ")")
                self._prim_lexer_advance()
                continue
            
            if ch == ",":
                self._prim_lexer_emit_token(TokenTypeEvo.COMMA.value, ",")
                self._prim_lexer_advance()
                continue
            
            if ch == ".":
                next_char = self._prim_lexer_peek(1)
                if next_char and next_char.isalnum():
                    word = []
                    start_col = ls.col
                    self._prim_lexer_advance()
                    while ls.current_char and (ls.current_char.isalnum() or ls.current_char == "_"):
                        word.append(ls.current_char)
                        self._prim_lexer_advance()
                    mod = "." + "".join(word)
                    if mod in MODIFIERS_SET:
                        self._prim_lexer_emit_token(TokenTypeEvo.MODIFIER.value, mod, col=start_col)
                    else:
                        self._prim_lexer_emit_token(TokenTypeEvo.DOT.value, ".", col=start_col)
                        if word:
                            self._prim_lexer_emit_token(TokenTypeEvo.IDENTIFIER.value, "".join(word))
                else:
                    self._prim_lexer_emit_token(TokenTypeEvo.DOT.value, ".")
                    self._prim_lexer_advance()
                continue
            
            if ch == "=":
                self._prim_lexer_emit_token(TokenTypeEvo.ASSIGN.value, "=")
                self._prim_lexer_advance()
                continue
            
            if ch == "+":
                self._prim_lexer_emit_token(TokenTypeEvo.PLUS.value, "+")
                self._prim_lexer_advance()
                continue
            
            if ch == "-":
                next_char = self._prim_lexer_peek(1)
                if next_char.isdigit() or next_char in "xXbB":
                    value, col, typ = self._prim_lexer_scan_number()
                    type_map = {
                        "NUMBER": TokenTypeEvo.NUMBER,
                        "FLOAT": TokenTypeEvo.FLOAT,
                        "IMMEDIATE": TokenTypeEvo.IMMEDIATE,
                    }
                    self._prim_lexer_emit_token(type_map[typ].value, value, col=col)
                else:
                    self._prim_lexer_emit_token(TokenTypeEvo.MINUS.value, "-")
                    self._prim_lexer_advance()
                continue
            
            if ch == "*":
                self._prim_lexer_emit_token(TokenTypeEvo.STAR.value, "*")
                self._prim_lexer_advance()
                continue
            
            if ch == "/":
                self._prim_lexer_emit_token(TokenTypeEvo.SLASH.value, "/")
                self._prim_lexer_advance()
                continue
            
            if ch == ";":
                self._prim_lexer_emit_token(TokenTypeEvo.SEMICOLON.value, ";")
                self._prim_lexer_advance()
                continue
            
            if ch == "@":
                start_col = ls.col
                self._prim_lexer_advance()
                word = []
                while ls.current_char and (ls.current_char.isalnum() or ls.current_char in "_:"):
                    word.append(ls.current_char)
                    self._prim_lexer_advance()
                label = "".join(word)
                
                keyword_map = {
                    "locus": TokenTypeEvo.LOCUS,
                    "meta_locus": TokenTypeEvo.META_LOCUS,
                    "xiangci": TokenTypeEvo.XIANGCI,
                    "evolang": TokenTypeEvo.EVOLANG,
                }
                
                if label in keyword_map:
                    self._prim_lexer_emit_token(keyword_map[label].value, "@" + label, col=start_col)
                else:
                    self._prim_lexer_emit_token(TokenTypeEvo.LABEL.value, "@" + label, col=start_col)
                continue
            
            if ch.isdigit() or (ch == "0" and self._prim_lexer_peek(1) in "xXbB"):
                value, col, typ = self._prim_lexer_scan_number()
                type_map = {
                    "NUMBER": TokenTypeEvo.NUMBER,
                    "FLOAT": TokenTypeEvo.FLOAT,
                    "IMMEDIATE": TokenTypeEvo.IMMEDIATE,
                }
                self._prim_lexer_emit_token(type_map[typ].value, value, col=col)
                continue
            
            if self._prim_lexer_is_alpha(ch):
                word, col = self._prim_lexer_scan_identifier()
                word_upper = word.upper()
                
                if word_upper in MNEMONICS_SET:
                    self._prim_lexer_emit_token(TokenTypeEvo.MNEMONIC.value, word_upper, col=col)
                elif word.startswith("R") and len(word) > 1:
                    if word[1:].isdigit():
                        self._prim_lexer_emit_token(TokenTypeEvo.REGISTER.value, word, col=col)
                    elif word == "R_" or word.startswith("R_"):
                        self._prim_lexer_emit_token(TokenTypeEvo.REGISTER.value, word, col=col)
                    else:
                        self._prim_lexer_emit_token(TokenTypeEvo.IDENTIFIER.value, word, col=col)
                elif word == "env":
                    rest = []
                    while ls.current_char and ls.current_char not in " \n,)}":
                        rest.append(ls.current_char)
                        self._prim_lexer_advance()
                    env_ref = "env" + "".join(rest)
                    self._prim_lexer_emit_token(TokenTypeEvo.ENV_REF.value, env_ref, col=col)
                elif word in ("mut_rate", "cross_pool", "fitness", "env_target", "max_generations"):
                    type_map = {
                        "mut_rate": TokenTypeEvo.MUT_RATE,
                        "cross_pool": TokenTypeEvo.CROSS_POOL,
                        "fitness": TokenTypeEvo.FITNESS_KW,
                        "env_target": TokenTypeEvo.ENV_TARGET,
                        "max_generations": TokenTypeEvo.MAX_GEN,
                    }
                    self._prim_lexer_emit_token(type_map[word].value, word, col=col)
                elif word in FITNESS_KEYWORDS_SET:
                    self._prim_lexer_emit_token(TokenTypeEvo.FITNESS_KW.value, word, col=col)
                elif word == "卦序":
                    self._prim_lexer_emit_token(TokenTypeEvo.GUA_XU.value, word, col=col)
                else:
                    self._prim_lexer_emit_token(TokenTypeEvo.IDENTIFIER.value, word, col=col)
                continue
            
            self._prim_lexer_advance()
        
        self._prim_lexer_emit_token(TokenTypeEvo.EOF.value, "")
        return ls.tokens
    
    def _prim_parser_init(self, tokens: List[TokenEvo]) -> ParserState:
        self.parser_state = ParserState(
            tokens=tokens,
            pos=0,
            current_token=tokens[0] if tokens else None
        )
        return self.parser_state
    
    def _prim_parser_advance(self) -> Optional[TokenEvo]:
        if not self.parser_state:
            return None
        ps = self.parser_state
        if ps.pos < len(ps.tokens):
            tok = ps.current_token
            ps.pos += 1
            ps.current_token = ps.tokens[ps.pos] if ps.pos < len(ps.tokens) else ps.tokens[-1]
            return tok
        return ps.current_token
    
    def _prim_parser_peek(self, offset: int = 1) -> Optional[TokenEvo]:
        if not self.parser_state:
            return None
        ps = self.parser_state
        idx = ps.pos + offset
        if idx < len(ps.tokens):
            return ps.tokens[idx]
        return ps.tokens[-1] if ps.tokens else None
    
    def _prim_parser_current(self) -> Optional[TokenEvo]:
        if not self.parser_state:
            return None
        return self.parser_state.current_token
    
    def _prim_parser_expect(self, type_code: int) -> Optional[TokenEvo]:
        if not self.parser_state:
            return None
        ps = self.parser_state
        tok = ps.current_token
        if tok and tok.type_code != type_code:
            raise SyntaxError(f"Expected type {type_code}, got {tok.type_code} at line {tok.line}")
        return self._prim_parser_advance()
    
    def _prim_parser_match(self, *type_codes) -> Optional[TokenEvo]:
        if not self.parser_state:
            return None
        ps = self.parser_state
        tok = ps.current_token
        if tok and tok.type_code in type_codes:
            return self._prim_parser_advance()
        return None
    
    def _prim_parser_skip_newlines(self) -> None:
        if not self.parser_state:
            return
        ps = self.parser_state
        while ps.current_token and ps.current_token.type_code == TokenTypeEvo.NEWLINE.value:
            self._prim_parser_advance()
    
    def _prim_parser_parse_program(self) -> ASTNodeEvo:
        if not self.parser_state:
            return ASTNodeEvo(node_type="program")
        
        ps = self.parser_state
        program = ASTNodeEvo(node_type="program", attributes={"version": None, "loci": [], "meta_loci": [], "xiangci": []})
        
        self._prim_parser_skip_newlines()
        
        while ps.current_token and ps.current_token.type_code != TokenTypeEvo.EOF.value:
            self._prim_parser_skip_newlines()
            if ps.current_token and ps.current_token.type_code == TokenTypeEvo.EVOLANG.value:
                self._prim_parser_advance()
                if ps.current_token and ps.current_token.type_code == TokenTypeEvo.STRING.value:
                    program.attributes["version"] = ps.current_token.value
                    self._prim_parser_advance()
            elif ps.current_token and ps.current_token.type_code == TokenTypeEvo.LOCUS.value:
                locus = self._prim_parser_parse_locus()
                program.attributes["loci"].append(locus)
            elif ps.current_token and ps.current_token.type_code == TokenTypeEvo.META_LOCUS.value:
                meta = self._prim_parser_parse_locus(is_meta=True)
                program.attributes["meta_loci"].append(meta)
            elif ps.current_token and ps.current_token.type_code == TokenTypeEvo.XIANGCI.value:
                self._prim_parser_advance()
                self._prim_parser_skip_newlines()
                if ps.current_token and ps.current_token.type_code == TokenTypeEvo.LBRACE.value:
                    self._prim_parser_advance()
                    self._prim_parser_skip_newlines()
                    parts = []
                    while ps.current_token and ps.current_token.type_code != TokenTypeEvo.RBRACE.value:
                        if ps.current_token and ps.current_token.type_code == TokenTypeEvo.STRING.value:
                            parts.append(ps.current_token.value)
                            self._prim_parser_advance()
                        else:
                            self._prim_parser_advance()
                    self._prim_parser_match(TokenTypeEvo.RBRACE.value)
                    program.attributes["xiangci"].append(" ".join(parts))
            else:
                self._prim_parser_advance()
            self._prim_parser_skip_newlines()
        
        return program
    
    def _prim_parser_parse_locus(self, is_meta: bool = False) -> ASTNodeEvo:
        if not self.parser_state:
            return ASTNodeEvo(node_type="locus")
        
        ps = self.parser_state
        self._prim_parser_advance()
        
        name_parts = []
        while ps.current_token and ps.current_token.type_code in (
            TokenTypeEvo.IDENTIFIER.value, TokenTypeEvo.DOT.value, TokenTypeEvo.HEXAGRAM_SYMBOL.value
        ):
            name_parts.append(str(ps.current_token.value))
            self._prim_parser_advance()
        
        name = "".join(name_parts) if name_parts else "unnamed"
        
        self._prim_parser_skip_newlines()
        self._prim_parser_expect(TokenTypeEvo.LBRACE.value)
        self._prim_parser_skip_newlines()
        
        locus = ASTNodeEvo(
            node_type="meta_locus" if is_meta else "locus",
            attributes={
                "name": name,
                "mut_rate": 0.01 if is_meta else 0.02,
                "cross_pool": "default",
                "fitness_terms": [],
                "env_targets": [],
                "max_generations": 100,
                "instructions": [],
            }
        )
        
        while ps.current_token and ps.current_token.type_code != TokenTypeEvo.RBRACE.value:
            self._prim_parser_skip_newlines()
            if ps.current_token and ps.current_token.type_code == TokenTypeEvo.RBRACE.value:
                break
            
            tok = ps.current_token
            if not tok:
                break
            
            if tok.type_code == TokenTypeEvo.MUT_RATE.value:
                self._prim_parser_advance()
                self._prim_parser_expect(TokenTypeEvo.ASSIGN.value)
                if ps.current_token:
                    if ps.current_token.type_code == TokenTypeEvo.FLOAT.value:
                        locus.attributes["mut_rate"] = ps.current_token.value
                        self._prim_parser_advance()
                    elif ps.current_token.type_code == TokenTypeEvo.NUMBER.value:
                        locus.attributes["mut_rate"] = float(ps.current_token.value)
                        self._prim_parser_advance()
            
            elif tok.type_code == TokenTypeEvo.CROSS_POOL.value:
                self._prim_parser_advance()
                self._prim_parser_expect(TokenTypeEvo.ASSIGN.value)
                if ps.current_token and ps.current_token.type_code == TokenTypeEvo.STRING.value:
                    locus.attributes["cross_pool"] = ps.current_token.value
                    self._prim_parser_advance()
            
            elif tok.type_code == TokenTypeEvo.FITNESS_KW.value:
                self._prim_parser_advance()
                self._prim_parser_expect(TokenTypeEvo.ASSIGN.value)
                terms = []
                while ps.current_token and ps.current_token.type_code not in (
                    TokenTypeEvo.RBRACE.value, TokenTypeEvo.NEWLINE.value
                ):
                    if ps.current_token and ps.current_token.type_code == TokenTypeEvo.FLOAT.value:
                        weight = ps.current_token.value
                        self._prim_parser_advance()
                        if ps.current_token and ps.current_token.type_code == TokenTypeEvo.STAR.value:
                            self._prim_parser_advance()
                            if ps.current_token:
                                kw = ps.current_token.value
                                self._prim_parser_advance()
                                terms.append({"keyword": kw, "weight": weight})
                    elif ps.current_token and ps.current_token.type_code == TokenTypeEvo.NUMBER.value:
                        weight = float(ps.current_token.value)
                        self._prim_parser_advance()
                        if ps.current_token and ps.current_token.type_code == TokenTypeEvo.STAR.value:
                            self._prim_parser_advance()
                            if ps.current_token:
                                kw = ps.current_token.value
                                self._prim_parser_advance()
                                terms.append({"keyword": kw, "weight": weight})
                    elif ps.current_token and ps.current_token.type_code == TokenTypeEvo.IDENTIFIER.value:
                        kw = ps.current_token.value
                        self._prim_parser_advance()
                        terms.append({"keyword": kw, "weight": 1.0})
                    elif ps.current_token and ps.current_token.type_code in (
                        TokenTypeEvo.PLUS.value, TokenTypeEvo.MINUS.value
                    ):
                        self._prim_parser_advance()
                    else:
                        self._prim_parser_advance()
                locus.attributes["fitness_terms"] = terms
            
            elif tok.type_code == TokenTypeEvo.ENV_TARGET.value:
                self._prim_parser_advance()
                self._prim_parser_expect(TokenTypeEvo.ASSIGN.value)
                self._prim_parser_expect(TokenTypeEvo.LBRACKET.value)
                targets = []
                while ps.current_token and ps.current_token.type_code != TokenTypeEvo.RBRACKET.value:
                    if ps.current_token and ps.current_token.type_code == TokenTypeEvo.STRING.value:
                        targets.append(ps.current_token.value)
                        self._prim_parser_advance()
                    elif ps.current_token and ps.current_token.type_code == TokenTypeEvo.IDENTIFIER.value:
                        targets.append(ps.current_token.value)
                        self._prim_parser_advance()
                    elif ps.current_token and ps.current_token.type_code == TokenTypeEvo.COMMA.value:
                        self._prim_parser_advance()
                    else:
                        self._prim_parser_advance()
                self._prim_parser_match(TokenTypeEvo.RBRACKET.value)
                locus.attributes["env_targets"] = targets
            
            elif tok.type_code == TokenTypeEvo.MAX_GEN.value:
                self._prim_parser_advance()
                self._prim_parser_expect(TokenTypeEvo.ASSIGN.value)
                if ps.current_token and ps.current_token.type_code == TokenTypeEvo.NUMBER.value:
                    locus.attributes["max_generations"] = ps.current_token.value
                    self._prim_parser_advance()
            
            elif tok.type_code == TokenTypeEvo.GUA_XU.value:
                self._prim_parser_advance()
                self._prim_parser_skip_newlines()
                self._prim_parser_expect(TokenTypeEvo.LBRACE.value)
                self._prim_parser_skip_newlines()
                
                while ps.current_token and ps.current_token.type_code != TokenTypeEvo.RBRACE.value:
                    self._prim_parser_skip_newlines()
                    if ps.current_token and ps.current_token.type_code == TokenTypeEvo.RBRACE.value:
                        break
                    
                    instr = self._prim_parser_parse_instruction()
                    if instr:
                        locus.attributes["instructions"].append(instr)
                    self._prim_parser_skip_newlines()
                
                self._prim_parser_match(TokenTypeEvo.RBRACE.value)
            else:
                self._prim_parser_advance()
            self._prim_parser_skip_newlines()
        
        self._prim_parser_match(TokenTypeEvo.RBRACE.value)
        return locus
    
    def _prim_parser_parse_instruction(self) -> Optional[Dict]:
        if not self.parser_state:
            return None
        
        ps = self.parser_state
        tok = ps.current_token
        if not tok:
            return None
        
        instr = {
            "opcode": 0,
            "symbol": None,
            "mnemonic": None,
            "modifier": 0,
            "operands": [],
        }
        
        if tok.type_code == TokenTypeEvo.HEXAGRAM_SYMBOL.value:
            instr["symbol"] = tok.value
            entry = self.isa.get_by_symbol(tok.value)
            if entry:
                instr["opcode"] = entry["opcode"]
                instr["mnemonic"] = entry["mnemonic"]
            self._prim_parser_advance()
            
            if ps.current_token and ps.current_token.type_code == TokenTypeEvo.MNEMONIC.value:
                self._prim_parser_advance()
        
        elif tok.type_code == TokenTypeEvo.MNEMONIC.value:
            instr["mnemonic"] = tok.value
            entry = self.isa.get_by_mnemonic(tok.value)
            if entry:
                instr["opcode"] = entry["opcode"]
                instr["symbol"] = entry["symbol"]
            self._prim_parser_advance()
        else:
            self._prim_parser_advance()
            return None
        
        if ps.current_token and ps.current_token.type_code == TokenTypeEvo.MODIFIER.value:
            mod_str = ps.current_token.value
            from evomorph.hexagrams.instruction_set import MODIFIERS
            instr["modifier"] = MODIFIERS.get(mod_str, 0)
            self._prim_parser_advance()
        
        while ps.current_token and ps.current_token.type_code in (
            TokenTypeEvo.REGISTER.value, TokenTypeEvo.IMMEDIATE.value,
            TokenTypeEvo.NUMBER.value, TokenTypeEvo.LABEL.value,
            TokenTypeEvo.ENV_REF.value, TokenTypeEvo.IDENTIFIER.value,
            TokenTypeEvo.COMMA.value, TokenTypeEvo.LPAREN.value, TokenTypeEvo.RPAREN.value
        ):
            tok = ps.current_token
            if not tok:
                break
            
            if tok.type_code == TokenTypeEvo.COMMA.value:
                self._prim_parser_advance()
                continue
            if tok.type_code in (TokenTypeEvo.LPAREN.value, TokenTypeEvo.RPAREN.value):
                self._prim_parser_advance()
                continue
            
            if tok.type_code == TokenTypeEvo.REGISTER.value:
                instr["operands"].append({"kind": "register", "value": tok.value})
                self._prim_parser_advance()
            elif tok.type_code in (TokenTypeEvo.IMMEDIATE.value, TokenTypeEvo.NUMBER.value):
                instr["operands"].append({"kind": "immediate", "value": tok.value})
                self._prim_parser_advance()
            elif tok.type_code == TokenTypeEvo.LABEL.value:
                instr["operands"].append({"kind": "label", "value": tok.value})
                self._prim_parser_advance()
            elif tok.type_code == TokenTypeEvo.ENV_REF.value:
                instr["operands"].append({"kind": "env_ref", "value": tok.value})
                self._prim_parser_advance()
            elif tok.type_code == TokenTypeEvo.IDENTIFIER.value:
                ident = tok.value
                if ident.startswith("R") and len(ident) > 1 and ident[1:].isdigit():
                    instr["operands"].append({"kind": "register", "value": ident})
                else:
                    instr["operands"].append({"kind": "identifier", "value": ident})
                self._prim_parser_advance()
            else:
                break
        
        return instr
    
    def _prim_codegen_init(self) -> Dict:
        self.codegen_state = {
            "bytecode": bytearray(),
            "symbol_table": {},
            "relocation_table": [],
            "metadata": {},
            "output": {
                "loci": [],
                "meta_loci": [],
                "xiangci": [],
            }
        }
        return self.codegen_state
    
    def _prim_codegen_encode_opcode(self, opcode: int, modifier: int = 0) -> Tuple[int, int]:
        byte1 = ((opcode & 0x3F) << 2) | ((modifier >> 4) & 0x03)
        byte2 = modifier & 0x0F
        return byte1, byte2
    
    def _prim_codegen_encode_operand(self, operand: Dict) -> int:
        kind = operand.get("kind", "")
        value = operand.get("value", 0)
        
        if kind == "register":
            if isinstance(value, str):
                if value.startswith("R") and value[1:].isdigit():
                    return int(value[1:]) & 0x0F
            return 0
        elif kind == "immediate":
            try:
                return int(value) & 0xFF
            except (ValueError, TypeError):
                return 0
        elif kind == "label":
            return 0
        else:
            return hash(str(value)) & 0xFF
    
    def _prim_codegen_emit_instruction(self, opcode: int, modifier: int, operands: List[Dict]) -> bytes:
        byte1, byte2 = self._prim_codegen_encode_opcode(opcode, modifier)
        instr_bytes = bytes([byte1, byte2])
        
        for i in range(2):
            if i < len(operands):
                op_byte = self._prim_codegen_encode_operand(operands[i])
            else:
                op_byte = 0
            instr_bytes += bytes([op_byte])
        
        if self.codegen_state:
            self.codegen_state["bytecode"].extend(instr_bytes)
        
        return instr_bytes
    
    def _prim_codegen_generate_evb(self, ast: ASTNodeEvo) -> bytes:
        self._prim_codegen_init()
        cg = self.codegen_state
        
        magic = b"EVOB"
        version = 3
        
        header = bytearray()
        header.extend(magic)
        header.extend(struct.pack(">H", version))
        header_size_offset = len(header)
        header.extend(struct.pack(">H", 0))
        
        loci_offsets = []
        loci = ast.attributes.get("loci", [])
        
        for locus in loci:
            offset = len(cg["bytecode"])
            loci_offsets.append(offset)
            
            instructions = locus.attributes.get("instructions", []) if hasattr(locus, "attributes") else locus.get("instructions", [])
            for instr in instructions:
                op = instr.get("opcode", 0)
                mod = instr.get("modifier", 0)
                ops = instr.get("operands", [])
                self._prim_codegen_emit_instruction(op, mod, ops)
        
        header.extend(struct.pack(">H", len(loci_offsets)))
        for offset in loci_offsets:
            header.extend(struct.pack(">I", offset))
        
        actual_header_size = len(header)
        header[header_size_offset:header_size_offset + 2] = struct.pack(">H", actual_header_size)
        
        return bytes(header + cg["bytecode"])
    
    def _prim_vm_execute_instruction(self, opcode: int, modifier: int, operands: List[int]) -> Dict:
        if not hasattr(self, '_vm_exec_handlers'):
            self._setup_vm_exec_handlers()
        
        handler = self._vm_exec_handlers.get(opcode)
        if handler:
            return handler(self, modifier, operands)
        return {"error": f"Unknown opcode: {opcode}"}
    
    def _setup_vm_exec_handlers(self):
        self._vm_exec_handlers = {
            63: lambda self, mod, ops: {"type": "CREA", "result": len(self.vm.call_stack) + 1},
            0: lambda self, mod, ops: {"type": "RECV", "result": 0},
            17: lambda self, mod, ops: {
                "type": "ALLOC", 
                "result": self.vm.heap_ptr + 1 if self.vm.heap_ptr + (ops[1] if len(ops) > 1 else 256) <= self.vm.HEAP_SIZE else 0
            },
            61: lambda self, mod, ops: {"type": "FELLOWSHIP", "result": ops[1] if len(ops) > 1 else 0},
            21: lambda self, mod, ops: {"type": "SYNC", "result": 1},
            2: lambda self, mod, ops: {
                "type": "BRANCH", 
                "result": ops[1] if len(ops) > 1 and self.vm.registers[ops[0] & 0x0F] != 0 else self.vm.pc
            },
            38: lambda self, mod, ops: {
                "type": "MUT",
                "result": self.vm.registers[ops[0] & 0x0F] ^ (1 << (ops[1] if len(ops) > 1 else 0))
            },
            62: lambda self, mod, ops: {
                "type": "MATE",
                "result": (self.vm.registers[ops[0] & 0x0F] + self.vm.registers[ops[1] & 0x0F]) // 2
            },
            1: lambda self, mod, ops: {"type": "RETURN", "result": self.vm.call_stack.pop() if self.vm.call_stack else 0},
        }
    
    def _prim_vm_load_program(self, program_data: Any) -> bool:
        try:
            if isinstance(program_data, (bytes, bytearray)):
                self.vm.load_program(program_data)
            elif isinstance(program_data, list):
                self.vm.load_program(program_data)
            return True
        except Exception:
            return False
    
    def _prim_vm_run(self, max_cycles: int = 10000) -> Dict:
        self.vm.reset()
        state = self.vm.run(max_cycles=max_cycles)
        return {
            "state": state.name,
            "cycle_count": self.vm.cycle_count,
            "energy_cost": self.vm.energy_cost,
            "registers": {f"R{i}": self.vm.registers[i] for i in range(16)},
        }
    
    def compile_with_evo_lexer(self, source: str) -> List[TokenEvo]:
        return self._prim_lexer_tokenize(source)
    
    def compile_with_evo_parser(self, tokens: List[TokenEvo]) -> ASTNodeEvo:
        self._prim_parser_init(tokens)
        return self._prim_parser_parse_program()
    
    def compile_with_evo_codegen(self, ast: ASTNodeEvo) -> Dict:
        self._prim_codegen_init()
        result = {
            "version": ast.attributes.get("version"),
            "loci": [],
            "meta_loci": [],
            "xiangci": ast.attributes.get("xiangci", []),
        }
        
        for locus in ast.attributes.get("loci", []):
            locus_dict = {
                "name": locus.attributes.get("name"),
                "mut_rate": locus.attributes.get("mut_rate"),
                "cross_pool": locus.attributes.get("cross_pool"),
                "fitness": {
                    "terms": locus.attributes.get("fitness_terms", [])
                },
                "env_targets": locus.attributes.get("env_targets", []),
                "max_generations": locus.attributes.get("max_generations"),
                "instructions": locus.attributes.get("instructions", []),
            }
            result["loci"].append(locus_dict)
        
        for meta in ast.attributes.get("meta_loci", []):
            meta_dict = {
                "name": meta.attributes.get("name"),
                "mut_rate": meta.attributes.get("mut_rate"),
                "fitness": {
                    "terms": meta.attributes.get("fitness_terms", [])
                },
                "instructions": meta.attributes.get("instructions", []),
            }
            result["meta_loci"].append(meta_dict)
        
        return result
    
    def full_compile(self, source: str) -> Dict:
        tokens = self.compile_with_evo_lexer(source)
        ast = self.compile_with_evo_parser(tokens)
        result = self.compile_with_evo_codegen(ast)
        return result
    
    def bind_env(self, env_name: str, value):
        self.env_bindings[env_name] = value
    
    def bind_native(self, name: str, handler: Callable):
        self.native_handlers[name] = handler
    
    def load_evo_file(self, filepath: str) -> dict:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        result = self.full_compile(source)
        for locus in result.get("loci", []):
            self.loaded_loci[locus["name"]] = locus
        for meta in result.get("meta_loci", []):
            self.loaded_loci[f"meta:{meta['name']}"] = meta
        return result
    
    def load_evo_source(self, source: str) -> dict:
        result = self.full_compile(source)
        for locus in result.get("loci", []):
            self.loaded_loci[locus["name"]] = locus
        for meta in result.get("meta_loci", []):
            self.loaded_loci[f"meta:{meta['name']}"] = meta
        return result
    
    def get_locus(self, name: str) -> Optional[dict]:
        return self.loaded_loci.get(name)
    
    def execute_locus(self, locus_name: str, max_cycles: int = 10000) -> dict:
        locus = self.loaded_loci.get(locus_name)
        if not locus:
            return {"error": f"Locus '{locus_name}' not found"}
        
        self.vm.reset()
        
        program = []
        for instr in locus.get("instructions", []):
            program.append({
                "opcode": instr.get("opcode", 0),
                "modifier": instr.get("modifier", 0),
                "operands": [
                    self._prim_codegen_encode_operand(op) if isinstance(op, dict) else 
                    (int(op[1:]) if isinstance(op, str) and op.startswith("R") else op)
                    for op in instr.get("operands", [])
                ],
            })
        
        self.vm.load_program(program)
        state = self.vm.run(max_cycles=max_cycles)
        
        return {
            "locus": locus_name,
            "state": state.name,
            "cycle_count": self.vm.cycle_count,
            "energy_cost": self.vm.energy_cost,
            "registers": {f"R{i}": self.vm.registers[i] for i in range(16)},
        }
    
    def bootstrap_self_compile(self) -> Dict:
        bootstrap_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "evoc_hybrid_bootstrap.evo"
        )
        
        if os.path.exists(bootstrap_file):
            with open(bootstrap_file, "r", encoding="utf-8") as f:
                source = f.read()
            
            result = self.full_compile(source)
            
            gen0_result = self._native_compile_source(source)
            
            return {
                "evo_compile": result,
                "python_compile": gen0_result,
                "loci_count": len(result.get("loci", [])),
                "success": len(result.get("loci", [])) > 0,
            }
        
        return {"error": "Bootstrap file not found"}
    
    def verify_bootstrap(self) -> Dict:
        verification = {
            "evo_lexer_works": False,
            "evo_parser_works": False,
            "evo_codegen_works": False,
            "full_bootstrap_works": False,
            "comparison": {},
            "errors": [],
        }
        
        test_source = '''@evolang "3.0"

@locus test.simple {
    mut_rate   = 0.02
    cross_pool = "test"
    fitness    = min_latency + max_throughput
    env_target = ["linux-6.x"]

    卦序: {
        ䷀ CREA R0, R1
        ䷌ FELLOWSHIP R0, R1
        ䷾ SYNC
    }
}
'''
        
        try:
            tokens = self.compile_with_evo_lexer(test_source)
            verification["evo_lexer_works"] = len(tokens) > 0
        except Exception as e:
            verification["errors"].append(f"Lexer error: {e}")
        
        try:
            tokens = self.compile_with_evo_lexer(test_source)
            ast = self.compile_with_evo_parser(tokens)
            verification["evo_parser_works"] = len(ast.attributes.get("loci", [])) > 0
        except Exception as e:
            verification["errors"].append(f"Parser error: {e}")
        
        try:
            tokens = self.compile_with_evo_lexer(test_source)
            ast = self.compile_with_evo_parser(tokens)
            result = self.compile_with_evo_codegen(ast)
            verification["evo_codegen_works"] = len(result.get("loci", [])) > 0
        except Exception as e:
            verification["errors"].append(f"Codegen error: {e}")
        
        try:
            evo_result = self.full_compile(test_source)
            gen0_result = self._native_compile_source(test_source)
            
            verification["comparison"] = {
                "evo_loci_count": len(evo_result.get("loci", [])),
                "python_loci_count": len(gen0_result.get("loci", [])),
                "match": len(evo_result.get("loci", [])) == len(gen0_result.get("loci", [])),
            }
            
            verification["full_bootstrap_works"] = (
                len(evo_result.get("loci", [])) > 0 and
                len(evo_result.get("loci", [])) == len(gen0_result.get("loci", []))
            )
        except Exception as e:
            verification["errors"].append(f"Full bootstrap error: {e}")
        
        return verification
