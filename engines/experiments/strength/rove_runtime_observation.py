"""Read-only observation of a running, pinned Rove candidate.

This does not launch an engine, send UCI commands, reserve memory, or grant
admission. Caller-selected TIDs and a caller-supplied address are observations,
not proof of the complete worker set or that the address belongs to the TT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid

try:
    from . import diagnostic_candidates, rove_worker_observer, rove_vma_observer
except ImportError:
    import diagnostic_candidates
    import rove_worker_observer
    import rove_vma_observer

_MAX_NATIVE_BYTES = 256 << 20


def _boot_id(proc):
    try:
        value = rove_vma_observer._read(proc / "sys/kernel/random/boot_id", 128).decode("ascii").strip()
        if str(uuid.UUID(value)) != value:
            raise ValueError("boot identity is not canonical")
    except (ValueError, AttributeError, UnicodeDecodeError) as error:
        raise ValueError("boot identity is invalid") from error
    return value


def _owner(pid, proc):
    """Read a stable process start identity; the executable may be a memfd."""
    if type(pid) is not int or pid <= 0:
        raise ValueError("positive process ID required")
    raw = rove_vma_observer._read(proc / str(pid) / "stat", 16384)
    try:
        prefix, suffix = raw.decode("ascii").rsplit(")", 1)
        fields = suffix.split()
        if not prefix.startswith(str(pid) + " (") or len(fields) < 20:
            raise ValueError("process stat identity differs")
        row = {"pid": pid, "start_ticks": int(fields[19]),
               "pgid": int(fields[2]), "session": int(fields[3])}
        if (fields[0] not in ("R", "S", "D", "T", "t", "I", "W", "P") or
                any(row[key] <= 0 for key in ("start_ticks", "pgid", "session"))):
            raise ValueError("process is not live")
        return row
    except (UnicodeDecodeError, IndexError) as error:
        raise ValueError("invalid process stat") from error


def _native(pid, expected_start_ticks, expected_sha256, proc):
    before = _owner(pid, proc)
    if before["start_ticks"] != expected_start_ticks:
        raise ValueError("process start identity differs")
    path = proc / str(pid) / "exe"
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
    try:
        first = os.fstat(fd)
        if not stat.S_ISREG(first.st_mode) or not 0 < first.st_size <= _MAX_NATIVE_BYTES:
            raise ValueError("native executable extent differs")
        digest, count = hashlib.sha256(), 0
        while True:
            block = os.read(fd, 1 << 20)
            if not block:
                break
            count += len(block)
            if count > _MAX_NATIVE_BYTES:
                raise ValueError("native executable exceeds bound")
            digest.update(block)
        last, live = os.fstat(fd), path.stat()
        stamp = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns)
        if (stamp(first) != stamp(last) or stamp(first) != stamp(live) or
                count != first.st_size or digest.hexdigest() != expected_sha256):
            raise ValueError("running native image differs from candidate")
    finally:
        os.close(fd)
    after = _owner(pid, proc)
    if before != after:
        raise ValueError("process identity changed while reading executable")
    return {"owner": before, "sha256": expected_sha256, "bytes": count,
            "device": first.st_dev, "inode": first.st_ino}


def observe_candidate(*, candidate_path, candidate_sha256, profile, artifact_id,
                      pid, expected_start_ticks, expected_boot_id, expected_pgid,
                      expected_session, worker_tids, cpu_ids,
                      allowed_nodes, sample_seconds=0.1, address=None,
                      proc=Path("/proc")):
    """Observe a pinned candidate already running under an external owner.

    The full 24-byte TT extent is used only as the length of a caller-selected
    range. Its provenance, real residency, ownership and worker completeness
    remain unproved even when every selected thread has positive CPU ticks.
    """
    if profile not in ("test-p16", "test-p192"):
        raise ValueError("P16 or P192 required")
    rows, candidate_digest = diagnostic_candidates.read_candidates(candidate_path, candidate_sha256, profile)
    selected = [row for row in rows if row["artifact"].id == artifact_id]
    if len(selected) != 1:
        raise ValueError("one pinned candidate identity is required")
    row = selected[0]
    artifact = row["artifact"]
    if (artifact.family not in ("A", "B", "C", "E", "F") or artifact.profile != profile or
            artifact.entry_bytes != 24 or artifact.tt_bytes != {"test-p16": 12 << 30, "test-p192": 192 << 30}[profile]):
        raise ValueError("Rove profile or TT layout differs")
    proc = Path(proc)
    if _boot_id(proc) != expected_boot_id:
        raise ValueError("boot identity differs")
    native_before = _native(pid, expected_start_ticks, artifact.native_sha256, proc)
    if (native_before["owner"]["pgid"], native_before["owner"]["session"]) != (expected_pgid, expected_session):
        raise ValueError("process group or session differs")
    worker = rove_worker_observer.observe_workers(
        pid, profile=profile, expected_start_ticks=expected_start_ticks,
        expected_boot_id=expected_boot_id, expected_pgid=expected_pgid, expected_session=expected_session,
        worker_tids=worker_tids, cpu_ids=cpu_ids, sample_seconds=sample_seconds, proc_root=proc)
    vma = None
    if address is not None:
        vma = rove_vma_observer.observe_range(
            pid, expected_start_ticks=expected_start_ticks, address=address,
            length=artifact.tt_bytes, allowed_nodes=allowed_nodes, proc=proc)
    native_after = _native(pid, expected_start_ticks, artifact.native_sha256, proc)
    if (_boot_id(proc) != expected_boot_id or native_before != native_after or
            worker.get("boot_id") != expected_boot_id or worker.get("owner") != native_before["owner"] or (
            vma is not None and vma.get("owner") != native_before["owner"])):
        raise ValueError("live process or native identity changed during observation")
    return {
        "format": "rove4k-live-runtime-observation-v1", "profile": profile,
        "family": artifact.family, "artifact_id": artifact.id,
        "candidate_set_sha256": candidate_digest,
        "candidate_whole_sha256": artifact.sha256,
        "candidate_evidence": row["evidence"],
        "native": native_before, "workers": worker, "address_range": vma,
        "scope": "sequential read-only samples; executable continuity and simultaneous placement are unproved",
        "claims": {"native_file_identity_observed": proc == Path("/proc"),
                   "wrapper_execution_verified": False,
                   "executable_continuity_verified": False,
                   "worker_vma_simultaneity_verified": False,
                   "host_pid_namespace_binding_verified": False,
                   "selected_worker_set_complete": False,
                   "search_causality_verified": False,
                   "range_is_tt_verified": False,
                   "tt_only_residency_verified": False,
                   "effective_numa_policy_verified": False,
                   "numa_remote_access_verified": False,
                   "actual_memory_reservation_verified": False,
                   "scored_game_admitted": False},
    }


def _ids(value):
    """Accept explicit IDs only; never infer worker identity from task count."""
    pieces = value.split(",")
    if not pieces or any(not piece.isdecimal() or len(piece) > 10 for piece in pieces):
        raise argparse.ArgumentTypeError("comma-separated nonnegative integer IDs required")
    values = [int(piece) for piece in pieces]
    if len(values) > 4096 or len(set(values)) != len(values):
        raise argparse.ArgumentTypeError("bounded unique IDs required")
    return values


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--candidates-sha256", required=True)
    parser.add_argument("--profile", choices=("test-p16", "test-p192"), required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--start-ticks", type=int, required=True)
    parser.add_argument("--boot-id", required=True)
    parser.add_argument("--pgid", type=int, required=True)
    parser.add_argument("--session", type=int, required=True)
    parser.add_argument("--worker-tids", type=_ids, required=True)
    parser.add_argument("--cpus", type=_ids, required=True)
    parser.add_argument("--nodes", type=_ids, required=True)
    parser.add_argument("--sample-seconds", type=float, default=0.1)
    parser.add_argument("--address", type=lambda value: int(value, 0), default=None,
                        help="optional caller-supplied address; TT identity is not proved")
    args = parser.parse_args(argv)
    result = observe_candidate(candidate_path=args.candidates, candidate_sha256=args.candidates_sha256,
                               profile=args.profile, artifact_id=args.artifact_id, pid=args.pid,
                               expected_start_ticks=args.start_ticks, expected_boot_id=args.boot_id,
                               expected_pgid=args.pgid, expected_session=args.session, worker_tids=args.worker_tids,
                               cpu_ids=args.cpus, allowed_nodes=args.nodes,
                               sample_seconds=args.sample_seconds, address=args.address)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
