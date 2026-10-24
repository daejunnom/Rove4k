#!/usr/bin/env python3
"""Positive qualification of the separate eight-worker F source-script entry.

Launch only the ordinary builder's exact whole script. Observe the resulting
native image and persistent worker pool through read-only /proc interfaces.
No compiler is invoked directly and no debugger, tracing or fault case is used.
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
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PUBLISHING = False
DEFERRED_SIGNAL = None


def bounded_signal(signum, frame):
    global DEFERRED_SIGNAL
    if PUBLISHING:
        DEFERRED_SIGNAL = signum
        return
    raise TimeoutError('bounded verifier signal '+str(signum))


def publish_owned(helper, image, out, budget):
    global PUBLISHING, DEFERRED_SIGNAL
    PUBLISHING = True
    try:
        owned = helper.Owned(image, out, budget)
    finally:
        PUBLISHING = False
    if DEFERRED_SIGNAL is not None:
        signum, DEFERRED_SIGNAL = DEFERRED_SIGNAL, None
        raise TimeoutError('bounded verifier signal '+str(signum))
    return owned


def require(value, message):
    if not value:
        raise AssertionError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def identity(path, expected=None):
    path = Path(path)
    raw = path.read_bytes()
    result = {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}
    if expected is not None:
        require(all(result[k] == expected[k] for k in ('bytes', 'sha256')), 'literal artifact identity differs: ' + str(path))
    return result


class Queue:
    def __init__(self, owned):
        self.owned = owned
        self.lines, self.queued = [], []
        self.pending, self.offset = b'', 0
        self.dispatched = self.accepted = 0

    def pump(self, seconds=0):
        if seconds:
            time.sleep(seconds)
        raw = self.owned.stdout.bytes()
        self.pending += raw[self.offset:]
        self.offset = len(raw)
        while b'\n' in self.pending:
            line, self.pending = self.pending.split(b'\n', 1)
            text = line.decode('ascii', errors='strict')
            self.lines.append(text)
            self.queued.append(text)

    def send(self, text):
        self.dispatched += sum(line.split()[:1] == ['go'] for line in text.splitlines())
        self.owned.send(text.encode('ascii'))

    def until(self, prefix, seconds=8):
        end = time.monotonic() + self.owned.budget.left(seconds)
        while time.monotonic() < end:
            while self.queued:
                line = self.queued.pop(0)
                if line.startswith(prefix):
                    return line
                require(not line.startswith('bestmove '), 'unexpected result before expected protocol boundary')
            self.pump(.005)
            require(not self.owned.stderr.bytes(), 'engine wrote stderr')
        raise TimeoutError('missing response ' + repr(prefix) + '; tail=' + repr(self.lines[-8:]))

    def best(self, allowed):
        line = self.until('bestmove ')
        match = re.fullmatch(r'bestmove ([a-h][1-8][a-h][1-8][nbrq]?)', line)
        require(match is not None and match.group(1) in allowed, 'illegal or malformed result: ' + line)
        self.accepted += 1
        require(self.accepted <= self.dispatched, 'extra result consumed')
        return match.group(1)

    def no_extra(self, active=False):
        self.pump(.015)
        expected = self.dispatched - int(active)
        require(self.accepted == expected and sum(s.startswith('bestmove ') for s in self.lines) == expected and
                not any(s.startswith('bestmove ') for s in self.queued), 'GO/result accounting or duplicate result differs')


def native_identity(pid, expected):
    link = os.readlink(f'/proc/{pid}/exe')
    require(link.endswith(' (deleted)'), 'compiled private native is not unlinked')
    path = Path(link[:-10])
    require(path.is_absolute() and path.name == 'x' and path.parent.name.startswith('r4-'), 'unexpected private native path')
    require(not path.exists() and not path.parent.exists(), 'private compiled executable/directory remains')
    actual = identity(Path(f'/proc/{pid}/exe'), expected)
    return {'exe_link': link, 'native_bytes': actual['bytes'], 'native_sha256': actual['sha256'],
            'private_executable_absent': True, 'private_parent_absent': True, 'private_parent': str(path.parent)}


def startup_states(pid):
    """Startup phase observation only; no FD/children/resource acceptance."""
    result = {}
    for path in Path(f'/proc/{pid}/task').iterdir():
        fields = (path/'stat').read_text().rsplit(')', 1)[1].split()
        result[int(path.name)] = fields[0]
    return result


def startup(owned, expected, helper, waiting):
    end = time.monotonic() + owned.budget.left(30)
    last = None
    while time.monotonic() < end:
        require(not owned.exited(), 'whole script exited before native worker startup')
        try:
            link = os.readlink(f'/proc/{owned.process.pid}/exe')
            if link.endswith(' (deleted)') and Path(link[:-10]).name == 'x' and Path(link[:-10]).parent.name.startswith('r4-'):
                native = native_identity(owned.process.pid, expected)
                pre_first = startup_states(owned.process.pid)
                waiting['samples'].append({'phase': 'waiting-count-state-only-not-resource-acceptance',
                                           'tasks': pre_first})
                last = pre_first
                if len(pre_first) == 9 and all(state == 'S' for state in pre_first.values()):
                    time.sleep(owned.budget.left(.05))
                    pre_second = startup_states(owned.process.pid)
                    waiting['samples'].append({'phase': 'waiting-count-state-only-not-resource-acceptance',
                                               'tasks': pre_second})
                    if set(pre_second) == set(pre_first) and all(state == 'S' for state in pre_second.values()):
                        waiting['strict_tasks_started_after_stable_nine_idle'] = True
                        first = helper.tasks(owned.process.pid)
                        if len(first) == 9 and all(v['state'] == 'S' for v in first.values()):
                            time.sleep(owned.budget.left(.05))
                            second = helper.tasks(owned.process.pid)
                            if set(second) == set(first) and all(v['state'] == 'S' for v in second.values()):
                                return sorted(first), {'native': native, 'first_tasks': first, 'second_tasks': second,
                                                      'pre_FD_count_state_first': pre_first,
                                                      'pre_FD_count_state_second': pre_second,
                                                      'idle_worker_CPU_tick_delta': {str(t): second[t]['cpu_ticks']-first[t]['cpu_ticks']
                                                                                    for t in first if t != owned.process.pid}}
                        last = first
        except FileNotFoundError:
            pass
        time.sleep(owned.budget.left(.005))
    raise TimeoutError('exact native identity and nine persistent idle TIDs not observed: ' + repr(last))


def observe(owned, expected_tids, helper, directory):
    tasks = helper.tasks(owned.process.pid)
    require(sorted(tasks) == expected_tids, 'persistent startup TIDs changed')
    maps = helper.mapping(owned.process.pid)
    status = {}
    for line in Path(f'/proc/{owned.process.pid}/status').read_text().splitlines():
        name, _, value = line.partition(':')
        if name in ('VmSize', 'VmRSS', 'Threads'):
            status[name] = value.strip()
    require(status.get('Threads') == '9', 'status thread count differs')
    directory.mkdir(parents=True)
    (directory/'maps.txt').write_text(Path(f'/proc/{owned.process.pid}/maps').read_text())
    return {'tasks': tasks, 'status': status, 'maps': maps,
            'scope': 'current mapped/RSS/VM observations; stack peak and throughput not measured',
            'no_WX_and_nonexec_process_stack': True, 'task_children_absent_and_stdio_only': True}


def active(owned, tids, helper):
    before = helper.tasks(owned.process.pid)
    require(sorted(before) == tids, 'startup TIDs changed before final GO')
    workers = [tid for tid in tids if tid != owned.process.pid]
    end, started, samples = time.monotonic()+owned.budget.left(3), time.monotonic(), []
    while time.monotonic() < end:
        current = helper.tasks(owned.process.pid)
        require(sorted(current) == tids, 'startup TIDs changed during final GO')
        delta = {str(t): current[t]['cpu_ticks']-before[t]['cpu_ticks'] for t in workers}
        samples.append({'elapsed': time.monotonic()-started, 'tasks': current, 'worker_CPU_tick_delta': delta})
        if current[owned.process.pid]['state'] == 'S' and all(current[t]['state'] == 'R' for t in workers) and all(n > 0 for n in delta.values()):
            return {'main_state': 'S', 'worker_states': ['R']*8, 'worker_CPU_tick_delta': delta,
                    'same_nine_TIDs': True, 'all_eight_worker_CPU_deltas_positive': True, 'samples': samples}
        time.sleep(owned.budget.left(.005))
    raise AssertionError('eight-worker active CPU observation absent: ' + repr(samples[-5:]))


def legal(oracle, history):
    board = oracle.Board.from_fen()
    for move in history:
        board = board.play(move)
    result = {str(move) for move in board.legal_moves()}
    require(result, 'normal fixture has no legal witness')
    return result


def qualify(image, whole, native, out, shutdown, budget, helper, oracle, row):
    identity(image, whole)
    owned = publish_owned(helper, image, out, budget)
    q = Queue(owned)
    tids = [owned.process.pid]
    row.update(pid=owned.process.pid, shutdown=shutdown, passed=False, results=[])
    row['startup_wait'] = {'scope': 'count/state only before strict FD/children inspection; not readiness acceptance',
                           'samples': [], 'strict_tasks_started_after_stable_nine_idle': False}
    try:
        tids, row['startup'] = startup(owned, native, helper, row['startup_wait'])
        row['startup_TIDs'] = tids
        row['startup_resources'] = observe(owned, tids, helper, out/'startup')
        q.send('uci\nisready\n')
        require(q.until('uciok') == 'uciok' and q.until('readyok') == 'readyok', 'minimal UCI acknowledgment differs')
        require(q.lines == ['uciok', 'readyok'], 'unexpected identification/option output')
        q.no_extra()
        histories = ([], ['e2e4'], ['d2d4', 'g8f6', 'c2c4'])
        allowed = [legal(oracle, h) for h in histories]
        q.send('position startpos\ngo\n')
        row['results'].append({'phase': 'bare GO natural completion', 'move': q.best(allowed[0]), 'legal': True})
        q.no_extra()
        q.send('position startpos moves e2e4\ngo wtime 3000 btime 3000\n')
        # The next position is a required physical completion fence for GO2.
        q.send('position startpos moves d2d4 g8f6 c2c4\nisready\n')
        row['results'].append({'phase': 'old black result before position readiness fence', 'move': q.best(allowed[1]), 'legal': True})
        require(q.until('readyok') == 'readyok', 'position readiness fence absent')
        q.no_extra()
        q.send('go wtime 3000 btime 3000\n')
        row['results'].append({'phase': 'three-move position clock completion', 'move': q.best(allowed[2]), 'legal': True})
        q.no_extra()
        q.send('go wtime 600000 btime 600000\n')
        row['active'] = active(owned, tids, helper)
        q.no_extra(active=True)
        row['active_resources'] = observe(owned, tids, helper, out/'active')
        row['active_native'] = native_identity(owned.process.pid, native)
        if shutdown == 'quit':
            q.send('quit\n')
        owned.close_input()
        row['settled'] = owned.finish()
        q.pump()
        row['results'].append({'phase': 'active final result before physical exit', 'move': q.best(allowed[2]), 'legal': True})
        q.no_extra()
        require(q.dispatched == 4 and q.accepted == 4 and not q.pending and
                q.lines.count('uciok') == 1 and q.lines.count('readyok') == 2,
                'final result/acknowledgment/partial tail differs')
        require(all(line in ('uciok', 'readyok') or line.startswith('bestmove ') for line in q.lines), 'unexpected public output')
        row.update(dispatched_GO=4, legal_bestmoves=4, stdout_sha256=sha(owned.stdout.bytes()),
                   completion_fence='GO2 result before replacement position readyok; active quit/EOF physically settled',
                   cancellation_causality='unproven; no tracing performed', hard_wall_cap='not claimed')
    except BaseException as error:
        row['operation_error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        cleanup = owned.cleanup()
        cleanup['all_observed_nine_TIDs_absent'] = all(not Path(f'/proc/{tid}').exists() for tid in tids)
        row['cleanup'] = cleanup
        if owned.finished:
            require(not cleanup['forced_cleanup'] and not cleanup['errors'] and cleanup['readers_joined'] and
                    cleanup['owned_group_absent'] and cleanup['all_observed_nine_TIDs_absent'], 'physical exit/readers/group needed intervention')
    row['passed'] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out, built = args.out.resolve(), args.build.resolve()
    require(sys.platform == 'linux' and args.build.is_absolute() and args.out.is_absolute() and not out.exists() and
            not any((part/'.git').exists() for part in (out, *out.parents)), 'new external absolute Linux output required')
    out.mkdir(parents=True)
    report = {'passed': False, 'scope': 'eight-worker F source-script normal positive qualification; quit and EOF; four GO each',
              'sessions': [], 'direct_compiler_invocations': 0, 'ptrace': 0, 'tracing': 0, 'negative_fault_or_SAN': 0,
              'resource_limits': {'parent_AS': 4*1024**3, 'child_inherited_AS': 4*1024**3,
                                  'parent_CPU': 180, 'child_inherited_CPU': 180, 'aggregate_wall': 120, 'per_pipe_bytes': 1048576},
              'resource_scope': 'each child inherits AS/CPU caps before exec; aggregate wall/alarm and per-operation Budget finite',
              'script_compilation': 'ordinary whole script compiles its selected source; compiler descendants are not traced',
              'stack_peak_and_throughput': 'not measured'}
    def save():
        (out/'runtime.json').write_text(json.dumps(report, indent=2)+'\n')
    saved_handlers = {sig: signal.signal(sig, bounded_signal)
                      for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM, signal.SIGXCPU)}
    helper = None
    try:
        resource.setrlimit(resource.RLIMIT_AS, (4*1024**3,)*2)
        resource.setrlimit(resource.RLIMIT_CPU, (180,)*2)
        signal.alarm(120)
        builder = module('f_resource8_builder', HERE/'build.py')
        closure = builder.source_closure()
        require(all(sha(builder.normalized(REPO/name)) == digest for name, digest in closure.items()), 'current source closure differs')
        recipe_raw = builder.normalized(HERE/'recipe.json')
        recipe = json.loads(recipe_raw)
        recorded = json.loads((built/'build.json').read_text())
        require(recorded['complete'] and recorded['source_closure'] == closure and recorded['recipe_sha256'] == sha(recipe_raw),
                'ordinary builder/source/recipe identity differs')
        require(recorded['class'] == recipe['class'] == 'full-F-late-fixed-resource8-TT18-v10' and
                recorded['base_stage'] == recipe['base_stage'] == 'full-after-MTD-state-and-sole-GO',
                'fixed late resource8 v10 class/base stage differs')
        identity(built/'base-source.c', recipe['base_source'])
        require(recorded['profile'] == recipe['profile'] == {'workers': 8, 'tt_bits': 18, 'ply': 128, 'native_TIDs': 9}, 'fixed resource8 profile differs')
        expected = recipe['expected']
        pins = {name: {'bytes': expected[name+'_bytes'], 'sha256': expected[name+'_sha256']}
                for name in ('source', 'native', 'bootstrap', 'whole')}
        require(len(recorded['attempts']) == 2, 'ordinary builder must reproduce twice')
        for attempt in recorded['attempts']:
            for name, pin in pins.items():
                identity(attempt[name]['path'], pin)
        helper = module('f_resource8_owned', HERE.parent/'tiny-entry-d/verify.py')
        oracle = module('f_resource8_oracle', REPO/'engines/tests/chess_oracle.py')
        report.update(source_closure=closure, recipe_sha256=sha(recipe_raw), profile=recorded['profile'],
                      actual_build=str(built/'build.json'), selected_artifacts=pins,
                      helpers={str(p.relative_to(REPO)): identity(p) for p in
                               (HERE.parent/'tiny-entry-d/verify.py', REPO/'engines/tests/chess_oracle.py')})
        image = Path(recorded['attempts'][0]['whole']['path'])
        budget = helper.Budget(120)
        for shutdown in ('quit', 'EOF'):
            row = {'shutdown': shutdown, 'whole': identity(image, pins['whole'])}
            report['sessions'].append(row)
            save()
            qualify(image, pins['whole'], pins['native'], out/shutdown, shutdown, budget, helper, oracle, row)
            save()
        require(len(report['sessions']) == 2 and all(row['passed'] for row in report['sessions']) and not helper.OWNED,
                'selected normal sessions or owned registry incomplete')
        require(builder.source_closure() == closure, 'source changed during qualification')
        report['passed'] = True
    except BaseException as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        if helper is not None:
            report['final_owned_cleanup'] = [owned.cleanup() for owned in tuple(helper.OWNED)]
        signal.alarm(0)
        for sig, handler in saved_handlers.items():
            signal.signal(sig, handler)
        save()
    print(json.dumps({'passed': report['passed'], 'sessions': len(report['sessions']), 'report': str(out/'runtime.json')}))


if __name__ == '__main__':
    main()