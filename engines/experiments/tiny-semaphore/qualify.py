#!/usr/bin/env python3
"""Qualify one exact semaphore source wrapper with frozen verifier sources.

Source and argv are literal data. The live ELF must match its recorded stripped
class. Filesystem absence is sampled after UCI-ready; cleanup before fd-exec is
established separately by the unchanged frozen bootstrap skeleton.
"""
import argparse
import ast
import bz2
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import re
import subprocess
import sys
import zlib


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def argument(script, owner, method):
    tree = ast.parse(script)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and node.args
             and isinstance(node.func, ast.Attribute) and node.func.attr == method
             and isinstance(node.func.value, ast.Name) and node.func.value.id == owner]
    require(len(calls) == 1, "expected one literal call: " + owner + "." + method)
    return calls[0].args[0]


def literal_value(node):
    """Only bytes/strings, argv literal containers and constant encode/split."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        result = [literal_value(item) for item in node.elts]
        require(all(isinstance(item, str) for item in result), "argv elements must be strings")
        return tuple(result) if isinstance(node, ast.Tuple) else result
    if (isinstance(node, ast.Call) and not node.args and not node.keywords
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str)):
        if node.func.attr == "encode":
            return node.func.value.value.encode("utf-8")
        if node.func.attr == "split":
            return node.func.value.value.split()
    raise ValueError("unapproved nonliteral source or compiler expression")


def source_argument(script):
    tree = ast.parse(script)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == "memoryview"]
    require(len(calls) == 1 and len(calls[0].args) == 1 and not calls[0].keywords,
            "expected one literal compiler source memoryview")
    return calls[0].args[0]


def decoded_wrapper(data, codec):
    prefix = re.match(
        rb'#!/bin/sh\np=\$\(tail -c\+([0-9]+) "\$0"\|(xz|gzip|bzip2) -dc\)\|\|exit\n'
        rb'exec python3 -c "\$p" "\$0" "\$@"\n', data)
    require(prefix is not None, "unexpected complete source-wrapper prefix")
    require(int(prefix[1]) == prefix.end() + 1, "source-wrapper payload offset mismatch")
    tool = prefix[2].decode("ascii")
    expected = "xz" if codec.startswith("xz") else codec
    require(tool == expected, "wrapper decoder differs from recorded codec")
    payload = data[prefix.end():]
    if tool == "xz":
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
        decoded = decoder.decompress(payload)
    elif tool == "bzip2":
        decoder = bz2.BZ2Decompressor()
        decoded = decoder.decompress(payload)
    else:
        decoder = zlib.decompressobj(31)
        decoded = decoder.decompress(payload) + decoder.flush()
        require(not decoder.unconsumed_tail, "gzip data was not fully consumed")
    require(decoder.eof and not decoder.unused_data, "one complete compressed stream required")
    ast.parse(decoded)
    return data[:prefix.end()], decoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--form", choices=("baseline", "semaphore"), default="semaphore")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.build.is_absolute() or not args.build.is_file():
        parser.error("--build must be an absolute existing build report")
    if not args.out.is_absolute() or args.out.exists():
        parser.error("--out must be a new absolute external directory")
    args.out = args.out.resolve()
    if args.out == ROOT or ROOT in args.out.parents:
        parser.error("output must stay outside the checkout")
    args.out.mkdir(parents=True)
    frozen = args.out / "frozen"
    frozen.mkdir()
    result = {"schema": 1, "passed": False, "form": args.form,
              "scope": "exact complete wrapper and live restored-image/startup qualification; no search-strength claim",
              "build_path": str(args.build), "frozen_sha256": {},
              "excluded": ["independent pre-input filesystem sample", "all-position correctness", "NPS/Elo", "large-profile scalability", "4K acceptance"]}
    save(args.out / "identity.json", result)
    engine = None
    try:
        report_bytes = args.build.read_bytes()
        build = json.loads(report_bytes)
        grouped = "compiler_group.py" in build.get("helpers_sha256", {})
        require(build.get("workers") == 2 and build.get("tt_bits") == 18, "qualifier requires the measured two-worker TT18 profile")
        choices = [record for record in build["records"] if record["name"] == args.form]
        require(len(choices) == 1, "expected one selected form")
        inputs = choices[0]["inputs_sha256"]
        if args.form == "semaphore":
            baselines = [record for record in build["records"] if record["name"] == "baseline"]
            require(len(baselines) == 1, "expected one matched baseline")
            for name in ("tiny.h", "board.c", "search.c"):
                require(inputs[name] == baselines[0]["inputs_sha256"][name],
                        "non-pool core source changed: " + name)
            result["unchanged_core_inputs_sha256"] = {name: inputs[name]
                for name in ("tiny.h", "board.c", "search.c")}
        result["runtime_input_sha256"] = inputs["main.c"]
        encoding = choices[0]["encoding"]
        artifact = encoding["selected"]
        path = Path(artifact["path"])
        require(path.is_absolute(), "selected artifact path must be absolute")
        whole = path.read_bytes()
        require(sha(whole) == artifact["sha256"] and len(whole) == artifact["bytes"], "selected complete file differs from build record")
        source = (args.build.parent / args.form / "encoded/main.c").read_bytes()
        script = (args.build.parent / args.form / "encoded/bootstrap.py").read_bytes()
        require(sha(source) == encoding["source_sha256"] and len(source) == encoding["source_bytes"], "encoded C differs from build record")
        prefix, decoded = decoded_wrapper(whole, artifact["codec"])
        require(decoded == script, "selected wrapper does not contain the exact recorded Python bootstrap")
        restored = literal_value(source_argument(script) if grouped else argument(script, "p", "communicate"))
        argv = literal_value(argument(script, "subprocess", "Popen"))
        require(isinstance(restored, bytes) and restored == source, "compiler stdin differs from encoded C bytes")
        require(isinstance(argv, (tuple, list)) and list(argv) == encoding["compiler"], "compiler argv differs from build record")
        require(all(isinstance(part, str) and part and "\0" not in part for part in argv), "invalid fixed compiler argv")

        snapshots = {"qualify.py": Path(__file__).read_bytes(), "build.json": report_bytes,
                     "encoded-main.c": source, "bootstrap.py": script, "selected-wrapper": whole,
                     "verify.py": (ROOT / "engines/tests/verify.py").read_bytes(),
                     "chess_oracle.py": (ROOT / "engines/tests/chess_oracle.py").read_bytes()}
        helper_names = ["pack_stream.py", "encoding_campaign.py"]
        if grouped:
            helper_names.append("compiler_group.py")
        for name in helper_names:
            data = (args.build.parent / "frozen" / name).read_bytes()
            require(sha(data) == build["helpers_sha256"][name], "frozen producer/helper hash mismatch: " + name)
            snapshots[name] = data
        for name, data in snapshots.items():
            (frozen / name).write_bytes(data)
            result["frozen_sha256"][name] = sha(data)
        executable = frozen / "selected-wrapper"
        executable.chmod(0o755)
        save(args.out / "identity.json", result)

        campaign = module("semaphore_frozen_expression_helper", frozen / "encoding_campaign.py")
        producer = module("semaphore_frozen_stream_producer", frozen / "pack_stream.py")
        control, _ = producer.bootstrap(source, encoding["compiler"])
        if grouped:
            compiler_group = module("semaphore_frozen_compiler_group", frozen / "compiler_group.py")
            argv_form = encoding["compiler_argv_representation"]
            require(argv_form in ("list", "split"), "unknown recorded compiler argv representation")
            if argv_form == "split":
                control = campaign.replace_argument(control, "subprocess", "Popen",
                                                    repr(" ".join(encoding["compiler"])) + ".split()")
            control, _ = compiler_group.transform_bootstrap(control)
            require(script == control, "signal/wait/cleanup/fd-exec bootstrap skeleton changed")
        else:
            def skeleton(body):
                body = campaign.replace_argument(body, "p", "communicate", "b'SOURCE'")
                return campaign.replace_argument(body, "subprocess", "Popen", "['COMMAND']")
            require(skeleton(script) == skeleton(control), "signal/wait/cleanup/fd-exec bootstrap skeleton changed")
        result.update(artifact_path=str(path), execution_path=str(executable), artifact_sha256=sha(whole),
                      whole_bytes=len(whole), launcher_bytes=len(prefix), decoded_sha256=sha(decoded),
                      source_sha256=sha(source), source_restored_exactly=True, compiler_argv=list(argv),
                      compiler_argv_exact=True, bootstrap_skeleton_unchanged=True,
                      expected_stripped_native_sha256=encoding["stripped_native_sha256"])
        save(args.out / "identity.json", result)

        # Pin both imported test sources before importing the verifier. The
        # oracle's explicit module name is the one verify.py itself imports.
        module("chess_oracle", frozen / "chess_oracle.py")
        verifier = module("semaphore_frozen_verifier", frozen / "verify.py")
        spec = {"id": "semaphore-qualified-actual", "command": [str(executable)],
                "cwd": str(frozen), "profile": "shipping", "workers": 2,
                "startup_threads": 3, "startup_timeout": 60}
        engine = verifier.Engine(spec, args.out, "actual", 10)
        launched_pid = engine.process.pid
        engine.initialize()
        engine.assert_threads_stable()
        proc = Path("/proc") / str(launched_pid)
        image = (proc / "exe").read_bytes()
        require(sha(image) == encoding["stripped_native_sha256"], "actual restored ELF differs from stripped reference class")
        image_link = os.readlink(proc / "exe")
        require(image_link.endswith("/x (deleted)"), "native fd-exec did not replace the wrapper with the removed output x")
        owned_directory = Path(image_link.removesuffix(" (deleted)")).parent
        require(not owned_directory.exists(), "owned compiler directory remains after UCI-ready")
        status = dict(line.split(":", 1) for line in (proc / "status").read_text().splitlines())
        require(int(status["Pid"]) == launched_pid and int(status["PPid"]) == os.getpid(), "an intermediate wrapper process remains")
        children = (proc / "task" / str(launched_pid) / "children").read_text().strip()
        require(not children, "compiler children remain after native execution")
        current_ids = {int(entry.name) for entry in (proc / "task").iterdir()}
        require(len(current_ids) == 3 and current_ids == engine.startup_task_ids, "startup threads changed before UCI-ready inspection")
        image_path = args.out / "actual-native"
        image_path.write_bytes(image)
        commands = (("needed", ["readelf", "-d", str(image_path)]),
                    ("symbols", ["readelf", "--dyn-syms", "--wide", str(image_path)]),
                    ("glibc", ["getconf", "GNU_LIBC_VERSION"]))
        tool_results = {}
        for label, command in commands:
            observed = subprocess.run(command, capture_output=True, timeout=10)
            (args.out / (label + ".stdout")).write_bytes(observed.stdout)
            (args.out / (label + ".stderr")).write_bytes(observed.stderr)
            require(observed.returncode == 0, "inspection tool failed: " + label)
            tool_results[label] = observed.stdout.decode("utf-8", errors="replace")
        pthread = [line.strip() for line in tool_results["symbols"].splitlines()
                   if "pthread_create" in line or "pthread_join" in line]
        require(any("pthread_create" in line for line in pthread) and any("pthread_join" in line for line in pthread), "actual native pthread imports were not observed")
        semaphore = [line.strip() for line in tool_results["symbols"].splitlines()
                     if any(name in line for name in ("sem_init", "sem_wait", "sem_post", "sem_destroy"))]
        if args.form == "semaphore":
            require(all(any(name + "@" in line for line in semaphore)
                        for name in ("sem_init", "sem_wait", "sem_post", "sem_destroy")),
                    "actual native semaphore imports were not observed")
        result.update(actual_restored_native_sha256=sha(image), native_bytes=len(image),
                      launched_pid=launched_pid, observed_native_pid=int(status["Pid"]),
                      observed_parent_pid=int(status["PPid"]), expected_parent_pid=os.getpid(),
                      same_pid_fd_exec=True, native_executable_link=image_link,
                      compiler_children=[], startup_threads=3, startup_thread_ids=sorted(current_ids),
                      thread_ids_preserved=True, temporary_directory=str(owned_directory),
                      temporary_directory_absent_after_uci_ready=True,
                      temporary_directory_observation="after_uci_ready",
                      cleanup_before_fd_exec_basis="unchanged frozen bootstrap source ordering",
                      glibc=tool_results["glibc"].strip(),
                      needed=[line.strip() for line in tool_results["needed"].splitlines() if "NEEDED" in line],
                      pthread_symbols=pthread, semaphore_symbols=semaphore)
        engine.close()
        result.update(passed=True, runtime_exitcode=engine.process.returncode,
                      runtime_transcript=str(engine.path), runtime_stderr=engine.stderr)
    except Exception as error:
        result["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if engine is not None and (engine.process.poll() is None or not engine.log.closed):
            try:
                engine.terminate()
            except Exception as error:
                result["cleanup_error"] = type(error).__name__ + ": " + str(error)
                result["passed"] = False
    save(args.out / "identity.json", result)
    print(json.dumps({"passed": result["passed"], "identity": str(args.out / "identity.json"),
                      "error": result.get("error")}), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
