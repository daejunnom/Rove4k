#!/usr/bin/env python3
"""Freeze and execute TinyF's real C contracts and independent runtime checks."""
import argparse
import contextlib
import ctypes
import hashlib
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(data):return hashlib.sha256(data).hexdigest()


def descendants(pid):
    result=set();pending=[pid]
    while pending:
        parent=pending.pop()
        try:tasks=list((Path("/proc")/str(parent)/"task").iterdir())
        except FileNotFoundError:continue
        for task in tasks:
            try:children=map(int,(task/"children").read_text().split())
            except FileNotFoundError:continue
            for child in children:
                if child not in result:result.add(child);pending.append(child)
    return result


@contextlib.contextmanager
def owned_children():
    """Adopt this isolated supervisor's compiler descendants and reap on error.

    SIGTERM lets the frozen bootstrap forward signals, wait and clean. The
    subreaper closes the exceptional case where that wrapper exits first and a
    separately-sessioned compiler survives it. No other child is admitted.
    """
    if descendants(os.getpid()):raise RuntimeError("identity supervisor already owns another child")
    libc=ctypes.CDLL(None,use_errno=True);previous=ctypes.c_int()
    if libc.prctl(37,ctypes.byref(previous),0,0,0) or libc.prctl(36,1,0,0,0):
        raise OSError(ctypes.get_errno(),"cannot establish owned-child subreaper")
    try:yield
    finally:
        # Every child of this otherwise child-free supervisor belongs to this
        # context. Compiler descendants are adopted if their parent exits.
        for sig in (signal.SIGTERM,signal.SIGKILL):
            end=time.monotonic()+2
            while time.monotonic()<end:
                for pid in descendants(os.getpid()):
                    try:os.kill(pid,sig)
                    except ProcessLookupError:pass
                while True:
                    try:pid,_=os.waitpid(-1,os.WNOHANG)
                    except ChildProcessError:pid=0
                    if not pid:break
                if not descendants(os.getpid()):break
                time.sleep(.01)
        remaining=descendants(os.getpid())
        libc.prctl(36,previous.value,0,0,0)
        if remaining:raise RuntimeError("owned compiler descendants remain: "+str(sorted(remaining)))


def admit_encoding(build_bytes,encoding):
    build=json.loads(build_bytes);record=json.loads(encoding.read_bytes())
    if set(record["input_hashes"])!={"encode.py","rename_c.py","pack_stream.py","compiler_group.py","main.c","input-build.json"}:
        raise ValueError("unknown frozen encoding input set")
    compact=next(item for item in build["engines"] if item["id"]=="tiny-F-compact")
    if record["input_hashes"].get("input-build.json")!=sha(build_bytes):
        raise ValueError("encoding belongs to a different build manifest")
    if record["input_source_sha256"]!=compact["source_sha256"]:
        raise ValueError("encoding belongs to a different compact F source")
    for name,digest in record["input_hashes"].items():
        path=Path(name)
        if path.name!=name or path.is_absolute():raise ValueError("unsafe encoding input name")
        if sha((encoding.parent/"frozen"/path).read_bytes())!=digest:
            raise ValueError("frozen encoding input changed: "+name)
    if sha((encoding.parent/"frozen/fixed-main.c").read_bytes())!=record["transformed_source_sha256"]:
        raise ValueError("transformed encoding source changed")
    for label,key in (("reference","reference_native"),("fixed","actual_native")):
        if sha((encoding.parent/"native"/(label+".elf")).read_bytes())!=record[key]["sha256"]:
            raise ValueError("encoding native identity class changed")
    if record["reference_native"]["sha256"]!=record["actual_native"]["sha256"]:
        raise ValueError("encoding native identity gate differs")
    allowed={str((encoding.parent/path).resolve()) for path in
             ("packed/xz/x","packed/gzip/x","packed/bzip2/x","xz-lc2-pb0/x")}
    if str(Path(record["selected"]["path"]).resolve()) not in allowed:
        raise ValueError("encoding selected artifact is outside its owned output")
    return {"build_manifest_sha256":sha(build_bytes),"compact_source_sha256":compact["source_sha256"],
            "encoding_report_sha256":sha(encoding.read_bytes()),"frozen_inputs_verified":True}


def identity(record,out):
    artifact=record["selected"];program=Path(artifact["path"])
    if sha(program.read_bytes())!=artifact["sha256"]:raise ValueError("selected complete file changed")
    temporary=out/"tmp";temporary.mkdir()
    with owned_children():
        return identity_process(record,out,temporary,program)


def identity_process(record,out,temporary,program):
    artifact=record["selected"]
    process=subprocess.Popen([str(program)],cwd=out,stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,
                             start_new_session=True,env={"PATH":os.defpath,"TMPDIR":str(temporary),"LC_ALL":"C"})
    lines=queue.Queue()
    def read():
        for line in process.stdout:lines.put(line.rstrip())
    thread=threading.Thread(target=read,daemon=True);thread.start()
    transcript=[]
    def send(command):process.stdin.write(command+"\n");process.stdin.flush()
    def until(expected):
        while True:
            line=lines.get(timeout=60);transcript.append(line)
            if line==expected:return
    try:
        send("uci");until("uciok")
        proc=Path("/proc")/str(process.pid)
        native=(proc/"exe").read_bytes()
        if sha(native)!=record["actual_native"]["sha256"]:raise AssertionError("actual restored native differs from identity class")
        tasks=sorted(int(path.name) for path in (proc/"task").iterdir())
        expected=record["representation"]["fixed_profile"]["WORKERS"]+1
        if len(tasks)!=expected:raise AssertionError("fixed workers not present before readiness")
        if (proc/"task"/str(process.pid)/"children").read_text().strip():raise AssertionError("compiler/decoder child remains")
        if list(temporary.iterdir()):raise AssertionError("owned compilation files remain at UCI-ready")
        send("isready");until("readyok")
        if tasks!=sorted(int(path.name) for path in (proc/"task").iterdir()):raise AssertionError("worker IDs changed")
        result={"passed":True,"wrapper_sha256":artifact["sha256"],"wrapper_bytes":artifact["bytes"],
                "actual_native_sha256":sha(native),"actual_native_bytes":len(native),
                "exe_target":os.readlink(proc/"exe"),"startup_task_ids":tasks,
                "compiler_children":[],"owned_temporary_entries":[],"transcript":transcript}
        send("quit");process.wait(timeout=3)
        if process.returncode:raise AssertionError("restored runtime failed quit")
        (out/"identity.json").write_text(json.dumps(result,indent=2)+"\n")
        return result
    finally:
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=7)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--encoding",type=Path)
    parser.add_argument("--cc",default="cc")
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or ROOT==args.out or ROOT in args.out.parents:
        parser.error("new absolute external output required")
    build_bytes=args.build.read_bytes();encoding_binding=admit_encoding(build_bytes,args.encoding) if args.encoding else None
    encoding_record=json.loads(args.encoding.read_bytes()) if args.encoding else None
    if args.encoding and sha(args.encoding.read_bytes())!=encoding_binding["encoding_report_sha256"]:
        raise ValueError("encoding report changed during admission")
    args.out.mkdir(parents=True);frozen=args.out/"frozen"
    names=("engines/compact/tiny-f/qualify.py","engines/compact/tiny-f/check.py","engines/compact/tiny-f/contract.c",
           "engines/tests/verify.py","engines/tests/chess_oracle.py")
    inputs={name:(ROOT/name).read_bytes() for name in names}
    for name,content in inputs.items():
        target=frozen/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
    build=json.loads(build_bytes);dev=next(record for record in build["engines"] if record["id"]=="tiny-F-dev")
    source=(Path(dev["cwd"])/"main.c").read_bytes()
    if sha(source)!=dev["source_sha256"]:raise ValueError("actual DEV source changed")
    dev_input=frozen/"dev/main.c";dev_input.parent.mkdir();dev_input.write_bytes(source)
    (frozen/"build.json").write_bytes(build_bytes)
    validation=list(build["engines"])
    if build.get("selected"):
        artifact=build["selected"]
        validation.append({"id":"tiny-F-selected","command":[artifact["path"]],"cwd":str(Path(artifact["path"]).parent),
                           "profile":"shipping","workers":dev["workers"],"startup_threads":dev["startup_threads"],
                           "startup_timeout":60,"expected_program_sha256":artifact["sha256"]})
    validation_path=frozen/"validation-manifest.json"
    validation_path.write_text(json.dumps({"engines":validation},indent=2)+"\n")
    contracts=[]
    for label,flags in (("optimized",["-O2"]),("sanitized",["-O1","-g","-fsanitize=address,undefined","-fno-omit-frame-pointer"]),
                        ("ply-cap",["-O2","-DPLY=4"])):
        command=[args.cc,"-std=c11",*flags,"-pthread","-DDEV=1","-DWORKERS=2","-DTT_BITS=8",
                 "-DTINY_F_STRUCTURED="+str(int(bool(build.get("structure")))),"-I"+str(dev_input.parent),
                 str(frozen/"engines/compact/tiny-f/contract.c"),"-o",str(args.out/(label+".elf"))]
        subprocess.run(command,check=True,capture_output=True,timeout=60)
        execution=subprocess.run([str(args.out/(label+".elf"))],check=True,capture_output=True,text=True,timeout=60)
        contracts.append({"label":label,"compile":command,"binary_sha256":sha((args.out/(label+".elf")).read_bytes()),
                          "result":json.loads(execution.stdout),"stderr":execution.stderr})
    if contracts[0]["result"]["state_digest"]!=contracts[1]["result"]["state_digest"]:raise AssertionError("sanitized state differs")
    subprocess.run([sys.executable,"-B",str(frozen/"engines/compact/tiny-f/check.py"),"--manifest",str(validation_path),
                    "--out",str(args.out/"independent")],check=True,timeout=120)
    subprocess.run([sys.executable,"-B",str(frozen/"engines/tests/verify.py"),"--manifest",str(validation_path),
                    "--out",str(args.out/"blackbox"),"--startup-threads",str(dev["startup_threads"])],check=True,timeout=180)
    encoding_identity=None
    if args.encoding:
        (frozen/"encoding-report.json").write_text(json.dumps(encoding_record,indent=2)+"\n")
        artifact=encoding_record["selected"]
        encoded_validation={"engines":[{"id":"tiny-F-encoding-selected","profile":"shipping","command":[artifact["path"]],
                                       "cwd":str(Path(artifact["path"]).parent),"workers":dev["workers"],
                                       "startup_threads":dev["startup_threads"],"startup_timeout":60,"expected_program_sha256":artifact["sha256"]}]}
        encoded_path=frozen/"encoded-validation-manifest.json";encoded_path.write_text(json.dumps(encoded_validation,indent=2)+"\n")
        encoding_identity=identity(encoding_record,args.out)
        subprocess.run([sys.executable,"-B",str(frozen/"engines/tests/verify.py"),"--manifest",str(encoded_path),
                        "--out",str(args.out/"encoded-blackbox"),"--startup-threads",str(dev["startup_threads"]),"--suite","shipping","--plies","16"],check=True,timeout=120)
    report={"passed":True,"build_manifest_sha256":sha(build_bytes),"dev_source_sha256":dev["source_sha256"],
            "test_inputs":{name:sha(content) for name,content in inputs.items()},"contracts":contracts,
            "encoding_binding":encoding_binding,"encoding_identity":encoding_identity}
    report["derived_validation_sha256"]=sha(validation_path.read_bytes())
    (args.out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"passed":True,"state_cases_per_contract":36,"contracts":len(contracts),"encoding_qualified":bool(encoding_identity)}),flush=True)


if __name__=="__main__":main()
