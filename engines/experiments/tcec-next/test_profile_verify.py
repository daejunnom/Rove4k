"""Profile qualifier admission and host-budget boundaries; no engine required."""
from __future__ import annotations

import importlib.util
import json
import lzma
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
PATH = Path(__file__).with_name("profile_verify.py")
SPEC = importlib.util.spec_from_file_location("profile_verify_tests_target", PATH)
VERIFY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VERIFY
SPEC.loader.exec_module(VERIFY)


def admitted(profile_id="test-p4", family="A"):
    api = VERIFY.contracts()
    profile, engine = api.resource_profile(profile_id), api.engine_spec(family)
    return VERIFY.AdmittedBuild(family, profile_id, "source-jit", "x", "main.c", "native/x", {},
                                profile.to_record(engine.entry_bytes), {}, {}, {}, {})


def resident_row(resident, approximate, pid=77):
    raw = b"0000-ffff ---p 00000000 00:00 0 [rollup]\nRss: " + str(resident // 1024).encode() + b" kB\n"
    account = {"source": "smaps_rollup", "before": {"pid": pid, "start_ticks": 123, "state": "S"},
               "after": {"pid": pid, "start_ticks": 123, "state": "R"}, "Rss_bytes": resident,
               "raw": raw.decode(), "raw_pin": VERIFY.pin(raw)}
    return ({"pid": pid, "startup_RSS_source": "smaps_rollup", "startup_resident_accounting": account,
             "startup_RSS_bytes_not_peak": resident, "startup_VmRSS_bytes_not_peak": approximate},
            {"memory_snapshot_not_peak": {"VmRSS": str(approximate // 1024) + " kB"}})


class ProfileRuntimeAdmission(unittest.TestCase):
    def setUp(self):
        if os.name != "posix":
            # These are pure Windows admission fixtures, not a claim that the
            # production POSIX no-follow transport runs on Windows.
            def local_read(path, *, limit, allow_hardlinks=False):
                data = Path(path).read_bytes()
                VERIFY.require(len(data) <= limit, "fixture extent exceeds bound")
                return data
            fixture = patch.object(VERIFY, "input_reader", return_value=types.SimpleNamespace(
                read_regular=local_read))
            fixture.start()
            self.addCleanup(fixture.stop)

    def test_artifact_reader_receives_the_exact_admitted_extent(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-input-bound-") as temporary:
            root = Path(temporary)
            (root / "candidate").write_bytes(b"actual")
            calls = []
            def read(path, *, limit):
                calls.append((path, limit))
                return b"actual"
            with patch.object(VERIFY, "input_reader", return_value=types.SimpleNamespace(read_regular=read)):
                self.assertEqual(VERIFY.checked_artifact(root, "candidate", VERIFY.pin(b"actual")), b"actual")
                self.assertEqual(calls, [(root / "candidate", 6)])
                with self.assertRaisesRegex(ValueError, "artifact identity differs"):
                    VERIFY.checked_artifact(root, "candidate", VERIFY.pin(b"fake!!"))

    def test_reader_dependency_is_derived_from_the_frozen_qualifier(self):
        self.assertFalse(VERIFY.runtime_reader_required(b'CLASS = "legacy"\n'))
        self.assertTrue(VERIFY.runtime_reader_required(PATH.read_bytes()))
        for source in (b'INPUT_READER = "different.py"\n', b'INPUT_READER = get_reader()\n',
                       b'INPUT_READER = "engines/scripts/production_input.py"\nINPUT_READER = "again"\n'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                VERIFY.runtime_reader_required(source)

    def test_cloud_image_uses_exact_types_and_revalidates_without_ci_environment(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory(prefix="rove4k-cloud-image-") as temporary:
            root = Path(temporary)
            (root / "native").mkdir()
            (root / "native/x").write_bytes(b"producer13")
            (root / "target").mkdir()
            target = root / "target/x"
            target.write_bytes(b"actual11")
            (root / "build.json").write_bytes(b"{}")
            original = {"native_" + key: value for key, value in VERIFY.pin(b"producer13").items()}
            selected = replace(admitted(), expected=dict(original))
            checks = []
            class Source:
                def assert_admission(self, value, build):
                    checks.append(("source", value, build))
                    VERIFY.require(value.program == "x", "source admission changed")
                def to_record(self):
                    return {"binding": {"source_profile": "exact source evidence"}}
            source = Source()
            class Reference:
                family, profile, native_path = "A", "test-p4", target
                native_pin, source_evidence = VERIFY.pin(b"actual11"), source
                def assert_admission(self, value, build):
                    checks.append(("reference", value, build))
                def revalidate(self, *, verify):
                    checks.append(("revalidate", verify))
                def to_record(self):
                    return {"runtime_eligible": True, "factory_replayed_on_target": False,
                            "original_build_expected_contract": dict(original),
                            "source_binding": source.to_record(),
                            "source_build": {"path": str(root), **VERIFY.pin(b"{}")}}
            class CIReference:
                pass
            class CI:
                @staticmethod
                def from_environment():
                    raise AssertionError("cloud reference must not borrow GitHub environment")
            helper = types.SimpleNamespace(TargetRuntimeReference=CIReference,
                ValidatedSourceEvidence=Source, CIContext=CI)
            provider = types.SimpleNamespace(CloudRuntimeReference=Reference)
            with patch.object(VERIFY, "target_module", return_value=helper), \
                    patch.object(VERIFY, "cloud_provider", return_value=provider), \
                    patch.object(VERIFY, "_CLOUD_PROVIDER", provider):
                self.assertEqual(VERIFY.runtime_image(selected, root, Reference()),
                                 (VERIFY.pin(b"actual11"), b"actual11"))
                VERIFY.revalidate_target(Reference())
                self.assertTrue(any(row[0] == "source" for row in checks))
                self.assertIn(("revalidate", VERIFY), checks)
                with self.assertRaisesRegex(ValueError, "source admission changed"):
                    VERIFY.runtime_image(replace(selected, program="different"), root, Reference())
                with patch.object(VERIFY, "_CLOUD_PROVIDER", None), self.assertRaisesRegex(ValueError, "validated TargetRuntimeReference"):
                    VERIFY.runtime_image(selected, root, Reference())
            self.assertEqual(selected.expected, original)

    def test_cloud_support_uses_the_typed_nested_source_record(self):
        tools = {"engines/experiments/tcec-next/target_runtime.py": VERIFY.pin(b"validator"),
                 VERIFY.INPUT_READER: VERIFY.pin(b"reader")}
        class Source:
            source_provenance_tools = tools
            def to_record(self):
                return {"format": "rove4k.source-evidence.v1", "binding": {"source_provenance_tools": tools}}
        source = Source()
        class Reference:
            source_evidence = source
            def __init__(self, changed=False):
                self.changed = changed
            def to_record(self):
                return {"source_binding": {} if self.changed else source.to_record(),
                        "compiler_evidence": {"compiler_tools": {
                            "engines/experiments/tcec-next/profile_compiler.py": VERIFY.pin(b"compiler")},
                            "reference_validator": {"path": "engines/experiments/tcec-next/target_runtime.py",
                                                    **VERIFY.pin(b"validator")}}}
        provider = types.SimpleNamespace(CloudRuntimeReference=Reference, HOST_SOURCE_FILES=())
        helper = types.SimpleNamespace(TargetRuntimeReference=type("CIReference", (), {}), ValidatedSourceEvidence=Source)
        with patch.object(VERIFY, "target_module", return_value=helper), \
                patch.object(VERIFY, "cloud_provider", return_value=provider), \
                patch.object(VERIFY, "_CLOUD_PROVIDER", provider):
            expected = {name: value["sha256"] for name, value in tools.items()}
            expected["engines/experiments/tcec-next/profile_compiler.py"] = VERIFY.pin(b"compiler")["sha256"]
            self.assertEqual(VERIFY.reference_support_pins(Reference()), expected)
            with self.assertRaisesRegex(ValueError, "exact typed source evidence"):
                VERIFY.reference_support_pins(Reference(True))

    def test_cloud_source_requires_the_canonical_layout_token(self):
        calls = []
        class Layout:
            def revalidate(self):
                calls.append("layout checked")
            def to_record(self):
                return {"roots": []}
        provider = types.SimpleNamespace(OriginalLayout=Layout)
        sentinel = object()
        def bind(*args, **kwargs):
            calls.append(kwargs)
            return sentinel
        helper = types.SimpleNamespace(sealed_source_binding=bind)
        arguments = dict(source_bundle=Path("bundle"), source_seal=Path("seal"), source_origin={},
                         seed_root=Path("seed"), member_map={})
        with patch.object(VERIFY, "cloud_provider", return_value=provider), \
                patch.object(VERIFY, "target_module", return_value=helper):
            with self.assertRaisesRegex(ValueError, "canonical OriginalLayout"):
                VERIFY.cloud_source_binding(admitted(), Path("build"), **arguments, restored_layout={"roots": []})
            self.assertIs(VERIFY.cloud_source_binding(admitted(), Path("build"), **arguments,
                restored_layout=Layout()), sentinel)
        self.assertEqual(calls[0], "layout checked")
        self.assertEqual(calls[1]["restored_layout"], {"roots": []})
        self.assertNotIn("expected_ci", calls[1])

    def test_cloud_compiler_and_rules_reject_untyped_source_maps(self):
        class Source:
            pass
        helper = types.SimpleNamespace(ValidatedSourceEvidence=Source)
        with patch.object(VERIFY, "target_module", return_value=helper):
            with self.assertRaisesRegex(ValueError, "validated source evidence"):
                VERIFY.cloud_compiler_binding(admitted(), Path("build"), Path("compiler.json"), source_binding={})
            with self.assertRaisesRegex(ValueError, "validated source evidence"):
                VERIFY.cloud_rules_receipt(admitted(), Path("build"), Path("rules.json"), source_binding={})
        self.assertFalse(VERIFY.cloud_runtime_supported({"native_pin": VERIFY.pin(b"untrusted")}))
        self.assertFalse(VERIFY.cloud_runtime_supported(types.ModuleType("another_provider")))

    def test_cloud_launch_support_requires_the_actual_validator_and_program_apis(self):
        class Evidence:
            pass
        compiler = types.SimpleNamespace(SCHEMA="rove4k.profile-compiler.v1",
            program_provenance_enabled=lambda explicit, source_port, *, system: explicit or source_port)
        helper = types.SimpleNamespace(ValidatedSourceEvidence=Evidence, ValidatedCompilerEvidence=Evidence,
            sealed_source_binding=lambda *args, **kwargs: None,
            compiler_receipt_binding=lambda *args, **kwargs: None,
            _compiler_module=lambda: compiler)
        with patch.object(VERIFY, "target_module", return_value=helper):
            self.assertTrue(VERIFY.cloud_bridge_available())
            saved = helper.compiler_receipt_binding
            del helper.compiler_receipt_binding
            self.assertFalse(VERIFY.cloud_bridge_available())
            helper.compiler_receipt_binding = saved
            del compiler.program_provenance_enabled
            self.assertFalse(VERIFY.cloud_bridge_available())
            compiler.program_provenance_enabled = lambda *args, **kwargs: True
            self.assertFalse(VERIFY.cloud_bridge_available())
            compiler.program_provenance_enabled = lambda explicit, source_port, *, system: explicit or source_port
            compiler.SCHEMA = "unimplemented"
            self.assertFalse(VERIFY.cloud_bridge_available())

    def test_exact_startup_residency_preserves_approximate_status_undercount(self):
        tt = 128 << 20
        row, snapshot = resident_row(tt + 128 * 1024, tt - 128 * 1024)
        self.assertEqual(VERIFY.startup_residency(row, snapshot, tt, exact_required=True), tt + 128 * 1024)
        self.assertEqual(row["startup_VmRSS_bytes_not_peak"], tt - 128 * 1024)
        self.assertTrue(VERIFY.runtime_feature_required(PATH.read_bytes(), "RSS_ACCOUNTING", "smaps_rollup"))
        self.assertFalse(VERIFY.runtime_feature_required(b'CLASS="old"\n', "RSS_ACCOUNTING", "smaps_rollup"))

    def test_true_under_touch_is_rejected_even_when_status_counter_is_high(self):
        tt = 128 << 20
        row, snapshot = resident_row(tt - 3 * 4096, tt + (1 << 20))
        with self.assertRaisesRegex(ValueError, "TT writes"):
            VERIFY.startup_residency(row, snapshot, tt, exact_required=True)
        # The existing 8 KiB allowance is retained exactly.
        row, snapshot = resident_row(tt - 8192, tt + (1 << 20))
        self.assertEqual(VERIFY.startup_residency(row, snapshot, tt, exact_required=True), tt - 8192)

    def test_missing_exact_accounting_never_falls_back_to_high_status(self):
        tt = 128 << 20
        row, snapshot = resident_row(tt, tt + (1 << 20))
        del row["startup_resident_accounting"]
        with self.assertRaisesRegex(ValueError, "unavailable"):
            VERIFY.startup_residency(row, snapshot, tt, exact_required=True)
        with patch.object(VERIFY, "_proc_bytes", side_effect=FileNotFoundError("smaps unavailable")):
            with self.assertRaises(FileNotFoundError):
                VERIFY.resident_accounting(77)

    def test_exact_resident_raw_bytes_and_start_tick_identity_are_bound(self):
        tt = 128 << 20
        for change in ("identity", "pid", "raw", "value"):
            row, snapshot = resident_row(tt, tt)
            account = row["startup_resident_accounting"]
            if change == "identity":
                account["after"]["start_ticks"] += 1
            elif change == "pid":
                account["after"]["pid"] += 1
            elif change == "raw":
                account["raw"] += "Rss: 999999 kB\n"
            else:
                account["Rss_bytes"] += 4096
            with self.subTest(change=change), self.assertRaises(ValueError):
                VERIFY.startup_residency(row, snapshot, tt, exact_required=True)
        for raw in (b"", b"Rss: -1 kB\n", b"Rss: 123 bytes\n", b"Rss: 1 kB\nRss: 2 kB\n"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                VERIFY.rollup_rss_bytes(raw)

    @unittest.skipUnless(os.name == "posix", "real bounded proc observation requires Linux")
    def test_actual_untouched_mapping_cannot_pass_residency_on_a_high_status_fixture(self):
        import select
        tt = 128 << 20
        code = "import mmap,sys; m=mmap.mmap(-1,134217728); m[0]=1; print('ready',flush=True); sys.stdin.buffer.read(1)"
        child = subprocess.Popen([sys.executable, "-I", "-B", "-c", code], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            self.assertTrue(select.select([child.stdout], [], [], 5)[0], "fixture did not become ready")
            self.assertEqual(os.read(child.stdout.fileno(), 64), b"ready\n")
            account = VERIFY.resident_accounting(child.pid)
            self.assertLess(account["Rss_bytes"], tt - 8192)
            row, snapshot = resident_row(account["Rss_bytes"], tt + (1 << 20), child.pid)
            row["startup_resident_accounting"] = account
            with self.assertRaisesRegex(ValueError, "TT writes"):
                VERIFY.startup_residency(row, snapshot, tt, exact_required=True)
            stdout, stderr = child.communicate(b"x", timeout=5)
            self.assertEqual((child.returncode, stdout, stderr), (0, b"", b""))
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=5)

    def test_cloud_rules_keep_the_original_sealed_bytes_before_and_after_replay(self):
        calls = []
        class Source:
            def __init__(self, changing=False):
                self.changing, self.reads = changing, 0
            def assert_admission(self, value, build):
                calls.append("admission")
            def revalidate(self, *, verify):
                calls.append("revalidate")
            def member_bytes(self, path):
                self.reads += 1
                return b"changed" if self.changing and self.reads > 1 else b"sealed"
        helper = types.SimpleNamespace(ValidatedSourceEvidence=Source)
        with patch.object(VERIFY, "target_module", return_value=helper), \
                patch.object(VERIFY, "rules_receipt", return_value={"nbrq_generation": True}) as replay:
            path = Path("rules.json")
            self.assertEqual(VERIFY.cloud_rules_receipt(admitted(), Path("build"), path,
                             source_binding=Source()), path)
            self.assertEqual(calls, ["admission", "revalidate", "revalidate"])
            replay.assert_called_once()
            with self.assertRaisesRegex(ValueError, "changed during"):
                VERIFY.cloud_rules_receipt(admitted(), Path("build"), path, source_binding=Source(True))

    def test_target_image_is_separate_from_the_original_producer_expectation(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory(prefix="rove4k-target-image-") as temporary:
            root = Path(temporary)
            (root / "native").mkdir()
            (root / "native/x").write_bytes(b"original compiler image")
            (root / "target").mkdir()
            target = root / "target/x"
            target.write_bytes(b"independent target image")
            (root / "build.json").write_bytes(b"{}")
            old = {"native_" + k: v for k, v in VERIFY.pin((root / "native/x").read_bytes()).items()}
            accepted = replace(admitted(), expected=dict(old))
            expected_target = VERIFY.pin(target.read_bytes())
            class Reference:
                family, profile, native_path = "A", "test-p4", target
                native_pin = expected_target
                def assert_admission(self, value, build):
                    VERIFY.require(value.program == "x", "reference execution object differs")
                def to_record(self):
                    return {"runtime_eligible": True, "factory_replayed_on_target": False,
                            "original_build_expected_contract": dict(old),
                            "source_build": {"path": str(root), **VERIFY.pin(b"{}")}}
            self.assertEqual(VERIFY.runtime_image(accepted, root),
                             (VERIFY.pin((root / "native/x").read_bytes()), b"original compiler image"))
            with patch.object(VERIFY, "target_module", return_value=types.SimpleNamespace(TargetRuntimeReference=Reference)):
                self.assertEqual(VERIFY.runtime_image(accepted, root, Reference()),
                                 (expected_target, b"independent target image"))
                with self.assertRaisesRegex(ValueError, "validated TargetRuntimeReference"):
                    VERIFY.runtime_image(accepted, root, {"native_pin": expected_target})
                with self.assertRaisesRegex(ValueError, "execution object differs"):
                    VERIFY.runtime_image(replace(accepted, program="unadmitted-program"), root, Reference())
            self.assertEqual(accepted.expected, old)

    def test_reference_for_another_profile_cannot_choose_a_runtime_image(self):
        from dataclasses import replace
        class Reference:
            family, profile = "A", "test-p28"
            def to_record(self):
                return {"runtime_eligible": True, "factory_replayed_on_target": False}
        with patch.object(VERIFY, "target_module", return_value=types.SimpleNamespace(TargetRuntimeReference=Reference)):
            with self.assertRaisesRegex(ValueError, "another source build/profile"):
                VERIFY.runtime_image(replace(admitted(), expected={}), Path("not-read"), Reference())

    def test_phase_and_model_proofs_have_exact_order_and_named_helper(self):
        resource = {"schema": "rove4k.c-resource-projection.v1"}
        phase = {"schema": "rove4k.portable-phase-source.v1"}
        model = {"stage": "canonical-e19-physical-binding"}
        post = {"path": "engines/experiments/tcec-next/profile_phase.py", "variant": "phase-init"}
        self.assertEqual(VERIFY.source_stages("E", post, [resource, phase, model]), "phase")
        self.assertEqual(VERIFY.source_stages("A", post, [resource, phase]), "phase")
        self.assertIsNone(VERIFY.source_stages("E", None, [resource, model]))
        for family, declaration, proofs in (
            ("E", post, [resource, model, phase]), ("E", post, [resource, phase]),
            ("A", None, [resource, phase]), ("B", post, [resource, phase]),
            ("A", {**post, "path": "engines/other.py"}, [resource, phase]),
            ("A", {**post, "variant": "phase"}, [resource, phase]),
            ("", None, [resource]), ("AC", None, [resource]),
        ):
            with self.subTest(family=family, post=declaration, proofs=proofs), self.assertRaises(ValueError):
                VERIFY.source_stages(family, declaration, proofs)

    def test_spelling_is_an_explicit_selected_last_stage_after_E19(self):
        resource = {"schema": "rove4k.c-resource-projection.v1"}
        phase = {"schema": "rove4k.portable-phase-source.v1"}
        model = {"stage": "canonical-e19-physical-binding"}
        spelling = {"schema": VERIFY.SPELLING_SCHEMA}
        post = {"path": "engines/experiments/tcec-next/profile_phase.py", "variant": "phase-init"}
        selected = {"path": VERIFY.SPELLING, "selection": "best", "variant": "clock-type"}
        options = {"representation": "source-jit", "entry_cleanup": "private-path"}
        self.assertEqual(VERIFY.source_stages("E", post, [resource, phase, model, spelling], selected, **options), "phase")
        b = {"path": "engines/experiments/tcec-next/profile_b.py", "variant": "tcec-final-lf"}
        self.assertEqual(VERIFY.source_stages("B", b,
            [resource, {"schema": "rove4k.profile-b-source.v1"}, spelling],
            {**selected, "variant": "atomic-assignment"}, **options), "B")
        cases = [
            (post, [resource, phase, spelling, model], selected, options),
            (post, [resource, phase, model, spelling, spelling], selected, options),
            (post, [resource, phase, model], selected, options),
            (post, [resource, phase, model, spelling], None, options),
            (None, [resource, model, spelling], selected, options),
            (post, [resource, phase, model, spelling], {**selected, "variant": "atomic-assignment"}, options),
            (post, [resource, phase, model, spelling], {**selected, "selection": "other"}, options),
            (post, [resource, phase, model, spelling], {**selected, "path": "engines/unknown.py"}, options),
            (post, [resource, phase, model, spelling], selected, {**options, "representation": "packed-native"}),
            (post, [resource, phase, model, spelling], selected, {**options, "entry_cleanup": "none"}),
        ]
        for declaration, proofs, final, parameters in cases:
            with self.subTest(declaration=declaration, proofs=proofs, final=final, parameters=parameters), self.assertRaises(ValueError):
                VERIFY.source_stages("E", declaration, proofs, final, **parameters)

    def test_final_spelling_is_undone_before_model_offsets_and_prior_stages(self):
        calls = []
        def restore(data, proof):
            calls.append(proof["name"])
            VERIFY.require(data.startswith(proof["prefix"]), "inverse prefix differs")
            return data[len(proof["prefix"]):]
        module = types.SimpleNamespace(restore_source=restore)
        base, resource, phase, model, shipping = (b"table=1;", b"Rtable=1;", b"PRtable=1;",
                                                  b"PRtable=222;", b"SPRtable=222;")
        stages = [(module, {"name": "resource", "prefix": b"R"}, base),
                  (module, {"name": "phase", "prefix": b"P"}, resource),
                  (None, {"table_value_offset": 8, "before": "1", "after": "222"}, phase),
                  (module, {"name": "spelling", "prefix": b"S"}, model)]
        self.assertEqual(VERIFY.inverse_source_stages(shipping, stages), base)
        self.assertEqual(calls, ["spelling", "phase", "resource"])
        with self.assertRaisesRegex(ValueError, "E19 inverse span"):
            VERIFY.inverse_source_stages(shipping, [*stages[:2], stages[3], stages[2]])

    def test_spelling_helper_requires_exact_frozen_current_pin_and_tool_role(self):
        from copy import deepcopy
        row = {"path": VERIFY.SPELLING, "role": "tool", **VERIFY.SPELLING_PIN}
        manifest = {"inputs": {VERIFY.SPELLING: dict(VERIFY.SPELLING_PIN)}, "source_closure": {"inputs": [row]}}
        with tempfile.TemporaryDirectory(prefix="rove4k-spelling-helper-") as temporary:
            build = Path(temporary)
            frozen = build / "inputs" / VERIFY.SPELLING
            frozen.parent.mkdir(parents=True)
            source = (VERIFY.ROOT / VERIFY.SPELLING).read_bytes().replace(b"\r\n", b"\n")
            frozen.write_bytes(source)
            self.assertEqual(VERIFY.spelling_module(manifest, build, {VERIFY.SPELLING}).SCHEMA, VERIFY.SPELLING_SCHEMA)
            for kind in ("role", "pin", "input", "duplicate", "missing"):
                altered = deepcopy(manifest)
                if kind == "role":
                    altered["source_closure"]["inputs"][0]["role"] = "engine"
                elif kind == "pin":
                    altered["source_closure"]["inputs"][0]["sha256"] = "0" * 64
                elif kind == "input":
                    altered["inputs"][VERIFY.SPELLING]["bytes"] += 1
                elif kind == "duplicate":
                    altered["source_closure"]["inputs"].append(dict(row))
                else:
                    altered["source_closure"]["inputs"] = []
                with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "helper production role"):
                    VERIFY.spelling_module(altered, build, {VERIFY.SPELLING})
            frozen.write_bytes(source + b"\n")
            with self.assertRaises(ValueError):
                VERIFY.spelling_module(manifest, build, {VERIFY.SPELLING})

    def test_runtime_snapshot_matches_the_code_that_this_process_actually_compiled(self):
        source = PATH.read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(VERIFY.executing_source(source), source)
        altered = source.replace(b'CLASS = "rove4k-production-profile-v1"',
                                 b'CLASS = "different-program"', 1)
        self.assertNotEqual(altered, source)
        with self.assertRaisesRegex(ValueError, "compiled its executing module"):
            VERIFY.executing_source(altered)

    def test_large_submission_is_rejected_by_real_headroom_before_execution(self):
        record = admitted("tcec-provisional")
        with self.assertRaisesRegex(ValueError, "insufficient effective headroom before allocation"):
            VERIFY.execution_limits(record, 16 << 30)
        # A successful arithmetic admission is not execution or qualification.
        limits = VERIFY.execution_limits(record, 512 << 30)
        self.assertEqual(limits["admission"]["tt_bytes"], 192 << 30)
        self.assertGreater(limits["address_space_bytes"], 192 << 30)
        self.assertNotIn("qualified", limits)

    def test_generic_tt_or_mislabeled_workers_do_not_match_production(self):
        api = VERIFY.contracts()
        record = api.resource_profile("test-p4").to_record(16)
        with self.assertRaisesRegex(ValueError, "selected immutable profile"):
            VERIFY._resource_record(record, "A")
        record = api.resource_profile("test-p4").to_record(24)
        record["workers"] = 2
        with self.assertRaisesRegex(ValueError, "selected immutable profile"):
            VERIFY._resource_record(record, "A")

    def test_small_test_budget_is_finite_and_does_not_use_large_submission_limit(self):
        limits = VERIFY.execution_limits(admitted(), 4 << 30, wall_seconds=300)
        self.assertEqual(limits["address_space_bytes"], 2 << 30)
        self.assertEqual(limits["wall_seconds"], 300)
        self.assertEqual(limits["output_bytes_per_pipe"], 1 << 20)
        self.assertEqual(limits["startup_seconds"], 60)
        with self.assertRaisesRegex(ValueError, "finite runtime wall bound"):
            VERIFY.execution_limits(admitted(), 4 << 30, wall_seconds=0)

    def test_payload_must_have_exact_bounded_single_stream(self):
        source = b"int main(void){return 0;}\n"
        encoded = lzma.compress(source, format=lzma.FORMAT_ALONE)
        self.assertEqual(VERIFY.restore_payload(encoded, len(source)), source)
        for corrupt in (encoded + b"unused", encoded[:-1]):
            with self.subTest(case=corrupt[-8:]), self.assertRaisesRegex(ValueError, "one bounded"):
                VERIFY.restore_payload(corrupt, len(source))
        with self.assertRaisesRegex(ValueError, "one bounded"):
            VERIFY.restore_payload(encoded, len(source) - 1)

    def test_legacy_or_incomplete_build_cannot_enter_new_profile_runtime(self):
        with self.assertRaisesRegex(ValueError, "explicit new C production-profile"):
            VERIFY.admit_c_build({"format": 1, "class": "tcec-full-C-v1"}, Path("not-read"))
        with self.assertRaisesRegex(ValueError, "generation/reproduction is incomplete"):
            VERIFY.admit_c_build({"format": 1, "class": VERIFY.CLASS,
                                  "complete": True, "reproducible": False}, Path("not-read"))

    def test_build_complete_flag_is_not_an_owned_runtime_receipt(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-profile-receipt-") as temporary:
            root = Path(temporary)
            receipt = root / "runtime.json"
            receipt.write_text('{"format": "rove4k-production-profile-v1", "complete": true}')
            with self.assertRaisesRegex(ValueError, "owned runtime has not completed cleanly"):
                VERIFY.qualification_record(admitted(), root, receipt)

    def test_completed_runtime_cannot_be_rebound_to_another_artifact(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-profile-binding-") as temporary:
            root = Path(temporary)
            receipt = root / "runtime.json"
            (root / "build.json").write_bytes(b"{}")
            record = {"format": "rove4k-profile-runtime-v1", "complete": True,
                      "owned_remaining": 0, "final_owned_cleanup": [], "family": "B",
                      "profile": "test-p4", "representation": "source-jit"}
            receipt.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "runtime artifact class differs"):
                VERIFY.qualification_record(admitted(), root, receipt)
            record.update(family="A", build_sha256="0" * 64)
            receipt.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "whole/native/source/resource identity"):
                VERIFY.qualification_record(admitted(), root, receipt)

    def test_effective_headroom_includes_each_cgroup_v2_ancestor(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-profile-budget-") as temporary:
            root = Path(temporary)
            proc, cgroups = root / "proc", root / "cgroups"
            (proc / "self").mkdir(parents=True)
            (proc / "meminfo").write_text("MemAvailable: 16777216 kB\n")
            (proc / "self/cgroup").write_text("0::/slice/job\n")
            (cgroups / "slice/job").mkdir(parents=True)
            (cgroups / "memory.max").write_text("max\n")
            (cgroups / "memory.current").write_text("0\n")
            (cgroups / "slice/memory.max").write_text(str(1 << 30))
            (cgroups / "slice/memory.current").write_text(str(256 << 20))
            (cgroups / "slice/job/memory.max").write_text(str(512 << 20))
            (cgroups / "slice/job/memory.current").write_text(str(64 << 20))
            self.assertEqual(VERIFY.effective_available_bytes(proc, cgroups), 448 << 20)
            (cgroups / "slice/job/memory.current").write_text(str(1 << 30))
            self.assertEqual(VERIFY.effective_available_bytes(proc, cgroups), 0)

    def test_effective_headroom_includes_cgroup_v1_memory_controller(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-profile-budget-v1-") as temporary:
            root = Path(temporary)
            proc, cgroups = root / "proc", root / "cgroups"
            (proc / "self").mkdir(parents=True)
            (proc / "meminfo").write_text("MemAvailable: 16777216 kB\n")
            (proc / "self/cgroup").write_text("7:cpu,cpuacct:/job\n8:memory:/job\n")
            memory = cgroups / "memory"
            (memory / "job").mkdir(parents=True)
            (memory / "memory.limit_in_bytes").write_text(str(2 << 30))
            (memory / "memory.usage_in_bytes").write_text(str(256 << 20))
            (memory / "job/memory.limit_in_bytes").write_text(str(1 << 30))
            (memory / "job/memory.usage_in_bytes").write_text(str(512 << 20))
            self.assertEqual(VERIFY.effective_available_bytes(proc, cgroups), 512 << 20)

    def test_cpu_budget_covers_all_observed_workers_without_unbounded_wall(self):
        with patch.object(VERIFY.os, "sched_getaffinity", return_value=set(range(256)), create=True):
            large = VERIFY.execution_limits(admitted("tcec-provisional"), 512 << 30)
            small = VERIFY.execution_limits(admitted(), 4 << 30)
        self.assertEqual(large["CPU_budget_effective_cpus"], 256)
        self.assertGreater(large["CPU_seconds"][0], 256 * 60)
        self.assertEqual(small["CPU_budget_effective_cpus"], 5)
        self.assertEqual(large["wall_seconds"], small["wall_seconds"])
        self.assertGreater(large["CPU_seconds"][1], large["CPU_seconds"][0])

    def test_native_dependency_gate_checks_executable_entry_and_stack(self):
        def native(load_flags=5, stack_flags=6, entry=0x4000C8):
            identity = b"\x7fELF\x02\x01\x01" + b"\0" * 9
            header = struct.pack("<16sHHIQQQIHHHHHH", identity, 2, 62, 1, entry,
                                 64, 0, 0, 64, 56, 2, 0, 0, 0)
            load = struct.pack("<IIQQQQQQ", 1, load_flags, 0, 0x400000, 0,
                               201, 201, 4096)
            stack = struct.pack("<IIQQQQQQ", 0x6474E551, stack_flags, 0, 0, 0,
                                0, 0, 16)
            return (header + load + stack).ljust(200, b"\0") + b"\xc3"
        record = VERIFY.native_dependencies(native())
        self.assertEqual(record["DT_NEEDED"], [])
        self.assertIsNone(record["interpreter"])
        self.assertFalse(record["executable_stack"])
        for image in (native(load_flags=7), native(stack_flags=7),
                      native(entry=0x500000), native()[:64]):
            with self.subTest(image=image[-8:]), self.assertRaises(ValueError):
                VERIFY.native_dependencies(image)

    def test_artifact_path_cannot_escape_build_or_follow_symlink(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-profile-files-") as temporary:
            root = Path(temporary)
            build = root / "build"
            build.mkdir()
            inside, outside = build / "x", root / "other-source.txt"
            inside.write_bytes(b"own")
            outside.write_bytes(b"outside")
            self.assertEqual(VERIFY.checked_artifact(build, "x", VERIFY.pin(b"own")), b"own")
            with self.assertRaisesRegex(ValueError, "escaped its build"):
                VERIFY.artifact_file(build, outside)
            link = build / "linked"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                return
            with self.assertRaisesRegex(ValueError, "cannot follow a symlink"):
                VERIFY.artifact_file(build, link)


if __name__ == "__main__":
    unittest.main()
