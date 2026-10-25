#!/usr/bin/env python3
"""One bounded instrumented DEV0 run of unchanged C production epoch bodies.

No shipping wrapper execution, old-engine execution, fault sweep, benchmark,
sanitizer, compiler-size claim, or race-detector claim is part of this witness.
The real worker clock is scheduled by a separate diagnostic gate; its value
and the actual engine code remain unchanged. Compiler and fixture each run
inside the immutable support.run owned process group.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CANDIDATE = '15999279c5bd4690db7129bda032c6b5962acbd814236719cda40755ae31794b'
OLD = '1f0f18ffee91ecddea3cb31e7553e1d1415e25b3f759cdec4e0f375fcd0b2298'
SUPPORT = '10cffa19a48b3d604fe22dfff468af27f2e01d30d86a1e39e2b5e410cf9df30e'
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
        # C canonicalizes uncapturable EP, while oracle's replay state retains
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
            'position_reused_after_actual_pending_zero': True,
            'worker_fields_read_only_after_pending_zero': True, 'joined_created_threads': 2,
            'causal_attribution': 'diagnostic gate orders actual production wait and actual result; no shipping timing or general race proof'}


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
              'diagnostic_executions': 0, 'profile': {'DEV': 0, 'workers': 2, 'tt_bits': 18, 'ISA': 'AVX2'},
              'excluded': ['shipping image proof', 'old engine execution', 'broad fault injection',
                           'join-failure safety', 'SAN/TSAN', 'performance', 'variant sweep']}

    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')

    tools = None
    save()
    try:
        manifest = json.loads((HERE / 'inputs.json').read_text())
        for name, pin in manifest['control_files'].items():
            raw = (HERE / 'control' / name).read_bytes()
            data = raw.replace(b'\r\n', b'\n')
            require(b'\r' not in data and len(data) == pin['bytes'] and sha(data) == pin['sha256'],
                    'frozen C composition input changed: ' + name)
            target = frozen / 'control' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            report['inputs']['control/' + name] = {'bytes': len(data), 'raw_sha256': sha(raw), 'sha256': sha(data)}
        for name in ('epoch-check.py', 'epoch-contract.c', 'inputs.json'):
            raw = (HERE / name).read_bytes()
            require(b'\r' not in raw, 'epoch source must use LF')
            (frozen / name).write_bytes(raw)
            report['inputs'][name] = {'bytes': len(raw), 'raw_sha256': sha(raw), 'sha256': sha(raw)}
        candidate = (frozen / 'control/candidate.c').read_bytes()
        old = (frozen / 'control/control/engines/compact/tiny-entry-c/engine.c').read_bytes()
        require(sha(candidate) == CANDIDATE and sha(old) == OLD, 'production source literal pin differs')
        transform = module('epoch_C_transform', frozen / 'control/transform.py')
        transformed, sites = transform.transform(old)
        require(transformed == candidate, 'candidate is not unchanged seven-site production composition')
        require(sha((frozen / 'control/support.py').read_bytes()) == SUPPORT, 'owned tool support changed')
        oracle_path = frozen / 'control/control/engines/tests/chess_oracle.py'
        require(sha(oracle_path.read_bytes()) == ORACLE, 'independent oracle pin changed')
        tools = module('epoch_C_tools', frozen / 'control/support.py')
        oracle = module('epoch_C_oracle', oracle_path)
        command = ['cc', '-std=c11', '-O2', '-pthread', '-DDEV=0', '-DWORKERS=2', '-DTT_BITS=18', '-mavx2',
                   '-DPRODUCTION_SOURCE="' + str(frozen / 'control/candidate.c') + '"',
                   str(frozen / 'epoch-contract.c'), '-o', str(out / 'epoch-contract')]
        report.update(source_transform=sites, compile_command=command,
                      included_production_text_unchanged=True,
                      diagnostic_interposition=['clock_gettime scheduling only, actual value unchanged',
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
        result = tools.run([str(out / 'epoch-contract')], out, timeout=8)
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
