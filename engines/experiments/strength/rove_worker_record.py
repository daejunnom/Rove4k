"""Check recorded Rove worker observations without authenticating their origin.

This checks the cold/warm rows in an independently SHA-pinned lifecycle record.
It never upgrades a report to host, TT, SMT or score qualification.
"""

import hashlib
import json
import re


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _digest(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def inspect_worker_records(raw, *, expected_sha256, expected_artifact,
                           expected_source_sha256, expected_candidate_sha256):
    """Inspect two recorded search sessions; external provenance is not established.

    All expected identities are independent caller inputs, not values copied from
    the report.  A true consistency result is only a property of recorded fields.
    """
    if (type(raw) is not bytes or not _digest(expected_sha256) or
            hashlib.sha256(raw).hexdigest() != expected_sha256):
        raise ValueError("lifecycle record SHA-256 mismatch")
    if (not _digest(expected_source_sha256) or not _digest(expected_candidate_sha256) or
            type(expected_artifact) is not dict):
        raise ValueError("independent artifact, source and candidate identities required")
    try:
        report = json.loads(raw, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid lifecycle JSON") from exc
    if type(report) is not dict or report.get("format") != "rove4k-owned-lifecycle-v1":
        raise ValueError("unexpected lifecycle format")
    if (report.get("artifact") != expected_artifact or
            report.get("source_sha256") != expected_source_sha256 or
            report.get("candidate_set_sha256") != expected_candidate_sha256):
        raise ValueError("independent identity mismatch")
    profile = report.get("profile")
    expected_workers = {"test-p16": 16, "test-p192": 192}.get(profile)
    if expected_workers is None or expected_artifact.get("profile") != profile:
        raise ValueError("unsupported or mismatched profile")
    if expected_artifact.get("workers") != expected_workers:
        raise ValueError("artifact worker count differs from profile")
    slot = report.get("slot")
    cpus = slot.get("cpus") if type(slot) is dict else None
    if (type(cpus) is not list or len(cpus) != expected_workers or
            any(not _integer(cpu) for cpu in cpus) or cpus != sorted(set(cpus))):
        raise ValueError("invalid recorded CPU slot")
    sessions = report.get("sessions")
    if type(sessions) is not list:
        raise ValueError("session list missing")
    searches = {}
    process_keys = set()
    for session in sessions:
        if type(session) is not dict:
            raise ValueError("invalid session")
        label = session.get("label")
        if label not in ("cold", "warm"):
            continue
        if label in searches or session.get("complete") is not True:
            raise ValueError("search session incomplete or duplicated")
        owner = session.get("owner_identity")
        if type(owner) is not dict:
            raise ValueError("owner identity missing")
        pid, started = owner.get("pid"), owner.get("start_ticks")
        if (not _integer(pid, 1) or not _integer(started, 1) or
                not _integer(owner.get("pgid"), 1) or not _integer(owner.get("session"), 1) or
                owner.get("pgid") != pid or owner.get("session") != pid or
                (pid, started) in process_keys):
            raise ValueError("invalid or reused owner identity")
        process_keys.add((pid, started))
        search = session.get("search")
        if type(search) is not dict or search.get("label") != label:
            raise ValueError("search label mismatch")
        workers = search.get("worker_ids")
        positive = search.get("positive_cpu_worker_ids")
        if (type(workers) is not list or len(workers) != expected_workers or
                any(not _integer(tid, 1) or tid == pid for tid in workers) or
                workers != sorted(set(workers)) or type(positive) is not list or
                any(not _integer(tid, 1) for tid in positive) or positive != workers or
                search.get("worker_affinity_evidence_complete") is not True):
            raise ValueError("incomplete worker set or progress record")
        observations = search.get("worker_affinity_evidence")
        if type(observations) is not list or len(observations) != expected_workers:
            raise ValueError("worker affinity records missing")
        recorded_ids = []
        for observation in observations:
            if type(observation) is not dict:
                raise ValueError("invalid worker observation")
            tid, start = observation.get("tid"), observation.get("start_ticks")
            first, last = observation.get("cpu_ticks_first"), observation.get("cpu_ticks_last")
            if (not _integer(tid, 1) or not _integer(start, 1) or
                    not _integer(first) or not _integer(last) or last <= first or
                    observation.get("cpus") != cpus):
                raise ValueError("worker identity, affinity or CPU progress mismatch")
            recorded_ids.append(tid)
        if recorded_ids != workers:
            raise ValueError("worker observations differ from worker IDs")
        searches[label] = {"pid": pid, "owner_start_ticks": started,
                           "workers": len(workers)}
    if set(searches) != {"cold", "warm"}:
        raise ValueError("both independently owned search sessions are required")
    return {"recorded_searches_consistent": True, "sessions": searches,
            "lifecycle_sha256": expected_sha256, "host_authenticated": False,
            "source_authenticated": False, "complete_worker_set_proven": False,
            "tt_provenance_proven": False, "smt_qualification": False,
            "score_authorized": False}
