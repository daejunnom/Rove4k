#!/usr/bin/env python3
"""A/F one fixed packed-HCE cost each; no normal generation or engine run."""
import argparse
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
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
    restored = decoder.decompress(whole[77:])
    need(decoder.eof and not decoder.unused_data and restored == script,
         'strict ALONE decode differs/trails/truncates')
    return {'format': 'ALONE', 'eof': True, 'trailing_bytes': 0,
            'bootstrap_exact': True, 'bootstrap_sha256': sha(restored)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    need(sys.platform == 'linux' and args.out.is_absolute() and not out.exists()
         and not any((p/'.git').exists() for p in (out, *out.parents)),
         'new absolute Linux output outside Git required')
    config = json.loads((HERE/'config.json').read_text())
    out.mkdir(parents=True)
    report = {'complete': False, 'scope': 'one uncombined fixed packed-HCE A/F cost each',
              'native_compile_attempts': 0, 'native_compiles_completed': 0,
              'candidate_compressions': 0, 'strict_pure_decodes': 0,
              'control_compiles_compressions_copies': 0, 'AST_PP_DEV_engine_game_benchmark': 0,
              'normal_source_changes_or_builder_calls': 0, 'D_compile_or_package': 0,
              'source_inputs': {}, 'families': {}}

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
        transform = module('fixed_AF_packed_HCE', HERE/'transform.py').transform
        literal = module('existing_source_literal', REPO/'engines/compact/tiny-a/pack_stream.py').source_literal
        for family in ('A', 'F'):
            fixed = config['families'][family]
            baseline_root = Path(fixed['baseline_root'])
            baseline = {}
            for name, expected in fixed['baseline'].items():
                data = (baseline_root/name).read_bytes()
                need(len(data) == expected['bytes'] and sha(data) == expected['sha256'],
                     'baseline differs: '+family+'/'+name)
                baseline[name] = data
            need(json.loads(baseline['build.json'])['complete'], 'baseline normal receipt incomplete')
            producing = json.loads(baseline['inputs/recipe.json'])
            current = json.loads(normalized(REPO/fixed['entry']/'recipe.json'))
            for key in ('compiler', 'compression', 'profile', 'expected'):
                need(current[key] == producing[key] == fixed[key], 'family settings differ: '+key)
            directory = out/family
            directory.mkdir()
            row = {'baseline_read_only': fixed['baseline'], 'baseline_root': str(baseline_root),
                   'compiler': fixed['compiler'], 'compression': fixed['compression'],
                   'native_compile_attempts': 0, 'candidate_compressions': 0,
                   'environment': 'inherited unchanged', 'cwd': str(directory/'native')}
            report['families'][family] = row
            template = normalized(REPO/fixed['entry']/'bootstrap.py.in')
            prefix = normalized(REPO/fixed['entry']/'launcher.sh')
            marker = b'__ROVE_SOURCE_LITERAL__'
            need(len(prefix) == 77 and template.count(marker) == 1, 'bootstrap geometry differs')
            old_expression, _ = literal(baseline['main.c'])
            old_script = template.replace(marker, old_expression.encode())
            need(old_script == baseline['bootstrap.py'], 'baseline bootstrap reconstruction differs')
            row['baseline_decode'] = strict(baseline['x'], prefix, old_script)
            report['strict_pure_decodes'] += 1
            candidate, row['transformation'] = transform(baseline['main.c'], family)
            (directory/'main.c').write_bytes(candidate)
            expression, kind = literal(candidate)
            script = template.replace(marker, expression.encode())
            (directory/'bootstrap.py').write_bytes(script)
            row.update(source_bytes=len(candidate), source_sha256=sha(candidate),
                       bootstrap_bytes=len(script), bootstrap_sha256=sha(script), literal_kind=kind)
            native_dir = directory/'native'
            native_dir.mkdir()
            row['native_compile_attempts'] = 1
            report['native_compile_attempts'] += 1
            save()
            built = subprocess.run(fixed['compiler'], input=candidate, cwd=native_dir,
                                   capture_output=True, timeout=90)
            (native_dir/'compiler.stdout').write_bytes(built.stdout)
            (native_dir/'compiler.stderr').write_bytes(built.stderr)
            row.update(compiler_returncode=built.returncode, compiler_terminal=True)
            need(built.returncode == 0, 'candidate compiler failed: '+family)
            native = (native_dir/'x').read_bytes()
            report['native_compiles_completed'] += 1
            row.update(native_bytes=len(native), native_sha256=sha(native),
                       native_equal_to_old=native == baseline['native/x'])
            filters = {'id': lzma.FILTER_LZMA1, 'preset': 9|lzma.PRESET_EXTREME,
                       'lc': 2, 'lp': 0, 'pb': 0}
            if family == 'F':
                filters.update(mf=lzma.MF_BT4, dict_size=67108864, nice_len=32)
            report['candidate_compressions'] += 1
            row['candidate_compressions'] = 1
            packed = lzma.compress(script, format=lzma.FORMAT_ALONE,
                                   check=lzma.CHECK_NONE, filters=[filters])
            need(packed[:13] == baseline['x'][77:90], 'fixed ALONE header differs')
            whole = prefix+packed
            (directory/'x').write_bytes(whole)
            (directory/'x').chmod(0o755)
            row['candidate_decode'] = strict(whole, prefix, script)
            report['strict_pure_decodes'] += 1
            row.update(whole_bytes=len(whole), whole_sha256=sha(whole),
                       whole_delta=len(whole)-len(baseline['x']), complete=True)
            save()
            print(json.dumps({'family': family, **{key: row[key] for key in
                             ('source_bytes', 'source_sha256', 'native_bytes', 'native_sha256',
                              'whole_bytes', 'whole_sha256', 'whole_delta')}}), flush=True)
        report['complete'] = True
        save()
    except Exception as error:
        report['error'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
