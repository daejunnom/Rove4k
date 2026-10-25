#!/usr/bin/env python3
"""Bounded shipping-core fixed-work comparison for the admitted F2/B inputs.

Only the iterative driver's depth limit and completed-iteration observer change.
Recursive search/make/eval/TT/learning bodies remain byte-identical. This is a
fixture, not the unmodified shipping image, SMP strength or an Elo test.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ADMITTED = {
    'F': (6901, '46bd9a21026afb7e289acbec67078235563534685f9413fbb989664f7728ea22'),
    'B': (8770, '23d9de0788b0058c0a11744290bdf2d39582b16d6af48501d9021bbb57f54bfe'),
}
POSITIONS = {
    'start': '',
    'italian': 'e2e4 e7e5 g1f3 b8c6 f1c4 g8f6 d2d3 f8c5 c2c3 d7d6 b1d2 e8g8 e1g1 a7a6',
    'queens-gambit': 'd2d4 d7d5 c2c4 e7e6 b1c3 g8f6 c1g5 f8e7 e2e3 e8g8 g1f3 h7h6 g5h4 b7b6',
    'sicilian': 'e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3 a7a6 c1g5 e7e6 f2f4',
}
PREFIX = b'''struct bench_row {int depth,score;unsigned move;uint64_t nodes;};
static int bench_limit,bench_count;
static struct bench_row bench_rows[7];
static void bench_record(int depth,int score,unsigned move,uint64_t nodes){
bench_rows[depth]=(struct bench_row){depth,score,move,nodes};++bench_count;}
'''


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def function(data, signature):
    start = data.find(signature)
    require(start >= 0 and data.count(signature) == 1, 'exact function signature differs')
    opening = data.index(b'{', start)
    level = 1
    end = opening + 1
    while level:
        require(end < len(data), 'unterminated exact function')
        level += (data[end] == 123) - (data[end] == 125)
        end += 1
    return start, end


def once(data, old, new):
    require(data.count(old) == 1, 'fixture splice anchor differs: ' + repr(old))
    return data.replace(old, new, 1)


def fixture_source(source, entry):
    require(entry in ADMITTED and (len(source), pin(source)['sha256']) == ADMITTED[entry],
            'fixed-work fixture only admits the exact reviewed current F2/B source')
    if entry == 'F':
        signature = b'void i(X*w,const I*p)'
        main = b'S main(void)'
        recursive = b'S qr('
        driver = once(source[slice(*function(source, signature))],
                      b'for(S a=1;a<127;a++){', b'for(S a=1;a<=bench_limit;a++){')
        driver = once(driver, b'*m+=l-*m/64;}}}', b'*m+=l-*m/64;}bench_record(a,q,b,w->e);}}')
        table, key, datum, flag, workers, root, init, parse, stop = 'B','a','b','zN','U','Z','o','z','V'
        identity, depth, move, nodes, arrays = 'a','b','d','e',('h','i','j')
    else:
        signature = b'void i(zd*w,const za*p)'
        main = b'I main(void)'
        recursive = b'I P('
        driver = once(source[slice(*function(source, signature))],
                      b'for(I a=1;a<=126;a++){', b'for(I a=1;a<=bench_limit;a++){')
        driver = once(driver, b'P(w,p,a,-30000,30000,0,6,&d,0,1);',
                      b'int bench_this_score=P(w,p,a,-30000,30000,0,6,&d,0,1);')
        driver = once(driver, b'w->m=d;w->d=a;}}',
                      b'w->m=d;w->d=a;bench_record(a,bench_this_score,d,w->n);}}')
        table, key, datum, flag, workers, root, init, parse, stop = 'qq','h','v','a','qr','ql','k','R','qp'
        identity, depth, move, nodes, arrays = 'i','d','m','n',('h','c','f')
    start, end = function(source, signature)
    transformed = source[:start] + PREFIX + driver + source[end:]
    transformed = once(transformed, main, main.replace(b'main', b'bench_shipping_main'))
    old_body = source[slice(*function(source, recursive))]
    require(old_body == transformed[slice(*function(transformed, recursive))],
            'recursive shipping search changed')
    hashing = '\n'.join('bench_hash_bytes(&'+workers+'[0].'+a+',sizeof '+workers+'[0].'+a+');' for a in arrays)
    suffix = '''
static uint64_t bench_digest=UINT64_C(1469598103934665603);
static void bench_hash_bytes(const void* object,size_t size){
const unsigned char* bytes=object;for(size_t index=0;index<size;++index){
bench_digest^=bytes[index];bench_digest*=UINT64_C(1099511628211);}}
static void bench_hash_word(uint64_t value){bench_hash_bytes(&value,sizeof value);}
int main(int bench_argc,char**bench_argv){
if(bench_argc!=4)return 64;
bench_limit=atoi(bench_argv[1]);int bench_expected=atoi(bench_argv[2]);
if(bench_limit<2||bench_limit>6||bench_expected<0||bench_expected>4094)return 64;
TABLE=calloc(262144,sizeof *TABLE);if(!TABLE)return 2;
for(size_t bench_index=0;bench_index<262144;++bench_index){
TABLE[bench_index].KEY=0;TABLE[bench_index].DATA=0;atomic_flag_clear(&TABLE[bench_index].FLAG);}
memset(WORKERS,0,sizeof WORKERS);memset(qg,0,sizeof qg);
INIT(&ROOTBOARD);qg[0]=ROOTBOARD.h;qh=1;WORKERS[0].IDENT=0;
char*bench_line=malloc(strlen(bench_argv[3])+1);if(!bench_line)return 2;
strcpy(bench_line,bench_argv[3]);char*bench_command=strtok(bench_line," \\t\\r\\n");
if(!bench_command||strcmp(bench_command,"position"))return 65;
PARSE();if(qh!=bench_expected+1)return 66;
qc=UINT64_MAX;atomic_store(&STOP,0);
struct timespec bench_begin,bench_end;clock_gettime(CLOCK_MONOTONIC,&bench_begin);
i(WORKERS,&ROOTBOARD);clock_gettime(CLOCK_MONOTONIC,&bench_end);
if(bench_count!=bench_limit||WORKERS[0].DEPTH!=bench_limit||atomic_load(&STOP))return 67;
if(bench_rows[bench_limit].move!=WORKERS[0].MOVE)return 68;
HASHING
for(size_t bench_index=0;bench_index<262144;++bench_index){
bench_hash_word(TABLE[bench_index].KEY);bench_hash_word(TABLE[bench_index].DATA);}
uint64_t bench_ns=(uint64_t)(bench_end.tv_sec-bench_begin.tv_sec)*1000000000+
(uint64_t)(bench_end.tv_nsec-bench_begin.tv_nsec);
printf("{\\"nanoseconds\\":%llu,\\"digest\\":\\"%016llx\\",\\"nodes\\":%llu,\\"root_hash\\":\\"%016llx\\",\\"qh\\":%d,\\"iterations\\":[",
(unsigned long long)bench_ns,(unsigned long long)bench_digest,(unsigned long long)WORKERS[0].NODES,
(unsigned long long)ROOTBOARD.h,qh);
for(int bench_index=1;bench_index<=bench_limit;++bench_index){
if(bench_rows[bench_index].depth!=bench_index)return 69;
printf("%s[%d,%d,%u,%llu]",bench_index==1?"":",",bench_index,bench_rows[bench_index].score,
bench_rows[bench_index].move,(unsigned long long)bench_rows[bench_index].nodes);}
puts("]}");free(bench_line);free(TABLE);return 0;}
'''
    replacements = {'TABLE':table, 'KEY':key, 'DATA':datum, 'FLAG':flag, 'WORKERS':workers,
                    'ROOTBOARD':root, 'INIT':init, 'PARSE':parse, 'STOP':stop, 'IDENT':identity,
                    'DEPTH':depth, 'MOVE':move, 'NODES':nodes, 'HASHING':hashing}
    for old in sorted(replacements, key=len, reverse=True):
        suffix = suffix.replace(old, replacements[old])
    result = transformed + suffix.encode('ascii')
    proof = {'kind':'shipping-core-fixed-work-fixture','entry':entry,
             'source':pin(source),'fixture':pin(result), 'recursive_search':pin(old_body),
             'recursive_search_unchanged':True,
             'changes':['bounded iterative depth','completed-iteration observer','unused shipping main renamed','one-worker driver'],
             'counter':'existing Worker local counter; no DEV/shared observer atomic',
             'timing':'only bounded think, excludes initialization/digest/printing',
             'not_proven':['unmodified shipping-native performance','SMP behavior','Elo']}
    return result, proof


def main(args):
    module = load('options_api', HERE/'compiler_options.py')
    comparison = json.loads((args.comparison/'comparison.json').read_bytes())
    require(comparison['complete'] is True, 'complete compiler build comparison required')
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists()
            and not any((p/'.git').exists() for p in (out,*out.parents)), 'new external absolute output required')
    require(2<=args.depth<=6 and 1<=args.repeats<=16, 'finite depth/repeat range required')
    out.mkdir()
    host_module = load('fixed_work_host', ROOT/module.HOST)
    require(pin(module.normalized(ROOT/module.HOST))['sha256'] == module.HOST_PIN, 'host revision drift')
    host_module.LIMITS = {**host_module.LIMITS, 'aggregate_wall':900, 'per_command_wall':90,
        'parent_CPU':180, 'parent_CPU_hard':210, 'child_CPU':60, 'tool_output_bytes':2<<20}
    oracle = load('fixed_work_oracle', ROOT/'engines/tests/chess_oracle.py')
    for moves in POSITIONS.values():
        board=oracle.Board.from_fen()
        for move in moves.split():
            require(move in {str(item) for item in board.legal_moves()}, 'fixture opening is not legal: '+move)
            board=board.play(move)
    report={'format':1,'complete':False,'kind':'shipping-core-fixed-work', 'commands':[],
            'depth':args.depth,'repeats':args.repeats,'timing_scope':args.timing_scope,
            'affinity':sorted(os.sched_getaffinity(0)), 'profiles':{},
            'not_proven':['unmodified shipping-native performance','target TCEC CPU','SMP scaling','Elo'],
            'selection':'measurement-only; never updates selected recipes'}
    def save():
        (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    host=host_module.Host(out,report,save)
    try:
        for entry in args.entries:
            require(entry in ADMITTED and entry in comparison['profiles'], 'admitted F/B build missing')
            profile=comparison['profiles'][entry]
            row={'proof':None,'correctness':{},'samples':[],'paired_ratios':{}}
            report['profiles'][entry]=row
            for level in module.LEVELS:
                build=Path(profile['levels'][level]['build'])
                manifest=json.loads((build/'build.json').read_bytes())
                source=(build/'main.c').read_bytes()
                fixture, proof=fixture_source(source,entry)
                directory=out/(entry+'-'+level[1:]);directory.mkdir()
                (directory/'main.c').write_bytes(fixture)
                command=[profile['compiler_path'],*manifest['compiler'][1:]]
                host.run(command,cwd=directory,kind=entry+'-'+level+'-fixture-compile',data=fixture)
                row['proof']=proof
                row['correctness'][level]={}
                for label,moves in POSITIONS.items():
                    command=[directory/'x',str(args.depth),str(len(moves.split())),
                             'position startpos'+(' moves '+moves if moves else '')]
                    data=host.run(command,cwd=out,kind=entry+'-'+level+'-'+label+'-correctness')
                    result=json.loads(data)
                    signature={k:v for k,v in result.items() if k!='nanoseconds'}
                    row['correctness'][level][label]=signature
            require(all(row['correctness'][level]==row['correctness']['-Os'] for level in module.LEVELS),
                    'compiler-level completed-iteration/work/learner/TT semantics differ')
            for candidate in ('-O2','-O3'):
                ratios=[]
                for repetition in range(args.repeats):
                    for label,moves in POSITIONS.items():
                        values=[]
                        for level in ('-Os',candidate,candidate,'-Os'):
                            directory=out/(entry+'-'+level[1:])
                            command=[directory/'x',str(args.depth),str(len(moves.split())),
                                     'position startpos'+(' moves '+moves if moves else '')]
                            data=host.run(command,cwd=out,kind=entry+'-'+level+'-'+label+'-timing')
                            result=json.loads(data)
                            require({k:v for k,v in result.items() if k!='nanoseconds'}==row['correctness']['-Os'][label],
                                    'timed fixed work drifted')
                            values.append(result['nanoseconds'])
                            row['samples'].append({'candidate':candidate,'repetition':repetition,
                                'position':label,'level':level,**result})
                        ratios.append((values[0]+values[3])/(values[1]+values[2]))
                row['paired_ratios'][candidate]={'samples':ratios,
                    'geometric_mean':math.exp(statistics.mean(map(math.log,ratios))),
                    'median':statistics.median(ratios),'minimum':min(ratios),'maximum':max(ratios)}
            save()
    except BaseException as error:
        report['failure']={'type':type(error).__name__,'message':str(error)};save();raise
    finally:
        host.close()
    report['complete']=True;save()
    print(json.dumps({'out':str(out),'complete':True,'entries':args.entries}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comparison',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--entries',nargs='+',choices=tuple(ADMITTED),default=['F','B'])
    parser.add_argument('--depth',type=int,default=4)
    parser.add_argument('--repeats',type=int,default=2)
    parser.add_argument('--timing-scope',choices=('contended-pilot','declared-isolated-local'),default='contended-pilot')
    main(parser.parse_args())
