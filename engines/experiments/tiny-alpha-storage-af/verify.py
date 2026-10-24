#!/usr/bin/env python3
"""Bind the two selected storage18 wrappers to their own frozen cost receipt.

Each family's original selected verifier is copied unchanged into an execution
mirror and invoked once. Only five recipe representation pins are derived.
No producer, codec, extra engine, or old runtime/source lookup is performed.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PIN_SHA256 = '0243096344ddaad506ca72c4d7e5590cd4e70bb41d9c0207112daef5c2f08192'
OVERRIDES = {'source_bytes', 'source_sha256', 'whole_bytes', 'whole_sha256', 'bootstrap_sha256'}
FAMILIES = ('A', 'F')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(data):
    return {'bytes': len(data), 'sha256': sha(data)}


def admit(path, pin, normalize=False):
    raw = path.read_bytes()
    data = raw.replace(b'\r\n', b'\n') if normalize else raw
    require(not normalize or b'\r' not in data, 'unexpected CR: ' + str(path))
    require(identity(data) == pin, 'identity mismatch: ' + str(path))
    return data, identity(raw)


def validate_fresh(fresh, candidate, original_recipe, pins):
    require(fresh['complete'], 'selected runtime receipt incomplete')
    require(fresh['whole_sha256'] == candidate['whole_sha256']
            and fresh['native_sha256'] == candidate['native_sha256'], 'runtime artifact differs')
    require(fresh['historical_receipt_reuse'] == original_recipe['qualified_receipt'], 'historical metadata changed')
    helpers = {k.removeprefix('control/'): v['sha256'] for k, v in pins['inputs'].items()
               if k in ('control/engines/tests/verify.py', 'control/engines/tests/chess_oracle.py')}
    require(fresh['helpers'] == helpers, 'runtime helpers differ')
    sessions = fresh['fresh_sessions']
    require(len(sessions) == 2 and [x['termination'] for x in sessions] == ['quit', 'EOF'], 'exact two sessions differ')
    for row in sessions:
        require(row['returncode'] == 0 and row['stderr'] == [] and row['exactly_one_closing_bestmove']
                and row['process_absent'] and row['readers_finished'], 'wrapper settlement failed')
        require([x['clock'] for x in row['completed']] == ['white zero', 'black zero', 'bare finite default'], 'clock coverage differs')
        image = row['image']
        require(image['image_sha256'] == candidate['native_sha256'] and image['private_path_absent']
                and len(image['startup_tids']) == 3 and not any(image['children_by_tid'].values()), 'restored image or startup differs')
        require(row['activity']['active_before_signal']
                and row['activity']['cancellation_causality'] == 'unproven', 'cancellation boundary changed')


def run_owned_verifier(command, out, report, save, timeout=35, grace=5):
    """Own the verifier from Popen through every save, wait and exception."""
    with (out / 'verifier.stdout').open('wb') as stdout, (out / 'verifier.stderr').open('wb') as stderr:
        proc = subprocess.Popen(command, cwd=out, stdout=stdout, stderr=stderr)
        try:
            report['owned_subprocess'] = {'pid': proc.pid, 'command': command, 'terminal': False}
            save()
            status = proc.wait(timeout=timeout)
            report['owned_subprocess'].update(returncode=proc.returncode, terminal=True)
            save()
            return status, proc.pid
        except BaseException as original:
            row = report.get('owned_subprocess')
            if not isinstance(row, dict):
                row = {'pid': proc.pid, 'command': command}
                report['owned_subprocess'] = row
            report['settled'] = False
            report['wrapper_settlement'] = 'unproven after owned verifier failure'
            row['exception'] = repr(original)
            def preserve():
                # A failed receipt write must not mask the initiating exception
                # or prevent ownership cleanup of the already-created process.
                try:
                    save()
                except BaseException:
                    pass
            preserve()
            if proc.poll() is None:
                try:
                    proc.send_signal(signal.SIGINT)
                    row['interrupt_sent'] = True
                except BaseException as error:
                    row['interrupt_error'] = repr(error)
                try:
                    proc.wait(timeout=grace)
                except BaseException as error:
                    row['grace_wait_error'] = repr(error)
                    row['forced_kill'] = True
                    report['unsettled_failure'] = True
                    preserve()  # Record uncertainty BEFORE forced kill/reap.
                    try:
                        proc.kill()
                    except BaseException as kill_error:
                        row['kill_error'] = repr(kill_error)
                    try:
                        proc.wait(timeout=grace)
                    except BaseException as reap_error:
                        row['reap_error'] = repr(reap_error)
            row.update(returncode=proc.poll(), terminal=proc.returncode is not None)
            if not row['terminal']:
                report['unsettled_failure'] = True
            preserve()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists(), 'new absolute output required')
    require(not any((p / '.git').exists() for p in (out, *out.parents)), 'output must be outside Git')
    pins_bytes = (HERE / 'runtime-pins.json').read_bytes()
    require(sha(pins_bytes) == PIN_SHA256, 'literal runtime pins changed')
    pins = json.loads(pins_bytes)
    own_source = Path(__file__).read_bytes()
    own_function = own_source[own_source.index(b'def run_owned_verifier('):own_source.index(b'\ndef main():')]
    require(identity(own_function) == {k: pins['ownership_function'][k] for k in ('bytes', 'sha256')}, 'reviewed ownership function changed')
    cost = Path(pins['cost_directory'])
    out.mkdir(parents=True)
    report = {'complete': False, 'scope': pins['scope'], 'runtime_pins_sha256': PIN_SHA256,
              'adapter_sha256': sha(own_source), 'cost_receipt_sha256': pins['cost_receipt']['sha256'],
              'ownership_function_sha256': pins['ownership_function']['sha256'],
              'original_verifier_invocations_planned': 2, 'wrapper_sessions_planned': 4, 'GO_epochs_planned': 16,
              'other_engine_launches': 0, 'new_core_qualification': False,
              'cancellation_causality': 'unproven', 'families': {}}
    def save():
        (out / 'runtime.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    try:
        admitted = {}
        def bindings():
            receipt, raw = admit(cost / pins['cost_receipt']['file'],
                                 {k: pins['cost_receipt'][k] for k in ('bytes', 'sha256')})
            values = {'cost_receipt': raw}
            for relative, pin in pins['inputs'].items():
                data, raw = admit(HERE / relative, pin, True)
                values['input:' + relative] = raw
                admitted[relative] = data
            for relative, pin in pins['artifacts'].items():
                _, raw = admit(cost / relative, pin)
                values['artifact:' + relative] = raw
            for family in FAMILIES:
                pin = pins['families'][family]['control_build_receipt']
                data = (cost / pin['file']).read_bytes()
                require(sha(data) == pin['sha256'], 'control receipt changed: ' + family)
                values['control_receipt:' + family] = identity(data)
            require((HERE / 'runtime-pins.json').read_bytes() == pins_bytes, 'runtime pins changed during run')
            values['adapter'] = identity(Path(__file__).read_bytes())
            return receipt, values
        receipt_bytes, observed_raw = bindings()
        r = json.loads(receipt_bytes)
        require(r['complete'] and r['engine_runs'] == 0, 'cost receipt is not pre-runtime complete')
        require(r['inputs'] == pins['inputs'] and set(r['families']) == set(FAMILIES), 'cost input/family closure differs')
        counts = {'control': sum(k.startswith('control/') for k in r['inputs']),
                  'reference': sum(k.startswith('reference/') for k in r['inputs'])}
        counts['producer'] = len(r['inputs']) - sum(counts.values())
        require(counts == pins['input_counts'] and len(r['inputs']) == 38, 'closure counts differ')
        for family in FAMILIES:
            actual = r['families'][family]
            fixed = pins['families'][family]
            require(actual['status'] == fixed['status'] and actual['engine_runs'] == 0, 'initial family status differs')
            require(actual['control'] == fixed['control'], 'control metadata differs: ' + family)
            c = actual['candidate']
            require({k: c[k] for k in fixed['candidate']} == fixed['candidate'], 'candidate cost differs: ' + family)
            require(c['full_native_exact'] and c['independent_attempts'] == 2 and len(c['attempts']) == 2, 'native repetition gate missing')
            require(c['native_sha256'] == actual['control']['native_sha256'], 'native identity changed')
            for i, attempt in enumerate(c['attempts'], 1):
                require(attempt['attempt'] == i, 'attempt numbering differs')
                for key in ('source_bytes', 'source_sha256', 'native_bytes', 'native_sha256',
                            'whole_bytes', 'whole_sha256', 'bootstrap_sha256'):
                    require(attempt[key] == c[key], 'attempt pin differs: ' + key)
            gate = actual['header_gate']
            require(gate['pass'] and gate['full_preprocessed_bytes_inverse_equal']
                    and gate['final_macro_definitions_equal'] and not gate['fresh_alias_capture'], 'header gate missing')
        report['prelaunch_binding'] = {'input_counts': counts, 'all_inputs': pins['inputs'],
                                       'artifacts': pins['artifacts'], 'raw_bindings': observed_raw,
                                       'both_header_and_full_native_gates_reused': True}
        original = out / 'original-inputs'
        mirror = out / 'execution-mirror'
        for relative, data in admitted.items():
            dest = original / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            if relative.startswith('control/'):
                dest = mirror / relative.removeprefix('control/')
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
        (out / 'cost.json').write_bytes(receipt_bytes)
        originals = {}
        for family in FAMILIES:
            fixed = pins['families'][family]
            old = json.loads(admitted[fixed['original_recipe']])
            originals[family] = old
            derived = copy.deepcopy(old)
            require(set(fixed['runtime_expected_overrides']) == OVERRIDES, 'expected override set differs')
            changes = {}
            for key, value in fixed['runtime_expected_overrides'].items():
                changes[key] = {'before': old['expected'][key], 'after': value}
                derived['expected'][key] = value
            restored = copy.deepcopy(derived)
            for key in OVERRIDES:
                restored['expected'][key] = old['expected'][key]
            require(restored == old, 'derived recipe changed more than five expected fields')
            require(all(x['before'] != x['after'] for x in changes.values()), 'five changes were not exact')
            recipe_path = mirror / fixed['original_recipe'].removeprefix('control/')
            derived_bytes = (json.dumps(derived, indent=2) + '\n').encode()
            recipe_path.write_bytes(derived_bytes)
            verifier = mirror / fixed['original_verifier'].removeprefix('control/')
            require(verifier.read_bytes() == admitted[fixed['original_verifier']], 'verifier changed in mirror')
            selected = out / ('selected-' + family)
            selected.mkdir()
            for name in ('main.c', 'native/x', 'x', 'bootstrap.py'):
                dest = selected / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(cost / ('candidate-' + family) / name, dest)
            os.chmod(selected / 'x', 0o755)
            os.chmod(selected / 'native/x', 0o755)
            # The frozen verifier reads complete; retain the actual producer
            # receipt byte-for-byte instead of fabricating a new build receipt.
            (selected / 'build.json').write_bytes(receipt_bytes)
            report['families'][family] = {
                'complete': False, 'owned_subprocess': None,
                'runtime_only_recipe': {'changes': changes, 'only_five_expected_fields_changed': True,
                                        'sha256': sha(derived_bytes), 'historical_metadata_unchanged': True},
                'verifier_sha256': sha(verifier.read_bytes()),
                'build_receipt_adapter': 'literal own cost receipt copied unchanged; no new build receipt'}
        save()
        before_launch = {str(p.relative_to(out)): identity(p.read_bytes())
                         for base in (original, mirror, out / 'selected-A', out / 'selected-F')
                         for p in base.rglob('*') if p.is_file()}
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        for family in FAMILIES:
            row = report['families'][family]
            fixed = pins['families'][family]
            run_dir = out / family
            run_dir.mkdir()
            verifier = mirror / fixed['original_verifier'].removeprefix('control/')
            command = [sys.executable, '-I', '-B', str(verifier), '--build', str(out / ('selected-' + family)),
                       '--out', str(run_dir / 'fresh')]
            status, verifier_pid = run_owned_verifier(command, run_dir, row, save)
            require(status == 0, 'original verifier failed; stdout/stderr retained: ' + family)
            fresh_bytes = (run_dir / 'fresh/runtime.json').read_bytes()
            fresh = json.loads(fresh_bytes)
            validate_fresh(fresh, fixed['candidate'], originals[family], pins)
            require(not (Path('/proc') / str(verifier_pid)).exists(), 'owned verifier remains after wait')
            row.update(complete=True, wrapper_sessions=2, GO_epochs=8,
                       fresh_runtime=family + '/fresh/runtime.json', fresh_runtime_sha256=sha(fresh_bytes),
                       whole_sha256=fixed['candidate']['whole_sha256'], native_sha256=fixed['candidate']['native_sha256'],
                       cancellation_causality='unproven')
            save()
        receipt_after, raw_after = bindings()
        require(receipt_after == receipt_bytes and raw_after == observed_raw, 'original inputs or artifacts changed during runtime')
        for relative, pin in before_launch.items():
            require(identity((out / relative).read_bytes()) == pin, 'execution mirror changed: ' + relative)
        report.update(complete=True, original_verifier_invocations=2, wrapper_sessions_observed=4, GO_epochs=16,
                      bindings_rechecked_after=True, mirror_rechecked_after=True,
                      historical_receipts='unchanged metadata; no new core qualification',
                      process_scope='original verifier mains/readers and observed compiler children; cancellation causality unproven')
        save()
        print(json.dumps({'complete': True, 'out': str(out), 'wrapper_sessions': 4, 'GO_epochs': 16,
                          'whole_bytes': {family: pins['families'][family]['candidate']['whole_bytes'] for family in FAMILIES}}))
    except Exception as error:
        report['error'] = repr(error)
        try:
            save()
        except BaseException:
            pass
        raise


if __name__ == '__main__':
    main()
