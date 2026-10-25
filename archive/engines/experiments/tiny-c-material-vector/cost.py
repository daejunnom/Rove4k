#!/usr/bin/env python3
"""One C shared-vector native compile and fixed ALONE package; no engine run."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    need(sys.platform == 'linux' and args.out.is_absolute() and not out.exists()
         and not any((p/'.git').exists() for p in (out, *out.parents)),
         'new absolute Linux output outside Git required')
    recipe = json.loads((HERE/'recipe.json').read_text())
    out.mkdir(parents=True)
    report = {'complete': False, 'scope': 'one fixed C shared-vector first cost',
              'native_compile_attempts': 0, 'native_compiles_completed': 0,
              'candidate_compressions': 0, 'strict_pure_decodes': 0,
              'control_compile_or_compression': 0, 'C_AST_or_PP': 0,
              'engine_DEV_game_benchmark_runs': 0, 'baseline_copies': 0,
              'compiler_terminal': False, 'environment': 'inherited unchanged',
              'cwd': str(out/'native'), 'source_inputs': {}}

    def save():
        (out/'cost.json').write_text(json.dumps(report, indent=2)+'\n')

    save()
    try:
        for name in ('transform.py', 'cost.py', 'recipe.json', 'README.md'):
            data = normalized(HERE/name)
            report['source_inputs'][name] = {'bytes': len(data), 'sha256': sha(data)}
        need(report['source_inputs']['transform.py']['sha256'] == recipe['transform_sha256'],
             'fixed transform differs')
        for relative, pin in recipe['helper_sha256'].items():
            data = normalized(REPO/relative)
            need(sha(data) == pin, 'helper differs: '+relative)
            report['source_inputs'][relative] = {'bytes': len(data), 'sha256': sha(data)}
        baseline = {}
        for name, expected in recipe['baseline'].items():
            data = (args.baseline/name).read_bytes()
            need(len(data) == expected['bytes'] and sha(data) == expected['sha256'],
                 'baseline differs: '+name)
            baseline[name] = data
        need(json.loads(baseline['build.json'])['complete'], 'baseline receipt incomplete')
        report['baseline_reused_read_only'] = recipe['baseline']
        current = json.loads(normalized(REPO/'engines/compact/tiny-entry-c/recipe.json'))
        need(current['compiler'] == recipe['compiler'] and current['compression'] == recipe['compression'],
             'normal compiler/compression differs')
        transformer = module('fixed_C_material_vector', HERE/'transform.py')
        literal = module('existing_source_literal', REPO/'engines/compact/tiny-a/pack_stream.py').source_literal
        template = normalized(REPO/'engines/compact/tiny-entry-c/bootstrap.py.in')
        prefix = normalized(REPO/'engines/compact/tiny-entry-c/launcher.sh')
        marker = b'__ROVE_SOURCE_LITERAL__'
        need(template.count(marker) == 1 and len(prefix) == 77, 'bootstrap geometry differs')
        old_expression, _ = literal(baseline['main.c'])
        need(template.replace(marker, old_expression.encode()) == baseline['bootstrap.py'],
             'baseline bootstrap reconstruction differs')
        candidate, report['transformation'] = transformer.transform(baseline['main.c'])
        (out/'main.c').write_bytes(candidate)
        expression, kind = literal(candidate)
        script = template.replace(marker, expression.encode())
        (out/'bootstrap.py').write_bytes(script)
        report.update(source_bytes=len(candidate), source_sha256=sha(candidate),
                      bootstrap_bytes=len(script), bootstrap_sha256=sha(script), literal_kind=kind)
        native_dir = out/'native'
        native_dir.mkdir()
        report['native_compile_attempts'] = 1
        report['compiler_argv'] = recipe['compiler']
        save()
        completed = subprocess.run(recipe['compiler'], input=candidate, cwd=native_dir,
                                   capture_output=True, timeout=90)
        (native_dir/'compiler.stdout').write_bytes(completed.stdout)
        (native_dir/'compiler.stderr').write_bytes(completed.stderr)
        report.update(compiler_returncode=completed.returncode, compiler_terminal=True)
        need(completed.returncode == 0, 'candidate compiler failed')
        native = (native_dir/'x').read_bytes()
        report.update(native_compiles_completed=1, native_bytes=len(native), native_sha256=sha(native),
                      native_equal_to_old=native == baseline['native/x'])
        report['candidate_compressions'] = 1
        packed = lzma.compress(script, format=lzma.FORMAT_ALONE, check=lzma.CHECK_NONE,
                               filters=[{'id': lzma.FILTER_LZMA1, 'preset': 9|lzma.PRESET_EXTREME,
                                         'lc': 2, 'lp': 0, 'pb': 0, 'mf': lzma.MF_BT4,
                                         'dict_size': 67108864, 'nice_len': 64}])
        whole = prefix+packed
        (out/'x').write_bytes(whole)
        (out/'x').chmod(0o755)
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
        unpacked = decoder.decompress(whole[77:])
        need(whole[:77] == prefix and decoder.eof and not decoder.unused_data and unpacked == script,
             'strict ALONE decode differs/trails/truncates')
        report.update(strict_pure_decodes=1, strict_decode_equal=True, trailing_bytes=0,
                      whole_bytes=len(whole), whole_sha256=sha(whole),
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
