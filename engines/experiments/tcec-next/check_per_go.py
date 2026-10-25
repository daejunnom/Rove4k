#!/usr/bin/env python3
"""Bounded source-JIT, learner and lifecycle probes for the ABCE projection.

This consumes the explicit experimental two-build cost bundle, not historical
runtime success. It recompiles meaningful instrumented/failure fixtures and
executes the uninstrumented source package and native. No speed/Elo claim.
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
ROOT = Path(__file__).resolve().parents[3]
PENDING = None
LEARNERS = {'A': ('zC', 'an', 'ah'), 'B': ('h', 'c', 'f'),
            'C': ('zC', 'an', 'ah'), 'E': ('zC', 'an', 'ah')}


def require(ok, text):
    if not ok:
        raise AssertionError(text)


def pin(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def signal_pending(number, frame):
    global PENDING
    PENDING = number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cost', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(sys.platform == 'linux' and 1 <= len(os.sched_getaffinity(0)) <= 2,
            'Linux and one/two admitted CPUs required; no performance claim')
    require(args.out.is_absolute() and not out.exists() and ROOT not in out.parents
            and not any((p/'.git').exists() for p in (out, *out.parents)), 'new external output required')
    cost = json.loads(args.cost.read_bytes())
    require(cost['complete'] is True and cost['host_cleanup'] == {'unsettled_commands': 0, 'errors': []},
            'two-build cost campaign must be complete/settled')
    out.mkdir(parents=True)
    report = dict(complete=False, cost=dict(path=str(args.cost), **pin(args.cost.read_bytes())),
                  scope='four exact selected ABCE async per-GO candidates; no timing/strength/scaling claim',
                  affinity=sorted(os.sched_getaffinity(0)), commands=[], profiles={}, inputs={},
                  limits=dict(AS=2 << 30, CPU=[150, 155], wall=240))

    def save():
        (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')

    source_files = ('engines/experiments/tcec-next/per_go.py',
                    'engines/compact/tiny-entry-d/verify.py', 'engines/tests/chess_oracle.py',
                    'engines/experiments/tcec-scope/verify.py')
    for name in source_files:
        data = (ROOT/name).read_bytes().replace(b'\r\n', b'\n')
        if name in cost['inputs']:
            require(pin(data) == cost['inputs'][name], 'projection changed after cost: '+name)
        target = out/'inputs'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        report['inputs'][name] = pin(data)
    module = load('abce_per_GO_source', out/'inputs'/source_files[0])
    helper = load('abce_owned', out/'inputs'/source_files[1])
    oracle = load('abce_oracle', out/'inputs'/source_files[2])
    scope = load('abce_scope', out/'inputs'/source_files[3])

    class Budget(helper.Budget):
        def left(self, seconds):
            if PENDING is not None:
                raise TimeoutError('probe signal '+str(PENDING))
            return super().left(seconds)

    def finish(owned, status=0):
        if status == 0:
            return scope.finish_owned(owned)
        end = time.monotonic()+owned.budget.left(8)
        while not owned.exited() or owned.group_others():
            require(time.monotonic() < end, 'failure process group did not settle')
            time.sleep(.005)
        owned.pre_reap_other_members = owned.group_others()
        owned.process.wait(timeout=owned.budget.left(3))
        owned.reaped = True
        for reader in (owned.stdout, owned.stderr):
            reader.thread.join(timeout=owned.budget.left(3))
            require(not reader.thread.is_alive() and reader.done and not reader.error, 'failure reader did not join')
        require(owned.process.returncode == status and not owned.stderr.bytes(), 'failure exit/stderr differs')
        owned.finished = True
        return dict(returncode=status, reaped=True, readers_joined=True,
                    original_identity_retained_until_group_settlement=True)

    def settled(owned):
        end = time.monotonic()+owned.budget.left(3)
        while True:
            tasks = scope.task_snapshot(owned.process.pid)
            require(len(tasks) <= 3, 'per-GO thread cap exceeded')
            if len(tasks) == 1:
                return tasks
            require(time.monotonic() < end, 'native did not return to main-only TID')
            time.sleep(.005)

    def check_result(owned, index, board):
        owned.wait_best(index)
        results = [x.split()[1].decode() for x in owned.stdout.bytes().splitlines() if x.startswith(b'bestmove ')]
        move = results[index-1]
        require(move in {str(x) for x in board.legal_moves()}, 'result is illegal for its exact root')
        return move

    def compile_source(directory, source, compiler):
        directory.mkdir(parents=True)
        (directory/'main.c').write_bytes(source)
        driver = directory/'compile'
        driver.write_text('#!/bin/sh\ncd '+shlex.quote(str(directory))+'||exit\nexec '+shlex.join(compiler)+' <main.c\n')
        driver.chmod(0o755)
        owned = helper.Owned(driver, directory/'compiler', Budget(30))
        row = dict(source=pin(source), command=compiler)
        report['commands'].append(row)
        try:
            owned.close_input()
            row['completion'] = finish(owned)
            row['native'] = pin((directory/'x').read_bytes())
        finally:
            row['cleanup'] = owned.cleanup()
            save()
        return directory/'x'

    resource.setrlimit(resource.RLIMIT_AS, (2 << 30,)*2)
    resource.setrlimit(resource.RLIMIT_CPU, (150, 155))
    handlers = {s: signal.signal(s, signal_pending) for s in
                (signal.SIGTERM, signal.SIGINT, signal.SIGALRM, signal.SIGXCPU)}
    signal.alarm(240)
    save()
    try:
        for family in ('A', 'B', 'C', 'E'):
            entry = cost['profiles'][family]
            candidate_dir = Path(entry['attempts'][0]['path'])
            candidate = (candidate_dir/'main.c').read_bytes()
            source = Path(entry['input_path']).read_bytes()
            projected, proof = module.transform_source(source, family=family)
            require(projected == candidate and module.restore_source(candidate, proof) == source,
                    'actual projection/inverse differs from cost')
            require(pin(candidate) == entry['attempts'][0]['source'], 'candidate source changed')
            native, whole = candidate_dir/'native/x', candidate_dir/'x'
            require(pin(native.read_bytes()) == entry['attempts'][0]['native']
                    and pin(whole.read_bytes()) == entry['attempts'][0]['whole'], 'actual product drift')
            directory = out/family
            directory.mkdir()
            row = dict(source=pin(candidate), native=pin(native.read_bytes()), sessions=[])
            report['profiles'][family] = row
            for wrong, bad_family in ((source[:-1]+bytes([source[-1]^1]), family), (source, 'F')):
                try:
                    module.transform_source(wrong, family=bad_family)
                except ValueError as error:
                    require(str(error) == 'exact selected full A/B/C/E source required', 'wrong admission boundary')
                else:
                    raise AssertionError('drift/unsupported family was admitted')
            row['negative_admission_cases'] = 2
            owned = helper.Owned(whole, directory/'source-JIT', Budget(20))
            session = dict(kind='actual-source-JIT', completed=[])
            row['sessions'].append(session)
            try:
                owned.send(b'uci\nisready\n')
                owned.wait_line(b'uciok');owned.wait_line(b'readyok')
                session['startup'] = settled(owned)
                require(pin((Path('/proc')/str(owned.process.pid)/'exe').read_bytes()) == row['native'],
                        'source-JIT native is not the compiled shipping product')
                owned.send(b'position startpos\ngo wtime 60000 btime 60000\n')
                max_ticks, peak, ready = {}, 0, False
                while not any(x.startswith(b'bestmove ') for x in owned.stdout.bytes().splitlines()):
                    owned.budget.left(4)
                    tasks = scope.task_snapshot(owned.process.pid)
                    peak = max(peak, len(tasks));require(len(tasks) <= 3, 'active TID cap exceeded')
                    for tid, data in tasks.items():
                        if tid != owned.process.pid:
                            max_ticks[tid] = max(max_ticks.get(tid, 0), data['cpu_ticks'])
                    if len(tasks) == 3 and not ready:
                        owned.send(b'isready\n')
                        owned.stdout.until(lambda b:b.splitlines().count(b'readyok') >= 2, owned.budget, .75)
                        require(not any(x.startswith(b'bestmove ') for x in owned.stdout.bytes().splitlines()),
                                'ready response waited for search result')
                        ready = True
                    time.sleep(.005)
                require(ready and peak == 3 and sum(x > 0 for x in max_ticks.values()) == 2,
                        'both search workers did not accrue CPU')
                session['active'] = dict(peak=peak, worker_ticks=max_ticks, ready_before_result=True)
                session['completed'].append(check_result(owned, 1, oracle.Board.from_fen()))
                settled(owned)
                for index, (label, moves, board) in enumerate(scope.promotion_fixtures(oracle), 2):
                    owned.send(('position startpos moves '+' '.join(moves)+'\ngo wtime 0 btime 0\n').encode())
                    session['completed'].append(check_result(owned, index, board))
                    settled(owned)
                owned.send(b'quit\n')
                session['completion'] = finish(owned)
            finally:
                session['cleanup'] = owned.cleanup();save()
            for eof in (False, True):
                owned = helper.Owned(native, directory/('pipeline-EOF' if eof else 'pipeline-quit'), Budget(12))
                session = dict(kind='pipeline-active-EOF' if eof else 'pipeline-active-quit', completed=[])
                row['sessions'].append(session)
                try:
                    owned.send(b'uci\nisready\n');owned.wait_line(b'readyok');settled(owned)
                    owned.send(b'position startpos\ngo wtime 60000 btime 60000\ngo wtime 0 btime 0\n'
                               b'position startpos moves e2e4\ngo wtime 0 btime 0\n')
                    for index, moves in enumerate(([], [], ['e2e4']), 1):
                        session['completed'].append(check_result(owned, index, scope.replay(oracle, moves)))
                    settled(owned)
                    owned.send(b'position startpos moves d2d4\ngo wtime 60000 btime 60000\n')
                    until = time.monotonic()+owned.budget.left(1)
                    while len(scope.task_snapshot(owned.process.pid)) != 3:
                        require(time.monotonic() < until, 'active close never observed two live workers')
                        time.sleep(.001)
                    owned.close_input() if eof else owned.send(b'quit\n')
                    session['completion'] = finish(owned)
                    session['active_closing_results'] = len([x for x in owned.stdout.bytes().splitlines()
                                                             if x.startswith(b'bestmove ')])-3
                finally:
                    session['cleanup'] = owned.cleanup();save()

            st,it,ret,pending,handles,count,wt,worker,think,root,select,stop,join,array,ident,depth = module.CONFIG[family]
            support = 'static unsigned long long ng_snap[2];static int ng_seen[2],ng_bad[2],ng_learn[2];'
            support += 'static unsigned long long ng_hash('+wt+'*w){unsigned long long h=1469598103934665603ull;'
            for field in LEARNERS[family]:
                support += '{unsigned char*p=(void*)w->'+field+';for(size_t j=0;j<sizeof w->'+field+';j++)h=(h^p[j])*1099511628211ull;}'
            support += 'return h;}static int ng_nonzero('+wt+'*w){int x=0;'
            for field in LEARNERS[family]:
                support += '{unsigned char*p=(void*)w->'+field+';for(size_t j=0;j<sizeof w->'+field+';j++)x|=p[j];}'
            support += 'return !!x;}'
            worker_sig = st+' void*'+worker+'(void*p){'
            old_worker = module._function(candidate.decode(), worker_sig)
            new_worker = old_worker.replace(worker_sig, worker_sig+wt+'*w=p;int ng_id=w->'+ident+';'
                'unsigned long long ng_root='+root+'.h;'
                'if(ng_seen[ng_id]&&ng_snap[ng_id]!=ng_hash(w))ng_bad[ng_id]=1;ng_seen[ng_id]++;', 1)
            new_worker = new_worker.replace(think+'(p,&'+root+');', think+'(p,&'+root+');'
                'ng_snap[ng_id]=ng_hash(w);ng_learn[ng_id]|=ng_nonzero(w);', 1)
            new_worker = new_worker[:-len(ret+' 0;}')]+'nanosleep(&(struct timespec){0,25000000},0);'
            new_worker += 'if(ng_root!='+root+'.h)exit(70+ng_id);'+ret+' 0;}'
            traced = candidate.decode().replace(old_worker, support+new_worker, 1)
            old_main = module._function(traced, it+' main(void){')
            tail = join+'();for(int ng_id=0;ng_id<2;ng_id++){if(ng_seen[ng_id]!=2||ng_bad[ng_id]||!ng_learn[ng_id])'
            tail += ret+' 80+ng_id;printf("learner %d %d %d\\n",ng_id,ng_seen[ng_id],ng_learn[ng_id]);}'+ret+' 0;}'
            traced = traced.replace(old_main, old_main[:-1]+tail, 1)
            trace_path = compile_source(directory/'learners', traced.encode(), entry['compiler'])
            owned = helper.Owned(trace_path, directory/'learners-runtime', Budget(10))
            trace = {}
            row['actual_learner_trace'] = trace
            try:
                owned.send(b'position startpos\ngo\n');owned.wait_best(1)
                owned.send(b'position startpos moves e2e4\ngo\n');owned.wait_best(2)
                owned.send(b'quit\n');trace['completion']=finish(owned)
                lines=[x.split() for x in owned.stdout.bytes().splitlines() if x.startswith(b'learner ')]
                require(len(lines)==2 and all(x[2:]==[b'2',b'1'] for x in lines), 'learners not retained/nonzero in every worker')
                trace.update(all_worker_entry_hashes_equal_prior_exit=True, workers_with_learning=2,
                             next_position_waited_for_post_result_25ms_return=True)
            finally:
                trace['cleanup']=owned.cleanup();save()

            row['failures']=[]
            for kind, call in (('create',1),('create',2),('join',1)):
                if kind=='create':
                    injection='static int ng_calls;static int ng_create(pthread_t*t,const pthread_attr_t*a,void*(*f)(void*),void*p){return ++ng_calls=='+str(call)+'?11:pthread_create(t,a,f,p);}\n#define pthread_create ng_create\n'
                else:
                    injection='static int ng_join(pthread_t t,void**v){return 22;}\n#define pthread_join ng_join\n'
                marker=candidate.index(b'\ntypedef')
                failed=candidate[:marker+1]+injection.encode()+candidate[marker+1:]
                path=compile_source(directory/(kind+str(call)),failed,entry['compiler'])
                owned=helper.Owned(path,directory/(kind+str(call)+'-runtime'),Budget(8))
                failure=dict(kind=kind,call=call);row['failures'].append(failure)
                try:
                    owned.send(b'position startpos\ngo wtime 60000 btime 60000\n'
                               b'position startpos moves e2e4\ngo wtime 0 btime 0\n')
                    owned.close_input();failure['completion']=finish(owned,2)
                finally:
                    failure['cleanup']=owned.cleanup();save()
        report['complete']=True
    finally:
        report['final_cleanup']=[x.cleanup() for x in tuple(helper.OWNED)]
        report['owned_remaining']=len(helper.OWNED)
        signal.alarm(0)
        for sig,handler in handlers.items():signal.signal(sig,handler)
        save()
    print(json.dumps(dict(complete=report['complete'], profiles=len(report['profiles']),
                         compiles=len(report['commands']), owned_remaining=report['owned_remaining'])))


if __name__=='__main__':
    main()
