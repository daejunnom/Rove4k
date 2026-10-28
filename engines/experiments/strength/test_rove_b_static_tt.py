"""Compile-only evidence tests; no engine or large allocation is executed."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rove_b_static_tt as subject


@unittest.skipUnless(sys.platform == "linux" and shutil.which("cc") and shutil.which("ld"), "Linux compiler required")
class StaticCandidateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "native").mkdir()
        self.cc = shutil.which("cc")
        ld = subprocess.check_output([self.cc, "-print-prog-name=ld"], text=True).strip()
        self.compiler_sha = self.hash(Path(self.cc).read_bytes())
        self.linker_sha = self.hash(Path(shutil.which(ld)).read_bytes())

    @staticmethod
    def hash(raw):
        return hashlib.sha256(raw).hexdigest()

    def make(self, bits, extra=b""):
        source = (f"#define qN ((size_t)1<<{bits})\n".encode() + b"""
#include <stddef.h>
#include <stdlib.h>
#include <stdatomic.h>
typedef struct { atomic_flag a; unsigned long h,v""" + extra + b"""; } zb;
zb*qq;
void f(unsigned long a){qq=aligned_alloc(4096,qN*sizeof*qq);zb*e=qq+(a&(qN-1));(void)e;}
int main(void){return 0;}
""")
        subprocess.run([self.cc, *subject.COMMAND[1:]], input=source, cwd=self.root, check=True)
        native = (self.root / "x").read_bytes()
        (self.root / "main.c").write_bytes(source)
        (self.root / "native/x").write_bytes(native)
        self.admitted = types.SimpleNamespace(family="B", profile_id={29: "test-p16", 33: "test-p192"}[bits],
            source="main.c", native="native/x", expected={
                "source_bytes": len(source), "source_sha256": self.hash(source),
                "native_bytes": len(native), "native_sha256": self.hash(native)}, resources={
                "tt_bits": bits, "tt_entries": 1 << bits, "tt_entry_bytes": 24,
                "tt_bytes": 24 << bits, "tt_mask": (1 << bits) - 1})

    def inspect(self):
        return subject.inspect(self.admitted, {"compiler": subject.COMMAND}, self.root,
                               self.compiler_sha, self.linker_sha)

    def test_both_profile_contracts_compile_without_running(self):
        for bits in (29, 33):
            with self.subTest(bits=bits):
                self.make(bits)
                evidence = self.inspect()
                self.assertEqual(evidence["candidate_tt_bytes"], 24 << bits)
                self.assertFalse(evidence["live_pointer_observed"])
                self.assertFalse(evidence["runtime_qualified"])

    def test_rejects_native_with_refreshed_pin_but_different_bytes(self):
        self.make(29)
        path = self.root / "native/x"
        changed = path.read_bytes() + b"x"
        path.write_bytes(changed)
        self.admitted.expected.update(native_bytes=len(changed), native_sha256=self.hash(changed))
        with self.assertRaisesRegex(ValueError, "compiler output differs"):
            self.inspect()

    def test_rejects_resource_mismatch_and_changed_compiler(self):
        self.make(29)
        self.admitted.resources["tt_bits"] = 33
        with self.assertRaisesRegex(ValueError, "resources differ"):
            self.inspect()
        self.admitted.resources["tt_bits"] = 29
        self.compiler_sha = "0" * 64
        with self.assertRaisesRegex(ValueError, "bytes differ"):
            self.inspect()

    def test_entry_width_is_checked_by_compiler(self):
        self.make(29, b",z")
        with self.assertRaisesRegex(ValueError, "source compile failed"):
            self.inspect()


if __name__ == "__main__":
    unittest.main()
