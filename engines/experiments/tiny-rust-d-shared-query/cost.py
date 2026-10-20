"""Four primary Rust links, then conditional fixed-class whole costs; no ELF run."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FILES = ('main.rs', 'board.rs', 'search.rs', 'runtime.rs', 'os.rs', 'link.ld', 'build.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


def module(name, path):
    raw = path.read_bytes()
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), result.__dict__)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('native', 'pack'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--rustc', default='/home/stemxstudio/.cargo/bin/rustc')
    parser.add_argument('--native-cost', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    require(sys.platform == 'linux' and platform.machine() == 'x86_64' and args.out.is_absolute() and
            not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)), 'new Linux output outside Git required')
    out.mkdir(parents=True)
    recipe_raw = (HERE/'recipe.json').read_bytes()
    recipe = json.loads(recipe_raw)
    report = {'complete': False, 'phase': args.phase, 'commands': [], 'forms': [], 'primary_Rust_links': 0,
              'extra_unstripped_or_repeat_links': 0, 'codec_calls': 0, 'loader_links': 0,
              'production_ELF_or_runtime_executions': 0, 'AST_PP_DEV_game_benchmark_executions': 0,
              'recipe_sha256': sha(recipe_raw), 'registered_handles': []}
    report_path = out/('native-cost.json' if args.phase == 'native' else 'whole-cost.json')
    active = None
    environment = {**os.environ, 'LC_ALL': 'C', 'TZ': 'UTC', 'SOURCE_DATE_EPOCH': '0',
                   'ROVE_WORKERS': '2', 'ROVE_TT_BITS': '18'}
    def save():
        report_path.write_text(json.dumps(report, indent=2)+'\n')
    def absent(pid):
        try:
            os.killpg(pid, 0)
            return False
        except ProcessLookupError:
            return True
    def partial(row, error, prefix):
        if isinstance(error, subprocess.TimeoutExpired):
            for name, value in (('stdout', error.output), ('stderr', error.stderr)):
                row[prefix+name] = value.decode(errors='replace') if isinstance(value, bytes) else value
    def cleanup(row):
        nonlocal active
        if active is None:
            return
        row['cleanup_attempted'] = True
        try:
            os.killpg(active.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except BaseException as error:
            row['cleanup_kill_error'] = repr(error)
        try:
            stdout, stderr = active.communicate(timeout=5)
            row.update(returncode=active.returncode, stdout=stdout, stderr=stderr, EOF_drained=True)
        except BaseException as error:
            partial(row, error, 'cleanup_partial_')
            row.update(cleanup_error=repr(error), EOF_drained=False)
        row['terminal'] = active.poll() is not None
        try:
            row['group_absent'] = absent(active.pid)
        except BaseException as error:
            row.update(group_absent=False, cleanup_inspection_error=repr(error))
        row['cleanup_complete'] = row['terminal'] and row['group_absent'] and row['EOF_drained']
        if row['cleanup_complete']:
            active = None
            report['registered_handles'] = []
    def run(command, cwd=None):
        nonlocal active
        row = {'command': command, 'cwd': str(cwd or out), 'pid': None, 'returncode': None}
        report['commands'].append(row)
        save()
        try:
            old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
            try:
                active = subprocess.Popen(command, cwd=cwd or out, env=environment, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
                    preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, old_mask))
                row['pid'] = active.pid
                report['registered_handles'] = [active.pid]
                save()
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
            stdout, stderr = active.communicate(timeout=120)
            row.update(returncode=active.returncode, stdout=stdout, stderr=stderr, EOF_drained=True,
                       terminal=True, group_absent=absent(active.pid))
            require(active.returncode == 0 and row['group_absent'], 'tool failed or group remains')
            active = None
            report['registered_handles'] = []
            return row
        except BaseException as error:
            row['error'] = {'type': type(error).__name__, 'message': str(error)}
            partial(row, error, 'first_partial_')
            save()
            cleanup(row)
            raise
        finally:
            save()
    def interrupted(signum, _frame):
        raise InterruptedError('signal '+str(signum))
    previous = {s: signal.signal(s, interrupted) for s in (signal.SIGINT, signal.SIGTERM)}
    save()
    try:
        for name, pin in recipe['source_sha256'].items():
            require(sha((HERE/name).read_bytes()) == pin, 'owned ordinary source changed: '+name)
        require(recipe['profile'] == {'workers': 2, 'tt_bits': 18, 'ply': 128} and
                not recipe['runtime_execution_authorized'], 'fixed profile/runtime boundary differs')
        packer = module('own_unchanged_packer', HERE/'packaging/packer.py')
        if args.phase == 'native':
            compiler = shutil.which(args.rustc)
            require(compiler is not None, 'fixed Rust compiler unavailable')
            version = run([compiler, '--version'])['stdout'].strip()
            require(version == recipe['compiler'], 'fixed Rust compiler version differs')
            producer = module('own_exact_query_composition', HERE/'producer.py')
            control = {name: (HERE/'control'/name).read_bytes() for name in FILES}
            candidate = producer.produce(control, recipe)
            report.update(compiler=version, source_transform_exact=True, raw_Rust_delta=recipe['raw_source_delta'])
            for kind, sources in (('control', control), ('candidate', candidate)):
                for backend in ('scalar', 'hq'):
                    form = kind+'-'+backend
                    local = out/form
                    local.mkdir()
                    for name, raw in sources.items():
                        (local/name).write_bytes(raw)
                    environment['ROVE_HQ'] = str(int(backend == 'hq'))
                    command = [compiler, '--remap-path-prefix', str(local)+'=.', *recipe['native_flags']]
                    report['primary_Rust_links'] += 1
                    compiled = run(command, local)
                    native = (local/'x').read_bytes()
                    row = {'form': form, 'path': str(local/'x'), 'bytes': len(native), 'sha256': sha(native),
                           'elf': packer.elf(native), 'compile_command': report['commands'].index(compiled),
                           'source_sha256': {name: sha(raw) for name, raw in sources.items()}}
                    report['forms'].append(row)
                    if kind == 'control':
                        expected = recipe['control_expected'][form]
                        require(len(native) == expected['bytes'] and sha(native) == expected['sha256'], 'fresh control native mismatch')
                    ph = run(['readelf', '-lW', str(local/'x')], local)['stdout']
                    sections = run(['readelf', '-SW', str(local/'x')], local)['stdout']
                    (local/'program_headers.txt').write_text(ph)
                    (local/'sections.txt').write_text(sections)
                    row['sections'] = {m[0]: {'type': m[1], 'address': int(m[2], 16), 'offset': int(m[3], 16), 'bytes': int(m[4], 16)}
                        for m in re.findall(r'\[\s*\d+\]\s+(\.\S+)\s+(\S+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)', sections)}
                    save()
            require(report['primary_Rust_links'] == 4, 'unexpected primary native link count')
            report.update(complete=True, next_phase='actual layout and separate literal identity admission before packing')
        else:
            require(args.native_cost is not None and 'packing' in recipe, 'literal native/layout packing review missing')
            native_raw = (args.native_cost/'native-cost.json').read_bytes()
            require(sha(native_raw) == recipe['packing']['native_cost_sha256'] and json.loads(native_raw)['complete'], 'native receipt differs/incomplete')
            admitted = module('new_literal_query_data8_class', HERE/'admit.py')
            old8 = module('unchanged_old_data8_guard', HERE/'reference/data8.py')
            old16 = module('unchanged_old_data16_guard', HERE/'reference/data16.py')
            codec = module('unchanged_fixed_codec', HERE/'packaging/loader/codec.py')
            require(admitted.CLASS == recipe['class'] and admitted.NATIVE == recipe['packing']['native_expected'], 'new literal class differs')
            require(codec.BCJ_VERSION == recipe['codec']['bcj_version'] and codec.FIXED_VERSION == recipe['codec']['fixed_version'], 'fixed codec differs')
            for kind in ('control', 'candidate'):
                for backend in ('scalar', 'hq'):
                    form = kind+'-'+backend
                    native = (args.native_cost/form/'x').read_bytes()
                    load, proof = admitted.admit(native, form, packer)
                    if kind == 'control':
                        oldload, _ = old8.admit(native, form, packer)
                        require(oldload == load, 'same original data8 control span differs')
                    else:
                        for old, oldform in ((old8, 'control-'+backend), (old16, backend)):
                            try:
                                old.admit(native, oldform, packer)
                            except ValueError as error:
                                require(str(error) == 'unknown original qualified Rust D native', 'unexpected original guard failure')
                            else:
                                raise ValueError('original guard unexpectedly admitted candidate')
                    local = out/form
                    local.mkdir()
                    (local/'load-span.bin').write_bytes(load)
                    report['codec_calls'] += 1
                    payload = codec.fixed_compress(codec.bcj(load))
                    decoded = codec.bcj(codec.fixed_decompress(payload, len(load)), inverse=True)
                    require(decoded == load and sha(decoded) == sha(load), 'strict fixed decode/inverse BCJ differs')
                    report['loader_links'] += 1
                    whole = packer.compile_loader(local/'whole', HERE/'packaging/loader', payload,
                        recipe['packing_layout'], recipe['loader_flags'], run, sha)
                    raw = Path(whole['path']).read_bytes()
                    require(packer.elf(raw)['section_offset'] == 0, 'whole loader section metadata remains')
                    if kind == 'control':
                        expected = recipe['packing']['control_whole_expected'][form]
                        require(len(raw) == expected['bytes'] and sha(raw) == expected['sha256'], 'fresh control whole differs')
                    report['forms'].append({'form': form, **whole, 'load_proof': proof,
                        'payload_sha256': sha(payload), 'strict_decoded_span_sha256': sha(decoded),
                        'whole_program_headers': packer.elf(raw), 'ELF_executed': False})
                    save()
            require(report['codec_calls'] == 4 and report['loader_links'] == 4, 'unexpected fixed packing count')
            report.update(complete=True, runtime_qualified=False)
        require((HERE/'recipe.json').read_bytes() == recipe_raw, 'recipe changed during bounded phase')
        for name, pin in recipe['source_sha256'].items():
            require(sha((HERE/name).read_bytes()) == pin, 'owned source changed during phase: '+name)
        print(json.dumps({'complete': report['complete'], 'phase': args.phase,
            'forms': [{k: r[k] for k in ('form', 'bytes', 'sha256')} for r in report['forms']]}))
    except BaseException as error:
        report.update(complete=False, error={'type': type(error).__name__, 'message': str(error)},
                      failure_policy='preserve and stop, no retry/variant/guard relaxation')
        raise
    finally:
        if active is not None:
            report['complete'] = False
            cleanup(report.setdefault('final_cleanup', {}))
        report['active_tool_present'] = active is not None
        save()
        for s, handler in previous.items():
            signal.signal(s, handler)


if __name__ == '__main__':
    main()
