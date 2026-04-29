import struct
import os
from typing import Dict, List, Optional, Tuple
from evomorph.vm.virtual_machine import IChingVM, VMState
from evomorph.hexagrams import HexagramInstructionSet


EVB_MAGIC = b"EVOB"
EVB_VERSION = 3


class EvbHeader:
    def __init__(self):
        self.magic = EVB_MAGIC
        self.version = EVB_VERSION
        self.header_size = 0
        self.locus_count = 0
        self.locus_offsets: List[int] = []
        self.locus_names: List[str] = []
        self.metadata: Dict[str, str] = {}

    def to_bytes(self) -> bytes:
        data = bytearray()
        data.extend(self.magic)
        data.extend(struct.pack(">H", self.version))
        header_start = len(data)
        data.extend(struct.pack(">H", 0))
        data.extend(struct.pack(">H", self.locus_count))
        for offset in self.locus_offsets:
            data.extend(struct.pack(">I", offset))
        if self.metadata:
            meta_bytes = str(self.metadata).encode("utf-8")
            data.extend(struct.pack(">H", len(meta_bytes)))
            data.extend(meta_bytes)
        self.header_size = len(data) + 2
        struct.pack_into(">H", data, header_start, self.header_size)
        return bytes(data)

    @classmethod
    def from_bytes(cls, data: bytes) -> Optional["EvbHeader"]:
        if len(data) < 8:
            return None
        header = cls()
        header.magic = data[:4]
        if header.magic != EVB_MAGIC:
            return None
        header.version = struct.unpack(">H", data[4:6])[0]
        header.header_size = struct.unpack(">H", data[6:8])[0]
        if len(data) < header.header_size:
            return None
        header.locus_count = struct.unpack(">H", data[8:10])[0]
        offset_pos = 10
        for i in range(header.locus_count):
            if offset_pos + 4 <= len(data):
                header.locus_offsets.append(struct.unpack(">I", data[offset_pos:offset_pos + 4])[0])
                offset_pos += 4
        return header


class LocusSegment:
    def __init__(self, name: str = "", mut_rate: float = 0.02,
                 cross_pool: str = "default", bytecode: bytes = b""):
        self.name = name
        self.mut_rate = mut_rate
        self.cross_pool = cross_pool
        self.bytecode = bytecode
        self.entry_point = 0

    def to_bytes(self) -> bytes:
        data = bytearray()
        name_bytes = self.name.encode("utf-8")
        data.extend(struct.pack(">H", len(name_bytes)))
        data.extend(name_bytes)
        data.extend(struct.pack(">f", self.mut_rate))
        pool_bytes = self.cross_pool.encode("utf-8")
        data.extend(struct.pack(">H", len(pool_bytes)))
        data.extend(pool_bytes)
        data.extend(struct.pack(">I", self.entry_point))
        data.extend(struct.pack(">I", len(self.bytecode)))
        data.extend(self.bytecode)
        return bytes(data)

    @classmethod
    def from_bytes(cls, data: bytes, offset: int = 0) -> Tuple[Optional["LocusSegment"], int]:
        pos = offset
        if pos + 2 > len(data):
            return None, pos
        name_len = struct.unpack(">H", data[pos:pos + 2])[0]
        pos += 2
        if pos + name_len > len(data):
            return None, pos
        name = data[pos:pos + name_len].decode("utf-8")
        pos += name_len
        if pos + 4 > len(data):
            return None, pos
        mut_rate = struct.unpack(">f", data[pos:pos + 4])[0]
        pos += 4
        if pos + 2 > len(data):
            return None, pos
        pool_len = struct.unpack(">H", data[pos:pos + 2])[0]
        pos += 2
        if pos + pool_len > len(data):
            return None, pos
        cross_pool = data[pos:pos + pool_len].decode("utf-8")
        pos += pool_len
        if pos + 8 > len(data):
            return None, pos
        entry_point = struct.unpack(">I", data[pos:pos + 4])[0]
        pos += 4
        bc_len = struct.unpack(">I", data[pos:pos + 4])[0]
        pos += 4
        if pos + bc_len > len(data):
            return None, pos
        bytecode = data[pos:pos + bc_len]
        pos += bc_len
        seg = cls(name=name, mut_rate=mut_rate, cross_pool=cross_pool, bytecode=bytecode)
        seg.entry_point = entry_point
        return seg, pos


class NativeLoader:
    def __init__(self):
        self.isa = HexagramInstructionSet()
        self.loaded_segments: Dict[str, LocusSegment] = {}

    def load_evb(self, filepath: str) -> Optional[Dict]:
        with open(filepath, "rb") as f:
            data = f.read()
        return self.load_evb_bytes(data)

    def load_evb_bytes(self, data: bytes) -> Optional[Dict]:
        header = EvbHeader.from_bytes(data)
        if not header:
            return None
        segments = {}
        for offset in header.locus_offsets:
            seg, _ = LocusSegment.from_bytes(data, offset)
            if seg:
                segments[seg.name] = seg
                self.loaded_segments[seg.name] = seg
        return {
            "header": {
                "version": header.version,
                "locus_count": header.locus_count,
            },
            "segments": {name: {
                "name": seg.name,
                "mut_rate": seg.mut_rate,
                "cross_pool": seg.cross_pool,
                "bytecode_size": len(seg.bytecode),
                "entry_point": seg.entry_point,
            } for name, seg in segments.items()},
        }

    def execute_segment(self, segment_name: str, vm: Optional[IChingVM] = None,
                        max_cycles: int = 100000) -> Dict:
        seg = self.loaded_segments.get(segment_name)
        if not seg:
            return {"error": f"Segment '{segment_name}' not loaded"}
        if vm is None:
            vm = IChingVM()
        vm.reset()
        program = self._bytecode_to_program(seg.bytecode)
        vm.load_program(program)
        state = vm.run(max_cycles=max_cycles)
        return {
            "segment": segment_name,
            "state": state.name,
            "cycles": vm.cycle_count,
            "energy": vm.energy_cost,
            "registers": {f"R{i}": vm.registers[i] for i in range(16)},
        }

    def _bytecode_to_program(self, bytecode: bytes) -> List[dict]:
        program = []
        pos = 0
        while pos + 1 < len(bytecode):
            byte1 = bytecode[pos]
            byte2 = bytecode[pos + 1]
            opcode = (byte1 >> 2) & 0x3F
            modifier = ((byte1 & 0x03) << 4) | (byte2 & 0x0F)
            pos += 2
            operands = []
            op_count = IChingVM._operand_count(opcode)
            for _ in range(op_count):
                if pos < len(bytecode):
                    operands.append(bytecode[pos])
                    pos += 1
                else:
                    operands.append(0)
            program.append({
                "opcode": opcode,
                "modifier": modifier,
                "operands": operands,
            })
        return program

    HEADER_SIZE = 256

    def build_evb(self, segments: List[LocusSegment]) -> bytes:
        header = EvbHeader()
        header.locus_count = len(segments)
        seg_bytes_list = [seg.to_bytes() for seg in segments]
        offsets = []
        current_offset = self.HEADER_SIZE
        for sb in seg_bytes_list:
            offsets.append(current_offset)
            current_offset += len(sb)
        header.locus_offsets = offsets
        header_bytes = header.to_bytes()
        if len(header_bytes) < self.HEADER_SIZE:
            header_bytes += b"\x00" * (self.HEADER_SIZE - len(header_bytes))
        else:
            header_bytes = header_bytes[:self.HEADER_SIZE]
        return header_bytes + b"".join(seg_bytes_list)

    def save_evb(self, filepath: str, segments: List[LocusSegment]):
        data = self.build_evb(segments)
        with open(filepath, "wb") as f:
            f.write(data)

    def link(self, evb_files: List[str], output_path: str,
             entry_locus: Optional[str] = None) -> Dict:
        all_segments = []
        for filepath in evb_files:
            self.load_evb(filepath)
        for name, seg in self.loaded_segments.items():
            all_segments.append(seg)
        self.save_evb(output_path, all_segments)
        return {
            "output": output_path,
            "segment_count": len(all_segments),
            "segments": [s.name for s in all_segments],
        }
