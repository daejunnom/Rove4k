#!/usr/bin/env python3
"""Exact restoration, independent UCI oracle, and completed 2x2 search study.

Elapsed samples are recorded as local smoke evidence. Run the repeatable timing
study later in a coordinated quiet window before making speed claims.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from generate import digest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "engines" / "tests"))
from verify import Engine, search
from chess_oracle import Board, START

FENS = (START,
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 19 42",
    "4k3/P6p/8/3pP3/8/8/7P/4K3 w - d6 0 10",
    "k3r3/8/8/3pP3/8/8/8/4K3 w - d6 99 37")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--no-sanitizer", action="store_true")
    parser.add_argument("--skip-oracle", action="store_true")
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT == args.out or ROOT in args.out.parents:
        parser.error("--out must be new, absolute, outside the checkout")
    args.out.mkdir(parents=True)
    manifest = json.loads(args.build.read_text())
    specs = [entry for entry in manifest["engines"] if entry["form"] == "dev"]
    result = {"build_sha256": digest(args.build.read_bytes()), "contracts": [], "search": [],
              "timing_scope": "shared local host smoke, no speed/rating/scaling claim", "passed": True}
    try:
        for spec in specs:
            for sanitizer in ([False] if args.no_sanitizer else [False, True]):
                label = spec["id"] + ("-asan" if sanitizer else "-optimized")
                destination = args.out / label
                destination.mkdir()
                source = Path(spec["cwd"])
                command = [args.cc, "-std=c11", "-O1" if sanitizer else "-Os", "-pthread", "-DROVE_VARIANT=1",
                           "-DROVE_DEV=1", "-DROVE_PARALLEL=0", f"-DROVE_WORKERS={manifest['workers']}",
                           f"-DROVE_TT_BITS={manifest['tt_bits']}", "-I", str(source)]
                if sanitizer:
                    command += ["-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
                command += [str(HERE / "contract.c"), str(source / "board.c"), str(source / "search.c"),
                            "-o", str(destination / "contract")]
                subprocess.run(command, check=True, capture_output=True, timeout=120)
                env = {**os.environ, "ASAN_OPTIONS": "detect_leaks=1:abort_on_error=1", "UBSAN_OPTIONS": "halt_on_error=1"}
                run = subprocess.run([str(destination / "contract")], check=True, capture_output=True,
                                     text=True, env=env, timeout=120)
                data = json.loads(run.stdout)
                data.update(id=label, command=command, program_sha256=digest((destination / "contract").read_bytes()))
                result["contracts"].append(data)
                print(json.dumps(data), flush=True)
        # Bit-for-bit normalized key/HCE and physical move-tree checksums must
        # agree across all four representations and both sanitizer modes.
        fields = ("nodes", "moves", "special_moves", "checksum", "cancel_budgets")
        signatures = {tuple(item[k] for k in fields) for item in result["contracts"]}
        if len(signatures) != 1:
            raise AssertionError("layout/update restoration contract signatures differ")
        for index, spec in enumerate(specs):
            engine = Engine(spec, args.out, spec["id"] + "-completed", 30)
            try:
                engine.initialize()
                for number, fen in enumerate(FENS):
                    engine.send("ucinewgame")
                    engine.ready()
                    engine.position(fen)
                    board = Board.from_fen(fen)
                    state = json.loads(engine.dev("state", "{"))
                    record = search(engine, board, "go depth 4", timeout=30)
                    stats = json.loads(engine.dev("stats", "{"))
                    record.update(id=spec["id"], fixture=number, fen=fen, state=state,
                                  nodes=stats["nodes"], completed_depth=stats["completed_depth"])
                    result["search"].append(record)
                engine.close()
            finally:
                if not engine.log.closed:
                    engine.terminate()
        # A single worker, normalized tie domains, identical ordered histories
        # and cleared TT give a strict score/node/witness comparison rather than
        # claiming that an unrelated benchmark happens to look similar.
        if manifest["workers"] == 1:
            for fixture in range(len(FENS)):
                rows = [r for r in result["search"] if r["fixture"] == fixture]
                semantic = [{"state": r["state"], "bestmove": r["bestmove"], "nodes": r["nodes"],
                             "completed_depth": r["completed_depth"], "info": r["info"]} for r in rows]
                if any(item != semantic[0] for item in semantic[1:]):
                    raise AssertionError(f"actual completed search differs across 2x2: fixture {fixture}")
        if not args.skip_oracle:
            command = [sys.executable, str(ROOT / "engines" / "tests" / "verify.py"),
                       "--manifest", str(args.build), "--out", str(args.out / "oracle")]
            subprocess.run(command, check=True, timeout=600)
            result["oracle"] = {"path": str(args.out / "oracle" / "results.json"), "passed": True}
    except Exception as error:
        result.update(passed=False, error=f"{type(error).__name__}: {error}")
        raise
    finally:
        (args.out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(str(args.out / "results.json"), flush=True)


if __name__ == "__main__":
    main()
