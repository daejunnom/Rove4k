#!/usr/bin/env python3
"""Narrow ownership/query comparison of two exact frozen engine sources.

The C fixture owns query, transactional replay, and worker-entry assertions.
This runner compares every shared report field and permits exactly the stated
direct-think best reset difference. It performs no oracle, perft, games, SMP,
performance or package-size campaign. Outputs and frozen inputs stay external.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONTROL_SHA256 = "321ab861fe8e8ebc1791cbd389edbecc53091ede195e172e9983f2455ee12c6d"
CANDIDATE_SHA256 = "79284c72b64d087aa3127ea65b461aef8c7776355ea1c4ab9b2f81e59b4b48ed"
DIRECT_CASES = {"seed-prestopped", "seed-zero"}
PRESERVED_FLAGS = ("heuristics_preserved", "keys_loaded", "tail_keys_preserved", "counters_preserved",
                   "stopped_preserved")
QUERY_NAMES = ("start", "castle-white", "castle-black", "ep-white", "ep-black", "pinned-ep",
               "promotion-white", "promotion-black")
TRANSACTIONS = {"valid-replay": (True, 5), "invalid-middle": (False, 2),
                "invalid-after-prefix": (False, 2), "matched-pinned-move": (False, 2),
                "malformed-fen": (False, 2), "empty-move-list": (True, 1),
                "promotion-n": (True, 2), "promotion-b": (True, 2),
                "promotion-r": (True, 2), "promotion-q": (True, 2),
                "ep-replay": (True, 2), "castle-replay": (True, 3),
                "history-boundary-4095": (True, 4096), "history-overflow-4096": (False, 2)}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_report(report, candidate):
    require(isinstance(report, dict) and report.get("passed") is True,
            "fixture must report an asserted passing result")
    shared = report.get("shared")
    require(isinstance(shared, dict), "missing complete shared report")
    require(shared.get("query_stopped_unchanged") is True,
            "all NULL/text/invalid/terminal queries must preserve a pre-existing stop")
    queries = shared.get("queries")
    require(isinstance(queries, list) and len(queries) == 8,
            "exactly eight bounded nonterminal query positions are required")
    names = []
    matched = rejected = 0
    for query in queries:
        require(isinstance(query, dict) and isinstance(query.get("name"), str),
                "query position needs a name")
        names.append(query["name"])
        require(isinstance(query.get("board"), dict), "query report omitted its input board")
        legal = query.get("legal_queries")
        require(isinstance(legal, list) and legal, "nonterminal query position has no legal-query report")
        tokens = [entry["token"] for entry in legal]
        require(all(isinstance(token, str) for token in tokens) and len(set(tokens)) == len(tokens),
                "legal coordinate query tokens must be unique strings")
        for entry in legal:
            require(type(entry.get("move")) is int and entry["move"] != 0 and
                    isinstance(entry.get("child"), dict), "successful query omitted its complete made child")
        require(query.get("first") == legal[0]["move"],
                "NULL query must select the first legal move in unchanged generator order")
        require(query.get("first_child") == legal[0]["child"],
                "NULL-query child must equal the made first coordinate-query child")
        require(type(query.get("invalid_rejected")) is int and query["invalid_rejected"] == 24,
                "each query position must reject the same twenty-four invalid tokens")
        matched += len(legal)
        rejected += query["invalid_rejected"]
    require(len(set(names)) == len(names), "query position names are duplicated")
    require(tuple(names) == QUERY_NAMES, "bounded query position identity/order changed")
    require(shared.get("terminal_first") == 0, "terminal NULL-query must return no legal move")
    transactions = shared.get("transactions")
    require(isinstance(transactions, list) and len(transactions) == len(TRANSACTIONS),
            "all fourteen bounded transaction reports are required")
    require(len({item["name"] for item in transactions}) == len(transactions),
            "transaction names are duplicated")
    require({item["name"] for item in transactions} == TRANSACTIONS.keys(),
            "a required transaction identity is missing")
    for transaction in transactions:
        require(type(transaction.get("accepted")) is bool and
                type(transaction.get("length")) is int and transaction["length"] >= 1 and
                isinstance(transaction.get("board"), dict) and "keys_digest" in transaction,
                "transaction must retain acceptance, length, complete board and key digest")
        require((transaction["accepted"], transaction["length"]) == TRANSACTIONS[transaction["name"]],
                f"transaction acceptance/history boundary differs in {transaction['name']}")
    production = shared.get("production_think")
    require(isinstance(production, list) and len(production) == 2,
            "both production-owned pre-stopped and zero-iteration entry paths are required")
    require(len({item["case"] for item in production}) == 2, "production entry cases duplicated")
    require({item["case"] for item in production} == {"production-prestopped", "production-zero"},
            "required production stopped/zero-loop cases differ")
    for entry in production:
        require(all(entry.get(field) == 0 for field in ("best", "nodes", "depth", "score")),
                "production-owned search entry retained prior completion metadata")
        require(type(entry.get("resolved_fallback")) is int and entry["resolved_fallback"] != 0,
                "zero-iteration production entry must resolve its current legal fallback")
        require(all(entry.get(flag) is True for flag in PRESERVED_FLAGS),
                "production entry failed a preserved-resource contract")
        require(entry.get("id") == 7 and entry.get("length") == 3,
                "production worker identity/history prefix changed")
    direct = report.get("direct_think")
    require(isinstance(direct, list) and {item.get("case") for item in direct} == DIRECT_CASES and len(direct) == 2,
            "exactly the two deliberately preseeded direct-think cases are required")
    for entry in direct:
        require(type(entry.get("seed_best")) is int and entry["seed_best"] != 0,
                "direct-think proof requires a nonzero prior witness")
        require(entry.get("best") == (0 if candidate else entry["seed_best"]),
                "direct-think best does not match the explicit old/new ownership contract")
        require(all(entry.get(field) == 0 for field in ("nodes", "depth", "score")),
                "stopped/zero-iteration direct think changed completed search metadata")
        require(all(entry.get(flag) is True for flag in PRESERVED_FLAGS),
                "direct-think entry failed a preserved-resource contract")
        require(entry.get("id") == 7 and entry.get("length") == 3,
                "direct-think worker identity/history prefix changed")
    return {"query_positions": len(queries), "matched_coordinate_queries": matched,
            "invalid_queries_rejected": rejected, "transaction_cases": len(transactions),
            "production_think_cases": len(production), "direct_think_cases": len(direct)}


def compare_reports(control, candidate):
    require(candidate["shared"] == control["shared"],
            "complete shared query/transaction/production-entry reports differ")
    require([entry["case"] for entry in candidate["direct_think"]] ==
            [entry["case"] for entry in control["direct_think"]],
            "direct-think case order changed")
    old_cases = {entry["case"]: entry for entry in control["direct_think"]}
    new_cases = {entry["case"]: entry for entry in candidate["direct_think"]}
    differences = []
    for name in sorted(DIRECT_CASES):
        old, new = old_cases[name], new_cases[name]
        expected = dict(old)
        expected["best"] = 0
        require(new == expected, f"unexpected direct-think metadata difference in {name}")
        differences.append({"case": name, "field": "best", "control": old["best"],
                            "candidate": new["best"],
                            "meaning": "worker-entry ownership now clears the previous search witness"})
    # No other top-level field may vary silently.
    expected = dict(control)
    expected["direct_think"] = candidate["direct_think"]
    require(candidate == expected, "unexpected difference outside the two direct-think best fields")
    return {"complete_shared_report_equal": True,
            "only_expected_direct_think_differences": differences}


def execute(binary, directory):
    process = subprocess.Popen([str(binary)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=directory)
    cleanup = []
    try:
        stdout, stderr = process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        cleanup.append({"unknown_owned_pid_on_timeout": process.pid})
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            cleanup.append({"kill_owned_pid": process.pid})
            process.kill()
            stdout, stderr = process.communicate(timeout=1)
        (directory / "stdout.json").write_bytes(stdout)
        (directory / "stderr.log").write_bytes(stderr)
        return None, process.returncode, cleanup, "unknown: bounded fixture run timed out before cleanup"
    (directory / "stdout.json").write_bytes(stdout)
    (directory / "stderr.log").write_bytes(stderr)
    if process.returncode:
        return None, process.returncode, cleanup, f"fixture exited {process.returncode}"
    if stderr:
        return None, process.returncode, cleanup, "fixture or sanitizer wrote stderr"
    try:
        report = json.loads(stdout)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        return None, process.returncode, cleanup, f"incomplete or invalid sole JSON report: {error}"
    return report, process.returncode, cleanup, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, default=HERE / "query-contract.c")
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--asan", action="store_true", help="explicitly add candidate ASAN/UBSAN with the same fixture cases")
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("this bounded Linux fixture must run in WSL Ubuntu")
    output = args.out.resolve()
    if not args.out.is_absolute() or output.exists() or output == ROOT or ROOT in output.parents:
        parser.error("--out must be a new absolute external directory")
    if not args.control.is_absolute() or not args.candidate.is_absolute():
        parser.error("both engine source paths must be absolute")
    sources = {"control.c": args.control, "candidate.c": args.candidate,
               "query-contract.c": args.fixture, "query-check.py": Path(__file__)}
    if any(not path.is_file() for path in sources.values()):
        parser.error("both exact engine sources, fixture and runner must exist")
    if sha(args.control) != CONTROL_SHA256 or sha(args.candidate) != CANDIDATE_SHA256:
        parser.error("engine source identity differs from the exact authorized ownership candidate")
    output.mkdir(parents=True)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    frozen = output / "frozen"
    frozen.mkdir()
    for name, path in sources.items():
        shutil.copyfile(path, frozen / name)
    result = {"scope": "narrow query/ownership proof; no general rules, SMP, performance or package acceptance",
              "source_origin": {name: str(path.resolve()) for name, path in sources.items()},
              "source_sha256": {name: sha(frozen / name) for name in sources},
              "fixed_profile": {"workers": 2, "tt_bits": 18, "dev": 1},
              "profiles": [], "all_passed": False}
    profiles = [("control-o2", "control.c", False, False),
                ("candidate-o2", "candidate.c", True, False)]
    if args.asan:
        profiles.append(("candidate-asan", "candidate.c", True, True))
    control_report = None
    for name, source_name, candidate, sanitized in profiles:
        directory = output / name
        directory.mkdir()
        flags = (["-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie"]
                 if sanitized else ["-O2"])
        command = [args.cc, "-std=c11", "-DDEV=1", f"-DCANDIDATE={int(candidate)}",
                   "-DWORKERS=2", "-DTT_BITS=18", "-pthread", "-Wall", "-Wextra", *flags,
                   f'-DENGINE_SOURCE="{frozen / source_name}"', str(frozen / "query-contract.c"),
                   "-o", str(directory / "contract")]
        profile = {"name": name, "compile_command": command, "passed": False, "cleanup": []}
        result["profiles"].append(profile)
        began = time.monotonic()
        try:
            compiled = subprocess.run(command, capture_output=True, timeout=60, cwd=directory)
            (directory / "compile.stdout.log").write_bytes(compiled.stdout)
            (directory / "compile.stderr.log").write_bytes(compiled.stderr)
            profile["compile_returncode"] = compiled.returncode
            require(compiled.returncode == 0, "contract compilation failed")
            profile["program_sha256"] = sha(directory / "contract")
            report, code, cleanup, error = execute(directory / "contract", directory)
            profile["returncode"], profile["cleanup"] = code, cleanup
            require(error is None, error)
            profile["counts"] = validate_report(report, candidate)
            if candidate:
                require(control_report is not None, "control did not establish a complete passing report")
                profile["comparison"] = compare_reports(control_report, report)
            else:
                control_report = report
            profile["passed"] = True
        except Exception as error:
            profile["error"] = f"{type(error).__name__}: {error}"
        finally:
            profile["seconds"] = round(time.monotonic() - began, 6)
            (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(profile), flush=True)
    result["all_passed"] = all(profile["passed"] for profile in result["profiles"])
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    raise SystemExit(0 if result["all_passed"] else 1)


if __name__ == "__main__":
    main()
