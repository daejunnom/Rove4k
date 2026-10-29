"""Revalidate a bootstrap envelope against an independent request.

No transported code is imported or run. The complete immutable snapshot is
checked by the established seed validator before being passed to a future
materializer. All request, host, source and client identities remain declared
data; the diagnostic result is never authority for SSM, a host, or GO.
"""
from __future__ import annotations

import hashlib
import io
import zipfile

try:
    from .league_pinned_bootstrap import BootstrapRequest, PinnedEnvelope, validate_declared_receipt
    from .league_seed_archive import inspect_snapshot
except ImportError:
    from league_pinned_bootstrap import BootstrapRequest, PinnedEnvelope, validate_declared_receipt
    from league_seed_archive import inspect_snapshot


def inspect_envelope(request, envelope, *, bootstrap_source):
    """Return the exact checked bytes plus a fresh, non-authoritative receipt.

    Callers must supply request pins from a separate trusted control path. This
    function checks their consistency, not their origin or the actual code that
    is running. Dataclass type or receipt contents are never proof of S3 access.
    """
    if (type(request) is not BootstrapRequest or type(envelope) is not PinnedEnvelope
            or type(bootstrap_source) is not bytes or not 0 < len(bootstrap_source) <= 512 << 10
            or hashlib.sha256(bootstrap_source).hexdigest() != request.bootstrap_sha256
            or type(envelope.archive) is not bytes or type(envelope.loader_sources) is not tuple):
        raise ValueError('independent request, bootstrap source and immutable envelope required')
    try:
        validate_declared_receipt(request, envelope.receipt_json)
        inspection = inspect_snapshot(envelope.archive, expected_archive_sha256=request.archive_sha256,
            expected_archive_bytes=request.archive_bytes, expected_manifest_sha256=request.manifest_sha256,
            expected_origin={'repository': request.repository, 'head_sha': request.source_head,
                             'run_id': request.producer_run_id, 'run_attempt': request.producer_run_attempt},
            require_workflow_proof=True)
        names = tuple(name for name, _ in envelope.loader_sources)
        if names != tuple(pin.name for pin in request.loader_pins):
            raise ValueError('loader list differs from the independent request')
        with zipfile.ZipFile(io.BytesIO(envelope.archive)) as archive:
            for pin, (name, data) in zip(request.loader_pins, envelope.loader_sources):
                if (type(name) is not str or type(data) is not bytes or len(data) != pin.bytes
                        or hashlib.sha256(data).hexdigest() != pin.sha256):
                    raise ValueError('loader bytes differ from the independent pin')
                with archive.open(name, 'r') as source:
                    archived = source.read(pin.bytes + 1)
                if archived != data:
                    raise ValueError('loader bytes differ from the checked snapshot')
    except Exception:
        # Avoid leaking untrusted ZIP names, source bytes or client errors.
        raise ValueError('bootstrap envelope inspection failed') from None
    return envelope.archive, {
        'format': 'rove4k-bootstrap-envelope-inspection-v1',
        'archive_sha256': request.archive_sha256, 'archive_bytes': request.archive_bytes,
        'manifest_sha256': request.manifest_sha256,
        'scope': {'request_fields_compared': True, 'bootstrap_source_pin_compared': True,
                  'declared_loader_bytes_compared': True, 'all_seed_members_checked': True,
                  'workflow_proof_checked': inspection['scope']['workflow_proof_checked'],
                  'actual_s3_access_authenticated': False, 'complete_loader_closure_verified': False,
                  'running_bootstrap_authenticated': False, 'host_authenticated': False,
                  'producer_authenticated': False, 'aws_cost_confirmed': False,
                  'materialized': False, 'runtime_qualified': False, 'go_authorized': False},
    }
