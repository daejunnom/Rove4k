"""B candidate pointer observer: owned Linux child and strict failure tests."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    from . import rove_b_tt_observe as observe, placement
except ImportError:
    import rove_b_tt_observe as observe
    import placement

_SOURCE = r'''#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
typedef struct { long long a[3]; } Entry;
Entry *qq;
int main(void) {
    qq = aligned_alloc(4096, 24 * 4096);
    if (!qq) return 2;
    qq[0].a[0] = 7; qq[4095].a[0] = 9;
    puts("READY"); fflush(stdout);
    char c; return read(0, &c, 1) == 1 ? 0 : 3;
}
'''


@unittest.skipUnless(sys.platform == "linux" and shutil.which("cc"), "Linux and C compiler required")
class OwnedPointerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rove-b-pointer-test-")
        self.root = Path(self.temp.name)
        self.image = self.root / "engine"
        subprocess.run(["cc", "-std=c11", "-Os", "-pthread", "-x", "c", "-", "-o", str(self.image)],
                       input=_SOURCE.encode(), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self.native_sha = hashlib.sha256(self.image.read_bytes()).hexdigest()
        self.process = subprocess.Popen([str(self.image)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, start_new_session=True)
        self.addCleanup(self.reap)
        self.assertEqual(self.process.stdout.readline(), b"READY\n")
        self.owned = SimpleNamespace(process=self.process, exited=lambda: self.process.poll() is not None)
        self.identity = placement._process_identity(self.process.pid)
        self.cpu = min(os.sched_getaffinity(0))
        status = Path(f"/proc/{self.process.pid}/status").read_text()
        nodes = next(row.split(":", 1)[1].strip() for row in status.splitlines() if row.startswith("Mems_allowed_list:"))
        self.nodes = sorted(placement.parse_list(nodes))
        group = self.root / "group"
        group.mkdir()
        (group / "cpuset.cpus.effective").write_text(str(self.cpu))
        (group / "cpuset.mems.effective").write_text(nodes)
        (group / "memory.max").write_text("1073741824")
        (group / "cgroup.procs").write_text(str(self.process.pid) + "\n")
        info = group.stat()
        self.group = {"path": str(group), "device": info.st_dev, "inode": info.st_ino,
                      "cpus": [self.cpu], "memory_nodes": self.nodes, "memory_max": 1 << 30}
        # The fixture exercises a real owned child but does not own a delegated
        # kernel cgroup; only this mount check is replaced for the test.
        self.mount = patch.object(observe, "_require_kernel_group")
        self.mount.start()
        self.addCleanup(self.mount.stop)
        self.profile = patch.dict(observe._PROFILE_TT_BYTES, {"test-p16": 24 * 4096})
        self.profile.start()
        self.addCleanup(self.profile.stop)

    def reap(self):
        if self.process.poll() is None:
            self.process.stdin.write(b"x")
            self.process.stdin.flush()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        for pipe in (self.process.stdin, self.process.stdout, self.process.stderr):
            pipe.close()
        self.temp.cleanup()

    def call(self, **kwargs):
        args = {"native_sha256": self.native_sha, "expected_identity": self.identity, "cgroup": self.group,
                "profile": "test-p16", "allowed_nodes": self.nodes, "symbol": "qq"}
        args.update(kwargs)
        return observe.observe_owned_b(self.owned, **args)

    def test_live_child_symbol_pointer_and_mapping_are_observed_without_qualification(self):
        result = self.call()
        self.assertGreater(result["pointer"], 0)
        self.assertEqual(result["declared_entry_bytes"], 24)
        self.assertEqual(result["declared_range_bytes"], 24 * 4096)
        self.assertTrue(result["numa"]["all_mapping_starts_observed"])
        self.assertFalse(any(result["claims"].values()))
        self.assertEqual(result["owner"], self.identity)

    def test_live_image_hash_and_identity_are_enforced(self):
        with self.assertRaisesRegex(ValueError, "native image differs"):
            self.call(native_sha256="0" * 64)
        changed = dict(self.identity, start_ticks=self.identity["start_ticks"] + 1)
        with self.assertRaisesRegex(ValueError, "identity changed"):
            self.call(expected_identity=changed)

    def test_symbol_and_cgroup_membership_are_enforced(self):
        with self.assertRaisesRegex(ValueError, "unique ELF object symbol"):
            self.call(symbol="not_the_symbol")
        (Path(self.group["path"]) / "cgroup.procs").write_text("999999\n")
        with self.assertRaisesRegex(ValueError, "left its cgroup"):
            self.call()

    def test_pointer_read_permission_is_observation_unavailable(self):
        with patch.object(observe.os, "pread", side_effect=PermissionError("denied")):
            with self.assertRaisesRegex(observe.ObservationUnavailable, "process pointer"):
                self.call()

    def test_pointer_open_permission_is_observation_unavailable(self):
        real = observe.os.open
        mem = f"/proc/{self.process.pid}/mem"
        def guarded(path, flags, *args, **kwargs):
            if str(path) == mem:
                raise PermissionError(13, "denied", str(path))
            return real(path, flags, *args, **kwargs)
        with patch.object(observe.os, "open", side_effect=guarded):
            with self.assertRaisesRegex(observe.ObservationUnavailable, "process pointer"):
                self.call()

    def test_only_numa_file_denial_is_observation_unavailable(self):
        real = observe.rove_vma_observer._read
        def denied(which):
            def read(path, limit):
                if path.name == which:
                    raise PermissionError(13, "denied", str(path))
                return real(path, limit)
            return read
        with patch.object(observe.rove_vma_observer, "_read", side_effect=denied("numa_maps")):
            with self.assertRaisesRegex(observe.ObservationUnavailable, "NUMA mappings"):
                self.call()
        with patch.object(observe.rove_vma_observer, "_read", side_effect=denied("maps")):
            with self.assertRaises(PermissionError):
                self.call()

    def test_image_and_cgroup_denials_remain_hard_errors(self):
        with patch.object(observe, "_image", side_effect=PermissionError("denied image")):
            with self.assertRaises(PermissionError):
                self.call()
        with patch.object(observe.placement, "verify_cgroup_live", side_effect=PermissionError("denied cgroup")):
            with self.assertRaises(PermissionError):
                self.call()

    def test_pointer_and_image_identity_changes_remain_integrity_errors(self):
        real = observe._candidate_pointer
        count = 0
        def change(*args):
            nonlocal count
            count += 1
            result = real(*args)
            if count == 2:
                result["pointer"] += 4096
            return result
        with patch.object(observe, "_candidate_pointer", side_effect=change):
            with self.assertRaisesRegex(ValueError, "changed during observation"):
                self.call()

    def test_symbol_must_belong_to_an_allocated_writable_section(self):
        original = self.image.read_bytes()
        elf = observe.peer_runtime.Elf64(original)
        patched = bytearray(original)
        for table in elf.sections:
            if table[1] != 2:
                continue
            strings = elf.segment(elf.sections[table[6]][4], elf.sections[table[6]][5])
            for at in range(table[4], table[4] + table[5], table[9]):
                item = elf.unpack("IBBHQQ", at)
                if elf.string(strings, item[0]) == "qq" and item[1] & 15 == 1:
                    struct.pack_into("<H", patched, at + 6, 0xfff1)  # SHN_ABS
                    with self.assertRaisesRegex(ValueError, "special-section"):
                        observe._symbol_value(observe.peer_runtime.Elf64(bytes(patched)), "qq")
                    return
        self.fail("fixture does not expose its pointer symbol")

    def test_observation_detects_native_identity_change(self):
        real = observe._image
        count = 0
        def different(*args):
            nonlocal count
            count += 1
            data, identity = real(*args)
            return (data, identity) if count == 1 else (data, (identity[0], identity[1] + 1, identity[2]))
        with patch.object(observe, "_image", side_effect=different):
            with self.assertRaisesRegex(ValueError, "changed during observation"):
                self.call()

    def test_profile_and_node_claims_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "profile"):
            self.call(profile="test-p28")
        with self.assertRaisesRegex(ValueError, "allowed NUMA nodes"):
            self.call(allowed_nodes=[])
        with self.assertRaisesRegex(ValueError, "allowed nodes differ"):
            self.call(allowed_nodes=[max(self.nodes) + 1])

    def test_plain_directory_is_not_a_kernel_cgroup(self):
        self.mount.stop()
        with self.assertRaisesRegex(ValueError, "visible cgroup2 mount"):
            self.call()


if __name__ == "__main__":
    unittest.main()
