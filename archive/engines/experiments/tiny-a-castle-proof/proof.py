#!/usr/bin/env python3
"""Focused castle child-state/attack proof plus exact selected-wrapper lifecycle."""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MASK = (1 << 64) - 1
OLD = '71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734'
NEW = '554d0700bffeda11850f1168b90dc25228382453683b7a962d522d29044dc2ff'
COST_REPORT = '41e357d650527dcb4a8b64c027b721095bb63565f5869cb2ed3a2d19fd825ac3'
COPIED = {
    'inputs/engine.c': OLD,
    'inputs/transform.py': 'c8adf7ec78dcdfd3e1ca18ecd4e0dd00abd3e87cc1ace5755497704a0a577252',
    'inputs/castle.c.in': '2570d1008ec976f364aeec6f2dee61c23dcfd2087261e70ce46b25bfa2fc7b86',
    'selected/engines/compact/tiny-entry-a/verify.py': 'cc63a511446c35db54676356a9d885b95db7da994133147cda3e3ff1c4464b0c',
    'selected/engines/tests/verify.py': '9327ad01dd75bc17f04f400b57d5af3d6891a1abbb7f22aa6222389d50da138f',
    'selected/engines/tests/chess_oracle.py': 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def mix(value):
    value = (value + 0x9e3779b97f4a7c15) & MASK
    value = ((value ^ (value >> 30)) * 0xbf58476d1ce4e5b9) & MASK
    value = ((value ^ (value >> 27)) * 0x94d049bb133111eb) & MASK
    return value ^ (value >> 31)


def normalized(board):
    homes = {'K': (4, 7, 'K', 'R'), 'Q': (4, 0, 'K', 'R'),
             'k': (60, 63, 'k', 'r'), 'q': (60, 56, 'k', 'r')}
    board.castling = ''.join(right for right in 'KQkq' if right in board.castling and
        board.cells[homes[right][0]] == homes[right][2] and board.cells[homes[right][1]] == homes[right][3])
    board.ep = board.repetition_key()[3]
    return board


def snapshot(board, previous=None):
    cells, kings, score, key = [0] * 128, [-1, -1], 0, 0
    for sq, char in enumerate(board.cells):
        if char == '.':
            continue
        sign, kind = (1 if char.isupper() else -1), ' PNBRQK'.index(char.upper())
        q, rank, file = (sq & 7) + 16 * (sq >> 3), sq >> 3, sq & 7
        value = sign * kind
        cells[q] = value
        if kind == 6:
            kings[sign < 0] = q
        center, advance = 7 - abs(2 * file - 7) - abs(2 * rank - 7), rank if sign > 0 else 7 - rank
        score += sign * ([0, 100, 320, 330, 500, 900, 0][kind] +
            advance * (7 if kind == 1 else 2 if kind == 4 else 0) +
            center * (9 if kind == 2 else 5 if kind == 3 else -3 if kind == 6 else 2 if kind in (1, 5) else 0))
        key ^= mix(q + (value + 6) * 128)
    rights = sum(1 << index for index, right in enumerate('KQkq') if right in board.castling)
    ep = -1 if board.ep < 0 else (board.ep & 7) + 16 * (board.ep >> 3)
    key ^= mix(2048 + rights) ^ (0 if board.turn else mix(2064)) ^ (0 if ep < 0 else mix(2065 + (ep & 7)))
    path = key
    if previous is not None and board.halfmove:
        old_path = int(previous['r'], 16)
        path = (((old_path << 1) | (old_path >> 63)) & MASK) ^ key
    return {'b': cells, 's': 1 if board.turn else -1, 'c': rights, 'e': ep, 'k': kings,
            'half': board.halfmove, 'v': score, 'h': f'{key:016x}', 'r': f'{path:016x}'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cost', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out, cost = args.out.resolve(), args.cost.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)),
            'new absolute non-Git output required')
    for name, pin in COPIED.items():
        require(sha((HERE/name).read_bytes()) == pin, 'copied ordinary source changed: '+name)
    out.mkdir(parents=True)
    frozen = out/'recipe'
    shutil.copytree(HERE, frozen)
    source_files = {p.relative_to(frozen).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
                    for p in sorted(frozen.rglob('*')) if p.is_file()}
    report = {'complete': False, 'scope': 'focused castle actual-source child sets/full state/attacks plus exact wrapper lifecycle',
        'source_files': source_files, 'cost_report_sha256': COST_REPORT,
        'cost_source_set_sha256': 'cc5eb7262828e017ee577836dd7f43ac0368679cfe5752d6355c58177b618b7f',
        'private_policy_admitted': ['generated king order and possible tied search order', 'possible repeated pure origin attacks'],
        'old_DEV_or_runtime_receipt_inherited': False, 'compiles': [], 'fixture_runs': [],
        'shipping_sessions': 0, 'games': 0, 'benchmarks': 0, 'training_or_AWS_operations': 0}
    def save():
        (out/'proof.json').write_text(json.dumps(report, indent=2)+'\n')
    def run(command, directory, label, data=None, environment=None, timeout=45):
        result = subprocess.run(command, input=data, cwd=directory, env=environment, capture_output=True, timeout=timeout)
        (out/(label+'.stdout')).write_bytes(result.stdout)
        (out/(label+'.stderr')).write_bytes(result.stderr)
        (out/(label+'.command.json')).write_text(json.dumps({'argv': command, 'cwd': str(directory), 'returncode': result.returncode}, indent=2)+'\n')
        require(result.returncode == 0 and not result.stderr, label+' failed; raw stdout/stderr retained')
        return result.stdout
    save()
    try:
        original = (frozen/'inputs/engine.c').read_bytes()
        candidate, mutation = load('castle_proof_transform', frozen/'inputs/transform.py').transform(original)
        require(sha(original) == OLD and sha(candidate) == NEW, 'exact old/new readable differs')
        require((cost/'combined.c').read_bytes() == candidate and sha((cost/'results.json').read_bytes()) == COST_REPORT,
                'actual selected cost readable/report changed')
        expected = json.loads((frozen/'selected/engines/compact/tiny-entry-a/recipe.json').read_bytes())['expected']
        require(json.loads((cost/'results.json').read_bytes())['complete'], 'cost incomplete')
        for name, kind in (('main.c', 'source'), ('native', 'native'), ('wrapper', 'whole'), ('bootstrap.py', 'bootstrap')):
            raw = (cost/name).read_bytes()
            require(sha(raw) == expected[kind+'_sha256'], 'actual cost artifact changed: '+name)
            if kind != 'bootstrap':
                require(len(raw) == expected[kind+'_bytes'], 'actual cost artifact size changed: '+name)
        fen_port = original.split(b'int fen(Board *p,const char *s){', 1)[1].split(b'int verify_board(', 1)[0]
        fen_port = b'int fixture_fen(Board *p,const char *s){'+fen_port
        require(b'#if' not in fen_port and b'#endif' not in fen_port, 'FEN fixture port boundary changed')
        oracle = load('castle_proof_oracle', frozen/'selected/engines/tests/chess_oracle.py')
        fixtures = json.loads((frozen/'fixtures.json').read_bytes())
        request = ''.join(case['fen']+'\t'+(' '.join(case['moves']) or '-')+'\t'+str(case.get('search_depth', 0))+'\n' for case in fixtures).encode()
        (out/'fixture-input.txt').write_bytes(request)
        answers = {}
        for profile, flags in (('O2', ['-O2']), ('SAN', ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'])):
            for variant, source in (('old', original), ('new', candidate)):
                label = profile+'-'+variant
                directory = out/label
                directory.mkdir()
                (directory/'engine.c').write_bytes(source)
                (directory/'fixture.c').write_bytes((frozen/'fixture.c').read_bytes())
                (directory/'fen-port.inc').write_bytes(fen_port)
                command = ['cc', '-std=c11', *flags, '-pthread', '-DDEV=0', '-DWORKERS=2', '-DTT_BITS=18', 'fixture.c', '-o', 'fixture']
                run(command, directory, label+'-compile')
                report['compiles'].append({'profile': profile, 'variant': variant, 'argv': command,
                    'readable_sha256': sha(source), 'fixture_native_sha256': sha((directory/'fixture').read_bytes())})
                save()
                environment = os.environ.copy()
                environment.update(ASAN_OPTIONS='detect_leaks=1:abort_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                rows = [json.loads(line) for line in run([str(directory/'fixture')], directory, label+'-run', request, environment).splitlines()]
                require(len(rows) == len(fixtures), label+' lost fixture output')
                checked, attacks, replayed, child_count = [], 0, 0, 0
                for index, (case, row) in enumerate(zip(fixtures, rows)):
                    require(row['index'] == index, label+' fixture index changed')
                    board = normalized(oracle.Board.from_fen(case['fen']))
                    state = snapshot(board)
                    require(row['initial'] == state, case['label']+' initial full state')
                    for move, observed in zip(case['moves'], row['replay']):
                        require(observed['move'] == move, case['label']+' replay token')
                        board = normalized(board.play(move))
                        state = snapshot(board, state)
                        require(observed['state'] == state, case['label']+' replay full state '+move)
                        replayed += 1
                    require(len(row['replay']) == len(case['moves']) and row['root'] == state, case['label']+' replay/root count/state')
                    expected_attacks = [[int(board.attacked(sq, white)) for sq in range(64)] for white in (True, False)]
                    require(row['attacks'] == expected_attacks, case['label']+' attack-query mode')
                    attacks += 128
                    legal = {str(move): move for move in board.legal_moves()}
                    children = {child['move']: child['state'] for child in row['children']}
                    require(len(children) == len(row['children']) and set(children) == set(legal), case['label']+' legal child SET')
                    require(set(case.get('must_have', [])) <= set(children) and not set(case.get('must_not_have', [])) & set(children), case['label']+' targeted edge premise')
                    for name, child in children.items():
                        expected_child = normalized(board.apply(legal[name]))
                        require(child == snapshot(expected_child, state), case['label']+' full child state '+name)
                    if 'search' in row:
                        search = row['search']
                        require(search['depth'] == 2 and not search['stopped'] and search['best'] in legal, case['label']+' actual bounded search')
                    checked.append({'label': case['label'], 'legal_children': len(children), 'normalized_ep': state['e'],
                        'hash': state['h'], 'path': state['r'], 'search': row.get('search')})
                    child_count += len(children)
                answers[profile, variant] = rows
                report['fixture_runs'].append({'profile': profile, 'variant': variant, 'cases': checked,
                    'legal_child_states': child_count, 'attack_query_values': attacks, 'replay_states': replayed,
                    'full_state_fields': ['b[128]', 's', 'c', 'e', 'k[2]', 'half', 'v', 'h', 'r'],
                    'sanitizer_stderr_empty': True if profile == 'SAN' else None})
                save()
            for case, old, new in zip(fixtures, answers[profile, 'old'], answers[profile, 'new']):
                for key in ('initial', 'replay', 'root', 'attacks', 'pseudo_count'):
                    require(old[key] == new[key], case['label']+' old/new '+key)
                require({x['move']: x['state'] for x in old['children']} == {x['move']: x['state'] for x in new['children']}, case['label']+' old/new child SET/full states')
                if 'search' in old:
                    require(old['search']['score'] == new['search']['score'], case['label']+' depth2 full-window value differs')
        report['source_change'] = mutation
        report['changed_order_observations'] = [case['label'] for case, old, new in zip(fixtures, answers['O2', 'old'], answers['O2', 'new'])
            if [x['move'] for x in old['children']] != [x['move'] for x in new['children']]]
        qa = out/'qa-build'
        (qa/'native').mkdir(parents=True)
        for source, target in (('main.c', 'main.c'), ('native', 'native/x'), ('wrapper', 'x'), ('bootstrap.py', 'bootstrap.py'), ('results.json', 'build.json')):
            (qa/target).write_bytes((cost/source).read_bytes())
        (qa/'x').chmod(0o755)
        (qa/'native/x').chmod(0o755)
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
        script = decoder.decompress((qa/'x').read_bytes()[77:])
        require(script == (qa/'bootstrap.py').read_bytes() and decoder.eof and not decoder.unused_data, 'QA strict raw-copy decode')
        calls = [node for node in ast.walk(ast.parse(script)) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'communicate']
        require(len(calls) == 1 and len(calls[0].args) == 1, 'bootstrap source port changed')
        value = calls[0].args[0]
        if isinstance(value, ast.Call):
            require(isinstance(value.func, ast.Attribute) and value.func.attr == 'encode' and not value.args and not value.keywords,
                    'unexpected bootstrap source encoding')
            embedded = ast.literal_eval(value.func.value).encode()
        else:
            embedded = ast.literal_eval(value)
        require(embedded == (qa/'main.c').read_bytes(), 'QA bootstrap source is not actual selected source')
        report['QA_raw_copy'] = {'cost_artifacts_unchanged': True, 'cost_report_raw_copied_to_build_json': True,
            'bootstrap_source_exact': True, 'strict_ALONE_decode': True, 'historical_receipt_reuse': None,
            'source_sha256': expected['source_sha256'], 'native_sha256': expected['native_sha256'], 'whole_sha256': expected['whole_sha256']}
        save()
        verifier = frozen/'selected/engines/compact/tiny-entry-a/verify.py'
        run([sys.executable, '-I', '-B', str(verifier), '--build', str(qa), '--out', str(out/'selected-runtime')], out, 'selected-runtime', timeout=45)
        runtime = json.loads((out/'selected-runtime/runtime.json').read_bytes())
        require(runtime['complete'] and runtime['historical_receipt_reuse'] is None and len(runtime['fresh_sessions']) == 2,
                'fresh selected runtime receipt incomplete or historical claim inherited')
        report.update(complete=True, shipping_sessions=2, fresh_runtime=runtime,
            fixture_processes=4, final_selected_wrapper_unchanged=True, stack_proof_claim=False,
            performance_or_strength_claim=False, promotion_claim=False, all_managed_processes_terminal=True)
        save()
        print(json.dumps({'complete': True, 'out': str(out), 'fixture_processes': 4, 'shipping_sessions': 2,
                          'whole_bytes': expected['whole_bytes'], 'promotion_claim': False}))
    except BaseException as error:
        report['failure'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
