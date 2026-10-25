#!/usr/bin/env python3
"""Single-worker actual shipping-core differential history/layout fixtures.

This is not a playing-strength or shipping-NPS benchmark. The unchanged search
functions run with deterministic history, TT and generous clock state. Their
scores, witnesses, node counts, logical learner/path/TT cells are compared.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
INFO={
 'A':dict(worker='M',pool='K',board='E',root='F',init='q',gen='T(&pos,moves)',make='v(&pos,moves[at],&child)',
          search='h(w,&pos,depth,-30000,30000,ply,6,&best)',half='aI',nodes='a5',hist='zC',cont='an',corr='ah',path='aA',
          tid='id',table='N',flag='X',clear='B',key='aT',data='U'),
 'B':dict(worker='zd',pool='qr',board='za',root='ql',init='k',gen='c(&pos,moves,0,pos.s)',make='h(&pos,moves[at],&child)',
          search='P(w,&pos,depth,-30000,30000,ply,6,&best,0,1)',half='n',nodes='n',hist='h',cont='c',corr='f',path='k',
          tid='i',table='qq',flag='qp',clear='B',key='h',data='v'),
 'C':dict(worker='ai',pool='qr',board='E',root='ql',init='q',gen='T(&pos,moves)',make='v(&pos,moves[at],&child)',
          search='h(w,&pos,depth,-30000,30000,ply,6,&best)',half='aI',nodes='a5',hist='zC',cont='an',corr='ah',path='aA',
          tid='id',table='qq',flag='qp',clear='B',key='aT',data='U'),
 'E':dict(worker='ai',pool='qr',board='E',root='ql',init='q',gen='T(&pos,moves)',make='v(&pos,moves[at],&child)',
          search='h(w,&pos,depth,-30000,30000,ply,6,&best)',half='aI',nodes='a5',hist='zC',cont='an',corr='ah',path='aA',
          tid='id',table='qq',flag='qp',clear='B',key='aT',data='U'),
 'F':dict(worker='X',pool='U',board='I',root='Z',init='o',gen='T(&pos,moves,0,pos.s)',make='h(&pos,moves[at],&child)',
          search='qr(w,&pos,depth,1,ply,6,&best)',half='a',nodes='e',hist='h',cont='i',corr='j',path='f',
          tid='a',table='B',flag='V',clear='qk',key='a',data='b'),
}
INFO['F8']=INFO['F']

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
 sys.modules[name]=module;spec.loader.exec_module(module);return module

def pin(data):return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())

HARNESS=r'''
static unsigned sH_excluded;
#define main history_unused_engine_main
#include "probe-engine.c"
#undef main
#undef J
#undef L
#undef I
#undef l
#undef H
#undef S
#undef aa
static uint64_t sH_digest=1469598103934665603ULL;
static unsigned sH_calls,sH_boundaries,sH_positions;
static void sH_add(uint64_t n){sH_digest=(sH_digest^n)*1099511628211ULL;}
static int sH_sq(int n){return n/8*16+n%8;}
static void sH_set(@WORKER@*w,int at,uint64_t value){
 if(at<qh){qg[at]=value;@COPY_KEY@}else w->@PATH@[@PRIVATE_INDEX@]=value;
}
static void sH_prepare(@WORKER@*w,@BOARD@*p,int length,int ply,int hits){
 memset(w,0,sizeof*w);w->@ID@=1;qh=length;
 for(int i=0;i<qh;i++){qg[i]=p->h^(uint64_t)(i+1);@SEED_PREFIX@}
 for(int i=0;i<128;i++)w->@PATH@[@SEED_PRIVATE_INDEX@]=p->h^(uint64_t)(i+1048576);
 @SEED_INVALID@
 for(int i=0;i<64;i++)for(int j=0;j<64;j++)w->@HIST@[@SEED_I@][@SEED_J@]=(i*31+j*7)%513-256;
 for(int i=0;i<13;i++)for(int j=0;j<13;j++)w->@CONT@[i][j]=(i*3+j*13)%65-32;
 for(int i=0;i<1024;i++)w->@CORR@[i]=(i*17)%513-256;
 for(int n=0;n<hits;n++){int at=qh+ply-3-n*2;if(at>=0)sH_set(w,at,p->h);}
 memset(@TABLE@,0,(1<<18)*sizeof*@TABLE@);@CLEAR@();
 qc=UINT64_MAX;atomic_store(&@FLAG@,0);
}
static void sH_state(@WORKER@*w,int full){
 sH_add(w->@NODES@);
 for(int i=0;i<64;i++)for(int j=0;j<64;j++)sH_add((uint16_t)w->@HIST@[@SEED_I@][@SEED_J@]);
 for(int i=0;i<13;i++)for(int j=0;j<13;j++)sH_add((uint16_t)w->@CONT@[i][j]);
 for(int i=0;i<1024;i++)sH_add((uint16_t)w->@CORR@[i]);
 for(int i=0;i<128;i++)sH_add(w->@PATH@[@SEED_PRIVATE_INDEX@]);
 if(full)for(int i=0;i<(1<<18);i++){sH_add(@TABLE@[i].@KEY@);sH_add(@TABLE@[i].@DATA@);}
 @CHECK_INVALID@
}
static void sH_search(@BOARD@ pos,int length,int ply,int depth,int hits,int full){
 @WORKER@*w=@POOL@;sH_prepare(w,&pos,length,ply,hits);unsigned best=0;
 int result=@SEARCH@;sH_add((unsigned)result);sH_add(best);
 const unsigned char*bytes=(const unsigned char*)&pos;
 for(unsigned i=0;i<sizeof pos;i++)sH_add(bytes[i]);
 sH_state(w,full);sH_calls++;
}
int main(void){
 @TABLE@=calloc(1<<18,sizeof*@TABLE@);if(!@TABLE@)return 2;
 for(int i=0;i<64;i++){
  int square=sH_sq(i);if(square-square/16*8!=i||(square+(square&7))/2!=i)return 10;
  for(int j=0;j<i;j++)if(sH_sq(j)==square)return 11;
 }
 @BOARD@ pos;@INIT@(&pos);
 for(int step=0;step<12;step++){
  sH_search(pos,1,0,3,0,1);sH_positions++;
  unsigned moves[512];int count=@GEN@,found=0;
  for(int i=0;i<count;i++){int at=(i+step*17)%count;@BOARD@ child;if(@MAKE@){pos=child;found=1;break;}}
  if(!found)break;
 }
 @INIT@(&pos);pos.@HALF@=40;
 static const int lengths[]={1,2,17,4096},plies[]={0,1,2,3,5,126,127};
 for(unsigned i=0;i<sizeof lengths/sizeof*lengths;i++)for(unsigned j=0;j<sizeof plies/sizeof*plies;j++){
  for(int hits=0;hits<3;hits++){sH_search(pos,lengths[i],plies[j],0,hits,0);sH_boundaries++;}
 }
 pos.@HALF@=100;sH_search(pos,4096,127,2,2,1);sH_search(pos,1,0,2,0,1);
 @SINGULAR@
 printf("{\"semantic\":{\"digest\":\"%016llx\",\"calls\":%u,\"boundary_calls\":%u,\"positions\":%u,\"excluded_calls\":%u},\"layout\":{\"Worker\":%zu,\"path\":%zu,\"history\":%zu}}\n",
  (unsigned long long)sH_digest,sH_calls,sH_boundaries,sH_positions,sH_excluded,
  sizeof(@WORKER@),sizeof(((@WORKER@*)0)->@PATH@),sizeof(((@WORKER@*)0)->@HIST@));
 free(@TABLE@);return 0;
}
'''

def fixture(source,family,prefix,dense):
 info=INFO[family];private=prefix or family in ('F','F8')
 mapping={k.upper():v for k,v in info.items()}
 mapping.update(ID=info['tid'],COPY_KEY='' if private else 'w->'+info['path']+'[at]=value;',
                PRIVATE_INDEX='at-qh' if private else 'at',
                SEED_PREFIX='' if private else 'w->'+info['path']+'[i]=qg[i];',
                SEED_PRIVATE_INDEX='i' if private else 'qh+i',
                SEED_I='i' if dense else 'sH_sq(i)',SEED_J='j' if dense else 'sH_sq(j)',
                SEED_INVALID='' if dense else 'for(int i=0;i<128;i++)for(int j=0;j<128;j++)if((i|j)&136)w->'+info['hist']+'[i][j]=23130;',
                CHECK_INVALID='' if dense else 'for(int i=0;i<128;i++)for(int j=0;j<128;j++)if(((i|j)&136)&&w->'+info['hist']+'[i][j]!=23130)exit(12);',
                SINGULAR='')
 if family=='B':
  signature=b'J I P(zd*w,const za*p,I a,I d,I f,I n,I yb,N*t,N u,I x){'
  if source.count(signature)!=1:raise ValueError('B actual singular fixture signature differs')
  source=source.replace(signature,signature+b'if(u)++sH_excluded;')
  mapping['SINGULAR']=r'''k(&pos);pos.n=0;zd*w=qr;sH_prepare(w,&pos,17,1,0);
   za child;unsigned move=H(&pos,0,&child);D key=pos.h^b(pos.r+(unsigned)pos.n);
   K(key,move|((D)3<<33)|((D)1<<41));unsigned best=0;
   int score=P(w,&pos,6,-30000,30000,1,6,&best,0,1);
   if(!sH_excluded)return 13;sH_add(score);sH_add(best);sH_state(w,1);sH_calls++;'''
 harness=HARNESS
 for key,value in mapping.items():harness=harness.replace('@'+key+'@',value)
 if '@' in harness:raise ValueError('unexpanded fixture port')
 return source,harness

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--sources',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
 parser.add_argument('--families',default='ABCEF');args=parser.parse_args()
 if not args.out.is_absolute() or args.out.exists() or args.out.resolve().is_relative_to(ROOT):
  raise ValueError('new absolute external output required')
 args.out.mkdir(parents=True)
 report=dict(complete=False,scope='actual shipping search functions, deterministic single worker fixtures; no protocol/strength/NPS claim',
             commands=[],source_inputs={},families={})
 def save():(args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 frozen=args.out/'source-inputs';frozen.mkdir()
 for name,path in (('history_layout.py',HERE/'history_layout.py'),('check_history_layout.py',Path(__file__)),
                   ('host.py',ROOT/'engines/experiments/tcec-scope/build.py')):
  data=path.read_bytes();(frozen/name).write_bytes(data);report['source_inputs'][name]=pin(data)
 module=load('history_stage',frozen/'history_layout.py')
 builder=load('history_host',frozen/'host.py')
 builder.LIMITS.update(aggregate_wall=600,per_command_wall=60,parent_AS=2<<30,parent_CPU=300,child_CPU=60)
 save();previous=signal.signal(signal.SIGCHLD,signal.SIG_DFL);host=builder.Host(args.out,report,save)
 failure=None
 try:
  requested=(args.families.split(',') if ',' in args.families else
             [args.families] if args.families in INFO else list(args.families))
  if not requested or len(requested)!=len(set(requested)) or not set(requested)<=set(INFO):
   raise ValueError('unknown or repeated fixture family')
  families=[name for name in INFO if name in requested]
  for family in families:
   source=(args.sources/(family+'.c')).read_bytes()
   variants=[('baseline',source,False,False,None)]
   if family not in ('F','F8'):
    for label,prefix,dense in (('prefix',True,False),('dense',False,True),('combined',True,True)):
     candidate,proof=module.transform_source(source,family=family,prefix=prefix,dense=dense)
     variants.append((label,candidate,prefix,dense,proof))
   else:
    candidate,proof=module.transform_source(source,family=family,prefix=False,dense=True)
    variants.append(('dense',candidate,False,True,proof))
    if family=='F8':
     candidate,proof=module.transform_source(source,family=family,prefix=False,dense=True,style='fold')
     variants.append(('dense-fold',candidate,False,True,proof))
   records={}
   for label,data,prefix,dense,proof in variants:
    directory=args.out/(family+'-'+label);directory.mkdir()
    actual,body=fixture(data,family,prefix,dense)
    (directory/'main.c').write_bytes(data);(directory/'probe-engine.c').write_bytes(actual)
    (directory/'fixture.c').write_text(body)
    host.run(['cc','-std=c11','-O1','-pthread','-fsanitize=undefined','-fno-sanitize-recover=all',
              'fixture.c','-o','fixture'],cwd=directory,kind=family+'-'+label+'-compile')
    raw=host.run(['./fixture'],cwd=directory,kind=family+'-'+label+'-actual-search')
    observed=json.loads(raw)
    if label!='baseline' and observed['semantic']!=records['baseline']['observed']['semantic']:
     raise ValueError('actual search/learner/TT/key semantics differ: '+family+'/'+label)
    records[label]=dict(source=pin(data),proof=proof,observed=observed)
    report['families'][family]=records;save()
    print(family,label,observed,flush=True)
 except BaseException as error:
  report['error']=dict(type=type(error).__name__,message=str(error));save();raise
 finally:
  try:host.close()
  finally:signal.signal(signal.SIGCHLD,previous)
 report['complete']=True;save()

if __name__=='__main__':main()
