#!/usr/bin/env python3
"""Explicit separate fault images, never production hooks or release artifacts.

Each image copies a pinned build's source and exact compiler recipe. Only os.rs
changes, with its original/new hash and full diff retained. Original failure
handling function bodies remain after a small syscall-return shim, except the
second raw-clone fixture which returns -EAGAIN before the actual clone syscall.
Own-child ptrace records real clone and exit_group cleanup of each fault image.
"""

if __name__ == "__main__":
    raise SystemExit("Rove4k Rust engine paths are retired; use C A-F")

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE/"tests"))
from verify_runtime import check,digest,pin,save
from runtime_trace import ptrace,preexec,info,SETOPTIONS,OPTIONS,GETEVENTMSG,SYSCALL,WALL
import ctypes

FAULTS={
    "mmap_enomem":("if n==9{return -12;}\n",111),
    "guard_mprotect_eacces":("if n==10{return -13;}\n",114),
    "clock_eio":("if n==228{return -5;}\n",119),
    "worker_clock_eio":('if n==228{let tid:isize;let pid:isize;unsafe{core::arch::asm!("syscall",inlateout("rax")186usize=>tid,lateout("rcx")_,lateout("r11")_,options(nostack));core::arch::asm!("syscall",inlateout("rax")39usize=>pid,lateout("rcx")_,lateout("r11")_,options(nostack));}if tid!=pid{return -5;}}\n',119),
    "read_eio":("if n==0{return -5;}\n",121),
    "wait_einval":("if n==202&&b==128{return -22;}\n",116),
    "write_eio":("if n==1{return -5;}\n",120),
    "munmap_einval":("if n==11{return -22;}\n",112),
    "write_short":("let c=if n==1{c.min(3)}else{c};\n",0),
    "read_eintr_once":("static ONCE:core::sync::atomic::AtomicU32=core::sync::atomic::AtomicU32::new(0);if n==0&&ONCE.fetch_add(1,Ordering::Relaxed)==0{return -4;}\n",0),
    "write_eintr_once":("static ONCE:core::sync::atomic::AtomicU32=core::sync::atomic::AtomicU32::new(0);if n==1&&ONCE.fetch_add(1,Ordering::Relaxed)==0{return -4;}\n",0),
    "second_clone_eagain":("",115),
    "lower_guard_segv":("",-11),
    "upper_guard_segv":("",-11),
}

def transformed(original,name):
    if name.endswith("guard_segv"):return original
    if name=="second_clone_eagain":
        anchor="raw_spawn:\n";check(original.count(anchor)==1,"raw_spawn fixture anchor")
        text=original.replace(anchor,anchor+"    lock inc dword ptr [rip+fault_clone_count]\n    cmp dword ptr [rip+fault_clone_count],2\n    jne 9f\n    mov rax,-11\n    ret\n9:\n")
        anchor='.section .note.GNU-stack,"",@progbits'
        check(text.count(anchor)==1,"counter fixture anchor")
        return text.replace(anchor,'.section .bss.fault,"aw",@nobits\n.balign 4\nfault_clone_count:\n.long 0\n'+anchor)
    anchor="    let result:isize;\n";check(original.count(anchor)==1,"syscall fixture anchor")
    return original.replace(anchor,"    "+FAULTS[name][0]+anchor)

def observe(image,out,expected,worker_stage=False):
    events=[];alive=set();reaped={};active={};selector=selectors.DefaultSelector();stdout=b"";stderr=b"";start=time.monotonic()
    p=subprocess.Popen([str(image)],cwd=out,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        start_new_session=True,preexec_fn=preexec,bufsize=0)
    alive.add(p.pid);report={"image_class":"separate injected syscall/raw-clone fault image","pid":p.pid,"expected_status":expected,"passed":False};worker_go=False
    def resume(tid,sig=0):
        try:ptrace(SYSCALL,tid,0,sig)
        except ProcessLookupError:pass
    def add(event):
        check(len(events)<200000,"fault syscall event cap exceeded");events.append(event)
    try:
        _,status=os.waitpid(p.pid,0);check(os.WIFSTOPPED(status),"fixture exec trap")
        ptrace(SETOPTIONS,p.pid,0,OPTIONS)
        for name,stream in(("stdout",p.stdout),("stderr",p.stderr)):
            os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,name)
        p.stdin.write(b"uci\nisready\n"if worker_stage else b"uci\nisready\ngo wtime 30\nquit\n");p.stdin.flush();resume(p.pid)
        while alive:
            check(time.monotonic()-start<12,"fault image deadline")
            for key,_ in selector.select(0):
                chunk=os.read(key.fileobj.fileno(),65536)
                if not chunk:selector.unregister(key.fileobj);continue
                if key.data=="stdout":stdout+=chunk
                else:stderr+=chunk
                check(len(stdout)+len(stderr)<65536,"fault output cap")
            if worker_stage and not worker_go and b"readyok\n"in stdout:
                tids=sorted(int(x.name)for x in Path(f"/proc/{p.pid}/task").iterdir());check(len(tids)==3,"worker fault did not reach three startup TIDs")
                report["startup_tids_before_fault_go"]=tids;p.stdin.write(b"go wtime 1000000\n");p.stdin.flush();worker_go=True
            tid,status=os.waitpid(-1,os.WNOHANG|WALL)
            if tid==0:time.sleep(.0005);continue
            if os.WIFEXITED(status)or os.WIFSIGNALED(status):
                code=os.WEXITSTATUS(status)if os.WIFEXITED(status)else-os.WTERMSIG(status)
                reaped[tid]=code;alive.discard(tid);add({"kind":"reaped","tid":tid,"status":code});continue
            check(os.WIFSTOPPED(status),"fault wait status");sig=os.WSTOPSIG(status);event=status>>16
            if event==3:
                data=ctypes.c_ulong()
                try:ptrace(GETEVENTMSG,tid,0,ctypes.addressof(data))
                except ProcessLookupError:add({"kind":"exit_group_raced_event_read","tid":tid});continue
                alive.add(data.value)
                add({"kind":"clone_child","tid":tid,"child":data.value});resume(tid);continue
            if event==6:add({"kind":"exit_event","tid":tid});resume(tid);continue
            if sig==signal.SIGSTOP:
                alive.add(tid)
                try:ptrace(SETOPTIONS,tid,0,OPTIONS)
                except ProcessLookupError:add({"kind":"exit_group_raced_option_set","tid":tid});continue
                resume(tid);continue
            if sig==(signal.SIGTRAP|0x80):
                try:kind,n,args=info(tid)
                except ProcessLookupError:add({"kind":"exit_group_raced_syscall_read","tid":tid});continue
                if kind=="entry":add({"kind":"syscall_entry","tid":tid,"number":n,"args":args});active[tid]=n
                elif kind=="exit":add({"kind":"syscall_exit","tid":tid,"number":active.pop(tid,None),"result":n})
                resume(tid);continue
            event_data={"kind":"delivered_signal","tid":tid,"signal":sig}
            if sig==signal.SIGSEGV:
                data=ctypes.create_string_buffer(128);ptrace(0x4202,tid,0,ctypes.addressof(data))
                import struct
                event_data["fault_address"]=struct.unpack_from("<Q",data.raw,16)[0]
            add(event_data);resume(tid,0 if sig==signal.SIGTRAP else sig)
        p.returncode=reaped[p.pid]
        drain=time.monotonic()+1
        while selector.get_map()and time.monotonic()<drain:
            for key,_ in selector.select(.01):
                chunk=os.read(key.fileobj.fileno(),65536)
                if not chunk:selector.unregister(key.fileobj);continue
                if key.data=="stdout":stdout+=chunk
                else:stderr+=chunk
                check(len(stdout)+len(stderr)<65536,"fault final pipe-drain output cap")
        check(not selector.get_map(),"fault pipes did not reach EOF")
        check(reaped[p.pid]==expected,f"wrong fault status {reaped}")
        check(not stderr,"fault stderr")
        for tid in reaped:check(not Path(f"/proc/{tid}").exists(),"fault left a task")
        exitgroups=[e for e in events if e["kind"]=="syscall_entry"and e["number"]==231]
        if expected>=0:check(exitgroups and exitgroups[-1]["args"][0]==expected,"failure did not reach expected exit_group")
        else:check(any(e["kind"]=="delivered_signal"and e["signal"]==-expected for e in events),"expected guard fault signal not observed")
        if expected==0:check(b"uciok\n"in stdout and b"readyok\n"in stdout and stdout.count(b"bestmove ")==1,"retry/short-write protocol")
        if worker_stage:check(worker_go and exitgroups[-1]["tid"]!=p.pid,"clock failure occurred on main rather than worker")
        report.update(passed=True,reaped=reaped,exit_group=exitgroups[-1]if exitgroups else None,stdout=stdout.decode(),stderr=stderr.decode(),
            clone_children=[e["child"]for e in events if e["kind"]=="clone_child"])
    except BaseException as error:report["error"]={"type":type(error).__name__,"message":str(error)};raise
    finally:
        if alive:
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            until=time.monotonic()+3
            while alive and time.monotonic()<until:
                try:tid,status=os.waitpid(-1,os.WNOHANG|WALL)
                except ChildProcessError:break
                if tid:
                    if os.WIFEXITED(status)or os.WIFSIGNALED(status):alive.discard(tid)
                    elif os.WIFSTOPPED(status):resume(tid,signal.SIGKILL)
                else:time.sleep(.002)
            report["cleanup_unreaped_tids"]=sorted(alive)
        selector.close()
        for stream in(p.stdin,p.stdout,p.stderr):stream.close()
        save(out/"events.json",events);save(out/"observation.json",report)
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--image",type=Path,required=True);ap.add_argument("--out",type=Path,required=True);a=ap.parse_args()
    image=a.image.resolve();root=a.out.resolve();check(sys.platform=="linux"and a.out.is_absolute()and not root.exists(),"new absolute Linux output required")
    production=pin(image,"hq");build=json.loads((image.parent.parent/"build.json").read_text());root.mkdir()
    (root/"runtime_faults.py").write_bytes(Path(__file__).read_bytes());(root/"runtime_trace.py").write_bytes((HERE/"tests/runtime_trace.py").read_bytes())
    report={"production_pin":production,"scope":"separate explicit fault images, not production ELF runtime identity","verifier_sha256":digest(__file__),"trace_helper_sha256":digest(HERE/"tests/runtime_trace.py"),"passed":False,"fixtures":{}}
    original_bytes=(image.parent/"os.rs").read_bytes();original=original_bytes.decode().replace("\r\n","\n")
    eol="\r\n"if b"\r\n"in original_bytes else"\n";environment=os.environ.copy();environment.update(build["compiler_environment"])
    try:
        for name,(_,expected)in FAULTS.items():
            local=root/name;local.mkdir();changed=transformed(original,name)
            for filename in build["source_sha256"]:(local/filename).write_bytes((image.parent/filename).read_bytes())
            (local/"os.rs").write_bytes(changed.replace("\n",eol).encode())
            (local/"source.diff").write_text("".join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile="production/os.rs",tofile="fault/os.rs")))
            if name.endswith("guard_segv"):
                offset="0"if name.startswith("lower")else"os::STACK_MAP-1"
                driver='''#![no_std]
#![no_main]
mod os;
use core::sync::atomic::AtomicI32;
static TID:AtomicI32=AtomicI32::new(0);
#[panic_handler]fn panic(_:&core::panic::PanicInfo)->!{os::fatal(134)}
#[unsafe(no_mangle)]extern "C" fn worker_entry(p:*mut u8){unsafe{core::arch::asm!("mov byte ptr [{0}],1",in(reg)p,options(nostack));}os::fatal(200)}
#[unsafe(no_mangle)]extern "C" fn engine_main()->!{let base=os::stack();unsafe{os::spawn(base,&TID,base.add(OFFSET));}os::join(&TID);os::fatal(201)}
'''.replace("OFFSET",offset)
                (local/"main.rs").write_text(driver)
                check(digest(local/"os.rs")==production["source_sha256"]["os.rs"],"guard probe altered production os.rs")
                (local/"driver.diff").write_text("".join(difflib.unified_diff((image.parent/"main.rs").read_text().splitlines(True),driver.splitlines(True),fromfile="production/main.rs",tofile="guard-probe/main.rs")))
            command=list(build["builds"][0]["command"]);command[2]=str(local)+"=."
            result=subprocess.run(command,cwd=local,env=environment,capture_output=True,text=True,timeout=120)
            entry={"class":"separate fault image","compile_command":command,"compile_returncode":result.returncode,"compile_stdout":result.stdout,"compile_stderr":result.stderr,
                "production_os_sha256":production["source_sha256"]["os.rs"],"fault_os_sha256":digest(local/"os.rs"),"diff":str(local/"source.diff")}
            if name.endswith("guard_segv"):entry.update(classification="separate hardware guard-page probe; exact production os.rs",driver_sha256=digest(local/"main.rs"),driver_diff=str(local/"driver.diff"))
            report["fixtures"][name]=entry;check(result.returncode==0,"fault fixture compile failed: "+name)
            entry["native_sha256"]=digest(local/"x");entry["observation"]=observe(local/"x",local,expected,name=="worker_clock_eio")
            if name=="clock_eio":check(not entry["observation"]["clone_children"],"startup clock failure accidentally occurred after clones")
            if name=="second_clone_eagain":check(len(entry["observation"]["clone_children"])==1,"partial-clone fixture did not create exactly one prior child")
            if name=="write_short":
                events=json.loads((local/"events.json").read_text());writes=[e for e in events if e["kind"]=="syscall_exit"and e["number"]==1]
                check(len(writes)>10 and all(0<e["result"]<=3 for e in writes),"short writes not actually exercised")
            if name.endswith("guard_segv"):
                events=json.loads((local/"events.json").read_text())
                base=next(e["result"]for e in events if e["kind"]=="syscall_exit"and e["number"]==9)
                address=next(e["fault_address"]for e in events if e["kind"]=="delivered_signal"and e["signal"]==11)
                expected_address=base+(0 if name.startswith("lower")else 1024*1024+8192-1)
                check(address==expected_address,"guard SIGSEGV address differs from protected page")
                entry.update(mapped_base=base,actual_sigsegv_address=address)
        report["passed"]=True
    except BaseException as error:report["error"]={"type":type(error).__name__,"message":str(error)};raise
    finally:save(root/"faults.json",report)
    print(json.dumps({"passed":True,"fixtures":len(FAULTS),"report":str(root/"faults.json")}))
if __name__=="__main__":main()
