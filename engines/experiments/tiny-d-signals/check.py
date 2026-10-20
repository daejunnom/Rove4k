#!/usr/bin/env python3
"""Run shared independent chess/protocol checks on actual D native/whole ELFs.

The harness and oracle are copied to the external report tree before execution.
The report records both exact binary and validation-source hashes. This script
does not infer correctness from scalar/HQ adapter parity alone.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
TESTS = HERE.parents[1] / "tests"


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
        parser.error("--out must be a new absolute directory outside the checkout")
    args.out.mkdir(parents=True)
    frozen = args.out / "validation/engines/tests"
    frozen.mkdir(parents=True)
    for name in ("verify.py", "chess_oracle.py"):
        shutil.copyfile(TESTS / name, frozen / name)
    build = json.loads(args.build.read_text())
    specs = []
    for record in build["engines"]:
        path = Path(record["command"][0])
        if sha(path) != record["native_sha256"]:
            raise RuntimeError("native hash drift: " + record["id"])
        spec = {**record, "expected_program_sha256": sha(path), "max_threads": record["startup_threads"]}
        specs.append(spec)
        for launcher in record["launchers"]:
            path = Path(launcher["path"])
            if sha(path) != launcher["sha256"]:
                raise RuntimeError("whole ELF hash drift: " + record["id"])
            specs.append({**spec, "id": record["id"] + "-self", "command": [str(path)],
                          "expected_program_sha256": sha(path)})
    manifest = args.out / "manifest.json"
    manifest.write_text(json.dumps({"engines": specs}, indent=2) + "\n")
    command = [sys.executable, str(frozen / "verify.py"), "--manifest", str(manifest),
               "--out", str(args.out / "checks"), "--match", "tiny-D-signals-scalar-dev,tiny-D-signals-hq-dev"]
    result = subprocess.run(command, timeout=300)
    record = {"build_manifest": str(args.build), "build_manifest_sha256": sha(args.build),
              "validation_sha256": {name: sha(frozen / name) for name in ("verify.py", "chess_oracle.py")},
              "command": command, "exit_code": result.returncode}
    (args.out / "check.json").write_text(json.dumps(record, indent=2) + "\n")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
