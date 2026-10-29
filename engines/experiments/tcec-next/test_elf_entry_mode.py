"""Pure finite entry-source checks; no factory, compiler, codec or engine run.

Synthetic fixtures exercise only the internal one-span mechanism. They never
replace the public fifteen-source admission pins. Actual admitted-source roundtrips
belong to the consumer's separately authorized exact-input verification.
"""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest


HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


entry = load("finite_elf_entry_tests", HERE / "elf_entry_mode.py")
projection = load("finite_elf_entry_splice_tests", HERE / "spelling_compound.py")


def fixture(family="A", tail=None):
    c = entry.CONTEXT[family]
    macros = []
    for alias, keyword in ((c["integer"], "int"), (c["returned"], "return"),
                           (c["conditional"], "if")):
        if alias != keyword:
            macros.append(f"#define {alias} {keyword}\n")
    # B's equal spellings in a previous function must remain valid and protected.
    earlier = f"{c['integer']} earlier({c['integer']} {c['argc']}){{{c['returned']} {c['argc']};}}\n"
    body = tail if tail is not None else f"char*s=\"{c['argc']} {c['argv']}\";/* {c['argv']} */{c['returned']} 0;}}\n"
    return ("".join(macros) + earlier + c["integer"] + " " + entry._before(family) + body).encode("ascii")


class FiniteElfEntry(unittest.TestCase):
    def test_exact_fifteen_profile_domain_and_fixed_helper_identity(self):
        profiles = ("test-p4", "test-p28", "tcec-provisional")
        domain = {(family, profile) for family in "ABCEF" for profile in profiles}
        self.assertEqual(entry.PROFILES, profiles)
        self.assertEqual(set(entry.INPUTS), domain)
        self.assertEqual(set(entry.OUTPUTS), domain)
        self.assertEqual(entry.PROJECTION, dict(path="engines/experiments/tcec-next/spelling_compound.py",
            bytes=9472, sha256="4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce"))
        self.assertEqual(entry.pin((HERE / "spelling_compound.py").read_bytes()),
                         {name: entry.PROJECTION[name] for name in ("bytes", "sha256")})
        for key in domain:
            for table in (entry.INPUTS, entry.OUTPUTS):
                self.assertIs(type(table[key][0]), int)
                self.assertRegex(table[key][1], r"^[0-9a-f]{64}$")
            self.assertEqual(entry.OUTPUTS[key][0] - entry.INPUTS[key][0],
                             len(entry.AFTER) - len(entry._before(key[0])))

    def test_one_entry_edit_preserves_all_original_complement_bytes(self):
        for family in entry.FAMILIES:
            source = fixture(family)
            candidate, edits, gaps = entry._project(source, family=family, projection=projection)
            self.assertEqual(len(edits), 1)
            self.assertEqual(len(gaps), 2)
            before = entry._before(family).encode("ascii")
            self.assertEqual(candidate, source.replace(before, entry.AFTER.encode("ascii"), 1))
            self.assertEqual(entry._inverse(candidate, copy.deepcopy(edits), family=family,
                                           projection=projection), source)
            for gap in gaps:
                old = source[gap["input_begin"]:gap["input_begin"] + gap["bytes"]]
                new = candidate[gap["output_begin"]:gap["output_begin"] + gap["bytes"]]
                self.assertEqual(new, old)
                self.assertEqual(entry.pin(new), {name: gap[name] for name in ("bytes", "sha256")})

    def test_actual_family_aliases_and_b_parameter_spellings(self):
        self.assertEqual(entry._before("B"), "main(I v,char**w){W(remove(*w))l 2;")
        self.assertEqual(entry._before("C"), "main(int z0,char**z1){if(remove(*z1))return 2;")
        for family in entry.FAMILIES:
            c, source = entry.CONTEXT[family], fixture(family)
            for alias, keyword in ((c["integer"], "int"), (c["returned"], "return"),
                                   (c["conditional"], "if")):
                if alias != keyword:
                    changed = source.replace(f"#define {alias} {keyword}\n".encode(),
                                             f"#define {alias} wrong\n".encode(), 1)
                else:
                    changed = f"#define {alias} wrong\n".encode() + source
                with self.assertRaises(ValueError):
                    entry._entry_edit(changed, family)
            for keyword in ("int", "return", "if", "void"):
                with self.assertRaises(ValueError):
                    entry._entry_edit(f"#define {keyword} wrong\n".encode() + source, family)

    def test_unused_parameters_checked_only_in_retained_main_tail(self):
        for family in entry.FAMILIES:
            c = entry.CONTEXT[family]
            entry._entry_edit(fixture(family), family)
            for name in (c["argc"], c["argv"]):
                source = fixture(family, tail=f"{c['returned']} {name}!=0;}}\n")
                with self.assertRaises(ValueError):
                    entry._entry_edit(source, family)

    def test_missing_duplicate_wrong_signature_or_nonascii_source_rejected(self):
        source, before = fixture(), entry._before("A").encode()
        for changed in (source.replace(before, b"main(void){", 1), source + source,
                        source.replace(b"L main(", b"wrong main(", 1), source + b"\xff",
                        bytearray(source)):
            with self.assertRaises(ValueError):
                entry._entry_edit(changed, "A")

    def test_inverse_rejects_untyped_coordinates_and_changed_edit_fields(self):
        candidate, edits, _ = entry._project(fixture(), family="A", projection=projection)
        for field in ("input_begin", "output_begin"):
            for value in (True, 1.0, -1, len(candidate) + 1):
                changed = copy.deepcopy(edits)
                changed[0][field] = value
                with self.assertRaises(ValueError):
                    entry._inverse(candidate, changed, family="A", projection=projection)
        for field in ("before", "after", "role", "component"):
            for value in ("changed", 1, None):
                changed = copy.deepcopy(edits)
                changed[0][field] = value
                with self.assertRaises(ValueError):
                    entry._inverse(candidate, changed, family="A", projection=projection)
        for changed in ([], edits + edits, tuple(edits), [{**edits[0], "extra": True}],
                        [{key: value for key, value in edits[0].items() if key != "role"}]):
            with self.assertRaises(ValueError):
                entry._inverse(candidate, changed, family="A", projection=projection)
        with self.assertRaises(ValueError):
            entry._inverse(candidate.replace(b"main(void){", b"main(other){", 1), edits,
                           family="A", projection=projection)

    def test_public_admission_rejects_unknown_domain_and_synthetic_payloads(self):
        for family, profile in (("D", "test-p4"), ("F8", "test-p28"), ("A", "test-w256"),
                                ("A", "other"), (True, "test-p4"), ([], "test-p4")):
            with self.assertRaises(ValueError):
                entry.transform_source(b"", family=family, profile_id=profile, projection=projection)
        for family in entry.FAMILIES:
            for profile in entry.PROFILES:
                for source in (fixture(family), bytearray(fixture(family)), b"wrong"):
                    with self.assertRaises(ValueError):
                        entry.transform_source(source, family=family, profile_id=profile, projection=projection)

    def test_public_restore_rejects_unpinned_candidate_with_any_proof_metadata(self):
        source = fixture()
        candidate, edits, gaps = entry._project(source, family="A", projection=projection)
        proof = dict(schema=entry.SCHEMA, family="A", profile_id="test-p4",
            representation=entry.REPRESENTATION, entry_cleanup="none", input=entry.pin(source),
            output=entry.pin(candidate), projection=dict(entry.PROJECTION), edits=edits,
            protected_gaps=gaps, full_inverse=True)
        for changed in (proof, {}, {**proof, "schema": "old-self-unlink"},
                        {**proof, "representation": "source-jit"}, {**proof, "entry_cleanup": "private-path"},
                        {**proof, "projection": {**entry.PROJECTION, "bytes": True}},
                        {**proof, "extra": True}, {**proof, "edits": []}):
            with self.assertRaises(ValueError):
                entry.restore_source(candidate, changed, projection=projection)

    def test_projection_rejects_incomplete_or_wrong_schema_owner(self):
        for helper in (None, SimpleNamespace(SCHEMA=projection.SCHEMA),
                       SimpleNamespace(SCHEMA="wrong", _splice=projection._splice,
                                       _inverse_edits=projection._inverse_edits)):
            with self.assertRaises(ValueError):
                entry._project(fixture(), family="A", projection=helper)

    def test_proof_json_preserves_types_and_rejects_noncanonical_values(self):
        self.assertNotEqual(entry._json({"value": 1}), entry._json({"value": True}))
        self.assertEqual(entry._json({"b": [], "a": False}), '{"a":false,"b":[]}')
        for value in (1.0, float("nan"), float("inf"), object(), (1,), {1: "key"}):
            with self.assertRaises(ValueError):
                entry._json({"value": value})
        cyclic = []
        cyclic.append(cyclic)
        with self.assertRaises(ValueError):
            entry._json(cyclic)


if __name__ == "__main__":
    unittest.main()
