#!/usr/bin/env python3
"""Run reviewed local engine manifests sequentially; codecs may use small pools.

No downloads, dependency installs, source edits, resource-constant changes or
remote writes occur. Every report distinguishes measured and UCI-accepted files.
An unavailable runtime is recorded, never converted into a successful UCI test.
"""
import argparse
import csv
import json
from pathlib import Path
import sys

import nvenvelope


def quarantine_accepted(directory: Path) -> dict:
    """Move only this run's owned accepted entry; preserve all search evidence."""
    accepted = directory / "accepted"
    if not accepted.exists() and not accepted.is_symlink():
        return {"status": "not_present"}
    target = directory / "rejected-campaign"
    suffix = 0
    while target.exists() or target.is_symlink():
        suffix += 1
        target = directory / ("rejected-campaign-%d" % suffix)
    accepted.rename(target)
    return {"status": "quarantined", "from": "accepted", "path": target.name}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifests", type=Path, default=Path(__file__).parent/"engines")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--only", nargs="+")
    parser.add_argument("--thorough", action="store_true")
    parser.add_argument("--pack-only", action="store_true")
    parser.add_argument("--oracle-path")
    parser.add_argument("--uci-config", type=Path)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--max-protocol-candidates", type=int, default=16)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 16 or not 1 <= args.max_protocol_candidates <= 256:
        parser.error("jobs must be1..16; protocol candidates1..256")
    # Replay runs in an engine-specific output directory. Resolve user inputs
    # against the invocation directory before passing them to child processes.
    if args.oracle_path:
        args.oracle_path = str(Path(args.oracle_path).resolve(strict=True))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifests = sorted(args.manifests.glob("*.json"))
    if args.only:
        missing = set(args.only)-{p.stem for p in manifests}
        if missing:
            parser.error("unknown engine names: " + ", ".join(sorted(missing)))
        manifests = [p for p in manifests if p.stem in args.only]
    coordinator_sha256 = nvenvelope.sha(Path(__file__).read_bytes())
    rows = []
    for path in manifests:
        name = path.stem
        directory = output / name
        row = {"engine": name}
        validation = {"format": "nvcompact.campaign-validation.v1", "engine": name,
                      "coordinator_sha256": coordinator_sha256,
                      "envelope_summary": "summary.json", "phase": "search",
                      "status": "running", "replays": []}
        print(json.dumps({"engine": name, "phase": "search"}), flush=True)
        try:
            report = nvenvelope.run(path, directory, thorough=args.thorough, jobs=args.jobs,
                                    uci=not args.pack_only, oracle_path=args.oracle_path,
                                    uci_config=json.loads(args.uci_config.read_text()) if args.uci_config else None,
                                    max_protocol_candidates=args.max_protocol_candidates)
            row = {"engine": name, "original_bytes": report["original_bytes"],
                   "smallest_bytes": report["winner"]["bytes"], "saved_bytes": report["saved_bytes"],
                   "candidates": report["candidates"], "source_variant": report["winner"]["variant"],
                   "accepted_bytes": report["accepted"]["bytes"] if report["accepted"] else None,
                   "uci": report["uci"].get("candidate_strict_verdict", report["uci"].get("status")),
                   "original_uci": report["uci"].get("baseline_strict_verdict"),
                   "summary": name+"/summary.json"}
            # Reproduce the measured minimum even when it is not acceptable.
            # A different accepted file needs its own source/codec replay and
            # UCI gate; a byte-identical accepted file shares the minimum's gate.
            accepted = report["accepted"]
            shared = bool(accepted and accepted["sha256"] == report["winner"]["sha256"])
            plans = [("smallest", report["winner"], "independent-replay", "replay", shared)]
            if accepted and not shared:
                plans.append(("accepted", accepted, "independent-replay-accepted", "replay-accepted", True))
            validation["phase"] = "independent_replay"
            for selection, record, folder, logs, uci in plans:
                replay = [sys.executable, str(Path(__file__).parent/"nvreproduce.py"),
                          str(directory/"summary.json"), "--output", str(directory/folder),
                          "--selection", selection]
                if uci:
                    replay += ["--uci"]
                    if args.oracle_path:
                        replay += ["--oracle-path", args.oracle_path]
                    if args.uci_config:
                        replay += ["--uci-config", str(args.uci_config.resolve())]
                attempt = {"selection": selection, "expected_sha256": record["sha256"],
                           "uci_requested": uci, "also_verifies_accepted": shared,
                           "report": folder + "/replay.json", "argv": replay,
                           "stdout": logs + ".stdout", "stderr": logs + ".stderr",
                           "status": "running"}
                validation["replays"].append(attempt)
                try:
                    result = nvenvelope.bounded_command(replay, b"", directory, timeout=480)
                    (directory/(logs + ".stdout")).write_bytes(result["stdout"])
                    (directory/(logs + ".stderr")).write_bytes(result["stderr"])
                    attempt["returncode"] = result["returncode"]
                    if result["returncode"]:
                        raise ValueError("independent %s replay failed; inspect %s.stderr and fix the underlying cause" % (selection, logs))
                    attempt["status"] = "pass"
                except Exception as exc:
                    attempt.update(status="error", error=str(exc))
                    raise
            validation.update(status="pass", phase="complete",
                              accepted_verdict="pass" if accepted else "not_available")
            row["independent_replay"] = "pass"
        except Exception as exc:
            validation.update(status="error", error=str(exc), accepted_verdict="rejected")
            try:
                validation["accepted_quarantine"] = quarantine_accepted(directory)
            except OSError as quarantine_error:
                validation["accepted_quarantine"] = {"status": "error", "error": str(quarantine_error)}
            row.update(error=str(exc), independent_replay="error", accepted_bytes=None)
            nvenvelope.write_json(directory/"campaign-error.json", {**row, "validation": validation})
        row["coordinator_validation"] = name + "/coordinator-validation.json"
        nvenvelope.write_json(directory/"coordinator-validation.json", validation)
        rows.append(row)
        nvenvelope.write_json(output/"results.json", rows)
        print(json.dumps(row), flush=True)
    columns = ["engine", "original_bytes", "smallest_bytes", "saved_bytes", "candidates", "source_variant",
               "accepted_bytes", "original_uci", "uci", "independent_replay", "summary", "error", "coordinator_validation"]
    with (output/"results.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return 2 if any(row.get("error") for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
