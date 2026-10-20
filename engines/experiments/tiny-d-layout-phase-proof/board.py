#!/usr/bin/env python3
"""One bounded actual-D Board layout contract, independent of search/runtime.

Four libc test subjects differ only in the pinned Board declaration and HQ
selection. Exact board.c/hq.c bodies run actual start/FEN/gen/make. Named fields,
all 128 mailbox cells, legal order and attacks are compared exactly across all
subjects. The independent pinned 64-square oracle supplies legal sets and
transitions; full HCE, repetition keys and ordered reversible context are
recomputed mathematically from that independent state. No raw ELF, SMP, search,
performance, sanitizer or broad game claim is made.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PINS_SHA = '792f510f4fd69baf72d2ab2a928baaf0ed550601e6a3d6ac06bbe5ae753e529d'
CONTROL_HEADER_SHA = '43df781e2a86d353d5ec1d64fc8dc6390065d8640b6c9775eb9d7535868397c0'
CANDIDATE_HEADER_SHA = 'e19749eb3315253e04171b89b8188df7e0db6b39ec4eb495187a6e158836823f'
ORACLE_SHA = 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8'
OLD = b'typedef struct { int8_t b[128]; int s,c,e,k[2],half,v; uint64_t h,r; } Board;'
NEW = b'typedef struct { int s,c,e,k[2],half,v; uint64_t h,r; int8_t b[128]; } Board;'
MASK = (1 << 64) - 1
RUNNING = set()
# Fixed once, before compilation. Depth two covers ordinary grandchildren and
# published perft totals; depth one records every focused special transition.
MATRIX = (
    ('start', 'start', 2, (), 400),
    ('kiwipete', 'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1', 2, (), 2039),
    ('rook-ep', '8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1', 2, (), 191),
    ('legal-ep', '4k3/8/8/3pP3/8/8/8/4K3 w - d6 7 2', 1, (), None),
    ('pinned-ep', 'k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', 1, (), None),
    ('horizontal-ep-discovery', '4k3/8/8/r4pPK/8/8/8/8 w - f6 0 1', 1, (), None),
    ('uncapturable-ep', '4k3/8/8/3p4/8/8/8/4K3 w - d6 0 1', 1, (), None),
    ('white-promotions', '1r2k3/P7/8/8/8/8/8/4K3 w - - 17 1', 1, (), None),
    ('black-promotions', '4k3/8/8/8/8/8/p7/1R2K3 b - - 17 1', 1, (), None),
    ('white-castles', 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 12 1', 1, (), None),
    ('black-castles', 'r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 12 1', 1, (), None),
    ('white-attacked-transit', 'r3k2r/8/8/8/8/5r2/8/R3K2R w KQkq - 0 1', 1, (), None),
    ('white-attacked-destination', 'r3k2r/8/8/8/8/6r1/8/R3K2R w KQkq - 0 1', 1, (), None),
    ('black-attacked-transit', 'r3k2r/8/5R2/8/8/8/8/R3K2R b KQkq - 0 1', 1, (), None),
    ('black-attacked-destination', 'r3k2r/8/6R1/8/8/8/8/R3K2R b KQkq - 0 1', 1, (), None),
    ('rook-capture-rights', 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1', 1, ('a1a8',), None),
    ('absent-rook-rights', '4k3/8/8/8/8/8/8/4K3 w KQkq - 0 1', 1, (), None),
    ('half99', '4k3/8/8/8/8/8/8/R3K3 w - - 99 1', 1, (), None),
    ('king-knight-cycle', 'start', 1, ('g1f3', 'g8f6', 'f3g1', 'f6g8'), None),
    ('queen-knight-cycle', 'start', 1, ('b1c3', 'b8c6', 'c3b1', 'c6b8'), None),
    ('irreversible-after-cycle', 'start', 1, ('g1f3', 'g8f6', 'f3g1', 'f6g8', 'e2e4'), None),
    ('created-legal-ep', '4k3/3p4/8/4P3/8/8/8/4K3 b - - 9 1', 1, ('d7d5',), None),
    ('both-castles-history', 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 5 1', 1, ('e1g1', 'e8c8'), None),
    ('ordinary-capture-history', '4k3/8/8/8/8/8/r7/R3K3 w - - 22 1', 1, ('a1a2',), None),
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, detail):
    if not value:
        raise AssertionError(detail)


def read_lf(path):
    raw = path.read_bytes()
    require(b'\r' not in raw, 'frozen input must be exact LF: ' + str(path))
    return raw


def mix64(number):
    """Unsigned splitmix permutation, with modulo 2**64 after each product."""
    number = (number + 0x9e3779b97f4a7c15) & MASK
    number = ((number ^ (number >> 30)) * 0xbf58476d1ce4e5b9) & MASK
    number = ((number ^ (number >> 27)) * 0x94d049bb133111eb) & MASK
    return number ^ (number >> 31)


def canonical(board):
    # FEN rights are sanitized by actual admission. Do this independently from
    # the oracle's 64-square pieces; legal EP comes from its complete legal set.
    homes = {'K': (4, 7, 'K', 'R'), 'Q': (4, 0, 'K', 'R'),
             'k': (60, 63, 'k', 'r'), 'q': (60, 56, 'k', 'r')}
    board.castling = ''.join(right for right in 'KQkq' if right in board.castling and
                             all(board.cells[q] == piece for q, piece in
                                 zip(homes[right][:2], homes[right][2:])))
    board.ep = board.repetition_key()[3]
    return board


def fields(board, context):
    """Full recomputation from independent 64-square state, no engine calls."""
    pieces = '.PNBRQK'
    cells = [0] * 128
    kings, evaluation = [-1, -1], 0
    for square, piece in enumerate(board.cells):
        if piece == '.':
            continue
        magnitude = pieces.index(piece.upper())
        side = 1 if piece.isupper() else -1
        file, rank = square % 8, square // 8
        mailbox = file + 16 * rank
        cells[mailbox] = side * magnitude
        if magnitude == 6:
            kings[side < 0] = mailbox
        advance = rank if side > 0 else 7 - rank
        center = 7 - abs(2 * file - 7) - abs(2 * rank - 7)
        coefficient = {1: 2, 2: 9, 3: 5, 4: 0, 5: 2, 6: -3}[magnitude]
        material = (0, 100, 320, 330, 500, 900, 0)[magnitude]
        evaluation += side * (material + advance * (7 if magnitude == 1 else 2 if magnitude == 4 else 0)
                              + center * coefficient)
    rights = sum(1 << index for index, right in enumerate('KQkq') if right in board.castling)
    ep = -1 if board.ep < 0 else board.ep % 8 + 16 * (board.ep // 8)
    key = mix64(2048 + rights) ^ (0 if board.turn else mix64(2064))
    if ep >= 0:
        key ^= mix64(2065 + ep % 8)
    for mailbox, piece in enumerate(cells):
        if piece:
            key ^= mix64(mailbox + (piece + 6) * 128)
    attacks = [sum(1 << square for square in range(64) if board.attacked(square, side))
               for side in (True, False)]
    return {'s': 1 if board.turn else -1, 'c': rights, 'e': ep, 'half': board.halfmove,
            'v': evaluation, 'k': kings, 'h': f'{key:016x}', 'r': f'{key if context is None else context:016x}',
            'attacks': [f'{value:016x}' for value in attacks], 'b': cells}


def transition(board, context, move):
    child = canonical(board.apply(move))
    key = int(fields(child, None)['h'], 16)
    rotated = ((context << 1) | (context >> 63)) & MASK
    return child, rotated ^ key if child.halfmove else key


def expectations(oracle, deadline):
    expected, summaries, roots = {}, [], []
    for index, (label, fen, depth, history, known) in enumerate(MATRIX):
        board = canonical(oracle.Board.from_fen(oracle.START if fen == 'start' else fen))
        context = int(fields(board, None)['h'], 16)
        for uci in history:
            matches = [move for move in board.legal_moves() if str(move) == uci]
            require(len(matches) == 1, 'fixed oracle history illegal: ' + label + '/' + uci)
            board, context = transition(board, context, matches[0])
        roots.append(fields(board, context))
        nodes = 0

        def visit(current, digest, path, remaining):
            nonlocal nodes
            require(time.monotonic() < deadline, 'aggregate deadline in independent oracle')
            nodes += 1
            require(len(expected) < 6000, 'fixed oracle node budget')
            moves = list(current.legal_moves())
            row = fields(current, digest)
            row.update(kind='node', case=index, path=path, remaining=remaining, legal={str(move) for move in moves})
            expected[index, path] = row
            if not remaining:
                return 1
            leaves = 0
            for move in moves:
                child, next_digest = transition(current, digest, move)
                leaves += visit(child, next_digest, (path + ' ' + str(move)).strip(), remaining - 1)
            return leaves

        leaves = visit(board, context, '', depth)
        require(known is None or leaves == known, 'published fixed perft differs: ' + label)
        summaries.append({'kind': 'summary', 'case': index, 'nodes': nodes, 'leaves': leaves,
                          'initialization_and_reinitialization': True})
    require(len(MATRIX) == 24, 'fixed case matrix differs')
    # Positive and negative fixture preconditions are explicit; missing special
    # moves cannot silently turn a purported transition test into an empty one.
    legal = lambda i: expected[i, '']['legal']
    require('e5d6' in legal(3) and all(roots[i]['e'] == -1 for i in (4, 5, 6)), 'EP fixture coverage')
    require('e5d6' not in legal(4) and 'g5f6' not in legal(5), 'illegal EP fixture coverage')
    for index, prefixes in ((7, ('a7a8', 'a7b8')), (8, ('a2a1', 'a2b1'))):
        require(all(prefix + promotion in legal(index) for prefix in prefixes for promotion in 'nbrq'), 'all promotions fixture coverage')
    require({'e1g1', 'e1c1'} <= legal(9) and {'e8g8', 'e8c8'} <= legal(10), 'both castles fixture coverage')
    require(all('e1g1' not in legal(i) and 'e1c1' in legal(i) for i in (11, 12)), 'white attacked castle fixture coverage')
    require(all('e8g8' not in legal(i) and 'e8c8' in legal(i) for i in (13, 14)), 'black attacked castle fixture coverage')
    require(roots[15]['c'] == 5 and roots[16]['c'] == 0, 'castling rights fixture coverage')
    require(roots[18]['h'] == roots[19]['h'] and roots[18]['half'] == roots[19]['half'] == 4
            and roots[18]['r'] != roots[19]['r'], 'distinct ordered reversible context fixture coverage')
    require(roots[20]['h'] == roots[20]['r'] and roots[21]['e'] == 83
            and roots[23]['half'] == 0 and roots[23]['h'] == roots[23]['r'], 'irreversible reset and created EP coverage')
    return expected, summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(os.name == 'posix', 'Linux test profile required')
    require(args.out.is_absolute() and not out.exists() and not any((p / '.git').exists() for p in (out, *out.parents)), 'new absolute external output required')
    out.mkdir(parents=True)
    started, deadline = time.monotonic(), time.monotonic() + 180
    report = {'complete': False, 'passed': False, 'failures': [], 'cleanup': [], 'subjects': [],
              'scope': 'actual D Board named-state/transition contract; no search/raw runtime/SMP/performance claim',
              'test_profile': {'workers': 1, 'dev': 1, 'tt_bits': 18, 'ply': 128, 'optimization': 'O2'},
              'shipping_profile_exercised': False, 'subject_count': 4, 'cases_per_subject': 24,
              'source_instrumentation': [], 'normalized_all_128_mailbox_cells': True, 'sanitizers': False}
    phase = 'freeze'

    def terminate(signum, frame):
        raise TimeoutError('board SIGTERM')

    previous_term = signal.signal(signal.SIGTERM, terminate)

    def run(command, directory, label, seconds):
        record = {'command': command, 'directory': str(directory), 'label': label}
        process, output, errors = None, directory / (label + '.stdout'), directory / (label + '.stderr')
        begin = time.monotonic()
        try:
            with output.open('wb') as stdout, errors.open('wb') as stderr:
                inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
                try:
                    process = subprocess.Popen(command, cwd=directory, stdout=stdout, stderr=stderr, start_new_session=True,
                                               preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, inherited))
                    RUNNING.add(process)
                finally:
                    signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
                remaining = min(seconds, deadline - time.monotonic())
                require(remaining > 0, 'aggregate deadline')
                process.wait(timeout=remaining)
                require(process.returncode == 0, label + ' exited nonzero')
        except BaseException as error:
            record['failure'] = {'type': type(error).__name__, 'detail': str(error)}
            raise
        finally:
            cleanup_errors = []
            if process is not None:
                try:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                        record['forced_cleanup'] = True
                    except ProcessLookupError:
                        record['forced_cleanup'] = False
                    process.wait(timeout=3)
                    RUNNING.discard(process)
                    record['returncode'] = process.returncode
                except BaseException as error:
                    cleanup_errors.append({'type': type(error).__name__, 'detail': str(error)})
            record.update(elapsed_seconds=time.monotonic() - begin, cleanup_errors=cleanup_errors)
            for key, path in (('stdout', output), ('stderr', errors)):
                if path.exists():
                    record[key] = {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
            (directory / (label + '.json')).write_text(json.dumps(record, indent=2) + '\n')
        require(not cleanup_errors and not record.get('forced_cleanup'), 'command cleanup was forced or incomplete')
        require(output.stat().st_size <= 32 * 1024 * 1024 and errors.stat().st_size <= 1024 * 1024, 'bounded command output exceeded')
        return record

    try:
        pins_raw = read_lf(HERE / 'pins.json')
        require(sha(pins_raw) == PINS_SHA, 'exact reviewed pins required')
        pins = json.loads(pins_raw)
        require(len(pins['frozen_inputs']) == 31, 'fixed 31-input closure differs')
        names = list(pins['frozen_inputs']) + ['pins.json', 'board.py', 'board.c.in']
        require(len(names) == len(set(names)) == 34, 'board producer closure differs')
        frozen = out / 'recipe'
        report['inputs'] = {}
        for name in names:
            data = read_lf(HERE / name)
            if name in pins['frozen_inputs']:
                require({'bytes': len(data), 'sha256': sha(data)} == pins['frozen_inputs'][name], 'frozen source identity differs: ' + name)
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            report['inputs'][name] = {'bytes': len(data), 'sha256': sha(data)}
        entry = frozen / 'inputs/combined/control/native'
        control = (entry / 'tiny.h').read_bytes()
        require(sha(control) == CONTROL_HEADER_SHA and control.count(OLD) == 1, 'exact original header required')
        candidate = control.replace(OLD, NEW)
        require(sha(candidate) == CANDIDATE_HEADER_SHA and candidate.replace(NEW, OLD) == control, 'exact single declaration candidate required')
        oracle_path = frozen / 'inputs/helpers/chess_oracle.py'
        require(sha(oracle_path.read_bytes()) == ORACLE_SHA, 'independent oracle identity differs')
        spec = importlib.util.spec_from_file_location('d_board_independent_oracle', oracle_path)
        oracle = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = oracle
        spec.loader.exec_module(oracle)
        phase = 'independent-expectations'
        expected, summaries = expectations(oracle, deadline)
        requests = ''.join(f'{i}|{depth}|{fen}|{" ".join(history) or "-"}\n'
                           for i, (_, fen, depth, history, _) in enumerate(MATRIX)).encode()
        (frozen / 'requests.txt').write_bytes(requests)
        report['matrix'] = [{'case': i, 'label': label, 'input': fen, 'depth': depth, 'history': list(history),
                             'published_perft': known, 'expected_nodes': summaries[i]['nodes'], 'expected_leaves': summaries[i]['leaves']}
                            for i, (label, fen, depth, history, known) in enumerate(MATRIX)]
        report['expected_nodes_per_subject'] = len(expected)
        report['request_sha256'] = sha(requests)
        reference = None
        for mode in ('scalar', 'hq'):
            for name, header in (('control', control), ('candidate', candidate)):
                phase = mode + '/' + name
                directory = out / mode / name
                directory.mkdir(parents=True)
                for unit in ('board.c', 'hq.h', 'hq.c'):
                    (directory / unit).write_bytes((entry / unit).read_bytes())
                (directory / 'tiny.h').write_bytes(header)
                (directory / 'check.c').write_bytes((frozen / 'board.c.in').read_bytes())
                row = {'id': phase, 'header_sha256': sha(header), 'exact_board_body_sha256': sha((entry / 'board.c').read_bytes())}
                report['subjects'].append(row)
                command = ['cc', '-std=c11', '-O2', '-DWORKERS=1', '-DDEV=1', '-DTT_BITS=18', '-DPLY=128', '-DD_HQ=' + str(int(mode == 'hq')),
                           'check.c', 'board.c', 'hq.c', '-o', 'check']
                row['compile'] = run(command, directory, 'compile', 45)
                row['execute'] = run([str(directory / 'check'), str(frozen / 'requests.txt')], directory, 'execute', 30)
                output = (directory / 'execute.stdout').read_bytes()
                seen, actual_summaries = set(), []
                for line in output.splitlines():
                    require(time.monotonic() < deadline, 'aggregate deadline during comparison')
                    actual = json.loads(line)
                    if actual['kind'] == 'summary':
                        actual_summaries.append(actual)
                        continue
                    identity = actual['case'], actual['path']
                    require(identity in expected and identity not in seen, 'unexpected or duplicate actual node')
                    seen.add(identity)
                    wanted = expected[identity]
                    legal = actual.pop('legal')
                    require(len(legal) == len(set(legal)) and set(legal) == wanted['legal'], 'independent legal set differs: ' + str(identity))
                    require(actual == {key: value for key, value in wanted.items() if key != 'legal'}, 'independent named state/attacks differ: ' + str(identity))
                require(seen == set(expected) and actual_summaries == summaries, 'fixed actual matrix incomplete or perft differs')
                if reference is None:
                    reference = output
                else:
                    require(output == reference, 'actual normalized state/order differs across control/candidate/scalar/HQ')
                row.update(passed=True, independently_checked_nodes=len(seen), exact_normalized_state_and_order=True,
                           published_perft_passed=[400, 2039, 191], output_bytes=len(output), output_sha256=sha(output))
        require(len(report['subjects']) == 4 and all(row.get('passed') for row in report['subjects']), 'four subjects required')
        report['complete'] = report['passed'] = True
    except BaseException as error:
        report['complete'] = report['passed'] = False
        report['failures'].append({'phase': phase, 'type': type(error).__name__, 'detail': str(error)})
    finally:
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        try:
            for process in list(RUNNING):
                item = {'pid': process.pid}
                try:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=3)
                    item['returncode'] = process.returncode
                except BaseException as error:
                    item['failure'] = {'type': type(error).__name__, 'detail': str(error)}
                report['cleanup'].append(item)
                report['complete'] = report['passed'] = False
            report['elapsed_seconds'] = time.monotonic() - started
            (out / 'results.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        finally:
            signal.signal(signal.SIGTERM, previous_term)
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
    print(json.dumps({'complete': report['complete'], 'passed': report['passed'], 'subjects': len(report['subjects']), 'out': str(out), 'failures': report['failures']}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
