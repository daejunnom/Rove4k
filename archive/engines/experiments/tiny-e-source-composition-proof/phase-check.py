#!/usr/bin/env python3
"""Five controlled startup schedules against unchanged E DEV0 composition.

The pinned A startup fixture's scheduling, real pthread target accounting and
assertions are reused unchanged; only its source-event hash is adapted to E.
This is new E diagnostic execution evidence, not inherited A/C/F execution.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CANDIDATE = 'c5f005b107f5d3fa93a4043fece78de848e248e67c4e58831a688efae8f2941d'
OLD = '0a7fe69022051e1893ffbd52ade7a2fbb3f342fe20b581bb786d6997b46fb712'
GENERATOR = '2f6112ce64a0c73abec6ffbd64ae69a495f116d9fcedfeb37870d4207c61363e'
SUPPORT = '10cffa19a48b3d604fe22dfff468af27f2e01d30d86a1e39e2b5e410cf9df30e'
INPUTS = '6c087b741124bc9ac5c311de1c19f6ad17ce341af10d13c5b1a5222251aa38f5'
PREFIX = 'edd3076de238d6555b48b85b950fcf9351cb186b8cdb270c838a8a39fe957f05'
ORIGINAL_EVENT = '71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734'
ORIGINAL_CHECK = '5ff17cf735d6b8eb273860f2419d269fcc958edd9a8a5def3ffeda7af2290f69'
ORIGINAL_CONTRACT = '7b2cc56148c5de5f71f27c162235dcace03617f2b508d1a34dbb8404a1d8620e'
CONTRACT = 'd13a0bfd22a2328a60d25652a78438fc2fa8764b982d27fd0cce7e312ee7327f'
CASES = ('success-early', 'success-late', 'fail-0', 'fail-1-early', 'fail-1-late')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def admit(root):
    candidate = (root / 'candidate.c').read_bytes()
    old = (root / 'control/engines/compact/tiny-entry-e/engine.c').read_bytes()
    raw = (root / 'generate.py').read_bytes()
    require(sha(candidate) == CANDIDATE and sha(old) == OLD and sha(raw) == GENERATOR,
            'E production source/generator literal identity changed')
    generator = module('phase_E_frozen_generator', root / 'generate.py')
    require(len(generator.EDITS) == 8, 'exact eight-site E composition required')
    require(generator.readable(old) == candidate, 'E candidate is not exact forward composition')
    forward, stages = old, []
    for before, after in generator.EDITS:
        require(forward.count(before) == 1, 'old E composition site is not unique')
        position = forward.index(before)
        stages.append((position, before, after))
        forward = forward[:position] + after + forward[position + len(before):]
    require(forward == candidate, 'recorded E forward composition differs')
    reverse = candidate
    for position, before, after in reversed(stages):
        require(reverse[position:position + len(after)] == after,
                'recorded E composition slice differs during inverse')
        reverse = reverse[:position] + before + reverse[position + len(after):]
    require(reverse == old, 'E composition inverse differs')
    marker = b'void think(Worker *w,const Board *p)'
    require(old.count(marker) == candidate.count(marker) == 1, 'E think marker count changed')
    prefix = old[:old.index(marker)]
    require(len(prefix) == 18042 and sha(prefix) == PREFIX
            and prefix == candidate[:candidate.index(marker)], 'E model/Board/search prefix changed')
    return {'candidate_sha256': CANDIDATE, 'control_sha256': OLD,
            'generator_sha256': GENERATOR, 'exact_literal_sites': 8,
            'exact_forward_and_inverse': True, 'unchanged_prefix_bytes': len(prefix),
            'unchanged_prefix_sha256': PREFIX, 'model_board_search_prefix_byte_identical': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p / '.git').exists() for p in (out, *out.parents)):
        parser.error('new absolute output outside Git required')
    out.mkdir(parents=True)
    frozen = out / 'frozen'
    frozen.mkdir()
    report = {'complete': False, 'passed': False, 'scope': __doc__, 'cases': [], 'inputs': {},
              'profile': {'workers': 2, 'tt_bits': 18, 'DEV': 0, 'ISA': 'generic x86-64; no AVX2 flag'},
              'private_differences': ['startup wait changes pre-first-GO stopped to1',
                                      'direct think clears caller-preseeded best; this fixture never calls think'],
              'fixture_execution_attempts': 0, 'fixture_executions': 0, 'wrapper_executions': 0,
              'excluded': ['whole wrapper execution', 'search/model/board matrix execution',
                           'search/query/deadline proof', 'join-failure safety',
                           'TSAN/SAN race proof', 'performance', 'variant sweep']}
    tools = None

    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    save()
    try:
        manifest_raw = (HERE / 'inputs.json').read_bytes()
        require(sha(manifest_raw) == INPUTS and b'\r' not in manifest_raw,
                'literal E proof closure changed or is not raw LF')
        manifest = json.loads(manifest_raw)
        for prefix, key in [('control', 'control_files'), ('reference', 'reference_files')]:
            for name, pin in manifest[key].items():
                raw = (HERE / prefix / name).read_bytes()
                require(b'\r' not in raw and len(raw) == pin['bytes'] and sha(raw) == pin['sha256'],
                        'frozen proof input changed: ' + prefix + '/' + name)
                target = frozen / prefix / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                report['inputs'][prefix + '/' + name] = {'bytes': len(raw), 'raw_sha256': sha(raw)}
                save()
        for name in ['phase-check.py', 'phase-contract.c', 'inputs.json']:
            raw = manifest_raw if name == 'inputs.json' else (HERE / name).read_bytes()
            require(b'\r' not in raw, 'owned phase source must use raw LF')
            (frozen / name).write_bytes(raw)
            report['inputs'][name] = {'bytes': len(raw), 'raw_sha256': sha(raw)}
            save()
        require(sha((frozen / 'phase-contract.c').read_bytes()) == CONTRACT,
                'owned E phase diagnostic source changed')
        report['source_transform'] = admit(frozen / 'control')
        reference_path = frozen / 'reference/engines/experiments/tiny-a-startup'
        original = (reference_path / 'phase-contract.c').read_bytes()
        require(sha(original) == ORIGINAL_CONTRACT
                and sha((reference_path / 'phase-check.py').read_bytes()) == ORIGINAL_CHECK,
                'original startup fixture/assertion source identity changed')
        require(original.count(ORIGINAL_EVENT.encode()) == 1
                and original.replace(ORIGINAL_EVENT.encode(), CANDIDATE.encode())
                == (frozen / 'phase-contract.c').read_bytes(),
                'startup instrumentation differs beyond target source-event identity')
        reference = module('phase_E_original_A_assertions', reference_path / 'phase-check.py')
        reference.CANDIDATE = CANDIDATE
        require(reference.CASES == CASES, 'original five controlled startup schedules changed')
        require(sha((frozen / 'control/support.py').read_bytes()) == SUPPORT,
                'owned C support primitive changed')
        tools = module('phase_E_owned_C_support', frozen / 'control/support.py')
        command = ['cc', '-std=c11', '-Os', '-pthread', '-DDEV=0', '-DWORKERS=2', '-DTT_BITS=18',
                   '-DPRODUCTION_SOURCE="' + str(frozen / 'control/candidate.c') + '"',
                   str(frozen / 'phase-contract.c'), '-o', str(out / 'phase-contract')]
        report.update(compile_command=command, source_sha256=CANDIDATE,
                      diagnostic_source_sha256=CONTRACT,
                      fixture_adaptation='original A scheduling/thread-target/interposition source; source-event hash only')
        save()
        result = tools.run(command, out, timeout=90)
        (out / 'compile.stdout').write_bytes(result.stdout)
        (out / 'compile.stderr').write_bytes(result.stderr)
        report.update(compile_returncode=result.returncode, tool_commands=tools.COMMANDS)
        save()
        require(result.returncode == 0, 'E phase diagnostic failed to compile; raw logs preserved')
        report['diagnostic_native_sha256'] = sha((out / 'phase-contract').read_bytes())
        save()
        for name in reference.CASES:
            report['fixture_execution_attempts'] += 1
            save()
            row = reference.run_case(out / 'phase-contract', name, out)
            report['cases'].append(row)
            report['fixture_executions'] = sum(isinstance(case.get('pid'), int) for case in report['cases'])
            save()
            require(isinstance(row.get('pid'), int), 'startup diagnostic process identity missing')
            row['owned_group_members_after_case'] = tools.group_members(row['pid'])
            row['owned_group_absent'] = not row['owned_group_members_after_case']
            save()
            require(row['owned_group_absent'], 'diagnostic group remains after case')
            print(json.dumps({'case': name, 'passed': row['passed'], 'returncode': row.get('returncode')}), flush=True)
            require(row['passed'], 'E phase case failed: ' + name)
        require(all(row['terminal'] and row['group_absent'] and row['returncode'] == 0
                    for row in tools.COMMANDS), 'owned compiler group did not settle successfully')
        report.update(complete=True, passed=True, passed_count=5, total=5, owned_live_handles=0,
                      expected_creation_failure_status=2)
        save()
        print(json.dumps({'complete': True, 'out': str(out),
                          'results_sha256': sha((out / 'results.json').read_bytes())}), flush=True)
    except BaseException as error:
        report.update(complete=False, passed=False, error=repr(error),
                      passed_count=sum(bool(row.get('passed')) for row in report['cases']),
                      total=len(report['cases']))
        if tools is not None:
            report['tool_commands'] = tools.COMMANDS
        save()
        raise


if __name__ == '__main__':
    main()
