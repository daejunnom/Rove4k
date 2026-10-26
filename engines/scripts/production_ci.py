#!/usr/bin/env python3
"""Run one selected TEST-P4 functional pipeline in a fresh CI temporary tree.

Generation, instrumented mechanisms, actual rules and shipping runtime retain
their own receipts. This driver does not admit a league player, confirm TCEC
allocation, or turn a passing functional job into size/placement acceptance.

--export-source-bundle adds source-bundle.zip and source-seal.json after the
Ubuntu24 pipeline settles. --ubuntu22-target consumes that exact pair, restores
its original owned paths, and writes independent compiler/rules/runtime evidence
under a separate --out. The source factory is not run on the target host.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import signal
import sys

sys.dont_write_bytecode = True
_EXECUTING_CODE = sys._getframe().f_code
ROOT = Path(__file__).resolve().parents[2]
SELF = "engines/scripts/production_ci.py"
HOST = "engines/experiments/tcec-scope/build.py"
HOST_SHA = "5fa10c6f8f032be374bf3a86bbe6ca558076630a2cc3170b41890f691688f563"
NEXT = "engines/experiments/tcec-next/"
D_ROOT = "engines/experiments/tiny-d-submission/"
SCHEMA = "rove4k-production-ci-functional-v1"
D_CANDIDATE = "D-packed-xz-bcj"
BEST_SPELLING = {"A": "clock-type", "B": "atomic-assignment", "C": "clock-type",
                 "E": "clock-type", "F": "atomic-assignment"}
COMPOUND_SPELLING = {"path": NEXT + "spelling_compound.py", "selection": "compound",
                     "variant": "clock-atomic-launcher"}
SCAN_DECLARATION = {"path": NEXT + "profile_scan.py", "variant": "square-successor"}
PROFILE_WORKERS = {"test-p4": 4, "test-p28": 28}
TRANSPORT = "engines/scripts/production_source_bundle.py"
COMPILER_REDIRECTION = ("CC", "CXX", "CPP", "AS", "AR", "LD", "GCC_EXEC_PREFIX", "COMPILER_PATH",
    "LIBRARY_PATH", "CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "OBJC_INCLUDE_PATH",
    "CFLAGS", "CPPFLAGS", "CXXFLAGS", "LDFLAGS")
QUALIFICATION_CHECKS = ("reproduction", "startup", "dependencies", "cleanup", "protocol",
                        "legal_moves", "resources", "lifecycle", "size", "placement")


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def same_value(actual, expected):
    """Compare new typed receipt records without Python's bool/int coercion."""
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return actual.keys() == expected.keys() and all(same_value(actual[key], value) for key, value in expected.items())
    if type(expected) is list:
        return len(actual) == len(expected) and all(same_value(a, b) for a, b in zip(actual, expected))
    return actual == expected


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_captured(name, path, data):
    """Execute the already pinned Python source, without reopening its pathname."""
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(path))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(data, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


def normalized(path, *, reader=None):
    data = (reader.read_regular(path, limit=16 << 20) if reader is not None else path.read_bytes()).replace(b"\r\n", b"\n")
    require(b"\r" not in data, "lone CR in named CI source")
    return data


def admit_output(out, runner_temp):
    """Do not create output until it is a new child of the real runner root."""
    out, runner_temp = Path(out), Path(runner_temp)
    require(out.is_absolute() and runner_temp.is_absolute() and runner_temp.is_dir(),
            "absolute output and existing RUNNER_TEMP required")
    require(".." not in out.parts and ".." not in runner_temp.parts and
            not any(p.is_symlink() for p in (out, *out.parents, runner_temp, *runner_temp.parents)),
            "CI paths cannot use traversal or filesystem links")
    out, runner_temp = out.resolve(), runner_temp.resolve()
    require(out != runner_temp and out.is_relative_to(runner_temp) and not out.exists(),
            "output must be a new child of RUNNER_TEMP")
    require(ROOT not in (out, *out.parents) and
            not any((p / ".git").exists() for p in (out, *out.parents)),
            "CI products must remain outside every Git checkout")
    return out


@dataclass(frozen=True)
class Stage:
    name: str
    command: tuple[str, ...]
    receipt: str


@dataclass(frozen=True)
class Plan:
    family: str
    out: Path
    stages: tuple[Stage, ...]
    spelling_variant: str = "control"
    profile: str = "test-p4"
    scan_variant: str = "control"

    @property
    def effective_spelling_variant(self):
        return effective_spelling(self.family, self.spelling_variant, profile=self.profile)

    @property
    def workers(self):
        return profile_workers(self.profile)


@dataclass(frozen=True)
class TargetPlan:
    family: str
    out: Path
    build: Path
    bundle: Path
    seal: Path
    stages: tuple[Stage, ...]
    profile: str = "test-p4"

    @property
    def workers(self):
        return profile_workers(self.profile)


def target_environment(environment):
    require(environment.get("PATH") == "/usr/bin:/bin" and
            not any(name.startswith("LD_") or name in COMPILER_REDIRECTION for name in environment),
            "Ubuntu22 target requires sanitized system PATH and no loader/compiler redirection variables")


def profile_workers(profile):
    require(type(profile) is str and profile in PROFILE_WORKERS, "explicit TEST-P4 or TEST-P28 profile required")
    return PROFILE_WORKERS[profile]


def p28_resources(family, resources):
    """The new path cannot relabel a smaller TT or worker allocation as P28."""
    bits, entry = (25, 16) if family == "D" else (24, 24)
    expected = {"id": "test-p28", "workers": 28, "tt_cap_bytes": 512 << 20,
                "tt_bits": bits, "tt_entries": 1 << bits, "tt_bytes": (1 << bits) * entry,
                "tt_entry_bytes": entry, "tt_mask": (1 << bits) - 1}
    require(type(resources) is dict and all(type(resources.get(key)) is type(value) and
            resources[key] == value for key, value in expected.items()),
            "TEST-P28 requires the exact actual worker/TT resource geometry")


def producer_spelling_variant(family, selection, *, profile="test-p4"):
    require(family in tuple("ABCDEF"), "one active C family A through F is required")
    profile_workers(profile)
    require(type(selection) is str and selection in ("control", "best", "compound"), "finite producer spelling selection required")
    require(family != "D" or selection == "control", "D supports only control spelling")
    if profile == "test-p28":
        require((family in "ACEF" and selection == "compound") or
                (family == "B" and selection in ("best", "compound")) or (family == "D" and selection == "control"),
                "TEST-P28 requires ACEF compound, B best/compound, or D control")
    return selection


def effective_spelling(family, selection, *, profile="test-p4"):
    selection = producer_spelling_variant(family, selection, profile=profile)
    return "best" if family == "B" and selection == "compound" else selection


def spelling_declaration(family, selection, *, profile="test-p4"):
    effective = effective_spelling(family, selection, profile=profile)
    if effective == "control":
        return None
    if effective == "compound":
        return dict(COMPOUND_SPELLING)
    return {"path": NEXT + "profile_spelling.py", "selection": "best", "variant": BEST_SPELLING[family]}


def target_plan(family, out, build, bundle, seal, *, profile="test-p4", python=sys.executable, repo=ROOT):
    """Consume sealed Ubuntu24 source; never replay its factory with cc11."""
    require(family in tuple("ABCDEF"), "one active C family A through F is required")
    profile_workers(profile)
    out, build, bundle, seal, repo = map(Path, (out, build, bundle, seal, repo))
    require(all(path.is_absolute() for path in (out, build, bundle, seal, repo)), "absolute target pipeline roots required")
    def command(script, *arguments):
        return tuple(map(str, (python, "-I", "-B", repo / script, *arguments)))
    compiler = command(NEXT + "profile_compiler.py", "--build", build, "--compiler", "/usr/bin/cc",
        "--ubuntu22-system", "--source-bundle", bundle, "--source-seal", seal, "--out", out / "compiler")
    rules = (command(D_ROOT + "profile_rules.py", "--build", build, "--out", out / "rules") if family == "D" else
        command(NEXT + "profile_rules.py", "--source", build / "main.c", "--baseline", build / "control/main.c",
            "--proof", build / "source-proof.json", "--family", family, "--profile", profile, "--build", build,
            "--out", out / "rules"))
    candidate = ("--candidate", "D-source-jit") if family == "D" else ()
    runtime = command(NEXT + "profile_verify.py", "--build", build, *candidate,
        "--rules", out / "rules/probe/rules.json", "--target-compiler-receipt", out / "compiler/compiler.json",
        "--source-bundle", bundle, "--source-seal", seal, "--out", out / "runtime")
    return TargetPlan(family, out, build, bundle, seal, (
        Stage("compiler", compiler, "compiler/compiler.json"), Stage("rules", rules, "rules/commands.json"),
        Stage("runtime", runtime, "runtime/runtime.json")), profile)


def producer_scan_variant(family, spelling, selection):
    require(type(selection) is str and selection in ("control", "square-successor"), "finite scan selection required")
    require(selection == "control" or (family in ("A", "C") and spelling == "compound"),
            "square-successor requires the explicit A/C compound route")
    return selection


def pipeline_plan(family, out, *, spelling_variant="control", scan_variant="control", profile="test-p4", python=sys.executable, repo=ROOT):
    spelling_variant = producer_spelling_variant(family, spelling_variant, profile=profile)
    scan_variant = producer_scan_variant(family, spelling_variant, scan_variant)
    out, repo = Path(out), Path(repo)
    require(out.is_absolute() and repo.is_absolute(), "absolute pipeline roots required")
    artifact = out / "artifact"
    def command(script, *arguments):
        return tuple(map(str, (python, "-I", "-B", repo / script, *arguments)))
    if family == "D":
        generation = command(D_ROOT + "build.py", "--profile", profile, "--storage", "prefix", "--out", artifact)
        mechanism = command(D_ROOT + ("check_profile_p28.py" if profile == "test-p28" else "test_startup.py"),
                            "--build", artifact, "--out", out / "mechanism")
        rules = command(D_ROOT + "profile_rules.py", "--build", artifact, "--out", out / "rules")
        runtime = command(NEXT + "profile_verify.py", "--build", artifact, "--candidate", D_CANDIDATE,
                          "--rules", out / "rules/probe/rules.json", "--out", out / "runtime")
    else:
        variant = ("--b-variant", "tcec-final-lf") if family == "B" else ("--phase-variant", "phase-init")
        generation = command(NEXT + "profile_build.py", "--entry", family, "--profile", profile,
                             *variant, "--spelling-variant", spelling_variant,
                             *(("--scan-variant", scan_variant) if scan_variant != "control" else ()),
                             "--source-dependencies", "unused-includes", "--out", artifact)
        mechanism = (command(NEXT + "check_profile_scan.py", "--build", artifact, "--out", out / "mechanism")
                     if scan_variant != "control" else
                     command(NEXT + "check_profile_p28.py", "--build", artifact, "--out", out / "mechanism")
                     if profile == "test-p28" else
                     command(NEXT + "check_profile_b.py", "--build", artifact, "--mode", "bound", "--out", out / "mechanism")
                     if family == "B" else command(NEXT + ("check_profile_compound.py"
                         if effective_spelling(family, spelling_variant) == "compound" else "check_profile_phase.py"),
                         "--build", artifact, "--out", out / "mechanism"))
        rules = command(NEXT + "profile_rules.py", "--source", artifact / "main.c", "--baseline", artifact / "control/main.c",
                        "--proof", artifact / "source-proof.json", "--family", family, "--profile", profile,
                        "--build", artifact, "--out", out / "rules")
        runtime = command(NEXT + "profile_verify.py", "--build", artifact,
                          "--rules", out / "rules/probe/rules.json", "--out", out / "runtime")
    return Plan(family, out, (
        Stage("generation", generation, "artifact/build.json"),
        Stage("mechanism", mechanism, "mechanism/result.json" if family == "B" and profile == "test-p4" else "mechanism/results.json"),
        Stage("rules", rules, "rules/commands.json"),
        Stage("runtime", runtime, "runtime/runtime.json")), spelling_variant, profile, scan_variant)


def evidence_bytes(out, relative, *, reader=None):
    path = Path(out) / relative
    require(not any(p.is_symlink() for p in (path, *path.parents)), "receipt cannot follow filesystem links")
    path = path.resolve(strict=True)
    require(path.is_relative_to(Path(out).resolve()) and path.is_file() and path.stat().st_nlink == 1
            and path.stat().st_size <= 64 << 20, "bounded ordinary pipeline receipt required")
    data = reader.read_regular(path, limit=64 << 20) if reader is not None else path.read_bytes()
    return data, {"path": str(path), **pin(data)}


def receipt(out, relative, *, reader=None):
    data, identity = evidence_bytes(out, relative, reader=reader)
    return json.loads(data), identity


def compiler_record(banner, version):
    first = banner.decode("ascii").splitlines()[0]
    actual = version.decode("ascii").strip()
    require(first.lower().startswith(("cc ", "gcc ")) and "clang" not in first.lower()
            and re.fullmatch(r"13\.[0-9]+(?:\.[0-9]+)?", actual) is not None,
            "ordinary Ubuntu24 generation requires its default GCC13 cc; alternate target compilers use a separate pipeline")
    return {"command": "cc", "version": first, "full_version": actual,
            "banner": pin(banner), "version_output": pin(version),
            "scope": "host backend admission; native literal checks remain in the maintained producers"}


def target_compiler_record(banner, version):
    first = banner.decode("ascii").splitlines()[0]
    actual = version.decode("ascii").strip()
    require(first.lower().startswith(("cc ", "gcc ")) and "clang" not in first.lower() and actual == "11.4.0",
            "Ubuntu22 target requires actual system cc11.4.0")
    return {"command": "/usr/bin/cc", "version": first, "full_version": actual,
            "banner": pin(banner), "version_output": pin(version),
            "scope": "observed system compiler; compiler receipt and reference bind target image independently"}


def owned_commands(report, *, expected_codes=None):
    expected_codes = expected_codes or {}
    require(report.get("complete") is True and report.get("host_cleanup") == {"unsettled_commands": 0, "errors": []},
            "nested stage did not complete its owned cleanup")
    commands = report.get("commands")
    require(isinstance(commands, list) and commands, "nested command ownership evidence is missing")
    for row in commands:
        require(all(row.get(key) is True for key in ("started", "terminal", "reaped", "owned_group_absent",
                    "original_identity_retained_until_other_members_absent"))
                and row.get("forced_cleanup") is False and row.get("other_group_members_before_reap") == []
                and type(row.get("returncode")) is int
                and row.get("returncode") == expected_codes.get(row.get("kind"), 0),
                "nested command failed, was forced, or lost its original ownership")
    require(all(sum(row.get("kind") == kind for row in commands) == 1 for kind in expected_codes),
            "required natural negative-control command is missing or duplicated")


def scan_mechanism_policy(plan, report, build, *, reader=None):
    require(producer_scan_variant(plan.family, plan.spelling_variant, plan.scan_variant) == "square-successor"
            and report.get("class") == "rove4k-bound-scan-mechanism-v1"
            and report.get("selected_post_scan") == build.get("post_scan") == SCAN_DECLARATION,
            "scan mechanism differs from the explicit producer choice")
    raw, _ = evidence_bytes(plan.out, "artifact/source-proof.json", reader=reader)
    require(same_value(report.get("source_proofs"), pin(raw)) and
            same_value(json.loads(raw), build.get("source_proofs")), "scan mechanism raw proof differs")
    name = NEXT + "check_profile_scan.py"
    captured, _ = evidence_bytes(plan.out, "inputs/" + name, reader=reader)
    require(captured == normalized(ROOT / name, reader=reader) and
            same_value(report.get("support_inputs", {}).get(name), pin(captured)),
            "scan checker differs from its frozen current CI input")
    checker = load_captured("production_ci_frozen_scan_policy", plan.out / "inputs" / name, captured)
    require(checker.bound_selection(build) == plan.profile, "scan mechanism resource/stage grammar differs")


def compound_mechanism(plan, report, build, *, reader=None):
    """Keep the named diagnostic alias separate from the actual startup source."""
    require(plan.family in "ACEF" and plan.effective_spelling_variant == "compound"
            and report.get("entry") == build.get("family") == plan.family
            and report.get("profile") == "test-p4" and report.get("mode") == "source-bound"
            and report.get("representation") == "source-jit"
            and report.get("selected_post_spelling") == build.get("post_spelling") == COMPOUND_SPELLING
            and report.get("selected_post_profile") == build.get("post_profile") ==
                {"path": NEXT + "profile_phase.py", "variant": "phase-init"}
            and report.get("source_dependencies") == build.get("source_dependencies") ==
                {"path": NEXT + "profile_dependencies.py", "variant": "unused-includes"},
            "compound mechanism selected a different source policy")
    require(all(report.get(field) is False for field in
                ("shipping_binary_executed", "large_submission_tt_executed", "derived_other_resource_profiles",
                 "timing_claimed", "production_adopted", "runtime_qualified"))
            and [row.get("kind") for row in report["commands"]] ==
                ["selected-W4-scaled-callback-compile", "selected-W4-scaled-callback-execute",
                 "selected-W4-last-initializer-compile"],
            "compound mechanism scope or owned command sequence differs")
    source, _ = evidence_bytes(plan.out, "artifact/main.c", reader=reader)
    source_pin = pin(source)
    replacement = "J" if plan.family == "F" else "rv"
    text = "\n#define rv_spawn " + replacement + "\n"
    prefix = source + text.encode()
    original_tt = b"#define RVN ((size_t)1<<22)\n"
    require(prefix.count(original_tt) == 1, "one fixed TEST-P4 TT declaration required for the scaled diagnostic")
    scaled_prefix = (b"#define main rv_unused_shipping_main\n" +
                     prefix.replace(original_tt, b"#define RVN ((size_t)1<<18)\n", 1))
    proofs = [row for row in build.get("source_proofs", [])
              if row.get("schema") == "rove4k.selected-spelling-compound.v1"]
    require(len(proofs) == 1 and proofs[0].get("family") == plan.family
            and proofs[0].get("profile_id") == "test-p4"
            and proofs[0].get("variant") == "clock-atomic-launcher"
            and proofs[0].get("components") == ["clock-type", "atomic-assignment", "launcher-short"],
            "one admitted compound mechanism proof required")
    launchers = [row.get("proof") for row in proofs[0].get("individual", [])
                 if row.get("variant") == "launcher-short"]
    require(len(launchers) == 1 and type(launchers[0]) is dict,
            "one authenticated diagnostic launcher component required")
    alias = {"macro": "rv_spawn", "replacement": replacement, "text": text,
             "shipping_source": source_pin, "diagnostic_prefix": pin(prefix), "launcher_component": launchers[0]}
    require(report.get("diagnostic_alias") == alias
            and report.get("actual", {}).get("source") == {"path": "main.c", **source_pin},
            "compound diagnostic alias is not bound to the shipping source and launcher proof")
    name = NEXT + ("check_profile_scan.py" if plan.scan_variant != "control" else "check_profile_compound.py")
    checker, _ = evidence_bytes(plan.out, "inputs/" + name, reader=reader)
    require(report.get("support_inputs", {}).get(name) == pin(checker),
            "compound diagnostic checker differs from the frozen CI input")
    rows, barriers = report.get("mechanisms", []), report.get("startup_barriers", [])
    require(len(rows) == len(barriers) == 1 and report.get("runtime_cleanup") ==
            {"remaining_owned": 0, "drained": [], "errors": []},
            "compound mechanism and runtime cleanup are incomplete")
    scaled, barrier = rows[0], barriers[0]
    for field, expected in (("profile", "test-p4"), ("variant", "clock-atomic-launcher"),
            ("shipping_source", source_pin), ("diagnostic_prefix_source", pin(prefix)),
            ("fixture_tt_entries", 1 << 18), ("selector_results", ["bestmove g1f3", "bestmove b1c3"])):
        require(scaled.get(field) == expected, "compound scaled diagnostic identity differs")
    require(scaled.get("shipping_worker_count_unchanged") is True and
            all(scaled.get(field) is False for field in
                ("shipping_tt_executed", "shipping_binary_executed", "search_executed")),
            "scaled compound diagnostic claims shipping execution")
    actual_prefix, _ = evidence_bytes(plan.out, "mechanism/selected-W4-scaled-callback/diagnostic-prefix.c", reader=reader)
    fixture, _ = evidence_bytes(plan.out, "mechanism/selected-W4-scaled-callback/fixture.c", reader=reader)
    native, _ = evidence_bytes(plan.out, "mechanism/selected-W4-scaled-callback/x", reader=reader)
    scaled_output, scaled_output_pin = evidence_bytes(plan.out,
        "mechanism/tool-2-selected-W4-scaled-callback-execute.stdout", reader=reader)
    startup, _ = evidence_bytes(plan.out, "mechanism/selected-W4-last-initializer/fixture.c", reader=reader)
    output, _ = evidence_bytes(plan.out, "mechanism/selected-W4-last-initializer/runtime.stdout", reader=reader)
    require(actual_prefix == prefix and fixture.startswith(scaled_prefix) and scaled.get("fixture_source") == pin(fixture)
            and scaled.get("native") == pin(native) and startup.startswith(source)
            and b"#define rv_spawn" not in startup and barrier.get("fixture_source") == pin(startup)
            and barrier.get("output") == pin(output),
            "compound diagnostic or alias-free startup bytes differ from their receipts")
    lines = scaled_output.decode("ascii").splitlines()
    require(len(lines) == 3 and lines[:2] == scaled["selector_results"]
            and scaled.get("output") == pin(scaled_output)
            and report["commands"][1].get("stdout") == scaled_output_pin,
            "compound scaled selector output differs from the owned raw stdout")
    observation = json.loads(lines[2])
    flags = ("every_callback_entered", "all_entries_initialized", "worker_storage_unchanged_except_id_depth",
             "pending_zero", "join_count_zero", "startup_history_zero")
    require(type(observation) is dict and set(observation) == {"workers", "entries", *flags}
            and type(observation["workers"]) is int and observation["workers"] == 4
            and type(observation["entries"]) is int and observation["entries"] == 1 << 18
            and all(observation[field] is True for field in flags) and scaled.get("observation") == observation,
            "compound scaled callbacks did not establish the declared state")
    require(barrier.get("shipping_source") == source_pin and barrier.get("variant") == "clock-atomic-launcher"
            and barrier.get("diagnostic_alias_applied") is False and barrier.get("shipping_identity_claimed") is False
            and barrier.get("actual_resource_profile") == "test-p4" and barrier.get("actual_tt_entries") == 1 << 22
            and all(barrier.get(field) is True for field in
                ("gate_arrival_observed", "post_GO2_join_observed", "private_copy_removed")),
            "compound startup did not retain unaliased actual resource and join evidence")
    physical, cleanup = barrier.get("physical", {}), barrier.get("cleanup", {})
    require(type(physical.get("returncode")) is int and physical["returncode"] == 0
            and all(physical.get(field) is True for field in
                ("readers_joined", "stdout_eof", "stderr_eof", "reaped", "original_identity_retained_until_other_members_absent"))
            and physical.get("forced_cleanup") is False and physical.get("pre_reap_other_members") == []
            and cleanup.get("forced_cleanup") is False and cleanup.get("errors") == []
            and all(cleanup.get(field) is True for field in
                ("settled_before_cleanup", "owned_group_absent", "readers_joined", "reaped"))
            and cleanup.get("pre_reap_other_members") == [],
            "compound startup ownership did not finish naturally")
    journal = report.get("barrier_runtime_cleanup", [])
    require(len(journal) == 1 and type(journal[0]) is dict and set(journal[0]) == {"directory", "pid", "cleanup"}
            and journal[0]["directory"] == str(plan.out / "mechanism/selected-W4-last-initializer/runtime")
            and type(journal[0]["pid"]) is int and journal[0]["pid"] > 0 and journal[0]["cleanup"] == cleanup,
            "compound startup cleanup journal differs from the owned barrier")
    return alias


def p28_startup(plan, report, barrier, source, *, reader=None):
    """Bind the separate unpoisoned main to actual W28 startup and ownership."""
    directory = "mechanism/selected-W28-last-initializer/"
    fixture, _ = evidence_bytes(plan.out, directory + "fixture.c", reader=reader)
    native, _ = evidence_bytes(plan.out, directory + "x", reader=reader)
    output, _ = evidence_bytes(plan.out, directory + "runtime.stdout", reader=reader)
    bits, entry = (25, 16) if plan.family == "D" else (24, 24)
    require(fixture.startswith(source) and same_value(barrier.get("fixture_source"), pin(fixture))
            and same_value(barrier.get("native"), pin(native)) and same_value(barrier.get("output"), pin(output))
            and same_value(barrier.get("shipping_source"), pin(source))
            and barrier.get("actual_resource_profile") == "test-p28"
            and all(type(barrier.get(key)) is int and barrier[key] == value for key, value in
                (("actual_workers", 28), ("actual_tt_entries", 1 << bits), ("actual_tt_bytes", (1 << bits) * entry),
                 ("tt_entry_bytes", entry), ("startup_deadline_ms", 60000), ("legal_search_relaunches", 2)))
            and all(barrier.get(key) is True for key in ("last_initializer_delayed", "gate_arrival_observed",
                "no_uci_before_release", "uci_ready_after_release", "startup_includes_intentional_hold",
                "private_copy_removed", "post_GO2_join_observed"))
            and all(barrier.get(key) is False for key in ("shipping_identity_claimed", "diagnostic_alias_applied",
                "resource_constants_changed", "all_workers_positive_CPU_claimed")),
            "P28 startup source/resource/deadline/gate evidence differs")
    elapsed = barrier.get("instrumented_native_startup_ms")
    require(type(elapsed) in (int, float) and math.isfinite(elapsed) and 0 <= elapsed <= 60000,
            "P28 single startup budget was not met")
    lines = output.splitlines()
    moves = [line[9:] for line in lines if line.startswith(b"bestmove ")]
    legal = {f"{file}2{file}{rank}".encode() for file in "abcdefgh" for rank in "34"} | {b"b1a3", b"b1c3", b"g1f3", b"g1h3"}
    require(lines.count(b"uciok") == 1 and lines.count(b"readyok") == 4 and len(moves) == 2
            and all(move in legal for move in moves), "P28 startup raw protocol/search output differs")
    physical, cleanup = barrier.get("physical", {}), barrier.get("cleanup", {})
    require(type(physical.get("returncode")) is int and physical["returncode"] == 0
            and all(physical.get(key) is True for key in ("readers_joined", "stdout_eof", "stderr_eof", "reaped",
                "original_identity_retained_until_other_members_absent"))
            and physical.get("forced_cleanup") is False and physical.get("pre_reap_other_members") == []
            and cleanup.get("forced_cleanup") is False and cleanup.get("errors") == []
            and all(cleanup.get(key) is True for key in ("settled_before_cleanup", "owned_group_absent", "readers_joined", "reaped"))
            and cleanup.get("pre_reap_other_members") == []
            and same_value(report.get("runtime_cleanup"), {"remaining_owned": 0, "drained": [], "errors": []}),
            "P28 startup ownership did not finish naturally")
    journal = report.get("barrier_runtime_cleanup", [])
    require(len(journal) == 1 and type(journal[0]) is dict and set(journal[0]) == {"directory", "pid", "cleanup"}
            and journal[0]["directory"] == str(plan.out / directory / "runtime")
            and type(journal[0]["pid"]) is int and journal[0]["pid"] > 0 and same_value(journal[0]["cleanup"], cleanup),
            "P28 startup cleanup journal differs from the owned barrier")


def p28_abcef_mechanism(plan, report, build, build_pin, *, reader=None):
    """Use the frozen pure renderer to reconstruct diagnostic C; never run it."""
    require(report.get("class") == ("rove4k-bound-scan-mechanism-v1" if plan.scan_variant != "control"
                                   else "rove4k-bound-p28-mechanism-v1") and report.get("mode") == "source-bound"
            and report.get("entry") == build.get("family") == plan.family and report.get("profile") == plan.profile
            and report.get("representation") == "source-jit" and same_value(report.get("build"),
                {**build_pin, "path": str(Path(build_pin["path"]).parent)})
            and same_value(report.get("resources"), build.get("resources"))
            and report.get("selected_post_spelling") == build.get("post_spelling") ==
                spelling_declaration(plan.family, plan.spelling_variant, profile=plan.profile)
            and report.get("selected_post_profile") == build.get("post_profile") ==
                {"path": NEXT + ("profile_b.py" if plan.family == "B" else "profile_phase.py"),
                 "variant": "tcec-final-lf" if plan.family == "B" else "phase-init"}
            and report.get("source_dependencies") == build.get("source_dependencies") ==
                {"path": NEXT + "profile_dependencies.py", "variant": "unused-includes"}
            and type(build.get("source_closure")) is dict
            and same_value(report.get("source_closure"), build["source_closure"]),
            "P28 mechanism differs from the selected source/build policy")
    p28_resources(plan.family, report["resources"])
    require(all(report.get(key) is False for key in ("production_adopted", "runtime_qualified", "placement_qualified",
                "timing_claimed", "NUMA_qualified", "shipping_binary_executed", "W256_executed"))
            and [row.get("kind") for row in report["commands"]] ==
                ["selected-W28-full-callback-compile", "selected-W28-full-callback-execute",
                 "selected-W28-last-initializer-compile"], "P28 callback scope or owned commands differ")
    source = None
    for role, relative in (("source", "main.c"), ("native", "native/x"), ("whole", "x")):
        data, _ = evidence_bytes(plan.out, "artifact/" + relative, reader=reader)
        require(same_value(report.get("actual", {}).get(role), {"path": relative, **pin(data)}) and
                same_value(pin(data), {key: build["expected_contract"][role + "_" + key] for key in ("bytes", "sha256")}),
                "P28 selected source/native/whole bytes differ")
        if role == "source":
            source = data
    proof_raw, _ = evidence_bytes(plan.out, "artifact/source-proof.json", reader=reader)
    require(same_value(report.get("source_proofs"), pin(proof_raw)) and same_value(json.loads(proof_raw), build.get("source_proofs")),
            "P28 source proof differs from the selected manifest")
    name = NEXT + "check_profile_p28.py"
    checker, _ = evidence_bytes(plan.out, "inputs/" + name, reader=reader)
    require(checker == normalized(ROOT / name, reader=reader) and same_value(report.get("support_inputs", {}).get(name), pin(checker)),
            "P28 checker differs from the frozen current CI input")
    renderer = load_captured("production_ci_frozen_p28_renderer", plan.out / "inputs" / name, checker)
    compiler = build.get("compiler")
    require(type(compiler) is list and compiler and all(type(part) is str for part in compiler),
            "P28 selected compile argv is missing")
    callback_directory = plan.out / "mechanism/selected-W28-full-callback"
    startup_directory = plan.out / "mechanism/selected-W28-last-initializer"
    expected_commands = (([*compiler, "-Wl,--wrap=pthread_create"], callback_directory),
        ([str(callback_directory / "x")], callback_directory),
        ([*compiler, "-Wl,--wrap=pthread_create"], startup_directory))
    require(all(row.get("command") == argv and row.get("cwd") == str(directory)
            for row, (argv, directory) in zip(report["commands"], expected_commands)),
            "P28 compile/execute argv or owned working directory differs")
    expected_fixture, expected_observation, expected_trace, expected_geometry = renderer.full_callback_fixture(
        source, plan.family, build["source_proofs"][0])
    rows, barriers = report.get("mechanisms", []), report.get("startup_barriers", [])
    require(len(rows) == len(barriers) == 1, "P28 requires one full callback and separate actual startup")
    callback = rows[0]
    prefix = "mechanism/selected-W28-full-callback/"
    fixture, _ = evidence_bytes(plan.out, prefix + "fixture.c", reader=reader)
    native, _ = evidence_bytes(plan.out, prefix + "x", reader=reader)
    trace, _ = receipt(plan.out, prefix + "trace-proof.json", reader=reader)
    output, output_pin = evidence_bytes(plan.out, "mechanism/tool-2-selected-W28-full-callback-execute.stdout", reader=reader)
    require(callback.get("name") == "full-W28-TT24-initialization" and callback.get("profile") == "test-p28"
            and same_value(callback.get("shipping_source"), pin(source)) and fixture == expected_fixture
            and same_value(callback.get("fixture_source"), pin(fixture)) and same_value(callback.get("native"), pin(native))
            and same_value(callback.get("output"), pin(output)) and same_value(report["commands"][1].get("stdout"), output_pin)
            and output == (json.dumps(expected_observation, separators=(",", ":")) + "\n").encode()
            and same_value(callback.get("observation"), expected_observation)
            and same_value(callback.get("geometry"), expected_geometry)
            and same_value(callback.get("trace_proof"), expected_trace) and same_value(trace, expected_trace)
            and same_value(callback.get("diagnostic_preamble"), {"text": renderer.DIAGNOSTIC_PREAMBLE.decode(),
                                                               **pin(renderer.DIAGNOSTIC_PREAMBLE)})
            and callback.get("poisoning_changes_first_touch") is True and all(callback.get(key) is False for key in
                ("resource_constants_changed", "padding_checked", "search_executed", "NUMA_claimed", "production_startup_timing_claimed")),
            "P28 full-resource callback bytes/trace/output/state evidence differs")
    directory = plan.out / "mechanism/selected-W28-last-initializer"
    startup, _ = evidence_bytes(plan.out, "mechanism/selected-W28-last-initializer/fixture.c", reader=reader)
    require(startup == renderer.blocked_main(source, plan.family, directory / "release", directory / "last-initializer-arrived"),
            "P28 actual main wrapper differs from the frozen alias-free renderer")
    p28_startup(plan, report, barriers[0], source, reader=reader)
    return {"actual_workers": 28, "actual_tt_bytes": report["resources"]["tt_bytes"],
            "scaled_resources": False, "startup_deadline_ms": 60000}


def p28_d_mechanism(plan, report, build, build_pin, *, reader=None):
    """D retains six production units and adds a separate syscall-only TU."""
    name, source_name = D_ROOT + "check_profile_p28.py", D_ROOT + "source.py"
    modules = []
    for role, relative in (("checker", name), ("source", source_name)):
        data, _ = evidence_bytes(plan.out, "inputs/" + relative, reader=reader)
        require(data == normalized(ROOT / relative, reader=reader) and
                same_value(report.get("inputs", {}).get(relative), pin(data)),
                "D P28 renderer differs from the frozen current CI input")
        modules.append(load_captured("production_ci_D_p28_" + role, plan.out / "inputs" / relative, data))
    renderer, source_module = modules
    geometry = renderer.bound_selection(build)
    p28_resources("D", build["resource"])
    flags = build.get("flags")
    require(type(flags) is list and all(type(flag) is str for flag in flags)
            and [flag for flag in flags if flag.startswith("-DWORKERS=")] == ["-DWORKERS=28"]
            and [flag for flag in flags if flag.startswith("-DTT_BITS=")] == ["-DTT_BITS=25"],
            "D P28 exact worker/TT compile flags required")
    require(report.get("class") == "rove4k-D-bound-p28-mechanism-v1" and report.get("family") == "D"
            and report.get("profile") == "test-p28" and report.get("frozen_execution") is True
            and report.get("real_target_allocation") is True
            and same_value(report.get("build"), {**build_pin, "path": str(Path(build_pin["path"]).parent)})
            and same_value(report.get("geometry"), geometry) and same_value(report.get("flags"), build.get("flags"))
            and type(report.get("actual_workers")) is int and report["actual_workers"] == 28
            and type(report.get("actual_tt_bytes")) is int and report["actual_tt_bytes"] == 512 << 20
            and all(report.get(key) is False for key in ("shipping_binary_executed", "runtime_qualified", "rules_qualified",
                "physical_placement_qualified", "NUMA_qualified", "locality_proof", "production_startup_timing_claimed",
                "strength_claimed", "event_target_confirmed")), "D P28 selected build/resource/scope differs")
    renderer.command_contract(report["commands"])
    inherited = report.get("inherited_CPU_limits")
    require(type(inherited) is list and len(inherited) == 2, "D P28 inherited CPU limit pair is missing")
    applied = renderer.mechanism_limits(tuple(inherited))
    require(same_value(report.get("applied_Host_limits"), applied)
            and same_value(report.get("startup_inherits_parent_CPU_limits"), [applied["parent_CPU"], applied["parent_CPU_hard"]])
            and type(report.get("minimum_launch_headroom_bytes")) is int and report["minimum_launch_headroom_bytes"] == 4 << 30
            and all(same_value(row.get("child_limits"), {"AS": 2 << 30, "CPU": 60}) for row in report["commands"]),
            "D P28 applied CPU/address-space limits differ")
    files = {name: evidence_bytes(plan.out, "artifact/generated-readable/" + name, reader=reader)[0]
             for name in renderer.NATIVE}
    source_pins = {name: pin(data) for name, data in sorted(files.items())}
    # Compare the actual raw manifest, not a reserialization of its JSON values.
    require(same_value(report.get("selected_source"), source_pins) and same_value(report.get("production_proof"), build.get("proof"))
            and same_value(report.get("inputs", {}).get("selection/build.json"),
                           {key: build_pin[key] for key in ("bytes", "sha256")}),
            "D P28 production readable source/proof differs")
    for filename, data in files.items():
        require(same_value(report["inputs"].get("selection/generated-readable/" + filename), pin(data)),
                "D P28 frozen readable source differs")
    rows = report.get("mechanisms", [])
    require(len(rows) == 3, "D P28 requires three separate full TT field/page diagnostics")
    for index, ((case, code), row) in enumerate(zip(renderer.CASES, rows)):
        negative = None if code == 0 else "omit-clear" if code == 7 else "omit-page-owner"
        expected, trace = renderer.poison_fixture(files, source_module, negative=negative)
        directory = plan.out / "mechanism" / case
        for filename, data in expected.items():
            actual, _ = evidence_bytes(plan.out, "mechanism/" + case + "/" + filename, reader=reader)
            require(actual == data, "D P28 full diagnostic source differs from its exact inverse renderer")
        native, _ = evidence_bytes(plan.out, "mechanism/" + case + "/x", reader=reader)
        output, output_pin = evidence_bytes(plan.out,
            "mechanism/tool-" + str(2 * index + 2) + "-execute-" + case + ".stdout", reader=reader)
        wanted = b"TEST_INITIALIZED\nuciok\nreadyok\n" if code == 0 else b"TEST_POISON_REMAINS\n" if code == 7 else b"TEST_OWNER_DIFFERS\n"
        command = ["cc", *build["flags"], *[str(directory / unit) for unit in source_module.UNITS],
                   "-Wl,-T," + str(directory / "image.ld"), "-o", str(directory / "x")]
        require(row.get("name") == case and type(row.get("expected_returncode")) is int and row["expected_returncode"] == code
                and same_value(row.get("instrumentation"), trace) and same_value(row.get("native"), pin(native))
                and same_value(row.get("output"), pin(output)) and output == wanted
                and same_value(report["commands"][2 * index + 1].get("stdout"), output_pin)
                and report["commands"][2 * index].get("command") == command
                and report["commands"][2 * index + 1].get("command") == [str(directory / "x")]
                and all(report["commands"][2 * index + offset].get("cwd") == str(directory) for offset in (0, 1))
                and row.get("complete_entry_fields_checked") is (code != 7)
                and row.get("complete_page_owners_checked") is (code == 0)
                and row.get("poisoning_changes_first_touch") is True and row.get("shipping_identity_claimed") is False,
                "D P28 full-field/page diagnostic proof, native or raw output differs")
    barriers = report.get("startup_barriers", [])
    require(len(barriers) == 1, "D P28 requires one separate unpoisoned main startup")
    barrier = barriers[0]
    directory = plan.out / "mechanism/selected-W28-last-initializer"
    paths = {name: directory / name for name in ("arrived", "release", "joined", "exit_release")}
    extra = renderer.startup_wrapper(paths)
    fixture, _ = evidence_bytes(plan.out, "mechanism/selected-W28-last-initializer/fixture.c", reader=reader)
    native, _ = evidence_bytes(plan.out, "mechanism/selected-W28-last-initializer/x", reader=reader)
    output, _ = evidence_bytes(plan.out, "mechanism/selected-W28-last-initializer/runtime.stdout", reader=reader)
    shipping, _ = evidence_bytes(plan.out, "artifact/shipping-inputs/main.c", reader=reader)
    for filename, data in files.items():
        actual, _ = evidence_bytes(plan.out, "mechanism/selected-W28-last-initializer/" + filename, reader=reader)
        require(actual == data, "D P28 unpoisoned startup changed a production unit")
    command = ["cc", *build["flags"], *[str(directory / unit) for unit in source_module.UNITS], str(directory / "fixture.c"),
               "-Wl,--wrap=spawn,--wrap=main", "-Wl,-T," + str(directory / "image.ld"), "-o", str(directory / "x")]
    require(fixture == extra and report["commands"][-1].get("command") == command and report["commands"][-1].get("cwd") == str(directory)
            and same_value(barrier.get("extra_TU"), pin(extra)) and same_value(barrier.get("fixture_source"), pin(extra))
            and same_value(barrier.get("native"), pin(native)) and same_value(barrier.get("output"), pin(output))
            and same_value(barrier.get("shipping_source"), pin(shipping)) and same_value(build.get("shipping_inputs", {}).get("main.c"), pin(shipping))
            and same_value(barrier.get("production_units"), source_pins)
            and same_value(barrier.get("production_proof"), build.get("proof"))
            and barrier.get("production_units_changed") is False and barrier.get("linker_wrappers") == ["spawn", "main"],
            "D P28 startup multi-unit/extra-TU/native binding differs")
    require(barrier.get("actual_resource_profile") == "test-p28" and all(type(barrier.get(key)) is int and barrier[key] == value
            for key, value in (("actual_workers", 28), ("actual_tt_entries", 1 << 25), ("actual_tt_bytes", 512 << 20),
                ("entry_bytes", 16), ("startup_deadline_ms", 60000), ("legal_GO_cycles", 2), ("spawn_calls_checked", 28),
                ("callback_entries_checked", 28), ("callback_returns_checked", 28)))
            and all(barrier.get(key) is True for key in ("original_stdin_preserved", "last_callback_delayed_before_work",
                "no_UCI_before_release", "final_position_acquire_fence"))
            and all(barrier.get(key) is False for key in ("shipping_identity_claimed", "all_workers_positive_CPU_claimed",
                "physical_placement_qualified", "NUMA_qualified"))
            and same_value(barrier.get("per_ID_callbacks_asserted"),
                           [{"worker": worker, "entries": 1, "returns": 1} for worker in range(28)])
            and type(barrier.get("original_stdin_pipe")) is str and barrier["original_stdin_pipe"].startswith("pipe:["),
            "D P28 actual startup geometry/gate/join counters differ")
    require(all(type(barrier.get(key)) in (int, float) and math.isfinite(barrier[key]) and 0 <= barrier[key] <= 60000
                for key in ("ready_ms_including_intentional_hold", "total_runtime_ms"))
            and barrier["ready_ms_including_intentional_hold"] <= barrier["total_runtime_ms"], "D P28 single 60-second deadline was exceeded")
    journal = report.get("barrier_runtime_cleanup", [])
    cleanup, physical = barrier.get("cleanup", {}), barrier.get("physical", {})
    require(len(journal) == 1 and type(journal[0].get("pid")) is int and journal[0]["pid"] > 0
            and journal[0].get("directory") == str(directory / "runtime") and same_value(journal[0].get("cleanup"), cleanup)
            and type(physical.get("returncode")) is int and physical["returncode"] == 0
            and all(physical.get(key) is True for key in ("reaped", "readers_joined", "stdout_eof", "stderr_eof",
                "original_identity_retained_until_other_members_absent"))
            and physical.get("forced_cleanup") is False and physical.get("pre_reap_other_members") == []
            and all(cleanup.get(key) is True for key in ("owned_group_absent", "readers_joined", "settled_before_cleanup", "reaped"))
            and cleanup.get("forced_cleanup") is False and cleanup.get("errors") == [] and cleanup.get("pre_reap_other_members") == []
            and same_value(report.get("runtime_cleanup"), {"remaining_owned": 0, "drained": [], "errors": []}),
            "D P28 startup ownership/journal did not finish naturally")
    pid = str(journal[0]["pid"])
    tasks, idle, joined = (barrier.get(key) for key in ("startup_tasks", "idle_tasks", "joined_tasks"))
    require(all(type(value) is dict for value in (tasks, idle, joined)) and len(tasks) == len(idle) == 29
            and set(tasks) == set(idle) and pid in tasks and set(joined) == {pid}
            and set(barrier.get("startup_snapshot", {}).get("tasks", {})) == set(tasks)
            and barrier.get("resident", {}).get("pid") == journal[0]["pid"], "D P28 physical task evidence is not29-to1")
    for observation in [*rows, barrier]:
        headroom = observation.get("launch_headroom", {})
        require(type(headroom) is dict and set(headroom) == {"minimum_bytes", "effective_available_bytes", "condition_met"}
                and type(headroom["minimum_bytes"]) is int and headroom["minimum_bytes"] == 4 << 30
                and type(headroom["effective_available_bytes"]) is int and headroom["effective_available_bytes"] >= 4 << 30
                and headroom["condition_met"] is True, "D P28 per-launch effective headroom condition was not met")
    for marker, expected in (("arrived", b"ok\n"), ("release", b"release\n"), ("joined", b"ok\n"), ("exit_release", b"exit\n")):
        data, identity = evidence_bytes(plan.out, "mechanism/selected-W28-last-initializer/" + marker, reader=reader)
        require(data == expected and same_value(barrier.get("markers", {}).get(marker), identity), "D P28 actual marker evidence differs")
    stdout, _ = evidence_bytes(plan.out, "mechanism/selected-W28-last-initializer/runtime/stdout.bin", reader=reader)
    stderr, _ = evidence_bytes(plan.out, "mechanism/selected-W28-last-initializer/runtime/stderr.bin", reader=reader)
    moves = [line[9:] for line in output.splitlines() if line.startswith(b"bestmove ")]
    legal = {f"{file}2{file}{rank}".encode() for file in "abcdefgh" for rank in "34"} | {b"b1a3", b"b1c3", b"g1f3", b"g1h3"}
    require(stdout == output and stderr == b"" and len(moves) == 2 and all(move in legal for move in moves)
            and output.splitlines() == [b"uciok", b"readyok", b"bestmove " + moves[0], b"readyok",
                                       b"bestmove " + moves[1], b"readyok", b"readyok"], "D P28 raw startup protocol differs")
    return {"actual_workers": 28, "actual_tt_bytes": 512 << 20, "scaled_resources": False, "startup_deadline_ms": 60000}


def check_stage(plan, stage, *, reader=None):
    report, identity = receipt(plan.out, stage.receipt, reader=reader)
    family = plan.family
    workers = plan.workers
    result = {"receipt": identity}
    if stage.name in ("generation", "mechanism", "rules"):
        negative = (({"execute-full-entry-omit-clear": 7, "execute-full-entry-omit-page-owner": 8}
                     if plan.profile == "test-p28" else {"execute-w4-spawn-fail": 2, "execute-w4-omit-clear": 7})
                    if stage.name == "mechanism" and family == "D" else None)
        owned_commands(report, expected_codes=negative)
    if stage.name == "generation":
        spelling_variant = producer_spelling_variant(family, plan.spelling_variant, profile=plan.profile)
        resources = report.get("resource" if family == "D" else "resources", {})
        require(report.get("family") == family and resources.get("id") == plan.profile and resources.get("workers") == workers,
                "generation did not produce this fixed " + plan.profile.upper() + " family")
        if plan.profile == "test-p28":
            p28_resources(family, resources)
        if family == "D":
            require(report.get("format") == "rove4k-D-general-source-v1" and report.get("native_reproduced") is True
                    and report.get("frozen_execution") is True and report.get("storage") == "prefix"
                    and report.get("source_reduced", False) is False, "D generation is not the selected prefix class")
        else:
            post = {"path": NEXT + ("profile_b.py" if family == "B" else "profile_phase.py"),
                    "variant": "tcec-final-lf" if family == "B" else "phase-init"}
            require(report.get("class") == "rove4k-production-profile-v1" and report.get("reproducible") is True
                    and report.get("post_profile") == post and report.get("plan", {}).get("representation") == "source-jit",
                    "generation is not the selected source-JIT class")
            spelling = spelling_declaration(family, spelling_variant, profile=plan.profile)
            require("post_spelling" in report and report["post_spelling"] == spelling
                    and report.get("source_dependencies") == {"path": NEXT + "profile_dependencies.py",
                                                               "variant": "unused-includes"},
                    "generation spelling/dependencies differ from the requested producer policy")
            selected_scan = SCAN_DECLARATION if plan.scan_variant != "control" else None
            require(report.get("post_scan") == selected_scan and
                    (selected_scan is not None or "scan_native_policy" not in report),
                    "generation scan differs from the requested producer policy")
            if family == "B" and spelling_variant == "compound":
                request = report.get("spelling_request")
                require(type(request) is dict and request == {"requested": "compound", "effective": "best",
                    "duplicate_best": True, "new_candidate_count": 0}
                    and type(request["duplicate_best"]) is bool and type(request["new_candidate_count"]) is int,
                    "B compound request must identify the existing best duplicate")
            else:
                require("spelling_request" not in report, "unexpected spelling request normalization metadata")
        result["requested_spelling_variant"] = spelling_variant
        if spelling_variant == "compound":
            result["effective_spelling_variant"] = plan.effective_spelling_variant
    elif stage.name == "mechanism":
        effective = effective_spelling(family, plan.spelling_variant, profile=plan.profile)
        require(report.get("source_bound") is True, "canonical/control mechanism is not selected-artifact evidence")
        build, build_pin = receipt(plan.out, "artifact/build.json", reader=reader)
        if plan.scan_variant != "control":
            scan_mechanism_policy(plan, report, build, reader=reader)
        if plan.profile == "test-p28":
            checker = p28_d_mechanism if family == "D" else p28_abcef_mechanism
            result["full_resource_mechanism"] = checker(plan, report, build, build_pin, reader=reader)
            result["scope"] = "actual W28/full TT callback coverage and separate unpoisoned main startup; no NUMA claim"
            return result
        if family == "D":
            require(report.get("kind") == "D-selected-source-poisoned-TT-startup-and-W256-GO-v3"
                    and report.get("selected_build_manifest") == {key: build_pin[key] for key in ("bytes", "sha256")}
                    and report.get("selected_build", {}).get("storage") == "prefix"
                    and report.get("real_target_allocation") is False,
                    "D selected mechanism/source binding differs")
            cases = report.get("cases", [])
            require(len(cases) == 6 and all(row.get("passed") is True and row.get("tt_bits") == 12
                    and row.get("selected_source_equal") is True for row in cases), "D bounded selected mechanism cases are incomplete")
        else:
            expected_class = ("rove4k-bound-scan-mechanism-v1" if plan.scan_variant != "control" else
                "rove4k-bound-B-mechanism-v1" if family == "B" else
                "rove4k-bound-compound-mechanism-v1" if effective == "compound" else "rove4k-bound-phase-mechanism-v1")
            bound_build = {**build_pin, "path": build_pin["path"] if family == "B" else str(Path(build_pin["path"]).parent)}
            require(report.get("class") == expected_class and report.get("build") == bound_build,
                    "selected mechanism build identity differs")
            mechanisms, barriers = report.get("mechanisms", []), report.get("startup_barriers", [])
            require(mechanisms and barriers and all(row.get("shipping_tt_executed") is False for row in mechanisms)
                    and all(row.get("actual_workers") == 4 and row.get("last_initializer_delayed") is True
                        and row.get("no_uci_before_release") is True and row.get("uci_ready_after_release") is True
                        and row.get("legal_search_relaunches") == 2 for row in barriers),
                    "selected callbacks and real startup gate are not separately complete")
            if effective == "compound":
                result["diagnostic_alias"] = compound_mechanism(plan, report, build, reader=reader)
        result["scope"] = "source-bound scaled mechanism and explicit startup gate; no large target TT or NUMA claim"
    elif stage.name == "rules":
        rules, rules_pin = receipt(plan.out, "rules/probe/rules.json", reader=reader)
        require(rules.get("complete") is True and rules.get("family") == family
                and [row.get("mode") for row in rules.get("modes", [])] == ["plain", "ubsan"]
                and all(row.get("cases") == 105 and row.get("legal_moves_compared") == 2858
                        and row.get("legal_sets_equal") is True for row in rules["modes"]),
                "actual plain/UBSan generated-rule evidence is incomplete")
        result.update(actual_rules=rules_pin, cases_per_mode=105, legal_moves_per_mode=2858)
    else:
        qualification, qualification_pin = receipt(plan.out, "runtime/qualification.json", reader=reader)
        _, rules_pin = receipt(plan.out, "rules/probe/rules.json", reader=reader)
        require(report.get("format") == "rove4k-profile-runtime-v1" and report.get("complete") is True
                and report.get("family") == family and report.get("profile") == plan.profile
                and report.get("owned_remaining") == 0 and report.get("final_owned_cleanup") == []
                and qualification.get("format") == "rove4k-qualification-v1"
                and qualification.get("functional_runtime_complete") is True,
                "shipping runtime did not complete naturally")
        sessions = report.get("sessions", [])
        require([row.get("termination") for row in sessions] == ["idle-quit", "idle-EOF", "active-quit", "active-EOF"]
                and report.get("counts", {}).get("GO") == 24 and 22 <= report["counts"].get("legal_bestmoves", 0) <= 24
                and all(row.get("complete") is True and row.get("settled", {}).get("returncode") == 0
                and row["settled"].get("forced_cleanup") is False and row["settled"].get("readers_joined") is True
                and row.get("cleanup", {}).get("owned_group_absent") is True for row in sessions),
                "runtime sessions have not settled their groups/readers")
        checks = qualification.get("checks", {})
        require(set(checks) == set(QUALIFICATION_CHECKS) and all(type(value) is bool for value in checks.values()),
                "qualification must explicitly state every boolean size/placement/functional check")
        require(all(checks.get(key) is True for key in ("reproduction", "startup", "dependencies", "cleanup", "protocol",
                    "legal_moves", "resources", "lifecycle")), "required functional runtime check failed")
        artifact = qualification["artifact"]
        generation, generation_pin = receipt(plan.out, "artifact/build.json", reader=reader)
        whole, whole_pin = evidence_bytes(plan.out, "artifact/" + (D_CANDIDATE if family == "D" else "x"), reader=reader)
        resources = generation["resource" if family == "D" else "resources"]
        if family == "D":
            candidates = [row for row in generation["candidates"] if Path(row["path"]).name == D_CANDIDATE]
            require(len(candidates) == 1, "one explicit D packed candidate required")
            native = candidates[0]["native"]
        else:
            native = {key: generation["expected_contract"]["native_" + key] for key in ("bytes", "sha256")}
        require(qualification.get("evidence", {}).get("runtime") == identity
                and qualification.get("evidence", {}).get("rules", {}).get("evidence", {}).get("rules_report") == rules_pin
                and report.get("build_sha256") == generation_pin["sha256"]
                and artifact.get("sha256") == whole_pin["sha256"] and artifact.get("whole_bytes") == len(whole)
                and artifact.get("representation") == ("packed-native" if family == "D" else "source-jit")
                and artifact.get("native_sha256") == native["sha256"] == report["expected_contract"]["native_sha256"]
                and native["bytes"] == report["expected_contract"]["native_bytes"]
                and artifact.get("tt_bytes") == resources["tt_bytes"]
                and artifact.get("entry_bytes") == resources["tt_entry_bytes"]
                and all(report.get("resources", {}).get(key) == resources[key] for key in resources),
                "runtime/qualification does not bind this fresh source/native/whole/resource cohort")
        require(artifact.get("family") == family and artifact.get("profile") == plan.profile and artifact.get("full") is True
                and artifact.get("workers") == workers and 0 < artifact["whole_bytes"]
                and checks.get("size") == (artifact["whole_bytes"] <= 4096),
                "runtime artifact/resource/size identity differs")
        observations = qualification.get("observations", {})
        startup = observations.get("startup_ms")
        require(type(startup) in (int, float) and math.isfinite(startup) and 0 <= startup <= 60000
                and observations.get("workers") == observations.get("positive_cpu_workers") == workers
                and observations.get("tt_bytes") == resources["tt_bytes"]
                and observations.get("runtime_native_sha256") == native["sha256"]
                and all(observations.get(key) is True for key in
                        ("temporary_cleanup_while_live", "nbrq_replay", "nbrq_generation")),
                "required observed startup/worker/TT/cleanup/rule evidence is missing")
        failures = [key for key, value in checks.items() if value is not True]
        require(set(failures) <= {"size", "placement"} and qualification.get("failures") == failures
                and qualification.get("complete") is (not failures),
                "qualification status contradicts its individual checks")
        result.update(qualification=qualification_pin, artifact=artifact, counts=report["counts"],
            size_eligible=checks["size"], placement_observed=checks.get("placement", False),
            qualification_complete=qualification.get("complete", False), qualification_failures=qualification.get("failures"),
            observations=qualification.get("observations"))
    return result


def execute_plan(plan, report, save, run_command, *, inspect_stage=check_stage):
    """Keep stages dependent; a failed command or receipt prevents its consumers."""
    for stage in plan.stages:
        row = {"name": stage.name, "command": list(stage.command), "complete": False}
        report["stages"].append(row)
        save()
        run_command(list(stage.command), cwd=plan.out, kind="ci-" + stage.name)
        row.update(inspect_stage(plan, stage), complete=True)
        save()


def pipeline_inputs(plan, own, *, verify=None, reader=None, transport=None):
    """Admit the selected factory/target plan through its canonical input reader."""
    names = {SELF, HOST, "engines/scripts/production.py", NEXT + "profile_verify.py",
             NEXT + "profile_rules.py", *(str(Path(s.command[3]).relative_to(ROOT)).replace("\\", "/") for s in plan.stages)}
    if isinstance(plan, Plan) and plan.profile == "test-p28" and plan.family == "D":
        names.add(D_ROOT + "source.py")
    if isinstance(plan, Plan) and plan.scan_variant != "control":
        names.update((NEXT + "check_profile_compound.py", NEXT + "check_profile_p28.py"))
    if transport is not None:
        names.update((TRANSPORT, NEXT + "target_runtime.py", NEXT + "profile_compiler.py", verify.INPUT_READER))
    inputs = {name: own if name == SELF else normalized(ROOT / name, reader=reader) for name in sorted(names)}
    if reader is not None:
        require(reader.source_identity() == inputs[verify.INPUT_READER],
                "CI input reader snapshot differs from its executing source")
        verify.executing_source(inputs[NEXT + "profile_verify.py"])
    require(pin(inputs[HOST])["sha256"] == HOST_SHA, "bounded owned command helper differs")
    return inputs


def target_inspector(plan, verify, admitted, target, ci_context):
    """Keep the validated target reference object out of transport JSON."""
    reference = None
    reader = verify.input_reader()
    def inspect(unused_plan, stage):
        nonlocal reference
        if stage.name == "compiler":
            report, identity = receipt(plan.out, stage.receipt, reader=reader)
            owned_commands(report)
            require(report.get("format") == target.COMPILER_FORMAT and report.get("engine_executed") is False
                    and report.get("large_TT_allocated") is False,
                    "actual target compiler-only receipt required")
            reference = target.validate_target_runtime(admitted, plan.build,
                plan.out / "compiler/compiler.json", verify=verify, source_bundle=plan.bundle,
                source_seal=plan.seal, expected_ci=ci_context)
            record = reference.to_record()
            require(record.get("family") == plan.family and record.get("profile") == plan.profile
                    and record.get("factory_replayed_on_target") is False,
                    "target compiler reference differs from the sealed single-family profile")
            return {"receipt": identity, "target_runtime_reference": record,
                    "factory_replayed_on_target": False}
        require(reference is not None, "target consumers require the validated compiler reference")
        if stage.name == "rules":
            return check_stage(plan, stage, reader=reader)
        require(stage.name == "runtime", "unrecognized target pipeline stage")
        report, identity = receipt(plan.out, "runtime/runtime.json", reader=reader)
        saved, saved_pin = receipt(plan.out, "runtime/qualification.json", reader=reader)
        reference.revalidate(verify=verify, expected_ci=ci_context)
        checked = verify.qualification_record(admitted, plan.build, plan.out / "runtime/runtime.json",
            rules_path=plan.out / "rules/probe/rules.json", target_reference=reference)
        record = reference.to_record()
        require(saved == checked and saved.get("target_compiler_bound") is True
                and saved.get("target_runtime_reference") == record
                and report.get("target_runtime_reference") == record
                and report.get("target_context_before_post_unchanged") is True
                and report.get("expected_contract") == admitted.expected
                and report.get("runtime_native_contract") == reference.native_pin,
                "target runtime does not bind the original source and independently validated cc11 image")
        checks = checked["checks"]
        require(checked.get("functional_runtime_complete") is True
                and set(checks) == set(QUALIFICATION_CHECKS) and all(type(value) is bool for value in checks.values())
                and all(checks[key] is True for key in QUALIFICATION_CHECKS if key not in ("size", "placement")),
                "target functional runtime checks are incomplete")
        return {"receipt": identity, "qualification": saved_pin, "artifact": checked["artifact"],
                "counts": report["counts"], "size_eligible": checks["size"], "placement_observed": checks["placement"],
                "qualification_complete": checked["complete"], "qualification_failures": checked["failures"],
                "observations": checked["observations"], "target_runtime_reference": record,
                "factory_replayed_on_target": False}
    return inspect


def export_closed_pipeline(report, out, *, family, runner_temp, verify, target, transport,
                           ci_context, reader, inputs, save, profile="test-p4"):
    """Keep requested transport failure separate from settled functional evidence."""
    try:
        profile_workers(profile)
        require(report.get("complete") is True and report.get("functional_complete") is True
                and report.get("host_cleanup") == {"unsettled_commands": 0, "errors": []},
                "source export requires a closed successful functional pipeline")
        functional = out / "pipeline-functional.json"
        require(not functional.exists(), "functional export preimage already exists")
        transport._write_new(functional, reader.read_regular(out / "pipeline.json", limit=64 << 20), target)
        report["source_export"] = transport.export_bundle(out, out / "artifact", family=family,
            runner_temp=runner_temp, verify=verify, target=target, ci_context=ci_context, pipeline_receipt=functional,
            profile=profile)
        require(all(normalized(ROOT / name, reader=reader) == data for name, data in inputs.items()),
                "source export tools changed during sealing")
    except BaseException as error:
        report.update(complete=False, export_failure={"type": type(error).__name__, "message": str(error)})
        raise
    finally:
        save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=tuple("ABCDEF"), required=True)
    parser.add_argument("--profile", choices=tuple(PROFILE_WORKERS), default="test-p4")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--export-source-bundle", action="store_true",
                        help="after successful Ubuntu24 cleanup export source-bundle.zip and source-seal.json")
    parser.add_argument("--ubuntu22-target", action="store_true",
                        help="restore the sealed source layout and observe system cc11.4 source-JIT runtime")
    parser.add_argument("--source-bundle", type=Path)
    parser.add_argument("--source-seal", type=Path)
    parser.add_argument("--spelling-variant", choices=("control", "best", "compound"),
                        help="producer-only source spelling selection (default: control); target consumes the sealed choice")
    parser.add_argument("--scan-variant", choices=("control", "square-successor"),
                        help="producer-only A/C compound scan selection; target consumes the sealed choice")
    args = parser.parse_args()
    profile_workers(args.profile)
    if args.ubuntu22_target:
        require(args.spelling_variant is None, "spelling selection is producer-only; target consumes the sealed choice")
        require(args.scan_variant is None, "scan selection is producer-only; target consumes the sealed choice")
    else:
        spelling_variant = producer_spelling_variant(args.family,
            "control" if args.spelling_variant is None else args.spelling_variant, profile=args.profile)
        scan_variant = producer_scan_variant(args.family, spelling_variant,
            "control" if args.scan_variant is None else args.scan_variant)
    require((args.source_bundle is not None) == (args.source_seal is not None), "source ZIP and seal must be supplied together")
    require(args.ubuntu22_target == (args.source_bundle is not None)
            and not (args.ubuntu22_target and args.export_source_bundle),
            "target mode requires source ZIP/seal; source export belongs only to the Ubuntu24 factory")
    require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux x86-64 CI host required")
    release = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
    required_release = "22.04" if args.ubuntu22_target else "24.04"
    require(release.get("ID", "").strip('"') == "ubuntu" and release.get("VERSION_ID", "").strip('"') == required_release,
            "this pipeline requires its explicit Ubuntu " + required_release + " backend")
    require("RUNNER_TEMP" in os.environ, "RUNNER_TEMP must name the CI temporary root")
    runner_temp = Path(os.environ["RUNNER_TEMP"])
    out = admit_output(args.out, runner_temp)
    own = normalized(Path(__file__))
    require(compile(own, __file__, "exec", dont_inherit=True) == _EXECUTING_CODE, "CI driver changed after module compilation")
    verify = target = transport = ci_context = restored = admitted = reader = None
    if args.ubuntu22_target or args.export_source_bundle:
        if args.ubuntu22_target:
            target_environment(os.environ)
        verify = load("production_ci_target_verify", ROOT / NEXT / "profile_verify.py")
        reader = verify.input_reader()
        reader.source_identity()
        verify.executing_source(normalized(ROOT / NEXT / "profile_verify.py", reader=reader))
        target = verify.target_module()
        ci_context = target.CIContext.from_environment()
        transport = load("production_ci_source_transport", ROOT / TRANSPORT)
    if args.ubuntu22_target:
        restored = transport.restore_bundle(args.source_bundle, args.source_seal, family=args.family,
            runner_temp=runner_temp, verify=verify, target=target, ci_context=ci_context, reserved_out=out,
            profile=args.profile)
        build = Path(restored["build_root"])
        raw = reader.read_regular(verify.artifact_file(build, "build.json"), limit=16 << 20)
        manifest = json.loads(raw)
        admitted = (verify.admit_d_build(manifest, build, "D-source-jit") if args.family == "D"
                    else verify.admit_c_build(manifest, build))
        require(admitted.family == args.family and admitted.profile_id == args.profile
                and admitted.representation == "source-jit", "sealed target source is not the requested fixed full TEST C-JIT profile")
        plan = target_plan(args.family, out, build, args.source_bundle, args.source_seal, profile=args.profile)
    else:
        plan = pipeline_plan(args.family, out, spelling_variant=spelling_variant, scan_variant=scan_variant, profile=args.profile)
    inputs = pipeline_inputs(plan, own, verify=verify, reader=reader, transport=transport)
    out.mkdir(parents=True)
    for name, data in inputs.items():
        path = out / "inputs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    report = {"format": SCHEMA, "family": args.family, "profile": args.profile,
        "backend": "ubuntu-22.04-system-cc11.4" if args.ubuntu22_target else "ubuntu-24.04-gcc13-host-cc",
        "complete": False, "functional_complete": False, "commands": [], "stages": [],
        "inputs": {name: pin(data) for name, data in inputs.items()},
        "league_admitted": False, "release_qualified": False, "event_target_confirmed": False,
        "target_compiler_qualified": False, "scope": "CI functional/source evidence; size and placement remain separate"}
    if ci_context is not None:
        report["source_context"] = ci_context.to_record()
    if args.ubuntu22_target:
        report.update(factory_replayed_on_target=False, source_restore=restored, target_compiler_bound=False)
    else:
        report["requested_spelling_variant"] = plan.spelling_variant
        if plan.scan_variant != "control":
            report["requested_scan_variant"] = plan.scan_variant
        if plan.spelling_variant == "compound":
            report["effective_spelling_variant"] = plan.effective_spelling_variant
    def save():
        (out / "pipeline.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    owner = load("production_ci_owned_host", out / "inputs" / HOST)
    owner.LIMITS = {**owner.LIMITS, "aggregate_wall": 3600, "per_command_wall": 1800,
        "parent_AS": 4 << 30, "parent_CPU": 300, "parent_CPU_hard": 1230,
        "child_AS": 4 << 30, "child_CPU": 1200, "tool_output_bytes": 16 << 20}
    class Host(owner.Host):
        def settle(self, child, row, force=False):
            row["cooperative_termination_seconds"] = 30
            return super().settle(child, row, force)
    previous = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    host = None
    try:
        host = Host(out, report, save)
        def run(command, **keywords):
            result = host.run(command, **keywords)
            require(all(normalized(ROOT / name, reader=reader) == data for name, data in inputs.items()),
                    "CI orchestration/backend source changed during a stage")
            if reader is not None:
                require(reader.source_identity() == inputs[verify.INPUT_READER],
                        "CI input reader changed during a stage")
            return result
        compiler_metadata = target_compiler_record if args.ubuntu22_target else compiler_record
        report["compiler"] = compiler_metadata(
            run(["cc", "--version"], cwd=out, kind="ci-compiler-banner"),
            run(["cc", "-dumpfullversion", "-dumpversion"], cwd=out, kind="ci-compiler-version"))
        save()
        inspector = target_inspector(plan, verify, admitted, target, ci_context) if args.ubuntu22_target else check_stage
        execute_plan(plan, report, save, run, inspect_stage=inspector)
        if args.ubuntu22_target:
            report["target_compiler_bound"] = True
        report["functional_complete"] = True
    except BaseException as error:
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        try:
            if host is not None:
                host.close()
        except BaseException as error:
            report["cleanup_failure"] = {"type": type(error).__name__, "message": str(error)}
            report["functional_complete"] = False
            raise
        finally:
            report["complete"] = report["functional_complete"] and report.get("host_cleanup") == {"unsettled_commands": 0, "errors": []}
            save()
            signal.signal(signal.SIGCHLD, previous)
    require(report["complete"], "functional pipeline did not complete its owned cleanup")
    if args.export_source_bundle:
        export_closed_pipeline(report, out, family=args.family, runner_temp=runner_temp,
            verify=verify, target=target, transport=transport, ci_context=ci_context,
            reader=reader, inputs=inputs, save=save, profile=args.profile)
    runtime = report["stages"][-1]
    print(json.dumps({"complete": True, "functional_complete": True, "family": args.family,
        "whole_bytes": runtime["artifact"]["whole_bytes"], "size_eligible": runtime["size_eligible"],
        "placement_observed": runtime["placement_observed"], "qualification_complete": runtime["qualification_complete"],
        "league_admitted": False, "release_qualified": False, **runtime["counts"]}), flush=True)


if __name__ == "__main__":
    main()
