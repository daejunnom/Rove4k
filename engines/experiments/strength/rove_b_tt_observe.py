"""Observe a candidate B pointer in its original owned live process.

The symbol and native digest are caller-supplied and are not source/compiler
attestation.  This diagnostic does not qualify the runtime, prove that the
symbol denotes the transposition table, reserve memory or authorize a game.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import sys

try:
    from . import memory_observation, peak_probe_session, peer_runtime, placement, rove_vma_observer
except ImportError:
    import memory_observation
    import peak_probe_session
    import peer_runtime
    import placement
    import rove_vma_observer

_PROFILE_TT_BYTES = {"test-p16": 24 * (1 << 29), "test-p192": 24 * (1 << 33)}
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_BOOT = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")
_SYMBOL = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}\Z")
_MAX_IMAGE = 256 << 20


class ObservationUnavailable(RuntimeError):
    """Kernel permissions prevent the requested pointer or NUMA observation."""


def _image(pid, expected_sha):
    """Read the actual /proc image via a pinned FD, not a reference path."""
    fd = os.open(f"/proc/{pid}/exe", os.O_RDONLY | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if not 0 < before.st_size <= _MAX_IMAGE:
            raise ValueError("native image extent is invalid")
        data = bytearray()
        while len(data) < before.st_size:
            part = os.read(fd, min(65536, before.st_size - len(data)))
            if not part:
                raise ValueError("native image read was incomplete")
            data.extend(part)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("native image changed while reading")
        raw = bytes(data)
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            raise ValueError("live native image differs from its pinned digest")
        return raw, (before.st_dev, before.st_ino, before.st_size)
    finally:
        os.close(fd)


def _require_kernel_group(path):
    if (not path.is_absolute() or ".." in path.parts or
            any(part.is_symlink() for part in (path, *path.parents))):
        raise ValueError("cgroup path must be an absolute non-symlink descendant")
    peak_probe_session._require_delegated_root(path)


def _group(pid, cgroup):
    path = Path(cgroup["path"])
    _require_kernel_group(path)
    expected = placement.verify_cgroup_live(cgroup)
    if str(pid) not in memory_observation._file(path / "cgroup.procs").splitlines():
        raise ValueError("owned process left its cgroup")
    return {k: expected[k] for k in ("device", "inode", "cpus", "memory_nodes", "memory_max")}


def _boot():
    value = memory_observation._file(Path("/proc/sys/kernel/random/boot_id")).strip()
    if not _BOOT.fullmatch(value):
        raise ValueError("kernel boot identity unavailable")
    return value


def _symbol_value(elf, symbol):
    """Require a real allocated writable object section, not just an address."""
    value = elf.pointer_symbol(symbol)
    matches = []
    for table in elf.sections:
        if table[1] != 2:
            continue
        strings = elf.segment(elf.sections[table[6]][4], elf.sections[table[6]][5])
        for offset in range(table[4], table[4] + table[5], table[9]):
            item = elf.unpack("IBBHQQ", offset)
            if elf.string(strings, item[0]) == symbol and item[1] & 15 == 1 and item[3] != 0:
                matches.append(item)
    if len(matches) != 1:
        raise ValueError("symbol metadata differs")
    item = matches[0]
    index = item[3]
    if item[1] >> 4 == 2 or not 0 < index < min(len(elf.sections), 0xff00):
        raise ValueError("weak or special-section symbol is not supported")
    section = elf.sections[index]
    kind, flags, start, offset, size = section[1:6]
    if kind not in (1, 8) or flags & 3 != 3 or not start <= value or value + 8 > start + size:
        raise ValueError("symbol is not in an allocated writable object section")
    owners = [p for p in elf.programs if p[0] == 1 and (p[1] & 6) == 6 and
              p[3] <= start and start + size <= p[3] + p[6]]
    if len(owners) != 1:
        raise ValueError("symbol section is not in one readable writable load segment")
    segment = owners[0]
    if kind == 1:
        elf.segment(offset, size)
        if offset - segment[2] != start - segment[3] or offset + size > segment[2] + segment[5]:
            raise ValueError("symbol section file mapping differs from its load segment")
    elif start < segment[3] + segment[5]:
        raise ValueError("NOBITS symbol section overlaps file-backed load bytes")
    return value


def _candidate_pointer(pid, elf, symbol_value, tt_bytes, expected_image_identity):
    """Read only the original image's pointer; integrity errors remain errors."""
    image_stat = Path(f"/proc/{pid}/exe").stat()
    if (image_stat.st_dev, image_stat.st_ino, image_stat.st_size) != expected_image_identity:
        raise ValueError("live native image identity changed")
    rows = peer_runtime.mappings(pid)
    image_rows = [row for row in rows if row["inode"] == image_stat.st_ino and
                  tuple(int(part, 16) for part in row["device"].split(":")) ==
                  (os.major(image_stat.st_dev), os.minor(image_stat.st_dev))]
    loads = [program for program in elf.programs if program[0] == 1 and program[2] == 0]
    if len(loads) != 1:
        raise ValueError("native has no unique zero-offset load segment")
    bases = {row["start"] - loads[0][3] for row in image_rows if row["offset"] == 0}
    if len(bases) != 1:
        raise ValueError("native image load bias is ambiguous")
    bias = next(iter(bases))
    address = bias + symbol_value
    if not (any(program[0] == 1 and bias + program[3] <= address and
                address + 8 <= bias + program[3] + program[6] for program in elf.programs) and
            any(row["start"] <= address and address + 8 <= row["end"] and
                "r" in row["permissions"] for row in rows)):
        raise ValueError("symbol lies outside the readable image mappings")
    try:
        descriptor = os.open(f"/proc/{pid}/mem", os.O_RDONLY | os.O_CLOEXEC)
    except PermissionError as error:
        raise ObservationUnavailable("kernel denied reading the process pointer") from error
    try:
        try:
            value = os.pread(descriptor, 8, address)
        except PermissionError as error:
            raise ObservationUnavailable("kernel denied reading the process pointer") from error
    finally:
        os.close(descriptor)
    if len(value) != 8:
        raise ValueError("pointer read was incomplete")
    pointer = int.from_bytes(value, "little")
    if not 0 < pointer or pointer + tt_bytes >= 1 << 63:
        raise ValueError("pointer range is invalid")
    coverage, mapped = pointer, []
    for row in rows:
        if row["end"] <= coverage or row["start"] > coverage:
            continue
        if row["permissions"][:2] != "rw" or row["permissions"][3] != "p":
            raise ValueError("pointer range is not private readable writable memory")
        mapped.append(row)
        coverage = min(pointer + tt_bytes, row["end"])
        if coverage == pointer + tt_bytes:
            break
    if coverage != pointer + tt_bytes:
        raise ValueError("pointer mapping is smaller than the declared range")
    return {"pointer_symbol_address": address, "pointer": pointer, "mappings": mapped}


def _observe_numa(pid, *, expected_start_ticks, address, length, allowed_nodes):
    try:
        return rove_vma_observer.observe_range(pid, expected_start_ticks=expected_start_ticks,
                    address=address, length=length, allowed_nodes=allowed_nodes)
    except PermissionError as error:
        # Only denial of the actual NUMA file is an observation limitation.
        # Denial of stat/maps or unrelated files must remain a hard error.
        if error.filename is not None and Path(error.filename) == Path(f"/proc/{pid}/numa_maps"):
            raise ObservationUnavailable("kernel denied reading NUMA mappings") from error
        raise


def observe_owned_b(owned, *, native_sha256, expected_identity, cgroup, profile, allowed_nodes, symbol="qq"):
    """Read one candidate pointer/range from the original owned B process.

    ``symbol`` is a caller-supplied candidate, not evidence of its semantic
    identity. Only P16/P192 fixed B TT byte sizes are accepted. The output is
    observation data; it cannot stand in for compilation replay, source
    provenance, an authenticated cgroup owner, full qualification, or GO.
    """
    if sys.platform != "linux" or profile not in _PROFILE_TT_BYTES:
        raise ValueError("Linux and a P16/P192 B profile are required")
    if not isinstance(native_sha256, str) or not _SHA.fullmatch(native_sha256):
        raise ValueError("pinned native SHA-256 required")
    if not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol):
        raise ValueError("exact bounded symbol candidate required")
    if (not isinstance(allowed_nodes, (list, tuple)) or not allowed_nodes or
            any(type(x) is not int or x < 0 for x in allowed_nodes) or len(set(allowed_nodes)) != len(allowed_nodes)):
        raise ValueError("distinct allowed NUMA nodes are required")
    try:
        pid = owned.process.pid
    except AttributeError as error:
        raise ValueError("original owned process handle is required") from error
    if type(pid) is not int or pid <= 0 or owned.exited():
        raise ValueError("owned process is not alive")
    before = placement._process_identity(pid)
    if (before != expected_identity or not before["alive"] or
            before["pgid"] != pid or before["session"] != pid):
        raise ValueError("owned process identity changed")
    boot_before = _boot()
    group_before = _group(pid, cgroup)
    if sorted(allowed_nodes) != group_before["memory_nodes"]:
        raise ValueError("allowed nodes differ from the observed cgroup")
    image, image_identity = _image(pid, native_sha256)
    elf = peer_runtime.Elf64(image)
    address = _symbol_value(elf, symbol)
    tt_bytes = _PROFILE_TT_BYTES[profile]
    first = _candidate_pointer(pid, elf, address, tt_bytes, image_identity)
    vmas = _observe_numa(pid, expected_start_ticks=before["start_ticks"],
              address=first["pointer"], length=tt_bytes, allowed_nodes=allowed_nodes)
    second = _candidate_pointer(pid, elf, address, tt_bytes, image_identity)
    second_image, image_identity_after = _image(pid, native_sha256)
    after, group_after, boot_after = placement._process_identity(pid), _group(pid, cgroup), _boot()
    if (owned.exited() or before != after or boot_before != boot_after or group_before != group_after or
            image_identity != image_identity_after or image != second_image or
            first["pointer_symbol_address"] != second["pointer_symbol_address"] or
            first["pointer"] != second["pointer"] or first["mappings"] != second["mappings"]):
        raise ValueError("process, image, pointer, or mappings changed during observation")
    return {"format": "rove4k-b-symbol-candidate-v1", "profile": profile,
            "owner": before, "boot_id": boot_before, "cgroup": group_before,
            "native_sha256": native_sha256, "native_identity": {"device": image_identity[0],
                "inode": image_identity[1], "bytes": image_identity[2]},
            "symbol_candidate": symbol, "elf_symbol_offset": address,
            "symbol_address": first["pointer_symbol_address"], "pointer": first["pointer"],
            "declared_entry_bytes": 24, "declared_range_bytes": tt_bytes,
            "mappings": first["mappings"], "numa": vmas,
            "claims": {"symbol_represents_tt": False, "source_compiler_provenance": False,
                       "cgroup_owner_authenticated": False,
                       "physical_reservation": False, "tt_only_pages": False,
                       "atomic_snapshot_or_aba_excluded": False, "runtime_qualified": False,
                       "score_go_authority": False},
            "scope": "live symbol candidate and overlapping VMAs; caller must prove source and symbol semantics"}
