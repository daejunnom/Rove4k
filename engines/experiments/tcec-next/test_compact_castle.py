"""Pure source/proof and finite inner-arm model checks, never actual C rules.

The synthetic scaffold exercises only private literal/context refusal. Public
positive checks require genuine pinned sources supplied by the caller. No C,
engine, compiler, codec, factory or subprocess is loaded or executed here.
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


castle = load("compact_castle_test_owner", HERE / "compact_castle.py")
projection = load("castle_test_projection", HERE / "spelling_compound.py")


def scaffold(family):
    """A fragment mock, deliberately not a public transform-admitted source."""
    integer, returned = castle.CONTEXT[family]
    aliases = "#define L int\n#define J return\n" if integer == "L" else ""
    opening = ("static " + integer + " g(const E*p,Y*B," + integer + " f," + integer + " s){"
        "if(B&&a==6){" + integer + " u=s>0?4:116,w=s>0?0:2;if(o==u&&!c(p,u,-s)){")
    return (aliases + opening).encode("ascii") + castle.BEFORE + ("}}}" + returned + " n;}").encode("ascii")


def check_actual_source(source, *, family, profile_id):
    """Check real source spans/inverse/tamper refusal without executing C."""
    candidate, proof = castle.transform(source, family=family, profile_id=profile_id, projection=projection)
    if castle.restore_source(candidate, proof, projection=projection) != source:
        raise ValueError("actual castle inverse differs")
    row = proof["edits"][0]
    old, new = row["before"].encode("ascii"), row["after"].encode("ascii")
    at, target = row["input_begin"], row["output_begin"]
    if source[at:at+len(old)] != old or candidate[target:target+len(new)] != new:
        raise ValueError("actual castle spans differ")
    for before, after, gap in ((source[:at], candidate[:target], proof["protected_gaps"][0]),
            (source[at+len(old):], candidate[target+len(new):], proof["protected_gaps"][1])):
        if before != after or castle.pin(before) != {key: gap[key] for key in ("bytes", "sha256")}:
            raise ValueError("actual castle protected complement differs")
    changed = []
    for key, value in (("family", "D"), ("profile_id", "test-p4"), ("full_inverse", 1),
            ("resources_changed", True), ("maker_or_evaluation_changed", True),
            ("search_policy_changed", True), ("ordering_or_ties_changed", True),
            ("runtime_qualified", True)):
        item = copy.deepcopy(proof);item[key] = value;changed.append(item)
    for key, value in (("loop_directions", [-1, 1]), ("rights_range", [0, 2147483647])):
        item = copy.deepcopy(proof);item["domain"][key] = value;changed.append(item)
    item = copy.deepcopy(proof);item["protected_gaps"][-1]["sha256"] = "0"*64;changed.append(item)
    item = copy.deepcopy(proof);item["edits"][0]["input_begin"] += 1;changed.append(item)
    item = copy.deepcopy(proof);item["domain"]["loop_directions"] = (1, -1);changed.append(item)
    item = copy.deepcopy(proof);item["protected_gaps"] = tuple(item["protected_gaps"]);changed.append(item)
    for item in changed:
        try:
            castle.restore_source(candidate, item, projection=projection)
        except ValueError:
            pass
        else:
            raise ValueError("modified castle proof accepted")
    for data in (candidate, source + b" "):
        try:
            castle.transform(data, family=family, profile_id=profile_id, projection=projection)
        except ValueError:
            pass
        else:
            raise ValueError("already-applied or altered source admitted")
    return dict(family=family, profile_id=profile_id, input=castle.pin(source),
        output=castle.pin(candidate), raw_delta=len(candidate)-len(source),
        protected_gaps=2, full_inverse=True, tampered_proofs_rejected=len(changed),
        actual_C_rules_executed=False, runtime_qualified=False)


class CastleBoundaries(unittest.TestCase):
    def test_only_three_real_W256_contexts_are_admitted(self):
        for family, profile in (("B", "tcec-provisional"), ("D", "tcec-provisional"),
                ("F", "tcec-provisional"), ("A", "test-p4"), ("C", "test-p28"),
                ("E", "unknown"), (True, "tcec-provisional"), ("A", True)):
            with self.assertRaisesRegex(ValueError, "finite A/C/E W256"):
                castle.transform(b"not admitted", family=family, profile_id=profile, projection=projection)
        for family, profile in castle.INPUTS:
            for data in (scaffold(family), "source", bytearray(b"source"), None):
                with self.assertRaisesRegex(ValueError, "exact selected full W256"):
                    castle.transform(data, family=family, profile_id=profile, projection=projection)

    def test_fragment_mock_byte_geometry_and_context_refusal(self):
        for family in castle.CONTEXT:
            data = scaffold(family)
            at, after, guard = castle._region(data, family)
            self.assertEqual(len(castle.BEFORE), 154)
            self.assertEqual(len(after)-len(castle.BEFORE), -31 if family == "C" else -33)
            self.assertTrue(data[:at].endswith(guard))
            mutations = (data.replace(b"if(o==u", b"if(o!=u"),
                data.replace(b"1<<w", b"2<<w", 1), data + castle.BEFORE,
                data.replace(b"-s)){", b"s)){", 1))
            for bad in mutations:
                with self.assertRaises(ValueError):
                    castle._region(bad, family)
            if family in ("A", "E"):
                with self.assertRaisesRegex(ValueError, "macro aliases"):
                    castle._region(data.replace(b"#define L int\n", b"#define L long\n"), family)

    def test_finite_inner_arm_model_preserves_attack_calls_and_emission_order(self):
        # This models only the two literal arms, not actual C or chess legality.
        for home, shift in ((4, 0), (116, 2)):
            squares = (home+1, home+2, home-1, home-2, home-3)
            for rights in range(16):
                for occupied in range(32):
                    empty = {square: not (occupied >> bit & 1) for bit, square in enumerate(squares)}
                    for attacks in range(4):
                        calls, moves = [], []
                        if rights & (1 << shift) and empty[home+1] and empty[home+2]:
                            calls.append(home+1)
                            if not attacks & 1:moves.append(home+2)
                        if rights & (2 << shift) and empty[home-1] and empty[home-2] and empty[home-3]:
                            calls.append(home-1)
                            if not attacks & 2:moves.append(home-2)
                        new_calls, new_moves = [], []
                        for direction in (1, -1):
                            bit = shift + (direction < 0)
                            self.assertIn(bit, range(4))
                            self.assertTrue(all(0 <= square < 128 and not square & 0x88 for square in squares))
                            if (rights & (1 << bit) and empty[home+direction] and empty[home+2*direction]
                                    and (direction > 0 or empty[home-3])):
                                new_calls.append(home+direction)
                                if not attacks & (1 if direction > 0 else 2):new_moves.append(home+2*direction)
                        self.assertEqual((calls, moves), (new_calls, new_moves))

    def test_restore_requires_bound_output_and_typed_proof(self):
        for value in ({"nested": (1, -1)}, {"nested": [{"number": 1.0}]}, {1: "key"}):
            with self.assertRaisesRegex(ValueError, "exact JSON proof"):
                castle._proof_types(value)
        for data, proof in ((b"x", {}), (bytearray(b"x"), {}),
                (b"x", dict(schema=castle.SCHEMA, edits=[], output=castle.pin(b"y")))):
            with self.assertRaisesRegex(ValueError, "complete bound output"):
                castle.restore_source(data, proof, projection=projection)


if __name__ == "__main__":
    unittest.main()
