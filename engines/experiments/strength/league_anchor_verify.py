"""Verify a proposed league history and *externally signed* anchor receipt.

This module is a pure diagnostic boundary: it performs no AWS I/O, does not
create an S3 object, does not initialize or migrate the existing epoch store,
and never provides GO, launch, or termination authority. Callers must obtain
complete strongly read history and exact S3 object versions by a separately
authenticated process; none of those facts can be inferred from a supplied
dictionary, a hash, or a successful signature check here. The TableId in the
manifest is pinned but the supplied DynamoDB rows have no authenticated table
identity: identical rows from a recreated table cannot be distinguished here.

The version ID is signed in a separate receipt, *after* object creation. The
object's manifest does not contain its own version ID. A trusted external
watermark selects the preceding signed receipt; a valid old signature alone
does not establish that watermark is the latest. History follows the
diagnostic `league_writer_history` v2 format, not the existing v1
`DynamoEpochStore` schema. This module is not a migration mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
import re

try:
    from . import league_writer_history as history
    from . import league_writer_lambda as writer
except ImportError:
    import league_writer_history as history
    import league_writer_lambda as writer


_HEX = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}")
_REGION = re.compile(r"[a-z]{2}(?:-gov)?-[a-z]+-[0-9]+")
_MAX_EVENTS = 100000


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as error:
        raise ValueError("noncanonical value") from error


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha(value):
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        raise ValueError("canonical SHA-256 required")
    return value


def _number(value, name):
    if type(value) is not int or not 0 <= value <= 2**63 - 1:
        raise ValueError("invalid " + name)
    return value


def _id(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError("invalid bounded identifier")
    return value


@dataclass(frozen=True)
class TrustContext:
    """Expected identities pinned independently by the caller, not this module."""
    account: str
    region: str
    table_arn: str
    table_id: str
    campaign: str
    generation: str
    bucket: str
    key: str
    signing_key_sha256: str
    algorithm: str

    def __post_init__(self):
        if not isinstance(self.account, str) or not re.fullmatch(r"[0-9]{12}", self.account):
            raise ValueError("canonical account required")
        if not isinstance(self.region, str) or not _REGION.fullmatch(self.region):
            raise ValueError("canonical home region required")
        prefix = f"arn:aws:dynamodb:{self.region}:{self.account}:table/"
        if (not isinstance(self.table_arn, str) or not self.table_arn.startswith(prefix)
                or not re.fullmatch(r"[A-Za-z0-9_.-]{3,255}", self.table_arn[len(prefix):])):
            raise ValueError("exact original table ARN required")
        if (not isinstance(self.table_id, str)
                or not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", self.table_id)):
            raise ValueError("canonical original DynamoDB TableId required")
        if not _id(self.campaign).startswith("league-"):
            raise ValueError("league campaign namespace required")
        _sha(self.generation)
        _sha(self.signing_key_sha256)
        if (not isinstance(self.bucket, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", self.bucket)
                or not isinstance(self.key, str) or len(self.key) > 1024 or len(self.key.encode("utf-8")) > 1024
                or not re.fullmatch(r"[A-Za-z0-9_./-]+", self.key) or not self.key.startswith(self.campaign + "/")
                or any(p in ("", ".", "..") for p in self.key.split("/"))):
            raise ValueError("canonical anchor location required")
        if not isinstance(self.algorithm, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", self.algorithm):
            raise ValueError("explicit external verifier algorithm required")


@dataclass(frozen=True)
class SignatureCheck:
    """A claim from the injected verifier, which must itself be trusted."""
    message_sha256: str
    signature_sha256: str
    signing_key_sha256: str
    algorithm: str


def _verify_receipt(context, receipt, manifest_bytes, expected_version, verifier):
    if not isinstance(receipt, dict) or set(receipt) != {"body", "signature_b64"}:
        raise ValueError("invalid signed receipt")
    body = receipt["body"]
    if (not isinstance(body, dict) or set(body) != {"schema", "bucket", "key", "version_id", "object_sha256",
                                                   "signing_key_sha256", "algorithm"}
            or body["schema"] != "rove4k-league-anchor-receipt-v1"
            or body["bucket"] != context.bucket or body["key"] != context.key
            or body["version_id"] != expected_version or not isinstance(expected_version, str)
            or expected_version in ("", "null") or len(expected_version) > 1024 or len(expected_version.encode("utf-8")) > 1024
            or any(ord(char) < 32 or ord(char) == 127 for char in expected_version)
            or body["signing_key_sha256"] != context.signing_key_sha256
            or body["algorithm"] != context.algorithm
            or not isinstance(manifest_bytes, bytes) or len(manifest_bytes) > 1_000_000
            or body["object_sha256"] != hashlib.sha256(manifest_bytes).hexdigest()):
        raise ValueError("receipt object, location, version or signer differs")
    if not isinstance(receipt["signature_b64"], str) or len(receipt["signature_b64"]) > 21848:
        raise ValueError("invalid receipt signature encoding")
    try:
        sig = base64.b64decode(receipt["signature_b64"], validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("invalid receipt signature encoding") from error
    if not sig or len(sig) > 16384 or base64.b64encode(sig).decode("ascii") != receipt["signature_b64"]:
        raise ValueError("invalid receipt signature encoding")
    if (getattr(verifier, "public_key_sha256", None) != context.signing_key_sha256
            or getattr(verifier, "algorithm", None) != context.algorithm
            or not callable(getattr(verifier, "verify", None))):
        raise ValueError("externally bound signature verifier differs")
    try:
        message = _canonical(body)
        result = verifier.verify(message, sig)
    except Exception as error:
        raise ValueError("external signature verification failed") from error
    expected_check = SignatureCheck(hashlib.sha256(message).hexdigest(), hashlib.sha256(sig).hexdigest(),
                                    context.signing_key_sha256, context.algorithm)
    if type(result) is not SignatureCheck or result != expected_check:
        raise ValueError("verifier did not return an exact signature verification claim")
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid anchor manifest") from error
    if _canonical(manifest) != manifest_bytes:
        raise ValueError("manifest encoding is not canonical")
    expected = {"schema", "account", "region", "table_arn", "table_id", "campaign", "generation", "head",
                "genesis_sha256", "previous_receipt_sha256"}
    if (not isinstance(manifest, dict) or set(manifest) != expected
            or manifest["schema"] != "rove4k-league-anchor-manifest-v1"
            or any(manifest[name] != getattr(context, name) for name in
                   ("account", "region", "table_arn", "table_id", "campaign", "generation"))):
        raise ValueError("anchor manifest identity differs")
    for name in ("genesis_sha256", "previous_receipt_sha256"):
        _sha(manifest[name])
    if not isinstance(manifest["head"], dict):
        raise ValueError("full writer HEAD required")
    _number(manifest["head"].get("revision"), "anchor revision")
    _sha(manifest["head"].get("history_sha256"))
    return manifest


def inspect(context, *, previous_receipt, previous_manifest, previous_version,
            next_receipt, next_manifest, next_version, external_watermark_sha256,
            root, head_before, rows, head_after, verifier):
    """Audit one adjacent, signed anchor step and complete supplied history.

    Signature verification calls the externally configured verifier and must
    raise on mismatch. A verifier returning no result or a boolean is rejected;
    the required bound claim still does not prove that arbitrary injected code
    actually performed cryptographic verification. The
    caller is responsible for verifier identity, authenticated watermark,
    immutable S3 version/retention, DDB TableId/read provenance and quiescence. This
    function deliberately cannot certify those external claims or issue GO.
    """
    if not isinstance(context, TrustContext):
        raise ValueError("independent trust context required")
    _sha(external_watermark_sha256)
    if previous_version == next_version:
        raise ValueError("distinct immutable object versions required")
    previous = _verify_receipt(context, previous_receipt, previous_manifest, previous_version, verifier)
    if _digest(previous_receipt) != external_watermark_sha256:
        raise ValueError("previous receipt differs from supplied watermark")
    current = _verify_receipt(context, next_receipt, next_manifest, next_version, verifier)
    previous_head, current_head = previous["head"], current["head"]
    if (current["previous_receipt_sha256"] != external_watermark_sha256
            or current_head["revision"] != previous_head["revision"] + 1):
        raise ValueError("anchor step is missing, forked or not adjacent")
    if not isinstance(root, dict) or len(root) != 10:
        raise ValueError("invalid writer genesis")
    history.replay(root, [], root)
    if (root.get("campaign") != context.campaign or root.get("generation") != context.generation
            or previous["genesis_sha256"] != _digest(root) or current["genesis_sha256"] != _digest(root)
            or _canonical(current_head) != _canonical(head_before)):
        raise ValueError("writer genesis or observed HEAD differs from anchor")
    if current_head["revision"] > _MAX_EVENTS or not isinstance(rows, list) or len(rows) > 3 * _MAX_EVENTS + 1:
        raise ValueError("history exceeds the audit bound")
    events = writer.validate_snapshot(root, head_before, rows, head_after)
    # The writer is the source of transition and index rules. Replay the
    # prefix against the previous signed HEAD to detect rollback or a fork.
    history.replay(root, events[:previous_head["revision"]], previous_head)
    return {"schema": "rove4k-league-anchor-diagnostic-v1", "history_chain_checked": True,
            "signature_verification_claim_received": True, "revision": current_head["revision"],
            "anchor_storage_authenticated": False, "watermark_independent": False,
            "caller_and_writer_authenticated": False, "read_snapshot_proven": False,
            "budget_authenticated": False, "authorizes_go": False,
            "authorizes_launch": False, "authorizes_termination": False}
