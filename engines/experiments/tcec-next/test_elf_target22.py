"""Pure boundaries for original-ELF transport; no compiler, loader or engine."""
import copy
import importlib.util
import io
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile


HERE = Path(__file__).resolve().parent


def source_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


target = source_module("original_elf_target_tests", HERE / "elf_target22.py")


def environment():
    return dict(GITHUB_ACTIONS="true", GITHUB_REPOSITORY="owner/engine", GITHUB_SHA="a" * 40,
        GITHUB_RUN_ID="123", GITHUB_RUN_ATTEMPT="2", GITHUB_REF="refs/pull/12/merge",
        GITHUB_WORKFLOW_REF="owner/engine/.github/workflows/elf-profiles.yml@refs/pull/12/merge")


def transport_modules():
    root = HERE.parents[2]
    return {"transport": source_module("elf22_test_transport", root / target.TRANSPORT),
            "target": source_module("elf22_test_bounds", root / target.TARGET)}


def small_bundle(m):
    values = {"build/main.c": b"int main(void){return 0;}\n", "build/x": b"inert ELF transport bytes"}
    stamps = {name: (0, 0, stat.S_IFREG | (0o755 if name.endswith("/x") else 0o644)) for name in values}
    data = m["transport"]._zip_bytes(values, stamps)
    return values, stamps, data, target.members_record(values, stamps)


class OriginalElfTarget(unittest.TestCase):
    def test_inactive_actions_do_not_capture_or_read(self):
        with patch.object(target, "capture", side_effect=AssertionError("must not capture")) as capture, \
                patch.object(target, "read", side_effect=AssertionError("must not read")) as read:
            with self.assertRaisesRegex(ValueError, "inactive"):
                target.export_bundle(Path("/unused/build"), Path("/unused/out"))
            with self.assertRaisesRegex(ValueError, "inactive"):
                target.consume(Path("/unused/elf-bundle.zip"), Path("/unused/elf-seal.json"), Path("/unused/out"))
            capture.assert_not_called()
            read.assert_not_called()

    def test_submission_gate_precedes_capture_zip_admission_and_memory(self):
        rejected = dict(family="A", profile="tcec-provisional", native_variant="lean")
        with patch.object(target, "capture", side_effect=AssertionError("must not capture")) as capture, \
                patch.object(target, "context", side_effect=AssertionError("must not inspect context")) as ci:
            with patch.object(target, "read", return_value=target.encoded(rejected)):
                with self.assertRaisesRegex(ValueError, "TEST-P4/P28"):
                    target.export_bundle(Path("/unused/build"), Path("/unused/out"), execute=True)
            with patch.object(target, "read", return_value=target.encoded(dict(selection=rejected))) as read:
                with self.assertRaisesRegex(ValueError, "TEST-P4/P28"):
                    target.consume(Path("/unused/elf-bundle.zip"), Path("/unused/elf-seal.json"),
                                   Path("/unused/out"), execute=True)
                self.assertEqual(read.call_count, 1)
            capture.assert_not_called()
            ci.assert_not_called()

    def test_finite_test_profiles_and_actual_ci_identity(self):
        for family in "ABCEF":
            for profile in ("test-p4", "test-p28"):
                for variant in ("baseline", "lean"):
                    value = dict(family=family, profile=profile, native_variant=variant)
                    self.assertEqual(target.selection(value), value)
        for key, value in (("family", "D"), ("family", "F8"), ("profile", True), ("native_variant", "other")):
            changed = dict(family="F", profile="test-p4", native_variant="lean")
            changed[key] = value
            with self.assertRaises(ValueError):
                target.selection(changed)
        ci = environment()
        self.assertEqual(target.context(ci)["GITHUB_SHA"], "a" * 40)
        for key, value in (("GITHUB_SHA", "a" * 39), ("GITHUB_ACTIONS", "false"),
                           ("GITHUB_RUN_ATTEMPT", "0"), ("GITHUB_RUN_ID", "12x"),
                           ("GITHUB_WORKFLOW_REF", "owner/engine/.github/workflows/other.yml@refs/pull/12/merge")):
            changed = dict(ci)
            changed[key] = value
            with self.assertRaises(ValueError):
                target.context(changed)

    def test_loader_output_is_exact_resolution_data(self):
        output = (b"\tlinux-vdso.so.1 (0x7f000000)\n"
                  b"\tlibc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x7f000001)\n"
                  b"\t/lib64/ld-linux-x86-64.so.2 (0x7f000002)\n")
        self.assertEqual(target.parse_resolution(output), {
            "libc.so.6": "/lib/x86_64-linux-gnu/libc.so.6", "ld-linux-x86-64.so.2": "/lib64/ld-linux-x86-64.so.2"})
        for bad in (b"", b"libc.so.6 => not found\n", b"statically linked\n", output + output,
                    b"libc.so.6 => relative/libc.so.6 (0x7f01)\n", b"\xff\n"):
            with self.assertRaises((ValueError, UnicodeDecodeError)):
                target.parse_resolution(bad)
        paths = {"/lib/x86_64-linux-gnu": ("libc.so*",)}
        self.assertTrue(target.allowed_path("/lib/x86_64-linux-gnu/libc.so.6", paths))
        self.assertFalse(target.allowed_path("/tmp/libc.so.6", paths))
        with self.assertRaises(ValueError):
            target.allowed_path("/lib/../tmp/libc.so.6", paths)

    def test_deterministic_zip_roundtrip_and_exact_member_identity(self):
        m = transport_modules()
        values, stamps, data, manifest = small_bundle(m)
        restored, modes = target.decode_bundle(data, manifest, m)
        self.assertEqual(restored, values)
        self.assertEqual(modes, {"build/main.c": 0o644, "build/x": 0o755})
        self.assertEqual(m["transport"]._zip_bytes(values, stamps), data)
        for key, value in (("bytes", 1), ("sha256", "0" * 64), ("mode", 0o600)):
            changed = copy.deepcopy(manifest)
            changed["build/x"][key] = value
            with self.assertRaises(ValueError):
                target.decode_bundle(data, changed, m)
        changed = dict(manifest)
        changed.pop("build/x")
        with self.assertRaises(ValueError):
            target.decode_bundle(data, changed, m)
        with self.assertRaises(ValueError):
            target.decode_bundle(data + b"unowned trailing bytes", manifest, m)

    def test_zip_link_escape_and_wrong_root_reject_before_member_read(self):
        m = transport_modules()
        unused_values, unused_stamps, unused_data, manifest = small_bundle(m)
        for name, mode in (("build/x", stat.S_IFLNK | 0o777), ("../escape", stat.S_IFREG | 0o644),
                           ("other/x", stat.S_IFREG | 0o644)):
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = mode << 16
                archive.writestr(info, b"inert")
            with patch.object(zipfile.ZipFile, "read", side_effect=AssertionError("must reject metadata first")):
                with self.assertRaises(ValueError):
                    target.decode_bundle(output.getvalue(), manifest, m)

    @unittest.skipUnless(os.name == "posix", "descriptor reader is a POSIX target contract")
    def test_metadata_reader_refuses_links_hardlinks_and_oversized_extent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            path = root / "record.json"
            path.write_bytes(b"ordinary data")
            self.assertEqual(target.read(path, 64), b"ordinary data")
            with self.assertRaises(ValueError):
                target.read(path, 1)
            alias = root / "alias.json"
            alias.symlink_to(path)
            with self.assertRaises(OSError):
                target.read(alias, 64)
            alias.unlink()
            os.link(path, alias)
            with self.assertRaises(ValueError):
                target.read(path, 64)

    def test_cli_keeps_execution_opt_in(self):
        # The public action must remain explicitly opt-in; this test never
        # dispatches its nested rules/runtime commands or constructs an owner.
        with patch.object(target, "consume", return_value=dict(action="consume", complete=False)) as consume:
            target.main(["consume", "--bundle", "/unused/elf-bundle.zip", "--seal", "/unused/elf-seal.json",
                         "--out", "/unused/target"])
            self.assertIs(consume.call_args.kwargs["execute"], False)


    @unittest.skipUnless(os.name == "posix", "transport resource query is POSIX-only")
    def test_transport_artifact_domain_never_raises_inherited_file_limits(self):
        import resource
        larger_than_tool_file = (8 << 20) + 1
        with patch.object(resource, "getrlimit", return_value=(-1, -1)), \
                patch.object(resource, "setrlimit", side_effect=AssertionError("must not raise transport limits")) as change:
            raw = target.transport_file_limits((larger_than_tool_file,), maximum=target.MAX_BUNDLE)
            member = target.transport_file_limits((larger_than_tool_file,), maximum=target.MAX_MEMBER)
            self.assertEqual(raw["largest_file_bytes"], larger_than_tool_file)
            self.assertEqual(member["declared_maximum_bytes"], 16 << 20)
            self.assertIs(raw["inherited_limit_raised"], False)
            for extent, maximum in (((128 << 20) + 1, target.MAX_BUNDLE),
                                     ((16 << 20) + 1, target.MAX_MEMBER)):
                with self.assertRaises(ValueError):
                    target.transport_file_limits((extent,), maximum=maximum)
            change.assert_not_called()
        with patch.object(resource, "getrlimit", return_value=(8 << 20, 8 << 20)), \
                patch.object(resource, "setrlimit", side_effect=AssertionError("must not raise inherited cap")) as change:
            with self.assertRaisesRegex(ValueError, "inherited file limit"):
                target.transport_file_limits((larger_than_tool_file,), maximum=target.MAX_BUNDLE)
            with self.assertRaisesRegex(ValueError, "inherited file limit"):
                target.transport_file_limits((larger_than_tool_file,), maximum=target.MAX_MEMBER)
            change.assert_not_called()

    def test_both_transport_roles_prepare_before_host_tool_caps(self):
        for role in ("export", "consume"):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as temporary:
                out = Path(temporary) / "operation"
                events = []
                ci = {"role": role}
                report = dict(complete=False, commands=[], ci_context=ci)
                owner = SimpleNamespace(LIMITS={"original": 7})
                host = SimpleNamespace(out=out)

                def construct(*args):
                    events.append("host-tool-caps")
                    self.assertEqual(events, ["artifact-prepare", "host-tool-caps"])
                    return owner, {"original": 7}, host

                def finish(actual, observed, save, error):
                    events.append("settlement")
                    self.assertIs(actual, host)
                    self.assertIsNone(error)
                    observed.update(complete=True, host_cleanup={"unsettled_commands": 0, "errors": []})
                    save()

                def prepare(m, save):
                    self.assertIs(report["host_constructed"], False)
                    self.assertEqual(report["operation_stage"], "transport-artifacts-before-tool-limits")
                    events.append("artifact-prepare")

                E = SimpleNamespace(UTILITY="fixture-utility")
                with patch.object(target, "modules", return_value={}), \
                        patch.object(target, "write"), \
                        patch.object(target, "load", return_value=SimpleNamespace(finish_report=finish)), \
                        patch.object(target, "host_for", side_effect=construct), \
                        patch.object(target, "git_binding", side_effect=lambda *args: events.append("checkout")), \
                        patch.object(target, "recheck"), patch.object(target, "context", return_value=ci), \
                        patch.object(target.signal, "signal", return_value=None):
                    result = target._operation(out, E, {E.UTILITY: b""}, report, 0,
                        lambda *args: events.append("body"), prepare=prepare)
                self.assertIs(result["complete"], True)
                self.assertEqual(events, ["artifact-prepare", "host-tool-caps", "checkout", "body", "settlement"])

    def test_transport_preparation_failure_keeps_original_error_before_host(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "operation"
            report = dict(complete=False, commands=[], ci_context={})
            primary = OSError(27, "original partial raw-archive failure")
            seen = []

            def prepare(m, save):
                (out / target.BUNDLE).write_bytes(b"partial archive evidence")
                raise primary

            def finish(host, observed, save, error):
                self.assertIsNone(host)
                self.assertIs(error, primary)
                seen.append(error)
                observed["complete"] = False
                save()

            E = SimpleNamespace(UTILITY="fixture-utility")
            with patch.object(target, "modules", return_value={}), \
                    patch.object(target, "write"), \
                    patch.object(target, "load", return_value=SimpleNamespace(finish_report=finish)), \
                    patch.object(target, "host_for", side_effect=AssertionError("must not construct Host")) as host, \
                    patch.object(target, "git_binding", side_effect=AssertionError("must not run git")), \
                    patch.object(target.signal, "signal", return_value=None), \
                    self.assertRaises(OSError) as caught:
                target._operation(out, E, {E.UTILITY: b""}, report, 0,
                                  lambda *args: self.fail("must not execute body"), prepare=prepare)
            self.assertIs(caught.exception, primary)
            host.assert_not_called()
            self.assertEqual(seen, [primary])
            self.assertEqual((out / target.BUNDLE).read_bytes(), b"partial archive evidence")
            self.assertFalse((out / target.SEAL).exists())
            result = target.json.loads((out / "result.json").read_bytes())
            self.assertIs(result["complete"], False)
            self.assertIs(result["host_constructed"], False)
            self.assertEqual(result["failure"]["type"], "OSError")


if __name__ == "__main__":
    unittest.main()
