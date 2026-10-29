from __future__ import annotations

import hashlib
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

try:
    from . import rove_runtime_observation as observation
except ImportError:
    import rove_runtime_observation as observation


class RuntimeObservation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.proc = root / "proc"
        self.process = self.proc / "77"
        self.process.mkdir(parents=True)
        boot = self.proc / "sys/kernel/random"
        boot.mkdir(parents=True)
        self.boot_id = "1d172f62-38c5-49ec-95d1-724336430f42"
        (boot / "boot_id").write_text(self.boot_id + "\n")
        self.exe = root / "native"
        self.exe.write_bytes(b"synthetic executable")
        (self.process / "exe").symlink_to(self.exe)
        self.sha = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        self.owner = {"pid": 77, "pgid": 77, "session": 77, "start_ticks": 1234}
        fields = ["S", "1", "77", "77"] + ["0"] * 15 + ["1234"]
        (self.process / "stat").write_text("77 (engine name) " + " ".join(fields) + "\n")
        artifact = SimpleNamespace(id="candidate-a", family="A", profile="test-p16",
                                   entry_bytes=24, tt_bytes=12 << 30,
                                   native_sha256=self.sha, sha256="a" * 64)
        self.row = {"artifact": artifact, "evidence": {"kind": "file-pins-only",
                                                          "source_contract_verified": False}}
        self.args = {"candidate_path": root / "candidates.json", "candidate_sha256": "b" * 64,
                     "profile": "test-p16", "artifact_id": "candidate-a", "pid": 77,
                     "expected_start_ticks": 1234, "expected_boot_id": self.boot_id,
                     "expected_pgid": 77, "expected_session": 77, "worker_tids": list(range(100, 116)),
                     "cpu_ids": list(range(16)), "allowed_nodes": [0], "proc": self.proc}

    def test_native_identity_is_pinned_and_start_ticks_checked(self):
        result = observation._native(77, 1234, self.sha, self.proc)
        self.assertEqual(result["owner"], self.owner)
        with self.assertRaisesRegex(ValueError, "start identity"):
            observation._native(77, 1235, self.sha, self.proc)
        with self.assertRaisesRegex(ValueError, "native image"):
            observation._native(77, 1234, "0" * 64, self.proc)

    def test_samples_bind_the_same_native_owner_and_do_not_grant_authority(self):
        worker = {"owner": self.owner, "boot_id": self.boot_id, "all_selected_workers_positive": True}
        vma = {"owner": self.owner, "vmas": [{"mapping_start": 8192}]}
        with mock.patch.object(observation.diagnostic_candidates, "read_candidates", return_value=([self.row], "b" * 64)), \
             mock.patch.object(observation.rove_worker_observer, "observe_workers", return_value=worker), \
             mock.patch.object(observation.rove_vma_observer, "observe_range", return_value=vma) as inspect:
            result = observation.observe_candidate(**self.args, address=8192)
        self.assertEqual(result["native"]["owner"], self.owner)
        self.assertEqual(inspect.call_args.kwargs["length"], 12 << 30)
        self.assertEqual(inspect.call_args.kwargs["allowed_nodes"], [0])
        self.assertEqual(result["candidate_evidence"]["kind"], "file-pins-only")
        self.assertFalse(any(result["claims"].values()))

    def test_live_owner_mismatch_is_rejected(self):
        worker = {"owner": {**self.owner, "start_ticks": 1235}, "boot_id": self.boot_id}
        with mock.patch.object(observation.diagnostic_candidates, "read_candidates", return_value=([self.row], "b" * 64)), \
             mock.patch.object(observation.rove_worker_observer, "observe_workers", return_value=worker):
            with self.assertRaisesRegex(ValueError, "identity changed"):
                observation.observe_candidate(**self.args)

    def test_other_family_and_layout_cannot_use_rove_observation(self):
        self.row["artifact"].family = "D"
        with mock.patch.object(observation.diagnostic_candidates, "read_candidates", return_value=([self.row], "b" * 64)):
            with self.assertRaisesRegex(ValueError, "Rove profile"):
                observation.observe_candidate(**self.args)
        self.row["artifact"].family = "A"
        self.row["artifact"].tt_bytes = 16 << 30
        with mock.patch.object(observation.diagnostic_candidates, "read_candidates", return_value=([self.row], "b" * 64)):
            with self.assertRaisesRegex(ValueError, "Rove profile"):
                observation.observe_candidate(**self.args)

    def test_stale_boot_or_process_group_is_rejected_before_sampling(self):
        with mock.patch.object(observation.diagnostic_candidates, "read_candidates", return_value=([self.row], "b" * 64)), \
             mock.patch.object(observation.rove_worker_observer, "observe_workers") as sample:
            with self.assertRaisesRegex(ValueError, "boot identity"):
                observation.observe_candidate(**{**self.args, "expected_boot_id": "d4a7a973-f28e-4e4e-8183-40b873b2452d"})
            with self.assertRaisesRegex(ValueError, "process group"):
                observation.observe_candidate(**{**self.args, "expected_pgid": 123})
            sample.assert_not_called()

    def test_p192_range_uses_full_rove_tt_extent_without_claiming_its_origin(self):
        self.row["artifact"].profile = "test-p192"
        self.row["artifact"].tt_bytes = 192 << 30
        worker = {"owner": self.owner, "boot_id": self.boot_id}
        vma = {"owner": self.owner, "vmas": []}
        args = {**self.args, "profile": "test-p192", "worker_tids": list(range(100, 292)),
                "cpu_ids": list(range(192)), "allowed_nodes": [0, 1]}
        with mock.patch.object(observation.diagnostic_candidates, "read_candidates", return_value=([self.row], "b" * 64)), \
             mock.patch.object(observation.rove_worker_observer, "observe_workers", return_value=worker), \
             mock.patch.object(observation.rove_vma_observer, "observe_range", return_value=vma) as inspect:
            result = observation.observe_candidate(**args, address=8192)
        self.assertEqual(inspect.call_args.kwargs["length"], 192 << 30)
        self.assertFalse(result["claims"]["range_is_tt_verified"])
        self.assertFalse(result["claims"]["executable_continuity_verified"])
        self.assertFalse(result["claims"]["worker_vma_simultaneity_verified"])

    @unittest.skipUnless(sys.platform.startswith("linux") and hasattr(os, "sched_getaffinity"),
                         "Linux proc and scheduler are required")
    def test_small_owned_process_reads_real_proc_and_scheduler(self):
        # This is a tiny Python child, not a chess engine or a P16/P192 run.
        code = ("import ctypes,sys; b=ctypes.create_string_buffer(4096); "
                "print(ctypes.addressof(b),flush=True); sys.stdin.readline()")
        child = subprocess.Popen([sys.executable, "-c", code], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, start_new_session=True)
        try:
            ready, _, _ = select.select([child.stdout], [], [], 5)
            self.assertTrue(ready, "small child did not expose its buffer")
            address = int(child.stdout.readline().strip())
            proc = Path("/proc")
            owner = observation._owner(child.pid, proc)
            self.assertEqual((owner["pid"], owner["pgid"], owner["session"]),
                             (child.pid, child.pid, child.pid))
            digest = hashlib.sha256((proc / str(child.pid) / "exe").read_bytes()).hexdigest()
            self.assertEqual(observation._native(child.pid, owner["start_ticks"], digest, proc)["owner"], owner)
            cpus = sorted(os.sched_getaffinity(child.pid))
            sample = observation.rove_worker_observer._sample(
                proc, child.pid, [child.pid], cpus, owner, os.sched_getaffinity,
                time.monotonic() + 5, time.monotonic)
            self.assertEqual(sample[child.pid]["cpus"], cpus)
            status = (proc / str(child.pid) / "status").read_text()
            allowed = next(line.split(":", 1)[1].strip() for line in status.splitlines()
                           if line.startswith("Mems_allowed_list:"))
            nodes = []
            for piece in allowed.split(","):
                bounds = piece.split("-")
                first, last = int(bounds[0]), int(bounds[-1])
                nodes.extend(range(first, last + 1))
            vma = observation.rove_vma_observer.observe_range(
                child.pid, expected_start_ticks=owner["start_ticks"], address=address,
                length=4096, allowed_nodes=nodes, proc=proc)
            self.assertEqual(vma["owner"], owner)
            self.assertFalse(vma["claims"]["caller_range_is_tt"])
        finally:
            if child.poll() is None:
                try:
                    child.stdin.write("stop\n")
                    child.stdin.flush()
                except BrokenPipeError:
                    pass
            try:
                child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.communicate()
                raise
        self.assertEqual(child.returncode, 0)
if __name__ == "__main__":
    unittest.main()
