#!/usr/bin/env python3
"""Measure selected fixed-codec whole cost after the native layout checkpoint.

Only same-class, twice-reproduced, source-bound native outputs can enter this
cost phase.  Old expectations stay immutable.  Candidate hashes are observed
first-cost metadata, not an automatic update of old production admission.
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out, *out.parents)):
        parser.error('new absolute output outside Git required')
    out.mkdir(parents=True)
    started, deadline = time.monotonic(), time.monotonic()+120
    report = {'complete': False, 'stage': 'fixed whole first-cost', 'engines': [], 'candidate_executed': False,
              'candidate_qualified': False, 'automatic_expected_update': False, 'same_codec_flags_layout_profile': True}

    def save():
        (out/'build.json').write_text(json.dumps(report, indent=2)+'\n')

    def cancelled(signum, frame):
        raise TimeoutError('parent cancelled finite whole first-cost')

    previous_term = signal.signal(signal.SIGTERM, cancelled)

    def run(command):
        remaining = min(45, deadline-time.monotonic())
        if remaining <= 0:
            raise TimeoutError('aggregate fixed whole deadline')
        process, failed = None, None
        try:
            previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                    preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask))
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            stdout, stderr = process.communicate(timeout=remaining)
            if process.returncode:
                raise RuntimeError('fixed loader compiler failed')
            return {'command': command, 'returncode': process.returncode, 'stdout': stdout.decode(errors='replace'), 'stderr': stderr.decode(errors='replace')}
        except BaseException as error:
            failed = repr(error)
            raise
        finally:
            if process is not None:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                if process.poll() is None: process.wait(timeout=3)
                if failed is not None:
                    stdout, stderr = process.communicate(timeout=3)
                    (out/'failed-command.json').write_text(json.dumps({'command': command, 'returncode': process.returncode,
                        'stdout': stdout.decode(errors='replace'), 'stderr': stderr.decode(errors='replace'), 'failure': failed}, indent=2)+'\n')

    save()
    try:
        native_bytes = args.native.read_bytes()
        native = json.loads(native_bytes)
        if not native['complete'] or not native['all_layout_classes_unchanged'] or native.get('source_generation_reproduced') is not True:
            raise ValueError('changed or incomplete layout checkpoint; root confirmation is required, never bypass this guard')
        origin = args.native.resolve().parent
        (out/'native-checkpoint.json').write_bytes(native_bytes)
        report['native_checkpoint_sha256'] = sha(native_bytes)
        if set(native['producer_sources_sha256']) != {'build.py', 'transform.py', 'pins.json'}:
            raise ValueError('unexpected native producer set')
        for name, expected in native['producer_sources_sha256'].items():
            if sha((origin/name).read_bytes()) != expected or (origin/name).read_bytes() != (HERE/name).read_bytes():
                raise ValueError('native producer source drift')
            (out/name).write_bytes((origin/name).read_bytes())
        pins = json.loads((origin/'pins.json').read_text())
        if set(native['inputs']) != set(pins['entry_lf_sha256']) or len(native['inputs']) != 18:
            raise ValueError('expected exactly the eighteen pinned inputs')
        if any(native['inputs'][name]['sha256'] != expected for name, expected in pins['entry_lf_sha256'].items()):
            raise ValueError('checkpoint input set differs from pinned source')
        if len(native['engines']) != 2 or {row['id'] for row in native['engines']} != {'scalar-shipping', 'hq-shipping'}:
            raise ValueError('expected exactly scalar and HQ checkpoint forms')
        if set(native['candidate_source_sha256']) != {'tiny.h', 'board.c', 'search.c', 'runtime.c', 'hq.h', 'hq.c', 'start.S', 'image.ld'}:
            raise ValueError('expected exactly eight candidate source files')
        fixed = out/'entry'
        fixed.mkdir()
        for name, record in native['inputs'].items():
            data = (origin/'entry'/name).read_bytes()
            if sha(data) != record['sha256']:
                raise ValueError('frozen fixed input drift: '+name)
            target = fixed/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (out/'cost.py').write_bytes(Path(__file__).read_bytes())
        recipe = json.loads((fixed/'recipe.json').read_text())
        if recipe['expected'] != pins['old_expected']:
            raise ValueError('old expected images changed')
        checks = module('finite_native_checkpoint', origin/'build.py')
        packer = module('finite_cost_packer', fixed/'packer.py')
        codec = module('finite_cost_codec', fixed/'loader/codec.py')
        for name, expected in native['candidate_source_sha256'].items():
            if sha((origin/'candidate-sources'/name).read_bytes()) != expected:
                raise ValueError('candidate source drift')
            if name != 'runtime.c' and (origin/'candidate-sources'/name).read_bytes() != (fixed/'native'/name).read_bytes():
                raise ValueError('source changed outside the declared runtime')
        transform = module('finite_cost_transform', origin/'transform.py').transform
        reconstructed, policy = transform((fixed/'native/runtime.c').read_bytes())
        if reconstructed != (origin/'candidate-sources/runtime.c').read_bytes() or policy != native['policy']:
            raise ValueError('candidate differs from the one fixed policy transform')
        report['candidate_source_sha256'] = native['candidate_source_sha256']
        report['policy'] = native['policy']
        report['control_reproduced_before_candidate'] = native['baseline_build_sha256']
        for engine in native['engines']:
            form = engine['id']
            old = recipe['expected'][form]
            if old != engine['old_expected']:
                raise ValueError('old expected values changed')
            repeats = engine['native_repeats']
            if len(repeats) != 2:
                raise ValueError('expected two independent native repeats')
            data = Path(repeats[0]['path']).read_bytes()
            if any(sha(Path(row['path']).read_bytes()) != row['sha256'] for row in repeats) or Path(repeats[1]['path']).read_bytes() != data:
                raise ValueError('new native repeat identity changed')
            checkpoint = checks.class_check(data, old, packer)
            if not checkpoint['same_class'] or checkpoint != engine['layout_checkpoint']:
                raise ValueError('new native layout class changed; STOP for root confirmation')
            directory = out/form
            directory.mkdir()
            native_path = directory/'native'
            native_path.write_bytes(data)
            native_path.chmod(0o755)
            compiled = []
            for attempt in ('fixed', 'fixed-repeat'):
                payload = codec.fixed_compress(codec.bcj(bytes(data)))
                if codec.bcj(codec.fixed_decompress(payload, len(data)), inverse=True) != data:
                    raise ValueError('fixed codec restoration differs')
                compiled.append(packer.compile_loader(directory/attempt, fixed/'loader', payload, checkpoint['layout'], recipe['loader_flags'], run, sha))
            if Path(compiled[0]['path']).read_bytes() != Path(compiled[1]['path']).read_bytes():
                raise ValueError('independent whole repeats differ')
            compiled[0].update(codec='fixed', reproduction=compiled[1])
            row = {'id': form, 'native': str(native_path), 'input_sha256': sha(data), 'input_bytes': len(data), 'layout': checkpoint['layout'],
                   'candidates': [compiled[0]], 'old_whole_bytes': old['whole_bytes'], 'whole_delta': compiled[0]['bytes']-old['whole_bytes'],
                   'old_native_bytes': old['native_bytes'], 'native_delta': len(data)-old['native_bytes'], 'DEV_exact': engine['DEV_exact']}
            report['engines'].append(row)
            save()
        report['both_whole_files_strictly_smaller'] = all(row['whole_delta'] < 0 for row in report['engines'])
        # Same old CHECKPOINT branch is necessary only for the separately
        # authorized narrow runtime proof if the whole files actually win.
        if report['both_whole_files_strictly_smaller']:
            for row in report['engines']:
                data = Path(row['native']).read_bytes()
                payload = codec.fixed_compress(codec.bcj(data))
                row['candidates'][0]['audit'] = packer.compile_loader(out/row['id']/'fixed-audit', fixed/'loader', payload, row['layout'], recipe['loader_flags'], run, sha, checkpoint=True)
        report['complete'] = True
    except Exception as error:
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        report['elapsed_seconds'] = time.monotonic()-started
        save()
        signal.signal(signal.SIGTERM, previous_term)
    print(json.dumps({'complete': True, 'both_gain': report['both_whole_files_strictly_smaller'], 'forms': [
        {'id': row['id'], 'native': row['input_bytes'], 'whole': row['candidates'][0]['bytes'], 'delta': row['whole_delta'],
         'whole_sha256': row['candidates'][0]['sha256']} for row in report['engines']]}))


if __name__ == '__main__':
    main()
