#!/usr/bin/env python3
"""Interrupt the real finite A/P4 ELF factory at one controlled compiler leaf.

Hosted diagnostic only. The unchanged production Host owns the original
producer process. Its ordinary wait polling observes a named readiness file,
retains exact ancestor identities/pidfds, and sends TERM to that owned producer
group. No production grace, expected image, feature or verifier is changed.
The two intentionally failed builds never become artifact admissions.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import select
import shutil
import signal
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SELF = "engines/experiments/tcec-next/elf_profile_cancel.py"
PRODUCER = "engines/experiments/tcec-next/elf_profile.py"
PRODUCER_PIN = (64205, "b02e672300f38df3e78046a9fdb2ab6727c4172291840bc075cd2a1286ffab0a")
CLASS = "rove4k-elf-profile-cancellation-v1"
MODES = ("term", "ignore-term")
READY_SECONDS = 90
CLEANUP_SECONDS = 30
LEAF_GRACE_SECONDS = 3
MAX_FILE = 16 << 20
RECEIPTS = (
    ("build.json", "rove4k-full-profile-elf-v1", "fresh-profile"),
    ("fresh-profile/build.json", "rove4k-production-profile-v1", "fresh-profile-control"),
    ("fresh-profile/control/build.json", "tcec-full-C-v1", "fresh-selected-control"),
    ("fresh-profile/control/control/build.json", "tcec-full-C-v1", "control-A"),
)
_EXECUTING_CODE = sys._getframe().f_code


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(type(data) is bytes, "immutable diagnostic bytes required")
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def plan():
    return dict(family="A", profile="test-p4", modes=list(MODES),
        readiness_seconds=READY_SECONDS, cleanup_seconds=CLEANUP_SECONDS,
        leaf_TERM_grace_seconds=LEAF_GRACE_SECONDS, whole_work_seconds=600,
        outer_commands=2, engine_executed=False, TT_allocated=False,
        native_or_ELF_qualified=False, production_grace_changed=False)


def parse_stat(data, pid):
    """Parse only the named owned process; no command line or environment."""
    require(type(data) is bytes and len(data) <= 16384 and type(pid) is int and pid > 0,
            "bounded exact process stat required")
    try:
        prefix, rest = data.rsplit(b")", 1)
        require(int(prefix.split(b" (", 1)[0]) == pid, "process stat PID differs")
        fields = rest.split()
        result = dict(pid=pid, state=fields[0].decode("ascii"), ppid=int(fields[1]),
                      pgid=int(fields[2]), session=int(fields[3]), start_ticks=int(fields[19]))
        require(result["start_ticks"] > 0 and result["state"] in ("R", "S", "D", "T", "t", "Z", "X", "x", "I"),
                "process stat identity/state differs")
        return result
    except (IndexError, UnicodeError, TypeError) as error:
        raise ValueError("malformed owned process stat") from error


def validate_chain(chain, leader, readiness):
    require(type(chain) is list and len(chain) == 6 and type(leader) is int
            and chain[0]["pid"] == leader and len({row["pid"] for row in chain}) == 6,
            "exact A producer/profile/next/scope/compact/compiler chain required")
    for index, row in enumerate(chain):
        require(type(row) is dict and set(row) == {"pid", "state", "ppid", "pgid", "session", "start_ticks"}
                and all(type(row[key]) is int and row[key] > 0 for key in ("pid", "ppid", "pgid", "session", "start_ticks"))
                and row["state"] in ("R", "S", "D", "T", "t", "I"), "live typed ancestor identity required")
        if index:
            require(row["ppid"] == chain[index - 1]["pid"], "owned compiler ancestor relation differs")
        group = row["pid"] if index < 5 else chain[4]["pid"]
        require(row["pgid"] == group and row["session"] == group,
                "non-F8 separate owner / inherited compiler group topology differs")
    leaf = chain[-1]
    require(readiness.get("pid") == leaf["pid"] and readiness.get("start_ticks") == leaf["start_ticks"]
            and readiness.get("ppid") == leaf["ppid"] and readiness.get("pgid") == leaf["pgid"],
            "readiness does not identify the actual retained compiler leaf")
    return chain


def wrapper_source(python, compiler, readiness, mode):
    """Create a finite build-time compiler replacement; never a shipping tool."""
    require(mode in MODES and all(type(value) is str and PurePosixPath(value).is_absolute()
            and "\0" not in value and "\n" not in value and "\r" not in value
            for value in (python, compiler, readiness)), "explicit wrapper paths and finite mode required")
    require(not any(char.isspace() for char in python), "Python shebang path must contain no whitespace")
    text = '''#!@PYTHON@
import json, os, signal, sys
from pathlib import Path
compiler = @COMPILER@
ready = Path(@READY@)
mode = @MODE@
args = sys.argv[1:]
stdin_c = '-' in args and ('-xc' in args or any(args[i:i+2] == ['-x', 'c'] for i in range(len(args)-1)))
if not stdin_c:
    os.execv(compiler, [compiler, *args])
if mode == 'ignore-term':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
# Emergency backstop cannot explain an accepted <=30-second cancellation.
signal.alarm(120)
fields = Path('/proc/self/stat').read_bytes().rsplit(b')', 1)[1].split()
record = dict(mode=mode, pid=os.getpid(), ppid=os.getppid(), pgid=os.getpgrp(),
              start_ticks=int(fields[19]), SIGTERM_ignored=mode == 'ignore-term',
              stdin_C_blocked=True, stdin_consumed=False, command=args)
temporary = ready.with_suffix('.part')
with temporary.open('x') as output:
    json.dump(record, output, sort_keys=True)
os.replace(temporary, ready)
while True:
    signal.pause()
'''
    return text.replace("@PYTHON@", python).replace("@COMPILER@", repr(compiler)).replace(
        "@READY@", repr(readiness)).replace("@MODE@", repr(mode)).encode()


def validate_receipts(records):
    """Check the four actual owner receipts, including failed active commands."""
    require(type(records) is list and len(records) == len(RECEIPTS), "all four finite owner receipts required")
    for record, (name, kind, command) in zip(records, RECEIPTS):
        require(type(record) is dict and type(record.get("format")) is int and record["format"] == 1
                and record.get("class") == kind and record.get("complete") is False
                and record.get("host_cleanup") == {"unsettled_commands": 0, "errors": []},
                "interrupted owner is not incomplete and physically settled: " + name)
        rows = record.get("commands")
        require(type(rows) is list and len(rows) == 1 and rows[0].get("kind") == command,
                "first blocked C tool must be the sole active command: " + name)
        row = rows[0]
        require(row.get("started") is True and row.get("terminal") is True and row.get("reaped") is True
                and row.get("owned_group_absent") is True and row.get("forced_cleanup") is True
                and row.get("other_group_members_before_reap") == []
                and row.get("original_identity_retained_until_other_members_absent") is True
                and type(row.get("returncode")) is int and row["returncode"] != 0
                and type(row.get("pid")) is int and row["pid"] > 0 and row.get("pgid") == row["pid"],
                "interrupted command lost its original group/leader settlement: " + name)
    return True


def read_regular(path, maximum=MAX_FILE):
    require(path.is_file() and not any(item.is_symlink() for item in (path, *path.parents))
            and path.stat().st_size <= maximum, "bounded named regular diagnostic file required")
    return path.read_bytes()


def _proc(pid):
    return parse_stat(read_regular(Path("/proc") / str(pid) / "stat", 16384), pid)


def _pidfd_exited(descriptor):
    poll = select.poll()
    poll.register(descriptor, select.POLLIN)
    return bool(poll.poll(0))


def _capture_chain(leader, readiness, handles):
    chain = []
    candidates = []
    require(all(type(readiness.get(key)) is int and readiness[key] > 0
                for key in ("pid", "ppid", "pgid", "start_ticks")), "typed exact readiness identity required")
    pid = readiness["pid"]
    try:
        while True:
            require(len(chain) < 6, "compiler is not in the finite owned A ancestor chain")
            before = _proc(pid)
            if not chain:
                require(all(before[key] == readiness[key] for key in ("pid", "ppid", "pgid", "start_ticks")),
                        "readiness leaf exited or changed before capture")
            descriptor = os.pidfd_open(pid, 0)
            candidates.append((before, descriptor))
            after = _proc(pid)
            require(all(before[key] == after[key] for key in ("pid", "ppid", "pgid", "session", "start_ticks"))
                    and after["state"] not in ("Z", "X", "x") and not _pidfd_exited(descriptor),
                    "owned process identity changed during pidfd capture")
            chain.append(before)
            if pid == leader:
                break
            pid = before["ppid"]
        chain.reverse()
        validate_chain(chain, leader, readiness)
        # Only a fully authenticated descendant chain becomes an emergency
        # signalling capability. Failed/raced candidates are closed below.
        handles.extend(candidates)
        candidates = []
        return chain
    finally:
        for _, descriptor in candidates:
            os.close(descriptor)


def _load(name, path, data):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(data, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


def run(out, *, execute=False):
    require(execute is True, "explicit --execute required before source capture, output or factory invocation")
    require(sys.platform == "linux" and platform.machine() == "x86_64" and os.sysconf("SC_PAGE_SIZE") == 4096
            and callable(getattr(os, "pidfd_open", None)) and callable(getattr(signal, "pidfd_send_signal", None)),
            "Linux x86-64/4KiB and stable pidfd APIs required")
    import resource
    started = time.monotonic()
    source = read_regular(ROOT / SELF).replace(b"\r\n", b"\n")
    require(compile(source, __file__, "exec", dont_inherit=True) == _EXECUTING_CODE, "executing cancellation source differs")
    producer_source = read_regular(ROOT / PRODUCER).replace(b"\r\n", b"\n")
    require(pin(producer_source) == {"bytes": PRODUCER_PIN[0], "sha256": PRODUCER_PIN[1]}, "frozen ELF producer changed")
    producer = _load("elf_cancel_actual_producer", ROOT / PRODUCER, producer_source)
    files = producer.capture()
    utility = producer.load_bytes("elf_cancel_existing_utility", producer.UTILITY, files[producer.UTILITY])
    owner = producer.load_bytes("elf_cancel_existing_process_owner", producer.OWNER, files[producer.OWNER])
    require(owner.EXECUTING_BUILD == files[producer.OWNER], "existing process owner reread differs")
    real_compiler = shutil.which("cc")
    require(real_compiler is not None and Path(real_compiler).is_absolute(), "actual compiler path required before replacement")
    out = utility.new_output(out)
    out.mkdir(parents=True)
    for name, data in {**files, SELF: source}.items():
        producer.write(out / "inputs", name, data)
    report = dict(format=1, **{"class": CLASS}, complete=False, policy=plan(), commands=[], cases=[],
        artifact_directory=str(out), source={name: pin(data) for name, data in {**files, SELF: source}.items()},
        engine_executed=False, TT_allocated=False, native_or_ELF_qualified=False,
        scope="two intentionally interrupted real A/P4 factories; cancellation evidence only")

    def save():
        (out / "result.json").write_bytes(producer.json_bytes(report))

    save()
    handles = []
    host = None
    previous_limits = dict(owner.LIMITS)
    previous_chld = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    body_error = None

    class Host(owner.Host):
        active = None

        def exited(self, child):
            exited = owner.Host.exited(child)
            case = self.active
            if exited or case is None or child not in self.owned or case.get("observer_stopped"):
                return exited
            now = time.monotonic()
            if "TERM_requested_at" not in case and case["ready"].is_file():
                ready = json.loads(read_regular(case["ready"], 16384))
                require(ready.get("mode") == case["mode"] and ready.get("stdin_C_blocked") is True
                        and ready.get("stdin_consumed") is False
                        and ready.get("SIGTERM_ignored") is (case["mode"] == "ignore-term"), "controlled compiler readiness differs")
                case["chain"] = _capture_chain(child.pid, ready, handles)
                require(case["chain"][0]["ppid"] == os.getpid(), "producer leader is not this owner's child")
                status = read_regular(Path("/proc") / str(ready["pid"]) / "status", 65536)
                ignored = [line for line in status.splitlines() if line.startswith(b"SigIgn:")]
                require(len(ignored) == 1 and bool(int(ignored[0].split()[1], 16) & (1 << (signal.SIGTERM - 1)))
                        is (case["mode"] == "ignore-term"), "actual compiler TERM disposition differs")
                case["readiness"] = ready
                require(not owner.Host.exited(child), "original producer exited before intentional TERM")
                case["TERM_requested_at"] = time.monotonic()
                os.killpg(child.pid, signal.SIGTERM)
                save()
            if "TERM_requested_at" in case:
                elapsed = now - case["TERM_requested_at"]
                leaf = case["chain"][-1]
                leaf_fd = next(fd for row, fd in handles if (row["pid"], row["start_ticks"]) ==
                               (leaf["pid"], leaf["start_ticks"]))
                if _pidfd_exited(leaf_fd):
                    case.setdefault("leaf_exit_seconds", max(0, elapsed))
                elif elapsed >= 2.75 and case["mode"] == "ignore-term":
                    case["ignored_TERM_alive_after_seconds"] = elapsed
                if elapsed > CLEANUP_SECONDS:
                    case["observer_stopped"] = True
                    raise TimeoutError("real producer cancellation exceeded 30 seconds")
            elif now - case["started_at"] > READY_SECONDS:
                case["observer_stopped"] = True
                raise TimeoutError("first actual stdin C tool did not reach controlled readiness")
            return False

        def settle(self, child, row, force=False):
            # Emergency cleanup keeps the actual producer owner alive for its
            # bounded shutdown. A forced outer settlement never passes below.
            row["cooperative_termination_seconds"] = CLEANUP_SECONDS
            return super().settle(child, row, force)

    try:
        inherited = {"CPU": resource.getrlimit(resource.RLIMIT_CPU), "AS": resource.getrlimit(resource.RLIMIT_AS),
                     "FSIZE": resource.getrlimit(resource.RLIMIT_FSIZE)}
        limits = producer.limit_plan(inherited["CPU"], inherited["AS"], inherited["FSIZE"])
        resource.setrlimit(resource.RLIMIT_FSIZE, limits["FSIZE"])
        remaining = math.floor(600 - (time.monotonic() - started))
        require(remaining > 0, "whole diagnostic work budget expired")
        owner.LIMITS.update(aggregate_wall=remaining, per_command_wall=READY_SECONDS + CLEANUP_SECONDS,
            parent_AS=limits["parent_AS"], parent_CPU=limits["parent_CPU"][0], parent_CPU_hard=limits["parent_CPU"][1],
            child_AS=4 << 30, child_CPU=480, tool_output_bytes=MAX_FILE)
        host = Host(out, report, save)
        report["limits"] = dict(inherited=inherited, applied=limits, whole_work_seconds=600,
            cleanup_budget_seconds=CLEANUP_SECONDS, readiness_seconds=READY_SECONDS,
            per_command_wall_seconds=READY_SECONDS + CLEANUP_SECONDS)
        for mode in MODES:
            directory = out / mode
            wrappers = directory / "tools"
            wrappers.mkdir(parents=True)
            ready_path = directory / "compiler-ready.json"
            wrapper = wrapper_source(sys.executable, real_compiler, str(ready_path), mode)
            producer.write(wrappers, "cc", wrapper)
            (wrappers / "cc").chmod(0o755)
            case = dict(mode=mode, ready=ready_path, started_at=time.monotonic())
            host.active = case
            command = [sys.executable, "-I", "-B", str(ROOT / PRODUCER), "produce", "--entry", "A",
                       "--profile", "test-p4", "--out", str(directory / "produce"), "--execute"]
            previous_path = os.environ.get("PATH", "")
            expected_error = None
            try:
                os.environ["PATH"] = str(wrappers) + os.pathsep + previous_path
                try:
                    host.run(command, cwd=directory, kind="cancel-" + mode)
                except ValueError as error:
                    expected_error = str(error)
            finally:
                os.environ["PATH"] = previous_path
            row = report["commands"][-1]
            require(expected_error is not None and "TERM_requested_at" in case
                    and row.get("terminal") is True and row.get("reaped") is True and row.get("owned_group_absent") is True
                    and row.get("forced_cleanup") is False and type(row.get("returncode")) is int
                    and row["returncode"] != 0, "outer producer did not fail and settle naturally after intentional TERM")
            elapsed = time.monotonic() - case["TERM_requested_at"]
            case_keys = {(value["pid"], value["start_ticks"]) for value in case["chain"]}
            case_handles = [(identity, fd) for identity, fd in handles
                            if (identity["pid"], identity["start_ticks"]) in case_keys]
            require(elapsed <= CLEANUP_SECONDS and all(_pidfd_exited(fd) for _, fd in case_handles),
                    "captured original compiler/owner identities remain after producer settlement")
            if mode == "ignore-term":
                require(case.get("ignored_TERM_alive_after_seconds", 0) >= 2.75,
                        "ignored-TERM leaf was not observed through the three-second leaf grace")
            records, identities = [], {}
            for name, _, _ in RECEIPTS:
                raw = read_regular(directory / "produce" / name)
                records.append(json.loads(raw))
                identities[name] = pin(raw)
            validate_receipts(records)
            require([record["commands"][0]["pid"] for record in records] ==
                    [value["pid"] for value in case["chain"][1:5]], "actual owner receipts do not name the retained ancestor chain")
            report["cases"].append(dict(mode=mode, complete=True, readiness=case["readiness"],
                chain=case["chain"], all_original_pidfds_exit_observed=True,
                TERM_to_all_owners_settled_seconds=elapsed, leaf_exit_observation_seconds=case.get("leaf_exit_seconds"),
                ignored_TERM_alive_after_seconds=case.get("ignored_TERM_alive_after_seconds"), wrapper=pin(wrapper),
                owner_receipts=identities, expected_outer_error=expected_error,
                leaf_SIGKILL=("inferred from observed ignored TERM plus reviewed deepest Host TERM3/KILL3; nonchild exit signal unavailable"
                              if mode == "ignore-term" else "not required by this case")))
            host.active = None
            save()
        require(len(report["commands"]) == len(MODES) and len(report["cases"]) == len(MODES), "both finite cancellation cases required")
        require(producer.capture() == files and read_regular(ROOT / SELF).replace(b"\r\n", b"\n") == source,
                "current diagnostic/producer support source changed")
        report["source_rechecked"] = True
    except BaseException as error:
        body_error = error
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        if host is not None:
            host.active = None
        try:
            utility.finish_report(host, report, save, body_error)
        finally:
            # Stable pidfds refer only to the six captured descendants of our
            # original producer handle. This exceptional fallback never signals
            # a recycled PID/group and makes the diagnostic fail visibly.
            emergency = []
            for identity, descriptor in handles:
                try:
                    if not _pidfd_exited(descriptor):
                        signal.pidfd_send_signal(descriptor, signal.SIGKILL)
                        emergency.append(identity)
                except ProcessLookupError:
                    pass
            if emergency:
                deadline = time.monotonic() + 3
                while any(not _pidfd_exited(fd) for _, fd in handles) and time.monotonic() < deadline:
                    time.sleep(.025)
                report.update(complete=False, emergency_exact_pidfd_cleanup=emergency,
                    emergency_remaining=[identity for identity, fd in handles if not _pidfd_exited(fd)])
                report.setdefault("failure", {"type": "RuntimeError", "message": "exceptional exact-pidfd cleanup was required"})
            for _, descriptor in handles:
                os.close(descriptor)
            owner.LIMITS.clear()
            owner.LIMITS.update(previous_limits)
            signal.signal(signal.SIGCHLD, previous_chld)
            save()
    require(report.get("complete") is True, "cancellation diagnostic did not complete without emergency cleanup")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    result = run(args.out, execute=args.execute)
    print(json.dumps({"complete": result["complete"], "cases": len(result["cases"]),
                      "native_or_ELF_qualified": False}, sort_keys=True))


if __name__ == "__main__":
    main()
