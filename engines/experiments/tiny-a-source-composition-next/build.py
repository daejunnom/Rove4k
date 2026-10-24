#!/usr/bin/env python3
"""One A source candidate first cost, after its copied ordinary baseline2."""
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
OWN = ('build.py', 'closure.json', 'transform.py', 'retry.c.in', 'candidate_domain.py', 'candidate-domain.json')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bind(data, expected, kind):
    require(len(data) == expected[kind+'_bytes'] and sha(data) == expected[kind+'_sha256'], kind + ' exact baseline differs')


def package(source, template, prefix, literal):
    require(len(prefix) == 77 and template.count(b'__ROVE_SOURCE_LITERAL__') == 1, 'fixed bootstrap/prefix differs')
    expression, _ = literal(source)
    script = template.replace(b'__ROVE_SOURCE_LITERAL__', expression.encode())
    ast.parse(script)
    payload = lzma.compress(script, format=lzma.FORMAT_ALONE, check=lzma.CHECK_NONE,
        filters=[{'id': lzma.FILTER_LZMA1, 'preset': 9 | lzma.PRESET_EXTREME, 'lc': 2, 'lp': 0, 'pb': 0}])
    require(payload[:13] == bytes.fromhex('0200000004ffffffffffffffff'), 'fixed ALONE header differs')
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    require(decoder.decompress(payload) == script and decoder.eof and not decoder.unused_data, 'strict Python restoration differs')
    cli = subprocess.run(['lzma', '-dc'], input=payload, capture_output=True, timeout=15)
    require(cli.returncode == 0 and not cli.stderr and cli.stdout == script, 'CLI restoration differs')
    return prefix+payload, script


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out, baseline = args.out.resolve(), args.baseline.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)),
            'new absolute non-Git output required')
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'fixed Linux x86-64 target required')
    own = {n: (HERE/n).read_bytes() for n in OWN}
    closure = json.loads(own['closure.json'])
    require(closure['format'] == 1 and closure['control_file_count'] == 18 and len(closure['control_files']) == 18,
            'ordinary closure shape differs')
    controls = {}
    for name, pin in closure['control_files'].items():
        relative = Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts, 'unsafe source closure path')
        raw = (HERE/'control'/relative).read_bytes()
        require(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'] and b'\r' not in raw, 'frozen control differs: '+name)
        controls[name] = raw
    review_raw = args.review.read_bytes()
    review = json.loads(review_raw)
    require(review['source_review_only'] is True and review['blockers'] == [], 'independent precompile review required')
    for name, raw in own.items():
        require(review['reviewed_source_sha256'][name] == sha(raw), 'reviewed candidate producer drift: '+name)
    baseline_raw = (baseline/'build.json').read_bytes()
    previous = json.loads(baseline_raw)
    require(previous['complete'] is True and len(previous['attempts']) == 2 and
            previous['diagnostic_exact_control'] is False, 'two shipping-only baseline attempts required')
    expected = closure['expected']
    for name, kind in (('main.c', 'source'), ('native/x', 'native'), ('x', 'whole'), ('bootstrap.py', 'bootstrap')):
        data = (baseline/name).read_bytes()
        if kind == 'bootstrap':
            require(sha(data) == expected['bootstrap_sha256'], 'baseline bootstrap differs')
        else:
            bind(data, expected, kind)
        for index in (1, 2):
            require((baseline/('attempt-'+str(index))/name).read_bytes() == data, 'physical baseline attempts differ')
    for name, row in previous['inputs'].items():
        relative = name if name.startswith('engines/') else closure['entry']+'/'+name
        require(relative in controls and row['sha256'] == sha(controls[relative]), 'baseline producer source differs: '+name)
        require((baseline/'inputs'/Path(name).name).read_bytes() == controls[relative], 'baseline frozen source differs')
    out.mkdir(parents=True)
    frozen = out/'recipe'
    frozen.mkdir()
    for name, raw in own.items():
        (frozen/name).write_bytes(raw)
    (frozen/'precompile-review.json').write_bytes(review_raw)
    (frozen/'baseline-build.json').write_bytes(baseline_raw)
    for name, raw in controls.items():
        target = frozen/'control'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    report = {'complete': False, 'scope': 'one fixed A retry source first cost; no runtime qualification',
        'producer_inputs': {n: {'bytes': len(v), 'sha256': sha(v)} for n, v in own.items()},
        'control_inputs': closure['control_files'], 'baseline_build_sha256': sha(baseline_raw),
        'baseline_reproduced_shipping_attempts': 2, 'independent_candidate_attempts': [],
        'engine_runs': 0, 'runtime_qualification_runs': 0, 'candidate_runtime_qualified': False,
        'profile': closure['profile'], 'compiler': closure['compiler'], 'compression': closure['compression'],
        'old_native_identity_required_for_candidate': False, 'new_name_or_flag_or_codec_trials': 0}
    def save():
        (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    save()
    try:
        base = frozen/'control'
        entry = base/closure['entry']
        original = json.loads((entry/'recipe.json').read_bytes())
        require(original['compiler'] == closure['compiler'] and original['compression'] == closure['compression'] and
                original['profile'] == closure['profile'] and original['expected'] == expected, 'unchanged profile/codec/expectation differs')
        transform = load('A_next_frozen_transform', frozen/'transform.py')
        adapter = load('A_next_frozen_domain', frozen/'candidate_domain.py')
        specialize = load('A_next_frozen_specialize', base/'engines/scripts/specialize.py').specialize_c
        compact = load('A_next_frozen_minify', base/'engines/scripts/minify.py').compact_source
        strip = load('A_next_frozen_strip', base/'engines/compact/tiny-a/stitch.py').strip_dev_counters
        lexer = load('A_next_frozen_lexer', base/'engines/scripts/rename_c.py')
        alpha = load('A_next_frozen_alpha', entry/'shipping_alpha.py')
        storage = load('A_next_frozen_storage', base/'engines/scripts/fixed_shipping_storage.py')
        literal = load('A_next_frozen_literal', base/'engines/compact/tiny-a/pack_stream.py').source_literal
        compile_c = load('A_next_original_builder', entry/'build.py').compile_c
        readable, mutation = transform.transform((entry/'engine.c').read_bytes())
        (out/'combined.c').write_bytes(readable)
        report['source_change'] = mutation
        sources = []
        for index in (1, 2):
            directory = out/('attempt-'+str(index))
            directory.mkdir()
            active, pp = specialize({'main.c': readable}, directory/'preprocess', original['preprocessor']+['-DDEV=0'], os.environ.copy())
            source, stripping = strip(compact(active['main.c'], 'c'))
            files = {'main.c': source}
            for old, new in original['fixed_renames']+original['resource_literals']+original['function_spellings']:
                files = lexer._replace(files, old, new)
            pre = files['main.c']
            source, metadata = adapter.transform(pre, readable, alpha=alpha, storage=storage, lexer=lexer)
            (directory/'pre-alpha.c').write_bytes(pre)
            (directory/'main.c').write_bytes(source)
            (directory/'source.json').write_text(json.dumps({'preprocessor': pp, 'stripping': stripping, 'candidate_domain': metadata}, indent=2)+'\n')
            sources.append(source)
        require(sources[0] == sources[1], 'independent candidate source differs')
        natives = []
        for index, source in enumerate(sources, 1):
            native = compile_c(original['compiler'], source, out/('attempt-'+str(index))/'native')
            require(native[:6] == b'\x7fELF\x02\x01', 'new native is not ELF64 little-endian')
            natives.append(native)
        require(natives[0] == natives[1], 'independent new native identity differs')
        report['new_native_before_packaging'] = {'bytes': len(natives[0]), 'sha256': sha(natives[0]),
                                                 'matches_old_native': sha(natives[0]) == expected['native_sha256']}
        save()
        packages = []
        for index, source in enumerate(sources, 1):
            whole, script = package(source, (entry/'bootstrap.py.in').read_bytes(), (entry/'launcher.sh').read_bytes(), literal)
            directory = out/('attempt-'+str(index))
            (directory/'wrapper').write_bytes(whole)
            (directory/'wrapper').chmod(0o755)
            (directory/'bootstrap.py').write_bytes(script)
            packages.append((whole, script))
            report['independent_candidate_attempts'].append({'attempt': index,
                'source_bytes': len(source), 'source_sha256': sha(source), 'native_bytes': len(natives[index-1]),
                'native_sha256': sha(natives[index-1]), 'whole_bytes': len(whole), 'whole_sha256': sha(whole),
                'bootstrap_sha256': sha(script)})
            save()
        require(packages[0] == packages[1], 'independent whole/bootstrap differs')
        (out/'main.c').write_bytes(sources[0])
        (out/'native').write_bytes(natives[0])
        (out/'native').chmod(0o755)
        (out/'wrapper').write_bytes(packages[0][0])
        (out/'wrapper').chmod(0o755)
        (out/'bootstrap.py').write_bytes(packages[0][1])
        report.update(complete=True, baseline_whole_bytes=expected['whole_bytes'],
            candidate_whole_bytes=len(packages[0][0]), whole_delta=len(packages[0][0])-expected['whole_bytes'],
            gain=len(packages[0][0]) < expected['whole_bytes'], source_delta=len(sources[0])-expected['source_bytes'],
            under_4096=len(packages[0][0]) <= 4096, remaining_to_4096=len(packages[0][0])-4096,
            next_action='handoff for root qualification decision; do not execute candidate' if len(packages[0][0]) < expected['whole_bytes'] else 'stop: no whole-file gain')
        save()
        print(json.dumps({'complete': True, 'baseline': expected['whole_bytes'], 'candidate': report['candidate_whole_bytes'],
                          'whole_delta': report['whole_delta'], 'source_delta': report['source_delta'],
                          'gain': report['gain'], 'engine_runs': 0, 'report': str(out/'results.json')}))
    except BaseException as error:
        report['failure'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
