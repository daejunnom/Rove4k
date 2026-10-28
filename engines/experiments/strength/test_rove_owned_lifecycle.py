"""Small owned-lifecycle boundary tests; no engine or large TT is started."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

try:
    from . import rove_owned_lifecycle as subject
except ImportError:
    import rove_owned_lifecycle as subject


class Stream:
    def __init__(self):
        self.data = b"uciok\nreadyok\n"

    def bytes(self):
        return self.data

    def until(self, predicate, _budget, *, seconds):
        if seconds <= 0 or not predicate(self.data):
            raise AssertionError("test stream did not satisfy protocol")


class Budget:
    def __init__(self, _wall=180):
        pass

    def left(self, seconds):
        return seconds


class Owned:
    def __init__(self, pid=123):
        self.process = SimpleNamespace(pid=pid)
        self.stdout = Stream()
        self.budget = Budget()
        self.sent = []
        self.input_closed = False
        self.cleanup_calls = 0

    def send(self, data):
        if self.input_closed:
            raise ValueError("input already closed")
        self.sent.append(data)

    def close_input(self):
        self.input_closed = True

    def exited(self):
        return False

    def cleanup(self):
        self.cleanup_calls += 1
        return {"owned_group_absent": True, "readers_joined": True,
                "forced_cleanup": False, "errors": []}


IDENTITY = {"pid": 123, "pgid": 123, "session": 123, "start_ticks": 44, "alive": True}


class LifecycleTests(unittest.TestCase):
    def test_group_comparison_ignores_timestamp_but_not_resource_identity(self):
        base = {"path": "/sys/fs/cgroup/test", "device": 1, "inode": 2,
                "cpus": [0, 1], "memory_nodes": [0], "memory_max": 1024,
                "observed_at_utc": "first"}
        changed = {**base, "observed_at_utc": "later"}
        self.assertEqual(subject._group_identity(base), subject._group_identity(changed))
        self.assertNotEqual(subject._group_identity(base), subject._group_identity({**changed, "inode": 9}))

    def active(self, label, *, identity=IDENTITY, cpus=(0, 1), bestmove=False):
        owned = Owned()
        scope = SimpleNamespace(task_snapshot=lambda _pid: {123: {"cpu_ticks": 0}, 124: {"cpu_ticks": 0}},
                                image_snapshot=lambda pid, sha: {"pid": pid, "sha256": sha})
        worker = {"tid": 124, "start_ticks": 45, "cpus": list(cpus), "cpu_ticks_first": 0, "cpu_ticks_last": 1}
        if bestmove:
            owned.stdout.data += b"bestmove e2e4\n"
        with mock.patch.object(subject.peer, "_worker_evidence", return_value=worker), \
             mock.patch.object(subject.placement, "_process_identity", return_value=identity), \
             mock.patch.object(subject.memory, "_file", return_value="123\n"):
            result = subject._active_termination(owned, scope, [0, 1], label,
                expected_identity=IDENTITY, group_path=Path("/unused"), native_sha256="a" * 64, maximum=.1)
        return owned, result

    def test_active_quit_and_eof_follow_real_observed_progress(self):
        quit_owner, quit_report = self.active("active-quit")
        eof_owner, eof_report = self.active("active-eof")
        self.assertEqual(quit_owner.sent[-1], b"quit\n")
        self.assertFalse(quit_owner.input_closed)
        self.assertTrue(eof_owner.input_closed)
        self.assertNotIn(b"quit\n", eof_owner.sent)
        self.assertEqual(quit_report["observed_progress_before_request"]["tid"], 124)
        self.assertFalse(eof_report["complete_worker_set_proven"])

    def test_active_terminal_rejects_changed_process_and_cpu_escape(self):
        with self.assertRaisesRegex(ValueError, "identity changed"):
            self.active("active-quit", identity={**IDENTITY, "start_ticks": 999})
        with self.assertRaisesRegex(ValueError, "escaped"):
            self.active("active-eof", cpus=(2,))

    def test_terminal_is_not_sent_if_search_finished_before_observation(self):
        owned = Owned()
        send = owned.send

        def immediately_finish(data):
            send(data)
            if b"go " in data:
                owned.stdout.data += b"bestmove e2e4\n"

        owned.send = immediately_finish
        scope = SimpleNamespace(task_snapshot=lambda _pid: {123: {"cpu_ticks": 0}},
                                image_snapshot=lambda pid, sha: {"pid": pid, "sha256": sha})
        with self.assertRaisesRegex(ValueError, "completed before active termination"):
            subject._active_termination(owned, scope, [0, 1], "active-quit", expected_identity=IDENTITY,
                                        group_path=Path("/unused"), native_sha256="a" * 64, maximum=.1)
        self.assertNotIn(b"quit\n", owned.sent)
        self.assertFalse(owned.input_closed)

    def test_original_cgroup_membership_is_checked_before_terminal_request(self):
        with mock.patch.object(subject.placement, "_process_identity", return_value=IDENTITY), \
             mock.patch.object(subject.memory, "_file", return_value="999\n"):
            with self.assertRaisesRegex(ValueError, "left its original cgroup"):
                subject._current_owner(IDENTITY, Path("/unused"))

    def test_candidate_evidence_change_is_not_reinterpreted_as_same_pin(self):
        artifact = SimpleNamespace(id="a-p16", identity=lambda: {"id": "a-p16"})
        candidate = {"artifact": artifact, "source": {"sha256": "a" * 64}, "native": {},
                     "whole": Path("/unused"), "evidence": {"source": "before"}}
        changed = {**candidate, "evidence": {"source": "after"}}
        with mock.patch.object(subject.diagnostic, "read_candidates", return_value=([changed], "d" * 64)):
            with self.assertRaisesRegex(ValueError, "candidate set or source evidence changed"):
                subject._candidate_still_matches(Path("/unused"), "d" * 64, "test-p16", candidate)

    @unittest.skipUnless(sys.platform == "linux", "owned collector contract runs on Linux")
    def test_four_distinct_modes_and_partial_claims_are_recorded(self):
        artifact = SimpleNamespace(id="a-p16", family="A", workers=16, tt_bytes=12 << 30,
            native_sha256="a" * 64, sha256="b" * 64, whole_bytes=4200,
            identity=lambda: {"id": "a-p16", "family": "A", "profile": "test-p16"})
        candidate = {"artifact": artifact, "source": {"sha256": "c" * 64}, "native": {},
                     "whole": Path("/unused"), "evidence": {"scope": "mock"}}
        slot = {"workers": 16, "cpus": list(range(16)), "memory_nodes": [0], "policy": "default"}
        group_path = Path("/sys/fs/cgroup/test")
        group = {"path": str(group_path), "device": 1, "inode": 2, "cpus": slot["cpus"],
                 "memory_nodes": [0], "memory_max": 20 << 30, "observed_at_utc": "first"}
        owner = SimpleNamespace(OWNED=[], Budget=Budget)
        scope = SimpleNamespace(image_snapshot=lambda pid, sha: {"pid": pid, "sha256": sha},
            task_snapshot=lambda pid: {pid: {"cpu_ticks": 0}, pid + 1: {"cpu_ticks": 0}})
        oracle = SimpleNamespace(Board=SimpleNamespace(from_fen=lambda: object()))
        reader = SimpleNamespace(read_regular=lambda path, limit: path.read_bytes())
        verifier = SimpleNamespace(support_modules=lambda: (scope, owner, oracle), input_reader=lambda: reader)
        owners = []

        def construct(*_args):
            item = Owned(123 + 100 * len(owners))
            owners.append(item)
            return item

        def launcher(_path, **kwargs):
            kwargs["record"].write_text("{}", encoding="utf-8")

        def group_observation(*_args):
            return group_path, {**group, "observed_at_utc": "new"}, {"frozen": True}

        def cgroup_file(path):
            return "populated 0\n" if path.name == "cgroup.events" else "123\n223\n323\n423\n"

        def worker(_pid, tid):
            return {"tid": tid, "start_ticks": tid + 1, "cpus": [0, 1],
                    "cpu_ticks_first": 0, "cpu_ticks_last": 1}

        def identity(pid):
            return {"pid": pid, "pgid": pid, "session": pid, "start_ticks": pid + 10, "alive": True}
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(subject.diagnostic, "read_candidates", return_value=([candidate], "d" * 64)), \
             mock.patch.object(subject.diagnostic, "_safe_output_path", side_effect=lambda p: Path(p)), \
             mock.patch.object(subject.diagnostic, "_profile_verifier", return_value=verifier), \
             mock.patch.object(subject.diagnostic.run, "verify_preexec_placement", return_value=True), \
             mock.patch.object(subject, "_verify_environment", side_effect=group_observation), \
             mock.patch.object(subject, "_pins"), mock.patch.object(subject, "_boot", return_value="boot"), \
             mock.patch.object(subject.functional, "_launcher", side_effect=launcher), \
             mock.patch.object(subject.functional, "_events", return_value={"oom": 0, "oom_kill": 0}), \
             mock.patch.object(subject.memory, "_file", side_effect=cgroup_file), \
             mock.patch.object(subject.placement, "_process_identity", side_effect=identity), \
             mock.patch.object(subject.peer, "construct_owned", side_effect=construct), \
             mock.patch.object(subject.peer, "_worker_evidence", side_effect=worker), \
             mock.patch.object(subject.peer, "_search", return_value={"bestmove": "e2e4"}), \
             mock.patch.object(subject.peer, "_finish_peer", return_value={"returncode": 0}):
            out = Path(tmp) / "lifecycle"
            report = subject.collect(candidate_path=Path("/unused"), candidate_sha256="d" * 64,
                artifact_id="a-p16", profile="test-p16", slot=slot, cgroup={},
                saved_ancestor_cpus=slot["cpus"], out=out)
            self.assertEqual([row["label"] for row in report["sessions"]], list(subject.LABELS))
            self.assertTrue(report["complete"])
            self.assertFalse(report["performance_eligible"])
            self.assertEqual(report["per_session_wall_seconds"], 180)
            self.assertGreaterEqual(report["elapsed_seconds"], 0)
            self.assertFalse(any(report["claims"].values()))
            self.assertEqual(owners[2].sent[-1], b"quit\n")
            self.assertTrue(owners[3].input_closed)
            self.assertEqual(json.loads((out / "lifecycle.json").read_text())["candidate_set_sha256"], "d" * 64)
            owners.clear()
            subject.peer._search.side_effect = ValueError("synthetic search failure")
            failed_out = Path(tmp) / "failed"
            with self.assertRaises(subject.functional.FunctionalProbeFailure):
                subject.collect(candidate_path=Path("/unused"), candidate_sha256="d" * 64,
                    artifact_id="a-p16", profile="test-p16", slot=slot, cgroup={},
                    saved_ancestor_cpus=slot["cpus"], out=failed_out)
            failed = json.loads((failed_out / "lifecycle.json").read_text())
            self.assertFalse(failed["complete"])
            self.assertFalse(failed["sessions"][0]["complete"])
            self.assertFalse(failed["claims"]["score_authorized"])
            self.assertEqual(owners[0].cleanup_calls, 1)
            owners.clear()
            subject.peer._search.side_effect = None
            duplicate_out = Path(tmp) / "duplicate"
            with mock.patch.object(subject.peer, "construct_owned", side_effect=lambda *_args: Owned(123)):
                with self.assertRaises(subject.functional.FunctionalProbeFailure):
                    subject.collect(candidate_path=Path("/unused"), candidate_sha256="d" * 64,
                        artifact_id="a-p16", profile="test-p16", slot=slot, cgroup={},
                        saved_ancestor_cpus=slot["cpus"], out=duplicate_out)
            duplicate = json.loads((duplicate_out / "lifecycle.json").read_text())
            self.assertFalse(duplicate["complete"])
            self.assertIn("reused an observed process identity", duplicate["failure"]["message"])


@unittest.skipUnless(sys.platform == "linux" and Path("/proc/self/exe").exists(),
                     "requires Linux process ownership and /proc")
class OwnedToyTests(unittest.TestCase):
    """Real toy child and worker, with no chess engine or large allocation."""

    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[3]

        def load(name, path):
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            return module

        cls.scope = load("lifecycle_toy_scope", root / "engines/experiments/tcec-scope/verify.py")
        cls.owner = load("lifecycle_toy_owner", root / "engines/compact/tiny-entry-d/verify.py")
        cls.native_sha = hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()
        rows = Path("/proc/self/cgroup").read_text(encoding="ascii").splitlines()
        unified = [row.split("::", 1)[1] for row in rows if row.startswith("0::")]
        if len(unified) != 1:
            raise unittest.SkipTest("visible cgroup v2 membership unavailable")
        cls.group_path = Path("/sys/fs/cgroup") / unified[0].lstrip("/")
        if not (cls.group_path / "cgroup.procs").is_file():
            raise unittest.SkipTest("visible cgroup.procs unavailable")

    def test_actual_owned_active_quit_and_eof(self):
        for label in ("active-quit", "active-eof"):
            with self.subTest(label=label), tempfile.TemporaryDirectory(prefix="rove-lifecycle-toy-") as tmp:
                root = Path(tmp)
                script = root / "toy"
                script.write_text(
                    "#!" + sys.executable + "\n"
                    "import sys,threading\n"
                    "done=threading.Event(); worker=None\n"
                    "def spin():\n"
                    " while not done.is_set(): pass\n"
                    "try:\n"
                    " for line in sys.stdin:\n"
                    "  cmd=line.strip()\n"
                    "  if cmd=='uci': print('id name lifecycle-toy\\nuciok',flush=True)\n"
                    "  elif cmd=='isready': print('readyok',flush=True)\n"
                    "  elif cmd.startswith('go '):\n"
                    "   worker=threading.Thread(target=spin);worker.start()\n"
                    "  elif cmd=='quit': break\n"
                    "finally:\n"
                    " done.set()\n"
                    " if worker: worker.join()\n",
                    encoding="utf-8")
                script.chmod(0o700)
                owned = self.owner.Owned(script, root / "owned", self.owner.Budget(15))
                try:
                    identity = subject.placement._process_identity(owned.process.pid)
                    self.assertEqual((identity["pid"], identity["pgid"], identity["session"]),
                                     (owned.process.pid,) * 3)
                    self.assertGreater(identity["start_ticks"], 0)
                    subject._startup(owned, time.monotonic())
                    observed = subject._active_termination(owned, self.scope,
                        sorted(os.sched_getaffinity(owned.process.pid)), label,
                        expected_identity=identity, group_path=self.group_path,
                        native_sha256=self.native_sha, maximum=5)
                    self.assertGreater(observed["observed_progress_before_request"]["cpu_ticks_last"],
                                       observed["observed_progress_before_request"]["cpu_ticks_before_go"])
                    self.assertFalse(observed["complete_worker_set_proven"])
                    finished = subject.peer._finish_peer(owned, seconds=5)
                    self.assertTrue(finished["original_identity_retained_until_other_members_absent"])
                    cleanup = owned.cleanup()
                    self.assertTrue(cleanup["owned_group_absent"])
                    self.assertTrue(cleanup["readers_joined"])
                    self.assertFalse(cleanup["forced_cleanup"])
                finally:
                    if not owned.reaped:
                        if not owned.exited():
                            try:
                                owned.send(b"quit\n")
                            except (BrokenPipeError, OSError, ValueError):
                                owned.close_input()
                        self.scope.finish_owned(owned)
                    owned.cleanup()


if __name__ == "__main__":
    unittest.main()
