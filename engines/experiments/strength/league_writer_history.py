"""Pure league writer history v2: complete replay, not execution authority.

The caller must independently authenticate the genesis, complete record set,
head, storage, writer and clock. A matching self-hash proves none of these.
No operation here grants GO, EC2 launch, takeover or termination. In
particular, ``budget_observed`` carries untrusted observations only.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re


SCHEMA = "rove4k-league-writer-history-v2"
_MAX = 2**63 - 2
_CAP = 120_000_000
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}")
_SHA = re.compile(r"[0-9a-f]{64}")
_HEAD_KEYS = {"schema", "campaign", "generation", "epoch", "revision", "owner", "mode",
              "budget_head", "budget_upper_micros", "history_sha256"}
_EVENT_KEYS = {"schema", "campaign", "generation", "revision", "epoch_before", "owner_before",
               "previous_sha256", "kind", "payload", "sha256"}
_INTENT_KEYS = {"attempt_id", "subject_id", "intent_kind", "job_sha256", "host_sha256",
                "request_sha256", "not_before_utc_ms", "expires_utc_ms"}


def _id(value):
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ValueError("invalid identifier")
    return value


def _sha(value):
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ValueError("lowercase SHA-256 required")
    return value


def _number(value, label):
    if type(value) is not int or not 0 <= value <= _MAX:
        raise ValueError(label + " must be a bounded nonnegative integer")
    return value


def _hash(domain, value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    return hashlib.sha256(domain + raw).hexdigest()


def genesis(campaign, generation, owner, budget_head, budget_upper_micros):
    """Create a deterministic untrusted root; callers must authenticate it."""
    _id(campaign)
    if not campaign.startswith("league-"):
        raise ValueError("league campaign namespace required")
    _sha(generation)
    _sha(owner)
    _sha(budget_head)
    amount = _number(budget_upper_micros, "budget")
    root = {"schema": SCHEMA, "campaign": campaign, "generation": generation,
            "epoch": 0, "revision": 0, "owner": owner,
            "mode": "draining" if amount >= _CAP else "active",
            "budget_head": budget_head, "budget_upper_micros": amount}
    return {**root, "history_sha256": _hash(b"rove4k-league-genesis-v2\0", root)}


def _root(value):
    if not isinstance(value, dict) or set(value) != _HEAD_KEYS:
        raise ValueError("invalid genesis fields")
    _number(value["epoch"], "genesis epoch")
    _number(value["revision"], "genesis revision")
    _sha(value["history_sha256"])
    expected = genesis(value["campaign"], value["generation"], value["owner"],
                       value["budget_head"], value["budget_upper_micros"])
    if value != expected:
        raise ValueError("genesis is not canonical")
    return expected


def _apply(head, kind, payload, attempts, subjects):
    if not isinstance(payload, dict):
        raise ValueError("event payload must be an object")
    new = dict(head)
    if kind == "diagnostic":
        if head["mode"] != "active" or set(payload) != _INTENT_KEYS:
            raise ValueError("invalid diagnostic intent or draining head")
        attempt, subject = _id(payload["attempt_id"]), _id(payload["subject_id"])
        intent = payload["intent_kind"]
        if intent not in ("go", "launch"):
            raise ValueError("unknown diagnostic intent kind")
        for key in ("job_sha256", "host_sha256", "request_sha256"):
            _sha(payload[key])
        start = _number(payload["not_before_utc_ms"], "window start")
        end = _number(payload["expires_utc_ms"], "window end")
        if not 0 < end - start <= 60_000:
            raise ValueError("intent window must be positive and at most 60 seconds")
        if attempt in attempts or (intent, subject) in subjects:
            raise ValueError("attempt or action/subject already exists")
        attempts.add(attempt)
        subjects.add((intent, subject))
    elif kind == "budget_observed":
        if set(payload) != {"budget_head", "budget_upper_micros", "evidence_sha256"}:
            raise ValueError("invalid budget observation")
        new["budget_head"] = _sha(payload["budget_head"])
        _sha(payload["evidence_sha256"])
        amount = _number(payload["budget_upper_micros"], "budget")
        if amount < head["budget_upper_micros"]:
            raise ValueError("diagnostic budget cannot decrease without an independent correction protocol")
        new["budget_upper_micros"] = amount
        if amount >= _CAP:
            new["mode"] = "draining"
    elif kind == "drain":
        if head["mode"] != "active" or set(payload) != {"reason"} or payload["reason"] not in ("budget", "fault", "manual"):
            raise ValueError("invalid drain transition")
        new["mode"] = "draining"
    elif kind == "handoff":
        if head["mode"] != "draining" or set(payload) != {"new_owner"}:
            raise ValueError("handoff requires a draining head")
        owner = _sha(payload["new_owner"])
        if owner == head["owner"] or head["epoch"] >= _MAX:
            raise ValueError("handoff owner or epoch differs")
        new["owner"] = owner
        new["epoch"] += 1
    else:
        raise ValueError("unknown writer history event")
    if head["revision"] >= _MAX:
        raise ValueError("revision overflow")
    new["revision"] += 1
    return new


def _replay(root, events, expected_head):
    head = _root(root)
    if not isinstance(events, list) or len(events) > 1_000_000:
        raise ValueError("history must be a bounded complete event list")
    attempts, subjects = set(), set()
    for event in events:
        if not isinstance(event, dict) or set(event) != _EVENT_KEYS:
            raise ValueError("invalid event fields")
        _number(event["revision"], "event revision")
        _number(event["epoch_before"], "event epoch")
        _sha(event["sha256"])
        expected = {"schema": SCHEMA, "campaign": head["campaign"], "generation": head["generation"],
                    "revision": head["revision"] + 1, "epoch_before": head["epoch"],
                    "owner_before": head["owner"], "previous_sha256": head["history_sha256"]}
        if any(event.get(key) != value for key, value in expected.items()):
            raise ValueError("event identity, order, owner or previous hash differs")
        core = {key: event[key] for key in _EVENT_KEYS if key != "sha256"}
        if event["sha256"] != _hash(b"rove4k-league-event-v2\0", core):
            raise ValueError("event digest differs")
        head = _apply(head, event["kind"], event["payload"], attempts, subjects)
        head["history_sha256"] = event["sha256"]
    if not isinstance(expected_head, dict) or set(expected_head) != _HEAD_KEYS:
        raise ValueError("invalid expected head")
    _number(expected_head["epoch"], "expected epoch")
    _number(expected_head["revision"], "expected revision")
    _number(expected_head["budget_upper_micros"], "expected budget")
    _sha(expected_head["history_sha256"])
    if head != expected_head:
        raise ValueError("complete history does not match expected head")
    return head, attempts, subjects


def replay(genesis_head, events, expected_head):
    """Replay a supplied complete history; this does not authenticate it."""
    return copy.deepcopy(_replay(genesis_head, events, expected_head)[0])


def append(genesis_head, events, expected_head, kind, payload):
    """Return the next HEAD/event; no storage write or authorization occurs."""
    head, attempts, subjects = _replay(genesis_head, events, expected_head)
    payload = copy.deepcopy(payload)
    new_head = _apply(head, kind, payload, attempts, subjects)
    event = {"schema": SCHEMA, "campaign": head["campaign"], "generation": head["generation"],
             "revision": new_head["revision"], "epoch_before": head["epoch"],
             "owner_before": head["owner"], "previous_sha256": head["history_sha256"],
             "kind": kind, "payload": payload}
    event["sha256"] = _hash(b"rove4k-league-event-v2\0", event)
    new_head["history_sha256"] = event["sha256"]
    return copy.deepcopy(new_head), copy.deepcopy(event)
