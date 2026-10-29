"""Single-region conditional epoch and immutable intent records for a league.

This module does not grant GO, EC2 launch, retry, takeover, or termination
authority. A DynamoDB transaction cannot fence an already sent socket message
or an EC2 request. The selected table, account, IAM writer isolation, immutable
generation, clock, budget input, old hosts and recipient fencing must be
independently authenticated before this can participate in a scored league.
The budget check compares only the last recorded upper-bound snapshot. It is
not an independently verified invoice or a projection through the GO window.
When a quarantine append or its fsync itself fails, persistence of that marker
cannot be established; storage failure needs independent operator recovery.

The table is expected to have string keys ``campaign_id`` and ``record_id`` in
one home region. It must be dedicated to the league; bootstrap, deletion and
restore are deliberately outside this module. Do not apply TTL to these rows.
Every remote mutation is preceded by a separately locked, fsynced journal
intent; a failure leaves the instance and its restarted journal blocked. A
strong read returning no attempt while a write is in flight does not prove the
write failed. There is no automatic retry or acknowledgement-based recovery.
Even a read-only timeout or expired STS session currently causes durable
quarantine. A separately authenticated read-recheck/owner-handoff procedure
does not exist here, so normal long-running/OIDC recovery is not implemented.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import os
import re
import threading

try:
    from .ledger import Journal, digest, valid_id
    from .shared_coordinator import _OWNER_LOCK, _sync_journal_directories
except ImportError:
    from ledger import Journal, digest, valid_id
    from shared_coordinator import _OWNER_LOCK, _sync_journal_directories


_SHA = re.compile(r"[0-9a-f]{64}")
_REGION = re.compile(r"[a-z]{2}(?:-gov)?-[a-z]+-\d+")
_TABLE = re.compile(r"[A-Za-z0-9_.-]{3,255}")
_MAX_EPOCH = 2**63 - 2
_CAP_MICROS = 120_000_000


class FenceConflict(ValueError):
    """The local snapshot or an explicit conditional write did not match."""


class FenceUncertain(RuntimeError):
    """A journal or remote operation may have committed; never retry it."""


def _sha(value):
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ValueError("a lowercase SHA-256 identity is required")
    return value


def _number(value, name, maximum=_MAX_EPOCH):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(name + " must be a bounded nonnegative integer")
    return value


@dataclass(frozen=True)
class EpochHead:
    epoch: int
    revision: int
    owner: str
    generation: str
    mode: str
    budget_head: str
    budget_upper_micros: int

    def __post_init__(self):
        _number(self.epoch, "epoch")
        _number(self.revision, "revision")
        _sha(self.owner)
        _sha(self.generation)
        _sha(self.budget_head)
        if self.mode not in ("active", "draining"):
            raise ValueError("unknown epoch mode")
        _number(self.budget_upper_micros, "budget upper micros")


@dataclass(frozen=True)
class AttemptIntent:
    attempt_id: str
    action: str
    subject_id: str
    job_sha256: str
    host_sha256: str
    request_sha256: str
    not_before_utc_ms: int
    expires_utc_ms: int

    def __post_init__(self):
        valid_id(self.attempt_id)
        valid_id(self.subject_id)
        if self.action not in ("launch", "go"):
            raise ValueError("intent action must be launch or go")
        for value in (self.job_sha256, self.host_sha256, self.request_sha256):
            _sha(value)
        _number(self.not_before_utc_ms, "window start")
        _number(self.expires_utc_ms, "window end")
        if not 0 < self.expires_utc_ms - self.not_before_utc_ms <= 60_000:
            raise ValueError("intent window must be positive and at most 60 seconds")


def _s(value):
    return {"S": value}


def _n(value):
    return {"N": str(value)}


def _parse_s(item, name):
    value = item.get(name)
    if not isinstance(value, dict) or set(value) != {"S"} or not isinstance(value["S"], str):
        raise ValueError("invalid DynamoDB string attribute: " + name)
    return value["S"]


def _parse_n(item, name):
    value = item.get(name)
    if not isinstance(value, dict) or set(value) != {"N"} or not isinstance(value["N"], str):
        raise ValueError("invalid DynamoDB numeric attribute: " + name)
    raw = value["N"]
    if len(raw) > 19 or not re.fullmatch(r"0|[1-9][0-9]*", raw):
        raise ValueError("noncanonical DynamoDB integer: " + name)
    return _number(int(raw), name)


class DynamoEpochStore:
    """Journaled conditional records; externally supervised and fail-closed.

    ``journal`` is exclusively locked and dedicated to this store. It must be
    externally protected against rollback and replacement; its hash chain is
    not an independent trust anchor. No method establishes a trusted clock,
    validates IAM, proves old owners quiescent, or dispatches an external GO.
    """

    provides_go_authority = False
    provides_launch_authority = False
    provides_termination_authority = False

    def __init__(self, client, *, table, account, region, campaign, generation, journal, root_head):
        if os.name != "posix" or not isinstance(journal, Journal):
            raise ValueError("a locked POSIX journal is required")
        if (not isinstance(table, str) or not _TABLE.fullmatch(table)
                or not isinstance(account, str) or not re.fullmatch(r"[0-9]{12}", account)
                or not isinstance(region, str) or not _REGION.fullmatch(region)
                or getattr(client, "region", None) != region):
            raise ValueError("explicit table, account and single home region required")
        self.campaign, self.generation = valid_id(campaign), _sha(generation)
        if journal.campaign != self.campaign:
            raise ValueError("journal campaign differs")
        if not isinstance(root_head, EpochHead) or root_head.generation != self.generation:
            raise ValueError("independently supplied root epoch head required")
        self.client, self.table, self.account, self.region, self.journal = client, table, account, region, journal
        self.identity = digest({"format": "rove4k-league-epoch-v1", "table": table, "account": account,
                                "region": region, "campaign": campaign, "generation": generation})
        self._lock, self._pending, self._blocked = threading.Lock(), None, False
        self._quarantined = False
        self._root, self._head = root_head, root_head
        self._attempts, self._subjects = set(), set()
        try:
            # Share the existing coordinator's process lock. Finish establishing
            # the dedicated genesis while holding it so another coordinator
            # cannot see the same Journal object as empty and append its genesis.
            with _OWNER_LOCK:
                if (getattr(journal, "_league_epoch_owner", None) is not None
                        or getattr(journal, "_shared_coordinator_owner", None) is not None):
                    raise ValueError("journal already belongs to a coordinator")
                journal._league_epoch_owner = self
                _sync_journal_directories(journal)
                self._restore_journal()
            try:
                self._account()
                actual = self._read_remote_head()
            except Exception as error:
                self._quarantine(None)
                raise FenceUncertain("epoch head or caller identity unavailable; preserve the journal") from error
            if actual != self._head:
                self._quarantine(actual)
        except BaseException:
            with _OWNER_LOCK:
                if getattr(journal, "_league_epoch_owner", None) is self:
                    del journal._league_epoch_owner
            raise

    @property
    def blocked(self):
        return self._blocked

    def _account(self):
        response = self.client.call("sts", "get-caller-identity", {})
        if not isinstance(response, dict) or response.get("Account") != self.account:
            raise ValueError("AWS caller account differs from the declared league account")

    def _restore_journal(self):
        rows = self.journal.rows
        if not rows:
            self.journal.append("epoch.genesis", {"identity": self.identity, "root_head": asdict(self._root)})
            return
        if (rows[0]["event"] != "epoch.genesis" or digest(rows[0]["data"])
                != digest({"identity": self.identity, "root_head": asdict(self._root)})):
            raise ValueError("epoch journal genesis differs")
        pending_operation = None
        for row in rows[1:]:
            name, data = row["event"], row["data"]
            if self._quarantined:
                raise ValueError("epoch journal continued after quarantine")
            if name == "epoch.intent":
                if (self._pending is not None or not isinstance(data, dict)
                        or set(data) != {"operation_sha256", "operation"}
                        or data["operation_sha256"] != digest(data["operation"])):
                    raise ValueError("epoch journal contains an invalid or overlapping intent")
                self._pending = data["operation_sha256"]
                pending_operation = data["operation"]
                self._next_head(pending_operation, self._head)
            elif name == "epoch.commit":
                if (self._pending is None or not isinstance(data, dict)
                        or set(data) != {"operation_sha256", "head"}
                        or data["operation_sha256"] != self._pending):
                    raise ValueError("epoch commit does not match a preceding intent")
                target = self._next_head(pending_operation, self._head)
                if digest(data["head"]) != digest(asdict(target)):
                    raise ValueError("epoch commit head differs from its intent")
                self._remember(pending_operation)
                self._head = target
                self._pending = None
                pending_operation = None
            elif name == "epoch.quarantine":
                if (not isinstance(data, dict) or set(data) != {"reason", "expected", "observed"}
                        or data["reason"] not in ("head-differs", "head-unavailable")
                        or digest(data["expected"]) != digest(asdict(self._head))):
                    raise ValueError("invalid epoch quarantine record")
                if data["reason"] == "head-unavailable":
                    if data["observed"] is not None:
                        raise ValueError("unavailable head must not contain an observation")
                else:
                    if not isinstance(data["observed"], dict):
                        raise ValueError("invalid observed epoch head")
                    try:
                        observed = EpochHead(**data["observed"])
                    except TypeError as error:
                        raise ValueError("invalid observed epoch head") from error
                    if observed == self._head:
                        raise ValueError("quarantine did not identify a head mismatch")
                self._quarantined = True
            else:
                raise ValueError("unknown event in dedicated epoch journal")
        self._blocked = self._pending is not None or self._quarantined

    def _quarantine(self, actual):
        self._blocked = True
        if self._quarantined:
            return
        try:
            self.journal.append("epoch.quarantine", {"reason": "head-unavailable" if actual is None else "head-differs",
                                                     "expected": asdict(self._head),
                                                     "observed": None if actual is None else asdict(actual)})
        except Exception as error:
            raise FenceUncertain("head mismatch could not be journaled; preserve the journal") from error
        self._quarantined = True

    def _key(self, name):
        return {"campaign_id": _s(self.campaign), "record_id": _s(name)}

    def _decode_head(self, item):
        names = {"campaign_id", "record_id", "generation", "epoch", "revision", "owner", "mode",
                 "budget_head", "budget_upper_micros"}
        if not isinstance(item, dict) or set(item) != names:
            raise ValueError("epoch head schema differs")
        if _parse_s(item, "campaign_id") != self.campaign or _parse_s(item, "record_id") != "epoch#head":
            raise ValueError("epoch head key differs")
        head = EpochHead(_parse_n(item, "epoch"), _parse_n(item, "revision"), _parse_s(item, "owner"),
                         _parse_s(item, "generation"), _parse_s(item, "mode"), _parse_s(item, "budget_head"),
                         _parse_n(item, "budget_upper_micros"))
        if head.generation != self.generation:
            raise ValueError("epoch head generation differs")
        return head

    def _read_remote_head(self):
        response = self.client.call("dynamodb", "get-item", {"TableName": self.table,
                                    "Key": self._key("epoch#head"), "ConsistentRead": True})
        if not isinstance(response, dict) or "Item" not in response:
            raise ValueError("pre-provisioned epoch head is unavailable")
        return self._decode_head(response["Item"])

    def read_head(self):
        with self._lock:
            try:
                self._account()
                actual = self._read_remote_head()
            except Exception as error:
                self._quarantine(None)
                raise FenceUncertain("epoch head or caller identity unavailable; preserve the journal") from error
            if actual != self._head:
                self._quarantine(actual)
            return actual

    def inspect_attempt(self, attempt_id):
        """A missing row remains unresolved, including for an in-flight write."""
        valid_id(attempt_id)
        self._account()
        response = self.client.call("dynamodb", "get-item", {"TableName": self.table,
                                    "Key": self._key("attempt#" + attempt_id), "ConsistentRead": True})
        if not isinstance(response, dict):
            raise ValueError("attempt lookup returned an invalid response")
        if "Item" not in response:
            return {"state": "unresolved", "present": False, "authorizes_go": False, "authorizes_launch": False}
        item = response["Item"]
        if not isinstance(item, dict) or item.get("campaign_id") != _s(self.campaign) or item.get("record_id") != _s("attempt#" + attempt_id):
            raise ValueError("attempt record key differs")
        return {"state": "observed", "present": True, "item": item, "authorizes_go": False, "authorizes_launch": False}

    def _next_head(self, operation, before):
        if (not isinstance(operation, dict)
                or digest(operation.get("expected")) != digest(asdict(before))):
            raise ValueError("epoch operation does not extend the journal head")
        _number(before.revision + 1, "next revision")
        kind = operation.get("kind")
        if kind == "drain" and set(operation) == {"kind", "expected"} and before.mode == "active":
            return replace(before, mode="draining", revision=before.revision + 1)
        if kind == "advance" and set(operation) == {"kind", "expected", "new_owner"} and before.mode == "draining":
            new_owner = _sha(operation["new_owner"])
            _number(before.epoch + 1, "next epoch")
            if new_owner == before.owner:
                raise ValueError("new owner must differ")
            return replace(before, epoch=before.epoch + 1, owner=new_owner, revision=before.revision + 1)
        if kind == "record_intent" and set(operation) == {"kind", "expected", "intent"} and before.mode == "active":
            if not isinstance(operation["intent"], dict):
                raise ValueError("epoch attempt intent is invalid")
            try:
                intent = AttemptIntent(**operation["intent"])
            except TypeError as error:
                raise ValueError("epoch attempt intent fields differ") from error
            if before.budget_upper_micros >= _CAP_MICROS:
                raise ValueError("aggregate budget upper bound has reached its cap")
            if intent.attempt_id in self._attempts or (intent.action, intent.subject_id) in self._subjects:
                raise ValueError("attempt or subject identity already used in the journal")
            return replace(before, revision=before.revision + 1)
        raise ValueError("unsupported epoch operation")

    def _remember(self, operation):
        if operation["kind"] == "record_intent":
            intent = AttemptIntent(**operation["intent"])
            self._attempts.add(intent.attempt_id)
            self._subjects.add((intent.action, intent.subject_id))

    def _condition(self, expected):
        if not isinstance(expected, EpochHead) or expected.generation != self.generation:
            raise ValueError("exact expected epoch head is required")
        _number(expected.revision + 1, "next revision")
        names = {"#g": "generation", "#e": "epoch", "#r": "revision", "#o": "owner", "#m": "mode",
                 "#b": "budget_head", "#u": "budget_upper_micros"}
        values = {":g": _s(expected.generation), ":e": _n(expected.epoch), ":r": _n(expected.revision),
                  ":o": _s(expected.owner), ":m": _s(expected.mode), ":b": _s(expected.budget_head),
                  ":u": _n(expected.budget_upper_micros), ":next": _n(expected.revision + 1)}
        condition = "#g = :g AND #e = :e AND #r = :r AND #o = :o AND #m = :m AND #b = :b AND #u = :u"
        return names, values, condition

    def _write(self, operation, service_request, *, validate=None):
        with self._lock:
            if self._blocked:
                raise FenceUncertain("prior intent requires independent reconciliation")
            target = self._next_head(operation, self._head)
            self._account()
            op_sha = digest(operation)
            # Mark blocked before appending: a short write/fsync failure is not
            # safe to treat as absent or immediately resubmit.
            self._blocked, self._pending = True, op_sha
            try:
                self.journal.append("epoch.intent", {"operation_sha256": op_sha, "operation": operation})
                result = self.client.call("dynamodb", service_request[0], service_request[1])
                if not isinstance(result, dict):
                    raise ValueError("DynamoDB write response is not an object")
                if validate is not None:
                    validate(result)
                self.journal.append("epoch.commit", {"operation_sha256": op_sha, "head": asdict(target)})
            except Exception as error:
                raise FenceUncertain("epoch operation is unresolved; do not retry") from error
            self._pending, self._blocked = None, False
            self._remember(operation)
            self._head = target
            return result

    def close_starts(self, expected):
        if not isinstance(expected, EpochHead) or expected.mode != "active":
            raise ValueError("an active expected head is required")
        names, values, condition = self._condition(expected)
        values[":drain"] = _s("draining")
        request = {"TableName": self.table, "Key": self._key("epoch#head"),
                   "UpdateExpression": "SET #m = :drain, #r = :next", "ConditionExpression": condition,
                   "ExpressionAttributeNames": names, "ExpressionAttributeValues": values, "ReturnValues": "ALL_NEW"}
        target = replace(expected, mode="draining", revision=expected.revision + 1)

        def validate(result):
            if self._decode_head(result.get("Attributes")) != target:
                raise ValueError("drain response differs")

        self._write({"kind": "drain", "expected": asdict(expected)}, ("update-item", request), validate=validate)
        return target

    def advance_epoch(self, expected, new_owner):
        if not isinstance(expected, EpochHead) or expected.mode != "draining":
            raise ValueError("epoch may advance only from a draining head")
        _sha(new_owner)
        if new_owner == expected.owner:
            raise ValueError("new owner must differ")
        _number(expected.epoch + 1, "next epoch")
        names, values, condition = self._condition(expected)
        values.update({":epoch_next": _n(expected.epoch + 1), ":owner_next": _s(new_owner)})
        request = {"TableName": self.table, "Key": self._key("epoch#head"),
                   "UpdateExpression": "SET #e = :epoch_next, #o = :owner_next, #r = :next",
                   "ConditionExpression": condition, "ExpressionAttributeNames": names,
                   "ExpressionAttributeValues": values, "ReturnValues": "ALL_NEW"}
        target = replace(expected, epoch=expected.epoch + 1, owner=new_owner, revision=expected.revision + 1)

        def validate(result):
            if self._decode_head(result.get("Attributes")) != target:
                raise ValueError("epoch response differs")

        self._write({"kind": "advance", "expected": asdict(expected), "new_owner": new_owner},
                    ("update-item", request), validate=validate)
        # It stays draining. Advancing an epoch alone never opens admission.
        return target

    def record_intent(self, expected, intent):
        if not isinstance(expected, EpochHead) or expected.mode != "active" or not isinstance(intent, AttemptIntent):
            raise ValueError("an active exact head and bounded attempt intent are required")
        if expected.budget_upper_micros >= _CAP_MICROS:
            raise ValueError("aggregate budget upper bound has reached its cap")
        names, values, condition = self._condition(expected)
        values[":cap"] = _n(_CAP_MICROS)
        operation = {"kind": "record_intent", "expected": asdict(expected), "intent": asdict(intent)}
        item = {**self._key("attempt#" + intent.attempt_id), "generation": _s(self.generation),
                "epoch": _n(expected.epoch), "owner": _s(expected.owner), "action": _s(intent.action),
                "subject_id": _s(intent.subject_id), "payload_sha256": _s(digest(operation)),
                "job_sha256": _s(intent.job_sha256), "host_sha256": _s(intent.host_sha256),
                "request_sha256": _s(intent.request_sha256), "not_before_utc_ms": _n(intent.not_before_utc_ms),
                "expires_utc_ms": _n(intent.expires_utc_ms)}
        subject = {**self._key("subject#" + intent.action + "#" + intent.subject_id),
                   "attempt_id": _s(intent.attempt_id), "generation": _s(self.generation),
                   "payload_sha256": _s(digest(operation))}
        unique = "attribute_not_exists(campaign_id) AND attribute_not_exists(record_id)"
        request = {"TransactItems": [
            {"Update": {"TableName": self.table, "Key": self._key("epoch#head"),
                        "UpdateExpression": "SET #r = :next", "ConditionExpression": condition + " AND #u < :cap",
                        "ExpressionAttributeNames": names, "ExpressionAttributeValues": values}},
            {"Put": {"TableName": self.table, "Item": item, "ConditionExpression": unique}},
            {"Put": {"TableName": self.table, "Item": subject, "ConditionExpression": unique}},
        ]}
        self._write(operation, ("transact-write-items", request))
        return {"state": "recorded", "attempt_id": intent.attempt_id, "epoch": expected.epoch,
                "revision": expected.revision + 1, "authorizes_go": False, "authorizes_launch": False}
