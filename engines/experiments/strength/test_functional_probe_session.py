"""Single-candidate session assembly tests; never start real engines or cgroups."""
import tempfile
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    from . import functional_probe_session as session, topology
except ImportError:
    import functional_probe_session as session
    import topology


def snapshot(profile):
    workers = 16 if profile == "test-p16" else 192
    cores = workers // 2
    cpus = tuple(topology.Cpu(i, 0, i % cores, 0 if profile == "test-p16" or i % cores < cores // 2 else 1,
                              tuple(sorted((i % cores, i % cores + cores))))
                 for i in range(workers))
    return topology.Topology(cpus, tuple(range(workers)), (0, 1), {}, "fixture")


class FakeManager:
    """Record cgroup calls and leave filesystem untouched on close."""
    instances = []
    setup_failure = None
    leaf_failure = None
    close_result = ()

    def __init__(self, root, campaign, *, root_identity):
        if self.setup_failure is not None:
            raise self.setup_failure
        self.root = root
        self.root_identity = root_identity
        self.parent = root / campaign
        self.parent.mkdir()
        parent_stat = self.parent.stat()
        self.created = [(self.parent, parent_stat.st_dev, parent_stat.st_ino)]
        self.calls = []
        self.__class__.instances.append(self)

    def parent_record(self):
        path, device, inode = self.created[0]
        return {"path": str(path), "device": device, "inode": inode}

    def create(self, slot, *, memory_bytes):
        self.calls.append(("create", slot, memory_bytes))
        if self.leaf_failure is not None:
            raise self.leaf_failure
        path = self.parent / slot.id
        path.mkdir()
        s = path.stat()
        self.created.append((path, s.st_dev, s.st_ino))
        return {"path": str(path), "device": s.st_dev, "inode": s.st_ino,
                "cpus": list(slot.cpus), "memory_nodes": list(slot.memory_nodes),
                "memory_max": memory_bytes}

    def close(self):
        self.calls.append(("close",))
        return list(self.close_result)


class FunctionalSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.candidates = self.root / "candidates.json"
        self.candidates.write_text("{}", encoding="utf-8")
        self.out = self.root / "runtime-report"
        self.digest = "a" * 64
        self.profile = "test-p16"
        self.artifact = SimpleNamespace(id="candidate-a", tt_bytes=12 << 30,
                                        workers=16, profile=self.profile)
        self.rows = [{"artifact": self.artifact}]
        self.snapshot = snapshot(self.profile)
        FakeManager.instances = []
        FakeManager.setup_failure = FakeManager.leaf_failure = None
        FakeManager.close_result = ()
        self.read = patch.object(session.diagnostic_candidates, "read_candidates",
                                 side_effect=lambda *args, **kwargs: (self.rows, self.digest))
        self.root_check = patch.object(session.peak_probe_session, "_require_delegated_root",
                                       side_effect=lambda root: root.stat())
        self.topology = patch.object(session.topology.Topology, "snapshot_target",
                                     side_effect=lambda *args, **kwargs: self.snapshot)
        self.manager = patch.object(session.placement, "CgroupSlots", FakeManager)
        self.empty = patch.object(session.peak_capacity, "_require_empty")
        self.probe = patch.object(session.functional_uci_probe, "run_candidate",
                                  return_value={"complete": True, "scored_game_admitted": False})
        for p in (self.read, self.root_check, self.topology, self.manager, self.empty, self.probe):
            mocked = p.start()
            if p is self.read:
                self.read_mock = mocked
            if p is self.empty:
                self.empty_mock = mocked
            if p is self.probe:
                self.probe_mock = mocked
            self.addCleanup(p.stop)

    def create(self, **changes):
        kwargs = {"root": self.root, "campaign": "league-test", "candidate_path": self.candidates,
                  "candidate_sha256": self.digest, "profile": self.profile,
                  "artifact_id": "candidate-a", "out": self.out, "wall_seconds": 120}
        kwargs.update(changes)
        return session.OwnedFunctionalProbe.create(**kwargs)

    def test_p16_uses_one_node_and_exact_tt_plus_aligned_headroom(self):
        owner = self.create()
        self.read_mock.assert_called_once_with(self.candidates, self.digest, "test-p16", allow_single=True)
        manager = owner.manager
        self.assertEqual(manager.root_identity, (self.root.stat().st_dev, self.root.stat().st_ino))
        name, selected, limit = manager.calls[0]
        self.assertEqual(name, "create")
        self.assertEqual(selected.workers, 16)
        self.assertEqual(len(selected.cpus), 16)
        self.assertEqual(len(selected.memory_nodes), 1)
        self.assertEqual(selected.policy, "default")
        self.assertEqual(limit, (12 << 30) + (768 << 20) + (256 << 20))
        self.empty_mock.assert_called_once_with(Path(owner.cgroup["path"]))
        self.assertEqual(owner.close(), [])

    def test_p192_uses_all_192_cpus_and_profile_headroom(self):
        self.profile = "test-p192"
        self.artifact = SimpleNamespace(id="candidate-a", tt_bytes=192 << 30, workers=192,
                                        profile=self.profile)
        self.rows = [{"artifact": self.artifact}]
        self.snapshot = snapshot(self.profile)
        owner = self.create()
        _, slot, limit = owner.manager.calls[0]
        self.assertEqual(len(slot.cpus), 192)
        self.assertEqual(len(slot.physical_cores), 96)
        self.assertEqual(limit, (192 << 30) + 192 * (16 << 20) + (256 << 20))
        self.assertEqual(owner.close(), [])

    def test_run_passes_original_slot_group_and_cpu_envelope(self):
        owner = self.create()
        report = owner.run()
        self.assertTrue(report["complete"])
        self.assertFalse(report["scored_game_admitted"])
        kwargs = self.probe_mock.call_args.kwargs
        self.assertEqual(kwargs["slot"], owner.slot.to_record())
        self.assertEqual(kwargs["cgroup"], owner.cgroup)
        self.assertEqual(kwargs["saved_ancestor_cpus"], list(self.snapshot.allowed_cpus))
        self.assertEqual(owner.saved_ancestor_nodes, list(self.snapshot.allowed_nodes))
        self.assertEqual(kwargs["saved_ancestor_nodes"], list(self.snapshot.allowed_nodes))
        self.assertEqual(kwargs["profile"], "test-p16")
        self.assertEqual(kwargs["artifact_id"], "candidate-a")
        self.assertEqual(kwargs["candidate_sha256"], self.digest)
        self.assertEqual(kwargs["wall_seconds"], 120)
        self.assertNotIn(("close",), owner.manager.calls)
        self.assertEqual(owner.close(), [])

    def test_unknown_or_ambiguous_candidate_is_rejected_before_cgroup(self):
        for rows in ([], [{"artifact": self.artifact}, {"artifact": self.artifact}]):
            with self.subTest(count=len(rows)):
                self.rows = rows
                with self.assertRaises(ValueError):
                    self.create()
                self.assertEqual(FakeManager.instances, [])

    def test_candidate_or_output_preflight_error_does_not_create_cgroup(self):
        with patch.object(session.diagnostic_candidates, "read_candidates", side_effect=ValueError("pin differs")):
            with self.assertRaisesRegex(ValueError, "pin differs"):
                self.create()
        self.assertEqual(FakeManager.instances, [])
        self.out.mkdir()
        with self.assertRaises(ValueError):
            self.create()
        self.assertEqual(FakeManager.instances, [])

    def test_kernel_virtual_output_paths_are_rejected_before_read_or_cgroup(self):
        for path in (Path("/sys/kernel/rove-report"), Path("/proc/rove-report"), Path("/dev/rove-report")):
            with self.subTest(path=str(path)), \
                 patch.object(session.diagnostic_candidates, "_safe_output_path", return_value=path), \
                 patch.object(session.diagnostic_candidates, "read_candidates") as read:
                with self.assertRaisesRegex(ValueError, "virtual filesystems"):
                    self.create(out=path)
                read.assert_not_called()
                self.assertEqual(FakeManager.instances, [])

    def test_wrong_profile_worker_count_or_tt_cap_is_rejected_before_cgroup(self):
        for replacement in (
            {"profile": "test-p192", "workers": 16, "tt_bytes": 12 << 30},
            {"profile": "test-p16", "workers": 192, "tt_bytes": 12 << 30},
            {"profile": "test-p16", "workers": 16, "tt_bytes": (16 << 30) + 1},
        ):
            with self.subTest(replacement=replacement):
                self.artifact = SimpleNamespace(id="candidate-a", **replacement)
                self.rows = [{"artifact": self.artifact}]
                with self.assertRaises(ValueError):
                    self.create()
                self.assertEqual(FakeManager.instances, [])

    def test_inconsistent_smt_siblings_are_rejected_before_cgroup(self):
        cpus = list(self.snapshot.cpus)
        first = cpus[0]
        cpus[0] = topology.Cpu(first.id, first.socket, first.core, first.node, (first.id,))
        self.snapshot = topology.Topology(tuple(cpus), self.snapshot.allowed_cpus,
                                          self.snapshot.allowed_nodes, {}, "fixture")
        with self.assertRaisesRegex(ValueError, "SMT|sibling"):
            self.create()
        self.assertEqual(FakeManager.instances, [])

    def test_delegated_root_identity_change_fails_before_manager(self):
        actual = self.root.stat()
        changed = SimpleNamespace(st_dev=actual.st_dev, st_ino=actual.st_ino + 1)
        with patch.object(session.peak_probe_session, "_require_delegated_root", side_effect=(actual, changed)):
            with self.assertRaises(ValueError):
                self.create()
        self.assertEqual(FakeManager.instances, [])

    def test_parent_topology_change_preserves_setup_failure_and_manager(self):
        actual = self.snapshot
        modified = topology.Topology(actual.cpus, actual.allowed_cpus, actual.allowed_nodes,
                                     {0: {0: 10}}, "different")
        with patch.object(session.topology.Topology, "snapshot_target", side_effect=(actual, modified)):
            with self.assertRaises(session.FunctionalSetupFailure) as caught:
                self.create()
        manager = FakeManager.instances[0]
        self.assertIs(caught.exception.owner, manager)
        self.assertTrue(caught.exception.records)
        self.assertIn(("close",), manager.calls)

    def test_partial_leaf_failure_returns_original_records_and_cleanup_errors(self):
        FakeManager.leaf_failure = ValueError("leaf readback failed")
        FakeManager.close_result = ({"error": "busy"},)
        with self.assertRaises(session.FunctionalSetupFailure) as caught:
            self.create()
        self.assertEqual(caught.exception.cleanup_errors, [{"error": "busy"}])
        self.assertIs(caught.exception.owner, FakeManager.instances[0])
        self.assertTrue(caught.exception.records)

    def test_partial_manager_constructor_preserves_unknown_original_identity(self):
        original = object()
        FakeManager.setup_failure = session.placement.CgroupSetupFailure(
            "setup failed", records=[{"path": "original", "device": 1, "inode": 2}],
            cleanup_errors=[{"error": "cannot verify"}], unrecorded_path="unknown", owner=original)
        with self.assertRaises(session.FunctionalSetupFailure) as caught:
            self.create()
        self.assertIs(caught.exception.owner, original)
        self.assertEqual(caught.exception.cleanup_errors, [{"error": "cannot verify"}])
        self.assertIn({"path": "unknown", "identity_unavailable": True}, caught.exception.records)

    def test_failed_probe_retains_owner_until_explicit_empty_cleanup(self):
        owner = self.create()
        self.probe_mock.side_effect = ValueError("probe failed")
        with self.assertRaisesRegex(ValueError, "probe failed"):
            owner.run()
        self.assertNotIn(("close",), owner.manager.calls)
        FakeManager.close_result = ({"error": "still populated"},)
        self.assertEqual(owner.close(), [{"error": "still populated"}])
        FakeManager.close_result = ()
        self.assertEqual(owner.close(), [])

    def test_one_shot_and_closed_owner_cannot_run(self):
        owner = self.create()
        owner.run()
        with self.assertRaises(ValueError):
            owner.run()
        self.assertEqual(owner.close(), [])
        with self.assertRaises(ValueError):
            owner.run()

    def test_running_owner_rejects_cleanup_until_probe_settles(self):
        owner = self.create()
        owner._running = True
        with self.assertRaises(RuntimeError):
            owner.close()
        self.assertNotIn(("close",), owner.manager.calls)
        owner._running = False
        self.assertEqual(owner.close(), [])

    def test_isolated_cli_can_load_its_sibling_modules(self):
        script = Path(session.__file__).resolve()
        result = subprocess.run([sys.executable, "-I", "-B", str(script), "--help"],
                                capture_output=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        self.assertIn(b"--candidates-sha256", result.stdout)
        self.assertIn(b"--profile", result.stdout)

    def test_cli_retains_probe_exception_and_owner_when_cleanup_raises(self):
        original = ValueError("original probe failure")
        cleanup_error = RuntimeError("group cleanup failed")
        owner = SimpleNamespace(manager=SimpleNamespace(created=[(self.root / "owned", 1, 2)]),
                                run=lambda: (_ for _ in ()).throw(original),
                                close=lambda: (_ for _ in ()).throw(cleanup_error))
        args = ["--root", str(self.root), "--campaign", "league-test",
                "--candidates", str(self.candidates), "--candidates-sha256", self.digest,
                "--profile", "test-p16", "--artifact", "candidate-a", "--out", str(self.out)]
        with patch.object(session.OwnedFunctionalProbe, "create", return_value=owner):
            with self.assertRaises(session.FunctionalCleanupFailure) as caught:
                session.main(args)
        self.assertIs(caught.exception.original, original)
        self.assertIs(caught.exception.owner, owner)
        self.assertIs(caught.exception.__cause__, original)
        self.assertEqual(caught.exception.errors, [{"error": "group cleanup failed"}])

    def test_cli_retains_owner_when_successful_probe_cleanup_raises(self):
        cleanup_error = RuntimeError("group cleanup failed")
        owner = SimpleNamespace(manager=SimpleNamespace(created=[(self.root / "owned", 1, 2)]),
                                run=lambda: {"complete": True},
                                close=lambda: (_ for _ in ()).throw(cleanup_error))
        args = ["--root", str(self.root), "--campaign", "league-test",
                "--candidates", str(self.candidates), "--candidates-sha256", self.digest,
                "--profile", "test-p16", "--artifact", "candidate-a", "--out", str(self.out)]
        with patch.object(session.OwnedFunctionalProbe, "create", return_value=owner):
            with self.assertRaises(session.FunctionalCleanupFailure) as caught:
                session.main(args)
        self.assertIs(caught.exception.owner, owner)
        self.assertIs(caught.exception.__cause__, cleanup_error)
        self.assertEqual(caught.exception.errors, [{"error": "group cleanup failed"}])


if __name__ == "__main__":
    unittest.main()
