#!/usr/bin/env python3
"""Actual W28/TT24 initialization and main-barrier evidence for selected C engines.

No resource constant is reduced. The poisoned callback process checks complete
key/data/flag initialization and actual page-unit owners, not entry padding or
NUMA. A separate process executes the unmodified shipping main with a test-only
last-initializer wrapper, a single 60-second startup deadline and two GO joins.
Existing phase/compound P4 diagnostic helpers remain unchanged.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NEXT = "engines/experiments/tcec-next/"
SELF = NEXT + "check_profile_p28.py"
SCHEMA = "rove4k-bound-p28-mechanism-v1"
VERIFIER = NEXT + "profile_verify.py"
LIFECYCLE = NEXT + "check_profile_compound.py"
LIFECYCLE_PIN = dict(bytes=20823, sha256="1f3b9fc6ccd3796a8bbffd8c9ebd81db1a9fb5f38eb9752ec23f40d432b68168")
OWNER = "engines/experiments/tcec-scope/build.py"
OWNER_SHA = "5fa10c6f8f032be374bf3a86bbe6ca558076630a2cc3170b41890f691688f563"
RUNTIME = "engines/compact/tiny-entry-d/verify.py"
COMPOUND = dict(path=NEXT + "spelling_compound.py", selection="compound", variant="clock-atomic-launcher")
F_COMPOUND_DECLARATION = dict(path=NEXT + "spelling_compound.py", selection="compound-v2", variant="clock-atomic-launcher-parentheses")
BEST_B = dict(path=NEXT + "profile_spelling.py", selection="best", variant="atomic-assignment")
DEPENDENCIES = dict(path=NEXT + "profile_dependencies.py", variant="unused-includes")
PROFILE = "test-p28"
WORKERS, BITS, ENTRY, UNIT = 28, 24, 24, 512
ENTRIES = 1 << BITS
TT_BYTES = ENTRIES * ENTRY
STARTUP_SECONDS = 60
DIAGNOSTIC_PREAMBLE = b"#define main rv28_unused_shipping_main\nstatic _Atomic unsigned rv28_owner[32768];\n"
LINK_FLAGS = ("-Wl,--wrap=pthread_create", "-Wl,--wrap=pthread_join", "-Wl,--wrap=aligned_alloc")
# This is appended diagnostic code. The shipping prefix, successful output,
# allocation/thread results and errno are unchanged. Reads are fixed, bounded
# kernel counters only; unavailable counters are explicitly marked.
FAILURE_DIAGNOSTICS = r'''
#include<errno.h>
#include<fcntl.h>
#include<sys/resource.h>
#include<unistd.h>
static void rv28_write(const char*text,size_t size){
 while(size){ssize_t n=write(2,text,size);if(n<0&&errno==EINTR)continue;if(n<=0)break;text+=n;size-=n;}
}
static void rv28_counter(const char*path){
 char message[512],buffer[2048];int fd=open(path,O_RDONLY),error=errno;
 int n=snprintf(message,sizeof message,"RV28_FILE path=%s available=%d errno=%d\n",path,fd>=0,fd>=0?0:error);
 if(n>0)rv28_write(message,(size_t)n<sizeof message?(size_t)n:sizeof message-1);
 if(fd<0)return;
 size_t total=0;ssize_t got=0;
 while(total<8192){size_t count=8192-total;if(count>sizeof buffer)count=sizeof buffer;
  got=read(fd,buffer,count);if(got<0&&errno==EINTR)continue;
  if(got<0){n=snprintf(message,sizeof message,"\nRV28_READ_ERROR errno=%d\n",errno);if(n>0)rv28_write(message,(size_t)n);break;}
  if(!got)break;rv28_write(buffer,(size_t)got);total+=(size_t)got;
 }
 if(total==8192)rv28_write("\nRV28_FILE limit_reached=8192\n",sizeof "\nRV28_FILE limit_reached=8192\n"-1);
 close(fd);rv28_write("\nRV28_FILE_END\n",sizeof "\nRV28_FILE_END\n"-1);
}
static void rv28_limit(const char*name,int which){
 struct rlimit limit;char message[256];int ok=getrlimit(which,&limit)==0,error=errno;
 int n=ok?snprintf(message,sizeof message,"RV28_LIMIT name=%s available=1 soft=%llu hard=%llu\n",name,
  (unsigned long long)limit.rlim_cur,(unsigned long long)limit.rlim_max):
  snprintf(message,sizeof message,"RV28_LIMIT name=%s available=0 errno=%d\n",name,error);
 if(n>0)rv28_write(message,(size_t)n<sizeof message?(size_t)n:sizeof message-1);
}
static void rv28_failure(const char*stage,int result,int observed_errno,unsigned long long detail0,unsigned long long detail1){
 int saved_errno=errno;char message[512];
 int n=snprintf(message,sizeof message,"RV28_FAILURE stage=%s rc=%d errno=%d detail0=%llu detail1=%llu pid=%ld\n",
  stage,result,observed_errno,detail0,detail1,(long)getpid());
 if(n>0)rv28_write(message,(size_t)n<sizeof message?(size_t)n:sizeof message-1);
 rv28_limit("AS",RLIMIT_AS);rv28_limit("STACK",RLIMIT_STACK);rv28_limit("CPU",RLIMIT_CPU);
#ifdef RLIMIT_NPROC
 rv28_limit("NPROC",RLIMIT_NPROC);
#else
 rv28_write("RV28_LIMIT name=NPROC available=0 unsupported=1\n",sizeof "RV28_LIMIT name=NPROC available=0 unsupported=1\n"-1);
#endif
 rv28_counter("/proc/self/status");rv28_counter("/proc/self/limits");rv28_counter("/proc/self/cgroup");
 rv28_counter("/sys/fs/cgroup/pids.current");rv28_counter("/sys/fs/cgroup/pids.max");
 errno=saved_errno;
}
extern void*__real_aligned_alloc(size_t,size_t);
void*__wrap_aligned_alloc(size_t alignment,size_t size){
 void*result=__real_aligned_alloc(alignment,size);int error=errno;
 if(!result||!alignment||((uintptr_t)result)%alignment)
  rv28_failure("aligned_alloc",!result?0:1,error,(unsigned long long)alignment,(unsigned long long)size);
 errno=error;return result;
}
extern int __real_pthread_join(pthread_t,void**);
int __wrap_pthread_join(pthread_t thread,void**result){
 int code=__real_pthread_join(thread,result),error=errno;
 if(code)rv28_failure("pthread_join",code,error,0,0);
 errno=error;return code;
}
'''.encode()
CONTEXT = {
    "A": dict(count="RVN", width="RVW", unit="RVU", table="N", key="aT", data="U", lock="zN",
              worker_type="M", workers="K", ident="id", depth="C", worker="A", launcher="rv", join="j", joined="qk", pending="I"),
    "C": dict(count="RVN", width="RVW", unit="RVU", table="qq", key="aT", data="U", lock="zN",
              worker_type="ai", workers="qr", ident="id", depth="C", worker="A", launcher="rv", join="j", joined="qk", pending="qj"),
    "E": dict(count="RVN", width="RVW", unit="RVU", table="qq", key="aT", data="U", lock="zN",
              worker_type="ai", workers="qr", ident="id", depth="C", worker="A", launcher="rv", join="j", joined="qk", pending="qj"),
    "F": dict(count="RVN", width="RVW", unit="RVU", table="B", key="a", data="b", lock="zN",
              worker_type="X", workers="U", ident="a", depth="b", worker="qq", launcher="J", join="k", joined="C", pending="A"),
    "B": dict(count="qN", width="qW", unit="qU", table="qq", key="h", data="v", lock="a",
              worker_type="zd", workers="qr", ident="i", depth="d", worker="s", launcher="V", join="U", joined="qk", pending="qj"),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def normalized(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named P28 support input")
    return data


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def geometry(resources):
    expected = dict(id=PROFILE, workers=WORKERS, tt_bits=BITS, tt_entries=ENTRIES,
        tt_bytes=TT_BYTES, tt_entry_bytes=ENTRY, tt_mask=ENTRIES - 1)
    require(all(resources.get(k) == v for k, v in expected.items()), "actual W28/TT24/24-byte resource record required")
    ranges = [(ENTRIES // UNIT * n // WORKERS * UNIT,
               ENTRIES // UNIT * (n + 1) // WORKERS * UNIT) for n in range(WORKERS)]
    require(ranges[0][0] == 0 and ranges[-1][1] == ENTRIES and
        all(ranges[n][1] == ranges[n + 1][0] for n in range(WORKERS - 1)) and
        all(a * ENTRY % 4096 == b * ENTRY % 4096 == 0 for a, b in ranges), "P28 floor partition is not exact/page-aligned")
    return dict(workers=WORKERS, tt_bits=BITS, tt_entries=ENTRIES, tt_entry_bytes=ENTRY,
        tt_bytes=TT_BYTES, page_unit_entries=UNIT, page_unit_bytes=UNIT * ENTRY,
        page_units=ENTRIES // UNIT, ranges=[dict(worker=n, begin=a, end=b) for n, (a, b) in enumerate(ranges)],
        range_entry_counts={str(size): sum(b - a == size for a, b in ranges) for size in sorted({b - a for a, b in ranges})})


def bound_selection(manifest):
    family = manifest.get("family")
    require(manifest.get("class") == "rove4k-production-profile-v1" and family in CONTEXT and
        manifest.get("entry") == family and
        (manifest.get("post_spelling") == (BEST_B if family == "B" else COMPOUND) or
         family == "F" and manifest.get("post_spelling") == F_COMPOUND_DECLARATION) and
        manifest.get("post_profile") == dict(path=NEXT + ("profile_b.py" if family == "B" else "profile_phase.py"),
                                              variant="tcec-final-lf" if family == "B" else "phase-init") and
        manifest.get("source_dependencies") == DEPENDENCIES and
        manifest.get("plan", {}).get("representation") == "source-jit" and
        manifest.get("plan", {}).get("entry_cleanup") == "private-path",
        "P28 mechanism accepts only selected ACEF compound or B final-lf/effective-best source-JIT")
    return geometry(manifest.get("resources", {}))


def init_marker(family):
    c = CONTEXT[family]
    N, W, U = c["count"], c["width"], c["unit"]
    begin = f"size_t n=(({c['worker_type']}*)p)->{c['ident']},i={N}/{U}*n/{W}*{U}"
    tail = (f";X(;i<{N}/{U}*(n+1)/{W}*{U};i++){{" if family == "B" else
            f",e={N}/{U}*(n+1)/{W}*{U};for(;i<e;i++){{")
    return (begin + tail).encode()


def trace_initialization(source, family):
    """One named diagnostic insertion; original bounds/stores remain untouched."""
    require(type(source) is bytes and family in CONTEXT and b"rv28_" not in source, "exact family diagnostic namespace required")
    c = CONTEXT[family]
    for key, value in (("width", "28"), ("count", "((size_t)1<<24)"), ("unit", "512")):
        require(source.count(f"#define {c[key]} {value}\n".encode()) == 1, "actual P28 resource constant differs")
    marker = init_marker(family)
    require(source.count(marker) == 1, "one exact selected page-floor initialization loop required")
    at = source.index(marker) + len(marker)
    inserted = (f"if(i%{c['unit']}==0){{if(i>={c['count']}||"
        f"atomic_exchange_explicit(rv28_owner+i/{c['unit']},(unsigned)n+1,memory_order_relaxed))exit(23);}} ").encode()
    result = source[:at] + inserted + source[at:]
    proof = dict(schema="rove4k.p28-initialization-trace.v1", family=family, profile=PROFILE,
        input=pin(source), output=pin(result), offset=at, inserted=inserted.decode(),
        protected_prefix=pin(source[:at]), protected_suffix=pin(source[at:]),
        bounds_and_stores_changed=False, resource_constants_changed=False, full_inverse=True)
    return result, proof


def restore_trace(result, proof):
    require(pin(result) == proof.get("output") and proof.get("schema") == "rove4k.p28-initialization-trace.v1",
            "exact diagnostic trace output required")
    at, inserted = proof["offset"], proof["inserted"].encode()
    require(result[at:at + len(inserted)] == inserted, "diagnostic trace span differs")
    source = result[:at] + result[at + len(inserted):]
    require(pin(source) == proof["input"] and trace_initialization(source, proof["family"]) == (result, proof),
            "diagnostic inverse or protected gaps differ")
    return source


def callback_launcher(family):
    """One-shot fixture slots stay immutable through joins; no child heap work.

    A failed real create has no child and releases its claim for a retry.
    Successful slots remain claimed until this callback-only process exits.
    This same diagnostic wrapper supplies the focused C fault cases.
    """
    c = CONTEXT[family]
    W = c["width"]
    return f"""
extern int __real_pthread_create(pthread_t*,const pthread_attr_t*,void*(*)(void*),void*);
static atomic_int rv28_seen[{W}];
typedef struct{{void*(*fn)(void*);void*arg;size_t id;}}rv28_launch;
static rv28_launch rv28_slots[{W}];
static atomic_int rv28_claimed[{W}];
static void*rv28_observe(void*p){{rv28_launch v=*(rv28_launch*)p;
 if(qh||atomic_fetch_add(&rv28_seen[v.id],1))exit(20);return v.fn(v.arg);}}
int __wrap_pthread_create(pthread_t*t,const pthread_attr_t*a,void*(*fn)(void*),void*p){{
 size_t n=(({c['worker_type']}*)p)->{c['ident']};
 if(qh||fn!={c['worker']}||n>={W}){{rv28_failure("create-precondition",21,errno,n,{W});return 21;}}
 if(atomic_exchange_explicit(rv28_claimed+n,1,memory_order_acq_rel)){{rv28_failure("create-slot",22,errno,n,{W});return 22;}}
 rv28_launch*v=rv28_slots+n;v->fn=fn;v->arg=p;v->id=n;
 int error=__real_pthread_create(t,a,rv28_observe,v),observed_errno=errno;
 if(error){{atomic_store_explicit(rv28_claimed+n,0,memory_order_release);rv28_failure("pthread_create",error,observed_errno,n,{W});}}errno=observed_errno;return error;
}}
""".encode()


def full_callback_fixture(source, family, resource_proof):
    geo = geometry(resource_proof["resources"])
    c = CONTEXT[family]
    traced, proof = trace_initialization(source, family)
    require(restore_trace(traced, proof) == source, "complete initialization trace inverse differs")
    N, W, U, T, S = (c[k] for k in ("count", "width", "unit", "table", "workers"))
    observation = dict(actual_workers=WORKERS, actual_tt_entries=ENTRIES, actual_tt_bytes=TT_BYTES,
        tt_entry_bytes=ENTRY, all_callbacks_entered_once=True, all_keys_data_flags_initialized=True,
        exact_page_unit_owners=True, worker_storage_unchanged_except_id_depth=True,
        pending_zero=True, join_count_zero=True, startup_history_zero=True)
    output = json.dumps(json.dumps(observation, separators=(",", ":")) + "\n")
    harness = f"""
#undef main
int main(void){{
 _Static_assert({W}==28&&{N}==((size_t)1<<24)&&{U}==512,"actual P28 constants");
 _Static_assert(sizeof*{T}==24,"actual P28 entry width");
 {T}=aligned_alloc(4096,{N}*sizeof*{T});if(!{T}||((uintptr_t){T})%4096)return 2;
 unsigned char*rv28_saved=malloc(sizeof {S});if(!rv28_saved)return 3;
 memset({S},0x5a,sizeof {S});
 for(size_t n=0;n<{W};n++){{{S}[n].{c['ident']}=n;{S}[n].{c['depth']}=0;}}
 memcpy(rv28_saved,{S},sizeof {S});
 for(size_t n=0;n<{N};n++){{{T}[n].{c['key']}={T}[n].{c['data']}=UINT64_MAX;
 atomic_flag_clear_explicit(&{T}[n].{c['lock']},memory_order_relaxed);
 atomic_flag_test_and_set_explicit(&{T}[n].{c['lock']},memory_order_relaxed);}}
 if(qh||{c['joined']}||atomic_load(&{c['pending']}))return 4;
 {c['joined']}={W};{c['launcher']}();{c['join']}();
 if(qh||{c['joined']}||atomic_load(&{c['pending']})||memcmp(rv28_saved,{S},sizeof {S}))return 5;
 for(size_t n=0;n<{W};n++)if(atomic_load(&rv28_seen[n])!=1)return 6;
 for(size_t n=0;n<{N};n++){{if({T}[n].{c['key']}||{T}[n].{c['data']}||
 atomic_flag_test_and_set_explicit(&{T}[n].{c['lock']},memory_order_relaxed))return 7;
 atomic_flag_clear_explicit(&{T}[n].{c['lock']},memory_order_relaxed);}}
 for(size_t n=0;n<{N}/{U};n++)if(atomic_load(&rv28_owner[n])!=((n+1)*{W}-1)/({N}/{U})+1)return 8;
 printf({output});free(rv28_saved);free({T});return 0;
}}
"""
    assertions = ("\n".join(resource_proof["target_type_assertions"]) + "\n").encode()
    fixture = (DIAGNOSTIC_PREAMBLE + traced + b"\n" + assertions + FAILURE_DIAGNOSTICS
               + callback_launcher(family) + harness.encode())
    return fixture, observation, proof, geo


def blocked_main(source, family, gate, arrived):
    """Own one held startup descriptor through the initializer's join."""
    c = CONTEXT[family]
    return source + b"\n" + FAILURE_DIAGNOSTICS + f"""
#include<unistd.h>
extern int __real_pthread_create(pthread_t*,const pthread_attr_t*,void*(*)(void*),void*);
typedef struct{{void*(*fn)(void*);void*arg;}}rv28_block;
static rv28_block rv28_held_slot;
static atomic_int rv28_held_claimed;
static void*rv28_wait(void*p){{rv28_block v=*(rv28_block*)p;
 FILE*f=fopen({json.dumps(str(arrived))},"w");if(!f)exit(24);fclose(f);
 while(access({json.dumps(str(gate))},F_OK)){{struct timespec t={{0,1000000}};nanosleep(&t,0);}}
 return v.fn(v.arg);
}}
int __wrap_pthread_create(pthread_t*t,const pthread_attr_t*a,void*(*fn)(void*),void*p){{
 if(!qh&&fn=={c['worker']}&&(({c['worker_type']}*)p)->{c['ident']}=={c['width']}-1){{
 if(atomic_exchange_explicit(&rv28_held_claimed,1,memory_order_acq_rel)){{rv28_failure("held-slot",25,errno,{c['width']}-1,{c['width']});return 25;}}
 rv28_held_slot.fn=fn;rv28_held_slot.arg=p;
 int error=__real_pthread_create(t,a,rv28_wait,&rv28_held_slot),observed_errno=errno;
 if(error){{atomic_store_explicit(&rv28_held_claimed,0,memory_order_release);rv28_failure("pthread_create",error,observed_errno,{c['width']}-1,{c['width']});}}errno=observed_errno;return error;}}
 int error=__real_pthread_create(t,a,fn,p),observed_errno=errno;
 if(error)rv28_failure("pthread_create",error,observed_errno,0,{c['width']});errno=observed_errno;return error;
}}
""".encode()


def wait_startup_line(runtime, line, deadline):
    remaining = deadline - time.monotonic()
    require(remaining > 0, "P28 single 60-second startup deadline expired")
    runtime.stdout.until(lambda data: data.splitlines().count(line) >= 1, runtime.budget, seconds=remaining)


def actual_barrier(host, runtime_module, lifecycle, directory, source, family, compiler, report):
    directory.mkdir()
    gate, arrived = directory / "release", directory / "last-initializer-arrived"
    fixture = blocked_main(source, family, gate, arrived)
    require(fixture.startswith(source) and b"#define rv_spawn" not in fixture and b"#define RVW qW" not in fixture,
            "P28 actual main must be alias-free and unchanged")
    (directory / "fixture.c").write_bytes(fixture)
    host.run([*compiler, *LINK_FLAGS], cwd=directory, kind="selected-W28-last-initializer-compile", data=fixture)
    disposable = directory / "disposable-native"
    shutil.copyfile(directory / "x", disposable)
    disposable.chmod(0o700)
    runtime = None
    try:
        budget = runtime_module.Budget(100)
        started = time.monotonic()
        deadline = started + STARTUP_SECONDS
        runtime = lifecycle.construct_owned(runtime_module, disposable, directory / "runtime", budget, host.handled)
        runtime.send(b"uci\nisready\n")
        while disposable.exists() or not arrived.exists():
            require(time.monotonic() < deadline and not runtime.exited(), "P28 last initializer did not reach its gate")
            time.sleep(.005)
        time.sleep(.1)
        require(time.monotonic() < deadline and not runtime.exited() and runtime.stdout.bytes() == b"", "P28 UCI escaped the held initializer")
        gate.write_bytes(b"release\n")
        wait_startup_line(runtime, b"uciok", deadline)
        wait_startup_line(runtime, b"readyok", deadline)
        startup_ms = (time.monotonic() - started) * 1000
        require(startup_ms <= 60000, "P28 instrumented native startup exceeded 60 seconds")
        legal = {f"{f}2{f}{r}".encode() for f in "abcdefgh" for r in "34"} | {b"b1a3", b"b1c3", b"g1f3", b"g1h3"}
        for count in (1, 2):
            runtime.send(b"position startpos\ngo wtime 30 btime 30 winc 0 binc 0\n")
            runtime.wait_best(count)
            runtime.send(b"isready\n")
            runtime.wait_line(b"readyok", count + 1)
            moves = [r[9:] for r in runtime.stdout.bytes().splitlines() if r.startswith(b"bestmove ")]
            require(len(moves) == count and all(move in legal for move in moves), "P28 GO emitted duplicate/illegal results")
        runtime.send(b"position startpos\nisready\n")
        runtime.wait_line(b"readyok", 4)
        runtime.send(b"quit\n")
        physical = runtime.finish()
        cleanup = runtime.cleanup()
        output = runtime.stdout.bytes()
        require(not cleanup["forced_cleanup"] and not cleanup["errors"] and output.count(b"bestmove ") == 2,
                "P28 actual main did not settle normally")
        (directory / "runtime.stdout").write_bytes(output)
        return dict(fixture_source=pin(fixture), native=pin((directory / "x").read_bytes()),
            shipping_source=pin(source), actual_resource_profile=PROFILE, actual_workers=WORKERS,
            actual_tt_entries=ENTRIES, actual_tt_bytes=TT_BYTES, tt_entry_bytes=ENTRY,
            last_initializer_delayed=True, gate_arrival_observed=True, no_uci_before_release=True,
            uci_ready_after_release=True, startup_deadline_ms=60000, instrumented_native_startup_ms=startup_ms,
            startup_includes_intentional_hold=True, private_copy_removed=not disposable.exists(),
            legal_search_relaunches=2, post_GO2_join_observed=True, output=pin(output),
            physical=physical, cleanup=cleanup, shipping_identity_claimed=False,
            diagnostic_alias_applied=False, resource_constants_changed=False, all_workers_positive_CPU_claimed=False)
    finally:
        if runtime is not None:
            row = dict(directory=str(runtime.directory), pid=runtime.process.pid)
            try:
                row["cleanup"] = runtime.cleanup()
            except BaseException as error:
                row.update(cleanup=runtime.cleaned, error=dict(type=type(error).__name__, message=str(error)))
                raise
            finally:
                report.setdefault("barrier_runtime_cleanup", []).append(row)


def run_bound(build, out):
    names = (SELF, VERIFIER, LIFECYCLE, OWNER, RUNTIME)
    observed = {name: normalized(ROOT / name) for name in names}
    require(pin(observed[LIFECYCLE]) == LIFECYCLE_PIN and pin(observed[OWNER])["sha256"] == OWNER_SHA,
            "reviewed lifecycle or bounded owner differs")
    verifier = load("p28_current_admission", ROOT / VERIFIER)
    manifest_raw = verifier.artifact_file(build, "build.json").read_bytes()
    manifest = json.loads(manifest_raw)
    geo = bound_selection(manifest)
    admitted = verifier.admit_c_build(manifest, build)
    require(admitted.family == manifest["family"] and admitted.profile_id == PROFILE and admitted.full and
        admitted.representation == "source-jit" and manifest["compile_executor"] == manifest["compiler"],
        "actual full P28 source-JIT admission/compiler required")
    proof_raw = verifier.artifact_file(build, "source-proof.json").read_bytes()
    require(json.loads(proof_raw) == manifest["source_proofs"], "P28 raw source proof differs from the admitted manifest")
    shipping = {role: verifier.checked_artifact(build, path,
        {key: admitted.expected[role + "_" + key] for key in ("bytes", "sha256")})
        for role, path in (("source", admitted.source), ("native", admitted.native), ("whole", admitted.program))}
    require(pin(observed[RUNTIME])["sha256"] == verifier.SUPPORT[RUNTIME], "reviewed process owner differs")
    limits = verifier.execution_limits(admitted, verifier.effective_available_bytes())
    for name, data in observed.items():
        require(normalized(ROOT / name) == data, "P28 support changed during admission: " + name)
    out.mkdir()
    for name, data in observed.items():
        target = out / "inputs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    owner = load("p28_frozen_host", out / "inputs" / OWNER)
    runtime_module = load("p28_frozen_runtime", out / "inputs" / RUNTIME)
    lifecycle = load("p28_frozen_lifecycle", out / "inputs" / LIFECYCLE)
    require(not runtime_module.OWNED, "new P28 runtime namespace is not empty")
    source = shipping["source"]
    fixture, expected, trace, oracle = full_callback_fixture(source, admitted.family, manifest["source_proofs"][0])
    require(oracle == geo, "full callback resource oracle differs")
    report = dict(format=1, **{"class": SCHEMA}, mode="source-bound", complete=False, source_bound=False,
        entry=admitted.family, profile=PROFILE, representation=admitted.representation,
        selected_post_profile=manifest["post_profile"], selected_post_spelling=manifest["post_spelling"],
        source_dependencies=manifest["source_dependencies"], build=dict(path=str(build), **pin(manifest_raw)),
        actual={role: dict(path=path, **pin(shipping[role])) for role, path in
            (("source", admitted.source), ("native", admitted.native), ("whole", admitted.program))},
        resources=admitted.resources, source_closure=manifest["source_closure"], source_contract=admitted.source_contract,
        admitted_input_pins=admitted.input_pins, source_proofs=pin(proof_raw),
        support_inputs={name: pin(data) for name, data in observed.items()}, host_admission=limits["admission"],
        observed_affinity=sorted(os.sched_getaffinity(0)), commands=[], mechanisms=[], startup_barriers=[],
        production_adopted=False, runtime_qualified=False, rules_eligibility="unproven", placement_qualified=False,
        timing_claimed=False, NUMA_qualified=False, shipping_binary_executed=False, W256_executed=False,
        scope="full actual W28/TT24 poisoned key/data/flag/page-unit callback coverage; separate unmodified main startup+GO. Poisoning is not NUMA or production startup timing.")

    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    cpu = limits["CPU_seconds"][0]
    owner.LIMITS.update(aggregate_wall=360, per_command_wall=120, parent_AS=limits["address_space_bytes"],
        child_AS=limits["address_space_bytes"], parent_CPU=cpu + 30, parent_CPU_hard=cpu + 60, child_CPU=cpu)
    previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    host = owner.Host(out, report, save)
    closed = False
    try:
        directory = out / "selected-W28-full-callback"
        directory.mkdir()
        (directory / "fixture.c").write_bytes(fixture)
        (directory / "trace-proof.json").write_text(json.dumps(trace, indent=2) + "\n")
        compiler = manifest["compiler"]
        host.run([*compiler, *LINK_FLAGS], cwd=directory,
                 kind="selected-W28-full-callback-compile", data=fixture)
        raw = host.run([directory / "x"], cwd=directory, kind="selected-W28-full-callback-execute")
        require(raw == (json.dumps(expected, separators=(",", ":")) + "\n").encode(), "full P28 key/data/flag/owner callback audit differs")
        report["mechanisms"].append(dict(name="full-W28-TT24-initialization", profile=PROFILE,
            shipping_source=pin(source), fixture_source=pin(fixture), native=pin((directory / "x").read_bytes()),
            output=pin(raw), observation=expected, trace_proof=trace, geometry=geo,
            diagnostic_preamble=dict(text=DIAGNOSTIC_PREAMBLE.decode(), **pin(DIAGNOSTIC_PREAMBLE)),
            resource_constants_changed=False, padding_checked=False, search_executed=False,
            poisoning_changes_first_touch=True, NUMA_claimed=False, production_startup_timing_claimed=False))
        save()
        barrier = actual_barrier(host, runtime_module, lifecycle, out / "selected-W28-last-initializer",
            source, admitted.family, compiler, report)
        report["startup_barriers"].append(barrier)
        require(verifier.artifact_file(build, "build.json").read_bytes() == manifest_raw and
            verifier.admit_c_build(manifest, build) == admitted, "actual P28 source admission changed")
        require(verifier.artifact_file(build, "source-proof.json").read_bytes() == proof_raw,
                "P28 raw source proof changed during its mechanisms")
        for name, data in observed.items():
            require(normalized(ROOT / name) == data, "P28 support changed during execution: " + name)
        lifecycle.drain_owned(runtime_module, host, report)
        host.close()
        closed = True
        require(report["host_cleanup"] == dict(unsettled_commands=0, errors=[]), "P28 owned commands are unsettled")
        report.update(complete=True, source_bound=True)
        save()
    except BaseException as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        save()
        raise
    finally:
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, set(host.handled))
        try:
            try:
                lifecycle.drain_owned(runtime_module, host, report)
            finally:
                if not closed:
                    host.close()
                save()
        finally:
            signal.signal(signal.SIGCHLD, previous)
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
    print(json.dumps(dict(entry=admitted.family, profile=PROFILE, complete=True, source_bound=True,
        actual_workers=WORKERS, actual_tt_bytes=TT_BYTES, legal_GO_cycles=2, placement_qualified=False)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if (sys.platform != "linux" or platform.machine() != "x86_64" or not args.out.is_absolute() or out.exists() or
        ROOT in (out, *out.parents) or any((p / ".git").exists() for p in (out, *out.parents))):
        parser.error("Linux x86-64 and a new absolute external output required")
    if not args.build.is_absolute() or not args.build.is_dir():
        parser.error("existing absolute selected P28 build required")
    run_bound(args.build.resolve(), out)


if __name__ == "__main__":
    main()
