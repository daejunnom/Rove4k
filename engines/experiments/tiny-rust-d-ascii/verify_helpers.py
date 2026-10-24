#!/usr/bin/env python3
"""Run two bounded std helper diagnostics; never execute a shipping engine ELF.

Candidate board and input helpers are exact frozen shipping-source bytes. Old
position/limits and the old board are separate exact preserved source oracles.
Only search::Limits/PLY are stubbed. This is not no_std/runtime/search/deep QA.
"""
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
PINS = {
    "candidate_main": "e10e1b797085c1f032edcbfe28a828cf91e8cf2c71f3f11c063328744c34b8a3",
    "candidate_board": "1a1ff1a0693a1b3f53ade2435d2996684a1bcd7b7eee333f28fe669645340b82",
    "original_main": "8b72a5561b85ae87177198f08257ddfeca0fe954c6ca20ac74756b39c199723c",
    "original_board": "f27472ea055b67e61cdd82a3d7747feced50c899bef72365ffdc940043dedef3",
}
ELFS = {
    "hq": "f8581a68f09d4d9cdc3e1413aa45ffb385bafd8240f1432403629ec2a0e544f8",
    "scalar": "bd0e3bd1567ae906d4ab9704603204d22302895df1f05679f6221d6445aef878",
}
FILES = ("main.rs", "board.rs", "search.rs", "runtime.rs", "os.rs", "link.ld", "build.py")
EXPECTED_TESTS = 7
OUTPUT_CAP = 131072


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def run_owned(command, cwd, timeout):
    """Incremental output cap and owned process-group deadline/cleanup."""
    start = time.monotonic()
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    selector = selectors.DefaultSelector()
    output = {"stdout": bytearray(), "stderr": bytearray()}
    for name in output:
        stream = getattr(process, name)
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, name)
    error = None
    try:
        while selector.get_map():
            if time.monotonic() - start >= timeout:
                error = "deadline exceeded"
                break
            for key, _ in selector.select(max(0.0, min(0.2, timeout - (time.monotonic() - start)))):
                chunk = os.read(key.fileobj.fileno(), 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                remaining = OUTPUT_CAP - sum(map(len, output.values()))
                output[key.data].extend(chunk[:max(remaining, 0)])
                if len(chunk) > remaining:
                    error = "combined output cap exceeded"
                    break
            if error:
                break
        if error:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
        selector.close()
        for name in output:
            getattr(process, name).close()
    return {"command": command, "cwd": str(cwd), "pid_and_owned_pgid": process.pid,
            "returncode": process.returncode, "seconds": time.monotonic() - start,
            "timeout_seconds": timeout, "combined_output_cap_bytes": OUTPUT_CAP,
            "error": error, "owned_process_terminal": process.poll() is not None,
            **{name: data.decode("utf-8", "replace") for name, data in output.items()}}


def extract(main, start):
    require(main.count(start) == 1, "helper start marker drift")
    begin = main.index(start)
    end = main.index(b"#[unsafe(no_mangle)]", begin)
    return main[begin:end]


def driver(candidate_helpers, original_helpers, tests):
    prefix = b'''#![allow(dead_code)]
#[path="candidate-board.rs"] mod board;
#[path="original-board.rs"] mod original_board;
use board::Board;
mod search {
    pub const PLY:usize=128;
    #[derive(Clone,Copy,Debug,PartialEq,Eq)]
    pub struct Limits {pub depth:u8,pub nodes:u64,pub millis:Option<u64>}
}
use search::Limits;
pub const HQ:bool=cfg!(helper_hq);
'''
    old_prefix = b'''\nmod old {
use super::original_board::Board;
use super::{Limits,search};
'''
    old_suffix = b'''
pub fn position_reference(words:&[&str])->Option<(Board,[u64;4096],usize)> {position(words)}
pub fn limits_reference(board:&Board,words:&[&str])->Limits {limits(board,words)}
}
'''
    return prefix + candidate_helpers + old_prefix + original_helpers + old_suffix + tests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cost-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--rustc", default="rustc")
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        parser.error("Linux x86-64 std diagnostics required")
    if not args.cost_dir.is_absolute() or not args.out.is_absolute():
        parser.error("absolute cost input and output required")
    cost, out = args.cost_dir.resolve(), args.out.resolve()
    if out.exists() or out == cost or cost in out.parents or HERE in out.parents:
        parser.error("new external output separate from cost inputs required")
    compiler = shutil.which(args.rustc)
    if compiler is None:
        parser.error("Rust compiler unavailable")
    out.mkdir(parents=True)
    report = {"passed": False, "scope": "focused std diagnostic helpers only",
              "shipping_engine_elf_executed": False, "search_implementation_compiled": False,
              "actual_runtime_main_or_OS_implementation_executed": False,
              "std_diagnostic_distinct_from_shipping_no_std_artifact": True,
              "owned_execution_sessions_terminal": False, "lanes": {}}
    save(out / "report.json", report)
    try:
        cost_report = json.loads((cost / "cost.json").read_text())
        require(cost_report["passed"], "FIRST-COST did not pass")
        tests = (HERE / "tests.rs.in").read_bytes()
        report["harness_sha256"] = {"verify_helpers.py": sha(Path(__file__).read_bytes()),
                                     "tests.rs.in": sha(tests)}
        (out / "verify_helpers.py").write_bytes(Path(__file__).read_bytes())
        (out / "tests.rs.in").write_bytes(tests)
        version = run_owned([compiler, "--version", "--verbose"], out, 10)
        save(out / "compiler.json", version)
        require(version["returncode"] == 0 and not version["error"], "compiler version failed")
        report["compiler"] = version["stdout"]
        for lane in ("hq", "scalar"):
            root = out / lane; root.mkdir()
            candidate_dir, original_dir = cost / ("candidate-" + lane) / "first", cost / ("control-" + lane) / "first"
            candidate = {name: (candidate_dir / name).read_bytes() for name in FILES}
            original = {name: (original_dir / name).read_bytes() for name in FILES}
            for role, files in (("candidate", candidate), ("original", original)):
                for kind in ("main", "board"):
                    require(sha(files[kind + ".rs"]) == PINS[role + "_" + kind], role + " " + kind + " source pin drift")
            require(all(candidate[name] == original[name] for name in FILES if name not in ("main.rs", "board.rs")),
                    "engine core/recipe changed")
            candidate_hashes = {name: sha(data) for name, data in candidate.items()}
            require(candidate_hashes == cost_report["builds"]["candidate-" + lane]["source_sha256"],
                    "candidate snapshot differs from compiled FIRST-COST input")
            elf = (candidate_dir / "x").read_bytes()
            require(len(elf) == 16816 and sha(elf) == ELFS[lane], "shipping ELF identity differs")
            helpers = extract(candidate["main.rs"], b"fn whitespace(")
            old_helpers = extract(original["main.rs"], b"fn position(")
            require(b"if line.iter().any(|&b|b==0||!b.is_ascii()){continue;}" in candidate["main.rs"],
                    "whole-line policy gate source witness changed")
            generated = driver(helpers, old_helpers, tests)
            for name, data in (("candidate-board.rs", candidate["board.rs"]), ("original-board.rs", original["board.rs"]),
                               ("candidate-main.rs", candidate["main.rs"]), ("original-main.rs", original["main.rs"]),
                               ("candidate-helpers.rs", helpers), ("original-helpers.rs", old_helpers), ("driver.rs", generated)):
                (root / name).write_bytes(data)
            lane_report = {
                "shipping_elf_sha256_source_identity_only_never_executed": ELFS[lane],
                "candidate_source_sha256": candidate_hashes,
                "original_source_sha256": {name: sha(data) for name, data in original.items()},
                "candidate_helpers_sha256": sha(helpers), "original_helpers_sha256": sha(old_helpers),
                "driver_sha256": sha(generated), "candidate_board_exact": True, "original_board_exact": True,
                "candidate_helpers_verbatim": True, "original_functions_verbatim_with_separate_module_wrappers": True,
                "std_stub_only": "search::Limits with original field types and PLY=128; no search body, control, raw runtime, OS, or main",
                "policy_scope": "NUL/nonASCII full-line pre-dispatch gate is source-witnessed, not executed by helper image; Words/unsigned tests may inspect rejected bytes in isolation",
            }
            report["lanes"][lane] = lane_report
            command = [compiler, "--edition=2024", "--test", "-C", "opt-level=1", "-C", "debuginfo=0",
                       "--check-cfg", "cfg(helper_hq)", "driver.rs", "-o", "helper-tests"]
            if lane == "hq":
                command[1:1] = ["--cfg", "helper_hq"]
            compilation = run_owned(command, root, 120)
            save(root / "compile.json", compilation)
            require(compilation["returncode"] == 0 and not compilation["error"], "std compilation failed: " + lane)
            lane_report["std_diagnostic_elf_sha256"] = sha((root / "helper-tests").read_bytes())
            execution = run_owned([str(root / "helper-tests"), "--test-threads=1", "--nocapture"], root, 30)
            save(root / "execution.json", execution)
            require(execution["returncode"] == 0 and not execution["error"], "std tests failed: " + lane)
            require(re.search(r"test result: ok\. " + str(EXPECTED_TESTS) + r" passed; 0 failed;", execution["stdout"]),
                    "unexpected or incomplete focused test count: " + lane)
            metrics = {name: int(value) for name, value in re.findall(r"QUAL_METRIC ([a-z0-9_]+)=([0-9]+)", execution["stdout"])}
            require(metrics.get("unsigned_ascii_pairs") == 16512 and metrics.get("token_ascii_pairs") == 16512
                    and metrics.get("maximum_line_tokens") == 16384 and metrics.get("position_history_boundary_cases") == 2
                    and metrics.get("special_move_expectations") == 19 and metrics.get("byte_parser_fixture_boards") == 9,
                    "required focused metrics missing: " + lane)
            lane_report.update(passed=True, focused_test_count=EXPECTED_TESTS, metrics=metrics,
                               compile_record=str(root / "compile.json"), execution_record=str(root / "execution.json"))
            save(out / "report.json", report)
        require(report["lanes"]["hq"]["metrics"] == report["lanes"]["scalar"]["metrics"], "lane coverage differs")
        report.update(passed=True, owned_execution_sessions_terminal=True,
                      excluded="No broad perft/HQ matrix/search/deep/strength/benchmark or shipping raw-runtime requalification")
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        report["owned_execution_sessions_terminal"] = True
        raise
    finally:
        save(out / "report.json", report)
    print(json.dumps({"passed": True, "report": str(out / "report.json"),
                      "tests_per_lane": EXPECTED_TESTS, "all_owned_sessions_terminal": True}))


if __name__ == "__main__":
    main()
