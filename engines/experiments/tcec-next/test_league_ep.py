"""Boundaries and actual-source checks for the opt-in league EP stage.

Positive source checks require the real pinned producer artifact; no engine
source is embedded here. Compilation and chess rules remain separate checks.
"""
import copy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


league = load("league_ep_test_owner", HERE / "league_ep.py")
ep = load("league_ep_test_existing_owner", HERE / "compact_ep.py")
projection = load("league_ep_test_projection", HERE / "spelling_compound.py")


def check_actual_source(source, *, family, profile_id):
    candidate, proof = league.transform_source(source, family=family, profile_id=profile_id,
                                               ep=ep, projection=projection)
    if league.restore_source(candidate, proof, ep=ep, projection=projection) != source:
        raise ValueError("league EP inverse differs")
    row = proof["edits"][0]
    before, after = row["before"].encode("ascii"), row["after"].encode("ascii")
    i, o = row["input_begin"], row["output_begin"]
    if len(proof["edits"]) != 1 or len(proof["protected_gaps"]) != 2:
        raise ValueError("league EP must own exactly one region")
    if source[i:i + len(before)] != before or candidate[o:o + len(after)] != after:
        raise ValueError("league EP source spans differ")
    for old, new, gap in ((source[:i], candidate[:o], proof["protected_gaps"][0]),
                          (source[i + len(before):], candidate[o + len(after):], proof["protected_gaps"][1])):
        if old != new or league.pin(old) != {key: gap[key] for key in ("bytes", "sha256")}:
            raise ValueError("league EP protected gap differs")
    for change in ("resources_changed", "models_changed", "features_removed", "runtime_qualified",
                   "native_identity_claimed", "production_selected", "timing_equivalence_claimed"):
        modified = copy.deepcopy(proof)
        modified[change] = True
        try:
            league.restore_source(candidate, modified, ep=ep, projection=projection)
        except ValueError:
            pass
        else:
            raise ValueError("tampered league EP proof accepted: " + change)
    for key in ("protected_maker",):
        modified = copy.deepcopy(proof)
        modified[key]["sha256"] = "0" * 64
        try:
            league.restore_source(candidate, modified, ep=ep, projection=projection)
        except ValueError:
            pass
        else:
            raise ValueError("tampered league EP proof accepted: " + key)
    malformed = copy.deepcopy(proof)
    malformed["edits"] = [{}]
    try:
        league.restore_source(candidate, malformed, ep=ep, projection=projection)
    except ValueError:
        pass
    else:
        raise ValueError("malformed league EP inverse edits accepted")
    for mutated in (source + b" ", source[:-1]):
        try:
            league.transform_source(mutated, family=family, profile_id=profile_id, ep=ep, projection=projection)
        except ValueError:
            pass
        else:
            raise ValueError("modified league resource projection accepted")
    return candidate, proof


class LeagueEPBoundaries(unittest.TestCase):
    def test_input_set_is_exactly_four_test_profiles(self):
        self.assertEqual(set(league.INPUTS), {(f, p) for f in "CE" for p in ("test-p16", "test-p192")})

    def test_other_families_profiles_and_types_rejected(self):
        for family, profile in (("A", "test-p16"), ("B", "test-p16"), ("D", "test-p16"),
                                ("F", "test-p16"), ("C", "test-p4"), (True, "test-p16"),
                                ("E", True)):
            with self.subTest(family=family, profile=profile), self.assertRaisesRegex(ValueError, "finite C/E"):
                league.transform_source(b"x", family=family, profile_id=profile, ep=ep, projection=projection)

    def test_input_pin_and_type_are_required(self):
        for family, profile in league.INPUTS:
            for source in (b"x", bytearray(b"x"), "x", None):
                with self.subTest(family=family, profile=profile, source=type(source)), self.assertRaisesRegex(ValueError, "exact observed"):
                    league.transform_source(source, family=family, profile_id=profile, ep=ep, projection=projection)

    def test_complete_bound_proof_is_required(self):
        for candidate, proof in ((b"x", {}), (bytearray(b"x"), {}),
                                 (b"x", {"schema": league.SCHEMA, "edits": [], "output": league.pin(b"y")})):
            with self.assertRaisesRegex(ValueError, "complete proof"):
                league.restore_source(candidate, proof, ep=ep, projection=projection)


if __name__ == "__main__":
    unittest.main()
