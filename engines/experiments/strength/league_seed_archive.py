"""Inspect one immutable in-memory seed snapshot before any materialization.

This diagnostic helper reuses the cloud-runtime ZIP and traveling-workflow
validators; its deployed source closure must therefore include their complete
dependencies. It never downloads data, opens a path, writes files, imports
transported source or grants host, cost, runtime or score authority.  The
caller must keep this exact immutable snapshot for any subsequent consumer;
reopening a pathname is not bound by this result.
"""
from __future__ import annotations

import hashlib
import io
import re
import zipfile

try:
    from . import cloud_runtime as cloud
except ImportError:
    import cloud_runtime as cloud

_SHA256 = re.compile(r'[0-9a-f]{64}\Z')
_GIT = re.compile(r'(?:[0-9a-f]{40}|[0-9a-f]{64})\Z')
_REPO = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z')
_DECIMAL = re.compile(r'[1-9][0-9]{0,19}\Z')
_CHUNK = 1 << 16


def _origin(value):
    if (type(value) is not dict or set(value) != {'repository', 'head_sha', 'run_id', 'run_attempt'}
            or not all(type(v) is str for v in value.values())
            or not _REPO.fullmatch(value['repository']) or len(value['repository']) > 200
            or not _GIT.fullmatch(value['head_sha'])
            or not _DECIMAL.fullmatch(value['run_id']) or not _DECIMAL.fullmatch(value['run_attempt'])):
        raise ValueError('exact declared producer identity required')
    return dict(value)


def inspect_snapshot(snapshot, *, expected_archive_sha256, expected_archive_bytes,
                     expected_manifest_sha256, expected_origin, require_workflow_proof=True):
    """Validate hashes and ZIP members from the same immutable bytes snapshot.

    `require_workflow_proof=False` explicitly permits historical pin-only seed
    fixtures; it does not claim their producer. Hashes and reconstructed CI
    documents are untrusted declarations until checked by live authority.
    No output, extraction, execution, or external process is performed here.
    """
    origin = _origin(expected_origin)
    if (type(snapshot) is not bytes or type(expected_archive_bytes) is not int
            or not 0 < expected_archive_bytes <= cloud.MAX_SEED
            or len(snapshot) != expected_archive_bytes
            or not isinstance(expected_archive_sha256, str) or not _SHA256.fullmatch(expected_archive_sha256)
            or not isinstance(expected_manifest_sha256, str) or not _SHA256.fullmatch(expected_manifest_sha256)
            or type(require_workflow_proof) is not bool):
        raise ValueError('bounded immutable snapshot and explicit pins required')
    if hashlib.sha256(snapshot).hexdigest() != expected_archive_sha256:
        raise ValueError('seed archive bytes differ from the controller pin')
    try:
        with zipfile.ZipFile(io.BytesIO(snapshot)) as archive:
            # ZipInfo can normalize platform separators or truncate at NUL;
            # reject such names instead of validating only their aliases.
            if any(info.orig_filename != info.filename for info in archive.infolist()):
                raise ValueError('seed ZIP member name was normalized')
            manifest, manifest_raw, infos = cloud.seed_archive_manifest(
                archive, expected_manifest_sha256=expected_manifest_sha256)
            if manifest['source_origin'] != origin:
                raise ValueError('seed producer identity differs from declared origin')
            for info in infos:
                if info.filename == 'seed.json':
                    continue
                expected = manifest['members'][info.filename]
                digest = hashlib.sha256()
                count = 0
                with archive.open(info, 'r') as source:
                    while True:
                        body = source.read(min(_CHUNK, expected['bytes'] + 1 - count))
                        if not body:
                            break
                        count += len(body)
                        if count > expected['bytes']:
                            raise ValueError('seed member exceeds its pinned length')
                        digest.update(body)
                if count != expected['bytes'] or digest.hexdigest() != expected['sha256']:
                    raise ValueError('seed member differs from its pin: ' + info.filename)

            def read_proof(name):
                # The cloud schema already pins each proof to <= 4 MiB.
                with archive.open(name, 'r') as source:
                    return source.read(cloud.MAX_SEED_MANIFEST + 1)

            proof = cloud.validate_workflow_provenance(manifest, read_proof)
            if require_workflow_proof and proof is None:
                raise ValueError('explicit traveling workflow proof required')
    except (zipfile.BadZipFile, EOFError, NotImplementedError) as exc:
        raise ValueError('invalid or unsupported seed ZIP') from exc
    return {
        'format': 'rove4k-league-seed-snapshot-v1',
        'archive_sha256': expected_archive_sha256, 'archive_bytes': len(snapshot),
        'manifest_sha256': hashlib.sha256(manifest_raw).hexdigest(),
        'member_count': len(infos) - 1, 'declared_origin': origin,
        'scope': {'archive_pin_checked': True, 'manifest_and_members_checked': True,
                  'workflow_proof_checked': proof is not None,
                  'host_authenticated': False, 'producer_authenticated': False,
                  'aws_cost_confirmed': False, 'materialized': False,
                  'runtime_qualified': False, 'launch_authorized': False, 'go_authorized': False},
    }
