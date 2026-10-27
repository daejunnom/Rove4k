"""Observe explicitly selected Rove threads without starting or authorizing work.

This reads Linux proc and scheduler state twice.  TIDs are supplied by the
caller: neither their role nor completeness can be inferred from CPU ticks.
The executable image, search state, NUMA placement and score admission are
outside this observer's authority.  It never changes affinity or starts a
process.  Fixtures and injected clocks/affinity functions are marked as such.
"""
from __future__ import annotations

import os
from pathlib import Path
import time
import uuid


def _require(value, reason):
    if not value:
        raise ValueError(reason)


def _read(path, maximum=32768):
    # proc stat and boot_id are small pseudo-files; reject unexpected extents.
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        chunks, size = [], 0
        while size <= maximum:
            part = os.read(fd, min(4096, maximum + 1 - size))
            if not part:
                break
            chunks.append(part)
            size += len(part)
        _require(size <= maximum, "proc record exceeds bounded observation size")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _stat(raw, tid):
    try:
        text = raw.decode("utf-8", errors="strict")
        prefix, suffix = text.rsplit(")", 1)
        _require(prefix.startswith(str(tid) + " ("), "proc task identity differs")
        fields = suffix.split()
        _require(len(fields) >= 20 and fields[0] in ("R", "S", "D", "T", "t", "I", "W", "P"),
                 "proc task is absent, terminal or malformed")
        ppid, pgid, session = (int(fields[i]) for i in (1, 2, 3))
        utime, stime, start = (int(fields[i]) for i in (11, 12, 19))
        _require(ppid >= 0 and pgid > 0 and session > 0 and utime >= 0 and stime >= 0 and start > 0,
                 "proc task counters or ownership differ")
        return {"tid": tid, "start_ticks": start, "cpu_ticks": utime + stime,
                "pgid": pgid, "session": session, "state": fields[0]}
    except (UnicodeError, IndexError, ValueError) as error:
        raise ValueError("invalid or terminal proc task record") from error


def _boot_id(proc_root):
    try:
        raw = _read(proc_root / "sys/kernel/random/boot_id", 128).decode("ascii").strip()
        _require(str(uuid.UUID(raw)) == raw, "canonical boot identity required")
        return raw
    except (UnicodeError, ValueError) as error:
        raise ValueError("invalid boot identity") from error


def _ids(values, count, name, *, allow_zero=False):
    _require(isinstance(values, (list, tuple)) and len(values) == count
             and all(type(value) is int and value >= (0 if allow_zero else 1) for value in values)
             and len(set(values)) == count, "explicit unique " + name + " required")
    return sorted(values)


def _leader(proc_root, pid, expected_start_ticks, expected_pgid, expected_session):
    row = _stat(_read(proc_root / str(pid) / "stat"), pid)
    _require((row["start_ticks"], row["pgid"], row["session"]) ==
             (expected_start_ticks, expected_pgid, expected_session), "original process identity changed")
    return row


def _sample(proc_root, pid, tids, cpus, leader, affinity, deadline, clock):
    result = {}
    for tid in tids:
        _require(clock() <= deadline, "worker observation exceeded deadline")
        path = proc_root / str(pid) / "task" / str(tid) / "stat"
        before = _stat(_read(path), tid)
        actual = sorted(affinity(tid))
        after = _stat(_read(path), tid)
        _require(before["start_ticks"] == after["start_ticks"]
                 and before["pgid"] == after["pgid"] == leader["pgid"]
                 and before["session"] == after["session"] == leader["session"]
                 and after["cpu_ticks"] >= before["cpu_ticks"],
                 "worker identity or CPU counters changed during affinity observation")
        _require(actual == cpus, "worker effective CPU mask differs from requested envelope")
        result[tid] = {"tid": tid, "start_ticks": after["start_ticks"],
                       "cpus": actual, "cpu_ticks_first": before["cpu_ticks"],
                       "cpu_ticks_last": after["cpu_ticks"]}
    return result


def observe_workers(pid, *, profile, expected_boot_id, expected_start_ticks, expected_pgid, expected_session,
                    worker_tids, cpu_ids,
                    sample_seconds=0.1, proc_root=Path("/proc"),
                    affinity_for_test=None, sleep_for_test=None, clock_for_test=None):
    """Measure selected task identities, masks and CPU tick progress twice.

    ``worker_tids`` and ``cpu_ids`` must have exactly 16 or 192 distinct
    members according to the named profile. The caller owns the identity and
    is responsible for choosing tasks during a live search and independently
    checking the actual native image. The leader is allowed as a selected TID.
    Returns a diagnostic observation, never an admission or GO authority.
    """
    _require(os.name == "posix" and hasattr(os, "sched_getaffinity"), "Linux scheduler observation required")
    _require(type(pid) is int and pid > 0 and type(expected_start_ticks) is int and expected_start_ticks > 0
             and type(expected_pgid) is int and expected_pgid > 0
             and type(expected_session) is int and expected_session > 0,
             "original PID, start ticks, process group and session required")
    try:
        _require(type(expected_boot_id) is str and str(uuid.UUID(expected_boot_id)) == expected_boot_id,
                 "original canonical boot identity required")
    except (ValueError, AttributeError) as error:
        raise ValueError("original canonical boot identity required") from error
    _require(profile in ("test-p16", "test-p192"), "P16 or P192 required")
    count = {"test-p16": 16, "test-p192": 192}[profile]
    tids = _ids(worker_tids, count, "worker TIDs")
    cpus = _ids(cpu_ids, count, "CPU IDs", allow_zero=True)
    _require(type(sample_seconds) in (int, float) and 0.02 <= sample_seconds <= 5,
             "observation interval must be from 0.02 to 5 seconds")
    proc_root = Path(proc_root)
    fixture = proc_root != Path("/proc") or any(x is not None for x in (affinity_for_test, sleep_for_test, clock_for_test))
    _require(proc_root != Path("/proc") or not fixture, "test injections cannot claim a live proc observation")
    affinity, sleep, clock = affinity_for_test or os.sched_getaffinity, sleep_for_test or time.sleep, clock_for_test or time.monotonic
    try:
        started = clock()
        deadline = started + 15.0
        boot = _boot_id(proc_root)
        _require(boot == expected_boot_id, "original boot identity changed")
        original = _leader(proc_root, pid, expected_start_ticks, expected_pgid, expected_session)
        first = _sample(proc_root, pid, tids, cpus, original, affinity, deadline, clock)
        middle = _leader(proc_root, pid, expected_start_ticks, expected_pgid, expected_session)
        _require((middle["pgid"], middle["session"]) == (original["pgid"], original["session"]),
                 "original process group or session changed")
        before_pause = clock()
        sleep(float(sample_seconds))
        after_pause = clock()
        _require(started <= before_pause <= after_pause <= deadline
                 and after_pause - before_pause + 1e-6 >= float(sample_seconds),
                 "requested observation interval was not completed")
        second = _sample(proc_root, pid, tids, cpus, original, affinity, deadline, clock)
        final = _leader(proc_root, pid, expected_start_ticks, expected_pgid, expected_session)
        ended = clock()
        _require(started <= ended <= deadline and _boot_id(proc_root) == boot
                 and (final["pgid"], final["session"]) == (original["pgid"], original["session"]),
                 "observation deadline, boot identity or owner changed")
        evidence = []
        for tid in tids:
            a, b = first[tid], second[tid]
            _require(a["start_ticks"] == b["start_ticks"] and b["cpu_ticks_first"] >= a["cpu_ticks_last"],
                     "worker was replaced or CPU counters moved backwards")
            evidence.append({"tid": tid, "start_ticks": a["start_ticks"], "cpus": cpus,
                             "cpu_ticks_first": a["cpu_ticks_first"], "cpu_ticks_last": b["cpu_ticks_last"],
                             "positive_cpu_ticks": b["cpu_ticks_last"] > a["cpu_ticks_first"]})
        return {"format": "rove4k-worker-observation-v1", "profile": profile,
                "boot_id": boot, "owner": {"pid": pid, "start_ticks": expected_start_ticks,
                                            "pgid": original["pgid"], "session": original["session"]},
                "sample_seconds_requested": float(sample_seconds), "sample_seconds_observed": after_pause - before_pause,
                "elapsed_seconds": ended - started,
                "workers": evidence, "positive_worker_ids": [row["tid"] for row in evidence if row["positive_cpu_ticks"]],
                "all_selected_workers_positive": all(row["positive_cpu_ticks"] for row in evidence),
                "fixture_inputs": fixture, "native_identity_verified": False,
                "pid_namespace_binding_verified": False, "continuous_affinity_verified": False,
                "selected_worker_set_complete": False, "search_causality_verified": False,
                "observed_entire_search": False, "numa_placement_verified": False,
                "scored_game_admitted": False,
                "scope": "two bounded observations of caller-selected live tasks; not a search or admission proof"}
    except (OSError, ProcessLookupError) as error:
        raise ValueError("original process or selected worker is unavailable") from error
