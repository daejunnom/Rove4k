"""Protocol tests only: no real engines, cgroups, subprocesses or TT."""
import socket
import os
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    from . import peak_supervisor as peak
except ImportError:
    import peak_supervisor as peak


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
        return {"runtime_admission": False, "scored_qualification": False}


@unittest.skipUnless(os.name == "posix" and hasattr(os, "sched_setaffinity"), "Linux diagnostic protocol")
class PeakSupervisorTests(unittest.TestCase):
    def test_live_measurement_still_cannot_create_admission_authority(self):
        assessment = {"runtime_admission": False, "launch_permitted": False,
                      "unresolved": ["hidden_ancestors", "exclusive_cgroup_and_host_writers",
                                     "representative_overhead_bound", "trusted_loaded_source"]}
        with patch.object(peak.peak_capacity, "inspect_capacity", return_value=assessment), \
             patch.object(peak.subprocess, "Popen") as popen:
            with self.assertRaises(peak.CapacityPending) as caught:
                peak._require_live_capacity_owner(frozen_topology={}, groups={}, controller={})
        self.assertIs(caught.exception.assessment, assessment)
        popen.assert_not_called()

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

        with patch.object(peak, "_require_live_capacity_owner"), \
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
        with patch.object(peak, "_require_live_capacity_owner"), \
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
        with patch.object(peak, "_require_live_capacity_owner"), \
             patch.object(peak.overhead, "CohortPeakObserver", return_value=observer), \
             patch.object(peak.overhead, "_sha_file", return_value="b" * 64), \
             patch.object(peak, "_group_records", return_value={"kind": "groups", "games": {}, "controller": {}, "runtime_admission": False}), \
             patch.object(peak.os, "open", return_value=999), \
             patch.object(peak.os, "fstat", return_value=SimpleNamespace(st_dev=1, st_ino=2)), \
             patch.object(peak.os, "close"), \
             patch.object(peak.threading, "active_count", return_value=1), \
             patch.object(peak.subprocess, "Popen", return_value=process), \
             patch.object(peak._Channel, "receive", side_effect=KeyboardInterrupt):
            with self.assertRaises(peak.SupervisorFailure) as caught:
                peak.observe(profile="test-p192", root="/unused", games=[], controller="/unused/control",
                    runner_sha256="a" * 64, controller_sha256="b" * 64, argv=["/controller"],
                    per_game_headroom_bytes=1, controller_headroom_bytes=1, timeout_seconds=2)
            self.assertIs(caught.exception.process, process)

    def test_missing_live_capacity_owner_rejects_before_process_start(self):
        with patch.object(peak.subprocess, "Popen") as launch, \
             patch.object(peak.overhead, "CohortPeakObserver") as observer:
            with self.assertRaisesRegex(ValueError, "authenticated live capacity owner"):
                peak.observe(profile="test-p192", root="/unused", games=[], controller="/unused/control",
                    runner_sha256="a" * 64, controller_sha256="b" * 64, argv=["/controller"],
                    per_game_headroom_bytes=1, controller_headroom_bytes=1, timeout_seconds=2)
            launch.assert_not_called()
            observer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
