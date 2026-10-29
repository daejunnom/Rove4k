#!/usr/bin/env python3
"""Compile focused contracts against the build's actual frozen TinyB DEV core."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    if not args.out.is_absolute():
        parser.error("--out must be absolute")
    args.out = args.out.resolve()
    if not args.out.is_absolute() or args.out.exists() or HERE.parents[2] in args.out.parents:
        parser.error("--out must be a new absolute directory outside the checkout")
    args.out.mkdir(parents=True)
    combined = (args.build / "combined.c").read_bytes()
    contract = (HERE / "contract.c").read_bytes()
    source = b"#define main tiny_b_protocol_main\n" + combined + b"\n#undef main\n" + contract
    (args.out / "contract.c").write_bytes(source)
    report = {"source_sha256": hashlib.sha256(combined).hexdigest(), "contract_sha256": hashlib.sha256(contract).hexdigest(), "forms": []}
    for name, flags in (("optimized", ["-O2"]), ("asan", ["-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"])):
        binary = args.out / name
        # 20 bits keeps the watched child away from a known legitimate later
        # descendant collision. It proves actual published depth, not slot luck.
        command = [args.cc, "-std=c11", "-pthread", "-DDEV=1", "-DWORKERS=2", "-DTT_BITS=20", *flags, str(args.out / "contract.c"), "-o", str(binary)]
        subprocess.run(command, check=True, timeout=120)
        result = subprocess.run([str(binary)], text=True, capture_output=True, timeout=60)
        (args.out / (name + ".stdout.txt")).write_text(result.stdout)
        (args.out / (name + ".stderr.txt")).write_text(result.stderr)
        entry = {"id": name, "command": command, "returncode": result.returncode,
                 "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(), "stdout": result.stdout, "stderr": result.stderr}
        report["forms"].append(entry)
        (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(name + " actual-core semantic contract failed; see external results")
    report["passed"] = True
    (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "out": str(args.out), "forms": [form["id"] for form in report["forms"]]}))


if __name__ == "__main__":
    main()
