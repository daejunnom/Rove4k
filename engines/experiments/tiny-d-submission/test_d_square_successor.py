"""Pure tests for the one closed D square-successor projection.

The optional fixture is read from the explicit retained six-file source root.
No compiler, engine, package generator or admission implementation is invoked.
"""
import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("d_square_successor_under_test", HERE / "d_square_successor.py")
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)
SOURCE_ROOT = Path("/home/stemxstudio/rove4k-D-no-tid-P4-20261026-v1/carrier/generated-readable")


class PureSyntaxTests(unittest.TestCase):
    def test_mask_preserves_offsets_and_opaque_braces(self):
        data = b'void f(){char *s="} q++";char c=\'}\';/* { from=9; */q; // }\n}'
        masked = subject._mask(data)
        self.assertEqual(len(masked), len(data))
        self.assertEqual(masked.count(b"{"), 1)
        self.assertEqual(masked.count(b"}"), 1)
        self.assertEqual(masked.count(b"\n"), data.count(b"\n"))
        self.assertEqual(subject._block_end(masked, data.index(b"{")), len(data))

    def test_escaped_literals_are_opaque(self):
        data = b'"\\\" q++";\'\\\'\';q;'
        self.assertEqual(subject._index_reads(data, b"q", 100), [100 + data.rindex(b"q")])

    def test_unclosed_or_spliced_source_is_rejected(self):
        for data in (b'"unterminated', b"/* unterminated", b"'x", b'"a\nb"', b'"a\\\nb"', b"x\0"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                subject._mask(data)
        with self.assertRaises(ValueError):
            subject._block_end(b"{x", 0)

    def test_nested_block_extent(self):
        data = subject._mask(b'{if(x){f("}");}g();}tail')
        self.assertEqual(data[subject._block_end(data, 0):], b"tail")

    def test_index_mutation_address_escape_or_shadow_is_rejected(self):
        for data in (b"q++;", b"++q;", b"q--;", b"--q;", b"q=1;", b"q+=1;", b"q<<=1;",
                     b"f(&q);", b"int q=1;", b"q;goto label;", b"q;longjmp(e,1);"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                subject._index_reads(data, b"q", 0)

    def test_readonly_index_expressions(self):
        data = b'if(q==7)return q;int v=b[q];f(q);"q++";/* &q */'
        self.assertEqual(len(subject._index_reads(data, b"q", 0)), 4)

    def test_canonical_types_reject_bool_integer_and_tuple_substitution(self):
        self.assertFalse(subject._same({"value": 1}, {"value": True}))
        for value in ((1,), 1.0, {1: "x"}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                subject._json(value)


class SuccessorWitnessTests(unittest.TestCase):
    def test_all_three_ordered_sequences_and_terminal(self):
        witness = subject._witness()
        expected = [rank * 16 + file for rank in range(8) for file in range(8)]
        self.assertEqual(witness["old_dead_visits"], expected)
        self.assertEqual(witness["old_scalar_walk_visits"], expected)
        self.assertEqual(witness["successor_visits"], expected)
        self.assertEqual(witness["exit"], 128)
        self.assertEqual(witness["largest_addition"], 128)
        self.assertEqual(witness["successor_steps"][-1], [119, 128])

    def test_continue_enters_same_next_meaningful_square(self):
        for value in subject._witness()["successor_visits"]:
            old = value + 1
            if old < 128 and old & 0x88:
                old += 8
            self.assertEqual((value + 9) & ~8, old)

    def test_clearing_bit7_would_break_terminal_contract(self):
        self.assertEqual((119 + 9) & ~8, 128)
        self.assertEqual((119 + 9) & ~0x88, 0)


class ActualClosedSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE_ROOT.is_dir():
            raise unittest.SkipTest("explicit retained six-file source fixture is unavailable")
        cls.files = {name: (SOURCE_ROOT / name).read_bytes() for name in subject.INPUTS}
        subject.transform(cls.files)

    def test_exact_six_inputs_and_only_two_edits(self):
        output, proof = subject.transform(self.files)
        self.assertEqual(len(output["board.c"]), 10320)
        self.assertEqual(len(self.files["board.c"]) - len(output["board.c"]), 41)
        self.assertEqual(len(proof["projection"]["edits"]), 2)
        self.assertEqual([(r["begin"], r["end"]) for r in proof["projection"]["edits"]], [(1334, 1370), (6302, 6380)])
        self.assertEqual(len(proof["projection"]["protected_gaps"]), 3)
        for name in set(self.files) - {"board.c"}:
            self.assertEqual(output[name], self.files[name])

    def test_complete_inverse_and_canonical_proof(self):
        output, proof = subject.transform(self.files)
        self.assertEqual(subject.restore(output, proof), self.files)
        self.assertEqual(subject.transform(self.files), (output, proof))
        self.assertTrue(proof["full_inverse"])
        for name in ("native_identity_claimed", "semantics_qualified", "rules_qualified", "runtime_qualified", "size_qualified", "selected"):
            self.assertIs(proof[name], False)

    def test_every_protected_complement_matches_actual_bytes(self):
        output, proof = subject.transform(self.files)
        before, after = self.files["board.c"], output["board.c"]
        old_at = new_at = 0
        gaps = []
        for row in proof["projection"]["edits"]:
            gap = before[old_at:row["begin"]]
            self.assertEqual(after[new_at:row["target"]], gap)
            gaps.append(subject.pin(gap))
            old_at = row["end"]; new_at = row["target"] + len(row["after"].encode())
        self.assertEqual(after[new_at:], before[old_at:])
        gaps.append(subject.pin(before[old_at:]))
        self.assertEqual(gaps, proof["projection"]["protected_gaps"])

    def test_HQ_DEV_and_later_full128_validation_are_untouched(self):
        output, proof = subject.transform(self.files)
        old, new = self.files["board.c"], output["board.c"]
        self.assertEqual(old.count(subject.WALK_BEFORE), 2)
        self.assertEqual(new.count(subject.WALK_BEFORE), 1)
        self.assertEqual(new[4529 - 8:6231 - 8], old[4529:6231])
        self.assertEqual(new[7879 - 41:], old[7879:])
        self.assertTrue(proof["scope"]["all_128_entry_DEV_validation_retained"])
        self.assertIn(b"for(int q=0;q<128;q++)", new[7879 - 41:])

    def test_control_targets_and_index_read_roles(self):
        _, proof = subject.transform(self.files)
        dead, walk = proof["scope"]["dead"], proof["scope"]["scalar_walk"]
        self.assertEqual(len(dead["controls"]["return"]), 4)
        self.assertEqual(dead["controls"]["continue"], [])
        self.assertEqual(dead["controls"]["break"], [])
        self.assertEqual(walk["controls"], {"continue": [6429], "break": [7054, 7162], "return": [6980]})
        self.assertFalse(dead["index_writes_or_address_escape"])
        self.assertFalse(walk["index_writes_or_address_escape"])

    def test_mutated_missing_extra_or_mutable_input_is_rejected(self):
        for name in subject.INPUTS:
            changed = dict(self.files)
            changed[name] += b" "
            with self.subTest(name=name), self.assertRaises(ValueError):
                subject.transform(changed)
        for changed in ({k: v for k, v in self.files.items() if k != "tiny.h"},
                        dict(self.files, extra=b"x"), dict(self.files, **{"board.c": bytearray(self.files["board.c"])})):
            with self.assertRaises(ValueError):
                subject.transform(changed)

    def test_modified_proof_fields_or_complement_are_rejected(self):
        output, proof = subject.transform(self.files)
        mutations = []
        for field in ("kind", "source_contract"):
            changed = deepcopy(proof); changed[field] += "x"; mutations.append(changed)
        for field in ("native_identity_claimed", "semantics_qualified", "rules_qualified", "runtime_qualified", "size_qualified", "selected"):
            changed = deepcopy(proof); changed[field] = True; mutations.append(changed)
        for field in ("before", "after", "role"):
            changed = deepcopy(proof); changed["projection"]["edits"][0][field] += "x"; mutations.append(changed)
        for field in ("begin", "end", "target"):
            changed = deepcopy(proof); changed["projection"]["edits"][0][field] += 1; mutations.append(changed)
        changed = deepcopy(proof); changed["projection"]["protected_gaps"][0]["sha256"] = "0" * 64; mutations.append(changed)
        changed = deepcopy(proof); changed["witness"]["exit"] = 0; mutations.append(changed)
        changed = deepcopy(proof); changed["witness"]["padding_mask"] = 0x88; mutations.append(changed)
        changed = deepcopy(proof); changed["witness"]["visits"] = True; mutations.append(changed)
        changed = deepcopy(proof); changed["projection"]["edits"] = tuple(changed["projection"]["edits"]); mutations.append(changed)
        changed = deepcopy(proof); changed["unreviewed"] = True; mutations.append(changed)
        for changed in mutations:
            with self.subTest(index=mutations.index(changed)), self.assertRaises(ValueError):
                subject.restore(output, changed)

    def test_changed_output_or_unchanged_file_cannot_restore(self):
        output, proof = subject.transform(self.files)
        for name in output:
            changed = dict(output); changed[name] += b" "
            with self.subTest(name=name), self.assertRaises(ValueError):
                subject.restore(changed, proof)


@unittest.skipUnless(sys.platform == "linux", "the cost-only driver deliberately requires Linux resource")
class DriverOfflineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("d_square_successor_driver_offline", HERE / "probe_d_square_successor.py")
        cls.driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.driver)

    def test_constants_bind_exact_retained_provenance(self):
        if not SOURCE_ROOT.is_dir():
            self.skipTest("explicit retained provenance fixture is unavailable")
        root = SOURCE_ROOT.parent.parent
        qualification = (root / "qualification.json").read_bytes()
        startup = (root / "startup-results.json").read_bytes()
        driver = self.driver
        self.assertEqual(driver.pin(qualification), driver.expected(driver.QUALIFICATION_PIN))
        self.assertEqual(driver.pin(startup), driver.expected(driver.STARTUP_PIN))
        parent = json.loads(qualification)["admission"]
        self.assertEqual(driver.FLAGS, parent["flags"])
        self.assertEqual(driver.UNITS, parent["units"])
        self.assertEqual(driver.LEGACY, parent["identifier_composition"]["legacy"])
        self.assertEqual(len(driver.LEGACY.values()), len(set(driver.LEGACY.values())))
        selected = next(row for row in json.loads(startup)["cases"] if row["name"] == "no-tid")
        self.assertEqual(selected["shipping"], {name: driver.expected(value) for name, value in driver.SHIPPING.items()})
        self.assertEqual(selected["native"][0]["linked"], driver.expected(driver.IDENTITY["linked"]))
        self.assertEqual(selected["native"][0]["stripped"], driver.expected(driver.IDENTITY["native"]))
        self.assertEqual({row["route"]: row["whole"] for row in selected["packages"]},
                         {name: driver.expected(value) for name, value in driver.WHOLE.items()})

    def test_strict_decoder_rejects_incomplete_or_trailing_payload(self):
        for eof, unused in ((True, b""), (False, b""), (True, b"trailing")):
            decoder = SimpleNamespace(eof=eof, unused_data=unused, decompress=lambda data: b"decoded")
            with self.subTest(eof=eof, unused=unused), patch.object(self.driver.lzma, "LZMADecompressor", return_value=decoder):
                if eof and not unused:
                    self.assertEqual(self.driver.strict_decode(b"synthetic"), b"decoded")
                else:
                    with self.assertRaises(ValueError):
                        self.driver.strict_decode(b"synthetic")

    def inverse_fixture(self, route, *, decoded=None, header_bytes=6):
        files, flags, native = {"main.c": b"int x;"}, ["-Os"], b"native-image"
        wanted = dict(files={"main.c": "int x;"}, flags=flags, units=self.driver.UNITS)
        if decoded is None:
            if route == "source-jit":
                decoded = json.dumps(wanted).encode()
            elif route == "packed-xz-bcj":
                decoded = native
            else:
                decoded = ("import os\nb=" + repr(wanted) + "\nx=0\nx=1\n").encode()
        package = SimpleNamespace(NATIVE_CODE="native-envelope", SOURCE_CODE="source-envelope",
            envelope=lambda code, payload: (b"header" + payload, b"header"))
        with patch.object(self.driver, "strict_decode", return_value=decoded):
            return self.driver.inverse(b"headerpayload", {"header_bytes": header_bytes}, route,
                                       files, flags, native, package)

    def test_all_three_inverse_routes_without_real_compression(self):
        for route in ("source-jit", "source-jit-compressed", "packed-xz-bcj"):
            with self.subTest(route=route):
                record = self.inverse_fixture(route)
                self.assertTrue(record["strict_EOF"])
                self.assertTrue(record["complete_input_inverse"])
                self.assertEqual(record["header"], self.driver.pin(b"header"))
                self.assertEqual(record["payload"], self.driver.pin(b"payload"))

    def test_inverse_rejects_wrong_native_files_literal_and_boundary(self):
        for route, decoded in (("packed-xz-bcj", b"other-native"), ("source-jit", b"{}"),
                               ("source-jit-compressed", b"import os\nb={}\nx=0\nx=1\n")):
            with self.subTest(route=route), self.assertRaises(ValueError):
                self.inverse_fixture(route, decoded=decoded)
        with self.assertRaises(ValueError):
            self.inverse_fixture("source-jit", header_bytes=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    args, rest = parser.parse_known_args()
    SOURCE_ROOT = args.source_root
    unittest.main(argv=[sys.argv[0], *rest])
