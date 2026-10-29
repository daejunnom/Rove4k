import copy
import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location("profile_league_compound_tested",
    Path(__file__).with_name("profile_league_compound.py"))
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)

SOURCE = b"prefix SQ middle EP body MAKER tail AT suffix BT done"


class Component:
    def __init__(self, name, spans):
        self.name = name
        self.SCHEMA = subject.SCHEMAS[name]
        self.VARIANT = subject.COMPONENT_VARIANTS[name]
        self.INPUTS = {(family, profile): (len(SOURCE), subject.pin(SOURCE)["sha256"])
                       for family in "ACE" for profile in ("test-p16", "test-p192")}
        self.spans = spans

    def transform_source(self, source, *, family, profile_id, **kwargs):
        if subject.pin(source)["sha256"] != self.INPUTS[family, profile_id][1]:
            raise ValueError("synthetic source pin differs")
        rows, candidate = [], source
        for before, after in self.spans:
            rows.append({"input_begin": source.index(before), "before": before.decode(), "after": after.decode()})
        delta = 0
        for row in sorted(rows, key=lambda item: item["input_begin"]):
            at = row["input_begin"] + delta
            before, after = row["before"].encode(), row["after"].encode()
            row["output_begin"] = at
            candidate = candidate[:at] + after + candidate[at + len(before):]
            delta += len(after) - len(before)
        return candidate, {"schema": self.SCHEMA, "variant": self.VARIANT, "family": family,
            "profile_id": profile_id, "input": subject.pin(source), "output": subject.pin(candidate),
            "edits": rows, "full_inverse": True}

    def restore_source(self, candidate, proof, **kwargs):
        for row in reversed(proof["edits"]):
            at = row["output_begin"]
            candidate = (candidate[:at] + row["before"].encode() +
                         candidate[at + len(row["after"].encode()):])
        return candidate


class EPOwner:
    SCHEMA = subject.EP_SCHEMA

    def _regions(self, source, family):
        return b"EP", b"E", b"MAKER"


class Projection:
    SCHEMA = subject.PROJECTION_SCHEMA


def helpers(variant):
    available = {"square": Component("square", [(b"SQ", b"S")]),
                 "ep": Component("ep", [(b"EP", b"E")]),
                 "atomic": Component("atomic", [(b"AT", b"A"), (b"BT", b"B")]),
                 "ep_owner": EPOwner(), "projection": Projection()}
    names = set(subject.VARIANTS[variant]) | ({"ep_owner", "projection"} if "ep" in subject.VARIANTS[variant] else set())
    return {name: available[name] for name in names}


class CombinedContract(unittest.TestCase):
    def test_all_twelve_finite_combinations_and_gap_identity(self):
        count = 0
        for variant, families in subject.FAMILIES.items():
            for family in families:
                for profile in ("test-p16", "test-p192"):
                    with self.subTest(variant=variant, family=family, profile=profile):
                        modules = helpers(variant)
                        candidate, proof = subject.transform_source(SOURCE, family=family,
                            profile_id=profile, variant=variant, helpers=modules)
                        self.assertEqual(subject.restore_source(candidate, proof, helpers=modules), SOURCE)
                        self.assertEqual([row["component"] for row in proof["components"]], list(subject.VARIANTS[variant]))
                        for gap in proof["protected_gaps"]:
                            old = SOURCE[gap["input_begin"]:gap["input_begin"] + gap["bytes"]]
                            new = candidate[gap["output_begin"]:gap["output_begin"] + gap["bytes"]]
                            self.assertEqual(old, new)
                            self.assertEqual(subject.pin(old), {key: gap[key] for key in ("bytes", "sha256")})
                        if "ep" in subject.VARIANTS[variant]:
                            self.assertEqual(proof["protected_ep_maker"]["sha256"], subject.pin(b"MAKER")["sha256"])
                        count += 1
        self.assertEqual(count, 12)

    def test_mutations_and_malformed_proofs_are_rejected(self):
        modules = helpers("square-ep-atomic")
        candidate, proof = subject.transform_source(SOURCE, family="C", profile_id="test-p16",
            variant="square-ep-atomic", helpers=modules)
        for mutate in (lambda p: p["protected_gaps"][0].update(sha256="0" * 64),
                       lambda p: p["components"].reverse(),
                       lambda p: p["edits"][0].update(output_begin=True),
                       lambda p: p.pop("protected_ep_maker")):
            changed = copy.deepcopy(proof)
            mutate(changed)
            with self.assertRaises(ValueError):
                subject.restore_source(candidate, changed, helpers=modules)
        with self.assertRaises(ValueError):
            subject.restore_source(candidate + b"x", proof, helpers=modules)

    def test_overlaps_and_protected_maker_change_are_rejected(self):
        modules = helpers("square-ep")
        modules["square"] = Component("square", [(b"EP", b"X")])
        with self.assertRaisesRegex(ValueError, "overlap"):
            subject.transform_source(SOURCE, family="C", profile_id="test-p16",
                variant="square-ep", helpers=modules)
        modules = helpers("square-ep")
        modules["square"] = Component("square", [(b"MAKER", b"M")])
        with self.assertRaisesRegex(ValueError, "maker"):
            subject.transform_source(SOURCE, family="C", profile_id="test-p16",
                variant="square-ep", helpers=modules)

    def test_exact_input_and_helper_roles_are_required(self):
        modules = helpers("ep-atomic")
        for payload, family, profile, variant, selected in (
            (SOURCE + b"x", "C", "test-p16", "ep-atomic", modules),
            (SOURCE, "A", "test-p16", "ep-atomic", modules),
            (SOURCE, "C", "test-p28", "ep-atomic", modules),
            (SOURCE, "C", "test-p16", "ep-atomic", {"ep": modules["ep"]}),
        ):
            with self.subTest(family=family, profile=profile), self.assertRaises(ValueError):
                subject.transform_source(payload, family=family, profile_id=profile,
                    variant=variant, helpers=selected)

    def test_component_output_and_edit_proof_must_match(self):
        class Broken(Component):
            def transform_source(self, *args, **kwargs):
                candidate, proof = super().transform_source(*args, **kwargs)
                proof["edits"][0]["after"] = "X"
                return candidate, proof

            def restore_source(self, candidate, proof, **kwargs):
                return SOURCE

        modules = helpers("square-atomic")
        modules["square"] = Broken("square", [(b"SQ", b"S")])
        with self.assertRaisesRegex(ValueError, "replay"):
            subject.transform_source(SOURCE, family="A", profile_id="test-p16",
                variant="square-atomic", helpers=modules)

    def test_component_overlap_boolean_offset_and_role_mutations_fail(self):
        class Broken(Component):
            def __init__(self, mode):
                super().__init__("square", [(b"SQ", b"S")])
                self.mode = mode

            def transform_source(self, *args, **kwargs):
                candidate, proof = super().transform_source(*args, **kwargs)
                if self.mode == "overlap":
                    proof["edits"].append(copy.deepcopy(proof["edits"][0]))
                else:
                    proof["edits"][0]["input_begin"] = True
                return candidate, proof

            def restore_source(self, candidate, proof, **kwargs):
                return SOURCE

        for mode, error in (("overlap", "overlap"), ("boolean", "typed")):
            modules = helpers("square-atomic")
            modules["square"] = Broken(mode)
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, error):
                subject.transform_source(SOURCE, family="A", profile_id="test-p16",
                    variant="square-atomic", helpers=modules)
        for defect in ("schema", "extra"):
            modules = helpers("square-atomic")
            if defect == "schema":
                modules["square"].SCHEMA = "not-the-reviewed-role"
            else:
                modules["ep_owner"] = EPOwner()
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                subject.transform_source(SOURCE, family="A", profile_id="test-p16",
                    variant="square-atomic", helpers=modules)


if __name__ == "__main__":
    unittest.main()
