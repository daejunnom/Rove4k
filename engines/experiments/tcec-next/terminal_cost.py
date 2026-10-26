#!/usr/bin/env python3
"""Opt-in A/E P4 source/native/whole costs; no generated program is executed.

The unchanged selected factory must pass its strict current verifier and all
five literal control identities before this one source hypothesis is measured.
Candidate native images are observations in a new COST class, never production
admissions. Fourteen outer commands per family exclude the factory's separately
reported nested commands. CPP identity is within each case, not across cases.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import lzma
import math
import os
from pathlib import Path
import platform
import signal
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = "engines/experiments/tcec-next/"
SELF = PREFIX + "terminal_cost.py"
HELPER = PREFIX + "terminal_queries.py"
PROJECTION = PREFIX + "spelling_compound.py"
BUILDER = PREFIX + "profile_build.py"
VERIFIER = PREFIX + "profile_verify.py"
DEPENDENCIES = PREFIX + "profile_dependencies.py"
WRAPPER = PREFIX + "wrapper.py"
UNLINK = PREFIX + "self_unlink.py"
OWNER = "engines/experiments/tcec-scope/build.py"
UTILITY = "engines/experiments/tiny-d-submission/structural_size.py"
PACKAGE = "engines/scripts/source_package.py"
PRODUCTION = "engines/scripts/production.py"
READERS = ("engines/scripts/production_input.py", "engines/scripts/source_composition.py")
SUPPORT = (SELF, HELPER, PROJECTION, BUILDER, VERIFIER, DEPENDENCIES, WRAPPER,
           UNLINK, OWNER, UTILITY, PACKAGE, PRODUCTION, *READERS)
FIXED = {
    HELPER: (6388, "b9a335870e07a7e0244a5554ec99bc7973c7783306112db5b52db560051ddb4d"),
    PROJECTION: (9472, "4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce"),
}
CLASS = "rove4k-AE-terminal-query-cost-v1"
PROFILE = "test-p4"
VARIANT = "terminal-owner-late-queries"
CASES = ("control", VARIANT)
COMPILER = ["cc", "-Os", "-x", "c", "-", "-o", "x", "-s"]
BANNER = "cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
MAX_FILE = 16 << 20
FSIZE = 8 << 20  # Each new stdout/stderr file is bounded before Host reads it.
OUTER_COMMANDS = 14
CONTROL = {
    "A": {
        "source": (7595, "02faeb563c435c02321fc6d497f54a31de01d9093be33bff5e44206a93dfbdc6"),
        "native": (18568, "dc2dc95fe41fc3ecb8dde3b5ace90961fb691caba45484cb8b55f31ebdce0a9e"),
        "whole": (3781, "afc51befbc02956e7b91a30f83f562e6e7c9a84531204dd2d9d84f9b813bf893"),
        "payload": (3687, "be6ef5c4266ac536b475157d39ec1e5e580ed51b13afd547dbb5ccdd734d1896"),
    },
    "E": {
        "source": (7815, "198bccf29d1441f63e3fd07b5da9ab4164fe3c31393af7ad35ab72d4d3fe08ff"),
        "native": (18568, "fafa02d83ca754ee094d3a38f0a78208465c4cf6acb98f470aa7e15b049cfead"),
        "whole": (3882, "872f64c2205e74e8100ded20bf2d4e13986f615af45b4bd4d46a885998ec3ba2"),
        "payload": (3788, "1beca73bd77c4094b0de9f50955776abd60a5eb56e5f460f72ec812b3f8843cc"),
    },
}
HEADER = (94, "44b95bde0944d710e4bd20c4ab2a8c3d380c824bfc442f54e69901e6bb32406e")
CANDIDATE = {
    "A": (7688, "e0c73ac70536ebc41afeac0d39866b38fe66448e439e7b1288200eff459cc8e8"),
    "E": (7909, "8f44f5223d6c05e3797132f7da2994af8a46db879dbfef82644a8ba55a093c4d"),
}
_EXECUTING_CODE = sys._getframe().f_code


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def expected(pair):
    return {"bytes": pair[0], "sha256": pair[1]}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def plan(family):
    require(type(family) is str and family in CONTROL, "finite A/E P4 family required")
    compression = dict(format="lzma-alone", filter="LZMA1", preset=6 if family == "A" else 9,
        extreme=family == "E", lc=2, lp=0, pb=0, check="NONE", mf="BT2" if family == "A" else "BT4",
        dictionary_bytes=65536, nice_len=24 if family == "A" else 32)
    return dict(family=family, profile=PROFILE, cases=list(CASES), outer_commands=OUTER_COMMANDS,
        work_seconds=600, cleanup_seconds=30, compiler=list(COMPILER), compiler_version=BANNER,
        compression=compression,
        control={**{key: expected(value) for key, value in CONTROL[family].items()},
                 "header": expected(HEADER)}, candidate_source=expected(CANDIDATE[family]))


def factory_argv(family, output):
    plan(family)
    command = [sys.executable, "-I", "-B", str(ROOT / BUILDER), "--entry", family,
        "--profile", PROFILE, "--representation", "source-jit", "--b-variant", "control",
        "--phase-variant", "phase-init", "--spelling-variant", "compound",
        "--source-dependencies", "unused-includes"]
    if family == "A":
        command += ["--scan-variant", "square-successor"]
    return [*command, "--out", str(output)]


def limit_plan(cpu, address_space, file_size):
    for pair in (cpu, address_space, file_size):
        require(type(pair) is tuple and len(pair) == 2
                and all(type(n) is int and (n == -1 or n > 0) for n in pair),
                "positive inherited resource pair required")
        require(pair[1] == -1 or pair[0] != -1 and pair[0] <= pair[1],
                "inconsistent inherited resource pair")
    hard = min([630] + ([cpu[1]] if cpu[1] != -1 else []))
    soft = min([600, hard] + ([cpu[0]] if cpu[0] != -1 else []))
    require(hard >= 480, "unchanged factory requires its 480-second CPU hard limit")
    require(all(n == -1 or n >= 4 << 30 for n in address_space),
            "unchanged factory requires 4GiB address space")
    fsize = min([FSIZE] + [n for n in file_size if n != -1])
    return dict(parent_CPU=(soft, hard), parent_AS=4 << 30, FSIZE=(fsize, fsize),
                factory_AS=4 << 30, factory_CPU=480, native_AS=2 << 30, native_CPU=120)


def read_source(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_FILE,
            "bounded named source file required")
    data = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named source")
    return data


def capture():
    files = {name: read_source(ROOT / name) for name in SUPPORT}
    require(compile(files[SELF], _EXECUTING_CODE.co_filename, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "executing controller differs from captured source")
    for name, value in FIXED.items():
        require(pin(files[name]) == expected(value), "frozen terminal/projection owner differs: " + name)
    return files


def load_bytes(name, logical, data):
    spec = importlib.util.spec_from_file_location(name, ROOT / logical)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(data, str(ROOT / logical), "exec", dont_inherit=True), module.__dict__)
    return module


def write(root, name, data):
    require(type(data) is bytes and len(data) <= MAX_FILE, "bounded output bytes required")
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def settled(commands):
    return type(commands) is list and bool(commands) and all(
        type(row) is dict and row.get("started") is True and row.get("terminal") is True
        and row.get("reaped") is True and type(row.get("returncode")) is int
        and row["returncode"] == 0 and row.get("owned_group_absent") is True
        and row.get("forced_cleanup") is False for row in commands)


def validate_factory_receipts(manifest, control, family):
    """New profile receipts are not legacy Host nested_receipt dictionaries."""
    plan(family)
    for record, kind in ((manifest, "rove4k-production-profile-v1"), (control, "tcec-full-C-v1")):
        require(type(record) is dict and type(record.get("format")) is int
                and record["format"] == 1 and record.get("class") == kind
                and record.get("family") == family and record.get("entry") == family
                and record.get("complete") is True and record.get("reproducible") is True
                and canonical(record.get("host_cleanup")) == canonical({"unsettled_commands": 0, "errors": []})
                and settled(record.get("commands")), "fresh new-format factory receipt is incomplete")


def run_command(host, owner, command, *, cwd, kind, data=None, factory=False):
    """Serial per-call child limits, using only the existing process owner."""
    require(len(host.report["commands"]) < OUTER_COMMANDS, "outer command limit exceeded")
    previous = dict(owner.LIMITS)
    limits = dict(AS=4 << 30, CPU=480) if factory else dict(AS=2 << 30, CPU=120)
    owner.LIMITS.update(child_AS=limits["AS"], child_CPU=limits["CPU"])
    first = len(host.report["commands"])
    try:
        return host.run(command, cwd=cwd, kind=kind, data=data)
    finally:
        owner.LIMITS.clear()
        owner.LIMITS.update(previous)
        for row in host.report["commands"][first:]:
            require(row.get("child_limits") == limits, "actual per-call child limits differ")
            # RLIMIT_FSIZE <=8MiB per new file also bounds the owner's earlier reads.
            total = 0
            for stream in ("stdout", "stderr"):
                if stream in row:
                    path = Path(row[stream]["path"])
                    require(path.is_file() and path.stat().st_size <= FSIZE,
                            "final individual stdio extent exceeds cap")
                    total += path.stat().st_size
            row["final_combined_stdio_bytes"] = total
            require(total <= MAX_FILE, "final combined stdio exceeds cap")
        host.save()


def restored_payload(whole, header, source):
    require(len(whole) <= MAX_FILE and whole.startswith(header) and 0 < len(header) < len(whole),
            "actual source wrapper boundary differs")
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    require(decoder.decompress(whole[len(header):], max_length=len(source) + 1) == source
            and decoder.eof and not decoder.unused_data, "strict whole source inverse differs")


def measure(family, out, *, execute=False):
    require(execute is True, "explicit --execute required before source capture or output creation")
    policy = plan(family)
    require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux x86-64 required")
    import resource
    started = time.monotonic()
    inherited = {"CPU": resource.getrlimit(resource.RLIMIT_CPU),
                 "AS": resource.getrlimit(resource.RLIMIT_AS),
                 "FSIZE": resource.getrlimit(resource.RLIMIT_FSIZE)}
    applied = limit_plan(inherited["CPU"], inherited["AS"], inherited["FSIZE"])
    files = capture()
    utility = load_bytes("terminal_cost_utility", UTILITY, files[UTILITY])
    out = utility.new_output(out)
    out.mkdir(parents=True)
    for name, data in files.items():
        write(out / "support", name, data)
    report = dict(format=1, **{"class": CLASS}, complete=False, reproducible=False,
        policy=policy, support={name: pin(data) for name, data in files.items()}, commands=[], attempts=[],
        engine_executed=False, TT_allocated=False, selected=False, runtime_qualified=False,
        scope="fresh strict control and one source hypothesis; compile/package observations only",
        host_context=dict(python=sys.version, uname=list(os.uname()),
                          cpu_affinity=sorted(os.sched_getaffinity(0))),
        limits={**applied, "work_seconds": 600, "cleanup_budget_seconds": 30,
                "inherited": inherited,
                "fresh_profile_TERM_grace_seconds": 15, "other_TERM_grace_seconds": 3,
                "combined_stdio_bytes": MAX_FILE}, outer_command_limit=OUTER_COMMANDS)

    def save():
        (out / "result.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")

    save()
    host = None
    owner = None
    original_owner_limits = None
    body_error = None
    previous_chld = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    try:
        resource.setrlimit(resource.RLIMIT_FSIZE, applied["FSIZE"])
        owner = load_bytes("terminal_cost_process_owner", OWNER, files[OWNER])
        require(owner.EXECUTING_BUILD == files[OWNER], "process owner reread changed")
        original_owner_limits = dict(owner.LIMITS)
        remaining = math.floor(600 - (time.monotonic() - started))
        require(remaining > 0, "work budget expired before Host construction")
        owner.LIMITS.update(aggregate_wall=remaining, per_command_wall=600,
            parent_AS=applied["parent_AS"], parent_CPU=applied["parent_CPU"][0],
            parent_CPU_hard=applied["parent_CPU"][1], tool_output_bytes=MAX_FILE)

        class Host(owner.Host):
            def settle(self, child, row, force=False):
                if row.get("kind") == "fresh-profile":
                    row["cooperative_termination_seconds"] = 15
                return super().settle(child, row, force)

        host = Host(out, report, save)
        report["limits"].update(aggregate_work_alarm_seconds=remaining,
            actual_parent_CPU=resource.getrlimit(resource.RLIMIT_CPU),
            actual_parent_AS=resource.getrlimit(resource.RLIMIT_AS),
            actual_FSIZE=resource.getrlimit(resource.RLIMIT_FSIZE))
        R = load_bytes("terminal_cost_strict_R", VERIFIER, files[VERIFIER])
        helper = load_bytes("terminal_cost_source_hypothesis", HELPER, files[HELPER])
        projection = load_bytes("terminal_cost_projection", PROJECTION, files[PROJECTION])
        baseline = out / "fresh-profile"
        run_command(host, owner, factory_argv(family, baseline), cwd=out, kind="fresh-profile", factory=True)
        raw = R.input_reader().read_regular(R.artifact_file(baseline, "build.json"), limit=MAX_FILE)
        manifest = json.loads(raw)
        admitted = R.admit_c_build(manifest, baseline)
        control_raw = R.checked_artifact(baseline, "control/build.json", manifest["control"]["report"])
        control_manifest = json.loads(control_raw)
        validate_factory_receipts(manifest, control_manifest, family)
        require(admitted.family == family and admitted.profile_id == PROFILE and admitted.full is True
                and admitted.representation == "source-jit" and manifest["plan"]["entry_cleanup"] == "private-path"
                and canonical(manifest["compiler"]) == canonical(COMPILER)
                and manifest["compile_executor"] == COMPILER and manifest["compile_executor_version"] == BANNER
                and canonical(manifest["compression"]) == canonical(policy["compression"]),
                "fresh strict control context differs from the finite P4 context")
        artifacts = {key: R.checked_artifact(baseline, name, policy["control"][key]) for key, name in
            (("source", "main.c"), ("native", "native/x"), ("whole", "x"),
             ("header", "header.sh"), ("payload", "payload.lzma"))}
        require(artifacts["whole"] == artifacts["header"] + artifacts["payload"], "control parts differ")
        inputs = {name: R.checked_artifact(baseline, "inputs/" + name, value)
                  for name, value in admitted.input_pins.items()}
        require(all(data == R.source_bytes(name, admitted.input_pins[name]) for name, data in inputs.items()),
                "fresh frozen factory input is not current")
        for name in (BUILDER, VERIFIER, OWNER, PROJECTION, DEPENDENCIES, WRAPPER, UNLINK, PACKAGE, PRODUCTION):
            require(inputs.get(name) == files[name], "factory/captured support differs: " + name)
        dependencies = load_bytes("terminal_cost_dependencies", DEPENDENCIES, inputs[DEPENDENCIES])
        wrapper = load_bytes("terminal_cost_wrapper", WRAPPER, inputs[WRAPPER])
        package = load_bytes("terminal_cost_package", PACKAGE, inputs[PACKAGE])
        unlink = load_bytes("terminal_cost_unlink", UNLINK, inputs[UNLINK])
        proofs = manifest["source_proofs"]
        require(proofs[-1].get("schema") == dependencies.SCHEMA, "dependency cleanup must be last")
        old_dependency = proofs[-1]
        precleanup = dependencies.restore_source(artifacts["source"], old_dependency)
        require(precleanup == artifacts["source"] and pin(precleanup) == policy["control"]["source"],
                "finite A/E dependency no-op bridge differs")
        assertions = proofs[0]["target_type_assertions"]
        require(type(assertions) is list and assertions and all(type(value) is str
                and value.startswith("_Static_assert(") for value in assertions), "actual resource type assertions required")
        report.update(factory_manifest=pin(raw), control_manifest=pin(control_raw), resources=admitted.resources,
            factory_inputs={name: pin(data) for name, data in inputs.items()},
            factory_profile_commands=manifest["commands"], factory_control_commands=control_manifest["commands"],
            compiler=manifest["compiler"], compression=manifest["compression"],
            nested_command_counts={"profile": len(manifest["commands"]), "selected_control": len(control_manifest["commands"]),
                                   "exhaustive_physical_process_count": False})
        banner = run_command(host, owner, [COMPILER[0], "--version"], cwd=out, kind="compiler-version")
        actual_banner = banner.decode("utf-8", "strict").splitlines()[0]
        require(actual_banner == BANNER, "actual compiler banner differs")
        report["compile_executor_version"] = actual_banner
        cpp_command = dependencies.preprocess_command(COMPILER)
        for case in CASES:
            for attempt in ("first", "repeat"):
                source = R.checked_artifact(baseline, attempt + "/main.c", policy["control"]["source"])
                source = dependencies.restore_source(source, old_dependency)
                source_proof = None
                if case == VARIANT:
                    source, source_proof = helper.transform_source(source, family=family, profile_id=PROFILE,
                                                                  projection=projection)
                    require(pin(source) == policy["candidate_source"] and helper.restore_source(source,
                        json.loads(json.dumps(source_proof, allow_nan=False)), projection=projection) == precleanup,
                        "finite terminal source or full typed inverse differs")
                final, dependency_proof = dependencies.transform_source(source)
                require(final == source and dependencies.restore_source(final, dependency_proof) == source,
                        "final dependency cleanup no-op/inverse differs")
                target = out / case / attempt
                native_dir, type_dir = target / "native", target / "types"
                native_dir.mkdir(parents=True)
                type_dir.mkdir()
                write(target, "main.c", final)
                asserted = final + b"\n" + ("\n".join(assertions) + "\n").encode()
                write(type_dir, "asserted.c", asserted)
                prefix = case + "-" + attempt
                run_command(host, owner, COMPILER, cwd=type_dir, kind=prefix + "-types", data=asserted)
                run_command(host, owner, COMPILER, cwd=native_dir, kind=prefix + "-native", data=final)
                native = R.input_reader().read_regular(native_dir / "x", limit=MAX_FILE)
                require(R.input_reader().read_regular(type_dir / "x", limit=MAX_FILE) == native,
                        "target type assertions changed native bytes")
                cpp = run_command(host, owner, cpp_command, cwd=target, kind=prefix + "-CPP", data=final)
                write(target, "expanded.i", cpp)
                require(all(row["stderr"]["bytes"] == 0 for row in report["commands"][-3:]),
                        "actual type/native/CPP compiler emitted diagnostics")
                header = wrapper.header(package, unlink, COMPILER)
                whole = wrapper.package(package, unlink, final, manifest["compression"], COMPILER)
                restored_payload(whole, header, final)
                observed = dict(source=pin(final), native=pin(native), header=pin(header),
                                payload=pin(whole[len(header):]), whole=pin(whole))
                if case == "control":
                    require(canonical(observed) == canonical(policy["control"]), "independent five-part control differs")
                for name, data in (("x", whole), ("header.sh", header), ("payload.lzma", whole[len(header):])):
                    write(target, name, data)
                report["attempts"].append(dict(case=case, attempt=attempt, artifacts=observed, CPP=pin(cpp),
                    source_proof=source_proof, dependency_proof=dependency_proof,
                    target_type_gate=dict(assertions=assertions, source=pin(asserted), image_identical=True)))
                save()
            first, repeat = [row for row in report["attempts"] if row["case"] == case]
            require(canonical({k: v for k, v in first.items() if k != "attempt"}) ==
                    canonical({k: v for k, v in repeat.items() if k != "attempt"}),
                    "case-internal source/type/native/whole/CPP reproduction differs")
            for name in ("main.c", "native/x", "types/x", "types/asserted.c", "x",
                         "header.sh", "payload.lzma", "expanded.i"):
                require(R.input_reader().read_regular(out / case / "first" / name, limit=MAX_FILE) ==
                        R.input_reader().read_regular(out / case / "repeat" / name, limit=MAX_FILE),
                        "case-internal actual repeated bytes differ: " + name)
        require(len(report["commands"]) == OUTER_COMMANDS and settled(report["commands"]),
                "fourteen original outer commands did not settle cleanly")
        require(R.input_reader().read_regular(R.artifact_file(baseline, "build.json"), limit=MAX_FILE) == raw,
                "fresh factory receipt changed")
        R.admit_c_build(manifest, baseline)
        require(all(R.checked_artifact(baseline, "inputs/" + name, admitted.input_pins[name]) == data
                    == R.source_bytes(name, admitted.input_pins[name]) for name, data in inputs.items()),
                "fresh frozen/current complete input closure changed")
        require(all(read_source(ROOT / name) == data and read_source(out / "support" / name) == data
                    for name, data in files.items()), "current/captured controller support changed")
        rows = {row["case"]: row["artifacts"] for row in report["attempts"]}
        report.update(reproducible=True, CPP_identity="two actual expansions within each case only",
            outer_commands=len(report["commands"]), support_rechecked=True,
            delta={key: rows[VARIANT][key]["bytes"] - rows["control"][key]["bytes"] for key in rows["control"]})
    except BaseException as error:
        body_error = error
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        try:
            utility.finish_report(host, report, save, body_error)
        finally:
            if owner is not None and original_owner_limits is not None:
                owner.LIMITS.clear()
                owner.LIMITS.update(original_owner_limits)
            signal.signal(signal.SIGCHLD, previous_chld)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", choices=("A", "E"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="explicitly run this bounded compile/package comparison")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required before source capture or output creation")
    report = measure(args.entry, args.out, execute=True)
    print(json.dumps({"class": CLASS, "complete": report["complete"],
                      "family": args.entry, "delta": report["delta"]}, sort_keys=True))


if __name__ == "__main__":
    main()
