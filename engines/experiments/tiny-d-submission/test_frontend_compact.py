#!/usr/bin/env python3
"""One in-place frontend candidate: actual clock/state/ID/rules/search/cost.

The old selected image and its admission remain unchanged. Each candidate is
fresh own-source generation; changes to ignored syscall registers and terminal
output ownership are named semantic classes, never old-byte equivalence.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FILES = ("tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld")
EXPECTED = {"linked": dict(bytes=7488, sha256="87c9f93a87a5d53aaa094a0019952cafbbf8da2ff83c382dee1f1c927d91f00f"),
            "stripped": dict(bytes=7136, sha256="448eeb52aa59e7eaaf7830940be18f5618129d55732d8855e0c8bcb13368f565")}


def pin(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def normalized(path):
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ValueError("lone CR in named input")
    return data


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def shipping_board(preprocessed,emitted,legacy,reduction,minifier,lexical):
    """Replay complete-TU accepted lexical stages on its actual Board prefix."""
    board=minifier.compact_source(preprocessed,"c").rstrip(b"\n")
    for old,new in legacy.items():board=lexical._replace({"main.c":board},old,new)["main.c"]
    alpha={}
    for stage in reduction["stages"]:
        if stage["status"]!="accepted":continue
        if stage["kind"]=="unused-scalar-typedefs":
            for round in stage["rounds"]:
                parts,at=[],0
                for row in round.get("main.c",{}).get("removed",[]):
                    a,b=row["begin"],row["end"]
                    if a>=len(board):continue
                    if a<at or b>len(board) or board[a:b]!=row["declaration"].encode():
                        raise ValueError("whole-TU typedef cut differs in Board prefix")
                    parts.append(board[at:a]);at=b
                parts.append(board[at:]);board=b"".join(parts)
        elif stage["kind"]=="batch-alpha":alpha=stage["renames"]
        else:raise ValueError("unknown accepted source stage")
    text,parts,at=board.decode(),[],0
    for a,b,token in lexical._identifier_spans(text):
        if token in alpha:parts.extend((text[at:a],alpha[token]));at=b
    parts.append(text[at:]);board="".join(parts).encode()
    if not board.endswith(b"}") or not emitted["main.c"].startswith(board):
        raise ValueError("fresh Board is not complete actual shipping prefix")
    names={n:alpha.get(legacy.get(n,n),legacy.get(n,n)) for n in ("Board","start","gen","make","size_t")}
    size=names["size_t"]
    declarations=("\ntypedef "+size+" size_t;\n").encode() if size!="size_t" else b"\n"
    declarations += (b"extern size_t strlen(const char *);extern int strcmp(const char *,const char *);"
        b"extern char *strtok_r(char *,const char *,char **);extern int printf(const char *,...);"
        b"extern int puts(const char *);extern char *strcpy(char *,const char *);\n")
    binding=dict(board=names["Board"],start=names["start"],generate=names["gen"],make=names["make"],four_args=False)
    return board,binding,declarations


FRONTEND_DRIVER = b'#include <stdio.h>\n#include <inttypes.h>\n#include <string.h>\n#include "tiny.h"\nextern unsigned long long strtoull(const char *,char **,int);\n#include "board.c"\n#include "search.c"\n#define main fixture_unused_engine_main\n#include "runtime.c"\n#undef main\n#ifndef FRONTEND_CSTRING\n#define FRONTEND_CSTRING 0\n#endif\n#ifndef FRONT_ID\n#define FRONT_ID D_command\n#endif\nstatic void fail(const char *s){printf("BROKEN %s\\n",s);fflush(stdout);abort();}\nstatic uint64_t hash_word(uint64_t h,uint64_t x){for(int i=0;i<8;i++){h^=(unsigned char)x;h*=UINT64_C(1099511628211);x>>=8;}return h;}\nstatic uint64_t board_hash(const Board *p){\n uint64_t h=UINT64_C(1469598103934665603);\n h=hash_word(h,(unsigned)p->s);h=hash_word(h,(unsigned)p->c);h=hash_word(h,(unsigned)p->e);\n h=hash_word(h,(unsigned)p->k[0]);h=hash_word(h,(unsigned)p->k[1]);h=hash_word(h,(unsigned)p->half);\n h=hash_word(h,(unsigned)p->v);h=hash_word(h,p->h);h=hash_word(h,p->r);\n for(int q=0;q<128;q++)h=hash_word(h,(unsigned char)p->b[q]);return h;\n}\nstatic uint64_t global_position_hash(void){\n uint64_t h=hash_word(board_hash(&position),(unsigned)game_length);\n for(int q=0;q<HISTORY;q++)h=hash_word(h,game_keys[q]);return h;\n}\nstatic int parse_text(const Board *p,char *s,Board *q){\n#if FRONTEND_CSTRING\n return parse_apply(p,s,q);\n#else\n return parse_apply(p,(Span){s,(unsigned)strlen(s)},q);\n#endif\n}\nstatic int command_text(char *line){\n#if FRONTEND_CSTRING\n char *cursor=line;int id=FRONT_ID(scan(&cursor));\n if(id==1||id==2)return id;\n if(*scan(&cursor))return 0;\n return id;\n#else\n const char *cursor=line;Span command=scan(&cursor);\n if(word(command,"position"))return 1;\n if(word(command,"go"))return 2;\n if(scan(&cursor).n)return 0;\n if(word(command,"uci"))return 3;\n if(word(command,"isready"))return 4;\n if(word(command,"quit"))return 5;\n return 0;\n#endif\n}\nstatic uint64_t reference_deadline(const char *cursor,int side){\n uint64_t clock=0,inc=0,budget;int present=0;char key[64],val[64];int used;\n while(sscanf(cursor,"%63s%n",key,&used)==1){\n  cursor+=used;\n  if(strcmp(key,"wtime")&&strcmp(key,"btime")&&strcmp(key,"winc")&&strcmp(key,"binc"))continue;\n  uint64_t value=0;\n  if(sscanf(cursor,"%63s%n",val,&used)==1&&val[0]>=\'0\'&&val[0]<=\'9\'){\n   char *end;unsigned long long parsed=strtoull(val,&end,10);cursor+=used;\n   if(!*end&&parsed<=(unsigned long long)LLONG_MAX)value=(uint64_t)parsed;\n  }\n  if((key[0]==\'w\'?1:-1)==side){if(key[1]==\'t\')clock=value,present=1;else inc=value;}\n }\n if(present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}\n else budget=1000;\n return UINT64_C(1000000)+(budget>86400000?86400000:budget);\n}\nstatic void clock_checks(void){\n static const char *cases[]={\n  "", "wtime 0 btime 0", "wtime 1", "btime 1", "wtime 30", "btime 30",\n  "wtime 30000 btime 60000 winc 100 binc 200", "binc 200 winc 100 btime 60000 wtime 30000",\n  "wtime 10 winc 86400000", "btime 10 binc 86400001", "wtime 9223372036854775807",\n  "btime 9223372036854775807", "wtime 9223372036854775808", "wtime 18446744073709551615",\n  "btime 18446744073709551616", "winc 18446744073709551616 wtime 30000", "wtime -1 btime +2",\n  "wtime btime 60 winc 0", "btime wtime 60 binc 0", "winc wtime 30", "binc btime 30",\n  "wtime 12x wtime 33", "btime 12x btime 33", "wtime 1 wtime 2", "btime 1 btime 2",\n  "unknown 8 wtime 30 debug 9", "wtime 30btime 40", "wtime 30 winc 40 binc 50 btime 60",\n  "  wtime\\t3000\\r winc 300  ", "wtime", "btime", "wtime wtime wtime 30"\n };\n for(int black=0;black<2;black++){\n  char setup[64];strcpy(setup,black?"startpos moves e2e4":"startpos");set_position(setup);\n  for(unsigned c=0;c<sizeof cases/sizeof *cases;c++){\n   char args[1024];strcpy(args,cases[c]);uint64_t before=global_position_hash(),expected=reference_deadline(cases[c],position.s);\n   atomic_store_explicit(&pending,0,memory_order_relaxed);atomic_store_explicit(&stopped,1,memory_order_relaxed);\n   int old_epoch=atomic_load_explicit(&epoch,memory_order_relaxed);go(args);\n   if(deadline!=expected||atomic_load_explicit(&pending,memory_order_relaxed)!=WORKERS+1||\n      atomic_load_explicit(&stopped,memory_order_relaxed)!=0||atomic_load_explicit(&epoch,memory_order_relaxed)!=old_epoch+1||\n      before!=global_position_hash())fail("clock-publication");\n   Board q;if(!fallback||!make(&position,fallback,&q))fail("fallback-legal");\n   printf("GO side=%d case=%u deadline=%" PRIu64 " fallback=%u pending=%d stopped=%d epoch=%d state=%016" PRIx64 "\\n",\n    position.s,c,deadline,fallback,atomic_load(&pending),atomic_load(&stopped),atomic_load(&epoch),before);\n   atomic_store_explicit(&pending,0,memory_order_relaxed);\n  }\n }\n}\nstatic void position_checks(void){\n static const struct{const char *s;int length;}cases[]={\n  {"startpos",1},{"startpos moves",1},{" startpos   moves e2e4  ",2},\n  {"startpos moves e2e4 e7e5 g1f3 b8c6",5},\n  {"startpos moves e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 e1g1",10},\n  {"startpos moves e2e4 h7h6 e4e5 d7d5 e5d6",6},\n  {"startpos moves g1f3 g8f6 f3g1 f6g8",5},\n  {"",0},{"fen whatever",0},{"startpos extra",0},{"startpos moves a1a1",0},\n  {"startpos moves e2e4 e7e5 e1g1",0},{"startpos moves e2e4 a7a8q",0},\n  {"startpos moves e2e4N",0},{"startpos moves i2i4",0},{"startpos moves e2e9",0}\n };\n memset(game_keys,0,sizeof game_keys);start(&position);game_length=1;game_keys[0]=position.h;\n for(unsigned c=0;c<sizeof cases/sizeof *cases;c++){\n  char input[32768];strcpy(input,cases[c].s);uint64_t before=global_position_hash();set_position(input);\n  if(cases[c].length){if(game_length!=cases[c].length)fail("position-length");}\n  else if(global_position_hash()!=before)fail("invalid-position-mutation");\n  printf("POSITION case=%u length=%d state=%016" PRIx64 "\\n",c,game_length,global_position_hash());\n }\n for(int plies=HISTORY-1;plies<=HISTORY;plies++){\n  char input[32768],*out=input;const char *prefix="startpos moves ";while(*prefix)*out++=*prefix++;\n  const char *cycle[]={"g1f3 ","g8f6 ","f3g1 ","f6g8 "};\n  for(int p=0;p<plies;p++){const char *s=cycle[p&3];while(*s)*out++=*s++;}*out=0;\n  if((size_t)(out-input)>=sizeof input)fail("fixture-input-bound");\n  uint64_t before=global_position_hash();set_position(input);\n  if(plies==HISTORY-1){if(game_length!=HISTORY)fail("history-full");}\n  else if(global_position_hash()!=before)fail("history-overflow-mutation");\n  printf("HISTORY plies=%d length=%d state=%016" PRIx64 "\\n",plies,game_length,global_position_hash());\n }\n}\nstatic void promotion_checks(void){\n unsigned checks=0;uint64_t digest=UINT64_C(1469598103934665603);\n for(int side=-1;side<=1;side+=2){\n  Board p={0};p.s=side;p.e=-1;put(&p,4,6);put(&p,116,-6);\n  if(side>0){put(&p,96,1);put(&p,113,-4);}else{put(&p,23,-1);put(&p,6,4);}\n  p.h^=state(&p);p.r=p.h;\n  for(unsigned promotion=2;promotion<=5;promotion++)for(int capture=0;capture<2;capture++){\n   char name[6];unsigned from=side>0?96:23,to=side>0?(capture?113:112):(capture?6:7);\n   Move move=MOVE(from,to,promotion)|(capture?8u:0);Board expected,actual;\n   text(move,name);if(!make(&p,move,&expected)||!parse_text(&p,name,&actual)||board_hash(&actual)!=board_hash(&expected))fail("promotion-parse");\n   digest=hash_word(digest,board_hash(&actual));checks++;\n  }\n  static const char *bad[]={"", "0000", "i1a2", "a0a2", "a1a9", "a7a8k", "h2h1k", "a7a8nn", "h2h1nn"};\n  for(unsigned b=0;b<sizeof bad/sizeof *bad;b++){char name[16];Board actual;strcpy(name,bad[b]);if(parse_text(&p,name,&actual))fail("invalid-move-accepted");}\n }\n printf("PROMOTION checks=%u invalid=18 digest=%016" PRIx64 "\\n",checks,digest);\n}\nint main(void){\n static const struct{const char *s;int id;}ids[]={\n  {"",0},{" ",0},{"position",1},{"position startpos",1},{"go",2},{" go wtime 3",2},\n  {"uci",3},{" uci \\t",3},{"uci extra",0},{"isready",4},{"isreadyx",0},{"isready extra",0},\n  {"quit",5},{"quit extra",0},{"goof",0},{"quits",0},{"positionx startpos",0},\n  {"setoption name Threads value 1",0},{"stop",0},{"ucinewgame",0},{"ponderhit",0},{"debug on",0},{"register",0}\n };\n printf("ABI worker=%zu board=%zu entry=%zu\\n",sizeof(Worker),sizeof(Board),sizeof(Entry));\n for(unsigned i=0;i<sizeof ids/sizeof *ids;i++){char text[256];strcpy(text,ids[i].s);int got=command_text(text);if(got!=ids[i].id)fail("command-id");printf("ID case=%u value=%d\\n",i,got);}\n position_checks();promotion_checks();clock_checks();puts("TOTAL commands=23 positions=18 promotions=16 clock_cases=64");return 0;\n}\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out, selected = args.out.resolve(), args.build.resolve()
    if (sys.platform != "linux" or platform.machine() != "x86_64" or not args.out.is_absolute()
            or not args.build.is_absolute() or out.exists() or any((p/".git").exists() for p in (out,*out.parents))):
        parser.error("new external output and absolute selected build on Linux x86-64 required")
    control = json.loads((selected/"build.json").read_bytes())
    producer={"engines/compact/tiny-entry-d/native/"+name for name in FILES}|{
        "engines/compact/tiny-entry-d/recipe.json", "engines/compact/tiny-entry-d/shipping_fused_ray.py",
        "engines/compact/tiny-entry-d/packer.py", "engines/experiments/tcec-scope/build.py",
        "engines/scripts/production.py", "engines/scripts/minify.py", "engines/scripts/rename_c.py",
        "engines/experiments/tiny-d-submission/source.py", "engines/experiments/tiny-d-submission/build.py",
        "engines/experiments/tiny-d-submission/packaging.py", "engines/experiments/tiny-d-submission/storage.py"}
    if (control.get("storage") != "prefix" or control.get("source_reduced") is not False or
            control.get("family")!="D" or control.get("equivalent_edits") is not True or
            any(control.get(key) is not True for key in ("complete","frozen_execution","native_reproduced")) or
            set(control.get("inputs",{}))!=producer or control.get("units")!=["main.c","start.S"]):
        raise ValueError("unreduced prefix control required")
    inputs = {name:normalized(ROOT/name) for name in control["inputs"]}
    for name,data in inputs.items():
        if pin(data) != control["inputs"][name] or (selected/"inputs"/name).read_bytes() != data:
            raise ValueError("current/selected exact producer differs: "+name)
    for name in ("reduce.py", "publication.py", "process_owner.py", "test_startup.py", "test_process_owner.py",
                 "compressed_bootstrap.py", "syscall_arity.py", "test_runtime_scaffold.py", "valid_input.py",
                 "search_compact.py", "probe_search_compact.py", "check_storage.py", "frontend_compact.py", "test_frontend_compact.py"):
        logical = "engines/experiments/tiny-d-submission/"+name
        inputs[logical] = normalized(ROOT/logical)
    inputs["selection/build.json"] = (selected/"build.json").read_bytes()
    for name in ("engines/experiments/tcec-next/profile_rules.py","engines/tests/chess_oracle.py"):
        inputs[name]=normalized(ROOT/name)
    out.mkdir()
    for name,data in inputs.items():
        path=out/"inputs"/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    frozen=load("d_frontend_frozen",out/"inputs/engines/experiments/tiny-d-submission/test_frontend_compact.py")
    frozen.run_snapshot(out,inputs,ROOT)


def run_snapshot(out,inputs,origin):
    mods={n:load("d_scaffold_"+n,HERE/(n+".py")) for n in
          ("source","build","storage","publication","process_owner","test_startup","test_process_owner",
           "packaging","compressed_bootstrap","reduce","syscall_arity","valid_input","test_runtime_scaffold",
           "search_compact","check_storage","probe_search_compact","frontend_compact")}
    rules_tool=load("d_frontend_actual_rules",ROOT/"engines/experiments/tcec-next/profile_rules.py")
    source, builder, startup = mods["source"],mods["build"],mods["test_startup"]
    original_dialogue=mods["test_runtime_scaffold"].DIALOGUE
    witness='  history=b"g1f3 g8f6 f3g1 f6g8 "*256\n'
    if original_dialogue.count(witness)!=1:raise ValueError("frozen valid dialogue extension boundary differs")
    extension='  send(b"isready"+b" "*32760+b"\\n");until(b"readyok");record["max_line_payload_bytes"]=32767;save()\n'
    DIALOGUE=original_dialogue.replace(witness,extension+witness)
    lexical=load("d_scaffold_lexical",ROOT/"engines/scripts/rename_c.py")
    minifier=load("d_scaffold_minify",ROOT/"engines/scripts/minify.py")
    packer=load("d_scaffold_packer",source.CANONICAL/"packer.py")
    hostmod=load("d_scaffold_commands",ROOT/source.HOST)
    if pin(normalized(ROOT/source.HOST))["sha256"] != source.HOST_SHA:
        raise ValueError("original command owner differs")
    hostmod.LIMITS={**hostmod.LIMITS,"aggregate_wall":900,"per_command_wall":90,"parent_CPU":500,"parent_CPU_hard":540,"child_CPU":75,"tool_output_bytes":8<<20}
    report=dict(kind="D-in-place-frontend-source-rules-search-cost-v1",complete=False,frozen_execution=True,
        inputs={n:pin(d) for n,d in inputs.items()},commands=[],variants=[],runtime_cases=[],
        selected=False,old_admission_changed=False,runtime_qualified=False,rules_qualified=False,
        real_target_allocation=False,locality_proof=False,strength_claim=False)
    def save():(out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    save();host=hostmod.Host(out,report,save)
    def run(command,*,cwd,kind,data=None):
        result=host.run(command,cwd=cwd,kind=kind,data=data)
        startup.require_execution(report["commands"][-1],0)
        return result
    try:
        report["compiler"]=run(["cc","--version"],cwd=out,kind="compiler-version").decode().splitlines()[0]
        api=source.production();profile=api.resource_profile("test-p4")
        baseline,production=startup.prepared(source,profile,True,mods["storage"],"prefix")
        owned,ownerproof=mods["process_owner"].transform(baseline,mods["publication"])
        if mods["process_owner"].restore(owned,ownerproof,mods["publication"])!=baseline:
            raise ValueError("owner full source inverse differs")
        report.update(resource=profile.to_record(16),production_proof=production,owner_proof=ownerproof)
        selected=json.loads(inputs["selection/build.json"])
        renames=selected["identifier_native_gate"]["accepted_renames"]
        aritybase,arityproof=mods["syscall_arity"].transform(owned,mods["process_owner"],mods["publication"],ownerproof,noinline_wake=True,immediate_exit=True)
        report["arity_proof"]=arityproof
        validbase,validproof=mods["valid_input"].transform(aritybase,mods["syscall_arity"],mods["process_owner"],mods["publication"],arityproof,mode="one-byte-valid")
        report["valid_proof"]=validproof
        structural,structural_proof=mods["search_compact"].transform(validbase,mods["valid_input"],mods["syscall_arity"],
            mods["process_owner"],mods["publication"],validproof,options=("previous-piece","unsigned-history"))
        report["structural_proof"]=structural_proof
        plans=(("control",False),("in-place-frontend",True))
        semantic_baseline=None;frontend_baseline=None
        cases,coverage=rules_tool.fixture_cases()
        for label,candidate in plans:
            options=("previous-piece","unsigned-history")
            immediate=True
            readable,proof=(structural,structural_proof) if not candidate else mods["frontend_compact"].transform(structural,
                mods["search_compact"],mods["valid_input"],mods["syscall_arity"],mods["process_owner"],mods["publication"],structural_proof)
            if candidate and mods["frontend_compact"].restore(readable,proof,mods["search_compact"],mods["valid_input"],
                    mods["syscall_arity"],mods["process_owner"],mods["publication"])!=structural:
                raise ValueError("frontend complete source inverse differs")
            directory=out/label;directory.mkdir();raw=directory/"generated-readable";raw.mkdir()
            for name,data in readable.items():(raw/name).write_bytes(data)
            semantic=[]
            instrumented,driver,semantic_proof=mods["probe_search_compact"].render(readable,source,mods["check_storage"],
                reference_board=validbase["board.c"],prefix=True,dense=False,variant_proof=proof,union_order="union-order" in options,
                previous_index="previous-piece" in options,constant_start="constant-start" in options,
                unsigned_history="unsigned-history" in options)
            for mode,extra in (("plain",[]),("ubsan",["-fsanitize=undefined","-fno-sanitize-recover=all"])):
                fixture=directory/("semantic-"+mode);fixture.mkdir()
                for name in ("tiny.h","board.c","search.c"):(fixture/name).write_bytes(instrumented[name])
                (fixture/"driver.c").write_bytes(driver);binary=fixture/"x"
                probe_flags=mods["probe_search_compact"].compiler_flags(prefix=True,dense=False,
                    previous_index="previous-piece" in options,unsigned_history="unsigned-history" in options,mode=mode)
                run(["cc",*probe_flags,
                    str(fixture/"driver.c"),"-o",str(binary)],cwd=fixture,kind=label+"-semantic-compile-"+mode)
                output=run([str(binary)],cwd=fixture,kind=label+"-semantic-run-"+mode)
                semantic_bytes,summary=mods["probe_search_compact"].verify_output(output)
                if semantic_baseline is None:semantic_baseline=semantic_bytes
                if semantic_bytes!=semantic_baseline:raise ValueError("actual structural search/order/learner observations differ: "+label)
                semantic.append(dict(mode=mode,output=pin(output),normalized=pin(semantic_bytes),summary=summary,binary=pin(binary.read_bytes())))
            frontend_results=[]
            for mode,extra in (("plain",[]),("ubsan",["-fsanitize=undefined","-fno-sanitize-recover=all"])):
                fixture=directory/("frontend-"+mode);fixture.mkdir();fixture_files=dict(readable)
                fixture_files["runtime.c"],clock_proof=source.project(readable["runtime.c"],[("fixture-only-constant-monotonic-clock",
                    b"uint64_t now(void){long t[2];if(Dsc2(228,(long)(1),(long)(t)))abort();return (uint64_t)t[0]*1000+(uint64_t)t[1]/1000000;}",
                    b"uint64_t now(void){return UINT64_C(1000000);}")])
                for name,data in fixture_files.items():(fixture/name).write_bytes(data)
                (fixture/"driver.c").write_bytes(FRONTEND_DRIVER);binary=fixture/"x"
                run(["cc","-std=c11","-O2","-g0","-fno-builtin","-ffunction-sections","-fdata-sections",
                    "-Wl,--gc-sections","-msse4.2","-mcx16","-DDEV=0","-DD_HQ=0","-DWORKERS=4","-DTT_BITS=12",
                    "-DFRONTEND_CSTRING="+str(int(candidate)),*extra,str(fixture/"driver.c"),"-o",str(binary)],
                    cwd=fixture,kind=label+"-frontend-compile-"+mode)
                output=run([str(binary)],cwd=fixture,kind=label+"-frontend-run-"+mode)
                lines=output.splitlines()
                if not lines or not lines[0].startswith(b"ABI ") or lines[-1]!=b"TOTAL commands=23 positions=18 promotions=16 clock_cases=64":
                    raise ValueError("actual frontend independent controls incomplete")
                frontend_bytes=b"\n".join(lines[1:])+b"\n"
                if frontend_baseline is None:frontend_baseline=frontend_bytes
                if frontend_bytes!=frontend_baseline:raise ValueError("actual frontend state/clock/ID observations differ")
                frontend_results.append(dict(mode=mode,output=pin(output),normalized=pin(frontend_bytes),clock_instrumentation=clock_proof,
                    driver=pin(FRONTEND_DRIVER),binary=pin(binary.read_bytes()),totals=lines[-1].decode(),equal=True))
            flags=builder.native_flags(profile);units=("main.c","start.S")
            cpp=run(["cc","-E","-P",*flags,"-I",str(raw),"-x","c","-"],cwd=raw,kind=label+"-preprocess",
                data=b''.join(('#include "'+n+'"\n').encode() for n in source.UNITS if n.endswith('.c')))
            walk_sites=len(re.findall(rb"\bwalk\s*\(",cpp))
            if walk_sites!=4:raise ValueError("unchanged scalar Board callgraph differs")
            entry=run(["cc","-E","-P","-x","assembler-with-cpp",str(raw/"start.S")],cwd=raw,kind=label+"-entry")
            emitted={"main.c":minifier.compact_source(cpp,"c"),"start.S":entry,"image.ld":readable["image.ld"]}
            words=set(lexical._ANY_WORD.findall(emitted["main.c"].decode()))
            if any(new in words for new in renames.values()):raise ValueError("legacy aliases capture fresh identifiers")
            mapped={"main.c":emitted["main.c"]}
            for old,new in renames.items():mapped=lexical._replace(mapped,old,new)
            emitted.update(mapped);gate_index=0
            def compile_gate(files,trial):
                nonlocal gate_index
                gate=directory/("gate-"+str(gate_index));gate_index+=1;gate.mkdir()
                for name,data in {**emitted,**files}.items():(gate/name).write_bytes(data)
                run(["cc",*flags,*[str(gate/n) for n in units],"-Wl,-T,"+str(gate/"image.ld"),"-o",str(gate/"linked")],cwd=gate,kind=label+"-source-gate-"+str(trial))
                return pin((gate/"linked").read_bytes())["sha256"]
            reduced,reduction=mods["reduce"].reduce_sources({"main.c":emitted["main.c"]},compile_gate,lexical,
                reserve=lexical._ANY_WORD.findall((entry+emitted["image.ld"]).decode()))
            emitted.update(reduced);shipping=directory/"shipping-inputs";shipping.mkdir()
            for name,data in emitted.items():(shipping/name).write_bytes(data)
            observations=[];images=[]
            for index in range(2):
                attempt=directory/("native-"+str(index));attempt.mkdir()
                run(["cc",*flags,*[str(shipping/n) for n in units],"-Wl,-T,"+str(shipping/"image.ld"),"-o",str(attempt/"linked")],cwd=attempt,kind=label+"-native-"+str(index))
                linked=(attempt/"linked").read_bytes();native=packer.strip_native(linked)
                (attempt/"native").write_bytes(native);images.append((linked,native))
                observations.append(dict(linked=pin(linked),stripped=pin(native),
                    linked_geometry=builder.kernel_geometry(packer,linked,profile.workers),
                    native_geometry=builder.kernel_geometry(packer,native,profile.workers)))
            if images[0]!=images[1] or observations[0]["linked"]["sha256"]!=reduction["final_native_sha256"]:
                raise ValueError("actual native double reproduction/source gate differs")
            identity={k:observations[0][k] for k in EXPECTED}
            if not candidate and identity!=EXPECTED:raise ValueError("current structural control native differs")
            board_cpp=run(["cc","-E","-P",*flags,str(raw/"board.c")],cwd=raw,kind=label+"-actual-board-preprocess")
            actual_board,binding,declarations=shipping_board(board_cpp,emitted,renames,reduction,minifier,lexical)
            rule_fixture=rules_tool.render_bound_fixture(actual_board,binding,cases,declarations)
            rule_results=[]
            for mode,extra in (("plain",[]),("ubsan",["-fsanitize=undefined","-fno-sanitize-recover=all"])):
                rules_dir=directory/("rules-"+mode);rules_dir.mkdir();(rules_dir/"fixture.c").write_bytes(rule_fixture)
                binary=rules_dir/"x"
                run(["cc","-std=c11","-O1","-g0","-fno-builtin","-msse4.2","-mcx16",*extra,
                    str(rules_dir/"fixture.c"),"-o",str(binary)],cwd=rules_dir,kind=label+"-rules-compile-"+mode)
                observed=run([str(binary)],cwd=rules_dir,kind=label+"-rules-run-"+mode)
                rule_results.append(dict(mode=mode,binary=pin(binary.read_bytes()),**rules_tool._compare_output(observed,cases)))
            packages=[]
            for codec in ("alone","xz","xz-bcj"):
                whole,detail=mods["packaging"].package_native(images[0][1],codec)
                repeated,_=mods["packaging"].package_native(images[0][1],codec)
                if whole!=repeated:raise ValueError("whole repeat differs")
                path=directory/("packed-"+codec);path.write_bytes(whole);path.chmod(0o700)
                packages.append(dict(route="packed-"+codec,whole=pin(whole),detail=detail,reproduced=True))
                if not candidate and codec=="xz-bcj" and len(whole)!=5261:raise ValueError("control whole cost differs")
            whole,detail=mods["compressed_bootstrap"].package_source(emitted,flags,units,mods["packaging"])
            repeated,_=mods["compressed_bootstrap"].package_source(emitted,flags,units,mods["packaging"])
            if whole!=repeated:raise ValueError("compressed source double reproduction differs")
            (directory/"source-jit-compressed").write_bytes(whole)
            packages.append(dict(route="source-jit-compressed",whole=pin(whole),detail=detail,reproduced=True))
            report["variants"].append(dict(name=label,source={n:pin(d) for n,d in readable.items()},proof=proof,
                flags=flags,units=list(units),shipping={n:pin(d) for n,d in emitted.items()},
                legacy_renames=renames,reduction=reduction,native=observations,packages=packages,
                last_search_output_required=False,input_domain="TCEC-valid-lines",options=list(options),
                semantic_proof=semantic_proof,semantic=semantic,semantic_equal=True,
                frontend_semantics=frontend_results,
                rules=dict(preprocessed=pin(board_cpp),shipping_board_prefix=pin(actual_board),fixture=pin(rule_fixture),
                    binding=binding,coverage=coverage,modes=rule_results,actual_shipping_prefix=True),
                scalar_walk_sites=walk_sites))
            cost=next(x["whole"]["bytes"] for x in packages if x["route"]=="packed-xz-bcj")
            if candidate:report["whole_improved"]=cost<5261
            save()
            small=api.ResourceProfile(label,"test",4,16<<12)
            smallflags=builder.native_flags(small)
            for mode in ("valid","quit","eof"):
                fixture=directory/("fixture-"+mode);fixture.mkdir();testfiles=dict(readable);instrumentation=None
                if mode!="valid":testfiles,instrumentation=mods["test_process_owner"].active_instrument(testfiles,source,mods["process_owner"])
                for name,data in testfiles.items():(fixture/name).write_bytes(data)
                binary=fixture/"x"
                run(["cc",*smallflags,*[str(fixture/n) for n in source.UNITS],"-Wl,-T,"+str(fixture/"image.ld"),"-o",str(binary)],cwd=fixture,kind=label+"-fixture-compile-"+mode)
                driver=fixture/"dialogue.py";driver.write_text(DIALOGUE);receipt=fixture/"dialogue.json"
                run([sys.executable,"-I","-B",str(driver),str(binary),str(receipt),mode,str(int(immediate))],cwd=fixture,kind=label+"-fixture-run-"+mode)
                dialogue=json.loads(receipt.read_text())
                if not dialogue.get("complete") or not dialogue.get("engine_reaped") or dialogue.get("forced_cleanup") or dialogue.get("returncode")!=0:
                    raise ValueError("finite actual-runtime contract failed")
                report["runtime_cases"].append(dict(name=label+"-"+mode,mode=mode,workers=4,tt_bits=12,
                    source_before={n:pin(d) for n,d in readable.items()},instrumentation=instrumentation,
                    binary=pin(binary.read_bytes()),dialogue=dialogue,last_search_output_required=not immediate))
                save()
        if len(report["runtime_cases"])!=3*len(plans):raise ValueError("finite runtime matrix incomplete")
        for row in report["commands"]:startup.require_execution(row,0)
        report["source_current_after"]={name:pin(normalized(origin/name)) for name in inputs if name.startswith("engines/")}
        if any(report["source_current_after"][name]!=pin(data) for name,data in inputs.items() if name.startswith("engines/")):
            raise ValueError("frozen/current producer changed during experiment")
        report["complete"]=True
    except BaseException as error:
        report["complete"]=False;report["failure"]=dict(type=type(error).__name__,message=str(error));raise
    finally:
        try:host.close()
        except BaseException as error:
            report["complete"]=False;report["cleanup_failure"]=dict(type=type(error).__name__,message=str(error));raise
        finally:
            cleanup=report.get("host_cleanup",{})
            if cleanup.get("errors") or cleanup.get("unsettled_commands"):report["complete"]=False
            save()
    print(json.dumps(dict(complete=report["complete"],variants=len(report["variants"]),runtime_cases=len(report["runtime_cases"]),selected=False)),flush=True)


if __name__=="__main__":main()
