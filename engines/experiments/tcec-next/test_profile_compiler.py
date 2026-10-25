"""Compiler/source/ELF admission boundaries; no compiler or engine is run."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("profile_compiler_test_target", HERE / "profile_compiler.py")
TARGET = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TARGET
SPEC.loader.exec_module(TARGET)
VERIFY = TARGET.load("profile_compiler_test_verify", HERE / "profile_verify.py")


def elf(*, version="GLIBC_2.34", load_flags=5, stack_flags=6,
        version_address=0x400380, need_count=1, duplicate=False, dynamic=True):
    data = bytearray(1024)
    identity = b"\x7fELF\x02\x01\x01" + b"\0" * 9
    headers = [(1, load_flags, 0, 0x400000, 0, len(data), len(data), 4096),
               (0x6474e551, stack_flags, 0, 0, 0, 0, 0, 0)]
    if dynamic:
        strings = b"libc.so.6\0" + version.encode() + b"\0"
        data[0x300:0x300 + len(strings)] = strings
        tags = [(1, 0), (5, 0x400300), (10, len(strings)),
                (0x6ffffffe, version_address), (0x6fffffff, need_count)]
        if duplicate:
            tags.append((0x6fffffff, need_count))
        tags.append((0, 0))
        for index, row in enumerate(tags):
            struct.pack_into("<qQ", data, 0x200 + index * 16, *row)
        struct.pack_into("<HHIII", data, 0x380, 1, 1, 0, 16, 0)
        struct.pack_into("<IHHII", data, 0x390, 0, 0, 2, 10, 0)
        headers.append((2, 4, 0x200, 0x400200, 0, len(tags) * 16, len(tags) * 16, 8))
    else:
        # An unrelated literal must not be mistaken for an imported ABI need.
        data[0x300:0x30b] = b"GLIBC_99.9\0"
    struct.pack_into("<16sHHIQQQIHHHHHH", data, 0, identity, 2, 62, 1,
                     0x400100, 64, 0, 0, 64, 56, len(headers), 0, 0, 0)
    for index, row in enumerate(headers):
        struct.pack_into("<IIQQQQQQ", data, 64 + index * 56, *row)
    return bytes(data)


class TargetCompilerBoundaries(unittest.TestCase):
    def test_source_port_is_opt_in_and_cannot_upgrade_an_sdk_receipt(self):
        self.assertFalse(TARGET.source_port_enabled(None, None, system=False))
        self.assertTrue(TARGET.source_port_enabled(Path("source-bundle.zip"), Path("source-seal.json"), system=True))
        with self.assertRaisesRegex(ValueError, "supplied together"):
            TARGET.source_port_enabled(Path("source-bundle.zip"), None, system=True)
        with self.assertRaisesRegex(ValueError, "explicit Ubuntu22 system"):
            TARGET.source_port_enabled(Path("source-bundle.zip"), Path("source-seal.json"), system=False)

    def provenance_fixture(self, base):
        # The public validator has its own archive/admission tests. Here its
        # response is isolated to test this producer's live/raw binding port.
        helper = TARGET.load("compiler_source_port_test_helper", HERE / "target_runtime.py")
        ci = helper.CIContext("owner/repo", "a" * 40, "12", "1")
        bundle, seal = base / "source-bundle.zip", base / "source-seal.json"
        bundle.write_bytes(b"unit fixture source bundle")
        seal.write_bytes(b"unit fixture source seal")
        source = TARGET.normalized(HERE / "target_runtime.py")
        record = {"source_context": ci.to_record(), "source_bundle": TARGET.pin(bundle.read_bytes()),
                  "source_seal": TARGET.pin(seal.read_bytes()),
                  "source_provenance_tools": {TARGET.SOURCE_PROVENANCE: TARGET.pin(source)},
                  "source_profile": {"family": "A", "profile": "test-p4"}}
        selected = SimpleNamespace(admission=object(), build=base / "source-build")
        return helper, ci, bundle, seal, record, selected

    def test_source_port_delegates_exact_admission_and_keeps_raw_helper_pins(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-compiler-source-port-") as temporary:
            helper, ci, bundle, seal, record, selected = self.provenance_fixture(Path(temporary).resolve())
            verify = object()
            with patch.object(TARGET, "load", return_value=helper), \
                    patch.object(helper.CIContext, "from_environment", return_value=ci), \
                    patch.object(helper, "source_bundle_binding", return_value=record) as binding:
                observed, sources = TARGET.source_provenance([selected], verify, bundle=bundle, seal=seal)
            self.assertEqual(observed, record)
            self.assertEqual(TARGET.pin(sources[TARGET.SOURCE_PROVENANCE]), record["source_provenance_tools"][TARGET.SOURCE_PROVENANCE])
            binding.assert_called_once_with(selected.admission, selected.build, verify=verify,
                source_bundle=bundle, source_seal=seal, expected_ci=ci)

    def test_source_port_rejects_missing_live_context_before_reading_raw_artifacts(self):
        helper = TARGET.load("compiler_source_port_missing_context", HERE / "target_runtime.py")
        with patch.object(TARGET, "load", return_value=helper), \
                patch.object(helper.CIContext, "from_environment", side_effect=ValueError("live GitHub Actions context required")), \
                patch.object(TARGET, "regular") as read:
            with self.assertRaisesRegex(ValueError, "live GitHub Actions"):
                TARGET.source_provenance([SimpleNamespace()], object(),
                    bundle=HERE / "source-bundle.zip", seal=HERE / "source-seal.json")
            read.assert_not_called()

    def test_source_port_rejects_compiler_redirection_before_artifact_read(self):
        helper = TARGET.load("compiler_source_port_redirect", HERE / "target_runtime.py")
        with patch.object(TARGET, "load", return_value=helper), \
                patch.dict(TARGET.os.environ, {"CPATH": "/not-an-admitted-header-context"}), \
                patch.object(TARGET, "regular") as read:
            with self.assertRaisesRegex(ValueError, "compiler redirection environment"):
                TARGET.source_provenance([SimpleNamespace()], object(),
                    bundle=HERE / "source-bundle.zip", seal=HERE / "source-seal.json")
            read.assert_not_called()

    def test_source_port_cannot_rebind_raw_inputs_or_a_changed_ci_context(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-compiler-source-port-reject-") as temporary:
            helper, ci, bundle, seal, record, selected = self.provenance_fixture(Path(temporary).resolve())
            for field in ("source_bundle", "source_seal", "source_context"):
                wrong = dict(record)
                wrong[field] = {}  # Reaches this port's exact binding boundary.
                with self.subTest(field=field), patch.object(TARGET, "load", return_value=helper), \
                        patch.object(helper.CIContext, "from_environment", return_value=ci), \
                        patch.object(helper, "source_bundle_binding", return_value=wrong):
                    with self.assertRaisesRegex(ValueError, "live context/raw inputs/helper"):
                        TARGET.source_provenance([selected], object(), bundle=bundle, seal=seal)
            changed = helper.CIContext("owner/repo", "a" * 40, "12", "2")
            with patch.object(TARGET, "load", return_value=helper), \
                    patch.object(helper.CIContext, "from_environment", side_effect=[ci, changed]), \
                    patch.object(helper, "source_bundle_binding", return_value=record):
                with self.assertRaisesRegex(ValueError, "context changed during capture"):
                    TARGET.source_provenance([selected], object(), bundle=bundle, seal=seal)

    def test_raw_source_inputs_cannot_change_during_validator_capture(self):
        for name in ("source-bundle.zip", "source-seal.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory(prefix="rove4k-compiler-source-port-race-") as temporary:
                helper, ci, bundle, seal, record, selected = self.provenance_fixture(Path(temporary).resolve())
                def changed(*args, **kwargs):
                    (bundle if name == bundle.name else seal).write_bytes(b"replacement raw input")
                    return record
                with patch.object(TARGET, "load", return_value=helper), \
                        patch.object(helper.CIContext, "from_environment", return_value=ci), \
                        patch.object(helper, "source_bundle_binding", side_effect=changed):
                    with self.assertRaisesRegex(ValueError, "input/helper changed during capture"):
                        TARGET.source_provenance([selected], object(), bundle=bundle, seal=seal)

    def test_source_port_is_one_explicit_family_profile_per_runtime_reference(self):
        with self.assertRaisesRegex(ValueError, "one explicit family/profile"):
            TARGET.source_provenance([object(), object()], object(),
                bundle=Path("source-bundle.zip"), seal=Path("source-seal.json"))

    def program_fixture(self, base):
        tools = base / "system"
        tools.mkdir()
        paths = {}
        for role in TARGET.PROGRAM_ROLES:
            path = tools / role
            path.write_bytes(("fixture " + role).encode())
            paths[role] = path
        calls = []
        def run(command, *, cwd, kind):
            role = command[1].split("=", 1)[1]
            calls.append((kind, tuple(command), cwd))
            return (str(paths[role]) + "\n").encode()
        return paths, calls, SimpleNamespace(run=run)

    def test_program_roles_are_observed_before_post_and_all_consumed(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-compiler-role-port-") as temporary:
            base = Path(temporary).resolve()
            paths, calls, host = self.program_fixture(base)
            consumed = {}
            before = TARGET.query_programs(base / "gcc", host=host, cwd=base, system=True,
                input_roots=(base,), consumed=consumed)
            after = TARGET.recheck_programs(base / "gcc", expected=before, host=host, cwd=base,
                system=True, input_roots=(base,), consumed=consumed)
            self.assertEqual(after, before)
            self.assertEqual(set(before), set(TARGET.PROGRAM_ROLES))
            self.assertEqual(set(consumed), {str(p) for p in paths.values()})
            self.assertEqual([c[0] for c in calls],
                ["compiler-program-" + q for q in TARGET.PROGRAM_ROLES] +
                ["compiler-program-recheck-" + q for q in TARGET.PROGRAM_ROLES])

    def test_program_role_resolution_cannot_change_even_to_identical_bytes(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-compiler-role-change-") as temporary:
            base = Path(temporary).resolve()
            paths, _, host = self.program_fixture(base)
            consumed = {}
            before = TARGET.query_programs(base / "gcc", host=host, cwd=base, system=True,
                input_roots=(base,), consumed=consumed)
            replacement = base / "system/as-replacement"
            replacement.write_bytes(paths["as"].read_bytes())
            paths["as"] = replacement
            with self.assertRaisesRegex(ValueError, "roles changed between before/post"):
                TARGET.recheck_programs(base / "gcc", expected=before, host=host, cwd=base,
                    system=True, input_roots=(base,), consumed=consumed)

    def test_imported_glibc_requirements_are_parsed_from_version_tables(self):
        result = TARGET.elf_abi(elf(version="GLIBC_2.35"), VERIFY)
        self.assertEqual(result["imported_versions"], [{"library": "libc.so.6", "version": "GLIBC_2.35"}])
        self.assertEqual(result["glibc_ceiling"], "2.35")
        self.assertFalse(result["writable_executable_segment"])
        self.assertFalse(result["executable_stack"])

    def test_newer_and_private_glibc_requirements_cannot_claim_jammy_compatibility(self):
        for version, reason in (("GLIBC_2.36", "newer than"),
                                ("GLIBC_PRIVATE", "private/non-numeric"),
                                ("GLIBC_ABI_DT_RELR", "private/non-numeric")):
            with self.subTest(version=version), self.assertRaisesRegex(ValueError, reason):
                TARGET.elf_abi(elf(version=version), VERIFY)

    def test_static_native_does_not_acquire_versions_from_plain_strings(self):
        result = TARGET.elf_abi(elf(dynamic=False), VERIFY)
        self.assertEqual(result["DT_NEEDED"], [])
        self.assertEqual(result["imported_versions"], [])

    def test_unmapped_duplicate_or_inconsistent_version_tables_are_rejected(self):
        for arguments, reason in (({"version_address": 0x900000}, "escaped uniquely"),
                                  ({"duplicate": True}, "duplicate ELF ABI"),
                                  ({"need_count": 2}, "count and termination")):
            with self.subTest(arguments=arguments), self.assertRaisesRegex(ValueError, reason):
                TARGET.elf_abi(elf(**arguments), VERIFY)

    def test_existing_program_permissions_gate_is_preserved(self):
        for arguments, reason in (({"load_flags": 7}, "writable executable"),
                                  ({"stack_flags": 7}, "stack is executable")):
            with self.subTest(arguments=arguments), self.assertRaisesRegex(ValueError, reason):
                TARGET.elf_abi(elf(**arguments), VERIFY)

    def test_family_flags_cannot_be_injected_through_a_build_receipt(self):
        accepted = SimpleNamespace(family="A", profile="tcec-provisional")
        verifier = SimpleNamespace(admit_c_build=lambda *args: accepted)
        with tempfile.TemporaryDirectory(prefix="rove4k-compiler-flags-") as temporary:
            build = Path(temporary).resolve()
            record = {"family": "A", "compiler": [*TARGET.C_FLAGS["A"], "-fplugin=unknown.so"]}
            (build / "build.json").write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "reviewed family contract"):
                TARGET.admit(build, verifier)

    def test_source_admission_failure_propagates_before_target_flags_or_artifacts(self):
        def failed(*args):
            raise ValueError("actual production projection differs")
        verifier = SimpleNamespace(admit_c_build=failed)
        with tempfile.TemporaryDirectory(prefix="rove4k-compiler-source-") as temporary:
            build = Path(temporary).resolve()
            (build / "build.json").write_text('{"family":"B"}')
            with self.assertRaisesRegex(ValueError, "production projection differs"):
                TARGET.admit(build, verifier)

    def test_input_adapter_consumes_the_real_admitted_build_api(self):
        source = b"int main(void){return 0;}\n"
        accepted = VERIFY.AdmittedBuild("A", "tcec-provisional", "source-jit", "x", "main.c",
            "native/x", {}, {}, {}, {}, {}, {})
        verifier = SimpleNamespace(admit_c_build=lambda *args: accepted,
                                  checked_artifact=lambda *args: source)
        with tempfile.TemporaryDirectory(prefix="rove4k-compiler-adapter-") as temporary:
            build = Path(temporary).resolve()
            record = {"family": "A", "compiler": list(TARGET.C_FLAGS["A"]),
                      "expected_contract": {"source_bytes": len(source),
                                            "source_sha256": TARGET.pin(source)["sha256"]},
                      "source_proofs": [{"target_type_assertions": ["_Static_assert(sizeof(void*)==8,\"LP64\");"]}]}
            (build / "build.json").write_text(json.dumps(record))
            result = TARGET.admit(build, verifier)
            self.assertEqual((result.family, result.profile), ("A", "tcec-provisional"))
            self.assertEqual(result.files, {"main.c": source})

    def descriptor(self, base):
        compiler = base / "bin/gcc-11"
        compiler.parent.mkdir()
        compiler.write_bytes(b"audited wrapper")
        driver = base / "root/usr/bin/gcc-11"
        driver.parent.mkdir(parents=True)
        driver.write_bytes(b"compiler")
        smoke = {"complete": True, "wrapper": str(compiler),
                 "wrapper_sha256": TARGET.pin(compiler.read_bytes())["sha256"],
                 "wrapper_version": "gcc-11 (Ubuntu 11.4.0) 11.4.0", "cc": str(driver)}
        smoke_raw = json.dumps(smoke).encode()
        audit = {"complete": True, "wrapper": {"path": str(compiler),
                 "sha256": smoke["wrapper_sha256"]},
                 "smoke_receipt_sha256": TARGET.pin(smoke_raw)["sha256"]}
        audit_raw = json.dumps(audit).encode()
        return compiler, audit_raw, smoke_raw, TARGET.pin(audit_raw)["sha256"]

    def test_sdk_audit_binds_wrapper_and_smoke_not_just_complete_booleans(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-compiler-sdk-") as temporary:
            compiler, audit, smoke, digest = self.descriptor(Path(temporary).resolve())
            result = TARGET.sdk_descriptor(compiler, audit, smoke, audit_sha256=digest)
            self.assertEqual(result["wrapper"]["sha256"], TARGET.pin(compiler.read_bytes())["sha256"])
            compiler.write_bytes(b"changed wrapper")
            with self.assertRaisesRegex(ValueError, "wrapper identity differs"):
                TARGET.sdk_descriptor(compiler, audit, smoke, audit_sha256=digest)

    def test_sdk_unbound_smoke_or_unreviewed_audit_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-compiler-sdk-pins-") as temporary:
            compiler, audit, smoke, digest = self.descriptor(Path(temporary).resolve())
            with self.assertRaisesRegex(ValueError, "audit identity differs"):
                TARGET.sdk_descriptor(compiler, audit, smoke, audit_sha256="0" * 64)
            with self.assertRaisesRegex(ValueError, "bind this compiler smoke"):
                TARGET.sdk_descriptor(compiler, audit, smoke + b"\n", audit_sha256=digest)

    def test_relocated_sdk_audit_binds_actual_driver_provider(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-compiler-relocated-") as temporary:
            compiler, old_audit, smoke_raw, _ = self.descriptor(Path(temporary).resolve())
            smoke = json.loads(smoke_raw)
            driver = Path(smoke["cc"])
            audit = {"schema": "rove4k.jammy-gcc11-relocated-sdk-audit.v2", "complete": True,
                     "wrapper": json.loads(old_audit)["wrapper"], "cc_version": smoke["wrapper_version"],
                     "dumpfullversion": "11.4.0", "compile": {"returncode": 0},
                     "ordinary_target_interpreter_preserved": True,
                     "providers": {"compiler": {"path": str(driver), "resolved": str(driver.resolve()),
                                    "sha256": TARGET.pin(driver.read_bytes())["sha256"]}}}
            raw = json.dumps(audit).encode()
            digest = TARGET.pin(raw)["sha256"]
            self.assertTrue(TARGET.sdk_descriptor(compiler, raw, audit_sha256=digest)["smoke_is_in_audit"])
            driver.write_bytes(b"changed compiler")
            with self.assertRaisesRegex(ValueError, "provider changed or escaped"):
                TARGET.sdk_descriptor(compiler, raw, audit_sha256=digest)

    def test_later_dependency_discovery_cannot_overwrite_an_earlier_pin(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-compiler-input-") as temporary:
            header = Path(temporary).resolve() / "header.h"
            header.write_bytes(b"original")
            inputs = {}
            TARGET.record_input(inputs, header)
            original = dict(inputs)
            header.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "input changed during discovery"):
                TARGET.record_input(inputs, header)
            self.assertEqual(inputs, original)

    def test_system_bare_program_uses_path_but_sdk_must_resolve_explicitly(self):
        with patch.object(TARGET.shutil, "which", return_value=sys.executable):
            self.assertEqual(TARGET.compiler_program("as", system=True), Path(sys.executable).resolve())
            with self.assertRaisesRegex(ValueError, "absolute executable"):
                TARGET.compiler_program("as", system=False)

    def test_executing_checker_source_cannot_be_rebound_to_a_later_edit(self):
        source = TARGET.normalized(HERE / "profile_compiler.py")
        self.assertEqual(TARGET.executing_source(source), source)
        with self.assertRaisesRegex(ValueError, "executing module was compiled"):
            TARGET.executing_source(source.replace(b"GLIBC_MAX = (2, 35)", b"GLIBC_MAX = (2, 99)"))

    def test_dependency_paths_allow_escaped_spaces_and_refuse_host_header_fallback(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-compiler-deps-") as temporary:
            base = Path(temporary).resolve()
            sdk, own = base / "sdk", base / "own"
            sdk.mkdir()
            own.mkdir()
            header = sdk / "a header.h"
            header.write_bytes(b"header")
            token = str(header).replace("\\", "/").replace(" ", "\\ ")
            result = TARGET.dependency_paths(("x: " + token + "\n").encode(), sdk_root=sdk, owned_root=own)
            self.assertEqual(result, {header})
            outside = base / "host-header.h"
            outside.write_bytes(b"host")
            token = str(outside).replace("\\", "/")
            with self.assertRaisesRegex(ValueError, "escaped the SDK"):
                TARGET.dependency_paths(("x: " + token + "\n").encode(), sdk_root=sdk, owned_root=own)

    def test_system_target_mode_does_not_relabel_noble_as_ubuntu22(self):
        TARGET.ubuntu22_host({"ID": "ubuntu", "VERSION_ID": "22.04"}, ("glibc", "2.35"))
        for fields, libc, reason in (({"ID": "ubuntu", "VERSION_ID": "24.04"},
                                     ("glibc", "2.39"), "actual Ubuntu 22.04"),
                                    ({"ID": "ubuntu", "VERSION_ID": "22.04"},
                                     ("glibc", "2.39"), "actual glibc 2.35")):
            with self.subTest(fields=fields, libc=libc), self.assertRaisesRegex(ValueError, reason):
                TARGET.ubuntu22_host(fields, libc)

    def test_provisional_layout_is_64_bit_and_not_an_allocation(self):
        api = VERIFY.contracts()
        profile = api.resource_profile("tcec-provisional")
        self.assertEqual(profile.workers, 256)
        for family, bits, byte_count in (("A", 33, 192 << 30), ("D", 34, 256 << 30)):
            with self.subTest(family=family):
                layout = profile.layout(api.engine_spec(family).entry_bytes)
                self.assertEqual(layout.bits, bits)
                self.assertEqual(layout.bytes, byte_count)
                self.assertGreater(layout.mask, (1 << 32) - 1)


if __name__ == "__main__":
    unittest.main()
