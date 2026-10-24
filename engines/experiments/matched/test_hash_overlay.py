"""Pinned source guards and optional real C/Rust matched-hash contract.

Run ordinary tests with ``python -m unittest discover -s
engines/experiments/matched -p test_hash_overlay.py``. On Linux set
ROVE_MATCHED_NATIVE=1 and RUSTC to enable the actual compiled dual-language
fixture. ROVE_MATCHED_SOURCE may identify a frozen directory containing only
the admitted runtime files; otherwise git show reads the pinned commit.
Native fixtures and executables live in the system temporary directory.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location("matched_hash_overlay", HERE / "hash_overlay.py")
overlay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(overlay)


def frozen(name):
    directory = os.environ.get("ROVE_MATCHED_SOURCE")
    if directory:
        return (Path(directory) / name).read_bytes()
    return subprocess.check_output([
        "git", "-C", str(ROOT), "show", f"{overlay.PINNED_BASE}:engines/{name}"
    ])


def reference_stream():
    # Stateful stream mirrors C's actual initialization, independently of the
    # indexed/random-access implementation under test.
    state = 0x726F7665346B
    values = []
    for _ in range(1561):
        state = (state + 0x9E3779B97F4A7C15) & ((1 << 64) - 1)
        value = state
        value ^= value >> 30
        value = value * 0xBF58476D1CE4E5B9 & ((1 << 64) - 1)
        value ^= value >> 27
        value = value * 0x94D049BB133111EB & ((1 << 64) - 1)
        values.append(value ^ (value >> 31))
    return values


CASES = [
    # Reversible repetition, irreversible reset, a legal EP capture.
    ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
     "g1f3 g8f6 f3g1 f6g8 g1f3 g8f6 f3g1 f6g8 e2e4 a7a6 e4e5 d7d5 e5d6"),
    # Both white and black king/queen-side castling move the rook as well.
    ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 9 1", "e1g1 e8c8"),
    ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 9 1", "e1c1 e8g8"),
    # Capturing underpromotion removes a pawn key and captured rook.
    ("1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7b8n"),
    ("4k3/8/8/8/8/8/7p/4K1R1 b - - 0 1", "h2g1q"),
    # Legal EP, irrelevant EP and EP pinned by a rook; both sides.
    ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "e5d6"),
    ("4k3/8/8/3p4/8/8/8/4K3 w - d6 0 1", "e1f1"),
    ("4r1k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "e5e6"),
    ("4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1", "e4d3"),
    ("4k3/8/8/8/3Pp3/8/8/4R1K1 b - d3 0 1", "e4e3"),
    # Context's longest searched suffix (half=99), then terminal half=100.
    ("4k3/8/8/8/8/8/8/4K3 w - - 98 1", "e1d1 e8d8"),
    # History capacity rollover is valid for position/pawn identity, not a
    # searched context: >=100 is explicitly represented as terminal here.
    ("4k3/8/8/8/8/8/8/4K3 w - - 0 1", " ".join(["e1d1 e8d8 d1e1 d8e8"] * 27)),
]

C_FIXTURE = r'''
#include <inttypes.h>
#include "c/board.c"
#include "c/search.c"
static Worker worker;
static void dump(const Board *board){
    if(!board_invariant(board))exit(4);
    printf("%016" PRIx64 " %016" PRIx64 " ",board->key,board->pawnkey);
    if(board->half<100)printf("%016" PRIx64,context_key(&worker,board));else printf("terminal");
    printf(" %d %d %" PRIu64 "\n",board->half,board->side,perft(board,2));
}
int main(void){
    board_init();
    for(int p=0;p<12;p++)for(int q=0;q<128;q++)printf("%016" PRIx64 "\n",pieces[p][q]);
    for(int i=0;i<16;i++)printf("%016" PRIx64 "\n",rights[i]);
    for(int i=0;i<8;i++)printf("%016" PRIx64 "\n",eps[i]);
    printf("%016" PRIx64 "\n",turn);
    char line[8192];
    while(fgets(line,sizeof line,stdin)){
        char *tab=strchr(line,'\t');if(!tab)return 2;*tab++=0;
        Board b;if(!board_fen(&b,line))return 3;
        worker.path_len=1;worker.path[0]=b.key;dump(&b);
        char *save=0;for(char *m=strtok_r(tab," \r\n",&save);m;m=strtok_r(0," \r\n",&save)){
            unsigned move=parse_move(&b,m);Board next;if(!move||!make_move(&b,move,&next))return 5;
            b=next;worker.path[worker.path_len++]=b.key;dump(&b);
        }
    }
}
'''

RUST_FIXTURE = r'''
mod board {
    include!("rust/board.rs");
    pub fn slot(index:u64)->u64{
        if index<1536{
            let piece=index/128;
            let p=if piece<6{piece as i8+1}else{5-piece as i8};
            piece_hash((index%128)as u8,p)
        }else{study_zobrist(index)}
    }
}
use std::io::{self,BufRead};
fn dump(board:&board::Board){
    let mut rebuilt=*board;rebuilt.rebuild();
    assert_eq!(board.hash,rebuilt.hash);assert_eq!(board.study_pawn_key,rebuilt.study_pawn_key);
    assert_eq!(board.bb,rebuilt.bb);assert_eq!(board.evalwhite(),rebuilt.evalwhite());
    print!("{:016x} {:016x} ",board.hash,board.study_pawn_key);
    if board.halfmove<100{print!("{:016x}",board.study_context_key())}else{print!("terminal")}
    println!(" {} {} {}",board.halfmove,board.side,board.perft(2));
}
fn main(){
    for index in 0..1561{println!("{:016x}",board::slot(index));}
    for line in io::stdin().lock().lines(){
        let line=line.unwrap();let(fen,moves)=line.split_once('\t').unwrap();
        let mut board=board::Board::from_fen(fen).unwrap();dump(&board);
        for text in moves.split_whitespace(){let m=board.parse_move(text).unwrap();board=board.play(m);dump(&board);}
    }
}
'''


class HashOverlayTests(unittest.TestCase):
    def test_all_reference_slots(self):
        expected = reference_stream()
        self.assertEqual([overlay.reference_slot(i) for i in range(1561)], expected)
        self.assertEqual(len(set(expected)), 1561)
        for invalid in [-1, 1561]:
            with self.assertRaises(ValueError):
                overlay.reference_slot(invalid)

    def test_bytes_and_text_preserve_other_files_and_input(self):
        source = frozen("rust/board.rs")
        for value in [source, source.decode("utf-8"), source.replace(b"\n", b"\r\n")]:
            original = {"rust/board.rs": value, "unchanged": b"other source"}
            output, changes = overlay.apply(original)
            self.assertEqual(original["rust/board.rs"], value)
            self.assertEqual(output["unchanged"], b"other source")
            self.assertIsInstance(output["rust/board.rs"], type(value))
            text = output["rust/board.rs"]
            text = text.decode() if isinstance(text, bytes) else text
            self.assertIn("pub study_pawn_key: u64", text)
            self.assertIn("pub fn study_context_key(&self)", text)
            self.assertIn("static STUDY_ZOBRIST: [u64; 1561]", text)
            self.assertIn("STUDY_ZOBRIST[index as usize]", text)
            self.assertEqual(len(changes), 8)

    def test_explicit_on_demand_mode_and_strict_option(self):
        source = frozen("rust/board.rs")
        output, changes = overlay.apply({"rust/board.rs": source}, precompute=False)
        self.assertNotIn(b"static STUDY_ZOBRIST", output["rust/board.rs"])
        self.assertIn(b"mix(0x726f7665346bu64.wrapping_add", output["rust/board.rs"])
        self.assertTrue(any("on-demand" in change for change in changes))
        default, changes = overlay.apply({"rust/board.rs": source})
        self.assertNotEqual(default["rust/board.rs"], output["rust/board.rs"])
        self.assertTrue(any("12488 initialized bytes" in change for change in changes))
        for invalid in [0, 1, "true", None]:
            with self.assertRaises(TypeError):
                overlay.apply({"rust/board.rs": source}, precompute=invalid)

    def test_guard_rejects_drift_missing_reapply_and_duplicate(self):
        source = frozen("rust/board.rs")
        patched, _ = overlay.apply({"rust/board.rs": source})
        for files in [{}, {"rust/board.rs": source + b"\n"}, patched,
                      {"rust/board.rs": source.replace(b"fn piece_hash", b"fn changed_hash")},
                      {"rust/board.rs": source + b"\n" + source}]:
            with self.assertRaises(ValueError):
                overlay.apply(files)

    @unittest.skipUnless(os.environ.get("ROVE_MATCHED_NATIVE") == "1", "explicit Linux native fixture")
    def test_actual_c_and_rust_slots_incremental_keys_context_and_perft(self):
        names = ["c/board.c", "c/rove.h", "c/parallel.h", "c/search.c", "rust/board.rs"]
        original = {name: frozen(name) for name in names}
        files, _ = overlay.apply(original)
        rustc = os.environ.get("RUSTC", "rustc")
        self.assertTrue(shutil.which(rustc) or Path(rustc).is_file(), "RUSTC unavailable")
        with tempfile.TemporaryDirectory(prefix="rove4k-matched-hash-") as tmp:
            directory = Path(tmp)
            for name, data in files.items():
                path = directory / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            (directory / "fixture.c").write_text(C_FIXTURE, encoding="utf-8")
            (directory / "fixture.rs").write_text(RUST_FIXTURE, encoding="utf-8")
            subprocess.run(["cc", "-std=c11", "-O2", "-ffunction-sections", "-fdata-sections", "-pthread",
                            "-Wl,--gc-sections", "fixture.c", "-o", "fixture-c"], cwd=tmp, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
            subprocess.run([rustc, "--edition=2024", "-O", "-Awarnings", "fixture.rs", "-o", "fixture-rust"],
                           cwd=tmp, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
            symbols = subprocess.check_output(["nm", "-S", "-C", "fixture-rust"], cwd=tmp, text=True)
            tables = [line.split() for line in symbols.splitlines() if line.endswith("::board::STUDY_ZOBRIST")]
            self.assertEqual(len(tables), 1)
            self.assertEqual(int(tables[0][1], 16), 1561 * 8)
            self.assertEqual(tables[0][2].lower(), "r", "table must be initialized read-only data")
            on_demand, _ = overlay.apply(original, precompute=False)
            (directory / "rust/board.rs").write_bytes(on_demand["rust/board.rs"])
            subprocess.run([rustc, "--edition=2024", "-O", "-Awarnings", "fixture.rs", "-o", "fixture-rust-on-demand"],
                           cwd=tmp, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
            data = "".join(f"{fen}\t{moves}\n" for fen, moves in CASES).encode()
            outputs = []
            for language in ["c", "rust", "rust-on-demand"]:
                result = subprocess.run([str(directory / f"fixture-{language}")], input=data,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=90)
                outputs.append(result.stdout.decode().splitlines())
            expected = [f"{value:016x}" for value in reference_stream()]
            self.assertEqual(outputs[0][:1561], expected)
            self.assertEqual(outputs[1][:1561], expected)
            self.assertEqual(outputs[2][:1561], expected)
            expected_states = sum(1 + len(moves.split()) for _, moves in CASES)
            self.assertEqual(len(outputs[0]), 1561 + expected_states)
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0], outputs[2])


if __name__ == "__main__":
    unittest.main()
