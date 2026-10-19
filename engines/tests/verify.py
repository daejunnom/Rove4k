#!/usr/bin/env python3
"""Bounded black-box chess-engine verification; Python standard library only.

Run this on Linux for Linux binaries. Reports and process transcripts must be
written outside the checkout. No engine implementation is imported or inspected.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import random
import re
import signal
import subprocess
import sys
import threading
import time
import traceback

from chess_oracle import Board, PERFT, START, self_check


MOVE = re.compile(r"^[a-h][1-8][a-h][1-8][qrbn]?$")
ROOT = Path(__file__).resolve().parents[2]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


class Engine:
    def __init__(self, spec, output, label, timeout):
        self.spec, self.timeout = spec, timeout
        self.path = output / f"{label}.jsonl"
        self.log = self.path.open("w", encoding="utf-8")
        self.lock = threading.Lock()
        self.lines, self.stderr = queue.Queue(), []
        self.start = time.monotonic()
        self.exhausted, self.output_bytes, self.peak_threads = False, 0, 0
        self.descendants = {}
        self.startup_task_ids = None
        self.sampling = True
        self.record("launch", spec["command"])
        try:
            self.process = subprocess.Popen(spec["command"], cwd=spec.get("cwd"),
                                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                            errors="replace", bufsize=1,
                                            start_new_session=os.name == "posix")
        except Exception:
            self.log.close()
            raise
        self.readers = []
        for stream, target in ((self.process.stdout, "stdout"), (self.process.stderr, "stderr")):
            reader = threading.Thread(target=self.read_stream, args=(stream, target), daemon=True)
            reader.start()
            self.readers.append(reader)
        self.sampler = threading.Thread(target=self.sample_process, daemon=True)
        self.sampler.start()

    def record(self, direction, value):
        with self.lock:
            self.log.write(json.dumps({"t": round(time.monotonic() - self.start, 6),
                                       "direction": direction, "value": value}) + "\n")
            self.log.flush()

    def read_stream(self, stream, direction):
        try:
            while True:
                line = stream.readline(65537)
                if not line:
                    break
                if len(line) > 65536:
                    self.lines.put(RuntimeError("engine output line exceeded 64 KiB limit"))
                    break
                line = line.rstrip("\r\n")
                self.output_bytes += len(line.encode("utf-8"))
                if self.output_bytes > 8 * 1024 * 1024:
                    self.exhausted = True
                    self.lines.put(RuntimeError("engine output exceeded 8 MiB limit"))
                    break
                self.record(direction, line)
                if direction == "stdout":
                    self.lines.put(line)
                else:
                    self.stderr.append(line)
        finally:
            if direction == "stdout":
                self.lines.put(EOFError("engine closed stdout"))

    def sample_process(self):
        proc = Path("/proc") / str(self.process.pid)
        while self.sampling and self.process.poll() is None:
            try:
                self.peak_threads = max(self.peak_threads, len(list((proc / "task").iterdir())))
                child_file = proc / "task" / str(self.process.pid) / "children"
                for pid in child_file.read_text().split():
                    child_stat = (Path("/proc") / pid / "stat").read_text().split()
                    self.descendants[int(pid)] = child_stat[21]
            except (OSError, ValueError):
                pass
            time.sleep(0.01)

    def send(self, command):
        require(self.process.poll() is None, f"engine exited before {command!r}")
        self.record("stdin", command)
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

    def until(self, predicate, timeout=None):
        deadline, seen = time.monotonic() + (timeout or self.timeout), []
        while time.monotonic() < deadline:
            try:
                line = self.lines.get(timeout=max(0.001, deadline - time.monotonic()))
            except queue.Empty:
                break
            if isinstance(line, Exception):
                raise line
            seen.append(line)
            if predicate(line):
                return seen
        raise TimeoutError(f"engine response timeout; last lines: {seen[-5:]}")

    def quiet(self, duration=0.08):
        deadline, lines = time.monotonic() + duration, []
        while time.monotonic() < deadline:
            try:
                line = self.lines.get(timeout=max(0.001, deadline - time.monotonic()))
            except queue.Empty:
                break
            if isinstance(line, Exception):
                raise line
            lines.append(line)
        return lines

    def drain(self):
        lines = []
        while True:
            try:
                item = self.lines.get_nowait()
            except queue.Empty:
                return lines
            if isinstance(item, str):
                lines.append(item)

    def ready(self):
        self.send("isready")
        return self.until(lambda line: line == "readyok")

    def initialize(self):
        configuration = self.spec.get("configuration", {})
        expected = self.spec.get("startup_threads")
        if expected is None and "ROVE_WORKERS" in configuration:
            expected = int(configuration["ROVE_WORKERS"]) + 1
        if expected is not None and sys.platform == "linux":
            deadline = time.monotonic() + self.timeout
            while time.monotonic() < deadline:
                tasks = self.task_ids()
                if len(tasks) == expected:
                    self.startup_task_ids = tasks
                    break
                require(len(tasks) <= expected, f"startup thread count {len(tasks)} exceeds fixed total {expected}")
                time.sleep(0.01)
            require(self.startup_task_ids is not None,
                    f"fixed total {expected} threads were not created before first UCI input")
            self.record("startup_threads", sorted(self.startup_task_ids))
        self.send("uci")
        lines = self.until(lambda line: line == "uciok")
        require(lines.count("uciok") == 1, "uci emitted duplicate uciok")
        self.ready()
        self.assert_threads_stable()
        return lines

    def task_ids(self):
        try:
            return {int(path.name) for path in (Path("/proc") / str(self.process.pid) / "task").iterdir()}
        except OSError:
            return set()

    def assert_threads_stable(self):
        if self.startup_task_ids is not None:
            require(self.task_ids() == self.startup_task_ids, "startup thread IDs changed across search lifecycle")

    def dev(self, command, prefix):
        self.send(command)
        return self.until(lambda line: line.startswith(prefix))[-1]

    def position(self, fen=None, moves=()):
        self.send("position " + ("startpos" if fen is None else "fen " + fen)
                  + (" moves " + " ".join(moves) if moves else ""))

    def state(self):
        self.send("state")
        line = self.until(lambda item: item.startswith("{") or item.startswith("state {"))[-1]
        data = json.loads(line[line.index("{"):])
        require(all(key in data for key in ("hash", "halfmove", "eval", "draw")),
                f"missing required development state fields: {data}")
        if "invariant" in data:
            require(data["invariant"] is True, f"engine incremental invariant failed: {data}")
        return data

    def stats(self):
        self.send("stats")
        line = self.until(lambda item: item.startswith("{") or item.startswith("stats {"))[-1]
        return json.loads(line[line.index("{"):])

    def close(self, eof=False):
        if self.process.poll() is None:
            if eof:
                self.record("stdin", "<EOF>")
                self.process.stdin.close()
            else:
                self.send("quit")
            try:
                self.process.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                self.terminate()
                raise AssertionError("engine failed to terminate after quit/EOF")
        require(self.process.returncode == 0, f"engine exited {self.process.returncode}; stderr={self.stderr[-5:]}")
        self.finish()
        survivors = []
        for pid, start_time in self.descendants.items():
            try:
                stat = (Path("/proc") / str(pid) / "stat").read_text().split()
                if stat[21] == start_time and stat[2] != "Z":
                    survivors.append(pid)
            except OSError:
                pass
        require(not survivors, f"engine left observed child processes alive after termination: {survivors}")

    def finish(self):
        self.sampling = False
        self.sampler.join(timeout=0.1)
        for reader in self.readers:
            reader.join(timeout=0.2)
        self.record("exit", {"code": self.process.returncode, "peak_threads": self.peak_threads,
                             "observed_child_processes": sorted(self.descendants)})
        self.log.close()

    def terminate(self):
        if self.process.poll() is None:
            if os.name == "posix":
                os.killpg(self.process.pid, signal.SIGKILL)
            else:
                self.process.kill()
            self.process.wait(timeout=2)
        if not self.log.closed:
            self.finish()


def parse_info(lines, board):
    records = []
    for line in lines:
        if not line.startswith("info "):
            continue
        fields = line.split()
        if "depth" not in fields or "score" not in fields:
            continue
        depth = int(fields[fields.index("depth") + 1])
        score_index = fields.index("score")
        score_type, score = fields[score_index + 1], int(fields[score_index + 2])
        require(score_type in ("cp", "mate"), f"invalid UCI score kind: {line}")
        if score_type == "cp":
            require(abs(score) < 30000, f"cp score crosses reserved mate range: {line}")
        pv = fields[fields.index("pv") + 1:] if "pv" in fields else []
        position = board
        for move in pv:
            require(MOVE.fullmatch(move), f"invalid PV token {move!r}: {line}")
            position = position.play(move)
        records.append({"depth": depth, "kind": score_type, "score": score, "pv": pv,
                        "nodes": int(fields[fields.index("nodes") + 1]) if "nodes" in fields else None,
                        "bound": "lower" if "lowerbound" in fields else "upper" if "upperbound" in fields else "exact"})
    return records


def search(engine, board, command, timeout=None, require_info=True):
    start = time.monotonic()
    engine.send(command)
    lines = engine.until(lambda line: line.startswith("bestmove "), timeout)
    elapsed = time.monotonic() - start
    best_lines = [line for line in lines if line.startswith("bestmove ")]
    require(len(best_lines) == 1, "search emitted multiple bestmove lines")
    fields = best_lines[0].split()
    require(len(fields) >= 2, "bestmove lacks a move")
    best = fields[1]
    legal = {str(move) for move in board.legal_moves()}
    require(best in legal if legal else best == "0000", f"illegal bestmove {best!r} in {board.fen()}")
    info = parse_info(lines, board)
    if require_info and legal:
        require(info, "development search emitted no completed score/depth")
        require(any(item["depth"] > 0 for item in info), "search completed no positive depth")
        require(all(item["pv"] for item in info if item["depth"] > 0), "completed search omitted legal PV")
    require(not any(line.startswith("bestmove ") for line in engine.quiet()),
            "duplicate or stale bestmove arrived after search completion")
    engine.assert_threads_stable()
    return {"bestmove": best, "elapsed_seconds": elapsed, "info": info}


def protocol(engine, _):
    handshake = engine.initialize()
    for command in ("this_command_is_unsupported", "setoption name Unknown value 123", "stop", "ucinewgame"):
        engine.send(command)
    require(not any(line.startswith("bestmove ") for line in engine.ready()), "idle command emitted bestmove")
    board, moves = Board.from_fen(), ["e2e4", "e7e5", "g1f3", "b8c6"]
    for move in moves:
        board = board.play(move)
    engine.position(moves=moves)
    result = search(engine, board, "go wtime 1000 btime 1000 winc 0 binc 0", require_info=False)
    require(result["elapsed_seconds"] < 3.0, "clocked go exceeded bounded clock allowance")
    engine.position()
    zero_clock = search(engine, Board.from_fen(), "go wtime 0 btime 0 winc 0 binc 0",
                        timeout=1.5, require_info=False)
    require(zero_clock["elapsed_seconds"] < 1.5, "zero-clock go did not honor an immediate bounded deadline")
    result["zero_clock"] = zero_clock
    result["uci_options"] = [line for line in handshake if line.startswith("option ")]
    return result


def rules(engine, options):
    engine.initialize()
    counts = []
    for label, fen, totals in PERFT:
        engine.position(fen)
        for depth, expected in enumerate(totals[:3 if options.quick else len(totals)], 1):
            response = engine.dev(f"perft {depth}", "perft ")
            fields = response.split()
            require(len(fields) == 3 and int(fields[1]) == depth, f"invalid perft response {response!r}")
            actual = int(fields[2])
            require(actual == expected, f"{label} depth {depth}: {actual} != {expected}")
            counts.append({"position": label, "depth": depth, "nodes": actual})
        expected = {str(move) for move in Board.from_fen(fen).legal_moves()}
        actual = engine.dev("legal", "legal").split()[1:]
        require(len(actual) == len(set(actual)), f"duplicate legal moves in {label}")
        require(set(actual) == expected, f"legal mismatch {label}: missing={expected-set(actual)} extra={set(actual)-expected}")
    # Isolate EP discovered check, promotion choices, pinned king shielding and
    # castling through check. Exact sets come from the independent oracle.
    edges = {
        "ep-discovered-check": "k7/8/8/4KPpr/8/8/8/8 w - g6 0 1",
        "ep-legal": "7k/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
        "promotion-capture": "1r5k/P7/8/8/8/8/8/4K3 w - - 0 1",
        "castle-through-check": "r3k2r/8/8/8/8/5r2/8/R3K2R w KQkq - 0 1",
        "absolute-pin": "4r2k/8/8/8/8/8/4R3/4K3 w - - 0 1",
        "castle-capture-right": "r3k2r/8/8/8/8/8/1B6/4K3 w kq - 0 1",
    }
    for label, fen in edges.items():
        board = Board.from_fen(fen)
        engine.position(fen)
        expected = {str(move) for move in board.legal_moves()}
        actual = engine.dev("legal", "legal").split()[1:]
        require(set(actual) == expected and len(actual) == len(expected),
                f"{label}: missing={expected-set(actual)} extra={set(actual)-expected}")
        actual_count = int(engine.dev("perft 2", "perft ").split()[2])
        require(actual_count == board.perft(2), f"{label} perft2 mismatch")
    return {"reference_perft": counts, "edge_positions": list(edges)}


def state(engine, options):
    engine.initialize()
    engine.position()
    baseline = engine.state()
    def fen_state(fen):
        engine.position(fen)
        return engine.state()

    hash_cases = (
        ("side", START, START.replace(" w ", " b ")),
        ("castling", PERFT[1][1], PERFT[1][1].replace(" KQkq ", " - ")),
        ("legal-en-passant", "7k/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "7k/8/8/3pP3/8/8/8/4K3 w - - 0 1"),
        ("piece-placement", "7k/8/8/8/8/8/P7/4K3 w - - 0 1", "7k/8/8/8/8/P7/8/4K3 w - - 0 1"),
    )
    for label, first, second in hash_cases:
        require(fen_state(first)["hash"] != fen_state(second)["hash"], f"hash failed to distinguish {label}")
    queen = "7k/8/8/8/8/8/1Q6/K7 w - - 0 1"
    rook = queen.replace("1Q6", "1R6")
    q_eval, r_eval = fen_state(queen)["eval"], fen_state(rook)["eval"]
    require(q_eval > r_eval and q_eval > 0, "evaluation failed simple queen-versus-rook material ordering")
    require(fen_state(queen.replace(" w ", " b "))["eval"] < 0, "state evaluation is not from side-to-move perspective")
    rng, board, moves, checked = random.Random(20261020), Board.from_fen(), [], 0
    for ply in range(24 if options.quick else 48):
        legal = list(board.legal_moves())
        if not legal:
            break
        move = rng.choice(legal)
        moves.append(str(move))
        board = board.apply(move)
        engine.position(moves=moves)
        replay = engine.state()
        require(replay["halfmove"] == board.halfmove, f"halfmove mismatch after {moves}")
        if "fen" in replay:
            require(replay["fen"] == board.fen(), f"FEN mismatch: {replay['fen']} != {board.fen()}")
        engine.position(board.fen())
        reconstructed = engine.state()
        for key in ("hash", "eval", "pawn_hash"):
            if key in replay:
                require(reconstructed.get(key) == replay[key], f"{key} differs between replay and FEN at ply {ply+1}")
        checked += 1
    cycle = ["g1f3", "g8f6", "f3g1", "f6g8"] * 2
    engine.position(moves=cycle[:4])
    require(not engine.state()["draw"], "twofold repetition incorrectly adjudicated as root draw")
    engine.position(moves=cycle)
    repetition = engine.state()
    require(repetition["hash"] == baseline["hash"], "reversible cycle changed position hash")
    require(repetition["halfmove"] == 8, "reversible cycle halfmove incorrect")
    require(bool(repetition["draw"]), "threefold repetition not recognized")
    # A rule-drawn root has no searched continuation to publish. Empty PV is
    # legitimate here, unlike a completed nonterminal search iteration.
    drawn = search(engine, Board.from_fen(), "go depth 3", require_info=False)
    require(drawn["info"], "development draw search omitted its root score")
    require(drawn["info"][-1]["kind"] == "cp" and drawn["info"][-1]["score"] == 0,
            "threefold root search did not return draw score")
    engine.position(START)
    require(not engine.state()["draw"], "FEN reset retained repetition history")
    ep_cycle = ["e2e4", "g8f6", "g1f3", "f6g8", "f3g1", "g8f6", "g1f3", "f6g8", "f3g1"]
    engine.position(moves=ep_cycle[:5])
    require(not engine.state()["draw"], "uncapturable EP cycle was adjudicated before threefold")
    engine.position(moves=ep_cycle)
    require(bool(engine.state()["draw"]), "irrelevant EP target split otherwise identical repetition positions")
    castle_start = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    castle_cycle = ["e1f1", "e8f8", "f1e1", "f8e8"]
    engine.position(castle_start, castle_cycle * 2)
    require(not engine.state()["draw"], "lost castling rights were ignored in repetition identity")
    engine.position(castle_start, castle_cycle * 3)
    require(bool(engine.state()["draw"]), "threefold after castling-right loss was not recognized")
    fifty = "7k/8/8/8/8/8/8/R3K3 w - - 100 80"
    engine.position(fifty.replace(" 100 80", " 99 80"))
    require(not engine.state()["draw"], "49.5 moves incorrectly adjudicated as a 50-move draw")
    engine.position(fifty)
    require(bool(engine.state()["draw"]), "50-move draw not recognized")
    fifty_search = search(engine, Board.from_fen(fifty), "go depth 3", require_info=False)
    require(fifty_search["info"], "development 50-move draw search omitted its root score")
    require(fifty_search["info"][-1]["kind"] == "cp" and fifty_search["info"][-1]["score"] == 0,
            "50-move root search did not return draw score")
    engine.position(moves=cycle + ["e2e4"])
    reset = engine.state()
    require(reset["halfmove"] == 0 and not reset["draw"], "pawn move did not reset draw clock/history")
    engine.position(moves=["e2e4", "d7d5", "e4d5"])
    require(engine.state()["halfmove"] == 0, "capture did not reset halfmove")
    return {"replay_fen_positions": checked, "threefold": repetition, "fifty_move": fifty_search}


def searching(engine, _):
    engine.initialize()
    engine.position()
    board = Board.from_fen()
    completed = search(engine, board, "go depth 4")
    require(completed["info"][-1]["depth"] == 4, "fixed-depth search did not complete depth 4")
    require(all(a["depth"] <= b["depth"] for a, b in zip(completed["info"], completed["info"][1:])),
            "reported completed depths regressed")
    limited = search(engine, board, "go nodes 1000 depth 30")
    require(limited["elapsed_seconds"] < 3.0, "node-limited search did not terminate promptly")
    final_stats = engine.stats()
    workers = final_stats.get("search_workers", final_stats.get("workers", 1))
    require(isinstance(workers, int) and workers > 0, "stats omitted a valid search worker count")
    # C workers can pass the stop check together before atomic increment. Its
    # declared maximum overshoot is workers-1. Rust CAS reservation is stricter.
    node_ceiling = 1000 + workers - 1
    require(isinstance(final_stats.get("nodes"), int) and 0 < final_stats["nodes"] <= node_ceiling,
            f"final work exceeded node limit including cancellation tolerance: {final_stats}")
    require(limited["info"] and all(isinstance(item["nodes"], int) and 0 <= item["nodes"] <= node_ceiling
                                    for item in limited["info"]),
            "node-limited search reported completed work outside its 1000-node budget")
    limited["final_stats"], limited["allowed_node_ceiling"] = final_stats, node_ceiling
    mate_fen = "7k/5Q2/6K1/8/8/8/8/8 w - - 0 1"
    mate_board = Board.from_fen(mate_fen)
    engine.position(mate_fen)
    mate = search(engine, mate_board, "go depth 3")
    child = mate_board.play(mate["bestmove"])
    require(child.in_check() and not list(child.legal_moves()), "mate-in-one position did not select checkmate")
    require(mate["info"][-1]["kind"] == "mate" and mate["info"][-1]["score"] == 1,
            "mate score did not encode one-move distance")
    terminal_results = []
    for name, fen in (("mate", "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"),
                      ("stalemate", "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")):
        engine.position(fen)
        result = search(engine, Board.from_fen(fen), "go depth 3", require_info=False)
        require(result["bestmove"] == "0000", f"{name} emitted a move")
        if name == "mate":
            require(result["info"] and result["info"][-1]["kind"] == "mate" and result["info"][-1]["score"] == 0,
                    "already checkmated root did not report mate distance zero")
        if name == "stalemate" and result["info"]:
            require(result["info"][-1]["kind"] == "cp" and result["info"][-1]["score"] == 0,
                    "stalemate score is not draw")
        terminal_results.append({"kind": name, **result})
    mate_boundary = "7k/6Q1/6K1/8/8/8/8/8 b - - 100 80"
    engine.position(mate_boundary)
    precedence = search(engine, Board.from_fen(mate_boundary), "go depth 3", require_info=False)
    require(precedence["info"] and precedence["info"][-1]["kind"] == "mate" and precedence["info"][-1]["score"] == 0,
            "50-move clock incorrectly took precedence over completed checkmate")
    engine.position()
    timed = search(engine, board, "go movetime 80")
    require(timed["elapsed_seconds"] < 1.5, "movetime deadline exceeded allowance")
    return {"depth": completed, "nodes": limited, "mate_in_one": mate, "terminal": terminal_results,
            "mate_at_fifty_move_boundary": precedence, "timed": timed}


def lifecycle(engine, options):
    engine.initialize()
    board = Board.from_fen()
    rounds = []
    # Each new position is sent only after the previous epoch's bestmove. A
    # second scenario below queues position/go behind stop to detect stale work.
    for index in range(3):
        engine.position()
        engine.send("go infinite")
        time.sleep(0.04)
        engine.assert_threads_stable()
        before_stop = engine.quiet(0.001)
        prematurely_completed = [line for line in before_stop if line.startswith("bestmove ")]
        if engine.spec.get("profile", "dev") != "shipping":
            require(not prematurely_completed, "development infinite search completed before stop; active cancellation unproven")
        engine.send("stop")
        lines = before_stop if prematurely_completed else before_stop + engine.until(lambda line: line.startswith("bestmove "), timeout=2)
        require(sum(line.startswith("bestmove ") for line in lines) == 1, "stop emitted duplicate bestmove")
        move = lines[-1].split()[1]
        board.play(move)
        parse_info(lines, board)
        require(not any(line.startswith("bestmove ") for line in engine.ready()), "old epoch bestmove followed readyok")
        require(not any(line.startswith("bestmove ") for line in engine.quiet()), "old epoch bestmove leaked after stop")
        rounds.append({"round": index, "bestmove": move, "active_before_stop": not bool(prematurely_completed)})
    engine.position()
    engine.send("go infinite")
    time.sleep(0.03)
    engine.send("stop")
    # All black replies at the new root are black moves. A stale white result
    # appearing after the old bestmove is consumed cannot pass this assertion.
    engine.position(moves=["e2e4"])
    engine.send("go wtime 1000 btime 1000 winc 0 binc 0")
    old = engine.until(lambda line: line.startswith("bestmove "), timeout=2)
    board.play(old[-1].split()[1])
    new_board = board.play("e2e4")
    new = engine.until(lambda line: line.startswith("bestmove "), timeout=3)
    new_board.play(new[-1].split()[1])
    parse_info(new, new_board)
    require(not any(line.startswith("bestmove ") for line in engine.quiet()), "queued search emitted duplicate/stale bestmove")
    direct = []
    for reset in ("position", "ucinewgame"):
        engine.position()
        engine.send("go infinite")
        time.sleep(0.04)
        before_reset = engine.quiet(0.001)
        if engine.spec.get("profile", "dev") != "shipping":
            require(not any(line.startswith("bestmove ") for line in before_reset),
                    f"development search completed before active {reset}")
        if reset == "ucinewgame":
            engine.send("ucinewgame")
        engine.position(moves=["e2e4"])
        engine.send("go wtime 1000 btime 1000 winc 0 binc 0")
        prior_best = [line for line in before_reset if line.startswith("bestmove ")]
        old_lines = before_reset if prior_best else before_reset + engine.until(lambda line: line.startswith("bestmove "), timeout=2)
        old_move = [line for line in old_lines if line.startswith("bestmove ")][-1].split()[1]
        board.play(old_move)
        new_lines = engine.until(lambda line: line.startswith("bestmove "), timeout=3)
        new_move = new_lines[-1].split()[1]
        new_board.play(new_move)
        parse_info(new_lines, new_board)
        require(not any(line.startswith("bestmove ") for line in engine.quiet()),
                f"stale result survived direct {reset} epoch reset")
        direct.append({"command": reset, "old_bestmove": old_move, "new_bestmove": new_move})
    return {"stop_rounds": rounds, "queued_new_root_bestmove": new[-1].split()[1], "direct_resets": direct,
            "observed_peak_threads": engine.peak_threads, "configured_workers": engine.spec.get("workers")}


def selfplay(engine, options):
    engine.initialize()
    board, moves, history = Board.from_fen(), [], []
    for ply in range(options.plies):
        legal = list(board.legal_moves())
        if not legal:
            break
        engine.position(moves=moves)
        result = search(engine, board, "go wtime 1000 btime 1000 winc 0 binc 0", require_info=False)
        board = board.play(result["bestmove"])
        moves.append(result["bestmove"])
        history.append({"ply": ply + 1, "move": result["bestmove"], "elapsed": result["elapsed_seconds"]})
    require(len(moves) == options.plies or not list(board.legal_moves()), "selfplay ended without legal terminal state")
    return {"moves": moves, "history": history, "final_fen": board.fen(),
            "scope": "bounded protocol/legal-move smoke; no Elo or strength claim"}


def shutdown(engine, _):
    engine.initialize()
    engine.position()
    engine.send("go infinite")
    time.sleep(0.04)
    engine.assert_threads_stable()
    before_eof = engine.quiet(0.001)
    if engine.spec.get("profile", "dev") != "shipping":
        require(not any(line.startswith("bestmove ") for line in before_eof), "development search completed before EOF; active termination unproven")
    engine.close(eof=True)
    final = before_eof + engine.drain()
    best = [line.split()[1] for line in final if line.startswith("bestmove ")]
    require(len(best) == 1, f"EOF epoch produced {len(best)} bestmoves")
    Board.from_fen().play(best[0])
    return {"input_eof_while_searching": "process_exited", "bestmove": best[0], "peak_threads": engine.peak_threads}


def quit_searching(engine, _):
    engine.initialize()
    engine.position()
    engine.send("go infinite")
    time.sleep(0.04)
    engine.assert_threads_stable()
    before_quit = engine.quiet(0.001)
    if engine.spec.get("profile", "dev") != "shipping":
        require(not any(line.startswith("bestmove ") for line in before_quit), "development search completed before quit; active termination unproven")
    engine.close()
    final = before_quit + engine.drain()
    best = [line.split()[1] for line in final if line.startswith("bestmove ")]
    require(len(best) == 1, f"quit epoch produced {len(best)} bestmoves")
    Board.from_fen().play(best[0])
    return {"quit_while_searching": "process_exited", "bestmove": best[0], "peak_threads": engine.peak_threads}


CHECKS = (("protocol", protocol, False), ("rules", rules, True), ("state", state, True),
          ("search", searching, True), ("lifecycle", lifecycle, False),
          ("selfplay", selfplay, False), ("eof", shutdown, False), ("quit", quit_searching, False))


def load_specs(args):
    specs = []
    if args.manifest:
        data = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        specs.extend(data["engines"] if isinstance(data, dict) else data)
    for item in args.engine:
        name, path = item.split("=", 1) if "=" in item else (Path(item).name, item)
        specs.append({"id": name, "command": [path], "profile": args.profile})
    for spec in specs:
        require(isinstance(spec.get("id"), str) and isinstance(spec.get("command"), list)
                and all(isinstance(item, str) for item in spec["command"]), "invalid engine manifest entry")
        if args.startup_threads is not None:
            require(1 <= args.startup_threads <= 513, "startup thread total must be within 1..513")
            spec["startup_threads"] = args.startup_threads
    require(len({spec["id"] for spec in specs}) == len(specs), "duplicate engine identifiers")
    if args.select:
        specs = [spec for spec in specs if spec["id"] in args.select]
    expanded, args.artifact_reuse = [], []
    for spec in specs:
        expanded.append(spec)
        program = Path(spec["command"][0])
        actual_hash = hashlib.sha256(program.read_bytes()).hexdigest() if program.is_file() else None
        seen = {actual_hash: spec["id"]} if actual_hash else {}
        for artifact in spec.get("artifacts", []):
            form = artifact.get("source_form")
            if form not in ("original", "compact") or artifact.get("format") != "native-elf" or artifact.get("returncode") != 0:
                continue
            path = Path(artifact["path"])
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            require(digest == artifact["sha256"], f"artifact bytes changed since build evidence: {path}")
            if str(path) == spec["command"][0]:
                continue
            if digest in seen:
                args.artifact_reuse.append({"engine": spec["id"], "source_form": form, "path": str(path),
                                           "program_sha256": digest, "verified_as": seen[digest],
                                           "reason": "actual executable bytes identical; reuse is limited to these exact bytes"})
                continue
            identifier = spec["id"] + "-" + form
            require(not any(item["id"] == identifier for item in expanded), f"duplicate expanded engine id {identifier}")
            expanded.append({**spec, "id": identifier, "command": [str(path)], "cwd": str(path.parent),
                             "source_form": form, "artifacts": []})
            seen[digest] = identifier
    return expanded


def play_match(left, right, options, output):
    """Two owned processes, then colours exchanged; bounded legal play only."""
    record = {"left": left["id"], "right": right["id"], "games": [],
              "scope": "colour-exchanged protocol smoke; no rating estimate", "passed": True}
    for game, ordered in enumerate(((left, right), (right, left)), 1):
        players, board, moves, positions = [], Board.from_fen(), [], []
        started = time.monotonic()
        evidence = {"white": ordered[0]["id"], "black": ordered[1]["id"]}
        try:
            for colour, spec in enumerate(ordered):
                label = re.sub(r"[^A-Za-z0-9_.-]", "_", f"match-{left['id']}-{right['id']}-{game}-{colour}")
                process = Engine(spec, output, label, options.timeout)
                players.append(process)
                process.initialize()
            for ply in range(options.plies):
                if not list(board.legal_moves()):
                    break
                player = players[0 if board.turn else 1]
                player.position(moves=moves)
                result = search(player, board, "go wtime 1000 btime 1000 winc 0 binc 0", require_info=False)
                board = board.play(result["bestmove"])
                moves.append(result["bestmove"])
                positions.append({"ply": ply + 1, "bestmove": result["bestmove"], "fen": board.fen(),
                                  "elapsed_seconds": result["elapsed_seconds"]})
            for process in players:
                process.close()
            evidence.update(status="pass", moves=moves, positions=positions, final_fen=board.fen())
        except Exception as error:
            evidence.update(status="fail", error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
            record["passed"] = False
        finally:
            for process in players:
                if not process.log.closed:
                    process.terminate()
        evidence["elapsed_seconds"] = round(time.monotonic() - started, 4)
        record["games"].append(evidence)
        print(f"match {evidence['white']} vs {evidence['black']}: {evidence['status']}", flush=True)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--select", action="append", help="select a manifest engine id; repeatable")
    parser.add_argument("--match", action="append", default=[], metavar="LEFT,RIGHT",
                        help="also run two colour-exchanged bounded games for selected engine ids")
    parser.add_argument("--profile", choices=("dev", "shipping"), default="dev")
    parser.add_argument("--startup-threads", type=int, help="require this total to exist before first input and preserve its task IDs")
    parser.add_argument("--suite", choices=("all", "dev", "shipping"), default="all")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--plies", type=int, default=12)
    parser.add_argument("--quick", action="store_true", help="perft <=3, 24 replay positions")
    parser.add_argument("--oracle-only", action="store_true")
    parser.add_argument("--oracle-deep", action="store_true", help="independently verify all frozen perft totals")
    args = parser.parse_args()
    output = args.out.resolve()
    require(output != ROOT and ROOT not in output.parents, "--out must be outside the Git checkout")
    require(0 < args.timeout <= 60 and 0 < args.plies <= 128, "invalid bounded test budget")
    output.mkdir(parents=True, exist_ok=True)
    specs = load_specs(args)
    require(specs or args.oracle_only, "provide --engine/--manifest or --oracle-only")
    report = {"schema": 1, "scope": "black-box correctness and bounded local resource evidence",
              "excluded": ["Elo/strength ranking", "512-hardware-thread scalability", "training", "AWS",
                           "algorithm-specific SEE/singular/SIMD/PALS/MTD contracts without separate diagnostic evidence"],
              "host": {"platform": sys.platform, "python": sys.version.split()[0]},
              "oracle": self_check(args.oracle_deep), "engines": [], "matches": [],
              "identical_artifact_reuse": args.artifact_reuse, "passed": True}
    atomic_json(output / "results.json", report)
    for spec in specs:
        entry = {"id": spec["id"], "command": spec["command"], "profile": spec.get("profile", "dev"), "checks": []}
        binary = Path(spec["command"][0])
        if binary.is_file():
            entry["program_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
        for name, check, dev_only in CHECKS:
            if dev_only and (args.suite == "shipping" or entry["profile"] == "shipping"):
                continue
            if args.suite == "dev" and not dev_only:
                continue
            label = re.sub(r"[^A-Za-z0-9_.-]", "_", f"{spec['id']}-{name}")
            process, started = None, time.monotonic()
            result = {"name": name, "transcript": str(output / (label + ".jsonl"))}
            try:
                process = Engine(spec, output, label, args.timeout)
                result["evidence"] = check(process, args)
                if not process.log.closed:
                    process.close()
                result["peak_threads"] = process.peak_threads
                if process.startup_task_ids is not None:
                    result["startup_thread_ids"] = sorted(process.startup_task_ids)
                maximum = spec.get("max_threads")
                if maximum is not None:
                    require(process.peak_threads <= maximum, f"observed {process.peak_threads} threads exceeds profile total {maximum}")
                result["status"] = "pass"
            except Exception as error:
                result.update(status="fail", error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
                report["passed"] = False
            finally:
                if process is not None and not process.log.closed:
                    process.terminate()
            result["elapsed_seconds"] = round(time.monotonic() - started, 4)
            entry["checks"].append(result)
            print(f"{spec['id']} {name}: {result['status']} ({result['elapsed_seconds']:.2f}s)", flush=True)
            if result["status"] != "pass":
                print(result["error"], flush=True)
            atomic_json(output / "results.json", {**report, "engines": report["engines"] + [entry]})
        report["engines"].append(entry)
        atomic_json(output / "results.json", report)
    by_id = {spec["id"]: spec for spec in specs}
    for pair in args.match:
        ids = pair.split(",")
        require(len(ids) == 2 and all(item in by_id for item in ids), f"unknown match pair {pair!r}")
        record = play_match(by_id[ids[0]], by_id[ids[1]], args, output)
        report["matches"].append(record)
        report["passed"] = report["passed"] and record["passed"]
        atomic_json(output / "results.json", report)
    print(str(output / "results.json"), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
