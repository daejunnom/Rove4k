#!/usr/bin/env python3
"""Prove selected D reproduction from two explicit closed source extractions.

Archive members are enumerated, text-normalized and hashed, then revalidated
before extraction.  Each extraction invokes its own builder in a fresh Python
interpreter.  No original module, historical report or executable is imported.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import signal
import subprocess
import sys
import tarfile
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = 'engines/compact/tiny-entry-d/'
LOCAL = ('.gitattributes', 'README.md', 'build.py', 'fresh.py', 'packer.py', 'recipe.json', 'verify.py', 'shipping_fused_ray.py', 'shipping_context_h28.py', 'shipping_refill.py',
         'native/tiny.h', 'native/board.c', 'native/search.c', 'native/runtime.c', 'native/hq.h',
         'native/hq.c', 'native/start.S', 'native/image.ld', 'loader/loader.c', 'loader/image.ld', 'loader/codec.py',
         'loader/decoder.h', 'loader/range_bits.py', 'loader/models.json')
MEMBERS = tuple(PREFIX+name for name in LOCAL) + ('engines/tests/chess_oracle.py', 'LICENSE')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)) and ROOT not in out.parents, 'new absolute external output required')
    out.mkdir(parents=True)
    started, deadline = time.monotonic(), time.monotonic()+300
    report = {'complete': False, 'scope': 'two explicit closed source extractions; independent selected native/own-ELF regeneration and narrow physical checks',
              'source_members': {}, 'extractions': [], 'archive_has_git_or_generated_files': False}

    def cancelled(signum, frame):
        raise TimeoutError('parent cancelled closed-source proof')

    previous_term = signal.signal(signal.SIGTERM, cancelled)

    def save():
        (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')

    def run(command, cwd, label, cap=200):
        remaining = min(cap, deadline-time.monotonic())
        if remaining <= 0:
            raise TimeoutError('aggregate fresh-source deadline')
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
        env.pop('PYTHONPATH', None)
        process = None
        stdout = stderr = b''
        try:
            previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
            try:
                process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                                           preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask))
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            stdout, stderr = process.communicate(timeout=remaining)
            require(process.returncode == 0, label+' failed; see preserved stderr')
            return {'command': command, 'cwd': str(cwd), 'returncode': process.returncode,
                    'stdout_sha256': sha(stdout), 'stderr_sha256': sha(stderr)}
        finally:
            if process is not None:
                # The child builder/verifier owns separate native processes.
                # Its TERM handler runs those finally cleanups before fallback.
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                if process.poll() is None:
                    process.wait(timeout=3)
                stdout, stderr = process.communicate(timeout=3)
            (out/(label+'.stdout')).write_bytes(stdout)
            (out/(label+'.stderr')).write_bytes(stderr)

    save()
    try:
        blobs = {}
        for name in MEMBERS:
            path = ROOT/name
            require(path.is_file() and not path.is_symlink(), 'source must be a regular declared file: '+name)
            raw = path.read_bytes()
            data = raw.replace(b'\r\n', b'\n')
            require(b'\r' not in data, 'lone CR in source '+name)
            blobs[name] = data
            report['source_members'][name] = {'bytes': len(data), 'sha256': sha(data), 'working_bytes_sha256': sha(raw), 'LF_normalization': data != raw}
        archive = out/'source.tar'
        with tarfile.open(archive, 'w', format=tarfile.PAX_FORMAT) as tar:
            for name in MEMBERS:
                info = tarfile.TarInfo(name)
                info.size = len(blobs[name])
                info.mode = 0o644
                info.mtime = 0
                info.uid = info.gid = 0
                tar.addfile(info, io.BytesIO(blobs[name]))
        report['archive_sha256'] = sha(archive.read_bytes())
        reference = None
        for attempt in (1, 2):
            checkout = out/f'checkout-{attempt}'
            checkout.mkdir()
            with tarfile.open(archive) as tar:
                entries = tar.getmembers()
                require(len(entries) == len(MEMBERS) and {m.name for m in entries} == set(MEMBERS), 'archive member set differs')
                for member in entries:
                    relative = PurePosixPath(member.name)
                    require(member.isfile() and not relative.is_absolute() and '..' not in relative.parts and '\\' not in member.name, 'unsafe archive member')
                    data = tar.extractfile(member).read()
                    require(sha(data) == report['source_members'][member.name]['sha256'], 'archive source bytes differ')
                    path = checkout/member.name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
            actual = {str(p.relative_to(checkout)) for p in checkout.rglob('*') if p.is_file()}
            require(actual == set(MEMBERS), 'extraction is not the declared closed source set')
            entry = checkout/PREFIX
            build_out, verify_out = out/f'build-{attempt}', out/f'verify-{attempt}'
            row = {'attempt': attempt, 'checkout': str(checkout), 'closed_source_members': len(actual), 'engines': []}
            report['extractions'].append(row)
            row['build_command'] = run([sys.executable, '-I', '-B', str(entry/'build.py'), '--out', str(build_out)], checkout, f'build-{attempt}')
            build_bytes = (build_out/'build.json').read_bytes()
            build = json.loads(build_bytes)
            require(build['complete'] and not build.get('failure'), 'extracted build incomplete/failed')
            require(len(build['engines']) == 2 and {e['id'] for e in build['engines']} == {'scalar-shipping', 'hq-shipping'}, 'extracted build must contain both selected forms')
            identities = {}
            for engine in build['engines']:
                require(len(engine['native_rebuilds']) == 2 and engine['native_reproduced'] and engine['whole_reproduced'], 'exact independent native/whole repeats required')
                require(len(engine['candidates']) == 1, 'exactly one selected codec required')
                selected = engine['candidates'][0]
                native = Path(engine['native']).read_bytes()
                whole = Path(selected['path']).read_bytes()
                audit = Path(selected['audit']['path']).read_bytes()
                require(all(Path(n['path']).read_bytes() == native for n in engine['native_rebuilds']), 'actual native repeat bytes differ')
                require(Path(selected['reproduction']['path']).read_bytes() == whole, 'actual whole repeat bytes differ')
                identities[engine['id']] = (native, whole, audit)
                row['engines'].append({'id': engine['id'], 'native_bytes': len(native), 'native_sha256': sha(native),
                                      'whole_bytes': len(whole), 'whole_sha256': sha(whole), 'audit_sha256': sha(audit)})
            if reference is None:
                reference = identities
            else:
                require(identities == reference, 'independent extracted native/whole/audit bytes differ')
            row['build_sha256'] = sha(build_bytes)
            row['verify_command'] = run([sys.executable, '-I', '-B', str(entry/'verify.py'), '--build', str(build_out/'build.json'), '--out', str(verify_out)], checkout, f'verify-{attempt}')
            receipt = (verify_out/'results.json').read_bytes()
            verified = json.loads(receipt)
            require(verified.get('complete') is True and not verified['failures'] and not verified['interrupted_constructors_cleanup'], 'physical narrow verification incomplete/failed')
            require(len(verified['results']) == 2 and {e['engine'] for e in verified['results']} == {'scalar-shipping', 'hq-shipping'}, 'physical proof must contain both forms')
            for result in verified['results']:
                require(len(result['production']) == 2 and {s['shutdown'] for s in result['production']} == {'quit', 'EOF'}, 'physical quit/EOF matrix differs')
                require(all(s['passed'] and s['settled']['returncode'] == 0 and not s['cleanup']['forced_cleanup'] and not s['cleanup']['errors'] for s in result['production']), 'physical session did not settle')
                require(result['pre_entry']['pre_entry_bss_padding_zero'] and result['pre_entry']['rx_matches_restored_image'] and result['pre_entry']['resumed_original_entry'] and result['pre_entry']['settled']['returncode'] == 0, 'pre-entry checkpoint incomplete')
            row['verification_sha256'] = sha(receipt)
            row['native_whole_audit_repeat_match'] = True
            save()
        report['independent_extractions_bytes_equal'] = True
        report['complete'] = True
    except BaseException as error:
        report['complete'] = False
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        report['elapsed_seconds'] = time.monotonic()-started
        save()
        signal.signal(signal.SIGTERM, previous_term)
    print(json.dumps({'complete': True, 'closed_members': len(MEMBERS), 'independent_extractions': 2, 'out': str(out)}))


if __name__ == '__main__':
    main()
