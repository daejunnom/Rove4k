#!/usr/bin/env python3
"""Poisoned small-TT proof of D's real raw-clone startup barrier.

This runs the actual generated runtime with test-only owner instrumentation.
It proves zeroing/coverage/publication, plus a real W256 GO with 257 pending
reservations and one think completion per worker before the actual result.
It does not prove NUMA locality, real TT34 memory admission, playing strength,
per-worker search work, throughput, or 4KiB qualification.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NATIVE = ("tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld")
PRODUCER_INPUTS = tuple("engines/compact/tiny-entry-d/native/" + name for name in NATIVE) + (
    "engines/compact/tiny-entry-d/recipe.json", "engines/compact/tiny-entry-d/shipping_fused_ray.py",
    "engines/compact/tiny-entry-d/packer.py", "engines/experiments/tcec-scope/build.py",
    "engines/scripts/production.py", "engines/scripts/minify.py", "engines/scripts/rename_c.py",
    "engines/experiments/tiny-d-submission/source.py", "engines/experiments/tiny-d-submission/build.py",
    "engines/experiments/tiny-d-submission/packaging.py")
STORAGE_INPUT = "engines/experiments/tiny-d-submission/storage.py"
CHECKER_INPUT = "engines/experiments/tiny-d-submission/test_startup.py"
STORAGE_MODES = ("none", "prefix", "dense", "prefix-dense")


def pin(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def normalized(path):
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ValueError("lone CR in named startup input: " + str(path))
    return data


def json_equal(left, right):
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(right, sort_keys=True, separators=(",", ":"))


def composition_inputs():
    recipe = json.loads(normalized(ROOT / "engines/compact/tiny-entry-d/recipe.json"))
    return tuple(recipe["shared_source_sha256"]) + tuple(recipe["helper_sha256"])


def require_execution(row, expected):
    if (row.get("returncode") != expected or not row.get("terminal") or not row.get("reaped") or
            not row.get("owned_group_absent") or row.get("forced_cleanup") or
            row.get("other_group_members_before_reap") != [] or
            not row.get("original_identity_retained_until_other_members_absent")):
        raise ValueError("startup execute returncode or settlement differs")


def prepared(source, profile, equivalent, storage_tool, storage_mode):
    """Replay and invert the entire own-source projection, before instrumentation."""
    base, proof = source.prepare(profile, equivalent_edits=equivalent)
    restored = dict(base)
    for name, record in proof["source_edits"].items():
        restored[name] = source.restore(base[name], record)
    canonical = {name:source.normalized(source.CANONICAL / "native" / name) for name in NATIVE}
    composition = source.load("d_startup_source_composition", source.ROOT / "engines/scripts/source_composition.py")
    canonical["board.c"] = composition.read_source(source.ROOT, "engines/compact/tiny-entry-d/native/board.c")
    fused = source.load("d_startup_fused_inverse", source.CANONICAL / "shipping_fused_ray.py")
    expected_board, _ = fused.transform_source(canonical["board.c"])
    if restored["board.c"] != expected_board:
        raise ValueError("startup prepare Board inverse differs")
    replacement = b"#if D_HQ || DEV\n" + fused.OLD + b"\n#else\n" + fused.SCALAR + b"\n#endif"
    at = fused.OFFSET
    if restored["board.c"][at:at + len(replacement)] != replacement:
        raise ValueError("startup fused Board inverse role differs")
    restored["board.c"] = restored["board.c"][:at] + fused.OLD + restored["board.c"][at + len(replacement):]
    if restored != canonical:
        raise ValueError("startup complete prepare inverse differs")
    files = base
    if storage_mode != "none":
        files, storage_proof = storage_tool.transform(base, prefix="prefix" in storage_mode, dense="dense" in storage_mode)
        if storage_tool.restore(files, storage_proof) != base:
            raise ValueError("startup complete storage inverse differs")
        proof["storage"] = storage_proof
    return files, proof


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def instrument(files, *, fail=False, omit_clear=False, go=False):
    result = dict(files)
    source = result["runtime.c"]
    roles = [
        ("trace-storage", b"static Move fallback;", b"static Move fallback;\nstatic atomic_uint test_owners[((size_t)1<<TT_BITS)/256],test_arrived[WORKERS];"
         + (b"\nstatic atomic_uint test_completed[WORKERS],test_published,test_results;" if go else b"")),
        ("poison-before-workers", b"table=allocate(((size_t)1<<TT_BITS)*sizeof *table);if(!table)return 2;start(&position);",
         b"table=allocate(((size_t)1<<TT_BITS)*sizeof *table);if(!table)return 2;memset(table,165,((size_t)1<<TT_BITS)*sizeof *table);start(&position);"),
        ("trace-before-production-clear", b"    memset(table+begin,0,(end-begin)*sizeof *table);",
         b"    for(size_t p=begin/256;p<end/256;p++)if(atomic_exchange_explicit(test_owners+p,(unsigned)w->id+1,memory_order_relaxed))abort();\n"
         b"    atomic_store_explicit(test_arrived+w->id,1,memory_order_relaxed);\n"
         + (b"    (void)begin;(void)end;" if omit_clear else b"    memset(table+begin,0,(end-begin)*sizeof *table);")),
        ("observe-after-production-barrier", b"    if(status)goto shutdown;\n    wait();\n    for(;;){",
         b"    if(status)goto shutdown;\n    wait();\n"
         b"    for(size_t b=0;b<((size_t)1<<TT_BITS)*sizeof *table;b++)if(((unsigned char *)table)[b]){output(\"TEST_POISON_REMAINS\\n\");status=7;goto shutdown;}\n"
         b"    for(size_t p=0;p<((size_t)1<<TT_BITS)/256;p++)if(atomic_load(test_owners+p)!=((p+1)*WORKERS-1)/(((size_t)1<<TT_BITS)/256)+1){output(\"TEST_OWNER_DIFFERS\\n\");status=8;goto shutdown;}\n"
         b"    for(int i=0;i<WORKERS;i++)if(atomic_load(test_arrived+i)!=1){output(\"TEST_ARRIVAL_DIFFERS\\n\");status=9;goto shutdown;}\n"
         b"    output(\"TEST_INITIALIZED\\n\");\n    for(;;){"),
    ]
    if fail:
        roles.append(("partial-spawn-failure", b"char *stack=allocate(1048576+4096);if(!stack){status=2;break;}",
                      b"if(created==2){output(\"TEST_INJECTED_SPAWN_FAILURE\\n\");status=2;break;}char *stack=allocate(1048576+4096);if(!stack){status=2;break;}"))
    if go:
        roles += [
            ("observe-257-after-real-store-before-epoch",
             b"atomic_store_explicit(&pending,WORKERS+1,memory_order_relaxed);atomic_fetch_add_explicit(&epoch,1,memory_order_release);wake(&epoch);",
             b"atomic_store_explicit(&pending,WORKERS+1,memory_order_relaxed);"
             b"_Static_assert(WORKERS==256,\"W256 GO fixture\");"
             b"unsigned test_count=(unsigned)atomic_load_explicit(&pending,memory_order_relaxed);"
             b"if(test_count!=257)abort();atomic_store_explicit(&test_published,test_count,memory_order_relaxed);"
             b"atomic_fetch_add_explicit(&epoch,1,memory_order_release);wake(&epoch);"),
            ("record-each-real-think-return-before-pending-decrement",
             b"seen=current;w->best=0;think(w,&position);",
             b"seen=current;w->best=0;think(w,&position);"
             b"if((unsigned)w->id>=WORKERS||atomic_fetch_add_explicit(test_completed+w->id,1,memory_order_relaxed))abort();"),
            ("check-all-256-before-real-result-reservation-release",
             b"result();atomic_store_explicit(&pending,0,memory_order_release);wake(&pending);",
             b"if(atomic_load_explicit(&test_published,memory_order_relaxed)!=257||"
             b"atomic_load_explicit(&pending,memory_order_relaxed)!=1||"
             b"atomic_fetch_add_explicit(&test_results,1,memory_order_relaxed))abort();"
             b"for(int i=0;i<WORKERS;i++)if(atomic_load_explicit(test_completed+i,memory_order_relaxed)!=1)abort();"
             b"output(\"TEST_PENDING_257\\nTEST_FINISHED_256\\n\");"
             b"result();atomic_store_explicit(&pending,0,memory_order_release);wake(&pending);"),
        ]
    tool = load("d_startup_source_projection", HERE / "source.py")
    result["runtime.c"], proof = tool.project(source, roles)
    return result, proof


# This child inherits the command owner's process group. It keeps stdin open
# until the real bestmove, avoiding quit/EOF's early stopped=1 side effect.
DIALOGUE = r'''import json,os,select,subprocess,sys,time
from pathlib import Path
receipt=Path(sys.argv[2]);record=dict(complete=False,events=[],engine_started=False,
    engine_reaped=False,forced_cleanup=False)
def save():receipt.write_text(json.dumps(record,indent=2)+"\n")
save();child=None;buffer=b"";deadline=time.monotonic()+20
def emit(data):
    while data:
        written=os.write(1,data);data=data[written:]
def send(data):
    child.stdin.write(data);child.stdin.flush()
    record["events"].append(dict(send=data.decode()));save()
def until(predicate):
    global buffer
    while True:
        if b"\n" in buffer:
            line,buffer=buffer.split(b"\n",1);line+=b"\n"
            emit(line);record["events"].append(dict(receive=line.decode()));save()
            if predicate(line):return line
            continue
        left=deadline-time.monotonic()
        if left<=0:raise TimeoutError("bounded W256 GO dialogue")
        if select.select([child.stdout],[],[],min(left,.25))[0]:
            data=os.read(child.stdout.fileno(),4096)
            if not data:raise ValueError("engine EOF before expected dialogue output")
            buffer+=data
            if len(buffer)>65536:raise ValueError("dialogue output limit")
try:
    child=subprocess.Popen([sys.argv[1]],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                           stderr=None,bufsize=0)
    record.update(engine_started=True,pid=child.pid,pgid=os.getpgid(child.pid),
                  owner_pgid=os.getpgrp(),inherits_owner_group=os.getpgid(child.pid)==os.getpgrp())
    save()
    if not record["inherits_owner_group"]:raise ValueError("nested engine left owned group")
    send(b"uci\n");until(lambda line:line==b"uciok\n")
    send(b"position startpos\ngo wtime 100 btime 100\n")
    best=until(lambda line:line.startswith(b"bestmove "))
    record["bestmove"]=best.decode().strip();save()
    send(b"isready\n");until(lambda line:line==b"readyok\n")
    send(b"quit\n");child.stdin.close();child.stdin=None
    code=child.wait(timeout=5);record.update(engine_reaped=True,returncode=code)
    trailing=buffer+child.stdout.read()
    if trailing:emit(trailing);raise ValueError("unexpected output after readyok")
    if code:raise ValueError("engine returned "+str(code))
    record["complete"]=True
except BaseException as error:
    record["failure"]=dict(type=type(error).__name__,message=str(error));raise
finally:
    if child is not None:
        if child.poll() is None:
            record["forced_cleanup"]=True;child.terminate()
            try:child.wait(timeout=2)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=2)
        record.update(engine_reaped=child.returncode is not None,returncode=child.returncode)
    save()
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--build", type=Path, help="bind to a complete unreduced D generated-readable source selection")
    args = parser.parse_args()
    out = args.out.resolve()
    if (sys.platform != "linux" or platform.machine() != "x86_64" or
            not args.out.is_absolute() or out.exists() or
            any((p / ".git").exists() for p in (out, *out.parents))):
        parser.error("new absolute external output on Linux x86-64 required")
    names = tuple("engines/compact/tiny-entry-d/native/" + n for n in NATIVE) + (
        "engines/compact/tiny-entry-d/recipe.json",
        "engines/compact/tiny-entry-d/shipping_fused_ray.py",
        "engines/experiments/tcec-scope/build.py", "engines/scripts/production.py",
        "engines/experiments/tiny-d-submission/source.py",
        "engines/experiments/tiny-d-submission/build.py",
        CHECKER_INPUT)
    names += composition_inputs()
    selected = None
    if args.build is not None:
        if not args.build.is_absolute():
            parser.error("--build requires an absolute D build directory")
        selected_root = args.build.resolve()
        manifest = (selected_root / "build.json").read_bytes(); selected = json.loads(manifest)
        if (any(selected.get(key) is not True for key in ("complete", "frozen_execution", "native_reproduced")) or
                selected.get("family") != "D" or selected.get("source_reduced") is not False or
                type(selected.get("equivalent_edits")) is not bool or selected.get("storage") not in STORAGE_MODES):
            raise ValueError("complete frozen unreduced D source selection required")
        names = PRODUCER_INPUTS + composition_inputs() + ((STORAGE_INPUT,) if selected["storage"] != "none" else ())
        if not isinstance(selected.get("inputs"), dict) or set(selected["inputs"]) != set(names):
            raise ValueError("selected producer input closure differs from explicit allowlist")
        names += (CHECKER_INPUT,)
    frozen = {}
    for name in names:
        data = normalized(ROOT / name)
        if selected is not None and name != CHECKER_INPUT:
            expected = selected["inputs"][name]
            if pin(data) != expected or (selected_root / "inputs" / name).read_bytes() != data:
                raise ValueError("selected producer current/frozen input differs: " + name)
        frozen[name] = data
    if selected is not None:
        frozen["selection/build.json"] = manifest
        for name in NATIVE:
            frozen["selection/generated-readable/" + name] = (selected_root / "generated-readable" / name).read_bytes()
    out.mkdir()
    for name, data in frozen.items():
        path = out / "inputs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    executing = load("d_startup_frozen_execution", out / "inputs/engines/experiments/tiny-d-submission/test_startup.py")
    executing.run_snapshot(out, frozen)


def run_snapshot(out, frozen):
    source = load("d_startup_source", HERE / "source.py")
    builder = load("d_startup_builder", HERE / "build.py")
    api = source.production()
    hostmod = load("d_startup_host", ROOT / source.HOST)
    if source.pin(source.normalized(ROOT / source.HOST))["sha256"] != source.HOST_SHA:
        raise ValueError("original command owner differs")
    hostmod.LIMITS = {**hostmod.LIMITS, "aggregate_wall": 240, "per_command_wall": 35,
                      "parent_CPU": 90, "parent_CPU_hard": 100, "child_CPU": 20}
    selected = json.loads(frozen["selection/build.json"]) if "selection/build.json" in frozen else None
    storage_mode = selected["storage"] if selected is not None else "none"
    equivalent = selected["equivalent_edits"] if selected is not None else True
    storage_tool = load("d_startup_selected_storage", HERE / "storage.py") if storage_mode != "none" else None
    report = dict(kind="D-selected-source-poisoned-TT-startup-and-W256-GO-v3" if selected is not None else
                      "D-real-raw-clone-poisoned-TT-startup-and-W256-GO-v2",
                  complete=False, commands=[], cases=[], frozen_execution=True,
                  source_bound=False, runtime_qualified=False, native_qualified=False, whole_artifact_qualified=False,
                  inputs={name: source.pin(data) for name, data in frozen.items()},
                  real_target_allocation=False, locality_proof=False,
                  strength_claim=False, per_worker_search_work_proof=False)
    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    host = hostmod.Host(out, report, save)
    try:
        selected_pins = None
        if selected is not None:
            resource = selected.get("resource")
            if not isinstance(resource, dict) or resource.get("id") not in ("test-p4", "test-p28", "tcec-provisional"):
                raise ValueError("finite selected D resource profile required")
            profile = api.resource_profile(resource["id"])
            selected_files, selected_proof = prepared(source, profile, equivalent, storage_tool, storage_mode)
            actual = {name:frozen["selection/generated-readable/" + name] for name in NATIVE}
            if (not json_equal(profile.to_record(16), resource) or not json_equal(selected_proof, selected["proof"]) or
                    selected_files != actual):
                raise ValueError("selected D full proof/resource/generated-readable replay differs")
            selected_pins = {name:source.pin(data) for name,data in sorted(actual.items())}
            report.update(source_bound=True, selected_build_manifest=source.pin(frozen["selection/build.json"]),
                selected_source=selected_pins, selected_build=dict(resource=resource, storage=storage_mode,
                    equivalent_edits=equivalent, producer_inputs=selected["inputs"], proof=selected_proof,
                    source_only=True, complete_inverse=True))
            save()
        for workers, fail, omit, go in ((4, False, False, False), (28, False, False, False),
                                      (256, False, False, False), (256, False, False, True),
                                      (4, True, False, False), (4, False, True, False)):
            name = f"w{workers}-" + ("spawn-fail" if fail else "omit-clear" if omit else "go" if go else "positive")
            directory = out / name
            directory.mkdir()
            # Explicit fixture profile, never relabelled as the production TT.
            profile = api.ResourceProfile(name, "test", workers, 16 << 12)
            files, production_proof = prepared(source, profile, equivalent, storage_tool, storage_mode)
            before_instrumentation = {name:source.pin(data) for name,data in sorted(files.items())}
            if selected_pins is not None and before_instrumentation != selected_pins:
                raise ValueError("scaled fixture is not exact selected source before instrumentation")
            files, test_proof = instrument(files, fail=fail, omit_clear=omit, go=go)
            for filename, data in files.items():
                (directory / filename).write_bytes(data)
            binary = directory / "x"
            host.run(["cc", *builder.native_flags(profile), *[str(directory / n) for n in source.UNITS],
                      "-Wl,-T," + str(directory / "image.ld"), "-o", str(binary)],
                     cwd=directory, kind="compile-" + name)
            expected = 2 if fail else 7 if omit else 0
            dialogue = None
            try:
                if go:
                    driver = directory / "dialogue.py"
                    driver.write_text(DIALOGUE)
                    receipt = directory / "dialogue.json"
                    output = host.run([sys.executable, "-I", "-B", str(driver), str(binary), str(receipt)],
                                      cwd=directory, kind="execute-" + name)
                    dialogue = json.loads(receipt.read_text())
                    if (not all(dialogue.get(key) is True for key in
                                ("complete", "engine_started", "engine_reaped", "inherits_owner_group")) or
                            dialogue.get("forced_cleanup") or dialogue.get("returncode") != 0):
                        raise ValueError("W256 GO dialogue did not settle normally")
                else:
                    output = host.run([str(binary)], cwd=directory, kind="execute-" + name,
                                      data=b"uci\nisready\nquit\n")
            except ValueError:
                if expected == 0:
                    raise
                row = report["commands"][-1]
                if (row.get("returncode") != expected or row.get("forced_cleanup") or not row.get("owned_group_absent")):
                    raise
                output = Path(row["stdout"]["path"]).read_bytes()
            require_execution(report["commands"][-1], expected)
            if expected == 0 and not all(token in output for token in (b"TEST_INITIALIZED\n", b"uciok\n", b"readyok\n")):
                raise ValueError("startup/protocol output differs")
            if go:
                lines = output.splitlines()
                legal = {f"{f}2{f}{r}" for f in "abcdefgh" for r in "34"} | {"b1a3", "b1c3", "g1f3", "g1h3"}
                if (len(lines) != 6 or lines[:4] != [b"TEST_INITIALIZED", b"uciok", b"TEST_PENDING_257", b"TEST_FINISHED_256"] or
                        lines[5] != b"readyok" or not lines[4].startswith(b"bestmove ") or
                        lines[4][9:].decode() not in legal):
                    raise ValueError("W256 real GO completion/result protocol differs")
            if fail and output != b"TEST_INJECTED_SPAWN_FAILURE\n":
                raise ValueError("failure did not reach injected spawn boundary")
            if omit and output != b"TEST_POISON_REMAINS\n":
                raise ValueError("negative clear control did not detect poisoned TT")
            report["cases"].append(dict(name=name, workers=workers, tt_bits=12,
                tt_bytes=16 << 12, expected_returncode=expected, passed=True,
                real_go=go, pending_after_production_store=257 if go else None,
                think_completions=256 if go else None, before_result_pending=1 if go else None,
                dialogue=dialogue, binary=source.pin(binary.read_bytes()),
                source_before_instrumentation=before_instrumentation, selected_source_equal=selected_pins is not None,
                flags=builder.native_flags(profile),
                output=output.decode(), production=production_proof, instrumentation=test_proof))
            save()
        report["complete"] = True
    except BaseException as error:
        report["complete"] = False
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        try:
            host.close()
        except BaseException as error:
            report["complete"] = False
            report["cleanup_failure"] = dict(type=type(error).__name__, message=str(error))
            raise
        finally:
            cleanup = report.get("host_cleanup", {})
            if cleanup.get("errors") or cleanup.get("unsettled_commands"):
                report["complete"] = False
            save()
    if not report["complete"]:
        raise ValueError("startup checker cleanup incomplete")
    print(json.dumps(dict(cases=len(report["cases"]), complete=True, source_bound=report["source_bound"],
                          real_target_allocation=False)))


if __name__ == "__main__":
    main()
