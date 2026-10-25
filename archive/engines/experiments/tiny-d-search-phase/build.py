#!/usr/bin/env python3
"""One fixed D-native phase first-cost experiment. Never packs or runs engines."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import signal
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RUNNING = set()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(value, detail):
    if not value:
        raise AssertionError(detail)


def lf(path):
    raw = path.read_bytes()
    normalized = raw.replace(b'\r\n', b'\n')
    need(b'\r' not in normalized, 'lone CR: ' + str(path))
    return raw, normalized


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def sections(raw):
    offset = struct.unpack_from('<Q', raw, 40)[0]
    width, count, strings = struct.unpack_from('<HHH', raw, 58)
    need(width == 64 and count and strings < count and offset + width * count <= len(raw), 'linked section metadata absent/invalid')
    rows = [struct.unpack_from('<IIQQQQIIQQ', raw, offset + width * i) for i in range(count)]
    names = raw[rows[strings][4]:rows[strings][4] + rows[strings][5]]
    result = []
    for row in rows:
        end = names.index(b'\0', row[0])
        result.append({'name': names[row[0]:end].decode(), 'type': row[1], 'flags': row[2], 'address': row[3], 'offset': row[4], 'bytes': row[5]})
    return result


def map_sections(path):
    text = path.read_text()
    pattern = r'^[ \t]+(\.text(?:\.[^\s]+)?)[ \t]*(?:\n[ \t]*)?(0x[0-9a-f]+)[ \t]+(0x[0-9a-f]+)'
    rows = [{'section': name, 'address': int(address, 16), 'bytes': int(size, 16)} for name, address, size in re.findall(pattern, text, re.M)]
    return {'path': str(path), 'sha256': sha(path.read_bytes()),
            'text_input_sections_partial': [r for r in rows if r['address'] >= 0x400000 and r['bytes']],
            'search_named_lines_partial': [s.strip() for s in text.splitlines() if 'search' in s and ('0x' in s or '.text.' in s)],
            'scope': 'partial linker map under unchanged LTO/-s; not all source functions remain symbols; no sum of overlapping sections claimed'}


def candidate_layout(native, packer, expected):
    parsed = packer.elf(native)
    segments = parsed['segments']
    need(len(segments) == 3 and [s['type'] for s in segments] == [1, 1, 0x6474e551], 'segment set changed')
    rx, bss, stack = segments
    old = expected['layout']
    need(all(rx[k] == old['segments'][0][k] for k in rx if k not in ('filesz', 'memsz')), 'RX contract changed')
    need(rx['filesz'] == rx['memsz'] == len(native), 'RX extent differs from native file')
    need(all(bss[k] == old['segments'][1][k] for k in bss if k not in ('vaddr', 'paddr')), 'BSS shape changed')
    pages = (len(native) + 4095) // 4096 * 4096
    need(bss['vaddr'] == bss['paddr'] == rx['vaddr'] + pages and stack == old['segments'][2], 'BSS alignment/nonexec stack changed')
    need(all(parsed[k] == 0 for k in ('section_offset', 'section_size', 'section_count', 'section_names')), 'stripped section metadata changed')
    need(rx['vaddr'] + 64 + 3 * 56 <= parsed['entry'] < rx['vaddr'] + len(native), 'entry outside file-backed RX')
    same = pages == old['image_pages'] and bss['vaddr'] == old['bss_base']
    try:
        packer.admit(native, expected, sha)
    except (ValueError, AssertionError) as error:
        rejection = str(error)
    else:
        need(len(native) == expected['native_bytes'] and sha(native) == expected['native_sha256'], 'admission accepted a changed image')
        rejection = None
    return {'entry': parsed['entry'], 'segments': segments, 'image_base': rx['vaddr'], 'image_bytes': len(native),
            'image_pages': pages, 'bss_base': bss['vaddr'], 'bss_size': bss['memsz'], 'bss_pages': old['bss_pages'],
            'same_mapping_class': same, 'current_exact_admission_accepts': rejection is None, 'current_admission_rejection': rejection,
            'fixed_three_page_contract_matches': pages == 12288 and bss['vaddr'] == 0x403000,
            'root_review_required_before_packaging': not same}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    need(args.out.is_absolute() and not out.exists() and not any((p / '.git').exists() for p in (out, *out.parents)), 'new absolute external output required')
    need(sys.platform == 'linux' and platform.machine() == 'x86_64', 'fixed Linux x86-64 target required')
    out.mkdir(parents=True)
    started, deadline, phase = time.monotonic(), time.monotonic() + 180, 'freeze'
    report = {'complete': False, 'scope': 'one existing PVS phase expression re-evaluated only for D raw native cost; no engine execution or restoration',
              'inputs': {}, 'controls': [], 'candidates': [], 'failures': [], 'cleanup': [],
              'candidate_packaged': False, 'candidate_executed': False, 'candidate_qualified': False,
              'historical_A': 'same template deterministic parity passed; source wrapper +16B; no D saving is inherited'}

    def cancelled(signum, frame):
        raise TimeoutError('phase producer SIGTERM')

    prior_term = signal.signal(signal.SIGTERM, cancelled)

    def run(command, directory):
        proc = None
        stdout = stderr = b''
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
            need(remaining > 0, 'aggregate native build deadline')
            stdout, stderr = proc.communicate(timeout=remaining)
            record.update(returncode=proc.returncode, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr))
            need(proc.returncode == 0, 'native compile failed: ' + str(directory))
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
            (directory / 'compile.json').write_text(json.dumps(record, indent=2) + '\n')
        return record

    try:
        pins = json.loads(lf(HERE / 'pins.json')[1])
        names = ['.gitattributes', 'README.md', 'build.py', 'pins.json', 'transform.py', 'phase.c.in'] + ['inputs/entry/' + n for n in pins['entry_lf_sha256']]
        need(len(names) == len(set(names)) == 24, 'source set differs')
        frozen = out / 'recipe'
        for name in names:
            raw, data = lf(HERE / name)
            if name.startswith('inputs/entry/'):
                need(sha(data) == pins['entry_lf_sha256'][name[len('inputs/entry/'):]], 'snapshot source pin differs')
            if name == 'phase.c.in':
                need(sha(data) == pins['phase_lf_sha256'], 'phase template pin differs')
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            report['inputs'][name] = {'bytes': len(data), 'sha256': sha(data), 'working_bytes_sha256': sha(raw), 'LF_normalization': raw != data}
        entry = frozen / 'inputs/entry'
        recipe = json.loads((entry / 'recipe.json').read_bytes())
        need(recipe['profile'] == {'workers': 2, 'tt_bits': 18, 'ply': 128, 'dev': 0}, 'profile differs')
        need(list(recipe['expected']) == ['scalar-shipping', 'hq-shipping'], 'forms differ')
        packer = module('phase_fixed_packer', entry / 'packer.py')
        transform = module('phase_fixed_transform', frozen / 'transform.py')
        source = (entry / 'native/search.c').read_bytes()
        phase_body = (frozen / 'phase.c.in').read_bytes()
        first, source_cost = transform.apply(source, phase_body)
        repeat, repeated_cost = transform.apply(source, phase_body)
        need(first == repeat and source_cost == repeated_cost, 'independent candidate source generations differ')
        report.update(source_generation_reproduced=True, source_cost=source_cost, resources=recipe['profile'],
                      native_flags=recipe['native_flags'], native_units=recipe['native_units'], shipping_protocol=recipe['shipping_protocol'],
                      diagnostic_flag='-Wl,-Map=<external> on second repeat only; original flags/order including -s retained',
                      all_other_seven_native_sources_exact=True)
        candidate_roots = []
        report['candidate_source_sha256'] = {}
        for attempt, search in (('first', first), ('repeat', repeat)):
            directory = out / ('candidate-source-' + attempt)
            directory.mkdir()
            for path in (entry / 'native').iterdir():
                (directory / path.name).write_bytes(search if path.name == 'search.c' else path.read_bytes())
            report['candidate_source_sha256'][attempt] = {p.name: sha(p.read_bytes()) for p in directory.iterdir()}
            need(all(digest == recipe['native_source_sha256']['native/' + name] for name, digest in report['candidate_source_sha256'][attempt].items() if name != 'search.c'), 'non-search native source changed')
            candidate_roots.append(directory)
        need(report['candidate_source_sha256']['first'] == report['candidate_source_sha256']['repeat'], 'candidate source sets differ')
        phase = 'tool versions'
        report['tools'] = {'python': sys.version, 'platform': platform.platform()}
        for tool in ('cc', 'ld'):
            directory = out / ('tool-' + tool)
            directory.mkdir()
            run([tool, '--version'], directory)
            report['tools'][tool] = (directory / 'compile.stdout').read_text()

        def compile_form(form, expected, candidate):
            row = {'id': form, 'native_repeats': [], 'candidate': candidate}
            (report['candidates'] if candidate else report['controls']).append(row)
            images = []
            for index, attempt in enumerate(('first', 'repeat')):
                source_root = candidate_roots[index] if candidate else entry / 'native'
                directory = out / ('candidate' if candidate else 'control') / form / attempt
                directory.mkdir(parents=True)
                command = ['cc', *recipe['native_flags'], f"-DD_HQ={expected['hq']}", '-DDEV=0',
                           *[str(source_root / name) for name in recipe['native_units']], '-Wl,-T,' + str(source_root / 'image.ld')]
                if index:
                    command.append('-Wl,-Map=' + str(directory / 'link.map'))
                command += ['-o', str(directory / 'linked')]
                compiled = run(command, directory)
                linked = (directory / 'linked').read_bytes()
                native = packer.strip_native(linked)
                path = directory / 'x'
                path.write_bytes(native)
                path.chmod(0o755)
                section_rows = sections(linked)
                section_cost = {name: next((s['bytes'] for s in section_rows if s['name'] == name), 0) for name in ('.text', '.rodata', '.data', '.bss')}
                layout = candidate_layout(native, packer, expected) if candidate else packer.admit(native, expected, sha)
                result = {'path': str(path), 'bytes': len(native), 'sha256': sha(native), 'compile': compiled, 'section_cost': section_cost,
                          'section_table': section_rows, 'symbol_table_present': any(s['type'] == 2 for s in section_rows), 'layout': layout}
                if index:
                    result['link_map'] = map_sections(directory / 'link.map')
                row['native_repeats'].append(result)
                images.append(native)
            need(images[0] == images[1], 'plain and diagnostic independent native bytes differ')
            row['plain_diagnostic_repeats_identical'] = True
            row['native_bytes'], row['native_sha256'] = len(images[0]), sha(images[0])
            return row

        # Every current literal control is reproduced before any candidate compile.
        for form, expected in recipe['expected'].items():
            phase = form + '/control'
            compile_form(form, expected, False)
        report['both_literal_controls_reproduced_before_candidate'] = True
        for form, expected in recipe['expected'].items():
            phase = form + '/candidate'
            row = compile_form(form, expected, True)
            control = next(r for r in report['controls'] if r['id'] == form)
            row['native_byte_change'] = row['native_bytes'] - control['native_bytes']
            row['section_changes'] = {k: row['native_repeats'][0]['section_cost'][k] - control['native_repeats'][0]['section_cost'][k] for k in control['native_repeats'][0]['section_cost']}
            row['cost_outcome'] = 'smaller' if row['native_byte_change'] < 0 else 'larger' if row['native_byte_change'] > 0 else 'tie'
        report['all_candidate_classes_unchanged'] = all(r['native_repeats'][0]['layout']['same_mapping_class'] for r in report['candidates'])
        report['both_native_files_strictly_smaller'] = all(r['native_byte_change'] < 0 for r in report['candidates'])
        report['stop_after_native_first_cost'] = True
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
                    proc.wait(timeout=3)
                    report['cleanup'].append({'pid': proc.pid, 'returncode': proc.returncode})
                except BaseException as error:
                    report['failures'].append({'phase': 'registered-cleanup', 'type': type(error).__name__, 'detail': str(error)})
                report['complete'] = False
            report['elapsed_seconds'] = time.monotonic() - started
            (out / 'build.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        finally:
            signal.signal(signal.SIGTERM, prior_term)
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
    print(json.dumps({'complete': report['complete'], 'out': str(out), 'failures': report['failures'],
                      'candidate_costs': [{'id': r['id'], 'bytes': r.get('native_bytes'), 'change': r.get('native_byte_change')} for r in report['candidates']]}))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
