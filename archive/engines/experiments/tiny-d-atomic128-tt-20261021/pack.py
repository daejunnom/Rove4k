"""Two fixed21 CRC whole costs and two existing positive DATA helper runs; no TT run."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
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
    require(recipe['candidate_encodes'] == recipe['loader_links'] == 2 and
            recipe['positive_data_helper_executions'] == 2 and not recipe['target_TT_ASM_engine_executions'],
            'bounded cost/data-diagnostic scope differs')
    for name, pin in recipe['loader_source_sha256'].items():
        require(sha((HERE/name).read_bytes()) == pin, 'unchanged codec/model/loader source differs')
    require(sha((HERE/'candidate-packer.py').read_bytes()) == recipe['candidate_packer_sha256'],
            'new literal class source differs')
    require(sha((HERE/'reference/packer.py').read_bytes()) == recipe['reference_packer_sha256'],
            'old reference packer differs')
    native_raw = Path(recipe['native_receipt_path']).read_bytes()
    require(sha(native_raw) == recipe['native_receipt_sha256'], 'native receipt differs')
    native_report = json.loads(native_raw)
    require(native_report['complete'] and native_report['native_links'] == 2 and not native_report['live_handles'],
            'native phase incomplete')
    for pin in recipe['helpers'].values():
        raw = Path(pin['path']).read_bytes()
        require((len(raw), sha(raw)) == (pin['bytes'], pin['sha256']), 'old DATA helper binary differs')
        require(sha(Path(pin['historical_receipt_path']).read_bytes()) == pin['historical_receipt_sha256'],
                'old DATA compile/source receipt differs')
        for name, digest in pin['source_sha256'].items():
            require(sha((HERE/'data-helper'/name).read_bytes()) == digest, 'exact DATA helper source differs')
    cpu_blocks = Path('/proc/cpuinfo').read_text().split('\n\n')
    allowed = os.sched_getaffinity(0)
    features = {}
    for block in cpu_blocks:
        fields = dict(line.split(':', 1) for line in block.splitlines() if ':' in line)
        fields = {key.strip(): value.strip() for key, value in fields.items()}
        if 'processor' in fields and int(fields['processor']) in allowed:
            features[int(fields['processor'])] = fields.get('flags', '').split()
    require(set(features) == allowed and all('sse4_2' in f for f in features.values()),
            'positive CRC DATA helper needs SSE4.2 on every affinity CPU')
    packer = module('separate_atomic128_literal_packer', HERE/'candidate-packer.py')
    codec = module('unchanged_fixed21_encoder', HERE/'loader/codec.py')
    require(packer.CLASS == recipe['class'] and codec.PACKET_FORMAT == recipe['codec'], 'fixed class/codec differs')
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
                  native_receipt_path=recipe['native_receipt_path'], native_receipt_sha256=sha(native_raw),
                  commands=[], forms=[], candidate_encodes=0, loader_links=0,
                  reused_positive_DATA_helper_runs=0, new_DATA_helper_compiles=0,
                  target_engine_loader_TT_ASM_executions=0, native_recompiles=0,
                  control_encodes_compiles=0, runtime_qualified=False, live_handles=[],
                  DATA_helper_CPU_profile={'available_cpus': sorted(allowed), 'sse4_2_all': True},
                  target_CX16_required_not_executed=True)
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

    def data_limits():
        bounds = recipe['helper_limits']
        resource.setrlimit(resource.RLIMIT_AS, (bounds['address_space_bytes'],)*2)
        resource.setrlimit(resource.RLIMIT_CPU, (bounds['cpu_seconds'],)*2)

    def run(command, kind='loader link'):
        row = dict(command=command, kind=kind, cwd=str(out), pid=None, terminal=False, EOF_drained=False)
        report['commands'].append(row)
        process = None
        save()
        try:
            diagnostic = kind == 'existing positive DATA decode'
            process = subprocess.Popen(command, cwd=out, env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
                preexec_fn=data_limits if diagnostic else None)
            row['pid'] = process.pid
            report['live_handles'] = [process.pid]
            save()
            stdout, stderr = process.communicate(timeout=recipe['helper_limits']['wall_seconds'] if diagnostic else 120)
            row.update(stdout=stdout, stderr=stderr, returncode=process.returncode,
                       terminal=True, EOF_drained=True, group_absent=absent(process.pid))
            require(process.returncode == 0 and row['group_absent'], 'tool/helper failed or owned group remains')
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

    def interrupted(signum, _frame):
        raise InterruptedError('signal '+str(signum))

    previous = {s: signal.signal(s, interrupted) for s in (signal.SIGINT, signal.SIGTERM)}
    save()
    try:
        for form, expected in recipe['native_expected'].items():
            old = recipe['controls'][form]
            old_whole = Path(old['whole_path']).read_bytes()
            require((len(old_whole), sha(old_whole)) == (old['whole_bytes'], old['whole_sha256']),
                    'actual immutable control whole differs')
            native = Path(expected['native_path']).read_bytes()
            layout = packer.admit(native, expected, sha)
            model = codec.load_models((HERE/'loader/models.json').read_bytes(), form)
            require(model[0] == expected['model_wmask'], 'unchanged fixed model differs')
            local = out/form
            local.mkdir()
            report['candidate_encodes'] += 1
            save()
            payload, encoding = codec.encode_native(native, model)
            require(encoding['format'] == recipe['codec'] and encoding['header_bytes'] == 21,
                    'fixed21 packet format differs')
            report['loader_links'] += 1
            built = packer.compile_loader(local/'whole', HERE/'loader', payload, layout,
                        recipe['loader_flags'], run, sha, model_wmask=model[0])
            raw = Path(built['path']).read_bytes()
            require(raw[-len(payload):] == payload and packer.stripped_loader(raw) == raw,
                    'actual complete whole/payload layout differs')
            row = dict(form=form, native_bytes=len(native), native_sha256=sha(native), layout=layout,
                       encoding=encoding, whole=built, whole_program_headers=packer.elf(raw),
                       whole_delta=len(raw)-old['whole_bytes'])
            report['forms'].append(row)
            save()
            diag = local/'data-decode'
            diag.mkdir()
            pin = recipe['helpers'][form]
            helper_raw = Path(pin['path']).read_bytes()
            require((len(helper_raw), sha(helper_raw)) == (pin['bytes'], pin['sha256']), 'DATA helper changed')
            helper = diag/'check'
            helper.write_bytes(helper_raw)
            helper.chmod(0o755)
            require(sha(helper.read_bytes()) == pin['sha256'], 'owned copied DATA helper differs')
            report['reused_positive_DATA_helper_runs'] += 1
            checked = run([str(helper), str(local/'whole/payload.bin'), expected['native_path'],
                           str(diag/'decoded.bcj'), str(diag/'decoded.native')], 'existing positive DATA decode')
            decode = json.loads(checked['stdout'])
            require(decode['complete'] and decode['decode_status'] == 0 and decode['bytes'] == len(native)
                    and decode['packet_bytes'] == len(payload) and all(decode[name] for name in
                    ('bcj_exact', 'native_exact', 'output_canaries', 'table_munmap')), 'DATA decoder proof failed')
            decoded = (diag/'decoded.native').read_bytes()
            decoded_bcj = (diag/'decoded.bcj').read_bytes()
            require(decoded == native and decoded_bcj == codec.bcj(native), 'complete decoded DATA bytes differ')
            row.update(DATA_diagnostic=decode, decoded_native_sha256=sha(decoded), decoded_BCJ_sha256=sha(decoded_bcj),
                       reused_DATA_helper_sha256=pin['sha256'], DATA_helper_limits=recipe['helper_limits'])
            save()
            print(json.dumps(dict(form=form, native=len(native), whole=len(raw), delta=row['whole_delta'])), flush=True)
        require(report['candidate_encodes'] == report['loader_links'] == report['reused_positive_DATA_helper_runs'] == 2
                and not report['live_handles'], 'bounded whole/data phase incomplete')
        for source in sources:
            require(sha((HERE/source['path']).read_bytes()) == source['sha256'], 'own source changed during cost')
        report['complete'] = True
    except BaseException as error:
        report['first_failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        save()
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    print(json.dumps(dict(out=str(out), complete=report['complete'], forms=[dict(form=r['form'],
        whole_bytes=r['whole']['bytes'], whole_sha256=r['whole']['sha256'], whole_delta=r['whole_delta'],
        packet_bytes=r['whole']['payload_bytes'], nonpacket_bytes=r['whole']['loader_and_headers_bytes'])
        for r in report['forms']], live_handles=report['live_handles'])))


if __name__ == '__main__':
    main()
