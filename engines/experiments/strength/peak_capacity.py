"""Live, conservative pre-GO capacity observation; not an admission authority.

The observed values are point-in-time kernel reads, not a memory reservation.
In particular, a namespace-relative cgroup mount may conceal ancestors, and
kernel memory limits do not exclude concurrent writers or other allocations.
Declared overhead is arithmetic input, not a verified workload upper bound.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

try:
    from . import ledger, memory_observation, placement, run, topology
except ImportError:
    import ledger
    import memory_observation
    import placement
    import run
    import topology


def _positive(value, name):
    if type(value) is not int or not 0 < value < (1 << 63):
        raise ValueError(name + " must be a positive bounded byte extent")
    return value


def _source_sha(path):
    path = Path(path).resolve(strict=True)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _owned_path(record, root):
    if not isinstance(record, dict) or not isinstance(record.get("path"), str):
        raise ValueError("original cgroup path identity is required")
    path = Path(record["path"])
    if (not path.is_absolute() or ".." in path.parts or not path.is_relative_to(root) or path == root or
            any(part.is_symlink() for part in (path, *path.parents)) or
            path.resolve(strict=True) != path or path.stat().st_dev != root.stat().st_dev):
        raise ValueError("cgroup path is not an original non-symlink descendant of the root")
    return path


def _require_empty(path):
    # A leaf's memory.max is meaningful for this cohort only if no prior
    # usage or processes remain. It still does not reserve future capacity.
    current = memory_observation._file(path / "memory.current").strip()
    try:
        peak = memory_observation._file(path / "memory.peak").strip()
    except FileNotFoundError as error:
        raise ValueError("kernel memory.peak is required to establish a fresh diagnostic cgroup") from error
    events = memory_observation._file(path / "cgroup.events")
    if current != "0" or peak != "0" or events.splitlines().count("populated 0") != 1:
        raise ValueError("fresh empty cgroup with zero memory current and peak is required")


def _finite_remaining(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("visible ancestor observations are required")
    remaining = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("malformed visible ancestor observation")
        if row.get("root_memory_files_unavailable") is True:
            continue
        limit, current, available = row.get("limit_bytes"), row.get("current_bytes"), row.get("remaining_bytes")
        if (type(current) is not int or current < 0 or
                limit is None and available is not None or
                limit is not None and (type(limit) is not int or type(available) is not int or
                                       limit <= 0 or available <= 0 or limit - current != available)):
            raise ValueError("malformed visible ancestor memory bound")
        if limit is not None:
            remaining.append(available)
    return remaining


def inspect_capacity(*, profile, root, games, groups, controller, frozen_topology,
                     per_game_headroom_bytes, controller_headroom_bytes, controller_path):
    """Read actual kernel capacity and reject inconsistent or insufficient bounds.

    Source hashes identify files read at observation time; they do not prove
    that the loaded code is trusted. This result never grants launch authority.
    """
    if profile not in ("test-p16", "test-p192"):
        raise ValueError("capacity observation accepts only P16 or P192")
    per_game = _positive(per_game_headroom_bytes, "per-game headroom")
    reserve = _positive(controller_headroom_bytes, "controller headroom")
    root = Path(root)
    if not root.is_absolute() or ".." in root.parts or any(part.is_symlink() for part in (root, *root.parents)):
        raise ValueError("original delegated root must be an absolute non-symlink path")
    if root.resolve(strict=True) != root:
        raise ValueError("original delegated root identity changed on resolution")
    checked_controller_path = _owned_path(controller, root)
    if str(checked_controller_path) != controller_path:
        raise ValueError("controller execution path differs from its original cgroup identity")
    common_parent = checked_controller_path.parent
    parent_stat = common_parent.stat()
    current = topology.Topology.snapshot_target(common_parent, device=parent_stat.st_dev, inode=parent_stat.st_ino)
    if json.loads(json.dumps(current.to_record())) != frozen_topology:
        raise ValueError("current target topology differs from frozen topology")
    slots, controller_cpus = run.league_placement(current, profile)
    records = [json.loads(json.dumps(slot.to_record())) for slot in slots]
    if not isinstance(games, list) or len(games) != len(records):
        raise ValueError("complete frozen game cohort is required")
    by_slot = {game.get("slot"): game for game in games if isinstance(game, dict)}
    if len(by_slot) != len(games) or set(by_slot) != {slot.id for slot in slots}:
        raise ValueError("game identities differ from frozen slots")
    if not isinstance(groups, dict) or set(groups) != set(by_slot):
        raise ValueError("original cgroup identities are required for every slot")
    live_controller = placement.verify_cgroup_live(controller)
    if live_controller["cpus"] != sorted(controller_cpus):
        raise ValueError("controller CPU affinity differs from frozen topology")
    if live_controller["memory_max"] < reserve:
        raise ValueError("controller cgroup memory limit is below its declared reserve")
    _require_empty(checked_controller_path)
    all_groups, node_games, game_extents = [], {}, []
    for slot in slots:
        game = by_slot[slot.id]
        _owned_path(groups[slot.id], root)
        live = placement.verify_cgroup_live(groups[slot.id])
        path = Path(live["path"])
        if (not path.is_relative_to(root) or path == root or game.get("path") != str(path) or
                live["cpus"] != sorted(slot.cpus) or live["memory_nodes"] != sorted(slot.memory_nodes) or
                game.get("cpus") != sorted(slot.cpus) or game.get("nodes") != sorted(slot.memory_nodes)):
            raise ValueError("live game cgroup identity or frozen resource masks differ")
        if not set(slot.memory_nodes) <= set(live_controller["memory_nodes"]):
            raise ValueError("controller cgroup excludes a required game node")
        _require_empty(path)
        artifacts = game.get("artifacts")
        if not isinstance(artifacts, list) or len(artifacts) != 2:
            raise ValueError("two engine identities are required per game")
        if any(not isinstance(row, dict) for row in artifacts):
            raise ValueError("engine TT extent differs from the named profile")
        extents = [_positive(row.get("tt_bytes"), "engine TT") for row in artifacts]
        if (profile == "test-p192" and any(value != 192 << 30 for value in extents) or
                profile == "test-p16" and any(value > 16 << 30 for value in extents)):
            raise ValueError("engine TT extent differs from the named profile")
        tt = sum(extents)
        declared = tt + per_game
        if live["memory_max"] < declared:
            raise ValueError("game cgroup memory limit is below TT and declared headroom")
        # memory.max is the kernel's actual upper bound for the whole leaf.
        # It may exceed the caller's estimate because of page alignment or a
        # deliberately larger limit. Capacity must cover that entire bound.
        amount = live["memory_max"]
        game_extents.append({"slot": slot.id, "tt_bytes": tt,
                             "declared_required_bytes": declared,
                             "memory_max_bytes": amount})
        all_groups.append(live)
        if profile == "test-p16":
            if len(slot.memory_nodes) != 1:
                raise ValueError("P16 requires single-node game slots")
            node = slot.memory_nodes[0]
            node_games[node] = node_games.get(node, 0) + amount
    controller_path = Path(live_controller["path"])
    if (not controller_path.is_relative_to(root) or controller_path == root or
            controller_path in {Path(group["path"]) for group in all_groups}):
        raise ValueError("controller cgroup must be a distinct descendant of the original root")
    # All leaves must be siblings so sampling their common parent includes
    # every finite shared ancestor through the visible cgroup mount.
    if any(Path(group["path"]).parent != common_parent for group in all_groups):
        raise ValueError("all diagnostic groups must be siblings under the same cgroup parent")
    observation = memory_observation.observe_capacity(records, common_parent,
                                                       extra_nodes=live_controller["memory_nodes"],
                                                       mask_scope="delegated-only")
    if (observation.get("test_inputs") is not False or
            observation.get("slot_sha256") != ledger.digest(records) or
            observation.get("runtime_admission_complete") is not False or
            observation.get("delegated_identity") != {"device": parent_stat.st_dev, "inode": parent_stat.st_ino} or
            observation.get("mask_scope") != "delegated-only" or
            observation.get("extra_nodes") != live_controller["memory_nodes"] or
            observation.get("delegated_effective_cpus") != list(current.allowed_cpus) or
            observation.get("delegated_effective_nodes") != list(current.allowed_nodes)):
        raise ValueError("capacity observation is not bound to actual slots or the target cgroup identity")
    required = sum(row["memory_max_bytes"] for row in game_extents) + live_controller["memory_max"]
    host_available = _positive(observation["host_memavailable_bytes"], "host available memory")
    target_bounds = _finite_remaining(observation["delegated_cgroup"])
    observer_bounds = _finite_remaining(observation["controller_cgroup"])
    target_available = min([host_available, *target_bounds])
    observer_available = min(observer_bounds) if observer_bounds else None
    # The observer may live in a smaller sibling cgroup. Its private finite
    # limit constrains that process, not the separate game/controller leaves.
    # Shared ancestors already occur in the target chain and remain included.
    if target_available < required:
        raise ValueError("host or target finite ancestor capacity is below declared cohort extent")
    node_available = observation["node_available_bytes"]
    controller_nodes = live_controller["memory_nodes"]
    if any(node not in node_available for node in controller_nodes):
        raise ValueError("controller permitted-node capacity observations are incomplete")
    if sum(node_available[node] for node in controller_nodes) < required:
        raise ValueError("controller permitted-node MemFree capacity is below the cohort extent; reclaimable cache is excluded")
    node_conservative_controller_fits = {}
    if profile == "test-p16":
        for node, amount in node_games.items():
            if node not in node_available or node_available[node] < amount:
                raise ValueError("NUMA node MemFree capacity is below the node-local games; reclaimable cache is excluded")
            # Charging the entire controller reserve to each node is a
            # useful worst case, not a necessary condition when allocations
            # can be split across nodes. The actual distribution is unknown.
            node_conservative_controller_fits[node] = node_available[node] >= amount + live_controller["memory_max"]
    else:
        nodes = slots[0].memory_nodes
        game_required = required - live_controller["memory_max"]
        if any(node not in node_available for node in nodes) or sum(node_available[node] for node in nodes) < game_required:
            raise ValueError("P192 game-node MemFree capacity is below game extent; reclaimable cache is excluded")
    return {"format": "rove4k-diagnostic-capacity-assessment-v1", "profile": profile,
            "boot_id": observation["boot_id"], "capacity": observation,
            "target_common_parent": {"path": str(common_parent), "device": parent_stat.st_dev,
                                     "inode": parent_stat.st_ino, "ownership_provenance_verified": False},
            "groups": all_groups, "controller": live_controller,
            "source_sha256": {**{module.__name__: _source_sha(module.__file__) for module in
                                  (memory_observation, placement, run, topology)},
                              "peak_capacity": _source_sha(__file__),
                              **{name: _source_sha(Path(__file__).with_name(name + ".py"))
                                 for name in ("peak_supervisor", "peak_probe_session", "peak_ready_probe", "overhead")}},
            "arithmetic": {"games": game_extents, "controller_reserve_bytes": reserve,
                           "controller_memory_max_bytes": live_controller["memory_max"],
                           "required_bytes": required, "node_game_bytes": node_games,
                           "target_available_bytes": target_available,
                           "observer_visible_remaining_bytes": observer_available,
                           "observer_future_headroom_verified": False,
                           "node_controller_reserve_worst_case_fits": node_conservative_controller_fits,
                           "node_capacity_basis": "kernel node MemFree; reclaimable cache excluded; no reservation",
                           "controller_node_distribution_verified": False,
                           "controller_node_aggregate_arithmetic_checked": True,
                           "overhead_is_declared_not_verified": True,
                           "p192_node_distribution_verified": False},
            "unresolved": ["hidden_ancestors", "exclusive_cgroup_and_host_writers",
                           "representative_overhead_bound", "trusted_loaded_source",
                           "artifact_resource_provenance", "target_common_parent_ownership"],
            "runtime_admission": False, "launch_permitted": False}
