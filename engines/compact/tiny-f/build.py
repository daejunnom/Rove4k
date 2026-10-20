#!/usr/bin/env python3
"""Freeze every TinyF producer/source input, then build outside the checkout.

TinyF owns a full-depth MTD(f) search. Only the admitted TinyA board and startup
runtime are reused; the overlay never changes their working-tree source files.
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
ROOT = HERE.parents[2]
INPUTS = (
    "engines/compact/tiny-f/build.py", "engines/compact/tiny-f/overlay.py", "engines/compact/tiny-f/search.c",
    "engines/compact/tiny-a/tiny.h", "engines/compact/tiny-a/board-generated.c.in", "engines/compact/tiny-a/main.c",
    "engines/compact/tiny-a/stitch.py", "engines/compact/tiny-a/pack_single.py", "engines/compact/tiny-a/pack_stream.py",
    "engines/scripts/minify.py", "engines/scripts/specialize.py", "engines/scripts/pack.py",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(out):
    data = {name: (ROOT / name).read_bytes() for name in INPUTS}
    for name, content in data.items():
        if (ROOT / name).read_bytes() != content:
            raise RuntimeError("producer/source changed during admission: " + name)
    for name, content in data.items():
        target = out / "recipe" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    manifest = {name: {"bytes": len(content), "sha256": sha(content),
                       "lf_sha256": sha(content.replace(b"\r\n", b"\n"))}
                for name, content in data.items()}
    (out / "recipe/inputs.json").write_text(json.dumps(manifest, indent=2)+"\n")


def run(args):
    frozen = json.loads((ROOT / "inputs.json").read_text())
    if set(frozen) != set(INPUTS):
        raise RuntimeError("frozen producer input set differs")
    for name, record in frozen.items():
        if sha((ROOT / name).read_bytes()) != record["sha256"]:
            raise RuntimeError("frozen input changed: " + name)
    overlay = load("tiny_f_overlay", HERE / "overlay.py")
    stitch = load("tiny_f_stitch", ROOT / "engines/compact/tiny-a/stitch.py")
    minify = load("tiny_f_minify", ROOT / "engines/scripts/minify.py")
    specialize = load("tiny_f_specialize", ROOT / "engines/scripts/specialize.py")
    stream = load("tiny_f_pack_stream", ROOT / "engines/compact/tiny-a/pack_stream.py")
    original = {name: (ROOT / "engines/compact/tiny-a" / name).read_bytes() for name in overlay.EXPECTED}
    source = overlay.transform(original, (HERE / "search.c").read_bytes())
    structure=None
    if args.structure=="compact":
        source,structure=overlay.co_design(source)
    selected = ("tiny.h", "board-generated.c.in", "search.c", "main.c")
    combined, layout = stitch.stitch(source, selected, True)
    flags = ["-std=c11", "-Os", "-pthread", f"-DWORKERS={args.workers}", f"-DTT_BITS={args.tt_bits}", f"-DPLY={args.ply}"]
    compile_recipe = [args.cc, *flags, "-DDEV=0", "main.c", "-o", "x"]
    specialized, observations = specialize.specialize_c({"main.c": combined}, args.out / "preprocess", compile_recipe, os.environ.copy())
    compact = minify.compact_source(specialized["main.c"], "c")
    compact, counter_recipe = overlay.strip_counters(compact)
    records = []
    original_native = None
    for form, content, dev in (("dev", combined, 1), ("original", combined, 0), ("compact", compact, 0)):
        directory = args.out / form
        directory.mkdir()
        (directory / "main.c").write_bytes(content)
        command = [args.cc, *flags, f"-DDEV={dev}", "main.c", "-o", "x"]
        subprocess.run(command, cwd=directory, check=True, timeout=120)
        subprocess.run(command[:-1]+["x.second"], cwd=directory, check=True, timeout=120)
        native = (directory / "x").read_bytes()
        if native != (directory / "x.second").read_bytes():
            raise RuntimeError(form + " native reproduction differs")
        if form == "original":
            original_native = native
        if form == "compact" and native != original_native:
            raise RuntimeError("known no-op diagnostic removal changed native bytes")
        record = {"id": "tiny-F-"+form, "command": [str(directory / "x")], "cwd": str(directory),
                  "profile": "dev" if dev else "shipping", "workers": args.workers,
                  "startup_threads": args.workers+1, "native_bytes": len(native), "native_sha256": sha(native),
                  "expected_program_sha256": sha(native), "source_bytes": len(content), "source_sha256": sha(content),
                  "compile": command, "native_reproduced": True}
        if not dev and not args.no_pack:
            recipe = [args.cc, *flags, "-DDEV=0", "-x", "c", "-", "-o", "x"]
            record["launchers"] = stream.write_stream(content, directory / "stream", recipe)
            repeated = stream.write_stream(content, directory / "stream-repeated", recipe)
            for first, second in zip(record["launchers"], repeated):
                if Path(first["path"]).read_bytes() != Path(second["path"]).read_bytes():
                    raise RuntimeError("complete launcher reproduction differs")
                first["reproduced"] = True
        records.append(record)
    candidates = [(record, artifact) for record in records for artifact in record.get("launchers", [])]
    chosen = min(candidates, key=lambda pair: pair[1]["bytes"]) if candidates else None
    report = {"candidate": "F full-depth MTD source-first mailbox experiment", "variant": "F",
              "contract": {"tt": "full-key coherent try-lock single bound; exact horizon; QS=0",
                           "search": "full-depth PVS/QS; no selective LMR",
                           "correction": "converged quiet root residual trains actual quiet ordering only",
                           "root": "attaining lower-bound witness; publish only converged completed iterations",
                           "parallel": "independent fixed startup workers; shared TT/deadline/cancellation"},
              "source_layout": layout, "structure": structure, "counter_recipe": counter_recipe,
              "recipe_inputs": frozen, "compiler": subprocess.check_output([args.cc,"--version"],text=True).splitlines()[0],
              "fixed_flags": flags, "preprocessor": observations,
              "engines": records, "selected": chosen[1] if chosen else None,
              "eligible_4k": bool(chosen and chosen[1]["bytes"] <= 4096)}
    (args.out / "build.json").write_text(json.dumps(report, indent=2)+"\n")
    validation = list(records)
    if chosen:
        engine, artifact = chosen
        validation.append({"id": "tiny-F-selected", "command": [artifact["path"]],
                           "cwd": str(Path(artifact["path"]).parent), "profile": "shipping",
                           "workers": args.workers, "startup_threads": args.workers+1,
                           "startup_timeout": 60, "expected_program_sha256": artifact["sha256"],
                           "selected_from": engine["id"], "selected_artifact": artifact})
    (args.out / "validation-manifest.json").write_text(json.dumps({**report,"engines":validation},indent=2)+"\n")
    print(json.dumps({"out":str(args.out),"minimum_complete_bytes":chosen[1]["bytes"] if chosen else None,
                      "eligible_4k":report["eligible_4k"],"forms":[{key:record[key] for key in ("id","native_bytes","source_bytes")} for record in records]}),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--tt-bits", type=int, default=18)
    parser.add_argument("--ply", type=int, default=128)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--no-pack", action="store_true")
    parser.add_argument("--structure", choices=("baseline","compact"), default="baseline")
    parser.add_argument("--execute-frozen", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.out.is_absolute() or (ROOT == args.out or ROOT in args.out.parents):
        parser.error("--out must be absolute and outside the checkout")
    if not 1 <= args.workers <= 512 or not 8 <= args.tt_bits <= 28 or not 4 <= args.ply <= 128:
        parser.error("workers 1..512; TT bits 8..28; ply 4..128")
    if args.execute_frozen:
        if args.out / "recipe" != ROOT:
            parser.error("frozen execution requires the owned output recipe")
        run(args)
    else:
        if args.out.exists():
            parser.error("--out must be a new directory")
        args.out.mkdir(parents=True)
        snapshot(args.out)
        subprocess.run([sys.executable,"-I","-B",str(args.out / "recipe/engines/compact/tiny-f/build.py"),
                        *sys.argv[1:],"--execute-frozen"],check=True)


if __name__ == "__main__":
    main()
