import unittest

from topology import Cpu, Topology, parse_list, plan_slots


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


if __name__ == "__main__":
    unittest.main()
