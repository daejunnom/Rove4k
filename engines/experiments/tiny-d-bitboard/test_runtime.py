#!/usr/bin/env python3
"""Probe the raw syscall runtime with a stub search, not the chess engine.

Run on Linux x86-64. Production runtime/assembly/linker inputs are copied without
changes; only the failure fixture interposes an EAGAIN-returning spawn wrapper.
This qualifies startup, generations, cancellation, stdin, and thread cleanup.
It does not qualify chess semantics, real search stack use, strength, or size.
All copied sources, binaries, commands, and results stay in a new external --out.
"""
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

HERE = Path(__file__).resolve().parent
NAMES = ("tiny.h", "runtime.c", "start.S", "image.ld")
STUB = r'''
#include "tiny.h"
void start(Board *p){memset(p,0,sizeof *p);p->s=0;p->e=-1;p->h=7;}
int gen(const Board *p,Move *m){(void)p;m[0]=MOVE(0,1,0,0,0);return 1;}
int make(const Board *p,Move m,Board *t){(void)m;*t=*p;t->s^=1;t->h++;return 1;}
void think(Worker *w,const Board *p){
    while(!atomic_load_explicit(&stopped,memory_order_relaxed)&&now()<deadline)w->nodes++;
    w->depth=1;w->score=(int)p->h;w->best=MOVE(0,1,0,0,0);
}
'''
INJECT = r'''
#include "tiny.h"
extern long real_spawn(void (*)(void *),void *,void *,int *);
long spawn(void (*fn)(void *),void *arg,void *stack,int *tid){
    static int calls;if(calls++==FAIL_AT)return -11;return real_spawn(fn,arg,stack,tid);
}
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decoded(data):
    return data.decode(errors="replace") if isinstance(data, bytes) else data or ""


def absent_group(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return True
    return False


def cleanup(process):
    # Kill the owned group even if its leader has already exited.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=3)


def require(condition, detail):
    if not condition:
        raise RuntimeError(detail)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=HERE,
                        help="TinyD directory containing frozen runtime inputs; default: this directory")
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    source = args.source_root.resolve()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists():
        parser.error("--out must be a new absolute directory")
    if source == out or source in out.parents:
        parser.error("--out must be outside the source directory")
    if any((parent / ".git").exists() for parent in (out, *out.parents)):
        parser.error("--out must be outside Git checkouts")
    if os.name != "posix" or not Path("/proc/self/task").is_dir() or os.uname().machine != "x86_64":
        parser.error("this probe requires Linux x86-64 with /proc")
    if not all((source / name).is_file() for name in NAMES):
        parser.error("--source-root must contain " + ", ".join(NAMES))
    out.mkdir(parents=True)
    frozen, fixtures, binaries = (out / name for name in ("sources", "fixtures", "binaries"))
    for directory in (frozen, fixtures, binaries):
        directory.mkdir()
    inputs = {name: (source / name).read_bytes() for name in NAMES}
    for name, data in inputs.items():
        (frozen / name).write_bytes(data)
    (out / "test_runtime.py").write_bytes(Path(__file__).read_bytes())
    (fixtures / "stub.c").write_text(STUB)
    (fixtures / "inject.c").write_text(INJECT)
    (fixtures / "start-inject.S").write_text(re.sub(r"\bspawn\b", "real_spawn", inputs["start.S"].decode()))
    flags = ["-Os", "-std=c11", "-nostdlib", "-static", "-no-pie", "-fno-pie", "-fno-pic",
             "-fno-stack-protector", "-fno-builtin", "-fno-asynchronous-unwind-tables", "-fno-unwind-tables",
             "-fno-ident", "-fcf-protection=none", "-ffunction-sections", "-fdata-sections",
             "-Wl,--gc-sections,--build-id=none,-s,-z,noexecstack", "-DWORKERS=2", "-DTT_BITS=8", "-DDEV=0",
             "-I", str(frozen)]
    report = {"scope": "Stub-search runtime probes only; no chess/search-stack/strength/size qualification.",
              "source_root": str(source), "source_sha256": {name: sha(data) for name, data in inputs.items()},
              "harness_sha256": sha(Path(__file__).read_bytes()),
              "fixture_sha256": {p.name: sha(p.read_bytes()) for p in fixtures.iterdir()},
              "production_runtime_copied_unmodified": True,
              "normal_spawn_assembly_copied_unmodified": True,
              "failure_fixture": "External assembly copy renames spawn; a wrapper returns -EAGAIN after 0 or 1 successful children.",
              "builds": [], "results": [], "passed": False}

    def build(name, failure=None):
        target = binaries / name
        assembly = frozen / "start.S" if failure is None else fixtures / "start-inject.S"
        command = [args.cc, *flags, str(frozen / "runtime.c"), str(fixtures / "stub.c"), str(assembly)]
        if failure is not None:
            command += [f"-DFAIL_AT={failure}", str(fixtures / "inject.c")]
        command += ["-Wl,-T," + str(frozen / "image.ld"), "-o", str(target)]
        record = {"id": name, "command": command}
        report["builds"].append(record)
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired as error:
            record.update(timeout=True, stdout=decoded(error.stdout), stderr=decoded(error.stderr))
            raise
        record.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        require(result.returncode == 0, f"build {name} failed: {result.stderr}")
        record["native_sha256"] = sha(target.read_bytes())
        return target

    def run(name, command, data, best=0, uci=0, ready=0, status=0):
        record = {"name": name, "passed": False, "stdin_sha256": sha(data)}
        report["results"].append(record)
        process = subprocess.Popen([str(command)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = process.communicate(data, timeout=4)
            lines = stdout.decode().splitlines()
            record.update(returncode=process.returncode, stdout=lines, stderr=stderr.decode(errors="replace"))
            require(process.returncode == status, f"{name}: unexpected exit {process.returncode}")
            require(sum(line.startswith("bestmove ") for line in lines) == best, f"{name}: wrong bestmove count")
            require(lines.count("uciok") == uci and lines.count("readyok") == ready, f"{name}: wrong protocol reply counts")
            require(not stderr, f"{name}: unexpected stderr")
            require(absent_group(process.pid), f"{name}: surviving process group")
            record["passed"] = True
        except subprocess.TimeoutExpired as error:
            record.update(timeout=True, stdout=decoded(error.stdout), stderr=decoded(error.stderr))
            raise
        except Exception as error:
            record["error"] = str(error)
            raise
        finally:
            cleanup(process)

    try:
        report["compiler"] = subprocess.check_output([args.cc, "--version"], text=True).splitlines()[0]
        native = build("runtime-normal")
        failed = [build(f"runtime-fail-{n}", n) for n in (0, 1)]
        run("startup_eof", native, b"")
        run("unterminated_uci_eof", native, b"uci", uci=1)
        run("crlf", native, b"uci\r\nisready\r\nquit\r\n", uci=1, ready=1)
        run("active_search_eof", native, b"go infinite\n", best=1)
        run("active_search_stop_quit", native, b"go infinite\nstop\nquit\n", best=1)
        run("rapid_generations", native, b"uci\n" + b"go wtime 30000 btime 30000\nstop\nposition startpos\n" * 256
            + b"isready\nquit\n", best=256, uci=1, ready=1)
        run("oversize_line_recovery", native, b"x" * 40000 + b"\nuci\nquit\n", uci=1)
        run("nul_line_recovery", native, b"u\0ci\nuci\nquit\n", uci=1)
        for n, binary in enumerate(failed):
            run(f"clone_failure_after_{n}", binary, b"", status=2)

        record = {"name": "fragmented_stdin_and_stable_startup_tids", "passed": False}
        report["results"].append(record)
        process = subprocess.Popen([str(native)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True, bufsize=0)
        try:
            end = time.monotonic() + 3
            ids = []
            while time.monotonic() < end:
                ids = sorted(p.name for p in Path(f"/proc/{process.pid}/task").iterdir())
                if len(ids) == 3:
                    break
                time.sleep(.005)
            require(len(ids) == 3, f"startup thread count: {ids}")
            process.stdin.write(b"u"); time.sleep(.01)
            process.stdin.write(b"ci\nisrea"); time.sleep(.01)
            process.stdin.write(b"dy\n")
            output = b""
            end = time.monotonic() + 3
            while b"readyok\n" not in output and time.monotonic() < end:
                if select.select([process.stdout], [], [], .1)[0]:
                    output += os.read(process.stdout.fileno(), 4096)
            record["stdout"] = output.decode(errors="replace").splitlines()
            require(b"uciok\n" in output and b"readyok\n" in output, "fragmented commands did not complete")
            after = sorted(p.name for p in Path(f"/proc/{process.pid}/task").iterdir())
            require(after == ids, "startup TIDs changed after UCI")
            process.stdin.write(b"go infinite\n"); time.sleep(.025)
            during = sorted(p.name for p in Path(f"/proc/{process.pid}/task").iterdir())
            require(during == ids, "startup TIDs changed during search")
            process.stdin.write(b"stop\nquit\n"); process.stdin.close(); process.stdin = None
            stdout, stderr = process.communicate(timeout=3)
            require(stdout.count(b"bestmove ") == 1, "fragmented session: wrong bestmove count")
            require(process.returncode == 0 and not stderr, "fragmented session: abnormal exit")
            require(absent_group(process.pid), "fragmented session: surviving process group")
            record.update(passed=True, startup_tids=ids, after_uci_tids=after, during_search_tids=during,
                          returncode=process.returncode, stdout=(output + stdout).decode().splitlines())
        except subprocess.TimeoutExpired as error:
            record.update(timeout=True, partial_stdout=decoded(error.stdout), stderr=decoded(error.stderr))
            raise
        except Exception as error:
            record["error"] = str(error)
            raise
        finally:
            cleanup(process)
        report["source_unchanged_at_finish"] = all((source / name).read_bytes() == data for name, data in inputs.items())
        report["passed"] = True
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "tests": len(report["results"]), "report": str(out / "results.json")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
