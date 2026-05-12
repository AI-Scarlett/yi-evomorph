"""
EVB 链接器 — Python 桥接层
=============================
状态: P4 — EVB-native 符号表实现已完成 (symbol.evo: djb2 hash + 符号查找)
      本文件为 Python 运行时桥接，提供跨模块符号解析和 struct 偏移写入
      在 P3 VM 自举完成前无法移除

EVB-native 实现: symbol.evo (djb2 哈希, 符号表查找)
Python 桥接原因: struct.pack_into (偏移写入), Python dict 符号表, 编译器接口
计划移除: P3 VM 自举后，链接器可在 EVB-native runtime 中运行
"""
import os
import struct
from typing import Dict, List, Optional
from evomorph.native.loader.evb_loader import NativeLoader, LocusSegment, EvbHeader


class LinkSymbol:
    def __init__(self, name: str, locus_name: str, offset: int, segment_idx: int):
        self.name = name
        self.locus_name = locus_name
        self.offset = offset
        self.segment_idx = segment_idx


class UnresolvedRef:
    def __init__(self, symbol_name: str, segment_idx: int, offset: int):
        self.symbol_name = symbol_name
        self.segment_idx = segment_idx
        self.offset = offset


class EvoLinker:
    def __init__(self):
        self.loader = NativeLoader()
        self.symbol_table: Dict[str, LinkSymbol] = {}
        self.unresolved: List[UnresolvedRef] = []
        self.segments: List[LocusSegment] = []

    def add_evb(self, filepath: str) -> int:
        result = self.loader.load_evb(filepath)
        if not result:
            return -1
        idx = len(self.segments)
        for name, seg in self.loader.loaded_segments.items():
            self.segments.append(seg)
            self.symbol_table[name] = LinkSymbol(
                name=name, locus_name=name,
                offset=seg.entry_point, segment_idx=idx,
            )
        return idx

    def add_evo_source(self, source: str, name_prefix: str = "") -> int:
        from evomorph.native.bytecode_utils import source_to_segments
        from evomorph.bootstrap.runtime.enhanced_runtime import EnhancedEvoRuntime

        compiler = EnhancedEvoRuntime()
        new_segments = source_to_segments(compiler, source)
        idx = len(self.segments)
        for seg in new_segments:
            self.segments.append(seg)
            self.symbol_table[seg.name] = LinkSymbol(
                name=seg.name, locus_name=seg.name,
                offset=seg.entry_point, segment_idx=idx,
            )
            idx += 1
        return idx

    def resolve_references(self) -> int:
        resolved = 0
        remaining = []
        for ref in self.unresolved:
            if ref.symbol_name in self.symbol_table:
                sym = self.symbol_table[ref.symbol_name]
                seg = self.segments[ref.segment_idx]
                bc = bytearray(seg.bytecode)
                if ref.offset + 4 <= len(bc):
                    struct.pack_into(">I", bc, ref.offset, sym.offset)
                    seg.bytecode = bytes(bc)
                resolved += 1
            else:
                remaining.append(ref)
        self.unresolved = remaining
        return resolved

    def link(self, output_path: str, entry_locus: Optional[str] = None) -> Dict:
        self.resolve_references()
        if entry_locus and entry_locus in self.symbol_table:
            sym = self.symbol_table[entry_locus]
            if sym.segment_idx < len(self.segments):
                self.segments[sym.segment_idx].entry_point = 0
        self.loader.save_evb(output_path, self.segments)
        return {
            "output": output_path,
            "segment_count": len(self.segments),
            "segments": [s.name for s in self.segments],
            "symbols": list(self.symbol_table.keys()),
            "unresolved_count": len(self.unresolved),
            "entry_locus": entry_locus,
        }

    def link_and_run(self, entry_locus: str, max_cycles: int = 100000) -> Dict:
        from evomorph.vm.virtual_machine import IChingVM
        seg = None
        for s in self.segments:
            if s.name == entry_locus:
                seg = s
                break
        if not seg:
            return {"error": f"Entry locus '{entry_locus}' not found"}
        for s in self.segments:
            self.loader.loaded_segments[s.name] = s
        vm = IChingVM()
        return self.loader.execute_segment(entry_locus, vm, max_cycles)
