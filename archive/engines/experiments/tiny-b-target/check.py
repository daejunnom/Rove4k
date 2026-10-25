#!/usr/bin/env python3
"""Focused B target-generator qualification after a measured first-cost gain.

No NPS/games/portfolio matrix. Actual B contracts, bounded independent legal
children and two selected-wrapper image/active-exit sessions are kept separate.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ORACLE = Path('/home/stemxstudio/rove4k-tiny-uci-min-verify-20261020/recipe/engines/tests/chess_oracle.py')
RAW = Path('/home/stemxstudio/rove4k-tiny-uci-min-verify-20261020/recipe/engines/experiments/tiny-protocol/edges.py')
CONTRACT = Path('/home/stemxstudio/rove4k-tiny-uci-portfolio-20261020/recipe/family-B/source-recipe/engines/compact/tiny-b/contract.c')
PINS = {'oracle': 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8',
        'raw': '253cf1c7d9d1a050de8e1275f46beefcf26bb065dbb308a2421386019c02a060',
        'contract': '89375afcf1110c8c49bd389b4da8f146a02472a06bd4e05e1929d4cbc0e11e83'}
POSITIONS = (
    ('start', 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'),
    ('white-castles', 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1'),
    ('black-castles', 'r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1'),
    ('castle-origin', 'k3r3/8/8/8/8/8/8/R3K2R w KQ - 0 1'),
    ('castle-transit', 'k4r2/8/8/8/8/8/8/R3K2R w KQ - 0 1'),
    ('castle-destination', 'k5r1/8/8/8/8/8/8/R3K2R w KQ - 0 1'),
    ('white-ep', '6k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1'),
    ('black-ep', '4k3/8/8/8/3Pp3/8/8/6K1 b - d3 0 1'),
    ('white-ep-file-pin', '4r1k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1'),
    ('white-ep-rank-pin', '8/8/8/r4pPK/8/8/8/7k w - f6 0 1'),
    ('black-ep-file-pin', '4k3/8/8/8/3Pp3/8/8/4R1K1 b - d3 0 1'),
    ('black-ep-rank-pin', '7K/8/8/8/R4Ppk/8/8/8 b - f3 0 1'),
    ('white-promotions', 'r1r4k/1P6/8/8/8/8/8/7K w - - 0 1'),
    ('black-promotions', '7k/8/8/8/8/8/1p6/R1R4K b - - 0 1'),
    ('pinned-defender', '4k3/4p3/3p4/8/1B6/8/8/4R2K w - - 0 1'),
)


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


def build(source, argv, directory):
    directory.mkdir()
    (directory / 'source.c').write_bytes(source)
    process = subprocess.run(argv, input=source, cwd=directory, capture_output=True, timeout=90)
    (directory / 'compile.stdout').write_bytes(process.stdout)
    (directory / 'compile.stderr').write_bytes(process.stderr)
    require(process.returncode == 0, 'compiler failed: ' + str(directory))
    return directory / 'x'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cost', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    require(args.out.is_absolute(), 'absolute external output required')
    out = args.out.resolve()
    require(not out.exists() and not any((p / '.git').exists() for p in (out, *out.parents)), 'new outside-Git output required')
    raw_cost = args.cost.read_bytes()
    cost = json.loads(raw_cost)
    require(cost['complete'] and cost['gain'], 'a completed measured first-cost gain is required')
    target = next(item for item in cost['forms'] if item['id'] == 'target')
    combined = Path(target['readable']).read_bytes()
    require(sha(combined) == target['readable_sha256'], 'candidate readable source changed')
    require(sha(Path(target['wrapper']).read_bytes()) == target['whole_sha256'], 'candidate whole wrapper changed')
    require(sha(Path(target['native']).read_bytes()) == target['native_sha256'], 'candidate shipping image changed')
    inputs = {'cost.json': raw_cost, 'candidate.c': combined, 'check.py': Path(__file__).read_bytes(),
              'target-contract.c.in': (HERE / 'target-contract.c.in').read_bytes()}
    for name, path in (('oracle', ORACLE), ('raw', RAW), ('contract', CONTRACT)):
        data = path.read_bytes()
        require(sha(data) == PINS[name], 'qualified helper changed: ' + name)
        inputs[name] = data
    out.mkdir(parents=True)
    recipe = out / 'recipe'
    raw_path = recipe / 'engines/experiments/tiny-protocol/edges.py'
    oracle_path = recipe / 'engines/tests/chess_oracle.py'
    for path, data in ((raw_path, inputs['raw']), (oracle_path, inputs['oracle'])):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for name, data in inputs.items():
        (recipe / name).write_bytes(data)
    report = {'complete': False, 'scope': 'focused actual B geometry/SEE/singular/excluded contracts and selected-wrapper exit',
              'input_sha256': {name: sha(data) for name, data in inputs.items()}, 'contracts': [],
              'independent_legal_children': None, 'selected_wrapper_runs': [], 'performance_claim': False,
              'stack_proof': 'separate compiler-frame receipt required; old image proof not reused'}
    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    try:
        tail = inputs['contract'].decode()
        needle = 'test_bitboards();test_see();test_singular();test_extension();free(table);return 0;'
        require(tail.count(needle) == 1 and tail.count('int main(void){') == 1, 'qualified B fixture shape changed')
        tail = tail.replace(needle, 'test_target();test_see();test_singular();test_extension();free(table);return 0;')
        tail = tail.replace('int main(void){', inputs['target-contract.c.in'].decode() + '\nint main(void){')
        unit = b'#define main B_target_protocol_main\n' + combined + b'\n#undef main\n' + tail.encode()
        flags = ['cc', '-std=c11', '-pthread', '-DDEV=1', '-DWORKERS=2', '-DTT_BITS=20']
        for name, optimize in (('optimized', ['-O2']), ('asan', ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'])):
            directory = out / name
            binary = build(unit, flags + optimize + ['-x', 'c', '-', '-o', 'x'], directory)
            result = subprocess.run([str(binary)], cwd=directory, capture_output=True, timeout=60)
            (directory / 'runtime.stdout').write_bytes(result.stdout)
            (directory / 'runtime.stderr').write_bytes(result.stderr)
            report['contracts'].append({'id': name, 'compile': flags + optimize + ['-x', 'c', '-', '-o', 'x'],
                'compiled_unit_sha256': sha(unit), 'program_sha256': sha(binary.read_bytes()), 'returncode': result.returncode,
                'stdout': result.stdout.decode(errors='replace'), 'stderr': result.stderr.decode(errors='replace')})
            save()
            require(result.returncode == 0, 'actual ' + name + ' B contract failed')
        oracle = load('chess_oracle', oracle_path)
        raw = load('B_target_frozen_raw', raw_path)
        dev_command = [part.replace('-DDEV=0', '-DDEV=1') for part in cost['compiler_argv']]
        dev = build(combined, dev_command, out / 'development')
        spec = {'command': [str(dev)], 'workers': 2, 'startup_timeout': 60, 'expected_program_sha256': sha(dev.read_bytes())}
        engine = raw.RawEngine(spec, out, 'legal-children', 8)
        rows = []
        try:
            engine.initialize()
            for name, fen in POSITIONS:
                board = oracle.Board.from_fen(fen)
                engine.send(('position fen ' + fen + '\n').encode())
                moves = engine.legal(board)
                require(engine.state()['halfmove'] == board.halfmove, 'root halfmove mismatch')
                for move in moves:
                    child = board.play(move)
                    engine.send(('position fen ' + fen + ' moves ' + move + '\n').encode())
                    engine.legal(child)
                    require(engine.state()['halfmove'] == child.halfmove, 'child halfmove mismatch')
                rows.append({'id': name, 'fen': fen, 'legal_children': len(moves), 'moves': moves})
            engine.finish()
        finally:
            engine.cleanup()
        report['independent_legal_children'] = {'passed': True, 'roots': len(rows), 'children': sum(row['legal_children'] for row in rows),
            'rows': rows, 'program_sha256': sha(dev.read_bytes()), 'oracle_sha256': PINS['oracle'], 'reader_joined': True}
        save()
        for label, final in (('quit', b'quit\n'), ('EOF', None)):
            directory = out / ('wrapper-' + label)
            directory.mkdir()
            temporary = directory / 'temporary'
            temporary.mkdir()
            original_tmp = os.environ.get('TMPDIR')
            os.environ['TMPDIR'] = str(temporary)
            try:
                spec = {'command': [target['wrapper']], 'workers': 2, 'startup_timeout': 60,
                        'expected_program_sha256': target['whole_sha256']}
                engine = raw.RawEngine(spec, directory, 'runtime', 8)
            finally:
                if original_tmp is None:
                    os.environ.pop('TMPDIR', None)
                else:
                    os.environ['TMPDIR'] = original_tmp
            try:
                engine.initialize()
                require(engine.runtime_pid == engine.process.pid, 'wrapper did not fd-exec in its original PID')
                pid = engine.runtime_pid
                actual = (Path('/proc') / str(pid) / 'exe').read_bytes()
                exe = os.readlink(Path('/proc') / str(pid) / 'exe')
                require(sha(actual) == target['native_sha256'], 'actual selected-wrapper image differs')
                require(raw.family(pid) == {pid} and not list(temporary.iterdir()), 'compiler/temp resources remain')
                fds = sorted(int(path.name) for path in (Path('/proc') / str(pid) / 'fd').iterdir())
                require(fds == [0, 1, 2], 'unexpected restored-wrapper file descriptors')
                tids = sorted(engine.startup_tids)
                engine.ready(b'position startpos\n')
                engine.send(b'go wtime 300000 btime 300000 winc 0 binc 0\n')
                active = engine.active_observation()
                require(active['worker_cpu_progress_observed'], 'work not observed before active exit')
                lines = engine.finish(final)
                bestmoves = [line for line in lines if line.startswith('bestmove ')]
                legal = {str(move) for move in oracle.Board.from_fen().legal_moves()}
                require(len(bestmoves) == 1 and bestmoves[0].split()[1] in legal, 'active exit lost/duplicated legal witness')
                require(not list(temporary.iterdir()), 'owned compiler directory remains after exit')
                report['selected_wrapper_runs'].append({'id': label, 'passed': True, 'whole_sha256': target['whole_sha256'],
                    'actual_native_sha256': sha(actual), 'actual_exe': exe, 'same_pid_fd_exec': True, 'startup_tids': tids,
                    'startup_threads': len(tids), 'active': active, 'bestmove': bestmoves[0], 'file_descriptors': fds,
                    'compiler_children': [], 'temporary_files': [], 'returncode': engine.process.returncode,
                    'runtime_absent': not (Path('/proc') / str(pid)).exists(), 'readers_joined': True})
                save()
            finally:
                engine.cleanup()
        report['complete'] = True
        print(json.dumps({'complete': True, 'contracts': len(report['contracts']),
                          'independent_roots': report['independent_legal_children']['roots'],
                          'independent_children': report['independent_legal_children']['children'],
                          'actual_selected_wrapper_active_exits': len(report['selected_wrapper_runs'])}), flush=True)
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
