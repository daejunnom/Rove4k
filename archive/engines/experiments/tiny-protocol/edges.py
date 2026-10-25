#!/usr/bin/env python3
"""Bounded raw-byte checks of actual Tiny A/D protocol candidate commands.

Linux only, Python standard library only. The only imported chess implementation
is the independent test oracle. This script never builds or reads engine source.
Pass a JSON object with an ``engines`` list; each entry needs id, profile, dev,
command (an argv list), and workers. Reports must be outside the checkout.
Timing is used solely for bounded liveness and pre-active observation, never for
NPS, strength, or performance comparisons. A bestmove alone proves no stop cause.
"""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import queue
import select
import signal
import subprocess
import sys
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "engines" / "tests"))
from chess_oracle import Board, START  # noqa: E402


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def proc_stat(pid):
    # comm may contain whitespace or ')'; split after its final closing paren.
    text = (Path("/proc") / str(pid) / "stat").read_text()
    fields = text[text.rindex(")") + 2:].split()
    return {"start": fields[19], "cpu": int(fields[11]) + int(fields[12])}


def family(pid):
    result, pending = set(), [pid]
    while pending:
        current = pending.pop()
        if current in result:
            continue
        try:
            proc_stat(current)
            tasks = (Path("/proc") / str(current) / "task").iterdir()
            children = []
            for task in tasks:
                try:
                    children.extend((task / "children").read_text().split())
                except OSError:
                    pass
        except (OSError, ValueError):
            continue
        result.add(current)
        pending.extend(int(child) for child in children)
    return result


class RawEngine:
    """Own one process group, nonblocking raw input, bounded output readers."""

    def __init__(self, spec, output, label, timeout):
        self.spec, self.timeout = spec, timeout
        self.started = time.monotonic()
        self.events = []
        self.lock = threading.Lock()
        self.log = (output / (label + ".jsonl")).open("w")
        self.lines = queue.Queue()
        self.error = None
        self.total_output = 0
        self.runtime_pid = None
        self.startup_tids = None
        self.closed = False
        self.record("launch", spec["command"])
        try:
            if "expected_program_sha256" in spec:
                actual = hashlib.sha256(Path(spec["command"][0]).read_bytes()).hexdigest()
                require(actual == spec["expected_program_sha256"], "manifest program hash mismatch")
                self.record("command_identity", {"sha256": actual})
            self.process = subprocess.Popen(spec["command"], cwd=spec.get("cwd"),
                                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, start_new_session=True,
                                            bufsize=0)
        except Exception:
            self.log.close()
            raise
        os.set_blocking(self.process.stdin.fileno(), False)
        self.readers = []
        for name in ("stdout", "stderr"):
            thread = threading.Thread(target=self.read, args=(name,), daemon=True)
            thread.start()
            self.readers.append(thread)

    def record(self, direction, data):
        with self.lock:
            event = {"t": round(time.monotonic() - self.started, 6),
                     "direction": direction, "value": data}
            self.events.append(event)
            self.log.write(json.dumps(event) + "\n")
            self.log.flush()

    def read(self, name):
        stream = getattr(self.process, name)
        try:
            while True:
                raw = stream.readline(65537)
                if not raw:
                    break
                self.total_output += len(raw)
                if len(raw) > 65536 or self.total_output > 2 * 1024 * 1024:
                    raise RuntimeError("output bound exceeded")
                line = raw.rstrip(b"\r\n").decode("utf-8", errors="strict")
                self.record(name, line)
                if name == "stdout":
                    self.lines.put(line)
        except Exception as exc:
            self.error = str(exc)
            self.lines.put(exc)
        finally:
            stream.close()
            if name == "stdout":
                self.lines.put(EOFError("stdout closed"))

    def send(self, data):
        require(isinstance(data, bytes), "raw input must be bytes")
        require(self.process.poll() is None, "engine exited before input")
        self.record("stdin-bytes", {"bytes": len(data), "base64": base64.b64encode(data).decode()})
        pending, end = memoryview(data), time.monotonic() + self.timeout
        while pending:
            remaining = end - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("raw input write blocked")
            _, writable, _ = select.select([], [self.process.stdin], [], remaining)
            if writable:
                try:
                    count = os.write(self.process.stdin.fileno(), pending)
                except BlockingIOError:
                    continue
                require(count > 0, "empty pipe write")
                pending = pending[count:]

    def until(self, predicate, timeout=None):
        end, seen = time.monotonic() + (self.timeout if timeout is None else timeout), []
        while time.monotonic() < end:
            try:
                item = self.lines.get(timeout=max(.001, end - time.monotonic()))
            except queue.Empty:
                break
            if isinstance(item, Exception):
                raise item
            seen.append(item)
            if predicate(item):
                return seen
        raise TimeoutError("response timeout; last lines: " + repr(seen[-6:]))

    def quiet(self, duration=.035):
        end, seen = time.monotonic() + duration, []
        while time.monotonic() < end:
            try:
                item = self.lines.get(timeout=max(.001, end - time.monotonic()))
            except queue.Empty:
                break
            if isinstance(item, Exception):
                raise item
            seen.append(item)
        return seen

    def tids(self):
        if self.runtime_pid is None:
            return set()
        try:
            return {int(path.name) for path in (Path("/proc") / str(self.runtime_pid) / "task").iterdir()}
        except OSError:
            return set()

    def stable(self):
        require(self.tids() == self.startup_tids, "fixed startup worker TIDs changed")

    def initialize(self):
        expected = self.spec["workers"] + 1
        end = time.monotonic() + self.spec.get("startup_timeout", self.timeout)
        while time.monotonic() < end:
            require(self.process.poll() is None, "engine exited during startup")
            matches = []
            for pid in family(self.process.pid):
                try:
                    tasks = {int(p.name) for p in (Path("/proc") / str(pid) / "task").iterdir()}
                except OSError:
                    continue
                if len(tasks) == expected:
                    matches.append((pid, tasks))
            require(len(matches) <= 1, "multiple possible engine worker pools")
            if matches:
                self.runtime_pid, self.startup_tids = matches[0]
                self.runtime_start = proc_stat(self.runtime_pid)["start"]
                executable = Path("/proc") / str(self.runtime_pid) / "exe"
                self.record("startup", {"pid": self.runtime_pid, "tids": sorted(self.startup_tids),
                                        "exe_sha256": hashlib.sha256(executable.read_bytes()).hexdigest()})
                break
            time.sleep(.005)
        require(self.startup_tids is not None, "fixed worker pool absent before first command")
        self.send(b"uci\nisready\n")
        lines = self.until(lambda line: line == "readyok")
        require(lines.count("uciok") == 1, "startup must emit one uciok")
        self.stable()

    def ready(self, prefix=b""):
        self.send(prefix + b"isready\n")
        lines = self.until(lambda line: line == "readyok")
        self.stable()
        return lines

    def best(self, board, timeout=None):
        lines = self.until(lambda line: line.startswith("bestmove "), timeout)
        publications = [line for line in lines if line.startswith("bestmove ")]
        require(len(publications) == 1, "multiple result publications in epoch")
        fields = publications[0].split()
        require(len(fields) == 2, "malformed bestmove")
        legal = {str(move) for move in board.legal_moves()}
        require(fields[1] in legal if legal else fields[1] == "0000", "bestmove is not oracle-legal")
        self.stable()
        return publications[0]

    def state(self):
        self.send(b"state\n")
        raw = self.until(lambda line: line.startswith("{"))[-1]
        result = json.loads(raw)
        require(result.get("invariant") is True, "incremental invariant failed")
        require(all(k in result for k in ("hash", "halfmove", "eval", "draw")), "incomplete DEV state")
        return result

    def legal(self, board):
        self.send(b"legal\n")
        raw = self.until(lambda line: line == "legal" or line.startswith("legal "))[-1].split()[1:]
        expected = {str(move) for move in board.legal_moves()}
        require(len(raw) == len(set(raw)) and set(raw) == expected, "DEV legal moves differ from independent oracle")
        return sorted(raw)

    def active_observation(self, window=.25):
        """Observe CPU progress by an existing search worker before sending stop."""
        before, after = {}, {}
        for tid in self.startup_tids - {self.runtime_pid}:
            try:
                before[tid] = proc_stat(tid)["cpu"]
            except OSError:
                pass
        end = time.monotonic() + window
        while time.monotonic() < end:
            require(not self.quiet(.012), "infinite epoch published before active observation")
            self.stable()
            for tid in before:
                after[tid] = proc_stat(tid)["cpu"]
            if any(after.get(tid, 0) > count for tid, count in before.items()):
                break
        observed = any(after.get(tid, 0) > count for tid, count in before.items())
        return {"worker_cpu_progress_observed": observed,
                "ticks_before": before, "ticks_after": after,
                "stop_causal_link": "unproven", "no_completed_result_before_control": True}

    def finish(self, final=b"quit\n"):
        if final is None:
            self.process.stdin.close()
        else:
            self.send(final)
            self.process.stdin.close()
        code = self.process.wait(timeout=self.timeout)
        require(code == 0, "engine exit status " + str(code))
        for reader in self.readers:
            reader.join(timeout=1)
            require(not reader.is_alive(), "output reader did not finish")
        require(self.error is None, "output reader error: " + str(self.error))
        if self.runtime_pid is not None:
            try:
                same = proc_stat(self.runtime_pid)["start"] == self.runtime_start
            except OSError:
                same = False
            require(not same, "runtime process remains after launcher exit")
        self.record("exit", {"code": code, "readers_joined": True, "runtime_process_absent": True})
        return [item["value"] for item in self.events if item["direction"] == "stdout"]

    def cleanup(self):
        if self.closed:
            return
        self.closed = True
        # Even a wrapper which already exited may have left its owned group.
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            self.process.wait(timeout=.3)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.process.wait(timeout=2)
        if not self.process.stdin.closed:
            self.process.stdin.close()
        for reader in self.readers:
            reader.join(timeout=2)
            require(not reader.is_alive(), "owned output reader did not join during cleanup")
        self.log.close()


def framing(engine, spec):
    fixtures = [
        ("nul-prefix", b"quit\0\n"),
        ("nul-hidden-tail", b"isready\0quit\n"),
        ("long-drain-tail", b"x" * 32768 + b"quit\n"),
        ("over-limit-prefix", b"isready" + b" " * 32761 + b"\n"),
    ]
    for label, raw in fixtures:
        lines = engine.ready(raw)
        require(lines == ["readyok"], label + " dispatched a bad line or failed full drain")
    engine.send(b"isready" + b" " * 32760 + b"\n")
    require(engine.until(lambda s: s == "readyok") == ["readyok"], "32767-byte valid line rejected")
    exact = (b"quitx\nquit extra\nstopwatch\nstop extra\nucix\nuci extra\n"
             b"isreadyx\nisready extra\nucinewgamex\nucinewgame extra\n")
    require(engine.ready(exact) == ["readyok"], "no-argument exact command contract violated")
    if not spec["dev"]:
        engine.send(b" \t uci\t\r\n\t isready\t \r\n")
        lines = engine.until(lambda s: s == "readyok")
        require(lines.count("uciok") == 1, "SHIPPING leading/tab/CRLF span dispatch failed")
    engine.send(b" \t\r\n\n\t\n")
    require(engine.ready() == ["readyok"], "whitespace-only command emitted output")
    for boundary in (4095, 4096, 4097):
        data = b"x" * (boundary - 4) + b"\nisready\r\n"
        for chunk in (data[:boundary], data[boundary:boundary + 1], data[boundary + 1:]):
            engine.send(chunk)
        require(engine.until(lambda s: s == "readyok") == ["readyok"], "fragment boundary lost or duplicated command")
    engine.send(b"isr")
    require(engine.quiet() == [], "partial command dispatched before physical line boundary")
    engine.send(b"eady\r")
    require(engine.quiet() == [], "CR dispatched before LF")
    engine.send(b"\n")
    require(engine.until(lambda s: s == "readyok") == ["readyok"], "fragmented CRLF failed")
    engine.stable()
    return {"bad_lines_fully_drained": len(fixtures), "exact_limit_bytes": 32767,
            "fragment_boundaries": [4095, 4096, 4097],
            "leading_whitespace_dispatch_checked": not spec["dev"],
            "DEV_dispatch": "original full-line dispatcher; shared replay/go scanner only"}


def clocks(engine):
    invalid = ("9223372036854775808", "18446744073709551615", "18446744073709551616",
               "-1", "+1", "1x", "0x10", "--1", "", "btime 40 winc 0")
    forms = ["binc 900 winc 0 btime 60000 wtime 0", "wtime 0 btime 60000 winc 0 binc 900",
             "unknown 7 wtime 0 another-token btime 1", "wtimeX 99999 btimee 99999 wtime 0",
             "wtime 30 wtime 0", "wtime 0 winc 9223372036854775807", "winc infinite wtime 0"]
    # The last form deliberately recovers 'infinite' after a missing winc value;
    # test it with the active-control cases, not as an automatic clock expiry.
    recovered_infinite = forms.pop()
    forms.extend("wtime " + value for value in invalid)
    records = []
    for fields in forms:
        engine.ready(b"position startpos\n")
        engine.send(("go " + fields + "\n").encode())
        best = engine.best(Board.from_fen(), timeout=engine.timeout)
        require(not any(s.startswith("bestmove ") for s in engine.ready()), "duplicate result after clock epoch")
        records.append({"fields": fields, "automatic_result": best})
    # A black root ensures that irrelevant-side zero is not the selected clock.
    black = Board.from_fen().play("e2e4")
    for fields in ("wtime 60000 binc 0 btime 0 winc 900", "binc 0 winc 900 btime 0 wtime 60000"):
        engine.ready(b"position startpos moves e2e4\n")
        engine.send(("go " + fields + "\n").encode())
        records.append({"fields": fields, "root": "black", "automatic_result": engine.best(black)})
        require(engine.ready() == ["readyok"], "extra result after black-root clock epoch")
    return records, recovered_infinite


def controls(engine, recovered_infinite):
    records = []
    for fields in ("infinite wtime 0", "wtime 0 infinite", recovered_infinite,
                   "unknown infinite wtime 0", "", "only-unknown 27",
                   "wtime 9223372036854775807 winc 9223372036854775807"):
        engine.ready(b"position startpos\n")
        engine.send(("go " + fields + "\nisready\n").encode())
        require(engine.until(lambda s: s == "readyok") == ["readyok"], "epoch unexpectedly completed before ready")
        pre = engine.active_observation()
        # These exactness checks occur during an epoch with observed worker CPU
        # progress when the scheduler exposes a tick; absence is recorded unknown.
        require(engine.ready(b"stopwatch\nstop extra\nquitx\nquit extra\n") == ["readyok"],
                "invalid control command completed an infinite epoch")
        after = engine.active_observation()
        engine.send(b"stop\n")
        result = engine.best(Board.from_fen())
        require(engine.ready(b"stop\n") == ["readyok"], "idle stop duplicated a result")
        records.append({"fields": fields, "before_invalid_controls": pre,
                        "after_invalid_controls": after, "result_after_stop": result,
                        "claim": "pre-active worker CPU observation and bounded result; stop causality remains unproven"})
    return records


def replay(engine):
    valid = [
        ("ordinary", "e2e4 e7e5 g1f3 b8c6"),
        ("ep", "e2e4 a7a6 e4e5 d7d5 e5d6"),
        ("castle", "e2e4 e7e5 g1f3 b8c6 f1e2 g8f6 e1g1"),
    ]
    promotion = "a2a4 h7h5 a4a5 h5h4 a5a6 h4h3 a6b7 h3g2 b7a8"
    valid.extend(("promotion-" + suffix, promotion + suffix) for suffix in "nbrq")
    valid.extend((("empty-moves", ""),))
    records = []
    for label, moves in valid:
        board = Board.from_fen()
        for move in moves.split():
            board = board.play(move)
        # DEV top-level syntax is intentionally old; span helpers after it are new.
        engine.send(("position startpos moves " + moves + "\n").encode())
        actual = engine.state()
        engine.legal(board)
        require(actual["halfmove"] == board.halfmove, "replay halfmove differs from oracle")
        engine.send(("position fen " + board.fen() + "\n").encode())
        reconstructed = engine.state()
        require({k: v for k, v in actual.items() if k != "draw"} ==
                {k: v for k, v in reconstructed.items() if k != "draw"},
                "replay and independent oracle FEN reconstruction differ")
        records.append({"case": label, "plies": len(moves.split()), "oracle_fen": board.fen(),
                        "state": actual})
    cycle = "g1f3 g8f6 f3g1 f6g8"
    held_moves = cycle + " " + cycle
    held = Board.from_fen()
    for move in held_moves.split():
        held = held.play(move)
    engine.send(("position startpos moves " + held_moves + "\n").encode())
    baseline, baseline_legal = engine.state(), engine.legal(held)
    require(baseline["draw"] is True, "repeated baseline did not retain accepted game history")
    invalid = ["position startposition", "position startpos junk", "position startpos moves moves",
               "position startpos moves e2e4 e7e5 e1e3", "position startpos moves e2e5",
               "position startpos moves e7e5", "position startpos moves e1g1",
               "position startpos moves e2e4 trailing", "position startpos moves e2e4q",
               "position startpos moves e2e4 e7e5 g1f3 b8c6 f1e2 g8f6 e1g1q",
               "position startpos moves e2e4 a7a6 e4e5 d7d5 e5d6q"]
    invalid.extend("position startpos moves " + promotion + suffix for suffix in ("", "p", "k", "Q", "qq"))
    invalid.extend("position startpos moves " + token for token in ("e2", "e2e4qq", "i2e4", "e0e4", "e2i4", "e2e9"))
    for command in invalid:
        engine.send(command.encode() + b"\n")
        require(engine.state() == baseline, "invalid suffix changed accepted DEV state: " + command)
        require(engine.legal(held) == baseline_legal, "invalid suffix changed legal board")
    # Non-start FEN root is also retained by a bad command that already replayed
    # several start-position plies into its private candidate board.
    other = Board.from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 17 31")
    engine.send(("position fen " + other.fen() + "\n").encode())
    other_state = engine.state()
    engine.send(b"position startpos moves e2e4 e7e5 g1f3 b8c6 illegal\n")
    require(engine.state() == other_state, "invalid replay replaced non-start root")
    engine.legal(other)
    # 4095 accepted plies + initial key fit HISTORY=4096; next ply must reject
    # the entire command. The fixture stays below the 32767-byte line capacity.
    moves = (cycle.split() * 1024)[:4095]
    boundary_board = Board.from_fen()
    for move in moves:
        boundary_board = boundary_board.play(move)
    engine.send(("position startpos moves " + " ".join(moves) + "\n").encode())
    accepted = engine.state()
    require(accepted["halfmove"] == 4095, "4095-ply HISTORY boundary not accepted")
    engine.legal(boundary_board)
    engine.send(("position startpos moves " + " ".join(cycle.split() * 1024) + "\n").encode())
    require(engine.state() == accepted, "HISTORY overflow did not transactionally preserve accepted root/history")
    engine.legal(boundary_board)
    return {"accepted_replays": records, "invalid_replays_preserved_state": len(invalid),
            "repetition_history_observed": True, "non_start_root_rollback": True,
            "history_boundary_accepted_plies": 4095, "history_overflow_rejected_plies": 4096,
            "scope": "DEV observable state/legal/draw; full game-key prefix belongs to parent's direct production harness"}


def eof_cases(spec, output, timeout):
    records = []
    cases = (("ready", b"isready", "readyok"), ("uci", b"uci", "uciok"),
             ("nul", b"isready\0quit", None),
             ("oversized", b"isready" + b" " * 32761, None),
             ("search", b"go wtime 0 btime 0", "bestmove"))
    for label, raw, expected in cases:
        engine = RawEngine(spec, output, spec["id"] + "-eof-" + label, timeout)
        try:
            engine.initialize()
            initial = len([item for item in engine.events if item["direction"] == "stdout"])
            engine.send(raw)
            all_lines = engine.finish(None)
            lines = all_lines[initial:]
            if expected == "bestmove":
                publications = [s for s in lines if s.startswith("bestmove ")]
                require(len(publications) == 1, "EOF final search did not publish exactly once")
                require(publications[0].split()[1] in {str(m) for m in Board.from_fen().legal_moves()},
                        "EOF final search bestmove illegal")
            elif expected is None:
                require(lines == [], "bad final line dispatched a valid-looking prefix")
            else:
                require(lines.count(expected) == 1, "valid final no-LF command lost or duplicated")
                require(not any(s.startswith("bestmove ") for s in lines), "EOF command unexpectedly searched")
            records.append({"case": label, "bytes": len(raw), "stdout": lines,
                            "exit": 0, "runtime_process_absent": True, "readers_joined": True})
        finally:
            engine.cleanup()
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--skip-eof", action="store_true")
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("actual Linux candidates and /proc thread observation are required")
    absolute_output = args.out.is_absolute()
    args.out = args.out.resolve()
    if not absolute_output or args.out.exists() or args.out.is_relative_to(ROOT.resolve()):
        parser.error("--out must be a new absolute directory outside the checkout")
    if not 1 <= args.timeout <= 60:
        parser.error("timeout must be in 1..60 seconds")
    manifest = json.loads(args.manifest.read_text())
    specs = manifest["engines"]
    require(isinstance(specs, list) and 0 < len(specs) <= 16, "expected bounded engines list")
    ids = set()
    for spec in specs:
        require(isinstance(spec.get("id"), str) and spec["id"] and
                all(c.isalnum() or c in "_-" for c in spec["id"]), "unsafe engine id")
        require(spec["id"] not in ids, "duplicate engine id")
        ids.add(spec["id"])
        if "dev" not in spec:
            require(spec.get("profile") in ("dev", "shipping"), "explicit dev or recognized profile required")
            spec["dev"] = spec["profile"] == "dev"
        require(type(spec.get("dev")) is bool, "boolean dev required")
        require(type(spec.get("workers")) is int and 1 <= spec["workers"] <= 16, "bounded worker count required")
        require(isinstance(spec.get("command"), list) and spec["command"] and
                all(isinstance(x, str) for x in spec["command"]), "command must be argv list")
        require(isinstance(spec.get("profile"), str), "profile required")
        if "startup_timeout" in spec:
            require(1 <= spec["startup_timeout"] <= 60, "startup timeout must be in 1..60 seconds")
    args.out.mkdir(parents=True)
    report = {"manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
              "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "oracle_sha256": hashlib.sha256((ROOT / "engines/tests/chess_oracle.py").read_bytes()).hexdigest(),
              "scope": "actual raw-input protocol candidates; bounded functionality, no timing/NPS/strength comparison",
              "engines": [], "passed": True}
    for spec in specs:
        result = {"id": spec["id"], "profile": spec["profile"], "dev": spec["dev"],
                  "command": spec["command"], "workers": spec["workers"], "passed": False}
        engine = None
        try:
            engine = RawEngine(spec, args.out, spec["id"] + "-edges", args.timeout)
            engine.initialize()
            result["framing"] = framing(engine, spec)
            result["clocks"], recovery = clocks(engine)
            result["controls"] = controls(engine, recovery)
            if spec["dev"]:
                result["replay"] = replay(engine)
            engine.finish()
            result["fixed_startup_tids"] = sorted(engine.startup_tids)
            result["runtime_process_absent_after_quit"] = True
            engine.cleanup()
            engine = None
            if not args.skip_eof:
                result["eof"] = eof_cases(spec, args.out, args.timeout)
            result["passed"] = True
        except Exception:
            result["failure"] = traceback.format_exc()
            report["passed"] = False
        finally:
            if engine is not None:
                engine.cleanup()
        report["engines"].append(result)
        save(args.out / "results.json", report)
        print(json.dumps({"id": spec["id"], "passed": result["passed"],
                          "failure": result.get("failure")}), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
