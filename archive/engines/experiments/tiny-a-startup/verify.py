#!/usr/bin/env python3
"""Two actual selected-wrapper startup/job/physical-exit observations only."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PINS={'verify.py':'9327ad01dd75bc17f04f400b57d5af3d6891a1abbb7f22aa6222389d50da138f',
      'chess_oracle.py':'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8'}
EXPECTED={'readable':('engine.c',24820,'71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734'),
          'source':('main.c',10855,'f69044dc9ad2869bd3583308ef446a67f3afa6b31b36e7daade6a6b8cd9a3e6a'),
          'native':('native/x',22672,'84ce7fd107783474af8f39aeec7b95c244d475ab797eefd2627b9741b265210a'),
          'whole':('x',5129,'5da238b8f2cc622e5f71a2da07a4f3a787c6679fa29f78b27546800174578527')}
LONG='go wtime 300000 btime 300000 winc 0 binc 0'
ZERO='go wtime 0 btime 0'


def sha(data):return hashlib.sha256(data).hexdigest()


def identity(pid):
    try:
        fields=(Path('/proc')/str(pid)/'stat').read_text().rpartition(') ')[2].split()
        return {'start_time':fields[19],'state':fields[0]}
    except (OSError,IndexError):return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();build=args.build.resolve();out=args.out.resolve();candidate=build/'candidate'
    if sys.platform!='linux':parser.error('Linux /proc observation is required; use WSL Ubuntu')
    if not args.out.is_absolute() or out.exists() or out==REPO or REPO in out.parents or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('a new absolute output outside any Git checkout is required')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    built_bytes=(build/'build.json').read_bytes();built=json.loads(built_bytes)
    if not built.get('complete'):raise ValueError('first-cost build is incomplete')
    form=built['forms']['candidate']
    if built['forms']['control']['whole_bytes']!=5140 or form['independent_identical_attempts']!=2:
        raise ValueError('unexpected fixed first-cost receipt')
    bindings={}
    for key,(relative,size,pin) in EXPECTED.items():
        data=(candidate/relative).read_bytes()
        if len(data)!=size or sha(data)!=pin or form[key+'_sha256']!=pin:
            raise ValueError('candidate identity differs before any launch: '+relative)
        bindings[key]={'path':str(candidate/relative),'bytes':size,'sha256':pin}
    helper_bytes={}
    for name,pin in PINS.items():
        data=(HERE/'tests'/name).read_bytes().replace(b'\r\n',b'\n')
        if b'\r' in data or sha(data)!=pin:raise ValueError('frozen local helper changed: '+name)
        helper_bytes[name]=data
    out.mkdir(parents=True);inputs=out/'inputs';inputs.mkdir()
    (inputs/'build.json').write_bytes(built_bytes)
    (inputs/'startup-verify.py').write_bytes(Path(__file__).read_bytes())
    for name,data in helper_bytes.items():(inputs/name).write_bytes(data)
    report={'complete':False,'scope':'two selected startup/job/physical-exit sessions; no broad core, games, NPS or cancellation-cause claim',
            'build_receipt_sha256':sha(built_bytes),'verifier_sha256':sha(Path(__file__).read_bytes()),
            'candidate_bindings_before_launch':bindings,'helpers':PINS,'sessions':[],
            'cancellation_causality':'unproven','cleanup':[]}
    def save():(out/'runtime.json').write_text(json.dumps(report,indent=2)+'\n')
    save();sys.path.insert(0,str(inputs))
    spec=importlib.util.spec_from_file_location('startup_frozen_shared_verify',inputs/'verify.py')
    shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
    require=shared.require

    def stable(engine):
        engine.assert_threads_stable()
        require(len(engine.task_ids())==3,'fixed three-thread total changed')

    def image(engine):
        proc=Path('/proc')/str(engine.process.pid);link=(proc/'exe').readlink();data=(proc/'exe').read_bytes()
        require(sha(data)==EXPECTED['native'][2],'actual /proc executable differs from pinned native ELF')
        require(str(link).endswith(' (deleted)'),'restored executable was not unlinked')
        native_path=Path(str(link).removesuffix(' (deleted)'))
        require(not native_path.exists() and not native_path.parent.exists(),'private restoration directory remains')
        children={str(tid):(proc/'task'/str(tid)/'children').read_text().split() for tid in engine.task_ids()}
        require(not any(children.values()),'a compiler/restoration helper remains attached after startup')
        return {'exe':str(link),'native_sha256':sha(data),'private_path_absent':True,'private_directory_absent':True,
                'startup_tids':sorted(engine.startup_task_ids),'startup_identities':{str(tid):identity(tid) for tid in engine.startup_task_ids},
                'children_by_tid':children}

    def receipts(engine,index):
        return [{'event_index':i,'received_seconds':stamp,'line':line}
                for i,(stamp,line) in enumerate(engine.stdout_events) if i>=index and line.startswith('bestmove ')]

    def result(lines,board):
        require(len(lines)==1 and lines[0].startswith('bestmove '),'epoch emitted extra/missing minimal output')
        words=lines[0].split();require(len(words)==2,'unexpected selected bestmove format')
        require(words[1] in {str(m) for m in board.legal_moves()},'epoch bestmove is not legal in its root')
        return words[1]

    def completed(engine,row,label,board):
        index=len(engine.stdout_events);engine.send(ZERO);posted=engine.sent_times['go']
        lines=engine.until(lambda line:line.startswith('bestmove '),3);move=result(lines,board)
        require(engine.quiet(.03)==[],'duplicate/stale output after zero-clock completion');stable(engine)
        events=receipts(engine,index);require(len(events)==1,'zero-clock epoch has other stdout receipts')
        row['epochs'].append({'label':label,'command':ZERO,'go_posted_seconds':posted,'bestmove':move,'receipt':events[0]})

    def fenced_result(engine,row,label,board,index,activity,signal):
        engine.send(signal);signal_time=engine.sent_times[signal.split()[0]]
        lines=engine.ready()
        require(lines[-1:]==['readyok'],'queued readiness fence missing')
        move=result(lines[:-1],board)
        events=receipts(engine,index);require(len(events)==1,'fenced epoch lost or duplicated a result')
        ready_events=[{'event_index':i,'received_seconds':stamp} for i,(stamp,line) in enumerate(engine.stdout_events)
                      if i>=index and line=='readyok']
        require(len(ready_events)==1 and events[0]['event_index']<ready_events[0]['event_index'],'physical bestmove did not precede queued readyok')
        require(engine.quiet(.03)==[],'old result crossed its readyok fence');stable(engine)
        activity.update(signal=signal,signal_posted_seconds=signal_time,bestmove_received_seconds=events[0]['received_seconds'],
                        cancellation_causality='unproven',cancellation_coverage='active_work_observed_then_one_physical_result_before_queued_readyok')
        require(activity['active_before_signal'] and events[0]['received_seconds']>signal_time,'active signal/result ordering was not observed')
        row['epochs'].append({'label':label,'bestmove':move,'receipt':events[0],'readyok_fence':ready_events[0],'activity':activity})

    def replacement_active(engine,posted):
        before=shared.process_cpu_ticks(engine);started=time.monotonic()
        lines=engine.quiet(.04);after=shared.process_cpu_ticks(engine)
        ticks=None if before is None or after is None else after-before
        if not lines and not(ticks is not None and ticks>0):
            lines+=engine.quiet(.06);after=shared.process_cpu_ticks(engine);ticks=None if before is None or after is None else after-before
        require(lines==[] and ticks is not None and ticks>0,'replacement GO was not observed unfinished and active after its publication fence')
        stable(engine)
        return {'command':LONG,'go_posted_seconds':posted,'phase_before_signal':'unfinished_with_observed_work',
                'active_before_signal':True,'cpu_ticks_delta':ticks,'observed_seconds':time.monotonic()-started,
                'work_evidence_scope':'whole-process CPU after previous-result readiness fence; no performance or causality claim'}

    try:
        for eof in (False,True):
            # Revalidate the selected bytes immediately before each actual launch.
            require(sha((candidate/'x').read_bytes())==EXPECTED['whole'][2],'wrapper changed after receipt binding')
            engine=shared.Engine({'command':[str(candidate/'x')],'cwd':str(out),'profile':'shipping','startup_threads':3,'startup_timeout':5},out,'eof' if eof else 'quit',5)
            row={'termination':'EOF' if eof else 'quit','pid':engine.process.pid,'epochs':[]};report['sessions'].append(row);save()
            try:
                require(engine.initialize()==['uciok'],'selected startup emitted other UCI metadata');stable(engine)
                row['initial_image']=image(engine);save()
                white=shared.Board.from_fen();black=white.play('e2e4')
                engine.position();completed(engine,row,'white-zero',white)
                engine.position(moves=['e2e4']);completed(engine,row,'black-zero',black)
                for turn in (0,1):
                    old=white if not turn else black;engine.position(moves=[] if not turn else ['e2e4'])
                    index=len(engine.stdout_events)
                    before,activity=shared.begin_lifecycle_search(engine,{'development':False})
                    require(before==[] and activity['active_before_signal'],'initial long GO was not observed active')
                    # A long replacement cannot hide a missing result behind an
                    # immediately completed second epoch. First readyok fences
                    # exactly the old result; CPU observation then binds new work.
                    fenced_result(engine,row,f'replacement-old-{turn}',old,index,activity,LONG)
                    replacement_posted=engine.sent_times['go'];index=len(engine.stdout_events)
                    new_activity=replacement_active(engine,replacement_posted)
                    new=black if not turn else white
                    signal='position startpos moves e2e4' if not turn else 'position startpos'
                    fenced_result(engine,row,f'position-reset-old-{turn}',old,index,new_activity,signal)
                    completed(engine,row,f'position-new-zero-{turn}',new)
                row['preclose_image']=image(engine)
                engine.position();index=len(engine.stdout_events)
                before,activity=shared.begin_lifecycle_search(engine,{'development':False})
                require(before==[] and activity['active_before_signal'],'closing long GO was not observed active')
                engine.close(eof=eof)
                events=receipts(engine,index);require(len(events)==1,'closing epoch lost or duplicated its result')
                move=result([events[0]['line']],white);signal='EOF' if eof else 'quit';posted=engine.sent_times[signal]
                require(events[0]['received_seconds']>posted,'closing result was not observed after the signal')
                activity.update(signal=signal,signal_posted_seconds=posted,bestmove_received_seconds=events[0]['received_seconds'],
                    cancellation_causality='unproven',cancellation_coverage='active_work_observed_then_physical_result_and_exit')
                row['epochs'].append({'label':'closing','bestmove':move,'receipt':events[0],'activity':activity})
                require(not any(reader.is_alive() for reader in engine.readers) and not engine.sampler.is_alive(),'reader/sampler joins did not settle')
                eof_bytes={}
                for name,stream in (('stdout',engine.process.stdout),('stderr',engine.process.stderr)):
                    os.set_blocking(stream.fileno(),False);tail=os.read(stream.fileno(),1)
                    require(tail==b'','reader termination was not followed by physical pipe EOF');eof_bytes[name]=True
                require(not(Path('/proc')/str(engine.process.pid)).exists(),'main PID remains after wait')
                for tid,old_identity in row['initial_image']['startup_identities'].items():
                    current=identity(tid);require(current is None or current['start_time']!=old_identity['start_time'],'an owned startup TID remains')
                descendant_receipt=[]
                for pid,start_time in engine.descendants.items():
                    current=identity(pid);absent=current is None or current['start_time']!=start_time
                    require(absent,'an observed owned descendant remains after physical exit')
                    descendant_receipt.append({'pid':pid,'start_time':start_time,'owned_identity_absent':True})
                require(not engine.stderr,'selected wrapper wrote stderr')
                all_best=receipts(engine,0);require(len(row['epochs'])==9 and len(all_best)==9,'session epoch/receipt total differs')
                require(all(line in ('uciok','readyok') or line.startswith('bestmove ') for _,line in engine.stdout_events),'unexpected selected output')
                row.update(returncode=engine.process.returncode,epoch_count=9,bestmove_count=9,readers_finished=True,sampler_finished=True,
                           physical_pipe_eof=eof_bytes,main_pid_absent=True,startup_owned_tids_absent=True,
                           observed_descendants=descendant_receipt,descendant_scope='startup all-TID child snapshot plus sampled direct-child identities',stderr=engine.stderr)
                save()
            finally:
                if engine.process.poll() is None or not engine.log.closed:
                    report['cleanup'].append({'pid':engine.process.pid,'reason':'incomplete/failing session; owned helper cleanup invoked'})
                    engine.terminate();save()
        report['complete']=True;save();print(json.dumps({'complete':True,'out':str(out),'sessions':2,'epochs':18,'whole_sha256':EXPECTED['whole'][2]}))
    except Exception as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':main()
