"""Synthetic Linux task observations; no engine or high-resource job runs."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

try:
    from . import rove_worker_observer as observer
except ImportError:
    import rove_worker_observer as observer


@unittest.skipUnless(os.name == "posix" and hasattr(os, "sched_getaffinity"), "Linux scheduler fixture")
class WorkerObservationTests(unittest.TestCase):
    pid = 100
    boot = "12345678-1234-1234-1234-123456789abc"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.proc = Path(self.temp.name) / "proc"
        (self.proc / "sys/kernel/random").mkdir(parents=True)
        (self.proc / "sys/kernel/random/boot_id").write_text(self.boot + "\n")
        (self.proc / str(self.pid) / "task").mkdir(parents=True)
        self.tids = list(range(self.pid, self.pid + 16))
        self.cpus = list(range(16))
        self.affinity = {tid: set(self.cpus) for tid in self.tids}
        self.elapsed = 100.0
        self.write_leader()
        for tid in self.tids:
            self.write_worker(tid)

    @staticmethod
    def stat(tid, *, start=1000, ticks=10, pgid=200, session=300, state="S"):
        fields = [state, "1", str(pgid), str(session)] + ["0"] * 16
        fields[11] = str(ticks)
        fields[12] = "0"
        fields[19] = str(start)
        # comm can contain spaces and ')' and is not parsed by whitespace.
        return str(tid) + " (worker name ) nested) " + " ".join(fields) + "\n"

    def write_leader(self, *, start=1000, pgid=200, session=300, state="S"):
        (self.proc / str(self.pid) / "stat").write_text(
            self.stat(self.pid, start=start, pgid=pgid, session=session, state=state))

    def write_worker(self, tid, *, start=None, ticks=10, pgid=200, session=300, state="S"):
        directory = self.proc / str(self.pid) / "task" / str(tid)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "stat").write_text(self.stat(tid, start=start if start is not None else 1000 + tid - self.pid,
                                                   ticks=ticks, pgid=pgid, session=session, state=state))

    def sleep(self, seconds):
        self.elapsed += seconds
        for tid in self.tids:
            self.write_worker(tid, ticks=20)

    def observe(self, **kwargs):
        return observer.observe_workers(
            kwargs.pop("pid", self.pid), profile=kwargs.pop("profile", "test-p16"),
            expected_boot_id=kwargs.pop("expected_boot_id", self.boot),
            expected_start_ticks=kwargs.pop("expected_start_ticks", 1000),
            expected_pgid=kwargs.pop("expected_pgid", 200), expected_session=kwargs.pop("expected_session", 300),
            worker_tids=kwargs.pop("worker_tids", self.tids), cpu_ids=kwargs.pop("cpu_ids", self.cpus),
            sample_seconds=kwargs.pop("sample_seconds", 0.1), proc_root=self.proc,
            affinity_for_test=kwargs.pop("affinity_for_test", lambda tid: self.affinity[tid]),
            sleep_for_test=kwargs.pop("sleep_for_test", self.sleep),
            clock_for_test=kwargs.pop("clock_for_test", lambda: self.elapsed), **kwargs)

    def test_bounded_two_sample_allows_leader_and_never_claims_admission(self):
        result = self.observe()
        self.assertEqual(result["owner"], {"pid": self.pid, "start_ticks": 1000, "pgid": 200, "session": 300})
        self.assertEqual(result["boot_id"], self.boot)
        self.assertEqual(result["positive_worker_ids"], self.tids)
        self.assertTrue(result["all_selected_workers_positive"])
        self.assertTrue(result["fixture_inputs"])
        for name in ("native_identity_verified", "selected_worker_set_complete", "search_causality_verified",
                     "observed_entire_search", "numa_placement_verified", "scored_game_admitted",
                     "pid_namespace_binding_verified", "continuous_affinity_verified"):
            self.assertFalse(result[name])
        self.assertEqual(result["workers"][0]["tid"], self.pid)
        self.assertEqual(result["workers"][0]["cpu_ticks_first"], 10)
        self.assertEqual(result["workers"][0]["cpu_ticks_last"], 20)

    def test_zero_tick_progress_is_recorded_not_called_active(self):
        def sleep(seconds):
            self.sleep(seconds)
            self.write_worker(self.tids[1], ticks=10)
        result = self.observe(sleep_for_test=sleep)
        self.assertFalse(result["all_selected_workers_positive"])
        self.assertNotIn(self.tids[1], result["positive_worker_ids"])
        self.assertFalse(result["workers"][1]["positive_cpu_ticks"])

    def test_worker_replacement_or_counter_regression_is_rejected(self):
        for mutation in (lambda: self.write_worker(self.tids[4], start=9000, ticks=20),
                         lambda: self.write_worker(self.tids[4], ticks=1)):
            with self.subTest(mutation=mutation):
                self.write_worker(self.tids[4], ticks=10)
                def sleep(seconds):
                    self.sleep(seconds)
                    mutation()
                with self.assertRaises(ValueError):
                    self.observe(sleep_for_test=sleep)
                for tid in self.tids:
                    self.write_worker(tid, ticks=10)

    def test_leader_replacement_group_or_boot_change_is_rejected(self):
        def replace(seconds):
            self.sleep(seconds)
            self.write_leader(start=1001)
        with self.assertRaises(ValueError):
            self.observe(sleep_for_test=replace)
        self.write_leader()
        def move_group(seconds):
            self.sleep(seconds)
            self.write_leader(pgid=201)
        with self.assertRaises(ValueError):
            self.observe(sleep_for_test=move_group)
        self.write_leader()
        def reboot(seconds):
            self.sleep(seconds)
            (self.proc / "sys/kernel/random/boot_id").write_text("87654321-1234-1234-1234-123456789abc\n")
        with self.assertRaises(ValueError):
            self.observe(sleep_for_test=reboot)

    def test_stale_expected_boot_or_owner_is_rejected_before_sampling(self):
        for args in ({"expected_boot_id": "87654321-1234-1234-1234-123456789abc"},
                     {"expected_boot_id": "not-a-uuid"}, {"expected_pgid": 201},
                     {"expected_session": 301}, {"expected_start_ticks": 1001}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.observe(**args)

    def test_affinity_mismatch_and_vanished_or_terminal_task_are_rejected(self):
        self.affinity[self.tids[1]] = {1, 2}
        with self.assertRaises(ValueError):
            self.observe()
        self.affinity[self.tids[1]] = set(self.cpus)
        self.write_worker(self.tids[1], state="Z")
        with self.assertRaises(ValueError):
            self.observe()
        (self.proc / str(self.pid) / "task" / str(self.tids[1]) / "stat").unlink()
        with self.assertRaises(ValueError):
            self.observe()

    def test_affinity_observation_detects_thread_replacement(self):
        def affinity(tid):
            if tid == self.tids[3]:
                self.write_worker(tid, start=9999)
            return self.affinity[tid]
        with self.assertRaises(ValueError):
            self.observe(affinity_for_test=affinity)

    def test_profile_and_explicit_input_contracts_are_checked(self):
        for args in ({"worker_tids": self.tids[:-1]}, {"worker_tids": [self.pid] * 16},
                     {"cpu_ids": self.cpus[:-1]}, {"cpu_ids": [0] * 16},
                     {"profile": "test-p28"}, {"sample_seconds": 0.01},
                     {"sample_seconds": 5.1}, {"expected_start_ticks": 0}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.observe(**args)

    def test_interrupted_interval_cannot_be_reported_as_full_sample(self):
        with self.assertRaisesRegex(ValueError, "interval was not completed"):
            self.observe(sleep_for_test=lambda seconds: None)

    def test_explicit_p192_geometry_is_not_inferred_from_p16(self):
        with self.assertRaises(ValueError):
            self.observe(profile="test-p192")
        self.tids = list(range(self.pid, self.pid + 192))
        self.cpus = list(range(192))
        self.affinity = {tid: set(self.cpus) for tid in self.tids}
        for tid in self.tids:
            self.write_worker(tid)
        result = self.observe(profile="test-p192")
        self.assertEqual(len(result["workers"]), 192)
        self.assertTrue(result["all_selected_workers_positive"])
        self.assertFalse(result["scored_game_admitted"])


if __name__ == "__main__":
    unittest.main()
