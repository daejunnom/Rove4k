#!/usr/bin/env python3
"""Actual scalar D shipping-board legal sets against the independent oracle.

Reproduce D's readable source/proof and its preprocessing/minification before
including the actual shipping board.c in a libc test driver. No native entry,
raw-clone runtime, TT allocation or search is executed by this rules fixture.
Those remain separate runtime/initialization qualifications.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCHEMA = "rove4k.D-generated-rules.v1"


def load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def modules():
    return (load("d_rules_shared_fixture", ROOT / "engines/experiments/tcec-next/profile_rules.py"),
            load("d_rules_source", HERE / "source.py"),
            load("d_rules_builder_flags", HERE / "build.py"),
            load("d_rules_minifier", ROOT / "engines/scripts/minify.py"),
            load("d_rules_renamer", ROOT / "engines/scripts/rename_c.py"))


def render_board_fixture(shared, board, renames, cases):
    shared.require(not set(renames).intersection({"memcpy", "memset", "strlen", "strcmp", "strtok_r", "abort"}),
                   "renamed libc boundary needs a separately reviewed fixture binding")
    declarations = b"\n"
    if "size_t" in renames:
        declarations += ("typedef " + renames["size_t"] + " size_t;\n").encode()
    declarations += b'extern int printf(const char *,...);extern int puts(const char *);extern char *strcpy(char *,const char *);\n'
    return shared.render_bound_fixture(board,
        dict(board=renames.get("Board", "Board"), start=renames.get("start", "start"),
             generate=renames.get("gen", "gen"), make=renames.get("make", "make"), four_args=False),
        cases, declarations)


def prepared_sources(record, build, source, shared):
    """Replay only the finite declared D source/storage stages, in order."""
    require, pin = shared.require, shared.pin
    require(record.get("source_reduced", False) is False,
            "D optional source-reduction stage needs separate rules admission")
    files, proof = source.prepare(source.production().resource_profile(record["resource"]["id"]),
                                  equivalent_edits=record["equivalent_edits"])
    declared = record["proof"]
    require(all(declared.get(key) == proof[key] for key in
        ("input_sources", "recipe", "fused", "dynamic_TT", "cleanup_policy", "model", "resource",
         "source_edits", "test_only", "equivalent_edits", "outputs")),
        "D rules current source derivation differs")
    mode = record.get("storage", "none")
    require(mode in ("none", "prefix", "dense", "prefix-dense"), "explicit finite D storage mode required")
    if mode == "none":
        require("storage" not in declared, "undeclared D storage proof stage")
        return files, proof
    relative = "engines/experiments/tiny-d-submission/storage.py"
    frozen = shared._evidence_bytes(Path(build) / "inputs" / relative, name="storage.py")
    require(record.get("inputs", {}).get(relative) == pin(frozen), "D frozen storage tool identity differs")
    storage = load("d_rules_finite_storage", HERE / "storage.py")
    before = files
    files, storage_proof = storage.transform(before, prefix="prefix" in mode, dense="dense" in mode)
    require(storage_proof == declared.get("storage") and storage.restore(files, storage_proof) == before and
            all(files[name] == data for name, data in before.items() if name not in ("tiny.h", "search.c")),
            "D full storage proof/inverse or protected source files differ")
    return files, proof


def receipt_fixture(report, *, profile, main_source, source_proof, build, cases,
                    commands, outputs, probe, compiler):
    """Pure D adapter used by the common stored-receipt validator."""
    shared, source, builder, minifier, renamer = modules()
    require, pin, evidence = shared.require, shared.pin, shared._evidence_bytes
    build = Path(build)
    build_bytes = evidence(build / "build.json", name="build.json")
    record = json.loads(build_bytes)
    require(report.get("build") == pin(build_bytes) and record.get("complete") is True and
            record.get("native_reproduced") is True and
            record.get("format") == "rove4k-D-general-source-v1" and record.get("family") == "D" and
            record.get("resource") == profile.to_record(16) and record.get("proof") == source_proof,
            "D rules receipt build/full proof identity differs")
    files, proof = prepared_sources(record, build, source, shared)
    if record.get("storage", "none") != "none":
        require(report.get("storage") == {"mode": record["storage"],
            "proof": pin(json.dumps(source_proof["storage"], sort_keys=True).encode())},
            "D rules receipt explicit storage mode/proof binding differs")
    for name, data in files.items():
        require(evidence(build / "generated-readable" / name, name=name) == data,
                "D rules receipt current readable source differs: " + name)
    flags = record["flags"]
    require(flags and flags[0] in ("-Os", "-Oz", "-O2") and
            flags == builder.native_flags(profile, flags[0][2:]),
            "D rules receipt flags differ from the explicit profile")
    require(record.get("units") == ["main.c", "start.S"] and
            record.get("single_TU", {}).get("members") == ["board.c", "search.c", "runtime.c"] and
            evidence(build / "shipping-inputs/main.c", name="main.c") == main_source and
            pin(main_source) == record["shipping_inputs"]["main.c"] == report.get("shipping_main"),
            "D rules receipt actual shipping single-TU source differs")
    aggregate = b''.join(('#include "' + name + '"\n').encode()
                         for name in record["single_TU"]["members"])
    require(pin(aggregate) == record["single_TU"]["driver"] and
            evidence(probe / "source-driver.c", name="source-driver.c") == aggregate and
            commands[0].get("command") == [compiler, "-E", "-P", *flags, "-I",
                str(build / "generated-readable"), "-x", "c", str(probe / "source-driver.c")] and
            commands[1].get("command") == [compiler, "-E", "-P", *flags,
                str(build / "generated-readable/board.c")],
            "D rules receipt exact preprocessor input/commands differ")
    renames = record.get("identifier_native_gate", {}).get("accepted_renames", {})
    require(isinstance(renames, dict) and all(
        isinstance(old, str) and isinstance(new, str) and
        re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", old) and
        re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", new)
        for old, new in renames.items()), "D receipt finite lexical renames required")
    def renamed(data):
        result = {"main.c": data}
        for old, new in renames.items():
            result = renamer._replace(result, old, new)
        return result["main.c"]
    whole_pp = outputs["D-rules-preprocess-actual-single-TU"]
    require(pin(whole_pp) == record["single_TU"]["preprocessed"] and
            renamed(minifier.compact_source(whole_pp, "c")) == main_source,
            "D entire actual shipping source no longer reproduces")
    board = renamed(minifier.compact_source(outputs["D-rules-preprocess-actual-board"], "c")).rstrip(b"\n")
    require(main_source.startswith(board) and board.endswith(b"}") and
            report.get("shipping_board_prefix") == pin(board) and
            report.get("readable_board") == pin(files["board.c"]) and
            report.get("shipping_preprocessing_reproduced") is True,
            "D actual shipping board prefix/readable derivation differs")
    return render_board_fixture(shared, board, renames, cases)


def verify_generated_rules(build: Path, out: Path, *, run_command, compiler="cc",
                           equivalent_edits=True):
    shared, source, builder, minifier, renamer = modules()
    require, pin = shared.require, shared.pin
    build, out = Path(build).resolve(), Path(out).resolve()
    require(build.is_absolute() and build.is_dir() and out.is_absolute() and not out.exists()
            and not any((p / ".git").exists() for p in (out, *out.parents)),
            "explicit build and new absolute rules output outside every checkout required")
    record = json.loads((build / "build.json").read_text())
    require(record.get("format") == "rove4k-D-general-source-v1" and
            record.get("family") == "D" and record.get("complete") is True and
            record.get("native_reproduced") is True,
            "complete source-owned scalar D generation/reproduction required")
    profile = source.production().resource_profile(record["resource"]["id"])
    require(record["resource"] == profile.to_record(16), "D resource record differs")
    require(record.get("equivalent_edits") is equivalent_edits, "explicit D equivalent-edit mode differs")
    files, proof = prepared_sources(record, build, source, shared)
    for name, data in files.items():
        path = build / "generated-readable" / name
        require(not path.is_symlink() and path.read_bytes() == data,
                "D readable generation differs: " + name)
    flags = record["flags"]
    require(flags and flags[0] in ("-Os", "-Oz", "-O2") and
            flags == builder.native_flags(profile, flags[0][2:]),
            "D preprocessor flags differ from the explicit profile")
    require(record.get("units") == ["main.c", "start.S"] and
            record.get("single_TU", {}).get("members") == ["board.c", "search.c", "runtime.c"],
            "explicit board-first single-TU D source class required")
    shipping = build / "shipping-inputs/main.c"
    require(not shipping.is_symlink(), "D shipping input must not be a link")
    actual = shipping.read_bytes()
    require(pin(actual) == record["shipping_inputs"]["main.c"],
            "D actual shipping single-TU source identity differs")
    renames = record.get("identifier_native_gate", {}).get("accepted_renames", {})
    require(isinstance(renames, dict) and all(
        isinstance(old, str) and isinstance(new, str) and
        re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", old) and
        re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", new)
        for old, new in renames.items()), "finite lexical identifier mapping required")
    def renamed(data):
        result = {"main.c": data}
        for old, new in renames.items():
            result = renamer._replace(result, old, new)
        return result["main.c"]
    cases, coverage = shared.fixture_cases()
    require(callable(run_command), "an owned bounded command runner is required")
    out.mkdir(parents=True)
    (out / "cases.json").write_text(json.dumps(
        [{k: value for k, value in case.items() if k != "board"} for case in cases],
        indent=2) + "\n")
    report = {"format": SCHEMA, "family": "D", "profile": profile.to_record(16),
              "build": pin((build / "build.json").read_bytes()), "shipping_main": pin(actual),
              "readable_board": pin(files["board.c"]),
              "oracle": {"path": shared.ORACLE, "sha256": shared.ORACLE_SHA},
              "coverage": coverage, "complete": False, "modes": [],
              "TT_allocated": False, "native_entry_called": False,
              "scope": "actual preprocessed scalar D start/gen/make legal sets; libc supplies fixture memory primitives",
              "not_proven": ["raw syscall/runtime or custom memory primitive implementation",
                             "TT initialization and resource execution", "search, protocol and tournament qualification",
                             "exhaustive chess correctness and playing strength"],
              "verifier_inputs": {relative: pin(shared.normalized(path)) for relative, path in (
                  ("engines/experiments/tiny-d-submission/profile_rules.py", Path(__file__)),
                  ("engines/experiments/tcec-next/profile_rules.py", ROOT / "engines/experiments/tcec-next/profile_rules.py"),
                  ("engines/experiments/tiny-d-submission/source.py", HERE / "source.py"),
                  ("engines/experiments/tiny-d-submission/build.py", HERE / "build.py"),
                  ("engines/scripts/minify.py", ROOT / "engines/scripts/minify.py"),
                  ("engines/scripts/rename_c.py", ROOT / "engines/scripts/rename_c.py"))}}
    if record.get("storage", "none") != "none":
        report["storage"] = {"mode": record["storage"],
            "proof": pin(json.dumps(record["proof"]["storage"], sort_keys=True).encode())}
        relative = "engines/experiments/tiny-d-submission/storage.py"
        report["verifier_inputs"][relative] = pin(shared.normalized(HERE / "storage.py"))
    def save():
        (out / "rules.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    try:
        aggregate = b''.join(('#include "' + name + '"\n').encode()
                             for name in record["single_TU"]["members"])
        require(pin(aggregate) == record["single_TU"]["driver"], "D single-TU driver differs")
        (out / "source-driver.c").write_bytes(aggregate)
        whole_pp = run_command([compiler, "-E", "-P", *flags,
                                "-I", str(build / "generated-readable"),
                                "-x", "c", str(out / "source-driver.c")],
                               cwd=out, kind="D-rules-preprocess-actual-single-TU")
        require(pin(whole_pp) == record["single_TU"]["preprocessed"] and
                renamed(minifier.compact_source(whole_pp, "c")) == actual,
                "D entire actual shipping unit does not reproduce")
        preprocessed = run_command([compiler, "-E", "-P", *flags,
                                    str(build / "generated-readable/board.c")],
                                   cwd=out, kind="D-rules-preprocess-actual-board")
        board = renamed(minifier.compact_source(preprocessed, "c")).rstrip(b"\n")
        require(actual.startswith(board) and board.endswith(b"}"),
                "D board must be the exact complete function prefix of the actual shipping unit")
        fixture = render_board_fixture(shared, board, renames, cases)
        (out / "fixture.c").write_bytes(fixture)
        report["shipping_board_prefix"] = pin(board)
        report["fixture"] = pin(fixture)
        report["shipping_preprocessing_reproduced"] = True
        for mode, sanitizers in (("plain", []), ("ubsan", ["-fsanitize=undefined", "-fno-sanitize-recover=all"])):
            program = out / ("probe-" + mode)
            run_command([compiler, "-std=c11", "-O1", "-g0", "-fno-builtin",
                         "-msse4.2", "-mcx16", *sanitizers,
                         str(out / "fixture.c"), "-o", str(program)],
                        cwd=out, kind="D-rules-compile-" + mode)
            output = run_command([str(program)], cwd=out, kind="D-rules-execute-" + mode)
            report["modes"].append({"mode": mode, "native": pin(program.read_bytes()),
                                    **shared._compare_output(output, cases)})
            save()
        report["complete"] = True
        return report
    except BaseException as error:
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--control", action="store_true")
    args = parser.parse_args()
    shared, source, _, _, _ = modules()
    require = shared.require
    require(sys.platform == "linux" and args.build.is_absolute() and args.out.is_absolute(),
            "Linux and absolute build/output paths required")
    out = args.out.resolve()
    require(not out.exists() and not any((p / ".git").exists() for p in (out, *out.parents)),
            "new output outside every checkout required")
    owner_path = ROOT / shared.HOST
    require(shared.pin(shared.normalized(owner_path))["sha256"] == shared.HOST_SHA,
            "bounded command owner differs")
    owner = load("d_rules_command_owner", owner_path)
    owner.LIMITS = {**owner.LIMITS, "aggregate_wall": 180, "per_command_wall": 45,
                    "parent_CPU": 100, "parent_CPU_hard": 120, "child_CPU": 40}
    out.mkdir()
    record = {"format": SCHEMA + ".commands", "complete": False, "commands": []}
    def save():
        (out / "commands.json").write_text(json.dumps(record, indent=2) + "\n")
    save()
    host = owner.Host(out, record, save)
    try:
        result = verify_generated_rules(args.build, out / "probe", run_command=host.run,
            compiler=args.cc, equivalent_edits=not args.control)
        record["complete"] = result["complete"]
    except BaseException as error:
        record["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        host.close()
        save()
    print(json.dumps({"complete": True, "family": "D", "cases": result["modes"][0]["cases"],
                      "coverage": result["coverage"]}), flush=True)


if __name__ == "__main__":
    main()
