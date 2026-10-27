#!/usr/bin/env python3
"""Apply an owned slot before exec, so runner/compiler/engines inherit it."""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
from collections import Counter
import hashlib

try:
    from .topology import format_list, parse_list
except ImportError:
    from topology import format_list, parse_list


def allowed_nodes():
    text = Path("/proc/self/status").read_text()
    match = re.search(r"^Mems_allowed_list:\s*(.*)$", text, re.MULTILINE)
    if match is None:
        raise ValueError("effective memory-node mask unavailable")
    return parse_list(match[1])


def memory_policy(policy=None, nodes=()):
    """The task policy, not mbind on an address range discarded by exec."""
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        return {"available": False, "reason": "unsupported syscall ABI"}
    library = ctypes.CDLL(None, use_errno=True)
    library.syscall.restype = ctypes.c_long
    possible_path = Path("/sys/devices/system/node/possible")
    possible = parse_list(possible_path.read_text()) if possible_path.exists() else set()
    maximum = max((*allowed_nodes(), *nodes, *possible), default=0) + 1
    bits = ctypes.sizeof(ctypes.c_ulong) * 8
    maximum = max(bits, ((maximum + bits - 1) // bits) * bits)
    mask = (ctypes.c_ulong * ((maximum + bits - 1) // bits))()
    for node in nodes:
        mask[node // bits] |= 1 << (node % bits)
    if policy not in (None, "inherit"):
        mode = {"default": 0, "interleave": 3}.get(policy)
        if mode is None:
            raise ValueError("unsupported task-memory policy")
        pointer = ctypes.cast(mask, ctypes.c_void_p) if mode else ctypes.c_void_p()
        result = library.syscall(ctypes.c_long(238), ctypes.c_int(mode), pointer,
                                 ctypes.c_ulong(maximum if mode else 0))
        if result != 0:
            return {"available": False, "request_applied": False,
                    "reason": "set_mempolicy rejected", "errno": ctypes.get_errno()}
    for index in range(len(mask)):
        mask[index] = 0
    mode = ctypes.c_int()
    result = library.syscall(ctypes.c_long(239), ctypes.byref(mode), ctypes.cast(mask, ctypes.c_void_p),
                             ctypes.c_ulong(maximum), ctypes.c_void_p(), ctypes.c_ulong(0))
    if result != 0:
        return {"available": False, "request_applied": True if policy not in (None, "inherit") else None,
                "reason": "get_mempolicy rejected", "errno": ctypes.get_errno()}
    observed = [node for node in range(maximum) if mask[node // bits] & (1 << (node % bits))]
    return {"available": True, "request_applied": True if policy not in (None, "inherit") else None,
            "mode": mode.value, "nodes": observed}


def _align_memory_extent(extent, page_bytes):
    """Round up an extent to the caller-observed kernel page size."""
    maximum = (1 << 63) - 1
    if type(page_bytes) is not int or not 0 < page_bytes <= (1 << 62) or page_bytes & (page_bytes - 1):
        raise ValueError("a positive power-of-two kernel page size is required")
    rounded = ((extent + page_bytes - 1) // page_bytes) * page_bytes
    if rounded > maximum:
        raise ValueError("page-aligned memory extent exceeds the supported range")
    return rounded


def slot_memory_budget(tt_bytes, *, overhead_bytes, available_bytes, page_bytes, node_available_bytes=None):
    """Size one game's cgroup from both artifact TT extents and observed bounds.

    The caller must supply actual, already-admitted artifact extents, an
    explicit operational allowance, and a current host availability reading.
    A node availability reading is optional for a multi-node slot; when absent,
    this result does not assert node capacity. This comparison is per game,
    not an admission for several concurrent slots or a reservation of memory.
    """
    maximum = (1 << 63) - 1
    if (not isinstance(tt_bytes, (list, tuple)) or len(tt_bytes) != 2 or
            any(type(value) is not int or not 0 < value <= maximum for value in tt_bytes)):
        raise ValueError("two positive actual artifact TT byte extents are required")
    if type(overhead_bytes) is not int or not 0 < overhead_bytes <= maximum:
        raise ValueError("an explicit positive operational overhead in bytes is required")
    if type(available_bytes) is not int or not 0 < available_bytes <= maximum:
        raise ValueError("a positive observed host available-byte bound is required")
    if node_available_bytes is not None and (
            type(node_available_bytes) is not int or not 0 < node_available_bytes <= maximum):
        raise ValueError("an observed node available-byte bound must be positive")
    raw_memory = sum(tt_bytes) + overhead_bytes
    if raw_memory > maximum:
        raise ValueError("single-game cgroup memory extent exceeds the supported range")
    memory_max = _align_memory_extent(raw_memory, page_bytes)
    if memory_max > available_bytes:
        raise ValueError("single-game memory extent exceeds observed host availability")
    if node_available_bytes is not None and memory_max > node_available_bytes:
        raise ValueError("single-game memory extent exceeds observed node availability")
    return {"tt_bytes": list(tt_bytes), "overhead_bytes": overhead_bytes,
            "unrounded_memory_bytes": raw_memory, "page_bytes": page_bytes,
            "page_rounding_bytes": memory_max - raw_memory,
            "memory_max": memory_max, "supplied_available_bytes": available_bytes,
            "supplied_node_available_bytes": node_available_bytes,
            "node_bound_provided": node_available_bytes is not None,
            "capacity_scope": ("one slot; caller-supplied bounds only; "
                               + ("node bound provided" if node_available_bytes is not None
                                  else "node capacity not checked")
                               + "; not a concurrent admission or reservation")}


def league_memory_admission(artifacts, slots, *, profile, host_available_bytes, node_available_bytes,
                            per_game_overhead_bytes, overhead_evidence_sha256, controller_reserve_bytes,
                            page_bytes):
    """Compare one cohort's conservative simultaneous memory demand to supplied bounds.

    Caller supplies verified artifact identities, the exact candidate slots,
    current effective host/node bounds and a separately authenticated overhead
    receipt. The digest is a binding label, not receipt authentication. This
    pure arithmetic check neither reserves resources nor verifies provenance,
    freshness, runtime TT residency or actual per-node page distribution.
    """
    maximum = (1 << 63) - 1

    def positive(value, message):
        if type(value) is not int or not 0 < value <= maximum:
            raise ValueError(message)
        return value

    if profile not in ("test-p16", "test-p192"):
        raise ValueError("named P16 or P192 profile required")
    if not isinstance(artifacts, (tuple, list)) or not 2 <= len(artifacts) <= 256:
        raise ValueError("at least two bounded artifact identities are required")
    if not isinstance(overhead_evidence_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", overhead_evidence_sha256):
        raise ValueError("a bound overhead evidence SHA-256 is required")
    overhead = positive(per_game_overhead_bytes, "a positive per-game operational overhead is required")
    reserve = positive(controller_reserve_bytes, "a positive controller reserve is required")
    available = positive(host_available_bytes, "a positive supplied host available-byte bound is required")
    players = []
    seen_players = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("artifact identity record required")
        name, digest = artifact.get("id"), artifact.get("sha256")
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", name)
                or name in seen_players or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
            raise ValueError("distinct named artifact identities with SHA-256 are required")
        tt = positive(artifact.get("tt_bytes"), "actual artifact TT extent must be positive")
        seen_players.add(name)
        players.append({"id": name, "sha256": digest, "tt_bytes": tt})
    players.sort(key=lambda row: (-row["tt_bytes"], row["id"]))
    worst = players[:2]
    raw_per_slot = sum(row["tt_bytes"] for row in worst) + overhead
    if raw_per_slot > maximum:
        raise ValueError("single-slot memory extent exceeds the supported range")
    per_slot = _align_memory_extent(raw_per_slot, page_bytes)
    expected_count = 11 if profile == "test-p16" else 1
    if not isinstance(slots, (tuple, list)) or len(slots) != expected_count:
        raise ValueError("P16 requires eleven slots and P192 requires one slot")
    if not isinstance(node_available_bytes, dict) or not node_available_bytes:
        raise ValueError("per-node supplied available-byte bounds are required")
    node_bounds = {}
    for node, value in node_available_bytes.items():
        if type(node) is not int or node < 0:
            raise ValueError("a nonnegative numeric NUMA node id is required")
        node_bounds[node] = positive(value, "a positive node available-byte bound is required")
    records, seen_slots, p16_nodes = [], set(), Counter()
    for slot in slots:
        if not isinstance(slot, dict):
            raise ValueError("actual slot identity record required")
        name, nodes = slot.get("id"), slot.get("memory_nodes")
        if (not isinstance(name, str) or not re.fullmatch(r"slot-\d{3}", name) or name in seen_slots
                or not isinstance(nodes, (tuple, list)) or not nodes
                or any(type(node) is not int or node < 0 for node in nodes)
                or len(nodes) != len(set(nodes))):
            raise ValueError("distinct slot identity and NUMA node list required")
        if profile == "test-p16" and len(nodes) != 1:
            raise ValueError("P16 slots must each use exactly one NUMA node")
        if any(node not in node_bounds for node in nodes):
            raise ValueError("supplied node bound is missing for an actual slot")
        seen_slots.add(name)
        if profile == "test-p16":
            p16_nodes[nodes[0]] += per_slot
        records.append({"id": name, "memory_nodes": sorted(nodes), "memory_max": per_slot})
    required = per_slot * len(records) + reserve
    if required > maximum:
        raise ValueError("concurrent memory extent exceeds the supported range")
    if required > available:
        raise ValueError("concurrent memory extent exceeds supplied host availability")
    if profile == "test-p16":
        for node, amount in p16_nodes.items():
            if amount > node_bounds[node]:
                raise ValueError("P16 slot aggregate exceeds supplied NUMA node availability")
        node_check = {"kind": "per-node-game-sums", "required_bytes": dict(sorted(p16_nodes.items())),
                      "controller_distribution_verified": False}
    else:
        allowed_nodes = records[0]["memory_nodes"]
        aggregate = sum(node_bounds[node] for node in allowed_nodes)
        if aggregate > maximum:
            raise ValueError("supplied node aggregate exceeds the supported range")
        if required > aggregate:
            raise ValueError("P192 game plus controller exceeds supplied aggregate node availability")
        node_check = {"kind": "aggregate-only", "allowed_nodes": allowed_nodes,
                      "supplied_aggregate_bytes": aggregate,
                      "per_node_distribution_verified": False}
    return {"profile": profile, "worst_two_artifacts": worst, "per_game_overhead_bytes": overhead,
            "overhead_evidence_sha256": overhead_evidence_sha256,
            "unrounded_per_slot_bytes": raw_per_slot, "page_bytes": page_bytes,
            "per_slot_page_rounding_bytes": per_slot - raw_per_slot, "slots": records,
            "controller_reserve_bytes": reserve, "required_bytes": required,
            "supplied_host_available_bytes": available, "supplied_node_available_bytes": dict(sorted(node_bounds.items())),
            "node_check": node_check, "runtime_admission_complete": False,
            "capacity_scope": "caller-supplied bounds and digest only; no provenance, freshness, reservation or TT page claim"}


class CgroupSlots:
    """Create only beneath an explicitly delegated controller-owned root."""
    def __init__(self, root, campaign):
        self.root = Path(root).resolve(strict=True)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", campaign):
            raise ValueError("invalid campaign namespace")
        if self.root == Path("/sys/fs/cgroup"):
            raise ValueError("delegate a dedicated root, not the global cgroup root")
        controllers = set((self.root / "cgroup.controllers").read_text().split())
        if not {"cpuset", "memory"} <= controllers:
            raise ValueError("dedicated cgroup root must delegate cpuset and memory")
        self.parent = self.root / campaign
        if self.parent.exists():
            raise ValueError("existing cgroup namespace needs its original ownership record")
        # The caller has explicitly delegated this root. No global ancestor is edited.
        (self.root / "cgroup.subtree_control").write_text("+cpuset +memory")
        self.parent.mkdir()
        stat = self.parent.stat()
        self.created = [(self.parent, stat.st_dev, stat.st_ino)]
        try:
            (self.parent / "cgroup.subtree_control").write_text("+cpuset +memory")
        except BaseException:
            self.close()
            raise

    def create(self, slot, memory_bytes=4 << 30):
        if not re.fullmatch(r"slot-\d{3}", slot.id) or type(memory_bytes) is not int or memory_bytes <= 0:
            raise ValueError("invalid owned cgroup slot")
        path = self.parent / slot.id
        path.mkdir()
        stat = path.stat()
        self.created.append((path, stat.st_dev, stat.st_ino))
        (path / "cpuset.cpus").write_text(format_list(slot.cpus))
        (path / "cpuset.mems").write_text(format_list(slot.memory_nodes))
        (path / "memory.max").write_text(str(memory_bytes))
        cpus = parse_list((path / "cpuset.cpus.effective").read_text())
        mems = parse_list((path / "cpuset.mems.effective").read_text())
        if cpus != set(slot.cpus) or mems != set(slot.memory_nodes):
            raise ValueError("kernel cgroup effective masks differ from the slot")
        # The cgroup file is kernel-owned, so do not report the value we sent
        # as an observed limit. Reject max, malformed or changed readback.
        memory_text = (path / "memory.max").read_text().strip()
        if not re.fullmatch(r"[0-9]+", memory_text) or int(memory_text) != memory_bytes:
            raise ValueError("kernel cgroup memory.max readback differs from the requested limit")
        stat = path.stat()
        return {"path": str(path), "device": stat.st_dev, "inode": stat.st_ino,
                "cpus": sorted(cpus), "memory_nodes": sorted(mems), "memory_max": int(memory_text)}

    def parent_record(self):
        path, device, inode = self.created[0]
        return {"path": str(path), "device": device, "inode": inode}

    def close(self):
        records = [{"path": str(path), "device": device, "inode": inode}
                   for path, device, inode in self.created]
        return [row for row in cleanup_owned_groups(records, root=self.root) if "error" in row]


def cleanup_owned_groups(records, *, root):
    """Remove only recorded, empty cgroups beneath the delegated root.

    Records must come from the campaign's verified journal, including the
    original parent identity. An unknown or replaced directory is preserved.
    Missing recorded groups are an idempotent cleanup outcome.
    """
    root = Path(root)
    if not root.is_absolute() or root == Path("/sys/fs/cgroup") or root.is_symlink():
        raise ValueError("cleanup requires the original dedicated cgroup root")
    root = root.resolve()
    owned = []
    seen = set()
    for record in records:
        path = Path(record["path"])
        if (not path.is_absolute() or path in seen or
                type(record.get("device")) is not int or type(record.get("inode")) is not int or
                record["device"] < 0 or record["inode"] <= 0):
            raise ValueError("invalid or duplicate original cgroup identity")
        try:
            relative = path.relative_to(root)
        except ValueError as error:
            raise ValueError("recorded cgroup escapes the dedicated root") from error
        if (len(relative.parts) not in (1, 2) or any(part in (".", "..") for part in relative.parts) or
                not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", relative.parts[0]) or
                (len(relative.parts) == 2 and not re.fullmatch(r"slot-\d{3}", relative.parts[1]))):
            raise ValueError("recorded cgroup is outside a campaign/slot namespace")
        seen.add(path)
        owned.append((path, record["device"], record["inode"]))
    outcomes = []
    for path, device, inode in sorted(owned, key=lambda row: (-len(row[0].parts), str(row[0]))):
        outcome = {"path": str(path), "device": device, "inode": inode}
        try:
            ancestor = path
            while ancestor != root:
                if ancestor.is_symlink():
                    raise ValueError("owned cgroup path now follows a link")
                ancestor = ancestor.parent
            try:
                stat = path.stat()
            except FileNotFoundError:
                outcome["already_absent"] = True
            else:
                if (stat.st_dev, stat.st_ino) != (device, inode):
                    raise ValueError("owned cgroup directory identity changed")
                events = dict(line.split() for line in (path / "cgroup.events").read_text().splitlines())
                if events.get("populated") != "0":
                    raise ValueError("owned cgroup still contains tasks")
                path.rmdir()  # cgroupfs rejects any group populated after the check.
                outcome["removed"] = True
        except (OSError, ValueError) as error:
            outcome["error"] = str(error)
        outcomes.append(outcome)
    return outcomes


def verify_cgroup_live(cgroup):
    """Re-read one owned cgroup's recorded limits at this observation instant.

    The caller must authenticate the original receipt. This does not reserve
    resources, check ancestor memory limits or prove live TT page placement;
    another actor could change the group after the observation.
    """
    if not isinstance(cgroup, dict) or not isinstance(cgroup.get("path"), str):
        raise ValueError("an original cgroup identity receipt is required")
    path = Path(cgroup["path"])
    device, inode, memory_max = cgroup.get("device"), cgroup.get("inode"), cgroup.get("memory_max")
    if (not path.is_absolute() or type(device) is not int or device < 0 or
            type(inode) is not int or inode <= 0 or type(memory_max) is not int or
            not 0 < memory_max < (1 << 63)):
        raise ValueError("invalid original cgroup identity or memory.max receipt")

    def expected_set(key):
        values = cgroup.get(key)
        if (not isinstance(values, (list, tuple)) or not values or
                any(type(value) is not int or value < 0 for value in values) or
                len(set(values)) != len(values)):
            raise ValueError("invalid original cgroup " + key + " receipt")
        return set(values)

    expected_cpus, expected_nodes = expected_set("cpus"), expected_set("memory_nodes")
    before = path.stat()
    if path.is_symlink() or (before.st_dev, before.st_ino) != (device, inode):
        raise ValueError("owned cgroup identity changed")
    actual_cpus = parse_list((path / "cpuset.cpus.effective").read_text())
    actual_nodes = parse_list((path / "cpuset.mems.effective").read_text())
    if actual_cpus != expected_cpus or actual_nodes != expected_nodes:
        raise ValueError("owned cgroup effective masks differ from their original receipt")
    memory_text = (path / "memory.max").read_text().strip()
    if not re.fullmatch(r"[0-9]+", memory_text) or int(memory_text) != memory_max:
        raise ValueError("owned cgroup memory.max differs from its original receipt")
    after = path.stat()
    if path.is_symlink() or (after.st_dev, after.st_ino) != (device, inode):
        raise ValueError("owned cgroup identity changed during observation")
    return {"path": str(path), "device": device, "inode": inode, "cpus": sorted(actual_cpus),
            "memory_nodes": sorted(actual_nodes), "memory_max": int(memory_text),
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "owned cgroup snapshot; not ancestor capacity, TT placement, reservation or future stability"}


def apply_slot(slot, *, cgroup=None, saved_ancestor_cpus=None):
    if not hasattr(os, "sched_setaffinity"):
        raise RuntimeError("slot execution requires Linux affinity")
    original_cpus = set(os.sched_getaffinity(0))
    original_nodes = allowed_nodes()
    cpus, nodes = set(slot["cpus"]), set(slot["memory_nodes"])
    envelope = original_cpus
    if saved_ancestor_cpus is not None:
        if not cgroup or not saved_ancestor_cpus:
            raise ValueError("restoring a saved ancestor mask requires its owned cgroup")
        envelope = set(saved_ancestor_cpus)
        if any(type(cpu) is not int or cpu < 0 for cpu in envelope):
            raise ValueError("invalid original host CPU envelope")
        online = parse_list(Path("/sys/devices/system/cpu/online").read_text())
        if not envelope <= online:
            raise ValueError("saved ancestor mask is outside current online CPUs")
    if not cpus or not cpus <= envelope or not nodes or not nodes <= original_nodes:
        raise ValueError("slot would widen inherited CPU or allowed-node masks")
    inherited_policy = memory_policy()
    if cgroup:
        observed_cgroup = verify_cgroup_live(cgroup)
        if set(observed_cgroup["cpus"]) != cpus or set(observed_cgroup["memory_nodes"]) != nodes:
            raise ValueError("owned cgroup effective masks changed")
        path = Path(observed_cgroup["path"])
        (path / "cgroup.procs").write_text(str(os.getpid()))
    os.sched_setaffinity(0, cpus)
    effective_cpus = set(os.sched_getaffinity(0))
    if effective_cpus != cpus:
        raise ValueError("effective CPU slot differs after placement")
    requested_policy = slot.get("policy", "inherit")
    observed_policy = memory_policy(requested_policy, sorted(nodes))
    fallback = None
    if observed_policy.get("request_applied") is False and requested_policy != "inherit":
        fallback = "inherited policy retained; " + observed_policy["reason"]
        observed_policy = memory_policy()
    effective_nodes = allowed_nodes()
    if cgroup and effective_nodes != nodes:
        raise ValueError("effective cgroup memory nodes differ after placement")
    return {"pid": os.getpid(), "time_utc": datetime.now(timezone.utc).isoformat(),
            "original_cpus": sorted(original_cpus), "saved_ancestor_cpus": sorted(envelope),
            "original_allowed_nodes": sorted(original_nodes),
            "requested_cpus": sorted(cpus), "effective_cpus": sorted(effective_cpus),
            "requested_nodes": sorted(nodes), "effective_allowed_nodes": sorted(effective_nodes),
            "inherited_policy": inherited_policy, "requested_policy": requested_policy,
            "observed_policy": observed_policy, "fallback": fallback,
            "cgroup": cgroup, "stage": "pre-exec runner; final engine observation is separate"}


def _process_identity(pid):
    text = Path(f"/proc/{pid}/stat").read_text()
    fields = text[text.rfind(")") + 2:].split()
    return {"pid": pid, "pgid": int(fields[2]), "session": int(fields[3]), "start_ticks": int(fields[19]),
            "alive": fields[0] not in ("Z", "X", "x")}


def observe_game_engines(runner_pid, expected_native_hashes, cpus, *, expected_start_ticks=None):
    """Bind both final engine images and their thread masks before wave GO.

    Only members of this still-live runner's original session are inspected.
    This does not equate balanced pages with remote-access or NUMA performance.
    """
    owner = _process_identity(runner_pid)
    if not owner["alive"] or owner["pgid"] != runner_pid or owner["session"] != runner_pid:
        raise ValueError("runner does not own its dedicated process session")
    if expected_start_ticks is not None and owner["start_ticks"] != expected_start_ticks:
        raise ValueError("runner PID was reused")
    if len(expected_native_hashes) != 2 or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
                                                for value in expected_native_hashes):
        raise ValueError("two frozen final native image hashes are required")
    expected = Counter(expected_native_hashes)
    allowed = set(cpus)
    matches = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        pid = int(path.name)
        if pid == runner_pid:
            continue
        try:
            identity = _process_identity(pid)
            if not identity["alive"] or identity["pgid"] != runner_pid or identity["session"] != runner_pid:
                continue
            image = hashlib.sha256()
            with (path / "exe").open("rb") as source:
                for block in iter(lambda: source.read(1 << 20), b""):
                    image.update(block)
            value = image.hexdigest()
            if value not in expected:
                continue
            threads = []
            for task in (path / "task").iterdir():
                mask = set(os.sched_getaffinity(int(task.name)))
                if not mask or not mask <= allowed:
                    raise ValueError("actual engine thread escaped its physical slot")
                threads.append({"tid": int(task.name), "cpus": sorted(mask)})
            if not threads:
                raise ValueError("actual engine has no live observable threads")
            pages = Counter()
            numa_reason = None
            try:
                numa = (path / "numa_maps").read_text()
                for node, count in re.findall(r"\bN(\d+)=(\d+)", numa):
                    pages[int(node)] += int(count)
            except PermissionError as error:
                numa_reason = str(error)
            if _process_identity(pid) != identity:
                continue
            matches.append({**identity, "native_sha256": value, "threads": sorted(threads, key=lambda row: row["tid"]),
                            "numa_pages": dict(sorted(pages.items())) if numa_reason is None else None,
                            "numa_unavailable_reason": numa_reason,
                            "numa_scope": "all observed mappings; not a TT-only or remote-access measurement"})
        except (FileNotFoundError, ProcessLookupError):
            continue
    if Counter(row["native_sha256"] for row in matches) != expected:
        raise ValueError("READY did not expose exactly the two qualified native images")
    if _process_identity(runner_pid) != owner:
        raise ValueError("runner identity changed during the observation")
    return {"runner": owner, "engines": matches, "observed_cpus": sorted(allowed),
            "time_utc": datetime.now(timezone.utc).isoformat(), "stage": "actual final images before scored GO"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slot", required=True, type=Path)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or not args.slot.is_absolute() or not args.record.is_absolute() or args.record.exists():
        parser.error("actual command, absolute slot input and new absolute observation required")
    value = json.loads(args.slot.read_text())
    observation = apply_slot(value["slot"], cgroup=value.get("cgroup"),
                             saved_ancestor_cpus=value.get("saved_ancestor_cpus"))
    with args.record.open("x", encoding="utf-8") as output:
        json.dump(observation, output, sort_keys=True)
        output.flush()
        os.fsync(output.fileno())
    os.execvpe(command[0], command, os.environ.copy())


if __name__ == "__main__":
    main()
