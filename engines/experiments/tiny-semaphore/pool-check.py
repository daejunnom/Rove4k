#!/usr/bin/env python3
"""Controlled lifetime/fault checks for the actual frozen semaphore runtime.

Compile the C interposer with unchanged board/search/runtime sources. Every
process, pipe and generated file belongs to this invocation. A timed-out process
is recorded as unknown before bounded cleanup; cleanup never turns it into a
passing case. This proves controlled schedules, not absence of every race.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_FROZEN = Path("/home/stemxstudio/rove4k-tiny-semaphore-first-20261020/frozen/semaphore")
MOVE = re.compile(r"bestmove (?:[a-h][1-8][a-h][1-8][nbrq]?|0000)\Z")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class Engine:
    """Drain both pipes without reader threads or stdout/stderr ordering claims."""
    def __init__(self, binary, directory, mode="normal", index=0):
        self.directory = directory
        directory.mkdir()
        self.control_read, self.control_write = os.pipe()
        command = [str(binary), "--mode", mode, "--index", str(index),
                   "--control-fd", str(self.control_read)]
        self.command = command
        self.mode = mode
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        pass_fds=(self.control_read,), bufsize=0)
        os.close(self.control_read)
        self.control_read = None
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ, "stdout")
        self.selector.register(self.process.stderr, selectors.EVENT_READ, "stderr")
        self.fragments = {"stdout": b"", "stderr": b""}
        self.raw = {"stdout": bytearray(), "stderr": bytearray()}
        self.stdout = []
        self.events = []
        self.observations = []
        self.cleanup = []
        self.released = False
        self.started = time.monotonic()

    def pump(self, seconds=0.02):
        for key, _mask in self.selector.select(max(0, seconds)):
            data = os.read(key.fileobj.fileno(), 65536)
            name = key.data
            if not data:
                self.selector.unregister(key.fileobj)
                continue
            self.raw[name].extend(data)
            self.fragments[name] += data
            while b"\n" in self.fragments[name]:
                line, self.fragments[name] = self.fragments[name].split(b"\n", 1)
                decoded = line.decode("utf-8", errors="replace").rstrip("\r")
                if name == "stdout":
                    self.stdout.append(decoded)
                else:
                    try:
                        event = json.loads(decoded)
                    except json.JSONDecodeError:
                        self.observations.append({"non_json_stderr": decoded})
                    else:
                        require(isinstance(event, dict) and "event" in event,
                                "interposer trace must contain event objects")
                        self.events.append(event)

    def until(self, predicate, label, timeout=5, allow_exit=False):
        deadline = time.monotonic() + timeout
        while True:
            self.pump(0.01)
            if predicate():
                return
            if self.process.poll() is not None:
                self.pump(0)
                if predicate():
                    return
                if not allow_exit:
                    raise AssertionError(f"process exited {self.process.returncode} before {label}")
            if time.monotonic() >= deadline:
                raise TimeoutError(f"unknown: timed out waiting for {label}; pid={self.process.pid}")

    def send(self, text, allow_closed=False):
        try:
            self.process.stdin.write(text.encode())
            self.process.stdin.flush()
        except (BrokenPipeError, ValueError):
            if not allow_closed:
                raise

    def count(self, event, index=None):
        return sum(item["event"] == event and
                   (index is None or item.get("index") == index) for item in self.events)

    def matching(self, event, index=None):
        return [item for item in self.events if item["event"] == event and
                (index is None or item.get("index") == index)]

    def lines(self, prefix):
        return [line for line in self.stdout if line.startswith(prefix)]

    def quiet(self, seconds=0.15):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.pump(min(0.02, deadline - time.monotonic()))

    def tids(self):
        return sorted(int(path.name) for path in Path(f"/proc/{self.process.pid}/task").iterdir())

    def startup(self):
        self.until(lambda: self.count("worker_ready") == 2, "two startup workers")
        self.quiet(0.03)
        tids = self.tids()
        require(len(tids) == 3, f"startup requires exactly three threads, got {tids}")
        require(not self.stdout, "runtime read or emitted protocol before input")
        self.observations.append({"startup_tids_before_input": tids})
        return tids

    def ready(self):
        before = self.stdout.count("readyok")
        self.send("isready\n")
        self.until(lambda: self.stdout.count("readyok") == before + 1, "readyok")

    def release(self):
        require(not self.released, "gate was already released")
        os.write(self.control_write, b"R")
        self.released = True
        self.observations.append({"release_after_events": len(self.events),
                                  "release_after_bestmoves": len(self.lines("bestmove "))})

    def finish(self, expected=0, timeout=5, eof=False):
        if eof:
            self.process.stdin.close()
        else:
            self.send("quit\n", allow_closed=True)
        self.until(lambda: self.process.poll() is not None, "bounded process exit", timeout,
                   allow_exit=True)
        self.until(lambda: not self.selector.get_map(), "both output pipes drained to EOF", timeout,
                   allow_exit=True)
        require(self.process.returncode == expected,
                f"expected exit {expected}, got {self.process.returncode}")
        require(not self.observations_nonjson(), "unexpected stderr outside JSON trace")
        require(all(MOVE.fullmatch(line) for line in self.lines("bestmove ")),
                "malformed bestmove line")
        graceful = self.mode not in ("wait-fail", "post-fail", "join-fail")
        exits = self.matching("exit")
        if graceful:
            require(len(exits) == 1 and exits[0].get("value") == expected,
                    "graceful runtime return is missing its exact status trace")
        else:
            require(not exits, "fatal runtime fault unexpectedly returned through main")

    def observations_nonjson(self):
        return [item for item in self.observations if "non_json_stderr" in item]

    def cleanup_owned(self):
        """Only this case's known Popen PID; a failed wait remains failed."""
        if self.process.poll() is None:
            self.cleanup.append({"live_pid_on_failure": self.process.pid,
                                 "status": "unknown before cleanup"})
            if not self.released:
                try:
                    self.release()
                except OSError:
                    pass
            self.send("quit\n", allow_closed=True)
            try:
                self.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self.cleanup.append({"terminate_owned_pid": self.process.pid})
                self.process.terminate()
                try:
                    self.process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    self.cleanup.append({"kill_owned_pid": self.process.pid})
                    self.process.kill()
                    self.process.wait(timeout=1)
        self.quiet(0.01)
        self.selector.close()
        os.close(self.control_write)
        self.control_write = None
        for pipe in (self.process.stdin, self.process.stdout, self.process.stderr):
            if pipe and not pipe.closed:
                pipe.close()

    def record(self, name, passed, error=None):
        (self.directory / "stdout.txt").write_bytes(self.raw["stdout"])
        (self.directory / "stderr.jsonl").write_bytes(self.raw["stderr"])
        result = {"name": name, "passed": passed, "error": error,
                  "command": self.command, "pid": self.process.pid,
                  "returncode": self.process.returncode,
                  "elapsed_seconds": round(time.monotonic() - self.started, 6),
                  "events": self.events, "stdout": self.stdout,
                  "observations": self.observations, "cleanup": self.cleanup}
        (self.directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result


def clean_prefix(engine, initialized, created):
    """Initialization failures must join/destroy exactly the successful prefix."""
    require([item["index"] for item in engine.matching("init")] == list(range(initialized)),
            "successful initialized prefix differs")
    require([item["index"] for item in engine.matching("create")] == list(range(created)),
            "successful created prefix differs")
    require([item["index"] for item in engine.matching("join")] == list(range(created)),
            "created prefix not joined exactly once")
    require([item["index"] for item in engine.matching("destroy")] == list(range(initialized)),
            "initialized prefix not destroyed exactly once")


def normal(engine):
    tids = engine.startup()
    engine.send("uci\n")
    engine.until(lambda: "uciok" in engine.stdout, "uciok")
    engine.ready()
    require(engine.tids() == tids, "threads changed during initial protocol")
    for cycle in range(96):
        before = len(engine.lines("bestmove "))
        ready_before = engine.stdout.count("readyok")
        command = ("go infinite", "go depth 1", "go movetime 2")[cycle % 3]
        position = "position startpos" + (" moves e2e4" if cycle & 1 else "")
        engine.send(f"{command}\nstop\n{position}\nucinewgame\nisready\n")
        engine.until(lambda: engine.stdout.count("readyok") == ready_before + 1,
                     f"rapid cycle {cycle} stop/position/newgame")
        require(len(engine.lines("bestmove ")) == before + 1,
                f"rapid cycle {cycle} did not emit exactly one result")
        if cycle % 8 == 0:
            require(engine.tids() == tids, f"worker lifetime changed at cycle {cycle}")
    engine.send("position startpos\ngo wtime 1000 btime 1000 winc 0 binc 0\n")
    engine.until(lambda: len(engine.lines("bestmove ")) == 97, "clocked search completion")
    engine.send("stop\n")
    engine.ready()
    require(len(engine.lines("bestmove ")) == 97, "stop duplicated completed clock result")
    require(engine.tids() == tids, "worker lifetime changed after rapid/clock searches")
    engine.observations.append({"rapid_go_stop_position_newgame_cycles": 96,
                                "stable_tids": tids, "bestmoves": 97})
    engine.finish()
    clean_prefix(engine, 4, 2)
    publications = engine.matching("publish")
    require([item["generation"] for item in publications] == list(range(1, 98)),
            "normal run must publish exactly generations 1 through 97")
    generation_summary = []
    for generation in range(1, 98):
        jobs = [item["index"] for item in engine.matching("job")
                if item["generation"] == generation]
        posts = [item["index"] for item in engine.matching("post")
                 if item["generation"] == generation and item["index"] in (0, 1)]
        require(sorted(jobs) == [0, 1],
                f"generation {generation} must execute exactly one job per worker")
        expected_posts = [0, 1] if generation < 97 else [0, 0, 1, 1]
        require(sorted(posts) == expected_posts,
                f"generation {generation} private job/shutdown post accounting differs")
        generation_summary.append({"generation": generation, "job_indices": sorted(jobs),
                                   "private_post_indices": sorted(posts)})
    require([engine.count("post", index) for index in (0, 1)] == [98, 98],
            "each private semaphore needs 97 GO posts and one shutdown post")
    require(engine.count("job") == 194, "normal run must execute exactly 194 search jobs")
    engine.observations.append({"exact_generation_accounting": generation_summary,
                                "private_post_totals": {"0": 98, "1": 98},
                                "search_job_total": 194,
                                "shutdown_posts_in_generation": 97,
                                "traces_drained_to_eof_before_accounting": True})


def active_exit(engine, eof):
    tids = engine.startup()
    engine.send("go infinite\n")
    engine.until(lambda: engine.count("job") >= 2, "both active search workers")
    require(engine.tids() == tids, "active search added or replaced threads")
    engine.finish(eof=eof)
    require(len(engine.lines("bestmove ")) == 1, "active exit must settle one search once")
    clean_prefix(engine, 4, 2)


def late_wait(engine):
    engine.startup()
    engine.until(lambda: engine.count("wait_gate", 1) == 1, "private wait gate")
    engine.send("go depth 1\n")
    engine.until(lambda: engine.count("post", 1) >= 1, "real private job post before wait")
    engine.until(lambda: len(engine.lines("bestmove ")) == 1, "stored-token wake and completed job")
    require(engine.count("wait_return", 1) >= 1, "stored job post did not wake late waiter")
    require(engine.matching("post", 1)[0]["seq"] < engine.matching("wait_enter", 1)[0]["seq"],
            "real private job post must precede the gated real sem_wait call")
    engine.observations.append({"late_wait_gate": "fixture condition gate releases only after real sem_post(1)",
                                "post_before_wait_verified_by_trace_sequence": True})
    engine.ready()
    engine.finish()
    clean_prefix(engine, 4, 2)


def hold_worker(engine):
    engine.startup()
    engine.until(lambda: engine.count("wait_enter", 0) >= 1,
                 "worker-zero initial real idle wait before any job")
    initial_idle = engine.count("wait_enter", 0)
    require(initial_idle == 1, "worker-zero must have exactly one initial private wait")
    engine.send("go depth 1\n")
    engine.until(lambda: engine.count("hold_worker", 1) == 1, "worker-one controlled hold")
    engine.until(lambda: engine.count("wait_enter", 0) == initial_idle + 1 and
                 engine.count("job", 0) == 1,
                 "other worker returned to private idle wait")
    job = engine.matching("job", 0)[0]
    idle = engine.matching("wait_enter", 0)[1]
    require(job["seq"] < idle["seq"], "second private idle wait must follow the real job")
    require(not engine.lines("bestmove "), "result emitted before every worker completed")
    pending = [item.get("value") for item in engine.events if "value" in item]
    engine.observations.append({"other_worker_idle_before_release": True,
                                "initial_worker_zero_wait_count": initial_idle,
                                "worker_zero_job_count_before_release": engine.count("job", 0),
                                "worker_zero_wait_count_before_release": engine.count("wait_enter", 0),
                                "worker_zero_job_seq": job["seq"],
                                "worker_zero_returned_idle_seq": idle["seq"],
                                "observed_pending_values": pending})
    engine.send("stop\nisready\n")
    engine.quiet()
    require(not engine.lines("bestmove ") and "readyok" not in engine.stdout,
            "stop advanced past incomplete worker")
    engine.release()
    engine.until(lambda: engine.stdout.count("readyok") == 1, "stop settled after worker release")
    require(len(engine.lines("bestmove ")) == 1, "released search did not settle once")
    engine.finish()
    clean_prefix(engine, 4, 2)


def hold_done(engine, quit_only=False):
    engine.startup()
    engine.send("go depth 1\n")
    engine.until(lambda: len(engine.lines("bestmove ")) == 1 and
                 engine.count("hold_done", 2) == 1, "stdout result before done-token gate")
    commits = engine.count("position_commit")
    publications = engine.count("publish")
    before_wait = engine.count("wait_enter", 2)
    if quit_only:
        engine.send("quit\n")
    else:
        engine.send("position startpos moves e2e4\nstate\nisready\n")
    engine.until(lambda: engine.count("wait_enter", 2) > before_wait,
                 "input owner waiting for held completion token")
    engine.quiet()
    require(engine.process.poll() is None, "input owner exited before done token")
    require(not engine.lines('{"hash"') and "readyok" not in engine.stdout,
            "position/state advanced before done token")
    require(engine.count("position_commit") == commits and engine.count("publish") == publications,
            "input owner committed state or published GO before completion token")
    engine.release()
    if not quit_only:
        engine.until(lambda: engine.stdout.count("readyok") == 1, "position after done release")
        state = [json.loads(line) for line in engine.lines('{"hash"')]
        require(len(state) == 1 and state[0]["halfmove"] == 0 and state[0]["invariant"],
                "position was not valid after completion release")
    engine.finish()
    require(len(engine.lines("bestmove ")) == 1, "completion token release duplicated result")
    clean_prefix(engine, 4, 2)


def hold_output(engine):
    engine.startup()
    engine.send("go depth 1\n")
    engine.until(lambda: engine.count("hold_output") == 1, "real stdout flush gate")
    require(not engine.lines("bestmove "), "bestmove was visible before controlled stdout flush")
    commits = engine.count("position_commit")
    publications = engine.count("publish")
    before_wait = engine.count("wait_enter", 2)
    engine.send("position startpos moves e2e4\nstate\nisready\n")
    engine.until(lambda: engine.count("wait_enter", 2) > before_wait,
                 "position owner awaiting output/completion")
    engine.quiet()
    require(engine.process.poll() is None, "input owner exited before output flush")
    require(not engine.lines("bestmove ") and not engine.lines('{"hash"'),
            "result/state became visible before controlled output flush")
    require(engine.count("position_commit") == commits and engine.count("publish") == publications,
            "input owner mutated/published position before physical result flush")
    engine.release()
    engine.until(lambda: engine.stdout.count("readyok") == 1, "position after stdout completion")
    require(len(engine.lines("bestmove ")) == 1 and engine.count("output_flushed") >= 1,
            "physical output did not complete exactly one result")
    state = [json.loads(line) for line in engine.lines('{"hash"')]
    require(len(state) == 1 and state[0]["invariant"], "committed position invalid after output release")
    engine.until(lambda: engine.count("position_commit") == commits + 1,
                 "trace of position commit after physical flush")
    committed = engine.matching("position_commit")[-1]
    flushed = engine.matching("output_flushed")[0]
    require(flushed["seq"] < committed["seq"], "position commit preceded real physical stdout flush")
    engine.send("go depth 1\n")
    engine.until(lambda: len(engine.lines("bestmove ")) == 2, "new job after output release")
    engine.until(lambda: engine.count("publish") == publications + 1,
                 "trace of new-position publication")
    published = engine.matching("publish")[-1]
    require(published.get("hash") == state[0]["hash"],
            "new job publication did not use the newly committed position hash")
    engine.finish()
    clean_prefix(engine, 4, 2)


def eintr_each(engine):
    engine.startup()
    engine.send("go depth 1\n")
    engine.until(lambda: len(engine.lines("bestmove ")) == 1, "search after interrupted waits")
    engine.ready()
    engine.finish()
    require(sorted(item["index"] for item in engine.matching("wait_eintr")) == [0, 1, 2, 3],
            "each semaphore must encounter exactly one EINTR and retry")
    clean_prefix(engine, 4, 2)


def fault(engine, mode, index):
    # Startup faults can exit before any stdin byte. Later call faults are
    # reached by this same bounded command sequence, without a restart.
    engine.send("uci\nposition startpos\ngo depth 1\nstop\nquit\n", allow_closed=True)
    engine.finish(expected=2)
    require("uciok" not in engine.stdout or mode in ("wait-fail", "post-fail", "join-fail"),
            "startup failure advertised protocol readiness")
    if mode == "init-fail":
        require(engine.count("init_fail", index) == 1, "requested initialization fault missing")
        clean_prefix(engine, index, 0)
    elif mode == "create-fail":
        require(engine.count("create_fail", index) == 1, "requested thread-creation fault missing")
        clean_prefix(engine, 4, index)
    elif mode == "calloc-fail":
        require(engine.count("calloc_fail", 0) == 1, "requested allocation fault missing")
        require(engine.count("init") == engine.count("create") == 0,
                "pool initialized after failed table allocation")
    else:
        event = {"wait-fail": "wait_fail", "post-fail": "post_fail",
                 "join-fail": "join_fail"}[mode]
        require(engine.count(event, index) == 1, f"requested {event} fault missing")
        if mode == "join-fail":
            require([item["index"] for item in engine.matching("join")] == list(range(index)),
                    "join failure did not retain the successful joined prefix")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen", type=Path, default=DEFAULT_FROZEN,
                        help="frozen directory containing tiny.h, board.c, search.c, main.c")
    parser.add_argument("--fixture", type=Path, default=HERE / "pool-contract.c")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    if os.name != "posix" or not Path("/proc/self/task").exists():
        parser.error("Linux /proc and POSIX pipes are required; run this harness in WSL Ubuntu")
    output = args.out.resolve()
    if not args.out.is_absolute() or output.exists() or output == ROOT or ROOT in output.parents:
        parser.error("--out must be a new absolute directory outside the repository")
    source = args.frozen.resolve()
    if (source / "semaphore").is_dir():
        source /= "semaphore"
    modules = [source / name for name in ("tiny.h", "board.c", "search.c", "main.c")]
    if any(not path.is_file() for path in modules) or not args.fixture.is_file():
        parser.error("frozen modules and C fixture must all exist")
    output.mkdir(parents=True)
    frozen = output / "frozen"
    frozen.mkdir()
    for path in modules:
        shutil.copyfile(path, frozen / path.name)
    shutil.copyfile(args.fixture, frozen / "pool-contract.c")
    shutil.copyfile(__file__, frozen / "pool-check.py")
    flags = ["-std=c11", "-O2", "-g", "-Wall", "-Wextra", "-pthread",
             "-DWORKERS=2", "-DTT_BITS=18", "-DDEV=1", "-I", str(frozen)]
    if args.sanitize:
        flags += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie"]
    for macro, name in (("BOARD_SOURCE", "board.c"), ("SEARCH_SOURCE", "search.c"),
                        ("RUNTIME_SOURCE", "main.c")):
        flags.append(f'-D{macro}="{frozen / name}"')
    command = [args.cc, *flags, str(frozen / "pool-contract.c"), "-o", str(output / "pool-contract")]
    compiled = subprocess.run(command, capture_output=True, timeout=60)
    (output / "compile.stdout.txt").write_bytes(compiled.stdout)
    (output / "compile.stderr.txt").write_bytes(compiled.stderr)
    metadata = {"scope": "controlled real-runtime semaphore lifetime/fault experiment; no size/performance claim",
                "source_origin": str(source), "fixed_profile": {"workers": 2, "tt_bits": 18, "dev": 1},
                "source_sha256": {path.name: digest(frozen / path.name) for path in modules},
                "fixture_sha256": digest(frozen / "pool-contract.c"),
                "harness_sha256": digest(frozen / "pool-check.py"),
                "compile_command": command, "compile_returncode": compiled.returncode,
                "sanitizers": args.sanitize, "cases": []}
    if compiled.returncode:
        (output / "results.json").write_text(json.dumps(metadata, indent=2) + "\n")
        raise SystemExit(compiled.returncode)
    metadata["program_sha256"] = digest(output / "pool-contract")
    cases = [("normal-96-cycles", "normal", 0, normal),
             ("quit-active", "normal", 0, lambda engine: active_exit(engine, False)),
             ("eof-active", "normal", 0, lambda engine: active_exit(engine, True)),
             ("post-before-private-wait", "late-wait", 1, late_wait),
             ("all-workers-before-result", "hold-worker", 1, hold_worker),
             ("done-token-before-position", "hold-done", 2, hold_done),
             ("done-token-before-quit", "hold-done", 2, lambda engine: hold_done(engine, True)),
             ("physical-output-before-position", "hold-output", 0, hold_output),
             ("retry-eintr-all-signals", "eintr-each", 0, eintr_each)]
    for mode, indices in (("init-fail", range(4)), ("create-fail", range(2)),
                          ("wait-fail", range(4)), ("post-fail", range(4)),
                          ("join-fail", range(2)), ("calloc-fail", range(1))):
        for index in indices:
            cases.append((f"{mode}-{index}", mode, index,
                          lambda engine, selected=mode, at=index: fault(engine, selected, at)))
    for name, mode, index, check in cases:
        engine = Engine(output / "pool-contract", output / name, mode, index)
        passed, error = False, None
        try:
            check(engine)
            passed = True
        except Exception as failure:
            error = f"{type(failure).__name__}: {failure}"
        finally:
            engine.cleanup_owned()
        result = engine.record(name, passed, error)
        metadata["cases"].append({"name": name, "passed": passed, "error": error,
                                  "returncode": result["returncode"],
                                  "elapsed_seconds": result["elapsed_seconds"],
                                  "result": str(engine.directory / "result.json")})
        metadata["passed"] = sum(item["passed"] for item in metadata["cases"])
        metadata["total"] = len(metadata["cases"])
        (output / "results.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(json.dumps(metadata["cases"][-1]), flush=True)
    metadata["all_passed"] = metadata["passed"] == metadata["total"]
    (output / "results.json").write_text(json.dumps(metadata, indent=2) + "\n")
    raise SystemExit(0 if metadata["all_passed"] else 1)


if __name__ == "__main__":
    main()
