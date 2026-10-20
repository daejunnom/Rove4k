#!/usr/bin/env python3
"""Actual raw go/main dispatch with explicit synthetic completion boundaries.

No physical worker is created by this class of proof. The native shipping
runtime is included with unchanged go/main bodies; only now/read_line/futex
definitions and spawn are interposed at named test boundaries. Actual TT bytes,
parser, deadline arithmetic, dispatch, result and wait bodies are exercised.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
NATIVE_MANIFEST_SHA = "1055c89f0f7bc042d33ad53ccad82fb9ca6a39368e6ed84dfd9e2a82fef24767"
RUNTIME_SHA = "82c62b57e500918827721553d67d9e23073c6cb5ca79dc22cdb8e38ab15f8e63"
HELPER_SHA = "045550ae095457923343fd5a462b47296f3749abf621a936329863cd5c69d252"
RUNNING = set()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(test, message):
    if not test:
        raise AssertionError(message)


def terminated(signum, frame):
    raise TimeoutError("unit validator SIGTERM")


def function_body(source, prefix):
    start = source.index(prefix) + len(prefix) - 1
    require(source[start] == "{", "function prefix must end at opening brace")
    depth, state, i = 0, "code", start
    while i < len(source):
        c, following = source[i], source[i:i + 2]
        if state == "line":
            if c == "\n":
                state = "code"
        elif state == "comment":
            if following == "*/":
                state, i = "code", i + 1
        elif state in ("'", '"'):
            if c == "\\":
                i += 1
            elif c == state:
                state = "code"
        elif following in ("//", "/*"):
            state, i = ("line" if following == "//" else "comment"), i + 1
        elif c in ("'", '"'):
            state = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if not depth:
                return source[start:i + 1].encode()
        i += 1
    raise ValueError("unterminated C function")


def instrument(data):
    require(sha(data) == RUNTIME_SHA, "unknown candidate runtime")
    source = data.decode()
    body_hashes = {"go": sha(function_body(source, "static void go(char *s){")),
                   "main": sha(function_body(source, "int main(void){"))}
    for old, new in (("static void futex_wait(", "static void real_futex_wait("),
                     ("uint64_t now(void){", "uint64_t real_now(void){"),
                     ("static int read_line(", "static int real_read_line("),
                     ("int main(void){", "int subject_main(void){")):
        require(source.count(old) == 1, "unexpected boundary declaration: " + old)
        source = source.replace(old, new, 1)
    require(sha(function_body(source, "static void go(char *s){")) == body_hashes["go"], "go body changed")
    require(sha(function_body(source, "int subject_main(void){")) == body_hashes["main"], "main body changed")
    return source.encode(), body_hashes


def load_helper():
    path = HERE / "inputs/entry/verify.py"
    require(sha(path.read_bytes()) == HELPER_SHA, "frozen process helper differs")
    spec = importlib.util.spec_from_file_location("finite_d_unit_helper", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compile_owned(command, directory, budget):
    with (directory / "compile.stdout").open("wb") as stdout, (directory / "compile.stderr").open("wb") as stderr:
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        try:
            proc = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True,
                                    preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, inherited))
            RUNNING.add(proc)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
        try:
            code = proc.wait(timeout=budget.left(35))
            require(code == 0, "raw fixture compilation failed")
            return code
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=3)
            RUNNING.discard(proc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=60)
    args = parser.parse_args()
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p / ".git").exists() for p in (out, *out.parents)), "new absolute external --out required")
    require(20 <= args.budget <= 180, "bounded budget required")
    out.mkdir(parents=True)
    report = {"passed": False, "scope": "actual dispatch/TT bytes/exact fixed-clock arithmetic with SYNTHETIC completion; no physical worker or join claim",
              "forms": [], "failures": [], "constructor_cleanup": []}
    helper, phase, started = None, "inputs", time.monotonic()
    prior_term = signal.signal(signal.SIGTERM, terminated)
    try:
        helper = load_helper()
        budget = helper.Budget(args.budget)
        manifest_bytes = args.native_build.read_bytes()
        require(sha(manifest_bytes) == NATIVE_MANIFEST_SHA, "native first-cost checkpoint differs")
        manifest = json.loads(manifest_bytes)
        require(manifest["complete"] and manifest["all_layout_classes_unchanged"], "native checkpoint incomplete/class differs")
        root = args.native_build.resolve().parent / "candidate-sources"
        sources = {name: (root / name).read_bytes() for name in manifest["candidate_source_sha256"]}
        require(all(sha(data) == manifest["candidate_source_sha256"][name] for name, data in sources.items()), "candidate source bytes differ")
        changed, bodies = instrument(sources["runtime.c"])
        report.update(native_manifest_sha256=NATIVE_MANIFEST_SHA, source_sha256=manifest["candidate_source_sha256"],
                      go_main_body_sha256=bodies, go_main_bodies_unchanged=True,
                      boundary_interposition=["now definition", "read_line definition", "futex_wait definition", "spawn macro", "main entry name"],
                      instrumented_runtime_sha256=sha(changed), validator_sha256=sha(Path(__file__).read_bytes()),
                      template_sha256=sha((HERE / "units.c.in").read_bytes()), helper_sha256=HELPER_SHA)
        recipe = out / "recipe"
        recipe.mkdir()
        for name in ("units.py", "units.c.in"):
            (recipe / name).write_bytes((HERE / name).read_bytes())
        (recipe / "native-build.json").write_bytes(manifest_bytes)
        (recipe / "helper.py").write_bytes((HERE / "inputs/entry/verify.py").read_bytes())
        for name, data in sources.items():
            (recipe / name).write_bytes(data)
        for mode in ("scalar-shipping", "hq-shipping"):
            phase = mode
            directory = out / mode
            directory.mkdir()
            for name, data in sources.items():
                (directory / name).write_bytes(data)
            (directory / "runtime-subject.c").write_bytes(changed)
            (directory / "units.c.in").write_bytes((recipe / "units.c.in").read_bytes())
            prelude = b'#include "tiny.h"\nstatic void futex_wait(atomic_int *,int,int);\nstatic int read_line(char *);\n#define spawn fixture_spawn\n#include "runtime-subject.c"\n#undef spawn\n#include "units.c.in"\n'
            (directory / "fixture.c").write_bytes(prelude)
            native = next(x for x in manifest["engines"] if x["id"] == mode)
            command = []
            for arg in native["native_repeats"][0]["compile"]["command"]:
                if str(root) in arg:
                    arg = arg.replace(str(root), str(directory))
                if arg == str(directory / "runtime.c"):
                    arg = str(directory / "fixture.c")
                command.append(arg)
            command[-1] = str(directory / "fixture")
            row = {"engine": mode, "passed": False, "compile": command, "physical_workers": False}
            report["forms"].append(row)
            row["compile_exit"] = compile_owned(command, directory, budget)
            row["fixture_sha256"] = sha((directory / "fixture").read_bytes())
            owned = helper.Owned(directory / "fixture", directory / "run", budget)
            try:
                row["settled"] = owned.finish()
                stdout = owned.stdout.bytes()
                expected = b"finite unit pass commands60 clocks38 ignored14 synthetic_completions38\n"
                require(stdout.endswith(expected), "actual dispatch fixture assertions failed")
                require(stdout.splitlines().count(b"uciok") == 2 and stdout.splitlines().count(b"readyok") == 4, "actual dispatch acknowledgments differ")
                require(sum(s.startswith(b"bestmove ") for s in stdout.splitlines()) == 38, "synthetic publication count differs")
                row.update(passed=True, command_cases=60, exact_clock_cases=38, ignored_all_state_cases=14,
                           synthetic_completion_publications=38, actual_tt_full_bytes_equal=True,
                           both_quit_and_eof=True, stdout_sha256=sha(stdout))
            finally:
                row["cleanup"] = owned.cleanup()
                if row.get("passed"):
                    require(not row["cleanup"]["forced_cleanup"] and not row["cleanup"]["errors"]
                            and row["cleanup"]["owned_group_absent"] and row["cleanup"]["readers_joined"]
                            and row["cleanup"]["settled_before_cleanup"], "raw unit cleanup was not fully settled")
    except BaseException as exc:
        report["failures"].append({"phase": phase, "type": type(exc).__name__, "detail": str(exc)})
    finally:
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        try:
            for proc in list(RUNNING):
                try:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait(timeout=3)
                except BaseException as exc:
                    report["failures"].append({"phase": phase + "/compiler-cleanup", "type": type(exc).__name__, "detail": str(exc)})
            if helper:
                for owned in list(helper.OWNED):
                    try:
                        report["constructor_cleanup"].append(owned.cleanup())
                    except BaseException as exc:
                        report["failures"].append({"phase": phase + "/constructor-cleanup", "type": type(exc).__name__, "detail": str(exc)})
            report["passed"] = len(report["forms"]) == 2 and all(r["passed"] for r in report["forms"]) and not report["failures"] and not report["constructor_cleanup"]
            report["elapsed_seconds"] = time.monotonic() - started
            (out / "results.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        finally:
            signal.signal(signal.SIGTERM, prior_term)
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
    print(json.dumps({"passed": report["passed"], "results": str(out / "results.json"), "failures": report["failures"]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
