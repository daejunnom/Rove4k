"""Observe NUMA rows for an explicitly supplied live process address range.

This does not discover or authenticate a transposition table.  NUMA page
counts refer to entire overlapping VMAs, which can contain unrelated data.
The two maps snapshots detect ordinary changes, not ABA or concurrent page
migration, and the PID start time does not prove executable continuity.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat


_HEX = re.compile(r"[0-9a-fA-F]+\Z")
_PERMISSIONS = re.compile(r"[r-][w-][x-][ps]\Z")
_NODE = re.compile(r"N(0|[1-9][0-9]*)=(0|[1-9][0-9]*)\Z")
_MAX_FILE = 16 << 20
_MAX_U64 = (1 << 64) - 1


def _read(path: Path, limit: int) -> bytes:
    """Bound proc reads without trusting their generally-zero st_size."""
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) |
                 getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("ordinary proc file required")
        chunks, size = [], 0
        while size <= limit:
            part = os.read(fd, min(65536, limit + 1 - size))
            if not part:
                break
            chunks.append(part)
            size += len(part)
        if size > limit:
            raise ValueError("proc observation exceeds size limit")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _identity(raw: bytes, pid: int) -> dict:
    try:
        prefix, tail = raw.decode("ascii").rsplit(")", 1)
        fields = tail.split()
        if not prefix.startswith(str(pid) + " (") or len(fields) < 20:
            raise ValueError("process stat identity differs")
        if fields[0] not in ("R", "S", "D", "T", "t", "I", "W", "P"):
            raise ValueError("process is not live")
        pgid, session, start = int(fields[2]), int(fields[3]), int(fields[19])
        if pgid <= 0 or session <= 0 or start <= 0:
            raise ValueError("process identity values differ")
        return {"pid": pid, "pgid": pgid, "session": session, "start_ticks": start}
    except (UnicodeDecodeError, IndexError) as error:
        raise ValueError("invalid process stat") from error


def _maps(raw: bytes) -> list[dict]:
    try:
        text = raw.decode("utf-8", "surrogateescape")
        rows, last_end = [], 0
        for line in text.splitlines():
            fields = line.split(maxsplit=5)
            if len(fields) < 5 or fields[0].count("-") != 1:
                raise ValueError("invalid maps row")
            first, last = fields[0].split("-")
            if (not _HEX.fullmatch(first) or not _HEX.fullmatch(last) or
                    not _PERMISSIONS.fullmatch(fields[1]) or not _HEX.fullmatch(fields[2]) or
                    not re.fullmatch(r"[0-9a-fA-F]+:[0-9a-fA-F]+", fields[3]) or
                    not fields[4].isdecimal()):
                raise ValueError("invalid maps field")
            start, end = int(first, 16), int(last, 16)
            offset, inode = int(fields[2], 16), int(fields[4])
            if not 0 <= start < end <= 1 << 64 or start < last_end or offset > _MAX_U64 or inode > _MAX_U64:
                raise ValueError("maps ranges or identity differ")
            rows.append({"start": start, "end": end, "permissions": fields[1],
                         "offset": offset, "device": fields[3], "inode": inode,
                         "path": fields[5] if len(fields) > 5 else ""})
            last_end = end
        if not rows:
            raise ValueError("empty maps observation")
        return rows
    except UnicodeError as error:
        raise ValueError("invalid maps encoding") from error


def _cover(rows: list[dict], address: int, end: int) -> list[dict]:
    result, covered = [], address
    for row in rows:
        if row["end"] <= covered:
            continue
        if row["start"] > covered:
            break
        if row["permissions"][:2] != "rw" or row["permissions"][3] != "p":
            raise ValueError("range is not entirely private readable writable memory")
        result.append(row)
        covered = min(end, row["end"])
        if covered == end:
            return result
    raise ValueError("range is not completely mapped")


def _numa(raw: bytes, starts: set[int], allowed_nodes: set[int]) -> list[dict]:
    try:
        text = raw.decode("utf-8", "surrogateescape")
        seen, matches = set(), []
        for line in text.splitlines():
            fields = line.split()
            if not fields or not _HEX.fullmatch(fields[0]):
                raise ValueError("invalid numa_maps row")
            start = int(fields[0], 16)
            if start not in starts:
                continue
            if start in seen:
                raise ValueError("duplicate numa_maps mapping")
            seen.add(start)
            pages = {}
            for field in fields[1:]:
                if not field.startswith("N"):
                    continue
                match = _NODE.fullmatch(field)
                if match is None:
                    raise ValueError("invalid NUMA page count")
                node, count = int(match.group(1)), int(match.group(2))
                if node not in allowed_nodes or node in pages or count > _MAX_U64:
                    raise ValueError("duplicate or disallowed NUMA node")
                pages[node] = count
            matches.append({"mapping_start": start, "node_pages": pages, "raw": line,
                            "page_count_fields_present": bool(pages)})
        if seen != starts:
            raise ValueError("missing numa_maps row for overlapping mapping")
        return sorted(matches, key=lambda row: row["mapping_start"])
    except UnicodeError as error:
        raise ValueError("invalid numa_maps encoding") from error


def observe_range(pid: int, *, expected_start_ticks: int, address: int, length: int,
                  allowed_nodes, proc: Path = Path("/proc")) -> dict:
    """Read a live PID's explicit range without starting or modifying it.

    ``allowed_nodes`` and the range are caller supplied, not proof of effective
    NUMA policy or TT identity.  Access errors and unstable observations fail.
    A custom ``proc`` is useful for fixtures and is marked as such.
    """
    if (type(pid) is not int or pid <= 0 or type(expected_start_ticks) is not int or expected_start_ticks <= 0 or
            type(address) is not int or type(length) is not int or address <= 0 or length <= 0 or
            address > _MAX_U64 or length > _MAX_U64 or address + length > 1 << 64):
        raise ValueError("bounded PID, process identity and address range required")
    if (not isinstance(allowed_nodes, (list, tuple, set, frozenset)) or not allowed_nodes or
            any(type(node) is not int or not 0 <= node <= _MAX_U64 for node in allowed_nodes) or
            len(set(allowed_nodes)) != len(allowed_nodes)):
        raise ValueError("distinct explicitly supplied NUMA nodes required")
    root = Path(proc) / str(pid)
    before = _identity(_read(root / "stat", 16384), pid)
    if before["start_ticks"] != expected_start_ticks:
        raise ValueError("process start time differs from expected owner")
    first = _cover(_maps(_read(root / "maps", _MAX_FILE)), address, address + length)
    starts = {row["start"] for row in first}
    numa = _numa(_read(root / "numa_maps", _MAX_FILE), starts, set(allowed_nodes))
    second = _cover(_maps(_read(root / "maps", _MAX_FILE)), address, address + length)
    after = _identity(_read(root / "stat", 16384), pid)
    if before != after or first != second:
        raise ValueError("owner or range mappings changed during observation")
    observed = sorted({node for row in numa for node, count in row["node_pages"].items() if count > 0})
    return {"owner": before, "range": {"address": address, "length": length},
            "allowed_nodes_supplied": sorted(allowed_nodes), "mappings": first, "vmas": numa,
            "observed_page_nodes": observed, "all_mapping_starts_observed": True,
            "source": {"kind": "proc-maps-and-numa-maps", "proc_path": str(proc),
                       "fixture": Path(proc) != Path("/proc")},
            "claims": {"caller_range_is_tt": False, "tt_only_residency": False,
                       "remote_access_or_efficiency": False, "executable_continuity": False,
                       "atomic_snapshot_or_aba_excluded": False, "score_go_authority": False},
            "scope": "whole VMAs overlapping caller-supplied range; counts are raw page counts"}
