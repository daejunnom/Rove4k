import hashlib
import unittest
from unittest.mock import patch

import c_macro_compact as subject


class CMacroCompactContract(unittest.TestCase):
    def setUp(self):
        # Six FROM, eight PROMO and three MOVE tokens include each directive.
        self.body = (b'\n#include <time.h>\n#define FROM(m) (m)\n#define PROMO(m) (m)\n#define MOVE(m) (m)\n'
                     + b'FROM(1);' * 5 + b'PROMO(2);' * 7 + b'MOVE(3);' * 2
                     + b' "PROMO FROM MOVE AO TQ YO"; /* PROMO AO */ // FROM TQ\n'
                     + b'1e+AO;\n#include<immintrin.h>\nstatic int U(\n'
                     + b'\n'.join(before for before, _ in subject._REWRITES)
                     + b'\naT aT zC zC zC\n')
        self.digest = hashlib.sha256(self.body).hexdigest()

    def test_inverse_and_opaque_literals_for_each_profile(self):
        for profile, prefix in subject._PREFIX.items():
            source = prefix + self.body
            with self.subTest(profile=profile), patch.object(subject, "_BODY_SHA256", self.digest):
                result, proof = subject.transform_source(source, family="C", profile_id=profile)
                self.assertEqual(subject.restore_source(result, proof), source)
                self.assertEqual(proof["schema"], subject.SCHEMA)
                self.assertLess(result.index(b'#include<immintrin.h>'), result.index(b'#define TQ'))
                self.assertIn(b'"PROMO FROM MOVE AO TQ YO"', result)
                self.assertIn(b'/* PROMO AO */ // FROM TQ\n1e+AO;', result)
                for before, after in subject._REWRITES:
                    self.assertNotIn(before, result)
                    self.assertIn(after.replace(b'aT', b'aN'), result)
                self.assertFalse(proof["native_identical"])
                self.assertFalse(proof["runtime_qualified"])

    def test_collision_unpinned_and_wrong_profile_are_rejected(self):
        source = subject._PREFIX["test-p4"] + self.body
        with patch.object(subject, "_BODY_SHA256", self.digest):
            for family, profile, data in (("B", "test-p4", source),
                                          ("C", "test-p192", source),
                                          ("C", "test-p4", source + b'x'),
                                          ("C", "tcec-provisional", source)):
                with self.subTest(family=family, profile=profile), self.assertRaises(ValueError):
                    subject.transform_source(data, family=family, profile_id=profile)
        collision = self.body + b' int AO;'
        with patch.object(subject, "_BODY_SHA256", hashlib.sha256(collision).hexdigest()):
            with self.assertRaisesRegex(ValueError, "target identifier"):
                subject.transform_source(subject._PREFIX["test-p4"] + collision,
                                         family="C", profile_id="test-p4")
        for extra in (b' aN', b' zO', b' aT', b' zC'):
            bad = self.body + extra
            with self.subTest(extra=extra), patch.object(subject, "_BODY_SHA256", hashlib.sha256(bad).hexdigest()):
                with self.assertRaises(ValueError):
                    subject.transform_source(subject._PREFIX["test-p4"] + bad,
                                             family="C", profile_id="test-p4")

    def test_changed_output_proof_and_ambiguous_lexer_are_rejected(self):
        source = subject._PREFIX["test-p4"] + self.body
        with patch.object(subject, "_BODY_SHA256", self.digest):
            result, proof = subject.transform_source(source, family="C", profile_id="test-p4")
            with self.assertRaises(ValueError):
                subject.restore_source(result, {**proof, "native_identical": True})
            with self.assertRaises(ValueError):
                subject.restore_source(result, {**proof, "native_identical": 0})
            with self.assertRaises(ValueError):
                subject.restore_source(result.replace(b'YO(3)', b'OTHER(3)', 1), proof)
        for text in (b'/* bad', b'"bad\n', b'x\\\ny', b'??='):
            with self.subTest(text=text), self.assertRaises(ValueError):
                subject._parts(text)
        with self.assertRaises(ValueError):
            subject._move_header(b'#include <time.h>\nstatic int U(')
        for source in (subject._EARLY * 2 + subject._LATE,
                       subject._EARLY + subject._LATE + subject._HEADER,
                       subject._EARLY + subject._LATE * 2):
            with self.subTest(source=source), self.assertRaises(ValueError):
                subject._move_header(source)
        with self.assertRaises(ValueError):
            subject._restore_header(subject._EARLY + subject._HEADER + b'static int U(static int U(')

    def test_rewrite_missing_duplicate_and_inverse_anchors_are_rejected(self):
        canonical = b'\n'.join(before for before, _ in subject._REWRITES)
        compact = subject._rewrite(canonical)
        self.assertEqual(subject._rewrite(compact, reverse=True), canonical)
        for before, after in subject._REWRITES:
            for bad in (canonical.replace(before, b'', 1), canonical + before,
                        canonical + after):
                with self.subTest(anchor=before, bad=bad[-40:]), self.assertRaises(ValueError):
                    subject._rewrite(bad)
            for bad in (compact.replace(after, b'', 1), compact + after, compact + before):
                with self.subTest(inverse_anchor=after, bad=bad[-40:]), self.assertRaises(ValueError):
                    subject._rewrite(bad, reverse=True)


if __name__ == "__main__":
    unittest.main()
