#!/usr/bin/env python3
"""Explicit bounded startup-only admission of D's fixed raw-clone pool.

The build command alone does not claim large-profile execution. This separate
driver freezes the common Linux resource/lifecycle harness and admits one
native shipping ELF at a time. It never submits a search and makes no hardware
scalability claim on an oversubscribed WSL host.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.is_absolute():
        args.out = args.out.resolve()
    if not args.out.is_absolute() or args.out.exists() or HERE.parents[2] in args.out.parents:
        parser.error("--out must be a new absolute external directory")
    args.out.mkdir(parents=True)
    frozen = args.out / "target_startup.py"
    shutil.copyfile(HERE.parents[1] / "tests/target_startup.py", frozen)
    spec = importlib.util.spec_from_file_location("tiny_d_frozen_startup", frozen)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    gib = 1024**3
    limits = SimpleNamespace(minimum_available_bytes=6*gib, max_rss_bytes=3*gib,
                             address_space_bytes=8*gib, data_bytes=8*gib,
                             cpu_seconds=20, timeout_seconds=45)
    report = {"source_manifest_sha256": sha(args.build), "harness_sha256": sha(frozen),
              "logical_cpu_count": os.cpu_count(), "search_submitted": False,
              "hardware_scalability_verified": False, "limits": vars(limits), "runs": [], "complete": False}
    for record in json.loads(args.build.read_text())["engines"]:
        if record["profile"] != "shipping":
            continue
        path = Path(record["command"][0])
        if sha(path) != record["native_sha256"]:
            raise RuntimeError("native hash drift")
        for mode in ("quit", "eof"):
            result = {"id": record["id"], "program_sha256": sha(path),
                      **module.check_one(path, record["startup_threads"], mode, limits)}
            result["program_sha256_after"] = sha(path)
            if result["program_sha256_after"] != result["program_sha256"]:
                result.update(passed=False, error="native bytes changed during execution")
            report["runs"].append(result)
            (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps({key: result.get(key) for key in ("id", "termination", "passed", "startup_ready_seconds", "observed_peak_rss_bytes", "error")}), flush=True)
            if not result["passed"]:
                return 1
    report["complete"] = True
    report["passed"] = bool(report["runs"]) and all(r["passed"] for r in report["runs"])
    (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
