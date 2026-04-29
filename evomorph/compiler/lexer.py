import re
from enum import Enum, auto


class TokenType(Enum):
    EVOLANG = auto()
    LOCUS = auto()
    META_LOCUS = auto()
    XIANGCI = auto()
    GUA_XU = auto()
    HEXAGRAM_SYMBOL = auto()
    MNEMONIC = auto()
    PINYIN = auto()
    REGISTER = auto()
    IMMEDIATE = auto()
    LABEL = auto()
    ENV_REF = auto()
    MODIFIER = auto()
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()
    FLOAT = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    DOT = auto()
    ASSIGN = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    SEMICOLON = auto()
    NEWLINE = auto()
    EOF = auto()
    FITNESS_KW = auto()
    CROSS_POOL = auto()
    MUT_RATE = auto()
    ENV_TARGET = auto()
    MAX_GEN = auto()
    COMMENT = auto()


HEXAGRAM_SYMBOLS = set("䷀䷁䷂䷃䷄䷅䷆䷇䷈䷉䷊䷋䷌䷍䷎䷏䷐䷑䷒䷓䷔䷕䷖䷗䷘䷙䷚䷛䷜䷝䷞䷟䷠䷡䷢䷣䷤䷥䷦䷧䷨䷩䷪䷫䷬䷭䷮䷯䷰䷱䷲䷳䷴䷵䷶䷷䷸䷹䷺䷻䷼䷽䷾䷿")

MNEMONICS = {
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

PINYIN_NAMES = {
    "QIAN", "KUN", "ZHUN", "MENG", "XU", "SONG", "SHI", "BI",
    "XIAOXU", "LV", "TAI", "PI", "TONGREN", "DAYOU", "QIAN", "YU",
    "SUI", "GU", "LIN", "GUAN", "SHIHE", "BI", "BO", "FU",
    "WUWANG", "DAXU", "YI", "DAGUO", "KAN", "LI", "XIAN", "HENG",
    "DUN", "DAGUO", "JIN", "MINGYI", "JIAREN", "KUI", "JIAN", "JIE",
    "SUN", "YI", "GUAI", "GOU", "CUI", "SHENG", "KUN", "JING",
    "GE", "DING", "ZHEN", "GEN", "JIAN", "GUIMEI", "FENG", "LV",
    "XUN", "DUI", "HUAN", "JIE", "ZHONGFU", "XIAOGUO", "JIJI", "WEIJI",
}

FITNESS_KEYWORDS = {"min_latency", "max_throughput", "min_energy", "min_size"}

MODIFIERS = {".ASYNC", ".ATOMIC", ".PRIV", ".WEAK", ".STRONG", ".VOLATILE"}


class Token:
    __slots__ = ("type", "value", "line", "col")

    def __init__(self, type_, value, line=0, col=0):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:{self.col})"


class Lexer:
    def __init__(self, source):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []

    def tokenize(self):
        self.tokens = []
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch == "\n":
                self.tokens.append(Token(TokenType.NEWLINE, "\n", self.line, self.col))
                self._advance()
                self.line += 1
                self.col = 1
                continue
            if ch in " \t\r":
                self._advance()
                continue
            if ch == "/" and self._peek(1) == "/":
                self._skip_comment()
                continue
            if ch in HEXAGRAM_SYMBOLS:
                self.tokens.append(Token(TokenType.HEXAGRAM_SYMBOL, ch, self.line, self.col))
                self._advance()
                continue
            if ch == '"':
                self._read_string()
                continue
            if ch == "\u201c":
                self._read_chinese_string()
                continue
            if ch == "{":
                self.tokens.append(Token(TokenType.LBRACE, "{", self.line, self.col))
                self._advance()
                continue
            if ch == "}":
                self.tokens.append(Token(TokenType.RBRACE, "}", self.line, self.col))
                self._advance()
                continue
            if ch == "[":
                self.tokens.append(Token(TokenType.LBRACKET, "[", self.line, self.col))
                self._advance()
                continue
            if ch == "]":
                self.tokens.append(Token(TokenType.RBRACKET, "]", self.line, self.col))
                self._advance()
                continue
            if ch == "(":
                self.tokens.append(Token(TokenType.LPAREN, "(", self.line, self.col))
                self._advance()
                continue
            if ch == ")":
                self.tokens.append(Token(TokenType.RPAREN, ")", self.line, self.col))
                self._advance()
                continue
            if ch == ",":
                self.tokens.append(Token(TokenType.COMMA, ",", self.line, self.col))
                self._advance()
                continue
            if ch == ".":
                self._read_dot_or_modifier()
                continue
            if ch == "=":
                self.tokens.append(Token(TokenType.ASSIGN, "=", self.line, self.col))
                self._advance()
                continue
            if ch == "+":
                self.tokens.append(Token(TokenType.PLUS, "+", self.line, self.col))
                self._advance()
                continue
            if ch == "-":
                if self._peek(1).isdigit() or self._peek(1) in ("x", "X", "b", "B"):
                    self._read_number()
                else:
                    self.tokens.append(Token(TokenType.MINUS, "-", self.line, self.col))
                    self._advance()
                continue
            if ch == "*":
                self.tokens.append(Token(TokenType.STAR, "*", self.line, self.col))
                self._advance()
                continue
            if ch == "/":
                self.tokens.append(Token(TokenType.SLASH, "/", self.line, self.col))
                self._advance()
                continue
            if ch == ";":
                self.tokens.append(Token(TokenType.SEMICOLON, ";", self.line, self.col))
                self._advance()
                continue
            if ch == "@":
                self._read_at_label()
                continue
            if ch.isdigit() or (ch == "0" and self._peek(1) in ("x", "X", "b", "B")):
                self._read_number()
                continue
            if ch.isalpha() or ch == "_":
                self._read_identifier()
                continue
            self._advance()

        self.tokens.append(Token(TokenType.EOF, "", self.line, self.col))
        return self.tokens

    def _advance(self):
        self.pos += 1
        self.col += 1

    def _peek(self, offset=0):
        idx = self.pos + offset
        if idx < len(self.source):
            return self.source[idx]
        return "\0"

    def _skip_comment(self):
        while self.pos < len(self.source) and self.source[self.pos] != "\n":
            self._advance()

    def _read_string(self):
        start_line, start_col = self.line, self.col
        self._advance()
        value = []
        while self.pos < len(self.source) and self.source[self.pos] != '"':
            if self.source[self.pos] == "\\":
                self._advance()
                if self.pos < len(self.source):
                    value.append(self.source[self.pos])
                    self._advance()
            else:
                value.append(self.source[self.pos])
                self._advance()
        if self.pos < len(self.source):
            self._advance()
        self.tokens.append(Token(TokenType.STRING, "".join(value), start_line, start_col))

    def _read_chinese_string(self):
        start_line, start_col = self.line, self.col
        self._advance()
        value = []
        end_char = "\u201d"
        while self.pos < len(self.source) and self.source[self.pos] != end_char:
            value.append(self.source[self.pos])
            self._advance()
        if self.pos < len(self.source):
            self._advance()
        self.tokens.append(Token(TokenType.STRING, "".join(value), start_line, start_col))

    def _read_dot_or_modifier(self):
        start_col = self.col
        self._advance()
        word = []
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == "_"):
            word.append(self.source[self.pos])
            self._advance()
        mod = "." + "".join(word)
        if mod in MODIFIERS:
            self.tokens.append(Token(TokenType.MODIFIER, mod, self.line, start_col))
        else:
            self.tokens.append(Token(TokenType.DOT, ".", self.line, start_col))
            if word:
                self.tokens.append(Token(TokenType.IDENTIFIER, "".join(word), self.line, start_col + 1))

    def _read_at_label(self):
        start_line, start_col = self.line, self.col
        self._advance()
        word = []
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] in ("_", "::")):
            word.append(self.source[self.pos])
            self._advance()
        label = "".join(word)
        if label == "locus":
            self.tokens.append(Token(TokenType.LOCUS, "@locus", start_line, start_col))
        elif label == "meta_locus":
            self.tokens.append(Token(TokenType.META_LOCUS, "@meta_locus", start_line, start_col))
        elif label == "xiangci":
            self.tokens.append(Token(TokenType.XIANGCI, "@xiangci", start_line, start_col))
        elif label == "evolang":
            self.tokens.append(Token(TokenType.EVOLANG, "@evolang", start_line, start_col))
        else:
            self.tokens.append(Token(TokenType.LABEL, "@" + label, start_line, start_col))

    def _read_number(self):
        start_line, start_col = self.line, self.col
        num_str = []
        is_float = False
        if self.source[self.pos] == "-":
            num_str.append("-")
            self._advance()
        if self.source[self.pos] == "0" and self._peek(1) in ("x", "X"):
            num_str.append("0x")
            self._advance()
            self._advance()
            while self.pos < len(self.source) and self.source[self.pos] in "0123456789abcdefABCDEF":
                num_str.append(self.source[self.pos])
                self._advance()
            self.tokens.append(Token(TokenType.IMMEDIATE, int("".join(num_str), 16), start_line, start_col))
            return
        if self.source[self.pos] == "0" and self._peek(1) in ("b", "B"):
            num_str.append("0b")
            self._advance()
            self._advance()
            while self.pos < len(self.source) and self.source[self.pos] in "01":
                num_str.append(self.source[self.pos])
                self._advance()
            self.tokens.append(Token(TokenType.IMMEDIATE, int("".join(num_str), 2), start_line, start_col))
            return
        while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == "."):
            if self.source[self.pos] == ".":
                is_float = True
            num_str.append(self.source[self.pos])
            self._advance()
        value = "".join(num_str)
        if is_float:
            self.tokens.append(Token(TokenType.FLOAT, float(value), start_line, start_col))
        else:
            self.tokens.append(Token(TokenType.NUMBER, int(value), start_line, start_col))

    def _read_identifier(self):
        start_line, start_col = self.line, self.col
        word = []
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] in ("_", "::")):
            word.append(self.source[self.pos])
            self._advance()
        value = "".join(word)
        if value.upper() in MNEMONICS:
            self.tokens.append(Token(TokenType.MNEMONIC, value.upper(), start_line, start_col))
        elif value.upper() in PINYIN_NAMES:
            self.tokens.append(Token(TokenType.PINYIN, value.upper(), start_line, start_col))
        elif value.startswith("R_"):
            self.tokens.append(Token(TokenType.REGISTER, value, start_line, start_col))
        elif value.startswith("R") and len(value) > 1 and value[1:].isdigit():
            self.tokens.append(Token(TokenType.REGISTER, value, start_line, start_col))
        elif value == "env":
            rest = []
            while self.pos < len(self.source) and self.source[self.pos] != " " and self.source[self.pos] not in ("\n", ",", ")", "}"):
                rest.append(self.source[self.pos])
                self._advance()
            self.tokens.append(Token(TokenType.ENV_REF, "env" + "".join(rest), start_line, start_col))
        elif value in ("mut_rate", "cross_pool", "fitness", "env_target", "max_generations"):
            type_map = {
                "mut_rate": TokenType.MUT_RATE,
                "cross_pool": TokenType.CROSS_POOL,
                "fitness": TokenType.FITNESS_KW,
                "env_target": TokenType.ENV_TARGET,
                "max_generations": TokenType.MAX_GEN,
            }
            self.tokens.append(Token(type_map[value], value, start_line, start_col))
        elif value == "卦序":
            self.tokens.append(Token(TokenType.GUA_XU, "卦序", start_line, start_col))
        else:
            self.tokens.append(Token(TokenType.IDENTIFIER, value, start_line, start_col))
