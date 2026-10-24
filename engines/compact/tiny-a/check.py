#!/usr/bin/env python3
"""Focused contracts beyond the shared external chess oracle; reports external.

The common engines/tests/verify.py remains the independent rule/protocol gate.
This checks actual algorithm counters and context-sensitive TT behavior through
the optional candidate's development UCI interface.
"""
import argparse
import hashlib
import json
from pathlib import Path
import queue
import subprocess
import threading


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cap-engine", type=Path, help="optional DEV build compiled with PLY=4")
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists():
        parser.error("--out must be a new absolute file outside the checkout")
    process = subprocess.Popen([str(args.engine)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    lines = queue.Queue()
    def read():
        for line in process.stdout:
            lines.put(line.strip())
    thread = threading.Thread(target=read, daemon=True)
    thread.start()
    transcript = []
    def send(command):
        transcript.append({"stdin": command})
        process.stdin.write(command + "\n")
        process.stdin.flush()
    def until(prefix):
        seen = []
        while True:
            line = lines.get(timeout=10)
            seen.append(line)
            transcript.append({"stdout": line})
            if line.startswith(prefix):
                return seen
    try:
        send("uci")
        until("uciok")
        send("position startpos")
        for _ in range(2):
            send("go depth 4")
            until("bestmove ")
        send("stats")
        stats = json.loads(until("{")[-1])
        for key in ("pvs", "qs", "tt_hits", "history_updates", "continuation_updates", "correction_updates", "correction_uses"):
            if stats[key] <= 0:
                raise AssertionError(f"actual algorithm branch not observed: {key}={stats[key]}")
        positions = ("7k/8/8/8/8/8/1Q6/K7 w - - 99 1", "7k/8/8/8/8/8/1Q6/K7 w - - 0 1")
        scores = []
        for fen in positions:
            send("position fen " + fen)
            send("go depth 3")
            replies = until("bestmove ")
            info = [line.split() for line in replies if line.startswith("info ")][-1]
            if info[info.index("score") + 1] != "cp":
                raise AssertionError("unexpected mate in context fixture")
            scores.append(int(info[info.index("score") + 2]))
        if scores[0] != 0 or scores[1] <= 0:
            raise AssertionError(f"halfmove-sensitive context contaminated TT: {scores}")
        send("stats")
        before_ep = json.loads(until("{")[-1])["correction_updates"]
        send("position fen 6k1/8/8/3pP3/8/8/8/6K1 w - d6 0 1")
        send("go depth 1")
        if until("bestmove ")[-1] != "bestmove e5d6":
            raise AssertionError("EP correction fixture did not select its winning capture")
        send("stats")
        after_ep = json.loads(until("{")[-1])["correction_updates"]
        if after_ep != before_ep:
            raise AssertionError("quiet-only correction learned from an en-passant capture")
        material = (
            ("kings", "7k/8/8/8/8/8/8/K7 w - - 0 1", True),
            ("one bishop", "7k/8/8/8/8/8/1B6/K7 w - - 0 1", True),
            ("one knight", "7k/8/8/8/8/8/1N6/K7 w - - 0 1", True),
            ("same-colour bishops", "7k/8/5b2/8/8/8/1B6/K7 w - - 0 1", True),
            ("opposite bishops", "7k/8/8/5b2/8/8/1B6/K7 w - - 0 1", False),
            ("two knights", "7k/8/8/8/8/8/1NN5/K7 w - - 0 1", False),
            ("knight each", "7k/8/5n2/8/8/8/1N6/K7 w - - 0 1", False),
            ("bishop knight", "7k/8/5n2/8/8/8/1B6/K7 w - - 0 1", False),
            ("rook", "7k/8/8/8/8/8/1R6/K7 w - - 0 1", False),
            ("pawn", "7k/8/8/8/8/8/1P6/K7 w - - 0 1", False),
        )
        material_results = []
        for label, fen, expected in material:
            send("position fen " + fen)
            send("state")
            state = json.loads(until("{")[-1])
            if state["draw"] is not expected:
                raise AssertionError(f"insufficient material mismatch: {label}: {state}")
            if expected:
                send("go depth 3")
                info = [line for line in until("bestmove ") if line.startswith("info ")][-1]
                if "score cp 0 " not in info:
                    raise AssertionError(f"dead root was searched as a winning position: {info}")
            material_results.append({"case": label, "draw": expected})
        send("quit")
        process.wait(timeout=3)
        if process.returncode:
            raise AssertionError("development engine failed shutdown")
        cap = None
        if args.cap_engine:
            thread.join(timeout=1)
            lines = queue.Queue()
            process = subprocess.Popen([str(args.cap_engine)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            thread = threading.Thread(target=read, daemon=True)
            thread.start()
            send("position startpos")
            send("go depth 2")
            replies = until("bestmove ")
            send("stats")
            cap = json.loads(until("{")[-1])
            if cap["ply_aborts"] < 1 or cap["completed_depth"] != 1 or replies[-1].endswith("0000"):
                raise AssertionError(f"ply cap lost or mislabeled completed witness: {cap}, {replies}")
            send("quit")
            process.wait(timeout=3)
            if process.returncode:
                raise AssertionError("ply cap fixture failed shutdown")
        report = {"passed": True, "engine": str(args.engine), "sha256": hashlib.sha256(args.engine.read_bytes()).hexdigest(),
                  "stats": stats, "halfmove_context_scores": scores, "material": material_results,
                  "ep_correction_updates": [before_ep, after_ep], "ply_cap": cap, "transcript": transcript}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"passed": True, "stats": stats, "halfmove_context_scores": scores}))
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
