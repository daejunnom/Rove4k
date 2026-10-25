#!/usr/bin/env python3
"""Measure one shipping precondition specialization, with the fixed 5223 B recipe.

No source, compiler, identifier, bootstrap or encoding search.  The exact
qualified readable/source/native/whole/DEV control must reproduce first.
"""
import argparse
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
CONTROL_BUILD_SHA256 = 'fa4587ce3af610e04edff071e5976b2fdb638f2c163701d21dbe61de34c907f2'
CONTROL = {
    'readable_sha256': '38d6c829a4d98a172b01c945a20e091bd529a5998174896dbf0ad2dbc01a0a7b',
    'source_sha256': 'b70dce2bd28834f6218b72e255ee5689028ab187be91bf2df661c6c48af55092',
    'native_sha256': '60797c218437055bdc56a46e9ff37d9007ba39e547bccccfa36d8f5acb9cb430',
    'whole_sha256': 'fbb416160e98beb8f10cc5fec6b3792f4591055626344dcbe31cb50ffce41ee9',
    'dev_source_sha256': '8a0985aad0b1514aa78a6aafc59c0fc1cc511d1b06a441bab91a404cdd98a477',
    'dev_native_sha256': 'dad84ccaa35f6c9d7860b1bd39d283f8bdb7d5a1c74ec6c25615e443376974ce',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or any((p / '.git').exists() for p in (args.out, *args.out.parents)):
        parser.error('a new absolute output outside Git is required')
    args.out.mkdir(parents=True)
    recipe = args.out / 'recipe'
    recipe.mkdir()
    report = {'complete': False, 'scope': 'one shipping-only legal-startpos-history precondition specialization',
              'inputs': {}, 'engines': [], 'resources': {'search_workers': 2, 'startup_threads': 3, 'tt_bits': 18},
              'compiler_command': ['cc', '-Os', '-x', 'c', '-', '-o', 'x', '-s'],
              'no_setting_or_identifier_sweep': True, 'shared_validator_modified': False}
    started = time.monotonic()
    deadline = started + 240

    def save():
        (args.out / 'build.json').write_text(json.dumps(report, indent=2) + '\n')

    def freeze(label, path, expected):
        data = path.read_bytes()
        if sha(data) != expected:
            raise ValueError('frozen input mismatch: ' + str(path))
        (recipe / label).write_bytes(data)
        report['inputs'][label] = {'sha256': sha(data), 'bytes': len(data)}
        return data

    def run(command, cwd, input=None, timeout=90):
        remaining = min(timeout, deadline - time.monotonic())
        if remaining <= 0:
            raise TimeoutError('aggregate build deadline')
        process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = process.communicate(input=input, timeout=remaining)
            if process.returncode:
                (cwd / 'compiler-error.txt').write_bytes(stderr)
                raise RuntimeError('compile failed; exact stderr retained: ' + str(cwd))
            return stdout
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            if process.poll() is None:
                process.wait(timeout=3)

    save()
    try:
        raw = freeze('control-build.json', args.control / 'build.json', CONTROL_BUILD_SHA256)
        previous = json.loads(raw)
        old = next(row for row in previous['engines'] if row['id'] == 'minimal')
        if any(old[key] != digest for key, digest in CONTROL.items()) or old['whole_bytes'] != 5223:
            raise ValueError('unexpected qualified control record')
        # The previously frozen producer supplies only pure source/packaging
        # helpers; its main() and policy transform are never invoked.
        helper_digest = previous['inputs']['policy/build.py']['sha256']
        freeze('control-producer.py', args.control / 'recipe/build.py', helper_digest)
        helper = module('preconditions_control_helpers', recipe / 'control-producer.py')
        for name, digest in helper.PINS.items():
            freeze(name, args.control / 'recipe' / name, digest)
        readable = freeze('control-readable.c', Path(old['readable']), CONTROL['readable_sha256'])
        freeze('control-source.c', Path(old['source']), CONTROL['source_sha256'])
        freeze('control-native', Path(old['native']), CONTROL['native_sha256'])
        wrapper = freeze('control-wrapper', Path(old['command'][0]), CONTROL['whole_sha256'])
        for name in ('build.py', 'transform.py'):
            data = (HERE / name).read_bytes()
            (recipe / ('preconditions-' + name)).write_bytes(data)
            report['inputs']['preconditions-' + name] = {'bytes': len(data), 'sha256': sha(data)}
        transform = module('preconditions_transform', recipe / 'preconditions-transform.py').transform
        specialize = helper.module('preconditions_specialize', recipe / 'specialize.py').specialize_c
        compact = helper.module('preconditions_compact', recipe / 'minify.py').compact_source
        strip = helper.module('preconditions_counters', recipe / 'stitch.py').strip_dev_counters
        lexer = helper.module('preconditions_rename', recipe / 'rename_c.py')
        literal = helper.module('preconditions_literal', recipe / 'pack_stream.py').source_literal
        spelling = json.loads((recipe / 'a-search-rename.json').read_text())
        trials = [x for x in spelling['rename']['trials'] if x['status'] == 'accepted' and x['trial'] <= spelling['selected']['trial']]
        encoding = json.loads((recipe / 'a-encoding.json').read_text())
        selected = next(x for x in encoding['records'] if x['case'] == 'combined-fixed-stripped')
        if selected['command'] != report['compiler_command']:
            raise ValueError('unexpected frozen compiler command')
        offset = wrapper.index(b'\xfd7zXZ\0')
        prefix, bootstrap = wrapper[:offset], lzma.decompress(wrapper[offset:])
        begin, end = helper.source_argument(bootstrap)
        filters = [{'id': lzma.FILTER_LZMA2, 'preset': 9 | lzma.PRESET_EXTREME, 'lc': 2, 'lp': 0, 'pb': 0}]
        report['tools'] = {name: run(command, args.out).decode().splitlines()[0] for name, command in {
            'cc': ['cc', '--version'], 'ld': ['ld', '--version'], 'python3': ['python3', '--version'], 'xz': ['xz', '--version']}.items()}
        report['wrapper'] = {'prefix_bytes': len(prefix), 'prefix_sha256': sha(prefix),
                             'compression': 'unchanged XZ LZMA2 preset9 extreme lc2 lp0 pb0 CRC64',
                             'restoration': 'unchanged compiler-process-group/signal/fdexec cleanup bootstrap, replacing only source argument'}

        def generate(combined, directory, dev=False):
            active, _ = specialize({'main.c': combined}, directory,
                                   ['cc', '-std=c11', '-Os', '-pthread', '-DWORKERS=2', '-DTT_BITS=18', '-DDEV=' + str(int(dev))], os.environ.copy())
            source = compact(active['main.c'], 'c')
            if dev:
                return source
            source, _ = strip(source)
            files = {'main.c': source}
            for trial in trials:
                files = lexer._replace(files, trial['identifier'], trial['replacement'])
            for name, value in {'WORKERS': '2', 'TT_BITS': '18'}.items():
                files = lexer._replace(files, name, value)
            for name, alias in selected['manual_function_spellings'].items():
                files = lexer._replace(files, name, alias)
            return files['main.c']

        def package(source):
            expression, _ = literal(source)
            script = bootstrap[:begin] + expression.encode() + bootstrap[end:]
            return prefix + lzma.compress(script, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, filters=filters), script

        candidate, omitted = transform(readable)
        report['omitted_shipping_guards'] = omitted
        reference_dev = reference_dev_native = None
        for name, combined in (('control', readable), ('specialized', candidate)):
            directory = args.out / name
            directory.mkdir()
            (directory / 'combined.c').write_bytes(combined)
            source = generate(combined, directory / 'preprocess-first')
            repeat = generate(combined, directory / 'preprocess-second')
            if source != repeat:
                raise ValueError('source generation did not reproduce')
            (directory / 'main.c').write_bytes(source)
            native_dir = directory / 'native'
            native_dir.mkdir()
            run(report['compiler_command'], native_dir, input=source)
            native = (native_dir / 'x').read_bytes()
            run(report['compiler_command'], native_dir, input=repeat)
            if native != (native_dir / 'x').read_bytes():
                raise ValueError('native bytes did not reproduce')
            packed, script = package(source)
            repeat_packed, repeat_script = package(repeat)
            if packed != repeat_packed or script != repeat_script:
                raise ValueError('whole file did not reproduce')
            wrapper_dir = directory / 'wrapper'
            wrapper_dir.mkdir()
            target = wrapper_dir / 'x'
            target.write_bytes(packed)
            target.chmod(0o755)
            (directory / 'bootstrap.py').write_bytes(script)
            dev = generate(combined, directory / 'preprocess-dev', dev=True)
            dev_dir = directory / 'dev'
            dev_dir.mkdir()
            (dev_dir / 'main.c').write_bytes(dev)
            run(['cc', '-Os', '-pthread', '-DWORKERS=2', '-DTT_BITS=18', '-x', 'c', '-', '-o', 'x'], dev_dir, input=dev)
            dev_native = (dev_dir / 'x').read_bytes()
            if reference_dev is None:
                reference_dev, reference_dev_native = dev, dev_native
            elif dev != reference_dev or dev_native != reference_dev_native:
                raise ValueError('DEV source or native bytes changed')
            actual_begin, actual_end = helper.source_argument(script)
            if helper.restore_literal(script[actual_begin:actual_end]) != source:
                raise ValueError('actual executable bootstrap source restoration mismatch')
            record = {'id': name, 'profile': 'shipping', 'workers': 2, 'startup_threads': 3, 'max_threads': 3,
                      'startup_timeout': 60, 'command': [str(target)], 'native': str(native_dir / 'x'), 'dev': str(dev_dir / 'x'),
                      'readable': str(directory / 'combined.c'), 'source': str(directory / 'main.c'),
                      'source_bytes': len(source), 'source_sha256': sha(source), 'readable_sha256': sha(combined),
                      'native_bytes': len(native), 'native_sha256': sha(native), 'whole_bytes': len(packed),
                      'whole_sha256': sha(packed), 'expected_program_sha256': sha(packed), 'bootstrap_sha256': sha(script),
                      'dev_source_sha256': sha(dev), 'dev_native_sha256': sha(dev_native),
                      'source_reproduced': True, 'native_reproduced': True, 'whole_reproduced': True,
                      'source_restored_exactly': True, 'compile': report['compiler_command'], 'under_4096_bytes': len(packed) <= 4096}
            if name == 'control' and (any(record[key] != digest for key, digest in CONTROL.items()) or packed != wrapper):
                raise ValueError('qualified exact control did not reproduce')
            report['engines'].append(record)
            save()
            print(json.dumps(record), flush=True)
        report['dev_exactly_unchanged'] = True
        report['delta'] = {key: report['engines'][1][key] - report['engines'][0][key] for key in ('source_bytes', 'native_bytes', 'whole_bytes')}
        report['complete'] = True
    except Exception as error:
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        report['elapsed_seconds'] = time.monotonic() - started
        save()


if __name__ == '__main__':
    main()
