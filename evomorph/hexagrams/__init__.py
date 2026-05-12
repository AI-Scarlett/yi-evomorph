# =============================================================================
# 六十四卦指令集
# =============================================================================
# .evo 自举等价文件 (运行时自省):
#   hexagram_table.evo   — 完整64条指令定义 + lookup_by_opcode/mnemonic 基因座
#   categories.evo        — 四大分类(元·亨·利·贞) + 按类查询基因座
#   modifiers.evo         — 6个修饰符标志 + encode/decode/combine 基因座
#
# AI 模型只需阅读上述 .evo 文件即可理解 Evomorph 的全部指令能力。
# 本 Python 模块保留用于: VM初始化、进化引擎的变异/交叉操作。
#
# 数据来源: 与 hexagram_table.evo / categories.evo / modifiers.evo 保持同步
# =============================================================================

HEXAGRAM_TABLE = [
    (63, "䷀", "QIAN",       "CREA",        "创生",       "乾元创生，创建新进程/线程"),
    (0,  "䷁", "KUN",        "RECV",        "承纳",       "坤厚载物，接收消息/映射"),
    (17, "䷂", "ZHUN",       "ALLOC",       "初生",       "初生之难，在堆/栈开辟内存"),
    (34, "䷃", "MENG",       "SPRT",        "苗蒙",       "蒙以养正，加载动态库"),
    (23, "䷄", "XU",         "WAIT",        "需待",       "需，须也，等待条件满足"),
    (58, "䷅", "SONG",       "LOCK",        "争讼",       "讼，争也，争抢互斥锁"),
    (2,  "䷆", "SHI",        "BRANCH",      "师众",       "师，众也，条件分支跳转"),
    (16, "䷇", "BI",         "MERGE",       "比辅",       "比，辅也，合并数据流"),
    (55, "䷈", "XIAOXU",     "PREFETCH",    "小畜",       "小畜，寡也，预取缓存行"),
    (59, "䷉", "LV",         "STEP",        "履礼",       "履，礼也，单步执行/迭代"),
    (7,  "䷊", "TAI",        "FLUSH",       "泰通",       "泰，通也，刷新写缓冲"),
    (56, "䷋", "PI",         "HALT",        "否闭",       "否，闭也，暂停/阻塞"),
    (61, "䷌", "TONGREN",    "FELLOWSHIP",  "同人",       "与人同者物必归，同步通信集结"),
    (47, "䷍", "DAYOU",      "ABUNDANCE",   "大有",       "大有，众也，写回/填充数据"),
    (4,  "䷎", "QIANX",      "YIELD",       "谦退",       "谦，退也，释放资源/让出"),
    (8,  "䷏", "YU",         "SPECULATE",   "豫乐",       "豫，乐也，预测分支/投机执行"),
    (25, "䷐", "SUI",        "FOLLOWING",   "随从",       "随，从也，数据流跟踪/复制"),
    (38, "䷑", "GU",         "MUT",         "蛊坏",       "蛊，败坏而后新生，强制变异"),
    (3,  "䷒", "LIN",        "APPROACH",    "临近",       "临，大也，接近临界区"),
    (48, "䷓", "GUAN",       "CONTEMPLATE", "观瞻",       "观，瞻也，观测/性能监视"),
    (41, "䷔", "SHIHE",      "BITE",        "噬嗑",       "噬嗑，食也，断言/校验"),
    (37, "䷕", "BIX",        "ADORN",       "贲饰",       "贲，饰也，格式化/编码转换"),
    (32, "䷖", "BO",         "STRIP",       "剥落",       "剥，落也，剥离/解构数据"),
    (1,  "䷗", "FU",         "RETURN",      "复归",       "复，归也，函数返回/循环回跳"),
    (57, "䷘", "WUWANG",     "INTRINSIC",   "无妄",       "无妄，天命也，内建原子操作"),
    (39, "䷙", "DAXU",       "BARRIER",     "大畜",       "大畜，厚积也，内存屏障"),
    (33, "䷚", "YI",         "NOURISH",     "颐养",       "颐，养也，垃圾回收/内存养护"),
    (30, "䷛", "DAGUO",      "OVERLOAD",    "大过",       "大过，颠也，异常/溢出处理"),
    (18, "䷜", "KAN",        "TRAP",        "坎险",       "坎，陷也，异常捕获/陷阱"),
    (45, "䷝", "LI",         "ILLUMINATE",  "离明",       "离，丽也，日志/调试输出"),
    (28, "䷞", "XIAN",       "SENSE",       "咸感",       "咸，感也，事件监听/感应"),
    (14, "䷟", "HENG",       "PERSIST",     "恒久",       "恒，久也，持久化存储"),
    (60, "䷠", "DUN",        "RETREAT",     "遁退",       "遁，退也，安全退出/回滚"),
    (15, "䷡", "DAZHUANG",   "THRUST",      "大壮",       "大壮，壮也，强制执行/突破"),
    (40, "䷢", "JIN",        "ADVANCE",     "晋进",       "晋，进也，队列推进/流水线"),
    (5,  "䷣", "MINGYI",     "OBSCURE",     "明夷",       "明夷，诛也，加密/混淆"),
    (53, "䷤", "JIAREN",     "BIND",        "家人",       "家人，内也，绑定/闭包"),
    (43, "䷥", "KUI",        "CONVERT",     "睽乖",       "睽，乖也，类型转换"),
    (20, "䷦", "JIANX",      "LAME",        "蹇难",       "蹇，难也，重试/降级"),
    (10, "䷧", "JIE",        "UNLOCK",      "解缓",       "解，缓也，解锁/释放"),
    (35, "䷨", "SUN",        "REDUCE",      "损减",       "损，减也，缩减/压缩"),
    (49, "䷩", "YIX",        "INCREASE",    "益增",       "益，增也，扩展/增强"),
    (31, "䷪", "GUAI",       "BREAK",       "夬决",       "夬，决也，中断/断开"),
    (62, "䷫", "GOU",        "MATE",        "姤遇",       "姤，遇也，基因交叉重组"),
    (24, "䷬", "CUI",        "GATHER",      "萃聚",       "萃，聚也，收集/归约"),
    (6,  "䷭", "SHENG",      "PUSH_UP",     "升推",       "升，推也，入栈/上推"),
    (26, "䷮", "KUNX",       "TRAPPED",     "困穷",       "困，穷也，死锁检测"),
    (22, "䷯", "JING",       "WELL",        "井泉",       "井，通也，阻塞读/管道"),
    (29, "䷰", "GE",         "REPLACE",     "革变",       "革，变也，替换/热更新"),
    (46, "䷱", "DING",       "CAST",        "鼎定",       "鼎，定也，类型铸造/固化"),
    (9,  "䷲", "ZHEN",       "SHOCK",       "震动",       "震，动也，信号/中断触发"),
    (36, "䷳", "GEN",        "STILL",       "艮止",       "艮，止也，暂停/冻结"),
    (52, "䷴", "JIANJ",      "GRADUAL",     "渐进",       "渐，进也，逐步执行"),
    (11, "䷵", "GUIMEI",     "MISMATCH",    "归妹",       "归妹，未当也，类型不匹配"),
    (13, "䷶", "FENG",       "ABOUND",      "丰盛",       "丰，大也，批量操作"),
    (44, "䷷", "LVX",        "TRAVEL",      "旅寄",       "旅，寄也，上下文切换"),
    (54, "䷸", "XUN",        "PENETRATE",   "巽入",       "巽，入也，渗透/穿透访问"),
    (27, "䷹", "DUI",        "JOY",         "兑悦",       "兑，悦也，回调/完成通知"),
    (50, "䷺", "HUAN",       "DISPERSE",    "涣散",       "涣，散也，分散写入"),
    (19, "䷻", "JIEX",       "THROTTLE",    "节度",       "节，度也，节流/流控"),
    (51, "䷼", "ZHONGFU",    "TRUST",       "中孚",       "中孚，信也，签名/验证"),
    (12, "䷽", "XIAOGUO",    "MICRO",       "小过",       "小过，过也，微调/微操作"),
    (21, "䷾", "JIJI",       "SYNC",        "既济",       "既济，事已成而防其乱，屏障同步"),
    (42, "䷿", "WEIJI",      "FUTU",        "未济",       "物不可穷，事未成，异步占位符"),
]

CATEGORY_YUAN = "元·创生"
CATEGORY_HENG = "亨·交互"
CATEGORY_LI = "利·转换"
CATEGORY_ZHEN = "贞·终成"

HEXAGRAM_CATEGORIES = {
    CATEGORY_YUAN: [63, 0, 17, 34, 23, 58, 2, 16, 55, 59, 7, 56, 61, 47, 4, 8],
    CATEGORY_HENG: [25, 38, 3, 48, 41, 37, 32, 1, 57, 39, 33, 30, 18, 45, 28, 14],
    CATEGORY_LI:   [60, 15, 40, 5, 53, 43, 20, 10, 35, 49, 31, 62, 24, 6, 26, 22],
    CATEGORY_ZHEN: [29, 46, 9, 36, 52, 11, 13, 44, 54, 27, 50, 19, 51, 12, 21, 42],
}

MODIFIERS = {
    ".ASYNC":   0b100000,
    ".ATOMIC":  0b010000,
    ".PRIV":    0b001000,
    ".WEAK":    0b000100,
    ".STRONG":  0b000010,
    ".VOLATILE": 0b000001,
}


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
