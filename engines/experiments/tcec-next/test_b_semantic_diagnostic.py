import importlib.util
from pathlib import Path
import tempfile
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("b_semantic_diagnostic_test", HERE / "b_semantic_diagnostic.py")
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class DiagnosticTests(unittest.TestCase):
    def test_pins_inverse_and_tampering(self):
        base = b"prefix k=i+1;k<Z;k++ middle ((q+(q&7))/2) suffix"
        candidate = b"prefix k=i;k<Z;k++ middle ((q+(q&7))>>1) suffix"
        with mock.patch.object(d,"BASE",(len(base),d.pin(base)["sha256"])), mock.patch.object(d,"CANDIDATE",(len(candidate),d.pin(candidate)["sha256"])):
            self.assertEqual(d.transform(base), candidate)
            self.assertEqual(d.restore(candidate), base)
            with self.assertRaises(ValueError): d.transform(base+b"x")
            with self.assertRaises(ValueError): d.restore(candidate+b"x")
            with mock.patch.object(d,"CANDIDATE",(len(candidate),"0"*64)):
                with self.assertRaises(ValueError): d.transform(base)

    def test_missing_and_duplicate_anchor_fail_even_with_input_pin(self):
        for base in (b"no anchors", b"k=i+1;k<Z;k++ k=i+1;k<Z;k++ ((q+(q&7))/2)"):
            with mock.patch.object(d,"BASE",(len(base),d.pin(base)["sha256"])):
                with self.assertRaises(ValueError): d.transform(base)

    def test_bad_dependency_and_native_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"module.py"
            path.write_bytes(b"raise AssertionError('must not execute')")
            with self.assertRaises(ValueError): d.load_pinned_module("bad", path, "0"*64)
        with self.assertRaises(ValueError): d.validate_native("base", b"wrong native")
        with self.assertRaises(ValueError): d.validate_native("candidate", b"wrong native")

    def test_invalid_rules_rows_are_rejected(self):
        class Rules:
            def _compare_output(self, data, cases): return {"legal_moves_compared": 2858}
        cases = [{}]*105
        rows = [f"{i} perft2:1" for i in range(105)]
        with self.assertRaises(ValueError): d.validate_rules(("\n".join(rows)+"\n").encode(),cases,Rules())
        rows[0] = "99 perft2:1"
        with self.assertRaises(ValueError): d.validate_rules(("\n".join(rows)+"\n").encode(),cases,Rules())

    def test_search_output_requires_correct_case_order(self):
        good = "".join(f"{i} {depth} 0 a2a3 2\n" for i in range(14) for depth in (3,4)).encode()
        d.validate_search(good)
        with self.assertRaises(ValueError): d.validate_search(good.replace(b"0 3 0", b"7 3 0", 1))
        with self.assertRaises(ValueError): d.validate_search(good[:-8])

    def test_failed_command_refused(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError): d.execute([sys.executable,"-c","raise SystemExit(2)"],Path(td))

    def test_failed_run_does_not_write_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)/"source"; base.write_bytes(b"wrong")
            out = Path(td)/"result.json"
            with mock.patch("sys.argv",["diag","--baseline",str(base),"--output",str(out)]):
                with self.assertRaises(ValueError): d.main()
            self.assertFalse(out.exists())

if __name__ == "__main__": unittest.main()
