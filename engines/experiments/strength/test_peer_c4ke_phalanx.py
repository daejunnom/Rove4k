import copy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from . import peer_c4ke_phalanx as phalanx, peers
except ImportError:
    import peer_c4ke_phalanx as phalanx
    import peers


class PhalanxTest(unittest.TestCase):
    def sources(self):
        sources = {path: b"fixture\r\n" for path in phalanx.PATHS}
        sources["src/chess.cpp"] = b"".join(phalanx._DEFINITIONS)
        sources["src/board.cpp"] = phalanx._START + b"\r\nfixture loop\r\n" + phalanx._BEFORE
        return sources

    def pins(self, sources):
        return mock.patch.dict(peers.SOURCE_BLOBS["c4ke"],
                               {path: peers.git_blob(data) for path, data in sources.items()})

    def context(self, sources):
        board = sources["src/board.cpp"]
        return mock.patch.object(phalanx, "_CONTEXT_SHA256", peers.sha(board))

    def test_inverse_and_reject_tampering(self):
        sources = self.sources()
        with self.pins(sources), self.context(sources):
            output, receipt = phalanx.transform(phalanx.VARIANT, sources)
            self.assertEqual(phalanx.restore(output, receipt), sources)
            self.assertEqual(len(output["src/board.cpp"]), len(sources["src/board.cpp"]) - 11)
            self.assertEqual(output["src/board.cpp"].count(phalanx._AFTER), 1)
            changed = dict(output)
            changed["src/board.cpp"] += b"x"
            with self.assertRaises(ValueError):
                phalanx.restore(changed, receipt)
            forged = copy.deepcopy(receipt)
            forged["files"]["src/board.cpp"]["edits"][0]["role"] = "other"
            with self.assertRaises(ValueError):
                phalanx.restore(output, forged)
            for path in phalanx.PATHS:
                changed = dict(sources)
                changed[path] += b"x"
                with self.subTest(path=path), self.assertRaises(ValueError):
                    phalanx.transform(phalanx.VARIANT, changed)

    def test_reject_wrong_closure_definitions_context_and_repetition(self):
        sources = self.sources()
        with self.pins(sources), self.context(sources):
            with self.assertRaises(ValueError):
                phalanx.transform("other", sources)
            with self.assertRaises(ValueError):
                phalanx.transform(phalanx.VARIANT, {"src/board.cpp": sources["src/board.cpp"]})
        bad = dict(sources)
        bad["src/chess.cpp"] = bad["src/chess.cpp"].replace(b"#define PAWN 0", b"#define PAWN 1")
        with self.pins(bad), self.context(sources), self.assertRaisesRegex(ValueError, "definitions"):
            phalanx.transform(phalanx.VARIANT, bad)
        for addition in (phalanx._BEFORE, phalanx._START):
            bad = dict(sources)
            bad["src/board.cpp"] += addition
            with self.pins(bad), self.context(sources), self.assertRaisesRegex(ValueError, "markers"):
                phalanx.transform(phalanx.VARIANT, bad)
        bad = dict(sources)
        bad["src/board.cpp"] = bad["src/board.cpp"].replace(b"fixture loop", b"altered loop")
        with self.pins(bad), self.context(sources), self.assertRaisesRegex(ValueError, "context"):
            phalanx.transform(phalanx.VARIANT, bad)

    def test_all_selected_squares_and_neighbors_in_cpp(self):
        compiler = shutil.which("c++") or shutil.which("g++")
        if compiler is None:
            self.skipTest("C++ compiler unavailable")
        before = phalanx._BEFORE.decode("ascii")
        after = phalanx._AFTER.decode("ascii")
        text = r'''#include <cstdint>
#include <random>
using u64 = uint64_t;
u64 west(u64 b) { return b >> 1 & ~0x8080808080808080ull; }
u64 original(u64 pawns_us, int square) { ''' + before + r''' return 1ull << square; return 0; }
u64 candidate(u64 pawns_us, int square) { ''' + after + r''' return 1ull << square; return 0; }
int main() {
 std::mt19937_64 rng(0x726f7665);
 // Every square and every relevant adjacent-bit value, with other bits varied.
 for (int square=0;square<64;square++) for (int neighbor=0;neighbor<2;neighbor++)
  for (int n=0;n<1024;n++) {
   u64 pawns_us = rng() | (1ull << square);
   if (square%8!=7) {
    u64 bit=1ull << (square+1);
    pawns_us = neighbor ? pawns_us | bit : pawns_us & ~bit;
   }
   if (original(pawns_us,square)!=candidate(pawns_us,square)) return 1;
  }
 // Recreate pawn-only LSB iteration for arbitrary entire bitboards.
 for (int n=0;n<10000;n++) {
  u64 pawns_us=rng(), mask=pawns_us;
  while(mask) { int square=__builtin_ctzll(mask); mask &= mask-1;
   if (original(pawns_us,square)!=candidate(pawns_us,square)) return 2;
  }
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="c4ke-phalanx-fixture-") as directory:
            root = Path(directory)
            source, executable = root / "fixture.cpp", root / "fixture"
            source.write_text(text, encoding="ascii")
            subprocess.run([compiler, "-std=c++20", "-O2", str(source), "-o", str(executable)],
                           check=True, timeout=60, capture_output=True)
            subprocess.run([str(executable)], check=True, timeout=30, capture_output=True)


if __name__ == "__main__":
    unittest.main()
