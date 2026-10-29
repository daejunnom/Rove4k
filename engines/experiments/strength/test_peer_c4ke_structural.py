import copy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from . import peer_c4ke_structural as structural
    from . import peers
except ImportError:
    import peer_c4ke_structural as structural
    import peers


class CastleStructuralTest(unittest.TestCase):
    def sources(self):
        return {"src/board.cpp": b"prefix\r\n" + structural._CASTLE_BEFORE + b"\r\nsuffix\r\n",
                "src/chess.cpp": b"pinned context\n"}

    def pin(self, sources):
        return mock.patch.dict(peers.SOURCE_BLOBS["c4ke"],
                               {path: peers.git_blob(data) for path, data in sources.items()})

    def test_reverse_replay_and_tamper_rejection(self):
        sources = self.sources()
        with self.pin(sources):
            outputs, receipt = structural.transform("castle-or-v1", sources)
            self.assertEqual(structural.restore(outputs, receipt), sources)
            changed = dict(outputs)
            changed["src/board.cpp"] += b"x"
            with self.assertRaises(ValueError):
                structural.restore(changed, receipt)
            changed_receipt = copy.deepcopy(receipt)
            changed_receipt["revision"] = "untrusted"
            with self.assertRaises(ValueError):
                structural.restore(outputs, changed_receipt)
            changed = dict(sources)
            changed["src/chess.cpp"] += b"x"
            with self.assertRaises(ValueError):
                structural.transform("castle-or-v1", changed)

    def test_duplicate_marker_missing_context_and_unknown_variant_rejected(self):
        sources = self.sources()
        sources["src/board.cpp"] += structural._CASTLE_BEFORE
        with self.pin(sources), self.assertRaises(ValueError):
            structural.transform("castle-or-v1", sources)
        with self.assertRaises(ValueError):
            structural.transform("castle-or-v1", {"src/board.cpp": sources["src/board.cpp"]})
        with self.assertRaises(ValueError):
            structural.edit_specs("unknown")

    def test_castling_expression_all_legal_squares_and_byte_states(self):
        corners = ((7, 1), (0, 2), (63, 4), (56, 8))
        for frm in range(64):
            for to in range(64):
                mask = sum((frm == square or to == square) * flag for square, flag in corners)
                for initial in range(256):
                    expected = initial
                    for square, flag in corners:
                        if frm == square or to == square:
                            expected |= flag
                    self.assertEqual(expected, initial | mask)

    def test_actual_expressions_in_cpp(self):
        compiler = shutil.which("c++") or shutil.which("g++")
        if compiler is None:
            self.skipTest("C++ compiler unavailable")
        prefix = """#include <cstdint>
constexpr int A1=0, H1=7, A8=56, H8=63;
constexpr int CASTLED_WK=1, CASTLED_WQ=2, CASTLED_BK=4, CASTLED_BQ=8;
uint8_t original(int from,int to,uint8_t castled){
"""
        code = (prefix + structural._CASTLE_BEFORE.decode("ascii") +
                "\nreturn castled;}\nuint8_t candidate(int from,int to,uint8_t castled){\n" +
                structural._CASTLE_AFTER.decode("ascii") +
                """\nreturn castled;}
int main(){for(int f=0;f<64;++f)for(int t=0;t<64;++t)
for(int c=0;c<256;++c)if(original(f,t,c)!=candidate(f,t,c))return 1;}
""")
        with tempfile.TemporaryDirectory(prefix="c4ke-castle-fixture-") as directory:
            path = Path(directory)
            source, executable = path / "fixture.cpp", path / "fixture"
            source.write_text(code, encoding="ascii")
            subprocess.run([compiler, "-std=c++23", "-O2", str(source), "-o", str(executable)],
                           check=True, timeout=60, capture_output=True)
            subprocess.run([str(executable)], check=True, timeout=30, capture_output=True)


if __name__ == "__main__":
    unittest.main()
