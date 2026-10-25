"""Shared source ownership, frozen closure and unchanged readable contracts."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("rove_source_composition", Path(__file__).with_name("source_composition.py"))
composition = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(composition)
UNIT = "engines/common/board.c"
TEMPLATE = b'/* owned prefix */\n#include "rove-common/board/value"\n/* owned suffix */\n'
SHARED = b'/* rove:begin value */\nint value(void){return 7;}\n/* rove:end value */\n'


class CompositionContracts(unittest.TestCase):
    def test_each_recipe_assembles_its_unchanged_readable_contract(self):
        for family in "abcdef":
            with self.subTest(family=family):
                entry = ROOT / ("engines/compact/tiny-entry-" + family)
                recipe = json.loads((entry / "recipe.json").read_text())
                name = "native/board.c" if family == "d" else "engine.c"
                source = (entry / name).read_bytes()
                shared, records = composition.read_shared(ROOT, recipe["shared_source_sha256"])
                self.assertEqual(set(composition.dependencies(source)), set(shared))
                self.assertEqual(set(records), set(shared))
                actual = composition.assemble(source, shared, expected_sha256=recipe["assembled_source_sha256"][name])
                self.assertNotIn(b"rove-common/", actual)
                self.assertNotEqual(actual, source)
                self.assertEqual(actual, composition.read_source(ROOT, (entry / name).relative_to(ROOT).as_posix()))

    def test_only_fragment_body_is_emitted_and_source_order_is_preserved(self):
        actual = composition.assemble(TEMPLATE, {UNIT: SHARED})
        self.assertEqual(actual, b'/* owned prefix */\nint value(void){return 7;}\n/* owned suffix */\n')
        with self.assertRaisesRegex(ValueError, "assembled canonical"):
            composition.assemble(TEMPLATE, {UNIT: SHARED}, expected_sha256="0" * 64)

    def test_unclosed_or_ambiguous_inputs_fail_before_compilation(self):
        for shared in ({}, {UNIT: SHARED, "engines/common/other.c": SHARED}):
            with self.subTest(shared=tuple(shared)), self.assertRaisesRegex(ValueError, "exactly cover"):
                composition.assemble(TEMPLATE, shared)
        with self.assertRaisesRegex(ValueError, "missing shared"):
            composition.assemble(TEMPLATE.replace(b"/value", b"/other"), {UNIT: SHARED})
        with self.assertRaisesRegex(ValueError, "malformed shared"):
            composition.dependencies(TEMPLATE.replace(b'#include "', b'# include "'))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            composition.assemble(TEMPLATE, {UNIT: SHARED + SHARED})
        with self.assertRaisesRegex(ValueError, "malformed or nested"):
            composition.assemble(TEMPLATE, {UNIT: SHARED.replace(b"rove:end value", b"rove:end other")})
        with self.assertRaisesRegex(ValueError, "recursive"):
            composition.assemble(TEMPLATE, {UNIT: SHARED.replace(b"int value(void){return 7;}", TEMPLATE.strip())})

    def test_frozen_inputs_remain_independent_of_later_workspace_edits(self):
        with tempfile.TemporaryDirectory(prefix="rove-composition-") as temporary:
            root = Path(temporary) / "source"
            path = root / UNIT
            path.parent.mkdir(parents=True)
            path.write_bytes(SHARED.replace(b"\n", b"\r\n"))
            expected = {UNIT: sha256(SHARED).hexdigest()}
            frozen, records = composition.freeze_shared(root, Path(temporary) / "frozen", expected)
            self.assertTrue(records[UNIT]["LF_normalization"])
            path.write_bytes(SHARED.replace(b"return 7", b"return 8"))
            self.assertIn(b"return 7", composition.assemble(TEMPLATE, frozen))
            with self.assertRaisesRegex(ValueError, "differs from recipe"):
                composition.read_shared(root, expected)

    def test_d_projection_proof_depends_on_normalized_inputs_not_checkout_line_endings(self):
        logical = "engines/experiments/tiny-d-submission/source.py"

        def load_source(root, name):
            spec = importlib.util.spec_from_file_location(name, root / logical)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        producer = load_source(ROOT, "rove_d_composition_normal")
        expected_files, expected_proof = producer.prepare(producer.production().resource_profile("test-p4"))
        closure = expected_proof["source_closure"]
        with tempfile.TemporaryDirectory(prefix="rove-d-composition-") as temporary:
            root = Path(temporary)
            for name in (*closure["engine_inputs"], *closure["tool_inputs"]):
                data = (ROOT / name).read_bytes()
                if name.startswith("engines/common/"):
                    data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            isolated = load_source(root, "rove_d_composition_crlf")
            files, proof = isolated.prepare(isolated.production().resource_profile("test-p4"))
            self.assertEqual(files, expected_files)
            self.assertEqual(proof, expected_proof)


if __name__ == "__main__":
    unittest.main()
