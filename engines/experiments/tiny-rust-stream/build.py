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
import signal
import subprocess
import sys
import time
import traceback


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE_PREFIX = "engines/compact/tiny-rust/"
PRODUCTION = ("main.rs", "board.rs", "search.rs", "runtime.rs")
# Exact source bytes stored by Git after the explicit CRLF-to-LF intake below.
# The older local 9,074-byte receipt had one CRLF in search.rs's final test line.
CANONICAL_SOURCE_BINDINGS = {
    "main.rs": "c1d659cf38473d838505e3912effac0798841eb160d7033a21ab2dc5443ed56d",
    "board.rs": "47e6289e06eff93484c50ef4218729b444eea7b4a8868362dd1d0d37eaaf06d9",
    "search.rs": "646bb5b61bbd3335154b9f7c1142d775d61502d39a2e9d4d8d0eaeb202ca8eb2",
    "runtime.rs": "2bf60847bf40c882ac16e0840f51fd24d9cf6dad5bb463e9dda0a83623ac6dec",
}
PRUNED_BINDINGS = {
    "main.rs": "15807c8fa1a76b5876d1e276d2e9089ed5285a6b30b053e50f6e52521f1f6f27",
    "board.rs": "d961a97bbf28995c8781fcfd6548ca819f23b822d7b846abdf8b18d77f3d9caf",
    "search.rs": "4b75f63da79b258f5c94d1caca3b3c079e1674167c863e1b5e8b1df5ab92558f",
    "runtime.rs": "f600cd89520c14851b205f6f9eab9310e574fedf76a430f8a0d277888c99a6a8",
}
HELPER_BINDINGS = {
    "engines/compact/tiny-rust-d-shipping/build.py": "67a89639402d8e27cc9728c3ad690c049c01e17a42fedb63b9d53f0f92fd0db8",
    "engines/compact/tiny-entry-d/verify.py": "18faa69aed5cb5dd85a054ef2e6830463f3d819f5f635d74d55550a877c81eae",
    "engines/scripts/compiler_stdin.py": "fc92bb6146fcfc5a6c73cd9f68929192a90d22a875bf591caf2cf3b32b87055b",
    "engines/scripts/compiler_seek.py": "8ca5fd736f010cd9dd1e3b668065c0cf7d82f9e98653580b8f9b4c23e7d75a41",
    "engines/compact/tiny-rust/build.py": "cec8e9a93efba045ea43ac7e70208896fe3c448da1c7ad39cfd61e7bdf389b35",
    "engines/compact/rust/syntax.py": "54ff9e05cbcb099c6ee96e09014be3d2a80c21fb8bf21e508b0a03bda5114100",
    "engines/experiments/packaging-control/pack.py": "f95a9166f8fc018e4250999fa60c10568fa2ef3388b704a1fdfab9802bef5083",
    "engines/experiments/packaging-control/pack_stream.py": "b4addefbb1233881e85707aa525ca4af7f8210d9d27f56fbb52e4440a966b99e",
    "engines/compact/tiny-a/pack_stream.py": "8e601c6a1d2c80478dc71f47d4cc7cee350cd388d430937a4953eae407234e25",
}
BASELINE_BYTES = 9074
BASELINE_SHA256 = "35bc0d0f930da90ac4826659c60db5c3dcf805edba7047d85855d86d13cc8a72"
_ACTIVE_OUTPUT = None
_HOST_RUNTIME = None


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


def canonical_inputs(raw_inputs):
    """Admit one Git-LF identity for the closed source/helper text closure."""
    required = {*(SOURCE_PREFIX + name for name in PRODUCTION), *HELPER_BINDINGS,
                "engines/experiments/tiny-rust-stream/build.py",
                "engines/experiments/tiny-rust-stream/merge.py",
                "engines/experiments/tiny-rust-stream/stream_pack.py"}
    optional = "engines/experiments/tiny-rust-stream/resources.py"
    if type(raw_inputs) is not dict or set(raw_inputs) not in (required, required | {optional}):
        raise ValueError("the closed Rust source/helper text inputs are required")
    inputs, entries = {}, {}
    for name, raw in sorted(raw_inputs.items()):
        if type(raw) is not bytes:
            raise TypeError("immutable Rust source/helper text bytes required")
        raw.decode("utf-8")
        canonical = raw.replace(b"\r\n", b"\n")
        if b"\r" in canonical:
            raise ValueError("lone CR is outside the canonical-LF text contract: " + name)
        inputs[name] = canonical
        entries[name] = {"raw_bytes": len(raw), "raw_sha256": sha(raw),
                         "canonical_bytes": len(canonical), "canonical_sha256": sha(canonical),
                         "CRLF_pairs": raw.count(b"\r\n"), "EOL_changed": raw != canonical}
    for name, expected in CANONICAL_SOURCE_BINDINGS.items():
        if sha(inputs[SOURCE_PREFIX + name]) != expected:
            raise ValueError("canonical-LF production source differs from the exact Git checkpoint: " + name)
    for name, expected in HELPER_BINDINGS.items():
        if sha(inputs[name]) != expected:
            raise ValueError("canonical-LF helper differs from the bound recipe: " + name)
    return inputs, {"policy": "git-canonical-LF-v1", "normalization": "CRLF to LF before exact SHA-256 admission; lone CR rejected",
                    "entries": entries, "changed_paths": [name for name, entry in entries.items() if entry["EOL_changed"]]}


def stdin_recipe(command, compiler):
    if command[-3:] != ["main.rs", "-o", "x"]:
        raise ValueError("stable compiler recipe has an unknown input/output shape")
    return [compiler, *command[1:-3], "--crate-name", "rove4k", "-", "-o", "x"]


def run_host(command, *, cwd=None, env=None, timeout=180, data=None):
    """Keep the stable call shape, using existing readers and original-owner settlement."""
    global _HOST_RUNTIME
    if _HOST_RUNTIME is None:
        owner_path=ROOT/'engines/compact/tiny-rust-d-shipping/build.py'
        readers_path=ROOT/'engines/compact/tiny-entry-d/verify.py'
        for path in (owner_path,readers_path):
            if sha(path.read_bytes())!=HELPER_BINDINGS[str(path.relative_to(ROOT))]:
                raise ValueError('Rust stream host dependency changed: '+str(path))
        _HOST_RUNTIME=(load('rust_stream_existing_tool_owner',owner_path),
                       load('rust_stream_existing_tool_readers',readers_path))
    owner,readers=_HOST_RUNTIME
    started=time.monotonic();deadline=started+timeout;child=None;ports=[];failure=None
    row={'command':list(map(str,command)),'started':False,'forced_cleanup':False}
    def interrupted(signum,frame):raise InterruptedError('Rust stream host signal '+str(signum))
    handlers={sig:signal.signal(sig,interrupted) for sig in (signal.SIGINT,signal.SIGTERM)}
    previous_chld=signal.signal(signal.SIGCHLD,signal.SIG_DFL)
    def check():
        if time.monotonic()>deadline:raise TimeoutError('Rust stream tool deadline')
        if any(port.error for port in ports):raise RuntimeError('Rust stream tool reader failure')
    try:
        try:
            mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
            try:
                child=subprocess.Popen(row['command'],cwd=cwd,env=env,stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,bufsize=0,
                    preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,mask))
                row.update(started=True,pid=child.pid);owner.owned[child]=row
                ports.append(readers.Reader(child.stdout,'rust-stream-tool-stdout'))
                ports.append(readers.Reader(child.stderr,'rust-stream-tool-stderr'))
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
            try:
                if data is not None:
                    os.set_blocking(child.stdin.fileno(),False);view=memoryview(data)
                    while view:
                        check()
                        try:count=os.write(child.stdin.fileno(),view)
                        except BrokenPipeError:break
                        except BlockingIOError:time.sleep(.005);continue
                        if not count:raise RuntimeError('zero Rust stream host write')
                        view=view[count:]
            finally:child.stdin.close()
            while not owner.exited_unreaped(child):check();time.sleep(.01)
        except BaseException as error:
            failure=error
        finally:
            mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
            try:
                if child is not None:owner.settle(child,row,force=not owner.exited_unreaped(child))
            finally:
                try:
                    for port in ports:
                        port.thread.join(timeout=3)
                        if port.thread.is_alive() or not port.done or port.error:
                            raise RuntimeError('Rust stream tool reader did not join')
                    if child is not None:
                        for pipe in (child.stdin,child.stdout,child.stderr):
                            if pipe is not None and not pipe.closed:pipe.close()
                finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
        stdout=ports[0].bytes().decode(errors='replace') if ports else ''
        stderr=ports[1].bytes().decode(errors='replace') if len(ports)>1 else ''
        record={**row,'returncode':child.returncode if child is not None else None,
                'wall_seconds':time.monotonic()-started,'stdout':stdout,'stderr':stderr,
                'readers_joined':all(port.done and not port.thread.is_alive() for port in ports)}
        if isinstance(failure,TimeoutError):raise RuntimeError('command timeout: '+repr(command)+'\n'+stderr) from failure
        if failure is not None:raise failure
        if record['returncode']:raise RuntimeError(json.dumps(record,indent=2))
        if record['forced_cleanup'] or not record.get('owned_group_absent') or not record['readers_joined']:
            raise RuntimeError('Rust stream tool required cleanup intervention: '+json.dumps(record,indent=2))
        return record
    finally:
        signal.signal(signal.SIGCHLD,previous_chld)
        for sig,handler in handlers.items():signal.signal(sig,handler)


def compile_stdin(stable, source, directory, command, fixed):
    directory.mkdir(parents=True)
    (directory / "source.stdin.rs").write_bytes(source)
    environment = os.environ.copy()
    environment.update(fixed)
    actual = [command[0], "--remap-path-prefix", str(directory) + "=.", *command[1:]]
    record = run_host(actual, cwd=directory, env=environment, data=source)
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
    pack = load("tiny_rust_stream_historical_zip", frozen_root / "engines/experiments/packaging-control/pack.py")
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
    baseline_record["historical_control"] = {
        "producer": "engines/experiments/packaging-control/pack.py",
        "sha256": HELPER_BINDINGS["engines/experiments/packaging-control/pack.py"],
        "origin": "1d2e3b7:engines/scripts/pack.py",
        "old_compiler_owner": True, "new_common_owner_qualification": False,
    }
    reference_applies = (args.workers, args.tt_bits) == (2, 18)
    if reference_applies and (len(baseline) != BASELINE_BYTES or sha(baseline) != BASELINE_SHA256):
        raise ValueError("regenerated four-file ZIP differs from exact 9,074-byte baseline")
    compiler_fixed = stream._guard(source, runtime_command, fixed,
                                   omit_resource_environment=args.omit_resource_environment)
    build = compile_stdin(stable, source, args.out / "stdin-native", command, compiler_fixed)
    artifacts = stream.write_stream(source, args.out / "stream", runtime_command, environment=fixed,
                                   prepared=args.prepared_input,
                                   omit_resource_environment=args.omit_resource_environment)
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
        repeated_native = compile_stdin(stable, source_second, args.out / "reproduction" / "stdin-native", command, compiler_fixed)
        if Path(repeated_native["path"]).read_bytes() != Path(build["path"]).read_bytes():
            raise RuntimeError("independent compiler-stdin native class reproduction differs")
        build["reproduced"] = True
        repeated_artifacts = stream.write_stream(source_second, args.out / "reproduction" / "stream", list(runtime_command), environment=dict(fixed),
                                                prepared=args.prepared_input,
                                                omit_resource_environment=args.omit_resource_environment)
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
              "compiler": run_host([compiler, "--version", "--verbose"])["stdout"].strip(),
              "host_compiler_command": command, "runtime_compiler_command": runtime_command, "compiler_environment": compiler_fixed,
              "compiler_environment_input": fixed, "wrapper_policy": "prepared-W1-W2-seek" if args.prepared_input else "legacy-pipe",
              "resource_environment_overrides_omitted": args.omit_resource_environment,
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
    parser.add_argument("--prepared-input", action="store_true", help="Rust-specific prepared-file W1/W2/seek wrapper")
    parser.add_argument("--omit-resource-environment", action="store_true", help="omit compiler resource overrides only after exact2/18 source embodiment")
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
    if args.omit_resource_environment and not args.embody_resources:
        parser.error("--omit-resource-environment requires --embody-resources")
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
    inputs, intake = canonical_inputs({name: (ROOT / name).read_bytes() for name in paths})
    # No engine producer/helper has been imported until every byte is frozen.
    frozen = args.out / "recipe"
    write_files(inputs, frozen)
    (args.out / "input-canonicalization.json").write_text(json.dumps(intake, indent=2) + "\n", encoding="utf-8")
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
