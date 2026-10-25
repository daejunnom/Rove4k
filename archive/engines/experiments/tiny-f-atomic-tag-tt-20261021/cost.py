#!/usr/bin/env python3
"""One F partial-tag atomic TT first cost; no engine or normal generation."""
import argparse
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import platform
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def normalized(path):
    data = path.read_bytes().replace(b'\r\n', b'\n')
    need(b'\r' not in data, 'lone CR in source input')
    return data


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def strict(whole, prefix, script):
    need(whole[:77] == prefix, 'prefix differs')
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    recovered = decoder.decompress(whole[77:])
    need(decoder.eof and not decoder.unused_data and recovered == script,
         'strict ALONE decode differs/trails/truncates')
    return {'eof': True, 'trailing_bytes': 0, 'bootstrap_sha256': sha(recovered)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    need(sys.platform == 'linux' and platform.machine() == 'x86_64'
         and args.out.is_absolute() and not out.exists()
         and not any((p/'.git').exists() for p in (out, *out.parents)),
         'new absolute x86-64 Linux output outside Git required')
    config = json.loads((HERE/'config.json').read_text())
    out.mkdir(parents=True)
    report = {'complete': False, 'scope': 'ONE F probabilistic partial-tag atomic TT first cost',
              'lossless_or_full_key_equivalence': False, 'source_inputs': {},
              'profile_macro_queries': 0, 'candidate_native_compile_attempts': 0,
              'candidate_native_compiles_completed': 0, 'candidate_packages': 0,
              'strict_pure_decodes': 0, 'control_compile_compress_copy': 0,
              'engine_DEV_game_benchmark_or_normal_generation': 0,
              'environment': 'inherited unchanged', 'native_cwd': str(out/'native'),
              'policy': {'index_bits': 18, 'tag_bits': 21, 'payload_bits': 43,
                         'random_tag_alias_conditional_on_slot': '2^-21 under uniform independent keys',
                         'random_pair_index_and_tag_alias': '2^-39 under uniform independent keys',
                         'constructed_collision': 'key and key XOR (1ULL<<18)',
                         'old_entry_bytes': 24, 'candidate_entry_bytes_fixed_ABI': 8,
                         'slots': 262144, 'old_table_bytes': 6291456,
                         'candidate_table_bytes_fixed_ABI': 2097152,
                         'runtime_lock_free_check_executed': False}}

    def save():
        (out/'cost.json').write_text(json.dumps(report, indent=2)+'\n')

    save()
    try:
        for name in ('transform.py', 'config.json', 'cost.py', 'README.md'):
            data = normalized(HERE/name)
            report['source_inputs'][name] = {'bytes': len(data), 'sha256': sha(data)}
        need(report['source_inputs']['transform.py']['sha256'] == config['transform_sha256'],
             'fixed transform differs')
        for relative, pin in config['helper_sha256'].items():
            data = normalized(REPO/relative)
            need(sha(data) == pin, 'pinned helper differs: '+relative)
            report['source_inputs'][relative] = {'bytes': len(data), 'sha256': sha(data)}
        baseline = {}
        for name, expected in config['baseline'].items():
            data = (Path(config['baseline_root'])/name).read_bytes()
            need(len(data) == expected['bytes'] and sha(data) == expected['sha256'],
                 'baseline differs: '+name)
            baseline[name] = data
        need(json.loads(baseline['build.json'])['complete'], 'baseline build incomplete')
        producing = json.loads(baseline['inputs/recipe.json'])
        current = json.loads(normalized(REPO/config['entry']/'recipe.json'))
        for key in ('compiler', 'compression', 'profile', 'expected'):
            need(producing[key] == current[key] == config[key], 'fixed family setting differs: '+key)
        report['baseline_reused_read_only'] = config['baseline']
        # Query fixed target ABI/atomic macros, not a second native candidate.
        command = list(config['compiler'])
        index = command.index('-o')
        del command[index:index+2]
        command += ['-dM', '-E']
        headers = b'#include <stdint.h>\n#include <stdatomic.h>\n'
        report['profile_macro_queries'] = 1
        observed = subprocess.run(command, input=headers, capture_output=True, timeout=15)
        (out/'profile.macros').write_bytes(observed.stdout)
        (out/'profile.stderr').write_bytes(observed.stderr)
        need(observed.returncode == 0, 'fixed profile macro query failed')
        macros = {}
        for line in observed.stdout.decode().splitlines():
            if line.startswith('#define '):
                pieces = line.split(None, 2)
                if len(pieces) == 3:
                    macros[pieces[1]] = pieces[2]
        required = {'__linux__': '1', '__x86_64__': '1', '__SIZEOF_POINTER__': '8',
                    '__SIZEOF_LONG__': '8', '__SIZEOF_LONG_LONG__': '8',
                    '__UINT64_TYPE__': 'long unsigned int',
                    '__GCC_ATOMIC_LONG_LOCK_FREE': '2', '__GCC_ATOMIC_LLONG_LOCK_FREE': '2'}
        need(all(macros.get(name) == value for name, value in required.items()),
             'fixed 64-bit unsigned-long always-lock-free profile not observed')
        report['profile_observation'] = {'command': command, 'returncode': observed.returncode,
                                         'required_macros': required, 'macro_sha256': sha(observed.stdout),
                                         'shipping_assertions_added': False,
                                         'scope': 'fixed GCC Linux LP64 uint64_t always-lock-free macros; no runtime execution'}
        transform = module('fixed_F_atomic_tag_TT', HERE/'transform.py').transform
        literal = module('existing_source_literal', REPO/'engines/compact/tiny-a/pack_stream.py').source_literal
        template = normalized(REPO/config['entry']/'bootstrap.py.in')
        prefix = normalized(REPO/config['entry']/'launcher.sh')
        marker = b'__ROVE_SOURCE_LITERAL__'
        need(len(prefix) == 77 and template.count(marker) == 1, 'bootstrap geometry differs')
        expression, _ = literal(baseline['main.c'])
        old_script = template.replace(marker, expression.encode())
        need(old_script == baseline['bootstrap.py'], 'baseline bootstrap reconstruction differs')
        report['baseline_decode'] = strict(baseline['x'], prefix, old_script)
        report['strict_pure_decodes'] = 1
        candidate, report['transformation'] = transform(baseline['main.c'])
        (out/'main.c').write_bytes(candidate)
        expression, kind = literal(candidate)
        script = template.replace(marker, expression.encode())
        (out/'bootstrap.py').write_bytes(script)
        report.update(source_bytes=len(candidate), source_sha256=sha(candidate),
                      bootstrap_bytes=len(script), bootstrap_sha256=sha(script), literal_kind=kind)
        directory = out/'native'
        directory.mkdir()
        report['candidate_native_compile_attempts'] = 1
        report['compiler'] = config['compiler']
        save()
        built = subprocess.run(config['compiler'], input=candidate, cwd=directory,
                               capture_output=True, timeout=90)
        (directory/'compiler.stdout').write_bytes(built.stdout)
        (directory/'compiler.stderr').write_bytes(built.stderr)
        report.update(compiler_returncode=built.returncode, compiler_terminal=True)
        need(built.returncode == 0, 'candidate native compiler failed')
        native = (directory/'x').read_bytes()
        need(native[:5] == b'\x7fELF\x02' and int.from_bytes(native[18:20], 'little') == 62,
             'candidate is not ELF64 x86-64')
        report.update(candidate_native_compiles_completed=1, native_bytes=len(native),
                      native_sha256=sha(native), native_equal_to_old=native == baseline['native/x'])
        need(config['compression']['nice_len'] == 32, 'fixed F nice_len differs')
        report['candidate_packages'] = 1
        payload = lzma.compress(script, format=lzma.FORMAT_ALONE, check=lzma.CHECK_NONE,
                                filters=[{'id': lzma.FILTER_LZMA1, 'preset': 9|lzma.PRESET_EXTREME,
                                          'lc': 2, 'lp': 0, 'pb': 0, 'mf': lzma.MF_BT4,
                                          'dict_size': 67108864, 'nice_len': 32}])
        need(payload[:13] == baseline['x'][77:90], 'fixed ALONE header differs')
        whole = prefix+payload
        (out/'x').write_bytes(whole)
        (out/'x').chmod(0o755)
        report['candidate_decode'] = strict(whole, prefix, script)
        report.update(strict_pure_decodes=2, whole_bytes=len(whole), whole_sha256=sha(whole),
                      whole_delta=len(whole)-len(baseline['x']), complete=True)
        save()
        print(json.dumps({key: report[key] for key in ('complete', 'source_bytes', 'source_sha256',
                          'native_bytes', 'native_sha256', 'whole_bytes', 'whole_sha256', 'whole_delta')}))
    except Exception as error:
        report['error'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
