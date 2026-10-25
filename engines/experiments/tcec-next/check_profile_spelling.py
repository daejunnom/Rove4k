#!/usr/bin/env python3
"""Finite unselected one-factor costs from newly regenerated full sources.

No source/default/expectation is changed. Every cost includes the current
unchanged five-line wrapper and fixed source recipe. Both native compilations
and both codec productions are independent. Focused C consumers never invoke
shipping main or allocate its TT; full P4 runtime is a separate leased step.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import lzma
import os
from pathlib import Path
import platform
import resource
import signal
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PREFIX="engines/experiments/tcec-next/"
SELF=PREFIX+"check_profile_spelling.py"
HELPER=PREFIX+"profile_spelling.py"
PROFILES=("test-p4","test-p28","tcec-provisional")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module);return module

def normalized(path):
    data=path.read_bytes().replace(b"\r\n",b"\n")
    require(b"\r" not in data,"lone CR in named source")
    return data

def require(value,message):
    if not value:raise ValueError(message)

def consumer_fixture(source,family,variant,spelling):
    """Actual changed learner/formatter; shipping entry and TT never called."""
    c=spelling.CONTEXT[family]
    formatter={"A":"o","B":"T","C":"o","E":"o","F":"j"}[family]
    learn=c["learn"]
    positive=""
    if variant=="positive-history":
        positive=f"""
 for(unsigned d=1;d<=126;d++)for(unsigned before=0;before<=16384;before++){{
  uint16_t value=before;{learn}(&value,d*d);
  unsigned expected=before+d*d-before*d*d/16384;
  if(value!=expected||value>16384)return 10;
 }}
 uint16_t persistent=0;unsigned reference=0;
 for(unsigned n=0;n<100000;n++){{unsigned d=n%126+1;{learn}(&persistent,d*d);
  reference+=d*d-reference*d*d/16384;if(persistent!=reference)return 11;}}
"""
    driver=f"""
#undef main
int main(void){{
 {positive}
 for(unsigned f=0;f<128;f++)if(!(f&136))
 for(unsigned t=0;t<128;t++)if(!(t&136))
 for(unsigned p=0;p<=5;p++)if(p!=1){{
  unsigned m=f|(t<<7)|(p<<14);char got[6],expected[6];
  {formatter}(m,got);
  if(!m){{if(strcmp(got,"0000"))return 12;continue;}}
  expected[0]='a'+(f&7);expected[1]='1'+(f>>4);
  expected[2]='a'+(t&7);expected[3]='1'+(t>>4);
  expected[4]=p?"xxnbrq"[p]:0;expected[5]=0;
  if(strcmp(got,expected))return 13;
 }}
 puts("consumer-ok");return 0;
}}
"""
    return b"#define main rv_spelling_unused_main\n"+source+driver.encode()

def smoke_costs(costs,out):
    """Leased functional JIT only; no strength, placement or target-11 claim."""
    report_raw=(costs/"results.json").read_bytes();old=json.loads(report_raw)
    require(old.get("class")=="rove4k-spelling-experiment-v1" and old.get("complete") is True
        and old.get("inputs_rechecked") is True and "failure" not in old
        and old.get("host_cleanup")==dict(unsettled_commands=0,errors=[])
        and all(r.get("returncode")==0 and r.get("terminal") and r.get("reaped")
            and r.get("owned_group_absent") and not r.get("forced_cleanup") for r in old["commands"]),
        "completed exact finite cost cohort required")
    family=old["family"];require(family in "ABCEF","named full family required")
    frozen=costs/"inputs"
    trusted=(HELPER,PREFIX+"profile_source.py",PREFIX+"profile_phase.py",PREFIX+"profile_b.py",
        PREFIX+"wrapper.py",PREFIX+"self_unlink.py",PREFIX+"profile_rules.py",
        "engines/scripts/source_package.py","engines/scripts/production.py",
        "engines/experiments/tcec-scope/build.py")
    if family=="E":trusted+=("engines/model/e19.py","engines/model/e19.json")
    # Check against trusted current named code before importing any archived
    # Python. Old report pins alone cannot authorize executable helper bytes.
    require(all(normalized(frozen/name)==normalized(ROOT/name) for name in trusted),
        "frozen experimental producer/support code is no longer current")
    helper=load("spelling_smoke_transform",frozen/HELPER)
    package=load("spelling_smoke_package",frozen/"engines/scripts/source_package.py")
    wrapper=load("spelling_smoke_wrapper",frozen/(PREFIX+"wrapper.py"))
    unlink=load("spelling_smoke_unlink",frozen/(PREFIX+"self_unlink.py"))
    owner=load("spelling_smoke_owner",frozen/"engines/experiments/tcec-scope/build.py")
    runtime_path=ROOT/"engines/compact/tiny-entry-d/verify.py"
    runtime_raw=normalized(runtime_path)
    executing=normalized(Path(__file__))
    runtime=load("spelling_smoke_runtime",runtime_path)
    rules=load("spelling_smoke_rules",frozen/(PREFIX+"profile_rules.py"))
    projection=load("spelling_smoke_resource",frozen/(PREFIX+"profile_source.py"))
    production=load("spelling_smoke_production",frozen/"engines/scripts/production.py")
    phase=load("spelling_smoke_phase",frozen/(PREFIX+"profile_phase.py"))
    b=load("spelling_smoke_b",frozen/(PREFIX+"profile_b.py"))
    # Read only the finite source/proof names this producer recorded, never an
    # arbitrary extra role/path supplied by the caller's metadata.
    for name in trusted:
        require(owner.pin(normalized(frozen/name))==old["inputs"][name],"frozen named smoke input differs")
    fresh=costs/"fresh-selected";manifest_raw=(fresh/"build.json").read_bytes()
    require(owner.pin(manifest_raw)==old["fresh_selected"]["report"],"fresh factory receipt differs")
    manifest=json.loads(manifest_raw)
    require(manifest["complete"] and manifest["reproducible"] and manifest["resources"]["id"]=="test-p4"
        and manifest["resources"]["workers"]==4 and manifest["host_cleanup"]==dict(unsettled_commands=0,errors=[]),
        "fresh full TEST-P4 source factory required")
    base=(fresh/"control/main.c").read_bytes()
    source,proof=projection.transform_source(base,family=family,profile=production.resource_profile("test-p4"))
    chain=[proof];parent=source
    if family=="B":
        source,proof=b.transform_source(source,profile_id="test-p4",variant="tcec-final-lf")
        require(b.restore_source(source,proof)==parent,"B smoke inverse differs")
    else:
        source,proof=phase.transform_source(source,family=family,profile_id="test-p4",variant="phase-init")
        require(phase.restore_source(source,proof)==parent,"phase smoke inverse differs")
    chain.append(proof)
    if family=="E":
        e19=load("spelling_smoke_e19",frozen/"engines/model/e19.py")
        for name in ("engines/model/e19.py","engines/model/e19.json"):
            require(owner.pin(normalized(frozen/name))==old["inputs"][name],"frozen E19 smoke input differs")
        model=e19.Model.load(frozen/"engines/model/e19.json")
        source_model=e19.Model.from_physical_source(source,model_id="e19-admitted-source-baseline")
        source,proof=model.bind_physical_table(source,source_model=source_model);chain.append(proof)
    require(source==(fresh/"main.c").read_bytes() and chain==manifest["source_proofs"],
        "complete fresh selected source chain does not replay")
    parent=source
    rows=[r for r in old["measurements"] if r["profile"]=="test-p4" and r["variant"] in old["cost_winners"]]
    require(rows,"at least one measured whole-cost winner required")
    out.mkdir();tmp=out/"tmp";tmp.mkdir()
    support=out/"support";support.mkdir();(support/"runtime.py").write_bytes(runtime_raw)
    (support/"check_profile_spelling.py").write_bytes(executing)
    report=dict(format=1,**{"class":"rove4k-spelling-functional-smoke-v1"},family=family,
        complete=False,source_cost_report=dict(path=str(costs/"results.json"),**owner.pin(report_raw)),
        runtime_support=owner.pin(runtime_raw),executing_checker=owner.pin(executing),
        sessions=[],resources=manifest["resources"],
        interrupted_constructor_cleanup=[],cleanup_errors=[],
        actual_workers=4,cpu_affinity=sorted(os.sched_getaffinity(0)),
        physical_placement_qualified=False,strength_measured=False,target11_runtime=False,
        production_adopted=False,scope="actual source-JIT private image, mandatory/optional protocol, two legal GO, joined position reuse")
    def save():(out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    save();old_tmp=os.environ.get("TMPDIR");os.environ["TMPDIR"]=str(tmp)
    resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30))
    prior_term=signal.signal(signal.SIGTERM,runtime.terminated)
    try:
        for row in rows:
            variant=row["variant"];source,proof=helper.transform_source(parent,family=family,
                profile_id="test-p4",variant=variant)
            require(helper.restore_source(source,proof)==parent,"spelling smoke inverse differs")
            chain_actual=chain+[proof]
            first,repeat=row["attempts"]
            require({k:v for k,v in first.items() if k!="path"}==
                {k:v for k,v in repeat.items() if k!="path"},"cost attempt records differ")
            for attempt in (first,repeat):
                directory=Path(attempt["path"])
                require(directory.is_relative_to(costs/"costs") and
                    (directory/"main.c").read_bytes()==source and owner.pin(source)==attempt["source"]
                    and json.loads((directory/"source-proof.json").read_bytes())==chain_actual,
                    "named repeated candidate source/proofs differ")
                for path,key in (("native/x","native"),("x","whole"),("header.sh","header"),("payload.lzma","payload")):
                    require(owner.pin((directory/path).read_bytes())==attempt[key],"repeated candidate artifact differs")
            whole=wrapper.package(package,unlink,source,old["compression"],old["compiler"])
            require(owner.pin(whole)==row["whole"],"replayed exact whole candidate differs")
            session_dir=out/variant;session_dir.mkdir();program=session_dir/"candidate"
            program.write_bytes(whole);program.chmod(0o700)
            original=owner.pin(program.read_bytes());owned=None
            observed=dict(variant=variant,source=owner.pin(source),whole=original,native=row["native"],complete=False)
            report["sessions"].append(observed);save()
            try:
                owned=runtime.Owned(program,session_dir/"runtime",runtime.Budget(40))
                owned.send(b"uci\nisready\n");owned.wait_line(b"uciok");owned.wait_line(b"readyok")
                pid=owned.process.pid
                native=Path(f"/proc/{pid}/exe").read_bytes()
                require(owner.pin(native)==row["native"],"actual source-JIT native image differs")
                require("(deleted)" in os.readlink(f"/proc/{pid}/exe"),"engine's own private native path was not removed")
                require(list(tmp.iterdir())==[],"private JIT output remains after entry unlink")
                tids=list(Path(f"/proc/{pid}/task").iterdir())
                require(len(tids)==1,"startup initializers did not all join before readiness")
                observed.update(actual_jit_native=owner.pin(native),entry_private_path_unlinked=True,
                    startup_tids=1)
                oracle=rules.oracle_module();moves=[]
                active=[]
                for count,(position,clock) in enumerate(((b"e2e4",b"wtime 3 btime 3000 winc 2 binc 0"),
                    (b"d2d4 d7d5",b"wtime 3000 btime 3 winc 0 binc 2")),1):
                    board=oracle.Board.from_fen()
                    for move in position.decode().split():board=board.play(move)
                    legal={str(move) for move in board.legal_moves()}
                    owned.send(b"position startpos moves "+position+b"\n")
                    owned.send(b"ucinewgame\nsetoption name Threads value 99\nstop\nponderhit\ndebug off\nregister later\nisready\n")
                    owned.wait_line(b"readyok",count*2)
                    require(sum(x.startswith(b"bestmove ") for x in owned.stdout.bytes().splitlines())==count-1,
                        "optional command triggered a false GO")
                    owned.send(b"go "+clock+b"\n")
                    deadline=time.monotonic()+owned.budget.left(3)
                    while time.monotonic()<deadline:
                        seen=len(list(Path(f"/proc/{pid}/task").iterdir()))
                        if seen==5:break
                        time.sleep(.001)
                    require(seen==5,"four actual GO workers were not observed")
                    active.append(seen);owned.wait_best(count)
                    values=[x[9:].decode() for x in owned.stdout.bytes().splitlines() if x.startswith(b"bestmove ")]
                    require(len(values)==count and values[-1] in legal,"duplicate/illegal result or optional command mutated position")
                    moves.append(values[-1])
                    owned.send(b"position startpos\nisready\n");owned.wait_line(b"readyok",count*2+1)
                    require(len(list(Path(f"/proc/{pid}/task").iterdir()))==1,
                        "position readiness preceded physical GO joins")
                owned.send(b"quit\n");physical=owned.finish();cleanup=owned.cleanup()
                require(not cleanup["forced_cleanup"] and not cleanup["errors"] and cleanup["owned_group_absent"],
                    "experimental runtime did not settle normally")
                require(sum(x.startswith(b"bestmove ") for x in owned.stdout.bytes().splitlines())==2,
                    "late duplicate result after final physical join")
                require(owner.pin(program.read_bytes())==original and list(tmp.iterdir())==[],
                    "source package changed or private JIT file remains")
                observed.update(complete=True,legal_moves=moves,GO_count=2,active_tids=active,final_position_join=True,
                    commands_optional_ignored=True,
                    physical=physical,cleanup=cleanup,stdout=owner.pin(owned.stdout.bytes()))
                save()
            finally:
                if owned is not None:
                    observed["cleanup"]=owned.cleanup();save()
        require(normalized(runtime_path)==runtime_raw and normalized(Path(__file__))==executing
            and (costs/"results.json").read_bytes()==report_raw,
            "runtime helper or original source-cost evidence changed")
        require(all(normalized(frozen/name)==normalized(ROOT/name) for name in trusted),
            "trusted experimental helper changed during actual runtime")
        report["complete"]=True;save()
    except BaseException as error:
        report["failure"]=dict(type=type(error).__name__,message=str(error));save();raise
    finally:
        inherited=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM})
        try:
            for interrupted in list(runtime.OWNED):
                report["complete"]=False
                try:report["interrupted_constructor_cleanup"].append(interrupted.cleanup())
                except BaseException as error:
                    report["cleanup_errors"].append(dict(type=type(error).__name__,message=str(error)))
            if old_tmp is None:os.environ.pop("TMPDIR",None)
            else:os.environ["TMPDIR"]=old_tmp
            save()
        finally:
            signal.signal(signal.SIGTERM,prior_term)
            signal.pthread_sigmask(signal.SIG_SETMASK,inherited)
    require(report["complete"] and not report["cleanup_errors"] and not runtime.OWNED,
        "experimental runtime owner did not close cleanly")
    print(json.dumps(dict(family=family,complete=True,sessions=len(report["sessions"]),actual_workers=4)))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--entry",choices=tuple("ABCEF"))
    mode.add_argument("--smoke-costs",type=Path,help="leased actual P4 JIT for this completed finite cohort's winners")
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    require(sys.platform=="linux" and platform.machine()=="x86_64" and args.out.is_absolute()
        and not out.exists() and ROOT not in (out,*out.parents)
        and not any((p/".git").exists() for p in (out,*out.parents)),
        "new absolute external Linux x86-64 output required")
    if args.smoke_costs is not None:
        require(args.smoke_costs.is_absolute() and args.smoke_costs.is_dir(),"existing absolute finite cost cohort required")
        smoke_costs(args.smoke_costs.resolve(),out);return
    names=[SELF,HELPER,PREFIX+"profile_build.py",PREFIX+"profile_source.py",
        PREFIX+"profile_phase.py",PREFIX+"profile_b.py",PREFIX+"wrapper.py",
        PREFIX+"self_unlink.py",PREFIX+"profile_rules.py","engines/scripts/production.py",
        "engines/scripts/source_package.py","engines/experiments/tcec-scope/build.py",
        "engines/tests/chess_oracle.py"]
    if args.entry=="E":names += ["engines/model/e19.py","engines/model/e19.json"]
    observed={name:normalized(ROOT/name) for name in names}
    owner=load("spelling_owner",ROOT/"engines/experiments/tcec-scope/build.py")
    out.mkdir();report=dict(format=1,**{"class":"rove4k-spelling-experiment-v1"},
        family=args.entry,complete=False,commands=[],measurements=[],consumers=[],rules=[],
        one_factor_candidates=8,production_adopted=False,runtime_qualified=False,
        large_tt_executed=False,shipping_entry_called=False,compressor_sweep=False,
        recipe_policy="unchanged selected source13 compression and W1/W2 wrapper",
        scope="fresh canonical production followed by exact unselected one-factor source projection")
    def save():(out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    save()
    owner.LIMITS.update(aggregate_wall=1800,per_command_wall=600,parent_AS=4<<30,
        parent_CPU=600,parent_CPU_hard=720,child_AS=4<<30,child_CPU=480)
    previous=signal.signal(signal.SIGCHLD,signal.SIG_DFL)
    class Host(owner.Host):
        def settle(self,child,row,force=False):
            if row.get("kind")=="fresh-selected-production":row["cooperative_termination_seconds"]=30
            return super().settle(child,row,force)
    host=Host(out,report,save)
    try:
        fresh=out/"fresh-selected"
        option=["--b-variant","tcec-final-lf"] if args.entry=="B" else ["--phase-variant","phase-init"]
        host.run([sys.executable,"-I","-B",ROOT/(PREFIX+"profile_build.py"),"--entry",args.entry,
            "--profile","test-p4",*option,"--out",fresh],cwd=out,kind="fresh-selected-production")
        raw=(fresh/"build.json").read_bytes();manifest=json.loads(raw)
        require(manifest["complete"] and manifest["reproducible"] and
            manifest["host_cleanup"]==dict(unsettled_commands=0,errors=[]),"fresh selected production incomplete")
        report["fresh_selected"]=dict(path=str(fresh),report=owner.pin(raw),
            source_closure=manifest["source_closure"],control_source_closure=manifest["control_source_closure"],
            source=owner.pin((fresh/"main.c").read_bytes()),source_proofs=manifest["source_proofs"])
        for name,data in observed.items():
            require(normalized(ROOT/name)==data,"named experiment input changed during factory: "+name)
            target=out/"inputs"/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        report["inputs"]={name:owner.pin(data) for name,data in observed.items()}
        frozen=out/"inputs"
        spelling=load("spelling_transform",frozen/HELPER)
        projection=load("spelling_resource",frozen/(PREFIX+"profile_source.py"))
        phase=load("spelling_phase",frozen/(PREFIX+"profile_phase.py"))
        b=load("spelling_B",frozen/(PREFIX+"profile_b.py"))
        production=load("spelling_contracts",frozen/"engines/scripts/production.py")
        packaging=load("spelling_package",frozen/"engines/scripts/source_package.py")
        unlink=load("spelling_unlink",frozen/(PREFIX+"self_unlink.py"))
        wrapper=load("spelling_wrapper",frozen/(PREFIX+"wrapper.py"))
        rules=load("spelling_rules",frozen/(PREFIX+"profile_rules.py"))
        model=None
        if args.entry=="E":
            e19=load("spelling_e19",frozen/"engines/model/e19.py")
            model=e19.Model.load(frozen/"engines/model/e19.json")
        compiler=manifest["compiler"];compression=manifest["compression"]
        require(manifest["compile_executor"]==compiler,"unchanged selected source compiler required")
        report.update(compiler=compiler,compression=compression,
            compiler_version=manifest["compile_executor_version"],wrapper_contract=manifest["wrapper_contract"])
        base=(fresh/"control/main.c").read_bytes()
        require((len(base),owner.sha(base))==projection.INPUTS[args.entry],"fresh maintained baseline pin differs")
        def selected(profile_id):
            profile=production.resource_profile(profile_id)
            source,proof=projection.transform_source(base,family=args.entry,profile=profile)
            require(projection.restore_source(source,proof)==base,"resource inverse differs")
            chain=[proof];parent=source
            if args.entry=="B":
                source,proof=b.transform_source(source,profile_id=profile_id,variant="tcec-final-lf")
                require(b.restore_source(source,proof)==parent,"B inverse differs")
            else:
                source,proof=phase.transform_source(source,family=args.entry,profile_id=profile_id,variant="phase-init")
                require(phase.restore_source(source,proof)==parent,"phase inverse differs")
            chain.append(proof)
            if model is not None:
                source_model=e19.Model.from_physical_source(source,model_id="e19-admitted-source-baseline")
                source,proof=model.bind_physical_table(source,source_model=source_model);chain.append(proof)
            require(spelling.INPUTS[(args.entry,profile_id)]==(len(source),owner.sha(source)),
                "fresh selected source differs from named spelling domain")
            if profile_id=="test-p4":
                require(source==(fresh/"main.c").read_bytes() and chain==manifest["source_proofs"],
                    "fresh factory source and complete reconstructed selected chain differ")
            return source,chain
        owner.LIMITS.update(child_AS=2<<30,child_CPU=120,per_command_wall=120)
        variants=("control",*spelling.available(args.entry));sources={}
        report["applicable_variants"]=list(variants)
        report["unapplied_variants"]=[v for v in spelling.VARIANTS if v not in variants]
        for profile_id in PROFILES:
            for variant in variants:
                attempts=[]
                for attempt in ("first","repeat"):
                    source,chain=selected(profile_id);parent=source
                    if variant!="control":
                        source,proof=spelling.transform_source(source,family=args.entry,
                            profile_id=profile_id,variant=variant)
                        require(spelling.restore_source(source,proof)==parent,"spelling inverse differs")
                        chain.append(proof)
                    directory=out/"costs"/profile_id/variant/attempt
                    native_dir=directory/"native";native_dir.mkdir(parents=True)
                    (directory/"main.c").write_bytes(source)
                    proof_raw=(json.dumps(chain,indent=2)+"\n").encode()
                    (directory/"source-proof.json").write_bytes(proof_raw)
                    host.run(compiler,cwd=native_dir,kind=f"{profile_id}-{variant}-{attempt}",data=source)
                    native=(native_dir/"x").read_bytes()
                    header=wrapper.header(packaging,unlink,compiler)
                    whole=wrapper.package(packaging,unlink,source,compression,compiler)
                    require(whole.startswith(header),"whole wrapper differs")
                    payload=whole[len(header):];decoder=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                    require(decoder.decompress(payload,max_length=len(source)+1)==source and
                        decoder.eof and not decoder.unused_data,"strict whole restoration differs")
                    for name,data in (("x",whole),("header.sh",header),("payload.lzma",payload)):
                        (directory/name).write_bytes(data)
                    (directory/"x").chmod(0o700)
                    pins={kind:owner.pin(data) for kind,data in (("source",source),("native",native),
                        ("whole",whole),("header",header),("payload",payload),("proof",proof_raw))}
                    attempts.append(dict(path=str(directory),**pins))
                    if attempt=="first":sources[(profile_id,variant)]=source
                require({k:v for k,v in attempts[0].items() if k!="path"}==
                    {k:v for k,v in attempts[1].items() if k!="path"},"independent generation/reproduction differs")
                row=dict(profile=profile_id,variant=variant,attempts=attempts,reproducible=True,**pins)
                if variant=="control":control=row
                row["delta_vs_selected"]={kind:row[kind]["bytes"]-control[kind]["bytes"]
                    for kind in ("source","native","whole")}
                report["measurements"].append(row);save()
        winners={min((r for r in report["measurements"] if r["profile"]==profile),
            key=lambda r:(r["whole"]["bytes"],r["source"]["bytes"]))["variant"] for profile in PROFILES}
        winners.discard("control");report["cost_winners"]=sorted(winners)
        gainers={r["variant"] for r in report["measurements"] if r["delta_vs_selected"]["whole"]<0}
        report["focused_candidates"]=sorted(gainers)
        cases,coverage=rules.fixture_cases()
        for variant in sorted(gainers):
            source=sources[("test-p4",variant)]
            directory=out/"focused"/variant;directory.mkdir(parents=True)
            fixture=consumer_fixture(source,args.entry,variant,spelling)
            (directory/"consumer.c").write_bytes(fixture)
            modes=[]
            for mode,flags in (("plain",[]),("ubsan",["-fsanitize=undefined","-fno-sanitize-recover=all"])):
                command=[x for x in compiler if x!="-s"]+flags
                host.run(command,cwd=directory,kind=variant+"-consumer-compile-"+mode,data=fixture)
                output=host.run([directory/"x"],cwd=directory,kind=variant+"-consumer-execute-"+mode)
                require(output==b"consumer-ok\n","actual formatter/learner consumer differs")
                modes.append(dict(mode=mode,native=owner.pin((directory/"x").read_bytes()),output=owner.pin(output)))
            report["consumers"].append(dict(variant=variant,source=owner.pin(source),fixture=owner.pin(fixture),
                modes=modes,coordinates_checked=64*64*5,shipping_entry_called=False,TT_allocated=False,
                positive_learner_exhaustive=variant=="positive-history"));save()
            fixture=rules.render_fixture(source,args.entry,cases)
            (directory/"rules.c").write_bytes(fixture);modes=[]
            for mode,flags in (("plain",[]),("ubsan",["-fsanitize=undefined","-fno-sanitize-recover=all"])):
                command=[x for x in compiler if x!="-s"]+flags
                host.run(command,cwd=directory,kind=variant+"-rules-compile-"+mode,data=fixture)
                output=host.run([directory/"x"],cwd=directory,kind=variant+"-rules-execute-"+mode)
                modes.append(dict(mode=mode,native=owner.pin((directory/"x").read_bytes()),
                    **rules._compare_output(output,cases)))
            report["rules"].append(dict(variant=variant,source=owner.pin(source),fixture=owner.pin(fixture),
                coverage=coverage,modes=modes,shipping_entry_called=False,TT_allocated=False));save()
        require(all(normalized(ROOT/name)==data for name,data in observed.items()),
            "named experiment inputs changed before closure")
        report["inputs_rechecked"]=True
    except BaseException as error:
        report["failure"]=dict(type=type(error).__name__,message=str(error));save();raise
    finally:
        try:host.close()
        finally:signal.signal(signal.SIGCHLD,previous)
    report["complete"]=True;save()
    print(json.dumps(dict(family=args.entry,complete=True,winners=report["cost_winners"],
        costs=[dict(profile=r["profile"],variant=r["variant"],source=r["source"]["bytes"],
            native=r["native"]["bytes"],whole=r["whole"]["bytes"],delta=r["delta_vs_selected"])
            for r in report["measurements"]],commands=len(report["commands"]))))

if __name__=="__main__":main()
