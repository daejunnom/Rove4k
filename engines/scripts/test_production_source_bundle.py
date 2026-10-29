"""Small-file transport fixtures; no real CI, compiler, engine or TT execution."""
from __future__ import annotations

import ast
from contextlib import ExitStack
from dataclasses import replace
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import warnings
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TRANSPORT = load("source_transport_test_subject", Path(__file__).with_name("production_source_bundle.py"))
TARGET = load("source_transport_test_authority", ROOT / "engines/experiments/tcec-next/target_runtime.py")
VERIFY = load("source_transport_fixture_file_checks", ROOT / "engines/experiments/tcec-next/profile_verify.py")
CI = load("source_transport_pipeline_contract", Path(__file__).with_name("production_ci.py"))


class Fixture:
    """Dummy factory admission; archive, seal and layout validators stay real."""
    def __init__(self, root, family="A", profile="test-p4"):
        self.family = family
        self.profile = profile
        self.runner = root / "runner"
        self.out = self.runner / ("source-" + family)
        self.build = self.out / "artifact"
        self.build.mkdir(parents=True)
        self.reserved = self.runner / ("target-" + family)
        self.context = TARGET.CIContext("fixture/Rove4k", "a" * 40, "17", "1")
        self.compiler = TARGET._compiler_module()
        self.main = b"/* dummy factory input; never executed */\nint main(void){return 0;}\n"
        program = b"fixture-header\nfixture-payload"
        self.program = "D-source-jit" if family == "D" else "x"
        (self.build / self.program).write_bytes(program)
        (self.build / self.program).chmod(0o700)
        (self.build / "native").mkdir()
        (self.build / "native/x").write_bytes(b"original-13-native-fixture")
        self.expected = {**{"whole_" + key: value for key, value in TARGET.pin(program).items()},
            **{"source_" + key: value for key, value in TARGET.pin(self.main).items()},
            **{"native_" + key: value for key, value in TARGET.pin(b"original-13-native-fixture").items()},
            "header_bytes": len(b"fixture-header\n")}
        api = VERIFY.contracts()
        resource = api.resource_profile(profile).to_record(16 if family == "D" else 24)
        self.admitted = VERIFY.AdmittedBuild(family, profile, "source-jit", self.program,
            None if family == "D" else "main.c", "native/x", self.expected, resource,
            {"kind": "dummy-factory"}, {"kind": "dummy-wrapper"}, {}, {"fixture_only": True}, full=True)
        self.record = {"family": family, "fixture_only": True, "expected_contract": self.expected,
                       "source_proofs": [{"target_type_assertions": []}]}
        if family == "D":
            builder = load("source_transport_fixture_D_flags", ROOT / "engines/experiments/tiny-d-submission/build.py")
            self.record.update(flags=builder.native_flags(api.resource_profile(profile)), units=["main.c", "start.S"])
            source = self.build / "shipping-inputs"
            source.mkdir()
            files = {"main.c": self.main, "start.S": b"/* fixture only */\n", "image.ld": b"/* fixture only */\n"}
            self.record["shipping_inputs"] = {name: TARGET.pin(data) for name, data in files.items()}
            for name, data in files.items():
                (source / name).write_bytes(data)
            self.record["fixture_absolute_candidate"] = str(self.build / self.program)
            self.record["fixture_absolute_native"] = str(self.build / "native/x")
        else:
            (self.build / "main.c").write_bytes(self.main)
            self.record["compiler"] = list(self.compiler.C_FLAGS[family])
        self.manifest = (json.dumps(self.record, indent=2) + "\n").encode()
        (self.build / "build.json").write_bytes(self.manifest)
        def admit(record, build, candidate=None):
            if family == "D":
                if candidate != "D-source-jit":
                    raise ValueError("fixture requires explicit source-JIT selection")
            return self.admitted
        self.verify = SimpleNamespace(admit_c_build=admit, admit_d_build=admit,
            checked_artifact=VERIFY.checked_artifact, artifact_file=VERIFY.artifact_file, contracts=VERIFY.contracts)
        rows = []
        paths = ("artifact/build.json", "mechanism/result.json" if family == "B" and profile == "test-p4" else "mechanism/results.json",
                 "rules/commands.json", "runtime/runtime.json")
        for name, relative in zip(("generation", "mechanism", "rules", "runtime"), paths):
            path = self.out / relative
            if name != "generation":
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps({"dummy_owned_stage": name}))
            rows.append({"name": name, "complete": True, "receipt": {"path": str(path), **TARGET.pin(path.read_bytes())}})
        self.pipeline = {"format": "rove4k-production-ci-functional-v1", "family": family, "profile": profile,
            "backend": "ubuntu-24.04-gcc13-host-cc", "source_context": self.context.to_record(),
            "complete": True, "functional_complete": True, "host_cleanup": {"unsettled_commands": 0, "errors": []},
            "commands": [{"started": True, "terminal": True, "reaped": True, "owned_group_absent": True,
                "original_identity_retained_until_other_members_absent": True, "forced_cleanup": False,
                "other_group_members_before_reap": [], "returncode": 0}], "stages": rows}
        self.pipeline_path = self.out / "pipeline-functional.json"
        self.save_pipeline()

    def save_pipeline(self):
        self.pipeline_path.write_text(json.dumps(self.pipeline, indent=2) + "\n")

    def context_patches(self):
        stack = ExitStack()
        stack.enter_context(patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": self.context.repository,
            "GITHUB_SHA": self.context.head_sha, "GITHUB_RUN_ID": self.context.run_id,
            "GITHUB_RUN_ATTEMPT": self.context.run_attempt, "RUNNER_TEMP": str(self.runner)}))
        stack.enter_context(patch.object(TARGET, "_checkout_head", return_value=self.context.head_sha))
        stack.enter_context(patch.object(TARGET, "_source_host", return_value={"ID": "ubuntu", "VERSION_ID": "24.04"}))
        return stack

    def export(self, **overrides):
        keywords = dict(family=self.family, runner_temp=self.runner,
            verify=self.verify, target=TARGET, ci_context=self.context, pipeline_receipt=self.pipeline_path)
        if self.profile != "test-p4":
            keywords["profile"] = self.profile
        keywords.update(overrides)
        return TRANSPORT.export_bundle(self.out, self.build, **keywords)

    def hold_original(self):
        held = self.runner / "original-held"
        self.out.rename(held)
        self.bundle, self.seal = held / "source-bundle.zip", held / "source-seal.json"
        return held

    def restore(self, **overrides):
        keywords = dict(family=self.family, runner_temp=self.runner, verify=self.verify,
            target=TARGET, ci_context=self.context, reserved_out=self.reserved)
        if self.profile != "test-p4":
            keywords["profile"] = self.profile
        keywords.update(overrides)
        return TRANSPORT.restore_bundle(self.bundle, self.seal, **keywords)

    def write_archive(self, entries):
        stream = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(stream, "w") as archive:
                for name, data, mode in entries:
                    info = zipfile.ZipInfo(name)
                    info.create_system = 3
                    info.external_attr = mode << 16
                    archive.writestr(info, data)
        raw = stream.getvalue()
        self.bundle.write_bytes(raw)
        seal = json.loads(self.seal.read_bytes())
        seal["bundle"] = TARGET.pin(raw)
        seal["members"] = {name: TARGET.pin(data) for name, data, mode in entries}
        self.seal.write_text(json.dumps(seal))


class PipelineReceiptContracts(unittest.TestCase):
    def test_fixture_stage_receipts_match_real_pipeline_plans_for_both_profiles(self):
        # Cross the transport fixture against the real producer plan; no CI
        # environment or stage execution is needed to observe its contract.
        for profile in ("test-p4", "test-p28"):
            for family in "ABCDEF":
                with self.subTest(profile=profile, family=family), \
                        tempfile.TemporaryDirectory(prefix="rove-source-stage-contract-") as directory:
                    fixture = Fixture(Path(directory), family=family, profile=profile)
                    selectors = (("control",) if family == "D" else ("control", "best", "compound"))
                    if profile == "test-p28":
                        selectors = (("control",) if family == "D" else
                                     ("best", "compound") if family == "B" else ("compound",))
                    actual = [(row["name"], Path(row["receipt"]["path"]).relative_to(fixture.out).as_posix())
                              for row in fixture.pipeline["stages"]]
                    for selector in selectors:
                        with self.subTest(selector=selector):
                            plan = CI.pipeline_plan(family, fixture.out, profile=profile, spelling_variant=selector)
                            self.assertEqual(actual, [(stage.name, stage.receipt) for stage in plan.stages])
                            for row, stage in zip(fixture.pipeline["stages"], plan.stages):
                                receipt = fixture.out / stage.receipt
                                self.assertEqual(row["receipt"], {"path": str(receipt), **TARGET.pin(receipt.read_bytes())})


@unittest.skipUnless(os.name == "posix", "real extraction requires POSIX no-follow directory handles")
class SourceBundleTransport(unittest.TestCase):
    def test_reads_and_scans_share_the_canonical_production_reader(self):
        reader = TARGET.input_reader()
        self.assertIs(reader, VERIFY.input_reader())
        with tempfile.TemporaryDirectory(prefix="rove-source-shared-reader-") as directory:
            fixture = Fixture(Path(directory))
            with patch.object(reader, "read_regular", wraps=reader.read_regular) as ordinary, \
                    patch.object(reader, "read_regular_at", wraps=reader.read_regular_at) as anchored:
                self.assertEqual(TRANSPORT._read(fixture.build / "main.c", TARGET), fixture.main)
                TRANSPORT._snapshot(fixture.build, TARGET)
                ordinary.assert_called_once_with(fixture.build / "main.c", limit=TARGET.MAX_MEMBER)
                self.assertGreaterEqual(anchored.call_count, 5)
            self.assertEqual(TRANSPORT._sources(TARGET)[2], reader.source_identity())

    def test_roundtrip_keeps_raw_source_native_metadata_and_executable_mode(self):
        with tempfile.TemporaryDirectory(prefix="rove-source-transport-") as directory:
            fixture = Fixture(Path(directory))
            with fixture.context_patches():
                exported = fixture.export()
                before = TRANSPORT._snapshot(fixture.build, TARGET)[0]
                fixture.hold_original()
                restored = fixture.restore()
                self.assertEqual(TRANSPORT._snapshot(fixture.build, TARGET)[0], before)
                self.assertEqual(restored["build_root"], str(fixture.build))
                self.assertFalse(restored["factory_replayed_on_target"])
                self.assertTrue(restored["exact_original_paths"])
                self.assertEqual(stat.S_IMODE((fixture.build / "x").stat().st_mode), 0o700)
                self.assertEqual(restored["source_bundle"]["sha256"], exported["source_bundle"]["sha256"])

    def test_both_named_profiles_roundtrip_every_family_without_relabeling(self):
        for profile in ("test-p4", "test-p28"):
            for family in "ABCDEF":
                with self.subTest(profile=profile, family=family), \
                        tempfile.TemporaryDirectory(prefix="rove-source-profile-") as directory:
                    fixture = Fixture(Path(directory), family, profile)
                    with fixture.context_patches():
                        exported = fixture.export()
                        before = TRANSPORT._snapshot(fixture.build, TARGET)[0]
                        fixture.hold_original()
                        sealed = json.loads(fixture.seal.read_bytes())
                        selected = sealed["profiles"][0]
                        self.assertEqual(selected["profile"], profile)
                        self.assertEqual(sealed["ci_context"], fixture.context.to_record())
                        self.assertEqual(set(sealed["ci_context"]),
                                         {"repository", "head_sha", "run_id", "run_attempt"})
                        restored = fixture.restore()
                    self.assertEqual(TRANSPORT._snapshot(fixture.build, TARGET)[0], before)
                    for record in (exported, restored):
                        self.assertEqual(record["profile"], profile)
                        self.assertEqual(record["source_context"], fixture.context.to_record())
                    self.assertEqual(restored["build_root"], str(fixture.build))
                    self.assertFalse(restored["factory_replayed_on_target"])
                    self.assertFalse(exported["engine_executed_by_export"])
                    resource = fixture.admitted.resources
                    self.assertEqual(resource["workers"], 4 if profile == "test-p4" else 28)
                    if profile == "test-p28":
                        self.assertEqual(resource["tt_bytes"], (512 if family == "D" else 384) << 20)
                    if family == "D":
                        self.assertEqual((fixture.build / "build.json").read_bytes(), fixture.manifest)
                        self.assertIn(str(fixture.build / "D-source-jit"), fixture.manifest.decode())
                        self.assertIn(str(fixture.build / "native/x"), fixture.manifest.decode())

    def test_mixed_profile_pipeline_or_admission_is_rejected_before_export(self):
        for profile, other in (("test-p4", "test-p28"), ("test-p28", "test-p4")):
            for role in ("pipeline", "admission"):
                with self.subTest(profile=profile, role=role), \
                        tempfile.TemporaryDirectory(prefix="rove-source-mixed-export-") as directory:
                    fixture = Fixture(Path(directory), profile=profile)
                    if role == "pipeline":
                        fixture.pipeline["profile"] = other
                        fixture.save_pipeline()
                    else:
                        fixture.admitted = replace(fixture.admitted, profile_id=other)
                    with fixture.context_patches(), patch.object(TRANSPORT, "_snapshot") as snapshot:
                        with self.assertRaises(ValueError):
                            fixture.export()
                        snapshot.assert_not_called()
                    self.assertFalse((fixture.out / "source-bundle.zip").exists())
                    self.assertFalse((fixture.out / "source-seal.json").exists())

    def test_B_P28_rejects_the_legacy_singular_receipt_before_export(self):
        with tempfile.TemporaryDirectory(prefix="rove-source-B-P28-receipt-") as directory:
            fixture = Fixture(Path(directory), family="B", profile="test-p28")
            mechanism = next(stage for stage in fixture.pipeline["stages"] if stage["name"] == "mechanism")
            plural = fixture.out / "mechanism/results.json"
            singular = fixture.out / "mechanism/result.json"
            self.assertTrue(plural.is_file())
            self.assertFalse(singular.exists())
            singular.write_bytes(plural.read_bytes())
            mechanism["receipt"] = {"path": str(singular), **TARGET.pin(singular.read_bytes())}
            fixture.save_pipeline()
            with fixture.context_patches(), patch.object(TRANSPORT, "_snapshot") as snapshot:
                with self.assertRaisesRegex(ValueError, "actual owned receipt"):
                    fixture.export()
                snapshot.assert_not_called()
            self.assertFalse((fixture.out / "source-bundle.zip").exists())
            self.assertFalse((fixture.out / "source-seal.json").exists())

    def test_requested_profile_must_match_the_seal_before_restoration(self):
        for profile, other in (("test-p4", "test-p28"), ("test-p28", "test-p4")):
            with self.subTest(profile=profile), \
                    tempfile.TemporaryDirectory(prefix="rove-source-mixed-restore-") as directory:
                fixture = Fixture(Path(directory), profile=profile)
                with fixture.context_patches():
                    fixture.export()
                    fixture.hold_original()
                    with patch.object(TRANSPORT, "_create_root") as create:
                        with self.assertRaisesRegex(ValueError, "one sealed full selected"):
                            fixture.restore(profile=other)
                        create.assert_not_called()
                self.assertFalse(fixture.out.exists())
                self.assertFalse(fixture.reserved.exists())

    def test_invalid_profile_values_fail_before_any_transport_input_or_output(self):
        for profile in (None, True, 4, 28.0, [], {}, b"test-p28", "TEST-P28", "tcec-provisional", ""):
            with self.subTest(profile=profile), \
                    tempfile.TemporaryDirectory(prefix="rove-source-invalid-profile-") as directory:
                fixture = Fixture(Path(directory))
                with patch.object(TRANSPORT, "_sources") as sources:
                    with self.assertRaisesRegex(ValueError, "explicit TEST-P4 or TEST-P28"):
                        fixture.export(profile=profile)
                    with self.assertRaisesRegex(ValueError, "explicit TEST-P4 or TEST-P28"):
                        TRANSPORT.restore_bundle(fixture.out / "missing.zip", fixture.out / "missing.json",
                            family=fixture.family, runner_temp=fixture.runner, verify=fixture.verify, target=TARGET,
                            ci_context=fixture.context, reserved_out=fixture.reserved, profile=profile)
                    sources.assert_not_called()
                self.assertFalse((fixture.out / "source-bundle.zip").exists())
                self.assertFalse((fixture.out / "source-seal.json").exists())
                self.assertFalse(fixture.reserved.exists())

    def test_shared_c_and_assembler_survive_the_sealed_roundtrip_for_every_family(self):
        api = VERIFY.contracts()
        helper = "engines/scripts/source_composition.py"
        for family in "ABCDEF":
            with self.subTest(family=family), tempfile.TemporaryDirectory(prefix="rove-source-common-") as directory:
                fixture = Fixture(Path(directory), family)
                spec = api.engine_spec(family)
                recipe_path = spec.source_root + "/recipe.json"
                names = (*spec.required_source_inputs, helper, recipe_path)
                expected = {name: (ROOT / name).read_bytes() for name in names}
                for name, data in expected.items():
                    path = fixture.build / "inputs" / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                with fixture.context_patches():
                    fixture.export()
                    fixture.hold_original()
                    with zipfile.ZipFile(fixture.bundle) as archive:
                        for name in names:
                            self.assertEqual(archive.read("artifact/inputs/" + name), expected[name])
                    fixture.restore()
                frozen = fixture.build / "inputs"
                for name, data in expected.items():
                    self.assertEqual((frozen / name).read_bytes(), data)
                # Compose from the transported helper/template/fragments only;
                # no source factory, compiler or engine executes on the target.
                composition = load("transported_composition_" + family, frozen / helper)
                recipe = json.loads((frozen / recipe_path).read_bytes())
                local = "native/board.c" if family == "D" else "engine.c"
                source = composition.read_source(frozen, spec.source_root + "/" + local)
                self.assertEqual(TARGET.pin(source)["sha256"], recipe["assembled_source_sha256"][local])

    def test_D_roundtrip_never_rewrites_absolute_candidate_or_native_paths(self):
        with tempfile.TemporaryDirectory(prefix="rove-source-D-") as directory:
            fixture = Fixture(Path(directory), "D")
            with fixture.context_patches():
                fixture.export()
                fixture.hold_original()
                fixture.restore()
                raw = (fixture.build / "build.json").read_bytes()
                self.assertEqual(raw, fixture.manifest)
                self.assertIn(str(fixture.build / "D-source-jit"), raw.decode())
                self.assertIn(str(fixture.build / "native/x"), raw.decode())

    def test_export_rejects_old_context_free_failed_or_unsettled_pipeline(self):
        mutations = (("source_context", None), ("complete", False), ("functional_complete", False),
                     ("host_cleanup", {"unsettled_commands": 1, "errors": []}))
        for key, value in mutations:
            with self.subTest(key=key), tempfile.TemporaryDirectory(prefix="rove-source-pipeline-") as directory:
                fixture = Fixture(Path(directory))
                fixture.pipeline[key] = value
                fixture.save_pipeline()
                with fixture.context_patches(), self.assertRaises(ValueError):
                    fixture.export()
                self.assertFalse((fixture.out / "source-bundle.zip").exists())

    def test_existing_or_overlapping_root_is_rejected_before_writes(self):
        with tempfile.TemporaryDirectory(prefix="rove-source-root-") as directory:
            fixture = Fixture(Path(directory))
            with fixture.context_patches():
                fixture.export()
                fixture.bundle, fixture.seal = fixture.out / "source-bundle.zip", fixture.out / "source-seal.json"
                with self.assertRaisesRegex(ValueError, "must be new"):
                    fixture.restore()
                fixture.hold_original()
                for reserved in (fixture.out, fixture.out / "target", fixture.runner):
                    with self.subTest(reserved=reserved), self.assertRaises(ValueError):
                        fixture.restore(reserved_out=reserved)
                    self.assertFalse(fixture.out.exists())

    def test_wrong_context_and_runner_temp_are_rejected_before_extract(self):
        with tempfile.TemporaryDirectory(prefix="rove-source-context-") as directory:
            fixture = Fixture(Path(directory))
            with fixture.context_patches():
                fixture.export()
                fixture.hold_original()
                for key, value in (("GITHUB_REPOSITORY", "other/Rove4k"), ("GITHUB_SHA", "b" * 40),
                                   ("GITHUB_RUN_ID", "18"), ("GITHUB_RUN_ATTEMPT", "2")):
                    with patch.dict(os.environ, {key: value}), self.subTest(key=key), self.assertRaises(ValueError):
                        fixture.restore()
                    self.assertFalse(fixture.out.exists())
                alternate = Path(directory) / "other-runner"
                alternate.mkdir()
                with self.assertRaises(ValueError):
                    fixture.restore(runner_temp=alternate)
                self.assertFalse(fixture.out.exists())
                with patch.dict(os.environ, {"RUNNER_TEMP": str(alternate)}), self.assertRaises(ValueError):
                    fixture.restore()
                self.assertFalse(fixture.out.exists())

    def test_modified_zip_or_member_pin_is_rejected_before_extract(self):
        for change in ("zip", "member"):
            with self.subTest(change=change), tempfile.TemporaryDirectory(prefix="rove-source-pin-") as directory:
                fixture = Fixture(Path(directory))
                with fixture.context_patches():
                    fixture.export()
                    fixture.hold_original()
                    if change == "zip":
                        fixture.bundle.write_bytes(fixture.bundle.read_bytes() + b"changed")
                    else:
                        seal = json.loads(fixture.seal.read_bytes())
                        seal["members"]["artifact/main.c"]["sha256"] = "b" * 64
                        fixture.seal.write_text(json.dumps(seal))
                    with self.assertRaises(ValueError):
                        fixture.restore()
                    self.assertFalse(fixture.out.exists())

    def test_unsafe_zip_members_cannot_create_the_original_root(self):
        attacks = ([('artifact/../../escape', b'x', stat.S_IFREG | 0o600)],
                   [('artifact/.env', b'fixture-not-a-secret-file', stat.S_IFREG | 0o600)],
                   [('artifact/link', b'../elsewhere', stat.S_IFLNK | 0o777)],
                   [('artifact/device', b'', stat.S_IFCHR | 0o600)],
                   [('artifact/same', b'x', stat.S_IFREG | 0o600), ('artifact/same', b'y', stat.S_IFREG | 0o600)],
                   [('artifact/file', b'x', stat.S_IFREG | 0o600), ('artifact/file/child', b'y', stat.S_IFREG | 0o600)],
                   [('artifact/' + 'x' * 256, b'x', stat.S_IFREG | 0o600)])
        for entries in attacks:
            with self.subTest(entries=[e[0] for e in entries]), tempfile.TemporaryDirectory(prefix="rove-source-zip-") as directory:
                fixture = Fixture(Path(directory))
                with fixture.context_patches():
                    fixture.export()
                    fixture.hold_original()
                    fixture.write_archive(entries)
                    with self.assertRaises(ValueError):
                        fixture.restore()
                    self.assertFalse(fixture.out.exists())

    def test_collection_rejects_symlinks_hardlinks_and_fifo_before_read(self):
        for kind in ("symlink", "hardlink", "fifo"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(prefix="rove-source-nonregular-") as directory:
                fixture = Fixture(Path(directory))
                path = fixture.build / "unsafe"
                if kind == "symlink":
                    path.symlink_to(fixture.build / "main.c")
                elif kind == "hardlink":
                    os.link(fixture.build / "main.c", path)
                else:
                    os.mkfifo(path)
                with fixture.context_patches(), self.assertRaises(ValueError):
                    fixture.export()
                self.assertFalse((fixture.out / "source-bundle.zip").exists())

    def test_caps_reject_small_test_expansions_without_allocating_large_data(self):
        with tempfile.TemporaryDirectory(prefix="rove-source-cap-") as directory:
            fixture = Fixture(Path(directory))
            with fixture.context_patches():
                fixture.export()
                fixture.hold_original()
                fixture.write_archive([("artifact/large", b"x" * 65, stat.S_IFREG | 0o600)])
                raw = fixture.bundle.read_bytes()
                with patch.object(TARGET, "MAX_MEMBER", 64), self.assertRaisesRegex(ValueError, "bounded uncompressed"):
                    TRANSPORT._zip_modes(raw, None, TARGET)
                self.assertFalse(fixture.out.exists())
                with patch.object(TARGET, "MAX_BUNDLE", len(raw) - 1), self.assertRaisesRegex(ValueError, "raw source bundle"):
                    TRANSPORT._zip_modes(raw, None, TARGET)
                self.assertFalse(fixture.out.exists())

    def test_compressed_or_excessive_member_archives_are_rejected_before_extract(self):
        for kind in ("compressed", "count"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(prefix="rove-source-header-") as directory:
                fixture = Fixture(Path(directory))
                with fixture.context_patches():
                    fixture.export()
                    fixture.hold_original()
                    if kind == "count":
                        fixture.write_archive([(f"artifact/file-{n}", b"", stat.S_IFREG | 0o600) for n in range(10001)])
                    else:
                        stream = io.BytesIO()
                        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                            info = zipfile.ZipInfo("artifact/compressed")
                            info.create_system = 3
                            info.external_attr = (stat.S_IFREG | 0o600) << 16
                            archive.writestr(info, b"x" * 1024, compress_type=zipfile.ZIP_DEFLATED)
                        raw = stream.getvalue()
                        fixture.bundle.write_bytes(raw)
                        seal = json.loads(fixture.seal.read_bytes())
                        seal.update(bundle=TARGET.pin(raw), members={"artifact/compressed": TARGET.pin(b"x" * 1024)})
                        fixture.seal.write_text(json.dumps(seal))
                    with self.assertRaises(ValueError):
                        fixture.restore()
                    self.assertFalse(fixture.out.exists())

    def test_leaf_FIFO_swap_is_nonblocking_and_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rove-source-fifo-race-") as directory:
            root = Path(directory)
            path = root / "owned-data"
            path.write_bytes(b"owned regular bytes")
            original_open = os.open
            swapped = False
            def racing_open(name, flags, *args, **keywords):
                nonlocal swapped
                if name == path.name and keywords.get("dir_fd") is not None and not swapped:
                    swapped = True
                    path.rename(root / "original-held")
                    os.mkfifo(path)
                return original_open(name, flags, *args, **keywords)
            started = time.monotonic()
            with patch.object(TRANSPORT.os, "open", side_effect=racing_open), self.assertRaises(ValueError):
                TRANSPORT._read(path, TARGET)
            self.assertTrue(swapped)
            self.assertLess(time.monotonic() - started, 1)

    def test_ancestor_swaps_cannot_read_scan_or_write_foreign_tree(self):
        for operation in ("read", "scan", "write"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory(prefix="rove-source-ancestor-race-") as directory:
                root = Path(directory)
                owned, foreign = root / "owned", root / "foreign"
                owned.mkdir()
                foreign.mkdir()
                (owned / "owned-file").write_bytes(b"owned")
                (foreign / "foreign-file").write_bytes(b"foreign fixture; must not be read")
                original_open = os.open
                swapped, foreign_leaf_opened = False, False
                def racing_open(name, flags, *args, **keywords):
                    nonlocal swapped, foreign_leaf_opened
                    if name == "foreign-file":
                        foreign_leaf_opened = True
                    if name == owned.name and keywords.get("dir_fd") is not None and not swapped:
                        swapped = True
                        owned.rename(root / "original-held")
                        owned.symlink_to(foreign, target_is_directory=True)
                    return original_open(name, flags, *args, **keywords)
                with patch.object(TRANSPORT.os, "open", side_effect=racing_open), self.assertRaises((OSError, ValueError)):
                    if operation == "read":
                        TRANSPORT._read(owned / "owned-file", TARGET)
                    elif operation == "scan":
                        TRANSPORT._snapshot(owned, TARGET)
                    else:
                        TRANSPORT._write_new(owned / "new-transport", b"must remain owned", TARGET)
                self.assertTrue(swapped)
                self.assertFalse(foreign_leaf_opened)
                self.assertFalse((foreign / "new-transport").exists())

    def test_empty_directory_nodes_are_bounded_before_descending(self):
        with tempfile.TemporaryDirectory(prefix="rove-source-directory-cap-") as directory:
            root = Path(directory)
            class Scan:
                def __enter__(self):
                    return iter(SimpleNamespace(name=f"empty-{n}") for n in range(10000))
                def __exit__(self, *arguments):
                    return False
            with patch.object(TRANSPORT.os, "scandir", return_value=Scan()), self.assertRaisesRegex(ValueError, "total node count"):
                TRANSPORT._snapshot(root, TARGET)

    def test_export_detects_source_mutation_and_preserves_failed_zip(self):
        with tempfile.TemporaryDirectory(prefix="rove-source-drift-") as directory:
            fixture = Fixture(Path(directory))
            original = TARGET.build_source_seal
            def changed(*args, **keywords):
                result = original(*args, **keywords)
                (fixture.build / "main.c").write_bytes(b"changed fixture input")
                return result
            with fixture.context_patches(), patch.object(TARGET, "build_source_seal", side_effect=changed):
                with self.assertRaisesRegex(ValueError, "changed after collection"):
                    fixture.export()
            self.assertTrue((fixture.out / "source-bundle.zip").is_file())
            self.assertFalse((fixture.out / "source-seal.json").exists())

    def test_zip_generation_is_deterministic_and_module_parses_as_Python310(self):
        with tempfile.TemporaryDirectory(prefix="rove-source-deterministic-") as directory:
            fixture = Fixture(Path(directory))
            members, stamps, _ = TRANSPORT._snapshot(fixture.build, TARGET)
            self.assertEqual(TRANSPORT._zip_bytes(members, stamps), TRANSPORT._zip_bytes(members, stamps))
        for name in ("production_source_bundle.py", "test_production_source_bundle.py"):
            ast.parse(Path(__file__).with_name(name).read_text(), filename=name, feature_version=(3, 10))


if __name__ == "__main__":
    unittest.main()
