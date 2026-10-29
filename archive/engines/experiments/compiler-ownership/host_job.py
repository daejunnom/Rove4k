"""External, single-job PGID host experiment; no submission bytes are added.

The existing validator's Owned/Budget/Reader code owns one fixed process group.
This module adds outer cancellation/registry cleanup and a host-owned TMPDIR. It
does not provide cgroup containment, a compiler-to-engine phase fence, SIGKILL
recovery, or an arbitrary concurrent service manager. Cancellation is observed
at existing Budget checkpoints for trusted small input; arbitrary blocking IO
and Popen construction have no new hard timeout.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import shutil
import signal
import threading

ROOT = Path(__file__).resolve().parents[3]
OWNER = 'engines/compact/tiny-entry-d/verify.py'
OWNER_SHA256 = '18faa69aed5cb5dd85a054ef2e6830463f3d819f5f635d74d55550a877c81eae'
_running = False


def capabilities():
    """Observe this caller's cgroup; do not create or modify host configuration."""
    root = Path('/sys/fs/cgroup')
    rows = Path('/proc/self/cgroup').read_text().splitlines()
    unified = [line.split(':', 2)[2] for line in rows if line.startswith('0::')]
    if len(unified) != 1 or not unified[0].startswith('/'):
        raise ValueError('one Linux unified cgroup path required')
    current = root / unified[0].lstrip('/')
    if root not in current.resolve().parents:
        raise ValueError('a non-root caller cgroup is required for this probe')
    files = {}
    for name in ('cgroup.type', 'cgroup.events', 'cgroup.controllers',
                 'cgroup.subtree_control', 'cgroup.kill'):
        path = current / name
        files[name] = {'exists': path.exists(), 'writable': os.access(path, os.W_OK)}
        if name != 'cgroup.kill' and path.is_file():
            files[name]['text'] = path.read_text().strip()
    uid = os.geteuid()
    user_manager = root / 'user.slice' / ('user-' + str(uid) + '.slice') / ('user@' + str(uid) + '.service')
    delegated_candidate = {'path': str(user_manager), 'exists': user_manager.is_dir(),
                          'directory_writable': os.access(user_manager, os.W_OK),
                          'procs_writable': os.access(user_manager / 'cgroup.procs', os.W_OK),
                          'subtree_control_writable': os.access(user_manager / 'cgroup.subtree_control', os.W_OK),
                          'kill_present': (user_manager / 'cgroup.kill').exists(),
                          'kill_writable': os.access(user_manager / 'cgroup.kill', os.W_OK),
                          'current_process_migration_or_job_creation_tested': False}
    return {'uid': os.geteuid(), 'kernel': platform.release(),
            'cgroup_v2': (root / 'cgroup.controllers').is_file(),
            'self_cgroup': unified[0], 'root_writable': os.access(root, os.W_OK),
            'self_directory_writable': os.access(current, os.W_OK), 'files': files,
            'own_user_manager_candidate': delegated_candidate,
            'scope': 'read-only self and own-UID candidate observations; no cgroup created or migrated'}


def owner_module():
    path = ROOT / OWNER
    data = path.read_bytes().replace(b'\r\n', b'\n')
    if b'\r' in data or hashlib.sha256(data).hexdigest() != OWNER_SHA256:
        raise ValueError('reviewed host owner input differs')
    spec = importlib.util.spec_from_file_location('rove4k_host_job_owner', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_job(program, directory, interaction, *, seconds=60):
    """Run one reviewed artifact with a bounded, small-input host interaction.

    ``interaction(owned, owner_module)`` drives the artifact and may use the
    existing readers.  On return the engine-success oracle requires zero status
    and empty stderr.  Primary failure and cleanup success remain separate.
    The host changes TMPDIR only while spawning, in this isolated main-thread,
    non-reentrant caller. INT/TERM handlers only record cancellation; they never
    raise across ownership publication or cleanup. Existing Budget checkpoints
    observe cancellation on the main thread; arbitrary blocking IO is excluded.
    Its private workspace is deleted only after physical
    group/reader settlement, including when artifact delayed cleanup was cut short.
    """
    global _running
    program, directory = Path(program).resolve(), Path(directory)
    if (platform.system() != 'Linux' or threading.current_thread() is not threading.main_thread()
            or _running or not math.isfinite(seconds) or seconds <= 0):
        raise ValueError('one finite Linux main-thread host job required')
    if (not program.is_file() or not directory.is_absolute() or directory.exists()
            or ROOT == directory.resolve() or ROOT in directory.resolve().parents
            or any((parent / '.git').exists() for parent in (directory, *directory.parents))):
        raise ValueError('existing artifact and new absolute external job directory required')
    if any(signal.getitimer(signal.ITIMER_REAL)):
        raise ValueError('an existing caller real-time alarm cannot be replaced')
    module = owner_module()
    directory.mkdir(parents=True)
    workspace = directory / 'workspace'
    workspace.mkdir(mode=0o700)
    report = {'complete': False, 'contract': 'external-fixed-PGID-job-end-v1',
              'program': {'path': str(program), 'bytes': program.stat().st_size,
                          'sha256': hashlib.sha256(program.read_bytes()).hexdigest()},
              'owner_sha256': OWNER_SHA256, 'primary': None, 'cleanup': [], 'artifact_returncodes': [],
              'workspace': str(workspace), 'workspace_removed': False,
              'compiler_phase_settlement_before_engine': 'not supplied by whole-job PGID',
              'containment': 'same process group only; no group/session migration support',
              'new_submission_bytes': 0, 'artifact_modified': False,
              'host_io_errors': []}
    pending = None
    handled = {signal.SIGINT, signal.SIGTERM}
    entry_mask = signal.pthread_sigmask(signal.SIG_BLOCK, handled)
    prior = {}

    def interrupted(signum, frame):
        nonlocal pending
        if pending is None:
            pending = signum

    def cancelled():
        if pending is not None:
            raise SystemExit(128 + pending)

    class CancelBudget(module.Budget):
        def left(self, maximum):
            cancelled()
            return super().left(maximum)

    try:
        prior = {sig: signal.signal(sig, interrupted) for sig in handled}
        _running = True
        signal.pthread_sigmask(signal.SIG_SETMASK, entry_mask)
        cancelled()
        old_tmpdir = os.environ.get('TMPDIR')
        try:
            os.environ['TMPDIR'] = str(workspace)
            owned = module.Owned(program, directory / 'io', CancelBudget(seconds))
        finally:
            if old_tmpdir is None:
                os.environ.pop('TMPDIR', None)
            else:
                os.environ['TMPDIR'] = old_tmpdir
        cancelled()
        report['interaction'] = interaction(owned, module)
        cancelled()
        report['settled'] = owned.finish()
        report['complete'] = True
    except BaseException as exc:
        report['primary'] = {'type': type(exc).__name__, 'detail': str(exc),
                             'code': exc.code if isinstance(exc, SystemExit) else None}
    finally:
        try:
            # The signal handlers never throw while these original handles and
            # readers remain owned. Registry cleanup also covers a constructor
            # that publishes its child before another synchronous error.
            for owned in list(module.OWNED):
                try:
                    report['cleanup'].append(owned.cleanup())
                except BaseException as exc:
                    report['cleanup'].append({'error': type(exc).__name__, 'detail': str(exc)})
                    report['complete'] = False
                report['artifact_returncodes'].append(owned.process.returncode)
            report['remaining_owned_handles'] = len(module.OWNED)
            settled = (not module.OWNED and all(
                row.get('owned_group_absent') and row.get('readers_joined') and not row.get('errors')
                for row in report['cleanup']))
            if settled:
                try:
                    shutil.rmtree(workspace)
                    report['workspace_removed'] = True
                except OSError as exc:
                    report['host_io_errors'].append({'operation': 'remove_workspace',
                                                    'type': type(exc).__name__, 'detail': str(exc)})
                    report['complete'] = False
            else:
                report['complete'] = False
            if pending is not None:
                report['complete'] = False
                report['cancellation_status'] = 128 + pending
                if report['primary'] is None:
                    report['primary'] = {'type': 'SystemExit', 'detail': str(128 + pending),
                                         'code': 128 + pending}
            try:
                (directory / 'host-result.json').write_text(json.dumps(report, indent=2) + '\n')
            except OSError as exc:
                report['complete'] = False
                report['host_io_errors'].append({'operation': 'write_report',
                                                'type': type(exc).__name__, 'detail': str(exc)})
                error = RuntimeError('host report write failed; primary and cleanup retained in host_report')
                error.host_report = report
                raise error from exc
        finally:
            signal.pthread_sigmask(signal.SIG_BLOCK, handled)
            _running = False
            for sig, handler in prior.items():
                signal.signal(sig, handler)
            signal.pthread_sigmask(signal.SIG_SETMASK, entry_mask)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true', required=True)
    parser.parse_args()
    print(json.dumps(capabilities(), indent=2))
