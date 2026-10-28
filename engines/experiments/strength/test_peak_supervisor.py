"""Protocol tests only: no real engines, cgroups, subprocesses or TT."""
import hashlib
import json
import socket
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    from . import peak_supervisor as peak, peak_probe_session, peak_ready_probe, peak_receipt, test_peak_receipt
except ImportError:
    import peak_supervisor as peak
    import peak_probe_session
    import peak_ready_probe
    import peak_receipt
    import test_peak_receipt


class FakeObserver:
    def __init__(self, **_):
        self.groups = {"controller": SimpleNamespace(path=None, device=1, inode=2, cpus=(0,))}
        self.events = []

    def begin(self):
        self.events.append("begin")

    def sample_active(self, **kwargs):
        self.events.append(("sample", kwargs))

    def finish(self, **kwargs):
        self.events.append(("finish", kwargs))
        report = {"runtime_admission": False, "scored_qualification": False}
        raw = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        report["observation_sha256"] = hashlib.sha256(raw).hexdigest()
        return report


@unittest.skipUnless(os.name == "posix" and hasattr(os, "sched_setaffinity"), "Linux diagnostic protocol")
class PeakSupervisorTests(unittest.TestCase):
    def test_live_measurement_allows_diagnostic_but_not_scored_admission(self):
        assessment = {"format": "rove4k-diagnostic-capacity-assessment-v1", "profile": "test-p192",
                      "runtime_admission": False, "launch_permitted": False,
                      "unresolved": ["hidden_ancestors", "exclusive_cgroup_and_host_writers",
                                     "representative_overhead_bound", "trusted_loaded_source"]}
        with patch.object(peak_probe_session, "_require_delegated_root") as check_root, \
             patch.object(peak.peak_capacity, "inspect_capacity", return_value=assessment) as inspect:
            observed = peak._require_live_capacity_owner(profile="test-p192", root="/selected",
                                                         frozen_topology={}, groups={}, controller={})
        self.assertIs(observed, assessment)
        check_root.assert_called_once_with(Path("/selected"))
        inspect.assert_called_once()
        self.assertFalse(observed["runtime_admission"])

    def test_observed_capacity_precedes_observer_and_process_start(self):
        events = []
        assessment = {"format": "rove4k-diagnostic-capacity-assessment-v1", "profile": "test-p192",
                      "runtime_admission": False, "launch_permitted": False,
                      "unresolved": ["hidden_ancestors", "representative_overhead_bound"]}
        observer = FakeObserver()
        observer.begin = lambda: events.append("observer.begin")
        def inspect(**kwargs):
            events.append("inspect_capacity")
            return assessment
        def launch(*args, **kwargs):
            events.append("Popen")
            raise OSError("fixture launch")
        with patch.object(peak, "_validate_probe_command"), \
             patch.object(peak_probe_session, "_require_delegated_root", side_effect=lambda root: events.append("cgroup2.mount")), \
             patch.object(peak.peak_capacity, "inspect_capacity", side_effect=inspect), \
             patch.object(peak.overhead, "CohortPeakObserver", return_value=observer), \
             patch.object(peak.overhead, "_sha_file", return_value="b" * 64), \
             patch.object(peak, "_group_records", return_value={}), \
             patch.object(peak, "_verify_handoff"), \
             patch.object(peak.os, "open", return_value=999), \
             patch.object(peak.os, "fstat", return_value=SimpleNamespace(st_dev=1, st_ino=2)), \
             patch.object(peak.os, "close"), \
             patch.object(peak.threading, "active_count", return_value=1), \
             patch.object(peak.subprocess, "Popen", side_effect=launch):
            with self.assertRaisesRegex(peak.SupervisorFailure, "fixture launch"):
                peak.observe(profile="test-p192", root="/selected", games=[], controller="/selected/control",
                    runner_sha256="a" * 64, controller_sha256="b" * 64, argv=["/controller"],
                    frozen_topology={}, group_records={}, controller_record={},
                    per_game_headroom_bytes=1, controller_headroom_bytes=1, timeout_seconds=2)
        self.assertEqual(events, ["cgroup2.mount", "inspect_capacity", "observer.begin", "Popen"])

    def test_inadequate_observed_capacity_never_creates_a_process(self):
        with patch.object(peak, "_validate_probe_command"), \
             patch.object(peak_probe_session, "_require_delegated_root"), \
             patch.object(peak.peak_capacity, "inspect_capacity", side_effect=ValueError("capacity too small")), \
             patch.object(peak.overhead, "CohortPeakObserver") as observer, \
             patch.object(peak.subprocess, "Popen") as launch:
            with self.assertRaisesRegex(ValueError, "capacity too small"):
                peak.observe(profile="test-p192", root="/selected", games=[], controller="/selected/control",
                    runner_sha256="a" * 64, controller_sha256="b" * 64, argv=["/controller"],
                    frozen_topology={}, group_records={}, controller_record={},
                    per_game_headroom_bytes=1, controller_headroom_bytes=1, timeout_seconds=2)
            observer.assert_not_called()
            launch.assert_not_called()

    def supervise(self, messages):
        observer = FakeObserver()
        process = SimpleNamespace(pid=321)
        results = []
        workers = []

        def launch(*_, **kwargs):
            self.assertEqual(set(kwargs["env"]), {"PATH", "LANG", "TZ", peak._FD_ENV})
            fd = kwargs["pass_fds"][0]
            # Model exec inheriting a distinct descriptor in the child.
            sock = socket.fromfd(fd, socket.AF_UNIX, socket.SOCK_STREAM)
            def run():
                channel = peak._Channel(sock)
                try:
                    channel.receive(peak.time.monotonic() + 2)
                    for msg in messages:
                        channel.send(msg)
                        results.append(channel.receive(peak.time.monotonic() + 2))
                except (OSError, EOFError, TimeoutError):
                    pass
                finally:
                    sock.close()
            thread = threading.Thread(target=run)
            thread.start()
            workers.append(thread)
            return process

        assessment = {"runtime_admission": False, "launch_permitted": False,
                      "unresolved": ["hidden_ancestors", "representative_overhead_bound"]}
        with patch.object(peak, "_validate_probe_command"), \
             patch.object(peak, "_require_live_capacity_owner", return_value=assessment), \
             patch.object(peak, "_verify_handoff"), \
             patch.object(peak.overhead, "CohortPeakObserver", return_value=observer), \
             patch.object(peak.overhead, "_sha_file", return_value="b" * 64), \
             patch.object(peak, "_group_records", return_value={"kind": "groups", "games": {}, "controller": {}, "runtime_admission": False}), \
             patch.object(peak.os, "open", return_value=999), \
             patch.object(peak.os, "fstat", return_value=SimpleNamespace(st_dev=1, st_ino=2)), \
             patch.object(peak.os, "close"), \
             patch.object(peak.threading, "active_count", return_value=1), \
             patch.object(peak.subprocess, "Popen", side_effect=launch):
            try:
                report, returned_process = peak.observe(profile="test-p192", root="/unused", games=[],
                    controller="/unused/control", runner_sha256="a" * 64, controller_sha256="b" * 64,
                    argv=["/controller"], per_game_headroom_bytes=1, controller_headroom_bytes=1,
                    timeout_seconds=2)
                outcome = (report, returned_process)
            except peak.SupervisorFailure as error:
                outcome = error
        for worker in workers:
            worker.join(3)
            self.assertFalse(worker.is_alive())
        return outcome, observer, process, results

    def test_full_protocol_reports_diagnostic_only_and_preserves_child_handle(self):
        members = {"slot-000": {"runner": 11, "engines": [12, 13]}}
        outcome, observer, process, responses = self.supervise([
            {"kind": "active", "members": members}, {"kind": "settled"}])
        report, returned = outcome
        self.assertIs(returned, process)
        self.assertFalse(report["runtime_admission"])
        self.assertEqual(report["capacity_preflight"]["unresolved"], ["hidden_ancestors", "representative_overhead_bound"])
        self.assertEqual(observer.events[0], "begin")
        self.assertEqual(observer.events[1][1]["members"], members)
        self.assertEqual(observer.events[1][1]["controller_pid"], 321)
        self.assertEqual([r["kind"] for r in responses], ["sampled", "finished"])
        self.assertTrue(all(r["runtime_admission"] is False for r in responses))

    def test_invalid_order_fails_without_terminating_child(self):
        error, observer, process, _ = self.supervise([{"kind": "settled"}])
        self.assertIsInstance(error, peak.SupervisorFailure)
        self.assertIs(error.process, process)
        self.assertEqual(observer.events, ["begin"])

    def test_malformed_settlement_has_no_report_or_kill(self):
        error, observer, process, _ = self.supervise([
            {"kind": "active", "members": {}}, {"kind": "settled", "extra": True}])
        self.assertIsInstance(error, peak.SupervisorFailure)
        self.assertIs(error.process, process)
        self.assertEqual([row if isinstance(row, str) else row[0] for row in observer.events], ["begin", "sample"])

    def test_stalled_settlement_times_out_but_preserves_owned_child(self):
        original_receive = peak._Channel.receive
        supervisor_thread = threading.current_thread()
        supervisor_receives = []

        def receive(channel, deadline):
            if threading.current_thread() is supervisor_thread:
                supervisor_receives.append(deadline)
                if len(supervisor_receives) == 2:
                    self.assertIsNotNone(deadline)
                    raise TimeoutError("diagnostic protocol deadline expired; child not terminated")
            return original_receive(channel, deadline)

        with patch.object(peak._Channel, "receive", autospec=True, side_effect=receive):
            error, observer, process, responses = self.supervise([{"kind": "active", "members": {}}])
        self.assertIsInstance(error, peak.SupervisorFailure)
        self.assertIn("deadline expired", str(error))
        self.assertIs(error.process, process)
        self.assertEqual(len(supervisor_receives), 2)
        self.assertEqual([row if isinstance(row, str) else row[0] for row in observer.events], ["begin", "sample"])
        self.assertEqual([response["kind"] for response in responses], ["sampled"])

    def test_controller_requires_active_before_settled(self):
        left, right = socket.socketpair()
        try:
            with patch.dict(peak.os.environ, {peak._FD_ENV: str(left.detach())}):
                channel = peak.ControllerChannel()
            with self.assertRaises(ValueError):
                channel.settled()
            channel.channel.sock.close()
        finally:
            right.close()

    def test_controller_observation_failure_does_not_raise_into_game_loop(self):
        left, right = socket.socketpair()
        try:
            with patch.dict(peak.os.environ, {peak._FD_ENV: str(left.detach())}):
                channel = peak.ControllerChannel()
            channel.state = "groups"
            right.close()
            self.assertFalse(channel.active({"slot-000": {"runner": 1, "engines": [2, 3]}}))
            self.assertEqual(channel.state, "unavailable")
            channel.channel.sock.close()
        finally:
            right.close()

    def test_controller_hash_mismatch_fails_before_any_launch(self):
        with patch.object(peak, "_validate_probe_command"), \
             patch.object(peak, "_require_live_capacity_owner"), \
             patch.object(peak.overhead, "_sha_file", return_value="c" * 64), \
             patch.object(peak.threading, "active_count", return_value=1), \
             patch.object(peak.subprocess, "Popen") as launch:
            with self.assertRaisesRegex(ValueError, "digest differs"):
                peak.observe(profile="test-p192", root="/unused", games=[], controller="/unused/control",
                    runner_sha256="a" * 64, controller_sha256="b" * 64, argv=["/controller"],
                    per_game_headroom_bytes=1, controller_headroom_bytes=1, timeout_seconds=2)
            launch.assert_not_called()

    def test_interrupt_retains_owned_child_for_reconciliation(self):
        observer, process = FakeObserver(), SimpleNamespace(pid=321)
        with patch.object(peak, "_validate_probe_command"), \
             patch.object(peak, "_require_live_capacity_owner"), \
             patch.object(peak, "_verify_handoff"), \
             patch.object(peak.overhead, "CohortPeakObserver", return_value=observer), \
             patch.object(peak.overhead, "_sha_file", return_value="b" * 64), \
             patch.object(peak, "_group_records", return_value={"kind": "groups", "games": {}, "controller": {}, "runtime_admission": False}), \
             patch.object(peak.os, "open", return_value=999), \
             patch.object(peak.os, "fstat", return_value=SimpleNamespace(st_dev=1, st_ino=2)), \
             patch.object(peak.os, "close"), \
             patch.object(peak.threading, "active_count", return_value=1), \
             patch.object(peak.subprocess, "Popen", return_value=process), \
             patch.object(peak, "_failure_snapshot", side_effect=OSError("cannot capture")), \
             patch.object(peak._Channel, "send"), \
             patch.object(peak._Channel, "receive", side_effect=KeyboardInterrupt):
            with self.assertRaises(peak.SupervisorFailure) as caught:
                peak.observe(profile="test-p192", root="/unused", games=[], controller="/unused/control",
                    runner_sha256="a" * 64, controller_sha256="b" * 64, argv=["/controller"],
                    per_game_headroom_bytes=1, controller_headroom_bytes=1, timeout_seconds=2)
            self.assertIs(caught.exception.process, process)
            self.assertIn("cannot capture", caught.exception.evidence["snapshot_error"])
            self.assertFalse(caught.exception.evidence["all_groups_read"])

    def test_pre_ready_eof_captures_oom_without_killing_owner(self):
        observer, process = FakeObserver(), SimpleNamespace(pid=321)
        observer.groups["controller"].events = {"oom": 0, "oom_kill": 0, "oom_group_kill": 0}
        observer.groups["controller"].path = Path("/unused/control")
        final_group = SimpleNamespace(path=Path("/unused/control"), device=1, inode=2,
                                      events={"oom": 1, "oom_kill": 1, "oom_group_kill": 0})
        observer._read_group = lambda *_: (final_group, 4096, 8192, {"populated": 1}, {321})
        assessment = {"runtime_admission": False, "launch_permitted": False,
                      "unresolved": ["representative_overhead_bound"]}
        with patch.object(peak, "_validate_probe_command"), \
             patch.object(peak, "_require_live_capacity_owner", return_value=assessment), \
             patch.object(peak, "_verify_handoff"), \
             patch.object(peak.overhead, "CohortPeakObserver", return_value=observer), \
             patch.object(peak.overhead, "_sha_file", return_value="b" * 64), \
             patch.object(peak, "_group_records", return_value={}), \
             patch.object(peak.os, "open", return_value=999), \
             patch.object(peak.os, "fstat", return_value=SimpleNamespace(st_dev=1, st_ino=2)), \
             patch.object(peak.os, "close"), \
             patch.object(peak.threading, "active_count", return_value=1), \
             patch.object(peak.subprocess, "Popen", return_value=process), \
             patch.object(peak._Channel, "send"), \
             patch.object(peak._Channel, "receive", side_effect=EOFError("pre-READY EOF")):
            with self.assertRaisesRegex(peak.SupervisorFailure, "pre-READY EOF") as caught:
                peak.observe(profile="test-p192", root="/unused", games=[], controller="/unused/control",
                    runner_sha256="a" * 64, controller_sha256="b" * 64, argv=["/controller"],
                    per_game_headroom_bytes=1, controller_headroom_bytes=1, timeout_seconds=2)
        self.assertIs(caught.exception.process, process)
        evidence = caught.exception.evidence
        self.assertTrue(evidence["oom_observed"])
        self.assertTrue(evidence["all_groups_read"])
        self.assertEqual(evidence["groups"][0]["observed_events"]["oom_kill"], 1)
        self.assertFalse(evidence["physical_settlement_proven"])
        self.assertFalse(evidence["runtime_admission"])

    def test_failure_snapshot_does_not_treat_a_replaced_group_as_clear(self):
        observer = FakeObserver()
        observer.groups["controller"].events = {"oom": 0, "oom_kill": 0, "oom_group_kill": 0}
        observer.groups["controller"].path = Path("/unused/control")
        changed = SimpleNamespace(path=Path("/unused/control"), device=1, inode=999,
                                  events={"oom": 0, "oom_kill": 0, "oom_group_kill": 0})
        observer._read_group = lambda *_: (changed, 0, 0, {"populated": 0}, set())
        evidence = peak._failure_snapshot(observer, {}, EOFError("lost runner"))
        self.assertFalse(evidence["all_groups_read"])
        self.assertIn("identity changed", evidence["groups"][0]["read_error"])
        self.assertFalse(evidence["physical_settlement_proven"])

    def test_existing_oom_evidence_survives_later_group_read_failure(self):
        observer = FakeObserver()
        observer.groups["controller"].path = Path("/unused/control")
        observer._read_group = lambda *_: (_ for _ in ()).throw(OSError("group disappeared"))
        original = {"initial_events": {"oom": 0, "oom_kill": 0},
                    "final_events": {"oom": 1, "oom_kill": 1}}
        evidence = peak._failure_snapshot(observer, {}, peak.overhead.ObservationFailure("OOM", original))
        self.assertTrue(evidence["oom_observed"])
        self.assertFalse(evidence["all_groups_read"])
        self.assertEqual(evidence["initial_observation_failure"], original)

    def test_missing_live_capacity_owner_rejects_before_process_start(self):
        with patch.object(peak, "_validate_probe_command"), \
             patch.object(peak.subprocess, "Popen") as launch, \
             patch.object(peak.overhead, "CohortPeakObserver") as observer:
            with self.assertRaisesRegex(ValueError, "original live capacity"):
                peak.observe(profile="test-p192", root="/unused", games=[], controller="/unused/control",
                    runner_sha256="a" * 64, controller_sha256="b" * 64, argv=["/controller"],
                    per_game_headroom_bytes=1, controller_headroom_bytes=1, timeout_seconds=2)
            launch.assert_not_called()
            observer.assert_not_called()

    def test_only_pinned_probe_can_receive_the_capacity_checked_cohort(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = [str(Path(sys.executable).resolve()), str(Path(peak_ready_probe.__file__).resolve()),
                       "--manifest", str(Path(tmp) / "plan.json"), "--manifest-sha256", "a" * 64]
            slot = SimpleNamespace(id="slot-000", cpus=(0, 1), memory_nodes=(0,))
            first = {"id": "A", "path": "/engine-a", "whole_sha256": "1" * 64,
                     "native_sha256": "2" * 64, "tt_bytes": 100}
            second = {"id": "B", "path": "/engine-b", "whole_sha256": "3" * 64,
                      "native_sha256": "4" * 64, "tt_bytes": 200}
            games = [{"slot": slot.id, "cpus": [0, 1], "nodes": [0],
                      "artifacts": [{key: row[key] for key in ("id", "whole_sha256", "native_sha256", "tt_bytes")}
                                    for row in (first, second)]}]
            manifest = {"profile": "test-p192", "topology": {"pinned": True}, "runner_sha256": "b" * 64,
                        "entries": [{"slot": slot, "engines": [first, second]}]}
            with patch.object(peak_ready_probe, "load_controller_manifest", return_value=manifest):
                peak._validate_probe_command(command, profile="test-p192", games=games,
                                             runner_sha256="b" * 64, frozen_topology={"pinned": True})
                with self.assertRaisesRegex(ValueError, "extents differ"):
                    games[0]["artifacts"][0]["tt_bytes"] = 99
                    peak._validate_probe_command(command, profile="test-p192", games=games,
                                                 runner_sha256="b" * 64, frozen_topology={"pinned": True})
                with self.assertRaisesRegex(ValueError, "only the pinned"):
                    peak._validate_probe_command([command[0], command[0], *command[2:]],
                        profile="test-p192", games=games, runner_sha256="b" * 64, frozen_topology={"pinned": True})

    def test_preflight_is_bound_to_receipt_without_granting_qualification(self):
        report, expected = test_peak_receipt.sample()
        assessment = {"runtime_admission": False, "launch_permitted": False,
                      "unresolved": ["hidden_ancestors", "exclusive_cgroup_and_host_writers"]}
        combined = peak._bind_capacity_report(report, assessment)
        checked = peak_receipt.inspect_diagnostic(combined, expected=expected)
        self.assertFalse(checked["runtime_admission"])
        self.assertEqual(combined["capacity_preflight"], assessment)
        combined["capacity_preflight"]["unresolved"].clear()
        with self.assertRaisesRegex(ValueError, "digest differs"):
            peak_receipt.inspect_diagnostic(combined, expected=expected)

    def test_cgroup_handoff_must_match_original_limits_and_inodes(self):
        group = {"path": "/sys/fs/cgroup/root/g", "device": 1, "inode": 2,
                 "cpus": [0], "memory_nodes": [0], "memory_max": 4096}
        controller = {**group, "path": "/sys/fs/cgroup/root/controller", "inode": 3}
        handoff = {"games": {"slot-000": dict(group)}, "controller": dict(controller)}
        peak._verify_handoff(handoff, {"slot-000": group}, controller)
        for key, value in (("inode", 999), ("memory_max", 8192), ("cpus", [1])):
            with self.subTest(key=key):
                changed = dict(group)
                changed[key] = value
                with self.assertRaisesRegex(ValueError, "changed after preflight"):
                    peak._verify_handoff({**handoff, "games": {"slot-000": changed}},
                                         {"slot-000": group}, controller)


if __name__ == "__main__":
    unittest.main()
