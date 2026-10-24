#!/usr/bin/env python3
"""Qualify an explicit source/Bash delayed-cleanup shell submission.

This is separate from the ordinary Python compiler-owner verifier. The selected
recipe supplies expected source/native/whole identities; this verifier never
fills those expectations from produced files. It observes the temporary image
before cleanup, then its absence and cleanup-child settlement while the same
engine is still alive. Only the explicit Bash/ignore-after-compile policy is
accepted here. Cancellation during compilation is a separate negative campaign.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
HELPERS = {
    'engines/compact/tiny-entry-d/verify.py': '18faa69aed5cb5dd85a054ef2e6830463f3d819f5f635d74d55550a877c81eae',
    'engines/tests/chess_oracle.py': 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8',
}
CONSTRUCTING_OWNED = False
DEFERRED_SIGNAL = None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def bounded_signal(signum, frame):
    global DEFERRED_SIGNAL
    if CONSTRUCTING_OWNED:
        # The frozen helper registers a new session before returning. Deferring
        # a Python exception here leaves the child's inherited mask unchanged.
        DEFERRED_SIGNAL = signum
        return
    raise TimeoutError('shell verifier signal ' + str(signum))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def task_snapshot(pid):
    proc = Path('/proc')/str(pid)
    result = {}
    for path in (proc/'task').iterdir():
        fields = (path/'stat').read_text().rsplit(')', 1)[1].split()
        result[int(path.name)] = {'state': fields[0],
            'cpu_ticks': int(fields[11]) + int(fields[12]),
            'children': (path/'children').read_text().split()}
    return result


def snapshot(pid, expected_native, *, settled=False):
    proc = Path('/proc')/str(pid)
    link = str((proc/'exe').readlink())
    raw = (proc/'exe').read_bytes()
    require(sha(raw) == expected_native, 'actual shell-compiled native image differs')
    path = Path(link.removesuffix(' (deleted)'))
    tasks = task_snapshot(pid)
    fds = sorted(p.name for p in (proc/'fd').iterdir())
    require(fds == ['0', '1', '2'], 'engine has a non-stdio descriptor')
    maps = (proc/'maps').read_text()
    require(all(not ('w' in row.split()[1] and 'x' in row.split()[1])
                for row in maps.splitlines()), 'writable executable memory mapping')
    stacks = [row for row in maps.splitlines() if '[stack]' in row]
    require(stacks and all('x' not in row.split()[1] for row in stacks), 'main stack is executable')
    status = (proc/'status').read_text()
    ignored = next(row.split()[1] for row in status.splitlines() if row.startswith('SigIgn:'))
    require(int(ignored, 16) & (1 << 16), 'Bash policy did not preserve ignored SIGCHLD into native')
    if settled:
        require(link.endswith(' (deleted)') and not path.exists() and not path.parent.exists(),
                'named shell restoration path remains after cleanup deadline')
        require(not any(row['children'] for row in tasks.values()),
                'cleanup child remains live or zombie after deadline')
    memory = {row.split(':', 1)[0]: row.split(':', 1)[1].strip()
              for row in status.splitlines() if row.startswith(('VmRSS:', 'VmSize:'))}
    return {'exe': link, 'native_sha256': sha(raw), 'named_path': str(path),
        'path_exists': path.exists(), 'directory_exists': path.parent.exists(),
        'tasks': tasks, 'FDs': fds, 'fd0': str((proc/'fd/0').readlink()),
        'cmdline': (proc/'cmdline').read_bytes().decode(errors='replace').split('\0'),
        'SIGCHLD_ignored': True, 'no_WX': True, 'main_stack_NX': True,
        'maps': maps, 'memory_snapshot_not_peak': memory}


def main():
    global CONSTRUCTING_OWNED
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--recipe', type=Path, required=True,
                        help='explicit effective recipe for this selected wrapper and engine policy')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build, out, recipe_path = args.build.resolve(), args.out.resolve(), args.recipe.resolve()
    require(sys.platform == 'linux', 'Linux /proc shell-policy target required')
    require(args.build.is_absolute() and args.out.is_absolute() and args.recipe.is_absolute()
            and not out.exists() and out != REPO and REPO not in out.parents
            and not any((p/'.git').exists() for p in (out, *out.parents)),
            'absolute inputs and new output outside every Git checkout required')
    tmp = os.environ.get('TMPDIR')
    require(tmp is None or Path(tmp).is_absolute(), 'relative TMPDIR is outside this shell target contract')
    recipe_raw = recipe_path.read_bytes().replace(b'\r\n', b'\n')
    recipe = json.loads(recipe_raw)
    expected = recipe['expected']
    profile = recipe['profile']
    workers = profile['workers']
    require(type(workers) is int and workers in (2, 8) and profile['tt_bits'] == 18,
            'explicit F two/eight-worker, TT18 profile required')
    whole = (build/'x').read_bytes()
    for name, key in (('x', 'whole'), ('main.c', 'source'), ('native/x', 'native')):
        data = (build/name).read_bytes()
        require(len(data) == expected[key + '_bytes'] and sha(data) == expected[key + '_sha256'],
                'selected shell artifact differs from explicit recipe: ' + name)
    require(whole.startswith(b'#!/bin/bash\n'), 'this verifier accepts the explicit Bash policy only')
    require(b'trap \'\' CHLD;' in whole.split(b'\n', 8)[7],
            'explicit post-compiler child reaping policy missing')
    # The currently qualified engine class makes no process children. This is a
    # narrow source check, not a theorem for arbitrary C programs or libraries.
    source = (build/'main.c').read_bytes()
    process_calls = re.findall(rb'\b(?:fork|vfork|clone|clone3|execve|execv|execvp|execl|wait|waitpid|waitid|posix_spawn|system|popen)\s*\(', source)
    require(not process_calls, 'ignored SIGCHLD needs a selected source with no process-child API calls')
    out.mkdir(parents=True)
    inputs = out/'inputs'
    inputs.mkdir()
    helper_rows = {}
    for relative, pin in HELPERS.items():
        data = (REPO/relative).read_bytes().replace(b'\r\n', b'\n')
        require(sha(data) == pin, 'shell verifier helper changed: ' + relative)
        target = inputs/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        helper_rows[relative] = {'bytes': len(data), 'sha256': pin}
    helper = load('shell_owned', inputs/'engines/compact/tiny-entry-d/verify.py')
    oracle = load('shell_oracle', inputs/'engines/tests/chess_oracle.py')
    report = {'complete': False, 'scope': 'new source/Bash shell whole, fixed recipe and actual native, delayed cleanup, legal GO and physical exit',
        'wrapper_policy': 'source-shell-bash-ignore-after-compile-v1',
        'recipe_sha256': sha(recipe_raw), 'expected_contract': expected,
        'profile': profile, 'helper_inputs': helper_rows, 'sessions': [],
        'actual_affinity': sorted(os.sched_getaffinity(0)),
        'workers_exceed_admitted_CPUs': workers > len(os.sched_getaffinity(0)),
        'resource_limits': {'AS_per_inheriting_process': 2147483648,
            'CPU_per_inheriting_process_soft_hard': [90, 95], 'aggregate_wall_alarm': 180},
        'counts': {'shell_launches': 0, 'compiler_invocations_by_exact_source_header': 0,
                   'GO': 0, 'legal_bestmoves': 0},
        'source_process_child_call_tokens': [], 'engine_algorithms_or_resources_changed': False,
        'target_environment': {'TMPDIR': tmp, 'Bash_path': '/bin/bash'},
        'limits_on_claims': ['no tournament admission', 'no strength/speed/peak claim',
            'compile cancellation not covered by this positive verifier',
            'SIGCHLD ignore and named/deferred cleanup differ from ordinary owner',
            'process-child source check is not arbitrary-C semantic analysis']}
    def save():
        (out/'runtime.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    def best(owned, board, command, count):
        owned.send(command)
        report['counts']['GO'] += 1
        owned.wait_best(count)
        lines = owned.stdout.bytes().splitlines()
        moves = [line.split()[1].decode() for line in lines if line.startswith(b'bestmove ')]
        require(len(moves) == count and moves[-1] in {str(m) for m in board.legal_moves()},
                'shell result is not exactly one legal move per GO')
        report['counts']['legal_bestmoves'] += 1
        require(len(task_snapshot(owned.process.pid)) == workers + 1, 'worker TID count changed')
        return moves[-1]
    resource.setrlimit(resource.RLIMIT_AS, (2147483648,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (90, 95))
    saved_handlers = {sig: signal.signal(sig, bounded_signal)
                      for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM, signal.SIGXCPU)}
    signal.alarm(180)
    try:
        for eof in (False, True):
            label = 'EOF' if eof else 'quit'
            started = time.monotonic()
            session_out = out/label
            session_out.mkdir()
            CONSTRUCTING_OWNED = True
            try:
                owned = helper.Owned(build/'x', session_out, helper.Budget(80))
            finally:
                CONSTRUCTING_OWNED = False
            if DEFERRED_SIGNAL is not None:
                bounded_signal(DEFERRED_SIGNAL, None)
            report['counts']['shell_launches'] += 1
            report['counts']['compiler_invocations_by_exact_source_header'] += 1
            try:
                parent_stdin = os.fstat(owned.process.stdin.fileno())
                owned.send(b'uci\nisready\n')
                owned.stdout.until(lambda data: b'uciok' in data.splitlines()
                                   and b'readyok' in data.splitlines(),
                                   owned.budget, seconds=60)
                ready_wall = time.monotonic() - started
                require(ready_wall <= 60, 'actual shell startup exceeds60 seconds')
                startup = snapshot(owned.process.pid, expected['native_sha256'])
                startup['wall_from_launch'] = ready_wall
                startup_ids = sorted(startup['tasks'])
                require(len(startup_ids) == workers + 1, 'fixed worker pool did not start')
                time.sleep(.03)
                stable_tasks = task_snapshot(owned.process.pid)
                require(sorted(stable_tasks) == startup_ids, 'startup worker TIDs were not persistent')
                if workers == 8:
                    require(all(task['state'] == 'S' for task in stable_tasks.values()),
                            'nine persistent idle TIDs were not sleeping')
                startup['persistent_tasks_after_30ms'] = stable_tasks
                native_stdin = os.stat(Path('/proc')/str(owned.process.pid)/'fd/0')
                require((parent_stdin.st_dev, parent_stdin.st_ino) ==
                        (native_stdin.st_dev, native_stdin.st_ino), 'original UCI stdin pipe changed')
                initial_path = Path(startup['named_path'])
                require(startup['path_exists'] and startup['directory_exists']
                        and any(item['children'] for item in startup['tasks'].values()),
                        'initial named executable/cleanup child phase was not observed')
                row = {'termination': label, 'pid': owned.process.pid, 'startup': startup,
                       'native_compile_exact': True, 'original_UCI_stdin_pipe_preserved': True,
                       'completed': []}
                board = oracle.Board.from_fen()
                owned.send(b'position startpos\n')
                row['completed'].append(best(owned, board, b'go wtime 0 btime 0\n', 1))
                board = board.play('e2e4')
                owned.send(b'position startpos moves e2e4\n')
                row['completed'].append(best(owned, board, b'go wtime 0 btime 0\n', 2))
                board = oracle.Board.from_fen()
                owned.send(b'position startpos\n')
                row['completed'].append(best(owned, board, b'go\n', 3))
                cleanup_deadline = started + 60
                while initial_path.parent.exists() or any(
                        item['children'] for item in task_snapshot(owned.process.pid).values()):
                    require(time.monotonic() < cleanup_deadline, 'delayed cleanup failed within startup60s window')
                    time.sleep(.01)
                settled_image = snapshot(owned.process.pid, expected['native_sha256'], settled=True)
                require(sorted(settled_image['tasks']) == startup_ids, 'persistent worker TIDs changed')
                settled_image['wall_from_launch'] = time.monotonic() - started
                require(settled_image['wall_from_launch'] <= 60,
                        'cleanup completion was not observed within startup60s window')
                row['after_delayed_cleanup'] = settled_image
                before = task_snapshot(owned.process.pid)
                owned.send(b'position startpos\ngo wtime 60000 btime 60000\n')
                report['counts']['GO'] += 1
                active_deadline = time.monotonic() + 3
                activity_samples = []
                while True:
                    after = task_snapshot(owned.process.pid)
                    require(sorted(after) == startup_ids, 'active worker TIDs changed')
                    active = [tid for tid in startup_ids if tid != owned.process.pid
                              and after[tid]['cpu_ticks'] > before[tid]['cpu_ticks']]
                    activity_samples.append({'tasks': after, 'worker_CPU_advanced': active})
                    eight_active = (len(active) == 8 and after[owned.process.pid]['state'] == 'S'
                                    and all(after[tid]['state'] == 'R' for tid in active))
                    if (workers == 2 and active) or (workers == 8 and eight_active):
                        break
                    require(time.monotonic() < active_deadline, 'closing GO did not show worker CPU activity')
                    time.sleep(.01)
                row['closing_activity'] = {'before': before, 'after': after,
                    'worker_CPU_advanced': active, 'samples': activity_samples,
                    'all_eight_workers_active_positive_CPU': eight_active if workers == 8 else 'not requested',
                    'cancellation_causality': 'unproven'}
                if eof:
                    owned.close_input()
                else:
                    owned.send(b'quit\n')
                owned.wait_best(4)
                closing = [line.split()[1].decode() for line in owned.stdout.bytes().splitlines()
                           if line.startswith(b'bestmove ')]
                require(len(closing) == 4 and closing[-1] in {str(m) for m in board.legal_moves()},
                        'closing result lost/duplicated/illegal')
                report['counts']['legal_bestmoves'] += 1
                row['completed'].append(closing[-1])
                row['settled'] = owned.finish()
                terminal_closing = [line.split()[1].decode() for line in owned.stdout.bytes().splitlines()
                                    if line.startswith(b'bestmove ')]
                require(terminal_closing == closing,
                        'bestmove output changed before physical exit and reader EOF')
                row['cleanup'] = owned.cleanup()
                require(not (Path('/proc')/str(owned.process.pid)).exists(), 'main PID remains after reap')
                require(all(not (Path('/proc')/str(tid)).exists() for tid in startup_ids),
                        'observed worker TID remains after physical exit')
                row['all_observed_TIDs_absent'] = True
                row.update(complete=True, closing_result_once=True,
                    stdout_sha256=sha(owned.stdout.bytes()), wall_from_launch=time.monotonic() - started)
                report['sessions'].append(row)
                save()
            finally:
                cleanup = owned.cleanup()
                if not report['sessions'] or report['sessions'][-1].get('pid') != owned.process.pid:
                    report.setdefault('failed_session_cleanup', []).append(cleanup)
        report['complete'] = True
    except BaseException as error:
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        report['final_owned_cleanup'] = [item.cleanup() for item in tuple(helper.OWNED)]
        report['owned_remaining'] = len(helper.OWNED)
        save()
        signal.alarm(0)
        for sig, handler in saved_handlers.items():
            signal.signal(sig, handler)
    print(json.dumps({'complete': True, 'sessions': 2, 'whole_bytes': len(whole),
                      'GO': report['counts']['GO'], 'legal': report['counts']['legal_bestmoves']}), flush=True)


if __name__ == '__main__':
    main()
