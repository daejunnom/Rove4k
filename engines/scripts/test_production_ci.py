"""CI orchestration boundaries without compilers, engines or large allocations."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("production_ci_test_target", Path(__file__).with_name("production_ci.py"))
CI = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CI
SPEC.loader.exec_module(CI)


def command_row(kind="good", code=0):
    return {"kind": kind, "started": True, "terminal": True, "reaped": True,
            "owned_group_absent": True, "original_identity_retained_until_other_members_absent": True,
            "forced_cleanup": False, "other_group_members_before_reap": [], "returncode": code}


def owner_report(rows=None):
    return {"complete": True, "host_cleanup": {"unsettled_commands": 0, "errors": []},
            "commands": rows if rows is not None else [command_row()]}


class ProductionCIBoundaries(unittest.TestCase):
    def test_actual_pipeline_input_gate_admits_all_current_family_plans(self):
        own = CI.normalized(CI.ROOT / CI.SELF)
        for family in "ABCDEF":
            for spelling in (("control",) if family == "D" else ("control", "best", "compound")):
                with self.subTest(family=family, spelling=spelling):
                    plan = CI.pipeline_plan(family, Path(tempfile.gettempdir()).resolve() / ("ci-inputs-" + family),
                                            spelling_variant=spelling)
                    inputs = CI.pipeline_inputs(plan, own)
                    self.assertEqual(inputs[CI.SELF], own)
                    self.assertEqual(CI.pin(inputs[CI.HOST])["sha256"], CI.HOST_SHA)
                    for stage in plan.stages:
                        name = Path(stage.command[3]).relative_to(CI.ROOT).as_posix()
                        self.assertEqual(inputs[name], CI.normalized(CI.ROOT / name))

    def test_actual_pipeline_input_gate_rejects_stale_host_pin(self):
        own = CI.normalized(CI.ROOT / CI.SELF)
        plan = CI.pipeline_plan("A", Path(tempfile.gettempdir()).resolve() / "ci-inputs-stale")
        with patch.object(CI, "HOST_SHA", "0" * 64):
            with self.assertRaisesRegex(ValueError, "bounded owned command helper differs"):
                CI.pipeline_inputs(plan, own)

    def test_actual_p28_input_closure_binds_its_new_checkers_and_D_source_renderer(self):
        own = CI.normalized(CI.ROOT / CI.SELF)
        for family in "ABCDEF":
            choices = ("control",) if family == "D" else ("best", "compound") if family == "B" else ("compound",)
            for selection in choices:
                with self.subTest(family=family, selection=selection):
                    plan = CI.pipeline_plan(family, Path(tempfile.gettempdir()).resolve() / ("ci-p28-inputs-" + family),
                                            spelling_variant=selection, profile="test-p28")
                    inputs = CI.pipeline_inputs(plan, own)
                    checker = (CI.D_ROOT if family == "D" else CI.NEXT) + "check_profile_p28.py"
                    self.assertEqual(inputs[checker], CI.normalized(CI.ROOT / checker))
                    self.assertEqual(inputs[CI.SELF], own)
                    if family == "D":
                        self.assertEqual(inputs[CI.D_ROOT + "source.py"], CI.normalized(CI.ROOT / CI.D_ROOT / "source.py"))

    def test_bundle_and_target_input_gates_keep_the_executing_reader_boundary(self):
        own = CI.normalized(CI.ROOT / CI.SELF)
        verify = CI.load("production_ci_test_bundle_verify", CI.ROOT / CI.NEXT / "profile_verify.py")
        reader = verify.input_reader()
        root = Path(tempfile.gettempdir()).resolve()
        for family in "ABCDEF":
            plans = (CI.pipeline_plan(family, root / ("ci-export-" + family)),
                     CI.target_plan(family, root / ("ci-target-" + family), root / "sealed/artifact",
                                    root / "source-bundle.zip", root / "source-seal.json"))
            if family != "D":
                plans += tuple(CI.pipeline_plan(family, root / ("ci-export-" + selection + "-" + family),
                    spelling_variant=selection) for selection in ("best", "compound"))
            choices = ("control",) if family == "D" else ("best", "compound") if family == "B" else ("compound",)
            plans += tuple(CI.pipeline_plan(family, root / ("ci-p28-export-" + selection + "-" + family),
                spelling_variant=selection, profile="test-p28") for selection in choices)
            plans += (CI.target_plan(family, root / ("ci-p28-target-" + family), root / "sealed/artifact",
                root / "source-bundle.zip", root / "source-seal.json", profile="test-p28"),)
            for plan in plans:
                with self.subTest(family=family, plan=type(plan).__name__), \
                        patch.object(reader, "read_regular", wraps=reader.read_regular) as reads:
                    inputs = CI.pipeline_inputs(plan, own, verify=verify, reader=reader, transport=object())
                    self.assertTrue(reads.called)
                    for name in (CI.TRANSPORT, CI.NEXT + "target_runtime.py",
                                 CI.NEXT + "profile_compiler.py", verify.INPUT_READER):
                        self.assertIn(name, inputs)
                    self.assertEqual(inputs[verify.INPUT_READER], reader.source_identity())
                    self.assertEqual(CI.pin(inputs[CI.HOST])["sha256"], CI.HOST_SHA)
        with patch.object(reader, "source_identity", return_value=b"changed executing reader"):
            with self.assertRaisesRegex(ValueError, "input reader snapshot differs"):
                CI.pipeline_inputs(plans[0], own, verify=verify, reader=reader, transport=object())

    def test_requested_export_failure_retains_functional_evidence_but_fails_overall(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-export-failure-") as directory:
            root = Path(directory)
            raw = b'{"complete":true}\n'
            report = {**owner_report(), "functional_complete": True}
            calls = []
            def write(*arguments):
                calls.append("exclusive-preimage")
                raise OSError("preimage creation failed")
            transport = SimpleNamespace(_write_new=write,
                export_bundle=lambda *a, **k: self.fail("failed preimage must prevent sealing"))
            reader = SimpleNamespace(read_regular=lambda path, **k: raw)
            with self.assertRaisesRegex(OSError, "preimage creation failed"):
                CI.export_closed_pipeline(report, root, family="D", runner_temp=root.parent,
                    verify=object(), target=object(), transport=transport, ci_context=object(),
                    reader=reader, inputs={}, save=lambda: calls.append("saved-failure"))
            self.assertEqual(calls, ["exclusive-preimage", "saved-failure"])
            self.assertTrue(report["functional_complete"])
            self.assertFalse(report["complete"])
            self.assertEqual(report["export_failure"]["type"], "OSError")
            self.assertNotIn("source_export", report)
            report = {**owner_report(), "functional_complete": True,
                      "host_cleanup": {"unsettled_commands": 1, "errors": []}}
            with self.assertRaisesRegex(ValueError, "closed successful"):
                CI.export_closed_pipeline(report, root, family="A", runner_temp=root.parent,
                    verify=object(), target=object(), transport=transport, ci_context=object(),
                    reader=reader, inputs={}, save=lambda: None)

    def test_target_plan_consumes_sealed_source_without_running_factory_or_native13(self):
        root = Path(tempfile.gettempdir()).resolve()
        for family in "ABCDEF":
            plan = CI.target_plan(family, root / "target", root / "original-source/artifact",
                                  root / "download/source-bundle.zip", root / "download/source-seal.json")
            self.assertEqual([stage.name for stage in plan.stages], ["compiler", "rules", "runtime"])
            self.assertEqual(plan.profile, "test-p4")
            self.assertEqual(plan.workers, 4)
            self.assertEqual(CI.TargetPlan(plan.family, plan.out, plan.build, plan.bundle, plan.seal, plan.stages).profile, "test-p4")
            compiler, _, runtime = [stage.command for stage in plan.stages]
            self.assertIn("--ubuntu22-system", compiler)
            self.assertEqual(compiler[compiler.index("--compiler") + 1], "/usr/bin/cc")
            self.assertFalse(any("profile_build.py" in part or "test_startup.py" in part for stage in plan.stages for part in stage.command))
            self.assertIn("--target-compiler-receipt", runtime)
            self.assertIn("--source-bundle", runtime)
            self.assertIn("--source-seal", runtime)
            self.assertFalse(hasattr(plan, "spelling_variant"))
            self.assertFalse(any("--spelling-variant" in stage.command for stage in plan.stages))
            if family == "D":
                self.assertEqual(runtime[runtime.index("--candidate") + 1], "D-source-jit")
                self.assertNotIn(CI.D_CANDIDATE, runtime)

    def test_target_environment_requires_system_resolution_without_printing_values(self):
        CI.target_environment({"PATH": "/usr/bin:/bin", "VIRTUAL_ENV": "/tmp/owned-venv"})
        for environment in ({"PATH": "/tmp/venv/bin:/usr/bin:/bin"},
                            {"PATH": "/usr/bin:/bin", "LD_AUDIT": ""},
                            {"PATH": "/usr/bin:/bin", "CPATH": "not-printed"},
                            {"PATH": "/usr/bin:/bin", "CC": "not-printed"}):
            with self.assertRaisesRegex(ValueError, "sanitized system PATH") as error:
                CI.target_environment(environment)
            self.assertNotIn("not-printed", str(error.exception))

    def test_target_system_compiler_gate_is_separate_from_default13(self):
        banner = b"cc (Ubuntu 11.4.0-1ubuntu1) 11.4.0\n"
        self.assertEqual(CI.target_compiler_record(banner, b"11.4.0\n")["full_version"], "11.4.0")
        with self.assertRaisesRegex(ValueError, "separate pipeline"):
            CI.compiler_record(banner, b"11.4.0\n")
        with self.assertRaisesRegex(ValueError, "system cc11.4.0"):
            CI.target_compiler_record(b"cc (Ubuntu 13.3.0) 13.3.0\n", b"13.3.0\n")

    def test_owned_driver_and_tests_parse_with_python310_grammar(self):
        import ast
        for path in (Path(CI.__file__), Path(__file__)):
            ast.parse(path.read_text(), filename=str(path), feature_version=(3, 10))

    def test_target_inspector_keeps_cc11_image_separate_from_original_cc13_contract(self):
        for profile in ("test-p4", "test-p28"):
            with tempfile.TemporaryDirectory(prefix="rove-ci-target-reference-") as directory:
                root = Path(directory)
                plan = CI.target_plan("A", root, root / "original/artifact",
                                      root / "source-bundle.zip", root / "source-seal.json", profile=profile)
                for child in (root / "compiler", root / "runtime"):
                    child.mkdir()
                old = {"native_bytes": 32, "native_sha256": "a" * 64}
                target_pin = {"bytes": 40, "sha256": "b" * 64}
                source_contract = {"post_spelling": {"path": CI.NEXT + "spelling_compound.py",
                    "selection": "compound", "variant": "clock-atomic-launcher"}}
                sealed_contract = json.loads(json.dumps(source_contract))
                admitted = SimpleNamespace(expected=old, source_contract=source_contract)
                record = {"family": "A", "profile": profile, "factory_replayed_on_target": False,
                          "target_native": target_pin,
                          "execution_admission": CI.pin(json.dumps({"source_contract": source_contract}, sort_keys=True).encode())}
                calls = []
                class Reference:
                    native_pin = target_pin
                    def to_record(self):
                        return record
                    def revalidate(self, **keywords):
                        calls.append("revalidate")
                def validate(*arguments, **keywords):
                    calls.append("validated-object")
                    self.assertIs(arguments[0], admitted)
                    self.assertEqual(arguments[1], plan.build)
                    self.assertEqual(keywords["source_bundle"], plan.bundle)
                    self.assertEqual(keywords["source_seal"], plan.seal)
                    return Reference()
                target = SimpleNamespace(COMPILER_FORMAT="compiler-fixture", validate_target_runtime=validate)
                checks = dict.fromkeys(CI.QUALIFICATION_CHECKS, True)
                checks["placement"] = False
                qualified = {"functional_runtime_complete": True, "target_compiler_bound": True,
                    "target_runtime_reference": record, "checks": checks, "complete": False,
                    "failures": ["placement"], "artifact": {"native_sha256": target_pin["sha256"]}, "observations": {}}
                def check(*arguments, **keywords):
                    self.assertIsInstance(keywords["target_reference"], Reference)
                    calls.append("runtime-rechecked")
                    return qualified
                reads = []
                def read_regular(path, *, limit):
                    reads.append((path, limit))
                    return path.read_bytes()
                verify = SimpleNamespace(qualification_record=check,
                                         input_reader=lambda: SimpleNamespace(read_regular=read_regular))
                inspect = CI.target_inspector(plan, verify, admitted, target, object())
                compiler = owner_report()
                compiler.update(format="compiler-fixture", engine_executed=False, large_TT_allocated=False)
                (root / "compiler/compiler.json").write_text(json.dumps(compiler))
                runtime = {"target_runtime_reference": record, "target_context_before_post_unchanged": True,
                           "expected_contract": old, "runtime_native_contract": target_pin,
                           "counts": {"GO": 24, "legal_bestmoves": 22}}
                (root / "runtime/runtime.json").write_text(json.dumps(runtime))
                (root / "runtime/qualification.json").write_text(json.dumps(qualified))
                inspect(plan, plan.stages[0])
                accepted = inspect(plan, plan.stages[-1])
                self.assertEqual(accepted["target_runtime_reference"], record)
                self.assertEqual(admitted.source_contract, sealed_contract)
                self.assertNotIn("requested_spelling_variant", accepted)
                self.assertNotIn("effective_spelling_variant", accepted)
                self.assertEqual(accepted["artifact"]["native_sha256"], target_pin["sha256"])
                self.assertFalse(accepted["factory_replayed_on_target"])
                self.assertIn("revalidate", calls)
                self.assertTrue(reads)
                self.assertTrue(all(limit == 64 << 20 for _, limit in reads))
                for field, value in (("runtime_native_contract", {"bytes": old["native_bytes"], "sha256": old["native_sha256"]}),
                                     ("expected_contract", {"native_bytes": 40, "native_sha256": target_pin["sha256"]})):
                    changed = {**runtime, field: value}
                    (root / "runtime/runtime.json").write_text(json.dumps(changed))
                    with self.subTest(field=field), self.assertRaisesRegex(ValueError, "original source"):
                        inspect(plan, plan.stages[-1])

    def test_plans_keep_six_families_and_fixed_profiles_separate(self):
        root = Path(tempfile.gettempdir()).resolve()
        for family in "ABCDEF":
            with self.subTest(family=family):
                plan = CI.pipeline_plan(family, root / ("ci-" + family))
                self.assertEqual(plan.spelling_variant, "control")
                self.assertEqual(plan.profile, "test-p4")
                self.assertEqual(plan.workers, 4)
                self.assertEqual(plan.effective_spelling_variant, "control")
                self.assertEqual(CI.Plan(family, plan.out, plan.stages).spelling_variant, "control")
                self.assertEqual([stage.name for stage in plan.stages], ["generation", "mechanism", "rules", "runtime"])
                self.assertTrue(all(stage.command[1:3] == ("-I", "-B") for stage in plan.stages))
                generation, mechanism, rules, runtime = [stage.command for stage in plan.stages]
                self.assertEqual(generation[generation.index("--profile") + 1], "test-p4")
                self.assertNotIn("tcec-provisional", generation)
                if family == "D":
                    self.assertNotIn("--spelling-variant", generation)
                    self.assertNotIn("--source-dependencies", generation)
                    self.assertEqual(generation[generation.index("--storage") + 1], "prefix")
                    self.assertIn("--build", mechanism)
                    self.assertEqual(runtime[runtime.index("--candidate") + 1], CI.D_CANDIDATE)
                    self.assertNotIn("--source", rules)
                elif family == "B":
                    self.assertIn("tcec-final-lf", generation)
                    self.assertEqual(mechanism[mechanism.index("--mode") + 1], "bound")
                else:
                    self.assertIn("phase-init", generation)
                    self.assertIn("--build", mechanism)
                    self.assertNotIn("--entry", mechanism)
                if family != "D":
                    self.assertEqual(generation[generation.index("--spelling-variant") + 1], "control")
                    self.assertEqual(generation[generation.index("--source-dependencies") + 1], "unused-includes")
                self.assertEqual(runtime[runtime.index("--rules") + 1], str(plan.out / "rules/probe/rules.json"))
        for retired in ("F8", "Rust", "a", "", "../A"):
            with self.assertRaisesRegex(ValueError, "active C family"):
                CI.pipeline_plan(retired, root / "no-read")

    def test_profile_is_trailing_and_p28_routes_are_finite_full_resource_plans(self):
        root = Path(tempfile.gettempdir()).resolve()
        for family in "ABCDEF":
            selection = "control" if family == "D" else "best" if family == "B" else "compound"
            plan = CI.pipeline_plan(family, root / ("p28-" + family), profile="test-p28", spelling_variant=selection)
            self.assertEqual((plan.profile, plan.workers, plan.spelling_variant), ("test-p28", 28, selection))
            generation, mechanism, rules, _ = [stage.command for stage in plan.stages]
            self.assertEqual(generation[generation.index("--profile") + 1], "test-p28")
            self.assertEqual(Path(mechanism[3]), CI.ROOT / (CI.D_ROOT if family == "D" else CI.NEXT) / "check_profile_p28.py")
            self.assertEqual(plan.stages[1].receipt, "mechanism/results.json")
            if family != "D":
                self.assertEqual(rules[rules.index("--profile") + 1], "test-p28")
            target = CI.target_plan(family, root / "target-p28", root / "sealed/artifact",
                root / "source-bundle.zip", root / "source-seal.json", profile="test-p28")
            self.assertEqual((target.profile, target.workers), ("test-p28", 28))
            self.assertFalse(any("--spelling-variant" in stage.command for stage in target.stages))
            if family != "D":
                self.assertEqual(target.stages[1].command[target.stages[1].command.index("--profile") + 1], "test-p28")
        old = CI.pipeline_plan("A", root / "old")
        self.assertEqual((CI.Plan("A", old.out, old.stages, "best").spelling_variant,
                          CI.Plan("A", old.out, old.stages, "best").profile), ("best", "test-p4"))
        for profile in ("tcec-provisional", "test-p16", "", None, True):
            with self.subTest(profile=profile), self.assertRaisesRegex(ValueError, "TEST-P4 or TEST-P28"):
                CI.pipeline_plan("D", root / "uncreated", profile=profile)
            with self.assertRaisesRegex(ValueError, "TEST-P4 or TEST-P28"):
                CI.target_plan("D", root / "uncreated", root / "build", root / "bundle", root / "seal", profile=profile)

    def test_unsupported_p28_producer_choices_fail_before_outputs_and_context(self):
        root = Path(tempfile.gettempdir()).resolve() / "rove-ci-p28-uncreated"
        for family in "ABCDEF":
            unsupported = ("best", "compound") if family == "D" else ("control",) if family == "B" else ("control", "best")
            for selection in unsupported:
                with self.subTest(family=family, selection=selection), self.assertRaises(ValueError):
                    CI.pipeline_plan(family, root, spelling_variant=selection, profile="test-p28")
            argv = ["production_ci.py", "--family", family, "--profile", "test-p28", "--out", str(root)]
            if family == "D":
                argv += ["--spelling-variant", "compound"]
            with patch.object(sys, "argv", argv), patch.object(CI, "admit_output") as output, \
                    patch.object(CI.Path, "read_text") as read:
                with self.assertRaisesRegex(ValueError, "supports only control|TEST-P28 requires"):
                    CI.main()
                output.assert_not_called()
                read.assert_not_called()
        self.assertFalse(root.exists())

    def test_source_export_forwards_an_explicit_profile_to_transport(self):
        for profile in ("test-p4", "test-p28"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory(prefix="rove-ci-export-profile-") as temporary:
                root = Path(temporary).resolve()
                report = {**owner_report(), "functional_complete": True, "profile": profile}
                calls = []
                def export(*args, **keywords):
                    calls.append(keywords)
                    return {"profile": keywords["profile"]}
                transport = SimpleNamespace(_write_new=lambda *args: None, export_bundle=export)
                reader = SimpleNamespace(read_regular=lambda *args, **keywords: b"controlled functional bytes")
                CI.export_closed_pipeline(report, root, family="A", runner_temp=root.parent, verify=object(),
                    target=object(), transport=transport, ci_context=object(), reader=reader, inputs={}, save=lambda: None,
                    profile=profile)
                self.assertEqual(calls[0]["profile"], profile)
                self.assertEqual(report["source_export"], {"profile": profile})

    def test_target_inspector_rejects_a_validated_reference_for_another_explicit_profile(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-target-profile-") as temporary:
            root = Path(temporary).resolve()
            (root / "compiler").mkdir()
            plan = CI.target_plan("A", root, root / "source/artifact", root / "source-bundle.zip",
                                  root / "source-seal.json", profile="test-p28")
            report = {**owner_report(), "format": "compiler-fixture", "engine_executed": False, "large_TT_allocated": False}
            (root / "compiler/compiler.json").write_text(json.dumps(report))
            reference = SimpleNamespace(to_record=lambda: {"family": "A", "profile": "test-p4", "factory_replayed_on_target": False})
            target = SimpleNamespace(COMPILER_FORMAT="compiler-fixture", validate_target_runtime=lambda *a, **k: reference)
            verify = SimpleNamespace(input_reader=lambda: SimpleNamespace(read_regular=lambda path, **k: path.read_bytes()))
            inspect = CI.target_inspector(plan, verify, object(), target, object())
            with self.assertRaisesRegex(ValueError, "sealed single-family profile"):
                inspect(plan, plan.stages[0])

    def test_p28_target_restore_forwards_profile_and_rejects_relabelled_admission(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-restore-profile-") as temporary:
            root = Path(temporary).resolve()
            build = root / "original/artifact"
            build.mkdir(parents=True)
            (build / "build.json").write_text("{}")
            reader = SimpleNamespace(source_identity=lambda: b"trusted fixture reader",
                read_regular=lambda path, **kw: path.read_bytes())
            admitted = SimpleNamespace(family="A", profile_id="test-p28", representation="source-jit")
            context = object()
            target = SimpleNamespace(CIContext=SimpleNamespace(from_environment=lambda: context))
            verify = SimpleNamespace(input_reader=lambda: reader, executing_source=lambda data: None,
                target_module=lambda: target, artifact_file=lambda directory, name: directory / name,
                admit_c_build=lambda manifest, directory: admitted)
            restored = []
            def restore(*args, **kw):
                restored.append(kw)
                return {"build_root": str(build)}
            transport = SimpleNamespace(restore_bundle=restore)
            argv = ["production_ci.py", "--family", "A", "--profile", "test-p28", "--ubuntu22-target",
                    "--source-bundle", str(root / "source.zip"), "--source-seal", str(root / "seal.json"),
                    "--out", str(root / "out")]
            read_text = Path.read_text
            def read(path, *args, **kw):
                return 'ID=ubuntu\nVERSION_ID="22.04"\n' if str(path) == "/etc/os-release" else read_text(path, *args, **kw)
            for wrong in (False, True):
                admitted.profile_id = "test-p4" if wrong else "test-p28"
                with patch.object(sys, "argv", argv), patch.object(sys, "platform", "linux"), \
                        patch.object(CI.platform, "machine", return_value="x86_64"), \
                        patch.dict(CI.os.environ, {"PATH": "/usr/bin:/bin", "RUNNER_TEMP": str(root)}, clear=True), \
                        patch.object(Path, "read_text", read), patch.object(CI, "admit_output", return_value=root / "out"), \
                        patch.object(CI, "load", side_effect=lambda name, path: transport if name.endswith("transport") else verify), \
                        patch.object(CI, "pipeline_inputs", side_effect=RuntimeError("stop before output")) as closure:
                    with self.assertRaisesRegex(ValueError if wrong else RuntimeError,
                            "requested fixed full TEST" if wrong else "stop before output"):
                        CI.main()
                    self.assertEqual(closure.call_count, 0 if wrong else 1)
                self.assertEqual(restored[-1]["profile"], "test-p28")
            self.assertFalse((root / "out").exists())

    def test_p28_generation_requires_exact_requested_profile_and_tt_geometry(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-p28-generation-") as temporary:
            root = Path(temporary).resolve()
            (root / "artifact").mkdir()
            path = root / "artifact/build.json"
            for family, selection in ((f, "compound") for f in "ABCEF"):
                plan = CI.pipeline_plan(family, root, profile="test-p28", spelling_variant=selection)
                resources = {"id": "test-p28", "workers": 28, "tt_cap_bytes": 512 << 20,
                    "tt_bits": 24, "tt_entries": 1 << 24, "tt_bytes": 384 << 20,
                    "tt_entry_bytes": 24, "tt_mask": (1 << 24) - 1}
                good = {**owner_report(), "family": family, "class": "rove4k-production-profile-v1",
                    "reproducible": True, "resources": resources, "plan": {"representation": "source-jit"},
                    "post_profile": {"path": CI.NEXT + ("profile_b.py" if family == "B" else "profile_phase.py"),
                                     "variant": "tcec-final-lf" if family == "B" else "phase-init"},
                    "post_spelling": CI.spelling_declaration(family, selection, profile="test-p28"),
                    "source_dependencies": {"path": CI.NEXT + "profile_dependencies.py", "variant": "unused-includes"}}
                if family == "B":
                    good["spelling_request"] = {"requested": "compound", "effective": "best", "duplicate_best": True,
                                                "new_candidate_count": 0}
                path.write_text(json.dumps(good))
                self.assertEqual(CI.check_stage(plan, plan.stages[0])["effective_spelling_variant"],
                                 "best" if family == "B" else "compound")
                for key, value in (("id", "test-p4"), ("workers", 4), ("tt_bits", 22),
                        ("tt_entries", 1 << 22), ("tt_bytes", 96 << 20), ("tt_entry_bytes", 16),
                        ("tt_mask", (1 << 22) - 1), ("tt_cap_bytes", 128 << 20), ("tt_bits", 24.0)):
                    changed = json.loads(json.dumps(good))
                    changed["resources"][key] = value
                    path.write_text(json.dumps(changed))
                    with self.subTest(family=family, field=key), self.assertRaisesRegex(ValueError, "fixed TEST-P28|exact actual"):
                        CI.check_stage(plan, plan.stages[0])

    def test_best_plans_select_only_the_producer_and_keep_consumers_unchanged(self):
        root = Path(tempfile.gettempdir()).resolve()
        for family in "ABCEF":
            control = CI.pipeline_plan(family, root / ("spelling-" + family))
            best = CI.pipeline_plan(family, control.out, spelling_variant="best")
            self.assertEqual(best.spelling_variant, "best")
            generation = best.stages[0].command
            self.assertEqual(generation[generation.index("--spelling-variant") + 1], "best")
            self.assertEqual(generation[generation.index("--source-dependencies") + 1], "unused-includes")
            self.assertEqual(best.stages[1:], control.stages[1:])
        for family, selection in (("D", "best"), ("D", "compound"), ("A", "clock-type"), ("F", None), ("A", True)):
            with self.subTest(family=family, selection=selection), self.assertRaises(ValueError):
                CI.pipeline_plan(family, root / "uncreated", spelling_variant=selection)
        self.assertFalse((root / "uncreated").exists())

    def test_compound_plans_preserve_requests_and_select_the_exact_effective_route(self):
        root = Path(tempfile.gettempdir()).resolve()
        compound = {"path": CI.NEXT + "spelling_compound.py", "selection": "compound",
                    "variant": "clock-atomic-launcher"}
        for family in "ABCEF":
            plan = CI.pipeline_plan(family, root / ("compound-" + family), spelling_variant="compound")
            self.assertEqual(plan.spelling_variant, "compound")
            self.assertEqual(plan.stages[0].command[plan.stages[0].command.index("--spelling-variant") + 1], "compound")
            if family == "B":
                self.assertEqual(plan.effective_spelling_variant, "best")
                self.assertEqual(CI.spelling_declaration(family, "compound"),
                    {"path": CI.NEXT + "profile_spelling.py", "selection": "best", "variant": "atomic-assignment"})
                self.assertEqual(plan.stages[1:], CI.pipeline_plan(family, plan.out, spelling_variant="best").stages[1:])
            else:
                self.assertEqual(plan.effective_spelling_variant, "compound")
                self.assertEqual(CI.spelling_declaration(family, "compound"), compound)
                self.assertEqual(Path(plan.stages[1].command[3]).name, "check_profile_compound.py")
                self.assertEqual(plan.stages[1].receipt, "mechanism/results.json")
                self.assertEqual(plan.stages[2:], CI.pipeline_plan(family, plan.out).stages[2:])

    def test_producer_cli_defaults_to_control_and_forwards_explicit_best(self):
        class PlanReached(Exception):
            pass
        with tempfile.TemporaryDirectory(prefix="rove-ci-policy-cli-") as temporary:
            root = Path(temporary).resolve()
            for option, expected in (([], "control"), (["--spelling-variant", "control"], "control"),
                                     (["--spelling-variant", "best"], "best"),
                                     (["--spelling-variant", "compound"], "compound")):
                argv = ["production_ci.py", "--family", "A", "--out", str(root / "out"), *option]
                with self.subTest(expected=expected), patch.object(sys, "argv", argv), \
                        patch.object(CI.sys, "platform", "linux"), \
                        patch.object(CI.platform, "machine", return_value="x86_64"), \
                        patch.object(CI.Path, "read_text", return_value='ID=ubuntu\nVERSION_ID="24.04"\n'), \
                        patch.dict(CI.os.environ, {"RUNNER_TEMP": str(root)}), \
                        patch.object(CI, "pipeline_plan", side_effect=PlanReached) as plan:
                    with self.assertRaises(PlanReached):
                        CI.main()
                    plan.assert_called_once_with("A", root / "out", spelling_variant=expected, scan_variant="control", profile="test-p4")
                self.assertFalse((root / "out").exists())

    def test_d_best_and_explicit_target_policy_fail_before_output_or_context_reads(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-policy-reject-") as temporary:
            root = Path(temporary).resolve()
            cases = [("D", ["--spelling-variant", selection], "D supports only control")
                     for selection in ("best", "compound")]
            for selection in ("control", "best", "compound"):
                cases.append(("A", ["--ubuntu22-target", "--source-bundle", str(root / "source-bundle.zip"),
                    "--source-seal", str(root / "source-seal.json"), "--spelling-variant", selection], "producer-only"))
            for family, options, error in cases:
                argv = ["production_ci.py", "--family", family, "--out", str(root / "out"), *options]
                with self.subTest(family=family, options=options), patch.object(sys, "argv", argv), \
                        patch.object(CI, "admit_output") as output, patch.object(CI, "load") as load, \
                        patch.object(CI.Path, "read_text") as read:
                    with self.assertRaisesRegex(ValueError, error):
                        CI.main()
                    output.assert_not_called()
                    load.assert_not_called()
                    read.assert_not_called()
                self.assertFalse((root / "out").exists())

    def test_generation_cannot_substitute_another_spelling_or_dependency_policy(self):
        variants = {"A": "clock-type", "B": "atomic-assignment", "C": "clock-type",
                    "E": "clock-type", "F": "atomic-assignment"}
        with tempfile.TemporaryDirectory(prefix="rove-ci-generation-policy-") as temporary:
            root = Path(temporary).resolve()
            (root / "artifact").mkdir()
            path = root / "artifact/build.json"
            for family, variant in variants.items():
                for selection in ("control", "best", "compound"):
                    plan = CI.pipeline_plan(family, root, spelling_variant=selection)
                    expected = (None if selection == "control" else
                        {"path": CI.NEXT + "spelling_compound.py", "selection": "compound", "variant": "clock-atomic-launcher"}
                        if selection == "compound" and family != "B" else
                        {"path": CI.NEXT + "profile_spelling.py", "selection": "best", "variant": variant})
                    good = {**owner_report(), "family": family, "class": "rove4k-production-profile-v1",
                        "reproducible": True, "resources": {"id": "test-p4", "workers": 4},
                        "plan": {"representation": "source-jit"},
                        "post_profile": {"path": CI.NEXT + ("profile_b.py" if family == "B" else "profile_phase.py"),
                                         "variant": "tcec-final-lf" if family == "B" else "phase-init"},
                        "post_spelling": expected,
                        "source_dependencies": {"path": CI.NEXT + "profile_dependencies.py", "variant": "unused-includes"},
                        "expected_contract": {"native_bytes": 32, "native_sha256": "a" * 64}}
                    if family == "B" and selection == "compound":
                        good["spelling_request"] = {"requested": "compound", "effective": "best",
                            "duplicate_best": True, "new_candidate_count": 0}
                    path.write_text(json.dumps(good))
                    original = path.read_bytes()
                    accepted = CI.check_stage(plan, plan.stages[0])
                    self.assertEqual(accepted["requested_spelling_variant"], selection)
                    if selection == "compound":
                        self.assertEqual(accepted["effective_spelling_variant"], "best" if family == "B" else "compound")
                    else:
                        self.assertNotIn("effective_spelling_variant", accepted)
                    self.assertEqual(path.read_bytes(), original)
                    best = {"path": CI.NEXT + "profile_spelling.py", "selection": "best", "variant": variant}
                    mutations = [("post_spelling", None if selection != "control" else best),
                                 ("post_spelling", {**best, "variant": "atomic-assignment" if variant == "clock-type" else "clock-type"}),
                                 ("post_spelling", {**best, "path": CI.NEXT + "profile_phase.py"}),
                                 ("post_spelling", {**best, "selection": "control"}),
                                 ("source_dependencies", None),
                                 ("source_dependencies", {"path": CI.NEXT + "profile_dependencies.py", "variant": "control"}),
                                 ("source_dependencies", {"path": "other.py", "variant": "unused-includes"}),
                                 ("source_dependencies", {**good["source_dependencies"], "extra": True})]
                    for key, value in mutations:
                        with self.subTest(family=family, selection=selection, key=key, value=value):
                            path.write_text(json.dumps({**good, key: value}))
                            with self.assertRaisesRegex(ValueError, "requested producer policy"):
                                CI.check_stage(plan, plan.stages[0])
                    for key in ("post_spelling", "source_dependencies"):
                        changed = dict(good)
                        del changed[key]
                        path.write_text(json.dumps(changed))
                        with self.subTest(family=family, selection=selection, missing=key), \
                                self.assertRaisesRegex(ValueError, "requested producer policy"):
                            CI.check_stage(plan, plan.stages[0])
            invalid = CI.Plan("F", root, plan.stages, "invalid")
            with self.assertRaisesRegex(ValueError, "finite producer spelling"):
                CI.check_stage(invalid, invalid.stages[0])

    def test_b_compound_requires_exact_typed_duplicate_metadata_and_no_new_tool_stage(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-B-compound-") as temporary:
            root = Path(temporary).resolve()
            (root / "artifact").mkdir()
            path = root / "artifact/build.json"
            plan = CI.pipeline_plan("B", root, spelling_variant="compound")
            request = {"requested": "compound", "effective": "best", "duplicate_best": True, "new_candidate_count": 0}
            good = {**owner_report(), "family": "B", "class": "rove4k-production-profile-v1", "reproducible": True,
                "resources": {"id": "test-p4", "workers": 4}, "plan": {"representation": "source-jit"},
                "post_profile": {"path": CI.NEXT + "profile_b.py", "variant": "tcec-final-lf"},
                "post_spelling": {"path": CI.NEXT + "profile_spelling.py", "selection": "best", "variant": "atomic-assignment"},
                "source_dependencies": {"path": CI.NEXT + "profile_dependencies.py", "variant": "unused-includes"},
                "spelling_request": request}
            for bad in (None, {**request, "requested": "best"}, {**request, "effective": "compound"},
                        {**request, "duplicate_best": 1}, {**request, "new_candidate_count": False},
                        {**request, "new_candidate_count": 1}, {**request, "extra": True}):
                with self.subTest(bad=bad):
                    path.write_text(json.dumps({**good, "spelling_request": bad}))
                    with self.assertRaisesRegex(ValueError, "existing best duplicate"):
                        CI.check_stage(plan, plan.stages[0])
            absent = dict(good)
            del absent["spelling_request"]
            path.write_text(json.dumps(absent))
            with self.assertRaisesRegex(ValueError, "existing best duplicate"):
                CI.check_stage(plan, plan.stages[0])
            path.write_text(json.dumps(good))
            for request_selection in ("control", "best"):
                altered = {**good, "post_spelling": None if request_selection == "control" else good["post_spelling"]}
                path.write_text(json.dumps(altered))
                requested = CI.pipeline_plan("B", root, spelling_variant=request_selection)
                with self.assertRaisesRegex(ValueError, "unexpected spelling request"):
                    CI.check_stage(requested, requested.stages[0])

    def compound_receipt_fixture(self, root, family="A"):
        """Inert owned files exercise receipt joins, never native/source admission."""
        plan = CI.pipeline_plan(family, root, spelling_variant="compound")
        replacement = "J" if family == "F" else "rv"
        source = ("#define RVN ((size_t)1<<22)\nvoid " + replacement + "(void){}\n").encode()
        text = "\n#define rv_spawn " + replacement + "\n"
        prefix = source + text.encode()
        fixture = (b"#define main rv_unused_shipping_main\n" + prefix.replace(b"1<<22", b"1<<18", 1) +
                   b"/* scaled callbacks */\n")
        startup = source + b"/* unaliased last initializer */\n"
        native = b"inert diagnostic image"
        output = b"uciok\nreadyok\nbestmove a2a3\nreadyok\nbestmove b2b3\nreadyok\n"
        flags = ("every_callback_entered", "all_entries_initialized", "worker_storage_unchanged_except_id_depth",
                 "pending_zero", "join_count_zero", "startup_history_zero")
        observation = {"workers": 4, "entries": 1 << 18, **dict.fromkeys(flags, True)}
        scaled_output = b"bestmove g1f3\nbestmove b1c3\n" + json.dumps(observation).encode() + b"\n"
        component = {"schema": "rove4k.selected-spelling-experiment.v1", "variant": "launcher-short",
                     "family": family, "profile_id": "test-p4", "edits": [{"before": "rv_spawn", "after": replacement}]}
        declaration = {"path": CI.NEXT + "spelling_compound.py", "selection": "compound", "variant": "clock-atomic-launcher"}
        build = {"family": family, "post_profile": {"path": CI.NEXT + "profile_phase.py", "variant": "phase-init"},
                 "post_spelling": declaration,
                 "source_dependencies": {"path": CI.NEXT + "profile_dependencies.py", "variant": "unused-includes"},
                 "source_proofs": [{"schema": "rove4k.selected-spelling-compound.v1", "family": family,
                    "profile_id": "test-p4", "variant": "clock-atomic-launcher",
                    "components": ["clock-type", "atomic-assignment", "launcher-short"],
                    "individual": [{"variant": "launcher-short", "proof": component}]}]}
        def write(name, data):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return {"path": str(path), **CI.pin(data)}
        write("artifact/main.c", source)
        build_pin = write("artifact/build.json", json.dumps(build).encode())
        checker = write("inputs/" + CI.NEXT + "check_profile_compound.py", b"inert checker source")
        for name, data in (("diagnostic-prefix.c", prefix), ("fixture.c", fixture), ("x", native)):
            write("mechanism/selected-W4-scaled-callback/" + name, data)
        write("mechanism/selected-W4-last-initializer/fixture.c", startup)
        write("mechanism/selected-W4-last-initializer/runtime.stdout", output)
        scaled_pin = write("mechanism/tool-2-selected-W4-scaled-callback-execute.stdout", scaled_output)
        commands = [command_row(name) for name in ("selected-W4-scaled-callback-compile",
            "selected-W4-scaled-callback-execute", "selected-W4-last-initializer-compile")]
        commands[1]["stdout"] = scaled_pin
        cleanup = {"forced_cleanup": False, "errors": [], "settled_before_cleanup": True,
                   "owned_group_absent": True, "readers_joined": True, "reaped": True, "pre_reap_other_members": []}
        physical = {"returncode": 0, "readers_joined": True, "stdout_eof": True, "stderr_eof": True,
            "reaped": True, "original_identity_retained_until_other_members_absent": True,
            "forced_cleanup": False, "pre_reap_other_members": []}
        alias = {"macro": "rv_spawn", "replacement": replacement, "text": text, "shipping_source": CI.pin(source),
                 "diagnostic_prefix": CI.pin(prefix), "launcher_component": component}
        report = {**owner_report(commands), "class": "rove4k-bound-compound-mechanism-v1", "source_bound": True,
            "entry": family, "profile": "test-p4", "mode": "source-bound", "representation": "source-jit",
            "selected_post_profile": build["post_profile"], "selected_post_spelling": declaration,
            "source_dependencies": build["source_dependencies"],
            "build": {**build_pin, "path": str(root / "artifact")},
            "actual": {"source": {"path": "main.c", **CI.pin(source)}}, "diagnostic_alias": alias,
            "support_inputs": {CI.NEXT + "check_profile_compound.py": {key: checker[key] for key in ("bytes", "sha256")}},
            **dict.fromkeys(("shipping_binary_executed", "large_submission_tt_executed", "derived_other_resource_profiles",
                            "timing_claimed", "production_adopted", "runtime_qualified"), False),
            "runtime_cleanup": {"remaining_owned": 0, "drained": [], "errors": []},
            "mechanisms": [{"profile": "test-p4", "variant": "clock-atomic-launcher", "shipping_source": CI.pin(source),
                "diagnostic_prefix_source": CI.pin(prefix), "fixture_source": CI.pin(fixture), "native": CI.pin(native),
                "observation": observation, "output": CI.pin(scaled_output), "fixture_tt_entries": 1 << 18,
                "selector_results": ["bestmove g1f3", "bestmove b1c3"], "shipping_worker_count_unchanged": True,
                **dict.fromkeys(("shipping_tt_executed", "shipping_binary_executed", "search_executed"), False)}],
            "startup_barriers": [{"variant": "clock-atomic-launcher", "shipping_source": CI.pin(source),
                "fixture_source": CI.pin(startup), "output": CI.pin(output), "physical": physical, "cleanup": cleanup,
                "actual_resource_profile": "test-p4", "actual_workers": 4, "actual_tt_entries": 1 << 22,
                "legal_search_relaunches": 2, "diagnostic_alias_applied": False, "shipping_identity_claimed": False,
                **dict.fromkeys(("last_initializer_delayed", "no_uci_before_release", "uci_ready_after_release",
                                "gate_arrival_observed", "post_GO2_join_observed", "private_copy_removed"), True)}],
            "barrier_runtime_cleanup": [{"directory": str(root / "mechanism/selected-W4-last-initializer/runtime"),
                                          "pid": 1234, "cleanup": cleanup}]}
        path = root / "mechanism/results.json"
        path.write_text(json.dumps(report))
        return plan, report, path

    def test_compound_mechanism_joins_alias_diagnostic_and_unaliased_startup_evidence(self):
        for family in "ACEF":
            with self.subTest(family=family), tempfile.TemporaryDirectory(prefix="rove-ci-compound-receipt-") as temporary:
                plan, report, path = self.compound_receipt_fixture(Path(temporary).resolve(), family)
                accepted = CI.check_stage(plan, plan.stages[1])
                self.assertEqual(accepted["diagnostic_alias"], report["diagnostic_alias"])
                self.assertEqual(json.loads(path.read_bytes()), report)

    def test_compound_mechanism_rejects_legacy_incomplete_or_rebound_receipts(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-compound-reject-") as temporary:
            plan, good, path = self.compound_receipt_fixture(Path(temporary).resolve())
            changes = [(("class",), "rove4k-bound-phase-mechanism-v1", "selected mechanism build"),
                (("selected_post_spelling",), None, "different source policy"),
                (("diagnostic_alias", "replacement"), "J", "diagnostic alias"),
                (("diagnostic_alias", "launcher_component"), {}, "diagnostic alias"),
                (("support_inputs", CI.NEXT + "check_profile_compound.py"), {}, "frozen CI input"),
                (("shipping_binary_executed",), True, "scope or owned command"),
                (("commands",), good["commands"][:-1], "owned command sequence"),
                (("mechanisms", 0, "observation", "pending_zero"), False, "declared state"),
                (("mechanisms", 0, "fixture_source"), {}, "bytes differ"),
                (("startup_barriers", 0, "actual_workers"), 3, "startup gate"),
                (("startup_barriers", 0, "diagnostic_alias_applied"), True, "unaliased actual resource"),
                (("startup_barriers", 0, "physical", "returncode"), False, "finish naturally"),
                (("startup_barriers", 0, "cleanup", "forced_cleanup"), True, "finish naturally"),
                (("runtime_cleanup", "remaining_owned"), 1, "runtime cleanup"),
                (("barrier_runtime_cleanup",), [], "cleanup journal")]
            for keys, value, error in changes:
                changed = json.loads(json.dumps(good))
                target = changed
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                path.write_text(json.dumps(changed))
                with self.subTest(keys=keys), self.assertRaisesRegex(ValueError, error):
                    CI.check_stage(plan, plan.stages[1])
            for missing, error in (("diagnostic_alias", "diagnostic alias"),
                                   ("selected_post_spelling", "different source policy"),
                                   ("startup_barriers", "startup gate")):
                changed = json.loads(json.dumps(good))
                del changed[missing]
                path.write_text(json.dumps(changed))
                with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, error):
                    CI.check_stage(plan, plan.stages[1])

    def test_compound_mechanism_rejects_changed_diagnostic_and_startup_files(self):
        files = ("selected-W4-scaled-callback/diagnostic-prefix.c", "selected-W4-scaled-callback/fixture.c",
                 "selected-W4-scaled-callback/x", "selected-W4-last-initializer/runtime.stdout")
        for name in files:
            with self.subTest(name=name), tempfile.TemporaryDirectory(prefix="rove-ci-compound-files-") as temporary:
                root = Path(temporary).resolve()
                plan, _, _ = self.compound_receipt_fixture(root)
                path = root / "mechanism" / name
                path.write_bytes(path.read_bytes() + b"changed")
                with self.assertRaisesRegex(ValueError, "bytes differ"):
                    CI.check_stage(plan, plan.stages[1])
        with tempfile.TemporaryDirectory(prefix="rove-ci-startup-alias-") as temporary:
            root = Path(temporary).resolve()
            plan, report, receipt = self.compound_receipt_fixture(root)
            path = root / "mechanism/selected-W4-last-initializer/fixture.c"
            path.write_bytes(path.read_bytes() + b"\n#define rv_spawn rv\n")
            report["startup_barriers"][0]["fixture_source"] = CI.pin(path.read_bytes())
            receipt.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "alias-free startup bytes"):
                CI.check_stage(plan, plan.stages[1])
        with tempfile.TemporaryDirectory(prefix="rove-ci-diagnostic-main-") as temporary:
            root = Path(temporary).resolve()
            plan, report, receipt = self.compound_receipt_fixture(root)
            path = root / "mechanism/selected-W4-scaled-callback/fixture.c"
            path.write_bytes(path.read_bytes().replace(b"rv_unused_shipping_main", b"rv_different_shipping_main", 1))
            report["mechanisms"][0]["fixture_source"] = CI.pin(path.read_bytes())
            receipt.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "diagnostic or alias-free startup bytes"):
                CI.check_stage(plan, plan.stages[1])

    def p28_receipt_fixture(self, root, family="A", selection="compound"):
        """Only inert bytes and pure rendering; no compiler or TT is executed."""
        plan = CI.pipeline_plan(family, root, profile="test-p28", spelling_variant=selection)
        name = CI.NEXT + "check_profile_p28.py"
        checker = CI.normalized(CI.ROOT / name)
        renderer = CI.load("ci_test_p28_renderer", CI.ROOT / name)
        c = renderer.CONTEXT[family]
        source = (f"#define {c['width']} 28\n#define {c['count']} ((size_t)1<<24)\n#define {c['unit']} 512\n".encode()
                  + renderer.init_marker(family) + b"/* inert selected body */}\n")
        resources = {"id": "test-p28", "workers": 28, "tt_cap_bytes": 512 << 20, "tt_bits": 24,
            "tt_entries": 1 << 24, "tt_bytes": 384 << 20, "tt_entry_bytes": 24, "tt_mask": (1 << 24) - 1}
        proof = {"resources": resources, "target_type_assertions": ["/* inert target type evidence */"]}
        build = {"family": family, "resources": resources, "compiler": ["cc", "-Os", "-x", "c", "-", "-o", "x"],
            "post_profile": {"path": CI.NEXT + ("profile_b.py" if family == "B" else "profile_phase.py"),
                             "variant": "tcec-final-lf" if family == "B" else "phase-init"},
            "post_spelling": CI.spelling_declaration(family, selection, profile="test-p28"),
            "source_dependencies": {"path": CI.NEXT + "profile_dependencies.py", "variant": "unused-includes"},
            "source_proofs": [proof], "source_closure": {"fixture": "controlled source authority"}, "expected_contract": {}}
        def write(name, data):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return {"path": str(path), **CI.pin(data)}
        actual = {}
        for role, relative, data in (("source", "main.c", source), ("native", "native/x", b"inert shipping native"),
                                     ("whole", "x", b"inert shipping whole")):
            write("artifact/" + relative, data)
            actual[role] = {"path": relative, **CI.pin(data)}
            build["expected_contract"].update({role + "_" + key: value for key, value in CI.pin(data).items()})
        build_pin = write("artifact/build.json", json.dumps(build).encode())
        proof_raw = json.dumps(build["source_proofs"]).encode()
        write("artifact/source-proof.json", proof_raw)
        write("inputs/" + name, checker)
        fixture, observation, trace, geometry = renderer.full_callback_fixture(source, family, proof)
        native = b"inert full callback native"
        output = (json.dumps(observation, separators=(",", ":")) + "\n").encode()
        for name2, data in (("fixture.c", fixture), ("x", native), ("trace-proof.json", json.dumps(trace).encode())):
            write("mechanism/selected-W28-full-callback/" + name2, data)
        output_pin = write("mechanism/tool-2-selected-W28-full-callback-execute.stdout", output)
        directory = root / "mechanism/selected-W28-last-initializer"
        startup = renderer.blocked_main(source, family, directory / "release", directory / "last-initializer-arrived")
        startup_native = b"inert startup image"
        stdout = b"uciok\nreadyok\nbestmove a2a3\nreadyok\nbestmove b2b3\nreadyok\nreadyok\n"
        for name2, data in (("fixture.c", startup), ("x", startup_native), ("runtime.stdout", stdout)):
            write("mechanism/selected-W28-last-initializer/" + name2, data)
        physical = {"returncode": 0, "readers_joined": True, "stdout_eof": True, "stderr_eof": True,
            "reaped": True, "original_identity_retained_until_other_members_absent": True,
            "forced_cleanup": False, "pre_reap_other_members": []}
        cleanup = {"forced_cleanup": False, "errors": [], "settled_before_cleanup": True,
                   "owned_group_absent": True, "readers_joined": True, "reaped": True, "pre_reap_other_members": []}
        commands = [command_row(kind) for kind in ("selected-W28-full-callback-compile",
                    "selected-W28-full-callback-execute", "selected-W28-last-initializer-compile")]
        for row, dirname in zip(commands, ("selected-W28-full-callback", "selected-W28-full-callback", "selected-W28-last-initializer")):
            row["cwd"] = str(root / "mechanism" / dirname)
            row["command"] = ([str(root / "mechanism" / dirname / "x")] if row["kind"].endswith("execute") else
                              [*build["compiler"], "-Wl,--wrap=pthread_create"])
        commands[1]["stdout"] = output_pin
        report = {**owner_report(commands), "class": "rove4k-bound-p28-mechanism-v1", "source_bound": True,
            "mode": "source-bound", "entry": family, "profile": "test-p28", "representation": "source-jit",
            "build": {**build_pin, "path": str(root / "artifact")}, "actual": actual, "resources": resources,
            "selected_post_spelling": build["post_spelling"], "selected_post_profile": build["post_profile"],
            "source_dependencies": build["source_dependencies"], "source_closure": build["source_closure"],
            "source_proofs": CI.pin(proof_raw), "support_inputs": {name: CI.pin(checker)},
            **dict.fromkeys(("production_adopted", "runtime_qualified", "placement_qualified", "timing_claimed",
                            "NUMA_qualified", "shipping_binary_executed", "W256_executed"), False),
            "mechanisms": [{"name": "full-W28-TT24-initialization", "profile": "test-p28", "shipping_source": CI.pin(source),
                "fixture_source": CI.pin(fixture), "native": CI.pin(native), "output": CI.pin(output), "observation": observation,
                "trace_proof": trace, "geometry": geometry,
                "diagnostic_preamble": {"text": renderer.DIAGNOSTIC_PREAMBLE.decode(), **CI.pin(renderer.DIAGNOSTIC_PREAMBLE)},
                "poisoning_changes_first_touch": True, **dict.fromkeys(("resource_constants_changed", "padding_checked",
                    "search_executed", "NUMA_claimed", "production_startup_timing_claimed"), False)}],
            "startup_barriers": [{"fixture_source": CI.pin(startup), "native": CI.pin(startup_native), "output": CI.pin(stdout),
                "shipping_source": CI.pin(source), "actual_resource_profile": "test-p28", "actual_workers": 28,
                "actual_tt_entries": 1 << 24, "actual_tt_bytes": 384 << 20, "tt_entry_bytes": 24,
                "startup_deadline_ms": 60000, "instrumented_native_startup_ms": 100, "legal_search_relaunches": 2,
                "physical": physical, "cleanup": cleanup, **dict.fromkeys(("last_initializer_delayed", "gate_arrival_observed",
                    "no_uci_before_release", "uci_ready_after_release", "startup_includes_intentional_hold",
                    "private_copy_removed", "post_GO2_join_observed"), True),
                **dict.fromkeys(("shipping_identity_claimed", "diagnostic_alias_applied", "resource_constants_changed",
                                "all_workers_positive_CPU_claimed"), False)}],
            "runtime_cleanup": {"remaining_owned": 0, "drained": [], "errors": []},
            "barrier_runtime_cleanup": [{"directory": str(root / "mechanism/selected-W28-last-initializer/runtime"),
                                          "pid": 1234, "cleanup": cleanup}]}
        path = root / "mechanism/results.json"
        path.write_text(json.dumps(report))
        return plan, report, path

    def test_p28_full_callback_and_actual_main_receipts_are_separate_from_p4(self):
        for family, selection in [(f, "compound") for f in "ABCEF"] + [("B", "best")]:
            with self.subTest(family=family, selection=selection), tempfile.TemporaryDirectory(prefix="rove-ci-p28-") as temporary:
                plan, report, path = self.p28_receipt_fixture(Path(temporary).resolve(), family, selection)
                accepted = CI.check_stage(plan, plan.stages[1])
                self.assertEqual(accepted["full_resource_mechanism"], {"actual_workers": 28, "actual_tt_bytes": 384 << 20,
                    "scaled_resources": False, "startup_deadline_ms": 60000})
                self.assertEqual(json.loads(path.read_bytes()), report)

    def test_p28_full_callback_rejects_scaled_rebound_and_unsettled_evidence(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-p28-reject-") as temporary:
            plan, good, path = self.p28_receipt_fixture(Path(temporary).resolve())
            for keys, value, error in [( ("class",), "rove4k-bound-compound-mechanism-v1", "selected source/build"),
                    (("build", "path"), str(plan.out), "selected source/build"),
                    (("commands", 1, "command"), ["/different/native"], "compile/execute argv"),
                    (("resources", "tt_bytes"), 96 << 20, "selected source/build|exact actual"),
                    (("mechanisms", 0, "observation", "actual_workers"), 4, "full-resource callback"),
                    (("mechanisms", 0, "observation", "actual_workers"), 28.0, "full-resource callback"),
                    (("mechanisms", 0, "observation", "all_callbacks_entered_once"), 1, "full-resource callback"),
                    (("mechanisms", 0, "geometry", "page_units"), 512, "full-resource callback"),
                    (("mechanisms", 0, "geometry", "workers"), 28.0, "full-resource callback"),
                    (("mechanisms", 0, "trace_proof", "full_inverse"), False, "full-resource callback"),
                    (("mechanisms", 0, "trace_proof", "bounds_and_stores_changed"), 0, "full-resource callback"),
                    (("mechanisms", 0, "fixture_source"), {}, "full-resource callback"),
                    (("startup_barriers", 0, "actual_workers"), 4, "startup source/resource"),
                    (("startup_barriers", 0, "actual_workers"), 28.0, "startup source/resource"),
                    (("startup_barriers", 0, "startup_deadline_ms"), 120000, "startup source/resource"),
                    (("startup_barriers", 0, "instrumented_native_startup_ms"), 60001, "single startup budget"),
                    (("startup_barriers", 0, "diagnostic_alias_applied"), True, "startup source/resource"),
                    (("startup_barriers", 0, "physical", "returncode"), False, "finish naturally"),
                    (("startup_barriers", 0, "native", "bytes"), float(good["startup_barriers"][0]["native"]["bytes"]), "startup source/resource"),
                    (("runtime_cleanup", "remaining_owned"), 1, "finish naturally"),
                    (("runtime_cleanup", "remaining_owned"), False, "finish naturally"),
                    (("barrier_runtime_cleanup",), [], "cleanup journal")]:
                changed = json.loads(json.dumps(good))
                target = changed
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                path.write_text(json.dumps(changed))
                with self.subTest(keys=keys), self.assertRaisesRegex(ValueError, error):
                    CI.check_stage(plan, plan.stages[1])
            changed = json.loads(json.dumps(good))
            changed["barrier_runtime_cleanup"][0]["cleanup"]["reaped"] = 1
            path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "cleanup journal"):
                CI.check_stage(plan, plan.stages[1])
            path.write_text(json.dumps(good))
            fixture = plan.out / "mechanism/selected-W28-full-callback/fixture.c"
            fixture.write_bytes(fixture.read_bytes().replace(b"1<<24", b"1<<18", 1))
            good["mechanisms"][0]["fixture_source"] = CI.pin(fixture.read_bytes())
            path.write_text(json.dumps(good))
            with self.assertRaisesRegex(ValueError, "full-resource callback"):
                CI.check_stage(plan, plan.stages[1])

    def test_p28_source_proof_raw_pin_does_not_replace_its_typed_manifest_join(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-p28-proof-types-") as temporary:
            plan, report, path = self.p28_receipt_fixture(Path(temporary).resolve())
            proof = plan.out / "artifact/source-proof.json"
            changed = json.loads(proof.read_bytes())
            changed[0]["resources"]["tt_bits"] = 24.0
            proof.write_text(json.dumps(changed))
            report["source_proofs"] = CI.pin(proof.read_bytes())
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "source proof differs"):
                CI.check_stage(plan, plan.stages[1])

    def test_p28_renderer_uses_captured_bytes_and_startup_forbids_later_aliases(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-p28-captured-") as temporary:
            plan, report, path = self.p28_receipt_fixture(Path(temporary).resolve())
            original = CI.evidence_bytes
            snapshot = plan.out / "inputs" / CI.NEXT / "check_profile_p28.py"
            def swap_after_capture(out, relative, **kw):
                data = original(out, relative, **kw)
                if relative == "inputs/" + CI.NEXT + "check_profile_p28.py":
                    snapshot.write_bytes(b"raise RuntimeError('reopened unpinned source')\n")
                return data
            with patch.object(CI, "evidence_bytes", side_effect=swap_after_capture):
                self.assertEqual(CI.check_stage(plan, plan.stages[1])["full_resource_mechanism"]["actual_workers"], 28)
            snapshot.write_bytes(CI.normalized(CI.ROOT / CI.NEXT / "check_profile_p28.py"))
            fixture = plan.out / "mechanism/selected-W28-last-initializer/fixture.c"
            fixture.write_bytes(fixture.read_bytes() + b"\n#define rv_spawn rv\n")
            report["startup_barriers"][0]["fixture_source"] = CI.pin(fixture.read_bytes())
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "alias-free renderer"):
                CI.check_stage(plan, plan.stages[1])

    def d_p28_receipt_fixture(self, root):
        """Produce only readable C/proof text and inert images for D's new schema."""
        plan = CI.pipeline_plan("D", root, profile="test-p28")
        modules = {key: CI.load("ci_D_p28_fixture_" + key, CI.ROOT / CI.D_ROOT / filename)
            for key, filename in (("source", "source.py"), ("startup", "test_startup.py"),
                ("storage", "storage.py"), ("checker", "check_profile_p28.py"), ("builder", "build.py"))}
        source, renderer = modules["source"], modules["checker"]
        profile = source.production().resource_profile("test-p28")
        files, proof = modules["startup"].prepared(source, profile, True, modules["storage"], "prefix")
        shipping = b"controlled D shipping C fixture"
        build = {**owner_report(), "format": "rove4k-D-general-source-v1", "family": "D", "storage": "prefix",
            "source_reduced": False, "equivalent_edits": True, "frozen_execution": True, "native_reproduced": True,
            "resource": profile.to_record(16), "proof": proof, "flags": modules["builder"].native_flags(profile),
            "shipping_inputs": {"main.c": CI.pin(shipping)}}
        def write(name, data):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return {"path": str(path), **CI.pin(data)}
        build_pin = write("artifact/build.json", json.dumps(build).encode())
        write("artifact/shipping-inputs/main.c", shipping)
        source_pins = {name: CI.pin(data) for name, data in sorted(files.items())}
        inputs = {"selection/build.json": {key: build_pin[key] for key in ("bytes", "sha256")}}
        for name in (CI.D_ROOT + "check_profile_p28.py", CI.D_ROOT + "source.py"):
            data = CI.normalized(CI.ROOT / name)
            write("inputs/" + name, data)
            inputs[name] = CI.pin(data)
        for name, data in files.items():
            write("artifact/generated-readable/" + name, data)
            inputs["selection/generated-readable/" + name] = CI.pin(data)
        commands, mechanisms = [], []
        for index, (case, code) in enumerate(renderer.CASES):
            negative = None if code == 0 else "omit-clear" if code == 7 else "omit-page-owner"
            fixture, trace = renderer.poison_fixture(files, source, negative=negative)
            directory = root / "mechanism" / case
            for name, data in fixture.items():
                write("mechanism/" + case + "/" + name, data)
            native = b"inert " + case.encode()
            write("mechanism/" + case + "/x", native)
            output = b"TEST_INITIALIZED\nuciok\nreadyok\n" if code == 0 else b"TEST_POISON_REMAINS\n" if code == 7 else b"TEST_OWNER_DIFFERS\n"
            stdout = write("mechanism/tool-" + str(2 * index + 2) + "-execute-" + case + ".stdout", output)
            command = ["cc", *build["flags"], *[str(directory / unit) for unit in source.UNITS],
                "-Wl,-T," + str(directory / "image.ld"), "-o", str(directory / "x")]
            commands.extend(({**command_row("compile-" + case), "command": command, "cwd": str(directory)},
                             {**command_row("execute-" + case, code), "stdout": stdout,
                              "command": [str(directory / "x")], "cwd": str(directory)}))
            mechanisms.append({"name": case, "expected_returncode": code, "output": CI.pin(output), "native": CI.pin(native),
                "instrumentation": trace, "complete_entry_fields_checked": code != 7, "complete_page_owners_checked": code == 0,
                "poisoning_changes_first_touch": True, "shipping_identity_claimed": False})
        directory = root / "mechanism/selected-W28-last-initializer"
        paths = {name: directory / name for name in ("arrived", "release", "joined", "exit_release")}
        extra = renderer.startup_wrapper(paths)
        write("mechanism/selected-W28-last-initializer/fixture.c", extra)
        native = b"inert D unpoisoned startup native"
        write("mechanism/selected-W28-last-initializer/x", native)
        for name, data in files.items():
            write("mechanism/selected-W28-last-initializer/" + name, data)
        command = ["cc", *build["flags"], *[str(directory / unit) for unit in source.UNITS], str(directory / "fixture.c"),
            "-Wl,--wrap=spawn,--wrap=main", "-Wl,-T," + str(directory / "image.ld"), "-o", str(directory / "x")]
        commands.append({**command_row("compile-unpoisoned-startup"), "command": command, "cwd": str(directory)})
        for row in commands:
            row["child_limits"] = {"AS": 2 << 30, "CPU": 60}
        markers = {name: write("mechanism/selected-W28-last-initializer/" + name, data) for name, data in
            (("arrived", b"ok\n"), ("release", b"release\n"), ("joined", b"ok\n"), ("exit_release", b"exit\n"))}
        output = b"uciok\nreadyok\nbestmove a2a3\nreadyok\nbestmove b2b3\nreadyok\nreadyok\n"
        for name, data in (("runtime.stdout", output), ("runtime/stdout.bin", output), ("runtime/stderr.bin", b"")):
            write("mechanism/selected-W28-last-initializer/" + name, data)
        cleanup = {"owned_group_absent": True, "readers_joined": True, "settled_before_cleanup": True,
            "reaped": True, "forced_cleanup": False, "errors": [], "pre_reap_other_members": []}
        physical = {"returncode": 0, "reaped": True, "readers_joined": True, "stdout_eof": True, "stderr_eof": True, "forced_cleanup": False,
            "pre_reap_other_members": [], "original_identity_retained_until_other_members_absent": True}
        tasks = {str(number): {"state": "S", "cpu_ticks": 0, "children": []} for number in range(1234, 1263)}
        barrier = {"extra_TU": CI.pin(extra), "fixture_source": CI.pin(extra), "native": CI.pin(native), "output": CI.pin(output),
            "shipping_source": CI.pin(shipping), "production_units": json.loads(json.dumps(source_pins)), "production_proof": proof,
            "production_units_changed": False, "linker_wrappers": ["spawn", "main"], "actual_resource_profile": "test-p28",
            "actual_workers": 28, "actual_tt_entries": 1 << 25, "actual_tt_bytes": 512 << 20, "entry_bytes": 16,
            "startup_deadline_ms": 60000, "legal_GO_cycles": 2, "spawn_calls_checked": 28, "callback_entries_checked": 28,
            "per_ID_callbacks_asserted": [{"worker": worker, "entries": 1, "returns": 1} for worker in range(28)],
            "callback_returns_checked": 28, "original_stdin_pipe": "pipe:[123456]", "original_stdin_preserved": True,
            "last_callback_delayed_before_work": True, "no_UCI_before_release": True, "final_position_acquire_fence": True,
            "shipping_identity_claimed": False, "all_workers_positive_CPU_claimed": False, "physical_placement_qualified": False,
            "NUMA_qualified": False, "ready_ms_including_intentional_hold": 100, "total_runtime_ms": 150,
            "physical": physical, "cleanup": cleanup, "markers": markers, "startup_tasks": tasks, "idle_tasks": tasks,
            "joined_tasks": {"1234": tasks["1234"]}, "startup_snapshot": {"tasks": tasks}, "resident": {"pid": 1234}}
        for observation in [*mechanisms, barrier]:
            observation["launch_headroom"] = {"minimum_bytes": 4 << 30, "effective_available_bytes": 8 << 30, "condition_met": True}
        applied = renderer.mechanism_limits((-1, -1))
        report = {**owner_report(commands), "class": "rove4k-D-bound-p28-mechanism-v1", "source_bound": True,
            "profile": "test-p28", "family": "D", "build": {**build_pin, "path": str(root / "artifact")},
            "inputs": inputs, "geometry": renderer.geometry(build["resource"]), "flags": build["flags"],
            "selected_source": source_pins, "production_proof": proof, "mechanisms": mechanisms, "startup_barriers": [barrier],
            "frozen_execution": True, "real_target_allocation": True, "actual_workers": 28, "actual_tt_bytes": 512 << 20,
            "inherited_CPU_limits": [-1, -1], "applied_Host_limits": applied, "minimum_launch_headroom_bytes": 4 << 30,
            "startup_inherits_parent_CPU_limits": [applied["parent_CPU"], applied["parent_CPU_hard"]],
            **dict.fromkeys(("shipping_binary_executed", "runtime_qualified", "rules_qualified", "physical_placement_qualified",
                "NUMA_qualified", "locality_proof", "production_startup_timing_claimed", "strength_claimed", "event_target_confirmed"), False),
            "runtime_cleanup": {"remaining_owned": 0, "drained": [], "errors": []},
            "barrier_runtime_cleanup": [{"directory": str(directory / "runtime"), "pid": 1234, "cleanup": cleanup}]}
        path = root / "mechanism/results.json"
        path.write_text(json.dumps(report))
        return plan, report, path

    def test_d_p28_full_field_negative_controls_and_multi_unit_startup_are_bound(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-D-p28-") as temporary:
            plan, report, path = self.d_p28_receipt_fixture(Path(temporary).resolve())
            accepted = CI.check_stage(plan, plan.stages[1])
            self.assertEqual(accepted["full_resource_mechanism"]["actual_tt_bytes"], 512 << 20)
            for keys, value, error in ((("commands", 3, "returncode"), 0, "nested command"),
                    (("commands", 5, "returncode"), 7, "nested command"),
                    (("commands", 1, "command"), ["/different/native"], "diagnostic proof"),
                    (("commands", 1, "command"), None, "diagnostic proof"),
                    (("commands", 0, "child_limits", "CPU"), 120, "applied CPU"),
                    (("applied_Host_limits", "child_CPU"), 120, "applied CPU"),
                    (("class",), "D-selected-source-poisoned-TT-startup-and-W256-GO-v3", "selected build/resource"),
                    (("mechanisms", 0, "instrumentation", "full_inverse"), 1, "diagnostic proof"),
                    (("mechanisms", 1, "expected_returncode"), 8, "diagnostic proof"),
                    (("startup_barriers", 0, "production_units_changed"), True, "multi-unit"),
                    (("startup_barriers", 0, "callback_returns_checked"), 27, "join counters"),
                    (("startup_barriers", 0, "per_ID_callbacks_asserted"), None, "join counters"),
                    (("startup_barriers", 0, "per_ID_callbacks_asserted", 1, "worker"), 0, "join counters"),
                    (("startup_barriers", 0, "per_ID_callbacks_asserted", 1, "entries"), True, "join counters"),
                    (("startup_barriers", 0, "per_ID_callbacks_asserted", 1, "returns"), 0, "join counters"),
                    (("startup_barriers", 0, "ready_ms_including_intentional_hold"), 60001, "deadline"),
                    (("startup_barriers", 0, "joined_tasks"), report["startup_barriers"][0]["startup_tasks"], "29-to1"),
                    (("startup_barriers", 0, "physical", "stdout_eof"), False, "finish naturally"),
                    (("mechanisms", 0, "launch_headroom", "effective_available_bytes"), 3 << 30, "headroom condition"),
                    (("barrier_runtime_cleanup", 0, "cleanup", "reaped"), 1, "finish naturally")):
                changed = json.loads(json.dumps(report))
                target = changed
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                path.write_text(json.dumps(changed))
                with self.subTest(keys=keys), self.assertRaisesRegex(ValueError, error):
                    CI.check_stage(plan, plan.stages[1])
            path.write_text(json.dumps(report))
            unit = plan.out / "mechanism/selected-W28-last-initializer/runtime.c"
            unit.write_bytes(unit.read_bytes() + b"/* changed production unit */\n")
            report["startup_barriers"][0]["production_units"]["runtime.c"] = CI.pin(unit.read_bytes())
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "changed a production unit"):
                CI.check_stage(plan, plan.stages[1])

    def test_output_is_a_new_nonlinked_runner_temp_child_outside_checkouts(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-path-") as directory:
            root = Path(directory)
            self.assertEqual(CI.admit_output(root / "run-A", root), root / "run-A")
            for out in (root, root.parent / "outside", root / "../traversal"):
                with self.assertRaises(ValueError):
                    CI.admit_output(out, root)
            (root / "exists").mkdir()
            with self.assertRaisesRegex(ValueError, "new child"):
                CI.admit_output(root / "exists", root)
            (root / ".git").mkdir()
            with self.assertRaisesRegex(ValueError, "Git checkout"):
                CI.admit_output(root / "run-B", root)

    def test_output_does_not_follow_a_runner_temp_symlink(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-links-") as directory:
            root = Path(directory)
            real, alias = root / "real", root / "alias"
            real.mkdir()
            try:
                alias.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlink unavailable")
            with self.assertRaisesRegex(ValueError, "filesystem links"):
                CI.admit_output(alias / "new", alias)

    def test_natural_ownership_and_cleanup_are_required(self):
        CI.owned_commands(owner_report())
        for key, bad in (("forced_cleanup", True), ("reaped", False), ("terminal", False),
                         ("owned_group_absent", False), ("original_identity_retained_until_other_members_absent", False),
                         ("other_group_members_before_reap", [{"pid": 1}]), ("returncode", False)):
            row = command_row()
            row[key] = bad
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "original ownership"):
                CI.owned_commands(owner_report([row]))
        for changed in ({"commands": []}, {"complete": False},
                        {"host_cleanup": {"unsettled_commands": 1, "errors": []}}):
            report = owner_report()
            report.update(changed)
            with self.assertRaises(ValueError):
                CI.owned_commands(report)

    def test_only_named_natural_negative_controls_are_permitted(self):
        codes = {"execute-w4-spawn-fail": 2, "execute-w4-omit-clear": 7}
        rows = [command_row("compile"), *(command_row(kind, code) for kind, code in codes.items())]
        CI.owned_commands(owner_report(rows), expected_codes=codes)
        with self.assertRaises(ValueError):
            CI.owned_commands(owner_report(rows))
        with self.assertRaisesRegex(ValueError, "missing or duplicated"):
            CI.owned_commands(owner_report(rows[:-1]), expected_codes=codes)
        rows[-1]["forced_cleanup"] = True
        with self.assertRaises(ValueError):
            CI.owned_commands(owner_report(rows), expected_codes=codes)

    def test_host_compiler_admission_does_not_upgrade_an_alternate_target(self):
        result = CI.compiler_record(b"cc (Ubuntu 13.3.0) 13.3.0\nCopyright\n", b"13.3.0\n")
        self.assertEqual(result["full_version"], "13.3.0")
        for banner, version in ((b"clang version 13.0.0\n", b"13.0.0"),
                                (b"cc (Ubuntu 14.2.0) 14.2.0\n", b"14.2.0"),
                                (b"cc (Ubuntu 11.4.0) 11.4.0\n", b"11.4.0")):
            with self.assertRaisesRegex(ValueError, "separate pipeline"):
                CI.compiler_record(banner, version)

    def test_consumers_run_only_after_their_actual_receipts_are_accepted(self):
        plan = CI.pipeline_plan("B", Path(tempfile.gettempdir()).resolve() / "ci-plan-test")
        events, report = [], {"stages": []}
        def run(command, *, cwd, kind):
            events.append(("run", kind))
        def inspect(plan, stage):
            events.append(("inspect", stage.name))
            return {"receipt": {"sha256": stage.name}}
        CI.execute_plan(plan, report, lambda: None, run, inspect_stage=inspect)
        self.assertEqual(events, [event for name in ("generation", "mechanism", "rules", "runtime")
                                 for event in (("run", "ci-" + name), ("inspect", name))])
        self.assertTrue(all(row["complete"] for row in report["stages"]))
        events.clear()
        def failed_inspect(plan, stage):
            events.append(("inspect", stage.name))
            if stage.name == "rules":
                raise ValueError("actual rules failed")
            return {}
        with self.assertRaisesRegex(ValueError, "actual rules failed"):
            CI.execute_plan(plan, {"stages": []}, lambda: None, run, inspect_stage=failed_inspect)
        self.assertNotIn(("run", "ci-runtime"), events)

    def test_failed_owned_command_is_not_retried_or_relabelled(self):
        plan = CI.pipeline_plan("D", Path(tempfile.gettempdir()).resolve() / "ci-failure-test")
        calls, report = [], {"stages": []}
        def run(command, **keywords):
            calls.append(keywords["kind"])
            raise TimeoutError("original child retained")
        with self.assertRaisesRegex(TimeoutError, "original child"):
            CI.execute_plan(plan, report, lambda: None, run, inspect_stage=lambda *a: self.fail("failed command inspected"))
        self.assertEqual(calls, ["ci-generation"])
        self.assertFalse(report["stages"][0]["complete"])

    def test_canonical_mechanism_cannot_claim_selected_source(self):
        with tempfile.TemporaryDirectory(prefix="rove-ci-control-") as directory:
            root = Path(directory)
            plan = CI.pipeline_plan("D", root)
            (root / "mechanism").mkdir()
            report = owner_report([command_row("execute-w4-spawn-fail", 2), command_row("execute-w4-omit-clear", 7)])
            report.update(kind="D-real-raw-clone-poisoned-TT-startup-and-W256-GO-v2", source_bound=False)
            (root / "mechanism/results.json").write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "canonical/control"):
                CI.check_stage(plan, plan.stages[1])

    def test_runtime_receipt_cannot_be_spliced_from_another_build_or_rules_run(self):
        for profile in ("test-p4", "test-p28"):
            with tempfile.TemporaryDirectory(prefix="rove-ci-runtime-binding-") as directory:
                root = Path(directory)
                workers = 28 if profile == "test-p28" else 4
                plan = CI.pipeline_plan("A", root, profile=profile,
                    spelling_variant="compound" if profile == "test-p28" else "control")
                for path in (root / "artifact", root / "runtime", root / "rules/probe"):
                    path.mkdir(parents=True, exist_ok=True)
                whole = b"owned test artifact"
                (root / "artifact/x").write_bytes(whole)
                resources = {"id": profile, "workers": workers, "tt_bytes": (384 if workers == 28 else 96) << 20, "tt_entry_bytes": 24}
                native = {"native_bytes": 32, "native_sha256": "a" * 64}
                generation = {"resources": resources, "expected_contract": native}
                def write(relative, value):
                    path = root / relative
                    path.write_text(json.dumps(value))
                    return {"path": str(path), **CI.pin(path.read_bytes())}
                generation_pin = write("artifact/build.json", generation)
                rules_pin = write("rules/probe/rules.json", {"unit_fixture": "controlled fake runner"})
                runtime = {"format": "rove4k-profile-runtime-v1", "complete": True, "family": "A", "profile": profile,
                    "owned_remaining": 0, "final_owned_cleanup": [], "build_sha256": generation_pin["sha256"],
                    "resources": resources, "expected_contract": native, "counts": {"GO": 24, "legal_bestmoves": 22},
                    "sessions": [{"termination": label, "complete": True,
                        "settled": {"returncode": 0, "forced_cleanup": False, "readers_joined": True},
                        "cleanup": {"owned_group_absent": True}}
                        for label in ("idle-quit", "idle-EOF", "active-quit", "active-EOF")]}
                runtime_pin = write("runtime/runtime.json", runtime)
                checks = dict.fromkeys(("reproduction", "startup", "dependencies", "cleanup", "protocol", "legal_moves", "resources", "lifecycle", "size"), True)
                checks["placement"] = False
                qualified = {"format": "rove4k-qualification-v1", "functional_runtime_complete": True,
                    "complete": False, "failures": ["placement"], "checks": checks,
                    "artifact": {"family": "A", "profile": profile, "full": True, "workers": workers,
                        "representation": "source-jit", "native_sha256": native["native_sha256"],
                        "tt_bytes": resources["tt_bytes"], "entry_bytes": 24,
                        "whole_bytes": len(whole), "sha256": CI.pin(whole)["sha256"]},
                    "evidence": {"runtime": runtime_pin, "rules": {"evidence": {"rules_report": rules_pin}}},
                    "observations": {"startup_ms": 100, "workers": workers, "positive_cpu_workers": workers,
                        "tt_bytes": resources["tt_bytes"], "runtime_native_sha256": native["native_sha256"],
                        "temporary_cleanup_while_live": True, "nbrq_replay": True, "nbrq_generation": True}}
                write("runtime/qualification.json", qualified)
                result = CI.check_stage(plan, plan.stages[-1])
                self.assertTrue(result["size_eligible"])
                self.assertFalse(result["qualification_complete"])
                for field in ("artifact", "runtime", "rules", "status", "observations", "zero-GO", "missing-placement", "non-bool", "artifact-workers", "runtime-profile", "artifact-profile"):
                    bad = json.loads(json.dumps(qualified))
                    current = json.loads(json.dumps(runtime))
                    if field == "artifact":
                        bad["artifact"]["sha256"] = "b" * 64
                    elif field == "runtime":
                        bad["evidence"]["runtime"]["sha256"] = "b" * 64
                    elif field == "rules":
                        bad["evidence"]["rules"]["evidence"]["rules_report"]["sha256"] = "b" * 64
                    elif field == "status":
                        bad["complete"] = True
                    elif field == "observations":
                        bad["observations"]["positive_cpu_workers"] = 4 if workers == 28 else 3
                    elif field == "artifact-workers":
                        bad["artifact"]["workers"] = 4 if workers == 28 else 28
                    elif field == "runtime-profile":
                        current["profile"] = "test-p4" if profile == "test-p28" else "test-p28"
                        bad["evidence"]["runtime"] = write("runtime/runtime.json", current)
                    elif field == "artifact-profile":
                        bad["artifact"]["profile"] = "test-p4" if profile == "test-p28" else "test-p28"
                    elif field == "missing-placement":
                        del bad["checks"]["placement"]
                        bad.update(failures=[], complete=True)
                    elif field == "non-bool":
                        bad["checks"]["size"] = 1
                    else:
                        current["counts"]["GO"] = 0
                        bad["evidence"]["runtime"] = write("runtime/runtime.json", current)
                    if field not in ("zero-GO", "runtime-profile"):
                        write("runtime/runtime.json", runtime)
                    write("runtime/qualification.json", bad)
                    with self.subTest(field=field), self.assertRaises(ValueError):
                        CI.check_stage(plan, plan.stages[-1])

class SquareScanPlans(unittest.TestCase):
    def test_explicit_AC_scan_routes_both_profiles_and_preserves_old_defaults(self):
        root=Path("/scan-plan").resolve()
        for family in "AC":
            for profile in ("test-p4","test-p28"):
                old=CI.pipeline_plan(family,root,spelling_variant="compound",profile=profile)
                selected=CI.pipeline_plan(family,root,spelling_variant="compound",scan_variant="square-successor",profile=profile)
                self.assertEqual(old.scan_variant,"control")
                self.assertNotIn("--scan-variant",old.stages[0].command)
                self.assertEqual(selected.scan_variant,"square-successor")
                self.assertIn("--scan-variant",selected.stages[0].command)
                self.assertEqual(Path(selected.stages[1].command[3]).name,"check_profile_scan.py")
        for family,spelling,selection in (("B","best","square-successor"),("E","compound","square-successor"),
            ("A","best","square-successor"),("C","compound",True),("D","control","square-successor")):
            with self.assertRaises(ValueError):
                CI.pipeline_plan(family,root,spelling_variant=spelling,scan_variant=selection)

    def test_scan_guard_binds_current_checker_raw_proof_and_exact_resource_stages(self):
        for profile,bits,workers in (("test-p4",22,4),("test-p28",24,28)):
            with tempfile.TemporaryDirectory(prefix="rove-ci-scan-policy-") as temporary:
                root=Path(temporary).resolve()
                plan=CI.pipeline_plan("A",root,spelling_variant="compound",scan_variant="square-successor",profile=profile)
                scanner=CI.NEXT+"profile_scan.py"
                stages=[{"schema":"rove4k.c-resource-projection.v1","family":"A"},
                    {"schema":"rove4k.portable-phase-source.v1","family":"A","profile_id":profile,"variant":"phase-init"},
                    {"schema":"rove4k.selected-spelling-compound.v1","family":"A","profile_id":profile,"variant":"clock-atomic-launcher"},
                    {"schema":"rove4k.selected-square-scan.v1","family":"A","profile_id":profile,"variant":"square-successor"},
                    {"schema":"rove4k.profile-dependencies.v1"}]
                build={"class":"rove4k-production-profile-v1","family":"A","entry":"A",
                    "resources":{"id":profile,"workers":workers,"tt_bits":bits,"tt_entries":1<<bits,
                        "tt_bytes":24*(1<<bits),"tt_entry_bytes":24,"tt_mask":(1<<bits)-1},
                    "post_profile":{"path":CI.NEXT+"profile_phase.py","variant":"phase-init"},
                    "post_spelling":CI.COMPOUND_SPELLING,"post_scan":CI.SCAN_DECLARATION,
                    "source_dependencies":{"path":CI.NEXT+"profile_dependencies.py","variant":"unused-includes"},
                    "plan":{"representation":"source-jit","entry_cleanup":"private-path"},"source_proofs":stages,
                    "inputs":{scanner:{"bytes":10623,"sha256":"98eb3139bcbd745f08fbab2d8a738b428d4e668de2604ac3fc715de8c58b879f"}}}
                raw=json.dumps(stages).encode();path=root/"artifact/source-proof.json";path.parent.mkdir();path.write_bytes(raw)
                name=CI.NEXT+"check_profile_scan.py"
                data=CI.normalized(CI.ROOT/name);path=root/"inputs"/name;path.parent.mkdir(parents=True);path.write_bytes(data)
                report={"class":"rove4k-bound-scan-mechanism-v1","selected_post_scan":CI.SCAN_DECLARATION,
                    "source_proofs":CI.pin(raw),"support_inputs":{name:CI.pin(data)}}
                CI.scan_mechanism_policy(plan,report,build)
                for bad in ({**report,"selected_post_scan":None},{**report,"source_proofs":{}},
                            {**report,"class":"rove4k-bound-compound-mechanism-v1"}):
                    with self.assertRaises(ValueError):CI.scan_mechanism_policy(plan,bad,build)
                build["resources"]["workers"]=4 if workers==28 else 28
                with self.assertRaises(ValueError):CI.scan_mechanism_policy(plan,report,build)


if __name__ == "__main__":
    unittest.main()
