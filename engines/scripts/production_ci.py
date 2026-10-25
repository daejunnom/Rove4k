#!/usr/bin/env python3
"""Run one selected TEST-P4 functional pipeline in a fresh CI temporary tree.

Generation, instrumented mechanisms, actual rules and shipping runtime retain
their own receipts. This driver does not admit a league player, confirm TCEC
allocation, or turn a passing functional job into size/placement acceptance.
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
HOST_SHA = "fc916e798952cff1c915a6846e758874bc2d858b3c59dec73870b95c7e3d4828"
NEXT = "engines/experiments/tcec-next/"
D_ROOT = "engines/experiments/tiny-d-submission/"
SCHEMA = "rove4k-production-ci-functional-v1"
D_CANDIDATE = "D-packed-xz-bcj"
QUALIFICATION_CHECKS = ("reproduction", "startup", "dependencies", "cleanup", "protocol",
                        "legal_moves", "resources", "lifecycle", "size", "placement")


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def normalized(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
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


def pipeline_plan(family, out, *, python=sys.executable, repo=ROOT):
    require(family in tuple("ABCDEF"), "one active C family A through F is required")
    out, repo = Path(out), Path(repo)
    require(out.is_absolute() and repo.is_absolute(), "absolute pipeline roots required")
    artifact = out / "artifact"
    def command(script, *arguments):
        return tuple(map(str, (python, "-I", "-B", repo / script, *arguments)))
    if family == "D":
        generation = command(D_ROOT + "build.py", "--profile", "test-p4", "--storage", "prefix", "--out", artifact)
        mechanism = command(D_ROOT + "test_startup.py", "--build", artifact, "--out", out / "mechanism")
        rules = command(D_ROOT + "profile_rules.py", "--build", artifact, "--out", out / "rules")
        runtime = command(NEXT + "profile_verify.py", "--build", artifact, "--candidate", D_CANDIDATE,
                          "--rules", out / "rules/probe/rules.json", "--out", out / "runtime")
    else:
        variant = ("--b-variant", "tcec-final-lf") if family == "B" else ("--phase-variant", "phase-init")
        generation = command(NEXT + "profile_build.py", "--entry", family, "--profile", "test-p4",
                             *variant, "--out", artifact)
        mechanism = (command(NEXT + "check_profile_b.py", "--build", artifact, "--mode", "bound", "--out", out / "mechanism")
                     if family == "B" else command(NEXT + "check_profile_phase.py", "--build", artifact, "--out", out / "mechanism"))
        rules = command(NEXT + "profile_rules.py", "--source", artifact / "main.c", "--baseline", artifact / "control/main.c",
                        "--proof", artifact / "source-proof.json", "--family", family, "--profile", "test-p4",
                        "--build", artifact, "--out", out / "rules")
        runtime = command(NEXT + "profile_verify.py", "--build", artifact,
                          "--rules", out / "rules/probe/rules.json", "--out", out / "runtime")
    return Plan(family, out, (
        Stage("generation", generation, "artifact/build.json"),
        Stage("mechanism", mechanism, "mechanism/result.json" if family == "B" else "mechanism/results.json"),
        Stage("rules", rules, "rules/commands.json"),
        Stage("runtime", runtime, "runtime/runtime.json")))


def evidence_bytes(out, relative):
    path = Path(out) / relative
    require(not any(p.is_symlink() for p in (path, *path.parents)), "receipt cannot follow filesystem links")
    path = path.resolve(strict=True)
    require(path.is_relative_to(Path(out).resolve()) and path.is_file() and path.stat().st_nlink == 1
            and path.stat().st_size <= 64 << 20, "bounded ordinary pipeline receipt required")
    data = path.read_bytes()
    return data, {"path": str(path), **pin(data)}


def receipt(out, relative):
    data, identity = evidence_bytes(out, relative)
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


def check_stage(plan, stage):
    report, identity = receipt(plan.out, stage.receipt)
    family = plan.family
    result = {"receipt": identity}
    if stage.name in ("generation", "mechanism", "rules"):
        negative = ({"execute-w4-spawn-fail": 2, "execute-w4-omit-clear": 7}
                    if stage.name == "mechanism" and family == "D" else None)
        owned_commands(report, expected_codes=negative)
    if stage.name == "generation":
        resources = report.get("resource" if family == "D" else "resources", {})
        require(report.get("family") == family and resources.get("id") == "test-p4" and resources.get("workers") == 4,
                "generation did not produce this fixed TEST-P4 family")
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
    elif stage.name == "mechanism":
        require(report.get("source_bound") is True, "canonical/control mechanism is not selected-artifact evidence")
        build, build_pin = receipt(plan.out, "artifact/build.json")
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
            expected_class = "rove4k-bound-B-mechanism-v1" if family == "B" else "rove4k-bound-phase-mechanism-v1"
            bound_build = {**build_pin, "path": build_pin["path"] if family == "B" else str(Path(build_pin["path"]).parent)}
            require(report.get("class") == expected_class and report.get("build") == bound_build,
                    "selected mechanism build identity differs")
            mechanisms, barriers = report.get("mechanisms", []), report.get("startup_barriers", [])
            require(mechanisms and barriers and all(row.get("shipping_tt_executed") is False for row in mechanisms)
                    and all(row.get("actual_workers") == 4 and row.get("last_initializer_delayed") is True
                        and row.get("no_uci_before_release") is True and row.get("uci_ready_after_release") is True
                        and row.get("legal_search_relaunches") == 2 for row in barriers),
                    "selected callbacks and real startup gate are not separately complete")
        result["scope"] = "source-bound scaled mechanism and explicit startup gate; no large target TT or NUMA claim"
    elif stage.name == "rules":
        rules, rules_pin = receipt(plan.out, "rules/probe/rules.json")
        require(rules.get("complete") is True and rules.get("family") == family
                and [row.get("mode") for row in rules.get("modes", [])] == ["plain", "ubsan"]
                and all(row.get("cases") == 105 and row.get("legal_moves_compared") == 2858
                        and row.get("legal_sets_equal") is True for row in rules["modes"]),
                "actual plain/UBSan generated-rule evidence is incomplete")
        result.update(actual_rules=rules_pin, cases_per_mode=105, legal_moves_per_mode=2858)
    else:
        qualification, qualification_pin = receipt(plan.out, "runtime/qualification.json")
        _, rules_pin = receipt(plan.out, "rules/probe/rules.json")
        require(report.get("format") == "rove4k-profile-runtime-v1" and report.get("complete") is True
                and report.get("family") == family and report.get("profile") == "test-p4"
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
        generation, generation_pin = receipt(plan.out, "artifact/build.json")
        whole, whole_pin = evidence_bytes(plan.out, "artifact/" + (D_CANDIDATE if family == "D" else "x"))
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
        require(artifact.get("family") == family and artifact.get("profile") == "test-p4" and artifact.get("full") is True
                and artifact.get("workers") == 4 and 0 < artifact["whole_bytes"]
                and checks.get("size") == (artifact["whole_bytes"] <= 4096),
                "runtime artifact/resource/size identity differs")
        observations = qualification.get("observations", {})
        startup = observations.get("startup_ms")
        require(type(startup) in (int, float) and math.isfinite(startup) and 0 <= startup <= 60000
                and observations.get("workers") == observations.get("positive_cpu_workers") == 4
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=tuple("ABCDEF"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux x86-64 CI host required")
    release = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
    require(release.get("ID", "").strip('"') == "ubuntu" and release.get("VERSION_ID", "").strip('"') == "24.04",
            "this functional bridge requires the Ubuntu 24.04 host backend")
    require("RUNNER_TEMP" in os.environ, "RUNNER_TEMP must name the CI temporary root")
    out = admit_output(args.out, Path(os.environ["RUNNER_TEMP"]))
    plan = pipeline_plan(args.family, out)
    own = normalized(Path(__file__))
    require(compile(own, __file__, "exec", dont_inherit=True) == _EXECUTING_CODE, "CI driver changed after module compilation")
    names = {SELF, HOST, "engines/scripts/production.py", NEXT + "profile_verify.py",
             NEXT + "profile_rules.py", *(str(Path(s.command[3]).relative_to(ROOT)).replace("\\", "/") for s in plan.stages)}
    inputs = {name: own if name == SELF else normalized(ROOT / name) for name in sorted(names)}
    require(pin(inputs[HOST])["sha256"] == HOST_SHA, "bounded owned command helper differs")
    out.mkdir(parents=True)
    for name, data in inputs.items():
        path = out / "inputs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    report = {"format": SCHEMA, "family": args.family, "profile": "test-p4", "backend": "ubuntu-24.04-gcc13-host-cc",
        "complete": False, "functional_complete": False, "commands": [], "stages": [],
        "inputs": {name: pin(data) for name, data in inputs.items()},
        "league_admitted": False, "release_qualified": False, "event_target_confirmed": False,
        "target_compiler_qualified": False, "scope": "CI functional/source evidence; size and placement remain separate"}
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
            require(all(normalized(ROOT / name) == data for name, data in inputs.items()),
                    "CI orchestration/backend source changed during a stage")
            return result
        report["compiler"] = compiler_record(
            run(["cc", "--version"], cwd=out, kind="ci-compiler-banner"),
            run(["cc", "-dumpfullversion", "-dumpversion"], cwd=out, kind="ci-compiler-version"))
        save()
        execute_plan(plan, report, save, run)
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
    runtime = report["stages"][-1]
    print(json.dumps({"complete": True, "functional_complete": True, "family": args.family,
        "whole_bytes": runtime["artifact"]["whole_bytes"], "size_eligible": runtime["size_eligible"],
        "placement_observed": runtime["placement_observed"], "qualification_complete": runtime["qualification_complete"],
        "league_admitted": False, "release_qualified": False, **runtime["counts"]}), flush=True)


if __name__ == "__main__":
    main()
