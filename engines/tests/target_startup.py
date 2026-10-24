#!/usr/bin/env python3
"""Opt-in Linux startup checks for fixed large profiles; never submits a search.

The central builder deliberately does not execute these profiles. This separate
check admits one native file at a time using current host memory and explicit
limits, then observes the real process through /proc. An oversubscribed local
startup is evidence of software resource admission, not hardware scalability.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import resource
import selectors
import signal
import subprocess
import sys
import time


GIB = 1024 ** 3


def memory_available():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("Linux MemAvailable is unavailable")


def resource_admission(expected_threads, args):
    available = memory_available()
    result = {"mem_available_bytes": available, "cgroup_limits": [],
              "max_rss_bytes": args.max_rss_bytes,
              "required_available_bytes": max(args.minimum_available_bytes, 2 * args.max_rss_bytes),
              "rlimit_as_bytes": args.address_space_bytes, "rlimit_data_bytes": args.data_bytes,
              "rlimit_cpu_seconds": args.cpu_seconds,
              "inherited_stack_limit": resource.getrlimit(resource.RLIMIT_STACK),
              "inherited_nproc_limit": resource.getrlimit(resource.RLIMIT_NPROC)}
    result["applied_limits"] = {}
    for label, name, requested in (("address_space_bytes", resource.RLIMIT_AS, args.address_space_bytes),
                                    ("data_bytes", resource.RLIMIT_DATA, args.data_bytes),
                                    ("cpu_seconds", resource.RLIMIT_CPU, args.cpu_seconds)):
        _, hard = resource.getrlimit(name)
        result["applied_limits"][label] = requested if hard == resource.RLIM_INFINITY else min(requested, hard)
    # A cgroup can impose a lower ceiling than the VM. Inspect every applicable
    # v2 ancestor without assuming WSL exposes a particular cgroup mount.
    relative = next((line.split(":", 2)[2] for line in Path("/proc/self/cgroup").read_text().splitlines()
                     if line.startswith("0::")), None)
    for line in Path("/proc/self/mountinfo").read_text().splitlines():
        before, _, after = line.partition(" - ")
        if not after.startswith("cgroup2 ") or relative is None:
            continue
        fields = before.split()
        root, mount = PurePosixPath(fields[3]), Path(fields[4])
        try:
            suffix = PurePosixPath(relative).relative_to(root)
        except ValueError:
            continue
        if ".." in suffix.parts:
            continue
        directory = mount.joinpath(*suffix.parts)
        while directory == mount or mount in directory.parents:
            observation = {"path": str(directory)}
            for kind in ("memory", "pids"):
                maximum, current = directory / (kind + ".max"), directory / (kind + ".current")
                if maximum.exists() and current.exists():
                    cap, used = maximum.read_text().strip(), int(current.read_text())
                    observation[kind] = {"max": cap, "current": used}
                    if cap != "max":
                        headroom = max(0, int(cap) - used)
                        observation[kind]["headroom"] = headroom
                        if kind == "memory":
                            available = min(available, headroom)
                        elif headroom < expected_threads + 64:
                            result["rejection"] = "insufficient cgroup task headroom"
            result["cgroup_limits"].append(observation)
            if directory == mount:
                break
            directory = directory.parent
    nproc = resource.getrlimit(resource.RLIMIT_NPROC)[0]
    if nproc != resource.RLIM_INFINITY:
        owned_threads = 0
        for directory in Path("/proc").iterdir():
            try:
                if directory.name.isdigit() and directory.stat().st_uid == os.getuid():
                    for line in (directory / "status").read_text().splitlines():
                        if line.startswith("Threads:"):
                            owned_threads += int(line.split()[1])
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                pass
        result["uid_current_tasks"] = owned_threads
        if nproc - owned_threads < expected_threads + 64:
            result["rejection"] = "insufficient per-user task headroom"
    result["effective_available_bytes"] = available
    if available < result["required_available_bytes"]:
        result["rejection"] = "insufficient current available memory"
    return result


def process_state(pid):
    status = {}
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in ("Threads", "VmRSS", "VmHWM", "VmSize", "VmPeak", "VmData", "VmStk"):
            fields = value.split()
            status[key] = int(fields[0]) * (1024 if len(fields) > 1 and fields[1] == "kB" else 1)
    status["task_ids"] = sorted(int(p.name) for p in Path(f"/proc/{pid}/task").iterdir())
    return status


def set_child_limits(address_bytes, data_bytes, cpu_seconds):
    os.setsid()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    for name, requested in ((resource.RLIMIT_AS, address_bytes),
                            (resource.RLIMIT_DATA, data_bytes),
                            (resource.RLIMIT_CPU, cpu_seconds)):
        _, hard = resource.getrlimit(name)
        limit = requested if hard == resource.RLIM_INFINITY else min(requested, hard)
        resource.setrlimit(name, (limit, limit))


def group_exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


def end_owned_group(child):
    """Drain group ownership even if the leader has already exited."""
    needed = group_exists(child.pid)
    if needed:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        until = time.monotonic() + 2
        while group_exists(child.pid) and time.monotonic() < until:
            child.poll()  # Reap an exited direct child, including its zombie.
            time.sleep(0.01)
        if group_exists(child.pid):
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        child.wait(timeout=2)
    except subprocess.TimeoutExpired:
        return needed, False
    until = time.monotonic() + 1
    while group_exists(child.pid) and time.monotonic() < until:
        time.sleep(0.01)
    return needed, not group_exists(child.pid)


def check_one(path, expected_threads, mode, args):
    admission = resource_admission(expected_threads, args)
    record = {"termination": mode, "expected_total_threads": expected_threads,
              "admission": admission,
              "passed": False, "observations": []}
    if "rejection" in admission:
        record["error"] = admission["rejection"] + "; process not started"
        record["process_started"] = False
        return record
    started = time.monotonic()
    try:
        child = subprocess.Popen([str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, bufsize=0,
                                 preexec_fn=lambda: set_child_limits(args.address_space_bytes,
                                                                     args.data_bytes, args.cpu_seconds))
    except (OSError, subprocess.SubprocessError) as error:
        record.update({"process_started": False, "error": "launch rejected: " + str(error)})
        return record
    record["process_started"] = True
    record["pid"] = child.pid
    selector = None
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    peak_rss = 0
    peak_virtual = 0
    peak_threads = 0
    deadline = started + args.timeout_seconds

    def poll():
        nonlocal peak_rss, peak_virtual, peak_threads
        if time.monotonic() >= deadline:
            raise RuntimeError("bounded startup/protocol deadline exceeded")
        for key, _ in selector.select(0.01):
            block = os.read(key.fileobj.fileno(), 65536)
            if block:
                buffers[key.data].extend(block)
                if len(buffers[key.data]) > 262144:
                    raise RuntimeError("unexpectedly large startup output")
            else:
                selector.unregister(key.fileobj)
        if child.poll() is not None:
            raise RuntimeError(f"process exited before requested termination: {child.returncode}")
        state = process_state(child.pid)
        peak_rss = max(peak_rss, state.get("VmRSS", 0), state.get("VmHWM", 0))
        peak_virtual = max(peak_virtual, state.get("VmSize", 0), state.get("VmPeak", 0))
        peak_threads = max(peak_threads, state.get("Threads", 0), len(state["task_ids"]))
        if peak_rss > args.max_rss_bytes:
            raise RuntimeError("resident-memory admission ceiling exceeded")
        if state.get("Threads", 0) > expected_threads or len(state["task_ids"]) > expected_threads:
            raise RuntimeError("observed more tasks than the fixed profile permits")
        return state

    def observe(label, state):
        record["observations"].append({"phase": label,
                                       "elapsed_seconds": time.monotonic() - started,
                                       **state})

    def command(line, response):
        offset = len(buffers["stdout"])
        child.stdin.write(line.encode() + b"\n")
        child.stdin.flush()
        wanted = response.encode()
        while True:
            state = poll()
            if wanted in bytes(buffers["stdout"][offset:]).splitlines():
                return state

    try:
        # Enter cleanup ownership before metadata/descriptor setup can fail.
        record["proc_start_time_ticks"] = int(Path(f"/proc/{child.pid}/stat").read_text().rpartition(")")[2].split()[19])
        selector = selectors.DefaultSelector()
        for stream, name in ((child.stdout, "stdout"), (child.stderr, "stderr")):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        stable_since = None
        stable_ids = None
        while True:
            state = poll()
            actual_exe = Path(f"/proc/{child.pid}/exe").resolve()
            if actual_exe == path.resolve() and state.get("Threads") == expected_threads and len(state["task_ids"]) == expected_threads:
                if stable_ids != state["task_ids"]:
                    stable_ids = state["task_ids"]
                    stable_since = time.monotonic()
                if time.monotonic() - stable_since >= 0.1:
                    break
            else:
                stable_since = None
                stable_ids = None
        observe("before_first_command", state)
        state = command("uci", "uciok")
        observe("after_uci", state)
        state = command("isready", "readyok")
        observe("after_isready", state)
        state = command("isready", "readyok")
        observe("after_second_isready", state)
        lines = bytes(buffers["stdout"]).splitlines()
        if lines.count(b"uciok") != 1 or lines.count(b"readyok") != 2:
            raise RuntimeError("handshake did not produce exactly the requested responses")
        if any(item["task_ids"] != stable_ids or item.get("Threads") != expected_threads
               for item in record["observations"]):
            raise RuntimeError("fixed startup task identities did not persist")
        record["startup_ready_seconds"] = record["observations"][1]["elapsed_seconds"]
        shutdown_started = time.monotonic()
        if mode == "quit":
            child.stdin.write(b"quit\n")
            child.stdin.flush()
        child.stdin.close()
        child.stdin = None
        # Continue checking memory and collecting output while shutdown joins.
        while child.poll() is None:
            if time.monotonic() >= deadline:
                raise RuntimeError("bounded shutdown deadline exceeded")
            for key, _ in selector.select(0.01):
                block = os.read(key.fileobj.fileno(), 65536)
                if block:
                    buffers[key.data].extend(block)
                    if len(buffers[key.data]) > 262144:
                        raise RuntimeError("unexpectedly large shutdown output")
                else:
                    selector.unregister(key.fileobj)
            try:
                state = process_state(child.pid)
                peak_rss = max(peak_rss, state.get("VmHWM", 0), state.get("VmRSS", 0))
            except (FileNotFoundError, ProcessLookupError):
                pass
            if peak_rss > args.max_rss_bytes:
                raise RuntimeError("resident-memory admission ceiling exceeded during shutdown")
        record["returncode"] = child.returncode
        record["shutdown_seconds"] = time.monotonic() - shutdown_started
        if child.returncode != 0:
            raise RuntimeError(f"nonzero shutdown status: {child.returncode}")
        record["passed"] = True
    except Exception as error:
        record["error"] = str(error)
    finally:
        forced, group_gone = end_owned_group(child)
        record["forced_group_cleanup"] = forced
        record["owned_process_group_gone"] = group_gone
        if forced and record["passed"]:
            record.update({"passed": False, "error": "owned group outlived normal direct-child exit"})
        if not group_gone:
            record.update({"passed": False, "error": "owned process group remains after cleanup"})
        if selector is not None:
            drain_deadline = time.monotonic() + 1
            while selector.get_map() and time.monotonic() < drain_deadline:
                for key, _ in selector.select(0.01):
                    block = os.read(key.fileobj.fileno(), 65536)
                    if not block:
                        selector.unregister(key.fileobj)
                    else:
                        buffers[key.data].extend(block)
                        if len(buffers[key.data]) > 262144:
                            record.update({"passed": False, "error": "startup output exceeded bounded diagnostic capacity"})
                            del buffers[key.data][:-262144]
            if selector.get_map():
                record.update({"passed": False, "error": "startup pipes did not reach EOF after cleanup"})
            selector.close()
        # Final validation includes bytes written during normal shutdown.
        if record["passed"]:
            lines = bytes(buffers["stdout"]).splitlines()
            if lines.count(b"uciok") != 1 or lines.count(b"readyok") != 2:
                record.update({"passed": False, "error": "unexpected acknowledgement count after shutdown"})
            elif any(line.startswith(b"bestmove ") for line in lines):
                record.update({"passed": False, "error": "unexpected search result during startup-only check"})
        for stream in (child.stdin, child.stdout, child.stderr):
            if stream is not None:
                stream.close()
        record["wall_seconds"] = time.monotonic() - started
        record["observed_peak_rss_bytes"] = peak_rss
        record["observed_peak_virtual_bytes"] = peak_virtual
        record["observed_peak_threads"] = peak_threads
        record["stdout"] = buffers["stdout"].decode(errors="replace")
        record["stderr"] = buffers["stderr"].decode(errors="replace")
        record["physical_process_exit_confirmed"] = child.poll() is not None
        record["mem_available_after_bytes"] = memory_available()
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--forms", default="original", help="explicit native source forms to execute")
    parser.add_argument("--minimum-available-bytes", type=int, default=6 * GIB)
    parser.add_argument("--max-rss-bytes", type=int, default=3 * GIB)
    parser.add_argument("--address-space-bytes", type=int, default=8 * GIB)
    # Linux RLIMIT_DATA also constrains anonymous mmap reservations, including
    # pthread stacks. Keep virtual reservation separate from the RSS ceiling.
    parser.add_argument("--data-bytes", type=int, default=8 * GIB)
    parser.add_argument("--cpu-seconds", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=float, default=45)
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("Linux /proc and resource limits are required")
    if not args.out.is_absolute() or args.out.exists():
        parser.error("--out must be a new absolute external JSON path")
    repo = Path(__file__).resolve().parents[2]
    if args.out == repo or repo in args.out.parents:
        parser.error("--out must be outside the checkout")
    if min(args.minimum_available_bytes, args.max_rss_bytes, args.address_space_bytes,
           args.data_bytes, args.cpu_seconds, args.timeout_seconds) <= 0:
        parser.error("resource ceilings and deadlines must be positive")
    report = {"schema": 1, "purpose": "startup/protocol/thread identity/physical shutdown only",
              "search_submitted": False, "hardware_scalability_verified": False,
              "budget_scope": "one deadline includes initialization, 0.1s task stability observation, handshakes and shutdown",
              "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "logical_cpu_count": os.cpu_count(), "runs": [], "complete": False}
    args.out.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.out.write_text(json.dumps(report, indent=2) + "\n")

    for manifest_path in args.manifest:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        if not manifest.get("complete"):
            parser.error("build manifest is incomplete: " + str(manifest_path))
        expected = manifest["profile"]["expected_total_threads"]
        if expected != manifest["profile"]["search_workers"] + 1:
            parser.error("profile must count stdin plus all search workers")
        for engine in manifest["engines"]:
            if int(engine["configuration"]["ROVE_WORKERS"]) != manifest["profile"]["search_workers"]:
                parser.error("artifact worker configuration does not match its profile")
            for artifact in engine["artifacts"]:
                if artifact.get("format") != "native-elf" or artifact.get("source_form") not in args.forms.split(","):
                    continue
                path = Path(artifact["path"])
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                if actual != artifact["sha256"] or path.read_bytes()[:4] != b"\x7fELF":
                    raise RuntimeError("native artifact changed: " + str(path))
                for mode in ("quit", "eof"):
                    record = {"manifest": str(manifest_path), "profile_name": manifest["profile_name"],
                              "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                              "profile": manifest["profile"],
                              "engine": engine["id"], "path": str(path), "sha256": actual,
                              "source_form": artifact["source_form"],
                              "generation_config_sha256": engine.get("generation_config_sha256"),
                              "configuration": engine["configuration"],
                              **check_one(path, expected, mode, args)}
                    record["sha256_after_execution"] = hashlib.sha256(path.read_bytes()).hexdigest()
                    if record["sha256_after_execution"] != actual:
                        record.update({"passed": False, "error": "native file changed during execution"})
                    report["runs"].append(record)
                    save()
                    print(json.dumps({key: record.get(key) for key in ("profile_name", "engine", "termination", "passed", "startup_ready_seconds", "observed_peak_rss_bytes", "error")}), flush=True)
                    if not record["passed"]:
                        return 1
    report["complete"] = True
    report["passed"] = bool(report["runs"]) and all(r["passed"] for r in report["runs"])
    save()
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
