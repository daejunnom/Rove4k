#!/usr/bin/env python3
"""Measure and exercise finite portable-phase experiments from a fresh control.

This command freshly regenerates one TEST-P4 control, derives each named
resource profile from that run's maintained source, then measures control,
phase and phase-init independently twice. Only bounded fixtures and actual W4
startup are executed. Large submitted TTs are never allocated. These results
are experiment evidence, not production adoption or tournament qualification.

The separate --build mode binds the same focused mechanisms to one admitted
actual TEST-P4 phase-init artifact. It never substitutes an experiment control
or derives another resource profile from that selected source.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import lzma
from pathlib import Path
import platform
import shutil
import signal
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SELF = "engines/experiments/tcec-next/check_profile_phase.py"
PHASE = "engines/experiments/tcec-next/profile_phase.py"
SOURCE = "engines/experiments/tcec-next/profile_source.py"
BUILDER = "engines/experiments/tcec-next/profile_build.py"
COMMON = "engines/scripts/production.py"
PACKAGE = "engines/scripts/source_package.py"
WRAPPER = "engines/experiments/tcec-next/wrapper.py"
UNLINK = "engines/experiments/tcec-next/self_unlink.py"
OWNER = "engines/experiments/tcec-scope/build.py"
RUNTIME = "engines/compact/tiny-entry-d/verify.py"
VERIFIER = "engines/experiments/tcec-next/profile_verify.py"
PROFILES = ("test-p4", "test-p28", "tcec-provisional")
VARIANTS = ("control", "phase", "phase-init")
FIXTURE_BITS = 18
BEST = {"A": "H", "C": "H", "E": "H", "F": "d"}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def normalized(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ValueError("lone CR in named source input: " + str(path))
    return data


def require(value, message):
    if not value:
        raise ValueError(message)


def scaled_fixture(source, resource_proof, context):
    """Preserve each profile's actual partition syntax, shrinking only RVN."""
    c = context
    workers = resource_proof["resources"]["workers"]
    bits = resource_proof["resources"]["tt_bits"]
    entries = 1 << FIXTURE_BITS
    require(entries // 512 >= workers and (workers == 28 or (entries // 512) % workers == 0),
            "scaled fixture must preserve whole-page partition admission")
    old = f"#define RVN ((size_t)1<<{bits})\n".encode()
    require(source.count(old) == 1 and source.count(f"#define RVW {workers}\n".encode()) == 1,
            "one unchanged named worker count and TT count required")
    actual = source.replace(old, f"#define RVN ((size_t)1<<{FIXTURE_BITS})\n".encode(), 1)
    tt, ws, ident, depth = (c[n] for n in ("table", "workers", "ident", "depth"))
    observation = dict(workers=workers, entries=entries, every_callback_entered=True,
        all_entries_initialized=True, worker_storage_unchanged_except_id_depth=True,
        pending_zero=True, join_count_zero=True, startup_history_zero=True)
    output = json.dumps(json.dumps(observation, separators=(",", ":")) + "\n")
    appended = f"""
extern int __real_pthread_create(pthread_t*,const pthread_attr_t*,void*(*)(void*),void*);
static atomic_int rv_seen[RVW];
typedef struct{{void*(*fn)(void*);void*arg;size_t id;}}rv_observed_launch;
static void*rv_observe(void*p){{rv_observed_launch v=*(rv_observed_launch*)p;free(p);
 if(qh||atomic_fetch_add(&rv_seen[v.id],1))exit(20);return v.fn(v.arg);}}
int __wrap_pthread_create(pthread_t*t,const pthread_attr_t*a,void*(*fn)(void*),void*p){{
 size_t n=(({c['worker_type']}*)p)->{ident};
 if(qh||fn!={c['worker']}||n>=RVW)return 21;
 rv_observed_launch*v=malloc(sizeof*v);if(!v)return 22;
 v->fn=fn;v->arg=p;v->id=n;
 int error=__real_pthread_create(t,a,rv_observe,v);if(error)free(v);return error;
}}
#undef main
int main(void){{
 {tt}=aligned_alloc(4096,RVN*sizeof*{tt});
 if(!{tt}||((uintptr_t){tt})%4096)return 2;
 unsigned char*rv_saved=malloc(sizeof {ws});if(!rv_saved)return 3;
 memset({ws},0x5a,sizeof {ws});
 for(size_t n=0;n<RVW;n++){{{ws}[n].{ident}=n;{ws}[n].{depth}=0;}}
 memcpy(rv_saved,{ws},sizeof {ws});
 for(size_t n=0;n<RVN;n++){{{tt}[n].{c['key']}=UINT64_MAX;{tt}[n].{c['data']}=UINT64_MAX;
 atomic_flag_clear_explicit(&{tt}[n].{c['lock']},memory_order_relaxed);
 atomic_flag_test_and_set_explicit(&{tt}[n].{c['lock']},memory_order_relaxed);}}
 if(qh||{c['joined']}||atomic_load(&{c['pending']}))return 4;
 {c['joined']}=RVW;rv_spawn();{c['join']}();
 if(qh||{c['joined']}||atomic_load(&{c['pending']})||
    memcmp(rv_saved,{ws},sizeof {ws}))return 5;
 for(size_t n=0;n<RVW;n++)if(atomic_load(&rv_seen[n])!=1)return 6;
 for(size_t n=0;n<RVN;n++)if({tt}[n].{c['key']}||{tt}[n].{c['data']}||
 atomic_flag_test_and_set_explicit(&{tt}[n].{c['lock']},memory_order_relaxed))return 7;
 for(size_t n=0;n<RVW;n++){{{ws}[n].{depth}=1;{ws}[n].{BEST[resource_proof['family']]}=MOVE(1,34,0);}}
 {ws}[RVW-1].{depth}=9;{ws}[RVW-1].{BEST[resource_proof['family']]}=MOVE(6,37,0);{c['selector']}();
 {ws}[0].{depth}=9;{c['selector']}();
 printf({output});free(rv_saved);free({tt});return 0;
}}
"""
    assertions = "\n".join(resource_proof["target_type_assertions"])
    rendered = (b"#define main rv_unused_shipping_main\n" + actual + b"\n" +
                assertions.encode() + appended.encode())
    return rendered, observation


def blocked_main(source, context, gate, arrived):
    """Wrap only the last startup callback; main/callback source stays intact."""
    c = context
    gate_text, arrived_text = json.dumps(str(gate)), json.dumps(str(arrived))
    return source + f"""
#include<unistd.h>
extern int __real_pthread_create(pthread_t*,const pthread_attr_t*,void*(*)(void*),void*);
typedef struct{{void*(*fn)(void*);void*arg;}}rv_blocked_launch;
static void*rv_wait_init(void*p){{rv_blocked_launch v=*(rv_blocked_launch*)p;free(p);
 FILE*f=fopen({arrived_text},"w");if(!f)exit(23);fclose(f);
 while(access({gate_text},F_OK)){{struct timespec t={{0,1000000}};nanosleep(&t,0);}}
 return v.fn(v.arg);
}}
int __wrap_pthread_create(pthread_t*t,const pthread_attr_t*a,void*(*fn)(void*),void*p){{
 if(!qh&&fn=={c['worker']}&&(({c['worker_type']}*)p)->{c['ident']}==RVW-1){{
 rv_blocked_launch*v=malloc(sizeof*v);if(!v)return 24;v->fn=fn;v->arg=p;
 int error=__real_pthread_create(t,a,rv_wait_init,v);if(error)free(v);return error;}}
 return __real_pthread_create(t,a,fn,p);
}}
""".encode()


def check_barrier(host, owner, runtime_module, directory, source, context, compiler):
    directory.mkdir()
    gate, arrived = directory / "release", directory / "last-initializer-arrived"
    fixture = blocked_main(source, context, gate, arrived)
    (directory / "fixture.c").write_bytes(fixture)
    host.run([*compiler, "-Wl,--wrap=pthread_create"], cwd=directory,
             kind=directory.name + "-compile", data=fixture)
    disposable = directory / "disposable-native"
    shutil.copyfile(directory / "x", disposable)
    disposable.chmod(0o700)
    runtime = None
    try:
        budget = runtime_module.Budget(25)
        runtime = runtime_module.Owned(disposable, directory / "runtime", budget)
        runtime.send(b"uci\nisready\n")
        deadline = time.monotonic() + budget.left(5)
        while disposable.exists() or not arrived.exists():
            require(time.monotonic() < deadline and not runtime.exited(),
                    "last startup callback did not reach its explicit gate")
            time.sleep(.005)
        time.sleep(.1)
        require(not runtime.exited() and runtime.stdout.bytes() == b"",
                "UCI escaped before the last startup initializer completed")
        gate.write_bytes(b"release\n")
        runtime.wait_line(b"uciok")
        runtime.wait_line(b"readyok")
        legal = {bytes((file,)) + b"2" + bytes((file,)) + rank
                 for file in range(ord("a"), ord("h") + 1) for rank in (b"3", b"4")}
        legal.update((b"b1a3", b"b1c3", b"g1f3", b"g1h3"))
        for count in (1, 2):
            runtime.send(b"position startpos\ngo wtime 30 btime 30 winc 0 binc 0\n")
            runtime.wait_best(count)
            runtime.send(b"isready\n")
            runtime.wait_line(b"readyok", count + 1)
            moves = [row[9:] for row in runtime.stdout.bytes().splitlines()
                     if row.startswith(b"bestmove ")]
            require(len(moves) == count and all(move in legal for move in moves),
                    "actual qh>=1 phase emitted duplicate or illegal start-position moves")
        # A bestmove can precede the last callback's return. Position reuses
        # board/history only after the real join; its following ready response
        # therefore establishes physical search completion before quit.
        runtime.send(b"position startpos\nisready\n")
        runtime.wait_line(b"readyok", 4)
        runtime.send(b"quit\n")
        physical = runtime.finish()
        cleanup = runtime.cleanup()
        require(not cleanup["forced_cleanup"] and not cleanup["errors"],
                "actual phase-main fixture needed forced cleanup")
        output = runtime.stdout.bytes()
        moves = [row[9:] for row in output.splitlines() if row.startswith(b"bestmove ")]
        require(len(moves) == 2 and all(move in legal for move in moves),
                "late duplicate or illegal phase result after the final join")
        (directory / "runtime.stdout").write_bytes(output)
        return dict(fixture_source=owner.pin(fixture), native=owner.pin((directory / "x").read_bytes()),
            actual_resource_profile="test-p4", actual_workers=4, actual_tt_entries=1 << 22,
            last_initializer_delayed=True, gate_arrival_observed=True,
            no_uci_before_release=True, uci_ready_after_release=True,
            private_copy_removed=not disposable.exists(), legal_search_relaunches=2,
            post_GO2_join_observed=True,
            output=owner.pin(output), physical=physical, cleanup=cleanup,
            shipping_identity_claimed=False)
    finally:
        if runtime is not None:
            runtime.cleanup()


def bound_selection(manifest):
    """Reject other families, representations and lifecycle stages before use."""
    require(manifest.get("class") == "rove4k-production-profile-v1" and
            manifest.get("family") in tuple("ACEF") and
            manifest.get("entry") == manifest.get("family") and
            manifest.get("resources", {}).get("id") == "test-p4" and
            manifest.get("post_profile") == {"path": PHASE, "variant": "phase-init"} and
            manifest.get("plan", {}).get("representation") == "source-jit" and
            manifest.get("plan", {}).get("entry_cleanup") == "private-path",
            "source-bound mechanism mode requires an actual A/C/E/F TEST-P4 phase-init source-JIT build")


def run_bound(build, out):
    """Exercise only the exact selected C after full current producer replay."""
    names = (SELF, PHASE, SOURCE, COMMON, VERIFIER, OWNER, RUNTIME)
    observed = {name: normalized(ROOT / name) for name in names}
    verifier = load("phase_bound_admission", ROOT / VERIFIER)
    manifest_raw = verifier.artifact_file(build, "build.json").read_bytes()
    manifest = json.loads(manifest_raw)
    bound_selection(manifest)
    admitted = verifier.admit_c_build(manifest, build)
    require(admitted.family == manifest["family"] and admitted.profile_id == "test-p4" and
            admitted.full and admitted.representation == "source-jit" and
            admitted.source == "main.c" and admitted.native == "native/x",
            "admitted actual phase artifact differs from the selected TEST-P4 build")
    require(manifest["compile_executor"] == manifest["compiler"],
            "bound mechanisms require the actual admitted source-JIT compiler argv")
    shipping = {}
    for role, path in (("source", admitted.source), ("native", admitted.native), ("whole", admitted.program)):
        expected = {key: admitted.expected[role + "_" + key] for key in ("bytes", "sha256")}
        shipping[role] = verifier.checked_artifact(build, path, expected)
    for name, data in observed.items():
        require(normalized(ROOT / name) == data, "bound mechanism support changed during admission: " + name)
    owner = load("phase_bound_owner", ROOT / OWNER)
    require(owner.pin(observed[PHASE]) == manifest["inputs"][PHASE],
            "bound phase helper differs from the selected production input")
    require(owner.pin(observed[RUNTIME])["sha256"] == verifier.SUPPORT[RUNTIME],
            "bound process owner differs from the maintained runtime driver")
    out.mkdir()
    frozen = out / "inputs"
    for name, data in observed.items():
        target = frozen / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    phase = load("phase_bound_helper", frozen / PHASE)
    runtime_module = load("phase_bound_runtime", frozen / RUNTIME)
    report = dict(format=1, **{"class": "rove4k-bound-phase-mechanism-v1"},
        mode="source-bound", complete=False, source_bound=False,
        entry=admitted.family, profile=admitted.profile_id, representation=admitted.representation,
        selected_post_profile=manifest["post_profile"],
        build=dict(path=str(build), **owner.pin(manifest_raw)),
        actual={role: dict(path=path, **owner.pin(shipping[role])) for role, path in
                (("source", admitted.source), ("native", admitted.native), ("whole", admitted.program))},
        resources=admitted.resources, source_closure=manifest["source_closure"],
        admitted_input_pins=admitted.input_pins, source_contract=admitted.source_contract,
        support_inputs={name: owner.pin(data) for name, data in observed.items()},
        commands=[], mechanisms=[], startup_barriers=[],
        production_adopted=False, runtime_qualified=False, rules_eligibility="unproven",
        scope="selected artifact source admission plus scaled callback and instrumented actual W4 main",
        shipping_binary_executed=False, large_submission_tt_executed=False,
        derived_other_resource_profiles=False, timing_claimed=False)

    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    owner.LIMITS.update(aggregate_wall=300, per_command_wall=60, parent_AS=2 << 30,
        child_AS=2 << 30, parent_CPU=120, parent_CPU_hard=150, child_CPU=45)
    previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    host = owner.Host(out, report, save)
    closed = False
    try:
        source = shipping["source"]
        context = phase.CONTEXT[admitted.family]
        resource_proof = manifest["source_proofs"][0]
        require(resource_proof["resources"] == {key: admitted.resources[key]
                    for key in resource_proof["resources"]} and
                resource_proof["resources"]["workers"] == 4,
                "actual selected resource proof differs from its admitted TEST-P4 record")
        directory = out / "selected-W4-scaled-callback"
        directory.mkdir()
        fixture, expected = scaled_fixture(source, resource_proof, context)
        (directory / "fixture.c").write_bytes(fixture)
        compiler = manifest["compiler"]
        host.run([*compiler, "-Wl,--wrap=pthread_create"], cwd=directory,
                 kind="selected-W4-scaled-callback-compile", data=fixture)
        raw = host.run([directory / "x"], cwd=directory, kind="selected-W4-scaled-callback-execute")
        lines = raw.decode("ascii").splitlines()
        require(len(lines) == 3 and lines[:2] == ["bestmove g1f3", "bestmove b1c3"] and
                json.loads(lines[2]) == expected, "actual selected phase callback/selector mechanism differs")
        report["mechanisms"].append(dict(profile="test-p4", variant="phase-init",
            shipping_source=owner.pin(source), fixture_source=owner.pin(fixture),
            native=owner.pin((directory / "x").read_bytes()), observation=expected,
            output=owner.pin(raw), selector_results=lines[:2], fixture_tt_entries=1 << FIXTURE_BITS,
            shipping_worker_count_unchanged=True, shipping_tt_executed=False,
            shipping_binary_executed=False, search_executed=False))
        save()
        barrier = check_barrier(host, owner, runtime_module, out / "selected-W4-last-initializer",
                                source, context, compiler)
        report["startup_barriers"].append(dict(variant="phase-init", shipping_source=owner.pin(source),
                                                **barrier))
        require(verifier.artifact_file(build, "build.json").read_bytes() == manifest_raw,
                "selected build receipt changed during its bound mechanisms")
        for role, path in (("source", admitted.source), ("native", admitted.native), ("whole", admitted.program)):
            require(verifier.checked_artifact(build, path, owner.pin(shipping[role])) == shipping[role],
                    "selected shipping artifact changed during its bound mechanisms")
        for name, data in observed.items():
            require(normalized(ROOT / name) == data, "bound mechanism support changed during execution: " + name)
        host.close()
        closed = True
        require(report["host_cleanup"] == {"unsettled_commands": 0, "errors": []},
                "source-bound mechanism commands are not settled")
        report.update(complete=True, source_bound=True)
        save()
    except BaseException as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        save()
        raise
    finally:
        try:
            if not closed:
                host.close()
        finally:
            signal.signal(signal.SIGCHLD, previous)
    print(json.dumps(dict(entry=admitted.family, profile=admitted.profile_id, complete=True,
        source_bound=True, build=report["build"], actual=report["actual"],
        mechanisms=1, startup_barriers=1, actual_short_GO_cycles=2,
        production_adopted=False, runtime_qualified=False)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--entry", choices=tuple("ACEF"), help="fresh all-variant experiment")
    mode.add_argument("--build", type=Path, help="actual selected TEST-P4 phase-init artifact")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if (sys.platform != "linux" or platform.machine() != "x86_64" or not args.out.is_absolute()
            or out.exists() or ROOT in (out, *out.parents)
            or any((p / ".git").exists() for p in (out, *out.parents))):
        parser.error("Linux x86-64 and a new absolute output outside every Git checkout required")
    if args.build is not None:
        if not args.build.is_absolute() or not args.build.is_dir():
            parser.error("source-bound mode requires an existing absolute build directory")
        run_bound(args.build.resolve(), out)
        return
    names = [SELF, PHASE, SOURCE, BUILDER, COMMON, PACKAGE, WRAPPER, UNLINK, OWNER, RUNTIME]
    if args.entry == "E":
        names.extend(("engines/model/e19.py", "engines/model/e19.json"))
    observed = {name: normalized(ROOT / name) for name in names}
    owner = load("phase_check_owner", ROOT / OWNER)
    out.mkdir()
    report = dict(format=1, **{"class": "rove4k-portable-phase-experiment-v1"},
        entry=args.entry, complete=False, commands=[], measurements=[], mechanisms=[], startup_barriers=[],
        scope="fresh source authority; two actual source/native/whole productions; bounded mechanism fixtures",
        production_adopted=False, runtime_qualified=False, rules_eligibility="unproven",
        large_submission_tt_executed=False, timing_claimed=False)

    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    owner.LIMITS.update(aggregate_wall=1800, per_command_wall=600, parent_AS=4 << 30,
        child_AS=4 << 30, parent_CPU=600, parent_CPU_hard=720, child_CPU=480)
    previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)

    class Host(owner.Host):
        def settle(self, child, row, force=False):
            if row.get("kind") == "fresh-profile-control":
                row["cooperative_termination_seconds"] = 30
            return super().settle(child, row, force)

    host = Host(out, report, save)
    try:
        control_build = out / "fresh-control"
        host.run([sys.executable, "-I", "-B", ROOT / BUILDER, "--entry", args.entry,
                  "--profile", "test-p4", "--out", control_build], cwd=out, kind="fresh-profile-control")
        manifest_raw = (control_build / "build.json").read_bytes()
        manifest = json.loads(manifest_raw)
        require(manifest["class"] == "rove4k-production-profile-v1" and
                manifest["complete"] and manifest["reproducible"] and
                manifest["host_cleanup"] == {"unsettled_commands": 0, "errors": []} and
                all(row["returncode"] == 0 and row["terminal"] and row["reaped"] and
                    row["owned_group_absent"] and not row["forced_cleanup"] for row in manifest["commands"]),
                "fresh maintained profile control is incomplete or unsettled")
        frozen = out / "inputs"
        for name, data in observed.items():
            require(normalized(ROOT / name) == data, "experiment input changed during fresh generation: " + name)
            expected = manifest["inputs"].get(name)
            require(expected is None or expected == owner.pin(data), "fresh control input disagrees: " + name)
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        report["inputs"] = {name: owner.pin(data) for name, data in observed.items()}
        report["fresh_control"] = dict(report=owner.pin(manifest_raw), path="fresh-control",
            current_production_closure=manifest["source_closure"], freshly_regenerated=True)
        projection = load("phase_check_projection", frozen / SOURCE)
        phase = load("phase_check_transform", frozen / PHASE)
        contracts = load("phase_check_contracts", frozen / COMMON)
        package = load("phase_check_package", frozen / PACKAGE)
        wrapper = load("phase_check_wrapper", frozen / WRAPPER)
        unlink = load("phase_check_unlink", frozen / UNLINK)
        runtime_module = load("phase_check_runtime", frozen / RUNTIME)
        base = (control_build / "control/main.c").read_bytes()
        require((len(base), owner.sha(base)) == projection.INPUTS[args.entry],
                "fresh underlying source is outside the exact resource projection domain")
        report["fresh_control"]["source"] = owner.pin(base)
        compiler, compression = manifest["compiler"], manifest["compression"]
        require(manifest["compile_executor"] == compiler, "this experiment requires the actual admitted cc argv")
        report.update(compiler=compiler, compression=compression,
            compiler_version=manifest["compile_executor_version"],
            wrapper_contract=wrapper.contract(package, unlink, compiler))
        model_module = model = None
        if args.entry == "E":
            model_module = load("phase_check_e19", frozen / "engines/model/e19.py")
            model = model_module.Model.load(frozen / "engines/model/e19.json")
        owner.LIMITS.update(child_AS=2 << 30, child_CPU=120, per_command_wall=120)
        sources = {}
        for profile_id in PROFILES:
            profile = contracts.resource_profile(profile_id)
            for variant in VARIANTS:
                attempts = []
                for attempt in ("first", "repeat"):
                    directory = out / "costs" / profile_id / variant / attempt
                    native_directory = directory / "native"
                    native_directory.mkdir(parents=True)
                    source, resource_proof = projection.transform_source(base, family=args.entry, profile=profile)
                    require(projection.restore_source(source, resource_proof) == base, "resource inverse differs")
                    proofs = [resource_proof]
                    if variant != "control":
                        parent = source
                        source, proof = phase.transform_source(source, family=args.entry, profile_id=profile_id,
                                                               variant=variant)
                        require(phase.restore_source(source, proof) == parent, "phase inverse differs")
                        proofs.append(proof)
                    if model is not None:
                        source_model = model_module.Model.from_physical_source(source,
                            model_id="e19-admitted-source-baseline")
                        source, proof = model.bind_physical_table(source, source_model=source_model)
                        proofs.append(proof)
                    (directory / "main.c").write_bytes(source)
                    proof_raw = (json.dumps(proofs, indent=2) + "\n").encode()
                    (directory / "source-proof.json").write_bytes(proof_raw)
                    host.run(compiler, cwd=native_directory,
                             kind=f"{profile_id}-{variant}-{attempt}-compile", data=source)
                    native = (native_directory / "x").read_bytes()
                    header = wrapper.header(package, unlink, compiler)
                    whole = wrapper.package(package, unlink, source, compression, compiler)
                    require(whole.startswith(header), "source package header differs")
                    payload = whole[len(header):]
                    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                    require(decoder.decompress(payload, max_length=len(source) + 1) == source and
                            decoder.eof and not decoder.unused_data, "strict source package restoration differs")
                    for name, data in (("x", whole), ("header.sh", header), ("payload.lzma", payload)):
                        (directory / name).write_bytes(data)
                    (directory / "x").chmod(0o700)
                    row = {kind + "_" + key: value for kind, data in
                        (("source", source), ("native", native), ("whole", whole),
                         ("header", header), ("payload", payload), ("proof", proof_raw))
                        for key, value in owner.pin(data).items()}
                    attempts.append(dict(directory=str(directory.relative_to(out)), **row))
                    if attempt == "first":
                        sources[(profile_id, variant)] = (source, resource_proof)
                require({k: v for k, v in attempts[0].items() if k != "directory"} ==
                        {k: v for k, v in attempts[1].items() if k != "directory"},
                        "independent source/native/whole reproduction differs")
                report["measurements"].append(dict(profile=profile_id, variant=variant,
                    attempts=attempts, reproducible=True, **{k: v for k, v in attempts[0].items()
                                                           if k != "directory"}))
                save()
        for row in report["measurements"]:
            control = next(r for r in report["measurements"]
                           if r["profile"] == row["profile"] and r["variant"] == "control")
            row["delta_vs_control"] = {kind: row[kind + "_bytes"] - control[kind + "_bytes"]
                                       for kind in ("source", "native", "whole")}
        save()
        context = phase.CONTEXT[args.entry]
        for profile_id in PROFILES:
            for variant in phase.VARIANTS:
                directory = out / "mechanisms" / profile_id / variant
                directory.mkdir(parents=True)
                source, resource_proof = sources[(profile_id, variant)]
                fixture, expected = scaled_fixture(source, resource_proof, context)
                (directory / "fixture.c").write_bytes(fixture)
                host.run([*compiler, "-Wl,--wrap=pthread_create"], cwd=directory,
                    kind=f"{profile_id}-{variant}-mechanism-compile", data=fixture)
                driver = ("import resource,os;resource.setrlimit(resource.RLIMIT_STACK,(262144,262144));"
                    "os.execv(" + repr(str(directory / "x")) + ",[" + repr(str(directory / "x")) + "])")
                raw = host.run([sys.executable, "-I", "-B", "-c", driver], cwd=directory,
                               kind=f"{profile_id}-{variant}-mechanism-execute")
                lines = raw.decode("ascii").splitlines()
                require(len(lines) == 3 and lines[:2] == ["bestmove g1f3", "bestmove b1c3"] and
                        json.loads(lines[2]) == expected, "actual phase initialization/selector mechanism differs")
                report["mechanisms"].append(dict(profile=profile_id, variant=variant,
                    fixture_source=owner.pin(fixture), native=owner.pin((directory / "x").read_bytes()),
                    observation=expected, output=owner.pin(raw), selector_results=lines[:2],
                    fixture_tt_entries=1 << FIXTURE_BITS, shipping_worker_count_unchanged=True,
                    shipping_tt_executed=False, default_stack_bytes=262144, search_executed=False))
                save()
        for variant in phase.VARIANTS:
            source, _ = sources[("test-p4", variant)]
            row = check_barrier(host, owner, runtime_module, out / ("startup-" + variant),
                                source, context, compiler)
            report["startup_barriers"].append(dict(variant=variant, **row))
            save()
        report["complete"] = True
        save()
    except BaseException as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        save()
        raise
    finally:
        try:
            host.close()
        finally:
            signal.signal(signal.SIGCHLD, previous)
    print(json.dumps(dict(entry=args.entry, complete=True, production_adopted=False,
        costs=[dict(profile=r["profile"], variant=r["variant"], source=r["source_bytes"],
                    native=r["native_bytes"], whole=r["whole_bytes"], delta=r["delta_vs_control"])
               for r in report["measurements"]], mechanisms=len(report["mechanisms"]),
        startup_barriers=len(report["startup_barriers"]))))


if __name__ == "__main__":
    main()
