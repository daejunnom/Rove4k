#!/usr/bin/env python3
"""Measure prepared representation candidates with one frozen central builder.

Initial measurements intentionally do not execute artifacts. Selected candidates
still require actual runtime and reproduction checks before adoption.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from generate import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--builder", type=Path, required=True, help="one frozen central build.py")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rustc", required=True)
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.resolve().is_relative_to(ROOT) or args.out.exists():
        parser.error("--out must be a new absolute directory outside checkout")
    prepared = json.loads(args.prepared.read_text())
    args.out.mkdir(parents=True)
    report = {"scope": "observed complete-file costs; runtime not executed in this measurement",
              "builder": str(args.builder),
              "builder_sha256": hashlib.sha256(args.builder.read_bytes()).hexdigest(),
              "prepared": str(args.prepared),
              "prepared_sha256": hashlib.sha256(args.prepared.read_bytes()).hexdigest(),
              "profile": "local-ship", "complete": False, "candidates": []}
    try:
        for candidate in prepared["candidates"]:
            fmt = candidate["runtime_representation"]
            command = [sys.executable, str(args.builder), "--variant", "E", "--language", "c,rust",
                       "--profile", "local-ship", "--source-root", candidate["source_root"],
                       "--out", str(args.out / fmt), "--rustc", args.rustc, "--no-smoke"]
            started = time.monotonic()
            with (args.out / (fmt + ".log")).open("w") as log:
                process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=1200)
            record = {"representation": fmt, "model": candidate, "command": command,
                      "exit_code": process.returncode, "wall_seconds": time.monotonic() - started}
            report["candidates"].append(record)
            if process.returncode:
                raise RuntimeError("measurement failed for " + fmt + "; inspect preserved log")
            path = args.out / fmt / "build.json"
            built = json.loads(path.read_text())
            if not built.get("complete"):
                raise ValueError("incomplete central builder report")
            record["build_report"] = str(path)
            record["build_report_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            record["smallest_observed"] = [{"id": e["id"], **min(e["artifacts"], key=lambda a: a["bytes"])}
                                           for e in built["engines"]]
            print(fmt + ": " + ", ".join(e["id"] + "=" + str(e["bytes"]) + "B"
                                         for e in record["smallest_observed"]), flush=True)
        report["complete"] = True
    except Exception as error:
        report["failure"] = str(error)
        raise
    finally:
        (args.out / "measurements.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
