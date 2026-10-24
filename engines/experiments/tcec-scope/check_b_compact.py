#!/usr/bin/env python3
"""Focused full-B differential checks; all products stay outside the repo.

The harness calls the original and selected real generator/maker/SEE/search,
not a rewritten chess implementation.  It also checks the finite coordinate
and promotion expression domains independently and compares macro expansion
before the semantic dead-copy/arithmetic edits.  Protocol qualification is a
separate existing-verifier run against the complete selected artifact.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import signal
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


HARNESS = r'''
#define main fixture_unused_engine_main
#include "main.c"
#undef main
_Static_assert(sizeof(D)==8&&sizeof(unsigned long)==8,"admitted Linux u64 literal type");
static D fixture_digest=1469598103934665603ULL;
static unsigned fixture_positions,fixture_searches,fixture_see;
static void fixture_add(D v){fixture_digest=(fixture_digest^v)*1099511628211ULL;}
static void fixture_board(const za*p){
 for(int i=0;i<128;i++)fixture_add((unsigned char)p->b[i]);
 for(int i=0;i<2;i++)for(int j=0;j<7;j++)fixture_add(p->bb[i][j]);
 fixture_add(p->s);fixture_add(p->c);fixture_add(p->e);fixture_add(p->k[0]);fixture_add(p->k[1]);
 fixture_add(p->zL);fixture_add(p->v);fixture_add(p->h);fixture_add(p->r);
}
static void fixture_search(const za*p,int repeat){
 zd*w=qr;memset(w,0,sizeof*w);w->id=1;
 for(int i=0;i<128;i++)for(int j=0;j<128;j++)w->zM[i][j]=(i*7+j*11)%1024-512;
 for(int i=0;i<13;i++)for(int j=0;j<13;j++)w->zw[i][j]=(i*3+j*13)%1024-512;
 for(int i=0;i<1024;i++)w->zx[i]=(i*17)%1024-512;
 memset(qq,0,(1<<18)*sizeof*qq);B();qh=repeat?5:1;
 for(int i=0;i<qh;i++)w->zQ[i]=p->h;
 qc=UINT64_MAX;atomic_store(&qp,0);N best=0;
 int score=P(w,p,3,-30000,30000,0,6,&best,0,1);
 fixture_add(score);fixture_add(best);fixture_add(w->z4);
 for(int i=0;i<128;i++)for(int j=0;j<128;j++)fixture_add(w->zM[i][j]);
 for(int i=0;i<13;i++)for(int j=0;j<13;j++)fixture_add(w->zw[i][j]);
 for(int i=0;i<1024;i++)fixture_add(w->zx[i]);fixture_searches++;
}
static void fixture_position(const za*p,int search){
 N moves[512];int count=c(p,moves,0,p->s);fixture_add(count);fixture_board(p);
 qc=UINT64_MAX;atomic_store(&qp,0);
 for(int i=0;i<count;i++){
  za child;int valid=h(p,moves[i],&child);fixture_add(moves[i]);fixture_add(valid);
  if(valid){fixture_board(&child);if(moves[i]&8){fixture_add(FIXTURE_SEE(p,moves[i]));fixture_see++;}}
 }
 if(search){fixture_search(p,0);fixture_search(p,1);}fixture_positions++;
}
int main(void){
 qq=calloc(1<<18,sizeof*qq);if(!qq)return 2;B();
 for(int rank=0;rank<8;rank++)for(int file=0;file<8;file++){
  int square=rank*16+file,index=rank*8+file;
  if(o(square)!=(1ULL<<index))return 10;
  if(index+(index&56)!=square)return 11;
  if((square+(square&7))/2!=index)return 12;
  for(int from=0;from<128;from++)if(!(from&136))for(int d=0;d<4;d++){
   N moves[512];int count=0;g(moves,&count,from,square,d);
   int promotion=d>1&&(rank==0||rank==7);
   if(count!=(promotion?4:1))return 13;
   for(int i=0;i<count;i++){
    if(FROM(moves[i])!=from||TO(moves[i])!=square||PROMO(moves[i])!=(promotion?i+2:0))return 14;
    fixture_add(moves[i]);
   }
  }
 }
 for(int promote=0;promote<6;promote++)if(promote!=1){
  int original=promote?qi[promote]-100:0;
  if(original!=qi[promote]-100*!!promote)return 15;
 }
 za position;k(&position);
 for(int step=0;step<20;step++){
  fixture_position(&position,step%5==0);
  N moves[512];int count=c(&position,moves,0,position.s),found=0;
  for(int i=0;i<count;i++){
   int at=(i+step*17)%count;za child;
   if(h(&position,moves[at],&child)){position=child;found=1;break;}
  }
  if(!found)break;
 }
 for(int side=-1;side<=1;side+=2){
  za position={0};position.s=side;position.e=-1;
  M(&position,4,6);M(&position,116,-6);
  M(&position,side>0?96:16,side);M(&position,side>0?113:1,-side*4);
  position.h^=S(&position);position.r=position.h;fixture_position(&position,1);
 }
 printf("%016llx positions=%u searches=%u SEE=%u\n",(unsigned long long)fixture_digest,fixture_positions,fixture_searches,fixture_see);
 free(qq);return 0;
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--forms', default='score,see,constants,promotion,bitindex,hash,return,static')
    args = parser.parse_args()
    def require(value, message):
        if not value:
            raise ValueError(message)
    require(args.out.is_absolute() and not args.out.exists()
            and not args.out.resolve().is_relative_to(HERE.parents[2].resolve()),
            'new absolute output outside the repo required')
    args.out.mkdir(parents=True)
    compact = load('focused_B_compact', HERE / 'b_compact.py')
    builder = load('focused_B_host', HERE / 'build.py')
    builder.LIMITS.update(aggregate_wall=90, per_command_wall=30, parent_CPU=90, child_CPU=30)
    package = load('focused_B_package', args.build / 'inputs/engines/scripts/source_package.py')
    recipe_input=json.loads((args.build/'build.json').read_text())
    minify_path=HERE.parents[2]/'engines/scripts/minify.py'
    require(compact.pin(minify_path.read_bytes().replace(b'\r\n',b'\n'))
            ==recipe_input['control_source_closure']['engines/scripts/minify.py'],
            'tracked minifier differs from integrated control source closure')
    minify = load('focused_B_minify', minify_path)
    source = args.source.read_bytes();forms = tuple(filter(None, args.forms.split(',')))
    candidate, proof = compact.transform_source(source, forms=forms)
    repeat, repeat_proof = compact.transform_source(source, forms=forms)
    require(candidate == repeat and proof == repeat_proof, 'pure B compact reproduction differs')
    frozen = args.out / 'source-inputs';frozen.mkdir()
    source_inputs = {}
    for name,path in (('b_compact.py',HERE/'b_compact.py'),
                      ('check_b_compact.py',HERE/'check_b_compact.py'),
                      ('host.py',HERE/'build.py'),
                      ('source_package.py',args.build/'inputs/engines/scripts/source_package.py'),
                      ('minify.py',minify_path),
                      ('control-build.json',args.build/'build.json')):
        data=path.read_bytes();(frozen/name).write_bytes(data)
        source_inputs[name]={'origin':str(path),**compact.pin(data)}
    report = {'complete': False, 'commands': [], 'input': compact.pin(source),
              'input_path': str(args.source), 'source_inputs': source_inputs,
              'producer': compact.pin((HERE / 'b_compact.py').read_bytes()), 'forms': forms,
              'proof': proof, 'candidate': compact.pin(candidate)}
    def save():
        (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    save();previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    host = builder.Host(args.out, report, save)
    failure = None
    try:
        recipe = json.loads((args.build / 'build.json').read_text())
        require(recipe.get('complete') is True and recipe.get('family')=='B'
                and recipe.get('compiler')==['cc','-std=c11','-Os','-pthread','-x','c','-','-o','x'],
                'completed minimal TCEC full-B control recipe required')
        control_source=(args.build/recipe['actual']['source']).read_bytes()
        expected=recipe['expected_contract']
        require(compact.pin(control_source)=={'bytes':expected['source_bytes'],'sha256':expected['source_sha256']},
                'integrated full-B control source identity differs')
        control_whole=(args.build/recipe['actual']['program']).read_bytes()
        require(compact.pin(control_whole)=={'bytes':expected['whole_bytes'],'sha256':expected['whole_sha256']}
                and package.package_tcec(control_source,recipe['compression'],compiler=recipe['compiler'],mode='pipe')==control_whole,
                'integrated full-B control recipe/package reproduction differs')
        report['control_build_identity']={'source':compact.pin(control_source),'whole':compact.pin(control_whole),
            'recipe_reproduction':True,'post_line_input_admission':len(source)==9283}
        for label,data in (('baseline',source),('candidate',candidate)):
            directory=args.out/label;directory.mkdir();(directory/'main.c').write_bytes(data)
            host.run(recipe['compiler'],cwd=directory,kind=label+'-native',data=data)
            report[label+'_native']=compact.pin((directory/'x').read_bytes())
            whole=package.package_tcec(data,recipe['compression'],compiler=recipe['compiler'],mode='pipe')
            (directory/'whole').write_bytes(whole);report[label+'_whole']=compact.pin(whole)
        macro_forms=tuple(f for f in forms if f in ('return','static','atomic','mutex'))
        macro_source,_=compact.transform_source(source,forms=macro_forms)
        cpp=['cc','-std=c11','-Os','-pthread','-E','-P','-x','c','-']
        old=host.run(cpp,cwd=args.out,kind='old-macro-CPP',data=source)
        new=host.run(cpp,cwd=args.out,kind='new-macro-CPP',data=macro_source)
        require(minify.compact_source(old,'c')==minify.compact_source(new,'c'), 'macro preprocessing tokens differ')
        report['macro_CPP_tokens_equal']=True
        outputs=[]
        for label,see in (('baseline',False),('candidate','see' in forms)):
            directory=args.out/label
            bridge='#define FIXTURE_SEE(p,m) Q('+('' if see else 'qr,')+'p,m)\n'
            harness=HARNESS.replace('#define main fixture_unused_engine_main',bridge+'#define main fixture_unused_engine_main')
            (directory/'fixture.c').write_text(harness)
            host.run(['cc','-std=c11','-Os','-pthread','fixture.c','-o','fixture'],cwd=directory,kind=label+'-fixture-compile')
            outputs.append(host.run(['./fixture'],cwd=directory,kind=label+'-actual-functions'))
        require(outputs[0]==outputs[1], 'actual B function results/learners differ')
        report['actual_functions_equal']=True;report['actual_functions_stdout']=outputs[0].decode('ascii')
        save()
    except BaseException as error:
        failure=error
        report['error']={'type':type(error).__name__,'message':str(error)};save()
    finally:
        try:
            host.close()
        except BaseException as error:
            report['cleanup_error']={'type':type(error).__name__,'message':str(error)};save()
            if failure is None:failure=error
        finally:signal.signal(signal.SIGCHLD, previous)
    if failure is not None:raise failure
    report['complete']=True;save()
    print(json.dumps({'complete':report['complete'],'candidate':report['candidate'],
        'whole':report['candidate_whole'],'functions':report.get('actual_functions_stdout')}))


if __name__ == '__main__':
    main()
