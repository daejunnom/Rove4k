#!/usr/bin/env python3
"""Compare actual normalized single-worker search state for two assembled TUs.

The controlled sentinel board must normalize hashes and move tie ordering. This
driver compares actual completed work, learned state and every TT slot; it does
not substitute perft or a duplicate search model. All products stay outside Git.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
COUNTERS = ("nodes", "atomic_nodes", "pvs", "qs", "hits", "hist", "cont", "corr", "corr_use", "abort")
DIGESTS = ("root_hash", "root_context", "learning_path", "history", "continuation", "correction", "path", "tt", "tt_keys", "tt_data")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def differences(left, right):
    result = []
    for index, (before, after) in enumerate(zip(left, right)):
        changed = {key: {"baseline": before.get(key), "candidate": after.get(key)}
                   for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)}
        if changed:
            result.append({"case": index, "fields": changed})
    if len(left) != len(right):
        result.append({"record_count": {"baseline": len(left), "candidate": len(right)}})
    return result


def records_from(data):
    records = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    if len(records) != 12:
        raise ValueError("expected exactly twelve actual search fixture records")
    for index, record in enumerate(records):
        if record.get("case") != index:
            raise ValueError("fixture order/index changed")
        for field in COUNTERS + ("best", "score", "depth", "root_eval", "root_halfmove", "tt_entries", "stopped"):
            if not isinstance(record.get(field), int):
                raise ValueError("missing integer field: " + field)
        for field in DIGESTS:
            if not isinstance(record.get(field), str) or re.fullmatch("[a-f0-9]{16}", record[field]) is None:
                raise ValueError("invalid normalized digest: " + field)
        if re.fullmatch(r"0000|[a-h][1-8][a-h][1-8][qrbn]?", record.get("best_uci", "")) is None:
            raise ValueError("invalid public best-move text")
        if record["nodes"] != record["atomic_nodes"]:
            raise ValueError("single-worker node counters disagree")
    for field in ("pvs", "qs", "hits", "hist", "cont", "corr", "corr_use"):
        if not any(record[field] > 0 for record in records):
            raise ValueError("required actual search branch was not observed: " + field)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-source", type=Path, required=True, help="absolute complete readable DEV-capable C TU")
    parser.add_argument("--sentinel-source", type=Path, required=True, help="absolute complete controlled sentinel C TU")
    parser.add_argument("--out", type=Path, required=True, help="new absolute external output directory")
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--sanitize", action="store_true", help="also repeat both actual harnesses with ASAN and UBSAN")
    parser.add_argument("--timeout", type=float, default=120, help="bounded seconds per compile or fixture process")
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists():
        parser.error("--out must be a new absolute external directory")
    args.out = args.out.resolve()
    if args.out == ROOT or ROOT in args.out.parents:
        parser.error("artifacts must stay outside the checkout")
    for path in (args.baseline_source, args.sentinel_source):
        if not path.is_absolute() or not path.is_file() or path.suffix != ".c":
            parser.error("both source inputs must be absolute existing .c translation units")
    if not 0 < args.timeout <= 600:
        parser.error("--timeout must be in (0,600]")

    args.out.mkdir(parents=True)
    frozen = args.out / "frozen"
    frozen.mkdir()
    fixture = (HERE / "compare.c.in").read_bytes()
    driver = Path(__file__).read_bytes()
    (frozen / "compare.c.in").write_bytes(fixture)
    (frozen / "compare.py").write_bytes(driver)
    inputs = {"baseline": args.baseline_source.read_bytes(), "sentinel": args.sentinel_source.read_bytes()}
    for name, data in inputs.items():
        (frozen / (name + ".c")).write_bytes(data)
    report = {
        "schema": 1, "passed": False,
        "scope": "twelve actual deterministic controlled single-worker search fixtures; no SMP or speed claim",
        "configuration": {"DEV": 1, "WORKERS": 1, "TT_BITS": 18, "CONTROLLED": 1},
        "source_sha256": {name: sha(data) for name, data in inputs.items()},
        "source_paths": {"baseline": str(args.baseline_source), "sentinel": str(args.sentinel_source)},
        "driver_sha256": sha(driver), "fixture_sha256": sha(fixture), "byteorder": sys.byteorder,
        "normalization": {
            "history": "128x128 canonical 0x88 projection, offboard zero and unused source cells asserted zero",
            "continuation": "old black indices 0..5 -> new 12..7; old empty6 -> new0; old white7..12 -> new1..6",
            "tt": "normalize only low17 move bits; preserve upper data bits, full key, slot and table traversal",
            "keys_correction": "unchanged full path-key and correction arrays under controlled equal hash semantics",
        },
        "runs": [], "comparisons": [],
        "excluded": ["all-position proof", "SMP determinism/scalability", "NPS/strength", "4K eligibility"],
    }
    save(args.out / "results.json", report)
    try:
        version = subprocess.run([args.cc, "--version"], check=True, capture_output=True, timeout=args.timeout)
        report["compiler"] = version.stdout.decode(errors="replace").splitlines()[0]
        forms = ("normal", "asan-ubsan") if args.sanitize else ("normal",)
        reference = None
        for form in forms:
            pair = {}
            for index, name in enumerate(("baseline", "sentinel")):
                directory = args.out / form / name
                directory.mkdir(parents=True)
                harness = b"#define main compared_engine_main\n" + inputs[name] + b"\n#undef main\n" + fixture
                (directory / "harness.c").write_bytes(harness)
                flags = ["-std=c11", "-pthread", "-DDEV=1", "-DWORKERS=1", "-DTT_BITS=18", "-DCONTROLLED=1",
                         "-DSENTINEL_COMPARE=" + str(index)]
                if form == "normal":
                    flags += ["-O2"]
                else:
                    flags += ["-O1", "-g", "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                              "-fno-omit-frame-pointer", "-fno-pie", "-no-pie"]
                command = [args.cc, *flags, "harness.c", "-o", "x"]
                run = {"form": form, "engine": name, "command": command, "cwd": str(directory),
                       "harness_sha256": sha(harness), "compiled": False, "executed": False}
                report["runs"].append(run)
                built = subprocess.run(command, cwd=directory, capture_output=True, timeout=args.timeout)
                (directory / "compile.stdout").write_bytes(built.stdout)
                (directory / "compile.stderr").write_bytes(built.stderr)
                run["compile_returncode"] = built.returncode
                if built.returncode:
                    raise RuntimeError("compile failed; inspect " + str(directory / "compile.stderr"))
                run["compiled"] = True
                run["native_sha256"] = sha((directory / "x").read_bytes())
                environment = None
                if form == "asan-ubsan":
                    environment = os.environ.copy()
                    environment["ASAN_OPTIONS"] = "detect_leaks=1:halt_on_error=1"
                    environment["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
                executed = subprocess.run([str(directory / "x")], cwd=directory, env=environment,
                                          capture_output=True, timeout=args.timeout)
                (directory / "runtime.stdout").write_bytes(executed.stdout)
                (directory / "runtime.stderr").write_bytes(executed.stderr)
                run["runtime_returncode"] = executed.returncode
                if executed.returncode or executed.stderr:
                    raise RuntimeError("actual harness failed; inspect " + str(directory / "runtime.stderr"))
                run["executed"] = True
                pair[name] = records_from(executed.stdout)
                save(directory / "records.json", pair[name])
                run["record_count"] = len(pair[name])
                run["records_sha256"] = sha(executed.stdout)
                save(args.out / "results.json", report)
                print(json.dumps({"form": form, "engine": name, "actual_records": len(pair[name])}), flush=True)
            changed = differences(pair["baseline"], pair["sentinel"])
            report["comparisons"].append({"form": form, "baseline_vs_sentinel_equal": not changed, "differences": changed})
            if reference is None:
                reference = pair["baseline"]
            else:
                for name in ("baseline", "sentinel"):
                    changed_form = differences(reference, pair[name])
                    report["comparisons"].append({"form": form, "engine": name,
                                                   "normal_reference_equal": not changed_form, "differences": changed_form})
            save(args.out / "results.json", report)
        report["passed"] = all(not item["differences"] for item in report["comparisons"])
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    save(args.out / "results.json", report)
    print(json.dumps({"passed": report["passed"], "report": str(args.out / "results.json"),
                      "error": report.get("error")}), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
