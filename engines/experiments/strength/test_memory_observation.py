"""Synthetic filesystem observations; no live host memory is sampled."""
from __future__ import annotations

import hashlib
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

    def test_missing_invalid_and_exhausted_nonroot_limits_fail_closed(self):
        limit = self.delegated / "memory.max"
        for value in ("", "junk", "0", "-1", str(1 << 64), "99999999"):
            with self.subTest(value=value):
                self.write(limit, value)
                with self.assertRaises(ValueError):
                    self.observe()
        limit.unlink()
        with self.assertRaises(OSError):
            self.observe()

    def test_host_node_and_boot_validation_do_not_fabricate_available_bytes(self):
        for text in ("", "MemAvailable: 0 kB\n", "MemAvailable: 2 MB\n",
                     "MemAvailable: 2 kB\nMemAvailable: 3 kB\n", f"MemAvailable: {1 << 60} kB\n"):
            with self.subTest(text=text):
                self.write(self.proc / "meminfo", text)
                with self.assertRaises(ValueError):
                    self.observe()
        self.write(self.proc / "meminfo", "MemAvailable: 1048576 kB\n")
        self.write(self.nodes / "node0/meminfo", "Node 1 MemFree: 50 kB\n")
        with self.assertRaises(ValueError):
            self.observe()
        self.write(self.nodes / "node0/meminfo", "Node 0 MemFree: 10 kB\n")
        self.write(self.proc / "sys/kernel/random/boot_id", "bad\n")
        with self.assertRaises(ValueError):
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


if __name__ == "__main__":
    unittest.main()
