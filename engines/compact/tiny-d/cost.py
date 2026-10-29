#!/usr/bin/env python3
"""Recover a function/storage cost map without changing selected ELF bytes.

Relink a selected recipe with symbol metadata retained, then strip only section
metadata using the same native transformation. The map is accepted only when
the resulting whole ELF is byte identical to the selected runtime artifact.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.is_absolute():
        args.out = args.out.resolve()
    if not args.out.is_absolute() or args.out.exists() or HERE.parents[2] in args.out.parents:
        parser.error("--out must be a new absolute directory outside Git")
    args.out.mkdir(parents=True)
    recipe = args.build.parent / "sources/build.py"
    spec = importlib.util.spec_from_file_location("tiny_d_frozen_build", recipe)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    report = []
    for record in json.loads(args.build.read_text())["engines"]:
        if record["profile"] != "shipping":
            continue
        output = args.out / record["id"]
        command = record["compile"][:-1] + [str(output)]
        command = [arg.replace("--build-id=none,-s,", "--build-id=none,") for arg in command]
        command.insert(1, "-fstack-usage")
        subprocess.run(command, check=True, timeout=120)
        stripped = builder.strip_sections(output.read_bytes())
        if hashlib.sha256(stripped).hexdigest() != record["native_sha256"]:
            raise RuntimeError("symbol cost map changes actual native bytes")
        listing = subprocess.check_output(["nm", "--print-size", "--size-sort", str(output)], text=True)
        sections = subprocess.check_output(["size", "-A", str(output)], text=True)
        (args.out / (record["id"] + ".symbols.txt")).write_text(listing)
        (args.out / (record["id"] + ".sections.txt")).write_text(sections)
        symbols = []
        for line in listing.splitlines():
            fields = line.split()
            if len(fields) == 4:
                address, size, kind, name = fields
                symbols.append({"name": name, "kind": kind, "bytes": int(size, 16), "address": int(address, 16)})
        stack_reports = {}
        for path in args.out.glob(output.name + "*.su"):
            stack_reports[path.name] = path.read_text()
        report.append({"id": record["id"], "native_sha256": record["native_sha256"],
                       "exact_runtime_byte_identity": True, "native_bytes": len(stripped),
                       "symbols": symbols, "sections": sections, "compiler_stack_usage": stack_reports})
    (args.out / "cost.json").write_text(json.dumps({"forms": report}, indent=2) + "\n")
    print(json.dumps({"forms": [{"id": r["id"], "native_bytes": r["native_bytes"],
                   "largest_text": [s for s in reversed(r["symbols"]) if s["kind"].lower() == "t"][:8]}
                  for r in report]}))


if __name__ == "__main__":
    main()
