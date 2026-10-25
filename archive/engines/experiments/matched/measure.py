#!/usr/bin/env python3
"""Bounded cold-process measurements of the frozen matched C-policy E engines.

prepare validates frozen bytes without launching engines; gate runs semantic
checks without publishing clocks; measure requires a coordinated quiet window.
Only the Python standard library is required. Outputs must be outside the repo.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import statistics
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
ORACLE = ROOT / "engines/tests/chess_oracle.py"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ORACLE.parent))
from chess_oracle import Board

CASES = (
    ("start", None, ()),
    ("opening", None, ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6")),
    ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", ()),
)
MOVE = re.compile(r"^[a-h][1-8][a-h][1-8][qrbn]?$")
RUNTIME_ENV = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "TZ": "UTC"}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def cpus(value):
    result = set()
    for item in value.split(","):
        bounds = item.split("-")
        require(len(bounds) in (1, 2), "invalid CPU list")
        first, last = int(bounds[0]), int(bounds[-1])
        require(0 <= first <= last, "invalid CPU range")
        result.update(range(first, last + 1))
    require(result, "CPU list is empty")
    return sorted(result)


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def process_snapshot(pid, include_cpu):
    proc = Path("/proc") / str(pid)
    values = {}
    for line in (proc / "status").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in ("VmPeak", "VmSize", "VmHWM", "VmRSS", "VmData", "VmStk", "Threads", "Cpus_allowed_list"):
            values[key] = value.strip()
    tasks = sorted(int(path.name) for path in (proc / "task").iterdir())
    result = {"status": values, "task_ids": tasks,
              "task_affinity": {str(tid): sorted(os.sched_getaffinity(tid)) for tid in tasks}}
    if include_cpu:
        # comm can contain spaces or parentheses; fields after its final ')' start at field 3.
        tail = (proc / "stat").read_text().rsplit(")", 1)[1].split()
        result["cpu_ticks"] = {"user": int(tail[11]), "system": int(tail[12])}
    return result


def cpu_ticks(pid):
    tail = (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
    return {"user": int(tail[11]), "system": int(tail[12]), "process_start_ticks": int(tail[19])}


def frozen_manifest(path, workers):
    manifest = json.loads(path.read_text())
    require(manifest.get("contract") == "matched-c-policy-v1", "wrong matched source contract")
    policy = manifest["policy"]
    required = {"variant": "E", "parallel": "loose", "search_workers": workers,
                "total_threads": workers + 1, "tt_slot_bytes": 16, "tt_bits": 18,
                "tt_total_bytes": 4194304, "search_stack_bytes": 1048576,
                "cold_process_per_fixture": True, "startup_tt_clear_prefault": True,
                "c_lto": True, "rust_lto": "fat", "optimization": "speed"}
    for key, value in required.items():
        require(policy.get(key) == value, f"manifest policy {key!r} is not {value!r}")
    require({item["id"] for item in manifest["engines"]} == {"E-c", "E-rust"}, "expected two independent E engines")
    files = []
    for item in manifest["sources"]:
        relative = Path(item["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "unsafe source path")
        source = path.parent / "source" / relative
        require(sha(source) == item["sha256"], f"frozen source drift: {source}")
        files.append({"path": str(source), "sha256": item["sha256"], "bytes": source.stat().st_size})
        for language in ("c", "rust"):
            relevant = relative.parts[0] == language or (relative.parts[0] == "model" and relative.suffix in ((".h",) if language == "c" else (".rs",)))
            if relevant:
                compiled = path.parent / language / relative
                require(sha(compiled) == item["sha256"], f"compiler input drift: {compiled}")
                files.append({"path": str(compiled), "sha256": item["sha256"], "bytes": compiled.stat().st_size})
    for engine in manifest["engines"]:
        native = engine["native"]
        require(len(engine["command"]) == 1 and engine["command"][0] == native["path"], "unexpected native command")
        binary = Path(native["path"])
        require(native["returncode"] == 0 and sha(binary) == native["sha256"], "native changed or did not compile")
        require(binary.stat().st_size == native["bytes"], "native size changed")
        require(engine["workers"] == workers and engine["profile"] == "dev", "wrong engine resource profile")
        files.append({"path": str(binary), "sha256": native["sha256"], "bytes": native["bytes"]})
    return manifest, {"path": str(path), "sha256": sha(path), "base": manifest["base"], "policy": policy,
                      "sources": manifest["sources"], "verified_files": files,
                      "templates": manifest["templates"], "recipe_helpers": manifest["recipe_helpers"],
                      "tools": manifest["tools"], "tool_metadata_sha256": json_sha(manifest["tools"]),
                      "engines": manifest["engines"]}


class Session:
    """One actual engine, no polling sampler, reader threads or hot-path log I/O."""
    def __init__(self, spec, affinity, timeout, measured, deadline):
        self.timeout, self.measured = timeout, measured
        self.deadline = deadline
        self.events, self.buffers, self.stderr = [], {}, []
        self.output_bytes, self.closed = 0, False
        self.launch_ns = time.perf_counter_ns() if measured else None
        self.process = subprocess.Popen([shutil.which("taskset"), "-c", ",".join(map(str, affinity)), *spec["command"]],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        start_new_session=True, env=RUNTIME_ENV)
        self.selector = selectors.DefaultSelector()
        for stream, name in ((self.process.stdout, "stdout"), (self.process.stderr, "stderr")):
            os.set_blocking(stream.fileno(), False)
            self.selector.register(stream, selectors.EVENT_READ, name)
            self.buffers[name] = bytearray()
        self.pending = []
        self.affinity = affinity
        self.workers = spec["workers"]

    def send(self, command):
        require(self.process.poll() is None, f"engine exited before {command}")
        self.events.append({"direction": "stdin", "value": command})
        self.process.stdin.write((command + "\n").encode())
        self.process.stdin.flush()

    def until(self, predicate):
        deadline = min(time.monotonic() + self.timeout, self.deadline)
        lines = []
        while True:
            while self.pending:
                line, received_ns = self.pending.pop(0)
                lines.append(line)
                if predicate(line):
                    return lines, received_ns
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"engine response timeout; last lines {lines[-4:]}")
            ready = self.selector.select(remaining)
            require(ready or self.process.poll() is None, "engine exited before response")
            for key, _ in ready:
                chunk = os.read(key.fd, 65536)
                received_ns = time.perf_counter_ns() if self.measured else None
                if not chunk:
                    self.selector.unregister(key.fileobj)
                    require(key.data != "stdout", "engine closed stdout before response")
                    continue
                self.output_bytes += len(chunk)
                require(self.output_bytes <= 1024 * 1024, "engine output exceeded 1 MiB")
                buffer = self.buffers[key.data]
                buffer.extend(chunk)
                require(len(buffer) <= 65536, "engine output line exceeded 64 KiB")
                while b"\n" in buffer:
                    raw, _, rest = buffer.partition(b"\n")
                    buffer[:] = rest
                    line = raw.rstrip(b"\r").decode("utf-8", "strict")
                    self.events.append({"direction": key.data, "value": line})
                    if key.data == "stdout":
                        self.pending.append((line, received_ns))
                    else:
                        self.stderr.append(line)

    def request(self, command, predicate):
        self.send(command)
        lines, _ = self.until(predicate)
        require(not any(line.startswith("bestmove ") for line in lines), "unsolicited or duplicate bestmove outside active search")
        return lines[-1]

    def initialize(self):
        self.request("uci", lambda line: line == "uciok")
        self.send("isready")
        _, ready_ns = self.until(lambda line: line == "readyok")
        self.startup = process_snapshot(self.process.pid, self.measured)
        require(len(self.startup["task_ids"]) == self.workers + 1, "wrong fixed startup thread count")
        require(all(mask == self.affinity for mask in self.startup["task_affinity"].values()), "thread affinity differs")
        if self.measured:
            self.startup["launch_to_ready_wall_seconds"] = (ready_ns - self.launch_ns) / 1e9

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.process.poll() is None:
                self.send("quit")
                self.process.stdin.close()
                self.process.wait(timeout=min(5, self.timeout))
            require(self.process.returncode == 0, f"engine exit {self.process.returncode}; {self.stderr[-4:]}")
        finally:
            if self.process.poll() is None:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=3)
            self.selector.close()
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                stream.close()


def parse_info(lines, board):
    info = []
    for line in lines:
        if not line.startswith("info ") or " score " not in line:
            continue
        fields = line.split()
        get = lambda token: fields[fields.index(token) + 1]
        kind = get("score")
        require(kind == "cp", "fixed nonmate fixture returned a mate score")
        pv = fields[fields.index("pv") + 1:]
        require(pv, "completed depth omitted PV")
        position = board
        for move in pv:
            require(MOVE.fullmatch(move), "invalid PV token")
            position = position.play(move)
        require("lowerbound" not in fields and "upperbound" not in fields, "root completed a nonexact bound")
        info.append({"depth": int(get("depth")), "kind": kind, "score": int(fields[fields.index("score") + 2]),
                     "nodes": int(get("nodes")), "pv": pv})
    return info


def run_case(spec, affinity, case, depth, timeout, measured, output, label, deadline):
    name, fen, moves = case
    board = Board.from_fen(fen) if fen else Board.from_fen()
    for move in moves:
        board = board.play(move)
    engine = Session(spec, affinity, timeout, measured, deadline)
    record = {"engine": spec["id"], "native_sha256": spec["native"]["sha256"], "passed": False}
    try:
        engine.initialize()
        prepare_ns = time.perf_counter_ns() if measured else None
        engine.send("position " + ("startpos" if fen is None else "fen " + fen) + (" moves " + " ".join(moves) if moves else ""))
        engine.request("isready", lambda line: line == "readyok")
        state_line = engine.request("state", lambda line: line.startswith("{") or line.startswith("state {"))
        state = json.loads(state_line[state_line.index("{"):])
        require(state.get("invariant", True) is True, "incremental board invariant failed")
        legal_line = engine.request("legal", lambda line: line.startswith("legal"))
        legal = set(legal_line.split()[1:])
        require(legal == {str(move) for move in board.legal_moves()}, "legal moves differ from independent oracle")
        require(legal, "fixture is terminal")
        before = cpu_ticks(engine.process.pid) if measured else None
        start_ns = time.perf_counter_ns() if measured else None
        engine.send(f"go depth {depth}")
        lines, end_ns = engine.until(lambda line: line.startswith("bestmove "))
        after = cpu_ticks(engine.process.pid) if measured else None
        cpu_after_ns = time.perf_counter_ns() if measured else None
        # Everything below, including oracle/PV validation, is outside the timed interval.
        best_lines = [line for line in lines if line.startswith("bestmove ")]
        require(len(best_lines) == 1, "duplicate bestmove in search response")
        best = best_lines[0].split()[1]
        require(best in legal, "bestmove is illegal")
        info = parse_info(lines, board)
        require([item["depth"] for item in info] == list(range(1, depth + 1)), "requested iterative depth was not completed exactly")
        stats_line = engine.request("stats", lambda line: line.startswith("{") or line.startswith("stats {"))
        stats = json.loads(stats_line[stats_line.index("{"):])
        # A chosen root's info can precede other workers' final cancellation/
        # completion. Preserve both; throughput uses the completed aggregate.
        if spec["workers"] == 1:
            require(stats["nodes"] == info[-1]["nodes"], "one-worker final info and stats nodes differ")
        else:
            require(stats["nodes"] >= info[-1]["nodes"], "aggregate stats lost already reported nodes")
        require(stats.get("tt_bytes", 4194304) == 4194304, "actual TT bytes differ")
        require(stats.get("workers", spec["workers"]) == spec["workers"], "actual workers differ")
        memory = process_snapshot(engine.process.pid, measured)
        require(memory["task_ids"] == engine.startup["task_ids"], "persistent task identities changed")
        require(all(mask == affinity for mask in memory["task_affinity"].values()), "search changed thread affinity")
        record.update({"case": name, "depth": depth, "state": state, "bestmove": best, "info": info,
                       "actual_nodes": stats["nodes"], "stats": stats, "startup": engine.startup, "postsearch": memory})
        if measured:
            require(before["process_start_ticks"] == after["process_start_ticks"], "process identity changed")
            ticks = {key: after[key] - before[key] for key in ("user", "system")}
            require(min(ticks.values()) >= 0, "process CPU counter moved backwards")
            hz = os.sysconf("SC_CLK_TCK")
            wall = (end_ns - start_ns) / 1e9
            cpu = sum(ticks.values()) / hz
            require(wall > 0, "search wall time is not positive")
            record["measurement"] = {"presearch_prepare_wall_seconds": (start_ns - prepare_ns) / 1e9,
                                     "search_wall_seconds": wall, "search_cpu_user_ticks": ticks["user"],
                                     "cpu_before": before, "cpu_after": after,
                                     "bestmove_receive_to_cpu_read_seconds": (cpu_after_ns - end_ns) / 1e9,
                                     "search_cpu_system_ticks": ticks["system"], "search_cpu_seconds": cpu,
                                     "cpu_tick_seconds": 1 / hz, "cpu_endpoint_quantization_bound_seconds": 2 / hz,
                                     "cpu_above_two_ticks": sum(ticks.values()) > 2,
                                     "nodes_per_wall_second": stats["nodes"] / wall,
                                     "nodes_per_cpu_second": stats["nodes"] / cpu if sum(ticks.values()) > 2 else None,
                                     "mean_cpu_parallelism": cpu / wall if sum(ticks.values()) > 2 else None}
        # A ready barrier also exposes any queued duplicate bestmove before shutdown.
        engine.send("isready")
        trailing, _ = engine.until(lambda line: line == "readyok")
        require(not any(line.startswith("bestmove ") for line in trailing), "late duplicate bestmove")
        record["passed"] = True
        return record
    finally:
        try:
            engine.close()
        finally:
            (output / (label + ".jsonl")).write_text("".join(json.dumps(event) + "\n" for event in engine.events))


def compare_pair(records, workers, depth):
    left, right = sorted(records, key=lambda item: item["engine"])
    for key in ("hash", "pawn_hash"):
        values = [int(item["state"][key], 16) if isinstance(item["state"][key], str) else item["state"][key] for item in (left, right)]
        require(values[0] == values[1], "cross-engine " + key + " differs")
    require(left["state"]["eval"] == right["state"]["eval"], "raw E evaluation differs")
    for a, b in zip(left["info"], right["info"]):
        require((a["depth"], a["kind"], a["score"]) == (b["depth"], b["kind"], b["score"]), "completed depth semantic value differs")
        if workers == 1:
            require(a["nodes"] == b["nodes"], f"one-worker tree differs at depth {a['depth']}: {a['nodes']} / {b['nodes']}")
    if workers == 1:
        require(left["bestmove"] == right["bestmove"], "one-worker attaining move differs")
        require(left["actual_nodes"] == right["actual_nodes"], "one-worker actual nodes differ")
    return {"every_depth_score_equal": True, "one_worker_exact_nodes_and_move_required": workers == 1,
            "requested_depth": depth, "passed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--one", type=Path, required=True)
    parser.add_argument("--four", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=("prepare", "gate", "measure"), default="prepare")
    parser.add_argument("--profiles", choices=("one", "four", "both"), default="both")
    parser.add_argument("--cases", action="append", help="known case name(s), comma separated or repeated; default all")
    parser.add_argument("--cpus-one", type=cpus, required=True)
    parser.add_argument("--cpus-four", type=cpus, required=True)
    parser.add_argument("--depths", default="5,5,4", help="start,opening,kiwipete fixed depths")
    parser.add_argument("--samples", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--sample-start", type=int, default=0, help="global first sample index, preserving cold-pair alternation")
    parser.add_argument("--timeout", type=float, default=15, help="finite timeout for each protocol response")
    parser.add_argument("--budget", type=float, default=55, help="campaign budget checked between cold processes")
    parser.add_argument("--quiet-window", help="coordination identifier; required only after the owner grants the quiet window")
    args = parser.parse_args()
    require(sys.platform == "linux", "Linux /proc and affinity are required")
    require(shutil.which("taskset") is not None, "taskset is required for affinity before worker creation")
    require(not args.out.exists() and not args.out.resolve().is_relative_to(ROOT), "output must be new and outside repository")
    require(0 < args.timeout <= 30 and 0 < args.budget <= 60, "finite timeout/budget must be at most 30/60 seconds")
    require(args.mode != "measure" or bool(args.quiet_window), "measure requires an explicitly coordinated --quiet-window")
    require(0 <= args.sample_start and args.sample_start + args.samples <= 3, "global samples must stay within indices 0,1,2")
    depths = [int(value) for value in args.depths.split(",")]
    require(len(depths) == 3 and all(1 <= depth <= 8 for depth in depths), "three depths between one and eight are required")
    known_cases = {case[0] for case in CASES}
    selected_cases = {name.strip() for value in args.cases for name in value.split(",")} if args.cases else known_cases
    require(selected_cases and selected_cases <= known_cases, "--cases must select known cases: " + ",".join(sorted(known_cases)))
    allowed = os.sched_getaffinity(0)
    for workers, mask in ((1, args.cpus_one), (4, args.cpus_four)):
        require(set(mask) <= allowed and len(mask) >= workers, "CPU masks must be available and cover search workers")
    manifests, metadata = {}, {}
    for workers, path in ((1, args.one), (4, args.four)):
        manifests[workers], metadata[workers] = frozen_manifest(path.resolve(), workers)
    first_policy = {key: value for key, value in manifests[1]["policy"].items() if key not in ("search_workers", "total_threads")}
    second_policy = {key: value for key, value in manifests[4]["policy"].items() if key not in ("search_workers", "total_threads")}
    require(first_policy == second_policy, "one/four policies differ beyond worker counts")
    require(manifests[1]["base"] == manifests[4]["base"], "different frozen Git base")
    args.out.mkdir(parents=True)
    helper_hashes = {str(Path(__file__).resolve()): sha(__file__), str(ORACLE): sha(ORACLE)}
    report = {"schema": 1, "contract": "matched-c-policy-v1", "mode": args.mode,
              "scope": "bounded frozen matched-E workload; no causal language, Elo, general NPS or target-scalability claim",
              "quiet_window": args.quiet_window, "definitions": {
                  "cold": "fresh engine process for each fixture/language/sample; TT and learning are cold",
                  "startup": "process launch through isready response, including taskset exec, loader and real TT prefault",
                  "search_wall": "before flushing go through kernel stdout-read receipt of bestmove; excludes later validation",
                  "search_cpu": "delta of aggregate process /proc/PID/stat utime+stime, all persistent engine threads; excludes supervisor",
                  "cpu_resolution": "kernel CLK_TCK; up to two ticks endpoint quantization; CPU rates omitted at <=2 ticks",
                  "memory": "kernel status VmRSS/VmHWM etc after ready/prefault and after real search; high-water is lifetime, not additive",
                  "affinity": "taskset before native exec; input and every worker inherit the same explicit mask",
                  "ordering": "alternating C/Rust and Rust/C cold pairs, reversed by fixture/profile; at most three paired samples",
                  "four_workers": "shared TT races can change actual nodes; each sample reports its real work, exact nodes required only with one worker"},
              "host": {"uname": list(os.uname()), "allowed_cpus": sorted(allowed),
                       "supervisor_cpus": sorted(os.sched_getaffinity(0)), "cpu_tick_hz": os.sysconf("SC_CLK_TCK"),
                       "logical_cpu_count": os.cpu_count(), "topology": {}},
              "affinity": {"one": args.cpus_one, "four": args.cpus_four},
              "native_environment": RUNTIME_ENV,
              "invocation": {"argv": list(sys.argv), "mode": args.mode, "profiles": args.profiles,
                             "cases": [case[0] for case in CASES if case[0] in selected_cases],
                             "depths_in_original_case_order": depths, "samples": args.samples,
                             "sample_start": args.sample_start,
                             "timeout_seconds": args.timeout, "budget_seconds": args.budget},
              "helper_sha256": helper_hashes, "manifests": metadata,
              "fixtures": [{"id": case[0], "original_index": index, "fen": case[1], "moves": case[2], "depth": depth}
                           for index, (case, depth) in enumerate(zip(CASES, depths)) if case[0] in selected_cases],
              "requested_samples": args.samples, "samples": [], "passed": False}
    for cpu in sorted(set(args.cpus_one + args.cpus_four)):
        root = Path("/sys/devices/system/cpu") / f"cpu{cpu}" / "topology"
        report["host"]["topology"][str(cpu)] = {key: (root / key).read_text().strip() for key in ("core_id", "physical_package_id", "thread_siblings_list")}
    report["campaign_started_utc"] = utc_now()
    write_json(args.out / "results.json", report)
    campaign_start = time.monotonic()
    try:
        if args.mode != "prepare":
            profiles = (1, 4) if args.profiles == "both" else ((1,) if args.profiles == "one" else (4,))
            for workers in profiles:
                profile_index = 0 if workers == 1 else 1
                manifest = manifests[workers]
                affinity = args.cpus_one if workers == 1 else args.cpus_four
                for case_index, (case, depth) in enumerate(zip(CASES, depths)):
                    if case[0] not in selected_cases:
                        continue
                    for sample in range(args.sample_start, args.sample_start + (args.samples if args.mode == "measure" else 1)):
                        engines = sorted(manifest["engines"], key=lambda item: item["id"])
                        if (sample + case_index + profile_index) % 2:
                            engines.reverse()
                        pair = {"workers": workers, "case": case[0], "sample": sample,
                                "order": [item["id"] for item in engines], "records": [], "passed": False}
                        report["samples"].append(pair)
                        for spec in engines:
                            require(time.monotonic() - campaign_start < args.budget, "bounded campaign budget exhausted; incomplete results retained")
                            label = f"w{workers}-{case[0]}-s{sample}-{spec['id']}"
                            pair["records"].append(run_case(spec, affinity, case, depth, args.timeout, args.mode == "measure", args.out, label,
                                                            campaign_start + args.budget))
                        pair["semantic_gate"] = compare_pair(pair["records"], workers, depth)
                        pair["passed"] = True
                        write_json(args.out / "results.json", report)
                        print(f"w{workers} {case[0]} sample {sample}: semantic PASS", flush=True)
        for workers, path in ((1, args.one), (4, args.four)):
            _, checked = frozen_manifest(path.resolve(), workers)
            require(checked == metadata[workers], "frozen metadata drifted during campaign")
        require(all(sha(path) == expected for path, expected in helper_hashes.items()), "measurement helper drifted during campaign")
        if args.mode == "measure":
            summaries = []
            for workers in profiles:
                for case in CASES:
                    if case[0] not in selected_cases:
                        continue
                    for engine in ("E-c", "E-rust"):
                        rows = [record for pair in report["samples"] if pair["workers"] == workers and pair["case"] == case[0]
                                for record in pair["records"] if record["engine"] == engine]
                        metrics = ("search_wall_seconds", "search_cpu_seconds", "nodes_per_wall_second")
                        summaries.append({"workers": workers, "case": case[0], "engine": engine, "count": len(rows),
                                          "actual_nodes": [row["actual_nodes"] for row in rows],
                                          "median": {key: statistics.median(row["measurement"][key] for row in rows) for key in metrics},
                                          "range": {key: [min(row["measurement"][key] for row in rows), max(row["measurement"][key] for row in rows)] for key in metrics}})
            report["summary"] = summaries
        report["passed"] = True
        print(args.mode + ": PASS", flush=True)
        return 0
    except Exception as error:
        report["error"] = {"kind": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        raise
    finally:
        report["campaign_ended_utc"] = utc_now()
        write_json(args.out / "results.json", report)


if __name__ == "__main__":
    raise SystemExit(main())
