#!/usr/bin/env python3
"""Experimental own-exit_group D class: frozen source/cost, then small-TT tests.

This never wires the baseline builder, admits a new image through an old hash
guard, or allocates TT34. All generated sources and test-only edits are named.
Natural group termination is required; external TERM/KILL is never a pass.
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
NATIVE = ("tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld")
EXPECTED = dict(linked=dict(bytes=7792,sha256="e5d54f2f9b918316efcb171631cf4745bf97f7dfacfb55faff6a5ee9aa71128f"),
                stripped=dict(bytes=7440,sha256="e06bce0d9998fa14cb85f135d3c5f54f9972d3dea533cede1f44ed28618e3337"))


def pin(data):
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def normalized(path):
    data = Path(path).read_bytes().replace(b"\r\n",b"\n")
    if b"\r" in data:
        raise ValueError("lone CR in named process-owner input")
    return data


def load(name,path):
    spec = importlib.util.spec_from_file_location(name,path); module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module; spec.loader.exec_module(module); return module


ACTIVE = r'''import json,os,select,subprocess,sys,time
from pathlib import Path
path=Path(sys.argv[2]);mode=sys.argv[3];negative=len(sys.argv)>4
record=dict(complete=False,mode=mode,negative=negative,events=[],engine_started=False,engine_reaped=False,forced_cleanup=False)
def save():path.write_text(json.dumps(record,indent=2)+"\n")
def emit(data):
 while data:data=data[os.write(1,data):]
def send(data):
 child.stdin.write(data);child.stdin.flush();record["events"].append(dict(send=data.decode()));save()
buffer=b"";deadline=time.monotonic()+20;child=None
def until(predicate):
 global buffer
 while True:
  if b"\n" in buffer:
   line,buffer=buffer.split(b"\n",1);line+=b"\n";emit(line)
   record["events"].append(dict(receive=line.decode()));save()
   if predicate(line):return line
   continue
  left=deadline-time.monotonic()
  if left<=0:raise TimeoutError("active owner bounded dialogue")
  if select.select([child.stdout],[],[],min(left,.25))[0]:
   data=os.read(child.stdout.fileno(),4096)
   if not data:raise EOFError("natural EOF before required output")
   buffer+=data
   if len(buffer)>65536:raise ValueError("active owner output bound")
exit_status=0
try:
 save();child=subprocess.Popen([sys.argv[1]],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=None,bufsize=0)
 record.update(engine_started=True,pid=child.pid,pgid=os.getpgid(child.pid),owner_pgid=os.getpgrp(),inherits_owner_group=os.getpgid(child.pid)==os.getpgrp());save()
 if not record["inherits_owner_group"]:raise ValueError("engine escaped owner group")
 send(b"uci\n");until(lambda s:s==b"uciok\n")
 send(b"position startpos\ngo wtime 3600000 btime 3600000\n")
 until(lambda s:s==b"TEST_OWNER_SEARCH_ENTERED\n")
 if mode=="quit":send(b"quit\n")
 elif mode!="eof":raise ValueError("finite interruption mode required")
 child.stdin.close();child.stdin=None;record["interrupted_after_real_claim"]=True;save()
 try:
  until(lambda s:s==b"TEST_OWNER_ACTIVE_PENDING\n")
  best=until(lambda s:s.startswith(b"bestmove "));record["bestmove"]=best.decode().strip()
  legal={f"{f}2{f}{r}" for f in "abcdefgh" for r in "34"}|{"b1a3","b1c3","g1f3","g1h3"}
  if best[9:].decode().strip() not in legal:raise ValueError("illegal root bestmove")
  if negative:raise ValueError("dropped wait negative unexpectedly completed")
 except EOFError:
  if not negative:raise
  code=child.wait(timeout=5);record.update(engine_reaped=True,returncode=code)
  received=[e["receive"] for e in record["events"] if "receive" in e]
  if code or any(s=="TEST_OWNER_ACTIVE_PENDING\n" or s.startswith("bestmove ") for s in received):raise ValueError("invalid dropped wait negative")
  record["negative_detected"]=True;exit_status=13
 if not record["engine_reaped"]:
  code=child.wait(timeout=5);record.update(engine_reaped=True,returncode=code)
  if code:raise ValueError("engine did not exit naturally with zero")
 trailing=buffer+child.stdout.read()
 if trailing:emit(trailing);raise ValueError("unexpected trailing active-owner output")
 record["complete"]=True
except BaseException as error:
 record["failure"]=dict(type=type(error).__name__,message=str(error));raise
finally:
 if child is not None:
  if child.poll() is None:
   record["forced_cleanup"]=True;child.terminate()
   try:child.wait(timeout=2)
   except subprocess.TimeoutExpired:child.kill();child.wait(timeout=2)
  record.update(engine_reaped=child.returncode is not None,returncode=child.returncode)
 save()
sys.exit(exit_status)
'''


def active_instrument(files,source,owner,*,drop_wait=False):
    result = dict(files); proofs = {}
    result["tiny.h"],proofs["tiny.h"] = source.project(result["tiny.h"],[("test-claim-prototype",
        b"void think(Worker *,const Board *);",b"void test_owner_claim(void);\nvoid think(Worker *,const Board *);")])
    result["search.c"],proofs["search.c"] = source.project(result["search.c"],[("after-real-successful-claim",
        b"    ++w->nodes;return 1;",b"    ++w->nodes;test_owner_claim();return 1;")])
    definitions = b'''static atomic_int test_owner_entered,test_owner_release;
void test_owner_claim(void){
 if(!atomic_exchange_explicit(&test_owner_entered,1,memory_order_acq_rel)){
  output("TEST_OWNER_SEARCH_ENTERED\\n");
  while(!atomic_load_explicit(&test_owner_release,memory_order_acquire))futex_wait(&test_owner_release,0,1);
 }
}
'''
    roles = [("test-only-held-real-claim",b"static void work(void *p){\n",definitions+b"static void work(void *p){\n"),
        ("release-only-after-real-stopped-store-before-pending-wait",
         b"    atomic_store_explicit(&stopped,1,memory_order_relaxed);\n    int count;",
         b"    atomic_store_explicit(&stopped,1,memory_order_relaxed);\n"
         b"    if(atomic_load_explicit(&test_owner_entered,memory_order_acquire)&&!atomic_load_explicit(&test_owner_release,memory_order_relaxed)){\n"
         b"     int n=atomic_load_explicit(&pending,memory_order_acquire);if(n<2||n>WORKERS+1||!atomic_load_explicit(&stopped,memory_order_relaxed))abort();\n"
         b'     output("TEST_OWNER_ACTIVE_PENDING\\n");atomic_store_explicit(&test_owner_release,1,memory_order_release);wake(&test_owner_release);\n    }\n    int count;')]
    if drop_wait:
        roles.append(("negative-delete-only-final-normal-wait",owner.FINAL_WAIT,b"    }\nshutdown:\n"))
    result["runtime.c"],proofs["runtime.c"] = source.project(result["runtime.c"],roles)
    return result,proofs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",type=Path,required=True); parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--compressed-bootstrap",action="store_true",help="additional frozen envelope cost only")
    args = parser.parse_args(); out,build = args.out.resolve(),args.build.resolve()
    if (sys.platform!="linux" or platform.machine()!="x86_64" or not args.out.is_absolute() or not args.build.is_absolute()
            or out.exists() or any((p/".git").exists() for p in (out,*out.parents))):
        parser.error("absolute selected build and new external output on Linux x86-64 required")
    raw = (build/"build.json").read_bytes(); selected = json.loads(raw)
    producer = tuple("engines/compact/tiny-entry-d/native/"+n for n in NATIVE)+(
        "engines/compact/tiny-entry-d/recipe.json","engines/compact/tiny-entry-d/shipping_fused_ray.py",
        "engines/compact/tiny-entry-d/packer.py","engines/experiments/tcec-scope/build.py",
        "engines/scripts/production.py","engines/scripts/minify.py","engines/scripts/rename_c.py",
        "engines/experiments/tiny-d-submission/source.py","engines/experiments/tiny-d-submission/build.py",
        "engines/experiments/tiny-d-submission/packaging.py","engines/experiments/tiny-d-submission/storage.py")
    if (any(selected.get(k) is not True for k in ("complete","frozen_execution","native_reproduced")) or
            selected.get("family")!="D" or selected.get("source_reduced") is not False or
            selected.get("equivalent_edits") is not True or selected.get("storage")!="prefix" or
            set(selected.get("inputs",{}))!=set(producer) or selected.get("units")!=["main.c","start.S"]):
        raise ValueError("exact unreduced prefix D control required")
    frozen = {"selection/build.json":raw}
    for name in producer:
        data = normalized(ROOT/name)
        if pin(data)!=selected["inputs"][name] or (build/"inputs"/name).read_bytes()!=data:
            raise ValueError("selected/current producer differs: "+name)
        frozen[name] = data
    for name in ("reduce.py","publication.py","process_owner.py","test_startup.py","test_process_owner.py"):
        logical = "engines/experiments/tiny-d-submission/"+name; frozen[logical] = normalized(ROOT/logical)
    if args.compressed_bootstrap:
        logical = "engines/experiments/tiny-d-submission/compressed_bootstrap.py"; frozen[logical] = normalized(ROOT/logical)
    for name in NATIVE:
        frozen["selection/generated-readable/"+name] = (build/"generated-readable"/name).read_bytes()
    if set(selected.get("shipping_inputs",{}))!={"main.c","start.S","image.ld"}:
        raise ValueError("complete selected single-TU shipping closure required")
    for name,expected in selected["shipping_inputs"].items():
        data=(build/"shipping-inputs"/name).read_bytes()
        if pin(data)!=expected:raise ValueError("actual selected shipping input differs")
        frozen["selection/shipping-inputs/"+name]=data
    out.mkdir()
    for name,data in frozen.items():
        p=out/"inputs"/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    executing=load("D_owner_frozen_execution",out/"inputs/engines/experiments/tiny-d-submission/test_process_owner.py")
    executing.run_snapshot(out,frozen,args.compressed_bootstrap)


def run_snapshot(out,frozen,compressed):
    source=load("D_owner_source",HERE/"source.py");builder=load("D_owner_builder",HERE/"build.py")
    storage=load("D_owner_storage",HERE/"storage.py");publication=load("D_owner_publication",HERE/"publication.py")
    owner=load("D_owner_projection",HERE/"process_owner.py");startup=load("D_owner_startup_fixture",HERE/"test_startup.py")
    reduce=load("D_owner_reducer",HERE/"reduce.py");packaging=load("D_owner_packaging",HERE/"packaging.py")
    lexical=load("D_owner_lexical",ROOT/"engines/scripts/rename_c.py")
    minifier=load("D_owner_minifier",ROOT/"engines/scripts/minify.py")
    packer=load("D_owner_elf",source.CANONICAL/"packer.py")
    bootstrap=load("D_owner_compressed_cost",HERE/"compressed_bootstrap.py") if compressed else None
    if pin(normalized(ROOT/source.HOST))["sha256"]!=source.HOST_SHA:
        raise ValueError("original command owner differs")
    hostmod=load("D_owner_commands",ROOT/source.HOST)
    hostmod.LIMITS={**hostmod.LIMITS,"aggregate_wall":300,"per_command_wall":35,
                   "parent_CPU":150,"parent_CPU_hard":170,"child_CPU":20}
    selected=json.loads(frozen["selection/build.json"]);api=source.production();profile=api.resource_profile("test-p4")
    report=dict(kind="D-process-owner-experimental-source-cost-runtime-v1",complete=False,commands=[],
        frozen_execution=True,inputs={n:pin(d) for n,d in frozen.items()},variants=[],runtime_cases=[],
        ownership_class=owner.KIND,baseline_wired=False,old_native_R_guard_used=False,
        real_target_allocation=False,locality_proof=False,strength_claim=False,
        per_worker_search_work_proof=False,runtime_qualified=False,whole_artifact_qualified=False,selected=False)
    def save():(out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    save();host=hostmod.Host(out,report,save)
    def expected_run(command,*,cwd,kind,expected=0,data=None):
        try:
            output=host.run(command,cwd=cwd,kind=kind,data=data)
        except ValueError as error:
            if str(error)!="tool failed or needed forced cleanup; evidence preserved: "+kind:
                raise
            startup.require_execution(report["commands"][-1],expected)
            output=Path(report["commands"][-1]["stdout"]["path"]).read_bytes()
        startup.require_execution(report["commands"][-1],expected)
        report["commands"][-1]["expected_returncode"]=expected
        return output
    try:
        report["compiler"]=expected_run(["cc","--version"],cwd=out,kind="compiler-version").decode().splitlines()[0]
        baseline,base_proof=startup.prepared(source,profile,True,storage,"prefix")
        if (not startup.json_equal(base_proof,selected["proof"]) or
                not startup.json_equal(profile.to_record(16),selected["resource"]) or
                baseline!={n:frozen["selection/generated-readable/"+n] for n in NATIVE}):
            raise ValueError("selected control full source/proof/resource replay differs")
        candidate,owner_proof=owner.transform(baseline,publication)
        if owner.restore(candidate,owner_proof,publication)!=baseline:
            raise ValueError("owner source inverse differs")
        report.update(selected_control_manifest=pin(frozen["selection/build.json"]),resource=profile.to_record(16),
            baseline_source={n:pin(d) for n,d in baseline.items()},owner_source={n:pin(d) for n,d in candidate.items()},
            production_proof=base_proof,owner_proof=owner_proof)
        owner_source_pins={n:pin(d) for n,d in sorted(candidate.items())}
        flags=builder.native_flags(profile);units=("main.c","start.S")
        for label,readable in (("baseline",baseline),("owner",candidate)):
            directory=out/label;directory.mkdir();raw=directory/"generated-readable";raw.mkdir()
            for n,d in readable.items():(raw/n).write_bytes(d)
            aggregate=b''.join(('#include "'+n+'"\n').encode() for n in source.UNITS if n.endswith('.c'))
            cpp=expected_run(["cc","-E","-P",*flags,"-I",str(raw),"-x","c","-"],cwd=directory,
                kind="preprocess-single-"+label,data=aggregate)
            entry=expected_run(["cc","-E","-P","-x","assembler-with-cpp",str(raw/"start.S")],
                cwd=directory,kind="preprocess-entry-"+label)
            emitted={"main.c":minifier.compact_source(cpp,"c"),"start.S":entry,"image.ld":readable["image.ld"]}
            raw_emitted={n:pin(d) for n,d in emitted.items()}
            legacy=selected.get("identifier_native_gate",{})
            renames=legacy.get("accepted_renames",{})
            if (not isinstance(renames,dict) or len(set(renames.values()))!=len(renames) or any(
                    not isinstance(a,str) or not isinstance(b,str) or re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*",a) is None or
                    re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*",b) is None for a,b in renames.items())):
                raise ValueError("finite capture-free selected identifier map required")
            if label=="baseline" and {"main.c":raw_emitted["main.c"]}!=legacy.get("before"):
                raise ValueError("selected v8 pre-identifier source differs")
            original_words=set(lexical._ANY_WORD.findall(emitted["main.c"].decode()))
            if any(new in original_words for new in renames.values()):
                raise ValueError("selected identifier map captures an original spelling")
            mapped={"main.c":emitted["main.c"]}
            for old,new in renames.items():mapped=lexical._replace(mapped,old,new)
            emitted.update(mapped)
            if label=="baseline" and (mapped!={"main.c":frozen["selection/shipping-inputs/main.c"]} or
                    {n:pin(d) for n,d in emitted.items()}!=selected["shipping_inputs"] or
                    {"main.c":pin(mapped["main.c"])}!=legacy.get("after")):
                raise ValueError("selected v8 exact post-identifier shipping replay differs")
            gate=directory/"identity-gate";gate.mkdir();observations=[]
            def compile_digest(c_files,trial):
                combined={**emitted,**c_files}
                for n,d in combined.items():(gate/n).write_bytes(d)
                expected_run(["cc",*flags,*[str(gate/n) for n in units],"-Wl,-T,"+str(gate/"image.ld"),"-o",str(gate/"linked")],
                    cwd=gate,kind=label+"-source-gate-"+str(trial))
                linked=(gate/"linked").read_bytes();native=packer.strip_native(linked)
                builder.kernel_geometry(packer,linked,profile.workers);builder.kernel_geometry(packer,native,profile.workers)
                observations.append(dict(trial=trial,linked=pin(linked),stripped=pin(native),
                    inputs={n:pin(d) for n,d in combined.items()}))
                return pin(linked)["sha256"]
            reduced,reduction=reduce.reduce_sources({"main.c":emitted["main.c"]},compile_digest,lexical,
                reserve=lexical._ANY_WORD.findall((entry+emitted["image.ld"]).decode()))
            emitted.update(reduced);prepared=directory/"shipping-inputs";prepared.mkdir()
            for n,d in emitted.items():(prepared/n).write_bytes(d)
            native_images=[];linked_images=[];native_records=[]
            for index in range(2):
                attempt=directory/("attempt-"+str(index));attempt.mkdir()
                expected_run(["cc",*flags,*[str(prepared/n) for n in units],"-Wl,-T,"+str(prepared/"image.ld"),"-o",str(attempt/"linked")],
                    cwd=attempt,kind=label+"-native-repeat-"+str(index))
                linked=(attempt/"linked").read_bytes();native=packer.strip_native(linked)
                (attempt/"native").write_bytes(native);linked_images.append(linked);native_images.append(native)
                native_records.append(dict(linked=pin(linked),stripped=pin(native),
                    linked_geometry=builder.kernel_geometry(packer,linked,profile.workers),
                    native_geometry=builder.kernel_geometry(packer,native,profile.workers)))
            if linked_images[0]!=linked_images[1] or native_images[0]!=native_images[1]:
                raise ValueError("independent owner/control native reproduction differs")
            if native_records[0]["linked"]["sha256"]!=reduction["final_native_sha256"]:
                raise ValueError("accepted source reduction is not final complete linked image")
            identity={k:native_records[0][k] for k in ("linked","stripped")}
            if label=="baseline" and identity!=EXPECTED:
                raise ValueError("baseline does not reproduce selected v8 linked/native identity")
            packages=[]
            for codec in ("alone","xz","xz-bcj"):
                whole,detail=packaging.package_native(native_images[0],codec)
                repeated,_=packaging.package_native(native_images[0],codec)
                if whole!=repeated:raise ValueError("native package reproduction differs")
                (directory/("native-"+codec)).write_bytes(whole)
                packages.append(dict(route="native-"+codec,whole=pin(whole),package=detail,package_reproduced=True))
            whole,detail=packaging.package_source(emitted,flags,units);repeated,_=packaging.package_source(emitted,flags,units)
            if whole!=repeated:raise ValueError("plain source-JIT reproduction differs")
            (directory/"source-jit").write_bytes(whole)
            packages.append(dict(route="source-jit",whole=pin(whole),package=detail,package_reproduced=True))
            if bootstrap is not None:
                whole,detail=bootstrap.package_source(emitted,flags,units,packaging)
                repeated,_=bootstrap.package_source(emitted,flags,units,packaging)
                if whole!=repeated:raise ValueError("compressed source-JIT reproduction differs")
                (directory/"source-jit-compressed").write_bytes(whole)
                packages.append(dict(route="source-jit-compressed",whole=pin(whole),package=detail,
                    package_reproduced=True,cost_only=True,runtime_qualified=False))
            report["variants"].append(dict(name=label,source={n:pin(d) for n,d in readable.items()},
                preprocessed=pin(cpp),shipping_inputs={n:pin(d) for n,d in emitted.items()},flags=flags,units=list(units),
                raw_pre_identifier_source=raw_emitted,legacy_control_identifier_map=renames,
                legacy_identifier_map_capture_free=True,selected_shipping_replayed=label=="baseline",
                source_reduction=reduction,reduction_digest_scope="complete linked ELF",reduction_observations=observations,
                native_rebuilds=native_records,native_reproduced=True,identity=identity,
                identity_is_selected_v8=identity==EXPECTED,packages=packages,experimental_owner_class=label=="owner"))
            save()
        old,new=report["variants"];costs={r["route"]:r["whole"]["bytes"] for r in old["packages"]}
        report["whole_savings"]={r["route"]:costs[r["route"]]-r["whole"]["bytes"] for r in new["packages"]}
        improve=any(n>0 for n in report["whole_savings"].values());report["cost_improved"]=improve
        if improve:
            cases=((4,False,False,False),(28,False,False,False),(256,False,False,False),
                   (256,False,False,True),(4,True,False,False),(4,False,True,False))
            plans=[dict(workers=w,fail=f,omit=o,go=g) for w,f,o,g in cases]
            plans += [dict(workers=4,zero=True),dict(workers=4,active="quit"),dict(workers=4,active="eof"),
                      dict(workers=4,active="quit",drop_wait=True)]
            for plan in plans:
                workers=plan["workers"];fail=plan.get("fail",False);omit=plan.get("omit",False);go=plan.get("go",False)
                active=plan.get("active");zero=plan.get("zero",False);negative=plan.get("drop_wait",False)
                suffix="drop-wait-negative" if negative else "active-"+active if active else "zero-spawn" if zero else "spawn-fail" if fail else "omit-clear" if omit else "go" if go else "startup"
                name=f"w{workers}-"+suffix;directory=out/name;directory.mkdir()
                small=api.ResourceProfile(name,"test",workers,16<<12)
                raw,small_proof=startup.prepared(source,small,True,storage,"prefix")
                owned,small_owner=owner.transform(raw,publication)
                if {n:pin(d) for n,d in sorted(owned.items())}!=owner_source_pins:
                    raise ValueError("scaled case differs from own class before instrumentation")
                files,test_proof=startup.instrument(owned,fail=fail,omit_clear=omit,go=go);extra=None
                if zero:
                    files["runtime.c"],extra=source.project(files["runtime.c"],[("fail-before-first-real-spawn",
                        b"char *stack=allocate(1048576+4096);if(!stack){status=2;break;}",
                        b'if(created==0){output("TEST_OWNER_ZERO_SPAWN_FAILURE\\n");status=2;break;}char *stack=allocate(1048576+4096);if(!stack){status=2;break;}')])
                if active:files,extra=active_instrument(files,source,owner,drop_wait=negative)
                for n,d in files.items():(directory/n).write_bytes(d)
                binary=directory/"x";small_flags=builder.native_flags(small)
                expected_run(["cc",*small_flags,*[str(directory/n) for n in source.UNITS],"-Wl,-T,"+str(directory/"image.ld"),"-o",str(binary)],
                    cwd=directory,kind="compile-"+name)
                builder.kernel_geometry(packer,binary.read_bytes(),workers)
                status=13 if negative else 2 if fail or zero else 7 if omit else 0;dialogue=None
                if active or go:
                    driver=directory/"dialogue.py";driver.write_text(ACTIVE if active else startup.DIALOGUE)
                    receipt=directory/"dialogue.json"
                    argv=[sys.executable,"-I","-B",str(driver),str(binary),str(receipt)]
                    if active:argv += [active]+(["negative"] if negative else [])
                    output=expected_run(argv,cwd=directory,kind="execute-"+name,expected=status)
                    dialogue=json.loads(receipt.read_text())
                    if (not all(dialogue.get(k) is True for k in ("complete","engine_started","engine_reaped","inherits_owner_group")) or
                            dialogue.get("forced_cleanup") or dialogue.get("returncode")!=0 or
                            negative and not dialogue.get("negative_detected")):
                        raise ValueError("owner dialogue failed natural group termination")
                else:
                    output=expected_run([str(binary)],cwd=directory,kind="execute-"+name,expected=status,data=b"uci\nisready\nquit\n")
                if active and not negative:
                    lines=output.splitlines()
                    if (len(lines)!=5 or lines[:4]!=[b"TEST_INITIALIZED",b"uciok",b"TEST_OWNER_SEARCH_ENTERED",b"TEST_OWNER_ACTIVE_PENDING"] or
                            not lines[4].startswith(b"bestmove ") or not dialogue.get("interrupted_after_real_claim")):
                        raise ValueError("deterministic active quit/EOF contract differs")
                elif negative:
                    if output!=b"TEST_INITIALIZED\nuciok\nTEST_OWNER_SEARCH_ENTERED\n":
                        raise ValueError("dropped final-wait negative did not fail at exact boundary")
                elif go:
                    lines=output.splitlines();legal={f"{f}2{f}{r}" for f in "abcdefgh" for r in "34"}|{"b1a3","b1c3","g1f3","g1h3"}
                    if (len(lines)!=6 or lines[:4]!=[b"TEST_INITIALIZED",b"uciok",b"TEST_PENDING_257",b"TEST_FINISHED_256"] or
                            lines[5]!=b"readyok" or not lines[4].startswith(b"bestmove ") or lines[4][9:].decode() not in legal):
                        raise ValueError("owner W256 real GO/output differs")
                elif fail or zero or omit:
                    marker=b"TEST_INJECTED_SPAWN_FAILURE\n" if fail else b"TEST_OWNER_ZERO_SPAWN_FAILURE\n" if zero else b"TEST_POISON_REMAINS\n"
                    if output!=marker:raise ValueError("exact owner failure boundary differs")
                elif not all(t in output for t in (b"TEST_INITIALIZED\n",b"uciok\n",b"readyok\n")):
                    raise ValueError("owner startup/protocol differs")
                report["runtime_cases"].append(dict(name=name,passed=True,expected_returncode=status,workers=workers,
                    tt_bits=12,tt_bytes=16<<12,source_before_instrumentation=owner_source_pins,owner_source_equal=True,
                    production=small_proof,owner=small_owner,instrumentation=test_proof,extra_instrumentation=extra,
                    flags=small_flags,binary=pin(binary.read_bytes()),output=output.decode(),dialogue=dialogue,
                    test_only_held_real_claim=bool(active),negative_final_wait_deleted=negative,
                    natural_termination=True,external_termination_used=False))
                save()
            if len(report["runtime_cases"])!=10:raise ValueError("owner full conditional runtime matrix incomplete")
            report["ownership_contract_passed"]=True
        else:
            report["ownership_contract_passed"]=False;report["runtime_deferred"]="no measured whole route improves"
        for row in report["commands"]:startup.require_execution(row,row["expected_returncode"])
        report["complete"]=True
    except BaseException as error:
        report["complete"]=False;report["failure"]=dict(type=type(error).__name__,message=str(error));raise
    finally:
        try:host.close()
        except BaseException as error:
            report["complete"]=False;report["cleanup_failure"]=dict(type=type(error).__name__,message=str(error));raise
        finally:
            c=report.get("host_cleanup",{})
            if c.get("errors") or c.get("unsettled_commands"):report["complete"]=False
            save()
    if not report["complete"]:raise ValueError("process-owner final cleanup incomplete")
    print(json.dumps(dict(complete=True,cost_improved=report["cost_improved"],whole_savings=report["whole_savings"],
        runtime_cases=len(report["runtime_cases"]),ownership_contract_passed=report["ownership_contract_passed"],
        runtime_qualified=False,selected=False)),flush=True)


if __name__=="__main__":main()
