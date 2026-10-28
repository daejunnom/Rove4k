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


class CgroupSetupFailure(RuntimeError):
    """Keep original identities if delegated subtree setup needs reconciliation."""
    def __init__(self, message, *, records, cleanup_errors, unrecorded_path=None, owner=None):
        super().__init__(message)
        self.records, self.cleanup_errors, self.unrecorded_path = records, cleanup_errors, unrecorded_path
        self.owner = owner


def _cgroup_at(directory_fd, name, *, value=None):
    """Read/write a cgroup attribute relative to an already-open directory."""
    if not re.fullmatch(r"[a-z]+(?:\.[a-z_]+)+", name):
        raise ValueError("invalid cgroup attribute name")
    flags = (os.O_RDONLY if value is None else os.O_WRONLY) | os.O_NOFOLLOW
    fd = os.open(name, flags, dir_fd=directory_fd)
    try:
        if value is None:
            data = os.read(fd, 65537)
            if len(data) > 65536:
                raise ValueError("cgroup attribute exceeds bound")
            return data.decode("ascii")
        raw = value.encode("ascii")
        if os.write(fd, raw) != len(raw):
            raise OSError("short cgroup attribute write")
    finally:
        os.close(fd)


class CgroupSlots:
    """Create only beneath an explicitly delegated controller-owned root."""
    def __init__(self, root, campaign, *, root_identity=None):
        self.root = Path(root).resolve(strict=True)
        self._root_fd = self._parent_fd = None
        self._removed = set()
        self._closed = False
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", campaign):
            raise ValueError("invalid campaign namespace")
        if self.root == Path("/sys/fs/cgroup"):
            raise ValueError("delegate a dedicated root, not the global cgroup root")
        if root_identity is not None:
            self._init_anchored(campaign, root_identity)
            return
        controllers = set((self.root / "cgroup.controllers").read_text().split())
        if not {"cpuset", "memory"} <= controllers:
            raise ValueError("dedicated cgroup root must delegate cpuset and memory")
        self.parent = self.root / campaign
        if self.parent.exists():
            raise ValueError("existing cgroup namespace needs its original ownership record")
        # The caller has explicitly delegated this root. No global ancestor is edited.
        (self.root / "cgroup.subtree_control").write_text("+cpuset +memory")
        self.parent.mkdir()
        try:
            stat = self.parent.stat()
        except BaseException as error:
            # Without the original identity we must not delete a path that an
            # external actor might already have replaced.
            raise CgroupSetupFailure(str(error), records=[], cleanup_errors=[],
                                     unrecorded_path=str(self.parent), owner=self) from error
        self.created = [(self.parent, stat.st_dev, stat.st_ino)]
        try:
            (self.parent / "cgroup.subtree_control").write_text("+cpuset +memory")
        except BaseException as error:
            records = [{"path": str(path), "device": device, "inode": inode}
                       for path, device, inode in self.created]
            try:
                errors = self.close()
            except Exception as cleanup:
                errors = [{"error": str(cleanup)}]
            raise CgroupSetupFailure(str(error), records=records, cleanup_errors=errors, owner=self) from error

    def _init_anchored(self, campaign, identity):
        if (os.name != "posix" or not hasattr(os, "O_NOFOLLOW") or
                not isinstance(identity, tuple) or len(identity) != 2 or
                any(type(value) is not int or value < 0 for value in identity)):
            raise ValueError("original Linux cgroup root identity is required")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        self.parent, self.created = self.root / campaign, []
        self._root_fd = os.open(self.root, flags)
        made = False
        try:
            original = os.fstat(self._root_fd)
            if (original.st_dev, original.st_ino) != identity:
                raise ValueError("delegated root identity changed before setup")
            if not {"cpuset", "memory"} <= set(_cgroup_at(self._root_fd, "cgroup.controllers").split()):
                raise ValueError("dedicated cgroup root must delegate cpuset and memory")
            _cgroup_at(self._root_fd, "cgroup.subtree_control", value="+cpuset +memory")
            os.mkdir(campaign, dir_fd=self._root_fd)
            made = True
            self._parent_fd = os.open(campaign, flags, dir_fd=self._root_fd)
            parent = os.fstat(self._parent_fd)
            if parent.st_dev != original.st_dev:
                raise ValueError("new cgroup parent belongs to a different filesystem")
            self.created.append((self.parent, parent.st_dev, parent.st_ino))
            _cgroup_at(self._parent_fd, "cgroup.subtree_control", value="+cpuset +memory")
            current = os.stat(campaign, dir_fd=self._root_fd, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != (parent.st_dev, parent.st_ino):
                raise ValueError("original cgroup parent identity changed during setup")
            self._check_anchored_parent()
        except BaseException as error:
            records = [{"path": str(path), "device": device, "inode": inode}
                       for path, device, inode in self.created]
            try:
                errors = self.close() if records else []
            except Exception as cleanup:
                errors = [{"error": str(cleanup)}]
            if not records:
                self._close_fds()
            raise CgroupSetupFailure(str(error), records=records, cleanup_errors=errors,
                unrecorded_path=str(self.parent) if made and not records else None, owner=self) from error

    def _close_fds(self):
        for field in ("_parent_fd", "_root_fd"):
            fd = getattr(self, field, None)
            if fd is not None:
                os.close(fd)
                setattr(self, field, None)

    def _check_anchored_parent(self):
        """Reject a detached or replaced path while keeping open handles."""
        root_fd, parent_fd = os.fstat(self._root_fd), os.fstat(self._parent_fd)
        if any(path.is_symlink() for path in (self.root, *self.root.parents)):
            raise ValueError("delegated root path became a symlink")
        root_path, parent_path = self.root.stat(), self.parent.stat()
        parent_at = os.stat(self.parent.name, dir_fd=self._root_fd, follow_symlinks=False)
        _, device, inode = self.created[0]
        if (self.parent.is_symlink() or
                (root_path.st_dev, root_path.st_ino) != (root_fd.st_dev, root_fd.st_ino) or
                (parent_fd.st_dev, parent_fd.st_ino) != (device, inode) or
                (parent_path.st_dev, parent_path.st_ino) != (device, inode) or
                (parent_at.st_dev, parent_at.st_ino) != (device, inode)):
            raise ValueError("original cgroup parent or root path changed")

    def create(self, slot, memory_bytes=4 << 30):
        if not re.fullmatch(r"slot-\d{3}", slot.id) or type(memory_bytes) is not int or memory_bytes <= 0:
            raise ValueError("invalid owned cgroup slot")
        return self._create_leaf(slot.id, slot.cpus, slot.memory_nodes, memory_bytes)

    def create_controller(self, *, cpus, memory_nodes, memory_bytes):
        """Create the diagnostic controller as a sibling of the game slots.

        This reserves no physical memory and does not establish exclusive
        ownership against outside writers. The original identity remains in
        ``created`` even if a kernel write or readback fails.
        """
        if type(memory_bytes) is not int or not 0 < memory_bytes < (1 << 63):
            raise ValueError("invalid controller memory limit")
        return self._create_leaf("controller", cpus, memory_nodes, memory_bytes)

    def _create_leaf(self, name, cpus, memory_nodes, memory_bytes):
        for values in (cpus, memory_nodes):
            if (not isinstance(values, (list, tuple, set, frozenset)) or not values or
                    any(type(value) is not int or value < 0 for value in values) or
                    len(set(values)) != len(values)):
                raise ValueError("owned cgroup needs distinct non-negative CPU and node masks")
        if getattr(self, "_parent_fd", None) is not None:
            return self._create_anchored_leaf(name, cpus, memory_nodes, memory_bytes)
        parent = self.parent.stat()
        if self.parent.is_symlink():
            raise ValueError("original cgroup parent became a symlink")
        if self.created and self.created[0][0] == self.parent:
            _, device, inode = self.created[0]
            if (parent.st_dev, parent.st_ino) != (device, inode):
                raise ValueError("original cgroup parent identity changed")
        path = self.parent / name
        path.mkdir()
        stat = path.stat()
        self.created.append((path, stat.st_dev, stat.st_ino))
        (path / "cpuset.cpus").write_text(format_list(cpus))
        (path / "cpuset.mems").write_text(format_list(memory_nodes))
        (path / "memory.max").write_text(str(memory_bytes))
        effective_cpus = parse_list((path / "cpuset.cpus.effective").read_text())
        mems = parse_list((path / "cpuset.mems.effective").read_text())
        if effective_cpus != set(cpus) or mems != set(memory_nodes):
            raise ValueError("kernel cgroup effective masks differ from the slot")
        # The cgroup file is kernel-owned, so do not report the value we sent
        # as an observed limit. Reject max, malformed or changed readback.
        memory_text = (path / "memory.max").read_text().strip()
        if not re.fullmatch(r"[0-9]+", memory_text) or int(memory_text) != memory_bytes:
            raise ValueError("kernel cgroup memory.max readback differs from the requested limit")
        current, current_parent = path.stat(), self.parent.stat()
        if (path.is_symlink() or self.parent.is_symlink() or
                (current.st_dev, current.st_ino) != (stat.st_dev, stat.st_ino) or
                (current_parent.st_dev, current_parent.st_ino) != (parent.st_dev, parent.st_ino)):
            raise ValueError("original cgroup identity changed during setup")
        return {"path": str(path), "device": stat.st_dev, "inode": stat.st_ino,
                "cpus": sorted(effective_cpus), "memory_nodes": sorted(mems), "memory_max": int(memory_text)}

    def _create_anchored_leaf(self, name, cpus, memory_nodes, memory_bytes):
        self._check_anchored_parent()
        parent = os.fstat(self._parent_fd)
        _, device, inode = self.created[0]
        if (parent.st_dev, parent.st_ino) != (device, inode):
            raise ValueError("original cgroup parent identity changed")
        os.mkdir(name, dir_fd=self._parent_fd)
        path = self.parent / name
        try:
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self._parent_fd)
        except BaseException as error:
            raise CgroupSetupFailure(str(error), records=[{"path": str(p), "device": d, "inode": i}
                for p, d, i in self.created], cleanup_errors=[], unrecorded_path=str(path), owner=self) from error
        try:
            original = os.fstat(fd)
            if original.st_dev != parent.st_dev:
                raise CgroupSetupFailure("new cgroup leaf belongs to a different filesystem",
                    records=[{"path": str(p), "device": d, "inode": i} for p, d, i in self.created],
                    cleanup_errors=[], unrecorded_path=str(path), owner=self)
            self.created.append((path, original.st_dev, original.st_ino))
            _cgroup_at(fd, "cpuset.cpus", value=format_list(cpus))
            _cgroup_at(fd, "cpuset.mems", value=format_list(memory_nodes))
            _cgroup_at(fd, "memory.max", value=str(memory_bytes))
            effective_cpus = parse_list(_cgroup_at(fd, "cpuset.cpus.effective"))
            effective_nodes = parse_list(_cgroup_at(fd, "cpuset.mems.effective"))
            actual_memory = _cgroup_at(fd, "memory.max").strip()
            current = os.stat(name, dir_fd=self._parent_fd, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino):
                raise ValueError("original cgroup leaf identity changed during setup")
            self._check_anchored_parent()
            if effective_cpus != set(cpus) or effective_nodes != set(memory_nodes):
                raise ValueError("kernel cgroup effective masks differ from the slot")
            if not re.fullmatch(r"[0-9]+", actual_memory) or int(actual_memory) != memory_bytes:
                raise ValueError("kernel cgroup memory.max readback differs from the requested limit")
            return {"path": str(path), "device": original.st_dev, "inode": original.st_ino,
                    "cpus": sorted(effective_cpus), "memory_nodes": sorted(effective_nodes),
                    "memory_max": int(actual_memory)}
        finally:
            os.close(fd)

    def parent_record(self):
        path, device, inode = self.created[0]
        return {"path": str(path), "device": device, "inode": inode}

    def close(self):
        if getattr(self, "_closed", False):
            return []
        records = [{"path": str(path), "device": device, "inode": inode}
                   for path, device, inode in self.created]
        outcomes = cleanup_owned_groups(records, root=self.root)
        expected = {(row["path"], row["device"], row["inode"]) for row in records}
        actual = [(row.get("path"), row.get("device"), row.get("inode")) for row in outcomes]
        if len(actual) != len(expected) or set(actual) != expected:
            return [{"error": "cleanup did not reconcile every original identity"}]
        errors = []
        removed = getattr(self, "_removed", set())
        for row in outcomes:
            key = (row["path"], row["device"], row["inode"])
            if row.get("removed"):
                removed.add(key)
            elif row.get("already_absent") and getattr(self, "_parent_fd", None) is not None and key not in removed:
                errors.append({**row, "error": "original group disappeared without verified removal"})
            elif "error" in row:
                errors.append(row)
        self._removed = removed
        if not errors:
            self._close_fds()
            self._closed = True
        return errors


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
                (len(relative.parts) == 2 and relative.parts[1] != "controller" and
                 not re.fullmatch(r"slot-\d{3}", relative.parts[1]))):
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


def _join_with_saved_node_envelope(path, observed, nodes, node_envelope):
    """Join the original leaf only after its parent validates a saved envelope.

    The caller must authenticate the original cgroup receipt and the saved
    ancestor snapshot. Open directory handles prevent following a replacement
    symlink while checking and writing; this does not exclude external writers.
    """
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("owned cgroup path traverses a symlink")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent_fd = os.open(path.parent, flags)
    child_fd = None
    try:
        parent_before = os.fstat(parent_fd)
        child_fd = os.open(path.name, flags, dir_fd=parent_fd)
        child_before = os.fstat(child_fd)
        if (child_before.st_dev, child_before.st_ino) != (observed["device"], observed["inode"]):
            raise ValueError("owned cgroup identity changed before joining")
        online = parse_list(Path("/sys/devices/system/node/online").read_text())
        parent_nodes = parse_list(_cgroup_at(parent_fd, "cpuset.mems.effective"))
        if not nodes <= node_envelope or not node_envelope <= online or not node_envelope <= parent_nodes:
            raise ValueError("saved node envelope differs from online or parent cgroup nodes")
        if (parse_list(_cgroup_at(child_fd, "cpuset.cpus.effective")) != set(observed["cpus"]) or
                parse_list(_cgroup_at(child_fd, "cpuset.mems.effective")) != nodes or
                _cgroup_at(child_fd, "memory.max").strip() != str(observed["memory_max"])):
            raise ValueError("owned cgroup limits changed before joining")
        current_parent = path.parent.stat()
        current_child = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        if ((current_parent.st_dev, current_parent.st_ino) != (parent_before.st_dev, parent_before.st_ino) or
                (current_child.st_dev, current_child.st_ino) != (child_before.st_dev, child_before.st_ino)):
            raise ValueError("owned cgroup path changed before joining")
        _cgroup_at(child_fd, "cgroup.procs", value=str(os.getpid()))
    finally:
        if child_fd is not None:
            os.close(child_fd)
        os.close(parent_fd)


def apply_slot(slot, *, cgroup=None, saved_ancestor_cpus=None, saved_ancestor_nodes=None):
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
    if not cpus or not cpus <= envelope or not nodes:
        raise ValueError("slot would widen inherited CPU or allowed-node masks")
    inherited_policy = memory_policy()
    if cgroup:
        observed_cgroup = verify_cgroup_live(cgroup)
        if set(observed_cgroup["cpus"]) != cpus or set(observed_cgroup["memory_nodes"]) != nodes:
            raise ValueError("owned cgroup effective masks changed")
        path = Path(observed_cgroup["path"])
        if saved_ancestor_nodes is not None:
            if (saved_ancestor_cpus is None or not isinstance(saved_ancestor_nodes, (list, tuple)) or
                    not saved_ancestor_nodes or any(type(node) is not int or node < 0 for node in saved_ancestor_nodes) or
                    len(set(saved_ancestor_nodes)) != len(saved_ancestor_nodes)):
                raise ValueError("restoring a saved node mask requires its owned cgroup and CPU envelope")
            node_envelope = set(saved_ancestor_nodes)
            _join_with_saved_node_envelope(path, observed_cgroup, nodes, node_envelope)
        elif not nodes <= original_nodes:
            raise ValueError("slot would widen inherited CPU or allowed-node masks")
        else:
            (path / "cgroup.procs").write_text(str(os.getpid()))
    elif saved_ancestor_nodes is not None or not nodes <= original_nodes:
        raise ValueError("slot would widen inherited CPU or allowed-node masks")
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
    receipt = {"pid": os.getpid(), "time_utc": datetime.now(timezone.utc).isoformat(),
            "original_cpus": sorted(original_cpus), "saved_ancestor_cpus": sorted(envelope),
            "original_allowed_nodes": sorted(original_nodes),
            "requested_cpus": sorted(cpus), "effective_cpus": sorted(effective_cpus),
            "requested_nodes": sorted(nodes), "effective_allowed_nodes": sorted(effective_nodes),
            "inherited_policy": inherited_policy, "requested_policy": requested_policy,
            "observed_policy": observed_policy, "fallback": fallback,
            "cgroup": cgroup, "stage": "pre-exec runner; final engine observation is separate"}
    if saved_ancestor_nodes is not None:
        receipt["saved_ancestor_nodes"] = sorted(saved_ancestor_nodes)
    return receipt


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
