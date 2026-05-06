from evomorph.hexagrams import HexagramInstructionSet
from evomorph.compiler import EvocCompiler, IChingEvocCompiler
from evomorph.vm.virtual_machine import IChingVM
from evomorph.evolution.engine import EvolutionEngine
from evomorph.simulator.niche import PlatformSimNiche
from evomorph.debugger.yaojing import YaoJingDebugger
from evomorph.monitor.evomon import EvoMon
from evomorph.hub.repository import EvoHub
from evomorph.sdk.xiangci import XiangciSDK

__version__ = "0.0.6"
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
