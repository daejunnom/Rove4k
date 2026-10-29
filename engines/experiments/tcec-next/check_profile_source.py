#!/usr/bin/env python3
"""Execute actual rendered C initialization/selection in bounded fixtures.

The fixture changes only resource constants and its entry, and reports that
fact separately from real shipping runtime qualification. It never allocates
the submitted 192GiB TT. A separate linker interposition holds the last actual
initializer to check that production main cannot answer UCI before its join.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import signal
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SELF = "engines/experiments/tcec-next/check_profile_source.py"
SOURCE = "engines/experiments/tcec-next/profile_source.py"
BEST = {"A": "H", "B": "m", "C": "H", "E": "H", "F": "d"}


def load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fixture_source(source, proof, context, workers):
    """Use the shipping callback/selector bodies, with an explicit tiny TT."""
    original_w = proof["resources"]["workers"]
    original_b = proof["resources"]["tt_bits"]
    old_w = f"#define RVW {original_w}\n".encode()
    old_n = f"#define RVN ((size_t)1<<{original_b})\n".encode()
    if source.count(old_w) != 1 or source.count(old_n) != 1:
        raise ValueError("one resource definition required for mechanism fixture")
    actual = source.replace(old_w, f"#define RVW {workers}\n".encode(), 1)
    actual = actual.replace(old_n, b"#define RVN ((size_t)1<<12)\n", 1)
    c = context
    table, ws, handles = c["table"], c["workers"], c["handles"]
    kind, ident, depth, best = c["worker_type"], c["ident"], c["depth"], BEST[proof["family"]]
    appended = f"""
#undef main
int main(void){{
 {table}=aligned_alloc(4096,RVN*sizeof*{table});
 if(!{table}||((uintptr_t){table})%4096)return 2;
 unsigned char*rv_saved=malloc(sizeof {ws});if(!rv_saved)return 3;
 memset({ws},0x5a,sizeof {ws});
 for(size_t n=0;n<RVW;n++){ws}[n].{ident}=n;
 memcpy(rv_saved,{ws},sizeof {ws});
 for(size_t n=0;n<RVN;n++){{{table}[n].{c['key']}=UINT64_MAX;{table}[n].{c['data']}=UINT64_MAX;
 atomic_flag_clear_explicit(&{table}[n].{c['lock']},memory_order_relaxed);
 atomic_flag_test_and_set_explicit(&{table}[n].{c['lock']},memory_order_relaxed);}}
 for(size_t n=0;n<RVW;n++)if(pthread_create({handles}+n,0,{c['clear']},{ws}+n))return 4;
 for(size_t n=0;n<RVW;n++)if(pthread_join({handles}[n],0))return 5;
 if(memcmp(rv_saved,{ws},sizeof {ws})||{c['joined']}||atomic_load(&{c['pending']}))return 6;
 for(size_t n=0;n<RVN;n++)if({table}[n].{c['key']}||{table}[n].{c['data']}||
 atomic_flag_test_and_set_explicit(&{table}[n].{c['lock']},memory_order_relaxed))return 7;
 for(size_t n=0;n<RVW;n++){{{ws}[n].{depth}=1;{ws}[n].{best}=MOVE(1,34,0);}}
 {ws}[RVW-1].{depth}=9;{ws}[RVW-1].{best}=MOVE(6,37,0);{c['selector']}();
 {ws}[0].{depth}=9;{c['selector']}();
 printf("{{\\\"workers\\\":%d,\\\"entries\\\":%zu,\\\"all_entries_initialized\\\":true,\\\"worker_storage_unchanged\\\":true,\\\"join_count_zero\\\":true}}\\n",RVW,RVN);
 free(rv_saved);free({table});return 0;
}}
"""
    # Keep the C JSON string legible without making it depend on Python's
    # representation of backslashes. This is fixture-only output code.
    appended = appended.replace('\\\\"', '\\"').replace('}}\\n', '}}\\n')
    assertions = "\n".join(proof["target_type_assertions"])
    return b"#define main rv_mechanism_unused_engine_main\n" + actual + assertions.encode() + appended.encode()


def barrier_source(source, context, gate):
    """Linker-only test hook; the production main/initializer stay unchanged."""
    path = json.dumps(str(gate))
    return source + f"""
#include <unistd.h>
extern int __real_pthread_create(pthread_t*,const pthread_attr_t*,void*(*)(void*),void*);
typedef struct{{void*(*fn)(void*);void*arg;}}rv_fixture_launch;
static void*rv_fixture_wait(void*p){{rv_fixture_launch v=*(rv_fixture_launch*)p;free(p);
 while(access({path},F_OK)){{struct timespec t={{0,1000000}};nanosleep(&t,0);}}
 return v.fn(v.arg);}}
int __wrap_pthread_create(pthread_t*t,const pthread_attr_t*a,void*(*fn)(void*),void*p){{
 if(fn=={context['clear']}&&(({context['worker_type']}*)p)->{context['ident']}==RVW-1){{
 rv_fixture_launch*v=malloc(sizeof*v);if(!v)return 12;v->fn=fn;v->arg=p;
 return __real_pthread_create(t,a,rv_fixture_wait,v);}}
 return __real_pthread_create(t,a,fn,p);
}}
""".encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out, build = args.out.resolve(), args.build.resolve()
    if (sys.platform != "linux" or not args.out.is_absolute() or not args.build.is_absolute() or
            out.exists() or ROOT in (out, *out.parents) or any((p / ".git").exists() for p in (out, *out.parents))):
        parser.error("existing absolute build and new external Linux output required")
    owner = load("profile_mechanism_owner", ROOT / "engines/experiments/tcec-scope/build.py")
    projection = load("profile_mechanism_projection", ROOT / SOURCE)
    contracts = load("profile_mechanism_contracts", ROOT / "engines/scripts/production.py")
    manifest_raw = (build / "build.json").read_bytes()
    manifest = json.loads(manifest_raw)
    owner.require(manifest.get("class") == "rove4k-production-profile-v1" and
                  manifest["complete"] and manifest["reproducible"] and
                  manifest["plan"]["representation"] == "source-jit" and
                  manifest["plan"]["entry_cleanup"] == "private-path", "completed source-JIT profile build required")
    family = manifest["family"]
    profile = contracts.resource_profile(manifest["resources"]["id"])
    # The real barrier fixture is deliberately bounded to TEST-P4. W28/W256
    # mechanism tests below scale only constants and never claim target runtime.
    owner.require(profile.id == "test-p4", "startup barrier fixture requires the actual TEST-P4 profile")
    base = (build / "control/main.c").read_bytes()
    expected, proof = projection.transform_source(base, family=family, profile=profile)
    source = (build / "main.c").read_bytes()
    owner.require(source == expected and proof == manifest["source_proofs"][0],
                  "actual emitted source/profile proof replay differs")
    owner.require(owner.pin(source) == {"bytes": manifest["expected_contract"]["source_bytes"],
                                      "sha256": manifest["expected_contract"]["source_sha256"]},
                  "actual emitted source identity differs")
    out.mkdir()
    report = dict(format=1, **{"class": "rove4k-actual-profile-mechanism-v1"},
        complete=False, family=family, build=owner.pin(manifest_raw),
        shipping_source=owner.pin(source), commands=[], mechanisms=[],
        scope="actual C initializer/selector and instrumented startup; not full submitted runtime qualification")

    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")

    owner.LIMITS.update(aggregate_wall=300, per_command_wall=45, parent_CPU=120,
                       parent_CPU_hard=150, child_CPU=30, child_AS=2 << 30)
    host = owner.Host(out, report, save)
    runtime = None
    try:
        c = projection.CONTEXT[family]
        for workers in (4, 28, 256):
            directory = out / ("workers-" + str(workers))
            directory.mkdir()
            fixture = fixture_source(source, proof, c, workers)
            (directory / "fixture.c").write_bytes(fixture)
            host.run(manifest["compiler"], cwd=directory, kind=f"W{workers}-compile", data=fixture)
            # Shrinking the process's default pthread stack is explicit test
            # setup so W256 fits the 2GiB fixture limit; no search is run here.
            driver = ("import resource,os;resource.setrlimit(resource.RLIMIT_STACK,(262144,262144));"
                      "os.execv(" + repr(str(directory / "x")) + ",[" + repr(str(directory / "x")) + "])")
            raw = host.run([sys.executable, "-I", "-B", "-c", driver], cwd=directory, kind=f"W{workers}-execute")
            lines = raw.decode("ascii").splitlines()
            owner.require(lines[:2] == ["bestmove g1f3", "bestmove b1c3"],
                          "all-worker max-depth/lowest-id selector differs")
            values = json.loads(lines[2])
            owner.require(values == dict(workers=workers, entries=4096, all_entries_initialized=True,
                                         worker_storage_unchanged=True, join_count_zero=True),
                          "actual initialization fixture differs")
            report["mechanisms"].append(dict(workers=workers, fixture_tt_entries=4096,
                fixture_source=owner.pin(fixture), native=owner.pin((directory / "x").read_bytes()),
                observation=values, selector_results=lines[:2], actual_submission_tt_executed=False))
            save()
        directory = out / "startup-last-initializer"
        directory.mkdir()
        gate = directory / "release"
        fixture = barrier_source(source, c, gate)
        (directory / "fixture.c").write_bytes(fixture)
        compiler = list(manifest["compiler"]) + ["-Wl,--wrap=pthread_create"]
        host.run(compiler, cwd=directory, kind="startup-barrier-compile", data=fixture)
        driver = load("profile_barrier_owned", ROOT / "engines/compact/tiny-entry-d/verify.py")
        disposable = directory / "disposable-native"
        shutil.copyfile(directory / "x", disposable)
        disposable.chmod(0o700)
        budget = driver.Budget(20)
        runtime = driver.Owned(disposable, directory / "runtime", budget)
        runtime.send(b"uci\nisready\n")
        deadline = time.monotonic() + budget.left(3)
        while disposable.exists():
            owner.require(time.monotonic() < deadline and not runtime.exited(),
                          "fixture entry did not unlink its private copy")
            time.sleep(.005)
        time.sleep(.2)
        owner.require(not runtime.exited() and runtime.stdout.bytes() == b"", "UCI escaped before last initializer joined")
        gate.write_bytes(b"release\n")
        runtime.wait_line(b"uciok")
        runtime.wait_line(b"readyok")
        runtime.send(b"quit\n")
        physical = runtime.finish()
        cleanup = runtime.cleanup()
        owner.require(not cleanup["forced_cleanup"] and not cleanup["errors"], "barrier fixture cleanup differed")
        report["startup_barrier"] = dict(fixture_source=owner.pin(fixture),
            native=owner.pin((directory / "x").read_bytes()), last_initializer_delayed=True,
            no_uci_before_release=True, uci_ready_after_release=True, private_copy_removed=True,
            physical=physical, cleanup=cleanup,
            shipping_identity_claimed=False)
        report["complete"] = True
        save()
    except BaseException as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        save()
        raise
    finally:
        if runtime is not None:
            runtime.cleanup()
        host.close()
        save()
    print(json.dumps(dict(family=family, complete=True, mechanisms=3, startup_barrier=True)))


if __name__ == "__main__":
    main()
