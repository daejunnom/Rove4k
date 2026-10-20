#!/usr/bin/env python3
"""Freeze one affine candidate and reproduce complete control/candidate ELFs.

This driver never executes an ELF. Its only precompile execution is the separate
Python arithmetic/source proof. Production and candidate use the unchanged,
frozen Tiny D builder, including its ELF audit and exact compiler/linker flags.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from producer import EXPECTED, merged_for_measurement, produce

CONTROLS = {
    "hq": "2c84c684d840ad7e7f0567b2b76d9c28693a00f6f95779675fb45ff84c06d3b3",
    "scalar": "0c364208165b79d95f146650ec8ae144f1e4cb6427197b80f37f0e97a90a4eb3",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rustc", default="rustc")
    args = parser.parse_args()
    source = args.source_dir.resolve()
    out = args.out.resolve()
    checkout = HERE.parents[2]
    if sys.platform != "linux" or platform.machine() != "x86_64":
        parser.error("Linux x86-64 required")
    if not args.out.is_absolute() or out.exists() or out == checkout or checkout in out.parents:
        parser.error("new absolute external output required")
    compiler = shutil.which(args.rustc)
    if compiler is None:
        parser.error("controlled Rust compiler unavailable")
    original = {name: (source / name).read_bytes() for name in EXPECTED}
    candidate, transformation = produce(original)
    out.mkdir(parents=True)
    report = {
        "passed": False,
        "phase": "frozen input; precompile proof pending",
        "scope": "FIRST-COST only; no native executed or new runtime qualification",
        "fixed_resources": {"workers": 2, "tt_bits": 18},
        "transformation": transformation,
        "original_controls": {label: {"bytes": 16824, "sha256": value} for label, value in CONTROLS.items()},
        "builds": {},
    }
    save(out / "cost.json", report)
    try:
        experiment = out / "experiment"
        experiment.mkdir()
        for name in ("producer.py", "value.rs.in", "verify_proof.py", "run_cost.py", "README.md"):
            (experiment / name).write_bytes((HERE / name).read_bytes())
        report["experiment_source_sha256"] = {
            name: sha((experiment / name).read_bytes()) for name in sorted(p.name for p in experiment.iterdir())
        }
        snapshots = {}
        lengths = {}
        for label, files in (("control", original), ("candidate", candidate)):
            local = out / (label + "-source") / "engines/compact/tiny-rust-d"
            local.mkdir(parents=True)
            for name, data in files.items():
                (local / name).write_bytes(data)
            snapshots[label] = local
            merged = merged_for_measurement(files)
            (out / (label + "-merged-measurement.rs")).write_bytes(merged)
            lengths[label] = {
                "readable_rust_files_bytes": sum(len(v) for k, v in files.items() if k.endswith(".rs")),
                "readable_all7_inputs_bytes": sum(map(len, files.values())),
                "board_bytes": len(files["board.rs"]),
                "merged_rust_bytes": len(merged),
                "merged_rust_sha256": sha(merged),
                "merged_is_measurement_only_not_compiled": True,
            }
        report["source_lengths"] = lengths
        (out / "source.diff").write_text("".join(difflib.unified_diff(
            original["board.rs"].decode().splitlines(True), candidate["board.rs"].decode().splitlines(True),
            fromfile="control/board.rs", tofile="candidate/board.rs")), encoding="utf-8")
        proof_command = [sys.executable, "-I", "-B", str(experiment / "verify_proof.py"),
                         "--source-dir", str(source), "--out", str(out / "precompile-proof.json")]
        proof = subprocess.run(proof_command, capture_output=True, text=True, timeout=30)
        save(out / "precompile-proof-process.json", {"command": proof_command,
             "returncode": proof.returncode, "stdout": proof.stdout, "stderr": proof.stderr})
        if proof.returncode:
            raise RuntimeError("independent precompile proof failed")
        proof_report = json.loads((out / "precompile-proof.json").read_text())
        if not proof_report["passed"]:
            raise RuntimeError("independent proof did not pass")
        if (proof_report["source_sha256"] != transformation["input_sha256"]
                or proof_report["candidate_source_sha256"] != transformation["output_sha256"]):
            raise RuntimeError("proved inputs differ from frozen compiler inputs")
        if any(report["experiment_source_sha256"][name] != digest
               for name, digest in proof_report["experiment_input_sha256"].items()):
            raise RuntimeError("proof producer/template differs from frozen experiment")
        report.update(phase="proof passed; fixed control/candidate builds", precompile_proof_passed=True,
                      precompile_proof_sha256=sha((out / "precompile-proof.json").read_bytes()))
        save(out / "cost.json", report)
        for mode in ("hq", "scalar"):
            for label in ("control", "candidate"):
                destination = out / (label + "-" + mode)
                command = [sys.executable, "-I", "-B", str(snapshots[label] / "build.py"),
                           "--out", str(destination), "--rustc", compiler, "--workers", "2",
                           "--tt-bits", "18", "--hq", mode, "--reproduce"]
                execution = subprocess.run(command, capture_output=True, text=True, timeout=390)
                save(out / (label + "-" + mode + "-process.json"), {"command": command,
                     "returncode": execution.returncode, "stdout": execution.stdout, "stderr": execution.stderr})
                if execution.returncode:
                    raise RuntimeError("build failed: " + label + "-" + mode)
                result = json.loads((destination / "build.json").read_text())
                if not result["reproduced"] or not all(result["artifact_gates"].values()):
                    raise RuntimeError("reproduction or ELF admission failed")
                if result["workers"] != 2 or result["tt_bits"] != 18 or result["hq"] != mode:
                    raise RuntimeError("fixed recipe drift")
                if label == "control" and (result["complete_native_bytes"] != 16824
                                           or result["complete_native_sha256"] != CONTROLS[mode]):
                    raise RuntimeError("qualified original whole-native control drift")
                report["builds"][label + "-" + mode] = {
                    "complete_native_bytes": result["complete_native_bytes"],
                    "complete_native_sha256": result["complete_native_sha256"],
                    "independent_reproduction": result["reproduced"],
                    "artifact_gates": result["artifact_gates"],
                    "compiler": result["compiler"],
                    "command_flags_after_remap": result["builds"][0]["command"][3:],
                    "build_report": str(destination / "build.json"),
                    "source_sha256": result["source_sha256"],
                }
                save(out / "cost.json", report)
        flags = [v["command_flags_after_remap"] for v in report["builds"].values()]
        if any(value != flags[0] for value in flags):
            raise RuntimeError("candidate/control compiler recipe changed")
        if any((source / name).read_bytes() != data for name, data in original.items()):
            raise RuntimeError("maintained production source changed during comparison")
        report["complete_native_savings_bytes"] = {
            mode: report["builds"]["control-" + mode]["complete_native_bytes"]
                  - report["builds"]["candidate-" + mode]["complete_native_bytes"] for mode in CONTROLS
        }
        report.update(passed=True, phase="FIRST-COST complete; no runtime executed",
                      exact_same_compiler_flags=True, maintained_production7_unchanged=True,
                      original_controls_reproduced=True,
                      cost_only_stop_before_focused_or_broad_qualification=True)
    except BaseException as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        save(out / "cost.json", report)
    print(json.dumps({"passed": True, "report": str(out / "cost.json"),
                      "whole_native_savings_bytes": report["complete_native_savings_bytes"],
                      "source_lengths": report["source_lengths"]}))


if __name__ == "__main__":
    main()
