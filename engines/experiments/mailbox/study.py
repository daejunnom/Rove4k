#!/usr/bin/env python3
"""Actual completed searches and observed Linux RAM; optional SMP regression.

Samples are local shared-host observations, not a speed/scaling/strength result.
With --workers, regenerate binaries from the selected frozen generated sources
using the same compiler arguments except the explicit worker count.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from generate import digest
from check import Engine, Board, FENS, ROOT, search


def resources(pid):
    fields = {}
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        name, _, value = line.partition(":")
        if name in ("VmRSS", "VmHWM", "VmSize", "Threads"):
            fields[name] = int(value.strip().split()[0])
    return fields


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--oracle", action="store_true")
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or args.out == ROOT or ROOT in args.out.parents:
        parser.error("--out must be new, absolute, outside the checkout")
    if not 1 <= args.depth <= 8 or not 1 <= args.repeat <= 10 or args.workers is not None and not 1 <= args.workers <= 8:
        parser.error("bounded local study requires depth 1..8, repeat 1..10, workers 1..8")
    args.out.mkdir(parents=True)
    build = json.loads(args.build.read_text())
    specs = [entry.copy() for entry in build["engines"] if entry["form"] == "dev"]
    report = {"scope": "actual Linux searches and observed resident memory on shared host; no speed/rating/scaling claim",
              "build_sha256": digest(args.build.read_bytes()), "workers": args.workers or build["workers"],
              "samples": [], "passed": False}
    for spec in specs:
        source = Path(spec["cwd"])
        for name, expected in spec["generated_sha256"].items():
            if digest((source / name).read_bytes()) != expected:
                raise RuntimeError("generated source changed since build evidence")
        if args.workers is not None:
            directory = args.out / spec["id"]
            directory.mkdir()
            for name in spec["generated_sha256"]:
                (directory / name).write_bytes((source / name).read_bytes())
            old = f"-DROVE_WORKERS={build['workers']}"
            if spec["compile"].count(old) != 1:
                raise RuntimeError("expected exactly one worker profile definition")
            command = [f"-DROVE_WORKERS={args.workers}" if item == old else item for item in spec["compile"]]
            subprocess.run(command, cwd=directory, check=True, capture_output=True, timeout=120)
            spec.update(command=[str(directory / "x")], cwd=str(directory), workers=args.workers,
                        startup_threads=args.workers + 1, max_threads=args.workers + 1,
                        compile=command, native_sha256=digest((directory / "x").read_bytes()))
    try:
        for repetition in range(args.repeat):
            # Alternate order, while retaining a record of every observation.
            ordered = specs if repetition % 2 == 0 else list(reversed(specs))
            for spec in ordered:
                for fixture, fen in enumerate(FENS):
                    label = f"{spec['id']}-r{repetition}-f{fixture}"
                    engine = Engine(spec, args.out, label, 30)
                    try:
                        engine.initialize()
                        startup = resources(engine.process.pid)
                        engine.position(fen)
                        state = json.loads(engine.dev("state", "{"))
                        actual = search(engine, Board.from_fen(fen), f"go depth {args.depth}", timeout=30)
                        memory = resources(engine.process.pid)
                        stats = json.loads(engine.dev("stats", "{"))
                        row = {"id": spec["id"], "layout": spec["layout"], "update": spec["update"],
                               "repeat": repetition, "fixture": fixture, "fen": fen,
                               "program_sha256": spec["native_sha256"], "state": state,
                               "startup_resources": startup, "completed_resources": memory,
                               "nodes": stats["nodes"], "completed_depth": stats["completed_depth"], **actual}
                        report["samples"].append(row)
                        engine.close()
                    finally:
                        if not engine.log.closed:
                            engine.terminate()
        if report["workers"] == 1:
            for fixture in range(len(FENS)):
                rows = [r for r in report["samples"] if r["fixture"] == fixture]
                semantic = [{k: r[k] for k in ("state", "bestmove", "info", "nodes", "completed_depth")} for r in rows]
                if any(s != semantic[0] for s in semantic[1:]):
                    raise AssertionError(f"single-worker actual search differs at fixture {fixture}")
        if args.oracle:
            manifest = args.out / "selected.json"
            manifest.write_text(json.dumps({"engines": specs}, indent=2) + "\n")
            subprocess.run([sys.executable, str(ROOT / "engines" / "tests" / "verify.py"),
                            "--manifest", str(manifest), "--out", str(args.out / "oracle")], check=True, timeout=600)
            report["oracle"] = {"path": str(args.out / "oracle" / "results.json"), "passed": True}
        report["passed"] = True
    finally:
        (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"out": str(args.out / "results.json"), "samples": len(report["samples"]),
                      "resident_hwm_kib": {s["id"]: sorted({r["completed_resources"]["VmHWM"] for r in report["samples"] if r["id"] == s["id"]}) for s in specs}}))


if __name__ == "__main__":
    main()
