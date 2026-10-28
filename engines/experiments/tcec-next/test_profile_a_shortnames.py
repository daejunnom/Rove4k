import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("profile_a_shortnames", HERE / "profile_a_shortnames.py")
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)


class AShortnamesTests(unittest.TestCase):
    def test_only_identifier_tokens_change_and_full_inverse(self):
        original = (b'#define OLD 1\nint f(void){return OLD;}\n'
                    b'/* OLD */ const char *s="OLD"; char c=\'O\'; // OLD\n')
        candidate, edits = target._project(original, ((b"OLD", b"NN", 2),))
        self.assertEqual(candidate, original.replace(b"#define OLD", b"#define NN").replace(b"return OLD", b"return NN"))
        self.assertEqual(target._inverse(candidate, edits), original)

    def test_collision_and_wrong_occurrence_count_fail(self):
        with self.assertRaisesRegex(ValueError, "already exists"):
            target._project(b"int OLD; int NN;", ((b"OLD", b"NN", 1),))
        with self.assertRaisesRegex(ValueError, "occurrence counts"):
            target._project(b"int OLD;", ((b"OLD", b"NN", 2),))

    def test_bad_inverse_and_unpinned_source_fail(self):
        candidate, edits = target._project(b"int OLD;", ((b"OLD", b"NN", 1),))
        with self.assertRaisesRegex(ValueError, "inverse token"):
            target._inverse(candidate.replace(b"NN", b"XX"), edits)
        for family, profile in (("B", "test-p4"), ("A", "test-p28"), ("A", "test-p4")):
            with self.subTest(family=family, profile=profile), self.assertRaises(ValueError):
                target.transform_source(b"int OLD;", family=family, profile_id=profile)


if __name__ == "__main__":
    unittest.main()
