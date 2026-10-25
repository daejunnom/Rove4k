#!/usr/bin/env python3
"""Run only the four selected whole-file minimal-UCI candidates and DEV controls.

Core feature/context/PLY proof receipts are separate evidence, produced by the
disjoint family proof helpers. This report makes no replacement for those gates.
The qualified A policy process checker is frozen unchanged, not weakened.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
A_ROOT = Path('/home/stemxstudio/rove4k-tiny-uci-min-verify-20261020')
A_PRODUCER = Path('/home/stemxstudio/rove4k-tiny-uci-min-20261020-v4')
INPUTS = {
    'policy-check.py': (A_ROOT / 'recipe/verify.py', '1e95b0a4e40c0584ca772b7545b73fcf758a0a82828f8dc9ba724ab812be0ddb'),
    'engines/experiments/tiny-protocol/edges.py': (A_ROOT / 'recipe/engines/experiments/tiny-protocol/edges.py', '253cf1c7d9d1a050de8e1275f46beefcf26bb065dbb308a2421386019c02a060'),
    'engines/tests/chess_oracle.py': (A_ROOT / 'recipe/engines/tests/chess_oracle.py', 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8'),
    'A-minimal-readable.c': (A_PRODUCER / 'minimal/combined.c', '38d6c829a4d98a172b01c945a20e091bd529a5998174896dbf0ad2dbc01a0a7b'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--portfolio', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(sys.platform == 'linux', 'requires Linux /proc')
    require(args.out.is_absolute(), 'new absolute external output required')
    out = args.out.resolve()
    require(not out.exists() and not any((p / '.git').exists() for p in (out, *out.parents)), 'new output outside Git required')
    raw_report = args.portfolio.read_bytes()
    portfolio = json.loads(raw_report)
    require(portfolio.get('complete') is True, 'producer is incomplete')
    require({row['family'] for row in portfolio['families']} == set('BCEF') and len(portfolio['families']) == 4,
            'exact four-family producer required')
    out.mkdir(parents=True)
    recipe = out / 'recipe'
    recipe.mkdir()
    report = {'complete': False, 'scope': 'selected whole source-stream candidates only; core proofs remain separate',
              'portfolio_sha256': sha(raw_report), 'validator_sha256': sha(Path(__file__).read_bytes()),
              'helpers': {}, 'families': [], 'shared_validator_modified': False}
    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    try:
        for name, (source, expected) in INPUTS.items():
            data = source.read_bytes()
            require(sha(data) == expected, 'qualified policy helper/input changed: ' + name)
            target = recipe / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            report['helpers'][name] = expected
        (recipe / 'verify.py').write_bytes(Path(__file__).read_bytes())
        transform_source = args.portfolio.parent / 'recipe/transform.py'
        data = transform_source.read_bytes()
        require(sha(data) == portfolio['tooling_sha256']['transform.py'], 'archived policy producer changed')
        (recipe / 'transform.py').write_bytes(data)
        transform = load('portfolio_runtime_transform', recipe / 'transform.py')
        policy = load('portfolio_frozen_policy_check', recipe / 'policy-check.py')
        raw = load('portfolio_frozen_raw_process', recipe / 'engines/experiments/tiny-protocol/edges.py')
        oracle = sys.modules['chess_oracle']
        report['oracle_self_check'] = oracle.self_check()
        a = (recipe / 'A-minimal-readable.c').read_bytes()
        ab, ae = transform.region(a.decode(), 'static void go(char *s){')
        a_go = a[ab:ae]
        for producer in portfolio['families']:
            family = producer['family']
            build_path = Path(producer['build'])
            build_bytes = build_path.read_bytes()
            require(sha(build_bytes) == producer['build_sha256'], 'family producer changed: ' + family)
            build = json.loads(build_bytes)
            require(build.get('complete') is True and build['family'] == family and build['DEV_source_native_exactly_unchanged'], 'family is incomplete')
            records = {row['id']: row for row in build['engines']}
            require(set(records) == {'baseline', 'minimal'}, 'one policy/control pair required')
            original, minimal = records['baseline'], records['minimal']
            for record in (original, minimal):
                for path, expected in ((record['readable'], record['readable_sha256']),
                                       (record['source'], record['source_sha256']),
                                       (record['native'], record['native_sha256']),
                                       (record['dev'], record['dev_native_sha256']),
                                       (record['command'][0], record['whole_sha256'])):
                    require(sha(Path(path).read_bytes()) == expected, 'actual artifact changed: ' + path)
            before, after = Path(original['readable']).read_bytes(), Path(minimal['readable']).read_bytes()
            regenerated, proof = transform.transform(before, family)
            require(regenerated == after and proof == build['policy'], 'policy transformation/body proof no longer matches')
            gb, ge = transform.region(after.decode(), 'static void go(char *s){')
            require(after[gb:ge] == a_go, 'go policy differs from the exact qualified A function')
            require(original['dev_source_sha256'] == minimal['dev_source_sha256'] and
                    original['dev_native_sha256'] == minimal['dev_native_sha256'], 'DEV bytes changed')
            family_out = out / family
            family_out.mkdir()
            entry = {'family': family, 'build_sha256': sha(build_bytes), 'passed': False,
                     'source_sha256': minimal['source_sha256'], 'whole_sha256': minimal['whole_sha256'],
                     'native_sha256': minimal['native_sha256'], 'protected_sha256': proof['protected_sha256'],
                     'same_qualified_A_go_body_sha256': sha(a_go),
                     'A_modeled_proof_reuse_scope': 'exact go function/default and clock arithmetic only; no new family TT snapshot claim',
                     'shipping_runs': []}
            report['families'].append(entry)
            save()
            for eof in (False, True):
                entry['shipping_runs'].append(policy.run_shipping(minimal, 'wrapper', family_out, raw, oracle, eof_only=eof))
                save()
            entry['DEV'] = policy.run_dev(minimal, family_out, raw, oracle)
            entry['passed'] = True
            save()
            print(json.dumps({'family': family, 'shipping_sessions': len(entry['shipping_runs']), 'DEV': True, 'passed': True}), flush=True)
        report['complete'] = True
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
