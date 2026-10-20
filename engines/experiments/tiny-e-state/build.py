#!/usr/bin/env python3
"""Freeze and build the two TinyE shipping-state forms outside Git."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ENGINES = HERE.parents[1]
ROOT = HERE.parents[2]
EOL_EQUIVALENT_INPUT = "engines/compact/tiny-ce/core/provenance.json"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha(data):
    return hashlib.sha256(data).hexdigest()


def admit_input(name, data, expected):
    """Keep literal bindings except the two audited provenance JSON EOL forms."""
    raw = {"bytes": len(data), "sha256": sha(data), "crlf_count": data.count(b"\r\n"),
           "lone_cr_count": data.count(b"\r") - data.count(b"\r\n")}
    equivalent = expected.get("eol_equivalence")
    if equivalent is None:
        if raw["bytes"] != expected["bytes"] or raw["sha256"] != expected["sha256"]:
            raise ValueError("frozen TinyE input changed: " + name)
        return {"raw": raw, "identity": {"bytes": raw["bytes"], "sha256": raw["sha256"]},
                "admission": "literal", "normalization": "none"}
    if name != EOL_EQUIVALENT_INPUT or equivalent["normalization"] != "CRLF_to_LF_only":
        raise ValueError("unsupported TinyE EOL equivalence: " + name)
    normalized = data.replace(b"\r\n", b"\n")
    identity = {"bytes": len(normalized), "sha256": sha(normalized)}
    if raw["lone_cr_count"] or identity != equivalent["normalized_identity"]:
        raise ValueError("frozen TinyE EOL content changed: " + name)
    original = {"bytes": expected["bytes"], "sha256": expected["sha256"],
                "crlf_count": equivalent["original_crlf_count"]}
    observed = {key: raw[key] for key in original}
    if observed not in (original, equivalent["verified_lf_variant"]):
        raise ValueError("unverified TinyE EOL byte variant: " + name)
    return {"raw": raw, "identity": identity, "admission": "verified-provenance-EOL-equivalence",
            "normalization": "CRLF_to_LF_only"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--form", choices=("baseline", "state"), required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--tt-bits", type=int, default=18)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--no-pack", action="store_true")
    args = parser.parse_args()
    args.variant = "E"
    ce = ENGINES / "compact/tiny-ce"
    if not args.out.is_absolute():
        parser.error("--out must be a new absolute directory outside the checkout")
    args.out = args.out.resolve()
    if args.out.exists() or ROOT == args.out or ROOT in args.out.parents or any((p / ".git").exists() for p in args.out.parents):
        parser.error("--out must be a new absolute directory outside the checkout")
    if not 1 <= args.workers <= 512 or not 8 <= args.tt_bits <= 28:
        parser.error("workers 1..512; TT bits 8..28")
    args.out.mkdir(parents=True)
    # Freeze the exact recipe tree before importing helpers. Both input hashes
    # and all producer bytes survive without reading a later mutable checkout.
    bindings = json.loads((HERE / "inputs.json").read_bytes())
    frozen = {}
    input_admission = {}
    for name, expected in bindings.items():
        data = (ROOT / name).read_bytes()
        input_admission[name] = admit_input(name, data, expected)
        frozen[name] = data
    for name in ("build.py", "generate.py", "inputs.json", "check.py", "contract.c", "test_generate.py"):
        path = HERE / name
        frozen[str(path.relative_to(ROOT))] = path.read_bytes()
    recipe_root = args.out / "recipe"
    for name, data in frozen.items():
        dest = recipe_root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    recipe_engines = recipe_root / "engines"
    recipe_here = recipe_engines / "compact/tiny-ce"
    state = load("tiny_e_state_overlay", recipe_engines / "experiments/tiny-e-state/generate.py")
    sys.path.insert(0, str(recipe_engines / "scripts"))
    minifier = load("tiny_ce_minify", recipe_engines / "scripts/minify.py")
    specializer = load("tiny_ce_specialize", recipe_engines / "scripts/specialize.py")
    packer = load("tiny_ce_pack", recipe_engines / "scripts/pack.py")
    single = load("tiny_ce_single", recipe_engines / "compact/tiny-a/pack_single.py")
    stream = load("tiny_ce_stream", recipe_engines / "compact/tiny-a/pack_stream.py")
    stitch = load("tiny_ce_stitch", recipe_engines / "compact/tiny-a/stitch.py")
    generate = load("tiny_ce_generate", recipe_here / "generate.py")
    selected = ("tiny.h", "board.c", "search.c", "main.c")
    sources = {name: (recipe_here / "core" / name).read_bytes() for name in selected}
    provenance = json.loads((recipe_here / "core/provenance.json").read_bytes())
    entries = provenance["inputs"]
    if len(entries) != len(selected) or {entry["frozen"] for entry in entries} != {"core/" + name for name in selected}:
        raise ValueError("frozen TinyA core manifest shape changed")
    for entry in entries:
        data = sources[entry["frozen"].removeprefix("core/")]
        if sha(data) != entry["sha256"] or len(data) != entry["bytes"]:
            raise ValueError("frozen TinyA core bytes changed: " + entry["frozen"])
    combined, layout = stitch.stitch(sources, selected, True)
    combined, features = generate.overlay(combined, args.variant,
                                        (recipe_here / (args.variant.lower() + "-eval.c.in")).read_bytes(),
                                        (recipe_here / "frozen.json").read_bytes())
    combined, state_record = state.overlay(combined, args.form)
    flags = ["-std=c11", "-Os", "-pthread", f"-DWORKERS={args.workers}", f"-DTT_BITS={args.tt_bits}"]
    if args.variant == "C":
        flags.append("-mavx2")
    recipe = [args.cc, *flags, "-DDEV=0", "main.c", "-o", "x"]
    specialized, observations = specializer.specialize_c({"main.c": combined}, args.out / "preprocess", recipe, os.environ.copy())
    compact = minifier.compact_source(specialized["main.c"], "c")
    compact, counter_recipe = stitch.strip_dev_counters(compact)
    if args.form == "state" and (b"p->v" in compact or b"int v;" in compact):
        raise ValueError("shipping specialization retained the removed HCE cache")
    records = []
    original_native = None
    for form, source, dev in (("dev", combined, 1), ("original", combined, 0), ("compact", compact, 0)):
        directory = args.out / form
        directory.mkdir()
        (directory / "main.c").write_bytes(source)
        command = [args.cc, *flags, f"-DDEV={dev}", "main.c", "-o", "x"]
        subprocess.run(command, cwd=directory, check=True, timeout=120)
        subprocess.run(command[:-1] + ["x.second"], cwd=directory, check=True, timeout=120)
        binary = directory / "x"
        if (directory / "x.second").read_bytes() != binary.read_bytes():
            raise RuntimeError("independent native compilation differs")
        if form == "original":
            original_native = binary.read_bytes()
        if form == "compact" and binary.read_bytes() != original_native:
            raise RuntimeError("diagnostic stripping or lexical compaction changed complete native bytes")
        entry = {"id": "tiny-" + args.variant + "-" + form, "command": [str(binary)], "cwd": str(directory),
                 "profile": "dev" if dev else "shipping", "workers": args.workers,
                 "startup_threads": args.workers + 1, "native_bytes": binary.stat().st_size,
                 "native_sha256": sha(binary.read_bytes()), "expected_program_sha256": sha(binary.read_bytes()),
                 "source_bytes": len(source), "source_sha256": sha(source), "compile": command,
                 "native_reproduced": True}
        if not dev and not args.no_pack:
            stdin_recipe = [args.cc, *flags, "-DDEV=0", "-x", "c", "-", "-o", "x"]
            subprocess.run(stdin_recipe[:-1] + ["x.stdin"], cwd=directory, input=source, check=True, timeout=120)
            subprocess.run(stdin_recipe[:-1] + ["x.stdin.second"], cwd=directory, input=source, check=True, timeout=120)
            stdin_binary = (directory / "x.stdin").read_bytes()
            if stdin_binary != (directory / "x.stdin.second").read_bytes():
                raise RuntimeError("stdin compiler recipe reproduction differs")
            launchers = packer.write_launchers({"main.c": source}, directory / "packed", command=recipe)
            launchers += single.write_single(source, directory / "single", stdin_recipe)
            launchers += stream.write_stream(source, directory / "stream", stdin_recipe)
            launchers += packer.write_launchers({"x": binary.read_bytes()}, directory / "native-packed")
            repeated = packer.write_launchers({"main.c": source}, directory / "packed-repeat", command=recipe)
            repeated += single.write_single(source, directory / "single-repeat", stdin_recipe)
            repeated += stream.write_stream(source, directory / "stream-repeat", stdin_recipe)
            repeated += packer.write_launchers({"x": binary.read_bytes()}, directory / "native-packed-repeat")
            for first, other in zip(launchers, repeated):
                if Path(first["path"]).read_bytes() != Path(other["path"]).read_bytes():
                    raise RuntimeError("complete packaged artifact reproduction differs")
                first["reproduced"] = True
                first["restored_native_sha256"] = sha(stdin_binary if first["format"] in
                    ("python3-source-zipapp-single", "sh-python3-source-stream-single") else binary.read_bytes())
                first["restoration_scope"] = "complete /proc/<pid>/exe bytes after UCI startup"
            entry["launchers"] = launchers
        records.append(entry)
    report = {"candidate": "E shipping-state " + args.form, "features": features, "state_overlay": state_record,
              "core_provenance": provenance,
              "source_layout": layout, "counter_recipe": counter_recipe,
              "input_sha256": {name: sha(data) for name, data in frozen.items()},
              "input_admission": input_admission,
              "compiler": subprocess.check_output([args.cc, "--version"], text=True).splitlines()[0],
              "preprocessor": observations, "engines": records, "eligible_4k": False}
    candidates = [(engine, artifact) for engine in records for artifact in engine.get("launchers", [])]
    selected_artifact = None
    if candidates:
        source_engine, selected_artifact = min(candidates, key=lambda pair: pair[1]["bytes"])
        records.append({"id": "tiny-" + args.variant + "-selected", "command": [selected_artifact["path"]],
                        "cwd": str(Path(selected_artifact["path"]).parent), "profile": "shipping",
                        "workers": args.workers, "startup_threads": args.workers + 1, "startup_timeout": 60,
                        "expected_program_sha256": selected_artifact["sha256"], "selected_from": source_engine["id"],
                        "selected_artifact": selected_artifact})
    report["selected"] = selected_artifact
    native_candidates = [(engine, artifact) for engine in records for artifact in engine.get("launchers", []) if "native" in artifact["format"]]
    if native_candidates:
        source_engine, selected_native = min(native_candidates, key=lambda pair: pair[1]["bytes"])
        report["selected_native"] = selected_native
        records.append({"id": "tiny-" + args.variant + "-selected-native", "command": [selected_native["path"]],
                        "cwd": str(Path(selected_native["path"]).parent), "profile": "shipping",
                        "workers": args.workers, "startup_threads": args.workers + 1, "startup_timeout": 60,
                        "expected_program_sha256": selected_native["sha256"], "selected_from": source_engine["id"],
                        "selected_artifact": selected_native})
    (args.out / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"variant": args.variant, "form": args.form, "out": str(args.out), "minimum_complete_bytes": selected_artifact["bytes"] if selected_artifact else None,
                      "forms": [{key: item[key] for key in ("id", "native_bytes", "source_bytes")} for item in records if "native_bytes" in item]}))


if __name__ == "__main__":
    main()
