"""Small-file POSIX boundary tests; no compiler or engine is executed."""
from __future__ import annotations

import importlib.util
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("rove4k_production_input", HERE / "production_input.py")
INPUT = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = INPUT
spec.loader.exec_module(INPUT)


@unittest.skipUnless(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "POSIX fd-relative reader required")
class ProductionInputBoundaries(unittest.TestCase):
    def run_bounded_reader(self, action):
        """A regression that FIFO-blocks is killed through its original process handle."""
        context = multiprocessing.get_context("fork")
        received, sent = context.Pipe(duplex=False)
        def worker():
            received.close()
            try:
                sent.send(("returned", action()))
            except BaseException as error:
                sent.send(("rejected", type(error).__name__, str(error)))
            finally:
                sent.close()
        process = context.Process(target=worker)
        process.start()
        sent.close()
        try:
            process.join(2)
            if process.is_alive():
                process.terminate()
                process.join(1)
                if process.is_alive():
                    process.kill()
                    process.join(1)
                self.fail("target evidence read blocked beyond its original bounded process lifetime")
            self.assertEqual(process.exitcode, 0)
            self.assertTrue(received.poll(.5), "bounded reader did not return a result")
            return received.recv()
        finally:
            if process.is_alive():
                process.kill()
                process.join(1)
            received.close()
            process.close()

    def test_ordinary_byte_bound_empty_and_explicit_installed_hardlink_policy(self):
        with tempfile.TemporaryDirectory(prefix="rove-target-file-bounds-") as temporary:
            root = Path(temporary)
            path = root / "evidence.json"
            path.write_bytes(b"source")
            self.assertEqual(INPUT.read_regular(path, limit=6), b"source")
            with self.assertRaisesRegex(ValueError, "bounded ordinary"):
                INPUT.read_regular(path, limit=5)
            alias = root / "hardlink.json"
            os.link(path, alias)
            with self.assertRaisesRegex(ValueError, "bounded ordinary"):
                INPUT.read_regular(path, limit=1 << 20)
            self.assertEqual(INPUT.read_regular(path, limit=6, allow_hardlinks=True), b"source")
            alias.unlink()
            path.write_bytes(b"")
            self.assertEqual(INPUT.read_regular(path, limit=0), b"")

    def test_leaf_FIFO_swap_is_nonblocking_and_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rove-target-fifo-race-") as temporary:
            root = Path(temporary)
            path = root / "evidence.json"
            path.write_bytes(b"original")
            def action():
                original_open = INPUT.os.open
                changed = False
                def swapping_open(name, flags, *args, **kwargs):
                    nonlocal changed
                    if name == path.name and kwargs.get("dir_fd") is not None and not changed:
                        changed = True
                        path.rename(root / "held.json")
                        os.mkfifo(path)
                    return original_open(name, flags, *args, **kwargs)
                try:
                    with patch.object(INPUT.os, "open", side_effect=swapping_open):
                        return INPUT.read_regular(path, limit=1 << 20)
                except (ValueError, OSError):
                    if changed:
                        raise RuntimeError("swap-exercised-and-rejected")
                    raise
            started = time.monotonic()
            result = self.run_bounded_reader(action)
            self.assertEqual(result, ("rejected", "RuntimeError", "swap-exercised-and-rejected"))
            self.assertLess(time.monotonic() - started, 2)

    def test_ancestor_swap_cannot_follow_foreign_tree_before_or_after_parent_open(self):
        for timing in ("before-parent-open", "after-parent-open"):
            with self.subTest(timing=timing), tempfile.TemporaryDirectory(prefix="rove-target-ancestor-race-") as temporary:
                root = Path(temporary)
                owned, foreign = root / "owned", root / "foreign"
                owned.mkdir()
                foreign.mkdir()
                path = owned / "evidence.json"
                path.write_bytes(b"original")
                (foreign / path.name).write_bytes(b"foreign")
                def action():
                    original_open = INPUT.os.open
                    changed = False
                    def swapping_open(name, flags, *args, **kwargs):
                        nonlocal changed
                        expected = owned.name if timing == "before-parent-open" else path.name
                        if name == expected and kwargs.get("dir_fd") is not None and not changed:
                            changed = True
                            owned.rename(root / "held")
                            owned.symlink_to(foreign, target_is_directory=True)
                        return original_open(name, flags, *args, **kwargs)
                    try:
                        with patch.object(INPUT.os, "open", side_effect=swapping_open):
                            return INPUT.read_regular(path, limit=1 << 20)
                    except (ValueError, OSError):
                        if changed:
                            raise RuntimeError("swap-exercised-and-rejected")
                        raise
                result = self.run_bounded_reader(action)
                self.assertEqual(result, ("rejected", "RuntimeError", "swap-exercised-and-rejected"))

    def test_same_inode_rewrite_during_bounded_read_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rove-target-rewrite-race-") as temporary:
            path = Path(temporary) / "evidence.json"
            path.write_bytes(b"a" * 100)
            def action():
                original_read = INPUT.os.read
                changed = False
                def rewriting_read(descriptor, size):
                    nonlocal changed
                    data = original_read(descriptor, size)
                    if not changed:
                        changed = True
                        path.write_bytes(b"b" * 100)
                        stamp = path.stat()
                        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1000000000))
                    return data
                with patch.object(INPUT.os, "read", side_effect=rewriting_read):
                    return INPUT.read_regular(path, limit=1 << 20)
            result = self.run_bounded_reader(action)
            self.assertEqual(result[0], "rejected")

    def test_anchored_scan_expected_identity_is_checked(self):
        with tempfile.TemporaryDirectory(prefix="rove-input-scan-") as temporary:
            root = Path(temporary)
            path = root / "input"
            path.write_bytes(b"old")
            expected = path.stat()
            parent = INPUT.open_directory(root)
            try:
                self.assertEqual(INPUT.read_regular_at(parent, path.name, limit=3, expected=expected), b"old")
                path.write_bytes(b"newer")
                with self.assertRaisesRegex(ValueError, "directory scan"):
                    INPUT.read_regular_at(parent, path.name, limit=8, expected=expected)
            finally:
                os.close(parent)

    def test_leaf_and_ancestor_links_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rove-input-links-") as temporary:
            root = Path(temporary)
            real = root / "real"
            real.mkdir()
            path = real / "input"
            path.write_bytes(b"source")
            (root / "link").symlink_to(real, target_is_directory=True)
            (root / "leaf").symlink_to(path)
            for linked in (root / "link/input", root / "leaf"):
                with self.subTest(path=linked), self.assertRaises((OSError, ValueError)):
                    INPUT.read_regular(linked, limit=10)

    def test_source_identity_and_canonical_module_are_bound(self):
        data = INPUT.source_identity()
        self.assertIn(b"def read_regular(", data)
        self.assertIs(INPUT.cached_module(), INPUT)
        with patch.object(INPUT, "_EXECUTING_CODE", compile("pass", INPUT.__file__, "exec")):
            with self.assertRaisesRegex(ValueError, "executing code"):
                INPUT.source_identity()
        with patch.dict(sys.modules, {INPUT.MODULE_NAME: SimpleNamespace(__file__=str(HERE / "other.py"), _EXECUTING_CODE=None)}):
            with self.assertRaisesRegex(ValueError, "canonical"):
                INPUT.cached_module()

    def test_relative_negative_and_nonboolean_policy_are_rejected(self):
        with self.assertRaises(ValueError):
            INPUT.read_regular(Path("relative"), limit=4)
        with tempfile.TemporaryDirectory(prefix="rove-input-invalid-") as temporary:
            path = Path(temporary) / "input"
            path.write_bytes(b"x")
            for kwargs in ({"limit": -1}, {"limit": True}, {"limit": 4, "allow_hardlinks": 1}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    INPUT.read_regular(path, **kwargs)


if __name__ == "__main__":
    unittest.main()
