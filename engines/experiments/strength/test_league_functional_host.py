"""Offline functional-host lifecycle tests; no cgroups or engines are started."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

try:
    from . import league_functional_host as host
except ImportError:
    import league_functional_host as host


class FakeProbe:
    def __init__(self, arguments, *, fail=False, cleanup_error=False, invalid_report=False,
                 interrupted=False, report_mode="normal", failed_report=False):
        self.arguments = arguments
        self.fail = fail
        self.cleanup_error = cleanup_error
        self.invalid_report = invalid_report
        self.interrupted = interrupted
        self.report_mode = report_mode
        self.failed_report = failed_report
        self.closed = False
        self.manager = SimpleNamespace(created=[])

    def run(self):
        if self.interrupted:
            raise KeyboardInterrupt("injected interruption")
        if self.fail:
            raise RuntimeError("injected diagnostic failure")
        out = Path(self.arguments["out"])
        out.mkdir(mode=0o700)
        report = {"format": "rove4k-functional-candidate-v1",
                  "profile": self.arguments["profile"],
                  "artifact_id": self.arguments["artifact_id"],
                  "candidate_set_sha256": self.arguments["candidate_sha256"],
                  "complete": not (self.invalid_report or self.failed_report),
                  "scored_game_admitted": False}
        path = out / "functional-runtime.json"
        if self.report_mode == "symlink":
            target = out / "other.json"
            target.write_text(json.dumps(report), encoding="utf-8")
            path.symlink_to(target)
        elif self.report_mode == "hardlink":
            target = out / "other.json"
            target.write_text(json.dumps(report), encoding="utf-8")
            os.link(target, path)
        elif self.report_mode != "missing":
            path.write_text(json.dumps(report), encoding="utf-8")
        if self.failed_report:
            raise RuntimeError("injected failure with report")
        return report

    def close(self):
        self.closed = True
        return [{"error": "injected unresolved owner"}] if self.cleanup_error else []


class FunctionalHostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.state = self.base / "state"
        self.state.mkdir(mode=0o700)
        os.chmod(self.state, 0o700)
        self.root = self.base / "delegated"
        self.root.mkdir()
        self.candidates = self.base / "candidates.json"
        self.candidates.write_text('{"fixture":true}', encoding="utf-8")
        self.out = self.base / "out"
        self.unrelated = self.base / "keep"
        self.unrelated.write_bytes(b"user data")
        self.sha = hashlib.sha256(self.candidates.read_bytes()).hexdigest()
        self.calls = []
        self.options = {}

    def factory(self, **kwargs):
        probe = FakeProbe(kwargs, **self.options)
        self.calls.append(probe)
        return probe

    def execute(self, **changes):
        args = dict(state_dir=self.state, root=self.root, campaign="league-2026",
                    candidates=self.candidates, candidates_sha256=self.sha,
                    profile="test-p16", artifact="candidate-a", out=self.out,
                    wall_seconds=120, _probe_factory=self.factory)
        args.update(changes)
        return host.run(**args)

    def assert_user_files_unchanged(self):
        self.assertEqual(self.unrelated.read_bytes(), b"user data")
        self.assertEqual(hashlib.sha256(self.candidates.read_bytes()).hexdigest(), self.sha)

    def test_success_p16_records_evidence_and_closes_original_owner(self):
        self.execute()
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(self.calls[0].closed)
        self.assertEqual(self.calls[0].arguments["profile"], "test-p16")
        self.assertEqual(self.calls[0].arguments["candidate_sha256"], self.sha)
        self.assertFalse((self.state / ".active").exists())
        self.assertEqual(len(list(self.state.rglob("request.json"))), 1)
        results = list(self.state.rglob("result.json"))
        self.assertEqual(len(results), 1)
        report_path = self.out / "functional-runtime.json"
        report_bytes = report_path.read_bytes()
        descriptor = json.loads(results[0].read_text(encoding="utf-8"))["report"]
        self.assertEqual(descriptor, {"path": str(report_path),
                                      "sha256": hashlib.sha256(report_bytes).hexdigest(),
                                      "bytes": len(report_bytes)})
        report = json.loads(report_bytes)
        self.assertTrue(report["complete"])
        self.assertFalse(report["scored_game_admitted"])
        self.assert_user_files_unchanged()

    def test_p192_is_forwarded_without_running_a_real_engine(self):
        self.execute(profile="test-p192")
        self.assertEqual(self.calls[0].arguments["profile"], "test-p192")
        self.assertTrue(self.calls[0].closed)
        self.assertFalse((self.state / ".active").exists())

    def test_preexisting_active_lock_prevents_probe_and_preserves_lock(self):
        lock = self.state / ".active"
        lock.write_bytes(b"previous uncertain attempt")
        with self.assertRaises(Exception):
            self.execute()
        self.assertEqual(self.calls, [])
        self.assertEqual(lock.read_bytes(), b"previous uncertain attempt")
        self.assert_user_files_unchanged()

    def test_diagnostic_failure_closes_owner_and_records_result(self):
        self.options["fail"] = True
        result = self.execute()
        self.assertEqual(result["status"], "quarantine")
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(self.calls[0].closed)
        self.assertTrue((self.state / ".active").exists())
        self.assertEqual(len(list(self.state.rglob("result.json"))), 1)
        self.assert_user_files_unchanged()

    def test_failed_cleanup_keeps_lock_and_inspection_is_read_only(self):
        self.options.update(fail=True, cleanup_error=True)
        result = self.execute()
        self.assertEqual(result["status"], "quarantine")
        self.assertTrue(self.calls[0].closed)
        lock = self.state / ".active"
        self.assertTrue(lock.is_file())
        old = lock.read_bytes()
        self.assertEqual(host.inspect(self.state)["state"], "quarantine")
        self.assertEqual(lock.read_bytes(), old)
        with self.assertRaises(Exception):
            self.execute()
        self.assertEqual(len(self.calls), 1)
        self.assert_user_files_unchanged()

    def test_invalid_report_keeps_lock_even_after_owner_close(self):
        self.options["invalid_report"] = True
        result = self.execute()
        self.assertEqual(result["status"], "quarantine")
        self.assertTrue(self.calls[0].closed)
        self.assertTrue((self.state / ".active").exists())
        self.assert_user_files_unchanged()

    def test_invalid_profile_and_digest_do_not_start_probe(self):
        for changes in ({"profile": "test-p28"}, {"profile": "test-p16", "candidates_sha256": "bad"}):
            with self.subTest(changes=changes), self.assertRaises(Exception):
                self.execute(**changes)
            self.assertEqual(self.calls, [])
            self.assertFalse((self.state / ".active").exists())
        self.assert_user_files_unchanged()

    def test_create_failure_keeps_quarantine_marker(self):
        def uncertain_factory(**kwargs):
            raise RuntimeError("setup outcome uncertain")
        result = self.execute(_probe_factory=uncertain_factory)
        self.assertEqual(result["status"], "quarantine")
        self.assertTrue((self.state / ".active").exists())
        self.assertEqual(host.inspect(self.state)["state"], "quarantine")
        self.assert_user_files_unchanged()

    def test_interrupted_run_keeps_marker_after_owner_close(self):
        self.options["interrupted"] = True
        result = self.execute()
        self.assertEqual(result["status"], "quarantine")
        self.assertTrue(self.calls[0].closed)
        self.assertTrue((self.state / ".active").exists())
        self.assert_user_files_unchanged()

    def test_unavailable_or_linked_report_is_quarantined(self):
        for mode in ("missing", "symlink", "hardlink"):
            with self.subTest(mode=mode):
                state = self.base / ("state-" + mode)
                state.mkdir(mode=0o700)
                os.chmod(state, 0o700)
                self.options["report_mode"] = mode
                result = self.execute(state_dir=state, out=self.base / ("out-" + mode))
                self.assertEqual(result["status"], "quarantine")
                self.assertTrue((state / ".active").exists())
                self.assertTrue(self.calls[-1].closed)
        self.assert_user_files_unchanged()

    def test_private_state_permissions_are_required_before_probe(self):
        os.chmod(self.state, 0o755)
        with self.assertRaises(Exception):
            self.execute()
        self.assertEqual(self.calls, [])
        self.assertFalse((self.state / ".active").exists())
        self.assert_user_files_unchanged()

    def test_foreign_state_owner_is_rejected_before_probe(self):
        foreign = SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=os.geteuid() + 1)
        with patch.object(host.os, "fstat", return_value=foreign):
            with self.assertRaises(Exception):
                self.execute()
        self.assertEqual(self.calls, [])
        self.assertFalse((self.state / ".active").exists())
        self.assert_user_files_unchanged()

    def test_isolated_inspect_cli_exit_status_and_json(self):
        command = [sys.executable, "-I", "-B", str(Path(host.__file__).resolve()),
                   "--state-dir", str(self.state), "--inspect"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        idle = json.loads(result.stdout)
        self.assertEqual(idle["state"], "idle")
        self.assertFalse(idle["scored_game_admitted"])
        marker = self.state / ".active"
        marker.write_bytes(b"unresolved")
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        quarantine = json.loads(result.stdout)
        self.assertEqual(quarantine["state"], "quarantine")
        self.assertFalse(quarantine["scored_game_admitted"])
        self.assertEqual(marker.read_bytes(), b"unresolved")
        self.assert_user_files_unchanged()

    def test_p192_failure_report_is_collected_without_start_authority(self):
        self.options["failed_report"] = True
        result = self.execute(profile="test-p192")
        self.assertEqual(result["status"], "quarantine")
        raw = (self.out / "functional-runtime.json").read_bytes()
        self.assertEqual(result["report"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["report"]["bytes"], len(raw))
        self.assertFalse(result["scored_game_admitted"])
        self.assertTrue((self.state / ".active").exists())
        self.assert_user_files_unchanged()

    def test_report_fsync_failure_keeps_marker(self):
        original_fsync = os.fsync
        for kind in ("file", "directory", "parent"):
            with self.subTest(kind=kind):
                state = self.base / ("state-fsync-" + kind)
                state.mkdir(mode=0o700)
                os.chmod(state, 0o700)
                output = self.base / ("out-fsync-" + kind)
                target = {"file": output / "functional-runtime.json",
                          "directory": output, "parent": output.parent}[kind]
                def injected_fsync(fd):
                    if target.exists():
                        observed = os.fstat(fd)
                        expected = target.stat()
                        if (observed.st_dev, observed.st_ino) == (expected.st_dev, expected.st_ino):
                            raise OSError("injected report fsync failure")
                    return original_fsync(fd)
                with patch.object(host.os, "fsync", side_effect=injected_fsync):
                    result = self.execute(state_dir=state, out=output)
                self.assertEqual(result["status"], "quarantine")
                self.assertTrue((state / ".active").exists())
                self.assertTrue(self.calls[-1].closed)
                self.assertIsNone(result["report"])
        self.assert_user_files_unchanged()


if __name__ == "__main__":
    unittest.main()
