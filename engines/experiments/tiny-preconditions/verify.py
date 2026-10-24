#!/usr/bin/env python3
"""Pin the measured shipping files and reuse the exact finite-UCI physical gate.

Both experiment forms have the already-qualified minimal shipping policy.
The existing strong-stop validator is unchanged.  This script delegates only
to the frozen minimal-policy gate, whose raw process helper and independent
chess oracle are frozen with it.  Transition/search specialization proof is
separate in transitions.py; these observations establish actual process/image,
startup resources, bounded finite UCI and physical reuse/shutdown fences.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINS = {
    'engines/experiments/tiny-uci-min/verify.py': '1e95b0a4e40c0584ca772b7545b73fcf758a0a82828f8dc9ba724ab812be0ddb',
    'engines/experiments/tiny-protocol/edges.py': '253cf1c7d9d1a050de8e1275f46beefcf26bb065dbb308a2421386019c02a060',
    'engines/tests/chess_oracle.py': 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--budget', type=int, default=180)
    args = parser.parse_args()
    require(sys.platform == 'linux' and Path('/proc/self/task').is_dir(), 'requires Linux /proc')
    require(0 < args.budget <= 300, 'budget must be within 0..300 seconds')
    require(args.out.is_absolute() and not args.out.exists() and not any((p / '.git').exists() for p in (args.out, *args.out.parents)), 'new absolute output outside Git required')
    args.out.mkdir(parents=True)
    recipe = args.out / 'recipe'
    recipe.mkdir()
    started = time.monotonic()
    report = {'complete': False, 'runs': [], 'scope': 'pinned actual native and complete launchers; finite-UCI and physical image/startup/reuse/shutdown fences',
              'budget_seconds': args.budget, 'validator_sha256': sha(Path(__file__).read_bytes())}

    def save():
        (args.out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')

    def timeout(signum, frame):
        raise TimeoutError('aggregate physical verification deadline')

    previous_handler = signal.signal(signal.SIGALRM, timeout)
    # Every process launched by either frozen gate shares this module object.
    # Register it while the aggregate alarm is blocked, including constructor
    # failures after Popen but before RawEngine can return its handle.  The
    # outer finally also owns compilers/harnesses interrupted by an ordinary
    # TimeoutError, which the older bounded helper does not catch itself.
    original_popen = subprocess.Popen
    owned = []

    class OwnedPopen(original_popen):
        def __init__(self, *positional, **keywords):
            require(keywords.get('start_new_session') is True, 'gate process must own a new session')
            require('preexec_fn' not in keywords, 'unexpected gate child setup')
            previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
            # Do not change the tested process's inherited signal mask merely
            # to make parent-side handle registration atomic with the alarm.
            keywords['preexec_fn'] = lambda: signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            try:
                super().__init__(*positional, **keywords)
                owned.append(self)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)

    subprocess.Popen = OwnedPopen
    signal.setitimer(signal.ITIMER_REAL, args.budget)
    save()
    try:
        build_bytes = args.build.read_bytes()
        build = json.loads(build_bytes)
        require(build.get('complete') is True and build.get('dev_exactly_unchanged') is True, 'build incomplete or DEV changed')
        records = build['engines']
        require([row['id'] for row in records] == ['control', 'specialized'], 'expected one exact control and specialization')
        require(records[0]['whole_bytes'] == 5223, 'unexpected control size')
        report['build_sha256'] = sha(build_bytes)
        (recipe / 'build.json').write_bytes(build_bytes)
        report['inputs'] = {}
        for relative, expected in PINS.items():
            data = (ROOT / relative).read_bytes()
            require(sha(data) == expected, 'gate source changed: ' + relative)
            target = recipe / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            report['inputs'][relative] = expected
        (recipe / 'preconditions-verify.py').write_bytes(Path(__file__).read_bytes())
        policy = module('preconditions_frozen_minimal_gate', recipe / 'engines/experiments/tiny-uci-min/verify.py')
        raw = module('preconditions_frozen_raw', recipe / 'engines/experiments/tiny-protocol/edges.py')
        oracle = sys.modules['chess_oracle']
        report['oracle_self_check'] = oracle.self_check()
        for row in records:
            for path, digest in ((row['readable'], row['readable_sha256']), (row['source'], row['source_sha256']),
                                 (row['native'], row['native_sha256']), (row['command'][0], row['whole_sha256']),
                                 (row['dev'], row['dev_native_sha256'])):
                require(sha(Path(path).read_bytes()) == digest, 'artifact identity mismatch: ' + path)
        require(records[0]['dev_source_sha256'] == records[1]['dev_source_sha256'] and
                records[0]['dev_native_sha256'] == records[1]['dev_native_sha256'], 'DEV identity differs')
        # The gate's id selects its declared protocol policy, not an engine
        # algorithm.  Give both the minimal id in distinct form directories.
        # Each receipt retains the original experiment identity explicitly.
        candidate_gate = dict(records[1], id='minimal')
        instrumented = args.out / 'instrumented'
        instrumented.mkdir()
        report['instrumented_candidate'] = policy.units([candidate_gate], instrumented)
        for row in records:
            form_out = args.out / row['id']
            form_out.mkdir()
            gate_row = dict(row, id='minimal')
            for transport in ('native', 'wrapper'):
                for eof in (False, True):
                    receipt = policy.run_shipping(gate_row, transport, form_out, raw, oracle, eof_only=eof)
                    receipt['experiment_form'] = row['id']
                    receipt['protocol_policy'] = 'qualified minimal finite UCI'
                    report['runs'].append(receipt)
                    save()
        report['complete'] = True
    except Exception as error:
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        subprocess.Popen = original_popen
        cleanup_errors = []
        for process in owned:
            try:
                # Let a source launcher run its own separately grouped
                # compiler cleanup before escalating the parent-owned group.
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=.5)
                except subprocess.TimeoutExpired:
                    pass
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=3)
            except Exception as error:
                cleanup_errors.append({'pid': process.pid, 'error': repr(error)})
        report['owned_processes'] = len(owned)
        report['owned_groups_settled'] = not cleanup_errors
        if cleanup_errors:
            report['complete'] = False
            report['cleanup_errors'] = cleanup_errors
        signal.signal(signal.SIGALRM, previous_handler)
        report['elapsed_seconds'] = time.monotonic() - started
        save()
    require(report['complete'] is True, 'verification cleanup failed')
    print(json.dumps({'complete': True, 'shipping_runs': len(report['runs']), 'modeled_candidate_cases': len(report['instrumented_candidate'][0]['cases']), 'out': str(args.out)}))


if __name__ == '__main__':
    main()
