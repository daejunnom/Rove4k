"""Fixture/admission boundaries; actual emitted-C runs are separate reports."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


RULES = module("test_production_rules", HERE / "profile_rules.py")
PRODUCTION = module("test_rules_production", HERE.parents[2] / "engines/scripts/production.py")


class GeneratedRulesBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases, cls.coverage = RULES.fixture_cases()

    def output(self, *, mutate=None):
        rows = []
        for index, case in enumerate(self.cases):
            moves = list(case["legal"])
            if mutate:
                moves = mutate(index, case, moves)
            rows.append(str(index) + (" " + " ".join(moves) if moves else ""))
        return ("\n".join(rows) + "\n").encode("ascii")

    def test_fixture_reaches_both_colours_quiet_and_capture_underpromotions(self):
        for colour in ("white", "black"):
            for kind in ("quiet", "capture"):
                self.assertEqual(set(self.coverage[colour + "_" + kind]), set("nbrq"))
        self.assertEqual(set(self.coverage["castles"]), {"e1c1", "e1g1", "e8c8", "e8g8"})
        self.assertEqual(set(self.coverage["en_passant"]), {"e5d6", "e4d3"})
        self.assertTrue(self.coverage["absolute_pin_cases"])
        self.assertTrue(self.coverage["checkmate_cases"])

    def test_queen_only_generated_set_cannot_pass_as_full_nbrq(self):
        def queen_only(index, case, moves):
            return [move for move in moves if len(move) != 5 or move[-1] == "q"]
        with self.assertRaisesRegex(ValueError, "actual generated legal move set differs"):
            RULES._compare_output(self.output(mutate=queen_only), self.cases)

    def test_duplicate_legal_move_is_not_hidden_by_set_comparison(self):
        def duplicate(index, case, moves):
            return moves + moves[:1] if index == 0 else moves
        with self.assertRaisesRegex(ValueError, "duplicate generated legal move"):
            RULES._compare_output(self.output(mutate=duplicate), self.cases)

    def test_unknown_source_rejected_before_output_or_compiler(self):
        calls = []
        with tempfile.TemporaryDirectory(prefix="rove4k-rules-admission-") as temporary:
            out = Path(temporary).resolve() / "not-created"
            with self.assertRaisesRegex(ValueError, "exact selected full C portfolio source required"):
                RULES.verify_generated_rules(b"not production C", {"entry_cleanup": "private-path"},
                    "A", PRODUCTION.resource_profile("test-p4"), baseline_source=b"not a qualified baseline",
                    out=out, run_command=lambda *args, **kwargs: calls.append(args))
            self.assertFalse(out.exists())
            self.assertEqual(calls, [])

    def test_D_manifest_cannot_inject_unreviewed_compiler_flags(self):
        rules = module("test_D_rules", HERE.parent / "tiny-d-submission/profile_rules.py")
        _, source, builder, _, _ = rules.modules()
        profile = PRODUCTION.resource_profile("test-p4")
        files, proof = source.prepare(profile)
        calls = []
        with tempfile.TemporaryDirectory(prefix="rove4k-D-rules-admission-") as temporary:
            base = Path(temporary).resolve()
            build = base / "producer"
            readable = build / "generated-readable"
            readable.mkdir(parents=True)
            for name, data in files.items():
                (readable / name).write_bytes(data)
            record = dict(format="rove4k-D-general-source-v1", family="D", complete=True,
                native_reproduced=True, resource=profile.to_record(16), proof=proof,
                equivalent_edits=True, flags=builder.native_flags(profile) + ["-fplugin=unreviewed.so"])
            (build / "build.json").write_text(json.dumps(record))
            out = base / "not-created"
            with self.assertRaisesRegex(ValueError, "preprocessor flags differ"):
                rules.verify_generated_rules(build, out,
                    run_command=lambda *args, **kwargs: calls.append(args))
            self.assertFalse(out.exists())
            self.assertEqual(calls, [])

    def test_D_storage_requires_full_proof_mode_and_frozen_tool(self):
        rules = module("test_D_rules_storage", HERE.parent / "tiny-d-submission/profile_rules.py")
        shared, source, _, _, _ = rules.modules()
        storage = module("test_D_storage_projection", HERE.parent / "tiny-d-submission/storage.py")
        profile = PRODUCTION.resource_profile("test-p4")
        before, proof = source.prepare(profile)
        after, storage_proof = storage.transform(before, prefix=True, dense=False)
        relative = "engines/experiments/tiny-d-submission/storage.py"
        frozen = shared.normalized(HERE.parent / "tiny-d-submission/storage.py")
        with tempfile.TemporaryDirectory(prefix="rove4k-D-storage-admission-") as temporary:
            build = Path(temporary).resolve()
            path = build / "inputs" / relative
            path.parent.mkdir(parents=True)
            path.write_bytes(frozen)
            record = dict(resource=profile.to_record(16), equivalent_edits=True, storage="prefix",
                proof={**proof, "storage": storage_proof}, inputs={relative: shared.pin(frozen)})
            self.assertEqual(rules.prepared_sources(record, build, source, shared)[0], after)
            record["proof"]["storage"] = {**storage_proof, "prefix": False}
            with self.assertRaisesRegex(ValueError, "full storage proof/inverse"):
                rules.prepared_sources(record, build, source, shared)
            record["proof"]["storage"] = storage_proof
            record["storage"] = "none"
            with self.assertRaisesRegex(ValueError, "undeclared D storage proof"):
                rules.prepared_sources(record, build, source, shared)
            record["storage"] = "prefix"
            path.write_bytes(frozen + b"\n# changed\n")
            with self.assertRaisesRegex(ValueError, "frozen storage tool identity differs"):
                rules.prepared_sources(record, build, source, shared)

    def test_complete_flag_cannot_replace_rules_evidence(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-rules-receipt-") as temporary:
            path = Path(temporary).resolve() / "rules.json"
            path.write_text(json.dumps(dict(family="A", complete=True)))
            with self.assertRaisesRegex(ValueError, "TT-free rules evidence required"):
                RULES.validate_rules_receipt(path, family="A", profile=PRODUCTION.resource_profile("test-p4"),
                    main_source=b"", source_proof={}, baseline_source=b"")

    def test_B_post_profile_cannot_choose_an_arbitrary_python_tool(self):
        # Isolate the module-path boundary. Real source/proof replays are covered
        # by the external receipts; no synthetic source is compiled here.
        baseline, actual, projected = b"baseline", b"post-profile", b"resource-profile"
        proof = {"schema": "test-resource-projection", "entry_cleanup": "none"}
        stages = [proof, {"schema": "rove4k.profile-b-source.v1", "variant": "phase"}]
        projection = SimpleNamespace(SCHEMA=proof["schema"],
            transform_source=lambda *args, **kwargs: (projected, proof),
            restore_source=lambda *args: baseline)
        loaded = []
        def current_only(name, path):
            loaded.append(name)
            self.assertEqual(name, "production_rules_projection")
            return projection
        with tempfile.TemporaryDirectory(prefix="rove4k-B-tool-admission-") as temporary:
            build = Path(temporary).resolve()
            (build / "control").mkdir()
            (build / "main.c").write_bytes(actual)
            (build / "control/main.c").write_bytes(baseline)
            record = dict(format=1, family="B", entry="B", complete=True, reproducible=True,
                post_profile={"path": "unreviewed.py", "variant": "phase"}, source_proofs=stages)
            record["class"] = "rove4k-production-profile-v1"
            (build / "build.json").write_text(json.dumps(record))
            with patch.object(RULES, "load", side_effect=current_only):
                with self.assertRaisesRegex(ValueError, "B named frozen producer"):
                    RULES.admit_source(actual, baseline, stages, "B",
                        PRODUCTION.resource_profile("test-p4"), build=build)
            self.assertEqual(loaded, ["production_rules_projection"])
            record["source_proofs"] = [proof]
            (build / "build.json").write_text(json.dumps(record))
            with patch.object(RULES, "load", side_effect=current_only):
                with self.assertRaisesRegex(ValueError, "unconsumed post-profile stage"):
                    RULES.admit_source(projected, baseline, [proof], "B",
                        PRODUCTION.resource_profile("test-p4"), build=build)

    def test_B_unknown_declared_stage_cannot_downgrade_to_control(self):
        proof = {"schema": "test-resource-projection", "entry_cleanup": "none"}
        projection = SimpleNamespace(SCHEMA=proof["schema"],
            transform_source=lambda *args, **kwargs: (b"control", proof),
            restore_source=lambda *args: b"baseline")
        with patch.object(RULES, "load", return_value=projection):
            with self.assertRaisesRegex(ValueError, "explicit B proof chain"):
                RULES.admit_source(b"control", b"baseline", [proof, {"schema": "unknown"}],
                    "B", PRODUCTION.resource_profile("test-p4"))


if __name__ == "__main__":
    unittest.main()
