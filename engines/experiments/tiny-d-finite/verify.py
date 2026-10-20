#!/usr/bin/env python3
"""Manually admitted finite-D own ELFs: narrow physical runtime proof only.

TT bytes/exact budgets/synthetic completion are a separate units.py result.
Physical cases establish actual pools, mapped images, legal results and output
completion fences. No image hash is inferred from output or auto-updated.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import sys
import time

HERE = Path(__file__).resolve().parent
NATIVE_SHA = "1055c89f0f7bc042d33ad53ccad82fb9ca6a39368e6ed84dfd9e2a82fef24767"
COST_SHA = "53cb8a1fc1e9857d87e11c09bfc1ad0d61255784f427368f5940e0f4ab83a390"
HELPER_SHA = "045550ae095457923343fd5a462b47296f3749abf621a936329863cd5c69d252"
EXPECTED = {
    "scalar-shipping": {"native_bytes": 8348, "native_sha256": "0e21d39f5f294f496f2224595462661864b4a274f4c2238a38f47024f0c93bbf",
                        "bytes": 7540, "sha256": "26eaedc2560776a226a8e17886e209501346524e97fc2b47483f13335fbde013",
                        "audit_bytes": 7563, "audit_sha256": "02a6400574c166d89bc0e8c0b22b9b68097e50ff4524b182683b8e83856ba6c9", "entry": 4202279},
    "hq-shipping": {"native_bytes": 8736, "native_sha256": "6b987cc4f616ce9d835679c61d9aff8c0c16b59ec9a74db055c8ce826e14581f",
                    "bytes": 7800, "sha256": "3c863ceba32bf9173bf53d72f575c9e28e2ce2eb1cc43fde38bf03d6c9eff3ca",
                    "audit_bytes": 7823, "audit_sha256": "828d858a00cf03460a006b9162dfa6f8f2e3fc6aedab2bd3aa098ec75bb063fb", "entry": 4202596},
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def terminated(signum, frame):
    raise TimeoutError("finite-D physical validator SIGTERM")


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def best_lines(owned):
    return [s for s in owned.stdout.bytes().splitlines() if s.startswith(b"bestmove")]


def physical(helper, candidate, layout, native_sha, out, budget, oracle, shutdown, row):
    owned = helper.Owned(Path(candidate["path"]), out, budget)
    row.update(shutdown=shutdown, passed=False, cases=[], active_observations=[])
    histories, ready_count = [], 0
    try:
        tids = helper.stable_startup(owned)
        row["startup_tids"] = tids
        row["before_uci"] = helper.inspect(owned.process.pid, layout, native_sha, candidate["sha256"])
        owned.send(b"uci\nisready\n")
        owned.wait_line(b"uciok")
        ready_count += 1
        owned.wait_line(b"readyok", ready_count)

        def ready():
            nonlocal ready_count
            owned.send(b"isready\n")
            ready_count += 1
            owned.wait_line(b"readyok", ready_count)

        def position(history):
            command = "position startpos" + (" moves " + " ".join(history) if history else "") + "\n"
            owned.send(command.encode("ascii"))

        def issue(history, options):
            board = oracle.Board.from_fen()
            for name in history:
                board = board.play(name)
            legal = {str(m) for m in board.legal_moves()}
            require(legal, "physical fixture requires a live position")
            before = helper.tasks(owned.process.pid)
            require(sorted(before) == tids, "startup TIDs replaced")
            histories.append({"history": history, "legal": legal, "side": "white" if board.turn else "black"})
            owned.send(("go" + (" " + options if options else "") + "\n").encode("ascii"))
            return before

        def settled(count, label, seconds=5):
            owned.stdout.until(lambda data: sum(s.startswith(b"bestmove") for s in data.splitlines()) >= count, budget, seconds)
            lines = best_lines(owned)
            require(len(lines) == count, label + ": unexpected result count")
            match = re.fullmatch(rb"bestmove ([a-h][1-8][a-h][1-8][nbrq]?)", lines[-1])
            require(match and match.group(1).decode() in histories[count - 1]["legal"], label + ": illegal result")
            require(sorted(helper.tasks(owned.process.pid)) == tids, label + ": startup TIDs replaced")
            row["cases"].append({"case": label, "result_number": count, "move": match.group(1).decode(), "legal": True})

        def active(before, label):
            evidence = helper.physical_active(owned, tids, before)
            evidence["case"] = label
            require(len(best_lines(owned)) == len(histories) - 1, label + ": search had already settled")
            evidence["image"] = helper.inspect(owned.process.pid, layout, native_sha, candidate["sha256"])
            row["active_observations"].append(evidence)

        position([])
        started = time.monotonic()
        issue([], "")
        settled(1, "finite bare go")
        row["bare_go_observed_seconds"] = time.monotonic() - started
        position(["e2e4"])
        issue(["e2e4"], "wtime 3000 btime 0 winc 0 binc 0")
        settled(2, "black own-clock zero")
        position(["e2e4", "e7e5"])
        issue(["e2e4", "e7e5"], "wtime 3000 btime 3000 winc 0 binc 0")
        settled(3, "white clocked")

        first_history = ["d2d4", "g8f6", "c2c4"]
        position(first_history)
        before = issue(first_history, "wtime 600000 btime 600000 winc 0 binc 0")
        active(before, "before ignored controls")
        owned.send(b"stop\nucinewgame\n")
        ready()
        require(len(best_lines(owned)) == 3, "ignored controls settled an active epoch")
        active(before, "after ignored controls acknowledged")
        row["ignored_controls"] = {"actual_dispatch_acknowledged": True, "active_pool_observed_after_ready": True,
                                   "physical_tt_preservation": "unproven; actual TT bytes are checked separately by units.py"}

        issue(first_history, "wtime 0 btime 0")
        settled(5, "next go waits for old publication, then publishes its own result")
        ready()
        second_history = ["g1f3", "g8f6"]
        position(second_history)
        before = issue(second_history, "wtime 600000 btime 600000")
        active(before, "before position completion fence")
        position(["e2e4"])
        ready()
        require(len(best_lines(owned)) == 6, "position did not settle exactly the prior epoch")
        lines = owned.stdout.bytes().splitlines()
        result_indexes = [i for i, s in enumerate(lines) if s.startswith(b"bestmove")]
        ready_indexes = [i for i, s in enumerate(lines) if s == b"readyok"]
        require(result_indexes[-1] < ready_indexes[-1], "position acknowledgment preceded old result publication")
        row["position_completion"] = {"old_result_precedes_following_ready": True, "old_result_number": 6}
        issue(["e2e4"], "wtime 0 btime 0")
        settled(7, "new position black witness")

        before = issue(["e2e4"], "wtime 600000 btime 600000")
        active(before, "physical active " + shutdown)
        if shutdown == "quit":
            owned.send(b"quit\n")
        owned.close_input()
        row["settled"] = owned.finish()
        data = owned.stdout.bytes()
        results = best_lines(owned)
        require(data.endswith(b"\n") and len(results) == 8, "settled output is incomplete or has extra/missing results")
        for line, expected in zip(results, histories):
            match = re.fullmatch(rb"bestmove ([a-h][1-8][a-h][1-8][nbrq]?)", line)
            require(match and match.group(1).decode() in expected["legal"], "a settled result is malformed/illegal")
        require(data.splitlines().count(b"uciok") == 1 and data.splitlines().count(b"readyok") == ready_count, "acknowledgment count differs")
        require(not any(s.startswith(b"id ") or s.startswith(b"option ") for s in data.splitlines()), "finite shipping emitted optional interface")
        row.update(passed=True, exactly_one_legal_result_per_go=True, go_count=8,
                   startup_tids_persistent=True, only_stdio_descriptors=True, no_children_observed=True,
                   readers_joined=True, stdout_sha256=sha(data))
    finally:
        row["cleanup"] = owned.cleanup()
        if row.get("passed"):
            require(not row["cleanup"]["forced_cleanup"] and not row["cleanup"]["errors"]
                    and row["cleanup"]["owned_group_absent"] and row["cleanup"]["readers_joined"]
                    and row["cleanup"]["settled_before_cleanup"], "physical cleanup needed intervention")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-build", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True, help="approved first whole-file cost manifest")
    parser.add_argument("--oracle", type=Path, default=HERE.parents[1] / "tests/chess_oracle.py")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=120)
    args = parser.parse_args()
    out = args.out.resolve()
    require(args.out.is_absolute() and not out.exists() and not any((p / ".git").exists() for p in (out, *out.parents)), "new absolute external --out required")
    require(30 <= args.budget <= 180, "bounded budget required")
    out.mkdir(parents=True)
    report = {"complete": False, "scope": "actual finite own-ELF mapped image/pool/output-completion proof; TT bytes and exact clock arithmetic are separate nonphysical units",
              "results": [], "failures": [], "constructor_cleanup": []}
    helper, phase, started = None, "inputs", time.monotonic()
    prior_term = signal.signal(signal.SIGTERM, terminated)
    try:
        helper_path = HERE / "inputs/entry/verify.py"
        require(sha(helper_path.read_bytes()) == HELPER_SHA, "frozen physical helper differs")
        helper = module("finite_d_physical_helper", helper_path)
        native_bytes, cost_bytes, oracle_bytes = args.native_build.read_bytes(), args.build.read_bytes(), args.oracle.read_bytes()
        require(sha(native_bytes) == NATIVE_SHA and sha(cost_bytes) == COST_SHA, "approved native/cost checkpoint differs")
        require(sha(oracle_bytes.replace(b"\r\n", b"\n")) == helper.ORACLE_LF_SHA, "independent oracle differs")
        native, cost = json.loads(native_bytes), json.loads(cost_bytes)
        require(native["complete"] and cost["complete"] and cost["both_whole_files_strictly_smaller"], "incomplete first-cost approval inputs")
        require({r["id"] for r in cost["engines"]} == set(EXPECTED) and len(cost["engines"]) == 2, "expected exactly two new forms")
        recipe = out / "recipe"
        recipe.mkdir()
        for name, data in (("verify.py", Path(__file__).read_bytes()), ("helper.py", helper_path.read_bytes()),
                           ("native-build.json", native_bytes), ("cost-build.json", cost_bytes), ("chess_oracle.py", oracle_bytes)):
            (recipe / name).write_bytes(data)
        oracle = module("finite_d_oracle", recipe / "chess_oracle.py")
        report.update(native_manifest_sha256=NATIVE_SHA, cost_manifest_sha256=COST_SHA, helper_sha256=HELPER_SHA,
                      validator_sha256=sha(Path(__file__).read_bytes()), oracle_sha256=sha(oracle_bytes), manual_admission=EXPECTED)
        budget = helper.Budget(args.budget - (time.monotonic() - started))
        for engine in cost["engines"]:
            phase = engine["id"] + "/admission"
            expected, layout = EXPECTED[engine["id"]], engine["layout"]
            require(engine["input_sha256"] == expected["native_sha256"] and engine["input_bytes"] == expected["native_bytes"], "new native admission differs")
            native_spec = next(r for r in native["engines"] if r["id"] == engine["id"])
            path = Path(native_spec["native_repeats"][0]["path"])
            require(path.stat().st_size == expected["native_bytes"] and sha(path.read_bytes()) == expected["native_sha256"], "actual native input differs")
            require(layout["entry"] == expected["entry"] and layout["image_base"] == 0x400000 and layout["image_size"] == expected["native_bytes"] and layout["image_pages"] == 12288, "approved RX class/entry differs")
            require(layout["bss_base"] == 0x403000 and layout["bss_size"] == 175092 and layout["bss_pages"] == 176128 and layout["guard_base"] == 0x3ff000 and layout["upper_guard"] == 4382720, "approved BSS/guards differ")
            require(len(engine["candidates"]) == 1, "expected one selected fixed-codec own ELF")
            candidate = engine["candidates"][0]
            audit = candidate["audit"]
            require(candidate["codec"] == "fixed" and candidate["sha256"] == expected["sha256"] and candidate["bytes"] == expected["bytes"], "new own ELF admission differs")
            require(audit["sha256"] == expected["audit_sha256"] and audit["bytes"] == expected["audit_bytes"], "new audit admission differs")
            for tag, file, size, digest in (("native", path, expected["native_bytes"], expected["native_sha256"]),
                                           ("own", Path(candidate["path"]), expected["bytes"], expected["sha256"]),
                                           ("audit", Path(audit["path"]), expected["audit_bytes"], expected["audit_sha256"])):
                data = file.read_bytes()
                require(len(data) == size and sha(data) == digest, "actual admitted " + tag + " differs")
                (recipe / (engine["id"] + "-" + tag + ".elf")).write_bytes(data)
            row = {"engine": engine["id"], "own_elf_sha256": expected["sha256"], "native_sha256": expected["native_sha256"], "pre_entry": {}, "production": []}
            report["results"].append(row)
            phase = engine["id"] + "/checkpoint"
            helper.checkpoint(candidate, layout, expected["native_sha256"], out / engine["id"] / "checkpoint", budget, row["pre_entry"])
            for shutdown in ("quit", "EOF"):
                phase = engine["id"] + "/" + shutdown
                case = {}
                row["production"].append(case)
                physical(helper, candidate, layout, expected["native_sha256"], out / engine["id"] / shutdown, budget, oracle, shutdown, case)
        report["complete"] = True
    except BaseException as exc:
        report["complete"] = False
        report["failures"].append({"phase": phase, "type": type(exc).__name__, "detail": str(exc)})
    finally:
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        try:
            if helper:
                for owned in list(helper.OWNED):
                    try:
                        report["constructor_cleanup"].append(owned.cleanup())
                    except BaseException as exc:
                        report["failures"].append({"phase": phase + "/registered-cleanup", "type": type(exc).__name__, "detail": str(exc)})
                    report["complete"] = False
            report["elapsed_seconds"] = time.monotonic() - started
            (out / "results.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        finally:
            signal.signal(signal.SIGTERM, prior_term)
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
    print(json.dumps({"complete": report["complete"], "results": str(out / "results.json"), "failures": report["failures"]}))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
