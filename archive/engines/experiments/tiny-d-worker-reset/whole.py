#!/usr/bin/env python3
"""One fixed-context encode/loader build per literal worker-reset native; no targets."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import resource
import signal
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


# Separate candidate-only cost admission. Normal packer.admit is not called or edited.
ADMITTED = {
    'scalar-shipping': (8060, '381fd1f478b090372365371d39337920c11fee4ab04ed59ab8616d0286b125d1',
                        0x401dfe, 0x2000, 0x402000, 0x42d000, 0x2f000),
    'hq-shipping': (8448, '215ee72678b41032e7f3283bf40fda752f385833df46d2b430bfc2d5c5f89008',
                    0x401f30, 0x3000, 0x403000, 0x42e000, 0x30000),
}


def admit(native, form, parser):
    size, digest, entry, pages, bss, upper, reserve = ADMITTED[form]
    require((len(native), sha(native)) == (size, digest), 'unknown worker-reset native identity')
    def segment(kind, flags, address, filesz, memsz, align):
        return dict(type=kind, flags=flags, offset=0, vaddr=address, paddr=address,
                    filesz=filesz, memsz=memsz, align=align)
    expected = dict(entry=entry, section_offset=0, section_size=0, section_count=0, section_names=0,
                    segments=[segment(1, 5, 0x400000, size, size, 4096),
                              segment(1, 6, bss, 0, 175092, 4096),
                              segment(0x6474e551, 6, 0, 0, 0, 8)])
    require(parser.elf(native) == expected, 'literal candidate ELF header/PHDR class differs')
    return {**expected, 'image_base': 0x400000, 'image_size': size, 'image_pages': pages,
            'bss_base': bss, 'bss_size': 175092, 'bss_pages': 176128, 'guard_base': 0x3ff000,
            'upper_guard': upper, 'reserve_size': reserve}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--out', type=Path, required=True)
    args = cli.parse_args()
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and
            not any((p/'.git').exists() for p in (out, *out.parents)), 'new absolute output outside Git required')
    require(sys.platform == 'linux' and platform.machine() == 'x86_64', 'fixed target required')
    recipe = json.loads((HERE/'whole-recipe.json').read_bytes())
    normal = (HERE/recipe['normal_entry']).resolve()
    require(sha((HERE/'build.py').read_bytes()) == recipe['build_helper_sha256'], 'reviewed section helper differs')
    require(sha((normal/'recipe.json').read_bytes()) == recipe['normal_recipe_sha256'], 'fixed normal recipe differs')
    fixed = json.loads((normal/'recipe.json').read_bytes())
    require(recipe['loader_flags'] == fixed['loader_flags'] and recipe['codec'] == fixed['codec'] == 'rove4k-context-h24-base10-u32-zero4-v1', 'fixed codec/flags differ')
    require(recipe['loader_source_sha256'] == fixed['loader_source_sha256'], 'fixed loader source declaration differs')
    require(sha((normal/'packer.py').read_bytes()) == recipe['packer_sha256'], 'normal parser/loader helper differs')
    for name, digest in recipe['loader_source_sha256'].items():
        require(sha((normal/name).read_bytes()) == digest, 'fixed loader/encoder source differs: '+name)
    out.mkdir()
    started, deadline = time.monotonic(), time.monotonic()+120
    report = {'complete': False, 'scope': 'one whole first-cost candidate per form; native reused, fixed own encoder/decoder, no target execution',
              'commands': [], 'cleanup': [], 'encodes': 0, 'loader_compile_count': 0, 'native_compile_count': 0,
              'control_compile_or_copy': 0, 'target_audit_fresh_negative': 0, 'whole_reproduced': False,
              'candidate_only_admission': 'two exact full hashes and literal ELF/geometry; normal exact guard unchanged',
              'inputs': {'normal_recipe_sha256': recipe['normal_recipe_sha256'], 'loader_sources': recipe['loader_source_sha256'],
                         'build_helper_sha256': recipe['build_helper_sha256'], 'packer_sha256': recipe['packer_sha256']},
              'limits': {'aggregate_wall_seconds': 120, 'compiler_wall_seconds': 45, 'compiler_CPU_seconds': 30,
                         'compiler_AS_bytes': 2<<30, 'parallel_compilers': 1}, 'candidates': []}
    def save():
        (out/'whole.json').write_text(json.dumps(report, indent=2)+'\n')
    def cancelled(signum, frame):
        raise TimeoutError('whole cost producer cancelled')
    previous_term = signal.signal(signal.SIGTERM, cancelled)

    def run(command):
        child = None
        row = {'command': command}
        report['commands'].append(row)
        report['loader_compile_count'] += 1
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
        helper = module('worker_reset_cost_sections', HERE/'build.py')
        packer = module('worker_reset_whole_packer', normal/'packer.py')
        # All six loader/model/helper pins were checked before codec imports its sibling.
        codec = module('worker_reset_fixed_encoder', normal/'loader/codec.py')
        source = Path(recipe['candidate_source8_root'])
        observed = {}
        for name, pin in recipe['candidate_source8'].items():
            data = (source/name).read_bytes()
            require((len(data), sha(data)) == (pin['bytes'], pin['sha256']), 'fixed candidate source8 differs')
            observed[name] = {'bytes': len(data), 'sha256': sha(data)}
        require(sha(json.dumps(observed, sort_keys=True, separators=(',', ':')).encode()) == recipe['candidate_source8_set_sha256'], 'candidate source8 set differs')
        report['candidate_source8_set_sha256'] = recipe['candidate_source8_set_sha256']
        for form in ADMITTED:
            native = Path(recipe['native_paths'][form]).read_bytes()
            layout = admit(native, form, packer)
            model = codec.load_models((normal/'loader/models.json').read_bytes(), form)
            payload, encoding = codec.encode_native(native, model)
            report['encodes'] += 1
            row = {'form': form, 'native_path': recipe['native_paths'][form], 'native_bytes': len(native),
                   'native_sha256': sha(native), 'layout': layout, 'encoding': encoding,
                   'baseline_whole_bytes': fixed['expected'][form]['whole_bytes'],
                   'baseline_whole_sha256': fixed['expected'][form]['whole_sha256']}
            report['candidates'].append(row)
            save()
            complete = packer.compile_loader(out/form, normal/'loader', payload, layout, recipe['loader_flags'], run, sha, checkpoint=False)
            require(complete['definitions']['CHECKPOINT'] == 0, 'audit compile forbidden')
            complete['ELF'] = packer.elf(Path(complete['path']).read_bytes())
            complete['sections'] = helper.sections((out/form/'linked').read_bytes())
            row.update(whole=complete, whole_byte_change=complete['bytes']-row['baseline_whole_bytes'],
                       packet_byte_change=len(payload)-fixed['expected'][form]['payload_bytes'])
            save()
        require(report['encodes'] == report['loader_compile_count'] == 2, 'unexpected cost commands')
        for name, digest in recipe['loader_source_sha256'].items():
            require(sha((normal/name).read_bytes()) == digest, 'normal input changed during cost stage')
        require(sha((normal/'recipe.json').read_bytes()) == recipe['normal_recipe_sha256'] and
                sha((normal/'packer.py').read_bytes()) == recipe['packer_sha256'], 'normal helper/recipe changed')
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
    print(json.dumps({'complete': True, 'encodes': 2, 'loader_compiles': 2,
                      'candidates': [{'form': r['form'], 'whole_bytes': r['whole']['bytes'], 'whole_sha256': r['whole']['sha256'],
                                      'packet_bytes': r['encoding']['payload_bytes'], 'whole_change': r['whole_byte_change']} for r in report['candidates']]}))


if __name__ == '__main__':
    main()
