#!/usr/bin/env python3
"""Actual production-source parity, SIMD consumption, startup and restoration."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def runtime(engine_module, binary, workers=2, search=False):
    started = time.monotonic()
    engine = engine_module.Engine(binary)
    try:
        engine.send("uci", "uciok")
        startup = time.monotonic() - started
        proc = Path("/proc") / str(engine.process.pid)
        tids = sorted(int(path.name) for path in (proc / "task").iterdir())
        if len(tids) != workers + 1:
            raise AssertionError("fixed pool missing at startup")
        status = {}
        for line in (proc / "status").read_text().splitlines():
            if line.startswith(("VmRSS:", "VmHWM:", "VmSize:", "VmData:")):
                key, value = line.split(":", 1);status[key] = value.strip()
        engine.send("isready", "readyok")
        stats = None
        if search:
            engine.send("position startpos\nisready", "readyok")
            engine.send("go depth 4", "bestmove ")
            stats = json.loads(engine.send("stats", "{")[-1])
            if any(stats[name] <= 0 for name in ("leaf_calls", "pvs", "qs", "history_updates", "continuation_updates", "correction_updates", "correction_uses")):
                raise AssertionError({"actual_algorithm_consumption": stats})
            if stats["ordering_calls"]:
                raise AssertionError("unintended E ordering path")
        if tids != sorted(int(path.name) for path in (proc / "task").iterdir()):
            raise AssertionError("startup task IDs changed")
        engine.close()
        return {"program_sha256": sha(binary), "startup_seconds_observed": startup, "resource_at_uci": status,
                "startup_thread_ids": tids, "threads_stable": True, "search": stats,
                "scope": "software startup observation under concurrent host load; no isolated timing or NPS claim"}
    finally:
        engine.terminate()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT == args.out or ROOT in args.out.parents:
        parser.error("new external absolute output required")
    args.out.mkdir(parents=True)
    campaign = json.loads(args.campaign.read_bytes())
    if not campaign["complete"]:
        raise ValueError("complete two-representation build campaign required")
    frozen = args.campaign.parent / "frozen"
    fixture = frozen / "engines/experiments/tiny-c-table/table_contract.c"
    engine_module = load("table_qualify_engine", frozen / "engines/compact/tiny-ce/check.py")
    report = {"campaign_sha256": sha(args.campaign), "fixture_sha256": sha(fixture), "passed": False,
              "baseline_C6059_startup": None, "candidates": []}
    try:
        control = json.loads((args.campaign.parent / "controls/C-build.json").read_bytes())
        baseline = next(item for item in control["engines"] if item["id"] == "tiny-C-original")
        baseline_binary = Path(baseline["command"][0])
        if sha(baseline_binary) != baseline["native_sha256"]:
            raise ValueError("baseline native control changed")
        report["baseline_C6059_startup"] = runtime(engine_module, baseline_binary)
        report["baseline_C6059_native_sections"] = subprocess.check_output(["size", "-A", str(baseline_binary)], text=True)
        for candidate in campaign["candidates"]:
            name = candidate["representation"]
            output = args.out / name;output.mkdir()
            build_path = Path(candidate["build"])
            if sha(build_path) != candidate["build_sha256"]:
                raise ValueError("candidate build manifest changed")
            build = json.loads(build_path.read_bytes())
            dev = next(item for item in build["engines"] if item["profile"] == "dev")
            source = Path(dev["cwd"]) / "main.c"
            if sha(source) != dev["source_sha256"]:
                raise ValueError("actual production input changed")
            harness = output / "actual-production-contract.c"
            harness.write_text("#define main tiny_c_table_engine_main\n#include " + json.dumps(str(source)) +
                               "\n#undef main\n#define TINY_C_TABLE_PRODUCTION_INCLUDED\n#include " + json.dumps(str(fixture)) + "\n")
            checks = []
            for label, flags in (("optimized", ["-O2"]), ("asan-ubsan", ["-O1", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"])):
                program = output / label
                command = ["cc", "-std=c11", "-pthread", "-DDEV=1", "-mavx2", *flags, str(harness), "-o", str(program)]
                subprocess.run(command, check=True, timeout=120)
                result = subprocess.run([str(program)], capture_output=True, text=True, check=True, timeout=60)
                if result.stderr:
                    raise AssertionError(result.stderr)
                table = subprocess.check_output([str(program), "--dump-table"], timeout=5)
                if hashlib.sha256(table).hexdigest() != candidate["table"]["table_i32le_sha256"]:
                    raise AssertionError("actual initialized/readonly production table identity mismatch")
                checks.append({"kind": label, "compile": command, "program_sha256": sha(program), "result": json.loads(result.stdout),
                               "actual_table_bytes": len(table), "actual_table_i32le_sha256": hashlib.sha256(table).hexdigest()})
            dev_binary = Path(dev["command"][0])
            actual_search = runtime(engine_module, dev_binary, search=True)
            shipping = next(item for item in build["engines"] if item["id"] == "tiny-C-original")
            instructions = {}
            for label, program in (("dev", dev_binary), ("shipping", Path(shipping["command"][0]))):
                assembly = subprocess.check_output(["objdump", "-d", str(program)], text=True)
                counts = {name: len(re.findall(r"\b" + name + r"\b", assembly)) for name in ("vpgatherdd", "vphaddd")}
                if not all(counts.values()):
                    raise AssertionError("actual lookup gather/reduction missing")
                instructions[label] = {"sha256": sha(program), "instructions": counts}
            restoration_out = output / "restoration"
            subprocess.run([sys.executable, "-I", "-B", str(frozen / "engines/compact/tiny-ce/restoration.py"),
                            "--build", str(build_path), "--out", str(restoration_out)], check=True, timeout=120)
            report["candidates"].append({"representation": name, "producer_source_sha256": sha(source), "harness_sha256": sha(harness),
                "parity": checks, "actual_search": actual_search, "actual_native_startup": runtime(engine_module, Path(shipping["command"][0])),
                "simd_instruction_proof": instructions, "restoration": str(restoration_out / "results.json")})
            (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
        report["passed"] = True
    finally:
        (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "representations": [item["representation"] for item in report["candidates"]]}))


if __name__ == "__main__":
    main()
