#!/usr/bin/env python3
"""Measure one worker-reset candidate, scalar/HQ once; no codec or target runs."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import resource
import signal
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def sections(data):
    offset = struct.unpack_from('<Q', data, 40)[0]
    width, count, names = struct.unpack_from('<HHH', data, 58)
    header = struct.unpack_from('<IIQQQQIIQQ', data, offset+width*names)
    strings = data[header[4]:header[4]+header[5]]
    result = []
    for i in range(count):
        h = struct.unpack_from('<IIQQQQIIQQ', data, offset+width*i)
        if h[2]&2:
            result.append(dict(name=strings[h[0]:].split(b'\0', 1)[0].decode(), type=h[1],
                               flags=h[2], address=h[3], offset=h[4], bytes=h[5], align=h[8]))
    return result


def geometry(parsed):
    loads = [s for s in parsed['segments'] if s['type'] == 1]
    rx, rw = ([s for s in loads if s['flags'] == f] for f in (5, 6))
    require(len(rx) == len(rw) == 1, 'record requires one RX and one RW segment')
    rx, rw = rx[0], rw[0]
    pages = lambda size: (size+4095)//4096*4096
    lower, upper = rx['vaddr']-4096, rw['vaddr']+pages(rw['memsz'])
    return {'entry': parsed['entry'], 'image_base': rx['vaddr'], 'image_bytes': rx['filesz'],
            'image_pages': pages(rx['memsz']), 'bss_base': rw['vaddr'], 'bss_size': rw['memsz'],
            'bss_pages': pages(rw['memsz']), 'RW_file_bytes': rw['filesz'],
            'lower_guard_derived': lower, 'upper_guard_derived': upper,
            'reservation_derived': upper+4096-lower,
            'guard_scope': 'derived static geometry only; no mapping or admission observation'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and
            not any((p/'.git').exists() for p in (out, *out.parents)), 'new absolute output outside Git required')
    require(sys.platform == 'linux' and platform.machine() == 'x86_64', 'fixed Linux x86-64 target required')
    recipe = json.loads((HERE/'recipe.json').read_bytes())
    normal = (HERE/recipe['normal_entry']).resolve()
    require(recipe['profile'] == {'workers': 2, 'tt_bits': 18, 'ply': 128, 'dev': 0}, 'fixed profile differs')
    require(sha((normal/'recipe.json').read_bytes()) == recipe['normal_recipe_sha256'], 'normal recipe changed')
    original_recipe = json.loads((normal/'recipe.json').read_bytes())
    require(original_recipe['native_flags'] == recipe['native_flags'] and
            original_recipe['profile'] == recipe['profile'] and
            original_recipe['native_units'] == recipe['native_units'], 'fixed native contract differs')
    require(sha((normal/'packer.py').read_bytes()) == recipe['packer_sha256'], 'normal parser/strip helper changed')
    require(sha((HERE/'transform.py').read_bytes()) == recipe['transform_sha256'], 'exact transform changed')
    out.mkdir()
    started, deadline = time.monotonic(), time.monotonic()+120
    report = {'complete': False, 'scope': 'one semantic reset-ownership rewrite; native first cost only, not object-identical spelling compression',
              'profile': recipe['profile'], 'inputs': {}, 'controls': [], 'candidates': [], 'commands': [],
              'native_compile_count': 0, 'control_compile_count': 0, 'compiler_metadata_commands': 0,
              'native_attempts_per_form': 1, 'native_reproduced': False,
              'whole_encoder_target_audit_fresh_negative_runs': 0, 'candidate_admitted_by_normal_guard': False,
              'admission_scope': 'candidate identities are observations only; normal exact guard remains unchanged',
              'cleanup': [], 'limits': {'aggregate_wall_seconds': 120, 'compiler_wall_seconds': 45,
                                       'compiler_CPU_seconds': 30, 'compiler_AS_bytes': 2<<30, 'parallel_compilers': 1}}

    def save():
        (out/'build.json').write_text(json.dumps(report, indent=2)+'\n')

    def cancelled(signum, frame):
        raise TimeoutError('native cost producer cancelled')

    previous_term = signal.signal(signal.SIGTERM, cancelled)

    def run(command):
        child = None
        row = {'command': command}
        report['commands'].append(row)
        report['native_compile_count'] += 1
        save()
        try:
            remaining = min(45, deadline-time.monotonic())
            require(remaining > 0, 'aggregate native deadline')
            mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            def setup():
                resource.setrlimit(resource.RLIMIT_AS, (2<<30, 2<<30))
                resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
                signal.pthread_sigmask(signal.SIG_SETMASK, mask)
            try:
                child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         start_new_session=True, preexec_fn=setup)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, mask)
            stdout, stderr = child.communicate(timeout=remaining)
            row.update(returncode=child.returncode, stdout=stdout.decode(errors='replace'), stderr=stderr.decode(errors='replace'))
            require(child.returncode == 0, 'native compiler failed; original output retained')
            return dict(row)
        except BaseException as error:
            row['failure'] = {'type': type(error).__name__, 'message': str(error)}
            raise
        finally:
            cleanup_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            try:
                if child is not None:
                    cleanup = {'pid': child.pid, 'killpg_sent': False, 'group_absent': False}
                    try:
                        try:
                            os.killpg(child.pid, signal.SIGKILL)
                            cleanup['killpg_sent'] = True
                        except ProcessLookupError:
                            pass
                        if child.poll() is None:
                            child.wait(timeout=3)
                        if 'returncode' not in row:
                            stdout, stderr = child.communicate(timeout=3)
                            row.update(returncode=child.returncode, stdout=stdout.decode(errors='replace'), stderr=stderr.decode(errors='replace'))
                        cleanup['returncode'] = child.returncode
                        try:
                            os.killpg(child.pid, 0)
                        except ProcessLookupError:
                            cleanup['group_absent'] = True
                        require(cleanup['group_absent'], 'owned compiler group did not settle')
                    except BaseException as error:
                        cleanup['failure'] = {'type': type(error).__name__, 'message': str(error)}
                        raise
                    finally:
                        report['cleanup'].append(cleanup)
                        save()
                save()
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, cleanup_mask)

    save()
    try:
        originals = {}
        for name, expected in recipe['native_source8'].items():
            data = (normal/'native'/name).read_bytes()
            require(sha(data) == expected and b'\r' not in data, 'exact original native input differs: '+name)
            originals[name] = data
            report['inputs'][name] = {'path': str(normal/'native'/name), 'bytes': len(data), 'sha256': sha(data)}
        packer = module('worker_reset_fixed_parser', normal/'packer.py')
        transform = module('worker_reset_transform', HERE/'transform.py')
        # Verify both previously qualified native repeats before either new compile.
        for form, control in recipe['controls'].items():
            native = None
            for path in control['native_paths']:
                data = Path(path).read_bytes()
                require(len(data) == control['bytes'] and sha(data) == control['sha256'], 'old native identity differs')
                require(native is None or data == native, 'old repeat bytes differ')
                native = data
            linked = Path(control['linked_path']).read_bytes()
            require(sha(linked) == control['linked_sha256'] and packer.strip_native(linked) == native, 'old linked/native binding differs')
            report['controls'].append({'form': form, **control, 'verified_actual_old_files': True,
                                       'ELF': packer.elf(native), 'geometry': geometry(packer.elf(native)), 'sections': sections(linked)})
        candidate = dict(originals)
        candidate['runtime.c'] = transform.transform(originals['runtime.c'])
        source = out/'candidate-source8'
        source.mkdir()
        mapping = {}
        for name, data in candidate.items():
            (source/name).write_bytes(data)
            mapping[name] = {'bytes': len(data), 'sha256': sha(data)}
        report['candidate_source8'] = mapping
        report['candidate_source8_set_sha256'] = sha(json.dumps(mapping, sort_keys=True, separators=(',', ':')).encode())
        report['only_runtime_changed'] = [n for n in candidate if candidate[n] != originals[n]] == ['runtime.c']
        require(report['only_runtime_changed'], 'unexpected source change')
        for form, control in recipe['controls'].items():
            directory = out/form
            directory.mkdir()
            command = ['cc', *recipe['native_flags'], f"-DD_HQ={control['hq']}", '-DDEV=0',
                       *[str(source/n) for n in recipe['native_units']], '-Wl,-T,'+str(source/'image.ld'), '-o', str(directory/'linked')]
            compiled = run(command)
            linked = (directory/'linked').read_bytes()
            native = packer.strip_native(linked)
            (directory/'x').write_bytes(native)
            (directory/'x').chmod(0o755)
            parsed, allocated = packer.elf(native), sections(linked)
            baseline = next(c for c in report['controls'] if c['form'] == form)
            text = next(s['bytes'] for s in allocated if s['name'] == '.text')
            oldtext = next(s['bytes'] for s in baseline['sections'] if s['name'] == '.text')
            report['candidates'].append({'form': form, 'path': str(directory/'x'), 'bytes': len(native), 'sha256': sha(native),
                'native_byte_change': len(native)-control['bytes'], 'text_bytes': text, 'text_byte_change': text-oldtext,
                'linked_bytes': len(linked), 'linked_sha256': sha(linked), 'ELF': parsed, 'geometry': geometry(parsed),
                'sections': allocated, 'compile': compiled, 'candidate_only_not_normal_admission': True})
            save()
        require(report['native_compile_count'] == 2, 'unexpected compiler count')
        for name, original in originals.items():
            require((normal/'native'/name).read_bytes() == original, 'maintained source changed during build')
        report['complete'] = True
    except BaseException as error:
        report['complete'] = False
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        final_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        try:
            report['elapsed_seconds'] = time.monotonic()-started
            save()
        finally:
            signal.signal(signal.SIGTERM, previous_term)
            signal.pthread_sigmask(signal.SIG_SETMASK, final_mask)
    print(json.dumps({'complete': True, 'native_compiles': 2, 'candidate_source8_set_sha256': report['candidate_source8_set_sha256'],
                      'candidates': [{k:c[k] for k in ('form', 'bytes', 'sha256', 'native_byte_change', 'text_byte_change')} for c in report['candidates']]}))


if __name__ == '__main__':
    main()
