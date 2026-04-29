from .instruction_set import HEXAGRAM_TABLE, HEXAGRAM_CATEGORIES, MODIFIERS


class HexagramInstructionSet:
    def __init__(self):
        self._by_opcode = {}
        self._by_symbol = {}
        self._by_mnemonic = {}
        self._by_pinyin = {}
        self._load()

    def _load(self):
        for opcode, symbol, pinyin, mnemonic, cn_name, desc in HEXAGRAM_TABLE:
            entry = {
                "opcode": opcode,
                "symbol": symbol,
                "pinyin": pinyin,
                "mnemonic": mnemonic,
                "cn_name": cn_name,
                "description": desc,
                "binary": format(opcode, "06b"),
                "yao": self._opcode_to_yao(opcode),
            }
            self._by_opcode[opcode] = entry
            self._by_symbol[symbol] = entry
            self._by_mnemonic[mnemonic] = entry
            self._by_pinyin[pinyin] = entry

    @staticmethod
    def _opcode_to_yao(opcode):
        bits = format(opcode, "06b")
        yao_lines = []
        for b in bits:
            yao_lines.append("⚊" if b == "1" else "⚋")
        return "".join(yao_lines)

    def get_by_opcode(self, opcode):
        return self._by_opcode.get(opcode)

    def get_by_symbol(self, symbol):
        return self._by_symbol.get(symbol)

    def get_by_mnemonic(self, mnemonic):
        return self._by_mnemonic.get(mnemonic.upper())

    def get_by_pinyin(self, pinyin):
        return self._by_pinyin.get(pinyin.upper())

    def lookup(self, key):
        if isinstance(key, int):
            return self.get_by_opcode(key)
        if key in self._by_symbol:
            return self._by_symbol[key]
        if key.upper() in self._by_mnemonic:
            return self._by_mnemonic[key.upper()]
        if key.upper() in self._by_pinyin:
            return self._by_pinyin[key.upper()]
        return None

    def all_instructions(self):
        return list(self._by_opcode.values())

    def instructions_by_category(self, category):
        opcodes = HEXAGRAM_CATEGORIES.get(category, [])
        return [self._by_opcode[op] for op in opcodes if op in self._by_opcode]

    def encode_instruction(self, opcode, modifier=0):
        byte1 = (opcode << 2) | ((modifier >> 4) & 0x03)
        byte2 = modifier & 0x0F
        return bytes([byte1, byte2])

    def decode_instruction(self, data):
        if len(data) < 2:
            return None
        byte1, byte2 = data[0], data[1]
        opcode = (byte1 >> 2) & 0x3F
        modifier = ((byte1 & 0x03) << 4) | (byte2 & 0x0F)
        return opcode, modifier

    def mutate_opcode(self, opcode, bit_position):
        if bit_position < 0 or bit_position > 5:
            return opcode
        return opcode ^ (1 << bit_position)

    def crossover_opcodes(self, opcode1, opcode2, crossover_point):
        mask_low = (1 << crossover_point) - 1
        mask_high = 0x3F ^ mask_low
        child1 = (opcode1 & mask_high) | (opcode2 & mask_low)
        child2 = (opcode2 & mask_high) | (opcode1 & mask_low)
        return child1, child2

    def neighbors(self, opcode, hamming_distance=1):
        result = []
        for i in range(6):
            neighbor = self.mutate_opcode(opcode, i)
            if neighbor != opcode:
                result.append(neighbor)
        return result
