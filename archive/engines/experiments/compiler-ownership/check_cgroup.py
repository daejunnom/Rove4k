#!/usr/bin/env python3
"""Bounded developer-only cgroup-v2 job experiment using an existing user manager.

No cgroup or service is assumed by a submission.  The current caller may be in
a read-only cgroup while the user's manager owns a writable delegation.  A
transient user service forks the experiment inside that delegation; it never
migrates unrelated tasks or modifies a pre-existing cgroup.  Its compiler fence
checks live-group emptiness, original-child wait/reap and reader EOF separately.
An intentional main-process exit then tests manager cleanup of a different-PGID
descendant.  This is neither a product-size saving nor tournament admission.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid


def require(value, message):
    if not value:
        raise RuntimeError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def cgroup_path():
    rows = Path('/proc/self/cgroup').read_text().splitlines()
    row = next(x for x in rows if x.startswith('0::'))
    relative = row[3:]
    path = (Path('/sys/fs/cgroup') / relative.lstrip('/')).resolve()
    require(path.is_relative_to(Path('/sys/fs/cgroup')), 'cgroup path escapes mount')
    return relative, path


def capability():
    relative, current = cgroup_path()
    delegated = Path('/sys/fs/cgroup/user.slice') / ('user-%d.slice' % os.geteuid()) / ('user@%d.service' % os.geteuid())
    def row(path):
        return {'path': str(path), 'exists': path.is_dir(), 'directory_writable': os.access(path, os.W_OK),
                'procs_writable': os.access(path/'cgroup.procs', os.W_OK),
                'subtree_writable': os.access(path/'cgroup.subtree_control', os.W_OK),
                'kill_present': (path/'cgroup.kill').exists()}
    return {'uid': os.geteuid(), 'current_relative': relative, 'current': row(current),
            'user_manager_delegation': row(delegated),
            'bus_socket_exists': Path('/run/user/%d/bus' % os.geteuid()).exists()}


def events(path):
    return {k: int(v) for k, v in (line.split() for line in (path/'cgroup.events').read_text().splitlines())}


def stat(pid):
    try:
        text = Path('/proc/%d/stat' % pid).read_text()
    except FileNotFoundError:
        return None
    fields = text.rsplit(')', 1)[1].split()
    return {'pid': pid, 'state': fields[0], 'ppid': int(fields[1]), 'pgid': int(fields[2]),
            'sid': int(fields[3]), 'starttime': int(fields[19])}


class Reader:
    def __init__(self, stream):
        self.stream, self.data, self.error = stream, bytearray(), None
        def run():
            try:
                while True:
                    data = stream.read(4096)
                    if not data:
                        break
                    require(len(self.data) + len(data) <= 65536, 'fixture reader output cap')
                    self.data.extend(data)
            except BaseException as error:
                self.error = repr(error)
        self.thread = threading.Thread(target=run)
        self.thread.start()

    def finish(self):
        self.thread.join(5)
        require(not self.thread.is_alive() and self.error is None, 'fixture reader did not reach EOF')
        self.stream.close()
        return {'EOF': True, 'joined': True, 'bytes': len(self.data), 'sha256': hashlib.sha256(self.data).hexdigest()}


def await_file(path, seconds=5):
    end = time.monotonic() + seconds
    while not path.exists():
        require(time.monotonic() < end, 'fixture ready timeout')
        time.sleep(.01)


def await_empty(path, seconds=5):
    end = time.monotonic() + seconds
    while True:
        value = events(path)
        if value['populated'] == 0:
            return value
        require(time.monotonic() < end, 'owned cgroup did not become unpopulated')
        time.sleep(.01)


GRANDCHILD = '''import json,os,sys,time
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({'pid':os.getpid(),'pgid':os.getpgrp(),'cgroup':Path('/proc/self/cgroup').read_text()}))
print('grandchild ready',flush=True)
while True:time.sleep(30)
'''
LEADER = '''import json,os,subprocess,sys,time
from pathlib import Path
gate=int(sys.argv[1]);approved=os.read(gate,1);os.close(gate)
if approved!=b'x':raise SystemExit(98)
grandchild=subprocess.Popen([sys.executable,'-B','-c',sys.argv[2],sys.argv[3]],start_new_session=True)
end=time.monotonic()+5
while not Path(sys.argv[3]).exists():
 if time.monotonic()>end:raise SystemExit(99)
 time.sleep(.005)
print('leader ready',flush=True)
if sys.argv[4]=='early':raise SystemExit(7)
while True:time.sleep(30)
'''


def inside(out, unit):
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30,)*2)
    resource.setrlimit(resource.RLIMIT_CPU, (60,)*2)
    relative, root = cgroup_path()
    require(root.name == unit and ('user@%d.service' % os.geteuid()) in root.parts,
            'transient service is outside its verified user delegation')
    require(root.is_dir() and os.access(root, os.W_OK), 'own unit cgroup is not delegated')
    result = {'complete': False, 'unit': unit, 'unit_cgroup': str(root), 'unit_relative': relative,
              'affinity': sorted(os.sched_getaffinity(0)), 'compiler_fences': [],
              'contract': 'developer host only; cgroup live emptiness is distinct from reaping and EOF'}
    save(out/'inside.json', result)
    group = root/'compiler'
    group.mkdir()
    try:
        for case in ('early', 'active'):
            gate_r, gate_w = os.pipe()
            ready = out/('compiler-grandchild-%s.json' % case)
            work = out/('compiler-work-%s' % case)
            work.mkdir(mode=0o700)
            (work/'held').write_text('owned compiler input')
            child = subprocess.Popen([sys.executable, '-B', '-c', LEADER, str(gate_r), GRANDCHILD,
                                      str(ready), case], pass_fds=(gate_r,), start_new_session=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            os.close(gate_r)
            readers = [Reader(child.stdout), Reader(child.stderr)]
            row = {'case': case, 'original_pid': child.pid, 'reaped': False}
            result['compiler_fences'].append(row)
            save(out/'inside.json', result)
            try:
                (group/'cgroup.procs').write_text(str(child.pid))
                os.write(gate_w, b'x')
                os.close(gate_w)
                gate_w = None
                await_file(ready)
                grandchild = json.loads(ready.read_text())
                require(grandchild['pgid'] != child.pid, 'fixture did not create a different process group')
                require(grandchild['cgroup'].strip() == '0::' + relative + '/compiler', 'grandchild escaped owned cgroup')
                if case == 'early':
                    end = time.monotonic() + 5
                    while os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
                        require(time.monotonic() < end, 'early leader not waitable')
                        time.sleep(.005)
                row.update(grandchild=grandchild, before=events(group),
                           leader_waitable_before_kill=os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None,
                           workspace_present_before_fence=work.exists())
                require(row['before']['populated'] == 1, 'live compiler group absent before kill')
                (group/'cgroup.kill').write_text('1')
                row['after_kill_events'] = await_empty(group)
                row['original_waitid'] = list(os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOWAIT))
                row['returncode'] = child.wait(timeout=5)
                row['reaped'] = True
                require(row['returncode'] == (7 if case == 'early' else -signal.SIGKILL), 'compiler status lost')
                row['readers'] = [r.finish() for r in readers]
                row['grandchild_after_live_fence'] = stat(grandchild['pid'])
                require(work.resolve().parent == out.resolve(), 'workspace deletion escapes owned output')
                shutil.rmtree(work)
                row['workspace_deleted_after_live_fence_reap_and_EOF'] = not work.exists()
                row['compile_phase_fence_before_engine'] = True
                save(out/'inside.json', result)
            finally:
                if gate_w is not None:
                    os.close(gate_w)
                if not row['reaped']:
                    (group/'cgroup.kill').write_text('1')
                    await_empty(group)
                    child.wait(timeout=5)
                    row['failure_path_original_reaped'] = True
                    row['failure_path_readers'] = [r.finish() for r in readers]
                    save(out/'inside.json', result)
        group.rmdir()
        # Deliberately leave a different-PGID descendant for unit-stop cleanup.
        ready = out/'job-end-descendant.json'
        pending = subprocess.Popen([sys.executable, '-B', '-c', GRANDCHILD, str(ready)], start_new_session=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await_file(ready)
        result['job_end_descendant'] = {**json.loads(ready.read_text()), 'before_exit_stat': stat(pending.pid)}
        result['inside_phase_complete'] = True
        result['intentional_main_exit'] = 17
        save(out/'inside.json', result)
        os._exit(17)
    finally:
        if group.exists():
            (group/'cgroup.kill').write_text('1')
            await_empty(group)
            group.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--inside', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--unit', help=argparse.SUPPRESS)
    args = parser.parse_args()
    require(sys.platform == 'linux', 'Linux cgroup-v2 experiment required')
    if args.inside:
        require(args.unit is not None and re.fullmatch(r'rove4k-ownership-[0-9a-f]{12}\.service', args.unit), 'invalid owned unit')
        inside(args.out.resolve(), args.unit)
        return
    require(args.out.is_absolute() and not args.out.exists(), 'new absolute external output required')
    out = args.out.resolve()
    require(not any((p/'.git').exists() for p in (out, *out.parents)), 'output must be outside Git')
    out.mkdir(parents=True, mode=0o700)
    env = dict(os.environ, XDG_RUNTIME_DIR='/run/user/%d' % os.geteuid(),
               DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/%d/bus' % os.geteuid())
    result = {'complete': False, 'capability': capability(), 'created_unit': None,
              'scope': 'bounded local user-manager host experiment; no submission dependency or size gain'}
    save(out/'results.json', result)
    manager = subprocess.run(['systemctl', '--user', 'is-system-running'], env=env,
                             capture_output=True, text=True, timeout=5)
    result['manager'] = {'returncode': manager.returncode, 'state': manager.stdout.strip(), 'error': manager.stderr}
    if manager.returncode not in (0, 1) or manager.stdout.strip() not in ('running', 'degraded'):
        result.update(probe_complete=True, supported=False, checks_run=False, reason='existing user manager unavailable')
        save(out/'results.json', result)
        print(json.dumps(result))
        return
    unit = 'rove4k-ownership-' + uuid.uuid4().hex[:12] + '.service'
    require(subprocess.run(['systemctl', '--user', 'show', unit, '-p', 'LoadState', '--value'], env=env,
                           capture_output=True, text=True, timeout=5).stdout.strip() == 'not-found', 'unit already exists')
    source = Path(__file__).read_bytes().replace(b'\r\n', b'\n')
    frozen = out/'check_cgroup.py'
    frozen.write_bytes(source)
    cpus = sorted(os.sched_getaffinity(0))[:2]
    require(0 < len(cpus) <= 2, 'bounded affinity unavailable')
    result.update(created_unit=unit, source_sha256=hashlib.sha256(source).hexdigest(),
                  intended_properties={'RuntimeMaxSec': 60, 'TimeoutStopSec': 5, 'KillMode': 'control-group',
                                       'Delegate': True, 'MemoryMax': 2 << 30, 'CPUAffinity': cpus}, checks_run=True)
    save(out/'results.json', result)
    command = ['systemd-run', '--user', '--collect', '--wait', '--pipe', '--unit=' + unit,
               '--property=RuntimeMaxSec=60', '--property=TimeoutStopSec=5', '--property=KillMode=control-group',
               '--property=Delegate=yes', '--property=MemoryMax=2G',
               '--property=CPUAffinity=' + ' '.join(map(str, cpus)), '--', sys.executable, '-B', str(frozen),
               '--inside', '--out', str(out), '--unit', unit]
    result['command'] = command
    save(out/'results.json', result)
    process = None
    primary = None
    validated = False
    cancellation = []
    def cancelled(signum, frame):
        if not cancellation:
            cancellation.append(signum)
    saved_handlers = {s: signal.signal(s, cancelled) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        with (out/'unit.stdout').open('wb') as stdout, (out/'unit.stderr').open('wb') as stderr:
            if cancellation:
                raise SystemExit(128 + cancellation[0])
            process = subprocess.Popen(command, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            result['original_cli_pid'] = process.pid
            save(out/'results.json', result)
            deadline = time.monotonic() + 75
            while os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
                if cancellation:
                    raise SystemExit(128 + cancellation[0])
                require(time.monotonic() < deadline, 'transient unit completion deadline')
                time.sleep(.02)
            result['cli_returncode'] = process.wait(timeout=3)
        require(result['cli_returncode'] == 17, 'fixture unit did not preserve intentional exit17')
        observed = json.loads((out/'inside.json').read_text())
        require(observed.get('inside_phase_complete') and len(observed['compiler_fences']) == 2,
                'compiler-fence experiment incomplete')
        query = subprocess.run(['systemctl', '--user', 'show', unit, '-p', 'LoadState', '-p', 'ActiveState', '-p', 'SubState'],
                               env=env, capture_output=True, text=True, timeout=5)
        result['unit_after'] = query.stdout
        require('ActiveState=inactive' in query.stdout or 'LoadState=not-found' in query.stdout, 'owned unit still active')
        group = Path(observed['unit_cgroup'])
        result['unit_cgroup_removed'] = not group.exists()
        result['unit_final_events'] = events(group) if group.exists() else None
        require(result['unit_cgroup_removed'] or result['unit_final_events']['populated'] == 0, 'unit has live descendants')
        desc = observed['job_end_descendant']
        after = stat(desc['pid'])
        same = after is not None and after['starttime'] == desc['before_exit_stat']['starttime']
        require(not same or after['state'] == 'Z', 'same-identity job descendant is still live')
        result['job_end_descendant_after'] = after
        result.update(supported=True, inside=observed,
                      limitation='populated0 means no live descendants; nonchild zombies are not attributed as reaped by caller')
        validated = True
    except BaseException as error:
        result['error'] = repr(error)
        primary = error, error.__traceback__
    finally:
        cleanup_errors = []
        try:
            stop = subprocess.run(['systemctl', '--user', 'stop', unit], env=env,
                                  capture_output=True, text=True, timeout=10)
            result['owned_unit_stop'] = {'returncode': stop.returncode, 'stdout': stop.stdout, 'stderr': stop.stderr}
        except BaseException as error:
            cleanup_errors.append({'operation': 'owned-unit-stop', 'error': repr(error)})
        if process is not None and process.returncode is None:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # A stop sent before StartTransientUnit may have raced creation.
                # Retry only this unique owned unit, then settle its CLI handle.
                try:
                    retry = subprocess.run(['systemctl', '--user', 'stop', unit], env=env,
                                           capture_output=True, text=True, timeout=10)
                    result['owned_unit_stop_after_cli_wait'] = {'returncode': retry.returncode,
                                                               'stdout': retry.stdout, 'stderr': retry.stderr}
                    process.wait(timeout=5)
                except BaseException as error:
                    cleanup_errors.append({'operation': 'owned-unit-stop-after-cli-wait', 'error': repr(error)})
                    try:
                        process.kill()
                        process.wait(timeout=3)
                        result['CLI_force_killed_after_unit_stop'] = True
                    except BaseException as error:
                        cleanup_errors.append({'operation': 'original-cli-reap', 'error': repr(error)})
            except BaseException as error:
                cleanup_errors.append({'operation': 'original-cli-wait', 'error': repr(error)})
        result['original_cli_reaped'] = process is not None and process.returncode is not None
        try:
            query = subprocess.run(['systemctl', '--user', 'show', unit, '-p', 'LoadState', '-p', 'ActiveState', '-p', 'SubState'],
                                   env=env, capture_output=True, text=True, timeout=5)
            result['final_unit_query'] = {'returncode': query.returncode, 'stdout': query.stdout, 'stderr': query.stderr}
            result['owned_unit_closed_confirmed'] = 'ActiveState=inactive' in query.stdout or 'LoadState=not-found' in query.stdout
            if not result['owned_unit_closed_confirmed']:
                cleanup_errors.append({'operation': 'owned-unit-closure', 'error': 'inactive/not-found not confirmed'})
        except BaseException as error:
            cleanup_errors.append({'operation': 'owned-unit-query', 'error': repr(error)})
        result.update(cleanup_errors=cleanup_errors, cancel_signal=cancellation[0] if cancellation else None,
                      complete=validated and primary is None and not cleanup_errors and not cancellation)
        try:
            save(out/'results.json', result)
        except BaseException as error:
            if primary is None:
                primary = error, error.__traceback__
            else:
                primary[0].add_note('final result write also failed: ' + repr(error))
        for signum, handler in saved_handlers.items():
            signal.signal(signum, handler)
    if primary is not None:
        raise primary[0].with_traceback(primary[1])
    if cancellation:
        raise SystemExit(128 + cancellation[0])
    require(not cleanup_errors, 'owned unit cleanup not confirmed: ' + repr(cleanup_errors))
    print(json.dumps({'complete': True, 'unit': unit, 'compiler_fences': 2,
                      'unit_cgroup_removed': result['unit_cgroup_removed']}))


if __name__ == '__main__':
    main()
