#!/usr/bin/env python3
"""Fresh fixed-resource Rust A with the separate minimal TCEC source wrapper.

The maintained Rust producer remains the source authority. This path freezes
that entire producer closure, regenerates its current control, and independently
specializes, merges, embodies, compiles and packages both new attempts. It does
not consume a historical generated source or binary. General compiler ownership
and optional development UCI remain separate contracts.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BUILDER = 'engines/experiments/tiny-rust-stream/build.py'
SELF = 'engines/experiments/tiny-rust-stream/tcec_build.py'
PACKAGE = 'engines/scripts/source_package.py'
VERIFIER = 'engines/experiments/tcec-scope/verify.py'
PINNED = {
    PACKAGE: '4c3775e713b093de39cb54e12abdef29793dd924731f1b3014c406d1df4e4f19',
    VERIFIER: 'b39321386f4ff2520ec7f7185178e01d9b9a005965c0840929d848d87c92fb48',
    'engines/compact/tiny-entry-d/verify.py': '18faa69aed5cb5dd85a054ef2e6830463f3d819f5f635d74d55550a877c81eae',
    'engines/tests/chess_oracle.py': 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8',
}
COMMAND = ('rustc', '--edition=2024', '-Copt-level=z', '-Clto=fat',
           '-Ccodegen-units=1', '-Cpanic=abort', '-Cstrip=symbols',
           '-Clink-arg=-Wl,--build-id=none', '--crate-name', 'rove4k', '-', '-o', 'x')
COMPRESSION = {'format': 'lzma-alone', 'filter': 'LZMA1', 'check': 'NONE',
               'preset': 9, 'extreme': True, 'lc': 2, 'lp': 0, 'pb': 0,
               'mf': 'BT4', 'dictionary_bytes': 65536, 'nice_len': 273}
# These literals were measured before this producer was written. They are not
# refreshed from generated output, and the two new native compilations must agree.
EXPECTED = {
    'source': (20655, '0f6ff2def3e94909dab9db781935e6e4cc87a5a59d389aa6d1893bb8508559b2'),
    'native': (336960, '5f7c4432f9cd118c287da8cb1589df27908b81829ff9060a98625c20749ea44b'),
    'whole': (7502, 'd9f4e8194ac44507a9c36fea81cf119fbc605b495974fe06ac454fc1f6f7de08'),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin(data):
    return {'bytes': len(data), 'sha256': sha(data)}


def normalized(path):
    data = path.read_bytes().replace(b'\r\n', b'\n')
    require(b'\r' not in data, 'lone CR in source: ' + str(path))
    return data


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    raise SystemExit("Rust A is retired; the historical7502-byte TCEC producer is disabled.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--rustc', default='rustc')
    args = parser.parse_args()
    out = args.out.resolve()
    require(sys.platform == 'linux', 'Linux native production required')
    require(args.out.is_absolute() and not out.exists()
            and not any((p / '.git').exists() for p in (out, *out.parents)),
            'new absolute output outside every Git checkout required')
    compiler = shutil.which(args.rustc)
    require(compiler is not None, 'fixed Rust compiler is unavailable')
    compiler = os.path.abspath(compiler)
    base = load('tcec_rust_intake_only', ROOT / BUILDER)
    names = [*(base.SOURCE_PREFIX + n for n in base.PRODUCTION), *base.HELPER_BINDINGS,
             BUILDER, 'engines/experiments/tiny-rust-stream/merge.py',
             'engines/experiments/tiny-rust-stream/stream_pack.py',
             'engines/experiments/tiny-rust-stream/resources.py']
    inputs, intake = base.canonical_inputs({name: (ROOT / name).read_bytes() for name in names})
    closure = dict(inputs)
    for name in (SELF, *PINNED):
        data = normalized(ROOT / name)
        require(name not in PINNED or sha(data) == PINNED[name], 'TCEC producer dependency changed: ' + name)
        require(name not in closure or closure[name] == data, 'conflicting source closure: ' + name)
        closure[name] = data
    out.mkdir()
    report = {
        'format': 1, 'class': 'tcec-full-Rust-A-v1', 'entry': 'Rust-A', 'family': 'A',
        'complete': False, 'reproducible': False,
        'resources': {'workers': 2, 'tt_bits': 18, 'ply': 128, 'max_position_plies': 4095},
        'policy': {'runtime': 'final', 'final': 'exit', 'wrapper': 'pipe', 'input_profile': 'finite-tcec'},
        'runtime_policy': {'mode': 'final', 'variant': None, 'startup_threads': 3,
            'active_threads': 3, 'between_GO_threads': 3, 'input_during_GO': 'asynchronous',
            'terminal': 'process-exit', 'worker_learning': 'persistent', 'full_promotions': 'NBRQ'},
        'qualification': {'selection': 'selected-literal-recipe', 'runtime': False,
                          'rules_eligibility': 'unproven', 'game_strength': 'unproven'},
        'authority': 'fresh canonical Rust closure and maintained exact specializer/merge/resource producers',
        'inputs': {name: pin(data) for name, data in sorted(closure.items())},
        'control_source_closure': {name: pin(data) for name, data in sorted(inputs.items())},
        'selected_verifier': {'path': VERIFIER, 'inputs': {name: pin(closure[name])
             for name in PINNED if name != PACKAGE}},
        'input_canonicalization': intake, 'compiler': list(COMMAND), 'compiler_environment': {},
        'compression': COMPRESSION, 'source_proofs': [], 'attempts': [],
        'not_proven': ['4 KiB eligibility', 'strength', 'NPS', 'target scaling', 'compiler cancellation'],
    }
    def save():
        (out / 'build.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    try:
        frozen = out / 'producer-repo'
        for name, data in closure.items():
            path = frozen / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        producer = load('tcec_rust_frozen_control', frozen / BUILDER)
        stable = load('tcec_rust_frozen_specializer', frozen / 'engines/compact/tiny-rust/build.py')
        merge = load('tcec_rust_frozen_merge', frozen / 'engines/experiments/tiny-rust-stream/merge.py')
        resource = load('tcec_rust_frozen_resources', frozen / 'engines/experiments/tiny-rust-stream/resources.py')
        packaging = load('tcec_rust_frozen_package', frozen / PACKAGE)
        version = producer.run_host([compiler, '--version', '--verbose'])
        require(version['stdout'].splitlines()[0].startswith('rustc 1.97.0 '), 'literal native needs Rust 1.97.0')
        report['host_compiler'] = version
        control = out / 'control'
        control.mkdir()
        control_args = SimpleNamespace(out=control, workers=2, tt_bits=18,
            embody_resources=True, prepared_input=True, omit_resource_environment=False,
            reproduce=True, smoke_selected=False)
        producer.execute_frozen(control_args, frozen, inputs, compiler)
        measured = json.loads((control / 'build.json').read_bytes())
        report['control'] = {'source': pin((control / 'merged.stdin.rs').read_bytes()),
            'native': pin((control / 'stdin-native/x').read_bytes()),
            'whole': pin(Path(measured['selected']['path']).read_bytes()), 'path': str(control)}
        header = packaging.tcec_header(compiler=COMMAND)
        report['wrapper_contract'] = packaging.tcec_contract(compiler=COMMAND)
        save()
        raw = {name: inputs[base.SOURCE_PREFIX + name] for name in base.PRODUCTION}
        generation = None
        for attempt in ('first', 'repeat'):
            directory = out / attempt
            directory.mkdir()
            pruned, pruning = stable.specialize(dict(raw), development=False)
            require({name: sha(data) for name, data in pruned.items()} == producer.PRUNED_BINDINGS,
                    'fresh minimal TCEC pruned source differs')
            merged, merging = merge.merge(pruned)
            source, resources = resource.embody(merged, workers=2, tt_bits=18)
            metadata = {'pruning': pruning, 'merge': merging, 'resources': resources}
            require(generation is None or generation == metadata, 'fresh source generation proof differs')
            generation = metadata
            require(source == (control / 'merged.stdin.rs').read_bytes(), 'control and new source differ')
            (directory / 'main.rs').write_bytes(source)
            native = producer.compile_stdin(stable, source, directory / 'native',
                                            [compiler, *COMMAND[1:]], {})
            report.setdefault('commands', []).append(native)
            whole = packaging.package_tcec(source, COMPRESSION, compiler=COMMAND)
            require(whole.startswith(header), 'minimal TCEC header differs')
            payload = whole[len(header):]
            decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
            require(decoder.decompress(payload, max_length=len(source) + 1) == source
                    and decoder.eof and not decoder.unused_data, 'strict TCEC source inverse differs')
            values = {'source': source, 'native': (directory / 'native/x').read_bytes(),
                      'whole': whole, 'header': header, 'payload': payload}
            for kind, expected in EXPECTED.items():
                require((len(values[kind]), sha(values[kind])) == expected,
                        'literal current Rust TCEC identity differs: ' + kind)
            require(pin(values['native']) == report['control']['native'],
                    'compact compiler without resource overrides changed native bytes')
            for name, data in [('x', whole), ('header.sh', header), ('payload.lzma', payload)]:
                (directory / name).write_bytes(data)
            (directory / 'x').chmod(0o700)
            (directory / 'source-proof.json').write_text('[]\n')
            expected = {prefix + '_' + key: value for prefix, data in values.items()
                        for key, value in pin(data).items()}
            report['attempts'].append({'directory': attempt, **expected, 'source_proofs': []})
            save()
        first, repeat = report['attempts']
        require({k: v for k, v in first.items() if k != 'directory'} ==
                {k: v for k, v in repeat.items() if k != 'directory'}, 'two fresh TCEC attempts differ')
        report['expected_contract'] = {k: v for k, v in first.items() if k not in ('directory', 'source_proofs')}
        report['source_generation'] = generation
        report['compiler_proof'] = {'native_equal_to_full_control': True,
            'removed': [['-C', 'debuginfo=0'], ['--check-cfg', 'cfg(tiny_dev)']],
            'joined_C_options': True, 'resource_options_embodied_in_source': True,
            'runtime_environment_overrides': {}}
        report['actual'] = {'source': 'main.rs', 'native': 'native/x', 'program': 'x'}
        for name in ('main.rs', 'native/x', 'x', 'header.sh', 'payload.lzma', 'source-proof.json'):
            path = out / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(out / 'first' / name, path)
        for name in ('x', 'native/x'):
            (out / name).chmod(0o700)
        report.update(complete=True, reproducible=True,
                      whole_delta_vs_control=EXPECTED['whole'][0] - report['control']['whole']['bytes'])
        save()
        print(json.dumps({'out': str(out), 'whole_bytes': EXPECTED['whole'][0],
            'source_bytes': EXPECTED['source'][0], 'native_bytes': EXPECTED['native'][0],
            'under_4096_bytes': False, 'runtime': 'not run by this producer'}))
    except BaseException as error:
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        save()
        raise


if __name__ == '__main__':
    main()
