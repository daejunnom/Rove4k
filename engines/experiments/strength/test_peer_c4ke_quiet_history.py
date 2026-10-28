import copy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from . import peer_c4ke_quiet_history as quiet, peers
except ImportError:
    import peer_c4ke_quiet_history as quiet
    import peers


class QuietHistoryTest(unittest.TestCase):
    def sources(self):
        sources = {path: b"pinned context\r\n" for path in quiet.PATHS}
        sources["src/search.cpp"] = (b"struct Thread {\r\n" + quiet._SEARCH + b") {\r\n"
                                     + quiet._BONUS_BEFORE + b"\r\n"
                                     + quiet._PENALTY_BEFORE + b"\r\n}};\r\n")
        return sources

    def pin(self, sources):
        return mock.patch.dict(peers.SOURCE_BLOBS["c4ke"],
                               {path: peers.git_blob(data) for path, data in sources.items()})

    def test_complete_inverse_and_tamper_rejection(self):
        sources = self.sources()
        with self.pin(sources):
            output, receipt = quiet.transform(quiet.VARIANT, sources)
            self.assertEqual(quiet.restore(output, receipt), sources)
            self.assertEqual(output["src/search.cpp"].count(quiet.IDENTIFIER), 3)
            changed = dict(output)
            changed["src/search.cpp"] += b"x"
            with self.assertRaises(ValueError):
                quiet.restore(changed, receipt)
            changed = copy.deepcopy(receipt)
            changed["files"]["src/search.cpp"]["edits"][0]["role"] = "other"
            with self.assertRaises(ValueError):
                quiet.restore(output, changed)
            changed = dict(sources)
            changed["src/board.cpp"] += b"changed"
            with self.assertRaises(ValueError):
                quiet.transform(quiet.VARIANT, changed)

    def test_pin_closure_markers_and_identifiers_are_strict(self):
        sources = self.sources()
        with self.pin(sources), self.assertRaises(ValueError):
            quiet.transform("other", sources)
        with self.pin(sources), self.assertRaises(ValueError):
            quiet.transform(quiet.VARIANT, {"src/search.cpp": sources["src/search.cpp"]})
        for identifier in quiet.IDENTIFIERS:
            for path in quiet.PATHS:
                collision = dict(sources)
                collision[path] += b"\r\nint " + identifier + b";\r\n"
                with self.subTest(identifier=identifier, path=path), self.pin(collision):
                    with self.assertRaisesRegex(ValueError, "identifier collides"):
                        quiet.transform(quiet.VARIANT, collision)
        duplicate = dict(sources)
        duplicate["src/search.cpp"] += quiet._BONUS_BEFORE
        with self.pin(duplicate), self.assertRaises(ValueError):
            quiet.transform(quiet.VARIANT, duplicate)

    def test_order_and_aliases_in_cpp(self):
        compiler = shutil.which("c++") or shutil.which("g++")
        if compiler is None:
            self.skipTest("C++ compiler unavailable")
        text = r'''#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <random>
using i16=int16_t; using i32=int; using null=void;
struct Board { int stm; int board[64]; };
using HTable=i16[12][64];
int move_from(int m){return m&63;} int move_to(int m){return m>>6&63;}
void update_history(i16& e,int v){e+=v-e*std::abs(v)/16384;}
struct Thread {
 i16 qhist[2][4096]; HTable h[2]; HTable* stack_conthist[2]; int left,right;
''' + quiet._HELPER.decode("ascii") + r'''
void original(Board& board,int ply,int move,int bonus,const i16* quiet_list,int quiet_count){
''' + quiet._BONUS_BEFORE.decode("ascii") + r'''
for(int k=0;k<quiet_count;k++)
''' + quiet._PENALTY_BEFORE.decode("ascii") + r'''
}
void candidate(Board& board,int ply,int move,int bonus,const i16* quiet_list,int quiet_count){
''' + quiet._BONUS_AFTER.decode("ascii") + r'''
for(int k=0;k<quiet_count;k++)
''' + quiet._PENALTY_AFTER.decode("ascii") + r'''
}
};
int main(){std::mt19937 r(0x4c4b); for(int n=0;n<8192;n++){
 Thread a{},b{};Board board{};board.stm=r()%2;for(auto& x:board.board)x=r()%12;
 for(auto& p:a.qhist)for(auto& x:p)x=int(r()%32769)-16384;
 for(auto& p:a.h)for(auto& q:p)for(auto& x:q)x=int(r()%32769)-16384;
 a.left=r()%2;a.right=(n&1)?a.left:1-a.left;b=a;
 a.stack_conthist[0]=&a.h[a.left];a.stack_conthist[1]=&a.h[a.right];
 b.stack_conthist[0]=&b.h[b.left];b.stack_conthist[1]=&b.h[b.right];
 int bonus=int(r()%3629)-1814;int move=int(i16(r()%65536)),count=r()%17;
 i16 list[16];for(int k=0;k<count;k++)list[k]=(k%3)?i16(r()%65536):i16(move);
 a.original(board,0,move,bonus,list,count);b.candidate(board,0,move,bonus,list,count);
 if(memcmp(a.qhist,b.qhist,sizeof a.qhist)||memcmp(a.h,b.h,sizeof a.h))return 1;
} }
'''
        with tempfile.TemporaryDirectory(prefix="c4ke-quiet-fixture-") as directory:
            root = Path(directory)
            source, executable = root / "fixture.cpp", root / "fixture"
            source.write_text(text, encoding="ascii")
            subprocess.run([compiler, "-std=c++20", "-O2", str(source), "-o", str(executable)],
                           check=True, timeout=60, capture_output=True)
            subprocess.run([str(executable)], check=True, timeout=30, capture_output=True)


if __name__ == "__main__":
    unittest.main()
