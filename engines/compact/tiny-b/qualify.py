#!/usr/bin/env python3
"""Observe the actual selected source wrapper and compiler-stdin ELF identity."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import signal
import subprocess
import threading
import time

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.out.is_absolute():
        parser.error("--out must be absolute")
    args.out = args.out.resolve()
    if not args.out.is_absolute() or args.out.exists() or HERE.parents[2] in args.out.parents:
        parser.error("--out must be a new absolute directory outside the checkout")
    manifest = json.loads((args.build / "validation-manifest.json").read_text())
    spec = next(item for item in manifest["engines"] if item["id"] == "tiny-B-selected")
    parent = next(item for item in manifest["engines"] if item["id"] == spec["selected_from"])
    wrapper = Path(spec["command"][0])
    if sha(wrapper.read_bytes()) != spec["expected_program_sha256"]:
        raise ValueError("selected whole-wrapper bytes changed")
    source = (Path(parent["cwd"]) / "main.c").read_bytes()
    if sha(source) != parent["source_sha256"]:
        raise ValueError("compiler-stdin source changed")
    args.out.mkdir(parents=True)
    (args.out / "source.c").write_bytes(source)
    argv = []
    for item in parent["compile"]:
        argv.extend(["-x", "c", "-"] if item == "main.c" else [item])
    subprocess.run(argv, input=source, cwd=args.out, check=True, timeout=60)
    reference = (args.out / "x").read_bytes()
    subprocess.run(argv, input=source, cwd=args.out, check=True, timeout=60)
    if (args.out / "x").read_bytes() != reference:
        raise ValueError("independent compiler-stdin repeat differs")
    temporary = args.out / "temporary"
    temporary.mkdir()
    environment = os.environ.copy()
    environment["TMPDIR"] = str(temporary)
    process = subprocess.Popen(spec["command"], cwd=spec["cwd"], env=environment,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    lines = queue.Queue()
    def reader():
        for line in process.stdout:
            lines.put(line.rstrip())
    worker = threading.Thread(target=reader, daemon=True)
    worker.start()
    transcript = []
    def send(text):
        transcript.append({"stdin": text})
        process.stdin.write(text + "\n")
        process.stdin.flush()
    def until(prefix):
        end = time.monotonic() + 60
        while True:
            text = lines.get(timeout=max(.01, end - time.monotonic()))
            transcript.append({"stdout": text})
            if text.startswith(prefix):
                return text
    try:
        send("uci")
        until("uciok")
        image = Path(f"/proc/{process.pid}/exe")
        actual = image.read_bytes()
        exe_target = os.readlink(image)
        if actual != reference:
            raise ValueError("actual restored ELF differs from recorded compiler-stdin reference")
        tids = sorted(path.name for path in Path(f"/proc/{process.pid}/task").iterdir())
        if len(tids) != spec["startup_threads"]:
            raise ValueError("unexpected fixed startup threads")
        for _ in range(2):
            send("isready")
            until("readyok")
            if sorted(path.name for path in Path(f"/proc/{process.pid}/task").iterdir()) != tids:
                raise ValueError("startup task identities changed")
        children = Path(f"/proc/{process.pid}/task/{process.pid}/children").read_text().strip()
        if children or list(temporary.iterdir()):
            raise ValueError("compiler/temporary wrapper resources remain after fd-exec")
        send("position startpos")
        send("go wtime 100 btime 100 winc 0 binc 0")
        best = until("bestmove ")
        if re.fullmatch(r"bestmove [a-h][1-8][a-h][1-8][qrbn]?", best) is None:
            raise ValueError("clocked complete source wrapper did not produce a move")
        send("quit")
        process.wait(timeout=3)
        if process.returncode or list(temporary.iterdir()):
            raise ValueError("wrapper failed clean shutdown")
        report = {"passed": True, "whole_file_bytes": wrapper.stat().st_size,
                  "whole_file_sha256": sha(wrapper.read_bytes()), "source_sha256": sha(source),
                  "compiler_stdin_argv": argv, "native_bytes": len(reference),
                  "native_sha256": sha(reference), "native_reproduced": True,
                  "actual_exe_target": exe_target,
                  "startup_task_ids": tids, "startup_threads": len(tids), "children_after_restore": children,
                  "temporary_files_after_restore": [], "transcript": transcript}
        (args.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({key: report[key] for key in ("passed", "whole_file_bytes", "native_sha256", "startup_threads")}))
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


if __name__ == "__main__":
    main()
