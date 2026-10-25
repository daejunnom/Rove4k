#!/usr/bin/env python3
"""Build separate exact CHECKPOINT images; never execute an engine or loader."""
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

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PINS_SHA = '792f510f4fd69baf72d2ab2a928baaf0ed550601e6a3d6ac06bbe5ae753e529d'
WHOLE_SHA = '4b0b4f62b4266c8e2e60c1d8b969fe28de0ff0970822c380a5d4156bd0716b83'
CLASSES = {
    'scalar-shipping': (0x400000, 8192, 0x402000, 175092, 176128, 0x3ff000, 0x2f000, 0x42d000),
    'hq-shipping': (0x400000, 12288, 0x403000, 175092, 176128, 0x3ff000, 0x30000, 0x42e000),
}
CLASS_FIELDS = ('image_base', 'image_pages', 'bss_base', 'bss_size', 'bss_pages', 'guard_base', 'reserve_size', 'upper_guard')
RUNNING = set()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(value, detail):
    if not value:
        raise AssertionError(detail)


def module(name, path):
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
    need(sys.platform == 'linux', 'fixed Linux target required')
    need(args.out.is_absolute() and not out.exists() and not any((p / '.git').exists() for p in (out, *out.parents)), 'new absolute output outside Git required')
    out.mkdir(parents=True)
    started, deadline, phase = time.monotonic(), time.monotonic() + 120, 'inputs'
    report = {'complete': False, 'scope': 'separate CHECKPOINT1 build only for two explicit layout-phase images; no execution or generic admission',
              'inputs': {}, 'audits': [], 'failures': [], 'cleanup': [], 'shipping_executed': False, 'audit_executed': False}

    def cancelled(signum, frame):
        raise TimeoutError('audit producer SIGTERM')

    prior_term = signal.signal(signal.SIGTERM, cancelled)

    def run(command):
        directory, process, stdout, stderr = Path(command[-1]).parent, None, b'', b''
        record = {'command': command, 'forced_cleanup': False, 'cleanup_errors': []}
        try:
            inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                                           preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, inherited))
                RUNNING.add(process)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
            remaining = min(45, deadline - time.monotonic())
            need(remaining > 0, 'aggregate audit deadline')
            stdout, stderr = process.communicate(timeout=remaining)
            need(process.returncode == 0, 'CHECKPOINT compilation failed')
        except BaseException as error:
            record['failure'] = {'type': type(error).__name__, 'detail': str(error)}
            raise
        finally:
            if process is not None:
                try:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                        record['forced_cleanup'] = True
                    except ProcessLookupError:
                        pass
                    stdout, stderr = process.communicate(timeout=3)
                    record['returncode'] = process.returncode
                    RUNNING.discard(process)
                except BaseException as error:
                    record['cleanup_errors'].append({'type': type(error).__name__, 'detail': str(error)})
            record.update(stdout_sha256=sha(stdout), stderr_sha256=sha(stderr))
            (directory / 'compile.stdout').write_bytes(stdout)
            (directory / 'compile.stderr').write_bytes(stderr)
            (directory / 'compile-command.json').write_text(json.dumps(record, indent=2) + '\n')
        need(not record['forced_cleanup'] and not record['cleanup_errors'], 'compiler required cleanup intervention')
        return record

    try:
        pins_raw = (HERE / 'pins.json').read_bytes()
        need(sha(pins_raw) == PINS_SHA, 'literal source/class pins differ')
        pins = json.loads(pins_raw)
        need(len(pins['frozen_inputs']) == 31 and set(pins['expected']) == set(CLASSES), 'fixed input/class matrix differs')
        frozen = out / 'recipe'
        for name in ('pins.json', 'audit.py', *pins['frozen_inputs']):
            raw = (HERE / name).read_bytes()
            need(b'\r' not in raw, 'LF source required: ' + name)
            if name in pins['frozen_inputs']:
                pin = pins['frozen_inputs'][name]
                need((len(raw), sha(raw)) == (pin['bytes'], pin['sha256']), 'frozen input differs: ' + name)
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            report['inputs'][name] = {'bytes': len(raw), 'sha256': sha(raw)}
        whole_raw = args.whole_build.read_bytes()
        need(sha(whole_raw) == WHOLE_SHA == pins['whole_report_sha256'], 'exact combined whole checkpoint required')
        whole = json.loads(whole_raw)
        need(whole['complete'] and not whole.get('failure') and whole['production_runtime_sessions'] == 0
             and whole['whole_and_payload_reproduced'] and whole['whole_compilations'] == 8, 'whole checkpoint scope/completion differs')
        (frozen / 'whole-build.json').write_bytes(whole_raw)
        entry = frozen / 'inputs/combined/control'
        recipe = json.loads((entry / 'recipe.json').read_bytes())
        packer = module('combined_proof_packer', entry / 'packer.py')
        codec = module('combined_proof_codec', entry / 'loader/codec.py')
        need(recipe['profile'] == {'workers': 2, 'tt_bits': 18, 'ply': 128, 'dev': 0}, 'shipping profile changed')
        report.update(whole_checkpoint_sha256=WHOLE_SHA, loader_flags=recipe['loader_flags'], resources=recipe['profile'])
        source = args.whole_build.resolve().parent
        for form in ('scalar-shipping', 'hq-shipping'):
            phase = form
            expected = pins['expected'][form]
            layout = expected['layout']
            need(tuple(layout[key] for key in CLASS_FIELDS) == CLASSES[form], 'exact per-form mapping class differs')
            native_path = source / 'native-first/candidate' / form / '1/x'
            native = native_path.read_bytes()
            need((len(native), sha(native)) == (expected['native_bytes'], expected['native_sha256']), 'literal native differs')
            need(native == (source / 'native-first/candidate' / form / '2/x').read_bytes(), 'native repeat drift')
            try:
                packer.admit(native, recipe['expected'][form], sha)
            except ValueError as error:
                rejection = str(error)
            else:
                raise AssertionError('unchanged original admission accepted candidate')
            # This new proof admits only the complete pinned header/PHDR and the
            # two root-approved literal classes; original packer.admit is intact.
            parsed = packer.elf(native)
            need(all(parsed[key] == layout[key] for key in parsed), 'literal full ELF header/segments differ')
            need(layout['image_size'] == len(native) and layout['image_pages'] == (len(native) + 4095) // 4096 * 4096
                 and layout['bss_base'] == layout['image_base'] + layout['image_pages']
                 and layout['upper_guard'] == layout['bss_base'] + layout['bss_pages']
                 and layout['reserve_size'] == layout['upper_guard'] + 4096 - layout['guard_base'], 'exact class geometry inconsistent')
            payload = codec.fixed_compress(codec.bcj(native))
            need(codec.bcj(codec.fixed_decompress(payload, len(native)), inverse=True) == native, 'payload inverse mismatch')
            for attempt in (1, 2):
                base = source / 'candidate' / form / str(attempt)
                shipping = (base / 'x').read_bytes()
                need((len(shipping), sha(shipping)) == (expected['whole_bytes'], expected['whole_sha256']), 'literal shipping image differs')
                need((base / 'payload.bin').read_bytes() == payload, 'shipping payload differs')
            audit = packer.compile_loader(out / form / 'checkpoint', entry / 'loader', payload, layout, recipe['loader_flags'], run, sha, checkpoint=True)
            report['audits'].append({'id': form, 'native_sha256': sha(native), 'shipping_sha256': expected['whole_sha256'],
                                     'layout': layout, 'original_admission_rejection': rejection, 'payload_equal_shipping': True, 'audit': audit})
        report['complete'] = True
    except BaseException as error:
        report['complete'] = False
        report['failures'].append({'phase': phase, 'type': type(error).__name__, 'detail': str(error)})
    finally:
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        try:
            for process in list(RUNNING):
                row = {'pid': process.pid}
                try:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.communicate(timeout=3)
                    RUNNING.discard(process)
                    row['returncode'] = process.returncode
                except BaseException as error:
                    row['failure'] = {'type': type(error).__name__, 'detail': str(error)}
                report['cleanup'].append(row)
                report['complete'] = False
            report['elapsed_seconds'] = time.monotonic() - started
            (out / 'build.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        finally:
            signal.signal(signal.SIGTERM, prior_term)
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
    print(json.dumps({'complete': report['complete'], 'out': str(out), 'failures': report['failures'],
                      'audits': [{'id': row['id'], 'bytes': row['audit']['bytes'], 'sha256': row['audit']['sha256']} for row in report['audits']]}))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
