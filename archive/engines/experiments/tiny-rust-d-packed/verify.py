#!/usr/bin/env python3
"""Observe only the literal selected Rust D own-ELFs; audits are separate files."""

if __name__ == "__main__":
    raise SystemExit("Rove4k Rust engine paths are retired; use C A-F")

import argparse
import ctypes
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
    'build.py': 'e842bb938b5a6ff9b95776407b93fa1a91cfe061f522e395398fd8833b215316',
    'recipe.json': '734922d1b2adafc2b9bbc5ebdb207cacd2e547afc3f3ce54db24a2276e1382dc',
    'helpers/c_entry_verify.py': '045550ae095457923343fd5a462b47296f3749abf621a936329863cd5c69d252',
    'helpers/rust_strict.py': 'd43b9d4b419ec1b778638bc741376b9f4122a5def780eb929cbba3af170ac2a3',
    'helpers/chess_oracle.py': 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8',
}
EXPECTED = {
    'hq': {'bytes': 12554, 'sha256': 'ec6d1b5dae6915a44affcfe319d72171a4115389185b83fe50f7bfb93dce1318',
           'payload': '9903b561c31d76f0e424caa6623e5bb839272b35e992ca0c8f9b8accd8b02715'},
    'scalar': {'bytes': 12194, 'sha256': '78137e6ea89a38ac1cb3e83edaec65d420a05fe3e9d1f3a340d23d76046489b7',
               'payload': 'a3b3865ce25267bb5fe5caf4335ae9f51e7fd57e07f405bea7635ab2b3864a3d'},
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
    """Use exact old strict accounting methods with the owned reader stream."""
    def __init__(self, owned, strict):
        self.owned, self.process = owned, owned.process
        self.strict = strict
        self.lines, self.queued, self.boundaries = [], [], []
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


def inspect(pid, load, whole_sha, helper, strict, initial=False):
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
    require(actual[:16400] == load, 'actual sectionless header/text/rodata/gap/data differs')
    require(actual[0x4000:0x4010] == bytes.fromhex('46014000000000008801400000000000'),
            'initialized memcpy/memcmp pointer slots differ')
    require(struct.unpack_from('<QQ', actual, 0x4000) == (0x400146, 0x400188), 'GOT pointer targets differ')
    require(not any(actual[0x4014:]), 'RW page padding after OUTPUT is not zero')
    output = struct.unpack_from('<I', actual, 0x4010)[0]
    require(output == 0 if initial else output in (0, 1), 'OUTPUT initial/live atomic differs')
    maps = Path(f'/proc/{pid}/maps').read_text()
    stacks = strict.guarded(maps)
    if initial:
        require(not stacks, 'native workers exist before original entry')
    else:
        require(len(stacks) == 2, 'two guarded raw 1MiB worker stacks absent')
    return {'whole_executable_sha256': sha(executable), 'sectionless_span_sha256': sha(actual[:16400]),
            'sectionless_RX4_sha256': sha(actual[:0x4000]), 'data16_sha256': sha(actual[0x4000:0x4010]),
            'OUTPUT_value': output, 'RW_padding_zero': True, 'pre_entry_full_RW_tail_zero': initial,
            'anonymous_native_mapping': True, 'final_RX4_RW1_and_guards': True,
            'no_WX_mapping': True, 'process_stack_nonexec': True, 'raw_worker_stacks': stacks,
            'maps': rows}


def settle_cleanup(owned, tids, row):
    cleanup = owned.cleanup()
    cleanup['all_observed_tids_absent'] = all(not Path(f'/proc/{t}').exists() for t in tids)
    row['cleanup'] = cleanup
    require(owned.finished and cleanup['owned_group_absent'] and not cleanup['forced_cleanup'] and
            not cleanup['errors'] and cleanup['readers_joined'] and cleanup['all_observed_tids_absent'],
            'physical exit/readers/TIDs required intervention or remain uncertain')


def checkpoint(path, pin, load, directory, budget, helper, strict, row):
    require(sha(path.read_bytes()) == pin, 'audit whole differs immediately before Popen')
    owned = helper.Owned(path, directory, budget)
    tids = [owned.process.pid]
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
        row['pre_entry'] = inspect(owned.process.pid, load, pin, helper, strict, initial=True)
        os.kill(owned.process.pid, signal.SIGCONT)
        owned.send(b'uci\nisready\nquit\n')
        owned.close_input()
        row['settled'] = owned.finish()
        lines = owned.stdout.bytes().splitlines()
        require(lines.count(b'uciok') == 1 and lines.count(b'readyok') == 1 and
                not any(x.startswith(b'bestmove') for x in lines), 'audit original-entry protocol differs')
        row['original_entry_resumed'] = True
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
    selected(path, form)  # literal whole guard immediately before every Popen
    owned = helper.Owned(path, directory, budget)
    tids = [owned.process.pid]
    queue = Queue(owned, strict)
    row.update(shutdown=shutdown, passed=False, witnesses=[])
    try:
        tids = helper.stable_startup(owned)
        row['startup_tids'] = tids
        row['initial_memory'] = inspect(owned.process.pid, load, EXPECTED[form]['sha256'], helper, strict)
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
        row['active_memory'] = inspect(owned.process.pid, load, EXPECTED[form]['sha256'], helper, strict)
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
        require(not queue.pending and queue.dispatched_go == 6 and queue.counts(6) == 6,
                'final partial output or cumulative GO/result count differs')
        require(queue.lines.count('uciok') == 1 and queue.lines.count('readyok') == 1,
                'protocol acknowledgment count differs')
        row.update(dispatched_GO=6, consumed_legal_bestmoves=6, boundaries=queue.boundaries,
                   no_helpers_or_extra_FDs_observed=True, startup_TIDs_persistent=True,
                   cancellation_causality='unproven', stdout_sha256=sha(owned.stdout.bytes()))
    except BaseException as error:
        row['operation_error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        settle_cleanup(owned, tids, row)
    row['passed'] = True


def personality_rejection(path, form, directory, budget, row):
    selected(path, form)
    directory.mkdir()
    libc = ctypes.CDLL(None, use_errno=True)
    libc.personality.argtypes = (ctypes.c_ulong,)
    libc.personality.restype = ctypes.c_int
    libc.ptrace.argtypes = (ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p)
    libc.ptrace.restype = ctypes.c_long

    def trace(request, pid, first=0, second=0):
        ctypes.set_errno(0)
        value = libc.ptrace(request, pid, ctypes.c_void_p(first), ctypes.c_void_p(second))
        error = ctypes.get_errno()
        if value == -1 and error:
            raise OSError(error, os.strerror(error))
        return value

    def preexec():
        old = libc.personality(0xffffffff)
        if old < 0 or libc.personality(old | 0x400000) < 0 or not libc.personality(0xffffffff) & 0x400000:
            os.write(2, b'personality-set-failed\n')
            os._exit(125)
        os.write(2, b'personality-set-confirmed\n')
        if libc.ptrace(0, 0, None, None) < 0:  # TRACEME, owned child only
            os._exit(124)

    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
    p = None
    try:
        def setup():
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            preexec()
        p = subprocess.Popen([str(path)], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True, preexec_fn=setup)
        RAW.add(p)
        row['pid'] = p.pid
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
    stdout = stderr = None
    events = []
    row['owned_negative_trace'] = events

    def append_event(event):
        events.append(event)
        with (directory/'trace-events.jsonl').open('a') as stream:
            stream.write(json.dumps(event)+'\n')
            stream.flush()

    try:
        end = time.monotonic() + budget.left(8)

        def wait_status():
            while time.monotonic() < end:
                pid, status = os.waitpid(p.pid, os.WNOHANG)
                if pid:
                    return status
                time.sleep(.001)
            raise TimeoutError('owned rejection trace deadline')

        status = wait_status()
        if os.WIFEXITED(status) or os.WIFSIGNALED(status):
            p.returncode = os.waitstatus_to_exitcode(status)
            stdout, stderr = p.communicate(timeout=2)
            row.update(returncode=p.returncode, stderr=stderr.decode(errors='replace'))
            raise AssertionError('personality setup/owned ptrace failed before exec stop; rejection unproven')
        require(os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGTRAP, 'no owned exec trap')
        require(sha(Path(f'/proc/{p.pid}/exe').read_bytes()) == EXPECTED[form]['sha256'],
                'rejection trace executable differs')
        trace(0x4200, p.pid, 0, 1 | 0x100000)  # TRACESYSGOOD | EXITKILL
        trace(24, p.pid)  # SYSCALL
        while True:
            status = wait_status()
            if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                p.returncode = os.waitstatus_to_exitcode(status)
                break
            require(os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGTRAP | 0x80,
                    'unexpected rejection trace stop')
            data = ctypes.create_string_buffer(128)
            count = trace(0x420e, p.pid, 128, ctypes.addressof(data))
            require(count >= 24, 'PTRACE_GET_SYSCALL_INFO unavailable')
            raw = data.raw
            if raw[0] == 1:
                append_event({'kind': 'entry', 'number': struct.unpack_from('<Q', raw, 24)[0],
                              'args': list(struct.unpack_from('<6Q', raw, 32))})
            elif raw[0] == 2:
                append_event({'kind': 'exit', 'result': struct.unpack_from('<q', raw, 24)[0]})
            else:
                raise AssertionError('unexpected syscall trace info kind')
            require(len(events) <= 8, 'unexpected pre-entry syscall count')
            trace(24, p.pid)
        stdout, stderr = p.communicate(timeout=2)
        row.update(pid=p.pid, returncode=p.returncode, stderr=stderr.decode(errors='replace'))
        row['owned_negative_trace'] = events
        (directory/'stdout.bin').write_bytes(stdout)
        (directory/'stderr.bin').write_bytes(stderr)
        require(stderr == b'personality-set-confirmed\n', 'READ_IMPLIES_EXEC could not be set; rejection unproven')
        require(p.returncode == 126 and not stdout, 'loader did not reject READ_IMPLIES_EXEC with exit126')
        require(len(events) == 3 and events[0]['kind'] == 'entry' and events[0]['number'] == 135 and
                events[0]['args'][0] == 0xffffffff and events[1]['kind'] == 'exit' and
                events[1]['result'] >= 0 and events[1]['result'] & 0x400000 and
                events[2]['kind'] == 'entry' and events[2]['number'] == 231 and events[2]['args'][0] == 126,
                'actual personality return -> exit126 before restore mmap not observed')
        require(absent(p.pid) and not Path(f'/proc/{p.pid}').exists(), 'personality case remains live')
        row.update(passed=True, personality_set_in_child_before_exec=True,
                   loader_rejection_exit=126, native_entry_not_observed=True,
                   rejection_preallocation_order='actual personality result -> exit_group126; no intervening mmap')
    finally:
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGKILL)
            row['forced_cleanup'] = True
        if stdout is None:
            stdout, stderr = p.communicate(timeout=3)
        row.update(returncode=p.returncode, stderr=stderr.decode(errors='replace'),
                   trace_event_count=len(events))
        (directory/'stdout.bin').write_bytes(stdout)
        (directory/'stderr.bin').write_bytes(stderr)
        row['owned_group_absent'] = absent(p.pid)
        RAW.discard(p)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--first-cost', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    out, base = a.out.resolve(), a.first_cost.resolve()
    require(sys.platform == 'linux' and a.out.is_absolute() and not out.exists() and
            not any((p/'.git').exists() for p in (out, *out.parents)), 'new absolute external Linux output required')
    out.mkdir()
    report = {'complete': False, 'scope': 'actual new Rust packed class; checkpoint/production/negative separate',
              'source_sha256': {}, 'forms': [], 'compiler_commands': [],
              'old_raw_kernel_trace_deep_fault_not_relabelled': True,
              'transient_WX_exclusion': 'unchanged pinned loader source sequence; final maps observed',
              'kernel_auxv_brk_nonuse': 'unchanged exact original Rust source proof reused',
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
            program = base/(form+'-first/whole/x')
            whole = selected(program, form)
            native = (base/(form+'-native/first/x')).read_bytes()
            load, static = producer.admit(native, form, packer)
            payload = (base/(form+'-first/whole/payload.bin')).read_bytes()
            require(sha(payload) == EXPECTED[form]['payload'], 'literal original fixed payload differs')
            row = {'form': form, 'whole_bytes': len(whole), 'whole_sha256': sha(whole),
                   'static_original_native_to_sectionless_binding': static, 'shipping': [], 'audit': {}, 'negative': {}}
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
        for row in report['forms']:
            form = row['form']
            personality_rejection(base/(form+'-first/whole/x'), form,
                                  out/(form+'-personality'), budget, row['negative'])
            save()
        require(not helper.OWNED and not RAW, 'owned handles remain registered')
        require(all(c['owned_group_absent'] for c in report['compiler_commands']), 'audit compiler group remains')
        report.update(complete=True, checkpoint_images_built_and_executed=2, shipping_sessions=4,
                      personality_rejection_sessions=2, live_owned_handles=0, runtime_qualified_fixed_profile=True,
                      under4096=False, strength_or_scaling_claim=False)
    except BaseException as error:
        report['complete'] = False
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
        save()
        signal.signal(signal.SIGTERM, previous_handler)
    print(json.dumps({'complete': report['complete'],
                      'shipping_sessions_passed': sum(bool(c.get('passed')) for r in report['forms'] for c in r['shipping']),
                      'audit_sessions_passed': sum(bool(r['audit'].get('passed')) for r in report['forms']),
                      'out': str(out)}))
    require(report['complete'], 'runtime receipt incomplete after cleanup; see runtime.json')


if __name__ == '__main__':
    main()
