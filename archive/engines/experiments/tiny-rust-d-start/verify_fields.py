#!/usr/bin/env python3
"""Two bounded std field-equivalence units per lane, never a shipping engine.

The frozen control/candidate Board bodies are compiled as separate modules.
This standalone harness does not import a producer, another experiment, or the
mutable maintained tree. Only ordinary runtime Board::start and Copy are used.
"""

if __name__ == "__main__":
    raise SystemExit("Rove4k Rust engine paths are retired; use C A-F")

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import signal
import subprocess
import time


HERE = Path(__file__).resolve().parent
ORIGINAL_BOARD = "1a1ff1a0693a1b3f53ade2435d2996684a1bcd7b7eee333f28fe669645340b82"
SOURCE_PINS = {
    "main.rs": "e10e1b797085c1f032edcbfe28a828cf91e8cf2c71f3f11c063328744c34b8a3",
    "board.rs": ORIGINAL_BOARD,
    "search.rs": "da2583806efea022b1b3b1337557b896a373a561f11d665b1ca747c29e3aed81",
    "runtime.rs": "802b497371a409744ad231cd8f621ea3d8b7cd931627e0396f3ec92ad1345b2d",
    "os.rs": "892cc62e2c126ebcbc171eb6f8059aacf92cf255d85341487e46effe2b94986e",
    "link.ld": "1e8f17bb2f06a6ddabf1f56d155bd7bdcd8c4406d140c22770bcfda96d459bbc",
    "build.py": "08f28ebdc45ad49c2a23f7eb8e28b086612ea9a33dbc39cb8ccbd66bfcf68e89",
}
NEW_START = """    pub fn start() -> Self {
        let mut b = Self::empty(); b.castle = 15;
        let back = [4, 2, 3, 5, 6, 3, 2, 4];
        for f in 0..8 {
            b.put(f, back[f]); b.put(f + 16, 1);
            b.put(f + 96, -1); b.put(f + 112, -back[f]);
        }
        b.hash ^= b.state(); b.context = b.hash; b
    }
"""
OUTPUT_CAP = 65536


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def source_proof(original, candidate):
    old, new = original.decode(), candidate.decode()
    begin_marker, end_marker = "    pub fn start() -> Self {\n", "    pub fn rebuild(&mut self) {\n"
    require(old.count(begin_marker) == new.count(begin_marker) == 1, "start signature drift")
    a, b = old.index(begin_marker), new.index(begin_marker)
    end_a, end_b = old.index(end_marker, a), new.index(end_marker, b)
    require(old[:a] == new[:b] and old[end_a:] == new[end_b:], "change outside ordinary start constructor")
    require(new[b:end_b] == NEW_START, "candidate differs from reviewed runtime put-only start")
    squares = [file + rank for file in range(8) for rank in (0, 16, 96, 112)]
    require(len(squares) == len(set(squares)) == 32 and all(s & 0x88 == 0 for s in squares), "non-disjoint or invalid target proof")
    return {"only_start_span_changed": True, "outside_start_bytes_identical": True,
            "old_start_sha256": sha(old[a:end_a].encode()), "new_start_sha256": sha(new[b:end_b].encode()),
            "generic_rebuild_put_value_and_other_bodies_exact": True,
            "no_const_marker_or_unsafe_or_indexing_change": True,
            "distinct_initial_empty_squares": squares,
            "semantic_argument": "All32put calls see old0; per-piece XOR/OR and bounded HCE additions reproduce rebuild. One king each, ep=-1 canonicalization is no-op, finalstate/context identical.",
            "score_absolute_sum_bound": 29120}


def run_owned(command, cwd, record_path, timeout, ledger):
    record = {"command": command, "cwd": str(cwd), "timeout_seconds": timeout,
              "combined_output_cap_bytes": OUTPUT_CAP, "terminal": False}
    ledger.append(record)
    start = time.monotonic()
    output = {"stdout": bytearray(), "stderr": bytearray()}
    selector = selectors.DefaultSelector()
    process = None
    try:
        process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
        record["pid_and_owned_pgid"] = process.pid
        for name in output:
            stream = getattr(process, name)
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map():
            remaining_time = timeout - (time.monotonic() - start)
            if remaining_time <= 0:
                raise TimeoutError("owned process deadline exceeded")
            for key, _ in selector.select(min(0.2, remaining_time)):
                chunk = os.read(key.fileobj.fileno(), 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                remaining = OUTPUT_CAP - sum(map(len, output.values()))
                output[key.data].extend(chunk[:max(remaining, 0)])
                if len(chunk) > remaining:
                    raise RuntimeError("combined output cap exceeded")
        process.wait(timeout=5)
    except BaseException as error:
        record["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        if process is not None:
            try:
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=5)
            except BaseException as error:
                record["cleanup_error"] = {"type": type(error).__name__, "message": str(error)}
            record["returncode"] = process.poll()
            record["terminal"] = process.poll() is not None
            for name in output:
                stream = getattr(process, name)
                if stream is not None:
                    stream.close()
        selector.close()
        record.update(seconds=time.monotonic() - start,
                      **{name: data.decode("utf-8", "replace") for name, data in output.items()})
        save(record_path, record)
    require(record.get("returncode") == 0 and record["terminal"]
            and "error" not in record and "cleanup_error" not in record,
            "owned diagnostic process failed; see " + str(record_path))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-dir", required=True, type=Path)
    parser.add_argument("--candidate-dir", required=True, type=Path)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--rustc", default="rustc")
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        parser.error("Linux x86-64 std diagnostics required")
    if not all(path.is_absolute() for path in (args.control_dir, args.candidate_dir, args.out)):
        parser.error("absolute source and output directories required")
    control, candidate, out = args.control_dir.resolve(), args.candidate_dir.resolve(), args.out.resolve()
    checkouts = {p for anchor in (HERE, control, candidate) for p in (anchor, *anchor.parents)
                 if (p / ".git").exists()}
    if out.exists() or any(out == p or p in out.parents for p in (control, candidate, *checkouts)):
        parser.error("new external output separate from input sources required")
    if not re.fullmatch("[0-9a-f]{64}", args.candidate_sha256):
        parser.error("lowercase exact candidate board SHA-256 required")
    compiler = shutil.which(args.rustc)
    if compiler is None:
        parser.error("controlled Rust compiler unavailable")
    out.mkdir(parents=True)
    ledger = []
    report = {"passed": False, "scope": "two focused ordinary-runtime std Board::start/Copy units per lane",
              "shipping_engine_executed": False, "raw_runtime_or_search_compiled": False,
              "const_factory_or_initializer_substitution_used": False,
              "external_source_dirs": {"control": str(control), "candidate": str(candidate)},
              "lanes": {}, "owned_execution_handles_terminal": False}
    try:
        old = {name: (control / name).read_bytes() for name in SOURCE_PINS}
        new = {name: (candidate / name).read_bytes() for name in SOURCE_PINS}
        require({name: sha(data) for name, data in old.items()} == SOURCE_PINS, "frozen control input drift")
        require(sha(new["board.rs"]) == args.candidate_sha256, "candidate board pin drift")
        require(all(new[name] == old[name] for name in SOURCE_PINS if name != "board.rs"), "candidate changed other six inputs")
        report["control_source_sha256"] = {name: sha(data) for name, data in old.items()}
        report["candidate_source_sha256"] = {name: sha(data) for name, data in new.items()}
        report["source_proof_before_any_compiler"] = source_proof(old["board.rs"], new["board.rs"])
        tests = (HERE / "tests.rs.in").read_bytes()
        report["harness_sha256"] = {"verify_fields.py": sha(Path(__file__).read_bytes()), "tests.rs.in": sha(tests)}
        (out / "verify_fields.py").write_bytes(Path(__file__).read_bytes())
        (out / "tests.rs.in").write_bytes(tests)
        prefix = b'''#![allow(dead_code)]
#[path="original-board.rs"] mod original;
#[path="candidate-board.rs"] mod candidate;
pub const HQ:bool=cfg!(fields_hq);
'''
        driver = prefix + tests
        report["driver_sha256"] = sha(driver)
        report["compiler"] = run_owned([compiler, "--version", "--verbose"], out, out / "compiler.json", 10, ledger)["stdout"]
        previous = None
        for lane in ("hq", "scalar"):
            local = out / lane; local.mkdir()
            (local / "original-board.rs").write_bytes(old["board.rs"])
            (local / "candidate-board.rs").write_bytes(new["board.rs"])
            (local / "driver.rs").write_bytes(driver)
            command = [compiler, "--edition=2024", "--test", "-C", "opt-level=0", "-C", "debuginfo=0",
                       "--check-cfg", "cfg(fields_hq)", "driver.rs", "-o", "field-tests"]
            if lane == "hq": command[1:1] = ["--cfg", "fields_hq"]
            run_owned(command, local, local / "compile.json", 120, ledger)
            execution = run_owned([str(local / "field-tests"), "--test-threads=1", "--nocapture"],
                                  local, local / "execution.json", 15, ledger)
            require(re.search(r"test result: ok\. 2 passed; 0 failed;", execution["stdout"]), "incomplete field test count")
            metrics = {name: int(value) for name, value in re.findall(r"QUAL_METRIC ([a-z0-9_]+)=([0-9]+)", execution["stdout"])}
            require(metrics == {"compared_field_elements": 151, "named_fields": 10,
                                "copy_independence_implementations": 2, "copied_named_fields_mutated": 20},
                    "field coverage incomplete")
            boards = {name: json.loads(value) for name, value in re.findall(r"QUAL_BOARD (original|candidate) (\{[^\n]+\})", execution["stdout"])}
            require(set(boards) == {"original", "candidate"} and boards["original"] == boards["candidate"], "recorded field values differ")
            if previous is not None: require(previous == boards, "scalar/HQ field outputs differ")
            previous = boards
            report["lanes"][lane] = {"passed": True, "std_diagnostic_elf_sha256": sha((local / "field-tests").read_bytes()),
                                      "std_diagnostic_distinct_from_shipping": True, "board_sources_exact": True,
                                      "ordinary_runtime_calls": "opaque black_box fn pointers, inline(never) driver wrappers, opt-level=0; no manual/const substitute",
                                      "driver_sha256": sha(driver), "metrics": metrics, "field_values": boards,
                                      "compile_record": str(local / "compile.json"), "execution_record": str(local / "execution.json")}
            save(out / "report.json", report)
        require(all(r["terminal"] for r in ledger), "owned process cleanup not confirmed")
        require(all((control / n).read_bytes() == old[n] and (candidate / n).read_bytes() == new[n] for n in SOURCE_PINS), "frozen source changed during diagnostic")
        report.update(passed=True, scalar_hq_field_values_identical=True,
                      excluded="No shipping ELF/runtime/packed payload/search/perft/strength or benchmark execution")
    except BaseException as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        report["owned_execution_handles_terminal"] = all(r.get("terminal") is True for r in ledger)
        report["owned_processes"] = [{k: r.get(k) for k in ("pid_and_owned_pgid", "returncode", "terminal", "error", "cleanup_error")} for r in ledger]
        save(out / "report.json", report)
    print(json.dumps({"passed": True, "report": str(out / "report.json"), "tests_per_lane": 2,
                      "owned_handles_terminal": report["owned_execution_handles_terminal"]}))


if __name__ == "__main__":
    main()
