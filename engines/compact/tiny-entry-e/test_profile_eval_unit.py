"""Bounded checks for the experimental E fixed-coefficient projection."""
import hashlib
import unittest
from unittest.mock import patch

import profile_eval_unit as target


def fixture():
    return (target.TABLE + b"\n" + b";".join(before for before, _ in target.EDITS) + b";\n")


class FixedEProjection(unittest.TestCase):
    def test_rewrites_all_three_fixed_values_and_preserves_inverse(self):
        source = fixture()
        with patch.object(target, "INPUT_SHA256", {hashlib.sha256(source).hexdigest()}):
            result, report = target.transform(source)
        for before, after in target.EDITS:
            self.assertNotIn(before, result)
            self.assertEqual(result.count(after), 1)
        self.assertTrue(report["inverse_exact"])
        self.assertFalse(report["runtime_qualified"])
        self.assertEqual(report["source_sha256"], hashlib.sha256(source).hexdigest())

    def test_unpinned_or_modified_table_is_rejected(self):
        source = fixture()
        with self.assertRaisesRegex(ValueError, "independently pinned"):
            target.transform(source)
        changed = source.replace(b"10,1,16", b"10,2,16")
        with patch.object(target, "INPUT_SHA256", {hashlib.sha256(changed).hexdigest()}):
            with self.assertRaisesRegex(ValueError, "fixed-model table"):
                target.transform(changed)

    def test_ambiguous_inverse_is_rejected(self):
        source = fixture() + b"p->a*abs(p->a);\n"
        with patch.object(target, "INPUT_SHA256", {hashlib.sha256(source).hexdigest()}):
            with self.assertRaisesRegex(ValueError, "expression layout"):
                target.transform(source)

    def test_macro_projection_follows_coefficients_and_restores_exactly(self):
        source = (b"#define FROM(m) (m)\n#define MOVE(a,b,c) (a)\n#define PROMO(m) (m)\n"
                  + fixture() + b"FROM(x);MOVE(x,y,z);PROMO(x);\n")
        with patch.object(target, "INPUT_SHA256", {hashlib.sha256(source).hexdigest()}):
            coefficient_result, _ = target.transform(source)
        with patch.object(target, "COEFFICIENT_RESULT_SHA256", {hashlib.sha256(coefficient_result).hexdigest()}):
            result, report = target.transform_macros(coefficient_result)
        self.assertIn(b"#define TT(m)", result)
        self.assertIn(b"#define YX(a,b,c)", result)
        self.assertIn(b"#define XX(m)", result)
        self.assertTrue(report["inverse_exact"])
        self.assertFalse(report["runtime_qualified"])

    def test_macro_collision_and_unpinned_stage_are_rejected(self):
        source = b"#define FROM(m) (m)\n#define MOVE(a,b,c) (a)\n#define PROMO(m) (m)\nTT;\n"
        with self.assertRaisesRegex(ValueError, "pinned E coefficient"):
            target.transform_macros(source)
        with patch.object(target, "COEFFICIENT_RESULT_SHA256", {hashlib.sha256(source).hexdigest()}):
            with self.assertRaisesRegex(ValueError, "macro identifiers"):
                target.transform_macros(source)

    def test_public_two_stage_proof_binds_profile_and_full_inverse(self):
        source = (b"#define FROM(m) (m)\n#define MOVE(a,b,c) (a)\n#define PROMO(m) (m)\n"
                  + fixture() + b"FROM(x);MOVE(x,y,z);PROMO(x);\n")
        source_sha = hashlib.sha256(source).hexdigest()
        with patch.object(target, "INPUT_SHA256", {source_sha}):
            coefficient_result, _ = target.transform(source)
            compact_sha = hashlib.sha256(coefficient_result).hexdigest()
            with patch.object(target, "COEFFICIENT_RESULT_SHA256", {compact_sha}), \
                    patch.object(target, "PROFILE_BY_SOURCE_SHA", {source_sha: ("test-p4", "legal-maker")}):
                candidate, proof = target.transform_source(source, family="E", profile_id="test-p4")
                self.assertEqual(proof["schema"], target.SCHEMA)
                self.assertEqual(proof["ep_variant"], "legal-maker")
                self.assertEqual(target.restore_source(candidate, proof), source)
                with self.assertRaisesRegex(ValueError, "profile differ"):
                    target.transform_source(source, family="E", profile_id="tcec-provisional")
                changed = {**proof, "runtime_qualified": True}
                with self.assertRaisesRegex(ValueError, "canonical E source proof"):
                    target.restore_source(candidate, changed)


if __name__ == "__main__":
    unittest.main()
