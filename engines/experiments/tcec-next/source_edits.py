"""Pure transport of exact source edits through the existing include cleanup.

The caller supplies authenticated projection/dependency owners and admitted
sources. This module performs no reads, builds, admission or recipe selection.
"""
from hashlib import sha256
import json


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def lift_source_edits(before, final, candidate, proof, old_dependency, *, projection, dependencies):
    """Commute final-source edits using actual dependency coordinates/inverses."""
    replay, canonical_dependency = dependencies.transform_source(before)
    require(replay == final and canonical(canonical_dependency) == canonical(old_dependency)
            and dependencies.restore_source(final, old_dependency) == before,
            "canonical original dependency relation differs")
    spans = old_dependency["spans"]
    require(type(spans) is list and len(spans) <= 1, "finite existing dependency cleanup required")
    offset = removed = None
    if spans:
        span = spans[0]
        offset, removed = span["offset"], span["before"].encode("ascii")
        require(type(offset) is int and 0 <= offset <= len(final) and removed == dependencies.DIRECTIVE
                and span["after"] == "" and before[:offset] == final[:offset]
                and before[offset:offset + len(removed)] == removed
                and before[offset + len(removed):] == final[offset:],
                "one exact unchanged include deletion required")
    require(projection._inverse_edits(candidate, proof["edits"]) == final,
            "actual final-source inverse differs before lifting")
    lifted = []
    for row in proof["edits"]:
        at, length = row["input_begin"], len(row["before"].encode("ascii"))
        require(type(at) is int and length > 0, "typed nonempty source edit required")
        if spans:
            require(at >= offset or at + length <= offset, "source edit crosses the removed include")
            at += len(removed) if at >= offset else 0
        lifted.append(dict(input_begin=at, before=row["before"], after=row["after"],
                           role=row["role"], component=row["component"]))
    pre_candidate, rows, gaps = projection._splice(before, lifted)
    require(projection._inverse_edits(pre_candidate, rows) == before,
            "lifted complete pre-cleanup inverse differs")
    cleaned, dependency_proof = dependencies.transform_source(pre_candidate)
    require(cleaned == candidate and dependencies.restore_source(cleaned, dependency_proof) == pre_candidate,
            "source/include projections do not commute")
    return pre_candidate, dependency_proof, dict(
        original_before=pin(before), original_final=pin(final), candidate_before=pin(pre_candidate),
        candidate_final=pin(candidate), original_dependency=old_dependency,
        lifted_edits=rows, protected_gaps=gaps, lifted_full_inverse=True,
        canonical_cleanup_last=True, exact_commuting_output=True)
