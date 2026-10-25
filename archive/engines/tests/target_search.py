#!/usr/bin/env python3
"""Opt-in bounded search/cancellation checks for fixed large Linux profiles.

This is separate from target_startup.py, which never searches. Four selected
native files run sequentially. These observations on an oversubscribed host
establish neither target-hardware scalability nor a performance ranking.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from chess_oracle import Board
from target_startup import (GIB, end_owned_group, process_state,
                            resource_admission, set_child_limits)


SELECTED = {"A-c": "stop", "F-c": "quit", "A-rust": "quit", "F-rust": "stop"}


def cpu_ticks(pid):
    def total(path):
        fields = path.read_text().rpartition(")")[2].split()
        return int(fields[11]) + int(fields[12])  # Original stat fields 14/15.
    process = total(Path(f"/proc/{pid}/stat"))
    stdin = total(Path(f"/proc/{pid}/task/{pid}/stat"))
    return {"process": process, "stdin": stdin, "search_workers": max(0, process - stdin)}


class Session:
    def __init__(self, path, expected, record, args):
        self.path, self.expected, self.record, self.args = path, expected, record, args
        self.process = None
        self.selector = None
        self.buffers = {"stdout": bytearray(), "stderr": bytearray()}
        self.ids = None
        self.phase = "startup"
        self.started = time.monotonic()
        self.deadline = self.started + args.timeout_seconds
        record.update({"commands": [], "observations": [], "output_chunks": [],
                       "phase_peak_rss_bytes": {}, "observed_peak_rss_bytes": 0,
                       "observed_peak_virtual_bytes": 0, "observed_peak_threads": 0})

    def start(self):
        self.process = subprocess.Popen([str(self.path)], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
                                        preexec_fn=lambda: set_child_limits(self.args.address_space_bytes,
                                                                            self.args.data_bytes,
                                                                            self.args.cpu_seconds))
        self.record["process_started"] = True
        self.record["pid"] = self.process.pid
        self.record["proc_start_time_ticks"] = int(Path(f"/proc/{self.process.pid}/stat").read_text().rpartition(")")[2].split()[19])
        self.selector = selectors.DefaultSelector()
        for stream, name in ((self.process.stdout, "stdout"), (self.process.stderr, "stderr")):
            os.set_blocking(stream.fileno(), False)
            self.selector.register(stream, selectors.EVENT_READ, name)

    def drain(self, duration=0.005):
        for key, _ in self.selector.select(duration):
            block = os.read(key.fileobj.fileno(), 65536)
            if not block:
                self.selector.unregister(key.fileobj)
                continue
            self.buffers[key.data].extend(block)
            self.record["output_chunks"].append({"t": time.monotonic() - self.started,
                                                   "stream": key.data,
                                                   "text": block.decode(errors="replace")})
            if len(self.buffers[key.data]) > 262144:
                raise RuntimeError("bounded search output exceeded 256 KiB")

    def poll(self, *, closing=False):
        if time.monotonic() >= self.deadline:
            raise RuntimeError("whole-process wall deadline exceeded")
        self.drain()
        if self.process.poll() is not None:
            if closing:
                return None
            raise RuntimeError(f"engine exited unexpectedly: {self.process.returncode}")
        state = process_state(self.process.pid)
        self.record["observed_peak_rss_bytes"] = max(self.record["observed_peak_rss_bytes"], state.get("VmHWM", 0), state.get("VmRSS", 0))
        self.record["observed_peak_virtual_bytes"] = max(self.record["observed_peak_virtual_bytes"], state.get("VmPeak", 0), state.get("VmSize", 0))
        self.record["observed_peak_threads"] = max(self.record["observed_peak_threads"], state.get("Threads", 0), len(state["task_ids"]))
        peaks = self.record["phase_peak_rss_bytes"]
        peaks[self.phase] = max(peaks.get(self.phase, 0), state.get("VmRSS", 0))
        if self.record["observed_peak_rss_bytes"] > self.args.max_rss_bytes:
            raise RuntimeError("resident-memory ceiling exceeded")
        if len(state["task_ids"]) > self.expected or state.get("Threads", 0) > self.expected:
            raise RuntimeError("fixed thread total exceeded")
        if self.ids is not None and not closing and state["task_ids"] != self.ids:
            raise RuntimeError("fixed startup TID set changed")
        return state

    def observe(self, label, state=None):
        state = state or self.poll()
        self.record["observations"].append({"phase": label,
                                            "elapsed_seconds": time.monotonic() - self.started,
                                            "cpu_ticks": cpu_ticks(self.process.pid), **state})

    def send(self, line):
        if self.process.poll() is not None:
            raise RuntimeError("engine exited before command")
        self.record["commands"].append({"t": time.monotonic() - self.started,
                                        "phase": self.phase, "line": line})
        self.process.stdin.write(line.encode() + b"\n")
        self.process.stdin.flush()

    def lines(self):
        return [line.rstrip(b"\r").decode(errors="replace")
                for line in bytes(self.buffers["stdout"]).split(b"\n")[:-1]]

    def bests(self):
        return [line for line in self.lines() if line.startswith("bestmove ")]

    def wait(self, condition, timeout):
        until = min(self.deadline, time.monotonic() + timeout)
        while time.monotonic() < until:
            self.poll()
            if condition():
                return
        raise RuntimeError("bounded protocol/search response deadline exceeded")

    def ready(self, count):
        self.send("isready")
        self.wait(lambda: self.lines().count("readyok") >= count, 3)
        if self.lines().count("readyok") != count:
            raise RuntimeError("duplicate ready acknowledgement")

    def quiet(self, expected_bests, seconds=0.04):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            self.poll()
            if len(self.bests()) != expected_bests:
                raise RuntimeError("stale or duplicate bestmove")

    def best(self, count, legal):
        self.wait(lambda: len(self.bests()) >= count, 3)
        if len(self.bests()) != count:
            raise RuntimeError("search emitted duplicate bestmove")
        parts = self.bests()[-1].split()
        if len(parts) != 2 or parts[1] not in legal:
            raise RuntimeError("bestmove is not legal for the independent oracle position")
        return parts[1]

    def initialize(self):
        stable = None
        since = None
        while True:
            state = self.poll()
            if (state.get("Threads") == self.expected and len(state["task_ids"]) == self.expected
                    and Path(f"/proc/{self.process.pid}/exe").resolve() == self.path.resolve()):
                if stable != state["task_ids"]:
                    stable, since = state["task_ids"], time.monotonic()
                if time.monotonic() - since >= 0.1:
                    self.ids = stable
                    break
            else:
                stable, since = None, None
        self.observe("before_first_input", state)
        self.send("uci")
        self.wait(lambda: self.lines().count("uciok") >= 1, 3)
        self.ready(1)
        self.observe("initialized")

    def shutdown(self):
        self.phase = "shutdown"
        until = min(self.deadline, time.monotonic() + 3)
        while self.process.poll() is None:
            if time.monotonic() >= until:
                raise RuntimeError("bounded physical shutdown deadline exceeded")
            self.poll(closing=True)
        self.record["returncode"] = self.process.returncode
        if self.process.returncode != 0:
            raise RuntimeError(f"nonzero engine shutdown: {self.process.returncode}")

    def finish(self):
        if self.process is None:
            if self.selector is not None:
                self.selector.close()
            return
        forced, gone = end_owned_group(self.process)
        self.record.update({"forced_group_cleanup": forced, "owned_process_group_gone": gone,
                            "physical_process_exit_confirmed": self.process.poll() is not None})
        if forced or not gone:
            self.record.update({"passed": False, "error": "normal owned-process-group termination failed"})
        if self.selector is not None:
            until = time.monotonic() + 1
            try:
                while self.selector.get_map() and time.monotonic() < until:
                    self.drain()
                if self.selector.get_map():
                    raise RuntimeError("pipes did not reach EOF")
            except Exception as error:
                self.record.update({"passed": False, "error": str(error)})
            self.selector.close()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream is not None:
                stream.close()
        self.record["stdout"] = bytes(self.buffers["stdout"]).decode(errors="replace")
        self.record["stderr"] = bytes(self.buffers["stderr"]).decode(errors="replace")
        self.record["wall_seconds"] = time.monotonic() - self.started


def check(path, expected, cancellation, args):
    admission = resource_admission(expected, args)
    record = {"passed": False, "admission": admission, "cancellation": cancellation,
              "expected_total_threads": expected, "process_started": False,
              "cpu_tick_hz": os.sysconf("SC_CLK_TCK")}
    if "rejection" in admission:
        record["error"] = admission["rejection"] + "; process not started"
        return record
    session = Session(path, expected, record, args)
    white = Board.from_fen()
    black = white.play("e2e4")
    legal_white = {str(m) for m in white.legal_moves()}
    legal_black = {str(m) for m in black.legal_moves()}
    record["oracle_legal_moves"] = {"short_search": sorted(legal_white), "cancel_search": sorted(legal_black)}
    try:
        session.start()
        session.initialize()
        session.send("position startpos")
        session.phase = "short-search"
        first = time.monotonic()
        session.send("go wtime 3000 btime 3000 winc 0 binc 0")
        move = session.best(1, legal_white)
        record["short_search"] = {"bestmove": move, "response_seconds": time.monotonic() - first}
        session.observe("after_short_search")
        session.phase = "idle"
        session.ready(2)
        session.quiet(1)
        session.send("position startpos moves e2e4")
        session.ready(3)
        session.quiet(1)
        session.observe("before_cancel_search")
        before = cpu_ticks(session.process.pid)
        session.phase = "cancel-search"
        second = time.monotonic()
        session.send("go wtime 300000 btime 300000 winc 0 binc 0")
        witnessed = None
        # Aim for 40ms. Hundreds of runnable workers may delay this observer;
        # keep a separate one-second fence instead of mistaking that for speed.
        while time.monotonic() - second < 1:
            session.poll()
            if len(session.bests()) != 1:
                raise RuntimeError("cancellation epoch completed before active-work observation")
            current = cpu_ticks(session.process.pid)
            delta = current["search_workers"] - before["search_workers"]
            elapsed = time.monotonic() - second
            if elapsed > 1:
                break
            if elapsed >= 0.04 and delta > 0:
                witnessed = {"before": before, "active": current, "worker_cpu_tick_delta": delta,
                             "observed_seconds": time.monotonic() - second,
                             "bestmove_count_before_cancel": len(session.bests())}
                break
        if witnessed is None:
            raise RuntimeError("active cancellation not witnessed within the short observation window")
        record["active_work_observation"] = witnessed
        session.observe("active_before_cancel")
        cancelled = time.monotonic()
        session.send(cancellation)
        if cancellation == "stop":
            move = session.best(2, legal_black)
            record["cancel_search"] = {"bestmove": move, "response_seconds": time.monotonic() - cancelled}
            session.observe("after_stop")
            session.phase = "idle"
            session.ready(4)
            session.quiet(2)
            session.send("quit")
        session.shutdown()
        record["cancellation_to_exit_seconds"] = time.monotonic() - cancelled
        record["passed"] = True
    except Exception as error:
        record["error"] = str(error)
    finally:
        session.finish()
    if record["passed"]:
        lines = session.lines()
        bests = session.bests()
        expected_ready = 4 if cancellation == "stop" else 3
        if session.buffers["stdout"] and not session.buffers["stdout"].endswith(b"\n"):
            record.update({"passed": False, "error": "unterminated stdout suffix at EOF"})
        elif lines.count("uciok") != 1 or lines.count("readyok") != expected_ready or len(bests) != 2:
            record.update({"passed": False, "error": "final acknowledgement or bestmove count mismatch"})
        else:
            for index, legal in enumerate((legal_white, legal_black)):
                parts = bests[index].split()
                if len(parts) != 2 or parts[1] not in legal:
                    record.update({"passed": False, "error": "final bestmove is illegal or stale"})
            record.setdefault("cancel_search", {"bestmove": bests[1].split()[1]})
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--minimum-available-bytes", type=int, default=6 * GIB)
    parser.add_argument("--max-rss-bytes", type=int, default=3 * GIB)
    parser.add_argument("--address-space-bytes", type=int, default=8 * GIB)
    parser.add_argument("--data-bytes", type=int, default=8 * GIB)
    parser.add_argument("--cpu-seconds", type=int, default=60)
    parser.add_argument("--timeout-seconds", type=float, default=45)
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("Linux /proc and resource limits are required")
    args.out = args.out.resolve()
    root = Path(__file__).resolve().parents[2]
    if args.out.exists() or root == args.out or root in args.out.parents:
        parser.error("--out must be a new external JSON path")
    if not math.isfinite(args.timeout_seconds) or not 0 < args.timeout_seconds <= 45:
        parser.error("whole-process timeout must be finite and at most 45 seconds")
    if min(args.minimum_available_bytes, args.max_rss_bytes, args.address_space_bytes, args.data_bytes, args.cpu_seconds) <= 0:
        parser.error("resource bounds must be positive")
    raw = args.manifest.read_bytes()
    manifest = json.loads(raw)
    if not manifest.get("complete"):
        parser.error("build manifest is incomplete")
    expected = manifest["profile"]["expected_total_threads"]
    if expected != manifest["profile"]["search_workers"] + 1:
        parser.error("profile must count stdin plus all search workers")
    report = {"schema": 1, "scope": "bounded clocked search/cancellation and observed memory; no performance or hardware-scalability claim",
              "logical_cpus": os.cpu_count(), "oversubscribed": expected > (os.cpu_count() or 1),
              "cpu_budget_reason": "Default60s rationale on8CPUs: 3s completion +3s cancellation +1s observer fence permits56 aggregate CPU seconds, plus startup/margin; observer aims for40ms. Actual CPU limit and CPU count are recorded separately; wall45s remains independent.",
              "requested_cpu_seconds": args.cpu_seconds,
              "manifest": str(args.manifest), "manifest_sha256": hashlib.sha256(raw).hexdigest(),
              "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "shared_startup_helper_sha256": hashlib.sha256(Path(__file__).with_name("target_startup.py").read_bytes()).hexdigest(),
              "oracle_sha256": hashlib.sha256(Path(__file__).with_name("chess_oracle.py").read_bytes()).hexdigest(),
              "profile": manifest["profile"], "profile_name": manifest["profile_name"],
              "runs": [], "complete": False}
    selected = {e["id"]: e for e in manifest["engines"] if e["id"] in SELECTED}
    if set(selected) != set(SELECTED):
        parser.error("manifest must contain all four A/F C/Rust configurations")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    for name, cancellation in SELECTED.items():
        engine = selected[name]
        if int(engine["configuration"]["ROVE_WORKERS"]) + 1 != expected:
            parser.error("artifact configuration does not match profile")
        original = [a for a in engine["artifacts"] if a.get("format") == "native-elf" and a.get("source_form") == "original"]
        if len(original) != 1:
            parser.error("expected exactly one original native artifact")
        artifact = original[0]
        path = Path(artifact["path"])
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != artifact["sha256"] or data[:4] != b"\x7fELF":
            raise RuntimeError("native artifact identity mismatch")
        record = {"id": name, "path": str(path), "sha256": artifact["sha256"],
                  "generation_config_sha256": engine.get("generation_config_sha256"),
                  "generation_config": engine.get("generation_config"),
                  "native_compiler_command": artifact["command"],
                  "configuration": engine["configuration"],
                  **check(path, expected, cancellation, args)}
        record["sha256_after_execution"] = hashlib.sha256(path.read_bytes()).hexdigest()
        if record["sha256_after_execution"] != artifact["sha256"]:
            record.update({"passed": False, "error": "native artifact changed during execution"})
        report["runs"].append(record)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({key: record.get(key) for key in ("id", "cancellation", "passed", "observed_peak_rss_bytes", "error")}), flush=True)
        if not record["passed"]:
            return 1
    report["complete"] = True
    report["passed"] = True
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
