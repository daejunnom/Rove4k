#!/usr/bin/env python3
"""Run explicit ownership prototypes with the unchanged maintained full F2.

This is an experiment checker, not a maintained builder or a new shipping
wrapper selector.  It reuses the existing physical owner and chess oracle.
Subreaper's byte inverse and its flag in the final chess process are not
claimed: its separate tiny-FFI fixtures cover flag restoration.  Compiler
PGID sampling observes this fixed GCC path, not every possible interleaving.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import resource
import signal
import sys
import threading
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PINS = {
    'engines/scripts/compiler_group.py': 'd859ccc460619102c27433e2476d6d5be2e8de4046e07d49f28c0944c7ff0a77',
    'engines/scripts/source_package.py': '149f616c6e8d78b52dc88ccf0dd303d37ad2bcc513e16c40a54ac1daf09d7d2f',
    'engines/compact/tiny-entry-d/verify.py': '18faa69aed5cb5dd85a054ef2e6830463f3d819f5f635d74d55550a877c81eae',
    'engines/tests/chess_oracle.py': 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8',
    'engines/experiments/compiler-ownership/fold.py': '363f31b9bfca737e15c7d31da73b1c96560ad48b48e4d477272086de13f4010e',
    'engines/experiments/compiler-ownership/subreaper.py': 'fdf64b64c6efa16098cca8137f213af5e0b833ce1f9b95a3fa0178e9fb86dbfb',
    'engines/experiments/compiler-ownership/group_phase.py': '6853f9dbfc38f56d2bdd6031767143b0108e2ed62b0c364dc3f7eadcf68d0081',
    'engines/experiments/compiler-ownership/pidfd.py': 'c21f5638392be3aaa3fd03eb9e8c79fa4c0a8044217013fd4ce8fab7d28d52be',
}
BASE = {
    'source': (7712, '546df93f9d7f6e6f8b8bdf76b8e3d5e7f9c92913f33db7bd77deec8d50bef20e'),
    'native': (18576, '3aaaacf7891a2a4660f45d75b2b3e550ab40bf01c0c1766768517719cd1e63ec'),
    'bootstrap': (9421, '4cc341ab941290a551c7396094491ecac4a90448a0554e5c37a0a787855d610b'),
    'whole': (4547, '92231fe356dc332983c2d95a5bb6e4580afac2a27fbee036fc92cac7a4666a17'),
}
CASES = {
    'fold': ('fold.py', {'variant': 'demorgan'}, 4547, 'f56716e425239bd32833001da38c81175fe09d2656529e14e5efd033404d473a'),
    'subreaper': ('subreaper.py', {'abi': 'pointer'}, 4618, 'a10c4085e67d8857dcbe410cb32a38657d5c9edf3e1952e146927a7ccad86a69'),
    'group': ('group_phase.py', {'variant': 'short'}, 4549, 'f5dea95c3a9d64b45d3282206fc5d843469483e6642d80b3eae85baf78832d87'),
    'pidfd': ('pidfd.py', {'style': 'poll'}, 4650, 'e195f6211bc0b38c730e24f3dadfeb746d39db5f3fb5463529cd4d28ac59a9b9'),
}
PENDING = None


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def interrupted(signum, frame):
    global PENDING
    PENDING = signum


def compiler_samples(pid, stopped, samples, errors):
    names = {'cc', 'cc1', 'as', 'collect2', 'ld', 'ld.bfd', 'gcc', 'gcc-13'}
    while not stopped.is_set():
        try:
            rows = {}
            for path in Path('/proc').iterdir():
                if not path.name.isdecimal():
                    continue
                try:
                    raw = (path/'stat').read_text()
                    fields = raw.rsplit(')', 1)[1].split()
                    rows[int(path.name)] = {'pid': int(path.name), 'comm': raw.split('(', 1)[1].rsplit(')', 1)[0],
                        'state': fields[0], 'ppid': int(fields[1]), 'pgid': int(fields[2]), 'sid': int(fields[3])}
                except (FileNotFoundError, ProcessLookupError, PermissionError):
                    pass
            descendants = {pid}
            while True:
                added = {n for n, r in rows.items() if r['ppid'] in descendants} - descendants
                if not added:
                    break
                descendants.update(added)
            selected = [rows[n] for n in descendants if n in rows and rows[n]['comm'] in names]
            if selected and len(samples) < 400:
                samples.append({'seconds': time.monotonic(), 'processes': sorted(selected, key=lambda r: r['pid'])})
        except BaseException as error:
            errors.append(repr(error))
            return
        stopped.wait(.003)


def image(helper, owned, expected):
    proc = Path('/proc')/str(owned.process.pid)
    link = str((proc/'exe').readlink())
    raw = (proc/'exe').read_bytes()
    require(pin(raw) == {'bytes': expected[0], 'sha256': expected[1]}, 'actual compiled full native differs')
    require(link.endswith(' (deleted)'), 'FD-executed native path is not unlinked')
    path = Path(link.removesuffix(' (deleted)'))
    require(not path.exists() and not path.parent.exists(), 'private restoration directory remains')
    tasks = helper.tasks(owned.process.pid)
    maps = helper.mapping(owned.process.pid)
    return {'native': pin(raw), 'exe': link, 'private_path_absent': True, 'tasks': tasks,
            'FDs': sorted(p.name for p in (proc/'fd').iterdir()), 'maps': maps,
            'subreaper_flag_observed_in_native': False,
            'subreaper_flag_scope': 'separate tiny-FFI fixtures; not exposed by proc status',
            'PIDFD_scope': 'only stdio remains in native; explicit close is a separate source/fixture proof'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build, out = args.build.resolve(), args.out.resolve()
    require(sys.platform == 'linux' and 1 <= len(os.sched_getaffinity(0)) <= 2, 'Linux with at most two affinity CPUs required')
    require(args.build.is_absolute() and args.out.is_absolute() and not out.exists()
            and out != REPO and REPO not in out.parents
            and not any((p/'.git').exists() for p in (out, *out.parents)), 'new external absolute output required')
    built = json.loads((build/'build.json').read_bytes())
    require(built['complete'] and built['family'] == 'F' and built['policy'] == 'full' and built['wrapper'] == 'grace', 'maintained full F2 grace baseline required')
    require(built['resources'] == {'workers': 2, 'tt_bits': 18, 'ply': 128, 'dev_default': False}, 'fixed F2 profile differs')
    raw_files = {}
    for name, key in (('main.c', 'source'), ('native/x', 'native'), ('bootstrap.py', 'bootstrap'), ('x', 'whole')):
        raw = (build/name).read_bytes()
        require((len(raw), pin(raw)['sha256']) == BASE[key], 'fixed baseline differs: ' + name)
        raw_files[key] = raw
    recipe_path = Path(built['selected_verifier']['recipe'])
    recipe_raw = recipe_path.read_bytes()
    require(pin(recipe_raw)['sha256'] == built['effective_recipe_sha256'], 'effective recipe hash differs from producer')
    recipe = json.loads(recipe_raw)
    require(recipe['expected']['whole_sha256'] == BASE['whole'][1], 'effective baseline recipe differs')
    require(recipe['compression'] == {'format': 'lzma-alone', 'filter': 'LZMA1', 'preset': 6,
        'extreme': False, 'lc': 2, 'lp': 0, 'pb': 0, 'check': 'NONE', 'mf': 'BT2',
        'dictionary_bytes': 16384, 'nice_len': 24}, 'reviewed baseline codec differs')
    out.mkdir(parents=True)
    frozen = out/'inputs'
    frozen.mkdir()
    report = {'complete': False, 'scope': 'four full F2 ownership prototypes; separate experiment, not maintained adoption',
        'baseline_build': str(build), 'baseline': BASE, 'effective_recipe': pin(recipe_raw),
        'affinity': sorted(os.sched_getaffinity(0)), 'inputs': {},
        'profiles': {}, 'counts': {'generations': 0, 'sessions': 0, 'GO': 0, 'legal_bestmoves': 0},
        'limits': {'AS': 2147483648, 'CPU_soft_hard': [120, 125], 'wall_alarm': 180},
        'claims': ['no strength, speed, scaling or tournament claim', 'compiler observations do not prove all interleavings',
                   'subreaper internal reaping differs from retained-leader model', 'original external host identity remains retained']}
    def save():
        (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    (frozen/'effective-recipe.json').write_bytes(recipe_raw)
    for relative, expected in PINS.items():
        raw = (REPO/relative).read_bytes().replace(b'\r\n', b'\n')
        require(b'\r' not in raw and pin(raw)['sha256'] == expected, 'fixed experiment/helper input differs: ' + relative)
        path = frozen/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        report['inputs'][relative] = pin(raw)
    owner = load('full_owner', frozen/'engines/scripts/compiler_group.py')
    package = load('full_package', frozen/'engines/scripts/source_package.py')
    require(package.package(raw_files['bootstrap'], recipe['compression'], prefix=package.XZ_STDIN_HEADER)
            == raw_files['whole'], 'exact maintained baseline codec/header replay differs')
    report['baseline_codec_replayed_exact'] = True
    helper = load('full_physical_owner', frozen/'engines/compact/tiny-entry-d/verify.py')
    oracle = load('full_oracle', frozen/'engines/tests/chess_oracle.py')
    class Budget(helper.Budget):
        def left(self, seconds):
            if PENDING is not None:
                raise TimeoutError('full prototype checker signal ' + str(PENDING))
            return super().left(seconds)
    resource.setrlimit(resource.RLIMIT_AS, (2147483648,)*2)
    resource.setrlimit(resource.RLIMIT_CPU, (120, 125))
    saved = {s: signal.signal(s, interrupted) for s in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM, signal.SIGXCPU)}
    signal.alarm(180)
    save()
    try:
        for name, (filename, options, expected_whole_bytes, expected_whole_sha) in CASES.items():
            module = load('full_experiment_' + name, frozen/'engines/experiments/compiler-ownership'/filename)
            target = out/name
            target.mkdir()
            first = None
            proofs = []
            for generation in (1, 2):
                bootstrap, proof = module.transform_bootstrap(raw_files['bootstrap'], owner=owner, **options)
                tree, original = ast.parse(bootstrap), ast.parse(raw_files['bootstrap'])
                require(ast.literal_eval(owner._call(tree, 'f', 'write').args[0]) == raw_files['source'],
                        'candidate literal no longer contains the exact full C source')
                for attribute, method in (('subprocess', 'Popen'), ('os', 'execve')):
                    require(ast.dump(owner._call(tree, attribute, method)) == ast.dump(owner._call(original, attribute, method)),
                            'candidate compiler or engine exec AST differs')
                if hasattr(module, 'restore_bootstrap'):
                    require(module.restore_bootstrap(bootstrap, proof) == raw_files['bootstrap'], 'candidate byte inverse differs')
                whole = package.package(bootstrap, recipe['compression'], prefix=package.XZ_STDIN_HEADER)
                decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                require(decoder.decompress(whole[len(package.XZ_STDIN_HEADER):]) == bootstrap and decoder.eof and not decoder.unused_data,
                        'candidate codec inverse differs')
                require((len(whole), pin(whole)['sha256']) == (expected_whole_bytes, expected_whole_sha),
                        'independently reviewed candidate whole identity differs')
                require(first is None or first == (bootstrap, whole), 'independent candidate generation differs')
                first = (bootstrap, whole)
                proofs.append(proof)
                report['counts']['generations'] += 1
            (target/'bootstrap.py').write_bytes(first[0])
            (target/'x').write_bytes(first[1])
            (target/'x').chmod(0o755)
            (target/'source-proof.json').write_text(json.dumps(proofs, indent=2)+'\n')
            row = {'whole': pin(first[1]), 'bootstrap': pin(first[0]), 'source': pin(raw_files['source']),
                   'byte_inverse_available': hasattr(module, 'restore_bootstrap'), 'sessions': []}
            report['profiles'][name] = row
            save()
            for eof in (False, True):
                directory = target/('EOF' if eof else 'quit')
                directory.mkdir()
                owned = helper.Owned(target/'x', directory, Budget(65))
                stopped = threading.Event()
                samples, sample_errors = [], []
                observer = threading.Thread(target=compiler_samples, args=(owned.process.pid, stopped, samples, sample_errors))
                observer.start()
                session = {'termination': 'EOF' if eof else 'quit', 'pid': owned.process.pid, 'completed': []}
                row['sessions'].append(session)
                try:
                    original_stdin = os.fstat(owned.process.stdin.fileno())
                    owned.send(b'uci\nisready\n')
                    owned.wait_line(b'uciok')
                    owned.wait_line(b'readyok')
                    stopped.set()
                    observer.join(timeout=3)
                    require(not observer.is_alive() and not sample_errors, 'compiler observation reader did not settle')
                    tids = helper.stable_startup(owned)
                    session['startup'] = image(helper, owned, BASE['native'])
                    native_stdin = os.stat(Path('/proc')/str(owned.process.pid)/'fd/0')
                    require((original_stdin.st_dev, original_stdin.st_ino) == (native_stdin.st_dev, native_stdin.st_ino), 'UCI input pipe replaced')
                    observed_groups = {r['pgid'] for s in samples for r in s['processes']}
                    if samples:
                        require(len(observed_groups) == 1 and owned.process.pid not in observed_groups
                                and all(r['sid'] == r['pgid'] for s in samples for r in s['processes']),
                                'observed compiler did not retain its separate private session/group')
                    session['compiler_observation'] = {'samples': samples,
                        'observed': bool(samples), 'fixed_PGID_observed': True if samples else None,
                        'scope': 'sampled known GCC child path only; no ptrace, reaping or universal compiler containment'}
                    board = oracle.Board.from_fen()
                    for history, command in (([], b'go wtime 0 btime 0\n'), (['e2e4'], b'go wtime 0 btime 0\n'), ([], b'go\n')):
                        board = oracle.Board.from_fen()
                        for move in history:
                            board = board.play(move)
                        owned.send(('position startpos' + (' moves ' + ' '.join(history) if history else '') + '\n').encode())
                        owned.send(command)
                        report['counts']['GO'] += 1
                        owned.wait_best(len(session['completed'])+1)
                        moves = [line.split()[1].decode() for line in owned.stdout.bytes().splitlines() if line.startswith(b'bestmove ')]
                        require(len(moves) == len(session['completed'])+1 and moves[-1] in {str(m) for m in board.legal_moves()}, 'result count/legality differs')
                        session['completed'].append(moves[-1])
                        report['counts']['legal_bestmoves'] += 1
                    board = oracle.Board.from_fen()
                    owned.send(b'position startpos\n')
                    before = helper.tasks(owned.process.pid)
                    owned.send(b'go wtime 60000 btime 60000\n')
                    report['counts']['GO'] += 1
                    session['activity'] = helper.physical_active(owned, tids, before)
                    if eof:
                        owned.close_input()
                    else:
                        owned.send(b'quit\n')
                    owned.wait_best(4)
                    moves = [line.split()[1].decode() for line in owned.stdout.bytes().splitlines() if line.startswith(b'bestmove ')]
                    require(len(moves) == 4 and moves[-1] in {str(m) for m in board.legal_moves()}, 'closing result lost/duplicated/illegal')
                    session['completed'].append(moves[-1])
                    report['counts']['legal_bestmoves'] += 1
                    session['settled'] = owned.finish()
                    require(moves == [line.split()[1].decode() for line in owned.stdout.bytes().splitlines() if line.startswith(b'bestmove ')], 'output changed before physical EOF')
                    require(all(not (Path('/proc')/str(tid)).exists() for tid in tids), 'observed engine TID remains after reap')
                    session['complete'] = True
                    report['counts']['sessions'] += 1
                finally:
                    stopped.set()
                    observer.join(timeout=3)
                    session['observer_joined'] = not observer.is_alive()
                    session['cleanup'] = owned.cleanup()
                    save()
                require(not session['cleanup']['forced_cleanup'] and not session['cleanup']['errors'], 'prototype runtime required host intervention')
        require(not helper.OWNED, 'external owned handle remains')
        for relative, expected in PINS.items():
            require(pin((REPO/relative).read_bytes().replace(b'\r\n', b'\n'))['sha256'] == expected, 'source changed during full experiment')
        require(recipe_path.read_bytes() == recipe_raw, 'effective recipe changed during full experiment')
        report['complete'] = True
        report['source_unchanged'] = True
        save()
        print(json.dumps({'complete': True, 'out': str(out), 'counts': report['counts']}), flush=True)
    except BaseException as error:
        report['error'] = repr(error)
        save()
        raise
    finally:
        signal.alarm(0)
        for owned in tuple(helper.OWNED):
            owned.cleanup()
        for sig, old in saved.items():
            signal.signal(sig, old)


if __name__ == '__main__':
    main()
