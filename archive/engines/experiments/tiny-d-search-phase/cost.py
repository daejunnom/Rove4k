#!/usr/bin/env python3
"""Fixed own-ELF first cost for the two explicitly admitted phase natives only."""
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
import zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
NATIVE_REPORT_SHA = '2af7f2aadda128a58f793dc4b4b62e30042195884e9916a3aa357b0372c3a9a1'
BUILD_SHA = '830c097151811d0db8e6525b3741d4ba6362d9f3517b1f366afb1b235e92e34d'
SEARCH_SHA = '48e0f21fee8091f1e5c5d08d606740f6ff8c56778a550af2bcfc282d655d974c'
EXPECTED = {
    'scalar-shipping': {'native_bytes': 8284, 'native_sha256': '875a8263ab335778fc7be58fda2a9975425a5445ffd7300c80c04f5179e2e841', 'entry': 4202204},
    'hq-shipping': {'native_bytes': 8672, 'native_sha256': '4d42ad7e663f826601d01b3f06d778483fc7ba2ec82d80b619967a1fb952061f', 'entry': 4202521},
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
    parser.add_argument('--native-build', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    need(args.out.is_absolute() and not out.exists() and not any((p / '.git').exists() for p in (out, *out.parents)), 'new absolute external output required')
    out.mkdir(parents=True)
    started, deadline, phase = time.monotonic(), time.monotonic() + 120, 'freeze'
    report = {'complete': False, 'scope': 'two literal phase natives packed twice by unchanged admitted3page fixed codec/loader; first whole cost only',
              'controls': [], 'candidates': [], 'failures': [], 'cleanup': [], 'candidate_executed': False,
              'candidate_qualified': False, 'audit_built': False, 'automatic_expected_update': False}

    def cancelled(signum, frame):
        raise TimeoutError('whole-cost producer SIGTERM')

    prior_term = signal.signal(signal.SIGTERM, cancelled)

    def run(command):
        directory = Path(command[-1]).parent
        record, proc, stdout, stderr = {'command': command}, None, b'', b''
        try:
            inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            try:
                proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                                        preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, inherited))
                RUNNING.add(proc)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
            remaining = min(45, deadline - time.monotonic())
            need(remaining > 0, 'aggregate whole-cost deadline')
            stdout, stderr = proc.communicate(timeout=remaining)
            need(proc.returncode == 0, 'loader compilation failed')
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
        native_raw = args.native_build.read_bytes()
        need(sha(native_raw) == NATIVE_REPORT_SHA, 'native checkpoint differs')
        native_report = json.loads(native_raw)
        need(native_report['complete'] and not native_report['failures'] and not native_report['cleanup'], 'native checkpoint incomplete')
        need(native_report['all_candidate_classes_unchanged'] and native_report['source_generation_reproduced'] and native_report['both_literal_controls_reproduced_before_candidate'], 'native class/source/control gate differs')
        need(not native_report['candidate_packaged'] and not native_report['candidate_executed'] and not native_report['candidate_qualified'], 'native checkpoint scope differs')
        need(sha((HERE / 'build.py').read_bytes().replace(b'\r\n', b'\n')) == BUILD_SHA, 'native producer differs')
        pins = json.loads((HERE / 'pins.json').read_bytes())
        need(len(pins['entry_lf_sha256']) == 18, 'snapshot18 required')
        frozen = out / 'recipe'
        names = ['.gitattributes', 'README.md', 'build.py', 'cost.py', 'transform.py', 'phase.c.in', 'pins.json'] + ['inputs/entry/' + n for n in pins['entry_lf_sha256']]
        need(len(names) == len(set(names)) == 25, 'exact source25 required')
        report['inputs'] = {}
        for name in names:
            raw = (HERE / name).read_bytes()
            data = raw.replace(b'\r\n', b'\n')
            need(b'\r' not in data, 'lone CR input')
            if name.startswith('inputs/entry/'):
                need(sha(data) == pins['entry_lf_sha256'][name[len('inputs/entry/'):]], 'entry source pin differs')
            if name not in ('cost.py', 'README.md'):
                need(sha(data) == native_report['inputs'][name]['sha256'], 'original native producer input differs')
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            report['inputs'][name] = {'bytes': len(data), 'sha256': sha(data), 'working_bytes_sha256': sha(raw)}
        (frozen / 'native-build.json').write_bytes(native_raw)
        entry = frozen / 'inputs/entry'
        recipe = json.loads((entry / 'recipe.json').read_bytes())
        packer = load('phase_whole_packer', entry / 'packer.py')
        codec = load('phase_whole_codec', entry / 'loader/codec.py')
        transform = load('phase_whole_transform', frozen / 'transform.py')
        generated, _ = transform.apply((entry / 'native/search.c').read_bytes(), (frozen / 'phase.c.in').read_bytes())
        need(sha(generated) == SEARCH_SHA == native_report['source_cost']['candidate_search_sha256'], 'candidate source binding differs')
        need(set(EXPECTED) == {r['id'] for r in native_report['controls']} == {r['id'] for r in native_report['candidates']} and len(native_report['controls']) == len(native_report['candidates']) == 2, 'two exact forms required')
        report.update(native_checkpoint_sha256=NATIVE_REPORT_SHA, explicit_candidate_admission=EXPECTED,
                      resources=recipe['profile'], loader_flags=recipe['loader_flags'], tools_from_native=native_report['tools'],
                      zlib_build=zlib.ZLIB_VERSION, zlib_runtime=zlib.ZLIB_RUNTIME_VERSION,
                      mapping_contract='unchanged3RXpages/BSS0x403000175092B43pages/lower+upperguards/reserve/nonexecstack',
                      original_packer_source_unchanged=True)
        natives, layouts = {}, {}
        for group in ('controls', 'candidates'):
            for row in native_report[group]:
                mode = row['id']
                need(len(row['native_repeats']) == 2 and row['plain_diagnostic_repeats_identical'], 'native repeats incomplete')
                expected = copy.deepcopy(recipe['expected'][mode])
                if group == 'candidates':
                    explicit = EXPECTED[mode]
                    expected['native_bytes'], expected['native_sha256'] = explicit['native_bytes'], explicit['native_sha256']
                    expected['layout']['entry'] = explicit['entry']
                    expected['layout']['image_size'] = explicit['native_bytes']
                    expected['layout']['segments'][0]['filesz'] = expected['layout']['segments'][0]['memsz'] = explicit['native_bytes']
                images = []
                for spec in row['native_repeats']:
                    raw = Path(spec['path']).read_bytes()
                    need(len(raw) == expected['native_bytes'] and sha(raw) == expected['native_sha256'] == spec['sha256'], 'actual literal native differs')
                    layout = packer.admit(raw, expected, sha)
                    images.append(raw)
                need(images[0] == images[1], 'actual native repeat bytes differ')
                natives[group, mode], layouts[group, mode] = images[0], layout
                copy_path = frozen / 'natives' / group / mode
                copy_path.parent.mkdir(parents=True, exist_ok=True)
                copy_path.write_bytes(images[0])

        def pack(group, mode, attempt):
            raw, layout = natives[group, mode], layouts[group, mode]
            payload = codec.fixed_compress(codec.bcj(raw))
            need(codec.bcj(codec.fixed_decompress(payload, len(raw)), inverse=True) == raw, 'codec exact inverse differs')
            return packer.compile_loader(out / group / mode / attempt, entry / 'loader', payload, layout, recipe['loader_flags'], run, sha)

        # Reproduce each selected old whole identity before any new whole cost.
        for mode, expected in recipe['expected'].items():
            phase = mode + '/control'
            result = pack('controls', mode, 'fixed')
            need((result['bytes'], result['sha256'], result['payload_bytes'], result['loader_and_headers_bytes']) == (expected['whole_bytes'], expected['whole_sha256'], expected['payload_bytes'], expected['loader_and_headers_bytes']), 'control whole identity differs')
            report['controls'].append({'id': mode, 'whole': result})
        report['both_control_whole_identities_reproduced_before_candidate'] = True
        for mode, explicit in EXPECTED.items():
            phase = mode + '/candidate'
            first, repeat = pack('candidates', mode, 'fixed'), pack('candidates', mode, 'fixed-repeat')
            need(Path(first['path']).read_bytes() == Path(repeat['path']).read_bytes(), 'whole repeat bytes differ')
            need(first['loader_and_headers_bytes'] == repeat['loader_and_headers_bytes'] == 1115, 'fixed loader/header overhead changed')
            change = first['bytes'] - recipe['expected'][mode]['whole_bytes']
            report['candidates'].append({'id': mode, 'native_sha256': explicit['native_sha256'], 'layout': layouts['candidates', mode],
                                         'whole': first, 'repeat': repeat, 'whole_reproduced': True, 'whole_byte_change': change,
                                         'whole_strictly_smaller': change < 0})
        report['qualifying_size_profiles'] = [r['id'] for r in report['candidates'] if r['whole_strictly_smaller']]
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
                      'whole_costs': [{'id': r['id'], 'bytes': r['whole']['bytes'], 'change': r['whole_byte_change']} for r in report['candidates']]}))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
