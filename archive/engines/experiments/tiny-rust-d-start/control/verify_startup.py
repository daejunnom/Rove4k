#!/usr/bin/env python3
"""First bounded actual no_std D startup/search/stop/quit, without a loader."""

if __name__ == "__main__":
    raise SystemExit("Rove4k Rust engine paths are retired; use C A-F")

import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import signal
import subprocess
import threading
import time

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--build",type=Path,required=True);ap.add_argument("--out",type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);build=json.loads(a.build.read_text());binary=Path(build["builds"][0]["path"])
    expected=build["complete_native_sha256"];assert hashlib.sha256(binary.read_bytes()).hexdigest()==expected
    log=[];events=queue.Queue();report={"passed":False,"artifact_sha256":expected,"native_bytes":binary.stat().st_size,"build":str(a.build)}
    process=subprocess.Popen([str(binary)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,bufsize=0)
    began=time.monotonic()
    def reader(pipe,label):
        total=0
        while True:
            line=pipe.readline(4097)
            if not line:events.put((label,None));return
            total+=len(line)
            if len(line)>4096 or total>65536:events.put(("error",b"output bound"));return
            events.put((label,line.decode("utf-8",errors="replace").rstrip("\r\n")))
    threads=[threading.Thread(target=reader,args=(process.stdout,"stdout"),daemon=True),threading.Thread(target=reader,args=(process.stderr,"stderr"),daemon=True)]
    for t in threads:t.start()
    def send(text):log.append({"t":time.monotonic()-began,"stdin":text});process.stdin.write((text+"\n").encode());process.stdin.flush()
    def receive(prefix):
        end=time.monotonic()+3
        while True:
            label,line=events.get(timeout=max(.001,end-time.monotonic()));log.append({"t":time.monotonic()-began,label:line})
            assert label!="error",line
            if label=="stdout":
                assert line is not None,"stdout closed before "+prefix
                if line.startswith(prefix):return line
            if time.monotonic()>end:raise TimeoutError(prefix)
    def tids():return sorted(int(p.name)for p in (Path("/proc")/str(process.pid)/"task").iterdir())
    try:
        end=time.monotonic()+3;ids=[]
        while time.monotonic()<end:
            assert process.poll() is None,"startup terminated"
            ids=tids()
            if len(ids)==build["startup_threads"]:break
            time.sleep(.005)
        assert len(ids)==3,ids
        send("uci");receive("uciok");send("isready");receive("readyok")
        send("position startpos");send("go wtime 200 btime 200 winc 0 binc 0");best=receive("bestmove ")
        legal={f+t for f in("a2","b2","c2","d2","e2","f2","g2","h2")for t in(f[0]+"3",f[0]+"4")}|{"b1a3","b1c3","g1f3","g1h3"}
        assert best.split()[1]in legal,best;assert tids()==ids
        send("go infinite");time.sleep(.05);send("stop");stopped=receive("bestmove ");assert stopped.split()[1]in legal;assert tids()==ids
        send("quit");assert process.wait(timeout=3)==0
        for t in threads:t.join(timeout=1)
        while not events.empty():
            label,line=events.get_nowait();log.append({"t":time.monotonic()-began,label:line})
        assert sum(isinstance(x.get("stdout"),str)and x["stdout"].startswith("bestmove ")for x in log)==2
        report.update(passed=True,pid=process.pid,startup_thread_ids=ids,clocked_bestmove=best,stopped_bestmove=stopped,returncode=process.returncode,elapsed_seconds=time.monotonic()-began)
    except Exception as error:
        report.update(error=type(error).__name__+": "+str(error),returncode=process.poll());raise
    finally:
        (a.out/"report.json").write_text(json.dumps({**report,"transcript":log},indent=2)+"\n")
        if process.poll()is None:
            os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
        for p in(process.stdin,process.stdout,process.stderr):p.close()
    print(json.dumps(report))
if __name__=="__main__":main()
