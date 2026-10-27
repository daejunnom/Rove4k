#!/usr/bin/env python3
"""Finite opt-in source costs; generated engines and TT are never executed.

The unchanged selected factory must pass its strict current verifier and all
five literal control identities before this one source hypothesis is measured.
Candidate native images are observations in a new COST class, never production
admissions. The default A/E terminal experiment retains fourteen outer commands.
The explicit A/B/C/E mate and C/E EP experiments add one fatal-UBSan diagnostic
compile/run, for sixteen commands. The mate diagnostic executes integer fragments;
EP uses the actual source's start/generate/make in the existing rules fixture.
Neither calls the original entry or allocates a TT. Nested factory commands remain
separate. CPP identity is case-internal, not control-versus-candidate.
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
MATE_HELPER = PREFIX + "compact_mate.py"
MATE_SEMANTICS = PREFIX + "test_compact_mate.py"
EP_HELPER = PREFIX + "compact_ep.py"
EP_TESTS = PREFIX + "test_compact_ep.py"
RULES = PREFIX + "profile_rules.py"
ORACLE = "engines/tests/chess_oracle.py"
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
MATE_CLASS = "rove4k-ABCE-mate-cost-v1"
MATE_VARIANTS = ("folded", "shared")
MATE_OUTER_COMMANDS = 16
MATE_FIXED = {
    PROJECTION: FIXED[PROJECTION],
    MATE_HELPER: (7726, "85ede9040965ac09e23a2366e63d833ca8edb804ea8f0dbda4cab4701db3704a"),
    MATE_SEMANTICS: (11732, "4082051c2d70d6a02d24494f955b17631cea3e8f258163b1b7a2c99d1bf84bd7"),
}
MATE_CONTROL = {
    **CONTROL,
    "B": {
        "source": (7934, "09546a75f5e417125ec033994fec52b1e23da4d504e5146a54cead53966136ce"),
        "native": (25744, "89b695055e8fbcdfd64f9cfd07e127180eb9827e4245631afd0525d2e0609e29"),
        "whole": (4071, "c64753dc77b2c287d13612f985ed4c77d53caafc532530169ec328ee577dbeae"),
        "payload": (3962, "2ff39681818973f97a03591af52d7ac77c6363aedd2e9df879e1e937d08f790e"),
    },
    "C": {
        "source": (8199, "86b7dd0e5f206d10086d098ce82083d4d12910df91a7f1215915727327f1d42a"),
        "native": (18568, "16031542896ac9d28cf6e7d70f32a8eef041baff2e65bcf030edea7eae689462"),
        "whole": (3915, "48f201d454749957eb9ada8589de8d75d7e331571f6958e31a15542cf2d00546"),
        "payload": (3814, "eb3969b146752bb83d39192730346d8987afdd610d5a777a4b839f90421132ef"),
    },
}
MATE_HEADERS = {
    "A": HEADER, "E": HEADER,
    "B": (109, "579c456c8ca9af8acde4bc4a41307807bc85d76d11b56ec5fcdcaa7e304ed911"),
    "C": (101, "05292d5798f864fcd3fee2d387e258d7105085d6753a123100dd246796bf4a38"),
}
MATE_COMPILERS = {
    "A": tuple(COMPILER), "E": tuple(COMPILER),
    "B": ("cc", "-std=c11", "-Os", "-pthread", "-x", "c", "-", "-o", "x"),
    "C": ("cc", "-Os", "-mavx2", "-x", "c", "-", "-o", "x", "-s"),
}
EP_CLASS = "rove4k-CE-ep-cost-v1"
EP_CASE = "legal-maker"
EP_FIXED = {
    PROJECTION: FIXED[PROJECTION],
    EP_HELPER: (7042, "c74f494ede124feddccadbfb5ff9f328f459734ba9355dc1052649ca78205c56"),
    EP_TESTS: (5696, "0806a637a579fa6530cc9ec122349fcc67b817548ec3753d7d185a1224b58559"),
    RULES: (46921, "0719f373c2180d5fb0a79e5b7ceaaea13d6fe8fc889c7e3bb7a42c1d17f93f93"),
    ORACLE: (10730, "aea285b5b5f07602c829595840d5270fa8dc25683ccd26c63607435679024db8"),
}
SEMANTIC_COMPILER = ("cc", "-std=c11", "-O2", "-fsanitize=undefined",
                     "-fno-sanitize-recover=undefined", "-x", "c", "-", "-o", "x")
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


def plan(family, *, experiment="terminal", variant=None):
    require(type(experiment) is str and experiment in ("terminal", "mate", "ep"), "finite source experiment required")
    terminal = experiment == "terminal"
    mate = experiment == "mate"
    families = CONTROL if terminal else MATE_CONTROL if mate else ("C", "E")
    require(type(family) is str and family in families, "finite family for the named P4 source experiment required")
    require(type(variant) is str and variant in MATE_VARIANTS if mate else variant is None,
            "explicit folded/shared mate variant, or no variant for terminal/EP, required")
    compression = dict(format="lzma-alone", filter="LZMA1", preset=6 if family == "A" else 9,
        extreme=family != "A", lc=2, lp=0, pb=0, check="NONE", mf="BT2" if family == "A" else "BT4",
        dictionary_bytes=65536, nice_len=24 if family == "A" else 64 if family == "C" else 32)
    controls = CONTROL if terminal else MATE_CONTROL
    result = dict(family=family, profile=PROFILE,
        cases=list(CASES) if terminal else ["control", variant if mate else EP_CASE],
        outer_commands=OUTER_COMMANDS if terminal else MATE_OUTER_COMMANDS,
        work_seconds=600, cleanup_seconds=30,
        compiler=list(COMPILER if terminal else MATE_COMPILERS[family]), compiler_version=BANNER,
        compression=compression,
        control={**{key: expected(value) for key, value in controls[family].items()},
                 "header": expected(HEADER if terminal else MATE_HEADERS[family])})
    if terminal:
        result["candidate_source"] = expected(CANDIDATE[family])
    elif mate:
        result.update(experiment=experiment, variant=variant,
                      diagnostic_compiler=list(SEMANTIC_COMPILER), diagnostic_engine=False)
    else:
        result.update(experiment=experiment, diagnostic_engine=False,
            diagnostic_compiler=["cc", "-std=c11", "-O1", "-pthread", "-g0",
                *(["-mavx2"] if family == "C" else []), "-fsanitize=undefined",
                "-fno-sanitize-recover=undefined", "-x", "c", "-", "-o", "x"])
    return result


def factory_argv(family, output, *, experiment="terminal", variant=None):
    plan(family, experiment=experiment, variant=variant)
    command = [sys.executable, "-I", "-B", str(ROOT / BUILDER), "--entry", family,
        "--profile", PROFILE, "--representation", "source-jit", "--b-variant",
        "tcec-final-lf" if family == "B" else "control",
        "--phase-variant", "control" if family == "B" else "phase-init",
        "--spelling-variant", "best" if family == "B" else "compound",
        "--source-dependencies", "unused-includes"]
    if family in ("A", "C"):
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


def capture(*, experiment="terminal"):
    require(experiment in ("terminal", "mate", "ep"), "finite support capture required")
    names = SUPPORT if experiment == "terminal" else (
        *[name for name in SUPPORT if name != HELPER],
        *((MATE_HELPER, MATE_SEMANTICS) if experiment == "mate" else (EP_HELPER, EP_TESTS, RULES, ORACLE)))
    files = {name: read_source(ROOT / name) for name in names}
    require(compile(files[SELF], _EXECUTING_CODE.co_filename, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "executing controller differs from captured source")
    fixed = FIXED if experiment == "terminal" else MATE_FIXED if experiment == "mate" else EP_FIXED
    for name, value in fixed.items():
        require(pin(files[name]) == expected(value), "frozen terminal/projection owner differs: " + name)
    return files


def merge_source_closure(factory_inputs, support, *, experiment="terminal"):
    """Preserve every admitted parent input and reject conflicting derived owners."""
    require(type(experiment) is str and experiment in ("terminal", "mate", "ep"), "finite source closure required")
    mandatory = (BUILDER, VERIFIER, OWNER, DEPENDENCIES, WRAPPER, UNLINK, PACKAGE, PRODUCTION)
    if experiment == "terminal":
        mandatory += (PROJECTION,)
    require(all(name in factory_inputs and name in support for name in mandatory),
            "mandatory factory/captured owner missing")
    closure = dict(factory_inputs)
    for name, data in support.items():
        require(name not in closure or closure[name] == data, "factory/captured support differs: " + name)
        closure[name] = data
    return closure


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


def validate_factory_receipts(manifest, control, family, *, experiment="terminal", variant=None):
    """New profile receipts are not legacy Host nested_receipt dictionaries."""
    plan(family, experiment=experiment, variant=variant)
    for record, kind in ((manifest, "rove4k-production-profile-v1"), (control, "tcec-full-C-v1")):
        require(type(record) is dict and type(record.get("format")) is int
                and record["format"] == 1 and record.get("class") == kind
                and record.get("family") == family and record.get("entry") == family
                and record.get("complete") is True and record.get("reproducible") is True
                and canonical(record.get("host_cleanup")) == canonical({"unsettled_commands": 0, "errors": []})
                and settled(record.get("commands")), "fresh new-format factory receipt is incomplete")


def run_command(host, owner, command, *, cwd, kind, data=None, factory=False):
    """Serial per-call child limits, using only the existing process owner."""
    command_limit = host.report.get("outer_command_limit", OUTER_COMMANDS)
    require(type(command_limit) is int and command_limit in (OUTER_COMMANDS, MATE_OUTER_COMMANDS)
            and len(host.report["commands"]) < command_limit, "outer command limit exceeded")
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


def lift_source_edits(before, final, candidate, proof, old_dependency, *, projection, dependencies):
    """Commute exact final-source edits through the existing include cleanup.

    The old dependency proof supplies coordinates; no include offset is guessed.
    All lifted spans and both complete inverses are checked before compilation.
    """
    replay, canonical_dependency = dependencies.transform_source(before)
    require(replay == final and canonical(canonical_dependency) == canonical(old_dependency)
            and dependencies.restore_source(final, old_dependency) == before,
            "canonical original dependency relation differs")
    spans = old_dependency["spans"]
    require(type(spans) is list and len(spans) <= 1, "finite existing dependency cleanup required")
    offset = removed = None
    if spans:
        span = spans[0]
        offset, removed = span["offset"], span["before"].encode("ascii")
        require(type(offset) is int and 0 <= offset <= len(final) and removed == dependencies.DIRECTIVE
                and span["after"] == "" and before[:offset] == final[:offset]
                and before[offset:offset + len(removed)] == removed
                and before[offset + len(removed):] == final[offset:],
                "one exact unchanged include deletion required")
    require(projection._inverse_edits(candidate, proof["edits"]) == final,
            "actual final-source inverse differs before lifting")
    lifted = []
    for row in proof["edits"]:
        at, length = row["input_begin"], len(row["before"].encode("ascii"))
        require(type(at) is int and length > 0, "typed nonempty source edit required")
        if spans:
            require(at >= offset or at + length <= offset, "source edit crosses the removed include")
            at += len(removed) if at >= offset else 0
        lifted.append(dict(input_begin=at, before=row["before"], after=row["after"],
                           role=row["role"], component=row["component"]))
    pre_candidate, rows, gaps = projection._splice(before, lifted)
    require(projection._inverse_edits(pre_candidate, rows) == before,
            "lifted complete pre-cleanup inverse differs")
    cleaned, dependency_proof = dependencies.transform_source(pre_candidate)
    require(cleaned == candidate and dependencies.restore_source(cleaned, dependency_proof) == pre_candidate,
            "source/include projections do not commute")
    return pre_candidate, dependency_proof, dict(
        original_before=pin(before), original_final=pin(final), candidate_before=pin(pre_candidate),
        candidate_final=pin(candidate), original_dependency=old_dependency,
        lifted_edits=rows, protected_gaps=gaps, lifted_full_inverse=True,
        canonical_cleanup_last=True, exact_commuting_output=True)


def lift_mate_source(before, final, candidate, proof, old_dependency, *, projection, dependencies):
    """Retain the original mate API while sharing the source-coordinate owner."""
    return lift_source_edits(before, final, candidate, proof, old_dependency,
                             projection=projection, dependencies=dependencies)


def semantic_observation(data, *, family, variant):
    record = json.loads(data)
    require(type(record) is dict and record.get("complete") is True
            and record.get("family") == family and record.get("profile") == PROFILE
            and record.get("variant") == variant, "actual mate diagnostic identity differs")
    for name, value in (("decode_cases", 8388608), ("store_cases", 8388608), ("TT_values", 65536), ("plies", 128)):
        require(type(record.get(name)) is int and record[name] == value,
                "actual mate exhaustive diagnostic count differs: " + name)
    require(type(record.get("checksum")) is int and 0 <= record["checksum"] < 1 << 64,
            "actual mate checksum type/range differs")
    return record


def measure(family, out, *, execute=False, experiment="terminal", variant=None):
    require(execute is True, "explicit --execute required before source capture or output creation")
    policy = plan(family, experiment=experiment, variant=variant)
    terminal = experiment == "terminal"
    mate = experiment == "mate"
    compiler, cases = policy["compiler"], policy["cases"]
    require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux x86-64 required")
    import resource
    started = time.monotonic()
    inherited = {"CPU": resource.getrlimit(resource.RLIMIT_CPU),
                 "AS": resource.getrlimit(resource.RLIMIT_AS),
                 "FSIZE": resource.getrlimit(resource.RLIMIT_FSIZE)}
    applied = limit_plan(inherited["CPU"], inherited["AS"], inherited["FSIZE"])
    files = capture(experiment=experiment)
    utility = load_bytes("terminal_cost_utility", UTILITY, files[UTILITY])
    out = utility.new_output(out)
    out.mkdir(parents=True)
    for name, data in files.items():
        write(out / "support", name, data)
    report = dict(format=1, **{"class": CLASS if terminal else MATE_CLASS if mate else EP_CLASS},
        complete=False, reproducible=False,
        policy=policy, support={name: pin(data) for name, data in files.items()}, commands=[], attempts=[],
        engine_executed=False, TT_allocated=False, selected=False, runtime_qualified=False,
        scope=("fresh strict control and one source hypothesis; compile/package observations only" if terminal else
               "fresh strict control, one mate hypothesis and actual-fragment UBSan diagnostic; no engine execution" if mate else
               "fresh strict control and one EP hypothesis; preliminary actual-source rules UBSan, not engine/TT or full rules acceptance"),
        host_context=dict(python=sys.version, uname=list(os.uname()),
                          cpu_affinity=sorted(os.sched_getaffinity(0))),
        limits={**applied, "work_seconds": 600, "cleanup_budget_seconds": 30,
                "inherited": inherited,
                "fresh_profile_TERM_grace_seconds": 15, "other_TERM_grace_seconds": 3,
                "combined_stdio_bytes": MAX_FILE}, outer_command_limit=policy["outer_commands"])
    if not terminal:
        report.update(experiment=experiment, diagnostic_C_executed=False)
        if mate:
            report["variant"] = variant

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
        helper_path = HELPER if terminal else MATE_HELPER if mate else EP_HELPER
        helper = load_bytes("terminal_cost_source_hypothesis", helper_path, files[helper_path])
        projection = load_bytes("terminal_cost_projection", PROJECTION, files[PROJECTION])
        semantics = load_bytes("terminal_cost_mate_semantics", MATE_SEMANTICS, files[MATE_SEMANTICS]) if mate else None
        if semantics is not None:
            require(read_source(Path(semantics.mate.__file__)) == files[MATE_HELPER]
                    and read_source(Path(semantics.projection.__file__)) == files[PROJECTION]
                    and all(getattr(semantics.mate, name).__code__ == getattr(helper, name).__code__
                            for name in ("transform_source", "restore_source", "_edits", "_admit"))
                    and all(getattr(semantics.projection, name).__code__ == getattr(projection, name).__code__
                            for name in ("_splice", "_inverse_edits"))
                    and semantics.mate.INPUTS == helper.INPUTS and semantics.mate.CONTEXT == helper.CONTEXT
                    and semantics.mate.DOMAIN == helper.DOMAIN,
                    "diagnostic module's real helper inputs differ from captured support")
        rules = oracle = None
        if experiment == "ep":
            rules = load_bytes("terminal_cost_EP_rules", RULES, files[RULES])
            require(rules.ORACLE == ORACLE and rules.ORACLE_SHA == pin(files[ORACLE])["sha256"],
                    "EP rules renderer's independent oracle owner differs")
            oracle = load_bytes("terminal_cost_EP_oracle", ORACLE, files[ORACLE])
        baseline = out / "fresh-profile"
        run_command(host, owner, factory_argv(family, baseline, experiment=experiment, variant=variant),
                    cwd=out, kind="fresh-profile", factory=True)
        raw = R.input_reader().read_regular(R.artifact_file(baseline, "build.json"), limit=MAX_FILE)
        manifest = json.loads(raw)
        admitted = R.admit_c_build(manifest, baseline)
        control_raw = R.checked_artifact(baseline, "control/build.json", manifest["control"]["report"])
        control_manifest = json.loads(control_raw)
        validate_factory_receipts(manifest, control_manifest, family, experiment=experiment, variant=variant)
        require(admitted.family == family and admitted.profile_id == PROFILE and admitted.full is True
                and admitted.representation == "source-jit" and manifest["plan"]["entry_cleanup"] == "private-path"
                and canonical(manifest["compiler"]) == canonical(compiler)
                and manifest["compile_executor"] == compiler and manifest["compile_executor_version"] == BANNER
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
        closure = merge_source_closure(inputs, files, experiment=experiment)
        dependencies = load_bytes("terminal_cost_dependencies", DEPENDENCIES, inputs[DEPENDENCIES])
        wrapper = load_bytes("terminal_cost_wrapper", WRAPPER, inputs[WRAPPER])
        package = load_bytes("terminal_cost_package", PACKAGE, inputs[PACKAGE])
        unlink = load_bytes("terminal_cost_unlink", UNLINK, inputs[UNLINK])
        proofs = manifest["source_proofs"]
        require(proofs[-1].get("schema") == dependencies.SCHEMA, "dependency cleanup must be last")
        old_dependency = proofs[-1]
        precleanup = dependencies.restore_source(artifacts["source"], old_dependency)
        if terminal:
            require(precleanup == artifacts["source"] and pin(precleanup) == policy["control"]["source"],
                    "finite A/E dependency no-op bridge differs")
        else:
            replay, dependency_control = dependencies.transform_source(precleanup)
            require(replay == artifacts["source"] and canonical(dependency_control) == canonical(old_dependency),
                    "fresh original dependency source relation differs")
        assertions = proofs[0]["target_type_assertions"]
        require(type(assertions) is list and assertions and all(type(value) is str
                and value.startswith("_Static_assert(") for value in assertions), "actual resource type assertions required")
        report.update(factory_manifest=pin(raw), control_manifest=pin(control_raw), resources=admitted.resources,
            factory_inputs={name: pin(data) for name, data in inputs.items()},
            factory_profile_commands=manifest["commands"], factory_control_commands=control_manifest["commands"],
            compiler=manifest["compiler"], compression=manifest["compression"],
            nested_command_counts={"profile": len(manifest["commands"]), "selected_control": len(control_manifest["commands"]),
                                   "exhaustive_physical_process_count": False})
        if not terminal:
            report.update(source_closure={name: pin(data) for name, data in closure.items()},
                derived_support={name: pin(data) for name, data in files.items() if name not in inputs})
        banner = run_command(host, owner, [compiler[0], "--version"], cwd=out, kind="compiler-version")
        actual_banner = banner.decode("utf-8", "strict").splitlines()[0]
        require(actual_banner == BANNER, "actual compiler banner differs")
        report["compile_executor_version"] = actual_banner
        cpp_command = dependencies.preprocess_command(compiler)
        for case in cases:
            for attempt in ("first", "repeat"):
                source = R.checked_artifact(baseline, attempt + "/main.c", policy["control"]["source"])
                before = dependencies.restore_source(source, old_dependency)
                source_proof = None
                commuting = None
                if case != "control":
                    arguments = dict(family=family, profile_id=PROFILE, projection=projection)
                    if mate:
                        arguments["variant"] = variant
                    candidate, source_proof = helper.transform_source(source, **arguments)
                    require(helper.restore_source(candidate,
                        json.loads(json.dumps(source_proof, allow_nan=False)), projection=projection) == source,
                        "finite source hypothesis full typed inverse differs")
                    if terminal:
                        require(pin(candidate) == policy["candidate_source"], "finite terminal source differs")
                        before = candidate
                    else:
                        before, _, commuting = lift_source_edits(before, source, candidate, source_proof, old_dependency,
                                                                 projection=projection, dependencies=dependencies)
                        if mate and "semantics" not in report:
                            fixture, fixture_proof = semantics.semantic_fixture(source, family=family,
                                profile_id=PROFILE, variant=variant)
                            require(fixture_proof["source"] == pin(source)
                                    and fixture_proof["candidate"] == pin(candidate)
                                    and fixture_proof["fixture"] == pin(fixture)
                                    and fixture_proof["actual_source_fragments"] is True,
                                    "actual diagnostic fixture is not bound to this source candidate")
                            diagnostic = out / "mate-semantic"
                            diagnostic.mkdir()
                            write(diagnostic, "fixture.c", fixture)
                            run_command(host, owner, list(SEMANTIC_COMPILER), cwd=diagnostic,
                                        kind="mate-semantic-compile", data=fixture)
                            semantic_raw = run_command(host, owner, [str(diagnostic / "x")], cwd=diagnostic,
                                                       kind="mate-semantic-execute")
                            require(all(row["stderr"]["bytes"] == 0 for row in report["commands"][-2:]),
                                    "fatal-UBSan mate diagnostic emitted stderr")
                            observation = semantic_observation(semantic_raw, family=family, variant=variant)
                            write(diagnostic, "result.stdout", semantic_raw)
                            report.update(diagnostic_C_executed=True, semantics=dict(
                                fixture=fixture_proof, native=pin(R.input_reader().read_regular(diagnostic / "x", limit=MAX_FILE)),
                                output=pin(semantic_raw), observation=observation, engine_executed=False,
                                TT_allocated=False, compiler=list(SEMANTIC_COMPILER),
                                scope="actual source fragments, promoted signed16 values and ply0..127; not an engine"))
                            save()
                        elif experiment == "ep" and "semantics" not in report:
                            rule_cases, coverage = rules.fixture_cases(oracle)
                            require(len(rule_cases) == 105 and sum(len(row["legal"]) for row in rule_cases) == 2858,
                                    "existing independent EP rules fixture domain differs")
                            fixture = rules.render_fixture(candidate, family, rule_cases)
                            diagnostic = out / "ep-rules-semantic"
                            diagnostic.mkdir()
                            write(diagnostic, "fixture.c", fixture)
                            case_bytes = (json.dumps([{key: value for key, value in row.items() if key != "board"}
                                                      for row in rule_cases], indent=2, sort_keys=True) + "\n").encode()
                            write(diagnostic, "cases.json", case_bytes)
                            run_command(host, owner, policy["diagnostic_compiler"], cwd=diagnostic,
                                        kind="ep-rules-semantic-compile", data=fixture)
                            semantic_raw = run_command(host, owner, [str(diagnostic / "x")], cwd=diagnostic,
                                                       kind="ep-rules-semantic-execute")
                            require(all(row["stderr"]["bytes"] == 0 for row in report["commands"][-2:]),
                                    "fatal-UBSan actual-source EP rules diagnostic emitted stderr")
                            observation = rules._compare_output(semantic_raw, rule_cases)
                            require(observation["cases"] == 105 and observation["legal_moves_compared"] == 2858
                                    and observation["legal_sets_equal"] is True,
                                    "actual-source EP rules diagnostic comparison differs")
                            write(diagnostic, "result.stdout", semantic_raw)
                            report.update(diagnostic_C_executed=True, semantics=dict(
                                mode="ubsan", source=pin(candidate), fixture=pin(fixture), cases=pin(case_bytes),
                                oracle=dict(path=ORACLE, **pin(files[ORACLE])), renderer=dict(path=RULES, **pin(files[RULES])),
                                coverage=coverage, native=pin(R.input_reader().read_regular(diagnostic / "x", limit=MAX_FILE)),
                                output=pin(semantic_raw), observation=observation, engine_executed=False,
                                original_entry_called=False, TT_allocated=False, compiler=policy["diagnostic_compiler"],
                                preliminary_only=True, full_plain_and_UBSan_rules_required_before_adoption=True,
                                scope="actual final candidate start/generate/make legal sets at standard-start-derived positions; not full rules or runtime acceptance"))
                            save()
                final, dependency_proof = dependencies.transform_source(before)
                require(dependencies.restore_source(final, dependency_proof) == before,
                        "final canonical dependency inverse differs")
                if case == "control":
                    require(final == source and canonical(dependency_proof) == canonical(old_dependency),
                            "fresh control final dependency relation differs")
                else:
                    require(final == candidate, "final dependency cleanup changed the source hypothesis")
                if terminal:
                    require(final == before, "finite terminal dependency no-op differs")
                target = out / case / attempt
                native_dir, type_dir = target / "native", target / "types"
                native_dir.mkdir(parents=True)
                type_dir.mkdir()
                write(target, "main.c", final)
                asserted = (final if terminal else before) + b"\n" + ("\n".join(assertions) + "\n").encode()
                write(type_dir, "asserted.c", asserted)
                if not terminal:
                    write(target, "pre-dependency.c", before)
                prefix = case + "-" + attempt
                run_command(host, owner, compiler, cwd=type_dir, kind=prefix + "-types", data=asserted)
                run_command(host, owner, compiler, cwd=native_dir, kind=prefix + "-native", data=final)
                native = R.input_reader().read_regular(native_dir / "x", limit=MAX_FILE)
                require(R.input_reader().read_regular(type_dir / "x", limit=MAX_FILE) == native,
                        "pre-cleanup resource assertions/final native images differ")
                cpp_source = before if not terminal and attempt == "first" else final
                cpp = run_command(host, owner, cpp_command, cwd=target, kind=prefix + "-CPP", data=cpp_source)
                write(target, "expanded.i", cpp)
                require(all(row["stderr"]["bytes"] == 0 for row in report["commands"][-3:]),
                        "actual type/native/CPP compiler emitted diagnostics")
                header = wrapper.header(package, unlink, compiler)
                whole = wrapper.package(package, unlink, final, manifest["compression"], compiler)
                restored_payload(whole, header, final)
                observed = dict(source=pin(final), native=pin(native), header=pin(header),
                                payload=pin(whole[len(header):]), whole=pin(whole))
                if case == "control":
                    require(canonical(observed) == canonical(policy["control"]), "independent five-part control differs")
                for name, data in (("x", whole), ("header.sh", header), ("payload.lzma", whole[len(header):])):
                    write(target, name, data)
                row = dict(case=case, attempt=attempt, artifacts=observed, CPP=pin(cpp),
                    source_proof=source_proof, dependency_proof=dependency_proof,
                    target_type_gate=dict(assertions=assertions, source=pin(asserted), image_identical=True))
                if not terminal:
                    row.update(CPP_input=pin(cpp_source), CPP_stage="before-cleanup" if attempt == "first" else "final",
                        commuting=commuting, pre_dependency=pin(before),
                        dependency_native_gate="pre-cleanup source plus static resource assertions equals final native")
                report["attempts"].append(row)
                save()
            first, repeat = [row for row in report["attempts"] if row["case"] == case]
            noncomparable = {"attempt", "CPP_input", "CPP_stage"}
            require(canonical({k: v for k, v in first.items() if k not in noncomparable}) ==
                    canonical({k: v for k, v in repeat.items() if k not in noncomparable}),
                    "case-internal source/type/native/whole/CPP reproduction differs")
            if not terminal:
                require(first["CPP_input"] == first["pre_dependency"]
                        and repeat["CPP_input"] == repeat["artifacts"]["source"]
                        and first["CPP_stage"] == "before-cleanup" and repeat["CPP_stage"] == "final",
                        "actual pre/final dependency CPP sequence differs")
            for name in ("main.c", "native/x", "types/x", "types/asserted.c", "x",
                         "header.sh", "payload.lzma", "expanded.i"):
                require(R.input_reader().read_regular(out / case / "first" / name, limit=MAX_FILE) ==
                        R.input_reader().read_regular(out / case / "repeat" / name, limit=MAX_FILE),
                        "case-internal actual repeated bytes differ: " + name)
            if not terminal:
                require(R.input_reader().read_regular(out / case / "first/pre-dependency.c", limit=MAX_FILE) ==
                        R.input_reader().read_regular(out / case / "repeat/pre-dependency.c", limit=MAX_FILE),
                        "case-internal repeated pre-cleanup source differs")
        require(len(report["commands"]) == policy["outer_commands"] and settled(report["commands"]),
                "finite original outer commands did not settle cleanly")
        require(R.input_reader().read_regular(R.artifact_file(baseline, "build.json"), limit=MAX_FILE) == raw,
                "fresh factory receipt changed")
        R.admit_c_build(manifest, baseline)
        require(all((name not in inputs or
                     R.checked_artifact(baseline, "inputs/" + name, admitted.input_pins[name]) == data
                     == R.source_bytes(name, admitted.input_pins[name])) and
                    (name not in files or read_source(ROOT / name) == data
                     and read_source(out / "support" / name) == data) for name, data in closure.items()),
                "fresh frozen/current complete factory and derived source closure changed")
        rows = {row["case"]: row["artifacts"] for row in report["attempts"]}
        report.update(reproducible=True, CPP_identity=("two actual expansions within each case only" if terminal else
            "first pre-cleanup and repeated final expansion agree within each case only"),
            outer_commands=len(report["commands"]), support_rechecked=True,
            delta={key: rows[cases[1]][key]["bytes"] - rows["control"][key]["bytes"] for key in rows["control"]})
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
    parser.add_argument("--entry", choices=("A", "B", "C", "E"), required=True)
    parser.add_argument("--experiment", choices=("terminal", "mate", "ep"), default="terminal")
    parser.add_argument("--variant", choices=MATE_VARIANTS,
                        help="explicit folded/shared mate hypothesis; invalid for terminal and EP experiments")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="explicitly run this bounded compile/package comparison")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required before source capture or output creation")
    report = measure(args.entry, args.out, execute=True, experiment=args.experiment, variant=args.variant)
    summary = {"class": report["class"], "complete": report["complete"],
               "family": args.entry, "delta": report["delta"]}
    if args.experiment != "terminal":
        summary.update(experiment=args.experiment, diagnostic_C_executed=report["diagnostic_C_executed"])
        if args.experiment == "mate":
            summary["variant"] = args.variant
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
