import os
import sys
import struct
import json
import tempfile
from typing import Dict, List, Optional
from evomorph.native.loader.evb_loader import NativeLoader, LocusSegment
from evomorph.native.bytecode_utils import source_to_segments
from evomorph.bootstrap.runtime.enhanced_runtime import EnhancedEvoRuntime


EVO_IMAGE_MAGIC = b"EVOI"
EVO_IMAGE_VERSION = 1


class EvoImage:
    def __init__(self):
        self.loader = NativeLoader()
        self.compiler = EnhancedEvoRuntime()
        self.image_data = bytearray()
        self.manifest: Dict = {}

    def build_from_source(self, evo_source: str, entry_locus: str,
                          platform: str = "linux-6.x") -> bytes:
        segments = source_to_segments(self.compiler, evo_source)
        for seg in segments:
            if seg.name == entry_locus:
                seg.entry_point = 0
        self.manifest = {
            "entry_locus": entry_locus,
            "platform": platform,
            "locus_count": len(segments),
            "loci": [s.name for s in segments],
            "version": EVO_IMAGE_VERSION,
        }
        return self._pack_image(segments)

    def build_from_evb(self, evb_path: str, entry_locus: str,
                       platform: str = "linux-6.x") -> bytes:
        self.loader.load_evb(evb_path)
        segments = list(self.loader.loaded_segments.values())
        for seg in segments:
            if seg.name == entry_locus:
                seg.entry_point = 0
        self.manifest = {
            "entry_locus": entry_locus,
            "platform": platform,
            "locus_count": len(segments),
            "loci": [s.name for s in segments],
            "version": EVO_IMAGE_VERSION,
        }
        return self._pack_image(segments)

    def _pack_image(self, segments: List[LocusSegment]) -> bytes:
        image = bytearray()
        image.extend(EVO_IMAGE_MAGIC)
        image.extend(struct.pack(">H", EVO_IMAGE_VERSION))
        manifest_json = json.dumps(self.manifest, ensure_ascii=False).encode("utf-8")
        image.extend(struct.pack(">I", len(manifest_json)))
        image.extend(manifest_json)
        evb_data = self.loader.build_evb(segments)
        image.extend(struct.pack(">I", len(evb_data)))
        image.extend(evb_data)
        runner_script = self._generate_runner_script()
        image.extend(struct.pack(">I", len(runner_script)))
        image.extend(runner_script)
        return bytes(image)

    def _generate_runner_script(self) -> bytes:
        script = '''#!/usr/bin/env python3
import sys
import os
import struct
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

EVO_IMAGE_MAGIC = b"EVOI"

def run_image(image_path):
    with open(image_path, "rb") as f:
        data = f.read()
    if data[:4] != EVO_IMAGE_MAGIC:
        print("Not a valid EvoImage file")
        sys.exit(1)
    pos = 4
    version = struct.unpack(">H", data[pos:pos+2])[0]
    pos += 2
    manifest_len = struct.unpack(">I", data[pos:pos+4])[0]
    pos += 4
    manifest = json.loads(data[pos:pos+manifest_len].decode("utf-8"))
    pos += manifest_len
    evb_len = struct.unpack(">I", data[pos:pos+4])[0]
    pos += 4
    evb_data = data[pos:pos+evb_len]
    pos += evb_len
    from evomorph.native.loader.evb_loader import NativeLoader
    from evomorph.vm.virtual_machine import IChingVM
    loader = NativeLoader()
    loader.load_evb_bytes(evb_data)
    entry = manifest.get("entry_locus", "")
    if entry:
        result = loader.execute_segment(entry, max_cycles=1000000)
        print(f"State: {result['state']}")
        print(f"Cycles: {result['cycles']}")
        print(f"Energy: {result['energy']:.2f}")
    else:
        print("No entry locus specified")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <image.evoi>")
        sys.exit(1)
    run_image(sys.argv[1])
'''
        return script.encode("utf-8")

    def save_image(self, filepath: str, image_data: bytes):
        with open(filepath, "wb") as f:
            f.write(image_data)

    @classmethod
    def load_and_run(cls, image_path: str, max_cycles: int = 1000000) -> Dict:
        with open(image_path, "rb") as f:
            data = f.read()
        return cls._run_image_data(data, max_cycles)

    @classmethod
    def load_and_run_bytes(cls, image_data: bytes, max_cycles: int = 1000000) -> Dict:
        return cls._run_image_data(image_data, max_cycles)

    @classmethod
    def _run_image_data(cls, data: bytes, max_cycles: int = 1000000) -> Dict:
        from evomorph.native.loader.evb_loader import NativeLoader
        if data[:4] != EVO_IMAGE_MAGIC:
            return {"error": "Not a valid EvoImage file"}
        pos = 4
        version = struct.unpack(">H", data[pos:pos + 2])[0]
        pos += 2
        manifest_len = struct.unpack(">I", data[pos:pos + 4])[0]
        pos += 4
        manifest = json.loads(data[pos:pos + manifest_len].decode("utf-8"))
        pos += manifest_len
        evb_len = struct.unpack(">I", data[pos:pos + 4])[0]
        pos += 4
        evb_data = data[pos:pos + evb_len]
        loader = NativeLoader()
        loader.load_evb_bytes(evb_data)
        entry = manifest.get("entry_locus", "")
        if not entry:
            return {"error": "No entry locus in manifest"}
        return loader.execute_segment(entry, max_cycles=max_cycles)
