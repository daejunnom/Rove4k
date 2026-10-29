#!/usr/bin/env python3
"""Exercise quiet promotions in the admitted selected B TEST-P4 search.

The shipping source is unchanged; only a diagnostic main is appended.  This
is a bounded single-worker search fixture, not event/runtime qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ANCHOR = b"W(ye&&(!zz||d>=f))continue;"
MUTANT = b"W(ye&&(!(zz&&!B(m))||d>=f))continue;"
FENS = (
    ("7k/8/8/8/8/8/3p4/K7 b - - 0 1", "d2d1"),
    ("7k/P7/8/8/8/8/8/K7 w - - 0 1", "a7a8"),
)

# Each position has exactly four legal quiet promotions.  Search is called at
# depth zero with an open alpha/beta window and a fresh table; a useful score
# and a promotion best move prove that an actual quiet promotion was searched.
DRIVER = rb'''
#undef main
int main(void){
 qq=aligned_alloc(4096,qN*sizeof*qq);if(!qq)return 2;
 int errors=0;
 for(int side=-1;side<=1;side+=2){
  za p={0};p.s=side;p.e=-1;M(&p,0,6);M(&p,119,-6);
  M(&p,side>0?96:19,side);p.h^=S(&p);p.r=p.h;
  memset(qr,0,sizeof qr);memset(qq,0,qN*sizeof*qq);
  for(size_t i=0;i<qN;i++)atomic_flag_clear_explicit(&qq[i].a,memory_order_relaxed);
  qh=1;qg[0]=p.h;qc=UINT64_MAX;atomic_store(&qp,0);
  N moves[512];int n=c(&p,moves,0,p.s),quiet=0;
  for(int i=0;i<n;i++)if(B(moves[i])&&!p.b[TO(moves[i])]){
   za child;if(h(&p,moves[i],&child)){if(!(moves[i]&8))return 9;quiet++;}
  }
  N best=0;int score=P(qr,&p,0,-30000,30000,0,6,&best,0,1);
  char text[6];T(best,text);
  printf("%d %d %d %d %llu %s\n",side,quiet,p.s*p.v,score,(unsigned long long)qr->n,text);
  if(quiet!=4||!best||!B(best)||p.b[TO(best)]||score<=p.s*p.v||qr->n<5||atomic_load(&qp))errors++;
 }
 free(qq);return errors?10:0;
}
'''


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "module unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check_oracle():
    oracle = load("quiet_promotion_oracle", ROOT / "engines/tests/chess_oracle.py")
    for fen, prefix in FENS:
        board = oracle.Board.from_fen(fen)
        require(not board.in_check() and not board.in_check(not board.turn), "fixture king is in check")
        legal = {str(move) for move in board.legal_moves()}
        require({prefix + piece for piece in "nbrq"} <= legal, "oracle rejects a quiet promotion")
        require(board.cells[oracle.square(prefix[2:4])] == ".", "promotion destination must be empty")


def checked_source(build):
    verify = load("quiet_promotion_verify", HERE / "profile_verify.py")
    manifest_file = verify.artifact_file(build, "build.json")
    manifest = json.loads(manifest_file.read_bytes())
    admitted = verify.admit_c_build(manifest, build)
    require(admitted.family == "B" and admitted.profile_id == "test-p4"
            and admitted.representation == "source-jit" and admitted.full,
            "admitted full B TEST-P4 source required")
    require(manifest.get("post_compact") == {
        "path": "engines/experiments/tcec-next/profile_b_w256_names.py",
        "variant": "b-search-names"}, "selected final B compaction required")
    source = verify.checked_artifact(build, "main.c", verify._field_pin(admitted.expected, "source"))
    require(source.count(ANCHOR) == 1 and source.count(MUTANT) == 0,
            "one actual selected B quiescence anchor required")
    return source


def run(build, cc):
    require(sys.platform == "linux", "Linux source-bound diagnostic required")
    check_oracle()
    source = checked_source(build)
    with tempfile.TemporaryDirectory(prefix="rove-b-promotion-") as temp:
        path = Path(temp) / "fixture"
        rows = {}
        for mode in ("plain", "ubsan", "mutation"):
            candidate = source.replace(ANCHOR, MUTANT, 1) if mode == "mutation" else source
            fixture = b"#define main rv_unused_shipping_main\n" + candidate + b"\n" + DRIVER
            flags = ["-fsanitize=undefined", "-fno-sanitize-recover=all"] if mode == "ubsan" else []
            compile_result = subprocess.run([cc, "-std=c11", "-O1", "-pthread", *flags,
                                             "-xc", "-", "-o", str(path)], input=fixture,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            require(compile_result.returncode == 0, "fixture compilation failed: " +
                    compile_result.stderr.decode("utf-8", "replace")[-2000:])
            result = subprocess.run([str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            if mode == "mutation":
                lines = result.stdout.decode("ascii").splitlines()
                require(result.returncode == 10 and not result.stderr and len(lines) == 2,
                        "missing-promotion mutation was not rejected for both sides")
                for line, side in zip(lines, (-1, 1)):
                    fields = line.split()
                    require(len(fields) == 6 and fields[0] == str(side) and fields[1] == "4"
                            and fields[2] == fields[3] and fields[4:] == ["1", "0000"],
                            "mutation did not omit both quiet-promotion searches")
                rows[mode] = {"rejected_exit": result.returncode, "sides": [-1, 1]}
                continue
            require(result.returncode == 0 and not result.stderr,
                    mode + " search fixture failed: " + result.stderr.decode("utf-8", "replace")[-2000:])
            lines = result.stdout.decode("ascii").splitlines()
            require(len(lines) == 2, "two promotion observations required")
            observed = []
            for line, (fen, prefix), side in zip(lines, FENS, (-1, 1)):
                fields = line.split()
                require(len(fields) == 6 and fields[0] == str(side) and fields[1] == "4"
                        and fields[2].lstrip("-").isdigit() and fields[3].lstrip("-").isdigit()
                        and fields[4].isdigit() and fields[5] in {prefix + piece for piece in "nbrq"},
                        "unexpected promotion result")
                observed.append({"fen": fen, "stand_pat": int(fields[2]), "score": int(fields[3]),
                                 "nodes": int(fields[4]), "bestmove": fields[5]})
            rows[mode] = observed
        require(rows["plain"] == rows["ubsan"], "plain and UBSan observations differ")
    return {"complete": True, "family": "B", "profile": "test-p4", "final_compact": "selected",
            "source_sha256": hashlib.sha256(source).hexdigest(), "observations": rows,
            "scope": "selected P4 source, direct single-worker quiet-promotion search; not W256 or event qualification"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    print(json.dumps(run(args.build.resolve(strict=True), args.cc), sort_keys=True))
