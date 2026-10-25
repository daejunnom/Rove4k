#!/usr/bin/env python3
"""One first-cost B target-generator comparison, with an exact 6219B control.

All outputs and inputs are frozen outside Git. No compiler/codec/identifier
sweep or runtime qualification is part of this first-cost driver.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
DEFAULT_CONTROL = Path('/home/stemxstudio/rove4k-tiny-uci-portfolio-20261020')
PINS = {
    'manifest': 'b94f663777d1219cad9827bd7322cd3a0872f5fcac2a82efb8d4df81335fef90',
    'readable': '1f879828346dfbc6023f6abfbbf1e1d2062e8e2dc0e9919aade254ba7a0a97f6',
    'source': 'eea1fe5f60c56aa90d2d51f3fa5a1aa56a63318527943500aa02d0105668f910',
    'native': '221a865e2712cb3e704128e0ae8353edd358343f564fe53093040f6515d522ec',
    'whole': '01261167253dd89a0e2d88aded2ee493fc0ffaec34cd2322459ddbc515f8aefd',
}
HELPERS = {
    'specialize.py': ('recipe/family-B/source-recipe/engines/scripts/specialize.py',
                      '3ba574c05f8c3be3629308f9bb1bc8214988893234cca25e2420dc0c7e00704d'),
    'minify.py': ('recipe/family-B/source-recipe/engines/scripts/minify.py',
                 'eb5eeca57b8f0f7225e639c8ee9e13fd1d5a5f159e58c38d66e0dea3b0433c3b'),
    'b_overlay.py': ('recipe/family-B/source-recipe/engines/compact/tiny-b/generate.py',
                    'c2cc1fd68d05d66f5525dfabc2368fdb0ddff2716bbf65ecb2033614b113aa59'),
    'portfolio_pack.py': ('recipe/build.py',
                         'bf92844002a0cdd4ebd901764be7f488597bc9a465ce8c88cf735bf14c9b6491'),
}
COMPILER = ['cc', '-std=c11', '-Os', '-pthread', '-DWORKERS=2', '-DTT_BITS=18',
            '-DDEV=0', '-x', 'c', '-', '-o', 'x']
COMPRESSION = {'format': 'xz', 'preset': 2147483657, 'lc': 3, 'lp': 0, 'pb': 2, 'check': 'CRC64'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control', type=Path, default=DEFAULT_CONTROL,
                        help='identical historical tree may be relocated; literal hashes remain mandatory')
    parser.add_argument('--review', type=Path, required=True, help='external independent precompile source receipt')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(args.out.is_absolute(), 'new absolute external output required')
    out = args.out.resolve()
    require(not out.exists() and not any((parent / '.git').exists() for parent in (out, *out.parents)),
            'new output outside Git required')
    inputs = {name: (HERE / name).read_bytes() for name in
              ('build.py', 'transform.py', 'generate.c.in', 'exchange-loop.c.in')}
    review_data = args.review.read_bytes()
    review = json.loads(review_data)
    require(review['source_review_only'] is True and review['blockers'] == [], 'independent source review required')
    require(review['baseline_readable_sha256'] == PINS['readable'], 'reviewed baseline differs')
    for name in ('transform.py', 'generate.c.in', 'exchange-loop.c.in'):
        require(review['reviewed_source_sha256'][name] == sha(inputs[name]), 'reviewed source changed: ' + name)
    manifest_data = (args.control / 'B/build.json').read_bytes()
    require(sha(manifest_data) == PINS['manifest'], 'qualified B manifest changed')
    manifest = json.loads(manifest_data)
    require(manifest['complete'] and manifest['family'] == 'B', 'qualified B control incomplete')
    row = next(item for item in manifest['engines'] if item['id'] == 'minimal')
    require(row['compile'] == COMPILER and manifest['wrapper_recipe']['compression'] == COMPRESSION,
            'fixed compiler/bootstrap compression recipe changed')
    require((row['workers'], row['startup_threads'], row['whole_bytes']) == (2, 3, 6219), 'fixed profile changed')
    paths = {'readable': 'B/minimal/combined.c', 'source': 'B/minimal/main.c',
             'native': 'B/minimal/native/x', 'whole': 'B/minimal/wrapper/x'}
    controls = {}
    for name, path in paths.items():
        data = (args.control / path).read_bytes()
        require(sha(data) == PINS[name], 'qualified control changed: ' + name)
        controls[name] = data
        inputs['control-' + name] = data
    inputs['control-manifest.json'] = manifest_data
    inputs['precompile-review.json'] = review_data
    for name, (path, expected) in HELPERS.items():
        data = (args.control / path).read_bytes()
        require(sha(data) == expected, 'qualified producer helper changed: ' + name)
        inputs[name] = data
    out.mkdir(parents=True)
    frozen = out / 'recipe'
    frozen.mkdir()
    for name, data in inputs.items():
        (frozen / name).write_bytes(data)
    report = {'complete': False, 'scope': 'one fixed target-centered B source first-cost; no runtime/4K/strength claim',
              'input_sha256': {name: sha(data) for name, data in inputs.items()},
              'precompile_review': review, 'compiler_argv': COMPILER, 'compression': COMPRESSION,
              'resources': {'workers': 2, 'total_threads': 3, 'tt_bits': 18, 'ply': 128},
              'forms': [], 'candidate_runtime_qualified': False}
    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    try:
        transform = load('B_target_frozen_transform', frozen / 'transform.py')
        specializer = load('B_target_frozen_specializer', frozen / 'specialize.py')
        minifier = load('B_target_frozen_minifier', frozen / 'minify.py')
        overlay = load('B_target_frozen_counters', frozen / 'b_overlay.py')
        packer = load('B_target_frozen_packager', frozen / 'portfolio_pack.py')
        package, package_record = packer.packager({'wrapper': controls['whole'], 'source': controls['source'],
                                                  'compression': COMPRESSION})
        report['bootstrap_recipe'] = package_record
        candidate, policy = transform.transform(controls['readable'])
        repeated_candidate, repeated_policy = transform.transform(controls['readable'])
        require(candidate == repeated_candidate and policy == repeated_policy, 'candidate source transformation differs')
        report['policy'] = policy
        report['compiler'] = subprocess.check_output(['cc', '--version'], text=True).splitlines()[0]
        report['glibc'] = subprocess.check_output(['getconf', 'GNU_LIBC_VERSION'], text=True).strip()
        for name, combined in (('control', controls['readable']), ('target', candidate)):
            directory = out / name
            directory.mkdir()
            (directory / 'combined.c').write_bytes(combined)
            generated = []
            for repeat in range(2):
                active, observations = specializer.specialize_c({'main.c': combined}, directory / f'preprocess-{repeat}',
                                                                 COMPILER, os.environ.copy())
                source, stripping = overlay.strip_counters(minifier.compact_source(active['main.c'], 'c'))
                generated.append(source)
                (directory / f'preprocess-{repeat}.json').write_text(json.dumps({'observations': observations,
                    'stripping': stripping, 'source_sha256': sha(source)}, indent=2) + '\n')
            require(generated[0] == generated[1], name + ' independent source generation differs')
            source = generated[0]
            (directory / 'main.c').write_bytes(source)
            images = []
            for repeat in range(2):
                work = directory / f'native-{repeat}'
                work.mkdir()
                process = subprocess.run(COMPILER, cwd=work, input=source, capture_output=True, timeout=90)
                (work / 'compile.stdout').write_bytes(process.stdout)
                (work / 'compile.stderr').write_bytes(process.stderr)
                require(process.returncode == 0, f'{name} compiler failed: {work}')
                images.append((work / 'x').read_bytes())
            require(images[0] == images[1], name + ' independent native compile differs')
            whole, bootstrap = package(source)
            require(package(generated[1]) == (whole, bootstrap), name + ' complete package repetition differs')
            (directory / 'bootstrap.py').write_bytes(bootstrap)
            artifact = directory / 'wrapper'
            artifact.write_bytes(whole)
            artifact.chmod(0o755)
            if name == 'control':
                require(source == controls['source'] and images[0] == controls['native'] and whole == controls['whole'],
                        'exact 6219B control source/native/whole did not reproduce')
            entry = {'id': name, 'readable_sha256': sha(combined), 'source_bytes': len(source), 'source_sha256': sha(source),
                     'native_bytes': len(images[0]), 'native_sha256': sha(images[0]), 'whole_bytes': len(whole),
                     'whole_sha256': sha(whole), 'source_reproduced': True, 'native_reproduced': True,
                     'whole_reproduced': True, 'source_argument_only_changed': True,
                     'runtime_qualified': False, 'source': str(directory / 'main.c'),
                     'readable': str(directory / 'combined.c'), 'native': str(directory / 'native-0/x'),
                     'wrapper': str(artifact), 'under_4096_bytes': len(whole) <= 4096}
            report['forms'].append(entry)
            save()
            print(json.dumps(entry), flush=True)
        report['delta'] = {key: report['forms'][1][key] - report['forms'][0][key]
                           for key in ('source_bytes', 'native_bytes', 'whole_bytes')}
        report['gain'] = report['delta']['whole_bytes'] < 0
        report['complete'] = True
        report['next_action'] = 'focused qualification permitted' if report['gain'] else 'STOP: first-cost loss/equality; no runtime QA'
        print(json.dumps({'complete': True, 'delta': report['delta'], 'gain': report['gain'], 'next_action': report['next_action']}), flush=True)
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
