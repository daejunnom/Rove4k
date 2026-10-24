#!/usr/bin/env python3
"""One fixed-recipe runtime start-put first cost; never execute a production ELF."""
import argparse
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("frozen_start_producer", HERE / "producer.py")
PRODUCER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRODUCER)
EXPECTED = PRODUCER.EXPECTED
merged_for_measurement = PRODUCER.merged_for_measurement
produce = PRODUCER.produce
CONTROL = {
    "hq": "f8581a68f09d4d9cdc3e1413aa45ffb385bafd8240f1432403629ec2a0e544f8",
    "scalar": "bd0e3bd1567ae906d4ab9704603204d22302895df1f05679f6221d6445aef878",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def run(command, directory, receipt, timeout=90):
    process = subprocess.Popen(command, cwd=directory, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate(timeout=5)
    record = {"command": command, "pid": process.pid, "returncode": process.returncode,
        "timeout": timed_out, "terminal": process.poll() is not None,
        "stdout": stdout.decode(), "stderr": stderr.decode()}
    save(receipt, record)
    if timed_out or process.returncode or len(stdout) + len(stderr) > 1048576:
        raise RuntimeError("bounded command failed: " + str(receipt))
    return record


def section_sizes(text):
    result = {}
    for line in text.splitlines():
        match = re.match(r"\s*\[\s*\d+\]\s+(\S+)\s+\S+\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)", line)
        if match:
            name, address, offset, size = match.groups()
            result[name] = {"address": int(address, 16), "offset": int(offset, 16), "bytes": int(size, 16)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rustc", default="rustc")
    args = parser.parse_args()
    out = args.out.resolve()
    repository = HERE.parents[2]
    if sys.platform != "linux" or platform.machine() != "x86_64":
        parser.error("Linux x86-64 required")
    if not args.out.is_absolute() or out.exists() or out == repository or repository in out.parents:
        parser.error("new absolute external output required")
    compiler = shutil.which(args.rustc)
    if not compiler:
        parser.error("Rust compiler unavailable")
    out.mkdir()
    version = run([compiler, "--version"], out, out / "compiler-version.json", 15)["stdout"]
    if not version.startswith("rustc 1.97.0 "):
        raise RuntimeError("fixed Rust1.97.0 compiler required")
    original = {name: (HERE / "control" / name).read_bytes() for name in EXPECTED}
    candidate, metadata = produce(original)
    sources = {"control": original, "candidate": candidate}
    frozen = out / "experiment-inputs"
    frozen.mkdir()
    for name in ("producer.py", "start.rs.in", "run_cost.py"):
        (frozen / name).write_bytes((HERE / name).read_bytes())
    (out / "board-source.diff").write_text("".join(difflib.unified_diff(
        original["board.rs"].decode().splitlines(True), candidate["board.rs"].decode().splitlines(True),
        fromfile="control/board.rs", tofile="candidate/board.rs")))
    report = {"passed": False, "scope": "one runtime start-put constructor; complete native cost only",
        "metadata": metadata, "compiler": version.strip(), "workers": 2, "tt_bits": 18,
        "production_ELF_executed": False, "packed_artifact_created_or_executed": False,
        "source": {}, "profiles": {}}
    try:
        for kind, files in sources.items():
            source = out / (kind + "-source") / "engines/compact/tiny-rust-d"
            source.mkdir(parents=True)
            for name, data in files.items():
                (source / name).write_bytes(data)
            merged = merged_for_measurement(files)
            (out / (kind + "-merged-measurement.rs")).write_bytes(merged)
            report["source"][kind] = {"path": str(source),
                "sha256": {n: sha(b) for n, b in files.items()},
                "readable_Rust_bytes": sum(len(b) for n, b in files.items() if n.endswith(".rs")),
                "merged_measurement_bytes": len(merged), "merged_was_compiled": False}
            for lane in ("hq", "scalar"):
                destination = out / (kind + "-" + lane)
                run([sys.executable, "-I", "-B", str(source / "build.py"),
                    "--out", str(destination), "--rustc", compiler,
                    "--workers", "2", "--tt-bits", "18", "--hq", lane, "--reproduce"],
                    out, out / (kind + "-" + lane + "-command.json"))
                build = json.loads((destination / "build.json").read_text())
                if build["source_sha256"] != report["source"][kind]["sha256"]:
                    raise RuntimeError("frozen source drift")
                if not build["reproduced"] or not all(build["artifact_gates"].values()):
                    raise RuntimeError("native reproduction or static gate failed")
                if kind == "control" and (build["complete_native_bytes"] != 16816 or build["complete_native_sha256"] != CONTROL[lane]):
                    raise RuntimeError("old control literal did not reproduce")
                native = destination / "first/x"
                audit = destination / "first/x.unstripped"
                symbols = run(["nm", "-S", "--size-sort", "--demangle", str(audit)],
                    out, out / (kind + "-" + lane + "-symbols.json"), 15)["stdout"]
                functions = {}
                for line in symbols.splitlines():
                    fields = line.split(maxsplit=3)
                    if len(fields) == 4:
                        functions[fields[3]] = {"address": "0x" + fields[0], "bytes": int(fields[1], 16)}
                value = {"build_report": str(destination / "build.json"), "native": str(native),
                    "complete_ELF_bytes": build["complete_native_bytes"],
                    "sha256": build["complete_native_sha256"], "independently_reproduced": True,
                    "sections": section_sizes((destination / "sections.txt").read_text()),
                    "functions": functions, "normal_builds": 2, "unstripped_audits": 1}
                report["profiles"][kind + "-" + lane] = value
                print(json.dumps({"form": kind + "-" + lane, "bytes": value["complete_ELF_bytes"],
                    "sha256": value["sha256"], "text": value["sections"][".text"]["bytes"],
                    "rodata": value["sections"][".rodata"]["bytes"], "data": value["sections"][".data"]["bytes"]}), flush=True)
        report["deltas"] = {}
        for lane in ("hq", "scalar"):
            old, new = (report["profiles"][kind + "-" + lane] for kind in ("control", "candidate"))
            report["deltas"][lane] = {"complete_ELF_bytes": new["complete_ELF_bytes"] - old["complete_ELF_bytes"],
                **{section + "_bytes": new["sections"][section]["bytes"] - old["sections"][section]["bytes"]
                   for section in (".text", ".rodata", ".data")}}
        report["source_deltas"] = {name: report["source"]["candidate"][name] - report["source"]["control"][name]
            for name in ("readable_Rust_bytes", "merged_measurement_bytes")}
        report["passed"] = True
    finally:
        save(out / "cost.json", report)
    print(json.dumps({"passed": True, "report": str(out / "cost.json"), "deltas": report["deltas"],
        "source_deltas": report["source_deltas"], "production_ELF_executed": False}))


if __name__ == "__main__":
    main()
