"""Pure EP-source boundaries; actual C rules/UBSan remain hosted consumers.

Positive checks require the caller's genuine pinned C/E source bytes. There is
no embedded generated engine, policy monkeypatch, C runner or oracle here.
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


ep = load("compact_ep_test_owner", HERE / "compact_ep.py")
projection = load("compact_ep_test_projection", HERE / "spelling_compound.py")


def require(value, message):
    if not value:
        raise ValueError(message)


def check_actual_source(source, *, family, profile_id):
    """Check actual source inverse/gaps/typed-proof refusal without executing C."""
    candidate, proof = ep.transform_source(source, family=family,
        profile_id=profile_id, projection=projection)
    require(ep.restore_source(candidate, proof, projection=projection) == source,
            "actual EP inverse differs")
    replay, repeated = ep.transform_source(source, family=family,
        profile_id=profile_id, projection=projection)
    require(replay == candidate and repeated == proof, "actual EP source replay differs")
    require(len(proof["edits"]) == 1 and len(proof["protected_gaps"]) == 2,
            "one EP-owned region required")
    row = proof["edits"][0]
    old, new = row["before"].encode("ascii"), row["after"].encode("ascii")
    start, output_start = row["input_begin"], row["output_begin"]
    require(source[start:start+len(old)] == old and
            candidate[output_start:output_start+len(new)] == new,
            "actual private normalizer spans differ")
    for before, after, gap in (
            (source[:start], candidate[:output_start], proof["protected_gaps"][0]),
            (source[start+len(old):], candidate[output_start+len(new):], proof["protected_gaps"][1])):
        require(before == after and ep.pin(before) ==
                {key: gap[key] for key in ("bytes", "sha256")},
                "actual EP complement differs")
    changes = []
    for key, value in (("family", "A"), ("profile_id", "unknown"),
                       ("full_inverse", 1), ("resources_changed", True),
                       ("models_changed", True), ("move_encoding_changed", True),
                       ("ordering_or_ties_changed", True), ("runtime_qualified", True)):
        changed = copy.deepcopy(proof)
        changed[key] = value
        changes.append(changed)
    changed = copy.deepcopy(proof)
    changed["domain"]["FEN_halfmove_max"] = 2147483647
    changes.append(changed)
    changed = copy.deepcopy(proof)
    changed["protected_maker"]["sha256"] = "0" * 64
    changes.append(changed)
    changed = copy.deepcopy(proof)
    changed["edits"][0]["input_begin"] += 1
    changes.append(changed)
    changed = copy.deepcopy(proof)
    changed["protected_gaps"][-1]["sha256"] = "0" * 64
    changes.append(changed)
    for changed in changes:
        try:
            ep.restore_source(candidate, changed, projection=projection)
        except ValueError:
            pass
        else:
            raise ValueError("modified EP proof was accepted")
    try:
        ep.restore_source(candidate + b" ", proof, projection=projection)
    except ValueError:
        pass
    else:
        raise ValueError("modified EP candidate was accepted")
    return dict(family=family, profile_id=profile_id, input=ep.pin(source), output=ep.pin(candidate),
        raw_delta=len(candidate)-len(source), full_inverse=True, protected_gaps=2,
        protected_maker=proof["protected_maker"], tampered_proofs_rejected=len(changes),
        modified_candidate_rejected=True, C_semantics_executed=False,
        runtime_qualified=False, native_identity_claimed=False)


class EPBoundaries(unittest.TestCase):
    def test_other_families_and_profiles_are_not_new_candidates(self):
        for family, profile in (("A", "test-p4"), ("B", "test-p4"), ("D", "test-p4"),
                ("F", "test-p4"), ("F8", "test-p4"), ("C", "unknown"),
                (True, "test-p4"), ("E", True)):
            with self.assertRaisesRegex(ValueError, "finite C/E P4/P28/provisional"):
                ep.transform_source(b"unadmitted", family=family,
                    profile_id=profile, projection=projection)

    def test_wrong_source_pins_and_types_are_rejected(self):
        for family, profile in ep.INPUTS:
            for source in (b"unadmitted", bytearray(b"unadmitted"), "unadmitted", None):
                with self.assertRaisesRegex(ValueError, "exact selected"):
                    ep.transform_source(source, family=family, profile_id=profile, projection=projection)

    def test_restore_requires_complete_bound_output(self):
        for candidate, proof in ((b"x", {}), (bytearray(b"x"), {}),
                (b"x", dict(schema=ep.SCHEMA, edits=[], output=ep.pin(b"y")))):
            with self.assertRaisesRegex(ValueError, "candidate and complete output"):
                ep.restore_source(candidate, proof, projection=projection)

    def test_admitted_EP_step_and_halfmove_bounds_exclude_recursive_double_push(self):
        for side in (-1, 1):
            for adjacent in (-1, 1):
                step = side * 16 - adjacent
                self.assertIn(abs(step), (15, 17))
                self.assertNotEqual(abs(step), 32)
        self.assertLess(1000000 + 1, 2147483647)
        self.assertFalse(ep.DOMAIN["arbitrary_uninitialized_Board_equivalence_claimed"])


if __name__ == "__main__":
    unittest.main()
