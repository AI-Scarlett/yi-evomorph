from .lexer import Lexer, TokenType
from evomorph.hexagrams import HexagramInstructionSet


class ASTNode:
    pass


class ProgramNode(ASTNode):
    def __init__(self):
        self.version = None
        self.loci = []
        self.xiangci_blocks = []
        self.meta_loci = []


class LocusNode(ASTNode):
    def __init__(self, name):
        self.name = name
        self.mut_rate = 0.02
        self.cross_pool = "default"
        self.fitness_expr = None
        self.env_targets = []
        self.max_generations = 100
        self.instructions = []


class MetaLocusNode(ASTNode):
    def __init__(self, name):
        self.name = name
        self.mut_rate = 0.01
        self.fitness_expr = None
        self.instructions = []


class XiangciNode(ASTNode):
    def __init__(self):
        self.text = ""


class InstructionNode(ASTNode):
    def __init__(self):
        self.opcode = None
        self.symbol = None
        self.mnemonic = None
        self.modifier = 0
        self.operands = []
        self.raw_text = ""


class FitnessExpr(ASTNode):
    def __init__(self):
        self.terms = []


class FitnessTerm(ASTNode):
    def __init__(self, keyword, weight=1.0):
        self.keyword = keyword
        self.weight = weight


class OperandNode(ASTNode):
    def __init__(self, kind, value):
        self.kind = kind
        self.value = value


class Parser:
    def __init__(self, tokens, instruction_set=None):
        self.tokens = tokens
        self.pos = 0
        self.isa = instruction_set or HexagramInstructionSet()

    def current(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]

    def peek(self, offset=1):
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def advance(self):
        tok = self.current()
        self.pos += 1
        return tok

    def expect(self, type_):
        tok = self.current()
        if tok.type != type_:
            raise SyntaxError(f"Expected {type_.name}, got {tok.type.name} ({tok.value!r}) at line {tok.line}")
        return self.advance()

    def match(self, *types):
        if self.current().type in types:
            return self.advance()
        return None

    def skip_newlines(self):
        while self.current().type == TokenType.NEWLINE:
            self.advance()

    def parse(self):
        program = ProgramNode()
        self.skip_newlines()
        while self.current().type != TokenType.EOF:
            self.skip_newlines()
            if self.current().type == TokenType.EOF:
                break
            if self.current().type == TokenType.EVOLANG:
                program.version = self._parse_evolang()
            elif self.current().type == TokenType.LOCUS:
                locus = self._parse_locus()
                program.loci.append(locus)
            elif self.current().type == TokenType.META_LOCUS:
                meta = self._parse_meta_locus()
                program.meta_loci.append(meta)
            elif self.current().type == TokenType.XIANGCI:
                xiangci = self._parse_xiangci()
                program.xiangci_blocks.append(xiangci)
            else:
                self.advance()
            self.skip_newlines()
        return program

    def _parse_evolang(self):
        self.expect(TokenType.EVOLANG)
        tok = self.expect(TokenType.STRING)
        return tok.value

    def _parse_locus(self):
        self.expect(TokenType.LOCUS)
        name = self._parse_locus_name()
        self.skip_newlines()
        self.expect(TokenType.LBRACE)
        self.skip_newlines()
        locus = LocusNode(name)
        while self.current().type != TokenType.RBRACE:
            self.skip_newlines()
            if self.current().type == TokenType.RBRACE:
                break
            if self.current().type == TokenType.MUT_RATE:
                locus.mut_rate = self._parse_mut_rate()
            elif self.current().type == TokenType.CROSS_POOL:
                locus.cross_pool = self._parse_cross_pool()
            elif self.current().type == TokenType.FITNESS_KW:
                locus.fitness_expr = self._parse_fitness()
            elif self.current().type == TokenType.ENV_TARGET:
                locus.env_targets = self._parse_env_target()
            elif self.current().type == TokenType.MAX_GEN:
                locus.max_generations = self._parse_max_gen()
            elif self.current().type == TokenType.GUA_XU:
                locus.instructions = self._parse_gua_xu()
            else:
                self.advance()
            self.skip_newlines()
        self.expect(TokenType.RBRACE)
        return locus

    def _parse_meta_locus(self):
        self.expect(TokenType.META_LOCUS)
        name = self._parse_locus_name()
        self.skip_newlines()
        self.expect(TokenType.LBRACE)
        self.skip_newlines()
        meta = MetaLocusNode(name)
        while self.current().type != TokenType.RBRACE:
            self.skip_newlines()
            if self.current().type == TokenType.RBRACE:
                break
            if self.current().type == TokenType.MUT_RATE:
                meta.mut_rate = self._parse_mut_rate()
            elif self.current().type == TokenType.FITNESS_KW:
                meta.fitness_expr = self._parse_fitness()
            elif self.current().type == TokenType.GUA_XU:
                meta.instructions = self._parse_gua_xu()
            else:
                self.advance()
            self.skip_newlines()
        self.expect(TokenType.RBRACE)
        return meta

    def _parse_xiangci(self):
        self.expect(TokenType.XIANGCI)
        self.skip_newlines()
        self.expect(TokenType.LBRACE)
        self.skip_newlines()
        xiangci = XiangciNode()
        parts = []
        while self.current().type != TokenType.RBRACE:
            if self.current().type == TokenType.STRING:
                parts.append(self.advance().value)
            elif self.current().type == TokenType.NEWLINE:
                self.advance()
            else:
                parts.append(str(self.advance().value))
        self.expect(TokenType.RBRACE)
        xiangci.text = " ".join(parts).strip()
        return xiangci

    def _parse_locus_name(self):
        parts = []
        while self.current().type in (TokenType.IDENTIFIER, TokenType.DOT, TokenType.HEXAGRAM_SYMBOL):
            parts.append(str(self.advance().value))
        return "".join(parts) if parts else "unnamed"

    def _parse_mut_rate(self):
        self.expect(TokenType.MUT_RATE)
        self.expect(TokenType.ASSIGN)
        tok = self.current()
        if tok.type == TokenType.FLOAT:
            self.advance()
            return tok.value
        elif tok.type == TokenType.NUMBER:
            self.advance()
            return float(tok.value)
        return 0.02

    def _parse_cross_pool(self):
        self.expect(TokenType.CROSS_POOL)
        self.expect(TokenType.ASSIGN)
        tok = self.expect(TokenType.STRING)
        return tok.value

    def _parse_fitness(self):
        self.expect(TokenType.FITNESS_KW)
        self.expect(TokenType.ASSIGN)
        expr = FitnessExpr()
        term = self._parse_fitness_term()
        if term:
            expr.terms.append(term)
        while self.current().type in (TokenType.PLUS, TokenType.MINUS, TokenType.STAR):
            op = self.advance()
            term = self._parse_fitness_term()
            if term:
                if op.type == TokenType.MINUS:
                    term.weight = -abs(term.weight)
                expr.terms.append(term)
        return expr

    def _parse_fitness_term(self):
        if self.current().type == TokenType.FLOAT:
            weight = self.advance().value
            if self.current().type == TokenType.STAR:
                self.advance()
            kw = self.advance().value
            return FitnessTerm(kw, weight)
        elif self.current().type == TokenType.NUMBER:
            weight = float(self.advance().value)
            if self.current().type == TokenType.STAR:
                self.advance()
            kw = self.advance().value
            return FitnessTerm(kw, weight)
        elif self.current().type == TokenType.IDENTIFIER:
            kw = self.advance().value
            return FitnessTerm(kw, 1.0)
        return None

    def _parse_env_target(self):
        self.expect(TokenType.ENV_TARGET)
        self.expect(TokenType.ASSIGN)
        self.expect(TokenType.LBRACKET)
        targets = []
        while self.current().type != TokenType.RBRACKET:
            if self.current().type == TokenType.STRING:
                targets.append(self.advance().value)
            elif self.current().type == TokenType.IDENTIFIER:
                targets.append(self.advance().value)
            elif self.current().type == TokenType.COMMA:
                self.advance()
            else:
                self.advance()
        self.expect(TokenType.RBRACKET)
        return targets

    def _parse_max_gen(self):
        self.expect(TokenType.MAX_GEN)
        self.expect(TokenType.ASSIGN)
        tok = self.expect(TokenType.NUMBER)
        return tok.value

    def _parse_gua_xu(self):
        self.expect(TokenType.GUA_XU)
        if self.current().type == TokenType.LBRACE:
            self.expect(TokenType.LBRACE)
        else:
            self.skip_newlines()
            self.expect(TokenType.LBRACE)
        self.skip_newlines()
        instructions = []
        while self.current().type != TokenType.RBRACE:
            self.skip_newlines()
            if self.current().type == TokenType.RBRACE:
                break
            instr = self._parse_instruction()
            if instr:
                instructions.append(instr)
            self.skip_newlines()
        self.expect(TokenType.RBRACE)
        return instructions

    def _parse_instruction(self):
        instr = InstructionNode()
        if self.current().type == TokenType.HEXAGRAM_SYMBOL:
            instr.symbol = self.advance().value
            entry = self.isa.get_by_symbol(instr.symbol)
            if entry:
                instr.opcode = entry["opcode"]
                instr.mnemonic = entry["mnemonic"]
            if self.current().type == TokenType.MNEMONIC:
                self.advance()
        elif self.current().type == TokenType.MNEMONIC:
            instr.mnemonic = self.advance().value
            entry = self.isa.get_by_mnemonic(instr.mnemonic)
            if entry:
                instr.opcode = entry["opcode"]
                instr.symbol = entry["symbol"]
        elif self.current().type == TokenType.PINYIN:
            pinyin = self.advance().value
            entry = self.isa.get_by_pinyin(pinyin)
            if entry:
                instr.opcode = entry["opcode"]
                instr.mnemonic = entry["mnemonic"]
                instr.symbol = entry["symbol"]
        else:
            self.advance()
            return None

        if self.current().type == TokenType.MODIFIER:
            mod = self.advance().value
            from evomorph.hexagrams.instruction_set import MODIFIERS as MOD_MAP
            instr.modifier = MOD_MAP.get(mod, 0)

        while self.current().type in (TokenType.REGISTER, TokenType.IMMEDIATE,
                                       TokenType.NUMBER, TokenType.LABEL,
                                       TokenType.ENV_REF, TokenType.IDENTIFIER,
                                       TokenType.COMMA, TokenType.LPAREN, TokenType.RPAREN):
            if self.current().type == TokenType.COMMA:
                self.advance()
                continue
            if self.current().type == TokenType.LPAREN:
                self.advance()
                continue
            if self.current().type == TokenType.RPAREN:
                self.advance()
                continue
            if self.current().type == TokenType.REGISTER:
                reg_name = self.advance().value
                instr.operands.append(OperandNode("register", reg_name))
            elif self.current().type in (TokenType.IMMEDIATE, TokenType.NUMBER):
                val = self.advance().value
                instr.operands.append(OperandNode("immediate", val))
            elif self.current().type == TokenType.LABEL:
                label = self.advance().value
                instr.operands.append(OperandNode("label", label))
            elif self.current().type == TokenType.ENV_REF:
                ref = self.advance().value
                instr.operands.append(OperandNode("env_ref", ref))
            elif self.current().type == TokenType.IDENTIFIER:
                ident = self.advance().value
                instr.operands.append(OperandNode("identifier", ident))
            else:
                break

        return instr
