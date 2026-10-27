"""Assemble a supervisor-owned, pre-GO cohort observation.

The caller owns and retains the already-created delegated cgroups and the
returned child handle. This diagnostic never grants GO, spends an AWS budget,
proves resident TT pages, or qualifies a scored league. It must run on the
target Linux host, with all outputs outside the repository. Receipt integrity
and a matching digest do not authenticate the producer or prove a measurement:
fabricated samples can match them. Executable hash-to-exec races and external
cgroup writers are not fenced. The receipt must not be used for admission.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

try:
    from . import overhead, peak_capacity, peak_ready_probe, placement, run, topology
except ImportError:
    import overhead
    import peak_capacity
    import peak_ready_probe
    import placement
    import run
    import topology


def observe_ready(*, manifest_path, manifest_sha256, root, games, controller,
                  artifacts, report_path, append, per_game_headroom_bytes,
                  controller_headroom_bytes, timeout_seconds=180, max_age_ns=60_000_000_000):
    """Connect the pinned controller, live groups and independent report context.

    ``games`` maps each frozen slot ID to its original cgroup identity record;
    ``artifacts`` maps each ID to two ordered {id, whole_sha256,
    native_sha256, tt_bytes} records. Neither a supplied manifest nor a
    supplied group record authenticates the owner or proves resource capacity.
    The receipt has no producer authentication and cannot establish that its
    purported process samples actually occurred.
    Any launched controller remains the caller's responsibility even on an
    exception (see SupervisorFailure.process).
    """
    manifest_path = run.protected_input(Path(manifest_path))
    manifest = peak_ready_probe.load_controller_manifest(manifest_path, manifest_sha256)
    entries = manifest["entries"]
    ids = [entry["slot"].id for entry in entries]
    if (type(games) is not dict or type(artifacts) is not dict or
            len(ids) != len(set(ids)) or set(games) != set(ids) or set(artifacts) != set(ids)):
        raise ValueError("one original group and ordered artifact pair per frozen slot required")
    root = Path(root)
    if not root.is_absolute() or ".." in root.parts or any(part.is_symlink() for part in (root, *root.parents)) or root.resolve(strict=True) != root:
        raise ValueError("original delegated root must be a real absolute non-symlink path")
    controller_path = peak_capacity._owned_path(controller, root)
    controller_live = placement.verify_cgroup_live(controller)
    parent = controller_path.parent
    parent_stat = parent.stat()
    # Compare against target cgroup effective masks, not this observer's
    # potentially narrower CPU and node affinity. A live snapshot is not
    # proof of trusted ownership or exclusion of a concurrent writer.
    current = topology.Topology.snapshot_target(parent, device=parent_stat.st_dev, inode=parent_stat.st_ino)
    if json.loads(json.dumps(current.to_record())) != manifest["topology"]:
        raise ValueError("current target topology differs from the frozen plan")
    game_plans, expected_plan = [], []
    for entry in entries:
        slot = entry["slot"]
        game_path = peak_capacity._owned_path(games[slot.id], root)
        if game_path.parent != parent:
            raise ValueError("game and controller cgroups must have the same original parent")
        group = placement.verify_cgroup_live(games[slot.id])
        if group["cpus"] != sorted(slot.cpus) or group["memory_nodes"] != sorted(slot.memory_nodes):
            raise ValueError("original group masks differ from frozen slot")
        if not set(slot.memory_nodes) <= set(controller_live["memory_nodes"]):
            raise ValueError("controller memory nodes must include every game node before placement")
        pair, commands = artifacts[slot.id], entry["engines"]
        if (type(pair) is not list or len(pair) != 2 or type(commands) is not list or len(commands) != 2 or
                any(type(a) is not dict or type(c) is not dict or
                    set(a) != {"id", "whole_sha256", "native_sha256", "tt_bytes"} or
                    set(c) != {"id", "path", "whole_sha256", "native_sha256", "tt_bytes"} or
                    (a["id"], a["whole_sha256"], a["native_sha256"], a["tt_bytes"]) !=
                    (c["id"], c["whole_sha256"], c["native_sha256"], c["tt_bytes"])
                    for a, c in zip(pair, commands))):
            raise ValueError("artifact identity or colour order differs from controller manifest")
        game_plans.append({"slot": slot.id, "path": group["path"], "cpus": sorted(slot.cpus),
                           "nodes": sorted(slot.memory_nodes), "artifacts": pair})
        expected_plan.append({"slot": slot.id, "cgroup_path": group["path"], "cpus": sorted(slot.cpus),
                              "nodes": sorted(slot.memory_nodes), "artifacts": pair})
    if type(max_age_ns) is not int or max_age_ns <= 0:
        raise ValueError("positive receipt age bound required")
    root = str(root)
    python = str(Path(sys.executable).resolve(strict=True))
    controller_sha256 = overhead._sha_file(Path(python))
    observer_sha256 = overhead._sha_file(Path(overhead.__file__).resolve())
    boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip().lower()
    args = {"profile": manifest["profile"], "root": root, "games": game_plans,
            "controller": controller_live["path"], "runner_sha256": manifest["runner_sha256"],
            "frozen_topology": manifest["topology"], "group_records": games,
            "controller_record": controller,
            "controller_sha256": controller_sha256,
            "argv": [python, str(Path(peak_ready_probe.__file__).resolve()), "--manifest", str(manifest_path),
                     "--manifest-sha256", manifest_sha256],
            "per_game_headroom_bytes": per_game_headroom_bytes,
            "controller_headroom_bytes": controller_headroom_bytes, "timeout_seconds": timeout_seconds}

    def expected_context():
        return {"profile": manifest["profile"], "plan": expected_plan, "boot_id": boot_id,
                "cgroup_root": root, "controller_cgroup_path": controller_live["path"],
                "runner_sha256": manifest["runner_sha256"], "controller_sha256": controller_sha256,
                "observer_source_sha256": observer_sha256, "now_monotonic_ns": time.monotonic_ns(),
                "max_age_ns": max_age_ns}

    return peak_ready_probe.observe_and_record(observe_args=args, expected_context=expected_context,
                                               report_path=report_path, append=append)
