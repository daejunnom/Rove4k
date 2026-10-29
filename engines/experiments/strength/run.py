#!/usr/bin/env python3
"""Freeze and execute a TEST-only colour-pair league using the pinned runner.

This controller does not create EC2 instances. The AWS lifecycle consumer owns
launch/termination and supplies an already verified live lease and publisher.
Every score-producing CLI path validates the exact artifact qualifications.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import gc
import hashlib
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import queue
import re
import shutil
import sys
import threading
import time
import uuid

# When invoked as a script or with -m, Wave imports the controller by its
# canonical name. Alias this exact module so the strict owner type is not
# duplicated by a second import.
if __name__ == "__main__":
    alias = __spec__.name if __spec__ is not None and __spec__.name != "__main__" else "run"
    existing = sys.modules.get(alias)
    if existing is not None and existing is not sys.modules[__name__]:
        raise RuntimeError("conflicting controller module prevents intent owner identity")
    sys.modules[alias] = sys.modules[__name__]

try:
    from . import budget, collect, durability, fastchess, ledger, placement, registry, topology
except ImportError:
    import budget, collect, durability, fastchess, ledger, placement, registry, topology

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ID = ledger.valid_id
SHA = re.compile(r"^[a-f0-9]{64}$")
TEST_PROFILES = ("test-p4", "test-p28", "test-p16", "test-p192")
BROAD_FOR_HIGH = {"test-p28": "test-p4", "test-p192": "test-p16"}


class CooperativeGcTracker:
    """Track only explicit, controller-owned cooperative GC interventions.

    The counters are process-wide, so an intervention overlaps every active
    game in this controller process. Automatic Python GC and activity in other
    processes are outside this observation scope. A missing scope never proves
    that a game was free of intervention.
    """
    def __init__(self, *, clock_ns=None, collector=None):
        self._clock_ns = clock_ns or time.monotonic_ns
        self._collector = collector or gc.collect
        self._lock = threading.Lock()
        self._requests = 0
        self._performed = 0
        self._inflight = 0
        self._scopes = {}

    def arm(self, key):
        """Capture a baseline before the corresponding runner is spawned."""
        with self._lock:
            if key in self._scopes:
                raise ValueError("cooperative GC scope is already armed")
            now = self._clock_ns()
            if type(now) is not int or now < 0:
                raise ValueError("invalid cooperative GC monotonic clock")
            # A request already in flight overlaps this game even when neither
            # absolute counter changes before scope close.
            self._scopes[key] = {"scope_start_ns": now,
                                 "request_count": self._requests,
                                 "performed_count": self._performed,
                                 "active_count": self._inflight}

    def collect(self):
        """Request GC in this process only, without any memory threshold."""
        with self._lock:
            self._requests += 1
            self._inflight += 1
        try:
            result = self._collector()
        except BaseException:
            with self._lock:
                self._inflight -= 1
            raise
        with self._lock:
            self._performed += 1
            self._inflight -= 1
        return result

    def open_record(self, key, campaign, pair, game, attempt, identity):
        with self._lock:
            scope = self._scopes.get(key)
            if scope is None or "identity" in scope:
                raise ValueError("pre-spawn cooperative GC baseline required")
            binding = dict(identity)
            binding["scope_start_ns"] = scope["scope_start_ns"]
            scope_id = ledger.cooperative_gc_scope_id(campaign, pair, game, attempt, binding)
            scope["identity"] = binding
            scope["scope_id"] = scope_id
            return {"format": "rove4k-cooperative-gc-v1",
                    "coverage_scope": "owned-controller-explicit-gc",
                    "scope_id": scope_id, **binding,
                    "request_count": scope["request_count"],
                    "performed_count": scope["performed_count"],
                    "active_count": scope["active_count"],
                    "coverage_complete": True}

    def close_record(self, key, result_data, *, identity_confirmed):
        with self._lock:
            scope = self._scopes.pop(key, None)
            if scope is None or "identity" not in scope:
                raise ValueError("original cooperative GC scope is unavailable")
            now = self._clock_ns()
            if type(now) is not int or now < scope["scope_start_ns"]:
                raise ValueError("cooperative GC monotonic clock regressed")
            return {"format": "rove4k-cooperative-gc-v1",
                    "coverage_scope": "owned-controller-explicit-gc",
                    "scope_id": scope["scope_id"], **scope["identity"],
                    "request_count": self._requests, "performed_count": self._performed,
                    "active_count": self._inflight,
                    "coverage_complete": identity_confirmed is True,
                    "scope_end_ns": now, "result_sha256": ledger.digest(result_data)}

    def forget(self, key):
        with self._lock:
            self._scopes.pop(key, None)


# Multiple controllers in this Python process must observe one another's
# explicit requests; separate processes require separate host evidence.
_COOPERATIVE_GC_TRACKER = CooperativeGcTracker()


def attempt_identity(campaign, pair, game, attempt, launch_id):
    """Bounded non-secret identity for this one allocated launch attempt."""
    if (any(not isinstance(value, str) or not value for value in (campaign, pair, game, launch_id))
            or type(attempt) is not int or attempt < 0):
        raise ValueError("explicit campaign, pair, game and launch attempt required")
    return hashlib.sha256(ledger.canonical({"campaign": campaign, "pair": pair, "game": game,
                                            "attempt": attempt, "launch_id": launch_id})).hexdigest()


class IntentJournalOwner:
    """Fsync pre-send intents away from the Wave selector thread.

    This records only a local journal, not global authority or replicated
    recovery. Its owner must register the sidecar with the main journal before
    a wave starts and preserve both files on every recovery path.
    """
    def __init__(self, path, campaign, instance_id, *, queue_size=64):
        if (os.name != "posix" or not isinstance(instance_id, str) or not instance_id
                or type(queue_size) is not int or not 1 <= queue_size <= 256):
            raise ValueError("bounded POSIX intent owner and instance identity required")
        self.path = ledger.external(path)
        self.campaign, self.instance_id = ledger.valid_id(campaign), instance_id
        self.boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        self.journal = ledger.Journal(self.path, self.campaign)
        if self.journal.rows:
            self.journal.close()
            raise ValueError("existing intent journal requires independent recovery before reuse")
        # Persist the sidecar directory entry before its registration is used.
        try:
            fd = os.open(str(self.path.parent), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except BaseException:
            self.journal.close()
            raise
        self._requests, self._responses = queue.Queue(queue_size), queue.Queue(queue_size)
        self._seen, self._tracked, self._failure, self._closed, self._registration = set(), set(), None, False, None
        self._thread = threading.Thread(target=self._worker, name="rove-intent-journal", daemon=True)
        self._thread.start()

    def bind_registration(self, main_journal, row):
        """Bind the already fsynced main-journal marker before a wave starts."""
        if self._registration is not None or main_journal.campaign != self.campaign:
            raise ValueError("intent owner registration already exists or campaign differs")
        seq = row.get("seq") if isinstance(row, dict) else None
        data = row.get("data") if isinstance(row, dict) else None
        if (type(seq) is not int or seq < 0 or seq >= len(main_journal.rows)
                or ledger.canonical(main_journal.rows[seq]) != ledger.canonical(row)
                or row.get("event") != "campaign.intent_journal" or row.get("campaign") != self.campaign
                or ledger.digest({name: value for name, value in row.items() if name != "sha256"}) != row.get("sha256")
                or not isinstance(data, dict) or data.get("path") != str(self.path)
                or data.get("instance_id") != self.instance_id or data.get("boot_id") != self.boot_id
                or type(data.get("device")) is not int or type(data.get("inode")) is not int
                or (data.get("device"), data.get("inode")) != self.journal.identity):
            raise ValueError("durable main-journal registration differs")
        self._registration = (main_journal, seq, row["sha256"], ledger.canonical(row))

    def registered(self):
        """Check in-memory ownership only; no file or network I/O here."""
        if self._registration is None or self._closed or self._failure is not None:
            return False
        journal, seq, sha, canonical = self._registration
        return (not journal.file.closed and seq < len(journal.rows)
                and journal.rows[seq].get("sha256") == sha
                and ledger.canonical(journal.rows[seq]) == canonical
                and journal.rows[seq].get("event") == "campaign.intent_journal")

    def track_wave(self, jobs):
        """Track every local gate before spawn; this performs no I/O."""
        identities = [job.identity for job in jobs]
        if (not self.registered() or len(set(identities)) != len(identities)
                or self._tracked.intersection(identities)):
            raise ValueError("registered intent owner needs distinct wave identities")
        self._tracked.update(identities)

    def confirm(self, decision, job, observation):
        """Check the worker's completed fsync receipt without filesystem I/O."""
        if not self.registered() or type(decision.journal_seq) is not int:
            return False
        seq = decision.journal_seq
        if seq < 0 or seq >= len(self.journal.rows):
            return False
        row = self.journal.rows[seq]
        try:
            from .wave import intent_payload
        except ImportError:
            from wave import intent_payload
        expected = intent_payload(job, observation, boot_id=self.boot_id)
        return (row.get("event") == "game.release_intent" and row.get("sha256") == decision.journal_sha256
                and ledger.digest({name: value for name, value in row.items() if name != "sha256"}) == decision.journal_sha256
                and row.get("campaign") == self.campaign and row.get("pair") == job.start_job.get("pair")
                and row.get("game") == job.start_job.get("game") and row.get("attempt") == job.start_job.get("attempt")
                and row.get("data", {}).get("instance_id") == self.instance_id
                and ledger.canonical(row.get("data", {}).get("intent")) == ledger.canonical(expected)
                and ledger.canonical(decision.intent) == ledger.canonical(expected))

    def request(self, job, observation):
        """Enqueue only; no file, network or fsync in the caller."""
        if self._closed or self._failure is not None or job.identity in self._seen or job.identity not in self._tracked:
            raise RuntimeError("intent owner is closed, failed or saw a duplicate job")
        if (job.start_job.get("campaign") != self.campaign or
                any(not isinstance(job.start_job.get(key), str) or not job.start_job[key] for key in ("pair", "game")) or
                type(job.start_job.get("attempt")) is not int or job.start_job["attempt"] < 0):
            raise ValueError("intent job identity differs from its owner")
        try:
            from .wave import intent_payload
        except ImportError:
            from wave import intent_payload
        payload = intent_payload(job, observation, boot_id=self.boot_id)
        if payload != observation.get("gate_intent_payload"):
            raise ValueError("intent request binding changed")
        request = (job.identity, payload, job.start_job["pair"], job.start_job["game"], job.start_job["attempt"])
        self._requests.put_nowait(request)
        self._seen.add(job.identity)

    def _worker(self):
        try:
            from .wave import AsyncIntentDecision
        except ImportError:
            from wave import AsyncIntentDecision
        while True:
            request = self._requests.get()
            if request is None:
                return
            identity, payload, pair, game, attempt = request
            try:
                row = self.journal.append("game.release_intent", {"intent": payload, "instance_id": self.instance_id},
                                          pair=pair, game=game, attempt=attempt)
                decision = AsyncIntentDecision(identity, payload, row["seq"], row["sha256"])
                self._responses.put_nowait(decision)
            except BaseException as error:
                # A failed write/fsync or lost response may have committed; do
                # not retry or issue a receipt. The journal is quarantined.
                self._failure = error
                return

    def poll(self):
        if self._failure is not None:
            raise RuntimeError("intent journal write or receipt is uncertain") from self._failure
        values = []
        while True:
            try:
                values.append(self._responses.get_nowait())
            except queue.Empty:
                return values

    def close(self, *, timeout=5):
        """Close outside the Wave loop; preserve a live blocked writer."""
        self._closed = True
        if self._thread.is_alive():
            self._requests.put_nowait(None)
            self._thread.join(timeout)
        if self._thread.is_alive():
            raise RuntimeError("intent writer remains live; preserve its journal owner")
        self.journal.close()


def registered_intent_rows(rows, out, campaign, *, allow_open=False):
    """Read a registered local sidecar, rejecting loss or ambiguous owners."""
    markers = [row for row in rows if row.get("event") == "campaign.intent_journal"]
    path = Path(out) / "release-intents.jsonl"
    if markers:
        if (len(markers) != 1 or not isinstance(markers[0].get("data"), dict)
                or markers[0]["data"].get("path") != str(path) or not path.is_file()):
            raise ValueError("registered intent journal missing or changed; preserve for recovery")
        stat = ledger.external(path).stat()
        if (type(markers[0]["data"].get("device")) is not int or type(markers[0]["data"].get("inode")) is not int
                or (stat.st_dev, stat.st_ino) != (markers[0]["data"].get("device"), markers[0]["data"].get("inode"))):
            raise ValueError("registered intent journal identity changed; preserve for recovery")
        intents = ledger.read_journal(path, campaign)
        closed = [row for row in rows if row.get("event") == "campaign.intent_journal_closed"]
        if not closed:
            if allow_open:
                return intents
            raise ValueError("open intent journal requires durable owner recovery before resume")
        data = closed[0].get("data") if len(closed) == 1 else None
        head = intents[-1]["sha256"] if intents else "0" * 64
        if (not isinstance(data, dict) or type(closed[0].get("seq")) is not int
                or type(markers[0].get("seq")) is not int or closed[0]["seq"] <= markers[0]["seq"]
                or data.get("path") != str(path) or type(data.get("count")) is not int
                or data.get("count") != len(intents) or data.get("head_sha256") != head
                or type(data.get("device")) is not int or type(data.get("inode")) is not int
                or data.get("device") != stat.st_dev or data.get("inode") != stat.st_ino):
            raise ValueError("closed intent journal differs; preserve for recovery")
        for row in rows:
            event_data = row.get("data")
            observation = event_data.get("observation") if isinstance(event_data, dict) else None
            uses_intent = (row.get("event") == "game.released" and isinstance(event_data, dict)
                           and event_data.get("gate_intent_required") is True) or (
                row.get("event") == "game.gate_received" and isinstance(observation, dict)
                and observation.get("gate_intent_required") is True)
            if uses_intent and (type(row.get("seq")) is not int or row["seq"] >= closed[0]["seq"]):
                raise ValueError("GO2 evidence after intent journal closure requires recovery")
        return intents
    if any(row.get("event") == "campaign.intent_journal_closed" for row in rows):
        raise ValueError("closed intent journal lacks registration")
    if path.exists() or path.is_symlink():
        raise ValueError("unregistered intent journal requires recovery before resume")
    return ()


def league_placement(snapshot, profile):
    """Derive TEST slots and controller mask; live placement is separate evidence."""
    if profile == "test-p192":
        slot = topology.plan_p192_slot(snapshot, policy="default")
        # The whole instance is shared; no independent controller core exists.
        return (slot,), list(slot.cpus)
    if profile == "test-p16":
        slots = topology.plan_slots(snapshot, 8, 16, reserve_physical=8, max_slots=11, policy="default")
        if len(slots) != 11:
            raise ValueError("P16 requires eleven complete node-local slots")
        by_id = {cpu.id: cpu for cpu in snapshot.cpus}
        for slot in slots:
            for key in slot.physical_cores:
                members = {cpu for cpu in slot.cpus if by_id[cpu].physical == key}
                if len(members) != 2 or any(set(by_id[cpu].siblings) != members for cpu in members):
                    raise ValueError("P16 requires complete mutually observed SMT siblings")
    elif profile in ("test-p4", "test-p28"):
        physical = 4 if profile == "test-p4" else 28
        slots = topology.plan_slots(snapshot, physical, physical, reserve_physical=8)
    else:
        raise ValueError("unknown TEST profile")
    used = {key for slot in slots for key in slot.physical_cores}
    unused = sorted({cpu.physical for cpu in snapshot.cpus if cpu.id in snapshot.allowed_cpus} - used)
    if profile == "test-p16":
        by_core = {}
        for cpu in snapshot.cpus:
            if cpu.id in snapshot.allowed_cpus and cpu.node in snapshot.allowed_nodes:
                by_core.setdefault(cpu.physical, []).append(cpu)
        def complete(key):
            rows = by_core.get(key, ())
            members = {cpu.id for cpu in rows}
            return (len(rows) == 2 and len({cpu.node for cpu in rows}) == 1 and
                    all(set(cpu.siblings) == members for cpu in rows))
        unused = [key for key in unused if complete(key)]
    controller_cores = set(unused[:8])
    if len(controller_cores) != 8:
        raise ValueError("eight whole physical controller cores were not reserved")
    controller_cpus = sorted(cpu.id for cpu in snapshot.cpus
                             if cpu.id in snapshot.allowed_cpus and cpu.physical in controller_cores)
    return slots, controller_cpus


def stage_profile_allowed(stage, profile):
    if profile not in TEST_PROFILES:
        return False
    if stage == "broad":
        return profile in BROAD_FOR_HIGH.values()
    if stage == "high":
        return profile in BROAD_FOR_HIGH
    return stage in ("update1", "update2")


def assert_no_unreconciled_releases(rows, intent_rows=()):
    # Reconciliation needs the durable global owner and is not yet implemented.
    # A locally settled process alone cannot prove no authorization committed.
    if any(row.get("event") in ("campaign.release_unreconciled", "campaign.game_evidence_unresolved") for row in rows):
        raise ValueError("unreconciled release or game evidence requires durable owner recovery before resume")
    # A controller may die after persisting a GO2 send but before persisting
    # its receipt (and hence before it can write an explicit quarantine row).
    # Do not infer reception from process exit or from the socket write alone.
    pending, seen, intents = {}, set(), {}
    previous, intent_campaign = "0" * 64, None
    for expected_seq, row in enumerate(intent_rows):
        if not isinstance(row, dict):
            raise ValueError("invalid intent journal requires durable owner recovery")
        claimed = row.get("sha256")
        unsigned = {name: value for name, value in row.items() if name != "sha256"}
        data = row.get("data")
        intent = data.get("intent") if isinstance(data, dict) else None
        job = intent.get("job") if isinstance(intent, dict) else None
        if (row.get("event") != "game.release_intent" or type(row.get("seq")) is not int or row.get("seq") != expected_seq
                or row.get("format") != "rove4k-campaign-v1" or row.get("previous_sha256") != previous
                or not isinstance(claimed, str) or not SHA.fullmatch(claimed) or ledger.digest(unsigned) != claimed
                or not isinstance(job, dict) or not isinstance(intent.get("identity"), str)
                or type(row.get("attempt")) is not int or type(job.get("attempt")) is not int
                or not isinstance(data.get("instance_id"), str) or not data["instance_id"]
                or any(row.get(name) != job.get(name) for name in ("pair", "game", "attempt"))):
            raise ValueError("invalid intent journal requires durable owner recovery")
        if intent_campaign is None:
            intent_campaign = row.get("campaign")
        if row.get("campaign") != intent_campaign or job.get("campaign") != intent_campaign:
            raise ValueError("intent journal campaign differs")
        previous = claimed
        key = (row.get("game"), row.get("attempt"), intent["identity"])
        if key in intents:
            raise ValueError("duplicate release intent requires durable owner recovery")
        intents[key] = row
    if intent_campaign is not None and any(row.get("campaign") != intent_campaign for row in rows):
        raise ValueError("main and intent journal campaigns differ")
    for row in rows:
        event, data = row.get("event"), row.get("data", {})
        if event == "game.released" and (not isinstance(data, dict) or
                type(data.get("gate_receipt_required", False)) is not bool):
            raise ValueError("invalid GO2 release requires durable owner recovery before resume")
        if event == "game.released" and data.get("gate_receipt_required") is True:
            binding = go2_local_binding(data)
            if any(row.get(name) != binding[name] for name in ("pair", "game", "attempt")):
                raise ValueError("GO2 release game identity differs")
            key = (row.get("game"), row.get("attempt"), binding["launch_id"])
            if key in seen:
                raise ValueError("duplicate GO2 release requires durable owner recovery before resume")
            if type(data.get("gate_intent_required", False)) is not bool:
                raise ValueError("invalid GO2 intent flag requires durable owner recovery")
            if key in intents and data.get("gate_intent_required") is not True:
                raise ValueError("GO2 release does not reference its durable pre-send intent")
            if data.get("gate_intent_required") is True:
                intent_row = intents.get(key)
                expected = {"identity": binding["launch_id"], "job": binding["ready"]["job"],
                            "ready": binding["ready"], "fence": binding["fence"], "receipt": binding["receipt"],
                            "pid": binding["pid"], "start_ticks": binding["start_ticks"], "boot_id": binding["boot_id"]}
                if (intent_row is None or ledger.canonical(intent_row["data"].get("intent")) != ledger.canonical(expected)
                        or intent_row["data"].get("instance_id") != binding["instance_id"]
                        or type(data.get("gate_intent_seq")) is not int
                        or data.get("gate_intent_seq") != intent_row["seq"]
                        or data.get("gate_intent_sha256") != intent_row["sha256"]):
                    raise ValueError("GO2 release lacks its durable pre-send intent")
            seen.add(key)
            pending[key] = binding
        elif event == "game.gate_received":
            if not isinstance(data, dict) or not isinstance(data.get("observation"), dict):
                raise ValueError("invalid GO2 receipt requires durable owner recovery before resume")
            binding = go2_local_binding(data["observation"], received=True)
            key = (row.get("game"), row.get("attempt"), binding["launch_id"])
            if (any(row.get(name) != binding[name] for name in ("pair", "game", "attempt")) or
                    key not in pending or pending[key] != binding or
                    data.get("launch_id") != binding["launch_id"] or
                    data.get("instance_id") != binding["instance_id"] or
                    data.get("boot_id") != binding["boot_id"]):
                raise ValueError("unmatched GO2 receipt requires durable owner recovery before resume")
            del pending[key]
            if key in intents:
                del intents[key]
    if pending:
        raise ValueError("unconfirmed GO2 receipt requires durable owner recovery before resume")
    if intents:
        raise ValueError("unsettled pre-send intent requires durable owner recovery before resume")


def go2_local_binding(observation, *, received=False):
    """Validate Wave's local match record; this is not remote authentication.

    The Wave parser compares the runner's JSON against the expected receipt,
    but does not retain its raw bytes. This binds that local match to the
    original job, process, fence and host boot without claiming UCI GO.
    """
    if not isinstance(observation, dict):
        raise ValueError("GO2 observation is not an object")
    launch = observation.get("identity")
    ready = observation.get("ready")
    job = ready.get("job") if isinstance(ready, dict) else None
    fence = observation.get("gate_fence")
    receipt = observation.get("gate_receipt_expected")
    if (not isinstance(launch, str) or not launch or not isinstance(job, dict) or
            not isinstance(fence, dict) or not isinstance(receipt, dict) or
            set(ready) != {"event", "job", "white_clock_ms", "black_clock_ms"} or
            ready.get("event") != "READY" or
            type(ready.get("white_clock_ms")) is not int or ready["white_clock_ms"] != 1803000 or
            type(ready.get("black_clock_ms")) is not int or ready["black_clock_ms"] != 1803000 or
            any(not isinstance(job.get(name), str) or not job[name] for name in ("pair", "game")) or
            type(job.get("attempt")) is not int or job["attempt"] < 0 or
            set(fence) != {"game_id", "fence_id", "job_sha256", "not_before_monotonic", "expires_monotonic"} or
            set(receipt) != {"event", "attempt_id", "fence_id", "job_sha256", "nonce"} or
            receipt.get("event") != "GO2_ACCEPTED" or
            not isinstance(receipt.get("attempt_id"), str) or not receipt["attempt_id"] or
            receipt["attempt_id"] != job.get("attempt_id") or
            not isinstance(receipt.get("fence_id"), str) or not receipt["fence_id"] or
            receipt["fence_id"] != fence.get("fence_id") or fence.get("game_id") != launch or
            not isinstance(receipt.get("nonce"), str) or not SHA.fullmatch(receipt["nonce"]) or
            not isinstance(receipt.get("job_sha256"), str) or not SHA.fullmatch(receipt["job_sha256"]) or
            receipt["job_sha256"] != fence.get("job_sha256") or
            receipt["job_sha256"] != observation.get("gate_fence_binding_sha256") or
            observation.get("gate_receipt_required") is not True or
            observation.get("gate_transport") != "sent" or observation.get("gate_authorized") is not True or
            observation.get("gate_authorization_unknown") is True or
            observation.get("gate_transport_observation_error") or
            observation.get("gate_release_event_error") or
            observation.get("gate_fence_send_time_uncertain") or
            type(observation.get("pid")) is not int or observation["pid"] <= 0 or
            type(observation.get("start_ticks")) is not int or observation["start_ticks"] < 0 or
            not isinstance(observation.get("instance_id"), str) or not observation["instance_id"] or
            not isinstance(observation.get("boot_id"), str) or not observation["boot_id"]):
        raise ValueError("GO2 local receipt binding differs")
    encoded = json.dumps({"identity": launch, "start_job": job}, sort_keys=True,
                         allow_nan=False, separators=(",", ":")).encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != receipt["job_sha256"]:
        raise ValueError("GO2 job binding differs")
    times = [fence.get("not_before_monotonic"), fence.get("expires_monotonic"),
             observation.get("gate_send_started_monotonic"), observation.get("released_monotonic"),
             observation.get("gate_receipt_deadline")]
    if (any(type(value) not in (int, float) or not math.isfinite(value) for value in times) or
            not 0 <= times[0] < times[1] or times[1] - times[0] > 60 or
            not times[0] <= times[2] <= times[3] < times[1] or
            not times[2] < times[4] <= times[1]):
        raise ValueError("GO2 local fence or send interval differs")
    if observation.get("gate_receipt_event_error"):
        raise ValueError("GO2 local receipt record failed")
    if not received and observation.get("gate_receipt") != "pending":
        raise ValueError("GO2 release did not precede its local receipt")
    if received and observation.get("gate_receipt") != "matched":
        raise ValueError("GO2 local receipt is not confirmed")
    if received:
        received_at = observation.get("gate_receipt_monotonic")
        if (type(received_at) not in (int, float) or not math.isfinite(received_at) or
                not times[3] <= received_at < times[4]):
            raise ValueError("GO2 local receipt is outside its window")
    return {"launch_id": launch, "instance_id": observation["instance_id"],
            "boot_id": observation["boot_id"], "pid": observation["pid"],
            "start_ticks": observation["start_ticks"], "pair": job["pair"],
            "game": job["game"], "attempt": job["attempt"], "ready": ready,
            "fence": fence, "receipt": receipt, "send_started": times[2],
            "sent_at": times[3], "receipt_deadline": times[4]}


def release_unresolved(observation):
    """A local child result cannot resolve a possibly committed release."""
    return bool(observation.get("gate_transport") == "uncertain" or
                observation.get("gate_authorization_unknown") is True or
                (observation.get("gate_intent_requested") is True and
                 (observation.get("gate_intent_resolved") is not True or
                  observation.get("gate_transport") != "sent" or observation.get("gate_receipt") != "matched")) or
                observation.get("gate_transport_observation_error") or
                observation.get("gate_release_event_error") or
                observation.get("gate_receipt_event_error") or
                (observation.get("gate_receipt_required", False) is not False and
                 (observation.get("gate_receipt_required") is not True or
                  observation.get("gate_receipt") != "matched")) or
                observation.get("gate_authorized") is True and observation.get("gate_transport") != "sent")


def score_evidence_unresolved(data, profile):
    if data.get("clock_tracking_complete") is not True:
        return "clock_continuity_unverified"
    # Unsupported or unobserved Ponder is recorded independently. The user
    # explicitly allows the local league to continue if it cannot be set.
    return None


def create_league_cgroups(manager, slots, players, profile, *, memory_preflight=None):
    """Create the owned groups using bounded profile-specific memory extents.

    The P16/P192 scored entrypoint remains closed: these supplied preflight
    fields are not themselves trusted host, overhead or concurrency evidence.
    Provenance, freshness, ancestor limits, a durable global owner and actual
    runtime admission must be verified before that gate can ever be opened.
    """
    if profile in ("test-p4", "test-p28"):
        return {slot.id: manager.create(slot) for slot in slots}, None
    if profile not in ("test-p16", "test-p192"):
        raise ValueError("unknown TEST profile cannot create a league cgroup")
    if type(memory_preflight) is not dict:
        raise ValueError("P16/P192 require explicit observed memory budget and overhead preflight")
    required = {"per_game_overhead_bytes", "overhead_evidence_sha256", "controller_reserve_bytes", "page_bytes"}
    telemetry = {"host_available_bytes", "node_available_bytes"}
    if not required <= set(memory_preflight) or set(memory_preflight) - required - telemetry:
        raise ValueError("P16/P192 memory preflight fields differ from the explicit contract")
    supplied = {**memory_preflight, "host_available_bytes": memory_preflight.get("host_available_bytes"),
                "node_available_bytes": memory_preflight.get("node_available_bytes")}
    admission = placement.league_memory_admission(
        [artifact.identity() for artifact in players], [slot.to_record() for slot in slots],
        profile=profile, **supplied)
    if admission.get("runtime_admission_complete") is not False:
        raise ValueError("arithmetic memory preflight must not assert runtime admission")
    by_id = {row["id"]: row["memory_max"] for row in admission["slots"]}
    if set(by_id) != {slot.id for slot in slots}:
        raise ValueError("calculated memory limits do not bind every owned slot")
    groups = {slot.id: manager.create(slot, memory_bytes=by_id[slot.id]) for slot in slots}
    return groups, admission


def capture_league_preflight(slots, cgroup_root, overhead, observe):
    """Bind one live capacity snapshot to frozen slots; no runtime admission."""
    names = {"per_game_overhead_bytes", "overhead_evidence_sha256", "controller_reserve_bytes"}
    if type(overhead) is not dict or set(overhead) != names:
        raise ValueError("actual cohort-bound overhead evidence owner is unavailable")
    slot_records = [slot.to_record() for slot in slots]
    expected_slots = ledger.digest(slot_records)
    capacity = observe(slot_records, cgroup_root)
    if (type(capacity) is not dict or capacity.get("format") != "rove4k-memory-capacity-observation-v1" or
            ledger.digest(slot_records) != expected_slots or capacity.get("slot_sha256") != expected_slots or
            capacity.get("test_inputs") is not False or
            capacity.get("runtime_admission_complete") is not False):
        raise ValueError("capacity observation is not the actual frozen-slot preflight")
    return capacity, {**overhead, "host_available_bytes": capacity.get("host_available_bytes"),
                      "node_available_bytes": capacity.get("node_available_bytes"), "page_bytes": capacity["page_bytes"]}


def verify_preexec_placement(receipt, *, pid, slot, cgroup):
    """Check the child's own pre-exec receipt; final engine identity is separate."""
    if (type(receipt) is not dict or type(pid) is not int or pid <= 0 or
            receipt.get("pid") != pid or receipt.get("stage") != "pre-exec runner; final engine observation is separate"):
        raise ValueError("pre-exec placement receipt does not identify the actual runner")
    cpus, nodes = list(slot.cpus), list(slot.memory_nodes)
    if (type(cgroup) is not dict or not isinstance(cgroup.get("path"), str) or
            not Path(cgroup["path"]).is_absolute() or type(cgroup.get("device")) is not int or
            cgroup["device"] < 0 or type(cgroup.get("inode")) is not int or cgroup["inode"] <= 0 or
            type(cgroup.get("memory_max")) is not int or cgroup["memory_max"] <= 0 or
            cgroup.get("cpus") != cpus or cgroup.get("memory_nodes") != nodes):
        raise ValueError("owned pre-exec cgroup identity and resource masks are required")
    if (receipt.get("requested_cpus") != cpus or receipt.get("effective_cpus") != cpus or
            receipt.get("requested_nodes") != nodes or receipt.get("effective_allowed_nodes") != nodes or
            receipt.get("cgroup") != cgroup):
        raise ValueError("pre-exec CPU, memory-node or cgroup evidence differs from the frozen slot")
    policy = receipt.get("observed_policy")
    if (slot.policy != "default" or receipt.get("requested_policy") != "default" or
            receipt.get("fallback") is not None or type(policy) is not dict or
            policy.get("available") is not True or policy.get("request_applied") is not True or
            policy.get("mode") != 0):
        raise ValueError("explicit default task memory policy was not applied and observed")
    return {"scope": "pre-exec runner; cgroup and task policy; TT pages unverified",
            "runner_pid": pid, "cpus": cpus, "memory_nodes": nodes,
            "requested_policy": "default", "observed_policy": policy,
            "cgroup": cgroup, "tt_page_placement": "pending"}


def protected_input(path):
    path = Path(path)
    if not path.is_absolute() or path.name == "inventory.json":
        raise ValueError("explicit absolute non-protected campaign input required")
    if any(part.startswith(".env") or part in (".ssh", ".aws", ".npmrc", "id_rsa", "id_ed25519") or
            any(word in part.lower() for word in ("credential", "service-account", "service_account", "api_key", "api-key", "ssh_key"))
            for part in path.parts):
        raise ValueError("protected file is not a campaign input")
    return path


def json_input(path, expected_sha=None):
    path = protected_input(path)
    if path.suffix != ".json":
        raise ValueError("explicit absolute JSON input required")
    if path.is_symlink() or path.stat().st_size > 32 << 20:
        raise ValueError("campaign input must be an ordinary bounded file")
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if expected_sha is not None and (not SHA.fullmatch(expected_sha) or actual != expected_sha):
        raise ValueError("input identity differs: " + path.name)
    return json.loads(raw), actual


def external_new(path):
    path = protected_input(path)
    if not path.is_absolute() or path.exists() or any((p / ".git").exists() for p in (path, *path.parents)):
        raise ValueError("new absolute output outside Git required")
    if any(p.is_symlink() for p in path.parents):
        raise ValueError("output must not follow links")
    return path


def bundle_path(root, logical):
    path = Path(logical)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("bundle members must be relative owned paths")
    result = root / path
    if result.is_symlink() or not result.resolve().is_relative_to(root.resolve()):
        raise ValueError("bundle member escaped its owner")
    return result


def runner_identity(binary, receipt):
    binary = protected_input(binary)
    record, receipt_sha = json_input(receipt)
    expected_patch = fastchess.sha(fastchess.PATCH.read_bytes())
    if (record.get("complete") is not True or record.get("upstream_commit") != fastchess.PIN or
            record.get("patch_sha256") != expected_patch or not binary.is_absolute() or binary.is_symlink()):
        raise ValueError("runner is not the reviewed pinned Fastchess build")
    command = record.get("command", {})
    if (command.get("returncode") != 0 or command.get("forced_cleanup") is not False or
            command.get("leader_reaped") is not True or command.get("group_absent") is not True):
        raise ValueError("runner build has no successful physical completion")
    binary_sha = registry.file_sha(binary)
    if record.get("binary_sha256") != binary_sha:
        raise ValueError("runner bytes differ from its actual build receipt")
    return {"sha256": binary_sha, "receipt_sha256": receipt_sha, "patch_sha256": expected_patch,
            "upstream_commit": fastchess.PIN}


def qualified_players(value, profile, *, base=None):
    if value.get("format") != "rove4k-league-registry-v1":
        raise ValueError("explicit qualification registry required")
    accepted, rejected, seen = [], [], set()
    for index, row in enumerate(value.get("players", [])):
        identity = row.get("artifact", {}).get("id", f"registry-row-{index}")
        try:
            raw = dict(row["artifact"])
            proof = Path(row["receipt"])
            if base is not None:
                raw["path"] = bundle_path(base, raw["path"])
                proof = bundle_path(base, row["receipt"])
            raw["path"] = protected_input(raw["path"])
            proof = protected_input(proof)
            artifact = registry.Artifact.from_record(raw)
            if artifact.profile != profile:
                continue
            if profile in ("test-p16", "test-p192") and artifact.family == "D":
                raise ValueError("D is outside the P16/P192 cohort")
            if artifact.id in seen:
                raise ValueError("duplicate player identity")
            admitted = registry.admit_to_test_league(artifact, proof, row["receipt_sha256"])
            seen.add(artifact.id)
            accepted.append({"artifact": artifact, "receipt": proof, "receipt_sha256": row["receipt_sha256"],
                             "admission": admitted})
        except (KeyError, OSError, ValueError, TypeError) as error:
            rejected.append({"id": identity, "reason": str(error)})
    return accepted, rejected


def validate_bank(path, expected_sha, stage, *, pgn_snapshot=None, bank_snapshot=None):
    if bank_snapshot is None:
        bank, actual_sha = json_input(path, expected_sha)
    else:
        if (type(bank_snapshot) is not bytes or not 0 < len(bank_snapshot) <= 32 << 20 or
                type(expected_sha) is not str or not SHA.fullmatch(expected_sha) or
                hashlib.sha256(bank_snapshot).hexdigest() != expected_sha):
            raise ValueError("opening bank snapshot differs from its supplied digest")
        bank, actual_sha = json.loads(bank_snapshot), expected_sha
    source = bank.get("source", {})
    if (source.get("revision") != "a6189a30dc273ccb21fc2536a9a2fefd5592a67a" or
            source.get("verified") is not True or source.get("license") != "CC0-1.0"):
        raise ValueError("league bank must be the verified pinned CC0 source")
    openings = bank.get("stages", {}).get(stage)
    if not openings:
        raise ValueError("the requested stage has no actual legal openings")
    families = []
    for row in openings:
        ID(row["id"])
        moves = row["moves"]
        if len(moves) < 8 or row["family"] != " ".join(moves[:8]):
            raise ValueError("opening family differs from its actual legal prefix")
        # Replaying again at plan time binds actual bank moves, not just a label.
        board = rules_module().Board.from_fen()
        for move in moves:
            board = board.play(move)
        families.append(row["family"])
    if len(families) != len(set(families)):
        raise ValueError("stage reuses an opening family")
    pgndata = bank["files"][stage]
    pgnpath = protected_input(pgndata["path"])
    if pgn_snapshot is None:
        if registry.file_sha(pgnpath) != pgndata["sha256"] or pgnpath.stat().st_size != pgndata["bytes"]:
            raise ValueError("opening PGN bytes differ from the bank")
    elif (type(pgn_snapshot) is not bytes or len(pgn_snapshot) != pgndata["bytes"] or
          hashlib.sha256(pgn_snapshot).hexdigest() != pgndata["sha256"]):
        raise ValueError("opening PGN snapshot differs from the bank")
    return bank, actual_sha, openings, pgnpath


def freeze_plan(campaign, profile, registry_path, bank_path, bank_sha256, runner_binary,
                runner_receipt, out, *, stage="broad", snapshot=None, selected_ids=None, repeats=1,
                broad_plan=None, broad_journal=None):
    ID(campaign)
    if profile not in TEST_PROFILES or stage not in ("broad", "high", "update1", "update2"):
        raise ValueError("score plans accept only named TEST profiles/stages")
    if type(repeats) is not int or repeats not in (1, 2):
        raise ValueError("one DRR, or explicitly two update opening pairs, required")
    if stage in ("broad", "high") and repeats != 1:
        raise ValueError("broad/high schedule is one DRR")
    source, source_sha = json_input(registry_path)
    players, rejected = qualified_players(source, profile)
    selection = None
    if not stage_profile_allowed(stage, profile):
        raise ValueError("broad/high stages use P4/P28 or P16/P192 respectively")
    if stage == "high":
        if broad_plan is None or broad_journal is None or selected_ids is not None:
            raise ValueError("high selection derives from the completed frozen broad stage")
        broad, broad_players = load_plan(broad_plan)
        if broad["content"]["campaign"] != campaign or broad["content"]["stage"] != "broad":
            raise ValueError("broad selection belongs to another campaign/stage")
        broad_profile = BROAD_FOR_HIGH[profile]
        if broad["content"]["profile"] != broad_profile:
            raise ValueError("high profile requires its matching broad TEST profile")
        broad_rows = ledger.read_journal(broad_journal, campaign)
        broad_families = {row["artifact"].id: row["artifact"].family for row in broad_players}
        summary = collect.collect(broad_rows, campaign,
            expected_pairs=[row["id"] for row in broad["content"]["pairs"]], profile=broad_profile,
            player_families=broad_families)
        selection = collect.select_high(summary, broad_families,
            [{"id": row["artifact"].id, "family": row["artifact"].family} for row in players])
        selection.update(broad_plan_sha256=broad["sha256"],
                         broad_journal_last_sha256=broad_rows[-1]["sha256"],
                         summary_sha256=ledger.digest(summary))
        selected_ids = selection["players"]
    if selected_ids is not None:
        if len(selected_ids) != len(set(selected_ids)):
            raise ValueError("duplicate selected player")
        available = {row["artifact"].id for row in players}
        if not set(selected_ids) <= available:
            raise ValueError("a selected player is not qualified at this TEST profile")
        players = [row for row in players if row["artifact"].id in selected_ids]
    players.sort(key=lambda row: row["artifact"].id)
    if len(players) < 2:
        raise ValueError("at least two qualified players are needed; no native fallback")
    if stage in ("broad", "high") and len({row["artifact"].family for row in players}) != len(players):
        raise ValueError("one qualified artifact per family in broad/high")
    if stage.startswith("update") and (selected_ids is None or len(players) != 2):
        raise ValueError("updates require an explicitly selected baseline/candidate pair")
    if stage.startswith("update") and (players[0]["artifact"].family != players[1]["artifact"].family or
            players[0]["artifact"].sha256 == players[1]["artifact"].sha256):
        raise ValueError("an update compares a distinct qualified candidate against its own family baseline")
    runner = runner_identity(runner_binary, runner_receipt)
    bank, bank_sha, openings, pgnpath = validate_bank(bank_path, bank_sha256, stage)
    snapshot = snapshot or topology.Topology.snapshot()
    slots, controller_cpus = league_placement(snapshot, profile)
    pairs = []
    for repeat in range(repeats):
        for a, b in itertools.combinations(players, 2):
            index = len(pairs)
            opening_index = index % len(openings)
            opening = openings[opening_index]
            ids = a["artifact"].id, b["artifact"].id
            pair_hash = ledger.digest({"campaign": campaign, "stage": stage, "profile": profile,
                                       "players": ids, "repeat": repeat, "opening": opening["id"]})[:12]
            pair_id = f"{stage}-{profile}-{index:03d}-{pair_hash}"
            pairs.append({"id": pair_id, "players": list(ids), "opening": opening,
                          "opening_index": opening_index + 1, "repeat": repeat})
    if len(pairs) > 128:
        raise ValueError("plan alone exceeds the cumulative campaign pair cap")
    out = external_new(out)
    out.mkdir(parents=True)
    (out / "players").mkdir()
    (out / "proofs").mkdir()
    (out / "runner").mkdir()
    published = []
    for row in players:
        artifact = row["artifact"]
        target = out / "players" / artifact.id
        shutil.copyfile(artifact.path, target)
        target.chmod(0o700)
        artifact.verify_bytes()
        if registry.file_sha(target) != artifact.sha256:
            raise ValueError("copied whole artifact changed")
        receipt_name = f"proofs/{artifact.id}.json"
        shutil.copyfile(row["receipt"], out / receipt_name)
        published.append({"artifact": {**artifact.identity(), "path": "players/" + artifact.id},
                          "receipt": receipt_name, "receipt_sha256": row["receipt_sha256"]})
    shutil.copyfile(runner_binary, out / "runner/fastchess")
    (out / "runner/fastchess").chmod(0o700)
    shutil.copyfile(runner_receipt, out / "runner/build.json")
    shutil.copyfile(pgnpath, out / "openings.pgn")
    shutil.copyfile(bank_path, out / "bank.json")
    body = {"campaign": campaign, "profile": profile, "stage": stage, "pairs": pairs,
            "registry": {"format": "rove4k-league-registry-v1", "players": published},
            "registry_input_sha256": source_sha, "excluded": rejected,
            "bank_id": bank["bank_id"], "bank_sha256": bank_sha, "bank_path": "bank.json", "selection": selection,
            "opening_pgn": "openings.pgn", "opening_pgn_sha256": registry.file_sha(out / "openings.pgn"),
            "runner": {**runner, "path": "runner/fastchess", "receipt": "runner/build.json"},
            "topology": snapshot.to_record(), "slots": [slot.to_record() for slot in slots],
            "controller_cpus": controller_cpus,
            "clock": {"tc": "30:00+3", "initial_ms": 1803000, "increment_ms": 3000, "ponder": False},
            "scope": "qualified TEST artifact cohort; not TCEC W256 strength", "partial_player_set": len(players) < 8}
    plan = {"format": "rove4k-campaign-plan-v1", "sha256": ledger.digest(body), "content": body}
    (out / "plan.json").write_bytes(ledger.canonical(plan) + b"\n")
    return plan


def load_plan(path):
    value, _ = json_input(path)
    if value.get("format") != "rove4k-campaign-plan-v1" or ledger.digest(value.get("content")) != value.get("sha256"):
        raise ValueError("frozen plan content identity changed")
    body = value["content"]
    if not stage_profile_allowed(body["stage"], body["profile"]) or not body["pairs"]:
        raise ValueError("nonempty TEST pair plan required")
    ID(body["campaign"])
    players, rejected = qualified_players(body["registry"], body["profile"], base=Path(path).parent)
    if rejected or len(players) != len(body["registry"]["players"]):
        raise ValueError("frozen player qualifications no longer match")
    runner = body["runner"]
    observed = runner_identity(bundle_path(Path(path).parent, runner["path"]), bundle_path(Path(path).parent, runner["receipt"]))
    if observed != {key: runner[key] for key in observed}:
        raise ValueError("frozen runner provenance changed")
    if registry.file_sha(bundle_path(Path(path).parent, body["opening_pgn"])) != body["opening_pgn_sha256"]:
        raise ValueError("frozen opening bank changed")
    bank, _ = json_input(bundle_path(Path(path).parent, body["bank_path"]), body["bank_sha256"])
    if bank["bank_id"] != body["bank_id"] or bank["files"][body["stage"]]["sha256"] != body["opening_pgn_sha256"]:
        raise ValueError("frozen bank/PGN binding changed")
    cohort = {row["artifact"].id for row in players}
    pair_ids = set()
    for pair in body["pairs"]:
        ID(pair["id"])
        if pair["id"] in pair_ids or len(pair["players"]) != 2 or len(set(pair["players"])) != 2 or not set(pair["players"]) <= cohort:
            raise ValueError("pair identity/cohort changed")
        pair_ids.add(pair["id"])
        index = pair["opening_index"]
        if type(index) is not int or index < 1 or pair["opening"] != bank["stages"][body["stage"]][index - 1]:
            raise ValueError("pair does not use its frozen source-bank opening")
    saved = topology.Topology.from_record(body["topology"])
    planned_slots, controller_cpus = league_placement(saved, body["profile"])
    expected_slots = [json.loads(json.dumps(slot.to_record())) for slot in planned_slots]
    if body["slots"] != expected_slots or body["clock"] != {"tc": "30:00+3", "initial_ms": 1803000, "increment_ms": 3000, "ponder": False}:
        raise ValueError("frozen placement/clock differs from the reviewed TEST contract")
    if body["controller_cpus"] != controller_cpus:
        raise ValueError("controller placement contract changed")
    return value, players


def rules_module():
    name = "rove_league_chess_oracle"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / "engines/tests/chess_oracle.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


TRACE = re.compile(r"^\[Engine\] \[(?P<time>[^\]]+)\] <[^>]+>\s+(?P<player>[A-Za-z0-9_.-]+) (?P<direction><---|--->) (?P<command>.*)$")


class TraceState:
    """Bind sent position/clock traffic to independently legal full history."""
    def __init__(self, opening, white, black):
        self.opening, self.white, self.black = tuple(opening), white, black
        self.moves = []
        self.board = rules_module().Board.from_fen()
        self.first_go = True
        self.clock = None
        self.candidate = None
        self.position_seen = False
        self.searching_player = None
        self.ponder_sent = {white: [], black: []}
        self.ponder_advertised = {white: False, black: False}
        self.pondering_players = set()
        self.ponder_positions = {}
        self.clock_tracking_complete = True

    def consume(self, line):
        match = TRACE.fullmatch(line)
        if match is None or match["player"] not in (self.white, self.black):
            return None
        command, sent = match["command"], match["direction"] == "<---"
        tokens = command.casefold().split()
        if not sent and tokens[:3] == ["option", "name", "ponder"]:
            self.ponder_advertised[match["player"]] = True
        if sent and tokens == ["ponderhit"]:
            player = match["player"]
            speculative = self.ponder_positions.get(player)
            if (player not in self.pondering_players or self.candidate is None or not self.candidate["legal"] or
                    speculative != self.moves + [self.candidate["move"]]):
                raise ValueError("ponderhit lacks its confirmed predicted reply")
            self.board = self.board.play(self.candidate["move"])
            self.moves.append(self.candidate["move"])
            if player != (self.white if self.board.turn else self.black):
                raise ValueError("ponderhit is not the confirmed side to move")
            self.candidate = None
            self.searching_player = player
            self.pondering_players.remove(player)
            self.ponder_positions.pop(player, None)
            # UCI ponderhit carries no new clock values; do not infer them.
            self.clock = None
            self.clock_tracking_complete = False
            return {"kind": "ponderhit_confirmed", "player": player, "raw_time": match["time"],
                    "moves": list(self.moves), "clock_continuity_verified": False}
        if sent and (tokens[:3] == ["setoption", "name", "ponder"] or
                     tokens[:1] == ["go"] and "ponder" in tokens[1:]):
            recorded = self.ponder_sent[match["player"]]
            if len(recorded) >= 2048:
                raise ValueError("excessive ponder control traffic")
            recorded.append(command)
            if tokens[:1] == ["go"]:
                self.pondering_players.add(match["player"])
                # Record actual protocol traffic without treating an optional
                # ponder GO as the scored side-to-move clock command.
                return {"kind": "ponder_go_sent", "player": match["player"],
                        "raw_time": match["time"], "actual_off_turn_search": None}
        if sent and command.startswith("position startpos"):
            tokens = command.split()
            if tokens[:2] != ["position", "startpos"] or len(tokens) > 2 and tokens[2] != "moves":
                raise ValueError("runner did not use full standard-start history")
            moves = tokens[3:] if len(tokens) > 2 else []
            if moves[:len(self.opening)] != list(self.opening) or moves[:len(self.moves)] != self.moves:
                raise ValueError("runner opening/history changed or retracted")
            added = moves[len(self.moves):]
            if (self.position_seen and self.candidate is not None and self.candidate["legal"] and
                    match["player"] == self.searching_player):
                # A pondering engine may receive its own just-selected move
                # plus a predicted reply. Replay the speculation independently
                # and never merge it into the scored confirmed history.
                if len(added) != 2 or added[0] != self.candidate["move"]:
                    raise ValueError("speculative position does not extend the actual candidate")
                speculative = self.board
                for move in added:
                    speculative = speculative.play(move)
                if match["player"] != (self.white if speculative.turn else self.black):
                    raise ValueError("speculative position is not the pondering side")
                self.ponder_positions[match["player"]] = list(moves)
                return {"kind": "ponder_position_sent", "player": match["player"],
                        "raw_time": match["time"], "moves": moves, "confirmed": False}
            if (self.position_seen and self.candidate is None and self.searching_player is not None and
                    match["player"] != self.searching_player and
                    self.searching_player == (self.white if self.board.turn else self.black) and len(added) == 1):
                speculative = self.board.play(added[0])
                if match["player"] != (self.white if speculative.turn else self.black):
                    raise ValueError("speculative reply is not the pondering side")
                self.ponder_positions[match["player"]] = list(moves)
                return {"kind": "ponder_position_sent", "player": match["player"],
                        "raw_time": match["time"], "moves": moves, "confirmed": False}
            if not self.position_seen:
                if moves != list(self.opening):
                    raise ValueError("first position differs from the whole frozen opening")
            elif added and (len(added) != 1 or self.candidate is None or not self.candidate["legal"] or
                            added[0] != self.candidate["move"]):
                raise ValueError("confirmed history is not the accepted bestmove candidate")
            for move in moves[len(self.moves):]:
                self.board = self.board.play(move)
                self.moves.append(move)
            expected_player = self.white if self.board.turn else self.black
            if match["player"] != expected_player:
                raise ValueError("position was sent to the wrong side")
            self.position_seen = True
            self.candidate = None
            return {"kind": "confirmed_position", "moves": list(self.moves), "raw_time": match["time"],
                    "player": match["player"]}
        if sent and command.startswith("go "):
            if not self.position_seen:
                raise ValueError("GO preceded its full position history")
            tokens = command.split()
            if len(tokens) != 9 or tokens[:1] != ["go"] or tokens[1::2] != ["wtime", "btime", "winc", "binc"]:
                raise ValueError("runner clock syntax changed")
            try:
                values = {tokens[index]: int(tokens[index + 1]) for index in range(1, len(tokens), 2)}
            except (ValueError, IndexError) as error:
                raise ValueError("invalid runner clock") from error
            if (set(values) != {"wtime", "btime", "winc", "binc"} or any(value < 0 for value in values.values()) or
                    values["winc"] != 3000 or values["binc"] != 3000):
                raise ValueError("clock/increment differs from the frozen control")
            if self.first_go and (values["wtime"] != 1803000 or values["btime"] != 1803000):
                raise ValueError("initial clock includes gate waiting or differs from the pinned convention")
            if match["player"] != (self.white if self.board.turn else self.black):
                raise ValueError("GO was sent to the wrong side")
            if self.clock is not None:
                mover = "wtime" if match["player"] == self.black else "btime"
                other = "btime" if mover == "wtime" else "wtime"
                if values[other] != self.clock[other] or values[mover] > self.clock[mover] + 3000:
                    raise ValueError("runner clock changed the waiting side or added excess time")
            self.first_go, self.clock = False, values
            self.searching_player = match["player"]
            return {"kind": "go_clock", "moves": list(self.moves), "clock": values,
                    "raw_time": match["time"], "player": match["player"]}
        if not sent and command.startswith("bestmove "):
            tokens = command.split()
            move = tokens[1] if len(tokens) > 1 else ""
            if match["player"] in self.pondering_players:
                self.pondering_players.remove(match["player"])
                self.ponder_positions.pop(match["player"], None)
                return {"kind": "ponder_bestmove_observed", "move": move,
                        "player": match["player"], "raw_time": match["time"], "confirmed": False}
            legal = False
            try:
                self.board.play(move)
                legal = match["player"] == self.searching_player
            except (ValueError, IndexError):
                pass
            self.candidate = {"kind": "bestmove_candidate", "move": move, "legal": legal,
                              "player": match["player"], "raw_time": match["time"]}
            return self.candidate
        return None


def parse_result(path, raw_path, spec):
    text = path.read_text(encoding="utf-8")
    headers = dict(re.findall(r'^\[(\w+) "([^"\r\n]*)"\]$', text, re.MULTILINE))
    if (len(re.findall(r'^\[Event ', text, re.MULTILINE)) != 1 or headers.get("White") != spec["white"] or
            headers.get("Black") != spec["black"] or headers.get("Result") not in ("1-0", "0-1", "1/2-1/2") or
            "FEN" in headers or "SetUp" in headers):
        raise ValueError("completed PGN does not bind this standard-start game")
    body = re.sub(r'^\[.*\]\s*$', '', text, flags=re.MULTILINE)
    body = re.sub(r'\{[^}]*\}', ' ', body, flags=re.DOTALL)
    moves = re.findall(r'(?<![A-Za-z0-9])([a-h][1-8][a-h][1-8][nbrq]?)(?![A-Za-z0-9])', body)
    if moves[:len(spec["opening_moves"])] != spec["opening_moves"]:
        raise ValueError("PGN does not preserve the entire frozen opening prefix")
    board = rules_module().Board.from_fen()
    seen = Counter({board.repetition_key(): 1})
    for move in moves:
        board = board.play(move)
        seen[board.repetition_key()] += 1
    legal = list(board.legal_moves())
    terminal = None
    if not legal:
        terminal = ("0-1" if board.turn else "1-0") if board.in_check() else "1/2-1/2"
    pieces = [(index, piece.lower()) for index, piece in enumerate(board.cells) if piece not in ".Kk"]
    dead = (not any(piece in "pqr" for _, piece in pieces) and
            (len(pieces) <= 1 or all(piece == "b" for _, piece in pieces) and
             len({(index // 8 + index % 8) % 2 for index, _ in pieces}) == 1))
    if terminal is None and (dead or seen[board.repetition_key()] >= 3 or board.halfmove >= 100):
        terminal = "1/2-1/2"
    result, reason = headers["Result"], "completed_chess_result"
    if terminal is not None and result != terminal:
        raise ValueError("PGN result contradicts the independent chess oracle")
    if terminal is None:
        explanation = (headers.get("Termination", "") + " " + text[-1024:]).lower()
        if "illegal" in explanation:
            reason = "engine_illegal"
        elif any(word in explanation for word in ("time forfeit", "loses on time", "time loss", "timeout")):
            reason = "engine_time_loss"
        elif any(word in explanation for word in ("disconnect", "crash", "stalled")):
            reason = "engine_crash"
        elif "resign" not in explanation:
            raise ValueError("nonterminal PGN has no recognized actual engine outcome")
        if result == "1/2-1/2":
            raise ValueError("nonterminal draw is not a supported score adjudication")
    trace = TraceState(spec["opening_moves"], spec["white"], spec["black"])
    if raw_path.is_symlink() or raw_path.stat().st_size > 128 << 20:
        raise ValueError("raw game evidence exceeds its owned finite extent")
    with raw_path.open(encoding="utf-8", errors="replace") as source:
        for line in source:
            if len(line) > 64 << 10 or not line.endswith("\n"):
                raise ValueError("raw game has an excessive or incomplete protocol line")
            trace.consume(line.rstrip("\r\n"))
    if trace.first_go:
        raise ValueError("completed game has no actual fixed-clock GO evidence")
    final = trace.moves + ([trace.candidate["move"]] if trace.candidate and trace.candidate["legal"] else [])
    if moves != trace.moves and moves != final:
        raise ValueError("PGN history differs from actual runner-confirmed UCI history")
    ponder = {player: {**fastchess.ponder_uci_evidence(trace.ponder_sent[player]),
                       "option_advertised_in_trace": trace.ponder_advertised[player]}
              for player in (spec["white"], spec["black"])}
    return {"result": result, "reason": reason, "moves": moves, "plies": len(moves),
            "pgn_sha256": registry.file_sha(path), "raw_sha256": registry.file_sha(raw_path),
            "white": spec["white"], "black": spec["black"], "opening_id": spec["opening_id"],
            "opening_sha256": spec["opening_sha256"], "bank_id": spec["bank_id"],
            "profile": spec["profile"], "artifact_sha256": spec["artifact_sha256"], "ponder_uci": ponder,
            "clock_tracking_complete": trace.clock_tracking_complete}


def proc_identity(pid):
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
    except FileNotFoundError:
        return None
    parts = raw[raw.rfind(")") + 2:].split()
    return {"pid": pid, "pgid": int(parts[2]), "session": int(parts[3]), "start_ticks": int(parts[19])}


def require_settled_prior_jobs(rows, instance_id, campaign_budget):
    """An elapsed wait or a different controller host is not process death."""
    starts, settled, unsettled = {}, set(), {}
    for row in rows:
        key = row.get("game"), row.get("attempt")
        if row["event"] == "game.process":
            starts[key] = row["data"]
        elif row["event"] == "game.process_completed":
            data = row["data"]
            if data.get("readers_done") is True and data.get("remaining_processes") == [] and type(data.get("returncode")) is int:
                settled.add(key)
        elif row["event"] == "campaign.unsettled_owner":
            unsettled[row["data"]["launch_id"]] = row["data"]
    current_boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    for launch, data in unsettled.items():
        owned = data["observation"]
        if data.get("instance_id") != instance_id:
            prior = [item for item in campaign_budget.instances if item.instance_id == data.get("instance_id")]
            if len(prior) != 1 or prior[0].active:
                raise RuntimeError("unsettled launch's prior host lacks authoritative termination")
            continue
        if not isinstance(data.get("boot_id"), str) or not re.fullmatch(r"[a-f0-9-]{36}", data["boot_id"]):
            raise ValueError("unsettled launch lacks its original boot identity")
        if data.get("boot_id") != current_boot:
            continue
        if (any(type(owned.get(name)) is not int or owned[name] <= 0 for name in
                ("pid", "pgid", "session", "start_ticks")) or owned.get("readers_done") is not True):
            raise RuntimeError("unverified launch/output owner remains unsettled on this boot; no new wave or resume")
        starts["launch:" + launch, None] = {**owned, "instance_id": instance_id, "boot_id": current_boot}
    for key, owned in starts.items():
        if key in settled:
            continue
        if owned.get("instance_id") != instance_id:
            prior = [item for item in campaign_budget.instances if item.instance_id == owned.get("instance_id")]
            if len(prior) != 1 or prior[0].active:
                raise RuntimeError("prior host has no authoritative termination observation")
            continue
        if not isinstance(owned.get("boot_id"), str) or not re.fullmatch(r"[a-f0-9-]{36}", owned["boot_id"]):
            raise ValueError("prior runner lacks its original boot identity")
        if owned.get("boot_id") != current_boot:
            continue  # Same verified EC2 lease, new kernel boot: old tasks cannot survive.
        leader = proc_identity(owned["pid"])
        if (owned["pid"], owned["pgid"], owned["session"]) != (owned["pid"],) * 3:
            raise ValueError("prior runner was not the recorded dedicated process-group/session leader")
        if leader is not None:
            if leader["start_ticks"] == owned["start_ticks"]:
                raise RuntimeError("original runner identity exists; settle its owner before resume")
            # Linux retains the dedicated leader's PID allocation while a
            # process-group/session still references it. A reused leader PID
            # has a new allocation; its groups belong to another owner.
            continue
        for path in Path("/proc").iterdir():
            if path.name.isdigit():
                observed = proc_identity(int(path.name))
                if observed and (observed["pgid"] == owned["pgid"] or observed["session"] == owned["session"]):
                    reallocated = proc_identity(owned["pid"])
                    if reallocated is not None and reallocated["start_ticks"] != owned["start_ticks"]:
                        break
                    raise RuntimeError("prior runner process group/session is still present")


class StageController:
    """One frozen stage; AWS lifecycle remains a separate verified owner."""
    def __init__(self, plan_path, out, journal, publisher, campaign_budget, *, wave_executor=None, lease_verifier=None):
        self.plan_path = Path(plan_path)
        self.envelope, players = load_plan(self.plan_path)
        self.plan = self.envelope["content"]
        assert_stage_binding(self.envelope, journal.rows)
        self.bundle = self.plan_path.parent
        self.players = {row["artifact"].id: row["artifact"] for row in players}
        self.out = Path(out)
        self.journal = journal
        self.publisher = publisher
        self.budget = campaign_budget
        self.results = ledger.CampaignResults.replay(self.plan["campaign"], journal.rows)
        if self.budget.campaign != self.plan["campaign"] or len(self.budget.active_instances) != 1 or not self.budget.active_instances[0].instance_id:
            raise ValueError("one verified, bound live campaign lease is required")
        self.instance_id = self.budget.active_instances[0].instance_id
        if wave_executor is None:
            try:
                from .wave import WaveExecutor
            except ImportError:
                from wave import WaveExecutor
            wave_executor = WaveExecutor()
        self.executor = wave_executor
        self.lease_verifier = lease_verifier
        self.pending_results = {}
        self.tail = {}
        self.job_specs = {}
        self.enqueued = len(journal.rows)
        self.last_replication = 0.0
        self.replication_tickets = []
        self.outbox = None
        self.slots = {}
        self.ready = {}
        self.unsettled = {}
        self.uncertain_releases = {}
        self.intent_owner = None
        self._gc_scope_prefix = uuid.uuid4().hex
        self._gc_scope_bindings = {}
        # Filled only by a future authenticated live-memory evidence owner.
        # The arithmetic helper alone cannot open P16/P192 execution.
        self.memory_preflight = None

    def cooperative_gc(self):
        """Collect this controller's garbage and mark overlapping games.

        This does not request GC in any engine or other process. A call that
        fails is still a requested intervention and cannot be scored as clean.
        """
        return _COOPERATIVE_GC_TRACKER.collect()

    def _gc_scope_key(self, job):
        prefix = getattr(self, "_gc_scope_prefix", None)
        return (prefix, job.identity) if prefix is not None else None

    def _gc_scope_open(self, job, spec, observation):
        key = self._gc_scope_key(job)
        if key is None:
            return
        try:
            observer = proc_identity(os.getpid())
            boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            if observer is None:
                raise ValueError("controller process identity unavailable")
            identity = {"instance_id": self.instance_id, "boot_id": boot,
                        "launch_pid": observation.get("pid"),
                        "launch_start_ticks": observation.get("start_ticks"),
                        "observer_pid": observer["pid"],
                        "observer_start_ticks": observer["start_ticks"]}
            record = _COOPERATIVE_GC_TRACKER.open_record(
                key, self.plan["campaign"], spec["pair"], spec["game"], spec["attempt"], identity)
        except (OSError, ValueError, KeyError, TypeError):
            # Incomplete identity or a missing pre-spawn baseline cannot prove
            # a clean performance interval; do not impede the game itself.
            _COOPERATIVE_GC_TRACKER.forget(key)
            return
        self._gc_scope_bindings[job.identity] = identity
        try:
            self.append("game.cooperative_gc_open", record, pair=spec["pair"],
                        game=spec["game"], attempt=spec["attempt"])
        except Exception:
            # A failed journal write can leave a partial durable record. Keep
            # existing owner/quarantine error handling rather than continuing
            # with a potentially corrupted authoritative journal.
            self._gc_scope_bindings.pop(job.identity, None)
            _COOPERATIVE_GC_TRACKER.forget(key)
            raise

    def _gc_scope_close(self, job, spec, observation, result_data):
        key = self._gc_scope_key(job)
        bindings = getattr(self, "_gc_scope_bindings", {})
        identity = bindings.pop(job.identity, None)
        if key is None or identity is None:
            return
        confirmed = False
        try:
            observer = proc_identity(os.getpid())
            boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            confirmed = (physically_settled(observation) and observer is not None
                         and observer["pid"] == identity["observer_pid"]
                         and observer["start_ticks"] == identity["observer_start_ticks"]
                         and boot == identity["boot_id"]
                         and observation.get("pid") == identity["launch_pid"]
                         and observation.get("start_ticks") == identity["launch_start_ticks"])
        except (OSError, ValueError, KeyError, TypeError):
            pass
        try:
            record = _COOPERATIVE_GC_TRACKER.close_record(key, result_data, identity_confirmed=confirmed)
        except (ValueError, TypeError):
            return
        # Durable journal failure is different from a missing observation: it
        # must follow the controller's existing owner/quarantine error path.
        self.append("game.cooperative_gc_close", record, pair=spec["pair"],
                    game=spec["game"], attempt=spec["attempt"])

    def prepare_intent_owner(self):
        """Register a local sidecar before entering the Wave selector loop.

        The sidecar is not replicated by this method; a missing registered
        file is therefore an explicit recovery failure, never a clean resume.
        """
        path = self.out / "release-intents.jsonl"
        existing = [row for row in self.journal.rows if row.get("event") == "campaign.intent_journal"]
        if existing or path.exists():
            raise ValueError("existing intent owner requires independent recovery before reuse")
        owner = IntentJournalOwner(path, self.plan["campaign"], self.instance_id)
        try:
            row = self.append("campaign.intent_journal", {"path": str(path), "instance_id": self.instance_id,
                "boot_id": owner.boot_id, "device": owner.journal.identity[0], "inode": owner.journal.identity[1],
                "scope": "local only; remote recovery requires the original sidecar"})
            owner.bind_registration(self.journal, row)
        except BaseException:
            owner.close()
            raise
        self.intent_owner = owner
        return owner

    def close_intent_owner(self, owner, observations):
        """Close only after every tracked local gate is physically settled.

        This is called outside the Wave loop. It records local closure only;
        remote/global authority and engine-go proof remain separate gates.
        """
        if owner is not self.intent_owner or not owner.registered() or not isinstance(observations, (list, tuple)):
            raise ValueError("registered intent owner and complete observations required")
        identities = [row.get("identity") for row in observations if isinstance(row, dict)]
        if (len(identities) != len(observations) or len(set(identities)) != len(identities)
                or set(identities) != owner._tracked or any(not physically_settled(row) or release_unresolved(row)
                                                            for row in observations)):
            raise ValueError("every tracked gate must be locally settled before intent closure")
        for observation in observations:
            identity = observation["identity"]
            spec = self.job_specs.get(identity)
            if not isinstance(spec, dict):
                raise ValueError("tracked gate has no original controller job")
            def matching(event):
                return [row for row in self.journal.rows if row.get("event") == event
                        and all(row.get(key) == spec.get(key) for key in ("pair", "game", "attempt"))]
            if observation.get("pid") is None:
                records = matching("campaign.game_not_started")
                if (matching("game.process") or matching("game.process_completed")
                        or len(records) != 1 or not isinstance(records[0].get("data"), dict)
                        or ledger.canonical(records[0]["data"].get("runner_observation")) != ledger.canonical(observation)):
                    raise ValueError("unstarted gate lacks its durable settlement observation")
                continue
            processes = matching("game.process")
            completions = matching("game.process_completed")
            fields = ("pid", "pgid", "session", "start_ticks")
            if (len(processes) != 1 or len(completions) != 1
                    or not isinstance(processes[0].get("data"), dict)
                    or not isinstance(completions[0].get("data"), dict)
                    or processes[0]["data"].get("identity") != identity
                    or completions[0]["data"].get("identity") != identity
                    or any(type(observation.get(key)) is not int or observation[key] <= 0
                           for key in ("pid", "pgid", "session"))
                    or observation["pid"] != observation["pgid"] or observation["pid"] != observation["session"]
                    or type(observation.get("start_ticks")) is not int or observation["start_ticks"] < 0
                    or type(processes[0].get("seq")) is not int or type(completions[0].get("seq")) is not int
                    or processes[0]["seq"] >= completions[0]["seq"]
                    or any(processes[0]["data"].get(key) != observation.get(key) for key in fields)
                    or any(completions[0]["data"].get(key) != observation.get(key) for key in fields)
                    or not physically_settled(completions[0]["data"])
                    or completions[0]["data"].get("returncode") != observation.get("returncode")
                    or processes[0]["data"].get("instance_id") != self.instance_id
                    or processes[0]["data"].get("boot_id") != owner.boot_id):
                raise ValueError("tracked gate lacks matching durable process settlement")
        owner.close()
        if owner._failure is not None:
            raise ValueError("failed intent journal cannot be closed as reconciled")
        intents = registered_intent_rows(self.journal.rows, self.out, self.plan["campaign"], allow_open=True)
        assert_no_unreconciled_releases(self.journal.rows, intents)
        stat = ledger.external(owner.path).stat()
        if (stat.st_dev, stat.st_ino) != owner.journal.identity:
            raise ValueError("intent journal identity changed before closure")
        return self.append("campaign.intent_journal_closed", {"path": str(owner.path),
            "device": stat.st_dev, "inode": stat.st_ino, "count": len(intents),
            "head_sha256": intents[-1]["sha256"] if intents else "0" * 64,
            "scope": "local closure only; not global authorization or remote recovery"})

    def record_unsettled(self, job, observation):
        if job.identity in self.unsettled:
            return
        spec = self.job_specs[job.identity]
        data = {"launch_id": job.identity, "game": spec["game"], "attempt": spec["attempt"],
                "instance_id": self.instance_id, "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                "observation": observation}
        self.append("campaign.unsettled_owner", data)
        self.unsettled[job.identity] = data

    def quarantine_release(self, job, observation, keys):
        data = {"launch_id": job.identity, "instance_id": self.instance_id,
                "observation": observation,
                "scope": "physical settlement does not reconcile possibly committed or transported GO"}
        self.append("campaign.release_unreconciled", data, **keys)
        self.uncertain_releases[job.identity] = data

    def append(self, event, data=None, *, pair=None, game=None, attempt=None):
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        preview = {"event": event, "data": {} if data is None else data,
                   "campaign": self.plan["campaign"], "pair": pair, "game": game, "attempt": attempt}
        results = self.results
        if event in ("game.started", "game.result", "game.remote_confirmed", "game.interrupted"):
            results = ledger.CampaignResults(results.campaign, dict(results.games))
            if (game, attempt) in results.games:
                results.games[game, attempt] = copy.copy(results.games[game, attempt])
        results.apply(preview)
        next_budget = self.budget.apply(event, preview["data"], timestamp)
        row = self.journal.append(event, data, pair=pair, game=game, attempt=attempt, time_utc=timestamp)
        self.results, self.budget = results, next_budget
        return row

    def replicate(self, *, force=False):
        self.outbox.check()
        now = time.monotonic()
        if not force and now - self.last_replication < 1:
            return
        rows = self.journal.rows[self.enqueued:]
        while rows:
            block, size = [], 0
            for row in rows:
                encoded = ledger.canonical(row) + b"\n"
                if block and size + len(encoded) > 4 << 20:
                    break
                block.append((row, encoded))
                size += len(encoded)
            data = b"".join(encoded for _, encoded in block)
            sha = hashlib.sha256(data).hexdigest()
            key = f"{self.plan['campaign']}/journal/{block[0][0]['seq']:09d}-{block[-1][0]['seq']:09d}-{sha}.jsonl"
            self.replication_tickets.append(self.outbox.submit(key, data))
            self.enqueued += len(block)
            rows = rows[len(block):]
        self.last_replication = now

    def queue_result(self, game, attempt, data):
        # FIFO publication makes the immutable start/READY/result journal
        # prefix durable before a result object can become visible remotely.
        self.replicate(force=True)
        required = []
        for kind, filename in (("pgn", "game.pgn"), ("raw", "raw.log")):
            key_name = kind + "_object_key"
            key = data[key_name]
            path = bundle_path(self.out, data["evidence_directory"]) / filename
            if path.is_file():
                body = path.read_bytes()
            elif hasattr(self.publisher, "read_verified"):
                body = self.publisher.read_verified(key, expected_sha=data[kind + "_sha256"], max_bytes=128 << 20)
            else:
                raise RuntimeError("completed evidence is missing; do not replay or fabricate its game")
            if hashlib.sha256(body).hexdigest() != data[kind + "_sha256"]:
                raise ValueError("completed evidence bytes changed")
            required.append(self.outbox.submit(key, body))
        raw = ledger.canonical(data)
        sha = hashlib.sha256(raw).hexdigest()
        key = f"{self.plan['campaign']}/results/{game}/attempt-{attempt:03d}/{sha}.json"
        self.pending_results[game, attempt] = {"result": self.outbox.submit(key, raw), "required": required}

    def acknowledge_results(self, *, wait=False):
        for key, tickets in list(self.pending_results.items()):
            ticket = tickets["result"]
            if not wait and not all(item.done.is_set() for item in (*tickets["required"], ticket)):
                continue
            evidence = [item.result(timeout=125 if wait else 0) for item in tickets["required"]]
            acknowledgement = ticket.result(timeout=125 if wait else 0)
            acknowledgement["evidence"] = evidence
            state = self.results.games[key]
            self.append("game.remote_confirmed", acknowledgement, pair=state.pair, game=state.game, attempt=state.attempt)
            del self.pending_results[key]
        for pair in self.results.pairs():
            if pair["pair"] not in self.budget.completed_pairs:
                self.append("budget.pair_completed", {"pair_id": pair["pair"]})

    def observe_raw(self, job):
        state = self.tail[job.identity]
        path = job.out / "raw.log"
        if not path.exists():
            return
        if path.is_symlink() or path.stat().st_size < state["offset"]:
            raise ValueError("owned raw trace was replaced or truncated")
        with path.open("rb") as stream:
            stream.seek(state["offset"])
            data = stream.read(128 << 10)
        if not data:
            return
        spec = self.job_specs[job.identity]
        import base64
        started = (spec["game"], spec["attempt"]) in self.results.games
        self.append("game.raw_chunk" if started else "campaign.launch_raw_chunk", {"launch_id": job.identity,
                    "offset": state["offset"], "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(), "base64": base64.b64encode(data).decode()},
                    pair=spec["pair"], game=spec["game"], attempt=spec["attempt"])
        state["offset"] += len(data)
        if not started:
            return
        text = state["partial"] + data.decode("utf-8", "replace")
        lines = text.split("\n")
        state["partial"] = lines.pop()
        if len(state["partial"]) > 64 << 10:
            raise ValueError("raw protocol line exceeds the admitted input extent")
        for line in lines:
            observed = state["trace"].consume(line.rstrip("\r"))
            if observed is not None:
                self.append("game." + observed["kind"], observed, pair=spec["pair"], game=spec["game"], attempt=spec["attempt"])

    def event(self, event, job, observation):
        spec = self.job_specs[job.identity]
        keys = {name: spec[name] for name in ("pair", "game", "attempt")}
        if event == "spawned":
            self.append("game.started", spec["identity"], **keys)
            self.append("game.process", {**observation, "instance_id": self.instance_id,
                        "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}, **keys)
            self._gc_scope_open(job, spec, observation)
        elif event in ("ready", "released"):
            if event == "ready":
                slot = self.slots[spec["identity"]["slot"]]
                if self.plan["profile"] in ("test-p16", "test-p192"):
                    receipt, receipt_sha = json_input(spec["placement_record"])
                    proof = verify_preexec_placement(receipt, pid=observation["pid"], slot=slot,
                                                    cgroup=spec["placement_cgroup"])
                    proof["receipt_sha256"] = receipt_sha
                    self.append("game.placement_preexec", proof, **keys)
                    observation = {**observation, "preexec_placement": proof}
                observation = {**observation, "engines": placement.observe_game_engines(
                    observation["pid"], [self.players[name].native_sha256 for name in
                    (spec["identity"]["white"], spec["identity"]["black"])], slot.cpus,
                    expected_start_ticks=observation["start_ticks"])}
                self.ready[job.identity] = observation
            elif observation.get("gate_receipt_required") is True:
                observation = {**observation, "instance_id": self.instance_id,
                               "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}
                binding = go2_local_binding(observation)
                if (binding["launch_id"] != job.identity or observation["ready"]["job"] != job.start_job or
                        any(binding[name] != spec[name] for name in ("pair", "game", "attempt"))):
                    raise ValueError("GO2 release changed the runner job")
                if observation.get("gate_intent_required") is True:
                    try:
                        from .wave import AsyncIntentDecision
                    except ImportError:
                        from wave import AsyncIntentDecision
                    owner = getattr(self, "intent_owner", None)
                    receipt = AsyncIntentDecision(job.identity, observation.get("gate_intent_payload"),
                                                  observation.get("gate_intent_seq"), observation.get("gate_intent_sha256"))
                    if type(owner) is not IntentJournalOwner or not owner.confirm(receipt, job, observation):
                        raise ValueError("GO2 release lacks its registered durable intent")
            self.append("game." + event, observation, **keys)
        elif event == "gate_received":
            # This records Wave's local receipt match, not authentication of
            # the coordinator or evidence of the engine's UCI go command.
            observation = {**observation, "instance_id": self.instance_id,
                           "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}
            binding = go2_local_binding(observation, received=True)
            ready = self.ready.get(job.identity)
            if (binding["launch_id"] != job.identity or observation["ready"]["job"] != job.start_job or
                    any(binding[name] != spec[name] for name in ("pair", "game", "attempt")) or
                    not isinstance(ready, dict) or
                    any(ready.get(name) != observation.get(name) for name in ("pid", "start_ticks"))):
                raise ValueError("GO2 receipt changed its READY process or job")
            prior = [row for row in self.journal.rows if row.get("event") == "game.released"
                     and row.get("game") == spec["game"] and row.get("attempt") == spec["attempt"]
                     and row.get("data", {}).get("identity") == job.identity]
            received = [row for row in self.journal.rows if row.get("event") == "game.gate_received"
                        and row.get("game") == spec["game"] and row.get("attempt") == spec["attempt"]
                        and row.get("data", {}).get("launch_id") == job.identity]
            if len(prior) != 1 or received or go2_local_binding(prior[0]["data"]) != binding:
                raise ValueError("GO2 receipt does not match one durable release")
            self.append("game.gate_received", {"launch_id": job.identity,
                        "instance_id": binding["instance_id"], "boot_id": binding["boot_id"],
                        "observation": observation,
                        "scope": "local runner receipt match; not coordinator authentication or engine UCI go"}, **keys)
        elif event == "tick":
            self.observe_raw(job)
        elif event == "cancelled":
            state = self.results.games.get((spec["game"], spec["attempt"]))
            if state is None:
                raise ValueError("cancelled runner has no original game owner")
            status = observation.get("status")
            if (status not in ("cancelled_before_go", "cancelled_unreconciled") or
                    observation.get("gate_cancelled") is not True or
                    observation.get("gate_transport") != "not_attempted" or
                    (observation.get("gate_released") is not None and observation.get("gate_released") is not False) or
                    observation.get("gate_send_started_monotonic") is not None or
                    observation.get("released_monotonic") is not None or
                    observation.get("gate_receipt") not in (None, "pending", "unresolved") or
                    observation.get("gate_receipt_monotonic") is not None or
                    (observation.get("gate_fence_send_time_uncertain") is not None and
                     observation.get("gate_fence_send_time_uncertain") is not False) or
                    observation.get("gate_transport_observation_error") is not None or
                    observation.get("gate_release_event_error") is not None or
                    observation.get("gate_receipt_event_error") is not None):
                raise ValueError("cancelled runner lacks a bounded gate outcome")
            # An authorization request or durable intent may already have
            # committed even when no socket write occurred. A caller cannot
            # relabel those cases as settled, nor present inconsistent
            # requested/resolved flags as a clean before-GO cancellation.
            requested = observation.get("gate_authorization_requested")
            resolved = observation.get("gate_authorization_resolved")
            intent_requested = observation.get("gate_intent_requested")
            if (type(observation.get("gate_authorized")) is not bool or
                    type(observation.get("gate_authorization_unknown")) is not bool or
                    any(value is not None and type(value) is not bool
                    for value in (requested, resolved, intent_requested)) or
                    resolved is True and requested is not True or
                    status == "cancelled_before_go" and
                    (observation.get("gate_authorized") is not False or
                     observation.get("gate_authorization_unknown") is not False or
                     intent_requested is True or requested is True and resolved is not True) or
                    status == "cancelled_unreconciled" and not
                    (observation.get("gate_authorized") is True or
                     observation.get("gate_authorization_unknown") is True or intent_requested is True)):
                raise ValueError("cancelled runner authorization state differs")
            if not physically_settled(observation):
                self.record_unsettled(job, observation)
            else:
                self.append("game.process_completed", observation, **keys)
            if status == "cancelled_unreconciled":
                self.quarantine_release(job, observation, keys)
            elif physically_settled(observation) and state.result is None and state.interrupted is None:
                self.append("game.interrupted", {"reason": "budget_drain", "runner_observation": observation}, **keys)
        elif event in ("completed", "aborted", "delivery_uncertain"):
            # The WaveExecutor only reports completed after group and readers
            # are physically settled. Earlier completed colours survive a later abort.
            state = self.results.games.get((spec["game"], spec["attempt"]))
            if state is None:
                self.append("campaign.game_not_started", {"runner_observation": observation}, **keys)
                if not physically_settled(observation):
                    self.record_unsettled(job, observation)
                return
            self.append("game.process_completed", observation, **keys)
            if release_unresolved(observation):
                if not physically_settled(observation):
                    self.record_unsettled(job, observation)
                self.quarantine_release(job, observation, keys)
                return
            if event == "delivery_uncertain":
                raise ValueError("delivery uncertainty event lacks an uncertain transport observation")
            self.observe_raw(job)
            if (event == "completed" and observation.get("gate_released") is True and
                    observation.get("returncode") == 0 and observation.get("cleanup_forced") is False and
                    observation.get("remaining_processes") == [] and observation.get("readers_done") is True):
                try:
                    data = parse_result(job.out / "game.pgn", job.out / "raw.log", spec["identity"])
                except (OSError, ValueError) as error:
                    self.append("game.interrupted", {"reason": "protocol_harness_error", "error": str(error)}, **keys)
                else:
                    prefix = f"{self.plan['campaign']}/games/{spec['game']}/attempt-{spec['attempt']:03d}"
                    data["pgn_object_key"] = f"{prefix}/pgn-{data['pgn_sha256']}.pgn"
                    data["raw_object_key"] = f"{prefix}/raw-{data['raw_sha256']}.log"
                    data["evidence_directory"] = str(job.out.relative_to(self.out))
                    unresolved_reason = score_evidence_unresolved(data, self.plan["profile"])
                    if unresolved_reason:
                        # The game completed; retain its result and raw evidence
                        # but do not turn an unverified clock into a score.
                        pending = {"launch_id": job.identity, "instance_id": self.instance_id,
                                   "result": data, "reason": unresolved_reason,
                                   "scope": "completed game, unscored until independent evidence reconciliation"}
                        self.append("campaign.game_evidence_unresolved", pending, **keys)
                        self.uncertain_releases[job.identity] = pending
                    else:
                        self.append("game.result", data, **keys)
                        self._gc_scope_close(job, spec, observation, data)
                        self.queue_result(spec["game"], spec["attempt"], data)
            elif state.result is None and state.interrupted is None:
                reason = "budget_termination" if time.time() >= self.budget.deadline(time.time()) else "protocol_harness_error"
                self.append("game.interrupted", {"reason": reason, "runner_observation": observation}, **keys)
        self.acknowledge_results()
        self.replicate()

    def pending(self):
        jobs = []
        for pair in self.plan["pairs"]:
            for leg in (0, 1):
                game = pair["id"] + f"-leg{leg}"
                states = [state for (name, _), state in self.results.games.items() if name == game]
                if any(state.accepted or state.result is not None for state in states):
                    continue
                if states and any(state.interrupted is None for state in states):
                    raise ValueError("an earlier game attempt is not settled/interrupted")
                attempt = max((state.attempt for state in states), default=-1) + 1
                jobs.append({"pair": pair, "leg": leg, "game": game, "attempt": attempt})
        jobs.sort(key=lambda row: (row["pair"]["id"] not in self.budget.started_pairs,
                                  self.plan["pairs"].index(row["pair"]), row["leg"]))
        return jobs

    def execute(self, cgroup_root, *, resume=False):
        if self.plan["profile"] in ("test-p16", "test-p192"):
            raise ValueError("P16/P192 execution awaits shared-budget, watchdog and live resource admission")
        assert_stage_binding(self.envelope, self.journal.rows)
        intent_rows = registered_intent_rows(self.journal.rows, self.out, self.plan["campaign"])
        assert_no_unreconciled_releases(self.journal.rows, intent_rows)
        current = topology.Topology.snapshot()
        saved = topology.Topology.from_record(self.plan["topology"])
        if current.to_record() != saved.to_record():
            raise ValueError("host topology/effective masks changed; freeze a new plan")
        if not self.out.is_absolute() or any((p / ".git").exists() for p in (self.out, *self.out.parents)):
            raise ValueError("external stage execution directory required")
        marker = self.out / "execution.json"
        if self.out.exists():
            if not resume or not marker.is_file() or json.loads(marker.read_text()) != {
                    "campaign": self.plan["campaign"], "plan_sha256": self.envelope["sha256"]}:
                raise ValueError("existing stage output is not this resumable execution")
        else:
            self.out.mkdir(parents=True)
            marker.write_bytes(ledger.canonical({"campaign": self.plan["campaign"], "plan_sha256": self.envelope["sha256"]}))
        require_settled_prior_jobs(self.journal.rows, self.instance_id, self.budget)
        prior_groups = []
        current_boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        for row in self.journal.rows:
            if (row["event"] == "campaign.cgroups" and row["data"].get("root") == str(cgroup_root)
                    and row["data"].get("instance_id") == self.instance_id and row["data"].get("boot_id") == current_boot):
                prior_groups.extend(row["data"].get("groups", {}).values())
                if row["data"].get("parent"):
                    prior_groups.append(row["data"]["parent"])
        if prior_groups:
            prior_cleanup = placement.cleanup_owned_groups(prior_groups, root=cgroup_root)
            self.append("campaign.prior_cgroup_cleanup", {"outcomes": prior_cleanup})
            if any(row.get("error") for row in prior_cleanup):
                raise RuntimeError("original owned cgroups are not safely settled; preserve them for audit")
        for state in self.results.games.values():
            if state.result is None and state.interrupted is None:
                self.append("game.interrupted", {"reason": "controller_failure", "evidence": "original group/session settled before resume"},
                            pair=state.pair, game=state.game, attempt=state.attempt)
        execution = sum(row["event"] == "campaign.stage_started" and row["data"].get("plan_sha256") == self.envelope["sha256"]
                        for row in self.journal.rows)
        launch = uuid.uuid4().hex[:16]
        self.append("campaign.stage_started", {"plan_sha256": self.envelope["sha256"], "stage": self.plan["stage"], "execution": execution,
                                              "launch_id": launch})
        original = set(os.sched_getaffinity(0))
        manager = None
        cleanup = []
        failure = None
        try:
            remote_audit = audit_remote_results(self.publisher, self.plan["campaign"], self.results)
            (self.out / f"remote-audit-{launch}.json").write_bytes(ledger.canonical(remote_audit))
            self.append("campaign.remote_result_audit", remote_audit)
            if remote_audit["uncertain"]:
                raise ValueError("uncertain remote completed result; preserve its evidence and do not replay its colour")
            namespace = self.plan["campaign"][:40] + "-" + self.plan["stage"] + "-" + ledger.digest({"plan": self.envelope["sha256"], "execution": execution, "launch": launch})[:12]
            self.append("campaign.cgroup_intent", {"root": str(cgroup_root), "namespace": namespace})
            manager = placement.CgroupSlots(cgroup_root, namespace)
            slots = []
            for row in self.plan["slots"]:
                slot = topology.Slot(**{**row, "cpus": tuple(row["cpus"]),
                                       "physical_cores": tuple(tuple(key) for key in row["physical_cores"]),
                                       "memory_nodes": tuple(row["memory_nodes"])})
                slots.append(slot)
            preflight = None
            if self.plan["profile"] in ("test-p16", "test-p192"):
                # No scored execution is permitted by the outer guard until a
                # real overhead evidence owner and the global GO fence exist.
                try:
                    from . import memory_observation
                except ImportError:
                    import memory_observation
                capacity, preflight = capture_league_preflight(slots, cgroup_root, self.memory_preflight,
                                                              memory_observation.observe_capacity)
                self.append("campaign.memory_capacity_observed", capacity)
            groups, memory_admission = create_league_cgroups(
                manager, slots, list(self.players.values()), self.plan["profile"],
                memory_preflight=preflight)
            if memory_admission is not None:
                self.append("campaign.memory_preflight", memory_admission)
            self.slots = {slot.id: slot for slot in slots}
            self.append("campaign.cgroups", {"root": str(cgroup_root), "namespace": namespace, "groups": groups,
                                             "parent": manager.parent_record(), "instance_id": self.instance_id,
                                             "boot_id": current_boot})
            os.sched_setaffinity(0, set(self.plan["controller_cpus"]))
            if set(os.sched_getaffinity(0)) != set(self.plan["controller_cpus"]):
                raise ValueError("controller reserve affinity was not applied")
            # Publisher and reader threads start after this one-time pin so
            # they inherit reserved cores, not scored engine cores.
            self.outbox = durability.DurableOutbox(self.out / f"outbox-{execution:03d}-{launch}", self.publisher)
            plan_ticket = self.outbox.submit(f"{self.plan['campaign']}/plans/{self.envelope['sha256']}.json",
                                              ledger.canonical(self.envelope))
            plan_ticket.result(timeout=125)
            self.enqueued = 0  # Republish complete hash-chain history on first stage/resume.
            self.replicate(force=True)
            for state in list(self.results.games.values()):
                if state.result is not None and state.remote is None and state.interrupted is None:
                    self.queue_result(state.game, state.attempt, state.result)
            self.acknowledge_results(wait=True)
            wave_number = 0
            while self.pending():
                if self.lease_verifier is None:
                    raise ValueError("scored execution requires a fresh actual AWS owned-lease verification port")
                lease = self.lease_verifier(self.budget)
                if not isinstance(lease, dict) or lease.get("verified") is not True or lease.get("instance_id") != self.instance_id:
                    raise ValueError("actual live instance ownership was not verified")
                self.append("campaign.lease_verified", lease)
                remaining = self.budget.admit(time.time(), 0).remaining_seconds
                if remaining <= 0:
                    self.append("campaign.budget_drain", {"reason": "no safe runtime remains"})
                    break
                candidates = self.pending()
                admitted = []
                proposed_pairs = set(self.budget.started_pairs)
                for row in candidates:
                    if row["pair"]["id"] not in proposed_pairs and len(proposed_pairs) >= self.budget.policy.max_pairs:
                        continue
                    horizon = 0 if row["pair"]["id"] in self.budget.started_pairs else (10800 if len(slots) % 2 else 5400)
                    if self.budget.admit(time.time(), horizon, pair_id=row["pair"]["id"]).allowed:
                        admitted.append(row)
                        proposed_pairs.add(row["pair"]["id"])
                    if len(admitted) == len(slots):
                        break
                if not admitted:
                    self.append("campaign.budget_drain", {"reason": "new pairs cannot reserve both colour legs"})
                    break
                try:
                    from .wave import WaveJob
                except ImportError:
                    from wave import WaveJob
                jobs, metadata = [], []
                for index, row in enumerate(admitted):
                    slot = slots[(index + wave_number) % len(slots)]
                    pair, leg, attempt = row["pair"], row["leg"], row["attempt"]
                    white, black = pair["players"] if leg == 0 else tuple(reversed(pair["players"]))
                    game = row["game"]
                    identity = {"leg": leg, "white": white, "black": black, "opening_id": pair["opening"]["id"],
                                "opening_moves": pair["opening"]["moves"], "opening_sha256": ledger.digest(pair["opening"]["moves"]),
                                "bank_id": self.plan["bank_id"], "profile": self.plan["profile"],
                                "artifact_sha256": {name: self.players[name].sha256 for name in (white, black)},
                                "runner_sha256": self.plan["runner"]["sha256"], "slot": slot.id, "wave": wave_number}
                    job_id = game + f".a{attempt:03d}.x{launch}"
                    job_out = self.out / "jobs" / game / f"attempt-{attempt:03d}-launch-{launch}"
                    slot_file = self.out / f"placement-{launch}-{wave_number:03d}-{slot.id}.json"
                    slot_file.write_bytes(ledger.canonical({"slot": slot.to_record(), "cgroup": groups[slot.id],
                                                           "saved_ancestor_cpus": list(saved.allowed_cpus)}))
                    runner_argv = fastchess.single_game_argv(bundle_path(self.bundle, self.plan["runner"]["path"]),
                        fastchess.EngineCommand(white, (str(self.players[white].path),)),
                        fastchess.EngineCommand(black, (str(self.players[black].path),)),
                        opening_pgn=bundle_path(self.bundle, self.plan["opening_pgn"]), opening_start=pair["opening_index"], out=job_out)
                    argv = (sys.executable, str(HERE / "placement.py"), "--slot", str(slot_file),
                            "--record", str(self.out / f"placement-observed-{job_id}.json"), "--", *runner_argv)
                    start_job = {"campaign": self.plan["campaign"], "pair": pair["id"], "game": game,
                                 "attempt": attempt, "slot": slot.id, "wave": wave_number,
                                 "artifacts": [white, black], "opening": pair["opening"]["id"], "launch_id": launch,
                                 "attempt_id": attempt_identity(self.plan["campaign"], pair["id"], game, attempt, job_id)}
                    job = WaveJob(job_id, tuple(argv), {"TZ": "UTC", "LANG": "C.UTF-8"}, start_job, job_out)
                    jobs.append(job)
                    self.job_specs[job_id] = {"pair": pair["id"], "game": game, "attempt": attempt, "identity": identity,
                                              "placement_record": self.out / f"placement-observed-{job_id}.json",
                                              "placement_cgroup": groups[slot.id]}
                    self.tail[job_id] = {"offset": 0, "partial": "", "trace": TraceState(pair["opening"]["moves"], white, black)}
                    self.append("campaign.launch_allocated", {"game": game, "attempt": attempt, "launch_id": job_id,
                                "directory": str(job_out.relative_to(self.out)), "plan_sha256": self.envelope["sha256"],
                                "identity": identity})
                    metadata.append(row)

                def release():
                    self.outbox.check()
                    for job in jobs:
                        observed = self.ready[job.identity]
                        spec = self.job_specs[job.identity]["identity"]
                        if self.plan["profile"] in ("test-p16", "test-p192"):
                            group = self.job_specs[job.identity]["placement_cgroup"]
                            live_group = placement.verify_cgroup_live(group)
                            self.append("game.cgroup_pre_go", live_group, pair=self.job_specs[job.identity]["pair"],
                                        game=self.job_specs[job.identity]["game"], attempt=self.job_specs[job.identity]["attempt"])
                        fresh = placement.observe_game_engines(observed["pid"],
                            [self.players[name].native_sha256 for name in (spec["white"], spec["black"])],
                            self.slots[spec["slot"]].cpus, expected_start_ticks=observed["start_ticks"])
                        owners = lambda proof: sorted((row["pid"], row["start_ticks"], row["native_sha256"]) for row in proof["engines"])
                        if owners(fresh) != owners(observed["engines"]):
                            raise ValueError("a READY engine owner changed before the global GO admission")
                        self.append("game.release_observation", fresh, pair=self.job_specs[job.identity]["pair"],
                                    game=self.job_specs[job.identity]["game"], attempt=self.job_specs[job.identity]["attempt"])
                    for pair_id in dict.fromkeys(row["pair"]["id"] for row in metadata):
                        if pair_id not in self.budget.started_pairs:
                            horizon = 10800 if len(slots) % 2 else 5400
                            if not self.budget.admit(time.time(), horizon, pair_id=pair_id).allowed:
                                return False
                            self.append("budget.pair_started", {"pair_id": pair_id, "reserved_wall_seconds": horizon})
                    if self.budget.admit(time.time(), 0).remaining_seconds <= 0:
                        return False
                    self.replicate(force=True)
                    return True

                remaining = min(remaining, self.budget.admit(time.time(), 0).remaining_seconds)
                # All jobs are armed before any Popen, including games waiting
                # for their peer in a parallel wave. A missing/failed arm yields
                # no completed performance scope and never a clean claim.
                for job in jobs:
                    key = self._gc_scope_key(job)
                    if key is not None:
                        try:
                            _COOPERATIVE_GC_TRACKER.arm(key)
                        except (ValueError, TypeError):
                            _COOPERATIVE_GC_TRACKER.forget(key)
                try:
                    observations = self.executor.run_wave(jobs, wall_seconds=remaining, release_callback=release, on_event=self.event)
                finally:
                    for job in jobs:
                        key = self._gc_scope_key(job)
                        if key is not None:
                            _COOPERATIVE_GC_TRACKER.forget(key)
                        getattr(self, "_gc_scope_bindings", {}).pop(job.identity, None)
                # Event callbacks may have failed and been disabled. Preserve
                # returned live/unknown ownership before any fallible trace
                # parsing can prevent this final admission check.
                for observation in observations:
                    identity = observation.get("identity", observation.get("id"))
                    if release_unresolved(observation):
                        if identity not in self.uncertain_releases:
                            job = next(job for job in jobs if job.identity == identity)
                            spec = self.job_specs[identity]
                            keys = {name: spec[name] for name in ("pair", "game", "attempt")}
                            self.quarantine_release(job, observation, keys)
                    if not physically_settled(observation):
                        job = next(job for job in jobs if job.identity == identity)
                        self.record_unsettled(job, observation)
                if self.unsettled:
                    self.replicate(force=True)
                    raise RuntimeError("a launch owner is not physically settled; no subsequent wave may initialize")
                if self.uncertain_releases:
                    self.replicate(force=True)
                    raise RuntimeError("release or game evidence is unreconciled; no subsequent wave may initialize")
                for job in jobs:
                    while (job.out / "raw.log").exists() and (job.out / "raw.log").stat().st_size > self.tail[job.identity]["offset"]:
                        self.observe_raw(job)
                for observation in observations:
                    spec = self.job_specs[observation.get("identity", observation.get("id"))]
                    state = self.results.games.get((spec["game"], spec["attempt"]))
                    if state is not None and state.result is None and state.interrupted is None:
                        settled = physically_settled(observation)
                        if settled:
                            keys = {name: spec[name] for name in ("pair", "game", "attempt")}
                            self.append("game.process_completed", observation, **keys)
                            self.append("game.interrupted", {"reason": "protocol_harness_error", "runner_observation": observation}, **keys)
                self.acknowledge_results(wait=True)
                self.replicate(force=True)
                (self.out / f"wave-{execution:03d}-{launch}-{wave_number:03d}.json").write_bytes(ledger.canonical(observations))
                if any(row.get("wave_aborted") for row in observations):
                    break
                wave_number += 1
            self.acknowledge_results(wait=True)
            self.replicate(force=True)
            for ticket in self.replication_tickets:
                ticket.result(timeout=125)
        except BaseException as error:
            failure = {"type": type(error).__name__, "error": str(error)}
            self.append("campaign.controller_error", failure)
        finally:
            if self.outbox is not None:
                try:
                    self.outbox.close(timeout=125)
                except BaseException as error:
                    cleanup.append({"component": "publisher", "error": str(error)})
            if manager is not None:
                cleanup.extend(manager.close())
            if self.unsettled:
                cleanup.append({"component": "runner", "unsettled_launches": sorted(self.unsettled)})
            os.sched_setaffinity(0, original)
        summary = collect.collect(self.journal.rows, self.plan["campaign"],
                                  expected_pairs=[row["id"] for row in self.plan["pairs"]], profile=self.plan["profile"],
                                  player_families={name: artifact.family for name, artifact in self.players.items()})
        report = {"format": "rove4k-stage-run-v1", "plan_sha256": self.envelope["sha256"],
                  "complete": summary["campaign_stage_complete"] and failure is None and not cleanup,
                  "summary": summary, "failure": failure, "cleanup_errors": cleanup,
                  "budget": self.budget.as_dict(time.time()), "scope": self.plan["scope"]}
        (self.out / f"run-{execution:03d}-{launch}.json").write_bytes(ledger.canonical(report) + b"\n")
        return report


def physically_settled(observation):
    if observation.get("readers_done") is not True or observation.get("remaining_processes") != []:
        return False
    if observation.get("pid") is None:
        return observation.get("pgid") is None and observation.get("session") is None and observation.get("returncode") is None
    return type(observation.get("returncode")) is int


def assert_stage_binding(envelope, rows):
    body = envelope["content"]
    if any(row["event"] == "campaign.stage_started" and row["data"].get("stage") == body["stage"]
           and row["data"].get("plan_sha256") != envelope["sha256"] for row in rows):
        raise ValueError("campaign stage is already bound to another full artifact/native cohort; use a fresh campaign or distinct authorized stage")


def audit_remote_results(publisher, campaign, results):
    """Reject a remote completed colour absent from the verified journal.

    This also protects imports from an older/non-FIFO publisher. Recovery does
    not manufacture the missing original start, READY, placement or result.
    """
    pattern = re.compile(re.escape(campaign) + r"/results/([A-Za-z0-9_.-]+)/attempt-(\d{3,})/([a-f0-9]{64})\.json")
    known, uncertain = [], []
    keys = publisher.list_keys(campaign + "/results")
    if len(keys) > 4096:
        raise ValueError("remote result namespace exceeds the bounded campaign")
    for key in keys:
        match = pattern.fullmatch(key)
        if match is None:
            raise ValueError("unrecognized object in the owned result namespace")
        raw = publisher.read_verified(key, expected_sha=match[3])
        data = json.loads(raw)
        if ledger.canonical(data) != raw:
            raise ValueError("remote result bytes are not the canonical published contract")
        state = results.games.get((match[1], int(match[2])))
        if state is not None and state.result is not None and state.result == data and state.result_sha256 == match[3]:
            known.append(key)
            continue
        preserved = []
        for kind in ("pgn", "raw"):
            body_key, expected = data.get(kind + "_object_key"), data.get(kind + "_sha256")
            if (not isinstance(body_key, str) or not body_key.startswith(campaign + "/games/") or
                    not isinstance(expected, str) or not SHA.fullmatch(expected)):
                raise ValueError("uncertain remote result lacks bounded owned evidence identities")
            body = publisher.read_verified(body_key, expected_sha=expected, max_bytes=128 << 20)
            preserved.append({"kind": kind, "object_key": body_key, "sha256": expected, "bytes": len(body)})
        uncertain.append({"game": match[1], "attempt": int(match[2]), "object_key": key,
                          "sha256": match[3], "evidence": preserved,
                          "reason": "original completed result/start/READY journal prefix is unavailable or differs"})
    return {"known": known, "uncertain": uncertain,
            "scope": "verified remote object audit; uncertain colours must not be replayed or fabricated"}


def restore_remote_journal(publisher, campaign, out):
    """Recover a complete verified prefix, deduplicating overlapping snapshots.

    A missing last cloud chunk stays missing. Recovery neither invents an event
    nor promotes a queued/unacknowledged result into an accepted game.
    """
    ID(campaign)
    out = external_new(out)
    out.mkdir(parents=True)
    key_pattern = re.compile(re.escape(campaign) + r"/journal/(\d{9})-(\d{9})-([0-9a-f]{64})\.jsonl")
    keys = publisher.list_keys(campaign + "/journal")
    if not keys or len(keys) > 100000:
        raise ValueError("a bounded nonempty remote journal prefix is required")
    rows, total = {}, 0
    for key in keys:
        match = key_pattern.fullmatch(key)
        if match is None:
            raise ValueError("unexpected object in the owned journal namespace")
        raw = publisher.read_verified(key, expected_sha=match[3], max_bytes=4 << 20)
        total += len(raw)
        if total > 16 << 30:
            raise ValueError("recovery exceeded the finite campaign journal bound")
        block = raw.splitlines(keepends=True)
        if not block or any(not row.endswith(b"\n") or len(row) > 1 << 20 for row in block):
            raise ValueError("remote journal contains an incomplete or excessive event")
        parsed = [json.loads(row) for row in block]
        if [row["seq"] for row in parsed] != list(range(int(match[1]), int(match[2]) + 1)):
            raise ValueError("remote journal range differs from its immutable key")
        for row in parsed:
            sequence = row["seq"]
            if sequence in rows and rows[sequence] != row:
                raise ValueError("remote journal snapshots conflict at one sequence")
            rows[sequence] = row
    if sorted(rows) != list(range(len(rows))):
        raise ValueError("remote journal has a missing prefix or gap; preserve it for audit")
    destination = out / "campaign.jsonl"
    with destination.open("xb") as output:
        for sequence in range(len(rows)):
            output.write(ledger.canonical(rows[sequence]) + b"\n")
        output.flush()
        os.fsync(output.fileno())
    checked = ledger.read_journal(destination, campaign)
    results = ledger.CampaignResults.replay(campaign, checked)
    budget.CampaignBudget.replay(campaign, checked)
    audit = audit_remote_results(publisher, campaign, results)
    (out / "remote-result-audit.json").write_bytes(ledger.canonical(audit))
    if audit["uncertain"]:
        raise ValueError("uncertain remote completed colour; verified objects preserved and automatic replay blocked")
    return {"journal": str(destination), "events": len(checked), "last_sha256": checked[-1]["sha256"],
            "objects": len(keys), "verified_download_bytes": total, "sha256": registry.file_sha(destination),
            "scope": "verified cloud prefix only; live-owner and lease checks still required before resume"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    freeze = actions.add_parser("plan", help="freeze an actual qualified partial or complete TEST cohort")
    freeze.add_argument("--campaign", required=True)
    freeze.add_argument("--profile", choices=TEST_PROFILES, required=True)
    freeze.add_argument("--stage", choices=("broad", "high", "update1", "update2"), default="broad")
    freeze.add_argument("--registry", type=Path, required=True)
    freeze.add_argument("--bank", type=Path, required=True)
    freeze.add_argument("--bank-sha256", required=True)
    freeze.add_argument("--runner", type=Path, required=True)
    freeze.add_argument("--runner-receipt", type=Path, required=True)
    freeze.add_argument("--out", type=Path, required=True)
    freeze.add_argument("--selected-id", action="append")
    freeze.add_argument("--repeats", type=int, default=1, choices=(1, 2))
    freeze.add_argument("--broad-plan", type=Path)
    freeze.add_argument("--broad-journal", type=Path)
    inspect = actions.add_parser("dry-run", help="verify a frozen bundle without executing engines or AWS calls")
    inspect.add_argument("--plan", type=Path, required=True)
    execute = actions.add_parser("run", help="run on the already allocated, verified owned instance")
    execute.add_argument("--plan", type=Path, required=True)
    execute.add_argument("--aws-plan", type=Path, required=True)
    execute.add_argument("--journal", type=Path, required=True)
    execute.add_argument("--out", type=Path, required=True)
    execute.add_argument("--cgroup-root", type=Path, required=True)
    execute.add_argument("--resume", action="store_true")
    recover = actions.add_parser("restore", help="read checksum-verified owned cloud journal objects")
    recover.add_argument("--aws-plan", type=Path, required=True)
    recover.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "plan":
        envelope = freeze_plan(args.campaign, args.profile, args.registry, args.bank, args.bank_sha256,
            args.runner, args.runner_receipt, args.out, stage=args.stage, selected_ids=args.selected_id,
            repeats=args.repeats, broad_plan=args.broad_plan, broad_journal=args.broad_journal)
        result = {"plan": str(args.out / "plan.json"), "sha256": envelope["sha256"],
                  "pairs": len(envelope["content"]["pairs"]), "players": len(envelope["content"]["registry"]["players"]),
                  "paid_launch_performed": False}
    elif args.action == "dry-run":
        envelope, players = load_plan(args.plan)
        content = envelope["content"]
        result = {"plan_sha256": envelope["sha256"], "campaign": content["campaign"],
                  "profile": content["profile"], "stage": content["stage"], "pairs": len(content["pairs"]),
                  "games": len(content["pairs"]) * 2, "slots": len(content["slots"]),
                  "cohort": [row["artifact"].identity() for row in players], "scope": content["scope"],
                  "engine_execution_performed": False, "aws_calls_performed": False}
    else:
        if args.action == "run":
            envelope, _ = load_plan(args.plan)
            if envelope["content"]["profile"] in ("test-p16", "test-p192"):
                raise ValueError("P16/P192 execution awaits shared-budget, watchdog and live resource admission")
        try:
            from . import aws
        except ImportError:
            import aws
        config, _ = json_input(args.aws_plan)
        aws_plan = aws.AWSPlan.from_dict(config)
        client = aws.AWSCLI(aws_plan.region)
        publisher = aws.S3Evidence(client, aws_plan, args.out)
        if args.action == "restore":
            result = restore_remote_journal(publisher, aws_plan.campaign_id, args.out)
        else:
            envelope, _ = load_plan(args.plan)
            if envelope["content"]["campaign"] != aws_plan.campaign_id:
                raise ValueError("execution plan and AWS ownership campaign differ")
            with ledger.Journal(args.journal, aws_plan.campaign_id) as journal:
                assert_stage_binding(envelope, journal.rows)
                state = budget.CampaignBudget.replay(aws_plan.campaign_id, journal.rows)
                aws.verify_owned_lease(client, aws_plan, state, time.time(), caller_kind="instance")
                controller = StageController(args.plan, args.out, journal, publisher, state,
                    lease_verifier=lambda current: aws.verify_owned_lease(client, aws_plan, current, time.time(), caller_kind="instance"))
                result = controller.execute(args.cgroup_root, resume=args.resume)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 2 if args.action == "run" and not result["complete"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
