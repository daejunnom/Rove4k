"""Two fixed candidate Rust links and static readback; never execute an ELF."""

if __name__ == "__main__":
    raise SystemExit("Rove4k Rust engine paths are retired; use C A-F")

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


def elf(raw):
    require(raw[:6] == b'\x7fELF\x02\x01', 'ELF64 little-endian required')
    e = struct.unpack_from('<16sHHIQQQIHHHHHH', raw)
    headers = [struct.unpack_from('<IIQQQQIIQQ', raw, e[6]+i*e[11]) for i in range(e[12])]
    names_header = headers[e[13]]
    names = raw[names_header[4]:names_header[4]+names_header[5]]
    sections = {}
    for h in headers:
        if h[2] & 2:
            name = names[h[0]:].split(b'\0', 1)[0].decode()
            content = bytes(h[5]) if h[1] == 8 else raw[h[4]:h[4]+h[5]]
            sections[name] = dict(type=h[1], flags=h[2], address=h[3], offset=h[4],
                                  bytes=h[5], alignment=h[8], sha256=sha(content))
    ph = [struct.unpack_from('<IIQQQQQQ', raw, e[5]+i*e[9]) for i in range(e[10])]
    return dict(entry=e[4], sections=sections, program_headers=[dict(type=h[0], flags=h[1],
        offset=h[2], vaddr=h[3], paddr=h[4], filesz=h[5], memsz=h[6], align=h[7]) for h in ph])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    require(sys.platform == 'linux' and os.uname().machine == 'x86_64', 'Linux x86-64 required')
    require(args.out.is_absolute() and not out.exists() and
            not any((p/'.git').exists() for p in (out, *out.parents)), 'new external output required')
    recipe_raw = (HERE/'recipe.json').read_bytes()
    recipe = json.loads(recipe_raw)
    control = {n: (HERE/'control'/n).read_bytes() for n in recipe['source_sha256']}
    for name, pin in recipe['source_sha256'].items():
        require(sha(control[name]) == pin, 'owned control changed: '+name)
        require(sha((Path(recipe['maintained_source_path'])/name).read_bytes()) == pin,
                'actual maintained input differs: '+name)
    candidate = dict(control)
    change = recipe['transform']
    old, new = change['old'].encode(), change['new'].encode()
    require(candidate['board.rs'].count(old) == 1, 'one exact old fragment required')
    candidate['board.rs'] = candidate['board.rs'].replace(old, new, 1)
    require(candidate['board.rs'].count(new) == 1 and
            candidate['board.rs'].replace(new, old, 1) == control['board.rs'], 'exact inverse failed')
    require(len(candidate['board.rs']) == change['candidate_bytes'] and
            sha(candidate['board.rs']) == change['candidate_sha256'], 'fixed candidate differs')
    require(recipe['profile'] == dict(workers=2, tt_bits=18) and
            recipe['approved_primary_links'] == 2 and not recipe['target_execution'], 'scope differs')
    require(sha(Path(recipe['compiler_actual_path']).read_bytes()) == recipe['compiler_actual_sha256'],
            'fixed compiler binary differs')
    controls = {}
    for backend, pin in recipe['control_native'].items():
        raw = Path(pin['path']).read_bytes()
        require(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], 'existing control native differs')
        controls[backend] = dict(path=pin['path'], bytes=len(raw), sha256=sha(raw), elf=elf(raw))
    out.mkdir(parents=True)
    source_freeze = out/'source-freeze'
    source_freeze.mkdir()
    source_rows = []
    for path in sorted(HERE.rglob('*')):
        require(path.is_file() or path.is_dir(), 'nonordinary owned entry')
        if not path.is_file():
            continue
        require(path.suffix != '.pyc' and path.name != '__pycache__', 'generated source not allowed')
        raw = path.read_bytes()
        relative = path.relative_to(HERE)
        target = source_freeze/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        source_rows.append(dict(path=str(relative), bytes=len(raw), sha256=sha(raw)))
    (out/'source-freeze.json').write_text(json.dumps(source_rows, indent=2)+'\n')
    report = dict(complete=False, recipe_sha256=sha(recipe_raw), source_freeze=source_rows,
                  controls=controls, forms=[], commands=[], primary_Rust_links=0,
                  control_links=0, extra_unstripped_or_repeat_links=0, codec_calls=0,
                  loader_links=0, target_runtime_executions=0, live_handles=[], whole='unmeasured')
    report_path = out/'native-cost.json'
    environment = {**os.environ, **recipe['environment']}

    def save():
        report_path.write_text(json.dumps(report, indent=2)+'\n')

    def absent(pid):
        try:
            os.killpg(pid, 0)
            return False
        except ProcessLookupError:
            return True

    def run(command, cwd):
        row = dict(command=command, cwd=str(cwd), pid=None, terminal=False, EOF_drained=False)
        report['commands'].append(row)
        process = None
        save()
        try:
            process = subprocess.Popen(command, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
            row['pid'] = process.pid
            report['live_handles'] = [process.pid]
            save()
            stdout, stderr = process.communicate(timeout=120)
            row.update(stdout=stdout, stderr=stderr, returncode=process.returncode,
                       terminal=True, EOF_drained=True, group_absent=absent(process.pid))
            require(process.returncode == 0 and row['group_absent'], 'tool failed or process group remains')
            report['live_handles'] = []
            return stdout
        except BaseException as error:
            row['first_failure'] = dict(type=type(error).__name__, message=str(error))
            if isinstance(error, subprocess.TimeoutExpired):
                row['first_partial_stdout'] = repr(error.output)
                row['first_partial_stderr'] = repr(error.stderr)
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
                    row.update(stdout=stdout, stderr=stderr, returncode=process.returncode,
                               EOF_drained=True)
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
        version = run([recipe['compiler_command'], '--version'], out).strip()
        require(version == recipe['compiler_version'], 'fixed compiler version differs')
        report['compiler'] = version
        for backend in ('scalar', 'hq'):
            local = out/('candidate-'+backend)
            local.mkdir()
            for name, raw in candidate.items():
                (local/name).write_bytes(raw)
            environment['ROVE_HQ'] = str(int(backend == 'hq'))
            resolved = run([str(Path(recipe['compiler_command']).with_name('rustup')),
                            'which', 'rustc'], local).strip()
            require(resolved == recipe['compiler_actual_path'] and
                    sha(Path(resolved).read_bytes()) == recipe['compiler_actual_sha256'],
                    'compiler shim resolves to a different fixed binary')
            command = [recipe['compiler_command'], '--remap-path-prefix', str(local)+'=.',
                       *recipe['native_flags']]
            report['primary_Rust_links'] += 1
            run(command, local)
            raw = (local/'x').read_bytes()
            image = elf(raw)
            row = dict(form=backend, path=str(local/'x'), bytes=len(raw), sha256=sha(raw), elf=image,
                       source_sha256={name: sha(data) for name, data in candidate.items()})
            row['native_delta'] = len(raw)-controls[backend]['bytes']
            row['section_deltas'] = {name: value['bytes']-controls[backend]['elf']['sections'][name]['bytes']
                                     for name, value in image['sections'].items()}
            report['forms'].append(row)
            save()
            for label, command in [('program_headers', ['readelf', '-lW', str(local/'x')]),
                                   ('sections', ['readelf', '-SW', str(local/'x')]),
                                   ('disassembly', ['objdump', '-d', str(local/'x')])]:
                (local/(label+'.txt')).write_text(run(command, local))
        require(report['primary_Rust_links'] == 2 and not report['live_handles'], 'bounded run incomplete')
        report['complete'] = True
    except BaseException as error:
        report['first_failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        save()
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    print(json.dumps(dict(out=str(out), forms=[{k: r[k] for k in
          ('form', 'bytes', 'sha256', 'native_delta', 'section_deltas')} for r in report['forms']],
          primary_Rust_links=report['primary_Rust_links'], live_handles=report['live_handles'],
          whole=report['whole'])))


if __name__ == '__main__':
    main()
