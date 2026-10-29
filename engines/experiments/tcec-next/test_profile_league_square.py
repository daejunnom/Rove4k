import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


league = load("league_square_test", "profile_league_square.py")
scan = load("league_scan_test", "profile_scan.py")


class LeagueSquareTests(unittest.TestCase):
    def test_source_contract_and_pinned_families(self):
        self.assertEqual(set(league.INPUTS), {(family, profile) for family in "AC" for profile in ("test-p16", "test-p192")})
        self.assertEqual(set(league.INPUTS), set(league.OUTPUTS))
        for key in league.INPUTS:
            self.assertEqual(league.INPUTS[key][0] - league.OUTPUTS[key][0], 29)
            self.assertEqual(len(league.INPUTS[key][1]), 64)
            self.assertEqual(len(league.OUTPUTS[key][1]), 64)

    def test_reversible_projection_and_tamper_checks(self):
        for family in "AC":
            spans = scan.SPANS[family]
            source = b"header\n" + spans[0][1].encode() + b"body1}\n" + spans[1][1].encode() + b"body2}\n"
            expected, _, _ = scan._project(source, spans)
            key = (family, "test-p16")
            with self.subTest(family=family), patch.dict(league.INPUTS, {key: tuple(league._pin(source).values())}), \
                    patch.dict(league.OUTPUTS, {key: tuple(league._pin(expected).values())}):
                result, proof = league.transform_source(source, family=family, profile_id=key[1])
                self.assertEqual(result, expected)
                self.assertEqual(league.restore_source(result, proof), source)
                self.assertFalse(proof["production_selected"])
                self.assertFalse(proof["runtime_qualified"])
                with self.assertRaises(ValueError):
                    league.transform_source(source + b"x", family=family, profile_id=key[1])
                with self.assertRaises(ValueError):
                    league.restore_source(result + b"x", proof)
                with self.assertRaises(ValueError):
                    league.restore_source(result, {**proof, "runtime_qualified": True})

    def test_wrong_domain_and_duplicate_scan_rejected(self):
        for family in ("B", "E", "F", "D"):
            with self.subTest(family=family), self.assertRaises(ValueError):
                league.transform_source(b"", family=family, profile_id="test-p16")
        source = b"\n".join(sp[1].encode() for sp in scan.SPANS["A"])
        duplicate = source + scan.SPANS["A"][0][1].encode()
        key = ("A", "test-p16")
        with patch.dict(league.INPUTS, {key: tuple(league._pin(duplicate).values())}), self.assertRaises(ValueError):
            league.transform_source(duplicate, family=key[0], profile_id=key[1])


if __name__ == "__main__":
    unittest.main()
