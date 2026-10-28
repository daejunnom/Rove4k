"""Offline tests for the reversible c4ke slider-call source candidate."""
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from . import peer_c4ke_slider_loop as candidate
except ImportError:
    import peer_c4ke_slider_loop as candidate


class SliderTransformTests(unittest.TestCase):
    def fixture(self):
        value = {name: b"unrelated source\r\n" for name in candidate.SOURCE_FILES}
        value["src/board.cpp"] = b"before\r\n" + candidate.BEFORE + b"\r\nafter\r\n"
        value["src/chess.cpp"] = b"#define BISHOP 2\r\n#define ROOK 3\r\n#define QUEEN 4\r\n"
        return value

    def test_pinned_source_contract_and_full_inverse(self):
        self.assertEqual(candidate.peers.SOURCE_BLOBS["c4ke"]["src/board.cpp"],
                         "bc78737f92158f95b1c8bd2204793b3c994acb51")
        self.assertEqual(candidate.peers.SOURCE_BLOBS["c4ke"]["src/chess.cpp"],
                         "59377f6afd07739bff3ececa7a588a5f60bd7ff7")
        original = self.fixture()
        with patch.object(candidate.peers, "verify_blob") as verified:
            after, receipt = candidate.transform(original)
            self.assertEqual(verified.call_count, 5)
            self.assertEqual(candidate.restore(after, receipt), original)
            changed = dict(after)
            changed["src/board.cpp"] += b"tamper"
            with self.assertRaises(ValueError):
                candidate.restore(changed, receipt)

    def test_constant_and_collision_contracts(self):
        original = self.fixture()
        with patch.object(candidate.peers, "verify_blob"):
            for bad in (b"#define BISHOP 3\r\n#define ROOK 2\r\n#define QUEEN 4\r\n",
                        b"#define BISHOP 2\r\n#define ROOK 4\r\n#define QUEEN 3\r\n"):
                sources = dict(original, **{"src/chess.cpp": bad})
                with self.assertRaisesRegex(ValueError, "constants differ"):
                    candidate.transform(sources)
            for path in candidate.SOURCE_FILES:
                sources = dict(original)
                sources[path] += candidate.LOOP_NAME
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, "already exists"):
                    candidate.transform(sources)
            sources = dict(original)
            sources["src/board.cpp"] += candidate.BEFORE
            with self.assertRaisesRegex(ValueError, "exactly once"):
                candidate.transform(sources)

    def test_ordered_call_arguments_for_random_masks(self):
        rng = random.Random(98118)
        for _ in range(100000):
            pieces = [rng.getrandbits(64) for _ in range(6)]
            colors = [rng.getrandbits(64) for _ in range(2)]
            side, targets, occupied = rng.randrange(2), rng.getrandbits(64), rng.getrandbits(64)
            original = [(targets, occupied, (pieces[2] | pieces[4]) & colors[side], 2),
                        (targets, occupied, (pieces[3] | pieces[4]) & colors[side], 3)]
            transformed = [(targets, occupied, (pieces[k] | pieces[4]) & colors[side], k)
                           for k in range(2, 4)]
            self.assertEqual(original, transformed)

    @unittest.skipUnless(shutil.which("c++"), "C++ compiler required for the synthetic move list")
    def test_compiled_move_list_and_call_order(self):
        # This models add_moves' iteration and the attack input deterministically;
        # it does not claim full chess legality or real minifier equivalence.
        original = candidate.BEFORE.decode().replace("\r\n", "\n")
        transformed = candidate.AFTER.decode().replace("\r\n", "\n")
        source = r'''
#include <cstdint>
#include <cstring>
#include <random>
using u64=uint64_t; using i16=int16_t; using i32=int;
enum { BISHOP=2, ROOK=3, QUEEN=4 };
struct Board {
 u64 pieces[6], colors[2]; i32 stm; int calls[2], nc;
 void add_moves(i16*& list,u64 targets,u64 occupied,u64 mask,i32 type) {
  calls[nc++]=type;
  while(mask) { int from=__builtin_ctzll(mask); mask&=mask-1;
   u64 attacks=((u64(1) << ((from+type)%64)) ^ (occupied >> (type+1))) & targets;
   while(attacks) { int to=__builtin_ctzll(attacks); attacks&=attacks-1; *list++=i16(from|to<<6); }
  }
 }
 int old_run(i16 *buf,u64 targets,u64 occupied) { i16* list=buf; nc=0; OLD return int(list-buf); }
 int new_run(i16 *buf,u64 targets,u64 occupied) { i16* list=buf; nc=0; NEW return int(list-buf); }
};
int main() {
 std::mt19937_64 r(98118);
 for(int n=0;n<50000;n++) {
  Board a{},b{}; for(int j=0;j<6;j++)a.pieces[j]=r();
  a.colors[0]=r();a.colors[1]=r();a.stm=int(r()&1);b=a;
  u64 t=r(),o=r();i16 x[8192]{},y[8192]{};
  int nx=a.old_run(x,t,o),ny=b.new_run(y,t,o);
  if(nx!=ny||a.nc!=2||b.nc!=2||a.calls[0]!=b.calls[0]||a.calls[1]!=b.calls[1]||
     std::memcmp(x,y,nx*sizeof(i16)))return 1;
 } return 0;
}
'''.replace("OLD", original).replace("NEW", transformed)
        with tempfile.TemporaryDirectory(prefix="rove-c4ke-slider-") as directory:
            src, exe = Path(directory) / "test.cpp", Path(directory) / "test"
            src.write_text(source, encoding="utf-8")
            subprocess.run([shutil.which("c++"), "-std=c++17", "-O1", str(src), "-o", str(exe)],
                           check=True, capture_output=True, timeout=30)
            subprocess.run([str(exe)], check=True, capture_output=True, timeout=30)


if __name__ == "__main__":
    unittest.main()
