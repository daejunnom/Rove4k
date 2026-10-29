#!/usr/bin/env python3
"""One exact B5955 control versus target+same89-alpha; no engine launches."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OWN = ('build.py', 'recipe.json', 'target_policy.py', 'target-policy.json')


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


def binding(data, row, kind):
    require(len(data) == row[kind + '_bytes'] and sha(data) == row[kind + '_sha256'],
            'literal ' + kind + ' identity mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and
            not any((p / '.git').exists() for p in (out, *out.parents)), 'new absolute non-Git output required')
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'fixed Linux x86-64 target required')
    own = {name: (HERE / name).read_bytes() for name in OWN}
    recipe = json.loads(own['recipe.json'])
    require(recipe['format'] == 1 and recipe['control_file_count'] == 23 and
            recipe['live_canonical_dependencies'] is False, 'closed recipe differs')
    review_raw = args.review.read_bytes()
    review = json.loads(review_raw)
    require(review['source_review_only'] is True and review['blockers'] == [], 'independent precompile review required')
    for name, data in own.items():
        require(review['reviewed_source_sha256'][name] == sha(data), 'reviewed input drift: ' + name)
    controls = {}
    for relative, pin in recipe['control_files'].items():
        path = Path(relative)
        require(not path.is_absolute() and '..' not in path.parts, 'unsafe control path')
        raw = (HERE / 'control' / path).read_bytes()
        require(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'] and b'\r' not in raw,
                'frozen ordinary control drift: ' + relative)
        controls[relative] = raw
    out.mkdir(parents=True)
    frozen = out / 'recipe'
    frozen.mkdir()
    for name, data in own.items():
        (frozen / name).write_bytes(data)
    (frozen / 'precompile-review.json').write_bytes(review_raw)
    for relative, raw in controls.items():
        path = frozen / 'control' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    report = {'complete': False, 'scope': 'one fixed target algorithm plus original89 shipping alpha combination',
              'producer_inputs': {n: {'bytes': len(d), 'sha256': sha(d)} for n, d in own.items()},
              'control_inputs': recipe['control_files'], 'review_sha256': sha(review_raw),
              'forms': [], 'engine_runs': 0, 'resources': recipe['resources'],
              'compiler': recipe['compiler'], 'compression': recipe['compression'],
              'candidate_runtime_qualified': False, 'performance_claim': False,
              'whole_runtime_stack_qualified': False}
    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    try:
        base = frozen / 'control'
        entry = base / 'engines/compact/tiny-entry-b'
        alpha = load('combination_original_alpha', base / 'alpha/policy.py')
        helper = load('combination_original_pack_header', base / 'alpha/build.py')
        lexer = load('combination_original_lexer', base / 'engines/scripts/rename_c.py')
        specialize = load('combination_specialize', base / 'engines/scripts/specialize.py').specialize_c
        compact = load('combination_minify', base / 'engines/scripts/minify.py').compact_source
        strip = load('combination_strip', base / 'engines/compact/tiny-b/generate.py').strip_counters
        literal = load('combination_literal', base / 'engines/compact/tiny-a/pack_stream.py').source_literal
        target = load('combination_target', base / 'target/transform.py')
        adapter = load('combination_target_alpha', frozen / 'target_policy.py')
        original = json.loads((entry / 'recipe.json').read_bytes())
        require(original['compiler'] == recipe['compiler'] and original['compression'] == recipe['compression'],
                'compiler/codec differs from original')
        mapping = json.loads((base / 'alpha/policy.json').read_bytes())['mapping']
        readable_control = (entry / 'engine.c').read_bytes()
        readable_target, target_meta = target.transform(readable_control)
        require(sha(readable_target) == recipe['target']['readable_sha256'], 'literal target readable differs')
        require(not (set(mapping.values()) & set(alpha._WORD.findall(readable_target.decode()))),
                'target readable fresh alias collision')
        report['target_algorithm'] = target_meta
        report['tools'] = {name: helper.subprocess.check_output(command, text=True).splitlines()[0] for name, command in
                           {'cc': ['cc', '--version'], 'ld': ['ld', '--version'],
                            'python': ['python3', '--version'], 'xz': ['xz', '--version']}.items()}
        for form, readable in (('control', readable_control), ('target', readable_target)):
            directory = out / form
            directory.mkdir()
            (directory / 'combined.c').write_bytes(readable)
            sources = []
            observations = []
            for repeat in (1, 2):
                active, observed = specialize({'main.c': readable}, directory / ('preprocess-' + str(repeat)),
                    original['preprocessor'] + ['-DDEV=0', 'main.c', '-o', 'x'], os.environ.copy())
                source, stripping = strip(compact(active['main.c'], 'c'))
                if form == 'control':
                    binding(source, original['expected'], 'source')
                    rewritten, metadata = alpha.transform_source(source, family='B', lexer=lexer)
                    binding(rewritten, recipe['control'], 'source')
                else:
                    require(len(source) == recipe['target']['compact_bytes'] and
                            sha(source) == recipe['target']['compact_sha256'], 'validated target compact differs')
                    rewritten, metadata = adapter.transform(source, original=alpha, lexer=lexer)
                sources.append((source, rewritten))
                observations.append({'preprocessor': observed, 'stripping': stripping, 'lexical': metadata})
            require(sources[0] == sources[1] and observations[0]['lexical'] == observations[1]['lexical'],
                    form + ' independent source generation differs')
            source, rewritten = sources[0]
            (directory / 'pre-alpha.c').write_bytes(source)
            (directory / 'main.c').write_bytes(rewritten)
            (directory / 'source-observations.json').write_text(json.dumps(observations, indent=2) + '\n')
            gate = directory / 'header-gate'
            gate.mkdir()
            header = helper.header_gate(source, rewritten, recipe['compiler'], mapping, lexer, gate)
            attempts = []
            expected = recipe[form]
            native_pin = expected if form == 'control' else recipe['target']
            for repeat in (1, 2):
                work = directory / ('attempt-' + str(repeat))
                process = helper.run(recipe['compiler'], work, rewritten, 90)
                (work / 'compiler.stdout').write_bytes(process.stdout)
                (work / 'compiler.stderr').write_bytes(process.stderr)
                require(process.returncode == 0, form + ' native compile failed')
                native = (work / 'x').read_bytes()
                binding(native, native_pin, 'native')
                whole, bootstrap = helper.package(rewritten, (entry / 'bootstrap.py.in').read_bytes(),
                    (entry / 'launcher.sh').read_bytes(), literal, recipe['compression'])
                if form == 'control':
                    binding(whole, recipe['control'], 'whole')
                (work / 'wrapper').write_bytes(whole)
                (work / 'wrapper').chmod(0o755)
                (work / 'bootstrap.py').write_bytes(bootstrap)
                attempts.append({'attempt': repeat, 'source_bytes': len(rewritten), 'source_sha256': sha(rewritten),
                    'native_bytes': len(native), 'native_sha256': sha(native), 'whole_bytes': len(whole),
                    'whole_sha256': sha(whole), 'bootstrap_sha256': sha(bootstrap)})
                if repeat == 1:
                    first = native, whole, bootstrap
                else:
                    require((native, whole, bootstrap) == first, form + ' independent native/whole differs')
            for filename, data in (('native', first[0]), ('wrapper', first[1]), ('bootstrap.py', first[2])):
                (directory / filename).write_bytes(data)
            (directory / 'wrapper').chmod(0o755)
            report['forms'].append({'id': form, 'header_gate': header, 'attempts': attempts,
                                   'pre_alpha_sha256': sha(source), **attempts[0]})
            save()
        control, candidate = report['forms']
        report.update(complete=True, gain=candidate['whole_bytes'] < control['whole_bytes'],
                      whole_delta=candidate['whole_bytes']-control['whole_bytes'],
                      under_4096=candidate['whole_bytes'] <= 4096,
                      remaining_to_4096=candidate['whole_bytes']-4096)
        save()
        print(json.dumps({'complete': True, 'control': control['whole_bytes'], 'target_alpha': candidate['whole_bytes'],
                          'delta': report['whole_delta'], 'gain': report['gain'], 'report': str(out / 'results.json')}))
    except BaseException as error:
        report['failure'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
