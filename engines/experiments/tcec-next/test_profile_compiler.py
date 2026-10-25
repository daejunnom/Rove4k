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
    def setUp(self):
        if TARGET.os.name != "posix":
            # Windows exercises the pure compiler policies with trusted local
            # fixtures only. The actual no-follow reader runs in POSIX tests.
            def fixture_read(path, *, limit, allow_hardlinks=False):
                with Path(path).open("rb") as stream:
                    data = stream.read(limit + 1)
                if len(data) > limit:
                    raise ValueError("trusted fixture exceeds its explicit bound")
                return data
            scoped = patch.object(TARGET.INPUT, "read_regular", side_effect=fixture_read)
            scoped.start()
            self.addCleanup(scoped.stop)

    def test_compiler_reads_delegate_exact_limits_and_hardlink_policy(self):
        path = HERE / "fixture.c"
        with patch.object(TARGET.INPUT, "read_regular", return_value=b"line\r\n") as read:
            self.assertEqual(TARGET.regular(path), b"line\r\n")
            read.assert_called_with(path, limit=64 << 20, allow_hardlinks=False)
            self.assertEqual(TARGET.regular(path, limit=16384, allow_hardlinks=True), b"line\r\n")
            read.assert_called_with(path, limit=16384, allow_hardlinks=True)
            self.assertEqual(TARGET.normalized(path), b"line\n")
            read.assert_called_with(path, limit=16 << 20, allow_hardlinks=False)
            read.return_value = b"lone\r"
            with self.assertRaisesRegex(ValueError, "lone CR"):
                TARGET.normalized(path)

    @unittest.skipUnless(TARGET.os.name == "posix", "actual POSIX input reader required")
    def test_installed_hardlinks_are_explicit_and_never_tool_evidence(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-compiler-hardlink-") as temporary:
            path = Path(temporary).resolve() / "installed-header.h"
            path.write_bytes(b"installed input")
            TARGET.os.link(path, path.with_name("second-name.h"))
            with self.assertRaisesRegex(ValueError, "bounded ordinary"):
                TARGET.regular(path)
            with self.assertRaisesRegex(ValueError, "bounded ordinary"):
                TARGET.normalized(path)
            self.assertEqual(TARGET.regular(path, allow_hardlinks=True), b"installed input")
            inputs = {}
            TARGET.record_input(inputs, path)
            self.assertEqual(inputs[str(path)], TARGET.pin(b"installed input"))

    def test_shared_reader_source_is_bound_to_its_executing_code(self):
        source = TARGET.INPUT.source_identity()
        self.assertEqual(source, TARGET.normalized(TARGET.ROOT / TARGET.INPUT_PATH))
        with patch.object(TARGET.INPUT, "read_regular", return_value=source + b"\nchanged = True\n"):
            with self.assertRaisesRegex(ValueError, "source differs from its executing code"):
                TARGET.INPUT.source_identity()

    def clean_source_environment(self, helper):
        # Source-port fixtures control their compiler context independently of
        # setup-python or a developer shell. Explicit injection tests run inside
        # this scope; unrelated environment entries (including CC) are retained.
        environment = {key: value for key, value in TARGET.os.environ.items()
                       if key not in helper.COMPILER_ENV}
        scoped = patch.dict(TARGET.os.environ, environment, clear=True)
        scoped.start()
        self.addCleanup(scoped.stop)

    def test_source_port_is_opt_in_and_cannot_upgrade_an_sdk_receipt(self):
        self.assertFalse(TARGET.source_port_enabled(None, None, system=False))
        self.assertTrue(TARGET.source_port_enabled(Path("source-bundle.zip"), Path("source-seal.json"), system=True))
        with self.assertRaisesRegex(ValueError, "supplied together"):
            TARGET.source_port_enabled(Path("source-bundle.zip"), None, system=True)
        with self.assertRaisesRegex(ValueError, "explicit Ubuntu22 system"):
            TARGET.source_port_enabled(Path("source-bundle.zip"), Path("source-seal.json"), system=False)

    def test_program_port_is_independent_of_ci_and_rejects_sdk_context(self):
        for system in (False, True):
            self.assertFalse(TARGET.program_provenance_enabled(False, False, system=system))
        for explicit, source in ((True, False), (False, True), (True, True)):
            with self.subTest(explicit=explicit, source=source):
                self.assertTrue(TARGET.program_provenance_enabled(explicit, source, system=True))
                with self.assertRaisesRegex(ValueError, "explicit Ubuntu22 system"):
                    TARGET.program_provenance_enabled(explicit, source, system=False)

    def test_program_cli_rejects_sdk_before_reading_any_context_or_tool(self):
        argv = ["profile_compiler.py", "--build", "unused", "--compiler", "unused",
                "--sdk-audit", "unused", "--program-provenance", "--out", "unused"]
        with patch.object(TARGET.sys, "argv", argv), \
                patch.object(TARGET.INPUT, "source_identity") as tool, \
                patch.object(TARGET, "regular") as read, \
                patch.object(TARGET, "sdk_descriptor") as context:
            with self.assertRaisesRegex(ValueError, "explicit Ubuntu22 system"):
                TARGET.main()
            tool.assert_not_called()
            read.assert_not_called()
            context.assert_not_called()

    def compiler_main_fixture(self, base, *, program, changed_env_at=None,
                              source_contract=None, after_command=None):
        """Exercise receipt flow with inert byte fixtures; never invoke a tool."""
        self.clean_source_environment(SimpleNamespace(COMPILER_ENV=TARGET.COMPILER_ENV))
        paths, _, _ = self.program_fixture(base)
        compiler = base / "system/gcc"
        compiler.write_bytes(b"inert compiler fixture")
        build, out = base / "source-build", base / "out"
        build.mkdir()
        source, manifest = b"int main(void){return 0;}\n", b'{"fixture":true}\n'
        (build / "main.c").write_bytes(source)
        (build / "build.json").write_bytes(manifest)
        selected = TARGET.SourceInput("A", "test-p4", build, manifest, {}, {"main.c": source},
            TARGET.C_FLAGS["A"][1:], (), (), TARGET.pin(elf()),
            SimpleNamespace(source_contract=source_contract) if source_contract is not None else None)
        binary = {"path": str(compiler), **TARGET.pin(compiler.read_bytes())}
        context = {"kind": "ubuntu22-system", "input_roots": [str(base / "system")],
                   "wrapper": binary, "driver": binary}
        calls = []
        class InertHost:
            def __init__(self, *args):
                pass
            def run(self, command, *, cwd, kind, data=None):
                calls.append(kind)
                if after_command is not None:
                    after_command(kind)
                if kind == changed_env_at:
                    TARGET.os.environ["CPATH"] = "/fixture-after-query"
                if kind == "compiler-version":
                    return b"11.4.0\n"
                if kind == "compiler-banner":
                    return b"inert GCC fixture 11.4.0\n"
                if kind.startswith("compiler-program-"):
                    return (str(paths[command[1].split("=", 1)[1]]) + "\n").encode()
                if kind.startswith("A-"):
                    (cwd / "x").write_bytes(elf())
                    (cwd / "dependencies.d").write_bytes(b"x:\n")
                    return b""
                raise AssertionError("unexpected inert compiler command")
            def close(self):
                calls.append("close")
        def fixture_load(name, path):
            if name == "profile_compiler_verify":
                return VERIFY
            if name == "profile_compiler_host":
                return SimpleNamespace(Host=InertHost, LIMITS={})
            raise AssertionError("program-only mode loaded an unrelated helper")
        argv = [str(HERE / "profile_compiler.py"), "--build", str(build), "--compiler", str(compiler),
                "--ubuntu22-system", "--out", str(out)] + (["--program-provenance"] if program else [])
        with patch.object(TARGET.sys, "argv", argv), patch.object(TARGET.sys, "platform", "linux"), \
                patch.object(TARGET.platform, "machine", return_value="x86_64"), \
                patch.object(TARGET.platform, "platform", return_value="inert unit fixture"), \
                patch.object(TARGET.platform, "libc_ver", return_value=("glibc", "2.35")), \
                patch.object(TARGET.os, "sched_getaffinity", return_value={0}, create=True), \
                patch.object(TARGET.signal, "SIGCHLD", 17, create=True), \
                patch.object(TARGET.signal, "signal", return_value=0), \
                patch.object(TARGET, "load", side_effect=fixture_load), \
                patch.object(TARGET, "admit", return_value=selected), \
                patch.object(TARGET, "system_descriptor", return_value=context), \
                patch.object(TARGET, "source_provenance") as ci_source, patch("builtins.print"):
            TARGET.main()
            ci_source.assert_not_called()
        return json.loads((out / "compiler.json").read_bytes()), calls

    def test_program_only_receipt_rechecks_roles_without_synthesizing_ci_fields(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-program-only-") as temporary:
            report, calls = self.compiler_main_fixture(Path(temporary).resolve(), program=True)
            self.assertTrue(report["complete"])
            self.assertTrue(report["program_provenance"])
            self.assertTrue(report["compiler_programs_rechecked"])
            self.assertEqual(set(report["compiler_programs"]), set(TARGET.PROGRAM_ROLES))
            self.assertEqual(set(report["tools"]), {TARGET.SELF, TARGET.VERIFY_PATH, TARGET.HOST_PATH, TARGET.INPUT_PATH})
            self.assertTrue(all(row["path"] in report["compiler_consumed_inputs"]
                                for row in report["compiler_programs"].values()))
            self.assertEqual(calls[-6:-1], ["compiler-program-recheck-" + role for role in TARGET.PROGRAM_ROLES])
            self.assertLess(calls.index("A-target-types"), calls.index("compiler-program-recheck-cc1"))
            self.assertFalse(report["engine_executed"])
            self.assertFalse(report["submission_qualified"])
            for name in ("source_context", "source_bundle", "source_seal", "source_provenance_tools",
                         "source_profile", "source_provenance_rechecked"):
                self.assertNotIn(name, report)

    def test_default_system_receipt_keeps_original_query_count_and_shape(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-program-default-") as temporary:
            report, calls = self.compiler_main_fixture(Path(temporary).resolve(), program=False, source_contract={})
            self.assertTrue(report["complete"])
            self.assertNotIn("source_dependencies", report["profiles"][0])
            self.assertEqual([kind for kind in calls if kind.startswith("compiler-program-")],
                             ["compiler-program-" + role for role in TARGET.PROGRAM_ROLES])
            for name in ("program_provenance", "compiler_programs", "compiler_programs_rechecked",
                         "source_context", "source_bundle", "source_seal", "source_provenance_rechecked"):
                self.assertNotIn(name, report)

    def test_source_dependency_receipt_is_an_exact_independent_json_copy(self):
        record = {"declaration": {"name": "proof"}, "proof": {"complete": True, "scale": 1.0},
                  "attempts": [{"directory": "first", "dependency_gate": {"checked": True},
                                "native": {"bytes": 1, "sha256": "a" * 64}}],
                  "compiler_commands": [{"terminal": True, "stdout": {"bytes": 0},
                     "stderr": {"bytes": 0}, "stdin": {"name": "main.c", "bytes": 1, "sha256": "b" * 64}}]}
        expected = json.loads(json.dumps(record))
        def mutate_original(kind):
            if kind == "A-first":
                record["proof"]["complete"] = False
                record["attempts"][0]["native"]["bytes"] = True
                record["compiler_commands"][0]["stdin"]["name"] = "changed.c"
        with tempfile.TemporaryDirectory(prefix="rove4k-source-dependencies-") as temporary:
            report, _ = self.compiler_main_fixture(Path(temporary).resolve(), program=False,
                source_contract={"source_dependencies": record}, after_command=mutate_original)
        observed = report["profiles"][0]["source_dependencies"]
        self.assertEqual(observed, expected)
        self.assertIs(type(observed["proof"]["complete"]), bool)
        self.assertIs(type(observed["proof"]["scale"]), float)
        self.assertIs(type(observed["attempts"][0]["native"]["bytes"]), int)
        self.assertEqual(observed["compiler_commands"][0]["stdin"]["name"], "main.c")

    def test_program_mode_cannot_succeed_after_postquery_environment_injection(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-program-env-race-") as temporary:
            base = Path(temporary).resolve()
            with self.assertRaisesRegex(ValueError, "compiler redirection environment"):
                self.compiler_main_fixture(base, program=True, changed_env_at="compiler-program-recheck-lto1")
            report = json.loads((base / "out/compiler.json").read_bytes())
            self.assertFalse(report["complete"])
            self.assertFalse(report["compiler_programs_rechecked"])

    def provenance_fixture(self, base):
        # The public validator has its own archive/admission tests. Here its
        # response is isolated to test this producer's live/raw binding port.
        helper = TARGET.load("compiler_source_port_test_helper", HERE / "target_runtime.py")
        self.clean_source_environment(helper)
        ci = helper.CIContext("owner/repo", "a" * 40, "12", "1")
        bundle, seal = base / "source-bundle.zip", base / "source-seal.json"
        bundle.write_bytes(b"unit fixture source bundle")
        seal.write_bytes(b"unit fixture source seal")
        source = TARGET.normalized(HERE / "target_runtime.py")
        record = {"source_context": ci.to_record(), "source_bundle": TARGET.pin(bundle.read_bytes()),
                  "source_seal": TARGET.pin(seal.read_bytes()),
                  "source_provenance_tools": {TARGET.SOURCE_PROVENANCE: TARGET.pin(source),
                      TARGET.INPUT_PATH: TARGET.pin(TARGET.INPUT.source_identity())},
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
            self.assertEqual({name: TARGET.pin(data) for name, data in sources.items()},
                             record["source_provenance_tools"])
            binding.assert_called_once_with(selected.admission, selected.build, verify=verify,
                source_bundle=bundle, source_seal=seal, expected_ci=ci)

    def test_source_port_rejects_compiler_environment_contract_divergence(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-source-env-contract-") as temporary:
            helper, ci, bundle, seal, record, selected = self.provenance_fixture(Path(temporary).resolve())
            with patch.object(TARGET, "load", return_value=helper), \
                    patch.object(helper, "COMPILER_ENV", ()), \
                    patch.object(helper.CIContext, "from_environment") as live:
                with self.assertRaisesRegex(ValueError, "compiler environment contract differs"):
                    TARGET.source_provenance([selected], object(), bundle=bundle, seal=seal)
                live.assert_not_called()

    def test_source_port_rejects_missing_live_context_before_reading_raw_artifacts(self):
        helper = TARGET.load("compiler_source_port_missing_context", HERE / "target_runtime.py")
        self.clean_source_environment(helper)
        helper_source = TARGET.normalized(HERE / "target_runtime.py")
        with patch.object(TARGET, "load", return_value=helper), \
                patch.object(TARGET, "normalized", return_value=helper_source), \
                patch.object(helper.CIContext, "from_environment", side_effect=ValueError("live GitHub Actions context required")), \
                patch.object(TARGET, "regular") as read:
            with self.assertRaisesRegex(ValueError, "live GitHub Actions"):
                TARGET.source_provenance([SimpleNamespace()], object(),
                    bundle=HERE / "source-bundle.zip", seal=HERE / "source-seal.json")
            read.assert_not_called()

    def test_source_port_rejects_compiler_redirection_before_artifact_read(self):
        helper = TARGET.load("compiler_source_port_redirect", HERE / "target_runtime.py")
        self.clean_source_environment(helper)
        helper_source = TARGET.normalized(HERE / "target_runtime.py")
        with patch.object(TARGET, "load", return_value=helper), \
                patch.object(TARGET, "normalized", return_value=helper_source), \
                patch.object(TARGET, "regular") as read:
            for name in TARGET.COMPILER_ENV:
                with self.subTest(name=name), patch.dict(TARGET.os.environ, {name: "/not-an-admitted-context"}):
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
