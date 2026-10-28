"""Offline start-position transform and full modeled board-state comparison."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from . import peer_c4ke_startpos_loop as candidate
except ImportError:
    import peer_c4ke_startpos_loop as candidate


class StartposTransformTests(unittest.TestCase):
    def fixture(self):
        value = {name: b"unrelated source\r\n" for name in candidate.SOURCE_FILES}
        value["src/board.cpp"] = b"before\r\n" + candidate.PRECONDITION + candidate.BEFORE + b"\r\nafter\r\n"
        value["src/chess.cpp"] = b"\r\n".join(candidate.CONSTANTS) + b"\r\n"
        value["src/eval.cpp"] = candidate.LAYOUT + b"\r\n"
        return value

    def test_pinned_source_contract_and_full_inverse(self):
        self.assertEqual(candidate.peers.SOURCE_BLOBS["c4ke"]["src/board.cpp"],
                         "bc78737f92158f95b1c8bd2204793b3c994acb51")
        self.assertEqual(candidate.peers.SOURCE_BLOBS["c4ke"]["src/chess.cpp"],
                         "59377f6afd07739bff3ececa7a588a5f60bd7ff7")
        self.assertEqual(candidate.peers.SOURCE_BLOBS["c4ke"]["src/eval.cpp"],
                         "e8ee08cfb46e5c4e06efb0870a5f01d654e5a63c")
        original = self.fixture()
        with patch.object(candidate.peers, "verify_blob") as verified:
            after, receipt = candidate.transform(original)
            self.assertEqual(verified.call_count, 5)
            self.assertEqual(candidate.restore(after, receipt), original)
            changed = dict(after)
            changed["src/board.cpp"] += b"tamper"
            with self.assertRaises(ValueError):
                candidate.restore(changed, receipt)

    def test_precondition_constants_layout_and_name_collision(self):
        original = self.fixture()
        with patch.object(candidate.peers, "verify_blob"):
            for path in candidate.SOURCE_FILES:
                sources = dict(original)
                sources[path] += candidate.LOOP_NAME
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, "already exists"):
                    candidate.transform(sources)
            for path, old in (("src/board.cpp", candidate.PRECONDITION),
                              ("src/chess.cpp", candidate.CONSTANTS[0]),
                              ("src/eval.cpp", candidate.LAYOUT)):
                sources = dict(original)
                sources[path] = sources[path].replace(old, b"altered", 1)
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, "precondition"):
                    candidate.transform(sources)

    def test_calls_cover_same_32_distinct_squares_and_pieces(self):
        layout = [3, 1, 2, 4, 5, 2, 1, 3]
        old = [(i + offset, piece) for i in range(8) for offset, piece in
               ((0, layout[i] * 2), (56, layout[i] * 2 + 1), (8, 0), (48, 1))]
        new = [(i + i // 16 * 32, layout[i % 8] * 2 * (not (i // 8 % 3)) + i // 16)
               for i in range(32)]
        self.assertEqual(len({square for square, _ in old}), 32)
        self.assertEqual(len({square for square, _ in new}), 32)
        self.assertEqual(sorted(old), sorted(new))
        self.assertNotEqual(old, new)  # The claimed property is final state, not call order.

    @unittest.skipUnless(shutil.which("c++"), "C++ compiler required for the synthetic state comparison")
    def test_compiled_full_modeled_board_state(self):
        # Exact edit operations and distinct start squares; random hash keys.
        # This is not a real minifier, move generation, or runtime test.
        old = candidate.PRECONDITION.decode().replace("\r\n", "\n") + candidate.BEFORE.decode().replace("\r\n", "\n")
        new = candidate.PRECONDITION.decode().replace("\r\n", "\n") + candidate.AFTER.decode().replace("\r\n", "\n")
        source = r'''
#include <cstdint>
#include <cstring>
#include <random>
using u64=uint64_t; using u8=uint8_t; using i32=int;
enum { A1=0,A2=8,A7=48,A8=56,WHITE=0,BLACK=1,WHITE_PAWN=0,BLACK_PAWN=1,
       WHITE_KNIGHT=2,PIECE_NONE=12 };
i32 LAYOUT[]={3,1,2,4,5,2,1,3};u64 KEYS[13][65];
struct Board {
 u64 checkers=0,hash=0,hash_pawn=0,hash_non_pawn[2]{},colors[2]{},pieces[6]{};
 i32 trend=0;u8 stm=0,castled=0,halfmove=0,enpassant=64,board[64]{};
 void edit(i32 square,i32 piece) {
  if(board[square]<PIECE_NONE)
   pieces[board[square]/2]^=1ull<<square,colors[board[square]%2]^=1ull<<square,
   hash^=KEYS[board[square]][square],
   (board[square]<WHITE_KNIGHT?hash_pawn:hash_non_pawn[board[square]%2])^=KEYS[board[square]][square];
  if(piece<PIECE_NONE)
   pieces[piece/2]^=1ull<<square,colors[piece%2]^=1ull<<square,
   hash^=KEYS[piece][square],
   (piece<WHITE_KNIGHT?hash_pawn:hash_non_pawn[piece%2])^=KEYS[piece][square];
  board[square]=piece;
 }
 void old_run(){ OLD }
 void new_run(){ NEW }
};
bool same(const Board&a,const Board&b) {
 return a.checkers==b.checkers&&a.hash==b.hash&&a.hash_pawn==b.hash_pawn&&
  !std::memcmp(a.hash_non_pawn,b.hash_non_pawn,sizeof a.hash_non_pawn)&&
  !std::memcmp(a.colors,b.colors,sizeof a.colors)&&!std::memcmp(a.pieces,b.pieces,sizeof a.pieces)&&
  a.trend==b.trend&&a.stm==b.stm&&a.castled==b.castled&&a.halfmove==b.halfmove&&
  a.enpassant==b.enpassant&&!std::memcmp(a.board,b.board,sizeof a.board);
}
int main(){std::mt19937_64 r(27202);for(int n=0;n<10000;n++){
 for(auto& row:KEYS)for(auto& k:row)k=r();
 Board a{},b{};a.old_run();b.new_run();if(!same(a,b))return 1;
 }return 0;}
'''.replace("OLD", old).replace("NEW", new)
        with tempfile.TemporaryDirectory(prefix="rove-c4ke-startpos-") as directory:
            src, exe = Path(directory) / "test.cpp", Path(directory) / "test"
            src.write_text(source, encoding="utf-8")
            subprocess.run([shutil.which("c++"), "-std=c++17", "-O1", str(src), "-o", str(exe)],
                           check=True, capture_output=True, timeout=30)
            subprocess.run([str(exe)], check=True, capture_output=True, timeout=30)


if __name__ == "__main__":
    unittest.main()
