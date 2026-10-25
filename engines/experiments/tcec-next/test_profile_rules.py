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

    def test_portable_phase_has_exact_family_variant_and_stage_order(self):
        proof = {"schema": "test-resource-projection", "entry_cleanup": "none"}
        projection = SimpleNamespace(SCHEMA=proof["schema"],
            transform_source=lambda *args, **kwargs: (b"resource", proof),
            restore_source=lambda *args: b"baseline")
        phase = {"schema": "rove4k.portable-phase-source.v1", "variant": "phase-init"}
        model = {"stage": "canonical-e19-physical-binding"}
        examples = (("A", [proof, {"schema": "unknown"}], "explicit A/C/F proof chain"),
                    ("C", [proof, {**phase, "variant": "phase"}], "reviewed ACEF phase-init"),
                    ("E", [proof, phase], "explicit E proof chain"),
                    ("E", [proof, model, phase], "explicit E proof chain"),
                    ("F", [proof, phase, model], "explicit A/C/F proof chain"))
        for family, stages, detail in examples:
            with self.subTest(family=family, stages=stages), patch.object(RULES, "load", return_value=projection):
                with self.assertRaisesRegex(ValueError, detail):
                    RULES.admit_source(b"resource", b"baseline", stages, family,
                        PRODUCTION.resource_profile("test-p4"))

    def test_named_phase_helper_must_have_a_matching_frozen_tool_role(self):
        relative = "engines/experiments/tcec-next/profile_phase.py"
        stages = [{"schema": "resource"}, {"schema": "phase"}]
        post = {"path": relative, "variant": "phase-init"}
        with tempfile.TemporaryDirectory(prefix="rove4k-phase-tool-admission-") as temporary:
            build = Path(temporary).resolve()
            (build / "control").mkdir()
            (build / "main.c").write_bytes(b"output")
            (build / "control/main.c").write_bytes(b"baseline")
            frozen = build / "inputs" / relative
            frozen.parent.mkdir(parents=True)
            frozen.write_bytes(b"fixed helper snapshot")
            expected = RULES.pin(frozen.read_bytes())
            record = dict(format=1, family="A", entry="A", complete=True, reproducible=True,
                post_profile=post, source_proofs=stages, inputs={relative: expected},
                source_closure={"inputs": [{"path": relative, "role": "engine", **expected}]})
            record["class"] = "rove4k-production-profile-v1"
            (build / "build.json").write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "frozen named post-profile/model tool"):
                RULES._source_build_record(build, family="A", stages=stages, post_profile=post,
                    main_source=b"output", baseline_source=b"baseline", tools=(relative,))

    def test_spelling_requires_selected_route_winner_and_final_position(self):
        proof = {"schema": "test-resource-projection", "entry_cleanup": "private-path"}
        projection = SimpleNamespace(SCHEMA=proof["schema"],
            transform_source=lambda *args, **kwargs: (b"resource", proof),
            restore_source=lambda *args: b"baseline")
        phase = {"schema": "rove4k.portable-phase-source.v1", "variant": "phase-init"}
        b_post = {"schema": "rove4k.profile-b-source.v1", "variant": "tcec-final-lf"}
        spelling = {"schema": RULES.SPELLING_SCHEMA, "variant": "clock-type"}
        model = {"stage": "canonical-e19-physical-binding"}
        examples = (
            ("A", [proof, spelling], "final spelling requires selected"),
            ("A", [proof, phase, {**spelling, "variant": "atomic-assignment"}], "reviewed winner"),
            ("A", [proof, phase, spelling, spelling], "explicit A/C/F proof chain"),
            ("A", [proof, phase, spelling, {"schema": "unknown"}], "explicit A/C/F proof chain"),
            ("E", [proof, phase, spelling, model], "explicit E proof chain"),
            ("B", [proof, {**b_post, "variant": "phase"},
                   {**spelling, "variant": "atomic-assignment"}], "final spelling requires selected"))
        for family, stages, detail in examples:
            with self.subTest(family=family, stages=stages), patch.object(RULES, "load", return_value=projection):
                with self.assertRaisesRegex(ValueError, detail):
                    RULES.admit_source(b"resource", b"baseline", stages, family,
                        PRODUCTION.resource_profile("test-p4"))

    def test_spelling_manifest_requires_exact_metadata_tool_pin_and_shipping_plan(self):
        post = {"path": "engines/experiments/tcec-next/profile_phase.py", "variant": "phase-init"}
        spelling = {"path": RULES.SPELLING, "selection": "best", "variant": "clock-type"}
        stages = [{"schema": "resource"}, {"schema": "phase"}, {"schema": RULES.SPELLING_SCHEMA}]
        frozen_bytes = RULES.normalized(HERE / "profile_spelling.py")
        self.assertEqual(RULES.pin(frozen_bytes), RULES.SPELLING_PIN)
        with tempfile.TemporaryDirectory(prefix="rove4k-spelling-tool-admission-") as temporary:
            build = Path(temporary).resolve()
            (build / "control").mkdir()
            (build / "main.c").write_bytes(b"output")
            (build / "control/main.c").write_bytes(b"baseline")
            helper = build / "inputs" / RULES.SPELLING
            helper.parent.mkdir(parents=True)
            helper.write_bytes(frozen_bytes)
            record = dict(format=1, family="A", entry="A", complete=True, reproducible=True,
                post_profile=post, post_spelling=spelling, source_proofs=stages,
                inputs={RULES.SPELLING: RULES.SPELLING_PIN},
                source_closure={"inputs": [{"path": RULES.SPELLING, "role": "tool", **RULES.SPELLING_PIN}]},
                plan=dict(family="A", full=True, representation="source-jit", entry_cleanup="private-path"))
            record["class"] = "rove4k-production-profile-v1"
            def check():
                (build / "build.json").write_text(json.dumps(record))
                return RULES._source_build_record(build, family="A", stages=stages, post_profile=post,
                    post_spelling=spelling, main_source=b"output", baseline_source=b"baseline",
                    tools=(RULES.SPELLING,))
            self.assertEqual(check(), record)
            for field, bad in (("path", "unreviewed.py"), ("selection", "control"),
                               ("variant", "protocol-prefix")):
                record["post_spelling"] = {**spelling, field: bad}
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, "named frozen producer"):
                    check()
            record["post_spelling"] = spelling
            for field, bad in (("full", False), ("representation", "packed-native"),
                               ("entry_cleanup", "none")):
                original = record["plan"][field]
                record["plan"][field] = bad
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, "full source-JIT/private-path"):
                    check()
                record["plan"][field] = original
            record["source_closure"]["inputs"][0]["role"] = "engine"
            with self.assertRaisesRegex(ValueError, "frozen named post-profile/model tool"):
                check()
            record["source_closure"]["inputs"][0]["role"] = "tool"
            helper.write_bytes(frozen_bytes + b"\n")
            changed = RULES.pin(helper.read_bytes())
            record["inputs"][RULES.SPELLING] = changed
            record["source_closure"]["inputs"][0].update(changed)
            with self.assertRaisesRegex(ValueError, "reviewed final spelling helper identity"):
                check()

    def test_E_spelling_inverse_precedes_model_offsets_and_earlier_stages(self):
        baseline, resource_body, phase_body, model_body, shipped = b"base", b"resource", b"pres", b"Pres", b"spellingPres"
        resource = {"schema": "test-resource-projection", "entry_cleanup": "private-path"}
        phase = {"schema": "rove4k.portable-phase-source.v1", "variant": "phase-init"}
        model = dict(stage="canonical-e19-physical-binding", source_model_id="e19-admitted-source-baseline",
                     table_value_offset=0, before="p", after="P")
        spelling = {"schema": RULES.SPELLING_SCHEMA, "variant": "clock-type"}
        inverses = []
        def inverse(label, actual, expected, restored):
            self.assertEqual(actual, expected)
            inverses.append(label)
            return restored
        projection = SimpleNamespace(SCHEMA=resource["schema"],
            transform_source=lambda *args, **kwargs: (resource_body, resource),
            restore_source=lambda actual, proof: inverse("resource", actual, resource_body, baseline))
        phase_module = SimpleNamespace(transform_source=lambda *args, **kwargs: (phase_body, phase),
            restore_source=lambda actual, proof: inverse("phase", actual, phase_body, resource_body))
        bound_model = SimpleNamespace(model_id="current-canonical-model",
            bind_physical_table=lambda actual, **kwargs: (model_body, model))
        model_module = SimpleNamespace(Model=SimpleNamespace(load=lambda path: bound_model,
            from_physical_source=lambda actual, **kwargs: self.assertEqual(actual, phase_body)))
        spelling_module = SimpleNamespace(SCHEMA=RULES.SPELLING_SCHEMA,
            transform_source=lambda *args, **kwargs: (shipped, spelling),
            restore_source=lambda actual, proof: inverse("spelling", actual, shipped, model_body))
        modules = {"production_rules_projection": projection, "production_rules_phase_projection": phase_module,
                   "production_rules_E19_model": model_module, "production_rules_spelling_projection": spelling_module}
        stages = [resource, phase, model, spelling]
        with patch.object(RULES, "load", side_effect=lambda name, path: modules[name]), \
             patch.object(RULES, "_source_build_record") as record:
            self.assertEqual(RULES.admit_source(shipped, baseline, stages, "E",
                PRODUCTION.resource_profile("test-p4"), build=Path("/named-build")), stages)
        self.assertEqual(inverses, ["spelling", "phase", "resource"])
        self.assertEqual(record.call_args.kwargs["post_spelling"],
            {"path": RULES.SPELLING, "selection": "best", "variant": "clock-type"})

    def test_control_manifest_cannot_hide_an_unconsumed_spelling_stage(self):
        proof = {"schema": "test-resource-projection", "entry_cleanup": "private-path"}
        projection = SimpleNamespace(SCHEMA=proof["schema"],
            transform_source=lambda *args, **kwargs: (b"resource", proof),
            restore_source=lambda *args: b"baseline")
        with tempfile.TemporaryDirectory(prefix="rove4k-unconsumed-spelling-") as temporary:
            build = Path(temporary).resolve()
            (build / "build.json").write_text(json.dumps(dict(source_proofs=[proof],
                post_spelling={"path": RULES.SPELLING, "selection": "best", "variant": "clock-type"})))
            with patch.object(RULES, "load", return_value=projection):
                with self.assertRaisesRegex(ValueError, "unconsumed post-profile stage"):
                    RULES.admit_source(b"resource", b"baseline", [proof], "A",
                        PRODUCTION.resource_profile("test-p4"), build=build)

    def test_legacy_E_receipt_cannot_upgrade_phase_or_changed_model(self):
        source = b"already admitted complete source"
        resource = {"schema": "resource"}
        model = dict(stage="canonical-e19-physical-binding", model_parameters_changed=False,
            full_inverse=True, consumer_code_changed=False, change_kind="model-input-binding",
            source_sha256=RULES.pin(source)["sha256"], result_sha256=RULES.pin(source)["sha256"])
        report = {"source_proof": RULES.pin(json.dumps(resource, sort_keys=True).encode())}
        self.assertTrue(RULES._legacy_model_report(report, [resource, model], "E", source))
        for changed in ({**model, "model_parameters_changed": True},
                        {**model, "result_sha256": "0" * 64},
                        {**model, "consumer_code_changed": True}):
            self.assertFalse(RULES._legacy_model_report(report, [resource, changed], "E", source))
        self.assertFalse(RULES._legacy_model_report(report,
            [resource, {"schema": "rove4k.portable-phase-source.v1"}, model], "E", source))
        self.assertFalse(RULES._legacy_model_report({**report, "build": {}}, [resource, model], "E", source))


if __name__ == "__main__":
    unittest.main()
