#!/usr/bin/env python3
"""Test actual compact C/E production consumers and frozen model semantics."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import queue
import random
import re
import subprocess
import sys
import threading

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Engine:
    def __init__(self, path):
        self.process = subprocess.Popen([str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.lines = queue.Queue()
        def read():
            for line in self.process.stdout:
                self.lines.put(line.strip())
        threading.Thread(target=read, daemon=True).start()
        self.transcript = []

    def send(self, command, prefix):
        self.transcript.append({"stdin": command})
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()
        result = []
        while True:
            line = self.lines.get(timeout=20)
            self.transcript.append({"stdout": line})
            result.append(line)
            if line.startswith(prefix):
                return result

    def position(self, fen):
        self.process.stdin.write("position fen " + fen + "\n")
        self.process.stdin.flush()

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.write("quit\n")
            self.process.stdin.flush()
            self.process.wait(timeout=5)
        if self.process.returncode:
            raise AssertionError("engine exited abnormally")

    def terminate(self):
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait()


def actual_model_harness(dev_source, reference, model, out):
    # Include the producer's exact combined DEV input, not a reconstructed model
    # function. Unrestricted synthetic boards independently cover promoted
    # material beyond FEN admission's <=16 pieces per side.
    source = '#define main tiny_ce_engine_main\n#include ' + json.dumps(str(dev_source)) + r'''
#undef main
int main(void){
    int side,from,to,prom,ep;char cells[65];const char *map=" PNBRQKpnbrqk";
    while(scanf("%d %64s %d %d %d %d",&side,cells,&from,&to,&prom,&ep)==6){
        Board p={0};p.s=side;p.e=ep;p.v=INT_MIN;
        for(int q=0;q<64;q++){
            const char *v=strchr(map,cells[q]);
            int piece=v?(int)(v-map):0;
            p.b[(q/8)*16+q%8]=(int8_t)(piece>6?6-piece:piece);
        }
        printf("%d %d %d\n",tiny_white(&p),tiny_raw(&p),tiny_order(&p,MOVE(from,to,prom)));
    }
    return ferror(stdin)?2:0;
}
'''
    harness = out / "actual-model-consumer.c"
    harness.write_text(source)
    rng = random.Random(0xCE20261020)
    positions = []
    fixtures = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w",
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b",
        "4k3/8/8/8/4P3/8/8/4K3 w", "4k3/8/8/4P3/4P3/8/8/4K3 w",
        "4k3/8/8/8/3PP3/8/8/4K3 w", "4k3/8/8/8/8/8/8/B3K2B w",
        "QQQQQQQQ/QQQQQQQQ/QQQQQQQQ/QQQQQQQQ/QQQkQQQQ/QQQQQQQQ/QQQQQQQQ/KQQQQQQQ w",
    ]
    positions.extend(reference.Position.fen(fen) for fen in fixtures)
    for _ in range(2000):
        squares = list(range(64));rng.shuffle(squares)
        board = ["."] * 64
        board[squares.pop()] = "K";board[squares.pop()] = "k"
        for q in squares[:rng.randrange(63)]:
            board[q] = rng.choice("PNBRQpnbrq")
        positions.append(reference.Position(tuple(board), rng.choice((-1, 1))))
    lines, expected = [], []
    for p in positions:
        own = [q for q, piece in enumerate(p.board) if piece != "." and piece.isupper() == (p.side > 0)]
        targets = [q for q, piece in enumerate(p.board) if piece == "." or piece.isupper() != (p.side > 0)]
        from_sq = rng.choice(own);to_sq = rng.choice(targets)
        piece = p.board[from_sq]
        promotion = rng.choice(".NBRQ") if piece.upper() == "P" else "."
        ep = piece.upper() == "P" and p.board[to_sq] == "." and rng.randrange(3) == 0
        white = reference.evaluate(p)
        assert abs(white) <= 56224
        order = reference.ordering_score(p, from_sq, to_sq, promotion, ep)
        assert abs(order) <= 24940
        from88, to88 = (from_sq//8)*16+from_sq%8, (to_sq//8)*16+to_sq%8
        prom = ".PNBRQK".index(promotion)
        lines.append(f"{p.side} {''.join(p.board)} {from88} {to88} {prom} {to88 if ep else -1}\n")
        expected.append((white, max(-20000, min(20000, white)), order))
    payload = "".join(lines)
    runs = []
    for label, flags in (("optimized", ["-O2"]), ("asan-ubsan", ["-O1", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"])):
        binary = out / ("model-" + label)
        command = ["cc", "-std=c11", "-pthread", "-DDEV=1", *flags, str(harness), "-o", str(binary)]
        subprocess.run(command, check=True, timeout=120)
        result = subprocess.run([str(binary)], input=payload, capture_output=True, text=True, timeout=60)
        if result.returncode or result.stderr:
            raise AssertionError({"returncode": result.returncode, "stderr": result.stderr})
        actual = [tuple(map(int, line.split())) for line in result.stdout.splitlines()]
        if actual != expected:
            first = next((i for i, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1]), min(len(actual), len(expected)))
            raise AssertionError({"first_mismatch": first, "actual": actual[first:first+1], "expected": expected[first:first+1]})
        runs.append({"kind": label, "compile": command, "program_sha256": sha(binary), "cases": len(expected),
                     "raw_evaluation": True, "clamped_evaluation": True, "ordering": True, "cached_hce_poisoned": True})
    return {"producer_dev_source_sha256": sha(dev_source), "harness_sha256": sha(harness),
            "positions": len(positions), "hand_raw_evaluations": [x[0] for x in expected[:7]], "runs": runs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT == args.out or ROOT in args.out.parents:
        parser.error("--out must be new, absolute and outside Git")
    args.out.mkdir(parents=True)
    build = json.loads(args.build.read_bytes())
    variant = build["features"]["variant"]
    dev = next(item for item in build["engines"] if item["profile"] == "dev")
    binary = Path(dev["command"][0])
    if sha(binary) != dev["expected_program_sha256"] or sha(binary.parent / "main.c") != dev["source_sha256"]:
        raise ValueError("production source or executable changed")
    engine = Engine(binary)
    report = {"variant": variant, "passed": False, "build_sha256": sha(args.build), "program_sha256": sha(binary)}
    try:
        engine.send("uci", "uciok")
        engine.send("position startpos\nisready", "readyok")
        engine.send("go depth 4", "bestmove ")
        stats = json.loads(engine.send("stats", "{")[-1])
        if stats["leaf_calls"] <= 0 or stats["pvs"] <= 0 or stats["qs"] <= 0:
            raise AssertionError("actual completed PVS/QS did not consume candidate leaf")
        if variant == "E":
            if stats["ordering_calls"] <= 0:
                raise AssertionError("actual E search did not consume model move ordering")
            model = json.loads((HERE / "frozen.json").read_bytes())
            weights = model["evaluation"]["weights"] + model["ordering"]["weights"]
            actual_weights = list(map(int, engine.send("model", "model ")[-1].split()[1:]))
            if actual_weights != weights:
                raise AssertionError("actual producer coefficients changed")
            reference_dir = args.out / "reference"
            reference_dir.mkdir()
            for name in ("reference.py", "codec.py", "frozen.json"):
                (reference_dir / name).write_bytes((HERE.parents[1] / "model" / name).read_bytes())
            sys.path.insert(0, str(reference_dir))
            load("codec", reference_dir / "codec.py")
            reference = load("tiny_ce_reference", reference_dir / "reference.py")
            fixtures = [
                ("4k3/8/8/8/4P3/8/8/4K3 w - - 0 1", None, 132),
                ("4k3/8/8/4P3/4P3/8/8/4K3 w - - 0 1", None, 248),
                ("4k3/8/8/8/3PP3/8/8/4K3 w - - 0 1", None, 270),
                ("4k3/8/8/8/8/8/8/B3K2B w - - 0 1", None, 694),
                ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "e2e4", 12),
                ("4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1", "e4d5", 14304),
                ("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7a8q", 9602),
                ("1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7b8q", 17504),
                ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "e5d6", 1502),
            ]
            hand = []
            for fen, move, expected in fixtures:
                engine.position(fen)
                prefix = "order " if move else "raw "
                actual = int(engine.send("order " + move if move else "raw", prefix)[-1].split()[1])
                if actual != expected:
                    raise AssertionError({"fen": fen, "move": move, "actual": actual, "expected": expected})
                hand.append({"fen": fen, "move": move, "actual": actual})
            report.update(coefficients=actual_weights, fixtures=hand,
                          reference_inputs={name: sha(reference_dir / name) for name in ("reference.py", "codec.py", "frozen.json")},
                          actual_consumer=actual_model_harness(binary.parent / "main.c", reference, model, args.out))
        elif stats["ordering_calls"]:
            raise AssertionError("C inherited an unintended E ordering path")
        else:
            proof = {}
            shipping = next(item for item in build["engines"] if item["id"] == "tiny-C-original")
            for label, program in (("dev", binary), ("shipping", Path(shipping["command"][0]))):
                assembly = subprocess.check_output(["objdump", "-d", str(program)], text=True)
                counts = {name: len(re.findall(r"\b" + name + r"\b", assembly)) for name in
                          ("vpgatherdd", "vpmulld", "vpsignd", "vphaddd")}
                if not all(counts.values()):
                    raise AssertionError({"actual_production_simd_instructions": counts})
                proof[label] = {"program_sha256": sha(program), "instructions": counts}
            report["actual_production_simd_instructions"] = proof
        engine.close()
        report.update(passed=True, actual_search=stats, transcript=engine.transcript)
    finally:
        engine.terminate()
        (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"variant": variant, "passed": True, "actual_search": stats}))


if __name__ == "__main__":
    main()
