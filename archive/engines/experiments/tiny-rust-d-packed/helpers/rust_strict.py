#!/usr/bin/env python3
"""Bounded Linux qualification of pinned complete no_std D ELFs, never a loader.

This verifier does not build the production image. Syscall tracing and fault
images are separate evidence classes in tests/runtime_trace.py/runtime_faults.py.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
CAP=1024*1024

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+"\n")
def check(value,message):
    if not value:raise AssertionError(message)

class Session:
    def __init__(self,image,directory,stdout=subprocess.PIPE):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=False)
        self.process=subprocess.Popen([str(image)],cwd=self.directory,stdin=subprocess.PIPE,
            stdout=stdout,stderr=subprocess.PIPE,start_new_session=True,bufsize=0)
        self.selector=selectors.DefaultSelector();self.lines=[];self.queued=[];self.pending=b"";self.error=b"";self.bytes=0
        self.input_pending=b"";self.dispatched_go=0;self.accepted_best=0;self.boundaries=[]
        for name,stream in (("stdout",self.process.stdout),("stderr",self.process.stderr)):
            if stream is not None:os.set_blocking(stream.fileno(),False);self.selector.register(stream,selectors.EVENT_READ,name)
        os.set_blocking(self.process.stdin.fileno(),False)
        self.identity=os.readlink(f"/proc/{self.process.pid}/exe")
    def pump(self,timeout):
        for key,_ in self.selector.select(max(0,timeout)):
            chunk=os.read(key.fileobj.fileno(),65536)
            if not chunk:self.selector.unregister(key.fileobj);continue
            self.bytes+=len(chunk);check(self.bytes<=CAP,"output cap exceeded")
            if key.data=="stderr":self.error+=chunk;continue
            self.pending+=chunk
            while b"\n" in self.pending:
                line,self.pending=self.pending.split(b"\n",1)
                text=line.decode("utf-8",errors="strict");self.lines.append(text);self.queued.append(text)
    def send(self,value,timeout=5):
        raw=value.encode() if isinstance(value,str) else value
        self.admit(raw);data=memoryview(raw);end=time.monotonic()+timeout
        while data:
            check(time.monotonic()<end,"stdin write timeout")
            check(self.process.poll() is None,"process exited before command")
            try:n=os.write(self.process.stdin.fileno(),data);data=data[n:]
            except BlockingIOError:self.pump(.01)
    def until(self,prefix,timeout=8):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            while self.queued:
                text=self.queued.pop(0)
                if text.startswith(prefix):return text
            self.pump(min(.05,max(0,end-time.monotonic())))
            if self.process.poll() is not None and not self.queued:break
        raise AssertionError(f"missing {prefix!r}; exit={self.process.poll()}, tail={self.lines[-8:]}, stderr={self.error!r}")
    def admit(self,data=b"",eof=False):
        self.input_pending+=data
        while b"\n"in self.input_pending or eof and self.input_pending:
            end=self.input_pending.find(b"\n")
            if end<0:raw=self.input_pending;self.input_pending=b""
            else:raw=self.input_pending[:end+1];self.input_pending=self.input_pending[end+1:]
            if len(raw)>32768 or b"\0"in raw:continue
            try:words=raw.decode().split()
            except UnicodeDecodeError:continue
            if words and words[0]=="go":self.dispatched_go+=1
            if words and words[0]in("go","stop","position","ucinewgame","quit"):
                self.boundaries.append({"command":words[0],"dispatched_go":self.dispatched_go,"accepted_best":self.accepted_best})
    def counts(self,expected):
        actual=sum(x.startswith("bestmove ")for x in self.lines)
        check(actual==expected,f"cumulative bestmove count {actual} != {expected}; GO dispatched {self.dispatched_go}")
        check(self.accepted_best==expected,f"consumed bestmove count {self.accepted_best} != {expected}")
        return actual
    def no_best(self,duration=.03,active=False):
        expected=self.dispatched_go-int(active)
        check(not any(x.startswith("bestmove ")for x in self.queued),"already queued duplicate bestmove")
        self.counts(expected)
        start=len(self.lines);end=time.monotonic()+duration
        while time.monotonic()<end:self.pump(min(.01,end-time.monotonic()))
        check(not any(x.startswith("bestmove ")for x in self.lines[start:]),"unexpected extra bestmove")
        check(not any(x.startswith("bestmove ")for x in self.queued),"queued duplicate bestmove after pump")
        self.counts(expected)
        self.boundaries.append({"checkpoint":"active"if active else"completed","dispatched_go":self.dispatched_go,"expected_best":expected,"actual_best":expected})
    def tasks(self):return sorted(int(p.name)for p in Path(f"/proc/{self.process.pid}/task").iterdir())
    def maps(self):return Path(f"/proc/{self.process.pid}/maps").read_text()
    def syscall(self):return Path(f"/proc/{self.process.pid}/syscall").read_text().strip()
    def finish(self,command="quit\n",expected=0):
        if command is not None:self.send(command)
        elif not self.process.stdin.closed:self.admit(eof=True);self.process.stdin.close()
        end=time.monotonic()+8
        while self.process.poll() is None and time.monotonic()<end:self.pump(.02)
        check(self.process.poll()==expected,f"exit {self.process.poll()} != {expected}; stderr {self.error!r}")
        drain=time.monotonic()+1
        while self.selector.get_map()and time.monotonic()<drain:self.pump(.02)
        check(not self.selector.get_map(),"output pipes did not reach EOF after process exit")
        check(not self.pending,f"unterminated stdout tail after final result: {self.pending!r}")
        check(not Path(f"/proc/{self.process.pid}").exists(),"leader still exists")
        check(not self.error,f"unexpected stderr: {self.error!r}")
        actual=sum(x.startswith("bestmove ")for x in self.lines)
        check(actual==self.dispatched_go,f"final/EOF bestmove count {actual} != GO dispatch count {self.dispatched_go}")
        self.boundaries.append({"checkpoint":"final/EOF","dispatched_go":self.dispatched_go,"actual_best":actual})
    def close(self):
        if self.process.poll() is None:
            try:os.killpg(self.process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            self.process.wait(timeout=5)
        for stream in (self.process.stdin,self.process.stdout,self.process.stderr):
            if stream is not None:stream.close()
        self.selector.close()
        save(self.directory/"session.json",{"pid":self.process.pid,"exe":self.identity,"returncode":self.process.returncode,
            "lines":self.lines,"stderr":self.error.decode(errors="replace"),"bytes":self.bytes,
            "dispatched_go":self.dispatched_go,"accepted_best":self.accepted_best,"boundaries":self.boundaries})

def best(session,allowed=None):
    line=session.until("bestmove ");move=line.split()[1]
    session.accepted_best+=1
    check(session.accepted_best<=session.dispatched_go,"more bestmoves consumed than dispatched GO commands")
    check(re.fullmatch(r"(?:[a-h][1-8][a-h][1-8][nbrq]?|0000)",move),f"bad move text {move}")
    if allowed is not None:check(move in allowed,f"move {move} is illegal for admitted position")
    return move

def initial(side):
    rank,pawn,knights=("1","2",("b1a3","b1c3","g1f3","g1h3"))if side=="white"else("8","7",("b8a6","b8c6","g8f6","g8h6"))
    del rank
    step=("3","4")if side=="white"else("6","5")
    return set(knights)|{f+ pawn+f+t for f in "abcdefgh"for t in step}

def guarded(maps):
    rows=[]
    for line in maps.splitlines():
        fields=line.split();a,b=(int(n,16)for n in fields[0].split("-"));rows.append((a,b,fields[1],line))
    found=[]
    for i,(a,b,mode,_)in enumerate(rows):
        if mode.startswith("rw")and b-a==1024*1024 and i and i+1<len(rows):
            lo,hi=rows[i-1],rows[i+1]
            if lo[1]==a and hi[0]==b and lo[2].startswith("---")and hi[2].startswith("---"):
                found.append({"base":hex(a-4096),"usable_start":hex(a),"usable_end":hex(b),"bytes":1024*1024,
                    "low_guard":lo[3],"high_guard":hi[3]})
    return found

def pin(image,label):
    image=Path(image).resolve();report_path=image.parent.parent/"build.json";report=json.loads(report_path.read_text())
    check(report["workers"]==2 and report["tt_bits"]==18 and report["hq"]==label,"wrong fixed production recipe")
    check(all(report["artifact_gates"].values()),"static artifact gate failed")
    check(digest(image)==report["complete_native_sha256"],"ELF hash differs from audited complete image")
    check(image.read_bytes()[:6]==b"\x7fELF\x02\x01","not native ELF64 little endian")
    for name,value in report["source_sha256"].items():check(digest(image.parent/name)==value,f"frozen source differs: {name}")
    return {"path":str(image),"sha256":digest(image),"bytes":image.stat().st_size,"build_report":str(report_path),
        "source_sha256":report["source_sha256"],"artifact_gates":report["artifact_gates"]}

def qualify(image,directory):
    root=Path(directory);root.mkdir();result={};s=Session(image,root/"lifecycle")
    try:
        s.send("uci\nisready\n");s.until("uciok");s.until("readyok")
        check(Path(s.identity).resolve()==Path(image).resolve(),"different executable at /proc/exe")
        tids=s.tasks();check(len(tids)==3,"not exactly two search workers plus main")
        maps=s.maps();(s.directory/"startup-maps.txt").write_text(maps)
        stacks=guarded(maps);check(len(stacks)==2,"two guarded 1MiB worker stacks not found")
        s.send("position startpos\ngo wtime 300\n");best(s,initial("white"));s.no_best()
        deadline=time.monotonic()+1;main_syscall=s.syscall()
        while main_syscall.split()[0]!="0"and time.monotonic()<deadline:time.sleep(.005);main_syscall=s.syscall()
        check(main_syscall.split()[0]=="0","main was not blocked in read after async output")
        for _ in range(6):
            s.send("go infinite\n");s.no_best(active=True);s.send("stop\n");best(s,initial("white"));s.no_best()
            check(s.tasks()==tids,"worker TIDs changed")
            current=s.maps()
            if current!=maps:(s.directory/"changed-maps.txt").write_text(current)
            # Kernel grows the ordinary main stack on first deeper call without
            # mmap. Retain its delta; only worker/fixed mappings are invariant.
            fixed=lambda text:[line for line in text.splitlines()if "[stack]"not in line]
            check(fixed(current)==fixed(maps),"fixed shipping mappings changed between GO jobs")
        s.send("go infinite\n");s.no_best(active=True);s.send("position startpos moves e2e4\n");best(s,initial("white"));s.no_best()
        s.send("go btime 30\n");best(s,initial("black"));s.no_best()
        s.send("go infinite\n");s.no_best(active=True);s.send("go btime 30\n");best(s,initial("black"));best(s,initial("black"));s.no_best()
        s.send("go infinite\n");s.no_best(active=True);s.send("ucinewgame\n");best(s,initial("black"));s.no_best()
        s.send("go btime 30\n");best(s,initial("black"));s.no_best()
        before=sum(x.startswith("bestmove ")for x in s.lines)
        s.send("go infinite\n");s.no_best(active=True);s.finish()
        check(sum(x.startswith("bestmove ")for x in s.lines)==before+1,"quit did not finish active GO exactly once")
        result["lifecycle"]={"passed":True,"startup_tids":tids,"worker_guard_mappings":stacks,"stable_mappings":True,
            "main_stack_vma_growth_allowed_and_recorded":True,"async_main_syscall":main_syscall,"bestmoves":sum(x.startswith("bestmove ")for x in s.lines)}
    finally:s.close()
    s=Session(image,root/"input-clock")
    try:
        s.send("uci\n");s.until("uciok")
        s.send("position startpos moves e2e4\n")
        rejected=[b"position startpos moves e2e4 e7e5 e1e8\n",b"position startpos "+b"x"*33000+b"\n",
            b"position startpos\x00\n",b"position startpos\xff\n"]
        cycle=("g1f3 g8f6 f3g1 f6g8 "*1024).split()
        rejected.append(("position startpos moves "+" ".join(cycle)+"\n").encode())
        for command in rejected:
            s.send(command+b"go btime 0\n");best(s,initial("black"));s.no_best()
        clocks=[]
        for black in (False,True):
            s.send("position startpos"+(" moves e2e4"if black else "")+"\n")
            for label,value in (("malformed","bad"),("negative","-1"),("overflow","18446744073709551616"),("missing",""),("zero","0")):
                s.send("go "+("btime "if black else "wtime ")+value+"\n")
                best(s,initial("black"if black else "white"));s.no_best()
                clocks.append({"side":"black"if black else"white","case":label,"best_before_stop_or_eof":True})
        # 4088 reversible plies plus Scholar's Mate is exactly 4095 moves.
        # Checkmate 0000 distinguishes admission from the retained earlier board.
        mate=cycle[:4088]+"e2e4 e7e5 d1h5 b8c6 f1c4 g8f6 h5f7".split()
        check(len(mate)==4095,"history fixture length")
        s.send("position startpos moves "+" ".join(mate)+"\ngo btime 0\n")
        best(s,{"0000"});s.no_best();s.finish()
        result["input_clock"]={"passed":True,"rejected_transactional_cases":len(rejected),"clock_cases":clocks,
            "4095_history_admitted":True,"4096_history_rejected":True}
    finally:s.close()
    eof=[]
    for label,active,terminated in (("idle",False,True),("active",True,True),("unterminated-go",True,False)):
        s=Session(image,root/("eof-"+label))
        try:
            s.send("uci\n");s.until("uciok")
            if active:s.send("go infinite"+("\n"if terminated else""));s.no_best(active=terminated)
            s.finish(None);n=sum(x.startswith("bestmove ")for x in s.lines)
            check(n==int(active),"EOF bestmove count")
            eof.append({"active":active,"line_terminated":terminated,"bestmoves":n,"exit":0})
        finally:s.close()
    result["eof"]={"passed":True,"cases":eof}
    read_end,write_end=os.pipe();os.close(read_end)
    s=Session(image,root/"closed-output",stdout=write_end);os.close(write_end)
    try:
        end=time.monotonic()+2;tids=s.tasks()
        while len(tids)!=3 and time.monotonic()<end:time.sleep(.005);tids=s.tasks()
        check(len(tids)==3,"closed-output failure did not reach startup three threads")
        s.finish("uci\n",expected=-signal.SIGPIPE)
        check(all(not Path(f"/proc/{tid}").exists()for tid in tids),"SIGPIPE left worker tasks")
        result["closed_output"]={"passed":True,"startup_tids":tids,"termination_signal":signal.SIGPIPE,"all_tasks_gone":True}
    finally:s.close()
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--hq",type=Path,required=True)
    ap.add_argument("--scalar",type=Path,required=True);ap.add_argument("--out",type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();repo=HERE.parents[2]
    if sys.platform!="linux"or not a.out.is_absolute()or out.exists()or out==repo or repo in out.parents:ap.error("new absolute external Linux output required")
    out.mkdir();(out/"verify_runtime.py").write_bytes(Path(__file__).read_bytes())
    report={"scope":"actual pinned no_std native runtime; source tests and syscall traces separate","verifier_sha256":digest(__file__),"passed":False,"variants":{}}
    try:
        for label,image in (("hq",a.hq),("scalar",a.scalar)):
            report["variants"][label]={"pin":pin(image,label),"checks":qualify(image,out/label)}
        report["passed"]=True
    except BaseException as error:
        report["error"]={"type":type(error).__name__,"message":str(error)};raise
    finally:save(out/"runtime.json",report)
    print(json.dumps({"passed":True,"report":str(out/"runtime.json"),"variants":list(report["variants"])}))

if __name__=="__main__":main()
