"""Assembly contract tests only; no live engines or cgroups."""
import tempfile
from types import SimpleNamespace
from pathlib import Path
import unittest
from unittest.mock import patch

try:
    from . import peak_probe_session as session, topology
except ImportError:
    import peak_probe_session as session
    import topology


class ProbeSessionTests(unittest.TestCase):
    def run_case(self, *, mismatch=False, missing_node=False, topology_mismatch=False, tt_mismatch=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slot = topology.Slot("slot-000", tuple(range(192)), tuple((0, i) for i in range(96)),
                                 (0, 1), 192, True, "default")
            commands = [{"id": "a", "path": "/a", "whole_sha256": "c" * 64, "native_sha256": "a" * 64, "tt_bytes": 12 << 30},
                        {"id": "b", "path": "/b", "whole_sha256": "d" * 64, "native_sha256": "b" * 64, "tt_bytes": 12 << 30}]
            pair = [{"id": c["id"], "native_sha256": c["native_sha256"],
                     "whole_sha256": c["whole_sha256"], "tt_bytes": 12 << 30} for c in commands]
            if mismatch:
                pair.reverse()
            if tt_mismatch:
                pair[0]["tt_bytes"] -= 1
            manifest = {"profile": "test-p192", "entries": [{"slot": slot, "engines": commands}], "topology": {"synthetic": True, "cpus": [1, 2]},
                        "runner_sha256": "d" * 64}
            game = {"path": str(root / "game"), "cpus": list(slot.cpus), "memory_nodes": list(slot.memory_nodes)}
            controller = {"path": str(root / "controller"), "cpus": list(slot.cpus), "memory_nodes": list(slot.memory_nodes)}
            (root / "game").mkdir()
            (root / "controller").mkdir()
            if missing_node:
                controller["memory_nodes"] = [0]
            with patch.object(session.peak_ready_probe, "load_controller_manifest", return_value=manifest), \
                 patch.object(session.topology.Topology, "snapshot_target", return_value=type("Snapshot", (), {"to_record": lambda self: {"synthetic": not topology_mismatch, "cpus": (1, 2)}})()), \
                 patch.object(session.placement, "verify_cgroup_live", side_effect=lambda record: record), \
                 patch.object(session.overhead, "_sha_file", return_value="e" * 64), \
                 patch.object(Path, "read_text", return_value="12345678-1234-1234-1234-123456789abc"), \
                 patch.object(session.peak_ready_probe, "observe_and_record", return_value=("receipt", "owner")) as observe:
                kwargs = dict(manifest_path=root / "manifest.json", manifest_sha256="f" * 64, root=root,
                              games={slot.id: game}, controller=controller, artifacts={slot.id: pair},
                              report_path=root / "report.json", append=lambda *_: None,
                              per_game_headroom_bytes=1, controller_headroom_bytes=1)
                if mismatch or missing_node or topology_mismatch or tt_mismatch:
                    message = "topology" if topology_mismatch else "memory nodes" if missing_node else "colour order"
                    with self.assertRaisesRegex(ValueError, message):
                        session.observe_ready(**kwargs)
                    observe.assert_not_called()
                    return
                self.assertEqual(session.observe_ready(**kwargs), ("receipt", "owner"))
                args = observe.call_args.kwargs["observe_args"]
                self.assertEqual(args["games"][0]["artifacts"], pair)
                self.assertIn("--manifest-sha256", args["argv"])
                expected = observe.call_args.kwargs["expected_context"]()
                self.assertEqual(expected["plan"][0]["artifacts"], pair)
                self.assertEqual(expected["controller_cgroup_path"], controller["path"])

    def test_builds_pinned_diagnostic_and_independent_context(self):
        self.run_case()

    def test_reversed_artifact_identity_fails_before_supervision(self):
        self.run_case(mismatch=True)

    def test_controller_must_cover_game_nodes_before_supervision(self):
        self.run_case(missing_node=True)

    def test_current_host_topology_must_match_frozen_plan_before_launch(self):
        self.run_case(topology_mismatch=True)

    def test_tt_extent_must_match_frozen_manifest_before_launch(self):
        self.run_case(tt_mismatch=True)

    def test_owned_cohort_creates_two_tt_extents_and_never_cleans_live_child(self):
        # This is a group-manager fixture; it neither creates kernel cgroups
        # nor bypasses the production supervisor's CapacityPending guard.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            slot = topology.Slot("slot-000", (0, 1), ((0, 0),), (0,), 2, True, "default")
            engines = [{"id": "a", "path": str(root / "a"), "whole_sha256": "a" * 64, "native_sha256": "b" * 64, "tt_bytes": 1000},
                       {"id": "b", "path": str(root / "b"), "whole_sha256": "c" * 64, "native_sha256": "d" * 64, "tt_bytes": 2000}]
            manifest = {"profile": "test-p192", "entries": [{"slot": slot, "engines": engines,
                        "opening_start": 1, "out": str(root / "out")}], "saved_ancestor_cpus": [0, 1],
                        "topology": {"fixture": [1, 2]}, "runner": str(root / "runner"), "runner_sha256": "e" * 64,
                        "opening": str(root / "opening"), "opening_sha256": "f" * 64}
            snapshot = SimpleNamespace(allowed_nodes=(0,), allowed_cpus=(0, 1), to_record=lambda: {"fixture": (1, 2)})

            class Manager:
                def __init__(self, supplied_root, campaign, *, root_identity):
                    if root_identity != (supplied_root.stat().st_dev, supplied_root.stat().st_ino):
                        raise ValueError("root identity differs")
                    self.root, self.parent, self.created, self.calls = supplied_root, supplied_root / campaign, [], []
                    self.parent.mkdir()
                    s = self.parent.stat()
                    self.created.append((self.parent, s.st_dev, s.st_ino))
                def parent_record(self):
                    path, device, inode = self.created[0]
                    return {"path": str(path), "device": device, "inode": inode}
                def make(self, name, cpus, nodes, memory):
                    path = self.parent / name
                    path.mkdir()
                    s = path.stat()
                    self.created.append((path, s.st_dev, s.st_ino))
                    self.calls.append((name, list(cpus), list(nodes), memory))
                    return {"path": str(path), "device": s.st_dev, "inode": s.st_ino,
                            "cpus": list(cpus), "memory_nodes": list(nodes), "memory_max": memory}
                def create_controller(self, *, cpus, memory_nodes, memory_bytes):
                    return self.make("controller", cpus, memory_nodes, memory_bytes)
                def create(self, item, *, memory_bytes):
                    return self.make(item.id, item.cpus, item.memory_nodes, memory_bytes)
                def close(self):
                    self.calls.append(("close",))
                    return []

            with patch.object(session.peak_ready_probe, "load_controller_manifest", return_value=manifest), \
                 patch.object(session.peak_ready_probe, "_file_sha", side_effect=lambda path: {
                     "runner": "e" * 64, "opening": "f" * 64, "a": "a" * 64, "b": "c" * 64}[path.name]), \
                 patch.object(session, "_require_delegated_root", return_value=root.stat()), \
                 patch.object(session.topology.Topology, "snapshot_target", return_value=snapshot), \
                 patch.object(session.run, "league_placement", return_value=([slot], [0, 1])), \
                 patch.object(session.placement, "CgroupSlots", Manager), \
                 patch.object(session.peak_capacity, "_require_empty"), \
                 patch.object(session.os, "sysconf", return_value=4096, create=True):
                owner = session.OwnedProbeCohort.create(root=root, campaign="fixture", manifest_path=root / "m.json",
                    manifest_sha256="f" * 64, per_game_headroom_bytes=2000, controller_headroom_bytes=1000)
                self.assertEqual(owner.manager.calls[:2], [("controller", [0, 1], [0], 4096),
                                                          ("slot-000", [0, 1], [0], 8192)])
                self.assertEqual(owner.artifacts["slot-000"][1]["tt_bytes"], 2000)
                with patch.object(session.placement, "verify_cgroup_live", side_effect=lambda row: row), \
                     patch.object(session.overhead, "_sha_file", return_value="e" * 64), \
                     patch.object(Path, "read_text", return_value="12345678-1234-1234-1234-123456789abc"), \
                     patch.object(session.peak_capacity, "inspect_capacity", return_value={"runtime_admission": False}), \
                     patch.object(session.peak_supervisor.subprocess, "Popen") as popen:
                    with self.assertRaises(session.peak_supervisor.CapacityPending):
                        owner.observe(report_path=root / "pending.json", append=lambda *_: None)
                    popen.assert_not_called()
                live = SimpleNamespace(pid=4321, poll=lambda: None)
                with patch.object(session, "observe_ready", side_effect=session.peak_supervisor.SupervisorFailure("uncertain", live)):
                    with self.assertRaises(session.peak_supervisor.SupervisorFailure):
                        owner.observe(report_path=root / "r.json", append=lambda *_: None)
                self.assertEqual(owner.close(), [{"error": "original diagnostic child remains live", "pid": 4321}])
                self.assertNotIn(("close",), owner.manager.calls)
                live.poll = lambda: 0
                self.assertEqual(owner.close(), [])
                self.assertEqual(owner.manager.calls[-1], ("close",))

    def test_owned_cohort_rejects_bad_engine_before_delegation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            slot = topology.Slot("slot-000", (0, 1), ((0, 0),), (0,), 2, True, "default")
            manifest = {"profile": "test-p192", "entries": [{"slot": slot, "engines": [{"id": "bad"}, {}],
                        "opening_start": 1, "out": str(root / "out")}], "saved_ancestor_cpus": [0, 1],
                        "topology": {"fixture": [1, 2]}, "runner": str(root / "runner"), "runner_sha256": "e" * 64,
                        "opening": str(root / "opening"), "opening_sha256": "f" * 64}
            snapshot = SimpleNamespace(allowed_nodes=(0,), allowed_cpus=(0, 1), to_record=lambda: {"fixture": (1, 2)})
            with patch.object(session.peak_ready_probe, "load_controller_manifest", return_value=manifest), \
                 patch.object(session.peak_ready_probe, "_file_sha", side_effect=lambda path: "e" * 64 if path.name == "runner" else "f" * 64), \
                 patch.object(session, "_require_delegated_root", return_value=root.stat()), \
                 patch.object(session.topology.Topology, "snapshot_target", return_value=snapshot), \
                 patch.object(session.run, "league_placement", return_value=([slot], [0, 1])), \
                 patch.object(session.placement, "CgroupSlots") as manager, \
                 patch.object(session.os, "sysconf", return_value=4096, create=True):
                with self.assertRaisesRegex(ValueError, "invalid pinned engine"):
                    session.OwnedProbeCohort.create(root=root, campaign="fixture", manifest_path=root / "m.json",
                        manifest_sha256="f" * 64, per_game_headroom_bytes=1, controller_headroom_bytes=1)
                manager.assert_not_called()

    def test_owned_cohort_preserves_failed_constructor_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            slot = topology.Slot("slot-000", (0, 1), ((0, 0),), (0,), 2, True, "default")
            engines = [{"id": "a", "path": str(root / "a"), "whole_sha256": "a" * 64, "native_sha256": "b" * 64, "tt_bytes": 1},
                       {"id": "b", "path": str(root / "b"), "whole_sha256": "c" * 64, "native_sha256": "d" * 64, "tt_bytes": 1}]
            manifest = {"profile": "test-p192", "entries": [{"slot": slot, "engines": engines,
                        "opening_start": 1, "out": str(root / "out")}], "saved_ancestor_cpus": [0, 1],
                        "topology": {"fixture": [1, 2]}, "runner": str(root / "runner"), "runner_sha256": "e" * 64,
                        "opening": str(root / "opening"), "opening_sha256": "f" * 64}
            snapshot = SimpleNamespace(allowed_nodes=(0,), allowed_cpus=(0, 1), to_record=lambda: {"fixture": (1, 2)})
            failure = session.placement.CgroupSetupFailure("init failed", records=[{"path": "original", "device": 1, "inode": 2}],
                cleanup_errors=[{"error": "busy"}])
            with patch.object(session.peak_ready_probe, "load_controller_manifest", return_value=manifest), \
                 patch.object(session.peak_ready_probe, "_file_sha", side_effect=lambda path: {
                     "runner": "e" * 64, "opening": "f" * 64, "a": "a" * 64, "b": "c" * 64}[path.name]), \
                 patch.object(session, "_require_delegated_root", return_value=root.stat()), \
                 patch.object(session.topology.Topology, "snapshot_target", return_value=snapshot), \
                 patch.object(session.run, "league_placement", return_value=([slot], [0, 1])), \
                 patch.object(session.placement, "CgroupSlots", side_effect=failure), \
                 patch.object(session.os, "sysconf", return_value=4096, create=True):
                with self.assertRaises(session.CohortSetupFailure) as caught:
                    session.OwnedProbeCohort.create(root=root, campaign="fixture", manifest_path=root / "m.json",
                        manifest_sha256="f" * 64, per_game_headroom_bytes=1, controller_headroom_bytes=1)
                self.assertEqual(caught.exception.records, failure.records)
                self.assertEqual(caught.exception.cleanup_errors, failure.cleanup_errors)

    def test_owned_cohort_preserves_unrecorded_leaf_and_live_manager(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            slot = topology.Slot("slot-000", (0, 1), ((0, 0),), (0,), 2, True, "default")
            engines = [{"id": "a", "path": str(root / "a"), "whole_sha256": "a" * 64, "native_sha256": "b" * 64, "tt_bytes": 1},
                       {"id": "b", "path": str(root / "b"), "whole_sha256": "c" * 64, "native_sha256": "d" * 64, "tt_bytes": 1}]
            manifest = {"profile": "test-p192", "entries": [{"slot": slot, "engines": engines,
                        "opening_start": 1, "out": str(root / "out")}], "saved_ancestor_cpus": [0, 1],
                        "topology": {"fixture": [1, 2]}, "runner": str(root / "runner"), "runner_sha256": "e" * 64,
                        "opening": str(root / "opening"), "opening_sha256": "f" * 64}
            snapshot = SimpleNamespace(allowed_nodes=(0,), allowed_cpus=(0, 1), to_record=lambda: {"fixture": (1, 2)})
            class Manager:
                def __init__(self, supplied_root, campaign, *, root_identity):
                    self.root, self.parent = supplied_root, supplied_root / campaign
                    self.parent.mkdir()
                    s = self.parent.stat()
                    self.created = [(self.parent, s.st_dev, s.st_ino)]
                def parent_record(self):
                    path, device, inode = self.created[0]
                    return {"path": str(path), "device": device, "inode": inode}
                def create_controller(self, **_kwargs):
                    path = self.parent / "controller"
                    path.mkdir()
                    raise session.placement.CgroupSetupFailure("open failed", records=[self.parent_record()],
                        cleanup_errors=[], unrecorded_path=str(path), owner=self)
                def close(self):
                    return [{"path": str(self.parent), "error": "unknown child"}]

            with patch.object(session.peak_ready_probe, "load_controller_manifest", return_value=manifest), \
                 patch.object(session.peak_ready_probe, "_file_sha", side_effect=lambda path: {
                     "runner": "e" * 64, "opening": "f" * 64, "a": "a" * 64, "b": "c" * 64}[path.name]), \
                 patch.object(session, "_require_delegated_root", return_value=root.stat()), \
                 patch.object(session.topology.Topology, "snapshot_target", return_value=snapshot), \
                 patch.object(session.run, "league_placement", return_value=([slot], [0, 1])), \
                 patch.object(session.placement, "CgroupSlots", Manager), \
                 patch.object(session.os, "sysconf", return_value=4096, create=True):
                with self.assertRaises(session.CohortSetupFailure) as caught:
                    session.OwnedProbeCohort.create(root=root, campaign="fixture", manifest_path=root / "m.json",
                        manifest_sha256="f" * 64, per_game_headroom_bytes=1, controller_headroom_bytes=1)
                self.assertIsInstance(caught.exception.owner, Manager)
                self.assertEqual(caught.exception.records[-1], {"path": str(root / "fixture" / "controller"),
                                                               "identity_unavailable": True})
                self.assertEqual(caught.exception.cleanup_errors[0]["error"], "unknown child")

    def test_owned_cohort_rejects_non_cgroup_root_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with self.assertRaisesRegex(ValueError, "dedicated descendant"):
                session._require_delegated_root(root)
            self.assertEqual(list(root.iterdir()), [])

    def test_owned_cohort_rejects_nested_output_directories_before_delegation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            first = topology.Slot("slot-000", (0, 1), ((0, 0),), (0,), 2, True, "default")
            second = topology.Slot("slot-001", (2, 3), ((0, 1),), (0,), 2, True, "default")
            engines = [{"id": "a", "path": str(root / "a"), "whole_sha256": "a" * 64, "native_sha256": "b" * 64, "tt_bytes": 1},
                       {"id": "b", "path": str(root / "b"), "whole_sha256": "c" * 64, "native_sha256": "d" * 64, "tt_bytes": 1}]
            manifest = {"profile": "test-p16", "saved_ancestor_cpus": [0, 1, 2, 3],
                "entries": [{"slot": first, "engines": engines, "opening_start": 1, "out": str(root / "out")},
                            {"slot": second, "engines": engines, "opening_start": 2, "out": str(root / "out" / "child")}],
                "topology": {"fixture": [1, 2]}, "runner": str(root / "runner"), "runner_sha256": "e" * 64,
                "opening": str(root / "opening"), "opening_sha256": "f" * 64}
            snapshot = SimpleNamespace(allowed_nodes=(0,), allowed_cpus=(0, 1, 2, 3), to_record=lambda: {"fixture": (1, 2)})
            with patch.object(session.peak_ready_probe, "load_controller_manifest", return_value=manifest), \
                 patch.object(session.peak_ready_probe, "_file_sha", side_effect=lambda path: {
                     "runner": "e" * 64, "opening": "f" * 64, "a": "a" * 64, "b": "c" * 64}[path.name]), \
                 patch.object(session, "_require_delegated_root", return_value=root.stat()), \
                 patch.object(session.topology.Topology, "snapshot_target", return_value=snapshot), \
                 patch.object(session.run, "league_placement", return_value=([first, second], [0, 1])), \
                 patch.object(session.placement, "CgroupSlots") as manager, \
                 patch.object(session.os, "sysconf", return_value=4096, create=True):
                with self.assertRaisesRegex(ValueError, "distinct new external"):
                    session.OwnedProbeCohort.create(root=root, campaign="fixture", manifest_path=root / "m.json",
                        manifest_sha256="f" * 64, per_game_headroom_bytes=1, controller_headroom_bytes=1)
                manager.assert_not_called()

    def test_owned_p16_cohort_constructs_all_eleven_shared_cpu_slots(self):
        # The manager and topology are fixtures: no large engine is launched.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            slots = [topology.Slot(f"slot-{i:03}", tuple(range(16 * i, 16 * (i + 1))),
                     tuple((0, j) for j in range(8 * i, 8 * (i + 1))), (0,), 16, True, "default")
                     for i in range(11)]
            engines = [{"id": "a", "path": str(root / "a"), "whole_sha256": "a" * 64, "native_sha256": "b" * 64, "tt_bytes": 12 << 30},
                       {"id": "b", "path": str(root / "b"), "whole_sha256": "c" * 64, "native_sha256": "d" * 64, "tt_bytes": 16 << 30}]
            manifest = {"profile": "test-p16", "saved_ancestor_cpus": list(range(192)),
                "entries": [{"slot": slot, "engines": engines, "opening_start": i + 1, "out": str(root / f"out-{i}")}
                            for i, slot in enumerate(slots)],
                "topology": {"fixture": [1, 2]}, "runner": str(root / "runner"), "runner_sha256": "e" * 64,
                "opening": str(root / "opening"), "opening_sha256": "f" * 64}
            snapshot = SimpleNamespace(allowed_nodes=(0,), allowed_cpus=tuple(range(192)), to_record=lambda: {"fixture": (1, 2)})
            class Manager:
                def __init__(self, supplied_root, campaign, *, root_identity):
                    self.root, self.parent, self.created = supplied_root, supplied_root / campaign, []
                    self.parent.mkdir()
                    s = self.parent.stat()
                    self.created.append((self.parent, s.st_dev, s.st_ino))
                def parent_record(self):
                    path, device, inode = self.created[0]
                    return {"path": str(path), "device": device, "inode": inode}
                def make(self, name, cpus, nodes, memory):
                    path = self.parent / name
                    path.mkdir()
                    s = path.stat()
                    self.created.append((path, s.st_dev, s.st_ino))
                    return {"path": str(path), "device": s.st_dev, "inode": s.st_ino,
                            "cpus": list(cpus), "memory_nodes": list(nodes), "memory_max": memory}
                def create_controller(self, *, cpus, memory_nodes, memory_bytes):
                    return self.make("controller", cpus, memory_nodes, memory_bytes)
                def create(self, item, *, memory_bytes):
                    return self.make(item.id, item.cpus, item.memory_nodes, memory_bytes)
                def close(self):
                    return []
            with patch.object(session.peak_ready_probe, "load_controller_manifest", return_value=manifest), \
                 patch.object(session.peak_ready_probe, "_file_sha", side_effect=lambda path: {
                     "runner": "e" * 64, "opening": "f" * 64, "a": "a" * 64, "b": "c" * 64}[path.name]), \
                 patch.object(session, "_require_delegated_root", return_value=root.stat()), \
                 patch.object(session.topology.Topology, "snapshot_target", return_value=snapshot), \
                 patch.object(session.run, "league_placement", return_value=(slots, list(range(176, 192)))), \
                 patch.object(session.placement, "CgroupSlots", Manager), \
                 patch.object(session.peak_capacity, "_require_empty"), \
                 patch.object(session.os, "sysconf", return_value=4096, create=True):
                owner = session.OwnedProbeCohort.create(root=root, campaign="fixture", manifest_path=root / "m.json",
                    manifest_sha256="f" * 64, per_game_headroom_bytes=1, controller_headroom_bytes=1)
                self.assertEqual(len(owner.games), 11)
                self.assertEqual(owner.controller["cpus"], list(range(176, 192)))
                for slot in slots:
                    self.assertEqual(owner.games[slot.id]["cpus"], list(slot.cpus))
                    self.assertEqual(owner.games[slot.id]["memory_nodes"], [0])
                    self.assertEqual(owner.games[slot.id]["memory_max"], (28 << 30) + 4096)
                    self.assertEqual([row["tt_bytes"] for row in owner.artifacts[slot.id]], [12 << 30, 16 << 30])
                self.assertEqual(owner.close(), [])

    def test_owned_cohort_rejects_bad_memory_before_delegation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with patch.object(session.peak_ready_probe, "load_controller_manifest", return_value={}), \
                 patch.object(session.placement, "CgroupSlots") as manager:
                with self.assertRaisesRegex(ValueError, "per-game headroom"):
                    session.OwnedProbeCohort.create(root=root, campaign="fixture", manifest_path=root / "m.json",
                        manifest_sha256="f" * 64, per_game_headroom_bytes=0, controller_headroom_bytes=1)
                manager.assert_not_called()


if __name__ == "__main__":
    unittest.main()
