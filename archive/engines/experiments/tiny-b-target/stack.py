#!/usr/bin/env python3
"""One byte-identical B target diagnostic compile and bounded C-stack accounting.

This freezes the exact first-cost inputs, adds only -fstack-usage to its stdin
compiler invocation, and never executes the engine. GCC .su frames and the
native direct-call/tail-call graph account for this translation unit only.
External libc, pthread, loader, signal and thread-entry frames are unmeasured.
"""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import subprocess


PINS = {
    'cost-report': '9794de8564b31404254fb14864827d40f4fb00323a40868abca6c26b9f9d3976',
    'source': '81cfb3099857a95a91f7e8f97caa080f938a6a73435277b75ea6201bc3b1b251',
    'readable': 'caadf2ed45ecde9fb760b2697f9f38b9023a6729870ea6eb8ff8472e0100d2ce',
    'native': '50e41afb800f86aff1022511d67d1bbba14c86c3a6e52a48233e1d5ce9174983',
}
COMPILER = ['cc', '-std=c11', '-Os', '-pthread', '-DWORKERS=2', '-DTT_BITS=18',
            '-DDEV=0', '-x', 'c', '-', '-o', 'x']
DIAGNOSTIC = COMPILER[:1] + ['-fstack-usage'] + COMPILER[1:]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def stack_frames(text):
    result = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        location, size, qualification = line.split('\t')
        name = location.rsplit(':', 1)[1]
        require(qualification in ('static', 'dynamic,bounded'),
                'unbounded or unknown GCC frame: ' + line)
        require(name not in result, 'duplicate GCC frame: ' + name)
        result[name] = {'bytes': int(size), 'qualification': qualification, 'location': location}
    require(result, 'no GCC stack frames')
    return result


def native_graph(text):
    symbols, instructions = {}, []
    current = None
    for line in text.splitlines():
        header = re.fullmatch(r'\s*[0-9a-f]+ <([^>]+)>:', line)
        if header:
            current = header.group(1)
            symbols.setdefault(current, set())
            continue
        item = re.match(r'\s*[0-9a-f]+:\s+(call\w*|jmp\w*)\s+(.+)', line)
        if item and current:
            instructions.append((current, item.group(1), item.group(2)))
    external, indirect = {}, {}
    for caller, operation, operand in instructions:
        match = re.search(r'<([^>]+)>', operand)
        if not match:
            if operand.startswith('*'):
                indirect.setdefault(caller, []).append(operation + ' ' + operand)
            continue
        callee = match.group(1)
        # A branch to an offset in the same function is ordinary control flow.
        if '+' in callee or '-' in callee:
            continue
        if '@' in callee or callee not in symbols:
            external.setdefault(caller, set()).add(callee)
        else:
            symbols[caller].add(callee)
    return symbols, external, indirect


def account(frames, graph, external, indirect):
    require(all(name in frames and name in graph for name in ('work', 'search', 'exchange')),
            'pinned worker/search/exchange symbols missing')
    reachable, pending, bindings = set(), ['work'], {}
    while pending:
        name = pending.pop()
        if name in reachable:
            continue
        reachable.add(name)
        # GCC13 .su labels omit the final numeric identifier on .isra.N and
        # .constprop.N clones. Resolve that exact spelling difference only.
        usage_name = name if name in frames else re.sub(r'\.(isra|constprop)\.\d+$', r'.\1', name)
        require(usage_name in frames, 'reachable native function has no GCC frame: ' + name)
        require(usage_name not in bindings.values() or bindings.get(name) == usage_name,
                'multiple native clones share an ambiguous GCC frame: ' + name)
        bindings[name] = usage_name
        require(not indirect.get(name), 'unresolved indirect worker transfer: ' + name)
        pending.extend(graph[name] - reachable)
    native_frames = {name: frames[usage_name] for name, usage_name in bindings.items()}
    # Each ordinary edge increases ply, and ply127 returns before recursing.
    # Same-ply excluded verification disables its own singular branch and
    # halves depth. Ordinary child depth never increases (extension<=1).
    depth, verification_chain = 126, []
    while depth >= 6:
        following = (depth - 1) // 2
        verification_chain.append([depth, following])
        depth = following
    max_search = 128 + len(verification_chain)
    # A legal SEE root has <=32 pieces. Every recapture removes one nonking;
    # two kings remain. A noncapture promotion can retain32 at the first call.
    # Thus <=30 recursive recaptures plus the initial exchange call =31 frames.
    max_exchange = 31
    active = set()

    @lru_cache(None)
    def maximum(name, searches, exchanges):
        if name == 'search':
            if not searches:
                return None
            searches -= 1
        if name == 'exchange':
            if not exchanges:
                return None
            exchanges -= 1
        state = (name, searches, exchanges)
        require(state not in active, 'unbounded non-search/exchange call cycle: ' + name)
        active.add(state)
        best = (native_frames[name]['bytes'], (name,))
        for child in sorted(graph[name]):
            suffix = maximum(child, searches, exchanges)
            if suffix is not None:
                # Count tail transfers as nested calls too. Add a separate
                # conservative16B/edge reserve rather than assuming .su's
                # return-address/outgoing-argument convention is disjoint.
                choice = (native_frames[name]['bytes'] + 16 + suffix[0], (name,) + suffix[1])
                if choice[0] > best[0]:
                    best = choice
        active.remove(state)
        return best

    bound, path = maximum('work', max_search, max_exchange)
    counts = {name: path.count(name) for name in sorted(set(path))}
    raw = sum(native_frames[name]['bytes'] for name in path)
    return {
        'entry': 'work', 'source_bound_assumptions': {
            'exact_pinned_DEV0_source': True, 'PLY': 128, 'iterative_max_depth': 126,
            'ordinary_ply_frames_upper_bound': 128,
            'same_ply_verification_depth_chain': verification_chain,
            'search_frames_upper_bound': max_search,
            'admitted_piece_count_upper_bound': 32, 'uncapturable_kings': 2,
            'recaptures_upper_bound': 30, 'exchange_frames_upper_bound': max_exchange,
            'initial_capture_exchange_frames_upper_bound': 30,
            'Move512_array_bytes_per_exchange': 2048,
            'exchange_arrays_only_upper_bound': 63488,
        },
        'reachable_functions': sorted(reachable),
        'native_to_gcc_frame_bindings': dict(sorted(bindings.items())),
        'internal_call_and_tail_call_graph': {name: sorted(graph[name]) for name in sorted(reachable)},
        'external_transfers': {name: sorted(external[name]) for name in sorted(reachable) if external.get(name)},
        'path_function_counts': counts, 'maximum_path': list(path),
        'gcc_frame_sum_bytes': raw, 'per_edge_extra_reserve_bytes': 16,
        'edge_reserve_total_bytes': 16 * (len(path) - 1),
        'compiler_accounted_conservative_worker_bytes': bound,
        'reference_stack_bytes': 1048576,
        'compiler_accounted_bytes_below_reference': 1048576 - bound,
        'whole_runtime_stack_qualified': False,
        'limitations': [
            'GCC frame reports and the native direct-call graph cover only this translation unit.',
            'Libc, pthread start/wait/stdio, dynamic loader and signal frames are not measured.',
            'No engine execution or empirical maximum-depth stack test is performed.',
            'The 1MiB reference is a comparison, not a newly enforced or fully qualified pthread stack.',
            'Tail transfers count conservatively as nested frames; recursion budgets deliberately overapproximate feasible paths.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cost-report', type=Path,
                        default=Path('/home/stemxstudio/rove4k-tiny-b-target-first-20261020/results.json'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--analyze-existing', action='store_true',
                        help='reuse this directory\'s recorded successful compile; never compile again')
    args = parser.parse_args()
    require(args.out.is_absolute(), 'absolute external output required')
    out = args.out.resolve()
    require(not any((parent / '.git').exists() for parent in (out, *out.parents)), 'output must be outside Git')
    report_data = args.cost_report.read_bytes()
    require(sha(report_data) == PINS['cost-report'], 'pinned first-cost report changed')
    cost = json.loads(report_data)
    require(cost['complete'] and cost['gain'] and cost['compiler_argv'] == COMPILER, 'first-cost admission differs')
    row = next(item for item in cost['forms'] if item['id'] == 'target')
    inputs = {'cost-report.json': report_data, 'stack.py': Path(__file__).read_bytes()}
    for name, field in (('source', 'source'), ('readable', 'readable'), ('native', 'native')):
        data = Path(row[field]).read_bytes()
        require(sha(data) == PINS[name] == row[name + '_sha256'], 'admitted input differs: ' + name)
        inputs[name] = data
    report = {'complete': False, 'scope': 'one byte-identical diagnostic compile; compiler-accounted C worker stack only',
              'engine_executed': False, 'base_compiler_argv': COMPILER, 'diagnostic_compiler_argv': DIAGNOSTIC,
              'input_sha256': {name: sha(data) for name, data in inputs.items()}}
    if args.analyze_existing:
        receipt = json.loads((out / 'compile.json').read_bytes())
        require(receipt['returncode'] == 0 and receipt['argv'] == DIAGNOSTIC and
                receipt['source_sha256'] == PINS['source'], 'existing compile receipt differs')
        require((out / 'recipe/source').read_bytes() == inputs['source'], 'existing frozen source differs')
        (out / 'analysis-stack.py').write_bytes(inputs['stack.py'])
    else:
        require(not out.exists(), 'new output directory required; use --analyze-existing for an admitted compile')
        (out / 'recipe').mkdir(parents=True)
        for name, data in inputs.items():
            (out / 'recipe' / name).write_bytes(data)
        process = subprocess.run(DIAGNOSTIC, cwd=out, input=inputs['source'], capture_output=True, timeout=90)
        (out / 'compile.stdout').write_bytes(process.stdout)
        (out / 'compile.stderr').write_bytes(process.stderr)
        receipt = {'argv': DIAGNOSTIC, 'source_sha256': PINS['source'], 'returncode': process.returncode,
                   'diagnostic_native_sha256': sha((out / 'x').read_bytes()) if (out / 'x').exists() else None}
        (out / 'compile.json').write_text(json.dumps(receipt, indent=2) + '\n')
    report['analysis_only_resume'] = args.analyze_existing
    report['original_compile_driver_sha256'] = sha((out / 'recipe/stack.py').read_bytes())
    report['frozen_input_files'] = {
        name: str(Path('analysis-stack.py') if args.analyze_existing and name == 'stack.py' else Path('recipe') / name)
        for name in inputs
    }
    for name, relative in report['frozen_input_files'].items():
        require((out / relative).read_bytes() == inputs[name], 'frozen input differs: ' + name)
    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    try:
        require(receipt['returncode'] == 0, 'diagnostic compile failed')
        native = (out / 'x').read_bytes()
        require(native == inputs['native'], 'entire diagnostic native differs from admitted target ELF')
        report['diagnostic_native_sha256'] = sha(native)
        report['entire_native_identical'] = True
        usage = sorted(out.glob('*.su'))
        require(len(usage) == 1, 'expected one compiler stack-usage output')
        report['stack_usage_file'] = usage[0].name
        report['stack_usage_sha256'] = sha(usage[0].read_bytes())
        frames = stack_frames(usage[0].read_text())
        report['gcc_frames'] = frames
        disassembly = subprocess.check_output(['objdump', '-d', '--no-show-raw-insn', 'x'], cwd=out)
        (out / 'disassembly.txt').write_bytes(disassembly)
        report['disassembly_sha256'] = sha(disassembly)
        report['compiler'] = subprocess.check_output(['cc', '--version'], text=True).splitlines()[0]
        report['objdump'] = subprocess.check_output(['objdump', '--version'], text=True).splitlines()[0]
        report['accounting'] = account(frames, *native_graph(disassembly.decode()))
        report['complete'] = True
        print(json.dumps({'complete': True, 'entire_native_identical': True,
                          'compiler_accounted_worker_bytes': report['accounting']['compiler_accounted_conservative_worker_bytes'],
                          'report': str(out / 'results.json')}), flush=True)
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
