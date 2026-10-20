"""One strict native/original-codec cost per admitted A/B/C/E shipping source."""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import platform
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
    parser.add_argument('--controls', required=True, type=Path)
    parser.add_argument('--source-root', default=REPO, type=Path)
    parser.add_argument('--clang-site', required=True, type=Path)
    parser.add_argument('--resource-dir', required=True, type=Path)
    parser.add_argument('--family', choices=('A', 'B', 'C', 'E'))
    args = parser.parse_args()
    out = args.out.resolve()
    if (not args.out.is_absolute() or out.exists() or
            any((p / '.git').exists() for p in (out, *out.parents))):
        parser.error('new absolute output outside Git required')
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        parser.error('admitted target is Linux x86-64')
    admission = json.loads((HERE / 'portfolio-inputs.json').read_bytes())
    tool = json.loads((HERE / 'inputs.json').read_bytes())
    for relative, pin in tool['clang_site_inputs'].items():
        if sha((args.clang_site / relative).read_bytes()) != pin:
            raise ValueError('external AST library input changed: ' + relative)
    if sha((args.resource_dir / 'include/stdatomic.h').read_bytes()) != tool['stdatomic_sha256']:
        raise ValueError('real Clang resource header changed')
    out.mkdir()
    producer = out / 'producer'
    producer.mkdir()
    report = {'complete': False, 'scope': 'one automatic-function-wide policy, one native/whole per A/B/C/E',
              'engine_runs': 0, 'native_compiles': 0, 'cases': {}, 'producer_inputs': {},
              'ordinary_inputs': {}, 'AST_tool': {'site': str(args.clang_site),
                  'resource_dir': str(args.resource_dir), 'library_pins': tool['clang_site_inputs'],
                  'stdatomic_sha256': tool['stdatomic_sha256']}}

    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')

    save()
    for name in ('portfolio.py', 'portfolio-inputs.json', 'rename.py', 'inputs.json'):
        raw = (HERE / name).read_bytes()
        (producer / name).write_bytes(raw)
        report['producer_inputs'][name] = {'bytes': len(raw), 'sha256': sha(raw)}
    rename = module('scope_portfolio_rename', producer / 'rename.py').rewrite
    sources = {}
    for relative, pin in admission['ordinary_inputs'].items():
        raw = (args.source_root / relative).read_bytes()
        data = raw.replace(b'\r\n', b'\n')
        if b'\r' in data or sha(data) != pin:
            raise ValueError('fixed ordinary input changed: ' + relative)
        sources[relative] = data
        report['ordinary_inputs'][relative] = {'bytes': len(data), 'sha256': sha(data), 'raw_sha256': sha(raw)}
    literal_path = args.source_root / 'engines/compact/tiny-a/pack_stream.py'
    literal = module('scope_portfolio_literal', literal_path).source_literal
    report['compiler_version'] = subprocess.run(['cc', '--version'], capture_output=True,
        text=True, check=True).stdout.splitlines()[0]
    save()
    for case in admission['cases']:
        family = case['family']
        if args.family is not None and family != args.family:
            continue
        directory = out / family
        directory.mkdir()
        row = {'complete': False, 'native_compiles': 0, 'engine_runs': 0}
        report['cases'][family] = row
        save()
        try:
            base = args.controls / case['control_directory']
            source = (base / 'main.c').read_bytes()
            script = (base / 'bootstrap.py').read_bytes()
            baseline_whole = (base / 'baseline/x').read_bytes()
            expected = case['baseline']
            if (len(source) != expected['source_bytes'] or sha(source) != expected['source_sha256'] or
                    sha(script) != expected['bootstrap_sha256'] or
                    len(baseline_whole) != expected['whole_bytes'] or sha(baseline_whole) != expected['whole_sha256']):
                raise ValueError('exact reused source/bootstrap/whole input changed')
            entry = 'engines/compact/tiny-entry-' + family.lower()
            recipe = json.loads(sources[entry + '/recipe.json'])
            template, prefix = sources[entry + '/bootstrap.py.in'], sources[entry + '/launcher.sh']
            if recipe['expected'] != expected or template.count(b'__ROVE_SOURCE_LITERAL__') != 1:
                raise ValueError('normal ordinary recipe admission differs')
            expression, _ = literal(source)
            if template.replace(b'__ROVE_SOURCE_LITERAL__', expression.encode()) != script:
                raise ValueError('reused baseline bootstrap differs from unchanged ordinary template')
            options = recipe['compression']
            alone = options['format'] == 'lzma-alone'
            if not alone and options['format'] != 'xz':
                raise ValueError('unknown fixed original format')
            fmt = lzma.FORMAT_ALONE if alone else lzma.FORMAT_XZ
            def decode(whole, expected_script):
                if not whole.startswith(prefix):
                    raise ValueError('fixed launcher differs')
                decoder = lzma.LZMADecompressor(format=fmt)
                restored = decoder.decompress(whole[len(prefix):])
                if restored != expected_script or not decoder.eof or decoder.unused_data:
                    raise ValueError('strict original-format restoration differs')
            decode(baseline_whole, script)
            compiler = recipe['compiler']
            flags = compiler[1:compiler.index('-x')]
            if not any(flag.startswith('-std=') for flag in flags):
                flags = ['-std=gnu17', *flags]
            candidate, metadata = rename(source, clang_site=args.clang_site,
                resource_dir=args.resource_dir, arguments=flags)
            (directory / 'main.c').write_bytes(candidate)
            (directory / 'offsets.json').write_text(json.dumps(metadata, indent=2) + '\n')
            row.update(source_bytes=len(candidate), source_sha256=sha(candidate),
                baseline_source_bytes=len(source), source_saved_bytes=len(source)-len(candidate),
                renamed_declarations=metadata['renamed_declarations'], baseline=expected,
                reused_inputs={'source': str(base/'main.c'), 'bootstrap': str(base/'bootstrap.py'),
                    'whole': str(base/'baseline/x')}, compiler=compiler,
                position_bound_inverse_exact=True, reparse_binding_graph_equal=True)
            save()
            print(json.dumps({'stage': 'source', 'family': family, 'source_bytes': len(candidate),
                'renamed_declarations': metadata['renamed_declarations']}), flush=True)
            native_dir = directory / 'native'
            native_dir.mkdir()
            process = subprocess.run(compiler, input=candidate, cwd=native_dir,
                capture_output=True, timeout=90)
            report['native_compiles'] += 1
            row['native_compiles'] += 1
            (native_dir / 'compiler.stdout').write_bytes(process.stdout)
            (native_dir / 'compiler.stderr').write_bytes(process.stderr)
            if process.returncode:
                raise ValueError('native compile failed; original diagnostics preserved')
            native = (native_dir / 'x').read_bytes()
            row.update(native_bytes=len(native), native_sha256=sha(native))
            save()
            if sha(native) != expected['native_sha256']:
                raise ValueError('complete native inequality; stop family without metadata exception')
            expression, _ = literal(candidate)
            candidate_script = template.replace(b'__ROVE_SOURCE_LITERAL__', expression.encode())
            ast.parse(candidate_script)
            filters = [{'id': lzma.FILTER_LZMA1 if alone else lzma.FILTER_LZMA2,
                'preset': options['preset'] | (lzma.PRESET_EXTREME if options['extreme'] else 0),
                'lc': options['lc'], 'lp': options['lp'], 'pb': options['pb']}]
            payload = lzma.compress(candidate_script, format=fmt, filters=filters,
                **({} if alone else {'check': lzma.CHECK_CRC64}))
            whole = prefix + payload
            decode(whole, candidate_script)
            (directory / 'bootstrap.py').write_bytes(candidate_script)
            (directory / 'x').write_bytes(whole)
            row.update(complete=True, full_old_native_equal=True, whole_bytes=len(whole),
                whole_sha256=sha(whole), bootstrap_sha256=sha(candidate_script),
                whole_saved_bytes=expected['whole_bytes']-len(whole), engine_runs=0,
                strict_decode_equal=True, compression=options)
            save()
            print(json.dumps({'stage': 'whole', 'family': family, 'whole_bytes': len(whole),
                'saved': row['whole_saved_bytes'], 'native_exact': True}), flush=True)
        except Exception as error:
            row['error'] = repr(error)
            save()
            print(json.dumps({'family': family, 'stopped': repr(error)}), flush=True)
    report.update(complete=all(row['complete'] for row in report['cases'].values()),
        all_owned_commands_terminal=True)
    save()
    print(json.dumps({'complete': report['complete'], 'results_sha256': sha((out/'results.json').read_bytes()),
        'engine_runs': 0, 'native_compiles': report['native_compiles']}), flush=True)


if __name__ == '__main__':
    main()
