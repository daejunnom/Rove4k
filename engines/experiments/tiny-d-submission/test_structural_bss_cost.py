"""Focused pure test design for the nonselected BSS cost controller.

No test invokes a compiler, encoder, generated program or TT allocation.
The tests themselves require a separately authorized bounded pure run.
"""
import importlib.util
import lzma
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("D_bss_cost_tested", HERE / "structural_bss_cost.py")
cost = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cost
SPEC.loader.exec_module(cost)


class OptInAndAuthenticationTests(unittest.TestCase):
    def test_execute_is_required_before_capture_or_output(self):
        with mock.patch.object(cost, "capture_inputs", side_effect=AssertionError("capture reached")):
            with self.assertRaisesRegex(ValueError, "inactive"):
                cost.main(["--out", "/not-created", "--tt33-layout"])

    def test_the_one_tt33_layout_case_requires_explicit_opt_in(self):
        with mock.patch.object(cost, "capture_inputs", side_effect=AssertionError("capture reached")):
            with self.assertRaisesRegex(ValueError, "explicit --tt33-layout"):
                cost.main(["--out", "/not-created", "--execute"])

    def test_exported_layout_and_critical_source_pins_are_authenticated(self):
        raw = cost._normalized(cost.__file__)
        with mock.patch.object(cost, "layout_data", lambda *a, **k: {}):
            with self.assertRaisesRegex(ValueError, "function differs"):
                cost._self(raw)
        with mock.patch.object(cost, "BSS_PIN", (8297, "0"*64)):
            with self.assertRaisesRegex(ValueError, "constants differ"):
                cost._self(raw)


def layout_fixture(bits):
    """A sub-KiB ELF with a NOBITS extent expressed only in integer fields."""
    names = b"\0.text\0.bss\0.kernel_tt\0.shstrtab\0"
    table_base, image_base = 0x402000, 0x400000
    data = bytearray(640)
    data[:16] = b"\x7fELF\x02\x01\x01" + b"\0"*9
    struct.pack_into("<HHIQQQIHHHHHH", data, 16, 2, 62, 1, image_base+240, 64, 320,
                     0, 64, 56, 3, 64, 5, 4)
    for i, fields in enumerate(((1, 5, 0, image_base, image_base, 256, 256, 4096),
                                 (1, 6, 256, image_base+4096, image_base+4096, 0,
                                  table_base+(1 << bits)*16-(image_base+4096), 4096),
                                 (0x6474E551, 6, 0, 0, 0, 0, 0, 16))):
        struct.pack_into("<IIQQQQQQ", data, 64+i*56, *fields)
    data[272:272+len(names)] = names
    sections = ((0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                (1, 1, 6, image_base+240, 240, 16, 0, 0, 16, 0),
                (7, 8, 3, image_base+4096, 256, 16, 0, 0, 16, 0),
                (12, 8, 3, table_base, 256, (1 << bits)*16, 0, 0, 4096, 0),
                (23, 3, 0, 0, 272, len(names), 0, 0, 1, 0))
    for i, fields in enumerate(sections):
        struct.pack_into("<IIQQQQIIQQ", data, 320+i*64, *fields)
    return bytes(data)


@unittest.skipUnless(sys.platform == "linux", "canonical owners include Linux resource support")
class CanonicalSourceAndLayoutTests(unittest.TestCase):
    def setUp(self):
        self.inputs = cost.capture_inputs()
        self.core = cost._core(cost.ROOT)
        self.baseline = cost.validate_inputs(self.inputs, self.core)
        self.modules = self.core.load_modules(cost.ROOT, self.baseline)

    def test_fresh_bss_projection_uses_the_real_finite_canonical_parent(self):
        helper = cost._bss(cost.ROOT, self.inputs[cost.BSS])
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("process forbidden")), \
             mock.patch.object(lzma, "compress", side_effect=AssertionError("encoding forbidden")), \
             mock.patch.object(lzma, "decompress", side_effect=AssertionError("codec forbidden")):
            files, _ = self.core.prepare_sources(self.modules, self.baseline)
            for bits in (23, 33):
                projected, proof = cost._apply_bss(helper, files, self.modules["source"], bits)
                self.assertEqual(helper.restore(projected, proof, self.modules["source"]), files)
                self.assertEqual(proof["tt_bytes"], (1 << bits)*16)
        self.assertEqual(len(self.inputs), 42)

    def test_tt33_layout_is_small_data_and_rejects_progbits_or_late_globals(self):
        linked = layout_fixture(33)
        layout = cost.layout_data(linked, self.modules, self.baseline, self.core, tt_bits=33)
        self.assertEqual(len(linked), 640)
        self.assertEqual(layout["logical_tt_bytes"], 137438953472)
        changed = bytearray(linked)
        struct.pack_into("<I", changed, 320+3*64+4, 1)
        with self.assertRaises(ValueError):
            cost.layout_data(bytes(changed), self.modules, self.baseline, self.core, tt_bits=33)
        changed = bytearray(linked)
        struct.pack_into("<Q", changed, 320+2*64+16, layout["kernel_tt"]["address"]+16)
        with self.assertRaisesRegex(ValueError, "small section follows"):
            cost.layout_data(bytes(changed), self.modules, self.baseline, self.core, tt_bits=33)


if __name__ == "__main__":
    unittest.main()
