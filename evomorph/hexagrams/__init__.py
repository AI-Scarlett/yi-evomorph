# =============================================================================
# 六十四卦指令集
# =============================================================================
# IChing EVB 自举等价文件 (运行时自省):
#   hexagram_table.evo   — 完整64条指令定义 + lookup_by_opcode/mnemonic 基因座
#   categories.evo        — 四大分类(元·亨·利·贞) + 按类查询基因座
#   modifiers.evo         — 6个修饰符标志 + encode/decode/combine 基因座
#
# AI 模型只需阅读上述 .evo 文件即可理解 Evomorph 的全部指令能力。
# 本 Python 模块保留用于: VM初始化、进化引擎的变异/交叉操作。
# =============================================================================

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

    def export_evo_heap_data(self) -> bytes:
        """导出指令表为 VM heap 可加载的二进制格式。

        格式: 每指令条目 [opcode(u8) | category(u8) | mnemonic_len(u8) | mnemonic(ascii) | cn_name_len(u8) | cn_name(utf8) | desc_len(u8) | desc(utf8)]
        用于 hexagram_table.evo 中 lookup_by_opcode 基因座的运行时自省查询。
        """
        import struct
        buf = bytearray()
        for opcode in range(64):
            entry = self._by_opcode.get(opcode)
            if not entry:
                buf.extend(struct.pack("BBB", opcode, 0xff, 0))
                buf.extend(struct.pack("B", 0))
                buf.extend(struct.pack("B", 0))
                continue
            mnemonic = entry["mnemonic"].encode("ascii")
            cn_name = entry["cn_name"].encode("utf-8")
            desc = entry["description"].encode("utf-8")
            buf.append(opcode)
            buf.append(self._get_category_index(opcode))
            buf.append(len(mnemonic))
            buf.extend(mnemonic)
            buf.append(len(cn_name))
            buf.extend(cn_name)
            buf.append(len(desc))
            buf.extend(desc)
        return bytes(buf)

    def _get_category_index(self, opcode: int) -> int:
        for idx, (cat_name, ops) in enumerate(HEXAGRAM_CATEGORIES.items()):
            if opcode in ops:
                return idx
        return 0xff

    @property
    def evo_files(self):
        """返回对应的 .evo 自举文件路径列表，供 AI 模型/自省系统使用。"""
        import os
        base = os.path.dirname(os.path.abspath(__file__))
        return {
            "table": os.path.join(base, "hexagram_table.evo"),
            "categories": os.path.join(base, "categories.evo"),
            "modifiers": os.path.join(base, "modifiers.evo"),
        }
