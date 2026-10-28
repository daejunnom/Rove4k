"""Materialize a pinned diagnostic seed into a private Linux directory.

The handle exposes bounded logical-name reads, resolving the sealed build
alias without changing the manifest. Paths returned to callers are observations,
not immutable executable inputs. Same-UID writers, live host/producer
authentication, cloud-runtime integration and scored GO remain unproven.
"""
from __future__ import annotations

from bisect import bisect_left
import hashlib
import io
import os
from pathlib import Path
import stat
import zipfile
from contextlib import contextmanager

try:
    from . import league_seed_layout as layout
    from .league_seed_transfer import _safe_stage_root
except ImportError:
    import league_seed_layout as layout
    from league_seed_transfer import _safe_stage_root


_DIR_FLAGS = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0)
_READ_FLAGS = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_CLOEXEC', 0)
_TOKEN = object()


class DescriptorCloseError(OSError):
    def __init__(self, errors):
        self.close_errors = tuple(errors)
        super().__init__('one or more owned descriptor closes failed')


def _close_all(*fds, primary=None):
    """Attempt every close once; never hide the active primary exception."""
    errors = []
    for fd in fds:
        if fd is None:
            continue
        try:
            os.close(fd)
        except OSError as error:
            errors.append(str(error))
    if not errors:
        return
    if primary is None:
        raise DescriptorCloseError(errors)
    previous = getattr(primary, '_fd_close_errors', ())
    primary._fd_close_errors = (*previous, *errors)
    if hasattr(primary, 'add_note'):
        primary.add_note('owned descriptor close errors: ' + repr(errors))


@contextmanager
def _closing(fds):
    try:
        yield
    except BaseException as error:
        _close_all(*fds, primary=error)
        raise
    else:
        _close_all(*fds)


def _identity(st):
    return st.st_dev, st.st_ino


def _directory(parent, name, *, create=False):
    if create:
        try:
            os.mkdir(name, 0o700, dir_fd=parent)
        except FileExistsError:
            pass
    before = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if not stat.S_ISDIR(before.st_mode):
        raise ValueError('materialization directory is not ordinary')
    fd = os.open(name, _DIR_FLAGS, dir_fd=parent)
    try:
        actual = os.fstat(fd)
        after = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if (_identity(before) != _identity(actual) or _identity(after) != _identity(actual)
                or actual.st_uid != os.geteuid() or stat.S_IMODE(actual.st_mode) != 0o700):
            raise ValueError('materialization directory identity or ownership changed')
        return fd
    except BaseException as error:
        _close_all(fd, primary=error)
        raise


def _walk(root_fd, parts, *, create=False):
    current = os.dup(root_fd)
    try:
        for part in parts:
            child = _directory(current, part, create=create)
            old, current = current, child
            _close_all(old)
        return current
    except BaseException as error:
        _close_all(current, primary=error)
        raise


def _file_stat(fd, mode, limit):
    st = os.fstat(fd)
    if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid() or st.st_nlink != 1
            or stat.S_IMODE(st.st_mode) != mode or st.st_size > limit):
        raise ValueError('materialized file identity, mode or size differs')
    return st


class MaterializationError(ValueError):
    """A partially created directory is retained and its path is untrusted."""
    def __init__(self, candidate, close_errors=()):
        self.candidate = candidate
        self.path_verified = False
        self.close_errors = close_errors
        super().__init__('materialization failed; partial candidate path is untrusted: ' + str(candidate))


class MaterializedSeed:
    """FD-owned diagnostic files; no host, producer or runtime authorization."""
    def __init__(self, token, parent, parent_fd, name, root_fd, prepared, mapping):
        if token is not _TOKEN:
            raise ValueError('materialization factory required')
        self._parent, self._parent_fd, self._name, self._root_fd = parent, parent_fd, name, root_fd
        self._parent_id, self._root_id = _identity(os.fstat(parent_fd)), _identity(os.fstat(root_fd))
        self._prepared, self._layout = prepared, mapping
        self._closed = False

    @property
    def root_path(self):
        return self._parent / self._name

    def _check_root(self):
        if self._closed:
            raise ValueError('materialized seed is closed')
        _, current = _safe_stage_root(self._parent)
        with _closing([current]):
            if _identity(os.fstat(current)) != self._parent_id:
                raise ValueError('materialization parent was replaced')
            entry = os.stat(self._name, dir_fd=current, follow_symlinks=False)
            held = os.fstat(self._root_fd)
            if (not stat.S_ISDIR(entry.st_mode) or _identity(entry) != self._root_id
                    or _identity(held) != self._root_id or held.st_uid != os.geteuid()
                    or stat.S_IMODE(held.st_mode) != 0o700):
                raise ValueError('materialization root was replaced')

    def _bind(self, spec):
        self._check_root()
        snapshot, _ = self._prepared.verify_for(spec)
        r = spec.request
        mapping = self._layout
        mapping.verify_for(snapshot, expected_archive_sha256=r.seed_archive_sha256,
            expected_archive_bytes=r.seed_archive_bytes, expected_manifest_sha256=r.seed_manifest_sha256,
            expected_origin={'repository': r.repository, 'head_sha': r.source_head,
                             'run_id': r.producer_run_id, 'run_attempt': r.producer_run_attempt})
        return mapping

    def physical_for(self, logical, spec):
        return self._bind(spec).physical_for(logical)

    def read_member(self, logical, spec):
        """Read and re-pin one exact logical file via its physical alias."""
        mapping = self._bind(spec)
        return self._read_bound_member(logical, mapping)

    def _read_bound_member(self, logical, mapping):
        self._check_root()
        # Layout validates an exact, uniquely sorted entry tuple.  A binary
        # search keeps full-tree verification subquadratic for large seeds.
        if type(logical) is not str:
            raise ValueError('logical member is not an exact sealed file')
        index = bisect_left(mapping.entries, logical, key=lambda row: row.logical)
        if index == len(mapping.entries) or mapping.entries[index].logical != logical:
            raise ValueError('logical member is not an exact sealed file')
        entry = mapping.entries[index]
        parts = entry.physical.split('/')
        parent = _walk(self._root_fd, parts[:-1])
        owned = [parent]
        with _closing(owned):
            before_path = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
            fd = os.open(parts[-1], _READ_FLAGS, dir_fd=parent)
            owned.insert(0, fd)
            before = _file_stat(fd, entry.mode, entry.bytes)
            if _identity(before_path) != _identity(before) or before.st_size != entry.bytes:
                raise ValueError('materialized file pathname changed')
            data = bytearray()
            while len(data) <= entry.bytes:
                chunk = os.read(fd, min(65536, entry.bytes + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
            after = _file_stat(fd, entry.mode, entry.bytes)
            current_path = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
            if (_identity(current_path) != _identity(before) or _identity(after) != _identity(before)
                    or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
                       (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                    or len(data) != entry.bytes or hashlib.sha256(data).hexdigest() != entry.sha256):
                raise ValueError('materialized file changed from its sealed pin')
            self._check_root()
            # Reopen the physical parent through the retained root and compare
            # its inode; a renamed/replaced subtree is not a usable path.
            check = _walk(self._root_fd, parts[:-1])
            with _closing([check]):
                if _identity(os.fstat(check)) != _identity(os.fstat(parent)):
                    raise ValueError('materialized parent path was replaced')
            return bytes(data)

    def verify_for(self, spec):
        mapping = self._bind(spec)
        # Reject unlisted files and directories before any caller treats this
        # as a complete materialization. Do not open or read unlisted entries.
        files = {entry.physical for entry in mapping.entries}
        directories = {''.join((part + '/') for part in entry.physical.split('/')[:index]).rstrip('/')
                       for entry in mapping.entries
                       for index in range(1, len(entry.physical.split('/')))}
        pending = [('', os.dup(self._root_fd))]
        seen = set()
        try:
            while pending:
                prefix, directory = pending.pop()
                with _closing([directory]):
                    for name in os.listdir(directory):
                        path = prefix + '/' + name if prefix else name
                        if path in directories:
                            pending.append((path, _directory(directory, name)))
                        elif path in files:
                            entry = os.stat(name, dir_fd=directory, follow_symlinks=False)
                            if not stat.S_ISREG(entry.st_mode):
                                raise ValueError('materialized tree has a non-regular member')
                            seen.add(path)
                        else:
                            raise ValueError('materialized tree has an unlisted entry')
        except BaseException as error:
            _close_all(*(directory for _, directory in pending), primary=error)
            raise
        else:
            _close_all(*(directory for _, directory in pending))
        if seen != files:
            raise ValueError('materialized tree is missing a sealed member')
        for entry in mapping.entries:
            self._read_bound_member(entry.logical, mapping)
        return self

    def scope(self):
        return {'materialized': True, 'logical_reader_available': True,
                'later_file_immutability_proven': False, 'same_uid_isolation_proven': False,
                'crash_durability_proven': False, 'atomic_tree_snapshot_proven': False,
                'host_authenticated': False, 'producer_authenticated': False,
                'cloud_consumer_integrated': False, 'runtime_qualified': False, 'go_authorized': False}

    def consume_cloud_diagnostic(self, spec, bank_out):
        """Run cloud's seed and bank consumers through this pinned alias tree.

        The independently supplied request, entire tree and immutable archive
        are checked before and after the consumer.  Each member read checks its
        original manifest pin through retained dirfds; archive verification is
        not repeated once per member.  The resulting bank contains physical
        paths, which are not frozen for a later executable.  This diagnostic
        confers neither host/source authority nor permission to start a game.
        On failure an output already written is untrusted and is not removed.
        """
        self.verify_for(spec)
        mapping = self._bind(spec)
        seed = mapping.manifest
        cloud = layout.cloud
        target = Path(bank_out)
        if not target.is_absolute() or '..' in target.parts:
            raise ValueError('absolute protected-safe bank output required')
        layout._parts(target.name)
        parent, parent_fd = _safe_stage_root(target.parent)
        with _closing([parent_fd]):
            try:
                os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise ValueError('bank output must be a new file')
            output_pin = {}

            def reader(logical):
                return self._read_bound_member(logical, mapping)

            def physical(logical):
                # Re-pin at lookup time, too; the returned pathname alone is not a
                # durable capability and must be revalidated before later use.
                reader(logical)
                return self.root_path / mapping.physical_for(logical)

            def owned_json(path, value):
                if Path(path) != target:
                    raise ValueError('unexpected bank output path')
                data = cloud.ledger.canonical(value) + b'\n'
                flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW |
                         getattr(os, 'O_CLOEXEC', 0))
                fd = os.open(target.name, flags, 0o600, dir_fd=parent_fd)
                with _closing([fd]):
                    written = 0
                    payload = memoryview(data)
                    while written < len(data):
                        count = os.write(fd, payload[written:])
                        if count <= 0:
                            raise OSError('short bank output write')
                        written += count
                    os.fsync(fd)
                    st = _file_stat(fd, 0o600, len(data))
                    entry = os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
                    if _identity(st) != _identity(entry) or entry.st_size != len(data):
                        raise ValueError('bank output inode changed during write')
                    output_pin.update({'identity': _identity(st), **cloud.pin(data)})

            workflow = cloud._revalidate_seed_reader(seed, reader)
            bank = cloud._rebase_bank_reader(seed, reader, physical, target, writer=owned_json)
            _, current = _safe_stage_root(parent)
            with _closing([current]):
                if _identity(os.fstat(current)) != _identity(os.fstat(parent_fd)):
                    raise ValueError('bank output directory changed during cloud consumption')
            self.verify_for(spec)
            fd = os.open(target.name, _READ_FLAGS, dir_fd=parent_fd)
            with _closing([fd]):
                before = _file_stat(fd, 0o600, output_pin['bytes'])
                data = bytearray()
                while len(data) <= output_pin['bytes']:
                    chunk = os.read(fd, min(65536, output_pin['bytes'] + 1 - len(data)))
                    if not chunk:
                        break
                    data.extend(chunk)
                after = _file_stat(fd, 0o600, output_pin['bytes'])
                entry = os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
                if (_identity(before) != output_pin['identity'] or _identity(after) != output_pin['identity']
                        or _identity(entry) != output_pin['identity'] or cloud.pin(bytes(data)) !=
                        {key: output_pin[key] for key in ('bytes', 'sha256')}):
                    raise ValueError('bank output changed before diagnostic completion')
            _, current = _safe_stage_root(parent)
            with _closing([current]):
                if _identity(os.fstat(current)) != _identity(os.fstat(parent_fd)):
                    raise ValueError('bank output directory changed before diagnostic completion')
        return {'format': 'rove4k-materialized-cloud-consumer-diagnostic-v1',
                'seed_manifest_sha256': mapping.manifest_sha256,
                'workflow_revalidated': workflow is not None,
                'bank': {'path': str(bank), 'bytes': output_pin['bytes'], 'sha256': output_pin['sha256']},
                'logical_alias_consumed': True,
                'later_file_immutability_proven': False, 'host_authenticated': False,
                'producer_authenticated': False, 'runtime_qualified': False,
                'score_qualified': False, 'go_authorized': False}

    def close(self):
        if not self._closed:
            self._closed = True
            _close_all(self._root_fd, self._parent_fd)


def materialize(prepared, spec, root):
    """Create an exclusive tree from the pipeline's independently pinned bytes.

    Never removes files, including on error. Verify the returned handle again
    before any read. Raw seed members are not returned in the receipt.
    """
    snapshot, _ = prepared.verify_for(spec)
    r = spec.request
    mapping = layout.build_layout(snapshot, expected_archive_sha256=r.seed_archive_sha256,
        expected_archive_bytes=r.seed_archive_bytes, expected_manifest_sha256=r.seed_manifest_sha256,
        expected_origin={'repository': r.repository, 'head_sha': r.source_head,
                         'run_id': r.producer_run_id, 'run_attempt': r.producer_run_attempt})
    parent, parent_fd = _safe_stage_root(root)
    name = 'tree-' + os.urandom(16).hex()
    root_fd = None
    created = False
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        created = True
        root_fd = _directory(parent_fd, name)
        with zipfile.ZipFile(io.BytesIO(snapshot)) as archive:
            for entry in mapping.entries:
                parts = entry.physical.split('/')
                directory = _walk(root_fd, parts[:-1], create=True)
                owned = [directory]
                with _closing(owned):
                    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)
                    fd = os.open(parts[-1], flags, entry.mode, dir_fd=directory)
                    owned.insert(0, fd)
                    os.fchmod(fd, entry.mode)
                    with archive.open(entry.logical, 'r') as source:
                        body = source.read(entry.bytes + 1)
                    if len(body) != entry.bytes or hashlib.sha256(body).hexdigest() != entry.sha256:
                        raise ValueError('archive member differs from sealed pin')
                    remaining = memoryview(body)
                    while remaining:
                        count = os.write(fd, remaining)
                        if count <= 0:
                            raise OSError('short materialization write')
                        remaining = remaining[count:]
                    os.fsync(fd)
                    file_st = _file_stat(fd, entry.mode, entry.bytes)
                    path_st = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
                    if _identity(file_st) != _identity(path_st) or file_st.st_size != entry.bytes:
                        raise ValueError('materialized file was exchanged')
                    os.fsync(directory)
        os.fsync(root_fd)
        os.fsync(parent_fd)
        handle = MaterializedSeed(_TOKEN, parent, parent_fd, name, root_fd, prepared, mapping)
        handle.verify_for(spec)
        return handle
    except BaseException as exc:
        _close_all(root_fd, parent_fd, primary=exc)
        close_errors = (*getattr(exc, 'close_errors', ()), *getattr(exc, '_fd_close_errors', ()))
        if created:
            if not isinstance(exc, Exception):
                if hasattr(exc, 'add_note'):
                    exc.add_note('Partial materialization path may remain and may have been exchanged: ' + str(parent / name)
                                 + '; descriptor close errors: ' + repr(close_errors))
                raise
            raise MaterializationError(parent / name, tuple(close_errors)) from None
        raise
