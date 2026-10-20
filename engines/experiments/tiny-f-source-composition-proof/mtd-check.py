#!/usr/bin/env python3
"""Two narrow O2 actual-readable F DEV fixtures: attaining MTD witness and same-job node interruption.

DEV counters and the existing diagnostic node budget expose the production
driver. This is not a candidate shipping DEV package or a whole-wrapper run.
Old/new search prefix and MTD driver bytes are separately bound; no widewindow
matrix, new search model, target-body replacement, game or benchmark is used.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
INPUTS_SHA='984bbab15969fad134b1b6237e37be26c544573813adc56cdd0210d7d2e5aeed'
OLD_SHA='dc065b98d99a147f862bd2d4cb0a1349ff79a2da7c1be873d906dff71cc9cd89'
NEW_SHA='ec39b5641ac9fc5ab19a0c919c05e0d68169b461cc1d32afeee83274926becbd'
QUIET="8/6pk/8/8/8/8/PK6/8 w - - 0 1"
def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(value,label):
    if not value:raise ValueError(label)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec)
    sys.modules[name]=obj;spec.loader.exec_module(obj);return obj
def uci(move):
    source,target=move&127,(move>>7)&127;promotion=(move>>14)&7
    return chr(97+(source&7))+str(1+(source>>4))+chr(97+(target&7))+str(1+(target>>4))+("  nbrq"[promotion] if promotion else "")
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();out=args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p/'.git').exists() for p in (out,*out.parents)),'new output outside Git')
    raw_manifest=(HERE/'inputs.json').read_bytes();require(sha(raw_manifest)==INPUTS_SHA,'literal functional closure')
    manifest=json.loads(raw_manifest);out.mkdir();frozen=out/'frozen';frozen.mkdir()
    tools=module('F_mtd_owned_tools',HERE/'control/tools.py')
    report={'complete':False,'scope':__doc__,'source_files':{},'forms':[],'commands':tools.COMMANDS,
        'whole_wrapper_executions':0,'shipping_DEV_package_built':False,'A_C_F_prior_execution_inherited':False}
    def save():(out/'results.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    save();resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:
        for section,prefix in (('control_files','control'),('reference_files','reference')):
            for name,pin in manifest[section].items():
                raw=(HERE/prefix/name).read_bytes();require(len(raw)==pin['bytes'] and sha(raw)==pin['sha256'],'ordinary source '+name)
                dest=frozen/prefix/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
                report['source_files'][prefix+'/'+name]={'bytes':len(raw),'sha256':sha(raw)}
        for name in ('inputs.json','mtd-check.py','mtd-contract.c'):
            raw=(HERE/name).read_bytes();(frozen/name).write_bytes(raw)
            report['source_files'][name]={'bytes':len(raw),'sha256':sha(raw)}
        old=frozen/'control/control/engines/compact/tiny-entry-f/engine.c';new=frozen/'control/candidate.c'
        original=old.read_bytes();candidate=new.read_bytes()
        require(sha(original)==OLD_SHA and sha(candidate)==NEW_SHA,'actual old/new F identities')
        changes=json.loads((frozen/'control/transform.json').read_bytes());forward=original.decode();inverse=candidate.decode()
        for site in changes['sites']:
            require(forward.count(site['old'])==1 and inverse.count(site['new'])==1,'unique seven-site transform')
            forward=forward.replace(site['old'],site['new']);inverse=inverse.replace(site['new'],site['old'])
        require(forward.encode()==candidate and inverse.encode()==original,'full transform inverse')
        prefix=original[:original.index(b'void think(')];new_prefix=candidate[:candidate.index(b'void think(')]
        driver=original[original.index(b'    w->length=game_length;'):original.index(b'static pthread_mutex_t')]
        new_driver=candidate[candidate.index(b'    w->length=game_length;'):candidate.index(b'static pthread_mutex_t')]
        require(prefix==new_prefix and len(prefix)==15340 and driver==new_driver and len(driver)==1354,'unchanged full search/MTD body')
        report['source_identity']={'prefix_bytes':len(prefix),'prefix_sha256':sha(prefix),'MTD_driver_bytes':len(driver),'MTD_driver_sha256':sha(driver),'only_entry_best_reset_before_driver':True}
        oracle=module('F_mtd_legal_oracle',frozen/'reference/engines/tests/chess_oracle.py')
        independent=module('F_mtd_source_only_reference',frozen/'reference/engines/experiments/tiny-f-zero/proof.py')
        expectations={}
        for name,fen,depth in (('quiet',QUIET,3),('completed_one',None,1)):
            board=oracle.Board.from_fen(fen) if fen else oracle.Board.from_fen()
            expectations[name]={'depth':depth,'value':independent.minimax(board,depth)}
        report['fresh_independent_minimax']=expectations
        first=None
        for label,engine in (('old',old),('new',new)):
            directory=out/label;directory.mkdir();binary=directory/'fixture'
            command=['cc','-std=c11','-O2','-pthread','-DDEV=1','-DWORKERS=2','-DTT_BITS=18','-DPLY=128',
                '-DENGINE_SOURCE="'+str(engine)+'"',str(frozen/'mtd-contract.c'),'-o',str(binary)]
            compiled=tools.run(command,directory,timeout=90)
            (directory/'compiler.stdout').write_bytes(compiled.stdout);(directory/'compiler.stderr').write_bytes(compiled.stderr)
            require(compiled.returncode==0,'focused DEV fixture compile')
            executed=tools.run([str(binary)],directory,timeout=30)
            (directory/'fixture.json').write_bytes(executed.stdout);(directory/'fixture.stderr').write_bytes(executed.stderr)
            require(executed.returncode==0 and not executed.stderr,'actual focused DEV driver')
            rows=json.loads(executed.stdout);require(rows['passed'] and rows['DEV']==1 and rows['board_bytes']==176,'focused shape')
            for name,fen in (('quiet',QUIET),('completed_one',None),('interrupted',None)):
                row=rows[name];key='completed_one' if name=='interrupted' else name;expected=expectations[key]
                board=oracle.Board.from_fen(fen) if fen else oracle.Board.from_fen()
                token=uci(row['move']);legal={str(m):m for m in board.legal_moves()}
                require(row['depth']==expected['depth'] and row['score']==expected['value'] and token in legal,'independent exact score/legal witness')
                attained=-independent.minimax(board.apply(legal[token]),expected['depth']-1,1)
                require(attained==row['score'],'root witness attains completed score')
                row['independent_witness_attains']=True
            require(rows['same_job_completed_iteration_retained'] and rows['interrupted']['nodes']==rows['limit'] and rows['interrupted']['stopped']==1,'same-job limit interruption')
            if first is None:first=rows
            else:require(rows==first,'unexpected actual old/new focused driver difference')
            report['forms'].append({'label':label,'passed':True,'fixture_binary_sha256':sha(binary.read_bytes()),
                'fixture_report_sha256':sha(executed.stdout),'driver_calls':3,'result':rows})
            save()
        report.update(complete=True,focused_native_compiles=2,focused_fixture_executions=2,actual_think_calls=6,
            original_search_MTD_body_source_only_reuse=True,new_source_actual_driver_executed=True,
            private_preseed_best_equivalence_claimed=False,owned_live_handles=0)
        save();print(json.dumps({'complete':True,'results_sha256':sha((out/'results.json').read_bytes()),'out':str(out)}))
    except BaseException as error:
        report['error']=repr(error);report['owned_live_handles']=sum(not(r['terminal'] and r['group_absent']) for r in tools.COMMANDS);save();raise
if __name__=='__main__':main()
