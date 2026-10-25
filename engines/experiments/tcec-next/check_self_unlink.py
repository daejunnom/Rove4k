#!/usr/bin/env python3
"""Bounded actual checks for the separate entry-owned TCEC unlink candidate.

Consumes an external finite-cost receipt, rechecks every source/proof/package,
compiles immutable candidate artifacts twice, and runs only disposable copies or
the real source-JIT wrapper.  It never executes a preserved native artifact.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shlex
import signal
import stat
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
PINS = {
    'engines/scripts/source_package.py': '4c3775e713b093de39cb54e12abdef29793dd924731f1b3014c406d1df4e4f19',
    'engines/compact/tiny-entry-d/verify.py': '18faa69aed5cb5dd85a054ef2e6830463f3d819f5f635d74d55550a877c81eae',
    'engines/tests/chess_oracle.py': 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def group_members(pgid):
    result = []
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal() or int(path.name) == pgid:
            continue
        try:
            fields = (path/'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid:
                result.append({'pid': int(path.name), 'state': fields[0]})
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cost', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--ports-only', action='store_true')
    parser.add_argument('--qualified', type=Path,
                        help='prior focused output supplies only a hash-checked failure-port ELF fixture')
    args = parser.parse_args()
    require(sys.platform == 'linux', 'Linux execution is required')
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists()
            and not any((p/'.git').exists() for p in (out, *out.parents)),
            'new absolute external output required')
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (180, 200))
    deadline = time.monotonic() + 240
    out.mkdir(parents=True)
    report = {'format': 1, 'complete': False, 'inputs': {}, 'commands': [],
              'sessions': [], 'ports': [], 'direct_disposable_sessions': [], 'preserved_native_artifacts': {},
              'scope': 'Self-unlink startup/package/failure scope, not strength or full engine acceptance'}
    def save():
        (out/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    def check_time():
        require(time.monotonic() < deadline, 'focused campaign wall budget exceeded')
    def interrupted(sig, frame):
        raise TimeoutError('self-unlink checker signal ' + str(sig))
    handlers = {s: signal.signal(s, interrupted) for s in (signal.SIGTERM, signal.SIGINT, signal.SIGXCPU, signal.SIGALRM)}
    signal.alarm(240)
    owned = set()
    helper = None
    try:
        names = [*PINS, 'engines/experiments/tcec-next/self_unlink.py',
                 'engines/experiments/tcec-next/check_self_unlink.py']
        for name in names:
            data = (ROOT/name).read_bytes().replace(b'\r\n', b'\n')
            require(b'\r' not in data, 'lone CR in source')
            if name in PINS:
                require(pin(data)['sha256'] == PINS[name], 'fixed focused dependency changed: ' + name)
            report['inputs'][name] = pin(data)
            target = out/'inputs'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        packaging = load('unlink_focused_package', out/'inputs/engines/scripts/source_package.py')
        projection = load('unlink_focused_source', out/'inputs/engines/experiments/tcec-next/self_unlink.py')
        helper = load('unlink_focused_owned', out/'inputs/engines/compact/tiny-entry-d/verify.py')
        oracle = load('unlink_focused_oracle', out/'inputs/engines/tests/chess_oracle.py')
        cost_raw = args.cost.read_bytes()
        cost = json.loads(cost_raw)
        report['cost'] = {'path': str(args.cost.resolve()), **pin(cost_raw)}
        require(cost['helper'] == report['inputs']['engines/experiments/tcec-next/self_unlink.py'],
                'cost receipt used another source projection')
        fixture_root = out
        if args.ports_only:
            require(args.qualified is not None and args.qualified.is_absolute(),
                    'ports-only requires an explicit prior qualified ELF fixture directory')
            fixture_root = args.qualified.resolve()
            data = (fixture_root/'result.json').read_bytes()
            qualified = json.loads(data)
            require(qualified['complete'] is True and qualified['final_owned_remaining'] == 0,
                    'failure-port fixture campaign was not complete')
            require(qualified['inputs']['engines/experiments/tcec-next/self_unlink.py']
                    == report['inputs']['engines/experiments/tcec-next/self_unlink.py'],
                    'failure fixture used another projection')
            require(pin((fixture_root/'F/first/x').read_bytes())
                    == qualified['preserved_native_artifacts']['F'], 'failure-port ELF fixture differs')
            report['prior_failure_port_fixture'] = {'receipt': pin(data), 'path': str(fixture_root),
                                                     'scope': 'fixture only, no new generation or normal-runtime claim'}

        def command(argv, cwd, stdin=None):
            check_time()
            row = {'argv': list(map(str, argv)), 'cwd': str(cwd), 'complete': False}
            report['commands'].append(row)
            d = out/'command-logs'/str(len(report['commands']))
            d.mkdir(parents=True)
            with (d/'stdout').open('wb') as stdout, (d/'stderr').open('wb') as stderr:
                child = subprocess.Popen(list(map(str, argv)), cwd=cwd,
                                         stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                                         stdout=stdout, stderr=stderr, start_new_session=True)
                owned.add(child)
                if stdin is not None:
                    child.stdin.write(stdin)
                    child.stdin.close()
                end = min(deadline, time.monotonic()+30)
                while os.waitid(os.P_PID, child.pid, os.WEXITED|os.WNOHANG|os.WNOWAIT) is None:
                    require(time.monotonic() < end, 'compiler/fixture wall timeout')
                    time.sleep(.005)
                require(not group_members(child.pid), 'compiler descendants remain before reap')
                row['returncode'] = child.wait(timeout=3)
                owned.remove(child)
                row.update(reaped=True, group_absent=not group_members(child.pid))
            row['stdout'] = pin((d/'stdout').read_bytes())
            row['stderr'] = pin((d/'stderr').read_bytes())
            require(row['returncode'] == 0, 'focused compile failed: ' + str(d))
            require(row['stderr']['bytes'] == 0, 'focused compile emitted stderr: ' + str(d))
            row['complete'] = True
            save()

        def start(path, directory):
            directory.mkdir(parents=True)
            previous = Path.cwd()
            try:
                os.chdir(directory)
                return helper.Owned(path, directory, helper.Budget(min(35, deadline-time.monotonic())))
            finally:
                os.chdir(previous)

        def finish_status(item, expected):
            end = time.monotonic()+item.budget.left(10)
            while not item.exited() or item.group_others():
                require(time.monotonic() < end, 'failure-port original/group did not settle')
                time.sleep(.005)
            actual = item.process.wait(timeout=3)
            item.reaped = True
            for reader in (item.stdout, item.stderr):
                reader.thread.join(timeout=3)
                require(reader.done and not reader.thread.is_alive() and not reader.error, 'failure reader did not settle')
            require(actual == expected, 'wrong declared failure status')
            item.finished = True
            return {'returncode': actual, 'reaped': True, 'readers_joined': True}

        for family in (() if args.ports_only else ('A', 'B', 'C', 'E', 'F', 'F8')):
            row = cost['profiles'][family]
            entry = row['variants']['return-short']
            source_path = args.cost.resolve().parent/family/'return-short/main.c'
            source = source_path.read_bytes()
            require(pin(source) == entry['source'], 'finite candidate source differs')
            original = projection.restore_source(source, json.loads((source_path.parent/'source-proof.json').read_bytes()))
            reproduced, proof = projection.transform_source(original, family=family)
            require(reproduced == source, 'focused regeneration differs')
            directory = out/family
            directory.mkdir()
            (directory/'main.c').write_bytes(source)
            program = projection.package(packaging, source, row['compression'], compiler=row['compiler'])
            require(pin(program) == entry['whole'], 'focused whole differs from finite cost')
            script = directory/'program'
            script.write_bytes(program)
            script.chmod(0o700)
            natives = []
            for name in ('first', 'repeat'):
                d = directory/name
                d.mkdir()
                command(row['compiler'], d, source)
                natives.append((d/'x').read_bytes())
            require(natives[0] == natives[1], 'two candidate native compilations differ')
            expected_native = pin(natives[0])
            report['preserved_native_artifacts'][family] = expected_native
            for ending in ('quit', 'EOF'):
                item = start(script, directory/ending)
                session = {'family': family, 'ending': ending, 'complete': False}
                report['sessions'].append(session)
                try:
                    stdin = os.fstat(item.process.stdin.fileno())
                    item.send(b'uci\nisready\n')
                    item.wait_line(b'readyok')
                    proc = Path('/proc')/str(item.process.pid)
                    image = (proc/'exe').read_bytes()
                    link = str((proc/'exe').readlink())
                    target = Path(link.removesuffix(' (deleted)'))
                    require(pin(image) == expected_native and link.endswith(' (deleted)'), 'actual JIT image/deletion differs')
                    require(target.is_absolute() and not target.exists(), 'entry did not remove owned absolute image path')
                    received = os.stat(proc/'fd/0')
                    require((stdin.st_dev, stdin.st_ino) == (received.st_dev, received.st_ino), 'JIT consumed original stdin')
                    require(not (proc/'task'/str(item.process.pid)/'children').read_text().split(), 'cleanup child remains')
                    item.send(b'position startpos\ngo wtime 150 btime 150\n')
                    item.wait_best(1)
                    move = [line.split()[1].decode() for line in item.stdout.bytes().splitlines() if line.startswith(b'bestmove ')][-1]
                    require(move in {str(m) for m in oracle.Board.from_fen().legal_moves()},
                            'focused bestmove is not legal')
                    session.update(native=expected_native, deleted_path=str(target), cleanup_child_absent=True,
                                   original_stdin=True, legal_bestmove=move)
                    if ending == 'EOF':
                        item.close_input()
                    else:
                        item.send(b'quit\n')
                    session['exit'] = item.finish()
                    session['complete'] = True
                finally:
                    session['cleanup'] = item.cleanup()
                    save()
                require(session['cleanup']['owned_group_absent'] and not session['cleanup']['forced_cleanup']
                        and not session['cleanup']['errors'], 'positive session required forced cleanup')

            # The preserved artifact is only read; a fresh disposable path is run.
            disposable = directory/'disposable-native'
            disposable.write_bytes(natives[0])
            disposable.chmod(0o700)
            direct = start(disposable, directory/'direct')
            direct_row = {'family': family, 'path': str(disposable), 'complete': False}
            report['direct_disposable_sessions'].append(direct_row)
            try:
                direct.send(b'uci\nisready\nquit\n')
                direct.wait_line(b'readyok')
                require(not disposable.exists(), 'disposable native did not remove only its own path')
                direct_row.update(deleted=True, native=expected_native, exit=direct.finish(), complete=True)
            finally:
                receipt = direct.cleanup()
                direct_row['cleanup'] = receipt
            require(not receipt['forced_cleanup'] and not receipt['errors'], 'disposable direct cleanup failed')
            for name in ('first', 'repeat'):
                require(pin((directory/name/'x').read_bytes()) == expected_native, 'preserved native artifact changed')
            require((directory/'main.c').read_bytes() == source and script.read_bytes() == program,
                    'source or submission script was modified by execution')

        # A controlled nonexistent argv0 exercises remove failure without naming
        # any protected source, script or preserved native file as the target.
        directory = out/'unlink-failure'
        directory.mkdir()
        disposable = directory/'disposable'
        disposable.write_bytes((fixture_root/'F/first/x').read_bytes())
        disposable.chmod(0o700)
        missing = directory/'never-created'
        launcher = directory/'launch'
        launcher.write_text('#!/bin/bash\nexec -a ' + shlex.quote(str(missing)) + ' '
                            + shlex.quote(str(disposable)) + '\n')
        launcher.chmod(0o700)
        item = start(launcher, directory/'run')
        try:
            receipt = finish_status(item, 2)
            require(item.stdout.bytes() == b'' and item.stderr.bytes() == b'', 'failed remove reached UCI')
            require(disposable.is_file() and not missing.exists(), 'failure port deleted an unintended path')
            report['ports'].append({'case': 'owned-missing-argv0', 'exit': receipt, 'UCI_output_bytes': 0,
                                    'disposable_retained': True})
        finally:
            failure_cleanup = item.cleanup()
        require(not failure_cleanup['forced_cleanup'] and not failure_cleanup['errors'], 'failure port cleanup failed')

        # A valid, hash-pinned ELF is deliberately left by each compiler port.
        # Pipeline failure must stop before it can execute and self-unlink.
        fixture = fixture_root/'F/first/x'
        fixture_pin = pin(fixture.read_bytes())
        source = (args.cost.resolve().parent/'F/return-short/main.c').read_bytes()
        require(pin(source) == cost['profiles']['F']['variants']['return-short']['source'],
                'failure-port source differs')
        for case, expected_status in (('compiler', 33), ('decoder', 1), ('tail', 44)):
            d = out/'pipeline-ports'/case
            d.mkdir(parents=True)
            temporary = d/'temporary'
            temporary.mkdir()
            fake = d/'compiler'
            fake.write_text('#!/usr/bin/python3\nimport os,shutil,sys\n'
                            'sys.stdin.buffer.read()\n'
                            'p=sys.argv[sys.argv.index("-o")+1]\n'
                            'shutil.copyfile(' + repr(str(fixture)) + ',p)\n'
                            'os.chmod(p,0o700)\nraise SystemExit('
                            + ('33' if case == 'compiler' else '0') + ')\n')
            fake.chmod(0o700)
            compiler = [str(fake), *cost['profiles']['F']['compiler'][1:]]
            program = projection.package(packaging, source, cost['profiles']['F']['compression'], compiler=compiler)
            if case == 'decoder':
                program = program[:-5]
            script = d/'program'
            script.write_bytes(program)
            script.chmod(0o700)
            environment = 'export LC_ALL=C TMPDIR=' + shlex.quote(str(temporary)) + '\n'
            if case == 'tail':
                bin_dir = d/'bin'
                bin_dir.mkdir()
                tail = bin_dir/'tail'
                tail.write_text('#!/bin/sh\n/usr/bin/tail "$@"\nexit 44\n')
                tail.chmod(0o700)
                environment += 'export PATH=' + shlex.quote(str(bin_dir) + ':/usr/bin:/bin') + '\n'
            launch = d/'launch'
            launch.write_text('#!/bin/bash\n' + environment + 'exec ' + shlex.quote(str(script)) + '\n')
            launch.chmod(0o700)
            item = start(launch, d/'run')
            port = {'case': case, 'expected_status': expected_status, 'complete': False}
            report['ports'].append(port)
            try:
                port['exit'] = finish_status(item, expected_status)
                require(not item.stdout.bytes(), 'failed pipeline reached native UCI')
                if case == 'decoder':
                    require(b'unexpected end of input' in item.stderr.bytes().lower(),
                            'decoder port missed the intended real xz error')
                else:
                    require(not item.stderr.bytes(), 'pipeline port emitted an unrelated error')
                targets = list(temporary.iterdir())
                require(len(targets) == 1 and not targets[0].is_symlink()
                        and stat.S_ISREG(targets[0].stat().st_mode)
                        and pin(targets[0].read_bytes()) == fixture_pin,
                        'failure port did not leave the intended valid native')
                require(script.read_bytes() == program and pin(fixture.read_bytes()) == fixture_pin,
                        'failure port changed its script or preserved ELF fixture')
                port.update(valid_native_retained=True, native=fixture_pin, UCI_output_bytes=0,
                            stderr=pin(item.stderr.bytes()))
            finally:
                port['cleanup'] = item.cleanup()
                save()
            require(not port['cleanup']['forced_cleanup'] and not port['cleanup']['errors']
                    and port['cleanup']['owned_group_absent'], 'pipeline port host cleanup failed')
            for target in temporary.iterdir():
                target.unlink()
            port.update(complete=True, retained_temp_removed_by_test_host_after_group_settled=True)
            save()

        report.update(complete=True, owned_remaining=len(owned)+len(helper.OWNED))
        save()
    finally:
        signal.alarm(0)
        for item in tuple(helper.OWNED) if helper is not None else ():
            item.cleanup()
        for child in tuple(owned):
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(child.pid, sig)
                except ProcessLookupError:
                    pass
                end = time.monotonic()+3
                while time.monotonic()<end and (os.waitid(os.P_PID, child.pid, os.WEXITED|os.WNOHANG|os.WNOWAIT) is None or group_members(child.pid)):
                    time.sleep(.01)
                if os.waitid(os.P_PID, child.pid, os.WEXITED|os.WNOHANG|os.WNOWAIT) is not None and not group_members(child.pid):
                    child.wait(timeout=3)
                    owned.remove(child)
                    break
        report['final_owned_remaining'] = len(owned)+(len(helper.OWNED) if helper else 0)
        save()
        for sig, previous in handlers.items():
            signal.signal(sig, previous)
    print(json.dumps({'path': str(out/'result.json'), **pin((out/'result.json').read_bytes()),
                      'complete': report['complete'], 'commands': len(report['commands']),
                      'sessions': len(report['sessions']), 'ports': len(report['ports'])}))


if __name__ == '__main__':
    main()
