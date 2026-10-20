#!/usr/bin/env python3
"""Build independent TinyB forms from frozen strict source inputs, outside Git."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
BASE_FILES = ("tiny.h", "board-generated.c.in", "search.c", "main.c",
              "stitch.py", "pack_single.py", "pack_stream.py")
OWN_FILES = ("build.py", "generate.py", "attackers.c.in", "search.c", "check.py", "contract.c", "qualify.py", "test_generate.py", "README.md")
SCRIPTS = ("minify.py", "specialize.py", "pack.py")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--tt-bits", type=int, default=18)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--no-pack", action="store_true")
    args = parser.parse_args()
    if not args.out.is_absolute():
        parser.error("--out must be absolute")
    args.out = args.out.resolve()
    if not args.out.is_absolute() or args.out.exists() or HERE.parents[2] == args.out or HERE.parents[2] in args.out.parents:
        parser.error("--out must be a new absolute directory outside the checkout")
    if not 1 <= args.workers <= 512 or not 8 <= args.tt_bits <= 28:
        parser.error("workers 1..512; TT bits 8..28")
    args.out.mkdir(parents=True)
    # Freeze every actual producer before importing/executing it. Root and
    # parallel agents can now change other source without mutating this build.
    frozen = args.out / "recipe" / "engines" / "compact" / "tiny-b"
    inputs = {"engines/compact/tiny-b/" + name: (HERE / name).read_bytes() for name in OWN_FILES}
    inputs.update({"engines/compact/tiny-b/base/" + name: (HERE / "base" / name).read_bytes() for name in BASE_FILES})
    inputs.update({"engines/scripts/" + name: (HERE.parents[1] / "scripts" / name).read_bytes() for name in SCRIPTS})
    for relative, data in inputs.items():
        target = args.out / "recipe" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    overlay = load("tiny_b_overlay", frozen / "generate.py")
    stitch = load("tiny_b_stitch", frozen / "base" / "stitch.py")
    minify = load("tiny_b_minify", frozen.parents[1] / "scripts" / "minify.py")
    specialize = load("tiny_b_specialize", frozen.parents[1] / "scripts" / "specialize.py")
    pack = load("tiny_b_pack", frozen.parents[1] / "scripts" / "pack.py")
    single = load("tiny_b_single", frozen / "base" / "pack_single.py")
    stream = load("tiny_b_stream", frozen / "base" / "pack_stream.py")
    sources = overlay.sources()
    combined, layout = stitch.stitch(sources, ("tiny.h", "board-generated.c.in", "search.c", "main.c"), True)
    (args.out / "combined.c").write_bytes(combined)
    flags = ["-std=c11", "-Os", "-pthread", f"-DWORKERS={args.workers}", f"-DTT_BITS={args.tt_bits}"]
    recipe = [args.cc, *flags, "-DDEV=0", "main.c", "-o", "x"]
    specialized, observations = specialize.specialize_c({"main.c": combined}, args.out / "preprocess", recipe, os.environ.copy())
    compact, counters = overlay.strip_counters(minify.compact_source(specialized["main.c"], "c"))
    records = []
    original_native = None
    for form, source, dev in (("dev", combined, 1), ("original", combined, 0), ("compact", compact, 0)):
        directory = args.out / form
        directory.mkdir()
        (directory / "main.c").write_bytes(source)
        command = [args.cc, *flags, f"-DDEV={dev}", "main.c", "-o", "x"]
        subprocess.run(command, cwd=directory, check=True, timeout=120)
        binary = directory / "x"
        subprocess.run(command[:-1] + ["x.second"], cwd=directory, check=True, timeout=120)
        data = binary.read_bytes()
        if (directory / "x.second").read_bytes() != data:
            raise RuntimeError(form + " native reproduction differs")
        if form == "original":
            original_native = data
        if form == "compact" and data != original_native:
            raise RuntimeError("specialization/known no-op removal changed complete native bytes")
        entry = {"id": "tiny-B-" + form, "command": [str(binary)], "cwd": str(directory),
                 "profile": "dev" if dev else "shipping", "workers": args.workers,
                 "startup_threads": args.workers + 1, "native_bytes": len(data),
                 "native_sha256": sha(data), "expected_program_sha256": sha(data),
                 "source_bytes": len(source), "source_sha256": sha(source),
                 "compile": command, "native_reproduced": True}
        if not dev and not args.no_pack:
            stdin_recipe = [args.cc, *flags, "-DDEV=0", "-x", "c", "-", "-o", "x"]
            entry["launchers"] = pack.write_launchers({"main.c": source}, directory / "packed", command=recipe)
            entry["launchers"] += single.write_single(source, directory / "single", stdin_recipe)
            entry["launchers"] += stream.write_stream(source, directory / "stream", stdin_recipe)
            repeated = pack.write_launchers({"main.c": source}, directory / "repeated", command=recipe)
            repeated += single.write_single(source, directory / "single-repeated", stdin_recipe)
            repeated += stream.write_stream(source, directory / "stream-repeated", stdin_recipe)
            for first, other in zip(entry["launchers"], repeated):
                if Path(first["path"]).read_bytes() != Path(other["path"]).read_bytes():
                    raise RuntimeError("complete launcher reproduction differs")
                first["reproduced"] = True
        records.append(entry)
    report = {"candidate": "B source-first incremental-bitboard/legal-SEE/singular architecture", "board": "generated",
              "source_layout": layout, "counter_recipe": counters,
              "source_sha256": {name: sha(data) for name, data in sources.items()},
              "recipe_sha256": {name: sha(data) for name, data in inputs.items()},
              "compiler": subprocess.check_output([args.cc, "--version"], text=True).splitlines()[0],
              "preprocessor": observations, "engines": records}
    candidates = [(engine, artifact) for engine in records for artifact in engine.get("launchers", [])]
    selected = None
    validation_engines = list(records)
    if candidates:
        source_engine, selected = min(candidates, key=lambda pair: pair[1]["bytes"])
        validation_engines.append({"id": "tiny-B-selected", "command": [selected["path"]],
                                   "cwd": str(Path(selected["path"]).parent), "profile": "shipping",
                                   "workers": args.workers, "startup_threads": args.workers + 1,
                                   "startup_timeout": 60, "expected_program_sha256": selected["sha256"],
                                   "selected_from": source_engine["id"], "selected_artifact": selected})
    report["eligible_4k"] = selected is not None and selected["bytes"] <= 4096
    (args.out / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.out / "validation-manifest.json").write_text(json.dumps({**report, "engines": validation_engines, "selected": selected}, indent=2) + "\n")
    print(json.dumps({"out": str(args.out), "forms": [{k: r[k] for k in ("id", "native_bytes", "source_bytes")} for r in records],
                      "minimum_complete_bytes": selected["bytes"] if selected else None}))


if __name__ == "__main__":
    main()
