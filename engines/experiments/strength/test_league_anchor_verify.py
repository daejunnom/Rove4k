"""Real signed-receipt checks and writer-v2 replay with fake AWS transports."""
import base64
import copy
from dataclasses import replace
import hashlib
import hmac
import json
import secrets
import unittest

try:
    from . import league_anchor_verify as anchor
    from . import league_writer_history as history
    from . import league_writer_lambda as writer
except ImportError:
    import league_anchor_verify as anchor
    import league_writer_history as history
    import league_writer_lambda as writer


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class FixtureVerifier:
    """Actual HMAC verification with an ephemeral test key, never production auth."""
    algorithm = "HMAC-SHA256-fixture"

    def __init__(self):
        self._key = secrets.token_bytes(32)
        self.public_key_sha256 = hashlib.sha256(self._key).hexdigest()

    def sign(self, body):
        return hmac.new(self._key, canonical(body), hashlib.sha256).digest()

    def verify(self, message, signature):
        if not hmac.compare_digest(hmac.new(self._key, message, hashlib.sha256).digest(), signature):
            raise ValueError("signature mismatch")
        return anchor.SignatureCheck(hashlib.sha256(message).hexdigest(), hashlib.sha256(signature).hexdigest(),
                                     self.public_key_sha256, self.algorithm)


class Codec:
    def serialize(self, value):
        if not isinstance(value, str):
            raise ValueError("expected string")
        return {"S": value}

    def deserialize(self, value):
        if not isinstance(value, dict) or set(value) != {"S"}:
            raise ValueError("invalid AttributeValue")
        return value["S"]


class FakePages:
    def __init__(self, client):
        self.client = client

    def paginate(self, **request):
        assert request["ConsistentRead"] is True
        rows = [copy.deepcopy(v) for k, v in sorted(self.client.rows.items()) if k.startswith(writer.PREFIX)]
        yield {"Items": rows[:1]}
        yield {"Items": rows[1:]}


class FakeDynamo:
    """Exercise actual DynamoRepository request generation, never AWS."""
    def __init__(self, root):
        self.codec, self.campaign = Codec(), root["campaign"]
        self.rows = {writer.HEAD: self.wire(writer.HEAD, root)}

    def wire(self, record_id, body):
        return {k: self.codec.serialize(v) for k, v in {"campaign_id": self.campaign,
                "record_id": record_id, "body": writer._canonical(body)}.items()}

    def get_item(self, **request):
        assert request["ConsistentRead"] is True
        record_id = request["Key"]["record_id"]["S"]
        return {"Item": copy.deepcopy(self.rows[record_id])} if record_id in self.rows else {}

    def get_paginator(self, name):
        assert name == "query"
        return FakePages(self)

    def transact_write_items(self, **request):
        update = request["TransactItems"][0]["Update"]
        if self.rows[writer.HEAD]["body"] != update["ExpressionAttributeValues"][":old"]:
            raise ValueError("head CAS")
        staged = copy.deepcopy(self.rows)
        for transaction in request["TransactItems"][1:]:
            put = transaction["Put"]
            assert put["ConditionExpression"] == "attribute_not_exists(#pk) AND attribute_not_exists(#sk)"
            record_id = put["Item"]["record_id"]["S"]
            if record_id in staged:
                raise ValueError("duplicate row")
            staged[record_id] = copy.deepcopy(put["Item"])
        staged[writer.HEAD]["body"] = update["ExpressionAttributeValues"][":new"]
        self.rows = staged
        return {}


class Fixture:
    def __init__(self):
        self.verifier = FixtureVerifier()
        self.context = anchor.TrustContext(
            account="123456789012", region="ap-southeast-2",
            table_arn="arn:aws:dynamodb:ap-southeast-2:123456789012:table/league-table",
            table_id="12345678-1234-1234-1234-123456789abc", campaign="league-test", generation="1" * 64,
            bucket="league-test-anchor", key="league-test/anchor.json",
            signing_key_sha256=self.verifier.public_key_sha256, algorithm=self.verifier.algorithm)
        self.root = history.genesis(self.context.campaign, self.context.generation, "2" * 64, "3" * 64, 0)
        self.db = FakeDynamo(self.root)
        self.repo = writer.DynamoRepository(self.db, "league-table", self.db.codec, self.db.codec)
        self.previous_manifest = self.make_manifest(self.root, "0" * 64)
        self.previous_receipt = self.make_receipt(self.previous_manifest, "version-0")
        payload = {"attempt_id": "attempt-1", "subject_id": "game-1", "intent_kind": "go",
                   "job_sha256": "a" * 64, "host_sha256": "b" * 64, "request_sha256": "c" * 64,
                   "not_before_utc_ms": 100, "expires_utc_ms": 200}
        # This is the actual writer execution and request builder, driven by a
        # fake DynamoDB client. It returns a diagnostic result only.
        outcome = writer.execute({"kind": "diagnostic", "payload": payload, "expected_head": self.root},
                                 self.root, self.repo)
        self.assert_diagnostic(outcome)
        self.before, self.rows, self.after = self.repo.read_v2_snapshot(self.context.campaign)
        self.current_manifest = self.make_manifest(outcome["head"], digest(self.previous_receipt))
        self.current_receipt = self.make_receipt(self.current_manifest, "version-1")

    @staticmethod
    def assert_diagnostic(outcome):
        assert outcome["anchor_pending"] is True and outcome["authorizes_go"] is False

    def make_manifest(self, head, previous, **overrides):
        result = {"schema": "rove4k-league-anchor-manifest-v1", "account": self.context.account,
                  "region": self.context.region, "table_arn": self.context.table_arn, "table_id": self.context.table_id,
                  "campaign": self.context.campaign, "generation": self.context.generation, "head": head,
                  "genesis_sha256": digest(self.root), "previous_receipt_sha256": previous}
        result.update(overrides)
        return canonical(result)

    def make_receipt(self, raw, version):
        body = {"schema": "rove4k-league-anchor-receipt-v1", "bucket": self.context.bucket,
                "key": self.context.key, "version_id": version, "object_sha256": hashlib.sha256(raw).hexdigest(),
                "signing_key_sha256": self.context.signing_key_sha256, "algorithm": self.context.algorithm}
        return {"body": body, "signature_b64": base64.b64encode(self.verifier.sign(body)).decode()}

    def kwargs(self):
        return {"previous_receipt": copy.deepcopy(self.previous_receipt), "previous_manifest": self.previous_manifest,
                "previous_version": "version-0", "next_receipt": copy.deepcopy(self.current_receipt),
                "next_manifest": self.current_manifest, "next_version": "version-1",
                "external_watermark_sha256": digest(self.previous_receipt), "root": copy.deepcopy(self.root),
                "head_before": copy.deepcopy(self.before), "rows": copy.deepcopy(self.rows),
                "head_after": copy.deepcopy(self.after), "verifier": self.verifier}


class AnchorAuditTests(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()

    def audit(self, **changes):
        return anchor.inspect(self.f.context, **{**self.f.kwargs(), **changes})

    def test_real_writer_output_and_hmac_verify_never_grant_authority(self):
        result = self.audit()
        self.assertTrue(result["history_chain_checked"])
        for key in ("anchor_storage_authenticated", "watermark_independent", "caller_and_writer_authenticated",
                    "read_snapshot_proven", "budget_authenticated", "authorizes_go", "authorizes_launch",
                    "authorizes_termination"):
            self.assertFalse(result[key], key)

    def test_partial_ddb_commit_without_anchor_never_passes(self):
        with self.assertRaisesRegex(ValueError, "receipt"):
            self.audit(next_receipt=None)
        with self.assertRaisesRegex(ValueError, "HEAD changed"):
            self.audit(head_after={**self.f.after, "revision": 2})

    def test_signature_mutation_is_rejected_by_real_verifier(self):
        receipt = copy.deepcopy(self.f.current_receipt)
        raw = bytearray(base64.b64decode(receipt["signature_b64"]))
        raw[0] ^= 1
        receipt["signature_b64"] = base64.b64encode(raw).decode()
        with self.assertRaisesRegex(ValueError, "signature verification"):
            self.audit(next_receipt=receipt)
        receipt = copy.deepcopy(self.f.previous_receipt)
        receipt["signature_b64"] = "A" * 21849
        with self.assertRaisesRegex(ValueError, "signature encoding"):
            self.audit(previous_receipt=receipt)

    def test_truthy_flag_and_noop_do_not_replace_signature_verifier(self):
        with self.assertRaisesRegex(ValueError, "signature verifier"):
            self.audit(verifier=True)
        class NoOpVerifier:
            public_key_sha256 = self.f.verifier.public_key_sha256
            algorithm = self.f.verifier.algorithm
            def verify(self, message, signature):
                pass
        with self.assertRaisesRegex(ValueError, "verification claim"):
            self.audit(verifier=NoOpVerifier())

    def test_s3_location_version_and_bytes_are_bound_to_signed_receipt(self):
        with self.assertRaisesRegex(ValueError, "version"):
            self.audit(next_version="different-version")
        with self.assertRaisesRegex(ValueError, "distinct"):
            self.audit(next_version="version-0")
        with self.assertRaisesRegex(ValueError, "receipt object"):
            self.audit(next_manifest=self.f.current_manifest + b" ")

    def test_missing_or_duplicate_writer_rows_are_rejected(self):
        for suffix in ("event#00000000000000000001", "attempt#attempt-1", "subject#go#game-1"):
            missing = [r for r in self.f.rows if r["record_id"] != writer.PREFIX + suffix]
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                self.audit(rows=missing)
        with self.assertRaisesRegex(ValueError, "row identity"):
            self.audit(rows=self.f.rows + [self.f.rows[0]])

    def test_changed_writer_index_and_head_are_rejected(self):
        rows = copy.deepcopy(self.f.rows)
        entry = next(r for r in rows if r["record_id"] == writer.PREFIX + "attempt#attempt-1")
        index = json.loads(entry["body"])
        index["revision"] = True
        entry["body"] = writer._canonical(index)
        with self.assertRaisesRegex(ValueError, "indexes differ"):
            self.audit(rows=rows)
        before = {**self.f.before, "revision": True}
        with self.assertRaisesRegex(ValueError, "observed HEAD differs"):
            self.audit(head_before=before)

    def test_fork_and_stale_watermark_are_detected(self):
        with self.assertRaisesRegex(ValueError, "watermark"):
            self.audit(external_watermark_sha256="f" * 64)
        fork = self.f.make_manifest(self.f.before, "f" * 64)
        with self.assertRaisesRegex(ValueError, "forked"):
            self.audit(next_manifest=fork, next_receipt=self.f.make_receipt(fork, "version-1"))

    def test_changed_manifest_table_arn_or_table_id_is_rejected(self):
        for changed in ({"table_arn": "arn:aws:dynamodb:ap-southeast-2:123456789012:table/restored"},
                        {"table_id": "abcdef01-1234-1234-1234-123456789abc"}):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "identity differs"):
                manifest = self.f.make_manifest(self.f.before, digest(self.f.previous_receipt), **changed)
                self.audit(next_manifest=manifest, next_receipt=self.f.make_receipt(manifest, "version-1"))

    def test_untrusted_root_or_changed_event_cannot_replace_signed_history(self):
        root = {**self.f.root, "owner": "f" * 64}
        with self.assertRaisesRegex(ValueError, "genesis"):
            self.audit(root=root)
        rows = copy.deepcopy(self.f.rows)
        entry = next(r for r in rows if r["record_id"] == writer._event_key(1))
        event = json.loads(entry["body"])
        event["payload"]["subject_id"] = "other-game"
        entry["body"] = writer._canonical(event)
        with self.assertRaisesRegex(ValueError, "digest differs"):
            self.audit(rows=rows)

    def test_account_and_anchor_path_require_safe_ascii(self):
        with self.assertRaisesRegex(ValueError, "canonical account"):
            replace(self.f.context, account="١٢٣٤٥٦٧٨٩٠١٢")
        with self.assertRaisesRegex(ValueError, "canonical anchor location"):
            replace(self.f.context, key="league-test/anchor\nname")

    def test_budget_drained_head_keeps_started_games_outside_scope(self):
        outcome = writer.execute({"kind": "drain", "payload": {"reason": "budget"},
                                  "expected_head": self.f.before}, self.f.root, self.f.repo)
        prior = self.f.current_manifest
        prior_receipt = self.f.current_receipt
        before, rows, after = self.f.repo.read_v2_snapshot(self.f.context.campaign)
        current = self.f.make_manifest(outcome["head"], digest(prior_receipt))
        result = self.audit(previous_manifest=prior, previous_receipt=prior_receipt, previous_version="version-1",
                            external_watermark_sha256=digest(prior_receipt), next_manifest=current,
                            next_receipt=self.f.make_receipt(current, "version-2"), next_version="version-2",
                            head_before=before, rows=rows, head_after=after)
        self.assertFalse(result["authorizes_termination"])
        self.assertFalse(result["budget_authenticated"])


if __name__ == "__main__":
    unittest.main()
