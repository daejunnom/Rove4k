#!/usr/bin/env python3
"""One F4720 futex-pool native compile and one unchanged fixed-codec whole cost.

Controls are read only at literal paths/hashes. No control regeneration, C AST,
preprocessing, engine execution, lifecycle qualification or normal promotion.
"""
import argparse
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import platform
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
COMPILER = ['cc', '-Os', '-pthread', '-x', 'c', '-', '-o', 'x', '-s']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p / '.git').exists() for p in (out, *out.parents)):
        parser.error('a new absolute output outside Git is required')
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        parser.error('fixed Linux x86-64 target required')
    recipe = json.loads((HERE / 'recipe.json').read_bytes())
    if recipe['family'] != 'F' or recipe['compiler'] != COMPILER or recipe['native_compiles'] != 1 or recipe['codec_compressions'] != 1:
        raise ValueError('fixed one-candidate scope changed')
    out.mkdir(parents=True)
    frozen = out / 'inputs'
    frozen.mkdir()
    report = {'complete': False, 'family': 'F', 'stage': recipe['stage'], 'inputs': {},
              'native_compiles': 0, 'control_compiles': 0, 'codec_compressions': 0,
              'C_AST': 0, 'preprocessing': 0, 'engine_runs': 0, 'bootstrap_runs': 0,
              'control_copies': 0, 'normal_sources_modified': False,
              'runtime_or_lifetime_qualified': False, 'reproduction_claimed': False}
    def save():
        (out / 'cost.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    try:
        for name in ('build.py', 'recipe.json', 'transform.py', 'README.md', '.gitattributes'):
            data = (HERE / name).read_bytes()
            if b'\r' in data:
                raise ValueError('ordinary experiment source must be LF: ' + name)
            (frozen / name).write_bytes(data)
            report['inputs'][name] = {'bytes': len(data), 'sha256': sha(data)}
        if report['inputs']['build.py']['sha256'] != recipe['producer_sha256']:
            raise ValueError('fixed producer changed')
        if report['inputs']['transform.py']['sha256'] != recipe['transform_sha256']:
            raise ValueError('fixed shipping stage changed')
        helpers = {}
        for name, pin in recipe['helpers'].items():
            data = (REPO / pin['path']).read_bytes()
            if sha(data) != pin['sha256']:
                raise ValueError('fixed ordinary helper changed: ' + name)
            destination = frozen / name
            destination.write_bytes(data)
            report['inputs'][pin['path']] = {'bytes': len(data), 'sha256': sha(data)}
            helpers[name] = destination
        prior = {}
        for name, pin in recipe['controls'].items():
            data = Path(pin['path']).read_bytes()
            if len(data) != pin['bytes'] or sha(data) != pin['sha256']:
                raise ValueError('literal current control mismatch: ' + name)
            prior[name] = data
        report['control_actual_read_and_verified'] = recipe['controls']
        current = json.loads(prior['normal_recipe'])
        if current['compiler'] != COMPILER or current['profile'] != {'workers': 2, 'tt_bits': 18, 'ply': 128, 'dev_default': False}:
            raise ValueError('current normal compiler/profile differs')
        expected = current['expected']
        for key, name in (('source', 'source'), ('native', 'native'), ('whole', 'whole')):
            if expected[key + '_bytes'] != len(prior[name]) or expected[key + '_sha256'] != sha(prior[name]):
                raise ValueError('control is not current normal identity: ' + name)
        if expected['bootstrap_sha256'] != sha(prior['bootstrap']):
            raise ValueError('baseline bootstrap does not match normal recipe')
        if current['compression'] != recipe['compression']:
            raise ValueError('normal fixed codec differs')
        template = helpers['bootstrap.py.in'].read_bytes()
        prefix = helpers['launcher.sh'].read_bytes()
        if len(prefix) != 77 or template.count(b'__ROVE_SOURCE_LITERAL__') != 1:
            raise ValueError('fixed launcher/bootstrap shape changed')
        literal = load('futex_fixed_source_literal', helpers['pack_stream.py']).source_literal
        decoder = load('futex_strict_input_decode', helpers['decode.py'])
        old_expression, _ = literal(prior['source'])
        if template.replace(b'__ROVE_SOURCE_LITERAL__', old_expression.encode()) != prior['bootstrap']:
            raise ValueError('unchanged bootstrap template does not reproduce old exact bootstrap')
        transform = load('futex_fixed_stage', frozen / 'transform.py').transform_source
        source, observations = transform(prior['source'])
        (out / 'main.c').write_bytes(source)
        report['transform'] = observations
        expression, literal_kind = literal(source)
        script = template.replace(b'__ROVE_SOURCE_LITERAL__', expression.encode())
        (out / 'bootstrap.py').write_bytes(script)
        report['tools'] = {name: subprocess.check_output(command, text=True).splitlines()[0]
                           for name, command in {'cc': ['cc', '--version'], 'ld': ['ld', '--version'],
                                                 'python': ['python3', '--version']}.items()}
        native_dir = out / 'native'
        native_dir.mkdir()
        report['native_compiles'] += 1
        save()
        compiled = subprocess.run(COMPILER, input=source, cwd=native_dir, capture_output=True, timeout=90)
        (native_dir / 'compiler.stdout').write_bytes(compiled.stdout)
        (native_dir / 'compiler.stderr').write_bytes(compiled.stderr)
        report['compiler_returncode'] = compiled.returncode
        if compiled.returncode:
            raise RuntimeError('candidate compiler failed; original stderr preserved')
        native = (native_dir / 'x').read_bytes()
        # The fixed -s image has only its dynamic symbol table.
        dynamic = subprocess.check_output(['nm', '-D', '--undefined-only', str(native_dir / 'x')], text=True)
        (out / 'undefined-symbols.txt').write_text(dynamic)
        if '__atomic_' in dynamic or '__sync_' in dynamic or 'libatomic' in dynamic:
            raise ValueError('external atomic helper is outside the lock-free int contract')
        report['external_atomic_helper_absent'] = True
        report['codec_compressions'] += 1
        save()
        payload = lzma.compress(script, format=lzma.FORMAT_ALONE, check=lzma.CHECK_NONE,
                                filters=[{'id': lzma.FILTER_LZMA1, 'preset': 9 | lzma.PRESET_EXTREME,
                                          'lc': 2, 'lp': 0, 'pb': 0, 'mf': lzma.MF_BT4,
                                          'dict_size': 67108864, 'nice_len': 32}])
        whole = prefix + payload
        (out / 'x').write_bytes(whole)
        (out / 'x').chmod(0o755)
        proof = decoder.verify(whole, prefix, source, COMPILER, script, expected_format='alone')
        proof_raw = (json.dumps(proof, indent=2) + '\n').encode()
        (out / 'decode.json').write_bytes(proof_raw)
        report.update(complete=True, source={'bytes': len(source), 'sha256': sha(source)},
                      native={'bytes': len(native), 'sha256': sha(native)},
                      whole={'bytes': len(whole), 'sha256': sha(whole)},
                      bootstrap={'bytes': len(script), 'sha256': sha(script)},
                      prefix={'bytes': len(prefix), 'sha256': sha(prefix)},
                      payload={'bytes': len(payload), 'sha256': sha(payload)},
                      source_literal_kind=literal_kind, compiler_argv=COMPILER,
                      source_delta=len(source)-len(prior['source']), native_delta=len(native)-len(prior['native']),
                      whole_delta=len(whole)-len(prior['whole']), remaining_over4096=len(whole)-4096,
                      strict_decode_source_argv=True, decode_receipt_sha256=sha(proof_raw),
                      useful_whole_gain=len(whole) < len(prior['whole']),
                      disposition='focused-lifecycle-proof-proposal-only' if len(whole) < len(prior['whole']) else 'STOP-tie-or-loss')
        save()
        print(json.dumps({key: report[key] for key in ('complete', 'source', 'native', 'whole', 'source_delta', 'native_delta', 'whole_delta', 'disposition')}), flush=True)
    except BaseException as error:
        report.update(complete=False, error=repr(error))
        save()
        raise


if __name__ == '__main__':
    main()
