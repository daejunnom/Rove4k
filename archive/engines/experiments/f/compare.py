#!/usr/bin/env python3
"""Compare the four production F contracts on identical frozen source bytes.

This is a correctness/work-count comparison. Elapsed values are diagnostic;
shared-host executions do not establish a throughput or playing-strength win.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "engines/tests"))
from chess_oracle import Board
from verify import Engine, parse_info, require

LABELS = ("paired-previous", "paired-parity", "single-previous", "single-parity")
QUIET = ("8/6pk/8/8/8/8/PK6/8 w - - 0 1",
         "8/6pk/8/8/8/P7/1K6/8 b - - 0 1",
         "8/7k/6p1/8/8/P7/1K6/8 w - - 0 1")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def static_eval(board, language):
    """Independent arithmetic for each F implementation's fixed HCE contract."""
    values = {"p": 100, "n": 320, "b": 330, "r": 500, "q": 900, "k": 0}
    total = 0
    for square, piece in enumerate(board.cells):
        if piece == ".":
            continue
        rank, file = divmod(square, 8)
        relative = rank if piece.isupper() else 7-rank
        kind = piece.lower()
        center = (7 if language == "c" else 6)-abs(2*file-7)-abs(2*relative-7)
        if language == "c":
            positional = {"p": relative*7+center*2, "n": center*9,
                          "b": center*5, "r": relative*2,
                          "q": center*2, "k": -center*3}[kind]
        else:
            positional = {"p": relative*6+center, "n": center*4,
                          "b": center*2, "r": relative, "q": 0, "k": 0}[kind]
        total += (1 if piece.isupper() else -1)*(values[kind]+positional)
    return max(-20000, min(20000, total*(1 if board.turn else -1)))


def minimax(board, depth, language, ply=0):
    moves = list(board.legal_moves())
    if not moves:
        return -30000+ply if board.in_check() else 0
    if depth == 0:
        require(not board.in_check(), "quiet oracle frontier is in check")
        require(all(board.cells[m.dst] == "." and not m.promotion
                    and not (board.cells[m.src].lower() == "p" and m.dst == board.ep)
                    for m in moves), "quiet oracle frontier has a capture/promotion")
        return static_eval(board, language)
    return max(-minimax(board.apply(m), depth-1, language, ply+1) for m in moves)


def run_search(engine, board, command):
    engine.send(command)
    lines = engine.until(lambda s: s.startswith("bestmove "))
    best = [s.split()[1] for s in lines if s.startswith("bestmove ")]
    require(len(best) == 1, "exactly one completed bestmove required")
    legal = {str(m) for m in board.legal_moves()}
    require(best[0] in legal, "completed move is illegal")
    info = parse_info(lines, board)
    seeds = [tuple(map(int, m.groups())) for line in lines
             if (m := re.fullmatch(r"info string f seed depth (\d+) guess (-?\d+)", line))]
    require(not any(s.startswith("bestmove ") for s in engine.quiet()), "duplicate bestmove")
    engine.assert_threads_stable()
    stats=engine.stats()
    probes=stats.get("mtd_probes",stats.get("f_probes",0))
    previous=getattr(engine,"f_prior_probes",0) if "mtd_probes" in stats else 0
    engine.f_prior_probes=probes
    return {"bestmove": best[0], "info": info, "seeds": seeds, "stats": stats,
            "probe_count": probes-previous}


def checked_record(record, artifact, label, out):
    language = record["id"].split("-")[1]
    spec = dict(record, command=[artifact["path"]], cwd=str(Path(artifact["path"]).parent))
    engine = Engine(spec, out, label, 30)
    results = []
    try:
        engine.initialize()
        for index, fen in enumerate(QUIET):
            board = Board.from_fen(fen)
            expected = minimax(board, 3, language)
            engine.send("ucinewgame")
            engine.position(fen)
            # Repeat retains the actual table, including completed deeper bounds.
            for repeat, depth in enumerate((3, 3, 1, 2)):
                result = run_search(engine, board, f"go depth {depth}")
                last = result["info"][-1]
                require(last["depth"] == depth and last["kind"] == "cp", "requested depth did not complete")
                value = expected if depth == 3 else minimax(board, depth, language)
                require(last["score"] == value, "MTD result differs from independent minimax")
                attained = -minimax(board.play(result["bestmove"]), depth-1, language, 1)
                require(attained == value, "published lower-bound witness does not attain score")
                result.update(case=index, repeat=repeat, expected=value)
                results.append(result)
        engine.send("ucinewgame")
        engine.position()
        board = Board.from_fen()
        completed = run_search(engine, board, "go depth 4")
        scores = {r["depth"]: r["score"] for r in completed["info"]}
        require(set(scores) == {1,2,3,4}, "seed comparison lacks four completed iterations")
        parity = label.split("-")[1] == "parity"
        for depth, seed in completed["seeds"]:
            expected = 0 if depth == 1 else scores[depth-2 if parity and depth > 2 else depth-1]
            require(seed == expected, "initial estimate does not follow completed-depth policy")
        require(len(completed["seeds"]) == 4, "missing actual production F seed observations")
        results.append(dict(completed, case="seed-policy"))
        engine.position()
        cancelled = run_search(engine, board, "go nodes 1000 depth 30")
        require(cancelled["info"] and cancelled["info"][-1]["depth"] < 30, "cancellation did not interrupt a deeper iteration")
        ceiling = 1000+int(record["workers"])-1
        require(0 < cancelled["stats"]["nodes"] <= ceiling, "cancelled work exceeded fixed budget")
        results.append(dict(cancelled, case="node-cancellation"))
        require(all(r["stats"].get("mtd_conflicts", r["stats"].get("bound_conflicts", 0)) == 0 for r in results), "bound conflict detected")
        return {"passed": True, "cases": results, "startup_threads": sorted(engine.startup_task_ids or ())}
    finally:
        try:
            engine.close()
        finally:
            if engine.process.poll() is None:
                engine.terminate()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="append", required=True, metavar="MODE=BUILD_JSON")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), "output must be a new directory")
    args.out.mkdir(parents=True)
    manifests = dict(item.split("=", 1) for item in args.manifest)
    require(set(manifests) == set(LABELS), "all four F experiment configurations are required")
    report = {"schema": 1, "scope": "correctness and work counts; elapsed times are not a fair performance comparison",
              "memory_contract": "equal TT slot count; representation changes allocated TT bytes",
              "probe_contract": {"c": "coordinated whole-root MTD rounds", "rust": "sum of independent worker MTD probes"},
              "engines": [], "passed": False}
    inputs = {}
    configurations = {}
    completed_values = {}
    try:
        for mode in LABELS:
            manifest = json.loads(Path(manifests[mode]).read_text())
            require(manifest.get("complete"), "incomplete build manifest")
            for record in manifest["engines"]:
                require(record["id"] in ("F-c", "F-rust"), "experiment may contain only F C/Rust")
                language = record["id"].split("-")[1]
                hashes = sorted((x["path"], x["sha256"]) for x in record["sources"])
                require(language not in inputs or inputs[language] == hashes, "comparison uses different canonical source bytes")
                inputs[language] = hashes
                config = record["configuration"]
                fixed = {k:v for k,v in config.items() if k not in ("ROVE_F_SINGLE", "ROVE_F_PARITY")}
                require(language not in configurations or configurations[language] == fixed,
                        "comparison changed a nonexperimental fixed configuration")
                configurations[language] = fixed
                require(int(config.get("ROVE_F_SINGLE", "0")) == int(mode.startswith("single-")), "TT mode flag mismatch")
                require(int(config.get("ROVE_F_PARITY", "0")) == int(mode.endswith("-parity")), "seed mode flag mismatch")
                unique = {}
                for artifact in record["artifacts"]:
                    require(digest(artifact["path"]) == artifact["sha256"], "artifact bytes changed")
                    if artifact["format"] != "native-elf":
                        continue
                    if artifact["sha256"] in unique:
                        continue
                    unique[artifact["sha256"]] = artifact
                    label = mode+"-"+language+"-"+artifact["source_form"]
                    evidence = checked_record(record, artifact, label, args.out)
                    values=[case["info"][-1]["score"] for case in evidence["cases"] if case["case"] != "node-cancellation"]
                    require(language not in completed_values or completed_values[language] == values,
                            "completed values differ across storage/estimate policies")
                    completed_values[language]=values
                    report["engines"].append({"mode": mode, "language": language, "artifact": artifact,
                        "tt_slot_bytes": (16 if mode.startswith("single") else (32 if language == "c" else 24)),
                        "tt_total_bytes": (1 << int(config["ROVE_TT_BITS"])) * (16 if mode.startswith("single") else (32 if language == "c" else 24)),
                        "evidence": evidence})
                    print(label+": independent minimax, witness, retained TT, initial seeds, cancellation PASS", flush=True)
        report["source_hashes"] = inputs
        report["passed"] = True
    finally:
        (args.out/"comparison.json").write_text(json.dumps(report, indent=2)+"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
