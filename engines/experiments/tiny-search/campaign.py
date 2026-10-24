#!/usr/bin/env python3
"""Measure independent tiny-A search expressions as complete source launchers.

Requires an immutable audited tiny-A build.json as a comparison reference.
Copies only named readable source/recipe inputs and writes every generated
source, executable, artifact and report to a new external output directory.
No baseline or tiny-A canonical file is changed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import itertools

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TINY = ROOT / 'engines/compact/tiny-a'
HISTORICAL_PACKERS = {
    'engines/scripts/pack.py': ('f95a9166f8fc018e4250999fa60c10568fa2ef3388b704a1fdfab9802bef5083',
                               'engines/experiments/packaging-control/pack.py'),
    'engines/compact/tiny-a/pack_single.py': ('0d7463f7b7ea4b6ff411ad81ea5efdc70828a24a6f9a305f5bf7be3c9d43b5ff',
                                           'engines/experiments/packaging-control/pack_single.py'),
    'engines/compact/tiny-a/pack_stream.py': ('b4addefbb1233881e85707aa525ca4af7f8210d9d27f56fbb52e4440a966b99e',
                                           'engines/experiments/packaging-control/pack_stream.py'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def run(command, cwd):
    process = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=90)
    if process.returncode:
        raise RuntimeError(json.dumps({'command': command, 'cwd': str(cwd), 'code': process.returncode,
                                       'stdout': process.stdout, 'stderr': process.stderr}))
    return process


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--select', action='append')
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT in args.out.parents:
        parser.error('new absolute output directory outside checkout required')
    reference = json.loads(args.baseline.read_text())
    args.out.mkdir(parents=True)
    frozen = args.out / 'frozen'
    frozen.mkdir()
    selected = tuple(reference['source_sha256'])
    sources = {}
    for name, expected in reference['source_sha256'].items():
        data = (TINY / name).read_bytes()
        if sha(data) != expected:
            raise ValueError('canonical source changed since audited baseline: ' + name)
        sources[name] = data
        (frozen / name).write_bytes(data)
    recipes, recipe_input_paths = {}, {}
    for name, expected in reference['recipe_sha256'].items():
        # build.py is provenance of the reference, not an executed dependency
        # of this independent driver. Its owner may add unrelated build forms.
        if Path(name).name == 'build.py' or Path(name).name == 'stitch.py' and not reference.get('counter_recipe'):
            continue
        historical = HISTORICAL_PACKERS.get(name)
        origin = historical[1] if historical and expected == historical[0] else name
        data = (ROOT / origin).read_bytes()
        if sha(data) != expected:
            raise ValueError('recipe changed since audited baseline: ' + name)
        recipes[name] = sha(data)
        recipe_input_paths[name] = origin
        (frozen / Path(name).name).write_bytes(data)
    (frozen / 'represent.py').write_bytes((HERE / 'represent.py').read_bytes())
    (frozen / 'pvs_loop.c.in').write_bytes((HERE / 'pvs_loop.c.in').read_bytes())
    (frozen / 'state.py').write_bytes((HERE / 'state.py').read_bytes())
    compiler_kwargs = {}
    if 'engines/scripts/compiler_group.py' in recipes:
        compiler_kwargs['compiler_group'] = module('tiny_search_compiler_group', frozen / 'compiler_group.py').transform_bootstrap
    representation = module('tiny_search_represent', frozen / 'represent.py')
    state = module('tiny_search_state', frozen / 'state.py')
    specialize = module('tiny_search_specialize', frozen / 'specialize.py').specialize_c
    compact = module('tiny_search_minify', frozen / 'minify.py').compact_source
    single = module('tiny_search_single', frozen / 'pack_single.py').write_single
    stream = module('tiny_search_stream', frozen / 'pack_stream.py').write_stream
    generic = module('tiny_search_pack', frozen / 'pack.py').write_launchers
    strip_counters = module('tiny_search_counter_strip', frozen / 'stitch.py').strip_dev_counters if reference.get('counter_recipe') else None
    configs = {
        'baseline': (), 'discard': ('discard',), 'loop': ('loop',),
        'trial': ('trial',), 'prior': ('prior',), 'packed': ('packed',),
        'flow': ('discard', 'loop'), 'root-state': ('discard', 'loop', 'trial', 'prior'),
        'packed-flow': ('packed', 'loop', 'trial', 'prior'),
        'bounded-eval': ('bounded-eval',),
        'discard-prior': ('discard','prior'),
        'bounded-discard-prior': ('discard','prior','bounded-eval'),
        'winner-state': ('discard','prior','bounded-eval','state:probe-marker','state:positive-bonus'),
    }
    for size in range(1, len(state.OPERATIONS) + 1):
        for operations in itertools.combinations(state.OPERATIONS, size):
            configs['state-' + '-'.join(operations)] = tuple('state:' + item for item in operations)
    report = {'baseline': str(args.baseline), 'source_sha256': reference['source_sha256'],
              'recipe_sha256': recipes, 'recipe_input_paths': recipe_input_paths,
              'compiler': subprocess.check_output(['cc', '--version'], text=True).splitlines()[0],
              'policy': 'same search expressions/order, unless explicit per-form deviation; no NPS campaign',
              'records': []}
    flags = ['-std=c11', '-Os', '-pthread', '-DWORKERS=2', '-DTT_BITS=18']
    file_recipe = ['cc', *flags, '-DDEV=0', 'main.c', '-o', 'x']
    stdin_recipe = ['cc', *flags, '-DDEV=0', '-x', 'c', '-', '-o', 'x']
    reference_combined = (args.baseline.parent / 'original/main.c').read_bytes()
    expected_combined = next(r['source_sha256'] for r in reference['engines'] if r['id'] == 'tiny-A-original')
    if sha(reference_combined) != expected_combined:
        raise ValueError('reference readable translation unit hash mismatch')
    (frozen / 'reference-combined.c').write_bytes(reference_combined)
    for name, choices in configs.items():
        if args.select and name not in args.select:
            continue
        directory = args.out / name
        directory.mkdir()
        transformed = representation.apply(sources, [choice for choice in choices if not choice.startswith('state:')])
        operations = [choice[6:] for choice in choices if choice.startswith('state:')]
        state_observations = None
        if operations:
            if 'hole-learners' in operations and 'board.c' not in transformed:
                transformed['board.c'] = next(data for name,data in transformed.items() if name.startswith('board'))
            transformed, state_observations = state.transform(transformed, operations=operations)
        # Use the exact audited definitions-before-callers unit. This avoids
        # depending on the concurrently evolving canonical producer script.
        original_search = sources['search.c'].replace(b'#include "tiny.h"', b'')
        changed_search = transformed['search.c'].replace(b'#include "tiny.h"', b'')
        if reference_combined.count(original_search) != 1:
            raise ValueError('fixed readable search body missing from reference unit')
        combined = reference_combined.replace(original_search, changed_search)
        if transformed['tiny.h'] != sources['tiny.h']:
            checked_header=sources['tiny.h'].decode()
            for old,new in (('int id,depth,score; Move best;','int id,depth,score; Move best,trial;'),
                            ('int16_t history[128][128],continuation[13][13],correction[1024];','int16_t history[16384];')):
                if new in transformed['tiny.h'].decode():
                    combined=representation.once(combined.decode(),old,new).encode()
                    checked_header=representation.once(checked_header,old,new)
            if checked_header.encode()!=transformed['tiny.h']:
                raise ValueError('unexpected readable header change')
        layout = reference['source_layout']
        (directory / 'combined.c').write_bytes(combined)
        specialized, observations = specialize({'main.c': combined}, directory / 'preprocess', file_recipe, os.environ.copy())
        source = compact(specialized['main.c'], 'c')
        counter_observation = None
        if strip_counters:
            source,counter_observation=strip_counters(source)
        (directory / 'main.c').write_bytes(source)
        if name == 'baseline':
            expected = next(r['source_sha256'] for r in reference['engines'] if r['id'] == 'tiny-A-compact')
            if sha(source) != expected:
                raise ValueError('exact baseline compact source did not reproduce')
        run(file_recipe, directory)
        binary = (directory / 'x').read_bytes()
        dev = directory / 'dev'
        dev.mkdir()
        (dev / 'main.c').write_bytes(combined)
        run(['cc', *flags, '-DDEV=1', 'main.c', '-o', 'x'], dev)
        packages = generic({'main.c': source}, directory / 'generic', command=file_recipe,
                           **compiler_kwargs)
        packages += single(source, directory / 'single', stdin_recipe, **compiler_kwargs)
        packages += stream(source, directory / 'stream', stdin_recipe, **compiler_kwargs)
        best = min(packages, key=lambda record: record['bytes'])
        record = {'name': name, 'choices': choices, 'source_bytes': len(source), 'source_sha256': sha(source),
                  'combined_sha256': sha(combined), 'native_bytes': len(binary), 'native_sha256': sha(binary),
                  'compile': file_recipe, 'layout': layout, 'preprocessor': observations,
                  'state_observations': state_observations,
                  'counter_observation': counter_observation,
                  'artifacts': packages, 'minimum_complete': best,
                  'shipping_command': [str(directory / 'x')], 'development_command': [str(dev / 'x')]}
        report['records'].append(record)
        (args.out / 'measure.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'name': name, 'source': len(source), 'complete': best['bytes'],
                          'codec': best['codec'], 'native': len(binary)}), flush=True)


if __name__ == '__main__':
    main()
