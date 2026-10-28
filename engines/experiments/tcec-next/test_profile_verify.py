"""Profile qualifier admission and host-budget boundaries; no engine required."""
from __future__ import annotations

import importlib.util
import json
import lzma
import os
from pathlib import Path
import stat
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


def compound_gate_fixture(build, family="A", profile="test-p4", *, v2=False):
    source, native = b"int main(void){return 0;}\n", b"actual independently compiled image"
    assertions = ["_Static_assert(sizeof(int)==4,\"integer\");"]
    asserted = source + b"\n" + ("\n".join(assertions) + "\n").encode()
    compiler = list(VERIFY.F_COMPOUND_COMPILER)
    declaration = VERIFY.F_COMPOUND_DECLARATION if v2 else VERIFY.COMPOUND_DECLARATION
    kind = VERIFY.F_COMPOUND_V2_POLICY if v2 else VERIFY.F_COMPOUND_POLICY
    manifest = {"family": family, "post_spelling": dict(declaration), "compiler": compiler,
                "compile_executor": compiler[:], "compile_executor_version": VERIFY.F_COMPOUND_COMPILER_VERSION,
                "attempts": [], "commands": []}
    original = "/original/compound-artifact"
    def add(kind, data, suffix, output=b""):
        index = len(manifest["commands"]) + 1
        row = {"kind": kind, "command": ["cc", "--version"] if kind == "target-compiler-version" else compiler[:],
               "cwd": original + suffix, "started": True, "returncode": 0, "terminal": True, "reaped": True,
               "owned_group_absent": True, "original_identity_retained_until_other_members_absent": True,
               "forced_cleanup": False, "other_group_members_before_reap": [], "pid": index + 100, "pgid": index + 100}
        for stream, value in (("stdout", output), ("stderr", b"")):
            name = "tool-" + str(index) + "-" + kind + "." + stream
            (build / name).write_bytes(value)
            row[stream] = {"path": original + "/" + name, **VERIFY.pin(value)}
        if data is not None:
            (build / ("tool-" + str(index) + "-" + kind + ".stdin")).write_bytes(data)
        manifest["commands"].append(row)
    if family == "F":
        manifest["native_policy"] = {"kind": kind, "family": "F", "profile_id": profile,
            "post_spelling": dict(declaration), "compiler": compiler[:],
            "compiler_version": VERIFY.F_COMPOUND_COMPILER_VERSION, "source": VERIFY.pin(source), "native": VERIFY.pin(native)}
        add("target-compiler-version", None, "", (VERIFY.F_COMPOUND_COMPILER_VERSION + "\nmore compiler details\n").encode())
    for directory in ("first", "repeat"):
        gate = {"assertions": assertions[:], "source": VERIFY.pin(asserted), "native": VERIFY.pin(native), "image_identical": True}
        if family == "F": gate.update(directory="target-type-gate", source_file="asserted.c", policy=kind)
        manifest["attempts"].append({"directory": directory, "target_type_gate": gate})
        for name, data in (("target-type-gate/asserted.c", asserted), ("target-type-gate/x", native), ("native/x", native)):
            path = build / directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        add(directory + "-target-types", asserted, "/" + directory + "/target-type-gate")
        add(directory + "-compile", source, "/" + directory + "/native")
    return manifest, source, native, {"target_type_assertions": assertions}


class ProfileRuntimeAdmission(unittest.TestCase):
    def test_profile_proof_inventory_requires_every_frozen_support(self):
        from copy import deepcopy
        production = {"engines/scripts/production.py"}
        inputs = {name: {"bytes": 9, "sha256": digest} for name, digest in VERIFY.SUPPORT.items()}
        inputs.update({name: VERIFY.pin(name.encode()) for name in
                       ("engines/scripts/verify_shell.py", "engines/experiments/tcec-next/profile_verify.py")})
        inputs["engines/scripts/production.py"] = VERIFY.pin(b"producer")
        proof = {name: value for name, value in inputs.items() if name not in production}
        manifest = {"family": "A", "plan": {"representation": "source-jit"},
                    "inputs": inputs, "proof_inputs": proof}
        VERIFY.require_profile_proof_closure(manifest, production)
        for helper in VERIFY.SUPPORT:
            with self.subTest(missing=helper):
                changed = deepcopy(manifest)
                # Remove both declaration and pin: set equality alone cannot
                # prove the producer's required helper inventory is complete.
                del changed["inputs"][helper]
                del changed["proof_inputs"][helper]
                with self.assertRaisesRegex(ValueError, "mandatory profile proof helper"):
                    VERIFY.require_profile_proof_closure(changed, production)
            with self.subTest(drift=helper):
                changed = deepcopy(manifest)
                changed["inputs"][helper]["sha256"] = "0" * 63
                changed["proof_inputs"][helper]["sha256"] = "0" * 63
                with self.assertRaisesRegex(ValueError, "mandatory profile proof helper"):
                    VERIFY.require_profile_proof_closure(changed, production)
        changed = deepcopy(manifest)
        changed["proof_inputs"].pop(next(iter(VERIFY.SUPPORT)))
        with self.assertRaisesRegex(ValueError, "proof inventory"):
            VERIFY.require_profile_proof_closure(changed, production)
        changed = deepcopy(manifest)
        changed["proof_inputs"]["engines/scripts/extra.py"] = VERIFY.pin(b"extra")
        with self.assertRaisesRegex(ValueError, "proof inventory"):
            VERIFY.require_profile_proof_closure(changed, production)
        for family, extra in (("A", ()), ("F", ("engines/compact/tiny-entry-f/verify.py", "engines/tests/verify.py"))):
            complete = deepcopy(manifest)
            complete["family"] = family
            for name in extra:
                complete["inputs"][name] = VERIFY.pin(name.encode())
                complete["proof_inputs"][name] = VERIFY.pin(name.encode())
            VERIFY.require_profile_proof_closure(complete, production)
            required = ("engines/scripts/verify_shell.py", *extra)
            for name in required:
                with self.subTest(family=family, missing=name):
                    changed = deepcopy(complete)
                    del changed["inputs"][name]
                    del changed["proof_inputs"][name]
                    with self.assertRaisesRegex(ValueError, "mandatory profile proof helper"):
                        VERIFY.require_profile_proof_closure(changed, production)
        # Early producer versions added the verifier only when present; a
        # frozen receipt is not rebound to the current verifier's bytes.
        historical = deepcopy(manifest)
        optional = "engines/experiments/tcec-next/profile_verify.py"
        del historical["inputs"][optional]
        del historical["proof_inputs"][optional]
        for helper in VERIFY.SUPPORT:
            historical["inputs"][helper]["sha256"] = "1" * 64
            historical["proof_inputs"][helper]["sha256"] = "1" * 64
        VERIFY.require_profile_proof_closure(historical, production)

    def test_control_frozen_inputs_must_match_the_profile(self):
        from copy import deepcopy
        control_inputs = {name: {"bytes": 9, "sha256": digest} for name, digest in VERIFY.SUPPORT.items()}
        control_closure = {"engines/scripts/production.py": VERIFY.pin(b"producer")}
        manifest = {"inputs": {**control_inputs, **control_closure},
                    "control_source_closure": deepcopy(control_closure)}
        control = {"inputs": deepcopy(control_inputs), "control_source_closure": deepcopy(control_closure)}
        VERIFY.require_profile_control_closure(manifest, control)
        for kind in ("missing", "changed", "closure"):
            with self.subTest(kind=kind):
                changed = deepcopy(manifest)
                key = next(iter(VERIFY.SUPPORT))
                if kind == "missing":
                    del changed["inputs"][key]
                elif kind == "changed":
                    changed["inputs"][key]["bytes"] += 1
                else:
                    changed["control_source_closure"]["engines/scripts/production.py"]["bytes"] += 1
                with self.assertRaisesRegex(ValueError, "maintained control"):
                    VERIFY.require_profile_control_closure(changed, control)

    def test_actual_admission_rejects_a_removed_proof_pin_before_input_reads(self):
        source, native, header, payload = b"source", b"native", b"header", b"payload"
        content = {"main.c": source, "native/x": native, "header.sh": header,
                   "payload.lzma": payload, "x": header + payload}
        expected = {prefix + "_" + key: value
                    for prefix, raw in (("source", source), ("native", native),
                                        ("header", header), ("payload", payload),
                                        ("whole", header + payload))
                    for key, value in VERIFY.pin(raw).items()}
        proof = {name: {"bytes": 9, "sha256": digest} for name, digest in VERIFY.SUPPORT.items()}
        proof.update({name: VERIFY.pin(name.encode()) for name in
                      ("engines/scripts/verify_shell.py", "engines/experiments/tcec-next/profile_verify.py")})
        removed = next(name for name in proof if "tiny-entry-d" in name)
        del proof[removed]
        production = "engines/scripts/production.py"
        source_proofs = []
        row = {"path": production, "role": "tool", **VERIFY.pin(b"producer")}
        attempts = [{"directory": name, **expected, "source_proofs": source_proofs,
                     "target_type_gate": {"image_identical": True}} for name in ("first", "repeat")]
        plan = {"representation": "source-jit", "entry_cleanup": "none"}
        manifest = {"format": 1, "class": VERIFY.CLASS, "complete": True, "reproducible": True,
                    "family": "A", "entry": "A", "resources": {}, "plan": plan,
                    "actual": {"source": "main.c", "native": "native/x", "program": "x"},
                    "expected_contract": expected, "attempts": attempts, "source_proofs": source_proofs,
                    "inputs": {production: VERIFY.pin(b"producer"), **proof}, "proof_inputs": proof,
                    "source_closure": {"family": "A", "admission": "expected-pins-verified", "inputs": [row]}}
        api = types.SimpleNamespace(ArtifactPlan=lambda *_args, **_kwargs: types.SimpleNamespace(to_record=lambda: plan),
                                    SourceClosure=types.SimpleNamespace(validate=lambda *_args, **_kwargs: None))
        reads = []
        def checked(_build, name, _expected):
            reads.append(name)
            key = name.split("/", 1)[1] if name.startswith(("first/", "repeat/")) else name
            return content[key]
        with patch.object(VERIFY, "validate_spelling_request"), \
                patch.object(VERIFY, "_resource_record", return_value=(object(), object())), \
                patch.object(VERIFY, "contracts", return_value=api), \
                patch.object(VERIFY, "_check_command_set"), \
                patch.object(VERIFY, "checked_artifact", side_effect=checked):
            with self.assertRaisesRegex(ValueError, "mandatory profile proof helper"):
                VERIFY.admit_c_build(manifest, Path("synthetic-not-read"))
        self.assertFalse(any(name.startswith("inputs/") for name in reads))

    def test_shared_profiles_cannot_enter_legacy_runtime_launcher(self):
        from dataclasses import replace
        for profile in ("test-p16", "test-p192"):
            with self.subTest(profile=profile), \
                    patch.object(VERIFY, "support_modules", side_effect=AssertionError("support loaded")), \
                    self.assertRaisesRegex(ValueError, "verified cohort resource owner"):
                VERIFY.run_runtime(replace(admitted(), profile_id=profile), Path("unused"), Path("unused"), {})

        # Legacy runtime launch reaches its pre-existing path; the guard is
        # specific to the new shared profiles, not a change to P4/P28/W256.
        for profile in ("test-p4", "test-p28", "tcec-provisional"):
            with self.subTest(profile=profile), \
                    patch.object(VERIFY, "support_modules", side_effect=LookupError("legacy reached")), \
                    self.assertRaisesRegex(LookupError, "legacy reached"):
                VERIFY.run_runtime(replace(admitted(), profile_id=profile), Path("unused"), Path("unused"), {})

    def test_shared_cli_guard_precedes_resource_target_and_process_work(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory(prefix="rove4k-shared-runtime-guard-") as temporary:
            base = Path(temporary).resolve()
            build = base / "source"
            build.mkdir()
            (build / "build.json").write_text("{}")
            for profile in ("test-p16", "test-p192"):
                out = base / ("out-" + profile)
                args = ["profile_verify.py", "--build", str(build), "--out", str(out),
                        "--target-compiler-receipt", str(base / "compiler.json"),
                        "--source-bundle", str(base / "bundle.zip"),
                        "--source-seal", str(base / "seal.json")]
                selected = replace(admitted(), profile_id=profile)
                with self.subTest(profile=profile), \
                        patch.object(VERIFY.sys, "argv", args), \
                        patch.object(VERIFY.sys, "platform", "linux"), \
                        patch.object(VERIFY, "resource", object()), \
                        patch.object(VERIFY, "admit_c_build", return_value=selected), \
                        patch.object(VERIFY, "target_module", side_effect=AssertionError("target subprocess")), \
                        patch.object(VERIFY, "effective_available_bytes", side_effect=AssertionError("memory scan")), \
                        patch.object(VERIFY, "execution_limits", side_effect=AssertionError("limits")), \
                        patch.object(VERIFY, "run_runtime", side_effect=AssertionError("launch")), \
                        self.assertRaisesRegex(ValueError, "verified cohort resource owner"):
                    VERIFY.main()
                self.assertFalse(out.exists())

    def test_shared_cli_still_allows_read_only_receipt_revalidation(self):
        from contextlib import redirect_stdout
        from dataclasses import replace
        from io import StringIO
        with tempfile.TemporaryDirectory(prefix="rove4k-shared-runtime-read-") as temporary:
            base = Path(temporary).resolve()
            build = base / "source"
            build.mkdir()
            (build / "build.json").write_text("{}")
            for profile in ("test-p16", "test-p192"):
                out = base / ("out-" + profile)
                runtime = base / "runtime.json"
                args = ["profile_verify.py", "--build", str(build), "--out", str(out),
                        "--runtime", str(runtime)]
                selected = replace(admitted(), profile_id=profile)
                qualification = {"complete": False, "functional_runtime_complete": True, "failures": []}
                with self.subTest(profile=profile), \
                        patch.object(VERIFY.sys, "argv", args), \
                        patch.object(VERIFY.sys, "platform", "linux"), \
                        patch.object(VERIFY, "resource", object()), \
                        patch.object(VERIFY, "admit_c_build", return_value=selected), \
                        patch.object(VERIFY, "qualification_record", return_value=qualification) as revalidate, \
                        patch.object(VERIFY, "run_runtime", side_effect=AssertionError("launch")), \
                        redirect_stdout(StringIO()):
                    VERIFY.main()
                revalidate.assert_called_once()
                self.assertEqual(json.loads((out / "qualification.json").read_text()), qualification)

    def test_anonymous_cleanup_requires_typed_self_contained_elf_contract(self):
        from dataclasses import replace
        marker = VERIFY.AnonymousMemfdContract()
        selected = replace(admitted(), representation="self-contained-elf", wrapper_contract=marker)
        expected = {"entry_cleanup": "none", "temp_strategy": "anonymous-memfd",
                    "cleanup_seconds": 0, "parent_removed": False}
        self.assertEqual(VERIFY._runtime_wrapper(selected), expected)
        for changed in (replace(selected, wrapper_contract=expected),
                        replace(selected, representation="source-jit"),
                        replace(selected, wrapper_contract={**expected, "temp_strategy": "private-path"})):
            with self.subTest(contract=changed.wrapper_contract), self.assertRaises(ValueError):
                VERIFY._runtime_wrapper(changed)
        self.assertTrue(VERIFY.runtime_feature_required(PATH.read_bytes(),
                        "ELF_ENTRY_CLEANUP", "anonymous-memfd-v1"))
        self.assertFalse(VERIFY.runtime_feature_required(b'CLASS="historical"\n',
                         "ELF_ENTRY_CLEANUP", "anonymous-memfd-v1"))

    def test_anonymous_cleanup_validates_native_memfd_and_preserved_outer_meaning(self):
        from dataclasses import replace
        whole, native = VERIFY.pin(b"submitted outer ELF"), VERIFY.pin(b"restored native")
        selected = replace(admitted(), representation="self-contained-elf",
            wrapper_contract=VERIFY.AnonymousMemfdContract(),
            expected={"whole_" + key: value for key, value in whole.items()})
        stamp = {"device": 1, "inode": 27, "mode": stat.S_IFREG | 0o700, "links": 1,
                 "bytes": whole["bytes"], "mtime_ns": 12, "ctime_ns": 13}
        outer = {"program": "x", "whole": whole, "stat": stamp}
        link = "/memfd:rove4k (deleted)"
        snapshot = {"exe": link, "path": "/memfd:rove4k", "path_exists": False,
                    "native_sha256": native["sha256"]}
        identity = {"pid": 77, "start_ticks": 123, "state": "S"}
        executable = {"exe": link, "path": snapshot["path"], "native": native,
            "stat": {**stamp, "inode": 28, "links": 0, "bytes": native["bytes"]},
            "before": identity, "after": dict(identity)}
        cleanup = {"entry_cleanup": "none", "temp_strategy": "anonymous-memfd",
                   "observed_while_alive": True, "wall_from_launch": .5,
                   "executable": executable, "submitted_file": outer}
        VERIFY._validate_anonymous_cleanup(cleanup, snapshot, selected, outer, native, 77)
        for defect in ("disk-path", "linked-image", "wrong-native", "different-process",
                       "outer-replaced", "outer-missing", "path-absent-claim"):
            altered = json.loads(json.dumps(cleanup))
            if defect == "disk-path": altered["executable"]["exe"] = "/tmp/x (deleted)"
            elif defect == "linked-image": altered["executable"]["stat"]["links"] = 1
            elif defect == "wrong-native": altered["executable"]["native"]["sha256"] = "0" * 64
            elif defect == "different-process": altered["executable"]["after"]["start_ticks"] += 1
            elif defect == "outer-replaced": altered["submitted_file"]["stat"]["inode"] += 1
            elif defect == "outer-missing": altered["submitted_file"]["stat"]["links"] = 0
            else: altered["path_absent"] = True
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                VERIFY._validate_anonymous_cleanup(altered, snapshot, selected, outer, native, 77)

    def test_anonymous_receipt_cannot_inherit_historical_frozen_cleanup_semantics(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory(prefix="rove4k-elf-historical-receipt-") as temporary:
            root, native = Path(temporary), VERIFY.pin(b"native")
            selected = replace(admitted(), representation="self-contained-elf",
                wrapper_contract=VERIFY.AnonymousMemfdContract(),
                expected={"native_" + key: value for key, value in native.items()})
            (root / "build.json").write_bytes(b"{}")
            own = "engines/experiments/tcec-next/profile_verify.py"
            historical = b'CLASS="historical"\n'
            frozen = root / "inputs" / own
            frozen.parent.mkdir(parents=True)
            frozen.write_bytes(historical)
            record = {"format": "rove4k-profile-runtime-v1", "complete": True,
                "owned_remaining": 0, "final_owned_cleanup": [], "family": selected.family,
                "profile": selected.profile_id, "representation": selected.representation,
                "build_sha256": VERIFY.pin(b"{}")["sha256"], "expected_contract": selected.expected,
                "source_closure": selected.input_pins, "resources": selected.resources,
                "runtime_support": {own: VERIFY.pin(historical)["sha256"]},
                "wrapper_contract": selected.wrapper_contract.to_record()}
            receipt = root / "runtime.json"
            receipt.write_text(json.dumps(record))
            with (patch.object(VERIFY, "SUPPORT", {}),
                  patch.object(VERIFY, "runtime_image", return_value=(native, b"native")),
                  self.assertRaisesRegex(ValueError, "frozen runtime qualifier")):
                VERIFY.qualification_record(selected, root, receipt)

    def test_submitted_elf_is_bounded_and_cannot_be_deleted_replaced_or_modified(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory(prefix="rove4k-preserved-elf-") as temporary:
            root, data = Path(temporary), b"original submitted outer ELF"
            path = root / "x"
            path.write_bytes(data)
            selected = replace(admitted(), representation="self-contained-elf",
                wrapper_contract=VERIFY.AnonymousMemfdContract(),
                expected={"whole_" + key: value for key, value in VERIFY.pin(data).items()})
            reads = []
            def read(path, *, limit):
                reads.append((path, limit))
                return path.read_bytes()
            with patch.object(VERIFY, "input_reader", return_value=types.SimpleNamespace(read_regular=read)):
                original = VERIFY._submitted_file(selected, root)
                self.assertEqual(VERIFY._submitted_file(selected, root, original), original)
                self.assertTrue(all(item == (path, len(data)) for item in reads))
                replacement = root / "replacement"
                replacement.write_bytes(data)
                replacement.replace(path)
                with self.assertRaisesRegex(ValueError, "replaced or changed"):
                    VERIFY._submitted_file(selected, root, original)
                original = VERIFY._submitted_file(selected, root)
                path.write_bytes(b"wrong same extent contents!!")
                with self.assertRaisesRegex(ValueError, "whole-file observation"):
                    VERIFY._submitted_file(selected, root, original)
                path.unlink()
                with self.assertRaises((ValueError, FileNotFoundError)):
                    VERIFY._submitted_file(selected, root, original)

    def test_anonymous_image_reads_actual_bounded_fd_bytes(self):
        native = b"actual anonymous image bytes"
        expected, link = VERIFY.pin(native), "/memfd:rove4k (deleted)"
        snapshot = {"exe": link, "path": "/memfd:rove4k", "path_exists": False,
                    "native_sha256": expected["sha256"]}
        stamp = types.SimpleNamespace(st_dev=1, st_ino=28, st_mode=stat.S_IFREG | 0o700,
            st_nlink=0, st_size=len(native), st_mtime_ns=12, st_ctime_ns=13)
        identity = {"pid": 77, "start_ticks": 123, "state": "S"}
        for actual in (native, b"x" * len(native)):
            with (patch.object(VERIFY, "_proc_bytes", return_value=b"bounded stat"),
                  patch.object(VERIFY, "_process_identity", return_value=dict(identity)),
                  patch.object(Path, "readlink", return_value=Path(link)),
                  patch.object(Path, "stat", return_value=stamp),
                  patch.object(VERIFY.os, "open", return_value=42) as opened,
                  patch.object(VERIFY.os, "read", side_effect=[actual, b""]) as read,
                  patch.object(VERIFY.os, "fstat", return_value=stamp),
                  patch.object(VERIFY.os, "close") as closed):
                if actual == native:
                    observed = VERIFY._anonymous_image(77, snapshot, expected)
                    self.assertEqual(observed["native"], expected)
                else:
                    with self.assertRaisesRegex(ValueError, "actual anonymous native"):
                        VERIFY._anonymous_image(77, snapshot, expected)
                self.assertEqual(opened.call_args.args[0], Path("/proc/77/exe"))
                read.assert_any_call(42, len(native) + 1)
                closed.assert_called_once_with(42)

    def test_private_path_and_loader_owned_fd_keep_their_cleanup_contracts(self):
        contract = {"entry_cleanup": "private-path", "temp_strategy": "private-directory"}
        result = {"path_absent": True}
        scope = types.SimpleNamespace(normal_cleanup=lambda *arguments: result)
        owned = types.SimpleNamespace(process=types.SimpleNamespace(pid=77), exited=lambda: False)
        self.assertIs(VERIFY._clean_live(scope, owned, {}, contract, 0), result)
        snapshot = {"exe": "/memfd:historical (deleted)", "path": "/memfd:historical"}
        with patch.object(Path, "stat", return_value=types.SimpleNamespace(st_nlink=0)):
            old = VERIFY._clean_live(scope, owned, snapshot, {"entry_cleanup": "loader-owned-fd"}, 0)
        self.assertTrue(old["path_absent"])
        self.assertEqual(old["entry_cleanup"], "loader-owned-fd")

    def test_scan_stage_requires_exact_AC_compound_then_dependency(self):
        resource={"schema":"rove4k.c-resource-projection.v1"}
        phase={"schema":"rove4k.portable-phase-source.v1"}
        compound={"schema":VERIFY.COMPOUND_SCHEMA}
        scan={"schema":VERIFY.SCAN_SCHEMA}
        dependency={"schema":"rove4k.profile-dependencies.v1"}
        post={"path":"engines/experiments/tcec-next/profile_phase.py","variant":"phase-init"}
        options=dict(post_spelling=VERIFY.COMPOUND_DECLARATION,post_scan=VERIFY.SCAN_DECLARATION,
            source_dependencies={"path":"engines/experiments/tcec-next/profile_dependencies.py","variant":"unused-includes"},
            representation="source-jit",entry_cleanup="private-path")
        stages=[resource,phase,compound,scan,dependency]
        for family in "AC":
            self.assertEqual(VERIFY.source_stages(family,post,stages,**options),"phase")
        for family,proofs,changes in (("F",stages,{}),("A",stages[:-1],{}),
            ("A",[resource,phase,scan,compound,dependency],{}),("C",stages+[scan],{}),
            ("A",stages,{"post_scan":{**VERIFY.SCAN_DECLARATION,"extra":True}}),
            ("A",stages,{"source_dependencies":None}),("A",stages,{"entry_cleanup":"none"})):
            with self.assertRaises(ValueError):
                VERIFY.source_stages(family,post,proofs,**{**options,**changes})

    def test_scan_helper_requires_exact_current_frozen_tool_and_full_inverse_order(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-scan-helper-") as temporary:
            root=Path(temporary)
            target=root/"inputs"/VERIFY.SCAN;target.parent.mkdir(parents=True)
            data=(VERIFY.ROOT/VERIFY.SCAN).read_bytes().replace(b"\r\n",b"\n");target.write_bytes(data)
            row={"path":VERIFY.SCAN,"role":"tool",**VERIFY.SCAN_PIN}
            manifest={"source_closure":{"inputs":[row]},"inputs":{VERIFY.SCAN:VERIFY.SCAN_PIN}}
            self.assertEqual(VERIFY.scan_module(manifest,root,{VERIFY.SCAN}).SCHEMA,VERIFY.SCAN_SCHEMA)
            for rows in ([],[row,row],[{**row,"role":"engine"}]):
                with self.assertRaises(ValueError):
                    VERIFY.scan_module({**manifest,"source_closure":{"inputs":rows}},root,{VERIFY.SCAN})
            target.write_bytes(data+b"#wrong\n")
            with self.assertRaises(ValueError):VERIFY.scan_module(manifest,root,{VERIFY.SCAN})
        calls=[]
        def stage(name,parent):
            def restore(actual,proof):
                self.assertEqual(actual,parent+name.encode());calls.append(name);return parent
            return types.SimpleNamespace(restore_source=restore)
        stages=[];body=b"base"
        for name in ("resource","phase","compound","scan","dependency"):
            stages.append((stage(name,body),{},body));body+=name.encode()
        self.assertEqual(VERIFY.inverse_source_stages(body,stages),b"base")
        self.assertEqual(calls,["dependency","scan","compound","phase","resource"])

    def test_scan_native_policy_is_finite_and_real_banner_bound(self):
        self.assertEqual(len(VERIFY.SCAN_IMAGES),6)
        for (family,profile),row in VERIFY.SCAN_IMAGES.items():
            compiler=["cc","-Os",*(["-mavx2"] if family=="C" else []),"-x","c","-","-o","x","-s"]
            source,native=b"admitted-fixture-source",b"x"*18568
            identities=(len(source),VERIFY.pin(source)["sha256"],VERIFY.pin(native)["sha256"])
            policy=dict(kind="AC-square-successor-gcc13-v1",family=family,profile_id=profile,
                post_scan=VERIFY.SCAN_DECLARATION,compiler=compiler,compiler_version=VERIFY.SCAN_COMPILER_VERSION,
                source=VERIFY.pin(source),native=VERIFY.pin(native))
            manifest=dict(family=family,post_scan=VERIFY.SCAN_DECLARATION,scan_native_policy=policy,
                compiler=compiler,compile_executor=compiler[:],compile_executor_version=VERIFY.SCAN_COMPILER_VERSION)
            with patch.dict(VERIFY.SCAN_IMAGES,{(family,profile):identities}), \
                 patch.object(VERIFY,"_compound_owned_command",return_value=({}, {"stdout":(VERIFY.SCAN_COMPILER_VERSION+"\n").encode()})):
                self.assertEqual(VERIFY.scan_native_evidence(manifest,Path("unused"),source,native,profile)["policy"],policy)
            with patch.dict(VERIFY.SCAN_IMAGES,{(family,profile):identities}), \
                 patch.object(VERIFY,"_compound_owned_command",return_value=({}, {"stdout":b"wrong banner\n"})):
                with self.assertRaisesRegex(ValueError,"banner"):
                    VERIFY.scan_native_evidence(manifest,Path("unused"),source,native,profile)
            for changes in ({"compile_executor":["gcc-11",*compiler[1:]]},{"scan_native_policy":{}},
                            {"compile_executor_version":"wrong"},{"post_scan":{**VERIFY.SCAN_DECLARATION,"extra":0}}):
                with self.assertRaises(ValueError):
                    VERIFY.scan_native_evidence({**manifest,**changes},Path("unused"),source,native,profile)
        with self.assertRaises(ValueError):
            VERIFY.scan_native_evidence({"scan_native_policy":{}},Path("unused"),b"",b"","test-p4")

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
        self.assertEqual(VERIFY.source_stages("E", post, [resource, phase, model, spelling], post_spelling=selected, **options), "phase")
        b = {"path": "engines/experiments/tcec-next/profile_b.py", "variant": "tcec-final-lf"}
        self.assertEqual(VERIFY.source_stages("B", b,
            [resource, {"schema": "rove4k.profile-b-source.v1"}, spelling],
            post_spelling={**selected, "variant": "atomic-assignment"}, **options), "B")
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
                VERIFY.source_stages("E", declaration, proofs, post_spelling=final, **parameters)

    def test_b_league_atomic_stage_is_profile_and_dependency_specific(self):
        resource = {"schema": "rove4k.c-resource-projection.v1"}
        b = {"schema": "rove4k.profile-b-source.v1"}
        atomic = {"schema": VERIFY.B_LEAGUE_SPELLING_SCHEMA}
        dependencies = {"schema": "rove4k.profile-dependencies.v1"}
        post = {"path": "engines/experiments/tcec-next/profile_b.py", "variant": "tcec-final-lf"}
        options = {"post_spelling": dict(VERIFY.B_LEAGUE_SPELLING_DECLARATION),
                   "source_dependencies": {"path": "engines/experiments/tcec-next/profile_dependencies.py",
                                           "variant": "unused-includes"},
                   "representation": "source-jit", "entry_cleanup": "private-path"}
        stages = [resource, b, atomic, dependencies]
        for profile in ("test-p16", "test-p192"):
            self.assertEqual(VERIFY.source_stages("B", post, stages, profile_id=profile, **options), "B")
        for profile in (None, "test-p4", "test-p28", "tcec-provisional", "unknown"):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                VERIFY.source_stages("B", post, stages, profile_id=profile, **options)
        for family, selected, proofs, changed in (
            ("A", post, stages, {}),
            ("B", {**post, "variant": "other"}, stages, {}),
            ("B", post, [resource, atomic, b, dependencies], {}),
            ("B", post, stages[:-1], {"source_dependencies": None}),
            ("B", post, stages, {"representation": "packed-native"}),
            ("B", post, stages, {"entry_cleanup": "none"}),
            ("B", post, stages, {"post_spelling": {**VERIFY.B_LEAGUE_SPELLING_DECLARATION,
                                                    "variant": "other"}}),
        ):
            with self.subTest(family=family, changed=changed), self.assertRaises(ValueError):
                VERIFY.source_stages(family, selected, proofs, profile_id="test-p16", **{**options, **changed})

    def test_independent_league_candidate_stage_is_finite_and_ordered(self):
        resource = {"schema": "rove4k.c-resource-projection.v1"}
        model = {"stage": "canonical-e19-physical-binding"}
        for variant, (path, _, schema, families) in VERIFY.LEAGUE_VARIANTS.items():
            declaration = {"path": path, "variant": variant}
            for family in families:
                stages = [resource, *([model] if family == "E" else []), {"schema": schema}]
                for profile in ("test-p16", "test-p192"):
                    options = dict(post_league=declaration, profile_id=profile,
                                   representation="source-jit", entry_cleanup="private-path")
                    with self.subTest(variant=variant, family=family, profile=profile):
                        self.assertIsNone(VERIFY.source_stages(family, None, stages, **options))
                        for changed in ({"profile_id": "test-p4"}, {"representation": "packed-native"},
                                        {"entry_cleanup": "none"}, {"source_dependencies": {"path": "x"}},
                                        {"post_league": {**declaration, "path": "wrong"}}):
                            with self.assertRaises(ValueError):
                                VERIFY.source_stages(family, None, stages, **{**options, **changed})
                        with self.assertRaises(ValueError):
                            VERIFY.source_stages(family, None, stages + [{"schema": schema}], **options)
            for family in set("ABCEF") - set(families):
                with self.assertRaises(ValueError):
                    VERIFY.source_stages(family, None, [resource, {"schema": schema}],
                        post_league=declaration, profile_id="test-p16",
                        representation="source-jit", entry_cleanup="private-path")

    def test_league_candidate_requires_exact_frozen_helper_and_support_roles(self):
        from copy import deepcopy
        for variant, (path, identity, schema, _) in VERIFY.LEAGUE_VARIANTS.items():
            extras = ({VERIFY.SCAN: VERIFY.SCAN_PIN} if variant == "square-successor" else
                      {VERIFY.LEAGUE_EP_SUPPORT: VERIFY.LEAGUE_EP_SUPPORT_PIN,
                       VERIFY.COMPOUND: VERIFY.COMPOUND_PIN} if variant == "legal-maker" else {})
            if variant in VERIFY.LEAGUE_COMBINATIONS:
                for role, component in VERIFY.LEAGUE_COMBINATIONS[variant]:
                    component_path, component_pin, _, _ = VERIFY.LEAGUE_VARIANTS[component]
                    extras[component_path] = component_pin
                    if role == "square":
                        extras[VERIFY.SCAN] = VERIFY.SCAN_PIN
                    if role == "ep":
                        extras.update({VERIFY.LEAGUE_EP_SUPPORT: VERIFY.LEAGUE_EP_SUPPORT_PIN,
                                       VERIFY.COMPOUND: VERIFY.COMPOUND_PIN})
            identities = {path: identity, **extras}
            manifest = {"inputs": deepcopy(identities), "source_closure": {"inputs": [
                {"path": name, "role": "tool", **pin} for name, pin in identities.items()]}}
            with tempfile.TemporaryDirectory(prefix="rove4k-league-helper-") as temporary:
                build = Path(temporary)
                for name in identities:
                    frozen = build / "inputs" / name
                    frozen.parent.mkdir(parents=True, exist_ok=True)
                    frozen.write_bytes((VERIFY.ROOT / name).read_bytes().replace(b"\r\n", b"\n"))
                declaration = {"path": path, "variant": variant}
                helper, binding = VERIFY.league_candidate_module(manifest, build, set(identities), declaration)
                self.assertEqual(helper.SCHEMA, schema)
                expected = ({"ep", "projection"} if variant == "legal-maker" else
                            {"helpers"} if variant in VERIFY.LEAGUE_COMBINATIONS else set())
                self.assertEqual(set(binding), expected)
                if variant in VERIFY.LEAGUE_COMBINATIONS:
                    component_roles = {role for role, _ in VERIFY.LEAGUE_COMBINATIONS[variant]}
                    self.assertEqual(set(binding["helpers"]), component_roles |
                                     ({"ep_owner", "projection"} if "ep" in component_roles else set()))
                for name in identities:
                    altered = deepcopy(manifest)
                    row = next(row for row in altered["source_closure"]["inputs"] if row["path"] == name)
                    row["role"] = "engine"
                    with self.subTest(variant=variant, bad=name), self.assertRaises(ValueError):
                        VERIFY.league_candidate_module(altered, build, set(identities), declaration)

    def test_combined_inverse_rejects_unhashable_variant(self):
        module = types.SimpleNamespace(SCHEMA="rove4k.league-combined-source.v1")
        proof = {"schema": module.SCHEMA, "variant": []}
        with self.assertRaises(ValueError):
            VERIFY.inverse_source_stages(b"candidate", [(module, proof, b"source", {"helpers": {}})])

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

    def test_b_league_atomic_helper_requires_exact_pin_and_tool_role(self):
        from copy import deepcopy
        path, identity = VERIFY.B_LEAGUE_SPELLING, VERIFY.B_LEAGUE_SPELLING_PIN
        row = {"path": path, "role": "tool", **identity}
        manifest = {"inputs": {path: dict(identity)}, "source_closure": {"inputs": [row]}}
        with tempfile.TemporaryDirectory(prefix="rove4k-b-league-spelling-") as temporary:
            build = Path(temporary)
            frozen = build / "inputs" / path
            frozen.parent.mkdir(parents=True)
            source = (VERIFY.ROOT / path).read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(VERIFY.pin(source), identity)
            frozen.write_bytes(source)
            helper = VERIFY.b_league_spelling_module(manifest, build, {path})
            self.assertEqual(helper.SCHEMA, VERIFY.B_LEAGUE_SPELLING_SCHEMA)
            for kind in ("role", "pin", "input", "duplicate", "missing"):
                altered = deepcopy(manifest)
                if kind == "role":
                    altered["source_closure"]["inputs"][0]["role"] = "engine"
                elif kind == "pin":
                    altered["source_closure"]["inputs"][0]["sha256"] = "0" * 64
                elif kind == "input":
                    altered["inputs"][path]["bytes"] += 1
                elif kind == "duplicate":
                    altered["source_closure"]["inputs"].append(dict(row))
                else:
                    altered["source_closure"]["inputs"] = []
                with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "helper production role"):
                    VERIFY.b_league_spelling_module(altered, build, {path})
            frozen.write_bytes(source + b"\n")
            with self.assertRaises(ValueError):
                VERIFY.b_league_spelling_module(manifest, build, {path})
        with self.assertRaisesRegex(ValueError, "named compound native policy"):
            VERIFY.compound_native_evidence({"family": "B", "post_spelling":
                                            VERIFY.B_LEAGUE_SPELLING_DECLARATION,
                                            "native_policy": {}}, Path("unread"), b"", b"", {}, "test-p16")

    def test_b_league_stage_uses_the_supplied_typed_proof_for_inverse(self):
        from copy import deepcopy
        expected = {"schema": VERIFY.B_LEAGUE_SPELLING_SCHEMA, "full_inverse": True,
                    "features_removed": False, "edits": [{"input_begin": 1}]}
        calls = []
        def transform(before, **options):
            self.assertEqual((before, options), (b"before", {"family": "B", "profile_id": "test-p16",
                                                               "variant": "atomic-assignment"}))
            return b"after", deepcopy(expected)
        def restore(candidate, supplied):
            calls.append((candidate, supplied))
            return b"before"
        helper = types.SimpleNamespace(transform_source=transform, restore_source=restore)
        supplied = deepcopy(expected)
        produced, saved = VERIFY.b_league_spelling_stage(helper, b"before", supplied, "test-p16",
                                                        "atomic-assignment")
        self.assertEqual(produced, b"after")
        self.assertIs(saved, supplied)
        self.assertIs(calls[0][1], supplied)
        for mutate in (lambda proof: proof.update(full_inverse=1),
                       lambda proof: proof.update(features_removed=0),
                       lambda proof: proof["edits"][0].update(input_begin=True)):
            forged = deepcopy(expected)
            mutate(forged)
            self.assertEqual(forged, expected)  # Python equality conflates bool and int.
            with self.assertRaisesRegex(ValueError, "atomic spelling proof differs"):
                VERIFY.b_league_spelling_stage(helper, b"before", forged, "test-p16", "atomic-assignment")
        self.assertEqual(len(calls), 1)

    def test_dependency_stage_is_explicit_and_last(self):
        resource = {"schema": "rove4k.c-resource-projection.v1"}
        model = {"stage": "canonical-e19-physical-binding"}
        dependency = {"schema": "rove4k.profile-dependencies.v1"}
        declaration = {"path": "engines/experiments/tcec-next/profile_dependencies.py",
                       "variant": "unused-includes"}
        self.assertIsNone(VERIFY.source_stages("E", None, [resource, model, dependency], source_dependencies=declaration))
        for stages, named in (([resource, dependency, model], declaration),
                              ([resource, model], declaration),
                              ([resource, model, dependency], None),
                              ([resource, model, dependency], {**declaration, "path": "other.py"})):
            with self.subTest(stages=stages, declaration=named), self.assertRaises(ValueError):
                VERIFY.source_stages("E", None, stages, source_dependencies=named)

    def test_compound_is_one_alternative_before_final_dependencies(self):
        resource = {"schema": "rove4k.c-resource-projection.v1"}
        phase = {"schema": "rove4k.portable-phase-source.v1"}
        model = {"stage": "canonical-e19-physical-binding"}
        compound = {"schema": VERIFY.COMPOUND_SCHEMA}
        individual = {"schema": VERIFY.SPELLING_SCHEMA}
        dependency = {"schema": "rove4k.profile-dependencies.v1"}
        post = {"path": "engines/experiments/tcec-next/profile_phase.py", "variant": "phase-init"}
        options = dict(post_spelling=dict(VERIFY.COMPOUND_DECLARATION),
            source_dependencies={"path": "engines/experiments/tcec-next/profile_dependencies.py", "variant": "unused-includes"},
            representation="source-jit", entry_cleanup="private-path")
        for family in "ACEF":
            proofs = [resource, phase, *([model] if family == "E" else []), compound, dependency]
            self.assertEqual(VERIFY.source_stages(family, post, proofs, **options), "phase")
            for invalid in (proofs[:-1], [*proofs[:-2], dependency, compound],
                            [*proofs[:-2], individual, compound, dependency], proofs + [compound]):
                with self.subTest(family=family, invalid=invalid), self.assertRaises(ValueError):
                    VERIFY.source_stages(family, post, invalid, **options)
        b = {"path": "engines/experiments/tcec-next/profile_b.py", "variant": "tcec-final-lf"}
        with self.assertRaises(ValueError):
            VERIFY.source_stages("B", b, [resource, {"schema": "rove4k.profile-b-source.v1"}, compound, dependency], **options)
        for key, value in (("path", VERIFY.SPELLING), ("variant", "launcher-short"), ("selection", "best")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                VERIFY.source_stages("A", post, [resource, phase, compound, dependency],
                    **{**options, "post_spelling": {**VERIFY.COMPOUND_DECLARATION, key: value}})

    def test_F_compound_v2_is_one_nested_stage_before_final_dependencies(self):
        resource = {"schema": "rove4k.c-resource-projection.v1"}
        phase = {"schema": "rove4k.portable-phase-source.v1"}
        compound = {"schema": VERIFY.F_COMPOUND_SCHEMA, "base": {"schema": VERIFY.COMPOUND_SCHEMA}}
        dependency = {"schema": "rove4k.profile-dependencies.v1"}
        post = {"path": "engines/experiments/tcec-next/profile_phase.py", "variant": "phase-init"}
        options = dict(post_spelling=dict(VERIFY.F_COMPOUND_DECLARATION), post_scan=None,
            source_dependencies={"path": "engines/experiments/tcec-next/profile_dependencies.py", "variant": "unused-includes"},
            representation="source-jit", entry_cleanup="private-path")
        stages = [resource, phase, compound, dependency]
        self.assertEqual(VERIFY.source_stages("F", post, stages, **options), "phase")
        for family, selected, proofs, changes in (
                ("A", post, stages, {}), ("B", post, stages, {}), ("C", post, stages, {}), ("E", post, stages, {}),
                ("F", None, [resource, compound, dependency], {}),
                ("F", post, stages, {"representation": "packed-native"}),
                ("F", post, stages, {"representation": "self-contained-elf"}),
                ("F", post, stages, {"entry_cleanup": "none"}),
                ("F", post, stages[:-1], {"source_dependencies": None}),
                ("F", post, stages, {"post_scan": dict(VERIFY.SCAN_DECLARATION)}),
                ("F", post, [resource, phase, {"schema": VERIFY.COMPOUND_SCHEMA}, dependency], {}),
                ("F", post, [resource, phase, dependency, compound], {}),
                ("F", post, [resource, phase, compound["base"], compound, dependency], {}),
                ("F", post, stages, {"post_spelling": {**VERIFY.F_COMPOUND_DECLARATION, "extra": True}})):
            with self.subTest(family=family, changes=changes, proofs=proofs), self.assertRaises(ValueError):
                VERIFY.source_stages(family, selected, proofs, **{**options, **changes})

    def test_F_compound_v2_builder_is_opt_in_and_keeps_v1_policies_separate(self):
        spec = importlib.util.spec_from_file_location("profile_F_v2_builder_test", PATH.with_name("profile_build.py"))
        builder = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = builder
        spec.loader.exec_module(builder)
        self.assertEqual(builder.spelling_selection("F", "source-jit", "control", "phase-init", "compound-v2"),
                         VERIFY.F_COMPOUND_DECLARATION)
        for family in "ABCE":
            with self.subTest(family=family), self.assertRaises(ValueError):
                builder.spelling_selection(family, "source-jit", "control", "phase-init", "compound-v2")
        for representation, b_variant, phase_variant in (("packed-native", "control", "phase-init"),
                ("self-contained-elf", "control", "phase-init"), ("source-jit", "control", "control"),
                ("source-jit", "tcec-final-lf", "phase-init")):
            with self.subTest(representation=representation, phase=phase_variant), self.assertRaises(ValueError):
                builder.spelling_selection("F", representation, b_variant, phase_variant, "compound-v2")
        self.assertIsNone(builder.scan_selection("F", "source-jit", "phase-init", builder.F_COMPOUND_DECLARATION,
                                                "unused-includes", "control"))
        for dependencies, scan in (("control", "control"), ("unused-includes", "square-successor")):
            with self.subTest(dependencies=dependencies, scan=scan), self.assertRaises(ValueError):
                builder.scan_selection("F", "source-jit", "phase-init", builder.F_COMPOUND_DECLARATION, dependencies, scan)
        defaults = builder.argument_parser().parse_args(["--entry", "F", "--profile", "test-p4", "--out", "unrun"])
        self.assertEqual((defaults.spelling_variant, defaults.scan_variant), ("control", "control"))
        self.assertEqual(builder.spelling_selection("F", "source-jit", "control", "phase-init", "compound"),
                         VERIFY.COMPOUND_DECLARATION)
        self.assertEqual(builder.COMPOUND_V1_HISTORICAL_PIN, VERIFY.COMPOUND_V1_HISTORICAL_PIN)
        self.assertEqual(builder.COMPOUND_PIN, VERIFY.COMPOUND_PIN)
        compiler = list(builder.F_COMPOUND_COMPILER)
        for profile, identity in VERIFY.F_COMPOUND_V2_IDENTITIES.items():
            size, source_sha, native_sha = builder.F_COMPOUND_V2_IMAGES[profile]
            self.assertEqual({"source": {"bytes": size, "sha256": source_sha},
                              "native": {"bytes": 18568, "sha256": native_sha}}, identity)
            old_size, old_sha, old_native = builder.F_COMPOUND_IMAGES[profile]
            self.assertEqual((old_size, old_sha, old_native),
                (VERIFY.F_COMPOUND_IDENTITIES[profile]["source"]["bytes"],
                 VERIFY.F_COMPOUND_IDENTITIES[profile]["source"]["sha256"], native_sha))
            self.assertNotEqual(source_sha, old_sha)
            self.assertEqual(size, old_size - 4)
            fixture = b"finite source fixture"
            fixture_pin = VERIFY.pin(fixture)
            with patch.dict(builder.F_COMPOUND_V2_IMAGES, {profile: (len(fixture), fixture_pin["sha256"], native_sha)}):
                policy = builder.compound_native_policy("F", profile, builder.F_COMPOUND_DECLARATION, fixture,
                                                       compiler, compiler, builder.F_COMPOUND_COMPILER_VERSION)
                self.assertEqual(policy["kind"], VERIFY.F_COMPOUND_V2_POLICY)
                self.assertEqual(policy["post_spelling"], VERIFY.F_COMPOUND_DECLARATION)
                with self.assertRaises(ValueError):
                    builder.compound_native_policy("F", profile, builder.COMPOUND_DECLARATION, fixture,
                                                   compiler, compiler, builder.F_COMPOUND_COMPILER_VERSION)
                for changed_compiler, changed_executor, changed_version in ((compiler, ["other-cc", *compiler[1:]],
                        builder.F_COMPOUND_COMPILER_VERSION), (["other-cc", *compiler[1:]], compiler,
                        builder.F_COMPOUND_COMPILER_VERSION), (compiler, compiler, "different compiler")):
                    with self.assertRaises(ValueError):
                        builder.compound_native_policy("F", profile, builder.F_COMPOUND_DECLARATION, fixture,
                                                       changed_compiler, changed_executor, changed_version)

    def test_compound_helper_requires_both_reviewed_tool_identities(self):
        from copy import deepcopy
        rows = [{"path": name, "role": "tool", **identity} for name, identity in
                ((VERIFY.SPELLING, VERIFY.SPELLING_PIN), (VERIFY.COMPOUND, VERIFY.COMPOUND_PIN))]
        manifest = {"inputs": {row["path"]: {key: row[key] for key in ("bytes", "sha256")} for row in rows},
                    "source_closure": {"inputs": rows}}
        paths = {VERIFY.SPELLING, VERIFY.COMPOUND}
        with tempfile.TemporaryDirectory(prefix="rove4k-compound-helper-") as temporary:
            build = Path(temporary)
            for name in paths:
                frozen = build / "inputs" / name
                frozen.parent.mkdir(parents=True, exist_ok=True)
                frozen.write_bytes((VERIFY.ROOT / name).read_bytes().replace(b"\r\n", b"\n"))
            compound, individual = VERIFY.compound_module(manifest, build, paths)
            self.assertEqual(compound.SCHEMA, VERIFY.COMPOUND_SCHEMA)
            self.assertEqual(individual.SCHEMA, VERIFY.SPELLING_SCHEMA)
            for name in paths:
                for kind in ("role", "pin", "input", "duplicate", "missing", "outside"):
                    altered = deepcopy(manifest)
                    row = next(row for row in altered["source_closure"]["inputs"] if row["path"] == name)
                    production = set(paths)
                    if kind == "role": row["role"] = "engine"
                    elif kind == "pin": row["sha256"] = "0" * 64
                    elif kind == "input": altered["inputs"][name]["bytes"] += 1
                    elif kind == "duplicate": altered["source_closure"]["inputs"].append(dict(row))
                    elif kind == "missing": altered["source_closure"]["inputs"].remove(row)
                    else: production.remove(name)
                    with self.subTest(name=name, kind=kind), self.assertRaises(ValueError):
                        VERIFY.compound_module(altered, build, production)
                frozen = build / "inputs" / name
                original = frozen.read_bytes()
                frozen.write_bytes(original + b"\n")
                with self.subTest(name=name, kind="frozen-tamper"), self.assertRaises(ValueError):
                    VERIFY.compound_module(manifest, build, paths)
                frozen.write_bytes(original)

    def test_compound_inverse_restores_dependencies_then_bound_helper_before_E19(self):
        calls = []
        individual = types.SimpleNamespace(SCHEMA=VERIFY.SPELLING_SCHEMA)
        def restore(data, proof, *, spelling):
            self.assertIs(spelling, individual)
            calls.append("compound")
            VERIFY.require(data.startswith(b"S"), "compound inverse span differs")
            return data[1:]
        compound = types.SimpleNamespace(SCHEMA=VERIFY.COMPOUND_SCHEMA, restore_source=restore)
        prior = types.SimpleNamespace(restore_source=lambda data, proof: calls.append(proof["name"]) or data[1:])
        dependency = types.SimpleNamespace(restore_source=lambda data, proof: calls.append("dependency") or data + b";")
        stages = [(prior, {"name": "resource"}, b"table=1;"),
            (prior, {"name": "phase"}, b"Rtable=1;"),
            (None, {"table_value_offset": 8, "before": "1", "after": "222"}, b"PRtable=1;"),
            (compound, {"schema": VERIFY.COMPOUND_SCHEMA}, b"PRtable=222;", {"spelling": individual}),
            (dependency, {}, b"SPRtable=222;")]
        self.assertEqual(VERIFY.inverse_source_stages(b"SPRtable=222", stages), b"table=1;")
        self.assertEqual(calls, ["dependency", "compound", "phase", "resource"])
        for binding in ({}, {"spelling": individual, "variant": "hidden"},
                        {"spelling": types.SimpleNamespace(SCHEMA="wrong")}):
            with self.subTest(binding=binding), self.assertRaises(ValueError):
                VERIFY.inverse_source_stages(b"SPRtable=222;", [(*stages[3][:3], binding)])

    def test_F_compound_v2_inverse_binds_current_helper_and_v1_base(self):
        calls = []
        individual = types.SimpleNamespace(SCHEMA=VERIFY.SPELLING_SCHEMA)
        proof = {"schema": VERIFY.F_COMPOUND_SCHEMA, "base": {"schema": VERIFY.COMPOUND_SCHEMA}}
        def restore(data, supplied, *, spelling):
            self.assertIs(supplied, proof)
            self.assertIs(spelling, individual)
            calls.extend(("parentheses", "base-v1"))
            return data[2:]
        helper = types.SimpleNamespace(SCHEMA=VERIFY.COMPOUND_SCHEMA, F_SCHEMA=VERIFY.F_COMPOUND_SCHEMA, restore_source=restore)
        dependency = types.SimpleNamespace(restore_source=lambda data, supplied: calls.append("dependency") or b"PS" + data)
        stages = [(helper, proof, b"resource-phase", {"spelling": individual}),
                  (dependency, {}, b"PSresource-phase")]
        self.assertEqual(VERIFY.inverse_source_stages(b"resource-phase", stages), b"resource-phase")
        self.assertEqual(calls, ["dependency", "parentheses", "base-v1"])
        for changed in (types.SimpleNamespace(SCHEMA=VERIFY.COMPOUND_SCHEMA, restore_source=restore),
                        types.SimpleNamespace(SCHEMA=VERIFY.COMPOUND_SCHEMA, F_SCHEMA="wrong", restore_source=restore)):
            with self.subTest(helper=changed), self.assertRaises(ValueError):
                VERIFY.inverse_source_stages(b"PSresource-phase", [(changed, proof, b"resource-phase", {"spelling": individual})])

    def test_compound_request_is_only_explicit_B_duplicate_best(self):
        from copy import deepcopy
        record = {"family": "B", "post_spelling": {"path": VERIFY.SPELLING, "selection": "best", "variant": "atomic-assignment"},
            "spelling_request": {"requested": "compound", "effective": "best", "duplicate_best": True, "new_candidate_count": 0}}
        VERIFY.validate_spelling_request(record)
        VERIFY.validate_spelling_request({"family": "E"})
        cases = []
        for key, value in (("requested", "best"), ("effective", "compound"), ("duplicate_best", 1),
                           ("new_candidate_count", False), ("extra", "unclassified")):
            altered = deepcopy(record); altered["spelling_request"][key] = value; cases.append(altered)
        cases.extend([{**record, "family": "E"}, {**record, "spelling_request": None},
                      {**record, "post_spelling": dict(VERIFY.COMPOUND_DECLARATION)},
                      {**record, "inputs": {VERIFY.COMPOUND: VERIFY.COMPOUND_PIN}},
                      {**record, "source_closure": {"inputs": [{"path": VERIFY.COMPOUND, "role": "tool"}]}},
                      {**record, "source_proofs": [{"schema": VERIFY.COMPOUND_SCHEMA}]}])
        for altered in cases:
            with self.subTest(altered=altered), self.assertRaises(ValueError):
                VERIFY.validate_spelling_request(altered)

    def test_compound_target_assertions_bind_actual_inputs_images_and_original_commands(self):
        from copy import deepcopy
        for defect in (None, "assertions", "marker-type", "asserted-file", "gate-native", "asserted-stdin", "shipping-stdin",
                       "missing", "duplicate", "forced", "not-reaped", "pid", "cwd", "pipe-path", "pipe-bytes"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(prefix="rove4k-compound-gate-") as temporary:
                build = Path(temporary)
                manifest, source, native, proof = compound_gate_fixture(build)
                row = manifest["commands"][0]
                if defect == "assertions": manifest["attempts"][0]["target_type_gate"]["assertions"] = ["not the resource assertions"]
                elif defect == "marker-type": manifest["attempts"][0]["target_type_gate"]["image_identical"] = 1
                elif defect == "asserted-file": (build / "first/target-type-gate/asserted.c").write_bytes(source)
                elif defect == "gate-native": (build / "first/target-type-gate/x").write_bytes(b"another native")
                elif defect == "asserted-stdin": (build / "tool-1-first-target-types.stdin").write_bytes(source)
                elif defect == "shipping-stdin": (build / "tool-2-first-compile.stdin").write_bytes(source + b"changed")
                elif defect == "missing": manifest["commands"].remove(row)
                elif defect == "duplicate": manifest["commands"].append(deepcopy(row))
                elif defect == "forced": row["forced_cleanup"] = True
                elif defect == "not-reaped": row["reaped"] = False
                elif defect == "pid": row["pgid"] += 1
                elif defect == "cwd": row["cwd"] = "/another/first/native"
                elif defect == "pipe-path": row["stdout"]["path"] = "/another/tool-1-first-target-types.stdout"
                elif defect == "pipe-bytes": (build / "tool-1-first-target-types.stderr").write_bytes(b"unrecorded warning")
                if defect is None:
                    evidence = VERIFY.compound_native_evidence(manifest, build, source, native, proof, "test-p4")
                    self.assertEqual(len(evidence["attempts"]), 2)
                    self.assertIsNone(evidence["native_policy"])
                    self.assertEqual(evidence["source"], VERIFY.pin(source))
                    self.assertEqual(evidence["attempts"][0]["asserted_command"]["stdin"]["sha256"],
                                     manifest["attempts"][0]["target_type_gate"]["source"]["sha256"])
                else:
                    with self.assertRaises(ValueError):
                        VERIFY.compound_native_evidence(manifest, build, source, native, proof, "test-p4")

    def test_F_compound_has_one_named_finite_compiler_policy_and_no_other_route_waiver(self):
        for profile in VERIFY.F_COMPOUND_IDENTITIES:
            for defect in (None, "missing", "name", "source", "native", "float", "alternate-compiler", "version", "banner", "gate-policy"):
                with self.subTest(profile=profile, defect=defect), tempfile.TemporaryDirectory(prefix="rove4k-F-compound-") as temporary:
                    build = Path(temporary)
                    manifest, source, native, proof = compound_gate_fixture(build, "F", profile)
                    fixture_identity = {"source": VERIFY.pin(source), "native": VERIFY.pin(native)}
                    if defect == "missing": del manifest["native_policy"]
                    elif defect == "name": manifest["native_policy"]["kind"] = "generic-waiver"
                    elif defect == "source": manifest["native_policy"]["source"]["sha256"] = "0" * 64
                    elif defect == "native": manifest["native_policy"]["native"]["sha256"] = "0" * 64
                    elif defect == "float": manifest["native_policy"]["native"]["bytes"] = float(len(native))
                    elif defect == "alternate-compiler": manifest["compile_executor"][0] = "/usr/bin/gcc-11"
                    elif defect == "version": manifest["compile_executor_version"] = "GCC 11.4"
                    elif defect == "banner":
                        row = manifest["commands"][0]
                        data = b"not the admitted compiler banner\n"
                        row["stdout"].update(VERIFY.pin(data))
                        (build / "tool-1-target-compiler-version.stdout").write_bytes(data)
                    elif defect == "gate-policy": manifest["attempts"][0]["target_type_gate"]["policy"] = "another-policy"
                    with patch.dict(VERIFY.F_COMPOUND_IDENTITIES, {profile: fixture_identity}):
                        if defect is None:
                            evidence = VERIFY.compound_native_evidence(manifest, build, source, native, proof, profile)
                            self.assertEqual(evidence["native_policy"], manifest["native_policy"])
                        else:
                            with self.assertRaises(ValueError):
                                VERIFY.compound_native_evidence(manifest, build, source, native, proof, profile)
        for declaration in (None, {"path": VERIFY.SPELLING, "selection": "best", "variant": "atomic-assignment"}):
            with self.subTest(declaration=declaration), self.assertRaisesRegex(ValueError, "outside its finite route"):
                VERIFY.compound_native_evidence({"post_spelling": declaration, "native_policy": {}}, Path("unread"), b"", b"", {}, "test-p4")

    def test_F_compound_v2_native_scope_rejects_v1_transplants_and_type_changes(self):
        for profile in VERIFY.F_COMPOUND_V2_IDENTITIES:
            for defect in (None, "missing", "v1-policy", "v1-source", "v1-declaration", "source", "native", "float", "bool",
                           "alternate-compiler", "version", "banner", "gate-policy", "extra-declaration", "family"):
                with self.subTest(profile=profile, defect=defect), tempfile.TemporaryDirectory(prefix="rove4k-F-compound-v2-") as temporary:
                    build = Path(temporary)
                    manifest, source, native, proof = compound_gate_fixture(build, "F", profile, v2=True)
                    fixture_identity = {"source": VERIFY.pin(source), "native": VERIFY.pin(native)}
                    if defect == "missing": del manifest["native_policy"]
                    elif defect == "v1-policy": manifest["native_policy"]["kind"] = VERIFY.F_COMPOUND_POLICY
                    elif defect == "v1-source": manifest["native_policy"]["source"] = VERIFY.F_COMPOUND_IDENTITIES[profile]["source"]
                    elif defect == "v1-declaration": manifest["post_spelling"] = dict(VERIFY.COMPOUND_DECLARATION)
                    elif defect == "source": manifest["native_policy"]["source"]["sha256"] = "0" * 64
                    elif defect == "native": manifest["native_policy"]["native"]["sha256"] = "0" * 64
                    elif defect == "float": manifest["native_policy"]["source"]["bytes"] = float(len(source))
                    elif defect == "bool": manifest["native_policy"]["source"]["bytes"] = True
                    elif defect == "alternate-compiler": manifest["compile_executor"][0] = "/usr/bin/gcc-11"
                    elif defect == "version": manifest["compile_executor_version"] = "different compiler"
                    elif defect == "banner":
                        data = b"different actual compiler banner\n"
                        manifest["commands"][0]["stdout"].update(VERIFY.pin(data))
                        (build / "tool-1-target-compiler-version.stdout").write_bytes(data)
                    elif defect == "gate-policy": manifest["attempts"][0]["target_type_gate"]["policy"] = VERIFY.F_COMPOUND_POLICY
                    elif defect == "extra-declaration": manifest["post_spelling"]["extra"] = True
                    elif defect == "family": manifest["family"] = "A"
                    with patch.dict(VERIFY.F_COMPOUND_V2_IDENTITIES, {profile: fixture_identity}):
                        if defect is None:
                            evidence = VERIFY.compound_native_evidence(manifest, build, source, native, proof, profile)
                            self.assertEqual(evidence["declaration"], VERIFY.F_COMPOUND_DECLARATION)
                            self.assertEqual(evidence["native_policy"]["kind"], VERIFY.F_COMPOUND_V2_POLICY)
                            self.assertEqual(len(evidence["attempts"]), 2)
                        else:
                            with self.assertRaises(ValueError):
                                VERIFY.compound_native_evidence(manifest, build, source, native, proof, profile)

    def test_dependency_cleanup_follows_spelling_and_is_undone_first(self):
        resource = {"schema": "rove4k.c-resource-projection.v1"}
        phase = {"schema": "rove4k.portable-phase-source.v1"}
        model = {"stage": "canonical-e19-physical-binding"}
        spelling = {"schema": VERIFY.SPELLING_SCHEMA}
        dependency = {"schema": "rove4k.profile-dependencies.v1"}
        post = {"path": "engines/experiments/tcec-next/profile_phase.py", "variant": "phase-init"}
        selected = {"path": VERIFY.SPELLING, "selection": "best", "variant": "clock-type"}
        declaration = {"path": "engines/experiments/tcec-next/profile_dependencies.py", "variant": "unused-includes"}
        options = dict(post_spelling=selected, source_dependencies=declaration,
                       representation="source-jit", entry_cleanup="private-path")
        proofs = [resource, phase, model, spelling, dependency]
        self.assertEqual(VERIFY.source_stages("E", post, proofs, **options), "phase")
        for stages in ([resource, phase, model, dependency, spelling], proofs + [dependency], proofs[:-1]):
            with self.subTest(stages=stages), self.assertRaises(ValueError):
                VERIFY.source_stages("E", post, stages, **options)
        with self.assertRaises(TypeError):
            VERIFY.source_stages("E", post, proofs, declaration)
        calls = []
        spell = types.SimpleNamespace(restore_source=lambda source, proof: calls.append("spelling") or source[1:])
        dep = types.SimpleNamespace(restore_source=lambda source, proof: calls.append("dependency") or source + b";")
        self.assertEqual(VERIFY.inverse_source_stages(b"Stable=1", [
            (spell, {}, b"table=1;"), (dep, {}, b"Stable=1;")]), b"table=1;")
        self.assertEqual(calls, ["dependency", "spelling"])

    def test_dependency_identity_still_binds_both_actual_shipping_stdins(self):
        from copy import deepcopy
        source = b"int main(void){return 0;}\n"
        manifest = {"compiler": ["cc"], "attempts": [], "commands": []}
        with tempfile.TemporaryDirectory(prefix="rove4k-dependency-evidence-") as temporary:
            build = Path(temporary)
            for index, directory in enumerate(("first", "repeat"), 1):
                manifest["attempts"].append({"directory": directory,
                    **{"native_" + key: value for key, value in VERIFY.pin(b"native").items()}})
                path = build / f"tool-{index}-{directory}-compile.stdout"
                path.with_suffix(".stdin").write_bytes(source)
                manifest["commands"].append({"kind": directory + "-compile", "command": ["cc"],
                                             "stdout": {"path": str(path)}})
            record = VERIFY.dependency_evidence(manifest, build, {}, {}, source, source)
            self.assertEqual([row["kind"] for row in record["compiler_commands"]], ["first-compile", "repeat-compile"])
            self.assertTrue(all(row["stdin"]["sha256"] == VERIFY.pin(source)["sha256"]
                                for row in record["compiler_commands"]))
            for kind in ("missing", "duplicate", "argv"):
                altered = deepcopy(manifest)
                if kind == "missing":
                    altered["commands"].pop()
                elif kind == "duplicate":
                    altered["commands"][1] = dict(altered["commands"][0])
                else:
                    altered["commands"][1]["command"] = ["other-compiler"]
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    VERIFY.dependency_evidence(altered, build, {}, {}, source, source)
            (build / "tool-2-repeat-compile.stdin").write_bytes(b"wrong")
            with self.assertRaises(ValueError):
                VERIFY.dependency_evidence(manifest, build, {}, {}, source, source)


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

    def test_league_resources_bind_reviewed_owner_and_complete_closure(self):
        owner = VERIFY.LEAGUE_PROFILE_OWNER
        expected = VERIFY.LEAGUE_PROFILE_OWNER_PIN
        pins = {owner: dict(expected)}
        self.assertEqual(VERIFY.pin(VERIFY.source_bytes(owner)), expected)
        with tempfile.TemporaryDirectory(prefix="rove4k-league-resource-") as temporary:
            root = Path(temporary)
            destination = root / "inputs" / owner
            destination.parent.mkdir(parents=True)
            destination.write_bytes(VERIFY.source_bytes(owner))
            closure = {"inputs": [{"path": owner, "role": "tool", **expected}]}
            for profile_id, workers, tt_bytes in (("test-p16", 16, 12 << 30),
                                                   ("test-p192", 192, 192 << 30)):
                with self.subTest(profile=profile_id):
                    profile = VERIFY.profile_resource(profile_id, input_pins=pins, build=root,
                                                      source_closure=closure)
                    self.assertEqual(profile.workers, workers)
                    self.assertEqual(profile.to_record(24)["tt_bytes"], tt_bytes)
                    selected = VERIFY._resource_record(profile.to_record(24), "A", input_pins=pins,
                                                       build=root, source_closure=closure)[0]
                    self.assertEqual(selected.to_record(24), profile.to_record(24))
                    forged = profile.to_record(24)
                    forged["workers"] += 1
                    with self.assertRaisesRegex(ValueError, "selected immutable profile"):
                        VERIFY._resource_record(forged, "A", input_pins=pins, build=root,
                                                source_closure=closure)
            for invalid in ({"inputs": []}, {"inputs": [{"path": owner, "role": "engine", **expected}]},
                            {"inputs": [{"path": owner, "role": "tool", **expected}] * 2}):
                with self.subTest(closure=invalid), self.assertRaisesRegex(ValueError, "pinned production tool"):
                    VERIFY.profile_resource("test-p16", input_pins=pins, build=root, source_closure=invalid)
            destination.write_bytes(b"forged owner")
            with self.assertRaisesRegex(ValueError, "artifact size differs|artifact identity differs"):
                VERIFY.profile_resource("test-p16", input_pins=pins, build=root, source_closure=closure)
        # Matching a malicious owner's self-claimed digest must be rejected before
        # reading or executing even if a manifest supplies the same digest.
        forged_pin = VERIFY.pin(b"malicious owner")
        with patch.object(VERIFY, "source_bytes", side_effect=AssertionError("must not read owner")):
            with self.assertRaisesRegex(ValueError, "pin differs from reviewed source"):
                VERIFY.profile_resource("test-p16", input_pins={owner: forged_pin})
        with self.assertRaisesRegex(ValueError, "missing from the admitted input closure"):
            VERIFY.profile_resource("test-p16", input_pins={})

    def test_league_runtime_headroom_rejects_before_execution(self):
        from dataclasses import replace
        pins = {VERIFY.LEAGUE_PROFILE_OWNER: dict(VERIFY.LEAGUE_PROFILE_OWNER_PIN)}
        for profile_id, tt_bytes, cpus, available in (("test-p16", 12 << 30, 16, 16 << 30),
                                                      ("test-p192", 192 << 30, 192, 196 << 30)):
            with self.subTest(profile=profile_id):
                profile = VERIFY.profile_resource(profile_id, input_pins=pins)
                selected = replace(admitted(), profile_id=profile_id, resources=profile.to_record(24),
                                   input_pins=pins)
                with patch.object(VERIFY.os, "sched_getaffinity", return_value=set(range(cpus)), create=True):
                    with self.assertRaisesRegex(ValueError, "insufficient effective headroom before allocation"):
                        VERIFY.execution_limits(selected, tt_bytes)
                    limits = VERIFY.execution_limits(selected, available)
                self.assertEqual(limits["admission"]["tt_bytes"], tt_bytes)
                self.assertEqual(limits["CPU_budget_effective_cpus"], cpus)
                self.assertGreater(limits["address_space_bytes"], tt_bytes)
                self.assertNotIn("qualified", limits)

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

    def test_shared_smt_shape_is_diagnostic_not_qualification(self):
        def rows(cores):
            return [{"cpu": cpu, "socket": 0, "core": cpu % 96,
                     "node": (cpu % 96) // 24,
                     "siblings": sorted([cpu % 96, cpu % 96 + 96])}
                    for cpu in cores]
        p16 = list(range(8)) + list(range(96, 104))
        small = VERIFY._shared_test_topology("test-p16", p16, rows(p16), 192)
        self.assertTrue(small["profile_cpu_node_shape_observed"])
        self.assertEqual(small["observed_nodes"], [0])
        self.assertFalse(small["all_online_cpus_in_affinity"])
        self.assertFalse(small["scored_placement_confirmed"])
        self.assertFalse(small["memory_policy_observed"])
        self.assertFalse(small["worker_affinity_observed"])
        self.assertFalse(small["tt_page_placement_observed"])
        p192 = list(range(192))
        large = VERIFY._shared_test_topology("test-p192", p192, rows(p192), 192)
        self.assertTrue(large["profile_cpu_node_shape_observed"])
        self.assertTrue(large["all_online_cpus_in_affinity"])
        self.assertEqual(large["observed_physical_groups"], 96)
        self.assertFalse(large["scored_placement_confirmed"])
        tampered = rows(p16)
        tampered[0]["siblings"] = [0]
        self.assertFalse(VERIFY._shared_test_topology("test-p16", p16, tampered, 192)
                         ["profile_cpu_node_shape_observed"])
        tampered = rows(p16)
        tampered[0]["node"] = None
        self.assertFalse(VERIFY._shared_test_topology("test-p16", p16, tampered, 192)
                         ["profile_cpu_node_shape_observed"])
        split = list(range(4)) + list(range(24, 28)) + list(range(96, 100)) + list(range(120, 124))
        self.assertFalse(VERIFY._shared_test_topology("test-p16", split, rows(split), 192)
                         ["profile_cpu_node_shape_observed"])

    def test_sysfs_cpu_list_parser_rejects_malformed_or_overlapping_ranges(self):
        self.assertEqual(VERIFY._parse_linux_cpu_list("0-2,7,9-10\n"), [0, 1, 2, 7, 9, 10])
        for value in ("", "2-1", "1,1", "1-2,2-3", "-1", "x", "0-1048576"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                VERIFY._parse_linux_cpu_list(value)

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
