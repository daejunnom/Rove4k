"""One fixed EP-to-make candidate: two native links from current atomic16 source, no engine run."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


def sections(raw):
    e = struct.unpack_from('<16sHHIQQQIHHHHHH', raw)
    hs = [struct.unpack_from('<IIQQQQIIQQ', raw, e[6]+i*e[11]) for i in range(e[12])]
    sh = hs[e[13]]
    names = raw[sh[4]:sh[4]+sh[5]]
    return {names[h[0]:].split(b'\0', 1)[0].decode(): dict(type=h[1], flags=h[2],
        address=h[3], offset=h[4], bytes=h[5], alignment=h[8]) for h in hs if h[2] & 2}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    require(sys.platform == 'linux' and os.uname().machine == 'x86_64' and args.out.is_absolute()
            and not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)),
            'new external Linux x86-64 output required')
    recipe_raw = (HERE/'recipe.json').read_bytes()
    recipe = json.loads(recipe_raw)
    require(recipe['profile'] == dict(workers=2, tt_bits=18, ply=128, dev=0) and
            recipe['native_links'] == 2 and not recipe['target_executions'], 'fixed scope differs')
    control = {name: (HERE/'control/native'/name).read_bytes() for name in recipe['source_sha256']}
    for name, pin in recipe['source_sha256'].items():
        require(sha(control[name]) == pin and
                sha((Path(recipe['normal_native_source_path'])/name).read_bytes()) == pin,
                'current exact native source differs: '+name)
    candidate = dict(control)
    for change in recipe['changes']:
        old, new = change['old'].encode(), change['new'].encode()
        require(candidate[change['file']].count(old) == 1, 'one reviewed old fragment required')
        candidate[change['file']] = candidate[change['file']].replace(old, new, 1)
    inverse = dict(candidate)
    for change in reversed(recipe['changes']):
        old, new = change['old'].encode(), change['new'].encode()
        require(inverse[change['file']].count(new) == 1, 'one reviewed inverse fragment required')
        inverse[change['file']] = inverse[change['file']].replace(new, old, 1)
    require(inverse == control, 'exact source inverse/complement differs')
    for name, expected in recipe['candidate_source_expected'].items():
        require(len(candidate[name]) == expected['bytes'] and sha(candidate[name]) == expected['sha256'],
                'fixed candidate bytes differ: '+name)
    reference = HERE/'reference/packer.py'
    require(sha(reference.read_bytes()) == recipe['reference_packer_sha256'], 'unchanged reference packer differs')
    spec = importlib.util.spec_from_file_location('unchanged_C_D_ELF_helpers', reference)
    packer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(packer)
    baseline_raw = Path(recipe['baseline_build_receipt_path']).read_bytes()
    require(sha(baseline_raw) == recipe['baseline_build_receipt_sha256'], 'authoritative baseline receipt differs')
    baseline = json.loads(baseline_raw)
    require(baseline['complete'], 'authoritative baseline incomplete')
    old = {}
    for form, pin in recipe['controls'].items():
        raw = Path(pin['native_path']).read_bytes()
        linked = Path(pin['linked_path']).read_bytes()
        whole = Path(pin['whole_path']).read_bytes()
        require((len(raw), sha(raw)) == (pin['native_bytes'], pin['native_sha256']) and
                packer.strip_native(linked) == raw and
                (len(whole), sha(whole)) == (pin['whole_bytes'], pin['whole_sha256']), 'old control bytes differ')
        old[form] = dict(**pin, sections=sections(linked), elf=packer.elf(raw))
    out.mkdir(parents=True)
    frozen = out/'source-freeze'
    frozen.mkdir()
    sources = []
    for path in sorted(HERE.rglob('*')):
        if path.is_file():
            require(path.suffix != '.pyc', 'generated source entry')
            raw = path.read_bytes()
            relative = path.relative_to(HERE)
            target = frozen/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            sources.append(dict(path=str(relative), bytes=len(raw), sha256=sha(raw)))
    (out/'source-freeze.json').write_text(json.dumps(sources, indent=2)+'\n')
    inputs = out/'candidate-inputs'
    inputs.mkdir()
    for name, raw in candidate.items():
        (inputs/name).write_bytes(raw)
    report = dict(complete=False, recipe_sha256=sha(recipe_raw), source_freeze=sources,
                  source_inverse_exact=True, raw_native_input_delta=recipe['raw_native_input_delta'],
                  execution_isa_required=recipe['execution_isa_required'], controls=old, forms=[], commands=[],
                  native_links=0, control_links=0, extra_unstripped_or_repeat_links=0,
                  target_ELF_or_TT_asm_executions=0, codec_encodes=0, live_handles=[])
    report_path = out/'native-cost.json'
    environment = {**os.environ, 'LC_ALL': 'C', 'TZ': 'UTC', 'SOURCE_DATE_EPOCH': '0'}

    def save():
        report_path.write_text(json.dumps(report, indent=2)+'\n')

    def absent(pid):
        try:
            os.killpg(pid, 0)
            return False
        except ProcessLookupError:
            return True

    def run(command):
        row = dict(command=command, cwd=str(out), pid=None, terminal=False, EOF_drained=False)
        report['commands'].append(row)
        process = None
        save()
        try:
            process = subprocess.Popen(command, cwd=out, env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
            row['pid'] = process.pid
            report['live_handles'] = [process.pid]
            save()
            stdout, stderr = process.communicate(timeout=120)
            row.update(stdout=stdout, stderr=stderr, returncode=process.returncode,
                       terminal=True, EOF_drained=True, group_absent=absent(process.pid))
            require(process.returncode == 0 and row['group_absent'], 'tool failed or owned group remains')
            report['live_handles'] = []
            return stdout
        except BaseException as error:
            row['first_failure'] = dict(type=type(error).__name__, message=str(error))
            if isinstance(error, subprocess.TimeoutExpired):
                row.update(first_partial_stdout=repr(error.output), first_partial_stderr=repr(error.stderr))
            save()
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except BaseException as cleanup_error:
                    row['kill_error'] = repr(cleanup_error)
                try:
                    stdout, stderr = process.communicate(timeout=5)
                    row.update(stdout=stdout, stderr=stderr, returncode=process.returncode, EOF_drained=True)
                except BaseException as cleanup_error:
                    row['drain_error'] = repr(cleanup_error)
                row.update(terminal=process.poll() is not None, group_absent=absent(process.pid))
                if row['terminal'] and row['EOF_drained'] and row['group_absent']:
                    report['live_handles'] = []
            raise
        finally:
            save()

    def interrupted(signum, _frame):
        raise InterruptedError('signal '+str(signum))

    previous = {s: signal.signal(s, interrupted) for s in (signal.SIGINT, signal.SIGTERM)}
    save()
    try:
        compiler = run(['cc', '--version'])
        require(compiler.splitlines()[0] == baseline['tools']['cc'].splitlines()[0], 'fixed baseline cc differs')
        report['compiler'] = compiler
        for form, pin in recipe['controls'].items():
            local = out/form
            local.mkdir()
            hq = int(form == 'hq-shipping')
            command = ['cc', *recipe['native_flags'], '-DD_HQ='+str(hq), '-DDEV=0',
                *[str(inputs/name) for name in recipe['native_units']],
                '-Wl,-T,'+str(inputs/'image.ld'), '-o', str(local/'linked')]
            report['native_links'] += 1
            run(command)
            linked = (local/'linked').read_bytes()
            native = packer.strip_native(linked)
            (local/'x').write_bytes(native)
            current = sections(linked)
            row = dict(form=form, native_path=str(local/'x'), native_bytes=len(native), native_sha256=sha(native),
                linked_path=str(local/'linked'), linked_sha256=sha(linked), sections=current, elf=packer.elf(native),
                native_delta=len(native)-pin['native_bytes'], section_deltas={name: section['bytes']-old[form]['sections'][name]['bytes']
                    for name, section in current.items()}, candidate_source_sha256={name: sha(raw) for name, raw in candidate.items()})
            report['forms'].append(row)
            save()
            for label, command in [('sections', ['readelf', '-SW', str(local/'linked')]),
                                   ('program_headers', ['readelf', '-lW', str(local/'x')]),
                                   ('disassembly', ['objdump', '-d', str(local/'linked')])]:
                output = run(command)
                (local/(label+'.txt')).write_text(output)
                if label == 'disassembly':
                    row['atomic16_instructions'] = [line for line in output.splitlines() if 'lock cmpxchg16b' in line]
                    require(row['atomic16_instructions'], 'atomic16 instruction missing')
        require(report['native_links'] == 2 and not report['live_handles'], 'two-link bounded native phase incomplete')
        for source in sources:
            require(sha((HERE/source['path']).read_bytes()) == source['sha256'], 'frozen own source changed')
        report['complete'] = True
    except BaseException as error:
        report['first_failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        save()
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    print(json.dumps(dict(out=str(out), complete=report['complete'], forms=[{k: row[k] for k in
        ('form', 'native_bytes', 'native_sha256', 'native_delta', 'section_deltas', 'atomic16_instructions')}
        for row in report['forms']], native_links=report['native_links'], live_handles=report['live_handles'])))


if __name__ == '__main__':
    main()
