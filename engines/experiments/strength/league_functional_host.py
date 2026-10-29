"""Run one pinned P16/P192 functional diagnostic on an already prepared host.

The private durable state directory serializes this controller's attempts on
one host.  A surviving active marker means unknown ownership, not permission
to kill, clean, retry, start an instance, or send a scored GO.  The caller is
responsible for a delegated cgroup, candidate delivery and result collection.
This module does not authenticate the caller, source closure, clock or host.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

sys.dont_write_bytecode = True
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from .functional_probe_session import OwnedFunctionalProbe
except ImportError:
    from functional_probe_session import OwnedFunctionalProbe

_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z')
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_LIMIT = 16 << 20


def _state_fd(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or path.resolve(strict=True) != path:
        raise ValueError('state directory must be an absolute real path')
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('state directory must not traverse a symlink')
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    st = os.fstat(fd)
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != 0o700:
        os.close(fd)
        raise ValueError('state directory must be private and owned by this user')
    return fd


def _write_exclusive(directory, name, value):
    data = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    try:
        with os.fdopen(fd, 'wb') as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
    except BaseException:
        raise
    os.fsync(directory)
    return hashlib.sha256(data).hexdigest()


def _read_report(out):
    out = Path(out)
    parent = os.open(out.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open(out.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            file = os.open('functional-runtime.json', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                st = os.fstat(file)
                if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or not 0 < st.st_size <= _LIMIT:
                    raise ValueError('functional report is not a bounded private regular file')
                with os.fdopen(file, 'rb', closefd=False) as source:
                    data = source.read(_LIMIT + 1)
                if len(data) != st.st_size:
                    raise ValueError('functional report changed while reading')
                os.fsync(file)
            finally:
                os.close(file)
            # Persist both the report entry and its newly created output
            # directory before recording a receipt or releasing the marker.
            os.fsync(fd)
            os.fsync(parent)
        finally:
            os.close(fd)
    finally:
        os.close(parent)
    return json.loads(data), {'path': str(Path(out) / 'functional-runtime.json'),
                              'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def inspect(state_dir):
    """Observe marker presence only; no cleanup, process claim or retry."""
    fd = _state_fd(state_dir)
    try:
        try:
            st = os.stat('.active', dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return {'state': 'idle', 'scored_game_admitted': False}
        return {'state': 'quarantine', 'marker_device': st.st_dev, 'marker_inode': st.st_ino,
                'scored_game_admitted': False,
                'reason': 'unsettled or unknown prior controller; independent reconciliation required'}
    finally:
        os.close(fd)


def run(*, state_dir, root, campaign, candidates, candidates_sha256, profile,
        artifact, out, wall_seconds=120, _probe_factory=None):
    """Execute once and retain bounded receipts; quarantine uncertain outcomes."""
    if (profile not in ('test-p16', 'test-p192') or type(wall_seconds) is not int or
            not 90 <= wall_seconds <= 300 or not isinstance(campaign, str) or
            not _ID.fullmatch(campaign) or not isinstance(artifact, str) or not _ID.fullmatch(artifact) or
            not isinstance(candidates_sha256, str) or not _SHA.fullmatch(candidates_sha256)):
        raise ValueError('invalid functional diagnostic identity or bounds')
    root, candidates, out = map(Path, (root, candidates, out))
    if any(not p.is_absolute() or '..' in p.parts for p in (root, candidates, out)):
        raise ValueError('root, candidate and output paths must be absolute')
    fd = _state_fd(state_dir)
    attempt_fd = None
    marker_fd = None
    marker_identity = None
    attempt = uuid.uuid4().hex
    request = {'format': 'rove4k-functional-host-request-v1', 'attempt': attempt,
               'root': str(root), 'campaign': campaign, 'candidates': str(candidates),
               'candidates_sha256': candidates_sha256, 'profile': profile, 'artifact': artifact,
               'out': str(out), 'wall_seconds': wall_seconds, 'pid': os.getpid(),
               'scored_game_admitted': False}
    try:
        marker_fd = os.open('.active', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                            0o600, dir_fd=fd)
        marker_stat = os.fstat(marker_fd)
        marker_identity = (marker_stat.st_dev, marker_stat.st_ino)
        marker = (json.dumps(request, sort_keys=True, separators=(',', ':')) + '\n').encode()
        with os.fdopen(marker_fd, 'wb') as file:
            marker_fd = None
            file.write(marker)
            file.flush()
            os.fsync(file.fileno())
        os.fsync(fd)
        os.mkdir(attempt, 0o700, dir_fd=fd)
        os.fsync(fd)
        attempt_fd = os.open(attempt, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        request_sha = _write_exclusive(attempt_fd, 'request.json', request)
        owner = None
        error = None
        report = None
        cleanup = None
        try:
            factory = _probe_factory or OwnedFunctionalProbe.create
            owner = factory(root=root, campaign=campaign, candidate_path=candidates,
                            candidate_sha256=candidates_sha256, profile=profile,
                            artifact_id=artifact, out=out, wall_seconds=wall_seconds)
            records = [{'path': str(path), 'device': device, 'inode': inode}
                       for path, device, inode in owner.manager.created]
            _write_exclusive(attempt_fd, 'cgroups.json', {'records': records})
            report = owner.run()
        except BaseException as exc:
            error = exc
        if owner is not None:
            try:
                cleanup = owner.close()
            except BaseException as exc:
                cleanup = [{'type': type(exc).__name__, 'message': str(exc)}]
        # Failure before owner creation can have left partial cgroup setup.
        # Report parsing failures and interrupted calls also preserve the lock.
        # An empty cgroup alone does not establish that the original process
        # group and output readers physically settled after a failed run.
        # Keep the marker for every failure, including missing reports.
        quarantined = owner is None or type(cleanup) is not list or bool(cleanup) or error is not None
        receipt = None
        if error is None and not quarantined:
            try:
                observed, receipt = _read_report(out)
                # The producer serializes tuples as arrays in the retained
                # JSON; compare the same representation rather than Python
                # container identity.
                normalized = json.loads(json.dumps(report, allow_nan=False))
                if (observed != normalized or not isinstance(observed, dict) or
                        observed.get('format') != 'rove4k-functional-candidate-v1' or
                        observed.get('profile') != profile or observed.get('artifact_id') != artifact or
                        observed.get('candidate_set_sha256') != candidates_sha256 or
                        observed.get('complete') is not True or observed.get('scored_game_admitted') is not False):
                    raise ValueError('functional report identity or completion differs')
            except Exception as exc:
                error = exc
                quarantined = True
        elif owner is not None:
            # A failed run may still have a useful, bounded on-disk report. It
            # is evidence only when it is tied to this exact attempt's input.
            try:
                observed, receipt = _read_report(out)
                if (not isinstance(observed, dict) or
                        observed.get('format') != 'rove4k-functional-candidate-v1' or
                        observed.get('profile') != profile or observed.get('artifact_id') != artifact or
                        observed.get('candidate_set_sha256') != candidates_sha256 or
                        observed.get('scored_game_admitted') is not False):
                    raise ValueError('failed diagnostic report identity differs')
            except FileNotFoundError:
                receipt = None
            except Exception:
                receipt = None
                quarantined = True
        result = {'format': 'rove4k-functional-host-result-v1', 'attempt': attempt,
                  'request_sha256': request_sha, 'status': 'quarantine' if quarantined else
                  ('failed' if error else 'complete'), 'report': receipt,
                  'error': None if error is None else {'type': type(error).__name__, 'message': str(error)},
                  'cleanup_errors': cleanup, 'scored_game_admitted': False,
                  'limitations': ['local marker is not authenticated remote ownership',
                                  'actual host readiness and scored league are not established']}
        _write_exclusive(attempt_fd, 'result.json', result)
        if not quarantined:
            current = os.stat('.active', dir_fd=fd, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != marker_identity or not stat.S_ISREG(current.st_mode):
                raise RuntimeError('active marker identity changed; independent reconciliation required')
            os.unlink('.active', dir_fd=fd)
            os.fsync(fd)
        return result
    finally:
        if marker_fd is not None:
            os.close(marker_fd)
        if attempt_fd is not None:
            os.close(attempt_fd)
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--root', type=Path)
    parser.add_argument('--campaign')
    parser.add_argument('--candidates', type=Path)
    parser.add_argument('--candidates-sha256')
    parser.add_argument('--profile', choices=('test-p16', 'test-p192'))
    parser.add_argument('--artifact')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--wall-seconds', type=int, default=120)
    args = parser.parse_args(argv)
    if args.inspect:
        result = inspect(args.state_dir)
    else:
        if any(value is None for value in (args.root, args.campaign, args.candidates,
                                            args.candidates_sha256, args.profile, args.artifact, args.out)):
            parser.error('all diagnostic identity arguments are required')
        result = run(state_dir=args.state_dir, root=args.root, campaign=args.campaign,
                     candidates=args.candidates, candidates_sha256=args.candidates_sha256,
                     profile=args.profile, artifact=args.artifact, out=args.out, wall_seconds=args.wall_seconds)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['state' if args.inspect else 'status'] in ('idle', 'complete') else 1


if __name__ == '__main__':
    raise SystemExit(main())
