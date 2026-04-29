import sys
import os
import json
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evomorph.native.loader.evb_loader import NativeLoader, EvbHeader, LocusSegment
from evomorph.native.linker.linker import EvoLinker
from evomorph.native.image.evo_image import EvoImage
from evomorph.native.shell.evoshell import EvoShell
from evomorph.native.bytecode_utils import source_to_segments
from evomorph.compiler import EvocCompiler
from evomorph.vm.virtual_machine import IChingVM, VMState
from evomorph.hexagrams import HexagramInstructionSet


class TestNativeLoader(unittest.TestCase):
    def setUp(self):
        self.loader = NativeLoader()
        self.compiler = EvocCompiler()

    def test_build_and_load_evb(self):
        source = '''@locus test_native {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
        ䷾ SYNC
        ䷋ HALT
    }
}'''
        segments = source_to_segments(self.compiler, source)
        evb_data = self.loader.build_evb(segments)
        self.assertIsInstance(evb_data, bytes)
        self.assertGreater(len(evb_data), 0)
        result = self.loader.load_evb_bytes(evb_data)
        self.assertIsNotNone(result)
        self.assertIn("test_native", result["segments"])

    def test_execute_segment(self):
        source = '''@locus exec_native {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
        ䷋ HALT
    }
}'''
        segments = source_to_segments(self.compiler, source)
        evb_data = self.loader.build_evb(segments)
        self.loader.load_evb_bytes(evb_data)
        result = self.loader.execute_segment("exec_native", max_cycles=100)
        self.assertEqual(result["state"], "HALTED")

    def test_save_and_load_evb_file(self):
        with tempfile.NamedTemporaryFile(suffix=".evb", delete=False) as f:
            tmppath = f.name
        try:
            seg = LocusSegment(name="file_test", mut_rate=0.02, bytecode=b"\xfc\x00\x00\x00\xe0\x00\x00\x00")
            self.loader.save_evb(tmppath, [seg])
            self.assertTrue(os.path.exists(tmppath))
            result = self.loader.load_evb(tmppath)
            self.assertIsNotNone(result)
        finally:
            os.unlink(tmppath)


class TestEvoLinker(unittest.TestCase):
    def test_add_evo_source(self):
        linker = EvoLinker()
        source = '''@locus link_test {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
        ䷾ SYNC
    }
}'''
        idx = linker.add_evo_source(source)
        self.assertGreaterEqual(idx, 0)
        self.assertGreater(len(linker.segments), 0)

    def test_link_sources(self):
        with tempfile.NamedTemporaryFile(suffix=".evb", delete=False) as f:
            tmppath = f.name
        try:
            linker = EvoLinker()
            source1 = '''@locus link_a {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
    }
}'''
            source2 = '''@locus link_b {
    mut_rate = 0.02
    卦序: {
        ䷁ RECV R0, R1
    }
}'''
            linker.add_evo_source(source1)
            linker.add_evo_source(source2)
            result = linker.link(tmppath, entry_locus="link_a")
            self.assertEqual(result["segment_count"], 2)
            self.assertIn("link_a", result["segments"])
            self.assertIn("link_b", result["segments"])
        finally:
            if os.path.exists(tmppath):
                os.unlink(tmppath)


class TestEvoImage(unittest.TestCase):
    def test_build_from_source(self):
        source = '''@locus image_test {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
        ䷾ SYNC
        ䷋ HALT
    }
}'''
        builder = EvoImage()
        image_data = builder.build_from_source(source, "image_test")
        self.assertIsInstance(image_data, bytes)
        self.assertTrue(image_data.startswith(b"EVOI"))

    def test_save_and_load_image(self):
        with tempfile.NamedTemporaryFile(suffix=".evoi", delete=False) as f:
            tmppath = f.name
        try:
            source = '''@locus img_run {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
        ䷋ HALT
    }
}'''
            builder = EvoImage()
            image_data = builder.build_from_source(source, "img_run")
            builder.save_image(tmppath, image_data)
            self.assertTrue(os.path.exists(tmppath))
            result = EvoImage.load_and_run(tmppath, max_cycles=100)
            self.assertEqual(result["state"], "HALTED")
        finally:
            if os.path.exists(tmppath):
                os.unlink(tmppath)


class TestEvoShell(unittest.TestCase):
    def test_cmd_compile_evb(self):
        with tempfile.NamedTemporaryFile(suffix=".evo", delete=False, mode="w", encoding="utf-8") as f:
            f.write('''@locus shell_test {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
        ䷋ HALT
    }
}''')
            evo_path = f.name
        evb_path = evo_path.replace(".evo", ".evb")
        try:
            shell = EvoShell()
            ret = shell.cmd_compile(evo_path, evb_path, fmt="evb")
            self.assertEqual(ret, 0)
            self.assertTrue(os.path.exists(evb_path))
        finally:
            os.unlink(evo_path)
            if os.path.exists(evb_path):
                os.unlink(evb_path)

    def test_cmd_run_evo(self):
        with tempfile.NamedTemporaryFile(suffix=".evo", delete=False, mode="w", encoding="utf-8") as f:
            f.write('''@locus run_test {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
        ䷋ HALT
    }
}''')
            evo_path = f.name
        try:
            shell = EvoShell()
            ret = shell.cmd_run(evo_path, max_cycles=100)
            self.assertEqual(ret, 0)
        finally:
            os.unlink(evo_path)

    def test_cmd_xiangci(self):
        shell = EvoShell()
        ret = shell.cmd_xiangci("并行求和")
        self.assertEqual(ret, 0)


class TestSelfHostingPipeline(unittest.TestCase):
    def test_evo_to_evb_to_execution(self):
        source = '''@evolang "3.0"

@locus self_host {
    mut_rate = 0.02
    env_target = ["linux-6.x"]
    卦序: {
        ䷀ CREA R0, R1
        ䷌ FELLOWSHIP R0, R1
        ䷾ SYNC
        ䷁ RECV R2, R0
        ䷋ HALT
    }
}'''
        compiler = EvocCompiler()
        segments = source_to_segments(compiler, source)
        loader = NativeLoader()
        evb_data = loader.build_evb(segments)
        loader2 = NativeLoader()
        loader2.load_evb_bytes(evb_data)
        result = loader2.execute_segment("self_host", max_cycles=1000)
        self.assertIn(result["state"], ["HALTED", "PAUSED"])

    def test_evo_to_image_to_execution(self):
        source = '''@locus img_host {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
        ䷋ HALT
    }
}'''
        builder = EvoImage()
        image_data = builder.build_from_source(source, "img_host")
        result = EvoImage.load_and_run_bytes(image_data, max_cycles=100)
        self.assertIn(result["state"], ["HALTED", "PAUSED"])

    def test_link_and_run(self):
        linker = EvoLinker()
        source = '''@locus link_run {
    mut_rate = 0.02
    卦序: {
        ䷀ CREA R0, R1
        ䷋ HALT
    }
}'''
        linker.add_evo_source(source)
        result = linker.link_and_run("link_run", max_cycles=100)
        self.assertIn(result["state"], ["HALTED", "PAUSED"])


class TestNativeStdlib(unittest.TestCase):
    def test_native_evo_compiles(self):
        native_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "evomorph", "stdlib", "native.evo"
        )
        if not os.path.exists(native_path):
            self.skipTest("native.evo not found")
        compiler = EvocCompiler()
        with open(native_path, "r", encoding="utf-8") as f:
            source = f.read()
        result = compiler.compile(source, output_format="dict")
        self.assertIn("loci", result)
        self.assertGreater(len(result["loci"]), 0)
        locus_names = [l["name"] for l in result["loci"]]
        self.assertIn("native.loader.open_image", locus_names)
        self.assertIn("native.loader.execute", locus_names)
        self.assertIn("native.linker.merge_segments", locus_names)


if __name__ == "__main__":
    unittest.main()
