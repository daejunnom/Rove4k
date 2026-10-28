"""Focused adapter tests and actual patched-runner protocol fault checks.

Run the small unit tests normally. The optional --build/--out command consumes
the real build receipt and writes actual mocked-UCI runtime evidence outside Git;
none of these games are strength or training data.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("rove_fastchess", HERE / "fastchess.py")
fastchess = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fastchess
spec.loader.exec_module(fastchess)
peer_spec = importlib.util.spec_from_file_location("rove_original_peer_uci", HERE / "original_peer_uci.py")
original_peer_uci = importlib.util.module_from_spec(peer_spec)
peer_spec.loader.exec_module(original_peer_uci)


class Adapter(unittest.TestCase):
    def test_go2_receipt_is_framed_and_not_a_search_claim(self):
        left, right = socket.socketpair()
        try:
            message = {"event": "GO2_ACCEPTED", "attempt_id": "fixture-attempt-0001",
                       "fence_id": "fence-1", "job_sha256": "a" * 64, "nonce": "b" * 64}
            wire = json.dumps(message).encode() + b"\n"
            right.sendall(wire[:13])
            right.sendall(wire[13:])
            self.assertEqual(_wait_go2_receipt(left), message)
        finally:
            left.close()
            right.close()

        left, right = socket.socketpair()
        try:
            right.close()
            with self.assertRaisesRegex(RuntimeError, "gate closed"):
                _wait_go2_receipt(left)
        finally:
            left.close()

    def test_one_game_colour_and_restart_contract(self):
        white = fastchess.EngineCommand("white", ("/tmp/white", "argument with spaces"))
        black = fastchess.EngineCommand("black", ("/tmp/black",))
        argv = fastchess.single_game_argv(Path("/tmp/fc"), white, black,
            opening_pgn=Path("/tmp/book.pgn"), opening_start=2, out=Path("/tmp/attempt"))
        self.assertEqual(argv[argv.index("-games") + 1], "1")
        self.assertEqual(argv[argv.index("-concurrency") + 1], "1")
        self.assertIn("-noswap", argv)
        self.assertIn("restart=on", argv)
        self.assertIn("timemargin=0", argv)
        self.assertIn("option.Ponder=false", argv[argv.index("-each") + 1:argv.index("-openings")])
        self.assertIn("start=2", argv)
        self.assertLess(argv.index("name=white"), argv.index("name=black"))
        self.assertIn("args='argument with spaces'", argv)
        for forbidden in ("-repeat", "-reverse", "-recover", "-use-affinity", "-strict"):
            self.assertNotIn(forbidden, argv)
        reverse = fastchess.single_game_argv(Path("/tmp/fc"), black, white,
            opening_pgn=Path("/tmp/book.pgn"), opening_start=2, out=Path("/tmp/reverse"))
        self.assertLess(reverse.index("name=black"), reverse.index("name=white"))

    def test_peer_resources_are_per_engine_and_follow_colour(self):
        for profile, hash_mib, threads in (("test-p16", 16384, 16), ("test-p192", 262144, 192)):
            peer = fastchess.EngineCommand("ice4", ("/tmp/ice4",), **original_peer_uci.fastchess_resources(profile))
            rove = fastchess.EngineCommand("rove", ("/tmp/rove",))
            for left, right in ((peer, rove), (rove, peer)):
                argv = fastchess.single_game_argv(Path("/tmp/fc"), left, right,
                    opening_pgn=Path("/tmp/book"), opening_start=1, out=Path("/tmp/out"))
                segments = {}
                for index, value in enumerate(argv):
                    if value == "-engine":
                        end = next(i for i in range(index + 1, len(argv)) if argv[i] in ("-engine", "-each"))
                        segments[argv[index + 1]] = argv[index + 2:end]
                self.assertIn(f"option.Hash={hash_mib}", segments["name=ice4"])
                self.assertIn(f"option.Threads={threads}", segments["name=ice4"])
                self.assertFalse(any(arg.startswith(("option.Hash=", "option.Threads="))
                                     for arg in segments["name=rove"]))
        for kwargs in ({"hash_mib": 16}, {"threads": 16}, {"hash_mib": True, "threads": 16},
                       {"hash_mib": 1, "threads": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                fastchess.EngineCommand("ice4", ("/tmp/ice4",), **kwargs)
        with self.assertRaises(ValueError):
            original_peer_uci.fastchess_resources("submission")

    def test_ponder_command_evidence_preserves_unknown_behavior(self):
        observed = fastchess.ponder_uci_evidence([
            "uci", "setoption name Ponder value false", "go wtime 3000 btime 3000",
            "go ponder wtime 2000 btime 3000"])
        self.assertEqual(observed["setoption_ponder_false_received"], 1)
        self.assertEqual(observed["go_ponder_received"], 1)
        self.assertIsNone(observed["actual_off_turn_search"])
        self.assertIsNone(observed["tcec_ponder_compliance"])
        unavailable = fastchess.ponder_uci_evidence(["uci", "go wtime 100 btime 100"])
        self.assertEqual(unavailable["setoption_ponder_false_received"], 0)
        self.assertEqual(unavailable["go_ponder_received"], 0)
        self.assertIsNone(unavailable["actual_off_turn_search"])
        for invalid in (("uci\nquit",), (None,), "uci"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                fastchess.ponder_uci_evidence(invalid)

    def test_bad_invocation_rejects(self):
        with self.assertRaises(ValueError):
            fastchess.EngineCommand("x", ("relative",))
        with self.assertRaises(ValueError):
            fastchess.EngineCommand("x\ninjected", ("/tmp/engine",))
        with self.assertRaises(ValueError):
            fastchess._external_new(Path("../external"))
        command = fastchess.EngineCommand("x", ("/tmp/engine",))
        with self.assertRaises(ValueError):
            fastchess.single_game_argv(Path("/tmp/fc"), command, command,
                opening_pgn=Path("/tmp/b"), opening_start=1, out=Path("/tmp/a"))
        other = fastchess.EngineCommand("y", ("/tmp/other",))
        with self.assertRaises(ValueError):
            fastchess.single_game_argv(Path("/tmp/fc"), command, other,
                opening_pgn=Path("/tmp/b"), opening_start=0, out=Path("/tmp/a"))

    def test_upstream_mutation_is_not_a_patch_input(self):
        with self.assertRaisesRegex(ValueError, "pinned upstream source differs"):
            fastchess.patched_sources({name: b"changed\n" for name in fastchess.PINS})

    @unittest.skipUnless(sys.platform == "linux", "owned group check requires Linux")
    def test_failed_owned_command_preserves_result_and_settles(self):
        with tempfile.TemporaryDirectory(prefix="rove-fastchess-owned-") as temporary:
            directory = Path(temporary)
            log = directory / "timeout.log"
            with self.assertRaisesRegex(RuntimeError, "external command failed or did not settle"):
                fastchess._run_owned([sys.executable, "-c", "import time; time.sleep(5)"],
                    cwd=directory, log=log, timeout=1)
            receipt = json.loads((directory / "timeout.command.json").read_text(encoding="utf-8"))
            self.assertNotEqual(receipt["returncode"], 0)
            self.assertTrue(receipt["forced_cleanup"])
            self.assertTrue(receipt["leader_reaped"])
            self.assertTrue(receipt["group_absent"])


MOCK = r'''#!/usr/bin/env python3
import json, os, stat, sys, time
trace, mode = sys.argv[1:3]
def note(**row):
    with open(trace, 'a', encoding='utf-8') as handle:
        handle.write(json.dumps(row) + '\n')
fd = int(os.environ.get('ROVE_START_FD', '-1'))
try:
    inherited = stat.S_ISSOCK(os.fstat(fd).st_mode)
except OSError:
    inherited = False
opening_inherited = False
for entry in os.listdir('/proc/self/fd'):
    try:
        opening_inherited |= 'memfd:rove4k-opening' in os.readlink('/proc/self/fd/' + entry)
    except OSError:
        pass
note(event='spawn', pid=os.getpid(), control_socket_inherited=inherited,
     opening_fd_inherited=opening_inherited, opening_env_inherited='ROVE_OPENING_FD' in os.environ)
moves = []
sequence = ['f2f3', 'e7e5', 'g2g4', 'd8h4']
for raw in sys.stdin:
    line = raw.strip()
    note(event='input', line=line)
    if line == 'uci':
        if mode == 'noise':
            until = time.monotonic() + .7
            while time.monotonic() < until:
                print('info string still initializing', flush=True)
                print('initializing', file=sys.stderr, flush=True)
                time.sleep(.005)
        if mode in ('ponder-option', 'resource-options'):
            print('option name Ponder type check default true', flush=True)
        if mode == 'resource-options':
            print('option name Hash type spin default 8 min 1 max 67108864', flush=True)
            print('option name Threads type spin default 1 min 1 max 2048', flush=True)
        print('uciok', flush=True)
    elif line == 'isready':
        print('readyok', flush=True)
    elif line.startswith('position '):
        assert line.startswith('position startpos'), line
        moves = line.split(' moves ',1)[1].split() if ' moves ' in line else []
    elif line.startswith('go'):
        print('bestmove ' + sequence[len(moves)], flush=True)
    elif line == 'quit':
        break
note(event='exit')
'''


def _rows(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _wait_ready(sock, process, timeout=10):
    sock.settimeout(.1)
    deadline, data = time.monotonic() + timeout, b""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("runner ended before READY")
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            continue
        if not chunk:
            raise RuntimeError("gate closed before READY")
        data += chunk
        if len(data) > 16384:
            raise RuntimeError("excessive gate message")
        if b"\n" in data:
            line, extra = data.split(b"\n", 1)
            if extra:
                raise RuntimeError("unexpected additional gate data")
            return json.loads(line)
    raise TimeoutError("READY wait exceeded")


def _wait_go2_receipt(sock, timeout=10):
    """Read one local acceptance receipt, never infer an engine GO from it."""
    sock.settimeout(timeout)
    data = b""
    while b"\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError("gate closed before GO2 receipt")
        data += chunk
        if len(data) > 16384:
            raise RuntimeError("excessive GO2 receipt")
    line, extra = data.split(b"\n", 1)
    if extra:
        raise RuntimeError("unexpected additional receipt data")
    return json.loads(line)


def actual_check(build_receipt: Path, out: Path) -> dict:
    if sys.platform != "linux":
        raise RuntimeError("actual runner verification requires Linux")
    built = json.loads(build_receipt.read_text(encoding="utf-8"))
    if not built["complete"] or built["upstream_commit"] != fastchess.PIN:
        raise ValueError("pinned complete build receipt required")
    if built["patch_sha256"] != fastchess.sha(fastchess.PATCH.read_bytes()):
        raise ValueError("build did not use this patch")
    binary = Path(built["binary"])
    if fastchess.sha(binary.read_bytes()) != built["binary_sha256"]:
        raise ValueError("actual binary differs from receipt")
    out = fastchess._external_new(out)
    out.mkdir(parents=True)
    mock = out / "mock engine.py"
    mock.write_text(MOCK, encoding="utf-8")
    mock.chmod(0o700)
    book = out / "book.pgn"
    book.write_text('[Event "Fixture only"]\n[Result "*"]\n\n1. f3 e5 *\n', encoding="utf-8")
    report = {"complete": False, "upstream_commit": fastchess.PIN,
              "patch_sha256": built["patch_sha256"], "binary_sha256": built["binary_sha256"],
              "evidence_scope": "protocol mocks; no strength, training or engine acceptance", "cases": []}
    def save():
        (out / "runtime.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    save()
    # Runner must reject an inherited but unsealed opening before parsing args
    # or launching any engine. This is separate from a valid helper invocation.
    unsealed = os.memfd_create("rove4k-test-unsealed", os.MFD_ALLOW_SEALING)
    try:
        probe_env = dict(os.environ, ROVE_OPENING_FD=str(unsealed))
        for key in ("ROVE_START_FD", "ROVE_START_JOB", "ROVE_START_PROTOCOL"):
            probe_env.pop(key, None)
        probe = subprocess.run([str(binary), "--help"], env=probe_env, pass_fds=(unsealed,),
                               capture_output=True, timeout=15)
        if probe.returncode == 0 or b"cannot protect sealed opening FD" not in probe.stderr:
            raise AssertionError("unsealed inherited opening was not rejected at startup")
        report["unsealed_opening_rejected"] = True
    finally:
        os.close(unsealed)
    for case, response in (("normal", b"GO\n"), ("reverse", b"GO\n"),
                           ("sealed-opening", b"GO\n"),
                           ("peer-resources-p16", b"GO\n"), ("peer-resources-p192", b"GO\n"),
                           ("abort", b"ABORT\n"), ("disconnect", None), ("noise", b"GO\n"),
                           ("go2", b""), ("go2-wrong-attempt", b""), ("go2-bad-digest", b""),
                           ("go2-legacy-go", b"GO\n"), ("go2-abort", b"ABORT\n"),
                           ("go2-long-attempt", b""), ("go2-too-long-attempt", b"")):
        directory = out / case
        directory.mkdir()
        ta, tb = directory / "a.jsonl", directory / "b.jsonl"
        peer_resources = case.startswith("peer-resources-")
        a_args = (sys.executable, str(mock), str(ta),
                  "noise" if case == "noise" else "resource-options" if peer_resources else "ponder-option")
        a = (fastchess.EngineCommand("mock-a", a_args, **original_peer_uci.fastchess_resources(
                    "test-p16" if case.endswith("p16") else "test-p192")) if peer_resources
             else fastchess.EngineCommand("mock-a", a_args))
        b = fastchess.EngineCommand("mock-b", (sys.executable, str(mock), str(tb), "normal"))
        white, black = (b, a) if case == "reverse" else (a, b)
        argv = fastchess.single_game_argv(binary, white, black, opening_pgn=book,
                                         opening_start=1, out=directory)
        if case == "sealed-opening":
            argv[argv.index("file=" + str(book))] = "file=/__rove4k_sealed_opening_snapshot_v1__"
            argv = [sys.executable, "-I", str(HERE / "sealed_opening_exec.py"),
                    "--source", str(book), "--sha256", fastchess.sha(book.read_bytes()),
                    "--bytes", str(book.stat().st_size), "--", *argv]
        if case == "noise":
            argv[argv.index("-startup-ms") + 1] = "100"
        parent, child = socket.socketpair()
        metadata = {"campaign_id": "fixture", "pair_id": "fixture-pair", "game_id": case,
                    "attempt_id": "fixture-attempt-0001", "slot_id": "fixture-slot", "wave_id": "fixture-wave",
                    "white": white.identity, "black": black.identity, "opening_id": "fixture-foolsmate"}
        if case in ("go2-long-attempt", "go2-too-long-attempt"):
            metadata["attempt_id"] = "x" * (128 if case == "go2-long-attempt" else 129)
        if case in ("go2", "go2-wrong-attempt", "go2-bad-digest", "go2-long-attempt", "go2-too-long-attempt"):
            attempt = "fixture-attempt-0002" if case == "go2-wrong-attempt" else metadata["attempt_id"]
            digest = "A" * 64 if case == "go2-bad-digest" else "a" * 64
            response = f"GO2 {attempt} fence-1 {digest} {'b' * 64}\n".encode("ascii")
        environment = dict(os.environ, ROVE_START_FD=str(child.fileno()),
                           ROVE_START_JOB=json.dumps(metadata, separators=(",", ":")))
        environment.pop("ROVE_OPENING_FD", None)
        if case.startswith("go2"):
            environment["ROVE_START_PROTOCOL"] = "2"
        else:
            environment.pop("ROVE_START_PROTOCOL", None)
        command_log = directory / "runner.log"
        started, forced, ready = time.monotonic(), False, None
        process = None
        failure = None
        ponder_evidence = None
        try:
            with command_log.open("wb") as output:
                process = subprocess.Popen(argv, cwd=directory, env=environment, stdout=output,
                    stderr=subprocess.STDOUT, pass_fds=(child.fileno(),), start_new_session=True)
                child.close()
                if case != "noise":
                    ready = _wait_ready(parent, process)
                    if ready != {"event": "READY", "job": metadata,
                                 "white_clock_ms": 1803000, "black_clock_ms": 1803000}:
                        raise AssertionError("READY metadata or initial clocks differ: " + repr(ready))
                    time.sleep(.2)
                    if any(row.get("line", "").startswith("go") for p in (ta, tb) for row in _rows(p)):
                        raise AssertionError("a scored GO occurred before controller release")
                    if response is None:
                        parent.close()
                    else:
                        # Deliberate split exercises stream framing, not TCP packet boundaries.
                        if case.startswith("go2"):
                            parent.sendall(response[:7])
                            parent.sendall(response[7:])
                        else:
                            parent.sendall(response)
                        if case in ("go2", "go2-long-attempt"):
                            receipt = _wait_go2_receipt(parent)
                            if receipt != {"event": "GO2_ACCEPTED", "attempt_id": metadata["attempt_id"],
                                           "fence_id": "fence-1", "job_sha256": "a" * 64,
                                           "nonce": "b" * 64}:
                                raise AssertionError("GO2 local receipt differs: " + repr(receipt))
                code = process.wait(timeout=15)
            rows = _rows(ta) + _rows(tb)
            if any(row.get("control_socket_inherited") for row in rows):
                raise AssertionError("engine inherited runner control socket")
            if case == "sealed-opening" and any(row.get("opening_fd_inherited") or row.get("opening_env_inherited") for row in rows):
                raise AssertionError("engine inherited the sealed opening descriptor or environment")
            pg = directory / "game.pgn"
            pgn = pg.read_text(encoding="utf-8") if pg.exists() else ""
            stdout = command_log.read_text(encoding="utf-8")
            if case in ("normal", "reverse", "sealed-opening", "peer-resources-p16", "peer-resources-p192", "go2", "go2-long-attempt"):
                if code or f'[White "{white.identity}"]' not in pgn or f'[Black "{black.identity}"]' not in pgn:
                    raise AssertionError("normal/reversed game or player colour failed: " + stdout[-2500:])
                if '[Result "0-1"]' not in pgn:
                    raise AssertionError("legal fixture did not end in black's mate")
                goes = [row["line"] for row in rows if row.get("line", "").startswith("go")]
                first_white = [row["line"] for row in _rows(tb if case == "reverse" else ta)
                               if row.get("line", "").startswith("go")]
                if len(goes) != 2 or not first_white or "wtime 1803000 btime 1803000" not in first_white[0]:
                    raise AssertionError("gate altered first game clocks: " + repr(goes))
                ponder_evidence = {name: fastchess.ponder_uci_evidence(
                    [row["line"] for row in _rows(trace) if row.get("event") == "input"])
                    for name, trace in (("mock-a", ta), ("mock-b", tb))}
                if (ponder_evidence["mock-a"]["setoption_ponder_false_received"] != 1 or
                        ponder_evidence["mock-b"]["setoption_ponder_false_received"] != 0 or
                        any(row["go_ponder_received"] for row in ponder_evidence.values())):
                    raise AssertionError("advertised/unsupported Ponder command behavior differed: "
                                         + repr(ponder_evidence))
                if peer_resources:
                    first = [row.get("line") for row in _rows(ta) if row.get("event") == "input"]
                    second = [row.get("line") for row in _rows(tb) if row.get("event") == "input"]
                    expected = [f"setoption name Hash value {a.hash_mib}", f"setoption name Threads value {a.threads}"]
                    if any(first.count(line) != 1 for line in expected) or any(line in second for line in expected):
                        raise AssertionError("peer resource commands were not engine-specific: " + repr((first, second)))
            elif case == "noise":
                if code == 0 or "Engine didn't respond to uciok after startup" not in stdout:
                    raise AssertionError("chatter extended the absolute startup deadline")
                raw_log = (directory / "raw.log").read_text(encoding="utf-8")
                sent = re.search(r'\[Engine\] \[([0-9:.]+)\].*mock-a <--- uci\n', raw_log)
                expired = re.search(r'\[WARN\s*\] \[([0-9:.]+)\].*did not respond to uciok in time', raw_log)
                if not sent or not expired:
                    raise AssertionError("startup deadline phase was not observed")
                phase = (datetime.strptime(expired[1], "%H:%M:%S.%f") -
                         datetime.strptime(sent[1], "%H:%M:%S.%f")).total_seconds() % 86400
                if not .07 <= phase <= .5:
                    raise AssertionError("noisy startup did not stop at its absolute 100ms limit: " + str(phase))
                if pgn.strip():
                    raise AssertionError("startup failure produced a scored PGN")
            else:
                if code == 0 or "ROVE_START_GATE_ABORT" not in stdout or pgn.strip():
                    raise AssertionError("gate failure was scored or accepted: " + stdout[-2500:])
                if any(row.get("line", "").startswith("go") for row in rows):
                    raise AssertionError("gate failure still started search")
        except Exception as error:
            failure = repr(error)
        finally:
            parent.close()
            child.close()
            if process is not None and process.poll() is None:
                forced = True
                fastchess.signal_owned_group(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    fastchess.signal_owned_group(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
            if process is None:
                absent = True
            else:
                try:
                    os.killpg(process.pid, 0)
                except ProcessLookupError:
                    absent = True
                else:
                    absent = False
                    forced = True
                    fastchess.signal_owned_group(process.pid, signal.SIGKILL)
            item = {"case": case, "argv": argv, "pid": process.pid if process else None,
                    "returncode": process.returncode if process else None, "elapsed_seconds": time.monotonic() - started,
                    "ready": ready, "forced_cleanup": forced, "group_absent": absent,
                    "runner_log_sha256": fastchess.sha(command_log.read_bytes()), "failure": failure}
            if case == "noise" and failure is None:
                item["startup_wait_seconds"] = phase
            if ponder_evidence is not None:
                item["ponder_command_evidence"] = ponder_evidence
            report["cases"].append(item)
            save()
        if failure or forced or not absent:
            raise AssertionError("runtime case did not qualify: " + json.dumps(item))
    report["complete"] = True
    report["owned_live_jobs"] = 0
    save()
    return report


if __name__ == "__main__":
    if "--build" in sys.argv:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--build", type=Path, required=True)
        parser.add_argument("--out", type=Path, required=True)
        args = parser.parse_args()
        proof = actual_check(args.build, args.out)
        print(json.dumps({"complete": proof["complete"], "cases": len(proof["cases"]),
                          "owned_live_jobs": proof["owned_live_jobs"]}))
    else:
        unittest.main()
