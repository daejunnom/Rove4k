"""Capacity assessment fixture tests; no live cgroup or engine is launched."""
from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    from . import ledger, peak_capacity, topology
except ImportError:
    import ledger
    import peak_capacity
    import topology


class CapacityTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.profile = "test-p192"
        self.slot = topology.Slot("slot-000", tuple(range(192)), tuple((0, i) for i in range(96)),
                                  (0, 1), 192, True, "default")
        self.slots = [self.slot]
        self.slot_records = [self.slot.to_record()]
        self.frozen_topology = {"frozen": "fixture"}
        self.snapshot = SimpleNamespace(to_record=lambda: deepcopy(self.frozen_topology),
                                        allowed_cpus=tuple(range(192)), allowed_nodes=(0, 1, 2))
        self.controller_cpus = list(self.slot.cpus)
        self.tt = 192 << 30
        self.game_limit = 2 * self.tt + 20
        self.host_limit = self.game_limit + 10000
        self.games = [{"slot": self.slot.id, "path": str(self.root / "game"), "cpus": list(self.slot.cpus),
                       "nodes": [0, 1], "artifacts": [
                           {"id": "a", "whole_sha256": "a" * 64, "native_sha256": "b" * 64, "tt_bytes": self.tt},
                           {"id": "b", "whole_sha256": "c" * 64, "native_sha256": "d" * 64, "tt_bytes": self.tt}]}]
        self.groups = {self.slot.id: {"path": self.games[0]["path"], "device": 1, "inode": 10,
                         "cpus": list(self.slot.cpus), "memory_nodes": [0, 1], "memory_max": self.game_limit}}
        self.controller = {"path": str(self.root / "controller"), "device": 1, "inode": 11,
                           "cpus": list(self.slot.cpus), "memory_nodes": [0, 1], "memory_max": 30}
        self.expected_controller = self.controller["path"]
        self.make_empty_group(Path(self.games[0]["path"]))
        self.make_empty_group(Path(self.controller["path"]))
        self.observation = {"test_inputs": False, "runtime_admission_complete": False, "slot_sha256": ledger.digest(self.slot_records),
                            "delegated_identity": {"device": self.root.stat().st_dev, "inode": self.root.stat().st_ino},
                            "delegated_effective_cpus": list(range(192)), "delegated_effective_nodes": [0, 1, 2],
                            "mask_scope": "delegated-only", "extra_nodes": [0, 1],
                            "host_memavailable_bytes": self.host_limit, "host_available_bytes": self.host_limit,
                            "controller_cgroup": [
                                {"path": str(self.root.parent / "observer"), "limit_bytes": 10000,
                                 "current_bytes": 0, "remaining_bytes": 10000, "root_memory_files_unavailable": False},
                                {"path": str(self.root.parent), "limit_bytes": None, "current_bytes": 0,
                                 "remaining_bytes": None, "root_memory_files_unavailable": False}],
                            "delegated_cgroup": [
                                {"path": str(self.root), "limit_bytes": self.host_limit, "current_bytes": 0,
                                 "remaining_bytes": self.host_limit, "root_memory_files_unavailable": False},
                                {"path": str(self.root.parent), "limit_bytes": None, "current_bytes": 0,
                                 "remaining_bytes": None, "root_memory_files_unavailable": False}],
                            "node_available_bytes": {0: self.host_limit, 1: self.host_limit},
                            "page_bytes": 4096, "boot_id": "12345678-1234-1234-1234-123456789abc"}

    @staticmethod
    def make_empty_group(path):
        path.mkdir(parents=True, exist_ok=True)
        (path / "memory.current").write_text("0\n", encoding="ascii")
        (path / "memory.peak").write_text("0\n", encoding="ascii")
        (path / "cgroup.events").write_text("populated 0\nfrozen 0\n", encoding="ascii")

    def inspect(self):
        with patch.object(peak_capacity.topology.Topology, "snapshot_target", return_value=self.snapshot) as target_topology, \
             patch.object(peak_capacity.run, "league_placement", return_value=(self.slots, self.controller_cpus)), \
             patch.object(peak_capacity.memory_observation, "observe_capacity", return_value=deepcopy(self.observation)) as observe, \
             patch.object(peak_capacity.placement, "verify_cgroup_live", side_effect=lambda record: deepcopy(record)):
            result = peak_capacity.inspect_capacity(profile=self.profile, root=self.root,
                    games=self.games, groups=self.groups, controller=self.controller,
                    frozen_topology=self.frozen_topology, per_game_headroom_bytes=20,
                    controller_headroom_bytes=30, controller_path=self.expected_controller)
            self.last_observe = observe.call_args
            self.last_topology = target_topology.call_args
            return result

    def test_good_arithmetic_still_cannot_authorize_without_independent_proofs(self):
        result = self.inspect()
        self.assertIs(result["runtime_admission"], False)
        self.assertTrue(result["unresolved"])
        reasons = " ".join(result["unresolved"]).casefold()
        for term in ("ancestor", "writer", "overhead", "source"):
            self.assertIn(term, reasons)
        self.assertEqual(result["capacity"]["boot_id"], self.observation["boot_id"])
        self.assertTrue(result["source_sha256"])
        self.assertIn("reclaimable cache excluded", result["arithmetic"]["node_capacity_basis"])

    def test_legacy_and_unknown_profiles_are_rejected(self):
        for profile in ("test-p4", "test-p28", "unknown"):
            with self.subTest(profile=profile):
                self.profile = profile
                with self.assertRaises(ValueError):
                    self.inspect()

    def test_insufficient_host_and_game_limit_fail_before_launch(self):
        self.observation["host_memavailable_bytes"] = 1
        with self.assertRaises(ValueError):
            self.inspect()
        self.observation["host_memavailable_bytes"] = self.host_limit
        self.groups[self.slot.id]["memory_max"] = self.game_limit - 1
        with self.assertRaises(ValueError):
            self.inspect()

    def test_kernel_limits_not_just_declared_extents_bound_cohort(self):
        # A caller may create leaves larger than the estimates. The kernel
        # can charge the full limits; admission must cover that upper bound.
        self.groups[self.slot.id]["memory_max"] = self.game_limit + 80
        self.controller["memory_max"] = 50
        self.observation["host_memavailable_bytes"] = self.game_limit + 129
        with self.assertRaisesRegex(ValueError, "capacity"):
            self.inspect()
        self.observation["host_memavailable_bytes"] = self.game_limit + 130
        result = self.inspect()
        self.assertEqual(result["arithmetic"]["required_bytes"], self.game_limit + 130)
        self.assertEqual(result["arithmetic"]["games"][0]["memory_max_bytes"], self.game_limit + 80)

    def test_observer_only_limit_does_not_reduce_target_cohort_capacity(self):
        self.observation["controller_cgroup"][0].update(limit_bytes=10, remaining_bytes=10)
        self.observation["host_available_bytes"] = 10
        result = self.inspect()
        self.assertEqual(result["arithmetic"]["required_bytes"], self.game_limit + 30)
        self.assertEqual(result["arithmetic"]["target_available_bytes"], self.host_limit)
        self.assertEqual(result["arithmetic"]["observer_visible_remaining_bytes"], 10)
        self.assertFalse(result["launch_permitted"])
        self.assertIn("representative_overhead_bound", result["unresolved"])

    def test_target_parent_and_its_shared_ancestor_limits_bound_the_cohort(self):
        self.observation["delegated_cgroup"][0].update(limit_bytes=self.game_limit + 29, remaining_bytes=self.game_limit + 29)
        with self.assertRaisesRegex(ValueError, "capacity"):
            self.inspect()
        self.observation["delegated_cgroup"][0].update(limit_bytes=self.host_limit, remaining_bytes=self.host_limit)
        self.observation["delegated_cgroup"][1].update(limit_bytes=self.game_limit + 29, remaining_bytes=self.game_limit + 29)
        self.observation["controller_cgroup"][1].update(limit_bytes=self.game_limit + 29, remaining_bytes=self.game_limit + 29)
        with self.assertRaisesRegex(ValueError, "capacity"):
            self.inspect()

    def test_unlimited_observer_has_no_finite_visible_limit(self):
        self.observation["controller_cgroup"][0].update(limit_bytes=None, remaining_bytes=None)
        result = self.inspect()
        self.assertIsNone(result["arithmetic"]["observer_visible_remaining_bytes"])

    def test_malformed_target_or_observer_ancestor_is_not_silently_unlimited(self):
        for field in ("delegated_cgroup", "controller_cgroup"):
            with self.subTest(field=field):
                original = deepcopy(self.observation[field])
                self.observation[field][0]["remaining_bytes"] = -1
                with self.assertRaises(ValueError):
                    self.inspect()
                self.observation[field] = original

    def test_insufficient_node_capacity_fails_before_launch(self):
        self.observation["node_available_bytes"] = {0: 1, 1: 1}
        with self.assertRaises(ValueError):
            self.inspect()

    def test_p192_controller_only_node_counts_towards_controller_reserve(self):
        self.controller["memory_nodes"] = [0, 1, 2]
        self.observation["extra_nodes"] = [0, 1, 2]
        self.observation["node_available_bytes"] = {0: self.tt, 1: self.tt + 20, 2: 30}
        result = self.inspect()
        self.assertFalse(result["launch_permitted"])
        self.assertTrue(result["arithmetic"]["controller_node_aggregate_arithmetic_checked"])
        self.assertFalse(result["arithmetic"]["controller_node_distribution_verified"])
        self.assertEqual(set(self.last_observe.kwargs["extra_nodes"]), {0, 1, 2})
        # Aggregate capacity over controller nodes is now one byte short.
        self.observation["node_available_bytes"][2] = 29
        with self.assertRaises(ValueError):
            self.inspect()
        # Plenty of controller-only memory cannot replace P192 game-node room.
        self.observation["node_available_bytes"] = {0: self.tt, 1: self.tt + 19, 2: 100}
        with self.assertRaises(ValueError):
            self.inspect()
        self.observation["node_available_bytes"] = {0: self.tt, 1: self.tt + 20}
        with self.assertRaises(ValueError):
            self.inspect()

    def test_mismatching_topology_and_slot_observation_fail(self):
        self.snapshot = SimpleNamespace(to_record=lambda: {"frozen": "other"},
                                        allowed_cpus=tuple(range(192)), allowed_nodes=(0, 1, 2))
        with self.assertRaises(ValueError):
            self.inspect()
        self.snapshot = SimpleNamespace(to_record=lambda: deepcopy(self.frozen_topology),
                                        allowed_cpus=tuple(range(192)), allowed_nodes=(0, 1, 2))
        self.observation["slot_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.inspect()

    def test_group_masks_and_fixture_observation_fail(self):
        self.groups[self.slot.id]["cpus"] = [0]
        with self.assertRaises(ValueError):
            self.inspect()
        self.groups[self.slot.id]["cpus"] = list(self.slot.cpus)
        self.observation["test_inputs"] = True
        with self.assertRaises(ValueError):
            self.inspect()

    def test_live_capacity_samples_shared_parent_including_intermediate_ancestors(self):
        shared = self.root / "intermediate"
        game = shared / "game"
        controller = shared / "controller"
        self.make_empty_group(game)
        self.make_empty_group(controller)
        self.games[0]["path"] = str(game)
        self.groups[self.slot.id]["path"] = str(game)
        self.controller["path"] = self.expected_controller = str(controller)
        self.observation["delegated_identity"] = {"device": shared.stat().st_dev, "inode": shared.stat().st_ino}
        self.inspect()
        self.assertEqual(self.last_observe.args[1], shared)
        self.assertEqual(self.last_observe.kwargs["mask_scope"], "delegated-only")
        self.assertEqual(self.last_topology.args[0], shared)
        self.assertEqual(self.last_topology.kwargs["device"], shared.stat().st_dev)
        self.assertEqual(self.last_topology.kwargs["inode"], shared.stat().st_ino)

    def test_capacity_observation_must_identify_the_same_target_parent(self):
        self.observation["delegated_identity"]["inode"] += 1
        with self.assertRaisesRegex(ValueError, "capacity observation"):
            self.inspect()

    def test_capacity_observation_masks_must_match_the_same_target_topology(self):
        for field in ("delegated_effective_cpus", "delegated_effective_nodes"):
            with self.subTest(field=field):
                original = self.observation[field]
                self.observation[field] = original[:-1]
                with self.assertRaisesRegex(ValueError, "capacity observation"):
                    self.inspect()
                self.observation[field] = original

    def test_capacity_scope_and_extra_nodes_must_match_observed_request(self):
        for field, changed in (("mask_scope", "observer-and-delegated"), ("extra_nodes", [0])):
            with self.subTest(field=field):
                original = self.observation[field]
                self.observation[field] = changed
                with self.assertRaisesRegex(ValueError, "capacity observation"):
                    self.inspect()
                self.observation[field] = original

    def test_game_and_controller_must_be_siblings_and_controller_identity_must_match(self):
        self.expected_controller = str(self.root / "other")
        with self.assertRaisesRegex(ValueError, "controller execution path"):
            self.inspect()
        self.expected_controller = self.controller["path"]
        other = self.root / "other" / "game"
        self.make_empty_group(other)
        self.games[0]["path"] = str(other)
        self.groups[self.slot.id]["path"] = str(other)
        with self.assertRaisesRegex(ValueError, "siblings"):
            self.inspect()

    def test_both_controller_and_game_groups_must_be_fresh_and_empty(self):
        for group in (Path(self.games[0]["path"]), Path(self.controller["path"])):
            for file, contents in (("memory.current", "1\n"), ("memory.peak", "1\n"),
                                   ("cgroup.events", "populated 1\nfrozen 0\n")):
                with self.subTest(group=group.name, file=file):
                    self.make_empty_group(group)
                    (group / file).write_text(contents, encoding="ascii")
                    with self.assertRaisesRegex(ValueError, "fresh empty"):
                        self.inspect()
            self.make_empty_group(group)

    def test_missing_memory_peak_fails_closed(self):
        (Path(self.games[0]["path"]) / "memory.peak").unlink()
        with self.assertRaisesRegex(ValueError, "kernel memory.peak is required"):
            self.inspect()

    def test_each_p192_engine_requires_exactly_192_gib(self):
        result = self.inspect()
        self.assertEqual(result["arithmetic"]["games"][0]["tt_bytes"], 2 * self.tt)
        for index in (0, 1):
            for extent in (128 << 30, self.tt - 1, self.tt + 1):
                with self.subTest(engine=index, extent=extent):
                    self.games[0]["artifacts"][index]["tt_bytes"] = extent
                    with self.assertRaisesRegex(ValueError, "engine TT extent differs"):
                        self.inspect()
                    self.games[0]["artifacts"][index]["tt_bytes"] = self.tt

    def test_p16_node_capacity_does_not_invent_controller_distribution(self):
        self.profile = "test-p16"
        self.slots, self.games, self.groups = [], [], {}
        for index in range(11):
            cpus = tuple(range(index * 16, index * 16 + 16))
            node = index % 2
            slot = topology.Slot(f"slot-{index:03d}", cpus, tuple((0, index * 8 + i) for i in range(8)),
                                 (node,), 16, True, "default")
            self.slots.append(slot)
            path = str(self.root / slot.id)
            self.make_empty_group(Path(path))
            self.games.append({"slot": slot.id, "path": path, "cpus": list(cpus), "nodes": [node],
                               "artifacts": [{"tt_bytes": 100}, {"tt_bytes": 100}]})
            self.groups[slot.id] = {"path": path, "device": 1, "inode": index + 20,
                                    "cpus": list(cpus), "memory_nodes": [node], "memory_max": 220}
        self.controller_cpus = list(range(176, 192))
        self.controller["cpus"] = self.controller_cpus
        self.slot_records = [slot.to_record() for slot in self.slots]
        self.observation["slot_sha256"] = ledger.digest(self.slot_records)
        self.observation["node_available_bytes"] = {0: 6 * 220 + 30, 1: 5 * 220 + 30}
        result = self.inspect()
        self.assertFalse(result["launch_permitted"])
        self.assertEqual(result["arithmetic"]["node_controller_reserve_worst_case_fits"], {0: True, 1: True})
        self.assertFalse(result["arithmetic"]["controller_node_distribution_verified"])
        self.observation["node_available_bytes"][0] -= 1
        result = self.inspect()
        self.assertEqual(result["arithmetic"]["node_controller_reserve_worst_case_fits"], {0: False, 1: True})
        self.assertFalse(result["launch_permitted"])
        # Controller can use a different node, while each game still requires
        # its full local capacity. The aggregate controller-node bound applies.
        self.controller["memory_nodes"] = [0, 1, 2]
        self.observation["extra_nodes"] = [0, 1, 2]
        self.observation["node_available_bytes"] = {0: 6 * 220, 1: 5 * 220, 2: 30}
        result = self.inspect()
        self.assertFalse(result["launch_permitted"])
        self.assertEqual(set(self.last_observe.kwargs["extra_nodes"]), {0, 1, 2})
        self.observation["node_available_bytes"][2] = 29
        with self.assertRaises(ValueError):
            self.inspect()
        self.observation["node_available_bytes"][0] = 6 * 220 - 1
        with self.assertRaises(ValueError):
            self.inspect()

        # P16 is an upper bound, so the explicitly accepted 12 GiB table is
        # valid for each engine. These are integer fixtures, not allocations.
        p16_tt = 12 << 30
        game_limit = 2 * p16_tt + 20
        for game in self.games:
            game["artifacts"] = [{"tt_bytes": p16_tt}, {"tt_bytes": p16_tt}]
            self.groups[game["slot"]]["memory_max"] = game_limit
        required = 11 * game_limit + self.controller["memory_max"]
        self.observation["host_memavailable_bytes"] = required
        self.observation["delegated_cgroup"][0].update(limit_bytes=required, remaining_bytes=required)
        self.observation["node_available_bytes"] = {0: 6 * game_limit, 1: 5 * game_limit, 2: 30}
        result = self.inspect()
        self.assertEqual(result["arithmetic"]["required_bytes"], required)
        self.assertTrue(all(game["tt_bytes"] == 2 * p16_tt for game in result["arithmetic"]["games"]))
        self.games[0]["artifacts"][0]["tt_bytes"] = (16 << 30) + 1
        with self.assertRaisesRegex(ValueError, "engine TT extent differs"):
            self.inspect()


if __name__ == "__main__":
    unittest.main()
