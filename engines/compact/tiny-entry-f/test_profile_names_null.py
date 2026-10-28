import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

PATH = Path(__file__).with_name("profile_names_null.py")
SPEC = importlib.util.spec_from_file_location("f_profile_names_null", PATH)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


class SelectedSpelling(unittest.TestCase):
    def setUp(self):
        self.source = b"NULL " * 4 + b"PROMO " * 8 + b"MOVE " * 3 + b"aa " * 28

    def candidate(self, variant):
        data = self.source
        for before, after, _ in HELPER.TOKENS:
            data = data.replace(before, after)
        return data

    def test_selected_variant_round_trip_and_reject_tampering(self):
        for variant in ("names-null",):
            with self.subTest(variant=variant):
                expected = self.candidate(variant)
                with patch.dict(HELPER.INPUTS, {"test-p4": HELPER.pin(self.source)}), \
                     patch.dict(HELPER.OUTPUTS[variant], {"test-p4": HELPER.pin(expected)}):
                    candidate, proof = HELPER.transform_source(self.source, family="F", profile_id="test-p4", variant=variant)
                    self.assertEqual(candidate, expected)
                    self.assertEqual(HELPER.restore_source(candidate, proof), self.source)
                    with self.assertRaises(ValueError):
                        HELPER.restore_source(candidate + b"x", proof)
                    changed = copy.deepcopy(proof)
                    changed["edits"][0]["before"] = "changed"
                    with self.assertRaises(ValueError):
                        HELPER.restore_source(candidate, changed)

    def test_rejects_other_family_profile_variant_or_changed_source(self):
        with self.assertRaises(ValueError):
            HELPER.transform_source(self.source, family="B", profile_id="test-p4")
        with self.assertRaises(ValueError):
            HELPER.transform_source(self.source, family="F", profile_id="test-p192")
        with self.assertRaises(ValueError):
            HELPER.transform_source(self.source, family="F", profile_id="test-p4", variant="unknown")
        with self.assertRaises(ValueError):
            HELPER.transform_source(self.source, family="F", profile_id="test-p4", variant="names-null-loops")
        with self.assertRaises(ValueError):
            HELPER.transform_source(self.source, family="F", profile_id="test-p4")

    def test_rejects_replacement_name_collision(self):
        unsafe = self.source + b" qO"
        with patch.dict(HELPER.INPUTS, {"test-p4": HELPER.pin(unsafe)}):
            with self.assertRaisesRegex(ValueError, "already used"):
                HELPER.transform_source(unsafe, family="F", profile_id="test-p4")


if __name__ == "__main__":
    unittest.main()
