#!/usr/bin/env python3
"""Explicit A5163 candidate adapter; exactly two unchanged canonical A sessions.

The A5207 recipe and verifier remain read-only. A separately named external
candidate recipe declares literal A5163 expected bytes, and the unchanged
canonical verifier executes its original quit/EOF/image/startup/legal-go gates.
No expectations are learned from the candidate under test.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CANDIDATE_SHA256 = '4f1562199786596c4addb36c1b47ecdcee143ca0338e8c986d350fe5639d1f8c'
CONTROL_SHA256 = '085fcf6bd411a59111aaebbdc6bd59e2687a5c38de2ce28f0ad9643882633e36'
SOURCE_SHA256 = '5e0e77321110371aec3a7a06f93290e7581f08f721fc9bb07fcef26c406429b7'
NATIVE_SHA256 = 'd39167146236aafde21b59439b853bd10561f04e9186c18b839c2f84f2e16e12'
BOOTSTRAP_SHA256 = '11679fb20e24e7cb777cb49e4bee5a7ee7ea999278651fbba6d622320e751d44'
FIRST_COST_SHA256 = 'd4b05dd0daae3e345e18f40d24eceb523d64b087bee811eb0f7c54b52d0c62b7'
FINAL_COST_SHA256 = '2cdc6859837ba17752bb8a30531bbee7cae8e647cdc183f438f4ab69cdbcd5df'
CANONICAL_PINS = {
    'engines/compact/tiny-entry-a/verify.py': 'cc63a511446c35db54676356a9d885b95db7da994133147cda3e3ff1c4464b0c',
    'engines/compact/tiny-entry-a/recipe.json': '749b6e102a581efe419de14e40bd7346afff18b5bc8b46c145084b11bb89456a',
    'engines/tests/verify.py': '9327ad01dd75bc17f04f400b57d5af3d6891a1abbb7f22aa6222389d50da138f',
    'engines/tests/chess_oracle.py': 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical_source(name):
    if name in ('engines/compact/tiny-entry-a/verify.py', 'engines/compact/tiny-entry-a/recipe.json'):
        return HERE/'control'/Path(name).name
    return REPO/name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cost', type=Path, required=True)
    parser.add_argument('--first-cost', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(args.out.is_absolute(), 'new absolute external output required')
    out = args.out.resolve()
    require(not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)), 'new output outside Git required')
    cost_raw, first_raw = args.cost.read_bytes(), args.first_cost.read_bytes()
    require(sha(cost_raw) == FINAL_COST_SHA256 and sha(first_raw) == FIRST_COST_SHA256, 'unknown fixed first-cost/repeat receipt')
    cost, first = json.loads(cost_raw), json.loads(first_raw)
    for data in (cost, first):
        require(data['complete'] and data['gain'] and not data['engine_campaign_run'], 'cost stage differs')
        require(data['records'][0]['whole_sha256'] == CONTROL_SHA256 and data['records'][0]['whole_bytes'] == 5207,
                'qualified control binding differs')
        require(data['records'][1]['whole_sha256'] == CANDIDATE_SHA256 and data['records'][1]['whole_bytes'] == 5163
                and data['records'][1]['source_sha256'] == SOURCE_SHA256
                and data['records'][1]['bootstrap_sha256'] == BOOTSTRAP_SHA256
                and data['records'][1]['original_native_sha256'] == NATIVE_SHA256, 'literal candidate binding differs')
    out.mkdir(parents=True)
    recipe = out/'recipe'
    recipe.mkdir()
    inputs = out/'inputs'
    inputs.mkdir()
    report = {'complete': False, 'scope': 'root-authorized exact two selected LZMA-alone sessions; unchanged canonical gates',
              'candidate_whole_sha256': CANDIDATE_SHA256, 'expected_native_sha256': NATIVE_SHA256,
              'first_cost_sha256': FIRST_COST_SHA256, 'repeat_cost_sha256': FINAL_COST_SHA256,
              'adapter_sha256': sha(Path(__file__).read_bytes()), 'canonical_inputs': {},
              'original_recipe_and_verifier_modified': False, 'broad_campaign_run': False}
    def save():
        (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    save()
    try:
        (inputs/'first-cost.json').write_bytes(first_raw)
        (inputs/'repeat-cost.json').write_bytes(cost_raw)
        (inputs/'candidate-adapter.py').write_bytes(Path(__file__).read_bytes())
        for name, expected in CANONICAL_PINS.items():
            raw = canonical_source(name).read_bytes()
            # Match exactly the canonical verifier's admitted shared-helper EOL
            # handling. Closed A recipe/verifier themselves retain literal LF.
            data = raw.replace(b'\r\n', b'\n') if name.startswith('engines/tests/') else raw
            require(b'\r' not in data and sha(data) == expected, 'canonical input changed: '+name)
            target = inputs/'canonical'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            report['canonical_inputs'][name] = {'raw_sha256': sha(raw), 'executed_sha256': sha(data),
                                               'CRLF_to_LF': raw != data}
            if not name.endswith('recipe.json'):
                target = recipe/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        producer = args.cost.parent/'recipe/build.py'
        producer_data = producer.read_bytes()
        require(sha(producer_data) == cost['inputs']['build.py']['sha256'], 'frozen cost producer changed')
        (inputs/'cost-producer.py').write_bytes(producer_data)
        spec = importlib.util.spec_from_file_location('literal_lzma_transport_producer', inputs/'cost-producer.py')
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        candidate = (args.cost.parent/'attempt-1/x').read_bytes()
        require(sha(candidate) == CANDIDATE_SHA256 and len(candidate) == 5163, 'candidate under test changed')
        prefix_size = 77
        require(candidate[:prefix_size].endswith(b'\n') and candidate[:prefix_size].count(b'|lzma -dc') == 1,
                'candidate launcher control-flow shape differs')
        bootstrap = transport.strict_decode(candidate[prefix_size:], transport.lzma.FORMAT_ALONE)
        source = transport.bootstrap_source(bootstrap)
        native = (args.cost.parent/'recipe/control/native/x').read_bytes()
        require(sha(bootstrap) == BOOTSTRAP_SHA256 and sha(source) == SOURCE_SHA256 and sha(native) == NATIVE_SHA256,
                'decoded bootstrap/source/native equality differs')
        original_bootstrap = (args.cost.parent/'recipe/control/bootstrap.py').read_bytes()
        require(bootstrap == original_bootstrap, 'original runtime/compiler/signal/cleanup bootstrap changed')
        report['decoded_reuse'] = {'bootstrap_sha256': sha(bootstrap), 'source_sha256': sha(source),
                                  'native_sha256': sha(native), 'exact_original_bootstrap_bytes': True,
                                  'scope': 'same compiler argv, C and runtime bytes; only the entry transport changes'}
        # This is a new explicit candidate recipe. The canonical A5207 recipe
        # is retained in inputs/canonical and is never overwritten or rebound.
        candidate_recipe = {'artifact_kind': 'one qualified-first-cost LZMA-alone A5163 transport',
                            'expected': {'whole_sha256': CANDIDATE_SHA256, 'native_sha256': NATIVE_SHA256,
                                         'source_sha256': SOURCE_SHA256},
                            'qualified_receipt': {'scope': 'exact decoded A5207 bootstrap/C/compiler/native reuse; new transport only',
                                                  'control_whole_sha256': CONTROL_SHA256,
                                                  'bootstrap_sha256': BOOTSTRAP_SHA256,
                                                  'first_cost_sha256': FIRST_COST_SHA256,
                                                  'repeat_cost_sha256': FINAL_COST_SHA256}}
        verifier_recipe = recipe/'engines/compact/tiny-entry-a/recipe.json'
        verifier_recipe.write_text(json.dumps(candidate_recipe, indent=2)+'\n')
        report['explicit_candidate_recipe_sha256'] = sha(verifier_recipe.read_bytes())
        build = out/'candidate-build'
        (build/'native').mkdir(parents=True)
        for name, data in (('x', candidate), ('main.c', source), ('bootstrap.py', bootstrap), ('native/x', native)):
            (build/name).write_bytes(data)
        (build/'x').chmod(0o755)
        (build/'build.json').write_text(json.dumps({'complete': True, 'scope': 'literal candidate adapter, no new engine generation',
                                                   'expected': candidate_recipe['expected'], 'decoded_reuse': report['decoded_reuse']}, indent=2)+'\n')
        command = [sys.executable, '-B', str(recipe/'engines/compact/tiny-entry-a/verify.py'),
                   '--build', str(build), '--out', str(out/'actual-two-sessions')]
        result = subprocess.run(command, capture_output=True, timeout=45)
        (out/'canonical.stdout').write_bytes(result.stdout)
        (out/'canonical.stderr').write_bytes(result.stderr)
        report['canonical_invocation'] = {'command': command, 'returncode': result.returncode}
        require(result.returncode == 0, 'unchanged canonical runtime gates failed; exact output retained')
        runtime_path = out/'actual-two-sessions/runtime.json'
        runtime_raw = runtime_path.read_bytes()
        runtime = json.loads(runtime_raw)
        require(runtime['complete'] and runtime['whole_sha256'] == CANDIDATE_SHA256 and runtime['native_sha256'] == NATIVE_SHA256
                and len(runtime['fresh_sessions']) == 2, 'actual canonical receipt binding differs')
        require({row['termination'] for row in runtime['fresh_sessions']} == {'quit', 'EOF'}, 'two authorized termination cases differ')
        report['canonical_runtime'] = {'path': str(runtime_path), 'sha256': sha(runtime_raw), 'sessions': 2}
        report['runtime_qualified'] = True
        report['complete'] = True
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        save()
    print(json.dumps({'complete': True, 'sessions': 2, 'whole_sha256': CANDIDATE_SHA256, 'out': str(out)}))


if __name__ == '__main__':
    main()
