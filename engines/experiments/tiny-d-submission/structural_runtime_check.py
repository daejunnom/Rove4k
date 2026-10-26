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


def failure(error):
    return {'type': type(error).__name__, 'message': str(error)}


class RuntimeOwner:
    """Own this observation's signals, registered children and final receipt.

    Owned registers the original process before constructing its Readers and
    unblocking TERM. A deferred signal may therefore precede its return value;
    final settlement must use the registry, not only the caller's local handle.
    """
    def __init__(self, owner, report, save):
        self.owner, self.report, self.save = owner, report, save
        self.constructing = self.cleaning = False
        self.deferred_signal = None
        self.handlers = {}
        self.previous_timer = None
        self.previous_mask = None
        self.previous_pending = set()
        self.timer_owned = False
        self.signals = {signal.SIGTERM, signal.SIGINT, signal.SIGALRM, signal.SIGXCPU}
        self.readers = []
        self.adapter = report.setdefault('ownership_adapter', {
            'kind': 'local Reader subclass captured before original initialization',
            'observer': report.get('observer'), 'readers': []})

    def bounded_signal(self, signum, frame):
        if self.constructing or self.cleaning:
            if self.deferred_signal is None:
                self.deferred_signal = signum
            return
        raise TimeoutError('structural runtime observer signal ' + str(signum))

    def __enter__(self):
        if self.owner.OWNED:
            raise ValueError('runtime observer requires an empty owned registry')
        self.cleaning = True
        try:
            self.previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
            signal.pthread_sigmask(signal.SIG_BLOCK, self.signals)
            self.previous_pending = signal.sigpending() & self.signals
            self.timer_started = time.monotonic()
            self.previous_timer = signal.getitimer(signal.ITIMER_REAL)
            self.timer_owned = True
            signal.setitimer(signal.ITIMER_REAL, 0)
            for sig in self.signals:
                self.handlers[sig] = signal.getsignal(sig)
                signal.signal(sig, self.bounded_signal)
            remaining = self.previous_timer[0]
            signal.setitimer(signal.ITIMER_REAL, min(115, remaining) if remaining else 115)
            # Keep setup deferred until every old handler is recorded. Unmasking
            # can itself deliver a pending callback before this call returns.
            signal.pthread_sigmask(signal.SIG_SETMASK, self.previous_mask)
            if self.deferred_signal is not None:
                raise TimeoutError('structural runtime observer signal '
                                   + str(self.deferred_signal))
            self.cleaning = False
            return self
        except BaseException as error:
            self.finalize(error)
            raise

    def construct(self, path, directory, budget):
        self.constructing = True
        original_reader, lifetime = self.owner.Reader, self
        self.adapter['original_reader'] = original_reader.__module__ + '.' + original_reader.__qualname__

        class CapturedReader(original_reader):
            def __init__(reader, pipe, name):
                trace = {'name': name, 'initialization_complete': False}
                lifetime.readers.append((reader, pipe, trace))
                lifetime.adapter['readers'].append(trace)
                try:
                    super().__init__(pipe, name)
                except BaseException as error:
                    trace['construction_failure'] = failure(error)
                    raise
                trace['initialization_complete'] = True

        try:
            self.owner.Reader = CapturedReader
            owned = self.owner.Owned(path, directory, budget)
        finally:
            self.owner.Reader = original_reader
            self.constructing = False
        if self.deferred_signal is not None:
            pending, self.deferred_signal = self.deferred_signal, None
            self.bounded_signal(pending, None)
        return owned

    def settle_readers(self, owned):
        """Attempt captured Reader joins after the original owner's cleanup.

        An initializer may start its non-daemon Thread and then raise before
        Owned assigns stdout/stderr. Do not attach that partial object to Owned:
        its historical cleanup assumes assigned Readers initialized fully.
        """
        errors = []
        for reader, pipe, trace in self.readers:
            if pipe is not owned.process.stdout and pipe is not owned.process.stderr:
                continue
            trace['pid'] = owned.process.pid
            trace['assigned_to_owner'] = reader is owned.stdout or reader is owned.stderr
            thread = getattr(reader, 'thread', None)
            trace['thread_created'] = thread is not None
            trace['thread_started'] = thread is not None and thread.ident is not None
            try:
                if thread is not None:
                    try:
                        thread.join(timeout=3)
                    except RuntimeError:
                        # Thread creation/start can fail before a join is valid.
                        if thread.ident is not None or thread.is_alive():
                            raise
                trace['reader_settled'] = thread is None or not thread.is_alive()
                if not trace['reader_settled']:
                    raise RuntimeError('captured output reader remains alive')
                pipe.close()
            except BaseException as error:
                trace['cleanup_failure'] = failure(error)
                errors.append(trace['cleanup_failure'])
        return errors

    def cleanup(self, owned, row, *, natural):
        observation = {'pid': owned.process.pid}
        was_cleaning = self.cleaning
        self.cleaning = True
        try:
            try:
                result = owned.cleanup()
            finally:
                reader_errors = self.settle_readers(owned)
                if reader_errors:
                    self.report.setdefault('cleanup_failure', []).append(
                        {'pid': owned.process.pid, 'captured_readers': reader_errors})
            observation['cleanup'] = result
            if row is not None:
                row['cleanup'] = result
            if (result.get('owned_group_absent') is not True
                    or result.get('readers_joined') is not True
                    or result.get('errors') != [] or reader_errors
                    or (natural and result.get('forced_cleanup') is not False)):
                raise ValueError('owned process group/readers did not settle cleanly')
        except BaseException as error:
            observation['failure'] = failure(error)
            self.report.setdefault('cleanup_failure', []).append(observation)
            if row is not None:
                row['cleanup_failure'] = observation['failure']
        finally:
            self.cleaning = was_cleaning
        return observation

    def restore_signals(self):
        errors = []
        if self.timer_owned:
            try:
                signal.setitimer(signal.ITIMER_REAL, 0)
            except BaseException as error:
                errors.append(failure(error))
        try:
            # These arrived while this observer owned the handlers. Do not
            # deliver them to restored caller handlers, or consume signals
            # which were already pending when setup first blocked the set.
            pending = ((signal.sigpending() & self.signals) - self.previous_pending
                       if self.handlers else set())
            for sig in pending:
                signal.sigwait({sig})
                if self.deferred_signal is None:
                    self.deferred_signal = sig
        except BaseException as error:
            errors.append(failure(error))
        for sig, handler in self.handlers.items():
            try:
                signal.signal(sig, handler)
            except BaseException as error:
                errors.append(failure(error))
        if self.previous_timer is not None:
            try:
                previous, interval = self.previous_timer
                elapsed = time.monotonic() - self.timer_started
                expired = bool(previous and elapsed >= previous)
                remaining = (interval - ((elapsed - previous) % interval)
                             if expired and interval else
                             0 if expired or not previous else previous - elapsed)
                signal.setitimer(signal.ITIMER_REAL, remaining, interval)
                if expired:
                    # Queue the actual elapsed event while blocked. A tiny new
                    # timer could instead invoke the old callback after this
                    # protected restoration, replacing the primary body error.
                    signal.raise_signal(signal.SIGALRM)
            except BaseException as error:
                errors.append(failure(error))
        if self.previous_mask is not None:
            try:
                signal.pthread_sigmask(signal.SIG_SETMASK, self.previous_mask)
            except BaseException as error:
                # A restored expired timer's old callback can raise here, after
                # the mask was restored. Preserve the body error and receipt.
                errors.append(failure(error))
        if errors:
            self.report.setdefault('cleanup_failure', []).append({'signal_restore': errors})

    def finalize(self, error):
        self.report['complete'] = False
        if error is not None:
            self.report['failure'] = failure(error)
        self.cleaning = True
        final_error = None
        try:
            try:
                if self.previous_mask is not None:
                    signal.pthread_sigmask(signal.SIG_BLOCK, self.signals)
                if self.timer_owned:
                    signal.setitimer(signal.ITIMER_REAL, 0)
            except BaseException as cleanup_error:
                self.report.setdefault('cleanup_failure', []).append(failure(cleanup_error))
            self.report['final_owned_cleanup'] = []
            for item in tuple(self.owner.OWNED):
                try:
                    observed = self.cleanup(item, None, natural=error is None)
                except BaseException as cleanup_error:
                    observed = {'failure': failure(cleanup_error)}
                    self.report.setdefault('cleanup_failure', []).append(observed)
                self.report['final_owned_cleanup'].append(observed)
            self.report['owned_remaining'] = len(self.owner.OWNED)
            if self.report['owned_remaining']:
                self.report.setdefault('cleanup_failure', []).append(
                    {'owned_remaining': self.report['owned_remaining']})
        except BaseException as cleanup_error:
            self.report.setdefault('cleanup_failure', []).append(failure(cleanup_error))
        if self.deferred_signal is not None:
            self.report['deferred_signal'] = self.deferred_signal
            if error is None:
                final_error = TimeoutError('structural runtime observer signal '
                                           + str(self.deferred_signal))
        if error is None and self.report.get('cleanup_failure'):
            final_error = final_error or RuntimeError('runtime observation ownership cleanup failed')
        if final_error is not None:
            self.report['failure'] = failure(final_error)
        # Persist an incomplete final receipt before rearming an expired old
        # timer or unblocking its handler. Either operation may invoke it.
        try:
            self.save()
        except BaseException as save_error:
            self.report['complete'] = False
            self.report['receipt_failure'] = failure(save_error)
            final_error = final_error or save_error
        try:
            self.restore_signals()
        except BaseException as restore_error:
            self.report.setdefault('cleanup_failure', []).append(
                {'signal_restore': failure(restore_error)})
        self.cleaning = False
        if self.deferred_signal is not None:
            self.report['deferred_signal'] = self.deferred_signal
            if error is None:
                final_error = final_error or TimeoutError('structural runtime observer signal '
                                                        + str(self.deferred_signal))
        if error is None and self.report.get('cleanup_failure'):
            final_error = final_error or RuntimeError('runtime observation ownership cleanup failed')
        if error is None and final_error is not None:
            self.report['failure'] = failure(final_error)
        self.report['complete'] = (error is None and final_error is None
                                   and self.report.get('observations_complete') is True)
        try:
            self.save()
        except BaseException as save_error:
            self.report['complete'] = False
            self.report.setdefault('receipt_failure', failure(save_error))
            self.report['receipt_failure']['final_save_failure'] = failure(save_error)
            final_error = final_error or save_error
        if error is None and final_error is not None:
            raise final_error

    def __exit__(self, exc_type, error, traceback):
        self.finalize(error)
        return False


def request_terminal(owned, session, terminal, started):
    """Sample the unanswered GO at the boundary that sends quit/closes stdin.

    A result racing after this observation remains optional and must be legal;
    an already completed GO cannot stand in for active-terminal evidence.
    """
    if terminal not in ('quit', 'eof'):
        raise ValueError('unknown terminal request')
    completed = len(session.moves())
    if completed >= session.count:
        raise ValueError('terminal request was not made during an unanswered GO')
    requested = time.monotonic()
    if terminal == 'quit':
        owned.send(b'quit\n')
    owned.close_input()
    return completed, {
        'terminal': terminal, 'requested_at_monotonic': requested,
        'seconds_after_GO': requested - started,
        'bestmoves_before_request': completed, 'expected_GO_results': session.count,
        'active_GO_unanswered': True,
    }


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
    case, out = Path(case), cost.new_output(out)
    record = json.loads((case / 'result.json').read_text())
    cost.require_settled_cost(record)
    if record.get('profile') != 'test-p4':
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
    save()
    with RuntimeOwner(owner, report, save) as lifetime:
        for terminal in ('quit', 'eof'):
            row = {'terminal': terminal, 'GO': [], 'passed': False}
            report['sessions'].append(row)
            started = time.monotonic()
            owned = lifetime.construct(package, out / terminal, budget)
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
                completed, row['terminal_request'] = request_terminal(
                    owned, session, terminal, active)
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
                lifetime.cleanup(owned, row, natural=row['passed'])
            if row.get('cleanup_failure'):
                raise RuntimeError('natural terminal cleanup failed')
            save()
        report['observations_complete'] = True
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
