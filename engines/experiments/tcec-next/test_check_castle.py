"""Pure castle fixture contracts; no C/compiler/engine or synthetic admission.

Actual-source positives take caller-supplied pinned parents. The setup-template
and parser mocks below grant no C, native, raw-call-trace or runtime evidence.
"""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


check = load("castle_fixture_test_owner", HERE / "check_castle.py")
castle = load("castle_fixture_source_owner", HERE / "compact_castle.py")
projection = load("castle_fixture_projection_owner", HERE / "spelling_compound.py")
rules = load("castle_fixture_existing_rules", HERE / "profile_rules.py")
oracle = load("castle_fixture_independent_oracle", HERE.parent.parent / "tests/chess_oracle.py")


def check_actual_source(source, *, family, profile_id):
    """Render only from a genuine pinned parent, without executing its TU."""
    fixture, metadata = check.render_fixture(source, family=family, profile_id=profile_id,
        castle=castle, projection=projection, oracle=oracle, rules=rules)
    candidate, proof = castle.transform(source, family=family, profile_id=profile_id, projection=projection)
    standard, _ = rules.fixture_cases(oracle)
    original, renamed, wrapper = check._original_generator(source, proof, family=family, castle=castle)
    if (not fixture.startswith(b"#define main rv_rule_original_main\n" + candidate)
            or fixture.count(renamed) != 1 or metadata["control"] != check.pin(source)
            or metadata["candidate"] != check.pin(candidate) or metadata["fixture"] != check.pin(fixture)
            or metadata["original_generator"] != check.pin(original)
            or metadata["actual_T_wrapper"] != check.pin(wrapper)
            or metadata["coverage"]["standard_cases"] != len(standard)
            or metadata["actual_attack_call_trace"] is not False
            or metadata["C_semantics_executed"] is not False):
        raise ValueError("actual castle source/function/fixture binding differs")
    if any("board" in case for case in metadata["cases"]):
        raise ValueError("stored castle cases cannot contain live oracle Boards")
    json.dumps(metadata, sort_keys=True, allow_nan=False)
    return dict(family=family, profile_id=profile_id, control=metadata["control"],
        candidate=metadata["candidate"], fixture=metadata["fixture"], coverage=metadata["coverage"],
        actual_original_generator_preserved=True, C_semantics_executed=False,
        actual_attack_call_trace=False, runtime_qualified=False)


class CastleFixtureContracts(unittest.TestCase):
    def test_fixed_cases_keep_standard_paths_and_cover_discriminating_arms(self):
        cases, coverage = check.fixture_cases(oracle, rules=rules)
        standard, _ = rules.fixture_cases(oracle)
        self.assertEqual(coverage["standard_cases"], len(standard))
        for expected, actual in zip(standard, cases):
            self.assertEqual({key:actual[key] for key in ("label", "moves", "legal")},
                             {key:expected[key] for key in ("label", "moves", "legal")})
        targeted = cases[len(standard):]
        self.assertEqual(coverage["targeted_cases"], len(targeted))
        self.assertEqual(coverage["own_rights_masks"], {"white":[0, 1, 2, 3], "black":[0, 1, 2, 3]})
        self.assertTrue(all(case["moves"] == [] and len(case["pieces"]) == 64 for case in targeted))
        for colour in ("white", "black"):
            rank = "1" if colour == "white" else "8"
            by_label = {case["label"]:case for case in targeted}
            both = by_label[colour + "-rights-3"]
            self.assertEqual(both["expected_raw_castles"], ["e" + rank + "g" + rank, "e" + rank + "c" + rank])
            for direction, destination in (("kingside", "g"), ("queenside", "c")):
                move = "e" + rank + destination + rank
                transit = by_label[colour + "-" + direction + "-transit-attacked"]
                final = by_label[colour + "-" + direction + "-destination-attacked"]
                self.assertNotIn(move, transit["expected_raw_castles"])
                self.assertIn(move, final["expected_raw_castles"])
                self.assertNotIn(move, final["legal"])
                self.assertNotIn(move, [str(item) for item in final["board"].pseudo_moves()])
            for tag in ("home-check", "off-home-no-rights"):
                self.assertEqual(by_label[colour + "-" + tag]["expected_raw_castles"], [])
            self.assertTrue(all(colour + "-path-block-" + file in by_label for file in "fgbcd"))

    def test_setup_template_compares_raw_order_and_const_Board_without_engine_main(self):
        cases, coverage = check.fixture_cases(oracle, rules=rules)
        # A private template check, deliberately never a public admitted source.
        declarations = check._start_declarations(cases, coverage["standard_cases"], b"/* supplied original generator */")
        for token in (b"q(p);return", b"memset(p,0,sizeof *p)", b"b(p,(square/8)*16+square%8",
                b"p->h^=l(p);p->r=p->h", b"rv_castle_original_g(&left,old_moves,0,left.s)",
                b"g(&right,new_moves,0,right.s)", b"memcmp(old_moves,new_moves",
                b"memcmp(&left,&before", b"memcmp(&right,&before", b"king>=queen"):
            self.assertIn(token, declarations)
        for token in (b"@", b"pthread_create", b"malloc", b"calloc", b"mmap",
                      b"rv_rule_original_main(", b"int main("):
            self.assertNotIn(token, declarations)

    def test_renderer_rejects_unadmitted_source_and_foreign_context(self):
        for family, profile in (("A", check.PROFILE), ("C", check.PROFILE), ("E", check.PROFILE),
                                ("B", check.PROFILE), ("D", check.PROFILE), ("A", "test-p4")):
            with self.subTest(family=family, profile=profile), self.assertRaises(ValueError):
                check.render_fixture(b"unadmitted", family=family, profile_id=profile,
                    castle=castle, projection=projection, oracle=oracle, rules=rules)

    def test_stdout_parser_reuses_existing_rules_checker_and_preserves_scope(self):
        cases = [dict(label="parser-fixture", moves=[], legal=["a1a2"])]
        raw = b"0 a1a2\n"
        expected = dict(cases=1, legal_moves_compared=1, stdout=check.pin(raw), legal_sets_equal=True)
        comparison = SimpleNamespace(_compare_output=Mock(return_value=expected))
        metadata = dict(schema=check.SCHEMA, cases=cases, source_only=True, original_entry_called=False,
            TT_allocated=False, actual_attack_call_trace=False, coverage=dict(standard_cases=1, targeted_cases=0))
        observed = check.check_output(raw, metadata, rules=comparison)
        comparison._compare_output.assert_called_once_with(raw, cases)
        self.assertEqual({key:observed[key] for key in expected}, expected)
        self.assertFalse(observed["actual_attack_call_trace"])
        self.assertFalse(observed["runtime_qualified"])
        for key, value in (("source_only", 1), ("original_entry_called", 0),
                           ("TT_allocated", True), ("actual_attack_call_trace", True), ("cases", {})):
            changed = copy.deepcopy(metadata)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                check.check_output(raw, changed, rules=comparison)
        with self.assertRaises(ValueError):
            check.check_output(bytearray(raw), metadata, rules=comparison)


if __name__ == "__main__":
    unittest.main()
