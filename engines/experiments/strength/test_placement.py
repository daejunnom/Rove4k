import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import select
import signal
import tempfile
import unittest
from unittest.mock import patch

import placement


class PlacementTests(unittest.TestCase):
    @unittest.skipUnless(hasattr(os, "sched_getaffinity"), "actual Linux /proc port")
    def test_actual_two_image_observation_and_wrong_binding_rejection(self):
        command = """import subprocess,sys
children=[]
try:
    children=[subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(10)']) for _ in range(2)]
    print('ready',flush=True)
    sys.stdin.readline()
finally:
    for child in children:
        if child.poll() is None: child.terminate()
    for child in children: child.wait(timeout=3)
"""
        child = subprocess.Popen([sys.executable, "-B", "-c", command], start_new_session=True,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            self.assertTrue(select.select([child.stdout], [], [], 5)[0], "owned observer fixture never became ready")
            self.assertEqual(child.stdout.readline(), b"ready\n")
            native = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
            cpus = os.sched_getaffinity(0)
            observed = placement.observe_game_engines(child.pid, [native, native], cpus)
            self.assertEqual(len(observed["engines"]), 2)
            self.assertTrue(all(row["alive"] for row in observed["engines"]))
            self.assertTrue(all(row["native_sha256"] == native for row in observed["engines"]))
            with self.assertRaisesRegex(ValueError, "two qualified native images"):
                placement.observe_game_engines(child.pid, [native, "0" * 64], cpus)
            with self.assertRaisesRegex(ValueError, "escaped"):
                placement.observe_game_engines(child.pid, [native, native], set())
        finally:
            try:
                child.communicate(b"stop\n", timeout=5)
            except subprocess.TimeoutExpired:
                identity = placement._process_identity(child.pid)
                if identity["pgid"] == child.pid and identity["session"] == child.pid:
                    os.killpg(child.pid, signal.SIGKILL)
                child.communicate(timeout=5)
        self.assertEqual(child.returncode, 0)

    def test_resume_cleanup_uses_original_empty_identities_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            parent, child = root / "campaign-fixture", root / "campaign-fixture" / "slot-000"
            child.mkdir(parents=True)
            for path in (parent, child):
                (path / "cgroup.events").write_text("populated 0\nfrozen 0\n")
            record = lambda path: {"path": str(path), "device": path.stat().st_dev, "inode": path.stat().st_ino}
            records = [record(parent), record(child)]
            with patch.object(Path, "rmdir", autospec=True) as remove:
                outcomes = placement.cleanup_owned_groups(records, root=root)
            self.assertEqual([call.args[0] for call in remove.call_args_list], [child, parent])
            self.assertTrue(all(row.get("removed") for row in outcomes))
            (child / "cgroup.events").write_text("populated 1\n")
            with patch.object(Path, "rmdir", autospec=True) as remove:
                outcome = placement.cleanup_owned_groups([records[1]], root=root)[0]
            self.assertIn("contains tasks", outcome["error"])
            remove.assert_not_called()
            changed = {**records[1], "inode": records[1]["inode"] + 1}
            with patch.object(Path, "rmdir", autospec=True) as remove:
                outcome = placement.cleanup_owned_groups([changed], root=root)[0]
            self.assertIn("identity changed", outcome["error"])
            remove.assert_not_called()
            with self.assertRaisesRegex(ValueError, "dedicated root"):
                placement.cleanup_owned_groups([records[1]], root=root / "other")

    def test_resume_cleanup_is_idempotent_and_preserves_raced_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            parent = root / "campaign-fixture"
            parent.mkdir()
            stat = parent.stat()
            record = {"path": str(parent), "device": stat.st_dev, "inode": stat.st_ino}
            (parent / "cgroup.events").write_text("populated 0\n")
            with patch.object(Path, "rmdir", autospec=True, side_effect=OSError(16, "busy")):
                outcome = placement.cleanup_owned_groups([record], root=root)[0]
            self.assertIn("busy", outcome["error"])
            self.assertTrue(parent.exists())
            (parent / "cgroup.events").unlink()
            parent.rmdir()
            outcome = placement.cleanup_owned_groups([record], root=root)[0]
            self.assertTrue(outcome["already_absent"])

    @unittest.skipUnless(hasattr(os, "sched_getaffinity"), "Linux execution port")
    def test_actual_preexec_mask_survives_exec(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            cpu = min(os.sched_getaffinity(0))
            node = min(placement.allowed_nodes())
            slot = root / "slot.json"
            slot.write_text(json.dumps({"slot": {"cpus": [cpu], "memory_nodes": [node], "policy": "inherit"}}))
            observed = root / "observed.json"
            command = [sys.executable, "-B", str(Path(placement.__file__).resolve()), "--slot", str(slot),
                       "--record", str(observed), "--", sys.executable, "-B", "-c",
                       "import os,json; print(json.dumps(sorted(os.sched_getaffinity(0))))"]
            result = subprocess.run(command, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(json.loads(result.stdout), [cpu])
            record = json.loads(observed.read_text())
            self.assertEqual(record["requested_cpus"], [cpu])
            self.assertEqual(record["effective_cpus"], [cpu])
            self.assertIn("pre-exec", record["stage"])

    @unittest.skipUnless(hasattr(os, "sched_getaffinity"), "Linux execution port")
    def test_failed_observation_does_not_claim_successful_set_fell_back(self):
        policy = [{"available": False}, {"available": False, "request_applied": True,
                                          "reason": "get_mempolicy rejected", "errno": 1}]
        with patch.object(placement.os, "sched_getaffinity", return_value={7}), \
                patch.object(placement.os, "sched_setaffinity"), \
                patch.object(placement, "allowed_nodes", return_value={0}), \
                patch.object(placement, "memory_policy", side_effect=policy):
            observed = placement.apply_slot({"cpus": [7], "memory_nodes": [0], "policy": "interleave"})
        self.assertIsNone(observed["fallback"])
        self.assertTrue(observed["observed_policy"]["request_applied"])
        self.assertFalse(observed["observed_policy"]["available"])

    @unittest.skipUnless(hasattr(os, "sched_getaffinity"), "Linux execution port")
    def test_no_unowned_mask_widening(self):
        with patch.object(placement.os, "sched_getaffinity", return_value={7}), \
                patch.object(placement, "allowed_nodes", return_value={0}):
            with self.assertRaisesRegex(ValueError, "widen"):
                placement.apply_slot({"cpus": [8], "memory_nodes": [0]})
            with self.assertRaisesRegex(ValueError, "owned cgroup"):
                placement.apply_slot({"cpus": [8], "memory_nodes": [0]}, saved_ancestor_cpus=[7, 8])


if __name__ == "__main__":
    unittest.main()
