#!/usr/bin/env python3
"""Compile/run C search semantic contracts with bounded external evidence."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--variants", default="BCF")
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    output = args.out.resolve()
    if ROOT == output or ROOT in output.parents:
        parser.error("--out must be outside the checkout")
    if not args.variants or any(v not in "BCF" for v in args.variants) or not 1 <= args.workers <= 8:
        parser.error("supported variants B/C/F and 1..8 local workers")
    output.mkdir(parents=True, exist_ok=True)
    if sys.platform == "linux":
        import resource
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    sources = [ROOT / p for p in ("engines/tests/search_contract.c", "engines/c/search.c",
                                  "engines/c/board.c", "engines/c/rove.h", "engines/c/parallel.h")]
    def fingerprint():
        return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    report = {"sources": fingerprint(), "workers": args.workers, "records": [], "passed": True}
    for variant in args.variants:
        binary = output / ("contract-" + variant)
        command = [args.cc, "-std=c11", "-O2", "-pthread", "-DROVE_VARIANT=" + str(ord(variant)-64),
                   "-DROVE_WORKERS=" + str(args.workers), "-DROVE_TT_BITS=18", "-DROVE_DEV=0",
                   str(sources[0]), str(ROOT / "engines/c/board.c"), "-o", str(binary)]
        started = time.monotonic()
        record = {"variant": variant, "compile_command": command}
        try:
            compile_result = subprocess.run(command, cwd=output, text=True, capture_output=True, timeout=60)
            record.update(compile_returncode=compile_result.returncode, compile_stdout=compile_result.stdout,
                          compile_stderr=compile_result.stderr)
            if compile_result.returncode:
                raise RuntimeError("C semantic contract compilation failed")
            record["program_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
            result = subprocess.run([str(binary)], cwd=output, text=True, capture_output=True, timeout=45)
            record.update(run_returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
            if result.returncode:
                raise RuntimeError("C semantic contract failed")
            if fingerprint() != report["sources"]:
                raise RuntimeError("source changed during semantic contract run; frozen-source claim unavailable")
            record["status"] = "pass"
        except Exception as error:
            record.update(status="fail", error=f"{type(error).__name__}: {error}")
            report["passed"] = False
        record["elapsed_seconds"] = time.monotonic() - started
        report["records"].append(record)
        (output / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(record), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
