#!/usr/bin/env python3
"""Prove selected complete wrappers restore the measured native bytes and pool."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import threading
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT == args.out or ROOT in args.out.parents:
        parser.error("--out must be a new external absolute directory")
    args.out.mkdir(parents=True)
    build = json.loads(args.build.read_bytes())
    report = {"passed": False, "build_sha256": sha(args.build.read_bytes()), "forms": []}
    try:
        for form in ("selected", "selected_native"):
            artifact = build[form]
            path = Path(artifact["path"])
            if sha(path.read_bytes()) != artifact["sha256"]:
                raise AssertionError("complete wrapper bytes changed")
            temporary = args.out / (form + "-tmp")
            temporary.mkdir()
            env = os.environ.copy();env["TMPDIR"] = str(temporary)
            process = subprocess.Popen([str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, env=env, start_new_session=True)
            lines = queue.Queue()
            def read():
                for line in process.stdout:
                    lines.put(line.rstrip())
            reader = threading.Thread(target=read, daemon=True);reader.start()
            transcript = []
            def send(command, expected):
                transcript.append({"stdin": command})
                process.stdin.write(command + "\n");process.stdin.flush()
                while True:
                    line = lines.get(timeout=60)
                    transcript.append({"stdout": line})
                    if line == expected:
                        return
            start = time.monotonic()
            try:
                send("uci", "uciok")
                elapsed = time.monotonic() - start
                proc = Path("/proc") / str(process.pid)
                restored = (proc / "exe").read_bytes()
                if sha(restored) != artifact["restored_native_sha256"]:
                    raise AssertionError({"restored": sha(restored), "expected": artifact["restored_native_sha256"]})
                task_ids = sorted(int(p.name) for p in (proc / "task").iterdir())
                expected_threads = build["engines"][0]["startup_threads"]
                if len(task_ids) != expected_threads:
                    raise AssertionError("pool did not exist before UCI response")
                send("isready", "readyok")
                if task_ids != sorted(int(p.name) for p in (proc / "task").iterdir()):
                    raise AssertionError("startup worker IDs changed")
                leftovers = [str(p.relative_to(temporary)) for p in temporary.rglob("*")]
                if leftovers:
                    raise AssertionError({"temporary_files_after_exec": leftovers})
                process.stdin.write("quit\n");process.stdin.flush();process.wait(timeout=5)
                if process.returncode:
                    raise AssertionError("nonzero wrapper shutdown")
                reader.join(timeout=1)
                report["forms"].append({"form": form, "wrapper_bytes": len(path.read_bytes()),
                    "wrapper_sha256": artifact["sha256"], "format": artifact["format"],
                    "restored_native_sha256": sha(restored), "restored_native_bytes": len(restored),
                    "startup_seconds": elapsed, "startup_thread_ids": task_ids,
                    "startup_threads_stable": True, "temporary_files_after_exec": leftovers,
                    "exit_code": process.returncode, "transcript": transcript})
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL);process.wait()
        report["passed"] = True
    finally:
        (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "forms": [{key: item[key] for key in ("form", "wrapper_bytes", "startup_seconds")} for item in report["forms"]]}))


if __name__ == "__main__":
    main()
