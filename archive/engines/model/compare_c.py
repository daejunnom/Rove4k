#!/usr/bin/env python3
"""Compare C baseline/C+E complete-file costs and bounded shipping-UCI searches.

This records response/startup timings and chosen moves, not NPS or playing strength.
Build both campaigns from identical source bytes and the same fixed profile first.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import signal
import statistics
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
POSITIONS = (
    "position startpos",
    "position startpos moves e2e4 e7e5 g1f3 b8c6 f1b5",
    "position startpos moves d2d4 d7d5 c1f4 g8f6 e2e3 c8f5 g1f3 e7e6 f1d3 f5d3 c2d3",
)


def verify_artifact(artifact):
    data = Path(artifact["path"]).read_bytes()
    if len(data) != artifact["bytes"] or hashlib.sha256(data).hexdigest() != artifact["sha256"]:
        raise ValueError("built artifact changed: " + artifact["path"])


def apply_runtime_recheck(build, build_path, path):
    recheck = json.loads(path.read_text())
    if not recheck.get("passed") or Path(recheck["original_build"]).resolve() != build_path.resolve():
        raise ValueError("runtime recheck does not match the model build")
    lookup = {(engine["id"], a["path"]): a for engine in build["engines"] for a in engine["artifacts"]}
    for observation in recheck["artifacts"]:
        artifact = lookup[(observation["engine"], observation["path"])]
        if observation["sha256"] != artifact["sha256"] or not observation["runtime"].get("passed"):
            raise ValueError("runtime recheck identity or result mismatch")
        artifact["runtime_before_recheck"] = artifact["runtime"]
        artifact["runtime"] = observation["runtime"]
        artifact["runtime_recheck_classification"] = observation["classification"]


def matched_file_costs(baseline, model):
    def key(artifact):
        return artifact["source_form"], artifact["format"], artifact.get("codec")

    cross = {key(a): a for a in model["artifacts"]}
    costs = []
    for before in baseline["artifacts"]:
        after = cross.get(key(before))
        if after is None:
            continue
        costs.append({"source_form": before["source_form"], "format": before["format"],
                      "codec": before.get("codec"), "baseline_bytes": before["bytes"],
                      "model_bytes": after["bytes"], "delta_bytes": after["bytes"] - before["bytes"],
                      "baseline_sha256": before["sha256"], "model_sha256": after["sha256"]})
    return costs


def search(command, position, clock_ms, timeout):
    started = time.monotonic()
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, bufsize=1,
                               start_new_session=True)
    lines, output = queue.Queue(), []

    def reader():
        for line in process.stdout:
            lines.put(line.rstrip("\n"))
        lines.put(None)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    def write(text):
        process.stdin.write(text + "\n")
        process.stdin.flush()

    def wait_for(prefix):
        deadline = time.monotonic() + timeout
        while True:
            try:
                line = lines.get(timeout=max(0.001, deadline - time.monotonic()))
            except queue.Empty as error:
                raise TimeoutError("engine did not produce " + prefix) from error
            if line is None:
                raise RuntimeError("engine exited before " + prefix)
            output.append(line)
            if sum(map(len, output)) > 1024 * 1024:
                raise RuntimeError("engine output exceeded 1 MiB")
            if line.startswith(prefix):
                return line
            if time.monotonic() >= deadline:
                raise TimeoutError("engine did not produce " + prefix)

    try:
        write("uci")
        wait_for("uciok")
        write("isready")
        wait_for("readyok")
        startup = time.monotonic() - started
        write(position)
        search_start = time.monotonic()
        write(f"go wtime {clock_ms} btime {clock_ms} winc 0 binc 0")
        bestmove = wait_for("bestmove ").split()[1]
        elapsed = time.monotonic() - search_start
        if not re.fullmatch("[a-h][1-8][a-h][1-8][nbrq]?", bestmove):
            raise RuntimeError("unexpected bestmove for opening position: " + bestmove)
        write("quit")
        process.wait(timeout=timeout)
        thread.join(timeout=1)
        while not lines.empty():
            line = lines.get_nowait()
            if line is not None:
                output.append(line)
        if sum(line.startswith("bestmove ") for line in output) != 1:
            raise RuntimeError("expected exactly one bestmove for the search")
        stderr = process.stderr.read()
        if process.returncode:
            raise RuntimeError(f"engine exited {process.returncode}: {stderr}")
        return {"startup_seconds": startup, "search_response_seconds": elapsed,
                "bestmove": bestmove, "stdout": output, "stderr": stderr,
                "exit_code": process.returncode}
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=timeout)
        process.stdin.close()
        process.stdout.close()
        process.stderr.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="baseline build.json")
    parser.add_argument("--model", type=Path, required=True, help="--model build.json")
    parser.add_argument("--model-runtime-recheck", type=Path,
                        help="optional same-byte runtime recheck; preserves initial runtime results")
    parser.add_argument("--out", type=Path, required=True, help="absolute JSON outside checkout")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--clock-ms", type=int, default=6000)
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    if os.name != "posix" or not args.out.is_absolute() or args.out.resolve().is_relative_to(ROOT):
        parser.error("run on Linux with absolute --out outside the checkout")
    if not 1 <= args.samples <= 10 or not 300 <= args.clock_ms <= 30000 or not 1 <= args.timeout <= 30:
        parser.error("bounded ranges: samples1..10, clock-ms300..30000, timeout1..30")
    paths = (args.baseline, args.model)
    builds = [json.loads(path.read_text()) for path in paths]
    if args.model_runtime_recheck:
        apply_runtime_recheck(builds[1], args.model, args.model_runtime_recheck)
    if not all(build.get("complete") for build in builds):
        raise ValueError("both complete build campaigns are required")
    for key in ("profile", "optimize", "parallel"):
        if builds[0][key] != builds[1][key]:
            raise ValueError("fixed build setting differs: " + key)
    if builds[0]["model_cross_candidate"] or not builds[1]["model_cross_candidate"]:
        raise ValueError("expected baseline model=false and cross model=true")
    if builds[0]["profile"]["development"]:
        raise ValueError("shipping-profile builds are required for this comparison")
    report = {"schema": 1, "purpose": "same-profile C versus C+E engineering comparison",
              "scope": "native shipping UCI timings; no NPS, legality or strength conclusion",
              "profile": builds[0]["profile"], "clock_ms": args.clock_ms,
              "samples_per_position": args.samples,
              "builds": [{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                         for path in paths], "comparisons": [], "complete": False}
    if args.model_runtime_recheck:
        report["model_runtime_recheck"] = {
            "path": str(args.model_runtime_recheck),
            "sha256": hashlib.sha256(args.model_runtime_recheck.read_bytes()).hexdigest()}
    try:
        for language in ("c", "rust"):
            records = [next(r for r in build["engines"] if r["id"] == f"C-{language}{suffix}")
                       for build, suffix in zip(builds, ("", "-model"))]
            if records[0]["sources"] != records[1]["sources"]:
                raise ValueError(language + " source bytes changed between build campaigns")
            settings = [{k: v for k, v in r["configuration"].items() if k != "ROVE_MODEL"}
                        for r in records]
            if settings[0] != settings[1]:
                raise ValueError(language + " compile settings differ beyond ROVE_MODEL")
            comparison = {"language": language, "candidates": []}
            report["comparisons"].append(comparison)
            for name, record in zip(("C", "C+E"), records):
                smallest = min(record["artifacts"], key=lambda a: a["bytes"])
                verified = min((a for a in record["artifacts"] if
                                a.get("runtime", {}).get("passed") is True), key=lambda a: a["bytes"])
                native = next(a for a in record["artifacts"] if a["path"] == record["command"][0])
                for artifact in (smallest, verified, native):
                    verify_artifact(artifact)
                candidate = {"name": name, "command": record["command"],
                             "smallest_complete_file": smallest,
                             "smallest_runtime_verified_file": verified,
                             "artifacts": record["artifacts"], "searches": []}
                comparison["candidates"].append(candidate)
                for position in POSITIONS:
                    for sample in range(args.samples):
                        observed = search(record["command"], position, args.clock_ms, args.timeout)
                        candidate["searches"].append({"position": position, "sample": sample, **observed})
                candidate["median_startup_seconds"] = statistics.median(
                    r["startup_seconds"] for r in candidate["searches"])
                candidate["median_search_response_seconds"] = statistics.median(
                    r["search_response_seconds"] for r in candidate["searches"])
            baseline, model = comparison["candidates"]
            comparison["matched_file_costs"] = matched_file_costs(baseline, model)
            comparison["smallest_complete_file_delta_bytes"] = (
                model["smallest_complete_file"]["bytes"] - baseline["smallest_complete_file"]["bytes"])
            comparison["smallest_runtime_verified_file_delta_bytes"] = (
                model["smallest_runtime_verified_file"]["bytes"] -
                baseline["smallest_runtime_verified_file"]["bytes"])
            comparison["median_startup_delta_seconds"] = (
                model["median_startup_seconds"] - baseline["median_startup_seconds"])
            comparison["median_response_delta_seconds"] = (
                model["median_search_response_seconds"] - baseline["median_search_response_seconds"])
        report["complete"] = True
    except Exception as error:
        report["failure"] = str(error)
        raise
    finally:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
    for comparison in report["comparisons"]:
        for candidate in comparison["candidates"]:
            print(comparison["language"], candidate["name"],
                  candidate["smallest_complete_file"]["bytes"], "bytes; median response",
                  round(candidate["median_search_response_seconds"], 6), "seconds")


if __name__ == "__main__":
    main()
