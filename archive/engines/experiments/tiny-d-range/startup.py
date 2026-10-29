#!/usr/bin/env python3
"""Three bounded cold-process exec-to-ready observations; startup is separate.

This includes scheduler/process launch and normal engine startup, not decoder
CPU time alone. It is a local WSL observation, not target timing acceptance.
"""
import argparse
import json
import os
from pathlib import Path
import select
import subprocess
import time

import native_support as support
import test_runtime as runtime


def sample(path):
    begin = time.monotonic_ns()
    process = subprocess.Popen([str(path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    try:
        process.stdin.write(b"isready\n");process.stdin.flush()
        output = bytearray()
        deadline = time.monotonic()+10
        while b"readyok\n" not in output:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise TimeoutError("no startup readiness")
            ready,_,_ = select.select([process.stdout],[],[],remaining)
            if not ready:
                raise TimeoutError("no startup readiness")
            block = os.read(process.stdout.fileno(),4096)
            if not block:
                raise ValueError("startup EOF before readiness")
            output.extend(block)
        elapsed = (time.monotonic_ns()-begin)/1e6
        status = Path(f"/proc/{process.pid}/status").read_text()
        memory = {line.split(":",1)[0]:line.split(":",1)[1].strip() for line in status.splitlines()
                  if line.startswith(("VmPeak:","VmSize:","VmHWM:","VmRSS:","Threads:"))}
        assert memory["Threads"] == "3"
        process.stdin.write(b"quit\n");process.stdin.flush()
        stdout,stderr = process.communicate(timeout=10)
        assert process.returncode == 0
        return {"exec_to_ready_ms":elapsed,"ready_status":memory,"returncode":0}
    finally:
        runtime.cleanup(process)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/".git").exists() for p in (out,*out.parents)):
        parser.error("--out must be new, absolute and outside Git")
    out.mkdir(parents=True)
    build = json.loads(args.build.read_text())
    report = {"complete":False,"build_sha256":support.sha(args.build.read_bytes()),"samples_per_file":3,
              "scope":"WSL local exec-to-ready includes process launch/scheduling/engine startup; no isolated decoder timing claim",
              "results":[],"all_owned_processes_reaped":False}
    try:
        for engine in build["engines"]:
            paths = [("native-control",args.build.parent/engine["id"]/"native-control",engine["input_sha256"])]
            paths += [(c["codec"],Path(c["path"]),c["sha256"]) for c in engine["candidates"]]
            for label,path,digest in paths:
                assert support.sha(path.read_bytes()) == digest
                report["results"].append({"engine":engine["id"],"form":label,"sha256":digest,
                                          "observations":[sample(path) for _ in range(3)]})
        report["complete"] = True
        report["all_owned_processes_reaped"] = True
    except Exception as error:
        report["failure"] = repr(error)
        raise
    finally:
        (out/"startup.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"complete":True,"forms":len(report["results"]),"samples":18,
                      "milliseconds":[{"engine":r["engine"],"form":r["form"],"values":[s["exec_to_ready_ms"] for s in r["observations"]]} for r in report["results"]]}))


if __name__ == "__main__":
    main()
