"""Tests for the isolated c4ke bitboard pop experiment."""
import copy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from . import peer_c4ke_pop_lsb as candidate, peers
except ImportError:
    import peer_c4ke_pop_lsb as candidate
    import peers


class PopTest(unittest.TestCase):
    def fixture(self):
        result = {path: b"unrelated\r\n" for path in candidate.PATHS}
        result["src/chess.cpp"] = b"".join(candidate.DEFINITIONS)
        result["src/board.cpp"] = b"\r\n".join(
            [candidate.ANCHOR, *(before for _, before, _ in candidate.SITES)])
        return result

    def pins(self, sources):
        return mock.patch.dict(peers.SOURCE_BLOBS["c4ke"],
                               {path: peers.git_blob(data) for path, data in sources.items()})

    def test_inverse_and_tampering(self):
        original = self.fixture()
        with self.pins(original):
            after, receipt = candidate.transform(original)
            self.assertEqual(candidate.restore(after, receipt), original)
            for path in candidate.PATHS:
                changed = dict(after)
                changed[path] += b"tamper"
                with self.subTest(path=path), self.assertRaises(ValueError):
                    candidate.restore(changed, receipt)
            forged = copy.deepcopy(receipt)
            forged["files"]["src/board.cpp"]["edits"][0]["role"] = "forged"
            with self.assertRaises(ValueError):
                candidate.restore(after, forged)

    def test_reject_collision_context_and_definitions(self):
        original = self.fixture()
        with self.assertRaises(ValueError):
            candidate.transform({})
        for path in candidate.PATHS:
            for name in candidate.NAMES:
                bad = dict(original)
                bad[path] += name
                with self.subTest(path=path, name=name), self.pins(bad), self.assertRaisesRegex(ValueError, "name"):
                    candidate.transform(bad)
        for _, before, _ in candidate.SITES:
            for replacement in (b"altered guard", before + before):
                bad = dict(original)
                bad["src/board.cpp"] = bad["src/board.cpp"].replace(before, replacement, 1)
                with self.subTest(site=before, duplicate=replacement != b"altered guard"), self.pins(bad), self.assertRaisesRegex(ValueError, "context"):
                    candidate.transform(bad)
        for definition in candidate.DEFINITIONS:
            bad = dict(original)
            bad["src/chess.cpp"] = bad["src/chess.cpp"].replace(definition, b"changed", 1)
            with self.pins(bad), self.assertRaisesRegex(ValueError, "definitions"):
                candidate.transform(bad)

    @unittest.skipUnless(shutil.which("c++"), "C++ compiler required")
    def test_real_fragments_preserve_order_and_masks(self):
        functions = []
        for index, (_, before, after) in enumerate(candidate.SITES):
            variable = ("to", "from", "to", "square")[index]
            bitboard = ("targets", "mask", "attacks", "mask")[index]
            for version, fragment in (("old", before), ("new", after)):
                text = fragment.decode().replace("\r\n", "\n")
                functions.append(f"void {version}{index}(u64 bits, Result& r) {{ u64 {bitboard}=bits;\n"
                                 f"{text}\n r.squares[r.n]={variable}; r.remaining[r.n++]={bitboard}; }} }}")
        source = r'''
#include <bit>
#include <cstdint>
#include <cstring>
#include <random>
using i32=int;using u64=uint64_t;
#define LSB std::countr_zero
struct Result { int n=0; int squares[64]{};u64 remaining[64]{}; };
HELPER
FUNCTIONS
using Run=void(*)(u64,Result&);
int main() {
 Run old[]={old0,old1,old2,old3}, now[]={new0,new1,new2,new3};
 std::mt19937_64 rng(918231);
 for(int site=0;site<4;site++) for(int n=0;n<10000;n++) {
  u64 bits=n==0?0:n==1?~0ull:n<66?(1ull<<(n-2)):rng();
  Result a,b;old[site](bits,a);now[site](bits,b);
  if(a.n!=b.n || std::memcmp(a.squares,b.squares,sizeof(a.squares)) ||
    std::memcmp(a.remaining,b.remaining,sizeof(a.remaining)))return 1;
  u64 expected=bits;
  for(int i=0;i<a.n;i++) {
   if(!expected || a.squares[i]!=int(std::countr_zero(expected)))return 2;
   expected &= expected-1;
   if(a.remaining[i]!=expected)return 3;
  }
  if(expected)return 4;
 }
}'''.replace("HELPER", candidate.HELPER.decode()).replace("FUNCTIONS", "\n".join(functions))
        with tempfile.TemporaryDirectory(prefix="c4ke-pop-fixture-") as directory:
            root = Path(directory)
            src, exe = root / "test.cpp", root / "test"
            src.write_text(source, encoding="ascii")
            subprocess.run([shutil.which("c++"), "-std=c++20", "-O2", str(src), "-o", str(exe)],
                           check=True, capture_output=True, timeout=60)
            subprocess.run([str(exe)], check=True, capture_output=True, timeout=30)


if __name__ == "__main__":
    unittest.main()
