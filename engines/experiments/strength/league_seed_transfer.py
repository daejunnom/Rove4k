"""Bounded, owner-requested seed GET for a declared league host.

The supplied plan, request, caller identity and price quote are declarations.
This module does not discover credentials, authenticate the host or source,
materialize ZIP contents, approve costs, dispatch SSM, or authorize GO.  The
caller owns an empty read/write file descriptor and must quarantine it on any
failure; no path is opened, replaced, removed, or retried here. Before use the
caller must create a dedicated private staging file with exclusive/no-follow
semantics outside protected and existing user paths. This module cannot prove
that path ownership or authenticate the caller from an arbitrary descriptor.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import os
from pathlib import Path
import re
import stat
import threading

try:
    from .league_controller import LeaguePlan
    from .league_ssm_dispatch import Request, PeerRequest
except ImportError:
    from league_controller import LeaguePlan
    from league_ssm_dispatch import Request, PeerRequest

_ROLE = re.compile(r'arn:aws:iam::([0-9]{12}):role/([A-Za-z0-9_+=,.@/-]+)\Z')
_QUOTE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z')
_CHUNK = 1 << 20
_PROTECTED = {'.git', '.aws', '.ssh', 'node_modules', 'dist', 'dist-server',
              'build', 'coverage', 'models', 'checkpoints', '.cache',
              'inventory.json', 'package-lock.json'}
_PROTECTED_PATTERN = re.compile(r'credential|service[-_ ]?account|api[-_ ]?key|ssh[-_ ]?key|'
                                r'private[-_ ]?key|password|^id_(rsa|ed25519)$', re.I)


def _rate(value):
    if not isinstance(value, str) or len(value) > 32:
        raise ValueError('explicit bounded decimal price required')
    try:
        rate = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('invalid decimal price') from exc
    if not rate.is_finite() or rate < 0 or rate > 1000000:
        raise ValueError('invalid decimal price')
    return rate


@dataclass(frozen=True)
class TransferQuote:
    """Recorded quote, not an AWS bill or spending authority."""
    quote_id: str
    observed_at: int
    transfer_usd_per_gib: str
    get_request_usd: str

    def __post_init__(self):
        if (not isinstance(self.quote_id, str) or not _QUOTE_ID.fullmatch(self.quote_id)
                or type(self.observed_at) is not int or self.observed_at <= 0):
            raise ValueError('quote identity and observation time required')
        _rate(self.transfer_usd_per_gib)
        _rate(self.get_request_usd)


@dataclass(frozen=True)
class TransferSpec:
    plan: LeaguePlan
    request: Request | PeerRequest
    host_launch_token: str
    bucket_region: str
    bucket_owner: str
    host_role_arn: str
    caller_arn: str
    quote: TransferQuote

    def __post_init__(self):
        p, r = self.plan, self.request
        if type(p) is not LeaguePlan or type(r) not in (Request, PeerRequest) or type(self.quote) is not TransferQuote:
            raise ValueError('typed league plan, request and quote required')
        hosts = [h for h in p.hosts if h.launch_token == self.host_launch_token]
        if (len(hosts) != 1 or r.campaign_id != p.campaign or r.account_id != p.account
                or r.region != hosts[0].region or r.profile not in (hosts[0].profile, *hosts[0].later_profiles)
                or self.bucket_region != p.home_region or self.bucket_owner != p.account
                or r.seed_bucket != p.bucket):
            raise ValueError('seed, account, host and home region must match the league plan')
        if (p.table.split(':', 5)[3] != p.home_region
                or p.watchdog_arn.split(':', 5)[3] != p.home_region):
            raise ValueError('controller resources must remain in the home region')
        role = _ROLE.fullmatch(self.host_role_arn) if isinstance(self.host_role_arn, str) else None
        if (role is None or role.group(1) != p.account
                or any(not part for part in role.group(2).split('/'))):
            raise ValueError('declared host role must belong to the plan account')
        # EC2 instance-profile session name is the instance ID.  Both strings
        # are caller-supplied assertions, not an STS or IMDS authentication.
        expected = f'arn:aws:sts::{p.account}:assumed-role/{role.group(2).split("/")[-1]}/{r.instance_id}'
        if self.caller_arn != expected:
            raise ValueError('declared caller role/session does not match the host')


def _file_state(fd):
    if type(fd) is not int or fd < 0:
        raise ValueError('caller-owned file descriptor required')
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        raise ValueError('output must be a single-link regular file')
    return st


def _identity(st):
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def _fetch_to_owned(spec: TransferSpec, s3, fd: int):
    """Fetch and re-read exactly one pinned version into caller-owned *fd*.

    The output must be an empty read/write regular file supplied by the caller.
    On errors it may contain partial or untrusted data and must be quarantined.
    Supplying a mock/compromised client can forge response metadata; caller and
    host assertions require a separate live authority.  The FD may be changed
    after return, so a later materializer must recheck the archive pin.
    """
    if type(spec) is not TransferSpec:
        raise ValueError('validated transfer spec required')
    if not hasattr(os, 'pread') or not hasattr(os, 'pwrite'):
        raise ValueError('positioned I/O support required for a retained output descriptor')
    try:
        client_region = getattr(getattr(s3, 'meta', None), 'region_name', None)
    except Exception:
        raise ValueError('S3 client region unavailable') from None
    if type(client_region) is not str or client_region != spec.bucket_region:
        raise ValueError('S3 client must target the declared source bucket region')
    st = _file_state(fd)
    if st.st_size != 0:
        raise ValueError('new empty output file required')
    try:
        # Zero-length operations validate access mode without modifying data.
        os.read(fd, 0)
        os.write(fd, b'')
    except OSError as exc:
        raise ValueError('read/write output file descriptor required') from exc
    r = spec.request
    try:
        response = s3.get_object(Bucket=r.seed_bucket, Key=r.seed_key,
                                 VersionId=r.seed_version_id, ExpectedBucketOwner=spec.bucket_owner)
    except Exception:
        raise ValueError('S3 request failed') from None
    if type(response) is not dict:
        raise ValueError('invalid S3 response')
    body = response.get('Body')
    if body is None:
        raise ValueError('missing S3 response body')
    total = 0
    digest = hashlib.sha256()
    try:
        if response.get('VersionId') != r.seed_version_id or type(response.get('ContentLength')) is not int or response['ContentLength'] != r.seed_archive_bytes:
            raise ValueError('S3 version or declared length differs')
        while total <= r.seed_archive_bytes:
            wanted = min(_CHUNK, r.seed_archive_bytes + 1 - total)
            try:
                chunk = body.read(wanted)
            except Exception:
                raise ValueError('S3 body read failed') from None
            if not isinstance(chunk, bytes):
                raise ValueError('S3 body must produce bytes')
            if len(chunk) > wanted:
                raise ValueError('S3 body exceeded requested chunk')
            if not chunk:
                break
            total += len(chunk)
            if total > r.seed_archive_bytes:
                raise ValueError('S3 body exceeds declared length')
            digest.update(chunk)
            offset = 0
            while offset < len(chunk):
                count = os.pwrite(fd, chunk[offset:], total - len(chunk) + offset)
                if count <= 0:
                    raise ValueError('short output write')
                offset += count
    finally:
        try:
            body.close()
        except Exception:
            raise ValueError('S3 body close failed') from None
    if total != r.seed_archive_bytes or digest.hexdigest() != r.seed_archive_sha256:
        raise ValueError('S3 body length or digest differs')
    os.fsync(fd)
    before = _file_state(fd)
    if (before.st_dev, before.st_ino) != (st.st_dev, st.st_ino) or before.st_size != total:
        raise ValueError('output identity or length changed')
    verified = hashlib.sha256()
    remaining = total
    while remaining:
        chunk = os.pread(fd, min(_CHUNK, remaining), total - remaining)
        if not chunk:
            raise ValueError('short output readback')
        verified.update(chunk)
        remaining -= len(chunk)
    after = _file_state(fd)
    if _identity(before) != _identity(after) or verified.hexdigest() != r.seed_archive_sha256:
        raise ValueError('output changed during readback')
    estimate = (_rate(spec.quote.transfer_usd_per_gib) * Decimal(total) / Decimal(1 << 30)
                + _rate(spec.quote.get_request_usd))
    return {
        'format': 'rove4k-league-seed-transfer-v1', 'plan_sha256': spec.plan.sha256,
        'campaign': r.campaign_id, 'request': r.record(), 'host_launch_token': spec.host_launch_token,
        'bucket_region': spec.bucket_region, 'bucket_owner': spec.bucket_owner,
        'declared_host_role_arn': spec.host_role_arn, 'declared_caller_arn': spec.caller_arn,
        'archive_sha256': digest.hexdigest(), 'archive_bytes': total,
        'quote': {'id': spec.quote.quote_id, 'observed_at': spec.quote.observed_at,
                  'transfer_usd_per_gib': spec.quote.transfer_usd_per_gib,
                  'get_request_usd': spec.quote.get_request_usd,
                  'estimated_usd': str(estimate)},
        'scope': {'expected_bucket_owner_requested': True, 'response_pin_checked': True,
                  'file_readback_checked': True, 'staging_ownership_authenticated': False,
                  'host_authenticated': False, 'caller_authenticated': False,
                  'timeouts_verified': False,
                  'producer_authenticated': False, 'materialized': False,
                  'aws_cost_confirmed': False, 'launch_authorized': False, 'go_authorized': False},
    }


def _fetch_declared_with_fd(spec: TransferSpec, s3, fd: int):
    """Retain a private duplicate while the caller may close its descriptor.

    Duplication is checked against the initial inode before any remote call.
    This does not exclude other writers to that inode, arbitrary threads that
    close our private descriptor, or mutations after return. Positioned I/O
    prevents a caller seek from changing the transfer offsets. The supplied S3
    client remains responsible for bounded connect/read timeouts and retries;
    this diagnostic function does not provide a total deadline or admission.
    """
    before = _file_state(fd)
    owned = os.dup(fd)
    try:
        if _identity(_file_state(owned)) != _identity(before):
            raise ValueError('caller output changed while retaining it')
        return _fetch_to_owned(spec, s3, owned)
    finally:
        # Never retry a failed close: the descriptor number may be recycled.
        os.close(owned)


def _safe_stage_root(root):
    """Open a pre-existing private staging directory without following links.

    Protected path names and Git ancestry are rejected before creating files.
    This is a process-local path check, not isolation against the same UID.
    """
    if (os.name != 'posix' or not hasattr(os, 'O_DIRECTORY') or not hasattr(os, 'O_NOFOLLOW')
            or not hasattr(os, 'pread') or not hasattr(os, 'pwrite')):
        raise ValueError('Linux/POSIX no-follow positioned I/O is required')
    if not isinstance(root, (str, Path)):
        raise ValueError('explicit absolute staging root required')
    raw = os.fspath(root)
    if (not isinstance(raw, str) or not raw.startswith('/') or '\x00' in raw
            or os.path.normpath(raw) != raw or raw == '/'):
        raise ValueError('normalized absolute private staging root required')
    parts = Path(raw).parts
    for part in parts[1:]:
        lower = part.casefold()
        if (lower in _PROTECTED or lower.startswith('.env') or _PROTECTED_PATTERN.search(part)
                or any(ord(c) < 32 or 127 <= ord(c) < 160 for c in part)):
            raise ValueError('protected staging path')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)
    current = os.open('/', flags)
    try:
        for part in parts[1:]:
            try:
                os.stat('.git', dir_fd=current, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise ValueError('staging inside a Git checkout is forbidden')
            child = os.open(part, flags, dir_fd=current)
            try:
                entry = os.stat(part, dir_fd=current, follow_symlinks=False)
                opened = os.fstat(child)
                if (not stat.S_ISDIR(entry.st_mode) or
                        (entry.st_dev, entry.st_ino) != (opened.st_dev, opened.st_ino)):
                    raise ValueError('staging directory changed during open')
            except BaseException:
                os.close(child)
                raise
            old, current = current, child
            os.close(old)
        try:
            os.stat('.git', dir_fd=current, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError('staging inside a Git checkout is forbidden')
        st = os.fstat(current)
        if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != 0o700:
            raise ValueError('pre-existing private owned 0700 staging directory required')
        result, current = current, None
        return Path(raw), result
    finally:
        if current is not None:
            os.close(current)


_FACTORY_TOKEN = object()
_STAGE_NAME = re.compile(r'seed-[0-9a-f]{32}\.zip\Z')


class StageCreationError(ValueError):
    """A newly created path may remain; it might have been exchanged."""
    def __init__(self, candidate, close_errors):
        self.candidate = candidate
        self.path_verified = False
        self.close_errors = close_errors
        super().__init__('new staging path may remain and may have been exchanged: ' + str(candidate))


class OwnedStage:
    """Exclusive file in a pre-existing private root, retaining both FDs.

    `close` never removes the file. On failure preserve it as untrusted and use
    a fresh stage for retry. Other same-UID writers, root replacement between
    observations, crash recovery and data changes after return remain outside
    this process-local contract.
    """
    def __init__(self, root, directory, name, fd, *, _factory=None):
        if _factory is not _FACTORY_TOKEN or not isinstance(name, str) or not _STAGE_NAME.fullmatch(name):
            raise ValueError('staging lease requires the exclusive creation factory')
        self.root, self.name = root, name
        self._directory, self._fd = directory, fd
        directory_state, file_state = os.fstat(directory), _file_state(fd)
        self._directory_id = (directory_state.st_dev, directory_state.st_ino)
        self._file_id = (file_state.st_dev, file_state.st_ino)
        self._lock = threading.RLock()
        self._closed = False
        self._failed = False
        self._pin = None

    @property
    def quarantine_path(self):
        """Candidate path only; a replacement may have occurred after failure."""
        return self.root / self.name

    def _check(self):
        if self._closed:
            raise ValueError('staging lease is closed')
        if not isinstance(self.name, str) or not _STAGE_NAME.fullmatch(self.name):
            raise ValueError('staging filename changed')
        directory = os.fstat(self._directory)
        if ((directory.st_dev, directory.st_ino) != self._directory_id
                or directory.st_uid != os.geteuid() or stat.S_IMODE(directory.st_mode) != 0o700):
            raise ValueError('owned staging directory changed')
        _, current = _safe_stage_root(self.root)
        try:
            observed = os.fstat(current)
            if (observed.st_dev, observed.st_ino) != self._directory_id:
                raise ValueError('staging root path no longer identifies the owned directory')
            entry = os.stat(self.name, dir_fd=current, follow_symlinks=False)
            held = _file_state(self._fd)
            if (not stat.S_ISREG(entry.st_mode) or entry.st_nlink != 1 or
                    (entry.st_dev, entry.st_ino) != self._file_id or
                    (held.st_dev, held.st_ino) != self._file_id or
                    entry.st_uid != os.geteuid() or held.st_uid != os.geteuid() or
                    stat.S_IMODE(entry.st_mode) != 0o600 or stat.S_IMODE(held.st_mode) != 0o600):
                raise ValueError('staging pathname no longer identifies the owned file')
        finally:
            os.close(current)

    def fetch(self, spec, s3):
        with self._lock:
            if self._failed or self._pin is not None:
                raise ValueError('stage cannot be reused')
            try:
                self._check()
                receipt = _fetch_to_owned(spec, s3, self._fd)
                self._check()
                os.fsync(self._directory)
                self._pin = (spec.request.seed_archive_bytes, spec.request.seed_archive_sha256)
                receipt['scope']['exclusive_stage_inode_checked'] = True
                # A matching inode is not independently authenticated host or source ownership.
                return receipt
            except BaseException:
                self._failed = True
                raise

    def snapshot(self):
        """Read bounded pinned bytes from the retained FD for a verifier.

        The caller must pass these exact bytes to archive verification; reopening
        `quarantine_path` for materialization does not preserve this binding.
        """
        with self._lock:
            if self._failed or self._pin is None:
                raise ValueError('successfully fetched stage required')
            try:
                self._check()
                length, expected = self._pin
                before = _file_state(self._fd)
                if before.st_size != length:
                    raise ValueError('staging length differs from transfer pin')
                data, offset = bytearray(), 0
                while offset < length:
                    chunk = os.pread(self._fd, min(_CHUNK, length - offset), offset)
                    if not chunk:
                        raise ValueError('short staging snapshot')
                    data.extend(chunk)
                    offset += len(chunk)
                after = _file_state(self._fd)
                self._check()
                if (_identity(before) != _identity(after) or len(data) != length
                        or hashlib.sha256(data).hexdigest() != expected):
                    raise ValueError('staging snapshot differs from transfer pin')
                return bytes(data)
            except BaseException:
                self._failed = True
                raise

    def close(self):
        """Release retained FDs exactly once; never delete the stage."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            fds, self._fd, self._directory = (self._fd, self._directory), None, None
            error = None
            for fd in fds:
                try:
                    os.close(fd)
                except OSError as exc:
                    error = error or exc
            if error is not None:
                raise error


def create_owned_stage(root):
    """Create one new inode; fail closed and retain any partial path on error."""
    root, directory = _safe_stage_root(root)
    name, fd, created = None, None, False
    try:
        name = 'seed-' + os.urandom(16).hex() + '.zip'
        flags = os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_RDWR | getattr(os, 'O_CLOEXEC', 0)
        fd = os.open(name, flags, 0o600, dir_fd=directory)
        created = True
        os.fchmod(fd, 0o600)
        os.fsync(fd)
        os.fsync(directory)
        lease = OwnedStage(root, directory, name, fd, _factory=_FACTORY_TOKEN)
        lease._check()
        return lease
    except BaseException as cause:
        errors = []
        for handle in (fd, directory):
            if handle is not None:
                try:
                    os.close(handle)
                except OSError as exc:
                    errors.append(str(exc))
        # This named path may have been exchanged; never remove it automatically.
        if created:
            raise StageCreationError(root / name, tuple(errors)) from cause
        raise


def fetch_declared(spec: TransferSpec, s3, stage: OwnedStage):
    """The public diagnostic fetch accepts only an exclusive staging lease."""
    if type(stage) is not OwnedStage:
        raise ValueError('exclusive owned staging lease required')
    return stage.fetch(spec, s3)
