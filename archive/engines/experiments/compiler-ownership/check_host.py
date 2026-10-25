"""Check the external PGID host with a freshly built full two-worker Bash entry.

This is a development/CI checker, not part of the submitted file. Cgroup support
is only observed; no host service or cgroup is created. The physical fixtures
and normal artifact sessions use the same frozen host_job/Owned production path.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[3]
SOURCES = ('engines/experiments/compiler-ownership/host_job.py',
           'engines/experiments/compiler-ownership/check_host.py',
           'engines/compact/tiny-entry-d/verify.py', 'engines/tests/chess_oracle.py')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build, out = args.build.resolve(), args.out.resolve()
    if (sys.platform != 'linux' or not args.out.is_absolute() or out.exists()
            or ROOT == out or ROOT in out.parents
            or any((parent / '.git').exists() for parent in (out, *out.parents))):
        parser.error('Linux and a new absolute output outside Git are required')
    raw_build = (build / 'build.json').read_bytes()
    manifest = json.loads(raw_build)
    require(manifest['complete'] and manifest['family'] == 'F' and manifest['policy'] == 'full'
            and manifest['wrapper'] == 'shell'
            and manifest['resources'] == {'workers': 2, 'tt_bits': 18, 'ply': 128, 'dev_default': False},
            'a completed full F2/TT18/PLY128 shell build is required')
    expected = manifest['expected_contract']
    for relative, key in (('x', 'whole'), ('main.c', 'source'), ('native/x', 'native')):
        data = (build / relative).read_bytes()
        require(len(data) == expected[key + '_bytes'] and sha(data) == expected[key + '_sha256'],
                'actual input differs from selected build contract: ' + relative)
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (180,) * 2)
    out.mkdir(parents=True)
    pins = {}
    for relative in SOURCES:
        raw = (ROOT / relative).read_bytes().replace(b'\r\n', b'\n')
        require(b'\r' not in raw, 'lone CR in source')
        target = out / 'inputs' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        pins[relative] = {'bytes': len(raw), 'sha256': sha(raw)}
    host = load('current_host_job', out / 'inputs' / SOURCES[0])
    oracle = load('current_host_oracle', out / 'inputs' / SOURCES[3])
    program = out / 'full-shell'
    program.write_bytes((build / 'x').read_bytes())
    program.chmod(0o755)
    report = {'complete': False, 'scope': 'external PGID job-end ownership, not compiler-phase containment',
              'source_pins': pins, 'build_json_sha256': sha(raw_build),
              'expected_contract': expected, 'cases': [], 'actual_affinity': sorted(os.sched_getaffinity(0)),
              'new_submission_bytes': 0, 'source_mutations': 0, 'cgroup_integration': 'not run'}
    try:
        report['capabilities'] = host.capabilities()
    except ValueError as exc:
        report['capabilities'] = {'probe_unavailable': str(exc), 'scope': 'no cgroup integration inferred'}

    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')

    def wait_for(predicate, owned):
        end = time.monotonic() + owned.budget.left(10)
        while not predicate():
            owned.budget.left(10)
            require(time.monotonic() < end, 'fixture readiness deadline')
            time.sleep(.005)

    def trace(owned, module, observations):
        original = module.os.killpg

        def killpg(pid, sig):
            if pid == owned.process.pid:
                observations.append({'signal': sig, 'leader_reaped': owned.reaped,
                                     'waitable': None if owned.reaped else owned.exited(),
                                     'members': owned.group_others()})
                require(not sig or not owned.reaped, 'nonzero group signal after original leader reap')
            return original(pid, sig)

        module.os.killpg = killpg
        return lambda: setattr(module.os, 'killpg', original)

    def accept(label, result, *, complete=False, observations=None):
        require(result['complete'] == complete and result['remaining_owned_handles'] == 0,
                'host outcome or remaining ownership differs: ' + label)
        require(all(row.get('owned_group_absent') and row.get('readers_joined') and not row.get('errors')
                    for row in result['cleanup']), 'physical cleanup differs: ' + label)
        report['cases'].append({'label': label, 'host_result': result, 'signal_observations': observations or []})
        save()

    try:
        control = out / 'leader-control'
        control.mkdir()
        ready, leader_exit = control / 'child', control / 'leader'
        child = ('import os,time\nfrom pathlib import Path\nPath(' + repr(str(ready))
                 + ').write_text(str(os.getpid()))\ntime.sleep(40)\n')
        leader = out / 'leader-first'
        leader.write_text('#!/usr/bin/python3\nimport os,subprocess,sys,time\nfrom pathlib import Path\n'
                          'p=subprocess.Popen([sys.executable,"-c",' + repr(child) + '])\nwhile not Path('
                          + repr(str(ready)) + ').exists():time.sleep(.005)\nPath(' + repr(str(leader_exit))
                          + ').write_text(str(os.getpid()))\n')
        leader.chmod(0o755)
        observations, restores = [], []

        def orphan_action(owned, module):
            restores.append(trace(owned, module, observations))
            wait_for(lambda: leader_exit.exists() and owned.exited(), owned)
            require(any(row['state'] != 'Z' for row in owned.group_others()), 'live orphan not observed')
            return {'live_descendants': owned.group_others()}

        try:
            result = host.run_job(leader, out / 'leader-job', orphan_action, seconds=30)
        finally:
            for restore in restores:
                restore()
        require(result['primary']['type'] == 'AssertionError' and result['artifact_returncodes'] == [0]
                and result['workspace_removed'], 'leader-first primary or cleanup was hidden')
        require(any(row['signal'] and row['waitable'] for row in observations), 'retained leader signal not observed')
        accept('leader-first-live-child', result, observations=observations)

        fake = out / 'fake-bin'
        fake.mkdir()
        control = out / 'compiler-control'
        control.mkdir()
        ready, compiler_ready = control / 'child', control / 'compiler'
        child = ('import os,signal,time\nfrom pathlib import Path\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\nPath('
                 + repr(str(ready)) + ').write_text(str(os.getpid()))\ntime.sleep(40)\n')
        compiler = fake / 'cc'
        compiler.write_text('#!/usr/bin/python3\nimport json,os,signal,subprocess,sys,time\nfrom pathlib import Path\n'
                            'sys.stdin.buffer.read()\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
                            'p=subprocess.Popen([sys.executable,"-c",' + repr(child) + '])\nwhile not Path('
                            + repr(str(ready)) + ').exists():time.sleep(.005)\nPath(' + repr(str(compiler_ready))
                            + ').write_text(json.dumps({"pid":os.getpid(),"pgid":os.getpgrp(),"child":p.pid}))\ntime.sleep(40)\n')
        compiler.chmod(0o755)
        observations, restores, senders = [], [], []
        old_path = os.environ.get('PATH')
        os.environ['PATH'] = str(fake) + ':' + os.defpath

        def cancel_action(owned, module):
            restores.append(trace(owned, module, observations))
            wait_for(compiler_ready.exists, owned)
            require(json.loads(compiler_ready.read_bytes())['pgid'] == owned.process.pid, 'compiler escaped job PGID')
            require(list((owned.directory.parent / 'workspace').iterdir()), 'compiler private workspace not observed')

            def storm():
                for _ in range(20):
                    os.kill(os.getpid(), signal.SIGTERM)
                    time.sleep(.005)

            sender = threading.Thread(target=storm, daemon=False)
            senders.append(sender)
            sender.start()
            owned.stdout.until(lambda data: False, owned.budget, seconds=10)

        try:
            result = host.run_job(program, out / 'compiler-job', cancel_action, seconds=30)
        finally:
            if old_path is None:
                os.environ.pop('PATH', None)
            else:
                os.environ['PATH'] = old_path
            for restore in restores:
                restore()
            for sender in senders:
                sender.join(timeout=3)
                require(not sender.is_alive(), 'test signal sender remained')
        require(result['primary']['code'] == 143 and result['workspace_removed']
                and any(row['signal'] == 9 for row in observations), 'repeated cancellation contract differs')
        accept('repeated-parent-TERM-during-fake-compiler', result, observations=observations)

        original_signal = host.signal.signal
        injected = []

        def signal_port(sig, handler):
            previous = original_signal(sig, handler)
            if sig == signal.SIGTERM and callable(handler) and not injected:
                injected.append(True)
                os.kill(os.getpid(), signal.SIGTERM)
            return previous

        host.signal.signal = signal_port
        try:
            result = host.run_job(program, out / 'setup-cancel-job', lambda *_: None, seconds=30)
        finally:
            host.signal.signal = original_signal
        require(injected and result['primary']['code'] == 143 and not result['artifact_returncodes']
                and result['workspace_removed'], 'pending setup cancellation launched or leaked a job')
        accept('pending-TERM-before-spawn', result)

        sleeper = out / 'sleeper'
        sleeper.write_text('#!/usr/bin/python3\nimport time\ntime.sleep(40)\n')
        sleeper.chmod(0o755)

        def primary_error(owned, module):
            raise ValueError('host fixture primary')

        original_remove = host.shutil.rmtree
        removal_workspace = out / 'remove-error-job/workspace'

        def remove_port(path, *args, **kwargs):
            if Path(path) == removal_workspace:
                raise OSError('injected workspace removal failure')
            return original_remove(path, *args, **kwargs)

        host.shutil.rmtree = remove_port
        try:
            result = host.run_job(sleeper, out / 'remove-error-job', primary_error, seconds=30)
        finally:
            host.shutil.rmtree = original_remove
        require(result['primary']['type'] == 'ValueError' and not result['workspace_removed']
                and result['host_io_errors'][0]['operation'] == 'remove_workspace', 'cleanup IO masked primary')
        accept('workspace-removal-error-preserves-primary', result)
        original_remove(removal_workspace)

        original_write = Path.write_text
        report_target = out / 'report-error-job/host-result.json'

        def write_port(path, *args, **kwargs):
            if path == report_target:
                raise OSError('injected report write failure')
            return original_write(path, *args, **kwargs)

        Path.write_text = write_port
        try:
            try:
                host.run_job(sleeper, out / 'report-error-job', primary_error, seconds=30)
            except RuntimeError as exc:
                result = exc.host_report
            else:
                raise AssertionError('report write error did not propagate')
        finally:
            Path.write_text = original_write
        require(result['primary']['type'] == 'ValueError' and result['workspace_removed']
                and result['host_io_errors'][0]['operation'] == 'write_report', 'report IO lost primary context')
        accept('report-write-error-retains-attached-primary', result)

        boards = [oracle.Board.from_fen(), oracle.Board.from_fen().play('e2e4'),
                  oracle.Board.from_fen(), oracle.Board.from_fen()]
        for eof in (False, True):
            holder = {}

            def interaction(owned, module):
                holder['owned'] = owned
                owned.send(b'uci\nisready\n')
                owned.stdout.until(lambda data: b'uciok' in data.splitlines() and b'readyok' in data.splitlines(),
                                   owned.budget, seconds=60)
                require(sha(Path(f'/proc/{owned.process.pid}/exe').read_bytes()) == expected['native_sha256'],
                        'actual hosted native differs')
                initial_path = os.readlink(f'/proc/{owned.process.pid}/exe')
                require(not initial_path.endswith(' (deleted)'), 'initial named executable phase was missed')
                tids = sorted(int(path.name) for path in Path(f'/proc/{owned.process.pid}/task').iterdir())
                require(len(tids) == 3, 'fixed host artifact TIDs differ')
                owned.send(b'position startpos\ngo wtime 0 btime 0\n')
                owned.wait_best(1)
                owned.send(b'position startpos moves e2e4\ngo wtime 0 btime 0\n')
                owned.wait_best(2)
                owned.send(b'position startpos\ngo\n')
                owned.wait_best(3)
                end = time.monotonic() + owned.budget.left(60)
                while Path(initial_path).parent.exists() or owned.group_others():
                    require(time.monotonic() < end, 'artifact startup cleanup deadline')
                    time.sleep(owned.budget.left(.01))
                require(tids == sorted(int(path.name) for path in Path(f'/proc/{owned.process.pid}/task').iterdir()),
                        'host artifact replaced persistent TIDs')
                before = module.tasks(owned.process.pid)
                owned.send(b'position startpos\ngo wtime 60000 btime 60000\n')
                activity = module.physical_active(owned, tids, before)
                if not eof:
                    owned.send(b'quit\n')
                owned.close_input()
                return {'initial_named_path': initial_path, 'artifact_cleanup_before_shutdown': True,
                        'TIDs': tids, 'native_sha256': expected['native_sha256'], 'activity': activity}

            result = host.run_job(program, out / ('full-EOF' if eof else 'full-quit'), interaction, seconds=80)
            moves = [line.split()[1].decode() for line in holder['owned'].stdout.bytes().splitlines()
                     if line.startswith(b'bestmove ')]
            require(len(moves) == 4 and all(move in {str(item) for item in board.legal_moves()}
                                           for move, board in zip(moves, boards)), 'hosted move is not legal')
            result['legal_moves'] = moves
            require(result['workspace_removed'], 'normal host workspace remains')
            accept('full-shell-EOF' if eof else 'full-shell-quit', result, complete=True)

        require(all(sha((ROOT / path).read_bytes().replace(b'\r\n', b'\n')) == pin['sha256']
                    for path, pin in pins.items()), 'source changed after freeze')
        report.update(complete=True, counts={'host_API_cases': 7, 'physical_jobs': 6,
                      'actual_full_shell_sessions': 2, 'actual_legal_GO': 8,
                      'real_compiler_invocations': 2, 'fake_compiler_invocations': 1,
                      'source_mutations': 0}, source_unchanged=True, owned_remaining=0)
    except BaseException as exc:
        report['failure'] = {'type': type(exc).__name__, 'detail': str(exc)}
        raise
    finally:
        save()
    print(json.dumps({'complete': True, 'cases': 7, 'sessions': 2, 'legal_GO': 8,
                      'results': str(out / 'results.json')}), flush=True)


if __name__ == '__main__':
    main()
