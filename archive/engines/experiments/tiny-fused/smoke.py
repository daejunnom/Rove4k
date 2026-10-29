#!/usr/bin/env python3
"""One actual failed-candidate wrapper: identity, clocks, fixed pool and joins."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT in args.out.parents:parser.error('new external output required')
    args.out.mkdir(parents=True)
    helpers=args.out/'helpers';helpers.mkdir()
    for name in ('verify.py','chess_oracle.py'):shutil.copyfile(ROOT/'engines/tests'/name,helpers/name)
    sys.path.insert(0,str(helpers))
    from verify import Engine,Board,search,begin_lifecycle_search,finish_signalled_search,record_completed_signal
    record=next(r for r in json.loads(args.build.read_text())['forms'] if r['id']=='fused')
    path=Path(record['wrapper']);assert sha(path.read_bytes())==record['whole_sha256']
    spec={'id':'fused-actual','command':[str(path)],'profile':'shipping','workers':2,'startup_threads':3,
          'max_threads':3,'startup_timeout':60,'expected_program_sha256':record['whole_sha256']}
    engine=Engine(spec,args.out,'actual',10);report={'passed':False,'scope':'one actual wrapper targeted smoke; no full suite, NPS or strength campaign'}
    try:
        engine.initialize();engine.assert_threads_stable()
        proc=Path('/proc')/str(engine.process.pid);image=(proc/'exe').read_bytes();link=os.readlink(proc/'exe')
        assert sha(image)==record['native_sha256']
        assert link.endswith(' (deleted)') and not Path(link.removesuffix(' (deleted)')).parent.exists()
        assert not any((task/'children').read_text().strip() for task in (proc/'task').iterdir())
        report.update(wrapper_sha256=record['whole_sha256'],native_sha256=sha(image),startup_tids=sorted(engine.startup_task_ids),
                      temporary_removed_before_input=True,no_compiler_children=True)
        engine.position();report['zero_clock_white']=search(engine,Board.from_fen(),'go wtime 0 btime 0',timeout=2,require_info=False)
        before,activity=begin_lifecycle_search(engine,None)
        engine.send('stop');_,move=finish_signalled_search(engine,before);Board.from_fen().play(move)
        record_completed_signal(engine,activity,'stop');report['stop']=activity
        assert not any(line.startswith('bestmove ') for line in engine.ready())
        engine.position(moves=['e2e4']);black=Board.from_fen().play('e2e4')
        report['zero_clock_black']=search(engine,black,'go wtime 0 btime 0',timeout=2,require_info=False)
        before,activity=begin_lifecycle_search(engine,None)
        engine.close()
        receipts=[line for stamp,line in engine.stdout_events if stamp>=activity['go_posted_seconds'] and line.startswith('bestmove ')]
        assert len(receipts)==1;black.play(receipts[0].split()[1]);record_completed_signal(engine,activity,'quit')
        report['quit']=activity
        assert not proc.exists() and not any(reader.is_alive() for reader in engine.readers)
        report.update(passed=True,runtime_absent=True,readers_joined=True)
    finally:
        if engine.process.poll() is None:engine.terminate()
        (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
