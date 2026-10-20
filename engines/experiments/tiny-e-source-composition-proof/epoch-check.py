#!/usr/bin/env python3
"""One bounded E DEV0 production epoch/reset witness using frozen F assertions.

Actual GO/result/position/clock bodies are included unchanged. Per-job reset is
witnessed by quiescent sentinel writes and the current worker's own first claim
clock read. This is no public UCI reset, TT-clear, shipping-image or race proof.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CANDIDATE = 'c5f005b107f5d3fa93a4043fece78de848e248e67c4e58831a688efae8f2941d'
OLD = '0a7fe69022051e1893ffbd52ade7a2fbb3f342fe20b581bb786d6997b46fb712'
GENERATOR = '2f6112ce64a0c73abec6ffbd64ae69a495f116d9fcedfeb37870d4207c61363e'
SUPPORT = '10cffa19a48b3d604fe22dfff468af27f2e01d30d86a1e39e2b5e410cf9df30e'
INPUTS = '6c087b741124bc9ac5c311de1c19f6ad17ce341af10d13c5b1a5222251aa38f5'
PREFIX = 'edd3076de238d6555b48b85b950fcf9351cb186b8cdb270c838a8a39fe957f05'
ASSERTIONS = '491fb666e81cf22219b98196aa81dc1c3def9db65cb65672ec1acd662930ee88'
ORACLE = 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8'
CONTRACT = '5cfb16f14bca8f3933f73c698101d32a17f22cbb375ba082ae009cf5164f4cc1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def admit(root):
    candidate = (root / 'candidate.c').read_bytes()
    old = (root / 'control/engines/compact/tiny-entry-e/engine.c').read_bytes()
    require(sha(candidate) == CANDIDATE and sha(old) == OLD
            and sha((root / 'generate.py').read_bytes()) == GENERATOR,
            'E production source/generator literal identity changed')
    generator = module('epoch_E_frozen_generator', root / 'generate.py')
    require(len(generator.EDITS) == 8 and generator.readable(old) == candidate,
            'exact eight-site E composition changed')
    forward, stages = old, []
    for before, after in generator.EDITS:
        require(forward.count(before) == 1, 'old E composition site is not unique')
        position = forward.index(before)
        stages.append((position, before, after))
        forward = forward[:position] + after + forward[position + len(before):]
    require(forward == candidate, 'recorded E forward composition differs')
    reverse = candidate
    for position, before, after in reversed(stages):
        require(reverse[position:position + len(after)] == after, 'E inverse slice differs')
        reverse = reverse[:position] + before + reverse[position + len(after):]
    require(reverse == old, 'E composition inverse differs')
    marker = b'void think(Worker *w,const Board *p)'
    require(old.count(marker) == candidate.count(marker) == 1, 'E think marker count differs')
    prefix = old[:old.index(marker)]
    require(len(prefix) == 18042 and sha(prefix) == PREFIX
            and prefix == candidate[:candidate.index(marker)], 'E model/Board/search prefix changed')
    start, end = b'    w->length=game_length;', b'static pthread_mutex_t mutex='
    driver = old[old.index(start):old.index(end)]
    require(driver == candidate[candidate.index(start):candidate.index(end)], 'E PVS driver changed')
    return {'candidate_sha256': CANDIDATE, 'control_sha256': OLD,
            'exact_literal_sites': 8, 'exact_forward_and_inverse': True,
            'unchanged_prefix_bytes': len(prefix), 'unchanged_prefix_sha256': PREFIX,
            'model_board_search_prefix_byte_identical': True,
            'PVS_driver_after_job_reset_byte_identical': True}


def validate_reset(events, assertions):
    publications = {row['epoch']: row for row in events if row['event'] == 'go_publication'}
    results = {row['epoch']: row for row in events if row['event'] == 'actual_result'}
    summaries = [row for row in events if row['event'] == 'worker_fields_seeded']
    seeds = [row for row in events if row['event'] == 'worker_field_seed']
    observations = [row for row in events if row['event'] == 'worker_first_claim_reset']
    require([row['next_epoch'] for row in summaries] == [1, 3], 'reset seed epoch inventory differs')
    require(len(seeds) == 4 and observations, 'reset witness inventory is empty or differs')
    witnessed = []
    for summary in summaries:
        epoch = summary['next_epoch']
        require(summary['epoch'] == epoch - 1 and summary['pending'] == 0
                and summary['results'] == epoch - 1 and summary['workers'] == 2,
                'worker sentinel write was not at an actual quiescent boundary')
        actual_seeds = [row for row in seeds if row['next_epoch'] == epoch]
        require([row['worker'] for row in actual_seeds] == [0, 1], 'sentinel worker inventory differs')
        for row in actual_seeds:
            worker = row['worker']
            require(row['pending'] == 0 and row['epoch'] == epoch - 1 and row['id'] == worker
                    and row['nodes'] == 123456789 + worker and row['depth'] == 91 + worker
                    and row['score'] == 12345 + worker and row['best'] == ((16 + worker) << 7)
                    and row['length'] == 7 + worker
                    and row['key0'] == f'{0x5a5aa5a501234567 + worker:016x}'
                    and row['seq'] < summary['seq'] < publications[epoch]['seq'],
                    'actual worker sentinel values or seed/publication order differ')
        rows = [row for row in observations if row['epoch'] == epoch]
        require(rows and len({row['worker'] for row in rows}) == len(rows),
                'no actual first-claim reset observation or duplicate worker observation')
        for row in rows:
            require(row['seeded_epoch'] == epoch and row['worker'] in [0, 1]
                    and row['id'] == row['worker']
                    and row['nodes'] == row['depth'] == row['score'] == row['best'] == 0
                    and row['length'] == row['game_length'] == 1 and row['history_matches']
                    and publications[epoch]['seq'] < row['seq'] < results[epoch]['seq'],
                    'E owner-worker first claim did not observe actual reset/history copy')
        witnessed.append({'epoch': epoch, 'seeded_workers': 2,
                          'owner_workers_observed_at_first_claim': [row['worker'] for row in rows],
                          'nodes_before_claim_increment': 0, 'reset_fields_zero': True,
                          'actual_history_copy_matches': True})
    require(all(row['epoch'] in [1, 3] for row in observations), 'unexpected reset-observation epoch')
    # Frozen F validation refers to controller pool snapshots. The E addition
    # also reads each clock-calling worker's own fields while it owns the job.
    require(assertions.pop('worker_fields_read_only_after_pending_zero') is True,
            'frozen controller snapshot boundary assertion changed')
    assertions.update(controller_worker_pool_reads_only_after_pending_zero=True,
                      owner_worker_reads_own_fields_at_first_claim=True,
                      per_job_reset_witnesses=witnessed,
                      reset_scope='actual think per-job reset; not public UCI reset or TT clear',
                      unobserved_worker_first_claim_reset='not claimed')
    return assertions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p / '.git').exists() for p in (out, *out.parents)):
        parser.error('new absolute external output outside Git required')
    out.mkdir(parents=True)
    frozen = out / 'frozen'
    frozen.mkdir()
    report = {'complete': False, 'passed': False, 'scope': __doc__, 'inputs': {},
              'engine_whole_executions': 0, 'diagnostic_executions': 0,
              'diagnostic_execution_attempts': 0,
              'profile': {'DEV': 0, 'workers': 2, 'tt_bits': 18, 'ISA': 'generic x86-64; no AVX2 flag'},
              'excluded': ['shipping image proof', 'old engine execution', 'broad model/search matrix',
                           'public UCI reset', 'TT-clear proof', 'broad fault injection',
                           'join-failure safety', 'SAN/TSAN', 'performance', 'variant sweep']}
    tools = None

    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    save()
    try:
        manifest_raw = (HERE / 'inputs.json').read_bytes()
        require(sha(manifest_raw) == INPUTS and b'\r' not in manifest_raw, 'literal E proof closure changed')
        manifest = json.loads(manifest_raw)
        for prefix, key in [('control', 'control_files'), ('reference', 'reference_files')]:
            for name, pin in manifest[key].items():
                raw = (HERE / prefix / name).read_bytes()
                require(b'\r' not in raw and len(raw) == pin['bytes'] and sha(raw) == pin['sha256'],
                        'frozen E proof input changed: ' + prefix + '/' + name)
                target = frozen / prefix / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                report['inputs'][prefix + '/' + name] = {'bytes': len(raw), 'raw_sha256': sha(raw)}
                save()
        for name in ['epoch-check.py', 'epoch-contract.c', 'inputs.json']:
            raw = manifest_raw if name == 'inputs.json' else (HERE / name).read_bytes()
            require(b'\r' not in raw, 'owned epoch source must use raw LF')
            (frozen / name).write_bytes(raw)
            report['inputs'][name] = {'bytes': len(raw), 'raw_sha256': sha(raw)}
            save()
        require(sha((frozen / 'epoch-contract.c').read_bytes()) == CONTRACT,
                'owned E epoch diagnostic source changed')
        report['source_transform'] = admit(frozen / 'control')
        require(sha((frozen / 'control/support.py').read_bytes()) == SUPPORT, 'owned C support changed')
        assertion_path = frozen / 'reference/engines/experiments/tiny-f-source-composition-proof/epoch-check.py'
        require(sha(assertion_path.read_bytes()) == ASSERTIONS, 'frozen F epoch assertions changed')
        oracle_path = frozen / 'control/control/engines/tests/chess_oracle.py'
        require(sha(oracle_path.read_bytes()) == ORACLE, 'independent legal oracle changed')
        reference = module('epoch_E_frozen_F_assertions', assertion_path)
        reference.CANDIDATE = CANDIDATE
        tools = module('epoch_E_owned_C_support', frozen / 'control/support.py')
        oracle = module('epoch_E_oracle', oracle_path)
        command = ['cc', '-std=c11', '-O2', '-pthread', '-DDEV=0', '-DWORKERS=2', '-DTT_BITS=18',
                   '-DPRODUCTION_SOURCE="' + str(frozen / 'control/candidate.c') + '"',
                   str(frozen / 'epoch-contract.c'), '-o', str(out / 'epoch-contract')]
        report.update(compile_command=command, included_production_text_unchanged=True,
                      assertion_reuse='frozen F validate only; CANDIDATE set to literal E; no F admit/main execution',
                      diagnostic_interposition=['actual clock value unchanged, bounded scheduling gate',
                                                'actual publication/result/positive-pending wait observations',
                                                'quiescent worker sentinels and owner-worker first-clock reset observation'])
        save()
        result = tools.run(command, out, timeout=90)
        (out / 'compile.stdout').write_bytes(result.stdout)
        (out / 'compile.stderr').write_bytes(result.stderr)
        report.update(compile_returncode=result.returncode, tool_commands=tools.COMMANDS)
        require(result.returncode == 0, 'E epoch diagnostic compile failed; logs preserved')
        report['diagnostic_native_sha256'] = sha((out / 'epoch-contract').read_bytes())
        report['diagnostic_execution_attempts'] = 1
        save()
        result = tools.run([str(out / 'epoch-contract')], out, timeout=12)
        report['diagnostic_executions'] = 1
        (out / 'stdout.txt').write_bytes(result.stdout)
        (out / 'stderr.jsonl').write_bytes(result.stderr)
        report.update(returncode=result.returncode, tool_commands=tools.COMMANDS)
        save()
        require(result.returncode == 0, 'E actual epoch diagnostic failed; logs preserved')
        require(len(result.stdout) + len(result.stderr) < 1024 * 1024, 'bounded fixture output exceeded 1 MiB')
        events = [json.loads(line) for line in result.stderr.decode().splitlines()]
        assertions = reference.validate(events, result.stdout.decode().splitlines(), oracle)
        report['assertions'] = validate_reset(events, assertions)
        require(all(row['terminal'] and row['group_absent'] and row['returncode'] == 0 for row in tools.COMMANDS),
                'owned groups did not settle successfully')
        report.update(complete=True, passed=True, owned_live_handles=0,
                      stdout_sha256=sha(result.stdout), stderr_sha256=sha(result.stderr))
        save()
        print(json.dumps({'complete': report['complete'], 'results': str(out / 'results.json'),
                          'sha256': sha((out / 'results.json').read_bytes())}), flush=True)
    except BaseException as error:
        report['complete'] = False
        report['passed'] = False
        if tools is not None:
            report['tool_commands'] = tools.COMMANDS
            report['diagnostic_executions'] = sum(
                row['command'] == [str(out / 'epoch-contract')] for row in tools.COMMANDS)
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        save()
        raise


if __name__ == '__main__':
    main()
