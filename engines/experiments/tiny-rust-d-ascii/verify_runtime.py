#!/usr/bin/env python3
"""Bounded actual-image checks for the one ASCII ingress cost candidate.

The old native runtime helper is copied unchanged into external evidence and
reused. Only its command-admission accounting is overridden for the declared
ASCII policy. This runner builds no engine or diagnostic variant.
"""

if __name__ == "__main__":
    raise SystemExit("Rove4k Rust engine paths are retired; use C A-F")

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import sys

HERE = Path(__file__).resolve().parent
HELPER_SHA = "d43b9d4b419ec1b778638bc741376b9f4122a5def780eb929cbba3af170ac2a3"
MAIN_SHA = "e10e1b797085c1f032edcbfe28a828cf91e8cf2c71f3f11c063328744c34b8a3"
BOARD_SHA = "1a1ff1a0693a1b3f53ade2435d2996684a1bcd7b7eee333f28fe669645340b82"
OTHER = {
    "search.rs": "da2583806efea022b1b3b1337557b896a373a561f11d665b1ca747c29e3aed81",
    "runtime.rs": "802b497371a409744ad231cd8f621ea3d8b7cd931627e0396f3ec92ad1345b2d",
    "os.rs": "892cc62e2c126ebcbc171eb6f8059aacf92cf255d85341487e46effe2b94986e",
    "link.ld": "1e8f17bb2f06a6ddabf1f56d155bd7bdcd8c4406d140c22770bcfda96d459bbc",
    "build.py": "08f28ebdc45ad49c2a23f7eb8e28b086612ea9a33dbc39cb8ccbd66bfcf68e89",
}
EXPECTED = {"main.rs": MAIN_SHA, "board.rs": BOARD_SHA, **OTHER}
ELFS = {
    "hq": "f8581a68f09d4d9cdc3e1413aa45ffb385bafd8240f1432403629ec2a0e544f8",
    "scalar": "bd0e3bd1567ae906d4ab9704603204d22302895df1f05679f6221d6445aef878",
}
SEPARATOR = re.compile(rb"[\x09-\x0d ]+")
TRIM = b"\t\n\v\f\r "


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(value, message):
    if not value:
        raise AssertionError(message)


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def load_helper(path, out, sessions):
    raw = Path(path).read_bytes()
    check(sha(raw) == HELPER_SHA, "old strict helper changed before freezing")
    frozen = out / "strict_native_helper.py"
    frozen.write_bytes(raw)
    check(sha(frozen.read_bytes()) == HELPER_SHA, "frozen helper byte mismatch")
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("frozen_native_runtime", frozen)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)

    class ASCIISession(helper.Session):
        """Keep strict pipe/count machinery; match the new input admission policy."""
        def __init__(self, *args, **kwargs):
            try:
                super().__init__(*args, **kwargs)
            except BaseException:
                process = getattr(self, "process", None)
                if process is not None and process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=5)
                raise
            self.rejected_lines = []
            self.emergency_cleanup_needed = None
            sessions.append(self)

        def admit(self, data=b"", eof=False):
            self.input_pending += data
            while b"\n" in self.input_pending or eof and self.input_pending:
                end = self.input_pending.find(b"\n")
                if end < 0:
                    raw, self.input_pending = self.input_pending, b""
                else:
                    raw, self.input_pending = self.input_pending[:end+1], self.input_pending[end+1:]
                if len(raw) > 32768 or 0 in raw or any(b > 127 for b in raw):
                    self.rejected_lines.append({"bytes": len(raw), "sha256": sha(raw)})
                    continue
                stripped = raw.strip(TRIM)
                words = SEPARATOR.split(stripped) if stripped else []
                if words and words[0] == b"go":
                    self.dispatched_go += 1
                if words and words[0] in (b"go", b"stop", b"position", b"ucinewgame", b"quit"):
                    self.boundaries.append({"command": words[0].decode("ascii"),
                        "dispatched_go": self.dispatched_go, "accepted_best": self.accepted_best})

        def close(self):
            self.emergency_cleanup_needed = self.process.poll() is None
            super().close()
            save(self.directory / "ascii-admission.json", {
                "rejected_lines": self.rejected_lines,
                "emergency_cleanup_needed": self.emergency_cleanup_needed,
                "returncode": self.process.returncode,
            })

    helper.Session = ASCIISession
    return helper


def supplemental(helper, image, root):
    root.mkdir()
    result = {}
    s = helper.Session(image, root / "ascii-no-effects")
    try:
        s.send("uci\nisready\n")
        s.until("uciok"); s.until("readyok")
        tids = s.tasks()
        check(len(tids) == 3, "supplemental startup did not have three TIDs")
        original_maps = s.maps()
        check(len(helper.guarded(original_maps)) == 2, "supplemental guarded stacks absent")
        s.send("position startpos moves e2e4\ngo infinite\n")
        s.no_best(active=True)
        rejected = [
            ("NUL-stop", b"stop \x00\n"),
            ("invalid-UTF8-stop", b"stop \xff\n"),
            ("valid-UTF8-NBSP-stop", b"stop\xc2\xa0\n"),
            ("valid-UTF8-argument-stop", b"stop \xc3\xa9\n"),
            ("valid-UTF8-GO-argument", b"go btime 0 \xc3\xa9\n"),
            ("valid-UTF8-GO-NBSP", b"go\xc2\xa0btime 0\n"),
            ("valid-UTF8-position-argument", b"position startpos \xc3\xa9\n"),
            ("valid-UTF8-position-whitespace", b"position\xe2\x80\x83startpos\n"),
            ("valid-UTF8-reset-argument", b"ucinewgame \xc3\xa9\n"),
            ("valid-UTF8-quit-argument", b"quit \xc3\xa9\n"),
            ("NUL-position", b"position startpos\x00\n"),
            ("NUL-quit", b"quit\x00\n"),
            ("valid-UTF8-isready-argument", b"isready \xc3\xa9\n"),
            ("valid-UTF8-uci-argument", b"uci \xc3\xa9\n"),
        ]
        evidence = []
        for label, command in rejected:
            ready_before = s.lines.count("readyok")
            uci_before = s.lines.count("uciok")
            start = len(s.lines)
            s.send(command + b"isready\n")
            s.until("readyok")
            s.no_best(duration=.025, active=True)
            check(s.lines.count("readyok") == ready_before + 1, label + ": rejected command produced readyok")
            check(s.lines.count("uciok") == uci_before, label + ": rejected command produced uciok")
            check(s.process.poll() is None, label + ": rejected line terminated process")
            check(s.tasks() == tids, label + ": TIDs changed")
            check(s.dispatched_go == 1, label + ": rejected GO counted as admitted")
            evidence.append({"case": label, "raw_hex": command.hex(), "barrier": "readyok",
                "new_lines": s.lines[start:], "active_search_preserved": True})
        controls = []
        for value in (28, 31, 127):
            s.send(b"stop" + bytes([value]) + b"\nisready\n")
            s.until("readyok"); s.no_best(duration=.025, active=True)
            controls.append({"byte": value, "unknown_command_preserved_active_search": True})
        s.send("stop\n")
        stopped_move = helper.best(s, helper.initial("black")); s.no_best()
        s.send(b"go btime 0 \xc3\xa9\nisready\n")
        s.until("readyok"); s.no_best(duration=.04)
        check(s.dispatched_go == 1, "idle rejected GO changed dispatch accounting")
        s.send("go btime +0\n")
        retained_move = helper.best(s, helper.initial("black")); s.no_best()
        fixed = lambda text: [line for line in text.splitlines() if "[stack]" not in line]
        check(fixed(s.maps()) == fixed(original_maps), "supplemental fixed mappings changed")
        check(s.tasks() == tids, "supplemental TIDs changed after stop and next GO")
        s.finish()
        check(all(not Path(f"/proc/{tid}").exists() for tid in tids), "supplemental quit left worker TID")
        result["whole_line_rejection"] = {"passed": True, "cases": evidence,
            "other_ASCII_controls_are_not_whitespace": controls,
            "idle_nonASCII_GO_rejected_without_bestmove": True,
            "active_stop_move": stopped_move, "retained_black_position_move": retained_move,
            "fixed_tids_and_mappings": True, "all_tasks_gone_before_cleanup": True}
    finally:
        s.close()

    s = helper.Session(image, root / "ascii-whitespace-numeric")
    try:
        s.send("uci\n"); s.until("uciok")
        whitespace = []
        for value in (9, 10, 11, 12, 13, 32):
            before = s.lines.count("readyok")
            s.send(bytes([value]) + b"isready\n")
            s.until("readyok")
            s.no_best()
            check(s.lines.count("readyok") == before + 1, "ASCII whitespace barrier count")
            whitespace.append({"byte": value, "role": "line delimiter" if value == 10 else "leading/token whitespace"})
            if value != 10:
                ws = bytes([value])
                s.send(ws.join((b"position", b"startpos", b"moves", b"e2e4")) + b"\n")
                s.send(ws.join((b"go", b"btime", b"+0")) + b"\n")
                helper.best(s, helper.initial("black")); s.no_best()
        # Every invalid replay starts from an owned candidate and must retain
        # the earlier one-ply black-to-move game instead of a partial replay.
        s.send("position startpos moves e2e4\n")
        invalid_position = [
            b"position startpos moves d2d4 d7d5 e1e8\n",
            b"position startpos moves e2e4q\n",
            b"position startpos moves a9a1\n",
            b"position startpos moves e2e4 E7E5\n",
        ]
        replay = []
        for command in invalid_position:
            s.send(command + b"go btime +0\n")
            move = helper.best(s, helper.initial("black")); s.no_best()
            replay.append({"command_ascii": command.decode("ascii").rstrip("\n"), "black_legal_bestmove": move})
        numeric_cases = [
            ("leading-plus-zero", b"go btime +0\n"),
            ("leading-plus-leading-zeros", b"go btime +0000000000000000000\n"),
            ("u64-overflow", b"go btime 18446744073709551616\n"),
            ("plus-u64-overflow", b"go btime +18446744073709551616\n"),
            ("increment-overflow", b"go btime +0 binc +18446744073709551616\n"),
            ("invalid-numeric-keeps-following-key", b"go btime winc +0\n"),
            ("unknown-key-numeric-pair", b"go unrecognized +001 btime +0\n"),
            ("wrong-side-clock-before-selected-clock", b"go wtime 0 btime +0\n"),
            ("maximum-u64-then-last-clock", b"go btime 18446744073709551615 btime +0\n"),
            ("bare-plus-invalid", b"go btime +\n"),
            ("double-plus-invalid", b"go btime ++1\n"),
            ("negative-zero-invalid", b"go btime -0\n"),
            ("trailing-letter-invalid", b"go btime 1x\n"),
            ("failed-unknown-lookahead-keeps-clock-key", b"go unrecognized btime +0\n"),
        ]
        numeric = []
        for label, command in numeric_cases:
            s.send(command)
            move = helper.best(s, helper.initial("black")); s.no_best()
            numeric.append({"case": label, "command_ascii": command.decode("ascii").rstrip("\n"),
                "black_legal_bestmove": move, "completed_before_stop_or_EOF": True})
        infinite = []
        for command in (b"go btime +0 infinite\n", b"go infinite btime +0\n", b"go btime infinite\n", b"go btime bad infinite\n"):
            s.send(command); s.no_best(duration=.06, active=True)
            s.send("isready\n"); s.until("readyok"); s.no_best(duration=.025, active=True)
            s.send("stop\n"); move = helper.best(s, helper.initial("black")); s.no_best()
            infinite.append({"command_ascii": command.decode("ascii").rstrip("\n"),
                "active_through_barrier_then_one_stop_bestmove": move})
        wrong_side = []
        for black in (False, True):
            s.send("position startpos" + (" moves e2e4" if black else "") + "\n")
            command = "go " + ("wtime" if black else "btime") + " 0\n"
            s.send(command); s.no_best(duration=.05, active=True)
            s.send("isready\n"); s.until("readyok"); s.no_best(duration=.025, active=True)
            s.send("stop\n"); move = helper.best(s, helper.initial("black" if black else "white")); s.no_best()
            wrong_side.append({"side": "black" if black else "white", "command": command.rstrip("\n"),
                "active_through_barrier_then_one_stop_bestmove": move})
        s.finish()
        result["ascii_whitespace_numeric_replay"] = {"passed": True,
            "whitespace": whitespace, "invalid_position_transactional": replay,
            "numeric": numeric, "infinite": infinite,
            "wrong_side_clock_only": wrong_side,
            "numeric_consumption_limit": "Unknown numeric pair is exercised through actual natural completion; internal token consumption additionally requires source equivalence, not inferred from the move."}
    finally:
        s.close()
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hq", type=Path, required=True)
    ap.add_argument("--scalar", type=Path, required=True)
    ap.add_argument("--helper", type=Path, default=HERE / "control/verify_runtime.py")
    ap.add_argument("--stable", type=Path, default=HERE / "control")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    out = args.out.resolve()
    repo = HERE.parents[2]
    if sys.platform != "linux" or not args.out.is_absolute() or out.exists() or out == repo or repo in out.parents:
        ap.error("new absolute external Linux output required")
    out.mkdir()
    raw = Path(__file__).read_bytes()
    (out / "verify_runtime.py").write_bytes(raw)
    sessions = []
    report = {"passed": False, "verifier_sha256": sha(raw), "helper_sha256": HELPER_SHA,
        "scope": "two actual pinned ASCII shipping images; no build, variant, trace, fault injection, deep search or performance campaign",
        "helper_reuse": "byte-exact old strict helper, new candidate pins, declared ASCII-only command-admission accounting subclass",
        "variants": {}}
    def alarm(_signum, _frame):
        raise TimeoutError("global 180-second runtime campaign cap")
    signal.signal(signal.SIGALRM, alarm)
    signal.alarm(180)
    try:
        helper = load_helper(args.helper, out, sessions)
        original = {"main.rs": "8b72a5561b85ae87177198f08257ddfeca0fe954c6ca20ac74756b39c199723c",
            "board.rs": "f27472ea055b67e61cdd82a3d7747feced50c899bef72365ffdc940043dedef3", **OTHER}
        for name, expected in original.items():
            check(sha((args.stable / name).read_bytes()) == expected, "stable production input drift: " + name)
        report["original_seven_production_inputs_unchanged"] = True
        pins = {}
        # All image/source pins are validated before the first process starts.
        for label, image in (("hq", args.hq), ("scalar", args.scalar)):
            pin = helper.pin(image, label)
            check(pin["sha256"] == ELFS[label] and pin["bytes"] == 16816, "unreviewed actual candidate ELF: " + label)
            check(pin["source_sha256"] == EXPECTED, "candidate seven-input provenance differs: " + label)
            pins[label] = pin
        report["both_image_and_source_pins_validated_before_Popen"] = True
        for label, image in (("hq", args.hq), ("scalar", args.scalar)):
            lane = out / label
            lane.mkdir()
            report["variants"][label] = {"pin": pins[label]}
            report["variants"][label]["reused_strict_checks"] = helper.qualify(image, lane / "strict")
            report["variants"][label]["ascii_supplement"] = supplemental(helper, image, lane / "supplement")
        check(all(s.process.poll() is not None and not Path(f"/proc/{s.process.pid}").exists() for s in sessions), "owned process remained after checks")
        check(all(s.emergency_cleanup_needed is False for s in sessions), "successful check needed emergency cleanup")
        report["passed"] = True
    except BaseException as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        signal.alarm(0)
        for s in sessions:
            if s.process.poll() is None:
                try:
                    os.killpg(s.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                s.process.wait(timeout=5)
        report["owned_processes"] = [{"pid": s.process.pid, "returncode": s.process.poll(),
            "proc_absent": not Path(f"/proc/{s.process.pid}").exists(),
            "emergency_cleanup_needed": s.emergency_cleanup_needed} for s in sessions]
        save(out / "runtime.json", report)
    print(json.dumps({"passed": True, "report": str(out / "runtime.json"), "profiles": list(report["variants"])}))


if __name__ == "__main__":
    main()
