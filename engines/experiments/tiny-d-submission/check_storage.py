#!/usr/bin/env python3
"""Actual scalar-D search/learner/TT comparison for storage projections.

The driver includes the generated board.c and search.c, with DEV=0 and D_HQ=0.
Only observation and explicit claim-cancellation hooks are injected identically
into each variant. Plain and UBSan builds are compared. This is a single-threaded
C contract fixture, not the
no-libc runtime, NUMA, packaging, 4KiB, target-throughput or strength acceptance.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


DRIVER = r'''#include <stdio.h>
#include <inttypes.h>
#include <string.h>
#include "tiny.h"

extern void *calloc(size_t,size_t);
extern void free(void *);
Entry *table;
atomic_int stopped;
uint64_t deadline=UINT64_MAX,game_keys[HISTORY];
int game_length;
Board position;
static Worker fixture_worker;
static uint64_t test_claims,test_cancel_at,test_narrow,test_research,path_digest;
static uint64_t total_runs,total_cancel_runs,total_research;
static void observe_entry(const Worker *,const Board *,int,int);
uint64_t now(void){return 0;}

#include "board.c"
#include "search.c"

static uint64_t add_hash(uint64_t h,uint64_t value){
    for(int i=0;i<8;i++){h^=(unsigned char)value;h*=UINT64_C(1099511628211);value>>=8;}
    return h;
}
static void observe_entry(const Worker *w,const Board *p,int depth,int ply){
    int length=game_length+ply,end=length-1-p->half;if(end<0)end=0;
    path_digest=add_hash(path_digest,(unsigned)depth);
    path_digest=add_hash(path_digest,(unsigned)ply);
    path_digest=add_hash(path_digest,p->h);
    path_digest=add_hash(path_digest,p->r);
    path_digest=add_hash(path_digest,(unsigned)p->half);
    for(int i=length-3;i>=end;i-=2){
#if CASE_PREFIX
        uint64_t key=i<game_length?game_keys[i]:w->keys[i-game_length];
#else
        uint64_t key=w->keys[i];
#endif
        path_digest=add_hash(path_digest,(unsigned)i);
        path_digest=add_hash(path_digest,key);
    }
}
static uint64_t learners(const Worker *w){
    uint64_t h=UINT64_C(1469598103934665603);
    /* Independently enumerate rank/file, never inherit layout padding/tails. */
    for(int a=0;a<64;a++)for(int b=0;b<64;b++){
#if CASE_DENSE
        int16_t value=w->history[a][b];
#else
        int16_t value=w->history[(a/8)*16+a%8][(b/8)*16+b%8];
#endif
        h=add_hash(h,(uint16_t)value);
    }
    for(int a=0;a<13;a++)for(int b=0;b<13;b++)h=add_hash(h,(uint16_t)w->continuation[a][b]);
    for(int a=0;a<1024;a++)h=add_hash(h,(uint16_t)w->correction[a]);
    return h;
}
static uint64_t tt_digest(void){
    uint64_t h=UINT64_C(1469598103934665603);
    for(size_t i=0;i<((size_t)1<<TT_BITS);i++){
        h=add_hash(h,table[i].key);h=add_hash(h,table[i].data);
    }
    return h;
}
static int replay(Board *p,const char *moves){
    start(p);game_length=1;game_keys[0]=p->h;
    while(*moves){
        while(*moves==' ')moves++;
        if(!*moves)break;
        char name[6];unsigned n=0;
        while(*moves&&*moves!=' '){if(n==5)return 0;name[n++]=*moves++;}
        name[n]=0;if(n!=4&&n!=5)return 0;
        unsigned from=(unsigned)(name[0]-'a')+16u*(unsigned)(name[1]-'1');
        unsigned to=(unsigned)(name[2]-'a')+16u*(unsigned)(name[3]-'1'),promotion=0;
        if(n==5){for(promotion=2;promotion<6&&"  nbrq"[promotion]!=name[4];promotion++);if(promotion==6)return 0;}
        Move wanted=MOVE(from,to,promotion),list[MOVES];int found=0,count=gen(p,list);Board next;
        for(int i=0;i<count;i++)if((list[i]&~8u)==wanted&&make(p,list[i],&next)){found=1;break;}
        if(!found||game_length==HISTORY)return 0;
        *p=next;game_keys[game_length++]=p->h;
    }
    return 1;
}
static int cycle_prefix(Board *p,int plies){
    const char *cycle[4]={"g1f3","g8f6","f3g1","f6g8"};
    start(p);game_length=1;game_keys[0]=p->h;
    for(int j=0;j<plies;j++){
        const char *s=cycle[j%4];
        Move wanted=MOVE((s[1]-'1')*16+s[0]-'a',(s[3]-'1')*16+s[2]-'a',0),list[MOVES];
        int count=gen(p,list),found=0;Board next;
        for(int i=0;i<count;i++)if((list[i]&~8u)==wanted&&make(p,list[i],&next)){found=1;break;}
        if(!found||game_length==HISTORY)return 0;
        *p=next;game_keys[game_length++]=p->h;
    }
    return 1;
}
static uint64_t run(const char *name,const Board *p,int depth,uint64_t cancel,int reset,int worker){
    if(reset){memset(&fixture_worker,0,sizeof fixture_worker);memset(table,0,((size_t)1<<TT_BITS)*sizeof *table);}
    fixture_worker.id=worker;fixture_worker.nodes=0;fixture_worker.depth=0;fixture_worker.best=0;
#if !CASE_PREFIX
    fixture_worker.length=game_length;memcpy(fixture_worker.keys,game_keys,(size_t)game_length*sizeof *game_keys);
#endif
    test_claims=test_narrow=test_research=0;test_cancel_at=cancel;
    path_digest=UINT64_C(1469598103934665603);
    atomic_store_explicit(&stopped,0,memory_order_relaxed);
    Move best=0;int score=search(&fixture_worker,p,depth,-MATE,MATE,0,0,&best);
#if !CASE_PREFIX
    if(fixture_worker.length!=game_length){puts("BROKEN_LOGICAL_LENGTH");return UINT64_MAX;}
#endif
    printf("%s depth=%d cancel=%" PRIu64 " reset=%d worker=%d score=%d best=%u nodes=%" PRIu64
           " claims=%" PRIu64 " stopped=%d narrow=%" PRIu64 " research=%" PRIu64
           " path=%016" PRIx64 " learner=%016" PRIx64 " tt=%016" PRIx64 "\n",
           name,depth,cancel,reset,worker,score,best,fixture_worker.nodes,test_claims,atomic_load(&stopped),
           test_narrow,test_research,path_digest,learners(&fixture_worker),tt_digest());
    total_runs++;total_cancel_runs+=cancel!=0;total_research+=test_research;
    return test_claims;
}
int main(void){
    table=calloc((size_t)1<<TT_BITS,sizeof *table);if(!table)return 2;
    printf("ABI worker=%zu board=%zu entry=%zu\n",sizeof(Worker),sizeof(Board),sizeof(Entry));
    const char *openings[]={
        "",
        "e2e4",
        "e2e4 e7e5 g1f3 b8c6",
        "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4",
        "d2d4 d7d5 c2c4 e7e6 b1c3 g8f6",
        "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 e1g1",
        "e2e4 h7h6 e4e5 d7d5 e5d6",
        "d2d4 g8f6 c2c4 g7g6 b1c3 d7d5 c4d5 f6d5",
        "e2e4 e7e5 f2f4 e5f4 g1f3 g7g5 h2h4",
        "g1f3 g8f6 f3g1 f6g8",
        "g1f3 g8f6 f3g1 f6g8 g1f3 g8f6 f3g1 f6g8"
    };
    Board p;char name[64];
    for(unsigned c=0;c<sizeof openings/sizeof *openings;c++){
        if(!replay(&p,openings[c])){printf("ILLEGAL_FIXTURE %u\n",c);return 3;}
        snprintf(name,sizeof name,"opening-%u",c);
        uint64_t claims=run(name,&p,c<9?4:3,0,1,c%3?0:255);
        if(claims==UINT64_MAX)return 4;
        uint64_t limit=claims<128?claims:128;
        for(uint64_t stop=1;stop<=limit;stop++)if(run(name,&p,c<9?4:3,stop,1,c%3?0:255)==UINT64_MAX)return 4;
        for(uint64_t stop=256;stop<claims;stop*=2)if(run(name,&p,c<9?4:3,stop,1,c%3?0:255)==UINT64_MAX)return 4;
        if(claims>128&&run(name,&p,c<9?4:3,claims,1,c%3?0:255)==UINT64_MAX)return 4;
    }
    /* Several GO-equivalent searches retain learners/TT across changed roots. */
    for(int round=0;round<3;round++)for(unsigned c=0;c<9;c++){
        if(!replay(&p,openings[c]))return 3;
        snprintf(name,sizeof name,"persistent-%d-%u",round,c);
        if(run(name,&p,3,(round==1&&c==3)?17:0,round==0&&c==0,(int)c%2)==UINT64_MAX)return 4;
    }
    /* Long legal move replay is an input/path boundary, already drawn. */
    if(!cycle_prefix(&p,HISTORY-1)||game_length!=HISTORY)return 5;
    if(run("history-4096",&p,4,0,1,0)==UINT64_MAX)return 4;
    /* Explicit halfmove-window boundary states; not claimed as corpus games. */
    for(int half=0;half<=101;half++){
        if(!replay(&p,openings[3]))return 3;p.half=half;
        snprintf(name,sizeof name,"synthetic-half-%d",half);
        if(run(name,&p,2,0,1,0)==UINT64_MAX)return 4;
    }
    printf("TOTAL runs=%" PRIu64 " cancellation_runs=%" PRIu64 " research=%" PRIu64 "\n",
           total_runs,total_cancel_runs,total_research);
    free(table);return total_research?0:6;
}
'''


def instrument(source_tool, files):
    edits = [
        ("claim-checkpoint", b"static int claim(Worker *w){\n",
         b"static int claim(Worker *w){\n    if(++test_claims==test_cancel_at){atomic_store(&stopped,1);return 0;}\n"),
        ("actual-search-entry", b"    if(!claim(w))return 0;\n",
         b"    if(!claim(w))return 0;\n    observe_entry(w,p,depth,ply);\n"),
        ("actual-PVS-narrow", b"        int narrow=legal>1&&depth>0,reduce=0;\n",
         b"        int narrow=legal>1&&depth>0,reduce=0;test_narrow+=narrow;\n"),
        ("actual-PVS-research", b"            if(reduce)reduce=0;else narrow=0;\n",
         b"            ++test_research;if(reduce)reduce=0;else narrow=0;\n"),
    ]
    result = dict(files)
    result["search.c"], proof = source_tool.project(files["search.c"], edits)
    return result, proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if (sys.platform != "linux" or platform.machine() != "x86_64" or
            not args.out.is_absolute() or out.exists() or
            any((p / ".git").exists() for p in (out, *out.parents))):
        parser.error("new absolute output outside Git on Linux x86-64 required")
    source = load("D_storage_actual_source", HERE / "source.py")
    storage = load("D_storage_actual_projection", HERE / "storage.py")
    api = source.production()
    profile = api.ResourceProfile("storage-fixture-tt12-w256", "test", 256, 16 << 12)
    files, source_proof = source.prepare(profile)
    hostmod = load("D_storage_actual_host", ROOT / source.HOST)
    if source.pin(source.normalized(ROOT / source.HOST))["sha256"] != source.HOST_SHA:
        raise ValueError("bounded original command owner differs")
    hostmod.LIMITS = {**hostmod.LIMITS, "aggregate_wall": 600, "per_command_wall": 90,
                      "parent_CPU": 240, "parent_CPU_hard": 270, "child_CPU": 75,
                      "tool_output_bytes": 4 << 20}
    out.mkdir()
    report = dict(kind="D-actual-C-search-storage-contract-v2", complete=False, commands=[],
                  source=source_proof, resource=profile.to_record(16), cases=[],
                  modes=["plain", "ubsan"],
                  actual_runtime=False, actual_target_allocation=False, strength_claim=False)
    named_inputs = set(source_proof["input_sources"]) | {
        "engines/compact/tiny-entry-d/recipe.json",
        "engines/compact/tiny-entry-d/shipping_fused_ray.py",
        "engines/scripts/production.py", source.HOST,
        *(str((HERE / name).relative_to(ROOT)).replace("\\", "/")
          for name in ("source.py", "storage.py", "check_storage.py"))}
    report["inputs"] = {}
    for logical in sorted(named_inputs):
        data = source.normalized(ROOT / logical)
        observed = source.pin(data)
        if logical in source_proof["input_sources"] and observed != source_proof["input_sources"][logical]:
            raise ValueError("canonical input changed before freezing: " + logical)
        frozen = out / "frozen-inputs" / logical
        frozen.parent.mkdir(parents=True, exist_ok=True)
        frozen.write_bytes(data)
        report["inputs"][logical] = observed
    prepared = out / "prepared"
    prepared.mkdir()
    for name, data in files.items():
        (prepared / name).write_bytes(data)
    report["prepared"] = {name: source.pin(data) for name, data in files.items()}
    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    host = hostmod.Host(out, report, save)
    baseline = None
    try:
        combinations = [(mode, prefix, dense) for mode in report["modes"]
                        for prefix, dense in ((False, False), (True, False), (False, True), (True, True))]
        for mode, prefix, dense in combinations:
            name = f"{mode}-prefix-{int(prefix)}-dense-{int(dense)}"
            directory = out / name
            directory.mkdir()
            projected, projection_proof = storage.transform(files, prefix=prefix, dense=dense)
            generated, observation_proof = instrument(source, projected)
            for filename in ("tiny.h", "board.c", "search.c"):
                (directory / filename).write_bytes(generated[filename])
            (directory / "driver.c").write_text(DRIVER)
            binary = directory / "fixture"
            flags = ["-std=c11", "-O2", "-g0", "-msse4.2", "-mcx16", "-DDEV=0", "-DD_HQ=0",
                     "-DWORKERS=256", "-DTT_BITS=12", "-DPLY=128",
                     f"-DCASE_PREFIX={int(prefix)}", f"-DCASE_DENSE={int(dense)}"]
            if mode == "ubsan":
                flags += ["-fsanitize=undefined", "-fno-sanitize-recover=undefined"]
            host.run(["cc", *flags, str(directory / "driver.c"), "-o", str(binary)],
                     cwd=directory, kind="compile-" + name)
            output = host.run([str(binary)], cwd=directory, kind="execute-" + name)
            lines = output.splitlines()
            if not lines or not lines[0].startswith(b"ABI ") or not lines[-1].startswith(b"TOTAL "):
                raise ValueError("actual C observation output incomplete")
            normalized = b"\n".join(lines[1:]) + b"\n"
            if baseline is None:
                baseline = normalized
            if normalized != baseline:
                raise ValueError("actual search/storage observations differ: " + name)
            row = dict(name=name, mode=mode, prefix=prefix, dense=dense, flags=flags,
                       binary=source.pin(binary.read_bytes()),
                       worker_abi=lines[0].decode(), totals=lines[-1].decode(),
                       observations=source.pin(normalized),
                       projection=projection_proof, instrumentation=observation_proof,
                       output=source.pin(output), equal=True)
            report["cases"].append(row)
            save()
        for logical, expected in report["inputs"].items():
            if source.pin(source.normalized(ROOT / logical)) != expected:
                raise ValueError("source changed during fixture")
        report["complete"] = True
        report["actual_functions_equal"] = True
        print(json.dumps(dict(complete=True, cases=len(report["cases"]),
                              totals=report["cases"][0]["totals"], actual_runtime=False)), flush=True)
    except BaseException as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        host.close()
        save()


if __name__ == "__main__":
    main()
