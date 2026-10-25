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
            with self.subTest(family=family):
                plan = CI.pipeline_plan(family, Path(tempfile.gettempdir()).resolve() / ("ci-inputs-" + family))
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

    def test_bundle_and_target_input_gates_keep_the_executing_reader_boundary(self):
        own = CI.normalized(CI.ROOT / CI.SELF)
        verify = CI.load("production_ci_test_bundle_verify", CI.ROOT / CI.NEXT / "profile_verify.py")
        reader = verify.input_reader()
        root = Path(tempfile.gettempdir()).resolve()
        for family in "ABCDEF":
            plans = (CI.pipeline_plan(family, root / ("ci-export-" + family)),
                     CI.target_plan(family, root / ("ci-target-" + family), root / "sealed/artifact",
                                    root / "source-bundle.zip", root / "source-seal.json"))
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
            compiler, _, runtime = [stage.command for stage in plan.stages]
            self.assertIn("--ubuntu22-system", compiler)
            self.assertEqual(compiler[compiler.index("--compiler") + 1], "/usr/bin/cc")
            self.assertFalse(any("profile_build.py" in part or "test_startup.py" in part for stage in plan.stages for part in stage.command))
            self.assertIn("--target-compiler-receipt", runtime)
            self.assertIn("--source-bundle", runtime)
            self.assertIn("--source-seal", runtime)
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
        with tempfile.TemporaryDirectory(prefix="rove-ci-target-reference-") as directory:
            root = Path(directory)
            plan = CI.target_plan("A", root, root / "original/artifact",
                                  root / "source-bundle.zip", root / "source-seal.json")
            for child in (root / "compiler", root / "runtime"):
                child.mkdir()
            old = {"native_bytes": 32, "native_sha256": "a" * 64}
            target_pin = {"bytes": 40, "sha256": "b" * 64}
            record = {"family": "A", "profile": "test-p4", "factory_replayed_on_target": False,
                      "target_native": target_pin}
            calls = []
            class Reference:
                native_pin = target_pin
                def to_record(self):
                    return record
                def revalidate(self, **keywords):
                    calls.append("revalidate")
            def validate(*arguments, **keywords):
                calls.append("validated-object")
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
            inspect = CI.target_inspector(plan, verify, SimpleNamespace(expected=old), target, object())
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
                self.assertEqual([stage.name for stage in plan.stages], ["generation", "mechanism", "rules", "runtime"])
                self.assertTrue(all(stage.command[1:3] == ("-I", "-B") for stage in plan.stages))
                generation, mechanism, rules, runtime = [stage.command for stage in plan.stages]
                self.assertEqual(generation[generation.index("--profile") + 1], "test-p4")
                self.assertNotIn("tcec-provisional", generation)
                if family == "D":
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
                self.assertEqual(runtime[runtime.index("--rules") + 1], str(plan.out / "rules/probe/rules.json"))
        for retired in ("F8", "Rust", "a", "", "../A"):
            with self.assertRaisesRegex(ValueError, "active C family"):
                CI.pipeline_plan(retired, root / "no-read")

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
        with tempfile.TemporaryDirectory(prefix="rove-ci-runtime-binding-") as directory:
            root = Path(directory)
            plan = CI.pipeline_plan("A", root)
            for path in (root / "artifact", root / "runtime", root / "rules/probe"):
                path.mkdir(parents=True, exist_ok=True)
            whole = b"owned test artifact"
            (root / "artifact/x").write_bytes(whole)
            resources = {"id": "test-p4", "workers": 4, "tt_bytes": 96 << 20, "tt_entry_bytes": 24}
            native = {"native_bytes": 32, "native_sha256": "a" * 64}
            generation = {"resources": resources, "expected_contract": native}
            def write(relative, value):
                path = root / relative
                path.write_text(json.dumps(value))
                return {"path": str(path), **CI.pin(path.read_bytes())}
            generation_pin = write("artifact/build.json", generation)
            rules_pin = write("rules/probe/rules.json", {"unit_fixture": "controlled fake runner"})
            runtime = {"format": "rove4k-profile-runtime-v1", "complete": True, "family": "A", "profile": "test-p4",
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
                "artifact": {"family": "A", "profile": "test-p4", "full": True, "workers": 4,
                    "representation": "source-jit", "native_sha256": native["native_sha256"],
                    "tt_bytes": resources["tt_bytes"], "entry_bytes": 24,
                    "whole_bytes": len(whole), "sha256": CI.pin(whole)["sha256"]},
                "evidence": {"runtime": runtime_pin, "rules": {"evidence": {"rules_report": rules_pin}}},
                "observations": {"startup_ms": 100, "workers": 4, "positive_cpu_workers": 4,
                    "tt_bytes": resources["tt_bytes"], "runtime_native_sha256": native["native_sha256"],
                    "temporary_cleanup_while_live": True, "nbrq_replay": True, "nbrq_generation": True}}
            write("runtime/qualification.json", qualified)
            result = CI.check_stage(plan, plan.stages[-1])
            self.assertTrue(result["size_eligible"])
            self.assertFalse(result["qualification_complete"])
            for field in ("artifact", "runtime", "rules", "status", "observations", "zero-GO", "missing-placement", "non-bool"):
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
                    bad["observations"]["positive_cpu_workers"] = 3
                elif field == "missing-placement":
                    del bad["checks"]["placement"]
                    bad.update(failures=[], complete=True)
                elif field == "non-bool":
                    bad["checks"]["size"] = 1
                else:
                    current["counts"]["GO"] = 0
                    bad["evidence"]["runtime"] = write("runtime/runtime.json", current)
                if field != "zero-GO":
                    write("runtime/runtime.json", runtime)
                write("runtime/qualification.json", bad)
                with self.subTest(field=field), self.assertRaises(ValueError):
                    CI.check_stage(plan, plan.stages[-1])


if __name__ == "__main__":
    unittest.main()
