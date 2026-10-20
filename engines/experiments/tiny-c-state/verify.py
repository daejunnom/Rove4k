#!/usr/bin/env python3
"""Bind a newly regenerated selected wrapper to restoration and physical exit.

This small selected-only check deliberately leaves historical full rule/core
coverage as exact-hash receipt reuse. It does not run a generic stop/infinite
contract that the minimal shipping interface does not expose.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PINS={'engines/tests/verify.py':'9327ad01dd75bc17f04f400b57d5af3d6891a1abbb7f22aa6222389d50da138f',
      'engines/tests/chess_oracle.py':'aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8'}


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();build=args.build.resolve();out=args.out.resolve()
    if not args.out.is_absolute() or out.exists() or out==REPO or REPO in out.parents or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('a new absolute output outside any Git checkout is required')
    recipe=json.loads((HERE/'inputs.json').read_text())
    built=json.loads((build/'build.json').read_text())
    if not built['complete'] or not built['strict_source_cost_gain'] or built['delta']['whole_bytes']!=-8:
        raise ValueError('the one 5947-byte cache candidate build did not complete')
    selected=next(row for row in built['forms'] if row['id']=='candidate')
    expected={key:selected[key] for key in ('whole_sha256','native_sha256','source_sha256')}
    if expected!={'whole_sha256':'76ed08f657398ac4b8cfbd0ff2230257ab18547f082b4c29af62428d802f33d3',
                  'native_sha256':'c948e31aea9f413614881b8e8e6060e5aa70314dd84b2d9b544e3f20edb99df2',
                  'source_sha256':'dcbfb3e92b52e2ee902055aa7331c068b6b95226f00b1edfc4b63b789405105c'}:
        raise ValueError('selected cache candidate identities differ')
    for name,key in (('x','whole'),('native','native'),('main.c','source')):
        if sha((build/'candidate'/name).read_bytes())!=expected[key+'_sha256']:raise ValueError('selected build identity differs: '+name)
    out.mkdir(parents=True);inputs=out/'inputs';inputs.mkdir()
    report={'complete':False,'scope':'fresh selected restoration, legal clocked moves, startup TIDs, quit/EOF physical fences',
            'whole_sha256':expected['whole_sha256'],'native_sha256':expected['native_sha256'],
            'historical_receipt_reuse':recipe['qualified_receipt'],'fresh_sessions':[],'helpers':{}}
    def save():(out/'runtime.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    for relative,pin in PINS.items():
        data=(REPO/relative).read_bytes().replace(b'\r\n',b'\n')
        if b'\r' in data or sha(data)!=pin:raise ValueError('verifier helper changed: '+relative)
        (inputs/Path(relative).name).write_bytes(data);report['helpers'][relative]=pin
    sys.path.insert(0,str(inputs))
    spec=importlib.util.spec_from_file_location('entry_shared_verify',inputs/'verify.py')
    shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
    def require(value,message):shared.require(value,message)
    def image(engine):
        proc=Path('/proc')/str(engine.process.pid);link=(proc/'exe').readlink()
        data=(proc/'exe').read_bytes()
        require(sha(data)==expected['native_sha256'],'restored process image is not the selected native ELF')
        require(str(link).endswith(' (deleted)'),'native image was not unlinked before execution')
        native_path=Path(str(link).removesuffix(' (deleted)'))
        require(not native_path.exists() and not native_path.parent.exists(),'private restoration path remains on disk')
        children={tid:(proc/'task'/str(tid)/'children').read_text().split() for tid in engine.task_ids()}
        require(not any(children.values()),'compiler/runtime helper still live after UCI initialization')
        descriptors=sorted(int(fd.name) for fd in (proc/'fd').iterdir())
        require(descriptors==[0,1,2],'unexpected live file descriptor after restoration')
        return {'exe':str(link),'image_sha256':sha(data),'private_path_absent':True,
                'startup_tids':sorted(engine.startup_task_ids),'children_by_tid':children,
                'file_descriptors':descriptors,'wrapper_pid_equals_native_pid':True}
    def best(engine,board,command):
        engine.send(command);lines=engine.until(lambda line:line.startswith('bestmove '),3)
        moves=[line.split()[1] for line in lines if line.startswith('bestmove ')]
        require(len(moves)==1 and moves[0] in {str(m) for m in board.legal_moves()},'clocked result is not exactly one legal move')
        require(engine.quiet(.03)==[],'duplicate/unexpected output after completed epoch')
        engine.assert_threads_stable();return moves[0]
    try:
        report['independent_oracle_self_check']=shared.self_check()
        for eof in (False,True):
            engine=shared.Engine({'command':[str(build/'candidate/x')],'profile':'shipping','startup_threads':3,'startup_timeout':5},out,'eof' if eof else 'quit',5)
            try:
                require(engine.initialize()==['uciok'],'selected minimal uci output differs')
                row={'termination':'EOF' if eof else 'quit','image':image(engine),'completed':[]}
                board=shared.Board.from_fen();engine.position()
                row['completed'].append({'clock':'white zero','bestmove':best(engine,board,'go wtime 0 btime 0')})
                board=board.play('e2e4');engine.position(moves=['e2e4'])
                row['completed'].append({'clock':'black zero','bestmove':best(engine,board,'go wtime 0 btime 0')})
                engine.position();board=shared.Board.from_fen()
                start=time.monotonic();move=best(engine,board,'go')
                row['completed'].append({'clock':'bare finite default','bestmove':move,'wall_seconds':time.monotonic()-start,
                                         'scope':'bounded completion, not a performance benchmark'})
                before,activity=shared.begin_lifecycle_search(engine,{'development':False})
                require(activity['active_before_signal'],'clocked search was not observed active before quit/EOF')
                engine.close(eof=eof)
                receipts=[(stamp,line) for stamp,line in engine.stdout_events if stamp>=activity['go_posted_seconds'] and line.startswith('bestmove ')]
                require(len(receipts)==1 and receipts[0][1].split()[1] in {str(m) for m in board.legal_moves()},'closing epoch lost/duplicated/invalid bestmove')
                require(not any(reader.is_alive() for reader in engine.readers),'output readers did not observe physical EOF')
                require(not (Path('/proc')/str(engine.process.pid)).exists(),'main process remains after wait')
                signal_name='EOF' if eof else 'quit'
                activity.update(signal=signal_name,signal_posted_seconds=engine.sent_times[signal_name],
                    bestmove_received_seconds=receipts[0][0],cancellation_coverage='active_search_physical_exit_observed',
                    cancellation_causality='unproven')
                row.update(activity=activity,returncode=engine.process.returncode,
                    exactly_one_closing_bestmove=True,process_absent=True,readers_finished=True,stderr=engine.stderr)
                report['fresh_sessions'].append(row);save()
            finally:
                if engine.process.poll() is None:engine.terminate()
        report['complete']=True;save();print(json.dumps({'complete':True,'out':str(out),'sessions':2,'whole_sha256':expected['whole_sha256']}))
    except Exception as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':main()
