#!/usr/bin/env python3
"""Bounded positive qualification of the separate finite Rust D shipping entry.

The canonical legacy Rust qualifier is not invoked. Only its strict byte/GO
accounting methods and the maintained Owned/Reader process helpers are reused.
No compiler, checkpoint, debugger, fault image or tracing is used here.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import struct
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, detail):
    if not value:
        raise AssertionError(detail)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def identity(path, expected=None):
    path = Path(path)
    raw = path.read_bytes()
    found = {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}
    if expected is not None:
        require(all(found[k] == expected[k] for k in ('bytes', 'sha256')), 'literal image identity differs: ' + str(path))
    return found


class Queue:
    """Owned bounded readers with the unchanged strict ASCII accounting API."""
    def __init__(self, owned, strict):
        self.owned, self.process, self.strict = owned, owned.process, strict
        self.lines, self.queued, self.boundaries, self.rejected_lines = [], [], [], []
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
            value = line.decode('ascii', errors='strict')
            self.lines.append(value)
            self.queued.append(value)

    def send(self, text):
        raw = text.encode('ascii') if isinstance(text, str) else text
        self.strict.Session.admit(self, raw)
        self.owned.send(raw)

    def until(self, prefix, timeout=8):
        def exit_status():
            if self.owned.reaped:
                return self.process.returncode
            status = os.waitid(os.P_PID, self.process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
            if status is None:
                return None
            return status.si_status if status.si_code == os.CLD_EXITED else -status.si_status

        end = time.monotonic() + timeout
        while time.monotonic() < end:
            while self.queued:
                text = self.queued.pop(0)
                if text.startswith(prefix):
                    return text
            self.pump(min(.05, max(0, end-time.monotonic())))
            if exit_status() is not None and not self.queued:
                break
        raise AssertionError(f"missing {prefix!r}; exit={exit_status()}, tail={self.lines[-8:]}, stderr={self.error!r}")

    def counts(self, expected):
        self.pump()
        return self.strict.Session.counts(self, expected)

    def no_best(self, duration=.025, active=False):
        self.pump()
        return self.strict.Session.no_best(self, duration, active)

    def best(self, allowed):
        return self.strict.best(self, allowed)


def memory(owned, kind, native, load, helper, strict, directory):
    pid = owned.process.pid
    rows = helper.mapping(pid)
    for begin, length, permissions in ((0x400000, 0x4000, 'r-x'), (0x404000, 0x1000, 'rw-')):
        helper.covers(rows, begin, length, permissions)
    if kind == 'whole':
        for begin in (0x3ff000, 0x405000):
            helper.covers(rows, begin, 4096, '---')
        require(all(len(row['line'].split()) == 5 for row in rows
                    if row['end'] > 0x400000 and row['start'] < 0x405000), 'restored mapping is not anonymous')
    stacks = strict.guarded(Path(f'/proc/{pid}/maps').read_text())
    require(len(stacks) == 2, 'two guarded nonexecutable 1MiB worker stacks required')
    with open(f'/proc/{pid}/mem', 'rb', buffering=0) as stream:
        actual = os.pread(stream.fileno(), 0x5000, 0x400000)
    expected = load if kind == 'whole' else native[:16392]
    require(len(actual) == 0x5000 and actual[:16392] == expected, 'mapped image bytes differ from selected load/native')
    require(actual[0x4000:0x4008] == bytes.fromhex('4601400000000000'), 'initialized memcpy pointer differs')
    output = struct.unpack_from('<I', actual, 0x4008)[0]
    require(output in (0, 1) and not any(actual[0x400c:]), 'OUTPUT atomic/RW page padding differs')
    directory.mkdir(parents=True)
    (directory/'maps.txt').write_text(Path(f'/proc/{pid}/maps').read_text())
    (directory/'image-five-pages.bin').write_bytes(actual)
    return {'kind': kind, 'mapped_load_sha256': sha(actual[:16392]), 'OUTPUT_value': output,
            'initialized_memcpy_pointer': 0x400146, 'RW_padding_zero_from': 0x40400c,
            'guarded_worker_stacks': stacks, 'image_guards': kind == 'whole',
            'final_maps_no_WX_and_process_stack_nonexec': True,
            'mapping': rows, 'snapshot': str(directory/'image-five-pages.bin')}


def session(path, kind, pin, native, load, directory, shutdown, budget, helper, strict, row):
    require(identity(path, pin)['sha256'] == pin['sha256'], 'image changed immediately before Popen')
    owned = helper.Owned(path, directory, budget)
    queue = Queue(owned, strict)
    tids = [owned.process.pid]
    row.update(pid=owned.process.pid, shutdown=shutdown, kind=kind, passed=False, searches=[])
    try:
        tids = helper.stable_startup(owned)
        row['startup_TIDs'] = tids
        require(sha(Path(f'/proc/{owned.process.pid}/exe').read_bytes()) == pin['sha256'], '/proc/exe identity differs')
        row['startup_memory'] = memory(owned, kind, native, load, helper, strict, directory/'startup-memory')
        queue.send(b'u')
        queue.pump(.01)
        require(not queue.lines, 'incomplete input line was dispatched')
        queue.send(b'ci\nisready\n')
        require(queue.until('uciok') == 'uciok' and queue.until('readyok') == 'readyok', 'minimal UCI acknowledgment differs')
        require(queue.lines == ['uciok', 'readyok'], 'unexpected identification/option/output line')
        queue.no_best()
        white, black = strict.initial('white'), strict.initial('black')

        def result(allowed, label):
            move = queue.best(allowed)
            row['searches'].append({'phase': label, 'move': move, 'legal': True})
            return move

        def active(label):
            before = helper.tasks(owned.process.pid)
            require(sorted(before) == tids, 'persistent startup TIDs changed')
            observed = helper.physical_active(owned, tids, before)
            queue.no_best(active=True)
            row[label] = observed

        queue.send('position startpos\ngo\n')
        result(white, 'finite bare natural completion')
        queue.no_best()
        queue.send('position startpos moves e2e4\ngo btime +0 wtime 0\n')
        result(black, 'own-side checked plus zero clock')
        queue.no_best()
        queue.send('go btime 30000 infinite depth 1 nodes 1 movetime 1\n')
        active('finite_infinite_and_unsupported_go_fields')
        queue.send('stop\nucinewgame\nsetoption name Hash value 1\nisready\n')
        require(queue.until('readyok') == 'readyok', 'ready barrier absent during consumed commands')
        queue.no_best(active=True)
        result(black, 'finite infinite and unsupported consume natural completion')
        queue.no_best()
        queue.send('go btime 30000\n')
        active('before_GO_replacement')
        queue.send('go btime 0\n')
        result(black, 'old result drained before next GO')
        result(black, 'replacement own-clock result')
        queue.no_best()
        queue.send('go btime 30000\n')
        active('before_position_fence')
        queue.send('position startpos\nisready\n')
        result(black, 'prior result before position acknowledgment')
        require(queue.until('readyok') == 'readyok', 'position fence readiness absent')
        queue.no_best()
        # Existing bounded ASCII reader policy: rejected lines cannot dispatch GO.
        queue.send(b'go btime 0\0\ngo btime 0\x80\n' + b'x'*32769 + b'\n')
        queue.send(b' \tposition\vstartpos\fmoves\re2e4\ngo\tbtime\v+0\n')
        result(black, 'ASCII whitespace and rejected-line resynchronization')
        queue.no_best()
        require(len(queue.rejected_lines) == 3, 'strict rejected-line accounting differs')
        queue.send('go btime 30000\n')
        active('before_active_shutdown')
        row['active_memory'] = memory(owned, kind, native, load, helper, strict, directory/'active-memory')
        require(sorted(helper.tasks(owned.process.pid)) == tids, 'startup TIDs replaced before exit')
        if shutdown == 'quit':
            queue.send('quit\n')
        else:
            queue.send(b'isready')
            strict.Session.admit(queue, eof=True)
        owned.close_input()
        row['settled'] = owned.finish()
        queue.pump()
        result(black, 'active final result before physical exit')
        if shutdown == 'EOF':
            # The final unterminated ASCII line is processed before EOF shutdown.
            require(queue.lines.count('readyok') == 4, 'unterminated EOF input was not dispatched')
        queue.no_best()
        require(queue.dispatched_go == 8 and queue.counts(8) == 8 and not queue.pending and not queue.input_pending,
                'GO/result accounting or final partial tail differs')
        require(all(line in ('uciok', 'readyok') or line.startswith('bestmove ') for line in queue.lines), 'unexpected public output')
        require(queue.lines.count('uciok') == 1 and queue.lines.count('readyok') == (4 if shutdown == 'EOF' else 3),
                'acknowledgment count differs')
        row.update(dispatched_GO=8, legal_bestmoves=8, boundaries=queue.boundaries,
                   rejected_lines=queue.rejected_lines, output_sha256=sha(owned.stdout.bytes()),
                   finite_clock_scope='natural completion and active observations; hard real-time deadline not claimed',
                   cancellation_causality='unproven; completion fences physically observed')
    except BaseException as error:
        row['operation_error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        cleanup = owned.cleanup()
        cleanup['all_observed_TIDs_absent'] = all(not Path(f'/proc/{tid}').exists() for tid in tids)
        row['cleanup'] = cleanup
        if owned.finished:
            require(not cleanup['forced_cleanup'] and not cleanup['errors'] and cleanup['readers_joined'] and
                    cleanup['owned_group_absent'] and cleanup['all_observed_TIDs_absent'], 'physical exit/readers/groups required intervention')
    row['passed'] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out, built = args.out.resolve(), args.build.resolve()
    require(sys.platform == 'linux' and args.build.is_absolute() and args.out.is_absolute() and not out.exists() and
            not any((part/'.git').exists() for part in (out, *out.parents)), 'new absolute external Linux output required')
    out.mkdir(parents=True)
    report = {'passed': False, 'scope': 'one selected finite Rust D positive qualification; native and whole scalar/HQ; quit and EOF',
              'sessions': [], 'runtime_profiles': {'workers': 2, 'tt_bits': 18, 'tiny_shipping': True},
              'resource_limits': {'parent_AS': 4*1024**3, 'child_inherited_AS': 4*1024**3,
                                  'parent_CPU': 180, 'child_inherited_CPU': 180, 'aggregate_wall': 180, 'per_pipe_bytes': 1048576},
              'limits_scope': 'children inherit finite AS/CPU before exec; shared Budget bounds each normal operation; owned groups/readers cleaned',
              'compiler_calls': 0, 'checkpoints': 0, 'ptrace': 0, 'tracing': 0, 'negative_layout_or_fault_sessions': 0,
              'legacy_qualify_calls': 0, 'runtime_admission_complete': False, 'all_loader_conditions_verified': False}
    def save():
        (out/'runtime.json').write_text(json.dumps(report, indent=2)+'\n')
    previous = {sig: signal.signal(sig, lambda s, f: (_ for _ in ()).throw(TimeoutError('bounded verifier signal '+str(s))))
                for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM, signal.SIGXCPU)}
    helper = None
    try:
        resource.setrlimit(resource.RLIMIT_AS, (4*1024**3,)*2)
        resource.setrlimit(resource.RLIMIT_CPU, (180,)*2)
        signal.alarm(180)
        builder = module('rust_d_shipping_builder', HERE/'build.py')
        closure = builder.source_closure()
        report['source_closure'] = closure
        require(all(sha((REPO/name).read_bytes()) == digest for name, digest in closure.items()), 'current source closure differs')
        recipe_raw = (HERE/'recipe.json').read_bytes()
        base_recipe = json.loads(recipe_raw)
        recorded = json.loads((built/'build.json').read_text())
        require(recorded['complete'] and recorded['source_closure'] == closure and recorded['recipe_sha256'] == sha(recipe_raw),
                'ordinary build/source/recipe identity differs')
        recipe, image_policy = builder.select_recipe(base_recipe, recorded['selected_image_policy'])
        require(recorded['class'] == recipe['class'] and recorded['image_policy'] == image_policy,
                'selected Rust restoration class/policy differs')
        report['recipe_sha256'] = sha(recipe_raw)
        report.update(selected_image_policy=recorded['selected_image_policy'], image_policy=image_policy,
                      image_class=recipe['class'])
        helper = module('rust_d_shipping_owned', HERE.parent/'tiny-entry-d/verify.py')
        strict = module('rust_d_shipping_strict', HERE.parent/'tiny-rust-d/verify_runtime.py')
        report['helpers'] = {str(p.relative_to(REPO)): identity(p) for p in
                             (HERE.parent/'tiny-entry-d/verify.py', HERE.parent/'tiny-rust-d/verify_runtime.py')}
        budget = helper.Budget(180)
        forms = {form['form']: form for form in recorded['forms']}
        require(set(forms) == {'scalar', 'hq'}, 'exact two selected forms required')
        for mode in ('scalar', 'hq'):
            form = forms[mode]
            require(form['artifact_gates'] and all(form['artifact_gates'].values()) and len(form['attempts']) == 2,
                    'ordinary repeated build/static artifact gate failed')
            first, repeated = form['attempts']
            for name in ('native', 'whole', 'load', 'restored'):
                identity(first[name]['path'], recipe['forms'][mode][name])
                identity(repeated[name]['path'], recipe['forms'][mode][name])
            native = Path(first['native']['path']).read_bytes()
            restored = Path(first['restored']['path']).read_bytes()
            for kind in ('native', 'whole'):
                path = Path(first[kind]['path'])
                for shutdown in ('quit', 'EOF'):
                    row = {'form': mode, 'image': identity(path), 'shutdown': shutdown}
                    report['sessions'].append(row)
                    save()
                    session(path, kind, recipe['forms'][mode][kind], native, restored,
                            out/(mode+'-'+kind+'-'+shutdown), shutdown, budget, helper, strict, row)
                    save()
        require(len(report['sessions']) == 8 and all(row['passed'] for row in report['sessions']), 'selected session set incomplete')
        require(not helper.OWNED, 'owned process registry not empty')
        require(builder.source_closure() == closure, 'source changed during qualification')
        report['passed'] = True
    except BaseException as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        if helper is not None:
            report['final_owned_cleanup'] = [owned.cleanup() for owned in tuple(helper.OWNED)]
        signal.alarm(0)
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        save()
    print(json.dumps({'passed': report['passed'], 'sessions': len(report['sessions']), 'report': str(out/'runtime.json')}))


if __name__ == '__main__':
    main()
