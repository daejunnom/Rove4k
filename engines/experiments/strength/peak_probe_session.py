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
import os
from pathlib import Path
import sys
import time

try:
    from . import overhead, peak_capacity, peak_ready_probe, peak_supervisor, placement, run, topology
except ImportError:
    import overhead
    import peak_capacity
    import peak_ready_probe
    import peak_supervisor
    import placement
    import run
    import topology


class CohortSetupFailure(RuntimeError):
    """Preserve original identities and cleanup errors after partial setup."""
    def __init__(self, message, *, records, cleanup_errors, owner=None):
        super().__init__(message)
        self.records = records
        self.cleanup_errors = cleanup_errors
        self.owner = owner


def _require_delegated_root(root):
    """Check the visible cgroup2 mount before changing a delegated subtree.

    A visible cgroup2 root does not prove that a cgroup namespace exposes all
    host ancestors or that other writers are excluded.
    """
    mount = Path("/sys/fs/cgroup")
    if os.name != "posix" or not root.is_relative_to(mount) or root == mount:
        raise ValueError("a dedicated descendant of the visible cgroup2 mount is required")
    mountinfo = Path("/proc/self/mountinfo").read_text(encoding="utf-8")
    record = peak_capacity.memory_observation._mount_record(mountinfo, mount)
    root_stat, mount_stat = root.stat(), mount.stat()
    device = f"{os.major(mount_stat.st_dev)}:{os.minor(mount_stat.st_dev)}"
    if root_stat.st_dev != mount_stat.st_dev or record["device"] != device:
        raise ValueError("delegated root does not belong to the visible cgroup2 mount")
    for name in ("cgroup.controllers", "cgroup.subtree_control", "cgroup.events"):
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("delegated cgroup2 root lacks required kernel attributes")
    return root_stat


class OwnedProbeCohort:
    """Own a new controller/game cgroup cohort for an existing probe manifest.

    The caller retains this object until all children have physically ended.
    The manager enables cpuset and memory in the caller-delegated root and
    creates a fresh campaign subtree; enabling those root controllers is not
    reverted by cleanup. This is not proof of exclusive access, available
    physical-memory reservation, trusted provenance or scored admission. The
    supervisor still checks live capacity before a pre-GO diagnostic starts;
    the observation cannot establish a future memory bound or grant GO.
    """
    def __init__(self, manager, manifest_path, manifest_sha256, profile, games,
                 controller, artifacts, per_game_headroom_bytes, controller_headroom_bytes):
        self.manager = manager
        self.manifest_path, self.manifest_sha256 = manifest_path, manifest_sha256
        self.profile, self.games, self.controller, self.artifacts = profile, games, controller, artifacts
        self.per_game_headroom_bytes = per_game_headroom_bytes
        self.controller_headroom_bytes = controller_headroom_bytes
        self.child = None

    @classmethod
    def create(cls, *, root, campaign, manifest_path, manifest_sha256,
               per_game_headroom_bytes, controller_headroom_bytes):
        """Prevalidate the manifest, then create each recorded group once.

        An unsuccessful partial setup attempts to remove only the original,
        empty cgroups. Any cleanup errors and original identities are exposed
        on ``CohortSetupFailure``; unknown/replaced groups are never removed.
        """
        manifest_path = run.protected_input(Path(manifest_path))
        manifest = peak_ready_probe.load_controller_manifest(manifest_path, manifest_sha256)
        root = Path(root)
        if (not root.is_absolute() or ".." in root.parts or
                any(path.is_symlink() for path in (root, *root.parents)) or root.resolve(strict=True) != root):
            raise ValueError("original delegated root must be a real absolute non-symlink path")
        per_game = peak_capacity._positive(per_game_headroom_bytes, "per-game headroom")
        reserve = peak_capacity._positive(controller_headroom_bytes, "controller headroom")
        page = os.sysconf("SC_PAGE_SIZE")
        reserve_limit = placement._align_memory_extent(reserve, page)
        for path_key, sha_key in (("runner", "runner_sha256"), ("opening", "opening_sha256")):
            path, digest = manifest.get(path_key), manifest.get(sha_key)
            if (not isinstance(path, str) or not Path(path).is_absolute() or not isinstance(digest, str) or
                    not run.SHA.fullmatch(digest) or peak_ready_probe._file_sha(Path(path)) != digest):
                raise ValueError("pinned runner or opening identity differs")
        original = _require_delegated_root(root)
        before = topology.Topology.snapshot_target(root, device=original.st_dev, inode=original.st_ino)
        if json.loads(json.dumps(before.to_record())) != manifest["topology"]:
            raise ValueError("current target topology differs from the frozen plan")
        if manifest.get("saved_ancestor_cpus") != list(before.allowed_cpus):
            raise ValueError("saved CPU envelope differs from the target topology")
        slots, controller_cpus = run.league_placement(before, manifest["profile"])
        entries = manifest["entries"]
        if ([entry["slot"].to_record() for entry in entries] != [slot.to_record() for slot in slots]):
            raise ValueError("manifest slots differ from the target cohort")
        limits, artifacts, outputs = {}, {}, set()
        cap = 16 << 30 if manifest["profile"] == "test-p16" else 192 << 30
        for entry in entries:
            slot, engines = entry["slot"], entry["engines"]
            if type(engines) is not list or len(engines) != 2 or any(type(engine) is not dict for engine in engines):
                raise ValueError("two engines are required per game")
            if engines[0].get("id") == engines[1].get("id"):
                raise ValueError("distinct engine identities are required per game")
            opening_start, output = entry.get("opening_start"), entry.get("out")
            if type(opening_start) is not int or not 0 < opening_start < (1 << 31) or not isinstance(output, str):
                raise ValueError("invalid opening or diagnostic output")
            output_path = run.external_new(Path(output))
            resolved = run.protected_input(output_path.resolve())
            if (not output_path.is_absolute() or output_path.exists() or output_path.is_symlink() or
                    any((parent / ".git").exists() for parent in (resolved, *resolved.parents)) or
                    any(resolved == prior or resolved.is_relative_to(prior) or prior.is_relative_to(resolved)
                        for prior in outputs)):
                raise ValueError("distinct new external diagnostic output directories are required")
            outputs.add(resolved)
            for engine in engines:
                if type(engine) is not dict or set(engine) != {"id", "path", "whole_sha256", "native_sha256", "tt_bytes"}:
                    raise ValueError("invalid pinned engine identity")
                run.ID(engine["id"])
                path = engine["path"]
                if (not isinstance(path, str) or not Path(path).is_absolute() or
                        any(not isinstance(engine[key], str) or not run.SHA.fullmatch(engine[key])
                            for key in ("whole_sha256", "native_sha256")) or
                        peak_ready_probe._file_sha(Path(path)) != engine["whole_sha256"]):
                    raise ValueError("pinned engine identity differs")
            values = [peak_capacity._positive(engine.get("tt_bytes"), "engine TT") for engine in engines]
            if any(value > cap for value in values):
                raise ValueError("engine TT exceeds the profile limit")
            if manifest["profile"] == "test-p192" and any(value != cap for value in values):
                raise ValueError("P192 requires exactly 192 GiB TT per engine")
            limits[slot.id] = placement._align_memory_extent(sum(values) + per_game, page)
            artifacts[slot.id] = [{key: engine[key] for key in ("id", "whole_sha256", "native_sha256", "tt_bytes")}
                                  for engine in engines]
        # Construction changes only the explicitly supplied delegated root.
        checked = _require_delegated_root(root)
        if (checked.st_dev, checked.st_ino) != (original.st_dev, original.st_ino):
            raise ValueError("delegated root identity changed during preflight")
        try:
            manager = placement.CgroupSlots(root, campaign, root_identity=(original.st_dev, original.st_ino))
        except placement.CgroupSetupFailure as error:
            records = list(error.records)
            if error.unrecorded_path is not None:
                records.append({"path": error.unrecorded_path, "identity_unavailable": True})
            raise CohortSetupFailure(str(error), records=records, cleanup_errors=error.cleanup_errors,
                                     owner=error.owner) from error
        try:
            current_root = manager.root.stat()
            if (manager.root != root or root.is_symlink() or
                    (current_root.st_dev, current_root.st_ino) != (original.st_dev, original.st_ino)):
                raise ValueError("delegated root identity changed during creation")
            parent = manager.parent_record()
            current = topology.Topology.snapshot_target(manager.parent, device=parent["device"], inode=parent["inode"])
            if json.loads(json.dumps(current.to_record())) != manifest["topology"]:
                raise ValueError("created cohort topology differs from the frozen plan")
            controller = manager.create_controller(cpus=controller_cpus, memory_nodes=current.allowed_nodes,
                                                   memory_bytes=reserve_limit)
            peak_capacity._require_empty(Path(controller["path"]))
            games = {}
            for slot in slots:
                group = manager.create(slot, memory_bytes=limits[slot.id])
                peak_capacity._require_empty(Path(group["path"]))
                games[slot.id] = group
            return cls(manager, manifest_path, manifest_sha256, manifest["profile"], games,
                       controller, artifacts, per_game, reserve)
        except BaseException as error:
            records = [{"path": str(path), "device": device, "inode": inode}
                       for path, device, inode in manager.created]
            if isinstance(error, placement.CgroupSetupFailure) and error.unrecorded_path is not None:
                records.append({"path": error.unrecorded_path, "identity_unavailable": True})
            try:
                errors = manager.close()
            except Exception as cleanup:
                errors = [{"error": str(cleanup)}]
            raise CohortSetupFailure(str(error), records=records, cleanup_errors=errors, owner=manager) from error

    def observe(self, *, report_path, append, timeout_seconds=180, max_age_ns=60_000_000_000):
        """Run the existing diagnostic; preserve any returned live child."""
        if self.child is not None:
            raise ValueError("a cohort cannot be observed twice")
        try:
            result = observe_ready(manifest_path=self.manifest_path, manifest_sha256=self.manifest_sha256,
                root=self.manager.root, games=self.games, controller=self.controller, artifacts=self.artifacts,
                report_path=report_path, append=append, per_game_headroom_bytes=self.per_game_headroom_bytes,
                controller_headroom_bytes=self.controller_headroom_bytes, timeout_seconds=timeout_seconds,
                max_age_ns=max_age_ns)
        except peak_supervisor.SupervisorFailure as error:
            self.child = error.process
            raise
        report, self.child = result
        return report, self.child

    def close(self):
        """Remove only recorded empty groups, never signal or reap children."""
        if self.child is not None and self.child.poll() is None:
            return [{"error": "original diagnostic child remains live", "pid": self.child.pid}]
        return self.manager.close()


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
