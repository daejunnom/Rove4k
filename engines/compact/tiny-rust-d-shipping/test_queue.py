#!/usr/bin/env python3
"""Exercise Queue's two exit boundaries with real Owned children, not engines."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def require(value, message):
    if not value:
        raise AssertionError(message)


def identity(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def exercise(out, label, line, code, shipping, helper, strict, row):
    directory = out/label
    directory.mkdir()
    fixture = directory/'fixture.py'
    inherited_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    fixture.write_text('#!'+sys.executable+'\nimport os,signal\nsignal.pthread_sigmask(signal.SIG_SETMASK,'+
                       repr(sorted(int(sig) for sig in inherited_mask))+')\nos.write(1,'+repr(line)+')\nos._exit('+str(code)+')\n')
    fixture.chmod(0o755)
    row.update(label=label, fixture=identity(fixture), expected_exit=code, passed=False)
    owned = None
    signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT, signal.SIGALRM, signal.SIGXCPU})
    try:
        owned = helper.Owned(fixture, directory/'owned', helper.Budget(10))
        queue = shipping.Queue(owned, strict)
        row['pid'] = owned.process.pid
        signal.pthread_sigmask(signal.SIG_SETMASK, inherited_mask)
        owned.stdout.until(lambda data: data == line, owned.budget, seconds=2)
        end = time.monotonic()+owned.budget.left(2)
        while not owned.exited():
            require(time.monotonic() < end, 'fixture did not naturally exit')
            time.sleep(.005)
        require(not queue.queued, 'response must enter through the actual Queue pump')
        row['reader_ready_before_until'] = True
        row['leader_exited_unreaped_before_until'] = True
        if code:
            try:
                queue.until('readyok', timeout=2)
            except AssertionError as error:
                row['expected_response_error'] = {'type': type(error).__name__, 'message': str(error)}
                require(str(error).startswith("missing 'readyok'; exit=17,"), 'missing-response diagnostic differs')
            else:
                raise AssertionError('missing response unexpectedly succeeded')
        else:
            row['response'] = queue.until('readyok', timeout=2)
            require(row['response'] == 'readyok', 'queued-on-exit response was lost')
        status = os.waitid(os.P_PID, owned.process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        require(status is not None and status.si_code == os.CLD_EXITED and status.si_status == code,
                'Queue consumed or changed the original leader exit status')
        require(not owned.reaped and owned.process.returncode is None, 'Queue reaped or mutated Popen state')
        row['exit_status_after_until'] = {'code': status.si_code, 'status': status.si_status}
        row['original_identity_retained_after_until'] = True
        if not code:
            row['settled'] = owned.finish()
    except BaseException as error:
        row['operation_error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        operation_error = sys.exc_info()[1]
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT, signal.SIGALRM, signal.SIGXCPU})
        try:
            if owned is not None:
                row['cleanup'] = owned.cleanup()
        except BaseException as error:
            row['cleanup_error'] = {'type': type(error).__name__, 'message': str(error)}
            if operation_error is None:
                raise
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited_mask)
    cleanup = row['cleanup']
    require(not cleanup['forced_cleanup'] and not cleanup['errors'] and cleanup['readers_joined'] and
            cleanup['owned_group_absent'] and cleanup['reaped'] and not cleanup['pre_reap_other_members'],
            'fixture required intervention or retained owned resources')
    require(owned.process.returncode == code and owned not in helper.OWNED, 'owner did not reap and unregister fixture')
    row['actual_exit'] = owned.process.returncode
    row['passed'] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    require(sys.platform == 'linux' and args.out.is_absolute() and not out.exists() and
            not any((p/'.git').exists() for p in (out, *out.parents)), 'new absolute external Linux output required')
    out.mkdir(parents=True)
    paths = (HERE/'test_queue.py', HERE/'verify.py', HERE.parent/'tiny-entry-d/verify.py',
             HERE.parent/'tiny-rust-d/verify_runtime.py')
    report = {'passed': False, 'scope': 'real Queue missing-response and queued-on-exit ownership regression',
              'source_pins': [identity(path) for path in paths], 'cases': [],
              'limits': {'wall_seconds': 30, 'inherited_CPU_seconds': 15, 'inherited_AS_bytes': 512*1024**2},
              'compiler_calls': 0, 'chess_engine_calls': 0}
    helper = None
    previous_chld = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    previous = {sig: signal.signal(sig, lambda s, f: (_ for _ in ()).throw(TimeoutError('regression signal '+str(s))))
                for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM, signal.SIGXCPU)}
    try:
        resource.setrlimit(resource.RLIMIT_AS, (512*1024**2,)*2)
        resource.setrlimit(resource.RLIMIT_CPU, (15,)*2)
        signal.alarm(30)
        require(signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL, 'SIGCHLD must retain child wait status')
        report['SIGCHLD_default_during_children'] = True
        shipping = module('rust_d_queue_regression_shipping', paths[1])
        helper = module('rust_d_queue_regression_owned', paths[2])
        strict = module('rust_d_queue_regression_strict', paths[3])
        require(not helper.OWNED, 'isolated helper already owns a child')
        for label, line, code in (('missing-exit-17', b'other\n', 17), ('queued-on-exit-0', b'readyok\n', 0)):
            row = {}
            report['cases'].append(row)
            exercise(out, label, line, code, shipping, helper, strict, row)
        require(not helper.OWNED, 'owned registry did not settle')
        require([identity(path) for path in paths] == report['source_pins'], 'regression inputs changed')
        report['passed'] = True
    except BaseException as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        report['final_cleanup'] = []
        if helper is not None:
            for owned in tuple(helper.OWNED):
                try:
                    report['final_cleanup'].append(owned.cleanup())
                except BaseException as error:
                    report['final_cleanup'].append({'type': type(error).__name__, 'message': str(error)})
            report['owned_remaining'] = len(helper.OWNED)
        signal.alarm(0)
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        if helper is None or not helper.OWNED:
            signal.signal(signal.SIGCHLD, previous_chld)
        (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'passed': report['passed'], 'report': str(out/'results.json')}))


if __name__ == '__main__':
    main()
