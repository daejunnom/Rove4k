#!/usr/bin/env python3
"""One fixed LVA-ordering native/ALONE cost; never execute the bootstrap/engine."""
import argparse
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import signal
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def info(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def need(value, message):
    if not value:
        raise ValueError(message)


def group_exists(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    need(args.out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)), 'fresh absolute non-Git output required')
    recipe_raw = (HERE/'recipe.json').read_bytes()
    recipe = json.loads(recipe_raw)
    need(recipe['cost_authorized'] is True, 'this sole first cost requires explicit authorization')
    base = Path(recipe['actual_cost_baseline'])

    def inputs():
        for name, pin in recipe['owned_executable_pins'].items():
            need(info((HERE/name).read_bytes()) == pin, 'owned executable changed: '+name)
        for name, pin in recipe['actual_cost_baseline_pins'].items():
            need(info((base/name).read_bytes()) == pin, 'fixed actual baseline changed: '+name)

    inputs()
    out.mkdir(parents=True)
    report = {'complete': False, 'scope': 'one combined legal-LVA ordering first cost after accepted B input profile',
        'recipe': info(recipe_raw), 'producer': info(Path(__file__).read_bytes()),
        'baseline_path': str(base), 'baseline_read_only': recipe['actual_cost_baseline_pins'],
        'baseline_cost_receipt_metadata': recipe['accepted_baseline_receipt_metadata_only'],
        'compiler': recipe['compiler'], 'profile': recipe['profile'], 'compression': recipe['compression'],
        'control_compile': 0, 'control_compress': 0, 'control_copy': 0,
        'candidate_compile': 0, 'candidate_ALONE': 0, 'strict_pure_decodes': 0,
        'C_AST': 0, 'standalone_PP': 0, 'bootstrap_execution': 0, 'engine_or_oracle_execution': 0,
        'DEV': 0, 'games_benchmarks': 0, 'sweep_retry': 0, 'repeat_claim': False,
        'policy_changed': True, 'full_minimax_equivalence': False, 'QS_SEE_pruning_disabled': True,
        'functional_strength_stack_qualified': False, 'normal_promotion': False,
        'old_minimax_DEV_visits_stack_evidence_inherited': False, 'metadata_exception_applied': False}
    proc = None

    def save():
        (out/'cost.json').write_text(json.dumps(report, indent=2)+'\n')

    save()
    try:
        source = (base/'main.c').read_bytes()
        spec = importlib.util.spec_from_file_location('fixed_LVA_cost_transform', HERE/'transform.py')
        transform = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transform)
        candidate, metadata = transform.transform(source, recipe['literal_domain'])
        need(info(candidate) == recipe['output_pin'], 'fixed candidate differs')
        report.update(source=info(candidate), source_delta_from_input=len(candidate)-len(source), transform=metadata)
        (out/'main.c').write_bytes(candidate)

        def literal(data):
            data.decode('ascii')
            need(b"'''" not in data, 'fixed raw-single source domain differs')
            return b"r'''"+data+b"'''.encode()"

        old_literal, new_literal = literal(source), literal(candidate)
        old_script = (base/'bootstrap.py').read_bytes()
        need(old_script.count(old_literal) == 1 and old_script.count(new_literal) == 0, 'baseline raw-single source binding differs')
        script = old_script.replace(old_literal, new_literal, 1)
        need(script.count(new_literal) == 1 and script.replace(new_literal, old_literal, 1) == old_script, 'bootstrap inverse differs')
        argv_literal = ('subprocess.Popen('+repr(recipe['compiler'])+',').encode()
        need(old_script.count(argv_literal) == script.count(argv_literal) == 1, 'literal compiler argv differs')
        old_whole = (base/'x').read_bytes()
        prefix = recipe['prefix'].encode('ascii')
        need(len(prefix) == 77 and old_whole[:77] == prefix, 'fixed 77-byte launcher differs')

        def decode(whole, expected):
            need(whole[:77] == prefix and whole[77:90].hex() == recipe['ALONE_header13'], 'fixed prefix/header differs')
            decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
            decoded = decoder.decompress(whole[77:], max_length=len(expected)+1)
            need(decoded == expected and decoder.eof and not decoder.unused_data and decoder.check == lzma.CHECK_NONE, 'strict sole-stream decode differs')
            report['strict_pure_decodes'] += 1

        decode(old_whole, old_script)
        (out/'bootstrap.py').write_bytes(script)
        native_dir = out/'native'
        native_dir.mkdir()
        env = os.environ.copy()
        env['TMPDIR'] = str(native_dir)
        report.update(candidate_compile=1, compiler_stdin=info(candidate), private_cwd=str(native_dir), compile_timeout_seconds=90)
        save()
        proc = subprocess.Popen(recipe['compiler'], cwd=native_dir, env=env, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        report['compiler_pid_pgid'] = proc.pid
        try:
            stdout, stderr = proc.communicate(candidate, timeout=90)
        except subprocess.TimeoutExpired:
            report['compile_timeout'] = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = proc.communicate()
            raise
        finally:
            if proc.poll() is not None:
                report['compiler_returncode'] = proc.returncode
        (out/'compiler.stdout').write_bytes(stdout)
        (out/'compiler.stderr').write_bytes(stderr)
        report['group_present_after_reap'] = group_exists(proc.pid)
        need(proc.returncode == 0 and not report['group_present_after_reap'], 'compiler failed or owned process group remains')
        native = (native_dir/'x').read_bytes()
        old_native = (base/'native/x').read_bytes()
        report.update(native=info(native), full_baseline_native_equal=native == old_native,
                      first_native_difference=next((i for i, (a, b) in enumerate(zip(native, old_native)) if a != b), None))
        report['candidate_ALONE'] = 1
        save()
        payload = lzma.compress(script, format=lzma.FORMAT_ALONE, check=lzma.CHECK_NONE,
            filters=[{'id': lzma.FILTER_LZMA1, 'preset': 9|lzma.PRESET_EXTREME,
                      'lc': 2, 'lp': 0, 'pb': 0, 'mf': lzma.MF_BT4, 'dict_size': 67108864, 'nice_len': 32}])
        whole = prefix+payload
        (out/'x').write_bytes(whole)
        decode(whole, script)
        inputs()
        delta = len(whole)-len(old_whole)
        report.update(complete=True, bootstrap=info(script), whole=info(whole),
            whole_delta_from_input5461=delta, whole_delta_from_prior_B5546=len(whole)-5546,
            gap_to_4096=len(whole)-4096,
            disposition='positive; report before functional' if delta < 0 else 'tie/loss; stop',
            argv_source_literal_exact=True, bootstrap_literal_inverse=True, live_owned_group=False,
            live_command_handles=0)
        save()
        print(json.dumps({k: report[k] for k in ('complete', 'source', 'native', 'full_baseline_native_equal', 'whole', 'whole_delta_from_input5461', 'whole_delta_from_prior_B5546', 'disposition')}), flush=True)
    except BaseException as error:
        report['failure'] = repr(error)
        if proc is not None:
            if group_exists(proc.pid):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            stdout, stderr = proc.communicate()
            (out/'compiler.stdout').write_bytes(stdout)
            (out/'compiler.stderr').write_bytes(stderr)
            report.update(compiler_returncode=proc.returncode, group_present_after_cleanup=group_exists(proc.pid))
        report['live_command_handles'] = 0
        save()
        raise


if __name__ == '__main__':
    main()
