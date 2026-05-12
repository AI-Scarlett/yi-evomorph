# P12: 所有 class re-export 已移除 (0 外部消费者, 仅 __version__/__lang__ 被 MCP server 使用)
# 原 9 个顶层导入产生 9 条 import chain, 移除后大幅加速包加载
__version__ = "0.0.7"
__lang__ = "易衍·Evomorph"

# 指令集自省 .evo 文件路径 (AI模型可直接阅读这些文件来理解语言能力)
# 无需阅读 Python 代码即可全面了解 Evomorph 的全部指令
_HEXAGRAMS_DIR = __path__[0] + "/hexagrams"
EVO_INTROSPECTION_FILES = {
    "instruction_table": _HEXAGRAMS_DIR + "/hexagram_table.evo",
    "categories": _HEXAGRAMS_DIR + "/categories.evo",
    "modifiers": _HEXAGRAMS_DIR + "/modifiers.evo",
    "xiangci_templates": _HEXAGRAMS_DIR.replace("hexagrams", "sdk") + "/xiangci_templates.evo",
    "xiangci_data": _HEXAGRAMS_DIR.replace("hexagrams", "sdk") + "/xiangci_data.evo",
    "bytecode_utils": _HEXAGRAMS_DIR.replace("hexagrams", "native") + "/bytecode_utils.evo",
    "niche_data": _HEXAGRAMS_DIR.replace("hexagrams", "simulator") + "/niche_data.evo",
    "opcode_cost": _HEXAGRAMS_DIR.replace("hexagrams", "simulator") + "/opcode_cost.evo",
    "evomon": _HEXAGRAMS_DIR.replace("hexagrams", "monitor") + "/evomon.evo",
}
