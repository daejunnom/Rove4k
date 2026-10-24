#!/usr/bin/env python3
"""Four fixed main links only; never execute a production ELF or builder main."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FILES = ('main.rs', 'board.rs', 'search.rs', 'runtime.rs', 'os.rs', 'link.ld', 'build.py')
COMPILER = 'rustc 1.97.0 (2d8144b78 2026-07-07)'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def flags(path):
    assignments = [node for node in ast.walk(ast.parse(path.read_bytes()))
                   if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'flags' for t in node.targets)]
    require(len(assignments) == 1, 'expected one literal flags assignment')
    value = ast.literal_eval(assignments[0].value)
    require(isinstance(value, list) and all(isinstance(s, str) for s in value), 'literal flags list required')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--rustc', default='/home/stemxstudio/.cargo/bin/rustc')
    args = parser.parse_args()
    out = args.out.resolve()
    require(sys.platform == 'linux' and platform.machine() == 'x86_64', 'Linux x86-64 only')
    repo = HERE.parents[2]
    require(args.out.is_absolute() and not out.exists() and out != repo and repo not in out.parents, 'new absolute external output required')
    out.mkdir()
    report = {'complete': False, 'scope': 'four main Rust links and static ELF inspection only',
              'production_ELF_executions': 0, 'runtime_qualified': False, 'commands': [], 'forms': []}
    active = None

    def save():
        (out/'native-cost.json').write_text(json.dumps(report, indent=2)+'\n')

    def group_absent(pid):
        try:
            os.killpg(pid, 0)
            return False
        except ProcessLookupError:
            return True

    def cleanup(row):
        nonlocal active
        if active is None:
            return
        row['cleanup_complete'] = False
        row['cleanup_attempts'] = row.get('cleanup_attempts', 0)+1
        try:
            os.killpg(active.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except BaseException as error:
            row['cleanup_kill_error'] = repr(error)
        try:
            stdout, stderr = active.communicate(timeout=5)
            row.update(cleanup_returncode=active.returncode, cleanup_stdout=stdout,
                       cleanup_stderr=stderr, cleanup_EOF_drained=True)
        except BaseException as error:
            row['cleanup_error'] = {'type': type(error).__name__, 'message': str(error)}
            if isinstance(error, subprocess.TimeoutExpired):
                for key, value in (('cleanup_partial_stdout', error.output), ('cleanup_partial_stderr', error.stderr)):
                    row[key] = value.decode(errors='replace') if isinstance(value, bytes) else value
            row['cleanup_EOF_drained'] = False
        row['cleanup_group_absent'] = group_absent(active.pid)
        row['cleanup_complete'] = (active.returncode is not None and row['cleanup_group_absent']
                                   and row['cleanup_EOF_drained'])
        if row['cleanup_complete']:
            active = None

    def run(command, cwd, environment):
        nonlocal active
        row = {'command': command, 'cwd': str(cwd), 'pid': None, 'returncode': None}
        report['commands'].append(row)
        save()
        try:
            old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
            try:
                active = subprocess.Popen(command, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
                                          preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, old_mask))
                row['pid'] = active.pid
                save()
            finally:
                # Registration precedes delivery of any pending parent signal.
                signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
            stdout, stderr = active.communicate(timeout=120)
            row.update(returncode=active.returncode, stdout=stdout, stderr=stderr,
                       group_absent=group_absent(active.pid), EOF_drained=True)
            save()
            require(active.returncode == 0, 'tool failed')
            require(row['group_absent'], 'tool group did not settle')
            return row
        except BaseException as error:
            row['error'] = {'type': type(error).__name__, 'message': str(error)}
            if isinstance(error, subprocess.TimeoutExpired):
                for key, value in (('partial_stdout', error.output), ('partial_stderr', error.stderr)):
                    row[key] = value.decode(errors='replace') if isinstance(value, bytes) else value
            try:
                save()
            finally:
                cleanup(row)
            raise
        finally:
            if active is not None and row.get('group_absent') and row.get('EOF_drained'):
                active = None
            save()

    def interrupted(signum, _frame):
        raise InterruptedError('signal '+str(signum))

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        pins = json.loads((HERE/'source-pins.json').read_bytes())
        for name, expected in pins.items():
            require(sha((HERE/name).read_bytes()) == expected, 'source pin differs: '+name)
        report['source_sha256'] = pins
        environment = os.environ.copy()
        environment.update(LC_ALL='C', TZ='UTC', SOURCE_DATE_EPOCH='0', ROVE_WORKERS='2', ROVE_TT_BITS='18')
        compiler = shutil.which(args.rustc)
        require(compiler, 'compiler unavailable')
        version = run([compiler, '--version'], out, environment)['stdout'].strip()
        require(version == COMPILER, 'unexpected Rust compiler')
        report['compiler'] = version
        spec = importlib.util.spec_from_file_location('own_packer', HERE/'packaging/packer.py')
        packer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(packer)
        recipe = json.loads((HERE/'recipe.json').read_bytes())
        for kind in ('control', 'candidate'):
            for backend in ('scalar', 'hq'):
                name = kind+'-'+backend
                local = out/name
                local.mkdir()
                for filename in FILES:
                    shutil.copyfile(HERE/kind/filename, local/filename)
                environment['ROVE_HQ'] = str(int(backend == 'hq'))
                command = [compiler, '--remap-path-prefix', str(local)+'=.', *flags(local/'build.py')]
                record = run(command, local, environment)
                native = (local/'x').read_bytes()
                parsed = packer.elf(native)
                row = {'form': name, 'bytes': len(native), 'sha256': sha(native), 'path': str(local/'x'),
                       'elf': parsed, 'compile_command_index': report['commands'].index(record),
                       'source_bytes': sum((local/f).stat().st_size for f in FILES if f.endswith('.rs'))}
                report['forms'].append(row)
                save()
                if kind == 'control':
                    expected = recipe['control_native'][name]
                    require(len(native) == expected['bytes'] and sha(native) == expected['sha256'], 'control native mismatch')
                for tool, suffix, option in (('readelf', 'program_headers.txt', '-lW'), ('readelf', 'sections.txt', '-SW'),
                                             ('readelf', 'dynamic.txt', '-dW'), ('objdump', 'disassembly.txt', '-d')):
                    r = run([tool, option, str(local/'x')], local, environment)
                    (local/suffix).write_text(r['stdout'])
        require(len([r for r in report['commands'] if r['command'][0] == compiler and '--version' not in r['command']]) == 4,
                'unexpected main link count')
        report.update(complete=True, Rust_main_links=4, extra_unstripped_links=0,
                      normal_builder_main_invoked=False, next_phase_requires_literal_layout_review=True)
        save()
        print(json.dumps({'complete': True, 'out': str(out), 'forms': [{k: r[k] for k in ('form', 'bytes', 'sha256')} for r in report['forms']]}))
    except BaseException as error:
        report['complete'] = False
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        if active is not None:
            report['complete'] = False
            cleanup(report['commands'][-1])
        save()


if __name__ == '__main__':
    main()
