#!/usr/bin/env python3
"""Bounded native-size comparison on one frozen D shipping source recipe.

Keep algorithms, 64-bit ABI, fixed resources and public commands unchanged.
Every complete candidate is rebuilt independently and executes a clocked search
before a minimum is reported. This is a code-generation size study, not NPS or
playing-strength evidence. Artifacts and reports must remain outside Git.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import threading
import time

HERE = Path(__file__).resolve().parent


CONFIGURATIONS = (
    ("os-lto", ["-Os", "-flto"]),
    ("oz-lto", ["-Oz", "-flto"]),
    ("os", ["-Os"]),
    ("oz", ["-Oz"]),
    ("oz-lto-no-once", ["-Oz", "-flto", "-fno-inline-functions-called-once"]),
    ("oz-lto-no-inline", ["-Oz", "-flto", "-fno-inline"]),
    ("oz-lto-whole", ["-Oz", "-flto", "-fwhole-program"]),
    ("os-lto-align1", ["-Os", "-flto", "-falign-functions=1", "-falign-jumps=1", "-falign-labels=1", "-falign-loops=1"]),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def smoke(path, threads):
    process = subprocess.Popen([str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True)
    lines = queue.Queue()
    transcript = []
    def read():
        for line in process.stdout:
            lines.put(line.strip())
        lines.put(None)
    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    def until(expected):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            line = lines.get(timeout=max(.01, deadline-time.monotonic()))
            transcript.append({"stdout": line})
            if line is None:
                raise AssertionError("engine exited before " + expected)
            if line.startswith(expected):
                return line
        raise TimeoutError(expected)
    def send(command):
        transcript.append({"stdin": command})
        process.stdin.write(command + "\n")
        process.stdin.flush()
    try:
        deadline = time.monotonic() + 5
        tasks = set()
        while len(tasks) != threads and time.monotonic() < deadline:
            tasks = set((Path("/proc") / str(process.pid) / "task").iterdir())
            time.sleep(.01)
        if len(tasks) != threads:
            raise AssertionError("fixed startup worker count differs")
        ids = sorted(int(task.name) for task in tasks)
        send("uci");until("uciok")
        send("isready");until("readyok")
        send("position startpos moves e2e4 e7e5")
        send("go wtime 1000 btime 1000 winc 0 binc 0")
        best = until("bestmove ")
        if best.endswith("0000"):
            raise AssertionError("live root has no witness")
        if ids != sorted(int(p.name) for p in (Path("/proc") / str(process.pid) / "task").iterdir()):
            raise AssertionError("worker identities changed")
        send("quit")
        process.wait(timeout=5)
        reader.join(timeout=1)
        if process.returncode:
            raise AssertionError("engine exit " + str(process.returncode))
        return {"status": "pass", "startup_task_ids": ids, "exit_code": process.returncode, "transcript": transcript}
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


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
    spec = importlib.util.spec_from_file_location("tiny_d_frozen_build", args.build.parent / "sources/build.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    manifest = json.loads(args.build.read_text())
    records = []
    for name, flags in CONFIGURATIONS:
        for engine in manifest["engines"]:
            if engine["profile"] != "shipping":
                continue
            directory = args.out / name / engine["id"]
            directory.mkdir(parents=True)
            command = [arg for arg in engine["compile"][:-1] if not arg.startswith("-O") and arg != "-flto"]
            command[1:1] = flags
            native = directory / "x"
            compile_command = command + [str(directory / "linked")]
            subprocess.run(compile_command, check=True, timeout=120)
            binary = builder.strip_sections((directory / "linked").read_bytes())
            subprocess.run(command + [str(directory / "linked-second")], check=True, timeout=120)
            if builder.strip_sections((directory / "linked-second").read_bytes()) != binary:
                raise RuntimeError("native reproduction differs")
            native.write_bytes(binary)
            native.chmod(0o755)
            check = smoke(native, engine["startup_threads"])
            records.append({"configuration": name, "id": engine["id"], "native_bytes": len(binary),
                            "native_sha256": sha(binary), "native_reproduced": True,
                            "compile": compile_command, "command": [str(native)],
                            "startup_threads": engine["startup_threads"], "profile": "shipping", "smoke": check})
            (args.out / "results.json").write_text(json.dumps({"source_manifest_sha256": sha(args.build.read_bytes()),
                "source_sha256": manifest["source_sha256"], "forms": records}, indent=2) + "\n")
            print(json.dumps({k: records[-1][k] for k in ("configuration", "id", "native_bytes")}), flush=True)
    print(str(args.out / "results.json"))


if __name__ == "__main__":
    main()
