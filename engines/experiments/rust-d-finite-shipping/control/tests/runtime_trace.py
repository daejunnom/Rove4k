#!/usr/bin/env python3
"""Own-child-only x86-64 ptrace receipts for the unchanged production ELF.

No ptrace attach, other process inspection, production hook or image rewrite.
The tracer deliberately parks worker EXIT events until the main thread has
entered shared clear-TID futex join. This schedule is recorded in the evidence.
"""
import argparse
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import struct
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from verify_runtime import check,digest,guarded,pin,save

libc=ctypes.CDLL(None,use_errno=True)
libc.ptrace.restype=ctypes.c_long
libc.ptrace.argtypes=(ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_void_p)
TRACEME=0;PEEK=2;SYSCALL=24;SETOPTIONS=0x4200;GETEVENTMSG=0x4201;GETINFO=0x420e
OPTIONS=1|8|64|0x100000 # TRACESYSGOOD, TRACECLONE, TRACEEXIT, EXITKILL
WALL=0x40000000
NAMES={0:"read",1:"write",9:"mmap",10:"mprotect",11:"munmap",12:"brk",35:"nanosleep",56:"clone",60:"exit",202:"futex",228:"clock_gettime",231:"exit_group"}

def ptrace(request,tid,a=0,b=0):
    ctypes.set_errno(0)
    value=libc.ptrace(request,tid,ctypes.c_void_p(a),ctypes.c_void_p(b))
    error=ctypes.get_errno()
    if value==-1 and error:raise OSError(error,os.strerror(error))
    return value
def preexec():
    if libc.ptrace(TRACEME,0,None,None)<0:os._exit(123)
def info(tid):
    data=ctypes.create_string_buffer(128);n=ptrace(GETINFO,tid,128,ctypes.addressof(data));raw=data.raw
    check(n>=24,"kernel lacks PTRACE_GET_SYSCALL_INFO")
    if raw[0]==1:return ("entry",struct.unpack_from("<Q",raw,24)[0],list(struct.unpack_from("<6Q",raw,32)))
    if raw[0]==2:return ("exit",struct.unpack_from("<q",raw,24)[0],[])
    return ("other",raw[0],[])
def memory(tid,address,count):
    output=bytearray()
    for at in range(0,count,8):output+=struct.pack("<Q",ptrace(PEEK,tid,address+at)&((1<<64)-1))
    return bytes(output[:count])
def value32(tid,address):return struct.unpack("<I",memory(tid,address,4))[0]

def diagnostic_pin(image):
    report=json.loads((image.parent/"report.json").read_text())
    check(digest(image)==report["actual_executed_elf_sha256"],"diagnostic ELF pin mismatch")
    check(digest(image.parent/"main.rs")==report["driver_sha256"],"diagnostic driver changed")
    for name,value in report["production_source_sha256"].items():
        production=(HERE/name).read_bytes();check(hashlib.sha256(production).hexdigest()==value,"diagnostic production pin mismatch "+name)
        data=(image.parent/name).read_bytes()
        check(data.startswith(production),"diagnostic changed production component "+name)
        if name=="search.rs":check(hashlib.sha256(data[len(production):]).hexdigest()==report["appendix_sha256"],"diagnostic appendix mismatch")
        else:check(data==production,"diagnostic extra component bytes "+name)
    return {"path":str(image),"sha256":digest(image),"class":"separate raw no_std deep-path diagnostic; not shipping whole image", "origin_report":report}

def trace(image,out,diagnostic=False):
    input_pin=diagnostic_pin(image)if diagnostic else pin(image,"scalar"if"scalar"in str(image)else"hq")
    out=Path(out);out.mkdir();(out/"runtime_trace.py").write_bytes(Path(__file__).read_bytes())
    events=[];children={};active={};alive=set();held={};joining={};reaped={};output=b"";errors=b""
    selector=selectors.DefaultSelector();start=time.monotonic();phase="startup";boundary=None;stop_at=None;quit_sent=False
    parked_write=None;finished_wait_address=None;finished_expected_old=None;best_entries=0
    output_gate=None;output_waiting_wake={};before_write_states=[];after_write_states=[];last_best_writer=None
    p=subprocess.Popen([str(image)],cwd=out,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        start_new_session=True,preexec_fn=preexec,bufsize=0)
    leader=p.pid;alive.add(leader);report={"pin":input_pin,"tracer_sha256":digest(__file__),"pid":leader,"passed":False}
    def record(kind,tid,**fields):
        check(len(events)<200000,"syscall event cap exceeded")
        row={"index":len(events),"elapsed":time.monotonic()-start,"kind":kind,"tid":tid,**fields};events.append(row);return row
    def command(text):p.stdin.write(text.encode());p.stdin.flush();record("command",leader,text=text)
    def resume(tid,sig=0):
        try:ptrace(SYSCALL,tid,0,sig)
        except OSError as e:
            if e.errno!=errno.ESRCH:raise
    def before_best_write(tid):
        check(finished_wait_address is not None and finished_expected_old is not None,"no main finished wait state")
        check(output_gate is not None and output_gate!=finished_wait_address,"finished address aliases OUTPUT gate")
        observed=value32(tid,finished_wait_address);gate=value32(tid,output_gate)
        check(observed==finished_expected_old,"finished generation published before physical bestmove write")
        check(gate==1,"bestmove writer does not own OUTPUT gate")
        before_write_states.append(record("atomic_state_before_best_write",tid,finished_address=finished_wait_address,
            expected_old=finished_expected_old,observed=observed,output_gate=output_gate,output_gate_value=gate))
    try:
        tid,status=os.waitpid(leader,0);check(os.WIFSTOPPED(status),"no initial exec trap")
        check(os.readlink(f"/proc/{leader}/exe")==str(Path(image).resolve()),"trace target /proc/exe differs")
        ptrace(SETOPTIONS,leader,0,OPTIONS)
        for name,stream in (("stdout",p.stdout),("stderr",p.stderr)):
            os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,name)
        resume(leader)
        if not diagnostic:command("uci\nisready\n")
        while alive:
            check(time.monotonic()-start<25,"trace deadline exceeded")
            for key,_ in selector.select(0):
                chunk=os.read(key.fileobj.fileno(),65536)
                if not chunk:selector.unregister(key.fileobj);continue
                if key.data=="stdout":output+=chunk
                else:errors+=chunk
                check(len(output)+len(errors)<1024*1024,"trace output cap exceeded")
            if phase=="startup"and (b"deep begin\n"if diagnostic else b"readyok\n")in output:
                tasks=sorted(int(x.name)for x in Path(f"/proc/{leader}/task").iterdir());check(len(tasks)==(2 if diagnostic else 3),"trace startup threads")
                maps=Path(f"/proc/{leader}/maps").read_text();save(out/"startup.json",{"tasks":tasks,"guard_stacks":guarded(maps)})
                (out/"startup-maps.txt").write_text(maps);check(len(guarded(maps))==(1 if diagnostic else 2),"trace guard stacks")
                boundary=len(events);phase="deep"if diagnostic else"clock"
                if not diagnostic:command("position startpos\ngo wtime 600\n")
            if diagnostic and b"deep nodes 128\n"in output:quit_sent=True
            bests=output.count(b"bestmove ")
            if phase=="clock"and bests==1:phase="infinite";command("go infinite\n");stop_at=time.monotonic()+.04
            if phase=="infinite"and stop_at and time.monotonic()>=stop_at:phase="stop";command("stop\n")
            if phase=="stop"and bests==2:phase="quit";command("quit\n");quit_sent=True
            # A held EXIT event keeps clear_child_tid nonzero. Release only
            # after main has resumed into the matching shared futex WAIT.
            for child,when in list(held.items()):
                if child in joining and time.monotonic()>=joining[child]+.01:
                    text=Path(f"/proc/{leader}/syscall").read_text().strip()
                    fields=text.split();check(len(fields)>=4,"main is not in shared join syscall")
                    check([int(n,0)for n in fields[:4]]==[202,children[child]["child_tid_address"],0,child],"main is not blocked on matching shared clear-TID wait")
                    observed=value32(child,children[child]["child_tid_address"]);check(observed==child,"held child TID is not still positive before kernel exit")
                    record("release_worker_exit",child,main_syscall=text,tid_before_clear=observed)
                    resume(child);del held[child]
            tid,status=os.waitpid(-1,os.WNOHANG|WALL)
            if tid==0:time.sleep(.0005);continue
            check(tid in alive or os.WIFSTOPPED(status),"waited for an unrelated process")
            if os.WIFEXITED(status)or os.WIFSIGNALED(status):
                code=os.WEXITSTATUS(status)if os.WIFEXITED(status)else-os.WTERMSIG(status)
                record("reaped",tid,status=code);reaped[tid]=code;alive.discard(tid);continue
            check(os.WIFSTOPPED(status),"unexpected wait status")
            sig=os.WSTOPSIG(status);event=status>>16
            if event==3:
                data=ctypes.c_ulong();ptrace(GETEVENTMSG,tid,0,ctypes.addressof(data));child=data.value
                args=active[tid]["args"];children[child]={"parent_tid_address":args[2],"child_tid_address":args[3],"child_stack_pointer":args[1],"stack_top":args[1]+16}
                alive.add(child);record("clone_child",tid,child=child,**children[child]);resume(tid);continue
            if event==6:
                record("exit_event",tid)
                if tid!=leader and quit_sent:
                    children[tid]["last_tid_value"]=value32(tid,children[tid]["child_tid_address"])
                    check(children[tid]["last_tid_value"]==tid,"TID cleared before held exit event")
                    held[tid]=time.monotonic();continue
                resume(tid);continue
            if sig==signal.SIGSTOP:
                ptrace(SETOPTIONS,tid,0,OPTIONS);resume(tid);continue
            if sig==signal.SIGTRAP|0x80:
                kind,n,args=info(tid)
                if kind=="entry":
                    fields={"number":n,"name":NAMES.get(n,str(n)),"args":args}
                    if n==1 and args[0]==1:fields["data"]=memory(tid,args[1],min(args[2],4096)).decode(errors="replace")
                    row=record("syscall_entry",tid,**fields);active[tid]=row
                    if n==202 and args[1]==128 and tid==leader and phase=="stop":
                        finished_wait_address=args[0];finished_expected_old=args[2]
                        if parked_write is not None:before_best_write(parked_write);resume(parked_write);parked_write=None
                    if n==1 and fields.get("data","").startswith("bestmove "):
                        best_entries+=1
                        if best_entries==2:
                            last_best_writer=tid
                            if finished_wait_address is None:
                                parked_write=tid;record("park_best_until_finished_wait",tid);continue
                            before_best_write(tid)
                    if n==202 and args[1]==129:
                        if tid in output_waiting_wake:
                            if output_gate is None:output_gate=args[0]
                            else:check(output_gate==args[0],"OUTPUT wake address changed")
                            del output_waiting_wake[tid]
                        if finished_wait_address is not None and args[0]==finished_wait_address:
                            check(tid==last_best_writer,"finished published by another thread than bestmove writer")
                            observed=value32(tid,finished_wait_address);expected=(finished_expected_old+1)&0xffffffff
                            check(observed==expected,"finished word did not advance after complete write")
                            check(value32(tid,output_gate)==0,"finished published while OUTPUT gate held")
                            after_write_states.append(record("atomic_state_at_finished_wake",tid,finished_address=finished_wait_address,
                                expected_new=expected,observed=observed,output_gate=output_gate,output_gate_value=0))
                    if n==202 and args[1]==0 and tid==leader:
                        child=next((c for c,v in children.items()if v["child_tid_address"]==args[0]),None)
                        if child is not None:
                            observed=value32(tid,args[0]);record("shared_join_wait",tid,child=child,address=args[0],value=observed)
                            check(observed==child,"shared wait expected positive live TID");joining[child]=time.monotonic()
                    if n==11 and tid==leader:
                        child=next((c for c,v in children.items()if v["stack_top"]-4096-1024*1024==args[0]),None)
                        if child is not None:
                            observed=value32(tid,children[child]["child_tid_address"])
                            record("unmap_after_clear",tid,child=child,address=args[0],bytes=args[1],clear_tid=observed)
                            check(observed==0,"stack unmap before kernel clear-TID")
                elif kind=="exit":
                    entry=active.pop(tid,None)
                    if entry:
                        record("syscall_exit",tid,entry=entry["index"],number=entry["number"],name=entry["name"],result=n)
                        if entry["number"]==1 and entry["args"][0]==1:output_waiting_wake[tid]=entry["index"]
                resume(tid);continue
            resume(tid,0 if sig==signal.SIGTRAP else sig)
        p.returncode=reaped[leader]
        # Drain pipes after leader exit without calling waitpid on tracees again.
        for key,_ in selector.select(.02):
            chunk=os.read(key.fileobj.fileno(),65536)
            if key.data=="stdout":output+=chunk
            else:errors+=chunk
        check(reaped.get(leader)==0 and all(v==0 for v in reaped.values()),f"trace exits {reaped}")
        check(not errors,"trace stderr")
        calls=[e for e in events if e["kind"]=="syscall_entry"]
        count=1 if diagnostic else 2
        check(len([e for e in calls if e["number"]==56])==count,"wrong startup clone count")
        if diagnostic:
            check(output==b"deep begin\ndeep nodes 128\ndeep joined\n","diagnostic output")
            begin=next(e for e in calls if e.get("data")=="deep begin\n")
            begin_exit=next(e for e in events if e["kind"]=="syscall_exit"and e["entry"]==begin["index"])
            nodes=next(e for e in calls if e.get("data")=="deep nodes 128\n")
            check(not[e for e in calls if begin_exit["index"]<e["index"]<nodes["index"]and e["number"]in(9,10,12,56)],"deep recursion mapped memory or cloned")
            report.update(deep_begin_write_exit=begin_exit,deep_nodes_write=nodes,recursive_mmap_brk_clone_absent=True)
        else:
            check(output.count(b"bestmove ")==2,"trace bestmove count")
            check(not[e for e in calls if e["index"]>=boundary and e["number"]in(9,10,12,56)],"GO created a mapping or thread")
        unmaps=[e for e in events if e["kind"]=="unmap_after_clear"]
        check(len(unmaps)==count and all(e["bytes"]==1024*1024+8192 for e in unmaps),"stack unmap receipts")
        joins=[e for e in events if e["kind"]=="shared_join_wait"]
        check(len(joins)==count,"forced shared kernel-clear-TID waits not observed")
        for receipt in joins+unmaps:
            exit_event=next(e for e in events if e["kind"]=="syscall_exit"and e["entry"]==receipt["index"]-1)
            check(exit_event["result"]==0,"shared join wake or stack munmap did not return zero")
            receipt["syscall_return"]=exit_event["result"];receipt["syscall_exit_index"]=exit_event["index"]
        for receipt in unmaps:
            reaped_event=next(e for e in events if e["kind"]=="reaped"and e["tid"]==receipt["child"])
            receipt["worker_reaped_event_index"]=reaped_event["index"]
            receipt["worker_reaped_before_unmap_entry"]=reaped_event["index"]<receipt["index"]
        writes=[e for e in calls if e["number"]==1 and e.get("data","").startswith("bestmove ")]
        if not diagnostic:
            check(len(writes)==2 and all(e["tid"]!=leader for e in writes),"bestmove was not written by persistent worker")
            check(finished_wait_address is not None,"main finished-generation futex address not witnessed")
            last_write=writes[-1]
            write_exit=next(e for e in events if e["kind"]=="syscall_exit"and e["entry"]==last_write["index"])
            done_wake=next(e for e in calls if e["number"]==202 and e["args"][1]==129 and e["args"][0]==finished_wait_address and e["index"]>last_write["index"])
            check(write_exit["result"]==last_write["args"][2] and write_exit["index"]<done_wake["index"],"finished wake preceded physical complete write")
            check(len(before_write_states)==1 and len(after_write_states)==1,"missing atomic completion-state receipts")
            report.update(finished_wait_address=finished_wait_address,physical_best_write_exit=write_exit,finished_wake_after_write=done_wake,
                atomic_before_best_write=before_write_states,atomic_after_best_write=after_write_states,output_gate_address=output_gate)
        report.update(passed=True,children=children,reaped=reaped,startup_event_boundary=boundary,bestmove_writes=writes,
            shared_join_waits=joins,unmaps_after_kernel_zero=unmaps,per_go_clone_mmap_absent=None if diagnostic else True,
            scheduling=("worker exits held until shared join wait"if diagnostic else"second best write parked until main finish wait; worker exits held until shared join wait"),stdout=output.decode(),stderr=errors.decode())
    except BaseException as error:
        report["error"]={"type":type(error).__name__,"message":str(error)};raise
    finally:
        if alive:
            try:os.killpg(leader,signal.SIGKILL)
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
        save(out/"events.json",events);save(out/"trace.json",report)
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--image",type=Path,required=True);ap.add_argument("--out",type=Path,required=True);ap.add_argument("--diagnostic",action="store_true");a=ap.parse_args()
    check(sys.platform=="linux"and a.out.is_absolute()and not a.out.exists(),"new absolute Linux output required")
    report=trace(a.image.resolve(),a.out,a.diagnostic);print(json.dumps({"passed":report["passed"],"out":str(a.out),"pid":report["pid"]}))
if __name__=="__main__":main()
