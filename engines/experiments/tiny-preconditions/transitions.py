#!/usr/bin/env python3
"""Bounded DEV=0 precondition parity on untouched frozen shipping functions.

The C translation unit renames only main and includes exact engine.c bytes.
Its test protocol is an instrumented observation surface, not a shipped UCI
extension. Every admitted Board is reached through startpos and validated legal
moves. Arbitrary FEN is never injected into a shipping Board. This is evidence
for the guarded-precondition experiment, not proof by testing or a size claim.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import select
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
CONTROL_SHA = "38d6c829a4d98a172b01c945a20e091bd529a5998174896dbf0ad2dbc01a0a7b"
MASK = (1 << 64) - 1
SPECIAL = {
    "white-ep": "e2e4 a7a6 e4e5 d7d5 e5d6",
    "black-ep": "a2a3 e7e5 a3a4 e5e4 d2d4 e4d3",
    "both-kingside": "e2e4 e7e5 g1f3 b8c6 f1c4 g8f6 e1g1 f8c5 d2d3 e8g8",
    "both-queenside": "d2d4 d7d5 b1c3 b8c6 c1f4 c8f5 d1d2 d8d7 e1c1 e8c8",
    "repetition": "g1f3 g8f6 f3g1 f6g8 " * 3,
}
for _promotion in "nbrq":
    SPECIAL["both-promote-" + _promotion] = ("a2a4 h7h5 a4a5 h5h4 a5a6 h4h3 a6b7 h3g2 "
                                               + "b7a8" + _promotion + " g2h1" + _promotion)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def mix(x):
    x = (x + 0x9E3779B97F4A7C15) & MASK
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & MASK
    return x ^ (x >> 31)


def square88(q):
    return (q // 8) * 16 + q % 8


def ep(board):
    return board.ep if board.ep >= 0 and any(
        m.dst == board.ep and board.cells[m.src].lower() == "p" and m.src % 8 != m.dst % 8
        for m in board.legal_moves()) else -1


def fields(board):
    rights = sum(1 << i for i, right in enumerate("KQkq") if right in board.castling)
    target = ep(board)
    h = mix(2048 + rights) ^ (0 if board.turn else mix(2064))
    if target >= 0:
        h ^= mix(2065 + target % 8)
    total = 0
    for q, piece in enumerate(board.cells):
        if piece == ".":
            continue
        kind, white = "pnbrqk".index(piece.lower()) + 1, piece.isupper()
        v = kind if white else -kind
        h ^= mix(square88(q) + (v + 6) * 128)
        rank, file = divmod(q, 8)
        advance, center = rank if white else 7 - rank, 7 - abs(2 * file - 7) - abs(2 * rank - 7)
        value = (0, 100, 320, 330, 500, 900, 0)[kind]
        value += advance * (7 if kind == 1 else 2 if kind == 4 else 0)
        value += center * (9 if kind == 2 else 5 if kind == 3 else -3 if kind == 6 else 2 if kind in (1, 5) else 0)
        total += value if white else -value
    return {"cells": "".join(board.cells), "side": 1 if board.turn else -1, "castle": rights,
            "ep": -1 if target < 0 else square88(target), "half": board.halfmove,
            "eval": total, "hash": f"{h:016x}"}


def record(board, prior=None):
    data = fields(board)
    h = int(data["hash"], 16)
    context = h if prior is None or not board.halfmove else (
        ((int(prior["context"], 16) << 1) | (int(prior["context"], 16) >> 63)) & MASK) ^ h
    data["context"] = f"{context:016x}"
    data["keys"] = ([] if prior is None else prior["keys"]) + [data["hash"]]
    return data


class Budget:
    def __init__(self, seconds):
        self.end = time.monotonic() + seconds

    def left(self, cap):
        left = min(cap, self.end - time.monotonic())
        if left <= 0:
            raise TimeoutError("aggregate deadline expired")
        return left


class Engine:
    def __init__(self, binary, directory, budget):
        self.budget, self.buffer, self.closed = budget, b"", False
        self.transcript = (directory / "transcript.jsonl").open("w", encoding="utf-8")
        self.stderr = (directory / "stderr.log").open("wb")
        env = dict(os.environ, ASAN_OPTIONS="detect_leaks=1:abort_on_error=1", UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
        self.process = subprocess.Popen([str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.stderr, start_new_session=True, env=env, bufsize=0)

    def command(self, text, timeout=8):
        self.budget.left(timeout)
        self.process.stdin.write((text + "\n").encode("ascii"))
        self.process.stdin.flush()
        deadline = time.monotonic() + self.budget.left(timeout)
        while b"\n" not in self.buffer:
            remain = min(deadline - time.monotonic(), self.budget.left(timeout))
            if remain <= 0 or not select.select([self.process.stdout], [], [], remain)[0]:
                raise TimeoutError(f"command deadline: {text[:180]}")
            data = os.read(self.process.stdout.fileno(), 65536)
            if not data:
                raise RuntimeError(f"harness exited {self.process.poll()} awaiting {text[:180]}")
            self.buffer += data
            require(len(self.buffer) < 1024 * 1024, "unbounded harness response")
        line, self.buffer = self.buffer.split(b"\n", 1)
        result = json.loads(line)
        self.transcript.write(json.dumps({"command": text, "response": result}, sort_keys=True) + "\n")
        self.transcript.flush()
        return result

    def close(self):
        if self.closed:
            return
        self.closed = True
        proc = self.process
        forced = False
        try:
            if proc.poll() is None:
                try:
                    proc.stdin.write(b"Q\n")
                    proc.stdin.flush()
                    proc.stdin.close()
                    proc.wait(timeout=3)
                except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
                    forced = True
        finally:
            # Always address the owned group, including after leader exit.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
                forced = True
            except ProcessLookupError:
                pass
            proc.wait(timeout=3)
            self.transcript.close()
            self.stderr.close()
        require(not forced and proc.returncode == 0 and not self.buffer,
                f"harness cleanup: forced={forced}, exit={proc.returncode}, extra={self.buffer[:100]!r}")


def load_oracle(path):
    spec = importlib.util.spec_from_file_location("preconditions_chess_oracle", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def corpus(oracle, games, plies):
    result = []
    for label, moves in SPECIAL.items():
        result.append((label, moves.split()))
    for game in range(games):
        rng, board, moves = random.Random(20261020 + game), oracle.Board.from_fen(), []
        for _ in range(plies):
            legal = sorted(board.legal_moves(), key=str)
            if not legal:
                break
            move = rng.choice(legal)
            moves.append(str(move))
            board = board.apply(move)
        result.append((f"random-{game}", moves))
    return result


def exercise(engine, oracle, cases, sanitized, ply, budget):
    output = {"snapshots": 0, "child_transitions": 0, "rollbacks": 0, "max_pseudo": 0,
              "cases": [], "search": [], "perft": []}
    signatures = []

    def check(command, board, expected, label):
        budget.left(8)
        actual = engine.command(command)
        for name, value in expected.items():
            require(actual.get(name) == value, f"{label}: {name}: {actual.get(name)!r} != {value!r}")
        wanted = {str(m) for m in board.legal_moves()}
        require(len(actual["legal"]) == len(set(actual["legal"])) and set(actual["legal"]) == wanted,
                f"{label}: legal extra={set(actual['legal'])-wanted}, missing={wanted-set(actual['legal'])}")
        require(actual["count"] == len(actual["pseudo"]) <= 415, f"{label}: pseudo count")
        require(len(set(actual["pseudo"])) == len(actual["pseudo"]), f"{label}: duplicate pseudo moves")
        output["max_pseudo"] = max(output["max_pseudo"], actual["count"])
        output["snapshots"] += 1
        signatures.append(actual)
        return actual

    start = oracle.Board.from_fen()
    start_fields = record(start)
    check("P startpos", start, start_fields, "initial")
    if ply < 128:
        for command in ("S 1", "S 3", "T"):
            result = engine.command(command)
            require(result["best"] in {str(m) for m in start.legal_moves()}, command + ": legal witness")
            require(result["length"] == 1, command + ": restored history")
            if command == "T":
                require(result["stopped"] == 1 and result["depth"] >= 1, "PLY abort retains a completed iteration")
            output["search"].append({"command": command, **result})
            signatures.append(result)
        check("V", start, start_fields, "PLY callback unchanged state")
        return output, sha(json.dumps(signatures, sort_keys=True).encode())

    depth = 3 if sanitized else 4
    perft = engine.command(f"F {depth}", timeout=40)
    require(perft["perft"] == (8902 if depth == 3 else 197281), "startpos perft")
    output["perft"].append({"depth": depth, **perft})
    signatures.append(perft)
    for label, sequence in cases:
        board, expected, played = start, start_fields, []
        for index, name in enumerate(sequence):
            budget.left(8)
            legal = {str(m): m for m in board.legal_moves()}
            require(name in legal, f"invalid test corpus {label}/{index}: {name}; {board.fen()}")
            board = board.apply(legal[name])
            expected = record(board, expected)
            played.append(name)
            check("P startpos moves " + " ".join(played), board, expected, f"{label}/{index}")
        original = check("V", board, expected, label + "/endpoint")
        # All endpoint legal children, each through the actual transactional parser.
        for name, move in sorted(((str(m), m) for m in board.legal_moves())):
            child = board.apply(move)
            child_fields = record(child, expected)
            check("P startpos moves " + " ".join(played + [name]), child, child_fields, label + "/child/" + name)
            output["child_transitions"] += 1
        check("P startpos moves " + " ".join(played), board, expected, label + "/restore")
        for invalid in ("startpos moves e2e5", "startpos moves e2e4 e7e5 a1a8",
                        "startpos moves " + " ".join(played) + " z9z9",
                        "fen " + oracle.START, "fen 8/8/8/8/8/8/8/8 w - - 0 1"):
            observed = engine.command("P " + invalid)
            require(observed == original, f"{label}: invalid transaction changed state: {invalid}")
            output["rollbacks"] += 1
            signatures.append(observed)
        if label in ("white-ep", "both-kingside", "both-queenside", "both-promote-q", "repetition", "random-0"):
            result = engine.command("S 2", timeout=8)
            require(not result["stopped"], label + ": fixed-depth search unexpectedly aborted")
            require(result["length"] == len(expected["keys"]), label + ": search path not restored")
            require(result["best"] in original["legal"] or not original["legal"] and result["best"] == "0000", label + ": legal root witness")
            output["search"].append({"case": label, **result})
            signatures.append(result)
        output["cases"].append({"case": label, "plies": len(sequence), "children": len(original["legal"]),
                                "fen": board.fen(), "context": expected["context"]})
    return output, sha(json.dumps(signatures, sort_keys=True).encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--control-sha", default=CONTROL_SHA)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--oracle", type=Path, default=HERE.parents[1] / "tests" / "chess_oracle.py")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=240)
    parser.add_argument("--random-games", type=int, default=2)
    parser.add_argument("--plies", type=int, default=64)
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists(), "--out must be a new absolute directory")
    require(not any((p / ".git").exists() for p in (out, *out.parents)), "--out must be outside Git")
    require(30 <= args.budget <= 600 and 0 <= args.random_games <= 4 and 1 <= args.plies <= 128, "bounded parameters")
    source_bytes = {"control": args.control.read_bytes(), "specialized": args.candidate.read_bytes()}
    require(sha(source_bytes["control"]) == args.control_sha, "control input identity")
    require(sha(source_bytes["specialized"]) == args.candidate_sha, "candidate input identity")
    out.mkdir(parents=True)
    recipe = out / "recipe"
    recipe.mkdir()
    for name in ("transitions.py", "transitions.c.in"):
        (recipe / name).write_bytes((HERE / name).read_bytes())
    oracle_bytes = args.oracle.read_bytes()
    (recipe / "chess_oracle.py").write_bytes(oracle_bytes)
    if args.manifest:
        (recipe / "build.json").write_bytes(args.manifest.read_bytes())
    for name, data in source_bytes.items():
        (recipe / (name + ".c")).write_bytes(data)
    report = {"passed": False, "scope": "DEV=0 legal-startpos precondition/transition/search parity; not a mathematical proof or release claim",
              "source_sha256": {name: sha(data) for name, data in source_bytes.items()},
              "recipe_sha256": {name: sha((recipe / name).read_bytes()) for name in ("transitions.py", "transitions.c.in", "chess_oracle.py")},
              "manifest_sha256": sha(args.manifest.read_bytes()) if args.manifest else None,
              "configuration": {"dev": 0, "workers": 2, "tt_bits": 18}, "forms": [], "failures": []}
    budget, started, engine, phase = Budget(args.budget), time.monotonic(), None, "oracle"
    try:
        oracle = load_oracle(recipe / "chess_oracle.py")
        report["oracle_self_check"] = oracle.self_check()
        cases = corpus(oracle, args.random_games, args.plies)
        signatures = {}
        for ply in (128, 4):
            for sanitized in (False, True):
                for name in ("control", "specialized"):
                    phase = f"{name}/{'asan' if sanitized else 'opt'}/PLY{ply}"
                    directory = out / name / ("asan" if sanitized else "opt") / ("ply" + str(ply))
                    directory.mkdir(parents=True)
                    (directory / "engine.c").write_bytes(source_bytes[name])
                    (directory / "harness.c").write_bytes((recipe / "transitions.c.in").read_bytes())
                    binary = directory / "harness"
                    command = [args.cc, "-std=c11", "-O2", "-pthread", "-DDEV=0", "-DWORKERS=2", "-DTT_BITS=18", f"-DPLY={ply}"]
                    if sanitized:
                        command += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
                    command += [str(directory / "harness.c"), "-o", str(binary)]
                    item = {"id": phase, "command": command, "passed": False}
                    report["forms"].append(item)
                    compile_started = time.monotonic()
                    with (directory / "compile.log").open("wb") as log:
                        proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                        try:
                            code = proc.wait(timeout=budget.left(35))
                        finally:
                            try:
                                os.killpg(proc.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            proc.wait(timeout=3)
                    item["compile_seconds"], item["compile_exit"] = time.monotonic() - compile_started, code
                    require(code == 0, phase + ": compilation failed; see compile.log")
                    item["binary_sha256"] = sha(binary.read_bytes())
                    item["binary_bytes"] = binary.stat().st_size
                    engine = Engine(binary, directory, budget)
                    result, signature = exercise(engine, oracle, cases, sanitized, ply, budget)
                    engine.close()
                    engine = None
                    item.update(result)
                    item["observation_sha256"] = signature
                    key = (sanitized, ply)
                    if name == "control":
                        signatures[key] = signature
                    else:
                        require(signature == signatures[key], phase + ": actual observations differ from control")
                    item["passed"] = True
        report["passed"] = True
    except BaseException as exc:
        report["failures"].append({"phase": phase, "type": type(exc).__name__, "detail": str(exc)})
    finally:
        if engine is not None:
            try:
                engine.close()
            except BaseException as exc:
                report["failures"].append({"phase": phase + "/cleanup", "type": type(exc).__name__, "detail": str(exc)})
        report["elapsed_seconds"] = time.monotonic() - started
        (out / "results.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "forms": len(report["forms"]), "results": str(out / "results.json"), "failures": report["failures"]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
