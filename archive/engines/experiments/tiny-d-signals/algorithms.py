#!/usr/bin/env python3
"""Exercise retained search contracts and exact scalar/HQ production parity.

Use one worker for deterministic fixed-depth comparisons. The independent
black-box oracle remains a separate gate; matching two backends alone cannot
establish chess correctness.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cleanup_group(process):
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.kill()
    if process.poll() is None:
        process.wait(timeout=2)


def run_bounded(command, *, timeout):
    process = subprocess.Popen(command, start_new_session=os.name == "posix")
    try:
        code = process.wait(timeout=timeout)
        if code:
            raise subprocess.CalledProcessError(code, command)
        return subprocess.CompletedProcess(command, code)
    finally:
        # A timed-out retained Python checker or compiler must not orphan its
        # engine, cc1 or linker descendants when its own finally cannot run.
        cleanup_group(process)


class Engine:
    def __init__(self, path, *, deadline=float("inf"), command_timeout=10):
        self.deadline, self.command_timeout = deadline, command_timeout
        self.process = subprocess.Popen([str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                                        start_new_session=os.name == "posix")
        self.lines = queue.Queue()
        self.transcript = []
        def read():
            for line in self.process.stdout:
                self.lines.put(line.strip())
            self.lines.put(None)
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()

    def command(self, text, prefix):
        self.transcript.append({"stdin": text})
        self.process.stdin.write(text + "\n")
        self.process.stdin.flush()
        lines = []
        deadline = min(self.deadline, time.monotonic() + self.command_timeout)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("engine command exceeded total wall deadline: " + text)
            try:
                line = self.lines.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError("engine command exceeded total wall deadline: " + text) from None
            if line is None:
                raise AssertionError("unexpected engine EOF")
            lines.append(line)
            self.transcript.append({"stdout": line})
            if line.startswith(prefix):
                return lines

    def send(self, text):
        self.transcript.append({"stdin": text})
        self.process.stdin.write(text + "\n")
        self.process.stdin.flush()

    def close(self):
        try:
            if self.process.poll() is None:
                self.send("quit")
                self.process.wait(timeout=max(.001, min(3, self.deadline - time.monotonic())))
        finally:
            # The process owns a new session, so abnormal exits cannot strand
            # its children. Cleanup also runs when sending quit or waiting fails.
            cleanup_group(self.process)
            self.reader.join(timeout=.2)
            self.transcript.append({"exit": self.process.returncode})
        if self.process.returncode:
            raise AssertionError("engine exit " + str(self.process.returncode))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=300,
                        help="aggregate wall budget for compilation, retained checks and comparisons")
    args = parser.parse_args()
    if args.out.is_absolute():
        args.out = args.out.resolve()
    if not args.out.is_absolute() or args.out.exists() or HERE.parents[2] in args.out.parents:
        parser.error("--out must be a new absolute directory outside Git")
    if not 0 < args.timeout <= 600:
        parser.error("--timeout must be within 0..600 seconds")
    args.out.mkdir(parents=True)
    started = time.monotonic()
    deadline = started + args.timeout

    def remaining(limit):
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            raise TimeoutError("algorithm checks exceeded aggregate wall deadline")
        return min(limit, seconds)

    frozen_check = args.out / "check-retained.py"
    binaries, engines, comparisons = [], [], []
    report = {"forms": [], "comparisons": comparisons, "passed": False,
              "timeout_seconds": args.timeout, "build_manifest": str(args.build)}
    cases = [
        "position startpos",
        "position fen r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "position fen 8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "position fen 6k1/8/8/3pP3/8/8/8/6K1 w - d6 0 1",
        "position fen 7k/P7/8/8/8/8/8/K7 w - - 0 1",
    ]
    try:
        shutil.copyfile(HERE.parents[1] / "compact/tiny-a/check.py", frozen_check)
        build = json.loads(args.build.read_text())
        report.update(source_manifest_sha256=sha(args.build), retained_check_sha256=sha(frozen_check))
        for record in build["engines"]:
            if record["profile"] != "dev":
                continue
            directory = args.out / record["id"]
            directory.mkdir()
            command = ["-DWORKERS=1" if arg.startswith("-DWORKERS=") else arg for arg in record["compile"][:-1]]
            native = directory / "x"
            run_bounded(command + [str(native)], timeout=remaining(120))
            cap = directory / "cap"
            run_bounded(command[:-1] + ["-DPLY=4", "-o", str(cap)], timeout=remaining(120))
            run_bounded([sys.executable, str(frozen_check), "--engine", str(native), "--cap-engine", str(cap),
                         "--out", str(directory / "retained.json")], timeout=remaining(90))
            binaries.append(native)
            report["forms"].append({"id": record["id"], "program_sha256": sha(native), "cap_sha256": sha(cap),
                                   "retained_report_sha256": sha(directory / "retained.json")})
        if len(binaries) != 2:
            raise ValueError("expected exactly two development slider forms")
        for path in binaries:
            remaining(10)
            engines.append(Engine(path, deadline=deadline))
        for index, case in enumerate(cases):
            actual = []
            for engine in engines:
                engine.send("ucinewgame")
                engine.send(case)
                replies = engine.command("go depth 4", "bestmove ")
                actual.append(replies)
            if actual[0] != actual[1]:
                raise AssertionError("actual fixed-depth scalar/HQ search differs: " + str(actual))
            comparisons.append({"case": case, "replies": actual[0], "exact_parity": True})
        report["passed"] = True
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        for engine in engines:
            try:
                engine.close()
            except Exception as error:
                report["passed"] = False
                report.setdefault("cleanup_errors", []).append({"type": type(error).__name__, "message": str(error)})
        report["transcripts"] = [engine.transcript for engine in engines]
        report["elapsed_seconds"] = time.monotonic() - started
        (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "retained_contracts": len(report["forms"]), "fixed_depth_comparisons": len(comparisons)}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
