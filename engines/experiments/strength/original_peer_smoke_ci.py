"""Build pinned upstream source and run a small, non-scoring UCI smoke.

All source, binaries and protocol output stay outside the checkout; the only
durable output is a bounded, allowlisted JSON receipt. This does not qualify a
large-resource profile, NUMA placement, performance or league admission.
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

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import original_peer_build as original
import original_peer_build_ci as intake
import original_peer_smoke_driver as driver
import peer_exact_runner as runner
import peers


def ci_identity():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        return None
    repo = os.environ['GITHUB_REPOSITORY']
    event = os.environ['GITHUB_EVENT_NAME']
    checkout = os.environ['CHECKOUT_SHA']
    event_sha = os.environ['GITHUB_SHA']
    head = os.environ.get('PR_HEAD_SHA') or None
    workflow = os.environ['GITHUB_WORKFLOW_REF']
    run = int(os.environ['GITHUB_RUN_ID'])
    attempt = int(os.environ['GITHUB_RUN_ATTEMPT'])
    if (re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) is None or
            re.fullmatch(r'[0-9a-f]{40}', checkout) is None or checkout != event_sha or
            event not in ('pull_request', 'workflow_dispatch') or
            (event == 'pull_request' and (head is None or re.fullmatch(r'[0-9a-f]{40}', head) is None)) or
            (event == 'workflow_dispatch' and head is not None) or
            not workflow.startswith(repo + '/.github/workflows/original-peer-uci-smoke.yml@') or
            len(workflow) > 512 or any(ord(c) < 33 or ord(c) > 126 for c in workflow) or
            not 0 < run < 1 << 63 or not 0 < attempt < 1 << 31):
        raise ValueError('CI identity differs')
    return {'repository': repo, 'checkout_sha': checkout, 'event_sha': event_sha,
            'pull_request_head_sha': head, 'event_name': event, 'workflow_ref': workflow,
            'run_id': run, 'run_attempt': attempt}


def run_smoke(peer, out, native_summary, cpu, *, timeout=45):
    """Execute a fresh, independently checked copy under the group supervisor."""
    out = original._outside_checkout(out)
    directory = runner._open_directory(out)
    source_fd = copy_fd = None
    try:
        source_fd = os.open('peer-native-1', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        info = os.fstat(source_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('native input is not an owned regular file')
        data = original._read_owned_fd(source_fd, original.MAX_NATIVE_BYTES)
        digest = hashlib.sha256(data).hexdigest()
        if len(data) != native_summary['bytes'] or digest != native_summary['sha256']:
            raise ValueError('native input differs from build')
        copy_fd = os.open('smoke-native', os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                          0o700, dir_fd=directory)
        with os.fdopen(os.dup(copy_fd), 'wb') as file:
            file.write(data)
            file.flush()
        os.fchmod(copy_fd, 0o700)
        if original._read_owned_fd(copy_fd, original.MAX_NATIVE_BYTES) != data:
            raise ValueError('smoke copy differs')
        copy_stat = os.fstat(copy_fd)
        os.close(copy_fd)
        copy_fd = os.open('smoke-native', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        reopened = os.fstat(copy_fd)
        if (reopened.st_dev, reopened.st_ino, reopened.st_nlink) != (copy_stat.st_dev, copy_stat.st_ino, 1):
            raise ValueError('smoke copy identity changed')
        observed, errors, record = runner.run(
            [sys.executable, '-I', '-B', str(Path(driver.__file__).resolve()), peer, '{fd:native}'],
            out, sandbox_home=out / 'home', timeout=timeout, cpu=cpu,
            fd_anchors={'work': (directory, out), 'native': (copy_fd, out / 'smoke-native')},
            cwd_anchor='work')
        if (errors or record['leader_reaped'] is not True or record['group_absent'] is not True or
                record['forced_cleanup'] is not False or
                record['original_group_empty_observed_before_reap'] is not True):
            raise ValueError('smoke supervision did not settle normally')
        result = json.loads(observed)
        if (type(result) is not dict or result.get('hash_mib_requested') != 1 or
                result.get('threads_requested') != 1 or result.get('uciok') is not True or
                result.get('readyok') is not True or result.get('quit_exit_code') != 0 or
                result.get('legal_startpos_bestmove') not in driver.MOVES):
            raise ValueError('smoke response differs')
        return {key: result[key] for key in ('hash_mib_requested', 'threads_requested',
            'uciok', 'readyok', 'legal_startpos_bestmove', 'quit_exit_code', 'ponder',
            'stdout_bytes', 'stderr_bytes', 'stdout_sha256', 'stderr_sha256')}
    finally:
        for fd in (source_fd, copy_fd, directory):
            if fd is not None:
                os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--peer', choices=('ice4', 'c4ke'), required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    cpu = min(os.sched_getaffinity(0))
    source = intake.verify_intake(args.peer, args.source)
    built = original.build(args.peer, 'test-p16', source, args.out, cpu=cpu, timeout=600)
    record = built['record']
    attempts = record['attempts']
    if (record['revision'] != peers.peer_spec(args.peer).revision or
            record['same_host_native_reproduced'] is not True or len(attempts) != 2 or
            (attempts[0]['bytes'], attempts[0]['sha256']) != (attempts[1]['bytes'], attempts[1]['sha256'])):
        raise ValueError('original build identity differs')
    result = run_smoke(args.peer, args.out, attempts[0], cpu)
    receipt = {'format': 'rove4k-original-peer-small-uci-smoke-v1',
        'ci': ci_identity(),
        'peer': args.peer, 'revision': record['revision'],
        'source_closure_sha256': record['source_closure_sha256'],
        'native_bytes': attempts[0]['bytes'], 'native_sha256': attempts[0]['sha256'],
        'same_host_native_reproduced': True, 'smoke': result,
        'leader_reaped': True, 'original_group_empty_observed_before_reap': True,
        'physical_group_settlement_proven': False, 'ci_origin_authenticated': False,
        'tcec_size_limit_applied': False, 'tt_allocation_observed': False,
        'worker_placement_observed': False, 'numa_observed': False,
        'performance_data': False, 'scored_game_admitted': False,
        'league_qualified': False, 'large_profile_validated': False,
        'scope': 'small-resource start-position UCI smoke only; readyok does not prove allocation'}
    path = original._outside_checkout(args.receipt)
    parent = runner._open_directory(path.parent)
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as file:
            file.write(peers.canonical(receipt) + b'\n')
    finally:
        os.close(parent)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:
        print('Original peer small UCI smoke failed.', file=sys.stderr)
        raise SystemExit(1)
