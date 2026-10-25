#!/usr/bin/env python3
"""Small, serial local C/Rust policy study; no rating or target scaling claim.

Build the ten retained-family / four-worker / TT-bits-18 development programs first. Supply
their build.py manifests, preserve the input sources, and run in a coordinated
quiet window. Evidence, transcripts and ordinary PGN go outside the checkout.
The earlier A study is historical; Rust A is no longer an active candidate.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import re
import statistics
import sys
import time
import traceback

from chess_oracle import Board, FILES, coord
from verify import Engine, ROOT, atomic_json, parse_info, require


OPENINGS = (
    ("open-game", ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6")),
    ("queens-gambit", ("d2d4", "d7d5", "c2c4", "e7e6", "b1c3", "g8f6")),
    ("indian", ("d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "f8g7")),
)
POLICIES = ("loose", "root", "groups", "pals", "hybrid")
TICKS = os.sysconf("SC_CLK_TCK") if sys.platform == "linux" else 100


class SearchWaitExpired(TimeoutError):
    def __init__(self, elapsed):
        super().__init__("no bestmove before the measured search wait expired")
        self.elapsed = elapsed


class StudyBudgetExpired(RuntimeError):
    pass


def remaining(deadline):
    value = deadline - time.monotonic()
    if value <= 0:
        raise StudyBudgetExpired("coordinated comparison wall budget exhausted")
    return value


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(moves):
    board, seen = Board.from_fen(), Counter()
    seen[board.repetition_key()] += 1
    for move in moves:
        board = board.play(move)
        seen[board.repetition_key()] += 1
    return board, seen


def dead_material(board):
    pieces = [(i, p.lower()) for i, p in enumerate(board.cells) if p not in ".Kk"]
    if any(p in "pqr" for _, p in pieces):
        return False
    return (len(pieces) <= 1 or
            all(p == "b" for _, p in pieces) and
            len({(i // 8 + i % 8) % 2 for i, _ in pieces}) == 1)


def adjudicate(board, seen):
    if not list(board.legal_moves()):
        return ("0-1" if board.turn else "1-0", "checkmate") if board.in_check() else ("1/2-1/2", "stalemate")
    if dead_material(board):
        return "1/2-1/2", "dead-material-sufficient-test"
    if seen[board.repetition_key()] >= 3:
        return "1/2-1/2", "available-threefold-claim"
    if board.halfmove >= 100:
        return "1/2-1/2", "available-fifty-move-claim"
    return None


def flag_outcome(board, flagged_colour):
    nonflagging = [p.lower() for p in board.cells if p != "." and p.isupper() == (flagged_colour == 1)]
    return (("1/2-1/2", "time-flag-opponent-lone-king") if nonflagging == ["k"] else
            ("0-1" if flagged_colour == 0 else "1-0", "time-forfeit"))


def san(board, text):
    moves = list(board.legal_moves())
    move = next((m for m in moves if str(m) == text), None)
    require(move is not None, "PGN move is not independently legal")
    piece = board.cells[move.src]
    if piece.lower() == "k" and abs(move.dst - move.src) == 2:
        result = "O-O" if move.dst > move.src else "O-O-O"
    else:
        capture = board.cells[move.dst] != "." or piece.lower() == "p" and move.src % 8 != move.dst % 8
        result = "" if piece.lower() == "p" else piece.upper()
        others = [m for m in moves if m.src != move.src and m.dst == move.dst and board.cells[m.src] == piece]
        if piece.lower() != "p" and others:
            if all(m.src % 8 != move.src % 8 for m in others):
                result += FILES[move.src % 8]
            elif all(m.src // 8 != move.src // 8 for m in others):
                result += str(move.src // 8 + 1)
            else:
                result += coord(move.src)
        if capture:
            result += (FILES[move.src % 8] if piece.lower() == "p" else "") + "x"
        result += coord(move.dst) + ("=" + move.promotion.upper() if move.promotion else "")
    child = board.apply(move)
    if child.in_check():
        result += "+" if list(child.legal_moves()) else "#"
    return result


def process_sample(engine):
    directory = Path("/proc") / str(engine.process.pid)
    # Fields after the final ')' are stable even if a process name has spaces.
    fields = (directory / "stat").read_text().rsplit(")", 1)[1].split()
    status = {}
    for line in (directory / "status").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in ("VmRSS", "VmHWM", "VmSize", "VmData"):
            status[key + "_bytes"] = int(value.split()[0]) * 1024
    return {"cpu_seconds": (int(fields[11]) + int(fields[12])) / TICKS,
            "threads": len(engine.task_ids()), **status}


def parallel_counters(lines, stats):
    result = {key: stats[key] for key in ("parallel", "groups", "assigned", "reassigned", "reused", "shared_bounds", "clauses", "repairs", "worker_bytes", "tt_bytes") if key in stats}
    for line in lines:
        if line.startswith("info string parallel "):
            words = line.split()[3:]
            for i in range(0, len(words) - 1, 2):
                try:
                    result[words[i]] = int(words[i + 1])
                except ValueError:
                    result[words[i]] = words[i + 1]
    return result


def measured_search(engine, board, command, timeout, require_iteration=True):
    require(timeout > 0, "comparison wall budget exhausted before search")
    before = process_sample(engine)
    start = time.monotonic()
    engine.send(command)
    try:
        lines = engine.until(lambda line: line.startswith("bestmove "), timeout)
    except TimeoutError as error:
        raise SearchWaitExpired(time.monotonic() - start) from error
    elapsed = time.monotonic() - start
    after = process_sample(engine)
    best = [line.split()[1] for line in lines if line.startswith("bestmove ")]
    require(len(best) == 1, "search returned an invalid bestmove count")
    legal = {str(move) for move in board.legal_moves()}
    require(best[0] in legal if legal else best[0] == "0000", f"illegal bestmove {best[0]} in {board.fen()}")
    info = parse_info(lines, board)
    require(info or not require_iteration, "development search did not report a completed iteration")
    require(not any(line.startswith("bestmove ") for line in engine.quiet(0.002)), "duplicate bestmove")
    engine.assert_threads_stable()
    stats = engine.stats()
    return {"command": command, "bestmove": best[0], "wall_seconds": elapsed,
            "cpu_seconds": after["cpu_seconds"] - before["cpu_seconds"],
            "completed_depth": info[-1]["depth"] if info else 0, "last_completed": info[-1] if info else None,
            "nodes": stats.get("nodes"), "resources_before": before,
            "resources_after": after, "counters": parallel_counters(lines, stats)}


def load_programs(manifests, family="E"):
    require(family in "BCDE" and len(family) == 1, "select one retained B/C/D/E family")
    specs, inputs = [], []
    for path in manifests:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        require(data.get("complete"), f"incomplete build manifest {path}")
        inputs.append({"path": str(path), "sha256": sha(path), "tools": data.get("tools"),
                       "git_head": data.get("git_head"), "engine_source_root": data.get("engine_source_root")})
        for candidate in data["engines"]:
            config = candidate["configuration"]
            require(config["ROVE_VARIANT"] == family and int(config["ROVE_WORKERS"]) == 4 and
                    int(config["ROVE_TT_BITS"]) == 18 and int(config["ROVE_DEV"]) == 1 and
                    int(config.get("ROVE_MODEL", 0)) == 0 and int(config.get("ROVE_HQ", 0)) == 0,
                    f"comparison requires {family}, four workers, TT bits 18, development interface, no cross-model or HQ")
            language = candidate["id"].split("-")[1]
            mode = int(config["ROVE_PARALLEL"])
            require(language in ("c", "rust") and 0 <= mode <= 4, "unexpected language/policy")
            original = next(a for a in candidate["artifacts"] if a["format"] == "native-elf" and a["source_form"] == "original")
            binary = Path(candidate["command"][0])
            require(sha(binary) == original["sha256"], "program hash differs from build record")
            sources = candidate["sources"]
            require(sources, "build record has no source hashes")
            spec = {**candidate, "id": f"{family}-{language}-{POLICIES[mode]}", "language": language,
                    "policy": mode, "startup_threads": 5, "startup_timeout": 15,
                    "expected_program_sha256": original["sha256"], "manifest": str(path),
                    "program_bytes": binary.stat().st_size}
            specs.append(spec)
    require(len(specs) == 10 and len({s["id"] for s in specs}) == 10,
            "supply exactly C and Rust programs for each of five policies")
    for language in ("c", "rust"):
        signatures = {tuple(sorted((s["path"], s["sha256"]) for s in item["sources"])) for item in specs if item["language"] == language}
        require(len(signatures) == 1, "policy builds did not use identical frozen language sources")
        recipes = set()
        for item in specs:
            if item["language"] != language:
                continue
            config = dict(item["generation_config"])
            config.pop("parallel", None)
            config["fixed_environment"] = {key: value for key, value in config["fixed_environment"].items() if key != "ROVE_PARALLEL"}
            config["command"] = [re.sub(r"^-DROVE_PARALLEL=\d+$", "-DROVE_PARALLEL=POLICY", word) for word in config["command"]]
            recipes.add(json.dumps(config, sort_keys=True))
        require(len(recipes) == 1, "language policy builds differ in more than their parallel selection")
    optimizations = {item["generation_config"]["optimize"] for item in specs}
    require(len(optimizations) == 1, "policy builds mix optimization objectives")
    return sorted(specs, key=lambda s: (s["policy"], s["language"])), inputs


def launch(spec, out, label, timeout, cpus):
    engine = Engine(spec, out, label, timeout)
    try:
        engine.initialize()
        startup = time.monotonic() - engine.start
        for tid in engine.task_ids():
            os.sched_setaffinity(tid, cpus)
        engine.assert_threads_stable()
        return engine, {"handshake_seconds": startup, "task_ids": sorted(engine.startup_task_ids),
                        "affinity_after_startup": sorted(cpus), "resources": process_sample(engine)}
    except Exception:
        engine.terminate()
        raise


def benchmark(specs, args, report, deadline, cpus):
    schedule = [(position, sample, work, spec["id"]) for position in range(3)
                for sample in range(args.samples) for work in ("depth", "nodes") for spec in specs]
    random.Random(args.seed).shuffle(schedule)
    report["benchmark_schedule"] = schedule
    by_id = {s["id"]: s for s in specs}
    for number, (position, sample, work, identity) in enumerate(schedule):
        remaining(deadline)
        opening, prefix = OPENINGS[position]
        board, _ = replay(prefix)
        spec = by_id[identity]
        engine = None
        label = f"bench-{number:03}-{identity}-{opening}-{sample}-{work}"
        try:
            engine, startup = launch(spec, args.out, label, args.timeout, cpus)
            engine.position(moves=prefix)
            command = f"go depth {args.depth}" if work == "depth" else f"go nodes {args.nodes}"
            try:
                result = measured_search(engine, board, command, min(args.timeout, remaining(deadline)))
            except SearchWaitExpired as error:
                if time.monotonic() >= deadline:
                    raise StudyBudgetExpired("comparison wall budget expired during benchmark") from error
                raise
            if work == "depth":
                require(result["completed_depth"] == args.depth, "fixed-depth work was not completed")
            else:
                require(result["nodes"] is not None and args.nodes <= result["nodes"] <= args.nodes + 4,
                        "shared node budget differs from frozen requested work")
            report["benchmarks"].append({"id": identity, "opening": opening, "prefix": prefix,
                "sample": sample, "work": work, "startup": startup, **result})
            engine.close()
        finally:
            if engine is not None and not engine.log.closed:
                engine.terminate()
        atomic_json(args.out / "results.json", report)
        print(f"benchmark {number + 1}/{len(schedule)} {identity} {opening} {work}", flush=True)


def pgn(record):
    reason = record["termination"]
    termination = "time forfeit" if reason == "time-forfeit" else "unterminated" if record["result"] == "*" else "normal"
    tags = {"Event": "Rove4k local bounded policy study", "Site": "local Linux", "Date": record["date"],
            "Round": f"{record['pair']+1}.{record['exchange']+1}",
            "White": record["white"], "Black": record["black"], "Result": record["result"],
            "TimeControl": f"{record['base_ms']/1000:g}+{record['increment_ms']/1000:g}",
            "Termination": termination, "RoveTermination": reason, "Opening": record["opening"]}
    header = "\n".join(f'[{k} "{str(v).replace(chr(34), chr(39))}"]' for k, v in tags.items())
    words = []
    for ply, text in enumerate(record["san"]):
        if ply % 2 == 0:
            words.append(str(ply // 2 + 1) + ".")
        words.append(text)
    return header + "\n\n" + " ".join(words + [record["result"]]) + "\n\n"


def games(specs, args, report, deadline, cpus):
    by_key = {(s["language"], s["policy"]): s for s in specs}
    pairs = [(by_key["c", mode], by_key["rust", mode], "matched-language") for mode in range(5)]
    pairs += [(by_key[language, 0], by_key[language, mode], "same-language-policy")
              for language in ("c", "rust") for mode in range(1, 5)]
    for pair, (left, right, comparison) in enumerate(pairs):
        opening, prefix = OPENINGS[pair % 3]
        for exchange, ordered in enumerate(((left, right), (right, left))):
            remaining(deadline)
            players = []
            board, seen = replay(prefix)
            replay_board = Board.from_fen()
            notation = []
            for move in prefix:
                notation.append(san(replay_board, move))
                replay_board = replay_board.play(move)
            moves, clocks, turns = list(prefix), [args.base_ms / 1000] * 2, []
            outcome = None
            game = {"white": ordered[0]["id"], "black": ordered[1]["id"], "comparison": comparison,
                    "pair": pair, "exchange": exchange, "opening": opening, "opening_moves": prefix,
                    "base_ms": args.base_ms, "increment_ms": args.increment_ms,
                    "date": datetime.now(timezone.utc).strftime("%Y.%m.%d"), "startup": []}
            try:
                for colour, spec in enumerate(ordered):
                    remaining(deadline)
                    engine, startup = launch(spec, args.out, f"game-{pair:02}-{exchange}-{colour}", args.timeout, cpus)
                    players.append(engine)
                    game["startup"].append(startup)
                for ply in range(args.plies):
                    outcome = adjudicate(board, seen)
                    if outcome:
                        break
                    if time.monotonic() >= deadline:
                        outcome = ("*", "bounded-wall-limit-unfinished")
                        break
                    colour = 0 if board.turn else 1
                    engine = players[colour]
                    engine.position(moves=moves)
                    command = f"go wtime {max(0,int(clocks[0]*1000))} btime {max(0,int(clocks[1]*1000))} winc {args.increment_ms} binc {args.increment_ms}"
                    remaining_batch = remaining(deadline)
                    wait = min(args.timeout, remaining_batch, max(0.001, clocks[colour]))
                    try:
                        result = measured_search(engine, board, command, wait, require_iteration=False)
                    except SearchWaitExpired as error:
                        if time.monotonic() >= deadline:
                            outcome = ("*", "bounded-wall-limit-unfinished")
                            break
                        if error.elapsed < clocks[colour]:
                            raise
                        clocks[colour] -= error.elapsed
                        turns.append({"ply_after_opening": ply + 1, "command": command,
                                      "no_bestmove_before_clock_expired": True,
                                      "wall_seconds": error.elapsed, "clocks_seconds": clocks.copy()})
                        outcome = flag_outcome(board, colour)
                        engine.send("stop")
                        late = engine.until(lambda line: line.startswith("bestmove "), min(0.5, max(0.001, deadline - time.monotonic())))
                        late_move = next(line.split()[1] for line in late if line.startswith("bestmove "))
                        require(late_move in {str(m) for m in board.legal_moves()}, "late stop returned illegal move")
                        turns[-1]["late_move_not_played"] = late_move
                        engine.assert_threads_stable()
                        break
                    clocks[colour] -= result["wall_seconds"]
                    turn = {"ply_after_opening": ply + 1, "clock_seconds_before_increment": clocks.copy(), **result}
                    turns.append(turn)
                    if clocks[colour] <= 0:
                        outcome = flag_outcome(board, colour)
                        break
                    notation.append(san(board, result["bestmove"]))
                    board = board.play(result["bestmove"])
                    seen[board.repetition_key()] += 1
                    moves.append(result["bestmove"])
                    clocks[colour] += args.increment_ms / 1000
                outcome = outcome or adjudicate(board, seen) or ("*", "bounded-ply-limit-unfinished")
                game.update(result=outcome[0], termination=outcome[1], moves=moves, san=notation,
                            turns=turns, clocks_seconds=clocks, final_fen=board.fen(), protocol_pass=True)
                for engine in players:
                    engine.close()
            except Exception as error:
                if isinstance(error, StudyBudgetExpired) and outcome is None:
                    outcome = ("*", "bounded-wall-limit-unfinished")
                game.update(result=outcome[0] if outcome else "*",
                            termination=outcome[1] if outcome else "error-unfinished",
                            protocol_pass=None if isinstance(error, StudyBudgetExpired) else False,
                            error=f"{type(error).__name__}: {error}", moves=moves, san=notation,
                            turns=turns, clocks_seconds=clocks, final_fen=board.fen())
                report["games"].append(game)
                (args.out / "games.pgn").write_text("".join(pgn(g) for g in report["games"]), encoding="utf-8")
                atomic_json(args.out / "results.json", report)
                raise
            finally:
                for engine in players:
                    if not engine.log.closed:
                        engine.terminate()
            report["games"].append(game)
            (args.out / "games.pgn").write_text("".join(pgn(g) for g in report["games"]), encoding="utf-8")
            atomic_json(args.out / "results.json", report)
            print(f"game {len(report['games'])}/26 {game['white']} {game['black']} {game['result']} {game['termination']}", flush=True)
            if game["termination"] == "bounded-wall-limit-unfinished":
                raise StudyBudgetExpired("comparison wall budget expired during game")


def summarize(report):
    family = report["family"]
    grouped = defaultdict(list)
    for sample in report["benchmarks"]:
        grouped[sample["id"], sample["opening"], sample["work"]].append(sample)
    report["medians"] = [{"id": identity, "opening": opening, "work": work, "samples": len(rows),
        **{field: statistics.median(r[field] for r in rows) for field in ("wall_seconds", "cpu_seconds", "nodes", "completed_depth")},
        "startup_seconds": statistics.median(r["startup"]["handshake_seconds"] for r in rows),
        "peak_rss_bytes": max(r["resources_after"]["VmHWM_bytes"] for r in rows)}
        for (identity, opening, work), rows in sorted(grouped.items())]
    medians = {(row["id"], row["opening"], row["work"]): row for row in report["medians"]}
    comparisons = []
    for opening, _ in OPENINGS:
        for work in ("depth", "nodes"):
            pairs = [(f"{family}-c-{policy}", f"{family}-rust-{policy}", "C/Rust") for policy in POLICIES]
            pairs += [(f"{family}-{language}-{policy}", f"{family}-{language}-loose", "policy/loose")
                      for language in ("c", "rust") for policy in POLICIES[1:]]
            for numerator, denominator, comparison in pairs:
                a, b = medians.get((numerator,opening,work)), medians.get((denominator,opening,work))
                if a and b:
                    comparisons.append({"numerator": numerator, "denominator": denominator,
                        "comparison": comparison, "opening": opening, "work": work,
                        "median_wall_ratio": a["wall_seconds"]/b["wall_seconds"],
                        "median_cpu_ratio": a["cpu_seconds"]/b["cpu_seconds"] if a["cpu_seconds"] > 0 and b["cpu_seconds"] > 0 else None,
                        "median_completed_depth_delta": a["completed_depth"]-b["completed_depth"]})
    report["comparisons"] = comparisons
    report["game_results"] = dict(Counter(g["termination"] for g in report["games"]))
    report["remaining_work"] = {"benchmarks": max(0, report["expected_benchmarks"]-len(report["benchmarks"])),
                                "games": max(0, report["expected_games"]-len(report["games"]))}
    model_scope = ("E uses the same frozen 21-coefficient evaluation/ordering model in both languages; surrounding search heuristics differ. "
                   if family == "E" else "Canonical evaluators and search heuristics are not assumed identical. ")
    report["interpretation"] = (f"Matched {family} feature families and fixed worker/TT-entry profiles, not identical searched trees. "
        + model_scope + "Ratios compare these implementations and do not isolate a language effect. "
        "Wall time includes protocol delivery; CPU ticks are quantized. C/Rust slot layouts use different bytes. "
        "Startup includes the shared client's 10-ms thread-observer polling and handshake, so sub-poll startup differences are unresolved. "
        "Four workers yield one four-worker locality group, so this profile cannot measure cross-group scaling. "
        "Bounded unfinished games are not draws. No Elo, tournament strength, 512-thread scaling or 4-KiB eligibility is inferred.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=("B", "C", "D", "E"), default="E",
                        help="one retained C/Rust family; the earlier Rust A study is historical")
    parser.add_argument("--manifest", action="append", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--nodes", type=int, default=12000)
    parser.add_argument("--plies", type=int, default=80)
    parser.add_argument("--base-ms", type=int, default=1500)
    parser.add_argument("--increment-ms", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--wall-seconds", type=float, default=300)
    parser.add_argument("--seed", type=int, default=20261020)
    parser.add_argument("--phase", choices=("benchmark", "games", "both"), default="both")
    args = parser.parse_args()
    require(sys.platform == "linux", "run Linux programs on Linux, including WSL Ubuntu")
    args.out = args.out.resolve()
    require(args.out != ROOT and ROOT not in args.out.parents, "evidence must be outside checkout")
    require(not args.out.exists(), "use a new evidence directory; preserve earlier results")
    require(1 <= args.samples <= 10 and 1 <= args.depth <= 8 and 1 <= args.nodes <= 1000000 and
            1 <= args.plies <= 256 and 1 <= args.base_ms <= 60000 and 0 <= args.increment_ms <= 1000 and
            0 < args.timeout <= 30 and 0 < args.wall_seconds <= 900, "comparison exceeds bounded local limits")
    specs, manifests = load_programs(args.manifest, args.family)
    cpus = set(sorted(os.sched_getaffinity(0))[:5])
    require(cpus, "no available CPU affinity")
    args.out.mkdir(parents=True)
    report = {"complete": False, "family": args.family, "input_manifests": manifests, "programs": specs,
        "inputs": {"openings": OPENINGS, "seed": args.seed, "options": {k: str(v) if isinstance(v,Path) else v for k,v in vars(args).items() if k != "manifest"}},
        "environment": {"platform": platform.platform(), "machine": platform.machine(), "python": sys.version,
            "cpu_count": os.cpu_count(), "affinity": sorted(cpus), "cpu_tick_seconds": 1 / TICKS,
            "load_average_before": os.getloadavg(), "clock": "monotonic wall, /proc process aggregate CPU ticks"},
        "client_inputs": [{"path": str(p), "sha256": sha(p)} for p in (Path(__file__), Path(__file__).with_name("verify.py"), Path(__file__).with_name("chess_oracle.py"))],
        "benchmarks": [], "games": [],
        "expected_benchmarks": 0 if args.phase == "games" else 3*args.samples*2*len(specs),
        "expected_games": 0 if args.phase == "benchmark" else 26,
        "game_policy": "Automatic claim of available threefold/fifty-move draws; conservative dead-material test; no score adjudication. Flags against a lone king draw; other flags lose under this local match policy, which does not solve every possible dead position. Each pair uses the same opening with colours exchanged. At most one engine searches at once; two idle persistent pools total ten threads."}
    deadline = time.monotonic() + args.wall_seconds
    started = time.monotonic()
    exit_code = 0
    try:
        if args.phase != "games":
            benchmark(specs, args, report, deadline, cpus)
        if args.phase != "benchmark":
            games(specs, args, report, deadline, cpus)
        report["complete"] = (len(report["benchmarks"]) == report["expected_benchmarks"] and
                              len(report["games"]) == report["expected_games"])
    except StudyBudgetExpired as error:
        report["interrupted"] = str(error)
        exit_code = 2
    except Exception as error:
        report["failure"] = f"{type(error).__name__}: {error}"
        report["traceback"] = traceback.format_exc()
        raise
    finally:
        report["wall_seconds"] = time.monotonic() - started
        report["environment"]["load_average_after"] = os.getloadavg()
        summarize(report)
        atomic_json(args.out / "results.json", report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit("All engine Rust paths are retired; this historical C/Rust comparison runner is disabled.")
