#!/usr/bin/env python3
"""Check closed parent stdio against the selected Fastchess Process and runner.

This owns only local mock processes. A passing result is not a GO receipt,
remote ownership proof, tournament qualification, or performance evidence.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("rove_closed_stdio_write_tests", HERE / "test_fastchess_write.py")
write_tests = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = write_tests
spec.loader.exec_module(write_tests)
fastchess = write_tests.fastchess

PROCESS_HARNESS = r'''#include <engine/process/process_posix.hpp>
#include <chrono>
#include <iostream>
#include <string>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>
namespace fastchess { const char* version = "fixture"; }
using fastchess::engine::process::Process;
using fastchess::engine::process::Line;
static int exercise(int mask, char* engine) {
    // No opened fixture descriptors intervene before Process creates pipes.
    for (int fd = 0; fd < 3; ++fd) if (mask & (1 << fd)) close(fd);
    Process process;
    auto opened = process.init("/tmp", "/usr/bin/python3", std::string("-u ") + engine, "closed-fds");
    if (!opened) return 10;
    if (!process.writeInput("hello\n")) return 11;
    std::vector<Line> lines;
    auto reply = process.readOutput(lines, "ACK:", std::chrono::seconds(3));
    if (!reply || lines.empty() || lines.back().line != "ACK:hello") return 12;
    if (!process.writeInput("quit\n")) return 13;
    process.terminate();
    return 0;
}
int main(int argc, char** argv) {
    if (argc != 2) return 90;
    for (int mask = 1; mask < 8; ++mask) {
        pid_t pid = fork();
        if (pid < 0) return 91;
        if (pid == 0) _exit(exercise(mask, argv[1]));
        int status = 0;
        if (waitpid(pid, &status, 0) != pid) return 92;
        if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
            std::cout << "mask=" << mask << " status=" << status << "\n";
            return 20 + mask;
        }
    }
    std::cout << "lifecycle-ok\n";
}
'''


def _group_absent(pid: int) -> bool:
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def _runner_case(binary: Path, root: Path, mask: int) -> dict:
    directory = root / ("mask-" + str(mask))
    directory.mkdir()
    mock = directory / "mock.py"
    mock.write_text(write_tests.runtime.MOCK, encoding="utf-8")
    book = directory / "book.pgn"
    book.write_text('[Event "Fixture only"]\n[Result "*"]\n\n1. f3 e5 *\n', encoding="utf-8")
    trace_a, trace_b = directory / "a.jsonl", directory / "b.jsonl"
    a = fastchess.EngineCommand("mock-a", (sys.executable, str(mock), str(trace_a), "normal"))
    b = fastchess.EngineCommand("mock-b", (sys.executable, str(mock), str(trace_b), "normal"))
    argv = fastchess.single_game_argv(binary, a, b, opening_pgn=book, opening_start=1, out=directory)
    argv[argv.index("tc=30:00+3")] = "tc=0:01+0"
    env = dict(os.environ)
    for key in ("ROVE_START_FD", "ROVE_START_JOB", "ROVE_START_PROTOCOL", "ROVE_OPENING_FD", "LD_PRELOAD"):
        env.pop(key, None)

    def close_standard() -> None:
        for fd in range(3):
            if mask & (1 << fd):
                try:
                    os.close(fd)
                except OSError:
                    pass

    started = time.monotonic()
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, env=env, start_new_session=True,
                               preexec_fn=close_standard)
    try:
        code = process.wait(timeout=45)
    except subprocess.TimeoutExpired:
        # The unreaped child reserves this process-group ID; never target any
        # unrelated process and never reuse an observed timeout as success.
        fastchess.signal_owned_group(process.pid, signal.SIGKILL)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired as error:
            raise AssertionError(f"mask {mask}: timed-out runner leader did not settle") from error
        deadline = time.monotonic() + 2
        while not _group_absent(process.pid) and time.monotonic() < deadline:
            time.sleep(.02)
        raise AssertionError(f"mask {mask}: owned runner timed out; group_absent={_group_absent(process.pid)}")
    # A completed leader does not itself prove descendant termination.
    deadline = time.monotonic() + 2
    while not _group_absent(process.pid) and time.monotonic() < deadline:
        time.sleep(.02)
    if not _group_absent(process.pid):
        # Do not signal a group ID after reaping the leader: its identity is no
        # longer held by this fixture. Treat uncertain settlement as failure.
        raise AssertionError(f"mask {mask}: runner group did not settle")

    rows = {key: write_tests._rows(path) if path.exists() else []
            for key, path in (("a", trace_a), ("b", trace_b))}
    pgn_path = directory / "game.pgn"
    pgn = pgn_path.read_text(encoding="utf-8") if pgn_path.exists() else ""
    if code or '[Result "0-1"]' not in pgn:
        raise AssertionError(f"mask {mask}: runner={code}, fixture game failed")
    for key in ("a", "b"):
        commands = [row.get("line", "") for row in rows[key] if row.get("event") == "input"]
        if "uci" not in commands or "isready" not in commands or not any(x.startswith("go ") for x in commands):
            raise AssertionError(f"mask {mask}: engine {key} UCI handshake/search incomplete")
    return {"closed_mask": mask, "runner_exit": code, "group_absent": True,
            "result": "0-1", "elapsed_ms": round((time.monotonic() - started) * 1000),
            "a_rows": len(rows["a"]), "b_rows": len(rows["b"])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("Linux required")
    output = fastchess._external_new(args.out)
    binary, built = write_tests._validate_build(args.build)
    output.mkdir(parents=True)
    report = {"complete": False, "scope": "owned local Process and runner mocks; not league or GO evidence",
              "runner_sha256": built["binary_sha256"], "patch_sha256": built["patch_sha256"],
              "cases": []}
    report_path = output / "closed-stdio.json"
    try:
        write_tests.LIFECYCLE_CPP = PROCESS_HARNESS
        report["process_fixture"] = write_tests._lifecycle(args.source, args.build, built, output)
        for mask in range(1, 8):
            report["cases"].append(_runner_case(binary, output, mask))
        report["complete"] = True
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
