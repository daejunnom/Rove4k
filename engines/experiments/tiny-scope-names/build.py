"""Bounded F5051 scope-name proof: two source/native/original-codec attempts."""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--source-root', default=REPO, type=Path)
    parser.add_argument('--clang-site', required=True, type=Path)
    parser.add_argument('--resource-dir', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if (not args.out.is_absolute() or out.exists() or
            any((p / '.git').exists() for p in (out, *out.parents))):
        parser.error('new absolute output outside Git required')
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        parser.error('the bounded target is qualified Linux x86-64')
    admission = json.loads((HERE / 'inputs.json').read_bytes())
    if admission['family'] != 'F' or admission['baseline']['whole_bytes'] != 5051:
        raise ValueError('unknown fixed campaign')
    out.mkdir()
    ordinary = out / 'ordinary'
    producer = out / 'producer'
    producer.mkdir()
    report = {'complete': False, 'scope': 'one function-wide automatic-name policy, F5051 only',
              'ordinary_inputs': {}, 'producer_inputs': {}, 'attempts': [],
              'engine_runs': 0, 'native_compiles': 0, 'codec': 'unchanged original XZ'}

    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')

    save()
    try:
        for relative, pin in admission['ordinary_inputs'].items():
            path = args.source_root / relative
            raw = path.read_bytes()
            data = raw.replace(b'\r\n', b'\n')
            if b'\r' in data or sha(data) != pin:
                raise ValueError('ordinary input changed: ' + relative)
            target = ordinary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            report['ordinary_inputs'][relative] = {'bytes': len(data), 'sha256': sha(data),
                                                   'raw_sha256': sha(raw)}
        for name in ('build.py', 'rename.py', 'inputs.json'):
            data = (HERE / name).read_bytes()
            (producer / name).write_bytes(data)
            report['producer_inputs'][name] = {'bytes': len(data), 'sha256': sha(data)}
        for relative, pin in admission['clang_site_inputs'].items():
            if sha((args.clang_site / relative).read_bytes()) != pin:
                raise ValueError('external Clang tool input changed: ' + relative)
        if sha((args.resource_dir / 'include/stdatomic.h').read_bytes()) != admission['stdatomic_sha256']:
            raise ValueError('real Clang resource header changed')
        report['AST_tool'] = {'site': str(args.clang_site), 'resource_dir': str(args.resource_dir),
                              'pinned_inputs': admission['clang_site_inputs'],
                              'native_recipe_flags_changed': False}
        entry = ordinary / 'engines/compact/tiny-entry-f'
        recipe = json.loads((entry / 'recipe.json').read_bytes())
        if recipe['expected'] != admission['baseline']:
            raise ValueError('fixed normal F baseline differs')
        specialize = module('scope_specialize', ordinary / 'engines/scripts/specialize.py').specialize_c
        compact = module('scope_compact', ordinary / 'engines/scripts/minify.py').compact_source
        lexer = module('scope_lexer', ordinary / 'engines/scripts/rename_c.py')
        literal = module('scope_literal', ordinary / 'engines/compact/tiny-a/pack_stream.py').source_literal
        strip = module('scope_F_normal', entry / 'build.py').strip_counters
        alpha = module('scope_F_alpha', entry / 'shipping_alpha.py').transform_source
        storage = module('scope_F_storage', entry / 'shipping_storage.py').transform_source
        rename = module('scope_independent_rename', producer / 'rename.py').rewrite
        canonical = (entry / 'engine.c').read_bytes()
        template = (entry / 'bootstrap.py.in').read_bytes()
        prefix = (entry / 'launcher.sh').read_bytes()
        if len(prefix) != 75 or template.count(b'__ROVE_SOURCE_LITERAL__') != 1:
            raise ValueError('fixed original transport changed')

        def package(source):
            expression, _ = literal(source)
            script = template.replace(b'__ROVE_SOURCE_LITERAL__', expression.encode())
            ast.parse(script)
            payload = lzma.compress(script, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64,
                filters=[{'id': lzma.FILTER_LZMA2, 'preset': 9 | lzma.PRESET_EXTREME,
                          'lc': 2, 'lp': 0, 'pb': 0}])
            decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
            if decoder.decompress(payload) != script or not decoder.eof or decoder.unused_data:
                raise ValueError('strict original-codec decode differs')
            return prefix + payload, script

        first = None
        for attempt in (1, 2):
            directory = out / ('attempt-' + str(attempt))
            directory.mkdir()
            active, observations = specialize({'main.c': canonical}, directory / 'conditional',
                recipe['preprocessor'] + ['-DDEV=0'], os.environ.copy())
            source, counters = strip(compact(active['main.c'], 'c'))
            files = {'main.c': source}
            for old, new in recipe['resource_literals']:
                count = sum(token == old for _, _, token in lexer._identifier_spans(files['main.c'].decode()))
                if count != recipe['resource_token_counts'][old]:
                    raise ValueError('normal resource count differs')
                files = lexer._replace(files, old, new)
            for old, new in recipe['function_spellings']:
                files = lexer._replace(files, old, new)
            source, _ = alpha(files['main.c'], family='F', lexer=lexer, readable=canonical)
            source, _ = storage(source, family='F', readable=canonical)
            if sha(source) != admission['baseline']['source_sha256']:
                raise ValueError('ordinary normal source did not reproduce')
            (directory / 'baseline.c').write_bytes(source)
            original, original_script = package(source)
            if sha(original) != admission['baseline']['whole_sha256'] or sha(original_script) != admission['baseline']['bootstrap_sha256']:
                raise ValueError('original normal package did not reproduce')
            candidate, metadata = rename(source, clang_site=args.clang_site,
                resource_dir=args.resource_dir, arguments=['-std=gnu17', '-Os', '-pthread'])
            (directory / 'main.c').write_bytes(candidate)
            (directory / 'offsets.json').write_text(json.dumps(metadata, indent=2) + '\n')
            row = {'attempt': attempt, 'source_bytes': len(candidate), 'source_sha256': sha(candidate),
                   'baseline_source_bytes': len(source), 'renamed_declarations': metadata['renamed_declarations'],
                   'preprocessor': observations, 'counter_strip': counters}
            report['attempts'].append(row)
            save()
            print(json.dumps({'stage': 'source', **{k: row[k] for k in ('attempt', 'source_bytes', 'source_sha256', 'renamed_declarations')}}), flush=True)
            native_dir = directory / 'native'
            native_dir.mkdir()
            process = subprocess.run(recipe['compiler'], input=candidate, cwd=native_dir,
                                     capture_output=True, timeout=90)
            report['native_compiles'] += 1
            (native_dir / 'compiler.stdout').write_bytes(process.stdout)
            (native_dir / 'compiler.stderr').write_bytes(process.stderr)
            if process.returncode:
                raise ValueError('final compiler failed; output preserved')
            native = (native_dir / 'x').read_bytes()
            row.update(native_bytes=len(native), native_sha256=sha(native))
            save()
            if sha(native) != admission['baseline']['native_sha256']:
                raise ValueError('complete native inequality; no metadata exception or automatic relaxation')
            whole, script = package(candidate)
            (directory / 'x').write_bytes(whole)
            (directory / 'bootstrap.py').write_bytes(script)
            row.update(whole_bytes=len(whole), whole_sha256=sha(whole), bootstrap_sha256=sha(script),
                       full_old_native_equal=True)
            current = candidate, native, whole, script
            if first is None:
                first = current
            elif first != current:
                raise ValueError('two independent source/native/whole tuples differ')
            save()
            print(json.dumps({'stage': 'whole', 'attempt': attempt, 'whole_bytes': len(whole),
                              'whole_sha256': sha(whole), 'native_exact': True}), flush=True)
        for name, data in zip(('main.c', 'native/x', 'x', 'bootstrap.py'), first):
            path = out / 'selected' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        report.update(complete=True, independent_source_native_whole_equal=True,
                      full_old_native_equal=True, source_bytes=len(first[0]), source_sha256=sha(first[0]),
                      native_sha256=sha(first[1]), whole_bytes=len(first[2]), whole_sha256=sha(first[2]),
                      bootstrap_sha256=sha(first[3]), whole_saved_bytes=5051-len(first[2]),
                      all_owned_commands_terminal=True)
        save()
        print(json.dumps({'complete': True, 'out': str(out), 'source_bytes': len(first[0]),
                          'whole_bytes': len(first[2]), 'native_exact': True}), flush=True)
    except BaseException as error:
        report['error'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
