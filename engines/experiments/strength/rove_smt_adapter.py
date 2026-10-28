"""Fail-closed bridge from owned observations to the SMT diagnostic inspector.

This module never manufactures qualification, worker, TT or host observations.
Four independently supplied SHA-256 pins identify bytes, not their origin. A
successful registry inspection only establishes consistency of the records;
it does not authenticate the host, source-to-native build, or TT semantics and
does not authorize scored games, performance claims, or release. The separate
file reads also do not constitute an atomic filesystem snapshot.
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    from . import diagnostic_candidates as diagnostic, registry
except ImportError:
    import diagnostic_candidates as diagnostic
    import registry


def _pinned(path, sha, limit, expected_name=None):
    # Check forbidden components before registry's filesystem operations.
    path = diagnostic._safe_input_path(path)
    return registry._read_inspection_file(path, sha, expected_name or path.name, limit)[1]


def _object(raw):
    value = json.loads(raw, object_pairs_hook=registry._unique_json_fields,
                       parse_constant=registry._reject_nonfinite_json,
                       parse_float=registry._finite_json_float)
    if type(value) is not dict:
        raise ValueError("observation must be an object")
    return value


def _incomplete_lifecycle(record, artifact):
    reasons = []
    if record.get("artifact") != artifact.identity() or record.get("profile") != artifact.profile:
        reasons.append("lifecycle artifact or profile differs from the requested artifact")
    if record.get("complete") is not True:
        reasons.append("the four-session lifecycle did not complete")
    rows = record.get("sessions")
    labels = ("cold", "warm", "active-quit", "active-eof")
    if type(rows) is not list or len(rows) != 4 or [r.get("label") if type(r) is dict else None for r in rows] != list(labels):
        reasons.append("the four ordered owned sessions are missing")
    else:
        for row in rows:
            if row.get("complete") is not True:
                reasons.append("session " + row["label"] + " did not complete")
            cleanup = row.get("cleanup")
            if (type(cleanup) is not dict or cleanup.get("owned_group_absent") is not True or
                    cleanup.get("readers_joined") is not True or cleanup.get("forced_cleanup") or cleanup.get("errors")):
                reasons.append("session " + row["label"] + " did not establish normal owned-group cleanup")
    claims = record.get("claims")
    if type(claims) is not dict:
        claims = {}
    for key, why in (("complete_worker_set", "complete worker provenance is not established"),
                     ("tt_address_provenance", "TT address meaning and provenance are not established"),
                     ("tt_only_residency", "TT-only NUMA residency is not established"),
                     ("loaded_driver_identity_proven", "loaded driver identity is not established"),
                     ("executable_continuity_proven", "executable continuity is not established"),
                     ("smt_qualification", "lifecycle is not an SMT qualification")):
        if claims.get(key) is not True:
            reasons.append(why)
    # Lifecycle and SMT schemas differ, even if a future lifecycle sets claims.
    reasons.append("no separately bound SMT observation was provided")
    return reasons


def inspect_owned_observation(artifact, observation_path, observation_sha256, *,
                              qualification_path=None, qualification_sha256=None,
                              runtime_path=None, runtime_sha256=None,
                              source_path=None, source_sha256=None):
    """Inspect independently pinned files without creating or upgrading evidence.

    Lifecycle records return an incomplete result. Full SMT records require a
    sibling qualification and independent runtime/source files and pins, and
    are passed unchanged to the registry's actual consistency validator.
    """
    if (artifact.profile not in ("test-p16", "test-p192") or
            artifact.family not in ("A", "B", "C", "E", "F") or
            artifact.purpose != "test" or artifact.full is not True):
        raise ValueError("Rove P16/P192 TEST artifact required")
    record = _object(_pinned(observation_path, observation_sha256, 16 << 20))
    result = {"diagnostic_eligible": False, "score_authorized": False, "release_authorized": False,
              "performance_authorized": False, "host_origin_authenticated": False,
              "source_origin_authenticated": False, "tt_symbol_origin_authenticated": False,
              "digest_authenticates_origin": False}
    if record.get("format") == "rove4k-owned-lifecycle-v1":
        result.update(status="incomplete", reasons=_incomplete_lifecycle(record, artifact))
        return result
    if record.get("format") != "rove4k-owned-smt-observation-v1":
        raise ValueError("unknown owned observation format")
    inputs = (qualification_path, qualification_sha256, runtime_path, runtime_sha256, source_path, source_sha256)
    if any(value is None for value in inputs):
        result.update(status="incomplete", reasons=["independent qualification, runtime and source paths and SHA-256 pins are required"])
        return result
    _pinned(qualification_path, qualification_sha256, 64 << 20, "qualification.json")
    _pinned(runtime_path, runtime_sha256, 64 << 20)
    _pinned(source_path, source_sha256, 64 << 20)
    inspection = registry.inspect_league_test_receipt(
        artifact, Path(qualification_path), qualification_sha256,
        smt_evidence_path=Path(observation_path), smt_evidence_sha256=observation_sha256,
        expected_runtime_sha256=runtime_sha256, expected_source_sha256=source_sha256)
    if (inspection.get("diagnostic_eligible") is not True or inspection.get("score_authorized") is not False or
            inspection.get("smt_observations_consistent") is not True or
            inspection.get("host_origin_authenticated") is not False or
            inspection.get("source_origin_authenticated") is not False or
            inspection.get("tt_symbol_origin_authenticated") is not False):
        raise ValueError("registry did not return a diagnostic-only SMT consistency result")
    result.update(status="consistent", diagnostic_eligible=True, reasons=[], registry_inspection=inspection)
    return result
