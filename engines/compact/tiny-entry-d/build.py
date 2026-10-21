#!/usr/bin/env python3
"""Regenerate both selected C D own-ELFs from maintained source, without history.

Resources, source bytes, compiler/linker order, layout and codec are fixed.
Only --out is configurable.  Historical receipt hashes are metadata, never
paths opened during this build.  All generated files remain outside Git.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CODEC = 'rove4k-context-h24-base10-fixed21-body232-zero4-v3'
EXECUTION_ISA = 'linux-x86_64-sse4.2-cx16-crc32b-v1'
SHIPPING_PROTOCOL = {
    'id': 'finite-minimum-v1', 'identification': False,
    'stop': 'consume', 'ucinewgame': 'consume', 'infinite': 'consume',
    'default_budget_ms': 1000, 'own_clock_formula': 'unchanged',
    'hard_wall_cap': False,
    'completion_fences': 'next go, position, quit, EOF acquire pending==0 after result output',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalized(path):
    raw = path.read_bytes()
    data = raw.replace(b'\r\n', b'\n')
    if b'\r' in data:
        raise ValueError('lone CR in maintained text: ' + str(path))
    return raw, data


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out, *out.parents)) or HERE in out.parents:
        parser.error('a new absolute output outside any Git checkout is required')
    if sys.platform != 'linux' or platform.machine() != 'x86_64':
        parser.error('the qualified fixed target is Linux x86-64')
    recipe = json.loads(normalized(HERE/'recipe.json')[1])
    if recipe['format'] != 1 or recipe['profile'] != {'workers': 2, 'tt_bits': 18, 'ply': 128, 'dev': 0}:
        raise ValueError('unsupported selected profile')
    if list(recipe['expected']) != ['scalar-shipping', 'hq-shipping']:
        raise ValueError('exactly the selected scalar/HQ images are required')
    if recipe['codec'] != CODEC:
        raise ValueError('unsupported fixed context codec')
    if recipe.get('execution_isa') != EXECUTION_ISA:
        raise ValueError('unsupported explicit execution ISA profile')
    if any(expected['audit_bytes'] is None or expected['audit_sha256'] is None for expected in recipe['expected'].values()):
        raise ValueError('context audit literals require explicit discovery and admission')
    if recipe['shipping_protocol'] != SHIPPING_PROTOCOL:
        raise ValueError('unsupported selected shipping protocol')
    out.mkdir(parents=True)
    frozen = out/'inputs'
    frozen.mkdir()
    started, deadline = time.monotonic(), time.monotonic()+180
    report = {'complete': False, 'scope': 'maintained body232 context own-ELFs; compiled native ELF, zero232 restored image and own-ELF have separate full identities; fixed model/ISA/layout/flags',
              'resources': recipe['profile'], 'execution_isa': EXECUTION_ISA, 'inputs': {}, 'engines': [], 'negative_decoder_controls': [],
              'shipping_protocol': recipe['shipping_protocol'],
              'qualified_receipt_reuse_metadata_only': recipe['qualified_receipts_metadata_only'],
              'runtime_validation': 'separate verify.py receipt required', 'under4096': False}

    def cancelled(signum, frame):
        raise TimeoutError('parent cancelled selected-entry build')

    previous_term = signal.signal(signal.SIGTERM, cancelled)

    def save():
        (out/'build.json').write_text(json.dumps(report, indent=2)+'\n')

    def run(command, timeout=60):
        remaining = min(timeout, deadline-time.monotonic())
        if remaining <= 0:
            raise TimeoutError('aggregate fixed-build deadline')
        process = None
        failed = None
        try:
            previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                                           preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask))
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            stdout, stderr = process.communicate(timeout=remaining)
            record = {'command': command, 'returncode': process.returncode, 'stdout': stdout.decode(errors='replace'),
                      'stderr': stderr.decode(errors='replace')}
            if process.returncode:
                (out/'failed-command.json').write_text(json.dumps(record, indent=2)+'\n')
                raise RuntimeError('fixed command failed; see failed-command.json')
            return record
        except BaseException as error:
            failed = {'type': type(error).__name__, 'message': str(error)}
            raise
        finally:
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                if process.poll() is None:
                    process.wait(timeout=3)
                if failed is not None:
                    stdout, stderr = process.communicate(timeout=3)
                    (out/'failed-command.json').write_text(json.dumps({'command': command, 'returncode': process.returncode,
                        'stdout': stdout.decode(errors='replace'), 'stderr': stderr.decode(errors='replace'), 'failure': failed}, indent=2)+'\n')

    save()
    try:
        expected_inputs = {**recipe['native_source_sha256'], **recipe['loader_source_sha256']}
        for name in (*expected_inputs, 'build.py', 'packer.py', 'recipe.json'):
            raw, data = normalized(HERE/name)
            if name in expected_inputs and sha(data) != expected_inputs[name]:
                raise ValueError('maintained source differs from fixed recipe: '+name)
            target = frozen/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            report['inputs'][name] = {'bytes': len(data), 'sha256': sha(data), 'working_bytes_sha256': sha(raw), 'LF_normalization': raw != data}
        packer = module('entry_d_fixed_packer', frozen/'packer.py')
        codec = module('entry_d_context_codec', frozen/'loader/codec.py')
        report['tools'] = {'cc': run(['cc', '--version'])['stdout'], 'ld': run(['ld', '--version'])['stdout'],
                           'python': sys.version, 'platform': platform.platform()}
        for form, expected in recipe['expected'].items():
            directory = out/form
            directory.mkdir()
            natives = []
            for attempt in ('native-first', 'native-repeat'):
                destination = directory/attempt
                destination.mkdir()
                command = ['cc', *recipe['native_flags'], f"-DD_HQ={expected['hq']}", '-DDEV=0',
                           *[str(frozen/'native'/name) for name in recipe['native_units']],
                           '-Wl,-T,'+str(frozen/'native/image.ld'), '-o', str(destination/'linked')]
                compiled = run(command)
                (destination/'compile.json').write_text(json.dumps(compiled, indent=2)+'\n')
                native = packer.strip_native((destination/'linked').read_bytes())
                layout = packer.admit(native, expected, sha)
                path = destination/'x'
                path.write_bytes(native)
                path.chmod(0o755)
                natives.append({'path': str(path), 'bytes': len(native), 'sha256': sha(native), 'compile': compiled})
            if Path(natives[0]['path']).read_bytes() != Path(natives[1]['path']).read_bytes():
                raise ValueError('native independent repeats differ')
            native = Path(natives[0]['path']).read_bytes()
            image = packer.body_image(expected)
            if codec.body_image(native)[1] != image:
                raise ValueError('codec/packer body232 image identities differ')
            restored = bytes(image['zero_prefix_bytes']) + native[image['zero_prefix_bytes']:]
            if (len(restored), sha(restored)) != (image['restored_image_bytes'], image['restored_image_sha256']):
                raise ValueError('whole restored-image identity differs')
            restored_path = directory/'restored-image.bin'
            restored_path.write_bytes(restored)
            complete = []
            model = codec.load_models((frozen/'loader/models.json').read_bytes(), form)
            if model[0] != expected['model_wmask']:
                raise ValueError('selected fixed21 WMASK differs')
            for attempt in ('context', 'context-repeat'):
                payload, encoding = codec.encode_body_native(native, model)
                if encoding['format'] != CODEC or encoding['header_bytes'] != 21:
                    raise ValueError('selected fixed21 packet format differs')
                if encoding['image'] != image or encoding['decoded_bytes'] != len(native)-image['zero_prefix_bytes']:
                    raise ValueError('body232 decoder extent or image identity differs')
                if (len(payload), sha(payload)) != (expected['payload_bytes'], expected['payload_sha256']):
                    raise ValueError('independent encoder differs from selected context payload')
                candidate = packer.compile_loader(directory/attempt, frozen/'loader', payload, layout, recipe['loader_flags'], run, sha, model_wmask=model[0], image=image)
                candidate['encoding'] = encoding
                if (candidate['bytes'], candidate['sha256'], candidate['payload_bytes'], candidate['loader_and_headers_bytes']) != (
                    expected['whole_bytes'], expected['whole_sha256'], expected['payload_bytes'], expected['loader_and_headers_bytes']):
                    raise ValueError('whole file differs from selected qualification')
                complete.append(candidate)
            if Path(complete[0]['path']).read_bytes() != Path(complete[1]['path']).read_bytes():
                raise ValueError('independent complete-file repeats differ')
            audit = packer.compile_loader(directory/'context-audit', frozen/'loader', payload, layout, recipe['loader_flags'], run, sha, model_wmask=model[0], checkpoint=True, image=image)
            if (audit['bytes'], audit['sha256']) != (expected['audit_bytes'], expected['audit_sha256']):
                raise ValueError('same admitted CHECKPOINT image differs')
            complete[0].update(codec=CODEC, reproduction=complete[1], audit=audit, within4096=False)
            report['engines'].append({'id': form, 'input_bytes': len(native), 'input_sha256': sha(native), 'layout': layout,
                                      'image': image, 'restored_image': {'path': str(restored_path), 'bytes': len(restored), 'sha256': sha(restored)},
                                      'native': natives[0]['path'], 'native_rebuilds': natives, 'native_reproduced': True,
                                      'candidates': [complete[0]], 'whole_reproduced': True})
            save()
            print(json.dumps({'form': form, 'native': len(native), 'whole': complete[0]['bytes'], 'sha256': complete[0]['sha256']}), flush=True)
        report['complete'] = True
    except BaseException as error:
        report['complete'] = False
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        report['elapsed_seconds'] = time.monotonic()-started
        save()
        signal.signal(signal.SIGTERM, previous_term)


if __name__ == '__main__':
    main()
