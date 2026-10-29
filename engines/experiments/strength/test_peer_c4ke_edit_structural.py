import copy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from . import peer_c4ke_edit_structural as structural
    from . import peers
except ImportError:
    import peer_c4ke_edit_structural as structural
    import peers


class EditStructuralTest(unittest.TestCase):
    def sources(self):
        sources = {path: b"pinned context\n" for path in structural.edit_specs(structural.VARIANT)}
        sources["src/board.cpp"] = b"prefix\r\n" + structural._EDIT_BEFORE + b"suffix\r\n"
        return sources

    def pin(self, sources):
        return mock.patch.dict(peers.SOURCE_BLOBS["c4ke"],
                               {path: peers.git_blob(data) for path, data in sources.items()})

    def test_inverse_replay_and_tamper(self):
        sources = self.sources()
        with self.pin(sources):
            output, receipt = structural.transform(structural.VARIANT, sources)
            self.assertEqual(structural.restore(output, receipt), sources)
            altered = dict(output)
            altered["src/board.cpp"] += b"x"
            with self.assertRaises(ValueError):
                structural.restore(altered, receipt)
            altered = copy.deepcopy(receipt)
            altered["revision"] = "bad"
            with self.assertRaises(ValueError):
                structural.restore(output, altered)
            altered = dict(sources)
            altered["src/chess.cpp"] += b"x"
            with self.assertRaises(ValueError):
                structural.transform(structural.VARIANT, altered)

    def test_duplicate_marker_missing_context_and_collision(self):
        sources = self.sources()
        sources["src/board.cpp"] += structural._EDIT_BEFORE
        with self.pin(sources), self.assertRaises(ValueError):
            structural.transform(structural.VARIANT, sources)
        with self.assertRaises(ValueError):
            structural.transform(structural.VARIANT, {"src/board.cpp": b""})
        sources = self.sources()
        sources["src/chess.cpp"] += b"rove_p"
        with self.pin(sources), self.assertRaises(ValueError):
            structural.transform(structural.VARIANT, sources)
        with self.assertRaises(ValueError):
            structural.edit_specs("unknown")

    def test_actual_cpp_all_square_and_byte_piece_combinations(self):
        compiler = shutil.which("c++") or shutil.which("g++")
        if compiler is None:
            self.skipTest("C++ compiler unavailable")
        prefix = r'''
#include <cstdint>
#include <cstring>
using i32=int; using u64=uint64_t; using u8=uint8_t;
constexpr int PIECE_NONE=12, WHITE_KNIGHT=2;
u64 KEYS[13][64];
struct Board {
    u64 pieces[6],colors[2],hash,hash_pawn,hash_non_pawn[2]; u8 board[64];
    void original(i32 square,i32 piece){
'''
        between = "\nboard[square]=piece;}\nvoid candidate(i32 square,i32 piece){\n"
        suffix = r'''
board[square]=piece;}
bool eq(const Board& b)const{
    return !std::memcmp(pieces,b.pieces,sizeof pieces) &&
      !std::memcmp(colors,b.colors,sizeof colors) && hash==b.hash &&
      hash_pawn==b.hash_pawn && !std::memcmp(hash_non_pawn,b.hash_non_pawn,sizeof hash_non_pawn) &&
      !std::memcmp(board,b.board,sizeof board);
}};
int main(){
 for(int p=0;p<13;++p)for(int s=0;s<64;++s)
    KEYS[p][s]=(0x9e3779b97f4a7c15ULL*(p+1))^(0xbf58476d1ce4e5b9ULL*(s+1));
 for(int s=0;s<64;++s)for(int old=0;old<256;++old)for(int next=0;next<256;++next){
    Board a{}; for(int i=0;i<6;++i)a.pieces[i]=KEYS[(old+i)%13][s];
    for(int i=0;i<2;++i)a.colors[i]=a.hash_non_pawn[i]=KEYS[(next+i)%13][s];
    a.hash=KEYS[old%13][s]; a.hash_pawn=KEYS[next%13][s]; a.board[s]=old;
    Board b=a; a.original(s,next); b.candidate(s,next); if(!a.eq(b))return 1;
 }
}
'''
        code = (prefix + structural._EDIT_BEFORE.decode("ascii") + between +
                structural._EDIT_AFTER.decode("ascii") + suffix)
        with tempfile.TemporaryDirectory(prefix="c4ke-edit-fixture-") as directory:
            path = Path(directory)
            source, executable = path / "fixture.cpp", path / "fixture"
            source.write_text(code, encoding="ascii")
            subprocess.run([compiler, "-std=c++23", "-O2", str(source), "-o", str(executable)],
                           check=True, timeout=60, capture_output=True)
            subprocess.run([str(executable)], check=True, timeout=30, capture_output=True)


if __name__ == "__main__":
    unittest.main()
