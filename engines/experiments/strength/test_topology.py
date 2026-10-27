from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from topology import Cpu, Topology, parse_list, plan_p192_slot, plan_slots


def guest(nodes=2, per_node=48):
    cpus = []
    for node in range(nodes):
        for core in range(per_node):
            # Sparse interleaved host IDs and non-consecutive SMT siblings.
            cpu = 10 + node * 1000 + core * 3
            siblings = (cpu, cpu + 100000)
            for logical in siblings:
                cpus.append(Cpu(logical, node, core, node, siblings))
    return Topology(tuple(cpus), tuple(cpu.id for cpu in cpus), tuple(range(nodes)),
                    {str(node): [10 if node == other else 20 for other in range(nodes)] for node in range(nodes)}, "fixture")


class TopologyTests(unittest.TestCase):
    def test_sparse_physical_slots_and_controller_reserve(self):
        topology = guest()
        small = plan_slots(topology, 4, 4)
        self.assertEqual(len(small), 22)
        used = [key for slot in small for key in slot.physical_cores]
        self.assertEqual(len(used), len(set(used)))
        self.assertEqual(len(used), 88)
        self.assertTrue(all(len(slot.cpus) == 4 and len(slot.memory_nodes) == 1 for slot in small))
        large = plan_slots(topology, 28, 28)
        self.assertEqual(len(large), 3)
        for slot in large:
            self.assertEqual(len(slot.physical_cores), 28)
            self.assertEqual(len(slot.cpus), 28)
            self.assertEqual(slot.memory_nodes, (0, 1))

    def test_smt_uses_same_physical_envelope(self):
        topology = guest()
        plain = plan_slots(topology, 28, 28)
        smt = plan_slots(topology, 28, 56)
        for first, second in zip(plain, smt):
            self.assertEqual(first.physical_cores, second.physical_cores)
            self.assertEqual(len(second.cpus), 56)
            self.assertTrue(set(first.cpus) <= set(second.cpus))

    def test_eleven_p16_smt_slots_are_disjoint_node_local_and_reserve_cores(self):
        topology = guest()
        slots = plan_slots(topology, 8, 16, reserve_physical=8)
        self.assertEqual(len(slots), 11)
        by_id = {cpu.id: cpu for cpu in topology.cpus}
        all_physical = {cpu.physical for cpu in topology.cpus}
        used_physical, used_logical = set(), set()
        for slot in slots:
            self.assertEqual(slot.workers, 16)
            self.assertTrue(slot.smt)
            self.assertEqual(len(slot.memory_nodes), 1)
            self.assertEqual(len(slot.physical_cores), 8)
            self.assertEqual(len(slot.cpus), 16)
            self.assertTrue(used_physical.isdisjoint(slot.physical_cores))
            self.assertTrue(used_logical.isdisjoint(slot.cpus))
            self.assertEqual({by_id[cpu].node for cpu in slot.cpus}, set(slot.memory_nodes))
            self.assertEqual({by_id[cpu].physical for cpu in slot.cpus}, set(slot.physical_cores))
            for cpu in slot.cpus:
                self.assertEqual(set(by_id[cpu].siblings),
                                 {other for other in slot.cpus
                                  if by_id[other].physical == by_id[cpu].physical})
            used_physical.update(slot.physical_cores)
            used_logical.update(slot.cpus)
        # These eight whole cores remain outside every game slot. A separate
        # runtime must actually place its controller on the reserved CPUs.
        self.assertEqual(len(all_physical - used_physical), 8)
        self.assertEqual(len(used_logical), 176)

    def test_p16_skips_a_core_when_only_one_smt_sibling_is_allowed(self):
        topology = guest()
        missing = topology.cpus[0].siblings[1]
        restricted = Topology(topology.cpus, tuple(cpu for cpu in topology.allowed_cpus if cpu != missing),
                              topology.allowed_nodes, topology.distances, topology.kernel)
        slots = plan_slots(restricted, 8, 16, reserve_physical=8)
        self.assertEqual(len(slots), 10)
        self.assertTrue(all(missing not in slot.cpus for slot in slots))
        self.assertTrue(all(topology.cpus[0].physical not in slot.physical_cores for slot in slots))

    def test_p192_full_slot_preserves_uneven_nodes_and_all_smt_siblings(self):
        original = guest(1, 96)
        # Deliberately uneven: 72 cores in node 0, 24 in node 1.
        rows = tuple(replace(cpu, node=1 if cpu.core >= 72 else 0) for cpu in original.cpus)
        topology = Topology(rows, original.allowed_cpus, (0, 1), original.distances, original.kernel)
        slot = plan_p192_slot(topology, policy="interleave")
        self.assertEqual(slot.id, "slot-000")
        self.assertEqual(slot.cpus, tuple(sorted(topology.allowed_cpus)))
        self.assertEqual(set(slot.physical_cores), {cpu.physical for cpu in rows})
        self.assertEqual(len(slot.physical_cores), 96)
        self.assertEqual(slot.memory_nodes, (0, 1))
        self.assertEqual((slot.workers, slot.smt, slot.policy), (192, True, "interleave"))
        self.assertEqual(sum(cpu.node == 0 for cpu in rows), 144)
        self.assertEqual(sum(cpu.node == 1 for cpu in rows), 48)

    def test_p192_requires_full_allowed_sibling_and_node_envelope(self):
        original = guest()
        missing = original.allowed_cpus[0]
        restricted = replace(original, allowed_cpus=tuple(cpu for cpu in original.allowed_cpus if cpu != missing))
        with self.assertRaisesRegex(ValueError, "192 distinct"):
            plan_p192_slot(restricted)
        duplicate = replace(original, allowed_cpus=(original.allowed_cpus[0],) + original.allowed_cpus[:-1])
        with self.assertRaisesRegex(ValueError, "192 distinct"):
            plan_p192_slot(duplicate)
        without_node = replace(original, allowed_nodes=(0,))
        with self.assertRaisesRegex(ValueError, "outside its allowed envelope"):
            plan_p192_slot(without_node)
        with self.assertRaisesRegex(ValueError, "memory policy"):
            plan_p192_slot(original, policy="unreviewed")

    def test_p192_rejects_inconsistent_reported_siblings_or_nodes(self):
        original = guest()
        first, other = original.cpus[0], original.cpus[2]
        inconsistent = replace(first, siblings=(first.id, other.id))
        rows = (inconsistent,) + original.cpus[1:]
        with self.assertRaisesRegex(ValueError, "mutually observed"):
            plan_p192_slot(replace(original, cpus=rows))
        misplaced = replace(original.cpus[1], node=1)
        rows = (first, misplaced) + original.cpus[2:]
        with self.assertRaisesRegex(ValueError, "mutually observed"):
            plan_p192_slot(replace(original, cpus=rows))

    def test_single_node_is_real_single_node_not_fake_numa(self):
        topology = guest(1, 96)
        slots = plan_slots(topology, 28, 28)
        self.assertEqual(len(slots), 3)
        self.assertEqual({slot.memory_nodes for slot in slots}, {(0,)})

    def test_reserve_does_not_fragment_every_small_node(self):
        self.assertEqual(len(plan_slots(guest(8, 12), 4, 4)), 22)
        self.assertEqual(len(plan_slots(guest(), 8, 8)), 11)

    def test_resource_and_parse_rejection(self):
        with self.assertRaisesRegex(ValueError, "insufficient"):
            plan_slots(guest(1, 4), 4, 4)
        self.assertEqual(parse_list("0-3,8,511"), {0, 1, 2, 3, 8, 511})
        for value in ("2-1", "0;1", "-1", "0,,2"):
            with self.assertRaises(ValueError):
                parse_list(value)


@unittest.skipUnless(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "Linux target cgroup fixture")
class TargetTopologyTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name).resolve()
        self.root, self.sysroot = root, root / "sys"
        self.target = root / "delegated" / "games"
        self.target.mkdir(parents=True)
        (self.target / "cpuset.cpus.effective").write_text("0-3\n")
        (self.target / "cpuset.mems.effective").write_text("0-1\n")
        cpu_root = self.sysroot / "devices/system/cpu"
        cpu_root.mkdir(parents=True)
        (cpu_root / "online").write_text("0-3\n")
        for cpu in range(4):
            directory = cpu_root / f"cpu{cpu}/topology"
            directory.mkdir(parents=True)
            (directory / "physical_package_id").write_text(f"{cpu // 2}\n")
            (directory / "core_id").write_text("0\n")
            (directory / "thread_siblings_list").write_text("0-1\n" if cpu < 2 else "2-3\n")
        for node in (0, 1):
            directory = self.sysroot / f"devices/system/node/node{node}"
            directory.mkdir(parents=True)
            (directory / "cpulist").write_text("0-1\n" if node == 0 else "2-3\n")
            (directory / "distance").write_text("10 20\n" if node == 0 else "20 10\n")
        stat = self.target.stat()
        self.device, self.inode = stat.st_dev, stat.st_ino

    def snapshot(self, path=None, *, device=None, inode=None):
        return Topology.snapshot_target(path or self.target,
                device=self.device if device is None else device,
                inode=self.inode if inode is None else inode, sysroot=self.sysroot)

    def test_target_masks_ignore_observer_affinity(self):
        with patch.object(os, "sched_getaffinity", return_value={0}):
            result = self.snapshot()
        self.assertEqual(result.allowed_cpus, (0, 1, 2, 3))
        self.assertEqual(result.allowed_nodes, (0, 1))
        self.assertEqual([cpu.node for cpu in result.cpus], [0, 0, 1, 1])
        self.assertEqual(result.cpus[2].siblings, (2, 3))

    def test_original_cgroup_identity_and_no_symlink_paths_are_required(self):
        with self.assertRaisesRegex(ValueError, "identity changed"):
            self.snapshot(inode=self.inode + 1)
        link = self.root / "link"
        link.symlink_to(self.target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            self.snapshot(link)
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            self.snapshot(self.root / "delegated" / ".." / "delegated" / "games")

    def test_empty_offline_and_unknown_masks_fail(self):
        cpu_file, node_file = (self.target / name for name in
                               ("cpuset.cpus.effective", "cpuset.mems.effective"))
        for value in ("", "0-4", "0;1"):
            with self.subTest(cpus=value):
                cpu_file.write_text(value)
                with self.assertRaises(ValueError):
                    self.snapshot()
        cpu_file.write_text("0-3")
        for value in ("", "0-2", "0;1"):
            with self.subTest(nodes=value):
                node_file.write_text(value)
                with self.assertRaises(ValueError):
                    self.snapshot()

    def test_rejects_effective_mask_change_during_snapshot(self):
        original = Path.read_text
        def changing(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if str(path).endswith("node0/cpulist"):
                (self.target / "cpuset.cpus.effective").write_text("0-1")
            return value
        with patch.object(Path, "read_text", changing):
            with self.assertRaisesRegex(ValueError, "changed during observation"):
                self.snapshot()

    def test_rejects_online_cpu_change_during_snapshot(self):
        original = Path.read_text
        def changing(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if str(path).endswith("node0/cpulist"):
                (self.sysroot / "devices/system/cpu/online").write_text("0-1")
            return value
        with patch.object(Path, "read_text", changing):
            with self.assertRaisesRegex(ValueError, "changed during observation"):
                self.snapshot()

    def test_rejects_replacement_of_target_path_during_snapshot(self):
        original = Path.read_text
        def replacing(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if str(path).endswith("node0/cpulist"):
                self.target.rename(self.target.parent / "old-target")
                self.target.mkdir()
                (self.target / "cpuset.cpus.effective").write_text("0-3")
                (self.target / "cpuset.mems.effective").write_text("0-1")
            return value
        with patch.object(Path, "read_text", replacing):
            with self.assertRaisesRegex(ValueError, "changed during observation"):
                self.snapshot()

    def test_duplicate_numa_membership_is_rejected(self):
        (self.sysroot / "devices/system/node/node1/cpulist").write_text("1-3")
        with self.assertRaisesRegex(ValueError, "multiple NUMA"):
            self.snapshot()


if __name__ == "__main__":
    unittest.main()
