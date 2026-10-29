"""Exercise the actual diagnostic Lambda transaction path with fake DynamoDB."""
import copy
import unittest
from unittest.mock import patch

try:
    from . import league_writer_history as history
    from . import league_writer_lambda as writer
except ImportError:
    import league_writer_history as history
    import league_writer_lambda as writer


class Codec:
    def serialize(self, value):
        if not isinstance(value, str):
            raise ValueError("test data should be strings")
        return {"S": value}

    def deserialize(self, value):
        if not isinstance(value, dict) or set(value) != {"S"}:
            raise ValueError("invalid fake AttributeValue")
        return value["S"]


class Pages:
    def __init__(self, client):
        self.client = client

    def paginate(self, **request):
        assert request["ConsistentRead"] is True
        assert request["KeyConditionExpression"] == "#pk = :pk AND begins_with(#sk, :prefix)"
        assert request["ExpressionAttributeValues"][":prefix"] == {"S": writer.PREFIX}
        rows = [copy.deepcopy(value) for key, value in sorted(self.client.rows.items())
                if key.startswith(writer.PREFIX)]
        # Split deliberately: strong Query pages are not a transaction snapshot.
        yield {"Items": rows[:1]}
        yield {"Items": rows[1:]}
        if self.client.replace_head_after_query is not None:
            self.client.rows[writer.HEAD] = self.client.replace_head_after_query


class Dynamo:
    def __init__(self, root):
        self.codec = Codec()
        self.campaign = root["campaign"]
        self.rows = {writer.HEAD: self.wire(writer.HEAD, root)}
        self.transactions = []
        self.replace_head_after_query = None
        self.fail_after_commit = False
        self.insert_orphan_before_put = False

    def wire(self, key, body):
        return {k: self.codec.serialize(v) for k, v in {"campaign_id": self.campaign,
                "record_id": key, "body": writer._canonical(body)}.items()}

    def get_item(self, **request):
        assert request["ConsistentRead"] is True
        key = request["Key"]["record_id"]["S"]
        return {"Item": copy.deepcopy(self.rows[key])} if key in self.rows else {}

    def get_paginator(self, name):
        assert name == "query"
        return Pages(self)

    def put_item(self, **request):
        assert request["ConditionExpression"] == "attribute_not_exists(#pk) AND attribute_not_exists(#sk)"
        if self.insert_orphan_before_put:
            orphan = writer.PREFIX + "event#" + "0" * 19 + "1"
            self.rows[orphan] = self.wire(orphan, {})
        row = request["Item"]
        key = row["record_id"]["S"]
        if key in self.rows:
            raise ValueError("conditional bootstrap duplicate")
        self.rows[key] = copy.deepcopy(row)
        return {}

    def transact_write_items(self, **request):
        self.transactions.append(copy.deepcopy(request))
        items = request["TransactItems"]
        update = items[0]["Update"]
        assert update["ConditionExpression"] == "#body = :old"
        assert update["Key"]["record_id"] == {"S": writer.HEAD}
        if self.rows[writer.HEAD]["body"] != update["ExpressionAttributeValues"][":old"]:
            raise ValueError("conditional HEAD failure")
        staged = copy.deepcopy(self.rows)
        for entry in items[1:]:
            put = entry["Put"]
            assert put["ConditionExpression"] == "attribute_not_exists(#pk) AND attribute_not_exists(#sk)"
            row = put["Item"]
            key = row["record_id"]["S"]
            if key in staged:
                raise ValueError("conditional duplicate failure")
            staged[key] = copy.deepcopy(row)
        staged[writer.HEAD]["body"] = update["ExpressionAttributeValues"][":new"]
        self.rows = staged
        if self.fail_after_commit:
            raise TimeoutError("response lost after commit")
        return {}


def intent(attempt="a1", subject="s1"):
    return {"attempt_id": attempt, "subject_id": subject, "intent_kind": "go",
            "job_sha256": "a" * 64, "host_sha256": "b" * 64, "request_sha256": "c" * 64,
            "not_before_utc_ms": 100, "expires_utc_ms": 200}


class DiagnosticWriterTests(unittest.TestCase):
    def setUp(self):
        self.root = history.genesis("league-example", "1" * 64, "2" * 64, "3" * 64, 0)
        self.client = Dynamo(self.root)
        self.repo = writer.DynamoRepository(self.client, "unit-table", self.client.codec, self.client.codec)

    def request(self, kind="diagnostic", payload=None, head=None):
        return {"kind": kind, "payload": intent() if payload is None else payload,
                "expected_head": self.root if head is None else head}

    def test_complete_read_and_conditioned_write_are_diagnostic_only(self):
        result = writer.execute(self.request(), self.root, self.repo)
        self.assertFalse(result["authorizes_go"])
        self.assertFalse(result["authorizes_launch"])
        self.assertFalse(result["authorizes_termination"])
        self.assertTrue(result["anchor_pending"])
        self.assertEqual(result["head"]["revision"], 1)
        self.assertEqual(len(self.client.transactions), 1)
        self.assertEqual(len(self.client.transactions[0]["TransactItems"]), 4)
        before, rows, after = self.repo.read_v2_snapshot(self.root["campaign"])
        self.assertEqual(len(writer.validate_snapshot(self.root, before, rows, after)), 1)

    def test_bootstrap_uses_only_fixed_root_and_cannot_overwrite_existing_rows(self):
        del self.client.rows[writer.HEAD]
        bootstrap = {"kind": "bootstrap", "payload": {}, "expected_head": None}
        result = writer.execute(bootstrap, self.root, self.repo)
        self.assertEqual(result["head"], self.root)
        self.assertFalse(result["authorizes_go"])
        self.assertFalse(result["authorizes_launch"])
        self.assertTrue(result["anchor_pending"])
        with self.assertRaises(ValueError):
            writer.execute(bootstrap, self.root, self.repo)

    def test_bootstrap_rejects_untrusted_root_or_existing_partial_namespace(self):
        del self.client.rows[writer.HEAD]
        for event in ({"kind": "bootstrap", "payload": {"owner": "3" * 64}, "expected_head": None},
                      {"kind": "bootstrap", "payload": {}, "expected_head": self.root}):
            with self.subTest(event=event), self.assertRaises(ValueError):
                writer.execute(event, self.root, self.repo)
        self.client.rows[writer.PREFIX + "attempt#orphan"] = self.client.wire(writer.PREFIX + "attempt#orphan", {})
        with self.assertRaises(ValueError):
            writer.execute({"kind": "bootstrap", "payload": {}, "expected_head": None}, self.root, self.repo)
        self.assertNotIn(writer.HEAD, self.client.rows)

    def test_bootstrap_query_put_race_is_not_claimed_as_verified_empty_history(self):
        del self.client.rows[writer.HEAD]
        self.client.insert_orphan_before_put = True
        result = writer.execute({"kind": "bootstrap", "payload": {}, "expected_head": None}, self.root, self.repo)
        self.assertTrue(result["anchor_pending"])
        self.assertFalse(result["authorizes_go"])
        self.assertFalse(result["authorizes_launch"])
        self.assertFalse(result["authorizes_termination"])
        with self.assertRaises(ValueError):
            writer.execute(self.request(), self.root, self.repo)
        self.assertFalse(self.client.transactions)

    def test_disallowed_operation_and_injected_table_are_rejected(self):
        for request in ({**self.request(), "kind": "handoff"},
                        {**self.request(), "kind": "budget_observed"},
                        {**self.request(), "TableName": "other"}):
            with self.subTest(request=request), self.assertRaises(ValueError):
                writer.execute(request, self.root, self.repo)
        self.assertFalse(self.client.transactions)

    def test_missing_event_or_index_is_rejected_before_write(self):
        result = writer.execute(self.request(), self.root, self.repo)
        for key in (writer._event_key(1), writer.PREFIX + "attempt#a1", writer.PREFIX + "subject#go#s1"):
            original = self.client.rows.pop(key)
            with self.subTest(key=key), self.assertRaises(ValueError):
                writer.execute(self.request(payload=intent("a2", "s2"), head=result["head"]), self.root, self.repo)
            self.client.rows[key] = original
        self.assertEqual(len(self.client.transactions), 1)

    def test_index_boolean_is_not_accepted_as_integer_revision(self):
        result = writer.execute(self.request(), self.root, self.repo)
        key = writer.PREFIX + "attempt#a1"
        body = writer._decode(self.client.rows[key]["body"]["S"])
        body["revision"] = True
        self.client.rows[key] = self.client.wire(key, body)
        with self.assertRaises(ValueError):
            writer.execute(self.request(payload=intent("a2", "s2"), head=result["head"]), self.root, self.repo)
        self.assertEqual(len(self.client.transactions), 1)

    def test_expected_boolean_is_not_accepted_as_integer_revision(self):
        result = writer.execute(self.request(), self.root, self.repo)
        malformed = {**result["head"], "revision": True}
        with self.assertRaises(ValueError):
            writer.execute(self.request(payload=intent("a2", "s2"), head=malformed), self.root, self.repo)
        self.assertEqual(len(self.client.transactions), 1)

    def test_extra_row_and_changed_head_between_pages_fail_closed(self):
        self.client.rows[writer.PREFIX + "unknown"] = self.client.wire(writer.PREFIX + "unknown", {})
        with self.assertRaises(ValueError):
            writer.execute(self.request(), self.root, self.repo)
        del self.client.rows[writer.PREFIX + "unknown"]
        changed = {**self.root, "revision": 1}
        self.client.replace_head_after_query = self.client.wire(writer.HEAD, changed)
        with self.assertRaises(ValueError):
            writer.execute(self.request(), self.root, self.repo)
        self.assertFalse(self.client.transactions)

    def test_duplicate_attempt_and_subject_are_rejected(self):
        result = writer.execute(self.request(), self.root, self.repo)
        for payload in (intent("a1", "other"), intent("other", "s1")):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                writer.execute(self.request(payload=payload, head=result["head"]), self.root, self.repo)
        self.assertEqual(len(self.client.transactions), 1)

    def test_failed_response_after_commit_never_creates_second_same_attempt(self):
        self.client.fail_after_commit = True
        with self.assertRaises(TimeoutError):
            writer.execute(self.request(), self.root, self.repo)
        self.client.fail_after_commit = False
        with self.assertRaises(ValueError):
            writer.execute(self.request(), self.root, self.repo)
        self.assertEqual(len(self.client.transactions), 1)

    def test_drain_closes_new_diagnostic_records_without_termination(self):
        result = writer.execute(self.request("drain", {"reason": "budget"}), self.root, self.repo)
        self.assertEqual(result["head"]["mode"], "draining")
        with self.assertRaises(ValueError):
            writer.execute(self.request(head=result["head"]), self.root, self.repo)
        self.assertFalse(result["authorizes_termination"])

    def test_missing_or_noncanonical_head_never_bootstraps(self):
        del self.client.rows[writer.HEAD]
        with self.assertRaises(ValueError):
            writer.execute(self.request(), self.root, self.repo)
        self.assertFalse(self.client.transactions)
        self.client.rows[writer.HEAD] = self.client.wire(writer.HEAD, self.root)
        self.client.rows[writer.HEAD]["body"] = {"S": '{"schema": "not-canonical"}'}
        with self.assertRaises(ValueError):
            writer.execute(self.request(), self.root, self.repo)
        self.assertFalse(self.client.transactions)

    def test_replay_bounds_fail_closed_without_truncating_or_writing(self):
        for name, cap in (("MAX_REPLAY_ROWS", 0), ("MAX_REPLAY_BODY_BYTES", 1)):
            with self.subTest(name=name), patch.object(writer, name, cap):
                with self.assertRaises(ValueError):
                    writer.execute(self.request(), self.root, self.repo)
            self.assertFalse(self.client.transactions)


if __name__ == "__main__":
    unittest.main()
