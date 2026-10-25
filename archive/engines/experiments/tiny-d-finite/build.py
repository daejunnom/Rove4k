#!/usr/bin/env python3
"""Freeze exact controls, reproduce them, and measure ONE finite native policy.

This phase deliberately does not pack or run a candidate image.  It reports
new native entry/segments/page class first; a changed class requires root
confirmation before any candidate restoration admission or runtime work.
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

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def class_check(native, expected, packer):
    """Compare all old layout constraints; only RX byte length/entry may move."""
    parsed = packer.elf(native)
    old = expected['layout']
    wanted = [dict(row) for row in old['segments']]
    wanted[0]['filesz'] = wanted[0]['memsz'] = len(native)
    pages = (len(native)+4095)&-4096
    same = (parsed['segments'] == wanted and pages == old['image_pages'] and
            all(parsed[key] == old[key] for key in ('section_offset', 'section_size', 'section_count', 'section_names')) and
            old['image_base']+232 <= parsed['entry'] < old['image_base']+len(native) and
            old['image_base']+pages == old['bss_base'])
    layout = {**old, **parsed, 'image_size': len(native), 'image_pages': pages}
    return {'same_class': same, 'old_entry': old['entry'], 'new_entry': parsed['entry'], 'old_native_bytes': expected['native_bytes'],
            'new_native_bytes': len(native), 'old_image_pages': old['image_pages'], 'new_image_pages': pages,
            'old_bss_base': old['bss_base'], 'actual_bss_base': next(row['vaddr'] for row in parsed['segments'] if row['type']==1 and row['flags']==6),
            'layout': layout, 'root_confirmation_required_before_candidate_pack': not same}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out, *out.parents)):
        parser.error('new absolute output outside Git required')
    out.mkdir(parents=True)
    started, deadline = time.monotonic(), time.monotonic()+300
    report = {'complete': False, 'stage': 'native-only first-cost checkpoint', 'inputs': {}, 'engines': [],
              'candidate_packed': False, 'candidate_executed': False, 'candidate_qualified': False,
              'scope': 'one explicit finite shipping policy; no expected binary hash updates or sweeps'}

    def save():
        (out/'build.json').write_text(json.dumps(report, indent=2)+'\n')

    def cancelled(signum, frame):
        raise TimeoutError('parent cancelled finite native checkpoint')

    previous_term = signal.signal(signal.SIGTERM, cancelled)

    def run(command, cap=80):
        remaining = min(cap, deadline-time.monotonic())
        if remaining <= 0:
            raise TimeoutError('aggregate finite native deadline')
        process, failed = None, None
        try:
            previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                    preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask))
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            stdout, stderr = process.communicate(timeout=remaining)
            record = {'command': command, 'returncode': process.returncode, 'stdout': stdout.decode(errors='replace'), 'stderr': stderr.decode(errors='replace')}
            if process.returncode:
                raise RuntimeError('fixed command failed')
            return record
        except BaseException as error:
            failed = {'type': type(error).__name__, 'message': str(error)}
            raise
        finally:
            if process is not None:
                if process.poll() is None:
                    try: os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError: pass
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired: pass
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                if process.poll() is None: process.wait(timeout=3)
                if failed is not None:
                    stdout, stderr = process.communicate(timeout=3)
                    (out/'failed-command.json').write_text(json.dumps({'command': command, 'returncode': process.returncode,
                        'stdout': stdout.decode(errors='replace'), 'stderr': stderr.decode(errors='replace'), 'failure': failed}, indent=2)+'\n')

    save()
    try:
        pins = json.loads((HERE/'pins.json').read_text())
        frozen = out/'entry'
        frozen.mkdir()
        for name, expected in pins['entry_lf_sha256'].items():
            raw = (HERE/'inputs/entry'/name).read_bytes()
            data = raw.replace(b'\r\n', b'\n')
            if b'\r' in data or sha(data) != expected:
                raise ValueError('pinned entry input mismatch: '+name)
            target = frozen/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            report['inputs'][name] = {'bytes': len(data), 'sha256': sha(data), 'working_sha256': sha(raw)}
        for name in ('build.py', 'transform.py', 'pins.json'):
            data = (HERE/name).read_bytes()
            (out/name).write_bytes(data)
        report['producer_sources_sha256'] = {name: sha((out/name).read_bytes()) for name in ('build.py', 'transform.py', 'pins.json')}
        report['prechange_external_freeze_sha256'] = pins['prechange_freeze_sha256']
        recipe = json.loads((frozen/'recipe.json').read_text())
        if recipe['expected'] != pins['old_expected']:
            raise ValueError('old expected images were changed')
        report['baseline_command'] = run([sys.executable, '-I', '-B', str(frozen/'build.py'), '--out', str(out/'control')], cap=200)
        baseline_bytes = (out/'control/build.json').read_bytes()
        baseline = json.loads(baseline_bytes)
        if not baseline['complete']:
            raise ValueError('exact old control failed reproduction')
        report['baseline_build_sha256'] = sha(baseline_bytes)
        packer = module('finite_native_fixed_packer', frozen/'packer.py')
        transformed = module('finite_native_transform', out/'transform.py')
        candidate, policy = transformed.transform((frozen/'native/runtime.c').read_bytes())
        repeated_source, repeated_policy = transformed.transform((frozen/'native/runtime.c').read_bytes())
        if candidate != repeated_source or policy != repeated_policy:
            raise ValueError('independent fixed source generations differ')
        report['source_generation_reproduced'] = True
        report['policy'] = policy
        source = out/'candidate-sources'
        source.mkdir()
        for name in ('tiny.h', 'board.c', 'search.c', 'runtime.c', 'hq.h', 'hq.c', 'start.S', 'image.ld'):
            data = candidate if name == 'runtime.c' else (frozen/'native'/name).read_bytes()
            (source/name).write_bytes(data)
        report['candidate_source_sha256'] = {p.name: sha(p.read_bytes()) for p in sorted(source.iterdir())}
        report['only_changed_native_source'] = 'runtime.c'
        report['all_other_native_source_bytes_exact'] = all((source/name).read_bytes()==(frozen/'native'/name).read_bytes() for name in report['candidate_source_sha256'] if name!='runtime.c')
        for form, expected in recipe['expected'].items():
            directory = out/form
            directory.mkdir()
            row = {'id': form, 'old_expected': expected, 'native_repeats': [], 'candidate_qualified': False}
            report['engines'].append(row)
            for attempt in ('first', 'repeat'):
                destination = directory/attempt
                destination.mkdir()
                command = ['cc', *recipe['native_flags'], f"-DD_HQ={expected['hq']}", '-DDEV=0',
                    *[str(source/name) for name in recipe['native_units']], '-Wl,-T,'+str(source/'image.ld'), '-o', str(destination/'linked')]
                compiled = run(command)
                (destination/'compile.json').write_text(json.dumps(compiled, indent=2)+'\n')
                native = packer.strip_native((destination/'linked').read_bytes())
                target = destination/'x'
                target.write_bytes(native)
                target.chmod(0o755)
                row['native_repeats'].append({'path': str(target), 'bytes': len(native), 'sha256': sha(native), 'compile': compiled})
            if Path(row['native_repeats'][0]['path']).read_bytes() != Path(row['native_repeats'][1]['path']).read_bytes():
                raise ValueError('candidate native repeats differ')
            row['layout_checkpoint'] = class_check(native, expected, packer)
            # DEV source preprocessing and native are matched independently;
            # these are equality checks, not a new diagnostic execution claim.
            dev = []
            for label, inputs in (('control', frozen/'native'), ('finite', source)):
                folder = directory/('dev-'+label)
                folder.mkdir()
                pp = run(['cc', '-std=c11', '-DWORKERS=2', '-DTT_BITS=18', f"-DD_HQ={expected['hq']}", '-DDEV=1', '-E', '-P', str(inputs/'runtime.c')])['stdout'].encode()
                (folder/'runtime-preprocessed.c').write_bytes(pp)
                command = ['cc', *recipe['native_flags'], f"-DD_HQ={expected['hq']}", '-DDEV=1',
                    *[str(inputs/name) for name in recipe['native_units']], '-Wl,-T,'+str(inputs/'image.ld'), '-o', str(folder/'linked')]
                compiled = run(command)
                (folder/'compile.json').write_text(json.dumps(compiled, indent=2)+'\n')
                data = packer.strip_native((folder/'linked').read_bytes())
                (folder/'x').write_bytes(data)
                dev.append({'preprocessed_sha256': sha(pp), 'native_sha256': sha(data), 'native_bytes': len(data)})
            if dev[0] != dev[1]:
                raise ValueError('DEV preprocessing/native changed')
            row['DEV_exact'] = dev[0]
            save()
            print(json.dumps({'form': form, 'native_bytes': len(native), 'native_sha256': sha(native),
                'layout': row['layout_checkpoint'], 'DEV_exact': True}), flush=True)
        report['all_layout_classes_unchanged'] = all(row['layout_checkpoint']['same_class'] for row in report['engines'])
        report['complete'] = True
    except Exception as error:
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        report['elapsed_seconds'] = time.monotonic()-started
        save()
        signal.signal(signal.SIGTERM, previous_term)


if __name__ == '__main__':
    main()
