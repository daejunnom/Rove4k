#!/usr/bin/env python3
"""Direct verifier for the single minimal shipping policy, with strict controls.

The existing raw-process helper/oracle are frozen unchanged outside Git. Their
legacy protocol checks are never called for the minimal policy. Instrumented
dispatch/arithmetic proofs and actual executable behavior are reported separately.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
T0 = 123456789


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise AssertionError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def save(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def bounded(command, cwd, timeout=30):
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate(timeout=5)
        raise TimeoutError("bounded instrumentation command timed out: " + repr(command))
    record = {"command": list(map(str, command)), "returncode": process.returncode,
              "stdout": stdout.decode(errors="replace"), "stderr": stderr.decode(errors="replace")}
    require(process.returncode == 0, "instrumentation failed: " + json.dumps(record))
    return record


HARNESS = r'''
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <time.h>
#include <stdatomic.h>
static int probe_getchar(void);
static int probe_clock(clockid_t,struct timespec*);
static int probe_create(pthread_t*,const pthread_attr_t*,void*(*)(void*),void*);
static int probe_join(pthread_t,void**);
static int probe_wait(pthread_cond_t*,pthread_mutex_t*);
#define getchar probe_getchar
#define clock_gettime probe_clock
#define pthread_create probe_create
#define pthread_join probe_join
#define pthread_cond_wait probe_wait
#define main engine_main
#include "engine.c"
#undef main
#undef getchar
#undef clock_gettime
#undef pthread_create
#undef pthread_join
#undef pthread_cond_wait
static const char *scenario,*script;
static size_t offset;
static int boundary,spawned,joined,completions,minimal,black_root;
static uint64_t expected_deadline,old_hash;
static unsigned char *tt_snapshot;
static Board saved_position;
static Worker saved_workers[WORKERS];
static uint64_t saved_keys[HISTORY];
static uint64_t saved_deadline;
static unsigned saved_epoch;
static int saved_length;
static void check(int value,const char*name){if(!value){fprintf(stderr,"unit assertion: %s\n",name);exit(90);}}
static int probe_clock(clockid_t id,struct timespec*t){
    check(id==CLOCK_MONOTONIC,"monotonic clock");t->tv_sec=123456;t->tv_nsec=789000000;return 0;
}
static int probe_create(pthread_t*t,const pthread_attr_t*a,void*(*fn)(void*),void*p){
    (void)a;(void)fn;(void)p;*t=(pthread_t)(unsigned long)(++spawned);ready++;return 0;
}
static int probe_join(pthread_t t,void**p){(void)p;check((unsigned long)t==(unsigned long)(joined+1),"synthetic join order");joined++;return 0;}
static int probe_wait(pthread_cond_t*c,pthread_mutex_t*m){
    check(c==&finished&&m==&mutex,"real wait boundary");check(atomic_load(&stopped)==1&&pending>0,"cancel before modeled completion");
    check(position.h==old_hash,"prior root retained until completion");completions++;pending=0;return 0;
}
static void seed(void){
    if(black_root){char text[]="startpos moves e2e4";set_position(text);}
    pending=WORKERS;epoch=17;deadline=7777777;atomic_store(&stopped,0);old_hash=position.h;
    if(!strcmp(scenario,"ignored")){
        size_t bytes=((size_t)1<<TT_BITS)*sizeof *table;
        for(size_t i=0;i<((size_t)1<<TT_BITS);i++){table[i].key=0x123456789abcdefULL+i;table[i].data=0xfedcba987654321ULL-i;}
        tt_snapshot=malloc(bytes);check(tt_snapshot!=0,"TT snapshot allocation");memcpy(tt_snapshot,table,bytes);
        saved_position=position;memcpy(saved_workers,workers,sizeof workers);memcpy(saved_keys,game_keys,sizeof game_keys);
        saved_length=game_length;saved_deadline=deadline;saved_epoch=epoch;
    }
}
static void boundary_check(void){
    if(!boundary){seed();boundary++;return;}
    if(!strcmp(scenario,"ignored")&&boundary<=4){
        if(minimal){
            check(completions==0&&pending==WORKERS&&atomic_load(&stopped)==0,"ignored command did not wait/cancel");
            check(!memcmp(tt_snapshot,table,((size_t)1<<TT_BITS)*sizeof *table),"whole TT unchanged");
            check(!memcmp(&saved_position,&position,sizeof position)&&!memcmp(saved_workers,workers,sizeof workers),"root/workers unchanged");
            check(!memcmp(saved_keys,game_keys,sizeof game_keys)&&saved_length==game_length,"complete history unchanged");
            check(saved_epoch==epoch&&saved_deadline==deadline,"epoch/deadline unchanged");
        }else{
            check(completions==1&&pending==0&&atomic_load(&stopped)==1,"legacy stop waited");
            if(boundary==1)check(!memcmp(tt_snapshot,table,((size_t)1<<TT_BITS)*sizeof *table),"legacy stop preserved TT");
            else for(size_t i=0;i<((size_t)1<<TT_BITS);i++)check(!table[i].key&&!table[i].data,"legacy newgame cleared TT");
        }
    }else if(!strcmp(scenario,"budget")&&boundary==1){
        check(completions==1&&epoch==18&&pending==WORKERS&&atomic_load(&stopped)==0,"next go settled prior epoch before reuse");
        check(deadline==expected_deadline,"exact budget/deadline");
    }else if(!strcmp(scenario,"position")&&boundary==1){
        check(completions==1&&pending==0&&position.s==-1&&game_length==2,"position settled prior epoch before root commit");
        old_hash=position.h;
    }
    boundary++;
}
static int probe_getchar(void){
    if(!offset||script[offset-1]=='\n')boundary_check();
    return script[offset]?(unsigned char)script[offset++]:EOF;
}
int main(int argc,char**argv){
    check(argc>=3,"arguments");minimal=atoi(argv[1]);scenario=argv[2];
    char input[2048];
    if(!strcmp(scenario,"ignored"))script="stop\nucinewgame\nuci\nisready\nquit\n";
    else if(!strcmp(scenario,"position"))script="position startpos moves e2e4\nisready\nquit\n";
    else if(!strcmp(scenario,"quit"))script="quit\n";
    else if(!strcmp(scenario,"eof"))script="";
    else{
        check(argc==6&&!strcmp(scenario,"budget"),"budget arguments");expected_deadline=strtoull(argv[4],0,10);black_root=atoi(argv[5]);
        snprintf(input,sizeof input,"go%s%s\nisready\nquit\n",*argv[3]?" ":"",argv[3]);script=input;
    }
    int code=engine_main();check(code==0&&spawned==WORKERS&&joined==WORKERS,"modeled workers joined");
    check(completions==(!strcmp(scenario,"budget")?2:1),"completion count");
    free(tt_snapshot);
    fprintf(stderr,"{\"instrumented\":true,\"scenario\":\"%s\",\"completions\":%d,\"joins\":%d,\"deadline\":%llu,\"physical_completion_claim\":false}\n",scenario,completions,joined,(unsigned long long)deadline);
    return 0;
}
'''


def units(records, out):
    destination = out / "units"
    destination.mkdir()
    results = []
    for record in records:
        work = destination / record["id"]
        work.mkdir()
        source = Path(record["readable"]).read_bytes()
        require(sha(source) == record["readable_sha256"], "readable source identity changed")
        (work / "engine.c").write_bytes(source)
        (work / "harness.c").write_text(HARNESS)
        command = ["cc", "-std=c11", "-Os", "-pthread", "-DWORKERS=2", "-DTT_BITS=18", "-DDEV=0",
                   "harness.c", "-o", "harness"]
        compile_record = bounded(command, work)
        row = {"id": record["id"], "source_sha256": sha(source), "harness_sha256": sha(HARNESS.encode()),
               "compile": compile_record, "program_sha256": sha((work / "harness").read_bytes()),
               "scope": "actual dispatch/wait/clear/go; environmental no-thread completion and fixed-clock stubs; no physical-completion claim", "cases": []}
        results.append(row)
        minimal = record["id"] == "minimal"
        for scenario in ("ignored", "position", "quit", "eof"):
            case = bounded([str(work / "harness"), str(int(minimal)), scenario], work, timeout=5)
            case["observation"] = json.loads(case["stderr"])
            if scenario == "ignored":
                expected = "uciok\nreadyok\n" if minimal else "id name Rove4k A\nuciok\nreadyok\n"
                require(case["stdout"] == expected, "instrumented UCI output policy differs")
            row["cases"].append(case)
        # Independent arithmetic values; no 24-hour runtime search is launched.
        cases = [
            ("", 1000, False), ("infinite", 1000, False),
            ("wtime 0 btime 9223372036854775807", 1, False),
            ("wtime 3000 winc 1000", 600, False),
            ("wtime 400000000 winc 86400000", 78133333, False),
            ("wtime 400000000 winc 9223372036854775807", 78133333, False),
            ("wtime 648000000 winc 86400000", 86400000, False),
            ("wtime 9223372036854775807 winc 0", 86400000, False),
            ("btime 0", 1000, False),
            ("wtime 9223372036854775807 btime 0 winc 999", 1, True),
            ("btime 3000 binc 20 winc 999", 115, True),
        ]
        for fields, budget, black in cases:
            expected_deadline = T0+budget
            if not minimal and (fields in ("", "infinite") or fields == "btime 0"):
                expected_deadline = (1 << 64)-1
            case = bounded([str(work / "harness"), str(int(minimal)), "budget", fields,
                            str(expected_deadline), str(int(black))], work, timeout=5)
            case["expected_budget_ms"] = budget if minimal or expected_deadline != (1 << 64)-1 else None
            case["observation"] = json.loads(case["stderr"])
            row["cases"].append(case)
    return results


def runtime_snapshot(engine, native_hash, cwd, temporary):
    pid = engine.runtime_pid
    require(pid == engine.process.pid, "wrapper did not replace itself with the native engine")
    require(sha(Path(f"/proc/{pid}/exe").read_bytes()) == native_hash, "actual native executable SHA differs")
    engine.stable()
    require(len(engine.startup_tids) == 3, "expected exactly three startup TIDs")
    children = []
    for task in Path(f"/proc/{pid}/task").iterdir():
        children.extend((task / "children").read_text().split())
    require(not children, "child processes remain after startup")
    descriptors = sorted(p.name for p in Path(f"/proc/{pid}/fd").iterdir())
    require(descriptors == ["0", "1", "2"], "native engine retained an extra descriptor")
    require(not list(cwd.iterdir()) and not list(temporary.iterdir()), "temporary files remain after startup")
    return {"pid": pid, "tids": sorted(engine.startup_tids), "native_sha256": native_hash,
            "only_stdio": True, "no_children": True, "cwd_and_tmp_empty": True}


def best_line(lines, board):
    publications = [line for line in lines if line.startswith("bestmove ")]
    legal = {str(move) for move in board.legal_moves()}
    for line in publications:
        fields = line.split()
        require(len(fields) == 2 and (fields[1] in legal if legal else fields[1] == "0000"), "not an oracle-legal bestmove")
    return publications


def run_shipping(record, transport, out, raw, oracle, *, eof_only=False):
    label = record["id"] + "-" + transport + ("-eof" if eof_only else "-policy")
    run_dir = out / "runs" / label
    run_dir.mkdir(parents=True)
    cwd, temporary = run_dir / "cwd", run_dir / "tmp"
    cwd.mkdir(); temporary.mkdir()
    program = record["command"][0] if transport == "wrapper" else record["native"]
    program_hash = record["whole_sha256"] if transport == "wrapper" else record["native_sha256"]
    spec = {"command": [program], "cwd": str(cwd), "workers": 2, "startup_timeout": 60,
            "expected_program_sha256": program_hash}
    previous_tmp = os.environ.get("TMPDIR")
    os.environ["TMPDIR"] = str(temporary)
    engine = None
    row = {"id": record["id"], "transport": transport, "scope": "actual pinned shipping executable", "passed": False}
    board = oracle.Board.from_fen()
    black = board.play("e2e4")
    minimal = record["id"] == "minimal"
    try:
        engine = raw.RawEngine(spec, run_dir, "events", timeout=3)
        engine.initialize()
        startup = [event["value"] for event in engine.events if event["direction"] == "stdout"]
        expected_startup = ["uciok", "readyok"] if minimal else ["id name Rove4k A", "uciok", "readyok"]
        require(startup == expected_startup, "actual UCI handshake violates selected policy")
        row["startup"] = runtime_snapshot(engine, record["native_sha256"], cwd, temporary)
        if eof_only:
            require(engine.ready(b"position startpos\ngo wtime 300000 btime 300000\n") == ["readyok"], "long epoch completed before EOF fixture")
            row["pre_eof"] = engine.active_observation(.25)
            output = engine.finish(final=None)
            require(len(best_line(output, board)) == 1, "EOF must settle exactly one outstanding epoch")
            row["shutdown"] = "EOF; outstanding epoch settled, readers joined, native process absent"
        else:
            row["clocks"] = []
            clocks = [(b"", "wtime 0 btime 9223372036854775807 winc 0 binc 999", board),
                      (b"", "binc 999 btime 9223372036854775807 wtime 0 winc 0", board),
                      (b" moves e2e4", "wtime 9223372036854775807 btime 0 winc 999 binc 0", black),
                      (b" moves e2e4", "binc 0 btime 0 winc 999 wtime 9223372036854775807", black),
                      (b"", "wtime 900 btime 0 winc 200 binc 0", board)]
            for moves, fields, root in clocks:
                require(engine.ready(b"position startpos"+moves+b"\n") == ["readyok"], "position barrier emitted stale result")
                started = time.monotonic()
                engine.send(("go "+fields+"\n").encode())
                result = engine.best(root, timeout=3)
                row["clocks"].append({"fields": fields, "result": result, "elapsed_bound_seconds": time.monotonic()-started})
                require(engine.ready() == ["readyok"], "clock epoch duplicated result")
            if minimal:
                row["default_go"] = []
                for fields in ("", "infinite"):
                    require(engine.ready(b"position startpos\n") == ["readyok"], "default-go position barrier")
                    started = time.monotonic()
                    engine.send(("go"+(" "+fields if fields else "")+"\n").encode())
                    result = engine.best(board, timeout=3)
                    elapsed = time.monotonic()-started
                    require(.25 <= elapsed <= 3, "clockless go not observably bounded near its nonzero default")
                    require(engine.ready() == ["readyok"], "default-go result duplicated")
                    row["default_go"].append({"fields": fields, "result": result, "elapsed_seconds": elapsed,
                                              "exact_1000ms_proof": "separate fixed-clock instrumented actual go"})
            # Start a ten-second budget but cancel it within this bounded test.
            require(engine.ready(b"position startpos\ngo wtime 300000 btime 300000\n") == ["readyok"], "long epoch completed prematurely")
            row["before_controls"] = engine.active_observation(.25)
            lines = engine.ready(b"stop\nucinewgame\n")
            if minimal:
                require(lines == ["readyok"], "ignored commands cancelled/published an epoch")
                require(engine.quiet(.08) == [], "ignored commands produced an early result")
                row["after_ignored_controls"] = engine.active_observation(.25)
            else:
                require(len(best_line(lines, board)) == 1 and lines[-1] == "readyok", "legacy stop did not settle its epoch before ready")
                require(engine.ready(b"go wtime 300000 btime 300000\n") == ["readyok"], "legacy restart unexpectedly ended")
            # next go must settle old work before starting one new epoch.
            engine.send(b"go wtime 0 btime 0\nisready\n")
            lines = engine.until(lambda line: line == "readyok", timeout=3)
            publications = best_line(lines, board)
            require(1 <= len(publications) <= 2, "next-go barrier lost/duplicated old epoch")
            if len(publications) == 1:
                engine.best(board, timeout=3)
            require(engine.ready() == ["readyok"], "next-go left duplicate publication")
            # position must settle before committing a different root.
            require(engine.ready(b"position startpos\ngo wtime 300000 btime 300000\n") == ["readyok"], "position-fence setup")
            lines = engine.ready(b"position startpos moves e2e4\n")
            require(len(best_line(lines, board)) == 1 and lines[-1] == "readyok", "position did not settle old root before ready")
            engine.send(b"go wtime 9223372036854775807 btime 0\n")
            engine.best(black, timeout=3)
            require(engine.ready() == ["readyok"], "new black-root result duplicated")
            row["after_fences"] = runtime_snapshot(engine, record["native_sha256"], cwd, temporary)
            # Active quit exercises the last internal wait and physical joins.
            require(engine.ready(b"position startpos\ngo wtime 300000 btime 300000\n") == ["readyok"], "quit-fence setup")
            before = sum(event["direction"] == "stdout" and event["value"].startswith("bestmove ") for event in engine.events)
            output = engine.finish(final=b"quit\n")
            # Earlier black-root moves were independently checked above, so do
            # not validate their legality against the current white root again.
            published = [line for line in output if line.startswith("bestmove ")]
            best_line(published[-1:], board)
            all_best = len(published)
            require(all_best == before+1, "active quit must settle exactly one outstanding epoch")
            row["shutdown"] = "quit; outstanding epoch settled, readers joined, native process absent"
            row["stop_causal_link"] = "unproven; ignored-policy arithmetic/dispatch is established separately"
        require(not list(cwd.iterdir()) and not list(temporary.iterdir()), "files remained after shutdown")
        require(not any(event["direction"] == "stderr" for event in engine.events), "actual executable emitted stderr")
        row["passed"] = True
        return row
    finally:
        if engine is not None:
            engine.cleanup()
        if previous_tmp is None:
            os.environ.pop("TMPDIR", None)
        else:
            os.environ["TMPDIR"] = previous_tmp


def run_dev(record, out, raw, oracle):
    work = out / "dev"
    work.mkdir()
    spec = {"command": [record["dev"]], "cwd": str(work), "workers": 2,
            "expected_program_sha256": record["dev_native_sha256"]}
    engine = raw.RawEngine(spec, work, "events", timeout=3)
    try:
        engine.initialize()
        require(any(event["direction"] == "stdout" and event["value"].startswith("id ") for event in engine.events), "DEV lost id output")
        require(engine.ready(b"position startpos\ngo infinite\n") == ["readyok"], "DEV go infinite completed")
        observed = engine.active_observation(.15)
        lines = engine.ready(b"stop\n")
        require(len(best_line(lines, oracle.Board.from_fen())) == 1, "DEV stop no longer settles work")
        require(engine.ready(b"ucinewgame\n") == ["readyok"], "DEV newgame duplicated result")
        engine.send(b"go depth 1\n")
        engine.best(oracle.Board.from_fen())
        engine.finish()
        return {"passed": True, "program_sha256": record["dev_native_sha256"], "active_observation": observed,
                "scope": "strict unchanged DEV id/infinite/stop/newgame/depth behavior; physical join"}
    finally:
        engine.cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(sys.platform == "linux" and Path("/proc/self/task").is_dir(), "requires Linux with /proc")
    require(args.out.is_absolute(), "output must be absolute")
    out = args.out.resolve()
    require(not out.exists() and not any((p / ".git").exists() for p in (out, *out.parents)), "new external output directory required")
    build_bytes = args.build.read_bytes()
    build = json.loads(build_bytes)
    require(build.get("complete") is True, "build is incomplete")
    records = build["engines"]
    require({record["id"] for record in records} == {"baseline", "minimal"} and len(records) == 2, "requires exactly baseline and one minimal policy")
    for record in records:
        for path, digest in ((record["command"][0], record["whole_sha256"]), (record["native"], record["native_sha256"]),
                             (record["dev"], record["dev_native_sha256"]), (record["readable"], record["readable_sha256"])):
            require(sha(Path(path).read_bytes()) == digest, "build artifact identity mismatch: " + path)
    require(records[0]["dev_source_sha256"] == records[1]["dev_source_sha256"] and
            records[0]["dev_native_sha256"] == records[1]["dev_native_sha256"], "DEV identity changed")
    out.mkdir(parents=True)
    report = {"complete": False, "build_sha256": sha(build_bytes), "validator_sha256": sha(Path(__file__).read_bytes()),
              "scope": "one explicit shipping policy; separate legacy/DEV controls and instrumented nonphysical proofs", "runs": []}
    try:
        recipe = out / "recipe"
        helper = recipe / "engines/experiments/tiny-protocol/edges.py"
        oracle_path = recipe / "engines/tests/chess_oracle.py"
        helper.parent.mkdir(parents=True)
        oracle_path.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "engines/experiments/tiny-protocol/edges.py", helper)
        shutil.copyfile(ROOT / "engines/tests/chess_oracle.py", oracle_path)
        shutil.copyfile(Path(__file__), recipe / "verify.py")
        report["frozen_helpers"] = {str(p.relative_to(recipe)): sha(p.read_bytes()) for p in (helper, oracle_path)}
        raw = module("tiny_uci_raw_frozen", helper)
        oracle = sys.modules["chess_oracle"]
        report["oracle_self_check"] = oracle.self_check()
        report["instrumented"] = units(records, out)
        for record in records:
            for transport in ("native", "wrapper"):
                for eof in (False, True):
                    report["runs"].append(run_shipping(record, transport, out, raw, oracle, eof_only=eof))
                    save(out / "results.json", report)
        report["dev"] = run_dev(records[0], out, raw, oracle)
        report["complete"] = True
    except Exception as error:
        report["failure"] = repr(error)
        raise
    finally:
        save(out / "results.json", report)
    print(json.dumps({"complete": True, "shipping_runs": len(report["runs"]), "instrumented_forms": len(report["instrumented"]),
                      "DEV": report["dev"]["passed"], "out": str(out)}))


if __name__ == "__main__":
    main()
