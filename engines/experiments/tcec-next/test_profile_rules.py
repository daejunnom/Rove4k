"""Fixture/admission boundaries; actual emitted-C runs are separate reports."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

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

    def test_new_test_profiles_do_not_admit_an_unknown_source_or_run_a_compiler(self):
        # The added CLI profiles must still pass the real resource projection
        # and source-identity boundary before any probe artifact is made.
        calls = []
        with tempfile.TemporaryDirectory(prefix="rove4k-new-profile-rules-admission-") as temporary:
            for profile_id in ("test-p16", "test-p192"):
                profile = RULES.resolve_resource_profile(PRODUCTION, profile_id)
                for family in "ABCEF":
                    with self.subTest(profile=profile_id, family=family):
                        out = Path(temporary).resolve() / (profile_id + family)
                        with self.assertRaisesRegex(ValueError, "exact selected full C portfolio source required"):
                            RULES.verify_generated_rules(b"not production C", {"entry_cleanup": "private-path"},
                                family, profile, baseline_source=b"not a qualified baseline", out=out,
                                run_command=lambda *args, **kwargs: calls.append(args))
                        self.assertFalse(out.exists())
        self.assertEqual(calls, [])

    def test_league_rules_use_reviewed_resource_owner_and_reject_redefinition(self):
        expectations = {"test-p16": (16, 16 << 30, 12 << 30),
                        "test-p192": (192, 192 << 30, 192 << 30)}
        for profile_id, (workers, cap, actual) in expectations.items():
            with self.subTest(profile=profile_id):
                profile = RULES.resolve_resource_profile(PRODUCTION, profile_id)
                record = profile.to_record(24)
                self.assertEqual((record["workers"], record["tt_cap_bytes"], record["tt_bytes"]),
                                 (workers, cap, actual))
                forged = SimpleNamespace(id=profile_id, to_record=lambda _: {**record, "workers": workers + 1})
                with self.assertRaisesRegex(ValueError, "league profile resources differ"):
                    RULES.admit_source(b"not source", b"not baseline", {}, "A", forged)
                changing = SimpleNamespace(id=profile_id, to_record=Mock(side_effect=[record, {}]))
                canonical = RULES.canonical_rules_profile(changing, "A")
                self.assertEqual(canonical.to_record(24), record)
                self.assertEqual(changing.to_record.call_count, 1)
                with self.assertRaisesRegex(ValueError, "A/B/C/E/F"):
                    RULES.canonical_rules_profile(profile, "D")
        with patch.object(RULES, "LEAGUE_OWNER_PIN", {"bytes": 0, "sha256": "0" * 64}):
            with self.assertRaisesRegex(ValueError, "league profile owner identity differs"):
                RULES.resolve_resource_profile(PRODUCTION, "test-p16")

    def test_league_resource_only_proof_keeps_build_binding(self):
        # A resource-only new profile still binds the frozen build manifest in
        # both production reports and receipt validation via the proof list.
        source, baseline = b"test-resource", b"test-baseline"
        proof = {"schema": "test-projection", "entry_cleanup": "private-path"}
        projection = SimpleNamespace(SCHEMA=proof["schema"],
            transform_source=lambda *a, **kw: (source, proof),
            restore_source=lambda actual, supplied: baseline)
        original_load = RULES.load
        def loaded(name, path):
            return projection if name == "production_rules_projection" else original_load(name, path)
        with tempfile.TemporaryDirectory(prefix="rove4k-league-rules-build-") as temporary:
            build = Path(temporary)
            (build / "build.json").write_text(json.dumps(dict(post_profile=None, post_spelling=None,
                post_scan=None, post_ep=None, source_dependencies=None, source_proofs=[proof])))
            with patch.object(RULES, "load", side_effect=loaded), \
                 patch.object(RULES, "_source_build_record", return_value={}) as checked:
                profile = RULES.resolve_resource_profile(PRODUCTION, "test-p16")
                self.assertEqual(RULES.admit_source(source, baseline, proof, "A", profile, build=build), [proof])
            self.assertIn(RULES.LEAGUE_OWNER, checked.call_args.kwargs["tools"])

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

        # The merged dependency stage comes after spelling. Its compiler gate
        # is additional evidence; its inverse must restore the spelling body
        # before the model's offsets and earlier inverses are consumed.
        dependency = {"schema": "rove4k.profile-dependencies.v1"}
        dependency_body = b"dependencyPres"
        inverses.clear()
        stages = [*stages, dependency]
        def compiler_gate(build, manifest, proof, source, *, checked):
            self.assertEqual((proof, source), (dependency, dependency_body))
            inverses.append("compiler-gate")
            return shipped
        modules["production_rules_dependencies"] = SimpleNamespace(
            transform_source=lambda actual: (dependency_body, dependency),
            restore_source=lambda actual, proof: inverse("dependency", actual, dependency_body, shipped),
            validate_receipt=compiler_gate)
        manifest = {"attempts": [{"directory": name, "source_proofs": stages}
                                  for name in ("first", "repeat")]}
        with patch.object(RULES, "load", side_effect=lambda name, path: modules[name]), \
             patch.object(RULES, "_source_build_record", return_value=manifest) as record:
            self.assertEqual(RULES.admit_source(dependency_body, baseline, stages, "E",
                PRODUCTION.resource_profile("test-p4"), build=Path("/named-build")), stages)
        self.assertEqual(inverses, ["compiler-gate", "dependency", "spelling", "phase", "resource"])
        self.assertEqual(record.call_args.kwargs["source_dependencies"],
            {"path": "engines/experiments/tcec-next/profile_dependencies.py", "variant": "unused-includes"})

    def test_dependency_must_follow_spelling_and_cannot_be_duplicated(self):
        resource = {"schema": "test-resource-projection", "entry_cleanup": "private-path"}
        phase = {"schema": "rove4k.portable-phase-source.v1", "variant": "phase-init"}
        spelling = {"schema": RULES.SPELLING_SCHEMA, "variant": "clock-type"}
        dependency = {"schema": "rove4k.profile-dependencies.v1"}
        projection = SimpleNamespace(SCHEMA=resource["schema"],
            transform_source=lambda *args, **kwargs: (b"resource", resource),
            restore_source=lambda *args: b"baseline")
        for stages in ([resource, phase, dependency, spelling],
                       [resource, phase, spelling, dependency, dependency],
                       [resource, phase, spelling, dependency, {"schema": "unknown"}]):
            with self.subTest(stages=stages), patch.object(RULES, "load", return_value=projection):
                with self.assertRaisesRegex(ValueError, "explicit A/C/F proof chain"):
                    RULES.admit_source(b"body", b"baseline", stages, "A",
                        PRODUCTION.resource_profile("test-p4"))

    def test_dependency_requires_both_full_attempts_and_actual_compiler_gate(self):
        resource = {"schema": "test-resource-projection", "entry_cleanup": "private-path"}
        dependency = {"schema": "rove4k.profile-dependencies.v1"}
        stages = [resource, dependency]
        gate_calls = []
        projection = SimpleNamespace(SCHEMA=resource["schema"],
            transform_source=lambda *args, **kwargs: (b"before", resource),
            restore_source=lambda *args: b"baseline")
        def compiler_gate(build, manifest, proof, source, *, checked):
            gate_calls.append((proof, source))
            raise ValueError("actual compiler receipt rejected")
        helper = SimpleNamespace(transform_source=lambda source: (b"after", dependency),
            validate_receipt=compiler_gate)
        modules = {"production_rules_projection": projection, "production_rules_dependencies": helper}
        attempts = [{"directory": name, "source_proofs": stages} for name in ("first", "repeat")]
        for bad in ([], attempts[:1], [*attempts, attempts[0]],
                    [{**attempts[0], "source_proofs": [resource]}, attempts[1]]):
            with self.subTest(attempts=bad), \
                 patch.object(RULES, "load", side_effect=lambda name, path: modules[name]), \
                 patch.object(RULES, "_source_build_record", return_value={"attempts": bad}):
                with self.assertRaisesRegex(ValueError, "both fresh full-chain attempts"):
                    RULES.admit_source(b"after", b"baseline", stages, "A",
                        PRODUCTION.resource_profile("test-p4"), build=Path("/named-build"))
        self.assertEqual(gate_calls, [])
        with patch.object(RULES, "load", side_effect=lambda name, path: modules[name]), \
             patch.object(RULES, "_source_build_record", return_value={"attempts": attempts}):
            with self.assertRaisesRegex(ValueError, "actual compiler receipt rejected"):
                RULES.admit_source(b"after", b"baseline", stages, "A",
                    PRODUCTION.resource_profile("test-p4"), build=Path("/named-build"))
        self.assertEqual(gate_calls, [(dependency, b"after")])
        for escaped in ("../other-build/native", "/other-build/native"):
            def outside_receipt(build, manifest, proof, source, *, checked):
                return checked(build, escaped, RULES.pin(b"outside"))
            helper.validate_receipt = outside_receipt
            with self.subTest(evidence=escaped), \
                 patch.object(RULES, "load", side_effect=lambda name, path: modules[name]), \
                 patch.object(RULES, "_source_build_record", return_value={"attempts": attempts}), \
                 patch.object(RULES, "_evidence_bytes", side_effect=AssertionError("outside evidence read")):
                with self.assertRaisesRegex(ValueError, "must remain in its named build"):
                    RULES.admit_source(b"after", b"baseline", stages, "A",
                        PRODUCTION.resource_profile("test-p4"), build=Path("/named-build"))

    def test_dependency_declaration_cannot_be_silently_dropped(self):
        stages = [{"schema": "resource"}]
        declaration = {"path": "engines/experiments/tcec-next/profile_dependencies.py", "variant": "unused-includes"}
        with tempfile.TemporaryDirectory(prefix="rove4k-unconsumed-dependency-") as temporary:
            build = Path(temporary).resolve()
            (build / "control").mkdir()
            (build / "main.c").write_bytes(b"source")
            (build / "control/main.c").write_bytes(b"baseline")
            record = dict(format=1, family="A", entry="A", complete=True, reproducible=True,
                post_profile=None, post_spelling=None, source_dependencies=declaration, source_proofs=stages)
            record["class"] = "rove4k-production-profile-v1"
            (build / "build.json").write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "named frozen producer"):
                RULES._source_build_record(build, family="A", stages=stages, post_profile=None,
                    main_source=b"source", baseline_source=b"baseline")

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

    def test_compound_stage_is_finite_ACEF_only_and_precedes_dependencies(self):
        resource = {"schema": "test-resource-projection", "entry_cleanup": "private-path"}
        phase = {"schema": "rove4k.portable-phase-source.v1", "variant": "phase-init"}
        b_post = {"schema": "rove4k.profile-b-source.v1", "variant": "tcec-final-lf"}
        compound = {"schema": RULES.COMPOUND_SCHEMA, "variant": RULES.COMPOUND_VARIANT}
        dependency = {"schema": "rove4k.profile-dependencies.v1"}
        projection = SimpleNamespace(SCHEMA=resource["schema"],
            transform_source=lambda *args, **kwargs: (b"resource", resource), restore_source=lambda *args: b"baseline")
        examples = (("B", [resource, b_post, compound], "limited to A/C/E/F"),
            ("A", [resource, compound], "final spelling requires selected"),
            ("A", [resource, phase, {**compound, "variant": "unknown"}], "reviewed winner"),
            ("A", [resource, phase, compound, compound], "explicit A/C/F proof chain"),
            ("A", [resource, phase, dependency, compound], "explicit A/C/F proof chain"),
            ("A", [resource, phase, compound, dependency, dependency], "explicit A/C/F proof chain"),
            ("E", [resource, phase, compound], "explicit E proof chain"),
            ("A", [resource, phase, {"schema": RULES.SPELLING_SCHEMA, "variant": RULES.COMPOUND_VARIANT}], "reviewed winner"))
        for family, stages, detail in examples:
            with self.subTest(family=family, stages=stages), patch.object(RULES, "load", return_value=projection):
                with self.assertRaisesRegex(ValueError, detail):
                    RULES.admit_source(b"body", b"baseline", stages, family, PRODUCTION.resource_profile("test-p4"))

    def test_compound_requires_both_reviewed_helper_roles_and_consumes_their_pinned_bytes(self):
        post = {"path": "engines/experiments/tcec-next/profile_phase.py", "variant": "phase-init"}
        spelling = {"path": RULES.COMPOUND, "selection": "compound", "variant": RULES.COMPOUND_VARIANT}
        stages = [{"schema": "resource"}, {"schema": "phase"}, {"schema": RULES.COMPOUND_SCHEMA}]
        source_pins = {RULES.SPELLING: RULES.SPELLING_PIN, RULES.COMPOUND: RULES.COMPOUND_PIN}
        helper_bytes = {name: RULES.normalized(RULES.ROOT / name) for name in source_pins}
        with tempfile.TemporaryDirectory(prefix="rove4k-compound-tool-admission-") as temporary:
            build = Path(temporary).resolve(); (build / "control").mkdir()
            (build / "main.c").write_bytes(b"output"); (build / "control/main.c").write_bytes(b"baseline")
            for name, data in helper_bytes.items():
                path = build / "inputs" / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
            def base_record():
                return dict(format=1, family="A", entry="A", complete=True, reproducible=True,
                    post_profile=post, post_spelling=spelling, source_proofs=stages,
                    inputs={name: dict(value) for name, value in source_pins.items()},
                    source_closure={"inputs": [{"path": name, "role": "tool", **value} for name, value in source_pins.items()]},
                    plan=dict(family="A", full=True, representation="source-jit", entry_cleanup="private-path"),
                    **{"class": "rove4k-production-profile-v1"})
            def check(record, tools=tuple(source_pins)):
                (build / "build.json").write_text(json.dumps(record))
                return RULES._source_build_record(build, family="A", stages=stages, post_profile=post,
                    post_spelling=spelling, main_source=b"output", baseline_source=b"baseline", tools=tools)
            record = base_record(); self.assertEqual(check(record), record)
            individual, compound = RULES.compound_modules(build)
            self.assertEqual((individual.SCHEMA, compound.SCHEMA), (RULES.SPELLING_SCHEMA, RULES.COMPOUND_SCHEMA))
            for name in source_pins:
                with self.subTest(helper=name, failure="unlisted"), self.assertRaisesRegex(ValueError, "both exact reviewed"):
                    check(base_record(), tuple(tool for tool in source_pins if tool != name))
                for failure in ("missing", "duplicate", "engine-role", "frozen-tamper", "current-tamper"):
                    record = base_record()
                    row = next(row for row in record["source_closure"]["inputs"] if row["path"] == name)
                    frozen = build / "inputs" / name
                    if failure == "missing": record["source_closure"]["inputs"].remove(row)
                    elif failure == "duplicate": record["source_closure"]["inputs"].append(dict(row))
                    elif failure == "engine-role": row["role"] = "engine"
                    elif failure == "frozen-tamper":
                        frozen.write_bytes(helper_bytes[name] + b"\n")
                        altered = RULES.pin(frozen.read_bytes()); record["inputs"][name] = altered; row.update(altered)
                    original = RULES.normalized
                    def current(path):
                        value = original(path)
                        return value + b"\n" if failure == "current-tamper" and path == RULES.ROOT / name else value
                    with self.subTest(helper=name, failure=failure), patch.object(RULES, "normalized", side_effect=current):
                        with self.assertRaises(ValueError): check(record)
                        if failure in ("frozen-tamper", "current-tamper"):
                            with self.assertRaisesRegex(ValueError, "consumed helper identity"):
                                RULES.compound_modules(build)
                    frozen.write_bytes(helper_bytes[name])

    def test_compound_inverse_receives_authenticated_individual_after_dependency_undo(self):
        baseline, resource_body, phase_body, model_body, compound_body, final_body = b"base", b"resource", b"pres", b"Pres", b"compoundPres", b"dependencyPres"
        resource = {"schema": "test-resource-projection", "entry_cleanup": "private-path"}
        phase = {"schema": "rove4k.portable-phase-source.v1", "variant": "phase-init"}
        model = dict(stage="canonical-e19-physical-binding", source_model_id="e19-admitted-source-baseline",
            table_value_offset=0, before="p", after="P")
        compound = {"schema": RULES.COMPOUND_SCHEMA, "variant": RULES.COMPOUND_VARIANT}
        dependency = {"schema": "rove4k.profile-dependencies.v1"}
        calls = []; individual = SimpleNamespace(SCHEMA=RULES.SPELLING_SCHEMA)
        def inverse(name, actual, expected, parent):
            self.assertEqual(actual, expected); calls.append(name); return parent
        projection = SimpleNamespace(SCHEMA=resource["schema"], transform_source=lambda *a, **kw: (resource_body, resource),
            restore_source=lambda actual, proof: inverse("resource", actual, resource_body, baseline))
        phase_module = SimpleNamespace(transform_source=lambda *a, **kw: (phase_body, phase),
            restore_source=lambda actual, proof: inverse("phase", actual, phase_body, resource_body))
        bound = SimpleNamespace(model_id="current", bind_physical_table=lambda *a, **kw: (model_body, model))
        model_module = SimpleNamespace(Model=SimpleNamespace(load=lambda path: bound, from_physical_source=lambda *a, **kw: None))
        def compound_forward(actual, *, family, profile_id, spelling):
            self.assertIs(spelling, individual); self.assertEqual(actual, model_body); return compound_body, compound
        def compound_inverse(actual, proof, *, spelling):
            self.assertIs(spelling, individual); return inverse("compound", actual, compound_body, model_body)
        compound_module = SimpleNamespace(SCHEMA=RULES.COMPOUND_SCHEMA, transform_source=compound_forward, restore_source=compound_inverse)
        dependency_module = SimpleNamespace(transform_source=lambda actual: (final_body, dependency),
            validate_receipt=lambda build, manifest, proof, source, **kw: compound_body,
            restore_source=lambda actual, proof: inverse("dependency", actual, final_body, compound_body))
        modules = {"production_rules_projection": projection, "production_rules_phase_projection": phase_module,
            "production_rules_E19_model": model_module, "production_rules_dependencies": dependency_module}
        stages = [resource, phase, model, compound, dependency]
        manifest = {"attempts": [{"directory": name, "source_proofs": stages} for name in ("first", "repeat")]}
        with patch.object(RULES, "load", side_effect=lambda name, path: modules[name]), \
             patch.object(RULES, "compound_modules", return_value=(individual, compound_module)), \
             patch.object(RULES, "_source_build_record", return_value=manifest) as source_record:
            self.assertEqual(RULES.admit_source(final_body, baseline, stages, "E", PRODUCTION.resource_profile("test-p4"), build=Path("/named")), stages)
        self.assertEqual(calls, ["dependency", "compound", "phase", "resource"])
        self.assertEqual(source_record.call_args.kwargs["post_spelling"],
            {"path": RULES.COMPOUND, "selection": "compound", "variant": RULES.COMPOUND_VARIANT})
        self.assertTrue({RULES.COMPOUND, RULES.SPELLING} <= set(source_record.call_args.kwargs["tools"]))
        altered = [resource, phase, model, {**compound, "components": ["unreviewed"]}, dependency]
        altered_manifest = {"attempts": [{"directory": name, "source_proofs": altered} for name in ("first", "repeat")]}
        with patch.object(RULES, "load", side_effect=lambda name, path: modules[name]), \
             patch.object(RULES, "compound_modules", return_value=(individual, compound_module)), \
             patch.object(RULES, "_source_build_record", return_value=altered_manifest):
            with self.assertRaisesRegex(ValueError, "compound spelling proof/protected gaps"):
                RULES.admit_source(final_body, baseline, altered, "E", PRODUCTION.resource_profile("test-p4"), build=Path("/named"))

    def test_F_compound_v2_replays_and_reverses_its_final_shipping_body(self):
        baseline, resource_body, phase_body, compound_body, final_body = b"base", b"resource", b"phase", b"F-v2", b"final"
        resource = {"schema": "test-resource", "entry_cleanup": "private-path"}
        phase = {"schema": "rove4k.portable-phase-source.v1", "variant": "phase-init"}
        base = {"schema": RULES.COMPOUND_SCHEMA, "variant": RULES.COMPOUND_VARIANT}
        compound = {"schema": RULES.F_COMPOUND_SCHEMA, "variant": RULES.F_COMPOUND_VARIANT, "base": base}
        dependency = {"schema": "rove4k.profile-dependencies.v1"}
        calls = []; individual = object()
        def inverse(name, actual, expected, parent):
            self.assertEqual(actual, expected); calls.append(name); return parent
        projection = SimpleNamespace(SCHEMA=resource["schema"], transform_source=lambda *a, **kw: (resource_body, resource),
            restore_source=lambda actual, proof: inverse("resource", actual, resource_body, baseline))
        phase_module = SimpleNamespace(transform_source=lambda *a, **kw: (phase_body, phase),
            restore_source=lambda actual, proof: inverse("phase", actual, phase_body, resource_body))
        def forward(actual, *, family, profile_id, spelling, variant):
            self.assertEqual((actual, family, variant), (phase_body, "F", RULES.F_COMPOUND_VARIANT))
            self.assertIs(spelling, individual); return compound_body, compound
        def backward(actual, proof, *, spelling):
            self.assertIs(spelling, individual); self.assertEqual(proof, compound)
            return inverse("compound-v2", actual, compound_body, phase_body)
        compound_module = SimpleNamespace(SCHEMA=RULES.COMPOUND_SCHEMA, F_SCHEMA=RULES.F_COMPOUND_SCHEMA,
            transform_source=forward, restore_source=backward)
        dependency_module = SimpleNamespace(transform_source=lambda actual: (final_body, dependency),
            validate_receipt=lambda *a, **kw: compound_body,
            restore_source=lambda actual, proof: inverse("dependency", actual, final_body, compound_body))
        modules = {"production_rules_projection": projection, "production_rules_phase_projection": phase_module,
                   "production_rules_dependencies": dependency_module}
        stages = [resource, phase, compound, dependency]
        record = {"attempts": [{"directory": name, "source_proofs": stages} for name in ("first", "repeat")]}
        for profile_id in ("test-p4", "test-p28", "tcec-provisional"):
            calls.clear()
            with self.subTest(profile=profile_id), patch.object(RULES, "load", side_effect=lambda name, path: modules[name]), \
                 patch.object(RULES, "compound_modules", return_value=(individual, compound_module)), \
                 patch.object(RULES, "_source_build_record", return_value=record) as build:
                self.assertEqual(RULES.admit_source(final_body, baseline, stages, "F",
                    PRODUCTION.resource_profile(profile_id), build=Path("/named")), stages)
            self.assertEqual(calls, ["dependency", "compound-v2", "phase", "resource"])
            self.assertEqual(build.call_args.kwargs["post_spelling"], RULES.F_COMPOUND_DECLARATION)
            self.assertIsNone(build.call_args.kwargs["post_scan"])

    def test_F_compound_v2_rules_forwards_supplied_typed_proof_to_real_inverse(self):
        compound = module("rules_actual_F_v2_projection", HERE / "spelling_compound.py")
        baseline, resource_body = b"base", b"resource"
        phase_body = b"clock atomic launcher for(S q=0;q<128;q=(q+9)&~8){}for(S j=0;j<128;j=(j+9)&~8){}"
        replacements = {"clock-type": (b"clock", b"short"), "atomic-assignment": (b"atomic", b"plain"),
                        "launcher-short": (b"launcher", b"J")}
        def individual_forward(source, *, family, profile_id, variant):
            before, after = replacements[variant]; at = source.index(before)
            result = source[:at] + after + source[at + len(before):]
            proof = dict(schema=RULES.SPELLING_SCHEMA, variant=variant, family=family, profile_id=profile_id,
                input=RULES.pin(source), output=RULES.pin(result),
                edits=[dict(input_begin=at, output_begin=at, before=before.decode(), after=after.decode(), role=variant)])
            return result, proof
        def individual_inverse(actual, proof):
            row = proof["edits"][0]; at = row["output_begin"]
            return actual[:at] + row["before"].encode() + actual[at + len(row["after"]):]
        individual = SimpleNamespace(SCHEMA=RULES.SPELLING_SCHEMA,
            INPUTS={("F", "test-p4"): (len(phase_body), RULES.pin(phase_body)["sha256"])},
            available=lambda family: tuple(replacements), transform_source=individual_forward, restore_source=individual_inverse)
        base = phase_body.replace(b"clock", b"short").replace(b"atomic", b"plain").replace(b"launcher", b"J")
        final = base.replace(b"(q+9)", b"q+9").replace(b"(j+9)", b"j+9")
        resource = {"schema": "test-resource", "entry_cleanup": "private-path"}
        phase = {"schema": "rove4k.portable-phase-source.v1", "variant": "phase-init"}
        dependency = {"schema": "rove4k.profile-dependencies.v1"}
        projection = SimpleNamespace(SCHEMA=resource["schema"], transform_source=lambda *a, **kw: (resource_body, resource),
            restore_source=lambda *a: baseline)
        phase_module = SimpleNamespace(transform_source=lambda *a, **kw: (phase_body, phase), restore_source=lambda *a: resource_body)
        dependency_module = SimpleNamespace(transform_source=lambda actual: (actual, dependency),
            validate_receipt=lambda *a, **kw: final, restore_source=lambda actual, proof: actual)
        modules = {"production_rules_projection": projection, "production_rules_phase_projection": phase_module,
                   "production_rules_dependencies": dependency_module}
        with patch.object(compound, "F_BASES", {"test-p4": (len(base), RULES.pin(base)["sha256"])}), \
             patch.object(compound, "F_OUTPUTS", {"test-p4": (len(final), RULES.pin(final)["sha256"])}), \
             patch.object(RULES, "load", side_effect=lambda name, path: modules[name]), \
             patch.object(RULES, "compound_modules", return_value=(individual, compound)):
            actual, proof = compound.transform_source(phase_body, family="F", profile_id="test-p4",
                spelling=individual, variant=compound.F_VARIANT)
            self.assertEqual(actual, final)
            def consume(supplied):
                stages = [resource, phase, supplied, dependency]
                record = {"attempts": [{"directory": name, "source_proofs": stages} for name in ("first", "repeat")]}
                with patch.object(RULES, "_source_build_record", return_value=record):
                    return RULES.admit_source(actual, baseline, stages, "F", PRODUCTION.resource_profile("test-p4"), build=Path("/named"))
            self.assertEqual(consume(proof)[2], proof)
            for path, value in ((("full_inverse",), 1), (("base", "full_inverse"), 1),
                    (("base", "duplicate_best"), 0), (("base", "new_candidate_count"), 1.0),
                    (("protected_gaps", 0, "bytes"), float(proof["protected_gaps"][0]["bytes"]))):
                supplied = json.loads(json.dumps(proof)); target = supplied
                for key in path[:-1]: target = target[key]
                target[path[-1]] = value
                self.assertEqual(supplied, proof)  # Python equality is precisely the unsafe shortcut.
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, "F compound v2 inverse"):
                    consume(supplied)

    def test_F_compound_v2_rejects_foreign_family_missing_cleanup_or_scan(self):
        resource = {"schema": "test-resource", "entry_cleanup": "private-path"}
        projection = SimpleNamespace(SCHEMA=resource["schema"], transform_source=lambda *a, **kw: (b"resource", resource))
        phase = {"schema": "rove4k.portable-phase-source.v1", "variant": "phase-init"}
        compound = {"schema": RULES.F_COMPOUND_SCHEMA, "variant": RULES.F_COMPOUND_VARIANT}
        dependency = {"schema": "rove4k.profile-dependencies.v1"}
        scan = {"schema": RULES.SCAN_SCHEMA, "variant": "square-successor"}
        for family, stages in (("A", [resource, phase, compound, dependency]),
                ("F", [resource, phase, compound]), ("F", [resource, phase, compound, scan, dependency])):
            with self.subTest(family=family, stages=stages), patch.object(RULES, "load", return_value=projection):
                with self.assertRaisesRegex(ValueError, "F-only compound v2"):
                    RULES.admit_source(b"body", b"baseline", stages, family, PRODUCTION.resource_profile("test-p4"))

    def test_B_compound_request_is_only_the_exact_existing_best_normalization(self):
        best = {"path": RULES.SPELLING, "selection": "best", "variant": "atomic-assignment"}
        request = {"requested": "compound", "effective": "best", "duplicate_best": True, "new_candidate_count": 0}
        self.assertIsNone(RULES.validate_spelling_request({"family": "B", "post_spelling": best}))
        self.assertEqual(RULES.validate_spelling_request({"family": "B", "post_spelling": best, "spelling_request": request}), request)
        examples = [{"family": "A", "post_spelling": best, "spelling_request": request},
            {"family": "B", "post_spelling": None, "spelling_request": request},
            {"family": "B", "post_spelling": best, "spelling_request": None},
            {"family": "B", "post_spelling": best, "spelling_request": request, "inputs": {RULES.COMPOUND: RULES.COMPOUND_PIN}},
            {"family": "B", "post_spelling": best, "spelling_request": request,
                "source_closure": {"inputs": [{"path": RULES.COMPOUND, "role": "tool", **RULES.COMPOUND_PIN}]}},
            {"family": "B", "post_spelling": best, "spelling_request": request, "source_proofs": [{"schema": RULES.COMPOUND_SCHEMA}]},
            {"family": "B", "post_spelling": best, "spelling_request": request, "source_proofs": [{"schema": RULES.F_COMPOUND_SCHEMA}]}]
        for bad in ({**request, "duplicate_best": 1}, {**request, "new_candidate_count": False},
                    {**request, "extra": False}, {**request, "effective": "compound"}, {**request, "requested": "best"}):
            examples.append({"family": "B", "post_spelling": best, "spelling_request": bad})
        for record in examples:
            with self.subTest(record=record), self.assertRaisesRegex(ValueError, "exact B compound-to-best"):
                RULES.validate_spelling_request(record)


class SquareScanRules(unittest.TestCase):
    def test_scan_helper_consumes_only_frozen_reviewed_bytes(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-rules-scan-helper-") as temporary:
            build=Path(temporary)
            data=RULES.normalized(RULES.ROOT/RULES.SCAN)
            path=build/"inputs"/RULES.SCAN;path.parent.mkdir(parents=True);path.write_bytes(data)
            self.assertEqual(RULES.scan_module(build).SCHEMA,RULES.SCAN_SCHEMA)
            path.write_bytes(data+b"#changed\n")
            with self.assertRaisesRegex(ValueError,"consumed bytes"):
                RULES.scan_module(build)
            path.write_bytes(data)
            with patch.object(RULES,"normalized",return_value=data+b"#changed\n"), self.assertRaisesRegex(ValueError,"consumed bytes"):
                RULES.scan_module(build)

    def test_scan_exact_chain_replays_and_reverses_before_compound(self):
        base,resource_body,phase_body,compound_body,scan_body,final=b"base",b"resource",b"phase",b"compound",b"scan",b"final"
        resource={"schema":"test-resource","entry_cleanup":"private-path"}
        phase={"schema":"rove4k.portable-phase-source.v1","variant":"phase-init"}
        compound={"schema":RULES.COMPOUND_SCHEMA,"variant":RULES.COMPOUND_VARIANT}
        scan={"schema":RULES.SCAN_SCHEMA,"variant":"square-successor"}
        dependency={"schema":"rove4k.profile-dependencies.v1"}
        calls=[];individual=SimpleNamespace(SCHEMA=RULES.SPELLING_SCHEMA)
        def module(label,parent,result,proof,**extra):
            def forward(actual,*args,**kwargs):
                self.assertEqual(actual,parent);return result,proof
            def inverse(actual,observed,**kwargs):
                self.assertEqual((actual,observed),(result,proof));calls.append(label);return parent
            return SimpleNamespace(transform_source=forward,restore_source=inverse,**extra)
        projection=module("resource",base,resource_body,resource,SCHEMA="test-resource")
        phase_module=module("phase",resource_body,phase_body,phase)
        compound_module=module("compound",phase_body,compound_body,compound,SCHEMA=RULES.COMPOUND_SCHEMA)
        scan_module=module("scan",compound_body,scan_body,scan,SCHEMA=RULES.SCAN_SCHEMA)
        dependency_module=module("dependency",scan_body,final,dependency,
            validate_receipt=lambda *args,**kwargs:scan_body)
        modules={"production_rules_projection":projection,"production_rules_phase_projection":phase_module,
            "production_rules_scan_projection":scan_module,"production_rules_dependencies":dependency_module}
        stages=[resource,phase,compound,scan,dependency]
        record={"attempts":[{"directory":name,"source_proofs":stages} for name in ("first","repeat")]}
        with patch.object(RULES,"load",side_effect=lambda name,path:modules[name]), \
             patch.object(RULES,"compound_modules",return_value=(individual,compound_module)), \
             patch.object(RULES,"scan_module",return_value=scan_module), \
             patch.object(RULES,"_source_build_record",return_value=record) as captured:
            self.assertEqual(RULES.admit_source(final,base,stages,"A",PRODUCTION.resource_profile("test-p4"),build=Path("/named")),stages)
        self.assertEqual(calls,["dependency","scan","compound","phase","resource"])
        self.assertEqual(captured.call_args.kwargs["post_scan"],RULES.SCAN_DECLARATION)
        self.assertIn(RULES.SCAN,captured.call_args.kwargs["tools"])
        invalid=(stages[:-1],stages+[scan],[resource,phase,scan,compound,dependency],
            [resource,phase,compound,{**scan,"variant":"unknown"},dependency])
        for proofs in invalid:
            with patch.object(RULES,"load",return_value=projection), self.assertRaises(ValueError):
                RULES.admit_source(final,base,proofs,"A",PRODUCTION.resource_profile("test-p4"),build=Path("/named"))
        with patch.object(RULES,"load",return_value=projection), self.assertRaisesRegex(ValueError,"A/C"):
            RULES.admit_source(final,base,stages,"F",PRODUCTION.resource_profile("test-p4"),build=Path("/named"))


if __name__ == "__main__":
    unittest.main()
