"""C/E source-bound evidence reuse and one bounded C core regression.

This is not a shipping protocol validator. The common portfolio gate owns fresh
whole-wrapper policy/lifecycle observations. Historical native search activity
is reused only through exact source and unchanged non-policy bytes, with the
old and new executable identities kept separate.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


HOME = Path('/home/stemxstudio')
C_QUAL = HOME / 'rove4k-tiny-c-table-qualification-20261020'
C_CAMPAIGN = HOME / 'rove4k-tiny-c-table-campaign-20261020'
E_ROOT = HOME / 'rove4k-tiny-e-state-20261020-evidence/final2'
PINS = {
    'C': {'report': 'fc2eed0df7e29a4455a5f154fc7d33c7782120fb4330c055a5795918d5671dcc',
          'readable': '8d951ec4e451bccf89064f30aaead77e49410017d825536d65c9c7e39a4cdb96',
          'old_dev': 'fabb555a7d76875771ea5d7f761165c2a7c332a2bd50f498ab916e47457aa021'},
    'E': {'report': '55e72d5c2ebf3644006d1aceb4c8c7be66082f62c994881798a0d55be3eb0b86',
          'readable': '09e67b5a2b4b17f04f08eebeb1b70421eb47eb235f7027099d1ff8ad5173b5e1',
          'old_dev': 'd4937e4d6ab310d19dc5b1504a157c46ed89ebc8efe096335091847b021787cd'},
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def safe_relative(name):
    path = Path(name)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in name,
            'unsafe archived relative path')
    return path


def positive_search(result, ordering):
    require(result['workers'] == 2 and result['total_threads'] == 3 and result['completed_depth'] >= 4,
            'historical completed fixed-worker search missing')
    for key in ('leaf_calls', 'pvs', 'qs', 'history_updates', 'continuation_updates',
                'correction_updates', 'correction_uses'):
        require(result[key] > 0, 'missing historical positive counter: ' + key)
    require((result['ordering_calls'] > 0) if ordering else result['ordering_calls'] == 0,
            'historical model ordering counter differs')


C_CORE = r'''#define main portfolio_engine_main
#include "minimal.c"
#undef main
#include <assert.h>

static Worker fixture_worker;
static void reset_fixture(Board *p){
    clear();memset(&fixture_worker,0,sizeof fixture_worker);start(p);
    fixture_worker.length=1;fixture_worker.keys[0]=p->h;
    deadline=UINT64_MAX;limit=0;atomic_store(&searched,0);atomic_store(&stopped,0);
}
int main(void){
    table=calloc(1u<<TT_BITS,sizeof *table);assert(table);
    Board p,q;Worker *w=&fixture_worker;Move best=0;
    reset_fixture(&p);
    uint64_t key=p.h^mix(p.r+(unsigned)p.half);
    uint64_t data=((uint64_t)27123<<17)|((uint64_t)10<<33)|((uint64_t)1<<41);
    probe(key,1,data);assert(probe(key,0,0)==data);
    assert(probe(key+((uint64_t)1<<TT_BITS),0,0)==0);
    assert(search(w,&p,1,-MATE,MATE,1,0,0)==27123);
    q=p;q.half++;assert((q.h^mix(q.r+(unsigned)q.half))!=key);
    memset(w,0,sizeof *w);w->length=1;w->keys[0]=q.h;
    assert(search(w,&q,1,-MATE,MATE,1,0,0)!=27123);
    clear();probe(key,1,data);q=p;q.r++;assert((q.h^mix(q.r+(unsigned)q.half))!=key);
    memset(w,0,sizeof *w);w->length=1;w->keys[0]=q.h;
    assert(search(w,&q,1,-MATE,MATE,1,0,0)!=27123);

    reset_fixture(&p);w->length=5;w->keys[0]=w->keys[2]=w->keys[4]=p.h;p.half=4;
    assert(search(w,&p,1,-MATE,MATE,0,0,&best)==0);
    assert(w->nodes==1&&!atomic_load(&stopped));
    reset_fixture(&p);w->length=3;w->keys[0]=w->keys[2]=p.h;p.half=4;
    best=0;search(w,&p,1,-MATE,MATE,0,0,&best);assert(best&&w->nodes>1);
    reset_fixture(&p);p.half=100;
    assert(search(w,&p,1,-MATE,MATE,0,0,&best)==0&&!atomic_load(&stopped));
    memset(&p,0,sizeof p);p.s=-1;p.e=-1;p.half=100;
    put(&p,119,-6);put(&p,102,5);put(&p,85,6);ep(&p);p.h^=state(&p);p.r=p.h;
    w->length=1;w->keys[0]=p.h;
    assert(search(w,&p,1,-MATE,MATE,0,0,&best)==-MATE);

    reset_fixture(&p);max_depth=2;game_length=1;game_keys[0]=p.h;think(w,&p);
    assert(w->depth==2&&w->best&&!atomic_load(&stopped));
    int completed_depth=w->depth,completed_score=w->score;Move completed_best=w->best;
    w->length=1;w->keys[0]=p.h;uint64_t aborts=w->ply_aborts;
    assert(search(w,&p,1,-MATE,MATE,PLY-1,0,0)==0&&atomic_load(&stopped));
    assert(w->ply_aborts==aborts+1&&w->depth==completed_depth&&
           w->score==completed_score&&w->best==completed_best);

    reset_fixture(&p);
    assert(fen(&p,"4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1"));
    w->length=1;w->keys[0]=p.h;Move ep_move=MOVE(68,83,0);
    assert(p.e==83&&capture(&p,ep_move)&&!PROMO(ep_move));
    best=0;search(w,&p,1,-MATE,MATE,0,0,&best);
    assert(!atomic_load(&stopped)&&best==ep_move&&w->corr_updates==0);
    free(table);
    puts("{\"full_key_collision_miss\":true,\"halfmove_context_search_miss\":true,"
         "\"reversible_context_search_miss\":true,\"third_visit_only\":true,"
         "\"halfmove_draw\":true,\"mate_precedence\":true,\"live_ply_abort\":true,"
         "\"completed_worker_fields_preserved\":true,\"ep_capture_correction_excluded\":true}");
    return 0;
}
'''


def verify(family, family_build, out):
    require(family in PINS, 'C/E proof admits only C or E')
    family_build = Path(family_build).resolve(strict=True)
    out = Path(out)
    require(out.is_absolute(), 'new absolute external output required')
    out = out.resolve()
    require(not out.exists() and not any((p / '.git').exists() for p in (out, *out.parents)),
            'new output outside Git required')
    out.mkdir(parents=True)
    frozen = out / 'frozen'
    frozen.mkdir()
    report = {'passed': False, 'family': family, 'fresh_whole_wrapper_runtime': False,
              'scope': 'unchanged readable-body historical evidence reuse; C adds direct actual-source core fixture',
              'input_sha256': {}, 'source_origins': {}, 'historical_receipts': {},
              'scope_limits': [
                  'Historical positive searches describe the recorded old DEV native images.',
                  'Reuse is through exact original readable bytes and identical bytes outside go/main.',
                  'New portfolio DEV is identical between baseline/minimal, not asserted identical to old DEV.',
                  'No elapsed-time search, strength, high-worker-count or 4096-byte eligibility claim.',
                  'Fresh common whole-wrapper policy/lifecycle qualification is separate.',
              ]}

    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')

    def freeze(path, name, expected=None):
        data = Path(path).read_bytes()
        digest = sha(data)
        require(expected is None or digest == expected, 'source/receipt hash drift: ' + str(path))
        target = frozen / safe_relative(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        require(not target.exists(), 'duplicate frozen input: ' + name)
        target.write_bytes(data)
        report['input_sha256'][name] = digest
        report['source_origins'][name] = str(path)
        return data

    save()
    try:
        freeze(Path(__file__), 'proof_ce.py')
        raw = freeze(family_build, 'family-build.json')
        build = json.loads(raw)
        report['build_sha256'] = sha(raw)
        require(build['complete'] and build['family'] == family and
                build['resources'] == {'workers': 2, 'startup_threads': 3, 'tt_bits': 18},
                'incomplete or changed family/resource manifest')
        require(build['controls']['qualified_control_report_sha256'] == PINS[family]['report'],
                'unknown old qualified control')
        archive = family_build.parent.parent / 'recipe'
        # All declared inputs are checked before importing the saved helper code.
        for name, expected in build['input_sha256'].items():
            freeze(archive / safe_relative(name), 'producer/' + name, expected)
        for name, expected in build['tooling_sha256'].items():
            freeze(archive / safe_relative(name), 'producer-tools/' + name, expected)
        transform = load('ce_proof_policy_' + family, frozen / 'producer-tools/transform.py')
        adapter = load('ce_proof_adapter_' + family, frozen / 'producer-tools/family_ce.py')
        records = {entry['id']: entry for entry in build['engines']}
        require(set(records) == {'baseline', 'minimal'}, 'unexpected policy forms')
        readable = {}
        for form, entry in records.items():
            readable[form] = freeze(entry['readable'], form + '/combined.c', entry['readable_sha256'])
            freeze(entry['source'], form + '/main.c', entry['source_sha256'])
            freeze(entry['native'], form + '/native', entry['native_sha256'])
            freeze(entry['command'][0], form + '/wrapper', entry['whole_sha256'])
            freeze(entry['dev'], form + '/dev-native', entry['dev_native_sha256'])
            freeze(Path(entry['dev']).parent / 'main.c', form + '/dev-source.c', entry['dev_source_sha256'])
        require(sha(readable['baseline']) == PINS[family]['readable'], 'unknown qualified readable bytes')
        original = (frozen / 'producer' / ('family-' + family) / 'original/main.c').read_bytes()
        require(original == readable['baseline'], 'baseline differs from qualified original readable')
        expected, policy = transform.transform(readable['baseline'], family)
        require(expected == readable['minimal'] and policy == build['policy'], 'actual policy output differs')
        protected = transform.protected_bytes(readable['baseline'])
        require(transform.protected_bytes(readable['minimal']) == protected,
                'global/type/helper/feature bytes outside policy changed')
        maps = [{name: adapter.body(data, name) for name in build['controls']['protected_function_sha256']}
                for data in (readable['baseline'], readable['minimal'])]
        require(maps[0] == maps[1] == build['controls']['protected_function_sha256'],
                'protected function body map differs')
        require(records['baseline']['compile'] == records['minimal']['compile'] and
                records['baseline']['dev_compile'] == records['minimal']['dev_compile'],
                'compiler/resources changed with policy')
        require((frozen / 'baseline/dev-source.c').read_bytes() == (frozen / 'minimal/dev-source.c').read_bytes()
                and (frozen / 'baseline/dev-native').read_bytes() == (frozen / 'minimal/dev-native').read_bytes(),
                'DEV bytes changed with policy')
        report['source_binding'] = {
            'old_readable_sha256': sha(original),
            'minimal_readable_sha256': sha(readable['minimal']),
            'all_bytes_outside_go_main_identical': True,
            'protected_bytes': len(protected), 'protected_sha256': sha(protected),
            'protected_function_sha256': maps[0], 'exact_expected_policy_transform': True,
            'DEV_baseline_minimal_source_native_identical': True,
            'historical_DEV_native_sha256': PINS[family]['old_dev'],
            'new_DEV_native_sha256': records['minimal']['dev_native_sha256'],
            'historical_new_DEV_native_identical': PINS[family]['old_dev'] == records['minimal']['dev_native_sha256'],
        }
        old_dev = frozen / 'producer' / ('family-' + family) / 'dev/x'
        require(sha(old_dev.read_bytes()) == PINS[family]['old_dev'], 'old DEV binary identity differs')

        if family == 'C':
            data = freeze(C_QUAL / 'results.json', 'receipts/c-qualification.json',
                          '61191a1c32205fec01db087e43ce8d60c0c1f0efb0af712556bdcaefe195bf1a')
            qual = json.loads(data)
            require(qual['passed'], 'C historical qualification failed')
            candidates = [row for row in qual['candidates'] if row['representation'] == 'startup']
            require(len(candidates) == 1, 'C startup qualification missing')
            candidate = candidates[0]
            require(candidate['producer_source_sha256'] == sha(original), 'C receipt source differs')
            freeze(C_QUAL / 'startup/actual-production-contract.c', 'receipts/c-production-contract.c',
                   candidate['harness_sha256'])
            freeze(C_CAMPAIGN / 'frozen/engines/experiments/tiny-c-table/table_contract.c',
                   'receipts/c-table-contract.c', qual['fixture_sha256'])
            require(candidate['actual_search']['program_sha256'] == PINS['C']['old_dev'],
                    'C actual search native differs')
            positive_search(candidate['actual_search']['search'], False)
            for row in candidate['parity']:
                result = row['result']
                require(result['parity'] and result['board_preserved'] and result['init_calls'] == 1 and
                        result['positions'] == 369255 and result['avx2_leaf_calls'] == 738510 and
                        result['table_terms'] == 832 and result['table_bytes'] == 3328 and
                        row['actual_table_i32le_sha256'] ==
                        '172c6eac2478f596fef4d0cc78a1ba644ae8bce06b4e5fd4258310713f49ae1c',
                        'C historical table parity differs')
            require({row['kind'] for row in candidate['parity']} == {'optimized', 'asan-ubsan'},
                    'C parity run forms differ')
            report['historical_receipts']['C_SIMD'] = {
                'receipt_sha256': sha(data), 'actual_search': candidate['actual_search']['search'],
                'parity': [row['result'] for row in candidate['parity']],
                'reuse': 'identical original readable and all non-policy source bytes; old executable activity',
            }
            fixture = out / 'c-core'
            fixture.mkdir()
            (fixture / 'minimal.c').write_bytes(readable['minimal'])
            (fixture / 'contract.c').write_text(C_CORE)
            command = ['cc', '-std=c11', '-O2', '-pthread', '-DWORKERS=2', '-DTT_BITS=18',
                       '-DDEV=1', '-mavx2', 'contract.c', '-o', 'x']
            result = subprocess.run(command, cwd=fixture, capture_output=True, timeout=60)
            (fixture / 'compile.stdout').write_bytes(result.stdout)
            (fixture / 'compile.stderr').write_bytes(result.stderr)
            require(result.returncode == 0, 'C direct actual-source fixture compilation failed')
            result = subprocess.run([str(fixture / 'x')], cwd=fixture, capture_output=True, timeout=20)
            (fixture / 'runtime.stdout').write_bytes(result.stdout)
            (fixture / 'runtime.stderr').write_bytes(result.stderr)
            require(result.returncode == 0, 'C direct actual-source core fixture failed')
            cases = json.loads(result.stdout)
            require(len(cases) == 9 and all(value is True for value in cases.values()),
                    'C direct fixture result differs')
            report['fresh_C_core'] = {
                'compile': command, 'compiler': subprocess.check_output(['cc', '--version'], text=True).splitlines()[0],
                'minimal_readable_sha256': sha(readable['minimal']),
                'fixture_sha256': sha((fixture / 'contract.c').read_bytes()),
                'program_sha256': sha((fixture / 'x').read_bytes()), 'cases': cases,
                'scope': 'direct DEV actual-source calls, no created workers or physical UCI dispatch',
                'completed_fields_scope': 'actual think completed depth2; direct PLY abort preserves Worker fields; publication unobserved',
                'exit_code': result.returncode,
            }
        else:
            data = freeze(E_ROOT / 'state-check/model/results.json', 'receipts/e-model.json',
                          'cad4117c71e69ecab4cc94bc2decab8878dcaf8a51b03885ce99955fbce99526')
            model = json.loads(data)
            require(model['passed'] and model['build_sha256'] == PINS['E']['report'] and
                    model['program_sha256'] == PINS['E']['old_dev'] and
                    model['actual_consumer']['producer_dev_source_sha256'] == sha(original),
                    'E model receipt source/build/native differs')
            weights = [100, 320, 330, 500, 900, 3, 8, 5, 2, 1, -3, 6, -12, -8, 24, 10, 16, -1, 12, 2, 4]
            require(model['coefficients'] == weights == build['controls']['features']['model']['weights'],
                    'E exact coefficients differ')
            freeze(E_ROOT / 'state-check/model/actual-model-consumer.c', 'receipts/e-model-consumer.c',
                   model['actual_consumer']['harness_sha256'])
            for name, expected in model['reference_inputs'].items():
                freeze(E_ROOT / 'state-check/model/reference' / safe_relative(name),
                       'receipts/e-reference/' + name, expected)
            require(model['actual_consumer']['positions'] == 2007 and
                    {row['kind'] for row in model['actual_consumer']['runs']} == {'optimized', 'asan-ubsan'} and
                    all(row['cases'] == 2007 and row['raw_evaluation'] and row['clamped_evaluation'] and
                        row['ordering'] and row['cached_hce_poisoned'] for row in model['actual_consumer']['runs']),
                    'E actual-consumer coverage differs')
            positive_search(model['actual_search'], True)
            context_data = freeze(E_ROOT / 'state-check/results.json', 'receipts/e-state-context.json',
                                  'f21c885b81c391a17d1c0ceafee250f327e4eaad6ee6c679161c711698631cff')
            contexts = json.loads(context_data)
            require(contexts['passed'] and contexts['build_sha256'] == PINS['E']['report'] and
                    len(contexts['runs']) == 6 and
                    {(r['form'], r['kind']) for r in contexts['runs']} ==
                    {(form, kind) for form in ('dev', 'original', 'compact') for kind in ('optimized', 'asan-ubsan')},
                    'E actual-state contract forms differ')
            for row in contexts['runs']:
                require(row['source_sha256'] == (records['baseline']['source_sha256'] if row['form'] == 'compact'
                                                else PINS['E']['readable']) and
                        row['results']['tt_context_abort'] and row['results']['transitions'] == 206389 and
                        row['results']['transition_digest'] == '27256fa4c94f319e',
                        'E actual-state source/result binding differs')
            freeze(E_ROOT / 'state/recipe/engines/experiments/tiny-e-state/contract.c',
                   'receipts/e-state-contract.c', 'f6e5db69ba2bf7ba51ca998dbdc2afc5859ac17d90fecfaa01edbb9bb585267e')
            report['historical_receipts']['E_model'] = {
                'receipt_sha256': sha(data), 'coefficients': weights,
                'actual_consumer': model['actual_consumer'], 'actual_search': model['actual_search'],
                'reuse': 'exact readable/model source and identical non-policy bytes; old executable activity',
            }
            report['historical_receipts']['E_context_PLY'] = {
                'receipt_sha256': sha(context_data), 'runs': len(contexts['runs']),
                'contracts': ['full-key collision miss', 'halfmove/path key separation', 'third visit',
                              'halfmove draw and mate precedence', 'live-position PLY-1 abort'],
                'reuse': 'existing actual DEV/original/compact source fixtures, unchanged non-policy bytes',
                'fresh_execution': False,
            }
            report['scope_limits'].append('E context fixture records key separation, not a forced production TT cutoff on changed context.')
        report['passed'] = True
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        save()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', required=True, choices=('C', 'E'))
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.family, args.build, args.out)
    print(json.dumps({'family': args.family, 'passed': result['passed'], 'out': str(args.out)}))
