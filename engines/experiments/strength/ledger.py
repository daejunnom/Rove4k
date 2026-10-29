"""Fsynced campaign journal and idempotent two-colour result reduction."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def valid_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", value):
        raise ValueError("invalid campaign job identifier")
    return value


def valid_boot_id(value):
    return type(value) is str and re.fullmatch(
        r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", value) is not None


def cooperative_gc_scope_id(campaign, pair, game, attempt, identity):
    """Bind a controller-observed cooperative-GC interval to one physical attempt.

    This is a content identity, not host attestation.  The owner must journal
    its scope open and close and cover all of its explicit cooperative calls.
    """
    for value in (campaign, pair, game):
        valid_id(value)
    if type(attempt) is not int or attempt < 0:
        raise ValueError("cooperative GC requires a nonnegative attempt")
    names = {"instance_id", "boot_id", "launch_pid", "launch_start_ticks",
             "observer_pid", "observer_start_ticks", "scope_start_ns"}
    if type(identity) is not dict or set(identity) != names:
        raise ValueError("cooperative GC scope identity differs")
    valid_id(identity["instance_id"])
    if not valid_boot_id(identity["boot_id"]):
        raise ValueError("cooperative GC requires the observed boot identity")
    for name in ("launch_pid", "observer_pid"):
        if type(identity[name]) is not int or not 0 < identity[name] <= (1 << 31) - 1:
            raise ValueError("cooperative GC requires positive process IDs")
    for name in ("launch_start_ticks", "observer_start_ticks", "scope_start_ns"):
        if type(identity[name]) is not int or not 0 <= identity[name] <= (1 << 63) - 1:
            raise ValueError("cooperative GC requires nonnegative process and interval observations")
    return digest({"format": "rove4k-cooperative-gc-scope-v1", "campaign": campaign,
                   "pair": pair, "game": game, "attempt": attempt, "identity": identity})


def external(path):
    path = Path(path)
    if not path.is_absolute() or path.suffix != ".jsonl":
        raise ValueError("journal requires an absolute external JSONL path")
    if any(token in path.name.lower() for token in ("credential", ".env", "inventory", "service-account", "api_key")):
        raise ValueError("protected input cannot be a campaign journal")
    for candidate in (path, *path.parents):
        if candidate.is_symlink() or (hasattr(candidate, "is_junction") and candidate.is_junction()):
            raise ValueError("journal must not follow links")
        if (candidate / ".git").exists():
            raise ValueError("journal must remain outside Git")
    return path


def read_journal(path, campaign):
    previous, sequence = "0" * 64, 0
    rows = []
    with external(path).open("rb") as source:
        for line in source:
            if len(line) > 1 << 20 or not line.endswith(b"\n"):
                raise ValueError("journal has an excessive or incomplete event; preserve it")
            row = json.loads(line)
            claimed = row.pop("sha256", None)
            if (row.get("format") != "rove4k-campaign-v1" or row.get("campaign") != campaign or
                    row.get("seq") != sequence or row.get("previous_sha256") != previous or digest(row) != claimed):
                raise ValueError("journal identity/order/hash chain differs")
            row["sha256"] = claimed
            rows.append(row)
            previous, sequence = claimed, sequence + 1
    return rows


class Journal:
    """One controller owns the writer for the journal's entire lifetime."""
    def __init__(self, path, campaign):
        self.path, self.campaign = external(path), valid_id(campaign)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("a+b", buffering=0)
        try:
            if os.name == "posix":
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.rows = read_journal(self.path, self.campaign)
            self.last = self.rows[-1]["sha256"] if self.rows else "0" * 64
            self.offset = self.path.stat().st_size
            stat = os.fstat(self.file.fileno())
            self.identity = stat.st_dev, stat.st_ino
        except BaseException:
            self.file.close()
            raise

    def append(self, event, data=None, *, pair=None, game=None, attempt=None, time_utc=None):
        stat = self.path.stat()
        if self.file.closed or stat.st_size != self.offset or (stat.st_dev, stat.st_ino) != self.identity:
            raise ValueError("journal writer or physical file identity changed")
        if not isinstance(event, str) or not event or len(event) > 80:
            raise ValueError("event name required")
        for value in (pair, game):
            if value is not None:
                valid_id(value)
        if attempt is not None and (type(attempt) is not int or attempt < 0):
            raise ValueError("nonnegative attempt required")
        timestamp = time_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if not isinstance(timestamp, str) or datetime.fromisoformat(timestamp.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("journal UTC timestamp requires an explicit timezone")
        if data is not None and not isinstance(data, dict):
            raise ValueError("journal event data must be an object")
        row = {"format": "rove4k-campaign-v1", "seq": len(self.rows), "event": event,
               "time_utc": timestamp, "campaign": self.campaign, "pair": pair,
               "game": game, "attempt": attempt, "data": {} if data is None else data,
               "previous_sha256": self.last}
        row["sha256"] = digest(row)
        body = canonical(row) + b"\n"
        if len(body) > 1 << 20:
            raise ValueError("event exceeds the bounded journal record")
        written = 0
        while written < len(body):
            count = self.file.write(body[written:])
            if type(count) is not int or count <= 0 or count > len(body) - written:
                raise OSError("journal record was not durably written; preserve its partial tail")
            written += count
        os.fsync(self.file.fileno())
        self.offset += len(body)
        self.rows.append(json.loads(body))
        self.last = row["sha256"]
        return json.loads(body)

    def close(self):
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, *error):
        self.close()


RESULT_REASONS = frozenset(("completed_chess_result", "engine_illegal", "engine_crash", "engine_time_loss"))
INFRA_REASONS = frozenset(("host_interruption", "controller_failure", "protocol_harness_error",
                           "budget_drain", "budget_termination", "user_cancel"))


def remote_identity(value):
    """Stable immutable object evidence, excluding retry receipt telemetry."""
    if isinstance(value, dict):
        return {name: remote_identity(item) for name, item in value.items()
                if name not in ("reused_existing", "acknowledged_at")}
    if isinstance(value, list):
        return [remote_identity(item) for item in value]
    return value


@dataclass
class GameState:
    pair: str
    game: str
    attempt: int
    spec: dict
    result: dict | None = None
    result_sha256: str | None = None
    remote: dict | None = None
    interrupted: str | None = None

    @property
    def accepted(self):
        return self.result is not None and self.remote is not None and self.interrupted is None


@dataclass
class CampaignResults:
    campaign: str
    games: dict = field(default_factory=dict)

    def apply(self, row):
        if row["campaign"] != self.campaign:
            raise ValueError("event belongs to another campaign")
        event, data = row["event"], row["data"]
        if not event.startswith("game."):
            return
        key = row["game"], row["attempt"]
        if event == "game.started":
            if type(data.get("leg")) is not int or data["leg"] not in (0, 1) or data.get("white") == data.get("black"):
                raise ValueError("two distinct players and explicit colour leg required")
            for name in ("white", "black", "opening_id", "profile"):
                valid_id(data[name])
            hashes = data.get("artifact_sha256", {})
            if set(hashes) != {data["white"], data["black"]} or any(
                    not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes.values()):
                raise ValueError("game requires the actual two artifact identities")
            if any(not isinstance(data.get(name), str) or not re.fullmatch(r"[0-9a-f]{64}", data[name])
                   for name in ("opening_sha256", "bank_id")):
                raise ValueError("game requires bound opening moves and bank identities")
            if key in self.games:
                if self.games[key].spec != data or self.games[key].pair != row["pair"]:
                    raise ValueError("duplicate game start changed its identity")
                return
            prior = [state for (game, _), state in self.games.items() if game == row["game"]]
            if not prior and row["attempt"] != 0:
                raise ValueError("first physical attempt must be zero")
            if prior and (any(state.result is not None or state.interrupted is None for state in prior)
                          or row["attempt"] != max(state.attempt for state in prior) + 1):
                raise ValueError("settle interrupted attempts; completed result cannot be replayed or sequence skipped")
            stable = lambda spec: {name: value for name, value in spec.items() if name not in ("slot", "wave")}
            if prior and any(stable(state.spec) != stable(data) for state in prior):
                raise ValueError("retry changed its artifact, opening, clock or resource identity")
            self.games[key] = GameState(row["pair"], row["game"], row["attempt"], json.loads(canonical(data)))
            return
        if key not in self.games:
            raise ValueError("result or interruption precedes actual game start")
        state = self.games[key]
        if state.pair != row["pair"]:
            raise ValueError("game pair identity changed")
        if event == "game.result":
            if data.get("result") not in ("1-0", "0-1", "1/2-1/2") or data.get("reason") not in RESULT_REASONS:
                raise ValueError("infrastructure abort is not a chess result")
            if state.interrupted:
                raise ValueError("interrupted attempt cannot later acquire a result")
            if any(data.get(name) != state.spec[name] for name in
                   ("white", "black", "opening_id", "opening_sha256", "bank_id", "profile", "artifact_sha256")):
                raise ValueError("result changed its started game identity")
            for kind in ("pgn", "raw"):
                if (not isinstance(data.get(kind + "_sha256"), str) or
                        not re.fullmatch(r"[0-9a-f]{64}", data[kind + "_sha256"]) or
                        not isinstance(data.get(kind + "_object_key"), str) or not data[kind + "_object_key"]):
                    raise ValueError("result requires its immutable PGN and raw UCI evidence")
            value = digest(data)
            if state.result_sha256 not in (None, value):
                raise ValueError("duplicate result changed accepted bytes")
            state.result, state.result_sha256 = json.loads(canonical(data)), value
        elif event == "game.remote_confirmed":
            if state.result is None or state.interrupted:
                raise ValueError("remote acknowledgement has no completed result")
            if (data.get("sha256") != state.result_sha256 or data.get("verified") is not True or
                    not isinstance(data.get("object_key"), str) or not data["object_key"]):
                raise ValueError("remote result acknowledgement is unbound or unverified")
            evidence = data.get("evidence")
            if not isinstance(evidence, list) or len(evidence) != 2:
                raise ValueError("remote acknowledgement requires both PGN and raw UCI objects")
            expected = {state.result[kind + "_object_key"]: state.result[kind + "_sha256"]
                        for kind in ("pgn", "raw")}
            if len(expected) != 2 or any(not isinstance(item, dict) for item in evidence):
                raise ValueError("remote required evidence has duplicate or malformed identities")
            observed = {}
            for item in evidence:
                key = item.get("object_key")
                if (not isinstance(key, str) or key in observed or key not in expected or
                        item.get("sha256") != expected[key] or item.get("verified") is not True or
                        any(item.get(name) != data.get(name) for name in ("backend", "bucket"))):
                    raise ValueError("remote required evidence is unbound or unverified")
                observed[key] = item["sha256"]
            if observed != expected:
                raise ValueError("remote required evidence differs from the completed result")
            if state.remote is not None and remote_identity(state.remote) != remote_identity(data):
                raise ValueError("duplicate remote acknowledgement changed")
            if state.remote is None:
                state.remote = json.loads(canonical(data))
        elif event == "game.interrupted":
            if data.get("reason") not in INFRA_REASONS or state.result is not None:
                raise ValueError("completed chess result cannot become an infrastructure interruption")
            if state.interrupted not in (None, data["reason"]):
                raise ValueError("duplicate interruption changed its cause")
            state.interrupted = data["reason"]

    @classmethod
    def replay(cls, campaign, rows):
        value = cls(campaign)
        for row in rows:
            value.apply(row)
        return value

    def pairs(self):
        grouped = {}
        for state in self.games.values():
            if state.accepted:
                grouped.setdefault(state.pair, {}).setdefault(state.spec["leg"], []).append(state)
        complete = []
        for pair, legs in sorted(grouped.items()):
            if set(legs) != {0, 1}:
                continue
            if any(len(values) != 1 for values in legs.values()):
                raise ValueError("pair has multiple accepted results for one colour leg")
            first, second = legs[0][0], legs[1][0]
            if (first.spec["white"] != second.spec["black"] or first.spec["black"] != second.spec["white"] or
                    first.spec["opening_id"] != second.spec["opening_id"] or
                    first.spec["opening_sha256"] != second.spec["opening_sha256"] or
                    first.spec["bank_id"] != second.spec["bank_id"] or
                    first.spec["profile"] != second.spec["profile"] or
                    first.spec.get("artifact_sha256") != second.spec.get("artifact_sha256")):
                raise ValueError("pair legs differ in opening, players, resource or artifacts")
            scores = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}
            points = scores[first.result["result"]] + 1.0 - scores[second.result["result"]]
            complete.append({"pair": pair, "first_player": first.spec["white"], "second_player": first.spec["black"],
                             "score": points, "opening_id": first.spec["opening_id"], "profile": first.spec["profile"],
                             "games": [first.game, second.game]})
        return complete
