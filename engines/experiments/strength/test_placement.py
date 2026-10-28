import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import select
import signal
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import placement


class PlacementTests(unittest.TestCase):
    def test_live_cgroup_observation_requires_original_identity_and_limits(self):
        # Fake attributes exercise the parser and receipt binding only; they do
        # not establish real cgroup, ancestor or memory-page observations.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / "slot-000"
            path.mkdir()
            cpu_path, node_path, memory_path = (path / "cpuset.cpus.effective",
                                                path / "cpuset.mems.effective", path / "memory.max")
            cpu_path.write_text("2-3\n")
            node_path.write_text("1\n")
            memory_path.write_text("4096\n")
            stat = path.stat()
            receipt = {"path": str(path), "device": stat.st_dev, "inode": stat.st_ino,
                       "cpus": [2, 3], "memory_nodes": [1], "memory_max": 4096}
            result = placement.verify_cgroup_live(receipt)
            self.assertEqual({key: result[key] for key in receipt}, receipt)
            self.assertIn("not ancestor capacity", result["scope"])
            self.assertIn("observed_at_utc", result)

            for label, attribute, value in (
                    ("changed-cpu", cpu_path, "2\n"), ("changed-node", node_path, "0-1\n"),
                    ("changed-memory", memory_path, "8192\n"), ("unlimited", memory_path, "max\n"),
                    ("malformed", memory_path, "invalid\n"), ("missing", memory_path, None)):
                cpu_path.write_text("2-3\n")
                node_path.write_text("1\n")
                memory_path.write_text("4096\n")
                if value is None:
                    attribute.unlink()
                else:
                    attribute.write_text(value)
                with self.subTest(label=label), self.assertRaises((ValueError, OSError)):
                    placement.verify_cgroup_live(receipt)

            memory_path.write_text("4096\n")
            for label, altered in (
                    ("replaced-inode", {**receipt, "inode": receipt["inode"] + 1}),
                    ("spoofed-device", {**receipt, "device": receipt["device"] + 1}),
                    ("spoofed-cpu", {**receipt, "cpus": [2]}),
                    ("spoofed-node", {**receipt, "memory_nodes": [0]}),
                    ("spoofed-memory", {**receipt, "memory_max": 8192}),
                    ("duplicate-cpu", {**receipt, "cpus": [2, 2, 3]}),
                    ("boolean-node", {**receipt, "memory_nodes": [True]}),
                    ("boolean-memory", {**receipt, "memory_max": True}),
                    ("missing-memory", {key: value for key, value in receipt.items() if key != "memory_max"})):
                with self.subTest(label=label), self.assertRaises(ValueError):
                    placement.verify_cgroup_live(altered)

    def test_cgroup_create_checks_actual_memory_max_readback(self):
        # Regular temporary files stand in for cgroupfs attributes: this tests
        # readback handling, not a kernel cgroup or actual memory admission.
        with tempfile.TemporaryDirectory() as tmp:
            manager = object.__new__(placement.CgroupSlots)
            manager.parent = Path(tmp).resolve()
            manager.created = []
            memory = 26 << 30
            original_read = Path.read_text

            def read_attributes(path, *args, **kwargs):
                if path.name == "cpuset.cpus.effective":
                    return original_read(path.parent / "cpuset.cpus", *args, **kwargs)
                if path.name == "cpuset.mems.effective":
                    return original_read(path.parent / "cpuset.mems", *args, **kwargs)
                return original_read(path, *args, **kwargs)

            slot = SimpleNamespace(id="slot-000", cpus=(2, 3), memory_nodes=(1,))
            with patch.object(Path, "read_text", autospec=True, side_effect=read_attributes):
                result = manager.create(slot, memory_bytes=memory)
            self.assertEqual(result["memory_max"], memory)
            self.assertEqual(result["cpus"], [2, 3])
            self.assertEqual(result["memory_nodes"], [1])

            for index, override in enumerate(("max", str(memory + 4096), "invalid"), 1):
                def changed_read(path, *args, **kwargs):
                    if path.name == "memory.max":
                        return override
                    return read_attributes(path, *args, **kwargs)
                slot = SimpleNamespace(id=f"slot-{index:03}", cpus=(2, 3), memory_nodes=(1,))
                with self.subTest(readback=override), patch.object(Path, "read_text", autospec=True,
                                                                  side_effect=changed_read):
                    with self.assertRaisesRegex(ValueError, "memory.max readback differs"):
                        manager.create(slot, memory_bytes=memory)
                self.assertEqual(manager.created[-1][0], manager.parent / slot.id)

            def missing_read(path, *args, **kwargs):
                if path.name == "memory.max":
                    raise OSError("kernel readback unavailable")
                return read_attributes(path, *args, **kwargs)
            slot = SimpleNamespace(id="slot-004", cpus=(2, 3), memory_nodes=(1,))
            with patch.object(Path, "read_text", autospec=True, side_effect=missing_read):
                with self.assertRaisesRegex(OSError, "readback unavailable"):
                    manager.create(slot, memory_bytes=memory)
            self.assertEqual(manager.created[-1][0], manager.parent / slot.id)

    def test_controller_group_is_created_and_cleaned_with_its_original_identity(self):
        # Attribute files and rmdir are fixtures, not evidence of real cgroups.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manager = object.__new__(placement.CgroupSlots)
            manager.root, manager.parent, manager.created = root, root / "campaign-fixture", []
            manager.parent.mkdir()
            stat = manager.parent.stat()
            manager.created.append((manager.parent, stat.st_dev, stat.st_ino))
            original_read = Path.read_text

            def read_attributes(path, *args, **kwargs):
                if path.name == "cpuset.cpus.effective":
                    return original_read(path.parent / "cpuset.cpus", *args, **kwargs)
                if path.name == "cpuset.mems.effective":
                    return original_read(path.parent / "cpuset.mems", *args, **kwargs)
                return original_read(path, *args, **kwargs)

            with patch.object(Path, "read_text", autospec=True, side_effect=read_attributes):
                record = manager.create_controller(cpus=[0, 1], memory_nodes=[0], memory_bytes=8192)
            self.assertEqual(Path(record["path"]).name, "controller")
            self.assertEqual((record["cpus"], record["memory_nodes"], record["memory_max"]), ([0, 1], [0], 8192))
            controller = manager.parent / "controller"
            for path in (controller, manager.parent):
                (path / "cgroup.events").write_text("populated 0\n")
            (controller / "cgroup.events").write_text("populated 1\n")
            (manager.parent / "cgroup.events").write_text("populated 1\n")
            with patch.object(Path, "rmdir", autospec=True) as remove:
                errors = manager.close()
            self.assertTrue(any("contains tasks" in error["error"] for error in errors))
            remove.assert_not_called()
            # A different, unrecorded child makes the kernel's parent rmdir
            # fail even when the recorded controller is already empty.
            (controller / "cgroup.events").write_text("populated 0\n")
            (manager.parent / "cgroup.events").write_text("populated 0\n")
            def busy_parent(path):
                if path == manager.parent:
                    raise OSError(16, "unrecorded child remains")
            with patch.object(Path, "rmdir", autospec=True, side_effect=busy_parent):
                errors = manager.close()
            self.assertTrue(any("unrecorded child remains" in error["error"] for error in errors))
            with patch.object(Path, "rmdir", autospec=True) as remove:
                self.assertEqual(manager.close(), [])
                self.assertEqual([call.args[0] for call in remove.call_args_list], [controller, manager.parent])
                self.assertEqual(manager.close(), [])
                self.assertEqual(remove.call_count, 2)
            with self.assertRaises(ValueError):
                placement.cleanup_owned_groups([{"path": str(manager.parent / "unrecorded"),
                                                  "device": stat.st_dev, "inode": stat.st_ino}], root=root)

    def test_controller_rejects_bad_masks_before_creating_any_leaf(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = object.__new__(placement.CgroupSlots)
            manager.parent, manager.created = Path(tmp), []
            for cpus, nodes, memory in (([0, 0], [0], 4096), ([True], [0], 4096),
                                        ([0], [], 4096), ([0], [0], True)):
                with self.subTest(cpus=cpus, nodes=nodes, memory=memory), self.assertRaises(ValueError):
                    manager.create_controller(cpus=cpus, memory_nodes=nodes, memory_bytes=memory)
            self.assertEqual(manager.created, [])

    def test_partial_parent_setup_reports_original_identity_and_cleanup_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "cgroup.controllers").write_text("cpuset memory\n")
            (root / "cgroup.subtree_control").write_text("")
            original_write = Path.write_text

            def write(path, *args, **kwargs):
                if path == root / "fixture" / "cgroup.subtree_control":
                    raise OSError("controller activation failed")
                return original_write(path, *args, **kwargs)

            with patch.object(Path, "write_text", autospec=True, side_effect=write):
                with self.assertRaises(placement.CgroupSetupFailure) as caught:
                    placement.CgroupSlots(root, "fixture")
            self.assertEqual(caught.exception.records[0]["path"], str(root / "fixture"))
            self.assertGreater(caught.exception.records[0]["inode"], 0)
            self.assertTrue(caught.exception.cleanup_errors)
            self.assertTrue((root / "fixture").is_dir())

    def test_leaf_identity_drift_rejects_and_retains_original_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manager = object.__new__(placement.CgroupSlots)
            manager.parent, manager.created = root, []
            original_read, original_stat = Path.read_text, Path.stat
            leaf = root / "controller"
            leaf_calls = 0

            def read_attributes(path, *args, **kwargs):
                if path.name == "cpuset.cpus.effective":
                    return original_read(path.parent / "cpuset.cpus", *args, **kwargs)
                if path.name == "cpuset.mems.effective":
                    return original_read(path.parent / "cpuset.mems", *args, **kwargs)
                return original_read(path, *args, **kwargs)

            def observed_stat(path, *args, **kwargs):
                nonlocal leaf_calls
                value = original_stat(path, *args, **kwargs)
                if path == leaf:
                    leaf_calls += 1
                    if leaf_calls == 2:
                        return SimpleNamespace(st_dev=value.st_dev, st_ino=value.st_ino + 1)
                return value

            with patch.object(Path, "read_text", autospec=True, side_effect=read_attributes), \
                 patch.object(Path, "stat", autospec=True, side_effect=observed_stat):
                with self.assertRaisesRegex(ValueError, "identity changed during setup"):
                    manager.create_controller(cpus=[0], memory_nodes=[0], memory_bytes=4096)
            self.assertEqual(manager.created[0][0], leaf)
            self.assertEqual(manager.created[0][2], leaf.stat().st_ino)

    @unittest.skipUnless(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "Linux dir-fd support required")
    def test_anchored_cohort_uses_original_directory_handles(self):
        # Real openat/mkdir identities with simulated cgroup attribute I/O.
        # This does not create or prove a kernel cgroup.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            root_stat = root.stat()
            values = {}

            def attr(fd, name, *, value=None):
                inode = os.fstat(fd).st_ino
                if value is not None:
                    values[inode, name] = value
                    return None
                if name == "cgroup.controllers":
                    return "cpuset memory"
                if name.endswith(".effective"):
                    return values[inode, name.removesuffix(".effective")]
                return values[inode, name]

            with patch.object(placement, "_cgroup_at", side_effect=attr), \
                 patch.object(placement, "cleanup_owned_groups", side_effect=lambda rows, **_: [
                     {**row, "removed": True} for row in rows]) as cleanup:
                manager = placement.CgroupSlots(root, "fixture", root_identity=(root_stat.st_dev, root_stat.st_ino))
                controller = manager.create_controller(cpus=[0, 1], memory_nodes=[0], memory_bytes=4096)
                slot = manager.create(SimpleNamespace(id="slot-000", cpus=(0, 1), memory_nodes=(0,)), memory_bytes=8192)
                self.assertEqual((controller["memory_max"], slot["memory_max"]), (4096, 8192))
                self.assertEqual([path.name for path, _, _ in manager.created], ["fixture", "controller", "slot-000"])
                root_fd, parent_fd = manager._root_fd, manager._parent_fd
                self.assertEqual(manager.close(), [])
                cleanup.assert_called_once()
                for fd in (root_fd, parent_fd):
                    with self.assertRaises(OSError):
                        os.fstat(fd)

    @unittest.skipUnless(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "Linux dir-fd support required")
    def test_anchored_cleanup_preserves_handles_when_a_group_disappears(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            root_stat = root.stat()
            def attr(_fd, name, *, value=None):
                return "cpuset memory" if value is None and name == "cgroup.controllers" else None
            with patch.object(placement, "_cgroup_at", side_effect=attr):
                manager = placement.CgroupSlots(root, "fixture", root_identity=(root_stat.st_dev, root_stat.st_ino))
            row = manager.parent_record()
            root_fd, parent_fd = manager._root_fd, manager._parent_fd
            try:
                with patch.object(placement, "cleanup_owned_groups", return_value=[{**row, "already_absent": True}]):
                    errors = manager.close()
                self.assertIn("disappeared without verified removal", errors[0]["error"])
                os.fstat(root_fd)
                os.fstat(parent_fd)
            finally:
                manager._close_fds()

    @unittest.skipUnless(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "Linux dir-fd support required")
    def test_anchored_cohort_rejects_changed_root_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            stat = root.stat()
            with patch.object(placement, "_cgroup_at") as attr:
                with self.assertRaises(placement.CgroupSetupFailure) as caught:
                    placement.CgroupSlots(root, "fixture", root_identity=(stat.st_dev, stat.st_ino + 1))
                attr.assert_not_called()
            self.assertEqual(caught.exception.records, [])
            self.assertFalse((root / "fixture").exists())

    @unittest.skipUnless(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "Linux dir-fd support required")
    def test_anchored_leaf_open_failure_retains_unrecorded_path_and_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            stat = root.stat()
            def attr(_fd, name, *, value=None):
                return "cpuset memory" if value is None and name == "cgroup.controllers" else None
            with patch.object(placement, "_cgroup_at", side_effect=attr):
                manager = placement.CgroupSlots(root, "fixture", root_identity=(stat.st_dev, stat.st_ino))
            real_open = os.open
            def opening(path, flags, *args, **kwargs):
                if path == "controller" and kwargs.get("dir_fd") == manager._parent_fd:
                    raise OSError("leaf open failed")
                return real_open(path, flags, *args, **kwargs)
            try:
                with patch.object(placement.os, "open", side_effect=opening):
                    with self.assertRaises(placement.CgroupSetupFailure) as caught:
                        manager.create_controller(cpus=[0], memory_nodes=[0], memory_bytes=4096)
                self.assertEqual(caught.exception.unrecorded_path, str(root / "fixture" / "controller"))
                self.assertIs(caught.exception.owner, manager)
                self.assertEqual(caught.exception.records, [manager.parent_record()])
                self.assertTrue((root / "fixture" / "controller").is_dir())
            finally:
                manager._close_fds()

    @unittest.skipUnless(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "Linux dir-fd support required")
    def test_anchored_parent_rename_is_rejected_before_a_leaf_is_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            stat = root.stat()
            def attr(_fd, name, *, value=None):
                return "cpuset memory" if value is None and name == "cgroup.controllers" else None
            with patch.object(placement, "_cgroup_at", side_effect=attr):
                manager = placement.CgroupSlots(root, "fixture", root_identity=(stat.st_dev, stat.st_ino))
            moved = root / "moved"
            manager.parent.rename(moved)
            try:
                with self.assertRaises((OSError, ValueError)):
                    manager.create_controller(cpus=[0], memory_nodes=[0], memory_bytes=4096)
                self.assertFalse((moved / "controller").exists())
                self.assertEqual(manager.created[0][2], moved.stat().st_ino)
            finally:
                manager._close_fds()

    @unittest.skipUnless(os.name == "posix" and Path("/proc/self/fd").is_dir(), "Linux proc fd support required")
    def test_anchored_groups_reject_other_device_before_attribute_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            root_stat = root.stat()
            real_fstat = os.fstat
            calls = []
            def attr(fd, name, *, value=None):
                calls.append((os.readlink(f"/proc/self/fd/{fd}"), name, value))
                return "cpuset memory" if value is None and name == "cgroup.controllers" else None
            def other_parent(fd):
                value = real_fstat(fd)
                if os.readlink(f"/proc/self/fd/{fd}") == str(root / "fixture"):
                    return SimpleNamespace(st_dev=value.st_dev + 1, st_ino=value.st_ino)
                return value
            with patch.object(placement, "_cgroup_at", side_effect=attr), \
                 patch.object(placement.os, "fstat", side_effect=other_parent):
                with self.assertRaises(placement.CgroupSetupFailure) as caught:
                    placement.CgroupSlots(root, "fixture", root_identity=(root_stat.st_dev, root_stat.st_ino))
            self.assertEqual(caught.exception.unrecorded_path, str(root / "fixture"))
            self.assertFalse(any(path == str(root / "fixture") for path, _, _ in calls))

    @unittest.skipUnless(os.name == "posix" and Path("/proc/self/fd").is_dir(), "Linux proc fd support required")
    def test_anchored_leaf_other_device_is_preserved_before_attribute_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            root_stat = root.stat()
            real_fstat = os.fstat
            calls = []
            def attr(fd, name, *, value=None):
                calls.append((os.readlink(f"/proc/self/fd/{fd}"), name, value))
                return "cpuset memory" if value is None and name == "cgroup.controllers" else None
            with patch.object(placement, "_cgroup_at", side_effect=attr):
                manager = placement.CgroupSlots(root, "fixture", root_identity=(root_stat.st_dev, root_stat.st_ino))
            def other_leaf(fd):
                value = real_fstat(fd)
                if os.readlink(f"/proc/self/fd/{fd}") == str(root / "fixture" / "controller"):
                    return SimpleNamespace(st_dev=value.st_dev + 1, st_ino=value.st_ino)
                return value
            try:
                with patch.object(placement, "_cgroup_at", side_effect=attr), \
                     patch.object(placement.os, "fstat", side_effect=other_leaf):
                    with self.assertRaises(placement.CgroupSetupFailure) as caught:
                        manager.create_controller(cpus=[0], memory_nodes=[0], memory_bytes=4096)
                self.assertEqual(caught.exception.unrecorded_path, str(root / "fixture" / "controller"))
                self.assertIs(caught.exception.owner, manager)
                self.assertFalse(any(path == str(root / "fixture" / "controller") for path, _, _ in calls))
            finally:
                manager._close_fds()

    @unittest.skipUnless(hasattr(os, "sched_getaffinity"), "Linux execution port")
    def test_preexec_rechecks_owned_memory_max_before_entering_cgroup(self):
        # Fake files and affinity stand in for cgroupfs and scheduler operations.
        # No assertion here proves actual kernel cgroup behavior.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / "slot-000"
            path.mkdir()
            (path / "cpuset.cpus.effective").write_text("2-3\n")
            (path / "cpuset.mems.effective").write_text("1\n")
            (path / "cgroup.procs").write_text("untouched\n")
            memory_path = path / "memory.max"
            memory_path.write_text("4096\n")
            stat = path.stat()
            original = {"path": str(path), "device": stat.st_dev, "inode": stat.st_ino,
                        "cpus": [2, 3], "memory_nodes": [1], "memory_max": 4096}
            slot = {"cpus": [2, 3], "memory_nodes": [1], "policy": "inherit"}
            with patch.object(placement.os, "sched_getaffinity", return_value={2, 3}), \
                    patch.object(placement.os, "sched_setaffinity") as set_affinity, \
                    patch.object(placement, "allowed_nodes", return_value={1}), \
                    patch.object(placement, "memory_policy", return_value={"available": False}):
                result = placement.apply_slot(slot, cgroup=original)
                self.assertEqual(result["cgroup"]["memory_max"], 4096)
                self.assertEqual((path / "cgroup.procs").read_text(), str(os.getpid()))
                set_affinity.assert_called_once()

            for label, receipt, readback in (
                    ("changed", original, "8192\n"), ("unlimited", original, "max\n"),
                    ("invalid", original, "garbage\n"),
                    ("spoofed-receipt", {**original, "memory_max": 8192}, "4096\n"),
                    ("missing-receipt", {key: value for key, value in original.items() if key != "memory_max"}, "4096\n"),
                    ("boolean-receipt", {**original, "memory_max": True}, "4096\n"),
                    ("zero-receipt", {**original, "memory_max": 0}, "0\n"),
                    ("missing-file", original, None)):
                (path / "cgroup.procs").write_text("untouched\n")
                if readback is None:
                    memory_path.unlink(missing_ok=True)
                else:
                    memory_path.write_text(readback)
                with self.subTest(label=label), \
                        patch.object(placement.os, "sched_getaffinity", return_value={2, 3}), \
                        patch.object(placement.os, "sched_setaffinity") as set_affinity, \
                        patch.object(placement, "allowed_nodes", return_value={1}), \
                        patch.object(placement, "memory_policy", return_value={"available": False}):
                    with self.assertRaises((ValueError, OSError)):
                        placement.apply_slot(slot, cgroup=receipt)
                    set_affinity.assert_not_called()
                self.assertEqual((path / "cgroup.procs").read_text(), "untouched\n")

            # Even a valid receipt cannot authorize a different slot mask.
            memory_path.write_text("4096\n")
            (path / "cgroup.procs").write_text("untouched\n")
            with patch.object(placement.os, "sched_getaffinity", return_value={2, 3}), \
                    patch.object(placement.os, "sched_setaffinity") as set_affinity, \
                    patch.object(placement, "allowed_nodes", return_value={1}), \
                    patch.object(placement, "memory_policy", return_value={"available": False}):
                with self.assertRaisesRegex(ValueError, "effective masks changed"):
                    placement.apply_slot({**slot, "cpus": [2]}, cgroup=original)
                set_affinity.assert_not_called()
            self.assertEqual((path / "cgroup.procs").read_text(), "untouched\n")

    def test_slot_memory_budget_uses_both_actual_tt_extents_and_overhead(self):
        gib = 1 << 30
        p16 = placement.slot_memory_budget((12 * gib, 12 * gib), overhead_bytes=2 * gib,
                                           available_bytes=700 * gib, page_bytes=4096, node_available_bytes=80 * gib)
        self.assertEqual(p16["tt_bytes"], [12 * gib, 12 * gib])
        self.assertEqual(p16["memory_max"], 26 * gib)
        self.assertEqual(p16["supplied_node_available_bytes"], 80 * gib)
        self.assertTrue(p16["node_bound_provided"])
        self.assertIn("not a concurrent admission", p16["capacity_scope"])
        self.assertFalse(p16["availability_used_for_admission"])
        self.assertFalse(p16["physical_capacity_verified"])

        p192 = placement.slot_memory_budget((192 * gib, 192 * gib), overhead_bytes=2 * gib,
                                            available_bytes=700 * gib, page_bytes=4096)
        self.assertEqual(p192["memory_max"], 386 * gib)
        self.assertIsNone(p192["supplied_node_available_bytes"])
        self.assertFalse(p192["node_bound_provided"])
        self.assertIn("node observation unavailable", p192["capacity_scope"])

    def test_slot_memory_budget_rejects_unbounded_invalid_or_overflow_inputs(self):
        good = {"overhead_bytes": 4, "available_bytes": 100, "page_bytes": 2}
        for extents in ((), (1,), (1, 2, 3), (0, 1), (True, 1), (-1, 1), ("1", 1), None):
            with self.subTest(extents=extents), self.assertRaisesRegex(ValueError, "two positive"):
                placement.slot_memory_budget(extents, **good)
        for name, value in (("overhead_bytes", 0), ("overhead_bytes", True),
                            ("available_bytes", -(1 << 63)), ("available_bytes", True),
                            ("node_available_bytes", False), ("node_available_bytes", -1)):
            with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                placement.slot_memory_budget((1, 2), **{**good, name: value})
        with self.assertRaisesRegex(ValueError, "supported range"):
            placement.slot_memory_budget(((1 << 63) - 1, 1), overhead_bytes=1,
                                         available_bytes=(1 << 63) - 1, page_bytes=4096)

    def test_slot_memory_budget_records_low_or_absent_availability_without_rejecting(self):
        for host, node in ((89, None), (100, 89), (0, 0), (-1, 0), (None, None)):
            with self.subTest(host=host, node=node):
                result = placement.slot_memory_budget((40, 40), overhead_bytes=10,
                    available_bytes=host, node_available_bytes=node, page_bytes=2)
                self.assertEqual(result["memory_max"], 90)
                self.assertEqual(result["supplied_available_bytes"], host)
                self.assertEqual(result["supplied_node_available_bytes"], node)
                self.assertFalse(result["availability_used_for_admission"])
                self.assertFalse(result["physical_capacity_verified"])

    def test_slot_memory_budget_rounds_before_host_and_node_checks(self):
        result = placement.slot_memory_budget((40, 40), overhead_bytes=10, available_bytes=96,
                                              node_available_bytes=96, page_bytes=16)
        self.assertEqual(result["unrounded_memory_bytes"], 90)
        self.assertEqual(result["memory_max"], 96)
        self.assertEqual(result["page_rounding_bytes"], 6)
        self.assertEqual(result["page_bytes"], 16)
        below = placement.slot_memory_budget((40, 40), overhead_bytes=10, available_bytes=95,
                                             node_available_bytes=0, page_bytes=16)
        self.assertEqual(below["memory_max"], 96)
        self.assertFalse(below["availability_used_for_admission"])
        for page in (None, 0, -1, True, 3, "4096", 1 << 63):
            with self.subTest(page=page), self.assertRaisesRegex(ValueError, "power-of-two kernel page"):
                placement.slot_memory_budget((1, 1), overhead_bytes=1, available_bytes=100, page_bytes=page)
        with self.assertRaisesRegex(ValueError, "page-aligned memory extent"):
            placement.slot_memory_budget(((1 << 63) - 4, 1), overhead_bytes=1,
                                         available_bytes=(1 << 63) - 1, page_bytes=4096)

    def test_league_memory_admission_p16_uses_worst_distinct_pair_per_slot(self):
        gib = 1 << 30
        players = [{"id": name, "sha256": digit * 64, "tt_bytes": amount * gib}
                   for name, digit, amount in (("a", "a", 12), ("b", "b", 8), ("c", "c", 16))]
        slots = [{"id": f"slot-{index:03}", "memory_nodes": [0 if index < 6 else 1]}
                 for index in range(11)]
        result = placement.league_memory_admission(players, slots, profile="test-p16",
            host_available_bytes=700 * gib, node_available_bytes={0: 200 * gib, 1: 180 * gib},
            per_game_overhead_bytes=2 * gib, overhead_evidence_sha256="a" * 64,
            controller_reserve_bytes=4 * gib, page_bytes=4096)
        self.assertEqual([row["id"] for row in result["worst_two_artifacts"]], ["c", "a"])
        self.assertTrue(all(row["memory_max"] == 30 * gib for row in result["slots"]))
        self.assertEqual(result["required_bytes"], 334 * gib)
        self.assertEqual(result["node_check"]["required_bytes"], {0: 180 * gib, 1: 150 * gib})
        self.assertFalse(result["node_check"]["controller_distribution_verified"])
        self.assertFalse(result["runtime_admission_complete"])
        self.assertFalse(result["node_check"]["capacity_checked"])
        self.assertFalse(result["availability_used_for_admission"])
        self.assertFalse(result["physical_capacity_verified"])
        self.assertIn("no provenance, freshness, reservation", result["capacity_scope"])

    def test_league_memory_admission_keeps_p16_shape_validation_without_availability_gate(self):
        players = [{"id": "a", "sha256": "a" * 64, "tt_bytes": 12},
                   {"id": "b", "sha256": "b" * 64, "tt_bytes": 12}]
        slots = [{"id": f"slot-{index:03}", "memory_nodes": [0]} for index in range(11)]
        args = {"profile": "test-p16", "host_available_bytes": 500,
                "node_available_bytes": {0: 286}, "per_game_overhead_bytes": 2,
                "overhead_evidence_sha256": "c" * 64, "controller_reserve_bytes": 4, "page_bytes": 2}
        equal = placement.league_memory_admission(players, slots, **args)
        self.assertEqual(equal["required_bytes"], 290)
        for change in ({"host_available_bytes": 0}, {"host_available_bytes": -1},
                       {"host_available_bytes": None},
                       {"node_available_bytes": {0: 0}}, {"node_available_bytes": {1: 500}},
                       {"node_available_bytes": None}):
            with self.subTest(change=change):
                result = placement.league_memory_admission(players, slots, **{**args, **change})
                self.assertEqual(result["required_bytes"], 290)
                self.assertEqual(result["supplied_host_available_bytes"],
                                 change.get("host_available_bytes", args["host_available_bytes"]))
                self.assertFalse(result["availability_used_for_admission"])
                self.assertFalse(result["node_check"]["capacity_checked"])
        unavailable = placement.league_memory_admission(players, slots, **{**args,
            "node_available_bytes": {0: None, 1: 0}})
        self.assertEqual(unavailable["supplied_node_available_bytes"], {0: None, 1: 0})
        self.assertFalse(unavailable["node_check"]["observations_complete"])
        self.assertFalse(unavailable["physical_capacity_verified"])
        for change, message in (({"host_available_bytes": -(1 << 63)}, "bounded signed integer"),
                                ({"node_available_bytes": {0: -1}}, "observation must be nonnegative"),
                                ({"per_game_overhead_bytes": True}, "positive per-game"),
                                ({"controller_reserve_bytes": 0}, "controller reserve"),
                                ({"overhead_evidence_sha256": "unknown"}, "overhead evidence")):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, message):
                placement.league_memory_admission(players, slots, **{**args, **change})
        with self.assertRaisesRegex(ValueError, "eleven slots"):
            placement.league_memory_admission(players, slots[:-1], **args)
        duplicate = [*slots[:-1], slots[0]]
        with self.assertRaisesRegex(ValueError, "distinct slot identity"):
            placement.league_memory_admission(players, duplicate, **args)
        with self.assertRaisesRegex(ValueError, "distinct named artifact"):
            placement.league_memory_admission([players[0], players[0]], slots, **args)
        with self.assertRaisesRegex(ValueError, "exactly one NUMA"):
            placement.league_memory_admission(players, [{**slots[0], "memory_nodes": [0, 1]}, *slots[1:]],
                                              **{**args, "node_available_bytes": {0: 500, 1: 500}})

    def test_league_memory_admission_p192_uses_only_allowed_node_aggregate(self):
        gib = 1 << 30
        players = [{"id": "a", "sha256": "a" * 64, "tt_bytes": 192 * gib},
                   {"id": "b", "sha256": "b" * 64, "tt_bytes": 192 * gib}]
        slot = [{"id": "slot-000", "memory_nodes": [0, 1, 2]}]
        args = {"profile": "test-p192", "host_available_bytes": 700 * gib,
                "node_available_bytes": {0: 130 * gib, 1: 130 * gib, 2: 130 * gib, 3: 500 * gib},
                "per_game_overhead_bytes": 2 * gib, "overhead_evidence_sha256": "c" * 64,
                "controller_reserve_bytes": 4 * gib, "page_bytes": 4096}
        result = placement.league_memory_admission(players, slot, **args)
        self.assertEqual(result["required_bytes"], 390 * gib)
        self.assertEqual(result["node_check"]["supplied_aggregate_bytes"], 390 * gib)
        self.assertFalse(result["node_check"]["per_node_distribution_verified"])
        self.assertFalse(result["runtime_admission_complete"])
        below = placement.league_memory_admission(players, slot, **{**args,
            "node_available_bytes": {0: 130 * gib, 1: 130 * gib, 2: 129 * gib, 3: 500 * gib}})
        self.assertEqual(below["node_check"]["supplied_aggregate_bytes"], 389 * gib)
        self.assertFalse(below["node_check"]["capacity_checked"])
        missing = placement.league_memory_admission(players, slot, **{**args,
            "node_available_bytes": {0: 200 * gib, 1: 200 * gib}})
        self.assertIsNone(missing["node_check"]["supplied_aggregate_bytes"])
        self.assertFalse(missing["node_check"]["observations_complete"])
        unavailable = placement.league_memory_admission(players, slot, **{**args,
            "node_available_bytes": {0: None, 1: 0, 2: 200 * gib}})
        self.assertEqual(unavailable["supplied_node_available_bytes"], {0: None, 1: 0, 2: 200 * gib})
        self.assertIsNone(unavailable["node_check"]["supplied_aggregate_bytes"])
        self.assertFalse(unavailable["node_check"]["observations_complete"])
        self.assertFalse(unavailable["node_check"]["capacity_checked"])
        large_observation = placement.league_memory_admission(players, slot, **{**args,
            "node_available_bytes": {0: (1 << 63) - 1, 1: (1 << 63) - 1, 2: 0}})
        self.assertEqual(large_observation["node_check"]["supplied_aggregate_bytes"], (1 << 64) - 2)
        self.assertTrue(large_observation["node_check"]["observations_complete"])
        self.assertFalse(large_observation["node_check"]["capacity_checked"])

    def test_p192_rove_and_original_peer_tt_sizes_are_summed_without_free_ram_gate(self):
        gib = 1 << 30
        players = [{"id": "rove", "sha256": "a" * 64, "tt_bytes": 192 * gib},
                   {"id": "peer", "sha256": "b" * 64, "tt_bytes": 256 * gib}]
        slots = [{"id": "slot-000", "memory_nodes": [0, 1]}]
        result = placement.league_memory_admission(players, slots, profile="test-p192",
            host_available_bytes=0, node_available_bytes={0: 0, 1: 0},
            per_game_overhead_bytes=2 * gib, overhead_evidence_sha256="c" * 64,
            controller_reserve_bytes=4 * gib, page_bytes=4096)
        self.assertEqual(result["slots"][0]["memory_max"], 450 * gib)
        self.assertEqual(result["required_bytes"], 454 * gib)
        self.assertFalse(result["node_check"]["capacity_checked"])
        self.assertFalse(result["physical_capacity_verified"])
        self.assertFalse(result["runtime_admission_complete"])

    def test_mock_observation_flows_through_preflight_with_unavailable_node(self):
        # Synthetic observation exercises only the preflight/arithmetic wiring;
        # it does not authorize a run or establish live capacity.
        import run
        slot_record = {"id": "slot-000", "memory_nodes": [0, 1]}
        slots = [SimpleNamespace(to_record=lambda: dict(slot_record))]
        overhead = {"per_game_overhead_bytes": 2, "overhead_evidence_sha256": "c" * 64,
                    "controller_reserve_bytes": 4}
        players = [{"id": "a", "sha256": "a" * 64, "tt_bytes": 12},
                   {"id": "b", "sha256": "b" * 64, "tt_bytes": 12}]
        for host in (None, -1):
            def observe(records, root):
                return {"format": "rove4k-memory-capacity-observation-v1",
                        "slot_sha256": run.ledger.digest(records), "test_inputs": False,
                        "runtime_admission_complete": False, "host_available_bytes": host,
                        "node_available_bytes": {0: None, 1: 0}, "page_bytes": 2}
            with self.subTest(host=host):
                capacity, preflight = run.capture_league_preflight(slots, "/synthetic", overhead, observe)
                result = placement.league_memory_admission(players, [slot_record],
                                                            profile="test-p192", **preflight)
                self.assertEqual(capacity["node_available_bytes"], {0: None, 1: 0})
                self.assertEqual(result["supplied_host_available_bytes"], host)
                self.assertEqual(result["supplied_node_available_bytes"], {0: None, 1: 0})
                self.assertFalse(result["node_check"]["observations_complete"])
                self.assertFalse(result["runtime_admission_complete"])
                self.assertFalse(result["physical_capacity_verified"])

    def test_league_memory_admission_rejects_integer_overflow_and_invalid_nodes(self):
        players = [{"id": "a", "sha256": "a" * 64, "tt_bytes": 1},
                   {"id": "b", "sha256": "b" * 64, "tt_bytes": 1}]
        slots = [{"id": "slot-000", "memory_nodes": [0]}]
        args = {"profile": "test-p192", "host_available_bytes": (1 << 63) - 1,
                "node_available_bytes": {0: (1 << 63) - 1}, "per_game_overhead_bytes": 1,
                "overhead_evidence_sha256": "c" * 64, "controller_reserve_bytes": 1, "page_bytes": 2}
        with self.assertRaisesRegex(ValueError, "single-slot memory extent"):
            placement.league_memory_admission([{**players[0], "tt_bytes": (1 << 63) - 1}, players[1]], slots, **args)
        with self.assertRaisesRegex(ValueError, "concurrent memory extent"):
            placement.league_memory_admission(players, slots, **{**args, "controller_reserve_bytes": (1 << 63) - 1})
        with self.assertRaisesRegex(ValueError, "numeric NUMA node"):
            placement.league_memory_admission(players, slots, **{**args, "node_available_bytes": {True: 50}})
        with self.assertRaisesRegex(ValueError, "distinct slot identity"):
            placement.league_memory_admission(players, [{"id": "slot-000", "memory_nodes": [0, 0]}], **args)

    def test_league_memory_admission_aligns_every_slot_before_summing(self):
        players = [{"id": "a", "sha256": "a" * 64, "tt_bytes": 1},
                   {"id": "b", "sha256": "b" * 64, "tt_bytes": 1}]
        slots = [{"id": f"slot-{index:03}", "memory_nodes": [0]} for index in range(11)]
        args = {"profile": "test-p16", "host_available_bytes": 180,
                "node_available_bytes": {0: 176}, "per_game_overhead_bytes": 1,
                "overhead_evidence_sha256": "c" * 64, "controller_reserve_bytes": 4, "page_bytes": 16}
        result = placement.league_memory_admission(players, slots, **args)
        self.assertEqual(result["unrounded_per_slot_bytes"], 3)
        self.assertEqual(result["per_slot_page_rounding_bytes"], 13)
        self.assertEqual(result["required_bytes"], 180)
        self.assertTrue(all(row["memory_max"] == 16 for row in result["slots"]))
        below = placement.league_memory_admission(players, slots, **{**args,
            "host_available_bytes": 0, "node_available_bytes": {0: 0}})
        self.assertEqual(below["required_bytes"], 180)
        self.assertFalse(below["availability_used_for_admission"])
        for page in (False, 0, 6, -2):
            with self.subTest(page=page), self.assertRaisesRegex(ValueError, "power-of-two kernel page"):
                placement.league_memory_admission(players, slots, **{**args, "page_bytes": page})
        with self.assertRaisesRegex(ValueError, "page-aligned memory extent"):
            placement.league_memory_admission([{**players[0], "tt_bytes": (1 << 63) - 4}, players[1]],
                [{"id": "slot-000", "memory_nodes": [0]}], **{**args, "profile": "test-p192",
                "host_available_bytes": (1 << 63) - 1, "node_available_bytes": {0: (1 << 63) - 1},
                "page_bytes": 4096})

    @unittest.skipUnless(hasattr(os, "sched_getaffinity"), "actual Linux /proc port")
    def test_actual_two_image_observation_and_wrong_binding_rejection(self):
        command = """import subprocess,sys
children=[]
try:
    children=[subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(10)']) for _ in range(2)]
    print('ready',flush=True)
    sys.stdin.readline()
finally:
    for child in children:
        if child.poll() is None: child.terminate()
    for child in children: child.wait(timeout=3)
"""
        child = subprocess.Popen([sys.executable, "-B", "-c", command], start_new_session=True,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            self.assertTrue(select.select([child.stdout], [], [], 5)[0], "owned observer fixture never became ready")
            self.assertEqual(child.stdout.readline(), b"ready\n")
            native = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
            cpus = os.sched_getaffinity(0)
            observed = placement.observe_game_engines(child.pid, [native, native], cpus)
            self.assertEqual(len(observed["engines"]), 2)
            self.assertTrue(all(row["alive"] for row in observed["engines"]))
            self.assertTrue(all(row["native_sha256"] == native for row in observed["engines"]))
            with self.assertRaisesRegex(ValueError, "two qualified native images"):
                placement.observe_game_engines(child.pid, [native, "0" * 64], cpus)
            with self.assertRaisesRegex(ValueError, "escaped"):
                placement.observe_game_engines(child.pid, [native, native], set())
        finally:
            try:
                child.communicate(b"stop\n", timeout=5)
            except subprocess.TimeoutExpired:
                identity = placement._process_identity(child.pid)
                if identity["pgid"] == child.pid and identity["session"] == child.pid:
                    os.killpg(child.pid, signal.SIGKILL)
                child.communicate(timeout=5)
        self.assertEqual(child.returncode, 0)

    def test_resume_cleanup_uses_original_empty_identities_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            parent, child = root / "campaign-fixture", root / "campaign-fixture" / "slot-000"
            child.mkdir(parents=True)
            for path in (parent, child):
                (path / "cgroup.events").write_text("populated 0\nfrozen 0\n")
            record = lambda path: {"path": str(path), "device": path.stat().st_dev, "inode": path.stat().st_ino}
            records = [record(parent), record(child)]
            with patch.object(Path, "rmdir", autospec=True) as remove:
                outcomes = placement.cleanup_owned_groups(records, root=root)
            self.assertEqual([call.args[0] for call in remove.call_args_list], [child, parent])
            self.assertTrue(all(row.get("removed") for row in outcomes))
            (child / "cgroup.events").write_text("populated 1\n")
            with patch.object(Path, "rmdir", autospec=True) as remove:
                outcome = placement.cleanup_owned_groups([records[1]], root=root)[0]
            self.assertIn("contains tasks", outcome["error"])
            remove.assert_not_called()
            changed = {**records[1], "inode": records[1]["inode"] + 1}
            with patch.object(Path, "rmdir", autospec=True) as remove:
                outcome = placement.cleanup_owned_groups([changed], root=root)[0]
            self.assertIn("identity changed", outcome["error"])
            remove.assert_not_called()
            with self.assertRaisesRegex(ValueError, "dedicated root"):
                placement.cleanup_owned_groups([records[1]], root=root / "other")

    def test_resume_cleanup_is_idempotent_and_preserves_raced_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            parent = root / "campaign-fixture"
            parent.mkdir()
            stat = parent.stat()
            record = {"path": str(parent), "device": stat.st_dev, "inode": stat.st_ino}
            (parent / "cgroup.events").write_text("populated 0\n")
            with patch.object(Path, "rmdir", autospec=True, side_effect=OSError(16, "busy")):
                outcome = placement.cleanup_owned_groups([record], root=root)[0]
            self.assertIn("busy", outcome["error"])
            self.assertTrue(parent.exists())
            (parent / "cgroup.events").unlink()
            parent.rmdir()
            outcome = placement.cleanup_owned_groups([record], root=root)[0]
            self.assertTrue(outcome["already_absent"])

    @unittest.skipUnless(hasattr(os, "sched_getaffinity"), "Linux execution port")
    def test_actual_preexec_mask_survives_exec(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            cpu = min(os.sched_getaffinity(0))
            node = min(placement.allowed_nodes())
            slot = root / "slot.json"
            slot.write_text(json.dumps({"slot": {"cpus": [cpu], "memory_nodes": [node], "policy": "inherit"}}))
            observed = root / "observed.json"
            command = [sys.executable, "-B", str(Path(placement.__file__).resolve()), "--slot", str(slot),
                       "--record", str(observed), "--", sys.executable, "-B", "-c",
                       "import os,json; print(json.dumps(sorted(os.sched_getaffinity(0))))"]
            result = subprocess.run(command, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(json.loads(result.stdout), [cpu])
            record = json.loads(observed.read_text())
            self.assertEqual(record["requested_cpus"], [cpu])
            self.assertEqual(record["effective_cpus"], [cpu])
            self.assertIn("pre-exec", record["stage"])

    @unittest.skipUnless(hasattr(os, "sched_getaffinity"), "Linux execution port")
    def test_cli_passes_saved_node_envelope_only_for_original_owned_group(self):
        # Temporary files model cgroup attributes; this exercises the real CLI
        # and apply_slot path, not a kernel cgroup or authenticated snapshot.
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp).resolve()
            group = parent / "slot-000"
            group.mkdir()
            (parent / "cpuset.mems.effective").write_text("0-1\n")
            (group / "cpuset.cpus.effective").write_text("2-3\n")
            (group / "cpuset.mems.effective").write_text("1\n")
            (group / "memory.max").write_text("4096\n")
            (group / "cgroup.procs").write_text("x")
            st = group.stat()
            receipt = {"path": str(group), "device": st.st_dev, "inode": st.st_ino,
                       "cpus": [2, 3], "memory_nodes": [1], "memory_max": 4096}
            slot = {"cpus": [2, 3], "memory_nodes": [1], "policy": "inherit"}
            slot_path = parent / "slot.json"
            original_read = Path.read_text

            def read(path, *args, **kwargs):
                if str(path) == "/sys/devices/system/node/online":
                    return "0-1\n"
                if str(path) == "/sys/devices/system/cpu/online":
                    return "2-3\n"
                return original_read(path, *args, **kwargs)

            def run_case(name, nodes, *, succeeds):
                (group / "cgroup.procs").write_text("x")
                record = parent / (name + ".json")
                value = {"slot": slot, "cgroup": receipt, "saved_ancestor_cpus": [2, 3]}
                if nodes is not None:
                    value["saved_ancestor_nodes"] = nodes
                slot_path.write_text(json.dumps(value))
                command = ["placement.py", "--slot", str(slot_path), "--record", str(record),
                           "--", "/bin/true"]
                with patch.object(sys, "argv", command), \
                     patch.object(Path, "read_text", autospec=True, side_effect=read), \
                     patch.object(placement.os, "sched_getaffinity", return_value={2, 3}), \
                     patch.object(placement.os, "sched_setaffinity") as affinity, \
                     patch.object(placement, "allowed_nodes", side_effect=[{0}, {1}]), \
                     patch.object(placement, "memory_policy", return_value={"available": False}), \
                     patch.object(placement.os, "execvpe") as execute:
                    if succeeds:
                        placement.main()
                        affinity.assert_called_once_with(0, {2, 3})
                        execute.assert_called_once()
                        self.assertEqual(execute.call_args.args[:2], ("/bin/true", ["/bin/true"]))
                        data = json.loads(record.read_text())
                        self.assertEqual(data["saved_ancestor_nodes"], [0, 1])
                        self.assertEqual(data["effective_allowed_nodes"], [1])
                        self.assertEqual((group / "cgroup.procs").read_text(), str(os.getpid()))
                    else:
                        with self.assertRaises(ValueError):
                            placement.main()
                        self.assertFalse(record.exists())
                        self.assertEqual((group / "cgroup.procs").read_text(), "x")
                        affinity.assert_not_called()
                        execute.assert_not_called()

            run_case("missing", None, succeeds=False)
            run_case("unowned-node", [0], succeeds=False)
            run_case("valid", [0, 1], succeeds=True)

    @unittest.skipUnless(hasattr(os, "sched_getaffinity"), "Linux execution port")
    def test_failed_observation_does_not_claim_successful_set_fell_back(self):
        policy = [{"available": False}, {"available": False, "request_applied": True,
                                          "reason": "get_mempolicy rejected", "errno": 1}]
        with patch.object(placement.os, "sched_getaffinity", return_value={7}), \
                patch.object(placement.os, "sched_setaffinity"), \
                patch.object(placement, "allowed_nodes", return_value={0}), \
                patch.object(placement, "memory_policy", side_effect=policy):
            observed = placement.apply_slot({"cpus": [7], "memory_nodes": [0], "policy": "interleave"})
        self.assertIsNone(observed["fallback"])
        self.assertTrue(observed["observed_policy"]["request_applied"])
        self.assertFalse(observed["observed_policy"]["available"])

    @unittest.skipUnless(hasattr(os, "sched_getaffinity"), "Linux execution port")
    def test_no_unowned_mask_widening(self):
        with patch.object(placement.os, "sched_getaffinity", return_value={7}), \
                patch.object(placement, "allowed_nodes", return_value={0}):
            with self.assertRaisesRegex(ValueError, "widen"):
                placement.apply_slot({"cpus": [8], "memory_nodes": [0]})
            with self.assertRaisesRegex(ValueError, "owned cgroup"):
                placement.apply_slot({"cpus": [8], "memory_nodes": [0]}, saved_ancestor_cpus=[7, 8])

    @unittest.skipUnless(hasattr(os, "sched_getaffinity"), "Linux execution port")
    def test_owned_sibling_nodes_use_explicit_ancestor_envelope_and_live_readback(self):
        # Ordinary temporary files stand in for cgroupfs. This checks ordering
        # and refusal behavior, not a real kernel cpuset or memory reservation.
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp).resolve()
            group = parent / "slot-000"
            group.mkdir()
            (parent / "cpuset.mems.effective").write_text("0-1\n")
            (group / "cpuset.cpus.effective").write_text("2-3\n")
            (group / "cpuset.mems.effective").write_text("1\n")
            (group / "memory.max").write_text("4096\n")
            # The production code writes without O_TRUNC, as required for
            # cgroupfs. A one-byte sentinel avoids regular-file trailing bytes.
            (group / "cgroup.procs").write_text("x")
            st = group.stat()
            receipt = {"path": str(group), "device": st.st_dev, "inode": st.st_ino,
                       "cpus": [2, 3], "memory_nodes": [1], "memory_max": 4096}
            slot = {"cpus": [2, 3], "memory_nodes": [1], "policy": "inherit"}
            actual_read = Path.read_text
            actual_stat = os.stat

            def run_case(*, group_receipt=receipt, cpus=[2, 3], nodes=[0, 1],
                         parent_mems="0-1\n", online_mems="0-1\n", after_nodes={1},
                         changed_leaf_at_join=False, changed_parent_at_join=False,
                         expect_error=False, expect_moved=False):
                (parent / "cpuset.mems.effective").write_text(parent_mems)
                (group / "cgroup.procs").write_text("x")

                def read(path, *args, **kwargs):
                    if str(path) == "/sys/devices/system/node/online":
                        return online_mems
                    if str(path) == "/sys/devices/system/cpu/online":
                        return "2-3\n"
                    return actual_read(path, *args, **kwargs)

                def stat(path, *args, **kwargs):
                    result = actual_stat(path, *args, **kwargs)
                    leaf_at = (str(path) == group.name and kwargs.get("dir_fd") is not None)
                    parent_path = (str(path) == str(parent) and kwargs.get("follow_symlinks", True))
                    if (changed_leaf_at_join and leaf_at) or (changed_parent_at_join and parent_path):
                        return SimpleNamespace(st_dev=result.st_dev, st_ino=result.st_ino + 1)
                    return result

                with patch.object(Path, "read_text", autospec=True, side_effect=read), \
                     patch.object(placement.os, "stat", side_effect=stat), \
                     patch.object(placement.os, "sched_getaffinity", return_value={2, 3}), \
                     patch.object(placement.os, "sched_setaffinity") as affinity, \
                     patch.object(placement, "allowed_nodes", side_effect=[{0}, after_nodes]), \
                     patch.object(placement, "memory_policy", return_value={"available": False}):
                    if expect_error:
                        with self.assertRaises((ValueError, OSError)):
                            placement.apply_slot(slot, cgroup=group_receipt,
                                                 saved_ancestor_cpus=cpus,
                                                 saved_ancestor_nodes=nodes)
                    else:
                        result = placement.apply_slot(slot, cgroup=group_receipt,
                                                      saved_ancestor_cpus=cpus,
                                                      saved_ancestor_nodes=nodes)
                        self.assertEqual(result["original_allowed_nodes"], [0])
                        self.assertEqual(result["effective_allowed_nodes"], [1])
                        self.assertEqual(result["cgroup"]["inode"], st.st_ino)
                        affinity.assert_called_once()
                expected = str(os.getpid()) if expect_moved else "x"
                self.assertEqual((group / "cgroup.procs").read_text(), expected)

            # The current sibling is node 0; the real target receipt and its
            # parent permit node 1. Move first, then require target readback.
            run_case(expect_moved=True)
            for label, kwargs in (
                    ("parent-does-not-allow", {"parent_mems": "0\n"}),
                    ("node-not-online", {"online_mems": "0\n"}),
                    ("saved-envelope-too-wide", {"nodes": [0, 1, 2], "parent_mems": "0-1\n", "online_mems": "0-2\n"}),
                    ("saved-envelope-excludes-target", {"nodes": [0]}),
                    ("missing-cpu-envelope", {"cpus": None}),
                    ("missing-node-envelope", {"nodes": None}),
                    ("empty-node-envelope", {"nodes": []}),
                    ("node-list-negative", {"nodes": [-1, 1]}),
                    ("changed-group-inode", {"group_receipt": {**receipt, "inode": st.st_ino + 1}}),
                    ("changed-group-device", {"group_receipt": {**receipt, "device": st.st_dev + 1}}),
                    ("replaced-leaf-at-join", {"changed_leaf_at_join": True}),
                    ("replaced-parent-at-join", {"changed_parent_at_join": True}),
                    ("node-list-duplicate", {"nodes": [0, 1, 1]}),
                    ("node-list-boolean", {"nodes": [False, 1]})):
                with self.subTest(label=label):
                    run_case(**kwargs, expect_error=True)
            # A successful write to cgroup.procs is not a successful
            # placement if the observed nodes after the move still differ.
            run_case(after_nodes={0}, expect_error=True, expect_moved=True)

    @unittest.skipUnless(hasattr(os, "sched_getaffinity"), "Linux execution port")
    def test_ancestor_nodes_cannot_authorize_an_unowned_move(self):
        with patch.object(placement.os, "sched_getaffinity", return_value={2, 3}), \
             patch.object(placement, "allowed_nodes", return_value={0}), \
             patch.object(placement.os, "sched_setaffinity") as affinity:
            with self.assertRaises(ValueError):
                placement.apply_slot({"cpus": [2, 3], "memory_nodes": [1]},
                                     saved_ancestor_cpus=[2, 3], saved_ancestor_nodes=[0, 1])
            affinity.assert_not_called()


if __name__ == "__main__":
    unittest.main()
