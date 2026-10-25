#!/usr/bin/env python3
"""Measure one shipping UCI policy against the exact 5283-byte Tiny A control.

No compiler, spelling, compression setting or protocol architecture sweep.
The prior qualified recipe is frozen before use; all output is external.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
PINS = {
    'specialize.py': '3ba574c05f8c3be3629308f9bb1bc8214988893234cca25e2420dc0c7e00704d',
    'minify.py': 'eb5eeca57b8f0f7225e639c8ee9e13fd1d5a5f159e58c38d66e0dea3b0433c3b',
    'stitch.py': 'e912ece9fa385f3cabc1486ef103a9c8596a527bb0232e1b0a02e58687dc1050',
    'rename_c.py': '9d7d09e2787cfda21701384be94ed00d588165574da5d8aacdf731fcb317cbe5',
    'pack_stream.py': 'b4addefbb1233881e85707aa525ca4af7f8210d9d27f56fbb52e4440a966b99e',
    'a-readable.c': '109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504',
    'a-search-rename.json': '3eae16eedebab9ae2870f298756503b51099c4902b0eb22eb143c087b3af4933',
    'a-encoding.json': '23f6b53adba6b28ae4c9c490cb1f0f347a46a189be2b31d7336fcace6b1b722b',
    'a-wrapper': '798c1492fcfc5734c9794704b5575a19755618e19d51aa12950302044065b645',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def source_argument(script):
    matches = [n for n in ast.walk(ast.parse(script)) if isinstance(n, ast.Call)
               and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
               and n.func.value.id == 'p' and n.func.attr == 'communicate']
    if len(matches) != 1 or len(matches[0].args) != 1:
        raise ValueError('expected one source-restoration call')
    node = matches[0].args[0]
    starts = [0] + [m.end() for m in re.finditer(rb'\r\n|\r|\n', script)]
    return starts[node.lineno - 1] + node.col_offset, starts[node.end_lineno - 1] + node.end_col_offset


def restore_literal(expression):
    node = ast.parse(expression, mode='eval').body
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'encode' and not node.args and not node.keywords:
        value = ast.literal_eval(node.func.value)
        if not isinstance(value, str):
            raise ValueError('expected string literal before encode')
        return value.encode()
    value = ast.literal_eval(node)
    if not isinstance(value, bytes):
        raise ValueError('expected bytes source literal')
    return value


def run(command, *, cwd, input=None):
    p = subprocess.run(command, cwd=cwd, input=input, capture_output=True, timeout=90)
    if p.returncode:
        (cwd / 'compiler-error.txt').write_bytes(p.stderr)
        raise RuntimeError('compiler failed; exact stderr retained in ' + str(cwd / 'compiler-error.txt'))
    return p


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control-recipe', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or any((p / '.git').exists() for p in (args.out, *args.out.parents)):
        parser.error('a new absolute output outside Git is required')
    args.out.mkdir(parents=True)
    recipe = args.out / 'recipe'
    recipe.mkdir()
    report = {'complete': False, 'scope': 'one explicit minimal shipping UCI policy, not semantic-preserving compression',
              'inputs': {}, 'engines': [], 'rules_url': 'https://wiki.chessdom.org/Rules#TCEC_4k_rules',
              'resources': {'search_workers': 2, 'expected_total_threads': 3, 'tt_bits': 18},
              'tools': {name: subprocess.check_output([*command], text=True).splitlines()[0]
                        for name, command in {'cc': ['cc', '--version'], 'ld': ['ld', '--version'],
                                              'python3': ['python3', '--version'], 'xz': ['xz', '--version']}.items()},
              'zlib': __import__('zlib').ZLIB_RUNTIME_VERSION, 'liblzma': 'Python stdlib lzma; xz version recorded',
              'shared_validator_modified': False}
    def save():
        (args.out / 'build.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    for name, expected in PINS.items():
        data = (args.control_recipe / name).read_bytes()
        if sha(data) != expected:
            raise ValueError('frozen control mismatch: ' + name)
        (recipe / name).write_bytes(data)
        report['inputs'][name] = {'sha256': sha(data), 'bytes': len(data)}
    for name in ('build.py', 'transform.py'):
        data = (HERE / name).read_bytes()
        (recipe / name).write_bytes(data)
        report['inputs']['policy/' + name] = {'sha256': sha(data), 'bytes': len(data)}
    transform = module('tiny_uci_policy', recipe / 'transform.py').transform
    specialize = module('tiny_uci_specialize', recipe / 'specialize.py').specialize_c
    compact = module('tiny_uci_compact', recipe / 'minify.py').compact_source
    strip = module('tiny_uci_counters', recipe / 'stitch.py').strip_dev_counters
    lexer = module('tiny_uci_rename', recipe / 'rename_c.py')
    literal = module('tiny_uci_literal', recipe / 'pack_stream.py').source_literal
    spelling = json.loads((recipe / 'a-search-rename.json').read_text())
    trials = [x for x in spelling['rename']['trials'] if x['status'] == 'accepted' and x['trial'] <= spelling['selected']['trial']]
    encoding = json.loads((recipe / 'a-encoding.json').read_text())
    selected = next(x for x in encoding['records'] if x['case'] == 'combined-fixed-stripped')
    command = ['cc', '-Os', '-x', 'c', '-', '-o', 'x', '-s']
    if selected['command'] != command:
        raise ValueError('unexpected fixed compiler command')
    wrapper = (recipe / 'a-wrapper').read_bytes()
    offset = wrapper.index(b'\xfd7zXZ\0')
    prefix, bootstrap = wrapper[:offset], lzma.decompress(wrapper[offset:])
    begin, end = source_argument(bootstrap)
    filters = [{'id': lzma.FILTER_LZMA2, 'preset': 9 | lzma.PRESET_EXTREME, 'lc': 2, 'lp': 0, 'pb': 0}]
    def package(source):
        expression, _ = literal(source)
        script = bootstrap[:begin] + expression.encode() + bootstrap[end:]
        return prefix + lzma.compress(script, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, filters=filters), script
    def generate(combined, directory, dev=False):
        active, _ = specialize({'main.c': combined}, directory,
                               ['cc', '-std=c11', '-Os', '-pthread', '-DWORKERS=2', '-DTT_BITS=18', '-DDEV=' + str(int(dev))], os.environ.copy())
        source = compact(active['main.c'], 'c')
        if dev:
            return source
        source, _ = strip(source)
        files = {'main.c': source}
        for trial in trials:
            files = lexer._replace(files, trial['identifier'], trial['replacement'])
        for name, value in {'WORKERS': '2', 'TT_BITS': '18'}.items():
            files = lexer._replace(files, name, value)
        for name, alias in selected['manual_function_spellings'].items():
            files = lexer._replace(files, name, alias)
        return files['main.c']
    baseline_dev = baseline_dev_native = None
    readable = (recipe / 'a-readable.c').read_bytes()
    minimal, policy = transform(readable)
    report['policy'] = policy
    report['wrapper'] = {'prefix_sha256': sha(prefix), 'prefix_bytes': len(prefix), 'compression': 'XZ LZMA2 preset9 extreme lc2 lp0 pb0 CRC64',
                         'restoration': 'same existing compiler process-group, signal handoff, fdexec and cleanup bootstrap; only source argument differs'}
    for name, combined in (('baseline', readable), ('minimal', minimal)):
        directory = args.out / name
        directory.mkdir()
        (directory / 'combined.c').write_bytes(combined)
        source = generate(combined, directory / 'preprocess-first')
        repeat_source = generate(combined, directory / 'preprocess-second')
        if source != repeat_source:
            raise ValueError('source generation did not reproduce')
        (directory / 'main.c').write_bytes(source)
        native_dir = directory / 'native'
        native_dir.mkdir()
        run(command, cwd=native_dir, input=source)
        native = (native_dir / 'x').read_bytes()
        run(command, cwd=native_dir, input=repeat_source)
        if (native_dir / 'x').read_bytes() != native:
            raise ValueError('native bytes did not reproduce')
        packed, script = package(source)
        repeat_packed, repeat_script = package(repeat_source)
        if packed != repeat_packed or script != repeat_script:
            raise ValueError('whole file did not reproduce')
        if name == 'baseline' and (sha(source) != selected['source_sha256'] or packed != wrapper or sha(native) != selected['native_gate']['native_sha256']):
            raise ValueError('exact frozen control did not reproduce')
        wrapper_dir = directory / 'wrapper'
        wrapper_dir.mkdir()
        target = wrapper_dir / 'x'
        target.write_bytes(packed)
        target.chmod(0o755)
        (directory / 'bootstrap.py').write_bytes(script)
        dev = generate(combined, directory / 'preprocess-dev', dev=True)
        dev_dir = directory / 'dev'
        dev_dir.mkdir()
        (dev_dir / 'main.c').write_bytes(dev)
        run(['cc', '-Os', '-pthread', '-DWORKERS=2', '-DTT_BITS=18', '-x', 'c', '-', '-o', 'x'], cwd=dev_dir, input=dev)
        dev_native = (dev_dir / 'x').read_bytes()
        if baseline_dev is None:
            baseline_dev = dev
            baseline_dev_native = dev_native
        elif dev != baseline_dev:
            raise ValueError('DEV source changed')
        elif dev_native != baseline_dev_native:
            raise ValueError('DEV native bytes changed')
        record = {'id': name, 'profile': 'shipping', 'workers': 2, 'startup_threads': 3, 'max_threads': 3,
                  'startup_timeout': 60, 'command': [str(target)], 'native': str(native_dir / 'x'), 'dev': str(dev_dir / 'x'),
                  'readable': str(directory / 'combined.c'), 'source': str(directory / 'main.c'),
                  'source_bytes': len(source), 'source_sha256': sha(source), 'readable_sha256': sha(combined),
                  'native_bytes': len(native), 'native_sha256': sha(native), 'whole_bytes': len(packed),
                  'whole_sha256': sha(packed), 'expected_program_sha256': sha(packed), 'bootstrap_sha256': sha(script),
                  'dev_source_sha256': sha(dev), 'dev_native_sha256': sha(dev_native),
                  'source_reproduced': True, 'native_reproduced': True, 'whole_reproduced': True,
                  'compile': command, 'under_4096_bytes': len(packed) <= 4096}
        # Parse the actual executable bootstrap rather than trusting the supplied source.
        actual_begin, actual_end = source_argument(script)
        restored = restore_literal(script[actual_begin:actual_end])
        if restored != source:
            raise ValueError('source literal restoration mismatch')
        record['source_restored_exactly'] = True
        report['engines'].append(record)
        save()
        print(json.dumps(record), flush=True)
    report['dev_exactly_unchanged'] = True
    report['delta'] = {key: report['engines'][1][key] - report['engines'][0][key]
                       for key in ('source_bytes', 'native_bytes', 'whole_bytes')}
    report['complete'] = True
    save()


if __name__ == '__main__':
    main()
