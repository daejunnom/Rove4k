"""Wave validation plus bounded toy/real-runner fault checks outside Git.

The CLI runtime checks are protocol fixtures only. They do not admit engines,
produce league scores, or supply training examples.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


wave = module("checked_rove_wave", HERE / "wave.py")


class Contracts(unittest.TestCase):
    def test_ready_metadata_compares_json_types(self):
        self.assertFalse(wave._same_json({"slot": 1}, {"slot": True}))
        self.assertFalse(wave._same_json({"slot": 1}, {"slot": 1.0}))
        self.assertTrue(wave._same_json({"slot": 1, "game": "g"}, {"game": "g", "slot": 1}))

    def test_proc_exit_race_is_absence(self):
        with patch.object(Path, "read_text", side_effect=ProcessLookupError()):
            self.assertIsNone(wave._proc_identity(123))

    def test_unverified_identity_is_unknown_and_never_signalled(self):
        job = wave.WaveJob("unknown", ("/tmp/e",), {}, {"attempt_id": "unknown"}, Path("/tmp/unknown"))
        observed = {"pid": 123, "pgid": 123, "session": 123, "start_ticks": None, "ownership_unverified": True}
        child = wave._Child(job, {}, observed, process=type("OwnedHandle", (), {"pid": 123})())
        with patch.object(wave.os, "killpg") as killpg:
            self.assertEqual(wave._owned_members(child)[0]["state"], "ownership_unverified")
            self.assertFalse(wave._signal(child, 15))
            self.assertTrue(all(call.args == (123, 0) for call in killpg.call_args_list))
        self.assertNotIn("pid_reused", observed)

    def test_job_contract(self):
        with self.assertRaises(ValueError):
            wave.WaveJob("x", ("relative",), {}, {"attempt_id": "x"}, Path("/tmp/a"))
        with self.assertRaises(ValueError):
            wave.WaveJob("x", ("/tmp/e",), {}, {"x": float("nan")}, Path("/tmp/a"))
        with self.assertRaises(ValueError):
            wave.WaveJob("x", ("/tmp/e",), {}, {"attempt_id": "x"}, Path("relative"))
        job = wave.WaveJob("x", ("/tmp/e",), {}, {"attempt_id": "x"}, Path("/tmp/a"))
        self.assertEqual(job.id, "x")

    def test_bounded_executor_contract(self):
        with self.assertRaises(ValueError):
            wave.WaveExecutor(ready_seconds=181)
        with self.assertRaises(ValueError):
            wave.WaveExecutor(output_limit_bytes=0)

    @unittest.skipUnless(sys.platform == "linux", "Linux admission boundary")
    def test_duplicate_rejects_before_spawn_or_output(self):
        with tempfile.TemporaryDirectory(prefix="rove-wave-admission-") as temporary:
            out = Path(temporary) / "not-created"
            job = wave.WaveJob("same", ("/does-not-exist",), {}, {"attempt_id": "a"}, out)
            with self.assertRaisesRegex(ValueError, "distinct"):
                wave.WaveExecutor().run_wave([job, job], 1)
            self.assertFalse(out.exists())

    @unittest.skipUnless(sys.platform == "linux", "Linux admission boundary")
    def test_stale_engine_evidence_is_preserved_before_spawn(self):
        with tempfile.TemporaryDirectory(prefix="rove-wave-stale-") as temporary:
            for name in ("game.pgn", "raw.log", "config.json"):
                out = Path(temporary) / name.replace(".", "-")
                out.mkdir()
                evidence = out / name
                evidence.write_text("old evidence\n")
                job = wave.WaveJob(name, ("/does-not-exist",), {}, {"attempt_id": name}, out)
                with self.assertRaisesRegex(ValueError, "evidence already exists"):
                    wave.WaveExecutor().run_wave([job], 1)
                self.assertEqual(evidence.read_text(), "old evidence\n")
                self.assertFalse((out / "runner.stdout.log").exists())
            out = Path(temporary) / "broken-link"
            out.mkdir()
            (out / "raw.log").symlink_to(out / "absent-target")
            job = wave.WaveJob("broken-link", ("/does-not-exist",), {}, {"attempt_id": "broken-link"}, out)
            with self.assertRaisesRegex(ValueError, "evidence already exists"):
                wave.WaveExecutor().run_wave([job], 1)
            self.assertFalse((out / "absent-target").exists())


TOY = r'''import json, os, socket, sys, time
from pathlib import Path
mode, trace = sys.argv[1:3]
def note(event):
    with open(trace, 'a') as f: f.write(json.dumps({'event':event,'time':time.monotonic()})+'\n')
note('spawn')
if mode=='pre_exit': sys.exit(7)
if mode=='delayed': time.sleep(1.1)
control=socket.socket(fileno=int(os.environ['ROVE_START_FD']))
job=json.loads(os.environ['ROVE_START_JOB'])
if mode=='wrong_job': job['attempt_id']='different'
ready={'event':'READY','job':job,'white_clock_ms':1803000,'black_clock_ms':1803000}
if mode=='wrong_clock': ready['white_clock_ms']=1802999
control.sendall((json.dumps(ready)+'\n').encode())
data=b''
while b'\n' not in data:
    chunk=control.recv(32)
    if not chunk: sys.exit(3)
    data+=chunk
if data!=b'GO\n': note('abort'); sys.exit(2)
note('go')
if mode=='long': time.sleep(10)
if mode=='flood':
    for _ in range(12): os.write(1,b'x'*65536)
if mode=='local_exit': sys.exit(9)
print('finished toy runner',flush=True)
print('toy stderr',file=sys.stderr,flush=True)
note('finish')
'''


def _external_out(out):
    if not out.is_absolute() or out.exists():
        raise ValueError("new absolute external evidence directory required")
    if any((parent / ".git").exists() for parent in (out, *out.parents)):
        raise ValueError("runtime evidence must remain outside Git")
    out.mkdir(parents=True)
    return out


def _read_rows(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def toy_checks(out: Path) -> dict:
    out = _external_out(out)
    script = out / "toy.py"
    script.write_text(TOY)
    cases = [
        ("delayed", ("normal", "delayed"), None, None, 5),
        ("pre_exit", ("normal", "pre_exit"), None, None, 5),
        ("wrong_job", ("normal", "wrong_job"), None, None, 5),
        ("wrong_clock", ("normal", "wrong_clock"), None, None, 5),
        ("denied", ("normal", "normal"), lambda: False, None, 5),
        ("release_exception", ("normal", "normal"), lambda: (_ for _ in ()).throw(RuntimeError("fixture release failure")), None, 5),
        ("local_exit", ("normal", "local_exit"), None, None, 5),
        ("wall", ("long", "long"), None, None, .3),
        ("partial_wall", ("normal", "long"), None, None, .3),
        ("event_exception", ("normal", "long"), None, None, 5),
        ("flood", ("flood", "normal"), None, None, 5),
        ("simultaneous_fault", ("normal", "flood"), None, None, 5),
        ("spawn_failure", ("normal", "missing"), None, None, 5),
    ]
    report = {"complete": False, "scope": "toy process/gate/fault checks; no engine acceptance", "cases": []}
    def save():
        (out / "toy-wave.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    for name, modes, release, _, wall in cases:
        directory = out / name
        directory.mkdir()
        jobs = []
        for index, mode in enumerate(modes):
            target = directory / str(index)
            argv = (sys.executable, str(script), mode, str(target / "events.jsonl"))
            if mode == "missing":
                argv = (str(out / "missing-executable"),)
            jobs.append(wave.WaveJob(f"{name}-{index}", argv, {},
                {"wave_id": name, "game_id": str(index), "attempt_id": f"{name}-{index}-1"}, target))
        events = []
        def event_callback(event, job, obs):
            events.append({"event": event, "identity": job.identity, "time": time.monotonic()})
            if name == "simultaneous_fault" and event == "released" and job.identity == jobs[0].identity:
                time.sleep(.08)  # Coalesce terminal EOF and sibling overflow into one poll batch.
            if name == "event_exception" and event == "tick" and any(item["event"] == "completed" for item in events):
                raise RuntimeError("fixture tick journal failure")
        before_fds = len(list(Path("/proc/self/fd").iterdir()))
        results = wave.WaveExecutor(output_limit_bytes=4096).run_wave(jobs, wall,
            release_callback=release, on_event=event_callback)
        report["cases"].append({"case": name, "observations": results, "events": events})
        save()
        if any(result["remaining_processes"] or not result["readers_done"] for result in results):
            raise AssertionError("owned runtime did not settle: " + repr(results))
        if len(list(Path("/proc/self/fd").iterdir())) != before_fds:
            raise AssertionError("wave leaked controller file descriptors: " + name)
        if name in ("delayed", "local_exit"):
            if any(result["wave_aborted"] for result in results):
                raise AssertionError("normal/local runner result aborted unrelated jobs")
            if max(result["ready_monotonic"] for result in results) > min(result["released_monotonic"] for result in results):
                raise AssertionError("a runner was released before all READY")
            if name == "local_exit" and sorted(result["returncode"] for result in results) != [0, 9]:
                raise AssertionError("individual nonzero runner exit was lost")
            if name == "delayed" and not any(event["event"] == "tick" and event["time"] - events[0]["time"] >= .7 for event in events):
                raise AssertionError("readiness wait emitted no continuing tick")
        elif name in ("partial_wall", "event_exception"):
            if results[0]["status"] != "completed" or results[0]["wave_aborted"] or results[0]["returncode"] != 0:
                raise AssertionError("earlier completed colour was discarded on later wave abort")
            if not results[1]["wave_aborted"] or not results[0].get("wave_error_context"):
                raise AssertionError("later interruption context was not preserved")
            completed = [event for event in events if event["event"] == "completed" and event["identity"] == jobs[0].identity]
            if len(completed) != 1 or completed[0]["time"] >= results[1]["completed_monotonic"]:
                raise AssertionError("completed event was not emitted while the other game was active")
        elif name == "flood":
            if not results[0]["wave_aborted"]:
                raise AssertionError("output overflow was accepted")
        elif name == "simultaneous_fault":
            if results[0]["status"] != "completed" or results[0]["wave_aborted"] or not results[1]["wave_aborted"]:
                raise AssertionError("terminal sibling was discarded by a simultaneous other fault")
        else:
            if not all(result["wave_aborted"] for result in results):
                raise AssertionError("infrastructure failure was accepted: " + name)
            if name not in ("wall", "flood") and any(result["gate_released"] for result in results):
                raise AssertionError("GO escaped a failed pregame wave: " + name)
        if name == "flood" and any(Path(result["stdout_path"]).stat().st_size > 4096 for result in results):
            raise AssertionError("stdio cap did not bound saved bytes")
    report["complete"] = True
    report["owned_live_jobs"] = 0
    save()
    return report


def identity_failure_check(out: Path) -> dict:
    out = _external_out(out)
    script = out / "toy.py"
    script.write_text(TOY)
    job = wave.WaveJob("missing-initial-identity", (sys.executable, str(script), "long", str(out / "attempt" / "events.jsonl")),
                       {}, {"attempt_id": "identity-fault-1"}, out / "attempt")
    original = wave._proc_identity
    calls = 0
    def missing_once(pid):
        nonlocal calls
        calls += 1
        return None if calls == 1 else original(pid)
    report = {"complete": False, "scope": "initial identity lookup fault; no engine acceptance", "cases": []}
    (out / "identity-fault.json").write_text(json.dumps(report, indent=2) + "\n")
    before_fds = len(list(Path("/proc/self/fd").iterdir()))
    with patch.object(wave, "_proc_identity", side_effect=missing_once):
        observed = wave.WaveExecutor().run_wave([job], 3)[0]
    report["cases"].append({"case": "missing_initial_identity", "observation": observed})
    (out / "identity-fault.json").write_text(json.dumps(report, indent=2) + "\n")
    if not observed["wave_aborted"] or observed["gate_released"] or not observed.get("initial_identity_failed"):
        raise AssertionError("failed identity admission was accepted")
    if not observed.get("identity_verified_during_cleanup") or observed["remaining_processes"] or not observed["readers_done"]:
        raise AssertionError("original child identity and stdio did not settle")
    if len(list(Path("/proc/self/fd").iterdir())) != before_fds:
        raise AssertionError("initial identity failure leaked controller descriptors")
    report.update(complete=True, owned_live_jobs=0)
    (out / "identity-fault.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def fastchess_checks(build: Path, out: Path) -> dict:
    fc = module("wave_actual_fastchess", HERE / "fastchess.py")
    fixture = module("wave_actual_fastchess_fixture", HERE / "test_fastchess.py")
    record = json.loads(build.read_text())
    binary = Path(record["binary"])
    if not record["complete"] or record["upstream_commit"] != fc.PIN or record["patch_sha256"] != fc.sha(fc.PATCH.read_bytes()) or record["binary_sha256"] != fc.sha(binary.read_bytes()):
        raise ValueError("exact reviewed runner build required")
    out = _external_out(out)
    mock_text = fixture.MOCK.replace("    if line == 'uci':\n", "    if line == 'uci':\n        if mode == 'startup_exit':\n            time.sleep(.4)\n            sys.exit(7)\n")
    mock_text = mock_text.replace("    elif line == 'isready':\n", "    elif line == 'isready':\n        if mode == 'delay': time.sleep(1.1)\n")
    mock = out / "mock.py"
    mock.write_text(mock_text)
    book = out / "book.pgn"
    book.write_text('[Event "Fixture only"]\n[Result "*"]\n\n1. f3 e5 *\n')
    report = {"complete": False, "scope": "actual patched Fastchess waves with protocol mocks only",
              "binary_sha256": record["binary_sha256"], "cases": []}
    for case in ("two_ready", "one_startup_failure"):
        base = out / case
        base.mkdir()
        jobs = []
        for index in range(2):
            directory = base / str(index)
            directory.mkdir()
            mode = "normal" if index == 0 else "delay" if case == "two_ready" else "startup_exit"
            white = fc.EngineCommand("mock-white", (sys.executable, str(mock), str(directory / "white.jsonl"), mode))
            black = fc.EngineCommand("mock-black", (sys.executable, str(mock), str(directory / "black.jsonl"), "normal"))
            argv = tuple(fc.single_game_argv(binary, white, black, opening_pgn=book, opening_start=1, out=directory))
            metadata = {"wave_id": case, "game_id": f"game-{index}", "attempt_id": f"{case}-{index}-1",
                        "slot_id": str(index), "opening_id": "fixture-foolsmate"}
            jobs.append(wave.WaveJob(metadata["attempt_id"], argv, {}, metadata, directory))
        events = []
        results = wave.WaveExecutor().run_wave(jobs, 15,
            on_event=lambda event, job, obs: events.append({"event": event, "identity": job.identity, "time": time.monotonic()}))
        if any(result["remaining_processes"] or not result["readers_done"] for result in results):
            raise AssertionError("actual wave did not physically settle")
        if case == "two_ready":
            if any(result["wave_aborted"] or result["returncode"] != 0 for result in results):
                raise AssertionError("actual ready wave failed: " + repr(results))
            if max(result["ready_monotonic"] for result in results) > min(result["released_monotonic"] for result in results):
                raise AssertionError("a real runner started before the delayed peer was ready")
            for job in jobs:
                pgn = (job.out / "game.pgn").read_text()
                if '[Result "0-1"]' not in pgn:
                    raise AssertionError("actual legal mate fixture failed")
        else:
            if not all(result["wave_aborted"] and not result["gate_released"] for result in results):
                raise AssertionError("startup failure released another game")
            if any((job.out / "game.pgn").exists() and (job.out / "game.pgn").read_text().strip() for job in jobs):
                raise AssertionError("failed pregame wave produced a scored game")
        report["cases"].append({"case": case, "observations": results, "events": events})
        (out / "actual-wave.json").write_text(json.dumps(report, indent=2) + "\n")
    report["complete"] = True
    report["owned_live_jobs"] = 0
    (out / "actual-wave.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    if "--toy-out" in sys.argv or "--build" in sys.argv or "--identity-out" in sys.argv:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--toy-out", type=Path)
        parser.add_argument("--identity-out", type=Path)
        parser.add_argument("--build", type=Path)
        parser.add_argument("--out", type=Path)
        args = parser.parse_args()
        if args.toy_out:
            result = toy_checks(args.toy_out)
        elif args.identity_out:
            result = identity_failure_check(args.identity_out)
        else:
            if not args.build or not args.out:
                parser.error("--build and --out are required for actual runner checks")
            result = fastchess_checks(args.build, args.out)
        print(json.dumps({"complete": result["complete"], "cases": len(result["cases"]), "owned_live_jobs": result["owned_live_jobs"]}))
    else:
        unittest.main()
