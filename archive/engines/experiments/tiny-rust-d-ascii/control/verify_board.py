#!/usr/bin/env python3
"""Qualify exact Tiny Rust D board bodies through NONSHIPPING std test images.

The two images include the same frozen production board.rs. They do not test
the custom no_std entry/thread/syscall ABI or establish shipping acceptance.
"""

if __name__ == "__main__":
    raise SystemExit("Rove4k Rust engine paths are retired; use C A-F")

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import random
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXPECTED_BOARD = "f27472ea055b67e61cdd82a3d7747feced50c899bef72365ffdc940043dedef3"
MASK = (1 << 64) - 1


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run(command, *, cwd, env, timeout, data=None, driver=False):
    start = time.monotonic()
    process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(data, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
    record = {"command": list(map(str, command)), "cwd": str(cwd), "returncode": process.returncode,
              "timed_out": timed_out, "terminal": True, "elapsed_seconds": time.monotonic() - start,
              "stdout_bytes": len(stdout), "stderr": stderr.decode(errors="replace"),
              "image_class": "nonshipping-std-board-driver" if driver else "test-image-compiler"}
    return record, stdout


def load_oracle(path):
    spec = importlib.util.spec_from_file_location("tiny_d_frozen_board_oracle", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def mix(x):
    x = (x + 0x9e3779b97f4a7c15) & MASK
    x = ((x ^ (x >> 30)) * 0xbf58476d1ce4e5b9) & MASK
    x = ((x ^ (x >> 27)) * 0x94d049bb133111eb) & MASK
    return x ^ (x >> 31)


def expected(board):
    cells, score, key, bb, kings = "", 0, 0, [[0] * 7 for _ in range(2)], [0, 0]
    minors, knights, colours = 0, 0, set()
    dead = True
    for q, piece in enumerate(board.cells):
        cells += piece
        if piece == ".":
            continue
        kind = " pnbrqk".index(piece.lower())
        side = int(piece.islower())
        signed = -kind if side else kind
        file, rank = q % 8, q // 8
        square = rank * 16 + file
        key ^= mix(square + (signed + 6) * 128)
        bb[side][0] |= 1 << q
        bb[side][kind] |= 1 << q
        if kind == 6:
            kings[side] = square
        advance = 7 - rank if side else rank
        centre = 7 - abs(2 * file - 7) - abs(2 * rank - 7)
        position = (0, advance * 7 + centre * 2, centre * 9, centre * 5,
                    advance * 2, centre * 2, -centre * 3)[kind]
        magnitude = (0, 100, 320, 330, 500, 900, 0)[kind] + position
        score += -magnitude if side else magnitude
        if kind in (1, 4, 5):
            dead = False
        elif kind == 2:
            minors += 1
            knights += 1
        elif kind == 3:
            minors += 1
            colours.add((rank + file) & 1)
    castle = sum(mask for c, mask in zip("KQkq", (1, 2, 4, 8)) if c in board.castling)
    ep64 = board.repetition_key()[3]
    ep = -1 if ep64 < 0 else ep64 // 8 * 16 + ep64 % 8
    key ^= mix(2048 + castle)
    if not board.turn:
        key ^= mix(2064)
    if ep >= 0:
        key ^= mix(2065 + (ep & 7))
    return {"cells": cells, "side": 1 if board.turn else -1, "castle": castle, "ep": ep,
            "halfmove": min(board.halfmove, 65535), "king": kings, "hash": f"{key:016x}",
            "score": score, "bb": bb, "check": board.in_check(),
            "dead": dead and (minors < 2 or knights == 0 and len(colours) <= 1)}


def check_state(actual, board, context, *, attacks=False):
    want = expected(board)
    for name, value in want.items():
        assert actual[name] == value, {"field": name, "actual": actual[name], "expected": value, "fen": board.fen()}
    assert actual["context"] == f"{context:016x}"
    assert actual["rebuild_coherent"] is True
    if attacks:
        masks = []
        for colour in (True, False):
            mask = sum(1 << q for q in range(64) if board.attacked(q, colour))
            masks.append(f"{mask:016x}")
        assert actual["attacked_scalar"] == masks
        assert actual["attacked_hq"] == masks


def replay(oracle, fen, names):
    board = oracle.Board.from_fen(fen)
    context = int(expected(board)["hash"], 16)
    keys = [context]
    for name in names:
        board = board.play(name)
        key = int(expected(board)["hash"], 16)
        context = key if board.halfmove == 0 else mix(context ^ key)
        keys.append(key)
    return board, context, keys


def fixtures(oracle):
    probes = [(name, fen, []) for name, fen, _ in oracle.PERFT]
    special = (
        ("pinned-ep-rank", "k7/8/8/r4pPK/8/8/8/8 w - f6 0 1"),
        ("legal-ep", "k7/8/8/5pP1/8/8/8/7K w - f6 0 1"),
        ("ep-both-sources", "4k3/8/8/2PpP3/8/8/8/4K3 w - d6 0 1"),
        ("white-promotions", "7k/P7/8/8/8/8/8/7K w - - 0 1"),
        ("black-promotions", "7k/8/8/8/8/8/p7/7K b - - 0 1"),
        ("capture-promotions", "1r5k/P7/8/8/8/8/8/7K w - - 0 1"),
        ("castle-all", "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"),
        ("castle-attacked-transit", "r3k2r/8/8/8/8/5r2/8/R3K2R w KQkq - 0 1"),
        ("castle-attacked-target", "r3k2r/8/8/8/8/6r1/8/R3K2R w KQkq - 0 1"),
        ("half99", "7k/8/8/8/8/8/8/KR6 w - - 99 1"),
        ("half100", "7k/8/8/8/8/8/8/KR6 w - - 100 1"),
        ("half-saturation", "7k/8/8/8/8/8/8/KR6 w - - 65535 1"),
        ("bare-kings", "7k/8/8/8/8/8/8/K7 w - - 0 1"),
        ("one-knight", "7k/8/8/8/8/8/8/KN6 w - - 0 1"),
        ("two-knights", "7k/8/8/8/8/8/8/KNN5 w - - 0 1"),
        ("opposed-knights", "6nk/8/8/8/8/8/8/KN6 w - - 0 1"),
        ("same-bishops", "7k/8/8/8/8/8/7b/K1B5 w - - 0 1"),
        ("opposite-bishops", "7k/8/8/8/8/8/6b1/K1B5 w - - 0 1"),
        ("stalemate", "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"),
        ("mate", "7k/6Q1/6K1/8/8/8/8/8 b - - 100 1"),
    )
    probes += [(name, fen, []) for name, fen in special]
    cycle = ["g1f3", "g8f6", "f3g1", "f6g8"]
    for n in (1, 4, 8, 12):
        probes.append((f"repetition-{n}", oracle.START, (cycle * 3)[:n]))
    probes.append(("context-pawn-reset", oracle.START, cycle * 2 + ["e2e4"]))
    probes.append(("context-capture-reset", oracle.START, ["e2e4", "d7d5", "e4d5"]))
    rng = random.Random(0xD4B04D)
    for game in range(4):
        board, names = oracle.Board.from_fen(), []
        for ply in range(48):
            choices = list(board.legal_moves())
            if not choices:
                break
            move = rng.choice(choices)
            names.append(str(move))
            board = board.apply(move)
            if ply % 2 == 1:
                probes.append((f"random-{game}-{ply + 1}", oracle.START, list(names)))
    return probes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rustc", default="rustc")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    if sys.platform != "linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        parser.error("Linux x86-64 qualification required")
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or out == ROOT or ROOT in out.parents:
        parser.error("new absolute output outside checkout required")
    if not 1 <= args.timeout <= 180:
        parser.error("timeout must be1..180seconds per process")
    compiler = shutil.which(args.rustc)
    if compiler is None:
        parser.error("Rust compiler unavailable")
    sources = {"board.rs": (HERE / "board.rs").read_bytes(), "tests/board.rs": (HERE / "tests/board.rs").read_bytes(),
               "verify_board.py": Path(__file__).read_bytes(), "oracle.py": (ROOT / "engines/tests/chess_oracle.py").read_bytes()}
    out.mkdir()
    report = {"passed": False, "image_class": "nonshipping-std-board-qualification",
              "shipping_abi_tested": False, "fixed_profile": {"workers": 2, "tt_bits": 18},
              "input_sha256": {name: sha(data) for name, data in sources.items()}, "lanes": {}}
    try:
        assert sha(sources["board.rs"]) == EXPECTED_BOARD, "production board changed: audit/rebind before qualification"
        frozen = out / "input"
        for name, data in sources.items():
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        oracle = load_oracle(frozen / "oracle.py")
        report["oracle_self_check"] = oracle.self_check()
        probes = fixtures(oracle)
        commands = ["hq\t2174920037\t512"]
        perfts = []
        for label, fen, totals in oracle.PERFT:
            for depth, count in enumerate(totals, 1):
                name = f"{label}-{depth}"
                commands.append(f"perft\t{name}\t{fen}\t{depth}")
                perfts.append((name, count))
        for label, fen, names in probes:
            commands.append(f"probe\t{label}\t{fen}\t{' '.join(names)}")
        request = ("\n".join(commands) + "\n").encode()
        (out / "requests.txt").write_bytes(request)
        flags = ["--edition=2024", "--crate-name", "tiny_d_board_qualification", "-C", "opt-level=z", "-C", "lto=fat", "-C", "codegen-units=1", "-C", "panic=abort", "--check-cfg", "cfg(board_test_hq)"]
        fixed = {"ROVE_WORKERS": "2", "ROVE_TT_BITS": "18", "LC_ALL": "C", "TZ": "UTC", "SOURCE_DATE_EPOCH": "0"}
        version_env = os.environ.copy()
        version_env.update(fixed)
        version, text = run([compiler, "--version", "--verbose"], cwd=frozen, env=version_env, timeout=args.timeout)
        version["stdout"] = text.decode(errors="replace")
        report["rustc"] = version
        assert version["returncode"] == 0 and not version["timed_out"]
        previous = None
        for lane in ("scalar", "hq"):
            folder = out / lane
            folder.mkdir()
            binary = folder / "driver"
            env = os.environ.copy()
            env.update(fixed, ROVE_HQ=str(int(lane == "hq")))
            command = [compiler, "--remap-path-prefix", str(frozen) + "=.", *flags,
                       *(["--cfg", "board_test_hq"] if lane == "hq" else []), str(frozen / "tests/board.rs"), "-o", str(binary)]
            compile_record, stdout = run(command, cwd=frozen, env=env, timeout=args.timeout)
            save(folder / "compile.json", compile_record)
            (folder / "compile.stdout").write_bytes(stdout)
            assert compile_record["returncode"] == 0 and not compile_record["timed_out"], compile_record
            native = binary.read_bytes()
            lane_report = {"compiler": compile_record, "binary_sha256": sha(native), "binary_bytes": len(native), "fixed_env": {**fixed, "ROVE_HQ": env["ROVE_HQ"]}}
            report["lanes"][lane] = lane_report
            execution, output = run([str(binary)], cwd=folder, env=env, timeout=args.timeout, data=request, driver=True)
            save(folder / "execution.json", execution)
            (folder / "responses.jsonl").write_bytes(output)
            lane_report["execution"] = execution
            assert execution["returncode"] == 0 and not execution["timed_out"], execution
            responses = [json.loads(line) for line in output.splitlines()]
            assert len(responses) == len(commands)
            assert responses[0] == {"kind": "hq", "cases": 64 * 2 * (512 + 68) * 2}
            at = 1
            for name, count in perfts:
                assert responses[at] == {"kind": "perft", "id": name, "nodes": count}, responses[at]
                at += 1
            transitions = 0
            for label, fen, names in probes:
                actual = responses[at]
                at += 1
                assert actual["kind"] == "probe" and actual["id"] == label
                board, context, keys = replay(oracle, fen, names)
                check_state(actual["position"], board, context, attacks=True)
                assert actual["repetition"] == keys.count(int(expected(board)["hash"], 16))
                legal = {str(move): move for move in board.legal_moves()}
                assert len(actual["legal"]) == len(legal)
                assert {entry["move"] for entry in actual["legal"]} == set(legal), label
                for entry in actual["legal"]:
                    move = legal[entry["move"]]
                    child = board.apply(move)
                    key = int(expected(child)["hash"], 16)
                    child_context = key if child.halfmove == 0 else mix(context ^ key)
                    check_state(entry["state"], child, child_context)
                    assert entry["capture"] == (board.cells[move.dst] != "." or board.cells[move.src].lower() == "p" and move.src % 8 != move.dst % 8)
                    transitions += 1
            lane_report["checks"] = {"published_perft_totals": len(perfts), "position_probes": len(probes),
                                     "independent_child_transitions": transitions, "raw_hq_ray_cases": responses[0]["cases"],
                                     "root_attacked_square_colour_queries": len(probes) * 128,
                                     "std_driver_only": True, "passed": True}
            if previous is not None:
                assert previous == output, "scalar/HQ board qualification output differs"
            previous = output
            lane_report["response_sha256"] = sha(output)
        report["scalar_hq_response_bytes_identical"] = True
        report["repetition_scope"] = "position keys and reversible contexts only; search adjudication is a separate test"
        report["passed"] = True
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        save(out / "report.json", report)
    print(out / "report.json")


if __name__ == "__main__":
    main()
