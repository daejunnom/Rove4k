"""Pre-seed, standard-library-only diagnostic bootstrap.

Caller-supplied pins and identity strings are declarations, not a live
authority. This module performs no imports from the fetched seed, does not
execute fetched Python, write paths, materialize files, discover credentials,
launch a host, dispatch SSM, or authorize a game. An independently trusted
outer launcher must bind the actual running bootstrap and its whole loader
closure before using the returned bytes. No source or payload is logged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import io
import json
from pathlib import PurePosixPath
import re
import stat
import struct
import zipfile

_HEX = re.compile(r'[0-9a-f]{64}\Z')
_GIT = re.compile(r'[0-9a-f]{40}\Z')
_REGION = re.compile(r'[a-z]{2}(?:-gov)?-[a-z]+-[0-9]+\Z')
_INSTANCE = re.compile(r'i-[0-9a-f]{17}\Z')
_BOOT = re.compile(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\Z')
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z')
_BUCKET = re.compile(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]\Z')
_ROLE = re.compile(r'arn:aws:iam::([0-9]{12}):role/([A-Za-z0-9_+=,.@/-]+)\Z')
_DENIED = {'.git', '.aws', '.ssh', 'node_modules', 'dist', 'dist-server', 'coverage',
           'models', 'checkpoints', '.cache', 'inventory.json', 'package-lock.json'}
_MAX_ARCHIVE = 128 << 20
_MAX_MANIFEST = 4 << 20
_MAX_MEMBER = 32 << 20
_MAX_MEMBERS = 20000
_CHUNK = 1 << 20


def _member(value):
    if (type(value) is not str or not value or len(value.encode('utf-8', 'surrogatepass')) > 4096
            or '\\' in value or ':' in value or '\0' in value or PurePosixPath(value).is_absolute()):
        raise ValueError('invalid logical seed member')
    parts = value.split('/')
    if any(part in ('', '.', '..') or part.casefold() in _DENIED or part.casefold().startswith('.env')
           or re.search(r'credential|service[-_ ]?account|api[-_ ]?key|ssh[-_ ]?key|^id_(rsa|ed25519)$', part, re.I)
           or any(ord(c) < 32 or 127 <= ord(c) < 160 or 0xd800 <= ord(c) <= 0xdfff for c in part)
           for part in parts):
        raise ValueError('protected or non-normalized logical seed member')
    return value


def _json(raw):
    def unique(pairs):
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError('duplicate JSON member')
        return result
    def reject(_value):
        raise ValueError('non-finite JSON number')
    return json.loads(raw, object_pairs_hook=unique, parse_constant=reject)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8') + b'\n'


@dataclass(frozen=True)
class LoaderPin:
    name: str
    sha256: str
    bytes: int

    def __post_init__(self):
        _member(self.name)
        if (not isinstance(self.sha256, str) or not _HEX.fullmatch(self.sha256)
                or type(self.bytes) is not int or not 0 < self.bytes <= _MAX_MEMBER):
            raise ValueError('bounded independently supplied loader pin required')


@dataclass(frozen=True)
class BootstrapRequest:
    campaign: str
    plan_sha256: str
    bucket: str
    bucket_region: str
    bucket_owner: str
    key: str
    version_id: str
    archive_sha256: str
    archive_bytes: int
    manifest_sha256: str
    repository: str
    source_head: str
    producer_run_id: str
    producer_run_attempt: str
    host_account: str
    host_region: str
    host_instance_id: str
    host_boot_id: str
    host_launch_token: str
    profile: str
    host_role_arn: str
    caller_arn: str
    transfer_quote_id: str
    quote_observed_at: int
    bootstrap_sha256: str
    loader_pins: tuple[LoaderPin, ...]

    def __post_init__(self):
        if (not isinstance(self.campaign, str) or not _ID.fullmatch(self.campaign)
                or not self.campaign.startswith('league-')
                or not all(isinstance(x, str) and _HEX.fullmatch(x) for x in
                           (self.plan_sha256, self.archive_sha256, self.manifest_sha256, self.bootstrap_sha256))
                or not isinstance(self.bucket, str) or not _BUCKET.fullmatch(self.bucket)
                or not isinstance(self.bucket_region, str) or not _REGION.fullmatch(self.bucket_region)
                or not isinstance(self.host_region, str) or not _REGION.fullmatch(self.host_region)
                or not isinstance(self.host_account, str) or not re.fullmatch(r'[0-9]{12}', self.host_account)
                or self.bucket_owner != self.host_account
                or not isinstance(self.host_instance_id, str) or not _INSTANCE.fullmatch(self.host_instance_id)
                or not isinstance(self.host_boot_id, str) or not _BOOT.fullmatch(self.host_boot_id)
                or self.host_boot_id == '00000000-0000-0000-0000-000000000000'
                or not isinstance(self.host_launch_token, str)
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{7,63}', self.host_launch_token)
                or self.profile not in ('test-p16', 'test-p192')
                or not isinstance(self.transfer_quote_id, str) or not _ID.fullmatch(self.transfer_quote_id)
                or type(self.quote_observed_at) is not int or self.quote_observed_at <= 0
                or type(self.archive_bytes) is not int or not 0 < self.archive_bytes <= _MAX_ARCHIVE
                or self.repository != 'daejunnom/Rove4k'
                or not isinstance(self.source_head, str) or not _GIT.fullmatch(self.source_head)
                or not all(isinstance(x, str) and re.fullmatch(r'[1-9][0-9]{0,19}', x)
                           for x in (self.producer_run_id, self.producer_run_attempt))):
            raise ValueError('explicit bounded source, host, account and archive pins required')
        if (not isinstance(self.key, str) or not self.key.startswith(self.campaign + '/seed/')
                or len(self.key.encode('utf-8', 'surrogatepass')) > 1024):
            raise ValueError('campaign-bound seed key required')
        _member(self.key)
        if (not isinstance(self.version_id, str) or self.version_id in ('', 'null')
                or len(self.version_id.encode('utf-8', 'surrogatepass')) > 1024
                or any(ord(c) < 32 or 127 <= ord(c) < 160 or 0xd800 <= ord(c) <= 0xdfff
                       for c in self.version_id)):
            raise ValueError('immutable S3 VersionId required')
        role = _ROLE.fullmatch(self.host_role_arn) if isinstance(self.host_role_arn, str) else None
        if (role is None or role.group(1) != self.host_account or any(not x for x in role.group(2).split('/'))
                or self.caller_arn != f'arn:aws:sts::{self.host_account}:assumed-role/'
                                      f'{role.group(2).split("/")[-1]}/{self.host_instance_id}'):
            raise ValueError('declared role and EC2 session differ')
        if (type(self.loader_pins) is not tuple or not 1 <= len(self.loader_pins) <= 64
                or any(type(pin) is not LoaderPin for pin in self.loader_pins)
                or len({pin.name for pin in self.loader_pins}) != len(self.loader_pins)):
            raise ValueError('bounded distinct loader pins required')


@dataclass(frozen=True)
class PinnedEnvelope:
    """Opaque in-memory bytes; repr never prints archive or loader contents."""
    archive: bytes = field(repr=False)
    loader_sources: tuple[tuple[str, bytes], ...] = field(repr=False)
    receipt_json: bytes

    @property
    def receipt(self):
        # A fresh copy prevents mutations to one consumer's view from changing
        # the pinned receipt held by this envelope. This is not authentication.
        return _json(self.receipt_json)


def _bounded_get(request, s3):
    try:
        region = getattr(getattr(s3, 'meta', None), 'region_name', None)
    except Exception:
        raise ValueError('S3 client region unavailable') from None
    if type(region) is not str or region != request.bucket_region:
        raise ValueError('S3 client region differs from source bucket')
    try:
        response = s3.get_object(Bucket=request.bucket, Key=request.key, VersionId=request.version_id,
                                 ExpectedBucketOwner=request.bucket_owner)
    except Exception:
        raise ValueError('S3 request failed') from None
    if type(response) is not dict:
        raise ValueError('invalid S3 response')
    body = response.get('Body')
    if body is None:
        raise ValueError('missing S3 response body')
    result, digest, total = bytearray(), hashlib.sha256(), 0
    try:
        if (type(response.get('VersionId')) is not str or response['VersionId'] != request.version_id
                or type(response.get('ContentLength')) is not int
                or response['ContentLength'] != request.archive_bytes):
            raise ValueError('S3 version or size differs')
        while total <= request.archive_bytes:
            wanted = min(_CHUNK, request.archive_bytes + 1 - total)
            try:
                chunk = body.read(wanted)
            except Exception:
                raise ValueError('S3 body read failed') from None
            if type(chunk) is not bytes or len(chunk) > wanted:
                raise ValueError('invalid S3 body chunk')
            if not chunk:
                break
            total += len(chunk)
            if total > request.archive_bytes:
                raise ValueError('S3 body exceeds pinned size')
            result.extend(chunk)
            digest.update(chunk)
    finally:
        try:
            body.close()
        except Exception:
            raise ValueError('S3 body close failed') from None
    if total != request.archive_bytes or digest.hexdigest() != request.archive_sha256:
        raise ValueError('S3 archive pin differs')
    return bytes(result)


def _bounded_zip_directory(data):
    """Bound ZIP metadata before ZipFile creates an object for each entry.

    League seed archives fit non-ZIP64 limits; multi-disk/ZIP64 and archives
    with an appended trailer are outside this bootstrap's explicit contract.
    """
    pos = data.rfind(b'PK\x05\x06', max(0, len(data) - 65557))
    if pos < 0 or len(data) - pos < 22:
        raise ValueError('missing bounded ZIP end record')
    try:
        _signature, disk, directory_disk, on_disk, entries, size, offset, comment = struct.unpack_from('<4s4H2LH', data, pos)
    except struct.error as exc:
        raise ValueError('truncated ZIP end record') from exc
    if (disk != 0 or directory_disk != 0 or on_disk != entries or not 1 <= entries <= _MAX_MEMBERS
            or entries == 0xffff or size == 0xffffffff or offset == 0xffffffff
            or pos + 22 + comment != len(data) or offset + size != pos):
        raise ValueError('unsupported ZIP directory size, disks or trailer')
    cursor = offset
    for _ in range(entries):
        if cursor + 46 > pos:
            raise ValueError('truncated ZIP directory entry')
        try:
            fields = struct.unpack_from('<4s6H3L5H2L', data, cursor)
        except struct.error as exc:
            raise ValueError('invalid ZIP directory entry') from exc
        if (fields[0] != b'PK\x01\x02' or fields[8] == 0xffffffff or fields[9] == 0xffffffff
                or fields[13] != 0 or fields[16] == 0xffffffff):
            raise ValueError('unsupported ZIP64 or invalid directory entry')
        cursor += 46 + fields[10] + fields[11] + fields[12]
        if cursor > pos:
            raise ValueError('ZIP directory entry exceeds its bounds')
    if cursor != pos:
        raise ValueError('ZIP directory size or count differs')


def _checked_loader_sources(request, data):
    _bounded_zip_directory(data)
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, ValueError):
        raise ValueError('invalid seed archive') from None
    with archive:
        infos = archive.infolist()
        if not 1 <= len(infos) <= _MAX_MEMBERS:
            raise ValueError('seed member count exceeds bound')
        names = {}
        expanded = 0
        for info in infos:
            name = _member(info.filename)
            mode = info.external_attr >> 16
            if (info.orig_filename != info.filename or name in names or info.is_dir() or info.flag_bits & 1
                    or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                    or type(info.file_size) is not int or info.file_size < 0
                    or info.file_size > (_MAX_MANIFEST if name == 'seed.json' else _MAX_MEMBER)):
                raise ValueError('duplicate, linked or excessive seed member')
            expanded += info.file_size
            names[name] = info
        if expanded > _MAX_ARCHIVE or 'seed.json' not in names:
            raise ValueError('P16/P192 seed expansion exceeds bound or manifest is missing')
        with archive.open(names['seed.json']) as source:
            raw = source.read(_MAX_MANIFEST + 1)
        if len(raw) != names['seed.json'].file_size or hashlib.sha256(raw).hexdigest() != request.manifest_sha256:
            raise ValueError('manifest pin differs')
        manifest = _json(raw)
        if type(manifest) is not dict or _canonical(manifest) != raw or manifest.get('format') != 'rove4k-cloud-seed-v1':
            raise ValueError('canonical seed manifest required')
        origin = manifest.get('source_origin')
        if (type(origin) is not dict or set(origin) != {'repository', 'head_sha', 'run_id', 'run_attempt'}
                or origin['repository'] != request.repository or origin['head_sha'] != request.source_head
                or any(type(origin[k]) not in (str, int) for k in ('run_id', 'run_attempt'))
                or str(origin['run_id']) != request.producer_run_id
                or str(origin['run_attempt']) != request.producer_run_attempt or any(k in manifest for k in
                ('qualified', 'complete', 'registry', 'native_map', 'scoring'))):
            raise ValueError('seed origin or qualification scope differs')
        members = manifest.get('members')
        if type(members) is not dict or not members or set(names) != {'seed.json', *members}:
            raise ValueError('archive and manifest member set differs')
        tree = _member(manifest.get('source_tree'))
        required_runtime = tree + '/engines/experiments/strength/cloud_runtime.py'
        if required_runtime not in {pin.name for pin in request.loader_pins}:
            raise ValueError('independent cloud runtime pin required')
        result = []
        for pin in request.loader_pins:
            if not pin.name.startswith(tree + '/'):
                raise ValueError('loader must belong to declared source tree')
            member = members.get(pin.name)
            if (type(member) is not dict or set(member) != {'bytes', 'sha256', 'mode'}
                    or type(member['mode']) is not int or member['mode'] not in (0o600, 0o700)
                    or type(member['bytes']) is not int
                    or member['bytes'] != pin.bytes or member['sha256'] != pin.sha256
                    or names[pin.name].file_size != pin.bytes):
                raise ValueError('loader manifest and external pins differ')
            with archive.open(names[pin.name]) as source:
                raw_source = source.read(pin.bytes + 1)
            if len(raw_source) != pin.bytes or hashlib.sha256(raw_source).hexdigest() != pin.sha256:
                raise ValueError('loader body differs from independent pin')
            result.append((pin.name, raw_source))
    return tuple(result)


def _loader_sources(request, data):
    # Untrusted ZIP/parser exceptions can contain untrusted names or bytes.
    try:
        return _checked_loader_sources(request, data)
    except Exception:
        raise ValueError('seed loader verification failed') from None


def _receipt_for(request):
    return {
        'format': 'rove4k-pinned-bootstrap-diagnostic-v1', 'plan_sha256': request.plan_sha256,
        'campaign': request.campaign, 'bucket': request.bucket, 'key': request.key,
        'bucket_region': request.bucket_region,
        'bucket_owner': request.bucket_owner, 'version_id': request.version_id,
        'archive_sha256': request.archive_sha256, 'archive_bytes': request.archive_bytes,
        'manifest_sha256': request.manifest_sha256, 'repository': request.repository,
        'source_head': request.source_head, 'producer_run_id': request.producer_run_id,
        'producer_run_attempt': request.producer_run_attempt, 'bootstrap_sha256': request.bootstrap_sha256,
        'host_region': request.host_region,
        'host_account': request.host_account, 'host_instance_id': request.host_instance_id,
        'host_boot_id': request.host_boot_id, 'host_launch_token': request.host_launch_token,
        'profile': request.profile, 'declared_host_role_arn': request.host_role_arn,
        'declared_caller_arn': request.caller_arn,
        'transfer_quote_id': request.transfer_quote_id, 'quote_observed_at': request.quote_observed_at,
        'loader_pins': [{'name': pin.name, 'sha256': pin.sha256, 'bytes': pin.bytes} for pin in request.loader_pins],
        'estimated_transfer_bytes': request.archive_bytes,
        'scope': {'expected_bucket_owner_requested': True, 'archive_pin_checked': True,
                  'manifest_pin_checked': True, 'listed_loader_pins_checked': True,
                  'bootstrap_source_pin_checked': True, 'running_bootstrap_authenticated': False,
                  'complete_loader_closure_verified': False, 'host_authenticated': False,
                  'producer_authenticated': False, 'all_seed_members_verified': False,
                  'actual_cost_confirmed': False, 'materialized': False, 'go_authorized': False},
    }


def validate_declared_receipt(request: BootstrapRequest, receipt_json: bytes):
    """Compare all declared fields; this is not producer/host authentication."""
    if type(request) is not BootstrapRequest or type(receipt_json) is not bytes or len(receipt_json) > 1 << 20:
        raise ValueError('bounded receipt and typed request required')
    if receipt_json != _canonical(_receipt_for(request)):
        raise ValueError('bootstrap receipt differs from declared request')
    return {'matches_declared_request': True, 'actual_fetch_proven': False,
            'receipt_origin_authenticated': False, 'producer_authenticated': False,
            'host_authenticated': False, 'go_authorized': False}


def fetch_for_verified_loader(request: BootstrapRequest, s3, *, bootstrap_source: bytes):
    """Retrieve a pinned snapshot, but never import or execute its loader.

    A verified outer prelude must establish that bootstrap_source corresponds to
    the running code, authenticate the plan/host and independently validate the
    entire loader closure. These cannot be established by hashes supplied by an
    arbitrary caller, and are explicitly unclaimed in the returned receipt.
    Client timeouts/retries, actual costs, and physical host ownership are also
    outside this in-memory diagnostic interface.
    """
    if type(request) is not BootstrapRequest or type(bootstrap_source) is not bytes or not 0 < len(bootstrap_source) <= 512 << 10:
        raise ValueError('typed request and bounded bootstrap source required')
    if hashlib.sha256(bootstrap_source).hexdigest() != request.bootstrap_sha256:
        raise ValueError('bootstrap source pin differs')
    data = _bounded_get(request, s3)
    sources = _loader_sources(request, data)
    return PinnedEnvelope(data, sources, _canonical(_receipt_for(request)))
