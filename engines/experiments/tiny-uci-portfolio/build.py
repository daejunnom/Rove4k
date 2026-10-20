#!/usr/bin/env python3
"""One fixed minimal UCI policy on the four qualified Tiny B/C/E/F controls."""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CONTROLS = {
    'B': {'build': '/home/stemxstudio/rove4k-tiny-b-final-20261020/build.json',
          'validation': '/home/stemxstudio/rove4k-tiny-b-final-20261020/validation-manifest.json',
          'identity': '/home/stemxstudio/rove4k-tiny-b-image-20261020/results.json'},
    'C': '/home/stemxstudio/rove4k-tiny-c-table-campaign-20261020/startup/build/build.json',
    'E': '/home/stemxstudio/rove4k-tiny-e-state-20261020-evidence/final2/state/build.json',
    'F': {'build': '/home/stemxstudio/rove4k-tiny-f-structural-20261020/build.json',
          'encoding': '/home/stemxstudio/rove4k-tiny-f-encoding-v2-20261020/results.json',
          'qualification': '/home/stemxstudio/rove4k-tiny-f-final-proof-v3-20261020/results.json'},
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def source_argument(script):
    matches = [node for node in ast.walk(ast.parse(script)) if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
               and node.func.value.id == 'p' and node.func.attr == 'communicate']
    if len(matches) != 1 or len(matches[0].args) != 1:
        raise ValueError('unknown compiler source-restoration call shape')
    node = matches[0].args[0]
    starts = [0] + [m.end() for m in re.finditer(rb'\r\n|\r|\n', script)]
    return starts[node.lineno - 1] + node.col_offset, starts[node.end_lineno - 1] + node.end_col_offset


def restored_literal(expression):
    node = ast.parse(expression, mode='eval').body
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'encode' and not node.args and not node.keywords:
        value = ast.literal_eval(node.func.value)
        if not isinstance(value, str):
            raise ValueError('unknown source literal encode shape')
        return value.encode()
    value = ast.literal_eval(node)
    if not isinstance(value, bytes):
        raise ValueError('unknown source literal type')
    return value


def source_literal(source):
    text = source.decode('utf-8')
    trailing = len(text) - len(text.rstrip('\\'))
    if '\r' not in text and '\0' not in text and not trailing % 2:
        for quote in ("'''", '"""'):
            if quote not in text and not text.endswith(quote[0]):
                return ('r' + quote + text + quote + '.encode()').encode()
    return repr(source).encode()


def packager(control):
    wrapper = control['wrapper']
    offset = wrapper.index(b'\xfd7zXZ\0')
    prefix, bootstrap = wrapper[:offset], lzma.decompress(wrapper[offset:])
    begin, end = source_argument(bootstrap)
    if restored_literal(bootstrap[begin:end]) != control['source']:
        raise ValueError('qualified wrapper does not contain the pinned source')
    configuration = control['compression']
    if configuration['format'] != 'xz' or configuration['check'] != 'CRC64':
        raise ValueError('unsupported declared selected transport')
    filters = [{'id': lzma.FILTER_LZMA2, **{key: configuration[key] for key in ('preset', 'lc', 'lp', 'pb')}}]
    def package(source):
        script = bootstrap[:begin] + source_literal(source) + bootstrap[end:]
        a, b = source_argument(script)
        if restored_literal(script[a:b]) != source:
            raise ValueError('source literal did not restore exact compiler input')
        packed = prefix + lzma.compress(script, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, filters=filters)
        return packed, script
    if package(control['source'])[0] != wrapper:
        raise ValueError('qualified selected wrapper did not reproduce with its fixed compression recipe')
    return package, {'prefix_bytes': len(prefix), 'prefix_sha256': sha(prefix),
                     'compression': configuration, 'source_argument_only_changed': True}


def compile_source(command, source, directory):
    directory.mkdir()
    process = subprocess.run(command, cwd=directory, input=source, capture_output=True, timeout=90)
    if process.returncode:
        (directory / 'compiler-stderr.txt').write_bytes(process.stderr)
        raise RuntimeError('compiler failed: ' + str(directory / 'compiler-stderr.txt'))
    return (directory / 'x').read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', choices=tuple(CONTROLS), action='append')
    parser.add_argument('--controls', type=Path, help='path overrides only; literal identity admission remains fixed')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if not args.out.is_absolute():
        parser.error('new absolute external output required')
    out = args.out.resolve()
    if out.exists() or any((p / '.git').exists() for p in (out, *out.parents)):
        parser.error('new output outside Git required')
    families = args.family or list(CONTROLS)
    if len(set(families)) != len(families):
        parser.error('duplicate family')
    paths = json.loads(args.controls.read_text()) if args.controls else CONTROLS
    out.mkdir(parents=True)
    frozen = out / 'recipe'
    frozen.mkdir()
    source_files = ('build.py', 'transform.py', 'family_bf.py', 'family_ce.py')
    report = {'complete': False, 'scope': 'one declared minimal shipping UCI policy; four qualified controls, no D',
              'policy_origin': 'tiny-uci-min qualified 5223-byte candidate, same policy only; no additive size claim',
              'tooling_sha256': {}, 'families': [], 'shared_validator_modified': False,
              'tools': {name: subprocess.check_output(command, text=True).splitlines()[0]
                        for name, command in {'cc': ['cc', '--version'], 'ld': ['ld', '--version'],
                                              'python3': ['python3', '--version'], 'xz': ['xz', '--version']}.items()}}
    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    try:
        for name in source_files:
            data = (HERE / name).read_bytes()
            (frozen / name).write_bytes(data)
            report['tooling_sha256'][name] = sha(data)
        transform = load('portfolio_policy', frozen / 'transform.py').transform
        adapters = {key: load('portfolio_' + key, frozen / ('family_' + key + '.py')) for key in ('bf', 'ce')}
        for family in families:
            if family in 'BF':
                owned = frozen / ('family-' + family)
                owned.mkdir()
                control, generate = adapters['bf'].prepare(family, paths[family], owned)
            else:
                control, generate = adapters['ce'].prepare(family, paths, frozen)
            readable = control['readable']
            minimal, policy_proof = transform(readable, family)
            package, package_metadata = packager(control)
            directory = out / family
            directory.mkdir()
            build = {'complete': False, 'family': family, 'policy': policy_proof, 'engines': [],
                     'controls': control['provenance'], 'input_sha256': control['input_sha256'],
                     'tooling_sha256': report['tooling_sha256'], 'wrapper_recipe': package_metadata,
                     'resources': {'workers': 2, 'startup_threads': 3, 'tt_bits': 18},
                     'shared_validator_modified': False}
            base_dev = base_dev_native = None
            for form, combined in (('baseline', readable), ('minimal', minimal)):
                work = directory / form
                work.mkdir()
                (work / 'combined.c').write_bytes(combined)
                source = generate(combined, work / 'generate-first', dev=False)
                repeat_source = generate(combined, work / 'generate-second', dev=False)
                if source != repeat_source:
                    raise ValueError(f'{family} {form} source generation did not reproduce')
                (work / 'main.c').write_bytes(source)
                native = compile_source(control['compiler_argv'], source, work / 'native')
                repeated_native = compile_source(control['compiler_argv'], repeat_source, work / 'native-second')
                if native != repeated_native:
                    raise ValueError('native image did not reproduce')
                packed, script = package(source)
                if package(repeat_source) != (packed, script):
                    raise ValueError('whole package did not reproduce')
                if form == 'baseline' and (source != control['source'] or packed != control['wrapper'] or sha(native) != control['expected_native_sha256']):
                    raise ValueError('qualified control source/native/whole did not reproduce exactly')
                target_dir = work / 'wrapper'
                target_dir.mkdir()
                target = target_dir / 'x'
                target.write_bytes(packed)
                target.chmod(0o755)
                (work / 'bootstrap.py').write_bytes(script)
                dev = generate(combined, work / 'generate-dev', dev=True)
                dev_native = compile_source(control['dev_argv'], dev, work / 'dev')
                (work / 'dev/main.c').write_bytes(dev)
                if base_dev is None:
                    base_dev, base_dev_native = dev, dev_native
                elif dev != base_dev or dev_native != base_dev_native:
                    raise ValueError('DEV source/native changed')
                entry = {'id': form, 'family': family, 'profile': 'shipping', 'workers': 2,
                         'startup_threads': 3, 'max_threads': 3, 'startup_timeout': 60,
                         'command': [str(target)], 'native': str(work / 'native/x'), 'dev': str(work / 'dev/x'),
                         'readable': str(work / 'combined.c'), 'source': str(work / 'main.c'),
                         'readable_sha256': sha(combined), 'source_sha256': sha(source), 'source_bytes': len(source),
                         'native_sha256': sha(native), 'native_bytes': len(native),
                         'whole_sha256': sha(packed), 'whole_bytes': len(packed), 'expected_program_sha256': sha(packed),
                         'dev_source_sha256': sha(dev), 'dev_native_sha256': sha(dev_native),
                         'compile': control['compiler_argv'], 'dev_compile': control['dev_argv'],
                         'source_reproduced': True, 'native_reproduced': True, 'whole_reproduced': True,
                         'source_restored_exactly': True, 'under_4096_bytes': len(packed) <= 4096}
                build['engines'].append(entry)
                (directory / 'build.json').write_text(json.dumps(build, indent=2) + '\n')
            build['complete'] = True
            build['DEV_source_native_exactly_unchanged'] = True
            build['delta'] = {key: build['engines'][1][key] - build['engines'][0][key] for key in ('source_bytes', 'native_bytes', 'whole_bytes')}
            (directory / 'build.json').write_text(json.dumps(build, indent=2) + '\n')
            row = {'family': family, 'build': str(directory / 'build.json'), 'build_sha256': sha((directory / 'build.json').read_bytes()),
                   'baseline': {key: build['engines'][0][key] for key in ('source_bytes', 'native_bytes', 'whole_bytes')},
                   'minimal': {key: build['engines'][1][key] for key in ('source_bytes', 'native_bytes', 'whole_bytes')},
                   'delta': build['delta'], 'runtime_qualified': False, 'protected_body_identical': True,
                   'DEV_source_native_exactly_unchanged': True}
            report['families'].append(row)
            save()
            print(json.dumps(row), flush=True)
        report['complete'] = True
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
