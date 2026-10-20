#!/usr/bin/env python3
"""Exact frozen Board-layout + phase search contract equivalence.

No raw runtime/loader/SMP/performance claim. Four test-only libc subjects use
WORKERS=1, DEV=1, TT_BITS=18, PLY=128 and fixed now(). Only the exact definition
rename and DEV COUNT hook instrument search; source bodies otherwise stay exact.
The 12 retained-table positions are the existing tiny-search corpus; only its
first startpos depth is raised 4 to 5 under the same 100000-node cap, permitting
interior depth4 reductions. Eight context/full-key/limit/stopped/PLY cases follow.
Compare actual files byte for byte
before reporting SHA metadata. No candidate/expectation is automatically admitted.
Only named Board fields/mailbox are compared across subjects; raw Board bytes are
used solely for same-object immutability within one process. Worker/Entry/game
storage remains byte-comparable and has explicit compile-time layout guards.
All 31 ordinary inputs come from this folder and are pinned before use. No
historical receipt, generated engine or mutable sibling folder is an input.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PINS_SHA = '792f510f4fd69baf72d2ab2a928baaf0ed550601e6a3d6ac06bbe5ae753e529d'
CONTROL_SHA = '87bec413c4dcbccafd1b9c48e2a4ae878caae11747caf942f36a1036e88c7fb8'
CANDIDATE_SHA = '48e0f21fee8091f1e5c5d08d606740f6ff8c56778a550af2bcfc282d655d974c'
PHASE_SHA = '0228587d1c602162ec8472c6d8f26431d4c721fee8654c9f39c51bcb6f6fd569'
CONTROL_HEADER_SHA = '43df781e2a86d353d5ec1d64fc8dc6390065d8640b6c9775eb9d7535868397c0'
CANDIDATE_HEADER_SHA = 'e19749eb3315253e04171b89b8188df7e0db6b39ec4eb495187a6e158836823f'
OLD_PY_SHA = '99c7e95554fe5c688aa355c855f376f31d5f4c7efacb24eafa758cae8555ccd2'
OLD_C_SHA = 'fc9df8fc4908e26375098b5265ab5182e9bf26fe866e7aeac553e0820464feee'
BOARD_BEFORE = b'typedef struct { int8_t b[128]; int s,c,e,k[2],half,v; uint64_t h,r; } Board;'
BOARD_AFTER = b'typedef struct { int s,c,e,k[2],half,v; uint64_t h,r; int8_t b[128]; } Board;'
SIGNATURE = b'static int search(Worker *w,const Board *p,int depth,int alpha,int beta,int ply,Move previous,Move *root){'
RENAMED = SIGNATURE.replace(b'search(', b'contract_body(', 1)
COUNT = b'#define COUNT(w,f) (++(w)->f)'
HOOK = b'#define COUNT(w,f) (++(w)->f,contract_count((w),CT_##f,(w)->f))'
RECORD = struct.Struct('<32Q')
RUNNING = set()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, detail):
    if not value:
        raise AssertionError(detail)


def lf(path):
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    require(b'\r' not in raw, 'lone CR in source ' + str(path))
    return raw


def instrument(raw):
    require(raw.count(SIGNATURE) == raw.count(COUNT) == 1, 'exact instrumentation boundaries required')
    changed = raw.replace(SIGNATURE, RENAMED).replace(COUNT, HOOK)
    require(changed.replace(RENAMED, SIGNATURE).replace(HOOK, COUNT) == raw, 'non-instrumentation body changed')
    return changed


def compare(left, right, deadline):
    require(left.stat().st_size == right.stat().st_size, 'file lengths differ: ' + left.name)
    digest, count = hashlib.sha256(), 0
    with left.open('rb') as a, right.open('rb') as b:
        while True:
            require(time.monotonic() < deadline, 'aggregate deadline during state comparison')
            x, y = a.read(1 << 20), b.read(1 << 20)
            require(x == y, 'actual file bytes differ: ' + str(left) + ' vs ' + str(right))
            if not x:
                break
            digest.update(x)
            count += len(x)
    return {'bytes': count, 'sha256': digest.hexdigest(), 'exact_byte_equality': True}


def signed(value):
    return value if value < (1 << 63) else value - (1 << 64)


def coverage(paths, deadline):
    counts = {key: 0 for key in ('calls', 'returns', 'counter_events', 'first_wide', 'qs_children',
              'late_null', 'reduced_null', 'reduced_fail_low', 'reduced_full_null_retry',
              'reduced_improvement_at_or_above_beta', 'null_to_wide_retry', 'unreduced_fail_high')}
    for path in paths:
        stack = []
        with path.open('rb') as stream:
            while True:
                require(time.monotonic() < deadline, 'aggregate deadline during trace analysis')
                raw = stream.read(RECORD.size)
                if not raw:
                    break
                require(len(raw) == RECORD.size, 'partial event record')
                e = RECORD.unpack(raw)
                if e[0] == 1:
                    require(e[2] == (stack[-1]['event'][1] if stack else 0), 'call parent differs')
                    stack.append({'event': e, 'children': []})
                    counts['calls'] += 1
                elif e[0] == 3:
                    require(stack and e[1] == stack[-1]['event'][1] and 1 <= e[4] <= 8, 'counter outside real call')
                    counts['counter_events'] += 1
                else:
                    require(e[0] == 2 and stack and e[1] == stack[-1]['event'][1], 'unbalanced return')
                    node = stack.pop()
                    parent = node['event']
                    require(e[2:10] == parent[2:10] and e[11] == parent[11] and e[15:31] == parent[15:31], 'argument/board identity changed')
                    groups = []
                    for child, score in node['children']:
                        identity = (child[8], child[15], child[16], child[7])
                        if not groups or groups[-1][0] != identity:
                            groups.append((identity, []))
                        groups[-1][1].append((child, score))
                    for index, (_, probes) in enumerate(groups):
                        first, result = probes[0]
                        depth = signed(parent[4])
                        if depth <= 0:
                            counts['qs_children'] += len(probes)
                        if index == 0 and depth > 0:
                            counts['first_wide'] += 1
                        if index and depth > 0 and signed(first[6]) - signed(first[5]) == 1:
                            counts['late_null'] += 1
                            reduced = signed(first[4]) == depth - 2
                            if reduced:
                                counts['reduced_null'] += 1
                                if -result <= -signed(first[6]):
                                    counts['reduced_fail_low'] += 1
                                if len(probes) >= 2 and signed(probes[1][0][4]) == depth - 1 and probes[1][0][5:7] == first[5:7]:
                                    counts['reduced_full_null_retry'] += 1
                                    if -result >= signed(parent[6]):
                                        counts['reduced_improvement_at_or_above_beta'] += 1
                            if len(probes) > 1 and signed(probes[-1][0][6]) - signed(probes[-1][0][5]) > 1:
                                counts['null_to_wide_retry'] += 1
                            last, score = probes[-1]
                            if signed(last[4]) == depth - 1 and signed(last[6]) - signed(last[5]) == 1 and -score >= signed(parent[6]):
                                counts['unreduced_fail_high'] += 1
                    if stack:
                        stack[-1]['children'].append((parent, signed(e[31])))
                    counts['returns'] += 1
        require(not stack, 'unterminated search trace')
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p / '.git').exists() for p in (out, *out.parents)), 'new absolute external output required')
    out.mkdir(parents=True)
    started, deadline = time.monotonic(), time.monotonic() + 180
    report = {'complete': False, 'passed': False, 'failures': [], 'cleanup': [], 'subjects': [],
              'scope': 'actual D Board-layout plus phase search deterministic single-worker DEV contract; no raw runtime/SMP/loader/performance claim',
              'test_profile': {'workers': 1, 'dev': 1, 'tt_bits': 18, 'ply': 128, 'clock': 'fixed zero'},
              'shipping_profile_exercised': False, 'source_instrumentation': ['single search definition rename', 'single DEV COUNT augmentation'],
              'board_cross_subject_comparison': 'named fields and mailbox only; no raw Board object bytes',
              'same_process_board_immutability': 'memcpy snapshot of actual object compared with same object only',
              'worker_tt_game_comparison': 'complete actual storage bytes; fixed Worker/Entry sizes and offsets compile-time guarded',
              'cases_per_subject': 20, 'subject_count': 4, 'sanitizers': False}
    phase = 'freeze'

    def terminate(signum, frame):
        raise TimeoutError('contracts SIGTERM')

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
        return record

    try:
        pins_raw = (HERE / 'pins.json').read_bytes()
        require(sha(pins_raw) == PINS_SHA, 'exact frozen31 pins required')
        pins = json.loads(pins_raw)
        require(len(pins['frozen_inputs']) == 31, 'exact31 ordinary inputs required')
        # Validate the entire immutable closure BEFORE reading any input as code,
        # recipe, source or fixture. No project module is imported by this driver.
        admitted = {}
        for name, expected in pins['frozen_inputs'].items():
            require(name.startswith('inputs/') and not Path(name).is_absolute() and '..' not in Path(name).parts, 'input path outside frozen closure')
            data = (HERE / name).read_bytes()
            require(len(data) == expected['bytes'] and sha(data) == expected['sha256'] and b'\r' not in data, 'frozen input identity differs: ' + name)
            admitted[name] = data
        require(sha(admitted['inputs/phase-contract/contracts.py']) == OLD_PY_SHA and sha(admitted['inputs/phase-contract/contracts.c.in']) == OLD_C_SHA, 'original qualified observer differs')
        names = ['pins.json', 'contracts.py', 'contracts.c.in'] + list(admitted)
        require(len(names) == len(set(names)) == 34, 'fixed proof closure differs')
        frozen = out / 'recipe'
        report['inputs'] = {}
        for name in names:
            data = admitted[name] if name in admitted else pins_raw if name == 'pins.json' else lf(HERE / name)
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            report['inputs'][name] = {'bytes': len(data), 'sha256': sha(data)}
        observer = (frozen / 'contracts.c.in').read_bytes()
        original_observer = observer
        guard_begin, guard_end = b'/* CONTRACT_LAYOUT_ADAPT_BEGIN */\n', b'/* CONTRACT_LAYOUT_ADAPT_END */\n'
        require(observer.count(guard_begin) == observer.count(guard_end) == 2, 'only two observation-precondition additions permitted')
        for _ in range(2):
            a, b = original_observer.index(guard_begin), original_observer.index(guard_end)
            require(a < b, 'observation-precondition boundaries differ')
            original_observer = original_observer[:a] + original_observer[b + len(guard_end):]
        require(original_observer == admitted['inputs/phase-contract/contracts.c.in'], 'original20case observer body changed')
        entry = frozen / 'inputs/combined/control/native'
        recipe = json.loads(admitted['inputs/combined/recipe.json'])
        require(recipe['control_file_count'] == len(recipe['control_files']) == 18, 'exact old18 control source required')
        for name, expected in recipe['control_files'].items():
            data = admitted['inputs/combined/control/' + name]
            require(len(data) == expected['bytes'] and sha(data) == expected['sha256'], 'combined recipe control differs')
        board_transform = recipe['transformations']['board']
        require(board_transform == {'file': 'native/tiny.h', 'before': BOARD_BEFORE.decode(), 'after': BOARD_AFTER.decode(), 'occurrences': 1}, 'only literal Board field reorder permitted')
        header = (entry / 'tiny.h').read_bytes()
        require(sha(header) == CONTROL_HEADER_SHA and header.count(BOARD_BEFORE) == 1 and BOARD_AFTER not in header, 'control header/Board boundary differs')
        candidate_header = header.replace(BOARD_BEFORE, BOARD_AFTER)
        require(candidate_header.count(BOARD_AFTER) == 1 and candidate_header.replace(BOARD_AFTER, BOARD_BEFORE) == header, 'non-Board header complement changed')
        require(sha(candidate_header) == CANDIDATE_HEADER_SHA == pins['candidate_header_sha256'] == recipe['candidate_sources']['native/tiny.h']['sha256'], 'candidate header identity differs')
        require(len(candidate_header) == recipe['candidate_sources']['native/tiny.h']['bytes'], 'candidate header length differs')
        control, template = (entry / 'search.c').read_bytes(), (frozen / 'inputs/combined/phase.c.in').read_bytes()
        require(sha(control) == CONTROL_SHA and sha(template) == PHASE_SHA, 'search/template identity differs')
        begin_marker, end_marker = b'        if(legal==1||depth<=0)score=-search(', b'        --w->length;'
        require(control.count(begin_marker) == control.count(end_marker) == 1, 'single phase boundaries required')
        begin, end = control.index(begin_marker), control.index(end_marker)
        require(control[begin:end].count(b'score=-search(w,&q,') == 4 and template.count(b'score=-search(w,&q,') == 1, 'four-to-one child-call replacement required')
        candidate = control[:begin] + template + control[end:]
        require(candidate[:begin] == control[:begin] and candidate[begin + len(template):] == control[end:], 'non-phase search complement changed')
        require(sha(candidate) == CANDIDATE_SHA == pins['candidate_search_sha256'] == recipe['candidate_sources']['native/search.c']['sha256'], 'candidate search identity differs')
        require(len(candidate) == recipe['candidate_sources']['native/search.c']['bytes'], 'candidate search length differs')
        # The other six of the eight ordinary native files are exactly shared.
        others = ('board.c', 'hq.c', 'hq.h', 'image.ld', 'runtime.c', 'start.S')
        report['source_preconditions'] = {'pins_sha256': PINS_SHA, 'frozen_input_count': 31,
            'control_header_sha256': sha(header), 'candidate_header_sha256': sha(candidate_header),
            'only_one_Board_declaration_reordered': True, 'inverse_header_complement_exact': True,
            'unchanged_six_native_sources': {name: sha((entry / name).read_bytes()) for name in others},
            'search_unchanged_prefix_suffix_sha256': sha(control[:begin] + control[end:]),
            'original_twenty_case_observer_sha256': OLD_C_SHA,
            'original_twenty_case_observer_runtime_body_exact': True,
            'observer_additions_only': ['normalization comment', 'compile-time representation preconditions']}
        report['body_bindings'] = {}
        for name, raw in (('control', control), ('candidate', candidate)):
            hooked = instrument(raw)
            report['body_bindings'][name] = {'exact_source_sha256': sha(raw), 'instrumented_sha256': sha(hooked),
                                            'reversed_instrumentation_exact': True, 'search_arity': 8}
        references = {}
        for mode in ('scalar', 'hq'):
            for name, raw in (('control', control), ('candidate', candidate)):
                phase = mode + '/' + name
                directory = out / mode / name
                directory.mkdir(parents=True)
                for unit in ('tiny.h', 'board.c', 'hq.h', 'hq.c'):
                    data = candidate_header if name == 'candidate' and unit == 'tiny.h' else (entry / unit).read_bytes()
                    (directory / unit).write_bytes(data)
                (directory / 'subject.c').write_bytes(instrument(raw))
                (directory / 'check.c').write_bytes((frozen / 'contracts.c.in').read_bytes())
                row = {'id': phase, 'source_sha256': sha(raw), 'header_sha256': sha((directory / 'tiny.h').read_bytes())}
                report['subjects'].append(row)
                command = ['cc', '-std=c11', '-O2', '-DWORKERS=1', '-DDEV=1', '-DTT_BITS=18', '-DPLY=128', '-DD_HQ=' + str(int(mode == 'hq')),
                           'check.c', 'board.c', 'hq.c', '-o', 'check']
                row['compile'] = run(command, directory, 'compile', 45)
                row['execute'] = run([str(directory / 'check')], directory, 'execute', 30)
                rows = [json.loads(line) for line in (directory / 'execute.stdout').read_text().splitlines()]
                require(len(rows) == 20 and [r['case'] for r in rows] == list(range(20)), 'fixed case matrix incomplete')
                row['rows'] = rows
                require(all(max(r[key] for r in rows[:12]) > 0 for key in ('history_nonzero', 'continuation_nonzero', 'correction_nonzero')), 'actual learning arrays were not exercised')
                row['coverage'] = coverage([directory / f'case-{i:02}.trace' for i in range(20)], deadline)
                must = ('first_wide', 'qs_children', 'late_null', 'reduced_null', 'reduced_full_null_retry', 'null_to_wide_retry')
                require(all(row['coverage'][key] for key in must), 'required real retry coverage missing')
                row['required_retry_coverage'] = list(must)
                row['retry_coverage_status'] = {key: 'covered' if value else 'unproven' for key, value in row['coverage'].items() if key not in ('calls', 'returns', 'counter_events')}
                if name == 'control':
                    references[mode] = (directory, rows)
                else:
                    reference, expected = references[mode]
                    require(rows == expected, 'actual result/field rows differ')
                    row['exact_files'] = []
                    for i in range(20):
                        item = {'case': i}
                        for suffix in ('trace', 'state'):
                            item[suffix] = compare(reference / f'case-{i:02}.{suffix}', directory / f'case-{i:02}.{suffix}', deadline)
                        row['exact_files'].append(item)
                    require(row['coverage'] == next(r['coverage'] for r in report['subjects'] if r['id'] == mode + '/control'), 'trace coverage differs')
                    row['exact_control_equivalence'] = True
                row['passed'] = True
        require(len(report['subjects']) == 4 and all(r.get('passed') for r in report['subjects']), 'four subjects required')
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
