import copy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from . import peer_c4ke_ep_hash as ep, peers
except ImportError:
    import peer_c4ke_ep_hash as ep
    import peers


class EnPassantHashTest(unittest.TestCase):
    def sources(self):
        result = {path: b"fixture\r\n" for path in ep.PATHS}
        result["src/board.cpp"] = (ep._EDIT_START + b"\r\nfixture edit\r\n" + ep._EDIT_END + b"\r\n"
                                   + ep._MAKE_START + b"\r\n" + ep._BEFORE + b"\r\n" + ep._MAKE_END)
        return result

    def pins(self, sources):
        return mock.patch.dict(peers.SOURCE_BLOBS["c4ke"],
                               {path: peers.git_blob(data) for path, data in sources.items()})

    def contexts(self, sources):
        board = sources["src/board.cpp"]
        a = board[board.index(ep._EDIT_START):board.index(ep._EDIT_END)]
        b = board[board.index(ep._MAKE_START):board.index(ep._MAKE_END)]
        return mock.patch.multiple(ep, _EDIT_SHA=peers.sha(a), _MAKE_SHA=peers.sha(b))

    def test_full_inverse_and_tampering(self):
        sources = self.sources()
        with self.pins(sources), self.contexts(sources):
            output, receipt = ep.transform(ep.VARIANT, sources)
            self.assertEqual(ep.restore(output, receipt), sources)
            self.assertEqual(output["src/board.cpp"].count(ep._AFTER), 1)
            changed = dict(output)
            changed["src/board.cpp"] += b"x"
            with self.assertRaises(ValueError):
                ep.restore(changed, receipt)
            forged = copy.deepcopy(receipt)
            forged["files"]["src/board.cpp"]["edits"][0]["role"] = "forged"
            with self.assertRaises(ValueError):
                ep.restore(output, forged)
            for path in ep.PATHS:
                changed = dict(sources)
                changed[path] += b"x"
                with self.subTest(path=path), self.assertRaises(ValueError):
                    ep.transform(ep.VARIANT, changed)

    def test_pin_and_context_guards(self):
        sources = self.sources()
        with self.pins(sources), self.contexts(sources):
            with self.assertRaises(ValueError):
                ep.transform("other", sources)
            with self.assertRaises(ValueError):
                ep.transform(ep.VARIANT, {"src/board.cpp": sources["src/board.cpp"]})
        for old, new in ((b"fixture edit", b"different edit"), (ep._BEFORE, ep._BEFORE + b"x")):
            changed = dict(sources)
            changed["src/board.cpp"] = changed["src/board.cpp"].replace(old, new)
            with self.pins(changed), self.contexts(sources), self.assertRaisesRegex(ValueError, "context"):
                ep.transform(ep.VARIANT, changed)
        changed = dict(sources)
        changed["src/board.cpp"] += ep._BEFORE
        with self.pins(changed), self.contexts(sources), self.assertRaises(ValueError):
            ep.transform(ep.VARIANT, changed)

    def test_cpp_entire_state_and_early_exit(self):
        compiler = shutil.which("c++") or shutil.which("g++")
        if compiler is None:
            self.skipTest("C++ compiler unavailable")
        source = r'''#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <random>
using u64=uint64_t;
const int PIECE_NONE=12, WHITE_KNIGHT=2, SQUARE_NONE=64;
u64 KEYS[13][65];
struct Board {
 u64 hash, hash_pawn, hash_non_pawn[2], colors[2], pieces[6];
 int enpassant, stm, halfmove, board[64], log[8], logsize;
 void edit(int square,int piece) {
  log[logsize++]=square*16+piece;
  int old=board[square];
  if(old<PIECE_NONE) {
   pieces[old/2]^=1ull<<square; colors[old%2]^=1ull<<square;
   hash^=KEYS[old][square];
   (old<WHITE_KNIGHT?hash_pawn:hash_non_pawn[old%2])^=KEYS[old][square];
  }
  if(piece<PIECE_NONE) {
   pieces[piece/2]^=1ull<<square; colors[piece%2]^=1ull<<square;
   hash^=KEYS[piece][square];
   (piece<WHITE_KNIGHT?hash_pawn:hash_non_pawn[piece%2])^=KEYS[piece][square];
  }
  board[square]=piece;
 }
 int run(int from,int to,int promo,bool early,bool candidate) {
  int piece=board[from]; halfmove++; halfmove*=board[to]>11 && piece>1;
  edit(to,promo?promo*2+stm:piece); edit(from,PIECE_NONE);
  if(candidate) {
''' + ep._AFTER.decode("ascii") + r'''
  } else {
''' + ep._BEFORE.decode("ascii") + r'''
  }
  enpassant=piece<WHITE_KNIGHT && abs(from-to)==16?to^8:SQUARE_NONE;
  hash^=KEYS[PIECE_NONE][enpassant];
  // Stand-in for the later early-return path: no later state changes on return.
  if(early) return 1;
  stm^=1; hash^=KEYS[PIECE_NONE][0]; return 0;
 }
};
int main() {
 std::mt19937_64 r(81173);
 for(int n=0;n<8192;n++) {
  for(auto& row:KEYS) for(auto& x:row) x=(n%4==0)?0:(n%4==1)?42:r();
  Board a{}; a.hash=r();a.hash_pawn=r(); for(auto& x:a.hash_non_pawn)x=r();
  for(auto& x:a.colors)x=r();for(auto& x:a.pieces)x=r();
  for(auto& x:a.board)x=r()%13; a.stm=r()%2;a.halfmove=r()%100;
  int from=r()%64,to=r()%64; if(from==to)to=(to+1)%64;
  bool capture=n%2; a.board[from]=capture?r()%2:2+r()%10;
  a.enpassant=capture?to:r()%65;
  int promo=(n%7==0)?5:0;bool early=n%3==0;Board b=a;
  int ra=a.run(from,to,promo,early,false), rb=b.run(from,to,promo,early,true);
  if(ra!=rb || a.hash!=b.hash || a.hash_pawn!=b.hash_pawn ||
     memcmp(a.hash_non_pawn,b.hash_non_pawn,sizeof(a.hash_non_pawn)) ||
     memcmp(a.colors,b.colors,sizeof(a.colors)) || memcmp(a.pieces,b.pieces,sizeof(a.pieces)) ||
     a.enpassant!=b.enpassant || a.stm!=b.stm || a.halfmove!=b.halfmove ||
     memcmp(a.board,b.board,sizeof(a.board)) || a.logsize!=b.logsize ||
     memcmp(a.log,b.log,sizeof(a.log))) return 1;
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="c4ke-ep-fixture-") as directory:
            root = Path(directory)
            cpp, executable = root / "fixture.cpp", root / "fixture"
            cpp.write_text(source, encoding="ascii")
            subprocess.run([compiler, "-std=c++20", "-O2", str(cpp), "-o", str(executable)],
                           check=True, timeout=60, capture_output=True)
            subprocess.run([str(executable)], check=True, timeout=30, capture_output=True)


if __name__ == "__main__":
    unittest.main()
