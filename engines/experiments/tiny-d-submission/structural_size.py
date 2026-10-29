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


def new_output(value):
    """Resolve a new absolute output before checking its real Git ancestry."""
    out = Path(value)
    if not out.is_absolute():
        raise ValueError('new absolute output outside every Git checkout required')
    out = out.resolve()
    if out.exists() or any((p / '.git').exists() for p in (out, *out.parents)):
        raise ValueError('new absolute output outside every Git checkout required')
    return out


def require_settled_cost(record):
    """Accept a complete cost observation only after its owner settled cleanly."""
    cleanup = record.get('host_cleanup') if type(record) is dict else None
    if (type(record) is not dict or record.get('complete') is not True or
            'failure' in record or 'cleanup_failure' in record or
            type(cleanup) is not dict or
            type(cleanup.get('unsettled_commands')) is not int or
            cleanup['unsettled_commands'] != 0 or
            type(cleanup.get('errors')) is not list or cleanup['errors']):
        raise ValueError('complete cost observation with clean owner settlement required')


def finish_report(host, report, save, body_error=None):
    """Close before success; retain a body exception if cleanup also fails."""
    cleanup_error = None
    report['complete'] = False
    try:
        if host is not None:
            host.close()
        if body_error is None:
            report['complete'] = True
            require_settled_cost(report)
    except BaseException as error:
        cleanup_error = error
        report['complete'] = False
        report['cleanup_failure'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        try:
            save()
        except BaseException as error:
            report['complete'] = False
            report['save_failure'] = {'type': type(error).__name__, 'message': str(error)}
            if body_error is None and cleanup_error is None:
                raise
    if cleanup_error is not None and body_error is None:
        raise cleanup_error


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
    out = new_output(out)
    m = modules()
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
    host = None
    body_error = None
    try:
        host = h.Host(out, report, save)
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
    except BaseException as error:
        body_error = error
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        finish_report(host, report, save, body_error)
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


def self_test():
    """Exercise the actual receipt/path helpers without loading engine tools."""
    import tempfile

    checks = 0
    def require(value):
        if not value:
            raise AssertionError('structural harness self-test failed')

    def reject(record):
        nonlocal checks
        try:
            require_settled_cost(record)
        except ValueError:
            checks += 1
        else:
            raise AssertionError('malformed settlement accepted')

    clean = {'complete': True, 'host_cleanup': {'unsettled_commands': 0, 'errors': []}}
    require_settled_cost(clean)
    checks += 1
    for record in (None, {}, {**clean, 'complete': 1},
                   {**clean, 'host_cleanup': None},
                   {**clean, 'host_cleanup': {'unsettled_commands': False, 'errors': []}},
                   {**clean, 'host_cleanup': {'unsettled_commands': 1, 'errors': []}},
                   {**clean, 'host_cleanup': {'unsettled_commands': 0, 'errors': ['failed']}},
                   {**clean, 'host_cleanup': {'unsettled_commands': 0, 'errors': ()}},
                   {**clean, 'failure': {}}, {**clean, 'cleanup_failure': {}}):
        reject(record)

    class Owner:
        def __init__(self, report, save, error):
            self.report, self.save, self.error = report, save, error

        def close(self):
            self.report['host_cleanup'] = {'unsettled_commands': int(self.error is not None),
                                          'errors': [str(self.error)] if self.error else []}
            self.save()  # The retained Host also saves before its final checks.
            if self.error is not None:
                raise self.error

    for body_fails, close_fails in ((False, False), (False, True), (True, False), (True, True)):
        report, observed = {'complete': False}, []
        def save():
            observed.append(json.loads(json.dumps(report)))
        body = RuntimeError('body failure') if body_fails else None
        closing = OSError('close failure') if close_fails else None
        owner = Owner(report, save, closing)
        caught = None
        try:
            try:
                if body is not None:
                    raise body
            except BaseException as error:
                report['failure'] = {'type': type(error).__name__, 'message': str(error)}
                raise
            finally:
                finish_report(owner, report, save, body)
        except BaseException as error:
            caught = error
        require(caught is (body if body is not None else closing))
        require(report['complete'] is (not body_fails and not close_fails))
        require(observed[-1] == report and all(not row['complete'] for row in observed[:-1]))
        require(('cleanup_failure' in report) is close_fails)
        if body_fails or close_fails:
            reject(report)
        else:
            require_settled_cost(report)
        checks += 1

    def rejected_path(path):
        nonlocal checks
        try:
            new_output(path)
        except ValueError:
            checks += 1
        else:
            raise AssertionError('non-external or existing output accepted')

    rejected_path(Path('relative-structural-output'))
    with tempfile.TemporaryDirectory(prefix='rove4k-structural-self-test-') as temporary:
        root = Path(temporary).resolve()
        require(new_output(root / 'new') == root / 'new')
        checks += 1
        checkout = root / 'checkout'
        (checkout / '.git').mkdir(parents=True)
        (checkout / 'subdirectory').mkdir()
        rejected_path(checkout / 'subdirectory' / 'new')
        rejected_path(checkout)
        alias = root / 'alias'
        alias.symlink_to(checkout / 'subdirectory', target_is_directory=True)
        rejected_path(alias / 'new')
        worktree = root / 'worktree'
        worktree.mkdir()
        (worktree / '.git').write_text('gitdir: external-test-only\n')
        rejected_path(worktree / 'new')
    print(json.dumps({'self_test': True, 'checks': checks, 'engine_modules_loaded': bool(MODULES)}))
    require(not MODULES)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--self-test', action='store_true', help='pure receipt/path regressions; no engine tools')
    parser.add_argument('--profile', choices=('test-p4', 'test-p28', 'tcec-provisional'), default='test-p4')
    parser.add_argument('--case', action='append', choices=('board', 'search', 'runtime', 'full'),
                        help='finite named candidates; baseline is always measured')
    parser.add_argument('--check', action='store_true', help='plain/UBSan rules and exact search observations; P4 only')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.out is None:
        parser.error('--out is required unless --self-test is selected')
    try:
        out = new_output(args.out)
    except ValueError as error:
        parser.error(str(error))
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
