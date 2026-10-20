#!/usr/bin/env python3
"""Positive observations only for literal put-start data8 own-ELFs; separate audits.

No negative fixture, debugger, personality setting or register change is included.
This campaign cannot qualify all loader conditions; prior RIE remains unproven.
"""
import argparse
import hashlib
import importlib.util
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
PINS = {
    'build.py': 'f47e2a2d0547d3d981c8a3493a5afa24b3e9440dc0fe3303b0b688d72ddf0733',
    'recipe.json': '59f21c94551a7b08e88ee8bd1a35255a0ab794d529e3f349e7cc052a59155835',
    'helpers/c_entry_verify.py': '045550ae095457923343fd5a462b47296f3749abf621a936329863cd5c69d252',
    'helpers/rust_strict.py': '5e93b4df6d6edf8393c4d57e87da3923569733f77e10e8925ed3daf6f8d5a2e6',
    'helpers/chess_oracle.py': 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8',
}
EXPECTED = {
    'hq': {'bytes': 11565, 'sha256': '48dfbe38442f6f39dbbd7559ade48ed3a134ccb558d23ad26416c128192bcaa7',
           'payload': 'e2187bba2f6829e865a459329c8d0fc7a25a677cab039a6de0ad7476d2040268'},
    'scalar': {'bytes': 11206, 'sha256': 'cd25152381cb3c42a906edff2dae4da0a053fdc421db4b72e645f6f0c200d0da',
               'payload': '118af3d507f59fad438ee9cb964b270f81a850a0d30bd710b0486fda1f1e1ff4'},
}
RAW = set()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise AssertionError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def absent(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return True
    return False


def selected(path, form):
    data = Path(path).read_bytes()
    require(len(data) == EXPECTED[form]['bytes'] and sha(data) == EXPECTED[form]['sha256'],
            'literal complete selected own-ELF guard failed')
    return data


class Queue:
    """Use exact pinned ASCII strict accounting methods with the owned reader stream."""
    def __init__(self, owned, strict):
        self.owned, self.process = owned, owned.process
        self.strict = strict
        self.lines, self.queued, self.boundaries = [], [], []
        self.rejected_lines = []
        self.pending = self.input_pending = b''
        self.offset = self.dispatched_go = self.accepted_best = 0

    @property
    def error(self):
        return self.owned.stderr.bytes()

    def pump(self, seconds=0):
        if seconds > 0:
            time.sleep(seconds)
        raw = self.owned.stdout.bytes()
        self.pending += raw[self.offset:]
        self.offset = len(raw)
        while b'\n' in self.pending:
            line, self.pending = self.pending.split(b'\n', 1)
            text = line.decode('utf8', errors='strict')
            self.lines.append(text)
            self.queued.append(text)

    def send(self, text):
        raw = text.encode('ascii')
        self.strict.Session.admit(self, raw)
        self.owned.send(raw)

    def until(self, prefix, timeout=8):
        return self.strict.Session.until(self, prefix, timeout)

    def counts(self, expected):
        self.pump()
        return self.strict.Session.counts(self, expected)

    def no_best(self, active=False):
        self.pump()
        return self.strict.Session.no_best(self, active=active)

    def best(self, legal):
        self.pump()
        return self.strict.best(self, legal)


def inspect(pid, load, whole_sha, helper, strict, directory, initial=False):
    rows = helper.mapping(pid)
    for base, length, permissions in ((0x400000, 0x4000, 'r-x'), (0x404000, 0x1000, 'rw-'),
                                      (0x3ff000, 0x1000, '---'), (0x405000, 0x1000, '---')):
        helper.covers(rows, base, length, permissions)
    for row in rows:
        if row['end'] > 0x400000 and row['start'] < 0x405000:
            require(len(row['line'].split()) == 5, 'restored native mapping is not anonymous')
    executable = Path(f'/proc/{pid}/exe').read_bytes()
    require(sha(executable) == whole_sha, '/proc/exe whole own-ELF differs')
    with open(f'/proc/{pid}/mem', 'rb', buffering=0) as memory:
        actual = os.pread(memory.fileno(), 0x5000, 0x400000)
    require(len(actual) == 0x5000, 'incomplete restored memory read')
    require(actual[:16392] == load, 'actual sectionless header/text/rodata/gap/data differs')
    require(actual[0x4000:0x4008] == bytes.fromhex('4601400000000000'),
            'initialized memcpy pointer slot differs')
    require(struct.unpack_from('<Q', actual, 0x4000) == (0x400146,), 'GOT pointer targets differ')
    require(not any(actual[0x400c:]), 'RW page padding after OUTPUT is not zero')
    output = struct.unpack_from('<I', actual, 0x4008)[0]
    require(output == 0 if initial else output in (0, 1), 'OUTPUT initial/live atomic differs')
    maps = Path(f'/proc/{pid}/maps').read_text()
    stacks = strict.guarded(maps)
    if initial:
        require(not stacks, 'native workers exist before original entry')
    else:
        require(len(stacks) == 2, 'two guarded raw 1MiB worker stacks absent')
    directory.mkdir(parents=True, exist_ok=False)
    (directory/'restored-five-pages.bin').write_bytes(actual)
    (directory/'maps.txt').write_text(maps)
    return {'restored_five_pages_sha256': sha(actual), 'memory_snapshot': str(directory/'restored-five-pages.bin'),
            'whole_executable_sha256': sha(executable), 'sectionless_span_sha256': sha(actual[:16392]),
            'sectionless_RX4_sha256': sha(actual[:0x4000]), 'data8_sha256': sha(actual[0x4000:0x4008]),
            'initialized_memcpy_pointer': 0x400146, 'OUTPUT_address': 0x404008,
            'OUTPUT_value': output, 'RW_padding_zero_from': 0x40400c, 'RW_padding_zero': True, 'pre_entry_BSS4_and_padding_zero': initial,
            'anonymous_native_mapping': True, 'final_RX4_RW1_and_guards': True,
            'no_WX_mapping': True, 'process_stack_nonexec': True, 'raw_worker_stacks': stacks,
            'maps': rows}


def surface(pid, helper):
    tasks = helper.tasks(pid)  # also rejects task children and descriptors beyond 0/1/2
    return {'tasks': tasks, 'fd_links': {str(fd): os.readlink(f'/proc/{pid}/fd/{fd}') for fd in (0, 1, 2)},
            'task_children_absent': True, 'stdio_only': True}


def settle_cleanup(owned, tids, row):
    cleanup = owned.cleanup()
    cleanup['all_observed_tids_absent'] = all(not Path(f'/proc/{t}').exists() for t in tids)
    row['cleanup'] = cleanup
    require(owned.finished and cleanup['owned_group_absent'] and not cleanup['forced_cleanup'] and
            not cleanup['errors'] and cleanup['readers_joined'] and cleanup['all_observed_tids_absent'],
            'physical exit/readers/TIDs required intervention or remain uncertain')


def checkpoint(path, pin, load, directory, budget, helper, strict, row):
    checked_whole = path.read_bytes()
    require(sha(checked_whole) == pin, 'audit whole differs immediately before Popen')
    owned = helper.Owned(path, directory, budget)
    tids = [owned.process.pid]
    row['pid'] = owned.process.pid
    row['pre_Popen_whole_sha256'] = sha(checked_whole)
    try:
        end = time.monotonic() + budget.left(8)
        while time.monotonic() < end:
            found, status = os.waitpid(owned.process.pid, os.WNOHANG | os.WUNTRACED)
            if found:
                require(os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGSTOP,
                        'audit status was not the exact pre-entry SIGSTOP')
                break
            require(owned.process.poll() is None, 'audit exited before checkpoint')
            time.sleep(.002)
        else:
            raise TimeoutError('pre-entry audit stop deadline')
        require(sorted(helper.tasks(owned.process.pid)) == tids, 'pre-entry is not one native-free TID')
        row['pre_entry_surface'] = surface(owned.process.pid, helper)
        row['pre_entry'] = inspect(owned.process.pid, load, pin, helper, strict, directory/'preentry-memory', initial=True)
        os.kill(owned.process.pid, signal.SIGCONT)
        owned.send(b'uci\nisready\nquit\n')
        owned.close_input()
        row['settled'] = owned.finish()
        lines = owned.stdout.bytes().splitlines()
        require(lines.count(b'uciok') == 1 and lines.count(b'readyok') == 1 and
                not any(x.startswith(b'bestmove') for x in lines), 'audit original-entry protocol differs')
        row['original_entry_resumed'] = True
        row['entry_evidence'] = 'SIGCONT past pinned pre-entry CHECKPOINT; unchanged source tail calls literal 0x4000f0; original uci/isready/quit observed'
    except BaseException as error:
        row['operation_error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        settle_cleanup(owned, tids, row)
    row['passed'] = True


def legal(oracle, history):
    board = oracle.Board.from_fen()
    for name in history:
        board = board.play(name)
    return {str(m) for m in board.legal_moves()}


def production(path, form, load, directory, budget, helper, strict, oracle, shutdown, row):
    checked_whole = selected(path, form)  # literal whole guard immediately before every Popen
    owned = helper.Owned(path, directory, budget)
    tids = [owned.process.pid]
    row['pid'] = owned.process.pid
    row['pre_Popen_whole_sha256'] = sha(checked_whole)
    queue = Queue(owned, strict)
    row.update(shutdown=shutdown, passed=False, witnesses=[])
    try:
        tids = helper.stable_startup(owned)
        row['startup_tids'] = tids
        row['startup_surface'] = surface(owned.process.pid, helper)
        row['initial_memory'] = inspect(owned.process.pid, load, EXPECTED[form]['sha256'], helper, strict, directory/'startup-memory')
        queue.send('uci\nisready\n')
        queue.until('uciok')
        queue.until('readyok')
        queue.no_best()
        white = legal(oracle, [])
        black = legal(oracle, ['e2e4'])
        final = legal(oracle, ['d2d4', 'g8f6', 'c2c4'])

        def best(allowed, label):
            name = queue.best(allowed)
            row['witnesses'].append({'phase': label, 'move': name, 'legal': True})

        def active(label):
            before = helper.tasks(owned.process.pid)
            require(sorted(before) == tids, 'startup TIDs changed')
            queue.send('go infinite\n')
            observation = helper.physical_active(owned, tids, before)
            queue.no_best(active=True)
            row[label] = observation

        queue.send('position startpos\ngo wtime 300 btime 300\n')
        best(white, 'white clock')
        queue.no_best()
        queue.send('position startpos moves e2e4\ngo wtime 300 btime 300\n')
        best(black, 'black clock')
        queue.no_best()
        active('before_GO_replacement')
        queue.send('go wtime 300 btime 300\n')
        best(black, 'prior GO drained before replacement')
        best(black, 'replacement GO')
        queue.no_best()
        active('before_position_replacement')
        queue.send('position startpos moves d2d4 g8f6 c2c4\n')
        best(black, 'prior position GO drained')
        queue.no_best()
        active('before_shutdown')
        row['active_surface'] = surface(owned.process.pid, helper)
        row['active_memory'] = inspect(owned.process.pid, load, EXPECTED[form]['sha256'], helper, strict, directory/'active-memory')
        require(sorted(helper.tasks(owned.process.pid)) == tids, 'active TIDs changed')
        if shutdown == 'quit':
            queue.send('quit\n')
        else:
            strict.Session.admit(queue, eof=True)
        owned.close_input()
        row['settled'] = owned.finish()
        queue.pump()
        best(final, 'final active result before physical exit')
        queue.no_best()
        require(not queue.pending and not queue.input_pending and not queue.rejected_lines and
                queue.dispatched_go == 6 and queue.counts(6) == 6,
                'final partial output or cumulative GO/result count differs')
        require(queue.lines.count('uciok') == 1 and queue.lines.count('readyok') == 1,
                'protocol acknowledgment count differs')
        row.update(dispatched_GO=6, observed_bestmoves=6, consumed_legal_bestmoves=6, boundaries=queue.boundaries,
                   rejected_lines=queue.rejected_lines, input_partial_tail_bytes=len(queue.input_pending),
                   output_partial_tail_bytes=len(queue.pending),
                   no_helpers_or_extra_FDs_observed=True, startup_TIDs_persistent=True,
                   cancellation_causality='unproven', stdout_sha256=sha(owned.stdout.bytes()))
    except BaseException as error:
        row['operation_error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        settle_cleanup(owned, tids, row)
    row['passed'] = True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--first-cost', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    out, base = a.out.resolve(), a.first_cost.resolve()
    require(sys.platform == 'linux' and a.out.is_absolute() and not out.exists() and
            not any((p/'.git').exists() for p in (out, *out.parents)), 'new absolute external Linux output required')
    out.mkdir()
    report = {'complete': False, 'positive_observation_complete': False,
              'scope': 'positive observations only; put-start data8 CHECKPOINT and shipping identities separate',
              'class': 'tiny-rust-d-data8-sectionless-v1',
              'all_loader_conditions_verified': False, 'runtime_admission_complete': False,
              'RIE_rejection': 'unproven; negative fixture excluded and not retried',
              'personality_setting_sessions': 0, 'register_change_sessions': 0,
              'negative_fixture_sessions': 0, 'ptrace_sessions': 0, 'benchmark_sessions': 0,
              'source_sha256': {}, 'forms': [], 'compiler_commands': [],
              'old_raw_kernel_trace_deep_fault_not_relabelled': True,
              'transient_WX_exclusion': 'unchanged pinned loader source sequence; final maps observed',
              'kernel_auxv_brk_nonuse': 'own pinned native source and constructor-only body proof; no new raw syscall trace',
              'cancellation_causality': 'unproven'}

    def save():
        (out/'runtime.json').write_text(json.dumps(report, indent=2)+'\n')

    helper = None
    previous_handler = signal.signal(signal.SIGTERM, lambda _s, _f: (_ for _ in ()).throw(InterruptedError('SIGTERM')))
    try:
        for name, pin in PINS.items():
            raw = (HERE/name).read_bytes()
            require(sha(raw) == pin, 'runtime source pin differs: '+name)
        producer = module('packed_fixed_producer', HERE/'build.py')
        for name, pin in producer.INPUTS.items():
            require(sha((HERE/name).read_bytes()) == pin, 'immutable engine/packaging snapshot differs')
        for name in (*PINS, *producer.INPUTS, 'verify.py'):
            raw = (HERE/name).read_bytes()
            frozen = out/'source'/name
            frozen.parent.mkdir(parents=True, exist_ok=True)
            frozen.write_bytes(raw)
            report['source_sha256'][name] = sha(raw)
        helper = module('packed_owned_helper', out/'source/helpers/c_entry_verify.py')
        strict = module('packed_strict_helper', out/'source/helpers/rust_strict.py')
        oracle = module('packed_chess_oracle', out/'source/helpers/chess_oracle.py')
        packer = module('packed_original_packer', out/'source/packaging/packer.py')
        budget = helper.Budget(120)

        def run_tool(command):
            original_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            try:
                p = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, start_new_session=True,
                                     preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, original_mask),
                                     env={**os.environ, 'LC_ALL': 'C', 'TZ': 'UTC', 'SOURCE_DATE_EPOCH': '0'})
                RAW.add(p)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, original_mask)
            row = {'pid': p.pid, 'command': command}
            report['compiler_commands'].append(row)
            failed = True
            try:
                stdout, stderr = p.communicate(timeout=budget.left(30))
                row.update(returncode=p.returncode, stdout=stdout.decode(), stderr=stderr.decode())
                require(p.returncode == 0, 'audit loader compilation failed')
                failed = False
                return row
            finally:
                if failed:
                    try:
                        os.killpg(p.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    p.communicate(timeout=3)
                row['owned_group_absent'] = absent(p.pid)
                RAW.discard(p)
                save()

        for form in ('hq', 'scalar'):
            program = base/('put-'+form+'-first/whole/x')
            whole = selected(program, form)
            native = (base/('put-'+form+'-native/first/x')).read_bytes()
            load, static = producer.admit(native, 'put-'+form, packer)
            payload = (base/('put-'+form+'-first/whole/payload.bin')).read_bytes()
            require(sha(payload) == EXPECTED[form]['payload'], 'literal original fixed payload differs')
            row = {'form': form, 'whole_bytes': len(whole), 'whole_sha256': sha(whole),
                   'static_original_native_to_sectionless_binding': static, 'shipping': [], 'audit': {}}
            report['forms'].append(row)
            save()
            audit = packer.compile_loader(out/(form+'-audit-build'), out/'source/packaging/loader',
                                           payload, producer.LAYOUT, producer.LOADER_FLAGS, run_tool, sha, checkpoint=True)
            row['audit']['build'] = audit
            require(audit['definitions']['CHECKPOINT'] == 1, 'audit is not separately marked CHECKPOINT')
            checkpoint(Path(audit['path']), audit['sha256'], load, out/(form+'-audit-runtime'),
                       budget, helper, strict, row['audit'])
            for shutdown in ('quit', 'EOF'):
                case = {}
                row['shipping'].append(case)
                save()
                production(program, form, load, out/(form+'-'+shutdown), budget, helper, strict,
                           oracle, shutdown, case)
            save()
        require(not helper.OWNED and not RAW, 'owned handles remain registered')
        require(all(c['owned_group_absent'] for c in report['compiler_commands']), 'audit compiler group remains')
        report.update(complete=True, positive_observation_complete=True,
                      checkpoint_images_built_and_executed=2, shipping_sessions=4,
                      live_owned_handles=0, under4096=False, strength_or_scaling_claim=False)
    except BaseException as error:
        report['complete'] = False
        report['positive_observation_complete'] = False
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        report['outer_cleanup'] = []
        if RAW or helper is not None and helper.OWNED:
            report['complete'] = False
        if helper is not None:
            for owned in list(helper.OWNED):
                try:
                    report['outer_cleanup'].append(owned.cleanup())
                except BaseException as error:
                    report['outer_cleanup'].append({'pid': owned.process.pid, 'error': repr(error)})
        for p in list(RAW):
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                p.communicate(timeout=3)
            except BaseException as error:
                report['outer_cleanup'].append({'pid': p.pid, 'error': repr(error)})
            if not absent(p.pid):
                report['outer_cleanup'].append({'pid': p.pid, 'error': 'owned process group remains'})
            RAW.discard(p)
        report['live_owned_handles_after_cleanup'] = len(RAW) + (len(helper.OWNED) if helper is not None else 0)
        if report['live_owned_handles_after_cleanup'] or any(x.get('errors') or x.get('error') or
                x.get('owned_group_absent') is False for x in report['outer_cleanup']):
            report['complete'] = False
        if not report['complete']:
            report['positive_observation_complete'] = False
        save()
        signal.signal(signal.SIGTERM, previous_handler)
    print(json.dumps({'complete': report['complete'],
                      'shipping_sessions_passed': sum(bool(c.get('passed')) for r in report['forms'] for c in r['shipping']),
                      'audit_sessions_passed': sum(bool(r['audit'].get('passed')) for r in report['forms']),
                      'out': str(out)}))
    require(report['complete'], 'runtime receipt incomplete after cleanup; see runtime.json')


if __name__ == '__main__':
    main()
