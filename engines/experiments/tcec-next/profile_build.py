#!/usr/bin/env python3
"""Regenerate one full C engine for a named test or submission profile.

Every run freshly invokes the maintained, pinned tracked-source producer.
There is no historical source/binary input, runtime family selector, implicit
reduced feature policy, or automatic selected-recipe update. Building a large
TT profile only compiles/packages it; no engine is executed by this command.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import lzma
from pathlib import Path
import platform
import shutil
import signal
import sys
from types import ModuleType

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SELF = "engines/experiments/tcec-next/profile_build.py"
CLASS = "rove4k-production-profile-v1"
BASELINE = "engines/experiments/tcec-next/build.py"
COMMON = "engines/scripts/production.py"
LEAGUE_PROFILES = "engines/scripts/league_resource_profiles.py"
LEAGUE_PROFILE_IDS = ("test-p16", "test-p192")
SOURCE = "engines/experiments/tcec-next/profile_source.py"
VERIFIER = "engines/experiments/tcec-next/profile_verify.py"
PACKAGE = "engines/scripts/source_package.py"
WRAPPER = "engines/experiments/tcec-next/wrapper.py"
UNLINK = "engines/experiments/tcec-next/self_unlink.py"
ELF = "engines/scripts/elf_loader.py"
B_PROFILE = "engines/experiments/tcec-next/profile_b.py"
PHASE = "engines/experiments/tcec-next/profile_phase.py"
SPELLING = "engines/experiments/tcec-next/profile_spelling.py"
B_LEAGUE_SPELLING = "engines/experiments/tcec-next/profile_b_league_spelling.py"
B_LEAGUE_SPELLING_PIN = dict(bytes=3925, sha256="e7e81ba58dbf6210fbf132a5baba3811c987fcb86728949bca0e6e2140bff1e5")
B_LEAGUE_DECLARATION = dict(path=B_LEAGUE_SPELLING, selection="league-atomic", variant="atomic-assignment")
# Isolated, source-pinned P16/P192 experiments: none are production selection.
LEAGUE_EXPERIMENTS = {
    "atomic-assignment": {"path": "engines/experiments/tcec-next/profile_acef_league_atomic.py", "pin": {"bytes": 4906, "sha256": "d551768ea423655cc5566430f5e185b8377321d03f9f3429fd8f18112eaaaddd"}, "families": "ACEF"},
    "square-successor": {"path": "engines/experiments/tcec-next/profile_league_square.py", "pin": {"bytes": 3790, "sha256": "8b832928e53bde3c007ed7e1bf8a35290bd8785f4233ea7246d9cb1392eed1b8"}, "families": "AC"},
    "legal-maker": {"path": "engines/experiments/tcec-next/league_ep.py", "pin": {"bytes": 4456, "sha256": "55d76f2740732672fd6abf9cc2650143525732eadf10a9a302cf652accfafc05"}, "families": "CE"},
}
LEAGUE_SUPPORT = {
    "square-successor": {"engines/experiments/tcec-next/profile_scan.py": {"bytes": 10623, "sha256": "98eb3139bcbd745f08fbab2d8a738b428d4e668de2604ac3fc715de8c58b879f"}},
    "legal-maker": {
        "engines/experiments/tcec-next/compact_ep.py": {"bytes": 7267, "sha256": "42963c889070f29da4dc05d08d5fc4749afb7aec36b0d00735ccc9d271215c6c"},
        "engines/experiments/tcec-next/spelling_compound.py": {"bytes": 9472, "sha256": "4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce"}},
}
COMPOUND = "engines/experiments/tcec-next/spelling_compound.py"
SCAN = "engines/experiments/tcec-next/profile_scan.py"
SCAN_DECLARATION = dict(path=SCAN, variant="square-successor")
SCAN_PIN = dict(bytes=10623, sha256="98eb3139bcbd745f08fbab2d8a738b428d4e668de2604ac3fc715de8c58b879f")
SCAN_COMPILER_VERSION = "cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
SCAN_IMAGES = {
    ("A", "test-p4"): (7595, "02faeb563c435c02321fc6d497f54a31de01d9093be33bff5e44206a93dfbdc6", "dc2dc95fe41fc3ecb8dde3b5ace90961fb691caba45484cb8b55f31ebdce0a9e"),
    ("A", "test-p28"): (7628, "f1d5465716752b23c31d63035bbcb94b12818a984c9afbc4ce20c0c843f82006", "4303194fb29769c10fe0800377370cd6a64e94428e9b26123caee3aab2cd29c1"),
    ("A", "tcec-provisional"): (7597, "f85fa3716aed39fe9b2ca973ac3d87650dbac95dfa9cedbaf800ada4f6375a23", "e5a644a334125a96e60f495fb24d40b00c8f7cc16a3a3dc7195494fc0a5dd4b7"),
    ("C", "test-p4"): (8199, "86b7dd0e5f206d10086d098ce82083d4d12910df91a7f1215915727327f1d42a", "16031542896ac9d28cf6e7d70f32a8eef041baff2e65bcf030edea7eae689462"),
    ("C", "test-p28"): (8232, "b3a968d2287a8418ce32b7b2f9f019c4695b55a32fd4f332eab89e16d012d2d0", "798beb0201c23da1de875be256d19626ee8a922c595c98588c5618a11d4a8544"),
    ("C", "tcec-provisional"): (8201, "ae131e49609b34eefaa54499f79f2aa738d103cbc800c1d7a70cde359106b807", "3850273327e027346316df07b94c88f7e6b7df44da8dbbffbae69d777ed7c459"),
}
DEPENDENCIES = "engines/experiments/tcec-next/profile_dependencies.py"
EP = "engines/experiments/tcec-next/profile_ep.py"
EP_PIN = dict(bytes=8476, sha256="d80d1421ff9c921fae899198094488a88dab88bd35009f4f36a44ca77588c44a")
BEST_SPELLING = {"A": "clock-type", "B": "atomic-assignment", "C": "clock-type",
                 "E": "clock-type", "F": "atomic-assignment"}
COMPOUND_DECLARATION = dict(path=COMPOUND, selection="compound", variant="clock-atomic-launcher")
SPELLING_PIN = dict(bytes=9921, sha256="7ec393bc9c805ee8e1e6d715f40cb9883f829e3c6b01e2f71f31701e35136ea8")
COMPOUND_V1_HISTORICAL_PIN = dict(bytes=5522, sha256="4a4f6079341998fd2d0ef1ff5fc9b35a435751131b4687ce950ef1892820754b")
# Fresh v1/v2 builds use the reviewed current helper; old receipts retain the old pin.
COMPOUND_PIN = dict(bytes=9472, sha256="4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce")
F_COMPOUND_SCHEMA = "rove4k.selected-spelling-compound.v2"
F_COMPOUND_VARIANT = "clock-atomic-launcher-parentheses"
F_COMPOUND_DECLARATION = dict(path=COMPOUND, selection="compound-v2", variant=F_COMPOUND_VARIANT)
F_COMPOUND_COMPILER = ("cc", "-Os", "-pthread", "-x", "c", "-", "-o", "x", "-s")
F_COMPOUND_COMPILER_VERSION = "cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
F_COMPOUND_POLICY = "F-compound-clock-gcc13-v1"
# This is a separately named three-profile policy. Existing control/best maps
# are unchanged. A fresh build must still reproduce both real type/native gates.
F_COMPOUND_IMAGES = {
    "test-p4": (7034, "c89769c80c70722f2a610dbe9371edce9f4063abc15ed2fff6cdc637fec4bc6e",
                "5b4e662a29f7a989c8b7a81f8a41e46a96df5c3e805f4b7b29929b6a2725ae50"),
    "test-p28": (7067, "ad730fee827851f5833e753eb55b60453ed009987211a65d4a7bc4426ca8b5f8",
                 "843bbc1ea78ef68c4cde578df93218f6d36b5f3c48cfa794ba6022b75e949262"),
    "tcec-provisional": (7036, "752720efdcc97c32eb79ff4796e4a0bc4cdfe4f24790863a52b585c667c1497b",
                         "e536de10e8792573548864d6267e8ce3cde76102b6134552f9dbca0d2672437b"),
}
F_COMPOUND_V2_POLICY = "F-compound-parentheses-gcc13-v2"
F_COMPOUND_V2_IMAGES = {
    "test-p4": (7030, "0aa062ec8440911d094a1b4eea48eceb96facfaa4ce94d654f46bfa19c83c7f0",
                "5b4e662a29f7a989c8b7a81f8a41e46a96df5c3e805f4b7b29929b6a2725ae50"),
    "test-p28": (7063, "5a016f252e8efb4faf356de92397964d19e6c5e95863e063a5179864988dcdc5",
                 "843bbc1ea78ef68c4cde578df93218f6d36b5f3c48cfa794ba6022b75e949262"),
    "tcec-provisional": (7032, "7701b38ad0957066d427bb085575f26b511691a6ea60e67f44835ce9359db9df",
                         "e536de10e8792573548864d6267e8ce3cde76102b6134552f9dbca0d2672437b"),
}


def spelling_selection(family, representation, b_variant, phase_variant, selection, *, profile_id=None):
    """Select only the measured final stage; controls acquire no new stage."""
    if (family not in BEST_SPELLING or selection not in ("control", "best", "compound", "compound-v2", "league-atomic")
            or selection == "compound-v2" and family != "F"):
        raise ValueError("explicit full C family and finite spelling selection required")
    if selection == "control":
        return None
    if representation != "source-jit":
        raise ValueError("selected spelling requires source-JIT/private-path")
    selected = ((family == "B" and b_variant == "tcec-final-lf" and phase_variant == "control") or
                (family in "ACEF" and b_variant == "control" and phase_variant == "phase-init"))
    if not selected:
        raise ValueError("selected spelling requires phase-init A/C/E/F or tcec-final-lf B")
    if selection == "league-atomic":
        if family != "B" or profile_id not in LEAGUE_PROFILE_IDS:
            raise ValueError("league atomic spelling requires the named B P16/P192 profiles")
        return dict(B_LEAGUE_DECLARATION)
    if selection == "compound-v2":
        return dict(F_COMPOUND_DECLARATION)
    if selection == "compound" and family != "B":
        return dict(COMPOUND_DECLARATION)
    return dict(path=SPELLING, selection="best", variant=BEST_SPELLING[family])


def compound_native_policy(family, profile_id, declaration, source, compiler, compile_executor, version):
    """Admit only the finite F compound images in their measured GCC13 context."""
    if family != "F" or declaration not in (COMPOUND_DECLARATION, F_COMPOUND_DECLARATION):
        return None
    images, kind = ((F_COMPOUND_V2_IMAGES, F_COMPOUND_V2_POLICY)
                    if declaration == F_COMPOUND_DECLARATION else (F_COMPOUND_IMAGES, F_COMPOUND_POLICY))
    if (profile_id not in images or tuple(compiler) != F_COMPOUND_COMPILER or
            list(compile_executor) != list(compiler) or version != F_COMPOUND_COMPILER_VERSION):
        raise ValueError("F compound requires its named GCC13 native policy; target compilers use sealed-source admission")
    size, source_sha, native_sha = images[profile_id]
    if type(source) is not bytes or (len(source), sha256(source).hexdigest()) != (size, source_sha):
        raise ValueError("F compound final source differs from its named profile policy")
    return dict(kind=kind, family="F", profile_id=profile_id,
        post_spelling=dict(declaration), compiler=list(F_COMPOUND_COMPILER),
        compiler_version=F_COMPOUND_COMPILER_VERSION,
        source=dict(bytes=size, sha256=source_sha), native=dict(bytes=18568, sha256=native_sha))


def scan_selection(family, representation, phase_variant, post_spelling, dependencies, selection):
    if post_spelling == F_COMPOUND_DECLARATION and (dependencies != "unused-includes" or selection != "control"):
        raise ValueError("F compound-v2 requires no scan stage and final unused-includes")
    if selection == "control":
        return None
    if (selection != "square-successor" or family not in ("A", "C") or
            representation != "source-jit" or phase_variant != "phase-init" or
            post_spelling != COMPOUND_DECLARATION or dependencies != "unused-includes"):
        raise ValueError("square-successor requires A/C source-JIT phase-init/compound and final unused-includes")
    return dict(SCAN_DECLARATION)


def scan_native_policy(family, profile_id, declaration, source, compiler, compile_executor, version):
    if declaration is None:
        return None
    expected = ["cc", "-Os", *(["-mavx2"] if family == "C" else []), "-x", "c", "-", "-o", "x", "-s"]
    if (declaration != SCAN_DECLARATION or (family, profile_id) not in SCAN_IMAGES or
            list(compiler) != expected or list(compile_executor) != expected or version != SCAN_COMPILER_VERSION):
        raise ValueError("square-successor requires its named six-context GCC13 policy")
    size, source_sha, native_sha = SCAN_IMAGES[family, profile_id]
    if type(source) is not bytes or (len(source), sha256(source).hexdigest()) != (size, source_sha):
        raise ValueError("square-successor final source differs from its named profile policy")
    return dict(kind="AC-square-successor-gcc13-v1", family=family, profile_id=profile_id,
        post_scan=dict(SCAN_DECLARATION), compiler=expected, compiler_version=SCAN_COMPILER_VERSION,
        source=dict(bytes=size, sha256=source_sha), native=dict(bytes=18568, sha256=native_sha))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def normalized(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ValueError("lone CR in named source input: " + str(path))
    return data


def load_reviewed_b_league_spelling(helper_bytes, helper_path):
    """Execute exactly the verified frozen helper bytes, not a later reread."""
    if (type(helper_bytes) is not bytes or
            {"bytes": len(helper_bytes), "sha256": sha256(helper_bytes).hexdigest()} != B_LEAGUE_SPELLING_PIN):
        raise ValueError("frozen B league spelling bytes differ before execution")
    module = ModuleType("profile_frozen_b_league_spelling")
    module.__file__ = str(helper_path)
    exec(compile(helper_bytes, str(helper_path), "exec"), module.__dict__)
    return module


def _tool_path(path, family):
    """The payload producer and its old receipt verifier are separate roles."""
    if path in (VERIFIER, "engines/experiments/tcec-next/profile_rules.py"):
        return False
    name = Path(path).name
    return ((path.endswith(".py") and not path.startswith("engines/tests/") and
             not name.startswith(("test", "check", "verify", "fresh"))) or
            name == "recipe.json" or path == "engines/model/e19.json" or
            path in (f"engines/compact/tiny-entry-{family.lower()}/bootstrap.py.in",
                     f"engines/compact/tiny-entry-{family.lower()}/launcher.sh"))


def argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", choices=tuple("ABCEF"), required=True)
    parser.add_argument("--profile", choices=("test-p4", "test-p28", "tcec-provisional", *LEAGUE_PROFILE_IDS), required=True)
    parser.add_argument("--representation", choices=("source-jit", "packed-native", "self-contained-elf"),
                        default="source-jit")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--compile-cc", help="final native/type-gate compiler only; runtime wrapper still uses admitted cc argv")
    parser.add_argument("--league-variant", choices=("control", *LEAGUE_EXPERIMENTS), default="control",
                        help="isolated reviewed P16/P192 source-only experiment")
    parser.add_argument("--b-variant", default="control",
                        help="explicit reviewed B post-profile projection; default preserves the control")
    parser.add_argument("--phase-variant", choices=("control", "phase-init"), default="control",
                        help="explicit measured A/C/E/F lifecycle projection; default preserves the control")
    parser.add_argument("--spelling-variant", choices=("control", "best", "compound", "compound-v2", "league-atomic"), default="control",
                        help="explicit measured final source spelling on selected source-JIT routes only")
    parser.add_argument("--scan-variant", choices=("control", "square-successor"), default="control",
                        help="explicit A/C valid-square projection after compound, before final include cleanup")
    parser.add_argument("--source-dependencies", choices=("control", "unused-includes"),
                        default="unused-includes",
                        help="reviewed final include cleanup with expanded-input/native/whole-cost gates")
    parser.add_argument("--ep-variant", choices=("control", "legal-maker"), default="control",
                        help="opt-in C/E full EP maker sharing; final include cleanup remains last")
    return parser


def league_selection(args):
    if args.league_variant == "control":
        return None
    experiment = LEAGUE_EXPERIMENTS.get(args.league_variant)
    if (experiment is None or args.profile not in LEAGUE_PROFILE_IDS or
            args.entry not in experiment["families"] or args.representation != "source-jit" or
            args.b_variant != "control" or args.phase_variant != "control" or
            args.spelling_variant != "control" or args.scan_variant != "control" or
            args.ep_variant != "control" or args.source_dependencies != "control"):
        raise ValueError("league experiment requires its named profile/family and isolated control stages")
    return dict(path=experiment["path"], variant=args.league_variant)


def main():
    parser = argument_parser()
    args = parser.parse_args()
    try:
        post_league = league_selection(args)
    except ValueError as error:
        parser.error(str(error))
    if args.profile in LEAGUE_PROFILE_IDS:
        if args.representation != "source-jit":
            parser.error("league profiles currently admit only source-JIT bootstrap")
        # This is an opt-in measurement of the exact full B projection; the
        # source helper itself admits only each CI-observed resource input.
        # It is not the maintained production selection or runtime admission.
        valid_b = args.b_variant == "control" or (args.entry == "B" and args.b_variant == "tcec-final-lf")
        valid_spelling = (args.spelling_variant == "control" or
                          (args.entry == "B" and args.b_variant == "tcec-final-lf" and
                           args.spelling_variant == "league-atomic" and
                           args.source_dependencies == "unused-includes"))
        if (not valid_b or args.phase_variant != "control" or
                not valid_spelling or args.scan_variant != "control" or
                args.ep_variant != "control"):
            parser.error("league profile source optimizations require their own audited profile pins")
    if args.b_variant != "control" and args.entry != "B":
        parser.error("--b-variant applies only to the independently owned B engine")
    if args.phase_variant != "control" and args.entry not in "ACEF":
        parser.error("--phase-variant applies only to A/C/E/F")
    try:
        post_spelling = spelling_selection(args.entry, args.representation, args.b_variant,
                                           args.phase_variant, args.spelling_variant, profile_id=args.profile)
        post_scan = scan_selection(args.entry, args.representation, args.phase_variant,
                                   post_spelling, args.source_dependencies, args.scan_variant)
        post_ep, ep_owner = None, None
        if args.ep_variant != "control":
            ep_input = normalized(ROOT / EP)
            if {"bytes": len(ep_input), "sha256": sha256(ep_input).hexdigest()} != EP_PIN:
                raise ValueError("reviewed full EP stage differs")
            ep_owner = load("profile_selected_ep", ROOT / EP)
            post_ep = ep_owner.selection(args.entry, args.representation, args.phase_variant,
                post_spelling, post_scan, args.source_dependencies, args.ep_variant)
            if (args.entry, args.profile) not in ep_owner.IMAGES:
                raise ValueError("EP profile has no audited literal source/native cost policy yet")
    except ValueError as error:
        parser.error(str(error))
    out = args.out.resolve()
    if (sys.platform != "linux" or platform.machine() != "x86_64" or
            not args.out.is_absolute() or out.exists() or
            ROOT in (out, *out.parents) or any((p / ".git").exists() for p in (out, *out.parents))):
        parser.error("Linux x86-64 and a new absolute output outside every Git checkout are required")
    source_bytes = normalized(ROOT / SOURCE)
    common_bytes = normalized(ROOT / COMMON)
    league_bytes = normalized(ROOT / LEAGUE_PROFILES) if args.profile in LEAGUE_PROFILE_IDS else None
    executing = normalized(Path(__file__))
    production = load("profile_build_contracts", ROOT / COMMON)
    projection = load("profile_build_projection", ROOT / SOURCE)
    league = load("profile_build_league_profiles", ROOT / LEAGUE_PROFILES) if league_bytes is not None else None
    spec = production.engine_spec(args.entry)
    profile = league.resource_profile(production, args.profile) if league else production.resource_profile(args.profile)
    cleanup = "none" if args.representation == "self-contained-elf" else "private-path"
    plan = production.ArtifactPlan(spec, profile, args.representation, cleanup)
    old = load("profile_build_owner", ROOT / "engines/experiments/tcec-scope/build.py")
    resources = {**profile.to_record(spec.entry_bytes), "ply": 128, "max_position_plies": 4095}
    runtime = old.runtime_policy("per-go", "async", profile.workers)
    runtime.update(initialization_threads=profile.os_threads,
                   initialization_join_before_uci=True, entry_cleanup=cleanup)
    report = dict(format=1, **{"class": CLASS}, entry=args.entry, family=args.entry,
        complete=False, reproducible=False, plan=plan.to_record(), resources=resources,
        runtime_policy=runtime, commands=[], attempts=[], source_proofs=[],
        qualification=dict(selection="new-profile-measurement", runtime=False,
                           rules_eligibility="unproven", game_strength="unproven"),
        authority="fresh maintained tracked-source producer then bound profile projection",
        execution_policy="compile/package only; engine and TT are never executed or allocated here")
    out.mkdir()

    def save():
        (out / "build.json").write_text(json.dumps(report, indent=2) + "\n")

    class Host(old.Host):
        def settle(self, child, row, force=False):
            if row.get("kind") == "fresh-profile-control":
                row["cooperative_termination_seconds"] = 30
            return super().settle(child, row, force)

    old.LIMITS.update(aggregate_wall=1800, per_command_wall=600, parent_AS=4 << 30,
                      child_AS=4 << 30, parent_CPU=300, parent_CPU_hard=480, child_CPU=420)
    previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    host = Host(out, report, save)
    try:
        # This nested builder independently freezes and verifies its complete
        # tracked closure; no caller-supplied control artifact is accepted.
        host.run([sys.executable, "-I", "-B", ROOT / BASELINE, "--entry", args.entry,
                  "--measure", "--out", out / "control"], cwd=out, kind="fresh-profile-control")
        control_raw = (out / "control/build.json").read_bytes()
        control = json.loads(control_raw)
        old.require(control["complete"] and control["reproducible"] and
                    control["host_cleanup"] == {"unsettled_commands": 0, "errors": []} and
                    all(c["returncode"] == 0 and c["terminal"] and c["reaped"] and
                        c["owned_group_absent"] and not c["forced_cleanup"] for c in control["commands"]),
                    "fresh maintained control incomplete or unsettled")
        base = (out / "control/main.c").read_bytes()
        old.require((len(base), old.sha(base)) == projection.INPUTS[args.entry],
                    "fresh maintained profile input differs")
        old.require(normalized(ROOT / SOURCE) == source_bytes and
                    normalized(ROOT / COMMON) == common_bytes and normalized(Path(__file__)) == executing,
                    "executing profile producer changed before input freeze")
        if league_bytes is not None:
            old.require(normalized(ROOT / LEAGUE_PROFILES) == league_bytes,
                        "executing league profile owner changed before input freeze")
        names = set(control["control_source_closure"]) | set(control["inputs"])
        names.update((SELF, COMMON, SOURCE, PACKAGE, WRAPPER, UNLINK))
        if league_bytes is not None:
            names.add(LEAGUE_PROFILES)
        if args.entry == "E":
            names.update(("engines/model/e19.py", "engines/model/e19.json"))
        if args.league_variant != "control":
            names.add(LEAGUE_EXPERIMENTS[args.league_variant]["path"])
            names.update(LEAGUE_SUPPORT.get(args.league_variant, {}))
        if args.b_variant != "control":
            names.add(B_PROFILE)
        if args.phase_variant != "control":
            names.add(PHASE)
        if post_spelling is not None:
            names.add(B_LEAGUE_SPELLING if post_spelling == B_LEAGUE_DECLARATION else SPELLING)
            if post_spelling in (COMPOUND_DECLARATION, F_COMPOUND_DECLARATION):
                names.add(COMPOUND)
        if post_scan is not None:
            names.add(SCAN)
        if post_ep is not None:
            names.update((EP, *(row["path"] for row in ep_owner.SUPPORT.values())))
        if args.source_dependencies != "control":
            names.add(DEPENDENCIES)
        if args.representation in ("packed-native", "self-contained-elf"):
            names.add(ELF)
        if args.representation == "self-contained-elf":
            names.update((ELF, "engines/scripts/elf-loader/loader.c", "engines/scripts/elf-loader/loader.ld"))
        # The new runtime verifier is a proof dependency, never payload code.
        if (ROOT / VERIFIER).is_file():
            names.add(VERIFIER)
        inputs = {}
        for name in sorted(names):
            data = normalized(ROOT / name)
            if name == LEAGUE_PROFILES:
                old.require(data == league_bytes, "league profile owner changed during input freeze")
            expected = control["control_source_closure"].get(name, control["inputs"].get(name))
            old.require(expected is None or old.pin(data) == expected,
                        "tracked baseline input changed after regeneration: " + name)
            target = out / "inputs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            inputs[name] = old.pin(data)
        tools = tuple(name for name in sorted(names) if _tool_path(name, args.entry))
        engine_inputs = list(spec.source_inputs)
        if args.representation == "self-contained-elf":
            engine_inputs.extend(("engines/scripts/elf-loader/loader.c", "engines/scripts/elf-loader/loader.ld"))
        tools = tuple(name for name in tools if name not in engine_inputs)
        closure = production.SourceClosure.validate(spec, engine_inputs=tuple(engine_inputs),
                                                    tool_inputs=tools, submission=True)
        snapshot = production.snapshot_closure(ROOT, closure,
            expected={name: inputs[name]["sha256"] for name in (*closure.engine_inputs, *closure.tool_inputs)})
        producer_paths = set((*closure.engine_inputs, *closure.tool_inputs, *closure.test_inputs))
        report.update(inputs=inputs, source_closure=snapshot.to_record(),
            proof_inputs={name: pin for name, pin in inputs.items() if name not in producer_paths},
            control_source_closure=control["control_source_closure"],
            control=dict(source=old.pin(base), report=old.pin(control_raw),
                         expected_contract=control["expected_contract"], path="control"),
            selected_verifier=dict(path=VERIFIER, command=[sys.executable, "-I", "-B",
                str(ROOT / VERIFIER), "--build", str(out), "--out", "<new external output>"]))
        own = out / "inputs"
        projection = load("profile_frozen_projection", own / SOURCE)
        frozen_production = load("profile_frozen_contracts", own / COMMON)
        if league_bytes is not None:
            frozen_league = load("profile_frozen_league_profiles", own / LEAGUE_PROFILES)
            profile = frozen_league.resource_profile(frozen_production, args.profile)
        else:
            profile = frozen_production.resource_profile(args.profile)
        packaging = load("profile_frozen_package", own / PACKAGE)
        wrapper = load("profile_frozen_wrapper", own / WRAPPER)
        unlink = load("profile_frozen_unlink", own / UNLINK)
        compiler, compression = control["compiler"], control["compression"]
        compile_executor = list(compiler)
        if args.compile_cc:
            compile_executor[0] = args.compile_cc
        report.update(compiler=compiler, compile_executor=compile_executor, compression=compression)
        report["post_profile"] = (dict(path=B_PROFILE, variant=args.b_variant)
            if args.b_variant != "control" else dict(path=PHASE, variant=args.phase_variant)
            if args.phase_variant != "control" else None)
        report["post_spelling"] = post_spelling
        league_helper, league_helpers = None, {}
        if args.league_variant != "control":
            named = LEAGUE_EXPERIMENTS[args.league_variant]
            old.require(inputs[named["path"]] == named["pin"], "league helper identity differs")
            for relative, expected in LEAGUE_SUPPORT.get(args.league_variant, {}).items():
                old.require(inputs[relative] == expected, "league helper support identity differs")
            league_helper = load("profile_frozen_league_candidate", own / named["path"])
            if args.league_variant == "legal-maker":
                ep_path, projection_path = LEAGUE_SUPPORT["legal-maker"]
                old.require(Path(ep_path).name == "compact_ep.py" and projection_path == COMPOUND,
                            "league EP support roles differ")
                league_helpers = {"ep": load("league_candidate_ep", own / ep_path),
                                  "projection": load("league_candidate_projection", own / projection_path)}
            report["post_league"] = post_league
        if post_scan is not None:
            report["post_scan"] = post_scan
        ep_helpers = {}
        if post_ep is not None:
            old.require(inputs[EP] == EP_PIN, "reviewed full EP stage differs")
            ep_owner = load("profile_frozen_ep", own / EP)
            for name, row in ep_owner.SUPPORT.items():
                old.require(inputs[row["path"]] == {key: row[key] for key in ("bytes", "sha256")},
                            "reviewed EP support differs: " + name)
                ep_helpers[name] = load("profile_frozen_ep_" + name, own / row["path"])
            report["post_ep"] = post_ep
        if args.entry == "B" and args.spelling_variant == "compound":
            report["spelling_request"] = dict(requested="compound", effective="best",
                duplicate_best=True, new_candidate_count=0)
        dependencies = (load("profile_frozen_dependencies", own / DEPENDENCIES)
                        if args.source_dependencies != "control" else None)
        report["source_dependencies"] = dict(dependencies.DECLARATION) if dependencies else None
        if args.representation == "source-jit":
            report["wrapper_contract"] = wrapper.contract(packaging, unlink, compiler)
        elif args.representation == "packed-native":
            report["wrapper_contract"] = dict(policy="private-file-native-delayed-directory-cleanup",
                argv0="wrapper-owned private absolute executable path", entry_cleanup=cleanup,
                cleanup_child=True, runtime_qualified=False)
        else:
            report["wrapper_contract"] = dict(policy="self-contained-memfd-loader", entry_cleanup="none",
                temporary_pathname=False, outer_preserved=True, runtime_qualified=False)
        old.LIMITS["child_AS"] = 2 << 30
        old.LIMITS["child_CPU"] = 120
        report["compile_executor_version"] = host.run([compile_executor[0], "--version"], cwd=out,
            kind="target-compiler-version").decode("utf-8", "strict").splitlines()[0]
        header_name, payload_name = (("header.bin", "payload.bin")
            if args.representation == "self-contained-elf" else ("header.sh", "payload.lzma"))
        report["package_parts"] = dict(header=header_name, payload=payload_name,
            codec="rove4k-lz-runs-v1" if args.representation == "self-contained-elf" else "lzma-alone")
        for attempt in ("first", "repeat"):
            directory = out / attempt
            native_dir = directory / "native"
            native_dir.mkdir(parents=True)
            source, proof = projection.transform_source(base, family=args.entry, profile=profile,
                                                        entry_cleanup=cleanup)
            old.require(projection.restore_source(source, proof) == base,
                        "profile projection inverse differs")
            proofs = [proof]
            abi_probe = None
            if args.b_variant != "control":
                b_profile = load("profile_frozen_B_projection", own / B_PROFILE)
                parent_source = source
                source, b_proof = b_profile.transform_source(source, profile_id=profile.id,
                    entry_cleanup=cleanup, variant=args.b_variant)
                old.require(b_profile.restore_source(source, b_proof) == parent_source,
                            "B post-profile inverse differs")
                proofs.append(b_proof)
                abi_probe = b_proof.get("target_abi_probe")
                old.require(abi_probe is None or
                            (isinstance(abi_probe, str) and abi_probe.strip() and "\0" not in abi_probe),
                            "B target ABI probe must be nonempty standalone C text")
            if args.phase_variant != "control":
                phase = load("profile_frozen_phase_projection", own / PHASE)
                parent_source = source
                source, phase_proof = phase.transform_source(source, family=args.entry,
                    profile_id=profile.id, entry_cleanup=cleanup, variant=args.phase_variant)
                old.require(phase.restore_source(source, phase_proof) == parent_source,
                            "portable phase post-profile inverse differs")
                proofs.append(phase_proof)
            if args.entry == "E":
                model_module = load("profile_e19_canonical", own / "engines/model/e19.py")
                model = model_module.Model.load(own / "engines/model/e19.json")
                source_model = model_module.Model.from_physical_source(source,
                    model_id="e19-admitted-source-baseline")
                source, model_proof = model.bind_physical_table(source, source_model=source_model)
                proofs.append(model_proof)
                report["model"] = dict(id=model.model_id, coefficient_sha256=model.coefficient_sha256(),
                    bounds=model.bounds(), source_coefficient_sha256=source_model.coefficient_sha256(),
                    model_parameters_changed=model.coefficients != source_model.coefficients,
                    optimizer_executed_by_builder=False)
            if league_helper is not None:
                before_league = source
                options = dict(family=args.entry, profile_id=profile.id, **league_helpers)
                if args.league_variant == "atomic-assignment":
                    options["variant"] = args.league_variant
                source, league_proof = league_helper.transform_source(source, **options)
                old.require(league_helper.restore_source(source, league_proof, **league_helpers) == before_league,
                            "isolated league experiment inverse differs")
                proofs.append(league_proof)
            if post_spelling is not None:
                parent_source = source
                if post_spelling == B_LEAGUE_DECLARATION:
                    old.require(inputs[B_LEAGUE_SPELLING] == B_LEAGUE_SPELLING_PIN,
                                "reviewed B league spelling helper differs")
                    helper_path = own / B_LEAGUE_SPELLING
                    helper_bytes = normalized(helper_path)
                    league_spelling = load_reviewed_b_league_spelling(helper_bytes, helper_path)
                    source, spelling_proof = league_spelling.transform_source(source, family=args.entry,
                        profile_id=profile.id, variant=post_spelling["variant"])
                    restored_spelling = league_spelling.restore_source(source, spelling_proof)
                elif post_spelling in (COMPOUND_DECLARATION, F_COMPOUND_DECLARATION):
                    old.require(inputs[SPELLING] == SPELLING_PIN, "reviewed individual spelling helper differs")
                    spelling = load("profile_frozen_spelling_projection", own / SPELLING)
                    old.require(inputs[COMPOUND] == COMPOUND_PIN, "reviewed compound helper differs")
                    compound = load("profile_frozen_compound_projection", own / COMPOUND)
                    source, spelling_proof = compound.transform_source(source, family=args.entry,
                        profile_id=profile.id, spelling=spelling, variant=post_spelling["variant"])
                    restored_spelling = compound.restore_source(source, spelling_proof, spelling=spelling)
                else:
                    old.require(inputs[SPELLING] == SPELLING_PIN, "reviewed individual spelling helper differs")
                    spelling = load("profile_frozen_spelling_projection", own / SPELLING)
                    source, spelling_proof = spelling.transform_source(source, family=args.entry,
                        profile_id=profile.id, variant=post_spelling["variant"])
                    restored_spelling = spelling.restore_source(source, spelling_proof)
                old.require(restored_spelling == parent_source,
                            "final spelling source inverse differs before E19/phase/B inverses")
                proofs.append(spelling_proof)
            if post_scan is not None:
                old.require(inputs[SCAN] == SCAN_PIN, "reviewed valid-square helper differs")
                scan = load("profile_frozen_scan_projection", own / SCAN)
                before_scan = source
                source, scan_proof = scan.transform_source(source, family=args.entry, profile_id=profile.id)
                old.require(scan.restore_source(source, scan_proof) == before_scan,
                            "valid-square inverse differs before compound inverse")
                proofs.append(scan_proof)
            if post_ep is not None:
                before_ep = source
                source, ep_proof = ep_owner.transform_source(source, family=args.entry,
                    profile_id=profile.id, **ep_helpers)
                old.require(ep_owner.restore_source(source, ep_proof, **ep_helpers) == before_ep,
                            "full EP lifted inverse differs before final include cleanup")
                proofs.append(ep_proof)
            dependency_gate = None
            before_dependencies = source
            if dependencies:
                source, dependency_proof = dependencies.transform_source(source)
                proofs.append(dependency_proof)
                if source != before_dependencies:
                    dependency_gate = dependencies.compile_gate(before_dependencies, source,
                        compiler=compile_executor, directory=directory / "dependency-gate",
                        run=host.run, prefix=attempt)
            (directory / "main.c").write_bytes(source)
            gate = directory / "target-type-gate"
            gate.mkdir()
            asserted = source + b"\n" + ("\n".join(proof["target_type_assertions"]) + "\n").encode()
            native_policy = compound_native_policy(args.entry, profile.id, post_spelling, source,
                compiler, compile_executor, report["compile_executor_version"])
            scan_policy = (scan_native_policy(args.entry, profile.id, post_scan, source,
                compiler, compile_executor, report["compile_executor_version"]) if post_ep is None else None)
            ep_policy = (ep_owner.native_policy(args.entry, profile.id, source, compiler,
                compile_executor, report["compile_executor_version"]) if post_ep is not None else None)
            if post_spelling in (COMPOUND_DECLARATION, F_COMPOUND_DECLARATION):
                (gate / "asserted.c").write_bytes(asserted)
            host.run(compile_executor, cwd=gate, kind=attempt + "-target-types", data=asserted)
            host.run(compile_executor, cwd=native_dir, kind=attempt + "-compile", data=source)
            native = (native_dir / "x").read_bytes()
            old.require((gate / "x").read_bytes() == native,
                        "target type assertions changed the shipping native image")
            if native_policy is not None:
                old.require(old.pin(native) == native_policy["native"],
                            "F compound native differs from its named three-profile policy")
                old.require(report.get("native_policy", native_policy) == native_policy,
                            "F compound native policy changed between attempts")
                report["native_policy"] = native_policy
            if scan_policy is not None:
                old.require(old.pin(native) == scan_policy["native"], "valid-square named native differs")
                old.require(report.get("scan_native_policy", scan_policy) == scan_policy,
                            "valid-square native policy changed between attempts")
                report["scan_native_policy"] = scan_policy
            if ep_policy is not None:
                old.require(old.pin(native) == ep_policy["native"], "full EP named native differs")
                old.require(report.get("ep_native_policy", ep_policy) == ep_policy,
                            "full EP native policy changed between attempts")
                report["ep_native_policy"] = ep_policy
            if dependency_gate is not None:
                old.require(dependency_gate["native"] == old.pin(native) and
                            (directory / "dependency-gate/x").read_bytes() == native,
                            "include removal changed the native image")
            abi_gate = None
            if abi_probe is not None:
                # ABI assertions are a separate translation unit. In particular,
                # feature macros and system headers never prefix shipping C.
                abi_directory = directory / "target-abi-gate"
                abi_directory.mkdir()
                probe_bytes = abi_probe.encode("utf-8")
                (abi_directory / "probe.c").write_bytes(probe_bytes)
                host.run([*compile_executor, "-c"], cwd=abi_directory,
                         kind=attempt + "-target-abi", data=probe_bytes)
                abi_gate = dict(directory="target-abi-gate", source=old.pin(probe_bytes),
                    object=old.pin((abi_directory / "x").read_bytes()), compile_only=True,
                    production_source_modified=False)
            loader = None
            if args.representation == "source-jit":
                header = wrapper.header(packaging, unlink, compiler)
                whole = wrapper.package(packaging, unlink, source, compression, compiler)
                payload = whole[len(header):]
                decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                old.require(decoder.decompress(payload, max_length=len(source) + 1) == source and
                            decoder.eof and not decoder.unused_data, "strict source restoration differs")
            elif args.representation == "packed-native":
                elf = load("profile_native_elf_admission", own / ELF)
                whole = packaging.package_shell(native, compression, kind="native", elf_admission=elf._elf)
                header = packaging.shell_header(kind="native")
                payload = whole[len(header):]
                decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                old.require(decoder.decompress(payload, max_length=len(native) + 1) == native and
                            decoder.eof and not decoder.unused_data, "strict native restoration differs")
            else:
                raw = host.run([sys.executable, "-I", "-B", own / ELF, native_dir / "x",
                                directory / "x", "--timeout", "120", "--cc", compile_executor[0]], cwd=directory,
                               kind=attempt + "-self-contained-loader")
                loader = json.loads(raw)
                whole = (directory / "x").read_bytes()
                boundary = loader["loader_and_headers_bytes"]
                header, payload = whole[:boundary], whole[boundary:]
                old.require(len(payload) == loader["payload_bytes"] and
                            loader["input_sha256"] == old.sha(native), "loader/native identity differs")
                elf = load("profile_elf_restore_check", own / ELF)
                restored = elf._decompress(payload, len(native))
                if loader["filter"] == "bcj":
                    restored = elf._bcj(restored, inverse=True)
                old.require(restored == native, "actual self-contained payload restoration differs")
                loader["actual_output_payload_restores_native"] = True
            old.require(whole.startswith(header), "package header differs")
            if dependency_gate is not None:
                before_whole = (wrapper.package(packaging, unlink, before_dependencies, compression, compiler)
                                if args.representation == "source-jit" else whole)
                old.require(len(whole) <= len(before_whole), "include removal grew the complete artifact")
                dependency_gate["whole_cost"] = dict(before=len(before_whole), after=len(whole))
            for name, data in (("main.c", source), ("x", whole), (header_name, header),
                               (payload_name, payload)):
                (directory / name).write_bytes(data)
            (directory / "x").chmod(0o700)
            (directory / "source-proof.json").write_text(json.dumps(proofs, indent=2) + "\n")
            actual = {kind + "_" + key: value for kind, data in
                      (("source", source), ("native", native), ("whole", whole),
                       ("header", header), ("payload", payload)) for key, value in old.pin(data).items()}
            report["attempts"].append(dict(directory=attempt, **actual, source_proofs=proofs,
                target_type_gate=dict(assertions=proof["target_type_assertions"],
                    source=old.pin(asserted), native=old.pin(native), image_identical=True), loader=loader,
                dependency_gate=dependency_gate))
            if native_policy is not None:
                report["attempts"][-1]["target_type_gate"].update(directory="target-type-gate",
                    source_file="asserted.c", policy=native_policy["kind"])
            if abi_gate is not None:
                report["attempts"][-1]["target_abi_gate"] = abi_gate
            if dependencies:
                def checked(root, name, expected):
                    data = (root / name).read_bytes()
                    old.require(old.pin(data) == expected, "dependency evidence identity differs: " + name)
                    return data
                dependencies.validate_receipt(out, report, dependency_proof, source, checked=checked)
            save()
        a, b = report["attempts"]
        # Loader command metadata contains its own output path; byte identity,
        # proof and target types are the reproducibility contract.
        same = lambda row: {k: v for k, v in row.items() if k not in ("directory", "loader")}
        old.require(same(a) == same(b), "independent profile reproduction differs")
        report["expected_contract"] = {key: value for key, value in a.items()
            if key not in ("directory", "source_proofs", "target_type_gate", "target_abi_gate", "loader", "dependency_gate")}
        report["source_proofs"] = a["source_proofs"]
        report["actual"] = dict(source="main.c", native="native/x", program="x")
        for name in ("main.c", "native/x", "x", header_name, payload_name, "source-proof.json"):
            target = out / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(out / "first" / name, target)
        (out / "x").chmod(0o700)
        report["qualification"]["divisions"] = [plan.size_decision(len((out / "x").read_bytes()), division)
                                                for division in ("general4k", "elf4k")]
        report.update(complete=True, reproducible=True)
        save()
    except BaseException as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        save()
        raise
    finally:
        try:
            host.close()
        finally:
            signal.signal(signal.SIGCHLD, previous)
    print(json.dumps(dict(entry=args.entry, profile=args.profile, representation=args.representation,
                          whole=report["expected_contract"]["whole_bytes"], complete=True)))


if __name__ == "__main__":
    main()
