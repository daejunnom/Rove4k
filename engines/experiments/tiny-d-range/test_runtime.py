#!/usr/bin/env python3
"""Actual stopped pre-entry image/BSS/permissions and running TinyD checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import select
import signal
import subprocess
import time



def sha(data):
    return hashlib.sha256(data).hexdigest()


def maps(pid):
    result = []
    for line in Path(f"/proc/{pid}/maps").read_text().splitlines():
        span, permission, *rest = line.split()
        first, last = (int(value,16) for value in span.split("-"))
        result.append({"start":first,"end":last,"permissions":permission,"line":line})
    if any("w" in m["permissions"] and "x" in m["permissions"] for m in result):
        raise AssertionError("a writable executable mapping exists")
    stack = next(m for m in result if "[stack]" in m["line"])
    assert "x" not in stack["permissions"]
    return result


def covers(mapping, begin, length, permission):
    end = begin+length
    position = begin
    for item in mapping:
        if item["end"] <= position: continue
        if item["start"] > position: break
        assert item["permissions"][:3] == permission, item
        position = min(end,item["end"])
        if position == end: return
    raise AssertionError("memory range absent/incomplete")


def inspect(pid, layout, expected, *, initial):
    mapping = maps(pid)
    covers(mapping,layout["image_base"],layout["image_pages"],"r-x")
    covers(mapping,layout["bss_base"],layout["bss_pages"],"rw-")
    covers(mapping,layout["guard_base"],4096,"---")
    covers(mapping,layout["upper_guard"],4096,"---")
    with open(f"/proc/{pid}/mem","rb",buffering=0) as memory:
        image = os.pread(memory.fileno(),layout["image_size"],layout["image_base"])
        assert sha(image) == expected, "actual restored RX differs"
        padding = os.pread(memory.fileno(),layout["image_pages"]-layout["image_size"],layout["image_base"]+layout["image_size"])
        assert not any(padding), "RX page padding not zero"
        if initial:
            state = os.pread(memory.fileno(),layout["bss_pages"],layout["bss_base"])
            assert len(state) == layout["bss_pages"] and not any(state), "BSS/padding not initially zero"
    return {"mapped_image_sha256":sha(image), "image_matches":True,"initial_bss_and_padding_zero":True if initial else None,
            "wx_forbidden":True,"nonexec_stack":True,"lower_upper_guards":True,"maps":mapping}


def stopped(process, timeout=10):
    deadline = time.monotonic()+timeout
    while time.monotonic()<deadline:
        pid, status = os.waitpid(process.pid,os.WNOHANG|os.WUNTRACED)
        if pid:
            assert os.WIFSTOPPED(status) and os.WSTOPSIG(status)==signal.SIGSTOP, status
            return
        if process.poll() is not None: raise AssertionError("audit exited before checkpoint")
        time.sleep(.005)
    raise TimeoutError("no pre-entry checkpoint")


def cleanup(process):
    if process.poll() is None:
        try: os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError: pass
    process.communicate(timeout=5)


def checkpoint(candidate, layout, expected):
    process = subprocess.Popen([candidate["audit"]["path"]],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    try:
        stopped(process)
        evidence = inspect(process.pid,layout,expected,initial=True)
        os.kill(process.pid,signal.SIGCONT)
        stdout,stderr = process.communicate(b"uci\nisready\nquit\n",timeout=15)
        assert process.returncode==0 and b"uciok\n" in stdout and b"readyok\n" in stdout,(process.returncode,stdout,stderr)
        evidence.update({"entry":layout["entry"],"resumed_original_entry":True,"returncode":0,"stdout":stdout.decode()})
        return evidence
    finally: cleanup(process)


def production(candidate, layout, expected):
    assert sha(Path(candidate["path"]).read_bytes())==candidate["sha256"]
    process = subprocess.Popen([candidate["path"]],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    output = bytearray()
    def send(data):
        process.stdin.write(data);process.stdin.flush()
    def until(pattern, seconds=15):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if re.search(pattern,bytes(output)): return
            ready,_,_=select.select([process.stdout],[],[],min(.1,max(0,deadline-time.monotonic())))
            if ready:
                data=os.read(process.stdout.fileno(),4096)
                if not data: raise AssertionError("unexpected engine EOF")
                output.extend(data)
        raise TimeoutError("engine response: "+repr(output))
    try:
        send(b"uci\nisready\n")
        until(rb"readyok\n")
        tasks=sorted(int(p.name) for p in Path(f"/proc/{process.pid}/task").iterdir())
        assert len(tasks)==3,tasks
        image=inspect(process.pid,layout,expected,initial=False)
        send(b"position startpos\ngo wtime 3000 btime 3000 winc 0 binc 0\n")
        until(rb"bestmove [a-h][1-8][a-h][1-8][nbrq]?\n")
        assert tasks==sorted(int(p.name) for p in Path(f"/proc/{process.pid}/task").iterdir()),"startup tasks replaced"
        after=inspect(process.pid,layout,expected,initial=False)
        descriptor_names=sorted(p.name for p in Path(f"/proc/{process.pid}/fd").iterdir())
        assert descriptor_names==["0","1","2"],descriptor_names
        if candidate["codec"]=="order1": send(b"quit\n")
        else: process.stdin.close();process.stdin=None
        tail,stderr=process.communicate(timeout=15)
        output.extend(tail)
        assert process.returncode==0,(process.returncode,stderr)
        return {"passed":True,"startup_tids":tasks,"persistent_tids":True,"expected_total_threads":3,
                "before_search":image,"after_search":after,"only_stdio_descriptors":True,
                "shutdown":"quit" if candidate["codec"]=="order1" else "EOF","returncode":0,"stdout":output.decode(),
                "claim":"actual clocked result and immutable RX; move legality/full shipping behavior checked separately"}
    finally: cleanup(process)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if not args.out.is_absolute() or args.out.exists() or any((p/".git").exists() for p in (args.out.resolve(),*args.out.resolve().parents)):
        parser.error("--out must be new, absolute and outside the checkout")
    args.out.mkdir(parents=True)
    build=json.loads(args.build.read_text())
    assert build["complete"]
    report={"complete":False,"build_sha256":sha(args.build.read_bytes()),"validator_sha256":sha(Path(__file__).read_bytes()),"results":[],"negative_decoder_results":[]}
    manifest={"engines":[]}
    try:
        for fixture in build["negative_decoder_controls"]:
            assert sha(Path(fixture["path"]).read_bytes())==fixture["sha256"]
            process=subprocess.run([fixture["path"]],input=b"",stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
            assert process.returncode==126 and not process.stdout,(fixture["name"],process.returncode,process.stdout,process.stderr)
            report["negative_decoder_results"].append({"name":fixture["name"],"passed":True,"returncode":process.returncode})
        for engine in build["engines"]:
            for candidate in engine["candidates"]:
                row={"engine":engine["id"],"codec":candidate["codec"],"program_sha256":candidate["sha256"]}
                report["results"].append(row)
                row["pre_entry"]=checkpoint(candidate,engine["layout"],engine["input_sha256"])
                row["production"]=production(candidate,engine["layout"],engine["input_sha256"])
                manifest["engines"].append({"id":"tiny-D-"+engine["id"]+"-"+candidate["codec"],"command":[candidate["path"]],
                    "cwd":str(Path(candidate["path"]).parent),"profile":"shipping","workers":2,"startup_threads":3,
                    "max_threads":3,"startup_timeout":60,"expected_program_sha256":candidate["sha256"]})
        report["complete"]=True
    except Exception as error:
        report["failure"]=repr(error)
        raise
    finally:
        (args.out/"results.json").write_text(json.dumps(report,indent=2)+"\n")
        (args.out/"selected-shipping-pinned.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"complete":True,"candidate_count":len(report["results"]),"checks":["pre-entryRX/BSS","W^X/guards/stack","clockedsearch","fixed3TIDs","quit/EOF","stdioonly"]}))


if __name__=="__main__": main()
