"""Diagnostic-only Lambda writer; does not grant launch, GO or recovery.

The dedicated function accepts only diagnostic bootstrap, diagnostic and drain events; callers never
supply a table name, update expression, DynamoDB operation, or AWS identity.
All rows in the v2 namespace are read and checked against an explicitly
configured genesis. A single conditional transaction appends the next event,
its unique diagnostic indexes, and a complete-history HEAD commitment.

This source is not deployed or wired to the existing v1 epoch store. A caller's
identity is not established by a field in the invocation event. Lambda version,
role/IAM, an independent authenticated anchor, budget provenance, clock,
remote recipient fence, and crash reconciliation remain unverified. Even a
successful write is only a diagnostic record, not permission to start anything.
Asynchronous Lambda invocation may retry errors or deliver duplicates even
when this code does not resubmit. This diagnostic handler does not establish a
durable independent quarantine for a lost invocation/transaction response.
"""
from __future__ import annotations

import json
import os

try:
    from . import league_writer_history as history
except ImportError:
    import league_writer_history as history


PREFIX = "writer-v2#"
HEAD = PREFIX + "head"
# A diagnostic replay exceeding either bound is rejected; it is not an
# authorization, a truncation, or evidence that omitted history is absent.
MAX_REPLAY_ROWS = 100_000
MAX_REPLAY_BODY_BYTES = 32 * 1024 * 1024


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _decode(raw):
    if not isinstance(raw, str):
        raise ValueError("stored body must be canonical JSON")
    value = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite value")))
    if _canonical(value) != raw:
        raise ValueError("stored body differs from canonical JSON")
    return value


def _event_key(revision):
    if type(revision) is not int or not 1 <= revision <= 2**63 - 2:
        raise ValueError("event revision is invalid")
    return PREFIX + "event#" + str(revision).zfill(20)


def _index_records(event):
    if event["kind"] != "diagnostic":
        return {}
    payload = event["payload"]
    record = {"event_sha256": event["sha256"], "revision": event["revision"]}
    return {
        PREFIX + "attempt#" + payload["attempt_id"]: record,
        PREFIX + "subject#" + payload["intent_kind"] + "#" + payload["subject_id"]: record,
    }


def validate_snapshot(root, head_before, rows, head_after):
    """Reject incomplete/forked v2 rows and HEAD changes during page reads.

    Consistent Query pages do not form an atomic snapshot. Matching HEAD reads
    and a digest are consistency checks, not evidence against privileged
    concurrent tampering or a substituted genesis/independent anchor.
    """
    if (not isinstance(head_before, dict) or not isinstance(head_after, dict)
            or _canonical(head_before) != _canonical(head_after) or not isinstance(rows, list)):
        raise ValueError("HEAD changed or snapshot shape differs")
    bodies = {}
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"campaign_id", "record_id", "body"}
                or row["campaign_id"] != root["campaign"] or not isinstance(row["record_id"], str)
                or not row["record_id"].startswith(PREFIX) or row["record_id"] in bodies):
            raise ValueError("snapshot row identity or schema differs")
        bodies[row["record_id"]] = _decode(row["body"])
    if HEAD not in bodies or _canonical(bodies[HEAD]) != _canonical(head_before):
        raise ValueError("queried HEAD differs from consistent HEAD read")
    revision = head_before.get("revision")
    if type(revision) is not int or not 0 <= revision <= 1_000_000:
        raise ValueError("HEAD revision is invalid or exceeds diagnostic replay bound")
    try:
        events = [bodies[_event_key(i)] for i in range(1, revision + 1)]
    except KeyError as error:
        raise ValueError("event history is incomplete") from error
    history.replay(root, events, head_before)
    expected = {HEAD: head_before}
    for event in events:
        expected[_event_key(event["revision"])] = event
        for key, value in _index_records(event).items():
            if key in expected:
                raise ValueError("duplicate attempt or subject index")
            expected[key] = value
    # JSON booleans and integers must remain distinct: Python dict equality
    # considers True == 1, which would accept a malformed index revision.
    if _canonical(bodies) != _canonical(expected):
        raise ValueError("history or materialized diagnostic indexes differ")
    return events


def execute(request, root, repository):
    """Check a diagnostic request, then ask the repository for one CAS write."""
    if not isinstance(request, dict) or set(request) != {"kind", "payload", "expected_head"}:
        raise ValueError("invocation fields differ")
    if request["kind"] == "bootstrap":
        if request["payload"] != {} or request["expected_head"] is not None:
            raise ValueError("diagnostic bootstrap accepts no caller-chosen root or head")
        history.replay(root, [], root)
        repository.bootstrap_v2(root["campaign"], root)
        return {"state": "diagnostic-bootstrap", "head": root, "anchor_pending": True,
                "authorizes_go": False, "authorizes_launch": False,
                "authorizes_termination": False}
    if request["kind"] not in ("diagnostic", "drain"):
        raise ValueError("untrusted invocations may only bootstrap diagnostics, record diagnostics or close starts")
    before, rows, after = repository.read_v2_snapshot(root["campaign"])
    events = validate_snapshot(root, before, rows, after)
    if _canonical(request["expected_head"]) != _canonical(before):
        raise ValueError("invocation expected HEAD differs")
    new_head, event = history.append(root, events, before, request["kind"], request["payload"])
    # Repository must translate only these exact arguments into a conditional
    # transaction. A timeout is unresolved; no automatic resubmission occurs.
    repository.append_v2(root["campaign"], before, new_head, event, _index_records(event))
    return {"state": "diagnostic-recorded", "head": new_head, "event_sha256": event["sha256"],
            "anchor_pending": True, "authorizes_go": False, "authorizes_launch": False,
            "authorizes_termination": False}


class DynamoRepository:
    """DynamoDB client with fixed expressions and exact table scope.

    Low-level client values use boto3 TypeSerializer/TypeDeserializer. There is
    no caller-controlled expression and no Delete operation. Construction is
    explicit so unit tests can exercise the actual request without credentials.
    """
    def __init__(self, client, table, serializer, deserializer):
        if not isinstance(table, str) or not table:
            raise ValueError("configured table name required")
        self.client, self.table = client, table
        self.serializer, self.deserializer = serializer, deserializer

    def _wire(self, row):
        return {key: self.serializer.serialize(value) for key, value in row.items()}

    def _native(self, row):
        return {key: self.deserializer.deserialize(value) for key, value in row.items()}

    def _head(self, campaign):
        response = self.client.get_item(TableName=self.table, ConsistentRead=True,
            Key=self._wire({"campaign_id": campaign, "record_id": HEAD}))
        if not isinstance(response, dict) or "Item" not in response:
            raise ValueError("pre-provisioned v2 HEAD is unavailable")
        row = self._native(response["Item"])
        if set(row) != {"campaign_id", "record_id", "body"} or row["campaign_id"] != campaign or row["record_id"] != HEAD:
            raise ValueError("HEAD row identity differs")
        return _decode(row["body"])

    def _query_v2(self, campaign):
        paginator = self.client.get_paginator("query")
        pages = paginator.paginate(TableName=self.table, ConsistentRead=True,
            KeyConditionExpression="#pk = :pk AND begins_with(#sk, :prefix)",
            ExpressionAttributeNames={"#pk": "campaign_id", "#sk": "record_id"},
            ExpressionAttributeValues=self._wire({":pk": campaign, ":prefix": PREFIX}))
        rows, body_bytes = [], 0
        for page in pages:
            if not isinstance(page, dict) or not isinstance(page.get("Items"), list):
                raise ValueError("query response differs")
            if len(rows) + len(page["Items"]) > MAX_REPLAY_ROWS:
                raise ValueError("diagnostic replay row budget exceeded")
            for item in page["Items"]:
                row = self._native(item)
                if not isinstance(row.get("body"), str):
                    raise ValueError("diagnostic replay body differs")
                body_bytes += len(row["body"].encode("utf-8"))
                if body_bytes > MAX_REPLAY_BODY_BYTES:
                    raise ValueError("diagnostic replay byte budget exceeded")
                rows.append(row)
        return rows

    def read_v2_snapshot(self, campaign):
        before = self._head(campaign)
        return before, self._query_v2(campaign), self._head(campaign)

    def bootstrap_v2(self, campaign, root):
        # This is diagnostic initialization, not independent genesis proof.
        # Query and conditional put are not one atomic snapshot: privileged
        # concurrent writers and table substitution remain outside this code.
        if self._query_v2(campaign):
            raise ValueError("diagnostic v2 namespace is not empty")
        return self.client.put_item(TableName=self.table,
            Item=self._wire({"campaign_id": campaign, "record_id": HEAD, "body": _canonical(root)}),
            ConditionExpression="attribute_not_exists(#pk) AND attribute_not_exists(#sk)",
            ExpressionAttributeNames={"#pk": "campaign_id", "#sk": "record_id"})

    def append_v2(self, campaign, previous_head, new_head, event, indexes):
        key = lambda record_id: self._wire({"campaign_id": campaign, "record_id": record_id})
        row = lambda record_id, body: self._wire({"campaign_id": campaign, "record_id": record_id, "body": _canonical(body)})
        items = [
            {"Update": {"TableName": self.table, "Key": key(HEAD),
                "UpdateExpression": "SET #body = :new", "ConditionExpression": "#body = :old",
                "ExpressionAttributeNames": {"#body": "body"},
                "ExpressionAttributeValues": self._wire({":new": _canonical(new_head), ":old": _canonical(previous_head)})}},
            {"Put": {"TableName": self.table, "Item": row(_event_key(event["revision"]), event),
                "ConditionExpression": "attribute_not_exists(#pk) AND attribute_not_exists(#sk)",
                "ExpressionAttributeNames": {"#pk": "campaign_id", "#sk": "record_id"}}},
        ]
        for record_id, body in sorted(indexes.items()):
            items.append({"Put": {"TableName": self.table, "Item": row(record_id, body),
                "ConditionExpression": "attribute_not_exists(#pk) AND attribute_not_exists(#sk)",
                "ExpressionAttributeNames": {"#pk": "campaign_id", "#sk": "record_id"}}})
        # Botocore may populate ClientRequestToken automatically. Its limited
        # idempotency window and disabled SDK retries do not replace durable
        # reconciliation after an ambiguous response or Lambda-level retry.
        return self.client.transact_write_items(TransactItems=items)


_runtime = None


def handler(event, context):
    """Lambda entrypoint; configuration must be pinned outside the event."""
    global _runtime
    if _runtime is None:
        import boto3
        from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
        from botocore.config import Config
        root = _decode(os.environ["ROVE_LEAGUE_GENESIS_JSON"])
        if _canonical(root) != _canonical(history.genesis(root["campaign"], root["generation"], root["owner"],
                                                          root["budget_head"], root["budget_upper_micros"])):
            raise ValueError("configured genesis differs")
        if root["campaign"] != os.environ["ROVE_LEAGUE_CAMPAIGN"]:
            raise ValueError("configured genesis campaign differs")
        client = boto3.client("dynamodb", config=Config(retries={"total_max_attempts": 1},
                                                       connect_timeout=5, read_timeout=10))
        _runtime = (root, DynamoRepository(client, os.environ["ROVE_LEAGUE_EPOCH_TABLE"],
                                           TypeSerializer(), TypeDeserializer()))
    return execute(event, _runtime[0], _runtime[1])
