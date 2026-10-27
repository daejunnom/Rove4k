"""Build a pre-GO diagnostic cohort from an independently frozen TEST plan.

This is an adapter, not an admission, capacity check or a game launcher.
The actual cgroups remain owned by a separate supervisor.  No GO is issued by
this module.  The diagnostic repeats frozen pairs when the cohort is larger
than the plan; its observations must never be counted as league results or
as a bound on any unobserved player pairing or search workload.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from . import ledger, run, topology
except ImportError:
    import ledger
    import run
    import topology


def build_probe_inputs(plan_path, output_root, *, wall_seconds=180):
    """Bind every diagnostic slot to a validated plan and its exact artifacts.

    The returned controller manifest and artifact map use whole submission
    hashes separately from post-start native image hashes.  Neither value is
    a claim about a source-code digest.  ``load_plan`` is the qualification
    boundary; until P16/P192 qualification is enabled it rejects those plans.
    """
    plan_path = run.protected_input(Path(plan_path))
    output_root = run.external_new(Path(output_root))
    if type(wall_seconds) not in (int, float) or not 0 < wall_seconds <= 180:
        raise ValueError("a positive bounded pre-GO deadline is required")
    envelope, rows = run.load_plan(plan_path)
    body = envelope["content"]
    profile = body["profile"]
    count = {"test-p16": 11, "test-p192": 1}.get(profile)
    if count is None or len(body["slots"]) != count:
        raise ValueError("a complete named P16 or P192 frozen cohort is required")
    pairs = body["pairs"]
    if not pairs:
        raise ValueError("at least one validated frozen pair is required")
    players = {row["artifact"].id: row["artifact"] for row in rows}
    if len(players) != len(rows):
        raise ValueError("duplicate player identity")
    bundle = plan_path.parent
    entries, artifacts = [], {}
    for index, slot in enumerate(body["slots"]):
        pair = pairs[index % len(pairs)]
        selected = pair["players"]
        if ((index // len(pairs)) % 2):
            selected = list(reversed(selected))
        if len(selected) != 2 or len(set(selected)) != 2 or not set(selected) <= set(players):
            raise ValueError("frozen pair must identify two distinct admitted players")
        if slot["id"] in artifacts:
            raise ValueError("duplicate frozen slot")
        chosen = [players[name] for name in selected]
        entries.append({"slot": slot, "engines": [
            {"id": artifact.id, "path": str(artifact.path), "whole_sha256": artifact.sha256,
             "native_sha256": artifact.native_sha256, "tt_bytes": artifact.tt_bytes} for artifact in chosen],
            "opening_start": pair["opening_index"], "out": str(output_root / "jobs" / slot["id"])})
        artifacts[slot["id"]] = [{"id": artifact.id, "whole_sha256": artifact.sha256,
                                  "native_sha256": artifact.native_sha256, "tt_bytes": artifact.tt_bytes}
                                 for artifact in chosen]
    ancestor = topology.Topology.from_record(body["topology"])
    manifest = {"format": "rove4k-pre-go-controller-v2", "profile": profile, "entries": entries,
                "runner": str(run.bundle_path(bundle, body["runner"]["path"])),
                "runner_sha256": body["runner"]["sha256"],
                "opening": str(run.bundle_path(bundle, body["opening_pgn"])),
                "opening_sha256": body["opening_pgn_sha256"],
                "topology": body["topology"],
                "saved_ancestor_cpus": list(ancestor.allowed_cpus), "wall_seconds": wall_seconds}
    return {"plan_sha256": envelope["sha256"], "manifest": manifest, "artifacts": artifacts,
            "runtime_admission": False, "scored_qualification": False}


def write_probe_inputs(plan_path, output_root, *, wall_seconds=180):
    """Write a fresh external manifest and artifact map; do not create cgroups."""
    data = build_probe_inputs(plan_path, output_root, wall_seconds=wall_seconds)
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=False)
    manifest_bytes = ledger.canonical(data["manifest"])
    manifest_path = root / "manifest.json"
    manifest_path.write_bytes(manifest_bytes)
    artifact_path = root / "artifacts.json"
    artifact_path.write_bytes(ledger.canonical(data["artifacts"]))
    return {"plan_sha256": data["plan_sha256"], "manifest_path": str(manifest_path),
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "artifacts_path": str(artifact_path),
            "artifacts_sha256": hashlib.sha256(ledger.canonical(data["artifacts"])).hexdigest(),
            "runtime_admission": False, "scored_qualification": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare a pinned diagnostic cohort; never start games")
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--wall-seconds", type=float, default=180)
    args = parser.parse_args(argv)
    print(json.dumps(write_probe_inputs(args.plan, args.out, wall_seconds=args.wall_seconds),
                     sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
