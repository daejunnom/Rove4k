#!/usr/bin/env python3
"""Two fixed candidate loader links; reuse two literal old whole controls."""

if __name__ == "__main__":
    raise SystemExit("Rove4k Rust engine paths are retired; use C A-F")

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


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--native-cost', type=Path, required=True)
    parser.add_argument('--old-cost', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(sys.platform == 'linux' and platform.machine() == 'x86_64', 'Linux x86-64 only')
    repo = HERE.parents[2]
    require(args.out.is_absolute() and not out.exists() and out != repo and repo not in out.parents, 'new absolute external output required')
    out.mkdir()
    report = {'complete': False, 'scope': 'two fixed whole candidate builds and two literal old control reuses',
              'production_ELF_executions': 0, 'runtime_qualified': False, 'commands': [], 'forms': []}
    active = None

    def save():
        (out/'whole-cost.json').write_text(json.dumps(report, indent=2)+'\n')

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
        require(sha((HERE/'packing-recipe.json').read_bytes()) == '7c843cf866fd1321f9db2278657e6d975a441b2504df965faf9d5c1b88def44e', 'packing recipe differs')
        require(sha((HERE/'admit.py').read_bytes()) == 'd0827e713ed9ba2c3db7f6fe0ab6a7db911ccc57af708ffeed95c98f9e0ebd4e', 'new literal admission differs')
        recipe = json.loads((HERE/'packing-recipe.json').read_bytes())
        native_report = (args.native_cost/'native-cost.json').read_bytes()
        require(sha(native_report) == recipe['native_cost_report_sha256'], 'native cost receipt differs')
        require(json.loads(native_report)['complete'], 'native phase incomplete')
        environment = {**os.environ, 'LC_ALL': 'C', 'TZ': 'UTC', 'SOURCE_DATE_EPOCH': '0'}
        packer = module('own_packer', HERE/'packaging/packer.py')
        codec = module('own_codec', HERE/'packaging/loader/codec.py')
        admitted = module('own_literal_class', HERE/'admit.py')
        old8 = module('immutable_data8', HERE/'reference/data8-build.py')
        old16 = module('immutable_data16', HERE/'reference/data16-guard.py')
        require(admitted.CLASS == recipe['class'] and admitted.NATIVE == recipe['native_expected'], 'class identity differs')
        require(codec.BCJ_VERSION == recipe['codec']['bcj_version'] and codec.FIXED_VERSION == recipe['codec']['fixed_version'], 'codec version differs')
        report.update(class_name=admitted.CLASS, source_sha256=pins, packing_recipe_sha256=sha((HERE/'packing-recipe.json').read_bytes()),
                      native_cost_report_sha256=sha(native_report), source_proof_only_zero_fill=True)
        for form, expected in recipe['control_whole'].items():
            original = args.old_cost/(form+'-first')/'whole/x'
            whole = original.read_bytes()
            require(len(whole) == expected['bytes'] and sha(whole) == expected['sha256'], 'old whole control differs')
            copied = out/(form+'-reused')
            copied.mkdir()
            (copied/'x').write_bytes(whole)
            (copied/'x').chmod(0o755)
            report['forms'].append({'form': form, 'bytes': len(whole), 'sha256': sha(whole), 'path': str(copied/'x'),
                                    'original_path': str(original), 'reused_not_rebuilt': True, 'codec_or_loader_invocations': 0})
        save()
        for backend in ('scalar', 'hq'):
            form = 'candidate-'+backend
            native = (args.native_cost/form/'x').read_bytes()
            load, proof = admitted.admit(native, form, packer)
            rejected = {}
            for label, old, oldform in (('original_data8', old8, 'control-'+backend), ('original_data16', old16, backend)):
                try:
                    old.admit(native, oldform, packer)
                except ValueError as error:
                    require(str(error) == 'unknown original qualified Rust D native', 'unexpected old guard failure')
                    rejected[label] = str(error)
                else:
                    raise ValueError('old class unexpectedly admitted candidate')
            local = out/form
            local.mkdir()
            (local/'load-span.bin').write_bytes(load)
            transformed = codec.bcj(load)
            payload = codec.fixed_compress(transformed)
            require(codec.fixed_decompress(payload, len(load)) == transformed and codec.bcj(transformed, inverse=True) == load,
                    'fixed codec roundtrip differs')
            result = packer.compile_loader(local/'whole', HERE/'packaging/loader', payload, recipe['layout'],
                                           recipe['loader_flags'], lambda command: run(command, out, environment), sha)
            require(result['payload_bytes'] == len(payload), 'payload accounting differs')
            row = {'form': form, 'native_bytes': len(native), 'native_sha256': sha(native), 'load_proof': proof,
                   'old_guards_rejected_without_changes': rejected, 'payload_bytes': len(payload), 'payload_sha256': sha(payload),
                   'bytes': result['bytes'], 'sha256': result['sha256'], 'path': result['path'],
                   'loader_and_headers_bytes': result['loader_and_headers_bytes'], 'reused_not_rebuilt': False,
                   'delta_to_literal_original_whole': result['bytes']-recipe['control_whole']['control-'+backend]['bytes']}
            report['forms'].append(row)
            save()
        require(len(report['commands']) == 2 and all(c['returncode'] == 0 and c['group_absent'] for c in report['commands']), 'loader tool count or settlement differs')
        report.update(complete=True, Rust_main_links=0, loader_links=2, reused_control_wholes=2,
                      one_fixed_codec_only=True, old_guards_or_loader_changed=False)
        save()
        print(json.dumps({'complete': True, 'out': str(out), 'forms': [{k: r[k] for k in ('form', 'bytes', 'sha256', 'reused_not_rebuilt')} for r in report['forms']]}))
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
