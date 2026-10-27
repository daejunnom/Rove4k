#!/usr/bin/env python3
"""Pinned external Fastchess preparation and the one-game league invocation.

The checkout, binary, logs and receipts must live outside Git. Only the small
reviewable patch is kept here; neither Fastchess nor peer engines are vendored.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import difflib
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
PIN = "ebfd64cb7fac80d4822c50b07dca4fe934779d21"
URL = "https://github.com/Disservin/fastchess.git"
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PATCH = HERE / "patches" / "fastchess-rove.patch"
PINS = {
    "app/src/engine/process/process_posix.hpp": "ffdbe2ce285ddb5e5558fd32035c6bbbfd96fb0493fc2af35f45faa12a5c81ef",
    "app/src/matchmaking/match/match.cpp": "c8e21fb6d3dc75a50365ca0b5a765aa05e1d155a8587ee775477cdc8741bab41",
    "app/src/main.cpp": "465606a822f6ca20fcaf6a1f75427e2cd0e2ffefc8e1b31cc72a99a58f6525a5",
}
HEADER = "app/src/core/rove_start_gate.hpp"

# The gate is outside the engine. It does not inspect or alter either engine's
# UCI traffic or clock, and is entered only after both ready handshakes.
GATE_HEADER = r'''#pragma once

#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <string>
#include <json.hpp>
#ifndef _WIN64
#include <cerrno>
#include <fcntl.h>
#include <poll.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#endif

namespace fastchess::rove {
inline int control_fd = -1;
inline nlohmann::json job;
inline std::atomic<bool> gate_used{false};

inline bool fail(const char* why) {
    std::fprintf(stderr, "ROVE_START_GATE_ABORT: %s\n", why);
    std::fflush(stderr);
    return false;
}

// Called in main, before any engine process can be spawned. pass_fds clears
// CLOEXEC for the runner, so reapply it here before engines inherit anything.
inline bool prepare() {
    const char* raw = std::getenv("ROVE_START_FD");
    const char* metadata = std::getenv("ROVE_START_JOB");
    if (!raw) return metadata ? fail("job without control FD") : true;
#ifdef _WIN64
    return fail("the league start gate requires POSIX");
#else
    char* end = nullptr;
    errno = 0;
    const long fd = std::strtol(raw, &end, 10);
    if (errno || !end || *end || end == raw || fd < 3 || fd > std::numeric_limits<int>::max())
        return fail("invalid control FD");
    control_fd = static_cast<int>(fd);
    const int flags = fcntl(control_fd, F_GETFD);
    if (flags < 0 || fcntl(control_fd, F_SETFD, flags | FD_CLOEXEC) < 0)
        return fail("cannot protect control FD");
    int type = 0;
    socklen_t length = sizeof(type);
    sockaddr_un address{};
    socklen_t address_length = sizeof(address);
    if (getsockopt(control_fd, SOL_SOCKET, SO_TYPE, &type, &length) || type != SOCK_STREAM ||
        getsockname(control_fd, reinterpret_cast<sockaddr*>(&address), &address_length) ||
        address.sun_family != AF_UNIX)
        return fail("control FD must be a Unix stream socket");
    if (!metadata || std::char_traits<char>::length(metadata) > 4096)
        return fail("missing or excessive job metadata");
    try {
        job = nlohmann::json::parse(metadata);
        if (!job.is_object()) return fail("job metadata must be an object");
    } catch (...) {
        return fail("invalid job JSON");
    }
    return true;
#endif
}

#ifndef _WIN64
inline int poll_left(std::chrono::steady_clock::time_point deadline) {
    const auto now = std::chrono::steady_clock::now();
    if (now >= deadline) return 0;
    const auto left = std::chrono::ceil<std::chrono::milliseconds>(deadline - now).count();
    return static_cast<int>(left > std::numeric_limits<int>::max() ?
                            std::numeric_limits<int>::max() : left);
}
#endif

inline bool await_start(int64_t white_clock, int64_t black_clock) {
    if (control_fd < 0) return true;
    if (gate_used.exchange(true)) return fail("one runner must own exactly one game");
#ifdef _WIN64
    return fail("the league start gate requires POSIX");
#else
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(180);
    const std::string message = nlohmann::json{{"event", "READY"}, {"job", job},
        {"white_clock_ms", white_clock}, {"black_clock_ms", black_clock}}.dump() + "\n";
    size_t sent = 0;
    while (sent < message.size()) {
        const auto count = send(control_fd, message.data() + sent, message.size() - sent,
                                MSG_NOSIGNAL | MSG_DONTWAIT);
        if (count > 0) { sent += static_cast<size_t>(count); continue; }
        if (count < 0 && errno == EINTR) continue;
        if (count < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            pollfd fd{control_fd, POLLOUT, 0};
            const int left = poll_left(deadline);
            if (left && poll(&fd, 1, left) > 0 && !(fd.revents & (POLLERR | POLLHUP))) continue;
        }
        return fail("READY delivery failed or timed out");
    }
    std::string command;
    while (true) {
        const int left = poll_left(deadline);
        if (!left) return fail("controller start deadline expired");
        pollfd fd{control_fd, POLLIN, 0};
        const int ready = poll(&fd, 1, left);
        if (ready < 0 && errno == EINTR) continue;
        if (ready <= 0) return fail("controller start deadline expired or poll failed");
        if (fd.revents & POLLIN) {
            char buffer[32];
            const auto count = recv(control_fd, buffer, sizeof(buffer), MSG_DONTWAIT);
            if (count < 0 && (errno == EINTR || errno == EAGAIN)) continue;
            if (count <= 0) return fail("controller disconnected");
            for (ssize_t i = 0; i < count; ++i) {
                command += buffer[i];
                if (command.size() > 16) return fail("invalid controller command");
                if (buffer[i] == '\n') {
                    if (command == "GO\n") return true;
                    return fail(command == "ABORT\n" ? "controller aborted wave" : "invalid controller command");
                }
            }
        }
        if (fd.revents & (POLLERR | POLLHUP | POLLNVAL)) return fail("controller disconnected");
    }
#endif
}
} // namespace fastchess::rove
'''


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def signal_owned_group(pid: int, sig: int) -> bool:
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        return False
    return True


def _replace_once(text: str, before: str, after: str, label: str) -> str:
    if text.count(before) != 1:
        raise ValueError("pinned Fastchess anchor changed: " + label)
    return text.replace(before, after, 1)


def patched_sources(originals: dict[str, bytes]) -> dict[str, bytes]:
    """Admit exact upstream bytes and produce the four reviewed patch outputs."""
    for path, expected in PINS.items():
        if path not in originals or sha(originals[path]) != expected:
            raise ValueError("pinned upstream source differs: " + path)
    result = {path: body.decode("utf-8") for path, body in originals.items()}
    path = "app/src/engine/process/process_posix.hpp"
    text = _replace_once(result[path], "#    include <optional>\n", "#    include <optional>\n#    include <limits>\n", "deadline include")
    text = _replace_once(text, "        const int poll_timeout_ms = normalize_poll_timeout_ms(threshold);\n", '''        const bool bounded = threshold.count() > 0;
        const auto began = std::chrono::steady_clock::now();
        const auto max_wait = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::time_point::max() - began);
        const auto deadline = bounded && threshold < max_wait ? began + threshold :
                              std::chrono::steady_clock::time_point::max();
''', "absolute deadline")
    text = _replace_once(text, "            const int ready = poll(fds.data(), static_cast<nfds_t>(fds_count), poll_timeout_ms);\n", '''            int poll_timeout_ms = -1;
            if (bounded) {
                const auto now = std::chrono::steady_clock::now();
                if (now >= deadline) {
                    flush_partials_on_timeout(lines);
                    return Result{Status::TIMEOUT, "timeout"};
                }
                const auto left = std::chrono::ceil<std::chrono::milliseconds>(deadline - now).count();
                poll_timeout_ms = static_cast<int>(left > std::numeric_limits<int>::max() ?
                                                   std::numeric_limits<int>::max() : left);
            }
            const int ready = poll(fds.data(), static_cast<nfds_t>(fds_count), poll_timeout_ms);
''', "remaining poll budget")
    text = _replace_once(text, "            if (ready == 0) {\n                flush_partials_on_timeout(lines);", "            if (ready == 0) {\n                if (bounded && std::chrono::steady_clock::now() < deadline) continue;\n                flush_partials_on_timeout(lines);", "long capped poll")
    result[path] = text
    path = "app/src/main.cpp"
    text = _replace_once(result[path], "#include <cstdlib>\n", "#include <cstdlib>\n#include <core/rove_start_gate.hpp>\n", "main gate include")
    result[path] = _replace_once(text, "int main(int argc, char const* argv[]) {\n    setCtrlCHandler();", "int main(int argc, char const* argv[]) {\n    if (!rove::prepare()) return EXIT_FAILURE;\n    setCtrlCHandler();", "early FD protection")
    path = "app/src/matchmaking/match/match.cpp"
    text = _replace_once(result[path], "#include <core/helper.hpp>\n", "#include <core/helper.hpp>\n#include <core/rove_start_gate.hpp>\n", "match gate include")
    result[path] = _replace_once(text, "    // check connection\n    validConnection(white_player, black_player);\n", '''    // check connection
    validConnection(white_player, black_player);

    if (data_.termination == MatchTermination::None &&
        !rove::await_start(white_player.getTimeControl().getTimeLeft(),
                          black_player.getTimeControl().getTimeLeft())) {
        atomic::abnormal_termination = true;
        atomic::stop = true;
        return;
    }
''', "pre-clock wave gate")
    outputs = {path: text.encode("utf-8") for path, text in result.items()}
    outputs[HEADER] = GATE_HEADER.encode("utf-8")
    return outputs


def make_patch(originals: dict[str, bytes], outputs: dict[str, bytes]) -> bytes:
    chunks = []
    for path in sorted(outputs):
        before = originals.get(path, b"").decode("utf-8").splitlines(keepends=True)
        after = outputs[path].decode("utf-8").splitlines(keepends=True)
        chunks.extend(difflib.unified_diff(before, after,
            fromfile="a/" + path if path in originals else "/dev/null", tofile="b/" + path))
    return "".join(chunks).encode("utf-8")


def _external_new(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError("absolute external output required")
    path = path.resolve()
    if not path.is_absolute() or path == REPO or REPO in path.parents:
        raise ValueError("absolute external output required")
    if any((parent / ".git").exists() for parent in (path, *path.parents)):
        raise ValueError("output must be outside every Git checkout")
    if path.exists():
        raise ValueError("new output required; existing work is preserved")
    return path


def _run_owned(argv: list[str], *, cwd: Path, log: Path, timeout: int, cpu: int | None = None) -> dict:
    """Own one process group, preserve its result, and settle timeout descendants."""
    if sys.platform != "linux":
        raise RuntimeError("run external Fastchess preparation/build in Linux, including WSL")
    import resource
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout + 5))
        resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
        resource.setrlimit(resource.RLIMIT_FSIZE, (64 << 20, 64 << 20))
        if cpu is not None:
            os.sched_setaffinity(0, {cpu})
    started = time.monotonic()
    forced = False
    with log.open("wb") as output:
        process = subprocess.Popen(argv, cwd=cwd, stdout=output, stderr=subprocess.STDOUT,
                                   start_new_session=True, preexec_fn=limits)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            forced = True
            signal_owned_group(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                signal_owned_group(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            code = process.returncode
    def group_exists():
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return False
        return True
    if group_exists():
        forced = True
        signal_owned_group(process.pid, signal.SIGKILL)
        settle_until = time.monotonic() + 2
        while group_exists() and time.monotonic() < settle_until:
            time.sleep(.02)
    group_absent = not group_exists()
    receipt = {"argv": argv, "pid": process.pid, "returncode": code,
               "elapsed_seconds": time.monotonic() - started, "forced_cleanup": forced,
               "leader_reaped": process.poll() is not None, "group_absent": group_absent,
               "log_sha256": sha(log.read_bytes())}
    log.with_name(log.stem + ".command.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if code or forced or not group_absent:
        raise RuntimeError("external command failed or did not settle: " + json.dumps(receipt))
    return receipt


def prepare_checkout(out: Path, *, write_patch: bool = False) -> dict:
    """Fetch one exact public source commit and apply only our reviewed changes."""
    out = _external_new(out)
    out.mkdir(parents=True)
    commands = []
    for index, argv in enumerate((
        ["git", "init", str(out)], ["git", "remote", "add", "origin", URL],
        ["git", "-c", "credential.helper=", "fetch", "--depth", "1", "origin", PIN],
        ["git", "checkout", "--detach", "FETCH_HEAD"],
    )):
        commands.append(_run_owned(argv, cwd=out, log=out / (f"prepare-{index}.log"), timeout=120))
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=out, text=True).strip()
    if head != PIN:
        raise ValueError("unexpected fetched Fastchess head")
    originals = {path: (out / path).read_bytes() for path in PINS}
    outputs = patched_sources(originals)
    patch = make_patch(originals, outputs)
    if write_patch:
        PATCH.parent.mkdir(parents=True, exist_ok=True)
        PATCH.write_bytes(patch)
    elif not PATCH.exists() or PATCH.read_bytes() != patch:
        raise ValueError("reviewed patch differs; do not update it automatically")
    for path, body in outputs.items():
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    receipt = {"complete": True, "upstream_url": URL, "upstream_commit": head,
               "patch_sha256": sha(patch), "source_inputs": PINS,
               "patched_sources": {path: sha(body) for path, body in outputs.items()},
               "commands": commands}
    (out / "rove-preparation.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def verify_checkout(source: Path) -> dict:
    if not source.is_absolute():
        raise ValueError("absolute external source required")
    source = source.resolve()
    if source == REPO or REPO in source.parents:
        raise ValueError("Fastchess must remain outside Rove4k")
    receipt = json.loads((source / "rove-preparation.json").read_text(encoding="utf-8"))
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    if head != PIN or receipt["upstream_commit"] != PIN or sha(PATCH.read_bytes()) != receipt["patch_sha256"]:
        raise ValueError("source or reviewed patch identity changed")
    changed = subprocess.check_output(["git", "diff", "--name-only"], cwd=source, text=True).splitlines()
    if set(changed) != set(PINS):
        raise ValueError("unexpected upstream changes")
    originals = {path: subprocess.check_output(["git", "show", "HEAD:" + path], cwd=source)
                 for path in PINS}
    expected_outputs = patched_sources(originals)
    if make_patch(originals, expected_outputs) != PATCH.read_bytes():
        raise ValueError("reviewed patch is not generated by the pinned transformation")
    if receipt["patched_sources"] != {path: sha(body) for path, body in expected_outputs.items()}:
        raise ValueError("preparation receipt does not describe the reviewed transformation")
    for path, body in expected_outputs.items():
        if (source / path).read_bytes() != body:
            raise ValueError("patched input changed: " + path)
    subprocess.run(["git", "apply", "--reverse", "--check", str(PATCH)], cwd=source,
                   check=True, capture_output=True)
    return receipt


def build(source: Path, out: Path, *, cpu: int) -> dict:
    prepared = verify_checkout(source)
    out = _external_new(out)
    out.mkdir(parents=True)
    compiler = subprocess.check_output(["g++", "--version"], text=True).splitlines()[0]
    # Object and binary paths belong to this new attempt. make does not track
    # flag changes, so reusing upstream app/tmp would not establish a rebuild.
    command = _run_owned(["make", "-C", "app", "-j1", "BUILDDIR=" + str(out / "objects"),
                          "BINARY_PATH=" + str(out), "NATIVE=-march=x86-64"], cwd=source.resolve(),
                         log=out / "build.log", timeout=600, cpu=cpu)
    binary = out / "fastchess"
    receipt = {"complete": True, "upstream_commit": PIN,
               "patch_sha256": prepared["patch_sha256"], "compiler": compiler,
               "binary": str(binary), "binary_sha256": sha(binary.read_bytes()),
               "command": command, "evidence_scope": "build only; no games or engine qualification"}
    (out / "build.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


@dataclass(frozen=True)
class EngineCommand:
    identity: str
    argv: tuple[str, ...]

    def __post_init__(self):
        if not self.identity or not self.argv or not Path(self.argv[0]).is_absolute():
            raise ValueError("an engine identity and absolute executable are required")
        if any(char in self.identity for char in "\x00\r\n"):
            raise ValueError("invalid engine identity")
        if any("\x00" in part or "\n" in part for part in self.argv):
            raise ValueError("invalid command component")


def single_game_argv(binary: Path, white: EngineCommand, black: EngineCommand, *,
                     opening_pgn: Path, opening_start: int, out: Path) -> list[str]:
    """opening_start is Fastchess's one-based PGN index; order sets actual colour."""
    if white.identity == black.identity or opening_start < 1:
        raise ValueError("distinct players and a positive one-based opening index required")
    if not all(path.is_absolute() for path in (binary, opening_pgn, out)):
        raise ValueError("absolute league paths required")
    argv = [str(binary), "-tournament", "roundrobin", "-concurrency", "1", "-rounds", "1",
            "-games", "1", "-noswap", "-startup-ms", "60000", "-ucinewgame-ms", "60000",
            "-ping-ms", "60000"]
    for engine in (white, black):
        argv += ["-engine", "name=" + engine.identity, "cmd=" + shlex.quote(engine.argv[0])]
        if len(engine.argv) > 1:
            argv += ["args=" + shlex.join(engine.argv[1:])]
    # Fastchess applies advertised UCI options after uciok; an unknown or
    # invalid Ponder option produces a warning and does not stop the game.
    # This request alone cannot prove what the engine does off turn.
    argv += ["-each", "tc=30:00+3", "timemargin=0", "restart=on", "option.Ponder=false", "-openings",
             "file=" + str(opening_pgn), "format=pgn", "order=sequential", "start=" + str(opening_start),
             "-log", "file=" + str(out / "raw.log"), "level=trace", "engine=true", "realtime=true",
             "compress=false", "append=false", "-pgnout", "file=" + str(out / "game.pgn"),
             "notation=uci", "timeleft=true", "latency=true", "nodes=true", "min=false", "append=false"]
    return argv


def ponder_uci_evidence(received_lines):
    """Describe engine-received commands, without asserting engine behavior.

    The caller owns provenance/completeness of the input trace. A sent option
    has no UCI acknowledgement and no observed go-ponder command alone cannot
    establish whether a running engine searches between turns.
    """
    if not isinstance(received_lines, (tuple, list)) or any(
            not isinstance(line, str) or any(char in line for char in "\x00\r\n")
            for line in received_lines):
        raise ValueError("a sequence of individual received UCI lines is required")
    commands = [line.casefold().split() for line in received_lines]
    set_false = sum(tokens == ["setoption", "name", "ponder", "value", "false"]
                    for tokens in commands)
    ponder_go = sum(bool(tokens) and tokens[0] == "go" and "ponder" in tokens[1:]
                    for tokens in commands)
    return {"setoption_ponder_false_received": set_false,
            "go_ponder_received": ponder_go,
            "actual_off_turn_search": None,
            "tcec_ponder_compliance": None,
            "scope": "caller-supplied engine input trace; no engine-behavior or complete-trace claim"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--out", type=Path, required=True)
    prep.add_argument("--write-reviewed-patch", action="store_true")
    compile_parser = sub.add_parser("build")
    compile_parser.add_argument("--source", type=Path, required=True)
    compile_parser.add_argument("--out", type=Path, required=True)
    compile_parser.add_argument("--cpu", type=int, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare_checkout(args.out, write_patch=args.write_reviewed_patch)
    else:
        result = build(args.source, args.out, cpu=args.cpu)
    print(json.dumps({key: value for key, value in result.items() if key != "commands"}, indent=2))


if __name__ == "__main__":
    main()
