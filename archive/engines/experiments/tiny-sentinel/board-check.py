#!/usr/bin/env python3
"""Bounded independent contract checks; all compilers/results stay outside Git.

CONTROLLED=1 must reproduce the signed 0x88 board's entire normalized report,
including ordered legal children and h/r. CONTROLLED=0 uses an independently
recomputed native hash; no equality to the old hash is asserted for that form.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import resource
import select
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location("sentinel_independent_oracle", ROOT / "engines/tests/chess_oracle.py")
oracle = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = oracle
spec.loader.exec_module(oracle)
MASK = (1 << 64) - 1


def mix(value):
    value = (value + 0x9E3779B97F4A7C15) & MASK
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK
    return value ^ (value >> 31)


def clean(board):
    board.castling = "".join(c for c, king, rook in (
        ("K", 4, 7), ("Q", 4, 0), ("k", 60, 63), ("q", 60, 56))
        if c in board.castling and board.cells[king] == ("K" if c.isupper() else "k")
        and board.cells[rook] == ("R" if c.isupper() else "r"))
    return board


def expected(board, controlled, path=None):
    ep = board.repetition_key()[3]
    castle = sum(1 << i for i, c in enumerate("KQkq") if c in board.castling)
    key = mix(2048 + castle) ^ (0 if board.turn else mix(2064))
    if ep >= 0:
        key ^= mix(2065 + ep % 8)
    value = 0
    for index, piece in enumerate(board.cells):
        if piece == ".":
            continue
        kind = " pnbrqk".index(piece.lower())
        x, y = index % 8, index // 8
        signed = kind if piece.isupper() else -kind
        domain = y * 16 + x + (signed + 6) * 128 if controlled else 21 + x + y * 10 + (kind | (8 if piece.isupper() else 16)) * 128
        key ^= mix(domain)
        center, advance = 7 - abs(x * 2 - 7) - abs(y * 2 - 7), y if piece.isupper() else 7 - y
        score = (0, 100, 320, 330, 500, 900, 0)[kind]
        if kind == 1:
            score += advance * 7 + center * 2
        elif kind == 2:
            score += center * 9
        elif kind == 3:
            score += center * 5
        elif kind == 4:
            score += advance * 2
        elif kind == 5:
            score += center * 2
        else:
            score -= center * 3
        value += score if piece.isupper() else -score
    minors = [(i, p.lower()) for i, p in enumerate(board.cells) if p.lower() in "nb"]
    majors = any(p.lower() in "prq" for p in board.cells)
    dead = not majors and (len(minors) <= 1 or all(p == "b" for _, p in minors)
                          and len({(i % 8 + i // 8) % 2 for i, _ in minors}) <= 1)
    return {"cells": "".join(board.cells), "side": int(not board.turn), "castle": castle,
            "ep": -1 if ep < 0 else ep // 8 * 16 + ep % 8,
            "kings": [board.cells.index(p) // 8 * 16 + board.cells.index(p) % 8 for p in ("K", "k")],
            "half": board.halfmove, "v": value, "h": f"{key:016x}",
            "r": f"{key if path is None else path:016x}", "dead": int(dead)}


def next_path(before, child):
    key = int(child["h"], 16)
    return key if child["half"] == 0 else (((before << 1) | (before >> 63)) & MASK) ^ key


class Driver:
    def __init__(self, path, log):
        self.log = log.open("w")
        self.process = subprocess.Popen([str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.log, text=True, bufsize=1)

    def ask(self, command):
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()
        ready, _, _ = select.select([self.process.stdout], [], [], 60)
        if not ready:
            raise TimeoutError(command)
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(f"driver stopped for {command}: {self.process.poll()}")
        return json.loads(line)

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.write("quit\n")
            self.process.stdin.flush()
        code = self.process.wait(timeout=10)
        self.log.close()
        assert code == 0, code


def audit(driver, board, controlled, path, counters):
    report = driver.ask("report")
    wanted = expected(board, controlled, path)
    assert report["state"] == wanted, (report["state"], wanted, board.fen())
    attack_bits = "".join(str(int(board.attacked(q, colour))) for q in range(64) for colour in (True, False))
    assert report["attacks"] == attack_bits
    legal = {str(move): move for move in board.legal_moves()}
    children = {entry["move"]: entry["state"] for entry in report["children"]}
    assert len(children) == len(report["children"]) and set(children) == set(legal), board.fen()
    for name, move in legal.items():
        child_board = board.apply(move)
        child = expected(child_board, controlled)
        child["r"] = f"{next_path(path, child):016x}"
        assert children[name] == child, (name, children[name], child, board.fen())
    counters["positions"] += 1
    counters["children"] += len(children)
    counters["pointwise_attacks"] += 128
    return report


SPECIAL = [
    "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1",
    *[f"{row}/8/8/8/8/8/8/R3K2R w KQ - 0 1" for row in ("k3r3", "k4r2", "k5r1", "k2r4", "k1r5")],
    *[f"r3k2r/8/8/8/8/8/8/{row} b kq - 0 1" for row in ("K3R3", "K4R2", "K5R1", "K2R4", "K1R5")],
    "6k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "4r1k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
    "8/8/8/r4pPK/8/8/8/7k w - f6 0 1", "4r1k1/8/8/2PpP3/8/8/8/4K3 w - d6 0 1",
    "4k3/8/8/8/3Pp3/8/8/6K1 b - d3 0 1", "4k3/8/8/8/3Pp3/8/8/4R1K1 b - d3 0 1",
    "7K/8/8/8/R4Ppk/8/8/8 b - f3 0 1", "4k3/8/8/8/2pPp3/8/8/4R1K1 b - d3 0 1",
    "r1r4k/1P6/8/8/8/8/8/7K w - - 0 1", "7k/8/8/8/8/8/1p6/R1R4K b - - 0 1",
    "4k3/8/8/8/8/8/8/4K3 w KQ - 0 1",
    "3Q2rk/3Q2pp/QQ1Q1Q1Q/3Q4/QQ1Q1Q1Q/3Q4/3Q4/K7 w - - 0 1",
    "7k/8/8/8/8/8/8/K7 w - - 0 1", "7k/8/8/8/8/8/8/KN6 w - - 0 1",
    "7k/8/8/8/8/8/8/K1B5 w - - 0 1", "5b1k/8/3b4/6B1/1b6/4B3/8/K1B5 w - - 0 1",
    "7k/8/8/8/8/8/8/KNN5 w - - 0 1", "6nk/8/8/8/8/8/8/KN6 w - - 0 1",
    "6bk/8/8/8/8/8/8/K1B5 w - - 0 1", "7k/8/8/8/8/8/8/KNB5 w - - 0 1",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--frozen", type=Path)
    parser.add_argument("--plies", type=int, default=96)
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT == args.out or ROOT in args.out.parents:
        parser.error("--out must be a new absolute directory outside the checkout")
    if not 0 <= args.plies <= 1024:
        parser.error("--plies must be 0..1024")
    args.out.mkdir(parents=True)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    old = args.frozen / "baseline/board.c" if args.frozen else ROOT / "engines/compact/tiny-a/board-generated.c.in"
    new = args.frozen / "sentinel/board.c" if args.frozen else HERE / "board.c"
    sources = [old, old.parent / "tiny.h", new, new.parent / "tiny.h", HERE / "board-contract.c", Path(__file__), Path(oracle.__file__)]
    result = {"source_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
              "frozen": str(args.frozen) if args.frozen else None, "profiles": [], "controlled_equal_reports": 0}
    profiles = [("baseline", old, 0, 1, False), ("controlled", new, 1, 1, False),
                ("native", new, 1, 0, False), ("controlled-asan", new, 1, 1, True), ("native-asan", new, 1, 0, True)]
    built = []
    for name, source, sentinel, controlled, sanitized in profiles:
        target = args.out / name
        flags = ["-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"] if sanitized else ["-O2"]
        command = [args.cc, "-std=c11", "-DDEV=1", f"-DSENTINEL={sentinel}", f"-DCONTROLLED={controlled}",
                   f'-DBOARD_SOURCE="{source}"', "-I", str(source.parent), "-Wall", "-Wextra", *flags,
                   str(HERE / "board-contract.c"), "-o", str(target)]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (args.out / (name + "-compile.log")).write_text(completed.stdout + completed.stderr)
        assert completed.returncode == 0, completed.stderr
        built.append((name, target, controlled, sanitized))
    controlled_reports = {}
    for name, target, controlled, sanitized in built:
        began = time.monotonic()
        counters = {"name": name, "positions": 0, "children": 0, "pointwise_attacks": 0, "perft": []}
        driver = Driver(target, args.out / (name + "-stderr.log"))
        try:
            assert driver.ask("random-attacks") == {"attack_queries": 131072}
            counters["random_attack_queries"] = 131072
            assert driver.ask("inventory-invariant")["ok"] and driver.ask("border-invariant")["ok"]
            for label, fen, totals in oracle.PERFT:
                assert driver.ask("fen " + fen)["ok"]
                observed = driver.ask("perft " + str(len(totals)))
                assert observed["nodes"] == totals[-1], (name, label, observed)
                counters["perft"].append({"position": label, **observed})
            for index, fen in enumerate([entry[1] for entry in oracle.PERFT] + SPECIAL):
                board = clean(oracle.Board.from_fen(fen))
                assert driver.ask("fen " + fen)["ok"]
                path = int(expected(board, controlled)["r"], 16)
                report = audit(driver, board, controlled, path, counters)
                key = ("fixture", index)
                if name == "baseline":
                    controlled_reports[key] = report
                elif name == "controlled":
                    assert report == controlled_reports[key]
                    result["controlled_equal_reports"] += 1
            for fen in ("7k/8/8/8/8/PPPPPPPP/PPPPPPPP/K7 w - - 0 1", "7k/pppppppp/pppppppp/8/8/8/8/K7 w - - 0 1"):
                before = driver.ask("report")["state"]
                response = driver.ask("fen " + fen)
                assert not response["ok"] and response["state"] == before
            rng = random.Random(0x524F5645)
            remaining = min(args.plies, 24) if sanitized else args.plies
            for game in range(3):
                board = oracle.Board.from_fen();driver.ask("start")
                path = int(expected(board, controlled)["r"], 16)
                for ply in range((remaining + 2 - game) // 3):
                    report = audit(driver, board, controlled, path, counters)
                    key = ("replay", game, ply)
                    if name == "baseline":
                        controlled_reports[key] = report
                    elif name == "controlled":
                        assert report == controlled_reports[key]
                        result["controlled_equal_reports"] += 1
                    legal = sorted(str(move) for move in board.legal_moves())
                    if not legal:
                        break
                    move = rng.choice(legal);board = board.play(move)
                    child = expected(board, controlled);path = next_path(path, child)
                    response = driver.ask("play " + move)
                    assert response["ok"] and response["state"] == expected(board, controlled, path)
        finally:
            driver.close()
        assert not (args.out / (name + "-stderr.log")).read_text()
        guard = subprocess.run([str(target), "--overflow"], capture_output=True, text=True, timeout=10)
        assert guard.returncode == -signal.SIGABRT, (name, guard.returncode, guard.stderr)
        counters["overflow_code"] = guard.returncode
        counters["seconds"] = time.monotonic() - began
        result["profiles"].append(counters)
        (args.out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(counters), flush=True)
    result["passed"] = True
    (args.out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": True, "controlled_equal_reports": result["controlled_equal_reports"], "out": str(args.out)}))


if __name__ == "__main__":
    main()
