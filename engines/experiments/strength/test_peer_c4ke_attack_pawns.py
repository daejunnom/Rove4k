"""Focused inverse and compiled original/candidate pawn-attacker comparison."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from . import peer_c4ke_attack_pawns as candidate
except ImportError:
    import peer_c4ke_attack_pawns as candidate


class PawnAttackerTests(unittest.TestCase):
    def fixture(self):
        sources = {path: b"unrelated\r\n" for path in candidate.SOURCE_FILES}
        sources["src/board.cpp"] = candidate.BEFORE
        sources["src/chess.cpp"] = b"\r\n".join(candidate.DIRECTIONS + candidate.CONSTANTS)
        return sources

    def test_five_pins_inverse_and_tamper(self):
        self.assertEqual({path: candidate.peers.SOURCE_BLOBS["c4ke"][path]
                          for path in candidate.SOURCE_FILES}, {
            "src/board.cpp": "bc78737f92158f95b1c8bd2204793b3c994acb51",
            "src/chess.cpp": "59377f6afd07739bff3ececa7a588a5f60bd7ff7",
            "src/eval.cpp": "e8ee08cfb46e5c4e06efb0870a5f01d654e5a63c",
            "src/search.cpp": "a9cf924b1ed07ef2f2815baa0c177fb7319628d5",
            "src/main.cpp": "57a942ee5c415dbcfd1b20912f6193bdd9372791"})
        original = self.fixture()
        with patch.object(candidate.peers, "verify_blob") as verify:
            result, receipt = candidate.transform(original)
            self.assertEqual(verify.call_count, 5)
            self.assertEqual(candidate.restore(result, receipt), original)
            for path in candidate.SOURCE_FILES:
                broken = dict(result)
                broken[path] += b"tamper"
                with self.subTest(path=path), self.assertRaises(ValueError):
                    candidate.restore(broken, receipt)

    def test_direction_preconditions_and_identifier_collisions(self):
        original = self.fixture()
        with patch.object(candidate.peers, "verify_blob"):
            for path in candidate.SOURCE_FILES:
                broken = dict(original)
                broken[path] += candidate.NAME
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, "already exists"):
                    candidate.transform(broken)
            for fragment in candidate.DIRECTIONS + candidate.CONSTANTS:
                broken = dict(original)
                broken["src/chess.cpp"] = broken["src/chess.cpp"].replace(fragment, b"altered", 1)
                with self.subTest(fragment=fragment), self.assertRaisesRegex(ValueError, "preconditions"):
                    candidate.transform(broken)
            with self.assertRaisesRegex(ValueError, "closure"):
                candidate.transform({})

    @unittest.skipUnless(shutil.which("c++"), "C++ compiler required")
    def test_compiled_original_and_candidate_pawn_masks(self):
        # Embed the pinned upstream direction definitions and both exact
        # attacker term fragments; not a full movegen or tournament test.
        source = r'''
#include <cstdint>
#include <cstring>
#include <random>
using u64=uint64_t;
#define PAWN 0
#define WHITE 0
#define BLACK 1
DIRECTIONS
struct Old {u64 pieces[6],colors[2],hash;uint8_t board[64];
 u64 pawn_attackers(u64 mask){OLD;}};
struct New {u64 pieces[6],colors[2],hash;uint8_t board[64];
 u64 pawn_attackers(u64 mask){NEW;}};
template<class A,class B>bool same(const A&a,const B&b){return a.hash==b.hash&&
 !std::memcmp(a.pieces,b.pieces,sizeof a.pieces)&&!std::memcmp(a.colors,b.colors,sizeof a.colors)&&
 !std::memcmp(a.board,b.board,sizeof a.board);}
int main(){std::mt19937_64 rng(139001);
 for(int n=0;n<10000;n++){
  Old a{};New b{};for(int i=0;i<6;i++)a.pieces[i]=b.pieces[i]=rng();
  for(int i=0;i<2;i++)a.colors[i]=b.colors[i]=rng();a.hash=b.hash=rng();
  for(int i=0;i<64;i++)a.board[i]=b.board[i]=rng()%13;Old baseline=a;
  for(int j=0;j<67;j++){
   u64 mask=j<64?1ull<<j:j==64?0:j==65?~0ull:rng();
   if(a.pawn_attackers(mask)!=b.pawn_attackers(mask)||!same(a,b)||!same(a,baseline))return 1;
  }
 }}
'''.replace("DIRECTIONS", b"\n".join(candidate.DIRECTIONS).decode().replace("\r\n", "\n"))
        source = source.replace("OLD", candidate.BEFORE.decode().replace("\r\n", "\n"))
        source = source.replace("NEW", candidate.AFTER.decode().replace("\r\n", "\n"))
        with tempfile.TemporaryDirectory(prefix="rove-c4ke-attack-pawns-") as directory:
            src, exe = Path(directory) / "test.cpp", Path(directory) / "test"
            src.write_text(source, encoding="utf-8")
            subprocess.run([shutil.which("c++"), "-std=c++20", "-O1", str(src), "-o", str(exe)],
                           check=True, capture_output=True, timeout=30)
            subprocess.run([str(exe)], check=True, capture_output=True, timeout=30)


if __name__ == "__main__":
    unittest.main()
