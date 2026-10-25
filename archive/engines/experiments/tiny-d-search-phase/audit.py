#!/usr/bin/env python3
"""Build-only separate CHECKPOINT images; never launch shipping or audit ELFs."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WHOLE_SHA = '9f632a7e5fc90256044067790a9d62568411607fcf798b4466874df874d1f6d8'
EXPECTED = {
    'scalar-shipping': {'native_bytes': 8284, 'native_sha256': '875a8263ab335778fc7be58fda2a9975425a5445ffd7300c80c04f5179e2e841', 'entry': 4202204,
                        'whole_bytes': 7501, 'whole_sha256': 'c18007cc3649df8e0ee8c4488f6967a17d8df0b26a5c88370e4094d9ca3129c0'},
    'hq-shipping': {'native_bytes': 8672, 'native_sha256': '4d42ad7e663f826601d01b3f06d778483fc7ba2ec82d80b619967a1fb952061f', 'entry': 4202521,
                    'whole_bytes': 7753, 'whole_sha256': '04c4cb588b103d6d31a302ab5177c58dd532278b7ab7eb4ef0ac6098603994c6'},
}
RUNNING = set()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(value, detail):
    if not value:
        raise AssertionError(detail)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--whole-build', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    need(args.out.is_absolute() and not out.exists() and not any((p / '.git').exists() for p in (out, *out.parents)), 'new absolute external output required')
    out.mkdir(parents=True)
    started, deadline, phase = time.monotonic(), time.monotonic() + 120, 'inputs'
    report = {'complete': False, 'scope': 'separate CHECKPOINT1 build-only images; newly observed audit identities must be manually pinned before execution',
              'inputs': {}, 'audits': [], 'failures': [], 'cleanup': [], 'audit_executed': False, 'shipping_executed': False}

    def cancelled(signum, frame):
        raise TimeoutError('audit producer SIGTERM')

    prior_term = signal.signal(signal.SIGTERM, cancelled)

    def run(command):
        directory, proc, stdout, stderr = Path(command[-1]).parent, None, b'', b''
        record = {'command': command}
        try:
            inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            try:
                proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                                        preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, inherited))
                RUNNING.add(proc)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
            remaining = min(45, deadline - time.monotonic())
            need(remaining > 0, 'aggregate audit deadline')
            stdout, stderr = proc.communicate(timeout=remaining)
            need(proc.returncode == 0, 'CHECKPOINT compilation failed')
        except BaseException as error:
            record['failure'] = {'type': type(error).__name__, 'detail': str(error)}
            raise
        finally:
            if proc is not None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = proc.communicate(timeout=3)
                record.update(returncode=proc.returncode, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr))
                RUNNING.discard(proc)
            (directory / 'compile.stdout').write_bytes(stdout)
            (directory / 'compile.stderr').write_bytes(stderr)
            (directory / 'compile-command.json').write_text(json.dumps(record, indent=2) + '\n')
        return record

    try:
        whole_raw = args.whole_build.read_bytes()
        need(sha(whole_raw) == WHOLE_SHA, 'whole first-cost receipt differs')
        whole = json.loads(whole_raw)
        need(whole['complete'] and not whole['failures'] and not whole['cleanup'] and not whole['candidate_executed'] and not whole['candidate_qualified'], 'whole checkpoint scope/completion differs')
        need(len(whole['candidates']) == 2 and {r['id'] for r in whole['candidates']} == set(EXPECTED), 'two exact forms required')
        frozen = out / 'recipe'
        for name in ('audit.py', *whole['inputs']):
            raw = (HERE / name).read_bytes().replace(b'\r\n', b'\n')
            need(b'\r' not in raw, 'lone CR source')
            if name not in ('audit.py', 'README.md'):
                need(sha(raw) == whole['inputs'][name]['sha256'], 'whole producer source differs: ' + name)
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            report['inputs'][name] = {'bytes': len(raw), 'sha256': sha(raw)}
        (frozen / 'whole-build.json').write_bytes(whole_raw)
        entry = frozen / 'inputs/entry'
        recipe = json.loads((entry / 'recipe.json').read_bytes())
        packer, codec = load('phase_audit_packer', entry / 'packer.py'), load('phase_audit_codec', entry / 'loader/codec.py')
        report.update(whole_checkpoint_sha256=WHOLE_SHA, explicit_shipping_admission=EXPECTED, loader_flags=recipe['loader_flags'], resources=recipe['profile'])
        for row in whole['candidates']:
            phase, explicit = row['id'], EXPECTED[row['id']]
            native_path = args.whole_build.resolve().parent / 'recipe/natives/candidates' / row['id']
            native = native_path.read_bytes()
            need(len(native) == explicit['native_bytes'] and sha(native) == explicit['native_sha256'], 'literal native differs')
            expected = copy.deepcopy(recipe['expected'][row['id']])
            expected['native_bytes'], expected['native_sha256'] = explicit['native_bytes'], explicit['native_sha256']
            expected['layout']['entry'], expected['layout']['image_size'] = explicit['entry'], explicit['native_bytes']
            expected['layout']['segments'][0]['filesz'] = expected['layout']['segments'][0]['memsz'] = explicit['native_bytes']
            layout = packer.admit(native, expected, sha)
            need(row['layout'] == layout and row['whole_reproduced'] and row['whole_strictly_smaller'], 'whole layout/gain gate differs')
            for spec in (row['whole'], row['repeat']):
                raw = Path(spec['path']).read_bytes()
                need(len(raw) == explicit['whole_bytes'] and sha(raw) == explicit['whole_sha256'], 'literal shipping whole differs')
            payload = codec.fixed_compress(codec.bcj(native))
            need(payload == (Path(row['whole']['path']).parent / 'payload.bin').read_bytes(), 'audit payload differs from shipping')
            need(codec.bcj(codec.fixed_decompress(payload, len(native)), inverse=True) == native, 'audit payload inverse differs')
            audit = packer.compile_loader(out / row['id'] / 'checkpoint', entry / 'loader', payload, layout, recipe['loader_flags'], run, sha, checkpoint=True)
            report['audits'].append({'id': row['id'], 'native_sha256': explicit['native_sha256'], 'shipping_sha256': explicit['whole_sha256'], 'layout': layout,
                                     'payload_equal_shipping': True, 'audit': audit})
        report['complete'] = True
    except BaseException as error:
        report['complete'] = False
        report['failures'].append({'phase': phase, 'type': type(error).__name__, 'detail': str(error)})
    finally:
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        try:
            for proc in list(RUNNING):
                try:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.communicate(timeout=3)
                except BaseException as error:
                    report['failures'].append({'phase': 'registered-cleanup', 'type': type(error).__name__, 'detail': str(error)})
                report['complete'] = False
            report['elapsed_seconds'] = time.monotonic() - started
            (out / 'build.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        finally:
            signal.signal(signal.SIGTERM, prior_term)
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
    print(json.dumps({'complete': report['complete'], 'out': str(out), 'failures': report['failures'],
                      'audits': [{'id': r['id'], 'bytes': r['audit']['bytes'], 'sha256': r['audit']['sha256']} for r in report['audits']]}))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
