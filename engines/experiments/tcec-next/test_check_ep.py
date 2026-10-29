"""Pure fixed-case/render contracts; this module never compiles or runs C.

Positive full-source checks require caller-supplied actual selected source bytes.
No synthetic source is admitted by replacing compact_ep's finite source pins.
"""
import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


check = load("ep_fixture_test_owner", HERE / "check_ep.py")
ep = load("ep_fixture_source_owner", HERE / "compact_ep.py")
projection = load("ep_fixture_projection_owner", HERE / "spelling_compound.py")
oracle = load("ep_fixture_independent_oracle", HERE.parent.parent / "tests" / "chess_oracle.py")


def check_actual_source(source, *, family, profile_id):
    """Generate only from genuine pinned source; do not execute the emitted TU."""
    fixture, metadata = check.render_fixture(source, family=family,
        profile_id=profile_id, ep=ep, projection=projection, oracle=oracle)
    candidate, proof = ep.transform_source(source, family=family,
        profile_id=profile_id, projection=projection)
    old = proof["edits"][0]["before"].encode("ascii")
    renamed = old.replace(b"static void D(", b"static void rv_ep_original(", 1)
    expected_prefix = b"#define main rv_ep_engine_main\n" + candidate + b"\n#undef main\n"
    if (not fixture.startswith(expected_prefix + renamed + b"\n")
            or fixture.count(b"static void rv_ep_original(") != 1
            or metadata["fixture"] != check.pin(fixture)
            or metadata["control"] != check.pin(source)
            or metadata["expected_normalizer_pairs"] != 192
            or metadata["expected_direct_trials"] != 160
            or metadata["C_semantics_executed"] is not False):
        raise ValueError("actual source/fixture binding or closed case coverage differs")
    return dict(family=family, profile_id=profile_id, fixture=metadata["fixture"],
        control=metadata["control"], candidate=metadata["candidate"],
        expected_normalizer_pairs=metadata["expected_normalizer_pairs"],
        expected_direct_trials=metadata["expected_direct_trials"],
        actual_original_slice_preserved=True, C_semantics_executed=False,
        runtime_qualified=False)


class EPFixtureContracts(unittest.TestCase):
    def test_closed_valid_FEN_oracle_EP_sets_and_adjacent_trials(self):
        cases = check.fixture_cases(oracle)
        self.assertEqual(len(cases), 12)
        self.assertEqual(sum(len(case["trials"]) for case in cases), 10)
        self.assertEqual(sum(len(case["legal_EP"]) for case in cases), 4)
        self.assertEqual({case["side"] for case in cases}, {-1, 1})
        for case in cases:
            self.assertEqual(len(case["pieces"]), 64)
            self.assertLessEqual(len(case["trials"]), 2)
            for trial in case["trials"]:
                self.assertEqual(trial["legal"], int(trial["move"] in case["legal_EP"]))
        for label in ("white-horizontal-discovery", "black-horizontal-discovery",
                "white-file-pin", "black-file-pin"):
            case = next(case for case in cases if case["label"] == label)
            self.assertGreaterEqual(case["raw_ep"], 0)
            self.assertEqual(case["expected_ep"], -1)
            self.assertEqual([trial["legal"] for trial in case["trials"]], [0])
        for label in ("white-first-pinned-second-legal", "black-first-pinned-second-legal"):
            case = next(case for case in cases if case["label"] == label)
            self.assertEqual([trial["legal"] for trial in case["trials"]], [0, 1])

    def test_half_hash_and_driver_scope_are_explicit(self):
        self.assertEqual(check.HALFMOVES, (0, 99, 100, 1000000))
        self.assertLess(max(check.HALFMOVES) + 1, 2147483647)
        self.assertEqual(check.HASH_MODES, ("piece-only", "state-bound", "zero", "unsigned-max"))
        driver = check._driver(check.fixture_cases(oracle))
        for token in (b"memset(&base,0,sizeof base)", b"base.e=rv_ep_cases[i].ep",
                b"p.h=(W)~(W)0", b"rv_ep_original(&old);D(&now)",
                b"memcmp(&old,&want,sizeof p)", b"memcmp(&now,&want,sizeof p)",
                b"memcmp(&p,&snapshot,sizeof p)", b"!!v(&p,MOVE(from,p.e,0),&child)"):
            self.assertIn(token, driver)
        for token in (b"@", b"mmap", b"calloc", b"malloc", b"pthread_create",
                b"rv_ep_engine_main(", b"q(&"):
            self.assertNotIn(token, driver)

    def test_renderer_refuses_unadmitted_control_source(self):
        for family, profile in (("A", "test-p4"), ("D", "test-p4"),
                ("C", "unknown"), ("C", "test-p4"), ("E", "tcec-provisional")):
            with self.assertRaises(ValueError):
                check.render_fixture(b"unadmitted", family=family, profile_id=profile,
                    ep=ep, projection=projection, oracle=oracle)


if __name__ == "__main__":
    unittest.main()
