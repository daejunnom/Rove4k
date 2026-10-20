#!/usr/bin/env python3
"""Bounded actual C DEV=0 query/board proof; no pool, launcher or games.

The owned A/C fixtures are design inputs only. Both current C sources execute
an adapted fixture, and an independent 64-square oracle checks their children.
FEN loading below is fixture-only; shipping set_position accepts startpos only.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
MASK=(1<<64)-1
OLD_SHA='1f0f18ffee91ecddea3cb31e7553e1d1415e25b3f759cdec4e0f375fcd0b2298'
NEW_SHA='15999279c5bd4690db7129bda032c6b5962acbd814236719cda40755ae31794b'
ORACLE_SHA='aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8'
NAMES=('start','castle-white','castle-black','ep-white','ep-black','pinned-ep',
       'promotion-white','promotion-black','mate','stalemate','pinned-rook','king-target')

def sha(data):return hashlib.sha256(data).hexdigest()
def require(ok,message):
    if not ok:raise AssertionError(message)
def mix(x):
    x=(x+0x9e3779b97f4a7c15)&MASK
    x=((x^(x>>30))*0xbf58476d1ce4e5b9)&MASK
    x=((x^(x>>27))*0x94d049bb133111eb)&MASK
    return x^(x>>31)
def scalar(cells):
    total=0
    for q,v in enumerate(cells):
        if not v:continue
        a=abs(v);advance=q//16 if v>0 else 7-q//16
        center=7-abs(2*(q%16)-7)-abs(2*(q//16)-7)
        n=(0,100,320,330,500,900,0)[a]
        n+=advance*(7 if a==1 else 2 if a==4 else 0)
        n+=center*{1:2,2:9,3:5,4:0,5:2,6:-3}[a]
        total+=n if v>0 else -n
    return total
def snapshot(board,parent_r=None):
    cells=[0]*128
    for i,p in enumerate(board.cells):
        if p!='.':cells[(i//8)*16+i%8]=' PNBRQK'.index(p.upper())*(1 if p.isupper() else -1)
    rights=sum(1<<i for i,c in enumerate('KQkq') if c in board.castling)
    e=-1
    if board.ep>=0 and any(m.dst==board.ep and board.cells[m.src].lower()=='p'
                          and m.src%8!=m.dst%8 for m in board.legal_moves()):
        e=(board.ep//8)*16+board.ep%8
    h=mix(2048+rights)^(mix(2064) if not board.turn else 0)^(mix(2065+(e&7)) if e>=0 else 0)
    for q,v in enumerate(cells):
        if v:h^=mix(q+(v+6)*128)
    r=h if parent_r is None or board.halfmove==0 else (((parent_r<<1)|(parent_r>>63))&MASK)^h
    return {'b':cells,'s':1 if board.turn else -1,'c':rights,'e':e,'k':[cells.index(6),cells.index(-6)],
            'half':board.halfmove,'h':f'{h:016x}','r':f'{r:016x}','raw':scalar(cells),'scalar':scalar(cells)}
def move_number(token):
    q=lambda s:(ord(s[0])-97)+(int(s[1])-1)*16
    return q(token[:2])|(q(token[2:4])<<7)|(('  nbrq'.index(token[4]) if len(token)==5 else 0)<<14)
def key_digest(keys):
    h=1469598103934665603
    for key in keys:h=((h^key)*1099511628211)&MASK
    return f'{h:016x}'
def replay(oracle,tokens):
    board=oracle.Board.from_fen();state=snapshot(board);keys=[int(state['h'],16)]
    for token in tokens:
        board=board.play(token);state=snapshot(board,int(state['r'],16));keys.append(int(state['h'],16))
    return state,keys
def oracle_check(report,oracle,candidate):
    require(report.get('passed') is True and report.get('board_bytes')==168 and report.get('table_terms')==832,'fixture shape')
    shared=report['shared'];queries=shared['queries']
    require(tuple(q['name'] for q in queries)==NAMES,'bounded twelve query identities changed')
    child_count=illegal=0
    for row in queries:
        board=oracle.Board.from_fen(row['fen']);root=snapshot(board)
        require(row['board']==root,'independent root fields/hash/scalar mismatch: '+row['name'])
        legal={str(m):m for m in board.legal_moves()};entries=row['legal_queries']
        require(len(entries)==len(legal) and {e['token'] for e in entries}==legal.keys(),'independent legal set mismatch: '+row['name'])
        for entry in entries:
            token=entry['token'];wanted=snapshot(board.apply(legal[token]),int(root['r'],16))
            require(entry['move']==move_number(token) and entry['child']==wanted,'independent child mismatch: '+row['name']+'/'+token)
        if entries:
            require(row['first']==entries[0]['move'] and row['first_child']==entries[0]['child'],'nullable first differs from preserved generator order')
        else:require(row['first']==0 and row['first_child'] is None,'terminal NULL query')
        require(row['invalid_rejected']==24,'invalid token coverage')
        child_count+=len(entries);illegal+=row['generated_illegal_rejected']
    require(shared['query_stopped_unchanged'] is True,'queries modified stopped')
    seed=snapshot(oracle.Board.from_fen('7k/8/8/8/8/8/8/KR6 w - - 0 1'))
    previous=[mix(i+17) for i in range(4096)];previous[0]=int(seed['h'],16)
    cases={
        'valid-replay':(True,['e2e4','e7e5','g1f3','b8c6']),
        'invalid-middle':(False,None),'invalid-after-prefix':(False,None),
        'shipping-fen-rejected':(False,None),'empty-move-list':(True,[]),
        'history-boundary-4095':(True,(['g1f3','g8f6','f3g1','f6g8']*1024)[:4095]),
        'history-overflow-4096':(False,None)}
    require({r['name'] for r in shared['transactions']}==cases.keys() and len(shared['transactions'])==7,'transaction cases')
    for row in shared['transactions']:
        accepted,tokens=cases[row['name']]
        if accepted:
            wanted,keys=replay(oracle,tokens);history=keys+previous[len(keys):];length=len(keys)
        else:wanted,history,length=seed,previous,2
        require(row['accepted'] is accepted and row['length']==length and row['board']==wanted and row['keys_digest']==key_digest(history),'independent global transaction mismatch: '+row['name'])
    for name in ('production_think','direct_think'):
        row=shared[name] if name=='production_think' else report[name]
        require(all(row[k]==0 for k in ('nodes','depth','score')) and row['id']==7 and row['length']==3,'think reset metadata')
        require(all(row[k] is True for k in ('heuristics_preserved','keys_loaded','tail_keys_preserved','stopped_preserved')),'think private resources changed')
        require(row['best']==(0 if candidate or name=='production_think' else row['seed_best']),'intentional best reset boundary')
        if name=='production_think':require(row['resolved_fallback'] in {e['move'] for e in queries[0]['legal_queries']},'fallback witness illegal')
    return {'roots':len(queries),'legal_children':child_count,'invalid_text_queries':len(queries)*24,
            'generated_illegal_queries':illegal,'transactions':7,'table_terms':832,
            'independent_fields_hash_path_scalar_and_legal_sets':True,'actual_SIMD_equals_scalar':True}
def members(group):
    result=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            fields=(p/'stat').read_text().rsplit(')',1)[1].split()
            if int(fields[2])==group:result.append(int(p.name))
        except (FileNotFoundError,ProcessLookupError,PermissionError):pass
    return result
def run_owned(command,directory,rows,timeout,environment=None):
    def limits():
        resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(45,45))
    process=subprocess.Popen(command,cwd=directory,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        start_new_session=True,preexec_fn=limits,env={**os.environ,'LC_ALL':'C','TZ':'UTC',**(environment or {})})
    row={'command':command,'pid':process.pid,'terminal':False,'group_absent':False,'cleanup':[]};rows.append(row)
    stdout=stderr=b'';error=None
    try:
        stdout,stderr=process.communicate(timeout=timeout)
        if members(process.pid):raise RuntimeError('owned leader exited with descendants')
    except BaseException as exc:
        error=exc
        for sig in (signal.SIGTERM,signal.SIGKILL):
            row['cleanup'].append({'signal':int(sig)})
            try:os.killpg(process.pid,sig)
            except ProcessLookupError:pass
            try:stdout,stderr=process.communicate(timeout=3)
            except subprocess.TimeoutExpired:continue
            until=time.monotonic()+3
            while members(process.pid) and time.monotonic()<until:time.sleep(.02)
            if not members(process.pid):break
    finally:
        row.update(returncode=process.poll(),terminal=process.poll() is not None,group_absent=not members(process.pid),
                   stdout_sha256=sha(stdout),stderr_sha256=sha(stderr))
        (directory/('command-'+str(len(rows))+'.stdout')).write_bytes(stdout)
        (directory/('command-'+str(len(rows))+'.stderr')).write_bytes(stderr)
    if error:raise error
    require(row['terminal'] and row['group_absent'],'owned group remains live')
    require(process.returncode==0,'owned command failed: '+str(process.returncode))
    return stdout,stderr
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();out=args.out.resolve()
    if os.name!='posix':parser.error('Linux/WSL required')
    if not args.out.is_absolute() or out.exists() or any((p/'.git').exists() for p in (out,*out.parents)):parser.error('new external absolute output required')
    out.mkdir(parents=True);frozen=out/'inputs';frozen.mkdir()
    report={'passed':False,'scope':'actual C DEV0 query/child/transaction and pre-stopped think; no pool/launcher/search campaign',
        'engine_wrapper_runs':0,'thread_pool_starts':0,'fixture_executions':0,'commands':[],'runs':[],
        'shipping_FEN_supported':False,'special_FEN_loader':'fixture-only exact renamed old C DEV body',
        'production_think_scope':'fixture adapter applies old GO reset then actual think; candidate actual think owns reset; no actual GO/work publication claim',
        'source_inputs':{},'A_execution_evidence_inherited':False}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        manifest=json.loads((HERE/'inputs.json').read_bytes())
        for section,base in (('control_files',HERE/'control'),('reference_files',HERE/'reference')):
            for rel,pin in manifest[section].items():
                data=(base/rel).read_bytes().replace(b'\r\n',b'\n')
                require(len(data)==pin['bytes'] and sha(data)==pin['sha256'],'owned input differs: '+rel)
                report['source_inputs'][section+'/'+rel]={'bytes':len(data),'sha256':sha(data)}
        paths={'control.c':HERE/'control/control/engines/compact/tiny-entry-c/engine.c',
               'candidate.c':HERE/'control/candidate.c','chess_oracle.py':HERE/'control/control/engines/tests/chess_oracle.py',
               'query-contract.c':HERE/'query-contract.c','query-check.py':Path(__file__),'manifest.json':HERE/'inputs.json'}
        for name,path in paths.items():
            data=path.read_bytes().replace(b'\r\n',b'\n');(frozen/name).write_bytes(data)
            report['source_inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        require(sha((frozen/'control.c').read_bytes())==OLD_SHA and sha((frozen/'candidate.c').read_bytes())==NEW_SHA and sha((frozen/'chess_oracle.py').read_bytes())==ORACLE_SHA,'actual C/oracle identities')
        source=(frozen/'control.c').read_text();start=source.index('int fen(Board *p,const char *s){');end=source.index('\nint verify_board(',start)
        fen=source[start:end].replace('int fen(Board *p,const char *s){','static int fixture_fen_board(Board *p,const char *s){',1)
        (frozen/'fixture-fen.h').write_text(fen+'\n');report['fixture_FEN_sha256']=sha((fen+'\n').encode())
        spec=importlib.util.spec_from_file_location('owned_C_query_oracle',frozen/'chess_oracle.py');oracle=importlib.util.module_from_spec(spec);sys.modules[spec.name]=oracle;spec.loader.exec_module(oracle)
        baseline=None
        for profile,flags in (('O2',['-O2']),('SAN',['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'])):
            for candidate in (False,True):
                name=profile+('-candidate' if candidate else '-control');directory=out/name;directory.mkdir();binary=directory/'contract'
                command=['cc','-std=c11','-pthread','-mavx2','-DDEV=0','-DWORKERS=2','-DTT_BITS=18','-DPLY=128',f'-DCANDIDATE={int(candidate)}',*flags,
                    '-I',str(frozen),'-DENGINE_SOURCE="'+str(frozen/('candidate.c' if candidate else 'control.c'))+'"',str(frozen/'query-contract.c'),'-o',str(binary)]
                row={'profile':profile,'candidate':candidate,'passed':False};report['runs'].append(row);save()
                run_owned(command,directory,report['commands'],90)
                stdout,stderr=run_owned([str(binary)],directory,report['commands'],45,{'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'})
                report['fixture_executions']+=1;require(not stderr,'fixture/sanitizer stderr')
                result=json.loads(stdout);row['counts']=oracle_check(result,oracle,candidate)
                if baseline is None:baseline=result
                expected=json.loads(json.dumps(baseline))
                if candidate:expected['direct_think']['best']=0
                require(result==expected,'unexpected old/new/O2/SAN report difference')
                (directory/'fixture.json').write_bytes(stdout)
                row.update(passed=True,binary_sha256=sha(binary.read_bytes()),fixture_report_sha256=sha(stdout));save()
        require(len(report['runs'])==4 and all(r['passed'] for r in report['runs']),'four exact profiles required')
        require(all(r['terminal'] and r['group_absent'] for r in report['commands']),'owned commands not terminal')
        report.update(passed=True,owned_live_handles=0,only_private_difference='direct preseed-best is cleared by candidate think')
        save();print(json.dumps({'passed':True,'out':str(out),'fixture_executions':4,'results_sha256':sha((out/'results.json').read_bytes())}),flush=True)
    except BaseException as error:
        report['error']=repr(error);report['owned_live_handles']=sum(not (r['terminal'] and r['group_absent']) for r in report['commands']);save();raise
if __name__=='__main__':main()
