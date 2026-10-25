#!/usr/bin/env python3
"""Admit literal5899 bytes, invoke the unchanged selected B verifier once."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PIN = 'c1e56ebb38454a7a17fd67c9049a6f370e8d5ae2364ad953d79c6653ca998144'
CHANGE_KEYS = {'readable_sha256', 'source_bytes', 'source_sha256', 'native_bytes',
               'native_sha256', 'whole_bytes', 'whole_sha256', 'bootstrap_sha256'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(document):
    return (json.dumps(document, indent=2) + '\n').encode()


def exact(root, relative, pin):
    root = root.resolve()
    relative = Path(relative)
    require(not relative.is_absolute() and '..' not in relative.parts, 'unsafe input path')
    path = root / relative
    require(root in path.resolve().parents, 'input path escaped')
    require(not any(p.is_symlink() for p in (path, *path.parents) if p != root and root in p.parents),
            'symlink in pinned input path')
    raw = path.read_bytes()
    require(sha(raw) == pin['sha256'] and len(raw) == pin['bytes'], 'literal raw input changed: ' + str(path))
    return raw


def admit(build, pins):
    raw = exact(build, 'results.json', pins['cost_receipt'])
    cost = json.loads(raw)
    require(cost['complete'] is True and cost['gain'] is True and cost['engine_runs'] == 0,
            'first cost did not complete as an unexecuted gain')
    require(cost['candidate_runtime_qualified'] is False and cost['whole_runtime_stack_qualified'] is False,
            'cost receipt qualification scope changed')
    require(cost['producer_inputs'] == pins['producer_inputs'] and cost['control_inputs'] == pins['control_inputs'],
            'cost closure differs')
    require(len(pins['control_inputs']) == 23 and set(pins['producer_inputs']) ==
            {'build.py', 'recipe.json', 'target_policy.py', 'target-policy.json'}, 'source closure shape differs')
    for name, pin in pins['producer_inputs'].items():
        require(exact(HERE, name, pin) == exact(build / 'recipe', name, pin), 'own/frozen producer differs')
    controls = {}
    for name, pin in pins['control_inputs'].items():
        controls[name] = exact(HERE / 'control', name, pin)
        require(controls[name] == exact(build / 'recipe/control', name, pin), 'own/frozen control differs')
    candidate = next(row for row in cost['forms'] if row['id'] == 'target')
    require(candidate['attempts'] == pins['candidate_attempts'] and len(candidate['attempts']) == 2,
            'two literal candidate attempts differ')
    require(candidate['header_gate']['pass'] is True and
            candidate['header_gate']['strict_full_preprocessed_alpha_inverse_bytes_equal'] is True,
            'strict header gate missing')
    artifacts = {name: exact(build / 'target', name, pin) for name, pin in pins['artifacts'].items()}
    for attempt in (1, 2):
        for name, actual in (('x', 'native'), ('wrapper', 'wrapper'), ('bootstrap.py', 'bootstrap.py')):
            require(exact(build / ('target/attempt-' + str(attempt)), name, pins['artifacts'][actual]) == artifacts[actual],
                    'physical attempt differs from selected bytes')
    return raw, controls, artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build, out = args.build.resolve(), args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and
            not any((p / '.git').exists() for p in (out, *out.parents)), 'new absolute non-Git output required')
    pins_raw = (HERE / 'runtime-pins.json').read_bytes()
    require(sha(pins_raw) == PIN, 'literal runtime pins changed')
    pins = json.loads(pins_raw)
    require(pins['format'] == 1 and set(pins['runtime_expected']) == CHANGE_KEYS, 'runtime pin schema differs')
    cost_raw, controls, artifacts = admit(build, pins)
    out.mkdir(parents=True)
    recipe_dir = out / 'recipe'
    recipe_dir.mkdir()
    (recipe_dir / 'verify.py').write_bytes(Path(__file__).read_bytes())
    (recipe_dir / 'runtime-pins.json').write_bytes(pins_raw)
    (recipe_dir / 'cost-results.json').write_bytes(cost_raw)
    report = {'complete': False, 'scope': 'two actual selected-wrapper sessions via unchanged original verifier',
              'cost_receipt_sha256': sha(cost_raw), 'runtime_pins_sha256': PIN,
              'verifier_sha256': sha(Path(__file__).read_bytes()),
              'fresh_sessions': 0, 'performance_claim': False, 'whole_runtime_stack_qualified': False,
              'target_native_historical_reuse': pins['target_native_historical_reuse']}
    def save():
        (out / 'results.json').write_bytes(encoded(report))
    save()
    try:
        execution = out / 'execution'
        for name, raw in controls.items():
            path = execution / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        entry = execution / 'engines/compact/tiny-entry-b'
        original_raw = (entry / 'recipe.json').read_bytes()
        original = json.loads(original_raw)
        derived = deepcopy(original)
        changes = {}
        for name, value in pins['runtime_expected'].items():
            changes[name] = {'before': original['expected'][name], 'after': value}
            require(changes[name]['before'] != value, 'declared runtime change is not a change')
            derived['expected'][name] = value
        require({key for key in original['expected'] if original['expected'][key] != derived['expected'][key]} == CHANGE_KEYS,
                'unexpected expected-field changes')
        derived['qualified_receipt'] = pins['target_native_historical_reuse']
        derived['provenance'] = {'scope': 'derived selected-runtime-only configuration; never a producer recipe',
                                 'original_recipe_sha256': sha(original_raw),
                                 'original_provenance': original['provenance'],
                                 'original_qualified_receipt_archive': original['qualified_receipt'],
                                 'DEV': 'unchanged archive; no new DEV generation/runtime'}
        derived_raw = encoded(derived)
        (entry / 'recipe.json').write_bytes(derived_raw)
        (recipe_dir / 'original-entry-recipe.json').write_bytes(original_raw)
        (recipe_dir / 'derived-runtime-recipe.json').write_bytes(derived_raw)
        report['derived_runtime_only_recipe'] = {'original_sha256': sha(original_raw), 'derived_sha256': sha(derived_raw),
                                                'exact_expected_changes': changes,
                                                'metadata_changes': ['qualified_receipt', 'provenance']}
        selected = out / 'selected'
        (selected / 'native').mkdir(parents=True)
        for target, source in (('main.c', 'main.c'), ('native/x', 'native'), ('x', 'wrapper'), ('bootstrap.py', 'bootstrap.py')):
            (selected / target).write_bytes(artifacts[source])
        (selected / 'x').chmod(0o755)
        (selected / 'native/x').chmod(0o755)
        (selected / 'build.json').write_bytes(encoded({'complete': True, 'runtime_representation_adapter': True,
                'scope': 'selected bytes copied from exact cost; no regeneration or native producer compile',
                'cost_receipt_sha256': sha(cost_raw)}))
        mirror_pins = {name: {'bytes': len((execution / name).read_bytes()),
                              'sha256': sha((execution / name).read_bytes())} for name in controls}
        command = [sys.executable, '-I', '-B', str(entry / 'verify.py'), '--build', str(selected),
                   '--out', str(out / 'selected-runtime')]
        report['command'] = command
        save()
        process = subprocess.run(command, capture_output=True, timeout=45)
        (out / 'verifier.stdout').write_bytes(process.stdout)
        (out / 'verifier.stderr').write_bytes(process.stderr)
        report['returncode'] = process.returncode
        require(process.returncode == 0, 'unchanged selected verifier failed; original diagnostics retained')
        runtime_raw = (out / 'selected-runtime/runtime.json').read_bytes()
        runtime = json.loads(runtime_raw)
        require(runtime['complete'] is True and len(runtime['fresh_sessions']) == 2, 'selected sessions incomplete')
        require({row['termination'] for row in runtime['fresh_sessions']} == {'quit', 'EOF'}, 'termination set differs')
        for row in runtime['fresh_sessions']:
            require(row['image']['image_sha256'] == pins['artifacts']['native']['sha256'] and
                    row['returncode'] == 0 and row['process_absent'] is True and row['readers_finished'] is True,
                    'selected image/physical completion differs')
            require(row['activity']['cancellation_causality'] == 'unproven', 'causality claim changed')
        admit(build, pins)
        require(Path(__file__).read_bytes() == (recipe_dir / 'verify.py').read_bytes() and
                (HERE / 'runtime-pins.json').read_bytes() == pins_raw, 'runtime source changed')
        for name, pin in mirror_pins.items():
            exact(execution, name, pin)
        for target, source in (('main.c', 'main.c'), ('native/x', 'native'), ('x', 'wrapper'), ('bootstrap.py', 'bootstrap.py')):
            exact(selected, target, pins['artifacts'][source])
        report.update(complete=True, fresh_sessions=2, selected_runtime_sha256=sha(runtime_raw),
                      sessions=runtime['fresh_sessions'], final_owned_frozen_mirror_rechecks=True)
        save()
        print(json.dumps({'complete': True, 'fresh_sessions': 2, 'whole_bytes': 5899,
                          'report': str(out / 'results.json')}))
    except BaseException as error:
        report['failure'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
