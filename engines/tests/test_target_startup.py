"""Small, non-launching regression checks for startup telemetry and ownership."""

from pathlib import Path
import resource
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

import target_startup as startup


class StartupAdmissionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="rove-startup-fixture-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.proc = self.root / "proc"
        self.proc.mkdir()
        self.cgroup = self.root / "cgroup"
        self.cgroup.mkdir()
        (self.proc / "meminfo").write_text("MemAvailable: 0 kB\n")
        (self.proc / "cgroup").write_text("0::/\n")
        (self.proc / "mountinfo").write_text(
            f"1 0 0:1 / {self.cgroup} rw - cgroup2 cgroup rw\n")
        (self.cgroup / "memory.max").write_text("100\n")
        (self.cgroup / "memory.current").write_text("100\n")
        (self.cgroup / "pids.max").write_text("1000\n")
        (self.cgroup / "pids.current").write_text("0\n")
        self.args = SimpleNamespace(minimum_available_bytes=8192, max_rss_bytes=4096,
                                    address_space_bytes=16000, data_bytes=14000,
                                    cpu_seconds=30, timeout_seconds=3)
        self.nproc = resource.RLIM_INFINITY
        self.paths = {
            "/proc": self.proc,
            "/proc/meminfo": self.proc / "meminfo",
            "/proc/self/cgroup": self.proc / "cgroup",
            "/proc/self/mountinfo": self.proc / "mountinfo",
        }
        self.path_patch = patch.object(startup, "Path", side_effect=self.fake_path)
        self.limit_patch = patch.object(startup.resource, "getrlimit", side_effect=self.getrlimit)
        self.path_patch.start()
        self.limit_patch.start()
        self.addCleanup(self.path_patch.stop)
        self.addCleanup(self.limit_patch.stop)
        startup._UNSETTLED.clear()
        self.addCleanup(startup._UNSETTLED.clear)

    def fake_path(self, value):
        return self.paths.get(str(value), Path(value))

    def getrlimit(self, kind):
        if kind == resource.RLIMIT_NPROC:
            return self.nproc, self.nproc
        if kind == resource.RLIMIT_AS:
            return 10000, 12000
        if kind == resource.RLIMIT_DATA:
            return 9000, 12000
        if kind == resource.RLIMIT_CPU:
            return 15, 20
        return resource.RLIM_INFINITY, resource.RLIM_INFINITY

    def test_zero_memory_and_cgroup_headroom_are_telemetry(self):
        admission = startup.resource_admission(4, self.args)
        self.assertNotIn("rejection", admission)
        self.assertEqual(admission["mem_available_bytes"], 0)
        self.assertEqual(admission["effective_available_bytes"], 0)
        self.assertEqual(admission["required_available_bytes"], 8192)
        self.assertEqual(admission["advisory_available_bytes"], 8192)
        self.assertIs(admission["advisory_available_met"], False)
        self.assertEqual(admission["cgroup_limits"][0]["memory"]["headroom"], 0)
        self.assertEqual(admission["applied_limits"], {
            "address_space_bytes": 10000, "data_bytes": 9000, "cpu_seconds": 15})

    def test_missing_or_malformed_memory_observation_does_not_block(self):
        for value in (None, "MemAvailable: no kB\n", "MemAvailable: 1 MB\n"):
            with self.subTest(value=value):
                if value is None:
                    (self.proc / "meminfo").unlink(missing_ok=True)
                else:
                    (self.proc / "meminfo").write_text(value)
                admission = startup.resource_admission(4, self.args)
                self.assertNotIn("rejection", admission)
                self.assertIsNone(admission["mem_available_bytes"])
                self.assertIsNone(admission["effective_available_bytes"])
                self.assertEqual(admission["observed_available_upper_bound_bytes"], 0)
                self.assertIs(admission["advisory_available_met"], False)

    def test_unknown_memory_without_a_known_bound_is_tristate_unknown(self):
        (self.proc / "meminfo").unlink()
        (self.cgroup / "memory.max").write_text("max\n")
        admission = startup.resource_admission(4, self.args)
        self.assertNotIn("rejection", admission)
        self.assertIsNone(admission["effective_available_bytes"])
        self.assertIsNone(admission["observed_available_upper_bound_bytes"])
        self.assertIsNone(admission["advisory_available_met"])

    def test_unreadable_memory_counter_is_unknown_not_a_gate(self):
        (self.proc / "meminfo").write_text("MemAvailable: 20 kB\n")
        (self.cgroup / "memory.current").write_text("not-a-number\n")
        admission = startup.resource_admission(4, self.args)
        self.assertNotIn("rejection", admission)
        self.assertEqual(admission["cgroup_limits"][0]["memory"], {"unavailable": True})
        self.assertIsNone(admission["effective_available_bytes"])
        self.assertEqual(admission["observed_available_upper_bound_bytes"], 20 * 1024)
        self.assertIsNone(admission["advisory_available_met"])

    def test_each_cgroup_memory_ancestor_is_telemetry_not_a_gate(self):
        (self.proc / "meminfo").write_text("MemAvailable: 20 kB\n")
        (self.proc / "cgroup").write_text("0::/outer/inner\n")
        (self.cgroup / "memory.max").write_text("max\n")
        outer = self.cgroup / "outer"
        inner = outer / "inner"
        inner.mkdir(parents=True)
        for directory, cap, used in ((outer, 8000, 4000), (inner, 10000, 8000)):
            (directory / "memory.max").write_text(str(cap))
            (directory / "memory.current").write_text(str(used))
        admission = startup.resource_admission(4, self.args)
        self.assertNotIn("rejection", admission)
        self.assertEqual(admission["effective_available_bytes"], 2000)
        self.assertIs(admission["advisory_available_met"], False)
        rows = admission["cgroup_limits"]
        self.assertEqual([row["path"] for row in rows], [str(inner), str(outer), str(self.cgroup)])
        self.assertEqual([row["memory"].get("headroom") for row in rows], [2000, 4000, None])

    def test_memory_existence_permission_failure_is_telemetry_unknown(self):
        (self.proc / "meminfo").write_text("MemAvailable: 20 kB\n")
        actual_exists = Path.exists

        def exists(path):
            if path == self.cgroup / "memory.max":
                raise PermissionError("memory controller inaccessible")
            return actual_exists(path)

        with patch.object(Path, "exists", autospec=True, side_effect=exists):
            admission = startup.resource_admission(4, self.args)
        self.assertNotIn("rejection", admission)
        self.assertEqual(admission["cgroup_limits"][0]["memory"], {"unavailable": True})
        self.assertIsNone(admission["effective_available_bytes"])
        self.assertIsNone(admission["advisory_available_met"])

    def test_cgroup_pid_limit_still_rejects_before_start(self):
        (self.cgroup / "pids.max").write_text("67\n")
        with patch.object(startup.subprocess, "Popen") as launch:
            result = startup.check_one(Path("/unused-engine"), 4, "quit", self.args)
        launch.assert_not_called()
        self.assertFalse(result["process_started"])
        self.assertIn("insufficient cgroup task headroom", result["error"])

    def test_invalid_cgroup_pid_observation_still_prevents_launch(self):
        (self.cgroup / "pids.current").write_text("invalid\n")
        with patch.object(startup.subprocess, "Popen") as launch:
            with self.assertRaises(ValueError):
                startup.check_one(Path("/unused-engine"), 4, "quit", self.args)
        launch.assert_not_called()

    def test_uid_task_limit_still_rejects_before_start(self):
        (self.cgroup / "pids.max").write_text("max\n")
        task = self.proc / "101"
        task.mkdir()
        (task / "status").write_text("Threads:\t20\n")
        self.nproc = 87
        with patch.object(startup.subprocess, "Popen") as launch:
            result = startup.check_one(Path("/unused-engine"), 4, "quit", self.args)
        launch.assert_not_called()
        self.assertIn("insufficient per-user task headroom", result["error"])

    def test_zero_or_unknown_ram_reaches_launch_and_records_real_failure(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                if missing:
                    (self.proc / "meminfo").unlink(missing_ok=True)
                with patch.object(startup.subprocess, "Popen", side_effect=OSError("fixture launch error")) as launch:
                    result = startup.check_one(Path("/unused-engine"), 4, "quit", self.args)
                launch.assert_called_once()
                self.assertFalse(result["process_started"])
                self.assertIn("launch rejected: fixture launch error", result["error"])

    def test_child_hard_limits_are_still_applied(self):
        with patch.object(startup.os, "setsid") as setsid, \
             patch.object(startup.resource, "setrlimit") as setlimit:
            startup.set_child_limits(16000, 14000, 30)
        setsid.assert_called_once_with()
        self.assertEqual(setlimit.call_args_list, [
            call(resource.RLIMIT_CORE, (0, 0)), call(resource.RLIMIT_AS, (10000, 10000)),
            call(resource.RLIMIT_DATA, (9000, 9000)), call(resource.RLIMIT_CPU, (15, 15))])


class StartupOwnershipTests(unittest.TestCase):
    def setUp(self):
        startup._UNSETTLED.clear()
        self.addCleanup(startup._UNSETTLED.clear)

    def test_live_child_is_retained_without_signalling_and_blocks_next_start(self):
        child = Mock(pid=12345)
        child.poll.return_value = None
        with patch.object(startup.os, "killpg") as killpg:
            self.assertEqual(startup.end_owned_group(child), (False, False))
        killpg.assert_not_called()
        child.wait.assert_not_called()
        self.assertIs(startup._UNSETTLED[child.pid], child)
        with patch.object(startup, "resource_admission", side_effect=AssertionError("unexpected admission")), \
             patch.object(startup.subprocess, "Popen") as launch:
            result = startup.check_one(Path("/unused-engine"), 4, "eof", SimpleNamespace())
        launch.assert_not_called()
        self.assertIn("unsettled", result["error"])

    def test_exited_child_never_signals_a_visible_or_reused_group(self):
        child = Mock(pid=23456)
        child.poll.return_value = 0
        with patch.object(startup.os, "killpg", return_value=None) as killpg:
            self.assertEqual(startup.end_owned_group(child), (False, False))
        killpg.assert_called_once_with(child.pid, 0)
        child.wait.assert_not_called()
        self.assertIs(startup._UNSETTLED[child.pid], child)

    def test_exited_child_with_absent_group_completes_without_signal(self):
        child = Mock(pid=34567)
        child.poll.return_value = 0
        with patch.object(startup.os, "killpg", side_effect=ProcessLookupError) as killpg:
            self.assertEqual(startup.end_owned_group(child), (False, True))
        killpg.assert_called_once_with(child.pid, 0)
        child.wait.assert_not_called()
        self.assertFalse(startup._UNSETTLED)

    def test_group_visibility_failure_and_lost_child_are_unsettled(self):
        for failure in (PermissionError("hidden group"), ChildProcessError("other waiter")):
            with self.subTest(failure=type(failure).__name__):
                startup._UNSETTLED.clear()
                child = Mock(pid=45678)
                child.poll.return_value = 0
                if isinstance(failure, ChildProcessError):
                    child.poll.side_effect = failure
                with patch.object(startup.os, "killpg", side_effect=failure) as killpg:
                    self.assertEqual(startup.end_owned_group(child), (False, False))
                if isinstance(failure, ChildProcessError):
                    killpg.assert_not_called()
                else:
                    killpg.assert_called_once_with(child.pid, 0)
                child.wait.assert_not_called()
                self.assertIs(startup._UNSETTLED[child.pid], child)


if __name__ == "__main__":
    unittest.main()
