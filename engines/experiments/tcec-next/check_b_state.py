#!/usr/bin/env python3
"""Bounded actual B transition/walker/LVA/search comparison for occupancy-only.

Raw shipping compiles are separate from the controlled-clock fixture.  The
fixture calls the actual c/h/Q/P, compares semantic Board projections instead
of unequal struct bytes, validates occupancy against mailbox independently,
and hashes the recursive Q move trace including illegal-origin attempts.
No public FEN command or product diagnostic branch is introduced.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import signal
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE_MODULE = 'engines/experiments/tcec-next/b_state.py'
HOST_MODULE = 'engines/experiments/tcec-scope/build.py'
HOST_PIN = 'fc916e798952cff1c915a6846e758874bc2d858b3c59dec73870b95c7e3d4828'
CLOCK = b'D q(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);l(D)t.tv_sec*1000+t.tv_nsec/1000000;}'
HOOK_PREFIX = b'static unsigned fixture_clock_ticks,fixture_clock_trip=4294967295u,fixture_query_visits;static unsigned long long fixture_query_digest=1469598103934665603ULL;\n'
HOOK_CLOCK = b'D q(void){++fixture_clock_ticks;l fixture_clock_ticks>=fixture_clock_trip?UINT64_MAX:0;}'
Q_ENTRY = b'J I Q(const za*p,N m){'
Q_HOOK = Q_ENTRY + b'fixture_query_digest=(fixture_query_digest^((D)m*2+(p->s<0)))*1099511628211ULL;++fixture_query_visits;'

HARNESS = r'''
#define main fixture_unused_engine_main
#include "fixture-core.c"
#undef main
_Static_assert(sizeof(D)==8&&sizeof(int)==4,"Linux64 Board layout contract");
static D fixture_digest=1469598103934665603ULL;
static unsigned fixture_positions,fixture_searches,fixture_see,fixture_interrupts;
static void fixture_add(D v){fixture_digest=(fixture_digest^v)*1099511628211ULL;}
static void fixture_clock(unsigned trip){fixture_clock_ticks=0;fixture_clock_trip=trip;fixture_query_visits=0;fixture_query_digest=1469598103934665603ULL;qc=UINT64_MAX;atomic_store(&qp,0);}
static void fixture_board(const za*p){
 D types[2][7]={{0}};
 for(int i=0;i<128;i++){fixture_add((unsigned char)p->b[i]);if(!(i&136)&&p->b[i]){int side=p->b[i]<0,kind=abs(p->b[i]);types[side][0]|=o(i);types[side][kind]|=o(i);}}
 FIXTURE_OCCUPANCY_CHECK
 for(int i=0;i<2;i++)fixture_add(types[i][0]);
 fixture_add(p->s);fixture_add(p->c);fixture_add(p->e);fixture_add(p->k[0]);fixture_add(p->k[1]);
 fixture_add(p->n);fixture_add(p->v);fixture_add(p->h);fixture_add(p->r);
}
static void fixture_search(const za*p,int repeat){
 zd*w=qr;memset(w,0,sizeof*w);w->i=1;
 for(int i=0;i<128;i++)for(int j=0;j<128;j++)w->h[i][j]=(i*7+j*11)%1024-512;
 for(int i=0;i<13;i++)for(int j=0;j<13;j++)w->c[i][j]=(i*3+j*13)%1024-512;
 for(int i=0;i<1024;i++)w->f[i]=(i*17)%1024-512;
 memset(qq,0,(1<<18)*sizeof*qq);B();qh=repeat?5:1;
 for(int i=0;i<qh;i++)w->k[i]=p->h;
 fixture_clock(4294967295u);N best=0;
 int score=P(w,p,3,-30000,30000,0,6,&best,0,1);
 fixture_add(score);fixture_add(best);fixture_add(w->n);fixture_add(fixture_query_visits);fixture_add(fixture_query_digest);fixture_add(fixture_clock_ticks);
 for(int i=0;i<128;i++)for(int j=0;j<128;j++)fixture_add(w->h[i][j]);
 for(int i=0;i<13;i++)for(int j=0;j<13;j++)fixture_add(w->c[i][j]);
 for(int i=0;i<1024;i++)fixture_add(w->f[i]);fixture_searches++;
}
static void fixture_position(const za*p,int search){
 N moves[512];int count=c(p,moves,0,p->s);fixture_add(count);fixture_board(p);
 for(int side=-1;side<=1;side+=2)for(int sq=0;sq<128;sq++)if(!(sq&136))fixture_add(c(p,0,sq,side));
 for(int i=0;i<count;i++){
  za child;int valid=h(p,moves[i],&child);fixture_add(moves[i]);fixture_add(valid);
  if(valid)fixture_board(&child);
  if(moves[i]&8){
   fixture_clock(4294967295u);int see=Q(p,moves[i]);unsigned ticks=fixture_clock_ticks;
   fixture_add(see);fixture_add(fixture_query_visits);fixture_add(fixture_query_digest);fixture_add(ticks);fixture_see++;
   for(unsigned trip=1;trip<=ticks+1&&trip<=5;trip++){
    fixture_clock(trip);fixture_add(Q(p,moves[i]));fixture_add(fixture_query_visits);fixture_add(fixture_query_digest);fixture_add(fixture_clock_ticks);fixture_add(atomic_load(&qp));fixture_interrupts++;
   }
  }
 }
 if(search){fixture_search(p,0);fixture_search(p,1);}fixture_positions++;
}
static void fixture_finish(za*p){p->h^=S(p);p->r=p->h;}
int main(void){
 printf("layout=%zu\n",sizeof(za));qq=calloc(1<<18,sizeof*qq);if(!qq)return 2;B();
 za position;k(&position);
 for(int step=0;step<20;step++){
  fixture_position(&position,step%5==0);
  N moves[512];int count=c(&position,moves,0,position.s),found=0;
  for(int i=0;i<count;i++){int at=(i+step*17)%count;za child;if(h(&position,moves[at],&child)){position=child;found=1;break;}}
  if(!found)break;
 }
 for(int side=-1;side<=1;side+=2){
  za promotion={0};promotion.s=side;promotion.e=-1;M(&promotion,4,6);M(&promotion,116,-6);
  M(&promotion,side>0?96:16,side);M(&promotion,side>0?113:1,-side*4);fixture_finish(&promotion);fixture_position(&promotion,1);
  za ep={0};ep.s=side;ep.e=side>0?83:35;M(&ep,4,6);M(&ep,116,-6);M(&ep,side>0?68:52,side);M(&ep,side>0?67:51,-side);fixture_finish(&ep);fixture_position(&ep,0);
  za castle={0};castle.s=side;castle.e=-1;castle.c=15;M(&castle,4,6);M(&castle,116,-6);
  M(&castle,0,4);M(&castle,7,4);M(&castle,112,-4);M(&castle,119,-4);fixture_finish(&castle);fixture_position(&castle,0);
 }
 /* After Bc4xd5, c6 is the first pawn attacker and is pinned to Kc8.
    e6 remains a legal next origin of the same kind. */
 za pin={0};pin.s=1;pin.e=-1;M(&pin,0,6);M(&pin,114,-6);M(&pin,2,4);M(&pin,50,3);M(&pin,67,-1);M(&pin,82,-1);M(&pin,84,-1);fixture_finish(&pin);fixture_position(&pin,0);
 printf("%016llx positions=%u searches=%u SEE=%u interruptions=%u\n",(unsigned long long)fixture_digest,fixture_positions,fixture_searches,fixture_see,fixture_interrupts);
 free(qq);return 0;
}
'''


def require(value, message):
    if not value:
        raise ValueError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(sys.platform == 'linux' and args.source.is_absolute() and args.out.is_absolute()
            and not out.exists() and not any((p/'.git').exists() for p in (out,*out.parents)),
            'Linux, explicit source and new external output required')
    out.mkdir(parents=True)
    inputs = out/'inputs';inputs.mkdir()
    # Freeze named modules before the first compiler is launched.
    provenance = {}
    for name, relative in (('b_state.py',SOURCE_MODULE), ('host.py',HOST_MODULE),
                           ('check_b_state.py','engines/experiments/tcec-next/check_b_state.py')):
        data=(REPO/relative).read_bytes().replace(b'\r\n',b'\n')
        (inputs/name).write_bytes(data)
        provenance[relative]={'origin':str(REPO/relative),'bytes':len(data)}
    module=load('B_state_source',inputs/'b_state.py')
    for relative,row in provenance.items():
        row.update(module.pin((REPO/relative).read_bytes().replace(b'\r\n',b'\n')))
    require(provenance[HOST_MODULE]['sha256']==HOST_PIN, 'frozen development host differs')
    source=args.source.read_bytes();candidate,proof=module.transform_source(source,variant='branch')
    require(module.restore_source(candidate,proof)==source, 'B state full inverse differs')
    host_module=load('B_state_host',inputs/'host.py')
    host_module.LIMITS.update(aggregate_wall=180,per_command_wall=45,parent_AS=2<<30,
                              child_AS=2<<30,parent_CPU=120,child_CPU=45)
    report={'complete':False,'scope':'raw native compiles plus controlled-clock actual c/h/Q/P and UBSan',
            'source_path':str(args.source),'input':module.pin(source),'candidate':module.pin(candidate),
            'proof':proof,'source_inputs':provenance,'commands':[], 'cases':{}}
    def save():
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    save();prior=signal.signal(signal.SIGCHLD,signal.SIG_DFL)
    host=host_module.Host(out,report,save);failure=None
    try:
        outputs={}
        for label,data in (('baseline',source),('candidate',candidate)):
            directory=out/label;directory.mkdir();(directory/'main.c').write_bytes(data)
            host.run(['cc','-std=c11','-Os','-pthread','-x','c','-','-o','x'],cwd=directory,kind=label+'-shipping-native',data=data)
            native=module.pin((directory/'x').read_bytes())
            require(data.count(CLOCK)==data.count(Q_ENTRY)==1,'one exact clock/Q test port required')
            fixture_core=HOOK_PREFIX+data.replace(CLOCK,HOOK_CLOCK).replace(Q_ENTRY,Q_HOOK)
            (directory/'fixture-core.c').write_bytes(fixture_core)
            assertion=('for(int side=0;side<2;side++)if(p->a[side]!=types[side][0])abort();' if label=='candidate'
                       else 'for(int side=0;side<2;side++)for(int kind=0;kind<7;kind++)if(p->a[side][kind]!=types[side][kind])abort();')
            harness=HARNESS.replace('FIXTURE_OCCUPANCY_CHECK',assertion)
            (directory/'fixture.c').write_text(harness)
            values=[]
            for sanitize in (False,True):
                flags=['cc','-std=c11','-O1' if sanitize else '-Os','-pthread']
                if sanitize:flags+=['-g','-fsanitize=undefined','-fno-sanitize-recover=all']
                output='fixture-ubsan' if sanitize else 'fixture'
                host.run(flags+['fixture.c','-o',output],cwd=directory,kind=label+'-'+output+'-compile')
                text=host.run(['./'+output],cwd=directory,kind=label+'-'+output+'-actual-functions').decode('ascii')
                lines=text.splitlines();require(len(lines)==2,'explicit layout and semantic digest lines required')
                layout=int(lines[0].removeprefix('layout='))
                values.append({'layout':layout,'semantic':lines[1]})
            require(values[0]==values[1], 'UBSan and raw actual function digests differ')
            report['cases'][label]={'native':native,'fixture':values[0],
                                    'fixture_core':module.pin(fixture_core),
                                    'fixture_source':module.pin(harness.encode())}
            outputs[label]=values[0];save()
        require(outputs['baseline']['semantic']==outputs['candidate']['semantic'], 'actual state/query/search/learner digest differs')
        require((outputs['baseline']['layout'],outputs['candidate']['layout'])==(288,192), 'measured Linux Board layout differs')
        report['actual_functions_equal']=True
        report['measured_Board_bytes']={'baseline':288,'candidate':192,'delta':-96}
        report['query_checkpoint_scope']='controlled clock; includes query-entry trace and incomplete checkpoints, not shipping speed'
    except BaseException as exc:
        failure=exc;report['error']={'type':type(exc).__name__,'message':str(exc)};save()
    finally:
        try:host.close()
        except BaseException as exc:
            report['cleanup_error']={'type':type(exc).__name__,'message':str(exc)};save()
            if failure is None:failure=exc
        finally:signal.signal(signal.SIGCHLD,prior)
    if failure is not None:raise failure
    report['complete']=True;save()
    print(json.dumps({'complete':True,'functions':outputs['candidate']['semantic'],
                      'measured_Board_bytes':report['measured_Board_bytes']}))


if __name__=='__main__':
    main()
