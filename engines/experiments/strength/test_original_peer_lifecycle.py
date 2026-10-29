"""Owned original-peer orchestration checks using toy streams, never a large TT."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import original_peer_lifecycle as subject


class Stream:
    def __init__(self):
        self.data = b""

    def bytes(self):
        return self.data

    def until(self, predicate, _budget, *, seconds):
        if seconds <= 0 or not predicate(self.data):
            raise TimeoutError("toy stream missing response")


class ToyOwned:
    def __init__(self):
        self.stdout, self.budget = Stream(), SimpleNamespace(left=lambda value: value)
        self.process = SimpleNamespace(pid=123)
        self.sent, self.cleanup_calls = [], 0

    def send(self, command):
        self.sent.append(command)
        if command == b"uci\n":
            self.stdout.data += (b"id name ice4 v6.1\n"
                b"option name Hash type spin default 8 min 1 max 67108864\n"
                b"option name Threads type spin default 1 min 1 max 2048\n"
                b"option name Ponder type check default true\nuciok\n")
        if b"isready\n" in command:
            self.stdout.data += b"readyok\n"

    def wait_line(self, line, count):
        if self.stdout.data.splitlines().count(line) != count:
            raise TimeoutError("toy stream missing acknowledgement")

    def close_input(self):
        pass

    def exited(self):
        return False

    def cleanup(self):
        self.cleanup_calls += 1
        return {"owned_group_absent": True, "readers_joined": True,
                "forced_cleanup": False, "errors": []}


class OriginalPeerLifecycleTests(unittest.TestCase):
    def test_infinite_stop_waits_for_activity_and_requires_one_legal_move(self):
        class StopToy(ToyOwned):
            def __init__(self, response, *, late=False, early=False):
                super().__init__()
                self.response, self.late, self.early = response, late, early

            def send(self, command):
                self.sent.append(command)
                if command == b"position startpos\ngo infinite\n" and self.early:
                    self.stdout.data += b"bestmove e2e4\n"
                if command == b"stop\n":
                    self.stdout.data += self.response
                if command == b"isready\n":
                    self.stdout.data += (b"bestmove e2e4\n" if self.late else b"") + b"readyok\n"

        board = SimpleNamespace(legal_moves=lambda: ["e2e4", "g1f3"])
        oracle = SimpleNamespace(Board=SimpleNamespace(from_fen=lambda: board))
        worker = {"tid": 124, "start_ticks": 5, "cpus": [0, 1],
                  "cpu_ticks_first": 1, "cpu_ticks_last": 2}
        def run(owned):
            snapshots = iter(({123: {"cpu_ticks": 0}, 124: {"cpu_ticks": 0}},
                              {123: {"cpu_ticks": 0}, 124: {"cpu_ticks": 2}}))
            scope = SimpleNamespace(task_snapshot=lambda _: next(snapshots))
            with mock.patch.object(subject.peer, "_worker_evidence", return_value=worker):
                return subject._infinite_stop(owned, scope, oracle, [0, 1])

        owned = StopToy(b"bestmove e2e4\n")
        result = run(owned)
        self.assertEqual(owned.sent, [b"position startpos\ngo infinite\n", b"stop\n", b"isready\n"])
        self.assertEqual(result["bestmove"], "e2e4")
        self.assertTrue(result["ready_observed"])
        self.assertIn("timed GO stop responsiveness is unproved", result["scope"])
        for response, late, message in ((b"bestmove a1a8\n", False, "illegal"),
                                        (b"bestmove e2e4\nbestmove g1f3\n", False, "duplicate"),
                                        (b"bestmove e2e4\n", True, "late duplicate")):
            with self.subTest(response=response, late=late), self.assertRaisesRegex(ValueError, message):
                run(StopToy(response, late=late))
        early = StopToy(b"bestmove e2e4\n", early=True)
        with self.assertRaisesRegex(ValueError, "ended before stop"):
            run(early)
        self.assertEqual(early.sent, [b"position startpos\ngo infinite\n"])

    def test_recheck_allows_historical_peak_but_rejects_changed_owner_and_topology(self):
        group_path = Path("toy-group")
        group = {"path": str(group_path), "device": 1, "inode": 2, "cpus": [0],
                 "memory_nodes": [0], "memory_max": 300 << 30}
        original = subject.lifecycle._group_identity(group)
        snapshot = {"cpus": [0], "nodes": [0]}

        def only_events(path):
            self.assertEqual(path, group_path / "cgroup.events", "must not inspect cumulative memory.peak")
            return "populated 0\n"

        with mock.patch.object(subject.placement, "verify_cgroup_live", return_value=group.copy()) as live, \
             mock.patch.object(subject.memory, "_file", side_effect=only_events) as files, \
             mock.patch.object(subject.functional.peak_capacity, "_require_empty", side_effect=AssertionError("peak is cumulative")), \
             mock.patch.object(subject.lifecycle.topology.Topology, "snapshot_target",
                 return_value=SimpleNamespace(to_record=lambda: snapshot)) as topology, \
             mock.patch.object(subject.lifecycle, "_boot", return_value="boot") as boot:
            subject._recheck_environment(group_path, group, original, snapshot, "boot")
            files.assert_called_once_with(group_path / "cgroup.events")
            topology.assert_called_once_with(group_path, device=1, inode=2)
            for key, value in (("inode", 3), ("device", 3), ("cpus", [1]),
                               ("memory_nodes", [1]), ("memory_max", 1)):
                with self.subTest(changed=key):
                    live.return_value = group | {key: value}
                    with self.assertRaisesRegex(ValueError, "identity or fixed limits changed"):
                        subject._recheck_environment(group_path, group, original, snapshot, "boot")
            live.return_value = group.copy()
            topology.return_value = SimpleNamespace(to_record=lambda: {"cpus": [1], "nodes": [0]})
            with self.assertRaisesRegex(ValueError, "boot or topology changed"):
                subject._recheck_environment(group_path, group, original, snapshot, "boot")
            topology.return_value = SimpleNamespace(to_record=lambda: snapshot)
            boot.return_value = "different"
            with self.assertRaisesRegex(ValueError, "boot or topology changed"):
                subject._recheck_environment(group_path, group, original, snapshot, "boot")
            boot.return_value = "boot"
            files.side_effect = lambda _: "populated 1\n"
            with self.assertRaisesRegex(ValueError, "not empty"):
                subject._recheck_environment(group_path, group, original, snapshot, "boot")

    def test_bad_arguments_fail_before_build_and_no_output(self):
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(subject.sys, "platform", "linux"), \
             mock.patch.object(subject.original, "build") as build:
            base = dict(peer_name="ice4", profile="test-p16", source_root=Path(tmp) / "src",
                        output=Path(tmp) / "out", slot={}, cgroup={}, saved_ancestor_cpus=[0])
            for bad in ({"peer_name": "ice4\nquit"}, {"profile": "submit-w256"},
                        {"wall_seconds": True}, {"wall_seconds": 89}, {"wall_seconds": 3601}):
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    subject.collect(**(base | bad))
            build.assert_not_called()
            self.assertFalse(base["output"].exists())

    def test_collect_reports_only_bounded_non_scoring_observation(self):
        slot = {"cpus": [0], "memory_nodes": [0], "policy": "default"}
        group = {"memory_max": 300 << 30}
        attempts = [{"bytes": 10, "sha256": "a" * 64}] * 2
        built = {"sha256": "b" * 64, "record": {"complete": True,
            "same_host_native_reproduced": True, "attempts": attempts,
            "revision": "toy", "source_closure_sha256": "c" * 64}}
        real_mkdir, real_open, real_close = subject.os.mkdir, subject.os.open, subject.os.close
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(subject.sys, "platform", "linux"), \
             mock.patch.object(subject.os, "O_DIRECTORY", getattr(subject.os, "O_DIRECTORY", 0), create=True), \
             mock.patch.object(subject.os, "O_NOFOLLOW", getattr(subject.os, "O_NOFOLLOW", 0), create=True), \
             mock.patch.object(subject.original.peer_exact_runner, "_open_directory", return_value=99991), \
             mock.patch.object(subject.original, "_guard_output_path"), \
             mock.patch.object(subject.os, "mkdir", side_effect=lambda p, mode=0o777, *, dir_fd=None: real_mkdir(Path(tmp) / p if dir_fd == 99991 else p, mode)), \
             mock.patch.object(subject.os, "open", side_effect=lambda p, flags, mode=0o777, *, dir_fd=None: 99992 if dir_fd == 99991 else real_open(p, flags, mode)), \
             mock.patch.object(subject.os, "close", side_effect=lambda fd: None if fd in (99991, 99992) else real_close(fd)), \
             mock.patch.object(subject.original, "_outside_checkout", side_effect=lambda p: p), \
             mock.patch.object(subject.lifecycle, "_verify_environment", return_value=(Path(tmp), group, {})) as initial, \
             mock.patch.object(subject, "_recheck_environment") as recheck, \
             mock.patch.object(subject.lifecycle, "_group_identity", return_value=(1, 2)), \
             mock.patch.object(subject.lifecycle, "_boot", return_value="toy"), \
             mock.patch.object(subject.os, "sched_getaffinity", return_value={0}, create=True), \
             mock.patch.object(subject.original, "build", return_value=built) as compile_peer, \
             mock.patch.object(subject, "_pins"), \
             mock.patch.object(subject, "_run_session", side_effect=lambda **kw: kw["sessions"].append({"label": kw["label"], "complete": True})) as session, \
             mock.patch.object(subject.functional, "_write_exclusive", side_effect=lambda path, raw: path.write_bytes(raw)):
            out = Path(tmp) / "out"
            report = subject.collect(peer_name="ice4", profile="test-p16", source_root=Path(tmp) / "src",
                output=out, slot=slot, cgroup={}, saved_ancestor_cpus=[0])
            self.assertTrue(report["complete"])
            self.assertEqual([row["label"] for row in report["sessions"]], list(subject.LABELS))
            self.assertEqual(initial.call_count, 1)
            self.assertEqual(recheck.call_count, len(subject.LABELS))
            for key in ("current_availability_enforced", "performance_eligible", "scored_game_admitted",
                        "league_qualified", "tt_abi_verified", "tt_allocation_observed"):
                self.assertIs(report[key], False, key)
            self.assertEqual(json.loads((out / "lifecycle.json").read_text()), report)
            group["memory_max"] = 1
            calls = compile_peer.call_count
            out = Path(tmp) / "insufficient-limit"
            with self.assertRaisesRegex(ValueError, "hard limit"):
                subject.collect(peer_name="ice4", profile="test-p16", source_root=Path(tmp) / "src",
                    output=out, slot=slot, cgroup={}, saved_ancestor_cpus=[0])
            self.assertEqual(compile_peer.call_count, calls)
            self.assertFalse(out.exists())
            group["memory_max"] = 300 << 30
            session.side_effect = lambda **kw: kw["sessions"].append({"label": kw["label"], "complete": False})
            out = Path(tmp) / "incomplete"
            with self.assertRaises(subject.functional.FunctionalProbeFailure):
                subject.collect(peer_name="ice4", profile="test-p16", source_root=Path(tmp) / "src",
                    output=out, slot=slot, cgroup={}, saved_ancestor_cpus=[0])
            incomplete = json.loads((out / "lifecycle.json").read_text())
            self.assertFalse(incomplete["complete"])
            self.assertFalse(incomplete["performance_eligible"])
            compile_peer.side_effect = RuntimeError("synthetic build failure")
            out = Path(tmp) / "failed"
            with self.assertRaises(subject.functional.FunctionalProbeFailure):
                subject.collect(peer_name="ice4", profile="test-p16", source_root=Path(tmp) / "src",
                    output=out, slot=slot, cgroup={}, saved_ancestor_cpus=[0])
            failed = json.loads((out / "lifecycle.json").read_text())
            self.assertEqual(failed["failure"]["message"], "synthetic build failure")
            self.assertFalse(failed["complete"])

    def test_session_checks_policy_before_hash_and_cleans_after_failure(self):
        slot = {"cpus": [0], "memory_nodes": [0], "policy": "default"}
        owned = ToyOwned()
        identity = {"pid": 123, "pgid": 123, "session": 123, "start_ticks": 4, "alive": True}
        group = {"memory_max": 300 << 30}
        build = {"attempts": [{"sha256": "a" * 64}]}
        scope = SimpleNamespace(image_snapshot=lambda *_: {})
        owner = SimpleNamespace(OWNED=[], Budget=lambda _: owned.budget)
        verifier = SimpleNamespace(support_modules=lambda: (scope, owner, object()),
            input_reader=lambda: SimpleNamespace(read_regular=lambda path, limit: path.read_bytes()))
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(subject.diagnostic, "_profile_verifier", return_value=verifier), \
             mock.patch.object(subject, "_launcher", side_effect=lambda _path, **kw: kw["record"].write_text(
                 json.dumps({"runtime_limits": {"address_space": [99, 99], "cpu": [10, 15]}}))), \
             mock.patch.object(subject.functional, "_events", return_value={"oom": 0, "oom_kill": 0}), \
             mock.patch.object(subject.functional, "_write_exclusive", side_effect=lambda path, raw: path.write_bytes(raw)), \
             mock.patch.object(subject.peer, "construct_owned", return_value=owned) as construct, \
             mock.patch.object(subject.placement, "_process_identity", return_value=identity), \
             mock.patch.object(subject.diagnostic.run, "verify_preexec_placement", return_value=True), \
             mock.patch.object(subject.lifecycle, "_current_owner"), \
             mock.patch.object(subject.os, "sched_getaffinity", return_value={0}, create=True) as affinity, \
             mock.patch.object(subject.placement, "verify_cgroup_live", return_value=group), \
             mock.patch.object(subject.lifecycle, "_group_identity", return_value=(1, 2)), \
             mock.patch.object(subject, "_mapping_observation", side_effect=ValueError("toy observation failed")), \
             mock.patch.object(subject.memory, "_file", return_value="populated 0\n"), \
             mock.patch.object(subject, "_pins"), \
             mock.patch.object(subject, "_recheck_environment"), \
             mock.patch.object(subject.lifecycle, "_boot", return_value="toy"):
            with self.assertRaisesRegex(ValueError, "toy observation failed"):
                subject._run_session(label="cold", peer_name="ice4", profile="test-p16", build_dir=Path(tmp),
                    build_record=build, output=Path(tmp), slot=slot, cgroup={}, saved_cpus=[0], saved_nodes=None,
                    group_path=Path(tmp), identity_group=(1, 2), snapshot={}, boot="toy", wall_seconds=90,
                    address_limit=99, cpu_limit=10, seen=set(), sessions=[])
            self.assertEqual(owned.sent, [b"uci\n", b"setoption name Hash value 16384\n",
                b"setoption name Threads value 16\n", b"setoption name Ponder value false\n",
                b"isready\n", b"ucinewgame\nisready\n"])
            self.assertEqual(owned.cleanup_calls, 1)
            rejected = ToyOwned()
            construct.return_value = rejected
            affinity.return_value = {1}
            rows = []
            with self.assertRaisesRegex(ValueError, "CPU mask differs"):
                subject._run_session(label="warm", peer_name="ice4", profile="test-p16", build_dir=Path(tmp),
                    build_record=build, output=Path(tmp), slot=slot, cgroup={}, saved_cpus=[0], saved_nodes=None,
                    group_path=Path(tmp), identity_group=(1, 2), snapshot={}, boot="toy", wall_seconds=90,
                    address_limit=99, cpu_limit=10, seen=set(), sessions=rows)
            self.assertEqual(rejected.sent, [b"uci\n"])
            self.assertEqual(rejected.cleanup_calls, 1)
            self.assertFalse(rows[0]["complete"])


if __name__ == "__main__":
    unittest.main()
