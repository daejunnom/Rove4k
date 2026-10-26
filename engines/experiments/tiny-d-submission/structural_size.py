"""Reproduce a finite full-feature D structural-size portfolio from canonical source.

No selected recipe, historical authority, shared engine source or release is
changed. Output retains readable candidate C, actual compiler inputs, every
whole package, and rejected native-identity trials. --check invokes the existing
independent rules/search observers; it does not mint tournament qualification.
"""
import argparse
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import sys

sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent
ROOT = D.parents[2]
FILES = ('tiny.h', 'board.c', 'search.c', 'runtime.c', 'start.S', 'image.ld')
MODULES = {}


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def inventory(files):
    return {name: pin(data) for name, data in sorted(files.items())}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def modules():
    if not MODULES:
        for name in ('source', 'build', 'storage', 'test_startup', 'publication',
                     'process_owner', 'syscall_arity', 'valid_input', 'search_compact',
                     'no_tid_startup', 'd_square_successor', 'packaging',
                     'compressed_bootstrap', 'reduce', 'probe_d_square_successor'):
            MODULES[name] = load('structural_cost_' + name, D / (name + '.py'))
        for name, relative in (
                ('lexical', 'engines/scripts/rename_c.py'),
                ('minifier', 'engines/scripts/minify.py'),
                ('packer', 'engines/compact/tiny-entry-d/packer.py'),
                ('host', 'engines/experiments/tcec-scope/build.py')):
            MODULES[name] = load('structural_cost_' + name, ROOT / relative)
    return MODULES


def prepare_baseline(profile='test-p4'):
    m = modules()
    profile_name = profile
    profile = m['source'].production().resource_profile(profile)
    files, production = m['test_startup'].prepared(m['source'], profile, True, m['storage'], 'prefix')
    files, owner = m['process_owner'].transform(files, m['publication'])
    files, arity = m['syscall_arity'].transform(files, m['process_owner'], m['publication'], owner,
                                               noinline_wake=True, immediate_exit=True)
    files, valid = m['valid_input'].transform(files, m['syscall_arity'], m['process_owner'],
                                             m['publication'], arity, mode='one-byte-valid')
    files, search = m['search_compact'].transform(files, m['valid_input'], m['syscall_arity'],
        m['process_owner'], m['publication'], valid, options=('previous-piece', 'unsigned-history'))
    files, no_tid = m['no_tid_startup'].transform(files)
    files, square = m['d_square_successor'].transform(files)
    return files, dict(source_preparation_profile=profile_name,
                       production=production, owner=owner, arity=arity, valid=valid,
                       search=search, no_tid=no_tid, square=square)


def load_baseline():
    return prepare_baseline()[0]


def measure(files, out, *, label='candidate', flags_extra=(), optimize='s', repeat=False,
            profile='test-p4'):
    """Compare full linked/native images and all three unchanged whole routes."""
    m = modules()
    out = Path(out)
    if (not out.is_absolute() or out.exists() or
            any((p / '.git').exists() for p in (out, *out.parents))):
        raise ValueError('new absolute output outside every Git checkout required')
    if set(files) != set(FILES) or not all(type(v) is bytes for v in files.values()):
        raise ValueError('complete six-file readable D source required')
    out.mkdir(parents=True)
    raw = out / 'generated-readable'
    raw.mkdir()
    for name, data in files.items():
        (raw / name).write_bytes(data)
    resource = m['source'].production().resource_profile(profile)
    flags = m['build'].native_flags(resource, optimize)
    flags.extend(flags_extra)
    report = dict(label=label, complete=False, input=inventory(files), flags=flags,
                  profile=profile, workers=resource.workers,
                  commands=[], native_runs=[], packages={},
                  engine_executed=False, runtime_qualified=False, selected=False,
                  harness=pin(Path(__file__).read_bytes()),
                  tools={str(Path(v.__file__).relative_to(ROOT)): pin(Path(v.__file__).read_bytes())
                         for v in m.values()})
    def save():
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    h = m['host']
    h.LIMITS = {**h.LIMITS, 'aggregate_wall': 180, 'per_command_wall': 45,
                'parent_CPU': 1200, 'parent_CPU_hard': 1260, 'child_CPU': 40,
                'tool_output_bytes': 8 << 20}
    host = h.Host(out, report, save)
    try:
        report['compiler'] = host.run(['cc', '--version'], cwd=out, kind='compiler').decode().splitlines()[0]
        cpp = host.run(['cc', '-E', '-P', *flags, '-I', str(raw), '-x', 'c', '-'], cwd=raw,
                       kind='cpp', data=m['probe_d_square_successor'].DRIVER)
        entry = host.run(['cc', '-E', '-P', '-x', 'assembler-with-cpp', str(raw / 'start.S')],
                         cwd=raw, kind='assembly-cpp')
        emitted = {'main.c': m['minifier'].compact_source(cpp, 'c'), 'start.S': entry,
                   'image.ld': files['image.ld']}
        legacy = m['probe_d_square_successor'].LEGACY
        words = m['lexical']._ANY_WORD.findall(emitted['main.c'].decode())
        if set(legacy.values()).intersection(words):
            raise ValueError('legacy names would capture candidate identifiers')
        mapped = {'main.c': emitted['main.c']}
        for old, new in legacy.items():
            mapped = m['lexical']._replace(mapped, old, new)
        emitted.update(mapped)
        gate = 0
        def compile_files(contents, directory, kind):
            directory.mkdir()
            for name, data in contents.items():
                (directory / name).write_bytes(data)
            host.run(['cc', *flags, str(directory / 'main.c'), str(directory / 'start.S'),
                      '-Wl,-T,' + str(directory / 'image.ld'), '-o', str(directory / 'linked')],
                     cwd=directory, kind=kind)
            linked = (directory / 'linked').read_bytes()
            native = m['packer'].strip_native(linked)
            (directory / 'native').write_bytes(native)
            return linked, native
        def digest(contents, trial):
            nonlocal gate
            gate += 1
            linked, _ = compile_files({**emitted, **contents}, out / ('gate-' + trial), 'reduce-' + trial)
            return pin(linked)['sha256']
        reduced, reduction = m['reduce'].reduce_sources({'main.c': emitted['main.c']}, digest,
            m['lexical'], reserve=m['lexical']._ANY_WORD.findall((entry + emitted['image.ld']).decode()))
        emitted.update(reduced)
        report['reduction'] = reduction
        shipping = out / 'shipping-inputs'
        shipping.mkdir()
        for name, data in emitted.items():
            (shipping / name).write_bytes(data)
        report['shipping'] = inventory(emitted)
        linked, native = compile_files(emitted, out / 'native', 'native')
        if report['commands'][-1]['stderr']['bytes']:
            raise ValueError('final accepted native compiler emitted diagnostics')
        if pin(linked)['sha256'] != reduction['final_native_sha256']:
            raise ValueError('shipping native differs from reducer gate')
        report['native_runs'].append({'linked': pin(linked), 'native': pin(native)})
        if repeat:
            again = compile_files(emitted, out / 'repeat', 'native-repeat')
            if again != (linked, native):
                raise ValueError('repeat native differs')
            report['native_runs'].append({'linked': pin(again[0]), 'native': pin(again[1])})
        for route in ('source-jit', 'source-jit-compressed', 'packed-xz-bcj'):
            if route == 'source-jit':
                whole, detail = m['packaging'].package_source(emitted, flags, ('main.c', 'start.S'))
            elif route == 'source-jit-compressed':
                whole, detail = m['compressed_bootstrap'].package_source(emitted, flags,
                    ('main.c', 'start.S'), m['packaging'])
            else:
                whole, detail = m['packaging'].package_native(native, 'xz-bcj')
            (out / route).write_bytes(whole)
            report['packages'][route] = {**pin(whole), **detail}
        # A measured option for this complete native only; shared defaults stay
        # untouched. CRC64 and the original memfd/exec bootstrap are preserved.
        payload = lzma.compress(native, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64,
            filters=[{'id': lzma.FILTER_X86}, {'id': lzma.FILTER_LZMA2,
                'preset': 9 | lzma.PRESET_EXTREME, 'dict_size': 8192,
                'lc': 3, 'lp': 0, 'pb': 0}])
        if lzma.decompress(payload) != native:
            raise ValueError('tuned codec complete native inverse differs')
        whole, header = m['packaging'].envelope(m['packaging'].NATIVE_CODE, payload)
        (out / 'packed-xz-bcj-pb0').write_bytes(whole)
        report['packages']['packed-xz-bcj-pb0'] = {
            **pin(whole), 'header_bytes': len(header), 'payload_bytes': len(payload),
            'codec': 'xz-bcj', 'check': 'CRC64', 'dict_size': 8192, 'lc': 3, 'lp': 0, 'pb': 0,
            'restoration': 'complete kernel-executable ELF', 'cleanup': 'memfd-CLOEXEC'}
        report['complete'] = True
    except BaseException as error:
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        host.close()
        save()
    return report


def transforms():
    return {name: load('D_structural_' + name, D / ('structural_' + name + '.py'))
            for name in ('board', 'search', 'runtime')}


def candidate(files, selection, modules=None):
    """Explicit composition; family optima need not be the combined optimum."""
    modules = modules or transforms()
    result = dict(files)
    for name in ('board', 'search', 'runtime'):
        result = modules[name].apply(result, selection.get(name, ()))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--profile', choices=('test-p4', 'test-p28', 'tcec-provisional'), default='test-p4')
    parser.add_argument('--case', action='append', choices=('board', 'search', 'runtime', 'full'),
                        help='finite named candidates; baseline is always measured')
    parser.add_argument('--check', action='store_true', help='plain/UBSan rules and exact search observations; P4 only')
    args = parser.parse_args()
    out = args.out
    if (not out.is_absolute() or out.exists() or
            any((p / '.git').exists() for p in (out, *out.parents))):
        parser.error('new absolute output outside every Git checkout required')
    if args.check and args.profile != 'test-p4':
        parser.error('local semantic observer is P4; other profiles are build-only')
    out.mkdir(parents=True)
    base, chain = prepare_baseline(args.profile)
    (out / 'source-chain.json').write_text(json.dumps(chain, indent=2) + '\n')
    modules = transforms()
    selections = {'board': {'board': modules['board'].BEST},
                  'search': {'search': modules['search'].BEST},
                  'runtime': {'runtime': modules['runtime'].BEST},
                  'full': {'board': modules['board'].BEST,
                           'search': modules['search'].BEST,
                           'runtime': modules['runtime'].BEST}}
    summary = {'profile': args.profile, 'source': inventory(base), 'cases': [],
               'transforms': {name: pin(Path(module.__file__).read_bytes()) for name, module in modules.items()},
               'selected': False, 'runtime_qualified': False}
    for name in ('control', *dict.fromkeys(args.case or ('full',))):
        selection = selections.get(name, {})
        files = candidate(base, selection, modules)
        report = measure(files, out / name, label=name, repeat=True, profile=args.profile)
        summary['cases'].append({'name': name, 'options': selection,
            'native': report['native_runs'][0]['native'],
            'whole': {key: value['bytes'] for key, value in report['packages'].items()}})
        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps(summary['cases'][-1]), flush=True)
        if args.check:
            checker = load('D_structural_checks', D / 'structural_checks.py')
            checker.check(out / name, out / (name + '-checks'),
                          control=out / 'control-checks' if name != 'control' else None)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
