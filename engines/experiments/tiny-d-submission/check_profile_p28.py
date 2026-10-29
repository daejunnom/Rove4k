#!/usr/bin/env python3
"""Source-bound D W28/TT25 mechanism diagnostics, never a scored qualification.

The poisoned process checks the entire 512 MiB TT and every page-floor owner.
A separate, unpoisoned process retains all six readable production inputs and
uses only an extra syscall-only TU plus linker wrappers. Its one 60s deadline
includes the intentional startup hold, two legal GO cycles and physical exit.
Neither diagnostic native is the submission native. Poisoning changes NUMA
first touch; local task counts do not establish physical placement or strength.
"""
from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import signal
import sys
import time

sys.dont_write_bytecode = True
_EXECUTING_CODE = sys._getframe().f_code
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = "engines/experiments/tiny-d-submission/"
SELF = D + "check_profile_p28.py"
STARTUP = D + "test_startup.py"
SOURCE_INPUTS = D + "source_inputs.py"
RECIPE = "engines/compact/tiny-entry-d/recipe.json"
VERIFIER = "engines/experiments/tcec-next/profile_verify.py"
READER = "engines/scripts/production_input.py"
OWNER = "engines/experiments/tcec-scope/build.py"
RUNTIME = "engines/compact/tiny-entry-d/verify.py"
SCOPE = "engines/experiments/tcec-scope/verify.py"
ORACLE = "engines/tests/chess_oracle.py"
SCHEMA = "rove4k-D-bound-p28-mechanism-v1"
PROFILE = "test-p28"
WORKERS, BITS, ENTRY, PAGE_ENTRIES = 28, 25, 16, 256
ENTRIES, TT_BYTES = 1 << BITS, (1 << BITS) * ENTRY
STARTUP_SECONDS = 60
NATIVE = ("tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld")
CASES = (("full-entry-positive", 0), ("full-entry-omit-clear", 7), ("full-entry-omit-page-owner", 8))


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def executing_source(data):
    require(isinstance(data, bytes) and compile(data, __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "D P28 frozen checker differs from its executing code")
    return pin(data)


def normalized(path):
    data = Path(path).read_bytes()
    require(len(data) <= 16 << 20, "named source exceeds 16 MiB")
    data = data.replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named source: " + str(path))
    return data


def json_equal(left, right):
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(right, sort_keys=True, separators=(",", ":"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def literal(source, name):
    values = [node.value for node in ast.parse(source).body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
    require(len(values) == 1, "one literal support declaration required: " + name)
    return ast.literal_eval(values[0])


def geometry(resources):
    expected = {"id": PROFILE, "workers": WORKERS, "tt_bits": BITS, "tt_entries": ENTRIES,
                "tt_bytes": TT_BYTES, "tt_entry_bytes": ENTRY, "tt_mask": ENTRIES - 1}
    require(isinstance(resources, dict) and all(type(resources.get(k)) is type(v) and resources[k] == v
            for k, v in expected.items()), "actual integer W28/TT25/16-byte geometry required")
    pages = ENTRIES // PAGE_ENTRIES
    ranges = [(pages * n // WORKERS * PAGE_ENTRIES,
               pages * (n + 1) // WORKERS * PAGE_ENTRIES) for n in range(WORKERS)]
    require(ranges[0][0] == 0 and ranges[-1][1] == ENTRIES and
            all(ranges[n][1] == ranges[n + 1][0] for n in range(WORKERS - 1)) and
            all(a < b and a * ENTRY % 4096 == b * ENTRY % 4096 == 0 for a, b in ranges),
            "D P28 page-floor partition differs")
    counts = {str(size): sum((b - a) // PAGE_ENTRIES == size for a, b in ranges)
              for size in sorted({(b - a) // PAGE_ENTRIES for a, b in ranges})}
    require(counts == {"4681": 24, "4682": 4}, "D P28 floor remainder differs")
    return {**expected, "pages": pages, "page_entries": PAGE_ENTRIES, "page_bytes": 4096,
            "page_counts": counts, "ranges": [dict(worker=n, begin=a, end=b) for n, (a, b) in enumerate(ranges)]}


def bound_selection(manifest):
    require(isinstance(manifest, dict) and manifest.get("format") == "rove4k-D-general-source-v1" and
            manifest.get("family") == "D" and manifest.get("storage") == "prefix" and
            manifest.get("source_reduced") is False and manifest.get("equivalent_edits") is True and
            all(manifest.get(k) is True for k in ("complete", "frozen_execution", "native_reproduced")),
            "complete base/prefix equivalent unreduced D P28 selection required")
    return geometry(manifest.get("resource"))


def source_binding(files, proof, manifest, selected):
    require(set(files) == set(selected) == set(NATIVE) and files == selected and
            json_equal(proof, manifest.get("proof")), "D P28 complete readable source/proof differs")
    return {name: pin(data) for name, data in sorted(files.items())}


def poison_fixture(files, source, *, negative=None):
    """Retain production floor bounds and clear, with two explicitly named faults."""
    require(set(files) == set(NATIVE) and negative in (None, "omit-clear", "omit-page-owner"),
            "finite full D readable fixture/negative required")
    original = files["runtime.c"]
    clear = b"    memset(table+begin,0,(end-begin)*sizeof *table);"
    owner = (b"    for(size_t p=begin/256;p<end/256;p++)"
             + (b"if(p)" if negative == "omit-page-owner" else b"")
             + b"if(atomic_exchange_explicit(test_p28_owners+p,(unsigned)w->id+1,memory_order_relaxed))abort();\n"
             b"    if(atomic_fetch_add_explicit(test_p28_arrived+w->id,1,memory_order_relaxed))abort();\n")
    roles = [
        ("test-page-owner-storage", b"static Move fallback;", b"static Move fallback;\n"
         b"static atomic_uint test_p28_owners[((size_t)1<<TT_BITS)/256],test_p28_arrived[WORKERS];"),
        ("test-poison-all-entry-fields-before-spawn",
         b"table=allocate(((size_t)1<<TT_BITS)*sizeof *table);if(!table)return 2;start(&position);",
         b"table=allocate(((size_t)1<<TT_BITS)*sizeof *table);if(!table)return 2;"
         b"memset(table,165,((size_t)1<<TT_BITS)*sizeof *table);start(&position);"),
        ("test-page-owners-before-unchanged-clear" if negative is None else "test-negative-" + negative,
         clear, owner + (b"    (void)begin;(void)end;" if negative == "omit-clear" else clear)),
        ("test-complete-entry-fields-after-real-acquire-barrier",
         b"    if(status)goto shutdown;\n    wait();\n    for(;;){",
         b"    if(status)goto shutdown;\n    wait();\n"
         b"    _Static_assert(WORKERS==28 && TT_BITS==25 && sizeof(Entry)==16 && offsetof(Entry,key)==0 && offsetof(Entry,data)==8,\"P28 exact full field geometry\");\n"
         b"    for(size_t e=0;e<((size_t)1<<TT_BITS);e++)if(table[e].key||table[e].data){output(\"TEST_POISON_REMAINS\\n\");status=7;goto shutdown;}\n"
         b"    for(size_t p=0;p<((size_t)1<<TT_BITS)/256;p++)if(atomic_load_explicit(test_p28_owners+p,memory_order_relaxed)!=((p+1)*WORKERS-1)/(((size_t)1<<TT_BITS)/256)+1){output(\"TEST_OWNER_DIFFERS\\n\");status=8;goto shutdown;}\n"
         b"    for(int i=0;i<WORKERS;i++)if(atomic_load_explicit(test_p28_arrived+i,memory_order_relaxed)!=1){output(\"TEST_ARRIVAL_DIFFERS\\n\");status=9;goto shutdown;}\n"
         b"    output(\"TEST_INITIALIZED\\n\");\n    for(;;){"),
    ]
    result = dict(files)
    result["runtime.c"], proof = source.project(original, roles)
    require(source.restore(result["runtime.c"], proof) == original, "D P28 diagnostic full inverse differs")
    require(all(result[name] == files[name] for name in NATIVE if name != "runtime.c"), "diagnostic changed another unit")
    return result, {"negative": negative, "runtime": proof, "source": {n: pin(d) for n, d in files.items()},
                    "outputs": {n: pin(d) for n, d in result.items()}, "full_inverse": True,
                    "production_floor_bounds_changed": False, "production_clear_changed": negative == "omit-clear"}


def startup_wrapper(paths):
    """Extra no-libc TU: original fn/arg/stack/clear_tid and six units stay intact."""
    require(set(paths) == {"arrived", "release", "joined", "exit_release"} and
            len(set(str(v) for v in paths.values())) == 4 and all(Path(v).is_absolute() for v in paths.values()),
            "four distinct absolute diagnostic marker paths required")
    names = {k: json.dumps(str(v)) for k, v in paths.items()}
    return (r'''#include "tiny.h"
extern long __real_spawn(void (*)(void *),void *,void *,int *);
extern int __real_main(void);
static long rv28_call(long n,long a,long b,long c,long d,long e,long f){
 register long r10 __asm__("r10")=d,r8 __asm__("r8")=e,r9 __asm__("r9")=f;long z;
 __asm__ volatile("syscall":"=a"(z):"a"(n),"D"(a),"S"(b),"d"(c),"r"(r10),"r"(r8),"r"(r9):"rcx","r11","memory");return z;
}
#define RC(n,a,b,c,d,e,f) rv28_call(n,(long)(a),(long)(b),(long)(c),(long)(d),(long)(e),(long)(f))
static void rv28_close(long fd){long z=RC(3,fd,0,0,0,0,0);if(z&&z!=-4)abort();}
static void rv28_marker(const char*p){long fd;do{fd=RC(2,p,193,0600,0,0,0);}while(fd==-4);if(fd<0)abort();
 const char*s="ok\n";long n=3;while(n){long z=RC(1,fd,s,n,0,0,0);if(z==-4)continue;if(z<=0||z>n)abort();s+=z;n-=z;}rv28_close(fd);}
static void rv28_gate(const char*p){for(;;){long fd=RC(2,p,0,0,0,0,0);if(fd>=0){rv28_close(fd);return;}
 if(fd!=-2&&fd!=-4)abort();long t[2]={0,1000000};RC(35,t,0,0,0,0,0);}}
typedef struct{void(*fn)(void*);void*arg;unsigned id;} rv28_context;
static rv28_context rv28_contexts[WORKERS];
static atomic_uint rv28_called,rv28_entered[WORKERS],rv28_returned[WORKERS];
static void rv28_trampoline(void*p){rv28_context*c=p;
 if(c->id>=WORKERS||c!=rv28_contexts+c->id||c->arg!=workers+c->id||
 atomic_fetch_add_explicit(rv28_entered+c->id,1,memory_order_acq_rel))abort();
 if(c->id==WORKERS-1){rv28_marker(@arrived@);rv28_gate(@release@);}
 c->fn(c->arg);if(atomic_fetch_add_explicit(rv28_returned+c->id,1,memory_order_release))abort();}
long __wrap_spawn(void(*fn)(void*),void*arg,void*stack,int*tid){unsigned n=atomic_fetch_add_explicit(&rv28_called,1,memory_order_relaxed);
 if(n>=WORKERS||!fn||!stack||!tid||arg!=workers+n||((Worker*)arg)->id!=(int)n||
 (uintptr_t)stack%16||(uintptr_t)tid%_Alignof(atomic_int))abort();rv28_contexts[n]=(rv28_context){fn,arg,n};
 return __real_spawn(rv28_trampoline,rv28_contexts+n,stack,tid);}
int __wrap_main(void){_Static_assert(WORKERS==28&&TT_BITS==25,"P28 unchanged resource flags");int status=__real_main();
 if(status||atomic_load_explicit(&rv28_called,memory_order_acquire)!=WORKERS)abort();
 for(unsigned i=0;i<WORKERS;i++)if(atomic_load_explicit(rv28_entered+i,memory_order_acquire)!=1||
 atomic_load_explicit(rv28_returned+i,memory_order_acquire)!=1)abort();
 rv28_marker(@joined@);rv28_gate(@exit_release@);return status;}
'''.replace("@arrived@", names["arrived"]).replace("@release@", names["release"])
            .replace("@joined@", names["joined"]).replace("@exit_release@", names["exit_release"])).encode()


class Deadline:
    def __init__(self, started=None, seconds=STARTUP_SECONDS, *, clock=time.monotonic):
        require(type(seconds) is int and seconds == STARTUP_SECONDS, "one fixed 60-second P28 deadline required")
        self.clock = clock
        self.started = clock() if started is None else started
        require(type(self.started) in (int, float) and math.isfinite(self.started), "finite launch time required")
        self.end = self.started + seconds

    def left(self, maximum=STARTUP_SECONDS):
        require(type(maximum) in (int, float) and math.isfinite(maximum) and maximum > 0, "positive finite deadline cap required")
        remaining = min(maximum, self.end - self.clock())
        if remaining <= 0:
            raise TimeoutError("single D P28 60-second runtime deadline expired")
        return remaining


def mechanism_limits(inherited_cpu):
    """Bound these short mechanisms independently of a 28-core match budget."""
    require(isinstance(inherited_cpu, tuple) and len(inherited_cpu) == 2 and
            all(type(value) is int and (value == -1 or value > 0) for value in inherited_cpu),
            "finite inherited CPU pair or RLIM_INFINITY required")
    soft, hard = inherited_cpu
    require(hard == -1 or (soft != -1 and soft <= hard), "inherited CPU pair is inconsistent")
    require(hard == -1 or hard >= 60, "inherited CPU hard limit is below the mechanism60s minimum")
    parent_hard = 540 if hard == -1 else min(540, hard)
    return dict(aggregate_wall=600, per_command_wall=60, parent_AS=2 << 30, child_AS=2 << 30,
                parent_CPU=min(480, parent_hard), parent_CPU_hard=parent_hard, child_CPU=60)


def launch_capacity(verifier, admitted):
    """Record available memory as telemetry; retain explicit execution limits."""
    available = verifier.effective_available_bytes()
    limits = verifier.execution_limits(admitted, available, wall_seconds=60)
    return {**limits, "launch_headroom": dict(effective_available_bytes=available,
            used_for_admission=False)}


def require_execution(row, expected):
    require(type(expected) is int and expected in (0, 7, 8), "finite D P28 command exit policy required")
    require(row.get("returncode") == expected and type(row.get("returncode")) is int and
            all(row.get(k) is True for k in ("started", "terminal", "reaped", "owned_group_absent",
                "original_identity_retained_until_other_members_absent")) and
            row.get("forced_cleanup") is False and row.get("other_group_members_before_reap") == [],
            "D P28 command exit or original group lifetime differs")


def command_contract(rows):
    expected = [(prefix + "-" + name, code) for name, exit_code in CASES
                for prefix, code in (("compile", 0), ("execute", exit_code))]
    expected.append(("compile-unpoisoned-startup", 0))
    require(len(rows) == len(expected), "exact seven D P28 Host commands required")
    for row, (kind, code) in zip(rows, expected):
        require(row.get("kind") == kind, "D P28 command role/order differs")
        require_execution(row, code)


def _send(owned, data, deadline):
    deadline.left()
    require(isinstance(data, bytes) and len(data) <= 256, "small original-stdin command required")
    owned.sent.extend(data)
    owned.process.stdin.write(data)
    owned.process.stdin.flush()
    deadline.left()


def _line(owned, value, count, deadline):
    owned.stdout.until(lambda data: data.splitlines().count(value) >= count, deadline, seconds=deadline.left())


def _best(owned, count, deadline):
    owned.stdout.until(lambda data: sum(line.startswith(b"bestmove ") for line in data.splitlines()) >= count,
                       deadline, seconds=deadline.left())


def _wait(predicate, owned, deadline, message):
    while not predicate():
        deadline.left()
        require(not owned.exited(), message)
        time.sleep(min(.005, deadline.left()))


def joined_tasks(scope, owned, deadline):
    # clear_tid can wake real main just before proc removes an exiting TID.
    # __wrap_main remains held before exit_group throughout this observation.
    pid = owned.process.pid
    _wait(lambda: set(scope.task_snapshot(pid)) == {pid}, owned, deadline,
          "D P28 joined worker task directories did not physically disappear")
    snapshot = scope.task_snapshot(pid)
    require(set(snapshot) == {pid}, "D P28 actual worker task exit/join is incomplete")
    return snapshot


def construct_owned(runtime, path, directory, deadline, handled):
    deferred = [sig for sig in handled if sig != signal.SIGTERM]
    old, pending = {sig: signal.getsignal(sig) for sig in deferred}, []
    for sig in deferred:
        signal.signal(sig, lambda sig, frame: pending.append((sig, frame)))
    try:
        owned = runtime.Owned(path, directory, deadline)
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)
    if pending:
        sig, frame = pending[0]
        if callable(old[sig]):
            old[sig](sig, frame)
        raise TimeoutError("deferred P28 ownership-construction signal")
    return owned


def natural_finish(owned, deadline):
    while not (owned.exited() and not owned.group_others()):
        deadline.left()
        time.sleep(min(.005, deadline.left()))
    owned.pre_reap_other_members = owned.group_others()
    require(not owned.pre_reap_other_members, "D P28 other group members remain before original reap")
    owned.process.wait(timeout=deadline.left())
    owned.reaped = True
    for reader in (owned.stdout, owned.stderr):
        reader.thread.join(timeout=deadline.left())
        require(not reader.thread.is_alive() and reader.done and not reader.error, "D P28 output reader did not join")
    require(owned.process.returncode == 0 and not owned.stderr.bytes(), "D P28 natural exit/stderr differs")
    owned.finished = True
    return dict(returncode=0, reaped=True, readers_joined=True, stdout_eof=True, stderr_eof=True, forced_cleanup=False,
                pre_reap_other_members=[], original_identity_retained_until_other_members_absent=True)


def drain_owned(runtime, host, report):
    inherited = signal.pthread_sigmask(signal.SIG_BLOCK, set(host.handled))
    try:
        rows, errors = [], []
        for owned in list(runtime.OWNED):
            try:
                rows.append(owned.cleanup())
            except BaseException as error:
                errors.append(str(error))
        prior = report.get("runtime_cleanup", {})
        report["runtime_cleanup"] = dict(drained=prior.get("drained", []) + rows,
            errors=prior.get("errors", []) + errors, remaining_owned=len(runtime.OWNED))
        require(not runtime.OWNED and not report["runtime_cleanup"]["errors"], "D P28 runtime ownership cleanup incomplete")
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, inherited)


def startup_runtime(binary, directory, paths, *, admitted, verifier, runtime, scope, host, report):
    limits = launch_capacity(verifier, admitted)
    require(limits["address_space_bytes"] == 2 << 30, "D P28 requires the admitted 2GiB address-space envelope")
    native = binary.read_bytes()
    owned = None
    started = time.monotonic()
    deadline = Deadline(started)
    try:
        owned = construct_owned(runtime, binary, directory, deadline, host.handled)
        pid = owned.process.pid
        stdin_link = os.readlink(f"/proc/{pid}/fd/0")
        require(stdin_link.startswith("pipe:["), "D P28 original stdin is not a pipe")
        _send(owned, b"uci\nisready\n", deadline)
        _wait(lambda: paths["arrived"].exists(), owned, deadline, "D P28 last callback did not reach its gate")
        before = scope.task_snapshot(pid)
        require(len(before) == 29 and pid in before, "D P28 held startup must expose29 actual tasks")
        hold_end = time.monotonic() + .1
        while time.monotonic() < hold_end:
            deadline.left()
            require(not owned.exited() and owned.stdout.bytes() == b"", "D P28 UCI escaped the held initializer")
            time.sleep(min(.005, deadline.left()))
        require(owned.stdout.bytes() == b"", "D P28 emitted output before gate release")
        paths["release"].write_bytes(b"release\n")
        _line(owned, b"uciok", 1, deadline)
        _line(owned, b"readyok", 1, deadline)
        ready_ms = (time.monotonic() - started) * 1000
        snapshot = scope.image_snapshot(pid, pin(native)["sha256"])
        require(len(snapshot["tasks"]) == 29 and set(snapshot["tasks"]) == set(before), "D P28 idle task set differs")
        account = verifier.resident_accounting(pid)
        resident = {"pid": pid, "startup_resident_accounting": account, "startup_RSS_source": "smaps_rollup",
            "startup_VmRSS_bytes_not_peak": verifier._rss_bytes(snapshot), "startup_RSS_bytes_not_peak": account["Rss_bytes"]}
        verifier.startup_residency(resident, snapshot, TT_BYTES, exact_required=True)
        require(os.readlink(f"/proc/{pid}/fd/0") == stdin_link, "D P28 original stdin pipe changed")
        legal = {f"{f}2{f}{r}".encode() for f in "abcdefgh" for r in "34"} | {b"b1a3", b"b1c3", b"g1f3", b"g1h3"}
        for count in (1, 2):
            _send(owned, b"position startpos\ngo wtime 3000 btime 3000 winc 0 binc 0\n", deadline)
            _best(owned, count, deadline)
            _send(owned, b"isready\n", deadline)
            _line(owned, b"readyok", count + 1, deadline)
            moves = [line[9:] for line in owned.stdout.bytes().splitlines() if line.startswith(b"bestmove ")]
            require(len(moves) == count and all(move in legal for move in moves), "D P28 duplicate or illegal GO output")
        _send(owned, b"position startpos\nisready\n", deadline)
        _line(owned, b"readyok", 4, deadline)
        idle = scope.task_snapshot(pid)
        require(set(idle) == set(before), "D P28 workers did not persist through both GO fences")
        _send(owned, b"quit\n", deadline)
        _wait(lambda: paths["joined"].exists(), owned, deadline, "D P28 main did not return after real worker joins")
        joined = joined_tasks(scope, owned, deadline)
        paths["exit_release"].write_bytes(b"exit\n")
        physical = natural_finish(owned, deadline)
        output = owned.stdout.bytes()
        require(output.splitlines() == [b"uciok", b"readyok", *sum(([line, b"readyok"] for line in
                [r for r in output.splitlines() if r.startswith(b"bestmove ")]), []), b"readyok"] and
                output.count(b"bestmove ") == 2, "D P28 final protocol transcript differs")
        cleanup = owned.cleanup()
        require(cleanup["forced_cleanup"] is False and not cleanup["errors"] and cleanup["owned_group_absent"],
                "D P28 natural runtime cleanup differs")
        (directory.parent / "runtime.stdout").write_bytes(output)
        return dict(host_admission=limits["admission"], launch_headroom=limits["launch_headroom"],
            native=pin(native), output=pin(output), shipping_identity_claimed=False,
            actual_resource_profile=PROFILE, actual_workers=WORKERS, actual_tt_entries=ENTRIES,
            actual_tt_bytes=TT_BYTES, entry_bytes=ENTRY,
            original_stdin_pipe=stdin_link, original_stdin_preserved=True, startup_deadline_ms=60000,
            ready_ms_including_intentional_hold=ready_ms, total_runtime_ms=(time.monotonic() - started) * 1000,
            last_callback_delayed_before_work=True, no_UCI_before_release=True, legal_GO_cycles=2,
            spawn_calls_checked=28, callback_entries_checked=28, callback_returns_checked=28,
            per_ID_callbacks_asserted=[dict(worker=n, entries=1, returns=1) for n in range(WORKERS)],
            markers={name: dict(path=str(path), **pin(path.read_bytes())) for name, path in paths.items()},
            final_position_acquire_fence=True, startup_tasks=before, idle_tasks=idle, joined_tasks=joined,
            startup_snapshot=snapshot, resident=resident, physical=physical, cleanup=cleanup,
            all_workers_positive_CPU_claimed=False, physical_placement_qualified=False, NUMA_qualified=False)
    finally:
        if owned is not None:
            row = dict(directory=str(directory), pid=owned.process.pid, cleanup=owned.cleanup())
            report.setdefault("barrier_runtime_cleanup", []).append(row)


def _write(root, files):
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def freeze_inputs(build, out):
    """Freeze the complete named authority before executing any producer."""
    manifest_raw = normalized(build / "build.json")
    manifest = json.loads(manifest_raw)
    bound_selection(manifest)
    early = {name: normalized(ROOT / name) for name in (SELF, SOURCE_INPUTS, RECIPE, VERIFIER)}
    executing_source(early[SELF])
    # source_inputs is the pure name contract, loaded only from its copied bytes.
    out.mkdir()
    _write(out / "inputs", early)
    names_module = load("D_p28_frozen_source_names", out / "inputs" / SOURCE_INPUTS)
    recipe = json.loads(early[RECIPE])
    producer_names = names_module.producer_names(recipe)
    require(len(producer_names) == len(set(producer_names)) and set(manifest.get("inputs", {})) == set(producer_names),
            "D P28 exact recipe-derived producer closure differs")
    support = literal(early[VERIFIER], "SUPPORT")
    require(isinstance(support, dict) and set(support) == {SCOPE, RUNTIME, ORACLE} and
            literal(early[VERIFIER], "INPUT_READER") == READER, "D P28 finite runtime support declaration differs")
    names = set(producer_names) | {SELF, SOURCE_INPUTS, STARTUP, VERIFIER, READER} | set(support)
    frozen = {name: normalized(ROOT / name) for name in sorted(names)}
    require(all(frozen[name] == data for name, data in early.items()), "D P28 source changed while snapshotting")
    for name in producer_names:
        require(pin(frozen[name]) == manifest["inputs"][name] and normalized(build / "inputs" / name) == frozen[name],
                "D P28 current/frozen producer differs: " + name)
    for name, digest in support.items():
        require(pin(frozen[name])["sha256"] == digest, "D P28 pinned runtime support differs: " + name)
    frozen["selection/build.json"] = manifest_raw
    for name in NATIVE:
        frozen["selection/generated-readable/" + name] = normalized(build / "generated-readable" / name)
    _write(out / "inputs", frozen)
    require(all(normalized(ROOT / name) == data for name, data in frozen.items() if not name.startswith("selection/")),
            "D P28 authority changed before frozen execution")
    return frozen


def run_bound(build, out):
    frozen = freeze_inputs(build, out)
    executing = load("D_p28_frozen_execution", out / "inputs" / SELF)
    executing.run_snapshot(build, out, frozen, ROOT)


def run_snapshot(build, out, frozen, working_root):
    executing_source(frozen[SELF])
    manifest = json.loads(frozen["selection/build.json"])
    geo = bound_selection(manifest)
    verifier = load("D_p28_frozen_admission", ROOT / VERIFIER)
    admitted = verifier.admit_d_build(manifest, build, "D-source-jit")
    require(admitted.family == "D" and admitted.profile_id == PROFILE and admitted.representation == "source-jit",
            "D P28 source-JIT admission differs")
    source = load("D_p28_frozen_source", HERE / "source.py")
    builder = load("D_p28_frozen_flags", HERE / "build.py")
    startup = load("D_p28_frozen_startup", ROOT / STARTUP)
    storage = load("D_p28_frozen_storage", HERE / "storage.py")
    profile = source.production().resource_profile(PROFILE)
    require(json_equal(profile.to_record(ENTRY), manifest["resource"]), "D P28 exact canonical resource differs")
    files, proof = startup.prepared(source, profile, True, storage, "prefix")
    selected = {name: frozen["selection/generated-readable/" + name] for name in NATIVE}
    source_pins = source_binding(files, proof, manifest, selected)
    flags = builder.native_flags(profile)
    require(flags == manifest["flags"] and flags.count("-DWORKERS=28") == flags.count("-DTT_BITS=25") == 1,
            "D P28 actual native resource/compiler flags differ")
    owner = load("D_p28_frozen_owner", ROOT / OWNER)
    runtime = load("D_p28_frozen_runtime", ROOT / RUNTIME)
    scope = load("D_p28_frozen_scope", ROOT / SCOPE)
    require(not runtime.OWNED, "D P28 runtime owner namespace is not empty")
    limits = verifier.execution_limits(admitted, verifier.effective_available_bytes(), wall_seconds=60)
    require(limits["address_space_bytes"] == 2 << 30, "D P28 requires exactly2GiB inherited AS")
    report = dict(format=1, **{"class": SCHEMA}, complete=False, source_bound=False,
        profile=PROFILE, family="D", build=dict(path=str(build), **pin(frozen["selection/build.json"])),
        inputs={n: pin(d) for n, d in frozen.items()}, geometry=geo, flags=flags,
        selected_source=source_pins, production_proof=proof, commands=[], mechanisms=[], startup_barriers=[],
        frozen_execution=True, real_target_allocation=False, actual_tt_bytes=TT_BYTES, actual_workers=WORKERS,
        shipping_binary_executed=False, runtime_qualified=False, rules_qualified=False,
        physical_placement_qualified=False, NUMA_qualified=False, locality_proof=False,
        production_startup_timing_claimed=False, strength_claimed=False, event_target_confirmed=False)

    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    import resource
    inherited_cpu = resource.getrlimit(resource.RLIMIT_CPU)
    applied = mechanism_limits(inherited_cpu)
    report.update(inherited_CPU_limits=list(inherited_cpu), applied_Host_limits=applied,
                  startup_inherits_parent_CPU_limits=[applied["parent_CPU"], applied["parent_CPU_hard"]])
    owner.LIMITS.update(applied)
    previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    host, closed = None, False
    try:
        host = owner.Host(out, report, save)
        for name, expected in CASES:
            negative = None if expected == 0 else "omit-clear" if expected == 7 else "omit-page-owner"
            fixture, trace = poison_fixture(files, source, negative=negative)
            directory = out / name
            directory.mkdir()
            _write(directory, fixture)
            binary = directory / "x"
            host.run(["cc", *flags, *[str(directory / n) for n in source.UNITS],
                      "-Wl,-T," + str(directory / "image.ld"), "-o", str(binary)], cwd=directory, kind="compile-" + name)
            capacity = launch_capacity(verifier, admitted)
            try:
                output = host.run([str(binary)], cwd=directory, kind="execute-" + name,
                                  data=b"uci\nisready\nquit\n")
            except ValueError:
                require(expected in (7, 8), "positive D P28 diagnostic failed")
                require_execution(report["commands"][-1], expected)
                output = Path(report["commands"][-1]["stdout"]["path"]).read_bytes()
            require_execution(report["commands"][-1], expected)
            wanted = b"TEST_INITIALIZED\nuciok\nreadyok\n" if expected == 0 else (
                b"TEST_POISON_REMAINS\n" if expected == 7 else b"TEST_OWNER_DIFFERS\n")
            require(output == wanted, "D P28 diagnostic output/fault boundary differs")
            report["real_target_allocation"] = True
            report["mechanisms"].append(dict(name=name, expected_returncode=expected, output=pin(output),
                native=pin(binary.read_bytes()), host_admission=capacity["admission"],
                launch_headroom=capacity["launch_headroom"], instrumentation=trace,
                complete_entry_fields_checked=expected != 7, complete_page_owners_checked=expected == 0,
                poisoning_changes_first_touch=True, shipping_identity_claimed=False))
            save()
        directory = out / "selected-W28-last-initializer"
        directory.mkdir()
        _write(directory, files)
        paths = {name: directory / name for name in ("arrived", "release", "joined", "exit_release")}
        extra = startup_wrapper(paths)
        (directory / "fixture.c").write_bytes(extra)
        binary = directory / "x"
        host.run(["cc", *flags, *[str(directory / n) for n in source.UNITS], str(directory / "fixture.c"),
                  "-Wl,--wrap=spawn,--wrap=main", "-Wl,-T," + str(directory / "image.ld"), "-o", str(binary)],
                 cwd=directory, kind="compile-unpoisoned-startup")
        require(all(normalized(directory / n) == files[n] for n in NATIVE), "D P28 startup changed readable production units")
        barrier = startup_runtime(binary, directory / "runtime", paths, admitted=admitted, verifier=verifier,
                                  runtime=runtime, scope=scope, host=host, report=report)
        shipping_source = verifier.checked_artifact(build, "shipping-inputs/main.c", manifest["shipping_inputs"]["main.c"])
        barrier.update(extra_TU=pin(extra), fixture_source=pin(extra), shipping_source=pin(shipping_source),
                       production_units=source_pins, production_proof=proof, production_units_changed=False,
                       linker_wrappers=["spawn", "main"])
        report["startup_barriers"].append(barrier)
        require(verifier.admit_d_build(manifest, build, "D-source-jit") == admitted, "D P28 selected admission changed")
        require(normalized(build / "build.json") == frozen["selection/build.json"], "D P28 selected manifest changed")
        for name in NATIVE:
            require(normalized(build / "generated-readable" / name) == selected[name], "D P28 selected readable changed")
        for name, data in frozen.items():
            if not name.startswith("selection/"):
                require(normalized(working_root / name) == data and normalized(ROOT / name) == data,
                        "D P28 current/frozen source changed: " + name)
        command_contract(report["commands"])
        drain_owned(runtime, host, report)
        host.close()
        closed = True
        require(report["host_cleanup"] == dict(unsettled_commands=0, errors=[]), "D P28 Host cleanup differs")
        report.update(complete=True, source_bound=True)
    except BaseException as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if host is not None:
            inherited = signal.pthread_sigmask(signal.SIG_BLOCK, set(host.handled))
            try:
                try:
                    drain_owned(runtime, host, report)
                finally:
                    if not closed:
                        host.close()
            except BaseException as error:
                report["complete"] = False
                report["cleanup_failure"] = dict(type=type(error).__name__, message=str(error))
                raise
            finally:
                signal.signal(signal.SIGCHLD, previous)
                signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
                save()
        else:
            signal.signal(signal.SIGCHLD, previous)
            save()
    print(json.dumps(dict(complete=True, source_bound=True, actual_tt_bytes=TT_BYTES,
                         workers=WORKERS, runtime_qualified=False, physical_placement_qualified=False)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux x86-64 mechanism host required")
    require(args.build.is_absolute() and args.build.is_dir() and args.out.is_absolute() and not args.out.exists() and
            not any((p / ".git").exists() for p in (args.out, *args.out.parents)), "existing absolute build/new external output required")
    run_bound(args.build.resolve(), args.out.resolve())


if __name__ == "__main__":
    main()
