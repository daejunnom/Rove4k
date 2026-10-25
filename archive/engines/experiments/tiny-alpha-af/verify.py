#!/usr/bin/env python3
"""F-only runtime adapter for the literal v2 alpha cost receipt.

The frozen selected verifier is copied unchanged into a separate execution
mirror. Only five recipe representation pins are derived. This adapter does
not build, preprocess, recompress, or execute A, and creates no new core proof.
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
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PIN_SHA256 = 'f90c37aa58ebab481898cbb8da02edb4ca76d1274d41e7b5e28ac16921d7e6f6'
OVERRIDES = {'source_bytes', 'source_sha256', 'whole_bytes', 'whole_sha256', 'bootstrap_sha256'}


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
    cost = Path(pins['cost_directory'])
    out.mkdir(parents=True)
    report = {
        'complete': False,
        'scope': pins['scope'],
        'runtime_pins_sha256': PIN_SHA256,
        'adapter_sha256': sha(Path(__file__).read_bytes()),
        'cost_receipt_sha256': pins['cost_receipt']['sha256'],
        'A': pins['A_preserved'],
        'F_wrapper_sessions_planned': 2,
        'other_engine_launches': 0,
        'new_core_qualification': False,
        'cancellation_causality': 'unproven',
        'owned_subprocess': None,
    }
    def save():
        (out / 'runtime.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    try:
        admitted = {}
        observed_raw = {}
        def bindings():
            receipt, receipt_raw = admit(cost / pins['cost_receipt']['file'],
                                         {k: pins['cost_receipt'][k] for k in ('bytes', 'sha256')})
            values = {'cost_receipt': receipt_raw}
            for relative, pin in pins['inputs'].items():
                data, raw = admit(HERE / relative, pin, True)
                values['input:' + relative] = raw
                admitted[relative] = data
            for relative, pin in pins['artifacts'].items():
                data, raw = admit(cost / relative, pin)
                values['artifact:' + relative] = raw
            cb = cost / pins['control_build_receipt']['file']
            cb_data = cb.read_bytes()
            require(sha(cb_data) == pins['control_build_receipt']['sha256'], 'control receipt changed')
            values['control_build_receipt'] = identity(cb_data)
            require((HERE / 'runtime-pins.json').read_bytes() == pins_bytes, 'runtime pins changed during run')
            values['adapter'] = identity(Path(__file__).read_bytes())
            return receipt, values
        receipt_bytes, observed_raw = bindings()
        r = json.loads(receipt_bytes)
        require(r['complete'] and r['engine_runs'] == 0, 'cost receipt is not pre-runtime complete')
        require(r['inputs'] == pins['inputs'], 'cost closure differs')
        counts = {'control': sum(k.startswith('control/') for k in r['inputs']),
                  'reference': sum(k.startswith('reference/') for k in r['inputs'])}
        counts['producer'] = len(r['inputs']) - sum(counts.values())
        require(counts == pins['input_counts'] and len(r['inputs']) == 36, 'closure counts differ')
        a, f = r['families']['A'], r['families']['F']
        require({k: a[k] for k in ('status', 'error', 'engine_runs')} == pins['A_preserved'], 'A failure changed')
        require(a['status'] == 'stopped' and 'strict full-PP inverse mismatch at 81960' in a['error'], 'A must remain failed')
        require(f['status'] == pins['F_status'] and f['engine_runs'] == 0, 'F initial status differs')
        require(f['control'] == pins['F_control'], 'control cost metadata differs')
        c = f['candidate']
        require({k: c[k] for k in pins['F_candidate']} == pins['F_candidate'], 'candidate cost differs')
        require(c['full_native_exact'] and c['independent_attempts'] == 2 and len(c['attempts']) == 2, 'native repetition gate missing')
        require(c['native_sha256'] == f['control']['native_sha256'], 'F native identity changed')
        for i, attempt in enumerate(c['attempts'], 1):
            require(attempt['attempt'] == i, 'attempt numbering differs')
            for k in ('source_bytes', 'source_sha256', 'native_bytes', 'native_sha256',
                      'whole_bytes', 'whole_sha256', 'bootstrap_sha256'):
                require(attempt[k] == c[k], 'attempt pin differs: ' + k)
        gate = f['header_gate']
        require(gate['pass'] and gate['full_preprocessed_bytes_inverse_equal']
                and gate['final_macro_definitions_equal'] and not gate['fresh_alias_capture'], 'F header gate missing')
        report['prelaunch_binding'] = {'input_counts': counts, 'all_inputs': pins['inputs'],
                                       'artifacts': pins['artifacts'], 'raw_bindings': observed_raw,
                                       'F_header_gate_reused': True, 'F_full_native_exact_reused': True}
        original = out / 'original-inputs'
        for relative, data in admitted.items():
            dest = original / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        (out / 'cost-v2.json').write_bytes(receipt_bytes)
        mirror = out / 'execution-mirror'
        for relative, data in admitted.items():
            if relative.startswith('control/'):
                dest = mirror / relative.removeprefix('control/')
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
        original_recipe = json.loads(admitted[pins['original_recipe']])
        derived = copy.deepcopy(original_recipe)
        require(set(pins['runtime_expected_overrides']) == OVERRIDES, 'expected override set differs')
        changes = {}
        for key, value in pins['runtime_expected_overrides'].items():
            changes[key] = {'before': original_recipe['expected'][key], 'after': value}
            derived['expected'][key] = value
        restored = copy.deepcopy(derived)
        for key in OVERRIDES:
            restored['expected'][key] = original_recipe['expected'][key]
        require(restored == original_recipe, 'derived recipe changed more than five expected fields')
        require(all(x['before'] != x['after'] for x in changes.values()), 'five changes were not exact')
        recipe_path = mirror / 'engines/compact/tiny-entry-f/recipe.json'
        derived_bytes = (json.dumps(derived, indent=2) + '\n').encode()
        recipe_path.write_bytes(derived_bytes)
        verifier = mirror / 'engines/compact/tiny-entry-f/verify.py'
        require(verifier.read_bytes() == admitted[pins['original_verifier']], 'verifier changed in mirror')
        selected = out / 'selected-F'
        selected.mkdir()
        for name in ('main.c', 'native/x', 'x', 'bootstrap.py'):
            dest = selected / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cost / 'candidate-F' / name, dest)
        os.chmod(selected / 'x', 0o755)
        os.chmod(selected / 'native/x', 0o755)
        # The unmodified verifier reads only complete. Preserve the real producer
        # receipt verbatim rather than manufacture a new build-success manifest.
        (selected / 'build.json').write_bytes(receipt_bytes)
        report['runtime_only_recipe'] = {'changes': changes, 'only_five_expected_fields_changed': True,
                                         'sha256': sha(derived_bytes), 'historical_metadata_unchanged': True}
        report['verifier_sha256'] = sha(verifier.read_bytes())
        report['build_receipt_adapter'] = 'literal cost-v2 receipt copied byte-for-byte; no new build receipt'
        save()
        before_launch = {
            str(p.relative_to(out)): identity(p.read_bytes())
            for base in (original, mirror, selected) for p in base.rglob('*') if p.is_file()
        }
        command = [sys.executable, '-I', '-B', str(verifier), '--build', str(selected), '--out', str(out / 'fresh')]
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        status, verifier_pid = run_owned_verifier(command, out, report, save)
        require(status == 0, 'original verifier failed; stdout/stderr retained')
        fresh = json.loads((out / 'fresh/runtime.json').read_text())
        require(fresh['complete'], 'selected runtime receipt incomplete')
        require(fresh['whole_sha256'] == c['whole_sha256'] and fresh['native_sha256'] == c['native_sha256'], 'runtime artifact differs')
        require(fresh['historical_receipt_reuse'] == original_recipe['qualified_receipt'], 'historical metadata changed')
        require(fresh['helpers'] == {k.removeprefix('control/'): v['sha256'] for k, v in pins['inputs'].items()
                                    if k in ('control/engines/tests/verify.py', 'control/engines/tests/chess_oracle.py')}, 'runtime helpers differ')
        sessions = fresh['fresh_sessions']
        require(len(sessions) == 2 and [x['termination'] for x in sessions] == ['quit', 'EOF'], 'exact two sessions differ')
        for row in sessions:
            require(row['returncode'] == 0 and row['stderr'] == [] and row['exactly_one_closing_bestmove']
                    and row['process_absent'] and row['readers_finished'], 'wrapper settlement failed')
            require([x['clock'] for x in row['completed']] == ['white zero', 'black zero', 'bare finite default'], 'clock coverage differs')
            image = row['image']
            require(image['image_sha256'] == c['native_sha256'] and image['private_path_absent']
                    and len(image['startup_tids']) == 3 and not any(image['children_by_tid'].values()), 'restored image or startup differs')
            require(row['activity']['active_before_signal'] and row['activity']['cancellation_causality'] == 'unproven', 'cancellation boundary changed')
        receipt_after, raw_after = bindings()
        require(receipt_after == receipt_bytes and raw_after == observed_raw, 'original inputs or artifacts changed during runtime')
        for relative, pin in before_launch.items():
            require(identity((out / relative).read_bytes()) == pin, 'execution mirror changed: ' + relative)
        require(not (Path('/proc') / str(verifier_pid)).exists(), 'owned verifier remains after wait')
        report.update(complete=True, F_wrapper_sessions_observed=2, F_go_epochs=8,
                      original_verifier_runtime_sha256=sha((out / 'fresh/runtime.json').read_bytes()),
                      bindings_rechecked_after=True, mirror_rechecked_after=True,
                      fresh_runtime='fresh/runtime.json', owned_descendant_agents='read-only audit; no execution handles',
                      historical_receipts='unchanged metadata; no new core qualification',
                      process_scope='original verifier main/readers and observed compiler children; cancellation causality unproven')
        save()
        print(json.dumps({'complete': True, 'out': str(out), 'F_sessions': 2, 'A_engine_runs': 0,
                          'whole_bytes': c['whole_bytes'], 'whole_sha256': c['whole_sha256']}))
    except Exception as error:
        report['error'] = repr(error)
        try:
            save()
        except BaseException:
            pass
        raise


if __name__ == '__main__':
    main()
