# IChing EVB 自举等价文件:
#   niche_data.evo    — 5平台性能配置 + evaluate基因座
#   opcode_cost.evo   — 64指令成本映射 + 基础成本表
from .niche import PlatformSimNiche, PlatformProfile, PLATFORM_PROFILES

__all__ = ["PlatformSimNiche", "PlatformProfile", "PLATFORM_PROFILES"]
