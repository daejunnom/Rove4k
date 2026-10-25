#!/usr/bin/env python3
"""One literal completion-latch native first cost. No packaging or execution."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PINS_SHA = 'a70fa1b43e1ab224e4713b809787cba8cae448c387013411baa7363278dc1b61'
TRANSFORM_SHA = '76e1226817618405753a643a21867df1c34a9a733bfcf636b60bdd5855bfebcf'
CONTROL_RUNTIME_SHA = '82c62b57e500918827721553d67d9e23073c6cb5ca79dc22cdb8e38ab15f8e63'
CANDIDATE_RUNTIME_SHA = '5b20d4e60d60b5edfb4b7b5a15217346098f0bd9ccdd155a7369c90743e81ed1'
MASKED_COMPLEMENT_SHA = 'c1e5eed8c6241337ca0a4e823b8fc9debf11a4cc047cf0f691240ba077c55089'
CONTROLS = {
    'scalar-shipping': (0, 8124, '199da6e1e1a94c97fe853e0ff3d89b52e2057a55592052e7fbe5500147e4aeec'),
    'hq-shipping': (1, 8512, '3f4269dc5c0d72c0b43bc73c6a11afdab5844836e12e7c31d60dde08c8ae2806'),
}
NATIVE = ('tiny.h', 'board.c', 'search.c', 'runtime.c', 'hq.h', 'hq.c', 'start.S', 'image.ld')
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


def sections(raw):
    need(len(raw) >= 64, 'linked ELF header absent')
    offset = struct.unpack_from('<Q', raw, 40)[0]
    width, count, strings = struct.unpack_from('<HHH', raw, 58)
    need(width == 64 and count and strings < count and offset + width * count <= len(raw), 'linked section table invalid')
    rows = [struct.unpack_from('<IIQQQQIIQQ', raw, offset + width * i) for i in range(count)]
    names_row = rows[strings]
    need(names_row[1] == 3 and names_row[4] + names_row[5] <= len(raw), 'section-name string table invalid')
    names, result = raw[names_row[4]:names_row[4] + names_row[5]], []
    for row in rows:
        need(row[0] < len(names), 'section name offset invalid')
        end = names.find(b'\0', row[0])
        need(end >= 0 and (row[1] == 8 or row[4] + row[5] <= len(raw)), 'section name/file extent invalid')
        result.append({'name': names[row[0]:end].decode('ascii'), 'type': row[1], 'flags': row[2],
                       'address': row[3], 'offset': row[4], 'bytes': row[5], 'alignment': row[8]})
    return result


def observed_elf(raw):
    """Record raw headers before enforcing the experiment's ELF shape."""
    result = {'header_hex': raw[:64].hex()}
    try:
        entry, offset = struct.unpack_from('<QQ', raw, 24)
        width, count = struct.unpack_from('<HH', raw, 54)
        result.update(entry=entry, program_header_offset=offset, program_header_size=width,
                      program_header_count=count, program_headers_hex=raw[offset:offset + width * count].hex())
        if width == 56 and offset + width * count <= len(raw):
            result['segments'] = [dict(zip(('type', 'flags', 'offset', 'vaddr', 'paddr', 'filesz', 'memsz', 'align'),
                struct.unpack_from('<IIQQQQQQ', raw, offset + width * i))) for i in range(count)]
    except (struct.error, OverflowError) as error:
        result['observation_error'] = str(error)
    return result


def geometry(native, section_rows, packer, expected, candidate):
    parsed = packer.elf(native)
    segments = parsed['segments']
    need(len(segments) == 3 and [s['type'] for s in segments] == [1, 1, 0x6474e551], 'exact RX/BSS/nonexec-stack segment set required')
    rx, bss, stack = segments
    need(not any((s['flags'] & 3) == 3 for s in segments), 'writable executable segment')
    need(rx['flags'] == 5 and rx['offset'] == 0 and rx['vaddr'] == rx['paddr'] == 0x400000 and rx['align'] == 4096, 'RX shape differs')
    need(rx['filesz'] == rx['memsz'] == len(native), 'RX file/memory extent differs')
    pages = (len(native) + 4095) // 4096 * 4096
    need(bss['flags'] == 6 and bss['offset'] == bss['filesz'] == 0 and bss['memsz'] > 0 and bss['align'] == 4096, 'zero-file-backed BSS shape differs')
    need(bss['vaddr'] == bss['paddr'] == rx['vaddr'] + pages, 'BSS base not derived from actual RX pages')
    need(stack == expected['layout']['segments'][2] and stack['flags'] == 6, 'non-executable stack differs')
    need(all(parsed[k] == 0 for k in ('section_offset', 'section_size', 'section_count', 'section_names')), 'stripped section metadata remains')
    need(rx['vaddr'] + 64 + 3 * 56 <= parsed['entry'] < rx['vaddr'] + len(native), 'entry outside file-backed RX')
    need(sum(s['bytes'] for s in section_rows if s['name'] == '.data') == 0, 'nonzero .data forbidden')
    need(not any(s['bytes'] and (s['flags'] & 3) == 3 and s['type'] != 8 for s in section_rows), 'file-backed writable allocated section forbidden')
    bss_rows = [s for s in section_rows if s['name'] == '.bss']
    need(len(bss_rows) == 1 and bss_rows[0]['type'] == 8 and bss_rows[0]['flags'] == 3 and
         bss_rows[0]['address'] == bss['vaddr'] and bss_rows[0]['bytes'] == bss['memsz'], 'BSS must be exactly matching NOBITS storage')
    for s in section_rows:
        if s['bytes'] and (s['flags'] & 2) and s['type'] != 8:
            need(rx['vaddr'] <= s['address'] and s['address'] + s['bytes'] <= rx['vaddr'] + len(native), 'allocated file section outside RX')
    bss_pages = (bss['memsz'] + 4095) // 4096 * 4096
    layout = dict(parsed, image_base=rx['vaddr'], image_size=len(native), image_pages=pages,
                  bss_base=bss['vaddr'], bss_size=bss['memsz'], bss_pages=bss_pages,
                  guard_base=rx['vaddr'] - 4096, upper_guard=bss['vaddr'] + bss_pages,
                  reserve_size=pages + bss_pages + 8192)
    rejection = None
    if candidate:
        try:
            packer.admit(native, expected, sha)
        except (ValueError, AssertionError) as error:
            rejection = str(error)
        else:
            raise AssertionError('unchanged old admission unexpectedly accepted candidate')
    else:
        need(packer.admit(native, expected, sha) == layout, 'literal old control admission/layout differs')
    page_keys = ('image_base', 'image_pages', 'bss_base', 'bss_pages', 'guard_base', 'upper_guard', 'reserve_size')
    return {'actual_layout': layout, 'same_page_geometry': all(layout[k] == expected['layout'][k] for k in page_keys),
            'same_BSS_memsz': bss['memsz'] == expected['layout']['bss_size'],
            'BSS_memsz_change': bss['memsz'] - expected['layout']['bss_size'],
            'current_exact_admission_accepts': not candidate, 'current_admission_rejection': rejection,
            'BSS_zero_contract': 'SHT_NOBITS and PT_LOAD filesz0 only; memory initialization not executed',
            'no_interpreter_WX_or_executable_stack': True,
            'root_review_required_before_packaging': candidate}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    need(args.out.is_absolute() and not out.exists() and not any((p / '.git').exists() for p in (out, *out.parents)), 'new absolute external output required')
    need(sys.platform == 'linux' and platform.machine() == 'x86_64', 'fixed Linux x86-64 target required')
    out.mkdir(parents=True)
    started, deadline, phase = time.monotonic(), time.monotonic() + 180, 'freeze'
    report = {'complete': False, 'scope': 'one literal pending-latch native first cost under unchanged original recipe; no restoration/engine execution',
              'inputs': {}, 'controls': [], 'candidates': [], 'failures': [], 'cleanup': [], 'commands': [],
              'candidate_packaged': False, 'candidate_executed': False, 'candidate_qualified': False,
              'automatic_expected_update': False, 'loader_compiled': False, 'codec_called': False,
              'additional_map_or_code_flags': False}

    def cancelled(signum, frame):
        raise TimeoutError('completion-latch producer SIGTERM')

    previous_term = signal.signal(signal.SIGTERM, cancelled)

    def run(command, directory, kind):
        process, stdout, stderr, problem = None, b'', b'', None
        record = {'command': command, 'cwd': str(directory), 'kind': kind}
        report['commands'].append(record)
        begin = time.monotonic()
        try:
            need(deadline > time.monotonic(), 'aggregate native-cost deadline')
            inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            try:
                process = subprocess.Popen(command, cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                                           preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, inherited))
                RUNNING.add(process)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
            remaining = min(45, deadline - time.monotonic())
            need(remaining > 0, 'aggregate native-cost deadline')
            stdout, stderr = process.communicate(timeout=remaining)
            need(process.returncode == 0, kind + ' command failed')
        except BaseException as error:
            problem = error
            record['failure'] = {'type': type(error).__name__, 'detail': str(error)}
        finally:
            inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            try:
                record['cleanup_errors'] = []
                if process is not None:
                    try:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                            record['forced_cleanup'] = True
                        except ProcessLookupError:
                            record['forced_cleanup'] = False
                        stdout, stderr = process.communicate(timeout=3)
                        record['returncode'] = process.returncode
                        RUNNING.discard(process)
                    except BaseException as error:
                        record['cleanup_errors'].append({'type': type(error).__name__, 'detail': str(error)})
                record.update(elapsed_seconds=time.monotonic() - begin, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr))
                (directory / 'command.stdout').write_bytes(stdout)
                (directory / 'command.stderr').write_bytes(stderr)
                (directory / 'command.json').write_text(json.dumps(record, indent=2) + '\n')
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
        if problem is not None:
            raise problem
        need(not record['cleanup_errors'] and not record.get('forced_cleanup'), 'command required forced/incomplete cleanup')
        return record

    try:
        pins_raw = (HERE / 'pins.json').read_bytes()
        need(sha(pins_raw) == PINS_SHA, 'exact control18 manifest required')
        pins = json.loads(pins_raw)
        need(len(pins['entry']) == 18 and pins['runtime_control_sha256'] == CONTROL_RUNTIME_SHA, 'fixed control18/runtime required')
        admitted = {}
        for name, expected in pins['entry'].items():
            need(not Path(name).is_absolute() and '..' not in Path(name).parts, 'entry path outside fixed source closure')
            data = (HERE / 'inputs/entry' / name).read_bytes()
            need(len(data) == expected['bytes'] and sha(data) == expected['sha256'] and b'\r' not in data, 'raw LF entry pin differs: ' + name)
            admitted['inputs/entry/' + name] = data
        # Every ordinary entry is checked before importing the two frozen helpers.
        names = ['.gitattributes', 'README.md', 'build.py', 'pins.json', 'transform.py'] + list(admitted)
        need(len(names) == len(set(names)) == 23, 'exact23 source closure required')
        frozen = out / 'recipe'
        for name in names:
            raw = admitted[name] if name in admitted else pins_raw if name == 'pins.json' else (HERE / name).read_bytes()
            data = raw.replace(b'\r\n', b'\n')
            need(b'\r' not in data, 'lone CR in own source')
            if name == 'transform.py':
                need(sha(data) == TRANSFORM_SHA, 'single approved transform differs')
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            report['inputs'][name] = {'bytes': len(data), 'sha256': sha(data), 'working_bytes_sha256': sha(raw), 'LF_normalization': raw != data}
        entry = frozen / 'inputs/entry'
        recipe = json.loads((entry / 'recipe.json').read_bytes())
        need(recipe['profile'] == {'workers': 2, 'tt_bits': 18, 'ply': 128, 'dev': 0}, 'fixed profile differs')
        need(list(recipe['expected']) == list(CONTROLS), 'two literal forms/order required')
        need(recipe['native_units'] == ['board.c', 'search.c', 'runtime.c', 'hq.c', 'start.S'], 'original unit order differs')
        for form, literal in CONTROLS.items():
            expected = recipe['expected'][form]
            need((expected['hq'], expected['native_bytes'], expected['native_sha256']) == literal, 'literal old native control differs')
        packer = load('latch_frozen_packer', entry / 'packer.py')
        transform = load('latch_frozen_transform', frozen / 'transform.py')
        source = (entry / 'native/runtime.c').read_bytes()
        need(sha(source) == CONTROL_RUNTIME_SHA, 'control runtime differs')
        candidate, proof = transform.apply(source)
        repeat, repeat_proof = transform.apply(source)
        need(candidate == repeat and proof == repeat_proof and len(candidate) == 15123 and sha(candidate) == CANDIDATE_RUNTIME_SHA, 'independent literal candidate generations differ')
        need(proof['inverse_complement_exact'] and proof['masked_complement_sha256'] == MASKED_COMPLEMENT_SHA and proof['candidate_variants'] == 1, 'runtime complement/one-variant proof differs')
        report.update(source_generation_reproduced=True, source_cost=proof, resources=recipe['profile'],
                      native_flags=recipe['native_flags'], native_units=recipe['native_units'], shipping_protocol=recipe['shipping_protocol'],
                      all_other_seven_native_sources_exact=True, candidate_source_sha256={})
        candidate_roots = []
        for attempt, runtime in (('first', candidate), ('repeat', repeat)):
            directory = out / ('candidate-source-' + attempt)
            directory.mkdir()
            identities = {}
            for name in NATIVE:
                data = runtime if name == 'runtime.c' else (entry / 'native' / name).read_bytes()
                if name != 'runtime.c':
                    need(sha(data) == recipe['native_source_sha256']['native/' + name], 'non-runtime native source differs')
                (directory / name).write_bytes(data)
                identities[name] = sha(data)
            report['candidate_source_sha256'][attempt] = identities
            candidate_roots.append(directory)
        need(report['candidate_source_sha256']['first'] == report['candidate_source_sha256']['repeat'], 'candidate source roots differ')
        phase = 'tool metadata'
        report['tools'] = {'python': sys.version, 'platform': platform.platform()}
        for tool in ('cc', 'ld'):
            directory = out / ('metadata-' + tool)
            directory.mkdir()
            run([tool, '--version'], directory, 'metadata')
            report['tools'][tool] = (directory / 'command.stdout').read_text()

        def compile_form(form, expected, is_candidate):
            row = {'id': form, 'candidate': is_candidate, 'native_repeats': []}
            (report['candidates'] if is_candidate else report['controls']).append(row)
            images, linked_images = [], []
            for index, attempt in enumerate(('first', 'repeat')):
                source_root = candidate_roots[index] if is_candidate else entry / 'native'
                directory = out / ('candidate' if is_candidate else 'control') / form / attempt
                directory.mkdir(parents=True)
                command = ['cc', *recipe['native_flags'], '-DD_HQ=' + str(expected['hq']), '-DDEV=0',
                           *[str(source_root / name) for name in recipe['native_units']], '-Wl,-T,' + str(source_root / 'image.ld'),
                           '-o', str(directory / 'linked')]
                compiled = run(command, directory, 'native-compile')
                linked = (directory / 'linked').read_bytes()
                # Preserve observed cost/headers before any shape or old-image
                # admission assertion. Unexpected .data or geometry is a failure
                # with actual bytes and metadata retained, never a repaired cost.
                result = {'compile': compiled, 'linked_path': str(directory / 'linked'),
                          'linked_bytes': len(linked), 'linked_sha256': sha(linked), 'linked_ELF_observed': observed_elf(linked)}
                row['native_repeats'].append(result)
                section_rows = sections(linked)
                section_cost = {name: sum(s['bytes'] for s in section_rows if s['name'] == name) for name in ('.text', '.rodata', '.data', '.bss')}
                result.update(section_table=section_rows, section_cost=section_cost)
                native = packer.strip_native(linked)
                path = directory / 'x'
                path.write_bytes(native)
                path.chmod(0o755)
                result.update(path=str(path), bytes=len(native), sha256=sha(native), native_ELF_observed=observed_elf(native))
                result['geometry'] = geometry(native, section_rows, packer, expected, is_candidate)
                images.append(native)
                linked_images.append(linked)
            need(images[0] == images[1], 'independent full native repeat bytes differ')
            row.update(native_reproduced=True, native_bytes=len(images[0]), native_sha256=sha(images[0]),
                       linked_bytes_equal=linked_images[0] == linked_images[1])
            return row

        # Four exact old native controls precede every candidate compilation.
        for form, expected in recipe['expected'].items():
            phase = form + '/control'
            compile_form(form, expected, False)
        report['both_literal_controls_reproduced_before_candidate'] = True
        for form, expected in recipe['expected'].items():
            phase = form + '/candidate'
            row = compile_form(form, expected, True)
            control = next(r for r in report['controls'] if r['id'] == form)
            row['native_byte_change'] = row['native_bytes'] - control['native_bytes']
            row['section_changes'] = {k: row['native_repeats'][0]['section_cost'][k] - control['native_repeats'][0]['section_cost'][k] for k in ('.text', '.rodata', '.data', '.bss')}
            row['cost_outcome'] = 'smaller' if row['native_byte_change'] < 0 else 'larger' if row['native_byte_change'] > 0 else 'tie'
        need(sum(r['kind'] == 'native-compile' for r in report['commands']) == 8, 'exactly eight native compile commands required')
        report['native_compile_count'] = 8
        report['all_candidate_page_geometries_unchanged'] = all(r['native_repeats'][0]['geometry']['same_page_geometry'] for r in report['candidates'])
        report['both_native_files_strictly_smaller'] = all(r['native_byte_change'] < 0 for r in report['candidates'])
        report['stop_after_native_first_cost'] = True
        report['complete'] = True
    except BaseException as error:
        report['complete'] = False
        report['failures'].append({'phase': phase, 'type': type(error).__name__, 'detail': str(error)})
    finally:
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        try:
            for process in list(RUNNING):
                try:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.communicate(timeout=3)
                    report['cleanup'].append({'pid': process.pid, 'returncode': process.returncode})
                except BaseException as error:
                    report['failures'].append({'phase': 'registered-cleanup', 'type': type(error).__name__, 'detail': str(error)})
                report['complete'] = False
            report['elapsed_seconds'] = time.monotonic() - started
            (out / 'build.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        finally:
            signal.signal(signal.SIGTERM, previous_term)
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
    print(json.dumps({'complete': report['complete'], 'out': str(out), 'failures': report['failures'],
                      'candidate_costs': [{'id': r['id'], 'bytes': r.get('native_bytes'), 'change': r.get('native_byte_change')} for r in report['candidates']]}))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
