"""Bounded synthetic tests for the controller's explicit-GC event path."""
import copy
import gc
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import collect
import ledger
import run


BOOT = "01234567-89ab-cdef-0123-456789abcdef"
OBSERVER = {"pid": 42, "start_ticks": 10}


class Budget:
    def apply(self, event, data, timestamp):
        return self


class RunnerGcTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.journal = ledger.Journal(Path(self.tmp.name) / "events.jsonl", "fixture")
        self.addCleanup(self.journal.close)
        self.tracker = run.CooperativeGcTracker()
        gc_patch = patch.object(run, "_COOPERATIVE_GC_TRACKER", self.tracker)
        gc_patch.start()
        self.addCleanup(gc_patch.stop)
        self.controller = run.StageController.__new__(run.StageController)
        self.controller.plan = {"campaign": "fixture", "profile": "test-p16"}
        self.controller.out = Path(self.tmp.name)
        self.controller.journal = self.journal
        self.controller.results = ledger.CampaignResults("fixture")
        self.controller.budget = Budget()
        self.controller.instance_id = "i-fixture"
        self.controller._gc_scope_prefix = "fixture-controller"
        self.controller._gc_scope_bindings = {}
        self.controller.job_specs = {}
        self.controller.observe_raw = lambda job: None
        self.controller.acknowledge_results = lambda: None
        self.controller.replicate = lambda: None
        self.controller.queue_result = lambda *args, snapshots: None
        identity = patch.object(run, "proc_identity", return_value=OBSERVER)
        identity.start()
        self.addCleanup(identity.stop)
        boot = patch.object(Path, "read_text", return_value=BOOT)
        boot.start()
        self.addCleanup(boot.stop)
        self.jobs = []
        for leg in range(2):
            spec = {"leg": leg, "white": "A" if leg == 0 else "B",
                    "black": "B" if leg == 0 else "A", "opening_id": "opening",
                    "profile": "test-p16", "opening_sha256": "c" * 64,
                    "bank_id": "d" * 64, "artifact_sha256": {"A": "a" * 64, "B": "b" * 64}}
            job = SimpleNamespace(identity=f"job-{leg}", out=Path(self.tmp.name) / f"game-{leg}")
            self.controller.job_specs[job.identity] = {"pair": "pair", "game": f"game-{leg}",
                                                       "attempt": 0, "identity": spec}
            self.jobs.append(job)

    def spawn(self, job, *, arm=True):
        if arm:
            self.tracker.arm(self.controller._gc_scope_key(job))
        pid = 100 + self.jobs.index(job)
        obs = {"identity": job.identity, "pid": pid, "pgid": pid, "session": pid,
               "start_ticks": 200 + self.jobs.index(job), "spawn_monotonic": time.monotonic()}
        self.controller.event("spawned", job, obs)
        return obs

    def finish(self, job, obs):
        spec = self.controller.job_specs[job.identity]["identity"]
        data = {name: spec[name] for name in ("white", "black", "opening_id", "opening_sha256",
                                               "bank_id", "profile", "artifact_sha256")}
        data.update(result="1-0", reason="completed_chess_result", pgn_sha256="e" * 64,
                    raw_sha256="f" * 64)
        settled = {**obs, "completed_monotonic": time.monotonic(),
                   "gate_released": True, "returncode": 0, "cleanup_forced": False,
                   "remaining_processes": [], "readers_done": True}
        with patch.object(run, "parse_result", return_value=data), patch.object(run, "score_evidence_unresolved", return_value=None):
            self.controller.event("completed", job, settled)

    def status(self, job, rows=None):
        spec = self.controller.job_specs[job.identity]
        state = self.controller.results.games[(spec["game"], 0)]
        return collect.cooperative_gc_status(self.journal.rows if rows is None else rows, "fixture", state)

    def test_real_event_ledger_collector_clean_and_automatic_gc(self):
        job = self.jobs[0]
        obs = self.spawn(job)
        # This is Python's normal GC mechanism, not the controller intervention hook.
        gc.collect()
        self.finish(job, obs)
        self.assertEqual(self.status(job), "clean")
        events = [row["event"] for row in self.journal.rows]
        self.assertLess(events.index("game.process"), events.index("game.cooperative_gc_open"))
        self.assertLess(events.index("game.result"), events.index("game.cooperative_gc_close"))
        close = next(row["data"] for row in self.journal.rows if row["event"] == "game.cooperative_gc_close")
        self.assertEqual(close["result_sha256"], self.controller.results.games[("game-0", 0)].result_sha256)
        self.assertEqual(close["active_count"], 0)
        replay = ledger.CampaignResults.replay("fixture", ledger.read_journal(self.journal.path, "fixture"))
        self.assertEqual(replay.games[("game-0", 0)].result_sha256, close["result_sha256"])

    def test_explicit_intervention_marks_both_overlapping_games(self):
        observations = [self.spawn(job) for job in self.jobs]
        self.controller.cooperative_gc()
        for job, observation in zip(self.jobs, observations):
            self.finish(job, observation)
            self.assertEqual(self.status(job), "intervened")

    def test_inflight_before_arm_and_during_close(self):
        entered, release = threading.Event(), threading.Event()
        def collector():
            entered.set()
            if not release.wait(5):
                raise TimeoutError("test collector did not release")
        self.tracker._collector = collector
        worker = threading.Thread(target=self.controller.cooperative_gc)
        worker.start()
        self.addCleanup(lambda: (release.set(), worker.join(5)))
        self.assertTrue(entered.wait(5))
        job = self.jobs[0]
        obs = self.spawn(job)
        self.finish(job, obs)
        opened = next(row["data"] for row in self.journal.rows if row["event"] == "game.cooperative_gc_open")
        closed = next(row["data"] for row in self.journal.rows if row["event"] == "game.cooperative_gc_close")
        self.assertEqual((opened["active_count"], closed["active_count"]), (1, 1))
        self.assertEqual((opened["request_count"], opened["performed_count"]),
                         (closed["request_count"], closed["performed_count"]))
        self.assertEqual(self.status(job), "intervened")

    def test_failed_explicit_gc_request_is_not_clean(self):
        job = self.jobs[0]
        obs = self.spawn(job)
        self.tracker._collector = lambda: (_ for _ in ()).throw(RuntimeError("failed"))
        with self.assertRaises(RuntimeError):
            self.controller.cooperative_gc()
        self.finish(job, obs)
        self.assertEqual(self.status(job), "intervened")
        close = next(row["data"] for row in self.journal.rows if row["event"] == "game.cooperative_gc_close")
        self.assertEqual((close["request_count"], close["performed_count"], close["active_count"]), (1, 0, 0))

    def test_request_begun_after_arm_still_active_at_close(self):
        job = self.jobs[0]
        obs = self.spawn(job)
        entered, release = threading.Event(), threading.Event()
        def collector():
            entered.set()
            if not release.wait(5):
                raise TimeoutError("test collector did not release")
        self.tracker._collector = collector
        worker = threading.Thread(target=self.controller.cooperative_gc)
        worker.start()
        self.addCleanup(lambda: (release.set(), worker.join(5)))
        self.assertTrue(entered.wait(5))
        self.finish(job, obs)
        close = next(row["data"] for row in self.journal.rows if row["event"] == "game.cooperative_gc_close")
        self.assertEqual((close["request_count"], close["performed_count"], close["active_count"]), (1, 0, 1))
        self.assertEqual(self.status(job), "intervened")

    def test_missing_duplicate_and_identity_mismatch_are_unverified(self):
        job = self.jobs[0]
        obs = self.spawn(job)
        self.finish(job, obs)
        original = self.journal.rows
        for field in ("pid", "boot_id"):
            rows = copy.deepcopy(original)
            process = next(row["data"] for row in rows if row["event"] == "game.process")
            process[field] = 999 if field == "pid" else "f" * 36
            self.assertEqual(self.status(job, rows), "unverified")
        for event in ("game.cooperative_gc_open", "game.cooperative_gc_close"):
            rows = copy.deepcopy(original)
            target = next(row for row in rows if row["event"] == event)
            self.assertEqual(self.status(job, [row for row in rows if row is not target]), "unverified")
            rows.insert(rows.index(target) + 1, copy.deepcopy(target))
            self.assertEqual(self.status(job, rows), "unverified")

    def test_unarmed_game_and_changed_observer_fail_closed(self):
        first, second = self.jobs
        obs = self.spawn(first, arm=False)
        self.finish(first, obs)
        self.assertEqual(self.status(first), "unverified")
        obs = self.spawn(second)
        with patch.object(run, "proc_identity", return_value={"pid": 42, "start_ticks": 11}):
            self.finish(second, obs)
        self.assertEqual(self.status(second), "unverified")

    def test_missing_observer_does_not_block_game_and_cannot_prove_clean(self):
        first, second = self.jobs
        with patch.object(run, "proc_identity", return_value=None):
            first_obs = self.spawn(first)
        self.finish(first, first_obs)
        self.assertIsNotNone(self.controller.results.games[("game-0", 0)].result)
        self.assertEqual(self.status(first), "unverified")
        second_obs = self.spawn(second)
        with patch.object(run, "proc_identity", return_value=None):
            self.finish(second, second_obs)
        self.assertIsNotNone(self.controller.results.games[("game-1", 0)].result)
        self.assertEqual(self.status(second), "unverified")

    def test_partial_journal_write_on_scope_open_propagates(self):
        job = self.jobs[0]
        append = self.journal.append
        def fail_open(event, *args, **kwargs):
            if event == "game.cooperative_gc_open":
                self.journal.file.write(b'{"partial":')
                raise OSError("injected partial journal write")
            return append(event, *args, **kwargs)
        with patch.object(self.journal, "append", side_effect=fail_open):
            with self.assertRaisesRegex(OSError, "partial journal"):
                self.spawn(job)
        with self.assertRaises(ValueError):
            ledger.read_journal(self.journal.path, "fixture")
        self.assertNotIn(job.identity, self.controller._gc_scope_bindings)

    def test_partial_journal_write_on_scope_close_propagates(self):
        job = self.jobs[0]
        obs = self.spawn(job)
        append = self.journal.append
        def fail_close(event, *args, **kwargs):
            if event == "game.cooperative_gc_close":
                self.journal.file.write(b'{"partial":')
                raise OSError("injected partial journal write")
            return append(event, *args, **kwargs)
        with patch.object(self.journal, "append", side_effect=fail_close):
            with self.assertRaisesRegex(OSError, "partial journal"):
                self.finish(job, obs)
        with self.assertRaises(ValueError):
            ledger.read_journal(self.journal.path, "fixture")
        self.assertIsNotNone(self.controller.results.games[("game-0", 0)].result)


if __name__ == "__main__":
    unittest.main()
