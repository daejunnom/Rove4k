"""One fixed inverse-BCJ expression, two loader compiles, no target execution."""
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
NORMAL = HERE.parents[1]/'compact/tiny-entry-d'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def save(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n')


def load_module(path):
    spec = importlib.util.spec_from_file_location('fixed_D_packer', path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def build(args):
    out = args.out.resolve()
    need(args.out.is_absolute() and not out.exists() and
         not any((p/'.git').exists() for p in (out, *out.parents)), 'new absolute output outside Git required')
    need(sys.platform == 'linux' and platform.machine() == 'x86_64', 'fixed Linux AMD64 only')
    recipe_raw = (HERE/'recipe.json').read_bytes();recipe = json.loads(recipe_raw)
    out.mkdir();sources = out/'sources';sources.mkdir();producer = out/'producer';producer.mkdir()
    report = {'complete': False, 'stage': 'two loader compilations; static codegen review pending',
              'loader_compile_count': 0, 'native_compile_count': 0, 'encoder_runs': 0,
              'target_runs': 0, 'audit_runs': 0, 'fresh_runs': 0, 'negative_runs': 0,
              'AST_runs': 0, 'packet_copies': 0, 'native_copies': 0, 'inputs': {}, 'candidates': []}
    save(out/'build.json', report)
    deadline = time.monotonic()+120

    def cancelled(signum, frame):
        raise TimeoutError('parent cancelled bounded loader cost')

    previous = signal.signal(signal.SIGTERM, cancelled)

    def run(command):
        process = None
        try:
            timeout = min(45, deadline-time.monotonic())
            need(timeout > 0, 'aggregate loader cost deadline')
            mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    start_new_session=True, preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, mask))
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, mask)
            stdout, stderr = process.communicate(timeout=timeout)
            record = {'command': command, 'returncode': process.returncode,
                      'stdout': stdout.decode(errors='replace'), 'stderr': stderr.decode(errors='replace')}
            need(process.returncode == 0, 'fixed tool failed: '+json.dumps(record))
            return record
        finally:
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                if process.poll() is None:
                    process.wait(timeout=3)

    try:
        for name in ('build.py', 'recipe.json'):
            data = (HERE/name).read_bytes();(producer/name).write_bytes(data)
            report['inputs'][name] = {'bytes': len(data), 'sha256': sha(data)}
        for name, pin in recipe['normal_sources'].items():
            raw = (NORMAL/name).read_bytes();data = raw.replace(b'\r\n', b'\n')
            need(b'\r' not in data and sha(data) == pin, 'normal source drift: '+name)
            target = sources/name;target.parent.mkdir(parents=True, exist_ok=True);target.write_bytes(data)
            report['inputs']['normal/'+name] = {'bytes': len(data), 'sha256': sha(data), 'raw_sha256': sha(raw)}
        source = (sources/'loader/loader.c').read_bytes()
        before, after = recipe['before'].encode(), recipe['after'].encode()
        need(source.count(before) == 1 and source.count(after) == 0, 'literal input boundary differs')
        candidate = source.replace(before, after)
        need(candidate.count(after) == 1 and candidate.replace(after, before) == source, 'literal inverse differs')
        need(len(candidate) == recipe['candidate_loader_bytes'] and
             sha(candidate) == recipe['candidate_loader_sha256'], 'fixed candidate differs')
        (sources/'loader/loader-control.c').write_bytes(source)
        (sources/'loader/loader.c').write_bytes(candidate)
        report.update(candidate_loader_bytes=len(candidate), candidate_loader_sha256=sha(candidate),
                      exact_source_inverse=True, unchanged_other_source=True)
        packer = load_module(sources/'packer.py')
        # All baseline files are verified before either compiler is started.
        for form, expected in recipe['forms'].items():
            for role, item in expected['files'].items():
                data = Path(item['path']).read_bytes()
                need((len(data), sha(data)) == (item['bytes'], item['sha256']), 'baseline drift: '+form+'/'+role)
            native = Path(expected['files']['native']['path']).read_bytes()
            parsed = packer.elf(native)
            need(all(parsed[k] == expected['layout'][k] for k in parsed), 'literal native layout differs')
            baseline = Path(expected['files']['whole']['path']).read_bytes()
            linked = Path(expected['files']['linked']['path']).read_bytes()
            need(packer.stripped_loader(linked) == baseline, 'baseline linked/whole identity differs')
            packet = Path(expected['files']['packet']['path']).read_bytes()
            need(packet[-4:] == bytes(4) and baseline[1367:] == packet, 'fixed packet extent/tail differs')
            definitions = expected['definitions']
            need(definitions['CHECKPOINT'] == 0 and definitions['IMAGE_SIZE'] == len(native) and
                 definitions['IMAGE_ENTRY'] == parsed['entry'], 'selected definitions differ')
        save(out/'build.json', report)
        for form, expected in recipe['forms'].items():
            directory = out/form;directory.mkdir()
            packet = Path(expected['files']['packet']['path']).read_bytes()
            (directory/'payload.bin').write_bytes(packet);report['packet_copies'] += 1
            assembly = directory/'payload.S'
            quoted = str(directory/'payload.bin').replace('\\', '\\\\').replace('"', '\\"')
            assembly.write_text('.section .payload,"a",@progbits\n.global payload,payload_end\npayload:\n'
                '.incbin "'+quoted+'"\npayload_end:\n.section .note.GNU-stack,"",@progbits\n')
            command = ['cc', *recipe['loader_flags'],
                *[f'-D{k}={v}UL' for k, v in expected['definitions'].items()],
                str(sources/'loader/loader.c'), str(assembly),
                '-Wl,-T,'+str(sources/'loader/image.ld'), '-o', str(directory/'linked')]
            report['loader_compile_count'] += 1;save(out/'build.json', report)
            compiled = run(command);save(directory/'compile.json', compiled)
            binary = (directory/'linked').read_bytes()
            whole = packer.stripped_loader(binary)
            need(whole.endswith(packet), 'packet bytes changed')
            need(packer.elf(whole)['entry'] == 0x100000b0, 'loader entry changed')
            disassembly = run(['objdump', '-d', '-M', 'intel', '--section=.text', str(directory/'linked')])
            (directory/'disassembly.txt').write_text(disassembly['stdout'])
            symbols = run(['readelf', '--dyn-syms', '--wide', str(directory/'linked')])
            (directory/'dynamic-symbols.txt').write_text(symbols['stdout'])
            row = {'form': form, 'linked_bytes': len(binary), 'linked_sha256': sha(binary),
                   'pending_whole_bytes': len(whole), 'pending_whole_sha256': sha(whole),
                   'packet_bytes': len(packet), 'packet_sha256': sha(packet),
                   'nonpacket_bytes': len(whole)-len(packet), 'ELF': packer.elf(whole),
                   'definitions': expected['definitions'], 'source_sha256': sha(candidate),
                   'native_reused': expected['files']['native'], 'baseline_files_reused': expected['files'],
                   'manual_codegen_required': True}
            report['candidates'].append(row);save(out/'build.json', report)
            print(json.dumps({'form': form, 'loader_compile': 'PASS', 'codegen_pending': True}), flush=True)
        need(report['loader_compile_count'] == 2, 'exactly one compiler per form required')
        report['compile_stage_complete'] = True;save(out/'build.json', report)
    except BaseException as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        save(out/'build.json', report)
        raise
    finally:
        signal.signal(signal.SIGTERM, previous)


def finish(args):
    out = args.build.resolve();report_raw = (out/'build.json').read_bytes();report = json.loads(report_raw)
    need(report.get('compile_stage_complete') and report['loader_compile_count'] == 2 and
         not (out/'cost.json').exists(), 'only the one completed compile pair may finish once')
    review_raw = args.review.read_bytes();review = json.loads(review_raw)
    recipe = json.loads((out/'producer/recipe.json').read_bytes())
    need(sha((HERE/'build.py').read_bytes()) == report['inputs']['build.py']['sha256'] and
         sha((HERE/'recipe.json').read_bytes()) == report['inputs']['recipe.json']['sha256'], 'producer changed')
    need(review['result'] == 'PASS' and review['build_sha256'] == sha(report_raw), 'static readback missing')
    for name, item in report['inputs'].items():
        if name.startswith('normal/'):
            relative = name.removeprefix('normal/')
            relative = 'loader/loader-control.c' if relative == 'loader/loader.c' else relative
            need(sha((out/'sources'/relative).read_bytes()) == item['sha256'], 'frozen ordinary input drift')
    need(sha((out/'sources/loader/loader.c').read_bytes()) == recipe['candidate_loader_sha256'],
         'candidate source drift')
    save(out/'cost.json', {'complete': False, 'build_sha256': sha(report_raw),
         'review_sha256': sha(review_raw), 'scope': 'one finish attempt; preserve failure, no retry',
         'loader_compile_count': 2, 'native_compile_count': 0, 'encoder_runs': 0, 'target_runs': 0})
    packer = load_module(out/'sources/packer.py')
    rows = []
    for row in report['candidates']:
        form = row['form'];directory = out/form;proof = review['forms'][form]
        linked = (directory/'linked').read_bytes()
        need(sha(linked) == row['linked_sha256'] == proof['linked_sha256'] and
             proof['fixed_four_byte_inline'] and proof['no_new_helper_or_undefined'] and
             proof['BCJ_bounds_modulo_skip_preserved'], 'new inline/codegen gate failed')
        whole = packer.stripped_loader(linked);packet = (directory/'payload.bin').read_bytes()
        need(sha(packet) == row['packet_sha256'] and whole.endswith(packet), 'packet drift')
        (directory/'x').write_bytes(whole)
        reset = recipe['forms'][form]['files']['whole'];maintained = recipe['forms'][form]['maintained_whole']
        rows.append({**row, 'whole_bytes': len(whole), 'whole_sha256': sha(whole),
            'reset_control_bytes': reset['bytes'], 'versus_reset_bytes': len(whole)-reset['bytes'],
            'maintained_control_bytes': maintained['bytes'], 'versus_maintained_bytes': len(whole)-maintained['bytes'],
            'codegen_review_pass': True})
    save(out/'cost.json', {'complete': True, 'scope': 'D worker reset plus one BCJ load expression; cost only',
         'build_sha256': sha(report_raw), 'review_sha256': sha(review_raw), 'candidates': rows,
         'loader_compile_count': 2, 'native_compile_count': 0, 'encoder_runs': 0, 'target_runs': 0,
         'audit_runs': 0, 'fresh_runs': 0, 'negative_runs': 0, 'AST_runs': 0,
         'disposition': 'stop at cost; await root' if all(r['versus_reset_bytes'] < 0 for r in rows)
                        else 'loss/tie; stop with no retry'})
    print(json.dumps([{k: r[k] for k in ('form', 'whole_bytes', 'whole_sha256', 'versus_reset_bytes',
                     'versus_maintained_bytes', 'nonpacket_bytes')} for r in rows]), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);sub = parser.add_subparsers(dest='stage', required=True)
    first = sub.add_parser('build');first.add_argument('--out', type=Path, required=True)
    second = sub.add_parser('finish');second.add_argument('--build', type=Path, required=True)
    second.add_argument('--review', type=Path, required=True)
    args = parser.parse_args();{'build': build, 'finish': finish}[args.stage](args)
