#!/usr/bin/env python3
"""Freeze shared black-box validator bytes, then test the two separate builds."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT == args.out or ROOT in args.out.parents:
        parser.error("--out must be a new external absolute directory")
    validator = args.out / "recipe/engines/tests"
    validator.mkdir(parents=True)
    hashes = {}
    for name in ("verify.py", "chess_oracle.py"):
        data = (HERE.parents[1] / "tests" / name).read_bytes()
        (validator / name).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    report = {"validator_sha256": hashes, "scope": "shared quick black-box suite; frozen unchanged board has separate deeper oracle evidence", "builds": [], "passed": False}
    for build in args.build:
        manifest = json.loads(build.read_bytes())
        variant = manifest["features"]["variant"]
        output = args.out / variant
        command = [sys.executable, "-B", str(validator / "verify.py"), "--manifest", str(build), "--out", str(output), "--quick"]
        result = subprocess.run(command)
        entry = {"variant": variant, "build_sha256": hashlib.sha256(build.read_bytes()).hexdigest(), "command": command, "exit_code": result.returncode, "results": str(output / "results.json")}
        report["builds"].append(entry)
        (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
        if result.returncode:
            raise SystemExit(result.returncode)
    report["passed"] = True
    (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
