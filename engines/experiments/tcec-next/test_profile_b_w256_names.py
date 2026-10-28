import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


target = load(HERE / "profile_b_w256_names.py", "b_w256_names")
lexer = load(HERE.parents[1] / "scripts" / "rename_c.py", "b_w256_lexer")


def fixture():
    body = "".join((name + ";") * count for name, count in target.COUNTS.items())
    return ('#define AA 0\nJ I P(){p->v;' + body + '}void i(){}\n').encode("ascii")


class ShortNames(unittest.TestCase):
    def transform(self, data):
        with patch.dict(target.INPUTS, {"tcec-provisional": (len(data), target.sha256(data).hexdigest())}):
            return target.transform_source(data, family="B", profile_id="tcec-provisional", lexer=lexer)

    def test_exact_inverse_preserves_literals_directives_and_gaps(self):
        data = fixture().replace(b"}void i(", b'puts("preserved literal");}void i(')
        with patch.dict(target.INPUTS, {"tcec-provisional": (len(data), target.sha256(data).hexdigest())}):
            result, proof = target.transform_source(data, family="B", profile_id="tcec-provisional", lexer=lexer)
            self.assertIs(proof["selection_made_by_helper"], False)
            self.assertNotIn("production_selected", proof)
            self.assertIn(b'puts("preserved literal")', result)
            self.assertIn(b"p->v;", result)
            self.assertEqual(len(data) - len(result), 17)
            self.assertEqual(target.restore_source(result, proof, lexer=lexer), data)
            changed = bytearray(result)
            changed[0] ^= 1
            with self.assertRaises(ValueError):
                target.restore_source(bytes(changed), proof, lexer=lexer)
            proof["protected_gaps"][0]["bytes"] += 1
            with self.assertRaises(ValueError):
                target.restore_source(result, proof, lexer=lexer)

    def test_refuses_extra_old_token_and_target_collisions(self):
        for insertion in (b'zU;', b'"zU";', b'qY;', b'I v;', b'I e;'):
            data = fixture().replace(b"}void i(", insertion + b"}void i(")
            with self.subTest(insertion=insertion), self.assertRaises(ValueError):
                self.transform(data)
        with self.assertRaises(ValueError):
            self.transform(b"#define v 3\n" + fixture())

    def test_requires_full_named_source_pin_and_profile(self):
        data = fixture()
        with self.assertRaises(ValueError):
            target.transform_source(data, family="B", profile_id="tcec-provisional", lexer=lexer)
        with self.assertRaises(ValueError):
            target.transform_source(data, family="B", profile_id="test-p192", lexer=lexer)
        with self.assertRaises(ValueError):
            target.transform_source(data.decode("ascii"), family="B", profile_id="test-p4", lexer=lexer)
        with self.assertRaises(ValueError):
            target.transform_source(data, family="A", profile_id="test-p4")

    def test_duplicate_lexer_span_cannot_hide_a_missing_token(self):
        data = fixture()
        spans = list(lexer._identifier_spans(data.decode("ascii")))
        indices = [i for i, row in enumerate(spans) if row[2] == "zU"]
        spans[indices[1]] = spans[indices[0]]
        broken = SimpleNamespace(_identifier_spans=lambda _text: iter(spans))
        with patch.dict(target.INPUTS, {"tcec-provisional": (len(data), target.sha256(data).hexdigest())}):
            with self.assertRaisesRegex(ValueError, "ordinary identifier"):
                target.transform_source(data, family="B", profile_id="tcec-provisional", lexer=broken)

    def test_builtin_lexer_matches_reviewed_lexer_and_rejects_unsupported_input(self):
        data = fixture() + b'// comment\nI other=0x1234; char*s="x";\n'
        self.assertEqual(list(target._identifier_spans(data.decode("ascii"))),
                         list(lexer._identifier_spans(data.decode("ascii"))))
        with patch.dict(target.INPUTS, {"tcec-provisional": (len(data), target.sha256(data).hexdigest())}):
            one, proof = target.transform_source(data, family="B", profile_id="tcec-provisional")
            two, _ = target.transform_source(data, family="B", profile_id="tcec-provisional", lexer=lexer)
            self.assertEqual(one, two)
            self.assertEqual(target.restore_source(one, proof), data)
        for unsupported in (b'\\\n', b'??='):
            with self.subTest(unsupported=unsupported), self.assertRaises(ValueError):
                list(target._identifier_spans(unsupported.decode("ascii")))


if __name__ == "__main__":
    unittest.main()
