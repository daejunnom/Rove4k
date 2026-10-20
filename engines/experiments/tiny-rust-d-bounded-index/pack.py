"""Fixed data8 whole costs: decode two old controls, pack two candidates; no ELF run."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    require(sys.platform == 'linux' and os.uname().machine == 'x86_64' and args.out.is_absolute()
            and not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)),
            'new external Linux x86-64 output required')
    raw_recipe = (HERE/'pack-recipe.json').read_bytes()
    recipe = json.loads(raw_recipe)
    for name, pin in recipe['unchanged_source_sha256'].items():
        require(sha((HERE/name).read_bytes()) == pin, 'unchanged own packaging source differs: '+name)
    admit_raw = (HERE/'admit.py').read_bytes()
    require(sha(admit_raw) == recipe['new_admit_sha256'] and
            sha(admit_raw[admit_raw.index(b'def sha(data):'):]) == recipe['unchanged_admit_body_sha256'],
            'separate identity or unchanged data8 guard body differs')
    native_receipt = Path(recipe['native_cost_path']).read_bytes()
    require(sha(native_receipt) == recipe['native_cost_sha256'], 'completed native receipt differs')
    native_report = json.loads(native_receipt)
    require(native_report['complete'] and native_report['primary_Rust_links'] == 2 and
            not native_report['live_handles'] and not recipe['runtime_execution_authorized'],
            'native phase incomplete or runtime scope differs')
    packer = module('fixed_own_packer', HERE/'packaging/packer.py')
    codec = module('fixed_own_codec', HERE/'packaging/loader/codec.py')
    admitted = module('separate_bounded_index_data8', HERE/'admit.py')
    require(admitted.CLASS == recipe['class'] and admitted.NATIVE == recipe['native_expected'] and
            recipe['codec'] == dict(bcj_version=codec.BCJ_VERSION, fixed_version=codec.FIXED_VERSION),
            'fixed class/codec differs')
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
    report = dict(complete=False, recipe_sha256=sha(raw_recipe), source_freeze=sources,
                  native_cost_path=recipe['native_cost_path'], native_cost_sha256=sha(native_receipt),
                  controls=[], candidates=[], commands=[], candidate_encodes=0, loader_links=0,
                  strict_full_decodes=0, control_encodes=0, native_recompiles=0,
                  target_runtime_executions=0, runtime_qualified=False, live_handles=[])
    report_path = out/'whole-cost.json'
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
            require(process.returncode == 0 and row['group_absent'], 'loader link failed or group remains')
            report['live_handles'] = []
            return row
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

    def decoded_actual_whole(raw, payload_bytes, load):
        require(packer.stripped_loader(raw) == raw and len(raw)-payload_bytes == 1115,
                'actual whole fixed loader/header layout differs')
        payload = raw[-payload_bytes:]
        report['strict_full_decodes'] += 1
        decoded = codec.bcj(codec.fixed_decompress(payload, len(load)), inverse=True)
        require(decoded == load and sha(decoded) == sha(load), 'actual whole strict decode/inverse differs')
        return dict(payload_sha256=sha(payload), strict_decoded_span_sha256=sha(decoded),
                    whole_program_headers=packer.elf(raw))

    def interrupted(signum, _frame):
        raise InterruptedError('signal '+str(signum))

    previous = {s: signal.signal(s, interrupted) for s in (signal.SIGINT, signal.SIGTERM)}
    save()
    try:
        for backend in ('scalar', 'hq'):
            pin = recipe['controls'][backend]
            native = Path(pin['native_path']).read_bytes()
            load, proof = admitted.admit(native, 'control-'+backend, packer)
            raw = Path(pin['whole_path']).read_bytes()
            require(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'] and
                    sha(raw[-pin['payload_bytes']:]) == pin['payload_sha256'], 'old actual control whole differs')
            row = dict(form=backend, path=pin['whole_path'], bytes=len(raw), sha256=sha(raw),
                       payload_bytes=pin['payload_bytes'], loader_and_headers_bytes=1115,
                       control_reused_read_only=True, load_proof=proof,
                       **decoded_actual_whole(raw, pin['payload_bytes'], load))
            report['controls'].append(row)
            save()
        for backend in ('scalar', 'hq'):
            native = Path(recipe['candidate_paths'][backend]).read_bytes()
            load, proof = admitted.admit(native, 'candidate-'+backend, packer)
            local = out/('candidate-'+backend)
            local.mkdir()
            (local/'load-span.bin').write_bytes(load)
            report['candidate_encodes'] += 1
            payload = codec.fixed_compress(codec.bcj(load))
            report['loader_links'] += 1
            whole = packer.compile_loader(local/'whole', HERE/'packaging/loader', payload,
                         recipe['packing_layout'], recipe['loader_flags'], run, sha)
            raw = Path(whole['path']).read_bytes()
            require(raw[-len(payload):] == payload, 'actual loader payload bytes differ')
            row = dict(form=backend, **whole, load_proof=proof,
                       whole_delta=len(raw)-recipe['controls'][backend]['bytes'],
                       **decoded_actual_whole(raw, len(payload), load))
            report['candidates'].append(row)
            save()
        require(report['candidate_encodes'] == 2 and report['loader_links'] == 2 and
                report['strict_full_decodes'] == 4 and not report['live_handles'], 'bounded pack incomplete')
        require((HERE/'pack-recipe.json').read_bytes() == raw_recipe, 'pack recipe changed')
        for source in sources:
            require(sha((HERE/source['path']).read_bytes()) == source['sha256'], 'own source changed during pack')
        report['complete'] = True
    except BaseException as error:
        report['first_failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        save()
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    print(json.dumps(dict(out=str(out), complete=report['complete'], candidates=[{k: r[k] for k in
        ('form', 'bytes', 'sha256', 'whole_delta', 'payload_bytes', 'loader_and_headers_bytes')}
        for r in report['candidates']], encodes=report['candidate_encodes'], loader_links=report['loader_links'],
        strict_full_decodes=report['strict_full_decodes'], live_handles=report['live_handles'])))


if __name__ == '__main__':
    main()
