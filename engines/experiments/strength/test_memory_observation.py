"""Synthetic filesystem observations; no live host memory is sampled."""
from __future__ import annotations

import hashlib
import errno
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import memory_observation as observation


@unittest.skipUnless(os.name == "posix" and hasattr(os, "major") and hasattr(os, "minor"),
                     "Linux cgroup mount identity fixture")
class CapacityObservationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name).resolve()
        self.proc, self.nodes, self.mount = (self.root / item for item in ("proc", "nodes", "cgroup"))
        self.controller, self.delegated = self.mount / "controller", self.mount / "delegated"
        for directory in (self.proc / "self", self.proc / "sys/kernel/random", self.nodes / "node0",
                          self.nodes / "node1", self.controller, self.delegated):
            directory.mkdir(parents=True)
        self.write(self.proc / "meminfo", "MemAvailable: 1048576 kB\n")
        self.write(self.proc / "self/cgroup", "0::/controller\n")
        self.device = f"{os.major(self.mount.stat().st_dev)}:{os.minor(self.mount.stat().st_dev)}"
        self.write(self.proc / "self/mountinfo", f"12 1 {self.device} / {self.mount} rw - cgroup2 cgroup rw\n")
        self.write(self.proc / "self/status", "Name: fixture\nMems_allowed_list:\t0-1\n")
        self.write(self.proc / "sys/kernel/random/boot_id", "12345678-1234-1234-1234-123456789abc\n")
        self.write(self.controller / "memory.max", "700000000\n")
        self.write(self.controller / "memory.current", "100000000\n")
        self.write(self.delegated / "memory.max", "500000000\n")
        self.write(self.delegated / "memory.current", "100000000\n")
        self.write(self.delegated / "cpuset.cpus.effective", "0-3\n")
        self.write(self.delegated / "cpuset.mems.effective", "0-1\n")
        self.write(self.nodes / "node0/meminfo", "Node 0 MemFree: 131072 kB\n")
        self.write(self.nodes / "node1/meminfo", "Node 1 MemFree: 262144 kB\n")
        self.slots = [{"id": "slot-000", "cpus": [0, 1], "memory_nodes": [0], "policy": "default"},
                      {"id": "slot-001", "cpus": [2, 3], "memory_nodes": [1], "policy": "default"}]

    @staticmethod
    def write(path, text):
        path.write_text(text, encoding="utf-8")

    def observe(self, **kwargs):
        return observation.observe_capacity(self.slots, self.delegated, proc_root=self.proc,
            node_root=self.nodes, cgroup_mount=self.mount, page_size_for_test=kwargs.pop("page_size_for_test", 4096),
            cpu_affinity_for_test=kwargs.pop("cpu_affinity_for_test", {0, 1, 2, 3}),
            **kwargs)

    def test_controller_and_distinct_delegated_ancestor_limits_are_both_counted(self):
        result = self.observe()
        self.assertEqual(result["host_memavailable_bytes"], 1 << 30)
        self.assertEqual(result["host_available_bytes"], 400000000)
        self.assertEqual(result["node_available_bytes"], {0: 128 << 20, 1: 256 << 20})
        self.assertEqual(result["page_bytes"], 4096)
        self.assertTrue(result["test_inputs"])
        self.assertFalse(result["hidden_ancestors_verified"])
        self.assertFalse(result["runtime_admission_complete"])
        self.assertTrue(result["controller_cgroup"][-1]["root_memory_files_unavailable"])
        self.assertEqual(result["slot_sha256"], hashlib.sha256(json.dumps(self.slots, sort_keys=True,
            separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest())
        self.assertLessEqual(result["started_monotonic_ns"], result["completed_monotonic_ns"])

    def test_extra_controller_node_is_measured_without_changing_frozen_slots(self):
        (self.nodes / "node2").mkdir()
        self.write(self.nodes / "node2/meminfo", "Node 2 MemFree: 65536 kB\n")
        self.write(self.delegated / "cpuset.mems.effective", "0-2\n")
        original = self.observe()
        result = self.observe(extra_nodes=[2])
        self.assertEqual(result["node_available_bytes"], {0: 128 << 20, 1: 256 << 20, 2: 64 << 20})
        self.assertEqual(result["extra_nodes"], [2])
        self.assertEqual(result["controller_allowed_nodes"], [0, 1])
        self.assertEqual(result["delegated_effective_nodes"], [0, 1, 2])
        self.assertEqual(result["slot_sha256"], original["slot_sha256"])
        self.assertEqual(result["slots"], original["slots"])
        self.assertFalse(result["runtime_admission_complete"])

    def test_extra_controller_nodes_must_be_distinct_bounded_and_delegated(self):
        for extra in (None, "0", [True], [-1], [1000001], [0, 0], [[]]):
            with self.subTest(extra=extra), self.assertRaisesRegex(ValueError, "extra memory-node"):
                self.observe(extra_nodes=extra)
        with self.assertRaisesRegex(ValueError, "effective masks"):
            self.observe(extra_nodes=[2])
        self.write(self.delegated / "cpuset.mems.effective", "0-2\n")
        with self.assertRaisesRegex(ValueError, "node directory"):
            self.observe(extra_nodes=[2])

    def test_unlimited_ancestor_is_not_a_numeric_capacity(self):
        self.write(self.delegated / "memory.max", "max\n")
        result = self.observe()
        self.assertEqual(result["host_available_bytes"], 600000000)
        self.assertIsNone(result["delegated_cgroup"][0]["remaining_bytes"])

    def test_each_visible_delegated_ancestor_can_be_the_tightest_bound(self):
        child = self.delegated / "nested"
        child.mkdir()
        self.write(child / "memory.max", "450000000\n")
        self.write(child / "memory.current", "100000000\n")
        self.write(child / "cpuset.cpus.effective", "0-3\n")
        self.write(child / "cpuset.mems.effective", "0-1\n")
        result = observation.observe_capacity(self.slots, child, proc_root=self.proc, node_root=self.nodes,
                                               cgroup_mount=self.mount, page_size_for_test=4096,
                                               cpu_affinity_for_test={0, 1, 2, 3})
        self.assertEqual(result["host_available_bytes"], 350000000)
        self.assertEqual([row["path"] for row in result["delegated_cgroup"]],
                         [str(child), str(self.delegated), str(self.mount)])

    def test_missing_or_invalid_nonroot_limits_fail_closed(self):
        limit = self.delegated / "memory.max"
        for value in ("", "junk", "-1", str(1 << 64)):
            with self.subTest(value=value):
                self.write(limit, value)
                with self.assertRaises(ValueError):
                    self.observe()
        limit.unlink()
        with self.assertRaises(OSError):
            self.observe()

    def test_host_node_and_boot_validation_do_not_fabricate_available_bytes(self):
        for text in ("MemAvailable: 2 MB\n", "MemAvailable: bad kB\n",
                     "MemAvailable: 2 kB\nMemAvailable: invalid\n",
                     "MemAvailable: 2 kB\nMemAvailable: 3 kB\n", f"MemAvailable: {1 << 60} kB\n"):
            with self.subTest(text=text):
                self.write(self.proc / "meminfo", text)
                result = self.observe()
                self.assertIsNone(result["host_memavailable_bytes"])
                self.assertIsNone(result["host_available_bytes"])
                self.assertIn({"metric": "host_memavailable_bytes", "error": "malformed"},
                              result["telemetry_errors"])
        self.write(self.proc / "meminfo", "MemAvailable: 1048576 kB\n")
        self.write(self.nodes / "node0/meminfo", "Node 1 MemFree: 50 kB\n")
        with self.assertRaises(ValueError):
            self.observe()
        self.write(self.nodes / "node0/meminfo", "Node 0 MemFree: 50 kB\nNode 1 MemFree: 50 kB\n")
        with self.assertRaises(ValueError):
            self.observe()
        self.write(self.nodes / "node0/meminfo", "Node 0 MemFree: 50 MB\n")
        result = self.observe()
        self.assertIsNone(result["node_available_bytes"][0])
        self.assertIn({"metric": "node_available_bytes", "node": 0, "error": "malformed"},
                      result["telemetry_errors"])
        self.write(self.nodes / "node0/meminfo", "Node 0 MemFree: 10 kB\n")
        self.write(self.proc / "sys/kernel/random/boot_id", "bad\n")
        with self.assertRaises(ValueError):
            self.observe()

    def test_zero_and_negative_headroom_are_recorded_without_admission(self):
        self.write(self.proc / "meminfo", "MemAvailable: 0 kB\n")
        self.write(self.nodes / "node0/meminfo", "Node 0 MemFree: 0 kB\n")
        self.write(self.delegated / "memory.max", "100000000\n")
        equal = self.observe()
        self.assertEqual(equal["host_memavailable_bytes"], 0)
        self.assertEqual(equal["host_available_bytes"], 0)
        self.assertEqual(equal["node_available_bytes"][0], 0)
        self.assertEqual(equal["delegated_cgroup"][0]["remaining_bytes"], 0)
        self.assertFalse(equal["runtime_admission_complete"])
        self.write(self.delegated / "memory.current", "100000001\n")
        over = self.observe()
        self.assertEqual(over["delegated_cgroup"][0]["remaining_bytes"], -1)
        self.assertEqual(over["host_available_bytes"], -1)
        self.assertFalse(over["runtime_admission_complete"])
        self.write(self.delegated / "memory.max", "0\n")
        zero_limit = self.observe()
        self.assertEqual(zero_limit["delegated_cgroup"][0]["limit_bytes"], 0)
        self.assertEqual(zero_limit["delegated_cgroup"][0]["remaining_bytes"], -100000001)

    def test_unavailable_metrics_are_null_not_unlimited_or_zero(self):
        self.write(self.proc / "meminfo", "MemTotal: 123 kB\n")
        self.write(self.nodes / "node0/meminfo", "Node 0 MemTotal: 123 kB\n")
        self.delegated.joinpath("memory.current").unlink()
        result = self.observe()
        self.assertIsNone(result["host_memavailable_bytes"])
        self.assertIsNone(result["host_available_bytes"])
        self.assertIsNone(result["node_available_bytes"][0])
        self.assertEqual(result["delegated_cgroup"][0]["limit_bytes"], 500000000)
        self.assertIsNone(result["delegated_cgroup"][0]["current_bytes"])
        self.assertIsNone(result["delegated_cgroup"][0]["remaining_bytes"])
        self.assertIn({"metric": "host_memavailable_bytes", "error": "missing"}, result["telemetry_errors"])
        self.assertIn({"metric": "node_available_bytes", "node": 0, "error": "missing"}, result["telemetry_errors"])
        self.assertIn({"metric": "cgroup_current_bytes", "path": str(self.delegated), "error": "missing"},
                      result["telemetry_errors"])
        self.assertFalse(result["runtime_admission_complete"])

    def test_missing_finite_ancestor_usage_does_not_fabricate_effective_capacity(self):
        self.delegated.joinpath("memory.current").unlink()
        result = self.observe()
        self.assertEqual(result["host_memavailable_bytes"], 1 << 30)
        self.assertIsNone(result["host_available_bytes"])

    def test_unreadable_and_malformed_usage_are_distinct_unknown_telemetry(self):
        original = observation._file
        def denied(path, **kwargs):
            if Path(path) in (self.proc / "meminfo", self.nodes / "node0/meminfo", self.controller / "memory.current"):
                raise PermissionError("fixture telemetry access denied")
            return original(path, **kwargs)
        with patch.object(observation, "_file", side_effect=denied):
            result = self.observe()
        self.assertIsNone(result["host_memavailable_bytes"])
        self.assertIsNone(result["host_available_bytes"])
        self.assertIsNone(result["node_available_bytes"][0])
        self.assertIsNone(result["controller_cgroup"][0]["current_bytes"])
        self.assertIn({"metric": "host_memavailable_bytes", "error": "unreadable"}, result["telemetry_errors"])
        self.assertIn({"metric": "node_available_bytes", "node": 0, "error": "unreadable"}, result["telemetry_errors"])
        self.assertIn({"metric": "cgroup_current_bytes", "path": str(self.controller), "error": "unreadable"},
                      result["telemetry_errors"])
        for value in ("-1\n", "junk\n", "\n", str(1 << 64), "1\n2\n"):
            with self.subTest(value=value):
                self.write(self.controller / "memory.current", value)
                result = self.observe()
                self.assertIsNone(result["controller_cgroup"][0]["current_bytes"])
                self.assertIsNone(result["controller_cgroup"][0]["remaining_bytes"])
                self.assertIsNone(result["host_available_bytes"])
                self.assertIn({"metric": "cgroup_current_bytes", "path": str(self.controller), "error": "malformed"},
                              result["telemetry_errors"])

    def test_invalid_encoding_and_oversized_metric_are_unknown_not_paths_ignored(self):
        for data in (b"\xff", b"x" * 65537):
            with self.subTest(length=len(data)):
                (self.proc / "meminfo").write_bytes(data)
                result = self.observe()
                self.assertIsNone(result["host_memavailable_bytes"])
                self.assertIn({"metric": "host_memavailable_bytes", "error": "malformed"},
                              result["telemetry_errors"])

    def test_transient_read_error_is_unknown_but_unsafe_path_error_is_rejected(self):
        original = observation._file
        measured = (self.proc / "meminfo", self.nodes / "node0/meminfo", self.controller / "memory.current")
        def failed_read(path, **kwargs):
            if Path(path) in measured:
                raise OSError(errno.EIO, "fixture I/O failure")
            return original(path, **kwargs)
        with patch.object(observation, "_file", side_effect=failed_read):
            result = self.observe()
        self.assertIsNone(result["host_memavailable_bytes"])
        self.assertIsNone(result["node_available_bytes"][0])
        self.assertIsNone(result["controller_cgroup"][0]["current_bytes"])
        self.assertIn({"metric": "host_memavailable_bytes", "error": "unreadable"}, result["telemetry_errors"])
        def unsafe_path(path, **kwargs):
            if Path(path) == self.proc / "meminfo":
                raise OSError(errno.ELOOP, "fixture unsafe path")
            return original(path, **kwargs)
        with patch.object(observation, "_file", side_effect=unsafe_path):
            with self.assertRaises(OSError):
                self.observe()

    def test_cgroup_membership_and_mount_mapping_are_bound(self):
        for text in ("0::/../escape\n", "0::/missing\n", "0::/controller\n0::/controller\n", "bad\n"):
            with self.subTest(text=text):
                self.write(self.proc / "self/cgroup", text)
                with self.assertRaises(ValueError):
                    self.observe()
        self.write(self.proc / "self/cgroup", "0::/controller\n")
        self.write(self.proc / "self/mountinfo", f"12 1 {self.device} /hidden {self.mount} rw - cgroup2 cgroup rw\n")
        with self.assertRaisesRegex(ValueError, "mount mapping"):
            self.observe()

    def test_root_only_membership_is_explicitly_unverified(self):
        self.write(self.proc / "self/cgroup", "0::/\n")
        result = self.observe()
        self.assertEqual(result["controller_membership"], "/")
        self.assertFalse(result["hidden_ancestors_verified"])
        self.assertFalse(result["runtime_admission_complete"])

    def test_effective_cpu_and_memory_masks_must_allow_all_planned_slots(self):
        self.write(self.delegated / "cpuset.cpus.effective", "0-2\n")
        with self.assertRaisesRegex(ValueError, "effective masks"):
            self.observe()
        self.write(self.delegated / "cpuset.cpus.effective", "0-3\n")
        self.write(self.delegated / "cpuset.mems.effective", "0\n")
        with self.assertRaisesRegex(ValueError, "effective masks"):
            self.observe()
        self.write(self.delegated / "cpuset.mems.effective", "0-1\n")
        with self.assertRaisesRegex(ValueError, "effective masks"):
            self.observe(cpu_affinity_for_test={0, 1, 2})
        self.write(self.proc / "self/status", "Mems_allowed_list: 0\n")
        with self.assertRaisesRegex(ValueError, "effective masks"):
            self.observe()

    def test_delegated_only_scope_observes_target_with_smaller_sibling_observer(self):
        self.write(self.proc / "self/status", "Mems_allowed_list: 0\n")
        # The default remains strict for existing callers.
        with self.assertRaisesRegex(ValueError, "effective masks"):
            self.observe(cpu_affinity_for_test={0})
        result = self.observe(cpu_affinity_for_test={0}, mask_scope="delegated-only")
        self.assertEqual(result["mask_scope"], "delegated-only")
        self.assertEqual(result["controller_cpu_affinity"], [0])
        self.assertEqual(result["controller_allowed_nodes"], [0])
        self.assertEqual(result["delegated_effective_cpus"], [0, 1, 2, 3])
        self.assertEqual(result["delegated_effective_nodes"], [0, 1])
        self.assertEqual(result["node_available_bytes"], {0: 128 << 20, 1: 256 << 20})
        self.assertFalse(result["runtime_admission_complete"])

        # Target cpuset restrictions still cannot be bypassed by the mode.
        self.write(self.delegated / "cpuset.cpus.effective", "0-2\n")
        with self.assertRaisesRegex(ValueError, "effective masks"):
            self.observe(cpu_affinity_for_test={0}, mask_scope="delegated-only")
        self.write(self.delegated / "cpuset.cpus.effective", "0-3\n")
        self.write(self.delegated / "cpuset.mems.effective", "0\n")
        with self.assertRaisesRegex(ValueError, "effective masks"):
            self.observe(cpu_affinity_for_test={0}, mask_scope="delegated-only")

    def test_mask_scope_must_be_explicit_and_known(self):
        for scope in (None, True, "target", "", []):
            with self.subTest(scope=scope), self.assertRaisesRegex(ValueError, "mask scope"):
                self.observe(mask_scope=scope)

    def test_delegated_only_scope_still_checks_observer_mask_stability(self):
        original, calls = observation._file, 0
        status = self.proc / "self/status"
        def changing(path, **kwargs):
            nonlocal calls
            value = original(path, **kwargs)
            if Path(path) == status:
                calls += 1
                if calls == 2:
                    return "Mems_allowed_list: 0\n"
            return value
        with patch.object(observation, "_file", side_effect=changing):
            with self.assertRaisesRegex(ValueError, "changed during"):
                self.observe(cpu_affinity_for_test={0}, mask_scope="delegated-only")

    def test_cgroup_mount_device_mismatch_is_rejected(self):
        self.write(self.proc / "self/mountinfo", f"12 1 999999:999999 / {self.mount} rw - cgroup2 cgroup rw\n")
        with self.assertRaisesRegex(ValueError, "device differs"):
            self.observe()

    def test_unrelated_unicode_mount_path_does_not_break_mountinfo(self):
        with (self.proc / "self/mountinfo").open("a", encoding="utf-8") as output:
            output.write("13 1 0:99 / /other-한글 rw - tmpfs tmpfs rw\n")
        self.assertEqual(self.observe()["host_available_bytes"], 400000000)

    def test_unicode_cgroup_mount_with_escaped_space_is_matched(self):
        mount = self.root / "검증 공백"
        controller, delegated = mount / "controller", mount / "delegated"
        controller.mkdir(parents=True)
        delegated.mkdir()
        for target, limit in ((controller, 700000000), (delegated, 500000000)):
            self.write(target / "memory.max", f"{limit}\n")
            self.write(target / "memory.current", "100000000\n")
        self.write(delegated / "cpuset.cpus.effective", "0-3\n")
        self.write(delegated / "cpuset.mems.effective", "0-1\n")
        encoded_mount = str(mount).replace(" ", "\\040")
        self.write(self.proc / "self/mountinfo", f"12 1 {self.device} / {encoded_mount} rw - cgroup2 cgroup rw\n")
        result = observation.observe_capacity(self.slots, delegated, proc_root=self.proc, node_root=self.nodes,
                                              cgroup_mount=mount, page_size_for_test=4096,
                                              cpu_affinity_for_test={0, 1, 2, 3})
        self.assertEqual(result["mount"]["mount"], str(mount))
        self.assertEqual(result["host_available_bytes"], 400000000)

    def test_slot_and_kernel_page_inputs_are_bounded(self):
        for page in (0, -1, True, 3000, 1 << 31):
            with self.subTest(page=page), self.assertRaises(ValueError):
                self.observe(page_size_for_test=page)
        self.slots.append(dict(self.slots[0]))
        with self.assertRaises(ValueError):
            self.observe()

    def test_membership_change_during_sampling_is_rejected(self):
        original, calls = observation._file, 0
        membership = self.proc / "self/cgroup"
        def changing(path, **kwargs):
            nonlocal calls
            value = original(path, **kwargs)
            if Path(path) == membership:
                calls += 1
                if calls == 2:
                    return "0::/delegated\n"
            return value
        with patch.object(observation, "_file", side_effect=changing):
            with self.assertRaisesRegex(ValueError, "changed during"):
                self.observe()

    def test_symlink_node_or_delegated_outside_mount_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        with self.assertRaises(ValueError):
            observation.observe_capacity(self.slots, outside, proc_root=self.proc, node_root=self.nodes,
                                         cgroup_mount=self.mount, page_size_for_test=4096)
        link = self.nodes / "node2"
        try:
            link.symlink_to(self.nodes / "node0", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        self.slots[0]["memory_nodes"] = [2]
        self.write(self.proc / "self/status", "Mems_allowed_list: 0-2\n")
        self.write(self.delegated / "cpuset.mems.effective", "0-2\n")
        with self.assertRaisesRegex(ValueError, "node directory"):
            self.observe()

    def test_symlink_node_meminfo_is_not_followed(self):
        meminfo = self.nodes / "node0/meminfo"
        other = self.nodes / "node1/meminfo"
        meminfo.unlink()
        try:
            meminfo.symlink_to(other)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        with self.assertRaises(ValueError):
            self.observe()

    def test_node_directory_replacement_during_metric_read_is_rejected(self):
        original = observation._optional_kb_file
        node = self.nodes / "node0"
        swapped = False
        def replacing(path, *args, **kwargs):
            nonlocal swapped
            result = original(path, *args, **kwargs)
            if Path(path) == node / "meminfo" and not swapped:
                swapped = True
                node.rename(self.nodes / "node0-previous")
                node.mkdir()
                self.write(node / "meminfo", "Node 0 MemFree: 131072 kB\n")
            return result
        with patch.object(observation, "_optional_kb_file", side_effect=replacing):
            with self.assertRaisesRegex(ValueError, "node directory identity changed"):
                self.observe()


if __name__ == "__main__":
    unittest.main()
