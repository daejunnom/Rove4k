"""Small synthetic contract tests; no upstream engine sources are included."""
from __future__ import annotations

import sys
import os
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import original_peer_build as subject


class OriginalPeerBuildTests(unittest.TestCase):
    def setUp(self):
        self.files = {"src/main.cpp": b"synthetic main\n"}
        self.files.update({f"src/file-{index}.cpp": f"synthetic {index}\n".encode() for index in range(4)})
        self.pins = {name: subject.peers.git_blob(data) for name, data in self.files.items()}
        self.patcher = patch.dict(subject.peers.SOURCE_BLOBS, {"c4ke": self.pins})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_original_identity_profiles_and_unqualified_scope(self):
        for profile, workers, mib, extent in (("test-p16", 16, 16384, 16 << 30),
                                              ("test-p192", 192, 262144, 256 << 30)):
            record = subject.source_record("c4ke", profile, self.files)
            self.assertEqual(record["requested_uci"], {"workers": workers, "hash_mib": mib,
                "expected_tt_bytes_if_entry8": extent})
            self.assertEqual(set(record["source"]), set(self.files))
            self.assertTrue(record["build"]["planning_only"])
            self.assertFalse(record["build"]["execution_available"])
            self.assertEqual(len(record["build"]["blockers"]), 3)
            self.assertTrue(record["qualification"]["source_blob_identity_checked"])
            self.assertFalse(record["qualification"]["source_to_native_proven"])
            self.assertFalse(record["qualification"]["tt_abi_verified"])
            self.assertFalse(record["qualification"]["runtime_qualified"])
            self.assertFalse(record["qualification"]["league_qualified"])
            self.assertFalse(record["qualification"]["scored_game_admitted"])
            self.assertNotIn("size_within_4096", record["qualification"])

    def test_original_bytes_and_closure_are_required(self):
        cases = [dict(self.files, **{"src/main.cpp": b"tampered"}),
                 {k: v for k, v in self.files.items() if k != "src/main.cpp"},
                 dict(self.files, **{"src/unpinned.cpp": b"extra"}),
                 dict(self.files, **{"src/main.cpp": "not bytes"})]
        for files in cases:
            with self.subTest(files=files), self.assertRaises(ValueError):
                subject.source_record("c4ke", "test-p16", files)
        with self.assertRaises(ValueError):
            subject.source_record("c4ke", "submit-w256", self.files)

    def test_exact_upstream_flags_and_private_outputs(self):
        self.assertEqual(subject.compile_argv("ice4", "peer-native-1"),
                         ["g++", "-DOPENBENCH", "-g", "-O3", "-pthread",
                          "src/main.cpp", "-o", "peer-native-1"])
        self.assertEqual(subject.compile_argv("c4ke", "peer-native-2"),
                         ["g++", "-DNDEBUG", "-std=c++23", "-O3", "-march=native", "-pthread",
                          "src/main.cpp", "-o", "peer-native-2"])
        for output in ("../../engine", "peer-native-3", "/tmp/bin", "peer-native-1\nquit"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                subject.compile_argv("c4ke", output)

    def test_test_source_has_no_4k_size_gate(self):
        files = dict(self.files)
        files["src/main.cpp"] = b"x" * 5000
        pins = {name: subject.peers.git_blob(data) for name, data in files.items()}
        with patch.dict(subject.peers.SOURCE_BLOBS, {"c4ke": pins}):
            record = subject.source_record("c4ke", "test-p16", files)
        self.assertEqual(record["source"]["src/main.cpp"]["bytes"], 5000)
        self.assertFalse(record["qualification"]["scored_game_admitted"])

    def test_protected_paths_rejected_before_filesystem_lookup(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-peer-") as tmp:
            for name in (".env.production", "secret-data", "access_key", "build", "private.pem"):
                with self.subTest(name=name), patch.object(subject.os, "lstat") as lstat:
                    with self.assertRaises(ValueError):
                        subject._outside_checkout(Path(tmp) / name)
                    lstat.assert_not_called()

    @unittest.skipUnless(sys.platform == "linux", "no-follow dirfd boundary requires Linux")
    def test_snapshot_preserves_verified_unmodified_files_without_size_gate(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-peer-") as tmp:
            root = Path(tmp)
            source, out = root / "source", root / "candidate"
            (source / "src").mkdir(parents=True)
            for name, raw in self.files.items():
                (source / name).write_bytes(raw)

            result = subject.prepare("c4ke", "test-p192", source, out)
            for name, raw in self.files.items():
                self.assertEqual((out / name).read_bytes(), raw)
            self.assertNotIn("size_within_4096", result["qualification"])
            self.assertFalse(result["qualification"]["runtime_qualified"])
            self.assertFalse(result["qualification"]["scored_game_admitted"])
            self.assertTrue((out / "source-snapshot.json").is_file())

    @unittest.skipUnless(sys.platform == "linux", "no-follow dirfd boundary requires Linux")
    def test_rejects_linked_source_before_output_creation(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-peer-") as tmp:
            root = Path(tmp)
            source = root / "source"
            (source / "src").mkdir(parents=True)
            for name, raw in self.files.items():
                (source / name).write_bytes(raw)
            alias = root / "source-alias"
            alias.symlink_to(source, target_is_directory=True)
            with self.assertRaises(OSError):
                subject.prepare("c4ke", "test-p16", alias, root / "bad")
            self.assertFalse((root / "bad").exists())

    @unittest.skipUnless(sys.platform == "linux", "no-follow dirfd boundary requires Linux")
    def test_rejects_hardlinked_input_and_git_checkout_paths(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-peer-") as tmp:
            root = Path(tmp)
            source = root / "source"
            (source / "src").mkdir(parents=True)
            for name, raw in self.files.items():
                (source / name).write_bytes(raw)
            os.link(source / "src/main.cpp", root / "hardlink")
            with self.assertRaises(ValueError):
                subject.prepare("c4ke", "test-p16", source, root / "out")
            self.assertFalse((root / "out").exists())
            (root / "checkout" / ".git").mkdir(parents=True)
            with self.assertRaises(ValueError):
                subject._outside_checkout(root / "checkout" / "candidate")

    def test_build_rejects_protected_input_without_starting_a_process(self):
        cpu = min(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else 0
        with patch.object(subject.peer_exact_runner, "run") as run:
            with self.assertRaises(ValueError):
                subject.build("c4ke", "test-p192", "/.env.private", "/not-created", cpu=cpu)
        run.assert_not_called()


@unittest.skipUnless(sys.platform == "linux", "Linux no-follow dirfd boundary required")
class OriginalPeerNativeBuildTests(unittest.TestCase):
    """Build policy with a simulated compiler; no peer source or native runs."""

    def setUp(self):
        self.cpu = min(os.sched_getaffinity(0))
        self.files = {"src/main.cpp": b"synthetic main\n"}
        self.files.update({f"src/file-{index}.cpp": f"synthetic {index}\n".encode() for index in range(4)})
        self.pins = {name: subject.peers.git_blob(data) for name, data in self.files.items()}
        self.patcher = patch.dict(subject.peers.SOURCE_BLOBS, {"c4ke": self.pins})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def fixture(self, root):
        source = root / "input"
        (source / "src").mkdir(parents=True)
        for name, data in self.files.items():
            (source / name).write_bytes(data)
        compiler = root / "compiler"
        compiler.write_bytes(b"synthetic compiler executable")
        return source, root / "output", compiler

    @staticmethod
    def compiler(path):
        data = path.read_bytes()
        return str(path), hashlib.sha256(data).hexdigest(), len(data), os.open(path, os.O_RDONLY)

    @staticmethod
    def settled_record():
        return {"exit_code": 0, "leader_reaped": True, "group_absent": True,
                "original_group_empty_observed_before_reap": True,
                "physical_group_settlement_proven": False}

    def test_invalid_cpu_and_timeout_are_rejected_before_output_or_runner(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-native-") as tmp:
            root = Path(tmp)
            source, out = root / "not-opened", root / "not-created"
            cases = ((True, 60), (-1, 60), (max(os.sched_getaffinity(0)) + 1, 60),
                     (self.cpu, 0), (self.cpu, True), (self.cpu, float("nan")),
                     (self.cpu, 3601))
            with patch.object(subject, "_prepare_at") as prepare, \
                    patch.object(subject, "_open_compiler") as compiler, \
                    patch.object(subject.peer_exact_runner, "run") as run:
                for cpu, timeout in cases:
                    with self.subTest(cpu=cpu, timeout=timeout), self.assertRaises(ValueError):
                        subject.build("c4ke", "test-p16", source, out, cpu=cpu, timeout=timeout)
                    self.assertFalse(out.exists())
                prepare.assert_not_called()
                compiler.assert_not_called()
                run.assert_not_called()

    def test_two_owned_builds_keep_upstream_source_and_do_not_authorize_runtime(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-native-") as tmp:
            source, out, compiler = self.fixture(Path(tmp))
            calls = []

            def fake_run(command, cwd, **kwargs):
                calls.append((command, cwd, kwargs))
                self.assertEqual(Path(cwd), out)
                self.assertEqual(kwargs["cwd_anchor"], "work")
                self.assertEqual(set(kwargs["fd_anchors"]), {"work", "compiler", "output"})
                self.assertIn("src/main.cpp", command)
                self.assertIn("/proc/self/fd/{fd:output}", command)
                self.assertIn("-DNDEBUG", command)
                self.assertEqual((out / "src/main.cpp").read_bytes(), self.files["src/main.cpp"])
                os.write(kwargs["fd_anchors"]["output"][0], b"synthetic native")
                return b"", b"", self.settled_record()

            with patch.object(subject, "_open_compiler", side_effect=lambda: self.compiler(compiler)), \
                    patch.object(subject.peer_exact_runner, "run", side_effect=fake_run), \
                    patch.object(subject, "_validate_native") as validate:
                result = subject.build("c4ke", "test-p16", source, out, cpu=self.cpu)
            self.assertEqual(len(calls), 2)
            validate.assert_called()
            self.assertEqual(Path(result["path"]), out / "original-peer-build.json")
            self.assertTrue(result["record"]["complete"])
            self.assertTrue(result["record"]["same_host_native_reproduced"])
            self.assertFalse(result["record"]["source_modified_by_builder"])
            self.assertFalse(result["record"]["concurrent_source_mutation_excluded"])
            snapshot = json.loads((out / "source-snapshot.json").read_text(encoding="utf-8"))
            self.assertTrue(snapshot["build"]["planning_only"])
            self.assertFalse(snapshot["build"]["execution_available"])
            for key in ("source_to_native_proven", "tt_abi_verified", "runtime_qualified",
                        "league_qualified", "scored_game_admitted"):
                self.assertFalse(result["record"]["qualification"][key])
            for name, data in self.files.items():
                self.assertEqual((out / name).read_bytes(), data)
            self.assertEqual((out / "peer-native-1").read_bytes(), (out / "peer-native-2").read_bytes())

    def test_both_build_records_retain_requested_uci_without_claiming_configuration(self):
        cases = (("test-p16", 16, 16384, 16 << 30),
                 ("test-p192", 192, 262144, 256 << 30))
        with tempfile.TemporaryDirectory(prefix="rove-original-resources-") as tmp:
            for profile, workers, hash_mib, extent in cases:
                with self.subTest(profile=profile):
                    root = Path(tmp) / profile
                    root.mkdir()
                    source, out, compiler = self.fixture(root)

                    def fake_run(command, cwd, **kwargs):
                        os.write(kwargs["fd_anchors"]["output"][0], b"synthetic native")
                        return b"", b"", self.settled_record()

                    with patch.object(subject, "_open_compiler", side_effect=lambda: self.compiler(compiler)), \
                            patch.object(subject.peer_exact_runner, "run", side_effect=fake_run), \
                            patch.object(subject, "_validate_native"):
                        result = subject.build("c4ke", profile, source, out, cpu=self.cpu)
                    record = result["record"]
                    snapshot = json.loads((out / "source-snapshot.json").read_text(encoding="utf-8"))
                    expected = {"workers": workers, "hash_mib": hash_mib,
                                "expected_tt_bytes_if_entry8": extent}
                    self.assertEqual(snapshot["requested_uci"], expected)
                    self.assertEqual(record["requested_uci"], expected)
                    self.assertFalse(record["uci_setup_performed"])
                    self.assertEqual(record["engines_executed"], 0)
                    for key in ("tt_abi_verified", "allocation_observed", "runtime_qualified",
                                "league_qualified", "scored_game_admitted"):
                        self.assertFalse(record["qualification"][key])

    def test_mismatched_native_builds_never_get_success_receipt(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-native-") as tmp:
            source, out, compiler = self.fixture(Path(tmp))
            calls = []

            def fake_run(command, cwd, **kwargs):
                calls.append(1)
                os.write(kwargs["fd_anchors"]["output"][0], bytes(calls))
                return b"", b"", self.settled_record()

            with patch.object(subject, "_open_compiler", side_effect=lambda: self.compiler(compiler)), \
                    patch.object(subject.peer_exact_runner, "run", side_effect=fake_run), \
                    patch.object(subject, "_validate_native"):
                with self.assertRaisesRegex(ValueError, "native attempts differ"):
                    subject.build("c4ke", "test-p16", source, out, cpu=self.cpu)
            self.assertEqual(len(calls), 2)
            self.assertFalse((out / "original-peer-build.json").exists())

    def test_source_modified_during_build_is_rejected_without_success_receipt(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-native-") as tmp:
            source, out, compiler = self.fixture(Path(tmp))

            def fake_run(command, cwd, **kwargs):
                os.write(kwargs["fd_anchors"]["output"][0], b"synthetic native")
                (out / "src/main.cpp").write_bytes(b"tampered")
                return b"", b"", self.settled_record()

            with patch.object(subject, "_open_compiler", side_effect=lambda: self.compiler(compiler)), \
                    patch.object(subject.peer_exact_runner, "run", side_effect=fake_run), \
                    patch.object(subject, "_validate_native"):
                with self.assertRaisesRegex(ValueError, "snapshot changed"):
                    subject.build("c4ke", "test-p16", source, out, cpu=self.cpu)
            self.assertFalse((out / "original-peer-build.json").exists())

    def test_replaced_output_inode_is_rejected_even_with_identical_bytes(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-native-") as tmp:
            source, out, compiler = self.fixture(Path(tmp))

            def fake_run(command, cwd, **kwargs):
                os.write(kwargs["fd_anchors"]["output"][0], b"synthetic native")
                path = out / "peer-native-1"
                path.rename(out / "moved-original-native")
                path.write_bytes(b"synthetic native")
                return b"", b"", self.settled_record()

            with patch.object(subject, "_open_compiler", side_effect=lambda: self.compiler(compiler)), \
                    patch.object(subject.peer_exact_runner, "run", side_effect=fake_run), \
                    patch.object(subject, "_validate_native"):
                with self.assertRaises((OSError, ValueError)):
                    subject.build("c4ke", "test-p16", source, out, cpu=self.cpu)
            self.assertEqual((out / "moved-original-native").read_bytes(), b"synthetic native")
            self.assertFalse((out / "original-peer-build.json").exists())

    def test_output_symlink_replacement_does_not_touch_its_target(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-native-") as tmp:
            root = Path(tmp)
            source, out, compiler = self.fixture(root)
            target = root / "unrelated"
            target.write_bytes(b"preserve")

            def fake_run(command, cwd, **kwargs):
                os.write(kwargs["fd_anchors"]["output"][0], b"synthetic native")
                path = out / "peer-native-1"
                path.rename(out / "moved-original-native")
                path.symlink_to(target)
                return b"", b"", self.settled_record()

            with patch.object(subject, "_open_compiler", side_effect=lambda: self.compiler(compiler)), \
                    patch.object(subject.peer_exact_runner, "run", side_effect=fake_run), \
                    patch.object(subject, "_validate_native"):
                with self.assertRaises((OSError, ValueError)):
                    subject.build("c4ke", "test-p16", source, out, cpu=self.cpu)
            self.assertEqual(target.read_bytes(), b"preserve")
            self.assertFalse((out / "original-peer-build.json").exists())

    def test_forged_physical_settlement_claim_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-native-") as tmp:
            source, out, compiler = self.fixture(Path(tmp))

            def fake_run(command, cwd, **kwargs):
                os.write(kwargs["fd_anchors"]["output"][0], b"synthetic native")
                record = self.settled_record()
                record["physical_group_settlement_proven"] = True
                return b"", b"", record

            with patch.object(subject, "_open_compiler", side_effect=lambda: self.compiler(compiler)), \
                    patch.object(subject.peer_exact_runner, "run", side_effect=fake_run), \
                    patch.object(subject, "_validate_native"):
                with self.assertRaises(ValueError):
                    subject.build("c4ke", "test-p16", source, out, cpu=self.cpu)
            self.assertFalse((out / "original-peer-build.json").exists())

    def test_unsettled_original_group_retains_only_its_owned_fds_without_receipt(self):
        with tempfile.TemporaryDirectory(prefix="rove-original-native-") as tmp:
            source, out, compiler = self.fixture(Path(tmp))
            marker = object()
            previous_quarantine_count = len(subject._ORIGINAL_QUARANTINE)
            captured = []

            def fake_run(command, cwd, **kwargs):
                captured.extend(item[0] for item in kwargs["fd_anchors"].values())
                # This is a test-owned marker, not a real child or process.
                subject.peer_exact_runner._UNSETTLED[marker] = {"synthetic": True}
                raise subject.peer_exact_runner.GroupUnsettled("synthetic unsettled group")

            try:
                with patch.object(subject, "_open_compiler", side_effect=lambda: self.compiler(compiler)), \
                        patch.object(subject.peer_exact_runner, "run", side_effect=fake_run):
                    with self.assertRaises(subject.peer_exact_runner.GroupUnsettled):
                        subject.build("c4ke", "test-p16", source, out, cpu=self.cpu)
                self.assertFalse((out / "original-peer-build.json").exists())
                self.assertEqual(len(subject._ORIGINAL_QUARANTINE), previous_quarantine_count + 1)
                retained = subject._ORIGINAL_QUARANTINE[-1]
                self.assertEqual(retained["reason"], "ownership-unsettled")
                self.assertTrue(set(captured).issubset(set(retained["fds"])))
                for fd in retained["fds"]:
                    os.fstat(fd)
            finally:
                # No child is started in this test. Remove only our own fake
                # marker and close only descriptors this test caused to exist.
                subject.peer_exact_runner._UNSETTLED.pop(marker, None)
                while len(subject._ORIGINAL_QUARANTINE) > previous_quarantine_count:
                    retained = subject._ORIGINAL_QUARANTINE.pop()
                    for fd in set(retained["fds"]):
                        os.close(fd)


@unittest.skipUnless(sys.platform == "linux" and hasattr(os, "sched_getaffinity") and shutil.which("g++"),
                     "Linux, CPU affinity and g++ required")
class OriginalPeerRealCompileTests(unittest.TestCase):
    """Compile synthetic input only; never execute a produced binary or peer."""

    def test_upstream_flags_compile_synthetic_include_closures_twice(self):
        # Preserve this private workspace. Original-group observation does not
        # prove that descendants which escaped the group have stopped using it.
        root = Path(tempfile.mkdtemp(prefix="rove-original-real-cc-")).resolve()
        cpu = min(os.sched_getaffinity(0))
        for peer, profile, count in (("ice4", "test-p16", 8), ("c4ke", "test-p192", 5)):
            with self.subTest(peer=peer, profile=profile):
                source = root / (peer + "-input")
                (source / "src").mkdir(parents=True)
                files = {f"src/file-{index}.cpp": f"static constexpr int v{index} = {index};\n".encode()
                         for index in range(count - 1)}
                includes = "".join(f'#include "file-{index}.cpp"\n' for index in range(count - 1))
                files["src/main.cpp"] = (includes + "int main() { return v0; }\n").encode()
                for name, data in files.items():
                    (source / name).write_bytes(data)
                pins = {name: subject.peers.git_blob(data) for name, data in files.items()}
                out = root / (peer + "-output")
                with patch.dict(subject.peers.SOURCE_BLOBS, {peer: pins}):
                    result = subject.build(peer, profile, source, out, cpu=cpu, timeout=45)
                record = result["record"]
                self.assertTrue(record["complete"])
                self.assertTrue(record["same_host_native_reproduced"])
                self.assertEqual(record["engines_executed"], 0)
                self.assertFalse(record["source_modified_by_builder"])
                self.assertFalse(record["concurrent_source_mutation_excluded"])
                self.assertEqual(record["compiler"]["flags"], list(subject._FLAGS[peer]))
                self.assertEqual(len(record["attempts"]), 2)
                self.assertEqual(record["attempts"][0]["sha256"], record["attempts"][1]["sha256"])
                self.assertTrue(all(not row["command"]["physical_group_settlement_proven"]
                                    for row in record["attempts"]))
                self.assertFalse(any(record["qualification"][key] for key in
                                     ("tt_abi_verified", "allocation_observed", "runtime_qualified",
                                      "league_qualified", "scored_game_admitted")))
                for name, data in files.items():
                    self.assertEqual((out / name).read_bytes(), data)
                self.assertEqual((out / "peer-native-1").read_bytes(), (out / "peer-native-2").read_bytes())


if __name__ == "__main__":
    unittest.main()
