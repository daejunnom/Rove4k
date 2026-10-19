#!/usr/bin/env python3
"""Optional A architecture experiment; all artifacts stay outside the checkout.

This does not replace the canonical A implementation. The exact source hashes,
compiler arguments and complete launcher bytes form this candidate's recipe.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
from minify import compact_source
from specialize import specialize_c
from pack import write_launchers
single_spec = importlib.util.spec_from_file_location("rove_tiny_a_pack_single", HERE / "pack_single.py")
single_module = importlib.util.module_from_spec(single_spec)
single_spec.loader.exec_module(single_module)
write_single = single_module.write_single
stream_spec = importlib.util.spec_from_file_location("rove_tiny_a_pack_stream", HERE / "pack_stream.py")
stream_module = importlib.util.module_from_spec(stream_spec)
stream_spec.loader.exec_module(stream_module)
write_stream = stream_module.write_stream
stitch_spec = importlib.util.spec_from_file_location("rove_tiny_a_stitch", HERE / "stitch.py")
stitch_module = importlib.util.module_from_spec(stitch_spec)
stitch_spec.loader.exec_module(stitch_module)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--tt-bits", type=int, default=18)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--no-pack", action="store_true")
    parser.add_argument("--runtime", choices=("posix", "futex"), default="posix")
    parser.add_argument("--board", choices=("standard", "rays", "forward", "generated"), default="standard")
    parser.add_argument("--single-unit", action="store_true", help="compare definitions-before-callers without duplicate module declarations")
    parser.add_argument("--strip-dev-counters", action="store_true", help="remove eight known shipping no-op counters, gated by full native byte identity")
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists():
        parser.error("--out must be a new absolute directory outside the checkout")
    if HERE.parents[2] == args.out or HERE.parents[2] in args.out.parents:
        parser.error("artifacts must stay outside the checkout")
    if not 1 <= args.workers <= 512 or not 8 <= args.tt_bits <= 28:
        parser.error("workers 1..512; TT bits 8..28")
    args.out.mkdir(parents=True)
    selected = ("tiny.h", {"standard": "board.c", "rays": "board-rays.c.in", "forward": "board-forward.c.in", "generated": "board-generated.c.in"}[args.board], "search.c",
                "main.c" if args.runtime == "posix" else "main-futex.c.in")
    sources = {name: (HERE / name).read_bytes() for name in selected}
    combined, layout = stitch_module.stitch(sources, selected, args.single_unit)
    if args.runtime == "futex":
        combined = b"#define _GNU_SOURCE\n" + combined
    flags = ["-std=c11", "-Os", "-pthread", f"-DWORKERS={args.workers}", f"-DTT_BITS={args.tt_bits}"]
    recipe = [args.cc, *flags, "-DDEV=0", "main.c", "-o", "x"]
    specialized, observations = specialize_c({"main.c": combined}, args.out / "preprocess", recipe, os.environ.copy())
    compact = compact_source(specialized["main.c"], "c")
    counter_recipe = None
    if args.strip_dev_counters:
        compact, counter_recipe = stitch_module.strip_dev_counters(compact)
    records = []
    original_native = None
    for form, source, dev in (("dev", combined, 1), ("original", combined, 0), ("compact", compact, 0)):
        directory = args.out / form
        directory.mkdir()
        (directory / "main.c").write_bytes(source)
        command = [args.cc, *flags, f"-DDEV={dev}", "main.c", "-o", "x"]
        subprocess.run(command, cwd=directory, check=True, timeout=120)
        binary = directory / "x"
        second = directory / "x.second"
        subprocess.run(command[:-1] + [second.name], cwd=directory, check=True, timeout=120)
        if second.read_bytes() != binary.read_bytes():
            raise RuntimeError(f"{form} native reproduction differs")
        if form == "original":
            original_native = binary.read_bytes()
        if form == "compact" and args.strip_dev_counters and binary.read_bytes() != original_native:
            raise RuntimeError("no-op diagnostic removal changed complete native bytes")
        entry = {"id": "tiny-A-" + form, "command": [str(binary)],
                 "cwd": str(directory), "profile": "dev" if dev else "shipping",
                 "workers": args.workers, "startup_threads": args.workers + 1,
                 "native_bytes": binary.stat().st_size, "native_sha256": sha(binary.read_bytes()),
                 "expected_program_sha256": sha(binary.read_bytes()),
                 "source_bytes": len(source), "source_sha256": sha(source),
                 "compile": command, "native_reproduced": True}
        if not dev and not args.no_pack:
            entry["launchers"] = write_launchers({"main.c": source}, directory / "packed", command=recipe)
            single_recipe = [args.cc, *flags, "-DDEV=0", "-x", "c", "-", "-o", "x"]
            entry["launchers"] += write_single(source, directory / "single", single_recipe)
            entry["launchers"] += write_stream(source, directory / "stream", single_recipe)
            # Regenerate complete wrappers in a separate tree and compare bytes,
            # including shebang, archive metadata and compiler recipe.
            repeated = write_launchers({"main.c": source}, directory / "repeated", command=recipe)
            repeated += write_single(source, directory / "single-repeated", single_recipe)
            repeated += write_stream(source, directory / "stream-repeated", single_recipe)
            for first, other in zip(entry["launchers"], repeated):
                if Path(first["path"]).read_bytes() != Path(other["path"]).read_bytes():
                    raise RuntimeError("complete launcher reproduction differs")
                first["reproduced"] = True
        records.append(entry)
    report = {"candidate": "A source-first mailbox architecture experiment", "runtime": args.runtime, "board": args.board,
              "source_layout": layout,
              "counter_recipe": counter_recipe,
              "eligible_4k": False, "source_sha256": {name: sha(data) for name, data in sources.items()},
              "recipe_sha256": {str(path.relative_to(HERE.parents[2])): sha(path.read_bytes()) for path in
                                  (HERE / "build.py", HERE / "pack_single.py", HERE / "pack_stream.py", HERE / "stitch.py", HERE.parents[1] / "scripts/minify.py",
                                   HERE.parents[1] / "scripts/specialize.py", HERE.parents[1] / "scripts/pack.py")},
              "compiler": subprocess.check_output([args.cc, "--version"], text=True).splitlines()[0],
              "preprocessor": observations, "engines": records}
    (args.out / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    candidates = [(engine, artifact) for engine in records for artifact in engine.get("launchers", [])]
    selected = None
    validation_engines = list(records)
    if candidates:
        source_engine, selected = min(candidates, key=lambda pair: pair[1]["bytes"])
        validation_engines.append({"id": "tiny-A-selected", "command": [selected["path"]],
                                   "cwd": str(Path(selected["path"]).parent), "profile": "shipping",
                                   "workers": args.workers, "startup_threads": args.workers + 1,
                                   "startup_timeout": 60, "expected_program_sha256": selected["sha256"],
                                   "selected_from": source_engine["id"], "selected_artifact": selected})
    validation = {**report, "engines": validation_engines, "selected": selected}
    (args.out / "validation-manifest.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps({"out": str(args.out), "forms": [{k: r[k] for k in ("id", "native_bytes", "source_bytes")} for r in records],
                      "minimum_complete_bytes": min((p["bytes"] for r in records for p in r.get("launchers", [])), default=None)}))


if __name__ == "__main__":
    main()
