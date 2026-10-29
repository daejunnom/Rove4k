"""Focused reversible-transform and compiled move-emission comparisons."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from . import peer_c4ke_move_emission as candidate
except ImportError:
    import peer_c4ke_move_emission as candidate


class MoveEmissionTests(unittest.TestCase):
    def fixture(self):
        sources = {name: b"unrelated\r\n" for name in candidate.SOURCE_FILES}
        sources["src/board.cpp"] = b"\r\n".join(
            (candidate.PAWN_BEFORE, candidate.PIECE_BEFORE, *candidate.PAWN_CALLS))
        sources["src/chess.cpp"] = b"\r\n".join(candidate.CONSTANTS)
        return sources

    def test_pins_inverse_and_tampering(self):
        self.assertEqual({path: candidate.peers.SOURCE_BLOBS["c4ke"][path]
                          for path in candidate.SOURCE_FILES}, {
            "src/board.cpp": "bc78737f92158f95b1c8bd2204793b3c994acb51",
            "src/chess.cpp": "59377f6afd07739bff3ececa7a588a5f60bd7ff7",
            "src/eval.cpp": "e8ee08cfb46e5c4e06efb0870a5f01d654e5a63c",
            "src/search.cpp": "a9cf924b1ed07ef2f2815baa0c177fb7319628d5",
            "src/main.cpp": "57a942ee5c415dbcfd1b20912f6193bdd9372791"})
        original = self.fixture()
        with patch.object(candidate.peers, "verify_blob") as verify:
            after, receipt = candidate.transform(original)
            self.assertEqual(verify.call_count, 5)
            self.assertEqual(candidate.restore(after, receipt), original)
            for path in candidate.SOURCE_FILES:
                broken = dict(after)
                broken[path] += b"tamper"
                with self.subTest(path=path), self.assertRaises(ValueError):
                    candidate.restore(broken, receipt)

    def test_offsets_closure_and_collisions(self):
        original = self.fixture()
        with patch.object(candidate.peers, "verify_blob"):
            for path in candidate.SOURCE_FILES:
                bad = dict(original)
                bad[path] += candidate.NAME
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, "already exists"):
                    candidate.transform(bad)
            for call in candidate.PAWN_CALLS:
                bad = dict(original)
                bad["src/board.cpp"] = bad["src/board.cpp"].replace(call, b"altered", 1)
                with self.subTest(call=call), self.assertRaisesRegex(ValueError, "preconditions"):
                    candidate.transform(bad)
            bad = dict(original)
            bad["src/board.cpp"] += b"add_pawn_moves(list, targets, 0);"
            with self.assertRaisesRegex(ValueError, "preconditions"):
                candidate.transform(bad)
            for token in candidate.CONSTANTS:
                bad = dict(original)
                bad["src/chess.cpp"] = bad["src/chess.cpp"].replace(token, b"altered", 1)
                with self.subTest(token=token), self.assertRaisesRegex(ValueError, "preconditions"):
                    candidate.transform(bad)
            with self.assertRaisesRegex(ValueError, "closure"):
                candidate.transform({})

    @unittest.skipUnless(shutil.which("c++"), "C++ compiler required")
    def test_compiled_original_and_candidate_fragments(self):
        # Actual emitter bodies are inserted directly, with only an enclosing
        # synthetic Board/attack fixture; no full engine or minifier is run.
        piece_prefix = b'''null add_moves(i16*& list, u64 targets, u64 occupied, u64 mask, i32 type) {
        for (; mask;) {
            i32 from = LSB(mask);
            mask &= mask - 1;

            u64 attacks = attack(1ull << from, occupied, type) & targets;

            '''
        piece_suffix = b'''\n        }\n    }'''
        def methods(pawn, piece):
            return (pawn + b"\n" + piece_prefix + piece + piece_suffix).decode().replace("\r\n", "\n")
        source = r'''
#include <bit>
#include <cstdint>
#include <cstring>
#include <random>
using u64=uint64_t;using i16=int16_t;using i32=int;using null=void;
#define PAWN 0
#define QUEEN 4
#define LSB std::countr_zero
i16 move_make(i32 from,i32 to,i32 promo=PAWN){return from|to<<6|promo<<12;}
u64 attack(u64 mask,u64 occupied,i32 type){return (mask*0x9e3779b97f4a7c15ULL) ^ occupied ^ (u64(type)*1234567);}
struct Old { u64 checkers,hash,hash_pawn,hash_non_pawn[2],colors[2],pieces[6];
 i32 trend;uint8_t stm,castled,halfmove,enpassant,board[64]; OLD_METHODS };
struct New { u64 checkers,hash,hash_pawn,hash_non_pawn[2],colors[2],pieces[6];
 i32 trend;uint8_t stm,castled,halfmove,enpassant,board[64]; NEW_METHODS };
template<class A,class B> bool same(const A&a,const B&b){return a.checkers==b.checkers &&
 a.hash==b.hash && a.hash_pawn==b.hash_pawn &&
 !std::memcmp(a.hash_non_pawn,b.hash_non_pawn,sizeof a.hash_non_pawn) &&
 !std::memcmp(a.colors,b.colors,sizeof a.colors) && !std::memcmp(a.pieces,b.pieces,sizeof a.pieces) &&
 a.trend==b.trend && a.stm==b.stm && a.castled==b.castled &&
 a.halfmove==b.halfmove && a.enpassant==b.enpassant &&
 !std::memcmp(a.board,b.board,sizeof a.board);}
int main(){
 std::mt19937_64 random(121021);Old a{};New b{};
 a.checkers=b.checkers=random();a.hash=b.hash=random();a.hash_pawn=b.hash_pawn=random();
 for(int i=0;i<2;i++){a.colors[i]=b.colors[i]=random();a.hash_non_pawn[i]=b.hash_non_pawn[i]=random();}
 for(int i=0;i<6;i++)a.pieces[i]=b.pieces[i]=random();
 a.trend=b.trend=123;a.stm=b.stm=1;a.castled=b.castled=7;
 a.halfmove=b.halfmove=14;a.enpassant=b.enpassant=64;
 for(int i=0;i<64;i++)a.board[i]=b.board[i]=random()%13;
 Old baseline=a;
 for(int n=0;n<5000;n++){
  u64 target=n%4?random():0, occupied=random(), mask=n%3?random():0;
  i16 x[22000]{},y[22000]{};i16 *p=x,*q=y;
  for(int offset : {-16,-9,-8,-7,7,8,9,16}) {
   u64 legal=target;for(int t=0;t<64;t++)if(t-offset<0||t-offset>63)legal&=~(1ull<<t);
   a.add_pawn_moves(p,legal,offset);b.add_pawn_moves(q,legal,offset);
  }
  for(int type=1;type<=5;type++){
   a.add_moves(p,target,occupied,mask,type);b.add_moves(q,target,occupied,mask,type);
  }
  if(p-x!=q-y || std::memcmp(x,y,(p-x)*sizeof(i16)) || !same(a,b) || !same(a,baseline))return 1;
 }
}
'''.replace("OLD_METHODS", methods(candidate.PAWN_BEFORE, candidate.PIECE_BEFORE)).replace(
            "NEW_METHODS", methods(candidate.PAWN_AFTER, candidate.PIECE_AFTER))
        with tempfile.TemporaryDirectory(prefix="rove-c4ke-emission-") as directory:
            src, exe = Path(directory) / "test.cpp", Path(directory) / "test"
            src.write_text(source, encoding="utf-8")
            subprocess.run([shutil.which("c++"), "-std=c++20", "-O1", str(src), "-o", str(exe)],
                           check=True, capture_output=True, timeout=30)
            subprocess.run([str(exe)], check=True, capture_output=True, timeout=30)


if __name__ == "__main__":
    unittest.main()
