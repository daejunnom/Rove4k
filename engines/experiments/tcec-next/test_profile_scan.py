"""Pure finite source-stage tests. No generated-source, compiler or engine runs."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("finite_square_scan_tests", HERE / "profile_scan.py")
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)


def fixture(family="A"):
    first, second = scan.SPANS[family]
    body1 = "seen[q]++;if(q==stop)return q;if(q&1)continue;total+=q;}"
    body2 = "piece=board[o];if(!piece)continue;for(int r=0;r<8;r++){ray[r]+=o;}return piece;}"
    source = ("#include<limits.h>\nHEAD\n" + first[1] + body1 + "\nMIDDLE\n" + second[1] + body2 + "\nTAIL\n").encode()
    return source, (body1.encode(), body2.encode())


class FiniteSquareScan(unittest.TestCase):
    def test_finite_six_literal_policies_and_cleanup_last(self):
        domain = {(family, profile) for family in ("A", "C")
                  for profile in ("test-p4", "test-p28", "tcec-provisional")}
        self.assertEqual(set(scan.INPUTS), domain)
        for table in (scan.OUTPUTS, scan.POST_DEPENDENCY_INPUTS, scan.POST_DEPENDENCY_OUTPUTS):
            self.assertEqual(set(table), domain)
        self.assertEqual(scan.STAGE_ORDER,
            ("resource", "phase-init", "compound", "square-successor", "dependency-cleanup"))
        self.assertEqual(scan.DECLARATION, {"path": scan.SELF, "variant": "square-successor"})
        for key in domain:
            for table in (scan.INPUTS, scan.OUTPUTS, scan.POST_DEPENDENCY_INPUTS,
                          scan.POST_DEPENDENCY_OUTPUTS):
                size, digest = table[key]
                self.assertIs(type(size), int)
                self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertEqual(scan.OUTPUTS[key][0] - scan.INPUTS[key][0], -29)
            self.assertEqual(scan.POST_DEPENDENCY_OUTPUTS[key][0] -
                             scan.POST_DEPENDENCY_INPUTS[key][0], -29)
            cleanup = 0 if key[0] == "A" else len(b"#include<limits.h>\n")
            self.assertEqual(scan.INPUTS[key][0] - scan.POST_DEPENDENCY_INPUTS[key][0], cleanup)
            self.assertEqual(scan.OUTPUTS[key][0] - scan.POST_DEPENDENCY_OUTPUTS[key][0], cleanup)

    def test_integer_visitation_order_and_signed_bound(self):
        witness = scan.iteration_witness()
        expected = [rank * 16 + file for rank in range(8) for file in range(8)]
        self.assertEqual(witness["values"], expected)
        self.assertEqual((witness["count"], witness["last"], witness["exit"],
                          witness["maximum_addition"]), (64, 119, 128, 128))
        self.assertIs(witness["compiled_C_executed"], False)

    def test_two_literal_openings_only_and_exact_full_inverse(self):
        for family in scan.FAMILIES:
            source, bodies = fixture(family)
            candidate, edits, gaps = scan._project(source, scan.SPANS[family])
            expected = source
            for _, before, after in scan.SPANS[family]:
                expected = expected.replace(before.encode(), after.encode(), 1)
            self.assertEqual(candidate, expected)
            self.assertEqual(scan._inverse(candidate, json.loads(json.dumps(edits))), source)
            self.assertEqual(len(edits), 2)
            self.assertEqual(len(gaps), 3)
            self.assertTrue(all(body in candidate for body in bodies))
            for gap in gaps:
                old = source[gap["input_begin"]:gap["input_begin"] + gap["bytes"]]
                new = candidate[gap["output_begin"]:gap["output_begin"] + gap["bytes"]]
                self.assertEqual(new, old)
                self.assertEqual(scan.pin(new), {name: gap[name] for name in ("bytes", "sha256")})

    def test_cleanup_bridge_inert_fixture_preserves_stage_order(self):
        directive = b"#include<limits.h>\n"
        for family in scan.FAMILIES:
            source, _ = fixture(family)
            scan_first, _, _ = scan._project(source, scan.SPANS[family])
            cleanup_last = scan_first.replace(directive, b"", 1)
            cleanup_first, _, _ = scan._project(source.replace(directive, b"", 1), scan.SPANS[family])
            self.assertEqual(cleanup_last, cleanup_first)
            self.assertIn(directive, scan_first)
            self.assertNotIn(directive, cleanup_last)

    def test_missing_duplicate_or_overlapping_opening_is_rejected(self):
        source, _ = fixture()
        first = scan.SPANS["A"][0][1].encode()
        for changed in (source.replace(first, b"missing", 1), source + first):
            with self.assertRaises(ValueError):
                scan._project(changed, scan.SPANS["A"])
        with self.assertRaises(ValueError):
            scan._project(b"abcdef", (("outer", "abcd", "x"), ("inner", "bc", "y")))

    def test_inverse_requires_exact_typed_finite_coordinates(self):
        source, _ = fixture()
        candidate, edits, _ = scan._project(source, scan.SPANS["A"])
        for name, values in (("output_begin", (True, 1.0, -1, len(candidate) + 1)),
                             ("input_begin", (False, 1.0, -1))):
            for value in values:
                changed = copy.deepcopy(edits)
                changed[0][name] = value
                with self.assertRaises(ValueError):
                    scan._inverse(candidate, changed)
        for changed in ([], edits[:1], edits + edits[:1]):
            with self.assertRaises(ValueError):
                scan._inverse(candidate, changed)
        changed = copy.deepcopy(edits)
        changed[0]["extra"] = True
        with self.assertRaises(ValueError):
            scan._inverse(candidate, changed)

    def test_public_admission_rejects_other_families_profiles_and_wrong_bytes(self):
        for family, profile in (("B", "test-p4"), ("E", "test-p28"), ("F", "tcec-provisional"),
                                ("A", "other"), (True, "test-p4"), ([], "test-p4")):
            with self.assertRaises(ValueError):
                scan.transform_source(b"", family=family, profile_id=profile)
        for family in scan.FAMILIES:
            for profile in scan.PROFILES:
                for source in (b"wrong", bytearray(b"wrong")):
                    with self.assertRaises(ValueError):
                        scan.transform_source(source, family=family, profile_id=profile)

    def test_public_inverse_does_not_accept_synthetic_source_or_partial_proof(self):
        source, _ = fixture()
        candidate, edits, _ = scan._project(source, scan.SPANS["A"])
        proof = dict(schema=scan.SCHEMA, family="A", profile_id="test-p4",
                     output=scan.pin(candidate), edits=edits)
        for changed in (proof, {**proof, "family": "B"}, {**proof, "profile_id": "other"}):
            with self.assertRaises(ValueError):
                scan.restore_source(candidate, changed)

    def test_canonical_json_is_type_sensitive_and_finite(self):
        self.assertNotEqual(scan._json({"offset": 1}), scan._json({"offset": True}))
        self.assertNotEqual(scan._json({"offset": 1}), scan._json({"offset": 1.0}))
        for value in (float("nan"), float("inf"), object()):
            with self.assertRaises(ValueError):
                scan._json({"bad": value})

    def test_source_files_parse_as_python310(self):
        for path in (HERE / "profile_scan.py", Path(__file__)):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 10))


if __name__ == "__main__":
    unittest.main()
