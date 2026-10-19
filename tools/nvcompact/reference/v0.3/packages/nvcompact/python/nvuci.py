#!/usr/bin/env python3
"""Bounded, independent UCI protocol/legality probes for complete artifacts.

The TCEC 4k required subset is deliberately distinct from the larger UCI probe.
chess is a development-only oracle: never bundled into an engine by this tool.
No network install, automatic engine repair, or wall-clock move equality occurs.
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import asdict, dataclass
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any


FORMAT = "nvcompact.uci.v1"
UCI_SOURCE = "https://backscattering.de/chess/uci/"
TCEC_SOURCE = "https://wiki.chessdom.org/index.php?title=TCEC_4k_Rules&oldid=7853"
MOVE = re.compile(r"(?:[a-h][1-8]){2}[qrbn]?\Z")
OPTION = re.compile(r"option\s+name\s+(.+?)\s+type\s+(check|spin|combo|button|string)(?:\s+(.*))?\Z")


@dataclass
class Config:
    profile: str = "tcec4k"
    extensions: bool = False
    quick: bool = False
    oracle_path: str | None = None
    artifact_path: str | None = None
    startup_seconds: float = 60.0
    ready_seconds: float = 5.0
    search_seconds: float = 5.0
    stop_seconds: float = 2.0
    quit_seconds: float = 2.0
    cleanup_seconds: float = 5.0
    max_seconds: float = 180.0
    clock_ms: int = 2000
    clock_grace_ms: int = 1000
    movetime_ms: int = 100
    depth: int = 3
    nodes: int = 1000
    threads: int = 1
    hash_mb: int = 16
    preserve_engine_options: bool = False
    max_output_bytes: int = 2 << 20
    max_line_bytes: int = 65536
    max_transcript_bytes: int = 256 << 10

    def validate(self) -> None:
        if self.profile not in ("tcec4k", "uci"):
            raise ValueError("profile must be tcec4k or uci")
        for key in ("startup_seconds", "ready_seconds", "search_seconds",
                    "stop_seconds", "quit_seconds", "cleanup_seconds", "max_seconds"):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(key + " must be positive and finite")
        if self.startup_seconds > 60:
            raise ValueError("startup_seconds must not exceed the TCEC 60-second ceiling")
        if self.cleanup_seconds > 60:
            raise ValueError("cleanup_seconds must not exceed 60 seconds")
        for key in ("clock_ms", "movetime_ms", "depth", "nodes", "threads", "hash_mb",
                    "max_output_bytes", "max_line_bytes", "max_transcript_bytes"):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(key + " must be a positive integer")
        if isinstance(self.clock_grace_ms, bool) or not isinstance(self.clock_grace_ms, int) or self.clock_grace_ms < 0:
            raise ValueError("clock_grace_ms must be a nonnegative integer")
        if any(type(value) is not bool for value in (self.extensions, self.quick, self.preserve_engine_options)):
            raise ValueError("extensions, quick and preserve_engine_options must be booleans")


class ProbeError(Exception):
    def __init__(self, message: str, kind: str = "protocol"):
        super().__init__(message)
        self.kind = kind


def _oracle(path: str | None):
    if path:
        root = str(Path(path).resolve(strict=True))
        if root not in sys.path:
            sys.path.insert(0, root)
    try:
        chess = importlib.import_module("chess")
    except ImportError:
        raise ValueError("independent legality oracle missing: install chess==1.11.2 in the verifier environment, or pass --oracle-path") from None
    if not hasattr(chess, "Board") or not hasattr(chess, "Move"):
        raise ValueError("imported chess module does not provide the rules oracle")
    return chess


def _proc_group_members(pgid: int) -> list[dict]:
    """Linux process-group observation only; escaped new sessions are out of scope."""
    try:
        # Containers may expose a procfs from a different PID namespace. Never
        # attribute an unrelated visible process to our child by numeric ID.
        if int(Path("/proc/self/stat").read_text().split()[0]) != os.getpid():
            return []
    except (OSError, ValueError):
        return []
    result = []
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            text = path.read_text()
            tail = text[text.rfind(")") + 2:].split()
            if int(tail[2]) == pgid:
                result.append({"pid": int(path.parent.name), "state": tail[0]})
        except (OSError, ValueError, IndexError):
            continue
    return sorted(result, key=lambda item: item["pid"])


def _group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


class Session:
    def __init__(self, command: list[str], config: Config, deadline: float, cwd: Path):
        self.config, self.deadline = config, deadline
        self.started = time.monotonic()
        temporary = cwd / "tmp"
        temporary.mkdir()
        environment = dict(os.environ, TMPDIR=str(temporary))
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, cwd=cwd, start_new_session=True,
                                        bufsize=0, close_fds=True, env=environment)
        self.selector = selectors.DefaultSelector()
        for stream, name in ((self.process.stdout, "stdout"), (self.process.stderr, "stderr")):
            os.set_blocking(stream.fileno(), False)
            self.selector.register(stream, selectors.EVENT_READ, name)
        os.set_blocking(self.process.stdin.fileno(), False)
        self.buffer = bytearray()
        self.lines = deque()
        self.transcript: list[dict] = []
        self.transcript_bytes = 0
        self.transcript_omitted = 0
        self.output_bytes = {"stdout": 0, "stderr": 0}
        self.stderr_tail = bytearray()
        self.finished = False
        self.cleanup: dict[str, Any] = {}

    def record(self, direction: str, text: str) -> None:
        size = len(text.encode("utf-8", errors="replace"))
        if self.transcript_bytes + size <= self.config.max_transcript_bytes:
            self.transcript.append({"at_ms": round((time.monotonic() - self.started) * 1000, 3),
                                    "direction": direction, "text": text})
            self.transcript_bytes += size
        else:
            self.transcript_omitted += 1

    def bound(self, seconds: float) -> float:
        if time.monotonic() >= self.deadline:
            raise ProbeError("total verifier budget exhausted", "budget")
        return min(self.deadline, time.monotonic() + seconds)

    def send(self, text: str) -> None:
        if "\n" in text or "\r" in text:
            raise ValueError("command must contain one line")
        data = (text + "\n").encode("ascii")
        deadline = self.bound(self.config.ready_seconds)
        self.record("send", text)
        while data:
            if self.process.poll() is not None:
                raise ProbeError("engine exited before command: " + text, "exit")
            try:
                count = os.write(self.process.stdin.fileno(), data)
                data = data[count:]
            except BlockingIOError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ProbeError("engine stopped reading commands", "timeout")
                with selectors.DefaultSelector() as selector:
                    selector.register(self.process.stdin, selectors.EVENT_WRITE)
                    selector.select(remaining)
            except BrokenPipeError:
                raise ProbeError("engine closed stdin", "exit") from None

    def _pump(self, deadline: float) -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            kind = "budget" if time.monotonic() >= self.deadline else "timeout"
            raise ProbeError("response deadline exceeded", kind)
        if not self.selector.get_map():
            if self.buffer:
                raise ProbeError("stdout ended with an unterminated protocol line")
            raise ProbeError("engine stdout/stderr closed (exit %s)" % self.process.poll(), "exit")
        # A cleanup helper may inherit both pipes after the actual engine dies.
        # Do not wait for that helper's EOF and misclassify the crash as timeout.
        events = self.selector.select(min(remaining, .05))
        if not events:
            if self.process.poll() is not None:
                raise ProbeError("engine leader exited while awaiting response (exit %s)" % self.process.returncode, "exit")
            if time.monotonic() >= deadline:
                kind = "budget" if time.monotonic() >= self.deadline else "timeout"
                raise ProbeError("response deadline exceeded", kind)
            return
        for key, _ in events:
            try:
                data = os.read(key.fileobj.fileno(), 65536)
            except BlockingIOError:
                continue
            if not data:
                self.selector.unregister(key.fileobj)
                continue
            name = key.data
            self.output_bytes[name] += len(data)
            if sum(self.output_bytes.values()) > self.config.max_output_bytes:
                raise ProbeError("combined stdout/stderr exceeds output limit", "output_limit")
            if name == "stderr":
                self.stderr_tail.extend(data)
                del self.stderr_tail[:-16384]
                continue
            self.buffer.extend(data)
            while b"\n" in self.buffer:
                line, _, remainder = self.buffer.partition(b"\n")
                self.buffer = bytearray(remainder)
                if len(line) > self.config.max_line_bytes:
                    raise ProbeError("stdout line exceeds line limit", "output_limit")
                try:
                    text = line.rstrip(b"\r").decode("utf-8")
                except UnicodeDecodeError:
                    raise ProbeError("stdout protocol line is not UTF-8 text") from None
                self.lines.append(text.strip())
            if len(self.buffer) > self.config.max_line_bytes:
                raise ProbeError("unterminated stdout line exceeds line limit", "output_limit")

    def next_line(self, deadline: float) -> str:
        if time.monotonic() >= deadline:
            raise ProbeError("response deadline exceeded", "budget" if time.monotonic() >= self.deadline else "timeout")
        while not self.lines:
            self._pump(deadline)
        line = self.lines.popleft()
        self.record("receive", line)
        return line

    def wait_token(self, token: str, seconds: float, *, absolute: float | None = None) -> list[str]:
        deadline = absolute if absolute is not None else self.bound(seconds)
        seen = []
        while True:
            line = self.next_line(deadline)
            seen.append(line)
            if line == token:
                return seen
            if line.startswith("bestmove"):
                raise ProbeError("unsolicited or duplicate bestmove while waiting for " + token)
            if line.startswith(token + " "):
                raise ProbeError("malformed acknowledgement: " + line)

    def ready(self, seconds: float | None = None) -> list[str]:
        self.send("isready")
        return self.wait_token("readyok", seconds or self.config.ready_seconds)

    def wait_bestmove(self, board, chess, seconds: float) -> dict:
        deadline = self.bound(seconds)
        info = {}
        while True:
            line = self.next_line(deadline)
            if line.startswith("bestmove"):
                answer = validate_bestmove(line, board, chess)
                answer["final_info"] = info
                return answer
            if line.startswith("info ") and not line.startswith("info string "):
                info = _info(line)

    def quit(self) -> dict:
        self.send("quit")
        deadline = self.bound(self.config.quit_seconds)
        # Drain both streams while waiting: a final large info/stderr write must
        # not deadlock a process that is otherwise trying to exit.
        while self.process.poll() is None:
            try:
                self._pump(min(deadline, time.monotonic() + .05))
            except ProbeError as exc:
                if exc.kind not in ("timeout", "exit"):
                    raise
            if time.monotonic() >= deadline and self.process.poll() is None:
                raise ProbeError("engine did not exit after quit", "timeout")
        code = self.process.wait()
        cleanup_started = time.monotonic()
        immediate_group = _group_exists(self.process.pid)
        cleanup_deadline = self.bound(self.config.cleanup_seconds)
        while _group_exists(self.process.pid) and time.monotonic() < cleanup_deadline:
            if self.selector.get_map():
                try:
                    self._pump(min(cleanup_deadline, time.monotonic() + .05))
                except ProbeError as exc:
                    if exc.kind not in ("timeout", "exit"):
                        raise
            else:
                time.sleep(min(.01, max(0, cleanup_deadline - time.monotonic())))
        members = [item for item in _proc_group_members(self.process.pid)
                   if item["pid"] != self.process.pid and item["state"] != "Z"]
        group_exists = _group_exists(self.process.pid)
        self.cleanup = {"quit_returncode": code, "live_group_members_after_quit": members,
                        "process_group_exists_immediately_after_quit": immediate_group,
                        "process_group_exists_after_quit": group_exists,
                        "cleanup_wait_ms": round((time.monotonic() - cleanup_started) * 1000, 3),
                        "cleanup_grace_seconds": self.config.cleanup_seconds,
                        "scope": "original Linux process group; detached sessions not observed"}
        if group_exists:
            raise ProbeError("engine process group remains after quit, leader reap, and finite cleanup grace", "cleanup")
        if code != 0:
            raise ProbeError("quit returned nonzero exit status %s" % code, "exit")
        self.finished = True
        return self.cleanup

    def close(self) -> dict:
        before = _proc_group_members(self.process.pid)
        forced = _group_exists(self.process.pid)
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.cleanup["leader_reap_timeout"] = True
        self.selector.close()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()
        self.cleanup.update({"forced_cleanup": forced, "group_members_before_cleanup": before,
                             "returncode": self.process.returncode})
        return self.cleanup


def _info(line: str) -> dict:
    parts, result = line.split(), {}
    for key in ("depth", "seldepth", "nodes", "time"):
        try:
            index = parts.index(key)
            result[key] = int(parts[index + 1])
        except (ValueError, IndexError):
            pass
    try:
        index = parts.index("score")
        kind, number = parts[index + 1:index + 3]
        if kind in ("cp", "mate"):
            result["score"] = {"kind": kind, "value": int(number)}
    except (ValueError, IndexError):
        pass
    if "pv" in parts:
        result["pv"] = parts[parts.index("pv") + 1:]
    return result


def validate_bestmove(line: str, board, chess) -> dict:
    words = line.split()
    if len(words) not in (2, 4) or words[0] != "bestmove" or (len(words) == 4 and words[2] != "ponder"):
        raise ProbeError("malformed bestmove: " + line)
    move = words[1]
    if move == "0000":
        if any(board.legal_moves):
            raise ProbeError("null bestmove returned in a position with legal moves")
        if len(words) == 4:
            raise ProbeError("ponder supplied after a null bestmove")
        return {"bestmove": move, "legal": True, "terminal": True}
    if not MOVE.fullmatch(move):
        raise ProbeError("bestmove must use UCI long algebraic notation or 0000: " + move)
    try:
        candidate = chess.Move.from_uci(move)
    except ValueError:
        raise ProbeError("invalid UCI move: " + move) from None
    if candidate not in board.legal_moves:
        raise ProbeError("illegal bestmove %s for %s" % (move, board.fen()))
    result = {"bestmove": move, "legal": True, "terminal": False}
    if len(words) == 4:
        ponder = words[3]
        after = board.copy(stack=False)
        after.push(candidate)
        try:
            reply = chess.Move.from_uci(ponder) if MOVE.fullmatch(ponder) else None
        except ValueError:
            reply = None
        if reply is None or reply not in after.legal_moves:
            raise ProbeError("illegal ponder move: " + ponder)
        result["ponder"] = ponder
    return result


def parse_option(line: str) -> dict:
    match = OPTION.fullmatch(line)
    if not match:
        raise ProbeError("malformed advertised option: " + line)
    name, kind, rest = match.groups()
    fields = re.split(r"(?:^|\s)(default|min|max|var)(?:\s|$)", rest or "")
    result: dict[str, Any] = {"name": name, "type": kind}
    if fields[0].strip():
        raise ProbeError("unrecognized option attribute: " + line)
    for index in range(1, len(fields), 2):
        key, value = fields[index], fields[index + 1].strip()
        if key == "var":
            result.setdefault("var", []).append(value)
        elif key in result:
            raise ProbeError("duplicate option attribute: " + line)
        else:
            result[key] = value
    if kind == "spin":
        try:
            low, default, high = (int(result[key]) for key in ("min", "default", "max"))
        except (ValueError, KeyError):
            raise ProbeError("spin option needs integer min/default/max: " + line) from None
        if not low <= default <= high:
            raise ProbeError("spin option default outside range: " + line)
        result.update(min=low, default=default, max=high)
    elif kind == "check" and result.get("default") not in ("true", "false"):
        raise ProbeError("check option requires true/false default: " + line)
    elif kind == "combo" and result.get("default") not in result.get("var", []):
        raise ProbeError("combo default is not an advertised var: " + line)
    return result


def _configure(session: Session, options: list[dict], config: Config) -> list[dict]:
    if config.preserve_engine_options:
        return [{"name": item["name"], "status": "preserved", "advertised_default": item.get("default")}
                for item in options]
    changes = []
    for option in options:
        name, kind = option["name"], option["type"]
        key = name.casefold()
        value: str | int | None = None
        if key in ("hash", "threads", "multipv") and kind == "spin":
            requested = {"hash": config.hash_mb, "threads": config.threads, "multipv": 1}[key]
            if option["min"] > requested:
                changes.append({"name": name, "status": "not_set", "reason": "advertised minimum exceeds configured resource budget"})
                continue
            value = min(option["max"], max(option["min"], requested))
        elif key in ("ponder", "ownbook") and kind == "check":
            value = "false"
        if value is not None:
            session.send("setoption name %s value %s" % (name, value))
            changes.append({"name": name, "value": value, "status": "sent"})
    return changes


START_CASES = [
    ("startpos_white", ""),
    ("startpos_black", "e2e4"),
    ("castling_history", "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 e1g1"),
    ("en_passant_history", "e2e4 a7a6 e4e5 d7d5 e5d6"),
    ("middlegame_history", "e2e4 e7e5 g1f3 b8c6 f1c4 g8f6 d2d3 f8c5 c1g5 d7d6 b1c3 e8g8"),
    ("promotion_history", "a2a4 h7h5 a4a5 h5h4 a5a6 h4h3 a6b7 h3g2 b7a8q g2h1q"),
]


def _board_start(chess, moves: str):
    board = chess.Board()
    for word in moves.split():
        board.push_uci(word)
    return board


def _check(session: Session, report: dict, label: str, requirement: str, operation):
    started = time.monotonic()
    item = {"id": label, "requirement": requirement}
    try:
        detail = operation()
        item.update(status="pass", detail=detail)
        return detail
    except ProbeError as exc:
        item.update(status="incomplete" if exc.kind == "budget" else "fail",
                    kind=exc.kind, error=str(exc))
        raise
    finally:
        item["elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)
        report["cases"].append(item)


def _search(session: Session, chess, board, position: str, go: str,
            mode: str, budget: int, seconds: float) -> dict:
    session.send(position)
    session.ready()
    started = time.monotonic()
    session.send(go)
    result = session.wait_bestmove(board, chess, seconds)
    result.update(position=position, fen=board.fen(), go=go, mode=mode, budget=budget,
                  search_elapsed_ms=round((time.monotonic() - started) * 1000, 3))
    # One bestmove per go: use the following readyok as the synchronization
    # boundary and reject a duplicate bestmove before that acknowledgement.
    session.ready()
    return result


def _handshake(session: Session, report: dict, config: Config, requirement: str) -> dict:
    startup_deadline = min(session.deadline, session.started + config.startup_seconds)
    session.send("uci")
    lines = session.wait_token("uciok", config.startup_seconds, absolute=startup_deadline)
    identity, options, option_errors = {}, [], []
    for line in lines:
        for field in ("name", "author"):
            prefix = "id " + field + " "
            if line.startswith(prefix):
                identity[field] = line[len(prefix):]
        if line.startswith("option"):
            try:
                option = parse_option(line)
                if any(old["name"].casefold() == option["name"].casefold() for old in options):
                    raise ProbeError("duplicate advertised option: " + option["name"])
                options.append(option)
            except ProbeError as exc:
                option_errors.append(str(exc))
    changes = _configure(session, options, config)
    session.send("isready")
    session.wait_token("readyok", config.startup_seconds, absolute=startup_deadline)
    detail = {"identity": identity, "options": options, "option_errors": option_errors,
              "configured_options": changes,
              "ready_after_launch_ms": round((time.monotonic() - session.started) * 1000, 3)}
    report.setdefault("handshakes", []).append(detail)
    if requirement == "uci" and (not identity.get("name") or not identity.get("author") or option_errors):
        raise ProbeError("UCI identification/options incomplete: " + json.dumps({"identity": identity, "option_errors": option_errors}))
    return detail


def _core(session: Session, report: dict, config: Config, chess) -> None:
    _check(session, report, "handshake", "tcec4k", lambda: _handshake(session, report, config, "tcec4k"))
    for label, command in (("newgame_tolerance", "ucinewgame"),
                           ("idle_stop_tolerance", "stop"),
                           ("unknown_command_tolerance", "nvcompact_unknown_command")):
        def tolerance(command=command):
            session.send(command)
            session.ready()
            return {"command": command, "ready": True}
        _check(session, report, label, "tcec4k", tolerance)
    corpus = START_CASES[:3] if config.quick else START_CASES
    for label, moves in corpus:
        board = _board_start(chess, moves)
        position = "position startpos" + (" moves " + moves if moves else "")
        go = "go wtime %d btime %d winc 0 binc 0" % (config.clock_ms, config.clock_ms)
        result = _check(session, report, label, "tcec4k",
                        lambda b=board, p=position: _search(session, chess, b, p, go, "clock", config.clock_ms,
                                                           min(config.search_seconds, (config.clock_ms + config.clock_grace_ms) / 1000)))
        report["observations"].append({"case": label, **result})
    _check(session, report, "quit_idle", "tcec4k", session.quit)


def _extensions(session: Session, report: dict, config: Config, chess) -> None:
    handshake = _check(session, report, "extension_handshake", "uci", lambda: _handshake(session, report, config, "tcec4k"))
    def identification():
        identity = handshake["identity"]
        if not identity.get("name") or not identity.get("author") or handshake["option_errors"]:
            raise ProbeError("UCI identification/options incomplete: " + json.dumps({"identity": identity, "option_errors": handshake["option_errors"]}))
        return {"identity": identity, "options_well_formed": True}
    try:
        _check(session, report, "uci_identification", "uci", identification)
    except ProbeError:
        # Missing optional id in a 4k engine does not corrupt session state.
        # Keep that full-UCI failure and still investigate its search controls.
        pass
    for label, fen, moves in (
        ("fen_startpos", chess.STARTING_FEN, "e2e4 e7e5"),
        ("fen_promotion", "8/P7/8/8/8/6k1/8/4K3 w - - 0 1", ""),
        ("fen_castling", "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", ""),
        ("fen_en_passant", "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", ""),
        ("fen_checkmate", "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", ""),
        ("fen_stalemate", "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", ""),
    ):
        board = chess.Board(fen)
        for move in moves.split():
            board.push_uci(move)
        position = "position fen " + fen + (" moves " + moves if moves else "")
        result = _check(session, report, label, "uci", lambda b=board, p=position:
                        _search(session, chess, b, p, "go depth %d" % config.depth, "depth", config.depth, config.search_seconds))
        report["observations"].append({"case": label, **result})
    for mode, budget in (("depth", config.depth), ("nodes", config.nodes), ("movetime", config.movetime_ms)):
        result = _check(session, report, "go_" + mode, "uci", lambda m=mode, b=budget:
                        _search(session, chess, chess.Board(), "position startpos", "go %s %d" % (m, b), m, b, config.search_seconds))
        report["observations"].append({"case": "go_" + mode, **result})
    def asynchronous():
        session.send("position startpos")
        session.ready()
        session.send("go infinite")
        session.ready(config.stop_seconds)
        started = time.monotonic()
        session.send("stop")
        result = session.wait_bestmove(chess.Board(), chess, config.stop_seconds)
        result["stop_to_bestmove_ms"] = round((time.monotonic() - started) * 1000, 3)
        session.ready()
        return result
    _check(session, report, "ready_and_stop_during_infinite", "uci", asynchronous)
    def quit_search():
        session.send("position startpos")
        session.ready()
        session.send("go infinite")
        return session.quit()
    _check(session, report, "quit_during_search", "uci", quit_search)


def _aggregate(cases: list[dict]) -> str:
    if any(item["status"] == "fail" for item in cases):
        return "fail"
    if any(item["status"] == "incomplete" for item in cases):
        return "incomplete"
    return "pass" if cases else "not_run"


def verify_engine(command: list[str], config: Config | dict | None = None) -> dict:
    """Run the actual artifact command; return JSON-compatible finite evidence.

    tcec4k verdict never becomes a pass merely because a baseline also failed.
    --extensions findings do not enlarge the published TCEC required subset.
    """
    config = Config(**config) if isinstance(config, dict) else config or Config()
    config.validate()
    if not isinstance(command, list) or not command or not all(isinstance(item, str) and item and "\x00" not in item for item in command):
        raise ValueError("command must be a nonempty argv list")
    if not Path(command[0]).is_absolute():
        raise ValueError("command executable must be an absolute path; no implicit shell/PATH search")
    chess = _oracle(config.oracle_path)
    started = time.monotonic()
    deadline = started + config.max_seconds
    report: dict[str, Any] = {
        "format": FORMAT, "command": command, "profile": config.profile,
        "configuration": asdict(config), "sources": [TCEC_SOURCE, UCI_SOURCE],
        "oracle": {"module": "chess", "version": getattr(chess, "__version__", "unknown"),
                   "source": str(Path(chess.__file__).resolve()),
                   "module_sha256": hashlib.sha256(Path(chess.__file__).read_bytes()).hexdigest(),
                   "development_only": True},
        "cases": [], "observations": [], "sessions": [],
        "scope": {"rules": "standard chess", "evidence": "finite legal move and protocol probes, not full semantic equivalence or tournament certification",
                  "tcec_subset": "required 4k subset; optional full-UCI commands reported separately",
                  "file_cleanup": "owned working directory and original process group only; no system-wide filesystem/exec audit",
                  "time_control": "short representative sudden-death clock probe; no 30min+3s match or many-core performance claim"}}
    artifact = Path(config.artifact_path).resolve(strict=True) if config.artifact_path else None
    before = None
    if artifact is not None:
        before = artifact.read_bytes()
        report["artifact"] = {"path": str(artifact), "bytes": len(before), "sha256": hashlib.sha256(before).hexdigest(),
                              "within_4096_bytes": len(before) <= 4096}
    with tempfile.TemporaryDirectory(prefix="nvcompact-uci-") as root:
        for phase in ("core", "extensions"):
            if phase == "extensions" and not (config.extensions or config.profile == "uci"):
                continue
            if phase == "extensions" and _aggregate([item for item in report["cases"] if item["requirement"] == "tcec4k"]) != "pass":
                report["extension_skip_reason"] = "required core did not pass; no false full-UCI verdict"
                break
            cwd = Path(root) / phase
            cwd.mkdir()
            session = None
            try:
                if time.monotonic() >= deadline:
                    raise ProbeError("total verifier budget exhausted before phase", "budget")
                session = Session(command, config, deadline, cwd)
                (_core if phase == "core" else _extensions)(session, report, config, chess)
            except ProbeError as exc:
                if session is None:
                    report["cases"].append({"id": phase + "_launch", "requirement": "tcec4k" if phase == "core" else "uci",
                                             "status": "incomplete" if exc.kind == "budget" else "fail", "kind": exc.kind, "error": str(exc)})
            except OSError as exc:
                report["cases"].append({"id": phase + "_launch", "requirement": "tcec4k" if phase == "core" else "uci",
                                         "status": "fail", "kind": "launch", "error": str(exc)})
            finally:
                if session is not None:
                    cleanup = session.close()
                    leftovers = sorted(str(path.relative_to(cwd)) for path in cwd.rglob("*")
                                       if path != cwd / "tmp")
                    report["sessions"].append({"phase": phase, "output_bytes": session.output_bytes,
                        "transcript": session.transcript, "omitted_transcript_lines": session.transcript_omitted,
                        "stderr_tail": session.stderr_tail.decode("utf-8", errors="replace"),
                        "cleanup": cleanup, "working_directory_leftovers": leftovers})
                    if leftovers:
                        interrupted = cleanup.get("forced_cleanup", False)
                        report["cases"].append({"id": phase + "_working_directory_cleanup", "requirement": "tcec4k" if phase == "core" else "uci",
                            "status": "incomplete" if interrupted else "fail",
                            "kind": "cleanup_observation" if interrupted else "cleanup",
                            "error": "leftover files observed after forced harness termination; engine cleanup may have been interrupted" if interrupted else "engine left files in its owned working directory",
                            "harness_interrupted_cleanup": interrupted, "files": leftovers})
    if artifact is not None and artifact.read_bytes() != before:
        report["cases"].append({"id": "artifact_unchanged", "requirement": "tcec4k", "status": "fail",
                                 "kind": "mutation", "error": "engine modified the artifact being checked"})
    core = _aggregate([item for item in report["cases"] if item["requirement"] == "tcec4k"])
    extended = _aggregate([item for item in report["cases"] if item["requirement"] == "uci"])
    report["required_tcec4k_verdict"] = core
    report["extended_uci_verdict"] = extended
    report["verdict"] = core if config.profile == "tcec4k" else ("fail" if "fail" in (core, extended) else "pass" if core == extended == "pass" else "incomplete")
    report["elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)
    return report


def compare_results(baseline: dict, candidate: dict, *, deterministic_mode: str = "none") -> dict:
    """Describe inherited defects/regressions; never relabel strict failures.

    Exact output checks need the caller's deterministic fixed-budget contract.
    They are sampled observations, not a proof for every input or scheduler.
    """
    if deterministic_mode not in ("none", "depth", "nodes"):
        raise ValueError("deterministic_mode must be none, depth, or nodes")
    base = {item["id"]: item for item in baseline.get("cases", [])}
    cand = {item["id"]: item for item in candidate.get("cases", [])}
    inherited, regressions, improvements, gaps = [], [], [], []
    for key in sorted(base.keys() | cand.keys()):
        a, b = base.get(key), cand.get(key)
        if a is None or b is None:
            gaps.append(key)
        elif a["status"] == "pass" and b["status"] != "pass":
            regressions.append(key)
        elif a["status"] != "pass" and b["status"] == "pass":
            improvements.append(key)
        elif a["status"] != "pass" and b["status"] != "pass":
            inherited.append({"case": key, "baseline": a["status"], "candidate": b["status"],
                              "same_failure_kind": a.get("kind") == b.get("kind")})
    exact = {"mode": deterministic_mode, "status": "not_requested", "matched": [], "mismatches": [], "missing": [],
             "observable": "bestmove and optional ponder; not full engine state or all info output"}
    if deterministic_mode != "none":
        control_differences = {}
        for field in ("threads", "hash_mb", deterministic_mode):
            a = baseline.get("configuration", {}).get(field)
            b = candidate.get("configuration", {}).get(field)
            if a != b:
                control_differences[field] = {"baseline": a, "candidate": b}
        a_options = [item.get("configured_options", []) for item in baseline.get("handshakes", [])]
        b_options = [item.get("configured_options", []) for item in candidate.get("handshakes", [])]
        if a_options != b_options:
            control_differences["configured_options"] = {"baseline": a_options, "candidate": b_options}
        exact["control_differences"] = control_differences
        a_items = {item["case"]: item for item in baseline.get("observations", []) if item["mode"] == deterministic_mode}
        b_items = {item["case"]: item for item in candidate.get("observations", []) if item["mode"] == deterministic_mode}
        for key in sorted(a_items.keys() | b_items.keys()):
            a, b = a_items.get(key), b_items.get(key)
            if a is None or b is None or (a["position"], a["budget"]) != (b["position"], b["budget"]):
                exact["missing"].append(key)
            elif (a["bestmove"], a.get("ponder")) != (b["bestmove"], b.get("ponder")):
                exact["mismatches"].append({"case": key, "baseline": a["bestmove"], "candidate": b["bestmove"]})
            else:
                exact["matched"].append(key)
        exact["status"] = "incomplete" if control_differences else "mismatch" if exact["mismatches"] else "incomplete" if exact["missing"] or not exact["matched"] else "observed_equal"
    comparison_verdict = {"not_requested": "not_requested", "observed_equal": "pass", "mismatch": "fail", "incomplete": "incomplete"}[exact["status"]]
    return {"baseline_strict_verdict": baseline.get("verdict"), "candidate_strict_verdict": candidate.get("verdict"),
            "regressions": regressions, "inherited_observed_failures": inherited, "improvements": improvements,
            "coverage_gaps": gaps, "exact_fixed_budget_observations": exact,
            "comparison_verdict": comparison_verdict,
            "scope": "sampled protocol and legal-move observations; inherited failure is not a pass; clock-mode bestmoves are never compared for exact equality"}


def acceptance_verdict(result: dict) -> str:
    """Combine explicitly requested comparison with, but do not rewrite, protocol."""
    protocol = result["verdict"]
    comparison = result.get("comparison", {}).get("comparison_verdict", "not_requested")
    if protocol == "error":
        return "error"
    if "fail" in (protocol, comparison):
        return "fail"
    if "incomplete" in (protocol, comparison):
        return "incomplete"
    return protocol


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--binary", type=Path)
    source.add_argument("--command", help="JSON argv array; first item must be an absolute executable")
    parser.add_argument("--artifact", type=Path, help="actual submission file when --command uses an interpreter")
    parser.add_argument("--profile", choices=("tcec4k", "uci"), default="tcec4k")
    parser.add_argument("--extensions", action="store_true")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--preserve-engine-options", action="store_true",
                        help="send no setoption commands; keep advertised defaults and embedded resource constants")
    parser.add_argument("--oracle-path")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--baseline-report", type=Path)
    parser.add_argument("--deterministic-mode", choices=("none", "depth", "nodes"), default="none")
    for flag in ("startup-seconds", "ready-seconds", "search-seconds", "stop-seconds", "quit-seconds", "cleanup-seconds", "max-seconds"):
        parser.add_argument("--" + flag, type=float, default=getattr(Config(), flag.replace("-", "_")))
    for flag in ("clock-ms", "clock-grace-ms", "movetime-ms", "depth", "nodes", "threads", "hash-mb", "max-output-bytes", "max-line-bytes", "max-transcript-bytes"):
        parser.add_argument("--" + flag, type=int, default=getattr(Config(), flag.replace("-", "_")))
    args = vars(parser.parse_args(argv))
    binary, command, artifact = args.pop("binary"), args.pop("command"), args.pop("artifact")
    output, baseline, deterministic = args.pop("report"), args.pop("baseline_report"), args.pop("deterministic_mode")
    try:
        if binary:
            binary = binary.resolve(strict=True)
            command = [str(binary)]
            artifact = artifact or binary
        else:
            command = json.loads(command)
        args["artifact_path"] = str(artifact.resolve(strict=True)) if artifact else None
        result = verify_engine(command, Config(**args))
        if baseline:
            result["comparison"] = compare_results(json.loads(baseline.read_text()), result, deterministic_mode=deterministic)
    except (OSError, ValueError, TypeError) as exc:
        result = {"format": FORMAT, "verdict": "error", "error": str(exc)}
    result["acceptance_verdict"] = acceptance_verdict(result)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text)
    print(text, end="")
    return {"pass": 0, "fail": 1, "incomplete": 2, "error": 2}.get(result["acceptance_verdict"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
