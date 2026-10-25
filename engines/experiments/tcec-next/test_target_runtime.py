"""Pure contract fixtures only: no compiler or chess engine is executed."""
from __future__ import annotations

import copy
from dataclasses import fields, make_dataclass, replace
import importlib.util
import json
import lzma
import multiprocessing
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TARGET = load("target_runtime_tests_subject", HERE / "target_runtime.py")
VERIFY = load("target_runtime_tests_file_checks", HERE / "profile_verify.py")


def native_fixture():
    identity = b"\x7fELF\x02\x01\x01" + b"\0" * 9
    header = struct.pack("<16sHHIQQQIHHHHHH", identity, 2, 62, 1, 0x4000C8,
                         64, 0, 0, 64, 56, 2, 0, 0, 0)
    load_segment = struct.pack("<IIQQQQQQ", 1, 5, 0, 0x400000, 0, 201, 201, 4096)
    stack = struct.pack("<IIQQQQQQ", 0x6474E551, 6, 0, 0, 0, 0, 0, 16)
    return (header + load_segment + stack).ljust(200, b"\0") + b"\xc3"


def dependency_fixture():
    """A synthetic already-admitted record; not a real producer dependency proof."""
    return {"declaration": {"format": "synthetic-dependency-contract", "required": True},
            "proof": {"format": "synthetic-inverse-proof", "edits": 1},
            "attempts": [{"directory": "attempt-" + str(index),
                          "dependency_gate": {"expanded_source": TARGET.pin(b"synthetic expanded source"),
                                              "inverse": True},
                          "native": TARGET.pin(b"synthetic original native")}
                         for index in range(2)],
            "compiler_commands": [{"kind": "compile", "command": ["cc", "-x", "c", "-"],
                "started": True, "terminal": True, "reaped": True, "returncode": 0,
                "stdout": TARGET.pin(b""), "stderr": TARGET.pin(b""),
                "stdin": {"name": "tool-1-compile.stdin", **TARGET.pin(b"synthetic expanded source")}}]}


class Fixture:
    """Synthetic, source-admission-stubbed transcript, never real evidence."""
    def __init__(self, root, family="A", source_dependencies=None, *, profile_id="test-p4",
                 source_contract=None, wrapper_contract=None):
        self.root = root
        self.compiler = TARGET._compiler_module()
        self.ci = TARGET.CIContext("example/Rove4k", "a" * 40, "123", "1")
        self.family = family
        self.profile_id = profile_id
        self.profile = VERIFY.contracts().resource_profile(profile_id)
        resources = self.profile.to_record(16 if family == "D" else 24)
        source_contract = copy.deepcopy(source_contract) if source_contract is not None else {}
        if source_dependencies is not None:
            source_contract["source_dependencies"] = copy.deepcopy(source_dependencies)
        self.build = root / ("build-" + family)
        self.build.mkdir()
        source = b"int main(void){return 0;}\n"
        header = b"#!/bin/sh\n# synthetic unit header\n"
        payload = lzma.compress(source, format=lzma.FORMAT_ALONE)
        whole = header + payload
        old_native = b"synthetic original-compiler identity, not executed"
        values = {"source": source, "header": header, "payload": payload,
                  "whole": whole, "native": old_native}
        expected = {prefix + "_" + key: value for prefix, data in values.items()
                    for key, value in TARGET.pin(data).items()}
        program = "D-source-jit" if family == "D" else "x"
        self.admitted = VERIFY.AdmittedBuild(family, profile_id, "source-jit", program,
            None if family == "D" else "main.c", "native/x",
            expected, resources, {"mode": "per-go"}, copy.deepcopy(wrapper_contract or {}), {}, source_contract)
        self.verify = SimpleNamespace(
            admit_c_build=lambda record, build: self.admitted,
            admit_d_build=lambda record, build, candidate: self.admitted,
            checked_artifact=VERIFY.checked_artifact, artifact_file=VERIFY.artifact_file,
            native_dependencies=VERIFY.native_dependencies, contracts=VERIFY.contracts)
        self.source = source
        self.manifest = {"family": family, "resources": copy.deepcopy(resources),
            "expected_contract": expected, "source_proofs": [{"target_type_assertions":
                ['_Static_assert(sizeof(void*)==8,"unit ABI");']}],
            "complete": True, "reproducible": True}
        if family != "D":
            self.manifest["compiler"] = list(self.compiler.C_FLAGS[family])
        files = {"main.c": source}
        if family == "D":
            files.update({"start.S": b".global _start\n_start: ret\n", "image.ld": b"ENTRY(_start)\n"})
            builder = load("target_unit_D_flag_contract", TARGET.ROOT / "engines/experiments/tiny-d-submission/build.py")
            self.manifest.update(resource=copy.deepcopy(resources),
                flags=builder.native_flags(self.profile), units=["main.c", "start.S"],
                shipping_inputs={name: TARGET.pin(data) for name, data in files.items()})
        self.manifest_raw = (json.dumps(self.manifest, sort_keys=True) + "\n").encode()
        (self.build / "build.json").write_bytes(self.manifest_raw)
        source_prefix = "shipping-inputs/" if family == "D" else ""
        for name, data in files.items():
            path = self.build / (source_prefix + name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (self.build / program).write_bytes(whole)
        (self.build / "header.sh").write_bytes(header)
        (self.build / "payload.lzma").write_bytes(payload)
        (self.build / "native").mkdir()
        (self.build / "native/x").write_bytes(old_native)
        self.bundle = root / "source-bundle.zip"
        with zipfile.ZipFile(self.bundle, "w") as archive:
            for name in ("build.json", program, "header.sh", "payload.lzma", "native/x",
                         *(source_prefix + n for n in files)):
                archive.writestr("profiles/" + family + "-" + profile_id + "/" + name, (self.build / name).read_bytes())
        with patch.object(TARGET, "_source_host", return_value={"ID": "ubuntu", "VERSION_ID": "24.04"}), \
                patch.object(TARGET, "_checkout_head", return_value=self.ci.head_sha), \
                patch.dict(TARGET.os.environ, self.environment()):
            seal = TARGET.build_source_seal(self.bundle,
                [(self.admitted, self.build, "profiles/" + family + "-" + profile_id)],
                verify=self.verify, ci_context=self.ci)
        self.seal = root / "source-seal.json"
        self.seal.write_text(json.dumps(seal, sort_keys=True) + "\n")
        self.receipt_root = root / "compiler"
        self.receipt_root.mkdir()
        self.receipt = self.receipt_root / "compiler.json"
        self.commands = []
        self.driver = Path(shutil.which("true")).resolve()
        self.header = Path("/usr/include/stdint.h").resolve()
        self.context = {"kind": "ubuntu22-system", "root": "/",
            "input_roots": ["/usr", "/lib", "/lib64", "/bin"],
            "wrapper": {"path": str(self.driver), **TARGET.pin(self.driver.read_bytes())},
            "driver": {"path": str(self.driver), **TARGET.pin(self.driver.read_bytes())},
            "os_release": {"ID": "ubuntu", "VERSION_ID": "22.04", **TARGET.pin(b"synthetic OS fixture")},
            "libc": ["glibc", "2.35"], "scope": "synthetic unit context; never executed"}
        self.add_command("compiler-version", [str(self.driver), "-dumpfullversion"], self.receipt_root,
                         stdout=b"11.4.0\n")
        banner = "synthetic compiler 11.4.0; not executed\n"
        self.add_command("compiler-banner", [str(self.driver), "--version"], self.receipt_root,
                         stdout=banner.encode())
        for query in ("cc1", "as", "ld", "collect2", "lto1"):
            self.add_command("compiler-program-" + query,
                [str(self.driver), "-print-prog-name=" + query], self.receipt_root,
                stdout=(str(self.driver) + "\n").encode())
        selected = self.compiler.admit(self.build, self.verify)
        self.directory = self.receipt_root / (family + "-" + profile_id)
        (self.directory / "source").mkdir(parents=True)
        for name, data in selected.files.items():
            (self.directory / "source" / name).write_bytes(data)
        (self.directory / "input-build.json").write_bytes(self.manifest_raw)
        self.native = native_fixture()
        native_pin = TARGET.pin(self.native)
        if family == "D":
            for unit in selected.units:
                dep = self.directory / ("unit-" + unit + ".d")
                dep.write_text("x: " + str(self.directory / "source" / unit) + " " + str(self.header) + "\n")
                self.add_command("D-dependencies-" + unit,
                    [str(self.driver), *selected.flags, "-M", "-MF", str(dep), str(self.directory / "source" / unit)],
                    self.directory)
        attempts = []
        for label in ("dependency-discovery", "first", "repeat", "target-types"):
            output = self.directory / label
            output.mkdir()
            (output / "x").write_bytes(self.native)
            dependencies = [self.directory / "source/main.c", self.header]
            (output / "dependencies.d").write_text("x: " + " ".join(map(str, dependencies)) + "\n")
            data = source
            if label == "target-types":
                data += ("\n" + "\n".join(selected.assertions) + "\n").encode()
            command = [str(self.driver), *selected.flags]
            if family == "D":
                (output / "main.c").write_bytes(data)
                command += [str(output / "main.c"), str(self.directory / "source/start.S"),
                            "-Wl,-T," + str(self.directory / "source/image.ld"), "-o", "x"]
            command += ["-MD", "-MF", str(output / "dependencies.d"), "-Wl,-t"]
            self.add_command(family + "-" + label, command, output, stdin=None if family == "D" else data,
                             stdout=(str(self.header) + "\n").encode())
            attempts.append({"directory": label, "native": native_pin,
                             "dependencies": sorted(map(str, dependencies))})
        for query in ("cc1", "as", "ld", "collect2", "lto1"):
            self.add_command("compiler-program-recheck-" + query,
                [str(self.driver), "-print-prog-name=" + query], self.receipt_root,
                stdout=(str(self.driver) + "\n").encode())
        self.report = {"format": TARGET.COMPILER_FORMAT, "complete": True,
            "engine_executed": False, "large_TT_allocated": False, "submission_qualified": False,
            "compiler_context": self.context, "compiler_version": banner,
            "source_context": self.ci.to_record(), "source_bundle": TARGET.pin(self.bundle.read_bytes()),
            "source_seal": TARGET.pin(self.seal.read_bytes()),
            "source_profile": {key: value for key, value in seal["profiles"][0].items() if key != "archive_prefix"},
            "host": {"libc": ["glibc", "2.35"]}, "commands": self.commands,
            "host_cleanup": {"unsettled_commands": 0, "errors": []},
            "compiler_consumed_inputs": {str(p): TARGET.pin(p.read_bytes()) for p in (self.driver, self.header)},
            "compiler_programs": {query: {"path": str(self.driver), **TARGET.pin(self.driver.read_bytes())}
                                  for query in ("cc1", "as", "ld", "collect2", "lto1")},
            "compiler_programs_rechecked": True,
            "source_provenance_tools": {name: TARGET.pin((TARGET.ROOT / name).read_bytes().replace(b"\r\n", b"\n")) for name in (TARGET.SELF, TARGET.INPUT_PATH)},
            "tools": {}, "profiles": [{"family": family, "profile": profile_id, "build": str(self.build),
                "input_manifest": TARGET.pin(self.manifest_raw),
                "sources": {name: TARGET.pin(data) for name, data in selected.files.items()},
                "original_compiler_native": copy.deepcopy(expected),
                "flags": list(selected.flags), "attempts": attempts,
                "engine_executed": False, "native": native_pin,
                "elf": self.compiler.elf_abi(self.native, VERIFY), "native_reproduced": True,
                "type_assertions_native_identical": True,
                "dependency_discovery_precedes_two_fresh_compiles": True,
                "cross_compiler_native_identity_required": False}]}
        if "source_dependencies" in self.admitted.source_contract:
            self.report["profiles"][0]["source_dependencies"] = copy.deepcopy(self.admitted.source_contract["source_dependencies"])
        if family == "D":
            self.report["profiles"][0]["per_unit_dependency_discovery"] = list(selected.units)
        for name in (self.compiler.SELF, self.compiler.VERIFY_PATH, self.compiler.HOST_PATH, TARGET.INPUT_PATH, TARGET.SELF):
            data = self.compiler.normalized(TARGET.ROOT / name)
            path = self.receipt_root / "tools" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            if name != TARGET.SELF:
                self.report["tools"][name] = TARGET.pin(data)
        self.save()

    def add_command(self, kind, command, cwd, *, stdin=None, stdout=b""):
        index = len(self.commands) + 1
        row = {"kind": kind, "command": command, "cwd": str(cwd), "started": True,
            "returncode": 0, "terminal": True, "reaped": True, "forced_cleanup": False,
            "owned_group_absent": True, "other_group_members_before_reap": [],
            "original_identity_retained_until_other_members_absent": True}
        for pipe, data in (("stdout", stdout), ("stderr", b"")):
            path = (self.receipt_root / ("tool-" + str(index) + "-" + kind)).with_suffix("." + pipe)
            path.write_bytes(data)
            row[pipe] = {"path": str(path), **TARGET.pin(data)}
        if stdin is not None:
            (self.receipt_root / ("tool-" + str(index) + "-" + kind)).with_suffix(".stdin").write_bytes(stdin)
        self.commands.append(row)

    def save(self):
        self.receipt.write_text(json.dumps(self.report, sort_keys=True) + "\n")

    def cloud_seed(self):
        seed = self.root / "seed"
        seed.mkdir()
        members = {}
        files = {}
        for path in sorted(self.build.rglob("*")):
            if path.is_file():
                relative = path.relative_to(self.build).as_posix()
                name = "artifact/" + relative
                destination = seed / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                data = path.read_bytes()
                destination.write_bytes(data)
                members[name] = {**TARGET.pin(data), "mode": 0o600}
                files[relative] = TARGET.pin(data)
        for path in (self.bundle, self.seal):
            data = path.read_bytes()
            (seed / path.name).write_bytes(data)
            members[path.name] = {**TARGET.pin(data), "mode": 0o600}
        (seed / "rules.json").write_bytes(b'{"synthetic":true}\n')
        members["rules.json"] = {**TARGET.pin((seed / "rules.json").read_bytes()), "mode": 0o600}
        plan = {"original_root": str(self.build), "seed_prefix": "artifact", "files": files}
        manifest = {"format": "rove4k-cloud-seed-v1", "source_origin": self.ci.to_record(),
                    "members": members,
                    "original_layout": {"format": "rove4k-original-layout-plan-v1", "roots": [plan]}}
        raw = (json.dumps(manifest, sort_keys=True) + "\n").encode()
        (seed / "seed.json").write_bytes(raw)
        current = self.build.stat()
        layout = {"format": "rove4k-original-layout-v1", "seed_root": str(seed),
            "seed_manifest": TARGET.pin(raw),
            "roots": [{**plan, "device": current.st_dev, "inode": current.st_ino}],
            "scope": "exact transport correspondence; not source/runtime qualification"}
        return {"source_bundle": seed / self.bundle.name, "source_seal": seed / self.seal.name,
                "source_origin": self.ci.to_record(), "seed_root": seed,
                "member_map": {name: {key: value[key] for key in ("bytes", "sha256")} for name, value in members.items()},
                "restored_layout": layout}

    def environment(self):
        return {**{name: "" for name in (*TARGET.COMPILER_ENV, "CC", "CXX")},
                "GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": self.ci.repository,
                "GITHUB_SHA": self.ci.head_sha, "GITHUB_RUN_ID": self.ci.run_id,
                "GITHUB_RUN_ATTEMPT": self.ci.run_attempt}

    def validate(self, **kwargs):
        with patch.object(TARGET, "current_system_context", return_value=self.context), \
                patch.object(TARGET, "_checkout_head", return_value=self.ci.head_sha), \
                patch.dict(TARGET.os.environ, self.environment()):
            return TARGET.validate_target_runtime(kwargs.pop("admitted", self.admitted), self.build, self.receipt,
                verify=self.verify, source_bundle=self.bundle, source_seal=self.seal,
                expected_ci=kwargs.pop("expected_ci", self.ci), **kwargs)


class PureContext(unittest.TestCase):
    def test_optional_source_dependency_presence_and_nested_types_are_exact(self):
        self.assertTrue(TARGET._same_source_dependencies({}, {}))
        for extra in ({}, None, False):
            self.assertFalse(TARGET._same_source_dependencies({"source_dependencies": extra}, {}))
            self.assertFalse(TARGET._same_source_dependencies({}, {"source_dependencies": extra}))
        for left, right in ((True, 1), (1, 1.0), (False, 0)):
            self.assertFalse(TARGET._same_source_dependencies(
                {"source_dependencies": {"nested": [left]}}, {"source_dependencies": {"nested": [right]}}))
        with self.assertRaisesRegex(ValueError, "JSON-native"):
            TARGET._source_dependency_copy({"not_a_JSON_array": (1, 2)})

    def test_real_compiler_context_rejects_each_redirection_variable(self):
        for name in TARGET.COMPILER_ENV:
            with self.subTest(variable=name), patch.object(TARGET.sys, "platform", "linux"), \
                    patch.object(TARGET.platform, "machine", return_value="x86_64"), \
                    patch.dict(TARGET.os.environ, {name: "synthetic-redirection"}, clear=True):
                with self.assertRaisesRegex(ValueError, "redirection"):
                    TARGET.current_system_context(SimpleNamespace())

    def test_restore_layout_keeps_exact_live_root_output_and_profile_paths(self):
        layout = {"runner_temp_root": "/home/runner/work/_temp",
            "output_root": "/home/runner/work/_temp/rove4k-production-A-1",
            "builds": {"artifact": "/home/runner/work/_temp/rove4k-production-A-1/artifact"}}
        seal = {"profiles": [{"archive_prefix": "artifact", "build_root": layout["builds"]["artifact"]}],
                "restore_layout": layout}
        self.assertEqual(TARGET.validate_restore_layout(seal, runner_temp_root="/home/runner/work/_temp"), layout)
        cases = []
        for key, value in (("runner_temp_root", "/different/temp"),
                           ("output_root", "/outside/output"),
                           ("builds", {"artifact": "/home/runner/work/_temp/rewritten/artifact"})):
            changed = copy.deepcopy(seal)
            changed["restore_layout"][key] = value
            cases.append(changed)
        changed = copy.deepcopy(seal)
        changed["profiles"][0]["build_root"] += "/../artifact"
        cases.append(changed)
        changed = copy.deepcopy(seal)
        changed["restore_layout"]["untrusted_extra_root"] = "/elsewhere"
        cases.append(changed)
        for changed in cases:
            with self.subTest(seal=changed), self.assertRaises(ValueError):
                TARGET.validate_restore_layout(changed, runner_temp_root="/home/runner/work/_temp")
        with self.assertRaisesRegex(ValueError, "live RUNNER_TEMP"):
            TARGET.validate_restore_layout(seal, runner_temp_root=None)

    def test_restore_layout_rejects_overlapping_profiles_and_missing_metadata(self):
        profiles = [{"archive_prefix": "A", "build_root": "/tmp/runner/output/A"},
                    {"archive_prefix": "B", "build_root": "/tmp/runner/output/A/child"}]
        seal = {"profiles": profiles, "restore_layout": {"runner_temp_root": "/tmp/runner",
            "output_root": "/tmp/runner/output", "builds": {p["archive_prefix"]: p["build_root"] for p in profiles}}}
        with self.assertRaisesRegex(ValueError, "not overlap"):
            TARGET.validate_restore_layout(seal, runner_temp_root="/tmp/runner")
        with self.assertRaisesRegex(ValueError, "explicit restore_layout"):
            TARGET.validate_restore_layout({"profiles": profiles}, runner_temp_root="/tmp/runner")

    def test_expected_context_is_live_and_explicit(self):
        with self.assertRaisesRegex(ValueError, "live GitHub Actions"):
            TARGET.CIContext.from_environment({})
        with self.assertRaisesRegex(ValueError, "head SHA"):
            TARGET.CIContext("example/Rove4k", "main", "1", "1")
        with patch.object(TARGET, "_checkout_head", return_value="1" * 40):
            context = TARGET.CIContext.from_environment({"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "a/b",
                "GITHUB_SHA": "1" * 40, "GITHUB_RUN_ID": "2", "GITHUB_RUN_ATTEMPT": "3"})
        self.assertEqual(context.to_record()["run_attempt"], "3")
        with self.assertRaisesRegex(ValueError, "supplied separately"):
            TARGET._ci(context.to_record())

    def test_protected_and_link_bundle_members_are_rejected_before_decompression(self):
        for name in ("../file", "/file", "x/.env", "x/inventory.json", "x/node_modules/data", "x/api_key.txt"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                TARGET._member(name)
        buffer = __import__("io").BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            info = zipfile.ZipInfo("source/link")
            info.external_attr = 0o120777 << 16
            archive.writestr(info, "elsewhere")
        with self.assertRaisesRegex(ValueError, "links"):
            TARGET._archive(buffer.getvalue())

    def test_a_native_map_cannot_construct_a_validated_reference(self):
        with self.assertRaisesRegex(ValueError, "must pass"):
            TARGET.TargetRuntimeReference(None, family="A", profile="test-p4", native_path=Path("x"),
                native_pin={"bytes": 1, "sha256": "0" * 64}, record={})

    def test_manually_constructed_context_cannot_authorize_a_non_CI_consumer(self):
        context = TARGET.CIContext("example/Rove4k", "a" * 40, "123", "1")
        with patch.dict(TARGET.os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "CI-only"):
                TARGET._ci(context)
        with patch.dict(TARGET.os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
            with self.assertRaisesRegex(ValueError, "live workflow identity"):
                TARGET._ci(context)


@unittest.skipUnless(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "POSIX fd-relative reader required")
class EvidenceReadBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Import capability checks before a child deliberately patches os.open.
        TARGET.input_reader()

    def run_bounded_reader(self, action):
        """A regression that FIFO-blocks is killed through its original process handle."""
        context = multiprocessing.get_context("fork")
        received, sent = context.Pipe(duplex=False)
        def worker():
            received.close()
            try:
                sent.send(("returned", action()))
            except BaseException as error:
                sent.send(("rejected", type(error).__name__, str(error)))
            finally:
                sent.close()
        process = context.Process(target=worker)
        process.start()
        sent.close()
        try:
            process.join(2)
            if process.is_alive():
                process.terminate()
                process.join(1)
                if process.is_alive():
                    process.kill()
                    process.join(1)
                self.fail("target evidence read blocked beyond its original bounded process lifetime")
            self.assertEqual(process.exitcode, 0)
            self.assertTrue(received.poll(.5), "bounded reader did not return a result")
            return received.recv()
        finally:
            if process.is_alive():
                process.kill()
                process.join(1)
            received.close()
            process.close()

    def test_ordinary_byte_bound_empty_and_explicit_installed_hardlink_policy(self):
        with tempfile.TemporaryDirectory(prefix="rove-target-file-bounds-") as temporary:
            root = Path(temporary)
            path = root / "evidence.json"
            path.write_bytes(b"source")
            self.assertEqual(TARGET._regular(path, limit=6), b"source")
            with self.assertRaisesRegex(ValueError, "bounded ordinary"):
                TARGET._regular(path, limit=5)
            alias = root / "hardlink.json"
            os.link(path, alias)
            with self.assertRaisesRegex(ValueError, "bounded ordinary"):
                TARGET._regular(path)
            self.assertEqual(TARGET._read_file(path, limit=6, allow_hardlinks=True), b"source")
            alias.unlink()
            path.write_bytes(b"")
            self.assertEqual(TARGET._regular(path, limit=0), b"")

    def test_leaf_FIFO_swap_is_nonblocking_and_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rove-target-fifo-race-") as temporary:
            root = Path(temporary)
            path = root / "evidence.json"
            path.write_bytes(b"original")
            def action():
                original_open = TARGET.os.open
                changed = False
                def swapping_open(name, flags, *args, **kwargs):
                    nonlocal changed
                    if name == path.name and kwargs.get("dir_fd") is not None and not changed:
                        changed = True
                        path.rename(root / "held.json")
                        os.mkfifo(path)
                    return original_open(name, flags, *args, **kwargs)
                try:
                    with patch.object(TARGET.os, "open", side_effect=swapping_open):
                        return TARGET._regular(path)
                except (ValueError, OSError):
                    if changed:
                        raise RuntimeError("swap-exercised-and-rejected")
                    raise
            started = time.monotonic()
            result = self.run_bounded_reader(action)
            self.assertEqual(result, ("rejected", "RuntimeError", "swap-exercised-and-rejected"))
            self.assertLess(time.monotonic() - started, 2)

    def test_ancestor_swap_cannot_follow_foreign_tree_before_or_after_parent_open(self):
        for timing in ("before-parent-open", "after-parent-open"):
            with self.subTest(timing=timing), tempfile.TemporaryDirectory(prefix="rove-target-ancestor-race-") as temporary:
                root = Path(temporary)
                owned, foreign = root / "owned", root / "foreign"
                owned.mkdir()
                foreign.mkdir()
                path = owned / "evidence.json"
                path.write_bytes(b"original")
                (foreign / path.name).write_bytes(b"foreign")
                def action():
                    original_open = TARGET.os.open
                    changed = False
                    def swapping_open(name, flags, *args, **kwargs):
                        nonlocal changed
                        expected = owned.name if timing == "before-parent-open" else path.name
                        if name == expected and kwargs.get("dir_fd") is not None and not changed:
                            changed = True
                            owned.rename(root / "held")
                            owned.symlink_to(foreign, target_is_directory=True)
                        return original_open(name, flags, *args, **kwargs)
                    try:
                        with patch.object(TARGET.os, "open", side_effect=swapping_open):
                            return TARGET._regular(path)
                    except (ValueError, OSError):
                        if changed:
                            raise RuntimeError("swap-exercised-and-rejected")
                        raise
                result = self.run_bounded_reader(action)
                self.assertEqual(result, ("rejected", "RuntimeError", "swap-exercised-and-rejected"))

    def test_same_inode_rewrite_during_bounded_read_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rove-target-rewrite-race-") as temporary:
            path = Path(temporary) / "evidence.json"
            path.write_bytes(b"a" * 100)
            def action():
                original_read = TARGET.os.read
                changed = False
                def rewriting_read(descriptor, size):
                    nonlocal changed
                    data = original_read(descriptor, size)
                    if not changed:
                        changed = True
                        path.write_bytes(b"b" * 100)
                        stamp = path.stat()
                        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1000000000))
                    return data
                with patch.object(TARGET.os, "read", side_effect=rewriting_read):
                    return TARGET._regular(path)
            result = self.run_bounded_reader(action)
            self.assertEqual(result[0], "rejected")

    def test_target_system_inputs_do_not_fall_back_to_Path_read_bytes(self):
        tool = shutil.which("true")
        if tool is None:
            self.skipTest("installed ordinary system tool needed")
        path = Path(tool).resolve()
        with patch.object(Path, "read_bytes", side_effect=AssertionError("unanchored read attempted")):
            self.assertTrue(TARGET._system_input(path))


@unittest.skipUnless(sys.platform == "linux" and shutil.which("true") and Path("/usr/include/stdint.h").is_file(),
                     "pure system-file fixture requires Linux development headers")
class TargetReferenceBoundaries(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rove4k-target-reference-unit-")
        self.addCleanup(self.temporary.cleanup)
        self.fixture = Fixture(Path(self.temporary.name))

    def test_named_P4_and_P28_profiles_bind_every_family_and_original_CI_identity(self):
        self.assertEqual(self.fixture.profile_id, "test-p4")
        self.assertEqual(self.fixture.admitted.resources["workers"], 4)
        for profile_id in ("test-p4", "test-p28"):
            for family in "ABCDEF":
                with self.subTest(profile=profile_id, family=family), \
                        tempfile.TemporaryDirectory(prefix="rove4k-named-target-unit-") as temporary:
                    fixture = Fixture(Path(temporary), family=family, profile_id=profile_id)
                    reference = fixture.validate()
                    record = reference.to_record()
                    profile = VERIFY.contracts().resource_profile(profile_id)
                    expected_resources = profile.to_record(16 if family == "D" else 24)
                    self.assertEqual(fixture.admitted.resources, expected_resources)
                    self.assertEqual(reference.family, family)
                    self.assertEqual(reference.profile, profile_id)
                    self.assertEqual(record["profile"], profile_id)
                    self.assertEqual(record["ci_context"], fixture.ci.to_record())
                    self.assertEqual(set(record["ci_context"]), {"repository", "head_sha", "run_id", "run_attempt"})
                    self.assertEqual(fixture.report["source_profile"]["profile"], profile_id)
                    self.assertEqual(record["execution_admission"],
                                     TARGET.pin(TARGET._admission_snapshot(fixture.admitted).encode()))
                    self.assertEqual(Path(record["target_native"]["path"]).parent.parent.name,
                                     family + "-" + profile_id)
                    self.assertEqual(record["flags"], fixture.report["profiles"][0]["flags"])
                    if profile_id == "test-p28":
                        self.assertEqual(expected_resources["workers"], 28)
                        self.assertEqual(expected_resources["tt_bytes"],
                                         (512 if family == "D" else 384) * (1 << 20))
                    for key in ("factory_replayed_on_target", "runtime_executed", "runtime_qualified",
                                "event_target_confirmed"):
                        self.assertIs(record[key], False)
                    self.assertIs(fixture.report["large_TT_allocated"], False)
                    self.assertEqual(fixture.admitted.expected["native_sha256"],
                                     record["original_build_expected_contract"]["native_sha256"])

    def test_P4_and_P28_seals_compiler_profiles_and_admissions_cannot_be_spliced(self):
        for profile_id, other_profile in (("test-p4", "test-p28"), ("test-p28", "test-p4")):
            with self.subTest(profile=profile_id), \
                    tempfile.TemporaryDirectory(prefix="rove4k-profile-splice-unit-") as temporary:
                fixture = Fixture(Path(temporary), profile_id=profile_id)
                original_report = copy.deepcopy(fixture.report)
                for role in ("source_profile", "compiler_row"):
                    fixture.report = copy.deepcopy(original_report)
                    row = fixture.report["source_profile"] if role == "source_profile" else fixture.report["profiles"][0]
                    row["profile"] = other_profile
                    fixture.save()
                    with self.subTest(role=role), self.assertRaises(ValueError):
                        fixture.validate()
                fixture.report = original_report
                fixture.save()
                original_seal = fixture.seal.read_bytes()
                seal = json.loads(original_seal)
                seal["profiles"][0]["profile"] = other_profile
                fixture.seal.write_text(json.dumps(seal) + "\n")
                with self.assertRaisesRegex(ValueError, "unique selected family/profile"):
                    fixture.validate()
                fixture.seal.write_bytes(original_seal)
                resources = VERIFY.contracts().resource_profile(other_profile).to_record(24)
                for changed in (replace(fixture.admitted, profile_id=other_profile),
                                replace(fixture.admitted, profile_id=other_profile, resources=resources)):
                    with self.assertRaisesRegex(ValueError, "fresh strict source admission"):
                        fixture.validate(admitted=changed)
                self.assertEqual(fixture.validate().profile, profile_id)

    def test_P28_binds_every_admission_field_including_nested_compound_and_wrapper_policy(self):
        # These nested policies are synthetic admission data, not a real compound proof.
        compound = {"post_spelling": {"selection": "compound", "variant": "clock-atomic-launcher"},
                    "compound_native_evidence": {"source": TARGET.pin(b"synthetic compound source"),
                        "native_policy": {"id": "synthetic-policy", "full": True},
                        "attempts": [{"directory": "synthetic-attempt", "terminal": True}]}}
        wrapper = {"policy": "synthetic-wrapper-ownership", "cleanup": {"per_go": True, "owners": ["launcher"]}}
        with tempfile.TemporaryDirectory(prefix="rove4k-P28-admission-unit-") as temporary:
            fixture = Fixture(Path(temporary), family="F", profile_id="test-p28",
                              source_contract=compound, wrapper_contract=wrapper)
            original = fixture.admitted
            reference = fixture.validate()
            inputs = fixture.cloud_seed()
            with patch.object(TARGET, "ORIGINAL_LAYOUT_PARENT", fixture.root), \
                    patch.dict(TARGET.os.environ, {}, clear=True):
                source = TARGET.sealed_source_binding(original, fixture.build, verify=fixture.verify, **inputs)
                for field in fields(original):
                    value = getattr(original, field.name)
                    if isinstance(value, dict):
                        changed = {**copy.deepcopy(value), "synthetic_changed": True}
                    elif type(value) is bool:
                        changed = not value
                    elif value is None:
                        changed = "synthetic_changed"
                    else:
                        changed = value + "-synthetic_changed"
                    admission = replace(original, **{field.name: changed})
                    with self.subTest(field=field.name), self.assertRaisesRegex(ValueError, "execution object differs"):
                        source.assert_admission(admission, fixture.build)
                    with self.subTest(field=field.name), self.assertRaisesRegex(ValueError, "execution admission differs"):
                        reference.assert_admission(admission, fixture.build)
            changes = []
            for field, path, value in (
                    ("source_contract", ("post_spelling", "variant"), "control"),
                    ("source_contract", ("compound_native_evidence", "native_policy", "full"), False),
                    ("source_contract", ("compound_native_evidence", "attempts", 0, "terminal"), 1),
                    ("wrapper_contract", ("cleanup", "per_go"), False),
                    ("resources", ("workers",), 4),
                    ("resources", ("tt_bytes",), 96 * (1 << 20))):
                changed = copy.deepcopy(getattr(original, field))
                cursor = changed
                for key in path[:-1]:
                    cursor = cursor[key]
                cursor[path[-1]] = value
                changes.append((field + "/" + "/".join(map(str, path)), replace(original, **{field: changed})))
            changes.append(("full", replace(original, full=False)))
            for name, admission in changes:
                with self.subTest(policy=name), self.assertRaises(ValueError):
                    fixture.validate(admitted=admission)
                with self.subTest(policy=name), self.assertRaisesRegex(ValueError, "execution admission differs"):
                    reference.assert_admission(admission, fixture.build)
            self.assertEqual(original.source_contract, compound)
            self.assertEqual(original.wrapper_contract, wrapper)

    def test_P28_typed_dependencies_bind_CI_and_original_layout_with_unchanged_origin(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-P28-dependencies-unit-") as temporary:
            fixture = Fixture(Path(temporary), profile_id="test-p28", source_dependencies=dependency_fixture())
            reference = fixture.validate()
            facts, _, _ = TARGET._source_facts(fixture.admitted, fixture.build, fixture.verify, fixture.compiler)
            self.assertEqual(TARGET._frozen_value(facts["source_dependencies"]),
                             TARGET._frozen_value(dependency_fixture()))
            self.assertEqual(reference.to_record()["ci_context"], fixture.ci.to_record())
            original_report = copy.deepcopy(fixture.report)
            for role in ("source_profile", "compiler_row"):
                fixture.report = copy.deepcopy(original_report)
                row = fixture.report["source_profile"] if role == "source_profile" else fixture.report["profiles"][0]
                row["source_dependencies"]["declaration"]["required"] = 1
                fixture.save()
                with self.subTest(role=role), self.assertRaisesRegex(ValueError, "dependency proof/native/compiler stdin"):
                    fixture.validate()
            fixture.report = original_report
            fixture.save()
            inputs = fixture.cloud_seed()
            with patch.object(TARGET, "ORIGINAL_LAYOUT_PARENT", fixture.root), \
                    patch.dict(TARGET.os.environ, {}, clear=True):
                source = TARGET.sealed_source_binding(fixture.admitted, fixture.build, verify=fixture.verify, **inputs)
                source_record = source.to_record()
                self.assertEqual(source_record["source_origin"], fixture.ci.to_record())
                self.assertEqual(source_record["binding"]["source_context"], fixture.ci.to_record())
                self.assertEqual(source_record["binding"]["source_profile"]["profile"], "test-p28")
                self.assertIs(source_record["factory_replayed_on_consumer"], False)
                self.assertEqual(TARGET._frozen_value(source_record["binding"]["source_profile"]["source_dependencies"]),
                                 TARGET._frozen_value(dependency_fixture()))
                for name in ("source_context", "source_bundle", "source_seal", "source_provenance_tools", "source_profile"):
                    fixture.report.pop(name)
                fixture.report["program_provenance"] = True
                fixture.save()
                with patch.object(TARGET, "current_system_context", return_value=fixture.context):
                    compiled = TARGET.compiler_receipt_binding(fixture.admitted, fixture.build, fixture.receipt,
                        verify=fixture.verify, source_binding=source)
                    evidence = compiled.to_record()["evidence"]
                    self.assertEqual(evidence["source_origin"], fixture.ci.to_record())
                    self.assertEqual(TARGET._frozen_value(evidence["source_dependencies"]),
                                     TARGET._frozen_value(dependency_fixture()))
                    self.assertIs(evidence["engine_executed"], False)
                    self.assertIs(evidence["runtime_qualified"], False)
                    fixture.report["profiles"][0]["source_dependencies"]["compiler_commands"][0]["terminal"] = 1
                    fixture.save()
                    with self.assertRaisesRegex(ValueError, "dependency proof/native/compiler stdin"):
                        TARGET.compiler_receipt_binding(fixture.admitted, fixture.build, fixture.receipt,
                            verify=fixture.verify, source_binding=source)

    def test_non_CI_source_and_compiler_authority_use_original_layout_without_fake_environment(self):
        inputs = self.fixture.cloud_seed()
        with patch.object(TARGET, "ORIGINAL_LAYOUT_PARENT", self.fixture.root), \
                patch.dict(TARGET.os.environ, {}, clear=True):
            source = TARGET.sealed_source_binding(self.fixture.admitted, self.fixture.build,
                verify=self.fixture.verify, **inputs)
            self.assertIs(type(source), TARGET.ValidatedSourceEvidence)
            self.assertEqual(source.assert_member(self.fixture.build / "main.c"), "artifact/main.c")
            self.assertEqual(source.member_bytes(inputs["seed_root"] / "rules.json"), b'{"synthetic":true}\n')
            self.assertEqual(source.to_record()["source_origin"], self.fixture.ci.to_record())
            self.assertFalse(source.to_record()["factory_replayed_on_consumer"])
            source.revalidate(verify=self.fixture.verify)
            for name in ("source_context", "source_bundle", "source_seal", "source_provenance_tools", "source_profile"):
                self.fixture.report.pop(name)
            self.fixture.report["program_provenance"] = True
            self.fixture.save()
            with patch.object(TARGET, "current_system_context", return_value=self.fixture.context):
                result = TARGET.compiler_receipt_binding(self.fixture.admitted, self.fixture.build,
                    self.fixture.receipt, verify=self.fixture.verify, source_binding=source)
            record = result.to_record()
            self.assertEqual(set(record), {"native_path", "native", "compiler_context", "compiler_inputs", "evidence"})
            self.assertEqual(record["native"], TARGET.pin(self.fixture.native))
            self.assertFalse(record["evidence"]["runtime_qualified"])
            self.assertEqual(set(record["evidence"]["source_provenance_tools"]), {TARGET.SELF, TARGET.INPUT_PATH})
            self.assertEqual(self.fixture.admitted.expected["native_sha256"],
                             self.fixture.report["profiles"][0]["original_compiler_native"]["native_sha256"])

    def test_cloud_source_rejects_changed_origin_mapping_inode_and_members(self):
        original = self.fixture.cloud_seed()
        with patch.object(TARGET, "ORIGINAL_LAYOUT_PARENT", self.fixture.root), patch.dict(TARGET.os.environ, {}, clear=True):
            for field in ("origin", "inode", "filemap", "seedpin"):
                inputs = copy.deepcopy(original)
                if field == "origin":
                    inputs["source_origin"]["run_attempt"] = "2"
                elif field == "inode":
                    inputs["restored_layout"]["roots"][0]["inode"] += 1
                elif field == "filemap":
                    inputs["restored_layout"]["roots"][0]["files"]["main.c"]["sha256"] = "0" * 64
                else:
                    inputs["restored_layout"]["seed_manifest"]["sha256"] = "0" * 64
                with self.subTest(field=field), self.assertRaises(ValueError):
                    TARGET.sealed_source_binding(self.fixture.admitted, self.fixture.build, verify=self.fixture.verify, **inputs)
            source = TARGET.sealed_source_binding(self.fixture.admitted, self.fixture.build, verify=self.fixture.verify, **original)
            with self.assertRaises(ValueError):
                source.assert_member(self.fixture.root / "unregistered")
            (original["seed_root"] / "rules.json").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                source.member_bytes(original["seed_root"] / "rules.json")
            with self.assertRaises(ValueError):
                source.assert_admission(replace(self.fixture.admitted, program="other"), self.fixture.build)

    def test_cloud_compiler_rejects_naked_source_map_missing_program_flag_CI_claim_and_SDK(self):
        inputs = self.fixture.cloud_seed()
        with patch.object(TARGET, "ORIGINAL_LAYOUT_PARENT", self.fixture.root), patch.dict(TARGET.os.environ, {}, clear=True):
            source = TARGET.sealed_source_binding(self.fixture.admitted, self.fixture.build, verify=self.fixture.verify, **inputs)
            with self.assertRaisesRegex(ValueError, "validated source evidence"):
                TARGET.compiler_receipt_binding(self.fixture.admitted, self.fixture.build, self.fixture.receipt,
                    verify=self.fixture.verify, source_binding=source.to_record())
            original = copy.deepcopy(self.fixture.report)
            for field in ("program_flag", "CI_claim", "SDK"):
                self.fixture.report = copy.deepcopy(original)
                for name in ("source_context", "source_bundle", "source_seal", "source_provenance_tools", "source_profile"):
                    self.fixture.report.pop(name)
                self.fixture.report["program_provenance"] = True
                if field == "program_flag":
                    self.fixture.report["program_provenance"] = False
                elif field == "CI_claim":
                    self.fixture.report["source_context"] = self.fixture.ci.to_record()
                else:
                    self.fixture.report["compiler_context"]["kind"] = "audited-jammy-sdk"
                self.fixture.save()
                with self.subTest(field=field), patch.object(TARGET, "current_system_context", return_value=self.fixture.context), \
                        self.assertRaisesRegex(ValueError, "program provenance|claim live CI|runtime eligible"):
                    TARGET.compiler_receipt_binding(self.fixture.admitted, self.fixture.build, self.fixture.receipt,
                        verify=self.fixture.verify, source_binding=source)

    def test_cloud_D_preserves_both_units_linker_and_all_common_compiler_guards(self):
        root = self.fixture.root / "cloud-D"
        root.mkdir()
        fixture = Fixture(root, family="D")
        inputs = fixture.cloud_seed()
        with patch.object(TARGET, "ORIGINAL_LAYOUT_PARENT", root), patch.dict(TARGET.os.environ, {}, clear=True):
            source = TARGET.sealed_source_binding(fixture.admitted, fixture.build, verify=fixture.verify, **inputs)
            self.assertEqual(source.member_bytes(fixture.build / "shipping-inputs/start.S"),
                             b".global _start\n_start: ret\n")
            self.assertEqual(set(source.to_record()["binding"]["source_profile"]["source_files"]),
                             {"main.c", "start.S", "image.ld"})
            self.assertNotIn("source_dependencies", source.to_record()["binding"]["source_profile"])
            for name in ("source_context", "source_bundle", "source_seal", "source_provenance_tools", "source_profile"):
                fixture.report.pop(name)
            fixture.report["program_provenance"] = True
            fixture.save()
            with patch.object(TARGET, "current_system_context", return_value=fixture.context):
                compiled = TARGET.compiler_receipt_binding(fixture.admitted, fixture.build,
                    fixture.receipt, verify=fixture.verify, source_binding=source)
                self.assertEqual(compiled.to_record()["native"], TARGET.pin(fixture.native))
                path = fixture.receipt_root / "D-test-p4/target-types/main.c"
                path.write_bytes(b"int main(void){return 1;}\n")
                with self.assertRaisesRegex(ValueError, "type-gate source"):
                    TARGET.compiler_receipt_binding(fixture.admitted, fixture.build,
                        fixture.receipt, verify=fixture.verify, source_binding=source)

    def test_cloud_source_revalidation_rejects_replaced_original_root_and_retained_object_mutation(self):
        inputs = self.fixture.cloud_seed()
        with patch.object(TARGET, "ORIGINAL_LAYOUT_PARENT", self.fixture.root), patch.dict(TARGET.os.environ, {}, clear=True):
            source = TARGET.sealed_source_binding(self.fixture.admitted, self.fixture.build, verify=self.fixture.verify, **inputs)
            snapshot = source.to_record()
            returned = source.to_record()
            returned["binding"]["source_profile"]["program"] = "mutated-copy"
            self.assertEqual(source.to_record(), snapshot)
            self.fixture.admitted.source_contract["unexpected"] = True
            with self.assertRaisesRegex(ValueError, "execution object"):
                source.revalidate(verify=self.fixture.verify)
            self.fixture.admitted.source_contract.pop("unexpected")
            held = self.fixture.root / "held-original-build"
            self.fixture.build.rename(held)
            shutil.copytree(held, self.fixture.build)
            with self.assertRaisesRegex(ValueError, "root inode"):
                source.revalidate(verify=self.fixture.verify)

    def test_final_source_dependency_record_binds_CI_and_cloud_proof_native_and_stdin(self):
        root = self.fixture.root / "dependencies"
        root.mkdir()
        fixture = Fixture(root, source_dependencies=dependency_fixture())
        reference = fixture.validate()
        self.assertIs(type(reference), TARGET.TargetRuntimeReference)
        facts, _, _ = TARGET._source_facts(fixture.admitted, fixture.build, fixture.verify, fixture.compiler)
        self.assertEqual(facts["source_dependencies"], dependency_fixture())
        facts["source_dependencies"]["attempts"][0]["native"]["bytes"] += 1
        self.assertEqual(fixture.admitted.source_contract["source_dependencies"], dependency_fixture())
        inputs = fixture.cloud_seed()
        with patch.object(TARGET, "ORIGINAL_LAYOUT_PARENT", root), patch.dict(TARGET.os.environ, {}, clear=True):
            source = TARGET.sealed_source_binding(fixture.admitted, fixture.build, verify=fixture.verify, **inputs)
            self.assertEqual(source.to_record()["binding"]["source_profile"]["source_dependencies"], dependency_fixture())
            for name in ("source_context", "source_bundle", "source_seal", "source_provenance_tools", "source_profile"):
                fixture.report.pop(name)
            fixture.report["program_provenance"] = True
            fixture.save()
            with patch.object(TARGET, "current_system_context", return_value=fixture.context):
                compiled = TARGET.compiler_receipt_binding(fixture.admitted, fixture.build, fixture.receipt,
                    verify=fixture.verify, source_binding=source)
                self.assertEqual(compiled.to_record()["evidence"]["source_dependencies"], dependency_fixture())
                fixture.report["profiles"][0]["source_dependencies"]["compiler_commands"][0]["stdin"]["sha256"] = "0" * 64
                fixture.save()
                with self.assertRaisesRegex(ValueError, "dependency proof/native/compiler stdin"):
                    TARGET.compiler_receipt_binding(fixture.admitted, fixture.build, fixture.receipt,
                        verify=fixture.verify, source_binding=source)

    def test_dependency_row_presence_and_each_original_receipt_component_cannot_drift(self):
        root = self.fixture.root / "dependencies"
        root.mkdir()
        fixture = Fixture(root, source_dependencies=dependency_fixture())
        original = copy.deepcopy(fixture.report)
        for field in ("omission", "attempt_order", "directory", "gate", "native", "stdout", "stderr", "stdin", "bool_as_int", "int_as_float"):
            fixture.report = copy.deepcopy(original)
            row = fixture.report["profiles"][0]
            evidence = row["source_dependencies"]
            if field == "omission":
                row.pop("source_dependencies")
            elif field == "attempt_order":
                evidence["attempts"].reverse()
            elif field == "directory":
                evidence["attempts"][0]["directory"] = "another-directory"
            elif field == "gate":
                evidence["attempts"][0]["dependency_gate"]["inverse"] = False
            elif field == "native":
                evidence["attempts"][0]["native"]["sha256"] = "0" * 64
            elif field in ("stdout", "stderr", "stdin"):
                evidence["compiler_commands"][0][field]["sha256"] = "0" * 64
            elif field == "bool_as_int":
                evidence["compiler_commands"][0]["terminal"] = 1
            else:
                evidence["proof"]["edits"] = 1.0
            fixture.save()
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "dependency proof/native/compiler stdin"):
                fixture.validate()
        for role in ("source_profile", "row"):
            fixture.report = copy.deepcopy(original)
            selected = fixture.report["source_profile"] if role == "source_profile" else fixture.report["profiles"][0]
            selected["source_dependencies"]["declaration"]["required"] = 1
            fixture.save()
            with self.subTest(role=role), self.assertRaisesRegex(ValueError, "dependency proof/native/compiler stdin"):
                fixture.validate()
        fixture.report = copy.deepcopy(original)
        fixture.save()
        changed_seal = json.loads(fixture.seal.read_bytes())
        changed_seal["profiles"][0]["source_dependencies"]["compiler_commands"][0]["terminal"] = 1
        fixture.seal.write_text(json.dumps(changed_seal) + "\n")
        with self.assertRaisesRegex(ValueError, "source seal dependency"):
            fixture.validate()
        for extra in ({}, None):
            self.fixture.report["profiles"][0]["source_dependencies"] = extra
            self.fixture.save()
            with self.subTest(unexpected=extra), self.assertRaisesRegex(ValueError, "dependency proof/native/compiler stdin"):
                self.fixture.validate()

    def test_full_unit_contract_keeps_original_native_and_never_claims_execution(self):
        before = copy.deepcopy(self.fixture.admitted.expected)
        reference = self.fixture.validate()
        record = reference.to_record()
        self.assertEqual(self.fixture.admitted.expected, before)
        self.assertEqual(reference.native_pin, TARGET.pin(self.fixture.native))
        self.assertNotEqual(reference.native_pin["sha256"], before["native_sha256"])
        self.assertFalse(record["factory_replayed_on_target"])
        self.assertFalse(record["runtime_executed"])
        self.assertFalse(record["runtime_qualified"])
        self.assertEqual(record["consumer_scope"], "github-actions-ubuntu22-system")
        changed = reference.native_pin
        changed["sha256"] = "0" * 64
        self.assertEqual(reference.native_pin, TARGET.pin(self.fixture.native))

    def test_sdk_and_missing_source_provenance_never_promote(self):
        for mutate in (lambda r: r["compiler_context"].update(kind="audited-jammy-sdk"),
                       lambda r: r.pop("source_seal"), lambda r: r.pop("source_profile"),
                       lambda r: r.update(complete=False)):
            original = copy.deepcopy(self.fixture.report)
            mutate(self.fixture.report)
            self.fixture.save()
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                self.fixture.validate()
            self.fixture.report = original

    def test_wrong_ci_head_run_or_bundle_identity_is_rejected(self):
        other = TARGET.CIContext("example/Rove4k", "b" * 40, "123", "1")
        with self.assertRaisesRegex(ValueError, "live workflow identity|git HEAD|seal context"):
            self.fixture.validate(expected_ci=other)
        self.fixture.report["source_context"]["run_id"] = "124"
        self.fixture.save()
        with self.assertRaisesRegex(ValueError, "matching CI"):
            self.fixture.validate()

    def test_wrong_source_header_flags_profile_and_manifest_are_rejected(self):
        changes = (
            lambda r: r["profiles"][0]["sources"]["main.c"].update(sha256="0" * 64),
            lambda r: r["profiles"][0]["flags"].append("-DREDUCED=1"),
            lambda r: r["profiles"][0].update(profile="test-p28"),
            lambda r: r["profiles"][0]["input_manifest"].update(sha256="0" * 64),
        )
        for change in changes:
            original = copy.deepcopy(self.fixture.report)
            change(self.fixture.report)
            self.fixture.save()
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.fixture.validate()
            self.fixture.report = original
        (self.fixture.build / "x").write_bytes(b"different source-JIT header")
        with self.assertRaises(ValueError):
            self.fixture.validate()

    def test_actual_type_gate_native_and_compiler_stdin_are_checked(self):
        output = self.fixture.directory / "target-types/x"
        output.write_bytes(self.fixture.native + b"different")
        with self.assertRaisesRegex(ValueError, "native repetitions"):
            self.fixture.validate()
        output.write_bytes(self.fixture.native)
        command_index = next(i for i, r in enumerate(self.fixture.commands, 1) if r["kind"] == "A-first")
        source = self.fixture.receipt_root / ("tool-" + str(command_index) + "-A-first.stdin")
        source.write_bytes(b"int main(void){return 7;}")
        with self.assertRaisesRegex(ValueError, "stdin/type assertions"):
            self.fixture.validate()

    def test_failed_or_forced_owned_commands_and_spliced_raw_output_are_rejected(self):
        original = copy.deepcopy(self.fixture.report)
        for key, value in (("forced_cleanup", True), ("returncode", 1), ("reaped", False)):
            self.fixture.report = copy.deepcopy(original)
            self.fixture.report["commands"][0][key] = value
            self.fixture.save()
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, "original group"):
                self.fixture.validate()
        self.fixture.report = original
        self.fixture.save()
        (self.fixture.receipt_root / "tool-1-compiler-version.stdout").write_bytes(b"13.3.0\n")
        with self.assertRaisesRegex(ValueError, "raw pipe identity"):
            self.fixture.validate()

    def test_changed_system_context_and_consumed_file_pin_are_rejected(self):
        with patch.object(TARGET, "current_system_context", return_value={"kind": "other"}), \
                patch.object(TARGET, "_checkout_head", return_value=self.fixture.ci.head_sha), \
                patch.dict(TARGET.os.environ, self.fixture.environment()):
            with self.assertRaisesRegex(ValueError, "current source-JIT"):
                TARGET.validate_target_runtime(self.fixture.admitted, self.fixture.build, self.fixture.receipt,
                    verify=self.fixture.verify, source_bundle=self.fixture.bundle, source_seal=self.fixture.seal,
                    expected_ci=self.fixture.ci)
        self.fixture.report["compiler_consumed_inputs"][str(self.fixture.header)]["sha256"] = "0" * 64
        self.fixture.save()
        with self.assertRaisesRegex(ValueError, "changed after compile"):
            self.fixture.validate()

    def test_omitted_consumed_header_and_changed_subprogram_role_are_rejected(self):
        original = copy.deepcopy(self.fixture.report)
        self.fixture.report["compiler_consumed_inputs"].pop(str(self.fixture.header))
        self.fixture.save()
        with self.assertRaisesRegex(ValueError, "missing dependencies"):
            self.fixture.validate()
        self.fixture.report = original
        self.fixture.report["compiler_programs"]["as"]["path"] = str(self.fixture.header)
        self.fixture.save()
        with self.assertRaisesRegex(ValueError, "subprogram role changed"):
            self.fixture.validate()

    def test_unrelated_consumed_path_is_rejected_without_reading_it(self):
        self.fixture.report["compiler_consumed_inputs"]["/usr/unrelated-data"] = {
            "bytes": 1, "sha256": "0" * 64}
        self.fixture.save()
        original = TARGET._system_input
        def guarded(path):
            self.assertNotEqual(str(path), "/usr/unrelated-data")
            return original(path)
        with patch.object(TARGET, "_system_input", side_effect=guarded):
            with self.assertRaisesRegex(ValueError, "unrelated extra paths"):
                self.fixture.validate()

    def test_executed_shared_reader_must_be_bound_in_both_tool_roles(self):
        original = copy.deepcopy(self.fixture.report)
        for role in ("source_provenance_tools", "tools"):
            self.fixture.report = copy.deepcopy(original)
            self.fixture.report[role].pop(TARGET.INPUT_PATH)
            self.fixture.save()
            with self.subTest(role=role), self.assertRaisesRegex(ValueError, "matching CI/source|tool closure"):
                self.fixture.validate()

    def test_post_compile_role_and_optional_helper_evidence_cannot_be_skipped(self):
        original = copy.deepcopy(self.fixture.report)
        self.fixture.report["compiler_programs_rechecked"] = False
        self.fixture.save()
        with self.assertRaisesRegex(ValueError, "not rechecked"):
            self.fixture.validate()
        self.fixture.report = copy.deepcopy(original)
        recheck = next(r for r in self.fixture.report["commands"] if r["kind"] == "compiler-program-recheck-as")
        recheck["command"] = [str(self.fixture.driver), "--version"]
        self.fixture.save()
        with self.assertRaisesRegex(ValueError, "role query absent"):
            self.fixture.validate()
        self.fixture.report = original
        self.fixture.report.pop("source_provenance_tools")
        self.fixture.save()
        with self.assertRaisesRegex(ValueError, "matching CI"):
            self.fixture.validate()

    def test_reindexed_post_queries_cannot_precede_target_compilation(self):
        fixture = self.fixture
        old_rows = list(fixture.report["commands"])
        data = {}
        for index, row in enumerate(old_rows, 1):
            stem = fixture.receipt_root / ("tool-" + str(index) + "-" + row["kind"])
            data[row["kind"]] = {pipe: stem.with_suffix("." + pipe).read_bytes()
                for pipe in ("stdout", "stderr", "stdin") if stem.with_suffix("." + pipe).is_file()}
        ordered = ([r for r in old_rows if r["kind"].startswith("compiler-program-recheck-")] +
                   [r for r in old_rows if not r["kind"].startswith("compiler-program-recheck-")])
        for index, row in enumerate(ordered, 1):
            stem = fixture.receipt_root / ("tool-" + str(index) + "-" + row["kind"])
            for pipe, value in data[row["kind"]].items():
                path = stem.with_suffix("." + pipe)
                path.write_bytes(value)
                if pipe != "stdin":
                    row[pipe] = {"path": str(path), **TARGET.pin(value)}
        fixture.report["commands"] = ordered
        fixture.save()
        with self.assertRaisesRegex(ValueError, "chronology differs"):
            fixture.validate()

    def test_saved_reference_is_revalidated_not_trusted_as_native_map(self):
        reference = self.fixture.validate()
        path = self.fixture.root / "target-runtime.json"
        record = reference.to_record()
        record["target_native"]["sha256"] = "0" * 64
        path.write_text(json.dumps(record))
        with patch.object(TARGET, "current_system_context", return_value=self.fixture.context), \
                patch.object(TARGET, "_checkout_head", return_value=self.fixture.ci.head_sha), \
                patch.dict(TARGET.os.environ, self.fixture.environment()):
            with self.assertRaisesRegex(ValueError, "saved target reference"):
                TARGET.load_reference(path, self.fixture.admitted, self.fixture.build, self.fixture.receipt,
                    verify=self.fixture.verify, source_bundle=self.fixture.bundle, source_seal=self.fixture.seal,
                    expected_ci=self.fixture.ci)

    def test_before_post_revalidation_retains_the_entire_reference(self):
        reference = self.fixture.validate()
        with patch.object(TARGET, "current_system_context", return_value=self.fixture.context), \
                patch.object(TARGET, "_checkout_head", return_value=self.fixture.ci.head_sha), \
                patch.dict(TARGET.os.environ, self.fixture.environment()):
            same = reference.revalidate(verify=self.fixture.verify, expected_ci=self.fixture.ci)
            self.assertEqual(same.to_record(), reference.to_record())
            self.fixture.report["host"]["additional_observation"] = "changed after initial reference"
            self.fixture.save()
            with self.assertRaisesRegex(ValueError, "changed between"):
                reference.revalidate(verify=self.fixture.verify, expected_ci=self.fixture.ci)

    def test_fresh_source_admission_rejects_every_execution_body_field_change(self):
        original = self.fixture.admitted
        changes = {"program": "another-program", "source": "another-source.c", "native": "another-native",
            "wrapper_contract": {"different": "ownership"}, "source_contract": {"different": "body proof"},
            "full": False}
        for name, value in changes.items():
            with self.subTest(field=name), self.assertRaises(ValueError):
                self.fixture.validate(admitted=replace(original, **{name: value}))

    def test_reference_execution_object_cannot_change_any_dataclass_field(self):
        original = self.fixture.admitted
        reference = self.fixture.validate()
        reference.assert_admission(copy.deepcopy(original), self.fixture.build)
        changed_names = set()
        for field in fields(original):
            value = getattr(original, field.name)
            if isinstance(value, dict):
                changed = {**copy.deepcopy(value), "unit_changed": True}
            elif type(value) is bool:
                changed = not value
            elif value is None:
                changed = "unit_changed"
            elif type(value) is str:
                changed = value + "-unit_changed"
            else:
                self.fail("fixture must exercise every admission field: " + field.name)
            changed_names.add(field.name)
            with self.subTest(field=field.name), self.assertRaisesRegex(ValueError, "execution admission differs"):
                reference.assert_admission(replace(original, **{field.name: changed}), self.fixture.build)
        self.assertEqual(changed_names, {field.name for field in fields(original)})
        with self.assertRaisesRegex(ValueError, "build root differs"):
            reference.assert_admission(original, self.fixture.build.parent / "different-build")

    def test_reference_snapshot_is_immutable_when_retained_nested_dict_changes(self):
        reference = self.fixture.validate()
        recorded = reference.to_record()
        self.fixture.admitted.wrapper_contract["changed_after_creation"] = {"nested": [1]}
        with self.assertRaisesRegex(ValueError, "immutable target reference"):
            reference.assert_admission(self.fixture.admitted, self.fixture.build)
        self.assertEqual(reference.to_record(), recorded)
        with patch.object(TARGET, "current_system_context", return_value=self.fixture.context), \
                patch.object(TARGET, "_checkout_head", return_value=self.fixture.ci.head_sha), \
                patch.dict(TARGET.os.environ, self.fixture.environment()):
            with self.assertRaisesRegex(ValueError, "immutable target reference"):
                reference.revalidate(verify=self.fixture.verify, expected_ci=self.fixture.ci)

    def test_identically_shaped_other_dataclass_is_not_the_admitted_execution_type(self):
        original = self.fixture.admitted
        other_class = make_dataclass("OtherAdmission", [(field.name, object) for field in fields(original)], frozen=True)
        other = other_class(*(getattr(original, field.name) for field in fields(original)))
        with self.assertRaisesRegex(ValueError, "fresh strict source admission"):
            self.fixture.validate(admitted=other)
        reference = self.fixture.validate()
        with self.assertRaisesRegex(ValueError, "execution admission differs"):
            reference.assert_admission(other, self.fixture.build)

    def test_D_binds_both_units_linker_flags_and_original_absolute_layout(self):
        builder = load("target_unit_D_profile_flag_checks", TARGET.ROOT / "engines/experiments/tiny-d-submission/build.py")
        for profile_id in ("test-p4", "test-p28"):
            with self.subTest(profile=profile_id), \
                    tempfile.TemporaryDirectory(prefix="rove4k-D-target-reference-unit-") as temporary:
                fixture = Fixture(Path(temporary), family="D", profile_id=profile_id)
                reference = fixture.validate()
                record = reference.to_record()
                self.assertEqual(reference.family, "D")
                self.assertEqual(reference.profile, profile_id)
                self.assertEqual(record["units"], ["main.c", "start.S"])
                self.assertEqual(set(record["source_files"]), {"main.c", "start.S", "image.ld"})
                self.assertEqual(record["flags"], builder.native_flags(fixture.profile))
                self.assertEqual(record["source_build"]["path"], str(fixture.build))
                self.assertEqual(record["ci_context"], fixture.ci.to_record())
                self.assertIs(record["factory_replayed_on_target"], False)
                self.assertIs(record["runtime_executed"], False)
                self.assertEqual(fixture.admitted.resources["tt_bytes"],
                                 (512 if profile_id == "test-p28" else 128) * (1 << 20))
                row = fixture.report["profiles"][0]
                original_flags = list(row["flags"])
                other_profile = "test-p4" if profile_id == "test-p28" else "test-p28"
                row["flags"] = builder.native_flags(VERIFY.contracts().resource_profile(other_profile))
                fixture.save()
                with self.assertRaisesRegex(ValueError, "original source/profile/flags/whole manifest"):
                    fixture.validate()
                row["flags"] = original_flags
                row["per_unit_dependency_discovery"] = ["main.c"]
                fixture.save()
                with self.assertRaisesRegex(ValueError, "every frozen compilation unit"):
                    fixture.validate()
                row["per_unit_dependency_discovery"] = ["main.c", "start.S"]
                fixture.save()
                (fixture.directory / "source/image.ld").write_bytes(b"different linker input")
                with self.assertRaisesRegex(ValueError, "frozen source differs"):
                    fixture.validate()


if __name__ == "__main__":
    unittest.main()
