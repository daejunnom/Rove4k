#!/usr/bin/env python3
"""Real single-worker C differential checks for the fixed query projections.

The fixture includes the actual shipping search, generation, make and TT
functions. Only the entry name and local observation counters are added.
Timing of this instrumented fixture is not shipping NPS evidence.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PATHS = {
    'A': '/home/stemxstudio/rove4k-tcec-a-final-20261025-v1/main.c',
    'B': '/home/stemxstudio/rove4k-tcec-entry-b-fields-final-20261025-v1/main.c',
    'C': '/home/stemxstudio/rove4k-tcec-entry-c-final-20261025-v1/main.c',
    'E': '/home/stemxstudio/rove4k-tcec-e-final-20261025-v1/main.c',
    'F': '/home/stemxstudio/rove4k-tcec-f2-final-20261025-v1/main.c',
    'F8': '/home/stemxstudio/rove4k-tcec-f8-final-20261025-v2/main.c',
}
CFG = {
    'A': dict(board='E', worker='M', table='N', init='q', set='b', meta='l', make='v', gen='T',
              search='h', stop='X', clock='u', half='aI', nodes='a5', path='aA',
              learners=('zC', 'an', 'ah'), ttinit='B', probe='V', key='aT', data='U', mix='e'),
    'B': dict(board='za', worker='zd', table='qq', init='k', set='M', meta='S', make='h', gen='c',
              search='P', stop='qp', clock='q', half='n', nodes='n', path='k',
              learners=('h', 'c', 'f'), ttinit='B', probe='K', key='h', data='v', mix='b'),
    'C': dict(board='E', worker='ai', table='qq', init='q', set='b', meta='l', make='v', gen='T',
              search='h', stop='qp', clock='u', half='aI', nodes='a5', path='aA',
              learners=('zC', 'an', 'ah'), ttinit='B', probe='V', key='aT', data='U', mix='e'),
    'E': dict(board='E', worker='ai', table='qq', init='q', set='b', meta='l', make='v', gen='T',
              search='h', stop='qp', clock='u', half='aI', nodes='a5', path='aA',
              learners=('zC', 'an', 'ah'), ttinit='B', probe='V', key='aT', data='U', mix='e'),
    'F': dict(board='I', worker='X', table='B', init='o', set='b', meta='l', make='h', gen='T',
              search='qr', stop='V', clock='q', half='a', nodes='e', path='f',
              learners=('h', 'i', 'j'), ttinit='qk', probe='qp', key='a', data='b', mix='r'),
}
CFG['F8'] = CFG['F']


def pin(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def require(value, message):
    if not value:
        raise ValueError(message)


def fixture(source, family):
    c = CFG[family]
    # The prefix has no system include: _POSIX_C_SOURCE remains before the
    # first system header in the exact admitted source.
    prefix = b'static unsigned long long sq_gen,sq_make,sq_eval,sq_see,sq_clock;\n#define main sq_original_main\n'
    observations = [
        (c['clock'] + '(void){').encode(),
    ]
    for old in observations:
        require(source.count(old) == 1, 'clock observation anchor differs')
        source = source.replace(old, old + b'++sq_clock;', 1)
    if family == 'B':
        gen = b'J D c(const za*p,N*f,I sq,I s){'
        make = b'I h(const za*p,N m,za*t){'
        see = b'J I Q(const za*p,N m){'
        source = source.replace(see, see + b'++sq_see;', 1)
        source = source.replace(gen, gen + b'if(f)++sq_gen;', 1)
    elif family in ('F', 'F8'):
        gen = (b'aa' if family == 'F' else b'static') + b' S T(const I*p,Y*f,S g,S s){'
        make = b'S h(const I*p,Y m,I*t){'
        source = source.replace(gen, gen + b'if(f)++sq_gen;', 1)
    else:
        scalar = b'L' if family in ('A', 'E') else b'int'
        gen = scalar + b' T(const E*p,Y*B){'
        make = scalar + b' v(const E*p,Y m,E*w){'
        source = source.replace(gen, gen + b'++sq_gen;', 1)
    require(source.count(make) == 1 and source.count(gen) == 1, 'make/gen observation anchor differs')
    source = source.replace(make, make + b'++sq_make;', 1)
    evals = {'A': b'F=p->s*p->v', 'B': b'zF=p->s*p->v', 'C': b'F=p->s*U(p)',
             'E': b'F=p->s*S(p)', 'F': b'D=p->s*p->v', 'F8': b'D=p->s*p->v'}
    old = evals[family]
    require(source.count(old) == 1, 'evaluation observation anchor differs')
    left, right = old.split(b'=')
    source = source.replace(old, left + b'=(++sq_eval,' + right + b')', 1)
    gen_call = c['gen'] + '(p,sq_moves,0,p->s)' if family == 'B' or family in ('F', 'F8') else c['gen'] + '(p,sq_moves)'
    if family == 'B':
        call = 'P(w,p,sq_depth,sq_alpha,sq_beta,sq_ply,6,best,sq_excluded,1)'
    elif family in ('F', 'F8'):
        call = 'qr(w,p,sq_depth,sq_beta,sq_ply,6,best)'
    else:
        call = 'h(w,p,sq_depth,sq_alpha,sq_beta,sq_ply,6,best)'
    learner_lines = '\n'.join('sq_learn=sq_hash(sq_learn,w->'+field+',sizeof w->'+field+');' for field in c['learners'])
    seed_lines = '\n'.join('sq_seed((int16_t*)w->'+field+',sizeof w->'+field+'/sizeof(int16_t));' for field in c['learners'])
    path_copy = '' if family in ('F', 'F8') else 'memcpy(w->'+c['path']+',qg,qh*sizeof qg[0]);'
    # Actual F table tags encode an exact depth and null-window side.
    tag = '((unsigned long long)(sq_depth*2+2+(sq_forced_score<sq_beta))<<33)' if family in ('F', 'F8') else '((unsigned long long)sq_depth<<33)|((unsigned long long)1<<41)'
    harness = r'''
#undef main
static unsigned long long sq_hash(unsigned long long h,const void*p,size_t n){
 const unsigned char*b=p;while(n--){h^=*b++;h*=1099511628211ULL;}return h;
}
static void sq_seed(int16_t*p,size_t n){for(size_t i=0;i<n;i++)p[i]=(int16_t)((i*17%101)-50);}
static void sq_manual(@BOARD@*p,int side,int which){
 @INIT@(p);p->h^=@META@(p);for(int s=0;s<128;s++)if(!(s&0x88))@SET@(p,s,0);
 p->s=side;p->c=0;p->e=-1;p->@HALF@=0;
 if(which==1){@SET@(p,85,6);@SET@(p,102,5);@SET@(p,119,-6);}
 else if(which==2){@SET@(p,101,6);@SET@(p,86,5);@SET@(p,119,-6);}
 else{@SET@(p,4,6);@SET@(p,116,-6);@SET@(p,side>0?96:23,side);}
 p->h^=@META@(p);p->r=p->h;
}
static void sq_play(@BOARD@*p,int from,int to,int promo){
 @BOARD@ next;unsigned m=MOVE(from,to,promo);if(!@MAKE@(p,m,&next))abort();*p=next;qg[qh++]=p->h;
}
static unsigned sq_first(const @BOARD@*p){
 unsigned sq_moves[512];int n=@GENCALL@;@BOARD@ next;
 for(int i=0;i<n;i++)if(@MAKE@(p,sq_moves[i],&next))return sq_moves[i];return 0;
}
static int sq_call(@WORKER@*w,const @BOARD@*p,int sq_depth,int sq_alpha,int sq_beta,int sq_ply,unsigned sq_excluded,unsigned*best){return @CALL@;}
int main(void){
 @TABLE@=calloc(262144,sizeof*@TABLE@);@WORKER@*w=calloc(1,sizeof*w);if(!@TABLE@||!w)return 2;
 for(int sc=0;sc<24;sc++){
  @BOARD@ p;@INIT@(&p);qh=1;qg[0]=p.h;
  if(sc==1||sc==3){sq_play(&p,20,52,0);sq_play(&p,99,67,0);}
  if(sc==2){sq_play(&p,19,51,0);sq_play(&p,100,68,0);sq_play(&p,6,37,0);}
  if(sc==4||sc==5){sq_manual(&p,-1,sc==4?1:2);qg[0]=p.h;}
  if(sc>=6&&sc<=13){int side=sc<10?1:-1;sq_manual(&p,side,0);qg[0]=p.h;sq_play(&p,side>0?96:23,side>0?112:7,2+(sc-6)%4);}
  if(sc==14){for(int j=0;j<2;j++){sq_play(&p,6,37,0);sq_play(&p,118,85,0);sq_play(&p,37,6,0);sq_play(&p,85,118,0);}}
  if(sc==15||sc==16)p.@HALF@=sc==15?99:100;
  if(sc==17){sq_manual(&p,-1,1);p.@HALF@=100;qg[0]=p.h;}
  if(sc==18){sq_manual(&p,-1,2);p.@HALF@=100;qg[0]=p.h;}
  memset(@TABLE@,0,262144*sizeof*@TABLE@);@TTINIT@();memset(w,0,sizeof*w);@SEED@
  @PATHCOPY@
  atomic_store(&@STOP@,0);qc=UINT64_MAX;
  int sq_depth=(sc==2?3:2),sq_alpha=-30000,sq_beta=30000,sq_ply=0;unsigned sq_excluded=0,best=0;
  if(sc==3||sc==20){sq_depth=0;sq_beta=-20000;}
  if(sc==19)sq_ply=127;
  if(sc==21){unsigned warm=0;sq_call(w,&p,sq_depth,sq_alpha,sq_beta,0,0,&warm);sq_ply=1;}
  if(sc==22||sc==23){
   sq_ply=1;unsigned move=sq_first(&p);if(!move)abort();
   int sq_forced_score=12345;unsigned long long key=p.h^@MIX@(p.r+(unsigned)p.@HALF@);
   unsigned long long packet=move|((unsigned long long)(uint16_t)sq_forced_score<<17)|@TAG@;
   @PROBE@(key,packet);if(sc==23)sq_excluded=move;
  }
  w->@NODES@=0;sq_gen=sq_make=sq_eval=sq_see=sq_clock=0;
  int score=sq_call(w,&p,sq_depth,sq_alpha,sq_beta,sq_ply,sq_excluded,&best);
  if(sc==4||sc==17){if(score!=-30000)abort();}
  if(sc==5||sc==14||sc==16||sc==18||sc==19){if(score!=0)abort();}
  if(sc==22&&score!=12345)abort();
  @BEXCLUDEDASSERT@
  unsigned long long sq_learn=1469598103934665603ULL;@LEARN@
  sq_learn=sq_hash(sq_learn,w->@PATH@,sizeof w->@PATH@);
  unsigned long long sq_tt=1469598103934665603ULL;
  for(size_t i=0;i<262144;i++){sq_tt=sq_hash(sq_tt,&@TABLE@[i].@KEY@,sizeof @TABLE@[i].@KEY@);sq_tt=sq_hash(sq_tt,&@TABLE@[i].@DATA@,sizeof @TABLE@[i].@DATA@);}
  printf("%d %d %u %llu %d %llu %llu %llu %llu %llu %llu %llu\n",sc,score,best,(unsigned long long)w->@NODES@,atomic_load(&@STOP@),sq_learn,sq_tt,sq_see,sq_clock,sq_gen,sq_make,sq_eval);
 }
 free(w);free(@TABLE@);return 0;
}
'''
    mapping = {key.upper(): str(value) for key, value in c.items() if isinstance(value, str)}
    mapping.update(GENCALL=gen_call, CALL=call, SEED=seed_lines, PATHCOPY=path_copy,
                   TAG=tag, LEARN=learner_lines,
                   BEXCLUDEDASSERT='if(sc==23&&score==12345)abort();' if family == 'B' else '')
    for key, value in mapping.items():
        harness = harness.replace('@'+key+'@', value)
    require('@' not in harness, 'unreplaced fixture token')
    return prefix + source + harness.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--families', default='A,B,C,E,F,F8')
    args = parser.parse_args()
    out = args.out.resolve()
    require(sys.platform == 'linux' and args.out.is_absolute() and not out.exists(), 'new absolute Linux output required')
    require(not any((p/'.git').exists() for p in (out, *out.parents)), 'output must be outside Git')
    families = args.families.split(',')
    require(len(families) == len(set(families)) and all(f in PATHS for f in families), 'known unique families required')
    out.mkdir(parents=True)
    frozen = out/'inputs';frozen.mkdir()
    for name in ('search_queries.py', 'check_search_queries.py'):
        (frozen/name).write_bytes((HERE/name).read_bytes().replace(b'\r\n', b'\n'))
    host_path = REPO/'engines/experiments/tcec-scope/build.py'
    (frozen/'host.py').write_bytes(host_path.read_bytes().replace(b'\r\n', b'\n'))
    mod = load('sq_transform_frozen', frozen/'search_queries.py')
    host_mod = load('sq_host_frozen', frozen/'host.py')
    host_mod.LIMITS.update(aggregate_wall=1200, per_command_wall=45, parent_AS=2<<30,
                           parent_CPU=300, child_AS=2<<30, child_CPU=40, tool_output_bytes=1<<20)
    report = dict(format='rove4k-search-query-differential-v1', complete=False, commands=[],
                  inputs={n:pin((frozen/n).read_bytes()) for n in ('search_queries.py','check_search_queries.py','host.py')},
                  scope='Actual shipping functions, one controlled worker, no deadline cancellation; observations are fixture-only, not shipping NPS.', cases=[])
    def save():
        (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    host = None
    try:
        host = host_mod.Host(out, report, save)
        for family in families:
            source = Path(PATHS[family]).read_bytes()
            mod._admit(source, family)
            (frozen/(family+'.c')).write_bytes(source)
            modes = [('control',False),('gen',False),('gen-eval',False)]
            if family != 'B':
                modes.append(('gen-eval-decl',False))
            if family not in ('F','F8'):
                modes += [('control',True),('gen',True),('gen-eval',True)]
            baseline = None
            for tt, qs in modes:
                candidate, proof = mod.transform_source(source,family=family,tt=tt,qs=qs)
                require(mod.restore_source(candidate,proof)==source,'full source inverse differs')
                label=family+'-'+tt+('-qs' if qs else '')
                directory=out/label;directory.mkdir()
                actual=fixture(candidate,family)
                (directory/'main.c').write_bytes(actual)
                command=['cc','-std=c11','-O2','-pthread','-g0','main.c','-o','probe']
                host.run(command,cwd=directory,kind=label+'-cc')
                result=host.run([str(directory/'probe')],cwd=directory,kind=label+'-run')
                rows=[list(map(int,line.split())) for line in result.decode().splitlines()]
                require(len(rows)==24 and all(len(row)==12 and row[0]==i for i,row in enumerate(rows)), 'fixture output shape differs: '+label)
                semantic=[row[:9] for row in rows]
                if baseline is None:
                    baseline=rows
                require(semantic==[row[:9] for row in baseline], 'actual score/move/nodes/stop/learner/TT/SEE/clock differential: '+label)
                if tt!='control':
                    require(rows[22][9]==0 and baseline[22][9]>0,'forced TT did not remove unused gen: '+label)
                if tt=='gen-eval':
                    require(rows[22][11]==0 and baseline[22][11]>0,'forced TT did not remove pure evaluation: '+label)
                if qs:
                    require(rows[20][10]<baseline[20][10], 'stand-pat first-legal case did not reduce make work: '+label)
                report['cases'].append(dict(family=family,tt=tt,qs=qs,source=pin(candidate),fixture=pin(actual),
                    native=pin((directory/'probe').read_bytes()),output=pin(result),
                    semantic_digest=pin(json.dumps(semantic,separators=(',',':')).encode()),
                    rows=rows, actual_semantic_match=True))
                save()
        report['complete']=True
    except BaseException as error:
        report['failure']=dict(type=type(error).__name__,message=str(error))
        raise
    finally:
        if host is not None: host.close()
        save()
    print(json.dumps(dict(complete=True,cases=len(report['cases']),commands=len(report['commands']),out=str(out))))


if __name__=='__main__':
    main()
