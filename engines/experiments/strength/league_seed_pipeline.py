"""Compose owner-requested fetch and seed inspection on one bytes snapshot.

This is a diagnostic bridge, not an installed bootstrap, SSM authority, host
authentication, source provenance authentication or materialization. A real
bootstrap must pin this module and its complete transitive source closure before
the seed exists. No files are deleted on success or failure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json

try:
    from .league_seed_archive import inspect_snapshot
    from .league_seed_transfer import TransferSpec, create_owned_stage, fetch_declared
except ImportError:
    from league_seed_archive import inspect_snapshot
    from league_seed_transfer import TransferSpec, create_owned_stage, fetch_declared


class SeedPreparationError(ValueError):
    """A candidate file remains and its pathname may have been exchanged."""
    def __init__(self, candidate, close_error):
        self.candidate = candidate
        self.path_verified = False
        self.close_error = close_error
        self.actual_cost_known = False
        super().__init__('seed preparation failed; candidate path is untrusted: ' + str(candidate))


_SNAPSHOT_FACTORY = object()


@dataclass(frozen=True, slots=True)
class PreparedSnapshot:
    """Retain the exact immutable bytes inspected, not a reopened pathname."""
    _lease: object = field(repr=False, compare=False)
    _snapshot: bytes = field(repr=False, compare=False)
    _sha256: str
    _bytes: int
    _transfer_json: bytes = field(repr=False, compare=False)
    _inspection_json: bytes = field(repr=False, compare=False)
    _factory: object = field(repr=False, compare=False)

    def __post_init__(self):
        if (self._factory is not _SNAPSHOT_FACTORY or type(self._snapshot) is not bytes
                or type(self._bytes) is not int or len(self._snapshot) != self._bytes
                or hashlib.sha256(self._snapshot).hexdigest() != self._sha256):
            raise ValueError('verified immutable bytes snapshot required')

    @property
    def snapshot(self):
        # This checks the object's own pin; it is not independently trusted.
        if len(self._snapshot) != self._bytes or hashlib.sha256(self._snapshot).hexdigest() != self._sha256:
            raise ValueError('verified snapshot changed')
        return self._snapshot

    def verify_for(self, spec):
        """Revalidate against an independently supplied request before use.

        Dataclass construction, Python code in this process and supplied pins
        are not live authority. This performs the complete archive inspection
        again against the external request and still grants no runtime/GO right.
        """
        if type(spec) is not TransferSpec:
            raise ValueError('independent transfer spec required')
        r = spec.request
        recorded = self.transfer
        expected = {'plan_sha256': spec.plan.sha256, 'campaign': r.campaign_id,
                    'request': r.record(), 'host_launch_token': spec.host_launch_token,
                    'bucket_region': spec.bucket_region, 'bucket_owner': spec.bucket_owner,
                    'declared_host_role_arn': spec.host_role_arn, 'declared_caller_arn': spec.caller_arn,
                    'archive_sha256': r.seed_archive_sha256, 'archive_bytes': r.seed_archive_bytes}
        quote = {'id': spec.quote.quote_id, 'observed_at': spec.quote.observed_at,
                 'transfer_usd_per_gib': spec.quote.transfer_usd_per_gib,
                 'get_request_usd': spec.quote.get_request_usd}
        canonical = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'),
                                             ensure_ascii=False, allow_nan=False)
        if (type(recorded) is not dict or type(recorded.get('quote')) is not dict
                or any(k not in recorded or canonical(recorded[k]) != canonical(v) for k, v in expected.items())
                or any(k not in recorded['quote'] or canonical(recorded['quote'][k]) != canonical(v)
                       for k, v in quote.items())):
            raise ValueError('declared transfer differs from independently supplied request')
        if self._bytes != r.seed_archive_bytes or self._sha256 != r.seed_archive_sha256:
            raise ValueError('snapshot differs from independently supplied archive pin')
        snapshot = self.snapshot
        inspection = inspect_snapshot(snapshot, expected_archive_sha256=r.seed_archive_sha256,
            expected_archive_bytes=r.seed_archive_bytes, expected_manifest_sha256=r.seed_manifest_sha256,
            expected_origin={'repository': r.repository, 'head_sha': r.source_head,
                             'run_id': r.producer_run_id, 'run_attempt': r.producer_run_attempt},
            require_workflow_proof=True)
        return snapshot, inspection

    @property
    def transfer(self):
        # Return detached copies; callers cannot mutate the recorded evidence.
        return json.loads(self._transfer_json)

    @property
    def inspection(self):
        return json.loads(self._inspection_json)

    @property
    def quarantine_path(self):
        return self._lease.quarantine_path

    def close(self):
        self._lease.close()


def stage_and_inspect(spec, s3, root):
    """Bound exact-version transfer, FD snapshot and workflow validation.

    On success the caller owns the returned retained lease and immutable
    snapshot. Downstream code must consume `snapshot`, not reopen the path.
    On failure the partial file is preserved, its path may have been replaced,
    and actual AWS request cost remains unknown. There is no automatic retry.
    """
    if type(spec) is not TransferSpec:
        raise ValueError('validated transfer spec required')
    lease = create_owned_stage(root)
    try:
        transfer = fetch_declared(spec, s3, lease)
        snapshot = lease.snapshot()
        r = spec.request
        inspection = inspect_snapshot(snapshot, expected_archive_sha256=r.seed_archive_sha256,
            expected_archive_bytes=r.seed_archive_bytes, expected_manifest_sha256=r.seed_manifest_sha256,
            expected_origin={'repository': r.repository, 'head_sha': r.source_head,
                             'run_id': r.producer_run_id, 'run_attempt': r.producer_run_attempt},
            require_workflow_proof=True)
        canonical = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'),
                                             ensure_ascii=False, allow_nan=False).encode('utf-8')
        return PreparedSnapshot(lease, snapshot, r.seed_archive_sha256, r.seed_archive_bytes,
                                canonical(transfer), canonical(inspection), _SNAPSHOT_FACTORY)
    except BaseException as exc:
        close_error = None
        try:
            lease.close()
        except OSError as close_exc:
            close_error = str(close_exc)
        if not isinstance(exc, Exception):
            if hasattr(exc, 'add_note'):
                exc.add_note('Seed staging candidate may remain and may have been exchanged: '
                             + str(lease.quarantine_path) + '; actual cost is unknown; close error: '
                             + str(close_error))
            raise
        # Client or ZIP exception text may contain untrusted payload or keys.
        raise SeedPreparationError(lease.quarantine_path, close_error) from None
