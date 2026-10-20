#!/usr/bin/env python3
"""Measure frozen Tiny Rust A four-file ZIP and merged compiler-stdin streams.

Run on Linux x86-64. Outputs must be a new absolute directory outside the
checkout. This experiment does not modify the stable engine or its producers.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import traceback


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE_PREFIX = "engines/compact/tiny-rust/"
PRODUCTION = ("main.rs", "board.rs", "search.rs", "runtime.rs")
RAW_BINDINGS = {
    "main.rs": "c1d659cf38473d838505e3912effac0798841eb160d7033a21ab2dc5443ed56d",
    "board.rs": "47e6289e06eff93484c50ef4218729b444eea7b4a8868362dd1d0d37eaaf06d9",
    "search.rs": "4573947933c348cff4fa371f656dc5cdc21560ea09ca95d98dfaf0667ce6b981",
    "runtime.rs": "2bf60847bf40c882ac16e0840f51fd24d9cf6dad5bb463e9dda0a83623ac6dec",
}
PRUNED_BINDINGS = {
    "main.rs": "15807c8fa1a76b5876d1e276d2e9089ed5285a6b30b053e50f6e52521f1f6f27",
    "board.rs": "d961a97bbf28995c8781fcfd6548ca819f23b822d7b846abdf8b18d77f3d9caf",
    "search.rs": "4b75f63da79b258f5c94d1caca3b3c079e1674167c863e1b5e8b1df5ab92558f",
    "runtime.rs": "f600cd89520c14851b205f6f9eab9310e574fedf76a430f8a0d277888c99a6a8",
}
HELPER_BINDINGS = {
    "engines/compact/tiny-rust/build.py": "c614604f570e32b7d816c340f3ff0ba067a74f4826705f660bc29dcf6093ffbf",
    "engines/compact/rust/syntax.py": "54ff9e05cbcb099c6ee96e09014be3d2a80c21fb8bf21e508b0a03bda5114100",
    "engines/scripts/pack.py": "f95a9166f8fc018e4250999fa60c10568fa2ef3388b704a1fdfab9802bef5083",
    "engines/compact/tiny-a/pack_stream.py": "b4addefbb1233881e85707aa525ca4af7f8210d9d27f56fbb52e4440a966b99e",
}
BASELINE_BYTES = 9074
BASELINE_SHA256 = "35bc0d0f930da90ac4826659c60db5c3dcf805edba7047d85855d86d13cc8a72"
_ACTIVE_OUTPUT = None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_files(files, directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in sorted(files.items()):
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def stdin_recipe(command, compiler):
    if command[-3:] != ["main.rs", "-o", "x"]:
        raise ValueError("stable compiler recipe has an unknown input/output shape")
    return [compiler, *command[1:-3], "--crate-name", "rove4k", "-", "-o", "x"]


def compile_stdin(stable, source, directory, command, fixed):
    directory.mkdir(parents=True)
    (directory / "source.stdin.rs").write_bytes(source)
    environment = os.environ.copy()
    environment.update(fixed)
    actual = [command[0], "--remap-path-prefix", str(directory) + "=.", *command[1:]]
    record = stable.run(actual, cwd=directory, env=environment, data=source)
    native = (directory / "x").read_bytes()
    if native[:4] != b"\x7fELF":
        raise ValueError("compiler-stdin class did not produce a Linux ELF")
    record.update({"path": str(directory / "x"), "bytes": len(native), "sha256": sha(native),
                   "input": "compiler stdin", "source_bytes": len(source), "source_sha256": sha(source)})
    return record


def execute_frozen(args, frozen_root, inputs, compiler):
    """All producer imports below use the already frozen recipe tree."""
    stable = load("tiny_rust_stream_frozen_stable", frozen_root / "engines/compact/tiny-rust/build.py")
    merge = load("tiny_rust_stream_frozen_merge", frozen_root / "engines/experiments/tiny-rust-stream/merge.py")
    stream = load("tiny_rust_stream_frozen_pack", frozen_root / "engines/experiments/tiny-rust-stream/stream_pack.py")
    pack = load("tiny_rust_stream_frozen_zip", frozen_root / "engines/scripts/pack.py")
    raw = {name: inputs[SOURCE_PREFIX + name] for name in PRODUCTION}
    pruned, pruning = stable.specialize(raw, development=False)
    if {name: sha(data) for name, data in pruned.items()} != PRUNED_BINDINGS:
        raise ValueError("stable pruned production files differ from the 9,074-byte checkpoint")
    merged_source, merging = merge.merge(pruned)
    if not isinstance(merged_source, bytes):
        raise ValueError("merge producer must return compiler-stdin bytes")
    source, resources, resource_producer = merged_source, {"enabled": False}, None
    if args.embody_resources:
        resource_producer = load("tiny_rust_stream_frozen_resources", frozen_root / "engines/experiments/tiny-rust-stream/resources.py")
        source, resource_metadata = resource_producer.embody(merged_source, workers=args.workers, tt_bits=args.tt_bits)
        if not isinstance(source, bytes) or not isinstance(resource_metadata, dict):
            raise ValueError("resource producer must return source bytes and metadata")
        resources = {**resource_metadata, "enabled": True}
        (args.out / "pre-resource.stdin.rs").write_bytes(merged_source)
    write_files(pruned, args.out / "pruned")
    (args.out / "merged.stdin.rs").write_bytes(source)
    baseline_command, fixed = stable.recipe("rustc", development=False, workers=args.workers, tt_bits=args.tt_bits)
    command = stdin_recipe(baseline_command, compiler)
    runtime_command = stdin_recipe(baseline_command, "rustc")
    if any(Path(argument).is_absolute() for argument in runtime_command):
        raise ValueError("runtime compiler recipe contains a host absolute path")
    baseline, baseline_record = pack.make_launcher(pruned, command=baseline_command, environment=fixed, codec="lzma", transport="zip")
    baseline_path = args.out / "baseline" / "x"
    baseline_path.parent.mkdir()
    baseline_path.write_bytes(baseline)
    baseline_path.chmod(0o755)
    baseline_record["path"] = str(baseline_path)
    reference_applies = (args.workers, args.tt_bits) == (2, 18)
    if reference_applies and (len(baseline) != BASELINE_BYTES or sha(baseline) != BASELINE_SHA256):
        raise ValueError("regenerated four-file ZIP differs from exact 9,074-byte baseline")
    build = compile_stdin(stable, source, args.out / "stdin-native", command, fixed)
    artifacts = stream.write_stream(source, args.out / "stream", runtime_command, environment=fixed)
    if not artifacts or len(artifacts) != 3:
        raise ValueError("stream producer must return exactly three codec artifacts")
    if args.reproduce:
        pruned_second, pruning_second = stable.specialize(dict(raw), development=False)
        merged_second, merging_second = merge.merge(dict(pruned_second))
        source_second, resources_second = merged_second, {"enabled": False}
        if resource_producer is not None:
            source_second, resource_metadata_second = resource_producer.embody(merged_second, workers=args.workers, tt_bits=args.tt_bits)
            resources_second = {**resource_metadata_second, "enabled": True}
        if pruned_second != pruned or pruning_second != pruning or merged_second != merged_source or source_second != source or merging_second != merging or resources_second != resources:
            raise RuntimeError("independent source/pruning/merge/resource reproduction differs")
        baseline_second, baseline_second_record = pack.make_launcher(pruned_second, command=list(baseline_command), environment=dict(fixed), codec="lzma", transport="zip")
        if baseline_second != baseline:
            raise RuntimeError("independent baseline complete-file reproduction differs")
        baseline_record["reproduced"] = True
        repeated_native = compile_stdin(stable, source_second, args.out / "reproduction" / "stdin-native", command, fixed)
        if Path(repeated_native["path"]).read_bytes() != Path(build["path"]).read_bytes():
            raise RuntimeError("independent compiler-stdin native class reproduction differs")
        build["reproduced"] = True
        repeated_artifacts = stream.write_stream(source_second, args.out / "reproduction" / "stream", list(runtime_command), environment=dict(fixed))
        if len(repeated_artifacts) != len(artifacts):
            raise RuntimeError("independent stream artifact count differs")
        for first, second in zip(artifacts, repeated_artifacts):
            if first["codec"] != second["codec"] or Path(first["path"]).read_bytes() != Path(second["path"]).read_bytes():
                raise RuntimeError("independent complete stream bytes differ")
            first["reproduced"] = True
    selected = min(artifacts, key=lambda record: record["bytes"])
    controlled_path = os.pathsep.join(dict.fromkeys((str(Path(compiler).parent), "/usr/local/bin", "/usr/bin", "/bin")))
    environment = os.environ.copy()
    environment["PATH"] = controlled_path
    smoke = {"passed": None, "reason": "runtime qualification deferred; measure-only build"}
    if args.smoke_selected:
        smoke = stable.smoke(selected["path"], environment)
    native_spec = {"id": "tiny-rust-stream-stdin-native", "command": [build["path"]],
                   "cwd": str(Path(build["path"]).parent), "profile": "shipping", "workers": args.workers,
                   "startup_threads": args.workers + 1, "expected_program_sha256": build["sha256"],
                   "source_form": "bound inline-module compiler stdin", "native_bytes": build["bytes"]}
    def wrapper_spec(label, artifact):
        return {"id": label, "command": [artifact["path"]], "cwd": str(Path(artifact["path"]).parent),
                "profile": "shipping", "workers": args.workers, "startup_threads": args.workers + 1,
                "startup_timeout": 60, "expected_program_sha256": artifact["sha256"], "selected_artifact": artifact}
    report = {"candidate": "Tiny Rust A module-inline compiler-stdin stream experiment", "development": False,
              "workers": args.workers, "tt_bits": args.tt_bits, "startup_threads": args.workers + 1,
              "raw_source_sha256": {name: sha(data) for name, data in sorted(raw.items())},
              "recipe_sha256": {name: sha(data) for name, data in sorted(inputs.items())},
              "pruning": pruning, "merge": merging, "resources": resources,
              "pre_resource_source_bytes": len(merged_source), "pre_resource_source_sha256": sha(merged_source),
              "merged_source_bytes": len(source), "merged_source_sha256": sha(source),
              "compiler": stable.run([compiler, "--version", "--verbose"])["stdout"].strip(),
              "host_compiler_command": command, "runtime_compiler_command": runtime_command, "compiler_environment": fixed,
              "target_compiler_scope": {"command": "rustc", "resolution": "target caller PATH",
                                        "host_build_compiler": compiler, "controlled_verification_PATH": controlled_path,
                                        "host_path_embedded_in_runtime_recipe": False},
              "four_file_zip_baseline": baseline_record, "same_9074_reference_profile": reference_applies,
              "same_9074_reference_verified": reference_applies, "stdin_native": build, "stream_artifacts": artifacts,
              "selected": selected, "selected_smoke": smoke, "reproduction_requested": args.reproduce,
              "native_classes": "four-file and stdin/inline-module classes may differ in file/line panic metadata; no native cross-class identity claim",
              "eligible_4k": False, "under_4096_bytes": selected["bytes"] <= 4096,
              "eligibility": "unproven_requires_full_rules_and_runtime_review"}
    manifest = {"schema": 1, "scope": report["candidate"], "workers": args.workers, "tt_bits": args.tt_bits,
                "target_PATH": controlled_path, "engines": [native_spec,
                    wrapper_spec("tiny-rust-stable-four-file-zip", baseline_record),
                    wrapper_spec("tiny-rust-stream-selected", selected)]}
    (args.out / "build.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.out / "validation-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "four_file_zip_bytes": len(baseline), "same_9074_reference_verified": reference_applies,
                      "merged_source_bytes": len(source), "stdin_native_bytes": build["bytes"],
                      "complete_stream_bytes": {artifact["codec"]: artifact["bytes"] for artifact in artifacts},
                      "selected_bytes": selected["bytes"], "selected_codec": selected["codec"], "eligible_4k": False}))


def main():
    global _ACTIVE_OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--tt-bits", type=int, default=18)
    parser.add_argument("--rustc", default="rustc")
    parser.add_argument("--reproduce", action="store_true")
    parser.add_argument("--smoke-selected", action="store_true")
    parser.add_argument("--embody-resources", action="store_true", help="literal fixed resources in the bound source; only workers 2 / TT bits 18")
    args = parser.parse_args()
    if sys.platform != "linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        parser.error("run on Linux x86-64, including WSL Ubuntu")
    if not args.out.is_absolute():
        parser.error("--out must be absolute")
    args.out = args.out.resolve()
    if args.out.exists() or args.out == ROOT or ROOT in args.out.parents:
        parser.error("--out must be a new directory outside the checkout")
    if not 1 <= args.workers <= 512 or not 8 <= args.tt_bits <= 26:
        parser.error("workers 1..512; TT bits 8..26")
    if args.embody_resources and (args.workers, args.tt_bits) != (2, 18):
        parser.error("--embody-resources requires workers 2 and TT bits 18")
    compiler = shutil.which(args.rustc)
    if compiler is None:
        parser.error("Rust compiler is not executable: " + args.rustc)
    compiler = os.path.abspath(compiler)
    _ACTIVE_OUTPUT = args.out
    paths = [*(SOURCE_PREFIX + name for name in PRODUCTION), *HELPER_BINDINGS,
             "engines/experiments/tiny-rust-stream/build.py", "engines/experiments/tiny-rust-stream/merge.py",
             "engines/experiments/tiny-rust-stream/stream_pack.py"]
    if args.embody_resources:
        paths.append("engines/experiments/tiny-rust-stream/resources.py")
    inputs = {name: (ROOT / name).read_bytes() for name in paths}
    for name, expected in RAW_BINDINGS.items():
        if sha(inputs[SOURCE_PREFIX + name]) != expected:
            raise ValueError("raw production source differs from exact 9,074-byte checkpoint: " + name)
    for name, expected in HELPER_BINDINGS.items():
        if sha(inputs[name]) != expected:
            raise ValueError("stable helper differs from exact 9,074-byte checkpoint: " + name)
    # No engine producer/helper has been imported until every byte is frozen.
    frozen = args.out / "recipe"
    write_files(inputs, frozen)
    producer = load("tiny_rust_stream_frozen_builder", frozen / "engines/experiments/tiny-rust-stream/build.py")
    producer.execute_frozen(args, frozen, inputs, compiler)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if _ACTIVE_OUTPUT is not None and _ACTIVE_OUTPUT.is_dir():
            (_ACTIVE_OUTPUT / "failure.json").write_text(json.dumps({"passed": False, "exception": type(error).__name__,
                "error": str(error), "traceback": traceback.format_exc()}, indent=2) + "\n", encoding="utf-8")
        raise
