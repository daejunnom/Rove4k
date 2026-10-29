#!/usr/bin/env python3
"""Finite fresh-source D compiler/storage comparison; never selects a recipe.

Each case runs the real producer and preserves its own source/flags/native and
whole receipts. This is a cost comparison, not a search, timing or eligibility
certificate. Target profiles are compilation only; no engine is executed.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("test-p4", "test-p28", "tcec-provisional"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--flags-only", action="store_true")
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p / ".git").exists() for p in (out, *out.parents)):
        parser.error("new absolute external output required")
    source = load("d_finite_cost_source", HERE / "source.py")
    if source.pin(source.normalized(ROOT / source.HOST))["sha256"] != source.HOST_SHA:
        raise ValueError("bounded original owner differs")
    tools = load("d_finite_cost_owner", ROOT / source.HOST)
    tools.LIMITS = {**tools.LIMITS, "aggregate_wall": 900, "per_command_wall": 120,
                    "parent_CPU": 330, "parent_CPU_hard": 360,
                    "child_AS": 4 << 30, "child_CPU": 330}
    out.mkdir()
    report = dict(kind="D-general-fresh-source-finite-cost-v1", profile=args.profile,
                  complete=False, cases=[], commands=[], engines_executed=False,
                  selection_changed=False, target_memory_allocated=False)
    def save():
        (out / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    host = tools.Host(out, report, save)
    cases = [("Os", "s", "none"), ("O2", "2", "none"), ("Oz", "z", "none")]
    if not args.flags_only:
        cases += [("prefix-Os", "s", "prefix"), ("dense-Os", "s", "dense"),
                  ("prefix-dense-Os", "s", "prefix-dense")]
    try:
        for name, optimize, storage in cases:
            destination = out / name
            host.run([sys.executable, "-I", "-B", str(HERE / "build.py"),
                      "--profile", args.profile, "--out", str(destination),
                      "--optimize", optimize, "--storage", storage, "--rename-trials", "0"],
                     cwd=ROOT, kind="fresh-producer-" + name)
            raw = (destination / "build.json").read_bytes()
            child = json.loads(raw)
            cleanup = child.get("host_cleanup", {})
            if (not child.get("complete") or not child.get("frozen_execution") or
                    cleanup.get("unsettled_commands") or cleanup.get("errors") or
                    any(not row.get("terminal") or not row.get("reaped") or
                        row.get("returncode") != 0 or row.get("forced_cleanup")
                        for row in child["commands"])):
                raise ValueError("fresh producer is incomplete or unsettled: " + name)
            report["cases"].append(dict(name=name, optimize=optimize, storage=storage,
                receipt=dict(path=str(destination / "build.json"), **source.pin(raw)),
                native=child["native"], resources=child["resource"], candidates=child["candidates"],
                measured_minimum=child["minimum_measured"], runtime_qualified=False))
            save()
        report["measured_minimum"] = min(report["cases"], key=lambda row: row["measured_minimum"]["bytes"])
        report["complete"] = True
        print(json.dumps(dict(cases=len(report["cases"]), minimum=report["measured_minimum"]["name"],
                              whole=report["measured_minimum"]["measured_minimum"]["bytes"],
                              runtime_qualified=False)), flush=True)
    except BaseException as error:
        report["complete"] = False
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        try:
            host.close()
        except BaseException as error:
            report["complete"] = False
            report["cleanup_failure"] = dict(type=type(error).__name__, message=str(error))
            raise
        finally:
            cleanup = report.get("host_cleanup", {})
            if cleanup.get("errors") or cleanup.get("unsettled_commands"):
                report["complete"] = False
            save()


if __name__ == "__main__":
    main()
