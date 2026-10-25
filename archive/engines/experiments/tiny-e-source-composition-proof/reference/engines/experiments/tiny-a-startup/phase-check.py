#!/usr/bin/env python3
"""Five controlled startup-phase witnesses for one unchanged production source.

The C translation unit interposes calls and schedules startup gates; it never
edits the included candidate. No search, old-control execution, sanitizer,
join-failure injection, size trial, or timing/performance claim is included.
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
import threading
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CANDIDATE = "71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734"
CONTROL = "79284c72b64d087aa3127ea65b461aef8c7776355ea1c4ab9b2f81e59b4b48ed"
CASES = ("success-early", "success-late", "fail-0", "fail-1-early", "fail-1-late")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def lf(data):
    result = data.replace(b"\r\n", b"\n")
    require(b"\r" not in result, "unexpected lone CR")
    return result


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def matching(events, name, index=None):
    return [event for event in events if event["event"] == name
            and (index is None or event.get("index") == index)]


def only(events, name, index=None):
    result = matching(events, name, index)
    require(len(result) == 1, "expected one " + name + " at " + str(index))
    return result[0]


def assert_case(name, code, stdout, events):
    require(events and all(isinstance(event, dict) and "event" in event and "seq" in event for event in events),
            "missing structured events")
    sequence = [event["seq"] for event in events]
    require(sequence == sorted(set(sequence)), "event sequence is not strictly increasing")
    mode = only(events, "mode")
    require(mode["mode"] == name and mode["source_sha256"] == CANDIDATE,
            "diagnostic mode/source binding differs")
    require(not matching(events, "contract_violation"), "diagnostic reported a contract violation")
    success = name.startswith("success")
    created = 2 if success else 0 if name == "fail-0" else 1
    require(code == (0 if success else 2), "production returned an unexpected status")
    require(not any(line.startswith("bestmove") for line in stdout), "startup emitted an unsolicited result")
    require(stdout == (["uciok", "readyok"] if success else []), "unexpected production protocol output")
    attempts = matching(events, "create_attempt")
    returns = matching(events, "create_return")
    require([event["index"] for event in attempts] == list(range(2 if success else created + 1)),
            "pthread_create attempt prefix differs")
    require(len(returns) == len(attempts), "creation did not return for every attempted index")
    successful = [event for event in returns if event["rc"] == 0]
    failed = [event for event in returns if event["rc"] != 0]
    require([event["index"] for event in successful] == list(range(created)), "successful create prefix differs")
    require(not failed if success else len(failed) == 1 and failed[0]["index"] == created,
            "requested creation failure missing")
    entered = matching(events, "worker_entry")
    exited = matching(events, "worker_exit")
    joins = matching(events, "join_return")
    arrivals = matching(events, "worker_arrival")
    for label, records in (("entry", entered), ("exit", exited), ("arrival", arrivals), ("join", joins)):
        require(sorted(event["index"] for event in records) == list(range(created)),
                "actual worker " + label + " counts differ from created prefix")
    require(sorted(event["index"] for event in matching(events, "join_enter")) == list(range(created)),
            "join attempts differ from the created prefix")
    require(all(event["rc"] == 0 for event in joins), "real join did not succeed")
    targets = {event["index"]: event["target_thread"] for event in successful}
    require(len(set(targets.values())) == created, "actual created pthread identities are not distinct")
    for index in range(created):
        entry = only(events, "worker_entry", index)
        exit_event = only(events, "worker_exit", index)
        joined = only(events, "join_return", index)
        joining = only(events, "join_enter", index)
        require(entry["thread"] == exit_event["thread"] == targets[index]
                == joining["target_thread"] == joined["target_thread"],
                "entry/exit/join targets differ from actual created pthread")
        acquired = only(events, "worker_mutex_acquired", index)
        arrival = only(events, "worker_arrival", index)
        require(entry["seq"] < acquired["seq"] < arrival["seq"] < exit_event["seq"] < joined["seq"],
                "worker phase order is invalid")
    ordered_arrivals = sorted(arrivals, key=lambda event: event["seq"])
    require([event["pending"] for event in ordered_arrivals] == list(range(1, 1 - created, -1)),
            "startup pending decrements do not match exact arrival count")
    free_event = only(events, "tt_free")
    returned = only(events, "production_return")
    require(free_event["created"] == free_event["joined"] == free_event["exited"] == created,
            "TT freed before exact successful join/exit count")
    require(all(event["seq"] < free_event["seq"] for event in joins + exited), "TT free preceded real joins/exits")
    require(free_event["seq"] < returned["seq"] and returned["status"] == code, "production return trace differs")
    require(returned["violations"] == 0 and returned["tt_frees"] == 1 and returned["arrivals"] == created,
            "diagnostic counter/TT-free contract differs")
    require(all(returned[key] == created for key in ("created", "joined", "entered", "exited")),
            "production return lost a worker lifetime")
    shutdown = only(events, "shutdown_broadcast")
    require(shutdown["quitting"] == 1 and shutdown["rc"] == 0, "shutdown publication failed")
    startup_enter = matching(events, "main_startup_wait_enter")
    startup_return = matching(events, "main_startup_wait_return")
    first_input = matching(events, "first_input")
    if success:
        require(len(startup_enter) == len(startup_return) == len(first_input) == 1,
                "successful startup did not pass exactly one completion wait/input boundary")
        require(startup_enter[0]["stopped"] == startup_return[0]["stopped"] == first_input[0]["stopped"] == 1,
                "candidate startup did not physically observe stopped==1 before first GO")
        require(startup_return[0]["pending"] == first_input[0]["pending"] == 0,
                "protocol input admitted before all startup arrivals")
        require(startup_enter[0]["seq"] < startup_return[0]["seq"] < first_input[0]["seq"] < shutdown["seq"],
                "startup/input/shutdown order differs")
    else:
        require(not startup_enter and not startup_return and not first_input,
                "partial creation failure entered the nonexistent-worker barrier or read input")
        require(returned["input_calls"] == 0, "failed startup consumed protocol input")
    if name == "success-early":
        require(max(event["seq"] for event in arrivals) < startup_enter[0]["seq"],
                "early mode did not finish every real arrival before main startup wait")
        require(startup_enter[0]["pending"] == 0 and not matching(events, "main_finished_wait_enter"),
                "early completion was not consumed as a persistent zero predicate")
    elif name == "success-late":
        waits = matching(events, "main_finished_wait_enter")
        require(waits and waits[0]["pending"] > 0 and waits[0]["stopped"] == 1,
                "late mode did not observe the main wait predicate")
        require(waits[0]["seq"] < only(events, "worker_entry", 1)["seq"],
                "late worker entered production before the main wait predicate")
        require(waits[0]["seq"] < only(events, "worker_mutex_acquired", 1)["seq"]
                < only(events, "worker_arrival", 1)["seq"] < startup_return[0]["seq"],
                "late arrival did not complete after the real completion-wait release")
        require(all(event["pending"] > 0 for event in waits), "completion wait entered on zero predicate")
    elif name == "fail-1-early":
        require(only(events, "worker_arrival", 0)["seq"] < failed[0]["seq"],
                "first worker did not arrive before second creation failed")
        require(matching(events, "worker_command_wait_enter", 0), "early worker never reached its real idle wait")
    elif name == "fail-1-late":
        require(shutdown["seq"] < only(events, "worker_entry", 0)["seq"],
                "late worker entered production before persistent quitting publication")
        require(only(events, "worker_arrival", 0)["quitting"] == 1,
                "late arrival did not observe quitting after mutex acquisition")
        require(not matching(events, "worker_command_wait_enter"), "late failure worker waited for a lost shutdown broadcast")
    return {"created": created, "actual_created_pthreads": targets,
            "joined_created_pthreads_exactly": True, "entered": len(entered), "exited": len(exited),
            "startup_stopped_observed": 1 if success else None,
            "protocol_admitted_after_all_arrivals": success,
            "join_success_assumption": "all injected cases use real successful pthread_join; join-failure behavior is excluded"}


def run_case(program, name, out):
    directory = out / name
    directory.mkdir()
    command = [str(program), "--mode", name]
    result = {"name": name, "passed": False, "command": command, "forced_cleanup": [],
              "timeout_seconds": 5, "observed_children": []}
    process = None
    monitor = None
    sampling = threading.Event()
    child_starts = {}
    stdout = stderr = b""
    started = time.monotonic()
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        result["pid"] = process.pid
        def sample():
            while not sampling.is_set() and process.poll() is None:
                try:
                    children = (Path("/proc") / str(process.pid) / "task" / str(process.pid) / "children").read_text().split()
                    for child in children:
                        fields = (Path("/proc") / child / "stat").read_text().rpartition(") ")[2].split()
                        child_starts[int(child)] = fields[19]
                except OSError:
                    pass
                sampling.wait(0.001)
        monitor = threading.Thread(target=sample, daemon=True)
        monitor.start()
        try:
            stdout, stderr = process.communicate(b"uci\nisready\nquit\n", timeout=5)
        except subprocess.TimeoutExpired:
            result["error"] = "startup schedule timed out; outcome unknown before forced cleanup"
            result["forced_cleanup"].append({"action": "SIGKILL-owned-process-group", "pid": process.pid})
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=2)
            raise TimeoutError(result["error"])
        result["returncode"] = process.returncode
        require(len(stdout) + len(stderr) <= 2 * 1024 * 1024, "diagnostic output bound exceeded")
        events = [json.loads(line) for line in stderr.decode().splitlines() if line]
        lines = stdout.decode().splitlines()
        result.update(events=events, stdout=lines)
        result["assertions"] = assert_case(name, process.returncode, lines, events)
        require(not (Path("/proc") / str(process.pid)).exists(), "waited diagnostic PID remains")
        require(not result["forced_cleanup"], "forced cleanup cannot be a passing witness")
        result["passed"] = True
    except Exception as error:
        result["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if process is not None and process.poll() is None:
            result["forced_cleanup"].append({"action": "SIGKILL-owned-process-group", "pid": process.pid})
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=2)
        sampling.set()
        if monitor is not None:
            monitor.join(timeout=0.1)
        alive = []
        for pid, birth in child_starts.items():
            try:
                fields = (Path("/proc") / str(pid) / "stat").read_text().rpartition(") ")[2].split()
                if fields[19] == birth and fields[0] != "Z":
                    alive.append(pid)
            except OSError:
                pass
        result.update(observed_children=sorted(child_starts), surviving_observed_children=alive,
                      elapsed_seconds=time.monotonic() - started)
        if alive or result["forced_cleanup"]:
            result["passed"] = False
        if process is not None:
            result["returncode"] = process.returncode
        (directory / "stdout.txt").write_bytes(stdout)
        (directory / "stderr.jsonl").write_bytes(stderr)
        save(directory / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=Path("/home/stemxstudio/rove4k-tiny-a-startup-first-20261020/candidate/engine.c"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or out == REPO or REPO in out.parents:
        parser.error("new absolute external output required")
    if not args.candidate.is_absolute() or not args.candidate.is_file():
        parser.error("absolute immutable candidate source required")
    out.mkdir(parents=True)
    frozen = out / "frozen"
    frozen.mkdir()
    report = {"format": 1, "passed": False, "cases": [], "source_sha256": {},
        "scope": "five controlled startup-only schedules/faults; unchanged included production candidate",
        "profile": {"workers": 2, "tt_bits": 18, "DEV": 0},
        "excluded": ["join-failure injection or guaranteed cleanup after join failure", "old-control compilation",
            "search/board tests", "runtime scaling", "sanitizer/race-detector proof", "performance", "variant sweep"]}
    save(out / "results.json", report)
    try:
        for name, path in (("phase-check.py", Path(__file__)), ("phase-contract.c", HERE / "phase-contract.c"),
                           ("transform.py", HERE / "transform.py"), ("control-engine.c", HERE / "control/engine.c")):
            raw = path.read_bytes()
            (frozen / ("raw-" + name)).write_bytes(raw)
            data = lf(raw)
            (frozen / name).write_bytes(data)
            report["source_sha256"][name] = {"raw": sha(raw), "LF": sha(data)}
        candidate = args.candidate.read_bytes()
        require(sha(candidate) == CANDIDATE, "immutable candidate source changed")
        require(sha((frozen / "control-engine.c").read_bytes()) == CONTROL, "control source changed")
        transform = module("startup_phase_frozen_transform", frozen / "transform.py")
        require(transform.transform((frozen / "control-engine.c").read_bytes()) == candidate,
                "candidate is not the exact unchanged production transform")
        (frozen / "candidate.c").write_bytes(candidate)
        report.update(candidate_source_sha256=sha(candidate), production_transform_exact=True,
                      diagnostic_interposition="macro call wrappers and separate scheduling gates; candidate text is never edited")
        command = ["cc", "-std=c11", "-Os", "-pthread", "-DDEV=0", "-DWORKERS=2", "-DTT_BITS=18",
                   '-DPRODUCTION_SOURCE="' + str(frozen / "candidate.c") + '"',
                   str(frozen / "phase-contract.c"), "-o", str(out / "phase-contract")]
        report["compile_command"] = command
        save(out / "results.json", report)
        compiled = subprocess.run(command, capture_output=True, timeout=90)
        (out / "compile.stdout").write_bytes(compiled.stdout)
        (out / "compile.stderr").write_bytes(compiled.stderr)
        report["compile_returncode"] = compiled.returncode
        require(compiled.returncode == 0, "diagnostic compiler failed; preserved logs")
        report["diagnostic_native_sha256"] = sha((out / "phase-contract").read_bytes())
        for name in CASES:
            result = run_case(out / "phase-contract", name, out)
            report["cases"].append({"name": name, "passed": result["passed"],
                "returncode": result.get("returncode"), "error": result.get("error"),
                "forced_cleanup": result["forced_cleanup"], "result": str(out / name / "result.json")})
            save(out / "results.json", report)
            print(json.dumps(report["cases"][-1]), flush=True)
        report["passed"] = all(case["passed"] for case in report["cases"])
        report["passed_count"] = sum(case["passed"] for case in report["cases"])
        report["total"] = len(report["cases"])
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    save(out / "results.json", report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
