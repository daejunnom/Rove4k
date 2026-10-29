#!/usr/bin/env python3
"""Exercise a freshly built, explicitly identified TCEC full-engine submission.

The selected product contract requires responsive isready during finite GO.
Synchronous GO is an explicit comparison experiment. Persistent startup TIDs,
private compiler cancellation, descriptor
minimality and mapping policy are not admission requirements here. The test
host still owns each original process group until it has physically settled.
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
REPO = Path(__file__).resolve().parents[3]
HELPERS = {
    'engines/compact/tiny-entry-d/verify.py':
        '18faa69aed5cb5dd85a054ef2e6830463f3d819f5f635d74d55550a877c81eae',
    'engines/tests/chess_oracle.py':
        'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8',
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
        # The frozen Owned constructor registers the original child and its
        # readers before unblocking TERM. Preserve that construction fence.
        DEFERRED_SIGNAL = signum
        return
    raise TimeoutError('TCEC verifier signal ' + str(signum))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def task_snapshot(pid):
    result = {}
    for path in (Path('/proc')/str(pid)/'task').iterdir():
        try:
            fields = (path/'stat').read_text().rsplit(')', 1)[1].split()
            result[int(path.name)] = {
                'state': fields[0],
                'cpu_ticks': int(fields[11]) + int(fields[12]),
                'children': (path/'children').read_text().split(),
            }
        except (FileNotFoundError, ProcessLookupError):
            # Per-GO workers can join while this observation is being read.
            continue
    return result


def image_snapshot(pid, native_sha):
    proc = Path('/proc')/str(pid)
    image = (proc/'exe').read_bytes()
    require(sha(image) == native_sha, 'actual runtime-compiled native image differs')
    link = str((proc/'exe').readlink())
    status = (proc/'status').read_text()
    return {
        'exe': link, 'native_sha256': sha(image),
        'path': link.removesuffix(' (deleted)'),
        'path_exists': Path(link.removesuffix(' (deleted)')).exists(),
        'tasks': task_snapshot(pid),
        'memory_snapshot_not_peak': {
            row.split(':', 1)[0]: row.split(':', 1)[1].strip()
            for row in status.splitlines() if row.startswith(('VmRSS:', 'VmSize:'))
        },
    }


def checked_file(path, expected, prefix):
    data = path.read_bytes()
    require(len(data) == expected[prefix + '_bytes']
            and sha(data) == expected[prefix + '_sha256'],
            'selected artifact differs from explicit build contract: ' + str(path))
    return data


def source_input(relative, expected, root=REPO):
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts,
            'build source input must be repository-relative: ' + relative)
    require(path.name not in ('inventory.json', 'package-lock.json')
            and not path.name.startswith('.env')
            and not any(part in ('node_modules', 'dist', 'dist-server', 'build',
                                 'coverage', 'models', 'checkpoints', '.cache') for part in path.parts),
            'source closure contains a non-source input: ' + relative)
    data = (root/path).read_bytes().replace(b'\r\n', b'\n')
    require(len(data) == expected['bytes'] and sha(data) == expected['sha256'],
            'current source input differs from build closure: ' + relative)
    return data


def freeze_inputs(manifest, out, build):
    closure = dict(manifest['inputs'])
    verifier = manifest['selected_verifier']
    require(verifier['path'] == 'engines/experiments/tcec-scope/verify.py',
            'build selected a different verifier')
    for relative, expected in verifier['inputs'].items():
        require(relative not in closure or closure[relative] == expected,
                'inconsistent source closure pin: ' + relative)
        closure[relative] = expected
    require(verifier['path'] in closure, 'verifier itself must be pinned by the build')
    for relative, pin in HELPERS.items():
        data = (REPO/relative).read_bytes().replace(b'\r\n', b'\n')
        require(sha(data) == pin, 'frozen runtime helper changed: ' + relative)
        expected = {'bytes': len(data), 'sha256': pin}
        require(relative not in closure or closure[relative] == expected,
                'build and verifier helper pins disagree: ' + relative)
        closure[relative] = expected
    for relative, expected in closure.items():
        data = source_input(relative, expected)
        target = out/'inputs'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    require(manifest['control_source_closure'], 'fresh canonical producer closure is missing')
    for relative, expected in manifest['control_source_closure'].items():
        data = source_input(relative, expected, build/'producer-repo')
        target = out/'control-inputs'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return closure


def replay(oracle, moves):
    board = oracle.Board.from_fen()
    for move in moves:
        board = board.play(move)
    return board


def promotion_fixtures(oracle):
    # Both promotion corridors are opened by ordinary legal startpos moves.
    # Clearing f1/g1 makes black R/Q promotions check the white king. Extra
    # moves turn black N/B cases into check as well, so an untouched start
    # position cannot accidentally satisfy the expected legal-move set.
    prefix = 'e2e4 b8c6 g1f3 g8f6 f1d3 e7e6 a2a4 h7h5 a4a5 h5h4 a5a6 h4h3 a6b7 h3g2'.split()
    rows = []
    for piece in 'nbrq':
        rows.append(('white-' + piece, prefix + ['b7a8' + piece, 'g2h1q']))
    rows.extend((
        ('black-r', prefix + ['b7a8q', 'g2h1r']),
        ('black-b', prefix + ['b7a8q', 'g2h1b', 'e1f1', 'h1g2']),
        ('black-n', prefix + ['b7a8q', 'g2h1n', 'b2b3', 'h1f2', 'c2c3', 'f2d3']),
    ))
    initial_legal = {str(move) for move in oracle.Board.from_fen().legal_moves()}
    result = []
    for label, moves in rows:
        board = replay(oracle, moves)
        legal = {str(move) for move in board.legal_moves()}
        require(board.in_check(board.turn) and legal and not legal & initial_legal,
                'promotion fixture is not a legal discriminating check: ' + label)
        result.append((label, moves, board))
    return result


class Session:
    def __init__(self, owned, oracle, manifest, row, report):
        self.owned, self.oracle, self.manifest = owned, oracle, manifest
        self.row, self.report = row, report
        self.count, self.ready_count = 0, 1
        self.policy = manifest['runtime_policy']
        self.workers = manifest['resources']['workers']

    def moves(self):
        found = []
        for line in self.owned.stdout.bytes().splitlines():
            if line.startswith(b'bestmove '):
                fields = line.split()
                require(len(fields) == 2 and re.fullmatch(rb'[a-h][1-8][a-h][1-8][nbrq]?', fields[1]),
                        'malformed bestmove line: ' + repr(line))
                found.append(fields[1].decode('ascii'))
        return found

    def position(self, moves=()):
        self.owned.send(('position startpos' + (' moves ' + ' '.join(moves) if moves else '') + '\n').encode())
        return replay(self.oracle, moves)

    def ready(self):
        self.ready_count += 1
        self.owned.send(b'isready\n')
        self.owned.wait_line(b'readyok', self.ready_count)

    def between(self):
        deadline = time.monotonic() + self.owned.budget.left(2)
        while True:
            observed = task_snapshot(self.owned.process.pid)
            require(len(observed) <= self.policy['active_threads'], 'thread resource cap exceeded between GO')
            if len(observed) == self.policy['between_GO_threads']:
                return observed
            require(time.monotonic() < deadline, 'GO worker lifetime did not settle before next command')
            time.sleep(.002)

    def result(self, board, label, started, maximum, *, minimum=0, activity=None):
        self.owned.stdout.until(lambda data: sum(line.startswith(b'bestmove ') for line in data.splitlines())
                                >= self.count, self.owned.budget, seconds=maximum)
        elapsed = time.monotonic() - started
        moves = self.moves()
        require(len(moves) == self.count and moves[-1] in {str(move) for move in board.legal_moves()},
                label + ': lost, duplicated or illegal bestmove')
        require(minimum <= elapsed <= maximum, label + ': finite clock budget outside observation bound')
        self.report['counts']['legal_bestmoves'] += 1
        # ready may be queued until a synchronous GO joins. The selected
        # contract does not require it to overtake an active search.
        self.ready()
        between = self.between()
        row = {'label': label, 'bestmove': moves[-1], 'wall_seconds': elapsed,
               'observed_wall_bounds': [minimum, maximum], 'between_GO_tasks': between}
        if activity is not None:
            row['activity'] = activity
        self.row['GO'].append(row)
        return moves[-1]

    def go(self, board, command, label, maximum=3, minimum=0, observe=False):
        self.count += 1
        self.report['counts']['GO'] += 1
        before = task_snapshot(self.owned.process.pid)
        started = time.monotonic()
        self.owned.send(command)
        activity = None
        if observe:
            activity = self.observe_workers(before, started, maximum)
            self.ready_count += 1
            early_ready_count = self.ready_count
            ready_started = time.monotonic()
            self.owned.send(b'isready\n')
            asynchronous = self.policy['input_during_GO'] == 'asynchronous'
            if asynchronous:
                self.owned.stdout.until(lambda data: data.splitlines().count(b'readyok') >= early_ready_count,
                                        self.owned.budget, seconds=.25)
                require(sum(line.startswith(b'bestmove ') for line in self.owned.stdout.bytes().splitlines())
                        < self.count, 'isready was deferred until the active GO completed')
            activity['active_GO_isready'] = {
                            'contract': self.policy['input_during_GO'],
                            'response_before_bestmove': asynchronous,
                            'response_wall_seconds': time.monotonic()-ready_started if asynchronous else None,
                            'response_bound_seconds': .25 if asynchronous else None,
                            'deferred_response_allowed': not asynchronous,
                        }
        return self.result(board, label, started, maximum, minimum=minimum, activity=activity)

    def observe_workers(self, before, started, maximum):
        leader = self.owned.process.pid
        main_participates = self.policy['mode'] == 'per-go' and self.policy['variant'] == 'main'
        baseline = {tid: data['cpu_ticks'] for tid, data in before.items()}
        positive, observed_ids, peak, samples = set(), set(before), len(before), []
        deadline = started + min(maximum, 3)
        while True:
            after = task_snapshot(leader)
            require(len(after) <= self.policy['active_threads'], 'GO exceeded declared thread cap')
            peak = max(peak, len(after))
            observed_ids.update(after)
            for tid, data in after.items():
                if (main_participates or tid != leader) and data['cpu_ticks'] > baseline.get(tid, 0):
                    positive.add(tid)
            if len(samples) < 400:
                samples.append({'at': time.monotonic()-started, 'tasks': after})
            if len(positive) >= self.workers and peak == self.policy['active_threads']:
                break
            require(sum(line.startswith(b'bestmove ') for line in self.owned.stdout.bytes().splitlines())
                    < self.count, 'GO completed before every declared worker showed positive CPU')
            require(time.monotonic() < deadline, 'not every declared worker showed positive CPU during GO')
            time.sleep(.005)
        return {'before': before, 'positive_CPU_participant_TIDs': sorted(positive),
                'all_observed_TIDs': sorted(observed_ids), 'peak_threads': peak,
                'all_workers_positive_CPU': True, 'samples': samples,
                'simultaneously_running_state_required': False}

    def queued_positions(self):
        white = self.oracle.Board.from_fen()
        black = white.play('e2e4')
        self.owned.send(b'position startpos\ngo wtime 0 btime 0\n'
                        b'position startpos moves e2e4\ngo wtime 0 btime 0\n')
        self.report['counts']['GO'] += 2
        self.count += 2
        self.owned.wait_best(self.count)
        moves = self.moves()
        require(len(moves) == self.count
                and moves[-2] in {str(move) for move in white.legal_moves()}
                and moves[-1] in {str(move) for move in black.legal_moves()},
                'queued GO/position transitions lost, duplicated or corrupted a position')
        self.report['counts']['legal_bestmoves'] += 2
        self.ready()
        self.row['queued_GO_positions'] = {'bestmoves': moves[-2:], 'between_GO_tasks': self.between()}


def normal_cleanup(owned, startup, contract, launched):
    strategy = contract['temp_strategy']
    path = Path(startup['path'])
    # The wrapper, not the engine protocol, declares which path it owns.
    remove_parent = contract.get('parent_removed', contract.get('remove_parent', False))
    require(type(remove_parent) is bool, 'wrapper remove_parent must be explicit boolean')
    deadline = min(launched+60, time.monotonic()+owned.budget.left(contract['cleanup_seconds']))
    while path.exists() or (remove_parent and path.parent.exists()):
        require(not owned.exited(), 'engine exited before normal temporary cleanup was observed')
        require(time.monotonic() < deadline, 'normal wrapper temporary output was not removed')
        time.sleep(.01)
    require(not owned.exited(), 'normal temporary cleanup was not observed while engine remained alive')
    require(time.monotonic()-launched <= 60, 'normal temporary cleanup exceeded startup60s observation')
    return {'temp_strategy': strategy, 'path': str(path), 'path_absent': True,
            'parent_owned': remove_parent,
            'parent_absent': not path.parent.exists() if remove_parent else None,
            'cleanup_seconds': contract['cleanup_seconds'],
            'observed_wall_from_launch': time.monotonic()-launched}


def finish_owned(owned, terminal_observation=None):
    # The intentionally small wrapper can leave an exited cleanup child for
    # the system reaper. Retain the original leader until that entire group
    # has physically settled; never reap first and signal a recycled PGID.
    deadline = time.monotonic() + owned.budget.left(10)
    while True:
        exited, others = owned.exited(), owned.group_others()
        if terminal_observation is not None and exited and 'leader_exit_observed' not in terminal_observation:
            terminal_observation['leader_exit_observed'] = {
                'seconds_after_request': time.monotonic()-terminal_observation['requested_at_monotonic'],
                'other_group_members': others,
                'temporary_path_exists': Path(terminal_observation['temporary_path']).exists(),
                'original_leader_unreaped': not owned.reaped,
            }
        if exited and not others:
            break
        require(time.monotonic() < deadline, 'terminal process group did not physically settle')
        time.sleep(.005)
    return owned.finish()


def main():
    global CONSTRUCTING_OWNED, DEFERRED_SIGNAL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build, out = args.build.resolve(), args.out.resolve()
    require(sys.platform == 'linux', 'Linux /proc runtime target required')
    require(args.build.is_absolute() and args.out.is_absolute() and not out.exists()
            and out != REPO and REPO not in out.parents
            and not any((path/'.git').exists() for path in (out, *out.parents)),
            'absolute build and new output outside every Git checkout required')
    manifest_raw = (build/'build.json').read_bytes()
    manifest = json.loads(manifest_raw)
    require(manifest['format'] == 1 and manifest['class'] in ('tcec-full-C-v1', 'tcec-full-Rust-A-v1'),
            'explicit TCEC full C or Rust-A build contract required')
    rust_a = manifest['class'] == 'tcec-full-Rust-A-v1'
    require(manifest['complete'] is True and manifest['reproducible'] is True,
            'fresh build has not completed its reproduction contract')
    require(manifest['actual'] == {'source': 'main.rs' if rust_a else 'main.c',
                                   'native': 'native/x', 'program': 'x'},
            'unrecognized canonical build artifact layout')
    require(manifest['entry'] in (('Rust-A',) if rust_a else ('A', 'B', 'C', 'E', 'F', 'F8'))
            and manifest['family'] == ('A' if rust_a else
                'F' if manifest['entry'] == 'F8' else manifest['entry']),
            'unrecognized full engine entry/family')
    resources, policy = manifest['resources'], manifest['runtime_policy']
    workers = resources['workers']
    require(workers == (8 if manifest['entry'] == 'F8' else 2)
            and resources['tt_bits'] == 18 and resources['ply'] == 128
            and resources['max_position_plies'] >= 1024,
            'fixed full TT18/ply128 resource profile differs')
    require(policy['mode'] in ('control', 'final', 'per-go'), 'unknown runtime policy')
    per_go = policy['mode'] == 'per-go'
    require(not rust_a or not per_go, 'this Rust-A contract requires a persistent two-worker runtime')
    require(not per_go or policy['variant'] in ('spawn', 'main', 'async'), 'unknown per-GO worker topology')
    active = workers if per_go and policy['variant'] == 'main' else workers+1
    require(policy['active_threads'] == active
            and policy['startup_threads'] == (1 if per_go else active)
            and policy['between_GO_threads'] == (1 if per_go else active),
            'runtime topology and declared thread bounds disagree')
    expected = manifest['expected_contract']
    source = checked_file(build/manifest['actual']['source'], expected, 'source')
    checked_file(build/manifest['actual']['native'], expected, 'native')
    whole = checked_file(build/manifest['actual']['program'], expected, 'whole')
    header_bytes = expected['header_bytes']
    require(0 < header_bytes < len(whole)
            and sha(whole[:header_bytes]) == expected['header_sha256']
            and len(whole)-header_bytes == expected['payload_bytes']
            and sha(whole[header_bytes:]) == expected['payload_sha256'],
            'whole/header/payload contract differs')
    require(len(manifest['attempts']) == 2, 'two fresh build attempts are required')
    for attempt, directory in zip(manifest['attempts'], ('first', 'repeat')):
        require(attempt['directory'] == directory
                and {key: attempt[key] for key in expected} == expected,
                'recorded fresh build attempt differs from the explicit selected contract')
    require(manifest['attempts'][0]['source_proofs'] == manifest['attempts'][1]['source_proofs']
            == manifest.get('source_proofs', []), 'fresh source transformation proofs differ')
    require(all(proof['full_inverse'] is True for proof in manifest.get('source_proofs', [])),
            'selected source stage did not preserve its full inverse contract')
    require(manifest['qualification']['selection'] in ('selected-literal-recipe', 'experimental-measurement'),
            'build must distinguish literal selection from comparison measurement')
    require(policy['input_during_GO'] in ('asynchronous', 'queued_until_join'),
            'unrecognized GO input scheduling contract')
    require(manifest['qualification']['selection'] != 'selected-literal-recipe'
            or policy['input_during_GO'] == 'asynchronous',
            'selected TCEC profile requires responsive isready during active GO')
    contract = manifest['wrapper_contract']
    require(type(contract['cleanup_seconds']) in (int, float) and 0 <= contract['cleanup_seconds'] <= 60,
            'wrapper cleanup observation must have finite startup bound')
    out.mkdir(parents=True)
    (out/'build.json').write_bytes(manifest_raw)
    closure = freeze_inputs(manifest, out, build)
    helper = load('tcec_scope_owned', out/'inputs/engines/compact/tiny-entry-d/verify.py')
    oracle = load('tcec_scope_oracle', out/'inputs/engines/tests/chess_oracle.py')
    fixtures = promotion_fixtures(oracle)
    report = {
        'format': 1, 'class': manifest['class'], 'entry': manifest['entry'],
        'build_sha256': sha(manifest_raw), 'expected_contract': expected,
        'source_closure': closure, 'resources': resources, 'runtime_policy': policy,
        'canonical_producer_source_closure': manifest['control_source_closure'],
        'wrapper_contract': contract, 'selection': manifest['qualification']['selection'],
        'producer_source_proofs': manifest.get('source_proofs', []),
        'complete': False, 'sessions': [], 'counts': {'GO': 0, 'legal_bestmoves': 0},
        'host_limits': {'address_space_bytes': 2147483648, 'per_process_CPU_seconds': [180, 185],
                        'aggregate_wall_alarm_seconds': 300, 'affinity': sorted(os.sched_getaffinity(0))},
        'scope': ['full selected source identity and fresh runtime-compiled image identity',
                  'finite minimum protocol, legal moves, clock sides/increments, queued positions',
                  'responsive active-GO isready for asynchronous selected profiles',
                  'actual selected worker topology/CPU activity and between-GO lifetime',
                  'normal wrapper temporary-output cleanup and idle/active quit/EOF physical exit',
                  'active terminal requests before delayed temporary cleanup, where declared'],
        'not_proven': ['TCEC admission, current tournament hardware or external runner acceptance',
                       'playing strength, NPS, many-core scaling or peak memory',
                       'black-box promotion replay is not exhaustive move-generation equivalence',
                       'repetition/fifty-move replay alone cannot inspect an unreported draw score',
                       'compiler cancellation and private exception ordering are separate experiments',
                       'retained learner state is a source/runtime proof, not observable UCI output'],
    }
    def save():
        (out/'runtime.json').write_text(json.dumps(report, indent=2)+'\n')
    save()
    resource.setrlimit(resource.RLIMIT_AS, (2147483648,)*2)
    resource.setrlimit(resource.RLIMIT_CPU, (180, 185))
    saved_handlers = {sig: signal.signal(sig, bounded_signal)
                      for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM, signal.SIGXCPU)}
    signal.alarm(300)
    try:
        for eof, active_terminal in ((False, False), (True, False), (False, True), (True, True)):
            label = ('active-' if active_terminal else '') + ('EOF' if eof else 'quit')
            session_out = out/label
            session_out.mkdir()
            started = time.monotonic()
            CONSTRUCTING_OWNED = True
            try:
                owned = helper.Owned(build/manifest['actual']['program'], session_out, helper.Budget(140))
            finally:
                CONSTRUCTING_OWNED = False
            if DEFERRED_SIGNAL is not None:
                pending, DEFERRED_SIGNAL = DEFERRED_SIGNAL, None
                bounded_signal(pending, None)
            row = {'termination': label, 'active_terminal': active_terminal,
                   'pid': owned.process.pid, 'complete': False, 'GO': []}
            report['sessions'].append(row)
            save()
            try:
                parent_stdin = os.fstat(owned.process.stdin.fileno())
                owned.send(b'uci\nisready\n')
                owned.stdout.until(lambda data: b'uciok' in data.splitlines() and b'readyok' in data.splitlines(),
                                   owned.budget, seconds=60)
                row['startup_wall_seconds'] = time.monotonic()-started
                require(row['startup_wall_seconds'] <= 60, 'runtime compilation/startup exceeded 60 seconds')
                startup = image_snapshot(owned.process.pid, expected['native_sha256'])
                require(len(startup['tasks']) == policy['startup_threads'], 'selected startup topology differs')
                native_stdin = os.stat(Path('/proc')/str(owned.process.pid)/'fd/0')
                require((parent_stdin.st_dev, parent_stdin.st_ino) == (native_stdin.st_dev, native_stdin.st_ino),
                        'source restoration consumed or replaced the original UCI stdin pipe')
                row.update(startup=startup, original_UCI_stdin_pipe_preserved=True)
                session = Session(owned, oracle, manifest, row, report)
                if active_terminal:
                    board = session.position()
                    before = task_snapshot(owned.process.pid)
                    search_started = time.monotonic()
                    session.count = 1
                    report['counts']['GO'] += 1
                    owned.send(b'go wtime 30000 btime 0 winc 2000 binc 0\n')
                    activity = session.observe_workers(before, search_started, 4.5)
                    require(not session.moves(), 'terminal request was not made during an active GO')
                    temporary_path = Path(startup['path'])
                    request = {
                        'requested_at_monotonic': time.monotonic(),
                        'seconds_after_GO': time.monotonic()-search_started,
                        'temporary_path': str(temporary_path),
                        'temporary_path_exists': temporary_path.exists(),
                        'other_group_members': owned.group_others(),
                        'bestmoves_before_request': [],
                        'input_during_GO': policy['input_during_GO'],
                    }
                    delayed = contract.get('cleanup_delay_seconds', 0) > 0
                    if delayed:
                        require(request['temporary_path_exists'] and any(
                            member['state'] != 'Z' for member in request['other_group_members']),
                            'active terminal did not observe the declared live delayed-cleanup phase')
                    if eof:
                        owned.close_input()
                    else:
                        owned.send(b'quit\n')
                    row['terminal_request'] = request
                    save()
                    row['settled'] = finish_owned(owned, request)
                    closing = session.moves()
                    require(len(closing) <= 1 and all(
                        move in {str(item) for item in board.legal_moves()} for move in closing),
                        'active terminal emitted duplicate or illegal bestmove')
                    require(not temporary_path.exists(), 'temporary executable remains after terminal group settlement')
                    report['counts']['legal_bestmoves'] += len(closing)
                    row['GO'].append({'label': 'active-terminal', 'activity': activity,
                        'bestmoves': closing, 'bestmove_required': False,
                        'terminal_contract': 'finite GO may be terminated without a closing result; any result must be legal',
                        'temporary_path_absent_after_group_settlement': True})
                    row['cleanup'] = owned.cleanup()
                    require(row['cleanup']['owned_group_absent'] and row['cleanup']['readers_joined']
                            and not row['cleanup']['forced_cleanup'] and not row['cleanup']['errors'],
                            'active terminal process group/reader cleanup failed')
                    row.update(complete=True, wall_seconds=time.monotonic()-started,
                               stdout_sha256=sha(owned.stdout.bytes()), stderr_sha256=sha(owned.stderr.bytes()))
                    save()
                    continue
                row['normal_temporary_cleanup'] = normal_cleanup(owned, startup, contract, started)
                board = session.position()
                session.go(board, b'go wtime 0 btime 3600000 winc 0 binc 8000\n',
                           'white-own-zero-other-large', maximum=2)
                board = session.position(['e2e4'])
                session.go(board, b'go wtime 3600000 btime 0 winc 8000 binc 0\n',
                           'black-own-zero-other-large', maximum=2)
                board = session.position()
                session.go(board, b'go\n', 'bare-finite-GO', maximum=4, minimum=.5)
                session.queued_positions()
                # Unsupported commands are consumed between finite jobs. No
                # active-stop or state-reset semantics are required by this profile.
                owned.send(b'stop\nucinewgame\n')
                session.ready()
                row['unsupported_stop_ucinewgame'] = 'consumed without protocol corruption'
                board = session.position()
                session.go(board, b'go wtime 15000 btime 0 winc 1000 binc 0\n',
                           'white-increment-workers', maximum=4.5, minimum=.8, observe=True)
                board = session.position(['e2e4'])
                session.go(board, b'go wtime 0 btime 15000 winc 0 binc 1000\n',
                           'black-increment-workers', maximum=4.5, minimum=.8, observe=True)
                if not eof:
                    for promotion, moves, board in fixtures:
                        session.position(moves)
                        session.go(board, b'go wtime 0 btime 0\n', 'promotion-replay-'+promotion)
                    long_moves = 'g1f3 g8f6 f3g1 f6g8'.split()*256
                    board = session.position(long_moves)
                    require(board.halfmove == 1024, 'long fixture does not reach intended reversible ply count')
                    session.go(board, b'go wtime 0 btime 0\n', 'long-valid-repetition-fifty-move-replay')
                    row['long_position'] = {'plies': len(long_moves),
                        'line_bytes': len(('position startpos moves '+' '.join(long_moves)+'\n').encode()),
                        'oracle_halfmove': board.halfmove,
                        'draw_score_observation': 'not exposed by the minimum shipping protocol'}
                terminal_moves = session.moves()
                if eof:
                    owned.close_input()
                else:
                    owned.send(b'quit\n')
                row['settled'] = finish_owned(owned)
                require(session.moves() == terminal_moves, 'bestmove count changed before terminal reader EOF')
                row['cleanup'] = owned.cleanup()
                require(row['cleanup']['owned_group_absent'] and row['cleanup']['readers_joined']
                        and not row['cleanup']['forced_cleanup'] and not row['cleanup']['errors'],
                        'normal process group/reader cleanup failed')
                row.update(complete=True, wall_seconds=time.monotonic()-started,
                           stdout_sha256=sha(owned.stdout.bytes()), stderr_sha256=sha(owned.stderr.bytes()))
                save()
            finally:
                cleanup = owned.cleanup()
                if not row['complete']:
                    row['failed_session_cleanup'] = cleanup
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
    print(json.dumps({'complete': True, 'entry': manifest['entry'],
                      'selection': manifest['qualification']['selection'],
                      'whole_bytes': len(whole), **report['counts']}), flush=True)


if __name__ == '__main__':
    main()
