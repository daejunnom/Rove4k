#!/usr/bin/env python3
"""Five controlled startup schedules against unchanged F DEV0 composition.

The owned A startup fixture's scheduling, real pthread target accounting and
assertions remain unchanged; only the target source-event hash is adapted.
This is new F execution evidence, not inherited A or C execution evidence.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CANDIDATE = 'ec39b5641ac9fc5ab19a0c919c05e0d68169b461cc1d32afeee83274926becbd'
OLD = 'dc065b98d99a147f862bd2d4cb0a1349ff79a2da7c1be873d906dff71cc9cd89'
ORIGINAL_EVENT = '71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734'
TRANSFORM = 'ad4c012792ac9c9b1dc77495fe57956621d0855cc8d0a1597f4c1d26c1332aba'
TOOLS = 'f7b26670d27138229fbd20ac3207b2e48367cb878291ae42c3e40402e088a83e'
PREFIX = 'c3be7fdf0085a74173525f84d9cbb730304c27c70b20a66c853e4d2b72dd9ce2'
INPUTS = '984bbab15969fad134b1b6237e37be26c544573813adc56cdd0210d7d2e5aeed'


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
    old = (root / 'control/engines/compact/tiny-entry-f/engine.c').read_bytes()
    raw = (root / 'transform.json').read_bytes()
    require(sha(candidate) == CANDIDATE and sha(old) == OLD and sha(raw) == TRANSFORM,
            'F production source/transform literal identity changed')
    transform = json.loads(raw)
    require(len(transform['sites']) == 7, 'exact seven-site composition required')
    text = old.decode()
    for site in transform['sites']:
        require(text.count(site['old']) == 1, 'old composition site is not unique')
        text = text.replace(site['old'], site['new'])
    require(text.encode() == candidate, 'F candidate is not exact forward composition')
    for site in reversed(transform['sites']):
        require(text.count(site['new']) == 1, 'new composition site is not unique')
        text = text.replace(site['new'], site['old'])
    require(text.encode() == old, 'F composition inverse differs')
    prefix = old[:old.index(b'void think(')]
    require(len(prefix) == 15340 and sha(prefix) == PREFIX
            and prefix == candidate[:candidate.index(b'void think(')], 'F search prefix changed')
    start, end = b'    w->length=game_length;', b'static pthread_mutex_t mutex='
    driver = old[old.index(start):old.index(end)]
    require(driver == candidate[candidate.index(start):candidate.index(end)], 'F MTD driver changed')
    return {'candidate_sha256': CANDIDATE, 'control_sha256': OLD, 'exact_literal_sites': 7,
            'exact_forward_and_inverse': True, 'search_prefix_bytes': len(prefix),
            'search_prefix_sha256': PREFIX, 'MTD_driver_bytes': len(driver),
            'MTD_driver_after_job_reset_byte_identical': True}


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
    report = {'complete': False, 'scope': __doc__, 'cases': [], 'inputs': {},
              'profile': {'workers': 2, 'tt_bits': 18, 'DEV': 0, 'ISA': 'generic x86-64; no AVX2 flag'},
              'private_differences': ['startup wait changes pre-first-GO stopped to1',
                                      'direct think clears caller-preseeded best; this fixture never calls think'],
              'excluded': ['whole wrapper execution', 'search/query/deadline proof',
                           'join-failure safety', 'TSAN/SAN race proof', 'performance', 'variant sweep']}

    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')

    save()
    try:
        manifest_raw = (HERE / 'inputs.json').read_bytes()
        require(sha(manifest_raw) == INPUTS, 'literal F proof closure changed')
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
        for name in ['phase-check.py', 'phase-contract.c', 'inputs.json']:
            raw = (HERE / name).read_bytes()
            require(b'\r' not in raw, 'owned phase source must use LF')
            (frozen / name).write_bytes(raw)
            report['inputs'][name] = {'bytes': len(raw), 'raw_sha256': sha(raw)}
        report['source_transform'] = admit(frozen / 'control')
        reference_path = frozen / 'reference/engines/experiments/tiny-a-startup'
        original = (reference_path / 'phase-contract.c').read_bytes()
        require(original.count(ORIGINAL_EVENT.encode()) == 1
                and original.replace(ORIGINAL_EVENT.encode(), CANDIDATE.encode())
                == (frozen / 'phase-contract.c').read_bytes(),
                'startup instrumentation differs beyond target source-event identity')
        reference = module('phase_F_assertions', reference_path / 'phase-check.py')
        reference.CANDIDATE = CANDIDATE
        require(sha((frozen / 'control/tools.py').read_bytes()) == TOOLS, 'owned F tool primitive changed')
        tools = module('phase_F_owned_tools', frozen / 'control/tools.py')
        command = ['cc', '-std=c11', '-Os', '-pthread', '-DDEV=0', '-DWORKERS=2', '-DTT_BITS=18',
                   '-DPRODUCTION_SOURCE="' + str(frozen / 'control/candidate.c') + '"',
                   str(frozen / 'phase-contract.c'), '-o', str(out / 'phase-contract')]
        report.update(compile_command=command, source_sha256=CANDIDATE,
                      fixture_adaptation='original A scheduling/thread-target/interposition source; source-event hash only')
        save()
        result = tools.run(command, out, timeout=90)
        (out / 'compile.stdout').write_bytes(result.stdout)
        (out / 'compile.stderr').write_bytes(result.stderr)
        report.update(compile_returncode=result.returncode, tool_commands=tools.COMMANDS)
        require(result.returncode == 0, 'F phase diagnostic failed to compile')
        report['diagnostic_native_sha256'] = sha((out / 'phase-contract').read_bytes())
        save()
        for name in reference.CASES:
            row = reference.run_case(out / 'phase-contract', name, out)
            require(not tools.group_members(row['pid']), 'diagnostic group remains after case')
            row['owned_group_absent'] = True
            report['cases'].append(row)
            save()
            print(json.dumps({'case': name, 'passed': row['passed'], 'returncode': row.get('returncode')}), flush=True)
            require(row['passed'], 'F phase case failed: ' + name)
        report.update(complete=True, passed_count=5, total=5, owned_live_handles=0,
                      expected_creation_failure_status=2, fixture_executions=5, wrapper_executions=0)
        save()
        print(json.dumps({'complete': True, 'out': str(out),
                          'results_sha256': sha((out / 'results.json').read_bytes())}), flush=True)
    except BaseException as error:
        report['error'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
