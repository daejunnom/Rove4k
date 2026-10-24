#!/usr/bin/env python3
"""Bounded full-F per-GO source, native, thread and learner experiments.

This checker deliberately does not import persistent-pool TID assertions.
Spawn/main synchronous cases are comparisons, not immediate-ready UCI claims.
All generated files, compiler products and transcripts require a new external
directory. The original host process identity is retained through settlement.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shlex
import signal
import sys
import time

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[3]
PENDING = None
PINS = {
    'engines/compact/tiny-entry-d/verify.py': '18faa69aed5cb5dd85a054ef2e6830463f3d819f5f635d74d55550a877c81eae',
    'engines/tests/chess_oracle.py': 'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8',
    'engines/experiments/tcec-scope/c_per_go.py': 'a967b432b190624ddda415b6dc426bffa5a73233b14f844945651fa5fa5a0efe',
}


def require(ok, detail):
    if not ok:
        raise AssertionError(detail)


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def interrupted(signum, frame):
    global PENDING
    PENDING = signum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--f2-source', type=Path, required=True)
    parser.add_argument('--f8-source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--variants', nargs='+', choices=('spawn', 'main', 'async'),
                        default=('spawn', 'main', 'async'))
    parser.add_argument('--operators', action='store_true', help='refine only frozen async outputs with C11 operators')
    args = parser.parse_args()
    out = args.out.resolve()
    require(sys.platform == 'linux' and 1 <= len(os.sched_getaffinity(0)) <= 2,
            'Linux and at most two affinity CPUs required; no scaling claim')
    require(args.out.is_absolute() and not out.exists() and REPO not in out.parents
            and not any((p/'.git').exists() for p in (out, *out.parents)), 'new external output required')
    require(args.f2_source.is_absolute() and args.f8_source.is_absolute(), 'explicit source paths required')
    out.mkdir(parents=True)
    frozen = out/'inputs'
    report = {'complete': False,
              'scope': f'{2*len(args.variants)} finite full-F per-GO candidates; no strength/scaling/tournament claim',
              'variants': args.variants, 'operator_refinement': args.operators,
              'affinity': sorted(os.sched_getaffinity(0)), 'inputs': {}, 'profiles': {},
              'limits': {'AS': 2 << 30, 'CPU': [120, 125], 'wall_alarm': 180},
              'synchronous_candidates_meet_immediate_ready': False}

    def save():
        (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')

    require(not args.operators or args.variants == ['async'], 'operators requires --variants async')
    extra = ('engines/experiments/tcec-scope/c_per_go_operators.py',) if args.operators else ()
    for relative in (*PINS, 'engines/scripts/source_package.py', 'engines/compact/tiny-entry-f/recipe.json',
                     'engines/experiments/tcec-scope/check_per_go.py', *extra):
        raw = (REPO/relative).read_bytes().replace(b'\r\n', b'\n')
        require(b'\r' not in raw and (relative not in PINS or pin(raw)['sha256'] == PINS[relative]),
                'fixed checker input differs: '+relative)
        dest = frozen/relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        report['inputs'][relative] = pin(raw)
    helper = load('per_go_host', frozen/'engines/compact/tiny-entry-d/verify.py')
    oracle = load('per_go_oracle', frozen/'engines/tests/chess_oracle.py')
    module = load('per_go_source', frozen/'engines/experiments/tcec-scope/c_per_go.py')
    operators = load('per_go_operators', frozen/extra[0]) if extra else None
    package = load('per_go_package', frozen/'engines/scripts/source_package.py')
    recipe = json.loads((frozen/'engines/compact/tiny-entry-f/recipe.json').read_bytes())
    require(recipe['compiler'] == ['cc', '-Os', '-pthread', '-x', 'c', '-', '-o', 'x', '-s'], 'fixed compiler differs')
    require(recipe['compression'] == {'format': 'lzma-alone', 'filter': 'LZMA1', 'preset': 6, 'extreme': False,
        'lc': 2, 'lp': 0, 'pb': 0, 'check': 'NONE', 'mf': 'BT2', 'dictionary_bytes': 16384, 'nice_len': 24},
        'fixed codec differs')

    class Budget(helper.Budget):
        def left(self, seconds):
            if PENDING is not None:
                raise TimeoutError('per-GO checker signal '+str(PENDING))
            return super().left(seconds)

    def finish(owned, status=0):
        end = time.monotonic()+owned.budget.left(8)
        while not owned.exited():
            require(time.monotonic() < end, 'owned command exit deadline')
            time.sleep(.005)
        owned.pre_reap_other_members = owned.group_others()
        require(not owned.pre_reap_other_members, 'other process group members before original leader reap')
        owned.process.wait(timeout=owned.budget.left(3))
        owned.reaped = True
        for reader in (owned.stdout, owned.stderr):
            reader.thread.join(timeout=owned.budget.left(3))
            require(not reader.thread.is_alive() and reader.done and not reader.error, 'output reader did not join')
        require(owned.process.returncode == status and not owned.stderr.bytes(), 'exit/stderr differs')
        owned.finished = True
        return {'returncode': status, 'pre_reap_other_members': [], 'readers_joined': True,
                'original_identity_retained_until_group_settlement': True}

    def compile_source(directory, source):
        directory.mkdir(parents=True)
        (directory/'main.c').write_bytes(source)
        driver = directory/'compile'
        driver.write_text('#!/bin/sh\ncd '+shlex.quote(str(directory))+'||exit\nexec '+
                          shlex.join(recipe['compiler'])+' <main.c\n')
        driver.chmod(0o755)
        owned = helper.Owned(driver, directory/'compiler-log', Budget(25))
        row = {}
        try:
            owned.close_input()
            row['completion'] = finish(owned)
            row['native'] = pin((directory/'x').read_bytes())
            return row
        finally:
            row['cleanup'] = owned.cleanup()
            (directory/'compile.json').write_text(json.dumps(row, indent=2)+'\n')

    def settled(owned):
        end = time.monotonic()+owned.budget.left(4)
        while True:
            try:
                tasks = helper.tasks(owned.process.pid)
                if len(tasks) == 1:
                    return tasks
            except (AssertionError, FileNotFoundError, ProcessLookupError):
                pass
            require(time.monotonic() < end, 'per-GO native did not settle to main only')
            time.sleep(.01)

    resource.setrlimit(resource.RLIMIT_AS, (2 << 30,)*2)
    resource.setrlimit(resource.RLIMIT_CPU, (120, 125))
    saved = {s: signal.signal(s, interrupted) for s in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM, signal.SIGXCPU)}
    signal.alarm(180)
    save()
    try:
        for family, source_path in (('F2', args.f2_source), ('F8', args.f8_source)):
            source = source_path.read_bytes()
            require((len(source), pin(source)['sha256']) == module.INPUTS[family], 'fixed maintained source differs')
            workers = 2 if family == 'F2' else 8
            for variant in args.variants:
                name = family+'-'+variant
                directory = out/name
                directory.mkdir()
                candidate, proof = module.transform_source(source, family=family, variant=variant)
                require(module.restore_source(candidate, proof) == source, 'full inverse differs')
                operator_proof = None
                if operators:
                    original = candidate
                    candidate, operator_proof = operators.transform_source(candidate, family=family)
                    require(operators.restore_source(candidate, operator_proof) == original, 'operator inverse differs')
                    (directory/'operators-proof.json').write_text(json.dumps(operator_proof, indent=2)+'\n')
                (directory/'main.c').write_bytes(candidate)
                (directory/'source-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
                whole = package.package_shell(candidate, recipe['compression'], kind='source',
                                              compiler=recipe['compiler'], child_reaping='ignore-after-compile')
                target = directory/'x'
                target.write_bytes(whole)
                target.chmod(0o755)
                row = {'source': pin(candidate), 'whole': pin(whole), 'contract': proof['contract'], 'sessions': []}
                if operator_proof:
                    row['operators'] = operator_proof['contract']
                report['profiles'][name] = row
                save()
                row['compile'] = compile_source(directory/'native', candidate)
                owned = helper.Owned(target, directory/'runtime', Budget(25))
                session = {'pid': owned.process.pid, 'completed': [], 'activity': {}}
                row['sessions'].append(session)
                try:
                    owned.send(b'uci\nisready\n')
                    owned.wait_line(b'uciok')
                    owned.wait_line(b'readyok')
                    session['startup'] = settled(owned)
                    require(pin((Path('/proc')/str(owned.process.pid)/'exe').read_bytes()) == row['compile']['native'],
                            'actual source-JIT native differs from compiler product')
                    owned.send(b'position startpos\ngo wtime 60000 btime 60000\n')
                    samples, max_ticks, peak = [], {}, 0
                    before = next(iter(session['startup'].values()))['cpu_ticks']
                    ready_sent = False
                    began = time.monotonic()
                    while not any(line.startswith(b'bestmove ') for line in owned.stdout.bytes().splitlines()):
                        owned.budget.left(5)
                        try:
                            tasks = helper.tasks(owned.process.pid)
                        except (FileNotFoundError, ProcessLookupError):
                            continue
                        peak = max(peak, len(tasks))
                        require(len(tasks) <= proof['contract']['active_native_TID_cap'], 'active resource cap exceeded')
                        for tid, data in tasks.items():
                            max_ticks[tid] = max(max_ticks.get(tid, 0), data['cpu_ticks'])
                        if len(samples) < 64:
                            samples.append({'seconds': time.monotonic()-began, 'tasks': tasks})
                        if not ready_sent and len(tasks) == proof['contract']['active_native_TID_cap']:
                            owned.send(b'isready\n')
                            ready_sent = True
                            session['ready_sent_seconds'] = time.monotonic()-began
                            if variant == 'async':
                                owned.stdout.until(lambda data: data.splitlines().count(b'readyok') == 2, owned.budget, .75)
                                require(not any(line.startswith(b'bestmove ') for line in owned.stdout.bytes().splitlines()),
                                        'ready reply was deferred until search finished')
                                session['ready_replied_before_result'] = True
                        time.sleep(.01)
                    require(ready_sent and peak == proof['contract']['active_native_TID_cap'], 'full GO worker topology not observed')
                    active = [tid for tid, ticks in max_ticks.items()
                              if (ticks > before if tid == owned.process.pid else ticks > 0)]
                    search_workers = [tid for tid in active if variant == 'main' or tid != owned.process.pid]
                    require(len(search_workers) == workers, 'not every search worker accrued actual CPU ticks')
                    session['activity'] = {'peak_TIDs': peak, 'search_workers_with_CPU': search_workers,
                                           'samples': samples, 'seconds': time.monotonic()-began}
                    owned.wait_line(b'readyok', 2)
                    session['after_GO'] = settled(owned)
                    board = oracle.Board.from_fen()
                    for number, moves in enumerate(([], ['e2e4'], ['d2d4', 'd7d5']), 1):
                        if number > 1:
                            owned.send(('position startpos moves '+' '.join(moves)+'\ngo wtime 0 btime 0\n').encode())
                        owned.wait_best(number)
                        board = oracle.Board.from_fen()
                        for move in moves:
                            board = board.play(move)
                        chosen = [line.split()[1].decode() for line in owned.stdout.bytes().splitlines() if line.startswith(b'bestmove ')][-1]
                        require(chosen in {str(m) for m in board.legal_moves()}, 'continuous position/GO result illegal')
                        session['completed'].append(chosen)
                        settled(owned)
                    owned.send(b'quit\n')
                    session['completion'] = finish(owned)
                finally:
                    session['cleanup'] = owned.cleanup()
                    save()

                # Include the exact candidate, replacing only main for deterministic
                # state/selector/underpromotion observations. Search code is unchanged.
                fixture = (b'#define main engine_main\n'+candidate+b'\n#undef main\n'+r'''
int main(void){
 B=calloc(1<<18,sizeof*B);if(!B)return 2;qk();o(&Z);qg[0]=Z.h;qh=1;
 X saved[WORKERS];pthread_t handles[WORKERS];
 for(int n=0;n<WORKERS;n++){U[n].a=n;U[n].b=99;
  for(int a=0;a<128;a++)for(int b=0;b<128;b++)U[n].h[a][b]=(a+b+n)%31+1;
  for(int a=0;a<13;a++)for(int b=0;b<13;b++)U[n].i[a][b]=(a*3+b+n)%31+1;
  for(int a=0;a<1024;a++)U[n].j[a]=(a+n)%31+1;
 }memcpy(saved,U,sizeof U);atomic_store(&V,1);ASYNC_PENDING
 for(int n=0;n<WORKERS;n++){U[n].b=0;if(pthread_create(handles+n,NULL,qq,U+n))return 3;}
 for(int n=0;n<WORKERS;n++)if(pthread_join(handles[n],NULL))return 4;
 for(int n=0;n<WORKERS;n++)if(U[n].b||U[n].d||U[n].e||
  memcmp(U[n].h,saved[n].h,sizeof U[n].h)||memcmp(U[n].i,saved[n].i,sizeof U[n].i)||
  memcmp(U[n].j,saved[n].j,sizeof U[n].j))return 5;
 I board;for(int n=0;n<WORKERS;n++){U[n].b=7;U[n].d=qb(&Z,"d2d4",&board);}
 U->d=qb(&Z,"e2e4",&board);y();U[WORKERS-1].b=8;y();
 for(int n=0;n<WORKERS;n++)U[n].b=U[n].d=0;y();
 memset(&Z,0,sizeof Z);Z.s=1;Z.e=-1;Z.b[4]=6;Z.k[0]=4;Z.b[116]=-6;Z.k[1]=116;Z.b[96]=1;
 char move[]="a7a8n",text[6];for(int n=0;n<4;n++){move[4]="nbrq"[n];Y chosen=qb(&Z,move,&board);
  if(!chosen)return 6;j(chosen,text);if(strcmp(move,text))return 7;}
 puts("seed-selector-NBRQ-ok");return 0;
}
'''.replace('WORKERS', str(workers)).replace('ASYNC_PENDING', 'atomic_store(&A,1000);' if variant == 'async' else '').encode())
                row['seed_fixture_compile'] = compile_source(directory/'seed-fixture', fixture)
                owned = helper.Owned(directory/'seed-fixture/x', directory/'seed-fixture/runtime', Budget(8))
                try:
                    owned.close_input()
                    row['seed_fixture_completion'] = finish(owned)
                    lines = owned.stdout.bytes().splitlines()
                    require(lines[:2] == [b'bestmove e2e4', b'bestmove d2d4']
                            and lines[-1] == b'seed-selector-NBRQ-ok', 'seed/selector/NBRQ fixture differs')
                    fallback = lines[2].split()[1].decode()
                    require(fallback in {str(m) for m in oracle.Board.from_fen().legal_moves()}, 'fallback illegal')
                    row['seed_fixture'] = {'all_worker_learners_retained': True, 'completed_depth_seed_0': True,
                                           'strict_greater_and_worker0_tie': True, 'fallback': fallback, 'full_NBRQ': True}
                finally:
                    row['seed_fixture_cleanup'] = owned.cleanup()
                    save()

                # Inject failure on the second pthread_create. F2-main reaches
                # that call in its second job; all other policies fail in job1.
                failure = (b'#include <pthread.h>\nstatic int calls;\n'
                    b'static int fail_create(pthread_t*t,const pthread_attr_t*a,void*(*f)(void*),void*p)'
                    b'{return ++calls==2?11:pthread_create(t,a,f,p);}\n#define pthread_create fail_create\n'+candidate)
                row['failure_compile'] = compile_source(directory/'failure-fixture', failure)
                owned = helper.Owned(directory/'failure-fixture/x', directory/'failure-fixture/runtime', Budget(8))
                try:
                    owned.send(b'position startpos\ngo wtime 0 btime 0\ngo wtime 0 btime 0\n')
                    owned.close_input()
                    row['failure_completion'] = finish(owned, 2)
                    row['creation_failure'] = 'second create process-wide exit2; no remaining group members'
                finally:
                    row['failure_cleanup'] = owned.cleanup()
                    save()

                # Real searches must carry their learned arrays into the next
                # job unchanged at entry. The probe hashes every learner cell;
                # it also keeps a worker alive briefly after its final output,
                # so the next position must wait for pthread_join, not A==0.
                prefix = 'aa ' if family == 'F2' else 'static '
                worker_start = prefix+'void*qq(void*p){'
                trace_support = r'''
static W snapshots[WORKERS];static S seen[WORKERS],changed[WORKERS],learned[WORKERS];
static W fingerprint(X*w){W value=1469598103934665603ull;
 for(int a=0;a<128;a++)for(int b=0;b<128;b++)value=(value^(uint16_t)w->h[a][b])*1099511628211ull;
 for(int a=0;a<13;a++)for(int b=0;b<13;b++)value=(value^(uint16_t)w->i[a][b])*1099511628211ull;
 for(int a=0;a<1024;a++)value=(value^(uint16_t)w->j[a])*1099511628211ull;return value;}
static int nonzero(X*w){int value=0;
 for(int a=0;a<128;a++)for(int b=0;b<128;b++)value|=w->h[a][b];
 for(int a=0;a<13;a++)for(int b=0;b<13;b++)value|=w->i[a][b];
 for(int a=0;a<1024;a++)value|=w->j[a];return !!value;}
'''.replace('WORKERS', str(workers))
                tracked = candidate.decode()
                require(tracked.count(worker_start) == 1 and tracked.count('i(p,&Z);') == 1, 'one exact worker probe site required')
                tracked = tracked.replace(worker_start, trace_support+worker_start+
                    'X*w=p;int id=w->a;W root_hash=Z.h;'
                    'if(seen[id]&&snapshots[id]!=fingerprint(w))changed[id]=1;seen[id]++;', 1)
                tracked = tracked.replace('i(p,&Z);', 'i(p,&Z);snapshots[id]=fingerprint(w);learned[id]|=nonzero(w);', 1)
                tracked = tracked.replace('H NULL;}', 'nanosleep(&(struct timespec){0,25000000},NULL);'
                    'if(root_hash!=Z.h)exit(70+id);H NULL;}', 1)
                require(tracked.count('}}H 0;}') == 1, 'one exact terminal probe site required')
                tracked = tracked.replace('}}H 0;}', '}}'+('k();' if variant == 'async' else '')+
                    f'for(int id=0;id<{workers};id++){{if(seen[id]!=2||changed[id])H 80+id;'
                    'printf("learner %d %d %d\\n",id,seen[id],learned[id]);}H 0;}', 1)
                row['learner_trace_compile'] = compile_source(directory/'learner-trace', tracked.encode())
                owned = helper.Owned(directory/'learner-trace/x', directory/'learner-trace/runtime', Budget(10))
                try:
                    owned.send(b'position startpos\ngo\n')
                    owned.wait_best(1)
                    owned.send(b'position startpos moves e2e4\ngo\n')
                    owned.wait_best(2)
                    owned.send(b'quit\n')
                    row['learner_trace_completion'] = finish(owned)
                    trace = [line.split() for line in owned.stdout.bytes().splitlines() if line.startswith(b'learner ')]
                    require(len(trace) == workers and all(line[2] == b'2' for line in trace)
                            and any(line[3] == b'1' for line in trace), 'real-search learner trace differs')
                    row['real_GO_learner_trace'] = {'workers': workers, 'GOs': 2,
                        'all_learner_entry_hashes_equal_prior_exit_hashes': True,
                        'actual_nonzero_learning_observed': [int(line[1]) for line in trace if line[3] == b'1'],
                        'next_position_waited_for_post_result_worker_return': True,
                        'instrumentation': 'full learner fingerprint and 25ms post-output worker delay; search body unchanged'}
                finally:
                    row['learner_trace_cleanup'] = owned.cleanup()
                    save()

                if variant == 'async':
                    row['pipeline_and_closing'] = []
                    for eof in (False, True):
                        owned = helper.Owned(directory/'native/x', directory/('active-EOF' if eof else 'active-quit'), Budget(10))
                        closing = {'mode': 'EOF' if eof else 'quit', 'completed': []}
                        row['pipeline_and_closing'].append(closing)
                        try:
                            owned.send(b'uci\nisready\n')
                            owned.wait_line(b'readyok')
                            settled(owned)
                            # No position between GO1 and GO2. Position before
                            # GO3 has a different root and must join GO2 first.
                            owned.send(b'position startpos\ngo wtime 60000 btime 60000\n'
                                       b'go wtime 0 btime 0\nposition startpos moves e2e4\n'
                                       b'go wtime 0 btime 0\n')
                            owned.wait_best(3)
                            chosen = [line.split()[1].decode() for line in owned.stdout.bytes().splitlines()
                                      if line.startswith(b'bestmove ')]
                            require(len(chosen) == 3, 'pipeline result count differs')
                            for index, move in enumerate(chosen):
                                board = oracle.Board.from_fen()
                                if index == 2:
                                    board = board.play('e2e4')
                                require(move in {str(m) for m in board.legal_moves()}, 'pipeline root/result mismatch')
                            closing['completed'] = chosen
                            settled(owned)
                            owned.send(b'go wtime 60000 btime 60000\n')
                            end = time.monotonic()+owned.budget.left(2)
                            while len(helper.tasks(owned.process.pid)) != workers+1:
                                require(time.monotonic() < end, 'active closing workers absent')
                                time.sleep(.005)
                            began = time.monotonic()
                            if eof:
                                owned.close_input()
                            else:
                                owned.send(b'quit\n')
                            closing['completion'] = finish(owned)
                            closing['seconds_to_process_exit'] = time.monotonic()-began
                            closing['closing_bestmove_required'] = False
                        finally:
                            closing['cleanup'] = owned.cleanup()
                            save()

                    join_failure = (b'#include <pthread.h>\n'
                        b'static int fail_join(pthread_t t,void**p){(void)t;(void)p;return 11;}\n'
                        b'#define pthread_join fail_join\n'+candidate)
                    row['join_failure_compile'] = compile_source(directory/'join-failure', join_failure)
                    owned = helper.Owned(directory/'join-failure/x', directory/'join-failure/runtime', Budget(8))
                    try:
                        owned.send(b'position startpos\ngo wtime 60000 btime 60000\nposition startpos moves e2e4\n')
                        owned.close_input()
                        row['join_failure_completion'] = finish(owned, 2)
                    finally:
                        row['join_failure_cleanup'] = owned.cleanup()
                        save()
                row['runtime_qualified_for_declared_local_checks'] = True
                save()
        report['complete'] = True
        save()
        print(json.dumps({'complete': True, 'profiles': len(report['profiles']), 'results': str(out/'results.json')}))
    except BaseException as error:
        report['error'] = repr(error)
        save()
        raise
    finally:
        signal.alarm(0)
        for owned in list(helper.OWNED):
            owned.cleanup()
        for number, previous in saved.items():
            signal.signal(number, previous)


if __name__ == '__main__':
    main()
