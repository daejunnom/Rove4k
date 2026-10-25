#!/usr/bin/env python3
"""Freeze runtime inputs, build all four F policies, then compare real searches."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/"engines/scripts"))
MODES = (("paired", "previous"), ("paired", "parity"),
         ("single", "previous"), ("single", "parity"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--rustc", default="rustc")
    parser.add_argument("--profile", choices=("local-dev", "local-smp"), default="local-smp")
    parser.add_argument("--pack", action="store_true", help="also measure and run complete source/native launchers")
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        parser.error("--out must be a new directory outside the repository")
    out.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location("f_campaign_build", ROOT/"engines/scripts/build.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    inputs = {}
    for language in ("c", "rust"):
        inputs.update(build.source_files(language, ROOT/"engines"))
    frozen = out/"source"
    build.write_files(inputs, frozen)
    hashes = {name:hashlib.sha256(data).hexdigest() for name,data in sorted(inputs.items())}
    report = {"schema": 1, "inputs": hashes, "commands": [], "complete": False}
    manifests = []
    builder=ROOT/"engines/scripts/build.py"
    try:
        for table, guess in MODES:
            label = table+"-"+guess
            destination = out/label
            command = [sys.executable, str(builder),
                       "--source-root", str(frozen), "--out", str(destination),
                       "--profile", args.profile, "--languages", "c,rust", "--variants", "F",
                       "--parallel", "loose", "--f-tt", table, "--f-guess", guess,
                       "--cc", args.cc, "--rustc", args.rustc, "--reproduce"]
            if not args.pack:
                command.append("--no-pack")
            report["commands"].append(command)
            subprocess.run(command, check=True, cwd=ROOT)
            if label=="paired-previous":builder=destination/"recipe/engines/scripts/build.py"
            manifests += ["--manifest", label+"="+str(destination/"build.json")]
        command = [sys.executable, str(ROOT/"engines/experiments/f/compare.py"),
                   "--out", str(out/"verification"), *manifests]
        report["commands"].append(command)
        subprocess.run(command, check=True, cwd=ROOT)
        report["complete"] = True
    finally:
        (out/"campaign.json").write_text(json.dumps(report, indent=2)+"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
