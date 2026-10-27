"""Observe one live Linux host/cgroup memory envelope without reserving it.

This reads no workload or credential files. The result is evidence for a
separate preflight, not a memory reservation, overhead estimate, TT placement
or scored-run admission. Cgroup namespace ancestors outside the visible mount
cannot be established by these reads and are always explicitly unverified.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import time


MAXIMUM = (1 << 63) - 1


def _root(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("observation roots must be absolute")
    for part in path.parts:
        lower = part.casefold()
        if (lower.startswith(".env") or lower in (".ssh", ".aws", "inventory.json") or
                any(word in lower for word in ("credential", "service-account", "service_account", "api_key", "api-key", "ssh_key"))):
            raise ValueError("protected paths are not observation roots")
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError("observation roots must not traverse symlinks")
    result = path.resolve(strict=True)
    if not result.is_dir():
        raise ValueError("observation root must be a directory")
    return result


def _file(path, *, filesystem=False):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("observation files must not be symlinks")
    if os.name == "posix" and not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("safe no-follow observation is unavailable")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        data = stream.read(65537)
    if len(data) > 65536:
        raise ValueError("observation file exceeds bounded extent")
    try:
        return os.fsdecode(data) if filesystem else data.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("invalid observation encoding") from error


def _kb(text, expression, message):
    hits = re.findall(expression, text, flags=re.MULTILINE)
    if len(hits) != 1 or not hits[0].isdecimal():
        raise ValueError(message)
    value = int(hits[0]) * 1024
    if not 0 < value <= MAXIMUM:
        raise ValueError(message)
    return value


def _linux_list(text):
    values = set()
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty effective CPU/node mask")
    for part in text.strip().split(","):
        if not re.fullmatch(r"\d+(?:-\d+)?", part):
            raise ValueError("invalid effective CPU/node mask")
        ends = [int(value) for value in part.split("-")]
        first, last = ends[0], ends[-1]
        if first > last or last > 1_000_000 or last - first > 1_000_000:
            raise ValueError("invalid effective CPU/node extent")
        values.update(range(first, last + 1))
    return values


def _allowed_nodes(text):
    matches = re.findall(r"^Mems_allowed_list:\s*([^\r\n]+)\s*$", text, re.MULTILINE)
    if len(matches) != 1:
        raise ValueError("controller allowed memory-node mask unavailable")
    return _linux_list(matches[0])


def _below(root, relative):
    if not isinstance(relative, str) or not relative.startswith("/"):
        raise ValueError("invalid cgroup membership path")
    if any(part in (".", "..") for part in relative.split("/")):
        raise ValueError("cgroup membership path escapes the mount")
    parts = PurePosixPath(relative).parts[1:]
    path = root.joinpath(*parts)
    for candidate in (path, *path.parents):
        if candidate == root:
            break
        if candidate.is_symlink():
            raise ValueError("cgroup membership traverses a symlink")
    if not path.is_dir():
        raise ValueError("visible controller cgroup is unavailable")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError("controller cgroup escapes the mount")
    return resolved


def _cgroup_ancestors(path, mount):
    """Read all visible v2 ancestors. Missing kernel root files are explicit."""
    if not path.is_relative_to(mount):
        raise ValueError("cgroup path escapes the mount")
    records, finite = [], []
    current = path
    mount_device = mount.stat().st_dev
    while True:
        if current.is_symlink() or current.stat().st_dev != mount_device:
            raise ValueError("visible cgroup ancestor changed filesystem identity")
        maximum_path, usage_path = current / "memory.max", current / "memory.current"
        if maximum_path.is_symlink() or usage_path.is_symlink():
            raise ValueError("visible cgroup memory files must not be symlinks")
        if current == mount and not maximum_path.exists() and not usage_path.exists():
            records.append({"path": str(current), "root_memory_files_unavailable": True})
        else:
            # Intermediate or partially visible/malformed controller files are
            # not silently treated as unlimited.
            maximum, usage = _file(maximum_path).strip(), _file(usage_path).strip()
            if maximum != "max" and not maximum.isdecimal() or not usage.isdecimal():
                raise ValueError("invalid visible cgroup v2 memory values")
            used = int(usage)
            if used < 0 or used > MAXIMUM:
                raise ValueError("cgroup current usage outside supported range")
            limit = None if maximum == "max" else int(maximum)
            if limit is not None and not 0 < limit <= MAXIMUM:
                raise ValueError("invalid finite cgroup memory limit")
            remaining = None if limit is None else limit - used
            if remaining is not None and remaining <= 0:
                raise ValueError("visible cgroup has no remaining memory")
            if remaining is not None:
                finite.append(remaining)
            records.append({"path": str(current), "limit_bytes": limit, "current_bytes": used,
                            "remaining_bytes": remaining, "root_memory_files_unavailable": False})
        if current == mount:
            break
        current = current.parent
    return records, finite


def _mount_record(text, mount):
    """Require an unambiguous visible cgroup2 root/mount mapping."""
    def decode(value):
        return re.sub(r"\\(040|011|012|134)", lambda match: chr(int(match[1], 8)), value)
    matches = []
    for line in text.splitlines():
        before, separator, after = line.partition(" - ")
        if not separator:
            raise ValueError("malformed mountinfo record")
        left, right = before.split(), after.split()
        if len(left) < 6 or len(right) < 3:
            raise ValueError("malformed mountinfo fields")
        if right[0] == "cgroup2" and decode(left[4]) == str(mount):
            if not left[0].isdecimal() or not re.fullmatch(r"\d+:\d+", left[2]):
                raise ValueError("invalid cgroup2 mount identity")
            matches.append({"mount_id": left[0], "device": left[2],
                            "root": decode(left[3]), "mount": decode(left[4])})
    if len(matches) != 1 or matches[0]["root"] != "/":
        raise ValueError("unverified or ambiguous cgroup2 mount mapping")
    return matches[0]


def observe_capacity(slots, cgroup_root, *, proc_root=Path("/proc"),
                     node_root=Path("/sys/devices/system/node"), cgroup_mount=Path("/sys/fs/cgroup"),
                     page_size_for_test=None, cpu_affinity_for_test=None, extra_nodes=(),
                     mask_scope="observer-and-delegated"):
    """Capture actual visible host, controller, delegated root and NUMA bounds.

    Injected roots/page size support fixtures only; they do not create trusted
    live evidence. A controller cannot infer invisible host ancestors from a
    cgroup namespace. The caller must separately bind provenance, freshness,
    ownership, overhead and the scored-execution authority.

    The default requires slot masks in both the observer and delegated root.
    ``delegated-only`` supports a separate observer in a smaller sibling:
    it observes the target masks, without granting permission to enter them or
    proving their ownership, topology, or future stability. Observer masks
    remain recorded and rechecked in both modes.
    """
    started = time.monotonic_ns()
    if mask_scope not in ("observer-and-delegated", "delegated-only"):
        raise ValueError("unknown observer/delegated mask scope")
    proc_root, node_root, mount, delegated = map(_root, (proc_root, node_root, cgroup_mount, cgroup_root))
    if not delegated.is_relative_to(mount) or delegated == mount:
        raise ValueError("delegated root must be a strict visible cgroup descendant")
    if not isinstance(slots, (list, tuple)) or not 1 <= len(slots) <= 11:
        raise ValueError("one through eleven observed slot records required")
    if (not isinstance(extra_nodes, (list, tuple, set)) or len(extra_nodes) > 4096 or
            any(type(node) is not int or not 0 <= node <= 1_000_000 for node in extra_nodes) or
            len(extra_nodes) != len(set(extra_nodes))):
        raise ValueError("distinct bounded extra memory-node identities required")
    # Snapshot caller input before the kernel reads; extras describe nodes a
    # target controller may use, not a change to the frozen slot digest.
    extra_nodes = frozenset(extra_nodes)
    rows, ids, nodes, selected_cpus = [], set(), set(), set()
    for slot in slots:
        row = slot.to_record() if hasattr(slot, "to_record") else slot
        if not isinstance(row, dict):
            raise ValueError("slot record required")
        try:
            row = json.loads(json.dumps(row, sort_keys=True, separators=(",", ":"),
                                        ensure_ascii=False, allow_nan=False))
        except (ValueError, TypeError) as error:
            raise ValueError("invalid slot record") from error
        identity, slot_nodes, cpus = row.get("id"), row.get("memory_nodes"), row.get("cpus")
        if (not isinstance(identity, str) or not re.fullmatch(r"slot-\d{3}", identity) or identity in ids or
                not isinstance(slot_nodes, (list, tuple)) or not slot_nodes or
                any(type(node) is not int or node < 0 for node in slot_nodes) or
                len(set(slot_nodes)) != len(slot_nodes)):
            raise ValueError("invalid or duplicate slot identity or node mask")
        if (not isinstance(cpus, (list, tuple)) or not cpus or
                any(type(cpu) is not int or cpu < 0 for cpu in cpus) or len(set(cpus)) != len(cpus) or
                selected_cpus.intersection(cpus)):
            raise ValueError("invalid or overlapping slot CPU masks")
        ids.add(identity)
        nodes.update(slot_nodes)
        selected_cpus.update(cpus)
        rows.append(row)
    try:
        slot_bytes = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                                allow_nan=False).encode("utf-8")
    except (ValueError, TypeError) as error:
        raise ValueError("invalid slot record") from error
    if len(slot_bytes) > 64 << 10:
        raise ValueError("slot record exceeds bounded extent")
    # The digest and retained records must stay bound if the caller mutates
    # an input dict while the filesystem sampling is in progress.
    rows = json.loads(slot_bytes)
    boot = _file(proc_root / "sys/kernel/random/boot_id").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}", boot):
        raise ValueError("invalid boot identity")
    host = _kb(_file(proc_root / "meminfo"), r"^MemAvailable:\s*(\d+)\s+kB\s*$",
               "host MemAvailable is missing or invalid")
    membership_text = _file(proc_root / "self/cgroup")
    mount_text = _file(proc_root / "self/mountinfo", filesystem=True)
    mount_record = _mount_record(mount_text, mount)
    if not hasattr(os, "major") or not hasattr(os, "minor"):
        raise ValueError("cgroup mount device identity is unavailable")
    mount_device = mount.stat().st_dev
    if mount_record["device"] != f"{os.major(mount_device)}:{os.minor(mount_device)}":
        raise ValueError("cgroup mount device differs from mountinfo")
    status_nodes = _allowed_nodes(_file(proc_root / "self/status"))
    delegated_cpus = _linux_list(_file(delegated / "cpuset.cpus.effective"))
    delegated_nodes = _linux_list(_file(delegated / "cpuset.mems.effective"))
    if cpu_affinity_for_test is None:
        if not hasattr(os, "sched_getaffinity"):
            raise ValueError("controller CPU affinity unavailable")
        controller_cpus = set(os.sched_getaffinity(0))
    else:
        if (not isinstance(cpu_affinity_for_test, (tuple, list, set)) or not cpu_affinity_for_test or
                any(type(cpu) is not int or cpu < 0 for cpu in cpu_affinity_for_test)):
            raise ValueError("invalid fixture controller CPU affinity")
        controller_cpus = set(cpu_affinity_for_test)
    observed_nodes = nodes | extra_nodes
    if (not selected_cpus <= delegated_cpus or not observed_nodes <= delegated_nodes or
            mask_scope == "observer-and-delegated" and
            (not selected_cpus <= controller_cpus or not nodes <= status_nodes)):
        raise ValueError("slots exceed actual controller or delegated effective masks")
    membership = []
    for line in membership_text.splitlines():
        fields = line.split(":", 2)
        if len(fields) != 3:
            raise ValueError("invalid cgroup membership record")
        if fields[0:2] == ["0", ""]:
            membership.append(fields[2])
    if len(membership) != 1:
        raise ValueError("exactly one visible cgroup v2 membership is required")
    controller = _below(mount, membership[0])
    controller_stat, delegated_stat = controller.stat(), delegated.stat()
    controller_rows, controller_finite = _cgroup_ancestors(controller, mount)
    delegated_rows, delegated_finite = _cgroup_ancestors(delegated, mount)
    node_available = {}
    for node in sorted(observed_nodes):
        directory = node_root / f"node{node}"
        if directory.is_symlink() or not directory.is_dir() or not directory.resolve().is_relative_to(node_root):
            raise ValueError("node directory is unavailable or unsafe")
        node_available[node] = _kb(_file(directory / "meminfo"),
            rf"^Node\s+{node}\s+MemFree:\s*(\d+)\s+kB\s*$", "node MemFree is missing or invalid")
    page = os.sysconf("SC_PAGE_SIZE") if page_size_for_test is None else page_size_for_test
    if type(page) is not int or not 0 < page <= 1 << 30 or page & (page - 1):
        raise ValueError("invalid kernel page size")
    controller_after, delegated_after = controller.stat(), delegated.stat()
    if ((controller_stat.st_dev, controller_stat.st_ino) != (controller_after.st_dev, controller_after.st_ino) or
            (delegated_stat.st_dev, delegated_stat.st_ino) != (delegated_after.st_dev, delegated_after.st_ino) or
            _file(proc_root / "self/cgroup") != membership_text or
            _file(proc_root / "self/mountinfo", filesystem=True) != mount_text or
            _allowed_nodes(_file(proc_root / "self/status")) != status_nodes or
            _linux_list(_file(delegated / "cpuset.cpus.effective")) != delegated_cpus or
            _linux_list(_file(delegated / "cpuset.mems.effective")) != delegated_nodes or
            cpu_affinity_for_test is None and set(os.sched_getaffinity(0)) != controller_cpus or
            _file(proc_root / "sys/kernel/random/boot_id").strip().lower() != boot):
        raise ValueError("cgroup identity, membership, mount or boot changed during observation")
    effective = min([host, *controller_finite, *delegated_finite])
    return {"format": "rove4k-memory-capacity-observation-v1", "boot_id": boot,
            "time_utc": datetime.now(timezone.utc).isoformat(), "started_monotonic_ns": started,
            "completed_monotonic_ns": time.monotonic_ns(), "mount": mount_record,
            "controller_membership": membership[0],
            "controller_cpu_affinity": sorted(controller_cpus), "controller_allowed_nodes": sorted(status_nodes),
            "mask_scope": mask_scope,
            "extra_nodes": sorted(extra_nodes),
            "delegated_effective_cpus": sorted(delegated_cpus), "delegated_effective_nodes": sorted(delegated_nodes),
            "controller_identity": {"device": controller_stat.st_dev, "inode": controller_stat.st_ino},
            "delegated_identity": {"device": delegated_stat.st_dev, "inode": delegated_stat.st_ino},
            "slot_sha256": hashlib.sha256(slot_bytes).hexdigest(), "slots": rows,
            "host_memavailable_bytes": host, "host_available_bytes": effective,
            "controller_cgroup": controller_rows, "delegated_cgroup": delegated_rows,
            "node_available_bytes": node_available, "page_bytes": page,
            "test_inputs": page_size_for_test is not None or cpu_affinity_for_test is not None or proc_root != Path("/proc") or
                           node_root != Path("/sys/devices/system/node") or mount != Path("/sys/fs/cgroup"),
            "hidden_ancestors_verified": False, "runtime_admission_complete": False,
            "scope": "one point-in-time visible read; no reservation, overhead, TT placement or hidden-ancestor claim"}
