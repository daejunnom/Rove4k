#!/usr/bin/env python3
"""Bounded actual B profile cost and c/h/Q/P/startup comparisons.

Cost mode never compiles, executes, or allocates a TT. Qualification compiles
each source twice and invokes the actual shipping functions under the existing
controlled-clock fixture, including all generated Q roots and UBSan. Large
submission profiles are size/compile only; only TEST P4 is executed here.
"""
import argparse
import importlib.util
import json
import lzma
from pathlib import Path
import signal
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HOST = 'engines/experiments/tcec-scope/build.py'
FIXTURE = 'engines/experiments/tcec-next/check_b_state.py'
SELF = 'engines/experiments/tcec-next/check_profile_b.py'
VERIFIER = 'engines/experiments/tcec-next/profile_verify.py'
PHASE_CHECK = 'engines/experiments/tcec-next/check_profile_phase.py'
RUNTIME = 'engines/compact/tiny-entry-d/verify.py'
B_HELPER_PIN = '23eb1f4e9d036c0e8c229cced86a3f49b99981e98b4c6f80c05883b4cdb12a30'
PHASE_CHECK_PIN = 'a0c0c0ff25dd2b935f281789e7842b2bf199f3167f80df27ac1ff3550c8f4c37'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def require(value, message):
    if not value:
        raise ValueError(message)


def bound_fixture(source, assertions, workers):
    """Run the selected P4 callback with diagnostic-only W/N constants.

    N=workers*1024 keeps all ranges on complete 512-entry page units, including
    W28. This is init/selection only, never the actual P28 floor expression or
    a search on its non-power-of-two diagnostic table.
    """
    entries = workers * 1024
    require(workers in (4, 28, 256) and entries % (workers * 512) == 0,
            'bounded, complete-page diagnostic geometry required')
    old_w = b'#define qW 4\n'
    old_n = b'#define qN ((size_t)1<<22)\n'
    require(source.count(old_w) == source.count(old_n) == 1,
            'one selected B TEST-P4 resource definition required')
    after_w = f'#define qW {workers}\n'.encode()
    after_n = f'#define qN ((size_t){entries})\n'.encode()
    actual = source.replace(old_w, after_w, 1).replace(old_n, after_n, 1)
    observation = dict(workers=workers, entries=entries, every_callback_entered=True,
        all_entries_initialized=True, worker_storage_unchanged_except_id_depth=True,
        pending_zero=True, join_count_zero=True, startup_history_zero=True)
    output = json.dumps(json.dumps(observation, separators=(',', ':'))+'\n')
    appended = f'''
extern int __real_pthread_create(pthread_t*,const pthread_attr_t*,void*(*)(void*),void*);
static atomic_int rv_seen[qW];
typedef struct{{void*(*fn)(void*);void*arg;size_t id;}}rv_bound_launch;
static void*rv_observe(void*p){{rv_bound_launch v=*(rv_bound_launch*)p;free(p);
 if(qh||atomic_fetch_add(&rv_seen[v.id],1))exit(20);return v.fn(v.arg);}}
int __wrap_pthread_create(pthread_t*t,const pthread_attr_t*a,void*(*fn)(void*),void*p){{
 size_t n=((zd*)p)->i;if(qh||fn!=s||n>=qW)return 21;
 rv_bound_launch*v=malloc(sizeof*v);if(!v)return 22;
 v->fn=fn;v->arg=p;v->id=n;
 int error=__real_pthread_create(t,a,rv_observe,v);if(error)free(v);return error;
}}
#undef main
int main(void){{
 qq=aligned_alloc(4096,qN*sizeof*qq);
 if(!qq||((uintptr_t)qq)%4096)return 2;
 unsigned char*rv_saved=malloc(sizeof qr);if(!rv_saved)return 3;
 memset(qr,0x5a,sizeof qr);
 for(size_t n=0;n<qW;n++){{qr[n].i=n;qr[n].d=0;}}
 memcpy(rv_saved,qr,sizeof qr);
 for(size_t n=0;n<qN;n++){{qq[n].h=qq[n].v=UINT64_MAX;
 atomic_flag_clear_explicit(&qq[n].a,memory_order_relaxed);
 atomic_flag_test_and_set_explicit(&qq[n].a,memory_order_relaxed);}}
 if(qh||qk||atomic_load(&qj))return 4;
 qk=qW;V();U();
 if(qh||qk||atomic_load(&qj)||memcmp(rv_saved,qr,sizeof qr))return 5;
 for(size_t n=0;n<qW;n++)if(atomic_load(&rv_seen[n])!=1)return 6;
 for(size_t n=0;n<qN;n++)if(qq[n].h||qq[n].v||
 atomic_flag_test_and_set_explicit(&qq[n].a,memory_order_relaxed))return 7;
 for(size_t n=0;n<qW;n++){{qr[n].d=1;qr[n].m=MOVE(1,34,0);}}
 qr[qW-1].d=9;qr[qW-1].m=MOVE(6,37,0);d();qr[0].d=9;d();
 printf({output});free(rv_saved);free(qq);return 0;
}}
'''
    rendered = (b'#define main rv_bound_unused_shipping_main\n'+actual+b'\n'+
                '\n'.join(assertions).encode()+appended.encode())
    edits = [dict(before=old_w.decode(), after=after_w.decode()),
             dict(before=old_n.decode(), after=after_n.decode())]
    return rendered, observation, edits


def run_bound(args):
    """Qualify mechanisms of one admitted selected artifact, with no fallback."""
    require(args.variants is None, 'bound mode consumes the selected manifest, not variant generation')
    build, out = args.build.resolve(), args.out.resolve()
    verifier = load('b_bound_current_admission', ROOT/VERIFIER)
    manifest_path = verifier.artifact_file(build, 'build.json')
    require(manifest_path.stat().st_size <= 16 << 20, 'bounded build manifest required')
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    admitted = verifier.admit_c_build(manifest, build)
    require(admitted.family == 'B' and admitted.profile_id == 'test-p4' and
            admitted.representation == 'source-jit' and manifest['plan']['entry_cleanup'] == 'private-path' and
            manifest.get('post_profile') == dict(path='engines/experiments/tcec-next/profile_b.py',
                                                 variant='tcec-final-lf'),
            'actual selected B TEST-P4 final-lf source-JIT artifact required')
    require(manifest['inputs']['engines/experiments/tcec-next/profile_b.py']['sha256'] == B_HELPER_PIN,
            'selected B mechanism consumer differs from the reviewed helper')
    source = verifier.checked_artifact(build, 'main.c', verifier._field_pin(admitted.expected, 'source'))
    native = verifier.checked_artifact(build, 'native/x', verifier._field_pin(admitted.expected, 'native'))
    whole = verifier.checked_artifact(build, 'x', verifier._field_pin(admitted.expected, 'whole'))
    names = (SELF, VERIFIER, PHASE_CHECK, HOST, RUNTIME,
             'engines/experiments/tcec-next/profile_b.py',
             'engines/experiments/tcec-next/profile_source.py', 'engines/scripts/production.py')
    originals = {name: (ROOT/name).read_bytes().replace(b'\r\n', b'\n') for name in names}
    require(verifier.pin(originals[PHASE_CHECK])['sha256'] == PHASE_CHECK_PIN,
            'shared last-initializer/two-GO diagnostic changed')
    out.mkdir()
    for name, data in originals.items():
        target = out/'inputs'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    owner = load('b_bound_frozen_owner', out/'inputs'/HOST)
    phase = load('b_bound_frozen_barrier', out/'inputs'/PHASE_CHECK)
    runtime_module = load('b_bound_frozen_runtime', out/'inputs'/RUNTIME)
    report = dict(format=1, **{'class':'rove4k-bound-B-mechanism-v1'}, mode='bound',
        complete=False, source_bound=False, family='B', profile='test-p4', variant='tcec-final-lf',
        build=dict(path=str(manifest_path), **verifier.pin(manifest_raw)),
        shipping_source=verifier.pin(source), shipping_native=verifier.pin(native),
        shipping_whole=verifier.pin(whole), source_proofs=manifest['source_proofs'],
        source_inputs=manifest['inputs'], diagnostic_inputs={k:verifier.pin(v) for k,v in originals.items()},
        commands=[], mechanisms=[], startup_barriers=[],
        scope='admitted actual selected source/native/whole; scaled init-only callback fixtures and actual W4 main gate; no target W28/W256 runtime, NUMA, speed or strength claim')

    def save():
        (out/'result.json').write_text(json.dumps(report, indent=2)+'\n')

    save()
    (out/'selected-source.c').write_bytes(source)
    owner.LIMITS.update(aggregate_wall=300, per_command_wall=45, parent_AS=2<<30,
                       child_AS=2<<30, parent_CPU=120, parent_CPU_hard=150, child_CPU=30)
    previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    host = owner.Host(out, report, save)
    failure = None
    try:
        compiler = list(manifest.get('compile_executor', manifest['compiler']))
        assertions = manifest['source_proofs'][0]['target_type_assertions']
        for workers in (4, 28, 256):
            directory = out/('scaled-workers-'+str(workers))
            directory.mkdir()
            fixture, expected, edits = bound_fixture(source, assertions, workers)
            (directory/'fixture.c').write_bytes(fixture)
            host.run([*compiler, '-Wl,--wrap=pthread_create'], cwd=directory,
                     kind='scaled-W'+str(workers)+'-compile', data=fixture)
            driver = ('import resource,os;resource.setrlimit(resource.RLIMIT_STACK,(262144,262144));'
                      'os.execv('+repr(str(directory/'x'))+',['+repr(str(directory/'x'))+'])')
            raw = host.run([sys.executable, '-I', '-B', '-c', driver], cwd=directory,
                           kind='scaled-W'+str(workers)+'-execute')
            lines = raw.decode('ascii').splitlines()
            require(len(lines) == 3 and lines[:2] == ['bestmove g1f3', 'bestmove b1c3'] and
                    json.loads(lines[2]) == expected, 'actual selected B callback/init/selector diagnostic differs')
            report['mechanisms'].append(dict(workers=workers, fixture_tt_entries=workers*1024,
                shipping_tt_executed=False, search_executed=False,
                geometry='test-only equal complete-page ranges; not the actual TEST-P28 floor partition',
                test_only_constant_edits=edits, fixture_source=owner.pin(fixture),
                native=owner.pin((directory/'x').read_bytes()), observation=expected,
                selector_results=lines[:2], stack_limit_bytes=262144,
                shipping_identity_claimed=False))
            save()
        # Only a diagnostic macro alias is appended. The actual selected P4
        # main, resource constants, callback, search and selector stay intact.
        alias = b'\n#define RVW qW\n'
        row = phase.check_barrier(host, owner, runtime_module, out/'startup-last-initializer',
                                  source+alias, dict(worker='s', worker_type='zd', ident='i'), compiler)
        require(row['post_GO2_join_observed'] is True, 'actual post-GO2 join witness missing')
        row.update(shipping_source=owner.pin(source), diagnostic_prefix=owner.pin(source+alias),
                   appended_alias=alias.decode(), helper=verifier.pin(originals[PHASE_CHECK]))
        report['startup_barriers'].append(row)
        save()
    except BaseException as error:
        failure = error
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        save()
    finally:
        try:
            host.close()
        except BaseException as error:
            report['cleanup_failure'] = dict(type=type(error).__name__, message=str(error))
            if failure is None:
                failure = error
        finally:
            signal.signal(signal.SIGCHLD, previous)
    if failure is None:
        try:
            require(report.get('host_cleanup') == dict(unsettled_commands=0, errors=[]) and
                    all(c.get('returncode') == 0 and c.get('terminal') is True and c.get('reaped') is True and
                        c.get('owned_group_absent') is True and c.get('forced_cleanup') is False for c in report['commands']),
                    'bound B commands did not physically settle')
            require(all((ROOT/name).read_bytes().replace(b'\r\n', b'\n') == data for name,data in originals.items()),
                    'bound diagnostic source changed during execution')
            require(manifest_path.read_bytes() == manifest_raw, 'selected build manifest changed during bound execution')
            verifier.checked_artifact(build, 'main.c', report['shipping_source'])
            verifier.checked_artifact(build, 'native/x', report['shipping_native'])
            verifier.checked_artifact(build, 'x', report['shipping_whole'])
            require(verifier.admit_c_build(manifest, build) == admitted,
                    'selected source admission changed during bound execution')
            report['admission_rechecked_after_execution'] = True
        except BaseException as error:
            failure = error
            report['failure'] = dict(type=type(error).__name__, message=str(error))
    if failure:
        save()
        raise failure
    report.update(complete=True, source_bound=True)
    save()
    print(json.dumps(dict(complete=True, source_bound=True, family='B', mode='bound',
                          mechanisms=3, startup_barriers=1, report=str(out/'result.json'))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=('cost', 'qualify', 'bound'), default='cost')
    parser.add_argument('--variants', nargs='+')
    args = parser.parse_args()
    out = args.out.resolve()
    require(sys.platform == 'linux' and args.build.is_absolute() and args.out.is_absolute() and
            not out.exists() and not any((p/'.git').exists() for p in (out, *out.parents)),
            'Linux and new absolute external output required')
    if args.mode == 'bound':
        return run_bound(args)
    out.mkdir()
    inputs = {}
    names = ('engines/experiments/tcec-next/profile_b.py',
             'engines/experiments/tcec-next/check_profile_b.py',
             'engines/experiments/tcec-next/profile_source.py',
             'engines/scripts/production.py', HOST, FIXTURE, 'engines/scripts/source_package.py')
    for name in names:
        data = (ROOT/name).read_bytes().replace(b'\r\n', b'\n')
        dest = out/'inputs'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        inputs[name] = data
    helper = load('profile_b_frozen', out/'inputs'/names[0])
    projection = load('profile_b_resource_frozen', out/'inputs'/names[2])
    production = load('profile_b_contract_frozen', out/'inputs'/names[3])
    package = load('profile_b_package_frozen', out/'inputs'/names[-1])
    variants = args.variants or list(helper.VARIANTS)
    require(variants and len(variants) == len(set(variants)) and set(variants) <= set(helper.VARIANTS),
            'explicit nonduplicate finite B variants required')
    build_raw = (args.build/'build.json').read_bytes()
    build = json.loads(build_raw)
    raw = (args.build/'main.c').read_bytes()
    require(build['complete'] and build['reproducible'] and build['entry'] == 'B' and
            build['plan']['resources']['id'] == 'test-p4' and
            helper.pin(raw) == {k: build['expected_contract']['source_'+k] for k in ('bytes', 'sha256')},
            'complete known source-produced TEST P4 B comparison input required')
    base = (args.build/'control/main.c').read_bytes()
    require((len(base), helper.pin(base)['sha256']) == projection.INPUTS['B'], 'maintained full B differs')
    source, resource_proof = projection.transform_source(base, family='B', profile=production.resource_profile('test-p4'))
    require(source == raw and projection.restore_source(source, resource_proof) == base,
            'current tracked resource projection differs from input report')
    report = dict(complete=False, mode=args.mode, commands=[], cases={},
        inputs={k: helper.pin(v) for k, v in inputs.items()},
        comparison_build=dict(path=str(args.build), report=helper.pin(build_raw)),
        authority='current maintained B source pin and current resource projection; comparison only, no production selection',
        scope='source/native/whole reproduction; actual c/h/Q/P traces and semantic Boards/learners; real startup init and UBSan; no speed/strength')
    def save():
        (out/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    save()
    host = previous = None
    failure = None
    try:
        if args.mode == 'qualify':
            hostmod = load('profile_b_host_frozen', out/'inputs'/HOST)
            hostmod.LIMITS.update(aggregate_wall=600, per_command_wall=90, parent_AS=2<<30,
                                  child_AS=2<<30, parent_CPU=300, parent_CPU_hard=330, child_CPU=90)
            previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
            host = hostmod.Host(out, report, save)
        header = (args.build/'header.sh').read_bytes()
        for profile_id in ('test-p4', 'test-p28', 'tcec-provisional'):
            current, resource_proof = projection.transform_source(base, family='B', profile=production.resource_profile(profile_id))
            for label in ('baseline', *variants):
                source, proof = (current, None) if label == 'baseline' else helper.transform_source(
                    current, profile_id=profile_id, variant=label)
                if proof:
                    require(helper.restore_source(source, proof) == current, 'whole B inverse differs')
                whole = package.package(source, build['compression'], prefix=header)
                require(whole == package.package(source, build['compression'], prefix=header), 'two complete-file reproductions differ')
                decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                require(decoder.decompress(whole[len(header):], max_length=len(source)+1) == source and
                        decoder.eof and not decoder.unused_data, 'strict full source restoration differs')
                key = profile_id+'/'+label
                command_key = profile_id+'-'+label
                directory = out/profile_id/label
                directory.mkdir(parents=True)
                (directory/'main.c').write_bytes(source)
                (directory/'x').write_bytes(whole)
                row = dict(source=helper.pin(source), whole=helper.pin(whole), proof=proof,
                           resource_proof=resource_proof, runtime=False)
                report['cases'][key] = row
                save()
                if args.mode != 'qualify':
                    continue
                if proof and proof.get('target_abi_probe'):
                    probe_dir = directory/'abi'
                    probe_dir.mkdir()
                    abi = proof['target_abi_probe'].encode()
                    host.run(build['compiler']+['-c'], cwd=probe_dir,
                             kind=command_key+'-target-abi', data=abi)
                    row['target_abi_probe'] = dict(source=helper.pin(abi), object=helper.pin((probe_dir/'x').read_bytes()), passed=True)
                natives = []
                for repeat in (1, 2):
                    host.run(build['compiler'], cwd=directory, kind=command_key+'-shipping-compile-'+str(repeat), data=source)
                    natives.append((directory/'x').read_bytes())
                require(natives[0] == natives[1], 'shipping native reproduction differs')
                (directory/'native').write_bytes(natives[0])
                (directory/'x').write_bytes(whole)
                row['native'] = helper.pin(natives[0])
                if profile_id != 'test-p4':
                    save()
                    continue
                fixture = load('profile_b_fixture_frozen', out/'inputs'/FIXTURE)
                clock = fixture.CLOCK if fixture.CLOCK in source else fixture.CLOCK.replace(b'(void)', b'()')
                require(source.count(clock) == source.count(fixture.Q_ENTRY) == 1, 'one actual clock/Q port required')
                core = fixture.HOOK_PREFIX+source.replace(clock, fixture.HOOK_CLOCK).replace(fixture.Q_ENTRY, fixture.Q_HOOK)
                (directory/'fixture-core.c').write_bytes(core)
                harness = fixture.HARNESS.replace('FIXTURE_OCCUPANCY_CHECK',
                    'for(int side=0;side<2;side++)if(p->a[side]!=types[side][0])abort();')
                harness = harness.replace('for(int i=0;i<qh;i++)w->k[i]=p->h;', 'for(int i=0;i<qh;i++)qg[i]=p->h;')
                harness = harness.replace('if(moves[i]&8){', '{')
                harness = harness.replace('za child;int valid=h(p,moves[i],&child);',
                    'if((moves[i]>>17)||(((moves[i]>>7)&127)&136)||'
                    '(((moves[i]>>14)&7)==1)||((moves[i]>>14)&7)>5)abort();'
                    'za child;int valid=h(p,moves[i],&child);')
                harness = harness.replace('(1<<18)*sizeof*qq', 'RVN*sizeof*qq')
                harness = harness.replace('qq=calloc(1<<18,sizeof*qq)', 'qq=aligned_alloc(4096,RVN*sizeof*qq)')
                clear = ('static void fixture_clear(void){for(size_t i=0;i<RVN;i++){qq[i].h=qq[i].v=0;'
                         'atomic_flag_clear_explicit(&qq[i].a,memory_order_relaxed);}}\n')
                harness = harness.replace('B();', 'fixture_clear();')
                start = source.split(b'qq=aligned_alloc(4096,', 1)[1].split(b'l 2;', 1)[1].split(b'k(&ql);', 1)[0].decode()
                startup = ('static void fixture_startup(void){qh=0;memset(qq,165,RVN*sizeof*qq);'+start+
                    'for(size_t i=0;i<RVN;i++){if(qq[i].h||qq[i].v||'
                    'atomic_flag_test_and_set_explicit(&qq[i].a,memory_order_relaxed))abort();}'
                    'if(qk||qj)abort();for(int i=0;i<RVW;i++)if(qr[i].i!=i||qr[i].d)abort();}\n')
                harness = harness.replace('static D fixture_digest=', clear+startup+'static D fixture_digest=')
                harness = harness.replace('if(!qq)return 2;fixture_clear();', 'if(!qq)return 2;fixture_startup();fixture_clear();')
                contracts = r'''
static void fixture_contracts(void){
 for(int r=0;r<8;r++)for(int f=0;f<8;f++){
  int expected=0;
  if(r==0){if(f==0)expected=2;if(f==4)expected=3;if(f==7)expected=1;}
  if(r==7){if(f==0)expected=8;if(f==4)expected=12;if(f==7)expected=4;}
  if(O(r*16+f)!=expected)abort();
 }
 for(int sign=-1;sign<=1;sign+=2)for(int n=0;n<4;n++)for(int b0=0;b0<3;b0++)
 for(int b1=0;b1<3;b1++)for(int other=0;other<4;other++){
  za board={0};board.s=1;board.e=-1;M(&board,4,6);M(&board,116,-6);
  for(int j=0;j<n;j++)M(&board,16+j,sign*2);
  for(int j=0;j<b0;j++)M(&board,32+j*2,sign*3);
  for(int j=0;j<b1;j++)M(&board,33+j*2,sign*3);
  if(other)M(&board,48,sign*(other==1?1:other==2?4:5));
  int expected=!other&&((n==0&&!(b0&&b1))||(n==1&&!b0&&!b1));
  if(y(&board)!=expected)abort();
 }
}
'''
                harness = harness.replace('static D fixture_digest=', contracts+'static D fixture_digest=')
                harness = harness.replace('fixture_startup();fixture_clear();', 'fixture_startup();fixture_clear();fixture_contracts();')
                if b'#define qN ' in source:
                    harness = harness.replace('RVN', 'qN').replace('RVW', 'qW')
                (directory/'fixture.c').write_text(harness)
                observations = []
                for sanitize in (False, True):
                    name = 'probe-ubsan' if sanitize else 'probe'
                    command = ['cc', '-std=c11', '-O1' if sanitize else '-Os', '-pthread']
                    if sanitize:
                        command += ['-fsanitize=undefined', '-fno-sanitize-recover=all']
                    host.run(command+['fixture.c', '-o', name], cwd=directory, kind=command_key+'-'+name+'-compile')
                    observations.append(host.run(['./'+name], cwd=directory, kind=command_key+'-'+name+'-actual-functions').decode())
                require(observations[0] == observations[1], 'UBSan actual semantic observation differs')
                require(observations[0].splitlines()[0] == 'layout=192', 'normal Board size differs')
                row.update(observation=observations[0], fixture=helper.pin(harness.encode()), core=helper.pin(core),
                           startup_initialized=True, actual_functions=True,
                           separate_contract_cases=dict(legal_castling_squares=64, material_classifications=288))
                if label != 'baseline':
                    require(observations[0] == report['cases'][profile_id+'/baseline']['observation'],
                            'actual Board/search/learners/LVA/clock or cancellation differs')
                save()
    except BaseException as error:
        failure = error
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        save()
    finally:
        if host:
            try:
                host.close()
            except BaseException as error:
                report['cleanup_failure'] = dict(type=type(error).__name__, message=str(error))
                if failure is None:
                    failure = error
            finally:
                signal.signal(signal.SIGCHLD, previous)
    if failure:
        save()
        raise failure
    report['complete'] = True
    save()
    print(json.dumps(dict(complete=True, mode=args.mode,
        costs={k:v['whole']['bytes'] for k,v in report['cases'].items()})))


if __name__ == '__main__':
    main()
