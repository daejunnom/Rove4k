"""Byte reproduction and bounded Linux runtime tests for Rust source streams.

All codecs get deterministic byte/stdin tests. Only the selected codec gets the
actual Rust compile/fd-exec and compiler-group signal lifecycle campaign.
"""
from __future__ import annotations
import argparse
import ast
import bz2
import gzip
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import selectors
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIXED = {"ROVE_WORKERS": "2", "ROVE_TT_BITS": "18", "SOURCE_DATE_EPOCH": "0", "LC_ALL": "C", "TZ": "UTC"}
COMMAND = ["rustc", "-", "--crate-name", "r4_stream_fixture", "--edition=2024",
           "-Copt-level=z", "-Clto=fat", "-Ccodegen-units=1", "-Cpanic=abort",
           "-Cstrip=symbols", "-Clink-arg=-Wl,--build-id=none", "-o", "x"]
PREPARED = False
_HOST = None
HOST_COMMANDS = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def module():
    spec = importlib.util.spec_from_file_location("r4_rust_stream_runtime_tests", HERE / "stream_pack.py")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def emit(producer, directory, source, command, codec, fixed=FIXED):
    directory.mkdir(parents=True, exist_ok=False)
    data, metadata = producer.make_stream(source, list(producer.COMMAND), codec, environment=fixed, prepared=PREPARED)
    path = directory / "launcher"
    path.write_bytes(data)
    path.chmod(0o755)
    scratch = directory / "scratch"
    scratch.mkdir()
    env = os.environ.copy()
    env["TMPDIR"] = str(scratch)
    if tuple(command) != producer.COMMAND:
        observing = directory / "compiler-bin"
        observing.mkdir()
        shim = observing / "rustc"
        shim.write_text("#!" + sys.executable + "\nimport os,sys\n"
                        + "os.execv(" + repr(command[0]) + "," + repr(list(command)) + "+sys.argv[1:])\n", encoding="utf-8")
        shim.chmod(0o755)
        env["PATH"] = str(observing) + os.pathsep + env.get("PATH", "")
    save(directory / "artifact.json", metadata)
    return path, scratch, env, metadata


def host_owner():
    global _HOST
    if _HOST is None:
        path=ROOT/'engines/compact/tiny-rust-d-shipping/build.py'
        spec=importlib.util.spec_from_file_location('rust_stream_existing_host_owner',path)
        _HOST=importlib.util.module_from_spec(spec);spec.loader.exec_module(_HOST)
    return _HOST


def start_owned(arguments, **options):
    owner=host_owner();process=None
    mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
    try:
        process=subprocess.Popen(arguments,start_new_session=True,
            preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,mask),**options)
        row={'pid':process.pid,'forced_cleanup':False,'started':True}
        owner.owned[process]=row;HOST_COMMANDS.append(row)
        return process
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK,mask)


def finish_owned(process, seconds):
    owner=host_owner();deadline=time.monotonic()+seconds
    while not owner.exited_unreaped(process):
        if time.monotonic()>deadline:raise TimeoutError('Rust fixture wrapper did not settle')
        time.sleep(.01)
    row=owner.owned[process]
    owner.settle(process,row)
    assert not row['forced_cleanup'] and row['owned_group_absent']
    return process.returncode


def run_owned(arguments, *, env, timeout):
    with tempfile.TemporaryFile() as stdout,tempfile.TemporaryFile() as stderr:
        process=start_owned(arguments,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
        try:
            code=finish_owned(process,timeout)
            stdout.seek(0);stderr.seek(0)
            return subprocess.CompletedProcess(arguments,code,stdout.read(),stderr.read())
        finally:close(process)


def close(process):
    owner=_HOST
    if owner is not None and process in owner.owned:
        row=owner.owned[process]
        mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
        try:
            if not owner.exited_unreaped(process):
                # Ask the still-owned wrapper to drain its separately owned
                # compiler group. Never signal a saved, post-reap compiler PGID.
                os.kill(process.pid,signal.SIGTERM);end=time.monotonic()+12
                while not owner.exited_unreaped(process) and time.monotonic()<end:time.sleep(.01)
            owner.settle(process,row,force=not owner.exited_unreaped(process))
        finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None and not stream.closed:
            stream.close()


def line(process, timeout=60):
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        assert selector.select(timeout), "no native output before bounded deadline"
    result = process.stdout.readline()
    assert result, "stdout closed before expected response"
    return result


def no_process(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


def byte_contract(producer, out):
    source = b'fn main(){println!("source literal");}\n'
    decoders = {"xz": lzma.decompress, "gzip": gzip.decompress, "bzip2": bz2.decompress}
    records = []
    for codec in producer.CODECS:
        first, metadata = producer.make_stream(source, COMMAND, codec, environment=FIXED)
        second, repeated = producer.make_stream(source, COMMAND, codec, environment=dict(FIXED))
        assert first == second and metadata == repeated, "complete file generation did not reproduce"
        assert metadata["bytes"] == len(first) and metadata["sha256"] == sha(first)
        origin = (ROOT / producer.ORIGIN["path"]).read_bytes()
        assert sha(origin) == producer.ORIGIN["sha256"] == metadata["upstream_helper_sha256"]
        assert first.startswith(b"#!/bin/sh\nexec python3 "), "shell must immediately exec its Python decoder"
        offset = metadata["payload_offset_1based"]
        assert offset - 1 == metadata["stub_bytes"]
        assert len(first) - offset + 1 == metadata["payload_bytes"]
        script = decoders[codec](first[offset-1:])
        assert len(script) == metadata["python_bytes"]
        tree=ast.parse(script)
        calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call)]
        process_calls=[node for node in calls if isinstance(node.func,ast.Attribute)
                       and isinstance(node.func.value,ast.Name) and node.func.value.id=='p']
        assert not any(node.func.attr in ('poll','communicate') for node in process_calls), "compiler leader must not be reaped during feed or observation"
        final_reaps=[node for node in process_calls if node.func.attr=='wait']
        assert len(final_reaps)==1, "one final compiler reap is required"
        waits=[node for node in calls if isinstance(node.func,ast.Attribute)
               and isinstance(node.func.value,ast.Name) and node.func.value.id=='os' and node.func.attr=='waitid']
        assert len(waits)>=2
        for wait in waits:
            flags={node.attr for node in ast.walk(wait.args[2]) if isinstance(node,ast.Attribute)}
            assert {'WEXITED','WNOWAIT'}<=flags, "all compiler-exit observation must preserve its zombie identity"
        initial=[node for node in waits if not any(isinstance(flag,ast.Attribute) and flag.attr=='WNOHANG' for flag in ast.walk(node.args[2]))]
        drains=[node for node in ast.walk(tree) if isinstance(node,ast.While) and isinstance(node.test,ast.Call)
                and isinstance(node.test.func,ast.Name) and node.test.func.id=='live']
        assert len(initial)==1 and len(drains)==1
        assert initial[0].lineno<drains[0].lineno and drains[0].end_lineno<final_reaps[0].lineno, "source feed/exited observation/group drain/final reap ordering changed"
        assert b"zipfile" not in script and b"sys.argv[1:]" in script
        for key, value in FIXED.items():
            assert key.encode() in script and value.encode() in script
        (out / f"complete-{codec}").write_bytes(first)
        records.append(metadata)
    fixtures = (b"fn main(){}\n", b"/* ''' */\n", b'/* \'\'\' """ */\n', b"line\r\n", b"zero\0byte",
                b"invalid\xffutf8", b"ends\\", b"ends\\\\", b"quote'", "/* 한글 é */\n".encode(),
                b'const S:&str="$(printf injected)";\n')
    captures = []
    for codec in producer.CODECS:
        for number, data in enumerate(fixtures):
            location = out / f"capture-{codec}-{number}"
            capture = location / "captured"
            details = location / "compiler.json"
            compiler = out / f"capture-compiler-{codec}-{number}.py"
            compiler.write_text("import json,os,sys\nfrom pathlib import Path\n"
                f"Path({str(capture)!r}).write_bytes(sys.stdin.buffer.read())\n"
                f"Path({str(details)!r}).write_text(json.dumps({{'argv':sys.argv,'cwd':os.getcwd(),'TMPDIR':os.environ['TMPDIR'],'workers':os.environ.get('ROVE_WORKERS'),'bits':os.environ.get('ROVE_TT_BITS')}}))\n"
                "raise SystemExit(23)\n", encoding="utf-8")
            path, scratch, env, _ = emit(producer, location, data, [sys.executable, str(compiler)], codec)
            env.update(ROVE_WORKERS="999", ROVE_TT_BITS="7")
            result = subprocess.run([str(path)], env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=8)
            assert result.returncode == 23 and result.stderr == b"", result.stderr
            assert capture.read_bytes() == data
            detail = json.loads(details.read_text())
            assert detail["workers"] == "2" and detail["bits"] == "18"
            assert detail["cwd"] == detail["TMPDIR"] and Path(detail["TMPDIR"]).parent == scratch
            assert not Path(detail["TMPDIR"]).exists() and not list(scratch.iterdir())
            captures.append({"codec": codec, "case": number, "stdin_sha256": sha(data), "stdin_bytes": len(data), "returncode": result.returncode})
    rejected=[]
    for label,changes in (("unknown-codec",{"codec":"unknown"}),
                          ("command-drift",{"command":["rustc","-"]}),
                          ("environment-missing",{"environment":{"ROVE_WORKERS":"2"}}),
                          ("environment-extra",{"environment":dict(FIXED,UNEXPECTED="value")}),
                          ("non-bytes",{"source":"text"})):
        arguments={"source":source,"command":COMMAND,"codec":"xz","environment":dict(FIXED)}
        arguments.update(changes)
        try:producer.make_stream(**arguments)
        except (ValueError,TypeError):rejected.append(label)
        else:raise AssertionError("unsafe producer input accepted: "+label)
    return {"passed": True, "complete_files": records, "exact_stdin_cases": captures,"rejected":rejected,
            "complete_file_reproduction_policy":"legacy-pipe control for all three codecs",
            "stdin_fixture_policy":"prepared-W1-W2-seek" if PREPARED else "legacy-pipe",
            "reap_contract":"all waitid use WNOWAIT; initial blocking exit observation precedes group drain; only p.wait follows drain; no communicate/poll"}


RUST = r'''use std::{env,io::{self,BufRead}};
fn main(){let args:Vec<_>=env::args().collect();let stdin=io::stdin();let mut lines=stdin.lock().lines();
let first=lines.next().unwrap().unwrap();
println!("{}|{}|{}|{}|{}|{}|{}",args[1],args[2],args[3],option_env!("ROVE_WORKERS").unwrap(),env::var("ROVE_WORKERS").unwrap(),env::var("R4_STREAM_TEST").unwrap(),first);
let _=lines.next();std::process::exit(17);}
'''.encode()


def actual_rust(producer, out, codec, rustc):
    control = out / "control"
    control.mkdir()
    env = os.environ.copy()
    env["PATH"] = str(Path(rustc).parent) + os.pathsep + env.get("PATH", "")
    compile_env = dict(env, **FIXED)
    built = subprocess.run(COMMAND, input=RUST, cwd=control, env=compile_env, capture_output=True, timeout=60)
    save(control / "compile.json", {"command": COMMAND, "returncode": built.returncode,
          "stdout": built.stdout.decode(errors="replace"), "stderr": built.stderr.decode(errors="replace"), "source_sha256": sha(RUST)})
    assert built.returncode == 0, built.stderr
    expected = sha((control / "x").read_bytes())
    path, scratch, environment, metadata = emit(producer, out / "native", RUST, COMMAND, codec)
    environment.update(PATH=env["PATH"], ROVE_WORKERS="999", ROVE_TT_BITS="7", R4_STREAM_TEST="environment")
    process = subprocess.Popen([str(path), "two words", "", "한글-'quoted'"], env=environment,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc = Path("/proc") / str(process.pid)
    start = (proc / "stat").read_text().rsplit(")",1)[1].split()[19]
    try:
        process.stdin.write(b"standard input queued during compilation\n")
        process.stdin.flush()
        observed = line(process)
        assert observed == "two words||한글-'quoted'|2|999|environment|standard input queued during compilation\n".encode(), observed
        assert process.poll() is None
        assert not list(scratch.iterdir()), "private compiler scratch survived native readiness"
        image = (proc / "exe").read_bytes()
        assert image[:4] == b"\x7fELF" and sha(image) == expected, "fdexec image is not independently built stdin image"
        assert os.readlink(proc / "exe").endswith("/x (deleted)")
        status = dict(v.split(":",1) for v in (proc / "status").read_text().splitlines())
        assert int(status["PPid"]) == os.getpid()
        assert (proc / "stat").read_text().rsplit(")",1)[1].split()[19] == start
        task_ids = sorted(p.name for p in (proc / "task").iterdir())
        for task in task_ids:
            assert not (proc / "task" / task / "children").read_text().strip(), "compiler/helper process survived exec"
        process.stdin.write(b"finish\n");process.stdin.flush()
        assert process.wait(timeout=5) == 17
        assert process.stderr.read() == b""
        return {"passed": True, "codec": codec, "program_sha256": expected, "source_sha256": sha(RUST),
                "launcher_pid": process.pid, "process_starttime": start, "task_ids": task_ids,
                "native_stdout": observed.decode(), "exitstatus":17, "metadata":metadata}
    finally:
        close(process)


def failure_contract(producer, out, codec):
    results = []
    for label, command in (("missing", ["/r4-missing-compiler/rustc"]),
                           ("missing-output", [sys.executable,"-c","raise SystemExit(0)"])):
        path, scratch, env, _ = emit(producer, out / label, b"fn main(){}", command, codec)
        result = subprocess.run([str(path)], env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=8)
        assert result.returncode != 0 and b"FileNotFoundError" in result.stderr
        assert b"AttributeError" not in result.stderr and b"During handling" not in result.stderr
        assert not list(scratch.iterdir())
        results.append({"case":label,"returncode":result.returncode,"stderr":result.stderr.decode()})
    command=[sys.executable,"-c","import os,signal;signal.signal(signal.SIGTERM,signal.SIG_DFL);os.kill(os.getpid(),signal.SIGTERM)"]
    path,scratch,env,_=emit(producer,out/"compiler-signal",b"fn main(){}",command,codec)
    result=subprocess.run([str(path)],env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=8)
    assert result.returncode==143 and not list(scratch.iterdir()),(result.returncode,result.stderr)
    results.append({"case":"compiler-self-sigterm","returncode":result.returncode})
    local=out/"leader-exit";local.mkdir()
    child_ready=local/"child-ready.json"
    child=local/"child.py"
    child.write_text("import json,os,signal,time\nfrom pathlib import Path\n"
                     "signal.signal(15,signal.SIG_IGN)\n"
                     f"Path({str(child_ready)!r}).write_text(json.dumps({{'pid':os.getpid(),'group':os.getpgrp(),'TMPDIR':os.environ['TMPDIR']}}))\n"
                     "while True:time.sleep(30)\n")
    compiler=local/"compiler.py"
    compiler.write_text("import subprocess,sys,time\nfrom pathlib import Path\n"
                       f"subprocess.Popen([sys.executable,{str(child)!r}])\n"
                       f"while not Path({str(child_ready)!r}).exists():time.sleep(.005)\n"
                       "raise SystemExit(23)\n")
    path,scratch,env,_=emit(producer,local/"launcher-test",b"fn main(){}",[sys.executable,str(compiler)],codec)
    try:
        result=run_owned([str(path)],env=env,timeout=12)
        identity=json.loads(child_ready.read_text())
        stat=Path('/proc')/str(identity['pid'])/'stat'
        assert result.returncode==23 and (not stat.exists() or stat.read_text().rsplit(')',1)[1].split()[0]=='Z')
        assert not Path(identity['TMPDIR']).exists() and not list(scratch.iterdir())
        results.append({"case":"exited-leader-live-grandchild","returncode":result.returncode,"child":identity,"no_live_group_member_before_cleanup":True})
    finally:
        # run_owned already settled the original wrapper before its final reap;
        # its compiler-group assertion above is an observation, not kill authority.
        pass
    return {"passed":True,"cases":results}


def inherited_sigchld_contract(producer,out,codec):
    """Preserve Python-entry disposition; the shebang shell can normalize it."""
    probe="import signal;print(int(signal.getsignal(signal.SIGCHLD)))"
    check=subprocess.run(['/bin/sh','-c','exec '+shlex.quote(sys.executable)+' -c '+shlex.quote(probe)],
          preexec_fn=lambda:signal.signal(signal.SIGCHLD,signal.SIG_IGN),capture_output=True,text=True,timeout=5)
    assert check.returncode==0
    shell_entry=int(check.stdout.strip())
    control=out/'control/x'
    cases=[]
    for entry,expected in (('whole-artifact',shell_entry),('direct-Python-decoder',int(signal.SIG_IGN))):
        fixture=out/('sigchld-'+entry);fixture.mkdir()
        observed=fixture/'compiler.json';compiler=fixture/'compiler.py'
        compiler.write_text("import hashlib,json,os,shutil,signal,sys\nfrom pathlib import Path\n"
            "data=sys.stdin.buffer.read()\n"
            f"shutil.copyfile({str(control)!r},'x');os.chmod('x',0o755)\n"
            f"Path({str(observed)!r}).write_text(json.dumps({{'sigchld':int(signal.getsignal(signal.SIGCHLD)),'source_sha256':hashlib.sha256(data).hexdigest(),'TMPDIR':os.environ['TMPDIR']}}))\n")
        path,scratch,env,metadata=emit(producer,fixture/'launcher-test',RUST,[sys.executable,str(compiler)],codec)
        env.update(ROVE_WORKERS='999',R4_STREAM_TEST='environment')
        arguments=[str(path),'two words','',"한글-'quoted'"]
        if entry=='direct-Python-decoder':
            prefix=path.read_bytes()[:metadata['stub_bytes']].decode().splitlines()[1]
            tokens=shlex.split(prefix)
            assert tokens[:3]==['exec','python3','-c'] and tokens[-2:]==['$0','$@']
            arguments=[sys.executable,'-c',tokens[3],*arguments]
        process=subprocess.Popen(arguments,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                 preexec_fn=lambda:signal.signal(signal.SIGCHLD,signal.SIG_IGN))
        try:
            process.stdin.write(b'standard input queued during compilation\n');process.stdin.flush()
            stdout=line(process,10)
            assert stdout=="two words||한글-'quoted'|2|999|environment|standard input queued during compilation\n".encode(),stdout
            actual=json.loads(observed.read_text())
            assert actual['sigchld']==int(signal.SIG_DFL) and actual['source_sha256']==sha(RUST)
            proc=Path('/proc')/str(process.pid)
            status=dict(item.split(':',1) for item in (proc/'status').read_text().splitlines())
            ignored=bool(int(status['SigIgn'].strip(),16)&(1<<(int(signal.SIGCHLD)-1)))
            assert ignored==(expected==int(signal.SIG_IGN)),"Python-entry SIGCHLD disposition was not restored for native exec"
            assert sha((proc/'exe').read_bytes())==sha(control.read_bytes())
            assert not Path(actual['TMPDIR']).exists() and not list(scratch.iterdir())
            process.stdin.write(b'finish\n');process.stdin.flush();assert process.wait(timeout=5)==17
            assert process.stderr.read()==b''
            cases.append({'entry':entry,'compiler_sigchld':actual['sigchld'],'expected_Python_entry_sigchld':expected,
                          'engine_SigIgn':status['SigIgn'].strip(),'engine_sigchld_restored':True,'returncode':process.returncode})
        finally:close(process)
    return {'passed':True,'scope':'restores disposition at Python decoder entry; shebang shell normalization is observed independently',
            'shell_entry_sigchld':shell_entry,'source_sha256':sha(RUST),'cases':cases}


def signal_contract(producer, out, codec):
    results = []
    for sig in (signal.SIGTERM, signal.SIGINT):
        local = out / f"signal-{int(sig)}"
        local.mkdir()
        ready=local/"ready.json"; child_ready=local/"child-ready"; parent_signal=local/"parent-signal"; child_signal=local/"child-signal"; waited=local/"waited"
        child=local/"child.py"
        child.write_text("import os,signal,time\nfrom pathlib import Path\n"
             f"def stop(s,f):\n Path({str(child_signal)!r}).write_text(str(s))\n raise SystemExit(0)\n"
             "signal.signal(2,stop);signal.signal(15,stop)\n"
             f"Path({str(child_ready)!r}).write_text(str(os.getpid()))\nwhile True:time.sleep(30)\n")
        compiler=local/"compiler.py"
        compiler.write_text("import json,os,signal,subprocess,sys,time\nfrom pathlib import Path\nchild=None\n"
             f"def stop(s,f):\n Path({str(parent_signal)!r}).write_text(str(s))\n code=child.wait(timeout=3)\n Path({str(waited)!r}).write_text(str(code))\n raise SystemExit(0)\n"
             "signal.signal(2,stop);signal.signal(15,stop)\n"
             f"child=subprocess.Popen([sys.executable,{str(child)!r}])\n"
             f"while not Path({str(child_ready)!r}).exists():time.sleep(.005)\n"
             f"Path({str(ready)!r}).write_text(json.dumps({{'pid':os.getpid(),'child':child.pid,'group':os.getpgrp(),'TMPDIR':os.environ['TMPDIR'],'cwd':os.getcwd(),'mode':os.stat(os.getcwd()).st_mode&511}}))\n"
             "while True:time.sleep(30)\n")
        path,scratch,env,_=emit(producer,local/"launcher-test",b"fn main(){}",[sys.executable,str(compiler)],codec)
        process=start_owned([str(path)],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        identity=None
        try:
            until=time.monotonic()+8
            while not ready.exists() and time.monotonic()<until and not host_owner().exited_unreaped(process):time.sleep(.01)
            assert ready.exists(),"compiler group did not become ready"
            identity=json.loads(ready.read_text())
            assert identity['group']==identity['pid'] and os.getpgid(identity['child'])==identity['group']
            assert identity['cwd']==identity['TMPDIR'] and Path(identity['TMPDIR']).parent==scratch and identity['mode']==0o700
            os.kill(process.pid,sig)
            assert finish_owned(process,8)==128+int(sig)
            assert parent_signal.read_text()==str(int(sig)) and child_signal.read_text()==str(int(sig)) and waited.read_text()=="0"
            assert not Path(identity['TMPDIR']).exists() and not list(scratch.iterdir())
            assert no_process(identity['pid']) and no_process(identity['child'])
            assert process.stderr.read()==b""
            results.append({"signal":int(sig),"returncode":process.returncode,"identity":identity,"passed_before_emergency_cleanup":True})
        finally:
            close(process)
    return {"passed":True,"scope":"cooperative compiler and grandchild group during compile; decoder stage is separate","cases":results}


def main():
    raise SystemExit("Rust A is retired; this historical stream/compiler test CLI is disabled.")
    global COMMAND,PREPARED
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--codec",choices=("xz","gzip","bzip2"),default="xz")
    parser.add_argument("--rustc",default=os.environ.get("RUSTC","rustc"))
    parser.add_argument("--prepared-input",action="store_true")
    args=parser.parse_args();out=args.out.resolve()
    if out==ROOT or ROOT in out.parents:parser.error("external output required")
    if sys.platform!="linux":parser.error("Linux /proc and shell lifecycle checks required")
    rustc=shutil.which(args.rustc)
    if rustc is None:parser.error("Rust compiler required")
    out.mkdir(parents=True,exist_ok=False);producer=module();COMMAND=list(producer.COMMAND);PREPARED=args.prepared_input
    report={"passed":False,"scope":"byte reproduction allcodecs; selectedcodec realRust and compilegroup lifecycle","checks":{}}
    def interrupted(signum,frame):raise InterruptedError('Rust stream fixture signal '+str(signum))
    saved={sig:signal.signal(sig,interrupted) for sig in (signal.SIGINT,signal.SIGTERM)}
    previous_chld=signal.signal(signal.SIGCHLD,signal.SIG_DFL)
    try:
        report['checks']['bytes']=byte_contract(producer,out)
        report['checks']['rust']=actual_rust(producer,out,args.codec,rustc)
        report['checks']['inherited_sigchld']=inherited_sigchld_contract(producer,out,args.codec)
        report['checks']['failures']=failure_contract(producer,out,args.codec)
        report['checks']['signals']=signal_contract(producer,out,args.codec)
        assert _HOST is not None and not _HOST.owned
        assert all(row.get('terminal') and row.get('reaped') and row.get('owned_group_absent')
                   and not row['forced_cleanup'] for row in HOST_COMMANDS)
        report['passed']=True
    except Exception as error:
        report['error']=f"{type(error).__name__}: {error}";raise
    finally:
        try:
            if _HOST is not None:
                for process in list(_HOST.owned):close(process)
                report['remaining_owned_handles']=len(_HOST.owned)
            report['host_commands']=HOST_COMMANDS
            save(out/'report.json',report)
        finally:
            signal.signal(signal.SIGCHLD,previous_chld)
            for sig,handler in saved.items():signal.signal(sig,handler)
    print(out/'report.json')


if __name__=="__main__":main()
