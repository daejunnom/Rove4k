"""Pure lexical fixtures only; never invoke a compiler or an engine."""

import hashlib
import importlib.util
import json
from pathlib import Path
import re
from types import SimpleNamespace
import unittest


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_HERE = Path(__file__).resolve().parent
policy = _load("fixed_alpha_policy_test", _HERE / "policy.py")
_LEXER_PATH = _HERE / "control" / "engines" / "scripts" / "rename_c.py"
if hashlib.sha256(_LEXER_PATH.read_bytes()).hexdigest() != "9d7d09e2787cfda21701384be94ed00d588165574da5d8aacdf731fcb317cbe5":
    raise ValueError("frozen test lexer SHA-256 mismatch")
lexer = _load("fixed_alpha_lexer_test", _LEXER_PATH)


class FixedPolicyTests(unittest.TestCase):
    def test_code_tokens_only_and_source_immutable(self):
        source = (b'#include <Board.h>\n#define KEEP Board\n'
                  b'#define SHOW(x) #x\n#define JOIN(x) x##Board\n'
                  b'typedef struct{int score;}Board;\n'
                  b'Board board;int main(){int Boarder=0;board.score=WORKERS+TT_BITS;'
                  b'puts("Board score WORKERS TT_BITS");/* score */return Boarder;}\n')
        original = bytes(source)
        candidate, counts, opaque = policy._rewrite(
            source, {"Board": "za", "score": "zb", "WORKERS": "2", "TT_BITS": "18"}, lexer=lexer)
        expected = source.replace(b";}Board;", b";}za;").replace(b"\nBoard board;", b"\nza board;")
        expected = expected.replace(b"int score;", b"int zb;").replace(b"board.score=WORKERS+TT_BITS", b"board.zb=2+18")
        self.assertEqual(candidate, expected)
        self.assertEqual(source, original)
        self.assertEqual(dict(counts), {"Board": 2, "score": 2, "WORKERS": 1, "TT_BITS": 1})
        self.assertEqual(policy._opaque_parts(candidate.decode()), opaque)

    def test_phase_two_opaque_regions_and_prefixed_literals(self):
        source = (b'#define X score \\\n+score\n// score \\\n+score\n'
                  b'/* score */int score;const char*s=u8"score\\\"";'
                  b'const int*c=L\'s\';score=1;\n')
        candidate, counts, opaque = policy._rewrite(source, {"score": "za"}, lexer=lexer)
        self.assertEqual(candidate, source.replace(b"int score;", b"int za;").replace(b";score=1;", b";za=1;"))
        self.assertEqual(counts["score"], 2)
        self.assertEqual(policy._opaque_parts(candidate.decode()), opaque)

    def test_alias_freshness_in_every_raw_region(self):
        for fragment in (b"int za;", b'puts("za");', b"/* za */", b"// za\n", b"#define KEEP za\n"):
            with self.subTest(fragment=fragment), self.assertRaisesRegex(ValueError, "not fresh"):
                policy._rewrite(fragment + b"int score;", {"score": "za"}, lexer=lexer)
        with self.assertRaisesRegex(ValueError, "not fresh"):
            policy._rewrite(b'puts("z\\\na");int score;', {"score": "za"}, lexer=lexer)

    def test_aliases_injective_and_keywords_reserved(self):
        with self.assertRaisesRegex(ValueError, "injective"):
            policy._rewrite(b"int score,depth;", {"score": "za", "depth": "za"}, lexer=lexer)
        with self.assertRaisesRegex(ValueError, "not fresh"):
            policy._rewrite(b"int score;", {"score": "for"}, lexer=lexer)
        with self.assertRaisesRegex(ValueError, "not fresh"):
            policy._rewrite(b"int score;", {"score": "depth", "depth": "za"}, lexer=lexer)

    def test_replacement_methods_must_agree(self):
        wrong = SimpleNamespace(_KEYWORDS=lexer._KEYWORDS,
                                _identifier_spans=lexer._identifier_spans,
                                _replace=lambda files, old, new: dict(files))
        with self.assertRaisesRegex(ValueError, "disagree"):
            policy._rewrite(b"int score;", {"score": "za"}, lexer=wrong)

    def test_independent_opaque_check_rejects_unsafe_lexer(self):
        def spans(text):
            return ((m.start(), m.end(), m.group()) for m in re.finditer(r"[A-Za-z_][A-Za-z_0-9]*", text))

        def replace(files, old, new):
            return {name: re.sub(r"\b" + old + r"\b", new, data.decode()).encode()
                    for name, data in files.items()}

        wrong = SimpleNamespace(_KEYWORDS=lexer._KEYWORDS, _identifier_spans=spans, _replace=replace)
        with self.assertRaisesRegex(ValueError, "bytes changed"):
            policy._rewrite(b'int score;puts("score");', {"score": "za"}, lexer=wrong)

    def test_overlapping_unedited_spans_rejected(self):
        wrong = SimpleNamespace(_KEYWORDS=lexer._KEYWORDS,
                                _identifier_spans=lambda text: iter(((0, 3, "int"), (0, 3, "int"))),
                                _replace=lexer._replace)
        with self.assertRaisesRegex(ValueError, "overlapping"):
            policy._rewrite(b"int score;", {"score": "za"}, lexer=wrong)

    def test_trigraph_and_malformed_opaque_input_rejected(self):
        for source in (b"??=define X score\nint score;", b"int score;/*", b'int score;"oops'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                policy._rewrite(source, {"score": "za"}, lexer=lexer)

    def test_public_api_has_no_fixture_or_modified_source_admission(self):
        for family in ("A", "F", "b", "", None):
            with self.subTest(family=family), self.assertRaisesRegex(ValueError, "unknown"):
                policy.transform_source(b"int score;", family=family, lexer=lexer)
        for family in ("B", "C", "E"):
            with self.subTest(family=family), self.assertRaisesRegex(ValueError, "input.*mismatch"):
                policy.transform_source(b"int score;", family=family, lexer=lexer)
        with self.assertRaisesRegex(ValueError, "immutable bytes"):
            policy.transform_source(bytearray(b"int score;"), family="B", lexer=lexer)

    def test_literal_policy_identity_and_internal_arithmetic(self):
        raw = (_HERE / "policy.json").read_bytes()
        self.assertNotIn(b"\r", raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), policy._POLICY_SHA256)
        document = json.loads(raw)
        self.assertEqual(document["source_report_sha256"], "7a49e468018e026e2ea95676bf09eeef7ab2e3c7b07c5c8cb0e20170288cfb9d")
        self.assertEqual(set(document["families"]), {"B", "C", "E"})
        mapping, resources = document["mapping"], document["resource_literals"]
        self.assertEqual(len(mapping), 89)
        self.assertEqual(len(set(mapping.values())), 89)
        self.assertTrue(all(len(new) == 2 for new in mapping.values()))
        self.assertEqual(resources, {"WORKERS": "2", "TT_BITS": "18"})
        self.assertFalse(set(mapping) & set(document["symbol_bearing_spellings_retained"]))
        for family, spec in document["families"].items():
            with self.subTest(family=family):
                self.assertEqual(set(spec["alpha_counts"]), set(mapping))
                self.assertEqual(spec["resource_counts"], {"WORKERS": 7, "TT_BITS": 3})
                self.assertEqual(spec["mapping_used"], sum(n > 0 for n in spec["alpha_counts"].values()))
                alpha = sum((len(old) - len(new)) * spec["alpha_counts"][old] for old, new in mapping.items())
                self.assertEqual(alpha, spec["alpha_saved_bytes"])
                self.assertEqual(spec["resource_saved_bytes"], 57)
                self.assertEqual(spec["source"]["bytes"] - spec["candidate"]["bytes"], alpha + 57)
                self.assertEqual(spec["source_edits_count"], sum(spec["alpha_counts"].values()) + 10)
                for kind in ("source", "candidate", "expected_old_native", "expected_old_whole"):
                    self.assertRegex(spec[kind]["sha256"], r"^[0-9a-f]{64}$")
                    self.assertGreater(spec[kind]["bytes"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
