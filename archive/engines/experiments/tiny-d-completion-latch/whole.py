#!/usr/bin/env python3
"""One exact whole first cost regenerated from ordinary completion-latch sources.

Only --out is configurable. A frozen local native producer regenerates all
inputs in this run. No historical report/image or mutable sibling is opened.
Old selected whole controls precede both literal new candidates. No checkpoint
or engine executes, and no observed whole identity becomes an expectation.
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
import zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PINS_SHA = 'a70fa1b43e1ab224e4713b809787cba8cae448c387013411baa7363278dc1b61'
NATIVE_PRODUCER_SHA = '0cd79e938853521726f116f9484c7c08685807ac51b76fbabd07c33b5f4fff4a'
TRANSFORM_SHA = '76e1226817618405753a643a21867df1c34a9a733bfcf636b60bdd5855bfebcf'
CANDIDATE_RUNTIME_SHA = '5b20d4e60d60b5edfb4b7b5a15217346098f0bd9ccdd155a7369c90743e81ed1'
CANDIDATES = {
    'scalar-shipping': {'hq': 0, 'native_bytes': 8092, 'native_sha256': '59829299f667cdb6682c5ed4a955fb50b76a5584209caf9e4bddf1c0ee2cd160',
                        'entry': 0x401e28, 'image_pages': 0x2000, 'bss_base': 0x402000, 'reserve_size': 0x2f000, 'upper_guard': 0x42d000},
    'hq-shipping': {'hq': 1, 'native_bytes': 8480, 'native_sha256': 'f1d6558ec5a13e400c2d6df182b01b3236bf1ee1e99f686e47f144a32d222c5c',
                    'entry': 0x401f5a, 'image_pages': 0x3000, 'bss_base': 0x403000, 'reserve_size': 0x30000, 'upper_guard': 0x42e000},
}
CONTROLS = {
    'scalar-shipping': (8124, '199da6e1e1a94c97fe853e0ff3d89b52e2057a55592052e7fbe5500147e4aeec', 7478, 'd4f2ba718c5e9391708c86468416338f78b6134d1f017267c6c34add187381f2'),
    'hq-shipping': (8512, '3f4269dc5c0d72c0b43bc73c6a11afdab5844836e12e7c31d60dde08c8ae2806', 7718, '3bb8a6a97a27a77508848ab9bd388a4802e07f8d8ff0e37b536176423aa7028f'),
}
RUNNING = {}


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


class ExactLatchAdmission:
    """Cost-only override for two full native identities; old admit is untouched."""
    def __init__(self, original):
        self.original = original

    def admit(self, data, form, old_expected):
        selected = CANDIDATES[form]
        size = selected['native_bytes']
        need(len(data) == size and sha(data) == selected['native_sha256'], 'unknown cost-only candidate native')
        need(old_expected['hq'] == selected['hq'], 'literal candidate/form pairing differs')
        layout = {
            'entry': selected['entry'], 'section_offset': 0, 'section_size': 0, 'section_count': 0, 'section_names': 0,
            'segments': [
                {'type': 1, 'flags': 5, 'offset': 0, 'vaddr': 0x400000, 'paddr': 0x400000, 'filesz': size, 'memsz': size, 'align': 4096},
                {'type': 1, 'flags': 6, 'offset': 0, 'vaddr': selected['bss_base'], 'paddr': selected['bss_base'], 'filesz': 0, 'memsz': 175092, 'align': 4096},
                {'type': 0x6474e551, 'flags': 6, 'offset': 0, 'vaddr': 0, 'paddr': 0, 'filesz': 0, 'memsz': 0, 'align': 8},
            ],
            'image_base': 0x400000, 'image_size': size, 'image_pages': selected['image_pages'],
            'bss_base': selected['bss_base'], 'bss_size': 175092, 'bss_pages': 0x2b000, 'guard_base': 0x3ff000,
            'reserve_size': selected['reserve_size'], 'upper_guard': selected['upper_guard'],
        }
        parsed = self.original.elf(data)
        need(parsed == {name: layout[name] for name in parsed}, 'literal full candidate ELF/PHDR differs')
        need(layout['image_pages'] == (size + 4095) // 4096 * 4096 and
             layout['bss_base'] == layout['image_base'] + layout['image_pages'] and
             layout['upper_guard'] == layout['bss_base'] + layout['bss_pages'] and
             layout['reserve_size'] == layout['image_pages'] + layout['bss_pages'] + 8192, 'literal candidate derived geometry differs')
        try:
            self.original.admit(data, old_expected, sha)
        except (ValueError, AssertionError) as error:
            rejection = str(error)
        else:
            raise AssertionError('old unchanged admission unexpectedly accepted candidate')
        return layout, rejection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    need(args.out.is_absolute() and not out.exists() and not any((p / '.git').exists() for p in (out, *out.parents)), 'new absolute external output required')
    need(sys.platform == 'linux' and platform.machine() == 'x86_64', 'fixed Linux x86-64 target required')
    out.mkdir(parents=True)
    started, deadline, phase = time.monotonic(), time.monotonic() + 240, 'freeze'
    report = {'complete': False, 'scope': 'one source-closed fixed whole first cost; regenerate native inputs then old controls first; no engine/checkpoint/fault qualification',
              'inputs': {}, 'commands': [], 'controls': [], 'candidates': [], 'failures': [], 'cleanup': [],
              'historical_report_or_image_input': False, 'native_regenerated_in_this_run': False,
              'candidate_executed': False, 'candidate_qualified': False, 'checkpoint_built': False,
              'automatic_expected_update': False, 'old_packer_source_and_admit_unchanged': True,
              'candidate_effective_completion_fence': 'result output then pending=0 release; main acquire0',
              'cost_only_exact_candidate_admission': CANDIDATES}

    def cancelled(signum, frame):
        raise TimeoutError('completion-latch whole producer SIGTERM')

    previous_term = signal.signal(signal.SIGTERM, cancelled)

    def cleanup(process, kind):
        item = {'forced_cleanup': False, 'errors': []}
        if kind == 'native-producer':
            item['native_descendant_cleanup'] = 'unverified until successful native receipt is checked'
        try:
            if process.poll() is None and kind == 'native-producer':
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    item['cooperative_TERM_sent'] = True
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    item['native_descendant_cleanup'] = 'unproven if forced fallback required'
            try:
                os.killpg(process.pid, signal.SIGKILL)
                item['forced_cleanup'] = True
                if kind == 'native-producer':
                    item['native_descendant_cleanup'] = 'unproven after forced group kill'
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate(timeout=3)
            item['returncode'] = process.returncode
            RUNNING.pop(process, None)
            return item, stdout, stderr
        except BaseException as error:
            item['errors'].append({'type': type(error).__name__, 'detail': str(error)})
            return item, b'', b''

    def run(command, directory, kind, cap):
        process, stdout, stderr, problem = None, b'', b'', None
        record = {'command': command, 'cwd': str(directory), 'kind': kind}
        report['commands'].append(record)
        begin = time.monotonic()
        try:
            need(deadline > time.monotonic(), 'aggregate whole-cost deadline')
            inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            try:
                process = subprocess.Popen(command, cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                                           preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, inherited))
                RUNNING[process] = {'kind': kind, 'directory': str(directory)}
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
            remaining = min(cap, deadline - time.monotonic())
            need(remaining > 0, 'aggregate whole-cost deadline')
            stdout, stderr = process.communicate(timeout=remaining)
            need(process.returncode == 0, kind + ' command failed')
        except BaseException as error:
            problem = error
            record['failure'] = {'type': type(error).__name__, 'detail': str(error)}
        finally:
            inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            try:
                if process is not None:
                    settled, late_stdout, late_stderr = cleanup(process, kind)
                    record['cleanup'] = settled
                    if late_stdout or late_stderr or not (stdout or stderr):
                        stdout, stderr = late_stdout, late_stderr
                record.update(elapsed_seconds=time.monotonic() - begin, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr))
                (directory / 'command.stdout').write_bytes(stdout)
                (directory / 'command.stderr').write_bytes(stderr)
                (directory / 'command.json').write_text(json.dumps(record, indent=2) + '\n')
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
        if problem is not None:
            raise problem
        need(not record['cleanup']['forced_cleanup'] and not record['cleanup']['errors'], 'command cleanup forced/incomplete')
        return record

    try:
        pins_raw = (HERE / 'pins.json').read_bytes()
        need(sha(pins_raw) == PINS_SHA, 'literal control18 manifest differs')
        pins = json.loads(pins_raw)
        need(len(pins['entry']) == 18, 'exactly18 ordinary control inputs required')
        admitted = {}
        for name, expected in pins['entry'].items():
            need(not Path(name).is_absolute() and '..' not in Path(name).parts, 'entry outside fixed closure')
            data = (HERE / 'inputs/entry' / name).read_bytes()
            need(len(data) == expected['bytes'] and sha(data) == expected['sha256'] and b'\r' not in data, 'raw LF entry pin differs: ' + name)
            admitted['inputs/entry/' + name] = data
        names = ['.gitattributes', 'README.md', 'build.py', 'pins.json', 'transform.py', 'whole.py'] + list(admitted)
        need(len(names) == len(set(names)) == 24, 'exact24 producing closure required')
        frozen = out / 'recipe'
        for name in names:
            raw = admitted[name] if name in admitted else pins_raw if name == 'pins.json' else (HERE / name).read_bytes()
            data = raw.replace(b'\r\n', b'\n')
            need(b'\r' not in data, 'lone CR own source')
            if name in ('build.py', 'transform.py'):
                need(sha(data) == {'build.py': NATIVE_PRODUCER_SHA, 'transform.py': TRANSFORM_SHA}[name], 'approved native producer/helper differs')
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            report['inputs'][name] = {'bytes': len(data), 'sha256': sha(data), 'working_bytes_sha256': sha(raw), 'LF_normalization': data != raw}
        entry = frozen / 'inputs/entry'
        recipe = json.loads((entry / 'recipe.json').read_bytes())
        need(recipe['profile'] == {'workers': 2, 'tt_bits': 18, 'ply': 128, 'dev': 0} and list(recipe['expected']) == list(CONTROLS), 'fixed profile/forms differ')
        for form, literal in CONTROLS.items():
            expected = recipe['expected'][form]
            need((expected['native_bytes'], expected['native_sha256'], expected['whole_bytes'], expected['whole_sha256']) == literal, 'literal control native/whole differs')
        report.update(resources=recipe['profile'], native_flags=recipe['native_flags'], native_units=recipe['native_units'],
                      loader_flags=recipe['loader_flags'], shipping_protocol=recipe['shipping_protocol'],
                      zlib_build=zlib.ZLIB_VERSION, zlib_runtime=zlib.ZLIB_RUNTIME_VERSION)
        phase = 'new native regeneration'
        native_out = out / 'native-first'
        command_directory = out / 'native-command'
        command_directory.mkdir()
        report['native_command'] = run([sys.executable, '-I', '-B', str(frozen / 'build.py'), '--out', str(native_out)], command_directory, 'native-producer', 180)
        native_bytes = (native_out / 'build.json').read_bytes()
        native = json.loads(native_bytes)
        need(native['complete'] and not native['failures'] and not native['cleanup'] and native['native_compile_count'] == 8 and
             native['both_literal_controls_reproduced_before_candidate'] and native['source_generation_reproduced'], 'new native-first receipt incomplete')
        need(all(c['returncode'] == 0 and not c['forced_cleanup'] and not c['cleanup_errors'] for c in native['commands']), 'nested native command cleanup differs')
        need(not native['candidate_executed'] and not native['candidate_packaged'] and not native['candidate_qualified'], 'new native-first scope differs')
        need(native['resources'] == recipe['profile'] and native['native_flags'] == recipe['native_flags'] and native['native_units'] == recipe['native_units'], 'new native-first flags/profile/order differs')
        need(set(native['inputs']) == set(report['inputs']) - {'whole.py'} and
             all(native['inputs'][n]['sha256'] == report['inputs'][n]['sha256'] for n in native['inputs']), 'nested producing source23 binding differs')
        need(native['source_cost']['candidate_runtime_sha256'] == CANDIDATE_RUNTIME_SHA and native['all_other_seven_native_sources_exact'], 'new native-first source binding differs')
        need(len(native['controls']) == len(native['candidates']) == 2 and
             {r['id'] for r in native['controls']} == {r['id'] for r in native['candidates']} == set(CANDIDATES), 'exactly two regenerated forms required')
        report.update(native_regenerated_in_this_run=True, native_build={'path': str(native_out / 'build.json'), 'bytes': len(native_bytes), 'sha256': sha(native_bytes),
                      'native_compile_count': 8, 'producing_source23_bound': True, 'commands': native['commands']})
        report['native_command']['native_cleanup_verified_by_successful_receipt'] = True
        report['native_command']['cleanup']['native_descendant_cleanup'] = 'verified by successful pinned native receipt and all clean owned commands'
        packer = load('latch_whole_original_packer', entry / 'packer.py')
        codec = load('latch_whole_original_codec', entry / 'loader/codec.py')
        cost_admission = ExactLatchAdmission(packer)
        natives, layouts = {}, {}
        report['native_intake'] = []
        for group in ('controls', 'candidates'):
            for row in native[group]:
                form = row['id']
                need(row['native_reproduced'] and len(row['native_repeats']) == 2, 'two regenerated native repeats required')
                images = []
                for repeat in row['native_repeats']:
                    path = Path(repeat['path']).resolve()
                    need(native_out in path.parents, 'native input outside this run')
                    data = path.read_bytes()
                    need(len(data) == repeat['bytes'] and sha(data) == repeat['sha256'], 'new native artifact differs from current receipt')
                    need(repeat['section_cost']['.data'] == 0 and repeat['section_cost']['.bss'] == 175092, 'approved native data/BSS cost differs')
                    if group == 'controls':
                        need((len(data), sha(data)) == CONTROLS[form][:2], 'actual literal native control differs')
                        layout, rejection = packer.admit(data, recipe['expected'][form], sha), None
                    else:
                        layout, rejection = cost_admission.admit(data, form, recipe['expected'][form])
                    need(layout == repeat['geometry']['actual_layout'], 'current native ELF/layout receipt differs')
                    images.append({'path': str(path), 'data': data})
                need(images[0]['data'] == images[1]['data'], 'actual regenerated native repeat bytes differ')
                natives[group, form], layouts[group, form] = images, layout
                report['native_intake'].append({'group': group, 'id': form, 'bytes': len(images[0]['data']), 'sha256': sha(images[0]['data']),
                                               'actual_layout': layout, 'native_reproduced': True, 'old_admission_rejection': rejection})

        def pack(group, form, index):
            phase_name = 'fixed' if index == 0 else 'fixed-repeat'
            directory = out / group / form / phase_name
            image = natives[group, form][index]
            payload = codec.fixed_compress(codec.bcj(bytes(image['data'])))
            need(codec.bcj(codec.fixed_decompress(payload, len(image['data'])), inverse=True) == image['data'], 'original codec exact inverse differs')

            def loader_command(command):
                need('-DCHECKPOINT=0UL' in command, 'only original CHECKPOINT0 loader allowed')
                return run(command, directory, 'loader-compile', 45)

            result = packer.compile_loader(directory, entry / 'loader', payload, layouts[group, form], recipe['loader_flags'], loader_command, sha)
            result.update(native_path=image['path'], native_sha256=sha(image['data']), payload_sha256=sha(payload), codec='fixed', checkpoint=False)
            return result

        # All four old complete files must reproduce before any candidate pack.
        for form, expected in recipe['expected'].items():
            phase = form + '/old whole control'
            row = {'id': form, 'whole_repeats': []}
            report['controls'].append(row)
            for index in (0, 1):
                result = pack('controls', form, index)
                row['whole_repeats'].append(result)
                need((result['bytes'], result['sha256'], result['payload_bytes'], result['loader_and_headers_bytes']) ==
                     (expected['whole_bytes'], expected['whole_sha256'], expected['payload_bytes'], expected['loader_and_headers_bytes']), 'old selected whole control differs')
            need(Path(row['whole_repeats'][0]['path']).read_bytes() == Path(row['whole_repeats'][1]['path']).read_bytes(), 'actual old whole repeat bytes differ')
            row['whole_reproduced'] = True
        report['both_control_whole_identities_reproduced_before_candidate'] = True
        for form in CANDIDATES:
            phase = form + '/candidate whole cost'
            row = {'id': form, 'whole_repeats': []}
            report['candidates'].append(row)
            for index in (0, 1):
                result = pack('candidates', form, index)
                row['whole_repeats'].append(result)
                need(result['loader_and_headers_bytes'] == 1115, 'unchanged fixed loader/header overhead differs')
            first, repeat = row['whole_repeats']
            need(Path(first['path']).read_bytes() == Path(repeat['path']).read_bytes(), 'actual candidate whole repeat bytes differ')
            need(first['payload_sha256'] == repeat['payload_sha256'], 'actual candidate codec repeat differs')
            change = first['bytes'] - recipe['expected'][form]['whole_bytes']
            row.update(whole_reproduced=True, whole_bytes=first['bytes'], whole_sha256=first['sha256'], whole_byte_change=change,
                       cost_outcome='smaller' if change < 0 else 'larger' if change > 0 else 'tie')
        need(sum(r['kind'] == 'loader-compile' for r in report['commands']) == 8, 'exactly eight CHECKPOINT0 loader compiles required')
        report['loader_compile_count'] = 8
        report['qualifying_size_profiles'] = [r['id'] for r in report['candidates'] if r['whole_byte_change'] < 0]
        report['complete'] = True
    except BaseException as error:
        report['complete'] = False
        report['failures'].append({'phase': phase, 'type': type(error).__name__, 'detail': str(error)})
    finally:
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        try:
            for process, owned in list(RUNNING.items()):
                try:
                    item, stdout, stderr = cleanup(process, owned['kind'])
                    item.update(pid=process.pid, kind=owned['kind'], stdout_sha256=sha(stdout), stderr_sha256=sha(stderr))
                    report['cleanup'].append(item)
                except BaseException as error:
                    report['failures'].append({'phase': 'registered-cleanup', 'type': type(error).__name__, 'detail': str(error)})
                report['complete'] = False
            report['elapsed_seconds'] = time.monotonic() - started
            (out / 'build.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        finally:
            signal.signal(signal.SIGTERM, previous_term)
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
    print(json.dumps({'complete': report['complete'], 'out': str(out), 'failures': report['failures'],
                      'whole_costs': [{'id': r['id'], 'bytes': r.get('whole_bytes'), 'change': r.get('whole_byte_change')} for r in report['candidates']]}))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
