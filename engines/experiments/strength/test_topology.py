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
