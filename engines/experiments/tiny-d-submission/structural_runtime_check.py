"""Finite local P4 runtime observations for a structural-cost candidate.

Uses the existing process owner and protocol session. It does not construct a
typed historical admission, qualify target NUMA/strength, or change a recipe.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def task_snapshot(pid):
    """Observe task CPU directly and visible child PPIDs, including kernels
    without CONFIG_CHECKPOINT_RESTORE's per-task children pseudo-file.

    This is a separate local observer; the historical verifier is unchanged.
    Missing task stat data is a failure, never evidence of a settled worker.
    """
    result = {}
    for path in (Path('/proc') / str(pid) / 'task').iterdir():
        fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
        result[int(path.name)] = {'state': fields[0],
            'cpu_ticks': int(fields[11]) + int(fields[12]), 'children': []}
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal(): continue
        try:
            fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
        except (FileNotFoundError, ProcessLookupError):
            continue  # unrelated process ended during this visible-process scan
        parent = int(fields[1])
        if parent in result: result[parent]['children'].append(int(path.name))
    if any(row['children'] for row in result.values()):
        raise ValueError('visible engine child process observed')
    descriptors = sorted(path.name for path in (Path('/proc') / str(pid) / 'fd').iterdir())
    if descriptors != ['0', '1', '2']:
        raise ValueError('engine has a non-stdio descriptor')
    return result


def session_type(protocol):
    class LocalSession(protocol.Session):
        def between(self):
            observed = task_snapshot(self.owned.process.pid)
            if len(observed) != self.policy['between_GO_threads']:
                raise ValueError('persistent worker count differs')
            return observed

        def observe_workers(self, before, started, maximum):
            positive = set(); samples = []
            while True:
                current = task_snapshot(self.owned.process.pid)
                if set(current) != set(before):
                    raise ValueError('persistent worker identities changed')
                for tid, row in current.items():
                    if tid != self.owned.process.pid and row['cpu_ticks'] > before[tid]['cpu_ticks']:
                        positive.add(tid)
                samples.append({'elapsed': time.monotonic() - started, 'tasks': current})
                if len(positive) == self.workers: break
                if len(self.moves()) >= self.count:
                    raise ValueError('search ended before all workers showed positive CPU')
                if time.monotonic() - started >= min(maximum, 3):
                    raise TimeoutError('not every worker showed positive CPU')
                time.sleep(min(.01, self.owned.budget.left(.01)))
            return {'all_workers_positive_CPU': True, 'positive_CPU_participant_TIDs': sorted(positive),
                    'samples': samples, 'observer': 'task-stat CPU and visible process PPIDs'}

        def go(self, board, command, label, maximum=3, minimum=0, observe=False):
            self.count += 1; self.report['counts']['GO'] += 1
            before = task_snapshot(self.owned.process.pid)
            started = time.monotonic(); self.owned.send(command)
            activity = self.observe_workers(before, started, maximum) if observe else None
            if observe:
                self.ready_count += 1; self.owned.send(b'isready\n')
                self.owned.stdout.until(lambda data: data.splitlines().count(b'readyok') >= self.ready_count,
                                        self.owned.budget, seconds=.25)
                if len(self.moves()) >= self.count:
                    raise ValueError('ready did not precede the active search result')
                activity['asynchronous_ready_before_bestmove'] = True
            return self.result(board, label, started, maximum, minimum=minimum, activity=activity)
    return LocalSession


def run(case, out):
    cost = load('structural_runtime_cost', HERE / 'structural_size.py')
    case, out = Path(case), Path(out)
    if not out.is_absolute() or out.exists() or any((p / '.git').exists() for p in (out, *out.parents)):
        raise ValueError('new absolute output outside Git required')
    record = json.loads((case / 'result.json').read_text())
    if not record['complete'] or record.get('profile') != 'test-p4':
        raise ValueError('complete source-owned local P4 cost record required')
    native = (case / 'native/native').read_bytes()
    package = case / 'packed-xz-bcj-pb0'
    if cost.pin(native) != record['native_runs'][0]['native'] or cost.pin(package.read_bytes()) != {
            key: record['packages'][package.name][key] for key in ('bytes', 'sha256')}:
        raise ValueError('measured native/package bytes changed')
    package.chmod(0o755)
    root = HERE.parents[2]
    owner = load('structural_process_owner', root / 'engines/compact/tiny-entry-d/verify.py')
    protocol = load('structural_protocol_session', root / 'engines/experiments/tcec-scope/verify.py')
    rules = load('structural_rules_corpus', root / 'engines/experiments/tcec-next/profile_rules.py')
    oracle = rules.oracle_module()
    cases, _ = rules.fixture_cases(oracle)
    out.mkdir()
    report = {'complete': False, 'profile': 'test-p4', 'workers': 4, 'TT_bytes': 128 << 20,
              'observer': cost.pin(Path(__file__).read_bytes()),
              'child_observation': 'visible process PPIDs and owned process group',
              'package': cost.pin(package.read_bytes()), 'native': cost.pin(native),
              'counts': {'GO': 0, 'legal_bestmoves': 0}, 'sessions': [],
              'target_qualified': False, 'strength_measured': False, 'selected': False,
              'tools': {str(Path(t.__file__).relative_to(root)): cost.pin(Path(t.__file__).read_bytes())
                        for t in (owner, protocol, rules, oracle)}}
    def save():
        (out / 'runtime.json').write_text(json.dumps(report, indent=2) + '\n')
    budget = owner.Budget(110)
    manifest = {'resources': {'workers': 4}, 'runtime_policy': {
        'mode': 'final', 'variant': None, 'active_threads': 5, 'between_GO_threads': 5,
        'input_during_GO': 'asynchronous'}}
    old_term = signal.signal(signal.SIGTERM, owner.terminated)
    old_alarm = signal.signal(signal.SIGALRM, owner.terminated)
    signal.alarm(115)
    try:
        for terminal in ('quit', 'eof'):
            row = {'terminal': terminal, 'GO': [], 'passed': False}
            report['sessions'].append(row)
            started = time.monotonic()
            owned = owner.Owned(package, out / terminal, budget)
            try:
                owned.send(b'uci\nisready\n')
                owned.wait_line(b'uciok'); owned.wait_line(b'readyok')
                elapsed = time.monotonic() - started
                if elapsed >= 60:
                    raise ValueError('local startup exceeded 60 seconds')
                tids = task_snapshot(owned.process.pid)
                if len(tids) != 5:
                    raise ValueError('four persistent workers plus input thread required')
                if cost.pin(Path(f'/proc/{owned.process.pid}/exe').read_bytes()) != cost.pin(native):
                    raise ValueError('restored running native differs')
                mappings = owner.mapping(owned.process.pid)
                guards = [item for item in mappings if item['permissions'][:3] == '---']
                if len(guards) != 4:
                    raise ValueError('four worker guard mappings required')
                for guard in guards:
                    if guard['end'] - guard['start'] != 4096:
                        raise ValueError('worker guard is not one page')
                    owner.covers(mappings, guard['end'], 1 << 20, 'rw-')
                row.update(startup_seconds=elapsed, persistent_TIDs=sorted(tids),
                           restored_native_exact=True, only_stdio=True, no_children=True,
                           guarded_worker_stacks=guards, no_RWX=True,
                           local_startup_under_60_seconds=True)
                session = session_type(protocol)(owned, oracle, manifest, row, report)
                board = session.position()
                session.go(board, b'go wtime 0 btime 0\n', 'fallback-zero-clock')
                board = session.position(('e2e4',))
                session.go(board, b'go wtime 600000 btime 30 winc 0 binc 0\n', 'black-own-clock')
                board = session.position()
                session.go(board, b'go wtime 30000 btime 30000 winc 0 binc 0\n',
                           'four-workers-and-asynchronous-ready', maximum=4, observe=True)
                session.queued_positions()
                if terminal == 'quit':
                    # Actual position replay after every kind of promotion,
                    # while the independent rules fixture checks all legal sets.
                    labels = {'white-b8' + p for p in 'nbrq'} | {'black-h1' + p for p in 'nbrq'}
                    chosen = []
                    seen = set()
                    for fixture in cases:
                        label = fixture['label'].rsplit('-', 1)[0]
                        if label in labels and label not in seen:
                            chosen.append(fixture); seen.add(label)
                    if seen != labels:
                        raise ValueError('promotion replay coverage differs')
                    for fixture in chosen:
                        board = session.position(fixture['moves'])
                        session.go(board, b'go wtime 0 btime 0\n', fixture['label'])
                board = session.position()
                before = task_snapshot(owned.process.pid)
                active = time.monotonic()
                owned.send(b'go wtime 3600000 btime 3600000\n')
                session.count += 1; report['counts']['GO'] += 1
                row['active_before_terminal'] = session.observe_workers(before, active, 3)
                if sorted(task_snapshot(owned.process.pid)) != row['persistent_TIDs']:
                    raise ValueError('worker identities changed')
                completed = len(session.moves())
                if terminal == 'quit': owned.send(b'quit\n')
                owned.close_input()
                row['settled'] = owned.finish()
                results = session.moves()
                # The maintained immediate exit_group contract does not owe an
                # active terminal reply. Any raced reply must still be legal.
                if len(results) not in (completed, completed + 1):
                    raise ValueError('unexpected terminal result count')
                if len(results) > completed:
                    if results[-1] not in {str(move) for move in board.legal_moves()}:
                        raise ValueError('illegal raced terminal reply')
                    report['counts']['legal_bestmoves'] += 1
                if not owned.stdout.bytes().endswith(b'\n'):
                    raise ValueError('partial final protocol output')
                row['passed'] = True
            finally:
                row['cleanup'] = owned.cleanup()
                save()
                if row['passed'] and (row['cleanup']['forced_cleanup'] or row['cleanup']['errors']):
                    raise ValueError('natural terminal cleanup failed')
        report['complete'] = True
    except BaseException as error:
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGTERM, old_term); signal.signal(signal.SIGALRM, old_alarm)
        save()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.case, args.out)
    print(json.dumps({'complete': result['complete'], 'counts': result['counts'],
        'sessions': [{key: row[key] for key in ('terminal', 'startup_seconds', 'passed', 'settled')}
                     for row in result['sessions']]}))
