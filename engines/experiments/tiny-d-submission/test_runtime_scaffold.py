#!/usr/bin/env python3
"""Finite new-contract D syscall/termination source experiment.

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
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FILES = ("tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld")
EXPECTED = {"linked": dict(bytes=7712, sha256="c80f6c4d3b7af14a96f47326c843abbabd7626a54c879ed21a376eca22d7eeca"),
            "stripped": dict(bytes=7360, sha256="cfa7b5d045d5f1e6e2232942e38d79cd8b8812e9e3ed7702fb4df50ab71296f4")}


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


DIALOGUE = r'''import json,os,select,subprocess,sys,time
from pathlib import Path
record=dict(complete=False,events=[],forced_cleanup=False,engine_reaped=False)
path=Path(sys.argv[2]);mode=sys.argv[3];immediate=sys.argv[4]=="1"
buffer=b"";child=None;deadline=time.monotonic()+25
legal={f"{f}2{f}{r}" for f in "abcdefgh" for r in "34"}|{"b1a3","b1c3","g1f3","g1h3"}
def save():path.write_text(json.dumps(record,indent=2)+"\n")
def send(data):
 child.stdin.write(data);child.stdin.flush();record["events"].append(dict(send=data.decode()));save()
def line():
 global buffer
 while b"\n" not in buffer:
  left=deadline-time.monotonic()
  if left<=0:raise TimeoutError("bounded scaffold dialogue")
  if select.select([child.stdout],[],[],min(left,.2))[0]:
   data=os.read(child.stdout.fileno(),4096)
   if not data:
    if buffer:raise ValueError("partial final output")
    return None
   buffer+=data
   if len(buffer)>65536:raise ValueError("output bound")
 value,buffer=buffer.split(b"\n",1)
 record["events"].append(dict(receive=value.decode()));save();return value
def until(value):
 while True:
  item=line()
  if item is None:raise EOFError("missing required reply")
  if item==value:return
def best():
 item=line()
 if item is None or not item.startswith(b"bestmove ") or item[9:].decode() not in legal:raise ValueError("legal complete startpos reply required")
 return item
try:
 child=subprocess.Popen([sys.argv[1]],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=None,bufsize=0)
 record.update(engine_started=True,pid=child.pid,pgid=os.getpgid(child.pid),owner_pgid=os.getpgrp(),inherits_owner_group=os.getpgid(child.pid)==os.getpgrp());save()
 if not record["inherits_owner_group"]:raise ValueError("engine group escape")
 send(b"uc");time.sleep(.01);send(b"i\nisready\n");until(b"uciok");until(b"readyok")
 if mode=="valid":
  send(b"setoption name Threads value 1\nponderhit\ndebug on\nregister\nunsupported\nisready\n");until(b"readyok")
  history=b"g1f3 g8f6 f3g1 f6g8 "*256
  record["history_plies"]=1024;record["history_line_bytes"]=len(b"position startpos moves "+history+b"\n")
  send(b"position startpos moves "+history+b"\ngo wtime 300 btime 300 winc 0 binc 0\n");best()
  send(b"position startpos\ngo\n");best()
  send(b"position startpos\ngo wtime 300 btime 300\nposition startpos\nisready\n");best();until(b"readyok")
  send(b"isready");child.stdin.close();child.stdin=None;until(b"readyok")
 else:
  send(b"position startpos\ngo wtime 3600000 btime 3600000\n");until(b"TEST_OWNER_SEARCH_ENTERED")
  if mode=="quit":send(b"quit\n")
  elif mode!="eof":raise ValueError("finite terminal mode")
  child.stdin.close();child.stdin=None;record["interrupted_after_real_claim"]=True;save()
  replies=[]
  while (item:=line()) is not None:
   if item==b"TEST_OWNER_ACTIVE_PENDING":record["stopped_before_wait"]=True
   elif item.startswith(b"bestmove ") and item[9:].decode() in legal:replies.append(item.decode())
   else:raise ValueError("unexpected terminal output")
  if len(replies)>1 or (not immediate and (len(replies)!=1 or not record.get("stopped_before_wait"))):raise ValueError("terminal output ownership contract differs")
  record["terminal_replies"]=replies
 if line() is not None:raise ValueError("unexpected trailing output")
 code=child.wait(timeout=5);record.update(returncode=code,engine_reaped=True)
 if code:raise ValueError("natural engine exit differs")
 record["complete"]=True;save()
finally:
 if child is not None and child.poll() is None:
  record["forced_cleanup"]=True;child.kill();child.wait();record["engine_reaped"]=True
 save()
'''


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
                 "compressed_bootstrap.py", "syscall_arity.py", "test_runtime_scaffold.py"):
        logical = "engines/experiments/tiny-d-submission/"+name
        inputs[logical] = normalized(ROOT/logical)
    inputs["selection/build.json"] = (selected/"build.json").read_bytes()
    out.mkdir()
    for name,data in inputs.items():
        path=out/"inputs"/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    frozen=load("d_scaffold_frozen",out/"inputs/engines/experiments/tiny-d-submission/test_runtime_scaffold.py")
    frozen.run_snapshot(out,inputs,ROOT)


def run_snapshot(out,inputs,origin):
    mods={n:load("d_scaffold_"+n,HERE/(n+".py")) for n in
          ("source","build","storage","publication","process_owner","test_startup","test_process_owner",
           "packaging","compressed_bootstrap","reduce","syscall_arity")}
    source, builder, startup = mods["source"],mods["build"],mods["test_startup"]
    lexical=load("d_scaffold_lexical",ROOT/"engines/scripts/rename_c.py")
    minifier=load("d_scaffold_minify",ROOT/"engines/scripts/minify.py")
    packer=load("d_scaffold_packer",source.CANONICAL/"packer.py")
    hostmod=load("d_scaffold_commands",ROOT/source.HOST)
    if pin(normalized(ROOT/source.HOST))["sha256"] != source.HOST_SHA:
        raise ValueError("original command owner differs")
    hostmod.LIMITS={**hostmod.LIMITS,"aggregate_wall":360,"per_command_wall":35,"parent_CPU":220,"parent_CPU_hard":240,"child_CPU":25}
    report=dict(kind="D-explicit-syscall-arity-and-TCEC-terminal-cost-v1",complete=False,frozen_execution=True,
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
        plans=(("owner-control",False,False,False),("arity",True,False,False),
               ("arity-wake",True,True,False),("arity-wake-immediate",True,True,True))
        for label,arity,noinline,immediate in plans:
            readable,proof=(owned,None) if not arity else mods["syscall_arity"].transform(
                owned,mods["process_owner"],mods["publication"],ownerproof,
                noinline_wake=noinline,immediate_exit=immediate)
            if arity and mods["syscall_arity"].restore(readable,proof,mods["process_owner"],mods["publication"])!=owned:
                raise ValueError("scaffold complete source inverse differs")
            directory=out/label;directory.mkdir();raw=directory/"generated-readable";raw.mkdir()
            for name,data in readable.items():(raw/name).write_bytes(data)
            flags=builder.native_flags(profile);units=("main.c","start.S")
            cpp=run(["cc","-E","-P",*flags,"-I",str(raw),"-x","c","-"],cwd=raw,kind=label+"-preprocess",
                data=b''.join(('#include "'+n+'"\n').encode() for n in source.UNITS if n.endswith('.c')))
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
            if not arity and identity!=EXPECTED:raise ValueError("current owner control native differs")
            packages=[]
            for codec in ("alone","xz","xz-bcj"):
                whole,detail=mods["packaging"].package_native(images[0][1],codec)
                repeated,_=mods["packaging"].package_native(images[0][1],codec)
                if whole!=repeated:raise ValueError("whole repeat differs")
                path=directory/("packed-"+codec);path.write_bytes(whole);path.chmod(0o700)
                packages.append(dict(route="packed-"+codec,whole=pin(whole),detail=detail,reproduced=True))
            whole,detail=mods["compressed_bootstrap"].package_source(emitted,flags,units,mods["packaging"])
            repeated,_=mods["compressed_bootstrap"].package_source(emitted,flags,units,mods["packaging"])
            if whole!=repeated:raise ValueError("compressed source double reproduction differs")
            (directory/"source-jit-compressed").write_bytes(whole)
            packages.append(dict(route="source-jit-compressed",whole=pin(whole),detail=detail,reproduced=True))
            report["variants"].append(dict(name=label,source={n:pin(d) for n,d in readable.items()},proof=proof,
                flags=flags,units=list(units),shipping={n:pin(d) for n,d in emitted.items()},
                legacy_renames=renames,reduction=reduction,native=observations,packages=packages,
                last_search_output_required=not immediate,ignored_syscall_register_trace_changed=arity))
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
        if len(report["runtime_cases"])!=12:raise ValueError("finite runtime matrix incomplete")
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
