#!/usr/bin/env python3
"""Generate an opt-in matched C-policy E study from one immutable Git source.

No canonical source is edited. Generated source, native files and reports must
stay in a new directory outside the repository. Acceptance remains unproven
until the explicit semantic/resource gates in README pass.
"""
import argparse
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
PIN="de5676dcbc498d77477c66064aca926633c851ff"
sys.path.insert(0,str(HERE))
from hash_overlay import apply as align_hashes


def once(text,old,new,label,count=1):
    if text.count(old)!=count:raise ValueError(f"{label}: expected {count} exact anchors, got {text.count(old)}")
    return text.replace(old,new)


def git(*args):
    result=subprocess.run(["git",*args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if result.returncode==0:return result.stdout
    # Windows-managed worktrees store a Windows .git target. WSL Git cannot
    # resolve that target; the Windows Git client still reads the same objects.
    location=str(ROOT)
    if location.startswith("/mnt/")and len(location)>7:
        executable=shutil.which("git.exe")or"/mnt/c/Program Files/Git/cmd/git.exe"
        if Path(executable).is_file():
            windows=location[5].upper()+":\\"+location[7:].replace("/","\\")
            return subprocess.run([executable,"-C",windows,*args],check=True,stdout=subprocess.PIPE).stdout
    raise RuntimeError(result.stderr.decode(errors="replace"))


def frozen_sources():
    revision=git("rev-parse",PIN+"^{commit}").decode().strip()
    if revision!=PIN:raise ValueError("unresolved exact frozen base")
    names=git("ls-tree","-r","--name-only",PIN,"--","engines/c","engines/rust","engines/model").decode().splitlines()
    files={}
    for name in names:
        relative=name.removeprefix("engines/")
        suffix=Path(name).suffix
        if (relative.startswith("c/")and suffix in(".c",".h"))or(relative.startswith("rust/")and suffix==".rs")or(relative.startswith("model/")and suffix in(".h",".rs")):
            files[relative]=git("show",PIN+":"+name)
    return files


def transform(files):
    output,changes=align_hashes(files)
    text=output["rust/search.rs"].decode()
    marker="fn mix(mut x: u64) -> u64"
    if text.count(marker)!=1:raise ValueError("Rust search implementation boundary drift")
    text=text[:text.index(marker)]+(HERE/"search_policy.rs.in").read_text()
    text=once(text,"pub const INF: i32 = 31000;","pub const INF: i32 = 32000;","common INF")
    text=once(text,"MATE - 128","MATE - 96","TT positive mate threshold",2)
    text=once(text,"-MATE + 128","-MATE + 96","TT negative mate threshold",2)
    allocation="Self{slots:(0..size).map(|_|Slot{key:UnsafeCell::new(0),data:UnsafeCell::new([0;7]),lock:AtomicU8::new(0)}).collect(),mask:size-1}"
    text=once(text,allocation,"let result="+allocation+";result.clear();result","startup single TT clear/prefault")
    for name in("search","f_tt"):
        module="tests"if name=="search"else"f_tt_tests"
        text=once(text,f'#[cfg(test)]\n#[path = "../tests/rust/{name}.rs"]\nmod {module};\n',"",f"omit default-policy-only {name} tests")
    output["rust/search.rs"]=text.encode()
    parallel=output["rust/parallel.rs"].decode()
    parallel=once(parallel,"Searcher, Table, INF, MATE","Searcher, Table, Correction, INF, MATE","correction import")
    parallel=once(parallel,"frozen: [[i16; 2048]; 3]","frozen: Correction","correction transport")
    parallel=once(parallel,"frozen: [[0; 2048]; 3]","frozen: [[0; 1024]; 2]","correction transport initialization")
    output["rust/parallel.rs"]=parallel.encode()
    rust_main=output["rust/main.rs"].decode()
    rust_main=once(rust_main,'println!("{{\\"hash\\":{},\\"halfmove\\":{},','println!("{{\\"hash\\":{},\\"pawn_hash\\":{},\\"halfmove\\":{},',"diagnostic pawn hash")
    rust_main=once(rust_main,'board.hash,board.halfmove,eval::evaluate','board.hash,board.study_pawn_key,board.halfmove,eval::evaluate',"diagnostic pawn argument")
    rust_main=once(rust_main,'board.hash==rebuilt.hash&&board.bb==rebuilt.bb','board.hash==rebuilt.hash&&board.study_pawn_key==rebuilt.study_pawn_key&&board.bb==rebuilt.bb',"diagnostic pawn invariant")
    output["rust/main.rs"]=rust_main.encode()

    c=output["c/search.c"].decode()
    c=once(c,"atomic_fetch_add_explicit(&rove_model_calls,1,memory_order_relaxed);","", "equal E raw-evaluation diagnostics")
    tie="if(moves[j].score>moves[at].score)"
    c=once(c,tie,"if(moves[j].score>moves[at].score||(moves[j].score==moves[at].score&&moves[j].m<moves[at].m))","common total ordering",2)
    c=once(c,"generate(p,moves,0)","study_generate(p,moves)","prelegal QS/PVS generation",2)
    witness="static int legal_witness(const Board *p,const Move *moves,int n){for(int i=0;i<n;i++){Board t;if(make_move(p,moves[i].m,&t))return 1;}return 0;}"
    replacement="static int study_generate(const Board *p,Move *moves){int n=generate(p,moves,0),kept=0;for(int i=0;i<n;i++){Board next;if(make_move(p,moves[i].m,&next))moves[kept++]=moves[i];}return kept;}\nstatic int legal_witness(const Board *p,const Move *moves,int n){(void)p;(void)moves;return n>0;}"
    c=once(c,witness,replacement,"prelegal witness contract")
    output["c/search.c"]=c.encode()

    header=output["c/rove.h"].decode()
    helper="""
#if ROVE_VARIANT != 5 || ROVE_PARALLEL != 0
#error matched-c-policy-v1 supports only E with fixed loose sharing
#endif
static inline int rove_study_spawn(pthread_t *thread,void *(*fn)(void *),void *arg){
    pthread_attr_t attr;int error=pthread_attr_init(&attr);if(error)return error;
    error=pthread_attr_setstacksize(&attr,1024*1024);if(!error)error=pthread_create(thread,&attr,fn,arg);
    pthread_attr_destroy(&attr);return error;
}
"""
    at=header.rfind("#endif")
    if at<0:raise ValueError("C header guard missing")
    output["c/rove.h"]=(header[:at]+helper+header[at:]).encode()
    main=output["c/main.c"].decode()
    main=once(main,"pthread_create(thread,NULL,coordinator,s)","rove_study_spawn(thread,coordinator,s)","C coordinator one-MiB stack")
    output["c/main.c"]=main.encode()
    pool=output["c/parallel.h"].decode()
    pool=once(pool,"pthread_create(&pool->threads[i-1],0,rove_parallel_helper,&pool->ids[i-1])","rove_study_spawn(&pool->threads[i-1],rove_parallel_helper,&pool->ids[i-1])","C helper one-MiB stacks")
    output["c/parallel.h"]=pool.encode()
    changes+= ["production Rust E Searcher uses C-policy PVS/QS/history/continuation/killers/correction/LMR",
               "both total order by score descending then packed move ascending; same worker diversity",
               "C QS/PVS prelegal generation; legal_order_domain=all_legal",
               "raw QS evaluation even in check in both; ordering only after standpat cutoff",
               "C E raw-model shared diagnostic increment omitted; neither study core adds shared TT-hit counter",
               "single full-key sixteen-byte TT; common INF/mate/ply/correction/history contracts",
               "both startup TT initialization paths touch every real slot before worker/input admission",
               "actual fixed startup pool, one-MiB search stacks and loose sharing retained"]
    return output,changes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--workers",type=int,choices=(1,4),default=1)
    parser.add_argument("--compile",action="store_true")
    parser.add_argument("--cc",default="cc")
    parser.add_argument("--rustc",default="rustc")
    args=parser.parse_args()
    out=args.out.resolve()
    if out.exists()or out.is_relative_to(ROOT):parser.error("output must be new and outside repository")
    out.mkdir(parents=True)
    before=frozen_sources()
    after,changes=transform(before)
    for name,data in after.items():
        path=out/"source"/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    digest=lambda data:hashlib.sha256(data).hexdigest()
    report={"schema":1,"contract":"matched-c-policy-v1","base":PIN,"changes":changes,
            "policy":{"variant":"E","parallel":"loose","prelegal_generation":True,"legal_order_domain":"all_legal",
                      "cold_process_per_fixture":True,"tt_slot_bytes":16,"tt_bits":18,"tt_total_bytes":4194304,
                      "search_workers":args.workers,"total_threads":args.workers+1,"search_stack_bytes":1048576,
                      "startup_tt_clear_prefault":True,
                      "correction_leaf":False,"correction_lmr":True,"raw_eval_in_checked_qs":True,
                      "ordering_tie":"score descending, packed move ascending","worker_diversity":"C additive 31-mask",
                      "c_lto":True,"rust_lto":"fat","optimization":"speed"},
            "sources":[{"path":name,"before_sha256":digest(before[name]),"sha256":digest(data)}for name,data in sorted(after.items())],
            "templates":[{"path":str(path.relative_to(ROOT)),"sha256":digest(path.read_bytes())}for path in sorted(HERE.iterdir())if path.suffix in(".py",".in")],
            "acceptance":"unproven; semantic/resource/runtime gates remain required","engines":[],"generated":True}
    try:
        if args.compile:
            sys.path.insert(0,str(ROOT/"engines/scripts"))
            spec=importlib.util.spec_from_file_location("matched_build",ROOT/"engines/scripts/build.py")
            build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
            report["recipe_helpers"]=[{"path":str(path.relative_to(ROOT)),"sha256":digest(path.read_bytes())}for path in(ROOT/"engines/scripts").iterdir()if path.suffix==".py"]
            report["tools"]={language:{"requested":tool,"resolved":str(Path(shutil.which(tool)or tool).resolve()),"version":build.tool_version(tool)}for language,tool in(("c",args.cc),("rust",args.rustc))}
            profile={"search_workers":args.workers,"expected_total_threads":args.workers+1,"tt_bits":18,"development":True}
            for language in("c","rust"):
                files={name:data for name,data in after.items()if name.startswith(language+"/")or name.startswith("model/")and name.endswith(".h"if language=="c"else".rs")}
                command,environment=build.compiler_recipe(language,"E",profile,"speed",compiler=args.cc if language=="c"else args.rustc,files=files,parallel=0,c_lto=True)
                if language=="rust":command[1:1]=["--cfg","rove_f_single","--cfg","rove_matched_c_policy"]
                native=build.compile_files(files,out/language,command,environment)
                report["engines"].append({"id":"E-"+language,"command":[native["path"]],"configuration":environment,"profile":"dev","workers":args.workers,"native":native})
                print(language+": compiled "+str(native["bytes"])+" bytes",flush=True)
    finally:
        (out/"generation.json").write_text(json.dumps(report,indent=2)+"\n")
    return 0


if __name__=="__main__":raise SystemExit(main())
