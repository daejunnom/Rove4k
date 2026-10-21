#!/usr/bin/env python3
"""Narrow physical proof for the two admitted, freshly rebuilt TinyD own ELFs.

This file and engines/tests/chess_oracle.py are the entire validator source
closure. Mapping checks adapt the admitted-image helpers from the tracked
experiments/tiny-d-loader/test_runtime.py. No historical receipt, generated
helper, broad fault suite, compiler, or network service is used at runtime.

/proc/PID/exe is the own-loader ELF. V2 RX is the compiled native ELF;
V3 RX is zero232 plus that ELF's unchanged body at its original offsets.
Compiled native, full restored RX and own-ELF identities are checked separately.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
ORACLE_LF_SHA = "aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8"
SHIPPING_PROTOCOL = {
    'id': 'finite-minimum-v1', 'identification': False,
    'stop': 'consume', 'ucinewgame': 'consume', 'infinite': 'consume',
    'default_budget_ms': 1000, 'own_clock_formula': 'unchanged',
    'hard_wall_cap': False,
    'completion_fences': 'next go, position, quit, EOF acquire pending==0 after result output',
}
V2_CODEC = 'rove4k-context-h24-base10-fixed21-replay-zero4-v2'
CODEC = 'rove4k-context-h24-base10-fixed21-body232-zero4-v3'
EXECUTION_ISA = 'linux-x86_64-sse4.2-cx16-crc32b-v1'
EXPECTED_V2 = {'scalar-shipping': {'bytes': 5908, 'sha256': 'd7a0b5fa3f5dcf96368630283f756fee4bf04034b58cd970700e6197c4471490', 'native_bytes': 7612, 'native_sha256': '662b0eb10046d0b0ab105bba0f793371bb869eb61aa4419c8c2fa95f7d39c32d', 'audit_bytes': 5931, 'audit_sha256': '46ebc96c8e0fdd46a6f5b93668fd3b82b4ee746b9e44513d1532a3fc48963e90', 'entry': 4201533, 'layout': {'image_base': 4194304, 'image_size': 7612, 'image_pages': 8192, 'entry': 4201533, 'bss_base': 4202496, 'bss_size': 175092, 'bss_pages': 176128, 'guard_base': 4190208, 'upper_guard': 4378624, 'reserve_size': 192512, 'section_offset': 0, 'section_size': 0, 'section_count': 0, 'section_names': 0, 'segments': [{'type': 1, 'flags': 5, 'offset': 0, 'vaddr': 4194304, 'paddr': 4194304, 'filesz': 7612, 'memsz': 7612, 'align': 4096}, {'type': 1, 'flags': 6, 'offset': 0, 'vaddr': 4202496, 'paddr': 4202496, 'filesz': 0, 'memsz': 175092, 'align': 4096}, {'type': 1685382481, 'flags': 6, 'offset': 0, 'vaddr': 0, 'paddr': 0, 'filesz': 0, 'memsz': 0, 'align': 8}]}}, 'hq-shipping': {'bytes': 6111, 'sha256': '9e4167c6b4bba2978d1b3685901bef89fd90ff9929f7991f8c39cbaa94819a62', 'native_bytes': 8000, 'native_sha256': '3c662941aa11af8521d3c601322e9aa38405a3bfbeb9332d55008907217a4b2e', 'audit_bytes': 6134, 'audit_sha256': '50dd8d89b10b2fc7b09b11f5f21215f7e8035d1edac6948dd6b7ff0ef68153f9', 'entry': 4201846, 'layout': {'image_base': 4194304, 'image_size': 8000, 'image_pages': 8192, 'entry': 4201846, 'bss_base': 4202496, 'bss_size': 175064, 'bss_pages': 176128, 'guard_base': 4190208, 'upper_guard': 4378624, 'reserve_size': 192512, 'section_offset': 0, 'section_size': 0, 'section_count': 0, 'section_names': 0, 'segments': [{'type': 1, 'flags': 5, 'offset': 0, 'vaddr': 4194304, 'paddr': 4194304, 'filesz': 8000, 'memsz': 8000, 'align': 4096}, {'type': 1, 'flags': 6, 'offset': 0, 'vaddr': 4202496, 'paddr': 4202496, 'filesz': 0, 'memsz': 175064, 'align': 4096}, {'type': 1685382481, 'flags': 6, 'offset': 0, 'vaddr': 0, 'paddr': 0, 'filesz': 0, 'memsz': 0, 'align': 8}]}}}
# V2 retains its full-native RX comparison and exact historical admissions.
# V3 has a separate full restored-image hash, including every zero prefix byte.
EXPECTED_BODY = {
    'scalar-shipping': dict(EXPECTED_V2['scalar-shipping'], bytes=5836,
        sha256='e726848454c05ca42eefcc65877203f5a2812d51e9902e169c01859bd06c72f9',
        audit_bytes=5859, audit_sha256='419c47835f0db582e86a4a1d5c4b45876bb22768ab2152d6b159897a2eea180f',
        restored_image_sha256='07b6754aabefd1171fbdfae84ce30e1b50cff8a527a124d99998e18170f0d07c'),
    'hq-shipping': dict(EXPECTED_V2['hq-shipping'], bytes=6037,
        sha256='b7cf68ec898e6b550c89ebb2dd94fc9f7c1f215b3c24237096ea1c55f54a0262',
        audit_bytes=6060, audit_sha256='6f2e808246e648f5c9fc65dd9fc103311375a87e4581946a89efacc70edb532e',
        restored_image_sha256='f2b4804631d293ccb4742ed8718869a29736bfb46f840044659e44c8d0f95d4b'),
}
OWNED = set()


def terminated(signum, frame):
    raise TimeoutError("validator received SIGTERM; preserving partial evidence and cleaning owned groups")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def execution_profile():
    require(os.uname().machine == "x86_64", "x86-64 ISA profile required")
    available = sorted(os.sched_getaffinity(0))
    flags = {}
    for block in Path("/proc/cpuinfo").read_text().strip().split("\n\n"):
        fields = {k.strip(): v.strip() for line in block.splitlines() if ":" in line
                  for k, v in [line.split(":", 1)]}
        if "processor" in fields:
            flags[int(fields["processor"])] = fields.get("flags", "").split()
    require(available and all("sse4_2" in flags.get(cpu, []) for cpu in available),
            "SSE4.2 CRC32 must be exposed on every available CPU")
    require(available and all("cx16" in flags.get(cpu, []) for cpu in available),
            "CX16 must be exposed on every available CPU")
    return {"profile": EXECUTION_ISA, "available_processors": available,
            "sse4_2_all_available": True, "cx16_all_available": True, "source": "/proc/cpuinfo and sched_getaffinity",
            "scope": "local exposed feature admission; generic compatibility and current tournament CPU unverified"}


class Budget:
    def __init__(self, seconds):
        self.end = time.monotonic() + seconds

    def left(self, seconds):
        result = min(seconds, self.end - time.monotonic())
        if result <= 0:
            raise TimeoutError("aggregate validator deadline expired")
        return result


def resolve(path, base):
    path = Path(path)
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def mapping(pid):
    result = []
    for line in Path(f"/proc/{pid}/maps").read_text().splitlines():
        span, permission, *_ = line.split()
        first, last = (int(value, 16) for value in span.split("-"))
        result.append({"start": first, "end": last, "permissions": permission, "line": line})
    require(not any("w" in m["permissions"] and "x" in m["permissions"] for m in result), "writable executable mapping")
    stacks = [m for m in result if "[stack]" in m["line"]]
    require(len(stacks) == 1 and "x" not in stacks[0]["permissions"], "missing/executable process stack")
    return result


def covers(items, begin, length, permission):
    require(length > 0, "invalid mapping length")
    end, position = begin + length, begin
    for item in items:
        if item["end"] <= position:
            continue
        if item["start"] > position:
            break
        require(item["permissions"][:3] == permission, "wrong mapping permission: " + item["line"])
        position = min(end, item["end"])
        if position == end:
            return
    raise AssertionError("memory range absent/incomplete")


def inspect(pid, layout, native_sha, executable_sha, *, initial=False, restored_sha=None):
    items = mapping(pid)
    covers(items, layout["image_base"], layout["image_pages"], "r-x")
    covers(items, layout["bss_base"], layout["bss_pages"], "rw-")
    covers(items, layout["guard_base"], 4096, "---")
    covers(items, layout["upper_guard"], 4096, "---")
    worker_guards = []
    if not initial:
        for item in items:
            if item["permissions"][:3] == "---" and not (
                    item["start"] <= layout["guard_base"] < item["end"] or
                    item["start"] <= layout["upper_guard"] < item["end"]):
                require(item["end"] - item["start"] == 4096, "worker stack guard size differs")
                covers(items, item["end"], 1048576, "rw-")
                worker_guards.append({"guard_base": item["start"], "stack_base": item["end"], "stack_bytes": 1048576})
        require(len(worker_guards) == 2, "expected two guarded non-executable worker stacks")
    actual_exe = sha(Path(f"/proc/{pid}/exe").read_bytes())
    require(actual_exe == executable_sha, "/proc/PID/exe differs from admitted own ELF")
    with open(f"/proc/{pid}/mem", "rb", buffering=0) as memory:
        image = os.pread(memory.fileno(), layout["image_size"], layout["image_base"])
        require(len(image) == layout["image_size"] and sha(image) == (restored_sha or native_sha), "actual full restored RX differs from pinned image")
        padding_length = layout["image_pages"] - layout["image_size"]
        padding = os.pread(memory.fileno(), padding_length, layout["image_base"] + layout["image_size"])
        require(len(padding) == padding_length and not any(padding), "RX page padding not zero")
        if initial:
            bss = os.pread(memory.fileno(), layout["bss_pages"], layout["bss_base"])
            require(len(bss) == layout["bss_pages"] and not any(bss), "pre-entry BSS/padding not zero")
    return {"own_executable_sha256": actual_exe, "compiled_native_sha256": native_sha, "mapped_image_sha256": sha(image),
            "mapped_native_sha256": sha(image) if restored_sha is None else None,
            "rx_matches_native": sha(image) == native_sha, "rx_matches_restored_image": True, "rx_padding_zero": True,
            "pre_entry_bss_padding_zero": True if initial else None,
            "no_writable_executable_mapping": True, "nonexec_process_stack": True,
            "lower_upper_guards": True, "worker_guarded_nonexec_stacks": worker_guards, "maps": items}


def tasks(pid):
    result = {}
    for path in Path(f"/proc/{pid}/task").iterdir():
        fields = (path / "stat").read_text().rsplit(")", 1)[1].split()
        children = (path / "children").read_text().split()
        require(not children, f"task {path.name} has child processes: {children}")
        result[int(path.name)] = {"state": fields[0], "cpu_ticks": int(fields[11]) + int(fields[12])}
    descriptors = sorted(p.name for p in Path(f"/proc/{pid}/fd").iterdir())
    require(descriptors == ["0", "1", "2"], f"non-stdio engine descriptors: {descriptors}")
    return result


class Reader:
    def __init__(self, pipe, name):
        self.pipe, self.data, self.error = pipe, bytearray(), None
        self.condition, self.done = threading.Condition(), False
        self.thread = threading.Thread(target=self.run, name=name, daemon=False)
        self.thread.start()

    def run(self):
        try:
            while True:
                chunk = os.read(self.pipe.fileno(), 4096)
                if not chunk:
                    break
                with self.condition:
                    self.data.extend(chunk)
                    require(len(self.data) <= 1024 * 1024, "output exceeded 1 MiB")
                    self.condition.notify_all()
        except BaseException as exc:
            self.error = repr(exc)
        finally:
            with self.condition:
                self.done = True
                self.condition.notify_all()

    def bytes(self):
        with self.condition:
            return bytes(self.data)

    def until(self, predicate, budget, seconds=10):
        deadline = time.monotonic() + budget.left(seconds)
        with self.condition:
            while not predicate(bytes(self.data)):
                require(not self.error, "reader failure: " + str(self.error))
                require(not self.done, "unexpected stdout EOF: " + repr(bytes(self.data)))
                remaining = min(deadline - time.monotonic(), budget.left(seconds))
                if remaining <= 0:
                    raise TimeoutError("engine response deadline: " + repr(bytes(self.data)))
                self.condition.wait(min(remaining, .1))


class Owned:
    def __init__(self, path, directory, budget):
        self.directory, self.budget, self.sent, self.finished = directory, budget, bytearray(), False
        self.stdout, self.stderr, self.cleaned = None, None, None
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        try:
            # Restore the exact inherited signal mask in the child before exec.
            # TERM remains blocked in this parent until its handle AND readers
            # are registered; the outer finally can clean even if unblocking
            # immediately delivers a pending signal before __init__ returns.
            self.process = subprocess.Popen([str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, start_new_session=True, bufsize=0,
                                            preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, inherited))
            OWNED.add(self)
            self.stdout = Reader(self.process.stdout, "tiny-entry-d-stdout")
            self.stderr = Reader(self.process.stderr, "tiny-entry-d-stderr")
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)

    def send(self, data):
        self.budget.left(10)
        self.sent.extend(data)
        self.process.stdin.write(data)
        self.process.stdin.flush()

    def close_input(self):
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()

    def wait_line(self, line, count=1):
        self.stdout.until(lambda data: data.splitlines().count(line) >= count, self.budget)

    def wait_best(self, count):
        self.stdout.until(lambda data: sum(s.startswith(b"bestmove ") for s in data.splitlines()) >= count, self.budget)

    def finish(self):
        self.process.wait(timeout=self.budget.left(10))
        for reader in (self.stdout, self.stderr):
            reader.thread.join(timeout=self.budget.left(3))
            require(not reader.thread.is_alive() and reader.done and not reader.error, "output reader did not join cleanly")
        require(self.process.returncode == 0, f"engine exit {self.process.returncode}")
        require(not self.stderr.bytes(), "engine stderr: " + repr(self.stderr.bytes()))
        self.finished = True
        return {"returncode": 0, "readers_joined": True, "stdout_eof": self.stdout.done,
                "stderr_eof": self.stderr.done, "forced_cleanup": False}

    def cleanup(self):
        if self.cleaned is not None:
            return self.cleaned
        forced = False
        errors = []
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
            forced = True
        except ProcessLookupError:
            pass
        try:
            self.close_input()
        except (BrokenPipeError, OSError):
            pass
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            errors.append("owned leader did not reap after SIGKILL")
        readers = [r for r in (self.stdout, self.stderr) if r is not None]
        for reader in readers:
            reader.thread.join(timeout=3)
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / "stdin.bin").write_bytes(self.sent)
        (self.directory / "stdout.bin").write_bytes(self.stdout.bytes() if self.stdout else b"")
        (self.directory / "stderr.bin").write_bytes(self.stderr.bytes() if self.stderr else b"")
        joined = not any(r.thread.is_alive() for r in readers)
        if not joined:
            errors.append("cleanup left output readers alive")
        else:
            self.process.stdout.close()
            self.process.stderr.close()
        try:
            os.killpg(self.process.pid, 0)
        except ProcessLookupError:
            group_absent = True
        else:
            group_absent = False
        if not group_absent:
            errors.append("owned process group remains")
        self.cleaned = {"owned_group_absent": group_absent, "readers_joined": joined,
                        "forced_cleanup": forced, "settled_before_cleanup": self.finished, "errors": errors}
        OWNED.discard(self)
        return self.cleaned


def stable_startup(owned):
    deadline = time.monotonic() + owned.budget.left(10)
    while time.monotonic() < deadline:
        require(owned.process.poll() is None, "engine exited during startup")
        observed = tasks(owned.process.pid)
        if len(observed) == 3:
            time.sleep(min(.05, owned.budget.left(.05)))
            again = tasks(owned.process.pid)
            if set(again) == set(observed):
                return sorted(observed)
        time.sleep(min(.005, owned.budget.left(.005)))
    raise TimeoutError("exact three persistent startup TIDs not observed")


def physical_active(owned, expected_tids, before):
    started, samples = time.monotonic(), []
    deadline = started + owned.budget.left(3)
    pid = owned.process.pid
    while time.monotonic() < deadline:
        current = tasks(pid)
        require(sorted(current) == expected_tids, "startup TIDs replaced during active search")
        workers = [tid for tid in current if tid != pid]
        delta = sum(current[t]["cpu_ticks"] - before[t]["cpu_ticks"] for t in workers)
        samples.append({"elapsed_seconds": time.monotonic() - started, "tasks": current, "worker_cpu_tick_delta": delta})
        if time.monotonic() - started >= .025 and current[pid]["state"] == "S" and all(current[t]["state"] == "R" for t in workers) and delta > 0:
            return {"main_state": "S", "worker_states": ["R", "R"], "worker_cpu_tick_delta": delta,
                    "startup_tids_persistent": True, "observed_before_shutdown": True, "samples": samples}
        time.sleep(min(.005, owned.budget.left(.005)))
    raise AssertionError("physical active state was not established within 3 seconds: " + repr(samples[-5:]))


def checkpoint(candidate, layout, native_sha, directory, budget, evidence, *, restored_sha=None):
    audit = candidate.get("audit")
    require(audit and "path" in audit and "sha256" in audit, "build must include the admitted CHECKPOINT image")
    path = Path(audit["path"])
    require(sha(path.read_bytes()) == audit["sha256"], "audit whole-file hash differs")
    if "bytes" in audit:
        require(path.stat().st_size == audit["bytes"], "audit size differs")
    owned = Owned(path, directory, budget)
    try:
        deadline = time.monotonic() + budget.left(10)
        while time.monotonic() < deadline:
            pid, status = os.waitpid(owned.process.pid, os.WNOHANG | os.WUNTRACED)
            if pid:
                require(os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGSTOP, "audit did not stop at pre-entry checkpoint")
                break
            require(owned.process.poll() is None, "audit exited before pre-entry checkpoint")
            time.sleep(min(.005, budget.left(.005)))
        else:
            raise TimeoutError("pre-entry CHECKPOINT deadline")
        evidence.update(inspect(owned.process.pid, layout, native_sha, audit["sha256"], initial=True, restored_sha=restored_sha))
        os.kill(owned.process.pid, signal.SIGCONT)
        owned.send(b"uci\nisready\nquit\n")
        owned.close_input()
        evidence["settled"] = owned.finish()
        lines = owned.stdout.bytes().splitlines()
        require(lines.count(b"uciok") == 1 and lines.count(b"readyok") == 1 and not any(s.startswith(b"bestmove") for s in lines), "audit resume protocol differs")
        evidence.update({"audit_sha256": audit["sha256"], "resumed_original_entry": True})
        return evidence
    finally:
        evidence["cleanup"] = owned.cleanup()
        if owned.finished:
            require(not evidence["cleanup"]["forced_cleanup"] and not evidence["cleanup"]["errors"], "audit cleanup required intervention")


def production(candidate, layout, native_sha, directory, budget, oracle, shutdown, row, *, restored_sha=None):
    path = Path(candidate["path"])
    require(sha(path.read_bytes()) == candidate["sha256"], "own ELF changed before launch")
    owned = Owned(path, directory, budget)
    row.update({"shutdown": shutdown, "passed": False, "searches": []})
    try:
        tids = stable_startup(owned)
        row["startup_tids"] = tids
        row["before_uci"] = inspect(owned.process.pid, layout, native_sha, candidate["sha256"], restored_sha=restored_sha)
        owned.send(b"uci\nisready\n")
        owned.wait_line(b"uciok")
        owned.wait_line(b"readyok")
        positions = ([], ["e2e4"], ["d2d4", "g8f6", "c2c4"])
        expected_legal = []
        for index, history in enumerate(positions):
            board = oracle.Board.from_fen()
            for name in history:
                board = board.play(name)
            legal = {str(m) for m in board.legal_moves()}
            require(bool(legal), "test position has no legal witness")
            expected_legal.append(legal)
            position = "position startpos" + (" moves " + " ".join(history) if history else "") + "\n"
            before = tasks(owned.process.pid)
            require(sorted(before) == tids, "startup TIDs replaced before search")
            owned.send(position.encode("ascii"))
            clock = 600000 if index == 2 else 3000
            owned.send(f"go wtime {clock} btime {clock} winc 0 binc 0\n".encode("ascii"))
            if index < 2:
                owned.wait_best(index + 1)
                lines = [s for s in owned.stdout.bytes().splitlines() if s.startswith(b"bestmove ")]
                require(len(lines) == index + 1, "extra result before next go")
                match = re.fullmatch(rb"bestmove ([a-h][1-8][a-h][1-8][nbrq]?)", lines[-1])
                require(match and match.group(1).decode() in legal, "clocked result is illegal")
                owned.send(b"isready\n")
                owned.wait_line(b"readyok", index + 2)
                require(sorted(tasks(owned.process.pid)) == tids, "startup TIDs replaced after search")
                row["searches"].append({"side": "white" if board.turn else "black", "history": history, "move": match.group(1).decode(), "legal": True})
            else:
                row["active_before_shutdown"] = physical_active(owned, tids, before)
                require(sum(s.startswith(b"bestmove ") for s in owned.stdout.bytes().splitlines()) == 2, "active search had already settled")
                row["during_active_search"] = inspect(owned.process.pid, layout, native_sha, candidate["sha256"], restored_sha=restored_sha)
                row["active_position"] = {"history": history, "side": "black"}
        if shutdown == "quit":
            owned.send(b"quit\n")
        owned.close_input()
        row["settled"] = owned.finish()
        stdout = owned.stdout.bytes()
        require(stdout.endswith(b"\n"), "trailing incomplete output")
        lines = stdout.splitlines()
        results = [s for s in lines if s.startswith(b"bestmove")]
        require(len(results) == 3 and lines.count(b"uciok") == 1 and lines.count(b"readyok") == 3, "settled command/result counts differ")
        require(not any(s.startswith(b"id ") or s.startswith(b"option ") for s in lines), "finite shipping emitted optional interface")
        for line, legal in zip(results, expected_legal):
            match = re.fullmatch(rb"bestmove ([a-h][1-8][a-h][1-8][nbrq]?)", line)
            require(match and match.group(1).decode() in legal, "settled result is malformed/illegal")
        row["active_result"] = results[-1].decode().split()[1]
        row.update({"passed": True, "startup_tids_persistent": True, "only_stdio_descriptors": True,
                    "no_children_observed": True, "exactly_one_legal_result_per_go": True,
                    "settled_stdout_sha256": sha(stdout), "readers_joined": True})
        return row
    finally:
        cleanup = owned.cleanup()
        row["cleanup"] = cleanup
        if row["passed"]:
            require(not cleanup["forced_cleanup"] and not cleanup["errors"] and cleanup["settled_before_cleanup"], "production cleanup required intervention")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--oracle", type=Path, default=HERE.parents[1] / "tests" / "chess_oracle.py")
    parser.add_argument("--budget", type=int, default=120)
    args = parser.parse_args()
    out, build_path = args.out.resolve(), args.build.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p / ".git").exists() for p in (out, *out.parents)), "--out must be new, absolute and outside Git")
    require(30 <= args.budget <= 300, "budget must be 30..300 seconds")
    require(sys.platform.startswith("linux"), "Linux /proc and parent memory access required")
    isa_observation = execution_profile()
    out.mkdir(parents=True)
    report = {"complete": False, "scope": "Fresh exact context own-ELF pre-entry RX/BSS/permissions and narrow shipping runtime proof; no decoder-fault suite, RIE/ptrace mutation or 4k eligibility claim",
              "execution_isa": EXECUTION_ISA, "ISA_observation": isa_observation,
              "build_sha256": None, "validator_sha256": None,
              "oracle_sha256": None, "oracle_lf_sha256": ORACLE_LF_SHA,
              "results": [], "failures": [], "interrupted_constructors_cleanup": []}
    budget, started, phase = Budget(args.budget), time.monotonic(), "input validation"
    prior_term = signal.signal(signal.SIGTERM, terminated)
    try:
        validator_bytes = Path(__file__).read_bytes()
        report["validator_sha256"] = sha(validator_bytes)
        build_bytes = build_path.read_bytes()
        report["build_sha256"] = sha(build_bytes)
        oracle_bytes = args.oracle.read_bytes()
        report["oracle_sha256"] = sha(oracle_bytes)
        require(sha(oracle_bytes.replace(b"\r\n", b"\n")) == ORACLE_LF_SHA, "independent oracle LF-normalized source differs")
        build = json.loads(build_bytes)
        codec = build.get('engines', [{}])[0].get('candidates', [{}])[0].get('codec')
        require(codec in (V2_CODEC, CODEC), "unknown packet/image class")
        expected_forms = EXPECTED_V2 if codec == V2_CODEC else EXPECTED_BODY
        report['codec'] = codec
        require(all(e["audit_bytes"] is not None and e["audit_sha256"] is not None for e in expected_forms.values()), "context audit literals require explicit discovery and admission")
        require(build.get("complete") is True, "build is incomplete")
        require(build.get("execution_isa") == EXECUTION_ISA, "build execution ISA declaration differs")
        require(not build.get("failure") and build["shipping_protocol"] == SHIPPING_PROTOCOL, "build protocol declaration differs or build failed")
        report["shipping_protocol"] = SHIPPING_PROTOCOL
        report["policy_scope"] = "declaration/exact-image binding; this run checks clocked play and quit/EOF, not ignored controls or default-budget arithmetic"
        require(len(build["engines"]) == 2 and {e["id"] for e in build["engines"]} == set(expected_forms), "expected exactly the scalar/HQ admitted images")
        recipe = out / "recipe"
        recipe.mkdir()
        (recipe / "verify.py").write_bytes(validator_bytes)
        (recipe / "chess_oracle.py").write_bytes(oracle_bytes)
        (recipe / "build.json").write_bytes(build_bytes)
        spec = importlib.util.spec_from_file_location("tiny_entry_d_oracle", recipe / "chess_oracle.py")
        oracle = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = oracle
        spec.loader.exec_module(oracle)
        for engine in build["engines"]:
            phase = engine["id"] + "/input-validation"
            expected, layout = expected_forms[engine["id"]], engine["layout"]
            require(engine["input_sha256"] == expected["native_sha256"] and engine["input_bytes"] == expected["native_bytes"], "native image admission differs")
            native = engine.get("native") or engine.get("native_path")
            if isinstance(native, dict):
                native = native["path"]
            if native is None and engine.get("native_rebuilds"):
                native = engine["native_rebuilds"][0]["path"]
            require(native is not None, "build must record native path")
            native_path = resolve(native, build_path.parent)
            require(sha(native_path.read_bytes()) == expected["native_sha256"] and native_path.stat().st_size == expected["native_bytes"], "actual native file differs")
            require(layout["image_size"] == expected["native_bytes"] and layout["image_base"] == 0x400000, "native mapping layout differs")
            require(layout == expected["layout"], "literal identity/form layout differs")
            require(layout["image_pages"] == (layout["image_size"] + 4095) // 4096 * 4096 and layout["bss_pages"] == 176128, "native page sizing differs")
            require(layout["guard_base"] == layout["image_base"] - 4096 and layout["bss_base"] == layout["image_base"] + layout["image_pages"] and layout["upper_guard"] == layout["bss_base"] + layout["bss_pages"], "native guard/BSS layout differs")
            require(len(engine["candidates"]) == 1, "expected exactly one selected context-codec own ELF")
            candidate = dict(engine["candidates"][0])
            candidate["path"] = str(resolve(candidate["path"], build_path.parent))
            require(candidate.get("codec") == codec and candidate["sha256"] == expected["sha256"] and candidate["bytes"] == expected["bytes"], "selected own ELF admission differs")
            restored_sha = expected.get('restored_image_sha256')
            if codec == CODEC:
                image = {'format': CODEC, 'zero_prefix_bytes': 232,
                         'compiled_native_bytes': expected['native_bytes'], 'compiled_native_sha256': expected['native_sha256'],
                         'restored_image_bytes': expected['native_bytes'], 'restored_image_sha256': restored_sha}
                require(engine.get('image') == image and candidate.get('image') == image
                        and candidate['encoding']['image'] == image, 'body232 image identities differ')
                require(candidate['encoding']['decoded_bytes'] == expected['native_bytes']-232
                        and candidate['definitions']['IMAGE_SIZE'] == expected['native_bytes']
                        and candidate['definitions']['DECODE_PREFIX'] == 232, 'body232 decode extent differs')
                native_data = native_path.read_bytes()
                require(sha(bytes(232)+native_data[232:]) == restored_sha, 'body232 full restored-image literal differs')
                restored = engine['restored_image']
                require(restored['bytes'] == expected['native_bytes'] and restored['sha256'] == restored_sha
                        and sha(resolve(restored['path'], build_path.parent).read_bytes()) == restored_sha,
                        'recorded whole restored image differs')
            program = Path(candidate["path"])
            require(program.stat().st_size == expected["bytes"] and sha(program.read_bytes()) == expected["sha256"], "actual own ELF file differs")
            if candidate.get("audit"):
                candidate["audit"] = dict(candidate["audit"])
                candidate["audit"]["path"] = str(resolve(candidate["audit"]["path"], build_path.parent))
            require(candidate.get("audit") and candidate["audit"]["bytes"] == expected["audit_bytes"]
                    and candidate["audit"]["sha256"] == expected["audit_sha256"], "selected context CHECKPOINT identity differs")
            frozen = recipe / engine["id"]
            frozen.mkdir()
            (frozen / "native.elf").write_bytes(native_path.read_bytes())
            (frozen / "own.elf").write_bytes(program.read_bytes())
            if candidate.get("audit"):
                (frozen / "audit.elf").write_bytes(Path(candidate["audit"]["path"]).read_bytes())
            row = {"engine": engine["id"], "own_elf_sha256": expected["sha256"], "native_sha256": expected["native_sha256"], "production": []}
            report["results"].append(row)
            phase = engine["id"] + "/pre-entry"
            row["pre_entry"] = {}
            checkpoint(candidate, layout, expected["native_sha256"], out / engine["id"] / "checkpoint", budget, row["pre_entry"], restored_sha=restored_sha)
            for shutdown in ("quit", "EOF"):
                phase = engine["id"] + "/active-" + shutdown
                case = {}
                row["production"].append(case)
                production(candidate, layout, expected["native_sha256"], out / engine["id"] / shutdown, budget, oracle, shutdown, case, restored_sha=restored_sha)
        report["complete"] = True
    except BaseException as exc:
        report["complete"] = False
        report["failures"].append({"phase": phase, "type": type(exc).__name__, "detail": str(exc)})
    finally:
        # A TERM received during constructor unmasking can arrive before the
        # caller obtains its Owned object. This registry closes that window.
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        try:
            for owned in list(OWNED):
                try:
                    report["interrupted_constructors_cleanup"].append(owned.cleanup())
                except BaseException as exc:
                    report["failures"].append({"phase": phase + "/registered-cleanup", "type": type(exc).__name__, "detail": str(exc)})
                report["complete"] = False
            report["elapsed_seconds"] = time.monotonic() - started
            (out / "results.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        finally:
            signal.signal(signal.SIGTERM, prior_term)
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
    print(json.dumps({"complete": report["complete"], "engines": len(report["results"]), "results": str(out / "results.json"), "failures": report["failures"]}))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
