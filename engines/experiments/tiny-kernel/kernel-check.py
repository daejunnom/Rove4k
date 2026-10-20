#!/usr/bin/env python3
"""Bounded independent rule and direct-kernel contract checks.

Two O2 profiles are the default. An explicitly requested --asan adds only the
kernel sanitizer profile. All inputs, commands, transcripts and results are
frozen outside the repository. No training, size, NPS or strength claim is made.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import resource
import selectors
import shutil
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ORACLE = ROOT / "engines/tests/chess_oracle.py"
MASK = (1 << 64) - 1
REQUIRED_CHECKS = {"utility_isolation", "stage_partition", "cached_rank", "learned_order",
                   "fresh_order", "stop", "draw", "ply", "positive_algorithms",
                   "ep_correction_exclusion", "halfmove_context"}
SPECIAL = (
    ("castles-white", "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"),
    ("castles-black", "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1"),
    ("castle-origin-white", "k3r3/8/8/8/8/8/8/R3K2R w KQ - 0 1"),
    ("castle-transit-white", "k4r2/8/8/8/8/8/8/R3K2R w KQ - 0 1"),
    ("castle-destination-white", "k5r1/8/8/8/8/8/8/R3K2R w KQ - 0 1"),
    ("castle-origin-black", "r3k2r/8/8/8/8/8/8/K3R3 b kq - 0 1"),
    ("castle-transit-black", "r3k2r/8/8/8/8/8/8/K4R2 b kq - 0 1"),
    ("castle-destination-black", "r3k2r/8/8/8/8/8/8/K5R1 b kq - 0 1"),
    ("ep-white", "6k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1"),
    ("ep-file-pin-white", "4r1k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1"),
    ("ep-rank-pin-white", "8/8/8/r4pPK/8/8/8/7k w - f6 0 1"),
    ("ep-black", "4k3/8/8/8/3Pp3/8/8/6K1 b - d3 0 1"),
    ("ep-file-pin-black", "4k3/8/8/8/3Pp3/8/8/4R1K1 b - d3 0 1"),
    ("ep-rank-pin-black", "7K/8/8/8/R4Ppk/8/8/8 b - f3 0 1"),
    ("all-promotions-white", "r1r4k/1P6/8/8/8/8/8/7K w - - 0 1"),
    ("all-promotions-black", "7k/8/8/8/8/8/1p6/R1R4K b - - 0 1"),
    ("dead-kings", "7k/8/8/8/8/8/8/K7 w - - 0 1"),
    ("dead-one-minor", "7k/8/8/8/8/8/8/KN6 w - - 0 1"),
    ("dead-same-square-colour-bishops", "5b1k/8/3b4/6B1/1b6/4B3/8/K1B5 w - - 0 1"),
    ("live-two-knights", "7k/8/8/8/8/8/8/KNN5 w - - 0 1"),
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_oracle(path):
    spec = importlib.util.spec_from_file_location("frozen_kernel_independent_oracle", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def mix(value):
    value = (value + 0x9E3779B97F4A7C15) & MASK
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK
    return value ^ (value >> 31)


def clean(board):
    # Match the documented admission rule: absent home king/rook removes rights.
    board.castling = "".join(c for c, king, rook in (
        ("K", 4, 7), ("Q", 4, 0), ("k", 60, 63), ("q", 60, 56))
        if c in board.castling and board.cells[king] == ("K" if c.isupper() else "k")
        and board.cells[rook] == ("R" if c.isupper() else "r"))
    return board


def expected(board, path=None):
    """Independent full HCE and FIDE-key recomputation in absolute coordinates."""
    ep = board.repetition_key()[3]
    castle = sum(1 << i for i, letter in enumerate("KQkq") if letter in board.castling)
    key = mix(2048 + castle) ^ (0 if board.turn else mix(2064))
    if ep >= 0:
        key ^= mix(2065 + ep % 8)
    value = 0
    for square, piece in enumerate(board.cells):
        if piece == ".":
            continue
        kind = " pnbrqk".index(piece.lower())
        x, y = square % 8, square // 8
        signed = kind if piece.isupper() else -kind
        key ^= mix(y * 16 + x + (signed + 6) * 128)
        center = 7 - abs(x * 2 - 7) - abs(y * 2 - 7)
        advance = y if piece.isupper() else 7 - y
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


def next_path(path, child):
    key = int(child["h"], 16)
    return key if child["half"] == 0 else (((path << 1) | (path >> 63)) & MASK) ^ key


class Driver:
    def __init__(self, binary, directory):
        self.directory = directory
        self.error_log = (directory / "stderr.log").open("wb")
        self.transcript = (directory / "transcript.jsonl").open("w")
        self.process = subprocess.Popen([str(binary)], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=self.error_log, bufsize=0)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.buffer = b""
        self.cleanup = []

    def ask(self, command, timeout=10):
        self.process.stdin.write((command + "\n").encode())
        self.process.stdin.flush()
        deadline = time.monotonic() + timeout
        while b"\n" not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"unknown: {command}; owned pid {self.process.pid}")
            for key, _ in self.selector.select(min(0.05, remaining)):
                data = os.read(key.fileobj.fileno(), 65536)
                if not data:
                    raise RuntimeError(f"driver exited before {command}: {self.process.poll()}")
                self.buffer += data
        line, self.buffer = self.buffer.split(b"\n", 1)
        response = json.loads(line)
        self.transcript.write(json.dumps({"command": command, "response": response}) + "\n")
        self.transcript.flush()
        return response

    def close(self):
        try:
            if self.process.poll() is None:
                self.process.stdin.write(b"quit\n")
                self.process.stdin.flush()
            code = self.process.wait(timeout=3)
            require(code == 0, f"fixture exit {code}")
            remainder = self.process.stdout.read()
            require(not self.buffer and not remainder,
                    "unsolicited fixture stdout after complete responses")
        except Exception:
            if self.process.poll() is None:
                self.cleanup.append({"unknown_owned_pid_before_cleanup": self.process.pid})
                self.process.terminate()
                try:
                    self.process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    self.cleanup.append({"kill_owned_pid": self.process.pid})
                    self.process.kill()
                    self.process.wait(timeout=1)
            raise
        finally:
            self.selector.close()
            self.error_log.close()
            self.transcript.close()
            for pipe in (self.process.stdin, self.process.stdout):
                if pipe and not pipe.closed:
                    pipe.close()


def audit(driver, board, path, counters):
    report = driver.ask("report")
    wanted = expected(board, path)
    require(report["state"] == wanted, f"state mismatch in {board.fen()}: {report['state']} vs {wanted}")
    attacks = "".join(str(int(board.attacked(q, colour))) for q in range(64) for colour in (True, False))
    require(report["attacks"] == attacks, f"128 pointwise attacks mismatch in {board.fen()}")
    legal = {str(move): move for move in board.legal_moves()}
    children = {entry["move"]: entry["state"] for entry in report["children"]}
    require(len(children) == len(report["children"]), "duplicate legal child")
    require(set(children) == set(legal), f"legal move set mismatch in {board.fen()}")
    for name, move in legal.items():
        child = expected(board.apply(move))
        child["r"] = f"{next_path(path, child):016x}"
        require(children[name] == child, f"child mismatch for {name} in {board.fen()}")
    counters["positions"] += 1
    counters["children"] += len(children)
    counters["pointwise_attacks"] += 128
    return {"state": report["state"], "attacks": report["attacks"],
            "children": sorted(report["children"], key=lambda item: item["move"])}


def profile_checks(driver, oracle, counters, baseline_reports, is_kernel):
    reports = {}
    for index, depth in ((0, 3), (1, 2), (2, 3)):
        name, fen, totals = oracle.PERFT[index]
        require(driver.ask("fen " + fen)["ok"], f"admission failed for {name}")
        board = clean(oracle.Board.from_fen(fen))
        report = audit(driver, board, int(expected(board)["r"], 16), counters)
        reports["perft:" + name] = report
        observed = driver.ask("perft " + str(depth))
        require(observed["nodes"] == totals[depth - 1], f"perft {name}/{depth}: {observed}")
        counters["perft"].append({"name": name, "depth": depth, "expected": totals[depth - 1], **observed})
    for name, fen in SPECIAL:
        response = driver.ask("fen " + fen)
        require(response["ok"], f"admission failed for {name}")
        board = clean(oracle.Board.from_fen(fen))
        path = int(expected(board)["r"], 16)
        reports["special:" + name] = audit(driver, board, path, counters)
        if name.startswith("all-promotions-"):
            prefix = "b7b8" if name.endswith("white") else "b2b1"
            for invalid in (prefix, prefix + "k", prefix + "p"):
                rejected = driver.ask("play " + invalid)
                require(not rejected["ok"] and rejected["state"] == expected(board, path),
                        "invalid promotion changed the admitted board")
                counters["transactional_invalid_moves"] += 1
    rng = random.Random(0x4B45524E)
    require(driver.ask("start")["ok"], "start failed")
    board = oracle.Board.from_fen()
    path = int(expected(board)["r"], 16)
    for ply in range(24):
        reports[f"replay:{ply}"] = audit(driver, board, path, counters)
        legal = sorted(str(move) for move in board.legal_moves())
        require(bool(legal), f"bounded deterministic replay ended early at ply {ply}")
        move = rng.choice(legal)
        board = board.play(move)
        path = next_path(path, expected(board))
        response = driver.ask("play " + move)
        require(response["ok"] and response["state"] == expected(board, path),
                f"replay transition mismatch at ply {ply}")
        counters["replay_plies"] += 1
    if baseline_reports is not None:
        require(reports == baseline_reports, "normalized baseline/kernel board reports differ")
        counters["equal_normalized_reports"] = len(reports)
    if is_kernel:
        proof = driver.ask("selftest", timeout=15)
        require(proof.get("passed") is True, "kernel selftest did not pass")
        checks = proof.get("checks", {})
        require(REQUIRED_CHECKS <= checks.keys(), "kernel selftest omitted required named proof checks")
        require(all(value is True for value in checks.values()), "kernel named proof check failed")
        positive = ("root_runs", "root_legal_observations", "snapshot_descendant_updates",
                    "pvs", "qs", "tt_hits", "correction_updates", "correction_uses")
        for name in positive:
            require(type(proof.get(name)) is int and proof[name] > 0,
                    f"kernel selftest must retain positive actual count: {name}")
        require(proof["root_runs"] == 10, "kernel fixture must retain its ten bounded root runs")
        require(proof.get("fresh_root_moves") == 20, "fresh order must cover all twenty start moves")
        require(type(proof.get("tactical_fixture_moves")) is int and proof["tactical_fixture_moves"] >= 13,
                "tactical fixture must include twelve promotions and one en passant")
        require(type(proof.get("learned_history")) is int and proof["learned_history"] >= 36,
                "actual depth-six quiet cutoff must train history")
        require(type(proof.get("learned_continuation")) is int and proof["learned_continuation"] >= 36,
                "actual depth-six quiet cutoff must train continuation")
        require(type(proof.get("other_quiet_continuation_rank")) is int and
                proof["other_quiet_continuation_rank"] >= 32,
                "another quiet move must cross the learned stage threshold")
        require(type(proof.get("fresh_score")) is int and proof["fresh_score"] > 0 and
                proof.get("half99_score") == 0,
                "fresh and halfmove-99 searches must retain distinct expected outcomes")
        counters["kernel_selftest"] = proof
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, default=HERE / "kernel-contract.c")
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--asan", action="store_true", help="explicitly add the kernel ASAN/UBSAN profile")
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("POSIX selectors and resource limits are required; use WSL Ubuntu")
    output = args.out.resolve()
    if not args.out.is_absolute() or output.exists() or output == ROOT or ROOT in output.parents:
        parser.error("--out must be a new absolute external directory")
    if not args.baseline.is_absolute() or not args.kernel.is_absolute():
        parser.error("--baseline and --kernel must name absolute frozen source files")
    paths = {"baseline.c": args.baseline, "kernel.c": args.kernel,
             "kernel-contract.c": args.fixture, "chess_oracle.py": ORACLE,
             "kernel-check.py": Path(__file__)}
    if any(not path.is_file() for path in paths.values()):
        parser.error("both assembled sources, fixture, oracle and harness must exist")
    output.mkdir(parents=True)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    frozen = output / "frozen"
    frozen.mkdir()
    for name, path in paths.items():
        shutil.copyfile(path, frozen / name)
    oracle = load_oracle(frozen / "chess_oracle.py")
    result = {"scope": "bounded independent board and actual direct-kernel contracts; no adoption/4K/performance claim",
              "source_origin": {name: str(path.resolve()) for name, path in paths.items()},
              "source_sha256": {name: sha(frozen / name) for name in paths},
              "fixed_profile": {"workers": 2, "tt_bits": 18, "dev": 1},
              "special_fens": len(SPECIAL), "replay_plies_per_profile": 24,
              "profiles": [], "all_passed": False}
    profiles = [("baseline-o2", "baseline.c", False, False), ("kernel-o2", "kernel.c", True, False)]
    if args.asan:
        profiles.append(("kernel-asan", "kernel.c", True, True))
    baseline_reports = None
    for name, source_name, is_kernel, sanitized in profiles:
        directory = output / name
        directory.mkdir()
        flags = (["-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie"]
                 if sanitized else ["-O2"])
        command = [args.cc, "-std=c11", "-DDEV=1", f"-DKERNEL={int(is_kernel)}", "-DWORKERS=2", "-DTT_BITS=18",
                   "-pthread", "-Wall", "-Wextra", *flags, f'-DENGINE_SOURCE="{frozen / source_name}"',
                   str(frozen / "kernel-contract.c"), "-o", str(directory / "contract")]
        counters = {"name": name, "passed": False, "positions": 0, "children": 0,
                    "pointwise_attacks": 0, "perft": [], "transactional_invalid_moves": 0,
                    "replay_plies": 0, "equal_normalized_reports": 0, "compile_command": command}
        result["profiles"].append(counters)
        began = time.monotonic()
        driver = None
        try:
            compiled = subprocess.run(command, capture_output=True, timeout=60)
            (directory / "compile.stdout.log").write_bytes(compiled.stdout)
            (directory / "compile.stderr.log").write_bytes(compiled.stderr)
            counters["compile_returncode"] = compiled.returncode
            require(compiled.returncode == 0, f"compile {name} failed")
            counters["program_sha256"] = sha(directory / "contract")
            driver = Driver(directory / "contract", directory)
            reports = profile_checks(driver, oracle, counters, baseline_reports, is_kernel)
            driver.close()
            counters["exit_code"] = driver.process.returncode
            require(not (directory / "stderr.log").read_bytes(), "fixture or sanitizer wrote stderr")
            if not is_kernel:
                baseline_reports = reports
            counters["passed"] = True
        except Exception as failure:
            counters["error"] = f"{type(failure).__name__}: {failure}"
            if driver is not None and not driver.error_log.closed:
                try:
                    driver.close()
                except Exception as closing:
                    counters["close_error"] = f"{type(closing).__name__}: {closing}"
            if driver is not None:
                counters["exit_code"] = driver.process.returncode
        finally:
            counters["cleanup"] = driver.cleanup if driver is not None else []
            counters["seconds"] = round(time.monotonic() - began, 6)
            (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(counters), flush=True)
    result["all_passed"] = all(profile["passed"] for profile in result["profiles"])
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    raise SystemExit(0 if result["all_passed"] else 1)


if __name__ == "__main__":
    main()
