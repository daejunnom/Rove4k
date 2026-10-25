#!/usr/bin/env python3
"""Fresh file-input source-JIT qualification of the protected D alpha class.

The source wrappers are unchanged. A separately labelled compiler observation
uses a delegating fixture, followed by ordinary R runs with the original PATH.
The actual source-wrapper image is linked7488; stripped7136 is a separate proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import stat
import sys
import types

sys.dont_write_bytecode=True
_EXECUTING_CODE=sys._getframe().f_code
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
D="engines/experiments/tiny-d-submission/"
SELF=D+"qualify_proper_alpha.py"
ALPHA_ADMISSION=D+"proper_alpha_admission.py"
PARENT=D+"search_admission.py"
BRIDGE=D+"search_runtime.py"
OLD_QUALIFIER=D+"qualify_search.py"
ROUTES=("source-jit","source-jit-compressed")


def require(value,message):
    if not value:raise ValueError(message)


def pin(data):
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def normalized(path):
    data=Path(path).read_bytes().replace(b"\r\n",b"\n")
    require(b"\r" not in data,"lone CR in named qualifier source")
    return data


def load(name,path,data=None):
    path=Path(path).resolve();data=path.read_bytes() if data is None else data
    module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module
    exec(compile(data,str(path),"exec",dont_inherit=True),module.__dict__);return module


def write(root,name,data):
    path=Path(root)/name;path.parent.mkdir(parents=True,exist_ok=True)
    require(not path.exists(),"qualifier never overwrites evidence")
    path.write_bytes(data)


def bounded_cpu(soft,hard,current,*,infinity=-1):
    require(all(type(v) is int and (v==infinity or v>=0) for v in (soft,hard,*current)),"integer inherited CPU pair required")
    def minimum(*items):
        values=[v for v in items if v!=infinity]
        return min(values) if values else infinity
    chosen_hard=minimum(hard,current[1]);chosen_soft=minimum(soft,current[0],chosen_hard)
    require(chosen_soft==infinity or chosen_soft>0,"CPU allowance exhausted")
    require(chosen_hard==infinity or 0<chosen_soft<=chosen_hard,"ordered CPU pair required")
    return chosen_soft,chosen_hard


def disjoint_output(out,roots):
    require(not out.exists() and not any((p/".git").exists() for p in (out,*out.parents)),"new external output required")
    for root in roots:
        root=Path(root).resolve()
        require(out!=root and root not in out.parents and out not in root.parents,
                "fresh output overlaps an archived evidence root")


CC_DELEGATE=r'''import hashlib,json,os,pathlib,stat,subprocess,sys
def require(value,message):
 if not value:raise ValueError(message)
def pin(data):return {"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
def readfd(fd,limit):
 os.lseek(fd,0,0);parts=[];count=0
 while True:
  b=os.read(fd,min(65536,limit+1-count))
  if not b:break
  parts.append(b);count+=len(b);require(count<=limit,"bounded compiler input")
 return b"".join(parts)
cfg=json.loads(pathlib.Path(os.environ["ROVE4K_CC_OBSERVATION"]).read_bytes())
out=pathlib.Path(cfg["compiler_evidence"]);out.mkdir()
report={"kind":"D-file-compiler-delegate-fixture-v1","complete":False,"instrumented":True,
 "pid":os.getpid(),"ppid":os.getppid(),"argv":sys.argv,"files_before":{},"files_after":{}}
fds=[]
try:
 args=sys.argv[1:];flags=cfg["flags"];units=cfg["units"]
 require(args[:len(flags)]==flags,"exact delegated flags")
 tail=args[len(flags):];require(len(tail)==len(units)+3,"exact file-input argv length")
 files=[pathlib.Path(v) for v in tail[:len(units)]];base=files[0].parent
 require(base.is_absolute() and base.name.startswith("rove4k-d-") and not base.is_symlink(),"owned wrapper private root")
 require(files==[base/n for n in units] and tail[-3]=="-Wl,-T,"+str(base/"image.ld")
  and tail[-2:]==["-o",str(base/"x")],"exact restored-file compiler argv")
 null=os.stat("/dev/null");actual=os.fstat(0)
 require(stat.S_ISCHR(actual.st_mode) and actual.st_rdev==null.st_rdev,"compiler FD0 must be /dev/null")
 report["compiler_fd0"]={"mode":actual.st_mode,"rdev":actual.st_rdev,"device":actual.st_dev,"inode":actual.st_ino,
  "is_devnull":True,"read_or_replaced":False}
 for name,want in cfg["shipping"].items():
  path=base/name;before=os.lstat(path)
  require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_uid==os.getuid(),"ordinary owned restored input")
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC);fds.append((name,path,fd,before))
  data=readfd(fd,1<<20);require(pin(data)==want,"actual restored input differs")
  (out/(name+".before")).write_bytes(data)
  report["files_before"][name]={"path":str(path),"pin":pin(data),"device":before.st_dev,"inode":before.st_ino}
 compiler=pathlib.Path(cfg["compiler"]["path"])
 require(not compiler.is_symlink() and pin(compiler.read_bytes())==cfg["compiler"]["pin"],"immutable delegated real compiler")
 actual_argv=[str(compiler),*args];report["real_argv"]=actual_argv
 child=subprocess.Popen(actual_argv,stdin=None,stdout=None,stderr=None)
 actual_child=os.stat("/proc/"+str(child.pid)+"/fd/0")
 child_stat=pathlib.Path("/proc/"+str(child.pid)+"/stat").read_text()
 require(stat.S_ISCHR(actual_child.st_mode) and actual_child.st_rdev==null.st_rdev,"real compiler FD0 must be /dev/null")
 report["real_compiler"]={"pid":child.pid,"start_ticks":int(child_stat.rpartition(")")[2].split()[19]),
  "fd0_is_devnull":True,"fd0_rdev":actual_child.st_rdev,"same_process_group":os.getpgid(child.pid)==os.getpgrp()}
 require(report["real_compiler"]["same_process_group"],"delegated compiler escaped owned process group")
 done=child.wait(timeout=60)
 report["returncode"]=done;require(done==0,"delegated compiler failed")
 for name,path,fd,before in fds:
  after=os.lstat(path);opened=os.fstat(fd);data=readfd(fd,1<<20)
  require((after.st_dev,after.st_ino)==(before.st_dev,before.st_ino)==(opened.st_dev,opened.st_ino)
   and stat.S_ISREG(after.st_mode) and after.st_nlink==1 and pin(data)==cfg["shipping"][name],"compiler input changed during read")
  (out/(name+".after")).write_bytes(data)
  report["files_after"][name]={"path":str(path),"pin":pin(data),"device":after.st_dev,"inode":after.st_ino}
 linked=(base/"x").read_bytes();require(pin(linked)==cfg["linked"],"actual linked output differs")
 (out/"linked.bin").write_bytes(linked);report["linked"]=pin(linked)
 require(pin(compiler.read_bytes())==cfg["compiler"]["pin"],"delegated compiler changed")
 report["complete"]=True
except BaseException as error:
 report["failure"]={"type":type(error).__name__,"message":str(error)}
 raise
finally:
 for _,_,fd,_ in fds:os.close(fd)
 (out/"compiler.json").write_text(json.dumps(report,indent=2)+"\n")
'''


def observe_wrapper(config_path):
    """Diagnostic child only: no typed admission is reconstructed here."""
    config_path=Path(config_path).resolve()
    require(config_path.name=="observation.json" and config_path.parent.is_dir(),"named observation config required")
    config=json.loads(config_path.read_bytes());root=config_path.parent
    require(config.get("kind")=="D-proper-alpha-file-input-observation-v1" and config["route"] in ROUTES,
            "exact diagnostic source-wrapper route required")
    runtime=load("D_alpha_observation_R",ROOT/"engines/experiments/tcec-next/profile_verify.py")
    scope,owner,_=runtime.support_modules()
    program=Path(config["program"])
    require(pin(program.read_bytes())==config["whole"],"measured observation wrapper differs")
    port=root/"compiler-port";port.mkdir()
    python=Path(sys.executable).resolve()
    require(" " not in str(python) and python.is_absolute(),"one absolute diagnostic Python required")
    delegate=("#!"+str(python)+" -I\n").encode()+CC_DELEGATE.encode()
    write(port,"cc",delegate);(port/"cc").chmod(0o700)
    report=dict(kind="D-proper-alpha-file-input-observation-v1",route=config["route"],complete=False,
        instrumented=True,shipping_timing=False,wrapper_before=pin(program.read_bytes()),delegate=pin(delegate),
        original_PATH=os.environ.get("PATH"),compiler=config["compiler"])
    save=lambda:(root/"mechanism.json").write_text(json.dumps(report,indent=2)+"\n")
    save();owned=None
    try:
        api=runtime.contracts();profile=api.resource_profile("test-p4")
        require(config["resources"]["workers"]==profile.workers==4
            and config["resources"]["tt_bits"]==23 and config["resources"]["tt_bytes"]==128<<20
            and config["resources"]["tt_entry_bytes"]==16,"diagnostic resource profile differs")
        available=runtime.effective_available_bytes()
        capacity=api.host_admission(profile,profile.layout(16),available,
            other_peak_bytes=max(768*api.MiB,profile.workers*16*api.MiB),reserve_bytes=256*api.MiB)
        capacity.require();report["launch_capacity"]=capacity.to_record();report["launch_available_bytes"]=available;save()
        os.environ["ROVE4K_CC_OBSERVATION"]=str(config_path)
        os.environ["PATH"]=str(port)+os.pathsep+config["original_PATH"]
        import time
        started=time.monotonic()
        engine=root/"engine";engine.mkdir()
        owned=owner.Owned(program,engine,owner.Budget(90))
        original=os.fstat(owned.process.stdin.fileno())
        owned.send(b"uci\nisready\n")
        owned.stdout.until(lambda data:b"uciok" in data.splitlines() and b"readyok" in data.splitlines(),owned.budget,seconds=60)
        snapshot=scope.image_snapshot(owned.process.pid,config["linked"]["sha256"])
        current=os.stat(Path("/proc")/str(owned.process.pid)/"fd/0")
        require((original.st_dev,original.st_ino)==(current.st_dev,current.st_ino),"observation changed original UCI pipe")
        require(len(snapshot["tasks"])==5,"observation worker topology differs")
        report.update(pid=owned.process.pid,startup=snapshot,original_UCI_stdin_pipe_preserved=True,
            cleanup_while_alive=runtime._clean_live(scope,owned,snapshot,config["wrapper_contract"],started))
        compiler=json.loads((Path(config["compiler_evidence"])/"compiler.json").read_bytes())
        require(compiler.get("complete") is True and compiler.get("returncode")==0
                and compiler.get("compiler_fd0",{}).get("is_devnull") is True,"actual file-input observation failed")
        report["compiler_record"]=pin((Path(config["compiler_evidence"])/"compiler.json").read_bytes())
        owned.send(b"quit\n");report["settled"]=scope.finish_owned(owned)
        require(report["settled"].get("returncode")==0,"observation engine did not exit naturally")
        report["wrapper_after"]=pin(program.read_bytes())
        require(report["wrapper_after"]==report["wrapper_before"]==config["whole"],"instrumentation changed shipping wrapper")
        report["complete"]=True
    except BaseException as error:
        report["failure"]=dict(type=type(error).__name__,message=str(error));raise
    finally:
        if owned is not None:
            cleanup=owned.cleanup();report["cleanup"]=cleanup
            if cleanup.get("forced_cleanup") or cleanup.get("errors") or not cleanup.get("owned_group_absent") or not cleanup.get("readers_joined"):
                report["complete"]=False
        report["owned_remaining"]=len(owner.OWNED)
        if report["owned_remaining"]:report["complete"]=False
        save()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observe",type=Path)
    parser.add_argument("--experiment",type=Path)
    parser.add_argument("--storage-evidence",type=Path)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    if args.observe:
        require(args.experiment is None and args.storage_evidence is None and args.out is None,"diagnostic child has one config only")
        observe_wrapper(args.observe);return
    require(sys.platform=="linux" and platform.machine()=="x86_64","Linux x86-64 qualifier required")
    require(args.experiment and args.storage_evidence and args.out and all(p.is_absolute() and ".." not in p.parts
        for p in (args.experiment,args.storage_evidence,args.out)),"explicit original evidence and fresh output required")
    experiment,storage_root,out=args.experiment.resolve(),args.storage_evidence.resolve(),args.out.resolve()
    disjoint_output(out,(experiment,storage_root))
    own=normalized(ROOT/SELF)
    require(compile(own,__file__,"exec",dont_inherit=True)==_EXECUTING_CODE,"executing qualifier source changed")
    old_raw=normalized(ROOT/OLD_QUALIFIER);old=load("D_alpha_old_qualifier_discovery",ROOT/OLD_QUALIFIER,old_raw)
    parent_raw=normalized(ROOT/PARENT);parent=load("D_alpha_parent_discovery",ROOT/PARENT,parent_raw)
    source_names_raw=normalized(ROOT/old.LOGICAL["source_inputs"])
    names=load("D_alpha_input_names",ROOT/old.LOGICAL["source_inputs"],source_names_raw)
    original=old.safe(experiment,"results.json");record=json.loads(original)
    producer=names.producer_names(json.loads(old.safe(experiment,"inputs/"+names.RECIPE)))
    inputs={n:old.safe(experiment,"inputs/"+n) for n in parent.input_names(record,producer)}
    products={n:old.safe(experiment,n) for n in parent.evidence_names(record,producer)}
    current={n:normalized(ROOT/n) for n in inputs if n.startswith("engines/")}
    require(all(current[n]==inputs[n] for n in current),"current/original producer closure differs")
    storage_raw=old.safe(storage_root,"results.json");storage_record=json.loads(storage_raw)
    storage_products={n:old.safe(storage_root,n) for n in parent.storage_evidence_names(storage_record)}
    alpha_raw=normalized(ROOT/ALPHA_ADMISSION);alpha=load("D_alpha_discovery",ROOT/ALPHA_ADMISSION,alpha_raw)
    frozen=dict(inputs)
    for n in alpha.REQUIRED_EXTRA:
        data=normalized(ROOT/n)
        require(n not in frozen or frozen[n]==data,"current shared helper differs from original")
        frozen[n]=data
    require(frozen[SELF]==own and frozen[PARENT]==parent_raw and frozen[OLD_QUALIFIER]==old_raw,
            "captured executing qualification source differs")
    out.mkdir()
    for n,data in frozen.items():write(out/"frozen",n,data)
    for n,data in products.items():write(out/"archived-products",n,data)
    for n,data in storage_products.items():write(out/"archived-storage",n,data)
    write(out,"original-results.json",original);write(out,"storage-results.json",storage_raw)
    active=load("D_alpha_frozen_qualifier",out/"frozen"/SELF,own)
    active.run_snapshot(out,experiment,storage_root,ROOT,record,original,inputs,products,current,
        storage_raw,storage_products,frozen)


def run_snapshot(out,experiment,storage_root,current_root,record,original,inputs,products,current,
                 storage_raw,storage_products,frozen):
    old=load("D_alpha_frozen_old_qualifier",ROOT/OLD_QUALIFIER,frozen[OLD_QUALIFIER])
    parent=load("D_alpha_frozen_parent",ROOT/PARENT,frozen[PARENT])
    bridge=load("D_alpha_frozen_parent_bridge",ROOT/BRIDGE,frozen[BRIDGE])
    alpha=load("D_alpha_frozen_admission",ROOT/ALPHA_ADMISSION,frozen[ALPHA_ADMISSION])
    runtime=load("D_alpha_frozen_R",ROOT/old.SUPPORT[0],frozen[old.SUPPORT[0]])
    rules=load("D_alpha_frozen_rules",ROOT/old.SUPPORT[1],frozen[old.SUPPORT[1]])
    old.require_support(runtime,{n:frozen[n] for n in old.SUPPORT})
    modules={n:load("D_alpha_parent_"+n,ROOT/path,inputs[path]) for n,path in old.LOGICAL.items()}
    extra_modules=dict(alpha=load("D_alpha_source_projection",ROOT/(D+"proper_alpha.py"),frozen[D+"proper_alpha.py"]),
        cleanup=load("D_alpha_closed_cleanup",ROOT/(D+"closed_tu_cleanup.py"),frozen[D+"closed_tu_cleanup.py"]),
        **{n:modules[n] for n in ("lexical","packaging","bootstrap","packer","builder")})
    host_path="engines/experiments/tcec-scope/build.py"
    require(pin(inputs[host_path])["sha256"]==modules["source"].HOST_SHA,"original current/frozen command owner differs")
    owner=load("D_alpha_commands",ROOT/host_path,inputs[host_path])
    report=dict(kind="D-proper-alpha-source-JIT-P4-qualification-v1",complete=False,commands=[],
        original_experiment=pin(original),storage_evidence=pin(storage_raw),
        frozen_execution=True,inputs={n:pin(d) for n,d in frozen.items()},
        source_admitted=False,native_admitted=False,package_generation_admitted=False,
        rules_qualified=False,fresh_full_artifact_runtime=False,size_qualified=False,
        physical_placement_qualified=False,strength_qualified=False,event_target_confirmed=False,
        selected=False,real_target_allocation=False,SDK11_compiled=False,
        compiler_file_observations=[],shipping_routes=[],old_maps_changed=False,
        shutdown_scope="local TCEC-targeted minimal shutdown contract; event approval unconfirmed")
    save=lambda:(out/"qualification.json").write_text(json.dumps(report,indent=2)+"\n")
    save();host=None;host_closed=False;counter=0
    # Reserve original and copied archives before the first fresh callback. A
    # callback can only create within new fresh-* directories outside them.
    reserved={str(experiment),str(storage_root),str(out/"frozen"),str(out/"archived-products"),str(out/"archived-storage")}
    reserved.update(str(experiment/n) for n in products)
    reserved.update(str(experiment/"inputs"/n) for n in inputs)
    reserved.update(str(storage_root/n) for n in storage_products)
    for row in record["commands"]+json.loads(storage_raw)["commands"]:
        reserved.add(row["cwd"])
        reserved.update(row[s]["path"] for s in ("stdout","stderr"))
        if isinstance(row.get("stdin"),dict):reserved.add(row["stdin"]["path"])
    reserved.update(str(out/"frozen"/n) for n in frozen)
    observed_paths=set()
    original_path=os.environ.get("PATH","")
    compiler_path=Path(shutil.which("cc",path=original_path) or "").resolve()
    require(compiler_path.is_file(),"literal real compiler required")
    compiler=dict(path=str(compiler_path),pin=pin(compiler_path.read_bytes()))
    report["compiler_context"]=dict(original_PATH=original_path,compiler=compiler,
        inherited_CPU=list(resource.getrlimit(resource.RLIMIT_CPU)))
    def fresh_path(path):
        path=Path(path)
        require(path.is_absolute() and out in path.parents and str(path) not in reserved
            and not any(Path(root)==path or Path(root) in path.parents for root in
                        (str(experiment),str(storage_root),str(out/"frozen"),str(out/"archived-products"),str(out/"archived-storage"))),
            "fresh callback aliases archived/source evidence")
        return path
    def run(command,*,cwd,kind,data=None):
        require(Path(cwd)==out or fresh_path(cwd),"fresh working directory required")
        result=host.run(command,cwd=cwd,kind=kind,data=data)
        row=dict(report["commands"][-1]);parent._settled(row)
        streams={}
        for name in ("stdout","stderr"):
            path=fresh_path(row[name]["path"])
            require(str(path) not in observed_paths,"fresh stream path reused")
            observed_paths.add(str(path));raw=old.safe(out,str(path.relative_to(out)))
            require(pin(raw)=={k:row[name][k] for k in ("bytes","sha256")},"fresh original stream pin differs")
            streams[name]=raw
        if data is not None:
            path=Path(row["stdout"]["path"]).with_suffix(".stdin")
            fresh_path(path);require(str(path) not in observed_paths,"fresh stdin path reused")
            observed_paths.add(str(path))
            require(old.safe(out,str(path.relative_to(out)))==data,"fresh actual compiler stdin differs")
        return result,row,streams
    def directory(label):
        nonlocal counter
        require(type(label) is str and label and all(p not in ("",".","..") for p in label.split("/")),"finite callback label required")
        counter+=1;path=fresh_path(out/("fresh-"+str(counter)+"-"+label.replace("/","-")))
        require(str(path) not in observed_paths,"fresh callback root reused")
        observed_paths.add(str(path));path.mkdir();return path
    def preprocess(files,flags,members,label):
        path=directory("pp-"+label)
        for n,d in files.items():write(path,n,d)
        driver=b''.join(('#include "'+n+'"\n').encode() for n in members)
        main,a,_=run(["cc","-E","-P",*flags,"-I",str(path),"-x","c","-"],cwd=path,
            kind="fresh-parent-preprocess-"+label,data=driver)
        entry,b,_=run(["cc","-E","-P","-x","assembler-with-cpp",str(path/"start.S")],cwd=path,
            kind="fresh-parent-entry-"+label)
        return dict(kind="D-search-preprocess-v1",label=label,input_pins=parent.inventory(files),flags=list(flags),
            members=list(members),driver=driver,readable_dir=str(path),commands=[a,b],outputs={"main.c":main,"start.S":entry})
    def compile_identity(files,flags,units,label):
        path=directory("native-"+label)
        for n,d in files.items():write(path,n,d)
        _,row,streams=run(["cc",*flags,*[str(path/n) for n in units],"-Wl,-T,"+str(path/"image.ld"),"-o",str(path/"linked")],
            cwd=path,kind="fresh-compile-"+label.replace("/","-"))
        linked=(path/"linked").read_bytes();native=modules["packer"].strip_native(linked);write(path,"native",native)
        return dict(kind="D-search-native-compile-v1",label=label,input_pins=parent.inventory(files),flags=list(flags),
            units=list(units),source_paths={n:str(path/n) for n in files},linked_path=str(path/"linked"),stripped_path=str(path/"native"),
            linked=linked,stripped=native,linked_pin=pin(linked),stripped_pin=pin(native),command=row,streams=streams)
    def semantic_callback(readable,*,label,options,valid_readable,structural_proof):
        generated,driver,proof=modules["probe"].render(readable,modules["source"],modules["storage_checker"],
            reference_board=valid_readable["board.c"],prefix=True,dense=False,variant_proof=structural_proof,
            union_order="union-order" in options,previous_index="previous-piece" in options,
            constant_start="constant-start" in options,unsigned_history="unsigned-history" in options)
        modes=[]
        for mode in ("plain","ubsan"):
            path=directory("semantic-"+label+"-"+mode)
            for n,d in generated.items():write(path,n,d)
            write(path,"driver.c",driver);program=path/"fixture"
            flags=modules["probe"].compiler_flags(prefix=True,dense=False,previous_index="previous-piece" in options,
                unsigned_history="unsigned-history" in options,mode=mode)
            _,compiled,_=run(["cc",*flags,str(path/"driver.c"),"-o",str(program)],cwd=path,kind="parent-semantic-compile-"+label+"-"+mode)
            output,executed,_=run([str(program)],cwd=path,kind="parent-semantic-run-"+label+"-"+mode)
            modes.append(dict(mode=mode,directory=str(path),source_paths={n:str(path/n) for n in (*generated,"driver.c")},
                binary_path=str(program),binary=program.read_bytes(),output=output,compile=compiled,execute=executed))
        return dict(kind="D-search-semantic-v1",label=label,options=list(options),input_pins=parent.inventory(readable),
            instrumented=generated,driver=driver,proof=proof,modes=modes)
    def preprocess_board(files,flags,label):
        path=directory("board-"+label)
        for n,d in files.items():write(path,n,d)
        output,row,streams=run(["cc","-E","-P",*flags,str(path/"board.c")],cwd=path,kind="proper-alpha-actual-board")
        return dict(kind="D-search-board-preprocess-v1",label=label,input_pins=parent.inventory(files),flags=list(flags),
            readable_dir=str(path),output=output,command=row,streams=streams)
    carriers=[]
    try:
        effective=bounded_cpu(480,600,resource.getrlimit(resource.RLIMIT_CPU),infinity=resource.RLIM_INFINITY)
        child=bounded_cpu(40,40,effective,infinity=resource.RLIM_INFINITY)[0]
        report["tool_CPU_limits"]=dict(parent=list(effective),child=child)
        owner.LIMITS={**owner.LIMITS,"aggregate_wall":900,"per_command_wall":120,"parent_AS":4<<30,
            "parent_CPU":effective[0],"parent_CPU_hard":effective[1],"child_CPU":child,"tool_output_bytes":4<<20}
        host=owner.Host(out,report,save)
        identity_root=directory("compiler-identity")
        version,version_command,_=run(["cc","--version"],cwd=identity_root,kind="actual-compiler-identity")
        require(version.decode().splitlines()[0]==record["compiler"],"actual compiler version differs from parent context")
        report["compiler_context"].update(version=version.decode().splitlines()[0],command=version_command);save()
        token=parent.admit_search(record,inputs,products,modules,current_inputs=current,
            admission_source={"current":frozen[PARENT],"frozen":frozen[PARENT]},evidence_root=str(experiment),
            preprocess=preprocess,compile_identity=compile_identity,semantic_callback=semantic_callback,
            storage_evidence=dict(raw=storage_raw,root=str(storage_root),products=storage_products))
        report["fresh_parent"]=token.to_record();save()
        for cmd in report["commands"]:
            reserved.add(cmd["cwd"])
            reserved.update(cmd[s]["path"] for s in ("stdout","stderr"))
            if isinstance(cmd.get("stdin"),dict):reserved.add(cmd["stdin"]["path"])
        alpha_token=alpha.admit_alpha(token,parent_module=parent,parent_source={"current":frozen[PARENT],"frozen":frozen[PARENT]},
            admission_source={"current":frozen[ALPHA_ADMISSION],"frozen":frozen[ALPHA_ADMISSION]},
            helper_sources={n:{"current":frozen[n],"frozen":frozen[n]} for n in (D+"proper_alpha.py",D+"closed_tu_cleanup.py")},
            frozen_inputs=frozen,current_inputs={n:d for n,d in frozen.items() if n.startswith("engines/")},
            modules=extra_modules,compile_identity=compile_identity,reserved_paths=tuple(sorted(reserved)))
        report.update(source_admitted=True,native_admitted=True,package_generation_admitted=True,admission=alpha_token.to_record());save()
        cases,coverage=rules.fixture_cases()
        fixture,rule_binding=alpha.render_rules(alpha_token,cases,parent_module=parent,search_runtime=bridge,
            preprocess_board=preprocess_board,shared=rules,minifier=modules["minifier"],lexical=modules["lexical"])
        rule_root=out/"rules";rule_root.mkdir();write(rule_root,"fixture.c",fixture)
        rule_report=dict(binding=rule_binding,coverage=coverage,complete=False,modes=[])
        for mode,extra in (("plain",[]),("ubsan",["-fsanitize=undefined","-fno-sanitize-recover=all"])):
            program=rule_root/("probe-"+mode)
            _,compiled,_=run(["cc","-std=c11","-O1","-g0","-fno-builtin","-msse4.2","-mcx16",*extra,
                str(rule_root/"fixture.c"),"-o",str(program)],cwd=rule_root,kind="proper-alpha-rules-compile-"+mode)
            output,executed,_=run([str(program)],cwd=rule_root,kind="proper-alpha-rules-run-"+mode)
            summary=rules._compare_output(output,cases)
            require(summary["cases"]==105 and summary["legal_moves_compared"]==2858,"complete actual rules comparison required")
            rule_report["modes"].append(dict(mode=mode,native=pin(program.read_bytes()),compile=compiled,execute=executed,**summary))
        rule_report["complete"]=True;write(rule_root,"rules.json",(json.dumps(rule_report,indent=2)+"\n").encode())
        report.update(rules_qualified=True,rules=pin((rule_root/"rules.json").read_bytes()));save()
        for route in ROUTES:
            named,accepted=alpha.carrier(alpha_token,route,runtime=runtime,frozen_inputs=frozen)
            carrier=out/("carrier-"+route);carrier.mkdir()
            for n,d in named.items():write(carrier,n,d)
            (carrier/accepted.program).chmod(0o700);carriers.append((route,carrier,named,accepted))
            obs=out/("file-input-"+route);obs.mkdir()
            config=dict(kind="D-proper-alpha-file-input-observation-v1",route=route,program=str(carrier/accepted.program),
                whole=pin(named[accepted.program]),shipping={n:pin(d) for n,d in alpha_token.shipping.items()},
                flags=token.to_record()["flags"],units=token.to_record()["units"],compiler=compiler,
                compiler_evidence=str(obs/"compiler-evidence"),linked=pin(alpha_token.linked),
                wrapper_contract=accepted.wrapper_contract,original_PATH=original_path,resources=accepted.resources,
                parent_launch_limits=runtime.execution_limits(accepted,runtime.effective_available_bytes(),wall_seconds=300))
            write(obs,"observation.json",(json.dumps(config,indent=2)+"\n").encode())
            _,command,_=run([sys.executable,"-I","-B",str(ROOT/SELF),"--observe",str(obs/"observation.json")],
                cwd=obs,kind="file-compiler-observation-"+route)
            mechanism_raw=(obs/"mechanism.json").read_bytes();mechanism=json.loads(mechanism_raw)
            ccroot=obs/"compiler-evidence";ccraw=(ccroot/"compiler.json").read_bytes();cc=json.loads(ccraw)
            require(mechanism.get("complete") is True and mechanism.get("instrumented") is True
                and mechanism.get("shipping_timing") is False and mechanism.get("owned_remaining")==0
                and cc.get("complete") is True and cc.get("returncode")==0,"actual compiler mechanism incomplete")
            require(cc["linked"]==pin(alpha_token.linked) and (ccroot/"linked.bin").read_bytes()==alpha_token.linked
                and modules["packer"].strip_native((ccroot/"linked.bin").read_bytes())==alpha_token.native,
                "actual file compiler output is not exact linked/canonical parent")
            for n,data in alpha_token.shipping.items():
                require((ccroot/(n+".before")).read_bytes()==data==(ccroot/(n+".after")).read_bytes(),
                        "actual compiler did not consume unchanged admitted file bytes")
            report["compiler_file_observations"].append(dict(route=route,instrumented=True,shipping_timing=False,
                mechanism=pin(mechanism_raw),compiler=pin(ccraw),actual_linked=cc["linked"],
                canonical_stripped=pin(alpha_token.native),command=command));save()
        host.close();host_closed=True
        require(report.get("host_cleanup")=={"unsettled_commands":0,"errors":[]},"all source/fixture commands must settle before R")
        require(os.environ.get("PATH","")==original_path and pin(compiler_path.read_bytes())==compiler["pin"],
                "diagnostic compiler delegation changed unmodified runtime context")
        for route,carrier,named,accepted in carriers:
            require(os.environ.get("PATH","")==original_path,"shipping R must use original PATH")
            limits=runtime.execution_limits(accepted,runtime.effective_available_bytes(),wall_seconds=300)
            observed=runtime.run_runtime(accepted,carrier,out/("runtime-"+route),limits)
            require(observed.get("complete") is True and observed.get("owned_remaining")==0
                and len(observed["sessions"])==4,"four natural unmodified shipping sessions required per route")
            report["shipping_routes"].append(dict(route=route,representation="source-jit",instrumented=False,
                original_PATH_preserved=True,runtime=pin((out/("runtime-"+route)/"runtime.json").read_bytes()),
                runtime_counts=observed["counts"],actual_linked=pin(alpha_token.linked),
                canonical_stripped=pin(alpha_token.native),whole=pin(named[accepted.program]),limits=limits))
            require(all(old.safe(carrier,n)==data for n,data in named.items()),"source carrier changed during unmodified R execution")
            save()
        require(all(normalized(current_root/n)==data for n,data in frozen.items() if n.startswith("engines/")),
                "current/frozen source changed during qualification")
        require(os.environ.get("PATH","")==original_path and pin(compiler_path.read_bytes())==compiler["pin"],"actual compiler context changed")
        alpha_token.assert_valid()
        report.update(fresh_full_artifact_runtime=True,current_frozen_closure_unchanged=True,carrier_unchanged=True,
            complete=True,unmodified_shipping_groups=8,instrumented_file_input_groups=2)
    except BaseException as error:
        report["complete"]=False;report["failure"]=dict(type=type(error).__name__,message=str(error));raise
    finally:
        if host is not None and not host_closed:
            try:host.close()
            except BaseException as error:
                report["cleanup_failure"]=dict(type=type(error).__name__,message=str(error));report["complete"]=False
        save()
    print(json.dumps({k:report[k] for k in ("complete","rules_qualified","fresh_full_artifact_runtime",
        "size_qualified","physical_placement_qualified","selected","unmodified_shipping_groups")}),flush=True)


if __name__=="__main__":main()
