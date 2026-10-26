"""Focused pure design tests for the inactive structural producer adapter.

No compiler, encoder, native image, engine or TT is needed by these tests.
The implementation-preparation task has not executed this test file.
"""
import importlib.util
import lzma
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("D_structural_producer_tested", HERE / "build_structural.py")
producer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = producer
SPEC.loader.exec_module(producer)


class SelectionTests(unittest.TestCase):
    def test_no_execution_opt_in_means_no_source_capture_or_output(self):
        with mock.patch.object(producer, "capture_inputs", side_effect=AssertionError("source capture was reached")):
            with self.assertRaisesRegex(ValueError, "inactive"):
                producer.main(["--profile", "test-p4", "--variant", "fast-capacity", "--out", "/not-created"])

    def test_only_named_p4_variant_is_available(self):
        producer.selection("test-p4", "fast-capacity")
        for profile, variant in (("test-p28", "fast-capacity"), ("tcec-provisional", "fast-capacity"),
                                 ("test-p4", "initial-full"), ("test-p4", "control"), (True, "fast-capacity")):
            with self.subTest(profile=profile, variant=variant), self.assertRaises(ValueError):
                producer.selection(profile, variant)

    def test_incomplete_closure_is_rejected_before_import(self):
        with mock.patch.object(producer, "_load", side_effect=AssertionError("module import was reached")):
            with self.assertRaisesRegex(ValueError, "exact producer input closure"):
                producer.load_modules(producer.ROOT, {})


class ReductionInverseTests(unittest.TestCase):
    def test_removed_declarations_restore_the_entire_original(self):
        before = b"typedef int gone;\nint kept;\n"
        after = b"\nint kept;\n"
        rounds = [{"main.c": {"input": producer.pin(before), "output": producer.pin(after),
                   "removed": [{"begin": 0, "end": 17, "declaration": "typedef int gone;", "alias": "gone"}]}}]
        self.assertEqual(producer.restore_scalar_rounds({"main.c": after}, rounds), {"main.c": before})
        changed = [{"main.c": {**rounds[0]["main.c"], "removed": [
            {**rounds[0]["main.c"]["removed"][0], "begin": 100, "end": 117}]}}]
        with self.assertRaises(ValueError):
            producer.restore_scalar_rounds({"main.c": after}, changed)

    def test_output_pin_cannot_be_replaced_by_a_value_equal_fixture(self):
        proof = [{"main.c": {"input": producer.pin(b"x"), "output": producer.pin(b"x"), "removed": []}}]
        with self.assertRaisesRegex(ValueError, "output differs"):
            producer.restore_scalar_rounds({"main.c": b"x\n"}, proof)


@unittest.skipUnless(sys.platform == "linux", "existing producer owners include Linux resource support")
class PureSourceCompositionTests(unittest.TestCase):
    def test_current_canonical_sources_replay_without_tools_or_an_upper_token(self):
        inputs = producer.capture_inputs()
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("process execution forbidden")), \
             mock.patch.object(lzma, "compress", side_effect=AssertionError("encoding forbidden")), \
             mock.patch.object(lzma, "decompress", side_effect=AssertionError("codec execution forbidden")):
            modules = producer.load_modules(producer.ROOT, inputs)
            authority = modules["structural_admission"]
            with mock.patch.object(authority.StructuralAdmission, "__init__", side_effect=AssertionError("upper token mint forbidden")):
                files, proof = producer.prepare_sources(modules, inputs)
        self.assertEqual(set(files), {"tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld"})
        self.assertEqual(proof["variant"], "fast-capacity")
        self.assertEqual(proof["resource"]["workers"], 4)
        self.assertEqual(proof["resource"]["tt_bits"], 23)
        self.assertEqual(proof["resource"]["tt_bytes"], 128 << 20)
        self.assertIn(b"#define MOVES 413", files["tiny.h"])
        self.assertEqual([row["role"] for row in proof["parent_stages"]],
            ["canonical", "prefix-storage", "process-owner", "syscall-arity", "valid-input", "search-compact", "no_tid", "square"])

    def test_foreign_or_modified_source_input_does_not_reach_modules(self):
        inputs = producer.capture_inputs()
        for changed in ({**inputs, "unknown.py": b""},
                        {**inputs, producer.D+"structural_platform.py": inputs[producer.D+"structural_platform.py"]+b"\n"},
                        {**inputs, producer.SELF: inputs[producer.SELF]+b"\n"}):
            with self.subTest(keys=len(changed)), \
                 mock.patch.object(producer, "_load", side_effect=AssertionError("module import was reached")), \
                 self.assertRaises(ValueError):
                producer.load_modules(producer.ROOT, changed)


if __name__ == "__main__":
    unittest.main()
