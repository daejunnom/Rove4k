#!/usr/bin/env python3
"""Bounded actual E DEV=0 query/model/order proof; no pool, launcher or games.

The owned A/C/F fixtures are design inputs only. Both exact E sources execute
an adapted fixture, and an independent 64-square oracle checks their children,
sixteen evaluation features and five ordering features. DEV order dispatch is
bound by exact source, not executed as a DEV command or qualified DEV image.
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
OLD_SHA='0a7fe69022051e1893ffbd52ade7a2fbb3f342fe20b581bb786d6997b46fb712'
NEW_SHA='c5f005b107f5d3fa93a4043fece78de848e248e67c4e58831a688efae8f2941d'
ORACLE_SHA='aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8'
INPUTS_SHA='6c087b741124bc9ac5c311de1c19f6ad17ce341af10d13c5b1a5222251aa38f5'
WEIGHTS=(100,320,330,500,900,3,8,5,2,1,-3,6,-12,-8,24,10,16,-1,12,2,4)
MODEL_SIGNED16_LE_SHA='eff32c8c6fe02961cb2adfd923897393bfc3448f3650116ece358cc68c79ddc6'
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
def center(square):
    file,rank=square%8,square//8
    return min(file,7-file)+min(rank,7-rank)
def model(board):
    features=[0]*16;features[15]=1 if board.turn else -1
    pawns=[[0]*8 for _ in range(2)];bishops=[0,0]
    for square,piece in enumerate(board.cells):
        if piece=='.':continue
        black=not piece.isupper();sign=-1 if black else 1
        kind=' PNBRQK'.index(piece.upper())
        if kind<6:features[kind-1]+=sign
        features[kind+4]+=sign*center(square)
        if kind==1:
            pawns[black][square%8]+=1
            relative_rank=7-square//8 if black else square//8
            features[11]+=sign*(relative_rank-1)
        if kind==3:bishops[black]+=1
    for black in range(2):
        sign=-1 if black else 1
        features[14]+=sign*int(bishops[black]>1)
        for file,n in enumerate(pawns[black]):
            if not n:continue
            features[12]+=sign*(n-1)
            if not (file and pawns[black][file-1]) and not (file<7 and pawns[black][file+1]):
                features[13]+=sign*n
    white=sum(weight*value for weight,value in zip(WEIGHTS[:16],features))
    return features,white,max(-20000,min(20000,white))
def ordering(board,move,normalized_ep):
    piece=board.cells[move.src];kind=' PNBRQK'.index(piece.upper())
    victim=board.cells[move.dst]
    victim_kind=0 if victim=='.' else ' PNBRQK'.index(victim.upper())
    to88=(move.dst//8)*16+move.dst%8
    if kind==1 and to88==normalized_ep and not victim_kind:victim_kind=1
    material=(0,*WEIGHTS[:5],0)
    prom=0 if not move.promotion else '  nbrq'.index(move.promotion)
    features=[material[victim_kind] if victim_kind else 0,
              material[kind] if victim_kind else 0,
              material[prom]-material[1] if prom else 0,
              center(move.dst)-center(move.src),
              (move.dst//8-move.src//8)*(1 if piece.isupper() else -1) if kind==1 else 0]
    return features,sum(weight*value for weight,value in zip(WEIGHTS[16:],features))
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
    _,white,raw=model(board);side=1 if board.turn else -1
    return {'b':cells,'s':side,'c':rights,'e':e,'k':[cells.index(6),cells.index(-6)],
            'half':board.halfmove,'h':f'{h:016x}','r':f'{r:016x}','white':white,'raw':raw,'eval':side*raw}
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
    require(report.get('passed') is True and report.get('board_bytes')==168 and
            report.get('shipping_board_has_hce_v') is False,'shipping DEV0 Board shape')
    require(report.get('model_coefficients')==21 and report.get('model_weights')==list(WEIGHTS),'exact E model storage')
    require(sha(b''.join(w.to_bytes(2,'little',signed=True) for w in WEIGHTS))==MODEL_SIGNED16_LE_SHA,'E signed16 model identity')
    shared=report['shared'];queries=shared['queries']
    require(tuple(q['name'] for q in queries)==NAMES,'bounded twelve query identities changed')
    child_count=illegal=order_count=0;eval_coverage=[False]*16;order_coverage=[False]*5
    def observe_eval(board):
        for i,value in enumerate(model(board)[0]):eval_coverage[i]|=value!=0
    for row in queries:
        board=oracle.Board.from_fen(row['fen']);root=snapshot(board)
        require(row['board']==root,'independent root fields/hash/model mismatch: '+row['name'])
        observe_eval(board)
        legal={str(m):m for m in board.legal_moves()};entries=row['legal_queries']
        require(len(entries)==len(legal) and {e['token'] for e in entries}==legal.keys(),'independent legal set mismatch: '+row['name'])
        for entry in entries:
            token=entry['token'];child=board.apply(legal[token]);wanted=snapshot(child,int(root['r'],16))
            require(entry['move']==move_number(token) and entry['child']==wanted,'independent child mismatch: '+row['name']+'/'+token)
            features,wanted_order=ordering(board,legal[token],root['e'])
            require(entry['order']==wanted_order,'E ordering must use pre-move parent: '+row['name']+'/'+token)
            for i,value in enumerate(features):order_coverage[i]|=value!=0
            observe_eval(child);order_count+=1
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
            'generated_illegal_queries':illegal,'transactions':7,'model_coefficients':21,
            'parent_orderings_checked':order_count,'evaluation_features_with_nonzero_observation':eval_coverage,
            'ordering_features_with_nonzero_observation':order_coverage,
            'independent_fields_hash_path_model_and_legal_sets':True,
            'actual_E_model_equals_independent_64_square_dot':True,
            'actual_E_order_equals_independent_parent_formula':True,
            'all_features_activated_not_required_or_claimed':True}
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
    report={'passed':False,'scope':'actual E DEV0 query/model/order/transaction and pre-stopped think; no pool/launcher/search campaign',
        'engine_wrapper_runs':0,'thread_pool_starts':0,'fixture_executions':0,'commands':[],'runs':[],
        'DEV_command_executions':0,'DEV_image_qualification_executions':0,
        'shipping_native_identity_inferred_from_fixtures':False,
        'shipping_FEN_supported':False,'special_FEN_loader':'fixture-only exact renamed old E DEV body',
        'production_think_scope':'fixture adapter applies old GO reset then actual think; candidate actual think owns reset; no actual GO/work publication claim',
        'DEV_order_scope':'exact old/new dispatcher source binds parent Board; fixture checks actual DEV0 tiny_order on that parent; no DEV command execution',
        'source_inputs':{},'other_family_execution_evidence_inherited':False}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        manifest_raw=(HERE/'inputs.json').read_bytes()
        require(sha(manifest_raw)==INPUTS_SHA and b'\r' not in manifest_raw,'literal raw LF input manifest differs')
        manifest=json.loads(manifest_raw)
        report['inputs_manifest_sha256']=sha(manifest_raw);report['owned_inputs_raw_LF_required']=True
        for section,base in (('control_files',HERE/'control'),('reference_files',HERE/'reference')):
            for rel,pin in manifest[section].items():
                data=(base/rel).read_bytes()
                require(b'\r' not in data and len(data)==pin['bytes'] and sha(data)==pin['sha256'],'owned raw LF input differs: '+rel)
                report['source_inputs'][section+'/'+rel]={'bytes':len(data),'sha256':sha(data)}
        paths={'control.c':HERE/'control/control/engines/compact/tiny-entry-e/engine.c',
               'candidate.c':HERE/'control/candidate.c','chess_oracle.py':HERE/'control/control/engines/tests/chess_oracle.py',
               'query-contract.c':HERE/'query-contract.c','query-check.py':Path(__file__),'manifest.json':HERE/'inputs.json'}
        for name,path in paths.items():
            data=path.read_bytes();require(b'\r' not in data,'frozen input must be raw LF: '+name)
            (frozen/name).write_bytes(data)
            report['source_inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        require(sha((frozen/'control.c').read_bytes())==OLD_SHA and sha((frozen/'candidate.c').read_bytes())==NEW_SHA and sha((frozen/'chess_oracle.py').read_bytes())==ORACLE_SHA,'actual E/oracle identities')
        source=(frozen/'control.c').read_text();new_source=(frozen/'candidate.c').read_text()
        old_order='wait();Move m=parse(&position,line+6);printf("order %d\\n",m?tiny_order(&position,m):INT_MIN);fflush(stdout);'
        new_order='wait();Board c;Move m=parse(&position,line+6,&c);printf("order %d\\n",m?tiny_order(&position,m):INT_MIN);fflush(stdout);'
        require(source.count(old_order)==1 and new_source.count(new_order)==1 and
                'tiny_order(&c,m)' not in new_source,'DEV order dispatcher parent-source binding')
        marker='void think(Worker *w,const Board *p)'
        require(source.split(marker)[0]==new_source.split(marker)[0] and len(source.split(marker)[0].encode())==18042,
                'E model/Board/search prefix source identity')
        report['DEV_order_dispatch_source_binding']={'old_fragment_sha256':sha(old_order.encode()),
            'candidate_fragment_sha256':sha(new_order.encode()),'parent_argument':'&position',
            'source_only':True,'actual_DEV_command_executed':False,'unchanged_prefix_bytes':18042}
        start=source.index('int fen(Board *p,const char *s){');end=source.index('\nint verify_board(',start)
        fen=source[start:end].replace('int fen(Board *p,const char *s){','static int fixture_fen_board(Board *p,const char *s){',1)
        (frozen/'fixture-fen.h').write_text(fen+'\n');report['fixture_FEN_sha256']=sha((fen+'\n').encode())
        spec=importlib.util.spec_from_file_location('owned_E_query_oracle',frozen/'chess_oracle.py');oracle=importlib.util.module_from_spec(spec);sys.modules[spec.name]=oracle;spec.loader.exec_module(oracle)
        baseline=None
        for profile,flags in (('O2',['-O2']),('SAN',['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'])):
            for candidate in (False,True):
                name=profile+('-candidate' if candidate else '-control');directory=out/name;directory.mkdir();binary=directory/'contract'
                command=['cc','-std=c11','-pthread','-DDEV=0','-DWORKERS=2','-DTT_BITS=18','-DPLY=128',f'-DCANDIDATE={int(candidate)}',*flags,
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
