"""Lean, bounded fixed-work comparison of measured D board/search bodies.

Preparation compiles but does not execute search. Run the prepared cohort only
after competing builders have stopped. This hosted, single-worker experiment
keeps the shipping clock/memory operations and 128-MiB TT; it is not the packed
runtime, a multicore throughput result, or an Elo/qualification measurement.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import statistics
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("D_fixed_work_cost", HERE / "structural_size.py")
h = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = h
_spec.loader.exec_module(h)
_search_next = h.load("D_benchmark_search_dependencies", HERE / "structural_search_next.py")

POSITIONS = (
    "",
    "e2e4 e7e5 g1f3 b8c6",
    "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4",
    "d2d4 d7d5 c2c4 e7e6 b1c3 g8f6",
    "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 e1g1",
    "e2e4 h7h6 e4e5 d7d5 e5d6",
)
CLAIM_BEFORE = b"static int claim(Worker *w){\n"
CLAIM_AFTER = (CLAIM_BEFORE +
    b"    if(++test_claims==test_cancel_at){atomic_store(&stopped,1);return 0;}\n")
TOOLS = ("structural_benchmark.py", "structural_size.py", "structural_search_next.py", "check_storage.py")
HOST_PATH = h.ROOT / "engines/experiments/tcec-scope/build.py"


def _function(source: bytes, name: str) -> bytes:
    """Extract one finite runtime body, preserving its exact measured spelling."""
    pattern = rb"^[A-Za-z_][^;={\n]*\b" + name.encode() + rb"\([^;{}\n]*\)\s*\{"
    matches = list(re.finditer(pattern, source, re.M))
    if len(matches) != 1:
        raise ValueError("one measured runtime function required: " + name)
    match = matches[0]
    end, depth = match.end(), 1
    while depth and end < len(source):
        depth += (source[end] == 123) - (source[end] == 125)
        end += 1
    if depth:
        raise ValueError("unbalanced measured runtime function: " + name)
    return source[match.start():end]


DRIVER = r'''#include "tiny.h"
extern int printf(const char *,...);
Entry *table;
Worker workers[WORKERS];
atomic_int stopped;
uint64_t deadline,game_keys[HISTORY];
int game_length;
Board position;
static uint64_t test_claims,test_cancel_at;
@RUNTIME@
#include "board.c"
@DEPENDENCIES@
#include "search.c"

/* Observe only outside the timed interval. No per-node/path hashing remains. */
static uint64_t hash_word(uint64_t h,uint64_t n){return (h^n)*UINT64_C(1099511628211);}
static uint64_t clock_ns(long clock){
    long t[2];if(Dsc2(228,clock,(long)t))abort();
    return (uint64_t)t[0]*UINT64_C(1000000000)+(uint64_t)t[1];
}
static uint64_t learners(const Worker *w){
    uint64_t h=UINT64_C(1469598103934665603);
    for(int a=0;a<64;a++)for(int b=0;b<64;b++)
        h=hash_word(h,w->history[(a/8)*16+a%8][(b/8)*16+b%8]);
    for(int a=0;a<13;a++)for(int b=0;b<13;b++)h=hash_word(h,w->continuation[a][b]);
    for(int a=0;a<1024;a++)h=hash_word(h,(uint16_t)w->correction[a]);
    return h;
}
static uint64_t tt_digest(void){
    uint64_t h=UINT64_C(1469598103934665603);
    for(size_t i=0;i<((size_t)1<<TT_BITS);i++){
        h=hash_word(h,table[i].key);h=hash_word(h,table[i].data);
    }
    return h;
}
static uint64_t root_digest(const Board *p){
    uint64_t h=UINT64_C(1469598103934665603);
    h=hash_word(h,p->h);h=hash_word(h,p->r);
    h=hash_word(h,(unsigned)p->s);h=hash_word(h,(unsigned)p->v);
    h=hash_word(h,(unsigned)p->e);h=hash_word(h,(unsigned)p->c);
    h=hash_word(h,(unsigned)p->half);
    for(int i=0;i<2;i++)h=hash_word(h,(unsigned)p->k[i]);
    for(int i=0;i<128;i++)h=hash_word(h,(unsigned char)p->b[i]);
    return h;
}
static int replay(Board *p,const char *moves){
    start(p);game_length=1;game_keys[0]=p->h;
    while(*moves){
        while(*moves==' ')moves++;
        if(!*moves)break;
        char name[6];unsigned n=0;
        while(*moves&&*moves!=' '){if(n==5)return 0;name[n++]=*moves++;}
        name[n]=0;if(n!=4&&n!=5)return 0;
        unsigned from=(unsigned)(name[0]-'a')+16u*(unsigned)(name[1]-'1');
        unsigned to=(unsigned)(name[2]-'a')+16u*(unsigned)(name[3]-'1'),promotion=0;
        if(n==5){for(promotion=2;promotion<6&&"  nbrq"[promotion]!=name[4];promotion++);if(promotion==6)return 0;}
        Move wanted=MOVE(from,to,promotion),list[MOVES];int found=0,count=gen(p,list);Board next;
        for(int i=0;i<count;i++)if((list[i]&~8u)==wanted&&make(p,list[i],&next)){found=1;break;}
        if(!found||game_length==HISTORY)return 0;
        *p=next;game_keys[game_length++]=p->h;
    }
    return 1;
}
int main(void){
    static const char *openings[]={@POSITIONS@};
    size_t table_bytes=((size_t)1<<TT_BITS)*sizeof *table;
    table=allocate(table_bytes);if(!table||(uintptr_t)table%16)return 2;
    for(unsigned i=0;i<sizeof openings/sizeof *openings;i++){
        memset(&workers[0],0,sizeof workers[0]);memset(table,0,table_bytes);
        memset(game_keys,0,sizeof game_keys);
        if(!replay(&position,openings[i]))return 3;
        Worker *w=&workers[0];w->id=0;w->best=0;
        test_claims=0;test_cancel_at=UINT64_C(@BUDGET@)+1;
        deadline=UINT64_MAX;atomic_store_explicit(&stopped,0,memory_order_relaxed);
        uint64_t cpu0=clock_ns(2),wall0=clock_ns(1);
        think(w,&position);
        uint64_t wall1=clock_ns(1),cpu1=clock_ns(2);
        /* A cancelled narrow PVS call may try another zero-work call before
         * its caller sees stopped. Keep those actual claim counts observable. */
        if(w->nodes!=UINT64_C(@BUDGET@)||test_claims<test_cancel_at||
           !atomic_load(&stopped)||!w->depth||wall1<=wall0||cpu1<=cpu0)return 4;
        Move list[MOVES];int count=gen(&position,list),legal=0;Board q;
        for(int j=0;j<count;j++)if(list[j]==w->best&&make(&position,list[j],&q)){legal=1;break;}
        if(!legal)return 5;
        uint64_t path=UINT64_C(1469598103934665603);
        for(int j=0;j<game_length;j++)path=hash_word(path,game_keys[j]);
        for(int j=0;j<PLY;j++)path=hash_word(path,w->keys[j]);
        printf("{\"position\":%u,\"nodes\":%llu,\"claims\":%llu,\"depth\":%d,\"score\":%d,\"best\":%u,"
               "\"root\":\"%016llx\",\"learners\":\"%016llx\",\"tt\":\"%016llx\",\"path\":\"%016llx\","
               "\"wall_ns\":%llu,\"cpu_ns\":%llu}\n",i,
               (unsigned long long)w->nodes,(unsigned long long)test_claims,w->depth,w->score,w->best,
               (unsigned long long)root_digest(&position),(unsigned long long)learners(w),
               (unsigned long long)tt_digest(),(unsigned long long)path,
               (unsigned long long)(wall1-wall0),(unsigned long long)(cpu1-cpu0));
    }
    return 0;
}
'''


def render(files: dict[str, bytes], *, budget: int = 100000) -> tuple[dict[str, bytes], dict]:
    """Pure rendering; search differs only at the old claim-cancellation port."""
    if not 4096 <= budget <= 1000000:
        raise ValueError("fixed node budget must be between 4096 and 1000000")
    if files["search.c"].count(CLAIM_BEFORE) != 1:
        raise ValueError("unique actual claim checkpoint required")
    dependencies = _search_next.runtime_dependencies(files)
    names = ("Dsc1", "Dsc2", "Dsc6", "memcpy", "memset", "memcmp", "abort", "allocate", "now")
    runtime = {name: _function(files["runtime.c"], name) for name in names}
    driver = DRIVER.replace("@RUNTIME@", b"\n".join(runtime.values()).decode())
    driver = driver.replace("@DEPENDENCIES@", dependencies.decode())
    driver = driver.replace("@POSITIONS@", ",\n".join(json.dumps(p) for p in POSITIONS))
    driver = driver.replace("@BUDGET@", str(budget)).encode()
    generated = {name: files[name] for name in ("tiny.h", "board.c", "search.c")}
    generated["search.c"] = files["search.c"].replace(CLAIM_BEFORE, CLAIM_AFTER)
    generated["driver.c"] = driver
    proof = {"budget": budget, "positions": list(POSITIONS), "input": h.inventory(files),
             "claim_before": h.pin(CLAIM_BEFORE), "claim_after": h.pin(CLAIM_AFTER),
             "runtime_functions": h.inventory(runtime), "terminal_dependency": h.pin(dependencies),
             "generated": h.inventory(generated)}
    return generated, proof


def _tools() -> dict:
    paths = [HERE / name for name in TOOLS] + [HOST_PATH]
    return {str(p.relative_to(h.ROOT)): h.pin(p.read_bytes()) for p in paths}


def _new_output(path) -> Path:
    path = h.new_output(path)
    path.mkdir(parents=True)
    return path


def _host(out, report, save, *, aggregate=180):
    module = h.load("D_fixed_work_host", HOST_PATH)
    module.LIMITS = {**module.LIMITS, "aggregate_wall": aggregate, "per_command_wall": 60,
                     "parent_CPU": 1200, "parent_CPU_hard": 1260, "child_CPU": 50,
                     "child_AS": 2 << 30, "tool_output_bytes": 1 << 20}
    report["limits"] = module.LIMITS
    return module.Host(out, report, save)


def prepare(cases, out, *, budget=100000):
    """Pin measured inputs, reuse the existing claim port, compile without search."""
    cases = [Path(p).resolve() for p in cases]
    if not 2 <= len(cases) <= 8 or len({p.name for p in cases}) != len(cases):
        raise ValueError("two to eight uniquely named cases required; first is control")
    storage = h.load("D_fixed_work_existing_port", HERE / "check_storage.py")
    class Capture:
        @staticmethod
        def project(source, edits):
            return source, edits
    _, edits = storage.instrument(Capture, {"search.c": b""})
    claim = [edit[1:] for edit in edits if edit[0] == "claim-checkpoint"]
    if claim != [(CLAIM_BEFORE, CLAIM_AFTER)]:
        raise ValueError("benchmark claim port differs from the existing observer")
    out = _new_output(out)
    report = {"complete": False, "prepared": False, "search_executed": False, "tools": _tools(),
              "commands": [], "cases": [], "budget": budget, "positions": list(POSITIONS),
              "active_workers": 1, "compiled_workers": 4, "tt_bytes": 128 << 20,
              "scope": "actual board/search bodies, hosted libc main, one active worker 0; not shipping binary timing",
              "clock": "actual shipping now() retained; CLOCK_MONOTONIC and process CPU bracket think()",
              "excluded_from_timing": ["TT/worker reset", "opening replay", "final result/learner/TT/path hashes", "output"],
              "included_overhead": "one existing claim-cancellation counter/check per claim"}
    def save():
        report["prepared"] = report["complete"] is True
        try:
            (out / "prepared.json").write_text(json.dumps(report, indent=2) + "\n")
        except BaseException:
            report["prepared"] = False
            raise
    host = None; body_error = None
    try:
        host = _host(out, report, save)
        report["compiler"] = host.run(["cc", "--version"], cwd=out, kind="compiler").decode().splitlines()[0]
        original_flags = None
        for case in cases:
            cost_bytes = (case / "result.json").read_bytes()
            cost = json.loads(cost_bytes)
            h.require_settled_cost(cost)
            files = {name: (case / "generated-readable" / name).read_bytes() for name in h.FILES}
            if h.inventory(files) != cost["input"]:
                raise ValueError("source no longer matches its completed cost run: " + str(case))
            if cost["profile"] != "test-p4" or cost["compiler"] != report["compiler"]:
                raise ValueError("same measured P4 compiler/profile required")
            if original_flags is None:
                original_flags = cost["flags"]
            if cost["flags"] != original_flags or not all(flag in cost["flags"] for flag in
                    ("-DDEV=0", "-DD_HQ=0", "-DWORKERS=4", "-DTT_BITS=23")):
                raise ValueError("identical shipping optimization and resource flags required")
            generated, proof = render(files, budget=budget)
            directory = out / case.name
            source_dir, bench_dir = directory / "input", directory / "bench"
            source_dir.mkdir(parents=True); bench_dir.mkdir()
            for name, data in files.items():
                (source_dir / name).write_bytes(data)
            for name, data in generated.items():
                (bench_dir / name).write_bytes(data)
            (directory / "cost.json").write_bytes(cost_bytes)
            # Hosted main/printf replaces only process startup and output.
            # Actual board/search, memory bodies, TT width and clock stay pinned.
            flags = [flag for flag in cost["flags"] if flag not in ("-nostdlib", "-static")]
            binary = bench_dir / "bench"
            row = {"name": case.name, "source_case": str(case), "cost": h.pin(cost_bytes),
                   "proof": proof, "flags": flags, "binary": None}
            report["cases"].append(row); save()
            host.run(["cc", *flags, str(bench_dir / "driver.c"), "-o", str(binary)],
                     cwd=bench_dir, kind="compile-" + case.name)
            row["binary"] = h.pin(binary.read_bytes()); save()
    except BaseException as error:
        body_error = error
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        h.finish_report(host, report, save, body_error)
    return report


def run(prepared, out, *, repeats=3, cpu=None):
    """Execute serially, accepting timings only after all fixed-work states agree."""
    prepared = Path(prepared).resolve()
    raw = (prepared / "prepared.json").read_bytes(); spec = json.loads(raw)
    h.require_settled_cost(spec)
    if spec.get("prepared") is not True or spec.get("search_executed") is not False or not 1 <= repeats <= 5:
        raise ValueError("completed preparation and one to five repetitions required")
    if spec["tools"] != _tools():
        raise ValueError("benchmark/observer tools changed after preparation")
    allowed = os.sched_getaffinity(0)
    if cpu is None:
        cpu = min(allowed)
    if cpu not in allowed:
        raise ValueError("requested CPU is outside this process's allowed affinity")
    for case in spec["cases"]:
        directory = prepared / case["name"]
        if (h.pin((directory / "cost.json").read_bytes()) != case["cost"] or
            h.inventory({name: (directory / "input" / name).read_bytes() for name in h.FILES}) != case["proof"]["input"] or
            h.inventory({name: (directory / "bench" / name).read_bytes() for name in case["proof"]["generated"]}) != case["proof"]["generated"] or
            h.pin((directory / "bench/bench").read_bytes()) != case["binary"]):
            raise ValueError("prepared input or binary changed: " + case["name"])
    out = _new_output(out)
    report = {"complete": False, "prepared": h.pin(raw), "prepared_path": str(prepared),
              "tools": _tools(), "scope": spec["scope"], "clock": spec["clock"],
              "included_overhead": spec["included_overhead"], "excluded_from_timing": spec["excluded_from_timing"],
              "cpu_affinity": [cpu], "original_cpu_affinity": sorted(allowed),
              "affinity_change_attempted": False, "affinity_restored": None,
              "machine": list(os.uname()), "repeats": repeats, "budget": spec["budget"],
              "commands": [], "runs": [], "comparisons": [], "all_observations_equal": False}
    def save():
        (out / "benchmark.json").write_text(json.dumps(report, indent=2) + "\n")
    host = None; body_error = None
    reference = None
    try:
        host = _host(out, report, save, aggregate=600)
        report["affinity_change_attempted"] = True
        os.sched_setaffinity(0, {cpu})
        for repeat in range(repeats):
            order = spec["cases"] if repeat % 2 == 0 else list(reversed(spec["cases"]))
            for case in order:
                directory = prepared / case["name"] / "bench"
                output = host.run([str(directory / "bench")], cwd=directory,
                                  kind=case["name"] + "-r" + str(repeat))
                rows = [json.loads(line) for line in output.decode().splitlines()]
                fields = {"position", "nodes", "claims", "depth", "score", "best", "root", "learners", "tt", "path", "wall_ns", "cpu_ns"}
                if (len(rows) != len(POSITIONS) or any(set(row) != fields or row["position"] != i or
                    row["nodes"] != spec["budget"] or row["claims"] < spec["budget"] + 1 or
                    type(row["score"]) is not int or row["wall_ns"] <= 0 or row["cpu_ns"] <= 0 for i, row in enumerate(rows))):
                    raise ValueError("incomplete fixed-work observation: " + case["name"])
                state = [{k: v for k, v in row.items() if k not in ("wall_ns", "cpu_ns")} for row in rows]
                if reference is None:
                    reference = state
                row = {"name": case["name"], "repeat": repeat, "positions": rows,
                       "observation": h.pin(json.dumps(state, sort_keys=True).encode()),
                       "equal_to_control": state == reference,
                       "cpu_ns": sum(row["cpu_ns"] for row in rows),
                       "wall_ns": sum(row["wall_ns"] for row in rows)}
                report["runs"].append(row); save()
                if state != reference:
                    raise ValueError("fixed-work state differs from control: " + case["name"])
        report["all_observations_equal"] = True
        baseline = spec["cases"][0]["name"]
        control_cpu = statistics.median(r["cpu_ns"] for r in report["runs"] if r["name"] == baseline)
        for case in spec["cases"]:
            runs = [r for r in report["runs"] if r["name"] == case["name"]]
            samples = [r["cpu_ns"] for r in runs]
            median = statistics.median(samples)
            report["comparisons"].append({"name": case["name"], "nodes_per_run": spec["budget"] * len(POSITIONS),
                "cpu_ns_samples": samples, "cpu_ns_median": median, "cpu_ns_min": min(samples), "cpu_ns_max": max(samples),
                "cpu_time_ratio_to_control": median / control_cpu,
                "wall_ns_samples": [r["wall_ns"] for r in runs]})
    except BaseException as error:
        body_error = error
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        restore_error = None
        if report["affinity_change_attempted"]:
            try:
                os.sched_setaffinity(0, allowed)
                report["affinity_restored"] = True
            except BaseException as error:
                restore_error = error
                report["affinity_restored"] = False
                report["affinity_failure"] = {"type": type(error).__name__, "message": str(error)}
        try:
            h.finish_report(host, report, save, body_error if body_error is not None else restore_error)
        finally:
            if restore_error is not None and body_error is None:
                raise restore_error
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("out", type=Path)
    prep.add_argument("cases", nargs="+", type=Path)
    prep.add_argument("--budget", type=int, default=100000)
    execute = commands.add_parser("run")
    execute.add_argument("prepared", type=Path)
    execute.add_argument("out", type=Path)
    execute.add_argument("--repeats", type=int, default=3)
    execute.add_argument("--cpu", type=int)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.cases, args.out, budget=args.budget)
        print(json.dumps({"prepared": result["prepared"], "search_executed": False,
                          "cases": [row["name"] for row in result["cases"]]}))
    else:
        result = run(args.prepared, args.out, repeats=args.repeats, cpu=args.cpu)
        print(json.dumps({"complete": result["complete"], "all_observations_equal": result["all_observations_equal"],
                          "comparisons": result["comparisons"]}))
