#!/usr/bin/env python3
"""Narrow physical proof for the two admitted, freshly rebuilt TinyD own ELFs.

This file and engines/tests/chess_oracle.py are the entire validator source
closure. Mapping checks adapt the admitted-image helpers from the tracked
experiments/tiny-d-loader/test_runtime.py. No historical receipt, generated
helper, broad fault suite, compiler, or network service is used at runtime.

/proc/PID/exe is the own-loader ELF, while restored RX is the native image.
The two identities are deliberately pinned and checked separately.
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
    'completion_fences': 'next go, position, quit, EOF wait for result-before-completed epoch',
}
EXPECTED = {'scalar-shipping': {'bytes': 7478, 'sha256': 'd4f2ba718c5e9391708c86468416338f78b6134d1f017267c6c34add187381f2', 'native_bytes': 8124, 'native_sha256': '199da6e1e1a94c97fe853e0ff3d89b52e2057a55592052e7fbe5500147e4aeec', 'audit_bytes': 7501, 'audit_sha256': '2d509965f30de9151b4e957e8a805b35f716ac7461960497b01c69639d8d815d', 'entry': 4202061, 'layout': {'bss_base': 4202496, 'bss_pages': 176128, 'bss_size': 175092, 'entry': 4202061, 'guard_base': 4190208, 'image_base': 4194304, 'image_pages': 8192, 'image_size': 8124, 'reserve_size': 192512, 'section_count': 0, 'section_names': 0, 'section_offset': 0, 'section_size': 0, 'segments': [{'align': 4096, 'filesz': 8124, 'flags': 5, 'memsz': 8124, 'offset': 0, 'paddr': 4194304, 'type': 1, 'vaddr': 4194304}, {'align': 4096, 'filesz': 0, 'flags': 6, 'memsz': 175092, 'offset': 0, 'paddr': 4202496, 'type': 1, 'vaddr': 4202496}, {'align': 8, 'filesz': 0, 'flags': 6, 'memsz': 0, 'offset': 0, 'paddr': 0, 'type': 1685382481, 'vaddr': 0}], 'upper_guard': 4378624}}, 'hq-shipping': {'bytes': 7718, 'sha256': '3bb8a6a97a27a77508848ab9bd388a4802e07f8d8ff0e37b536176423aa7028f', 'native_bytes': 8512, 'native_sha256': '3f4269dc5c0d72c0b43bc73c6a11afdab5844836e12e7c31d60dde08c8ae2806', 'audit_bytes': 7741, 'audit_sha256': '3253d027b6132e42e47e963e011dd230384aa96dae5c4b3f3f13a9ec8ea68a1a', 'entry': 4202367, 'layout': {'bss_base': 4206592, 'bss_pages': 176128, 'bss_size': 175092, 'entry': 4202367, 'guard_base': 4190208, 'image_base': 4194304, 'image_pages': 12288, 'image_size': 8512, 'reserve_size': 196608, 'section_count': 0, 'section_names': 0, 'section_offset': 0, 'section_size': 0, 'segments': [{'align': 4096, 'filesz': 8512, 'flags': 5, 'memsz': 8512, 'offset': 0, 'paddr': 4194304, 'type': 1, 'vaddr': 4194304}, {'align': 4096, 'filesz': 0, 'flags': 6, 'memsz': 175092, 'offset': 0, 'paddr': 4206592, 'type': 1, 'vaddr': 4206592}, {'align': 8, 'filesz': 0, 'flags': 6, 'memsz': 0, 'offset': 0, 'paddr': 0, 'type': 1685382481, 'vaddr': 0}], 'upper_guard': 4382720}}}
OWNED = set()


def terminated(signum, frame):
    raise TimeoutError("validator received SIGTERM; preserving partial evidence and cleaning owned groups")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


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


def inspect(pid, layout, native_sha, executable_sha, *, initial=False):
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
        require(len(image) == layout["image_size"] and sha(image) == native_sha, "actual restored RX differs from pinned native")
        padding_length = layout["image_pages"] - layout["image_size"]
        padding = os.pread(memory.fileno(), padding_length, layout["image_base"] + layout["image_size"])
        require(len(padding) == padding_length and not any(padding), "RX page padding not zero")
        if initial:
            bss = os.pread(memory.fileno(), layout["bss_pages"], layout["bss_base"])
            require(len(bss) == layout["bss_pages"] and not any(bss), "pre-entry BSS/padding not zero")
    return {"own_executable_sha256": actual_exe, "mapped_native_sha256": sha(image),
            "rx_matches_native": True, "rx_padding_zero": True,
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


def checkpoint(candidate, layout, native_sha, directory, budget, evidence):
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
        evidence.update(inspect(owned.process.pid, layout, native_sha, audit["sha256"], initial=True))
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


def production(candidate, layout, native_sha, directory, budget, oracle, shutdown, row):
    path = Path(candidate["path"])
    require(sha(path.read_bytes()) == candidate["sha256"], "own ELF changed before launch")
    owned = Owned(path, directory, budget)
    row.update({"shutdown": shutdown, "passed": False, "searches": []})
    try:
        tids = stable_startup(owned)
        row["startup_tids"] = tids
        row["before_uci"] = inspect(owned.process.pid, layout, native_sha, candidate["sha256"])
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
                row["during_active_search"] = inspect(owned.process.pid, layout, native_sha, candidate["sha256"])
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
    out.mkdir(parents=True)
    report = {"complete": False, "scope": "Fresh admitted-image physical RX/permissions and narrow shipping runtime proof; no broad fault-suite rerun or 4k eligibility claim",
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
        require(build.get("complete") is True, "build is incomplete")
        require(not build.get("failure") and build["shipping_protocol"] == SHIPPING_PROTOCOL, "build protocol declaration differs or build failed")
        report["shipping_protocol"] = SHIPPING_PROTOCOL
        report["policy_scope"] = "declaration/exact-image binding; this run checks clocked play and quit/EOF, not ignored controls or default-budget arithmetic"
        require(len(build["engines"]) == 2 and {e["id"] for e in build["engines"]} == set(EXPECTED), "expected exactly the scalar/HQ admitted images")
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
            expected, layout = EXPECTED[engine["id"]], engine["layout"]
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
            require(len(engine["candidates"]) == 1, "expected exactly one selected fixed-codec own ELF")
            candidate = dict(engine["candidates"][0])
            candidate["path"] = str(resolve(candidate["path"], build_path.parent))
            require(candidate.get("codec", "fixed") == "fixed" and candidate["sha256"] == expected["sha256"] and candidate["bytes"] == expected["bytes"], "selected own ELF admission differs")
            program = Path(candidate["path"])
            require(program.stat().st_size == expected["bytes"] and sha(program.read_bytes()) == expected["sha256"], "actual own ELF file differs")
            if candidate.get("audit"):
                candidate["audit"] = dict(candidate["audit"])
                candidate["audit"]["path"] = str(resolve(candidate["audit"]["path"], build_path.parent))
            require(candidate.get("audit") and candidate["audit"]["bytes"] == expected["audit_bytes"]
                    and candidate["audit"]["sha256"] == expected["audit_sha256"], "selected finite CHECKPOINT identity differs")
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
            checkpoint(candidate, layout, expected["native_sha256"], out / engine["id"] / "checkpoint", budget, row["pre_entry"])
            for shutdown in ("quit", "EOF"):
                phase = engine["id"] + "/active-" + shutdown
                case = {}
                row["production"].append(case)
                production(candidate, layout, expected["native_sha256"], out / engine["id"] / shutdown, budget, oracle, shutdown, case)
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
