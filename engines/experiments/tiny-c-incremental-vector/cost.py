#!/usr/bin/env python3
"""One candidate compile/package; two strict decodes; never executes an engine."""
import argparse,ast,hashlib,importlib.util,json,lzma,os,signal,subprocess
from pathlib import Path
from transform import transform
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(data):return hashlib.sha256(data).hexdigest()
def normalized(path):return path.read_bytes().replace(b'\r\n',b'\n')
def identity(data,expected,prefix):
    if len(data)!=expected[prefix+'_bytes'] or sha(data)!=expected[prefix+'_sha256']:
        raise ValueError(prefix+' identity mismatch')
def strict_decode(whole,source,template,prefix,command,literal):
    if not whole.startswith(prefix):raise ValueError('prefix mismatch')
    payload=whole[len(prefix):]
    if payload[0]!=2 or int.from_bytes(payload[1:5],'little')!=67108864:raise ValueError('ALONE lc2/lp0/pb0/dict differs')
    decoder=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    script=decoder.decompress(payload)
    if not decoder.eof or decoder.unused_data:raise ValueError('incomplete/trailing stream')
    tree=ast.parse(script);calls=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)]
    popen=[n for n in calls if n.func.attr=='Popen'and isinstance(n.func.value,ast.Name)and n.func.value.id=='subprocess']
    communicate=[n for n in calls if n.func.attr=='communicate'and isinstance(n.func.value,ast.Name)and n.func.value.id=='p']
    if len(popen)!=1 or ast.literal_eval(popen[0].args[0])!=command or len(communicate)!=1:raise ValueError('compiler/source consumer differs')
    node=communicate[0].args[0]
    if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)and node.func.attr=='encode'and not node.args and not node.keywords:
        recovered=ast.literal_eval(node.func.value).encode()
    else:recovered=ast.literal_eval(node)
    expression,_=literal(source)
    if recovered!=source or script!=template.replace(b'__ROVE_SOURCE_LITERAL__',expression.encode()):raise ValueError('restored source/bootstrap differs')
    return {'source_sha256':sha(recovered),'bootstrap_bytes':len(script),'bootstrap_sha256':sha(script),'eof':True,'unused_bytes':0,'compiler_argv_equal':True}
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path);parser.add_argument('--control-dir',required=True,type=Path);args=parser.parse_args()
    out=args.out.resolve();control=args.control_dir.resolve()
    if not args.out.is_absolute()or out.exists()or out==ROOT or ROOT in out.parents:parser.error('new absolute output outside Git required')
    out.mkdir();report={'complete':False,'candidate_compile_count':0,'candidate_package_count':0,'strict_decode_count':0,'control_compile_count':0,'engine_count':0,'fixed_variants':1,'active_compiler':False}
    def save():(out/'cost.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        cfg=json.loads((HERE/'config.json').read_text());entry=ROOT/'engines/compact/tiny-entry-c';recipe=json.loads((entry/'recipe.json').read_text())
        if recipe['profile']!=cfg['profile']or recipe['compiler']!=cfg['compiler']or recipe['compression']!=cfg['compression']:raise ValueError('current fixed C recipe differs')
        source=(control/'main.c').read_bytes();native=(control/'native/x').read_bytes();whole=(control/'x').read_bytes();meta=json.loads((control/'build.json').read_text())
        for data,kind in ((source,'source'),(native,'native'),(whole,'whole')):identity(data,cfg['baseline'],kind)
        if meta['actual']['source_sha256']!=sha(source)or meta['actual']['native_sha256']!=sha(native)or meta['actual']['whole_sha256']!=sha(whole):raise ValueError('actual control metadata mismatch')
        template=normalized(entry/'bootstrap.py.in');prefix=normalized(entry/'launcher.sh');helper=ROOT/'engines/compact/tiny-a/pack_stream.py'
        if sha(template)!=cfg['template_sha256']or len(prefix)!=77 or sha(prefix)!=cfg['prefix_sha256']or sha(normalized(helper))!=cfg['literal_helper_sha256']:raise ValueError('closing input changed')
        snapshots={p:p.read_bytes()for p in [entry/'recipe.json',entry/'bootstrap.py.in',entry/'launcher.sh',helper,*sorted(HERE.glob('*.py')),HERE/'config.json']}
        inputs=out/'inputs';inputs.mkdir()
        for index,(path,data)in enumerate(snapshots.items()):(inputs/(str(index)+'-'+path.name)).write_bytes(data)
        report['source_inputs']=[{'path':str(p),'bytes':len(d),'sha256':sha(d)}for p,d in snapshots.items()]
        spec=importlib.util.spec_from_file_location('incremental_cost_literal',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);literal=module.source_literal
        report['baseline_decode']=strict_decode(whole,source,template,prefix,cfg['compiler'],literal);report['strict_decode_count']+=1
        if report['baseline_decode']['bootstrap_sha256']!=cfg['baseline']['bootstrap_sha256']:raise ValueError('baseline bootstrap identity differs')
        candidate=transform(source);identity(candidate,cfg['candidate'],'source');(out/'main.c').write_bytes(candidate)
        report['compiler_version']=subprocess.check_output(['cc','--version'],text=True).splitlines()[0]
        if report['compiler_version']!=meta['tools']['cc']:raise ValueError('compiler identity differs from actual control')
        directory=out/'native';directory.mkdir();report['candidate_compile_count']=1;report['active_compiler']=True;save()
        process=subprocess.Popen(cfg['compiler'],cwd=directory,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:stdout,stderr=process.communicate(candidate,timeout=90)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);stdout,stderr=process.communicate();raise
        finally:report['active_compiler']=process.poll()is None
        (out/'compiler.stdout').write_bytes(stdout);(out/'compiler.stderr').write_bytes(stderr)
        if process.returncode:raise ValueError('candidate compile failed: '+str(process.returncode))
        image=(directory/'x').read_bytes()
        if image[:4]!=b'\x7fELF':raise ValueError('candidate is not ELF')
        expression,_=literal(candidate);script=template.replace(b'__ROVE_SOURCE_LITERAL__',expression.encode())
        package=prefix+lzma.compress(script,format=lzma.FORMAT_ALONE,check=lzma.CHECK_NONE,filters=[{'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0,'mf':lzma.MF_BT4,'dict_size':67108864,'nice_len':64}]);report['candidate_package_count']=1
        (out/'x').write_bytes(package);(out/'bootstrap.py').write_bytes(script)
        report['candidate_decode']=strict_decode(package,candidate,template,prefix,cfg['compiler'],literal);report['strict_decode_count']+=1
        for p,data in snapshots.items():
            if p.read_bytes()!=data:raise ValueError('upstream/source input drift')
        report.update(complete=True,baseline=cfg['baseline'],candidate={'source_bytes':len(candidate),'source_sha256':sha(candidate),'native_bytes':len(image),'native_sha256':sha(image),'whole_bytes':len(package),'whole_sha256':sha(package),'bootstrap_bytes':len(script),'bootstrap_sha256':sha(script)},delta={'source_bytes':len(candidate)-len(source),'native_bytes':len(image)-len(native),'whole_bytes':len(package)-len(whole)},result='gain'if len(package)<len(whole)else'loss'if len(package)>len(whole)else'tie',upstream_inputs_unchanged=True,semantic_or_layout_validation=False,old_board_state_proof_inherited=False)
    except BaseException as error:report['error']=repr(error);raise
    finally:save()
    print(json.dumps(report,indent=2))

FOCUSED_C='#define main omitted_engine_main\n#ifdef CHECK_DEV\n#include "dev.c"\ntypedef Board BT;\n#define HALF half\n#define PUT put\n#define NORM_EP ep\n#define STATE state\n#define RAW tiny_raw\n#define SEARCH search\n#define CLEAR clear\n#define NODES nodes\n#define KEYS keys\n#define LENGTH length\n#else\n#include "candidate-check.c"\ntypedef za BT;\n#define HALF zL\n#define PUT K\n#define NORM_EP C\n#define STATE R\n#define RAW U\n#define SEARCH P\n#define CLEAR y\n#define NODES z4\n#define KEYS zQ\n#define LENGTH zV\n#endif\n#undef main\n#include <stddef.h>\n#include <ctype.h>\n#include <inttypes.h>\nstatic unsigned scans,vector_calls,ordering_checks,scratch_checks,legal_total;\nstatic unsigned captures,eps,castles,promotions[2],promotion_captures[2];\nstatic void need(int good,const char *why){if(!good){fprintf(stderr,"FAIL %s\\n",why);exit(1);}}\nstatic int low(int a,int b){return a<b?a:b;}\nstatic int math_value(int v,int q){\n const int m[7]={0,100,320,330,500,900,0},a[7]={0,7,0,0,2,0,0},c[7]={0,2,9,5,0,2,-3};\n int k=abs(v),rank=q/16,file=q%16,center=2*(low(rank,7-rank)+low(file,7-file))-7;\n int n=m[k]+(v>0?rank:7-rank)*a[k]+center*c[k];return v>0?n:-n;\n}\nstatic uint64_t ref_mix(uint64_t n){n+=UINT64_C(0x9e3779b97f4a7c15);n=(n^(n>>30))*UINT64_C(0xbf58476d1ce4e5b9);n=(n^(n>>27))*UINT64_C(0x94d049bb133111eb);return n^(n>>31);}\nstatic int scan(const BT *p){\n static const int material[7]={0,100,320,330,500,900,0},weights[16]={100,320,330,500,900,0,1,0,-100,-320,-330,-500,-900,0,-1,0};\n int lanes[16]={0},pieces[2]={0},score=0,dot=0;\n uint64_t h=ref_mix(2048+p->c)^(p->s<0?ref_mix(2064):0)^(p->e<0?0:ref_mix(2065+(p->e&7)));\n for(int q=0;q<128;q++){\n  int v=p->b[q];need(!(q&0x88)||v==0,"mailbox padding");if((q&0x88)||!v)continue;\n  int k=abs(v),o=8*(v<0),term=math_value(v,q);need(k<=6,"piece domain");\n  pieces[v<0]++;lanes[o+k-1]++;lanes[o+6]+=(v>0?term:-term)-material[k];score+=term;\n  h^=ref_mix((uint64_t)(q+(v+6)*128));\n }\n need(pieces[0]<=16&&pieces[1]<=16,"population bound");need(p->h==h,"full independent hash rebuild");\n for(int i=0;i<16;i++){\n  need(abs(lanes[i])<=1008,"feature bound");dot+=lanes[i]*weights[i];\n#ifndef CHECK_DEV\n  need(p->x[i]==lanes[i],"full feature rebuild");\n#endif\n }\n need(lanes[7]==0&&lanes[15]==0&&dot==score,"independent dot/scalar equality");\n#ifdef CHECK_DEV\n need(p->v==score,"DEV independent incremental HCE");\n#endif\n scans++;return score;\n}\n#ifndef CHECK_DEV\n/* Only U\'s definition name is changed in the included fixture copy. Its body\n * is exact. P\'s existing U calls reach this independent checker then the body. */\nstatic int U(const za *p){int expected=scan(p),actual=shipping_U(p);need(actual==expected,"actual SIMD/scalar");vector_calls++;return actual;}\n#endif\nstatic void check(const BT *p){int expected=scan(p);need(RAW(p)==expected,"actual raw evaluator");}\nstatic void empty(BT *p){memset(p,0,sizeof *p);p->s=1;p->e=-1;p->h=STATE(p);}\nstatic void load(BT *p,const char *text){\n#ifdef CHECK_DEV\n need(fen(p,text),"reference FEN ingress");\n#else\n char cells[96],side,rights[8],enpassant[3];int half,full;static const char letters[]=" PNBRQK",castle_flags[]="KQkq";\n need(sscanf(text,"%95s %c %7s %2s %d %d",cells,&side,rights,enpassant,&half,&full)==6,"fixture FEN fields");\n BT t={0};t.s=side==\'w\'?1:-1;t.e=-1;t.HALF=half;\n int rank=7,file=0;for(const char *c=cells;*c;c++){\n  if(*c==\'/\'){rank--;file=0;}else if(isdigit((unsigned char)*c))file+=*c-\'0\';else{\n   const char *k=strchr(letters,toupper((unsigned char)*c));need(k!=0,"fixture piece");\n   PUT(&t,rank*16+file++,(int)(k-letters)*(isupper((unsigned char)*c)?1:-1));\n  }\n }\n for(const char *c=rights;*c&&*c!=\'-\';c++){const char *k=strchr(castle_flags,*c);need(k!=0,"fixture right");t.c|=1<<(k-castle_flags);}\n if(enpassant[0]!=\'-\')t.e=(enpassant[1]-\'1\')*16+enpassant[0]-\'a\';\n NORM_EP(&t);t.h^=STATE(&t);t.r=t.h;*p=t;\n#endif\n check(p);\n}\nstatic void children(const BT *p,int id){\n BT saved;memcpy(&saved,p,sizeof saved);Move list[MOVES];int n=gen(p,list),legal=0;uint64_t digest=0;\n check(p);\n for(int i=0;i<n;i++){\n  BT child;if(!make(p,list[i],&child))continue;check(&child);legal++;legal_total++;\n  need(memcmp(&saved,p,sizeof saved)==0,"const parent changed");\n  uint64_t context=child.HALF?((p->r<<1)|(p->r>>63))^child.h:child.h;\n  need(child.r==context&&child.s==-p->s,"reversible context and side");\n  int from=FROM(list[i]),to=TO(list[i]),color=p->s<0,cap=p->b[to]!=0;\n  if(cap)captures|=1u<<color;\n  if(abs(p->b[from])==1&&to==p->e&&!p->b[to])eps|=1u<<color;\n  if(abs(p->b[from])==6&&abs(to-from)==2)castles|=1u<<(color*2+(to<from));\n  if(PROMO(list[i])){promotions[color]|=1u<<PROMO(list[i]);if(cap)promotion_captures[color]|=1u<<PROMO(list[i]);}\n  digest=ref_mix(digest^child.h^child.r^((uint64_t)list[i]<<32)^(uint32_t)math_value(child.b[TO(list[i])],TO(list[i]))^(unsigned)child.HALF);\n }\n printf("{\\"kind\\":\\"case\\",\\"id\\":%d,\\"legal\\":%d,\\"hash\\":\\"%016" PRIx64 "\\",\\"digest\\":\\"%016" PRIx64 "\\",\\"ep\\":%d,\\"half\\":%d}\\n",id,legal,p->h,digest,p->e,p->HALF);\n}\nstatic void scratch(const char *fen_text,int requested,int expected){\n BT p;load(&p,fen_text);p.e=requested;BT original=p,poisoned=p;\n#ifndef CHECK_DEV\n for(int i=0;i<16;i++)poisoned.x[i]=(int16_t)(i&1?-30000:30000);\n int16_t before[16];memcpy(before,poisoned.x,sizeof before);\n#else\n poisoned.v=123456789;\n#endif\n NORM_EP(&original);NORM_EP(&poisoned);\n need(original.e==expected&&poisoned.e==expected,"attack-only EP result depends on cache");\n need(memcmp(original.b,poisoned.b,sizeof original.b)==0,"EP mutated mailbox");\n#ifndef CHECK_DEV\n need(memcmp(before,poisoned.x,sizeof before)==0,"EP touched feature cache");\n#else\n need(poisoned.v==123456789,"EP touched DEV cache");\n#endif\n scratch_checks++;\n}\nstatic void search_check(int color){\n BT p;if(!color)start(&p);else load(&p,"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1");check(&p);\n CLEAR();memset(workers,0,sizeof workers);workers[0].LENGTH=1;workers[0].KEYS[0]=p.h;deadline=UINT64_MAX;atomic_store(&stopped,0);\n Move best=0;int score=SEARCH(workers,&p,2,-MATE,MATE,0,0,&best);need(!atomic_load(&stopped)&&workers[0].NODES>1,"positive actual search");\n Move list[MOVES];int n=gen(&p,list),found=0;for(int i=0;i<n;i++)if(list[i]==best){BT child;found=make(&p,best,&child);if(found)check(&child);}\n need(found,"search returned illegal move");\n printf("{\\"kind\\":\\"search\\",\\"color\\":%d,\\"score\\":%d,\\"best\\":%u,\\"nodes\\":%llu}\\n",color,score,best,(unsigned long long)workers[0].NODES);\n}\nint main(void){\n#ifdef CHECK_DEV\n need(sizeof(BT)==176&&offsetof(BT,h)==160,"actual DEV reference layout");\n#else\n typedef struct{int8_t b[128];int s,c,e,k[2],zL;uint64_t h,r;}OldBoard;\n need(sizeof(OldBoard)==168&&offsetof(OldBoard,s)==128&&offsetof(OldBoard,h)==152&&offsetof(OldBoard,r)==160,"actual old shipping declaration layout");\n need(sizeof(BT)==200&&offsetof(BT,x)==128&&offsetof(BT,s)==160&&offsetof(BT,h)==184&&offsetof(BT,r)==192,"actual new Board layout");\n printf("{\\"kind\\":\\"layout\\",\\"old_size\\":%zu,\\"new_size\\":%zu,\\"x_offset\\":%zu,\\"side_offset\\":%zu,\\"hash_offset\\":%zu,\\"context_offset\\":%zu}\\n",sizeof(OldBoard),sizeof(BT),offsetof(BT,x),offsetof(BT,s),offsetof(BT,h),offsetof(BT,r));\n#endif\n for(int v=-6;v<=6;v++)for(int q=0;q<128;q++)if(!(q&0x88)){\n  need(value(v,q)==math_value(v,q),"independent piece value");BT p;empty(&p);PUT(&p,q,v);check(&p);\n }\n for(int k=1;k<=6;k++){\n  BT p;empty(&p);for(int f=0;f<8;f++)for(int rank=0;rank<2;rank++){\n   PUT(&p,rank*16+f,k);check(&p);PUT(&p,(rank+6)*16+f,-k);check(&p);\n  }\n }\n for(int v=-6;v<=6;v++)for(int victim=-6;victim<=6;victim++)for(int q=0;q<128;q++)if(!(q&0x88)){\n  BT p;empty(&p);int to=119-q;PUT(&p,q,v);PUT(&p,to,victim);\n  int actual=500000+abs(value(p.b[to],to))*16-abs(value(p.b[q],q));\n  int expected=500000+abs(math_value(victim,to))*16-abs(math_value(v,q));need(actual==expected,"capture ordering");ordering_checks++;\n }\n BT start_board;start(&start_board);children(&start_board,0);\n#ifndef CHECK_DEV\n int original=shipping_U(&start_board);for(int i=0;i<16;i++){BT p=start_board;p.x[i]++;need(shipping_U(&p)==original+qm[i],"all actual SIMD lanes/halves");}\n#endif\n const char *cases[]={\n  "4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1","4k3/8/8/3p4/4P3/8/8/4K3 b - - 0 1",\n  "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1","4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1",\n  "k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1","4k3/8/8/8/3Pp3/8/8/K3R3 b - d3 0 1",\n  "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1","r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1",\n  "1r5k/P7/8/8/8/8/8/7K w - - 0 1","7k/8/8/8/8/8/p7/1R5K b - - 0 1",\n  "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 99 1"};\n for(unsigned i=0;i<sizeof cases/sizeof *cases;i++){BT p;load(&p,cases[i]);children(&p,(int)i+1);}\n scratch(cases[2],83,83);scratch(cases[3],35,35);scratch(cases[4],83,-1);scratch(cases[5],35,-1);\n need(captures==3&&eps==3&&castles==15,"both-color capture/EP/castle coverage");\n need(promotions[0]==60&&promotions[1]==60&&promotion_captures[0]==60&&promotion_captures[1]==60,"all four promotions both colors");\n table=calloc((size_t)1<<18,sizeof *table);need(table!=0,"fixture TT allocation");search_check(0);search_check(1);free(table);\n printf("{\\"kind\\":\\"summary\\",\\"scans\\":%u,\\"actual_vector_checks\\":%u,\\"ordering_checks\\":%u,\\"scratch_checks\\":%u,\\"legal_children\\":%u,\\"pass\\":true}\\n",scans,vector_calls,ordering_checks,scratch_checks,legal_total);\n return 0;\n}\n'

def focused_main():
    import re,sys
    parser=argparse.ArgumentParser(description='Focused actual candidate Board/SIMD and fixed DEV reference checks')
    parser.add_argument('--out',required=True,type=Path);parser.add_argument('--control-dir',required=True,type=Path);parser.add_argument('--candidate-dir',required=True,type=Path);args=parser.parse_args()
    out=args.out.resolve();control=args.control_dir.resolve();first=args.candidate_dir.resolve()
    if not args.out.is_absolute()or out.exists()or out==ROOT or ROOT in out.parents:parser.error('new absolute output outside Git required')
    out.mkdir();report={'complete':False,'fixture_compiles':0,'fixture_runs':0,'full_engine_sessions':0,'old_layout_proof_inherited':False,'codec_runs':0,'active_processes':0}
    def save():(out/'focused.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(command,*,cwd=out,timeout=90):
        p=subprocess.Popen(command,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);report['active_processes']=1
        try:stdout,stderr=p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);stdout,stderr=p.communicate();raise
        finally:report['active_processes']=int(p.poll()is None)
        return p.returncode,stdout,stderr
    try:
        cfg=json.loads((HERE/'config.json').read_text());entry=ROOT/'engines/compact/tiny-entry-c';recipe=json.loads((entry/'recipe.json').read_text())
        control_source=(control/'main.c').read_bytes();candidate=(first/'main.c').read_bytes();dev=(control/'dev/main.c').read_bytes()
        identity(control_source,cfg['baseline'],'source');identity(candidate,cfg['candidate'],'source')
        if transform(control_source)!=candidate or sha(dev)!=recipe['expected']['dev_source_sha256']:raise ValueError('candidate/DEV source pin differs')
        if sha((first/'native/x').read_bytes())!='db608da6eecd01fef7d845bb3bd8b52fe792ed527f4d2501c7c05900aad64b9a':raise ValueError('actual first-cost candidate native differs')
        identity((control/'native/x').read_bytes(),cfg['baseline'],'native')
        snapshots={path:path.read_bytes()for path in [entry/'recipe.json',entry/'engine.c',HERE/'config.json',HERE/'transform.py',HERE/'cost.py']}
        (out/'candidate.c').write_bytes(candidate);(out/'control.c').write_bytes(control_source);(out/'dev.c').write_bytes(dev)
        prefix=b'static int U(const za*p){'
        if candidate.count(prefix)!=1:raise ValueError('actual U definition guard')
        # Definition-name-only instrumentation retains the exact U body; P's
        # original calls reach a checked wrapper, then the actual SIMD body.
        instrumented=candidate.replace(prefix,b'static int U(const za*p);static int shipping_U(const za*p){',1)
        (out/'candidate-check.c').write_bytes(instrumented);(out/'fixture.c').write_text(FOCUSED_C)
        report['sources']={name:{'bytes':len(data),'sha256':sha(data)}for name,data in [('candidate.c',candidate),('control.c',control_source),('dev.c',dev),('candidate-check.c',instrumented),('fixture.c',FOCUSED_C.encode())]}
        report['compiler_version']=subprocess.check_output(['cc','--version'],text=True).splitlines()[0]
        report['native_observations']={}
        for label,binary in [('control',control/'native/x'),('candidate',first/'native/x')]:
            rc,asm,err=run(['objdump','-d','--no-show-raw-insn','--disassemble=P',str(binary)])
            (out/(label+'-P.asm')).write_bytes(asm)
            if rc:raise ValueError('actual native disassembly failed')
            text=asm.decode();body=text.split('<P>:',1)[1];prologue=body.split('call',1)[0]
            allocation=sum(int(x,16)for x in re.findall(r'sub\s+\$0x([0-9a-f]+),%rsp',prologue))
            if not allocation:raise ValueError('unrecognized actual P frame')
            report['native_observations'][label]={'native_sha256':sha(binary.read_bytes()),'P_static_stack_allocation':allocation,'prologue_push_count':len(re.findall(r'\bpush\b',prologue)),'alignment_masks':re.findall(r'and\s+\$([^,]+),%rsp',prologue)}
            if label=='candidate':
                if not all(op in text for op in ('vpmaddwd','vextracti128','vpaddd'))or not re.search(r'vmovdqu\s+0x80\([^)]*\),%ymm',text):raise ValueError('actual P does not consume Board x through both SIMD halves')
        report['P_stack_allocation_delta']=report['native_observations']['candidate']['P_static_stack_allocation']-report['native_observations']['control']['P_static_stack_allocation']
        base=['cc','-std=c11','-O1','-g','-pthread','-mavx2','-DWORKERS=2','-DTT_BITS=18','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-no-pie','fixture.c']
        results={}
        for label,extra in [('candidate',[]),('dev',['-DCHECK_DEV=1'])]:
            command=base+extra+['-o',label+'-fixture'];report['fixture_compiles']+=1;rc,stdout,stderr=run(command)
            (out/(label+'-compile.stdout')).write_bytes(stdout);(out/(label+'-compile.stderr')).write_bytes(stderr)
            if rc:raise ValueError(label+' focused fixture compile failed')
            report['fixture_runs']+=1;rc,stdout,stderr=run([str(out/(label+'-fixture'))],timeout=30)
            (out/(label+'.stdout')).write_bytes(stdout);(out/(label+'.stderr')).write_bytes(stderr)
            if rc:raise ValueError(label+' focused fixture execution failed')
            lines=[json.loads(line)for line in stdout.decode().splitlines()];results[label]=lines
            if not lines[-1].get('pass'):raise ValueError(label+' focused result absent')
        for kind in ('case','search'):
            a=[row for row in results['candidate']if row['kind']==kind];b=[row for row in results['dev']if row['kind']==kind]
            if a!=b:raise ValueError('candidate/fixed DEV '+kind+' differs')
        for path,data in snapshots.items():
            if path.read_bytes()!=data:raise ValueError('source input drift')
        report.update(complete=True,results=results,candidate_DEV_cases_and_search_equal=True,upstream_inputs_unchanged=True,actual_shipping_U_body_retained=True,cache_validation_on_every_candidate_search_U=True,source_static_review_required_for_scratch_non_escape=True)
    except BaseException as error:report['error']=repr(error);raise
    finally:save()
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    import sys
    if '--check' in sys.argv:
        sys.argv.remove('--check');focused_main()
    else:main()
