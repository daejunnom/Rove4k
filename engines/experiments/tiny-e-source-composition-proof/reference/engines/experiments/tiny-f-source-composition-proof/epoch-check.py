#!/usr/bin/env python3
"""One bounded instrumented DEV0 run of unchanged F production epoch bodies.

No shipping wrapper execution, old-engine execution, fault sweep, benchmark,
sanitizer, compiler-size claim, or race-detector claim is part of this witness.
The real worker clock is scheduled by a separate diagnostic gate; its value
and the actual engine code remain unchanged. Long jobs are forcibly drained
with cancellation causality unproven. Zero-own-clock jobs drain naturally;
actual controller now/deadline values and worker expiration are observed.
Compiler and fixture each run inside the immutable tools.run owned group.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CANDIDATE = 'ec39b5641ac9fc5ab19a0c919c05e0d68169b461cc1d32afeee83274926becbd'
OLD = 'dc065b98d99a147f862bd2d4cb0a1349ff79a2da7c1be873d906dff71cc9cd89'
TOOLS = 'f7b26670d27138229fbd20ac3207b2e48367cb878291ae42c3e40402e088a83e'
TRANSFORM = 'ad4c012792ac9c9b1dc77495fe57956621d0855cc8d0a1597f4c1d26c1332aba'
PREFIX = 'c3be7fdf0085a74173525f84d9cbb730304c27c70b20a66c853e4d2b72dd9ce2'
INPUTS = '984bbab15969fad134b1b6237e37be26c544573813adc56cdd0210d7d2e5aeed'
ORACLE = 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def only(events, name, epoch=None):
    rows = [event for event in events if event['event'] == name
            and (epoch is None or event.get('epoch') == epoch)]
    require(len(rows) == 1, f'expected exactly one {name} at epoch {epoch}')
    return rows[0]


def admit(root):
    candidate = (root / 'candidate.c').read_bytes()
    old = (root / 'control/engines/compact/tiny-entry-f/engine.c').read_bytes()
    raw = (root / 'transform.json').read_bytes()
    require(sha(candidate) == CANDIDATE and sha(old) == OLD and sha(raw) == TRANSFORM,
            'F production source/transform literal identity changed')
    transform = json.loads(raw)
    require(len(transform['sites']) == 7, 'exact seven-site composition required')
    text = old.decode()
    for site in transform['sites']:
        require(text.count(site['old']) == 1, 'old composition site is not unique')
        text = text.replace(site['old'], site['new'])
    require(text.encode() == candidate, 'F candidate is not exact forward composition')
    for site in reversed(transform['sites']):
        require(text.count(site['new']) == 1, 'new composition site is not unique')
        text = text.replace(site['new'], site['old'])
    require(text.encode() == old, 'F composition inverse differs')
    prefix = old[:old.index(b'void think(')]
    require(len(prefix) == 15340 and sha(prefix) == PREFIX
            and prefix == candidate[:candidate.index(b'void think(')], 'F search prefix changed')
    start, end = b'    w->length=game_length;', b'static pthread_mutex_t mutex='
    driver = old[old.index(start):old.index(end)]
    require(driver == candidate[candidate.index(start):candidate.index(end)], 'F MTD driver changed')
    return {'candidate_sha256': CANDIDATE, 'control_sha256': OLD, 'exact_literal_sites': 7,
            'exact_forward_and_inverse': True, 'search_prefix_bytes': len(prefix),
            'search_prefix_sha256': PREFIX, 'MTD_driver_bytes': len(driver),
            'MTD_driver_after_job_reset_byte_identical': True}



def validate(events, stdout, oracle):
    require(events and [row['seq'] for row in events] == list(range(1, len(events) + 1)),
            'diagnostic event sequence differs')
    require(not [row for row in events if row['event'] == 'violation'], 'fixture reported violation')
    source = only(events, 'fixture')
    require(source['source_sha256'] == CANDIDATE and source['DEV'] == 0
            and source['workers'] == 2 and source['tt_bits'] == 18, 'source/profile mismatch')
    initial = oracle.Board.from_fen()
    later = initial.apply(next(move for move in initial.legal_moves() if str(move) == 'e2e4'))
    piece = {'.': 0, 'P': 1, 'N': 2, 'B': 3, 'R': 4, 'Q': 5, 'K': 6,
             'p': -1, 'n': -2, 'b': -3, 'r': -4, 'q': -5, 'k': -6}

    def board_matches(event, board, length):
        require(event['board'] == [piece[item] for item in board.cells]
                and event['side'] == (1 if board.turn else -1), 'actual root differs from oracle')
        expected_castles = sum(bit for name, bit in [('K', 1), ('Q', 2), ('k', 4), ('q', 8)]
                               if name in board.castling)
        # F canonicalizes uncapturable EP, while oracle's replay state retains
        # the FEN target. Both tested roots have no legal en-passant capture.
        require(event['castles'] == expected_castles and event['ep'] == -1
                and event['half'] == board.halfmove and event['game_length'] == length,
                'actual root metadata differs')
        require(len(event['game_keys']) == length and event['game_keys'][-1] == event['hash'],
                'published path does not end at actual root key')

    startup = only(events, 'startup_wait_return')
    require(startup['epoch'] == 0 and startup['pending'] == 0 and startup['stopped'] == 1
            and startup['results'] == 0, 'startup barrier not consumed before GO')
    board_matches(startup, initial, 1)
    publications = [row for row in events if row['event'] == 'go_publication']
    results = [row for row in events if row['event'] == 'actual_result']
    require([row['epoch'] for row in publications] == [1, 2, 3, 4]
            and [row['epoch'] for row in results] == [1, 2, 3, 4], 'epoch/result inventory differs')
    require(all(row['pending'] == 2 and row['stopped'] == 0 and not row['quitting']
                for row in publications), 'public GO did not clear stopped and publish actual pool')
    require([row['results'] for row in publications] == [0, 1, 2, 3],
            'new epoch published before prior actual result')
    clocks = [row for row in events if row['event'] == 'controller_production_clock']
    require(len(clocks) == 4 and all(row['clock_id'] == 1 and row['returncode'] == 0 for row in clocks),
            'actual production monotonic-clock inventory differs')
    for index, budget in enumerate([10000, 1, 10000, 1]):
        require(clocks[index]['seq'] < publications[index]['seq']
                and publications[index]['controller_now_ms'] == clocks[index]['actual_ms']
                and publications[index]['deadline'] - clocks[index]['actual_ms'] == budget,
                'actual long/zero-own-clock deadline arithmetic differs')
    require([row['ordinal'] for row in results] == [1, 2, 3, 4]
            and all(row['pending'] == 0 for row in results), 'results are not unique final completions')
    require(stdout == ['bestmove ' + row['move'] for row in results],
            'actual protocol output differs from actual result observations')
    for i, row in enumerate(results):
        root = initial if i < 3 else later
        board_matches(row, root, 1 if i < 3 else 2)
        require(row['move'] in {str(move) for move in root.legal_moves()},
                'actual result is not independently legal')
        require(publications[i]['seq'] < row['seq'], 'result preceded actual GO publication')
        if i < 3:
            require(row['seq'] < publications[i + 1]['seq'], 'old result crossed next GO publication')

    waits = [row for row in events if row['event'] == 'production_wait_condition']
    active = []
    for epoch, before_name in [(1, 'before_go_replacement'), (3, 'before_position_wait')]:
        before = only(events, before_name)
        require(before['epoch'] == epoch and before['pending'] > 0 and before['stopped'] == 0,
                'requested active operation had no active pending search')
        observed = [row for row in events if row['event'] == 'controller_observed_claim' and row['gate'] == epoch]
        require(len(observed) == 1 and observed[0]['okay'] and observed[0]['held_mask']
                and observed[0]['gate_closed'], 'actual worker claim was not held for active operation')
        gated = [row for row in waits if row['epoch'] == epoch and row['gate_closed']]
        require(len(gated) == 1 and gated[0]['pending'] > 0 and gated[0]['stopped'] == 1
                and gated[0]['held_mask'], 'actual wait did not consume positive-pending active epoch')
        require(observed[0]['seq'] < before['seq'] < gated[0]['seq'] < results[epoch - 1]['seq'],
                'active observation/wait/result order differs')
        active.append({'epoch': epoch, 'actual_claim_clock_held_mask': gated[0]['held_mask'],
                       'actual_positive_pending_wait': True, 'actual_result_before_next_publication': True})

    natural = []
    for epoch in [2, 4]:
        entering = only(events, 'natural_completion_wait_enter', epoch)
        completed = only(events, 'natural_completion_wait_return', epoch)
        expirations = [row for row in events if row['event'] == 'actual_clock_expiration' and row['epoch'] == epoch]
        require(expirations and all(row['returncode'] == 0 and row['clock_id'] == 1
                and row['worker'] in [0, 1]
                and row['actual_ms'] >= row['deadline'] == publications[epoch - 1]['deadline']
                and publications[epoch - 1]['seq'] < row['seq'] < results[epoch - 1]['seq']
                for row in expirations), 'natural zero-clock job has no actual deadline expiration')
        require(not [row for row in waits if row['epoch'] == epoch],
                'zero-clock job was forcibly drained by positive-pending production wait')
        require(completed['okay'] and completed['pending'] == 0 and completed['stopped'] == 1
                and completed['results'] == epoch and results[epoch - 1]['stopped'] == 1
                and entering['seq'] < completed['seq'] and results[epoch - 1]['seq'] < completed['seq'],
                'zero-clock completion was not naturally settled before controller drain')
        natural.append({'epoch': epoch, 'computed_budget_ms': 1,
                        'actual_worker_expirations': len(expirations),
                        'controller_did_not_stop_positive_pending_job': True,
                        'pending_zero_before_production_wait': True})

    replacement = only(events, 'replacement_wait_return')
    old_position = only(events, 'position_wait_return')
    reused = only(events, 'position_reused_after_wait')
    black = only(events, 'black_wait_return')
    require(replacement['epoch'] == 2 and replacement['results'] == 2
            and old_position['epoch'] == 3 and old_position['results'] == 3
            and black['epoch'] == 4 and black['results'] == 4, 'drain boundaries lost results')
    for row in [replacement, old_position, black]:
        require(row['pending'] == 0 and row['stopped'] == 1
                and all(worker['history_matches'] for worker in row['workers']),
                'workers were not quiescent with actual restored history')
    board_matches(old_position, initial, 1)
    board_matches(reused, later, 2)
    require(old_position['seq'] < reused['seq'] < publications[3]['seq']
            and reused['epoch'] == 3 and reused['pending'] == 0,
            'global position was reused before actual previous epoch drained')
    require(reused['game_keys'][0] == startup['hash'] and reused['hash'] != startup['hash'],
            'actual replay path does not preserve initial and changed position keys')
    shutdown = only(events, 'shutdown_publication')
    joined = [row for row in events if row['event'] == 'join_return']
    returned = only(events, 'fixture_return')
    require(shutdown['pending'] == 0 and shutdown['quitting'] == 1 and shutdown['results'] == 4,
            'shutdown preceded final actual result')
    require([row['worker'] for row in joined] == [0, 1]
            and all(row['returncode'] == 0 for row in joined)
            and len({row['thread'] for row in joined}) == 2, 'real created pthread joins differ')
    require(shutdown['seq'] < joined[0]['seq'] < joined[1]['seq'] < returned['seq'],
            'shutdown/join/free return order differs')
    require(returned['status'] == returned['violations'] == 0 and returned['results'] == 4
            and returned['created'] == returned['joined'] == 2 and returned['table_freed'],
            'fixture did not finish exact successful joins before TT free')
    return {'actual_epochs': 4, 'actual_unique_results': 4, 'independently_legal_results': 4,
            'active_boundaries': active, 'go_clears_startup_stopped': True,
            'actual_computed_budgets_ms': [10000, 1, 10000, 1],
            'natural_zero_clock_jobs': natural,
            'position_reused_after_actual_pending_zero': True,
            'worker_fields_read_only_after_pending_zero': True, 'joined_created_threads': 2,
            'causal_attribution': 'long-job cancellation causality unproven; zero-own-clock actual worker expiry and natural completion observed; no shipping timing or general race proof'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p / '.git').exists() for p in (out, *out.parents)):
        parser.error('new absolute external output outside Git required')
    out.mkdir(parents=True)
    frozen = out / 'frozen'
    frozen.mkdir()
    report = {'complete': False, 'scope': __doc__, 'inputs': {}, 'engine_whole_executions': 0,
              'diagnostic_executions': 0, 'profile': {'DEV': 0, 'workers': 2, 'tt_bits': 18, 'ISA': 'generic x86-64; no AVX2 flag'},
              'timeout_seconds': 12,
              'private_differences': ['pre-first-GO startup stopped1',
                                      'direct think clears caller-preseeded best; no old private equality claimed'],
              'excluded': ['shipping image proof', 'old engine execution', 'broad fault injection',
                           'same-job MTD witness proof (separate fixture)', 'join-failure safety',
                           'SAN/TSAN', 'performance', 'variant sweep']}

    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')

    tools = None
    save()
    try:
        manifest_raw = (HERE / 'inputs.json').read_bytes()
        require(sha(manifest_raw) == INPUTS, 'literal F proof closure changed')
        manifest = json.loads(manifest_raw)
        for prefix, key in [('control', 'control_files'), ('reference', 'reference_files')]:
            for name, pin in manifest[key].items():
                raw = (HERE / prefix / name).read_bytes()
                require(b'\r' not in raw and len(raw) == pin['bytes'] and sha(raw) == pin['sha256'],
                        'frozen F proof input changed: ' + prefix + '/' + name)
                target = frozen / prefix / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                report['inputs'][prefix + '/' + name] = {'bytes': len(raw), 'raw_sha256': sha(raw)}
        for name in ('epoch-check.py', 'epoch-contract.c', 'inputs.json'):
            raw = (HERE / name).read_bytes()
            require(b'\r' not in raw, 'epoch source must use LF')
            (frozen / name).write_bytes(raw)
            report['inputs'][name] = {'bytes': len(raw), 'raw_sha256': sha(raw), 'sha256': sha(raw)}
        sites = admit(frozen / 'control')
        require(sha((frozen / 'control/tools.py').read_bytes()) == TOOLS, 'owned F tool primitive changed')
        oracle_path = frozen / 'reference/engines/tests/chess_oracle.py'
        require(sha(oracle_path.read_bytes()) == ORACLE, 'independent oracle pin changed')
        tools = module('epoch_F_tools', frozen / 'control/tools.py')
        oracle = module('epoch_F_oracle', oracle_path)
        command = ['cc', '-std=c11', '-O2', '-pthread', '-DDEV=0', '-DWORKERS=2', '-DTT_BITS=18',
                   '-DPRODUCTION_SOURCE="' + str(frozen / 'control/candidate.c') + '"',
                   str(frozen / 'epoch-contract.c'), '-o', str(out / 'epoch-contract')]
        report.update(source_transform=sites, compile_command=command,
                      included_production_text_unchanged=True,
                      diagnostic_interposition=['clock_gettime scheduling only, actual value unchanged',
                                                'controller actual now/deadline and worker expiration observations',
                                                'pthread_cond_wait diagnostic gate release',
                                                'pthread_cond_broadcast publication observation',
                                                'printf actual result observation'])
        save()
        result = tools.run(command, out, timeout=90)
        (out / 'compile.stdout').write_bytes(result.stdout)
        (out / 'compile.stderr').write_bytes(result.stderr)
        report.update(compile_returncode=result.returncode, tool_commands=tools.COMMANDS)
        require(result.returncode == 0, 'diagnostic compile failed; logs preserved')
        report['diagnostic_native_sha256'] = sha((out / 'epoch-contract').read_bytes())
        save()
        report['diagnostic_execution_attempts'] = 1
        save()
        result = tools.run([str(out / 'epoch-contract')], out, timeout=12)
        report['diagnostic_executions'] = 1
        (out / 'stdout.txt').write_bytes(result.stdout)
        (out / 'stderr.jsonl').write_bytes(result.stderr)
        report.update(returncode=result.returncode, tool_commands=tools.COMMANDS)
        require(result.returncode == 0, 'actual epoch diagnostic failed; logs preserved')
        require(len(result.stdout) + len(result.stderr) < 1024 * 1024, 'bounded fixture output exceeded 1 MiB')
        events = [json.loads(line) for line in result.stderr.decode().splitlines()]
        report['assertions'] = validate(events, result.stdout.decode().splitlines(), oracle)
        require(all(row['terminal'] and row['group_absent'] and row['returncode'] == 0 for row in tools.COMMANDS),
                'owned groups did not settle successfully')
        report.update(complete=True, owned_live_handles=0,
                      stdout_sha256=sha(result.stdout), stderr_sha256=sha(result.stderr))
        save()
        print(json.dumps({'complete': True, 'results': str(out / 'results.json'),
                          'sha256': sha((out / 'results.json').read_bytes())}), flush=True)
    except BaseException as error:
        if tools is not None:
            report['tool_commands'] = tools.COMMANDS
            report['diagnostic_executions'] = sum(
                row['command'] == [str(out / 'epoch-contract')] for row in tools.COMMANDS)
        report['error'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
