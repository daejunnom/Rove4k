#!/usr/bin/env python3
"""Bounded Linux x86-64 signal-runtime fixtures with a stub search.

Use --source-root pointing at a frozen build's sources/ directory. The actual
runtime, native clone assembly and header are copied and hash-pinned. Explicit
external transforms add syscall fault injection or a controlled startup gate.
This qualifies signal/runtime behavior only, not chess, real search stacks,
shipping file size, strength, performance, or 512-thread hardware scaling.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
NAMES = ("tiny.h", "runtime.c", "start.S", "image.ld")
PRIVATE = (1 << 9) | (1 << 11)
INHERITED = PRIVATE | (1 << 13)
STUB = r'''
#include "tiny.h"
static long raw(long n,long a,long b,long c,long d,long e,long f){
    register long r10 __asm__("r10")=d,r8 __asm__("r8")=e,r9 __asm__("r9")=f;long result;
    __asm__ volatile("syscall":"=a"(result):"a"(n),"D"(a),"S"(b),"d"(c),"r"(r10),"r"(r8),"r"(r9):"rcx","r11","memory");return result;
}
static void trace(const char *s){unsigned n=0;while(s[n])n++;raw(1,2,(long)s,n,0,0,0);}
void start(Board *p){memset(p,0,sizeof *p);p->s=1;p->e=-1;p->h=7;}
int gen(const Board *p,Move *m){(void)p;m[0]=MOVE(0,1,0);return 1;}
int make(const Board *p,Move m,Board *t){(void)m;*t=*p;t->s=-t->s;t->h++;return 1;}
void think(Worker *w,const Board *p){
    while(!atomic_load_explicit(&stopped,memory_order_relaxed)&&now()<deadline)w->nodes++;
    w->depth=1;w->score=(int)p->h;w->best=MOVE(0,1,0);
}
void fixture_gate(void){char c;long r;do{r=raw(0,100,(long)&c,1,0,0,0);}while(r==-4);if(r!=1)abort();}
/* Real early wake, then kernel-observed target disappearance. The production
 * notify subsequently receives a genuine ESRCH; no live-target ESRCH is faked. */
void fixture_late(int tid,int quitting){
    if(!quitting)return;
    long pid=raw(39,0,0,0,0,0,0),r=raw(234,pid,tid,10,0,0,0);
    if(r&&r!=-3)abort();
    uint64_t end=now()+500;long delay[2]={0,1000000};
    while((r=raw(234,pid,tid,0,0,0,0))!=-3){if(r||now()>=end)abort();raw(35,(long)delay,0,0,0,0,0);}
    trace("CONFIRMED kernel ESRCH\n");
}
#ifndef FAULT_NR
#define FAULT_NR -1
#endif
#ifndef FAULT_ARG
#define FAULT_ARG -1
#endif
#ifndef FAULT_ERROR
#define FAULT_ERROR 22
#endif
int fixture_fault(long n,long a,long b,long c,long d,long e,long f,long *result){
    (void)b;(void)d;(void)e;(void)f;
    static atomic_int fired;
    int match=n==FAULT_NR&&(FAULT_ARG<0||(n==13?a:c)==FAULT_ARG);
    if(match&&!atomic_exchange(&fired,1)){trace("INJECT selected syscall errno\n");*result=-FAULT_ERROR;return 1;}return 0;
}
#ifdef FAIL_AT
extern long real_spawn(void (*)(void *),void *,void *,int *);
long spawn(void (*fn)(void *),void *arg,void *stack,int *tid){
    static int calls;if(calls++==FAIL_AT){trace("INJECT clone EAGAIN\n");return -11;}return real_spawn(fn,arg,stack,tid);
}
#endif
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def decode(data):
    return data.decode(errors="replace") if isinstance(data, bytes) else data or ""


class Bounds:
    def __init__(self, seconds):
        self.end = time.monotonic() + seconds

    def deadline(self, seconds):
        require(time.monotonic() < self.end, "aggregate deadline exceeded")
        return min(self.end, time.monotonic() + seconds)

    def remaining(self, end):
        left = min(end, self.end) - time.monotonic()
        require(left > 0, "aggregate or per-command deadline exceeded")
        return left


class Client:
    def __init__(self, binary, bounds, pass_fds=()):
        self.bounds = bounds
        self.process = subprocess.Popen([str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, pass_fds=pass_fds, start_new_session=True)
        self.stdout, self.stderr, self.buffer, self.lines = b"", b"", b"", []
        self.streams = {self.process.stdout.fileno(): "stdout", self.process.stderr.fileno(): "stderr"}
        for fd in (*self.streams, self.process.stdin.fileno()):
            os.set_blocking(fd, False)

    def pump(self, end, writable=False):
        read, write, _ = select.select(list(self.streams), [self.process.stdin.fileno()] if writable else [], [],
                                       min(.02, self.bounds.remaining(end)))
        for fd in read:
            data = os.read(fd, 4096)
            if not data:
                del self.streams[fd]
            elif self.streams[fd] == "stderr":
                self.stderr += data
            else:
                self.stdout += data; self.buffer += data
                while b"\n" in self.buffer:
                    line, self.buffer = self.buffer.split(b"\n", 1)
                    self.lines.append(line.decode(errors="replace"))
            require(len(self.stdout) + len(self.stderr) <= 1024 * 1024, "fixture output exceeded 1 MiB")
        return bool(write)

    def send(self, data, seconds=3):
        end = self.bounds.deadline(seconds)
        while data:
            if self.pump(end, writable=True):
                count = os.write(self.process.stdin.fileno(), data[:4096])
                data = data[count:]

    def until(self, expected, seconds=3):
        end = self.bounds.deadline(seconds)
        while True:
            if expected in self.lines:
                at = self.lines.index(expected)
                result, self.lines = self.lines[:at + 1], self.lines[at + 1:]
                return result
            require(self.process.poll() is None, f"fixture exited before {expected}: {self.stderr!r}")
            self.pump(end)

    def quiet(self, seconds):
        end = self.bounds.deadline(seconds)
        while time.monotonic() < end:
            self.pump(end)

    def finish(self, seconds=4):
        if not self.process.stdin.closed:
            self.process.stdin.close()
        end = self.bounds.deadline(seconds)
        while self.process.poll() is None or self.streams:
            self.pump(end)
        self.process.wait(timeout=self.bounds.remaining(end))
        try:
            os.killpg(self.process.pid, 0)
        except ProcessLookupError:
            pass
        else:
            raise RuntimeError("fixture left a surviving process group")

    def cleanup(self):
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.process.wait(timeout=2)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()


def status(pid):
    result = {}
    for path in sorted(Path(f"/proc/{pid}/task").iterdir()):
        fields = dict(line.split(":", 1) for line in (path / "status").read_text().splitlines() if ":" in line)
        stat = (path / "stat").read_text().rsplit(") ", 1)[1].split()
        result[int(path.name)] = {name: int(fields[name], 16) for name in ("SigBlk", "SigIgn", "SigCgt", "SigPnd", "ShdPnd")}
        result[int(path.name)]["cpu_ticks"] = int(stat[11]) + int(stat[12])
    return result


def transform_once(text, old, new):
    require(text.count(old) == 1, "fixture transform admission failed: " + old[:80])
    return text.replace(old, new)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--aggregate-seconds", type=float, default=60)
    args = parser.parse_args()
    out, source = args.out.resolve(), args.source_root.resolve()
    if not args.out.is_absolute() or out.exists() or source == out or source in out.parents:
        parser.error("--out must be a new absolute directory outside source-root")
    if any((p / ".git").exists() for p in (out, *out.parents)):
        parser.error("--out must be outside Git checkouts")
    if os.name != "posix" or os.uname().machine != "x86_64" or not Path("/proc/self/task").is_dir():
        parser.error("Linux x86-64 and /proc are required")
    if not 10 <= args.aggregate_seconds <= 180:
        parser.error("aggregate-seconds must be 10..180")
    out.mkdir(parents=True)
    # Reserve bounded teardown time inside the requested aggregate budget.
    bounds = Bounds(args.aggregate_seconds - 2)
    report = {"scope": "Stub-search signal runtime only; no chess/search-stack/size/strength/scaling qualification.",
              "source_root": str(source), "harness_sha256": sha(Path(__file__).read_bytes()),
              "aggregate_seconds": args.aggregate_seconds, "builds": [], "cases": [], "passed": False}
    started = time.monotonic()
    active = None
    try:
        inputs = {name: (source / name).read_bytes() for name in NAMES}
        report["source_sha256"] = {name: sha(data) for name, data in inputs.items()}
        manifest = source.parent / "build.json"
        if manifest.is_file():
            manifest_bytes = manifest.read_bytes()
            expected = json.loads(manifest_bytes)["source_sha256"]
            require(all(sha(data) == expected[name] for name, data in inputs.items()), "frozen build source hash mismatch")
            report["build_manifest_sha256"] = sha(manifest_bytes)
            (out / "build-input.json").write_bytes(manifest_bytes)
        (out / "test_signals.py").write_bytes(Path(__file__).read_bytes())
        recipe = out / "sources"
        recipe.mkdir()
        for name, data in inputs.items():
            (recipe / name).write_bytes(data)
        (recipe / "stub.c").write_text(STUB)
        report["stub_sha256"] = sha(STUB.encode())
        flags = ["-Oz", "-flto", "-std=c11", "-nostdlib", "-static", "-no-pie", "-fno-pie", "-fno-pic",
                 "-fno-stack-protector", "-fno-builtin", "-fno-asynchronous-unwind-tables", "-fno-unwind-tables",
                 "-fno-ident", "-fcf-protection=none", "-ffunction-sections", "-fdata-sections",
                 "-Wl,--gc-sections,--build-id=none,-s,-z,noexecstack", "-DWORKERS=2", "-DTT_BITS=18", "-DDEV=0"]
        report["compiler"] = subprocess.check_output([args.cc, "--version"], text=True,
                                                     timeout=bounds.remaining(bounds.deadline(5))).splitlines()[0]

        def build(name, gate=False, late=False, clone=None, fault=None):
            directory = out / name
            directory.mkdir()
            runtime, assembly = inputs["runtime.c"].decode(), inputs["start.S"].decode()
            transforms, extra = [], []
            if gate:
                runtime = "void fixture_gate(void);\n" + transform_once(runtime,
                    "atomic_fetch_add_explicit(&ready,1,memory_order_release);notify(process_id,12);",
                    "atomic_fetch_add_explicit(&ready,1,memory_order_release);notify(process_id,12);fixture_gate();")
                transforms.append("block each worker on fd100 after ready publication, before first work-loop wait")
            if late:
                runtime = "void fixture_late(int,int);\n" + transform_once(runtime, "if(tid)notify(tid,10);",
                    "if(tid){fixture_late(tid,atomic_load_explicit(&quitting,memory_order_relaxed));notify(tid,10);}")
                transforms.append("during shutdown, raw-wake sampled TID and observe kernel ESRCH before production notify")
            if clone is not None:
                assembly = assembly.replace("spawn", "real_spawn")
                extra += [f"-DFAIL_AT={clone}"]
                transforms.append(f"interpose spawn; first {clone} clones are genuine, next returns -EAGAIN")
            if fault:
                runtime = "int fixture_fault(long,long,long,long,long,long,long,long *);\n" + transform_once(runtime,
                    "static long system_call(long n,long a,long b,long c,long d,long e,long f){",
                    "static long system_call(long n,long a,long b,long c,long d,long e,long f){long injected;if(fixture_fault(n,a,b,c,d,e,f,&injected))return injected;")
                extra += [f"-DFAULT_NR={fault[0]}", f"-DFAULT_ARG={fault[1]}", f"-DFAULT_ERROR={fault[2]}"]
                transforms.append(f"one traced synthetic raw errno {fault[2]} at syscall {fault[0]}, argument selector {fault[1]}")
            (directory / "runtime.c").write_text(runtime)
            (directory / "start.S").write_text(assembly)
            binary = directory / "x"
            command = [args.cc, *flags, *extra, "-I", str(recipe), str(directory / "runtime.c"), str(recipe / "stub.c"),
                       str(directory / "start.S"), "-Wl,-T," + str(recipe / "image.ld"), "-o", str(binary)]
            record = {"id": name, "transforms": transforms, "command": command,
                      "runtime_sha256": sha(runtime.encode()), "assembly_sha256": sha(assembly.encode())}
            report["builds"].append(record)
            try:
                result = subprocess.run(command, capture_output=True, timeout=bounds.remaining(bounds.deadline(15)))
            except subprocess.TimeoutExpired as error:
                record.update(timeout=True, stdout=decode(error.stdout), stderr=decode(error.stderr))
                raise
            record.update(returncode=result.returncode, stdout=decode(result.stdout), stderr=decode(result.stderr))
            require(result.returncode == 0, "fixture compilation failed: " + name)
            record["binary_sha256"] = sha(binary.read_bytes())
            return binary

        def case(name, binary, payload=b"", code=0, best=0, trace=None):
            nonlocal active
            record = {"case": name, "passed": False, "binary_sha256": sha(binary.read_bytes()),
                      "stdin_sha256": sha(payload), "expected_exit": code, "expected_bestmoves": best}
            report["cases"].append(record)
            active = Client(binary, bounds)
            try:
                if payload:
                    active.send(payload)
                # Keep stdin open briefly so an idle wait fault cannot be
                # bypassed by immediate EOF/shutdown before workers wait.
                active.quiet(.02)
                active.finish()
                record.update(returncode=active.process.returncode, stdout=decode(active.stdout), stderr=decode(active.stderr))
                require(active.process.returncode == code, f"{name}: expected exit {code}")
                require(decode(active.stdout).count("bestmove ") == best, f"{name}: duplicate or missing job completion")
                if trace:
                    require(trace in decode(active.stderr), f"{name}: injection was not observed")
                else:
                    require(not active.stderr, f"{name}: unexpected stderr")
                record.update(passed=True, owned_group_gone=True)
            finally:
                record.update(returncode=active.process.poll(), stdout=decode(active.stdout), stderr=decode(active.stderr))
                active.cleanup(); active = None

        base = build("base")
        case("256-rapid-generations", base, b"uci\n" + b"go infinite\nstop\n" * 256 + b"isready\nquit\n", best=256)
        gate = build("ready-gate", gate=True)
        record = {"case": "inherited-masks-private-pending-stale-notifications", "passed": False,
                  "binary_sha256": sha(gate.read_bytes())}
        report["cases"].append(record)
        read_fd, write_fd = os.pipe()
        os.dup2(read_fd, 100)
        if read_fd != 100:
            os.close(read_fd)
        old_handlers = {s: signal.getsignal(s) for s in (signal.SIGUSR1, signal.SIGUSR2)}
        old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGUSR1, signal.SIGUSR2, signal.SIGALRM})
        try:
            for s in old_handlers:
                signal.signal(s, signal.SIG_IGN)
            active = Client(gate, bounds, (100,))
        finally:
            for s, handler in old_handlers.items():
                signal.signal(s, handler)
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
            os.close(100)
        try:
            active.send(b"uci\nisready\n"); active.until("uciok"); active.until("readyok")
            initial = status(active.process.pid)
            require(len(initial) == 3, "startup did not create exactly three TIDs")
            require(all(v["SigBlk"] & INHERITED == INHERITED and not (v["SigIgn"] | v["SigCgt"]) & PRIVATE
                        for v in initial.values()), "inherited mask/IGN normalization failed")
            active.send(b"go infinite\n")
            libc = ctypes.CDLL(None, use_errno=True)
            for tid in initial:
                for number in (10, 12):
                    require(libc.syscall(234, active.process.pid, tid, number) == 0, "fixture tgkill failed")
            pending = status(active.process.pid)
            require(all(v["SigPnd"] & PRIVATE == PRIVATE and not v["ShdPnd"] & PRIVATE for v in pending.values()),
                    "per-thread private pending bits were not observed before first worker wait")
            os.write(write_fd, b"xx"); os.close(write_fd); write_fd = None
            active.send(b"stop\n"); active.until("bestmove a1b1")
            # Pending wrong-target USR1 on main and USR2 on workers remain harmless.
            active.send(b"go infinite\nstop\ngo wtime 30 btime 30\n")
            active.until("bestmove a1b1"); active.until("bestmove a1b1")
            active.send(b"isready\n"); active.until("readyok")
            before = status(active.process.pid)
            active.quiet(.2)
            after = status(active.process.pid)
            require(set(before) == set(after) == set(initial), "startup TIDs changed")
            idle_ticks = sum(v["cpu_ticks"] for v in after.values()) - sum(v["cpu_ticks"] for v in before.values())
            require(idle_ticks <= 2, f"idle runtime spun: {idle_ticks} CPU ticks")
            require(not any(line.startswith("bestmove ") for line in active.lines), "stale signal executed a duplicate job")
            active.send(b"quit\n"); active.finish()
            require(active.process.returncode == 0 and not active.stderr and active.stdout.count(b"bestmove ") == 3,
                    "stale-signal session failed completion/shutdown")
            record.update(passed=True, configured_inherited_ignore=[10, 12], configured_inherited_block=[10, 12, 14],
                          initial=initial, pending_before_first_wait=pending, idle_cpu_ticks=idle_ticks,
                          idle_window_seconds=.2, returncode=active.process.returncode, owned_group_gone=True)
        finally:
            if write_fd is not None:
                os.close(write_fd)
            record.update(stdout=decode(active.stdout), stderr=decode(active.stderr))
            active.cleanup(); active = None

        for n in (0, 1):
            binary = build(f"clone-fail-{n}", clone=n)
            case(f"clone-failure-after-{n}", binary, code=2, trace="INJECT clone EAGAIN")
        faults = [("mask-error", 14, -1, 22, b"", 2), ("action-usr1-error", 13, 10, 22, b"", 2),
                  ("action-usr2-error", 13, 12, 22, b"", 2), ("wait-error", 128, -1, 22, b"", 2),
                  ("notify-ready-error", 234, 12, 1, b"", 2),
                  ("notify-work-error", 234, 10, 1, b"go infinite\n", 2),
                  ("wait-eintr-retry", 128, -1, 4, b"uci\nisready\n", 0),
                  ("notify-eintr-retry", 234, -1, 4, b"uci\nisready\nquit\n", 0)]
        for name, nr, arg, error, payload, code in faults:
            binary = build(name, fault=(nr, arg, error))
            case(name, binary, payload, code=code, trace="INJECT selected syscall errno")
        late = build("late-shutdown", late=True)
        # Give workers a completed handshake before quit so shutdown samples
        # live idle threads; the transformed hook then proves kernel ESRCH.
        active = Client(late, bounds)
        record = {"case": "genuine-late-shutdown-esrch", "passed": False, "binary_sha256": sha(late.read_bytes())}
        report["cases"].append(record)
        try:
            active.send(b"uci\nisready\n"); active.until("uciok"); active.until("readyok")
            active.quiet(.02); active.send(b"quit\n"); active.finish()
            require(active.process.returncode == 0 and b"CONFIRMED kernel ESRCH" in active.stderr,
                    "genuine ESRCH shutdown fixture failed")
            record.update(passed=True, returncode=active.process.returncode, owned_group_gone=True)
        finally:
            record.update(stdout=decode(active.stdout), stderr=decode(active.stderr))
            active.cleanup(); active = None
        report["source_unchanged_at_finish"] = all((source / name).read_bytes() == data for name, data in inputs.items())
        require(report["source_unchanged_at_finish"], "frozen source changed")
        report["passed"] = True
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        if active is not None:
            try:
                active.cleanup()
            except Exception as error:
                report["cleanup_error"] = str(error)
        report["elapsed_seconds"] = time.monotonic() - started
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "cases": len(report["cases"]), "report": str(out / "results.json")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
